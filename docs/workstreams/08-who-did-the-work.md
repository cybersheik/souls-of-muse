# 08. Who did the work: tools and the Meta models behind them

## Why this page exists
Every task in the team's internal tracker is formally assigned to the project owner, who sets requirements, decides and accepts results. Tracker assignment therefore does not show who did the work.

The work itself was done with AI tools and agent harnesses. A harness name often hides the model behind it: Hermes Agent, OpenCode, MetaMezonin and TopDog Colors were in many sessions running a Meta Muse model. This page pairs each public tool or harness with the model actually behind it, lists the deliverables of Meta models separately, and credits other tools honestly so that Meta models are not over-credited.

Sources: harness configurations on the development workstation, public pull request descriptions, production records and the team's tracker, all read on 5 Nov 2026. Work by agents whose model could not be confirmed is not listed here and is not credited to Meta.

## Tools and the models behind them

| Tool or harness | What it is | Model(s) behind it | What it delivered |
|---|---|---|---|
| Project owner | Human | — | Requirements, architecture, mandatory scope, go/no-go gates and every acceptance decision. Every tracker task is formally assigned to the owner; that assignment is not authorship |
| Muse Code (Meta) | Meta's own coding agent for the terminal, orchestrated by Codex and Claude | Muse Wonder (`muse-wonder-1.0`) and Muse Wonder Full (`muse-wonder-full-1.0`) | Most Muse code and media work: admission control, cloud and budget work, Entrance v4, personal cabinet, site fixes, sound adapters and renderer, research films, explainer films, and Ganesha screenplay, direction, review and score work |
| Hermes Agent | An open agent harness from Nous Research; on this project a profile running Muse Wonder through the Meta API | Muse Wonder (`muse-wonder-1.0`) through the direct Meta API by default; reviewer subagents used Muse Wonder routed through Nous Portal; auxiliary slots Muse Wonder and Muse Spark 1.3. One fallback call in one early sound-portrait session went to Grok (xAI), so that session is not 100% Muse | First Welcome portal code; the runner and controller code of the Bi-Level sound research and the repairs of its stopped run; the 15-second note-aware C-major scale; contract reviews through the muse-council preset |
| muse-council | A mixture-of-agents preset inside the Hermes Agent profile | Muse Wonder (aggregator), Muse Spark 1.3 and Muse Spark 1.2 answer in parallel; Muse Wonder aggregates | Clause-by-clause contract reviews (30 Oct, 3 Nov); the engine of Museon, the Ray-Ban Meta contract council |
| OpenCode | An open-source coding agent, run with Muse Wonder selected | Muse Wonder (`muse-wonder-1.0`) through the Meta API (sessions of 2 and 4 Nov); a Muse Wonder Full probe on 2 Nov returned nothing | An audit of the two explainer films (4 Nov: their design approval was outdated by a later owner colour rule) |
| MetaMezonin | The team's rehearsal room for Convention members, rebuilt during the event from an earlier Hermes-based desktop application onto Meta Muse; its resident agent works in the app | Muse Wonder (`muse-wonder-1.0`) through the Meta API; Muse Image (`muse-image-1.0`) for images | Installed build with on-demand tools, persistent memory and recovery checks; an earlier Ganesha screenplay revision (scenario v3) and substantive review |
| TopDog Colors | The team's music-video studio for musicians | Muse Wonder Full (`muse-wonder-full-1.0`) through the official subscription workflow | The restored studio completed real Muse Wonder Full turns for Ganesha. The current editing interface (UI 002) was implemented with OpenAI Codex under the owner's direction (see below); the earlier Muse Code SDK client was built with ZCode (GLM) |
| Meta AI (meta.ai) | Meta's consumer web assistant, "Reasoning" mode | Meta AI; the interface does not show which model | 12 week-one post captions in English and Russian, invitations in Vietnamese and Hindi (two sessions; a third failed and is excluded) |
| Codex (OpenAI) | Coding agent; not a Meta model | Codex | Integration and verification of most Muse runs; final regression of admission control and a later bug fix; Bi-Level method design and independent acceptance; publication of Sci Sound Labs; TopDog Colors UI 002 (episode navigation and player, timeline with second ranges, edit notes and change branches, three working slots, an 82-image / 6-branch reference library; 38 project checks and TypeScript passed on 5 Nov); video editing, score performance and the Ganesha mix |
| Claude Code (Anthropic) | Coding agent; not a Meta model | Claude | All code of the three Ray-Ban Meta services (with Claude subagents); disclosure policy and check; LiDAR offline analysis; speech fine-tuning assessment; this page |
| Claude (Anthropic) | Assistant in the Cowork app, with Claude Design; not a Meta model | Claude | Lesson screen and portal design work with Claude Design; porting of Portal 2.0 and 2.1 into code; launched several Muse Wonder Full runs; Sci Sound Labs plan; clickable "Glasses 1.0" design prototype |
| ZCode (GLM) | Coding agent on GLM (Z.ai); not a Meta model | GLM | Hackathon application; map of Meta models; coverage model; the earlier Muse Code SDK client for TopDog Colors; LiDAR research and depth receiver; desk-robot metronome plan; independent production check on 4 Nov |
| Grok-based review bots | Review bots (xAI Grok); not a Meta model | Grok | Reviews and drafts of internal summary chapters |
| A MiniMax research agent | Research sub-agent; not a Meta model | MiniMax | Versions 2 and 3 of the research note "Who still plays?" |
| Kimi (Moonshot AI) | Agent; not a Meta model | Kimi | Starting "Sound Made Visible" demo; the harness bench and plan; internal progress tracking; first lesson runtime (rejected as a public backend); the heart component |

### Meta models used as components, not as agents
- **SAM 3.1** (cloud and local weights): keys, fingers and side view in MuseEveryThings, the Ray-Ban Meta keys trainer.
- **DINOv2 small:** "key appearance changed" vote in the keys trainer.
- **Llama 3.2 Vision 11B** (local, 4-bit): tested as a key-press judge and rejected (see [09](09-dead-ends.md)).
- **MMS-TTS** (`facebook/mms-tts-eng`, `facebook/mms-tts-vie`): server-side EN/VI speech in the cloud pilot.
- **Meta speech recognition** through the Meta API: lesson speech input.
- Licences for DINOv3 and SAM 3D Body were accepted on 4 Nov; neither was downloaded or used.

## Deliverables of Meta models
The main results produced by Meta models, in one list. Integration, testing and acceptance were done by the tools named in each item and by the project owner.

- **Ganesha R8, 82 s** (1,968 frames at 24 fps, 13 chapters). Muse Wonder Full wrote the screenplay and storyboard through the subscription route. Muse Wonder directed, reviewed shots and revisions, wrote the director's report and **composed the score**: six melodic cells, harmony, percussion and orchestration, preserved as score data and editable MIDI. Muse Image (`muse-image-1.0`) created the teacher reference and the production reference images used in the film. Video shots: Krea; editing, score performance and mix: Codex and local tools.
- **Sound Made Visible.** Both research loops ran on Muse Wonder in separate contexts: 24 windows of 300 s, 59 completed requests (48 inner, 11 outer), 23 promising synthetic calibrations and 1 inconclusive result; the evaluator stayed frozen. Muse Wonder Full produced the adapters, renderer, research films and publication media.
- **Museon**, the Ray-Ban Meta contract council: Muse Wonder and Muse Spark advisers (muse-council), 18 of 18 planted issues found on the demo contract.
- **MuseAudioNotes**, the Ray-Ban Meta audio notebook: Muse Spark reads chord material.
- **Sol Muse robot:** Muse Responses integration; the project's own prepared model was loaded and the project software installed.
- **Service and engineering through Muse Code:** admission control, cloud and budget work, Entrance v4, the personal cabinet, site fixes and the EN↔VI interpretation backend.
- **Outreach through Meta AI:** week-one captions and invitations.

## Work done by Meta Muse models, by workstream
Status per `docs/DISCLOSURE_POLICY.md` §5. "Integration" names the non-Meta tool that wired, tested or published the Muse output.

### 01 Service and lesson
| Deliverable | Muse model and harness | Integration | Status | Public proof |
|---|---|---|---|---|
| Lesson admission control with an operator-selected capacity (durable SQLite store; five slots appear only as a test fixture) | Generated by Muse Wonder, independently reviewed by Muse Spark, both through Muse Code | Codex (OpenAI) integrated and added the final path regression; 54 offline checks | Offline-tested | [PR #1](https://github.com/cybersheik/souls-of-muse/pull/1) (merged) |
| Private EN↔VI text interpretation backend | Implementation by Muse Wonder through Muse Code | Codex (OpenAI) integration and verification | Offline-tested | [PR #3](https://github.com/cybersheik/souls-of-muse/pull/3) (draft) |
| Lesson runtime: lesson-plan proposals and translation | Muse Wonder prepares lesson-plan proposals; Muse Spark interprets and reviews translations (one real EN→VI step in 9.078 s) | Codex (OpenAI) | Prototype | [PR #5](https://github.com/cybersheik/souls-of-muse/pull/5) (draft) |
| First Welcome portal (convention signature preview, Welcome card, seven Leagues, three role contexts) | Muse Wonder in a Hermes Agent profile, direct Meta API | Codex (OpenAI) integration | Prototype; rejected on design by the owner | [PR #2](https://github.com/cybersheik/souls-of-muse/pull/2) |
| Entrance v4 and its fixes | Muse Wonder through Muse Code | Claude (Anthropic) first run, Codex (OpenAI) integration | Prototype | [PR #4](https://github.com/cybersheik/souls-of-muse/pull/4) (draft) |
| Site candidate fixes, 1 Nov (four frontend regressions, deploy routing, honesty labels) | Muse Wonder through Muse Code | Codex (OpenAI) found the regressions | Prototype | none |
| Personal cabinet 1.4 and 1.5 (Leagues, video demo, tests, 390 px phone layout, League catalogue) | Muse Wonder Full through Muse Code | Claude (Anthropic) combined them into PR #5 | Prototype | [PR #5](https://github.com/cybersheik/souls-of-muse/pull/5) (draft) |
| Proposal to use MMS-TTS for lesson speech (19 Oct, before the event) | Muse Wonder | Codex (OpenAI) wired MMS-TTS into the service | Designed (the proposal); the speech integration built from it is a Prototype, not owner-accepted | <https://soulsofmuse.app/api/harness/health> |
| Sol Muse robot: Muse Responses integration, project software installed, the project's own prepared model loaded | Muse Responses | Firmware build and music modules (moving metronome, melody notebook, rap partner); a four-note synthetic notebook fixture produced C4–E4–G4–C5 | Prototype (acceptance of each physical mode is open; the watch application is not done) | [jury dossier](https://soulsofmuse.app/dossier/) |

### 02 Engineering on Meta models
| Deliverable | Muse model and harness | Integration | Status | Public proof |
|---|---|---|---|---|
| Cloud plan, budget implementation, cloud survey, deploy plans, paid-hosting implementation and tests (27–29 Oct) | Muse Wonder through Muse Code; Muse Spark reviewed budget, cloud, timestamp and deploy work | Codex (OpenAI) integrated; mostly plans and reviews | Offline-tested | none |
| Text-only brainstorm on MetaMezonin and TopDog Colors as Souls of Muse apps (2 Nov) | Muse Wonder Full through Muse Code | — | Designed | none |
| MetaMezonin rehearsal room: on-demand tools, persistent memory and retrieval, Muse Image route back into the conversation | Muse Wonder and Muse Image through the Meta API | Harness code itself is not credited to Muse | Prototype (installed locally; no public installer) | none |
| TopDog Colors restored studio: real Muse Wonder Full turns through the official subscription workflow | Muse Wonder Full | UI 002 by Codex (OpenAI); earlier SDK client by ZCode (GLM); agent execution is disabled in the interface-editing build | Prototype | [live-action film](https://www.youtube.com/shorts/1EAl-cj0DJ4) shows the studio window |

### 03 Research with Muse
| Deliverable | Muse model and harness | Integration | Status | Public proof |
|---|---|---|---|---|
| Bi-Level AutoResearch on "Sound Made Visible": both loop roles (48 inner and 11 outer requests in campaign v2, two separate contexts of the same model) | Muse Wonder (`muse-wonder-1.0`), direct Meta API | Method design, independent acceptance tests, final audit and report by Codex (OpenAI); starting prototype by Kimi | Offline-tested | <https://soulsofmuse.app/sci-sound-labs/jury-report.html> |
| Runner and controller code of the research loop, and the repairs of the stopped first run | Muse Wonder in a Hermes Agent profile | Acceptance by Codex (OpenAI) | Offline-tested | none |
| Audio adapters (beats, harmonic balance, decay), renderer, showcase, research films, Muse retrospective report | Muse Wonder Full (`muse-wonder-full-1.0`) through Muse Code | Codex (OpenAI): 26/26 independent renderer tests, fact check, publication | Offline-tested | <https://soulsofmuse.app/sci-sound-labs/> |
| Museon, Ray-Ban Meta contract council: reading of contract pages (shown on a synthetic page only), clause-by-clause review, spoken summary; 18 of 18 planted issues on the demo contract | Muse Spark 1.3 reads pages; muse-council (Muse Wonder + Muse Spark 1.3 + Muse Spark 1.2, Muse Wonder aggregating) in a Hermes Agent profile. The Muse models did inference only | All page code by Claude Code (Anthropic) | Prototype | none (local app) |
| MuseAudioNotes, Ray-Ban Meta audio notebook: chord chart read from an image (a generated chart, not a real photo) | Muse Spark 1.3; inference only | Page code by Claude Code (Anthropic) | Prototype | none (local app) |

MuseEveryThings, the Ray-Ban Meta keys trainer: its Meta components are SAM 3.1 and DINOv2 (see above); no Muse model wrote code for it, and the plan for Muse Wonder to write a glasses app never started. Its LiDAR depth line completed a live USB run of 2,261 frames at 30 fps for more than 75 s without disconnects; touch accuracy, frame-to-event latency and MIDI correspondence are still open.

The owner rates one of the three Ray-Ban Meta services as complete and two as near-complete. Museon is the most complete (run end to end from the app on real model calls); the keys trainer passes on a recording and slow single notes, and the audio notebook has not been tried on the glasses. All three remain Prototype, run as a local Mac app, and have no public URL.

### 05 Outreach
| Deliverable | Meta model | Integration | Status | Public proof |
|---|---|---|---|---|
| 12 week-one captions (EN, RU) and invitations (VI, HI) | Meta AI (meta.ai), model not shown | Claude (Anthropic) recorded the sessions | Prototype | none |

### 06 Media
| Deliverable | Muse model and harness | Integration | Status | Public proof |
|---|---|---|---|---|
| Two 16-second explainer films, a fifth and beats, EN and RU, 1080×1920 | Muse Wonder Full through Muse Code | Design approved by Claude (Anthropic) with Claude Design; facts checked by Codex (OpenAI) | Prototype (EN versions published on the site; not posted to social networks; no listening review; the beats film's design approval is outdated by a later owner colour rule) | <https://soulsofmuse.app/sci-sound-labs/assets/video/intervals-en.mp4> |
| Ganesha R8, 82 s, 13 chapters: screenplay and storyboard; direction, shot and revision reviews, director's report; composed score (six melodic cells, harmony, percussion, orchestration; score data and editable MIDI) | Muse Wonder Full (screenplay and storyboard, through the subscription route in Muse Code and TopDog Colors); Muse Wonder (direction, review, composition); scenario v3 revised and reviewed in MetaMezonin on Muse Wonder | Video shots generated by non-Meta models on Krea (Wan, Seedance); editing, score performance and mix by Codex (OpenAI) and local tools | Completed master; the owner approved the previous cut and requested an English ending title, which R8 implements. Public since 5 Nov: [release asset](https://github.com/cybersheik/souls-of-muse/releases/tag/jury-media-20261105) | [jury dossier](https://soulsofmuse.app/dossier/) |
| Ganesha teacher reference and production reference images | Muse Image (`muse-image-1.0`) | Receipts and completed outputs checked against production records | Used in the completed master | [jury dossier](https://soulsofmuse.app/dossier/) |

## Credit to non-Meta tools
- **Codex (OpenAI):** orchestration, integration, tests, fact checks, the Bi-Level method design and acceptance, publication of the site sections, TopDog Colors UI 002, video editing, score performance and mixing.
- **Claude Code and Claude (Anthropic):** the three Ray-Ban Meta services, disclosure policy and check, design work, portal porting, plans. **Claude Design** produced the portal and lesson mockups that replaced the first portal, and the design approval of the explainer films.
- **Kimi (Moonshot AI):** the starting "Sound Made Visible" demo, the harness bench and plan, progress tracking, a first lesson runtime (replaced), the heart component.
- **Krea** (with Wan and Seedance models): all generated video shots of the Ganesha film. Google Flow was tried as a video route before Krea.
- **ZCode (GLM, Z.ai):** research documents, the earlier SDK client for TopDog Colors, LiDAR depth work.
- **A MiniMax research agent** and **Grok-based review bots (xAI):** research notes, reviews and internal drafts.
- **Nous Portal:** routing for some Muse Wonder reviewer calls inside Hermes Agent.
- **Apple Vision** hand pose: used in the keys trainer from 30 Oct to 4 Nov, then removed.
- **macOS voices:** the narrator (Daniel) and the studio's question (Samantha) in the live-action film; they are not presented as model-generated replies.
- **Gemini:** no contribution to these deliverables was found in the sources checked.

## Who did the work
This page is the attribution record for all workstreams. It was compiled with Claude Code (Anthropic) and Claude verifier subagents; no Meta model wrote it. The underlying configurations and production records were read, not edited.

## Paths that did not work
- **Muse Wonder Full from our own code.** Manual API keys returned 404 and a subscription key used outside Muse Code returned 403; an OpenCode probe returned no output. Muse Wonder Full is only reachable through Muse Code and its official SDK, which is why the team built its own SDK client.
- **Muse Code as the inner research role.** It was planned, but both research roles ended up on Muse Wonder (`muse-wonder-1.0`) in Hermes Agent.

Full list: [09 Paths that did not work](09-dead-ends.md).

## Not claimed
- No Muse credit for work whose model is not confirmed.
- No Muse credit for video shots (Krea), for the Portal 2.0 port (Claude), for the Ray-Ban Meta services code (Claude Code) or for TopDog Colors UI 002 (Codex).
- No claim that Muse Image produced the Portal 2.0 image set; that separate scope was not delivered.
- The live-action jury film (2:55.733, public on [YouTube](https://www.youtube.com/shorts/1EAl-cj0DJ4)) contains staged interactions; it is not end-to-end acceptance evidence for every feature it portrays.
- Sol Muse: no claim that a new foundation model was trained from scratch or that its weights run on the microcontroller.
- The terms of use of the Krea-generated clips are not yet recorded, as `docs/DISCLOSURE_POLICY.md` §3.6 requires before publication.
- "The sound research was done by Muse" covers the research itself (both loop roles, the loop code and repairs, adapters, renderer, films, retrospective). Method design, acceptance, the final audit and publication were done by Codex (OpenAI), and one early sound-portrait session in Hermes Agent contains one fallback call to Grok.
- "Done by Muse" means the Muse model produced the content; integration, testing and acceptance were done by the tools named in each row and by the project owner.
