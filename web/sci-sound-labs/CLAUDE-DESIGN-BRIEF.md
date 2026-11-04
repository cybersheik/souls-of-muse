# Design Brief — Sci Sound Labs: Sound Made Visible

*For Claude Design · Sci Sound Labs research team, with Meta Muse · English edition*

## What this package is

A complete, self-contained public section for the Souls of Muse portal:
a research article (`index.html` / `article.md`), a printable jury report
(`jury-report.html` / `jury-report.md`), an applied performance section, and a
mini-widget proposal (`widget-brief.md`). Everything is in English. Some
archival media keeps its historical on-screen labels from before this English
edition; those items are explicitly marked as historical originals and always
carry English captions.

## The complete collection — seven catalogue groups (18 films, 24 cards)

1. **Where it started: a live sound lab.** Screenshots and link for the
   Kimi-built starting prototype supplied to the project, *Sound Made Visible,
   created with Kimi* (https://visionsound.ok.kimi.link/): Sound Sculpture,
   Wave Explorer (pure and rich 440 Hz tones), Resonance Patterns. Credited;
   shown as a linked preview.
2. **Musical portrait of a melody.** The six early pilot films (12 s each):
   quiet, energetic, contrast-and-clarity and sparks portraits of one motif,
   C-major solfège, and an 80 BPM rhythm study — plus the four-portrait
   comparison film and card. Status: engineering feasibility; their visible
   weakness (notes hard to tell apart) motivated group 3.
3. **Note = colour + shape.** The C-major scale in two versions, before and
   after: the final note-aware film (15 s, eight distinct note-states, honest
   fades on rests), the earlier version for comparison, and the eight-note
   alphabet still. An artificial teaching convention; human readability is
   untested.
4. **The nature of sound.** Six 11-second model films, each varying one
   parameter: Lissajous intervals, beats, harmonic balance H2/H1, decay τ,
   membrane modes, string tension.
5. **24 experiment cards — 10 families explored.** The completed campaign
   catalogue: one table of 24 rows (23 promising calibrations + 1
   inconclusive) and 24 square cards. Ten families were explored; nine are
   calibrated, and the capillary/surface-wave family is inconclusive.
   Four families exist as cards only, without films.
6. **Two English social films** (16 s): *A fifth, made visible* and *Two
   notes, one pulse* (beats).
7. **Name signature as notation.** A name becomes a melody and staff notation
   in five styles; it already lives on the main Souls of Muse site and is
   referenced, not duplicated, here.

Plus the applied piece below: 18 unique films and 24 cards in total
(17 original catalogue films + 1 performance loop).

## The article

*Sound Made Visible: what changes when a note changes?* — a readable research
story: the Kimi starting prototype, the pilot and its honest downgrade, the
note-aware turn, the two-hour 24-window campaign with a bounded two-loop
method (inspired by Andrej Karpathy's autoresearch), selected works with
"what changes / what we tested / possible use / evidence status", and the
full 24-experiment catalogue. Numbers are stated at their true size:
synthetic calibrations against a frozen evaluator; nine calibrated families
and one inconclusive of ten explored; the held-out check (19
candidate-condition entries × 2 seeded points, max mean relative error
0.081218%) is not 38 independent physical measurements.

## The jury report

A concise, printable formal summary: motivation, method and roles, numerical
results, representative output, failure handling, contributions and limits,
public references. No generated candidate code was executed during the
research (hypotheses were data-only); the renderer and media tools were
authored separately by Muse.

## Applied direction — Dynamic Visuals for Your Performance

A curated 39-second visual montage for ambient performance projection
(`#performance` on the article page). It plays as a pre-rendered silent loop
on a fixed timeline; start it with a set or let it run throughout the show.
Curated licensed footage (credits on the page); edit and sequence by
Sci Sound Labs. Controls: Play/Pause, Fullscreen (starts the muted loop in
the same click, letterboxed without cropping), and MP4 download. Presented
as a creative direction, clearly distinguished from the scientific
demonstrations.

## Optional next step — the mini-widget

`widget-brief.md` proposes a small "see the sound" starter widget grown from
the supplied Kimi-built prototype: three built-in tone presets, sound opt-in,
pause/reset, a one-line text alternative per preset, and a linked-preview
fallback. Where supplied prototype source is available to the project, the
brief allows adapting it with Kimi attribution and notices preserved;
embedding a live form still needs a compatibility and privacy check. The
linked preview works today. No widget has been built yet.

## Design language and constraints

- Nocturne ground (`#0d1020`) with gold `#EDC142` and lavender `#b7a6ff`
  accents; serif editorial body text; cards and chips for evidence status.
- Self-contained pages: local media only, lazy-loaded images, `preload="none"`
  videos with posters — nothing plays or downloads heavy media uninvited;
  the only autoplaying media is the muted performance loop when scrolled
  into view (respecting `prefers-reduced-motion`).
- Mobile-safe: legible at 390 px with no horizontal scrolling; touch targets
  at least 44 px; the shared site navigation link stays narrow.
- Complete archive stays complete: the full seven groups, 18 films and
  24 cards ship with the section; long galleries may collapse or lazy-load
  for readability, but no original group is dropped.
- All new copy is English. Historical archival labels inside media are
  marked as historical originals with English captions.

*Prepared for design handoff. Publication and deployment are handled
separately by the project owner.*
