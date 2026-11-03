"""Server-only RTC endpoints: receive private microphones, publish approved WAVs.

Raw ingress is never copied to a recipient channel. Performance routing and SAM
remain separate processing stages; camera tracks are not subscribed here.
"""
import asyncio
import io
import time
import uuid
import wave

from .media import MediaError
from .speech import validate_wav


class AudioCapture:
    def __init__(self):
        self.data = bytearray()
        self.started = time.monotonic()

    def push(self, pcm):
        if len(pcm) % 2:
            raise ValueError("invalid_pcm")
        if time.monotonic() - self.started <= 10:
            self.data.extend(pcm[:max(0, 320_000 - len(self.data))])

    def finish(self):
        if len(self.data) < 320 or not any(self.data):
            raise ValueError("no_recorded_audio")
        output = io.BytesIO()
        with wave.open(output, "wb") as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
            audio.writeframes(self.data)
        return output.getvalue()


class LiveKitTransport:
    def __init__(self, authority, room_api):
        self.authority, self.api = authority, room_api
        self.channels, self.tasks, self.captures, self.sending = {}, {}, {}, set()
        self.lock = asyncio.Lock()
        self.checked = False
        self.closing = set()

    async def check_manual_creation(self):
        """A stale participant token must not recreate a deleted room."""
        if self.checked:
            return
        import aiohttp
        epoch = str(uuid.uuid4())
        token = self.authority.token(epoch, "probe", "artist", "playback")
        room = self.authority.channel(epoch, "probe", "playback")
        await self.api.list([room])  # Proves this is a reachable authenticated LiveKit API.
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as client:
                async with client.ws_connect(self.authority.url + "/rtc",
                    headers={"Authorization": "Bearer " + token},
                    params={"protocol": "15", "sdk": "python", "version": "1.2.0", "auto_subscribe": "0"}):
                    pass
        except aiohttp.WSServerHandshakeError as error:
            if error.status == 404:
                self.checked = True
                return
            raise MediaError("media_server_policy_unconfirmed") from error
        except Exception as error:
            raise MediaError("media_server_policy_unconfirmed") from error
        await self.api.delete(room)
        raise MediaError("media_server_auto_creation_must_be_disabled")

    async def ensure(self, record):
        async with self.lock:
            await self.check_manual_creation()
            epoch = record["epoch"]
            try:
                for user, role in record["members"].items():
                    for direction in ("ingress", "playback"):
                        key = (epoch, user, direction)
                        existing = self.channels.get(key)
                        if existing and existing["room"].isconnected():
                            continue
                        if existing:
                            raise MediaError("media_worker_disconnected")
                        self.channels[key] = await self.connect(epoch, user, role, direction)
            except Exception:
                await self._disconnect(epoch)
                raise

    async def connect(self, epoch, user, role, direction):
        from livekit import rtc
        room = rtc.Room()
        source = None
        if direction == "ingress":
            expected = "member-" + self.authority.opaque(epoch + ":" + user)
            def subscribe(publication, participant):
                if (participant.identity == expected and publication.kind == rtc.TrackKind.KIND_AUDIO
                        and publication.source == rtc.TrackSource.SOURCE_MICROPHONE):
                    publication.set_subscribed(True)
            @room.on("track_published")
            def published(publication, participant):
                subscribe(publication, participant)
            @room.on("track_subscribed")
            def subscribed(track, publication, participant):
                if participant.identity != expected or publication.source != rtc.TrackSource.SOURCE_MICROPHONE:
                    publication.set_subscribed(False)
                    return
                task = asyncio.create_task(self.read_audio(epoch, user, track))
                self.tasks[task] = epoch
                task.add_done_callback(lambda done: self.tasks.pop(done, None))
        try:
            token = self.authority.token(epoch, user, role, direction, server=True)
            await asyncio.wait_for(room.connect(self.authority.url, token, rtc.RoomOptions(auto_subscribe=False)), 8)
            if direction == "playback":
                source = rtc.AudioSource(16000, 1, queue_size_ms=200)
                track = rtc.LocalAudioTrack.create_audio_track("Muse", source)
                await room.local_participant.publish_track(track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
            else:
                for participant in room.remote_participants.values():
                    for publication in participant.track_publications.values():
                        subscribe(publication, participant)
            return {"room": room, "source": source, "lock": asyncio.Lock()}
        except Exception:
            if source:await source.aclose()
            await room.disconnect()
            raise

    async def read_audio(self, epoch, user, track):
        from livekit import rtc
        stream = rtc.AudioStream(track, capacity=4, sample_rate=16000, num_channels=1, frame_size_ms=20)
        try:
            async for event in stream:
                capture = self.captures.get((epoch, user))
                if capture:
                    capture[1].push(event.frame.data.tobytes())
        finally:
            await stream.aclose()

    def begin_capture(self, epoch, user, event_id):
        key = (epoch, user)
        channel = self.channels.get((epoch, user, "ingress"))
        if epoch in self.closing or not channel or not channel["room"].isconnected():
            raise MediaError("media_worker_disconnected")
        if key in self.captures:
            raise MediaError("recording_in_progress")
        self.captures[key] = (event_id, AudioCapture())

    def finish_capture(self, epoch, user, event_id):
        capture = self.captures.get((epoch, user))
        if not capture or capture[0] != event_id:
            raise MediaError("recording_not_found")
        self.captures.pop((epoch, user))
        return capture[1].finish()

    def cancel_capture(self, epoch, user, event_id):
        capture = self.captures.get((epoch,user))
        if capture and capture[0] == event_id:
            self.captures.pop((epoch,user),None)

    async def send(self, epoch, user, audio):
        from livekit import rtc
        validate_wav(audio)
        channel = self.channels.get((epoch, user, "playback"))
        if epoch in self.closing or not channel or not channel["room"].isconnected():
            raise MediaError("media_worker_disconnected")
        async with channel["lock"]:
            self.sending.add((epoch, user))
            try:
                with wave.open(io.BytesIO(audio), "rb") as recording:
                    while pcm := recording.readframes(320):
                        await channel["source"].capture_frame(rtc.AudioFrame(
                            data=pcm, sample_rate=16000, num_channels=1, samples_per_channel=len(pcm)//2))
                await channel["source"].wait_for_playout()
            finally:
                self.sending.discard((epoch, user))

    def busy(self, epoch):
        return any(key[0] == epoch for key in (*self.captures, *self.sending))

    async def disconnect(self, epoch):
        self.closing.add(epoch)
        try:
            async with self.lock:
                await self._disconnect(epoch)
        finally:
            self.closing.discard(epoch)

    async def _disconnect(self, epoch):
        for key in list(self.captures):
            if key[0] == epoch: self.captures.pop(key, None)
        tasks = [task for task, owner in self.tasks.items() if owner == epoch]
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for key in list(self.channels):
            if key[0] != epoch: continue
            channel = self.channels.pop(key)
            if channel["source"]:
                channel["source"].clear_queue()
                await channel["source"].aclose()
            await channel["room"].disconnect()
