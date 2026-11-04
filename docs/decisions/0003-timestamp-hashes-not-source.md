# 0003. Timestamp hashes of published source, never the source itself

- **Status:** Accepted
- **Date:** 2026-10-27
- **Workstream:** 07 Process and provenance
- **Decided by:** project owner
- **Prepared with:** workflow implemented by Muse Spark, independently reviewed by Muse Wonder; integration by the integrator agent

## Context
The project wanted independent, low-cost evidence of which exact source bytes existed at a given time. It must not send source code to third parties, create accounts or spend money, and it must not overstate what a timestamp proves.

## Options considered
1. **Rely on commit dates.** These are self-asserted and trivially editable.
2. **Paid notarisation or registration services.** Cost, accounts, and they still prove only existence.
3. **OpenTimestamps over a canonical manifest.** Free calendars, no account. Only a hash leaves the repository.

## Decision
Option 3. On each push to `main`, CI builds:
- a deterministic `git archive`;
- a canonical JSON manifest with the archive's SHA-256;
- an OpenTimestamps receipt for the manifest only.

All three are kept as release assets. A scheduled job upgrades receipts once a Bitcoin attestation exists and keeps the original pending proof.

## Consequences
- Only a hash is sent to the calendar servers.
- "Pending" is never called confirmed. CI never claims independent full-node verification.
- A timestamp is evidence of existence of particular bytes, **not** copyright registration or proof of authorship.
- Every push to `main` creates permanent public evidence. This is why `docs/DISCLOSURE_POLICY.md` requires review **before** merge.

## Verification
`tests/test_provenance.py`, the `source-timestamp` workflow runs and their `evidence-*` releases. Procedure: `docs/SOURCE_PROVENANCE.md`.
