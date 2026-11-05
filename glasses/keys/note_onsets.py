# -*- coding: utf-8 -*-
"""Удары по клавишам из аудиодорожки записи: момент и нота. Инструмент РАЗМЕТКИ для оценки стенда по записи,
не канал стенда (стенд работает по видео). Спектральный поток → пики = удары; высота тона после удара →
нота (произведение гармоник, 150–1300 Гц). Выход: json [{t, midi, name, f0, conf}].

  .venv-mlx/bin/python keys/note_onsets.py in.wav --out onsets.json --from 10 --to 40
"""
from __future__ import annotations
import argparse, json, wave
import numpy as np

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def name(m): return f"{NAMES[m % 12]}{m // 12 - 1}"

def load(path):
    w = wave.open(path); sr = w.getframerate(); n = w.getnframes(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    return x, sr

def spectrogram(x, sr, win=2048, hop=160):
    nfr = (len(x) - win) // hop
    w = np.hanning(win).astype(np.float32)
    idx = np.arange(win)[None, :] + hop * np.arange(nfr)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * w, axis=1))
    f = np.fft.rfftfreq(win, 1 / sr)
    return S, f, hop / sr

def onsets(S, f, dt, lo=200, hi=3000, min_gap=0.15, k=2.5):
    band = (f >= lo) & (f <= hi)
    L = np.log1p(S[:, band] * 50)
    flux = np.maximum(L[1:] - L[:-1], 0).sum(1); flux = np.concatenate([[0], flux])
    # сглаживание и адаптивный порог: медиана ± MAD в окне 1 с
    win = int(1.0 / dt); half = win // 2
    thr = np.empty_like(flux)
    for i in range(len(flux)):
        seg = flux[max(0, i - half): i + half + 1]; med = np.median(seg); mad = np.median(np.abs(seg - med)) + 1e-6
        thr[i] = med + k * mad * 1.4826
    peaks = []; last = -1e9; r = int(0.05 / dt)
    for i in range(r, len(flux) - r):
        if flux[i] >= thr[i] and flux[i] == flux[i - r: i + r + 1].max() and flux[i] > 0.02 * flux.max():
            if i * dt - last >= min_gap: peaks.append(i); last = i * dt
            elif flux[i] > flux[peaks[-1]]: peaks[-1] = i; last = i * dt
    return peaks, flux, thr

def pitch(S, f, dt, i, t0=0.06, t1=0.35, lo=150, hi=1300):
    a, b = i + int(t0 / dt), i + int(t1 / dt)
    if b >= len(S): return None
    # спектр после удара минус спектр до удара: дозвон предыдущих клавиш уходит
    before = S[max(0, i - int(0.25 / dt)): max(1, i - int(0.02 / dt))].mean(0)
    m = np.maximum(S[a:b].mean(0) - before, 0)
    grid = np.arange(lo, hi, 1.0)
    g = lambda fr: np.interp(fr, f, m) + 1e-6
    # произведение трёх гармоник; октавой ниже не уходим, если сама основная слабее половины второй
    hps = g(grid) * g(2 * grid) * g(3 * grid)
    hps[g(grid) < 0.5 * g(2 * grid)] *= 0.1
    j = int(np.argmax(hps)); f0 = float(grid[j])
    far = np.abs(np.log2(grid / f0)) > 1 / 24
    conf = float(hps[j] / (hps[far].max() + 1e-9)) if far.any() else 1.0
    midi = int(round(69 + 12 * np.log2(f0 / 440)))
    return f0, midi, conf

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav"); ap.add_argument("--out"); ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=1e9); ap.add_argument("--k", type=float, default=2.5)
    args = ap.parse_args()
    x, sr = load(args.wav); S, f, dt = spectrogram(x, sr)
    peaks, flux, thr = onsets(S, f, dt, k=args.k)
    rows = []
    for i in peaks:
        t = i * dt
        if not (args.t0 <= t <= args.t1): continue
        p = pitch(S, f, dt, i)
        if p is None: continue
        f0, midi, conf = p
        rows.append({"t": round(t, 2), "midi": midi, "name": name(midi), "f0": round(f0, 1), "conf": round(conf, 2), "flux": round(float(flux[i] / flux.max()), 2)})
    for r in rows: print(f"{r['t']:7.2f} с  {r['name']:4s} midi {r['midi']:3d}  f0 {r['f0']:7.1f}  уверенность {r['conf']:5.2f}  сила {r['flux']:.2f}")
    print(f"ударов {len(rows)}")
    if args.out: json.dump(rows, open(args.out, "w"), ensure_ascii=False, indent=0)

if __name__ == "__main__": main()
