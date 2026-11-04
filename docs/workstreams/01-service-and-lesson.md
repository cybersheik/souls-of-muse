# 01. Service and lesson

## Why it matters
Teachers and students of live music need a lesson space where language is not a barrier and the human skill stays at the centre. Muse acts as a mediator, not a replacement for the teacher.

## Before the event
The concept, the teacher/student lesson flow and most of the Muse Lesson 2.0 interface design existed before 26 Oct 2026 (`docs/HACKATHON_CONTRIBUTIONS.md`).

## During the event
| Item | Status | Evidence |
|---|---|---|
| Reproducible static deployment of the lesson prototype | Prototype | `web/`, public preview linked from `README.md` |
| Durable admission and lifecycle control for up to five simultaneous lessons | Offline-tested | `runtime/`, `tests/test_lesson_admission.py`, [ADR 0002](../decisions/0002-lesson-slots-never-expire-by-time.md) |
| Public service site and entry points from Meta channels | <!-- FILL: status --> | <!-- FILL: public URL(s) --> |
| Personal cabinet on the approved lesson design | <!-- FILL: status --> | <!-- FILL: evidence --> |
| Welcome flow, Leagues, listener cabinet | <!-- FILL: status --> | <!-- FILL: evidence --> |
| Voice output for translations (EN/VI) | <!-- FILL: status and engine; credit Meta models only if they are used --> | <!-- FILL --> |

## Meta models
<!-- FILL: which model does what in the lesson (interpreter, reviewer, transcription), with the verified status of each. -->

## Not claimed
- Student indicators, messages, video and lesson metrics in `web/` are simulated. It is not a live lesson service.
- Admission tests prove admission concurrency only, not media capacity.
- <!-- FILL: mandatory scope items (voice for both participants, real lesson hours, tactile metronome) at their verified status on submission day. -->
