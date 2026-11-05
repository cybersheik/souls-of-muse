"""Снять ноты (момент, midi) из монофонической записи: онсеты + высота по pyin в окне после атаки.
  python notes_from_audio.py in.wav out.json"""
import sys, json, numpy as np, librosa
y, sr = librosa.load(sys.argv[1], sr=22050, mono=True)
on = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=False, delta=0.05, wait=3)
f0, vf, vp = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr, frame_length=2048, hop_length=256)
t_f0 = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=256)
notes = []
for t in on:
    sel = (t_f0 >= t + 0.02) & (t_f0 <= t + 0.12) & vf
    if sel.sum() < 2: continue
    midi = int(round(float(np.median(librosa.hz_to_midi(f0[sel])))))
    if notes and notes[-1][1] == midi and t - notes[-1][0] < 0.08: continue
    notes.append((float(t), midi))
json.dump(notes, open(sys.argv[2], "w"))
tempo = librosa.feature.tempo(y=y, sr=sr)[0]
print(f"длительность {len(y)/sr:.1f} с, онсетов {len(on)}, нот с высотой {len(notes)}, темп по librosa ~{tempo:.0f} bpm")
names = [librosa.midi_to_note(m) for _, m in notes]
print("первые 16 нот:", " ".join(names[:16]))
ioi = np.diff([t for t, _ in notes]); print(f"медианный интервал между нотами {np.median(ioi)*1000:.0f} мс")
