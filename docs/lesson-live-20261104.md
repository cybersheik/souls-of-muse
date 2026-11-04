# Three-person lesson candidate — 4 November 2026

This candidate starts at DW1's merged Portal 2.1 integration commit
`4a8b1e890549dc7b22cf487e69741892782a0c56`. It preserves that portal and
adds a registered Maestro plus two registered Artists to the live lesson.
It has not been promoted to production.

## Behavior

- Group membership, personal cookie accounts and private notes are independent
  for all three people. Only the Maestro starts/ends the lesson, changes the
  shared worksheet and approves translations. Group message retries are scoped
  to the actual sending account; the shared chat shows that person's name.
- An explicit camera/microphone action starts a three-person native WebRTC mesh.
  Camera, mute, hang up and reconnect operate on the participant's own tracks.
  Direct speech and video are retained per Aidar's existing decision. Muse's
  translation path is separate. The older Kimi mediated-only description does
  not override the owner's later decision.
  Signalling requires membership and the current connection generation. Media
  is not recorded or relayed by the application. There is no TURN/SFU; this is
  a bounded single-process classroom transport, not proven remote-NAT coverage.
- The local macOS site can opt into installed Daniel/Linh voices with
  `SOM_NATIVE_TTS=1`. This uses the existing approved-translation speech route;
  it does not download MMS models or make provider calls. It is not Linux TTS.
- Vercel's plain Node entry point now has an explicit rewrite and derives the
  public route from `req.url`, with a fixed-function query fallback. The gateway
  passes personal cookies and the participant marker, never model/pilot keys.
- Normal authenticated limits are 120 requests/minute/account; signalling has
  a separate 360/account allowance. Anonymous or stale account contexts retain
  the 120/IP limit. Three idle clients perform 144 ordinary GETs/minute, so a
  shared IP must not be treated as one participant.
- Kimi's original signed heart remains unchanged. A two-Artist group reports
  `group_policy_pending` and receives no invented pair credits. Individual
  completion retains its existing signed, idempotent behavior.

## Observed verification

CX1 ran the current site on ML1 loopback with three isolated Chrome contexts.
All three personal logins and group opening worked; six native peer connections
exchanged inbound audio RTP bytes and decoded video frames. Mute, one Artist's
hang up, the other pair continuing, and the Artist reconnecting passed. Desktop
1440 and Artist 390 had no horizontal overflow; there were no page errors.
Camera/microphone streams were synthetic. This is not a three-device or human
audio-quality acceptance. Installed EN/VI voices separately produced valid PCM
WAVs. The offline adapters in unit tests are not live model acceptance.

Offline verification: 224 service tests passed (two macOS voice integration
checks skipped in the ordinary suite), 65 Harness, 37 root, five unchanged
original Kimi heart tests and 102 Node tests passed. The two opt-in macOS voice
checks also passed separately. This is not cloud E2E acceptance.

At this checkpoint the operator's local process deliberately has no model key:
`model_ready=false`. Real translation/ASR and reviewed spoken delivery therefore
remain unavailable. The existing local budget/ledger is referenced in place;
no reservations, history or allowance were reset. This work made no model calls.

## Release configuration and operator handoff

The same-origin local entry point is `uvicorn service.site:app`, one worker.
It serves the Portal 2.1 files and `/api/harness` under one origin. Participant
passwords, tokens, signing key, budget paths and runtime data stay server-side.
The fresh local classroom signing key is not production identity/SoulID.

For a separately approved public HTTPS classroom, allow its exact Origin in
`SOM_WEB_ORIGINS` (comma separated) and use `SOM_COOKIE_SECURE=1`. Authenticate
and recheck three participants on that actual HTTPS origin before calling it
usable. ML1 must remain awake with the single writer running. The owner must
choose an external recording workflow; this candidate does not record children.

For a later owner-approved Vercel release:

- Release this candidate's exact reviewed commit, preserving Portal 2.1.
- Set server-only `SOM_HARNESS_URL` to the reachable new backend API root.
  For a public `service.site` instance that is `https://<host>/api/harness`;
  for a standalone Harness ASGI instance it is the host root. It must not point
  at the old Modal 0.2.0 backend.
- Backend `SOM_WEB_ORIGINS` must include `https://soulsofmuse.app` and the exact
  approved preview/public classroom origins, with secure cookies enabled.
- Supply `MODEL_API_KEY` only from an approved source, preserve the approved
  budget config and complete ledger, and retain a controlled single writer.
- Deploying to the existing cloud additionally needs fresh cloud ledger
  reconciliation and the existing production heart identity. Local classroom
  keys/data do not replace them.

No production environment, DNS, access protection or cloud deployment was changed.
