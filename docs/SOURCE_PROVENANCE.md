# Source Provenance (OpenTimestamps)

This repo records time-fixed technical evidence for public code. It does not claim blockchain guarantees copyright or legal authorship. No filing is made. No legal advice is given. Licensing is undecided; nothing here grants a license.

## What is stored

Each `main` push, `v*` tag on main history, or manual `stamp` dispatch creates a prerelease `evidence-<shortSHA>` holding:

- `snapshot-<shortSHA>.tar.gz`: `git archive` output (`gzip -n`), exact bytes kept; its SHA-256 is in the manifest.
- `manifest-<shortSHA>.json`: canonical JSON with `commit_sha`, `archive_sha256`, repo, and `created_utc`. That date is the claimed git commit date (UTC, untrusted); it is explicitly recorded as not a proven timestamp.
- `manifest-<shortSHA>.json.ots`: OpenTimestamps proof for the manifest file only (`ots_target` names the manifest, not the archive).
- `manifest-<shortSHA>.ots-status.json`: written separately after stamping: calendar receipt, Bitcoin anchoring pending.

The manifest is built with `claims.status: prepared` before any submission. Only the manifest hash is sent to the free calendar; no source contents are sent. Existing release assets are never automatically replaced; a complete existing asset set makes a rerun exit early.

## Pending vs confirmed

- `ots stamp` means calendar receipt, Bitcoin anchoring pending, not confirmed.
- The scheduled / manual `upgrade` job checks the last 100 `evidence-*` releases. It upgrades a private copy, keeping the initial pending proof untouched, and inspects `ots info` for `BitcoinBlockHeaderAttestation`.
- Only if that attestation is present does it upload `<manifest>.bitcoin.ots` plus a status JSON stating `bitcoin_attestation_present: true` and `independent_full_node_verified: false`, and retitle the release to `Bitcoin attestation included; independent verification required`. If still pending, it uploads nothing.
- Full independent verification requires Bitcoin Core; no node is available in CI, so CI never claims verified.

## Verify

```sh
ots info manifest-<short>.json.ots
ots verify manifest-<short>.json.ots -f manifest-<short>.json  # needs Bitcoin Core for full independence
sha256sum snapshot-<short>.tar.gz  # compare to manifest archive_sha256
```

## Rollout to other repos

Disabled by default. Copy this workflow plus `scripts/provenance_manifest.py` only into repos on a repo-specific allowlist under explicit owner consent for that repo. This workflow only operates on the current repository (`gh --repo` is validated owner/name). Keep triggers on `main` and `v*` only, never `pull_request`. Keep `contents: write` scoped to the stamp/upgrade jobs, `persist-credentials: false`, no PAT, no paid transaction.
