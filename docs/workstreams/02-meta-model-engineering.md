# 02. Engineering on Meta models

## Why it matters
A music lesson mediated by AI fails if terminology is wrong, latency is unbounded or costs run away. This workstream builds the guardrails and test benches that let Meta models be used safely in a live product, and records how the team actually worked with Meta models: which harness ran which model, what each model did, and where it failed.

## Before the event
An initial Python test bench existed and was reviewed at the start of the event (`docs/HACKATHON_CONTRIBUTIONS.md`). The third-party agent harnesses used during the event (Hermes Agent, OpenCode) and Meta's own Muse Code CLI are external products and are not claimed as project work. Two of the team's own desktop applications existed before the event and were rebuilt for Meta during it. **MetaMezonin (Mezzanine)** was an earlier Hermes-based desktop application; during the event it was rebuilt onto Meta Muse and became the **rehearsal room for members of the Convention**. **TopDog Colors** was an earlier studio of a different design; during the event it was rebuilt as a **music-video studio for musicians**. Only the rebuild onto Meta models and the new work are claimed as event work; a baseline file describing the pre-event state of both is not yet published. `README.md` credits Kimi (a third-party agent, not a Meta model) with preparing the initial harness bench, which the team reviewed and reworked at the start of the event.

## During the event
Times are UTC+7.

| Item | Status | Evidence |
|---|---|---|
| Model role map: interpreter, reviewer, transcription, vision | Designed | `harness-bench/config/models.yaml` |
| Musical terminology validator and seed glossary (EN/VI) | Offline-tested | `harness-bench/harness/validator.py`, `harness-bench/data/` |
| Pre-request atomic budget reservation | Offline-tested | [ADR 0001](../decisions/0001-reserve-model-budget-before-each-paid-call.md), `harness-bench/tests/`. Implemented by Muse Wonder and reviewed by Muse Spark (27 Oct 2026), integrated by Codex (OpenAI) |
| Honest probe reporting: estimated latency is never reported as measured | Offline-tested | `harness-bench/tests/test_probe_reporting.py` |
| Rehearsal room for Convention members (MetaMezonin, rebuilt from the earlier Hermes-based desktop application onto Meta Muse) | Installed local application. Public availability: no public installer is linked | Installed application with tools loaded on demand (internal test: tool-schema bytes fell by 94–99%), persistent memory and retrieval, source-linked history, and a Muse Image (`muse-image-1.0`) route that returns generated images to Muse Wonder (`muse-wonder-1.0`, through the Meta API) for further work. Recovery scenarios and both source-level and packaged-application checks were recorded. A native UI over Meta's own Muse Code runtime works through the official Muse Code SDK (live handshake and a real Muse turn passed). The Hermes backend was removed from the Meta build. Its resident Muse assistant contributed an earlier screenplay revision and substantive review to the film Ganesha (workstream 06). Future work: 3D avatars, movement analysis and home-practice extensions. A limit of 8 tool rounds per turn remains |
| Music-video studio for musicians (TopDog Colors, rebuilt from the earlier studio) | Implemented (local). Public availability: source is not published | Interface UI 002, implemented under the project owner's direction by Codex (OpenAI): episode navigation and player, timeline with second ranges, edit notes, change branches, three working slots and a reference library checked with 82 images in 6 branches. 38 project checks and a TypeScript check passed on 5 Nov 2026. Agent execution is deliberately disabled in this interface-editing build. Separately, the restored studio completed real Muse Wonder Full (`muse-wonder-full-1.0`) turns through the official subscription workflow (Meta's Muse Code SDK bridge), on 2 and 3 Nov 2026 including Ganesha screenplay and storyboard work (workstream 06). The earlier SDK client integration was written by ZCode (GLM, not a Meta model). The public live-action film shows the real studio window. Video frames in the film work came from a third-party platform (Krea) and are credited there, not to Meta |

## Harnesses, tools and the model behind each
Every task in the team's tracker is formally assigned to the project owner. Much of the work was done by Meta Muse models running inside Meta's own CLI, the team's applications or a third-party harness, with other AI tools integrating and checking. This table names each tool or harness and the model behind it. Counts come from the local session records of the development workstation, counted on 5 Nov 2026.

| Tool or harness | What it is | Model actually behind it | Main use during the event |
|---|---|---|---|
| Muse Code CLI | Meta's terminal coding agent (subscription), launched and supervised by Codex (OpenAI) and Claude (Anthropic) | muse-wonder-1.0 in 175 sessions and muse-wonder-full-1.0 in 25 sessions since 26 Oct | Most of the Muse-authored code and media: admission control, budget and hosting code, EN-VI backend, Entrance v4, cabinet 1.3-1.5, sound renderer and films; Ganesha direction and score work (workstream 06) |
| A Hermes Agent profile | A profile of Hermes Agent (third-party agent harness) | muse-wonder-1.0 through the direct Meta API; its reviewer and code-review sub-agents used Muse Wonder routed through Nous Portal; auxiliary slots muse-wonder and muse-spark-1.3; one fallback call in one early sound-pilot session went to a non-Meta model (Grok) | First portal (PR #2), runner and controller code for the sound research, the "muse-council" mixture of three Muse models (workstream 03). 12 project sessions, 29 Oct - 3 Nov |
| muse-council | A mixture-of-agents preset inside that Hermes Agent profile | References muse-wonder-1.0, muse-spark-1.3, muse-spark-1.2; aggregator muse-wonder-1.0 | Museon contract council on the glasses line (workstream 03) |
| OpenCode | Third-party agent harness | muse-wonder-1.0 in its sessions of 2 and 4 Nov (its default configured model is not a Meta model; the hackathon sessions selected Muse explicitly). A muse-wonder-full-1.0 probe returned no output | Audit of the social video approvals (4 Nov) |
| MetaMezonin's resident agent | The resident agent of MetaMezonin, the team's own desktop application | muse-wonder-1.0 for reasoning, muse-image-1.0 for images | Harness checks; an earlier Ganesha screenplay revision and review, with three image generations; one Muse Image proof generation (29 Oct) |
| TopDog Colors studio client | The studio's client on Meta's official Muse Code SDK bridge (subscription workflow) | muse-wonder-full-1.0 | Five sessions, 2-3 Nov, including Ganesha screenplay and storyboard work |
| Meta AI (meta.ai) | Meta's consumer web assistant | Model not shown by the interface | Two sessions: week-1 post captions and invitations (workstream 05) |
| Codex (OpenAI) | Not a Meta model | Codex | Integrator, QA and fact-checker for most Muse runs; some integration code (e.g. the final path regression in PR #1); TopDog Colors interface UI 002; film editing, score performance and mixing |
| Claude (Anthropic) in Cowork | Not a Meta model | Claude | Launched several Muse Wonder Full runs; design coordination with Claude Design; ported Portal 2.0/2.1 |
| Claude Code (Anthropic) | Not a Meta model | Claude | Code of the three glasses services (workstream 03); disclosure review |
| ZCode (GLM) | Not a Meta model | GLM | Model map of the Meta Model API, the earlier studio SDK client, depth-sensing and desk-robot plans |
| Other agents | Agent labels whose model was not recorded | Model not recorded | Voice research (workstream 01); formatting of the final-film script. None of their work is credited to Muse |
| Kimi | Third-party agent and model, not Meta | Kimi | First harness bench, the event-journal ("heart") component, a rejected lesson runtime, the starting "Sound Made Visible" demo |

## How Meta models were used
Built from the session records and public pull requests; the sanitized per-session journal in `docs/journal/` is not yet filled.

**Muse Wonder (muse-wonder-1.0)**
- Role: main implementation model; lesson-plan proposer in the service; both research roles in the sound study (workstream 03); aggregator of the muse-council mixture; director and composer of the film Ganesha (workstream 06).
- Tasks: admission control with an operator-selected capacity (PR #1; five slots and twelve contenders are a concurrency test fixture, not a product limit), budget guard and hosting implementation, cloud plans (27-29 Oct), private EN-VI backend (PR #3), first portal (PR #2), Entrance v4 (PR #4), fixes of four frontend regressions (1 Nov), runner and controller code for the sound research; Ganesha direction, shot and revision review, the director's report and the score (six melodic cells, harmony, percussion patterns and orchestration, kept as score data and editable MIDI).
- How the output was checked: independent review by Muse Spark for admission, budget, cloud, deploy and timestamp work; integration, tests and acceptance by Codex (OpenAI); design acceptance by the project owner.
- Unexpected and limits: with short output limits the model spent its budget on reasoning and returned empty answers (298 of 300 tokens on reasoning; in the sound run, 4094 of 4096), so empty or incomplete answers were turned into explicit errors and reasoning effort was set low with larger caps; one generated plan put a title into a duration field; the first portal it wrote passed all tests but was rejected on design.

**Muse Wonder Full (muse-wonder-full-1.0)**
- Role: long implementation and media runs; screenplay and storyboard.
- Tasks: personal cabinet 1.3-1.5 (2 Nov), the audio adapters, renderer, two 16-second films and the retrospective of the sound research (31 Oct - 2 Nov), Ganesha screenplay and storyboard work through the subscription route (workstream 06), one product brainstorm (2 Nov).
- How checked: tests and review by Codex (OpenAI); film design approved by Claude (Anthropic) with Claude Design.
- Unexpected and limits: reachable only inside the Muse Code subscription. Manually created API keys returned 404, and the subscription key used outside the Muse Code host returned 403; an OpenCode probe returned nothing. The only legitimate route from the team's own interface was Meta's official Muse Code SDK bridge, which is why the studio's SDK client exists. One 77-minute run (Portal 2.0, 3 Nov) changed no files; one cabinet run hung on starting an HTTP server.

**Muse Spark (muse-spark-1.3, also 1.2 in the council)**
- Role: interpreter and translation reviewer in the service; independent code reviewer; reader of document and chord-chart images on the glasses line.
- Tasks: reviews of admission, budget, cloud, timestamp workflow and deploy work (27-29 Oct); EN↔VI interpretation and review in the lesson.
- Unexpected and limits: as a judge of guitar finger posture from the glasses view it answered "curled" for both a correct and a collapsed hand, and returned empty answers unless reasoning effort was low (workstream 03).

**Muse Image (muse-image-1.0)**
- Created the teacher reference and the production reference imagery for the film Ganesha (workstream 06). Earlier, one proof generation (29 Oct) and three image generations during a Ganesha screenplay review ran through MetaMezonin, whose Muse Image route returns images to Muse Wonder. The planned Portal 2.0 image set is a separate scope and was not delivered.

**Voice Transcribe, SAM 3.1, MMS-TTS**
- Voice Transcribe is the lesson ASR (workstream 01) and probe P3 of the bench. SAM 3.1 has a mask-contract probe in `harness-bench/probes/p4_sam.py` and is the vision core of the glasses line (workstream 03). MMS-TTS (open weights) speaks approved translations (workstream 01).

**Generation/review pairs**
- Muse Wonder generates, Muse Spark reviews independently, a non-Meta integrator (Codex, OpenAI) runs the tests: admission control (PR #1, 54 offline tests), budget guard, cloud and deploy plans.
- In the lesson: Muse Spark interprets, a deterministic validator and a second Muse Spark pass review the terminology, and the human Maestro approves before delivery.
- In the council: three Muse models answer independently and Muse Wonder aggregates.

## Paths that did not work
- **Muse Wonder Full from own code by API key**: 404 with manual keys, 403 with the subscription key outside the Muse Code host, empty output through OpenCode. Replaced by the official SDK bridge.
- **Short output limits on reasoning models**: answers came back empty because reasoning used the whole budget. Fixed by explicit errors, low reasoning effort and larger caps.
- **Long unattended Muse Code runs**: a 77-minute run with no changes (Portal 2.0, ported by Claude, Anthropic, instead), a cabinet run hung on an HTTP server (stopped; later cabinet runs completed), a run stopped at its 8-step maximum (redone by Muse Code). The failed runs themselves are not credited to Muse.
- **Muse Wonder Full through the studio's SDK client during Ganesha (3 Nov)**: a Meta HTTP 504; the integrator (Codex, OpenAI) then switched the clip work to a third-party video agent without the owner's approval, and that first cut was rejected by the owner as off-script. The redo kept Muse Wonder as director (workstream 06).
- **MetaMezonin expansion (2 Nov)**: an expansion phase was paused by the project owner on 2 Nov; the 8-rounds-per-turn limit and its proposed fix were not implemented.
- **Meta-only video generation**: the Meta Model API has no video endpoint (chat, responses, images, audio and segmentation only), and the consumer Muse app with video was waitlisted in the owner's region on 27 Oct. Video shots moved to a third-party platform (Krea) with Muse Wonder as director (workstream 06).
- **A Meta Model API voice loop**: there is no text-to-speech endpoint; open MMS-TTS weights were used instead (workstream 01).

## Not claimed
- The paid transcription route is disabled until its usage contract is verified. SAM and TTS are not implemented in the budget-safe adapter; the lesson's MMS-TTS voice runs in a separate worker outside it.
- The budget guard bounds only calls routed through its ledger on one machine.
- No public installer for MetaMezonin and no public source for TopDog Colors are linked here; public availability is a separate field from their implemented local state. Agent execution is disabled in TopDog Colors' interface-editing build. The pre-event versions (the Hermes-based desktop application, the earlier studio) are not claimed as event work.
- Session counts per harness come from local records and are not independently auditable. They are not a measure of quality.
- Work by Codex, Claude, Claude Design, ZCode/GLM, MiniMax, Kimi, Nous Portal routing and Krea is named as such and is not credited to Meta models.
