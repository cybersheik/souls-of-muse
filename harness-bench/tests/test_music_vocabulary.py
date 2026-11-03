"""Pitch identity must survive translation between letter names and fixed-do names."""
import unittest
import unicodedata
from pathlib import Path

from harness.validator import compare, load_glossary, notes, signature
from harness.music_vocabulary import field_pitches


class MusicalPitchValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glossary = load_glossary(Path(__file__).resolve().parents[1] / "data/seed_terms.jsonl")

    def test_vietnamese_fixed_do_and_accidentals_have_the_same_pitch_identity(self):
        cases = [
            ("hợp âm La thứ", {"A"}),
            ("Đô trưởng", {"C"}),
            ("Rê giáng thứ", {"Db"}),
            ("nốt Mi giáng", {"Eb"}),
            ("nốt Pha thăng", {"F#"}),
            ("gam Son trưởng", {"G"}),
            ("hợp âm Si giáng trưởng", {"Bb"}),
            ("hợp âm La thứ và Mi trưởng", {"A", "E"}),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(notes(text), expected)
                self.assertEqual(notes(unicodedata.normalize("NFD", text)), expected)

    def test_spoken_and_symbol_accidentals_are_equivalent_in_context(self):
        for text, expected in [
            ("Play the F sharp minor chord.", {"F#"}),
            ("Play the F-sharp minor chord.", {"F#"}),
            ("Play note F-sharp.", {"F#"}),
            ("Play the B-flat major chord.", {"Bb"}),
            ("Play B flat major.", {"Bb"}),
            ("Play the C♯ minor chord.", {"C#"}),
            ("Play the G♭ major scale.", {"Gb"}),
            ("Play note E.", {"E"}),
            ("Switch to the key of D.", {"D"}),
            ("Play the chord B.", {"B"}),
        ]:
            with self.subTest(text=text):
                self.assertEqual(notes(text), expected)

    def test_faithful_en_vi_chord_translation_passes_and_changed_root_flags(self):
        source = signature("Play the A minor chord.", "en", self.glossary)
        correct = signature("Hãy chơi hợp âm La thứ.", "vi", self.glossary)
        wrong = signature("Hãy chơi hợp âm Mi thứ.", "vi", self.glossary)
        self.assertEqual(compare(source, correct), [])
        self.assertTrue(any("ноты" in issue for issue in compare(source, wrong)))
        self.assertTrue(any("ноты" in issue for issue in compare(correct, source | {"notes": {"E"}})))

    def test_loss_or_reversal_of_spoken_accidental_flags(self):
        src = signature("Play the F sharp minor chord.", "en", self.glossary)
        faithful = signature("Hãy chơi hợp âm Fa thăng thứ.", "vi", self.glossary)
        self.assertEqual(compare(src, faithful), [])
        for changed in ["Hãy chơi hợp âm Fa thứ.", "Hãy chơi hợp âm Fa giáng thứ."]:
            with self.subTest(changed=changed):
                self.assertTrue(any("ноты" in issue for issue in compare(src, signature(changed, "vi", self.glossary))))

    def test_vietnamese_ordinal_thu_is_not_a_minor_key(self):
        source = signature("Play the second measure slowly.", "en", self.glossary)
        translated = signature("Hãy chơi ô nhịp thứ hai thật chậm.", "vi", self.glossary)
        self.assertEqual(compare(source, translated), [])
        chord = signature("Chơi hợp âm La thứ ba lần.", "vi", self.glossary)
        self.assertIn("KEY_MINOR", chord["terms"])
        self.assertEqual(compare(signature("Play the A minor chord 3 times.", "en", self.glossary), chord), [])

    def test_rootless_minor_repetition_is_distinct_from_chord_ordinal(self):
        for source, translated in [
            ("Play the minor chord 3 times.", "Chơi hợp âm thứ ba lần."),
            ("Play the minor scale 3 times.", "Chơi gam thứ ba lần."),
            ("Play the minor chord 23 times.", "Chơi hợp âm thứ hai mươi ba lần."),
            ("Play the third chord.", "Chơi hợp âm thứ ba."),
            ("Play the third chord 2 times.", "Chơi hợp âm thứ ba hai lần."),
        ]:
            with self.subTest(source=source):
                self.assertEqual(compare(signature(source, "en", self.glossary),
                                         signature(translated, "vi", self.glossary)), [])

    def test_typed_note_fields_keep_all_pitches_order_repetition_and_octaves(self):
        for value, expected in [("C4", ("C4",)), ("Mi4", ("E4",)),
                ("F sharp and G sharp", ("F#", "G#")),
                ("Fa thăng và La thăng", ("F#", "A#")),
                ("F#4, A♭3, F#4", ("F#4", "Ab3", "F#4")),
                ("Si giáng4", ("Bb4",)),
                ("A minor and E major", ("A:minor", "E:major")),
                ("La trưởng và Mi thứ", ("A:major", "E:minor"))]:
            with self.subTest(value=value):
                self.assertEqual(field_pitches(value), (expected, True))

    def test_unsupported_note_field_forms_are_not_silent_empty_matches(self):
        for value in ("Am7", "C-1", "C diminished", "the chord", "C4foo", "minor C"):
            with self.subTest(value=value):
                self.assertFalse(field_pitches(value)[1])

    def test_unqualified_letters_or_solfege_in_prose_do_not_invent_notes(self):
        for text in ["Play a little slower.", "Do not speed up.", "Let me see.",
                     "La is an alias.", "A and B are participants.", "Please do repeat.",
                     "The word bass starts with b.", "Repeat the chord a little slower.",
                     "Play a scale.", "It is a major problem.", "Play a chord.",
                     "A scale has seven notes.", "A chord is built from notes.",
                     "Listen first. A chord contains several notes."]:
            with self.subTest(text=text):
                self.assertEqual(notes(text), set())

    def test_short_vietnamese_note_label_preserves_note_concept_and_accidental(self):
        for source,target in [('Play note F-sharp on beat 1.','Chơi nốt Fa thăng ở phách 1.'),('Play note C.','Chơi nốt đô.'),('Play note B-flat.','Chơi nốt Si giáng.'),('Play note F.','Chơi nốt F.')]:
            with self.subTest(target=target):self.assertEqual(compare(signature(source,'en',self.glossary),signature(target,'vi',self.glossary)),[])
    def test_colloquial_not_is_not_a_musical_note_reference(self):
        for text in ['Làm nốt phần còn lại.','Làm nốt phần còn lại. Chơi hợp âm Fa.','nốt factor','nốt a little slower.']:
            with self.subTest(text=text):self.assertNotIn('NOTE',signature(text,'vi',self.glossary)['terms'])
