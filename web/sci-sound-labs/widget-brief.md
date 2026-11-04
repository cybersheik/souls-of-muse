# Mini-Widget Brief: a "See the Sound" starter for the portal

*Handoff brief for Claude Design · Sci Sound Labs research team, with Meta Muse · This document specifies a proposal. No widget has been built yet.*

## 1. Starting point — the supplied Kimi-built prototype, credited

The idea begins with the Kimi-built starting prototype supplied to the project,
**Sound Made Visible, created with Kimi** (https://visionsound.ok.kimi.link/),
externally hosted and working today via the link. As first observed, it offered
three modes — Sound Sculpture, Wave Explorer and Resonance Patterns — and its
current landing offers curated built-in tones (a 220 Hz tone, a rich tone, a
pulse rhythm and a voice-like hum) alongside microphone and file options. In our
historical checks only the built-in tones were exercised. Keep the Kimi credit
and link attached wherever the prototype is shown. Where supplied source from
the prototype is available to the project, design may propose adapting it, with
attribution and any required notices preserved; whether an embedded live form
is compatible with the portal (technically and for privacy) still needs to be
checked before it is promised — the linked preview works now.

## 2. What we ask design to explore

A small, self-contained starter widget for the Souls of Muse portal that lets a
visitor *see* three contrasting sounds and understand, at a glance, what changed
between them. Think of it as a doorway into the Sci Sound Labs research page —
inviting, finite, honest about being a synthetic model.

**Embedding caveat (please design around it).** Whether the externally hosted
prototype can be embedded (for example in an iframe) has not been tested, and
this brief does not promise that embedding works. The safe default presentation
is a linked preview — screenshot, short caption, credit line, and an outbound
link that opens the prototype in a new tab — exactly as the research article
already does. Any future embedded variant requires a separate compatibility and
privacy check by the portal team before it is promised in copy or layout.

## 3. Suggested supported first version (v1 scope)

- **Three built-in tone presets only**, mirroring the spirit of the starting
  prototype: a pure tone, a richer tone (added harmonics), and a gentle pulse.
  Each preset drives one clear visual behaviour so the contrast is legible.
- **Sound is opt-in.** The widget loads silent and still (poster state).
  A single "Play" action starts sound and motion together.
- **Pause and reset** are always visible; pause freezes both sound and form.
- **Text alternative** under the canvas, one sentence per preset, e.g.
  "Richer tone: same pitch, more harmonics — the rosette gains petals."
- **Link fallback:** if audio or graphics are unavailable, the widget degrades
  to the linked preview of the prototype plus a link to the research page.
- **No microphone, no file upload in v1.** Those options exist on the hosted
  prototype, but for our portal they are a later, separately reviewed step:
  they raise permission, privacy and support questions that v1 deliberately
  avoids.

## 4. Implementation boundaries for whoever builds it

- Build on sources the project can support: our own existing renderer, and —
  where the supplied Kimi-built prototype source is available to the project —
  adaptation of that source with Kimi attribution and any required notices
  preserved. Confirm support with the portal team either way. Do not build a
  new arbitrary-audio analysis pipeline under this brief — v1 knows its three
  presets in advance, like our note-aware scale knew its score.
- Respect `prefers-reduced-motion`: show the poster state and require an
  explicit press to animate.
- Mobile-first: legible at 390 px width, no horizontal scrolling, touch targets
  at least 44 px, captions in English.
- Visual language: Nocturne ground with gold and lavender accents, matching the
  Sci Sound Labs page; one quiet line under the widget reads "Synthetic model
  demonstration".

## 5. What success looks like (and what it is not)

Success: a visitor presses play once, switches between the three presets, and
can say in their own words what changed — pitch same, tone richer; pulse
faster or slower. That is a design goal to be checked with real people later.
This widget is not a tuner, not a pitch recogniser, not a promise about the
hosted prototype's privacy or network behaviour, and not evidence of learning
benefit. Copy must not claim any of those. (In this brief, "the prototype"
means the externally hosted Kimi-built starting prototype supplied to the
project and linked in section 1.)

## 6. Open questions for the design review

1. Where does the widget sit best — the Sci Sound Labs page only, or also a
   quiet corner of the welcome/lesson surfaces — without disturbing accepted
   layouts?
2. One canvas with three preset chips, or three small cards side by side?
3. Should the linked preview of the Kimi prototype sit directly beneath the widget
   ("Where this started") to keep credit and story together?

*Prepared as a handoff brief. Build, embedding tests and portal placement are
separate, later decisions.*
