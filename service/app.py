"""Souls of Muse — minimal real Harness backend (vertical slice).

Only text EN<->VI interpretation via harness-bench MetaAdapter
(/chat/completions, muse-spark-1.3) is implemented. No /responses, ASR,
SAM, TTS, media, watches, registration or votes.
Fail-closed: no auto-created budget ledger, no default pilot token,
role credentials are derived from the Authorization token only.
Author: Meta Muse Wonder.
"""
import hashlib, hmac, json, os, sqlite3, sys, threading, time, uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

VERSION = "0.2.0"
LEAGUES = {"guitar", "keys", "winds", "drums", "electronic", "voice", "folk"}
KINDS = {"individual", "group", "stream"}
LANGS = {"en", "vi"}
ALLOWED_ORIGINS = ["https://preview.soulsofmuse.com", "https://soulsofmuse.com"]
MAX_TEXT = 2000
MAX_BODY = 32768
MAX_RESPONSE_CHARS = 4000
MIN_TOKEN_LEN = 16
PILOT_TOTAL_MAX_MICRO = 1_000_000
PILOT_STOP_MAX_MICRO = 950_000
_HERE = Path(__file__).resolve().parent
_BENCH = _HERE.parent / "harness-bench"
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

SYSTEM_PROMPT = (
    "You are the Souls of Muse interpreter in a teacher-led music lesson. "
    "Translate faithfully between English and Vietnamese. Preserve the teacher's "
    "instruction exactly in meaning: keep all numbers, note names, musical "
    "terminology and negations. Use a soft, respectful tone. Do not add advice, "
    "do not invent any evaluation of a performance, do not summarise. "
    "Output only the translated text."
)

def _now():
    return datetime.now(timezone.utc).isoformat()

def _hash_event(prev, payload):
    return hashlib.sha256((prev + "|" + json.dumps(payload, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()

def _request_hash(body):
    canon = {"speaker": body.speaker, "text": body.text, "source_lang": body.source_lang, "target_lang": body.target_lang}
    return hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

class PersistenceError(RuntimeError):
    """Durable write (e.g. Volume.commit) could not be verified."""

class PersistentBudgetGuard:
    """Persistence-aware proxy around the real BudgetGuard.

    reserve_chat: real reserve -> successful on_write -> return id.
    A persistence failure raises before any paid HTTP call can happen.
    settle: real settle -> successful on_write -> return cost.
    A persistence failure raises; the durable (volume) snapshot still
    holds the conservative HOLD because it was never committed.
    Without on_write (local disk) this is a transparent proxy.

    Exception paths that mutate the ledger must also be persisted:
    the real settle() writes BLOCKED (committed locally) and then
    raises BudgetExceeded when usage exceeds the reservation. If
    _persist were skipped there, a cloud restart would see only the
    old HOLD and lose the global block. So settle (and reserve, on
    the same principle if it ever writes before raising) persists
    on both success and exception: the original exception is
    re-raised after a successful persist, and a persistence failure
    raises PersistenceError instead (fail-closed).
    """
    def __init__(self, guard, on_write=None):
        object.__setattr__(self, "_guard", guard)
        object.__setattr__(self, "_on_write", on_write)
    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_guard"), name)
    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_guard"), name, value)
    def _persist(self):
        cb = object.__getattribute__(self, "_on_write")
        if cb is not None:
            try:
                cb()
            except Exception as exc:
                raise PersistenceError("durable commit failed") from exc
    def reserve_chat(self, model, max_input_tokens, max_output_tokens):
        try:
            rid = object.__getattribute__(self, "_guard").reserve_chat(model, max_input_tokens, max_output_tokens)
        except Exception:
            # Persist any BLOCKED/mutation written before the raise;
            # PersistenceError from _persist propagates (fail-closed),
            # otherwise the original exception is preserved.
            self._persist()
            raise
        self._persist()  # raises before HTTP on failure
        return rid
    # alias used by some callers
    def reserve(self, model, max_input_tokens, max_output_tokens):
        return self.reserve_chat(model, max_input_tokens, max_output_tokens)
    def settle(self, reservation_id, model, usage):
        try:
            cost = object.__getattribute__(self, "_guard").settle(reservation_id, model, usage)
        except Exception:
            self._persist()
            raise
        self._persist()  # on failure durable HOLD is retained (never committed away)
        return cost
    def settle_chat(self, reservation_id, model, usage):
        return self.settle(reservation_id, model, usage)

class BodyLimitMiddleware:
    """ASGI middleware enforcing MAX_BODY on actual streamed bytes.

    Counts every http.request chunk (chunked / missing Content-Length
    included) and aborts with 413 past the limit before the app parses.
    """
    def __init__(self, app, max_body=MAX_BODY):
        self.app = app; self.max_body = max_body
    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send); return
        chunks = []; total = 0
        while True:
            msg = await receive()
            if msg.get("type") == "http.request":
                body = msg.get("body", b"") or b""
                total += len(body)
                if total > self.max_body:
                    await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json")]})
                    await send({"type": "http.response.body", "body": b'{"detail":"request_too_large"}'})
                    return
                chunks.append(msg)
                if not msg.get("more_body"):
                    break
            elif msg.get("type") == "http.disconnect":
                chunks.append(msg); break
            else:
                chunks.append(msg)
        it = iter(chunks)
        async def replay():
            try:
                return next(it)
            except StopIteration:
                return {"type": "http.request", "body": b"", "more_body": False}
        await self.app(scope, replay, send)

def verify_audit_chain(conn):
    """Recompute the hash-linked audit chain. Returns (valid, count)."""
    rows = conn.execute("SELECT session_id,event_type,ref_id,actor,prev_hash,hash,created_at FROM audit ORDER BY id").fetchall()
    prev = "GENESIS"
    for r in rows:
        if r[4] != prev:
            return False, len(rows)
        payload = {"session_id": r[0], "event_type": r[1], "ref_id": r[2], "actor": r[3], "at": r[6]}
        if _hash_event(prev, payload) != r[5]:
            return False, len(rows)
        prev = r[5]
    return True, len(rows)

class SessionIn(BaseModel):
    kind: str; league: str; maestro_alias: str = Field(min_length=1, max_length=80)
    artist_alias: str = Field(min_length=1, max_length=80); source_lang: str; target_lang: str

class MessageIn(BaseModel):
    client_event_id: str = Field(min_length=1, max_length=120); speaker: str
    text: str = Field(min_length=1, max_length=MAX_TEXT); source_lang: str; target_lang: str

class ApproveIn(BaseModel):
    confirm_flagged: bool = False

def _build_real_adapter(data_dir, environ, on_write=None, transport=None):
    """Return (adapter, ready). Never creates a budget ledger.

    Budget config defaults to <data_dir>/budget.yaml (the provisioned
    pilot config). SOM_BUDGET_CONFIG is honoured only if explicitly set.
    Pilot allocation is enforced: total <= $1, operational stop <= $0.95.
    """
    try:
        from harness.budget import BudgetGuard
        from harness.adapters.meta import MetaAdapter
        import yaml
    except Exception:
        return None, False
    ledger_override = environ.get("SOM_BUDGET_LEDGER") or environ.get("SERVICE_BUDGET_LEDGER")
    ledger = Path(ledger_override) if ledger_override else Path(data_dir) / "budget_ledger.sqlite3"
    if not ledger.exists():
        return None, False
    cfg_env = environ.get("SOM_BUDGET_CONFIG") or environ.get("SERVICE_BUDGET_CONFIG")
    cfg_path = Path(cfg_env) if cfg_env else Path(data_dir) / "budget.yaml"
    if not cfg_path.exists():
        return None, False
    if not environ.get("MODEL_API_KEY"):
        return None, False
    try:
        guard = BudgetGuard(str(cfg_path), ledger_path=str(ledger))
        if guard.total_micro > PILOT_TOTAL_MAX_MICRO or guard.stop_micro > PILOT_STOP_MAX_MICRO:
            return None, False
        models = yaml.safe_load((_BENCH / "config" / "models.yaml").read_text(encoding="utf-8")) or {}
        cfg = dict(models); cfg["roles"] = {"interpreter": {"model": "muse-spark-1.3", "endpoint": "/chat/completions", "reasoning_effort": "low", "temperature": 0.1, "max_tokens": 1024}}
        wrapped = PersistentBudgetGuard(guard, on_write)
        return MetaAdapter(cfg, wrapped, transport=transport, environ=environ), True
    except Exception:
        return None, False

def _load_glossary():
    try:
        from harness.validator import load_glossary
        p = _BENCH / "data" / "seed_terms.jsonl"
        return load_glossary(str(p)) if p.exists() else []
    except Exception:
        return []

def _validate_translation(src_text, src_lang, out_text, tgt_lang, glossary):
    if not glossary:
        return []
    try:
        from harness.validator import signature, compare
        return compare(signature(src_text, src_lang, glossary), signature(out_text, tgt_lang, glossary))
    except Exception:
        return []

def create_app(data_dir=None, pilot_token=None, adapter=None, environ=None, max_concurrent=1, on_write=None, maestro_token=None, artist_token=None):
    env = os.environ if environ is None else environ
    data_dir = data_dir or env.get("SERVICE_DATA_DIR") or env.get("SOM_DATA_DIR")
    if not data_dir or not Path(data_dir).is_dir():
        raise RuntimeError("SERVICE_DATA_DIR must name an existing, explicitly provisioned directory; failing closed")
    if isinstance(max_concurrent, bool) or max_concurrent != 1:
        raise RuntimeError("inference is single serialized: max_concurrent must be 1")
    # Role-bound credentials: derived from Authorization only.
    maestro_tok = maestro_token if maestro_token is not None else (env.get("SOM_MAESTRO_TOKEN") or "")
    artist_tok = artist_token if artist_token is not None else (env.get("SOM_ARTIST_TOKEN") or "")
    if pilot_token is not None and maestro_token is None:
        maestro_tok = pilot_token  # explicit legacy arg maps to Maestro only; Artist still required
    tokens_valid = bool(maestro_tok) and bool(artist_tok) and len(maestro_tok) >= MIN_TOKEN_LEN and len(artist_tok) >= MIN_TOKEN_LEN and not hmac.compare_digest(maestro_tok, artist_tok)
    model_ready = adapter is not None
    if adapter is None:
        adapter, model_ready = _build_real_adapter(data_dir, env, on_write=on_write)
    glossary = _load_glossary()
    db_path = Path(data_dir) / "service.sqlite3"
    lock = threading.Lock()
    inference_gate = threading.BoundedSemaphore(1)
    rate = {}
    conn_init = sqlite3.connect(str(db_path))
    conn_init.executescript("""
      CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, kind TEXT, league TEXT, maestro_alias TEXT, artist_alias TEXT, source_lang TEXT, target_lang TEXT, state TEXT, created_at TEXT);
      CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, session_id TEXT, client_event_id TEXT, speaker TEXT, source_text TEXT, source_lang TEXT, target_lang TEXT, draft_text TEXT, state TEXT, validation_issues TEXT, created_at TEXT, request_hash TEXT, UNIQUE(session_id, client_event_id));
      CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, event_type TEXT, ref_id TEXT, actor TEXT, prev_hash TEXT, hash TEXT, created_at TEXT);
      CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'audit_append_only'); END;
      CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit_append_only'); END;
    """)
    cols = {r[1] for r in conn_init.execute("PRAGMA table_info(messages)").fetchall()}
    if "request_hash" not in cols:
        conn_init.execute("ALTER TABLE messages ADD COLUMN request_hash TEXT")
    conn_init.commit(); conn_init.close()
    if on_write is not None:
        on_write()  # propagate: startup fails closed if durable commit fails

    def _commit(c):
        c.commit()
        if on_write is not None:
            try:
                on_write()  # failure propagates as PersistenceError; never swallowed
            except PersistenceError:
                raise
            except Exception as exc:
                raise PersistenceError("durable commit failed") from exc
    def db():
        c = sqlite3.connect(str(db_path), timeout=30); c.row_factory = sqlite3.Row; return c
    def audit(c, session_id, event_type, ref_id="", actor=""):
        prev = c.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev_h = prev[0] if prev else "GENESIS"
        payload = {"session_id": session_id, "event_type": event_type, "ref_id": ref_id, "actor": actor, "at": _now()}
        c.execute("INSERT INTO audit(session_id,event_type,ref_id,actor,prev_hash,hash,created_at) VALUES(?,?,?,?,?,?,?)",
                  (session_id, event_type, ref_id, actor, prev_h, _hash_event(prev_h, payload), payload["at"]))
    def err(status, code):
        return JSONResponse({"detail": code}, status_code=status)

    app = FastAPI(title="Souls of Muse Harness", version=VERSION)
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
    app.add_middleware(BodyLimitMiddleware)

    @app.middleware("http")
    async def bounds(request: Request, call_next):
        key = (request.client.host if request.client else "?", int(time.time() // 60))
        with lock:
            rate[key] = rate.get(key, 0) + 1; count = rate[key]
            if len(rate) > 10000: rate.clear()
        if count > 120:
            return JSONResponse({"detail": "rate_limited"}, status_code=429)
        return await call_next(request)

    def actor_from_auth(authorization):
        """Return (actor, error_response). Actor comes from token only."""
        if not tokens_valid:
            return None, err(503, "role_tokens_not_configured")
        if not authorization or not authorization.startswith("Bearer "):
            return None, err(401, "unauthorized")
        presented = authorization[len("Bearer "):]
        if hmac.compare_digest(presented, maestro_tok):
            return "maestro", None
        if hmac.compare_digest(presented, artist_tok):
            return "artist", None
        return None, err(401, "unauthorized")

    def get_session(c, sid):
        return c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    def msg_dict(r, include_draft=True):
        d = {"id": r["id"], "speaker": r["speaker"], "source_lang": r["source_lang"], "target_lang": r["target_lang"], "state": r["state"], "created_at": r["created_at"]}
        if r["state"] == "approved" or include_draft:
            d["text"] = r["draft_text"]
        if include_draft:
            d["source_text"] = r["source_text"]
            try: d["validation_issues"] = json.loads(r["validation_issues"] or "[]")
            except Exception: d["validation_issues"] = []
        return d

    @app.get("/health")
    def health():
        # Honest readiness: liveness (status ok) is not usability.
        # auth_ready/role_ready reflect the role-token configuration
        # only (private pilot tokens, not full participant identity);
        # an invalid/missing token must not look fully usable.
        auth_ready = bool(tokens_valid)
        pilot_ready = bool(auth_ready and model_ready)
        return {"status": "ok", "version": VERSION, "model_ready": bool(model_ready),
                "auth_ready": auth_ready, "role_ready": auth_ready,
                "roles_ready": auth_ready, "pilot_ready": pilot_ready,
                "production_ready": False, "full_participant_identity": False,
                "capabilities": {"text_interpretation_en_vi": bool(pilot_ready), "sessions": bool(auth_ready), "maestro_approval": bool(auth_ready), "hash_linked_audit": True,
                                 "responses": False, "asr": False, "sam": False, "tts": False, "media_rooms": False, "watches": False, "registration": False, "votes": False},
                "not_implemented": ["lessons_media", "group_media_streams", "league_interactions_beyond_text_sessions", "responses", "asr", "sam", "tts", "watches", "heart_journal_integration", "full_participant_identity", "production_readiness"]}

    @app.get("/pilot")
    def pilot():
        p = _HERE / "pilot.html"
        return FileResponse(str(p), media_type="text/html") if p.exists() else err(404, "pilot_not_found")

    @app.post("/sessions", status_code=201)
    def create_session(body: SessionIn, authorization: str = Header(default="")):
        actor, e = actor_from_auth(authorization)
        if e: return e
        if actor != "maestro": return err(403, "maestro_required")
        if body.kind not in KINDS or body.league not in LEAGUES or body.source_lang not in LANGS or body.target_lang not in LANGS or body.source_lang == body.target_lang:
            return err(422, "invalid_session_fields")
        sid = uuid.uuid4().hex
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)", (sid, body.kind, body.league, body.maestro_alias, body.artist_alias, body.source_lang, body.target_lang, "created", _now()))
            audit(c, sid, "session_created", "", actor); _commit(c)
        except PersistenceError:
            return err(503, "persistence_failed")
        finally: c.close()
        return {"id": sid, "state": "created", "kind": body.kind, "league": body.league}

    @app.post("/sessions/{sid}/start")
    def start_session(sid: str, authorization: str = Header(default="")):
        actor, e = actor_from_auth(authorization)
        if e: return e
        if actor != "maestro": return err(403, "maestro_required")
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            s = get_session(c, sid)
            if not s: return err(404, "session_not_found")
            cur = c.execute("UPDATE sessions SET state='active' WHERE id=? AND state='created'", (sid,))
            if cur.rowcount != 1: return err(409, "invalid_transition")
            audit(c, sid, "session_started", "", actor); _commit(c)
            return {"id": sid, "state": "active"}
        except PersistenceError:
            return err(503, "persistence_failed")
        finally: c.close()

    @app.post("/sessions/{sid}/complete")
    def complete_session(sid: str, authorization: str = Header(default="")):
        actor, e = actor_from_auth(authorization)
        if e: return e
        if actor != "maestro": return err(403, "maestro_required")
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            s = get_session(c, sid)
            if not s: return err(404, "session_not_found")
            if s["state"] != "active": return err(409, "invalid_transition")
            busy = c.execute("SELECT COUNT(*) FROM messages WHERE session_id=? AND state='processing'", (sid,)).fetchone()[0]
            if busy: return err(409, "session_has_processing_messages")
            cur = c.execute("UPDATE sessions SET state='completed' WHERE id=? AND state='active'", (sid,))
            if cur.rowcount != 1: return err(409, "invalid_transition")
            audit(c, sid, "session_completed", "", actor); _commit(c)
            return {"id": sid, "state": "completed"}
        except PersistenceError:
            return err(503, "persistence_failed")
        finally: c.close()

    @app.post("/sessions/{sid}/messages", status_code=201)
    def create_message(sid: str, body: MessageIn, authorization: str = Header(default="")):
        actor, e = actor_from_auth(authorization)
        if e: return e
        if body.speaker not in ("maestro", "artist") or body.source_lang not in LANGS or body.target_lang not in LANGS or body.source_lang == body.target_lang:
            return err(422, "invalid_message_fields")
        if body.speaker != actor:
            return err(403, "speaker_mismatch")
        if not model_ready or adapter is None:
            return err(503, "model_not_ready")
        req_hash = _request_hash(body)
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            s = get_session(c, sid)
            if not s: return err(404, "session_not_found")
            if s["state"] != "active": return err(409, "session_not_active")
            existing = c.execute("SELECT * FROM messages WHERE session_id=? AND client_event_id=?", (sid, body.client_event_id)).fetchone()
            if existing:
                if existing["request_hash"] is not None and not hmac.compare_digest(existing["request_hash"], req_hash):
                    return err(409, "idempotency_conflict")
                if existing["state"] == "processing": return err(409, "duplicate_in_progress")
                if existing["state"] == "failed": return err(502, "upstream_failed")
                return msg_dict(existing, include_draft=(actor == "maestro" or existing["state"] == "approved"))
            mid = uuid.uuid4().hex
            try:
                c.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (mid, sid, body.client_event_id, body.speaker, body.text, body.source_lang, body.target_lang, None, "processing", "[]", _now(), req_hash))
                audit(c, sid, "message_received", mid, actor); _commit(c)
            except sqlite3.IntegrityError:
                row = c.execute("SELECT * FROM messages WHERE session_id=? AND client_event_id=?", (sid, body.client_event_id)).fetchone()
                if row and row["request_hash"] is not None and not hmac.compare_digest(row["request_hash"], req_hash):
                    return err(409, "idempotency_conflict")
                if row and row["state"] == "processing": return err(409, "duplicate_in_progress")
                if row and row["state"] == "failed": return err(502, "upstream_failed")
                return msg_dict(row, include_draft=(actor == "maestro")) if row else err(409, "duplicate_in_progress")
        except PersistenceError:
            return err(503, "persistence_failed")
        finally: c.close()
        # Single serialized inference, bounded wait. Budget HOLD is
        # retained inside MetaAdapter on upstream failure; no retry.
        user = f"Translate from {body.source_lang} to {body.target_lang}:\n{body.text}"
        draft = None; failure = None; fail_code = "upstream_failed"
        if not inference_gate.acquire(timeout=30):
            failure = "busy"; fail_code = "inference_busy"
        else:
            try:
                result = adapter.complete("interpreter", SYSTEM_PROMPT, user)
                draft = result.get("text") if isinstance(result, dict) else None
                if not isinstance(draft, str) or not draft.strip():
                    failure = "empty"; draft = None
                elif len(draft) > MAX_RESPONSE_CHARS:
                    failure = "oversized"; fail_code = "upstream_response_too_large"; draft = None
            except PersistenceError:
                failure = "persistence"
            except Exception:
                failure = "upstream"
            finally:
                inference_gate.release()
        if failure is not None:
            c = db()
            try:
                c.execute("BEGIN IMMEDIATE")
                c.execute("UPDATE messages SET state='failed' WHERE id=? AND state='processing'", (mid,))
                audit(c, sid, "interpretation_failed", mid, actor); _commit(c)
            except PersistenceError:
                return err(503, "persistence_failed")
            finally: c.close()
            if failure == "persistence":
                return err(503, "persistence_failed")
            if fail_code == "inference_busy":
                return err(429, fail_code)
            return err(502, fail_code)
        issues = _validate_translation(body.text, body.source_lang, draft, body.target_lang, glossary)
        state = "flagged" if issues else "draft"
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            s = get_session(c, sid)
            row0 = c.execute("SELECT * FROM messages WHERE id=?", (mid,)).fetchone()
            if not s or s["state"] != "active" or not row0 or row0["state"] != "processing":
                # Session completed meanwhile: never persist/deliver a draft.
                c.execute("UPDATE messages SET state='failed' WHERE id=? AND state='processing'", (mid,))
                audit(c, sid, "draft_discarded_session_not_active", mid, actor); _commit(c)
                return err(409, "session_not_active")
            cur = c.execute("UPDATE messages SET draft_text=?, state=?, validation_issues=? WHERE id=? AND state='processing'", (draft, state, json.dumps(issues, ensure_ascii=False), mid))
            if cur.rowcount != 1: return err(409, "invalid_transition")
            audit(c, sid, "draft_flagged" if issues else "draft_created", mid, actor); _commit(c)
            row = c.execute("SELECT * FROM messages WHERE id=?", (mid,)).fetchone()
            return msg_dict(row, include_draft=(actor == "maestro" or row["state"] == "approved"))
        except PersistenceError:
            return err(503, "persistence_failed")
        finally: c.close()

    @app.post("/sessions/{sid}/messages/{mid}/approve")
    def approve(sid: str, mid: str, body: ApproveIn = None, authorization: str = Header(default="")):
        actor, e = actor_from_auth(authorization)
        if e: return e
        if actor != "maestro": return err(403, "maestro_approval_required")
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            s = get_session(c, sid)
            if not s: return err(404, "session_not_found")
            if s["state"] == "completed": return err(409, "session_completed")
            r = c.execute("SELECT * FROM messages WHERE id=? AND session_id=?", (mid, sid)).fetchone()
            if not r: return err(404, "message_not_found")
            if r["state"] == "flagged" and not (body and body.confirm_flagged):
                return err(409, "flagged_requires_maestro_confirmation")
            if r["state"] not in ("draft", "flagged"): return err(409, "invalid_transition")
            cur = c.execute("UPDATE messages SET state='approved' WHERE id=? AND session_id=? AND state IN ('draft','flagged')", (mid, sid))
            if cur.rowcount != 1: return err(409, "invalid_transition")
            audit(c, sid, "message_approved", mid, actor); _commit(c)
            row = c.execute("SELECT * FROM messages WHERE id=?", (mid,)).fetchone()
            return msg_dict(row)
        except PersistenceError:
            return err(503, "persistence_failed")
        finally: c.close()

    @app.get("/sessions/{sid}")
    def get_one(sid: str, authorization: str = Header(default="")):
        actor, e = actor_from_auth(authorization)
        if e: return e
        include_draft = (actor == "maestro")
        c = db()
        try:
            s = get_session(c, sid)
            if not s: return err(404, "session_not_found")
            rows = c.execute("SELECT * FROM messages WHERE session_id=? ORDER BY created_at", (sid,)).fetchall()
            deliveries = [msg_dict(r, include_draft=include_draft) for r in rows if r["state"] == "approved" or include_draft]
            return {"id": sid, "state": s["state"], "kind": s["kind"], "league": s["league"], "maestro_alias": s["maestro_alias"], "artist_alias": s["artist_alias"], "deliveries": deliveries}
        finally: c.close()

    @app.get("/sessions/{sid}/events")
    def events(sid: str, authorization: str = Header(default="")):
        actor, e = actor_from_auth(authorization)
        if e: return e
        c = db()
        try:
            if not get_session(c, sid): return err(404, "session_not_found")
            rows = c.execute("SELECT event_type, ref_id, actor, hash, created_at FROM audit WHERE session_id=? ORDER BY id", (sid,)).fetchall()
            return {"events": [dict(r) for r in rows]}
        finally: c.close()

    @app.get("/sessions/{sid}/audit/verify")
    def audit_verify(sid: str, authorization: str = Header(default="")):
        actor, e = actor_from_auth(authorization)
        if e: return e
        if actor != "maestro": return err(403, "maestro_required")
        c = db()
        try:
            if not get_session(c, sid): return err(404, "session_not_found")
            valid, count = verify_audit_chain(c)
            return {"valid": valid, "events": count, "scope": "service_audit_hash_linked"}
        finally: c.close()

    return app

app = None  # No import-time app: provisioning must be explicit. Use create_app.
