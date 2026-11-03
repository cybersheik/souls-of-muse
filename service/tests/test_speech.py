"""Speech must use approved canonical text and the same participant boundary."""
import base64
import io
import wave
import unittest

from fastapi import FastAPI
from service.app import create_app
from service.tests import test_participants as participants


class SpeechService(unittest.TestCase):
    def setUp(self):
        participants.ParticipantIntegration.setUpClass()
        self.meeting = participants.ParticipantIntegration("test_logout_revokes_cookie")
        self.meeting.setUp()
        self.addCleanup(self.meeting.doCleanups)
        self.calls = []
        audio = io.BytesIO()
        with wave.open(audio, "wb") as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(16000)
            out.writeframes(b"\1\0" * 1600)
        self.wav = audio.getvalue()
        test = self
        class Speech:
            revision = "offline-test-only"
            def synthesize(self, text, language):
                test.calls.append((text, language))
                return test.wav
        self.speech = Speech()
        self.build()
        self.meeting.m = self.meeting.login("M")
        self.meeting.a = self.meeting.login("A")
        self.meeting.active()
        self.client = self.meeting.a
        self.message = self.meeting.m.post(self.meeting.path + "/messages", json={
            "client_event_id": "speech-1", "speaker": "maestro", "text": "Play slowly.",
            "source_lang": "en", "target_lang": "vi"}).json()
        self.path = self.meeting.path + "/messages/" + self.message["id"] + "/speech"

    def build(self, enabled=True):
        app = create_app(data_dir=self.meeting.directory.name, adapter=self.meeting.adapter,
                         environ=self.meeting.env, heart_key=self.meeting.key,
                         speech=self.speech if enabled else None)
        self.meeting.site = FastAPI()
        self.meeting.site.mount("/api/harness", app)

    def approve(self):
        response = self.meeting.m.post(self.meeting.path + "/messages/" + self.message["id"] + "/approve", json={})
        self.assertEqual(response.status_code, 200)

    def test_draft_cannot_be_heard_even_by_maestro(self):
        for client in [self.client, self.meeting.m]:
            self.assertEqual(client.post(self.path, json={}).status_code, 409)
        self.assertEqual(self.calls, [])

    def test_only_canonical_translation_is_spoken_and_restart_reuses_audio(self):
        self.approve()
        response = self.client.post(self.path, json={"text": "Never read client input", "language": "en"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["language"], "vi")
        self.assertEqual(base64.b64decode(response.json()["wav_base64"]), self.wav)
        self.assertEqual(self.calls, [(self.message["text"], "vi")])
        cookies = self.client.cookies
        self.build()
        from fastapi.testclient import TestClient
        restarted = TestClient(self.meeting.site, cookies=cookies, headers={"Origin": "http://testserver"})
        self.assertEqual(restarted.post(self.path, json={}).json(), response.json())
        self.assertEqual(len(self.calls), 1)

    def test_outsider_and_cross_origin_cannot_trigger_speech(self):
        self.approve()
        self.assertEqual(self.meeting.login("other").post(self.path, json={}).status_code, 404)
        self.assertEqual(self.client.post(self.path, json={}, headers={"Origin": "https://evil.invalid"}).status_code, 403)
        self.assertEqual(self.calls, [])

    def test_not_enabled_and_corrupt_audio_fail_closed(self):
        self.approve()
        self.wav = b"not a waveform"
        self.assertEqual(self.client.post(self.path, json={}).status_code, 502)
        self.build(enabled=False)
        from fastapi.testclient import TestClient
        client = TestClient(self.meeting.site, cookies=self.client.cookies, headers={"Origin": "http://testserver"})
        self.assertEqual(client.post(self.path, json={}).status_code, 503)
