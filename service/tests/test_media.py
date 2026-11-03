"""Room capabilities and durable admission; external room calls are explicit fakes."""
import json
import sqlite3
import tempfile
import unittest

import jwt

from runtime.admission import initialize_database, CapacityExceeded
from service.media import MediaAuthority, MediaRooms, MediaError


class RoomAPI:
    def __init__(self):
        self.rooms = {}; self.creates = 0; self.fail_create = False; self.fail_delete = False

    async def create(self, name, metadata):
        self.creates += 1
        if self.fail_create: raise TimeoutError("uncertain external outcome")
        self.rooms[name] = metadata

    async def list(self, names):
        return {name: self.rooms[name] for name in names if name in self.rooms}

    async def delete(self, name):
        if self.fail_delete: raise TimeoutError("uncertain deletion")
        self.rooms.pop(name, None)


class MediatedMedia(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="cx1-media-", dir="/private/tmp")
        self.addCleanup(self.directory.cleanup)
        self.admission = initialize_database(self.directory.name + "/admission.sqlite3", capacity=1)
        self.authority = MediaAuthority("ws://127.0.0.1:54410", "local-key", "s" * 48)
        self.api = RoomAPI()
        self.members = {"private-maestro-id": "maestro", "private-artist-id": "artist"}
        self.build()

    def build(self, persist=None):
        self.media = MediaRooms(self.directory.name + "/media.sqlite3", self.admission,
                                self.authority, self.api, persist=persist)

    def test_room_grants_are_directional_and_pseudonymous(self):
        channels = self.authority.channels("epoch", "private-maestro-id", "maestro")
        for direction in ("ingress", "playback"):
            token = jwt.decode(channels[direction]["token"], "s"*48, algorithms=["HS256"], issuer="local-key")
            video = token["video"]
            self.assertEqual(video["canPublish"], direction == "ingress")
            self.assertEqual(video["canSubscribe"], direction == "playback")
            for grant in ("canPublishData", "roomCreate", "roomAdmin", "roomList", "roomRecord", "canUpdateOwnMetadata"):
                self.assertIs(video[grant], False)
            self.assertLessEqual(token["exp"] - token["nbf"], 60)
            self.assertNotIn("private-maestro-id", json.dumps(token))
        self.assertNotEqual(channels["ingress"]["room"], channels["playback"]["room"])
        other = self.authority.channels("epoch", "private-artist-id", "artist")
        self.assertNotEqual(channels["ingress"]["room"], other["ingress"]["room"])

    async def test_capacity_is_reserved_before_any_room_api_call(self):
        first = await self.media.open("meeting-a", self.members)
        self.assertEqual(first["state"], "active")
        self.assertEqual(len(self.api.rooms), 4)
        before = self.api.creates
        with self.assertRaises(CapacityExceeded): await self.media.open("meeting-b", self.members)
        self.assertEqual(self.api.creates, before)

    async def test_restart_replay_checks_rooms_without_reprovision(self):
        first = await self.media.open("meeting", self.members)
        self.build()
        second = await self.media.open("meeting", self.members)
        self.assertEqual(first, second)
        self.assertEqual(self.api.creates, 4)
        bad_members = {**self.members, "outsider": "artist"}
        with self.assertRaises(MediaError): await self.media.open("meeting", bad_members)

    async def test_uncertain_creation_holds_slot_and_cannot_autoretry(self):
        self.api.fail_create = True
        with self.assertRaises(MediaError): await self.media.open("meeting", self.members)
        snapshot = self.admission.snapshot()
        self.assertEqual(snapshot["reservations"][0]["state"], "STARTING")
        self.assertTrue(snapshot["reservations"][0]["provision_started"])
        calls = self.api.creates
        self.api.fail_create = False
        self.build()
        with self.assertRaises(MediaError): await self.media.open("meeting", self.members)
        self.assertEqual(self.api.creates, calls)
        await self.media.close("meeting")
        self.assertEqual(self.admission.snapshot()["reservations"][0]["state"], "COMPLETED")

    async def test_unconfirmed_close_holds_slot_until_confirmed_cleanup(self):
        first = await self.media.open("meeting", self.members)
        self.api.fail_delete = True
        with self.assertRaises(MediaError): await self.media.close("meeting")
        self.assertEqual(self.admission.snapshot()["reservations"][0]["state"], "CLOSING")
        self.api.fail_delete = False
        await self.media.close("meeting")
        self.assertEqual(self.api.rooms, {})
        self.assertEqual(self.admission.snapshot()["reservations"][0]["state"], "COMPLETED")
        reopened = await self.media.open("meeting", self.members)
        self.assertNotEqual(first["epoch"], reopened["epoch"])

    async def test_missing_or_changed_remote_room_fails_closed(self):
        opened = await self.media.open("meeting", self.members)
        self.api.rooms.pop(next(iter(self.api.rooms)))
        with self.assertRaises(MediaError): await self.media.open("meeting", self.members)
        self.assertEqual(self.admission.snapshot()["reservations"][0]["state"], "ACTIVE")

    async def test_durability_failure_prevents_external_provisioning(self):
        enabled = [False]
        def persist():
            if enabled[0]: raise OSError("volume commit failed")
        self.build(persist)
        enabled[0] = True
        with self.assertRaises(OSError): await self.media.open("meeting", self.members)
        self.assertEqual(self.api.creates, 0)

    async def test_lost_close_acknowledgment_recovers_after_restart(self):
        await self.media.open("meeting", self.members)
        await self.media.close("meeting")
        with sqlite3.connect(self.directory.name + "/media.sqlite3") as connection:
            connection.execute("UPDATE media_sessions SET state='closing'")
        self.build()
        await self.media.close("meeting")
        self.assertEqual(self.media.state("meeting")["state"], "closed")
        self.assertEqual(self.admission.snapshot()["reservations"][0]["state"], "COMPLETED")
