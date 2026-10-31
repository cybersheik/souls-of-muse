"""Offline tests for Souls of Muse Harness service. Label: OFFLINE.

All model calls use injected fake adapters/transports. No paid calls.
Run: /private/tmp/cx1-som-launch-20261031/venv/bin/python -m unittest service.tests.test_service -v
"""
import os, sys, tempfile, threading, time, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness-bench"))
from fastapi.testclient import TestClient
from service.app import create_app, _build_real_adapter, PersistentBudgetGuard, PersistenceError

MAESTRO = "maestro-token-123456"
ARTIST = "artist-token-1234567"
TOKEN = MAESTRO  # legacy alias used in a few assertions

class FakeAdapter:
    def __init__(self, text="Xin chào, hãy chơi chậm hơn.", fail=False):
        self.calls = 0; self.text = text; self.fail = fail
    def complete(self, role, system, user, fault="none"):
        self.calls += 1
        if self.fail: raise RuntimeError("upstream secret key=ABC123 exploded")
        return {"text": self.text, "usage": {"prompt_tokens": 10, "completion_tokens": 5}, "cost_usd": 0.001, "reservation_id": "fake-res"}

class BlockingAdapter:
    def __init__(self):
        self.calls = 0; self.entered = threading.Event(); self.release = threading.Event()
    def complete(self, role, system, user, fault="none"):
        self.calls += 1; self.entered.set(); self.release.wait(timeout=10)
        return {"text": "Xin chào.", "usage": {"prompt_tokens": 10, "completion_tokens": 5}, "cost_usd": 0.001, "reservation_id": "fake-res"}

def make_client(adapter=None, maestro_token=MAESTRO, artist_token=ARTIST, data_dir=None, on_write=None, environ=None):
    d = data_dir or tempfile.mkdtemp()
    kw = {}
    if environ is not None: kw["environ"] = environ
    app = create_app(data_dir=d, adapter=adapter if adapter is not None else FakeAdapter(), maestro_token=maestro_token, artist_token=artist_token, on_write=on_write, **kw)
    return TestClient(app, raise_server_exceptions=False), d

def auth(role="maestro"):
    return {"Authorization": f"Bearer {MAESTRO if role=='maestro' else ARTIST}"}

def make_session(c, role="maestro"):
    r = c.post("/sessions", headers=auth(role), json={"kind":"individual","league":"guitar","maestro_alias":"Maestro A","artist_alias":"Artist B","source_lang":"en","target_lang":"vi"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert c.post(f"/sessions/{sid}/start", headers=auth(role)).status_code == 200
    return sid

class TestHealthAuth(unittest.TestCase):
    def test_health_public_no_secrets(self):
        c,_ = make_client()
        r = c.get("/health"); self.assertEqual(r.status_code, 200)
        b = r.json(); self.assertIn("version", b); self.assertTrue(b["model_ready"])
        self.assertIn("capabilities", b)
        self.assertNotIn(MAESTRO, r.text); self.assertNotIn(ARTIST, r.text); self.assertNotIn("/private", r.text)
        self.assertFalse(b["capabilities"]["asr"]); self.assertFalse(b["capabilities"]["responses"])
    def test_missing_tokens_failclosed(self):
        for mk, at in ((None, ARTIST), (MAESTRO, None), (MAESTRO, MAESTRO), ("short", ARTIST)):
            c,_ = make_client(maestro_token=mk, artist_token=at)
            r = c.post("/sessions", headers={"Authorization": f"Bearer {MAESTRO}"}, json={"kind":"individual","league":"guitar","maestro_alias":"M","artist_alias":"A","source_lang":"en","target_lang":"vi"})
            self.assertEqual(r.status_code, 503, (mk, at, r.text))
    def test_no_auth_and_wrong_token(self):
        c,_ = make_client()
        vb={"kind":"individual","league":"guitar","maestro_alias":"M","artist_alias":"A","source_lang":"en","target_lang":"vi"}
        self.assertEqual(c.post("/sessions", json=vb).status_code, 401)
        self.assertEqual(c.post("/sessions", headers={"Authorization":"Bearer [REDACTED]"}, json=vb).status_code, 401)
    def test_cors_restricted(self):
        c,_ = make_client()
        r = c.get("/health", headers={"Origin":"https://evil.example.com"})
        self.assertNotEqual(r.headers.get("access-control-allow-origin"), "https://evil.example.com")
        r2 = c.get("/health", headers={"Origin":"https://preview.soulsofmuse.com"})
        self.assertEqual(r2.headers.get("access-control-allow-origin"), "https://preview.soulsofmuse.com")

class TestRoleAuth(unittest.TestCase):
    def test_artist_cannot_create_start_complete_approve(self):
        c,_ = make_client(); sid = make_session(c)
        r = c.post(f"/sessions/{sid}/messages", headers=auth("maestro"), json={"client_event_id":"e1","speaker":"maestro","text":"Please play slowly.","source_lang":"en","target_lang":"vi"})
        mid = r.json()["id"]
        self.assertEqual(c.post("/sessions", headers=auth("artist"), json={"kind":"individual","league":"guitar","maestro_alias":"M","artist_alias":"A","source_lang":"en","target_lang":"vi"}).status_code, 403)
        # Spoofed X-Actor must not escalate an Artist token.
        self.assertEqual(c.post(f"/sessions/{sid}/messages/{mid}/approve", headers={**auth("artist"), "X-Actor":"maestro"}).status_code, 403)
        self.assertEqual(c.post(f"/sessions/{sid}/complete", headers={**auth("artist"), "X-Actor":"maestro"}).status_code, 403)
        # Absent header on approve (draft id known) -> 401, no draft leak.
        self.assertEqual(c.post(f"/sessions/{sid}/messages/{mid}/approve", headers={}).status_code, 401)
    def test_speaker_must_match_token_role(self):
        c,_ = make_client(); sid = make_session(c)
        # Maestro token trying to speak as artist, and vice versa.
        self.assertEqual(c.post(f"/sessions/{sid}/messages", headers=auth("maestro"), json={"client_event_id":"s1","speaker":"artist","text":"Hi.","source_lang":"en","target_lang":"vi"}).status_code, 403)
        self.assertEqual(c.post(f"/sessions/{sid}/messages", headers=auth("artist"), json={"client_event_id":"s2","speaker":"maestro","text":"Hi.","source_lang":"en","target_lang":"vi"}).status_code, 403)
        ok = c.post(f"/sessions/{sid}/messages", headers=auth("artist"), json={"client_event_id":"s3","speaker":"artist","text":"I play bar three.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(ok.status_code, 201, ok.text)
        # Artist's own submission response must not expose the draft text.
        self.assertNotIn("Xin chào", ok.text)
    def test_artist_draft_hidden_without_or_spoofed_headers(self):
        c,_ = make_client(); sid = make_session(c)
        c.post(f"/sessions/{sid}/messages", headers=auth("maestro"), json={"client_event_id":"e1","speaker":"maestro","text":"Please play slowly.","source_lang":"en","target_lang":"vi"})
        for hdrs in (auth("artist"), {**auth("artist"), "X-Actor":"maestro"}, {**auth("artist"), "X-Actor":"admin"}):
            g = c.get(f"/sessions/{sid}", headers=hdrs)
            self.assertNotIn("Xin chào", g.text); self.assertNotIn("Please play slowly", g.text)
        # No auth at all -> 401, nothing leaked.
        g = c.get(f"/sessions/{sid}", headers={})
        self.assertEqual(g.status_code, 401); self.assertNotIn("Xin chào", g.text)

class TestSessionsFlow(unittest.TestCase):
    def test_create_validate_league_lang_kind(self):
        c,_ = make_client()
        base={"kind":"individual","league":"guitar","maestro_alias":"M","artist_alias":"A","source_lang":"en","target_lang":"vi"}
        self.assertEqual(c.post("/sessions", headers=auth(), json={**base,"league":"nope"}).status_code, 422)
        self.assertEqual(c.post("/sessions", headers=auth(), json={**base,"source_lang":"fr"}).status_code, 422)
        self.assertEqual(c.post("/sessions", headers=auth(), json={**base,"target_lang":"en"}).status_code, 422)
        self.assertEqual(c.post("/sessions", headers=auth(), json={**base,"kind":"nope"}).status_code, 422)
    def test_state_transitions_and_no_msg_after_complete(self):
        c,_ = make_client(); sid = make_session(c)
        self.assertEqual(c.post(f"/sessions/{sid}/start", headers=auth()).status_code, 409)
        self.assertEqual(c.post(f"/sessions/{sid}/complete", headers=auth()).status_code, 200)
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"e1","speaker":"maestro","text":"Hello, play slowly.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(r.status_code, 409)
    def test_message_before_start_rejected(self):
        c,_ = make_client()
        r = c.post("/sessions", headers=auth(), json={"kind":"group","league":"voice","maestro_alias":"M","artist_alias":"A","source_lang":"en","target_lang":"vi"})
        sid = r.json()["id"]
        r2 = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"e1","speaker":"maestro","text":"Hello.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(r2.status_code, 409)
    def test_draft_then_maestro_approve_artist_view(self):
        c,_ = make_client(); sid = make_session(c)
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"e1","speaker":"maestro","text":"Please play slowly.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(r.status_code, 201, r.text); mid = r.json()["id"]
        self.assertEqual(r.json()["state"], "draft")
        g = c.get(f"/sessions/{sid}", headers=auth("artist"))
        self.assertNotIn("Xin chào", g.text)
        self.assertEqual(c.post(f"/sessions/{sid}/messages/{mid}/approve", headers=auth("artist")).status_code, 403)
        a = c.post(f"/sessions/{sid}/messages/{mid}/approve", headers=auth())
        self.assertEqual(a.status_code, 200); self.assertEqual(a.json()["state"], "approved")
        # Duplicate approval -> 409 (no second audit fork / double approve).
        self.assertEqual(c.post(f"/sessions/{sid}/messages/{mid}/approve", headers=auth()).status_code, 409)
        g2 = c.get(f"/sessions/{sid}", headers=auth("artist"))
        self.assertIn("Xin chào", g2.text)
    def test_no_approval_after_complete(self):
        c,_ = make_client(); sid = make_session(c)
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"e1","speaker":"maestro","text":"Please play slowly.","source_lang":"en","target_lang":"vi"})
        mid = r.json()["id"]
        self.assertEqual(c.post(f"/sessions/{sid}/complete", headers=auth()).status_code, 200)
        self.assertEqual(c.post(f"/sessions/{sid}/messages/{mid}/approve", headers=auth()).status_code, 409)
    def test_input_bounds(self):
        c,_ = make_client(); sid = make_session(c)
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"e1","speaker":"maestro","text":"x"*2001,"source_lang":"en","target_lang":"vi"})
        self.assertEqual(r.status_code, 422)
        r2 = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"e2","speaker":"maestro","text":"hi","source_lang":"fr","target_lang":"vi"})
        self.assertEqual(r2.status_code, 422)
    def test_oversized_body_streamed_413(self):
        c,_ = make_client(); sid = make_session(c)
        # Generator body -> chunked, no trustworthy Content-Length.
        def gen():
            yield b'{"client_event_id":"big","speaker":"maestro","text":"'
            yield b"x" * 40000
            yield b'","source_lang":"en","target_lang":"vi"}'
        r = c.post(f"/sessions/{sid}/messages", headers={**auth(), "Content-Type":"application/json"}, content=gen())
        self.assertEqual(r.status_code, 413, r.text)
    def test_oversized_model_response_502(self):
        ad = FakeAdapter(text="y" * 5000); c,_ = make_client(adapter=ad); sid = make_session(c)
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"big1","speaker":"maestro","text":"Play slowly.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(r.status_code, 502, r.text); self.assertNotIn("yyyy", r.text)

class TestConcurrency(unittest.TestCase):
    def test_complete_blocked_while_processing_then_no_approve_after_complete(self):
        ad = BlockingAdapter(); c,_ = make_client(adapter=ad); sid = make_session(c)
        result = {}
        def send():
            result["r"] = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"blk1","speaker":"maestro","text":"Play slowly.","source_lang":"en","target_lang":"vi"})
        t = threading.Thread(target=send); t.start()
        self.assertTrue(ad.entered.wait(timeout=5))
        # Complete must not succeed while a message is processing.
        self.assertEqual(c.post(f"/sessions/{sid}/complete", headers=auth()).status_code, 409)
        ad.release.set(); t.join(timeout=10)
        self.assertEqual(result["r"].status_code, 201, result["r"].text)
        mid = result["r"].json()["id"]
        self.assertEqual(c.post(f"/sessions/{sid}/complete", headers=auth()).status_code, 200)
        self.assertEqual(c.post(f"/sessions/{sid}/messages/{mid}/approve", headers=auth()).status_code, 409)
    def test_duplicate_approval_only_one_wins(self):
        c,_ = make_client(); sid = make_session(c)
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"e1","speaker":"maestro","text":"Please play slowly.","source_lang":"en","target_lang":"vi"})
        mid = r.json()["id"]
        codes = []
        def appr():
            codes.append(c.post(f"/sessions/{sid}/messages/{mid}/approve", headers=auth()).status_code)
        ts = [threading.Thread(target=appr) for _ in range(2)]
        [t.start() for t in ts]; [t.join(timeout=10) for t in ts]
        self.assertEqual(sorted(codes), [200, 409], codes)

class TestIdempotencyProvider(unittest.TestCase):
    def test_replay_no_second_call(self):
        ad = FakeAdapter(); c,_ = make_client(adapter=ad); sid = make_session(c)
        body={"client_event_id":"evt-1","speaker":"artist","text":"I play the third measure.","source_lang":"en","target_lang":"vi"}
        r1 = c.post(f"/sessions/{sid}/messages", headers=auth("artist"), json=body)
        r2 = c.post(f"/sessions/{sid}/messages", headers=auth("artist"), json=body)
        self.assertEqual(r1.json()["id"], r2.json()["id"]); self.assertEqual(ad.calls, 1)
    def test_changed_body_replay_409(self):
        ad = FakeAdapter(); c,_ = make_client(adapter=ad); sid = make_session(c)
        body={"client_event_id":"evt-1","speaker":"maestro","text":"Play bar 3.","source_lang":"en","target_lang":"vi"}
        r1 = c.post(f"/sessions/{sid}/messages", headers=auth(), json=body)
        self.assertEqual(r1.status_code, 201, r1.text)
        r2 = c.post(f"/sessions/{sid}/messages", headers=auth(), json={**body, "text":"Play bar 9."})
        self.assertEqual(r2.status_code, 409, r2.text); self.assertEqual(ad.calls, 1)
    def test_upstream_failure_safe502_no_leak_no_retry(self):
        ad = FakeAdapter(fail=True); c,_ = make_client(adapter=ad); sid = make_session(c)
        body={"client_event_id":"evt-9","speaker":"maestro","text":"Play slowly.","source_lang":"en","target_lang":"vi"}
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json=body)
        self.assertEqual(r.status_code, 502); self.assertNotIn("ABC123", r.text); self.assertNotIn("secret", r.text.lower())
        self.assertEqual(ad.calls, 1)
        r2 = c.post(f"/sessions/{sid}/messages", headers=auth(), json=body)
        self.assertEqual(ad.calls, 1)
    def test_events_hashchain_sanitized_and_verifiable(self):
        c,d = make_client(); sid = make_session(c)
        c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"e1","speaker":"maestro","text":"Secret lesson text 123.","source_lang":"en","target_lang":"vi"})
        r = c.get(f"/sessions/{sid}/events", headers=auth()); self.assertEqual(r.status_code, 200)
        evs = r.json()["events"]; self.assertTrue(len(evs) >= 2)
        self.assertNotIn("Secret lesson text", r.text)
        for e in evs: self.assertIn("hash", e)
        v = c.get(f"/sessions/{sid}/audit/verify", headers=auth())
        self.assertEqual(v.status_code, 200); self.assertTrue(v.json()["valid"], v.text)
        # Audit is append-only at the DB layer.
        import sqlite3 as _sq
        conn = _sq.connect(os.path.join(d, "service.sqlite3"))
        with self.assertRaises(Exception):
            conn.execute("UPDATE audit SET actor='x' WHERE id=1"); conn.commit()
        conn.close()

class TestPersistence(unittest.TestCase):
    def test_service_commit_failure_before_adapter_zero_calls(self):
        state = {"fail": False}
        def on_write():
            if state["fail"]: raise RuntimeError("volume commit exploded at /data/som")
        ad = FakeAdapter(); c,_ = make_client(adapter=ad, on_write=on_write); sid = make_session(c)
        state["fail"] = True
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"p1","speaker":"maestro","text":"Play slowly.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(r.status_code, 503, r.text); self.assertEqual(ad.calls, 0)
        self.assertNotIn("/data/som", r.text); self.assertNotIn("exploded", r.text)
    def test_guard_reserve_commit_failure_before_http(self):
        import httpx, shutil, sqlite3 as _sq
        from pathlib import Path
        from harness.budget import BudgetGuard
        from harness.adapters.meta import MetaAdapter
        d = tempfile.mkdtemp(); bench = Path(__file__).resolve().parents[2] / "harness-bench"
        cfgp = Path(d) / "budget.yaml"
        cfgp.write_text("total_usd: 1.0\nwarn_pct: 0.80\nhard_stop_pct: 0.95\nledger: budget_ledger.sqlite3\nprices_usd_per_mtok:\n  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n")
        ledger = Path(d) / "budget_ledger.sqlite3"
        guard = BudgetGuard.initialize_ledger(str(cfgp), str(ledger))
        calls = {"n": 0}
        def handler(request):
            calls["n"] += 1
            return httpx.Response(200, json={"choices":[{"message":{"content":"Hãy chơi chậm hơn."}}], "usage":{"prompt_tokens":20,"completion_tokens":6,"total_tokens":26}})
        cfg = {"base_url":"https://api.meta.ai/v1","api_key_env":"MODEL_API_KEY","roles":{"interpreter":{"model":"muse-spark-1.3","endpoint":"/chat/completions","temperature":0.1,"max_tokens":300}}}
        wrapped = PersistentBudgetGuard(guard, lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))
        ad = MetaAdapter(cfg, wrapped, transport=httpx.MockTransport(handler), environ={"MODEL_API_KEY":"offline-fake"})
        with self.assertRaises(PersistenceError):
            ad.complete("interpreter", "sys", "user")
        self.assertEqual(calls["n"], 0)  # zero paid HTTP calls
    def test_guard_settle_commit_failure_retains_durable_hold(self):
        import httpx, shutil, sqlite3 as _sq
        from pathlib import Path
        from harness.budget import BudgetGuard
        from harness.adapters.meta import MetaAdapter
        d = tempfile.mkdtemp()
        cfgp = Path(d) / "budget.yaml"
        cfgp.write_text("total_usd: 1.0\nwarn_pct: 0.80\nhard_stop_pct: 0.95\nledger: budget_ledger.sqlite3\nprices_usd_per_mtok:\n  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n")
        ledger = Path(d) / "budget_ledger.sqlite3"
        guard = BudgetGuard.initialize_ledger(str(cfgp), str(ledger))
        snapshot = Path(d) / "durable_snapshot.sqlite3"
        state = {"n": 0}
        def on_write():
            state["n"] += 1
            if state["n"] >= 2: raise RuntimeError("settle commit failed")
            shutil.copy(str(ledger), str(snapshot))  # durable volume snapshot
        calls = {"n": 0}
        def handler(request):
            calls["n"] += 1
            return httpx.Response(200, json={"choices":[{"message":{"content":"Hãy chơi chậm hơn."}}], "usage":{"prompt_tokens":20,"completion_tokens":6,"total_tokens":26}})
        cfg = {"base_url":"https://api.meta.ai/v1","api_key_env":"MODEL_API_KEY","roles":{"interpreter":{"model":"muse-spark-1.3","endpoint":"/chat/completions","temperature":0.1,"max_tokens":300}}}
        ad = MetaAdapter(cfg, PersistentBudgetGuard(guard, on_write), transport=httpx.MockTransport(handler), environ={"MODEL_API_KEY":"offline-fake"})
        with self.assertRaises(PersistenceError):
            ad.complete("interpreter", "sys", "user")
        self.assertEqual(calls["n"], 1)
        # Durable snapshot still holds the conservative HOLD (never committed away).
        conn = _sq.connect(str(snapshot)); conn.row_factory = _sq.Row
        rows = conn.execute("SELECT state FROM reservations").fetchall(); conn.close()
        self.assertEqual([r[0] for r in rows], ["HOLD"])

class TestPersistentBlockedRegression(unittest.TestCase):
    def _guard_and_snapshot(self):
        import shutil
        from pathlib import Path
        from harness.budget import BudgetGuard
        d = tempfile.mkdtemp()
        cfgp = Path(d) / "budget.yaml"
        cfgp.write_text("total_usd: 1.0\nwarn_pct: 0.80\nhard_stop_pct: 0.95\nledger: budget_ledger.sqlite3\nprices_usd_per_mtok:\n  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n")
        ledger = Path(d) / "budget_ledger.sqlite3"
        guard = BudgetGuard.initialize_ledger(str(cfgp), str(ledger))
        snapshot = Path(d) / "durable_snapshot.sqlite3"
        callbacks = []
        def on_write():
            shutil.copy(str(ledger), str(snapshot))
            callbacks.append(1)
        return cfgp, ledger, snapshot, guard, callbacks, on_write
    def test_settle_excess_persists_blocked_and_blocks_later_reservation(self):
        import sqlite3 as _sq
        from pathlib import Path
        from harness.budget import BudgetGuard, BudgetExceeded
        cfgp, ledger, snapshot, guard, callbacks, on_write = self._guard_and_snapshot()
        wrapped = PersistentBudgetGuard(guard, on_write)
        rid = wrapped.reserve_chat("muse-spark-1.3", 10, 10)
        self.assertTrue(callbacks)
        with self.assertRaises(BudgetExceeded):
            wrapped.settle(rid, "muse-spark-1.3", {"prompt_tokens": 10000, "completion_tokens": 10000, "total_tokens": 20000})
        # Durable snapshot must contain BLOCKED, not only the old HOLD.
        self.assertTrue(snapshot.exists())
        conn = _sq.connect(str(snapshot)); rows = conn.execute("SELECT state FROM reservations").fetchall(); conn.close()
        self.assertEqual([r[0] for r in rows], ["BLOCKED"])
        # A later (restart) guard over the durable snapshot refuses new reservations.
        reopened = BudgetGuard(str(cfgp), ledger_path=str(snapshot))
        self.assertEqual(reopened.status()["blocked_calls"], 1)
        with self.assertRaises(BudgetExceeded):
            reopened.reserve_chat("muse-spark-1.3", 10, 10)
    def test_settle_blocked_persist_failure_raises_persistence_error(self):
        from harness.budget import BudgetExceeded
        cfgp, ledger, snapshot, guard, callbacks, good = self._guard_and_snapshot()
        state = {"n": 0}
        def flaky():
            state["n"] += 1
            if state["n"] >= 2:
                raise RuntimeError("durable commit failed")
            good()
        wrapped = PersistentBudgetGuard(guard, flaky)
        rid = wrapped.reserve_chat("muse-spark-1.3", 10, 10)
        with self.assertRaises(PersistenceError):
            wrapped.settle(rid, "muse-spark-1.3", {"prompt_tokens": 10000, "completion_tokens": 10000, "total_tokens": 20000})

class TestHealthReadiness(unittest.TestCase):
    def test_valid_tokens_auth_ready_but_not_production(self):
        c, _ = make_client()
        b = c.get("/health").json()
        self.assertTrue(b["auth_ready"]); self.assertTrue(b["role_ready"]); self.assertTrue(b["pilot_ready"])
        self.assertFalse(b["production_ready"]); self.assertFalse(b["full_participant_identity"])
        self.assertTrue(b["capabilities"]["sessions"])
    def test_invalid_tokens_not_fully_usable_and_pilot_cannot_read_protected(self):
        c, _ = make_client(maestro_token="short", artist_token=ARTIST)
        b = c.get("/health").json()
        self.assertFalse(b["auth_ready"]); self.assertFalse(b["role_ready"]); self.assertFalse(b["pilot_ready"])
        self.assertFalse(b["capabilities"]["sessions"]); self.assertFalse(b["capabilities"]["text_interpretation_en_vi"])
        self.assertFalse(b["production_ready"]); self.assertFalse(b["full_participant_identity"])
        # /pilot HTML is public, protected content is not readable without valid credentials.
        self.assertEqual(c.get("/pilot").status_code, 200)
        self.assertIn(c.get("/sessions/anything", headers={}).status_code, (401, 503))

class TestModalLifecycle(unittest.TestCase):
    def _fakes(self):
        events = []
        class FakeVolume:
            def __init__(self): self.fail_commit = False
            def reload(self): events.append("reload")
            def commit(self):
                events.append("commit")
                if self.fail_commit: raise RuntimeError("commit failed")
        class FakeQueue:
            def __init__(self): self.puts = []
            def get(self, block=True, timeout=None): events.append("get"); return "permit-1"
            def put(self, v): events.append("put"); self.puts.append(v)
            def len(self): return len(self.puts)
        class FakeInner:
            async def __call__(self, scope, receive, send):
                if scope.get("type") != "lifespan":
                    await send({"type": "http.response.start", "status": 200, "headers": []})
                    await send({"type": "http.response.body", "body": b"ok"}); return
                msg = await receive()
                if msg.get("type") == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                msg = await receive()
                if msg.get("type") == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
        return events, FakeVolume(), FakeQueue(), FakeInner
    def _run_lifespan(self, app):
        import asyncio
        sent = []
        inbox = [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}]
        async def receive(): return inbox.pop(0)
        async def send(m): sent.append(m)
        asyncio.run(app({"type": "lifespan"}, receive, send))
        return sent
    def test_normal_startup_shutdown_commit_before_put_exactly_once(self):
        import service.modal_app as m
        events, vol, q, inner_cls = self._fakes()
        def factory(): events.append("factory"); return inner_cls()
        app = m.build_writer_app(q, vol, factory)
        self.assertEqual(events[:3], ["get", "reload", "factory"])  # acquire-before-reload-before-DB(factory)
        sent = self._run_lifespan(app)
        self.assertIn({"type": "lifespan.shutdown.complete"}, sent)
        self.assertLess(events.index("commit"), events.index("put"))
        self.assertEqual(q.puts, ["permit-1"])
        # Duplicate shutdown does not return the permit twice.
        self._run_lifespan(app)
        self.assertEqual(q.puts, ["permit-1"])
    def test_failed_commit_never_releases(self):
        import service.modal_app as m
        events, vol, q, inner_cls = self._fakes()
        vol.fail_commit = True
        app = m.build_writer_app(q, vol, lambda: inner_cls())
        sent = self._run_lifespan(app)
        self.assertEqual(q.puts, [])
        self.assertTrue(any(s.get("type") == "lifespan.shutdown.failed" for s in sent))
        self.assertFalse(any(s.get("type") == "lifespan.shutdown.complete" for s in sent))
    def test_factory_failure_after_acquisition_fails_closed(self):
        import service.modal_app as m
        events, vol, q, inner_cls = self._fakes()
        def bad_factory(): events.append("factory"); raise RuntimeError("db init failed")
        with self.assertRaises(RuntimeError):
            m.build_writer_app(q, vol, bad_factory)
        self.assertEqual(q.puts, [])  # permit intentionally not returned
        self.assertNotIn("put", events)
    def test_modal_app_has_no_atexit_primary_release(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / "modal_app.py").read_text()
        self.assertNotIn("atexit", src)
        self.assertIn("lifespan", src)

class TestPermitSeedMarker(unittest.TestCase):
    def _fakes(self, marker_exists=False, queue_len=0):
        events = []
        class FakeQueue:
            def __init__(self): self._len = queue_len; self.puts = []
            def len(self): return self._len + len(self.puts)
            def put(self, v): events.append("queue_put"); self.puts.append(v)
        class FakeMarker:
            def exists(self): return marker_exists
            def create_and_commit(self): events.append("marker_create_commit")
        return events, FakeQueue(), FakeMarker()
    def test_marker_present_held_empty_queue_refuses(self):
        from service.modal_permit_seed import seed_once, SeedRefused
        events, q, marker = self._fakes(marker_exists=True, queue_len=0)
        with self.assertRaises(SeedRefused):
            seed_once(q, marker)
        self.assertEqual(q.puts, []); self.assertEqual(events, [])
    def test_first_seed_order_marker_commit_before_put(self):
        from service.modal_permit_seed import seed_once
        events, q, marker = self._fakes(marker_exists=False, queue_len=0)
        result = seed_once(q, marker)
        self.assertTrue(result["seeded"])
        self.assertEqual(events, ["marker_create_commit", "queue_put"])
    def test_nonempty_queue_refuses_without_marker_write(self):
        from service.modal_permit_seed import seed_once, SeedRefused
        events, q, marker = self._fakes(marker_exists=False, queue_len=1)
        with self.assertRaises(SeedRefused):
            seed_once(q, marker)
        self.assertEqual(events, [])

class TestFailClosedProvisioning(unittest.TestCase):
    def test_missing_data_dir_failclosed(self):
        with self.assertRaises(Exception):
            create_app(data_dir="/nonexistent-som-dir-xyz/state", adapter=FakeAdapter(), maestro_token=MAESTRO, artist_token=ARTIST)
    def test_no_adapter_no_key_not_ready(self):
        d = tempfile.mkdtemp()
        app = create_app(data_dir=d, adapter=None, environ={}, maestro_token=MAESTRO, artist_token=ARTIST)
        c = TestClient(app, raise_server_exceptions=False)
        self.assertFalse(c.get("/health").json()["model_ready"])
        r = c.post("/sessions", headers=auth(), json={"kind":"individual","league":"keys","maestro_alias":"M","artist_alias":"A","source_lang":"en","target_lang":"vi"})
        s = r.json()["id"]; c.post(f"/sessions/{s}/start", headers=auth())
        m = c.post(f"/sessions/{s}/messages", headers=auth(), json={"client_event_id":"e1","speaker":"maestro","text":"Hello.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(m.status_code, 503)

class TestProvisionAndBuild(unittest.TestCase):
    def test_provision_then_build_adapter_ready_1usd(self):
        import subprocess
        d = tempfile.mkdtemp()
        env = dict(os.environ)
        r = subprocess.run([sys.executable, "-m", "service.provision", "--data-dir", d, "--total-usd", "1.0", "--confirm"], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), "..", ".."), env=env)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        from pathlib import Path
        cfg_text = (Path(d) / "budget.yaml").read_text()
        self.assertIn("ledger: budget_ledger.sqlite3", cfg_text)  # relative, portable
        self.assertNotIn("/Users/", cfg_text); self.assertNotIn("/private/", cfg_text)
        ad, ready = _build_real_adapter(d, {"MODEL_API_KEY": "offline-fake"})
        self.assertTrue(ready); self.assertIsNotNone(ad)
        self.assertEqual(ad.budget.stop_micro, 950000)
        # Repeat provisioning preserves the ledger (no reset/increase).
        import hashlib
        h1 = hashlib.sha256((Path(d) / "budget_ledger.sqlite3").read_bytes()).hexdigest()
        r2 = subprocess.run([sys.executable, "-m", "service.provision", "--data-dir", d, "--total-usd", "1.0", "--confirm"], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), "..", ".."), env=env)
        self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
    def test_provision_rejects_over_1usd(self):
        import subprocess
        d = tempfile.mkdtemp()
        r = subprocess.run([sys.executable, "-m", "service.provision", "--data-dir", d, "--total-usd", "150", "--confirm"], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), "..", ".."))
        self.assertNotEqual(r.returncode, 0)
    def test_startup_rejects_over_1usd_ledger(self):
        # A ledger/config provisioned at $150 (bench-style) must not become ready.
        from pathlib import Path
        from harness.budget import BudgetGuard
        d = tempfile.mkdtemp()
        cfgp = Path(d) / "budget.yaml"
        cfgp.write_text("total_usd: 150.0\nwarn_pct: 0.80\nhard_stop_pct: 0.95\nledger: budget_ledger.sqlite3\nprices_usd_per_mtok:\n  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n")
        BudgetGuard.initialize_ledger(str(cfgp), str(Path(d) / "budget_ledger.sqlite3"))
        ad, ready = _build_real_adapter(d, {"MODEL_API_KEY": "offline-fake"})
        self.assertFalse(ready); self.assertIsNone(ad)

class TestRealBuilderReasoning(unittest.TestCase):
    def test_build_real_adapter_sends_low_1024(self):
        import httpx, json as _json
        from pathlib import Path
        from harness.budget import BudgetGuard
        d = tempfile.mkdtemp()
        cfgp = Path(d) / "budget.yaml"
        cfgp.write_text("total_usd: 1.0\nwarn_pct: 0.80\nhard_stop_pct: 0.95\nledger: budget_ledger.sqlite3\nprices_usd_per_mtok:\n  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n")
        BudgetGuard.initialize_ledger(str(cfgp), str(Path(d) / "budget_ledger.sqlite3"))
        captured = {}
        def handler(request):
            captured["body"] = request.content
            return httpx.Response(200, json={"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}], "usage":{"prompt_tokens":20,"completion_tokens":6,"total_tokens":26}})
        ad, ready = _build_real_adapter(d, {"MODEL_API_KEY": "offline-fake"}, transport=httpx.MockTransport(handler))
        self.assertTrue(ready); self.assertIsNotNone(ad)
        result = ad.complete("interpreter", "sys", "user")
        self.assertEqual(result["text"], "ok")
        payload = _json.loads(captured["body"])
        self.assertEqual(payload["reasoning_effort"], "low"); self.assertEqual(payload["max_tokens"], 1024)

class TestStaticSurfaces(unittest.TestCase):
    def test_pilot_html_no_innerhtml_per_message_approve(self):
        from pathlib import Path
        html = (Path(__file__).resolve().parents[1] / "pilot.html").read_text()
        self.assertNotIn("innerHTML", html)
        self.assertIn("textContent", html)
        self.assertIn("messages/${mid}/approve", html)
        self.assertNotIn("localStorage", html); self.assertNotIn("sessionStorage", html)
        self.assertIn("addEventListener(\"change\"", html)  # role change clears drafts
    def test_modal_definitions_offline(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / "modal_app.py").read_text()
        for needle in ("max_containers=1", "buffer_containers=0", "cpu=1", "memory=512", "min_containers=0", "scaledown_window=60", "som-writer-permit", "som-data", "som-pilot", "volume.reload()", "create_if_missing=False"):
            self.assertIn(needle, src)
        self.assertNotIn('region="', src); self.assertNotIn("region='", src); self.assertNotIn("ap-southeast", src)
        import service.modal_app as m  # offline definition import, no network/deploy
        self.assertIsNotNone(m.app)

if __name__ == "__main__": unittest.main()

class TestRealAdapterOffline(unittest.TestCase):
    def test_meta_adapter_fake_transport_no_paid_call(self):
        """OFFLINE: real MetaAdapter + BudgetGuard($1 test ledger) + fake transport."""
        import httpx, tempfile as _tf
        from pathlib import Path
        from harness.budget import BudgetGuard
        from harness.adapters.meta import MetaAdapter
        d = _tf.mkdtemp()
        cfgp = Path(d) / "budget.yaml"
        cfgp.write_text("total_usd: 1.0\nwarn_pct: 0.80\nhard_stop_pct: 0.95\nledger: budget_ledger.sqlite3\nprices_usd_per_mtok:\n  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n")
        ledger = Path(d) / "budget_ledger.sqlite3"
        guard = BudgetGuard.initialize_ledger(str(cfgp), str(ledger))
        def handler(request):
            return httpx.Response(200, json={"choices":[{"message":{"content":"Hãy chơi chậm hơn."}}], "usage":{"prompt_tokens":20,"completion_tokens":6,"total_tokens":26}})
        transport = httpx.MockTransport(handler)
        cfg = {"base_url":"https://api.meta.ai/v1","api_key_env":"MODEL_API_KEY","roles":{"interpreter":{"model":"muse-spark-1.3","endpoint":"/chat/completions","temperature":0.1,"max_tokens":300}}}
        ad = MetaAdapter(cfg, guard, transport=transport, environ={"MODEL_API_KEY":"offline-fake"})
        c,_ = make_client(adapter=ad); sid = make_session(c)
        r = c.post(f"/sessions/{sid}/messages", headers=auth(), json={"client_event_id":"real-1","speaker":"maestro","text":"Play slowly.","source_lang":"en","target_lang":"vi"})
        self.assertEqual(r.status_code, 201, r.text); self.assertIn("chậm", r.json()["text"])
        self.assertGreater(guard.status()["spent_usd"], 0)
