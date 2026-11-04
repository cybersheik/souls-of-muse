"""Тесты журнала «сердца» — приёмка §8.6 и §10 хандоффа v1.1.

(а) 3 урока подряд → цепочка валидна, счётчики верны;
(б) правка байта в записи → verify ловит seq; триггер append-only держит UPDATE;
(в) повторная доставка event_id → без дубля (T-08);
(г) превышение лимита пары за неделю → отказ с записью причины;
(д) Merkle inclusion-proof для случайных 10 записей.
"""
import random
import sqlite3
import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from heart import anchor, journal, verify


@pytest.fixture()
def env(tmp_path, monkeypatch):
    db = tmp_path / "heart.db"
    monkeypatch.setenv("HEART_DB", str(db))
    monkeypatch.setenv("HEART_PUBLISH_DIR", str(tmp_path / "anchors"))
    priv = Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    con = journal.init_db(str(db))
    return con, priv, pub_hex, str(db)


def ev(type_, actor, soul, cp):
    return {
        "event_id": str(uuid.uuid4()),
        "lesson_id": f"L-{uuid.uuid4().hex[:8]}",
        "seq": 1,
        "ts": "2026-10-31T08:00:00Z",
        "type": type_,
        "actor": actor,
        "payload": {"soul_id": soul, "counterparty": cp},
    }


def test_a_three_lessons_chain_valid(env):
    con, priv, pub, db = env
    for cp in ("learnerA", "learnerB", "learnerC"):
        journal.append_event(con, ev("lesson.completed", "server", "mentorM", cp), priv)
    journal.append_event(con, ev("badge.awarded", "learner", "mentorM", "learnerA"), priv)
    journal.append_event(con, ev("badge.awarded", "mentor", "learnerA", "mentorM"), priv)

    c = journal.counters(con, "mentorM")
    assert (c["happened"], c["useful"], c["progress"]) == (3, 1, 0)
    assert journal.counters(con, "learnerA")["progress"] == 1

    ok, msg = verify.verify(db, pub)
    assert ok, msg

    # убывающий вес повторных сессий (§3.6) записан в payload
    rows = con.execute(
        "SELECT payload_json FROM heart_events WHERE kind='happened' ORDER BY seq").fetchall()
    assert '"weight":1' in rows[0]["payload_json"]


def test_b_tamper_is_caught(env):
    con, priv, pub, db = env
    journal.append_event(con, ev("lesson.completed", "server", "M", "A"), priv)
    journal.append_event(con, ev("lesson.completed", "server", "M", "B"), priv)

    # обычная правка запрещена триггером append-only
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE heart_events SET kind='useful' WHERE seq=1")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("DELETE FROM heart_events WHERE seq=1")

    # атакующий с доступом к файлу снимает триггер — verify обязан поймать
    con.execute("DROP TRIGGER heart_no_update")
    con.execute("UPDATE heart_events SET kind='useful' WHERE seq=1")
    ok, msg = verify.verify(db, pub)
    assert not ok
    assert "seq=1" in msg


def test_c_idempotent_redelivery(env):
    con, priv, pub, db = env
    e = ev("lesson.completed", "server", "M", "A")
    r1 = journal.append_event(con, e, priv)
    r2 = journal.append_event(con, e, priv)
    assert r1["status"] == "appended"
    assert r2["status"] == "duplicate" and r2["seq"] == r1["seq"]
    n = con.execute("SELECT COUNT(*) c FROM heart_events").fetchone()["c"]
    assert n == 1


def test_d_pair_weekly_limit(env, monkeypatch):
    con, priv, pub, db = env
    monkeypatch.setenv("HEART_PAIR_WEEKLY_LIMIT", "3")
    for _ in range(3):
        journal.append_event(con, ev("lesson.completed", "server", "M", "A"), priv)
    with pytest.raises(journal.Rejected) as ei:
        journal.append_event(con, ev("lesson.completed", "server", "M", "A"), priv)
    assert ei.value.reason == "pair_weekly_limit"

    n = con.execute(
        "SELECT COUNT(*) c FROM heart_events WHERE kind='happened'").fetchone()["c"]
    assert n == 3  # счётчик не вырос
    rej = con.execute(
        "SELECT * FROM heart_rejections WHERE reason='pair_weekly_limit'").fetchall()
    assert len(rej) == 1 and "M×A" in rej[0]["detail"]

    # другая пара не затронута лимитом
    r = journal.append_event(con, ev("lesson.completed", "server", "M", "B"), priv)
    assert r["status"] == "appended"

    # невалидное событие тоже журналируется как отказ, не попадая в цепочку
    with pytest.raises(journal.Rejected):
        journal.append_event(con, {"event_id": "x", "type": "lesson.completed"}, priv)
    kinds = con.execute(
        "SELECT COUNT(DISTINCT reason) c FROM heart_rejections").fetchone()["c"]
    assert kinds >= 2


def test_e_merkle_inclusion_random_10(env):
    con, priv, pub, db = env
    for i in range(12):
        journal.append_event(
            con, ev("lesson.completed", "server", f"M{i % 3}", f"L{i}"), priv)
    day = journal.utc_now()[:10]
    out = anchor.anchor_day(con, day, priv)

    leaves, _ = anchor.day_leaves(con, day)
    random.seed(7)
    for idx in random.sample(range(12), 10):
        proof = anchor.inclusion_proof(leaves, idx)
        assert anchor.verify_inclusion(leaves[idx], proof, out["root_hash"])

    # подменённый лист не проходит проверку
    bad = "ff" * 32
    assert not anchor.verify_inclusion(
        bad, anchor.inclusion_proof(leaves, 0), out["root_hash"])

    # verify() сверяет опубликованный корень суток и его подпись
    ok, msg = verify.verify(db, pub)
    assert ok, msg

    # proof через модульное API anchor.proof_for_seq
    p = anchor.proof_for_seq(con, 5)
    assert p["anchored"] and p["root_hash"] == out["root_hash"]
    assert anchor.verify_inclusion(p["record_hash"], p["proof"], p["root_hash"])
