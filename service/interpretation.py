"""Typed, quoted lesson notes: no ungrounded performance observations."""
import json
import re
import unicodedata
from jsonschema import Draft202012Validator, ValidationError


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _quote():
    return {"anyOf": [_object({"source": {"type": "string"}, "translation": {"type": "string"}}), {"type": "null"}]}


NOTE_SCHEMA = _object({"heard": _quote(), "where": _object({"measure": _quote(), "note": _quote()}),
                       "change": _quote(), "try": _quote()})
INTERPRETATION_SCHEMA = _object({"translation": {"type": "string"}, "lesson_note": NOTE_SCHEMA})
INTERPRETATION_FORMAT = {"type": "json_schema", "json_schema": {
    "name": "music_interpretation", "strict": True, "schema": INTERPRETATION_SCHEMA}}
MAX_RAW = 16000


class InvalidInterpretation(ValueError):
    pass


def note_parts(note):
    for field in ("heard", "change", "try"):
        yield field, note[field]
    for field in ("measure", "note"):
        yield "where." + field, note["where"][field]


def parse_interpretation(raw, source):
    """Check shape and canonical Unicode substring evidence before any delivery."""
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise InvalidInterpretation("invalid_interpretation")
            value[key] = item
        return value
    try:
        if not isinstance(raw, str) or not 0 < len(raw) <= MAX_RAW:
            raise InvalidInterpretation("invalid_interpretation")
        data = json.loads(raw, object_pairs_hook=unique)
        Draft202012Validator(INTERPRETATION_SCHEMA).validate(data)
        normalized = lambda text: unicodedata.normalize("NFC", text)
        translation = normalized(data["translation"]).strip()
        if not 0 < len(translation) <= 4000:
            raise InvalidInterpretation("invalid_interpretation")
        source = normalized(source)
        def complete_sentence(quote, text):
            trim = lambda value: value.strip().rstrip(".!?…")
            # Whole sentences (or the whole utterance) preserve their governing
            # negation. A bare action excerpt is not sufficient evidence.
            return any(trim(quote) == trim(sentence) for sentence in
                       [text, *re.split(r"(?<=[.!?])\s+", text)])
        for field, part in note_parts(data["lesson_note"]):
            if part is None:
                continue
            part["source"] = normalized(part["source"]).strip()
            part["translation"] = normalized(part["translation"]).strip()
            if (not 0 < len(part["source"]) <= 400 or not 0 < len(part["translation"]) <= 800
                    or part["source"] not in source or part["translation"] not in translation):
                raise InvalidInterpretation("invalid_interpretation")
            if field in ("heard", "change", "try") and (not complete_sentence(part["source"], source)
                    or not complete_sentence(part["translation"], translation)):
                raise InvalidInterpretation("invalid_interpretation")
        return translation, data["lesson_note"]
    except (ValueError, TypeError, ValidationError, RecursionError):
        raise InvalidInterpretation("invalid_interpretation") from None


def display_note(note):
    """Recipients receive target quotes only; source evidence stays server-side."""
    quote = lambda part: part["translation"] if part else None
    return {"heard": quote(note["heard"]), "where": {key: quote(note["where"][key]) for key in ("measure", "note")},
            "change": quote(note["change"]), "try": quote(note["try"])}
