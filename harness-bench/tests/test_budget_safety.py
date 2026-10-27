import multiprocessing as mp
import os
import tempfile
import unittest
import wave
from pathlib import Path

import httpx

from harness.budget import BudgetGuard, BudgetExceeded, BudgetLedgerError
from harness.adapters.meta import MetaAdapter, ConfigError

FAKE_ENV = {"MODEL_API_KEY": "cx1-fake-key-not-a-real-secret"}


def write_config(root, total=150.0):
    ledger = Path(root) / ".budget_ledger.sqlite3"
    cfg = Path(root) / "budget.yaml"
    cfg.write_text(
        f"total_usd: {total}\nwarn_pct: 0.80\nhard_stop_pct: 0.95\nledger: {ledger}\n"
        "prices_usd_per_mtok:\n"
        "  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n"
        "  muse-spark-1.2: {input: 1.25, output: 4.25, cached_input: 0.15}\n"
        "  muse-wonder-1.0: {input: 4.00, output: 20.00, cached_input: 0.20}\n"
        "asr_usd_per_1000min:\n  muse-voice-transcribe-1.0: 3.0\n",
        encoding="utf-8")
    return cfg


def models_cfg(model="muse-spark-1.3", endpoint="/chat/completions", max_tokens=100):
    return {"base_url": "https://api.meta.ai/v1", "api_key_env": "MODEL_API_KEY", "roles": {
        "interpreter": {"model": model, "endpoint": endpoint, "temperature": 0.1, "max_tokens": max_tokens},
        "orchestrator": {"model": "muse-wonder-1.0", "endpoint": "/responses", "temperature": 0.1, "max_tokens": 100},
        "asr": {"model": "muse-voice-transcribe-1.0", "endpoint_file": "/asr/transcribe"},
    }}


def ok_handler(calls, usage=None):
    def handler(request):
        calls.append(1)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": usage if usage is not None else {"prompt_tokens": 10, "completion_tokens": 5}})
    return handler


def _reserve_worker(payload):
    cfg, attempts = payload
    guard = BudgetGuard(str(cfg))
    ok = 0
    for _ in range(attempts):
        try:
            guard.reserve_chat("muse-wonder-1.0", 600000, 100)
            ok += 1
        except BudgetExceeded:
            pass
    return ok


class BudgetSafetyTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cx1-budget-test-")
        self.cfg = write_config(self.root)
        self.guard = BudgetGuard.initialize_ledger(str(self.cfg))

    def adapter(self, handler, cfg=None):
        calls = []
        transport = httpx.MockTransport(handler(calls) if False else handler)
        return MetaAdapter(cfg or models_cfg(), self.guard, transport=transport, environ=FAKE_ENV), calls

    def make_adapter(self, handler_factory, cfg=None):
        calls = []
        transport = httpx.MockTransport(handler_factory(calls))
        return MetaAdapter(cfg or models_cfg(), self.guard, transport=transport, environ=FAKE_ENV), calls

    def test_missing_and_corrupt_ledger_fail_closed(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-missing-")
        cfg = write_config(root)
        with self.assertRaises(BudgetLedgerError):
            BudgetGuard(str(cfg))
        guard = BudgetGuard.initialize_ledger(str(cfg))
        ledger = Path(guard.status()["ledger"])
        ledger.write_bytes(b"not a sqlite database at all")
        with self.assertRaises(BudgetLedgerError):
            BudgetGuard(str(cfg))

    def test_legacy_json_blocks(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-legacy-")
        cfg = write_config(root)
        Path(root, ".budget_ledger.json").write_text('{"spent_usd": 1}', encoding="utf-8")
        with self.assertRaises(BudgetLedgerError):
            BudgetGuard.initialize_ledger(str(cfg))

    def test_reopen_preserves_holds_and_duplicate_settle_idempotent(self):
        rid = self.guard.reserve_chat("muse-spark-1.3", 1000, 100)
        reopened = BudgetGuard(str(self.cfg))
        self.assertGreater(reopened.status()["held_usd"], 0)
        first = reopened.settle(rid, "muse-spark-1.3", {"prompt_tokens": 100, "completion_tokens": 10})
        spent_after_first = reopened.status()["spent_usd"]
        second = reopened.settle(rid, "muse-spark-1.3", {"prompt_tokens": 999, "completion_tokens": 999})
        self.assertEqual(first, second)
        self.assertEqual(spent_after_first, reopened.status()["spent_usd"])
        self.assertEqual(reopened.status()["calls"], 1)

    def test_cached_tokens_not_double_counted(self):
        plain = self.guard.charge_tokens("muse-spark-1.3", {"prompt_tokens": 1000, "completion_tokens": 100})
        cached = self.guard.charge_tokens("muse-spark-1.3", {"prompt_tokens": 1000, "completion_tokens": 100, "prompt_cache_hit_tokens": 900})
        self.assertEqual(plain, cached)

    def test_admission_denied_sends_zero_http(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-denied-")
        cfg = write_config(root, total=1.0)
        guard = BudgetGuard.initialize_ledger(str(cfg))
        guard.reserve_chat("muse-wonder-1.0", 200000, 7000)
        calls = []
        adapter = MetaAdapter(models_cfg(model="muse-wonder-1.0"), guard, transport=httpx.MockTransport(ok_handler(calls)), environ=FAKE_ENV)
        with self.assertRaises(BudgetExceeded):
            adapter.complete("interpreter", "sys", "hello")
        self.assertEqual(calls, [])

    def test_successful_chat_settles_and_frees_difference(self):
        adapter, calls = self.make_adapter(ok_handler)
        result = adapter.complete("interpreter", "sys", "hello")
        self.assertEqual(result["text"], "ok")
        self.assertEqual(len(calls), 1)
        status = self.guard.status()
        self.assertEqual(status["held_usd"], 0.0)
        self.assertGreater(status["spent_usd"], 0)
        self.assertLess(status["spent_usd"], 0.01)

    def test_missing_usage_and_timeout_retain_hold(self):
        def missing(calls):
            def handler(request):
                calls.append(1)
                return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
            return handler
        adapter, _ = self.make_adapter(missing)
        with self.assertRaises(Exception):
            adapter.complete("interpreter", "sys", "hello")
        self.assertGreater(self.guard.status()["held_usd"], 0)
        root = tempfile.mkdtemp(prefix="cx1-budget-timeout-")
        cfg = write_config(root)
        guard = BudgetGuard.initialize_ledger(str(cfg))
        def timeout_handler(request):
            raise httpx.ReadTimeout("timed out", request=request)
        adapter2 = MetaAdapter(models_cfg(), guard, transport=httpx.MockTransport(timeout_handler), environ=FAKE_ENV)
        with self.assertRaises(Exception):
            adapter2.complete("interpreter", "sys", "hello")
        self.assertGreater(guard.status()["held_usd"], 0)

    def test_unknown_model_and_responses_before_http(self):
        adapter, calls = self.make_adapter(ok_handler, cfg=models_cfg(model="muse-spark-1.3-contributor"))
        with self.assertRaises(ConfigError):
            adapter.complete("interpreter", "sys", "hello")
        self.assertEqual(calls, [])
        adapter2, calls2 = self.make_adapter(ok_handler)
        with self.assertRaises(ConfigError):
            adapter2.complete("orchestrator", "sys", "hello")
        self.assertEqual(calls2, [])

    def test_excess_usage_blocks_and_disables_new_calls(self):
        def excess(calls):
            def handler(request):
                calls.append(1)
                return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 10000000, "completion_tokens": 1000}})
            return handler
        adapter, _ = self.make_adapter(excess)
        with self.assertRaises(BudgetExceeded):
            adapter.complete("interpreter", "sys", "hello")
        status = self.guard.status()
        self.assertEqual(status["state"], "blocked")
        self.assertGreater(status["blocked_usd"], 0)
        with self.assertRaises(BudgetExceeded):
            self.guard.reserve_chat("muse-spark-1.3", 10, 10)

    def test_no_secret_in_exceptions(self):
        secret = FAKE_ENV["MODEL_API_KEY"]
        def bad(calls):
            def handler(request):
                calls.append(1)
                return httpx.Response(500, json={"error": "upstream failed"})
            return handler
        adapter, _ = self.make_adapter(bad)
        try:
            adapter.complete("interpreter", "sys", "hello")
            self.fail("expected exception")
        except Exception as exc:
            self.assertNotIn(secret, str(exc))
            self.assertNotIn("Bearer", str(exc))

    def test_asr_disabled_before_http_and_wav_inspected(self):
        wav_path = Path(self.root) / "sample.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
            wf.writeframes(b"\x00\x00" * 2400)
        calls = []
        adapter = MetaAdapter(models_cfg(), self.guard, transport=httpx.MockTransport(ok_handler(calls)), environ=FAKE_ENV)
        with self.assertRaises(ConfigError):
            adapter.transcribe(str(wav_path))
        self.assertEqual(calls, [])
        self.assertEqual(self.guard.status()["held_usd"], 0.0)
        stereo = Path(self.root) / "stereo.wav"
        with wave.open(str(stereo), "wb") as wf:
            wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(24000)
            wf.writeframes(b"\x00\x00\x00\x00" * 100)
        with self.assertRaises(ConfigError):
            adapter.transcribe(str(stereo))

    def test_multiprocess_race_cannot_overspend(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-race-")
        cfg = write_config(root, total=10.0)
        BudgetGuard.initialize_ledger(str(cfg))
        ctx = mp.get_context("fork") if "fork" in mp.get_all_start_methods() else mp.get_context()
        with ctx.Pool(processes=4) as pool:
            results = pool.map(_reserve_worker, [(str(cfg), 3)] * 4)
        guard = BudgetGuard(str(cfg))
        status = guard.status()
        self.assertLessEqual(status["committed_usd"], status["stop_usd"] + 1e-9)
        self.assertGreaterEqual(sum(results), 1)
        self.assertLessEqual(sum(results), 3)


if __name__ == "__main__":
    unittest.main()
