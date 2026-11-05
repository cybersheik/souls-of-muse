# 03. Research with Muse

## Why it matters
Before and while building, the team used Meta models as research partners: to make sound visible and explainable, and to find where wearables and vision can help a learner at the instrument without replacing the teacher. Two background studies (who still plays music; how practice apps work) were done by other AI tools and are listed here with that credit.

## Before the event
Meta's open MMS-TTS voices were proposed for the lesson by Muse Wonder on 19 Oct 2026, before the event. The starting point of the sound study, "Sound Made Visible", is a demo built with Kimi (third-party, not a Meta model) and supplied to the project: https://visionsound.ok.kimi.link/ (its build date is not recorded here, so it is not claimed as pre-event work).

## During the event
Times are UTC+7.

| Study | Question | Status | Evidence |
|---|---|---|---|
| Sound Made Visible | Can multi-round AutoResearch with Muse turn sound into explainable geometry? | Offline-tested: completed campaign of 31 Oct 2026 against a frozen synthetic evaluator; results, cards and films are public | Public section https://soulsofmuse.app/sci-sound-labs/ (article, 24 result cards, 18 films) and jury report https://soulsofmuse.app/sci-sound-labs/jury-report.html. Round summary: 24 windows × 300 s (7,200 s), 59 completed Meta calls (48 inner, 11 outer), 11 outer changes applied to later windows, 23 PROMISING calibrations, 1 INCONCLUSIVE, 0 final rejections, 10 sound and wave families; held-out check on 19 candidate-condition entries × 2 seeded points, maximum mean relative error 0.081%. Research by Muse models; see "Sound Made Visible: the double loop" |
| Bilevel AutoResearch architecture | How to structure research loops between agents | Designed (governed design of 30 Oct 2026, not run as designed); a simplified double loop ran in the 31 Oct campaign (row above) | Method as run: section "Sound Made Visible: the double loop" below and section 2 of the jury report. References: Karpathy's single-loop autoresearch (https://github.com/karpathy/autoresearch) and the published Bilevel Autoresearch paper (https://arxiv.org/abs/2603.23420). The governed design (locked evaluator, hidden holdout, immutable envelope, Muse Code as inner proposer) was written as a read-only consultation by CX1 (Codex); it is not published |
| Who still plays? | How amateur music-making changed from the 1980s to the 2020s | Not done (no public report). An internal draft exists; no Meta model took part | None published. Internal drafts: v1 by DZ1 (ZCode on GLM); v2 and v3 by MI1 (a MiniMax research agent). No figure from them is used in the submission until it is published with its primary source |
| Learning-app landscape | How established practice apps work and where a human-centred service differs | Not done (no public summary). An internal dossier exists; its author model is not confirmed and it is not credited to Meta models | None published. An internal dossier on two established practice apps exists (author model not confirmed). A public summary with links to the vendors' own pages is not yet written |
| Vision-based score following | Can SAM 3.1 follow a player's position in the score? | Offline-tested (synthetic tests only; not public) | Not public. Own score follower fed by SAM 3.1 vision (code by DC1, Claude Code). Synthetic tests (30-31 Oct 2026): on clean input an off-the-shelf follower was more accurate (0.03 vs 0.07 beats), but with the 20-30% missed notes typical of vision input it lost position in 13-29% of cases versus 0% for our follower; a no-metre mode followed 85 of 85 notes. Lag reduced from -838 ms to +3 ms on synthetic input; not checked on live playing |
| Wearables | Finger-position coaching and audio notebook on smart glasses | Prototype (local app; not public) | Not public. Three Ray-Ban Meta developments, run as one local app on the development workstation with video from the glasses: Museon (contract council), MuseEveryThings (finger-on-key trainer), MuseAudioNotes (audio notebook). See "Ray-Ban Meta: three developments" |
| Voice for the lesson | Which open Meta text-to-speech can voice EN/VI translations, and can it be fine-tuned? | Prototype (untuned MMS-TTS in the service, workstream 01); fine-tuning not done | Model cards https://huggingface.co/facebook/mms-tts-eng and https://huggingface.co/facebook/mms-tts-vie. Research by MS1 (model not confirmed) |

## Sound Made Visible: the double loop
**What it is.** A bounded Bi-Level AutoResearch campaign: a double loop in which an inner loop searches for relationships between sound and visible form and an outer loop changes how that search is conducted. It is adapted from Karpathy's autoresearch, which is a single greedy loop, by adding an outer level, in the spirit of the published Bilevel Autoresearch work. It is a simplified version of the team's governed design (see "Paths that did not work").

**Inner loop (muse-wonder-1.0, 2 calls per window).** In each 300-second window the first call proposes a hypothesis: a formula inside a pre-declared family and range, passed as data only; no generated code was executed. A frozen evaluator, fixed before the campaign, scores it against targets built from hidden seeds: relative numerical error and, where applicable, an FFT check on synthesised audio. The second call reads the counterexamples and refines the formula. Example: in the first window the model corrected its Lissajous ratio from p/q to q/p. 24 windows × 2 calls = 48 inner calls.

**Outer loop (muse-wonder-1.0, separate context, 11 calls).** After every second window the outer role reads the outcomes and rewrites the research conditions: focus, priorities, ranges and assumptions, inside a pre-set set of families. Every change is logged with the window that requested it and takes effect only from a later window boundary. 11 of 11 outer decisions were actually applied. The search moved from Lissajous figures and beats, to harmonic balance (H2/H1) and decay, to spatial resonators (string, membrane, Helmholtz resonator, pipes), to open versus closed pipes, to capillary waves, to invariance controls, and finally to geometric similarity.

**What the outer loop did not do.** It did not change the evaluator, the metric or the holdout, and added no executable physics modules: the six engine source files kept their frozen hashes. The design allowed metric-weight changes within approved intervals; the campaign did not use that option. Whether the outer loop beats a fixed search strategy was not measured.

**Results (31 Oct 2026, 12:25-14:25).** 24 windows × 300 s, 7,200.368 s in total; 59 completed direct Meta calls (48 inner + 11 outer), about 2.05 million tokens. 23 PROMISING, 1 INCONCLUSIVE, 0 final REJECTED, across 10 families (Lissajous 1, beats 2, H2/H1 6, decay 4, membrane 2, string 1, Helmholtz 2, closed pipe 2, open pipe 3, capillary 1). Held-out check: 19 candidate-condition entries × 2 seeded points, maximum mean relative error 0.081218%, covering 9 families; the capillary case did not pass. "PROMISING" means agreement with a known physical law in a synthetic model: these are calibrations, not 24 discoveries, and later windows repeated H2/H1 and decay controls, so progress plateaued.

**Outputs.** 24 result cards (1080 × 1080), six 11-second videos with synchronised audio, and two 16-second English films (a fifth with a 4:3 control: https://soulsofmuse.app/sci-sound-labs/assets/video/intervals-en.mp4; and beats from 3 Hz to 0 Hz). The public page also keeps the six pilot films and a 39-second performance loop of curated licensed third-party footage (edited by the team; source credits are listed on the page), which is not a research result and is not credited to Meta models.

**Who did it.**
- Both research roles: muse-wonder-1.0 in separate contexts, through the direct Meta API.
- Runner and controller code, the controller fix after review, wiring of the three audio adapters into the loop, the repair of the stopped first run, and the 15-second note-aware scale: Muse Wonder in the Hermes Agent profile "Jack" (a third-party harness running muse-wonder-1.0), as recorded in the team's task records; the session logs were not re-checked for this page. Who wrote the frozen evaluator is not recorded separately. Whether the 59 research calls were sent from that session or by the runner it wrote is not recorded.
- Three audio adapters (beats, harmonic balance, decay), the renderer and showcase, the two 16-second films and the written retrospective: Muse Wonder Full (muse-wonder-full-1.0) in Meta's Muse Code CLI.
- Not Muse: method consultation, independent acceptance tests, the final audit and report, caption fact-checks and publication of the site section by CX1 (Codex); film design approval by DW1 (Claude) with Claude Design; the starting demo by Kimi. One fallback call in an early pilot session of Jack went to a non-Meta model (Grok); the completed campaign's 59 calls were all muse-wonder-1.0.

## Ray-Ban Meta: three developments
**What exists.** Three developments for Ray-Ban Meta glasses, built from 30 Oct to 4 Nov 2026 in one dedicated Claude Code working session ("Meta Ray-Ban for Soul of Muse") by DC1 (Claude Code). They run as one local web app on the development workstation with three pages. Video from the glasses reaches the workstation through a WhatsApp video call placed from the glasses; there is no app on the glasses themselves. On 4 Nov they were renamed Museon, MuseEveryThings and MuseAudioNotes.

The project owner rates one development as complete and two as near-complete. On the recorded evidence the most complete is **Museon**: it is the only one that ran end to end from the app's button on real model calls with a scored result. All three remain Prototype in the sense of policy §5: they run locally, and no code, video or page from them is public.

**Museon: contract council (Prototype).** As designed, the user photographs the pages of a contract and Muse Spark 1.3 reads them (so far shown only on a synthetic page, see below). A "muse-council" mixture inside Hermes Agent profile "Jack" then reviews the contract: muse-wonder-1.0, muse-spark-1.3 and muse-spark-1.2 answer in parallel, and muse-wonder-1.0 aggregates. The output is a 90-word spoken summary, a clause-by-clause red/amber/green review under English law with fair alternatives and case references, and a two-language line saying it is not legal advice.
- 30 Oct: Muse Spark transcribed a synthetic contract page (3° tilt, blur) word for word with zero errors in 10.8 s. The full council run on a 17-article demo contract took 160 s, found 18 of 18 planted traps and gave 14 relevant case references; the answer key was never shown to the models. A smoke test found the right precedent on artists' contracts in 16.6 s.
- 3 Nov 21:27: a live run from the app's button took 206 s and returned 15 clauses (14 red, 1 amber), a negotiation package and the disclaimer.
- Not done: no real photo of contract pages taken with the glasses has gone through the chain; both council runs used the demo contract as text; the 3 Nov run was not re-scored against the trap key; traces are off, so a trace does not prove the four-model fan-out; case citations need a human check; the spoken summary was not checked through the glasses' Bluetooth; advice during a live conversation was not built.

**MuseEveryThings: finger-on-key trainer (Prototype).** It does not recognise notes. The score (Für Elise) is known, so the next expected key is known, and the stand only confirms that the finger landed on that key and held still for two frames. SAM 3.1 segments the black keys; a known keyboard blueprint is fitted to them (a cardboard keyboard, or a one-dimensional model along the black keys of a real piano) and tracked frame to frame; the octave is locked from the first note of the score; DINOv2 small gives a third vote ("the key's appearance changed"). The confirmed note plays from the workstation.
- On a glasses recording of a real piano (2 Nov), slow single-note passage: finger on the expected key 12 of 12; confirmed by the DINOv2 threshold 11 of 12; AUC 0.94 strict and 0.88 hard; the stand replay confirmed 9 of 9 notes in score order with no extra notes.
- Live, cardboard keyboard over the WhatsApp call (3 Nov, 23:00-23:40): the blueprint held with 28-37 keys in frame; the best take confirmed 10 notes in a row.
- Speed: local SAM 3.1 0.09 / 0.21 / 0.67 s at 336 / 504 / 1008 px; cloud SAM 3.1 1.4-5.3 s per 1024 px frame; black-key tracking 4 ms per frame against 94 ms for a full scan; DINOv2 20-25 ms per frame; confirmation to sound 100-130 ms; the video-call path adds about 1 s.
- Not done: normal tempo with two hands and a moving head (36 of 187 hits, 53 of 187 with an anchor); "pressed" versus "resting" (75% false positives among resting fingers); the SAM-only build used since 4 Nov 03:50 has had no live take; a side phone view added on 4 Nov was never checked on live playing; the final recorded take was not made before the deadline.

**MuseAudioNotes: audio notebook (Prototype).** A chord grid with tempo, a quiet click and a spoken cue in the ear (current chord, next chord, what to prepare), built with the browser's audio and speech features. A photo of a chord chart goes to Muse Spark 1.3, which returns the song as structured data. 3 Nov: a 48-bar chart read in 15.3 s with the song form correct.
- Not done: the chart was a generated test image, not a photo of a real music stand; voice and click through the glasses' Bluetooth were never checked live; the "follow the player" mode (listen and adapt the cues to tempo) was not built.

**Other Meta models on this line.** SAM 3.1 (cloud and local weights) for keys, fingers and the side view; DINOv2 small as the third vote; Llama 3.2 Vision 11B tested and rejected (see below). Licences for DINOv3 and SAM 3D Body were accepted on the evening of 4 Nov, but neither model was downloaded or used. The Wearables Device Access Toolkit was not integrated.

**Side line: depth for "pressed versus resting" (Offline-tested).** Researched by DZ1 (ZCode on GLM; cookbook and depth receiver) and analysed by DC1 (Claude Code) on an offline phone LiDAR recording: key-surface noise under 2 mm at 65-90 cm; a pressed fingertip sits 5-10 mm above the surface, a hovering one 20-35 mm. The live USB stream was never run because of a hardware fault on the test phone; deferred to the final round.

## Meta models
| Study | Model | Role | Verified outcome |
|---|---|---|---|
| Sound Made Visible | muse-wonder-1.0 | Inner proposer and, in a separate context, outer redirector | 48 + 11 completed calls; 11 of 11 outer changes applied; 23 PROMISING, 1 INCONCLUSIVE (Offline-tested) |
| Sound Made Visible | muse-wonder-1.0 in Hermes Agent profile "Jack" | Wrote and repaired the runner and controller; built the note-aware scale | Accepted after independent tests by CX1 (Codex) |
| Sound Made Visible | muse-wonder-full-1.0 in the Muse Code CLI | Audio adapters, renderer, films, retrospective | Renderer accepted on independent tests; films public |
| Bilevel architecture | — | The governed design was a consultation by CX1 (Codex); no Meta model was called in it | Designed, not run as designed |
| Museon | Muse Spark 1.3; muse-council (muse-wonder-1.0, muse-spark-1.3, muse-spark-1.2, aggregator muse-wonder-1.0) | Page reading; contract review | 18 of 18 traps (30 Oct, demo text); live app run 206 s (3 Nov) (Prototype) |
| MuseEveryThings | SAM 3.1; DINOv2 small | Key and finger segmentation; key-appearance vote | 9 of 9 notes on a recording; 10 in a row live on cardboard (Prototype) |
| MuseAudioNotes | Muse Spark 1.3 | Reads a chord chart from a photo | 48 bars in 15.3 s on a generated test chart (Prototype) |
| Score following | SAM 3.1 (input only) | Vision input; the follower is the team's own algorithm | Synthetic tests only (Offline-tested) |
| Voice | MMS-TTS (open weights) | EN/VI speech | Untuned, in the service as a technical pilot (workstream 01) |
| Who still plays?; learning-app landscape | none credited | — | Done by other tools; not published |

All glasses code was written by DC1 (Claude Code) and its Claude sub-agents. The Meta models on that line did inference only; a plan for Muse Wonder to write an Android app for the glasses never started.

## Who did the work
Every task in the team's tracker is formally assigned to the project owner. This section states who actually did the work.

- **Muse models (credited separately).** muse-wonder-1.0: both research roles of the sound campaign; the runner, controller and repairs (in Hermes Agent profile "Jack"); the council reviews and aggregation. muse-wonder-full-1.0 (Muse Code CLI): the sound adapters, renderer, films and retrospective. Muse Spark 1.3 and 1.2: contract-page and chord-chart reading, council references. SAM 3.1 and DINOv2: vision on the glasses line.
- **Other AI tools.** CX1, Codex (OpenAI): method consultation for the double loop, acceptance tests, final audit, publication of the site section. DW1, Claude (Anthropic): film design approval with Claude Design; the clickable "Glasses 1.0" design prototype (4 Nov). DC1, Claude Code (Anthropic): all glasses code, the score follower, the depth analysis. DZ1, ZCode on GLM: the first "Who still plays?" draft, the depth cookbook and receiver. MI1, MiniMax: "Who still plays?" v2 and v3. MS1 (model not confirmed): voice research. Kimi: the starting "Sound Made Visible" demo.
- **Project owner.** Questions, go/no-go gates for every long run, rejection and redirection of failed paths.

## Paths that did not work
**Sound research**
- **The six-variant pilot (30 Oct)** produced four musical portraits, a scale and a rhythm, and was downgraded on review to "engineering feasibility pass, bi-level experiment not yet run": outcomes were pre-assigned per slot, there was no baseline, no working holdout and no measured improvement, and the outer role narrowed ranges without any improvement signal. Lesson: two contexts of one model are not yet a bi-level loop; the outer level must change the search and act only in the next cycle. The pilot films stay on the page as history.
- **Shape from band energy (30 Oct)** could not tell apart different notes inside the same frequency band, and the shape stayed active during rests. Replaced by a note-aware scale with a distinct colour and outline per note (31 Oct).
- **The first runner (31 Oct)** was rejected (4 checks passed, 1 failed): a partial checkpoint was billed twice, outer decisions were applied late, and fresh feedback was lost in a truncated context.
- **The first 24-window run (31 Oct, from 10:23)** was stopped at about 10:55: three empty public answers (4094 of 4096 output tokens spent on reasoning), a lost failure reason, and an outer-loop request (disable the Helmholtz end correction) that the frozen engine silently ignored (78.346 Hz either way). Muse repaired the code (empty answers become explicit errors; the flag now gives 78.35 versus 97.21 Hz); an intermediate request format returned HTTP 400 and was discarded. The run was restarted from zero and its windows are excluded from every count.
- **Capillary waves (window 12)** ended INCONCLUSIVE: numeric error about 0.018%, but the mandatory FFT check fell outside the available range. No film was made; the page shows it as the honest gap.
- **Outer-loop weak points.** After window 12 it mostly repeated controls; one outer rationale claimed a quantity was not yet isolated when an earlier window had already tested it, and the claim was rejected; a cross-family scaling exponent was not declared proven; irrelevant literature hits were not used as evidence.
- **The governed design (30 Oct)** was not run as designed: Muse Code was planned as the inner proposer, but both roles ended up on muse-wonder-1.0, and the campaign ran on a bounded standalone runner instead of the team's governed research platform.
- **Social films:** the first eight draft uploads failed (HTTP 403, wrong content type) and Muse reported this itself; two design rounds were rejected before approval; a later colour rule from the owner made that approval out of date for the beats film, and the requested fix was not applied before publication (the public beats film is the earlier master); no human listening review was made and the films were not posted to Facebook or Instagram.

**Ray-Ban Meta glasses**
- **Shadow touch detector (31 Oct - 2 Nov):** 3% errors on synthetic data; on real video, top light gave no shadow on 29 of 30 fingertips and low side light gave no single hover-to-touch transition. Closed: the method failed, not the lighting.
- **Llama 3.2 Vision 11B as judge** of "finger on the outlined key" (2 Nov): 10 of 20 under every prompt, the same answer for every crop, 3.6-5.5 s per crop. Replaced by DINOv2 small (AUC 0.85 versus 0.73 for a pixel baseline on cardboard; 0.77 versus 0.50 on a real piano).
- **Muse Spark as judge of guitar finger posture** (30 Oct): answered "curled" for both the correct and the collapsed hand; the square-versus-triangle rule degenerates from the glasses' viewpoint. The guitar posture line was dropped from the demo.
- **Homography on a real piano** (night 2-3 Nov): ten frames of one scene gave four different fits (wide-angle bend, merged black keys, hands hiding keys). Replaced by a one-dimensional model along the black keys plus an octave lock from the score.
- **Cloud SAM 3.1 in the live loop:** 1.4-5.3 s per frame plus network; kept for calibration only. The live loop moved to local SAM 3.1 weights.
- **Anchors and box prompts:** a template anchor above the keys and a fingertip anchor locked onto the neighbouring octave or the key edge; box prompts in local SAM did not track their boxes. Disabled.
- **Apple Vision hand pose** (used from 30 Oct, about 5 ms per frame) was removed on 4 Nov at the owner's direction: it worked poorly, and the showcase must rest on Meta segmentation. Fingers now come only from SAM 3.1.
- **"Every touched key sounds" mode** played the whole resting hand, because from above resting and pressing look the same.
- **Two-camera live take** (night 3-4 Nov) failed: the video-call window collapsed when switching windows, so the stand went blind; enabling the glasses' microphone muted the workstation's audio.
- **A sound channel** (the tap on cardboard heard by the glasses' microphone) was rejected by the owner: the demo is about segmentation. Audio onsets were used only to label ground truth.
- **An app on the glasses themselves** was not reached: Meta AI features on the glasses were not available in the owner's region and the Wearables Device Access Toolkit's developer mode was never verified; transport became a video call.
- **Live depth stream** blocked by a phone hardware fault; offline analysis only.
- **Score follower:** an off-the-shelf follower was rejected after measurement (above); a metre-based ensemble "played in someone else's bar" on a free-tempo sketch and was replaced by a no-metre mode.

**Voice research**
- **Fine-tuning a dedicated Muse voice** with MMS-TTS needs a clean single-speaker corpus of 0.5-1 hour per language and rented compute; it was not done. Training text-to-speech from scratch was rejected.

## Not claimed
- No physical measurements were taken in the sound study; every sound is synthetic. No human perception, learning or engagement test was run. The 23 PROMISING results are calibrations of known laws, not discoveries. The advantage of the outer loop over a fixed strategy was not measured. Live or arbitrary-audio recognition is not implemented.
- The Sci Sound Labs section was merged into `main` on 5 Nov (commit `fc6cc6c`) and is covered by that timestamp evidence release.
- Nothing from the three glasses developments is public: no code, video or page. None runs on the glasses; video reaches a local workstation through a video call. None has been used in a real lesson.
- The contract council is not legal advice; its case citations need a human check, and it has not read real photographed contract pages from the glasses.
- The score follower is tested on synthetic input only.
- The depth line and the "follow the player" notebook mode are future work.
- "Who still plays?" and the learning-app landscape are not credited to Meta models and are not published; no figure from them is claimed.
- Competitor or participant names from community channels are never published (policy §3.5).
```
