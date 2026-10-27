# Budget Safety

## Scope
This bench is not a live service. The budget guard bounds only Meta API calls routed through `harness.adapters.meta.MetaAdapter` and this SQLite ledger on this one VM. It cannot promise an account-wide $150 cap if other clients, machines, or API keys spend independently.

## Limits
- Absolute lifetime budget in config: $150.00.
- Conservative operational cap: 95% = $142.50.
- Money is stored as integer micro-USD in SQLite. Chat/ASR rates are checked against the verified Standard catalog in code. Contributor models are not enabled.
- Holds and settled charges count together. A reservation is made before any chat HTTP call, using serialized request UTF-8 bytes plus 2048 framing tokens as a deliberately overconservative input-token bound, and the explicit role `max_tokens` as the output bound.

## First-time setup
Normal execution never creates or resets a missing ledger. Initialize explicitly once, after reviewing any legacy `.budget_ledger.json`:

```sh
python3 run_all.py --initialize-budget
# or
python3 -m harness.budget --initialize --config config/budget.yaml
```

If `.budget_ledger.json` exists, execution blocks. Do not delete or reset it blindly; an operator must review and import it deliberately before SQLite initialization.

## Failure behavior
- Unknown/disabled models, unknown prices, invalid endpoint/model/max_tokens/temperature, oversized serialized requests, and `/responses` fail with `ConfigError` or budget errors before HTTP.
- Only `/chat/completions` is supported.
- Network timeout/error, HTTP error, malformed JSON, and missing/invalid usage retain the full HOLD. There is no retry and no TTL release.
- If trusted usage exceeds the reservation, the reservation becomes BLOCKED at the conservative reserved amount and new reservations are disabled.
- Cached prompt tokens are part of prompt tokens and are charged once at the full input rate; they are not added again.
- Corrupt, missing, or schema/total-mismatched ledgers fail closed.

## Operator reconcile
There is no automatic release. For HOLD/BLOCKED rows, an operator must inspect the provider console/billing evidence, decide the real charge, and reconcile the SQLite ledger manually with a reviewed procedure while the bench is stopped. Never edit balances casually and never reset production history to make a run pass.

## ASR / SAM / TTS
WAV files are inspected locally with the standard library (mono 16-bit PCM, 16/24 kHz, at most 60 seconds). The paid ASR route is disabled with `ConfigError` before POST because its usage/billing contract is unverified. SAM and TTS remain unimplemented; no local machine fallback or system TTS is claimed.

## Tests
Tests use `httpx.MockTransport`, a fake environment key, temporary directories created with `tempfile.mkdtemp(prefix='cx1-...')`, and no real API calls. Temporary test directories are intentionally left for inspection rather than automatically deleted.

## Production activation prerequisite

An empty development database is not evidence of zero account spend. Reconcile the provider account's existing usage, pending charges and every API client before initializing any production ledger. The $150 promo is account-wide; this SQLite ledger governs only callers routed through this single durable VM ledger. Other keys, service replicas with separate databases or restores from stale backups can bypass that limit. No provider-enforced no-overage cap has been confirmed. Therefore this candidate is tested offline only and must not be activated for paid production use yet. No development ledger is included in the deliverable.

## Evidence and reporting

19 offline unit tests pass, including a cross-process reservation race, restart holds, duplicate settlement, missing/corrupt ledger rejection, unknown/malformed usage holds, budget rejection with zero HTTP calls, unsafe configuration and NaN rejection. The original missing-ledger regression was observed failing before the repair and passing after it. A fresh ASR report regression was observed failing before its status fix and passing afterward. The mock probe uses simulated latency; P1 now labels measured text API plus estimated ASR/TTS as partial, never a successful live voice E2E. An empty ASR corpus is blocked.
