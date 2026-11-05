# 09. Paths that did not work

Dead ends, corrections and retracted claims are evidence of rigour (`docs/DISCLOSURE_POLICY.md` §4). This page lists the paths we tried and dropped, with what we measured. Each entry names the tool that did the work and the model behind it; see [08 Who did the work](08-who-did-the-work.md) for the full map. Where a failure was later resolved, the dated failure is followed by the resolution.

Dates are ICT (UTC+7). Numbers are from the team's internal measurements on the stated date unless a public link is given. Status of each entry is the status of the abandoned path, not of the project.

## 01 Service and lesson

### First Welcome portal (29–30 Oct)
- **Tried:** a Welcome page, seven Leagues and three role cabinets, coded from a text brief. Code by Muse Wonder in a Hermes Agent profile through the direct Meta API; coordination and publication by Codex (OpenAI).
- **Measured:** 24 of 24 frontend tests passed and the deploy was ready, but those gates checked function, not design.
- **Dropped because:** the owner rejected it on structure and visual quality on 30 Oct. Post-mortem: no designer had drawn the pages, the coding model invented the interface from text, and honesty rules were rendered as warning paragraphs.
- **Replaced by:** mockups in Claude Design (Portal P0 → Entrance v4 → Portal 2.0/2.1), coded afterwards. Muse Wonder also proposed three alternative visual directions on 30 Oct; none was chosen, although the first is close to what Claude Design later drew.
- **Lesson:** design first, then Muse codes from mockups. Tests passing is not design acceptance. Public: [PR #2](https://github.com/cybersheik/souls-of-muse/pull/2).

### Portal 2.0 through Muse Code (3 Nov)
- **Tried:** a 77-minute Muse Code run (Muse Wonder Full) to port the Portal 2.0 mockup into code, launched by Claude (Anthropic).
- **Measured:** the model read the references and changed no files.
- **Replaced by:** a port by Claude (Anthropic). Portal 2.0 is not credited to Muse.

### Stalled and failed Muse Code runs (1–2 Nov)
- **Personal cabinet 1.3** (Muse Wonder Full, 2 Nov): code was written, but the run hung while starting an HTTP server and was stopped. Versions 1.4 and 1.5 completed.
- **Site candidate fixes** (Muse Wonder, 1 Nov): one run ended in a failure after its maximum of 8 steps and was redone.

### First lesson runtime (31 Oct)
- **Tried:** a lesson runtime v0.1 handed over by Kimi (not a Meta model).
- **Dropped because:** the independent review by Codex (OpenAI) found it unsafe as a public backend: an unauthenticated demo endpoint calling Meta, lesson endpoints trusting a client-supplied actor, a fresh budget ledger replacing the real one, no durable restart, delivery even when the validator failed, and output limits that reproduced an empty-answer failure (298 of 300 tokens spent on reasoning).
- **Replaced by:** the base in [PR #3](https://github.com/cybersheik/souls-of-muse/pull/3), fixed by Muse Wonder through Muse Code (real EN→VI 3.886 s, VI→EN 3.323 s).

### First real voice run (3 Nov)
- **Tried:** two browser profiles, Meta speech recognition twice, Muse Spark twice, MMS-TTS over a local real-time connection. Run by Codex (OpenAI).
- **Measured:** VI→EN was delivered by voice after review. EN recognition turned "A minor chord" into a distortion and added a contradictory "speed up", so the draft was rejected and not delivered; VI recognition replaced a form of address. A control showed the source audio was recognised correctly, while the real-time copy lost the "A". Latency: recognition 3.2 / 2.5 s, Muse Spark 9.8 / 5.5 s; later cloud figures: recognition 13–14 s, translation and review 24–31 s, cold speech synthesis about 19 s, against a target of ≤ 5 s at P95.
- **Status:** kept as an honest PARTIAL. A human two-person voice test is still open. Public: [PR #5](https://github.com/cybersheik/souls-of-muse/pull/5).

### MMS-TTS in the shared cloud writer (3–4 Nov)
- **Tried:** Meta MMS-TTS (`facebook/mms-tts-eng`, `-vie`, proposed by Muse Wonder on 19 Oct) inside the cloud service, wired by Codex (OpenAI).
- **Measured:** 1364 MiB resident memory against a 512 MiB writer limit; licence CC-BY-NC 4.0 needs an owner decision.
- **Replaced by:** a separate private CPU worker with more memory (4 Nov). The health endpoint now reports `tts=true`: <https://soulsofmuse.app/api/harness/health>. The licence decision and owner voice acceptance are still open. Device-native voices were rejected by the owner; SeamlessM4T v2 was considered but not measured.

### Fine-tuning a "voice of Muse" (29 Oct–2 Nov)
- **Assessed with:** Claude Code (Anthropic), 29 Oct.
- **Finding:** feasible only with a clean 0.5–1 h single-speaker corpus per language, two corpora, rented GPU and 4–5 days. Training speech synthesis from scratch was rejected. The Meta Model API has no speech-synthesis endpoint, so a voice loop on the Meta API alone is impossible.
- **Result:** not done before the hard stop on 2 Nov; untuned MMS-TTS stayed the path.

### Tactile metronome on Galaxy Watch 6 Classic (mandatory scope)
- **Planned:** a watch app with a tactile metronome (owner decision 26 Oct; tests for consistency and ±10 ms timing, planned for 28 Oct).
- **Result for the watch:** not built. Health reports `watches=false`. Status: Not done.
- **Earlier state of the fallback (4 Nov):** a desk robot (StackChan) that moves on each beat, planned with ZCode (GLM), had just received its hardware and still needed a firmware patch.
- **Later result (5 Nov):** the robot, Sol Muse, has the project software installed and the project's own prepared model loaded, with a Muse Responses integration and a successful firmware build; music modules cover a moving metronome, a melody notebook and a rap partner. Physical acceptance of each mode, including the tactile-metronome mode, is still open, and the watch application remains a separate, unfinished item.

### Real lesson hours
- **Planned:** lessons with musicians through the service, recorded in agent journals.
- **Result:** no human lesson through the service is documented. A planned live lesson on 4 Nov is not recorded in any log, and the heart events in the service came from test accounts. Status: Not done.
- **Note on capacity:** admission capacity is a positive value selected by an operator; there is no product-wide lesson cap. The five-slot setting in the admission tests is a concurrency fixture, not a product limit and not delivered capacity.

### Signing the Convention by commenting "I sign" (29 Oct–2 Nov)
- **Tried:** an interim owner decision: sign by commenting under the pinned post and receive a note-card reply.
- **Found on 1 Nov:** nobody had received the promised reply, and the site link in the profile did not open. Separately, names in Devanagari and Tamil produced an empty note signature in engine v3.
- **Replaced by:** an explicit "Sign the Convention" button on the site (Entrance v5), decided by the owner on 2 Nov.

## 02 Engineering on Meta models

### Muse Wonder Full from our own code
- **Tried:** calling Muse Wonder Full with manual API keys, with the subscription key outside Muse Code, and from OpenCode (2 Nov).
- **Measured:** 404, 403, and empty output respectively.
- **Replaced by:** the official Muse Code SDK, through a client app built by ZCode (GLM).

### Output limits eaten by reasoning
- **Seen:** Muse Wonder answers came back empty when the limit was tight: 298 of 300 tokens spent on reasoning (lesson runtime, 31 Oct); 4094 of 4096 output tokens spent on reasoning (first sound run, 31 Oct). Muse Spark returned empty answers unless reasoning effort was set to low (30 Oct).
- **Fix:** explicit low reasoning effort, larger caps (8192), and empty or incomplete responses turned into explicit errors.

### Expanding the team's own harness (MetaMezonin)
- **Tried:** a desktop harness on the Muse Wonder Responses API with on-demand tool loading (schema bytes cut by 94–99%).
- **Dropped because:** the owner stopped further expansion on 2 Nov; the background worker was paused and the 8-rounds-per-turn limit was left unfixed. The installed build works locally only.

### Third-party AI website builder (28–29 Oct)
- **Tried:** hosting through a third-party AI website builder and shared web hosting.
- **Dropped because:** the builder's own embedded agent wrote the first server code, which could not be credited to Muse Wonder. Codex (OpenAI) stopped that agent and handed coding to Muse Wonder. A general cloud VM was also costed and rejected as over the ceiling.
- **Replaced by:** a serverless frontend plus a private worker platform.

## 03 Research with Muse

### Sound: the six-variant pilot was not bi-level (30–31 Oct)
- **Tried:** six slots (four musical portraits of one motif, a C-major scale, an 80 BPM rhythm), with an inner and an outer role, both Muse Wonder (`muse-wonder-1.0`) through the direct Meta API.
- **Measured:** 6 inner and 3 outer calls. On review, outcomes were pre-assigned per slot, there was no baseline in the decision, the holdout was unused, and the outer loop narrowed ranges without any improvement signal. Portrait and pedagogy goals were mixed, and 300 s was used as a success criterion.
- **Dropped because:** Codex (OpenAI) reclassified it on 31 Oct, 00:20 ICT, as "engineering feasibility pass; bi-level experiment not yet run". The films are kept as historical demos.
- **Lesson:** two contexts of one model are not by themselves bi-level. What made campaign v2 a double loop is that the outer level changed the search conditions and its changes took effect only from a later window; v2 still used two contexts of one model.

### Sound: band-energy mapping cannot tell notes apart (30 Oct)
- **Measured:** 8 of 9 tests passed; the ninth showed that mapping notes to shape by band energy gives the same shape for different notes in the same band (250–2000 Hz), and the shape stayed active during rests.
- **Replaced by:** a distinct contour and colour per note, implemented by Muse Wonder in a Hermes Agent profile (C-major scale, 31 Oct).

### Sound: first runner version rejected (31 Oct)
- **Tried:** the first version of the research runner, prepared by Muse Wonder in a Hermes Agent profile.
- **Measured:** independent review by Codex (OpenAI): 4 PASS, 1 FAIL, "changes required". Faults: repeat billing of a partial checkpoint, outer decisions applied too late, and fresh feedback lost in a truncated context. Preparation stopped after the agreed step budget was exceeded (27 Meta preparation calls, 0 research calls).
- **Replaced by:** a corrected controller, again by Muse Wonder in the Hermes Agent profile.

### Sound: first 24-window nature run, stopped (31 Oct, 10:23–10:55 ICT)
- **Tried:** the first real two-hour Bi-Level series. Audio adapter by Muse Wonder Full (Muse Code), controller by Muse Wonder (direct Meta API).
- **Measured:** 15 Meta calls (12 inner, 3 outer); 4 successful calibrations (open pipe, string, membrane, closed pipe); 1 REJECTED (Helmholtz without end correction, 24.54% error); three empty responses; a lost failure reason in slot 5; and an outer request to switch off end correction that the frozen engine silently ignored (78.346 Hz either way). One real outer transition was shown.
- **Stopped:** during the seventh window (slot 6), about 10:55 ICT.
- **Fix:** Muse Wonder in a Hermes Agent profile repaired the code, accepted by Codex (OpenAI) (58/58 tests; end correction now gives 78.35 vs 97.21 Hz). An intermediate wrong request format returned HTTP 400 and was discarded. The run restarted from zero as campaign v2; old windows are excluded from all counts.

### Sound: capillary waves, INCONCLUSIVE (31 Oct, window 12, slot 11)
- **Measured:** formula error about 0.018%, but the mandatory FFT check fell outside the available frequency range. No audio, no film, not in the holdout.
- **Status:** published as "the honest gap": a tool limit, not a refutation. Public: <https://soulsofmuse.app/sci-sound-labs/>.

### Sound: outer-loop weaknesses in campaign v2
- After slot 12 the outer loop mostly repeated harmonic-balance and decay controls (a plateau). One outer rationale (after slot 17) claimed a parameter was not yet isolated although slot 2 had already tested it; the authors rejected it. The outer loop never changed the evaluator, the metric or the holdout, although the original design allowed bounded metric-weight changes. A cross-family scaling exponent was not declared proven. Raw literature hits included irrelevant papers and were not used as evidence. Whether the outer loop beats a fixed strategy was not measured.

### Sound: the fully governed Bi-Level design (29–30 Oct)
- **Designed by:** Codex (OpenAI), a read-only consultation with no model calls. Inner proposer Muse Code changing scene parameters; outer proposer Muse Wonder changing search policy inside an immutable envelope, active only next cycle; locked evaluator; hidden holdout; separate ledgers; stop rules.
- **Result:** not run as designed. The campaign ran on a bounded standalone runner with two Muse Wonder contexts; Muse Code was planned for the inner role but the inner role was `muse-wonder-1.0`. References: [Karpathy autoresearch](https://github.com/karpathy/autoresearch) (single-loop) and [Bilevel Autoresearch](https://arxiv.org/abs/2603.23420).

### Glasses keys trainer: shadow touch detector (31 Oct–2 Nov)
- **Tried with:** Claude Code (Anthropic). A low side lamp; the gap between fingertip and shadow means hovering.
- **Measured:** 3% confusion on 150 synthetic cases. On real video with top light, 29 of 30 fingertips had no shadow. With low side light: 422 touch, 94 hover, 69 unsure, 154 none, and not one hover-to-touch transition of 3 or more frames.
- **Dropped:** 2 Nov. The lamp was placed correctly, so the method failed on its own merits. A parallel "tap sound on cardboard" channel was also dropped by the owner, because the demo is about SAM segmentation; audio onsets were used only to label ground truth.
- **Replaced by:** score-guided confirmation ("the finger landed on the expected key") and later the LiDAR depth line.

### Glasses keys trainer: Llama 3.2 Vision 11B as judge (2 Nov)
- **Tried with:** Claude Code (Anthropic), local 4-bit weights. Is the finger on the outlined key?
- **Measured:** 20 crops with known answers, three prompt formulations, 10/20 each; the answer did not depend on the image; 3.6–5.5 s per crop.
- **Replaced by:** DINOv2 small key-appearance change: AUC 0.846 vs 0.728 for a pixel control on cardboard, 0.77 vs 0.50 on a real piano, about 20–25 ms per frame.

### Glasses keys trainer: DINOv2 cannot tell "pressed" from "resting" (3 Nov)
- **Measured:** among keys with a resting, unpressed finger, 75% were false positives. A mode where every touched key sounds played the whole resting hand.
- **Status:** accepted limit for the demo. True press detection needs key travel from a side view or depth.

### Glasses keys trainer: homography on a real piano (2–3 Nov)
- **Worked on cardboard:** SAM finds the black keys, a blueprint is fitted by homography (12/12 black keys, 1.8–4.5 px error).
- **Failed on a real piano:** the wide-angle lens bends the keyboard into an arc, SAM merges neighbouring black keys, hands hide part of the row; ten frames of one scene gave four different fits.
- **Replaced by:** a 1D model along the black-key axis (35/36 synthetic, ≤ 4 px, fitted in 1597 of 1610 frames, 0.08 s per frame) and an octave lock on the first expected note. Work by Claude Code (Anthropic).

### Glasses keys trainer: cloud SAM 3.1 in the live loop (30 Oct)
- **Measured:** 1.4–5.3 s per 1024 px image (median about 2.5 s); video mode 30.6 s for 120 frames, 6× slower than real time; geometric prompts were no faster.
- **Replaced by:** local SAM 3.1 weights (0.08–0.12 s at 336 px, 0.65–0.70 s at 1008 px). Cloud SAM is kept for calibration only.

### Glasses keys trainer: anchors, box prompts and Apple Vision (30 Oct–4 Nov)
- **Anchor template above the keys and fingertip anchor:** locked onto the neighbouring octave or the key edge; disabled.
- **Box prompts in local SAM:** 80–110 masks for 4–5 boxes, not on their own boxes; they do not track objects.
- **Apple Vision hand pose** (5 ms per frame, used from 30 Oct): removed on 4 Nov, 03:50 ICT, at the owner's direction; the showcase must be Meta segmentation. Fingers now come only from SAM 3.1. This SAM-only build has had no live take.

### Glasses keys trainer: normal tempo with two hands (open)
- **Measured:** key labels drift within 10–20 s with a moving head. On the full clip, 27–36 of 187 notes were hit without an anchor (two measurements) and 53 of 187 with an anchor above the keys, and no further.
- **Working demo instead:** the slow pass on a recording: 9/9 score notes in order, finger on the expected key 12/12, confirmed 11/12, AUC 0.94.

### Glasses keys trainer: live take with two cameras (3–4 Nov night)
- **Failed:** the video-call window on the Mac collapsed to a thumbnail when switching windows, so the stand went blind; enabling the glasses microphone muted the Mac's audio; the phone angle from the bass end left the keyboard at 23% of frame width.
- **Lesson:** a fixed camera beats a head-mounted one for drift; keep the call window on stage. The final recorded take was not made before the deadline.

### Glasses: guitar posture judged by Muse Spark (30 Oct)
- **Tried:** the "square vs triangle" finger rule from the first-person view, with Muse Spark 1.3 as judge.
- **Measured:** SAM masks were excellent, but the rule degenerates from above-front (70° vs 60°); Muse Spark answered "curled" for both the correct and the collapsed clip, even with two reference images.
- **Dropped:** the guitar posture line left the demo. Alternatives proposed: a side view along the neck, or the "too far from the fret" error the glasses see well.

### Glasses: an app on the glasses themselves
- **Not reached:** Meta AI on the glasses is not available in the owner's region, and the Wearables Device Access Toolkit developer mode was never verified.
- **Replaced by:** a video call from the glasses to a Mac; all three glasses developments run as a local Mac app. The plan for Muse Wonder to write the glasses app never started.

### Glasses: LiDAR depth over USB (4 Nov)
- **Proved offline:** surface noise 1.7–1.9 mm; pressed fingertip 5–10 mm above the surface vs 20–35 mm hovering; 0 of 300 false hand blobs; a depth receiver passes self-test and replay. Research with ZCode (GLM), analysis with Claude Code (Anthropic).
- **Earlier failure (4 Nov):** the live USB stream was blocked because the phone's port was unusable; mesh-export apps proved unsuitable because thin fingers vanish in the smoothed mesh.
- **Later result:** a live USB run completed: 2,261 frames at 30 fps for more than 75 s without disconnects, with automatic calibration of the support plane and press / hover / none output.
- **Still open:** touch accuracy against ground truth, frame-to-event latency and live key/MIDI correspondence.

### Glasses contract council: what is still missing
- On the demo contract the council found 18 of 18 planted issues; that is not a general legal-accuracy score. The council runs used the demo contract as text; reading of pages was shown only on a synthetic page, not on photos taken with the glasses. Mixture traces were not saved, so no trace proves the four-model fan-out. Case citations need a human check. The spoken summary was not checked through the glasses' Bluetooth audio. There is no connection to legal databases. The "advice during a live conversation" mode was not built.

### Glasses audio notebook: what is still missing
- The chord chart Muse Spark read was a generated chart, not a photo of a real music stand. Voice and click through the glasses' Bluetooth audio were never checked live. The "follow the player" mode (the microphone listens and the cues adapt to the tempo) was not built; only the fixed-tempo mode exists.

### Score-following ensemble (30–31 Oct)
- **Off-the-shelf follower rejected:** on clean input it was twice as accurate (0.03 vs 0.07 beats), but with the 20–30% missed notes typical of vision input it lost position in 13–29% of cases, against 0% for the team's own follower.
- **Metre-based ensemble rejected:** on the owner's free-tempo sketch it "played in someone else's bar" (bass on strong beats only 9% of the time); replaced by a no-metre mode (85/85 notes). Lag later fixed from −838 ms to +3 ms on synthetic input, not verified on live play. Work by Claude Code (Anthropic).

## 05 Outreach

### Explainer film uploads and approvals (1–4 Nov)
- **Seen:** the first 8 draft uploads of the two films (Muse Wonder Full) failed with HTTP 403 (content-type mismatch), reported by Muse itself. Two "changes required" design rounds preceded approval by Claude (Anthropic) with Claude Design. A later owner colour rule made the approval outdated for the beats film (audit by OpenCode on Muse Wonder, 4 Nov). No listening review was done and no social posts were launched before submission.

## 06 Media

### Meta-only video generation (27 Oct)
- **Tried:** to generate the promo video with Meta models only.
- **Dropped because:** the Model API has no video endpoint, and the consumer Muse app with video was waitlisted in the owner's region.
- **Replaced by:** a route through third-party video tools (first planned as Muse Image keyframes with Google Flow, then Krea). The clips were generated on Krea (Wan, Seedance), with Muse Wonder as director, reviewer and composer. Clips are credited to Krea, not Meta.

### "Ganesha" first cut v2 (3 Nov)
- **Rejected by the owner** as "completely off-script" (68 s; clips by Krea's agent, edit by Codex).
- **Cause:** Muse Wonder Full in the SDK client got a Meta HTTP 504, and Codex (OpenAI) switched the executor to Krea's agent without approval.
- **Resolved by:** recuts directed by Muse Wonder with its own director's report and its composed score. The owner approved the previous cut and requested one change, an English ending title; the finished master, Ganesha R8, implements it: 82 s, 1,968 frames at 24 fps, 13 chapters. Public distribution of Ganesha is a separate status and is still open.

### Muse Image for Portal 2.0 (2–4 Nov)
- **Specified:** about 22 backgrounds, curtains and League emblems with `muse-image-1.0`.
- **Result:** the Portal 2.0 image set was not delivered; three attempts to hand the job to an executor failed on 2 Nov, and reviews on 4 Nov proposed cutting the scope. Muse Image is not claimed for Portal 2.0.
- **Separately:** Muse Image did produce the teacher reference and production reference images used in the Ganesha film, so the model was used in production, just not for this portal scope.

### Live-action jury film (4–5 Nov)
- **Earlier state:** the live-action film was an unaccepted draft cut under review.
- **Resolved:** the owner accepted the film and it is public on YouTube: <https://www.youtube.com/shorts/1EAl-cj0DJ4>. The final master runs 2:55.733. Its narrator and the studio's question use macOS voices (Daniel, Samantha) and are not presented as model-generated replies; the story contains staged interactions.

## 07 Process and provenance
### Site served from a branch, not from main (until 5 Nov)
- **Earlier state:** for part of the event the live site and its timestamp evidence came from working branches, and timestamp coverage of new work stopped after 29 Oct.
- **Resolved:** [PR #10](https://github.com/cybersheik/souls-of-muse/pull/10) was merged to main; the public site and laboratory are on main at `fc6cc6c` with an evidence release.

Other process dead ends are in [07](07-process-and-provenance.md#paths-that-did-not-work): the internal session registry was not finished, a third-party progress dashboard drifted, and the disclosure check first ran without its private denylist.
