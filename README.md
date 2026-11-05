# Souls of Muse

Souls of Muse is a service for the international community of musicians, dedicated to keeping the human skills of playing musical instruments and singing alive.

Music education is one part of this broader mission. The current prototype focuses on teacher-led lessons, a Muse AI mediator and bilingual musical instruction.

This public repository contains the site served at https://soulsofmuse.app and the model test bench prepared for the Meta Global AI Developer Hackathon 2026.

## For the jury

- Jury dossier (eight developments, 5 Nov 2026): https://soulsofmuse.app/dossier/ · PDF: https://soulsofmuse.app/dossier/Souls-of-Muse-Jury-Dossier.pdf
- The eight developments: Souls of Muse & Muse Lesson; MetaMezonin rehearsal room; TopDog Colors music-video studio; three Ray-Ban Meta services; Sol Muse robot; Sound Made Visible; musical signature & community; music and filmmaking with Muse.
- Live-action film (2:56): https://www.youtube.com/shorts/1EAl-cj0DJ4
- Live service: https://soulsofmuse.app/ · capability report: https://soulsofmuse.app/api/harness/health
- Research: https://soulsofmuse.app/sci-sound-labs/
- Reviewer map: `docs/FOR_REVIEWERS.md` · workstreams: `docs/workstreams/` (including who did the work and the paths that did not work)

## Current state

- `web/`: the site served at https://soulsofmuse.app — the Convention portal (sign with your name written as music; the signature is kept on the visitor's device), the seven Leagues as a 3D circle, League pages, My space and the lesson interface. The lesson connects to the Muse service in `service/`; its verified scope and open items are recorded in `service/README.md`.
- `harness-bench/`: Python terminology validator, event schema, model adapters and budget reservation guard. 19 offline tests pass.
- `deploy/godaddy/`: dependency-free Node 22 wrapper and HTTP checks for uploading the existing design preview to GoDaddy Web Hosting. This is deployment tooling, not the live lesson backend.
- `runtime/`: durable single-VM admission and lifecycle control for a bounded number of own-media lesson slots, with the positive capacity explicitly selected by an operator (no product-wide maximum; some tests use five slots purely as a fixture). Counts include starting and closing rooms; restart does not free occupied slots. This bounds only our own media workers — participant matching, chats and agent jobs are separate and do not consume these slots. See `runtime/README.md` for the internal integration contract and future scaling boundary. Admission concurrency tests are not a media benchmark.
- Cloud pilot (5 Nov 2026): participant login, roles, text sessions, EN↔VI interpretation with approval before delivery, Meta speech recognition and spoken replies with Meta MMS-TTS (English and Vietnamese) are enabled; the service reports `production_ready=false`.
- Still open and verified as not done: full human acceptance of a bilingual lesson and the target response time, live media rooms, automatic matching, the watch application, the physical tactile metronome and production load capacity. They remain project requirements.

Live site: https://soulsofmuse.app/

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

The project concept and interface work predate the hackathon. Work done during the event (26 Oct – 5 Nov 2026) is recorded per workstream in `docs/workstreams/01`–`07`, with the tools and the Meta models behind them in `docs/workstreams/08-who-did-the-work.md` and the abandoned paths in `docs/workstreams/09-dead-ends.md`. The 27 October record in `docs/HACKATHON_CONTRIBUTIONS.md` covers the first day only. This repository does not claim that every feature of the broader project was created during the event.

## Attribution and rights

Aidar Kozhakhmetov directs the project, requirements, architecture and acceptance decisions. Meta Muse models (Muse Wonder, Muse Wonder Full, Muse Spark, Muse Image) did much of the code, research, music and media work, often running inside agent harnesses such as Muse Code, Hermes Agent, OpenCode, MetaMezonin and TopDog Colors; `docs/workstreams/08-who-did-the-work.md` pairs each tool with the model behind it. Codex (OpenAI) integrated and verified many of the resulting artifacts. Prior interface work was prepared in Claude Design, and the initial Harness bench was prepared by Kimi. AI-generated implementation is labelled as such.

Public availability permits inspection through GitHub. No general reuse or patent license is granted by this notice; an open-source license requires the project owner's explicit choice. Third-party libraries, model weights and assets retain their own licenses. A timestamp is evidence of existence of particular bytes at or before a time, not copyright registration or proof of legal ownership.
