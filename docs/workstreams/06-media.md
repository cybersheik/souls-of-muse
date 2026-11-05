# 06. Media

## Why it matters
The demo video carries a quarter of the score, and the community grows through what people can see and hear.

Status vocabulary on this page: **Live** (works publicly; "Working" in DISCLOSURE_POLICY §5), **Prototype**, **Offline-tested**, **Plan** (designed or planned, not built), **Not done**.

## During the event
| Item | Status | Made with | Evidence |
|---|---|---|---|
| Final demo video | Prototype (draft cut, 2:36, awaiting owner review and one pickup shot) | Live camera footage with performing musicians, 3 Nov 2026; edit by CX1 (Codex, OpenAI); English script drafts by GB1 and GBH (Grok, xAI); product screens filmed from the site and from screens prepared for the shoot | Public link to be added when the final cut is accepted (≤ 3:00) |
| Promo video (script by the project owner) | Prototype (current cut 82 s, awaiting owner acceptance; earlier 68 s cut rejected) | Direction, contact-sheet review, music decisions and director's report: **Muse Wonder** (muse-wonder-1.0 in Meta's Muse Code terminal; muse-wonder-full-1.0 through an SDK client on the official Muse Code SDK). Script review: MZM (the team's own desktop harness MetaMezonin, running Muse Wonder). Video clips: **Krea** models, including Seedance 2 mini (ByteDance) and Wan (Alibaba), not Meta. Edit, score performance and mix: CX1 (Codex, OpenAI). | Not public yet |
| Educational shorts on musical intervals and beats | Live on the site; not posted to social channels | **Muse Wonder Full** (muse-wonder-full-1.0) in Meta's Muse Code terminal; design review by DW1 (Claude in Cowork, Anthropic) with Claude Design; fact and audio check and caption copy-edit by CX1 (Codex) | https://soulsofmuse.app/sci-sound-labs/ · [intervals-en.mp4](https://soulsofmuse.app/sci-sound-labs/assets/video/intervals-en.mp4) |
| Generated design material: backgrounds, curtains, League emblems | Not done | Muse Image (planned, never run) | None |

### Educational shorts in brief
Two 16-second vertical films (1080×1920), English for publication; Russian versions exist for owner review only.
- **A fifth, made visible:** tones of 440 and 660 Hz draw a closed Lissajous figure, with a 4:3 interval shown as a control.
- **Beats you can hear and see:** 440 Hz against 443, 441 and 440 Hz gives a pulse of 3, 1 and 0 per second.

The audio is synthetic sine tones, checked numerically (spectrum and envelope rate). Nobody has done a human listening review yet. The films illustrate known physics; they are not a new research result. The research behind them is in [03](03-research-with-muse.md).

## Who did the work
Every task in the team tracker is formally assigned to the project owner. This table names who actually did each part.

| Part | Meta model | Agent (callsign → model behind it) | Non-Meta tools | Owner |
|---|---|---|---|---|
| Promo film: story and script | — | — | — | Wrote the story and script |
| Promo film: direction, contact-sheet review, music decisions, director's report | **Muse Wonder** (muse-wonder-1.0; about 100 Muse Code sessions on 4 Nov directing Krea through its connector) and **Muse Wonder Full** (muse-wonder-full-1.0) through an SDK client | SDK client built by DZ1 (ZCode on GLM) | — | Rejected the 68 s cut; acceptance of the 82 s cut pending |
| Promo film: script v3 review | **Muse Wonder** inside MZM (MetaMezonin harness) | — | — | — |
| Promo film: video clips | none | First 11-clip plan by TUZ (model not confirmed) | Krea: Seedance 2 mini, Wan | — |
| Promo film: edit, score performance, mix | — | CX1 (Codex, OpenAI) | FFmpeg | — |
| Educational shorts | **Muse Wonder Full** (muse-wonder-full-1.0) made storyboard, render code, films and captions, and posted its own drafts for review | Design review: DW1 (Claude in Cowork) + Claude Design; fact check and caption copy-edit: CX1 (Codex); later audit: OC1 (OpenCode, whose 4 Nov sessions ran Muse Wonder) | — | Asked for the films |
| Final demo video | Muse appears in the film as the product | Edit: CX1 (Codex); scene-to-product map: DW1 (Claude in Cowork); camera storyboard: Grok Bot (xAI); English script drafts: GB1 and GBH (both Grok bots, xAI); script formatting: MC1 (model not confirmed) | Camera footage | Wrote the scenario and directed the shoot |
| Portal design material (Muse Image) | Muse Image: not run | — | — | — |

**Muse credit, stated separately:** Meta Muse models directed and reviewed the promo film and decided its music, wrote its director's report, and made both educational shorts (storyboard, render code, films and captions; design approval and caption copy-editing were done by non-Meta agents). No Meta model generated video frames: the Meta Model API has no video endpoint, so all promo clips come from Krea models.

## Paths that did not work
- **Meta-only video.** The Meta Model API offers chat, responses, images, audio and segmentation, but no video. The consumer Muse app with short video was waitlisted in the owner's region on 27 Oct 2026. The route first switched to Muse Image keyframes with Google Flow (Google), then to Krea models for the clips.
- **Promo film, first cut.** When Muse Wonder Full returned an HTTP 504 error in the SDK client, CX1 (Codex) switched clip making to Krea's own agent without Muse direction and without the owner's approval. The owner rejected the resulting 68 s cut on 3 Nov as off-script. The film was redone under Muse Wonder direction: 72, 74 and 78 s versions, then the current 82 s cut with a new Muse Wonder score.
- **Educational shorts.** The first eight draft uploads failed (HTTP 403, content-type mismatch); Muse Wonder Full reported this itself. Two design rounds returned "changes required" before approval on 2 Nov. A later owner colour rule (gold and red only as accents) made the approval of the beats design outdated. A listening review was never done.
- **Muse Image for the portal.** About 22 images (backgrounds, curtains, doors, League emblems) were specified but never generated: no agent with the API key was assigned after three failed attempts on 2 Nov, and reviews on 4 Nov proposed cutting the scope. Muse Image was exercised only in test generations inside the MZM harness; none is used in the product.

## Not claimed
- No Meta model generated any video frames; promo clips are Krea output (models including Seedance 2 mini and Wan).
- Muse Image is not used for portal design material.
- The final demo video and the promo film are not public at the time of writing; the promo film is not owner-accepted.
- The educational shorts are on the site only; they were not posted to social channels and were not reviewed by ear.
- The demo video does not show a working watch app or tactile metronome; neither exists at submission.
- Glasses scenes, if shown, are a local Mac prototype that receives frames from the glasses over a video call, not an app running on the glasses.
- Product screens prepared for filming are not live features unless labelled as such in the video.

## Rights and origin
| Asset | Origin | Licence / basis |
|---|---|---|
| Final demo video | Live footage of performing musicians, 3 Nov 2026; edited by CX1 (Codex) | Own footage; documented consent of every person shown (faces and voices) and rights to the music performed must be on file before publication (policy §3.5); people without documented consent are cut or not identifiable |
| Promo film: story, script | Project owner | Own work |
| Promo film: video clips | Krea models, including Seedance 2 mini (ByteDance) and Wan (Alibaba), team subscription | Krea terms and model terms for public promotional use: to be confirmed |
| Promo film: score | Music decisions by Muse Wonder; performed and mixed by CX1 (Codex) | Own work; instrument and sample sources to be confirmed |
| Educational shorts (2 films) | Muse Wonder Full; synthetic sine tones | Own work; fonts below |
| Sci Sound Labs films and 24 cards | Research loop: two-level (Bi-Level AutoResearch) loop with both research roles run by Muse Wonder (muse-wonder-1.0); renderer and media export by Muse Wonder Full (muse-wonder-full-1.0); direction and independent acceptance by CX1 (Codex); see [03](03-research-with-muse.md) | Own work |
| Sci Sound Labs 39-second performance loop | Three stock clips from Pexels and Pixabay, authors credited on the page; the edit is credited on the page to "Sci Sound Labs" (the agent behind the edit is not recorded) | Pexels and Pixabay licences; not claimed as research |
| Starting-prototype images on Sci Sound Labs | Screens of the Kimi-built "Sound Made Visible" prototype ([link](https://visionsound.ok.kimi.link/)) | Credited to Kimi (Moonshot AI) |
| Community marks: lyre emblem, seal, medals, honours, Muse badge and disc mark | Generated by CX1 (Codex, OpenAI) with the image generator built into Codex ("ImageGen"), 26 Oct 2026; not a Meta model | OpenAI terms for generated images: to be confirmed |
| Muse mascot (blue Muse in a coral beret) | Pre-event project asset | Origin and basis to be recorded in its baseline file |
| Museum images of the Muses | The Met, Cleveland Museum of Art, Vatican Museums, Smithsonian | Linked as references only; not reproduced |
| Fonts | Cormorant Garamond, Inter, JetBrains Mono, Noto Music, Noto Serif JP and KR via Google Fonts | SIL Open Font License 1.1 |
| Icons | Phosphor Icons | MIT |
| Notation renderer library | abcjs 6.7.2 | MIT (licence file shipped with the library) |
| Real-time media client library | LiveKit client | Apache License 2.0 (licence file shipped with the library) |

Media made by tools other than Meta models is labelled with the real tool and checked against its terms. Historical artworks, music and fonts need a public-domain or licence basis (policy §3.6).
```
