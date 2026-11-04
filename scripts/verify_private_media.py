"""Opt-in localhost RTC verification, with no paid models or production resources.

Supply a private JSON file with url/key/secret, an existing empty test directory,
and a mono PCM16/16kHz WAV (e.g. one produced by the MMS evaluation).
"""
import argparse
import asyncio
import io
import json
import math
from pathlib import Path
import struct
import sys
import wave
import time
import jwt

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from livekit import rtc
from service.media import MediaAuthority,MediaRooms,LiveKitRoomAPI
from service.media_transport import LiveKitTransport
from runtime.admission import initialize_database


async def verify(config, directory, wav):
    authority=MediaAuthority(config["url"],config["key"],config["secret"])
    if not authority.url.startswith(("ws://127.0.0.1:","ws://localhost:")):
        raise ValueError("This verifier operates on loopback only")
    admin=LiveKitRoomAPI(authority)
    transport=LiveKitTransport(authority,admin)
    await transport.check_manual_creation()
    admission=initialize_database(str(directory/"admission.sqlite3"),capacity=1)
    rooms=MediaRooms(str(directory/"media.sqlite3"),admission,authority,admin)
    record=await rooms.open("local-verification",{"sender":"maestro","recipient":"artist"})
    epoch=record["epoch"]
    publisher,recipient,stale=rtc.Room(),rtc.Room(),rtc.Room()
    received=[];readers=[];phase=["raw"]
    source=None

    @recipient.on("track_subscribed")
    def subscribed(track,publication,participant):
        async def collect():
            stream=rtc.AudioStream(track,sample_rate=16000,num_channels=1,capacity=4)
            try:
                async for event in stream:
                    pcm=event.frame.data.tobytes()
                    values=struct.unpack("<"+"h"*(len(pcm)//2),pcm)
                    received.append((phase[0],max(abs(v) for v in values)))
            finally:await stream.aclose()
        readers.append(asyncio.create_task(collect()))

    try:
        await transport.ensure(record)
        ingress=authority.channels(epoch,"sender","maestro")["ingress"]["token"]
        playback=authority.channels(epoch,"recipient","artist")["playback"]["token"]
        await recipient.connect(authority.url,playback)
        await publisher.connect(authority.url,ingress)
        source=rtc.AudioSource(16000,1,queue_size_ms=200)
        track=rtc.LocalAudioTrack.create_audio_track("synthetic-private-mic",source)
        published=await publisher.local_participant.publish_track(track,rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
        await asyncio.wait_for(published.wait_for_subscription(),8)
        transport.begin_capture(epoch,"sender","verification")
        for index in range(50):
            samples=[int(10000*math.sin(2*math.pi*440*(index*320+i)/16000)) for i in range(320)]
            await source.capture_frame(rtc.AudioFrame(data=struct.pack("<320h",*samples),sample_rate=16000,num_channels=1,samples_per_channel=320))
        await source.wait_for_playout();await asyncio.sleep(.2)
        captured=transport.finish_capture(epoch,"sender","verification")
        with wave.open(io.BytesIO(captured)) as audio:frames=audio.getnframes()
        if frames<8000:raise AssertionError("No sustained real RTC microphone input")
        if any(value>500 for mode,value in received if mode=="raw"):
            raise AssertionError("Private microphone leaked to recipient")
        denied=False
        try:
            forbidden=rtc.LocalAudioTrack.create_audio_track("forbidden",source)
            await recipient.local_participant.publish_track(forbidden,rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
        except Exception:denied=True
        if not denied:raise AssertionError("Receive-only participant published")
        if not recipient.isconnected():raise AssertionError("Publication check lost the receiver connection")
        phase[0]="approved"
        await transport.send(epoch,"recipient",wav.read_bytes())
        await asyncio.sleep(.2)
        audible=sum(value>500 for mode,value in received if mode=="approved")
        if audible<20:raise AssertionError("Approved audio was not decoded")
        await transport.disconnect(epoch);await rooms.close("local-verification")
        claims=jwt.decode(ingress,config["secret"],algorithms=["HS256"],issuer=config["key"])
        if claims["exp"]<time.time()+5:raise AssertionError("Capability expired before the closed-room check")
        rejected=False
        try:await asyncio.wait_for(stale.connect(authority.url,ingress),5)
        except Exception as error:rejected="404" in str(error) or "does not exist" in str(error)
        if not rejected:raise AssertionError("Old capability recreated a deleted room")
        if await admin.list(authority.rooms(epoch,record["members"])):
            raise AssertionError("Room deletion not confirmed")
        reservation=next(r for r in admission.snapshot()["reservations"] if r["lesson_id"]==epoch)
        if reservation["state"]!="COMPLETED":raise AssertionError("Admission slot was not settled")
        return {"result":"PASS","real_rtc_microphone_samples":frames,"raw_microphone_leaked":False,
                "approved_decoded_frames":audible,"receive_only_publish_denied":True,
                "stale_token_denied":True,"admission":"COMPLETED"}
    finally:
        for task in readers:task.cancel()
        await asyncio.gather(*readers,return_exceptions=True)
        await transport.disconnect(epoch)
        await publisher.disconnect();await recipient.disconnect();await stale.disconnect()
        if source:await source.aclose()
        await rooms.close("local-verification")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials",required=True,type=Path)
    parser.add_argument("--data-dir",required=True,type=Path)
    parser.add_argument("--wav",required=True,type=Path)
    args=parser.parse_args()
    if not args.data_dir.is_absolute() or not args.data_dir.is_dir():
        parser.error("Use an existing absolute test directory")
    result=asyncio.run(verify(json.loads(args.credentials.read_text()),args.data_dir,args.wav))
    print(json.dumps(result))
