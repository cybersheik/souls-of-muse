# -*- coding: utf-8 -*-
"""Локальный VLM-судья: Llama 3.2 Vision 11B (MLX 4-bit) смотрит на кроп и отвечает, лежит ли кончик пальца на обведённой клавише.

  .venv-mlx/bin/python keys/judge_llama.py out/judge_crops            # manifest.json → точность, время на кадр
  .venv-mlx/bin/python keys/judge_llama.py --image one.jpg            # один кроп

Модель: mlx-community/Llama-3.2-11B-Vision-Instruct-4bit (скачана с разрешения Айдара 02.11.2026).
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path

MODEL = "mlx-community/Llama-3.2-11B-Vision-Instruct-4bit"
PROMPT = ("Photo from the pianist's own glasses: a paper piano keyboard and a hand. One key is outlined in bright green. "
          "Is a fingertip resting on the green-outlined key? Answer with one word: yes or no.")

def load(model=MODEL):
    from mlx_vlm import load as _load
    from mlx_vlm.utils import load_config
    m, proc = _load(model); cfg = load_config(model)
    return m, proc, cfg

def ask(m, proc, cfg, image, prompt=PROMPT, max_tokens=4):
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template
    fp = apply_chat_template(proc, cfg, prompt, num_images=1)
    t0 = time.perf_counter()
    r = generate(m, proc, fp, image=[str(image)], max_tokens=max_tokens, verbose=False, temperature=0.0)
    txt = r.text if hasattr(r, "text") else str(r)
    dt = time.perf_counter() - t0
    low = txt.strip().lower()
    ans = "yes" if re.match(r"\W*yes", low) else "no" if re.match(r"\W*no", low) else "?"
    return ans, txt.strip(), dt

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", default="out/judge_crops"); ap.add_argument("--image", default=None)
    ap.add_argument("--model", default=MODEL); ap.add_argument("--prompt", default=PROMPT)
    args = ap.parse_args()
    t0 = time.perf_counter(); m, proc, cfg = load(args.model); print(f"модель загружена за {time.perf_counter()-t0:.1f} с", flush=True)
    if args.image:
        ans, txt, dt = ask(m, proc, cfg, args.image, args.prompt); print(f"{ans:4s} {dt:5.2f} с  «{txt}»"); return
    man = json.load(open(Path(args.folder) / "manifest.json")); ok = 0; times = []
    ask(m, proc, cfg, Path(args.folder) / man[0]["file"])            # прогрев
    print(f"{'кроп':<12}{'правда':<7}{'ответ':<7}{'с':>6}  обведена / под кончиком")
    for r in man:
        ans, txt, dt = ask(m, proc, cfg, Path(args.folder) / r["file"]); times.append(dt); hit = ans == r["truth"]; ok += hit
        print(f"{r['file']:<12}{r['truth']:<7}{ans:<7}{dt:6.2f}  {r['outlined']} / {r['under_tip']}  {'' if hit else '← мимо'} «{txt}»", flush=True)
    import statistics as s
    print(f"\nточность {ok}/{len(man)} = {ok/len(man):.0%}; время на кроп медиана {s.median(times):.2f} с, макс {max(times):.2f} с")
    yes = [r for r in man if r["truth"] == "yes"]; print(f"(из них «да» {len(yes)}, «нет» {len(man)-len(yes)})")

if __name__ == "__main__": main()
