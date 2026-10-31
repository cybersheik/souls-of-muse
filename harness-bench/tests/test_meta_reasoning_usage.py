"""Offline MetaAdapter/BudgetGuard tests for documented completion_tokens_details.

Documented Chat Completions usage (dev.meta.ai chat-completions schemas and
token-counting): prompt/completion/total plus prompt_tokens_details.cached_tokens
and completion_tokens_details.reasoning_tokens. Reasoning tokens are a subset
of completion_tokens, not an added charge. No real HTTP or API key is used.
"""
import tempfile
import unittest
from pathlib import Path

import httpx

from harness.budget import BudgetGuard, UsageValidationError
from harness.adapters.meta import MetaAdapter, MetaResponseError, ConfigError

FAKE_ENV = {"MODEL_API_KEY": "cx1-fake-key-not-a-real-secret"}
OFFICIAL = "https://api.meta.ai/v1"
# muse-spark-1.3: 100*1.25 + 50*4.25 = 337.5 micro-USD -> ceil 338.
EXPECTED_COST_USD = 338 / 1e6


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


def models_cfg():
    return {"base_url": OFFICIAL, "api_key_env": "MODEL_API_KEY", "roles": {
        "interpreter": {"model": "muse-spark-1.3", "endpoint": "/chat/completions",
                        "temperature": 0.1, "max_tokens": 100}}}


def documented_usage(**over):
    usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
             "prompt_tokens_details": {"cached_tokens": 20},
             "completion_tokens_details": {"reasoning_tokens": 10}}
    usage.update(over)
    return usage


def make_guard():
    root = tempfile.mkdtemp(prefix="cx1-reasoning-test-")
    cfg = write_config(root)
    return BudgetGuard.initialize_ledger(str(cfg)), cfg


def make_adapter(guard, usage, calls):
    def handler(request):
        calls.append(1)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}}], "usage": usage})
    return MetaAdapter(models_cfg(), guard,
                       transport=httpx.MockTransport(handler), environ=FAKE_ENV)


class ReasoningGuardTests(unittest.TestCase):
    def test_documented_usage_cost_no_double_counting(self):
        plain = BudgetGuard.actual_chat_cost_micro(
            "muse-spark-1.3", {"prompt_tokens": 100, "completion_tokens": 50,
                               "total_tokens": 150})
        documented = BudgetGuard.actual_chat_cost_micro(
            "muse-spark-1.3", documented_usage())
        self.assertEqual(documented, 338)
        self.assertEqual(documented, plain)

    def test_reasoning_boundaries_valid(self):
        for reasoning in (0, 50):
            with self.subTest(reasoning=reasoning):
                cost = BudgetGuard.actual_chat_cost_micro(
                    "muse-spark-1.3",
                    documented_usage(completion_tokens_details={"reasoning_tokens": reasoning}))
                self.assertEqual(cost, 338)
        # Empty details mapping carries no unknown keys.
        self.assertEqual(BudgetGuard.actual_chat_cost_micro(
            "muse-spark-1.3", documented_usage(completion_tokens_details={})), 338)

    def test_malformed_reasoning_rejected(self):
        bad_usages = [
            documented_usage(completion_tokens_details={"reasoning_tokens": 51}),
            documented_usage(completion_tokens_details={"reasoning_tokens": -1}),
            documented_usage(completion_tokens_details={"reasoning_tokens": True}),
            documented_usage(completion_tokens_details={"reasoning_tokens": 10.0}),
            documented_usage(completion_tokens_details={"reasoning_tokens": "10"}),
            documented_usage(completion_tokens_details={"reasoning_tokens": None}),
            documented_usage(completion_tokens_details=10),
            documented_usage(completion_tokens_details="reasoning"),
            documented_usage(completion_tokens_details=["reasoning_tokens"]),
            documented_usage(completion_tokens_details={"reasoning_tokens": 10, "extra": 1}),
            documented_usage(completion_tokens_details={"unknown_tokens": 10}),
            documented_usage(unknown_billing_field=1),
        ]
        for usage in bad_usages:
            with self.subTest(usage=usage):
                with self.assertRaises(UsageValidationError):
                    BudgetGuard.actual_chat_cost_micro("muse-spark-1.3", usage)


class ReasoningMetaAdapterTests(unittest.TestCase):
    def test_documented_response_settles_correct_cost_once(self):
        guard, _ = make_guard()
        calls = []
        adapter = make_adapter(guard, documented_usage(), calls)
        result = adapter.complete("interpreter", "sys", "hello")
        self.assertEqual(result["text"], "ok")
        self.assertEqual(result["usage"], documented_usage())
        self.assertEqual(result["cost_usd"], EXPECTED_COST_USD)
        self.assertEqual(len(calls), 1)  # no retry / no repeat HTTP
        status = guard.status()
        self.assertEqual(status["spent_usd"], EXPECTED_COST_USD)
        self.assertEqual(status["held_usd"], 0.0)
        self.assertEqual(status["calls"], 1)
        # Idempotent settle: same reservation returns same cost, no double charge.
        again = guard.settle(result["reservation_id"], "muse-spark-1.3",
                             {"prompt_tokens": 999, "completion_tokens": 999})
        self.assertEqual(again, EXPECTED_COST_USD)
        self.assertEqual(guard.status()["spent_usd"], EXPECTED_COST_USD)
        self.assertEqual(guard.status()["calls"], 1)
        self.assertEqual(len(calls), 1)

    def test_negative_responses_retain_hold_no_retry(self):
        bad_usages = [
            documented_usage(completion_tokens_details={"reasoning_tokens": 51}),
            documented_usage(completion_tokens_details={"reasoning_tokens": -1}),
            documented_usage(completion_tokens_details={"reasoning_tokens": True}),
            documented_usage(completion_tokens_details={"reasoning_tokens": 10.0}),
            documented_usage(completion_tokens_details={"reasoning_tokens": "10"}),
            documented_usage(completion_tokens_details=10),
            documented_usage(completion_tokens_details={"reasoning_tokens": 10, "extra": 1}),
            documented_usage(completion_tokens_details={"unknown_tokens": 10}),
            documented_usage(unknown_billing_field=1),
        ]
        for usage in bad_usages:
            with self.subTest(usage=usage):
                guard, _ = make_guard()
                calls = []
                adapter = make_adapter(guard, usage, calls)
                with self.assertRaises(MetaResponseError):
                    adapter.complete("interpreter", "sys", "hello")
                self.assertEqual(len(calls), 1)
                status = guard.status()
                self.assertEqual(status["spent_usd"], 0.0)
                self.assertGreater(status["held_usd"], 0.0)
                self.assertEqual(status["calls"], 0)


OBSERVED_USAGE = {"prompt_tokens": 112, "completion_tokens": 300, "total_tokens": 412,
                  "completion_tokens_details": {"reasoning_tokens": 298}}
OBSERVED_COST_USD = 1415 / 1e6  # 112*1.25 + 300*4.25 micro-USD


def make_adapter_full(guard, handler, role_cfg=None):
    cfg = models_cfg()
    if role_cfg is not None:
        cfg["roles"]["interpreter"] = role_cfg
    return MetaAdapter(cfg, guard, transport=httpx.MockTransport(handler), environ=FAKE_ENV)


class TruncationAndReasoningEffortTests(unittest.TestCase):
    def test_observed_truncated_none_content_rejected_usage_settled(self):
        guard, _ = make_guard(); calls = []
        def handler(request):
            calls.append(1)
            return httpx.Response(200, json={"choices": [{"message": {"content": None}, "finish_reason": "length"}], "usage": OBSERVED_USAGE})
        adapter = make_adapter_full(guard, handler)
        with self.assertRaises(MetaResponseError) as cm:
            adapter.complete("interpreter", "sys", "hello")
        self.assertIn("length", str(cm.exception))
        self.assertEqual(len(calls), 1)
        st = guard.status()
        self.assertEqual(st["spent_usd"], OBSERVED_COST_USD); self.assertEqual(st["held_usd"], 0.0); self.assertEqual(st["calls"], 1)

    def test_truncated_partial_content_rejected_usage_settled(self):
        guard, _ = make_guard(); calls = []
        def handler(request):
            calls.append(1)
            return httpx.Response(200, json={"choices": [{"message": {"content": "partial translation"}, "finish_reason": "length"}], "usage": OBSERVED_USAGE})
        adapter = make_adapter_full(guard, handler)
        with self.assertRaises(MetaResponseError) as cm:
            adapter.complete("interpreter", "sys", "hello")
        self.assertIn("length", str(cm.exception))
        self.assertEqual(len(calls), 1)
        st = guard.status()
        self.assertEqual(st["spent_usd"], OBSERVED_COST_USD); self.assertEqual(st["held_usd"], 0.0)

    def test_low_and_1024_in_outgoing_json_and_reservation_ceiling(self):
        import json as _json, math
        guard, _ = make_guard(); captured = {}
        def handler(request):
            captured["body"] = request.content
            captured["held_usd"] = guard.status()["held_usd"]
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": documented_usage()})
        role = {"model": "muse-spark-1.3", "endpoint": "/chat/completions", "temperature": 0.1, "max_tokens": 1024, "reasoning_effort": "low"}
        adapter = make_adapter_full(guard, handler, role)
        result = adapter.complete("interpreter", "sys", "hello")
        self.assertEqual(result["text"], "ok")
        payload = _json.loads(captured["body"])
        self.assertEqual(payload["reasoning_effort"], "low"); self.assertEqual(payload["max_tokens"], 1024)
        expected_micro = math.ceil((len(captured["body"]) + 2048) * 1.25 + 1024 * 4.25)
        self.assertAlmostEqual(captured["held_usd"], expected_micro / 1e6, places=9)

    def test_unsupported_reasoning_effort_fails_before_http_and_reservation(self):
        for bad in ("none", "NONE", "", "extreme", 0, 1, True, None, ["low"], {"effort": "low"}):
            with self.subTest(bad=bad):
                guard, _ = make_guard(); calls = []
                def handler(request):
                    calls.append(1)
                    return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": documented_usage()})
                role = {"model": "muse-spark-1.3", "endpoint": "/chat/completions", "temperature": 0.1, "max_tokens": 1024, "reasoning_effort": bad}
                adapter = make_adapter_full(guard, handler, role)
                with self.assertRaises(ConfigError):
                    adapter.complete("interpreter", "sys", "hello")
                self.assertEqual(calls, [])
                st = guard.status()
                self.assertEqual(st["held_usd"], 0.0); self.assertEqual(st["spent_usd"], 0.0); self.assertEqual(st["calls"], 0)


if __name__ == "__main__":
    unittest.main()
