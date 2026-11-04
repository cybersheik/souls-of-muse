"""Offline group identity regressions; fixtures are retained under /private/tmp/cx1-*."""
import json
import sqlite3
import sys
import tempfile
import unittest
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.app import create_app
from service.identity import password_hash
from service.tests.test_service import FakeAdapter


class GroupParticipants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.accounts = {
            name: {"role": role, "name": display, "password_hash": password_hash("offline-group-fixture")}
            for name, role, display in [
                ("M", "maestro", "Maestro"), ("A", "artist", "Artist A"),
                ("B", "artist", "Artist B"), ("outside", "artist", "Outside"),
            ]
        }

    def setUp(self):
        # Deliberately no automatic directory cleanup: CX1 storage policy.
        self.directory = tempfile.mkdtemp(prefix="cx1-group-participants-", dir="/private/tmp" if sys.platform == "darwin" else None)
        self.adapter = FakeAdapter()
        self.build()
        self.clients = {name: self.login(name) for name in self.accounts}

    def build(self):
        self.site = FastAPI()
        self.site.mount("/api/harness", create_app(
            data_dir=self.directory, adapter=self.adapter,
            environ={"SOM_WEB_ACCOUNTS": json.dumps(self.accounts), "SOM_COOKIE_SECURE": "0"},
        ))

    def login(self, name):
        client = TestClient(self.site, headers={"Origin": "http://testserver"})
        response = client.post("/api/harness/auth/login", json={"username": name, "password": "offline-group-fixture"})
        self.assertEqual(response.status_code, 200, response.text)
        client.headers["X-SOM-Participant"] = quote(name, safe="")
        return client

    def create(self, **changes):
        body = {"kind": "group", "league": "string", "maestro_alias": "Maestro", "artist_alias": "Children",
                "artist_ids": ["A", "B"], "source_lang": "en", "target_lang": "vi", **changes}
        return self.clients["M"].post("/api/harness/sessions", json=body)

    def group(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.text)
        return "/api/harness/sessions/" + response.json()["id"]

    def test_both_artists_have_the_same_shared_lesson_and_presence(self):
        route = self.group()
        self.assertEqual(self.clients["M"].post(route + "/start").status_code, 200)
        lesson = {"revision": 0, "plan": [{"title": "Pulse", "duration": "5 min", "goal": "Keep time", "tips": []}],
                  "step": 0, "notebook": {"chords": ["Am"], "notation": "", "tabs": ""}}
        self.assertEqual(self.clients["M"].post(route + "/lesson", json=lesson).status_code, 200)
        for name in ["M", "A", "B"]:
            client = self.clients[name]
            meeting = client.get(route)
            self.assertEqual(meeting.status_code, 200, meeting.text)
            self.assertEqual(meeting.json()["artist_ids"], ["A", "B"])
            self.assertEqual({member["id"] for member in meeting.json()["members"]}, {"M", "A", "B"})
            self.assertEqual(client.get("/api/harness/sessions").json()["sessions"][0]["id"], meeting.json()["id"])
            self.assertEqual(client.get(route + "/lesson").json()["plan"][0]["title"], "Pulse")
            self.assertEqual(client.post(route + "/join").status_code, 200)
        for name in ["A", "B"]:
            self.assertEqual(self.clients[name].post(route + "/lesson", json={**lesson, "revision": 1}).status_code, 403)
        with sqlite3.connect(self.directory + "/service.sqlite3") as connection:
            self.assertEqual({row[0] for row in connection.execute("SELECT participant FROM session_presence")}, {"M", "A", "B"})

    def test_private_notes_and_index_are_owned_by_each_of_three_accounts(self):
        route = self.group()
        for name in ["M", "A", "B"]:
            response = self.clients[name].post(route + "/notes", json={"revision": 0, "text": name + " private"})
            self.assertEqual(response.status_code, 200, response.text)
        for name in ["M", "A", "B"]:
            client = self.clients[name]
            self.assertEqual(client.get(route + "/notes").json()["text"], name + " private")
            self.assertEqual(client.get(route).json()["private_notes"]["text"], name + " private")
            index = client.get("/api/harness/notes").json()["notes"]
            self.assertEqual(len(index), 1)
            self.assertEqual(index[0]["preview"], name + " private")
        for suffix in ["", "/notes", "/lesson", "/events", "/heart"]:
            self.assertEqual(self.clients["outside"].get(route + suffix).status_code, 404)
        self.assertEqual(self.clients["outside"].post(route + "/notes", json={"revision": 0, "text": "foreign"}).status_code, 404)
        self.assertEqual(self.clients["outside"].get("/api/harness/sessions").json()["sessions"], [])

    def test_session_list_rejects_a_cookie_that_no_longer_matches_the_tab(self):
        response = self.create(kind="individual", artist_id="A", artist_ids=None)
        self.assertEqual(response.status_code, 201, response.text)
        self.clients["A"].headers["X-SOM-Participant"] = "B"
        response = self.clients["A"].get("/api/harness/sessions")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "participant_context_changed")

    def test_invalid_or_ambiguous_rosters_and_unknown_fields_are_rejected(self):
        for changes in [
            {"artist_ids": []}, {"artist_ids": ["A", "A"]}, {"artist_ids": ["A", "B", "outside"]},
            {"artist_ids": ["A", "missing"]}, {"artist_ids": ["A", "M"]},
            {"artist_ids": ["A", 2]}, {"artist_ids": [""]},
            {"artist_id": "A"}, {"kind": "individual"},
            {"kind": "individual", "artist_id": "A", "artist_ids": None, "owner": "B"},
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(self.create(**changes).status_code, 422)

    def test_artist_message_replays_are_independent_and_attributed_to_actual_accounts(self):
        route = self.group()
        self.assertEqual(self.clients["M"].post(route + "/start").status_code, 200)
        ids = []
        for name in ["A", "B"]:
            body = {"client_event_id": "same-event", "speaker": "artist", "text": "I play " + name + ".",
                    "source_lang": "en", "target_lang": "vi"}
            response = self.clients[name].post(route + "/messages", json=body)
            self.assertEqual(response.status_code, 201, response.text)
            message = response.json()
            ids.append(message["id"])
            self.assertEqual(message["participant_id"], name)
            self.assertEqual(message["participant_name"], "Artist " + name)
            replay = self.clients[name].post(route + "/messages", json=body)
            self.assertEqual(replay.json()["id"], message["id"])
        self.assertNotEqual(ids[0], ids[1])
        deliveries = self.clients["M"].get(route).json()["deliveries"]
        self.assertEqual({row["participant_id"] for row in deliveries}, {"A", "B"})
        self.assertEqual(self.clients["B"].post(route + "/messages", json={**body, "participant_id": "A"}).status_code, 422)

    def test_legacy_individual_membership_survives_upgrade_and_restart(self):
        response = self.create(kind="individual", artist_id="A", artist_ids=None)
        self.assertEqual(response.status_code, 201, response.text)
        route = "/api/harness/sessions/" + response.json()["id"]
        self.build()
        meeting = self.clients["A"].get(route)
        self.assertEqual(meeting.status_code, 200)
        self.assertIn("artist_ids", meeting.json())
        self.assertEqual(meeting.json()["artist_ids"], ["A"])
        self.assertEqual(self.clients["B"].get(route).status_code, 404)


if __name__ == "__main__":
    unittest.main()
