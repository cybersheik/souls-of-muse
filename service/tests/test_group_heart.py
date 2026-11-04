"""Offline group heart guard; retained fixtures, ephemeral signing keys, no models."""
import json
import sqlite3
import tempfile
import sys
import unittest
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.app import create_app
from service.identity import password_hash


class NoModels:
    asr_enabled = False

    def complete(self, *args, **kwargs):
        raise AssertionError("A heart transition must never call a model")


class GroupHeart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.accounts = {
            person: {"role": role, "password_hash": password_hash("offline-group-heart")}
            for person, role in [("M", "maestro"), ("A", "artist"), ("B", "artist")]
        }

    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="cx1-group-heart-", dir="/private/tmp" if sys.platform == "darwin" else None)
        self.key = Ed25519PrivateKey.generate()
        self.build()
        self.clients = {}
        for person in self.accounts:
            client = TestClient(self.site, headers={"Origin": "http://testserver", "X-SOM-Participant": person})
            response = client.post("/api/harness/auth/login", json={"username": person, "password": "offline-group-heart"})
            self.assertEqual(response.status_code, 200, response.text)
            self.clients[person] = client

    def build(self):
        self.site = FastAPI()
        self.site.mount("/api/harness", create_app(
            data_dir=self.directory, adapter=NoModels(), heart_key=self.key,
            environ={"SOM_WEB_ACCOUNTS": json.dumps(self.accounts), "SOM_COOKIE_SECURE": "0"},
        ))

    def meeting(self, group=True):
        roster = {"artist_ids": ["A", "B"]} if group else {"artist_id": "A"}
        response = self.clients["M"].post("/api/harness/sessions", json={
            "kind": "group" if group else "individual", "league": "string",
            "maestro_alias": "M", "artist_alias": "Artists", "source_lang": "en", "target_lang": "vi", **roster,
        })
        self.assertEqual(response.status_code, 201, response.text)
        sid = response.json()["id"]
        route = "/api/harness/sessions/" + sid
        self.assertEqual(self.clients["M"].post(route + "/start").status_code, 200)
        for person in (["M", "A", "B"] if group else ["M", "A"]):
            self.assertEqual(self.clients[person].post(route + "/join").status_code, 200)
        return sid, route

    def test_three_present_group_members_complete_without_fictitious_pair_awards(self):
        sid, route = self.meeting()
        for _ in range(2):
            response = self.clients["M"].post(route + "/complete")
            self.assertEqual(response.status_code, 200, response.text)
        with sqlite3.connect(self.directory + "/service.sqlite3") as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM heart_outbox WHERE session_id=?", (sid,)).fetchone()[0], 0)
        for person in ["M", "A", "B"]:
            response = self.clients[person].get(route + "/heart")
            self.assertEqual(response.status_code, 200, response.text)
            heart = response.json()
            self.assertEqual(heart.get("accrual"), {"supported": False, "state": "group_policy_pending"})
            self.assertEqual(heart["counters"]["happened"], 0)
            self.assertEqual(heart["delivery"], [])
            self.assertTrue(heart["signing_ready"])

    def test_individual_pair_awards_still_happen_once_per_present_member(self):
        sid, route = self.meeting(group=False)
        for _ in range(2):
            self.assertEqual(self.clients["M"].post(route + "/complete").status_code, 200)
        for person in ["M", "A"]:
            heart = self.clients[person].get(route + "/heart").json()
            self.assertEqual(heart["counters"]["happened"], 1)
            self.assertEqual([row["state"] for row in heart["delivery"]], ["delivered", "delivered"])

    def test_restart_does_not_drain_a_stale_group_pair_event_into_signed_journal(self):
        sid, route = self.meeting()
        event = {"event_id": str(uuid.uuid4()), "lesson_id": sid, "seq": 1, "ts": "2026-11-04T06:00:00Z",
                 "type": "lesson.completed", "actor": "server", "payload": {"soul_id": "M", "counterparty": "A"}}
        with sqlite3.connect(self.directory + "/service.sqlite3") as connection:
            connection.execute("INSERT INTO heart_outbox(event_id,session_id,event_json) VALUES(?,?,?)", (event["event_id"], sid, json.dumps(event)))
        self.build()
        heart = self.clients["M"].get(route + "/heart").json()
        self.assertEqual(heart["counters"]["happened"], 0)
        self.assertEqual(heart["delivery"], [{"state": "rejected", "reason": "group_policy_pending"}])


if __name__ == "__main__":
    unittest.main()
