"""Optional speech for approved translations; never accepts browser-supplied text."""
import base64
import hashlib
import io
import wave

from fastapi import Header, Request

MAX_TEXT = 400
MAX_AUDIO_BYTES = 960_100  # 30 seconds of mono PCM16 at 16 kHz, with a WAV header.


def validate_wav(audio):
    if not isinstance(audio, bytes) or not 44 < len(audio) <= MAX_AUDIO_BYTES:
        raise ValueError("invalid_speech_audio")
    with wave.open(io.BytesIO(audio), "rb") as recording:
        if (recording.getnchannels(), recording.getsampwidth(), recording.getframerate()) != (1, 2, 16000):
            raise ValueError("invalid_speech_format")
        frames = recording.getnframes()
        if not 0 < frames <= 480_000 or len(recording.readframes(frames)) != frames * 2:
            raise ValueError("invalid_speech_duration")


def install_speech(app, db, commit, authorize, get_session, err, speech, gate):
    c = db()
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS speech_audio(
            message_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, audio BLOB NOT NULL)""")
        commit(c)
    finally:
        c.close()

    @app.post("/sessions/{sid}/messages/{mid}/speech")
    def speak(sid: str, mid: str, request: Request, authorization: str = Header(default="")):
        actor, error = authorize(authorization, request)
        if error:
            return error
        c = db()
        try:
            if not get_session(c, sid, request):
                return err(404, "session_not_found")
            message = c.execute("SELECT * FROM messages WHERE id=? AND session_id=?", (mid, sid)).fetchone()
            if not message:
                return err(404, "message_not_found")
            if message["state"] != "approved":
                return err(409, "approved_translation_required")
            if speech is None:
                return err(503, "speech_not_enabled")
            text, language = message["draft_text"], message["target_lang"]
            if language not in ("en", "vi") or not text or len(text) > MAX_TEXT:
                return err(422, "unsupported_speech_text")
            digest = hashlib.sha256((speech.revision + ":" + language + ":" + text).encode()).hexdigest()
            if not gate.acquire(timeout=1):
                return err(503, "inference_busy")
            try:
                cached = c.execute("SELECT audio FROM speech_audio WHERE message_id=? AND request_hash=?", (mid, digest)).fetchone()
                audio = bytes(cached["audio"]) if cached else speech.synthesize(text, language)
                validate_wav(audio)
                if not cached:
                    c.execute("INSERT OR REPLACE INTO speech_audio VALUES(?,?,?)", (mid, digest, audio))
                    commit(c)
            except ValueError:
                return err(502, "speech_unavailable")
            except Exception:
                # Neither model diagnostics nor private paths belong in a public response.
                return err(503, "speech_unavailable")
            finally:
                gate.release()
            return {"wav_base64": base64.b64encode(audio).decode(), "language": language}
        finally:
            c.close()
