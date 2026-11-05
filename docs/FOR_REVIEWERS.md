# For reviewers

Souls of Muse – Meta Global AI Developer Hackathon 2026, Startup track.

This page maps each judging criterion to evidence in this repository. Every statement carries one of five statuses: **Working**, **Prototype**, **Offline-tested**, **Designed**, **Planned** (`docs/DISCLOSURE_POLICY.md` §5). Anything simulated is named as simulated.

## In one paragraph
Souls of Muse is a service for an international community of musicians, dedicated to keeping the human skills of playing instruments and singing alive. The hackathon work, carried out by the project owner with a team of AI agents on Meta models, spans seven workstreams: the lesson service, engineering on Meta models, research, community and governance, outreach, media, and process. Code is one of them, not all of them.

## Impact (30%)
- Mission and problem: `README.md`, [04 Community and governance](workstreams/04-community-and-governance.md)
- Who still plays music, and why it matters: [03 Research](workstreams/03-research-with-muse.md)
- Community and outreach, in aggregate: [05 Outreach](workstreams/05-outreach.md)

## Use of Meta AI tooling (25%)
- Model roles and the generation/review pattern: [02 Engineering on Meta models](workstreams/02-meta-model-engineering.md)
- Research driven by Muse: [03 Research](workstreams/03-research-with-muse.md)
- Media generated with Muse Image: [06 Media](workstreams/06-media.md)
- Journal of model participation (sanitized from the team's session registry): [`docs/journal/`](journal/)

## Technical depth and execution (20%)
- Decision records: [`docs/decisions/`](decisions/)
- Budget safety for paid model calls: `harness-bench/`, [ADR 0001](decisions/0001-reserve-model-budget-before-each-paid-call.md)
- Lesson admission runtime: `runtime/`, [ADR 0002](decisions/0002-lesson-slots-never-expire-by-time.md)
- Source provenance: `docs/SOURCE_PROVENANCE.md`, [ADR 0003](decisions/0003-timestamp-hashes-not-source.md)
- Outbound disclosure gate: `docs/DISCLOSURE_POLICY.md`, `scripts/disclosure_check.py`

Reproduce the offline checks (no API key, no paid calls):
```sh
python3 -m unittest discover -s tests -v
cd harness-bench && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt && .venv/bin/python -m unittest discover -s tests -v
```

## Demo (25%)
- Demo video: https://www.youtube.com/shorts/1EAl-cj0DJ4 (2:56) · jury dossier: https://soulsofmuse.app/dossier/
- Live preview: linked from `README.md`
- What is real and what is simulated: [01 Service and lesson](workstreams/01-service-and-lesson.md)

## What existed before the event
[`docs/HACKATHON_CONTRIBUTIONS.md`](HACKATHON_CONTRIBUTIONS.md) and the `BASELINE.md` of each component. We do not claim that every part of the broader project was created during the event.

## Attribution
Human decisions, architecture and acceptance: the project owner. AI-assisted implementation, review and research are labelled per item. See `README.md` and `NOTICE.md`.
