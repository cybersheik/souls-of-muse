"""Explicit operator provisioning (never run automatically by the app).

Usage:
  python -m service.provision --data-dir /data/som --total-usd 1.0 --confirm
Pilot allocation is enforced: total must be <= $1.00 (operational stop
<= $0.95). Creates the data dir, writes a portable budget config
snapshot (ledger path is the relative name budget_ledger.sqlite3, or an
operator --ledger-path override) and explicitly initializes the SQLite
budget ledger via BudgetGuard. Existing config/ledger are preserved:
repeat provisioning only validates and never resets or increases funds.
Author: Meta Muse Wonder.
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness-bench"))
from harness.budget import BudgetGuard
import yaml

PILOT_MAX_TOTAL_USD = 1.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--total-usd", type=float, default=1.0)
    ap.add_argument("--ledger-path", default=None, help="ledger path written to config (default: relative budget_ledger.sqlite3)")
    ap.add_argument("--confirm", action="store_true", help="required: confirms explicit provisioning")
    a = ap.parse_args()
    if not a.confirm:
        ap.error("--confirm is required; provisioning is explicit, never automatic")
    if not (0 < a.total_usd <= PILOT_MAX_TOTAL_USD):
        ap.error("--total-usd must be in (0, 1.0] for this pilot; operational stop is total*0.95 <= 0.95")
    d = Path(a.data_dir); d.mkdir(parents=True, exist_ok=True)
    cfg = d / "budget.yaml"
    ledger_rel = a.ledger_path or "budget_ledger.sqlite3"
    ledger_file = Path(ledger_rel) if Path(ledger_rel).is_absolute() else (d / ledger_rel)
    if cfg.exists():
        try:
            existing = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
            total = float(existing.get("total_usd", 0))
        except Exception:
            ap.error("existing budget.yaml is invalid; refusing to overwrite it")
        if not (0 < total <= PILOT_MAX_TOTAL_USD):
            ap.error("existing budget.yaml total exceeds the $1 pilot allocation; refusing to change it")
        # Preserve existing ledger reference; resolve it relative to data dir if relative.
        cfg_ledger = existing.get("ledger") or ledger_rel
        ledger_file = Path(cfg_ledger) if Path(str(cfg_ledger)).is_absolute() else (d / str(cfg_ledger))
    else:
        cfg.write_text(
            f"total_usd: {a.total_usd}\nwarn_pct: 0.80\nhard_stop_pct: 0.95\n"
            f"ledger: {ledger_rel}\n"
            "prices_usd_per_mtok:\n"
            "  muse-spark-1.3: {input: 1.25, output: 4.25, cached_input: 0.15}\n", encoding="utf-8")
    guard = BudgetGuard.initialize_ledger(str(cfg), str(ledger_file))
    st = guard.status()
    if guard.total_micro > 1_000_000 or guard.stop_micro > 950_000:
        raise SystemExit("provisioned ledger exceeds pilot allocation; failing closed")
    print({"provisioned": True, "total_usd": st["total_usd"], "stop_usd": st["stop_usd"], "spent_usd": st["spent_usd"], "held_usd": st["held_usd"]})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
