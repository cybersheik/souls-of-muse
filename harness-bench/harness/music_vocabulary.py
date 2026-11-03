"""Bounded recognition hints and contextual EN/VI pitch names.

Hints are general musical vocabulary, never an expected transcript. They do
not constrain ASR or repair its output. Pitch matching uses fixed-do Vietnamese
names; enharmonic spellings remain distinct so a changed accidental flags.
"""
import re
import unicodedata
from .spoken_numbers import numeric_text


VI_PITCHES = {"đô": "C", "do": "C", "rê": "D", "re": "D", "mi": "E",
              "fa": "F", "pha": "F", "sol": "G", "son": "G", "la": "A", "si": "B"}
_ROOT = r"(?:đô|do|rê|re|mi|pha|fa|sol|son|la|si|[a-g])"
_ACC = r"(?:sharp|flat|thăng|giáng|[#♯b♭])"
_PITCH = rf"(?P<root>{_ROOT})(?:[\s\-‐‑]*(?P<acc>{_ACC}))?(?![\w#♯♭\-‐‑])"
_AFTER = re.compile(rf"(?<!\w){_PITCH}\s+(?:major|minor|chord|scale|trưởng|thứ|hợp\s+âm)\b", re.I)
_BEFORE = re.compile(rf"\b(?:note|chord|key(?:\s+of)?|scale(?:\s+of)?|nốt(?:\s+nhạc)?|hợp\s+âm|gam|giọng)\s+{_PITCH}", re.I)
_PITCH_END = re.compile(rf"(?<!\w){_PITCH}\s*$", re.I)
_ORDINAL_THU = re.compile(r"\bthứ(?=\s+(?:nhất|một|hai|ba|tư|bốn|năm|sáu|bảy|tám|chín|mười|\d+)\b)", re.I)
_FIELD_PITCH = re.compile(rf"(?<!\w)(?P<root>{_ROOT})(?:[\s\-‐‑]*(?P<acc>{_ACC}))?(?P<octave>[0-9])?(?:\s+(?P<quality>major|minor|trưởng|thứ))?(?![\w#♯♭\-‐‑])", re.I)
_FIELD_WORDS = re.compile(r"\b(?:and|or|then|the|note|notes|chord|chords|key|keys|scale|scales|of|in|nốt|nhạc|hợp|âm|gam|giọng|và|rồi|từ|đến)\b", re.I)


def field_pitches(text):
    """Ordered pitch identities in an explicitly typed note field.

    Unlike prose matching, this binds every bare pitch, octave and major/minor
    quality to its position. Unknown
    notation is reported as unsupported, never silently treated as equality.
    """
    text = unicodedata.normalize("NFC", text)
    pitches = []
    def consume(match):
        root = match["root"].lower()
        accidental = (match["acc"] or "").lower()
        if accidental in ("sharp", "thăng", "♯"):
            accidental = "#"
        elif accidental in ("flat", "giáng", "♭"):
            accidental = "b"
        quality = (match["quality"] or "").lower()
        quality = {"trưởng": "major", "thứ": "minor"}.get(quality, quality)
        pitches.append(VI_PITCHES.get(root, root.upper()) + accidental + (match["octave"] or "")
                       + (":" + quality if quality else ""))
        return " "
    leftover = _FIELD_PITCH.sub(consume, text)
    leftover = _FIELD_WORDS.sub(" ", leftover)
    leftover = re.sub(r"[\s,.;:/()\[\]–—\-]+", "", leftover)
    return tuple(pitches), bool(pitches) and not leftover


def ordinal_thu_spans(text):
    """Exclude ordinal thứ hai from minor, preserving La thứ ba lần (Am ×3)."""
    out = set()
    for match in _ORDINAL_THU.finditer(text):
        prefix = text[:match.start()]
        if _PITCH_END.search(prefix):
            continue
        quality = re.search(r"\b(?:hợp\s+âm|gam|giọng|âm\s+giai)\s*$", prefix, re.I)
        # "minor chord three times" does not require a named root. A single
        # numeric phrase before lần marks repetitions; "third chord two times"
        # has two independent numbers and keeps the ordinal interpretation.
        if quality and re.match(r"\s*\d+(?:[.,]\d+)?\s+lần\b", numeric_text(text[match.end():], "vi")):
            continue
        out.add((match.start(), match.end()))
    return out


def _contextual_match(text, match, pattern):
    # "a" may be an article; share this distinction with NOTE terminology.
    prefix = text[:match.start("root")].strip()
    article_position = not prefix or re.search(r"[.!?:]$", prefix)
    if match["root"].lower() == "a" and not match["acc"] and (match["root"] == "a" or article_position):
        tail = text[match.end("root"):]
        qualified = re.match(r"\s+(?:major|minor)(?=\s+(?:chord|scale|key)\b|\s*[,.;:!?]|\s*$)", tail, re.I)
        terminal = pattern is _BEFORE and re.match(r"\s*(?:[,.;:!?]|$)", tail)
        return bool(qualified or terminal)
    return True


def has_vi_note_reference(text):
    """Short nốt is a NOTE only when it introduces a contextual named pitch."""
    text = unicodedata.normalize("NFC", text)
    return any(match.group(0).lower().startswith("nốt") and _contextual_match(text, match, _BEFORE)
               for match in _BEFORE.finditer(text))


def contextual_pitches(text):
    """Recognize named pitches only next to musical context, not bare a/do/la."""
    text = unicodedata.normalize("NFC", text)
    out = set()
    for pattern in (_AFTER, _BEFORE):
        for match in pattern.finditer(text):
            if not _contextual_match(text, match, pattern):
                continue
            root = match["root"].lower()
            letter = VI_PITCHES.get(root, root.upper())
            accidental = (match["acc"] or "").lower()
            if accidental in ("sharp", "thăng", "♯"):
                accidental = "#"
            elif accidental in ("flat", "giáng", "♭"):
                accidental = "b"
            out.add(letter + accidental)
    return out


def recognition_keywords(glossary, language):
    """One language's glossary plus all seven roots with major/minor triads.

    Both sharp and flat forms are covered uniformly. This list is independent
    of the speaker's recording, draft or reference text and meets the adapter's
    200-entry / 100-character contract. No client-supplied hints are accepted.
    """
    if language not in ("en", "vi"):
        raise ValueError("unsupported_recognition_language")
    base = []
    for term in glossary:
        forms = term.get(language, [])
        base.extend(forms if isinstance(forms, list) else [forms])
    hints = []
    roots = list("CDEFGAB") if language == "en" else ["Đô", "Rê", "Mi", "Fa", "Sol", "La", "Si"]
    accidentals = ("", " sharp", " flat") if language == "en" else ("", " thăng", " giáng")
    for root in roots:
        for accidental in accidentals:
            pitch = root + accidental
            hints.append("note " + pitch if language == "en" else "nốt " + pitch)
            for quality in (("major", "minor") if language == "en" else ("trưởng", "thứ")):
                hints.append(f"{pitch} {quality} chord" if language == "en" else f"hợp âm {pitch} {quality}")
    # Keep complete pitch coverage even if a future glossary grows very large.
    # Sorting only the glossary makes selection deterministic across processes.
    return list(dict.fromkeys(hints + sorted({form for form in base
        if isinstance(form, str) and 0 < len(form) <= 100})))[:200]
