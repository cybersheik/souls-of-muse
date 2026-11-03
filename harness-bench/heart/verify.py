"""verify.py — независимая проверка цепочки и дневных Merkle-корней (§5).

Пересчитывает всю цепочку (prev_hash-связность + подписи Ed25519) и сверяет
Merkle-корни суток с опубликованными. Вывод: OK или первый битый seq.

Запуск из корня стенда:
  python3 -m heart.verify --db data/heart.db --pubkey config/heart_public_key.txt
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from . import anchor, config, journal


def verify(db_path: str, pubkey_hex: str) -> tuple[bool, str]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubkey_hex))

    rows = con.execute("SELECT * FROM heart_events ORDER BY seq").fetchall()
    prev = journal.GENESIS_PREV
    for i, row in enumerate(rows, start=1):
        rec = dict(row)
        if rec["seq"] != i:
            return False, f"BROKEN: разрыв seq на {rec['seq']} (ожидался {i})"
        if rec["prev_hash"] != prev:
            return False, f"BROKEN seq={rec['seq']}: prev_hash не сходится"
        rh = journal.record_hash_of(rec)
        if not journal.check_signature(pub, rh, rec["signature"]):
            return False, f"BROKEN seq={rec['seq']}: подпись невалидна"
        prev = rh

    for r in con.execute("SELECT * FROM daily_roots ORDER BY day_utc").fetchall():
        leaves, _ = anchor.day_leaves(con, r["day_utc"])
        if len(leaves) != r["count_events"]:
            return False, f"ROOT MISMATCH day={r['day_utc']}: count {len(leaves)} != {r['count_events']}"
        if leaves and anchor.merkle_root(leaves) != r["root_hash"]:
            return False, f"ROOT MISMATCH day={r['day_utc']}"
        if not journal.check_signature(pub, r["root_hash"], r["signature"]):
            return False, f"ROOT SIGN INVALID day={r['day_utc']}"

    return True, "OK"


def main() -> None:
    ap = argparse.ArgumentParser(description="Проверка журнала «сердца» Souls of Muse")
    ap.add_argument("--db", default=None, help="путь к heart.db (default: config.db_path())")
    ap.add_argument("--pubkey", default=None, help="файл с публичным ключом hex")
    args = ap.parse_args()
    db = args.db or config.db_path()
    pub = Path(args.pubkey or config.pubkey_path()).read_text(encoding="utf-8").strip()
    ok, msg = verify(db, pub)
    print(msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
