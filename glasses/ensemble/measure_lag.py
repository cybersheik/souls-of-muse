"""Опоздание со знаком: сильная доля ансамбля минус ОЖИДАЕМАЯ сильная доля записи (та же доля партитуры, не ближайшая).
Прогон как в demo_audio: ноты подаются по времени записи.  python measure_lag.py notes.json beats.json score spe"""
import sys, time, json, importlib, numpy as np; sys.path.insert(0, "ensemble")
from follower import Follower
notes = json.load(open(sys.argv[1])); beats = np.array(json.load(open(sys.argv[2]))); score = importlib.import_module(sys.argv[3]); spe = float(sys.argv[4])
log = []
class Cap:
    def note_on(self, ch, m, v): pass
    def note_off(self, ch, m): pass
f = Follower(score, Cap(), sec_per_eighth=spe, log=lambda m: log.append((time.perf_counter(), m)))
f.start(); t0 = time.perf_counter() + 0.2
for t, m in notes:
    while time.perf_counter() - t0 < t: time.sleep(0.0005)
    f.observe(time.perf_counter(), m)
time.sleep(0.5); f.stop()
rows = []
for tt, m in log:
    if not m.startswith("доля"): continue
    e = int(m.split()[1]); 
    if e < len(beats): rows.append((e, tt - t0, beats[e], (tt - t0) - beats[e]))
lag = np.array([r[3] for r in rows])
print(f"долей {len(rows)}; опоздание ансамбля относительно той же доли записи: медиана {np.median(lag)*1000:+.0f} мс, мин {lag.min()*1000:+.0f}, макс {lag.max()*1000:+.0f}")
print("по долям (номер, опоздание мс):", [(r[0], int(r[3]*1000)) for r in rows[::4]])
