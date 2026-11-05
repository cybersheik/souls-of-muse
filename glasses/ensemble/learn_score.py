"""Снять партитуру с записи солиста: ноты (t, midi) → опорная мелодия на сетке восьмых + сетка аккордов по тактам.
  python learn_score.py notes.json out_module.py --spe 0.21 --bar 6   (--spe секунд на восьмую, --bar восьмых в такте)"""
import sys, json, argparse, collections, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("notes"); ap.add_argument("out")
ap.add_argument("--spe", type=float, default=None, help="секунд на восьмую; по умолчанию = медианный интервал между нотами")
ap.add_argument("--bar", type=int, default=3, help="единиц в такте (3 для 3/8; 4 если единица = четверть)"); ap.add_argument("--key", default="learned")
ap.add_argument("--beats", default=None, help="json со временем отслеженных долей: единица времени = доля, темп переменный")
ap.add_argument("--phase", type=int, default=0, help="какая отслеженная доля — первая сильная")
a = ap.parse_args()
notes = json.load(open(a.notes)); t0 = notes[0][0]
if a.beats:
    bt = np.array(json.load(open(a.beats)))[a.phase:]
    spe = float(np.median(np.diff(bt)))
    def to_units(t):                                            # дробный номер доли, линейно между соседними долями
        return float(np.interp(t, bt, np.arange(len(bt))))
    mel = [(round(to_units(t) * 2) / 2, m, 0.5) for t, m in notes]
    mel = [(max(0.0, u), m, d) for u, m, d in mel]
else:
    spe = a.spe or float(np.median(np.diff([t for t, _ in notes])))
    mel = [(round((t - t0) / spe * 2) / 2, m, 0.5) for t, m in notes]       # на сетку шестнадцатых (0.5 восьмой)
length = float(np.ceil((mel[-1][0] + 1) / a.bar) * a.bar)
MAJ, MIN = {0, 4, 7}, {0, 3, 7}
chords = []
for s in np.arange(0, length, a.bar):
    pcs = collections.Counter(m % 12 for t, m, _ in mel if s <= t < s + a.bar)
    if not pcs: chords.append((float(s), float(a.bar), chords[-1][2] if chords else 9, chords[-1][3] if chords else "m")); continue
    best = None
    for root in range(12):
        for kind, tones in (("", MAJ), ("m", MIN)):
            score = sum(w for pc, w in pcs.items() if (pc - root) % 12 in tones) + 0.5 * pcs.get(root, 0)
            if best is None or score > best[0]: best = (score, root, kind)
    chords.append((float(s), float(a.bar), best[1], best[2]))
names = "C C# D D# E F F# G G# A A# B".split()
src = f'''"""Партитура, снятая с записи: {a.notes} ({len(mel)} нот, {spe*1000:.0f} мс на восьмую при записи)."""
NAMES = "C C# D D# E F F# G G# A A# B".split()
MELODY = {mel!r}
CHORDS = {[(s, d, r, names[r] + k) for s, d, r, k in chords]!r}
LENGTH = {length!r}
KEY = {a.key!r}
BAR = {a.bar!r}
CHORD_TONES = {{**{{NAMES[r]: [0, 4, 7] for r in range(12)}}, **{{NAMES[r] + "m": [0, 3, 7] for r in range(12)}}}}
def chord_at(t):
    t = t % LENGTH
    for s, d, root, kind in CHORDS:
        if s <= t < s + d: return root, kind
    return CHORDS[-1][2], CHORDS[-1][3]
'''
open(a.out, "w").write(src)
print(f"нот {len(mel)}, {spe*1000:.0f} мс/восьмую, длина {length:.0f} восьмых, тактов {len(chords)}; аккорды: {' '.join(names[r]+k for _,_,r,k in chords)}")
