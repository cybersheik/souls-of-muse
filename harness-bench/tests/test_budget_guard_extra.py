import tempfile
import unittest
from pathlib import Path

import httpx

from harness.budget import BudgetGuard, BudgetExceeded, BudgetLedgerError
from harness.adapters.meta import MetaAdapter, ConfigError

FAKE_ENV = {"MODEL_API_KEY": "cx1-fake-key-not-a-real-secret"}
OFFICIAL = "https://api.meta.ai/v1"


def write_config(root, total=150.0, hard_stop=0.95):
    ledger = Path(root) / ".budget_ledger.sqlite3"
    cfg = Path(root) / "budget.yaml"
    cfg.write_text(
        f"total_usd: {total}\nwarn_pct: 0.80\nhard_stop_pct: {hard_stop}\nledger: {ledger}\n"
        "prices_usd_per_mtok:\n"
        "  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n"
        "  muse-spark-1.2: {input: 1.25, output: 4.25, cached_input: 0.15}\n"
        "  muse-wonder-1.0: {input: 4.00, output: 20.00, cached_input: 0.20}\n"
        "asr_usd_per_1000min:\n  muse-voice-transcribe-1.0: 3.0\n",
        encoding="utf-8")
    return cfg


def models_cfg(**over):
    cfg = {"base_url": OFFICIAL, "api_key_env": "MODEL_API_KEY", "roles": {
        "interpreter": {"model": "muse-spark-1.3", "endpoint": "/chat/completions", "temperature": 0.1, "max_tokens": 100},
    }}
    cfg.update(over)
    return cfg


class BudgetGuardExtraTests(unittest.TestCase):
    def test_total_over_hard_lifetime_rejected(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-cap-")
        cfg = write_config(root, total=150.01)
        with self.assertRaises(BudgetLedgerError):
            BudgetGuard.initialize_ledger(str(cfg))

    def test_hard_stop_above_max_rejected(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-stop-")
        cfg = write_config(root, total=150.0, hard_stop=0.96)
        with self.assertRaises(BudgetLedgerError):
            BudgetGuard.initialize_ledger(str(cfg))

    def test_nonfinite_total_rejected(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-fin-")
        cfg = write_config(root, total=float("inf"))
        with self.assertRaises(BudgetLedgerError):
            BudgetGuard.initialize_ledger(str(cfg))

    def test_nan_temperature_rejected_before_http(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-nan-")
        cfg = write_config(root, total=1.0)
        guard = BudgetGuard.initialize_ledger(str(cfg))
        calls = []
        def handler(request):
            calls.append(1)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
        bad = models_cfg()
        bad["roles"]["interpreter"]["temperature"] = float("nan")
        adapter = MetaAdapter(bad, guard, transport=httpx.MockTransport(handler), environ=FAKE_ENV)
        with self.assertRaises(ConfigError):
            adapter.complete("interpreter", "sys", "hello")
        self.assertEqual(calls, [])
        self.assertEqual(guard.status()["held_usd"], 0.0)

    def test_non_official_url_rejected_before_http(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-url-")
        cfg = write_config(root, total=1.0)
        guard = BudgetGuard.initialize_ledger(str(cfg))
        calls = []
        def handler(request):
            calls.append(1)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
        bad = models_cfg(base_url="https://example.invalid/v1")
        with self.assertRaises(ConfigError):
            MetaAdapter(bad, guard, transport=httpx.MockTransport(handler), environ=FAKE_ENV)
        self.assertEqual(calls, [])

    def test_near_cap_denial_sends_zero_http(self):
        root = tempfile.mkdtemp(prefix="cx1-budget-nearcap-")
        cfg = write_config(root, total=1.0)
        guard = BudgetGuard.initialize_ledger(str(cfg))
        guard.reserve_chat("muse-wonder-1.0", 200000, 7000)
        self.assertGreater(guard.status()["committed_usd"], 0.93)
        calls = []
        def handler(request):
            calls.append(1)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
        roles = {"base_url": OFFICIAL, "api_key_env": "MODEL_API_KEY", "roles": {
            "interpreter": {"model": "muse-wonder-1.0", "endpoint": "/chat/completions", "temperature": 0.1, "max_tokens": 100},
        }}
        adapter = MetaAdapter(roles, guard, transport=httpx.MockTransport(handler), environ=FAKE_ENV)
        with self.assertRaises(BudgetExceeded):
            adapter.complete("interpreter", "sys", "hello")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
