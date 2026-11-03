"""Participant integration regressions. The adapter is explicitly offline."""
import json
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.app import create_app
from service.identity import password_hash
from service.tests.test_service import FakeAdapter
from heart import verify


class ParticipantIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.accounts = {
            name: {"role": role, "password_hash": password_hash("private-test-password")}
            for name, role in [("M", "maestro"), ("A", "artist"), ("other", "artist")]
        }

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.key = Ed25519PrivateKey.generate()
        self.adapter = FakeAdapter()
        self.env = {"SOM_WEB_ACCOUNTS": json.dumps(self.accounts), "SOM_COOKIE_SECURE": "0"}
        self.build()
        self.m = self.login("M")
        self.a = self.login("A")

    def build(self, key=True):
        app = create_app(data_dir=self.directory.name, adapter=self.adapter,
                         environ=self.env, heart_key=self.key if key else None)
        self.site = FastAPI()
        self.site.mount("/api/harness", app)

    def login(self, name):
        client = TestClient(self.site, headers={"Origin": "http://testserver"})
        response = client.post("/api/harness/auth/login", json={"username": name, "password": "private-test-password"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertNotIn("password", response.text)
        return client

    def create(self):
        response = self.m.post("/api/harness/sessions", json={"kind": "individual", "league": "string",
            "maestro_alias": "Maestro", "artist_alias": "Artist", "artist_id": "A", "source_lang": "en", "target_lang": "vi"})
        self.assertEqual(response.status_code, 201, response.text)
        self.path = "/api/harness/sessions/" + response.json()["id"]
        return self.path

    def active(self):
        self.create()
        self.assertEqual(self.m.post(self.path + "/start").status_code, 200)
        for client in [self.m, self.a]:
            self.assertEqual(client.post(self.path + "/join").status_code, 200)

    def test_flow_role_gate_replay_and_restart(self):
        self.active()
        body = {"client_event_id": "stable-1", "speaker": "maestro", "text": "Play slowly.", "source_lang": "en", "target_lang": "vi"}
        response = self.m.post(self.path + "/messages", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        mid = response.json()["id"]
        self.assertEqual(self.a.get(self.path).json()["deliveries"], [])
        self.assertEqual(self.a.post(self.path + f"/messages/{mid}/approve", json={}).status_code, 403)
        self.assertEqual(self.m.post(self.path + f"/messages/{mid}/approve", json={}).status_code, 200)
        self.assertEqual(len(self.a.get(self.path).json()["deliveries"]), 1)
        self.m.post(self.path + "/messages", json=body)
        self.assertEqual(self.adapter.calls, 1)
        for _ in range(2):
            self.assertEqual(self.m.post(self.path + "/complete").status_code, 200)
        for client in [self.m, self.a]:
            heart = client.get(self.path + "/heart").json()
            self.assertEqual(heart["counters"]["happened"], 1)
            self.assertEqual([r["state"] for r in heart["delivery"]], ["delivered", "delivered"])
        pub = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        self.assertTrue(verify.verify(self.directory.name + "/heart.sqlite3", pub)[0])
        cookies = self.a.cookies
        self.build()
        restarted = TestClient(self.site, cookies=cookies)
        self.assertEqual(restarted.get(self.path).json()["state"], "completed")
        self.assertEqual(restarted.get(self.path + "/heart").json()["counters"]["happened"], 1)

    def test_other_participant_cannot_read_or_write_meeting(self):
        self.active()
        other = self.login("other")
        self.assertEqual(other.get("/api/harness/sessions").json()["sessions"], [])
        for suffix in ["", "/events", "/heart"]:
            self.assertEqual(other.get(self.path + suffix).status_code, 404)
        self.assertEqual(other.post(self.path + "/join").status_code, 404)

    def test_cookie_does_not_accept_cross_origin_writes(self):
        self.active()
        response = self.m.post(self.path + "/complete", headers={"Origin": "https://evil.invalid"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.m.get(self.path).json()["state"], "active")

    def test_no_credit_without_both_participants(self):
        self.create()
        self.m.post(self.path + "/start")
        self.m.post(self.path + "/join")
        self.m.post(self.path + "/complete")
        heart = self.m.get(self.path + "/heart").json()
        self.assertEqual(heart["counters"]["happened"], 0)
        self.assertEqual(heart["delivery"], [])

    def test_pending_delivery_recovers_when_key_is_available(self):
        self.build(key=False)
        self.m, self.a = self.login("M"), self.login("A")
        self.active()
        self.m.post(self.path + "/complete")
        self.assertEqual(self.m.get(self.path + "/heart").json()["delivery"][0]["state"], "pending")
        cookies = self.m.cookies
        self.build()
        recovered = TestClient(self.site, cookies=cookies)
        heart = recovered.get(self.path + "/heart").json()
        self.assertEqual(heart["counters"]["happened"], 1)
        self.assertTrue(all(r["state"] == "delivered" for r in heart["delivery"]))

    def test_lost_acknowledgment_replays_without_double_credit(self):
        self.active()
        self.m.post(self.path + "/complete")
        # The signed journal survived, but the delivery acknowledgment did not.
        with sqlite3.connect(self.directory.name + "/service.sqlite3") as c:
            c.execute("UPDATE heart_outbox SET state='pending'")
        cookies = self.m.cookies
        self.build()
        recovered = TestClient(self.site, cookies=cookies)
        heart = recovered.get(self.path + "/heart").json()
        self.assertEqual(heart["counters"]["happened"], 1)
        self.assertTrue(all(r["state"] == "delivered" for r in heart["delivery"]))

    def test_logout_revokes_cookie(self):
        self.create()
        cookie = self.m.cookies
        self.assertEqual(self.m.post("/api/harness/auth/logout").status_code, 200)
        replay = TestClient(self.site, cookies=cookie)
        self.assertEqual(replay.get("/api/harness/auth/me").status_code, 401)
