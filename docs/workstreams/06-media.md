# 06. Media

## Why it matters
The demo video carries a quarter of the score, and the community grows through what people can see and hear.

Status vocabulary on this page: **Live** (works publicly; "Working" in DISCLOSURE_POLICY §5), **Finished** (completed master), **Prototype**, **Offline-tested**, **Plan** (designed or planned, not built), **Not done**. Public availability is stated separately from completion.

## During the event
| Item | Status | Made with | Evidence |
|---|---|---|---|
| Final live-action film | Finished, accepted by the project owner and public on YouTube (2:55.733) | Live camera footage with performing musicians, 3 Nov 2026; the real TopDog Colors studio window; edit by Codex (OpenAI); English script drafts by Grok-based bots (xAI); product screens filmed from the site and from screens prepared for the shoot. Staged voices, disclosed: the added narration is macOS Daniel and the studio's spoken question is macOS Samantha; neither is a model reply | https://www.youtube.com/shorts/1EAl-cj0DJ4 |
| Ganesha (short film; story and script by the project owner) | Finished: master R8, 82 s, 13 chapters, 1,968 frames at 24 fps. The owner's single requested change (English ending title) is done. Public: [https://github.com/cybersheik/souls-of-muse/releases/tag/jury-media-20261105](https://github.com/cybersheik/souls-of-muse/releases/tag/jury-media-20261105) (download https://github.com/cybersheik/souls-of-muse/releases/download/jury-media-20261105/ganesha.mp4, 62,216,903 bytes, SHA-256 c14c8f9e4386bdb47253e6c3307242c4549d466400134a73442720961db284ac) | Screenplay and storyboard: **Muse Wonder Full** (muse-wonder-full-1.0, through the subscription workflow). Direction, shot and revision review, director's report and the composed score: **Muse Wonder** (muse-wonder-1.0). Teacher reference and production reference imagery: **Muse Image** (muse-image-1.0). Earlier screenplay revision and review: MetaMezonin's resident agent (running Muse Wonder). Video shots: **Krea** models, including Seedance 2 mini (ByteDance) and Wan (Alibaba), not Meta. Editing, score performance and mix: Codex (OpenAI) and local tools | Production records with completed model outputs, image receipts, score data, MIDI and checksummed masters are kept with the project; no public file link yet |
| Educational shorts on musical intervals and beats | Live on the site; not posted to social channels | **Muse Wonder Full** (muse-wonder-full-1.0) in Meta's Muse Code terminal; design review by Claude (Anthropic, in Cowork) with Claude Design; fact and audio check and caption copy-edit by Codex (OpenAI) | https://soulsofmuse.app/sci-sound-labs/ · [intervals-en.mp4](https://soulsofmuse.app/sci-sound-labs/assets/video/intervals-en.mp4) |
| Portal 2.0 design image set: backgrounds, curtains, League emblems | Not delivered (separate scope from the film work) | Muse Image (planned) | None |

### Educational shorts in brief
Two 16-second vertical films (1080×1920), English for publication; Russian versions exist for owner review only.
- **A fifth, made visible:** tones of 440 and 660 Hz draw a closed Lissajous figure, with a 4:3 interval shown as a control.
- **Beats you can hear and see:** 440 Hz against 443, 441 and 440 Hz gives a pulse of 3, 1 and 0 per second.

The audio is synthetic sine tones, checked numerically (spectrum and envelope rate). Nobody has done a human listening review yet. The films illustrate known physics; they are not a new research result. The research behind them is in [03](03-research-with-muse.md).

## Who did the work
Every task in the team tracker is formally assigned to the project owner. This table names who actually did each part.

| Part | Meta model | Other agent (tool or role) | Non-Meta tools | Owner |
|---|---|---|---|---|
| Ganesha: story and script | — | — | — | Wrote the story and script |
| Ganesha: screenplay and storyboard | **Muse Wonder Full** (muse-wonder-full-1.0) through the subscription workflow, in the TopDog Colors studio client | Earlier SDK client integration by ZCode (GLM) | — | — |
| Ganesha: direction, shot and revision review, director's report | **Muse Wonder** (muse-wonder-1.0) in Meta's Muse Code terminal, directing Krea through its connector | — | — | Rejected the 68 s cut; approved the following cut and asked for one change (English ending title), done in R8 |
| Ganesha: score composition | **Muse Wonder** composed the score: six melodic cells, harmony, percussion patterns and orchestration, kept as score data and editable MIDI | — | — | — |
| Ganesha: earlier screenplay revision and review | **Muse Wonder** inside MetaMezonin (its resident agent) | — | — | — |
| Ganesha: teacher reference and production reference imagery | **Muse Image** (muse-image-1.0) | — | — | — |
| Ganesha: video shots | none | First 11-clip plan by an agent (model not recorded) | Krea: Seedance 2 mini, Wan | — |
| Ganesha: editing, score performance, mix | — | Codex (OpenAI) | FFmpeg and local tools | — |
| Educational shorts | **Muse Wonder Full** (muse-wonder-full-1.0) made storyboard, render code, films and captions, and posted its own drafts for review | Design review: Claude (Anthropic, in Cowork) + Claude Design; fact check and caption copy-edit: Codex (OpenAI); later audit: OpenCode (whose 4 Nov sessions ran Muse Wonder) | — | Asked for the films |
| Final live-action film | Muse appears in the film as the product | Edit: Codex (OpenAI); scene-to-product map: Claude (Anthropic, in Cowork); camera storyboard: Grok Bot (xAI); English script drafts: Grok-based bots (xAI) | Camera footage; macOS voices Daniel (narration) and Samantha (studio question) | Wrote the scenario, directed the shoot and accepted the final film |
| Portal 2.0 design image set (Muse Image) | Not delivered | — | — | — |

**Muse credit, stated separately:** for Ganesha, Muse Wonder Full wrote the screenplay and storyboard; Muse Wonder directed, reviewed shots and revisions, wrote the director's report and composed the score; Muse Image created the teacher reference and production reference imagery. Muse Wonder Full also made both educational shorts (storyboard, render code, films and captions; design approval and caption copy-editing were done by non-Meta agents). No Meta model generated video frames: the Meta Model API has no video endpoint, so all video shots come from Krea models.

## Paths that did not work
- **Meta-only video.** The Meta Model API offers chat, responses, images, audio and segmentation, but no video. The consumer Muse app with short video was waitlisted in the owner's region on 27 Oct 2026. The route first switched to Muse Image keyframes with Google Flow (Google), then to Krea models for the shots.
- **Ganesha, first cut.** When Muse Wonder Full returned an HTTP 504 error in the studio's SDK client, Codex (OpenAI) switched clip making to Krea's own agent without Muse direction and without the owner's approval. The owner rejected the resulting 68 s cut on 3 Nov as off-script. The film was redone under Muse Wonder direction: 72, 74 and 78 s versions, then the 82 s cut with a new Muse Wonder score, and finally master R8 with the English ending title.
- **Educational shorts.** The first eight draft uploads failed (HTTP 403, content-type mismatch); Muse Wonder Full reported this itself. Two design rounds returned "changes required" before approval on 2 Nov. A later owner colour rule (gold and red only as accents) made the approval of the beats design outdated. A listening review has not been done.
- **Muse Image for the portal.** About 22 images (backgrounds, curtains, doors, League emblems) for Portal 2.0 were specified but not delivered: no agent with the API key was assigned after three failed attempts on 2 Nov, and reviews on 4 Nov proposed cutting the scope. This is separate from the film, where Muse Image did produce the teacher reference and production reference imagery.

## Not claimed
- No Meta model generated any video frames; video shots are Krea output (models including Seedance 2 mini and Wan).
- Muse Image is not used for portal design material; the Portal 2.0 image set was not delivered.
- Ganesha's finished master is public as a GitHub release asset: https://github.com/cybersheik/souls-of-muse/releases/tag/jury-media-20261105
- The live-action film contains staged interactions; it is not end-to-end acceptance evidence for every feature it shows. Its narrator (macOS Daniel) and the studio's spoken question (macOS Samantha) are not model-generated replies.
- The educational shorts are on the site only; they were not posted to social channels and were not reviewed by ear.
- The live-action film does not show a working watch app; the watch application is unfinished. The Sol Muse robot's individual musical modes, including the tactile metronome, are still awaiting physical acceptance.
- Glasses scenes, if shown, are a local Mac prototype that receives frames from the glasses over a video call, not an app running on the glasses.
- Product screens prepared for filming are not live features unless labelled as such in the video.

## Rights and origin
| Asset | Origin | Licence / basis |
|---|---|---|
| Final live-action film | Live footage of performing musicians, 3 Nov 2026; edited by Codex (OpenAI); macOS system voices Daniel and Samantha for the staged narration and studio question | Own footage, accepted and published by the project owner; consent of every person shown and rights to the music performed fall under policy §3.5 |
| Ganesha: story, script | Project owner | Own work |
| Ganesha: video shots | Krea models, including Seedance 2 mini (ByteDance) and Wan (Alibaba), team subscription | Krea terms and model terms for public promotional use: to be confirmed |
| Ganesha: score | Composed by Muse Wonder (score data and editable MIDI); performed and mixed with Codex (OpenAI) and local tools | Own work; instrument and sample sources to be confirmed |
| Ganesha: reference imagery | Muse Image (teacher reference and production references) | Own work; Meta model terms |
| Educational shorts (2 films) | Muse Wonder Full; synthetic sine tones | Own work; fonts below |
| Sci Sound Labs films and 24 cards | Research loop: two-level (Bi-Level AutoResearch) loop with both research roles run by Muse Wonder (muse-wonder-1.0); renderer and media export by Muse Wonder Full (muse-wonder-full-1.0); direction and independent acceptance by Codex (OpenAI); see [03](03-research-with-muse.md) | Own work |
| Sci Sound Labs 39-second performance loop | Three stock clips from Pexels and Pixabay, authors credited on the page; the edit is credited on the page to "Sci Sound Labs" (the agent behind the edit is not recorded) | Pexels and Pixabay licences; not claimed as research |
| Starting-prototype images on Sci Sound Labs | Screens of the Kimi-built "Sound Made Visible" prototype ([link](https://visionsound.ok.kimi.link/)) | Credited to Kimi (Moonshot AI) |
| Community marks: lyre emblem, seal, medals, honours, Muse badge and disc mark | Generated by Codex (OpenAI) with the image generator built into Codex ("ImageGen"), 26 Oct 2026; not a Meta model | OpenAI terms for generated images: to be confirmed |
| Muse mascot (blue Muse in a coral beret) | Pre-event project asset | Origin and basis to be recorded in its baseline file |
| Museum images of the Muses | The Met, Cleveland Museum of Art, Vatican Museums, Smithsonian | Linked as references only; not reproduced |
| Fonts | Cormorant Garamond, Inter, JetBrains Mono, Noto Music, Noto Serif JP and KR via Google Fonts | SIL Open Font License 1.1 |
| Icons | Phosphor Icons | MIT |
| Notation renderer library | abcjs 6.7.2 | MIT (licence file shipped with the library) |
| Real-time media client library | LiveKit client | Apache License 2.0 (licence file shipped with the library) |

Media made by tools other than Meta models is labelled with the real tool and checked against its terms. Historical artworks, music and fonts need a public-domain or licence basis (policy §3.6).
