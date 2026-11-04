"""Ephemeral authenticated WebRTC mesh signalling, never a media relay.

One service process owns the bounded in-memory roster/queues. A process restart
requires a new conference connection; SDP/ICE and raw media are never persisted.
The application supplies its ordinary identity, session and membership checks.
"""
import json
import threading
import time
import uuid

from fastapi import Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Join(StrictBody):
    pass


class Connection(StrictBody):
    connection_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class Description(StrictBody):
    type: str = Field(pattern=r"^(offer|answer)$")
    sdp: str = Field(min_length=1, max_length=20000)


class Candidate(StrictBody):
    candidate: str = Field(max_length=4096)
    sdpMid: str | None = Field(default=None, max_length=256)
    sdpMLineIndex: int | None = Field(default=None, ge=0, le=32)
    usernameFragment: str | None = Field(default=None, max_length=256)


class Signal(Connection):
    to: str = Field(min_length=1, max_length=100)
    to_connection: str = Field(pattern=r"^[a-f0-9]{32}$")
    description: Description | None = None
    candidate: Candidate | None = None

    @model_validator(mode="after")
    def one_payload(self):
        if ("description" in self.model_fields_set) == ("candidate" in self.model_fields_set):
            raise ValueError("one description or candidate is required")
        if "description" in self.model_fields_set and self.description is None:
            raise ValueError("description is required")
        return self


def register_routes(app, db, commit, authenticate, find_session, err, *, member_ids=None, clock=time.monotonic):
    """Install routes; member_ids(c,sid,session) supplies group account IDs.

    The fallback deliberately supports only the existing registered pair.
    ``session_presence`` must already record the person's logical lesson join.
    No budgets, keys, external service or schema migration is involved.
    """
    rooms = {}
    lock = threading.RLock()
    ttl = 45

    def authorize(sid, request, authorization):
        _, failure = authenticate(authorization, request)
        if failure is not None:
            return None, None, failure
        user = getattr(request.state, "participant", None)
        if not user:
            return None, None, err(403, "participant_login_required")
        c = db()
        try:
            session = find_session(c, sid, request)
            if not session:
                return None, None, err(404, "session_not_found")
            if session["state"] != "active":
                with lock:
                    rooms.pop(sid, None)
                return None, None, err(409, "session_not_active")
            members = set(member_ids(c, sid, session) if member_ids else
                          (session["maestro_id"], session["artist_id"])) - {None}
            if user not in members:
                return None, None, err(404, "session_not_found")
            joined = {row[0] for row in c.execute(
                "SELECT participant FROM session_presence WHERE session_id=?", (sid,))}
            if user not in joined:
                return None, None, err(403, "lesson_join_required")
            return user, members & joined, None
        finally:
            c.close()

    def prune(room, members=None):
        now = clock()
        for user, peer in list(room["peers"].items()):
            if now - peer["seen"] >= ttl or (members is not None and user not in members):
                del room["peers"][user]
        for peer in room["peers"].values():
            peer["events"] = [e for e in peer["events"] if now - e["at"] < ttl
                              and e["from"] in room["peers"]
                              and room["peers"][e["from"]]["connection_id"] == e["from_connection"]]

    def current(sid, user, connection_id, members):
        room = rooms.get(sid)
        if room:
            prune(room, members)
        peer = room and room["peers"].get(user)
        if not peer or peer["connection_id"] != connection_id:
            return None, None, err(409, "conference_connection_expired")
        peer["seen"] = clock()
        return room, peer, None

    def roster(room, user):
        return [{"id": uid, "connection_id": peer["connection_id"]}
                for uid, peer in sorted(room["peers"].items()) if uid != user]

    @app.post("/sessions/{sid}/conference/join")
    def join(sid: str, body: Join, request: Request, authorization: str = Header(default="")):
        user, members, failure = authorize(sid, request, authorization)
        if failure is not None:
            return failure
        with lock:
            for key, value in list(rooms.items()):
                prune(value)
                if not value["peers"]:
                    del rooms[key]
            if sid not in rooms and len(rooms) >= 64:
                return err(429, "conference_capacity_reached")
            room = rooms.setdefault(sid, {"peers": {}, "cursor": 0})
            prune(room, members)
            if user not in room["peers"] and len(room["peers"]) >= 3:
                return err(429, "conference_three_participants_maximum")
            connection_id = uuid.uuid4().hex
            room["peers"][user] = {"connection_id": connection_id, "seen": clock(), "events": []}
            return {"self": user, "connection_id": connection_id, "peers": roster(room, user), "cursor": room["cursor"]}

    @app.get("/sessions/{sid}/conference/events")
    def events(sid: str, request: Request,
               connection_id: str = Query(pattern=r"^[a-f0-9]{32}$"),
               after: int = Query(default=0, ge=0, le=2**53-1), authorization: str = Header(default="")):
        user, members, failure = authorize(sid, request, authorization)
        if failure is not None:
            return failure
        with lock:
            room, peer, failure = current(sid, user, connection_id, members)
            if failure is not None:
                return failure
            peer["events"] = [e for e in peer["events"] if e["id"] > after]
            return {"self": user, "peers": roster(room, user), "cursor": room["cursor"],
                    "events": [{k: v for k, v in event.items() if k != "at"} for event in peer["events"]]}

    @app.post("/sessions/{sid}/conference/signal")
    def signal(sid: str, body: Signal, request: Request, authorization: str = Header(default="")):
        user, members, failure = authorize(sid, request, authorization)
        if failure is not None:
            return failure
        with lock:
            room, peer, failure = current(sid, user, body.connection_id, members)
            if failure is not None:
                return failure
            if body.to == user or body.to not in members:
                return err(404, "conference_recipient_not_found")
            target = room["peers"].get(body.to)
            if not target or target["connection_id"] != body.to_connection:
                return err(409, "conference_recipient_reconnected")
            if len(target["events"]) >= 128:
                return err(429, "conference_signal_queue_full")
            room["cursor"] += 1
            event = {"id": room["cursor"], "at": clock(), "from": user,
                     "from_connection": body.connection_id}
            if "description" in body.model_fields_set:
                event["description"] = body.description.model_dump()
            else:
                event["candidate"] = body.candidate.model_dump(exclude_none=True) if body.candidate is not None else None
            # Bound UTF-8 storage as well as event count (SDP can be Unicode).
            size = lambda value: len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            if size(event) + sum(size(item) for item in target["events"]) > 262144:
                return err(429, "conference_signal_queue_full")
            target["events"].append(event)
            return {"ok": True}

    @app.post("/sessions/{sid}/conference/leave")
    def leave(sid: str, body: Connection, request: Request, authorization: str = Header(default="")):
        user, members, failure = authorize(sid, request, authorization)
        if failure is not None:
            return failure
        with lock:
            room = rooms.get(sid)
            peer = room and room["peers"].get(user)
            if peer and peer["connection_id"] == body.connection_id:
                del room["peers"][user]
            return {"ok": True}
