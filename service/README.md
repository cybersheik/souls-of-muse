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
CORS: `https://soulsofmuse.app`, `https://preview.soulsofmuse.com`, `https://soulsofmuse.com`.
Missing tokens/key/ledger → fail closed; messages return `503`.

## Tests (offline only — fake transports/adapters, no paid calls)
```sh
/private/tmp/cx1-som-launch-20261031/venv/bin/python -m unittest service.tests.test_service -v
cd harness-bench && /private/tmp/cx1-som-launch-20261031/venv/bin/python -m unittest discover -s tests -v
/private/tmp/cx1-som-launch-20261031/venv/bin/python -m unittest discover -s tests -v   # repo root tests
```

## Modal deploy (NOT performed here; no cloud action taken)

### Budget history reconciliation before an update

Do not upload the local ledger over the deployed ledger. The observed local
and cloud histories have common reservation IDs plus distinct actual charges.
`service.reconcile_budget` compares **provided snapshots**, using OS read-only
descriptors and SQLite only in memory, and can prepare a separate offline ledger:

```sh
python -m service.reconcile_budget --local /private/operator/local.sqlite3 --cloud /private/operator/cloud-snapshot.sqlite3
python -m service.reconcile_budget --local /private/operator/local.sqlite3 --cloud /private/operator/cloud-snapshot.sqlite3 --stage /private/operator/NEW-unapproved-stage.sqlite3
```

The output path must not exist. No source ledger, cap, token, cloud resource or
model is changed. Shared IDs are deduplicated only when **every stored field
matches**. Different lineage/metadata/caps or conflicting shared reservations
fail closed; the tool never chooses a winner or raises the allowance. Distinct
HOLD/BLOCKED entries stay intact. A union above the stop still preserves the
original stop and reports the budget blocked. Unknown/corrupt schema or row
accounting is rejected, rather than omitted.

Only quiescent rollback-mode snapshots are supported. WAL-mode headers and any
`-wal`, `-shm` or `-journal` sidecar cause rejection: ignoring WAL can lose real
charges, while even SQLite `mode=ro` can create an absent `-shm` file. The helper
never SQLite-opens the source pathname. It checks the descriptor, inode, size
and nanosecond modification/change times before and after reading bytes, then
validates a deserialized in-memory image. A changing input is rejected. Obtain
a proper checkpointed snapshot through a separately controlled writer handoff;
this helper never checkpoints or modifies an active database for you.

The staging database is built in memory and written through an exclusive new
0600 file descriptor. Existing paths/symlinks cannot be overwritten; a swapped
path cannot redirect SQLite writes into a source. The resulting snapshot and
source snapshots are checked again. Descriptor-bound verification and a final
file-version/path check reject late swaps and in-place changes. A source change or failed check produces
no success receipt; any incomplete or unapproved output requires inspection,
never automatic retry/overwrite/upload. Reports contain counts, integer
micro-USD and snapshot hashes, not raw reservation IDs or note content.

**A stage is not deployment approval or proof of fresh cloud history.** Every
report keeps `cloud_freshness_verified=false` and `deployment_approved=false`.
An operator must first obtain a fresh snapshot from the correct account and
verify the single-writer handoff/quiescence. Compare again before any separately
reviewed replacement. Do not re-seed permits, reset history or assume that an
old downloaded cloud snapshot is current. The helper contains no upload,
resource-management, cap-increase or token-creation command.

The 3 November read-only comparison independently verified the available
snapshots: local24 settled/$0.036050, cloud snapshot6/$0.010601, four identical
shared rows, and two cloud-only rows/$0.003911. Their union is26 settled/$0.039961
under the unchanged $0.05 allocation/$0.0475 stop, remaining$0.007539.
This is snapshot evidence, not a refreshed cloud balance or a working-ledger
replacement. The existing Modal profile was checked with one read-only
`modal app list`; the provider reported that its token had expired. No new
token/login flow was started. The Modal login-readiness question remains open.
The owner subsequently approved $0.25 total / $0.2375 stop, preserving all
history. Until live cloud history is available, the existing local ledger has
a conservative $0.20 allocation/$0.19 stop; $0.05/$0.0475 is reserved for the
unchanged old cloud pilot. These stops sum to the approved $0.2375, even when
shared historic records count twice in the bound. All original24 local rows
were preserved exactly; only local cap metadata and its matching config changed.
The old staged union is historical and was not installed or uploaded. Fresh
cloud reconciliation and reviewed cap migration are still required before a
single consolidated cloud ledger replaces the two shares.

Four real Meta calls then settled $0.038352: two Wonder planning attempts and
one Spark step translation plus its mandatory reviewer. Local history is now
28 settled/$0.074402, HOLD0, under the $0.19 local stop. Including the two known
cloud-only records gives a last-known union of $0.078313, not a refreshed cloud
balance. Provider catalog and Standard pricing were checked on3November.

The first shape-valid Wonder plan incorrectly used `title` for all three
durations; it was not adopted. Planning now describes timing values explicitly
and rejects schema-token placeholders, including quoted/nested wrappers, before
exposing or adopting a draft. Maestro-authored timing remains free text. One
explicit retry of the same brief preserved4/8/8minutes, Am/C,60BPM and the
requested downstrokes. Test Maestro reviewed and adopted it. Its first step
translated faithfully EN→VI, while two deterministic glossary flags remained
for `tay gảy`/`dây`; explicit bilingual review preceded approval. Artist saw no
target before approval and the exact canonical target after it. Replay made
no additional call. The original Kimi heart verified both signed completion
events in subsequent fresh processes. This is a bounded local real-provider
case, not general model-quality, human-voice or Modal acceptance.
See `docs/qa-live-planning-20261103.json` for the complete sanitized evidence.

### Existing cloud resources

The candidate Modal image now installs directly from `service/requirements.txt`,
the same pinned manifest used by the isolated `cloud-runtime` Linux/Python 3.12
CI job. This includes both `livekit-api` (room control) and `livekit` (native RTC
audio); the former alone cannot run `service.media_transport`.
`requirements-media.txt` remains a compatibility entry point to that manifest.
Installing the SDK does not enable media, provision an SFU or change capacity.
MMS/Torch/model assets remain excluded from the cloud image and TTS remains off.

Run `python scripts/verify_cloud_runtime.py` in a fresh environment containing
only these requirements. The check uses a new isolated fixture directory,
synthetic accounts/key, a zero-spend $0.05 ledger and outbound-HTTP rejection.
It checks primary-Origin CORS, role-bound login, shared worksheet, private notes,
signed original heart journal and preserved cookies/data in a second Python
process. It also sends a silent PCM frame through the actual native RTC FFI
without connecting to any room or microphone. This is not a Modal image build,
Modal cold-start test, hosted SFU test or provider-quality acceptance. Fixture
directories are retained for inspection; operator ledgers/configs are not read.

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
raises **before** any paid HTTP call. Participant responses wait for
pending durable commits; a failed commit latches the process closed,
including reads and replays, until a fresh successful startup. `/health`
remains readable and reports `degraded`/`durability_ready=false`.
This prevents a concurrent reader from observing a local SQLite approval
whose Volume commit later fails. It does not establish distributed
transaction guarantees. `/health` reports
`auth_ready`/`role_ready` honestly (invalid tokens do not look
fully usable); pilot role tokens are not full participant identity
and this is not production readiness. `/pilot` is public HTML but
cannot read protected content without a role token.
The original 0.2.0 pilot is already deployed in the authorized Modal
account. Its expired CLI login must be renewed before deploying this
0.3.0 integration; do not replace the existing model secret or reset
the budget ledger. Health may be published with `model_ready=false`;
live model tests require the existing authorization and budget evidence.

## Limitations
Single-writer SQLite on one volume; deliberately limited pilot, not
production scaling, no horizontal scaling claim, no SLA. A real first
Harness/Muse acceptance requires a supervised live EN→VI and VI→EN
exchange and a cold restart against the existing ledger. Earlier 0.2.0
text calls do not establish acceptance of this integration. Offline
tests in this change make no paid model calls.

## Cabinet integration (0.3.0)

Run the site and backend together with `uvicorn service.site:app --host 127.0.0.1 --port 54403` after supplying the existing `SERVICE_DATA_DIR` and model/budget configuration. This does not initialize or reset a budget ledger.

Set `SOM_WEB_ACCOUNTS` on the server to a JSON object keyed by stable participant IDs, each containing `role` (`maestro` or `artist`), `name`, and `password_hash`. Generate hashes with `service.identity.password_hash`; never store plaintext passwords in the repository. Account registration remains operator-managed for this private build. Set `SOM_COOKIE_SECURE=0` only on a loopback HTTP development server. Cookies are HttpOnly, SameSite Strict, scoped to `/api/harness`, expire after eight hours, and are revoked by logout. Browser writes require an allowed Origin.

For Vercel set server-only `SOM_HARNESS_URL` to the deployed Modal service. The `/api/harness/*` function forwards only participant cookies and explicitly allowed routes. Add the exact preview Origin to backend `SOM_WEB_ORIGINS` for a preview login. The main `https://soulsofmuse.app` Origin is included. Pilot bearer tokens and model credentials stay on the server. The Modal entrypoint expects a separate `som-participants` Secret containing `SOM_WEB_ACCOUNTS`, `SOM_WEB_ORIGINS` and `HEART_ED25519_KEY`. Provision it before deployment, preserving the existing `som-pilot` Secret and budget volume.

A Maestro creates a meeting for a registered Artist ID. Both accounts can see only their own meetings. Start, join from both accounts, submit text EN ↔ VI, inspect and approve as Maestro, refresh as Artist, then complete. Replays preserve the client event ID. The original Kimi `heart/` lives in `harness-bench/heart` with its existing event schema. `HEART_ED25519_KEY` supplies the existing private signing key on the server. Completion queues one deterministic event per participating account in the same transaction as meeting completion. The durable outbox retries after restart, and the journal deduplicates by event ID. Missing signing configuration leaves delivery pending. Heart pair limits and cryptography are unchanged.

Offline verification uses injected adapters, never paid models. Run `python -m unittest discover -s service/tests -v` and `PYTHONPATH=harness-bench python -m pytest harness-bench/heart/tests -q`. Browser acceptance and real-model/cloud acceptance are separate results.

## Teacher-led plan and Notebook

Authenticated members read `/sessions/{sid}/lesson`; only that meeting's Maestro
may update it with POST while the meeting is created or active. New meetings
start with an empty plan and Notebook. No example people, progress percentages,
chords, notation or teaching advice are substituted into the live workspace.
The approved layout stays intact: plan in the centre, Notebook in the right
drawer. Maestro can author steps (title, duration, goal, tips), select the
current step, and share chord bars, an ABC score and tablature. The existing
local Maestro metronome remains available; watch/tactile synchronization is
still open.

The entire workspace is saved atomically in the existing service SQLite DB
and uses the same durable commit barrier. Updates carry a revision: a different
stale edit gets 409 instead of overwriting newer material. Replaying the same
content adds neither a revision nor an audit event. Completed/closing meetings
are read-only. Persisted content is revalidated; corrupt state is unavailable,
never silently replaced. Payloads are bounded to 28,000 UTF-8 bytes within the
existing HTTP limit; per-field limits apply too.

Artist follows saved changes through the existing five-second visible-page
poll. Each refresh captures user/meeting context and applies one coherent
snapshot; a late old response cannot replace a newly selected meeting or log
out another account. Unsaved forms remain in memory during errors/conflicts.
Only one editor can be open, and its controls are disabled during a save;
changing the step is unavailable while editing. No private document drafts
are put in localStorage. Maestro sees authored plan fields; Artist sees a
labelled original until the matching reviewed translation is approved.
Private account-owned notes are separate from this shared material (see below).
Full group fanout remains unfinished.

## Private participant notes

Each signed-in member has an independent plain-text document per meeting.
`GET/POST /sessions/{sid}/notes` resolves ownership from the HttpOnly participant
cookie and meeting membership; a shared legacy role bearer cannot identify a
person and is rejected. The request cannot specify another owner. The normal
Origin checks and durable commit barrier apply.

Authenticated browser requests carry a percent-encoded `X-SOM-Participant`
account precondition. It never selects the owner: the server compares it with
the actual cookie account before reading or writing. This rejects an old tab
after another tab changes their shared login cookie. Private-note writes
require the precondition; responses carry the actual account marker, forwarded
by the gateway and checked before the client accepts private data. A mismatch
clears the private editor/index and visible page. `auth/me` and logout use the
same check, so a stale tab cannot log out the newly signed-in account. Unicode
account IDs are encoded in headers. An auth preflight alone would not close the
race and is not used as a substitute for this per-request check.

Notes use revision-based compare-and-swap and exact-content replay: a lost save
response does not add a revision, and another tab's different stale text gets
409. The editor retains the unsaved draft on failure/conflict and clears it on
account or meeting change. A late old-account save cannot replace current state;
a delayed poll cannot roll back an acknowledged higher note revision. An unauthorized
response clears private state and redraws the visible page.
No drafts are stored in localStorage. Text is escaped, bounded to 8000 characters
and 24000 UTF-8 bytes, and never silently truncated.

Personal notes remain editable after the meeting, so a participant can write
their own reflection. They do not change the shared plan/Notebook, enter a
shared audit/heart event, or get appended to interpreter/planning prompts.
Saving notes never calls a model. The existing microphone control is explicitly
labelled **Dictate a message** in the Muse chat; it does not dictate into private
notes or send their text for ASR.

The cabinet's **My notes** link opens only the current account's saved note
previews, with cursor pagination through `GET /notes`; **Open meeting** returns
to the full note. The server always filters by account and membership regardless
of cursor contents. Clearing the text removes its preview from the index while
preserving the document revision. Other participants receive neither the text
nor the note's existence through this index or the shared audit. An interrupted
index request cannot reveal a previous account's previews.

Local acceptance uses the actual site, API, SQLite, three isolated Chrome
contexts (two accounts plus a second Maestro tab) and a fresh server process.
Owner isolation, escaped text, stale-tab conflict/draft retention, completed
meeting edits, the personal index and logout were verified; both roles at
1440/390/320 had no overflow. All inference was explicitly forbidden in this
test. See `docs/qa-private-notes-20261103.json`. This verifies local behavior,
not cloud deployment or full product acceptance.

The Notation tab renders actual ABC through vendored **abcjs 6.7.2 / MIT**,
with pinned npm SHA512 and file SHA256 in `web/vendor/abcjs-6.7.2.json`.
See the primary [rendering documentation](https://docs.abcjs.net/visual/render-abc-options.html).
The renderer runs in an opaque sandbox frame with no parent DOM/cookies,
network or audio access; active SVG content and links are removed. Parse
warnings remain visible. Unknown chord names are shown as text rather than
invented guitar fingerings. There are no runtime CDN requests for abcjs.

The local browser check uses real HTTP/storage and two isolated Chrome
profiles, with inference explicitly forbidden. It checks authoring, automatic
Artist progression, all three Notebook tabs, actual score SVG, hostile-title
isolation, stale-edit retention and 1440/390/320 layouts. A separate server
process restart preserved the workspace. This is local worksheet acceptance,
not cloud, real-model translation, group, acoustic-performance or full-service acceptance.

### Reviewed EN↔VI step translation

POST `/sessions/{sid}/lesson/translations` takes the workspace revision, step
index and stable client event ID; the meeting fixes the language pair. Only
its Maestro can request or approve translation. The interpreter returns a
strict object with translated title, duration, goal and ordered tips, retaining
empty fields. Local parsing rejects duplicates, unknown/missing fields,
misaligned tip counts and oversized output. Each field passes the existing
music/number/negation validator. Full-context field alignment always requires
the reviewer and explicit Maestro confirmation. A faithful verdict never
automatically publishes material or clears deterministic flags.
The observed short Vietnamese `nốt` before a recognized named pitch now retains
the NOTE concept; colloquial `nốt` and English article controls do not create it.

Immutable source/language hashes bind each result to its actual content.
Changing a source field invalidates its translated view; changing the selected
step or Notebook preserves a matching approval. Artist receives only approved
target fields, in their original plan positions. Until then it shows a labelled
original. A different workspace revision cannot mix new targets with an old
client snapshot. Maestro alone can inspect unapproved targets and review.
The projection travels with the existing session poll, adding no HTTP poll.

Attempts and request aliases are committed before inference. Identical source
requests share an in-flight/completed attempt; stable replay never repeats it.
After failure, a new event ID alone cannot spend again: `retry:true` is required.
An explicit retry of failed review reuses the canonical translation and reruns
only the reviewer. Explicit regeneration leaves a previous approved target
visible until a new approval. An older pending version cannot supersede a newer
approved one. Restart marks interrupted attempts failed without replay; all
budget holds remain for reconciliation. Source edits/meeting closure during
inference discard the result, including before a second paid stage if detected.

The material roles inherit the current Spark/minimal settings and share the
same MetaAdapter/BudgetGuard, with 8192/2048 output bounds for full step fields.
Conversation bounds remain 1024/512. This changes no allocation or stop limit.
The full serialized schema/payload is bounded and reserved before HTTP; a
failed durable reserve prevents HTTP and retains its hold. Oversized/truncated
outputs or review failures cannot publish partial text. There is no automatic
retry, source summarization, music-notation rewrite or separate budget ledger.

Acceptance is currently **offline model contract only**: real HTTP/storage and
two Chrome profiles with explicit interpreter/reviewer responses verified the
original → private draft → Maestro confirmation → translated Artist fields,
Notebook edit preservation, process restart and source invalidation. Factory
tests use actual budget code with MockTransport in isolated test ledgers.
No provider call, real allocation change, real material translation quality,
cloud acceptance or latency result is claimed. See
`docs/qa-lesson-translation-20261103.json`.

## Flagged translation review

The required reviewer stage runs after a deterministic flag, using `muse-spark-1.3`, minimal reasoning, temperature 0 and a 512-token output bound under the same budget guard. Source transcript, canonical draft, flags and any lesson-note grouping are sent as quoted JSON data. A strict two-field reply (`verdict`, `reason`) is requested with JSON Schema and checked locally; unknown fields, duplicate keys, invalid verdicts or empty/oversized reasons fail closed. This is a second opinion about the supplied transcript, not acoustic recognition or proof that a performance occurred. It never edits the translation, clears a deterministic flag or approves delivery.

Review state is committed before paid inference. A successful verdict remains visible only to Maestro, including on replay; an Artist sees only approved text. Maestro must explicitly confirm a flagged translation even when the reviewer calls it faithful. Unavailable/malformed review blocks approval even with that confirmation. Replays and restarts do not repeat paid work; interrupted messages/reviews become failed, and budget holds remain untouched. Legacy flagged messages without a completed review stay blocked. Approval revalidates earlier drafts with the current validator, makes no paid call and stops if validation is unavailable. A missing glossary also prevents new interpretation calls and makes pilot readiness false.

Maestro can explicitly retry an unavailable check with
`POST /sessions/{sid}/messages/{mid}/review` and a new `client_event_id`.
The check uses the saved canonical source, translation and structured note;
it never retranslates, edits, approves or delivers the message. Current
validation runs before the request is committed. The attempt and processing
state are persisted before entering the same serialized inference gate and
BudgetGuard as the original review. A failed request's unknown-usage HOLD is
never released to fund a retry. Replaying an event ID, reloading or restarting
does not call a model; a completed review is reused even under a new ID.
Only an active meeting's Maestro member may start a retry. Pending review
blocks completion and approval. Startup marks interrupted attempts failed;
another new explicit intent is required. The cabinet preserves an ambiguous
request ID until an acknowledged response or matching terminal server marker,
and offers **Retry translation check** instead of resending the whole message.

Earlier Spark testing on two fixed synthetic text pairs was **partial**: it correctly identified a changed tempo of 60→80, but review of a faithful ordinal phrase failed closed. No retry or automatic delivery occurred; the cause of that second failure was not established. A related false `KEY_MINOR` flag for Vietnamese ordinal `thứ hai` was fixed independently and checked through HTTP without another model call; `La thứ ba lần` still means A minor repeated three times. The two reviewer requests cost $0.004853 in the existing ledger. Their measured HTTP times were 13.424 and 6.213 seconds; these are not full voice latency or a P95 result. See `docs/qa-translation-review-20261103.json`; the newer structured-output experiment below is separate.

## Structured lesson notes

The interpreter now requests a strict JSON Schema response containing the whole
`translation` and `lesson_note`: `heard`, `where.measure`, `where.note`, `change`
and `try`. Every slot is null or a source/translation quote pair. The parser
rejects duplicate or extra fields, truncated/plain-text responses, ungrounded
quotes and oversized content; it never falls back to an unstructured draft.
Source quotes must occur in the source, and target quotes in the canonical
translation, after NFC normalization. Action/observation quotes must preserve
whole sentences or the whole utterance. Raw responses are bounded to 16,000
characters, whole translations to 4,000, source quotes to 400 and target quotes
to 800.

Literal quotation alone does not prove meaning. A prior sentence can govern an
otherwise intact quote (for example, "Do not do the following"). Any non-null
observation/action/repetition slot therefore requires full-context review and
explicit Maestro confirmation. Typed note locations additionally compare every
named pitch in order, with per-pitch octave, accidental and major/minor quality.
Unsupported or ambiguous notation requires review. These checks do not establish
general semantic equivalence, completeness or acoustic truth.

The original evidence is stored atomically with the draft. After approval,
Artist receives only the canonical translation and its target-language quote
card. Source evidence and private review remain Maestro-only, including replay.
The card says whose words it quotes and labels observations as reported speech.
Legacy messages without structured evidence remain text history; no note is
invented for them. This card does not replace the lesson plan or Notebook.

Interpreter/reviewer settings come from `harness-bench/config/models.yaml`.
Both use documented `minimal` reasoning at their existing 1024/512 output caps;
`none` is rejected locally. Schema bytes are validated and included in the
request-size and budget reservation bounds before paid HTTP. See the primary
[structured-output](https://dev.meta.ai/docs/cookbook/structured-output) and
[reasoning](https://dev.meta.ai/docs/reasoning) documentation. Reasoning tokens
consume the output allowance; a strict schema does not guarantee a complete
response at that allowance.

Real acceptance remains **PARTIAL**. Two initial low-reasoning EN/VI text calls
exhausted 1024 tokens, returned incomplete/no content and failed closed without
delivery. A new held-out EN→VI input using minimal reasoning completed both
translation and review in 15.858 seconds. After CX1's explicit controlled-test
Maestro approval, Artist received the canonical text/card; completion awarded
one original-heart increment per participant, and a new-process restart
preserved state, card and verified Ed25519 chain without model calls. However,
`where.note` was null despite an explicitly named E-minor chord. Complete slot
extraction, VI→EN, human voice, cloud restart and the ≤5-second/P95 target are
not accepted. Browser layout/privacy checks used explicit offline model fixtures
at 1440/390/320 px. See `docs/qa-structured-lesson-20261103.json`.

Those four paid requests added $0.016666 to the existing local ledger:
24 SETTLED/$0.036050, no unsettled holds. Allocation $0.05 and stop $0.0475
were unchanged. Adding the previously confirmed cloud-only $0.003911 gives a
last-known aggregate $0.039961; the cloud ledger has not been refreshed. Its
remaining $0.007539 cannot cover the next conservative interpreter reservation
(about $0.01054). Stop further paid tests until explicit allocation approval
and reconciliation of the actual histories; do not replace either ledger.

## Maestro-led planning proposals

The lesson's **Plan with Muse** form sends a Maestro brief and the existing plan
to `muse-wonder-1.0` through stateless `POST /responses`. It stays outside the
ASR/interpretation/delivery path, as required by the Harness v0.1 architecture.
Only the meeting's Maestro can request, inspect or adopt a proposal. The model
receives the source language, meeting kind/League, brief and plan; participant
identifiers, chat, private notes and Notebook content are not sent.

The strict JSON response is validated as 1–32 bounded lesson steps and checked
against the complete workspace size, preserving the current Notebook. The
request includes the remaining plan byte allowance. A malformed, truncated,
refused or oversized reply cannot become an adoptable draft. The default
orchestrator output bound is 4096 tokens, including reasoning. This can truncate
a large proposed plan; it is rejected rather than silently shortened.

The private draft changes the shared plan only after **Use this plan** and an
explicit Maestro confirmation. Adoption compares the original workspace
revision, preserves Notebook content and writes the new plan plus adoption
record atomically. Any intervening workspace edit or meeting closure blocks it.
Replaying an adopted request never increments the revision again. The model
does not execute tools, match participants, close meetings or deliver messages.

`GET/POST /sessions/{id}/lesson/proposals` and
`POST /sessions/{id}/lesson/proposals/{proposal}/apply` use the existing
server-side membership, role and Origin checks. Only Maestro's meeting
projection contains the planner draft. Request IDs and cache aliases are
committed before inference; duplicate requests do not call the model again.
Returning to a cached brief selects that draft. After a failed attempt, a new
request requires explicit retry; the UI offers **Retry this goal**, with no
automatic retry. Interrupted generation becomes failed on startup, preserving
budget holds. Changed snapshots discard pending results.

The [official create reference](https://dev.meta.ai/docs/api-reference/responses/create-response),
[schemas](https://dev.meta.ai/docs/api-reference/responses/schemas),
[structured-output recipe](https://dev.meta.ai/docs/cookbook/structured-output)
and [Wonder example](https://dev.meta.ai/docs/overview) were checked on
3 November 2026. The adapter maps `max_tokens` to `max_output_tokens`, reasoning
to `reasoning.effort`, and strict schema to `text.format`. It sends
`store=false`, `stream=false`, `background=false`, with no tools or history.
Responses accounting is validated and normalized into the same existing
BudgetGuard: reserve/persist before HTTP, settle trusted input/output usage,
count reasoning once within output, retain HOLD for ambiguous failures.

Local acceptance uses a real site, API, SQLite, MetaAdapter and BudgetGuard
with `httpx.MockTransport`, two isolated Chrome contexts and a fresh server
process. It verifies privacy, explicit adoption, Notebook preservation,
idempotent replay, EN/RU labels and both roles at 1440/390/320 widths.
This made **zero provider calls** and changed no real allocation. See
`docs/qa-lesson-planner-20261103.json`. Actual Wonder admission, planning quality,
latency, matching and cloud readiness remain unaccepted.

## Optional microphone input

`SOM_ENABLE_ASR=1` enables Muse Voice Transcribe on the same existing model key and budget ledger. The browser records only after a click, stops after ten seconds or a second click, converts to mono 16-bit PCM WAV at 16 kHz, and closes microphone tracks. The participant reviews the recognized text before submitting it for interpretation. Navigation and logout cancel capture.

The authenticated `/sessions/{id}/transcriptions` endpoint checks meeting membership, bounds the actual request body to 1 MB, persists the request ID before inference and returns a cached transcript on replay. Only a recording hash and transcript are kept, while the temporary WAV is closed and removed. Musical vocabulary biasing comes from the existing glossary. The budget guard persists a conservative hold before HTTP, settles from `audioDurationMs` rounded down to whole seconds, retains holds for ambiguous failures and blocks excessive reported usage. This leaves the ledger allocation unchanged.

The wire contract and metering were checked against Meta's [file-transcription reference](https://dev.meta.ai/docs/api-reference/voice/transcribe), [response schemas](https://dev.meta.ai/docs/api-reference/voice/schemas), and [pricing](https://dev.meta.ai/docs/pricing-rate-limits) on 3 November 2026. This is speech recognition. Synthesized replies and live streaming voice remain separate acceptance work.

A local real-model run on 3 November used two MMS-synthesized microphone samples through actual Chrome/RTC and made two Meta ASR plus two Spark calls. VI→EN was reviewed and delivered with actual MMS/RTC, heart completion and persistence after a local process restart. EN ASR changed “A minor chord” and appended contradictory words; that draft was rejected and stayed hidden from Artist. This is **partial acceptance**, not human speech quality or full EN↔VI acceptance. See `docs/qa-real-voice-20261103.json`. No automatic retry was made. The existing local ledger records the four new settled calls; its real rows must be reconciled with the cloud ledger before the next deployment, preserving the two earlier cloud-only charges.

Contextually named pitches now share letter-name / Vietnamese fixed-do identities, including spoken and hyphenated accidentals (for example `F-sharp` ↔ `Fa thăng`). Losing one sharp in a two-note phrase flags the draft and ordinary approval cannot deliver it; an Artist cannot override the Maestro gate. Ordinary articles such as “a scale” are not pitch A. This is a check of named-pitch sets, not proof of full musical or semantic equivalence: order, voicing and acoustic transcription still require review.

`SOM_ASR_MUSIC_HINTS=1` opts into general, language-scoped note and major/minor triad hints (97 EN / 93 VI). It is **off by default**; client requests cannot enable it. Hints never contain an expected transcript and recognized text is not silently corrected. Meta documents keyword/language bias as a nudge, not a constraint: [official recipe](https://github.com/meta-models/meta-model-cookbook/blob/main/06_muse_voice/01_voice_api_fundamentals/README.md#bias-the-transcription). The four-recording paired experiment recovered the previous A-minor root but failed on a held-out F-sharp sample and introduced a repeated Vietnamese numeric word. Thus it is not promoted to default or accepted as a quality fix. Eight real ASR calls settled $0.001800 in the existing ledger; no retries or interpretation/delivery were made. See `docs/qa-asr-music-vocabulary-20261103.json` for all outputs and mixed findings.

The deterministic validator now recognizes EN/VI spelled cardinals, decimal spellings and full BPM unit names. Numeric Vietnamese `không` is distinguished from negation in the same normalization path, and the denominator in `nhịp một phút` is a unit rather than a new count. A clear validator result is not proof of complete semantic equivalence or correct ASR; source review and Maestro approval remain required.

## Optional MMS speech evaluation

The existing Cabinet can play approved translations through Meta's [English](https://huggingface.co/facebook/mms-tts-eng) and [Vietnamese](https://huggingface.co/facebook/mms-tts-vie) MMS-TTS checkpoints. This candidate is disabled by default. The weights are **CC-BY-NC 4.0**; public/commercial deployment remains a separate unresolved release decision. No fine-tuning or voice cloning is included.

For a private technical evaluation, install `service/requirements-tts.txt` into an isolated environment, then run `python -m service.prepare_mms --output /private/tmp/cx1-som-tts-evaluation/models`. The preparation command downloads only pinned public assets and checks their SHA256; existing mismatched files are refused. Set `SOM_MMS_TTS_EVALUATION=1` and `SOM_MMS_TTS_DIR` to that model directory when starting the site. Runtime loading is local-only, safetensors-only, and does not download or execute remote model code. Both checkpoints use CPU inference with two threads.

`POST /sessions/{sid}/messages/{mid}/speech` checks the same meeting membership and Origin rules as other participant writes. It speaks only the canonical approved translation and language; request-supplied text cannot replace them. Neither role may hear a draft. The durable audio cache is keyed by message plus text/language/model/normalization revision. Browser playback starts after a click, exposes audio controls, and stops on navigation/logout. Audio is limited to 30 seconds of mono PCM16 at 16 kHz, and source text to 400 characters; longer text remains readable. Unsupported characters or ambiguous numeric formatting fail instead of silently disappearing. Musical numbers, decimal zeros, ranges, accidentals and time signatures are normalized before tokenization.

On 3 November, real CPU synthesis produced four EN/VI WAVs. The first request took 5.98 seconds including imports/load; subsequent samples took 0.25–0.56 seconds. Peak macOS process RSS reached 1364 MiB with both languages loaded, so the existing 512 MiB Modal configuration is insufficient for this implementation. It has not been increased or deployed. Production resource sizing, listening review and genuine microphone → ASR → translation → approval → speech acceptance are still open. The two-profile browser test used fixture translations and real MMS output; it confirmed EN and VI playback, no draft audio, no overflow at 390 px and cleanup on logout. It does not establish real ASR or translation quality.

## Server voice and participant language

The owner rejected browser/device voices. The live cabinet offers server audio only when its capability is connected; a failed or unavailable server never falls back to `SpeechSynthesis`. Playback is guarded by the same participant request/response marker and captured account/meeting object, including late A→B→A replies, logout and navigation.

Each participant selects their own EN or VI speaking language independently of their role or interface language. Dictation uses that choice and puts the transcript in an editable field. Only an explicit Send requests interpretation; source review, the reviewer and Maestro approval remain required.

The 4 November cloud candidate isolates MMS in a private Modal CPU worker with 3072 MiB, no Volume, writer Queue, account/model Secrets or public HTTP endpoint. The existing writer remains 512 MiB. Opt in at deployment with `SOM_DEPLOY_MMS_TTS=1` and an operator-selected `SOM_DEPLOY_MMS_TTS_DIR` containing the exact pinned assets. The worker image uses `requirements-tts-cpu.txt`; build and Linux CI must pass actual EN/VI synthesis, dense Vietnamese stress and a 2816 MiB peak-RSS gate before release. Runtime has no model downloads. Worker failures return a sanitized speech error; they do not own or release the writer permit.

Speech normalization is bounded to 240 characters after expansion, without truncation. Longer approved messages remain readable as text; unsupported notation/length is refused before inference. Audio remains bounded to 30 seconds of mono 16 kHz PCM16. Normalization revision v4 invalidates older audio-cache entries. This is a noncommercial technical evaluation of the existing MMS checkpoints, not fine-tuning or owner acceptance of their voice quality.

## Optional private RTC voice transport

Install `service/requirements-media.txt` in the backend environment and provision a dedicated admission database explicitly with `python -m service.prepare_media --database /absolute/operator/path/admission.sqlite3 --capacity 5`. Capacity is an operator choice for concurrent hosted lessons, not a product-wide participant limit. Existing valid databases are verified without reset; a capacity mismatch fails closed. The existing Modal writer permit or a single local orchestrator must own all related SQLite stores before app construction.

Set server-only `SOM_ENABLE_MEDIA=1`, `SOM_MEDIA_ADMISSION_DB`, `SOM_LIVEKIT_URL`, `SOM_LIVEKIT_API_KEY` and `SOM_LIVEKIT_API_SECRET`. Runtime never provisions a hosting account. Public operation requires a separately provisioned SFU with TLS/TURN and measured resource limits; none was deployed by this change. LiveKit must have `room.auto_create: false`: a real negative handshake probe verifies that participant tokens cannot create rooms. `deploy/livekit/local.example.yaml` is loopback-only; the official server accepts private key configuration through `LIVEKIT_KEYS`.

Each authenticated member gets a separate publish-only ingress room and subscribe-only Muse playback room. Room names/identities are keyed pseudonyms; 60-second participant JWTs grant no room administration, data publishing or metadata changes. No participant gets another member's ingress capability. The server subscribes to microphone audio only and **never copies raw ingress to playback**. Camera, performance/VAD/SAM processing, groups and streams remain unfinished stages. The browser SDK is pinned and vendored with its Apache-2.0 license, and loads only after an explicit voice connection. Microphone capture starts only on a recording click and is bounded to ten seconds independently on the server. RTC PCM uses the same persisted ASR/budget path as HTTP recordings, producing editable text rather than automatic delivery. Approved speech uses the existing canonical translation/cache and is published only by Muse.

Creation reserves admission and persists `provision_started` before any room API. Uncertain creation/deletion retains the slot. Completion enters `closing`, refuses new speech jobs, confirms all room deletions, then awards the original heart event. Failed cleanup is retryable; logout attempts every owned meeting and revokes the cookie even if some cleanup is pending. Server shutdown closes native workers and rooms before its existing writer permit can be returned. A stale generation's leave request cannot close reopened rooms. Client cleanup sends generation-bound keepalive immediately and serializes reconnect behind confirmed cleanup. Lost previous-owner PCM is cancelled; interrupted delivery/RTC recognition is marked uncertain without replay, while every model budget HOLD remains intact.

Server presence leases also cover a crashed browser or a lost leave request. A successful join grants 60 seconds to establish initial participant connections. Once a participant is observed, both of that person's private channels are expected; a missing channel gets a 20-second grace. The server's own Muse connections do not count as client presence. These times start from server observation: SFU reconnect timeouts can delay confirmation of a browser's departure. Authenticated HTTP polling alone does not renew RTC presence. A failed background cleanup retries after five seconds measured from the failure; admission stays reserved until external deletion is confirmed. Lease cleanup does not complete the logical meeting or award heart events. Presence is rechecked under the session lifecycle lock, so a recovered connection cannot be closed using an old snapshot. Shutdown drains an in-flight watcher cleanup and retains native handles until teardown succeeds before returning the writer permit.

The real localhost default-timer test closed a lost browser's rooms after 75.157 seconds including the SFU reconnect timeout, admitted the next lesson, then closed an unconsumed join after 61.019 seconds. The client leave request was blocked, all external rooms disappeared, and cleanup awarded no heart event. See `docs/qa-media-presence-20261103.json`. The separate original-versus-RTC ASR diagnostic still omitted the pitch A from the RTC sample; speech accuracy remains an open acceptance issue.

For an opt-in real localhost check, run `python scripts/verify_private_media.py --credentials /private/operator/livekit.json --data-dir /absolute/dedicated/test-directory --wav /absolute/mms-sample.wav`. The private JSON contains `url`, `key`, `secret`; it is never included in the repository. The verifier sends synthetic PCM into the actual SFU, decodes the supplied WAV at the recipient, rejects publish from a receive-only capability and verifies that a still-valid token gets 404 after confirmed deletion.

On 3 November, the verifier measured 19200 real ingress samples and 246 decoded MMS frames with no raw microphone leak; deletion freed admission. Two independent Chrome profiles passed real WebRTC recording/playback in both directions, a disconnect/reconnect cycle, 390 px layout and completion with exactly one heart increment per participant; the original heart signature/chain verified. **ASR and translation were explicit offline fixtures in that browser run.** This proves the private transport path, not real-model speech quality, cloud capacity, instrument/video handling, full group/stream behavior or watch acceptance. `/health` exposes `private_media_transport` separately and keeps full `media_rooms` and production readiness false.
