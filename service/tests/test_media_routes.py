import io
import wave
import unittest

from fastapi import FastAPI
from service.app import create_app
from service.media import MediaAuthority, MediaRooms
from service.media_api import ParticipantMedia
from service.media_transport import AudioCapture
from service.tests import test_participants as participants
from service.tests.test_media import RoomAPI
from runtime.admission import initialize_database


class OfflineTransport:
    def __init__(self): self.captures = {}; self.sent = []
    async def check_manual_creation(self): pass
    async def ensure(self, record): pass
    def begin_capture(self, epoch, user, event_id): self.captures[(epoch,user)] = (event_id,AudioCapture())
    def finish_capture(self, epoch, user, event_id):
        rid,capture=self.captures[(epoch,user)]
        if rid!=event_id:raise ValueError('wrong recording')
        self.captures.pop((epoch,user));return capture.finish()
    def cancel_capture(self, epoch, user, event_id):
        capture=self.captures.get((epoch,user))
        if capture and capture[0]==event_id:self.captures.pop((epoch,user),None)
    def busy(self, epoch): return any(key[0] == epoch for key in self.captures)
    async def disconnect(self, epoch): self.captures = {k:v for k,v in self.captures.items() if k[0] != epoch}
    async def send(self, epoch, user, audio): self.sent.append((user,audio))


class MediaRoutes(unittest.TestCase):
    def setUp(self):
        participants.ParticipantIntegration.setUpClass()
        self.p = participants.ParticipantIntegration("test_logout_revokes_cookie")
        self.p.setUp(); self.addCleanup(self.p.doCleanups)
        self.api = RoomAPI(); self.transport = OfflineTransport()
        authority = MediaAuthority("ws://127.0.0.1:54410", "test", "s"*48)
        admission = initialize_database(self.p.directory.name + "/admission.sqlite3",capacity=1)
        rooms = MediaRooms(self.p.directory.name + "/media.sqlite3",admission,authority,self.api)
        self.media = ParticipantMedia(rooms,self.transport)
        self.asr_calls = 0
        self.p.adapter.asr_enabled = True
        def asr(path, **kwargs):
            self.asr_calls += 1
            self.assertEqual(kwargs["language_bias"], ["English"])
            with wave.open(path) as audio: self.assertGreater(audio.getnframes(), 100)
            return {"text":"Play slowly."}
        self.p.adapter.transcribe = asr
        audio = io.BytesIO()
        with wave.open(audio,"wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000); f.writeframes(b"\1\0"*1600)
        self.wav=audio.getvalue()
        test=self
        class Speech:
            revision="offline"
            def synthesize(self,text,lang): return test.wav
        self.speech=Speech()
        app=create_app(data_dir=self.p.directory.name,adapter=self.p.adapter,environ=self.p.env,
                       heart_key=self.p.key,speech=self.speech,media=self.media)
        self.harness=app
        self.p.site=FastAPI(); self.p.site.mount("/api/harness",app)
        self.p.m=self.p.login("M"); self.p.a=self.p.login("A"); self.p.active()
        self.path=self.p.path+"/media"

    def join(self):
        response=self.p.m.post(self.path+"/join",json={"user":"other","role":"maestro"})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def message(self):
        response=self.p.m.post(self.p.path+"/messages",json={"client_event_id":"msg","speaker":"maestro",
            "text":"Play slowly.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()["id"]

    def test_join_is_scoped_to_cookie_member_and_blocks_other_origin(self):
        result=self.join()
        self.assertIn("ingress",result); self.assertIn("playback",result)
        self.assertNotIn("other",str(result))
        self.assertEqual(self.p.login("other").post(self.path+"/join").status_code,404)
        self.assertEqual(self.p.m.post(self.path+"/join",headers={"Origin":"https://evil.invalid"}).status_code,403)

    def test_rtc_recording_reuses_asr_and_never_delivers_automatically(self):
        self.join()
        started=self.p.m.post(self.path+"/recordings",json={"client_event_id":"mic"})
        self.assertEqual(started.status_code,200,started.text)
        record=self.media.rooms.state(self.p.path.split('/')[-1])
        self.transport.captures[(record['epoch'],'M')][1].push(b"\1\0"*1600)
        for _ in range(2):
            response=self.p.m.post(self.path+"/recordings/mic/stop",json={})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["text"],"Play slowly.")
        self.assertEqual(self.asr_calls,1)
        self.assertEqual(self.p.a.get(self.p.path).json()["deliveries"],[])

    def test_draft_speech_blocked_and_replay_does_not_broadcast_twice(self):
        self.join();mid=self.message()
        self.assertEqual(self.p.a.post(self.path+f"/speech/{mid}",json={"client_event_id":"say"}).status_code,409)
        self.p.m.post(self.p.path+f"/messages/{mid}/approve",json={})
        for _ in range(2):
            response=self.p.a.post(self.path+f"/speech/{mid}",json={"client_event_id":"say"})
            self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.transport.sent,[("A",self.wav)])

    def test_completion_waits_for_recording_and_confirmed_room_cleanup(self):
        self.join(); self.p.m.post(self.path+"/recordings",json={"client_event_id":"mic"})
        self.assertEqual(self.p.m.post(self.p.path+"/complete").status_code,409)
        self.p.m.post(self.path+"/recordings/mic/cancel",json={})
        self.api.fail_delete=True
        self.assertEqual(self.p.m.post(self.p.path+"/complete").status_code,503)
        self.assertEqual(self.p.m.get(self.p.path).json()["state"],"closing")
        self.assertEqual(self.p.m.get(self.p.path+"/heart").json()["counters"]["happened"],0)
        self.api.fail_delete=False
        self.assertEqual(self.p.m.post(self.p.path+"/complete").status_code,200)
        self.assertEqual(self.api.rooms,{})
        self.assertEqual(self.p.m.get(self.p.path+"/heart").json()["counters"]["happened"],1)

    def test_logout_closes_media_capability_rooms(self):
        self.join()
        self.assertEqual(self.p.m.post("/api/harness/auth/logout").status_code,200)
        self.assertEqual(self.api.rooms,{})

    def test_previous_owner_processing_does_not_permanently_block_completion(self):
        import sqlite3,time
        from fastapi.testclient import TestClient
        self.join();sid=self.p.path.split('/')[-1]
        with sqlite3.connect(self.p.directory.name+"/service.sqlite3") as connection:
            connection.execute("INSERT INTO media_recordings VALUES(?,?,?,'processing',?,NULL)",(sid,'M','lost',time.time()))
            connection.execute("INSERT INTO transcriptions VALUES(?,?,?,'processing',NULL)",(sid,'M:rtc-lost','hash'))
            connection.execute("INSERT INTO media_deliveries VALUES(?,?,?,?,'processing')",(sid,'A','lost-speech','message'))
        self.media=ParticipantMedia(self.media.rooms,OfflineTransport())
        app=create_app(data_dir=self.p.directory.name,adapter=self.p.adapter,environ=self.p.env,
            heart_key=self.p.key,speech=self.speech,media=self.media)
        site=FastAPI();site.mount('/api/harness',app)
        client=TestClient(site,cookies=self.p.m.cookies,headers={'Origin':'http://testserver'})
        response=client.post(self.p.path+'/complete')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.asr_calls,0)
        with sqlite3.connect(self.p.directory.name+'/service.sqlite3') as connection:
            self.assertEqual(connection.execute("SELECT state FROM media_deliveries").fetchone()[0],'unconfirmed')
            self.assertEqual(connection.execute("SELECT state FROM media_recordings").fetchone()[0],'unconfirmed')

    def test_logout_attempts_every_meeting_after_one_cleanup_failure(self):
        self.media.rooms.admission=initialize_database(self.p.directory.name+'/two-slots.sqlite3',capacity=2)
        self.join();first=self.media.rooms.state(self.p.path.split('/')[-1])
        first_rooms=set(self.media.rooms.authority.rooms(first['epoch'],first['members']))
        self.p.active();self.path=self.p.path+'/media';self.join()
        second=self.media.rooms.state(self.p.path.split('/')[-1])
        second_rooms=set(self.media.rooms.authority.rooms(second['epoch'],second['members']))
        original=self.api.delete
        async def delete(name):
            if name in first_rooms:raise TimeoutError('first meeting cleanup unavailable')
            await original(name)
        self.api.delete=delete
        response=self.p.m.post('/api/harness/auth/logout')
        self.assertEqual(response.status_code,503,response.text)
        self.assertTrue(first_rooms.intersection(self.api.rooms))
        self.assertFalse(second_rooms.intersection(self.api.rooms))
        self.assertEqual(self.p.m.get('/api/harness/auth/me').status_code,401)

    def test_shutdown_closes_transport_without_awarding_lesson_completion(self):
        from fastapi.testclient import TestClient
        self.join()
        site=FastAPI(lifespan=self.harness.router.lifespan_context)
        site.mount('/api/harness',self.harness)
        with TestClient(site) as client:
            self.assertTrue(self.api.rooms)
        self.assertEqual(self.api.rooms,{})
        self.assertEqual(self.p.m.get(self.p.path).json()['state'],'active')
        self.assertEqual(self.p.m.get(self.p.path+'/heart').json()['counters']['happened'],0)

    def test_old_generation_leave_cannot_close_reopened_rooms(self):
        self.join();old=self.media.rooms.state(self.p.path.split('/')[-1])['epoch']
        self.assertEqual(self.p.m.post(self.path+'/leave',json={'generation':old}).status_code,200)
        self.join()
        response=self.p.m.post(self.path+'/leave',json={'generation':old})
        self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(self.api.rooms)
