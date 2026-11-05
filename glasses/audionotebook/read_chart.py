#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сетка аккордов с фото (пюпитр, тетрадь, распечатка) → песня для аудиотетради через Muse Spark (Meta Model API).

  .venv/bin/python audionotebook/read_chart.py --env-file ~/.hermes/profiles/jack/.env --out out/notebook/song.json chart.jpg
Пишет JSON в формате SONG страницы (title, artist, key, timeSignature, beatsPerBar, sections, form, hints).
"""
from __future__ import annotations
import argparse, base64, json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import importlib.util
_spec = importlib.util.spec_from_file_location("samtest", Path(__file__).resolve().parent.parent / "sam_fret_test.py")
samtest = importlib.util.module_from_spec(_spec); sys.modules["samtest"] = samtest; _spec.loader.exec_module(samtest)

PROMPT = """This photo shows a chord chart or lead sheet for a song (chords over bars, maybe lyrics). Read it and return ONLY a JSON object, no prose, in exactly this shape:
{"title": "...", "artist": "...", "key": "C", "timeSignature": "4/4", "beatsPerBar": 4, "subdivision": 1, "defaultTempo": 80, "cueLeadBeats": 1,
 "sections": {"verse": {"name": {"en": "Verse", "ru": "Куплет"}, "bars": [["C"], ["Am"], ["F", "G"]]}},
 "form": ["verse", "chorus"], "hints": [{"chord": "F", "leadBeats": 2, "en": "prepare F barre", "ru": "готовь фа баррэ"}]}
Rules: one array per bar; two chords in a bar = two entries; repeat signs expanded; section ids lowercase ascii (verse, chorus, bridge, intro, outro); form lists sections in playing order; keep chord symbols as written (C, Am, F#m7, G/B); if tempo or time signature is not printed, choose sensible values; put a hint only for barre or awkward changes. No lyrics."""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("image", type=Path); ap.add_argument("--env-file"); ap.add_argument("--model", default="muse-spark-1.3"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from openai import OpenAI
    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=samtest.load_key(a.env_file))
    data = base64.b64encode(a.image.read_bytes()).decode("ascii"); mime = "image/png" if a.image.suffix.lower() == ".png" else "image/jpeg"
    t0 = time.perf_counter()
    resp = client.chat.completions.create(model=a.model, max_tokens=3000, messages=[{"role": "user", "content": [
        {"type": "text", "text": PROMPT}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}]}])
    text = resp.choices[0].message.content or ""
    print(f"{a.image.name}: {time.perf_counter() - t0:.1f} s, {len(text)} chars, usage={getattr(resp, 'usage', None)}", flush=True)
    m = re.search(r"\{.*\}", text, re.S)
    if not m: sys.exit("в ответе нет JSON:\n" + text[:800])
    song = json.loads(m.group(0))
    for k in ("sections", "form"):
        if k not in song: sys.exit(f"в песне нет поля {k}")
    song.setdefault("title", a.image.stem); song.setdefault("artist", ""); song.setdefault("beatsPerBar", 4); song.setdefault("subdivision", 1); song.setdefault("defaultTempo", 80)
    for sid, sec in song["sections"].items():
        sec["bars"] = [[str(c) for c in (b if isinstance(b, list) else [b])] for b in sec.get("bars", [])]
        sec.setdefault("name", {"en": sid.title(), "ru": sid.title()})
    song["form"] = [s for s in song["form"] if s in song["sections"]] or list(song["sections"])
    song["source"] = {"image": str(a.image), "model": a.model, "read_at": time.strftime("%Y-%m-%d %H:%M")}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(song, ensure_ascii=False, indent=1))
    print("→", a.out, "| тактов:", sum(len(song["sections"][s]["bars"]) for s in song["form"]), flush=True)

if __name__ == "__main__": main()
