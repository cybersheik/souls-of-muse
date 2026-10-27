#!/usr/bin/env python3
"""Orchestrator for Souls of Muse Harness probes.
  python3 run_all.py --adapter mock
  python3 run_all.py --adapter meta
  python3 run_all.py --initialize-budget   # explicit first-time ledger setup only
Reports: reports/run_*.md and reports/run_*.json.
"""
import argparse, json, tempfile
from datetime import datetime
from pathlib import Path

import yaml

from harness.budget import BudgetGuard, BudgetExceeded, BudgetLedgerError
from harness.adapters.mock import MockAdapter
from harness.adapters.meta import MetaAdapter, ConfigError
from probes import p1_latency, p2_terminology, p3_asr, p4_sam


def _write_temp_budget_config(root, total_usd=1.0):
    ledger = Path(root) / ".budget_ledger.sqlite3"
    cfg_path = Path(root) / "budget.yaml"
    prices = ("prices_usd_per_mtok:\n"
              "  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n"
              "  muse-spark-1.2: {input: 1.25, output: 4.25, cached_input: 0.15}\n"
              "  muse-wonder-1.0: {input: 4.00, output: 20.00, cached_input: 0.20}\n"
              "asr_usd_per_1000min:\n  muse-voice-transcribe-1.0: 3.0\n")
    cfg_path.write_text(f"total_usd: {total_usd}\nwarn_pct: 0.80\nhard_stop_pct: 0.95\nledger: {ledger}\n" + prices, encoding="utf-8")
    return cfg_path


def budget_selfcheck():
    """Offline hard-stop check using an isolated initialized DB. No cleanup is
    performed automatically; the temp directory is left for inspection."""
    root = tempfile.mkdtemp(prefix="cx1-budget-selfcheck-")
    cfg_path = _write_temp_budget_config(root, total_usd=1.0)
    guard = BudgetGuard.initialize_ledger(str(cfg_path))
    try:
        guard.charge_tokens("muse-wonder-1.0", {"prompt_tokens": 500000, "completion_tokens": 100000})
        return False
    except BudgetExceeded:
        return True


def _format_status(status):
    if isinstance(status, dict):
        return (f"spent ${status['spent_usd']:.4f}, held ${status['held_usd']:.4f}, "
                f"blocked ${status['blocked_usd']:.4f} of ${status['total_usd']:.0f} "
                f"(stop ${status['stop_usd']:.2f}), calls {status['calls']}")
    return str(status)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", choices=["mock", "meta"], default="mock")
    ap.add_argument("--initialize-budget", action="store_true", help="explicitly initialize/validate the configured SQLite budget ledger and exit; never resets it")
    args = ap.parse_args()
    if args.initialize_budget:
        budget = BudgetGuard.initialize_ledger("config/budget.yaml")
        print(json.dumps(budget.status(), ensure_ascii=False, indent=2))
        return 0
    cfg = yaml.safe_load(Path("config/models.yaml").read_text(encoding="utf-8"))
    budget = BudgetGuard("config/budget.yaml")
    mock_mode = args.adapter == "mock"
    adapter = MockAdapter(cfg, budget) if mock_mode else MetaAdapter(cfg, budget)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = [p(adapter, budget, mock_mode) for p in (p1_latency.run, p2_terminology.run, p3_asr.run, p4_sam.run)]
    selfcheck = budget_selfcheck()
    status = budget.status()
    md = [f"# Souls of Muse - model bench run {ts}", f"Adapter: **{args.adapter}** " + ("(offline mock; no credits)" if mock_mode else "(Meta Model API)"), f"Budget guard: {_format_status(status)}; hard-stop selfcheck: {'OK' if selfcheck else 'FAIL'}", ""]
    md.append("| Probe | Status | Detail |")
    md.append("|---|---|---|")
    for r in results:
        md.append(f"| {r['probe']} | {r['status']} | {r['detail']} |")
    md.append("")
    md.append(f"Mode: {results[0]['mode_note']}.")
    Path(f"reports/run_{ts}.md").write_text("\n".join(md), encoding="utf-8")
    Path(f"reports/run_{ts}.json").write_text(json.dumps({"ts": ts, "adapter": args.adapter, "budget": status, "budget_selfcheck": selfcheck, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(md))
    return 0 if all(r["status"] in ("ok",) for r in results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConfigError as e:
        raise SystemExit(f"CONFIG: {e}")
    except (BudgetExceeded, BudgetLedgerError) as e:
        raise SystemExit(f"BUDGET: {e}")
