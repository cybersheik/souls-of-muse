import json
import tempfile
import unittest
import wave
from pathlib import Path

import httpx

from harness.adapters.meta import MetaAdapter, MetaResponseError, MetaTransportError
from harness.budget import BudgetExceeded, BudgetGuard
from test_budget_safety import FAKE_ENV, models_cfg, write_config


class VoiceContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cfg = write_config(self.directory.name, total=0.05)
        self.guard = BudgetGuard.initialize_ledger(str(self.cfg))
        self.wav = Path(self.directory.name) / "recording.wav"
        with wave.open(str(self.wav), "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(16000)
            recording.writeframes(b"\0\0" * 16000)
        self.models = models_cfg()
        self.models["roles"]["asr"]["enabled"] = True

    def adapter(self, handler):
        return MetaAdapter(self.models, self.guard, transport=httpx.MockTransport(handler), environ=FAKE_ENV)

    def response(self, **changes):
        body = {"sessionId": "voice-1", "transcript": "Play slowly.", "audioDurationMs": 1000, "turns": []}
        body.update(changes)
        return httpx.Response(200, json=body)

    def test_multipart_has_durable_hold_before_http_and_second_based_settlement(self):
        def handler(request):
            self.assertEqual(self.guard.status()["holds"], 1)
            self.assertEqual(request.url.path, "/v1/asr/transcribe")
            self.assertTrue(request.headers["content-type"].startswith("multipart/form-data; boundary="))
            self.assertIn(b'"audioEncoding": "WAV"', request.content)
            return self.response()
        result = self.adapter(handler).transcribe(self.wav, language_bias=["English"])
        self.assertEqual(result["text"], "Play slowly.")
        self.assertAlmostEqual(result["cost_usd"], 0.00005)
        self.assertEqual(self.guard.status()["held_usd"], 0)
        self.guard.settle_asr_seconds(result["reservation_id"], "muse-voice-transcribe-1.0", 1)
        self.assertEqual(self.guard.status()["calls"], 1)

    def test_missing_duration_retains_hold(self):
        with self.assertRaises(MetaResponseError):
            self.adapter(lambda _: self.response(audioDurationMs=None)).transcribe(self.wav)
        self.assertEqual(self.guard.status()["holds"], 1)

    def test_network_failure_retains_hold_without_retry(self):
        calls = []
        def handler(request):
            calls.append(1)
            raise httpx.ReadTimeout("private upstream detail", request=request)
        with self.assertRaises(MetaTransportError):
            self.adapter(handler).transcribe(self.wav)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.guard.status()["holds"], 1)

    def test_processed_duration_above_reservation_blocks(self):
        with self.assertRaises(BudgetExceeded):
            self.adapter(lambda _: self.response(audioDurationMs=61000)).transcribe(self.wav)
        self.assertEqual(self.guard.status()["blocked_calls"], 1)

    def test_subsecond_audio_rounds_down_as_documented(self):
        result = self.adapter(lambda _: self.response(audioDurationMs=800)).transcribe(self.wav)
        self.assertEqual(result["cost_usd"], 0)
        self.assertEqual(self.guard.status()["holds"], 0)
