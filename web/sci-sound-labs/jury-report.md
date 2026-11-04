# Sound Made Visible — Jury Report

*Sci Sound Labs (research direction of Souls of Muse) · Sci Sound Labs research team, with Meta Muse*

## 1. Motivation

Musicians reason about sound with words for what they hear — brighter, longer, nearly in tune — but the underlying quantity is invisible at the moment it matters. This project asks whether a visual form can be tied to sound so strictly that every visible change is caused by a specific audible one: an interval ratio, a detuning, a harmonic balance, a decay time, a resonator's geometry. If so, the image becomes discussable evidence in a music session rather than decoration, and short demonstrations can carry a real question ("which tail lasts longer?") instead of a slogan.

## 2. Method and roles

We ran a bounded two-loop research procedure. An inner loop proposed candidate relationships (formulas supplied as data only; no generated candidate code was executed during the research) within pre-declared families and ranges. A frozen evaluator, fixed before the campaign, scored each candidate numerically and, where applicable, spectrally against synthesised audio. An outer loop reviewed outcomes and could redirect later windows — focus, ranges, assumptions — with each change recorded and applied only from a subsequent window. Both research roles were performed by muse-wonder-1.0 in separate contexts via the direct Meta API. The renderer and media-export tools were authored separately by Muse (Meta Muse), outside the research loop. The procedure is our bounded adaptation for this single campaign — 24 windows, one frozen evaluator, two research roles — inspired by Andrej Karpathy's autoresearch.

Development history is part of the evidence. A six-variant pilot (four styles of one motif, C-major solfège, 80 BPM rhythm; 21.87–49.95 s per variant, 5 min 14.82 s total) was reclassified after review as engineering feasibility only: no objective delta, no baseline promotion, no working holdout; its note-band mapping failed to distinguish individual notes and contained a pause-handling defect. A follow-up 15-second note-aware scale (C4–C5 and back, 16 notes, 2 rests, 80 BPM, eight distinct colours/outlines, quiet fades on rests) corrected the note/rest mapping for a known score: in software checks each note is now distinguishable and repeats reproduce exactly. Human readability of the code, and any learning benefit, remain untested. A first nature-themed run was stopped after six closed windows plus a partial seventh (empty responses; a non-operative condition flag), repaired, and discarded from the successful count.

## 3. Numerical results (completed campaign, 31 October 2026)

| Quantity | Value |
|---|---|
| Windows | 24 × 300 s; total 7,200.368 s (≈ 2 h) |
| Research requests | 59 completed (48 inner + 11 outer) |
| Outer-loop changes applied to later windows | 11 |
| Outcomes | 23 PROMISING synthetic calibrations; 1 INCONCLUSIVE; 0 final rejections |
| Families explored (10); calibrated 9, inconclusive 1 | Lissajous 1, beats 2, harmonic balance H2/H1 6, decay 4, membrane 2, string 1, Helmholtz 2, closed pipe 2, open pipe 3, capillary/surface waves 1 (inconclusive) |
| Held-out check | 19 candidate-condition entries × 2 seeded points; max mean relative error 0.081218%. The seeded points reuse the same candidate conditions and model families: not 38 independent physical measurements, and not proof of generalisation beyond the given synthetic evaluator |
| Evaluator | Frozen for the whole campaign; hypotheses data-only |

"PROMISING" means agreement with the frozen numerical/synthetic model. The inconclusive case (surface/capillary waves) had 0.0184% numeric error but its mandatory spectral check fell outside the available range. An initial inversion in the first window's ratio (p/q corrected to q/p) is preserved in the record. Full per-experiment values accompany the 24-card catalogue on the public page.

## 4. Representative output

The campaign produced 24 square research cards (1080 × 1080) and six distinct 11-second vertical videos with synchronised audio: Lissajous intervals, beats (rate = |f1 − f2|), harmonic balance H2/H1 (H2 = second harmonic), decay τ, membrane modes, and string resonance. Two polished 16-second English films (intervals; beats) present the clearest demonstrations. Slow-motion drawing is used for string/membrane oscillation and fast carriers; audio is real-time. The drawn nodal shapes are schematic renderings of the models; the numerical frequency/formula checks are what was validated, not physical spatial patterns independently. The public page preserves the complete original collection — seven catalogue groups, 17 original films (including the six early pilot films and the earlier scale version) and 24 cards — plus a separate applied piece, a 39-second seamless projection loop for live performance (18 films in total on the page). The loop is curated licensed footage, presented as an applied creative direction (edit and sequence: Sci Sound Labs), and is not claimed as a research result.

## 5. Failure handling

Three failures were preserved rather than edited away: (i) the pilot's downgrade from "experiment" to "feasibility"; (ii) the stopped first run, excluded from all successful counts; (iii) the inconclusive capillary window, published with its gap labelled. In each case the correction — note-aware coding, repaired response handling and an operative end-correction condition, a locked evaluator — preceded any renewed claim.

## 6. Contributions and limits

Contributions: a reproducible sound-to-form media pipeline; a demonstrated two-loop search with genuine outer-loop redirection under a frozen evaluator (eleven changes truly applied, which supports that the method operates); exploration of ten sound and wave families — nine with numerical calibrations and held-out support, one (capillary surface waves, a fluid-surface family) inconclusive; and a public catalogue in which every card carries its status. Limits: no physical measurements were taken; no human learning, perception or engagement tests have been performed; several later windows repeated controls and progress plateaued, so the 24 rounds are not 24 independent mechanisms or discoveries; any comparative advantage of the outer loop over a fixed strategy was not measured; colour/shape coding is an artificial teaching convention; live or arbitrary-audio recognition is not implemented. Closed/open-pipe octave relations are approximate (end corrections apply in real instruments), and H2/H1 alone does not determine perceived timbre.

## 7. Public references

- Andrej Karpathy, *autoresearch* — https://github.com/karpathy/autoresearch (method inspiration)
- *Sound Made Visible*, the Kimi-built starting prototype supplied to the project (created with Kimi) — https://visionsound.ok.kimi.link/
- UNSW Physclips, *Beats* — https://www.animations.physics.unsw.edu.au/jw/beats.htm
- UNSW Music Acoustics, *Helmholtz Resonance* — https://www.phys.unsw.edu.au/jw/Helmholtz.html
- UNSW Music Acoustics, *Pipes and harmonics* — https://www.phys.unsw.edu.au/jw/pipes.html
- UNSW Music Acoustics, *How harmonic are harmonics?* — https://phys.unsw.edu.au/jw/harmonics.html

*The jury can inspect all public media, the 24-experiment catalogue and the numeric summaries above on the accompanying page. No live or interactive capability beyond what is shown is claimed.*
