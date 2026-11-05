# -*- coding: utf-8 -*-
"""Синтетическая проверка привязки профиля piano: чертёж → гомография в кадр 1280×720 → полигоны чёрных (12 вершин,
шум) → cardboard.fit(profile="piano") → сравнение центров белых с истиной. Без подсказки октавы C3..E4 обязан
промахиваться на октаву (рисунок чёрных периодичен).  .venv-mlx/bin/python keys/piano_fit_synth.py"""
import sys, numpy as np, cv2
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import cardboard as c
W, H = 1280, 720
wt, bt = c.template(4, "piano"); ww, wl, bw, bl, n, start = c.dims("piano")
idx = {k["midi"]: i for i, k in enumerate(wt)}
def make(i0, i1, tilt, noise, drop=()):
    src = np.array([[i0, 0], [i1, 0], [i1, wl], [i0, wl]], np.float32)
    dst = np.array([[W*(0.1+tilt), 80], [W*(0.9-tilt), 80], [W*0.95, 680], [W*0.05, 680]], np.float32)
    Hm = cv2.getPerspectiveTransform(src, dst); polys = []
    for j, b in enumerate(bt):
        x0, y0, x1, y1 = b["rect"]
        if x1 < i0 - 0.2 or x0 > i1 + 0.2 or j in drop: continue
        q = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32)
        pts = np.concatenate([np.linspace(q[i], q[(i+1) % 4], 4, endpoint=False) for i in range(4)])
        P = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), Hm).reshape(-1, 2) + np.random.randn(len(pts), 2) * noise
        if P[:, 0].min() < 0 or P[:, 0].max() > W: continue
        polys.append([(float(x), float(y)) for x, y in P])
    return polys, Hm
cases = {"C4..E5": (idx[60]-1, idx[76]+1, (), None), "G3..G5": (idx[55], idx[79], (), None),
         "C4..E5 -1 чёрная": (idx[60]-1, idx[76]+1, (20,), None), "C3..E4 подсказка 52": (idx[48]-1, idx[64]+1, (), 52),
         "A4..A6 подсказка 81": (idx[69], idx[93], (), 81), "C3..E4 без подсказки": (idx[48]-1, idx[64]+1, (), None)}
ctr = np.array([[(x0+x1)/2, wl*0.5] for (x0,_,x1,_) in (k["rect"] for k in wt)], np.float32).reshape(-1,1,2)
ok = tot = 0; np.random.seed(1); cv2.setRNGSeed(0); worst = 0.0
for tilt in (0.05, 0.1, 0.15):
    for noise in (1.0, 3.0):
        for name, (i0, i1, drop, hint) in cases.items():
            polys, Hm = make(i0, i1, tilt, noise, drop); expect_miss = name.endswith("без подсказки"); tot += 1
            keys, info = c.fit(polys, W, H, profile="piano", hint_midi=hint)
            if keys is None: print(f"tilt {tilt} шум {noise} {name}: НЕТ — {info}"); continue
            # сравниваем центры белых по midi: истина через Hm, найденное — из keys
            a = cv2.perspectiveTransform(ctr, Hm).reshape(-1, 2); by_midi = {k["midi"]: k for k in keys if k["kind"] == "white"}
            diffs = [abs(by_midi[k["midi"]]["cx"] - a[i, 0]) for i, k in enumerate(wt) if 0 < a[i, 0] < W and k["midi"] in by_midi]
            d = float(np.median(diffs)) if len(diffs) >= 5 else 999.0
            good = (d < 12) != expect_miss; ok += good
            if not expect_miss: worst = max(worst, d)
            if not good: print(f"tilt {tilt} шум {noise} {name}: сопоставлено {info['blacks_matched']}, ошибка {info['err_px']:.1f} px, поперечное расхождение центров белых {d:.1f} px ПРОМАХ")
print(f"верно {ok}/{tot}; худшее поперечное расхождение центров белых {worst:.1f} px (ширина белой внизу кадра ≈ {W*0.9/16:.0f} px)")
