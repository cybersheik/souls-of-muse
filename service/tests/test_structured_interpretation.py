"""Canonical translation plus source-grounded lesson-card HTTP regressions."""
import copy
import json
import sqlite3
import threading
import unittest

from service.tests import test_participants as participants
from service.tests.interpretation_fixtures import interpretation_text

SOURCE = "In bar 3, the A minor chord was late. Change on the beat. Try it 4 times."
TRANSLATION = "Trong ô nhịp 3, hợp âm La thứ bị chậm. Đổi đúng phách. Thử 4 lần."
NOTE = {
    "heard": {"source": "In bar 3, the A minor chord was late.", "translation": "Trong ô nhịp 3, hợp âm La thứ bị chậm."},
    "where": {
        "measure": {"source": "bar 3", "translation": "ô nhịp 3"},
        "note": {"source": "A minor", "translation": "La thứ"}},
    "change": {"source": "Change on the beat", "translation": "Đổi đúng phách"},
    "try": {"source": "Try it 4 times", "translation": "Thử 4 lần"},
}
DISPLAY = {"heard": "Trong ô nhịp 3, hợp âm La thứ bị chậm.", "where": {"measure": "ô nhịp 3", "note": "La thứ"},
           "change": "Đổi đúng phách", "try": "Thử 4 lần"}


class StructuredInterpretation(unittest.TestCase):
    def setUp(self):
        participants.ParticipantIntegration.setUpClass()
        self.p = participants.ParticipantIntegration("test_logout_revokes_cookie")
        self.p.setUp(); self.addCleanup(self.p.doCleanups)
        self.p.active(); self.path = self.p.path + "/messages"
        self.body = {"client_event_id": "structured-1", "speaker": "maestro", "text": SOURCE,
                     "source_lang": "en", "target_lang": "vi"}
        self.raw = interpretation_text(TRANSLATION, NOTE)
        self.calls = []
        def complete(role, system, user):
            self.calls.append(role)
            if role == "reviewer":
                return {"text": '{"verdict":"uncertain","reason":"Explicit offline review fixture."}'}
            return {"text": self.raw}
        self.p.adapter.complete = complete

    def test_grounded_note_is_persisted_private_until_approval_and_never_reinferred(self):
        message = self.p.m.post(self.path, json=self.body).json()
        self.assertEqual(message["text"], TRANSLATION)
        self.assertEqual(message["lesson_note"], DISPLAY)
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])
        replay = self.p.m.post(self.path, json=self.body).json()
        self.assertEqual(replay, message)
        calls = list(self.calls)
        self.p.build(); self.p.m, self.p.a = self.p.login("M"), self.p.login("A")
        stored = self.p.m.get(self.p.path).json()["deliveries"][0]
        self.assertEqual(stored["lesson_note"], DISPLAY)
        self.assertEqual(self.calls, calls)
        response = self.p.m.post(self.path + "/" + message["id"] + "/approve", json={"confirm_flagged": True})
        self.assertEqual(response.status_code, 200, response.text)
        received = self.p.a.get(self.p.path).json()["deliveries"][0]
        self.assertEqual(received["lesson_note"], DISPLAY)
        self.assertNotIn("source", json.dumps(received["lesson_note"]))
        self.assertNotIn("source_text", received)
        self.assertNotIn("the A minor chord was late", json.dumps(received))

    def test_unquoted_observation_or_invented_target_is_never_deliverable(self):
        for index, (field, value) in enumerate([("source", "The student played perfectly"),
                                               ("translation", "Người học chơi hoàn hảo")]):
            note = copy.deepcopy(NOTE); note["heard"][field] = value
            self.raw = interpretation_text(TRANSLATION, note)
            body = {**self.body, "client_event_id": "invented-" + str(index)}
            response = self.p.m.post(self.path, json=body)
            self.assertEqual(response.status_code, 502, response.text)
            self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])
            before = len(self.calls); self.p.m.post(self.path, json=body)
            self.assertEqual(len(self.calls), before)

    def test_plain_text_missing_fields_and_duplicate_keys_are_rejected(self):
        for index, raw in enumerate([TRANSLATION, '{"translation":"Hi"}',
            '{"translation":"Hi","translation":"Bye","lesson_note":null}',
            interpretation_text(TRANSLATION, {**NOTE, "invented_advice": "Practice more"})]):
            self.raw = raw
            response = self.p.m.post(self.path, json={**self.body, "client_event_id": "bad-shape-" + str(index)})
            self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])

    def test_instructions_can_have_no_reported_observation(self):
        self.body["text"] = "Play slowly."
        self.raw = interpretation_text("Chơi chậm.")
        message = self.p.m.post(self.path, json=self.body).json()
        self.assertEqual(message["text"], "Chơi chậm.")
        self.assertEqual(message["lesson_note"], {"heard": None, "where": {"measure": None, "note": None}, "change": None, "try": None})
        self.assertEqual(self.calls, ["interpreter"])

    def test_existing_literal_target_quote_with_wrong_source_mapping_triggers_review(self):
        source = "Play A minor then E minor."
        translated = "Chơi La thứ rồi Mi thứ."
        note = {"heard": None, "where": {"measure": None, "note": {"source": "A minor", "translation": "Mi thứ"}}, "change": None, "try": None}
        self.raw = interpretation_text(translated, note)
        message = self.p.m.post(self.path, json={**self.body, "text": source}).json()
        self.assertEqual(message["state"], "flagged")
        self.assertTrue(any("lesson_note.where.note" in issue for issue in message["validation_issues"]))
        self.assertEqual(self.calls, ["interpreter", "reviewer"])

    def test_bare_pitch_quotes_are_checked_in_note_field_context(self):
        source = "Play note F sharp and note G sharp."
        target = "Chơi nốt nhạc Fa thăng và nốt nhạc Sol thăng."
        note = {"heard": None, "where": {"measure": None, "note": {"source": "F sharp", "translation": "Sol thăng"}}, "change": None, "try": None}
        self.raw = interpretation_text(target, note)
        message = self.p.m.post(self.path, json={**self.body, "text": source}).json()
        self.assertEqual(message["state"], "flagged")
        self.assertTrue(any("lesson_note.where.note" in issue for issue in message["validation_issues"]))
        self.assertEqual(self.calls, ["interpreter", "reviewer"])
        self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve", json={}).status_code, 409)

    def test_extracted_action_cannot_strip_its_governing_negation(self):
        source = "Do not repeat the measure."
        target = "Đừng lặp lại ô nhịp."
        note = {"heard": None, "where": {"measure": None, "note": None},
                "change": {"source": "repeat the measure", "translation": "lặp lại ô nhịp"}, "try": None}
        self.raw = interpretation_text(target, note)
        response = self.p.m.post(self.path, json={**self.body, "text": source})
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])

    def test_reported_observation_grouping_requires_review_even_with_literal_quotes(self):
        source = "Play slowly."
        note = {"heard": {"source": source, "translation": "Chơi chậm."},
                "where": {"measure": None, "note": None}, "change": None, "try": None}
        self.raw = interpretation_text("Chơi chậm.", note)
        message = self.p.m.post(self.path, json={**self.body, "text": source}).json()
        self.assertEqual(message["state"], "flagged")
        self.assertEqual(self.calls, ["interpreter", "reviewer"])
        self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve", json={}).status_code, 409)

    def test_complete_action_sentence_still_requires_full_context_review(self):
        source = "Do not do the following. Repeat the measure."
        target = "Đừng làm việc sau đây. Lặp lại ô nhịp."
        note = {"heard": None, "where": {"measure": None, "note": None},
                "change": {"source": "Repeat the measure.", "translation": "Lặp lại ô nhịp."}, "try": None}
        self.raw = interpretation_text(target, note)
        message = self.p.m.post(self.path, json={**self.body, "text": source}).json()
        self.assertEqual(message["state"], "flagged")
        self.assertEqual(self.calls, ["interpreter", "reviewer"])
        self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve", json={}).status_code, 409)

    def test_octaves_and_pitch_lists_cannot_hide_a_wrong_note_mapping(self):
        cases = [
            ("Play note C4 and note E4.", "Chơi nốt nhạc Đô4 và nốt nhạc Mi4.", "C4", "Mi4"),
            ("Play note F sharp and G sharp. Then play note F sharp and A sharp.",
             "Chơi nốt nhạc Fa thăng và Sol thăng. Sau đó chơi nốt nhạc Fa thăng và La thăng.",
             "F sharp and G sharp", "Fa thăng và La thăng"),
            ("Compare A minor and E major with A major and E minor.",
             "So sánh La thứ và Mi trưởng với La trưởng và Mi thứ.",
             "A minor and E major", "La trưởng và Mi thứ"),
        ]
        for index, (source, target, source_quote, target_quote) in enumerate(cases):
            with self.subTest(index=index):
                note = {"heard": None, "where": {"measure": None, "note": {"source": source_quote, "translation": target_quote}}, "change": None, "try": None}
                self.raw = interpretation_text(target, note)
                message = self.p.m.post(self.path, json={**self.body, "text": source, "client_event_id": "pitch-list-" + str(index)}).json()
                self.assertEqual(message["state"], "flagged")
                self.assertTrue(any("lesson_note.where.note" in issue for issue in message["validation_issues"]))
                self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve", json={}).status_code, 409)

    def test_unsupported_note_notation_requires_review_instead_of_empty_equality(self):
        note = {"heard": None, "where": {"measure": None, "note": {"source": "Am7", "translation": "Am7"}}, "change": None, "try": None}
        self.raw = interpretation_text("Chơi Am7.", note)
        message = self.p.m.post(self.path, json={**self.body, "text": "Play Am7."}).json()
        self.assertEqual(message["state"], "flagged")
        self.assertEqual(self.calls, ["interpreter", "reviewer"])
        self.assertEqual(self.p.m.post(self.path + "/" + message["id"] + "/approve", json={}).status_code, 409)

    def _install_writer(self, callback):
        from fastapi import FastAPI
        from service.app import create_app
        app = create_app(data_dir=self.p.directory.name, adapter=self.p.adapter, environ=self.p.env,
                         heart_key=self.p.key, on_write=callback)
        self.p.site = FastAPI(); self.p.site.mount("/api/harness", app)
        self.p.m, self.p.a = self.p.login("M"), self.p.login("A")

    def test_failed_note_commit_closes_reads_and_replay_until_restart(self):
        def failed_write():
            with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
                if c.execute("SELECT COUNT(*) FROM message_notes").fetchone()[0]:
                    raise RuntimeError("simulated volume commit failure")
        self._install_writer(failed_write)
        response = self.p.m.post(self.path, json=self.body)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.calls, ["interpreter", "reviewer"])
        self.assertEqual(self.p.m.post(self.path, json=self.body).status_code, 503)
        self.assertEqual(self.p.a.get(self.p.path).status_code, 503)
        self.assertFalse(self.p.m.get("/api/harness/health").json()["pilot_ready"])
        self.assertEqual(self.calls, ["interpreter", "reviewer"])

    def test_failed_approval_commit_cannot_leak_an_unconfirmed_local_transition(self):
        failure = {"enabled": False}
        def write():
            if failure["enabled"]:
                raise RuntimeError("simulated volume commit failure")
        self._install_writer(write)
        message = self.p.m.post(self.path, json=self.body).json()
        failure["enabled"] = True
        response = self.p.m.post(self.path + "/" + message["id"] + "/approve", json={"confirm_flagged": True})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.p.a.get(self.p.path).status_code, 503)
        self.assertFalse(self.p.m.get("/api/harness/health").json()["pilot_ready"])

    def test_read_waits_for_inflight_volume_commit_before_showing_approval(self):
        entered, release, read_done = threading.Event(), threading.Event(), threading.Event()
        state = {"block": False}
        def write():
            if state["block"]:
                entered.set(); release.wait(5)
                raise RuntimeError("simulated failed pending commit")
        self._install_writer(write)
        message = self.p.m.post(self.path, json=self.body).json()
        state["block"] = True
        results = {}
        approve = threading.Thread(target=lambda: results.update(approval=self.p.m.post(
            self.path + "/" + message["id"] + "/approve", json={"confirm_flagged": True})))
        def read():
            results["read"] = self.p.a.get(self.p.path); read_done.set()
        reader = threading.Thread(target=read)
        approve.start()
        try:
            self.assertTrue(entered.wait(3))
            reader.start()
            self.assertFalse(read_done.wait(.2), "Unconfirmed local approval escaped during Volume.commit")
        finally:
            release.set(); approve.join(5)
            if reader.ident is not None: reader.join(5)
        self.assertEqual(results["approval"].status_code, 503)
        self.assertEqual(results["read"].status_code, 503)

    def test_corrupt_persisted_note_cannot_be_approved(self):
        message = self.p.m.post(self.path, json=self.body).json()
        self.assertIn("lesson_note", message)
        invalid = copy.deepcopy(NOTE); invalid["heard"]["source"] = "Invented performance"
        with sqlite3.connect(self.p.directory.name + "/service.sqlite3") as c:
            c.execute("UPDATE message_notes SET content=?", (json.dumps(invalid),))
        response = self.p.m.post(self.path + "/" + message["id"] + "/approve", json={"confirm_flagged": True})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"], [])
