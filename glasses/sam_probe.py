#!/usr/bin/env python3
"""Одиночная проба SAM 3.1: картинка + промпт → задержка, число масок, оверлей.

  .venv/bin/python sam_probe.py --env-file ~/.hermes/profiles/jack/.env image.jpg "white key" "black key"
Оверлей пишется рядом: <image>.<prompt>.sam.jpg ; строка результата печатается в stdout.
"""
from __future__ import annotations

import argparse, asyncio, os, sys, time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
_spec = importlib.util.spec_from_file_location("samtest", Path(__file__).parent / "sam_fret_test.py")
samtest = importlib.util.module_from_spec(_spec); sys.modules["samtest"] = samtest; _spec.loader.exec_module(samtest)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("prompts", nargs="+")
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--max-side", type=int, default=1024)
    ap.add_argument("--repeat", type=int, default=1, help="повторить вызов N раз для оценки задержки")
    args = ap.parse_args()

    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=samtest.load_key(args.env_file))

    img = cv2.imread(str(args.image))
    if img is None:
        raise SystemExit(f"не открыть {args.image}")
    h, w = img.shape[:2]
    scale = min(1.0, args.max_side / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    H, W = img.shape[:2]
    url = samtest.jpeg_data_url(img, max_side=args.max_side)

    for prompt in args.prompts:
        times, masks = [], []
        for _ in range(args.repeat):
            t0 = time.perf_counter()
            masks = await samtest.segment_image(client, url, prompt, (H, W))
            times.append(time.perf_counter() - t0)
        vis = img.copy()
        for k, (oid, m, conf) in enumerate(masks):
            col = samtest.COLORS[k % len(samtest.COLORS)]
            vis[m > 0] = (0.5 * vis[m > 0] + 0.5 * np.array(col)).astype(np.uint8)
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(vis, cnts, -1, col, 2)
            ys, xs = np.nonzero(m)
            if len(xs):
                cv2.putText(vis, f"#{oid} {conf if conf is None else round(conf, 2)}", (int(xs.min()), max(14, int(ys.min()) - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2, cv2.LINE_AA)
        out = args.image.with_suffix("").as_posix() + "." + prompt.replace(" ", "_") + ".sam.jpg"
        cv2.putText(vis, f"{prompt}: {len(masks)} masks, {np.median(times)*1000:.0f} ms", (8, H - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(out, vis)
        areas = sorted((int(m.sum()) for _, m, _ in masks), reverse=True)
        print(f"{args.image.name} | '{prompt}' | masks={len(masks)} | latency ms: "
              f"{' '.join(f'{t*1000:.0f}' for t in times)} | areas={areas[:8]} | {W}x{H} -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
