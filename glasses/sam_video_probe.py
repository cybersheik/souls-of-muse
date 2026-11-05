#!/usr/bin/env python3
"""Видеорежим SAM 3.1: загрузить клип через Files API, попросить вести объект по кадрам, измерить время.

  .venv/bin/python sam_video_probe.py --env-file ~/.hermes/profiles/jack/.env clip.mp4 "finger"
Печатает: время загрузки, время ответа, число кадров и объектов, пишет 4 кадра с масками в out/video_probe/.
"""
from __future__ import annotations

import argparse, asyncio, sys, time
from pathlib import Path

import cv2, numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
_spec = importlib.util.spec_from_file_location("samtest", Path(__file__).parent / "sam_fret_test.py")
samtest = importlib.util.module_from_spec(_spec); sys.modules["samtest"] = samtest; _spec.loader.exec_module(samtest)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("prompt")
    ap.add_argument("--env-file", default=None)
    args = ap.parse_args()
    from openai import AsyncOpenAI
    from meta_sam_parser import (decode_mask_to_raster, parse_responses_stream, video_segmentation_format,
                                 SegmentationMaskRecord, SegmentationBoxRecord)
    client = AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=samtest.load_key(args.env_file))

    t0 = time.perf_counter()
    with open(args.video, "rb") as fh:
        f = await client.files.create(file=fh, purpose="user_data")
    t_up = time.perf_counter() - t0
    print(f"upload: {t_up:.1f} s, file_id={f.id}")

    t1 = time.perf_counter()
    stream = await client.responses.create(
        model="sam-3.1", stream=True,
        metadata={"include_confidence": "true", "mask_encoding": "one_bit"},
        input=[{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": args.prompt},
            {"type": "input_video", "file_id": f.id},
        ]}],
    )
    first_delta = None
    parsed = parse_responses_stream(stream, video_segmentation_format())
    frames_seen = set()
    async for snap in parsed:
        if first_delta is None:
            first_delta = time.perf_counter() - t1
        for r in snap.records:
            if getattr(r, "frame", None) is not None: frames_seen.add(r.frame.frame_index)
    result = await parsed.final_result()
    t_resp = time.perf_counter() - t1
    try:
        await stream.close()
    except Exception:
        pass

    masks = [r for r in result.records if isinstance(r, SegmentationMaskRecord)]
    boxes = [r for r in result.records if isinstance(r, SegmentationBoxRecord)]
    frames = sorted({r.frame.frame_index for r in masks if r.frame})
    objs = sorted({r.object_id for r in masks})
    print(f"response: {t_resp:.1f} s (first data after {first_delta:.1f} s); frames with masks: {len(frames)} "
          f"(first {frames[:5]} … last {frames[-3:] if frames else []}); objects: {len(objs)} {objs[:8]}")

    # нарисовать 4 кадра
    cap = cv2.VideoCapture(str(args.video)); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out = Path(__file__).parent / "out" / "video_probe"; out.mkdir(parents=True, exist_ok=True)
    pick = [frames[i] for i in sorted(set([0, len(frames) // 3, 2 * len(frames) // 3, len(frames) - 1]))] if frames else []
    for fi in pick:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi); ok, img = cap.read()
        if not ok: continue
        H, W = img.shape[:2]
        for k, r in enumerate([m for m in masks if m.frame and m.frame.frame_index == fi]):
            raster = np.frombuffer(decode_mask_to_raster(r.mask), dtype=np.uint8).reshape(r.mask.height, r.mask.width)
            b = r.bounds; x0, y0, x1, y1 = int(b.left), int(b.top), int(b.right), int(b.bottom)
            x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, max(x0 + 1, x1)), min(H, max(y0 + 1, y1))
            patch = cv2.resize(raster, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
            col = np.array(samtest.COLORS[int(r.object_id) % len(samtest.COLORS)] if r.object_id.isdigit() else samtest.COLORS[k % 6])
            roi = img[y0:y1, x0:x1]; roi[patch > 0] = (0.5 * roi[patch > 0] + 0.5 * col).astype(np.uint8)
            cv2.putText(img, f"#{r.object_id}", (x0, max(12, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, tuple(int(c) for c in col), 2)
        cv2.putText(img, f"{args.video.name} frame {fi}/{n} '{args.prompt}'", (8, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imwrite(str(out / f"{args.video.stem}_{args.prompt.replace(' ', '_')}_f{fi:04d}.jpg"), img)
    print("→", out)


if __name__ == "__main__":
    asyncio.run(main())
