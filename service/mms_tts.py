"""Pinned Meta MMS-TTS evaluation. No downloads or remote code at runtime."""
import hashlib
import importlib.util
import io
import json
import re
import unicodedata
import wave
from pathlib import Path

from .speech import MAX_TEXT, validate_wav


# Bound the model input after numbers/chords expand; never truncate a message.
MAX_SPOKEN_TEXT = 240
MMS_NORMALIZATION_REVISION = "mms-normalization-v4"


def speech_revision(catalog=None):
    """Return the cache identity using only the bundled checkpoint catalog."""
    if catalog is None:
        catalog = json.loads(Path(__file__).with_name("mms_models.json").read_text())
    return MMS_NORMALIZATION_REVISION + ":" + ":".join(catalog[lang]["revision"] for lang in ("en", "vi"))


_PITCH = re.compile(
    r"(?P<root>[A-G])(?P<acc>[#♯b♭]|-?(?:sharp|flat))?"
    r"(?P<quality>-?(?:minor|major|min|maj|m))?(?P<octave>[0-9])?"
    r"(?:/(?P<bass>[A-G])(?P<bass_acc>[#♯b♭]|-?(?:sharp|flat))?)?"
)
_CUE = re.compile(
    r"\b(?P<cue>chords?(?:\s+(?:list|progression))?|hợp\s+âm|notes?|nốt(?:\s+nhạc)?|"
    r"play(?:s|ed|ing)?|strum(?:s|med|ming)?|chơi|đánh|repeat|practi[cs]e|lặp\s+lại|tập)"
    r"\b\s*(?::|=)?\s*", re.IGNORECASE
)
_SEPARATOR = re.compile(r"(?:\s*[,;]\s*(?:(?:and|then|và|rồi)\b\s*)?|\s+(?:(?:and|then|và|rồi)\b\s*)?)", re.IGNORECASE)
_POSTFIX = re.compile(
    r"\b[A-G][\w#♯♭/+\-‐‑]*(?:\s+(?:sharp|flat|thăng|giáng))?"
    r"(?:\s+(?:major|minor|trưởng|thứ))?\s+(?P<kind>chords?|notes?|hợp\s+âm|nốt(?:\s+nhạc)?)\b",
    re.IGNORECASE,
)


def _pitch_at(text, start):
    """Read a whole token, so unsupported extensions never become naturals."""
    token = re.match(r"[A-G][\w#♯♭/+\-‐‑]*", text[start:])
    if token is None:
        return None
    raw = token.group().replace("‐", "-").replace("‑", "-")
    match = _PITCH.fullmatch(raw)
    if match is None:
        # Ordinary capitalized words (Amazing, Carefully) are not notation.
        if re.match(r"[A-G](?:[#♯b♭/0-9]|-?(?:sharp|flat|minor|major|min|maj|dim|aug|sus|add)|m(?=[0-9/]|$))", raw):
            raise ValueError("unsupported_speech_pitch")
        return None
    pitch = match.groupdict()
    pitch["start"], pitch["end"], pitch["raw"] = start, start + token.end(), raw
    if not any(pitch[key] for key in ("quality", "octave", "bass")):
        accidental = re.match(r"\s+(sharp|flat|thăng|giáng)\b", text[pitch["end"]:], re.IGNORECASE)
        if accidental:
            if pitch["acc"]:
                raise ValueError("unsupported_speech_pitch")
            pitch["acc"] = accidental.group(1).lower()
            pitch["end"] += accidental.end()
    if not any(pitch[key] for key in ("quality", "octave", "bass")):
        quality = re.match(r"\s+(major|minor|trưởng|thứ)\b", text[pitch["end"]:], re.IGNORECASE)
        if quality:
            pitch["quality"] = quality.group(1).lower()
            pitch["end"] += quality.end()
    if pitch["quality"] and pitch["octave"]:
        raise ValueError("unsupported_speech_pitch")
    if re.match(r"\s+(?:diminished|augmented|dim|aug|sus[24]?|add[0-9]+|"
                r"(?:major|minor|maj|min)[0-9]+|seventh|ninth|eleventh|thirteenth|giảm|tăng)\b",
                text[pitch["end"]:], re.IGNORECASE):
        raise ValueError("unsupported_speech_pitch")
    return pitch


def _pitch_run(text, start):
    pitches = []
    while True:
        pitch = _pitch_at(text, start)
        if pitch is None:
            break
        pitches.append(pitch)
        separator = _SEPARATOR.match(text, pitch["end"])
        if separator is None:
            break
        start = separator.end()
    return pitches


def _musical_text(text, language):
    """Expand case-sensitive pitch tokens only in an explicit musical grammar.

    Cues introduce a contiguous pitch list. Minor/major or slash notation makes
    that list chords; explicit notes retain octaves without inventing a quality.
    Bare letter lists without a cue, and article A followed by prose, stay prose.
    This changes speech input only, never the saved canonical translation.
    """
    roots = dict(zip("ABCDEFG", ("ay", "bee", "see", "dee", "ee", "eff", "gee") if language == "en"
                     else ("la", "si", "đô", "rê", "mi", "fa", "sol")))

    def name(root, accidental):
        result = roots[root]
        if accidental:
            sharp = accidental.lstrip("-") in ("#", "♯", "sharp", "thăng")
            result += " " + (("sharp" if sharp else "flat") if language == "en" else ("thăng" if sharp else "giáng"))
        return result

    def render(pitches, chord):
        result, previous = [], pitches[0]["start"]
        for pitch in pitches:
            result.append(text[previous:pitch["start"]])
            words = name(pitch["root"], pitch["acc"])
            if pitch["quality"] or chord:
                minor = (pitch["quality"] or "").lstrip("-") in ("m", "min", "minor", "thứ")
                words += " " + (("minor" if minor else "major") if language == "en" else ("thứ" if minor else "trưởng"))
            if pitch["octave"]:
                words += " " + pitch["octave"]
            if pitch["bass"]:
                words += (" over " if language == "en" else " trên ") + name(pitch["bass"], pitch["bass_acc"])
            result.append(words)
            previous = pitch["end"]
        return "".join(result)

    replacements = []
    for cue in _CUE.finditer(text):
        if replacements and cue.start() < replacements[-1][1]:
            continue
        pitches = _pitch_run(text, cue.end())
        if not pitches:
            continue
        if len(pitches) == 1 and pitches[0]["raw"] == "Am" and re.match(r"\s+I\b", text[pitches[0]["end"]:]):
            continue
        label = cue["cue"].lower()
        notes = label.startswith(("note", "nốt"))
        explicit_chord = label.startswith(("chord", "hợp", "strum"))
        marked = any(p["acc"] or p["quality"] or p["bass"] for p in pitches)
        if label in ("repeat", "practice", "practise", "lặp lại", "tập") and not marked:
            continue
        if notes and any(p["quality"] or p["bass"] for p in pitches):
            raise ValueError("unsupported_speech_pitch")
        if any(p["octave"] for p in pitches) and not notes:
            raise ValueError("ambiguous_speech_pitch")
        # Capitalization alone does not turn the English article A into a note.
        if len(pitches) == 1 and pitches[0]["raw"] == "A" and not pitches[0]["acc"]:
            tail = text[pitches[0]["end"]:]
            if tail.strip() and not re.match(r"\s*(?:[.,!?;:]|(?:chord|scale|key|note|at|for|in|on|again|once|twice|slowly)\b)", tail, re.IGNORECASE):
                continue
        chord = explicit_chord or (not notes and any(p["quality"] or p["bass"] for p in pitches))
        replacements.append((pitches[0]["start"], pitches[-1]["end"], render(pitches, chord)))
    for noun in _POSTFIX.finditer(text):
        if any(start <= noun.start() < end for start, end, _ in replacements):
            continue
        pitch = _pitch_at(text, noun.start())
        if pitch is None:
            continue
        # Sentence-initial "A minor chord" can have an indefinite article.
        # "an/the A minor chord" identifies the named pitch instead.
        if (pitch["raw"] == "A" and not pitch["acc"]
                and not re.search(r"\b(?:an|the)\s+$", text[:noun.start()], re.IGNORECASE)):
            continue
        notes = noun["kind"].lower().startswith(("note", "nốt"))
        if notes and (pitch["quality"] or pitch["bass"]):
            raise ValueError("unsupported_speech_pitch")
        if pitch["octave"] and not notes:
            raise ValueError("ambiguous_speech_pitch")
        replacements.append((pitch["start"], pitch["end"], render([pitch], not notes)))
    if not replacements:
        # A complete compact progression can stand alone; bare A B C cannot.
        start = len(text) - len(text.lstrip())
        pitches = _pitch_run(text, start)
        if (len(pitches) > 1 and not text[pitches[-1]["end"]:].strip(" \t\r\n.,!?:;")
                and any(p["acc"] or p["quality"] or p["bass"] for p in pitches)):
            if any(p["octave"] for p in pitches):
                raise ValueError("ambiguous_speech_pitch")
            chord = any(p["quality"] or p["bass"] for p in pitches)
            replacements.append((start, pitches[-1]["end"], render(pitches, chord)))
    for start, end, words in sorted(replacements, reverse=True):
        text = text[:start] + words + text[end:]
    return text


def spoken_text(text, language):
    """Expand musical quantities before MMS normalization can discard digits."""
    if language not in ("en", "vi") or not text.strip() or len(text) > MAX_TEXT:
        raise ValueError("unsupported_speech_text")
    from num2words import num2words
    text = _musical_text(unicodedata.normalize("NFC", text), language).lower()
    text = re.sub(r"\bbpm\b", "beats per minute" if language == "en" else "nhịp mỗi phút", text)
    # A quantity can touch its unit, e.g. 60bpm.
    text = re.sub(r"(?<=\d)bpm\b", " beats per minute" if language == "en" else " nhịp mỗi phút", text)
    text = re.sub(r"(?<=\d)\s*[-–—]\s*(?=\d)", " to " if language == "en" else " đến ", text)
    text = re.sub(r"[-−](?=\d)", " minus " if language == "en" else " âm ", text)
    def number(match):
        raw = match.group()
        group, decimal = (",", ".") if language == "en" else (".", ",")
        grouped = rf"\d{{1,3}}(?:{re.escape(group)}\d{{3}})+(?:{re.escape(decimal)}\d+)?"
        plain = rf"\d+(?:{re.escape(decimal)}\d+)?"
        if not re.fullmatch(grouped if group in raw else plain, raw):
            raise ValueError("ambiguous_speech_quantity")
        parts = raw.replace(group, "").split(decimal)
        value = int(parts[0])
        if value > 999_999 or (len(parts) > 1 and len(parts[1]) > 6):
            raise ValueError("unsupported_speech_quantity")
        words = num2words(value, lang=language)
        if len(parts) > 1:
            words += (" point " if language == "en" else " phẩy ") + " ".join(num2words(int(digit), lang=language) for digit in parts[1])
        return " " + words + " "
    text = re.sub(r"\d+(?:[.,]\d+)*", number, text)
    replacements = {"#": ("sharp", "thăng"), "♯": ("sharp", "thăng"),
                    "♭": ("flat", "giáng"), "/": ("over", "trên"),
                    "+": ("plus", "cộng"), "%": ("percent", "phần trăm"),
                    "&": ("and", "và"), "=": ("equals", "bằng")}
    for symbol, words in replacements.items():
        text = text.replace(symbol, " " + words[language == "vi"] + " ")
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r'[.,!?;:()\[\]{}"“”«»…—]', " ", text)
    text = " ".join(text.split())
    if not text or len(text) > MAX_SPOKEN_TEXT:
        raise ValueError("unsupported_speech_text")
    return text


class MmsSpeech:
    def __init__(self, root):
        self.root = Path(root)
        self.catalog = json.loads(Path(__file__).with_name("mms_models.json").read_text())
        for language, manifest in self.catalog.items():
            for filename, digest in manifest["files"].items():
                path = self.root / language / filename
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError("missing_or_changed_mms_asset")
        self.revision = speech_revision(self.catalog)
        self.models = {}

    @classmethod
    def from_environ(cls, env):
        # This is an opt-in technical evaluation under CC-BY-NC 4.0. Public or
        # commercial release requires a separately resolved deployment choice.
        if env.get("SOM_MMS_TTS_EVALUATION") != "1" or not env.get("SOM_MMS_TTS_DIR"):
            return None
        if any(importlib.util.find_spec(module) is None for module in ("torch", "transformers", "num2words")):
            return None
        try:
            return cls(env["SOM_MMS_TTS_DIR"])
        except (ValueError, OSError):
            return None

    def synthesize(self, text, language):
        normalized = spoken_text(text, language)
        import numpy as np
        import torch
        from transformers import VitsModel, VitsTokenizer
        torch.set_num_threads(2)
        if language not in self.models:
            path = self.root / language
            tokenizer = VitsTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
            model = VitsModel.from_pretrained(path, local_files_only=True, trust_remote_code=False, use_safetensors=True).eval()
            self.models[language] = tokenizer, model
        tokenizer, model = self.models[language]
        # Fail before inference if MMS would silently omit a letter, symbol or
        # number. Punctuation and supported quantities were handled above.
        if any(char not in tokenizer.get_vocab() for char in normalized):
            raise ValueError("unsupported_speech_character")
        encoded = tokenizer(normalized, return_tensors="pt")
        with torch.random.fork_rng(devices=[]), torch.inference_mode():
            torch.manual_seed(7)
            values = model(**encoded).waveform[0].cpu().numpy()
        if not np.isfinite(values).all() or not np.any(values):
            raise ValueError("invalid_speech_waveform")
        if model.config.sampling_rate != 16000:
            raise ValueError("invalid_speech_sample_rate")
        pcm = (np.clip(values, -1, 1) * 32767).astype("<i2").tobytes()
        output = io.BytesIO()
        with wave.open(output, "wb") as recording:
            recording.setnchannels(1); recording.setsampwidth(2); recording.setframerate(16000)
            recording.writeframes(pcm)
        result = output.getvalue()
        validate_wav(result)
        return result
