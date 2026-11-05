# 07. Process and provenance

## Why it matters
Reviewers need to trust what they see: who did what, what existed before the event, and that published claims match reality.

## How the team works
- **Decisions:** the project owner sets requirements and architecture and accepts results.
- **Generation and review:** where possible, Meta models generate, a different model or agent reviews independently, and an integrator agent tests, integrates and verifies. Not all work followed this pattern: some deliverables were built by non-Meta tools, and [08](08-who-did-the-work.md) names them.
- **Records:** agent sessions that involve Meta models were kept in an internal journal registry, whose last snapshot is 31 Oct. Public summaries are meant to be derived from it through `docs/templates/JOURNAL_ENTRY.md`; none have been written yet.
- **Outbound review:** from 4 Nov, public text is checked against `docs/DISCLOSURE_POLICY.md`, with an automated check that runs in CI on draft PR #6. In CI the check runs without the private denylist, so internal names are checked locally. Material published before the policy existed (earlier pull request descriptions, branch names, commit metadata, site briefs) has not been re-reviewed.
- **Attribution:** every task in the team's internal tracker is formally assigned to the project owner, who is accountable for it. Assignment therefore says nothing about who did the work. Our agents work under short call signs, and a call sign often hides the model behind it: a third-party agent harness such as Hermes Agent or OpenCode was frequently running a Meta Muse model. [08 Who did the work](08-who-did-the-work.md) pairs every call sign with the model actually behind it and lists the work done by Meta Muse models separately from the work done by other tools.
- **Dead ends are published, not hidden:** [09 Paths that did not work](09-dead-ends.md).

## Research method: Bi-Level AutoResearch (double loop)
The sound research ("Sound Made Visible", workstream 03) ran as a two-level AutoResearch loop. It is inspired by Karpathy's single-loop [autoresearch](https://github.com/karpathy/autoresearch) and adds an outer loop; the method consultation compared the design with the published [Bilevel Autoresearch](https://arxiv.org/abs/2603.23420). Both levels were two separate contexts of the same Meta model, so this is a simplified double loop, not the fully governed design described in [09](09-dead-ends.md).

- **Inner loop (changes the candidate).** In each 300-second window, Muse Wonder (`muse-wonder-1.0`, direct Meta API) makes two calls. Call 1 proposes a hypothesis: a formula from a pre-declared family and range, passed as data; no generated code is executed. A frozen evaluator scores it against targets built from hidden seeds (relative numerical error plus an FFT check on synthesised audio). Call 2 reads the counterexamples and refines the formula.
- **Outer loop (changes the search).** Muse Wonder, in a separate context, runs after every second window. It reads the outcomes and rewrites the research conditions: focus, priorities, ranges and assumptions, inside a fixed set of families. A change takes effect only from a later window. 11 of 11 outer decisions were applied.
- **Frozen parts.** The outer loop did not change the evaluator, the metric or the holdout. The engine source files kept their recorded hashes for the whole run.
- **Campaign v2, 31 Oct 2026, 12:25–14:25 ICT:** 24 windows, 59 direct Meta API calls (48 inner, 11 outer), 23 PROMISING, 1 INCONCLUSIVE, 0 REJECTED. These are calibrations of known physics against a synthetic model, not 24 discoveries. Whether the outer loop beats a fixed strategy was not measured.
- **Who:** both research roles were Muse Wonder (`muse-wonder-1.0`) in separate contexts, called through the direct Meta API. The runner and controller code and the repairs of the stopped run were written by Muse Wonder in an agent harness (Hermes Agent, profile "Jack", running Muse Wonder). Whether the 59 research calls were issued from inside that harness or by the runner it wrote is not recorded. Audio adapters, the renderer and the films were written by Muse Wonder Full (`muse-wonder-full-1.0`) in Meta's Muse Code. Not done by Muse: the method design, the independent acceptance tests, the final audit and report and the publication of the site section were done by CX1 (Codex, OpenAI); the film design was approved by DW1 (Claude, Anthropic) with Claude Design; the starting prototype was a Kimi demo. The originally planned governed design (Muse Code in the inner role, separate ledgers, stop rules) was not run as designed; see [09](09-dead-ends.md).
- **Public report:** <https://soulsofmuse.app/sci-sound-labs/jury-report.html>.

## Timeline
Times are ICT (UTC+7). Workstream numbers in brackets.

| Date | Milestone |
|---|---|
| 19 Oct 2026 | Application submitted, Startup track |
| 26 Oct 2026 | Kickoff |
| 27 Oct 2026 | Public repository, budget guard, admission control, timestamp evidence |
| 29 Oct 2026 | [07] Last change to `main` (`26224ed`) and its timestamp evidence release. [01] First Welcome portal preview, code by Muse Wonder in Hermes Agent (PR #2, draft). [03] Bi-Level method consultation (design only, no model calls). |
| 30 Oct 2026 | [01] Owner rejects the Welcome portal on design; design moves to Claude Design. [03] Sound pilot with six variants; reclassified by the independent reviewer as engineering feasibility only. [03] Glasses: first live SAM 3.1 calls; first contract-council run (Muse Wonder + Muse Spark mixture) finds 18 of 18 planted issues in a demo contract supplied as text. |
| 31 Oct 2026 | [03] First Bi-Level nature run stopped during its seventh window and repaired by Muse Wonder; campaign v2 completed: 24 × 300 s, 59 Meta API calls. [01] Private EN↔VI text interpretation backend (PR #3, draft). Internal session-registry snapshot. |
| 1 Nov 2026 | [01] Entrance v4 with fixes by Muse Wonder through Muse Code (PR #4, draft). |
| 2 Nov 2026 | [06] Two 16-second explainer films (fifth, beats) by Muse Wonder Full. [01] Personal cabinet 1.4 and 1.5 by Muse Wonder Full (the 1.3 run hung and was stopped). [03] Glasses: shadow detector and Llama 3.2 Vision judge closed; DINOv2 adopted. [02] Owner pauses further work on the team's own harness. |
| 3 Nov 2026 | [01] Cabinet and lesson harness with MMS-TTS EN/VI wired (PR #5, draft); first real voice run ends PARTIAL. [03] Glasses app with three pages; live council run from the app in 206 s. [01] A Muse Code run for Portal 2.0 changes nothing; Portal 2.0 ported by DW1 (Claude). |
| 4 Nov 2026 | [07] Disclosure policy, reviewer map and disclosure check (PR #6, draft, opened 03:34 ICT). [01] Live lesson branch (PR #7, draft): neural MMS-TTS EN/VI on an isolated private worker; production health reports `tts=true`. [03] Sci Sound Labs section published (PR #8 and #9, merged into the PR #7 branch, not into `main`). |
| 5 Nov 2026, before 09:00 ICT | [06] Rough cut of the final video (2:36), a draft awaiting owner review; no public link. [01] Desk-robot metronome fallback started; no result. |
| 4 Nov 2026, 21:00 ET (5 Nov, 09:00 ICT) | Submission |

## Evidence
| Item | Status | Evidence |
|---|---|---|
| Pre-event vs event boundary | Working | `docs/HACKATHON_CONTRIBUTIONS.md` |
| Source timestamp evidence on every push to `main` | Working | `docs/SOURCE_PROVENANCE.md`, `evidence-*` releases (latest release `evidence-fc6cc6c434af`, 5 Nov 2026, after the live site was merged into `main`), [ADR 0003](../decisions/0003-timestamp-hashes-not-source.md) |
| Outbound disclosure policy and automated check | Offline-tested | `docs/DISCLOSURE_POLICY.md`, `scripts/disclosure_check.py`, `tests/test_disclosure_check.py` (draft PR #6, not yet on `main`) |
| Report on Meta model participation, from the journal registry | Prototype | [08 Who did the work](08-who-did-the-work.md): call sign → underlying model map and the deliverables of Meta Muse models, built on 5 Nov 2026 from harness configurations and local session indexes. Journal entries in [docs/journal/](../journal/) are not written yet. The team's internal session registry stops at 31 Oct and its headline count does not match its own table, so no session total from it is published. |
| Corrections and retracted claims | Prototype | Dated list in the section "Corrections and retracted claims" below, and dead ends in [09 Paths that did not work](09-dead-ends.md). |

## Mandatory scope at submission
The project owner set three items as mandatory for the submission (25 Oct 2026). They are claimed only at the status verified on submission day (`docs/DISCLOSURE_POLICY.md` §5).

| Item | Status | What is true on 5 Nov 2026 | Evidence |
|---|---|---|---|
| Muse voice replies to both lesson participants (EN↔VI) | Prototype | Server-side neural speech with Meta MMS-TTS (`facebook/mms-tts-eng`, `facebook/mms-tts-vie`) runs on an isolated private CPU worker; the health endpoint reports `tts=true` and `asr=true`, `production_ready=false`. Not done: owner acceptance of voice quality, a human two-person EN↔VI test on physical devices, and the latency target (≤ 5 s at P95; measured by the integrator on 4 Nov: speech recognition 13–14 s, translation and review 24–31 s, cold speech synthesis about 19 s). MMS-TTS is licensed CC-BY-NC 4.0; it is used as a technical pilot. | <https://soulsofmuse.app/api/harness/health>, PR #7 (draft) |
| App on a real watch (Galaxy Watch 6 Classic) | Not done | No watch app exists in any branch. Health reports `watches=false` and lists watches as not implemented. | <https://soulsofmuse.app/api/harness/health> |
| Physical tactile metronome | Not done | The watch path was not built. A fallback on a small desk robot (a head nod per beat) started execution on 5 Nov early morning; no result yet. | none |

## Corrections and retracted claims
Each entry: date found, what was said, what is true.

1. **27 Oct.** Bench reporting presented an estimated speech latency like a measured voice round trip. Corrected: it is labelled "estimated", and an empty speech corpus now blocks the run (`docs/HACKATHON_CONTRIBUTIONS.md`).
2. **30 Oct.** The first Welcome portal passed its frontend tests and deployed, and was presented as delivered. The owner rejected it on structure and visual quality. Rule since then: technical verification is not design acceptance ([PR #2](https://github.com/cybersheik/souls-of-muse/pull/2)).
3. **31 Oct, 00:20 ICT.** The six-variant sound pilot was first described as a bi-level experiment. The independent reviewer reclassified it as "engineering feasibility pass; bi-level experiment not yet run": outcomes were pre-assigned, there was no baseline and no measured improvement.
4. **31 Oct.** The first 24-window nature run was stopped during its seventh window (empty model responses, an evaluator flag that had no effect). Its results are excluded from every count; the campaign was rerun from zero.
5. **3 Nov.** A 77-minute Muse Code run meant to port Portal 2.0 into code changed no files. Portal 2.0 was ported by DW1 (Claude) and is not credited to Muse.
6. **4 Nov.** The PR #5 description (3 Nov) says MMS-TTS stays off in the cloud (memory 1364 MiB against a 512 MiB limit, licence unresolved). Superseded: speech now runs on a separate private worker with more memory and the health endpoint reports `tts=true`. The licence question and owner acceptance remain open.
7. **5 Nov.** The `README.md` "Preview" link points to a domain that no longer resolves. The live site is <https://soulsofmuse.app/>.
8. **5 Nov.** Production provenance. Until 5 Nov the live site served content from draft pull requests that were not in `main`. On 5 Nov it was merged into `main` (pull request #10, `fc6cc6c`); the served frontend now matches `main`, and the merge has its own timestamp evidence release. The health field `source_commit` (`11a3458`) names the backend release commit.
9. **5 Nov.** Mandatory-scope wording. "Real watches" in the owner's mandatory scope means an app on a Galaxy Watch 6 Classic. An internal progress page, and the first draft of `docs/DISCLOSURE_POLICY.md` §5, rendered it as "real lesson hours in agent journals". Status of the watch app: Not done. No completed lesson hours are claimed either: none are documented.

## Who did the work
Call signs are paired with the model behind them on first mention. Full map: [08](08-who-did-the-work.md).

| Work in this workstream | Done by | Model behind it |
|---|---|---|
| Requirements, mandatory scope, decisions, acceptance | Project owner | Human |
| Timestamp evidence workflow and manifest | Planned and reviewed by Muse models through Meta's Muse Code (Muse Spark reviewed the timestamp design); integrated by CX1 | Muse Wonder, Muse Spark (Meta); Codex (OpenAI) for integration. Exact split of authorship: medium confidence |
| Disclosure policy, workstream page skeletons, disclosure check, reviewer map | DC1 | Claude Code (Anthropic) |
| Internal session registry and its collector | DW1 | Claude in the Cowork app (Anthropic) |
| Review of the registry count | GB1 | Grok-based bot (xAI) |
| Independent check of production on 4 Nov | DZ1 | ZCode on GLM (Z.ai) |
| Acceptance tests and fact checks of Muse output (service, sound research, films) | CX1 | Codex (OpenAI) |
| Bi-Level method design (consultation) | CX1 | Codex (OpenAI) |
| Bi-Level research execution (both loops) | Muse Wonder through the direct Meta API; runner and controller written in Hermes Agent, profile "Jack" | Muse Wonder (`muse-wonder-1.0`, Meta) |
| Attribution map, dead-end list and provenance checks for these pages | DC1 and its verifier subagents | Claude Code (Anthropic) |

No Meta model wrote the disclosure tooling or the registry. Meta models contributed to this workstream through the timestamp workflow and as the subjects of the attribution records.

## Paths that did not work
Full list across workstreams: [09](09-dead-ends.md).

- **Timestamp evidence stopped covering new work after 29 Oct.** The workflow stamps pushes to `main` only. From 30 Oct all work went to stacked draft pull requests (#2–#7), so it has GitHub commit times but no evidence release. Not replaced: unless the stack is merged to `main` before submission (owner decision), this gap stands as stated here.
- **The internal session registry was not finished.** Its last snapshot is 31 Oct, its headline count does not match its table, and one agent's journal was not found. Replacement: the attribution map in page 08, built directly from harness configurations and session indexes, without a session total.
- **Plan to replace call signs by neutral roles everywhere.** Scrubbing call signs would have hidden which model did the work, because a call sign or third-party harness often ran a Muse model. The owner decided on 5 Nov to keep call signs and pair each with its model.
- **A third-party progress dashboard as the reconciliation source.** An auto-generated dashboard (built by Kimi) was used to reconcile status. By 5 Nov it was two days stale, missed the newest tasks and misread one mandatory-scope item. Replaced by direct checks against the tracker, the repository and live endpoints.
- **Disclosure check without the private denylist.** Run without the private denylist (as in CI), the check reported zero internal-name hits because no internal names were loaded to look for. Pages 07–09 were therefore checked by hand and, on 5 Nov, again locally with the denylist loaded.

## Not claimed
A timestamp proves the existence of particular bytes, not authorship or copyright. AI-generated implementation is labelled as such (`README.md`, `NOTICE.md`).

- Timestamp evidence covers `main` only. Work from 30 Oct to 4 Nov entered `main` on 5 Nov in one merge (`fc6cc6c`); its evidence release dates that merge, not the individual earlier days.
- The Bitcoin attestations in the evidence releases have not been verified on an independent full node (`docs/SOURCE_PROVENANCE.md`).
- The live service reports `production_ready=false`: it is a pilot.
- No count of agent sessions and no count of completed lesson hours is claimed.
- Tracker assignment is not authorship; see [08](08-who-did-the-work.md).
- Statuses on this page are as of 5 Nov 2026, about 03:30 ICT.
