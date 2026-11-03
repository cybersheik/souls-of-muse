"""Participant-scoped push-to-talk transcription with durable replay protection."""
import base64
import binascii
import hashlib
import tempfile

from fastapi import Header, Request
from pydantic import BaseModel, Field

from harness.adapters.meta import ConfigError, MetaAPIError, MetaResponseError, MetaTransportError
from harness.budget import BudgetExceeded
from harness.music_vocabulary import recognition_keywords

class Transcription(BaseModel):
    client_event_id: str = Field(min_length=1, max_length=120)
    language: str
    wav_base64: str = Field(min_length=60, max_length=900_000)


def install_voice(app, db, commit, authorize, get_session, err, adapter, gate, data_dir, glossary, *, music_hints=False):
    # Keep the earlier recognition behaviour until a broader speech evaluation
    # establishes that music hints improve it. The fixed synthetic corpus has
    # mixed results, so only an operator can opt into the experiment.
    legacy = sorted({form for term in glossary for lang in ("en", "vi")
                     for form in (term[lang] if isinstance(term[lang], list) else [term[lang]])
                     if isinstance(form, str) and len(form) <= 100})[:200]
    keywords = {language: recognition_keywords(glossary, language) if music_hints else legacy
                for language in ("en", "vi")}
    c = db()
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS transcriptions(
            session_id TEXT NOT NULL, client_event_id TEXT NOT NULL, request_hash TEXT NOT NULL,
            state TEXT NOT NULL, transcript TEXT, PRIMARY KEY(session_id,client_event_id))""")
        commit(c)
    finally:
        c.close()

    @app.post("/sessions/{sid}/transcriptions")
    def transcribe(sid: str, body: Transcription, request: Request, authorization: str = Header(default="")):
        actor, error = authorize(authorization, request)
        if error:
            return error
        if body.language not in ("en", "vi"):
            return err(422, "unsupported_language")
        if not adapter or not getattr(adapter, "asr_enabled", False):
            return err(503, "asr_not_enabled")
        try:
            audio = base64.b64decode(body.wav_base64, validate=True)
        except (ValueError, binascii.Error):
            return err(422, "invalid_audio")
        request_hash = hashlib.sha256(body.language.encode() + b":" + audio).hexdigest()
        # Scope idempotence to the authenticated speaker as well as meeting.
        event_id = (getattr(request.state, "participant", None) or actor) + ":" + body.client_event_id
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            session = get_session(c, sid, request)
            if not session:
                return err(404, "session_not_found")
            if session["state"] != "active":
                return err(409, "session_not_active")
            row = c.execute("SELECT * FROM transcriptions WHERE session_id=? AND client_event_id=?", (sid, event_id)).fetchone()
            if row:
                if row["request_hash"] != request_hash:
                    return err(409, "idempotency_conflict")
                if row["state"] == "completed":
                    return {"text": row["transcript"], "language": body.language}
                return err(409, "transcription_in_progress") if row["state"] == "processing" else err(502, "transcription_failed")
            c.execute("INSERT INTO transcriptions VALUES(?,?,?,'processing',NULL)", (sid, event_id, request_hash))
            commit(c)
        finally:
            c.close()
        result = None
        status, reason = 502, "transcription_failed"
        if gate.acquire(timeout=30):
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", dir=data_dir) as recording:
                    recording.write(audio)
                    recording.flush()
                    result = adapter.transcribe(recording.name, keywords=keywords[body.language],
                                                language_bias=["English" if body.language == "en" else "Vietnamese"])
                if not isinstance(result.get("text"), str) or len(result["text"]) > 2000:
                    result = None
            except ConfigError:
                status, reason = 422, "unsupported_audio"
            except BudgetExceeded:
                status, reason = 429, "budget_exceeded"
            except (MetaAPIError, MetaResponseError, MetaTransportError):
                pass
            finally:
                gate.release()
        else:
            status, reason = 503, "inference_busy"
        c = db()
        try:
            c.execute("UPDATE transcriptions SET state=?,transcript=? WHERE session_id=? AND client_event_id=?",
                      ("completed" if result is not None else "failed", result["text"] if result is not None else None, sid, event_id))
            commit(c)
        finally:
            c.close()
        return {"text": result["text"], "language": body.language} if result is not None else err(status, reason)
    return transcribe
