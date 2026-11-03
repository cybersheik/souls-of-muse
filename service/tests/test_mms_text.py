import unittest
from service.mms_tts import spoken_text


class MusicalSpeechText(unittest.TestCase):
    def test_bpm_and_time_signature_survive_mms_normalization(self):
        self.assertEqual(spoken_text("Keep 60bpm. Play C# in 4/4.", "en"),
                         "keep sixty beats per minute play c sharp in four over four")
        self.assertEqual(spoken_text("Giữ 60bpm. Chơi Đô♯ trong nhịp 4/4.", "vi"),
                         "giữ sáu mươi nhịp mỗi phút chơi đô thăng trong nhịp bốn trên bốn")

    def test_decimal_digits_are_not_lost_or_reinterpreted(self):
        self.assertEqual(spoken_text("Wait 2.05 seconds.", "en"), "wait two point zero five seconds")
        self.assertEqual(spoken_text("Chờ 2,05 giây.", "vi"), "chờ hai phẩy không năm giây")
        self.assertEqual(spoken_text("1,000 notes", "en"), "one thousand notes")
        self.assertEqual(spoken_text("1.000 nốt", "vi"), "một nghìn nốt")

    def test_ambiguous_numbers_and_excessive_text_are_rejected(self):
        for text, lang in [("1,20 notes", "en"), ("2.05 giây", "vi"), ("1000000 notes", "en"), ("x"*401, "en")]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError): spoken_text(text, lang)

    def test_musical_ranges_are_not_spoken_as_negative_numbers(self):
        self.assertEqual(spoken_text("Play measures 2-4 at 60–80 bpm.", "en"),
                         "play measures two to four at sixty to eighty beats per minute")
        self.assertEqual(spoken_text("Chơi ô nhịp 2-4 ở 60–80 bpm.", "vi"),
                         "chơi ô nhịp hai đến bốn ở sáu mươi đến tám mươi nhịp mỗi phút")
        self.assertEqual(spoken_text("Shift by -2.", "en"), "shift by minus two")
        self.assertEqual(spoken_text("Shift by −2.", "en"), "shift by minus two")
        self.assertEqual(spoken_text("Dịch -2.", "vi"), "dịch âm hai")
