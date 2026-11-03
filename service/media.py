"""Private directional LiveKit channels behind durable lesson admission.

One trusted serialized orchestrator owns this store, like the existing service.
No participant receives another participant's microphone-room capability.
"""
import asyncio
import hashlib
import hmac
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import timedelta
from urllib.parse import urlsplit

from runtime.admission import CapacityExceeded


class MediaError(RuntimeError):
    pass


class MediaAuthority:
    def __init__(self, url, api_key, api_secret):
        parsed = urlsplit(url)
        if (parsed.scheme not in ("ws", "wss") or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError("invalid LiveKit URL")
        if parsed.scheme == "ws" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("LiveKit requires TLS outside loopback")
        if not api_key or len(api_secret) < 32:
            raise ValueError("LiveKit server credentials required")
        self.url, self.api_key, self.api_secret = url.rstrip("/"), api_key, api_secret

    def opaque(self, value):
        return hmac.new(self.api_secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]

    def channel(self, epoch, user, direction):
        if direction not in ("ingress", "playback"):
            raise ValueError("invalid media direction")
        return "som-" + self.opaque(epoch + ":" + user + ":" + direction)

    def token(self, epoch, user, role, direction, *, server=False):
        from livekit import api
        if role not in ("maestro", "artist"):
            raise ValueError("invalid media role")
        publish = (direction == "ingress") != server
        room = self.channel(epoch, user, direction)
        identity = ("muse-" if server else "member-") + self.opaque(epoch + ":" + user)
        grants = api.VideoGrants(room_join=True, room=room, room_create=False, room_list=False,
            room_admin=False, room_record=False, ingress_admin=False,
            can_publish=publish, can_subscribe=not publish, can_publish_data=False,
            can_update_own_metadata=False, can_publish_sources=["microphone", "camera"] if publish else [])
        return (api.AccessToken(self.api_key, self.api_secret).with_identity(identity)
                .with_name("Muse" if server else role).with_grants(grants)
                .with_ttl(timedelta(seconds=60)).to_jwt())

    def channels(self, epoch, user, role):
        return {"url": self.url, "expires_seconds": 60,
                **{direction: {"room": self.channel(epoch, user, direction),
                               "token": self.token(epoch, user, role, direction)}
                   for direction in ("ingress", "playback")}}

    def rooms(self, epoch, members):
        return {self.channel(epoch, user, direction): json.dumps(
                    {"som": 1, "owner": self.opaque(epoch), "direction": direction}, sort_keys=True)
                for user in members for direction in ("ingress", "playback")}


class LiveKitRoomAPI:
    def __init__(self, authority):
        self.authority = authority

    def client(self):
        import aiohttp
        from livekit import api
        auth = self.authority
        return api.LiveKitAPI(auth.url.replace("ws://", "http://").replace("wss://", "https://"),
                              auth.api_key, auth.api_secret,
                              timeout=aiohttp.ClientTimeout(total=5), failover=False)

    async def create(self, name, metadata):
        from livekit import api
        async with self.client() as client:
            await client.room.create_room(api.CreateRoomRequest(name=name, metadata=metadata,
                empty_timeout=600, departure_timeout=5, max_participants=2))

    async def list(self, names):
        from livekit import api
        async with self.client() as client:
            result = await client.room.list_rooms(api.ListRoomsRequest(names=list(names)))
            return {room.name: room.metadata for room in result.rooms}

    async def delete(self, name):
        from livekit import api
        async with self.client() as client:
            try:
                await client.room.delete_room(api.DeleteRoomRequest(room=name))
            except api.TwirpError as error:
                if error.code != "not_found":
                    raise


class MediaRooms:
    def __init__(self, path, admission, authority, room_api, persist=None):
        self.path, self.admission = path, admission
        self.authority, self.api = authority, room_api
        self.persist = persist or (lambda: None)
        self.lock = asyncio.Lock()
        with closing(self.db()) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS media_sessions(
                session_id TEXT PRIMARY KEY, epoch TEXT NOT NULL, reservation_id TEXT,
                state TEXT NOT NULL, members TEXT NOT NULL)""")
        self.persist()

    def db(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def state(self, sid):
        with closing(self.db()) as connection:
            found = connection.execute("SELECT * FROM media_sessions WHERE session_id=?", (sid,)).fetchone()
        if not found:
            return None
        record = dict(found)
        record["members"] = json.loads(record["members"])
        return record

    def save(self, record):
        with closing(self.db()) as connection, connection:
            connection.execute("INSERT OR REPLACE INTO media_sessions VALUES(?,?,?,?,?)",
                (record["session_id"], record["epoch"], record.get("reservation_id"),
                 record["state"], json.dumps(record["members"], sort_keys=True)))
        self.persist()

    async def open(self, sid, members):
        members = dict(members)
        if not members or any(role not in ("maestro", "artist") for role in members.values()):
            raise MediaError("invalid_media_members")
        async with self.lock:
            record = self.state(sid)
            if record and record["state"] != "closed":
                if record["members"] != members:
                    raise MediaError("media_membership_changed")
                if record["state"] != "active":
                    raise MediaError("media_reconciliation_required")
                rooms = self.authority.rooms(record["epoch"], members)
                if await self.api.list(rooms) != rooms:
                    raise MediaError("media_reconciliation_required")
                return record
            record = {"session_id": sid, "epoch": str(uuid.uuid4()),
                      "reservation_id": None, "state": "reserving", "members": members}
            self.save(record)
            try:
                reservation = self.admission.reserve(record["epoch"], record["epoch"])
            except CapacityExceeded:
                record["state"] = "closed"; self.save(record)
                raise
            record["reservation_id"] = reservation.reservation_id
            record["state"] = "starting"
            self.save(record)  # Commits both stores on the persistent volume.
            self.admission.note_provision_started(reservation.reservation_id)
            self.persist()  # MUST succeed before any external room call.
            try:
                rooms = self.authority.rooms(record["epoch"], members)
                for name, metadata in rooms.items():
                    await self.api.create(name, metadata)
                if await self.api.list(rooms) != rooms:
                    raise MediaError("room_provisioning_unconfirmed")
                self.admission.mark_active(reservation.reservation_id)
                record["state"] = "active"; self.save(record)
                return record
            except Exception as error:
                record["state"] = "pending"; self.save(record)
                raise MediaError("media_reconciliation_required") from error

    async def close(self, sid, expected_epoch=None):
        async with self.lock:
            record = self.state(sid)
            if record and expected_epoch and record["epoch"] != expected_epoch:
                return False
            if not record or record["state"] == "closed":
                return True
            # Handles a crash between admission reserve and storing its ID.
            reservations = self.admission.snapshot()["reservations"]
            reservation = next((r for r in reservations if r["lesson_id"] == record["epoch"]), None)
            if not reservation:
                record["state"] = "closed"; self.save(record)
                return True
            record["reservation_id"] = reservation["reservation_id"]
            if reservation["state"] in ("COMPLETED", "CANCELLED"):
                if await self.api.list(self.authority.rooms(record["epoch"], record["members"])):
                    raise MediaError("media_reconciliation_required")
                record["state"] = "closed"; self.save(record)
                return True
            if not reservation["provision_started"]:
                self.admission.cancel_unprovisioned(reservation["reservation_id"])
                record["state"] = "closed"; self.save(record)
                return True
            record["state"] = "closing"; self.save(record)
            self.admission.mark_closing(reservation["reservation_id"])
            self.persist()
            try:
                rooms = self.authority.rooms(record["epoch"], record["members"])
                existing = await self.api.list(rooms)
                if any(metadata != rooms.get(name) for name, metadata in existing.items()):
                    raise MediaError("room_ownership_changed")
                for name in existing:
                    await self.api.delete(name)
                if await self.api.list(rooms):
                    raise MediaError("room_deletion_unconfirmed")
                self.admission.confirm_closed(reservation["reservation_id"])
                record["state"] = "closed"; self.save(record)
                return True
            except Exception as error:
                raise MediaError("media_cleanup_pending") from error
