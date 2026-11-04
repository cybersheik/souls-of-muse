import unittest
from unittest.mock import patch
from service.mms_tts import MmsSpeech, spoken_text


class MusicalSpeechText(unittest.TestCase):
    def test_remote_revision_needs_only_the_bundled_catalog(self):
        from service import mms_tts
        original_import = __import__
        def no_model_runtime(name, *args, **kwargs):
            if name in ("numpy", "torch", "transformers"):
                raise AssertionError("revision loaded model runtime")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", no_model_runtime), patch("pathlib.Path.read_bytes", side_effect=AssertionError("revision read weights")):
            revision = mms_tts.speech_revision()
        self.assertEqual(revision, "mms-normalization-v4:c71de0fe7204c83f1c10820a7d696d0b450048ba:b58928d033932a49aa8e3d6cf11625b25fe928d2")
        self.assertEqual(mms_tts.MMS_NORMALIZATION_REVISION, "mms-normalization-v4")

    def test_bpm_and_time_signature_survive_mms_normalization(self):
        self.assertEqual(spoken_text("Keep 60bpm. Play C# in 4/4.", "en"),
                         "keep sixty beats per minute play see sharp in four over four")
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

    def test_expanded_speech_is_bounded_without_truncation(self):
        for language in ("en", "vi"):
            with self.subTest(language=language):
                self.assertEqual(spoken_text("x" * 240, language), "x" * 240)
                with self.assertRaisesRegex(ValueError, "unsupported_speech_text"):
                    spoken_text("x" * 241, language)
        for text, language in [("Play chords Am C Bb at 60 BPM. " * 4, "en"),
                               ("Chơi hợp âm Am C Bb ở 60 BPM. " * 4, "vi")]:
            with self.subTest(text=text, language=language):
                self.assertLess(len(text), 400)
                with self.assertRaisesRegex(ValueError, "unsupported_speech_text"):
                    spoken_text(text, language)

    def test_oversized_expanded_text_fails_before_model_runtime_load(self):
        original_import = __import__
        def no_model_runtime(name, *args, **kwargs):
            if name in ("numpy", "torch", "transformers"):
                raise AssertionError("oversized text reached model runtime")
            return original_import(name, *args, **kwargs)
        speech = MmsSpeech.__new__(MmsSpeech)
        for text, language in [("Play chords Am C Bb at 60 BPM. " * 4, "en"),
                               ("Chơi hợp âm Am C Bb ở 60 BPM. " * 4, "vi")]:
            with self.subTest(language=language), patch("builtins.__import__", no_model_runtime):
                with self.assertRaisesRegex(ValueError, "unsupported_speech_text"):
                    speech.synthesize(text, language)

    def test_full_musical_instructions_fit_exactly_at_the_spoken_limit(self):
        cases = [
            ("Play the chords Am, C and Bb for four beats at 60 BPM. Keep the pulse steady and listen to each note. "
             "Do not rush or change the rhythm. Repeat slowly and keep each beat even. Keep the last note very even.", "en"),
            ("Chơi các hợp âm Am, C và Bb trong bốn phách ở tốc độ 60 BPM. Giữ nhịp đều và nghe từng nốt. "
             "Đừng chơi nhanh hoặc đổi nhịp. Lặp lại chậm và giữ từng phách thật đều. Dừng một chút rồi tiếp tục với cùng nhịp.", "vi"),
        ]
        for text, language in cases:
            with self.subTest(language=language):
                normalized = spoken_text(text, language)
                self.assertEqual(len(normalized), 240)
                self.assertIn("ay minor" if language == "en" else "la thứ", normalized)
                self.assertIn("do not rush" if language == "en" else "đừng chơi nhanh", normalized)
                with self.assertRaisesRegex(ValueError, "unsupported_speech_text"):
                    spoken_text(text + " Again.", language)

    def test_musical_ranges_are_not_spoken_as_negative_numbers(self):
        self.assertEqual(spoken_text("Play measures 2-4 at 60–80 bpm.", "en"),
                         "play measures two to four at sixty to eighty beats per minute")
        self.assertEqual(spoken_text("Chơi ô nhịp 2-4 ở 60–80 bpm.", "vi"),
                         "chơi ô nhịp hai đến bốn ở sáu mươi đến tám mươi nhịp mỗi phút")
        self.assertEqual(spoken_text("Shift by -2.", "en"), "shift by minus two")
        self.assertEqual(spoken_text("Shift by −2.", "en"), "shift by minus two")
        self.assertEqual(spoken_text("Dịch -2.", "vi"), "dịch âm hai")

    def test_cued_chord_progressions_expand_roots_qualities_and_ascii_flats(self):
        cases = [
            ("Play Am and C, then Bb at 60 BPM four times.", "en",
             "play ay minor and see major then bee flat major at sixty beats per minute four times"),
            ("Chơi Am và C, rồi Bb ở 60 BPM bốn lần.", "vi",
             "chơi la thứ và đô trưởng rồi si giáng trưởng ở sáu mươi nhịp mỗi phút bốn lần"),
            ("Chords: C Dm Eb F# G A Bb.", "en",
             "chords see major dee minor ee flat major eff sharp major gee major ay major bee flat major"),
            ("Hợp âm: C Dm Eb F# G A Bb.", "vi",
             "hợp âm đô trưởng rê thứ mi giáng trưởng fa thăng trưởng sol trưởng la trưởng si giáng trưởng"),
            ("Am C Bb", "en", "ay minor see major bee flat major"),
            ("Am C Bb", "vi", "la thứ đô trưởng si giáng trưởng"),
        ]
        for text, language, expected in cases:
            with self.subTest(text=text, language=language):
                self.assertEqual(spoken_text(text, language), expected)

    def test_explicit_notes_keep_octaves_without_inventing_major_chords(self):
        cases = [
            ("Play notes C D E F G A B.", "en", "play notes see dee ee eff gee ay bee"),
            ("Chơi nốt C D E F G A B.", "vi", "chơi nốt đô rê mi fa sol la si"),
            ("Play note F#4 and note Bb3.", "en", "play note eff sharp four and note bee flat three"),
            ("Play note F-sharp and note B flat.", "en", "play note eff sharp and note bee flat"),
            ("Chơi nốt F♯4 và nốt B♭3.", "vi", "chơi nốt fa thăng bốn và nốt si giáng ba"),
            ("Play A minor chord.", "en", "play ay minor chord"),
        ]
        for text, language, expected in cases:
            with self.subTest(text=text, language=language):
                self.assertEqual(spoken_text(text, language), expected)

    def test_postfix_musical_noun_grounds_the_actual_canonical_translation(self):
        cases = [
            ("Play an A minor chord for four beats at 60 BPM.", "en",
             "play an ay minor chord for four beats at sixty beats per minute"),
            ("Start with the C# minor chord, then the F sharp note.", "en",
             "start with the see sharp minor chord then the eff sharp note"),
            ("Use the A major chord and the Bb note.", "vi",
             "use the la trưởng chord and the si giáng note"),
        ]
        for text, language, expected in cases:
            with self.subTest(text=text, language=language):
                self.assertEqual(spoken_text(text, language), expected)

    def test_slash_bass_and_negated_musical_instructions_preserve_meaning(self):
        cases = [
            ("Strum Am/C, then Bb/F.", "en", "strum ay minor over see then bee flat major over eff"),
            ("Đánh hợp âm Am/C rồi Bb/F.", "vi", "đánh hợp âm la thứ trên đô rồi si giáng trưởng trên fa"),
            ("Don't play Bb at 60–80 BPM; repeat Am/C 4 times.", "en",
             "don't play bee flat at sixty to eighty beats per minute repeat ay minor over see four times"),
            ("Đừng chơi Bb ở 60–80 BPM; lặp lại Am/C 4 lần.", "vi",
             "đừng chơi si giáng ở sáu mươi đến tám mươi nhịp mỗi phút lặp lại la thứ trên đô bốn lần"),
        ]
        for text, language, expected in cases:
            with self.subTest(text=text, language=language):
                self.assertEqual(spoken_text(text, language), expected)

    def test_articles_words_variables_and_unqualified_letters_are_not_chords(self):
        cases = [
            ("I am ready. Am I late? Plan C uses variable B.", "i am ready am i late plan c uses variable b"),
            ("Play a little slower. Play A little slower.", "play a little slower play a little slower"),
            ("Play A major role.", "play a major role"),
            ("Start with a minor change. A minor chord sounds different.",
             "start with a minor change a minor chord sounds different"),
            ("Play Am I late? Repeat Am I late?", "play am i late repeat am i late"),
            ("Play section B from plan C.", "play section b from plan c"),
            ("Repeat B in the equation.", "repeat b in the equation"),
            ("A B C", "a b c"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(spoken_text(text, "en"), expected)

    def test_unsupported_cued_notation_fails_before_partial_pitch_rewriting(self):
        for text in ("Play Am7.", "Chords: Cmaj7 Dm7.", "Play chord Cdim.",
                     "Chơi hợp âm Csus4.", "Play Am/C/G.", "Play note Am.",
                     "Chords: C diminished.", "Play chord C sus4.",
                     "Chơi hợp âm C giảm."):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    spoken_text(text, "en" if text.startswith(("Play", "Chords")) else "vi")
