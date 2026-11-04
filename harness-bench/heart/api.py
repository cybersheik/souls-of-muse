"""FastAPI-сервис журнала «сердца» (§7 хандоффа): порт 8010, за Caddy.

Запуск: uvicorn heart.api:app --port 8010
  HEART_SERVER_TOKEN — серверный токен для POST /heart/events (env, обязателен);
  HEART_DB, HEART_ED25519_KEY, HEART_PUBLISH_DIR — переопределения путей.

Часы (Wear OS) — только отображение: опрос GET /heart/{soul_id} раз в 15 мин;
локального состояния счётчиков на клиентах нет (T-08, §3.7).
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from . import anchor, journal

app = FastAPI(title="Souls of Muse · Heart journal", version="0.1.0")

_con = None


def db():
    global _con
    if _con is None:
        _con = journal.init_db()
    return _con


def auth(x_heart_token: str | None = Header(default=None)) -> bool:
    want = os.environ.get("HEART_SERVER_TOKEN", "")
    if not want or x_heart_token != want:
        raise HTTPException(401, "недействительный серверный токен")
    return True


@app.post("/heart/events")
def post_event(event: dict, _auth: bool = Depends(auth)):
    """Приём события Harness (внутренний). Отказ → 422 с reason/detail."""
    try:
        return journal.append_event(db(), event)
    except journal.Rejected as r:
        raise HTTPException(422, {"reason": r.reason, "detail": r.detail})


@app.get("/heart/public/root/latest")
def latest_root():
    """Последний опубликованный Merkle-корень — для внешних проверяющих."""
    row = db().execute(
        "SELECT day_utc, root_hash, count_events, signature, publish_url"
        " FROM daily_roots ORDER BY day_utc DESC LIMIT 1").fetchone()
    if not row:
        raise HTTPException(404, "корней ещё не публиковалось")
    return dict(row)


@app.get("/heart/{soul_id}")
def heart_state(soul_id: str):
    """Состояние «сердца» для циферблата: три числа + хвост цепочки, без содержимого."""
    con = db()
    state = journal.counters(con, soul_id)
    return {"soul_id": soul_id, **state, "tail": journal.tail_of_chain(con)}


@app.get("/heart/{soul_id}/proof")
def proof(soul_id: str, seq: int = Query(...)):
    """Inclusion-proof записи seq к опубликованному корню её суток."""
    con = db()
    row = con.execute("SELECT soul_id FROM heart_events WHERE seq=?", (seq,)).fetchone()
    if not row or row["soul_id"] != soul_id:
        raise HTTPException(404, "запись не найдена для этого soul_id")
    return anchor.proof_for_seq(con, seq)
