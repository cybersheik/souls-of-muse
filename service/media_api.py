"""Participant-scoped media controls sharing the existing ASR/speech boundaries."""
import asyncio
import base64
import importlib.util
import logging
import time
from contextlib import closing
from pathlib import Path

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .media import MediaAuthority, MediaRooms, LiveKitRoomAPI, MediaError
from .media_transport import LiveKitTransport
from .voice import Transcription
from runtime.admission import LessonAdmission, CapacityExceeded


class MediaEvent(BaseModel):
    client_event_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")


class MediaLeave(BaseModel):
    generation: str = Field(min_length=36, max_length=36, pattern=r"^[a-f0-9-]+$")


class ParticipantMedia:
    CONNECT_GRACE = 60
    DISCONNECT_GRACE = 20
    POLL_INTERVAL = 1
    RETRY_INTERVAL = 5

    def __init__(self, rooms, transport):
        self.rooms, self.transport = rooms, transport
        self.db = self.commit = None
        self.lifecycle_locks = {}
        self.clock = time.monotonic
        self.leases = {}
        self.watcher = None
        self.stop_event = None

    @classmethod
    def from_environ(cls, env, data_dir, persist=None):
        if env.get("SOM_ENABLE_MEDIA") != "1":
            return None
        if importlib.util.find_spec("livekit.rtc") is None:
            raise RuntimeError("SOM_ENABLE_MEDIA requires service/requirements-media.txt")
        authority = MediaAuthority(env.get("SOM_LIVEKIT_URL", ""), env.get("SOM_LIVEKIT_API_KEY", ""),
                                   env.get("SOM_LIVEKIT_API_SECRET", ""))
        path = Path(env.get("SOM_MEDIA_ADMISSION_DB", ""))
        if not path.is_absolute():
            raise RuntimeError("An explicitly provisioned media admission database is required")
        admission = LessonAdmission(str(path))
        api = LiveKitRoomAPI(authority)
        rooms = MediaRooms(str(Path(data_dir) / "media.sqlite3"), admission, authority, api, persist)
        return cls(rooms, LiveKitTransport(authority, api))

    def lifecycle_lock(self,sid):
        return self.lifecycle_locks.setdefault(sid,asyncio.Lock())

    async def enter(self,sid,members):
        async with self.lifecycle_lock(sid):
            try:
                await self.transport.check_manual_creation()
                record=await self.rooms.open(sid,members)
                await self.transport.ensure(record)
                lease = self.observe(record)
                # A successful join grants time to use its freshly issued
                # capabilities; browser connection follows this response.
                lease["opened"] = self.clock()
                if lease["users_seen"]:
                    lease["missing_since"] = self.clock()
                return record
            finally:
                record = self.rooms.state(sid)
                if record and record["state"] != "closed":
                    self.observe(record)

    def observe(self, record, now=None):
        sid = record["session_id"]
        lease = self.leases.get(sid)
        if not lease or lease["epoch"] != record["epoch"]:
            lease = {"epoch": record["epoch"], "opened": self.clock() if now is None else now,
                     "users_seen": set(), "missing_since": None, "retry_at": 0}
            self.leases[sid] = lease
        return lease

    async def reap(self):
        with closing(self.rooms.db()) as connection:
            ids = [r[0] for r in connection.execute("SELECT session_id FROM media_sessions WHERE state!='closed'")]
        for sid in list(self.leases):
            if sid not in ids:
                self.leases.pop(sid, None)
        for sid in ids:
            async with self.lifecycle_lock(sid):
                now = self.clock()
                record = self.rooms.state(sid)
                if not record or record["state"] == "closed":
                    continue
                lease = self.observe(record, now)
                present = self.transport.client_presence(record)
                lease["users_seen"].update(user for user, direction in present)
                expected = {(user, direction) for user in lease["users_seen"] for direction in ("ingress", "playback")}
                if expected and expected - present:
                    if lease["missing_since"] is None:
                        lease["missing_since"] = now
                else:
                    lease["missing_since"] = None
                expired = (record["state"] == "closing"
                    or (not expected and now - lease["opened"] >= self.CONNECT_GRACE)
                    or (lease["missing_since"] is not None and now - lease["missing_since"] >= self.DISCONNECT_GRACE))
                if expired and now >= lease["retry_at"]:
                    try:
                        await self.close_owned(sid, expected_epoch=record["epoch"])
                    except Exception:
                        # Capacity stays reserved until verified deletion.
                        lease["retry_at"] = self.clock() + self.RETRY_INTERVAL

    def start(self):
        if self.watcher is None:
            self.stop_event = asyncio.Event()
            self.watcher = asyncio.create_task(self.watch_presence())

    async def watch_presence(self):
        while not self.stop_event.is_set():
            try:
                await asyncio.wait_for(self.stop_event.wait(), self.POLL_INTERVAL)
            except asyncio.TimeoutError:
                pass
            if self.stop_event.is_set():
                break
            try:
                await self.reap()
            except Exception:
                logging.getLogger(__name__).warning("Media lease check failed; admission remains reserved")

    async def close(self, sid, expected_epoch=None):
        async with self.lifecycle_lock(sid):
            return await self.close_owned(sid, expected_epoch)

    async def close_owned(self, sid, expected_epoch=None):
        # Caller holds this session's lifecycle lock, including lease rechecks.
        record = self.rooms.state(sid)
        if record and expected_epoch and record["epoch"] != expected_epoch:
            return False
        if record:
            await self.transport.disconnect(record["epoch"])
        if self.db:
            with closing(self.db()) as connection:
                connection.execute("UPDATE media_recordings SET state='cancelled' WHERE session_id=? AND state='capturing'", (sid,))
                self.commit(connection)
        closed = await self.rooms.close(sid,expected_epoch)
        if closed:
            self.leases.pop(sid, None)
        return closed

    async def logout(self, user):
        with closing(self.rooms.db()) as connection:
            ids = [r[0] for r in connection.execute("SELECT session_id FROM media_sessions WHERE state!='closed'")]
        failures = []
        for sid in ids:
            record = self.rooms.state(sid)
            if user in record["members"]:
                try: await self.close(sid)
                except Exception: failures.append(sid)
        if failures: raise MediaError("media_cleanup_pending")

    async def shutdown(self):
        if self.watcher is not None:
            # Drain in-flight native teardown rather than cancelling it midway.
            if self.stop_event is not None:
                self.stop_event.set()
            await self.watcher
            self.watcher = None
        with closing(self.rooms.db()) as connection:
            ids=[r[0] for r in connection.execute("SELECT session_id FROM media_sessions")]
        failures=[]
        for sid in ids:
            try:await self.close(sid)
            except Exception:failures.append(sid)
        if failures:raise MediaError("media_shutdown_cleanup_pending")

    def busy(self, sid):
        record = self.rooms.state(sid)
        return bool(record and self.transport.busy(record["epoch"]))

    def reconcile(self, sid):
        with closing(self.db()) as connection:
            rows=connection.execute("SELECT * FROM media_recordings WHERE session_id=? AND state IN ('capturing','processing')",(sid,)).fetchall()
            record=self.rooms.state(sid)
            for row in rows:
                if row["state"]=="capturing" and time.time()-row["started"]>30:
                    if record:self.transport.cancel_capture(record["epoch"],row["participant"],row["event_id"])
                    connection.execute("UPDATE media_recordings SET state='cancelled' WHERE session_id=? AND participant=? AND event_id=?",(sid,row["participant"],row["event_id"]))
                if row["state"]=="processing":
                    completed=connection.execute("SELECT state,transcript FROM transcriptions WHERE session_id=? AND client_event_id=?",(sid,row["participant"]+":rtc-"+row["event_id"])).fetchone()
                    if completed and completed["state"] in ("completed","failed"):
                        connection.execute("UPDATE media_recordings SET state=?,transcript=? WHERE session_id=? AND participant=? AND event_id=?",(completed["state"],completed["transcript"],sid,row["participant"],row["event_id"]))
            self.commit(connection)

    def bind(self, app, db, commit, authorize, get_session, err, transcribe, speak):
        self.db, self.commit = db, commit
        with closing(db()) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS media_recordings(
                    session_id TEXT, participant TEXT, event_id TEXT, state TEXT,
                    started REAL NOT NULL, transcript TEXT, PRIMARY KEY(session_id,participant,event_id));
                CREATE TABLE IF NOT EXISTS media_deliveries(
                    session_id TEXT, participant TEXT, event_id TEXT, message_id TEXT,
                    state TEXT, PRIMARY KEY(session_id,participant,event_id));
            """)
            commit(connection)

        # App construction occurs only after exclusive writer ownership (the
        # existing Modal permit, or one local orchestrator). Old raw PCM is not
        # persisted. An interrupted playback is uncertain, never auto-replayed.
        # Interrupted RTC ASR retains every budget HOLD; no usage is invented.
        with closing(db()) as connection:
            connection.execute("UPDATE media_deliveries SET state='unconfirmed' WHERE state='processing'")
            connection.execute("UPDATE media_recordings SET state='cancelled' WHERE state='capturing'")
            abandoned=connection.execute("SELECT * FROM media_recordings WHERE state='processing'").fetchall()
            for row in abandoned:
                event_id=row["participant"]+":rtc-"+row["event_id"]
                transcript=connection.execute("SELECT * FROM transcriptions WHERE session_id=? AND client_event_id=?",(row["session_id"],event_id)).fetchone()
                state=transcript["state"] if transcript and transcript["state"] in ("completed","failed") else "unconfirmed"
                if transcript and transcript["state"]=="processing":
                    connection.execute("UPDATE transcriptions SET state='failed' WHERE session_id=? AND client_event_id=? AND state='processing'",(row["session_id"],event_id))
                connection.execute("UPDATE media_recordings SET state=?,transcript=? WHERE session_id=? AND participant=? AND event_id=?",(state,transcript["transcript"] if transcript else None,row["session_id"],row["participant"],row["event_id"]))
            commit(connection)

        def member(sid, request, authorization, active=True):
            actor, error = authorize(authorization, request)
            if error: return None, None, error
            user = getattr(request.state, "participant", None)
            if not user: return None, None, err(403, "participant_login_required")
            with closing(db()) as connection:
                session = get_session(connection, sid, request)
            if not session: return None, None, err(404, "session_not_found")
            if active and session["state"] != "active": return None, None, err(409, "session_not_active")
            return user, session, None

        def current(sid, user):
            record = self.rooms.state(sid)
            if not record or record["state"] != "active" or user not in record["members"]:
                raise MediaError("media_not_joined")
            return record

        @app.get("/sessions/{sid}/media/status")
        def status(sid: str, request: Request, authorization: str = Header(default="")):
            user, session, error = member(sid, request, authorization, active=False)
            if error: return error
            record = self.rooms.state(sid)
            return {"state": record["state"] if record else "closed"}

        @app.post("/sessions/{sid}/media/join")
        async def join(sid: str, request: Request, authorization: str = Header(default="")):
            user, session, error = member(sid, request, authorization)
            if error: return error
            members = {session["maestro_id"]: "maestro", session["artist_id"]: "artist"}
            if None in members: return err(409, "registered_members_required")
            try:
                record = await self.enter(sid,members)
                # Completion may race network provisioning. Never issue a token
                # after the logical meeting has closed.
                user, session, error = member(sid, request, authorization)
                if error:
                    await self.close(sid,record["epoch"])
                    return error
                return {"generation":record["epoch"],**self.rooms.authority.channels(record["epoch"], user, members[user])}
            except CapacityExceeded:
                return err(429, "media_capacity_reached")
            except Exception:
                return err(503, "media_unavailable_or_reconciliation_required")

        @app.post("/sessions/{sid}/media/leave")
        async def leave(sid: str, body: MediaLeave, request: Request, authorization: str = Header(default="")):
            user, session, error = member(sid, request, authorization, active=False)
            if error: return error
            try:
                closed=await self.close(sid,body.generation)
                return {"state": "closed" if closed else "superseded"}
            except Exception:
                return err(503, "media_cleanup_pending")

        @app.post("/sessions/{sid}/media/recordings")
        def begin(sid: str, body: MediaEvent, request: Request, authorization: str = Header(default="")):
            user, session, error = member(sid, request, authorization)
            if error: return error
            self.reconcile(sid)
            try: record = current(sid, user)
            except MediaError: return err(409, "media_not_joined")
            with closing(db()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                session = get_session(connection, sid, request)
                if session["state"] != "active": return err(409, "session_not_active")
                row = connection.execute("SELECT * FROM media_recordings WHERE session_id=? AND participant=? AND event_id=?",
                                          (sid,user,body.client_event_id)).fetchone()
                if row: return {"id": body.client_event_id, "state": row["state"]}
                if connection.execute("SELECT COUNT(*) FROM media_recordings WHERE session_id=? AND participant=? AND state IN ('capturing','processing')",(sid,user)).fetchone()[0]:
                    return err(409, "media_busy")
                connection.execute("INSERT INTO media_recordings VALUES(?,?,?,'capturing',?,NULL)",
                                   (sid,user,body.client_event_id,time.time()))
                commit(connection)
            try:
                self.transport.begin_capture(record["epoch"],user,body.client_event_id)
            except Exception:
                with closing(db()) as connection:
                    connection.execute("UPDATE media_recordings SET state='failed' WHERE session_id=? AND participant=? AND event_id=?",
                                       (sid,user,body.client_event_id)); commit(connection)
                return err(503,"media_worker_disconnected")
            return {"id": body.client_event_id, "state": "capturing"}

        @app.post("/sessions/{sid}/media/recordings/{rid}/cancel")
        def cancel(sid: str, rid: str, request: Request, authorization: str = Header(default="")):
            user, session, error = member(sid,request,authorization,active=False)
            if error: return error
            record=self.rooms.state(sid)
            with closing(db()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row=connection.execute("SELECT state FROM media_recordings WHERE session_id=? AND participant=? AND event_id=?",(sid,user,rid)).fetchone()
                if not row: return err(404,"recording_not_found")
                if row["state"] != "capturing": return {"id":rid,"state":row["state"]}
                connection.execute("UPDATE media_recordings SET state='cancelled' WHERE session_id=? AND participant=? AND event_id=? AND state='capturing'",(sid,user,rid));commit(connection)
            if record:self.transport.cancel_capture(record["epoch"],user,rid)
            return {"id":rid,"state":"cancelled"}

        @app.post("/sessions/{sid}/media/recordings/{rid}/stop")
        async def stop(sid: str, rid: str, request: Request, authorization: str = Header(default="")):
            user, session, error=member(sid,request,authorization)
            if error:return error
            self.reconcile(sid)
            with closing(db()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row=connection.execute("SELECT * FROM media_recordings WHERE session_id=? AND participant=? AND event_id=?",(sid,user,rid)).fetchone()
                if not row:return err(404,"recording_not_found")
                if row["state"]=="completed":return {"text":row["transcript"],"language":"en" if session["maestro_id"]==user else "vi"}
                if row["state"]!="capturing":return err(409,"recording_unavailable")
                if time.time()-row["started"]>30:return err(409,"recording_expired")
                try:
                    record=current(sid,user)
                    audio=self.transport.finish_capture(record["epoch"],user,rid)
                except (MediaError,ValueError):return err(422,"no_recorded_audio")
                connection.execute("UPDATE media_recordings SET state='processing' WHERE session_id=? AND participant=? AND event_id=?",(sid,user,rid));commit(connection)
            body=Transcription(client_event_id="rtc-"+rid,language="en" if session["maestro_id"]==user else "vi",wav_base64=base64.b64encode(audio).decode())
            result=await asyncio.to_thread(transcribe,sid,body,request,authorization)
            success=isinstance(result,dict) and isinstance(result.get("text"),str)
            with closing(db()) as connection:
                connection.execute("UPDATE media_recordings SET state=?,transcript=? WHERE session_id=? AND participant=? AND event_id=?",
                    ("completed" if success else "failed",result["text"] if success else None,sid,user,rid));commit(connection)
            return result

        @app.post("/sessions/{sid}/media/speech/{mid}")
        async def say(sid: str, mid: str, body: MediaEvent, request: Request, authorization: str=Header(default="")):
            user, session, error=member(sid,request,authorization)
            if error:return error
            try:record=current(sid,user)
            except MediaError:return err(409,"media_not_joined")
            with closing(db()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                message=connection.execute("SELECT state FROM messages WHERE id=? AND session_id=?",(mid,sid)).fetchone()
                if not message:return err(404,"message_not_found")
                if message["state"]!="approved":return err(409,"approved_translation_required")
                row=connection.execute("SELECT * FROM media_deliveries WHERE session_id=? AND participant=? AND event_id=?",(sid,user,body.client_event_id)).fetchone()
                if row:
                    if row["message_id"]!=mid:return err(409,"idempotency_conflict")
                    return {"state":"played"} if row["state"]=="played" else err(409,"speech_delivery_unconfirmed")
                connection.execute("INSERT INTO media_deliveries VALUES(?,?,?,?,'processing')",(sid,user,body.client_event_id,mid));commit(connection)
            result=await asyncio.to_thread(speak,sid,mid,request,authorization)
            if isinstance(result,JSONResponse):
                with closing(db()) as connection:
                    connection.execute("UPDATE media_deliveries SET state='failed' WHERE session_id=? AND participant=? AND event_id=?",(sid,user,body.client_event_id));commit(connection)
                return result
            try:
                await self.transport.send(record["epoch"],user,base64.b64decode(result["wav_base64"],validate=True))
            except Exception:
                with closing(db()) as connection:
                    connection.execute("UPDATE media_deliveries SET state='failed' WHERE session_id=? AND participant=? AND event_id=?",(sid,user,body.client_event_id));commit(connection)
                return err(503,"speech_delivery_unconfirmed")
            with closing(db()) as connection:
                connection.execute("UPDATE media_deliveries SET state='played' WHERE session_id=? AND participant=? AND event_id=?",(sid,user,body.client_event_id));commit(connection)
            return {"state":"played"}
