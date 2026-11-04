# 02. Engineering on Meta models

## Why it matters
A music lesson mediated by AI fails if terminology is wrong, latency is unbounded or costs run away. This workstream builds the guardrails and test benches that let Meta models be used safely in a live product.

## Before the event
An initial Python test bench existed and was reviewed at the start of the event (`docs/HACKATHON_CONTRIBUTIONS.md`). <!-- FILL: pre-event state of agent harnesses and desktop applications, per BASELINE.md -->

## During the event
| Item | Status | Evidence |
|---|---|---|
| Model role map: interpreter, reviewer, transcription, vision | Designed | `harness-bench/config/models.yaml` |
| Musical terminology validator and seed glossary (EN/VI) | Offline-tested | `harness-bench/harness/validator.py`, `harness-bench/data/` |
| Pre-request atomic budget reservation | Offline-tested | [ADR 0001](../decisions/0001-reserve-model-budget-before-each-paid-call.md), `harness-bench/tests/` |
| Honest probe reporting: estimated latency is never reported as measured | Offline-tested | `harness-bench/tests/test_probe_reporting.py` |
| Own agent harness on the Muse Wonder API with on-demand tool loading and memory | <!-- FILL: status --> | <!-- FILL: apps/… + BASELINE.md --> |
| Desktop rehearsal client with 3D Muse, vision and music geometry | <!-- FILL: status --> | <!-- FILL --> |
| Media studio client | <!-- FILL: status, stated exactly as verified; no claim beyond what runs --> | <!-- FILL --> |

## How Meta models were used
<!-- FILL from the agent-journal registry through docs/templates/JOURNAL_ENTRY.md. Per model: role, tasks, how the output was checked, what was unexpected, limits hit. Generation/review pairs (one model implements, another reviews) are a key pattern to show. -->

## Not claimed
- The paid transcription route is disabled until its usage contract is verified. SAM and TTS are not implemented in the budget-safe adapter.
- The budget guard bounds only calls routed through its ledger on one machine.
