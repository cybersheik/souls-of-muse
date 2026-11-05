# -*- coding: utf-8 -*-
"""Проба DINO (Meta) рядом с SAM: отличает ли визуальный эмбеддинг настоящие чёрные клавиши картонки от их отражения в лаке.

На кадрах, где cardboard.fit лёг: маски SAM «black piano key», чей центр попал в чёрную клавишу чертежа = «клавиша»,
остальные = «не клавиша» (отражение, тень, мусор). Каждую маску режем по bbox с запасом, DINOv2 даёт вектор
(CLS + среднее по патчам). Проверка leave-one-frame-out: ближайший центроид и логистическая регрессия.

  .venv-mlx/bin/python keys/dino_probe.py --out out/dino_probe side30/*.jpg
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cardboard
from tune_shadow import load_image, black_polys_sam

class Dino:
    def __init__(self, model="facebook/dinov2-small", size=224):
        import torch; from transformers import AutoImageProcessor, AutoModel
        self.torch = torch; self.dev = "mps" if torch.backends.mps.is_available() else "cpu"
        self.proc = AutoImageProcessor.from_pretrained(model); self.m = AutoModel.from_pretrained(model).to(self.dev).eval(); self.size = size
    def embed(self, crops_bgr):
        import torch
        ims = [cv2.cvtColor(cv2.resize(c, (self.size, self.size), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB) for c in crops_bgr]
        inp = self.proc(images=ims, return_tensors="pt", do_resize=False, do_center_crop=False).to(self.dev)
        with torch.no_grad(): h = self.m(**inp).last_hidden_state
        v = torch.cat([h[:, 0], h[:, 1:].mean(1)], dim=1); v = torch.nn.functional.normalize(v, dim=1)
        return v.float().cpu().numpy()

def bbox_crop(frame, poly, pad=0.25):
    P = np.array(poly, dtype=np.int32); x0, y0 = P.min(0); x1, y1 = P.max(0); H, W = frame.shape[:2]
    px, py = int((x1 - x0) * pad) + 4, int((y1 - y0) * pad) + 4
    return frame[max(0, y0 - py):min(H, y1 + py), max(0, x0 - px):min(W, x1 + px)]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+"); ap.add_argument("--out", default="out/dino_probe")
    ap.add_argument("--max-side", type=int, default=1408); ap.add_argument("--sam-res", type=int, default=1008)
    ap.add_argument("--base-octave", type=int, default=4); ap.add_argument("--model", default="facebook/dinov2-small")
    args = ap.parse_args(); out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    from air_keys import LocalSam; sam = LocalSam(); dino = Dino(args.model)
    X, y, fr, meta = [], [], [], []; t_dino = []
    for ip in args.images:
        p = Path(ip); frame = load_image(p, args.max_side, out / "jpg")
        if frame is None: continue
        H, W = frame.shape[:2]; polys = black_polys_sam(sam, frame, args.sam_res)
        keys, info = cardboard.fit(polys, W, H, args.base_octave, gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        if keys is None: continue
        blacks = [np.array(k["poly"], dtype=np.int32) for k in keys if k["kind"] == "black"]
        labs = []
        for pp in polys:
            c = np.array(pp, dtype=np.float32).mean(0)
            labs.append(1 if any(cv2.pointPolygonTest(b, (float(c[0]), float(c[1])), False) >= 0 for b in blacks) else 0)
        crops = [bbox_crop(frame, pp) for pp in polys]; crops = [c for c in crops if c.size]
        if not crops: continue
        t0 = time.perf_counter(); E = dino.embed(crops); t_dino.append((time.perf_counter() - t0, len(crops)))
        X.extend(E); y.extend(labs[:len(E)]); fr.extend([p.name] * len(E)); meta.append((p.name, sum(labs), len(labs) - sum(labs)))
        print(f"{p.name}: масок {len(polys)}, клавиш {sum(labs)}, прочих {len(labs)-sum(labs)}, DINO {t_dino[-1][0]*1000:.0f} мс", flush=True)
        # картинка для глаз: зелёные = клавиша, красные = прочее
        vis = frame.copy()
        for pp, l in zip(polys, labs): cv2.polylines(vis, [np.array(pp, dtype=np.int32)], True, (60, 220, 60) if l else (0, 0, 255), 3)
        cv2.imwrite(str(out / p.name), cv2.resize(vis, None, fx=0.5, fy=0.5), [cv2.IMWRITE_JPEG_QUALITY, 80])
    X = np.array(X); y = np.array(y); fr = np.array(fr)
    print(f"\nвсего масок {len(y)}: клавиш {int(y.sum())}, прочих {int((1-y).sum())}, кадров {len(set(fr))}")
    if len(set(fr)) < 2 or y.sum() == 0 or (1 - y).sum() == 0: print("мало данных"); return
    # leave-one-frame-out
    from sklearn.linear_model import LogisticRegression
    ok_nc = ok_lr = n = 0
    for f in sorted(set(fr)):
        tr, te = fr != f, fr == f
        c1, c0 = X[tr][y[tr] == 1].mean(0), X[tr][y[tr] == 0].mean(0)
        pred_nc = (X[te] @ c1 > X[te] @ c0).astype(int)
        lr = LogisticRegression(max_iter=2000, C=1.0).fit(X[tr], y[tr]); pred_lr = lr.predict(X[te])
        ok_nc += int((pred_nc == y[te]).sum()); ok_lr += int((pred_lr == y[te]).sum()); n += int(te.sum())
    sims = X @ X.T; same = sims[np.ix_(y == 1, y == 1)]; cross = sims[np.ix_(y == 1, y == 0)]
    print(f"leave-one-frame-out: ближайший центроид {ok_nc}/{n} = {ok_nc/n:.0%}, логрегрессия {ok_lr}/{n} = {ok_lr/n:.0%}")
    print(f"косинус клавиша–клавиша {same.mean():.3f}, клавиша–прочее {cross.mean():.3f}")
    tt = sum(t for t, _ in t_dino); nn = sum(k for _, k in t_dino); print(f"DINO: {tt/len(t_dino)*1000:.0f} мс на кадр, {tt/nn*1000:.1f} мс на маску, устройство {dino.dev}")
    json.dump({"frames": meta, "n": int(n), "nc": ok_nc, "lr": ok_lr}, open(out / "result.json", "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__": main()
