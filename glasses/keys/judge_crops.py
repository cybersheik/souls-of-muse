# -*- coding: utf-8 -*-
"""Набор кропов для проверки VLM-судьи: «кончик пальца лежит на обведённой клавише?» (да/нет).

На каждом кадре: SAM 3.1 → чёрные → cardboard.fit → Apple Vision кончики. Для кончика над клавишей делаем два кропа:
положительный (обведена клавиша под кончиком) и отрицательный (обведена соседняя белая, через 1–2). Правда известна
по построению. Кроп --crop px вокруг кончика, контур зелёный, манифест manifest.json: file, truth, key, frame, finger.

  .venv-mlx/bin/python keys/judge_crops.py --out out/judge_crops --n 20 top/*.jpg
"""
from __future__ import annotations
import argparse, json, random, sys, time
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cardboard
from tune_shadow import load_image, black_polys_sam, key_at

def crop_with_outline(frame, tip, key, crop):
    H, W = frame.shape[:2]; x, y = int(tip[0]), int(tip[1]); h = crop // 2
    x0, y0 = max(0, min(W - crop, x - h)), max(0, min(H - crop, y - h))
    vis = frame.copy()
    cv2.polylines(vis, [np.array(key["poly"], dtype=np.int32)], True, (0, 255, 0), 4)
    return vis[y0:y0 + crop, x0:x0 + crop]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+"); ap.add_argument("--out", default="out/judge_crops")
    ap.add_argument("--n", type=int, default=20); ap.add_argument("--crop", type=int, default=512)
    ap.add_argument("--max-side", type=int, default=1408); ap.add_argument("--sam-res", type=int, default=1008)
    ap.add_argument("--base-octave", type=int, default=4); ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(); random.seed(args.seed)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    from air_keys import LocalSam; from hand_pose import VisionHands
    sam = LocalSam(); hands = VisionHands(max_hands=2, min_conf=0.3)
    cands = []   # (frame_img, tip, key, finger, frame_name, keys)
    for ip in args.images:
        p = Path(ip); frame = load_image(p, args.max_side, out / "jpg")
        if frame is None: continue
        H, W = frame.shape[:2]; t0 = time.perf_counter()
        polys = black_polys_sam(sam, frame, args.sam_res)
        keys, info = cardboard.fit(polys, W, H, args.base_octave, gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        if keys is None: print(f"{p.name}: чертёж не лёг"); continue
        n = 0
        for hd in hands.detect(frame):
            for short, (x, y, c) in hd["tips"].items():
                k = key_at(keys, x, y)
                if k is None or k["kind"] != "white": continue
                cands.append((frame, (x, y), k, short, p.name, keys)); n += 1
        print(f"{p.name}: чёрных {info['blacks_matched']}, кончиков над белыми {n}, {time.perf_counter()-t0:.1f} с", flush=True)
    random.shuffle(cands); cands = cands[: max(1, args.n // 2)]
    man = []
    for i, (frame, tip, k, finger, fname, keys) in enumerate(cands):
        whites = sorted([q for q in keys if q["kind"] == "white"], key=lambda q: q["midi"])
        idx = next(j for j, q in enumerate(whites) if q["midi"] == k["midi"])
        choices = [whites[j] for j in (idx - 2, idx - 1, idx + 1, idx + 2) if 0 <= j < len(whites)]
        neg = random.choice(choices)
        for truth, key in (("yes", k), ("no", neg)):
            fn = f"c{i:02d}_{truth}.jpg"; cv2.imwrite(str(out / fn), crop_with_outline(frame, tip, key, args.crop), [cv2.IMWRITE_JPEG_QUALITY, 92])
            man.append({"file": fn, "truth": truth, "outlined": key["name"], "under_tip": k["name"], "frame": fname, "finger": finger})
    json.dump(man, open(out / "manifest.json", "w"), ensure_ascii=False, indent=1)
    print(f"кропов: {len(man)} → {out}")

if __name__ == "__main__": main()
