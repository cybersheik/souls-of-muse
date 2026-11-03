import io
import unittest
import wave

from service.media_transport import AudioCapture, LiveKitTransport


class MediaCaptureBounds(unittest.TestCase):
    def test_pcm_is_bounded_to_ten_seconds_and_keeps_wav_shape(self):
        capture = AudioCapture()
        capture.push(b"\1\0" * 170_000)
        with wave.open(io.BytesIO(capture.finish())) as audio:
            self.assertEqual((audio.getframerate(), audio.getnchannels(), audio.getsampwidth()), (16000, 1, 2))
            self.assertEqual(audio.getnframes(), 160_000)

    def test_no_recording_and_invalid_pcm_fail_without_recognizer_call(self):
        with self.assertRaises(ValueError): AudioCapture().finish()
        with self.assertRaises(ValueError): AudioCapture().push(b"odd")

    def test_old_recording_cancel_cannot_remove_new_capture(self):
        transport=LiveKitTransport(None,None)
        class Connected:
            def isconnected(self): return True
        transport.channels[("epoch","user","ingress")]={"room":Connected()}
        transport.begin_capture("epoch","user","old")
        transport.captures[("epoch","user")][1].push(b"\1\0"*160)
        transport.finish_capture("epoch","user","old")
        transport.begin_capture("epoch","user","new")
        transport.captures[("epoch","user")][1].push(b"\2\0"*160)
        transport.cancel_capture("epoch","user","old")
        with wave.open(io.BytesIO(transport.finish_capture("epoch","user","new"))) as audio:
            self.assertEqual(audio.readframes(160),b"\2\0"*160)
