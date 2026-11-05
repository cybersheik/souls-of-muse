# -*- coding: utf-8 -*-
"""Приёмник клипа с очков: mp4 → кадры 10 fps (ffmpeg) → press_dino.py (SAM → чертёж → DINO) → порог.

  .venv-mlx/bin/python keys/ingest_clip.py ~/Downloads/piano.mp4                # настоящее пианино (по умолчанию)
  .venv-mlx/bin/python keys/ingest_clip.py clip.mp4 --profile cardboard         # картонка
  .venv-mlx/bin/python keys/ingest_clip.py clip.mp4 --from 5 --to 40 --fps 10   # отрезок

Кадры и результат: out/clips/<имя клипа>/{frames, press_dino, result.json}. Повторный запуск кадры не пересчитывает.
Клип лежит там, куда его положили; сюда ничего не копируется.
"""
from __future__ import annotations
import argparse, subprocess, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip"); ap.add_argument("--profile", choices=["cardboard", "piano"], default="piano")
    ap.add_argument("--hint", type=int, default=None, help="midi ноты в центре кадра (пианино; по умолчанию 64 = E4)")
    ap.add_argument("--fps", type=float, default=10.0); ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None); ap.add_argument("--scale", type=int, default=1408, help="длинная сторона кадра")
    ap.add_argument("--only-frames", action="store_true", help="только нарезать кадры, DINO не гонять")
    args = ap.parse_args()
    clip = Path(args.clip).expanduser().resolve()
    if not clip.exists(): sys.exit(f"нет файла {clip}")
    out = ROOT / "out" / "clips" / clip.stem; frames = out / "frames"; frames.mkdir(parents=True, exist_ok=True)
    if not any(frames.glob("f_*.jpg")):
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(args.t0)]
        if args.t1 is not None: cmd += ["-to", str(args.t1)]
        cmd += ["-i", str(clip), "-vf", f"fps={args.fps},scale='if(gt(iw,ih),{args.scale},-2)':'if(gt(iw,ih),-2,{args.scale})'",
                "-q:v", "3", str(frames / "f_%04d.jpg")]
        subprocess.run(cmd, check=True)
    fl = sorted(frames.glob("f_*.jpg"))
    print(f"кадров {len(fl)} в {frames}", flush=True)
    if args.only_frames or not fl: return
    cmd = [sys.executable, str(ROOT / "keys" / "press_dino.py"), "--out", str(out / "press_dino"), "--profile", args.profile, "--cache", str(out / "cache")]
    if args.hint is not None: cmd += ["--hint", str(args.hint)]
    cmd += [str(f) for f in fl]
    log = out / "press_dino.log"
    with open(log, "w") as lf:
        r = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=str(ROOT))
    print(open(log).read()[-1500:])
    res = out / "press_dino" / "result.json"
    if res.exists():
        (out / "result.json").write_text(res.read_text()); print(f"итог: {out / 'result.json'}")
    if r.returncode: sys.exit(f"press_dino завершился с кодом {r.returncode}, лог {log}")

if __name__ == "__main__": main()
