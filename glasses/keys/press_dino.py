# -*- coding: utf-8 -*-
"""DINO как детектор «палец на клавише» по виду самой клавиши (проба рядом с SAM и Vision).

Каждый кадр: карта клавиш (cardboard.fit; при срыве держим последнюю), кроп каждой белой клавиши → DINOv2 →
вектор. Спокойное состояние клавиши = медиана её векторов в кадрах, где рядом нет кончиков пальцев. Сигнал
нажатия = 1 − cos(сейчас, спокойное). Правда для оценки: кончик пальца (Apple Vision) внутри клавиши.
Печатает AUC и порог, при котором 90 % «пальцев» ловится, и сколько ложных при этом; время DINO на кадр.
На настоящем пианино к этому сигналу добавится ход клавиши вниз.

  .venv-mlx/bin/python keys/press_dino.py --out out/press_dino top10/p_*.jpg
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cardboard
from tune_shadow import load_image, black_polys_sam, key_at
from dino_probe import Dino

def key_crop(frame, poly, size=(64, 160)):
    """Выпрямленный кроп клавиши: четырёхугольник → прямоугольник size (ш×в), чтобы вектор не зависел от перспективы."""
    P = np.array(poly, dtype=np.float32)
    # порядок углов чертежа: (x0,y0),(x1,y0),(x1,y1),(x0,y1) → верх-лево, верх-право, низ-право, низ-лево
    dst = np.array([[0, 0], [size[0], 0], [size[0], size[1]], [0, size[1]]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(P, dst)
    return cv2.warpPerspective(frame, M, size)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+"); ap.add_argument("--out", default="out/press_dino")
    ap.add_argument("--max-side", type=int, default=1408); ap.add_argument("--sam-res", type=int, default=1008)
    ap.add_argument("--base-octave", type=int, default=4); ap.add_argument("--model", default="facebook/dinov2-small")
    ap.add_argument("--near", type=float, default=1.5, help="кончик ближе этого числа ширин клавиши = клавиша «не спокойна»")
    ap.add_argument("--profile", choices=["cardboard", "piano"], default="cardboard", help="картонка или настоящее пианино (52 белых от A0)")
    ap.add_argument("--hint", type=int, default=None, help="midi ноты примерно в центре кадра (пианино: октаву иначе не угадать; по умолчанию 64 = E4)")
    ap.add_argument("--cache", default=None, help="папка кэша по кадрам (SAM-полигоны чёрных и кончики пальцев): повторный прогон без SAM и Vision")
    args = ap.parse_args(); out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    from air_keys import LocalSam; from hand_pose import VisionHands
    cv2.setRNGSeed(0)   # RANSAC в findHomography случайный — для сравнимости прогонов
    sam = hands = None; dino = Dino(args.model, size=112)      # SAM и Vision поднимаем только при промахе кэша
    cache = Path(args.cache) if args.cache else None
    if cache: cache.mkdir(parents=True, exist_ok=True)
    keys = None; per_key = {}      # name → list of (frame_idx, vec, tip_on, tip_near)
    hint, hw = args.hint, 0.0      # пианино: после первой привязки подсказка = центр предыдущего кадра, с весом
    t_dino = []; n_fit = 0
    for fi, ip in enumerate(args.images):
        p = Path(ip); frame = load_image(p, args.max_side, out / "jpg")
        if frame is None: continue
        H, W = frame.shape[:2]
        cp = cache / (p.stem + ".json") if cache else None
        if cp is not None and cp.exists():
            d = json.load(open(cp)); polys = [[tuple(pt) for pt in pl] for pl in d["polys"]]; tips = [tuple(t) for t in d["tips"]]
        else:
            if sam is None: sam = LocalSam(); hands = VisionHands(max_hands=2, min_conf=0.3)
            polys = black_polys_sam(sam, frame, args.sam_res)
            tips = [(float(x), float(y), str(n)) for hd in hands.detect(frame) for n, (x, y, c) in hd["tips"].items()]
            if cp is not None: json.dump({"polys": [[[float(x), float(y)] for x, y in pl] for pl in polys], "tips": tips}, open(cp, "w"))
        k2, info = cardboard.fit(polys, W, H, args.base_octave, gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                                 profile=args.profile, hint_midi=hint, hint_weight=hw)
        if k2 is not None:
            keys = k2; n_fit += 1
            if args.profile == "piano": hint, hw = info["center_midi"], 0.3
        if keys is None: continue
        whites = [k for k in keys if k["kind"] == "white" and 0 <= k["cx"] < W and 0 <= k["cy"] < H]
        wk = float(np.median([max(x for x, _ in k["poly"]) - min(x for x, _ in k["poly"]) for k in whites]))
        crops = [key_crop(frame, k["poly"]) for k in whites]
        t0 = time.perf_counter(); E = dino.embed(crops); t_dino.append(time.perf_counter() - t0)
        G = [cv2.resize(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY), (16, 40)).astype(np.float32).ravel() / 255.0 for c in crops]
        for k, v, g in zip(whites, E, G):
            on = any(key_at([k], x, y) is not None for x, y, *_ in tips)
            near = any(abs(x - k["cx"]) < args.near * wk and abs(y - k["cy"]) < 1.2 * (max(yy for _, yy in k["poly"]) - min(yy for _, yy in k["poly"])) for x, y, *_ in tips)
            per_key.setdefault(k["name"], []).append((fi, v, on, near, g))
        extra = f", центр midi {info['center_midi']}, ошибка {info['err_frac']:.2f}" if (k2 is not None and args.profile == "piano") else ""
        print(f"{p.name}: чертёж {'лёг' if k2 is not None else 'держу старый'}{extra}, клавиш {len(whites)}, кончиков {len(tips)}, DINO {t_dino[-1]*1000:.0f} мс", flush=True)
    scores, labels, pix = [], [], []
    for name, rows in per_key.items():
        calm = [v for _, v, on, near, g in rows if not near]
        if len(calm) < 3: continue
        base = np.median(np.stack(calm), 0); base /= np.linalg.norm(base) + 1e-9
        gbase = np.median(np.stack([g for _, v, on, near, g in rows if not near]), 0)
        for _, v, on, near, g in rows:
            scores.append(1.0 - float(v @ base)); labels.append(1 if on else 0); pix.append(float(np.abs(g - gbase).mean()))
    s, l, px = np.array(scores), np.array(labels), np.array(pix)
    if l.sum() == 0 or (1 - l).sum() == 0: print("нет пар для оценки"); return
    from sklearn.metrics import roc_auc_score
    auc = roc_auc_score(l, s)
    thr = float(np.quantile(s[l == 1], 0.10)); fp = float((s[l == 0] > thr).mean())
    print(f"\nкадров {len(t_dino)}, чертёж лёг в {n_fit}; пар клавиша×кадр {len(l)}: палец на клавише {int(l.sum())}, нет {int((1-l).sum())}")
    print(f"AUC {auc:.3f}; порог {thr:.3f} ловит 90 % пальцев, ложных срабатываний на спокойных клавишах {fp:.1%}")
    auc_p = roc_auc_score(l, px); thr_p = float(np.quantile(px[l == 1], 0.10)); fp_p = float((px[l == 0] > thr_p).mean())
    print(f"контроль, пиксельная разница 16×40: AUC {auc_p:.3f}; при 90 % пойманных ложных {fp_p:.1%}")
    print(f"сигнал: палец медиана {np.median(s[l==1]):.3f}, спокойно медиана {np.median(s[l==0]):.3f}; DINO {np.median(t_dino)*1000:.0f} мс на кадр ({len(crops)} клавиш), {dino.dev}")
    json.dump({"auc": auc, "auc_pixel": auc_p, "fp_pixel": fp_p, "thr": thr, "fp": fp, "n": int(len(l)), "pos": int(l.sum()), "ms_frame": float(np.median(t_dino) * 1000)}, open(out / "result.json", "w"), indent=1)

if __name__ == "__main__": main()
