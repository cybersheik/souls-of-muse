#!/usr/bin/env python3
"""Чтение страниц договора с фото через Muse Spark (Meta Model API, OpenAI-совместимый chat).

  .venv/bin/python council/read_pages.py --env-file ~/.hermes/profiles/jack/.env page1.jpg page2.jpg
Печатает задержку и возвращает транскрипцию в council/out/pages-<stamp>.md.
"""
from __future__ import annotations

import argparse, base64, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import importlib.util
_spec = importlib.util.spec_from_file_location("samtest", Path(__file__).resolve().parent.parent / "sam_fret_test.py")
samtest = importlib.util.module_from_spec(_spec); sys.modules["samtest"] = samtest; _spec.loader.exec_module(samtest)

PROMPT = ("Transcribe this page of a legal contract exactly as printed, preserving clause numbers and headings. "
          "Do not summarise or comment. If a word is unreadable, write [illegible].")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--model", default="muse-spark-1.3")
    args = ap.parse_args()

    from openai import OpenAI
    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=samtest.load_key(args.env_file))
    out_dir = Path(__file__).resolve().parent / "out"; out_dir.mkdir(exist_ok=True)
    out = out_dir / f"pages-{time.strftime('%Y%m%d-%H%M%S')}.md"
    chunks = []
    for img in args.images:
        data = base64.b64encode(img.read_bytes()).decode("ascii")
        mime = "image/png" if img.suffix.lower() == ".png" else "image/jpeg"
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
            ]}],
            max_tokens=4000,
        )
        dt = time.perf_counter() - t0
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        print(f"{img.name}: {dt:.1f} s, {len(text)} chars, usage={usage}")
        chunks.append(f"## {img.name}\n\n{text}\n")
    out.write_text("\n".join(chunks), encoding="utf-8")
    print("→", out)


if __name__ == "__main__":
    main()
