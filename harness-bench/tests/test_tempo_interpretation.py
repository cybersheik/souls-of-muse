import unittest
from pathlib import Path

from harness.validator import compare, load_glossary, signature


class TempoInterpretation(unittest.TestCase):
    def test_faithful_vietnamese_bpm_reply_does_not_gain_a_false_tempo_flag(self):
        glossary = load_glossary(Path(__file__).resolve().parents[1] / "data/seed_terms.jsonl")
        source = signature("Em sẽ giữ nhịp ở 60 bpm và lặp lại 4 lần.", "vi", glossary)
        translated = signature("I will keep the tempo at 60 bpm and repeat 4 times.", "en", glossary)
        self.assertEqual(compare(source, translated), [])
        wrong = signature("I will keep the tempo at 80 bpm and repeat 4 times.", "en", glossary)
        self.assertTrue(compare(source, wrong))
        invented = signature("Play at a fast tempo.", "en", glossary)
        self.assertTrue(compare(signature("Hãy chơi.", "vi", glossary), invented))
