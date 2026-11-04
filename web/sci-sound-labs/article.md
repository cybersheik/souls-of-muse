# Sound Made Visible: what changes when a note changes?

*Sci Sound Labs — the research direction of Souls of Muse · Sci Sound Labs research team, with Meta Muse*

Imagine you hear a single note — and at the same moment you see it: a shape that moves because the sound moved. The note rises, softens, fades. A second tone joins it, slightly out of tune, and the air itself seems to pulse. What exactly changed — the pitch, the colour of the tone, the length of its tail, or the space it rings in?

That question is the heart of Sound Made Visible, our research line on turning musical sound into honest, readable form. We want visuals where every visible change is caused by an audible one, so a musician or teacher can point at the screen and say: "There — that is the interval widening. That pulse is my tuning, still a little off."

## Where it started: a Kimi-built starting prototype, and our own questions

Our starting point was the Kimi-built starting prototype supplied to the project: [Sound Made Visible, created with Kimi](https://visionsound.ok.kimi.link/). It offered three modes — Sound Sculpture, Wave Explorer and Resonance Patterns — with built-in tones (220 Hz, a rich tone, a pulse rhythm, a voice-like hum) alongside microphone and file options. We explored the built-in examples only. It gave us a language; measuring came next. The prototype stays credited and linked here, and what follows is our research built from those questions.

## A first pilot, a useful failure, and a note-aware turn

Our first pilot rendered six short variants: four visual styles of the same motif, a C-major solfège exercise, and an 80 BPM rhythm study (21.87–49.95 seconds each; 5 minutes 14.82 seconds in total). It proved the media pipeline worked. Honest review then downgraded it: engineering feasibility, not a validated experiment — no objective score, no baseline, no working holdout. Worse, different notes inside one broad frequency band produced nearly identical geometry, and during a rest the shape kept living as if sound were still playing. A pause bug — and a musical lie.

The critique led to our clearest early piece: a 15-second note-aware scale. Sixteen notes climb from C4 to C5 and return, with two rests, at 80 BPM; each of the eight steps owns a distinct colour and outline, and on rests the form quietly fades. This is an artificial teaching code chosen by us: a deliberate convention (notes carry no natural colour) applied to a score known in advance, with distinguishability verified in software checks. Whether people find the code readable, and whether it helps learning, remains untested. The page keeps the earlier version beside the new one, so the improvement can be seen rather than described.

## The two-hour campaign: a bounded two-loop method

The centrepiece is a completed research campaign of 31 October 2026: 24 windows of exactly 300 seconds each, 7,200.368 seconds in total — about two hours — exploring how sound and form are linked in nature. The method is a bounded two-loop adaptation we call BiLevel AutoResearch, inspired by [Andrej Karpathy's autoresearch](https://github.com/karpathy/autoresearch), in which an agent adjusts training code, runs a brief five-minute training trial, and retains only changes that improve a fixed validation score, with preparation and evaluation held constant. We adapted the principle, not the subject: our 300-second windows test sound-and-form hypotheses rather than training language models.

In plain terms: an *inner loop* tests a candidate formula inside a fixed corridor of families and ranges. An *outer loop* reads the outcomes and, only at a later window boundary, may redirect the search — new focus, ranges, assumptions. The evaluator (independent numerical and spectral checks, frozen before the campaign) never changes mid-run; hypotheses arrive as data only, and no generated candidate code is executed during the research. The renderer and media-export tools are a separate matter: they were authored by Muse (Meta Muse) outside the research loop. Both research roles were played by muse-wonder-1.0 in separate contexts through the direct Meta API (59 completed requests: 48 inner, 11 outer); eleven outer-loop decisions were genuinely applied to later windows. That shows the method operates as designed; whether the outer loop outperforms a fixed strategy was not measured.

The trajectory: Lissajous figures and beats → harmonic balance H2/H1 and decay τ → spatial resonators (string, membrane, Helmholtz vessel, pipes) → surface waves → invariance controls and geometric similarity. An earlier attempt had been stopped after six closed windows plus a partial seventh (empty responses; a condition that changed nothing but its label), repaired, and restarted from zero — those windows are not counted in the 24.

## What the campaign found — and what it did not

Ten sound and wave families were explored. Nine have numerical calibrations with held-out support; the tenth is inconclusive. Twenty-three windows ended as PROMISING numerical calibrations against the frozen synthetic model. A held-out check (19 candidate-condition entries, two seeded points each) showed a maximum mean relative error of 0.081218%. Those seeded points reuse the same candidate conditions and model families, so they are not 38 independent physical measurements, and they do not prove generalisation beyond the given synthetic evaluator. One window — surface and capillary waves, a fluid-surface family explored for its wave mathematics — is INCONCLUSIVE: numeric error 0.0184%, but the required spectral check fell outside the available range. An early inverted ratio (p/q corrected to q/p) is preserved openly.

Read these numbers at their true size: calibrations of well-known relationships against a synthetic model. Several late windows repeat controls and progress plateaued, so the 24 rounds are rounds of one campaign, with physical measurement and human learning still ahead of us. They demonstrate a loop that can propose, test, redirect — and decline to claim.

## Selected works

**Intervals as a Lissajous figure.** *What changes:* the ratio of two tones' frequencies. *What we tested:* whether the predicted closed curve matches the model (0% mean error after correction). *Possible use:* hear a fifth or an octave and watch its figure settle; detune slightly and watch it drift. *Evidence status:* synthetic calibration.

**Beats — a pulse you can tune by.** *What changes:* the detuning between two near-identical tones; the beat rate equals |f1 − f2| ([UNSW Physclips](https://www.animations.physics.unsw.edu.au/jw/beats.htm)). *What we tested:* the audible envelope against the formula (0.0575% and 0.0365% mean error in two windows). *Possible use:* "slow the pulse down" as a tuning game. *Evidence status:* synthetic calibration; the white envelope runs in real time while fast carriers are drawn schematically.

**One stroke of timbre — H2/H1.** *What changes:* the strength of the second harmonic (H2 — the harmonic at twice the fundamental, not the "second overtone") relative to the first. *What we tested:* the ratio against spectral measurement of the synthesised tone, including controls showing invariance to the fundamental itself. *Possible use:* one note, several characters, as rosette cards. *Evidence status:* synthetic calibration; a single ratio does not determine perceived timbre, and we say so wherever the rosette appears.

**Two tails of a note — decay τ.** *What changes:* how quickly a note fades. *What we tested:* that initial loudness changes volume but not τ in this exponential model. *Possible use:* separating "louder" from "longer" when discussing articulation and release. *Evidence status:* synthetic calibration.

**Membrane and string — modes you can point at.** *What changes:* dimensions, tension, density and mode numbers. *What we tested:* predicted resonance frequencies of the idealised models, checked numerically (for strings and harmonics, see [UNSW](https://phys.unsw.edu.au/jw/harmonics.html)). The drawn node shapes are schematic renderings of those models, not independently validated physical spatial patterns. *Possible use:* predict where the still lines (nodes) fall before the tone sounds. *Evidence status:* synthetic calibration; visible oscillation is slowed down, audio is real-time.

**Helmholtz vessel and pipes — geometry sings.** *What changes:* a vessel's volume and neck, or a pipe's length and whether its far end is open or closed. *What we tested:* resonance frequencies against the classical models ([Helmholtz](https://www.phys.unsw.edu.au/jw/Helmholtz.html), [pipes](https://www.phys.unsw.edu.au/jw/pipes.html)). *Possible use:* "same length — open or closed?" In the ideal model the pitch leaps roughly an octave; real instruments need end corrections, so we present it as approximate. *Evidence status:* synthetic calibration.

**Note-aware solfège.** *What changes:* the note itself — colour, outline and an honest fade on rests. *What we tested:* distinctness (swapping one note changes the geometry; repeating the input repeats it exactly). *Possible use:* follow-the-light exercises in a music session. *Evidence status:* product demonstration with a known score; learning benefit untested.

**Surface waves — the honest gap.** *What changes:* wavelength, depth and density in a capillary-wave model. *What we tested:* the numbers matched, the mandatory spectral check could not run. *Evidence status:* inconclusive, and labelled so on its card.

## Where this can go

Every application follows one rule: the person predicts first, then we show. Guess the interval from its figure. Slow the beat pulse to a stop. Say which tail lasts longer. Because the answer is carried by the signal itself, these become conversations a Maestro can lead, short vertical films, and in time a small interactive corner of the portal.

Scientific visualisation and stage visuals are both valuable directions; they simply answer different questions. Our companion applied line, *Dynamic Visuals for Your Performance*, takes the same love of living form to the stage: a curated 39-second visual montage for ambient performance projection. It plays as a pre-rendered silent loop on a fixed timeline; start it with your set or let it run throughout the show. Source footage credits are listed with the loop on the page (edit and sequence: Sci Sound Labs). Teaching effects on real people remain untested: the next, human step.

For the complete record, the page also carries the full original collection. Its catalogue has seven groups: the Kimi starting prototype; the musical portrait of a melody (six early pilot films and the four-portrait comparison); the note-as-colour-and-shape scale in its earlier and final versions; six nature-of-sound films; the 24 experiment cards; two English social films; and the name-signature feature, which lives on the main Souls of Muse site. With the applied performance loop presented separately above, this page holds 18 films and 24 cards in all, with archival originals marked as historical where their on-screen labels predate this English edition.

---

*Sci Sound Labs research team, with Meta Muse. Starting prototype: the Kimi-built Sound Made Visible prototype supplied to the project (created with Kimi, credited and linked). Method inspiration: Andrej Karpathy's autoresearch. Physics references: UNSW Music Acoustics / Physclips, linked above. Several archival originals retain their historical on-screen labels, explicitly marked as historical; English captions accompany them throughout this page.*
