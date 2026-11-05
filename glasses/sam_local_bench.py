#!/usr/bin/env python3
"""Локальный SAM 3.1 (MLX, mlx-vlm) на ML1: задержка по кадру и качество масок против облачного SAM.

  .venv-mlx/bin/python sam_local_bench.py image.jpg --prompts finger "white piano key" --res 1008 504 224
Пишет оверлеи в out/local_sam/<image>.<prompt>.r<res>.jpg и печатает мс на кадр (после прогрева).
"""
from __future__ import annotations
import argparse, time
from pathlib import Path
import numpy as np, cv2
from PIL import Image

COLORS = [(0, 200, 255), (255, 120, 0), (0, 255, 120), (255, 0, 200), (200, 255, 0), (120, 0, 255)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--prompts", nargs="+", default=["finger"])
    ap.add_argument("--res", nargs="+", type=int, default=[1008, 504])
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--model", default="mlx-community/sam3.1-bf16")
    args = ap.parse_args()

    from mlx_vlm.utils import load_model, get_model_path
    from mlx_vlm.models.sam3.generate import Sam3Predictor
    from mlx_vlm.models.sam3_1.processing_sam3_1 import Sam31Processor
    t0 = time.perf_counter()
    mp = get_model_path(args.model); model = load_model(mp)
    processor = Sam31Processor.from_pretrained(str(mp))
    predictor = Sam3Predictor(model, processor, score_threshold=args.threshold)
    print(f"model loaded in {time.perf_counter()-t0:.1f} s")
    out = Path(__file__).parent / "out" / "local_sam"; out.mkdir(parents=True, exist_ok=True)

    for res in args.res:
        processor.image_size = res
        for img_path in args.images:
            image = Image.open(img_path).convert("RGB"); W, H = image.size
            for prompt in args.prompts:
                predictor.predict(image, text_prompt=prompt)          # прогрев (компиляция ядер)
                times = []
                for _ in range(args.repeat):
                    t = time.perf_counter(); r = predictor.predict(image, text_prompt=prompt); times.append(time.perf_counter() - t)
                n = len(r.scores)
                vis = np.array(image).copy()
                for i in range(n):
                    m = r.masks[i]
                    if m.shape != (H, W): m = cv2.resize(m.astype(np.float32), (W, H))
                    b = m > 0; col = np.array(COLORS[i % 6])
                    vis[b] = (vis[b] * 0.5 + col * 0.5).astype(np.uint8)
                    x1, y1, x2, y2 = [int(v) for v in r.boxes[i]]
                    cv2.putText(vis, f"{r.scores[i]:.2f}", (x1, max(12, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, tuple(int(c) for c in col), 2)
                ms = [int(x * 1000) for x in times]
                cv2.putText(vis, f"local SAM3.1 r{res} '{prompt}': {n} masks, {int(np.median(times)*1000)} ms", (8, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.imwrite(str(out / f"{img_path.stem}.{prompt.replace(' ', '_')}.r{res}.jpg"), cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
                print(f"r{res:4d} {img_path.name:28s} {prompt:18s} masks={n:2d} ms={ms} median={int(np.median(times)*1000)}", flush=True)

if __name__ == "__main__":
    main()
