"""Structured decoding is explicit and remains inside the pre-HTTP budget bound."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import httpx
from harness.adapters.meta import MetaAdapter, ConfigError
from harness.budget import BudgetGuard

FORMAT = {"type": "json_schema", "json_schema": {"name": "example", "strict": True,
    "schema": {"type": "object", "properties": {"value": {"type": "string"}},
               "required": ["value"], "additionalProperties": False}}}

class StructuredPayload(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="cx1-structured-test-")
        self.addCleanup(self.directory.cleanup)
        cfg = Path(self.directory.name) / "budget.yaml"
        ledger = Path(self.directory.name) / "budget.sqlite3"
        cfg.write_text(f"total_usd: 0.05\nwarn_pct: 0.8\nhard_stop_pct: 0.95\nledger: {ledger}\n")
        self.guard = BudgetGuard.initialize_ledger(str(cfg), str(ledger))
        self.models = {"roles": {"interpreter": {"model": "muse-spark-1.3", "endpoint": "/chat/completions", "max_tokens": 100, "response_format": copy.deepcopy(FORMAT)}}}
        self.requests = []
    def adapter(self):
        def handler(request):
            self.requests.append(request)
            self.assertEqual(self.guard.status()["holds"], 1)
            return httpx.Response(200, json={"choices": [{"message": {"content": '{"value":"ok"}'}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 10}})
        adapter = MetaAdapter(self.models, self.guard, transport=httpx.MockTransport(handler), environ={"MODEL_API_KEY": "offline-fixture"})
        self.addCleanup(adapter.http.close)
        return adapter
    def test_schema_is_on_the_paid_request_not_only_in_a_prompt(self):
        self.adapter().complete("interpreter", "system", "user")
        payload = json.loads(self.requests[0].content)
        self.assertEqual(payload["response_format"], FORMAT)
        self.assertEqual(self.guard.status()["calls"], 1)
    def test_documented_minimal_reasoning_preserves_the_same_budget_bound(self):
        self.models["roles"]["interpreter"]["reasoning_effort"] = "minimal"
        self.adapter().complete("interpreter", "system", "user")
        self.assertEqual(json.loads(self.requests[0].content)["reasoning_effort"], "minimal")
        self.assertEqual(self.guard.status()["holds"], 0)
        self.assertEqual(self.guard.status()["calls"], 1)

    def test_unsupported_or_invalid_schema_is_rejected_before_hold_and_http(self):
        for value in [{"type": "json_object"}, {"type": "json_schema", "json_schema": {"name": "x", "strict": False, "schema": {}}},
                      {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": {"type": "imaginary"}}},
                      {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": {"$ref": "https://invalid.example/schema"}}}]:
            with self.subTest(value=value):
                self.models["roles"]["interpreter"]["response_format"] = value
                with self.assertRaises(ConfigError):
                    self.adapter().complete("interpreter", "system", "user")
                self.assertEqual(self.guard.status()["calls"], 0)
                self.assertEqual(self.requests, [])
    def test_schema_size_is_included_in_request_limit_before_budget_reservation(self):
        self.models["roles"]["interpreter"]["response_format"]["json_schema"]["schema"]["description"] = "x" * 40000
        with self.assertRaises(ConfigError):
            self.adapter().complete("interpreter", "system", "user")
        self.assertEqual(self.guard.status()["calls"], 0)
        self.assertEqual(self.requests, [])
