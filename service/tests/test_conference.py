"""Real HTTP signalling boundaries; no camera, network, models or credentials."""
import sqlite3
import unittest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


class ConferenceRoutes(unittest.TestCase):
    def setUp(self):
        from service.conference import register_routes
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.execute("CREATE TABLE session_presence(session_id TEXT, participant TEXT)")
        self.connection.executemany("INSERT INTO session_presence VALUES('lesson',?)", [(u,) for u in ("M", "A", "B")])
        self.connection.commit()
        # The installer closes callback connections; retain this in-memory owner.
        class Connection:
            def __init__(self, raw): self.raw = raw
            def execute(self, *args): return self.raw.execute(*args)
            def close(self): pass
        self.db = lambda: Connection(self.connection)
        self.now = 0.0
        self.active = True
        self.members = {"M", "A", "B"}
        self.app = FastAPI()
        def err(code, reason): return JSONResponse({"detail": reason}, status_code=code)
        def auth(authorization, request):
            user = request.headers.get("X-Test-User")
            if not user: return None, err(401, "unauthorized")
            if request.method == "POST" and request.headers.get("Origin") != "http://testserver":
                return None, err(403, "origin_not_allowed")
            request.state.participant = user
            return "maestro" if user == "M" else "artist", None
        def find(c, sid, request):
            if sid != "lesson" or request.state.participant not in self.members: return None
            return {"state": "active" if self.active else "completed", "maestro_id": "M", "artist_id": "A"}
        register_routes(self.app, self.db, lambda c: None, auth, find, err,
                        member_ids=lambda c, sid, session: self.members, clock=lambda: self.now)
        self.clients = {u: TestClient(self.app, headers={"X-Test-User": u, "Origin": "http://testserver"}) for u in ("M", "A", "B", "other")}
        self.path = "/sessions/lesson/conference"
        self.addCleanup(self.connection.close)

    def join(self, user):
        response = self.clients[user].post(self.path + "/join", json={})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def poll(self, user, joined, after=0):
        return self.clients[user].get(self.path + "/events", params={"connection_id": joined["connection_id"], "after": after})

    def signal(self, user, source, target, dest, **payload):
        return self.clients[user].post(self.path + "/signal", json={
            "connection_id": source["connection_id"], "to": target,
            "to_connection": dest["connection_id"], **payload})

    def test_three_members_get_personal_roster_and_targeted_server_owned_sender(self):
        m, a, b = self.join("M"), self.join("A"), self.join("B")
        self.assertEqual({p["id"] for p in self.poll("M", m).json()["peers"]}, {"A", "B"})
        sent = self.signal("M", m, "A", a, description={"type": "offer", "sdp": "v=0\r\n"})
        self.assertEqual(sent.status_code, 200, sent.text)
        self.assertEqual(self.poll("B", b).json()["events"], [])
        event = self.poll("A", a).json()["events"][0]
        self.assertEqual(event["from"], "M")
        self.assertEqual(event["from_connection"], m["connection_id"])
        self.assertEqual(event["description"], {"type": "offer", "sdp": "v=0\r\n"})
        self.assertEqual(self.poll("A", a, event["id"]).json()["events"], [])

    def test_auth_membership_join_and_active_state_gate_all_routes(self):
        self.assertEqual(TestClient(self.app).post(self.path + "/join", json={}).status_code, 401)
        self.assertEqual(self.clients["other"].post(self.path + "/join", json={}).status_code, 404)
        self.connection.execute("DELETE FROM session_presence WHERE participant='B'")
        self.assertEqual(self.clients["B"].post(self.path + "/join", json={}).status_code, 403)
        m = self.join("M")
        self.active = False
        self.assertEqual(self.poll("M", m).status_code, 409)
        self.assertEqual(self.clients["M"].post(self.path + "/join", json={}).status_code, 409)

    def test_signal_cannot_spoof_sender_or_reach_outsider_or_old_connection(self):
        m, a = self.join("M"), self.join("A")
        payload = {"description": {"type": "offer", "sdp": "v=0"}}
        self.assertEqual(self.signal("M", m, "A", a, sender="B", **payload).status_code, 422)
        self.assertEqual(self.signal("M", m, "other", a, **payload).status_code, 404)
        newer = self.join("A")
        self.assertNotEqual(newer["connection_id"], a["connection_id"])
        self.assertEqual(self.signal("M", m, "A", a, **payload).status_code, 409)
        self.assertEqual(self.poll("A", a).status_code, 409)
        self.assertEqual(self.clients["A"].post(self.path + "/leave", json={"connection_id": a["connection_id"]}).status_code, 200)
        self.assertEqual(self.poll("A", newer).status_code, 200)

    def test_expired_peers_and_events_disappear_and_do_not_replay_to_new_connection(self):
        m, a = self.join("M"), self.join("A")
        self.signal("M", m, "A", a, candidate={"candidate": "candidate:1", "sdpMid": "0", "sdpMLineIndex": 0})
        self.now = 46
        self.assertEqual(self.poll("A", a).status_code, 409)
        newer = self.join("A")
        self.assertEqual(self.poll("A", newer).json()["events"], [])
        self.assertEqual(self.poll("A", newer).json()["peers"], [])

    def test_bounded_payload_and_queue_fail_without_silent_signal_loss(self):
        m, a = self.join("M"), self.join("A")
        self.assertEqual(self.signal("M", m, "A", a, description={"type": "offer", "sdp": "x" * 20001}).status_code, 422)
        self.assertEqual(self.signal("M", m, "A", a, description={"type": "offer", "sdp": "v=0"}, candidate=None).status_code, 422)
        self.assertEqual(self.signal("M", m, "A", a, description={"type": "rollback", "sdp": ""}).status_code, 422)
        for _ in range(128):
            self.assertEqual(self.signal("M", m, "A", a, candidate={"candidate": "candidate:1"}).status_code, 200)
        self.assertEqual(self.signal("M", m, "A", a, candidate={"candidate": "candidate:2"}).status_code, 429)

    def test_membership_revocation_removes_roster_and_prevents_delivery(self):
        m, a = self.join("M"), self.join("A")
        self.members.remove("A")
        self.assertEqual(self.poll("M", m).json()["peers"], [])
        self.assertEqual(self.signal("M", m, "A", a, candidate=None).status_code, 404)

    def test_large_unicode_signals_hit_byte_budget_before_event_count_limit(self):
        m, a = self.join("M"), self.join("A")
        payload = {"description": {"type": "offer", "sdp": "♪" * 12000}}
        for _ in range(7):
            self.assertEqual(self.signal("M", m, "A", a, **payload).status_code, 200)
        self.assertEqual(self.signal("M", m, "A", a, **payload).status_code, 429)


if __name__ == "__main__": unittest.main()
