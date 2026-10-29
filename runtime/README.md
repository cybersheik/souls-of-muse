# Lesson admission runtime

This module is durable admission and lifecycle control for a bounded
number of simultaneous lessons **on our own media workers**, with the
bound explicitly selected by an operator. It is not a media runtime: it
provides no ASR, live video, room server, API framework, or broker.

**What this capacity is not.** It is not a product limit on participants,
accounts, chats, matching, or agent jobs. Participant <-> MUSE <->
participant coordination (including asynchronous chat exchanges) does
not reserve these slots; only an actual own-media session does. The
five-slot value used in some tests is a fixture — one explicit operator
configuration used to exercise the logic — not a product maximum, and
no maximum is encoded in the module.

The admission module remains internal only. There is no public
unauthenticated lifecycle endpoint, and none must be added around it.
Trusted in-process or operator-controlled callers drive the lifecycle.

Concurrency wording: tests cover **ADMISSION CONTROL CONCURRENCY only**.
They are not a media/load benchmark and do not show that any number of
real voice calls passed. No real media capacity is claimed or measured here.

## Storage model

- SQLite is supported only on a single persistent VM where all lesson
  processes share one database file. It is **not** a Vercel
  multi-instance database: serverless/multi-instance deployments need a
  shared atomic store (see the scaling boundary below), not this file.
- Transactions use `BEGIN IMMEDIATE` and `busy_timeout`, so concurrent
  processes cannot overshoot the stored capacity.
- Capacity is any strictly positive integer explicitly selected by the
  operator for our own media workers; there is no encoded maximum.
  Stored capacity is the single authority across processes.
- An explicit capacity passed to `LessonAdmission` or
  `initialize_database` must equal stored capacity. A mismatch fails
  closed: capacity is never silently lowered or increased.
- If stored capacity changes after a `LessonAdmission` object is
  constructed, later operations on that object fail closed.
- The database path is resolved to an absolute path and opened through
  `Path.resolve().as_uri()` (with the SQLite mode appended), so `?`,
  `#`, `%` and spaces in a path address the exact intended file. A path
  containing NUL is rejected before opening.
- Identifiers are matched in full, so trailing newlines are rejected.
- Future horizontal scaling requires an atomic shared PostgreSQL
  implementation passing the same conformance tests. That PostgreSQL
  scaling boundary is documented only: it is not implemented here, and
  SQLite remains single-VM only.

## Operator initialization

Initialization is an explicit operator action, separate from normal runs:

```python
from runtime.admission import initialize_database
# Example only: pick the positive capacity your own media workers can
# actually serve; nothing in the product caps this at five.
service = initialize_database('/path/on/persistent/vm/lessons.db', capacity=8)
```

A fresh database **requires** an explicit capacity: omitting it fails
closed instead of silently applying a hidden default. Initialization
runs in a transaction. A fresh database file with no
user tables may be created. Any non-empty partial or unrelated schema
is validated without DDL and fails closed if invalid; missing tables
are not healed, and the original file is preserved on rollback. An
existing valid database is never reset and its stored capacity is
never changed.

Normal runs open the database read/write without creating it:

```python
from runtime.admission import LessonAdmission
service = LessonAdmission('/path/on/persistent/vm/lessons.db')
```

A missing or corrupt database fails closed in a normal run. Slots never
expire from elapsed time, timeouts, restarts, or TTL: there is no TTL,
and `STARTING`, `ACTIVE`, and `CLOSING` all count until an explicit
terminal transition. In particular, `CLOSING` holds its slot until
`confirm_closed`.

## Integration sequence

1. Reserve the lesson slot first: `reserve(lesson_id, request_id)`.
   `CapacityExceeded` is raised before any external call. Use pseudonymous
   UUIDs or strict bounded ASCII IDs, never human email addresses.
2. Reserve model budget for each paid call through the existing budget
   guard. Do this per paid call, before spending.
3. Call `note_provision_started(reservation_id)` and let it commit.
   This is allowed only from `STARTING`; it is idempotent while the row
   stays `STARTING` and is rejected in `ACTIVE`, `CLOSING`, and
   terminal states.
4. Only after that durable flag, call the actual LiveKit room API to
   create the real room.
5. On confirmed room creation, call `mark_active(reservation_id)`.
6. A timeout or uncertain external outcome leaves the row `STARTING` with
   `provision_started` set. It cannot be cancelled and frees no slot.
   Operator reconciliation decides the real external state.
7. To finish, call `mark_closing(reservation_id)`; the slot still counts.
8. Delete the external room and obtain confirmation of that deletion.
9. Only then call `confirm_closed(reservation_id)`, which frees the slot.

`cancel_unprovisioned(reservation_id)` is only for `STARTING` rows whose
provisioning flag is still false, before any network attempt.
`confirm_closed` is not proof of external cleanup by itself: the trusted
caller is responsible for confirming external deletion first.

## Idempotence boundary

Same-pair `reserve()` idempotence is database-only: concurrent callers
with the same `(lesson_id, request_id)` pair receive the same row. That
does NOT claim exactly-once external effects. Duplicate callers that
both proceed past `reserve()` would both reach the external-API step.

Therefore provisioning must be run by a single trusted serialized
orchestrator, and external room creation must use a deterministic
external room identity derived from `reservation_id` as its idempotent
key. Do not launch two orchestrators from replayed rows. Replays return
the stored reservation so the one orchestrator can reconcile; they are
not permission for a second orchestrator to provision again.

`COMPLETED` and `CANCELLED` rows remain stored for idempotency. A
`lesson_id` is one-per-lesson and cannot be reused after a terminal state.
Snapshots contain status counts and pseudonymous reservation records only:
no credentials and no personal data.

## Product coordination vs this module (proposal, not implemented)

First-stage participant coordination is agent-mediated and chat-first,
separate from this reservation module:

- Each participant speaks **separately** with the service (e.g. its own
  Messenger thread with the community Page); MUSE mediates between
  participants under pseudonyms — no direct identity sharing is assumed,
  and nobody's contact details pass through.
- Chats and asynchronous exchanges (proposals, scheduling, materials)
  are **not** reservations of our own media rooms and never consume the
  slots above. A slot is taken only when an actual own-media session is
  provisioned through the integration sequence.
- Media hosting architecture stays separate from the chat channel.
  Supported Messenger API windows, limits and access still require
  connector validation before any adapter is built; **no Messenger
  adapter is implemented or deployed by this module**, and no unlimited
  platform capacity is claimed.

## Test interpreter

Project Python tests in this workstation run (30.10.2026) use exactly:

```sh
/Applications/Xcode.app/Contents/Developer/usr/bin/python3 -m unittest discover -s tests
```

(Xcode Python 3.9.6.) Multiprocessing tests use the `spawn` start
method explicitly and assert every child's exit code before reading
results; do not reintroduce `fork` there (see AI3-935) and do not pipe
test output through commands that mask the suite's exit status.
