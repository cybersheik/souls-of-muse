"""Explicit upstream fixtures; never use the production decoder to build expected data."""
import json


def interpretation_text(translation, lesson_note=None):
    if lesson_note is None:
        lesson_note = {"heard": None, "where": {"measure": None, "note": None}, "change": None, "try": None}
    return json.dumps({"translation": translation, "lesson_note": lesson_note}, ensure_ascii=False)
