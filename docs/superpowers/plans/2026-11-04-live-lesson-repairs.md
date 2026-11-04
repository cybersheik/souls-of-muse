# Live lesson repair implementation plan

> Agentic workers: execute the already-approved947review plan with systematic debugging, targeted RED/GREEN tests and independent review. Owner's direct Go follows published review c2c3a982-78e4-47c8-a9a2-579a4d4ce7ee.

Goal: make the existing live cabinet usable and provide a guarded ENVI server-speech baseline on soulsofmuse.app.
Architecture: preserve Vercel frontend + existing Modal single-writer backend and all data/history. Separate explicit demo from account-bound live UI. Reuse the existing Meta MMS adapter for a noncommercial technical pilot; this is CX1's implementation choice and does not claim owner voice-quality acceptance or fine-tuning.
Tech: vanilla JS/CSS, FastAPI, pinned CPU PyTorch/Transformers, existing Modal Volume/Queue/Secrets.
Spec: AI3-947 critical review and latest owner direction to execute it.

## Constraints
- Public Portal2.1 and approved central plan/right Notebook retained; Portal2.2 design still needs owner acceptance. Compatible Notes bugfix can ship independently.
- No native-device-voice substitution, no new external paid provider/key/tunnel, no copied credentials.
- Two human↔Muse links; no permanent three-way presence requirement.
- Speaker edits transcript before explicit send; canonical translation/reviewer/Maestro approval remain.
- Whole-pilot Meta allowance0.25/stop0.2375/history unchanged; no reset/reseed/checkpoint. Only existing cloud writer, Volume and production identity.
- MMS weights CC-BY-NC4.0: technical noncommercial pilot only; no claim of commercial release approval.
- No directory deletions. Ignore existing untracked output/.playwright-cli.
- All API/user account context markers and private-note boundaries preserved.
- Actual human voice/hardware/5sP95 remain acceptance work, not inferred from CI.

## Review focus
- Late audio after accountA→B→A, meeting change or navigation must never play.
- Live home cannot render fake participants/time/metrics or select another role.
- Mobile source review, send and speech controls must be reachable without empty planning blocks above them.
- CPU-only TTS image must be tested with both pinned checkpoints before enabling it; memory must fit measured peak.
- Recreate must preserve original single-writer permit and full ledger; no retry of ambiguous queue mutation.

## Tasks
1. UI worker: cabinet.js/css and app.js; RED/GREEN live/demo separation, account-owned route, mobile conversation-first, accessible labels. No service/harness edits.
2. Notes worker: scoped hidden CSS and computed-style regression on1440/1179/390. No Portal2.2 redesign.
3. Root frontend: failing server-audio account/race tests, guarded request/response path, disable rejected device fallback; participant speaking-language setting independent ofrole.
4. TTS worker: bounded music-token normalization and cache revision with false-positive regressions; no downloads/cloud.
5. Root cloud packaging: explicit Linux CPU torch pins, public pinned weights image,2GiB requested memory only for MMS-enabled image, clean Linux synthesis verification and source metadata. Do not touch storage/caps/identity.
6. Root acceptance: targeted tests then full relevant Node/Python + clean Linux runtime. Own isolated browser1440/390 on local candidate before release.
7. Root release: fresh cloud ledger/noHOLD snapshot, review exact source and deployment patch, one substantive existing-app recreate, main frontend exact SHA. No cosmetic-only redeploy.
8. Root hosted check: health/source/files, roles, fresh canonical server audio, preserved ledger/history, actual user-visible fixes. Then concise947/920 checkpoint and update quiet monitor baseline.

Status: implementation started; review is published. No task is complete solely because a worker reports GREEN.
