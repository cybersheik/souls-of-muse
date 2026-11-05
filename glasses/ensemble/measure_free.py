# -*- coding: utf-8 -*-
"""R-04: сухой прогон режима без метра на записи. Смотрим: когда меняются аккорды относительно нот солиста и его тактов,
сколько басовых дублей, и не отстаёт ли смена аккорда от такта записи (beats.json).
  .venv-mlx/bin/python ensemble/measure_free.py clips/aidar_audio/k_elise_aidar.notes.json clips/aidar_audio/k_elise_aidar.beats.json k_elise_aidar"""
import sys, json, importlib, numpy as np; sys.path.insert(0, "ensemble")
from follower import Follower
notes = json.load(open(sys.argv[1])); beats = np.array(json.load(open(sys.argv[2]))); score = importlib.import_module(sys.argv[3])
class Cap:
    def __init__(self): self.ev = []
    def note_on(self, ch, m, v): self.ev.append((self.t, ch, m, v))
    def note_off(self, ch, m): pass
cap = Cap(); logs = []
f = Follower(score, cap, sec_per_eighth=0.40, meter=False, log=logs.append)
for t, m in notes:
    cap.t = t; f.observe(t, m)
pads = [(t, m) for t, ch, m, v in cap.ev if ch == 1]; bass = [(t, m) for t, ch, m, v in cap.ev if ch == 0]
chg = sorted(set(round(t, 3) for t, _ in pads))
print(f"нот солиста {len(notes)}, сопоставлено {f.matches}; смен аккорда {len(chg)} (в партитуре {len(score.CHORDS)} тактов), басовых нот {len(bass)}")
# смена аккорда относительно ближайшей сильной доли записи (каждая 4-я доля, фаза 0)
strong = beats[::score.BAR]
dev = np.array([t - strong[np.argmin(abs(strong - t))] for t in chg])
print(f"смена аккорда относительно ближайшей сильной доли записи: медиана {np.median(dev)*1000:+.0f} мс, 90 % |откл.| {np.percentile(abs(dev),90)*1000:.0f} мс (по построению совпадает с нотой солиста)")
low = [(t, m) for t, m in notes if m < f.low_note]
print(f"низких нот солиста (<{f.low_note}) {len(low)}; бас продублировал их в тот же момент: {sum(1 for t,_ in low if any(abs(t-tb)<1e-6 for tb,_ in bass))}")
print("аккорды по ходу:", " ".join(l.split()[1] for l in logs if l.startswith("аккорд")))
