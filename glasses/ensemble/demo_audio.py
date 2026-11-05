"""Слышимая проба на живой записи: играем WAV солиста через динамики, в те же моменты подаём снятые из него ноты
следящему ансамблю (как будто их увидели очки), ансамбль подыгрывает по снятой партитуре.
  python demo_audio.py clips/aidar_audio/k_elise_aidar.wav clips/aidar_audio/k_elise_aidar.notes.json k_elise_aidar 0.40 [free]
  free — режим без метра (R-04): аккорд и бас по нотам солиста"""
import sys, time, json, importlib, threading; sys.path.insert(0, "ensemble"); sys.path.insert(0, "keys")
import numpy as np, soundfile as sf, sounddevice as sd
from follower import Follower; from player import EnsemblePlayer
wav, notes_path, score_name, spe = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
score = importlib.import_module(score_name); notes = json.load(open(notes_path))
y, sr = sf.read(wav, dtype="float32"); y = y if y.ndim == 1 else y.mean(1)
free = len(sys.argv) > 5 and sys.argv[5] == "free"
ens = EnsemblePlayer(); f = Follower(score, ens, sec_per_eighth=spe, meter=not free, log=lambda m: None); f.start()
t_start = None
def play():
    global t_start; t_start = time.perf_counter(); sd.play(y * 0.9, sr); sd.wait()
th = threading.Thread(target=play); th.start()
while t_start is None: time.sleep(0.001)
for t, m in notes:
    while time.perf_counter() - t_start < t: time.sleep(0.001)
    f.observe(time.perf_counter(), m)
th.join(); time.sleep(0.8); f.stop()
print(f"нот подано {len(notes)}, сопоставлено {f.matches}, темп в конце {60/(f.T*2):.0f} bpm")
