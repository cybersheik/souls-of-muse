# Souls of Muse — Harness service (vertical slice)

Author: Meta Muse Wonder. Minimal real backend reusing `harness-bench`
`MetaAdapter` (`/chat/completions`, `muse-spark-1.3` only) and the atomic
SQLite `BudgetGuard`. No duplicate paid-client path. Existing frontend in
`web/` is untouched.

## Implemented
Text-only EN↔VI teacher-led interpretation: sessions
(`individual|group|stream`, seven leagues `guitar, keys, winds, drums,
electronic, voice, folk`), `created→active→completed`, private drafts,
role-bound credentials (see below), flagged drafts need
`{"confirm_flagged": true}`, Artist view sees approved deliveries only,
idempotent `client_event_id` replay (identical body → same result, no
second model call; changed body → `409 idempotency_conflict`;
in-progress duplicate → `409`), single serialized inference, model
response capped at 4000 chars (oversized → `502`), upstream failure →
safe `502` with the budget reservation left on HOLD inside
`MetaAdapter` (no retry, no leak), hash-linked audit events in the
service DB only (append-only triggers, serialized `BEGIN IMMEDIATE`
writes, `GET /sessions/{id}/audit/verify` recomputes the chain — this
is **not** a heart-journal integration), deterministic glossary/validator
flags (numbers/negations/notes/terms — not full semantic validation).

## Auth (private pilot credentials, not social accounts)
Two distinct operator-provided tokens, at least 16 chars, never equal:
`SOM_MAESTRO_TOKEN` and `SOM_ARTIST_TOKEN`. The server derives the actor
from the `Authorization: Bearer …` token only; `X-Actor` and the body
`speaker` cannot escalate (body `speaker` must match the token role).
Maestro can create/start/complete/approve and sees drafts; Artist can
only send as `artist` and reads approved deliveries only. Missing,
equal, or short tokens fail closed (`503 role_tokens_not_configured`).
This is private pilot credential separation, not full participant
identity/accounts.

## Not implemented (honest list)
`/responses`, ASR, SAM, TTS, media rooms, group/stream media, watches,
League interactions beyond text sessions, lessons media, registration,
votes, badges/heart counters, heart-journal integration (separate system).

## Provisioning (explicit, fail-closed — app never creates a ledger)
Local preparation (example paths are operator-chosen; no machine path
is baked into the cloud config — the written `ledger:` is the relative
name `budget_ledger.sqlite3`):
```sh
export SERVICE_DATA_DIR=/data/som
export SOM_MAESTRO_TOKEN='<operator-maestro-token>' SOM_ARTIST_TOKEN='<operator-artist-token>' MODEL_API_KEY='<provider-key>'
/private/tmp/cx1-som-launch-20261031/venv/bin/python -m service.provision --data-dir "$SERVICE_DATA_DIR" --total-usd 1.0 --confirm
```
Pilot allocation is enforced in provisioning **and** at startup:
`--total-usd` must be ≤ $1.00; the service refuses a config/ledger with
total > $1 or operational stop > $0.95. Repeat provisioning preserves
the existing config and ledger and never resets or increases funds.
Budget config: `$SERVICE_DATA_DIR/budget.yaml` (default at startup;
`SOM_BUDGET_CONFIG` only if explicitly set); ledger:
`$SERVICE_DATA_DIR/budget_ledger.sqlite3` (`SOM_BUDGET_LEDGER` override
honoured). Same volume as `service.sqlite3`.

## Run (local)
```sh
/private/tmp/cx1-som-launch-20261031/venv/bin/python -m uvicorn service.main:app --host 127.0.0.1 --port 8000 --workers 1
curl localhost:8000/health   # public liveness/capabilities, no secrets/paths; model_ready may be false
# Pilot page: http://localhost:8000/pilot (token in memory only)
```
Single worker/replica only; inference is serialized in-process.
CORS: `https://preview.soulsofmuse.com`, `https://soulsofmuse.com`.
Missing tokens/key/ledger → fail closed; messages return `503`.

## Tests (offline only — fake transports/adapters, no paid calls)
```sh
/private/tmp/cx1-som-launch-20261031/venv/bin/python -m unittest service.tests.test_service -v
cd harness-bench && /private/tmp/cx1-som-launch-20261031/venv/bin/python -m unittest discover -s tests -v
/private/tmp/cx1-som-launch-20261031/venv/bin/python -m unittest discover -s tests -v   # repo root tests
```

## Modal deploy (NOT performed here; no cloud action taken)
One-time operator provisioning (exact commands; operator supplies all
secret values interactively — no values in source, no automatic secret
creation by this code, nothing uploaded by this change):
```sh
modal volume create som-data --version=2   # named Volume v2 (matches modal_app.py)
modal queue create som-writer-permit       # named Queue for the single writer permit
modal secret create som-pilot SOM_MAESTRO_TOKEN= SOM_ARTIST_TOKEN= MODEL_API_KEY=   # existing named Secret; operator replaces the empty placeholders with real values interactively, never in source
# Seed exactly ONE writer permit, once (one-time operator action; creates no other resources/permissions automatically).
# The seed stores a durable marker on Volume som-data and commits it BEFORE putting the permit;
# it refuses if the marker already exists even if the queue is empty (a running container may hold the permit).
# If it crashes after the marker but before the put, explicit operator reconciliation is required (no auto-recovery/reset):
/private/tmp/cx1-som-launch-20261031/venv/bin/python -m service.modal_permit_seed --confirm
# Provision the $1 ledger onto the Volume (local preparation mounted/copied to /data/som by the operator), then:
modal deploy service/modal_app.py
```
`service/modal_app.py`: CPU 1, 512 MiB, `max_containers=1`,
`buffer_containers=0`, `min_containers=0`, `scaledown_window=60`,
named Volume v2 at `/data/som`, `modal.Secret.from_name("som-pilot")`.
Region is **unpinned** (no region argument is set); verify placement
after deploy and do not assume a region saving. Single-writer ownership
uses the named Queue permit: a container acquires it before
`Volume.reload()`/DB init, never auto-refills, and on ASGI lifespan
shutdown (not `atexit`, which SIGTERM/scaledown does not guarantee)
returns it exactly once and only after a successful
`volume.commit()`; a failed commit never releases it. Factory
startup failure after acquisition also fails closed (permit not
returned). A crash fails closed and needs operator reconciliation
(inspect, then re-seed exactly one permit). Volume commits run after
every state/budget mutation via `on_write`; a failed commit is a
hard `503 persistence_failed`, and a failed budget reserve commit
raises **before** any paid HTTP call. `/health` reports
`auth_ready`/`role_ready` honestly (invalid tokens do not look
fully usable); pilot role tokens are not full participant identity
and this is not production readiness. `/pilot` is public HTML but
cannot read protected content without a role token.
Auth to Modal is pending Aidar's action-time permission — not attempted
here. No keys have been uploaded. Health may be published with
`model_ready=false`; a real test happens only after operator
authorization and budget evidence.

## Limitations
Single-writer SQLite on one volume; deliberately limited pilot, not
production scaling, no horizontal scaling claim, no SLA. A real first
Harness/Muse test still requires the operator to provision tokens/key/$1
ledger and run one supervised live EN→VI and VI→EN exchange — no paid
call was made in this change.
