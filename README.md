# Souls of Muse

Music education with teacher-led lessons, a Muse AI mediator and bilingual musical instruction. This public repository contains the current prototype and the model test bench prepared for the Meta Global AI Developer Hackathon 2026.

## Current state

- `web/`: interactive Muse Lesson 2.0 design prototype. Student indicators, messages, video and lesson metrics are simulated. It is not a live lesson service.
- `harness-bench/`: Python terminology validator, event schema, model adapters and budget reservation guard. 19 offline tests pass.
- `deploy/godaddy/`: dependency-free Node 22 wrapper and HTTP checks for uploading the existing design preview to GoDaddy Web Hosting. This is deployment tooling, not the live lesson backend.
- `runtime/`: durable single-VM admission and lifecycle control for up to five simultaneous lessons. Counts include starting and closing rooms; restart does not free occupied slots. See `runtime/README.md` for the internal integration contract and future scaling boundary. Admission concurrency tests are not a five-room media benchmark.
- Real EN/VI audio, Meta voice delivery, live media rooms, real watch integration, tactile metronome and production load capacity are pending integration and verification. They remain project requirements.

Preview: https://preview.soulsofmuse.com/

## Run offline checks

```sh
python3 -m unittest discover -s tests -v
cd harness-bench
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

No API key or paid request is needed for the offline suite. Read `harness-bench/docs/BUDGET_SAFETY.md` before any paid use. A lost budget history must block execution. The app ledger does not cap other keys or clients in a provider account. Do not initialize a zero production history without reconciling earlier account usage.

## Hackathon contribution record

The project concept and interface work predate the hackathon. The prototype deployment tooling, current budget safety repair, regression checks and source timestamp integration were developed on 27 October 2026 during the hackathon. See `docs/HACKATHON_CONTRIBUTIONS.md` for exact boundaries. This repository does not claim that every feature of the broader project was created during the event.

## Attribution and rights

Aidar Kozhakhmetov directs the project, requirements, architecture and acceptance decisions. Meta Muse Wonder and Muse Spark assisted with code generation and independent review; CX1 integrated and verified the resulting artifacts. Prior interface work was prepared in Claude Design, and the initial Harness bench was prepared by Kimi. AI-generated implementation is labelled as such.

Public availability permits inspection through GitHub. No general reuse or patent license is granted by this notice; an open-source license requires the project owner's explicit choice. Third-party libraries, model weights and assets retain their own licenses. A timestamp is evidence of existence of particular bytes at or before a time, not copyright registration or proof of legal ownership.
