# 08. Who did the work: agents and the Meta models behind them

## Why this page exists
Every task in the team's internal tracker is formally assigned to the project owner, who sets requirements, decides and accepts results. Tracker assignment therefore does not show who did the work.

The work itself was done by AI agents under short call signs. A call sign, or the third-party harness it runs in, often hides the model behind it: Hermes Agent, OpenCode and the team's own desktop harness were in many sessions running a Meta Muse model. This page pairs every call sign with the model actually behind it, lists the deliverables of Meta Muse models separately, and credits other tools honestly so that Meta models are not over-credited.

Sources: harness configurations and local session indexes on the development workstation, public pull request descriptions, and the team's tracker, all read on 5 Nov 2026. Where the model behind a call sign could not be confirmed, the page says "model not confirmed" and credits nothing to Meta.

## Call signs and the models behind them

| Call sign / name | What it is | Model(s) behind it | What it delivered | Confidence |
|---|---|---|---|---|
| Project owner | Human | — | Requirements, architecture, mandatory scope, go/no-go gates and every acceptance decision. Every tracker task is formally assigned to the owner; that assignment is not authorship | High |
| Jack | A profile of Hermes Agent, an open agent harness from Nous Research | Muse Wonder (`muse-wonder-1.0`) through the direct Meta API by default. Reviewer and code-review subagents used Muse Wonder routed through Nous Portal; auxiliary slots Muse Wonder and Muse Spark 1.3. One fallback call in one early sound-portrait session went to Grok (xAI), so that session is not 100% Muse | First Welcome portal code; the runner and controller code of the Bi-Level sound research and the repairs of its stopped run (both research roles were Muse Wonder through the direct Meta API; whether those calls were issued from inside Jack or by the runner Jack wrote is not recorded); the 15-second note-aware C-major scale; contract reviews through the muse-council preset. 12 project sessions, 29 Oct–3 Nov | High |
| muse-council | A mixture-of-agents preset inside Jack | Reference models Muse Wonder (`muse-wonder-1.0`), Muse Spark 1.3 and Muse Spark 1.2 answer in parallel; Muse Wonder aggregates | Clause-by-clause contract reviews (30 Oct, 3 Nov); the engine of the glasses "contract council" page | High |
| Hermes / Hermes Agent | The harness itself (see Jack) | Whatever profile it runs; on this project the Muse profile Jack | See Jack | High |
| OC1 | OpenCode, an open-source coding agent | Muse Wonder (`muse-wonder-1.0`) through the Meta API in the sessions of 2 and 4 Nov. A Muse Wonder Full probe on 2 Nov returned nothing. Its configured default is a non-Meta model; the sessions counted here explicitly selected Muse Wonder | An audit of the two explainer films (4 Nov: their design approval was outdated by a later owner colour rule) | High for the model; medium for the deliverable |
| OS-1 | Call sign named by the owner | Model not confirmed. No configuration or record of this call sign was found for 26 Oct–5 Nov on the development workstation; whether it is the same instance as OC1 is not confirmed | Nothing credited until confirmed | None |
| MZM | Resident agent of MetaMezonin, the team's desktop harness, rebuilt during the event from a Hermes-based UI into the rehearsal room for Convention members | Muse Wonder (`muse-wonder-1.0`) through the Meta API; Muse Image (`muse-image-1.0`) for images | Harness checks; review of the "Ganesha" scenario v3; one Muse Image test image (29 Oct), not used in the product | High |
| Muse Code | Meta's own coding agent for the terminal, driven by CX1 and DW1 as orchestrators | Muse Wonder (`muse-wonder-1.0`) and Muse Wonder Full (`muse-wonder-full-1.0`). On the development workstation: 200 sessions since 26 Oct, 175 on Muse Wonder and 25 on Muse Wonder Full (session index, read 5 Nov; not filtered by workstream) | Most Muse code and media work: admission control, cloud and budget work, Entrance v4, personal cabinet, site fixes, sound adapters and renderer, films, the "Ganesha" direction | High |
| TopDog Colors Muse | The team's clip studio for musicians, rebuilt during the event from the earlier TopDog Colors onto the official Muse Code SDK; the client code was built by DZ1 | Muse Wonder Full (`muse-wonder-full-1.0`); 5 sessions, 2–3 Nov | "Ganesha" direction sessions | High |
| Meta AI (meta.ai) | Meta's consumer web assistant, "Reasoning" mode | Meta AI; the interface does not show which model | 12 week-one post captions in English and Russian, invitations in Vietnamese and Hindi (two sessions; a third failed and is excluded) | High |
| CX1 | Codex (OpenAI) | Codex; not a Meta model | Director, integrator, tester and fact-checker for most Muse runs; some integration code (final regression of admission control, a later bug fix); Bi-Level method design and independent acceptance; publication of Sci Sound Labs; video editing and the "Ganesha" mix | High |
| CX2 | Agent on the signing-ceremony task | Model not confirmed | Deliverable not verified; nothing credited to Meta | Low |
| DW1 | Claude (Anthropic) in the Cowork app | Claude; not a Meta model | Lesson screen and portal design work with Claude Design; porting of Portal 2.0 and 2.1 into code; launched several Muse Wonder Full runs; the internal session registry; Sci Sound Labs plan; clickable "Glasses 1.0" design prototype | High |
| DC1 | Claude Code (Anthropic) | Claude; not a Meta model | All code of the three Ray-Ban Meta glasses developments (with Claude subagents); disclosure policy and check; LiDAR offline analysis; speech fine-tuning assessment; this page | High |
| DZ1 | ZCode on GLM (Z.ai) | GLM; not a Meta model | Hackathon application; map of Meta models; coverage model; Muse Code SDK client; LiDAR research and depth receiver; desk-robot metronome plan; independent production check on 4 Nov | High for the model; medium for the deliverables (from internal summaries) |
| MI1 | MiniMax research sub-agent | MiniMax; not a Meta model | Versions 2 and 3 of the research note "Who still plays?" | Medium |
| GB1 | Grok bot (xAI) | Grok; not a Meta model | Reviews (for example of the session registry count) and drafts of internal summary chapters | Medium |
| GBH | A separate review bot | Not a Meta model; exact model not confirmed | Drafts of internal summary chapters | Low |
| Kimi | Kimi agent (Moonshot AI) | Kimi; not a Meta model | Starting "Sound Made Visible" demo; harness plan; first lesson runtime (rejected as a public backend); the heart component; internal progress tracking | High |
| MS1 | Author of the speech research for lesson and glasses | Model not confirmed | Speech research that recommended Meta MMS-TTS; not credited to Meta | Low |
| MUW1 | Author of the governance (DAO) draft | Model not confirmed; its session journal was not found | DAO draft; not credited to Meta | Low |
| MC1 | Script and card formatting reviewer | Model not confirmed | Formatting of the final-video script; name-card proposals; review of social cards | Low |
| TUZ | Agent on the promo-film and watch tasks | Model not confirmed | Plan of the 11-clip promo and the original watch-and-metronome stage; closed the Meta-only video route | Low |

### Meta models used as components, not as agents
- **SAM 3.1** (cloud and local weights): keys, fingers and side view in the glasses keys trainer.
- **DINOv2 small:** "key appearance changed" vote in the keys trainer.
- **Llama 3.2 Vision 11B** (local, 4-bit): tested as a key-press judge and rejected (see [09](09-dead-ends.md)).
- **MMS-TTS** (`facebook/mms-tts-eng`, `facebook/mms-tts-vie`): server-side EN/VI speech, technical pilot.
- **Meta speech recognition** through the Meta API: lesson speech input.
- Licences for DINOv3 and SAM 3D Body were accepted on 4 Nov; neither was downloaded or used.

## Work done by Meta Muse models, by workstream
Status per `docs/DISCLOSURE_POLICY.md` §5. "Integration" names the non-Meta agent that wired, tested or published the Muse output.

### 01 Service and lesson
| Deliverable | Muse model and harness | Integration | Status | Public proof |
|---|---|---|---|---|
| Five-lesson admission control (durable SQLite store) | Generated by Muse Wonder, independently reviewed by Muse Spark, both through Muse Code | CX1 (Codex) integrated and added the final path regression; 54 offline checks | Offline-tested | [PR #1](https://github.com/cybersheik/souls-of-muse/pull/1) (merged) |
| Private EN↔VI text interpretation backend | Implementation by Muse Wonder through Muse Code | CX1 (Codex) integration and verification | Offline-tested | [PR #3](https://github.com/cybersheik/souls-of-muse/pull/3) (draft) |
| Lesson runtime: lesson-plan proposals and translation | Muse Wonder prepares lesson-plan proposals; Muse Spark interprets and reviews translations (one real EN→VI step in 9.078 s) | CX1 (Codex) | Prototype | [PR #5](https://github.com/cybersheik/souls-of-muse/pull/5) (draft) |
| First Welcome portal (convention signature preview, Welcome card, seven Leagues, three role contexts) | Muse Wonder in Hermes Agent (Jack), direct Meta API | CX1 (Codex) integration | Prototype; rejected on design by the owner | [PR #2](https://github.com/cybersheik/souls-of-muse/pull/2) (draft) |
| Entrance v4 and its fixes | Muse Wonder through Muse Code | DW1 (Claude) first run, CX1 (Codex) integration | Prototype | [PR #4](https://github.com/cybersheik/souls-of-muse/pull/4) (draft) |
| Site candidate fixes, 1 Nov (four frontend regressions, deploy routing, honesty labels) | Muse Wonder through Muse Code | CX1 (Codex) found the regressions | Prototype | none |
| Personal cabinet 1.4 and 1.5 (Leagues, video demo, tests, 390 px phone layout, League catalogue) | Muse Wonder Full through Muse Code | DW1 (Claude) combined them into PR #5 | Prototype | [PR #5](https://github.com/cybersheik/souls-of-muse/pull/5) (draft) |
| Proposal to use MMS-TTS for lesson speech (19 Oct, before the event) | Muse Wonder | CX1 (Codex) wired MMS-TTS into the service | Designed (the proposal); the speech integration built from it is a Prototype, not owner-accepted | <https://soulsofmuse.app/api/harness/health> |

### 02 Engineering on Meta models
| Deliverable | Muse model and harness | Integration | Status | Public proof |
|---|---|---|---|---|
| Cloud plan, budget implementation, cloud survey, deploy plans, paid-hosting implementation and tests (27–29 Oct) | Muse Wonder through Muse Code; Muse Spark reviewed budget, cloud, timestamp and deploy work | CX1 (Codex) integrated; mostly plans and reviews | Offline-tested | none |
| Text-only brainstorm on the team's harness and client app as Souls of Muse apps (2 Nov) | Muse Wonder Full through Muse Code | — | Designed | none |
| Sessions of the team's own harness (MetaMezonin) and of OpenCode | Muse Wonder through the Meta API | Harness code itself is not credited to Muse | Prototype | none |

### 03 Research with Muse
| Deliverable | Muse model and harness | Integration | Status | Public proof |
|---|---|---|---|---|
| Bi-Level AutoResearch on "Sound Made Visible": both loop roles (48 inner and 11 outer calls in campaign v2, two separate contexts of the same model) | Muse Wonder (`muse-wonder-1.0`), direct Meta API | Method design, independent acceptance tests, final audit and report by CX1 (Codex); starting prototype by Kimi | Offline-tested | <https://soulsofmuse.app/sci-sound-labs/jury-report.html> |
| Runner and controller code of the research loop, and the repairs of the stopped first run | Muse Wonder in Hermes Agent (Jack) | Acceptance by CX1 (Codex) | Offline-tested | none |
| Audio adapters (beats, harmonic balance, decay), renderer, showcase, research films, Muse retrospective report | Muse Wonder Full (`muse-wonder-full-1.0`) through Muse Code | CX1 (Codex): 26/26 independent renderer tests, fact check, publication | Offline-tested | <https://soulsofmuse.app/sci-sound-labs/> |
| Ray-Ban Meta contract council: reading of contract pages (shown on a synthetic page only), clause-by-clause review, spoken summary | Muse Spark 1.3 reads pages; muse-council (Muse Wonder + Muse Spark 1.3 + Muse Spark 1.2, Muse Wonder aggregating) in Hermes Agent (Jack). The Muse models did inference only | All page code by DC1 (Claude Code) | Prototype | none (local app) |
| Ray-Ban Meta audio notebook: chord chart read from an image (a generated test chart, not a real photo) | Muse Spark 1.3; inference only | Page code by DC1 (Claude Code) | Prototype | none (local app) |

Ray-Ban Meta keys trainer: its Meta components are SAM 3.1 and DINOv2 (see above); no Muse model wrote code for it, and the plan for Muse Wonder to write a glasses app never started.

The owner rates one of the three Ray-Ban Meta developments as complete and two as near-complete. On the evidence, the contract council is the most complete (the only one run end to end from the app on real model calls, twice); the keys trainer passes only on a recording and slow single notes, and the audio notebook was never tried on the glasses. All three remain Prototype, run as a local Mac app, and have no public URL.

### 05 Outreach
| Deliverable | Meta model | Integration | Status | Public proof |
|---|---|---|---|---|
| 12 week-one captions (EN, RU) and invitations (VI, HI) | Meta AI (meta.ai), model not shown | DW1 (Claude) recorded the sessions | Prototype | none |

### 06 Media
| Deliverable | Muse model and harness | Integration | Status | Public proof |
|---|---|---|---|---|
| Two 16-second explainer films, a fifth and beats, EN and RU, 1080×1920 | Muse Wonder Full through Muse Code | Design approved by DW1 (Claude) with Claude Design; facts checked by CX1 (Codex) | Prototype (EN versions published on the site; not posted to social networks; no listening review; the beats film's design approval is outdated by a later owner colour rule) | <https://soulsofmuse.app/sci-sound-labs/assets/video/intervals-en.mp4> |
| "Ganesha" promo film: direction, contact-sheet reviews, music decisions, release report | Muse Wonder (Muse Code) and Muse Wonder Full (TopDog Colors Muse client); scenario v3 reviewed by MZM on Muse Wonder | Video frames generated by non-Meta models on Krea (Wan, Seedance); execution, editing and mix by CX1 (Codex). Muse is credited for direction only | Prototype (current cut awaits owner acceptance) | none |
| One Muse Image test image (29 Oct); not used in the product, and Muse Image for the portal was never run (see [09](09-dead-ends.md)) | Muse Image (`muse-image-1.0`) in MetaMezonin | — | Offline-tested (single test) | none |

## Credit to non-Meta tools
- **Codex (OpenAI), as CX1:** orchestration, integration, tests, fact checks, the Bi-Level method design, publication of the site sections, video editing.
- **Claude (Anthropic):** DW1 in Cowork (design porting, registry, plans) and DC1 in Claude Code (the three glasses developments, disclosure tooling). **Claude Design** produced the portal and lesson mockups that replaced the first portal, and the design approval of the explainer films (with DW1).
- **Kimi (Moonshot AI):** the starting "Sound Made Visible" demo, the harness plan, a first lesson runtime (replaced), the heart component.
- **Krea** (with Wan and Seedance models): all generated video clips of the "Ganesha" film. Google Flow was tried as a video route before Krea.
- **Gemini:** no contribution to these deliverables was found in the sources checked.
- **GLM through ZCode (Z.ai), as DZ1:** research documents, the SDK client app, LiDAR depth work.
- **MiniMax, as MI1**, and **Grok (xAI), as GB1/GBH:** research notes, reviews and internal drafts.
- **Nous Portal:** routing for some Muse Wonder reviewer calls inside Hermes Agent.
- **Apple Vision** hand pose: used in the keys trainer from 30 Oct to 4 Nov, then removed.

## Who did the work
This page is the attribution record for all workstreams. It was compiled by DC1 (Claude Code) with Claude verifier subagents; no Meta model wrote it. The underlying configurations and session indexes were read, not edited.

## Paths that did not work
- **Muse Wonder Full from our own code.** Manual API keys returned 404 and a subscription key used outside Muse Code returned 403; an OpenCode probe returned no output. Muse Wonder Full is only reachable through Muse Code and its official SDK, which is why the team built its own SDK client.
- **Muse Code as the inner research role.** It was planned, but both research roles ended up on Muse Wonder (`muse-wonder-1.0`) in Hermes Agent.
- **A complete session registry.** The internal registry stops at 31 Oct and its count does not reconcile, so this page uses configurations and session indexes and publishes no registry total.

Full list: [09 Paths that did not work](09-dead-ends.md).

## Not claimed
- No Muse credit for work whose model is not confirmed (OS-1, CX2, GBH, MS1, MUW1, MC1, TUZ).
- No Muse credit for video frames (Krea), for the Portal 2.0 port (Claude) or for the glasses code (Claude).
- The terms of use of the Krea-generated clips are not yet recorded, as `docs/DISCLOSURE_POLICY.md` §3.6 requires before publication.
- "The sound research was done by Muse" covers the research itself (both loop roles, the loop code and repairs, adapters, renderer, films, retrospective). Method design, acceptance, the final audit and publication were done by CX1 (Codex), and one early sound-portrait session in Jack contains one fallback call to Grok.
- Session counts come from local indexes on one workstation, read on 5 Nov; sessions on other machines are not counted, and sessions are not filtered by workstream.
- "Done by Muse" means the Muse model produced the content; integration, testing and acceptance were done by the agents named in each row and by the project owner.
