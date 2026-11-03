"""Пути и константы модуля heart (AI3-901).

Константы анти-накрутки — по §3.6 хандоффа; числовые значения подлежат
подтверждению ТУЗ/Aidar перед заделкой как финальные (§11 хандоффа).
"""
import os
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parent.parent


def db_path() -> str:
    return os.environ.get("HEART_DB", str(BENCH_ROOT / "data" / "heart.db"))


def default_key_path() -> str:
    # приватный ключ: файл 0600 ВНЕ репозитория/стенда (§3.2 хандоффа)
    return str(BENCH_ROOT.parent / ".secrets" / "heart_ed25519.pem")


def pubkey_path() -> str:
    return str(BENCH_ROOT / "config" / "heart_public_key.txt")


def schema_path() -> str:
    return str(BENCH_ROOT / "schemas" / "event.schema.json")


def publish_dir() -> str:
    return os.environ.get("HEART_PUBLISH_DIR", str(BENCH_ROOT / "data" / "heart_anchors"))


def pair_weekly_limit() -> int:
    # default 3 — НЕ подтверждён; финальное число за ТУЗ/Aidar (AI3-901, §11)
    return int(os.environ.get("HEART_PAIR_WEEKLY_LIMIT", "3"))
