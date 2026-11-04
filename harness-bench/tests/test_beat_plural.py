"""The explicit BEAT plural must preserve the existing canonical term identity."""
import unittest
from pathlib import Path

from harness.validator import load_glossary, signature, term_ids
from service.app import _validate_translation as validate_pair


class BeatPlural(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glossary = load_glossary(Path(__file__).resolve().parents[1] / 'data/seed_terms.jsonl')

    def test_four_beats_and_bon_phach_validate_in_both_directions(self):
        for source, sl, target, tl in [('four beats', 'en', 'bốn phách', 'vi'),
                                      ('bốn phách', 'vi', 'four beats', 'en')]:
            with self.subTest(source=source):
                self.assertEqual(validate_pair(source, sl, target, tl, self.glossary), [])
                self.assertEqual(signature(source, sl, self.glossary)['terms'], {'BEAT'})
                self.assertEqual(signature(target, tl, self.glossary)['terms'], {'BEAT'})

    def test_singular_beat_keeps_the_same_identity(self):
        self.assertEqual(validate_pair('one beat', 'en', 'một phách', 'vi', self.glossary), [])
        self.assertEqual(term_ids('beat', self.glossary), {'BEAT'})

    def test_heartbeats_is_not_the_musical_term(self):
        self.assertNotIn('BEAT', term_ids('heartbeats', self.glossary))

    def test_missing_beat_or_changed_count_still_flags(self):
        self.assertTrue(validate_pair('bốn phách', 'vi', 'four', 'en', self.glossary))
        self.assertTrue(validate_pair('bốn phách', 'vi', 'five beats', 'en', self.glossary))

    def test_bpm_phrase_keeps_its_existing_longest_match(self):
        self.assertEqual(term_ids('60 beats per minute', self.glossary), {'BPM', 'TEMPO'})

    def test_all_thirty_canonical_ids_remain_unique_and_unchanged(self):
        expected = {'TEMPO', 'BEAT', 'MEASURE', 'RHYTHM', 'MELODY', 'HARMONY', 'CHORD', 'SCALE',
                    'NOTE', 'KEY_MAJOR', 'KEY_MINOR', 'SHARP', 'FLAT', 'OCTAVE', 'INTONATION',
                    'STRING', 'FRET', 'CAPO', 'STRUM', 'FINGERPICK', 'STACCATO', 'LEGATO',
                    'VERSE', 'CHORUS', 'BRIDGE', 'METRONOME', 'BPM', 'DYNAMICS', 'REHEARSAL', 'TUNING'}
        self.assertEqual(len(self.glossary), 30)
        self.assertEqual({row['term_id'] for row in self.glossary}, expected)


if __name__ == '__main__':
    unittest.main()
