"""Durable lifetime budget guard for Meta Model API test bench.

Design invariants:
- SQLite is the only ledger; transactions are atomic across processes on one VM.
- Money is stored as integer micro-USD. Rates use Decimal.
- Holds (HOLD/BLOCKED) and settled charges count together against the cap:
  total_usd=150, hard_stop_pct=0.95 => operational cap $142.50.
- A missing ledger is never created silently by normal execution. First use
  requires explicit initialization: BudgetGuard(..., initialize=True),
  BudgetGuard.initialize_ledger(...), `python -m harness.budget --initialize`,
  or `python run_all.py --initialize-budget`.
- A legacy JSON ledger blocks execution until a reviewed import is done by an
  operator. It is never reset or silently converted here.
- No TTL/automatic release exists. Timeout/error/malformed/missing usage keeps
  the full HOLD. Excess/invalid settled charges become BLOCKED and disable new
  reservations until operator review.
- This controls only calls made through this ledger on this machine with this
  key path. It cannot promise an account-wide cap if other clients/keys spend.
"""
import argparse
import json
import math
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml


class BudgetExceeded(RuntimeError):
    pass


class BudgetLedgerError(RuntimeError):
    pass


class LegacyLedgerError(BudgetLedgerError):
    pass


class UnknownModelError(BudgetLedgerError):
    pass


class UsageValidationError(BudgetLedgerError):
    pass


_MICRO = Decimal("1000000")
_SCHEMA_VERSION = "1"

# Verified Standard catalog supplied in config/budget.yaml. Contributor is
# deliberately absent and therefore cannot be enabled by config edits alone.
KNOWN_CHAT_PRICES_USD_PER_MTOK = {
    "muse-spark-1.3": {"input": Decimal("1.25"), "output": Decimal("4.25"), "cached_input": Decimal("0.15")},
    "muse-spark-1.2": {"input": Decimal("1.25"), "output": Decimal("4.25"), "cached_input": Decimal("0.15")},
    "muse-wonder-1.0": {"input": Decimal("4.00"), "output": Decimal("20.00"), "cached_input": Decimal("0.20")},
}
KNOWN_ASR_PRICES_USD_PER_1000MIN = {
    "muse-voice-transcribe-1.0": Decimal("3.0"),
}
_ALLOWED_USAGE_KEYS = {"prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens", "prompt_tokens_details"}


def _dec(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BudgetLedgerError("invalid decimal value in budget config") from exc
    if not result.is_finite():
        raise BudgetLedgerError("invalid decimal value in budget config")
    return result


def _usd_to_micro(value):
    return int((_dec(value) * _MICRO).to_integral_value(rounding="ROUND_FLOOR"))


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


class BudgetGuard:
    def __init__(self, config_path="config/budget.yaml", ledger_path=None, initialize=False):
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise BudgetLedgerError(f"budget config missing: {self.config_path}")
        try:
            cfg = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise BudgetLedgerError("budget config is not readable YAML") from exc
        if not isinstance(cfg, dict):
            raise BudgetLedgerError("budget config must be a mapping")
        self.cfg = cfg
        total_dec = _dec(cfg.get("total_usd", 150.0))
        hard_stop = _dec(cfg.get("hard_stop_pct", 0.95))
        warn_pct = _dec(cfg.get("warn_pct", 0.80))
        if not total_dec.is_finite() or not hard_stop.is_finite() or not warn_pct.is_finite():
            raise BudgetLedgerError("invalid budget totals/percentages in config")
        self.total_micro = _usd_to_micro(cfg.get("total_usd", 150.0))
        self.total = float(total_dec)
        if self.total_micro <= 0 or self.total_micro > 150000000 or hard_stop <= 0 or hard_stop > Decimal("0.95") or warn_pct < 0 or warn_pct > hard_stop:
            raise BudgetLedgerError("invalid budget totals/percentages in config")
        self.stop_micro = int((Decimal(self.total_micro) * hard_stop).to_integral_value(rounding="ROUND_FLOOR"))
        self.warn_micro = int((Decimal(self.total_micro) * warn_pct).to_integral_value(rounding="ROUND_FLOOR"))
        self.warn_at = self.warn_micro / 1e6
        self.stop_at = self.stop_micro / 1e6
        configured_ledger = ledger_path if ledger_path is not None else cfg.get("ledger")
        if not configured_ledger:
            raise BudgetLedgerError("budget ledger path must be explicitly configured")
        self.ledger_path = Path(configured_ledger)
        if self.ledger_path.suffix.lower() == ".json":
            raise LegacyLedgerError("legacy JSON ledger configured; reviewed import required before any spend")
        self._check_legacy_block(cfg)
        self._validate_config_prices(cfg)
        if initialize:
            self.initialize_ledger(self.config_path, self.ledger_path)
        self._ensure_openable()

    # ---------- configuration / catalog ----------
    def _check_legacy_block(self, cfg):
        candidates = []
        legacy = cfg.get("legacy_ledger")
        if legacy:
            candidates.append(Path(str(legacy)))
        sibling = self.ledger_path.parent / ".budget_ledger.json"
        if sibling not in candidates:
            candidates.append(sibling)
        for cand in candidates:
            try:
                if cand.exists() and cand.resolve() != self.ledger_path.resolve():
                    raise LegacyLedgerError(f"legacy JSON ledger present at {cand}; reviewed import required, refusing to spend or reset it")
            except LegacyLedgerError:
                raise
            except Exception:
                if cand.exists():
                    raise LegacyLedgerError("legacy JSON ledger present; reviewed import required")

    def _validate_config_prices(self, cfg):
        prices = cfg.get("prices_usd_per_mtok") or {}
        if prices and not isinstance(prices, dict):
            raise BudgetLedgerError("prices_usd_per_mtok must be a mapping")
        for model, row in prices.items():
            if model in KNOWN_CHAT_PRICES_USD_PER_MTOK:
                if not isinstance(row, dict):
                    raise BudgetLedgerError(f"price row for {model} must be a mapping")
                for field in ("input", "output", "cached_input"):
                    if field not in row or _dec(row[field]) != KNOWN_CHAT_PRICES_USD_PER_MTOK[model][field]:
                        raise BudgetLedgerError(f"configured price for {model}.{field} differs from verified Standard catalog; failing closed")
        asr = cfg.get("asr_usd_per_1000min") or {}
        if asr and not isinstance(asr, dict):
            raise BudgetLedgerError("asr_usd_per_1000min must be a mapping")
        for model, value in asr.items():
            if model in KNOWN_ASR_PRICES_USD_PER_1000MIN and _dec(value) != KNOWN_ASR_PRICES_USD_PER_1000MIN[model]:
                raise BudgetLedgerError(f"configured ASR price for {model} differs from verified catalog; failing closed")

    def chat_price(self, model):
        price = KNOWN_CHAT_PRICES_USD_PER_MTOK.get(model)
        if price is None:
            raise UnknownModelError(f"unknown or disabled chat model: {model!r}; failing closed")
        return price

    # ---------- sqlite plumbing ----------
    @staticmethod
    def initialize_ledger(config_path="config/budget.yaml", ledger_path=None):
        # Build a temporary guard object without opening normal path, then create.
        cfg_path = Path(config_path)
        if not cfg_path.exists():
            raise BudgetLedgerError(f"budget config missing: {cfg_path}")
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        path = Path(ledger_path if ledger_path is not None else cfg.get("ledger", ""))
        if not str(path):
            raise BudgetLedgerError("budget ledger path must be explicitly configured")
        if path.suffix.lower() == ".json":
            raise LegacyLedgerError("legacy JSON ledger cannot be initialized as SQLite")
        # Legacy block also applies to explicit initialization: never overwrite it.
        legacy = cfg.get("legacy_ledger")
        legacy_candidates = [Path(str(legacy))] if legacy else []
        legacy_candidates.append(path.parent / ".budget_ledger.json")
        for cand in legacy_candidates:
            if cand.exists():
                raise LegacyLedgerError(f"legacy JSON ledger present at {cand}; reviewed import required before initialization")
        if path.parent and str(path.parent) not in ("", "."):
            path.parent.mkdir(parents=True, exist_ok=True)
        existed = path.exists() and path.stat().st_size > 0
        conn = sqlite3.connect(str(path), timeout=30.0, isolation_level=None)
        try:
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, model TEXT NOT NULL, kind TEXT NOT NULL, reserved_micro INTEGER NOT NULL CHECK(reserved_micro>=0), settled_micro INTEGER, state TEXT NOT NULL CHECK(state IN ('HOLD','SETTLED','BLOCKED')), created_at TEXT NOT NULL, settled_at TEXT, note TEXT)")
            total_micro = _usd_to_micro(cfg.get("total_usd", 150.0))
            stop_micro = int((Decimal(total_micro) * _dec(cfg.get("hard_stop_pct", 0.95))).to_integral_value(rounding="ROUND_FLOOR"))
            now = datetime.now(timezone.utc).isoformat()
            rows = {"schema_version": _SCHEMA_VERSION, "total_micro": str(total_micro), "stop_micro": str(stop_micro), "created_at": now}
            for key, value in rows.items():
                conn.execute("INSERT OR IGNORE INTO meta(key,value) VALUES(?,?)", (key, value))
            conn.execute("COMMIT")
        except sqlite3.DatabaseError as exc:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise BudgetLedgerError("ledger initialization failed or database is corrupt") from exc
        finally:
            conn.close()
        guard = BudgetGuard(str(cfg_path), ledger_path=str(path), initialize=False)
        if existed:
            # Validate only; existing balances/holds are preserved.
            guard.status()
        return guard

    @classmethod
    def initialize(cls, config_path="config/budget.yaml", ledger_path=None):
        return cls.initialize_ledger(config_path, ledger_path)

    def _connect(self):
        if not self.ledger_path.exists():
            raise BudgetLedgerError(f"budget ledger missing at {self.ledger_path}; run explicit initialization first")
        try:
            with self.ledger_path.open("rb") as fh:
                header = fh.read(16)
        except Exception as exc:
            raise BudgetLedgerError("budget ledger is not readable") from exc
        if len(header) != 16 or header != b"SQLite format 3\x00":
            raise BudgetLedgerError("budget ledger is corrupt or not a SQLite database; failing closed")
        conn = sqlite3.connect(str(self.ledger_path), timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _validate_db(self, conn):
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "meta" not in tables or "reservations" not in tables:
                raise BudgetLedgerError("budget ledger schema missing; failing closed")
            meta = {r[0]: r[1] for r in conn.execute("SELECT key,value FROM meta").fetchall()}
            if meta.get("schema_version") != _SCHEMA_VERSION:
                raise BudgetLedgerError("budget ledger schema version unknown; failing closed")
            if int(meta.get("total_micro", "-1")) != self.total_micro or int(meta.get("stop_micro", "-1")) != self.stop_micro:
                raise BudgetLedgerError("budget ledger totals differ from config; failing closed")
        except BudgetLedgerError:
            raise
        except Exception as exc:
            raise BudgetLedgerError("budget ledger is corrupt; failing closed") from exc

    def _ensure_openable(self):
        conn = self._connect()
        try:
            self._validate_db(conn)
        finally:
            conn.close()

    @staticmethod
    def _committed_micro(conn):
        row = conn.execute("SELECT COALESCE(SUM(CASE WHEN state='SETTLED' THEN settled_micro ELSE reserved_micro END),0) FROM reservations").fetchone()
        return int(row[0])

    @staticmethod
    def _blocked_count(conn):
        return int(conn.execute("SELECT COUNT(*) FROM reservations WHERE state='BLOCKED'").fetchone()[0])

    # ---------- cost math ----------
    @staticmethod
    def chat_cost_micro(model, max_input_tokens, max_output_tokens):
        price = KNOWN_CHAT_PRICES_USD_PER_MTOK.get(model)
        if price is None:
            raise UnknownModelError(f"unknown or disabled chat model: {model!r}; failing closed")
        if not _is_int(max_input_tokens) or not _is_int(max_output_tokens) or max_input_tokens < 0 or max_output_tokens <= 0:
            raise UsageValidationError("token bounds must be integers with output > 0")
        # $/Mtok to micro-USD: tokens * rate (because 1e6 micro / 1e6 tokens cancel).
        exact = Decimal(max_input_tokens) * price["input"] + Decimal(max_output_tokens) * price["output"]
        return int(exact.to_integral_value(rounding="ROUND_CEILING"))

    @staticmethod
    def actual_chat_cost_micro(model, usage):
        price = KNOWN_CHAT_PRICES_USD_PER_MTOK.get(model)
        if price is None:
            raise UnknownModelError(f"unknown or disabled chat model: {model!r}; failing closed")
        prompt, completion = BudgetGuard._validate_usage(usage)
        exact = Decimal(prompt) * price["input"] + Decimal(completion) * price["output"]
        return int(exact.to_integral_value(rounding="ROUND_CEILING"))

    @staticmethod
    def _validate_usage(usage):
        if not isinstance(usage, dict):
            raise UsageValidationError("usage missing or not an object; reservation remains on HOLD")
        unknown = set(usage.keys()) - _ALLOWED_USAGE_KEYS
        if unknown:
            raise UsageValidationError("usage contains unknown fields; reservation remains on HOLD")
        if "prompt_tokens" not in usage or "completion_tokens" not in usage:
            raise UsageValidationError("usage missing prompt/completion tokens; reservation remains on HOLD")
        prompt = usage["prompt_tokens"]
        completion = usage["completion_tokens"]
        if not _is_int(prompt) or not _is_int(completion) or prompt < 0 or completion < 0:
            raise UsageValidationError("usage tokens must be nonnegative integers; reservation remains on HOLD")
        if "total_tokens" in usage:
            total = usage["total_tokens"]
            if not _is_int(total) or total != prompt + completion:
                raise UsageValidationError("usage total_tokens inconsistent; reservation remains on HOLD")
        cached = 0
        if "prompt_cache_hit_tokens" in usage:
            cached = usage["prompt_cache_hit_tokens"]
            if not _is_int(cached) or cached < 0 or cached > prompt:
                raise UsageValidationError("cached token usage invalid; reservation remains on HOLD")
        if "prompt_tokens_details" in usage:
            details = usage["prompt_tokens_details"]
            if not isinstance(details, dict) or set(details.keys()) - {"cached_tokens"}:
                raise UsageValidationError("usage details unknown; reservation remains on HOLD")
            if "cached_tokens" in details:
                dcached = details["cached_tokens"]
                if not _is_int(dcached) or dcached < 0 or dcached > prompt:
                    raise UsageValidationError("cached token details invalid; reservation remains on HOLD")
                cached = max(cached, dcached)
        # Conservative rule: cached tokens are already inside prompt_tokens and
        # are charged at the full input rate. They are never added a second time.
        _ = cached
        return prompt, completion

    @staticmethod
    def asr_cost_micro(model, seconds):
        rate = KNOWN_ASR_PRICES_USD_PER_1000MIN.get(model)
        if rate is None:
            raise UnknownModelError(f"unknown or disabled ASR model: {model!r}; failing closed")
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(float(seconds)) or seconds <= 0:
            raise UsageValidationError("ASR duration must be positive")
        billed_minutes = int(math.ceil(float(seconds) / 60.0))
        if billed_minutes < 1:
            billed_minutes = 1
        # rate $ per 1000 min -> micro per minute = rate * 1000.
        return int((Decimal(billed_minutes) * rate * Decimal("1000")).to_integral_value(rounding="ROUND_CEILING"))

    # ---------- reservations / settlement ----------
    def reserve_chat(self, model, max_input_tokens, max_output_tokens):
        reserved = self.chat_cost_micro(model, max_input_tokens, max_output_tokens)
        return self._reserve(model, "chat", reserved)

    # Generic alias used by tests/callers that prefer reserve().
    def reserve(self, model, max_input_tokens, max_output_tokens):
        return self.reserve_chat(model, max_input_tokens, max_output_tokens)

    def reserve_asr_seconds(self, model, seconds):
        return self._reserve(model, "asr", self.asr_cost_micro(model, seconds))

    def _reserve(self, model, kind, reserved_micro):
        if reserved_micro < 0:
            raise UsageValidationError("reservation must be nonnegative")
        reservation_id = uuid.uuid4().hex
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._validate_db(conn)
            if self._blocked_count(conn) > 0:
                conn.execute("ROLLBACK")
                raise BudgetExceeded("a BLOCKED reservation requires operator review; new calls disabled")
            committed = self._committed_micro(conn)
            if committed + reserved_micro > self.stop_micro:
                conn.execute("ROLLBACK")
                raise BudgetExceeded(f"lifetime budget stop ${self.stop_micro/1e6:.2f} would be exceeded: committed ${committed/1e6:.4f}, reservation ${reserved_micro/1e6:.4f}")
            conn.execute("INSERT INTO reservations(id,model,kind,reserved_micro,settled_micro,state,created_at,settled_at,note) VALUES(?,?,?,?,NULL,'HOLD',?,NULL,'')", (reservation_id, model, kind, int(reserved_micro), datetime.now(timezone.utc).isoformat()))
            conn.execute("COMMIT")
            return reservation_id
        except (BudgetExceeded, BudgetLedgerError):
            raise
        except sqlite3.DatabaseError as exc:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise BudgetLedgerError("budget ledger transaction failed; failing closed") from exc
        finally:
            conn.close()

    def settle(self, reservation_id, model, usage):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._validate_db(conn)
            row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                raise BudgetLedgerError("unknown reservation id; failing closed")
            if row["state"] == "SETTLED":
                settled = int(row["settled_micro"])
                conn.execute("COMMIT")
                return settled / 1e6
            if row["state"] == "BLOCKED":
                conn.execute("ROLLBACK")
                raise BudgetExceeded("reservation is BLOCKED and requires operator review")
            if row["model"] != model:
                conn.execute("ROLLBACK")
                raise UsageValidationError("settlement model does not match reservation; reservation remains on HOLD")
            try:
                actual = self.actual_chat_cost_micro(model, usage)
            except (UsageValidationError, UnknownModelError):
                conn.execute("ROLLBACK")
                raise
            reserved = int(row["reserved_micro"])
            if actual > reserved:
                conn.execute("UPDATE reservations SET state='BLOCKED', note=? WHERE id=?", ("actual usage exceeded conservative reservation", reservation_id))
                conn.execute("COMMIT")
                raise BudgetExceeded("actual usage exceeded reservation; reservation BLOCKED at conservative amount pending operator review")
            conn.execute("UPDATE reservations SET state='SETTLED', settled_micro=?, settled_at=? WHERE id=?", (int(actual), datetime.now(timezone.utc).isoformat(), reservation_id))
            conn.execute("COMMIT")
            return actual / 1e6
        except (BudgetExceeded, BudgetLedgerError):
            raise
        except sqlite3.DatabaseError as exc:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise BudgetLedgerError("budget settlement failed; failing closed") from exc
        finally:
            conn.close()

    def settle_chat(self, reservation_id, model, usage):
        return self.settle(reservation_id, model, usage)

    def mark_blocked(self, reservation_id, reason="operator review required"):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._validate_db(conn)
            row = conn.execute("SELECT state FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                raise BudgetLedgerError("unknown reservation id; failing closed")
            if row[0] == "HOLD":
                conn.execute("UPDATE reservations SET state='BLOCKED', note=? WHERE id=?", (str(reason)[:200], reservation_id))
            conn.execute("COMMIT")
        finally:
            conn.close()

    # ---------- legacy direct-charge compatibility (mock bench) ----------
    def charge_tokens(self, model, usage):
        actual = self.actual_chat_cost_micro(model, usage)
        if actual <= 0:
            return 0.0
        reservation_id = uuid.uuid4().hex
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._validate_db(conn)
            if self._blocked_count(conn) > 0:
                conn.execute("ROLLBACK")
                raise BudgetExceeded("a BLOCKED reservation requires operator review; new calls disabled")
            committed = self._committed_micro(conn)
            if committed + actual > self.stop_micro:
                conn.execute("ROLLBACK")
                raise BudgetExceeded(f"lifetime budget stop ${self.stop_micro/1e6:.2f} would be exceeded")
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT INTO reservations(id,model,kind,reserved_micro,settled_micro,state,created_at,settled_at,note) VALUES(?,?, 'chat', ?, ?, 'SETTLED', ?, ?, 'direct-charge')", (reservation_id, model, int(actual), int(actual), now, now))
            conn.execute("COMMIT")
            return actual / 1e6
        finally:
            conn.close()

    def charge_asr_minutes(self, model, minutes):
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or float(minutes) <= 0:
            return 0.0
        return self.charge_asr_seconds(model, float(minutes) * 60.0)

    def charge_asr_seconds(self, model, seconds):
        actual = self.asr_cost_micro(model, seconds)
        reservation_id = uuid.uuid4().hex
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._validate_db(conn)
            if self._blocked_count(conn) > 0:
                conn.execute("ROLLBACK")
                raise BudgetExceeded("a BLOCKED reservation requires operator review; new calls disabled")
            committed = self._committed_micro(conn)
            if committed + actual > self.stop_micro:
                conn.execute("ROLLBACK")
                raise BudgetExceeded(f"lifetime budget stop ${self.stop_micro/1e6:.2f} would be exceeded")
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT INTO reservations(id,model,kind,reserved_micro,settled_micro,state,created_at,settled_at,note) VALUES(?,?, 'asr', ?, ?, 'SETTLED', ?, ?, 'direct-charge')", (reservation_id, model, int(actual), int(actual), now, now))
            conn.execute("COMMIT")
            return actual / 1e6
        finally:
            conn.close()

    # ---------- status ----------
    @property
    def spent(self):
        return float(self.status()["spent_usd"])

    @property
    def committed_micro(self):
        conn = self._connect()
        try:
            self._validate_db(conn)
            return self._committed_micro(conn)
        finally:
            conn.close()

    def warn(self):
        return self.committed_micro >= self.warn_micro

    def status(self):
        conn = self._connect()
        try:
            self._validate_db(conn)
            settled = int(conn.execute("SELECT COALESCE(SUM(settled_micro),0) FROM reservations WHERE state='SETTLED'").fetchone()[0])
            held = int(conn.execute("SELECT COALESCE(SUM(reserved_micro),0) FROM reservations WHERE state='HOLD'").fetchone()[0])
            blocked = int(conn.execute("SELECT COALESCE(SUM(reserved_micro),0) FROM reservations WHERE state='BLOCKED'").fetchone()[0])
            calls = int(conn.execute("SELECT COUNT(*) FROM reservations WHERE state='SETTLED'").fetchone()[0])
            holds = int(conn.execute("SELECT COUNT(*) FROM reservations WHERE state='HOLD'").fetchone()[0])
            blocked_calls = int(conn.execute("SELECT COUNT(*) FROM reservations WHERE state='BLOCKED'").fetchone()[0])
            by_model = {}
            for model, amount in conn.execute("SELECT model, COALESCE(SUM(settled_micro),0) FROM reservations WHERE state='SETTLED' GROUP BY model").fetchall():
                by_model[str(model)] = int(amount) / 1e6
            committed = settled + held + blocked
            return {"total_usd": self.total_micro / 1e6, "warn_usd": self.warn_micro / 1e6, "stop_usd": self.stop_micro / 1e6, "spent_usd": settled / 1e6, "held_usd": held / 1e6, "blocked_usd": blocked / 1e6, "committed_usd": committed / 1e6, "remaining_to_stop_usd": max(0, self.stop_micro - committed) / 1e6, "calls": calls, "holds": holds, "blocked_calls": blocked_calls, "by_model": by_model, "state": "blocked" if blocked_calls else "ok", "ledger": str(self.ledger_path)}
        finally:
            conn.close()


def _main(argv=None):
    parser = argparse.ArgumentParser(description="Budget ledger utilities")
    parser.add_argument("--config", default="config/budget.yaml")
    parser.add_argument("--ledger", default=None)
    parser.add_argument("--initialize", action="store_true", help="explicitly create/validate the SQLite ledger; never resets an existing ledger")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.initialize:
        guard = BudgetGuard.initialize_ledger(args.config, args.ledger)
        print(json.dumps(guard.status(), ensure_ascii=False, sort_keys=True))
        return 0
    if args.status:
        guard = BudgetGuard(args.config, ledger_path=args.ledger)
        print(json.dumps(guard.status(), ensure_ascii=False, sort_keys=True))
        return 0
    parser.error("one of --initialize or --status is required; normal execution never creates a ledger")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
