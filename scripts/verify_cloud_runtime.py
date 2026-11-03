"""Exercise the shipped Python runtime without provider calls or cloud access.

Run in a fresh environment installed ONLY from service/requirements.txt.
All accounts, keys, ledgers and lesson data below are disposable test fixtures.
The second phase runs in a new Python process; this is not a Modal cold start.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "harness-bench"))
PREFIX = "/api/harness"
ORIGIN = "https://soulsofmuse.app"


def require(condition, description):
    if not condition:
        raise RuntimeError(description)


async def native_audio():
    # Import and exercise the native FFI, not merely the control-plane API.
    # No room connection, SFU, microphone or remote participant is used.
    from livekit import rtc
    source = rtc.AudioSource(16000, 1, queue_size_ms=200)
    try:
        frame = rtc.AudioFrame(data=b"\x00\x00" * 320, sample_rate=16000,
                               num_channels=1, samples_per_channel=320)
        await asyncio.wait_for(source.capture_frame(frame), 5)
        await asyncio.wait_for(source.wait_for_playout(), 5)
    finally:
        await source.aclose()


def phase(directory, restart):
    import httpx
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from harness.budget import BudgetGuard
    from heart import verify
    from service.app import create_app
    from service.identity import password_hash

    state = directory / "fixture.json"
    if restart:
        fixture = json.loads(state.read_text())
    else:
        fixture = {"accounts": {user: {"role": role,
                    "password_hash": password_hash("runtime-fixture-password")}
                    for user, role in (("M", "maestro"), ("A", "artist"))}}
        (directory / "budget.yaml").write_text(
            "total_usd: 0.05\nwarn_pct: 0.80\nhard_stop_pct: 0.95\n"
            "ledger: budget_ledger.sqlite3\nprices_usd_per_mtok:\n"
            "  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n")
        BudgetGuard.initialize_ledger(str(directory / "budget.yaml"),
                                      str(directory / "budget_ledger.sqlite3"))

    config = {"MODEL_API_KEY": "invalid-runtime-fixture-key",
              "SOM_WEB_ACCOUNTS": json.dumps(fixture["accounts"])}
    # A fixed, public TEST key lets independent processes verify the same chain.
    key = Ed25519PrivateKey.from_private_bytes(b"\x01" * 32)
    durable_commits = []
    def commit():
        durable_commits.append(True)  # local disk only, NOT Modal Volume.commit
    def forbidden(*args, **kwargs):
        raise RuntimeError("runtime check must not make an outbound HTTP request")

    with patch.object(httpx.HTTPTransport, "handle_request", forbidden), \
         patch.object(httpx.AsyncHTTPTransport, "handle_async_request", forbidden):
        app = create_app(data_dir=str(directory), environ=config, heart_key=key,
                         on_write=commit)
        site = FastAPI()
        site.mount(PREFIX, app)
        with TestClient(site, base_url=ORIGIN) as m, TestClient(site, base_url=ORIGIN) as a:
            for client, user in ((m, "M"), (a, "A")):
                client.headers.update({"Origin": ORIGIN, "X-SOM-Participant": user})
                if restart:
                    client.cookies.update(fixture["cookies"][user])
                else:
                    r = client.post(PREFIX + "/auth/login", json={
                        "username": user, "password": "runtime-fixture-password"})
                    require(r.status_code == 200, "participant login failed")
                    require("HttpOnly" in r.headers["set-cookie"] and
                            "Secure" in r.headers["set-cookie"], "cookie protection missing")
                r = client.get(PREFIX + "/auth/me")
                require(r.status_code == 200 and r.json()["id"] == user,
                        "participant cookie did not survive process startup")
            health = m.get(PREFIX + "/health").json()
            require(health["version"] == "0.3.0" and health["pilot_ready"],
                    "runtime configuration/glossary/adapter failed to load")
            require(health["capabilities"]["responses"] and
                    health["capabilities"]["heart_journal_integration"], "shipped resources missing")
            require(not health["production_ready"] and not health["capabilities"]["tts"]
                    and not health["capabilities"]["private_media_transport"],
                    "optional services unexpectedly enabled")
            r = m.options(PREFIX + "/health", headers={"Access-Control-Request-Method": "GET"})
            require(r.status_code == 200 and r.headers.get("access-control-allow-origin") == ORIGIN,
                    "primary Origin CORS rejected")
            if not restart:
                r = m.post(PREFIX + "/sessions", json={"kind": "individual", "league": "string",
                    "maestro_alias": "Maestro", "artist_alias": "Artist", "artist_id": "A",
                    "source_lang": "en", "target_lang": "vi"})
                require(r.status_code == 201, "meeting creation failed")
                fixture["sid"] = r.json()["id"]
            route = PREFIX + "/sessions/" + fixture["sid"]
            if not restart:
                require(a.post(route + "/start").status_code == 403, "Artist started meeting")
                require(m.post(route + "/start").status_code == 200, "Maestro start failed")
                for client, user in ((m, "M"), (a, "A")):
                    require(client.post(route + "/join").status_code == 200, "presence failed")
                    require(client.post(route + "/notes", json={"revision": 0,
                        "text": "Private fixture " + user}).status_code == 200, "notes write failed")
                worksheet = {"revision": 0, "plan": [{"title": "Pulse", "duration": "2 min",
                    "goal": "Keep time.", "tips": ["Count four beats."]}], "step": 0,
                    "notebook": {"chords": ["Am"], "notation": "", "tabs": ""}}
                require(m.post(route + "/lesson", json=worksheet).status_code == 200,
                        "worksheet write failed")
                require(m.post(route + "/complete").status_code == 200, "meeting completion failed")
                fixture["cookies"] = {"M": dict(m.cookies), "A": dict(a.cookies)}
                with state.open("x") as stream:
                    os.chmod(state, 0o600)
                    json.dump(fixture, stream)
            for client, user in ((m, "M"), (a, "A")):
                require(client.get(route).json()["state"] == "completed", "meeting state lost")
                require(client.get(route + "/notes").json()["text"] == "Private fixture " + user,
                        "private notes lost or crossed accounts")
                require(client.get(route + "/lesson").json()["revision"] == 1, "worksheet lost")
                heart = client.get(route + "/heart").json()
                require(heart["counters"]["happened"] == 1 and
                        [r["state"] for r in heart["delivery"]] == ["delivered", "delivered"],
                        "heart completion missing or duplicated")
            pub = key.public_key().public_bytes(serialization.Encoding.Raw,
                                                serialization.PublicFormat.Raw).hex()
            require(verify.verify(str(directory / "heart.sqlite3"), pub)[0], "heart signature invalid")
            guard = BudgetGuard(str(directory / "budget.yaml"),
                                ledger_path=str(directory / "budget_ledger.sqlite3"))
            status = guard.status()
            require(guard.total_micro == 50_000 and guard.stop_micro == 47_500
                    and status["spent_usd"] == 0 and status["held_usd"] == 0,
                    "fixture ledger changed or provider work attempted")
            require(bool(durable_commits), "persistence callback not invoked")
    asyncio.run(native_audio())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "restart"))
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    if args.phase:
        require(args.directory is not None, "phase requires fixture directory")
        phase(args.directory, args.phase == "restart")
        return
    directory = Path(tempfile.mkdtemp(prefix="cx1-cloud-runtime-",
        dir="/private/tmp" if Path("/private/tmp").is_dir() else None))
    # Leave the isolated fixture directory for inspection; never touch operator data.
    for name in ("prepare", "restart"):
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--phase", name,
                        "--directory", str(directory)], cwd=ROOT, check=True, timeout=45)
    from importlib.metadata import version
    print(json.dumps({"check": "cloud_runtime", "result": "PASS",
        "fresh_python_processes": 2, "native_rtc": version("livekit"),
        "roles": ["maestro", "artist"], "primary_origin_cors": True,
        "signed_heart_restart": True, "private_notes_restart": True,
        "provider_calls": 0, "cloud_access": False, "modal_cold_start": False}))


if __name__ == "__main__":
    main()
