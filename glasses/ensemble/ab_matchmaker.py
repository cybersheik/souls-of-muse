# -*- coding: utf-8 -*-
"""R-03: pymatchmaker против своего следящего на одних и тех же событиях.
Партитура k_elise_aidar (единица = доля) → MIDI; события солиста → MIDI-файл; pymatchmaker в офлайн-режиме
(без ожидания реального времени); наш Follower — сухой прогон. Истина: для записи Айдара — отслеженные доли
(beats.json, позиция = интерполяция номера доли); для синтетики — известная кривая темпа.
  .venv-mlx/bin/python ensemble/ab_matchmaker.py [--methods pthmm,hmm,arzt,dixon,outerhmm]"""
import sys, os, json, time, random, argparse, importlib, warnings
import numpy as np
sys.path.insert(0, "ensemble")
warnings.filterwarnings("ignore")
import mido
from follower import Follower

ap = argparse.ArgumentParser()
ap.add_argument("--score", default="k_elise_aidar")
ap.add_argument("--methods", default="pthmm,hmm,arzt,dixon,outerhmm")
ap.add_argument("--out", default="ensemble/ab")
ap.add_argument("--drop", type=float, default=0.30); ap.add_argument("--wrong", type=float, default=0.05); ap.add_argument("--no-real", action="store_true")
a = ap.parse_args()
score = importlib.import_module(a.score)
PPQ = 480; os.makedirs(a.out, exist_ok=True)

def write_midi(path, events, tempo_bpm=60.0):
    """events: [(t_beats_or_sec, midi, dur)] при 60 bpm секунды = доли."""
    mid = mido.MidiFile(ticks_per_beat=PPQ); tr = mido.MidiTrack(); mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))
    msgs = []
    for t, m, d in events:
        msgs.append((t, 1, mido.Message("note_on", note=int(m), velocity=90)))
        msgs.append((t + d, 0, mido.Message("note_off", note=int(m), velocity=0)))
    msgs.sort(key=lambda x: (x[0], x[1]))
    last = 0
    for t, _, msg in msgs:
        tick = int(round(t * PPQ)); msg.time = max(0, tick - last); last = tick; tr.append(msg)
    mid.save(path)

score_mid = f"{a.out}/score_{a.score}.mid"
write_midi(score_mid, [(u, m, max(0.25, d)) for u, m, d in sorted(score.MELODY)])

# ---------- наборы данных: (имя, ноты [(t, midi)], функция истины gt(t) → позиция в долях)
datasets = []
if not a.no_real:
  notes = json.load(open("clips/aidar_audio/k_elise_aidar.notes.json"))
  beats = np.array(json.load(open("clips/aidar_audio/k_elise_aidar.beats.json")))
  datasets.append(("запись Айдара (85 нот)", [(float(t), int(m)) for t, m in notes],
                 lambda t, b=beats: float(np.interp(t, b, np.arange(len(b))))))

def synth_take(seed, spu0=0.40, spu1=0.33, rubato=0.10, drop=0.30, jitter=0.025, wrong=0.05):
    rnd = random.Random(seed)
    mel = sorted(score.MELODY); U = mel[-1][0] + 1
    grid = np.arange(0, U + 0.05, 0.05)                                 # кривая темпа: разгон + синусоидальное рубато
    spu = spu0 + (spu1 - spu0) * grid / U; spu = spu * (1 + rubato * np.sin(2 * np.pi * grid / 8.0))
    tgrid = np.concatenate([[0.0], np.cumsum(np.diff(grid) * spu[1:])])
    u2t = lambda u: float(np.interp(u, grid, tgrid)); t2u = lambda t: float(np.interp(t, tgrid, grid))
    out = []
    for u, m, d in mel:
        if rnd.random() < drop: continue
        mm = m
        if rnd.random() < wrong: mm = m + rnd.choice([-2, -1, 1, 2])
        out.append((u2t(u) + rnd.gauss(0, jitter), mm))
    out.sort()
    return out, t2u
for s in (1, 2, 3):
    nt, gt = synth_take(s, drop=a.drop, wrong=a.wrong)
    datasets.append((f"синтетика #{s} (разгон 0,40→0,33 с/долю, рубато ±10 %, пропуски {a.drop*100:.0f} %, чужие {a.wrong*100:.0f} %, {len(nt)} нот)", nt, gt))

# ---------- прогоны
def run_ours(nt, gt):
    f = Follower(score, None, sec_per_eighth=0.40, log=lambda m: None)
    post, pred, lost = [], [], 0
    for t, m in nt:
        p = f.predicted(t); i = f.observe(t, m); g = gt(t)
        if p is not None: pred.append(abs(p - g))
        if f.pos is not None: post.append(abs(f.pos - g))
    return dict(post=post, pred=pred, matched=f.matches, n=len(nt))

def run_mm(method, nt, gt, tag):
    from matchmaker import Matchmaker
    perf = f"{a.out}/perf_{tag}.mid"; write_midi(perf, [(t, m, 0.2) for t, m in nt])
    t0 = time.perf_counter()
    mm = Matchmaker(score_file=score_mid, performance_file=perf, input_type="midi", method=method, tempo=60.0)
    for _ in mm.run(verbose=False): pass
    dt = time.perf_counter() - t0
    path = np.asarray(mm.score_follower._alignment_path, dtype=float)
    if path.ndim != 2 or path.shape[0] != 2: path = path.T
    tp, beat = path[0], path[1]
    post = []
    for t, m in nt:
        k = np.searchsorted(tp, t + 1e-3, side="right") - 1          # оценка после обработки этой ноты (каузально)
        if k >= 0: post.append(abs(beat[k] - gt(t)))
    return dict(post=post, n=len(nt), points=len(tp), secs=dt, pred=[])

def fmt(v):
    if not v: return "—"
    v = np.array(v); return f"медиана {np.median(v):.2f} · 90 % {np.percentile(v, 90):.2f} · потеряно (>1 доли) {100*np.mean(v > 1):.0f} %"

print(f"партитура {a.score}: {len(score.MELODY)} нот, {score.LENGTH:.0f} долей → {score_mid}")
for name, nt, gt in datasets:
    print(f"\n## {name}")
    r = run_ours(nt, gt)
    print(f"свой следящий        : после ноты {fmt(r['post'])}; предсказание до ноты {fmt(r['pred'])}; сопоставлено {r['matched']}/{r['n']}")
    for method in a.methods.split(","):
        try:
            r = run_mm(method, nt, gt, f"{method}_{abs(hash(name))%10000}")
            print(f"pymatchmaker {method:9s}: после ноты {fmt(r['post'])}; точек пути {r['points']}, {r['secs']:.1f} с на прогон")
        except Exception as e:
            print(f"pymatchmaker {method:9s}: не прошёл — {type(e).__name__}: {str(e)[:160]}")
