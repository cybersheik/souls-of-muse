import io
import os
import sys
import unittest
import wave

try:
    from service.native_speech import NativeSpeech
except ImportError:
    NativeSpeech = None


@unittest.skipUnless(sys.platform == "darwin" and os.environ.get("SOM_TEST_NATIVE_TTS") == "1",
                     "operator-enabled macOS voice integration check")
class NativeSpeechTests(unittest.TestCase):
    def test_installed_english_and_vietnamese_voices_produce_nonempty_pcm_wav(self):
        self.assertIsNotNone(NativeSpeech, "native speech implementation is missing")
        speech = NativeSpeech()
        for language, text in [("en", "Hello. Play slowly."), ("vi", "Xin chào. Chơi chậm.")]:
            with self.subTest(language=language):
                audio = speech.synthesize(text, language)
                with wave.open(io.BytesIO(audio), "rb") as recording:
                    self.assertEqual((recording.getnchannels(), recording.getsampwidth(), recording.getframerate()), (1, 2, 16000))
                    self.assertGreater(recording.getnframes(), 1600)
                    self.assertTrue(any(recording.readframes(recording.getnframes())))

    def test_unsupported_language_and_overlong_text_are_rejected_before_synthesis(self):
        self.assertIsNotNone(NativeSpeech, "native speech implementation is missing")
        speech = NativeSpeech()
        for text, language in [("Hello", "ru"), ("", "en"), ("a" * 401, "en")]:
            with self.assertRaises(ValueError):
                speech.synthesize(text, language)
