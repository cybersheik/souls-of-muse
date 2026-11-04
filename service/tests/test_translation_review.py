"""Offline HTTP regressions for the mandatory flagged-translation review gate."""
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch

from service.tests import test_participants as participants
from service.tests.interpretation_fixtures import interpretation_text

SOURCE = "Play note F-sharp and note G sharp."
WRONG = "Chơi nốt nhạc Fa và nốt nhạc Sol thăng."
VERDICT = {"verdict": "unfaithful", "reason": "The first sharp has been lost."}


class ReviewAdapter:
    asr_enabled = False

    def __init__(self, directory, *, draft=WRONG, review=None):
        self.directory = directory
        self.draft = draft
        self.review = json.dumps(VERDICT) if review is None else review
        self.roles = []
        self.entered = self.release = None

    def complete(self, role, system, user):
        self.roles.append(role)
        if role == "interpreter":
            return {"text": interpretation_text(self.draft)}
        if role != "reviewer":
            raise AssertionError("Unexpected model role")
        with sqlite3.connect(self.directory + "/service.sqlite3") as c:
            row = c.execute("SELECT state FROM message_reviews WHERE state='processing'").fetchone()
            if row != ("processing",):
                raise AssertionError("Review was not persisted before inference")
        payload = json.loads(user)
        if payload["source_text"] != SOURCE or payload["translation"] != self.draft:
            raise AssertionError("Reviewer did not receive the canonical source and draft")
        if not payload["validation_issues"]:
            raise AssertionError("Reviewer invoked without a deterministic flag")
        if self.entered:
            self.entered.set()
            self.release.wait(5)
        if isinstance(self.review, Exception):
            raise self.review
        return {"text": self.review}


class TranslationReview(unittest.TestCase):
    def setUp(self):
        participants.ParticipantIntegration.setUpClass()
        self.p = participants.ParticipantIntegration("test_logout_revokes_cookie")
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.adapter = ReviewAdapter(self.p.directory.name)
        self.p.adapter = self.adapter
        self.p.build()
        self.p.m, self.p.a = self.p.login("M"), self.p.login("A")
        self.p.active()
        self.path = self.p.path + "/messages"
        self.body = {"client_event_id": "review-1", "speaker": "maestro", "text": SOURCE,
                     "source_lang": "en", "target_lang": "vi"}

    def test_flagged_review_is_durable_idempotent_and_keeps_maestro_authority(self):
        response = self.p.m.post(self.path, json=self.body)
        self.assertEqual(response.status_code, 201, response.text)
        message = response.json()
        self.assertEqual(message["state"], "flagged")
        self.assertEqual(message["text"], WRONG)
        self.assertIn("review", message)
        self.assertEqual(message["review"], {"state": "complete", **VERDICT})
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer"])
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])
        replay = self.p.m.post(self.path, json=self.body)
        self.assertEqual(replay.json(), message)
        self.p.build()
        self.p.m, self.p.a = self.p.login("M"), self.p.login("A")
        self.assertEqual(self.p.m.get(self.p.path).json()["deliveries"][0]["review"], message["review"])
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer"])
        approval = self.path + "/" + message["id"] + "/approve"
        self.assertEqual(self.p.m.post(approval, json={}).status_code, 409)
        self.assertEqual(self.p.a.post(approval, json={"confirm_flagged": True}).status_code, 403)
        self.assertEqual(self.p.m.post(approval, json={"confirm_flagged": True}).status_code, 200)
        received = self.p.a.get(self.p.path).json()["deliveries"][0]
        self.assertEqual(received["text"], WRONG)
        self.assertNotIn("review", received)

    def test_artist_replaying_own_approved_message_cannot_read_private_review(self):
        def model(role, system, user):
            self.adapter.roles.append(role)
            return {"text": interpretation_text("Play note F and note G sharp.") if role == "interpreter" else json.dumps(VERDICT)}
        self.adapter.complete = model
        body = {**self.body, "speaker": "artist", "text": "Chơi nốt nhạc Fa thăng và nốt nhạc Sol thăng.",
                "source_lang": "vi", "target_lang": "en"}
        created = self.p.a.post(self.path, json=body).json()
        self.assertNotIn("review", created)
        self.assertEqual(self.p.m.post(self.path + "/" + created["id"] + "/approve",
            json={"confirm_flagged": True}).status_code, 200)
        replay = self.p.a.post(self.path, json=body).json()
        self.assertEqual(replay["state"], "approved")
        self.assertNotIn("review", replay)
        self.assertNotIn("source_text", replay)
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer"])

    def test_clean_translation_does_not_call_reviewer_or_auto_deliver(self):
        self.body["text"] = "Play slowly."
        self.adapter.draft = "Chơi chậm."
        message = self.p.m.post(self.path, json=self.body).json()
        self.assertEqual(message["state"], "draft")
        self.assertTrue(message.get("approval_allowed", False))
        self.assertEqual(self.adapter.roles, ["interpreter"])
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])

    def test_faithful_vietnamese_ordinal_does_not_trigger_paid_review(self):
        self.body["text"] = "Play the second measure slowly."
        self.adapter.draft = "Hãy chơi ô nhịp thứ hai thật chậm."
        response = self.p.m.post(self.path, json=self.body)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["state"], "draft")
        self.assertEqual(response.json()["validation_issues"], [])
        self.assertNotIn("review", response.json())
        self.assertEqual(self.adapter.roles, ["interpreter"])
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])

    def test_failed_or_malformed_review_cannot_be_overridden_or_retried_by_replay(self):
        for index, result in enumerate([RuntimeError("upstream private detail"), "not JSON",
                '{"verdict":"faithful","reason":"","extra":true}',
                '{"verdict":"faithful","reason":"ok","extra":true}',
                '{"verdict":"approve","reason":"ok"}',
                '{"verdict":"faithful","reason":true}',
                '{"verdict":"unfaithful","verdict":"faithful","reason":"ok"}']):
            with self.subTest(index=index):
                self.adapter.review = result
                self.body["client_event_id"] = f"bad-review-{index}"
                message = self.p.m.post(self.path, json=self.body).json()
                self.assertEqual(message.get("review"), {"state": "failed"})
                self.assertFalse(message["approval_allowed"])
                self.assertNotIn("private detail", json.dumps(message))
                self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve",
                    json={"confirm_flagged": True}).status_code, 409)
                calls = len(self.adapter.roles)
                self.p.m.post(self.path, json=self.body)
                self.assertEqual(len(self.adapter.roles), calls)
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])

    def test_validator_exception_is_not_a_clean_draft(self):
        with patch("harness.validator.signature", side_effect=RuntimeError("private glossary path")):
            response = self.p.m.post(self.path, json=self.body)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["detail"], "validation_unavailable")
        self.assertEqual(self.adapter.roles, ["interpreter"])
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])
        self.assertNotIn("private glossary", response.text)

    def test_missing_glossary_prevents_any_paid_inference(self):
        with patch("service.app._load_glossary", return_value=[]):
            self.p.build()
        self.p.m = self.p.login("M")
        response = self.p.m.post(self.path, json=self.body)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["detail"], "validation_unavailable")
        self.assertEqual(self.adapter.roles, [])
        self.assertFalse(self.p.m.get("/api/harness/health").json()["pilot_ready"])

    def test_completion_and_duplicate_wait_for_review(self):
        self.adapter.entered, self.adapter.release = threading.Event(), threading.Event()
        responses = []
        worker = threading.Thread(target=lambda: responses.append(self.p.m.post(self.path, json=self.body)))
        worker.start()
        try:
            self.assertTrue(self.adapter.entered.wait(3))
            self.assertEqual(self.p.m.post(self.path, json=self.body).status_code, 409)
            self.assertEqual(self.p.m.post(self.p.path + "/complete").status_code, 409)
            self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])
        finally:
            self.adapter.release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(responses[0].status_code, 201)
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer"])

    def test_existing_draft_cannot_bypass_a_missing_validator_at_approval(self):
        self.body["text"] = "Play slowly."
        self.adapter.draft = "Chơi chậm."
        message = self.p.m.post(self.path, json=self.body).json()
        with patch("service.app._load_glossary", return_value=[]):
            self.p.build()
        self.p.m = self.p.login("M")
        response = self.p.m.post(self.path + "/" + message["id"] + "/approve", json={})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.adapter.roles, ["interpreter"])
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])

    def test_legacy_clean_draft_with_newly_detected_error_is_blocked(self):
        message = self.p.m.post(self.path, json=self.body).json()
        with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
            c.execute("UPDATE messages SET state='draft',validation_issues='[]'")
            c.execute("DELETE FROM message_reviews")
        response = self.p.m.post(self.path + "/" + message["id"] + "/approve", json={})
        self.assertEqual(response.status_code, 409)
        stored = self.p.m.get(self.p.path).json()["deliveries"][0]
        self.assertEqual(stored["state"], "flagged")
        self.assertFalse(stored["approval_allowed"])
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer"])
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])

    def test_review_persistence_failure_stops_before_second_inference(self):
        from fastapi import FastAPI
        from service.app import create_app
        def fail_review_commit():
            with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
                pending = c.execute("SELECT COUNT(*) FROM message_reviews WHERE state='processing'").fetchone()[0]
            if pending:
                raise RuntimeError("simulated Volume.commit failure")
        app = create_app(data_dir=self.p.directory.name, adapter=self.adapter, environ=self.p.env,
                         heart_key=self.p.key, on_write=fail_review_commit)
        self.p.site = FastAPI()
        self.p.site.mount("/api/harness", app)
        self.p.m = self.p.login("M")
        response = self.p.m.post(self.path, json=self.body)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(self.adapter.roles, ["interpreter"])
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])

    def test_real_adapter_review_failure_retains_budget_hold_without_replay(self):
        from pathlib import Path
        import httpx
        from fastapi import FastAPI
        from service.app import create_app, _build_real_adapter
        from harness.budget import BudgetGuard
        directory = Path(self.p.directory.name)
        config = directory / "budget.yaml"
        ledger = directory / "budget_ledger.sqlite3"
        config.write_text("total_usd: 0.05\nwarn_pct: 0.8\nhard_stop_pct: 0.95\nledger: budget_ledger.sqlite3\n")
        guard = BudgetGuard.initialize_ledger(str(config), str(ledger))
        calls = []
        recovered = [False]
        def handler(request):
            payload = json.loads(request.content)
            calls.append(payload)
            self.assertEqual(guard.status()["holds"], 2 if recovered[0] else 1)
            if len(calls) == 1:
                self.assertEqual(payload["response_format"]["json_schema"]["name"], "music_interpretation")
                return httpx.Response(200, json={"choices": [{"message": {"content": interpretation_text(WRONG)}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10}})
            self.assertEqual(payload["model"], "muse-spark-1.3")
            self.assertEqual(payload["max_tokens"], 512)
            self.assertEqual(payload["response_format"]["json_schema"]["name"], "translation_review")
            with sqlite3.connect(directory / "service.sqlite3") as c:
                self.assertEqual(c.execute("SELECT state FROM message_reviews").fetchone()[0], "processing")
            if recovered[0]:
                return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(VERDICT)}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10}})
            return httpx.Response(503, text="private upstream failure")
        adapter, ready = _build_real_adapter(str(directory), {"MODEL_API_KEY": "explicit-offline-fixture"},
                                             transport=httpx.MockTransport(handler))
        self.assertTrue(ready)
        self.addCleanup(adapter.http.close)
        app = create_app(data_dir=str(directory), adapter=adapter, environ=self.p.env, heart_key=self.p.key)
        self.p.site = FastAPI()
        self.p.site.mount("/api/harness", app)
        self.p.m = self.p.login("M")
        message = self.p.m.post(self.path, json=self.body).json()
        self.assertEqual(message["review"], {"state": "failed"})
        self.assertEqual(len(calls), 2)
        self.assertEqual(guard.status()["holds"], 1)
        self.p.m.post(self.path, json=self.body)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve",
            json={"confirm_flagged": True}).status_code, 409)
        self.assertEqual(guard.status()["holds"], 1)

        # Explicit retry uses the same real guarded adapter, retains the old
        # unknown-usage HOLD and settles only its new reviewer reservation.
        recovered[0] = True
        route = self.path + "/" + message["id"] + "/review"
        retried = self.p.m.post(route, json={"client_event_id": "recovered-review"})
        self.assertEqual(retried.status_code, 200, retried.text)
        self.assertEqual(retried.json()["review"]["state"], "complete")
        self.assertEqual(len(calls), 3)
        self.assertEqual(guard.status()["holds"], 1)
        self.assertEqual((guard.total_micro, guard.stop_micro), (50_000, 47_500))
        self.assertEqual(self.p.m.post(route, json={"client_event_id": "recovered-review"}).status_code, 200)
        self.assertEqual(len(calls), 3)

    def test_interrupted_review_is_not_replayed_after_restart(self):
        message = self.p.m.post(self.path, json=self.body).json()
        self.assertIn("review", message)
        with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
            c.execute("UPDATE message_reviews SET state='processing',verdict=NULL,reason=NULL")
            c.execute("UPDATE messages SET state='processing'")
        self.p.build()
        self.p.m = self.p.login("M")
        replay = self.p.m.post(self.path, json=self.body)
        self.assertEqual(replay.status_code, 502)
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer"])
        self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve",
            json={"confirm_flagged": True}).status_code, 409)

    def test_old_flagged_message_without_review_cannot_be_approved(self):
        message = self.p.m.post(self.path, json=self.body).json()
        self.assertIn("review", message)
        with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
            c.execute("DELETE FROM message_reviews")
        self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve",
            json={"confirm_flagged": True}).status_code, 409)

    def failed_review(self):
        self.adapter.review = RuntimeError("temporary private provider error")
        message = self.p.m.post(self.path, json=self.body).json()
        self.assertEqual(message["review"], {"state": "failed"})
        self.adapter.review = json.dumps(VERDICT)
        return message, self.path + "/" + message["id"] + "/review"

    def test_explicit_review_retry_reuses_canonical_translation_and_never_delivers(self):
        original, route = self.failed_review()
        result = self.p.m.post(route, json={"client_event_id": "retry-1"})
        self.assertEqual(result.status_code, 200, result.text)
        retried = result.json()
        self.assertEqual(retried["text"], original["text"])
        self.assertEqual(retried["review"], {"state": "complete", **VERDICT, "retry_event_id": "retry-1"})
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer", "reviewer"])
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])
        for event in ["retry-1", "another-id-after-success"]:
            self.assertEqual(self.p.m.post(route, json={"client_event_id": event}).json(), retried)
        self.assertEqual(len(self.adapter.roles), 3)
        self.assertEqual(self.p.m.post(route.replace("/review", "/approve"), json={}).status_code, 409)
        self.assertEqual(self.p.m.post(route.replace("/review", "/approve"),
            json={"confirm_flagged": True}).status_code, 200)
        self.assertNotIn("review", self.p.a.get(self.p.path).json()["deliveries"][0])

    def test_failed_retry_replay_and_restart_do_not_make_another_paid_attempt(self):
        _, route = self.failed_review()
        self.adapter.review = RuntimeError("private exception")
        body = {"client_event_id": "failed-retry"}
        result = self.p.m.post(route, json=body)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["review"], {"state": "failed", "retry_event_id": "failed-retry"})
        self.assertNotIn("private exception", result.text)
        self.p.build(); self.p.m = self.p.login("M")
        self.adapter.review = json.dumps(VERDICT)
        self.assertEqual(self.p.m.post(route, json=body).json()["review"]["state"], "failed")
        self.assertEqual(len(self.adapter.roles), 3)
        self.assertEqual(self.p.m.post(route, json={"client_event_id": "deliberate-new-retry"}).json()["review"]["state"], "complete")
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer", "reviewer", "reviewer"])

    def test_processing_retry_blocks_duplicate_approval_and_meeting_completion(self):
        _, route = self.failed_review()
        self.adapter.entered, self.adapter.release = threading.Event(), threading.Event()
        result = []
        thread = threading.Thread(target=lambda: result.append(self.p.m.post(route,
            json={"client_event_id": "in-flight"})))
        thread.start()
        try:
            self.assertTrue(self.adapter.entered.wait(3))
            for event in ["in-flight", "different-click"]:
                self.assertEqual(self.p.m.post(route, json={"client_event_id": event}).status_code, 409)
            self.assertEqual(self.p.m.post(self.p.path + "/complete").status_code, 409)
            self.assertEqual(self.p.m.post(route.replace("/review", "/approve"),
                json={"confirm_flagged": True}).status_code, 409)
        finally:
            self.adapter.release.set(); thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result[0].status_code, 200, result[0].text)
        self.assertEqual(len(self.adapter.roles), 3)

    def test_review_retry_requires_maestro_membership_and_valid_explicit_intent(self):
        _, route = self.failed_review()
        body = {"client_event_id": "one"}
        self.assertEqual(self.p.a.post(route, json=body).status_code, 403)
        other = self.p.login("other")
        self.assertEqual(other.post(route, json=body).status_code, 403)
        accounts = json.loads(self.p.env["SOM_WEB_ACCOUNTS"])
        accounts["foreignMaestro"] = dict(accounts["M"])
        self.p.env["SOM_WEB_ACCOUNTS"] = json.dumps(accounts)
        self.p.build(); self.p.m = self.p.login("M")
        self.assertEqual(self.p.login("foreignMaestro").post(route, json=body).status_code, 404)
        for invalid in [{}, {"client_event_id": ""}, {"client_event_id": "x", "translation": "replacement"}]:
            self.assertEqual(self.p.m.post(route, json=invalid).status_code, 422)
        missing = route.replace(route.split("/")[-2], "not-a-message")
        self.assertEqual(self.p.m.post(missing, json=body).status_code, 404)
        self.assertEqual(self.p.m.post(route, json=body, headers={"Origin": "https://bad.invalid"}).status_code, 403)
        self.assertEqual(len(self.adapter.roles), 2)
        self.assertEqual(self.p.m.post(self.p.path + "/complete").status_code, 200)
        self.assertEqual(self.p.m.post(route, json=body).status_code, 409)
        self.assertEqual(len(self.adapter.roles), 2)

    def test_missing_legacy_review_can_be_requested_without_retranslating(self):
        message = self.p.m.post(self.path, json=self.body).json()
        with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
            c.execute("DELETE FROM message_reviews")
        response = self.p.m.post(self.path + "/" + message["id"] + "/review",
            json={"client_event_id": "legacy"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["review"]["state"], "complete")
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer", "reviewer"])

    def test_interrupted_retry_requires_new_explicit_intent_after_restart(self):
        message, route = self.failed_review()
        self.p.m.post(route, json={"client_event_id": "interrupted"})
        with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
            c.execute("UPDATE message_review_retries SET state='processing'")
            c.execute("UPDATE message_reviews SET state='processing',verdict=NULL,reason=NULL")
        self.p.build(); self.p.m = self.p.login("M")
        replay = self.p.m.post(route, json={"client_event_id": "interrupted"})
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["review"]["state"], "failed")
        self.assertEqual(len(self.adapter.roles), 3)
        retried = self.p.m.post(route, json={"client_event_id": "after-restart"})
        self.assertEqual(retried.json()["review"]["state"], "complete")
        self.assertEqual(len(self.adapter.roles), 4)

    def test_retry_persistence_failure_prevents_the_reviewer_call(self):
        from service.app import create_app
        from fastapi import FastAPI
        _, route = self.failed_review()
        def fail_commit():
            with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
                if c.execute("SELECT COUNT(*) FROM message_review_retries WHERE state='processing'").fetchone()[0]:
                    raise RuntimeError("fixture persistence unavailable")
        app = create_app(data_dir=self.p.directory.name, adapter=self.adapter,
                         environ=self.p.env, heart_key=self.p.key, on_write=fail_commit)
        self.p.site = FastAPI(); self.p.site.mount("/api/harness", app)
        self.p.m = self.p.login("M")
        response = self.p.m.post(route, json={"client_event_id": "durable-first"})
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(len(self.adapter.roles), 2)
        self.assertFalse(self.p.m.get("/api/harness/health").json()["durability_ready"])

    def test_retry_revalidates_saved_content_before_any_new_model_call(self):
        message, route = self.failed_review()
        with patch("harness.validator.signature", side_effect=RuntimeError("private validator failure")):
            result = self.p.m.post(route, json={"client_event_id": "validator-unavailable"})
        self.assertEqual(result.status_code, 503, result.text)
        with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
            c.execute("UPDATE message_notes SET content='not-json' WHERE message_id=?", (message["id"],))
        self.assertEqual(self.p.m.post(route, json={"client_event_id": "corrupt-note"}).status_code, 409)
        self.assertEqual(self.adapter.roles, ["interpreter", "reviewer"])
