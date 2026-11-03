import base64
import io
import unittest
import wave
import threading
from pathlib import Path

from service.tests import test_participants as participants
from service.app import PersistentBudgetGuard, PersistenceError
from harness.budget import BudgetGuard


class VoiceService(unittest.TestCase):
    def setUp(self):
        self.integration = participants.ParticipantIntegration("test_logout_revokes_cookie")
        participants.ParticipantIntegration.setUpClass()
        self.integration.setUp()
        self.addCleanup(self.integration.doCleanups)
        self.integration.active()
        self.client = self.integration.m
        self.path = self.integration.path + "/transcriptions"
        self.calls = []
        self.integration.adapter.asr_enabled = True
        self.integration.adapter.transcribe = self.transcribe
        audio = io.BytesIO()
        with wave.open(audio, "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(16000)
            recording.writeframes(b"\0\0" * 16000)
        self.body = {"client_event_id": "voice-1", "language": "en", "wav_base64": base64.b64encode(audio.getvalue()).decode()}

    def transcribe(self, path, **kwargs):
        with wave.open(path) as recording:
            self.assertEqual(recording.getframerate(), 16000)
        self.calls.append(1)
        self.assertIn("tempo", kwargs["keywords"])
        return {"text": "Play slowly."}

    def test_transcription_replay_is_one_call_and_never_auto_delivered(self):
        for _ in range(2):
            response = self.client.post(self.path, json=self.body)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["text"], "Play slowly.")
        self.assertEqual(self.calls, [1])
        self.assertEqual(self.integration.a.get(self.integration.path).json()["deliveries"], [])

    def test_scope_and_changed_replay(self):
        other = self.integration.login("other")
        self.assertEqual(other.post(self.path, json=self.body).status_code, 404)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.client.post(self.path, json=self.body).status_code, 200)
        altered = {**self.body, "language": "vi"}
        self.assertEqual(self.client.post(self.path, json=altered).status_code, 409)
        self.assertEqual(self.calls, [1])

    def test_disable_and_body_limit_prevent_calls(self):
        self.integration.adapter.asr_enabled = False
        self.assertEqual(self.client.post(self.path, json=self.body).status_code, 503)
        self.integration.adapter.asr_enabled = True
        self.assertEqual(self.client.post(self.path, content=b"x" * 1_000_001).status_code, 413)
        self.assertEqual(self.calls, [])

    def test_asr_persistence_failure_stops_before_model_call(self):
        cfg = Path(self.integration.directory.name) / "budget.yaml"
        cfg.write_text("total_usd: 0.05\nwarn_pct: 0.8\nhard_stop_pct: 0.95\nledger: asr.sqlite3\n")
        guard = BudgetGuard.initialize_ledger(str(cfg), str(cfg.parent / "asr.sqlite3"))
        def failed_commit():
            raise RuntimeError("disk commit failed")
        wrapped = PersistentBudgetGuard(guard, failed_commit)
        with self.assertRaises(PersistenceError):
            wrapped.reserve_asr_seconds("muse-voice-transcribe-1.0", 10)
        self.assertEqual(guard.status()["holds"], 1)

    def test_completion_waits_for_transcription(self):
        entered, release = threading.Event(), threading.Event()
        result = []
        def blocking_transcribe(path, **kwargs):
            entered.set()
            release.wait(5)
            return {"text": "Play slowly."}
        self.integration.adapter.transcribe = blocking_transcribe
        worker = threading.Thread(target=lambda: result.append(self.client.post(self.path, json=self.body)))
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            self.assertEqual(self.client.post(self.integration.path + "/complete").status_code, 409)
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result[0].status_code, 200)
