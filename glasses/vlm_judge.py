#!/usr/bin/env python3
"""Второй сигнал для тренера пальцев: Muse Spark смотрит на кадр и судит постановку.

  .venv/bin/python vlm_judge.py --env-file ~/.hermes/profiles/jack/.env clips/a.mp4 clips/b.mp4 --fps 0.5 --max-frames 8
Печатает по кадру: вердикт (curled/flat/unclear), уверенность, короткую причину; в конце — сводку по клипу.
"""
from __future__ import annotations

import argparse, json, re, sys, time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
_spec = importlib.util.spec_from_file_location("samtest", Path(__file__).parent / "sam_fret_test.py")
samtest = importlib.util.module_from_spec(_spec); sys.modules["samtest"] = samtest; _spec.loader.exec_module(samtest)

PROMPT = (
    "You are a guitar teacher looking through the player's own glasses at their fretting (left) hand. "
    "Judge the fingers that are pressing strings. Correct technique: each finger is curved and stands on its fingertip, "
    "the last joint roughly perpendicular to the fretboard, like an arch or a square on the neck. Wrong technique: "
    "the finger is straight and lies flat across the strings, the last joint collapsed, like a triangle on the neck. "
    "Answer ONLY with JSON: {\"verdict\": \"curled\"|\"flat\"|\"unclear\", \"confidence\": 0..1, "
    "\"fingers_flat\": [\"index\",\"middle\",\"ring\",\"pinky\"] (those lying flat, may be empty), \"reason\": \"<12 words max>\"}"
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--fps", type=float, default=0.5)
    ap.add_argument("--max-frames", type=int, default=8)
    ap.add_argument("--max-side", type=int, default=1280)
    ap.add_argument("--model", default="muse-spark-1.3")
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--crop", default=None, help="доли кадра x0,y0,x1,y1, например 0,0.45,0.65,1 — вырезать область руки")
    ap.add_argument("--ref-good", type=Path, default=None, help="эталонный кадр с правильной постановкой (few-shot)")
    ap.add_argument("--ref-bad", type=Path, default=None, help="эталонный кадр с лежащими пальцами (few-shot)")
    args = ap.parse_args()

    from openai import OpenAI
    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=samtest.load_key(args.env_file))

    def crop(frame):
        if not args.crop:
            return frame
        x0, y0, x1, y1 = [float(v) for v in args.crop.split(",")]
        H, W = frame.shape[:2]
        return frame[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]

    refs = []
    if args.ref_good and args.ref_bad:
        for label, p in (("CORRECT technique (curled, on fingertips)", args.ref_good), ("WRONG technique (flat, collapsed)", args.ref_bad)):
            img = cv2.imread(str(p))
            refs += [{"type": "text", "text": f"Reference example of {label}, same player, same glasses:"},
                     {"type": "image_url", "image_url": {"url": samtest.jpeg_data_url(crop(img), max_side=args.max_side)}}]

    for video in args.videos:
        verdicts, times = [], []
        for idx, t, frame in samtest.sample_frames(video, args.fps, args.max_frames, 4000):
            url = samtest.jpeg_data_url(crop(frame), max_side=args.max_side)
            t0 = time.perf_counter()
            # Spark тратит на рассуждение reasoning-токены из того же лимита — даём запас и просим низкое усилие
            content = [{"type": "text", "text": PROMPT}] + refs + [
                {"type": "text", "text": "Now judge THIS frame:"},
                {"type": "image_url", "image_url": {"url": url}},
            ]
            resp = client.chat.completions.create(
                model=args.model, max_tokens=2500,
                extra_body={"reasoning_effort": "low"},
                messages=[{"role": "user", "content": content}],
            )
            dt = time.perf_counter() - t0
            text = resp.choices[0].message.content or ""
            m = re.search(r"\{.*\}", text, re.S)
            try:
                j = json.loads(m.group(0)) if m else {}
            except Exception:
                j = {}
            v = j.get("verdict", "?"); c = j.get("confidence"); r = j.get("reason", text[:80].replace("\n", " "))
            verdicts.append(v); times.append(dt)
            print(f"{video.name} f{idx:05d} t={t:5.1f}s {dt:4.1f}s → {v:8s} conf={c} flat={j.get('fingers_flat')} | {r}", flush=True)
        from collections import Counter
        cnt = Counter(verdicts)
        print(f"== {video.name}: {dict(cnt)}; средняя задержка {sum(times)/max(1,len(times)):.1f} s")


if __name__ == "__main__":
    main()
