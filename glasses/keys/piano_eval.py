# -*- coding: utf-8 -*-
"""Оценка привязки и DINO по записи с настоящего пианино, без SAM (кэш press_dino --cache).

Правда — удары из аудиодорожки (note_onsets.py: момент и нота; инструмент разметки, не канал стенда).
Нажатая клавиша = клавиша с нотой удара в окне 0.05–0.35 с после удара.
Проход 1: привязка (скан по кадрам / слежение), DINO-векторы белых клавиш в кадре, кончики пальцев.
Замок октавы по первому удару партитуры: среди клавиш под пальцами в окне первого удара берём ту, что сильнее
всего отклонилась от спокойного вида (DINO), объявляем её ожидаемой нотой → сдвиг меток (кратный 12).
По каждому удару: лежит ли какой-то кончик на ожидаемой клавише; какая клавиша «загорелась» по DINO (top-1).
AUC/ложные DINO: «строго» — спокойные клавиши вдали от пальцев, «жёстко» — все ненажатые, включая под рукой.

  .venv-mlx/bin/python keys/piano_eval.py out/clips/<stem> onsets.json --from 24 --to 37 [--no-track] [--no-lock]
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cardboard
from score_lock import PianoTracker, key_at
from press_dino import key_crop
from dino_probe import Dino

def nm(m): return cardboard.NOTE_NAMES[m % 12] + str(m // 12 - 1)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clipdir"); ap.add_argument("onsets")
    ap.add_argument("--from", dest="t0", type=float, default=0); ap.add_argument("--to", dest="t1", type=float, default=1e9)
    ap.add_argument("--fps", type=float, default=10); ap.add_argument("--hint", type=int, default=64)
    ap.add_argument("--no-track", action="store_true"); ap.add_argument("--no-lock", action="store_true")
    ap.add_argument("--min-strength", type=float, default=0.25); ap.add_argument("--min-conf", type=float, default=2.0)
    ap.add_argument("--near", type=float, default=1.5); ap.add_argument("--out")
    ap.add_argument("--no-anchor", action="store_true", help="без якоря над клавишами")
    ap.add_argument("--trace", action="store_true", help="печатать центр и число чёрных каждую секунду")
    ap.add_argument("--stride", type=int, default=1, help="брать каждый N-й кадр (проверка слежения при редкой привязке)")
    args = ap.parse_args(); cd = Path(args.clipdir)
    ons = [o for o in json.load(open(args.onsets)) if args.t0 <= o["t"] <= args.t1 and o["flux"] >= args.min_strength and o["conf"] >= args.min_conf]
    frames = [f for f in sorted((cd / "frames").glob("f_*.jpg")) if args.t0 <= (int(f.stem[2:]) - 1) / args.fps <= args.t1 and (cd / "cache" / (f.stem + ".json")).exists()]
    frames = frames[::args.stride]
    if not frames or not ons: sys.exit(f"кадров с кэшем {len(frames)}, ударов {len(ons)}")
    print(f"кадров {len(frames)} ({(int(frames[0].stem[2:])-1)/args.fps:.1f}–{(int(frames[-1].stem[2:])-1)/args.fps:.1f} с), ударов {len(ons)}: " + " ".join(o["name"] for o in ons))
    tr = PianoTracker(hint=args.hint, track=not args.no_track); dino = Dino(size=112)
    w0, w1 = (0.05, 0.35) if args.stride == 1 else (0.0, 0.6)       # окно после удара; при редких кадрах шире
    rows = []; t_fit = []; centers = []; n_fail = 0           # rows: (fi, t, raw midi, vec, near, tip_on)
    for f in frames:
        fi = int(f.stem[2:]) - 1; t = fi / args.fps
        frame = cv2.imread(str(f)); H, W = frame.shape[:2]
        d = json.load(open(cd / "cache" / (f.stem + ".json")))
        polys = [[tuple(pt) for pt in pl] for pl in d["polys"]]; tips = [tuple(x) for x in d["tips"]]
        t0 = time.perf_counter(); keys, info = tr.step(polys, W, H, frame if tr.anchor is not None else None); t_fit.append(time.perf_counter() - t0)
        if tr.anchor_log: print(f"    {t:6.1f} с: {tr.anchor_log}", flush=True); tr.anchor_log = None
        if keys is None: n_fail += 1; continue
        centers.append(tr.info["center_midi"])
        if tr.anchor is None and not args.no_lock and not args.no_anchor and ons[0]["t"] + w0 <= t <= ons[0]["t"] + w1:
            if tr.set_anchor(frame, tr.info): print(f"    {t:6.1f} с: якорь поставлен, фактура {tr.anchor['tex']:.0f}, чертёж t={tr.anchor['t']:.1f}", flush=True)
        if args.trace and fi % 10 == 0: print(f"    {t:6.1f} с: центр {tr.info['center_midi']}, чёрных {info['blacks_matched']}/{info['blacks_seen']}, {'слежение' if info.get('tracked') else 'СКАН'}", flush=True)
        whites = [k for k in keys if 0 <= k["cx"] < W and 0 <= k["cy"] < H]        # белые и чёрные в кадре
        wk = float(np.median([max(x for x, _ in k["poly"]) - min(x for x, _ in k["poly"]) for k in whites if k["kind"] == "white"]))
        E = dino.embed([key_crop(frame, k["poly"], (64, 160) if k["kind"] == "white" else (40, 120)) for k in whites])
        for k, v in zip(whites, E):
            near = any(abs(x - k["cx"]) < args.near * wk and abs(y - k["cy"]) < 1.2 * (max(yy for _, yy in k["poly"]) - min(yy for _, yy in k["poly"])) for x, y, *_ in tips)
            on = any(key_at([k], x, y) is not None for x, y, *_ in tips)
            rows.append((fi, t, k["midi"], v, near, on))
    print(f"привязка: сканов {tr.n_scan}, слежений {tr.n_track}, срывов {n_fail}, поправок по якорю {tr.n_anchor_fix}, медиана {np.median(t_fit)*1000:.0f} мс; центр midi {len(set(centers))} разных ({min(centers)}..{max(centers)})")
    # спокойный вид и сигнал по каждой клавише (сырые метки, без замка)
    bykey = {}
    for r in rows: bykey.setdefault(r[2], []).append(r)
    score = {}                                                   # (fi, raw midi) → 1 - cos
    for m, rs in bykey.items():
        calm = [v for _, _, _, v, near, _ in rs if not near]
        if len(calm) < 3: continue
        base = np.median(np.stack(calm), 0); base /= np.linalg.norm(base) + 1e-9
        for fi, t, _, v, near, on in rs: score[(fi, m)] = 1 - float(v @ base)
    def window(o): return [fi for fi in sorted(set(r[0] for r in rows)) if o["t"] + w0 <= fi / args.fps <= o["t"] + w1]
    def med_score(m, fis):
        s = [score[(fi, m)] for fi in fis if (fi, m) in score]; return float(np.median(s)) if s else None
    delta = 0; note = "без замка"
    if not args.no_lock:
        fis = window(ons[0]); cand = {}
        for fi, t, m, v, near, on in rows:
            if fi in fis and on:
                s = med_score(m, fis)
                if s is not None: cand[m] = s
        if not cand:    # спокойного вида ещё нет (мало кадров) — как в стенде: любая клавиша под кончиком
            cand = {m: 1.0 for fi, t, m, v, near, on in rows if fi in fis and on}
        if cand:
            m0 = max(cand, key=cand.get); d = ons[0]["midi"] - m0
            delta = d if d % 12 == 0 else 12 * int(round(d / 12))
            note = f"замок: по DINO под пальцами сильнее всех {nm(m0)} (сырая метка), ожидалась {ons[0]['name']}: разница {d:+d}" + \
                   (f" — не октава, рисунок сдвинут на клавишу; беру ближайшую октаву {delta:+d}" if d != delta else f" → сдвиг меток {delta:+d}")
        else: note = "замок: в окне первого удара нет клавиш под пальцами"
    print(note)
    hits = hits_top = conf_ok = 0
    thr = None
    def pressed(t, m): return any(o["midi"] - delta == m and o["t"] + w0 <= t <= o["t"] + w1 for o in ons)
    Spos = [score[(fi, m)] for fi, t, m, v, near, on in rows if (fi, m) in score and pressed(t, m)]
    if Spos: thr = float(np.quantile(Spos, 0.10))
    for o in ons:
        fis = window(o); exp_raw = o["midi"] - delta
        on_exp = [any(r[5] for r in rows if r[0] == fi and r[2] == exp_raw) for fi in fis]
        hit = bool(on_exp) and sum(on_exp) * 2 >= len(on_exp)
        ms = sorted({r[2] for r in rows if r[0] in fis}); sc = {m: med_score(m, fis) for m in ms}; sc = {m: s for m, s in sc.items() if s is not None}
        top = max(sc, key=sc.get) if sc else None; hit_top = top == exp_raw
        se = sc.get(exp_raw); ok = thr is not None and se is not None and se > thr
        hits += hit; hits_top += hit_top; conf_ok += ok
        print(f"  {o['t']:6.2f} с {o['name']:4s}: палец на ней {'✓' if hit else '✗'}; ожидаемая подтвердилась {'✓' if ok else '✗'} ({se if se is not None else float('nan'):.2f}); сильнее всех {nm(top + delta) if top is not None else '—':4s} ({sc[top]:.2f})" if top is not None else f"  {o['t']:6.2f} с {o['name']:4s}: клавиш в окне нет")
    print(f"палец на ожидаемой клавише {hits}/{len(ons)}; ожидаемая подтвердилась порогом {conf_ok}/{len(ons)}; сильнее всех именно она {hits_top}/{len(ons)}")
    def quiet(t): return not any(o["t"] - 0.1 <= t <= o["t"] + 0.6 for o in ons)
    S, L, Q = [], [], []
    for fi, t, m, v, near, on in rows:
        if (fi, m) not in score: continue
        S.append(score[(fi, m)]); L.append(1 if pressed(t, m) else 0); Q.append(quiet(t) and not near)
    S, L, Q = np.array(S), np.array(L), np.array(Q)
    from sklearn.metrics import roc_auc_score
    res = {"delta": delta, "hits": hits, "hits_top": hits_top, "n_onsets": len(ons), "scans": tr.n_scan, "tracks": tr.n_track, "anchor_fixes": tr.n_anchor_fix, "ms_fit": float(np.median(t_fit) * 1000)}
    if L.sum() and (1 - L).sum():
        thr = float(np.quantile(S[L == 1], 0.10))
        auc_h = roc_auc_score(L, S); fp_h = float((S[L == 0] > thr).mean())
        sel = (L == 1) | Q; auc_s = roc_auc_score(L[sel], S[sel]); fp_s = float((S[(L == 0) & Q] > thr).mean())
        print(f"DINO: нажатых пар {int(L.sum())}, порог {thr:.3f} (90 % нажатий); медиана сигнала нажатых {np.median(S[L==1]):.3f}, спокойных {np.median(S[(L==0)&Q]):.3f}")
        print(f"  жёстко (все ненажатые, {int((1-L).sum())}): AUC {auc_h:.3f}, ложных {fp_h:.1%}")
        print(f"  строго (спокойные вдали от пальцев, {int(((L==0)&Q).sum())}): AUC {auc_s:.3f}, ложных {fp_s:.1%}")
        T = np.array([on for fi, t, m, v, near, on in rows if (fi, m) in score])
        fp_t = float((S[(L == 0) & T] > thr).mean()) if ((L == 0) & T).any() else float("nan")
        print(f"  под пальцем, но не нажата ({int(((L==0)&T).sum())} пар): ложных подтверждений {fp_t:.1%}")
        res.update({"thr": thr, "auc_hard": auc_h, "fp_hard": fp_h, "auc_strict": auc_s, "fp_strict": fp_s, "fp_tip": fp_t, "pos": int(L.sum()), "confirmed": conf_ok})
    if args.out: json.dump(res, open(args.out, "w"), indent=1)

if __name__ == "__main__": main()
