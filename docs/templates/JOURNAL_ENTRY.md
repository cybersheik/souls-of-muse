# Journal entry template

Use this template to publish what happened in a piece of agent-assisted work. It replaces raw transcripts, which are never published (`docs/DISCLOSURE_POLICY.md` §3.4). One entry covers one decision or one unit of work. Copy the block below into `docs/journal/YYYY-MM-DD-short-title.md`.

```markdown
# <Short title>

- **Date:** YYYY-MM-DD (event day N)
- **Workstream:** 0N <name>
- **Status of result:** Working | Prototype | Offline-tested | Designed | Planned
- **Models and tools:** <Meta model names and versions; other tools named honestly>
- **Roles:** <e.g. implementation by Muse Wonder; independent review by Muse Spark; integration and tests by the integrator agent; decision by the project owner>

## Goal
One or two sentences: what had to be achieved and why it matters to musicians or teachers.

## What the models did
Concrete contributions: generated, reviewed, translated, measured. Include the
prompt *pattern* or role design if it is interesting, never the full system prompt.

## How it was verified
Tests, measurements, manual checks, reviewer findings. Name the evidence file in this repository.

## What failed or was corrected
Dead ends, wrong outputs, retracted claims and what replaced them.

## Result and limits
What now exists, its status, what is simulated, what remains.

## Evidence
- `path/in/repo` – what it shows
```

## Sanitising checklist

- [ ] No tracker IDs, chat links, local paths, machine names, session IDs (§8 replacement table).
- [ ] No names of people without consent; no other participants' projects.
- [ ] Every number has a source and date; estimates are labelled.
- [ ] Meta models credited only for what they did; other tools named.
- [ ] `python3 scripts/disclosure_check.py <file>` passes.
