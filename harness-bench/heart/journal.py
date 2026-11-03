"""Ядро журнала «сердца»: append-only SQLite + хеш-цепочка + подпись Ed25519.

AI3-901 · хандофф v1.1 (27.10.2026). Решения §3 хандоффа менять только через
комментарий в AI3-901 и решение Айдара.

Схема БД — §4 хандоффа; криптография — §5:
  record_hash = SHA-256 канонического JSON полей (seq, event_id, lesson_id, kind,
  soul_id, counterparty, payload_hash, prev_hash, created_utc);
  подпись Ed25519 — над 32 байтами record_hash, хранится в base64.
Отказы (лимиты, невалидные события) пишутся в heart_rejections — НЕ в цепочку,
т.к. kind вне трёх счётчиков в v1 запрещён (§5, решение Айдара).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from . import config

HEART_KINDS = ("happened", "useful", "progress")
GENESIS_PREV = "0" * 64

DDL = """
CREATE TABLE IF NOT EXISTS heart_events (
  seq          INTEGER PRIMARY KEY,
  event_id     TEXT NOT NULL UNIQUE,
  lesson_id    TEXT NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('happened','useful','progress')),
  soul_id      TEXT NOT NULL,
  counterparty TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  prev_hash    TEXT NOT NULL,
  signature    TEXT NOT NULL,
  created_utc  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_heart_soul ON heart_events(soul_id);
CREATE INDEX IF NOT EXISTS idx_heart_pair ON heart_events(soul_id, counterparty, created_utc);

CREATE TABLE IF NOT EXISTS daily_roots (
  day_utc      TEXT PRIMARY KEY,
  root_hash    TEXT NOT NULL,
  count_events INTEGER NOT NULL,
  signature    TEXT NOT NULL,
  published_at TEXT,
  publish_url  TEXT
);

CREATE TABLE IF NOT EXISTS heart_rejections (
  id          INTEGER PRIMARY KEY,
  event_id    TEXT,
  reason      TEXT NOT NULL,
  detail      TEXT,
  created_utc TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS heart_no_update BEFORE UPDATE ON heart_events
BEGIN SELECT RAISE(FAIL, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS heart_no_delete BEFORE DELETE ON heart_events
BEGIN SELECT RAISE(FAIL, 'append-only'); END;
"""


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def record_hash_of(rec: dict) -> str:
    """SHA-256 канонической сериализации 9 полей записи (§5)."""
    return sha256_hex(canonical({k: rec[k] for k in (
        "seq", "event_id", "lesson_id", "kind", "soul_id",
        "counterparty", "payload_hash", "prev_hash", "created_utc")}))


class Rejected(Exception):
    """Событие не принято в журнал; причина уходит в heart_rejections."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or config.db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.isolation_level = None  # autocommit; транзакции — явные BEGIN IMMEDIATE
    con.executescript(DDL)
    return con


def load_private_key(path: str | None = None) -> Ed25519PrivateKey:
    env = os.environ.get("HEART_ED25519_KEY", "") if path is None else ""
    if env.startswith("-----BEGIN"):
        return serialization.load_pem_private_key(env.encode(), password=None)
    pem = Path(path or env or config.default_key_path()).read_bytes()
    return serialization.load_pem_private_key(pem, password=None)


def load_public_key_hex() -> str:
    return Path(config.pubkey_path()).read_text(encoding="utf-8").strip()


def sign_record(priv: Ed25519PrivateKey, record_hash: str) -> str:
    """Ed25519 над 32 байтами record_hash; base64 (§5)."""
    return base64.b64encode(priv.sign(bytes.fromhex(record_hash))).decode()


def check_signature(pub: Ed25519PublicKey, record_hash: str, signature_b64: str) -> bool:
    try:
        pub.verify(base64.b64decode(signature_b64), bytes.fromhex(record_hash))
        return True
    except Exception:
        return False


def validate_event(event: dict) -> None:
    """Валидация по единому контракту Harness schemas/event.schema.json (§6)."""
    import jsonschema

    schema = json.loads(Path(config.schema_path()).read_text(encoding="utf-8"))
    jsonschema.validate(event, schema)


def classify(event: dict) -> str | None:
    """Событие Harness → счётчик «сердца» (таблица §6 хандоффа)."""
    t, actor = event.get("type"), event.get("actor")
    if t == "lesson.completed":
        return "happened"  # сервер: обе стороны были в комнате
    if t == "badge.awarded" and actor == "learner":
        return "useful"  # ученик: «было полезно»
    if t == "badge.awarded" and actor == "mentor":
        return "progress"  # наставник: отметка прогресса
    return None


def _log_rejection(con, event_id, reason, detail, now) -> None:
    con.execute(
        "INSERT INTO heart_rejections(event_id, reason, detail, created_utc) VALUES (?,?,?,?)",
        (event_id, reason, (detail or "")[:500], now),
    )


def _pair_happened_7d(con, soul_id, counterparty, now_dt) -> int:
    since = (now_dt - timedelta(days=7)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return con.execute(
        "SELECT COUNT(*) c FROM heart_events "
        "WHERE kind='happened' AND soul_id=? AND counterparty=? AND created_utc>=?",
        (soul_id, counterparty, since),
    ).fetchone()["c"]


def append_event(con, event: dict, priv: Ed25519PrivateKey | None = None,
                 now: str | None = None) -> dict:
    """Валидация → лимиты пары → seq/prev_hash/подпись → commit (§8.3)."""
    now = now or utc_now()
    now_dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
    priv = priv or load_private_key()

    try:
        validate_event(event)
    except Exception as e:
        _log_rejection(con, event.get("event_id"), "invalid_schema", str(e), now)
        raise Rejected("invalid_schema", str(e))

    kind = classify(event)
    if kind is None:
        _log_rejection(con, event["event_id"], "not_heart_relevant", event.get("type", ""), now)
        raise Rejected("not_heart_relevant", event.get("type", ""))

    payload = dict(event.get("payload") or {})
    soul_id, counterparty = payload.get("soul_id"), payload.get("counterparty")
    if not soul_id or not counterparty:
        _log_rejection(con, event["event_id"], "missing_soul_pair",
                       "payload.soul_id и payload.counterparty обязательны", now)
        raise Rejected("missing_soul_pair")

    # идемпотентность (T-08, §3.7): повторная доставка не создаёт двойного начисления
    dup = con.execute("SELECT seq FROM heart_events WHERE event_id=?",
                      (event["event_id"],)).fetchone()
    if dup:
        return {"status": "duplicate", "seq": dup["seq"], "event_id": event["event_id"]}

    if kind == "happened":
        n7 = _pair_happened_7d(con, soul_id, counterparty, now_dt)
        limit = config.pair_weekly_limit()
        if n7 >= limit:
            _log_rejection(con, event["event_id"], "pair_weekly_limit",
                           f"пара {soul_id}×{counterparty}: {n7} начислений за 7 дней "
                           f"при лимите {limit}", now)
            raise Rejected("pair_weekly_limit", f"{n7} за 7 дней при лимите {limit}")
        n_prior = con.execute(
            "SELECT COUNT(*) c FROM heart_events WHERE kind='happened' "
            "AND soul_id=? AND counterparty=?",
            (soul_id, counterparty)).fetchone()["c"]
        # убывающий вес повторных сессий (§3.6): влияет на репутацию (L2), не на счётчик
        payload["weight"] = round(1.0 / (1 + n_prior), 6)

    payload_json = canonical(payload)
    payload_hash = sha256_hex(payload_json)

    con.execute("BEGIN IMMEDIATE")
    try:
        tail = con.execute("SELECT * FROM heart_events ORDER BY seq DESC LIMIT 1").fetchone()
        seq = (tail["seq"] + 1) if tail else 1
        prev_hash = record_hash_of(dict(tail)) if tail else GENESIS_PREV
        rec = {
            "seq": seq, "event_id": event["event_id"], "lesson_id": event["lesson_id"],
            "kind": kind, "soul_id": soul_id, "counterparty": counterparty,
            "payload_hash": payload_hash, "prev_hash": prev_hash, "created_utc": now,
        }
        rh = record_hash_of(rec)
        sig = sign_record(priv, rh)
        con.execute(
            "INSERT INTO heart_events(seq, event_id, lesson_id, kind, soul_id,"
            " counterparty, payload_hash, payload_json, prev_hash, signature, created_utc)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (seq, rec["event_id"], rec["lesson_id"], kind, soul_id, counterparty,
             payload_hash, payload_json, prev_hash, sig, now))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return {"status": "appended", "seq": seq, "record_hash": rh, "kind": kind,
            "event_id": event["event_id"]}


def counters(con, soul_id: str) -> dict:
    """Три раздельных счётчика (§3.4); единый агрегат запрещён."""
    rows = con.execute(
        "SELECT kind, COUNT(*) c FROM heart_events WHERE soul_id=? GROUP BY kind",
        (soul_id,)).fetchall()
    out = {k: 0 for k in HEART_KINDS}
    for r in rows:
        out[r["kind"]] = r["c"]
    tail = con.execute("SELECT seq FROM heart_events ORDER BY seq DESC LIMIT 1").fetchone()
    out["last_seq"] = tail["seq"] if tail else 0
    return out


def tail_of_chain(con, n: int = 3) -> list[dict]:
    rows = con.execute(
        "SELECT seq, kind, created_utc FROM heart_events ORDER BY seq DESC LIMIT ?",
        (n,)).fetchall()
    return [dict(r) for r in rows]
