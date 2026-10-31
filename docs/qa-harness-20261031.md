# Harness verification — 31 October 2026

Implementation: Meta Muse Wonder through the existing Muse Code subscription.
Integration, deployment packaging and independent verification: CX1.

## Verified locally

- 104 Python tests passed, plus 23 subtests, using the exact FastAPI/Pydantic versions pinned for deployment.
- 25 frontend tests passed. The P0.1 frontend source is unchanged from e76d95f.
- A real loopback Uvicorn process passed six HTTP checks: honest health, role restriction, safe failure with no model key, protected state, persistence through a process restart, and audit-chain verification after restart. This was a local check with temporary test credentials and no model calls.
- The configured direct Meta credential passed a free GET /models check; the required Muse models were listed. This establishes credential/catalog access only.
- Meta Chat Completions usage was checked against the current official schema. Optional reasoning-token details are validated strictly and are not charged twice. Unknown or malformed billing fields retain the budget HOLD.

## Functionality in this source

Private EN–VI text interpretation with role-bound Maestro/Artist credentials, a draft that requires Maestro approval, persistent session state, idempotent messages, an audit log, and the existing MetaAdapter and atomic budget guard. A small `/pilot` page supports manual operator testing.

Modal packaging uses CPU only, one writer, a persistent Volume, explicit provisioning and a writer permit. Persisting the budget reservation must succeed before any paid HTTP request. Missing credentials, missing ledger, persistence failures and invalid billing usage fail closed.

## Delivery state

The updated P0.1 interface is published at https://preview.soulsofmuse.com/#/welcome and https://preview.soulsofmuse.com/#/space/maestro. It contains demonstration data and is not a connected lesson service. Frontend deployment packaging is dd146c0; public files were compared with source and the preview headers verified.

The backend in this change has **not** been deployed. No real paid EN–VI exchange has been run. Cloud authorization, secrets, bounded budget provisioning, actual startup/restart, and a supervised live exchange remain release checks. Local fake-transport results do not establish those outcomes.

Voice, ASR/TTS, live media, group sessions and streams with media, watches, social identity/signing, heart-journal integration and League management remain outside this first implemented scenario. The full product scope has not been reduced.

## Reproduce offline

Install `harness-bench/requirements.txt`, `service/requirements.txt`, `modal==1.6.3`, and pytest into an isolated environment. From the repository root:

```sh
python -m pytest service/tests harness-bench/tests tests -q -p no:cacheprovider
node --test tests/test_p01.cjs tests/test_portal.cjs
```

No API credential is needed for these tests. See `service/README.md` for explicit cloud provisioning; the application never silently creates or resets a spending ledger.
