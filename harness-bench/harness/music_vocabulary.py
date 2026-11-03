"""Bounded recognition hints and contextual EN/VI pitch names.

Hints are general musical vocabulary, never an expected transcript. They do
not constrain ASR or repair its output. Pitch matching uses fixed-do Vietnamese
names; enharmonic spellings remain distinct so a changed accidental flags.
"""
import re
import unicodedata


VI_PITCHES = {"đô": "C", "do": "C", "rê": "D", "re": "D", "mi": "E",
              "fa": "F", "pha": "F", "sol": "G", "son": "G", "la": "A", "si": "B"}
_ROOT = r"(?:đô|do|rê|re|mi|pha|fa|sol|son|la|si|[a-g])"
_ACC = r"(?:sharp|flat|thăng|giáng|[#♯b♭])"
_PITCH = rf"(?P<root>{_ROOT})(?:[\s\-‐‑]*(?P<acc>{_ACC}))?(?![\w#♯♭\-‐‑])"
_AFTER = re.compile(rf"(?<!\w){_PITCH}\s+(?:major|minor|chord|scale|trưởng|thứ|hợp\s+âm)\b", re.I)
_BEFORE = re.compile(rf"\b(?:note|chord|key(?:\s+of)?|scale(?:\s+of)?|nốt(?:\s+nhạc)?|hợp\s+âm|gam|giọng)\s+{_PITCH}", re.I)


def contextual_pitches(text):
    """Recognize named pitches only next to musical context, not bare a/do/la."""
    text = unicodedata.normalize("NFC", text)
    out = set()
    for pattern in (_AFTER, _BEFORE):
        for match in pattern.finditer(text):
            # "a" (also sentence-initial "A") is an English article. Accept an explicitly
            # qualified "a minor chord" or a terminal prefix such as "note a."
            # but never turn "a scale" / "chord a little slower" into a pitch.
            prefix = text[:match.start("root")].strip()
            article_position = not prefix or re.search(r"[.!?:]$", prefix)
            if match["root"].lower() == "a" and not match["acc"] and (match["root"] == "a" or article_position):
                tail = text[match.end("root"):]
                qualified = re.match(r"\s+(?:major|minor)(?=\s+(?:chord|scale|key)\b|\s*[,.;:!?]|\s*$)", tail, re.I)
                terminal = pattern is _BEFORE and re.match(r"\s*(?:[,.;:!?]|$)", tail)
                if not qualified and not terminal:
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
