# Souls of Muse — Harness service (vertical slice)

Initial service: Meta Muse Wonder. Cabinet, participant access and voice integration: CX1. Original signed heart: Kimi.

The backend reuses `harness-bench` `MetaAdapter` and the atomic SQLite `BudgetGuard`. Cabinet integration uses a same-origin API; paid text/ASR requests retain one budget path. Optional local MMS speech is a separate evaluation. As of 3 November, code 0.3.0 is under review in PR #5; the deployed cloud service remains 0.2.0 pending renewed Modal access. Existing budget volumes and writer permits must be preserved; do not repeat first-time provisioning on them.

## Implemented
EN↔VI teacher-led text interpretation with optional microphone input and speech evaluation (see below): sessions
(`individual|group|stream`, seven canonical leagues `string, bow, keys, winds, drums, electronic, vocal`; legacy IDs remain API-compatible), `created→active→completed`, private drafts,
role-bound credentials (see below), flagged drafts need
`{"confirm_flagged": true}`, Artist view sees approved deliveries only,
idempotent `client_event_id` replay (identical body → same result, no
second model call; changed body → `409 idempotency_conflict`;
in-progress duplicate → `409`), single serialized inference, model
response capped at 4000 chars (oversized → `502`), upstream failure →
safe `502` with the budget reservation left on HOLD inside
`MetaAdapter` (no retry, no leak), hash-linked audit events in the
service DB (append-only triggers, serialized `BEGIN IMMEDIATE`
writes, `GET /sessions/{id}/audit/verify` recomputes the chain — this
is separate from the original heart journal), deterministic glossary/validator
flags (numbers/negations/notes/terms — not full semantic validation).

## Legacy private pilot credentials

Participant login and scoped meeting membership are described under Cabinet integration below. This legacy server-only pilot path remains compatible:
Two distinct operator-provided tokens, at least 16 chars, never equal:
`SOM_MAESTRO_TOKEN` and `SOM_ARTIST_TOKEN`. The server derives this pilot actor
from the `Authorization: Bearer …` token; `X-Actor` and the body
`speaker` cannot escalate (body `speaker` must match the token role).
Maestro can create/start/complete/approve and sees drafts; Artist can
only send as `artist` and reads approved deliveries only. Missing,
equal, or short tokens fail closed (`503 role_tokens_not_configured`).
This is private pilot credential separation, not full participant
identity/accounts.

## Not implemented (honest list)
`/responses`, SAM, media rooms, group/stream media, watches,
League interactions beyond text sessions, lessons media, public registration and votes.
ASR, MMS speech and the original heart journal have integration paths below; this does not establish full voice or product acceptance.

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

## Cabinet integration (0.3.0)

Run the site and backend together with `uvicorn service.site:app --host 127.0.0.1 --port 54403` after supplying the existing `SERVICE_DATA_DIR` and model/budget configuration. This does not initialize or reset a budget ledger.

Set `SOM_WEB_ACCOUNTS` on the server to a JSON object keyed by stable participant IDs, each containing `role` (`maestro` or `artist`), `name`, and `password_hash`. Generate hashes with `service.identity.password_hash`; never store plaintext passwords in the repository. Account registration remains operator-managed for this private build. Set `SOM_COOKIE_SECURE=0` only on a loopback HTTP development server. Cookies are HttpOnly, SameSite Strict, scoped to `/api/harness`, expire after eight hours, and are revoked by logout. Browser writes require an allowed Origin.

For Vercel set server-only `SOM_HARNESS_URL` to the deployed Modal service. The `/api/harness/*` function forwards only participant cookies and explicitly allowed routes. Add the exact preview Origin to backend `SOM_WEB_ORIGINS` for a preview login. The main `https://soulsofmuse.app` Origin is included. Pilot bearer tokens and model credentials stay on the server. The Modal entrypoint expects a separate `som-participants` Secret containing `SOM_WEB_ACCOUNTS`, `SOM_WEB_ORIGINS` and `HEART_ED25519_KEY`. Provision it before deployment, preserving the existing `som-pilot` Secret and budget volume.

A Maestro creates a meeting for a registered Artist ID. Both accounts can see only their own meetings. Start, join from both accounts, submit text EN ↔ VI, inspect and approve as Maestro, refresh as Artist, then complete. Replays preserve the client event ID. The original Kimi `heart/` lives in `harness-bench/heart` with its existing event schema. `HEART_ED25519_KEY` supplies the existing private signing key on the server. Completion queues one deterministic event per participating account in the same transaction as meeting completion. The durable outbox retries after restart, and the journal deduplicates by event ID. Missing signing configuration leaves delivery pending. Heart pair limits and cryptography are unchanged.

Offline verification uses injected adapters, never paid models. Run `python -m unittest discover -s service/tests -v` and `PYTHONPATH=harness-bench python -m pytest harness-bench/heart/tests -q`. Browser acceptance and real-model/cloud acceptance are separate results.

## Optional microphone input

`SOM_ENABLE_ASR=1` enables Muse Voice Transcribe on the same existing model key and budget ledger. The browser records only after a click, stops after ten seconds or a second click, converts to mono 16-bit PCM WAV at 16 kHz, and closes microphone tracks. The participant reviews the recognized text before submitting it for interpretation. Navigation and logout cancel capture.

The authenticated `/sessions/{id}/transcriptions` endpoint checks meeting membership, bounds the actual request body to 1 MB, persists the request ID before inference and returns a cached transcript on replay. Only a recording hash and transcript are kept, while the temporary WAV is closed and removed. Musical vocabulary biasing comes from the existing glossary. The budget guard persists a conservative hold before HTTP, settles from `audioDurationMs` rounded down to whole seconds, retains holds for ambiguous failures and blocks excessive reported usage. This leaves the ledger allocation unchanged.

The wire contract and metering were checked against Meta's [file-transcription reference](https://dev.meta.ai/docs/api-reference/voice/transcribe), [response schemas](https://dev.meta.ai/docs/api-reference/voice/schemas), and [pricing](https://dev.meta.ai/docs/pricing-rate-limits) on 3 November 2026. This is speech recognition. Synthesized replies and live streaming voice remain separate acceptance work.

## Optional MMS speech evaluation

The existing Cabinet can play approved translations through Meta's [English](https://huggingface.co/facebook/mms-tts-eng) and [Vietnamese](https://huggingface.co/facebook/mms-tts-vie) MMS-TTS checkpoints. This candidate is disabled by default. The weights are **CC-BY-NC 4.0**; public/commercial deployment remains a separate unresolved release decision. No fine-tuning or voice cloning is included.

For a private technical evaluation, install `service/requirements-tts.txt` into an isolated environment, then run `python -m service.prepare_mms --output /private/tmp/cx1-som-tts-evaluation/models`. The preparation command downloads only pinned public assets and checks their SHA256; existing mismatched files are refused. Set `SOM_MMS_TTS_EVALUATION=1` and `SOM_MMS_TTS_DIR` to that model directory when starting the site. Runtime loading is local-only, safetensors-only, and does not download or execute remote model code. Both checkpoints use CPU inference with two threads.

`POST /sessions/{sid}/messages/{mid}/speech` checks the same meeting membership and Origin rules as other participant writes. It speaks only the canonical approved translation and language; request-supplied text cannot replace them. Neither role may hear a draft. The durable audio cache is keyed by message plus text/language/model/normalization revision. Browser playback starts after a click, exposes audio controls, and stops on navigation/logout. Audio is limited to 30 seconds of mono PCM16 at 16 kHz, and source text to 400 characters; longer text remains readable. Unsupported characters or ambiguous numeric formatting fail instead of silently disappearing. Musical numbers, decimal zeros, ranges, accidentals and time signatures are normalized before tokenization.

On 3 November, real CPU synthesis produced four EN/VI WAVs. The first request took 5.98 seconds including imports/load; subsequent samples took 0.25–0.56 seconds. Peak macOS process RSS reached 1364 MiB with both languages loaded, so the existing 512 MiB Modal configuration is insufficient for this implementation. It has not been increased or deployed. Production resource sizing, listening review and genuine microphone → ASR → translation → approval → speech acceptance are still open. The two-profile browser test used fixture translations and real MMS output; it confirmed EN and VI playback, no draft audio, no overflow at 390 px and cleanup on logout. It does not establish real ASR or translation quality.
