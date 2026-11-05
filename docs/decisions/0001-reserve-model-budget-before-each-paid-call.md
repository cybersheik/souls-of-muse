# 0001. Reserve model budget before each paid call, in SQLite

- **Status:** Accepted
- **Date:** 2026-10-27
- **Workstream:** 02 Engineering on Meta models
- **Decided by:** project owner
- **Prepared with:** implementation and review by Meta models (see `README.md` attribution); integration and tests by the integrator agent

## Context
Every participant receives a fixed, account-wide Meta Model API credit for the event. The initial test bench recorded cost in a JSON file **after** each request. A crash, timeout or parallel run could therefore spend money that was never recorded, and a missing file looked identical to "nothing spent yet".

## Options considered
1. **Keep post-request JSON accounting.** Simple, but unsafe under concurrency, crashes and timeouts.
2. **Rely on the provider's limits.** No provider-enforced no-overage cap could be confirmed for this credit.
3. **Atomic pre-request reservation in SQLite.** Reserve a deliberately pessimistic upper bound before the HTTP call, then settle against reported usage.

## Decision
Option 3. Money is stored as integer micro-USD. The input bound counts every serialized request byte as a token, plus framing. The output bound is the explicit role `max_tokens`. Holds and settled charges count together against a conservative operational cap of 95%.

## Consequences
- Timeouts, HTTP errors, malformed usage and missing usage keep the full hold. There is no retry and no automatic release.
- A missing, corrupt or legacy ledger blocks execution instead of starting from zero.
- The guard bounds only calls routed through this ledger on one machine. It does not cap other keys or clients on the same provider account, and the documentation says so.

## Verification
`harness-bench/tests/test_budget_safety.py` and `test_budget_guard_extra.py` (offline, mocked HTTP) cover:
- a cross-process reservation race;
- restart with open holds and duplicate settlement;
- missing or corrupt ledgers;
- malformed usage;
- rejection with zero HTTP calls.

The missing-ledger regression was observed failing before the repair and passing after it. Details: `harness-bench/docs/BUDGET_SAFETY.md`.
