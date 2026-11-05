# 02. Engineering on Meta models

## Why it matters
A music lesson mediated by AI fails if terminology is wrong, latency is unbounded or costs run away. This workstream builds the guardrails and test benches that let Meta models be used safely in a live product, and records how the team actually worked with Meta models: which harness ran which model, what each model did, and where it failed.

## Before the event
An initial Python test bench existed and was reviewed at the start of the event (`docs/HACKATHON_CONTRIBUTIONS.md`). The third-party agent harnesses used during the event (Hermes Agent, OpenCode) and Meta's own Muse Code CLI are external products and are not claimed as project work. Two of the team's own desktop applications existed before the event and were rebuilt for Meta during it. **MetaMezonin (Mezzanine)** was a conserved desktop UI built earlier for the Hermes agent stack; during the event it was moved onto Meta Muse and became the **rehearsal room for members of the Convention**. **TopDog Colors** was an earlier media-review tool of a different design; during the event it was rebuilt as a **clip studio where musicians write and produce clips with Muse**. Only the rebuild onto Meta models is claimed as event work; a BASELINE.md describing the pre-event state of both is still to be filed. `README.md` credits Kimi (a third-party agent, not a Meta model) with preparing the initial harness bench, which the team reviewed and reworked at the start of the event.

## During the event
Times are UTC+7.

| Item | Status | Evidence |
|---|---|---|
| Model role map: interpreter, reviewer, transcription, vision | Designed | `harness-bench/config/models.yaml` |
| Musical terminology validator and seed glossary (EN/VI) | Offline-tested | `harness-bench/harness/validator.py`, `harness-bench/data/` |
| Pre-request atomic budget reservation | Offline-tested | [ADR 0001](../decisions/0001-reserve-model-budget-before-each-paid-call.md), `harness-bench/tests/`. Implemented by Muse Wonder and reviewed by Muse Spark (27 Oct 2026), integrated by CX1 (Codex) |
| Honest probe reporting: estimated latency is never reported as measured | Offline-tested | `harness-bench/tests/test_probe_reporting.py` |
| Rehearsal room for Convention members (MetaMezonin, rebuilt from a conserved Hermes-based UI onto Meta) | Prototype by internal record (runs locally); no public evidence yet, so not claimed for judging until a source, screen video or BASELINE.md is published | Not public. Rebuild during the event: the resident agent runs on Muse Wonder (`muse-wonder-1.0`) through the Meta API, generates images with Muse Image (`muse-image-1.0`) and loads tool schemas on demand (internal test: tool-schema bytes fell by 94–99%); a native UI over Meta's own Muse Code runtime through the official Muse Code SDK (live handshake and a real Muse turn passed). The Hermes backend was removed from the Meta build. Planned next: a 3D Muse, cameras as Muse's "eyes" with SAM, and music explained through geometry (proposal of 3 Nov; not built). A limit of 8 tool rounds per turn remains |
| Clip studio for musicians (TopDog Colors Muse, rebuilt from the earlier TopDog Colors) | Prototype by internal record; no public evidence yet, so not claimed for judging | Not public. A desktop studio that reaches Muse Wonder Full (`muse-wonder-full-1.0`) only through Meta's official Muse Code SDK bridge; real Muse Wonder Full turns confirmed on 2 and 3 Nov 2026, including five sessions directing the promo film (workstream 06). The client code was written by DZ1 (ZCode on GLM, not a Meta model). Video frames in that work came from a third-party platform (Krea) and are credited there, not to Meta |

## Harnesses, callsigns and the model behind each
Every task in the team's tracker is formally assigned to the project owner. Much of the work was done by Meta Muse models running behind a callsign or inside a third-party harness. This table resolves each label used in the project. Counts come from the local session records of the development workstation, counted on 5 Nov 2026.

| Label (callsign or harness) | What it is | Model actually behind it | Main use during the event |
|---|---|---|---|
| Muse Code CLI | Meta's terminal coding agent (subscription), launched and supervised by CX1 (Codex) and DW1 (Claude) | muse-wonder-1.0 in 175 sessions and muse-wonder-full-1.0 in 25 sessions since 26 Oct | Most of the Muse-authored code and media: admission control, budget and hosting code, EN-VI backend, Entrance v4, cabinet 1.3-1.5, sound renderer and films |
| Jack | A profile of Hermes Agent (third-party agent harness) | muse-wonder-1.0 through the direct Meta API; its reviewer and code-review sub-agents used Muse Wonder routed through Nous Portal; auxiliary slots muse-wonder and muse-spark-1.3; one fallback call in one early sound-pilot session went to a non-Meta model (Grok) | First portal (PR #2), runner and controller code for the sound research, the "muse-council" mixture of three Muse models (workstream 03). 12 project sessions, 29 Oct - 3 Nov |
| muse-council | A mixture-of-agents preset inside Jack | References muse-wonder-1.0, muse-spark-1.3, muse-spark-1.2; aggregator muse-wonder-1.0 | Contract review on the glasses line (workstream 03) |
| OC1 | OpenCode (third-party agent harness) | muse-wonder-1.0 in its sessions of 2 and 4 Nov (its default configured model is not a Meta model; the hackathon sessions selected Muse explicitly). A muse-wonder-full-1.0 probe returned no output | Audit of the social video approvals (4 Nov) |
| MZM | The resident agent of MetaMezonin, the team's own desktop harness | muse-wonder-1.0 for reasoning, muse-image-1.0 for images | Harness checks; review of promo scenario v3 with three image generations; one Muse Image proof generation (29 Oct) |
| Muse Wonder Full SDK client | The team's desktop client on Meta's Muse Code SDK bridge | muse-wonder-full-1.0 | Five sessions, 2-3 Nov, including promo-film direction |
| Meta AI (meta.ai) | Meta's consumer web assistant | Model not shown by the interface | Two sessions: week-1 post captions and invitations (workstream 05) |
| CX1 | Codex (OpenAI), not a Meta model | Codex | Director, integrator, QA and fact-checker for most Muse runs; some integration code (e.g. the final path regression in PR #1) |
| DW1 | Claude (Anthropic) in Cowork, not a Meta model | Claude | Launched several Muse Wonder Full runs; design coordination with Claude Design; ported Portal 2.0/2.1 |
| DC1 | Claude Code (Anthropic), not a Meta model | Claude | Code of the glasses stand (workstream 03); disclosure review |
| DZ1 | ZCode on GLM, not a Meta model | GLM | Model map of the Meta Model API, the SDK client, depth-sensing and desk-robot plans |
| MS1 | Research agent | Model not confirmed | Voice research (workstream 01) |
| OS-1 | Agent label used by the project owner | Model not confirmed: the records swept for 26 Oct - 5 Nov do not define OS-1 (the owner reports that a Muse model ran behind it) | No work is attributed to OS-1 on these pages until its records are found |
| MC1 | Agent label | Model not confirmed | Formatted the final-video script; it did not render media and was not used to confirm the research loop |
| MUW1 | Agent label | Model not confirmed (its session journal was not found) | Not credited to Muse |
| Kimi | Third-party agent and model, not Meta | Kimi | First harness bench, the event-journal ("heart") component, a rejected lesson runtime, the starting "Sound Made Visible" demo |

## How Meta models were used
Built from the session records and public pull requests; the sanitized per-session journal in `docs/journal/` is not yet filled.

**Muse Wonder (muse-wonder-1.0)**
- Role: main implementation model; lesson-plan proposer in the service; both research roles in the sound study (workstream 03); aggregator of the muse-council mixture.
- Tasks: five-lesson admission control (PR #1), budget guard and hosting implementation, cloud plans (27-29 Oct), private EN-VI backend (PR #3), first portal (PR #2), Entrance v4 (PR #4), fixes of four frontend regressions (1 Nov), runner and controller code for the sound research.
- How the output was checked: independent review by Muse Spark for admission, budget, cloud, deploy and timestamp work; integration, tests and acceptance by CX1 (Codex); design acceptance by the project owner.
- Unexpected and limits: with short output limits the model spent its budget on reasoning and returned empty answers (298 of 300 tokens on reasoning; in the sound run, 4094 of 4096), so empty or incomplete answers were turned into explicit errors and reasoning effort was set low with larger caps; one generated plan put a title into a duration field; the first portal it wrote passed all tests but was rejected on design.

**Muse Wonder Full (muse-wonder-full-1.0)**
- Role: long implementation and media runs.
- Tasks: personal cabinet 1.3-1.5 (2 Nov), the audio adapters, renderer, two 16-second films and the retrospective of the sound research (31 Oct - 2 Nov), direction of the promo film (workstream 06), one product brainstorm (2 Nov).
- How checked: tests and review by CX1 (Codex); film design approved by DW1 (Claude) with Claude Design.
- Unexpected and limits: reachable only inside the Muse Code subscription. Manually created API keys returned 404, and the subscription key used outside the Muse Code host returned 403; an OpenCode probe returned nothing. The only legitimate route from the team's own interface was Meta's official Muse Code SDK bridge, which is why the SDK client exists. One 77-minute run (Portal 2.0, 3 Nov) changed no files; one cabinet run hung on starting an HTTP server.

**Muse Spark (muse-spark-1.3, also 1.2 in the council)**
- Role: interpreter and translation reviewer in the service; independent code reviewer; reader of document and chord-chart photos on the glasses line.
- Tasks: reviews of admission, budget, cloud, timestamp workflow and deploy work (27-29 Oct); EN↔VI interpretation and review in the lesson.
- Unexpected and limits: as a judge of guitar finger posture from the glasses view it answered "curled" for both a correct and a collapsed hand, and returned empty answers unless reasoning effort was low (workstream 03).

**Muse Image (muse-image-1.0)**
- One proof generation (29 Oct) and three image-generation calls during the promo scenario review, all through MetaMezonin; the records name muse-image-1.0 for two of them. None of these images is public. The planned Portal 2.0 image set was never run and is not claimed.

**Voice Transcribe, SAM 3.1, MMS-TTS**
- Voice Transcribe is the lesson ASR (workstream 01) and probe P3 of the bench. SAM 3.1 has a mask-contract probe in `harness-bench/probes/p4_sam.py` and is the vision core of the glasses line (workstream 03). MMS-TTS (open weights) speaks approved translations (workstream 01).

**Generation/review pairs**
- Muse Wonder generates, Muse Spark reviews independently, a non-Meta integrator (CX1, Codex) runs the tests: admission control (PR #1, 54 offline tests), budget guard, cloud and deploy plans.
- In the lesson: Muse Spark interprets, a deterministic validator and a second Muse Spark pass review the terminology, and the human Maestro approves before delivery.
- In the council: three Muse models answer independently and Muse Wonder aggregates.

## Paths that did not work
- **Muse Wonder Full from own code by API key**: 404 with manual keys, 403 with the subscription key outside the Muse Code host, empty output through OpenCode. Replaced by the official SDK bridge.
- **Short output limits on reasoning models**: answers came back empty because reasoning used the whole budget. Fixed by explicit errors, low reasoning effort and larger caps.
- **Long unattended Muse Code runs**: a 77-minute run with no changes (Portal 2.0, ported by DW1, Claude, instead), a cabinet run hung on an HTTP server (stopped; later cabinet runs completed), a run stopped at its 8-step maximum (redone by Muse Code). The failed runs themselves are not credited to Muse.
- **Muse Wonder Full through the SDK client during the promo film (3 Nov)**: a Meta HTTP 504; the integrator CX1 (Codex) then switched the clip work to a third-party video agent without the owner's approval, and that first cut was rejected by the owner as off-script. The redo kept Muse Wonder as director (workstream 06).
- **MetaMezonin expansion**: stopped by the project owner on 2 Nov; the 8-rounds-per-turn limit and its proposed fix were not implemented.
- **Meta-only video generation**: the Meta Model API has no video endpoint (chat, responses, images, audio and segmentation only), and the consumer Muse app with video was waitlisted in the owner's region on 27 Oct. Video work moved to a third-party platform with Muse Wonder as director (workstream 06).
- **A Meta Model API voice loop**: there is no text-to-speech endpoint; open MMS-TTS weights were used instead (workstream 01).

## Not claimed
- The paid transcription route is disabled until its usage contract is verified. SAM and TTS are not implemented in the budget-safe adapter; the lesson's MMS-TTS voice runs in a separate worker outside it.
- The budget guard bounds only calls routed through its ledger on one machine.
- The rehearsal room (MetaMezonin) and the clip studio (TopDog Colors Muse) have no public source, video or baseline here yet; their internal test counts are not offered as evidence. Their pre-event versions (Hermes-based UI, earlier TopDog Colors) are not claimed as event work.
- Session counts per harness come from local records and are not independently auditable. They are not a measure of quality.
- Work by Codex, Claude, Claude Design, ZCode/GLM, MiniMax, Kimi, Nous Portal routing and Krea is named as such and is not credited to Meta models.
```
