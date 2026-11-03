import unittest
from pathlib import Path

from harness.validator import compare, load_glossary, signature


class SpokenInstructions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glossary = load_glossary(Path(__file__).resolve().parents[1] / "data/seed_terms.jsonl")

    def sig(self, text, lang):
        return signature(text, lang, self.glossary)

    def test_real_vi_reply_preserves_spelled_tempo_and_repetitions(self):
        source = self.sig("anh sẽ giữ nhịp ở sáu mươi nhịp mỗi phút và lặp lại bốn lần.", "vi")
        translated = self.sig("I will keep the tempo at sixty beats per minute and repeat four times.", "en")
        self.assertEqual(source["numbers"], {"60", "4"})
        self.assertEqual(compare(source, translated), [])

    def test_changed_spelled_tempo_is_detected(self):
        source = self.sig("Giữ sáu mươi nhịp mỗi phút và lặp bốn lần.", "vi")
        for output in ("Keep eighty beats per minute and repeat four times.",
                       "Keep sixty beats per minute and repeat five times."):
            self.assertTrue(any("числа" in issue for issue in compare(source, self.sig(output, "en"))))

    def test_digits_and_spoken_forms_are_equivalent(self):
        self.assertEqual(compare(self.sig("Play four times at sixty bpm.", "en"),
                                 self.sig("Chơi 4 lần ở 60 BPM.", "vi")), [])

    def test_compound_numbers_do_not_collapse_to_separate_digits(self):
        for text, lang, expected in [("one hundred and twenty-four", "en", "124"),
                                     ("một trăm hai mươi tư", "vi", "124"),
                                     ("one thousand and five", "en", "1005"),
                                     ("một nghìn không trăm lẻ năm", "vi", "1005")]:
            with self.subTest(text=text):
                self.assertEqual(self.sig(text, lang)["numbers"], {expected})

    def test_spoken_decimal_preserves_zeroes(self):
        self.assertEqual(self.sig("one point zero five", "en")["numbers"], {"1.05"})
        self.assertEqual(self.sig("một phẩy không năm", "vi")["numbers"], {"1.05"})

    def test_independent_counts_and_article_are_not_added_together(self):
        self.assertEqual(self.sig("Play a minor chord four and five times.", "en")["numbers"], {"4", "5"})
        self.assertEqual(self.sig("Play one two three.", "en")["numbers"], {"1", "2", "3"})

    def test_tempo_alias_does_not_hide_invented_instruction(self):
        self.assertTrue(compare(self.sig("Hãy chơi.", "vi"), self.sig("Play at sixty beats per minute.", "en")))

    def test_vietnamese_negation_is_not_a_zero(self):
        source = self.sig("Không tăng tempo.", "vi")
        self.assertEqual(source["numbers"], set())
        self.assertEqual(compare(source, self.sig("Do not increase tempo.", "en")), [])

    def test_vietnamese_numeric_zero_is_not_a_negation(self):
        for source, output in [("Giữ không phẩy không năm BPM.", "Keep 0.05 BPM."),
                               ("Chơi một nghìn không trăm lẻ năm lần.", "Play 1005 times.")]:
            with self.subTest(source=source):
                self.assertEqual(compare(self.sig(source, "vi"), self.sig(output, "en")), [])

    def test_one_in_bpm_unit_is_not_a_new_quantity(self):
        self.assertEqual(compare(self.sig("Giữ sáu mươi nhịp một phút.", "vi"),
                                 self.sig("Keep sixty beats per minute.", "en")), [])

    def test_scale_linkers_and_scale_commas(self):
        for text, lang, expected in [("một nghìn lẻ một", "vi", "1001"),
                                     ("một nghìn linh bảy mươi", "vi", "1070"),
                                     ("one thousand, two hundred and thirty-four", "en", "1234")]:
            with self.subTest(text=text):
                self.assertEqual(self.sig(text, lang)["numbers"], {expected})
        self.assertEqual(self.sig("one thousand, two thousand", "en")["numbers"], {"1000", "2000"})
