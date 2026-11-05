# -*- coding: utf-8 -*-
"""Подбор порогов касания по тени на фотографиях/кадрах картонки (см. keys/touch_shadow.py, keys/SHOOT-shadow.md).

На каждый кадр: SAM 3.1 (local) → полигоны чёрных → cardboard.fit (гомография чертёж→кадр) → Apple Vision кончики
→ ShadowTouch.classify на каждый кончик → строка таблицы + размеченный кадр в --out.
В конце перебор dark × sat_skin: сколько кончиков вышло touch/hover/unsure/none при каждой паре.

  .venv-mlx/bin/python keys/tune_shadow.py --out out/tune_side side/*.jpg
  .venv-mlx/bin/python keys/tune_shadow.py --out out/tune_top --max-side 1280 top/*.jpg --sweep
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cardboard
from touch_shadow import ShadowTouch

DIPK = {"thumb": "VNHLKTIP", "index": "VNHLKIDIP", "middle": "VNHLKMDIP", "ring": "VNHLKRDIP", "little": "VNHLKPDIP"}

def load_image(p: Path, max_side: int, tmp: Path):
    if p.suffix.lower() in (".heic", ".heif"):
        tmp.mkdir(parents=True, exist_ok=True); j = tmp / (p.stem + ".jpg")
        if not j.exists():
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", str(p), "--out", str(j)], check=True, capture_output=True)
        p = j
    img = cv2.imread(str(p), cv2.IMREAD_COLOR)
    if img is None: return None
    H, W = img.shape[:2]; s = max_side / max(H, W)
    if s < 1.0: img = cv2.resize(img, (int(W * s), int(H * s)), interpolation=cv2.INTER_AREA)
    return img

def black_polys_sam(sam, frame, res):
    from air_keys import poly_from_mask
    H, W = frame.shape[:2]; polys = []
    for conf, m in sam.masks(frame, "black piano key", res, 0.3):
        if m.shape != (H, W): m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
        pp = poly_from_mask(m)
        if pp is not None: polys.append(pp)
    return polys

def finger_px(keys):
    wk = [max(p[0] for p in k["poly"]) - min(p[0] for p in k["poly"]) for k in keys if k["kind"] == "white"]
    return 0.6 * float(np.median(wk)) if wk else 16.0

def key_at(keys, x, y):
    # чёрные сверху, потом белые
    for kind in ("black", "white"):
        for k in keys:
            if k["kind"] != kind: continue
            if cv2.pointPolygonTest(np.array(k["poly"], dtype=np.int32), (float(x), float(y)), False) >= 0: return k
    return None

COL = {"touch": (60, 220, 120), "hover": (60, 160, 255), "unsure": (0, 220, 255), "none": (140, 140, 140)}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", default="out/tune_shadow")
    ap.add_argument("--max-side", type=int, default=1408)
    ap.add_argument("--sam-res", type=int, default=1008)
    ap.add_argument("--base-octave", type=int, default=4)
    ap.add_argument("--dark", type=float, default=0.62); ap.add_argument("--sat-skin", type=float, default=0.22)
    ap.add_argument("--touch-gap", type=float, default=0.12); ap.add_argument("--hover-gap", type=float, default=0.28)
    ap.add_argument("--sweep", action="store_true", help="перебрать dark × sat_skin по всем кончикам")
    ap.add_argument("--no-sam", action="store_true", help="чёрные по порогу яркости вместо SAM (быстро, грубо)")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True); tmp = out / "jpg"
    sam = None
    if not args.no_sam:
        from air_keys import LocalSam
        sam = LocalSam()
    from hand_pose import VisionHands
    hands = VisionHands(max_hands=2, min_conf=0.3)
    st = ShadowTouch(dark=args.dark, sat_skin=args.sat_skin, touch_gap=args.touch_gap, hover_gap=args.hover_gap)
    whites_t, blacks_t = cardboard.template(args.base_octave)
    rows = []; samples = []        # samples: (frame, tip, dip, w, H, label) для sweep
    print(f"{'кадр':<14}{'чертёж':<28}{'рук':>4}  кончики: палец→клавиша состояние щель/w сторона")
    for ip in args.images:
        p = Path(ip); t0 = time.perf_counter()
        frame = load_image(p, args.max_side, tmp)
        if frame is None: print(f"{p.name:<14}не читается"); continue
        H, W = frame.shape[:2]
        if sam is not None: polys = black_polys_sam(sam, frame, args.sam_res)
        else:
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY); m = (g < 60).astype(np.uint8)
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            polys = [cv2.approxPolyDP(c, 0.01 * cv2.arcLength(c, True), True).reshape(-1, 2).tolist() for c in cnts if 300 < cv2.contourArea(c) < 0.02 * W * H]
        keys, info = cardboard.fit(polys, W, H, args.base_octave, gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        vis = frame.copy()
        for pp in polys: cv2.polylines(vis, [np.array(pp, dtype=np.int32)], True, (0, 0, 255), 1)
        if keys is None:
            # чертёж не лёг: тень всё равно оцениваем, чёрные берём как есть (без гомографии), клавиша неизвестна
            st.set_layout(None); st.blacks_poly = [np.array(pp, dtype=np.int32) for pp in polys]; keys = []
            ws = [max(x for x, _ in pp) - min(x for x, _ in pp) for pp in polys]
            w = 1.0 * float(np.median(ws)) if ws else 24.0            # палец ≈ ширина чёрной клавиши (17 мм против 18)
            fit_txt = f"не лёг ({str(info)[:22]})"; Hm = None
        else:
            cardboard.draw(vis, keys)
            st.set_layout(info["H"], [b["rect"] for b in blacks_t]); w = finger_px(keys); Hm = info["H"]
            fit_txt = f"чёрных {info['blacks_matched']} ош {info['err_px']:.1f}px в кадре {info['in_frame']}"
        hs = hands.detect(frame); tips_txt = []
        for hd in hs:
            for short, (x, y, c) in hd["tips"].items():
                dp = hd["points"].get(DIPK[short]); dip = (dp[0], dp[1]) if dp is not None else (x, y + 40)
                r = st.classify(frame, (x, y), dip, w); k = key_at(keys, x, y)
                kn = k["name"] if k else "-"
                samples.append((frame, (x, y), dip, w, Hm, polys, k is not None or Hm is None))
                rows.append({"frame": p.name, "hand": hd["chirality"], "finger": short, "key": kn, "x": round(float(x), 1), "y": round(float(y), 1), "w": round(float(w), 1), **{kk: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for kk, v in r.items()}})
                tips_txt.append(f"{short[:2]}→{kn} {r['state']}" + (f" {r['gap_w']:.2f}{r['side']}" if "gap_w" in r else ""))
                col = COL[r["state"]]
                cv2.circle(vis, (int(x), int(y)), int(0.5 * w), col, 2); cv2.line(vis, (int(x), int(y)), (int(dip[0]), int(dip[1])), col, 1)
                cv2.putText(vis, f"{short[:2]} {r['state'][:2]}" + (f" {r['gap_w']:.2f}" if "gap_w" in r else ""), (int(x) + 8, int(y) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(vis, f"{short[:2]} {r['state'][:2]}" + (f" {r['gap_w']:.2f}" if "gap_w" in r else ""), (int(x) + 8, int(y) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.imwrite(str(out / (p.stem + ".jpg")), vis)
        print(f"{p.name:<14}{fit_txt:<28}{len(hs):>4}  " + "; ".join(tips_txt) + f"  [{time.perf_counter() - t0:.1f}s]")
    (out / "tips.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    from collections import Counter
    c = Counter(r["state"] for r in rows); print("\nитого по кончикам:", dict(c), f"| палец ≈ {w:.0f} px" if rows else "")
    on_key = [r for r in rows if r["key"] != "-"]; print("из них на клавише:", dict(Counter(r["state"] for r in on_key)))
    if args.sweep and samples:
        print("\nперебор dark × sat_skin (touch/hover/unsure/none по кончикам на клавише):")
        print(f"{'dark x sat':<10}" + "".join(f"{s:>16.2f}" for s in (0.12, 0.16, 0.22, 0.30, 0.40)))
        for dark in (0.5, 0.62, 0.72, 0.8):
            line = f"{dark:<10.2f}"
            for sat in (0.12, 0.16, 0.22, 0.30, 0.40):
                s2 = ShadowTouch(dark=dark, sat_skin=sat, touch_gap=args.touch_gap, hover_gap=args.hover_gap)
                cc = Counter()
                for frame, tip, dip, ww, Hm, pl, onk in samples:
                    if not onk: continue
                    if Hm is None: s2.set_layout(None); s2.blacks_poly = [np.array(pp, dtype=np.int32) for pp in pl]
                    else: s2.set_layout(Hm, [b["rect"] for b in blacks_t])
                    cc[s2.classify(frame, tip, dip, ww)["state"]] += 1
                line += f"{cc['touch']:>4}/{cc['hover']:>3}/{cc['unsure']:>3}/{cc['none']:>3}"
            print(line)

if __name__ == "__main__":
    main()
