# Baseline template (pre-event state of a component)

Place a copy as `BASELINE.md` in the folder of every component that existed before the hackathon (26 Oct 2026). It shows reviewers exactly where earlier work ends and event work begins, without publishing pre-event source code (`docs/DISCLOSURE_POLICY.md` §6).

```markdown
# <Component> – baseline before 26 Oct 2026

## What existed before the event
Short description of the pre-event state: purpose, main screens or modules, what worked, what did not.

## Evidence of the pre-event state
- Screenshots: `baseline/*.png` (no personal data, no machine names in title bars)
- Content hash of the pre-event source tree: `sha256:<hex>` (the source itself stays private)
- Hash method: e.g. `git archive <pre-event commit> | sha256sum`

Note: a hash proves which bytes existed when it was first timestamped, not when they were written.

## What was done during the event
| Area | Before | During the event | Status |
|---|---|---|---|
| <e.g. model integration> | <none / other model> | <Muse Wonder …> | Working / Prototype / … |

## Where the event work is
- `apps/<component>/…` – new code, published in full
- `apps/<component>/patches/…` – changes to pre-event files, as diffs

## Third-party assets
| Asset | Origin | Licence / basis |
|---|---|---|
```
