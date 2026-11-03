# 07. Process and provenance

## Why it matters
Reviewers need to trust what they see: who did what, what existed before the event, and that published claims match reality.

## How the team works
- **Decisions:** the project owner sets requirements and architecture and accepts results.
- **Generation and review:** Meta models generate. A different model or agent reviews independently. An integrator agent tests, integrates and verifies.
- **Records:** agent sessions that involve Meta models are kept in a journal registry. Public summaries are derived from it through `docs/templates/JOURNAL_ENTRY.md`.
- **Outbound review:** everything public passes `docs/DISCLOSURE_POLICY.md`, including an automated check in CI.

## Timeline
| Date | Milestone |
|---|---|
| 19 Oct 2026 | Application submitted, Startup track |
| 26 Oct 2026 | Kickoff |
| 27 Oct 2026 | Public repository, budget guard, admission control, timestamp evidence |
| <!-- FILL --> | <!-- FILL: key milestones per workstream --> |
| 4 Nov 2026 | Submission |

## Evidence
| Item | Status | Evidence |
|---|---|---|
| Pre-event vs event boundary | Working | `docs/HACKATHON_CONTRIBUTIONS.md` |
| Source timestamp evidence on every push to `main` | Working | `docs/SOURCE_PROVENANCE.md`, `evidence-*` releases, [ADR 0003](../decisions/0003-timestamp-hashes-not-source.md) |
| Outbound disclosure policy and automated check | Offline-tested | `docs/DISCLOSURE_POLICY.md`, `scripts/disclosure_check.py`, `tests/test_disclosure_check.py` |
| Report on Meta model participation, from the journal registry | <!-- FILL --> | <!-- FILL: docs/journal/ --> |
| Corrections and retracted claims | <!-- FILL --> | <!-- FILL: sanitized list --> |

## Not claimed
A timestamp proves the existence of particular bytes, not authorship or copyright. AI-generated implementation is labelled as such (`README.md`, `NOTICE.md`).
