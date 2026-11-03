"""Merkle-анкеринг суток UTC и публикация корня (§5, §8.4 хандоффа).

v1: публикация статическим JSON-файлом (отдаётся с сайта); GitHub Gist — при
появлении токена; публичный L2 — третье место публикации после запуска
контрактов AI3-925 (решение Айдара от 27.10).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from . import config, journal


def _h(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def merkle_root(leaves_hex: list[str]) -> str:
    """Корень над record_hash-листьями в порядке seq; нечётный узел дублируется (§5)."""
    level = [bytes.fromhex(h) for h in leaves_hex]
    if not level:
        raise ValueError("пустой набор листьев не анкорится")
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [_h(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0].hex()


def inclusion_proof(leaves_hex: list[str], index: int) -> list[tuple[str, str]]:
    """Путь (позиция 'L'/'R', hex соседа) от листа index до корня."""
    level = [bytes.fromhex(h) for h in leaves_hex]
    proof: list[tuple[str, str]] = []
    idx = index
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        sib = idx ^ 1
        proof.append(("L" if sib < idx else "R", level[sib].hex()))
        level = [_h(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        idx //= 2
    return proof


def verify_inclusion(leaf_hex: str, proof: list[tuple[str, str]], root_hex: str) -> bool:
    node = bytes.fromhex(leaf_hex)
    for pos, sib in proof:
        s = bytes.fromhex(sib)
        node = _h(s + node) if pos == "L" else _h(node + s)
    return node.hex() == root_hex


def day_leaves(con, day_utc: str) -> tuple[list[str], list]:
    rows = con.execute(
        "SELECT * FROM heart_events WHERE substr(created_utc,1,10)=? ORDER BY seq",
        (day_utc,)).fetchall()
    return [journal.record_hash_of(dict(r)) for r in rows], rows


def anchor_day(con, day_utc: str, priv=None, publish_dir: str | None = None) -> dict:
    """Merkle-корень суток → подпись → daily_roots + публикация (§8.4)."""
    priv = priv or journal.load_private_key()
    leaves, _ = day_leaves(con, day_utc)
    if not leaves:
        raise ValueError(f"за {day_utc} записей нет — анкорить нечего")
    root = merkle_root(leaves)
    sig = journal.sign_record(priv, root)
    now = journal.utc_now()
    pub_hex = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    out = {
        "day_utc": day_utc, "root_hash": root, "count_events": len(leaves),
        "signature": sig, "pubkey_hex": pub_hex, "published_at": now,
    }
    pub_dir = Path(publish_dir or config.publish_dir())
    pub_dir.mkdir(parents=True, exist_ok=True)
    pub_file = pub_dir / f"heart_root_{day_utc}.json"
    pub_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    con.execute(
        "INSERT INTO daily_roots(day_utc, root_hash, count_events, signature,"
        " published_at, publish_url) VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(day_utc) DO UPDATE SET root_hash=excluded.root_hash,"
        " count_events=excluded.count_events, signature=excluded.signature,"
        " published_at=excluded.published_at, publish_url=excluded.publish_url",
        (day_utc, root, len(leaves), sig, now, str(pub_file)))
    out["publish_url"] = str(pub_file)
    return out


def proof_for_seq(con, seq: int) -> dict:
    """Inclusion-proof записи seq к опубликованному корню её суток (§7 API)."""
    row = con.execute("SELECT * FROM heart_events WHERE seq=?", (seq,)).fetchone()
    if not row:
        raise KeyError(seq)
    day = row["created_utc"][:10]
    leaves, rows = day_leaves(con, day)
    index = [r["seq"] for r in rows].index(seq)
    root_row = con.execute("SELECT * FROM daily_roots WHERE day_utc=?", (day,)).fetchone()
    return {
        "seq": seq,
        "day_utc": day,
        "record_hash": journal.record_hash_of(dict(row)),
        "proof": inclusion_proof(leaves, index),
        "root_hash": root_row["root_hash"] if root_row else None,
        "root_signature": root_row["signature"] if root_row else None,
        "anchored": root_row is not None,
    }
