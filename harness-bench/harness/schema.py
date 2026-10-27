"""Минимальная проверка событий по schemas/event.schema.json (без внешних зависимостей)."""
import json, re
from pathlib import Path

SCHEMA = json.loads(Path("schemas/event.schema.json").read_text(encoding="utf-8"))
_TYPES = {"string": str, "integer": int, "object": dict}


def validate_event(ev):
    errors = []
    props = SCHEMA["properties"]
    for key in SCHEMA["required"]:
        if key not in ev:
            errors.append(f"нет поля {key}")
    for key, spec in props.items():
        if key not in ev:
            continue
        t = spec.get("type")
        if t and not isinstance(ev[key], _TYPES[t]):
            errors.append(f"{key}: ожидался {t}")
        if "enum" in spec and ev[key] not in spec["enum"]:
            errors.append(f"{key}: {ev[key]!r} вне enum")
    for key in ev:
        if key not in props:
            errors.append(f"лишнее поле {key}")
    if isinstance(ev.get("ts"), str) and not re.match(r"^\d{4}-\d{2}-\d{2}T", ev["ts"]):
        errors.append("ts: не ISO-8601")
    return errors
