"""Сухой прогон в реальном времени: ноты записи по их времени → моменты выдачи долей ансамбля → ровность и
совпадение сильных долей ансамбля с отслеженными долями записи.  python measure_beats.py notes.json score spe [beats.json]"""
import sys, time, json, importlib, numpy as np; sys.path.insert(0, "ensemble")
from follower import Follower
notes = json.load(open(sys.argv[1])); score = importlib.import_module(sys.argv[2]); spe = float(sys.argv[3])
ref = np.array(json.load(open(sys.argv[4]))) if len(sys.argv) > 4 else np.array([t for t, _ in notes])
class Cap:
    def __init__(self): self.on = []
    def note_on(self, ch, m, v): self.on.append((time.perf_counter(), ch, m, v))
    def note_off(self, ch, m): pass
cap = Cap(); f = Follower(score, cap, sec_per_eighth=spe, log=lambda m: None); f.start()
t0 = time.perf_counter() + 0.2
for t, m in notes:
    while time.perf_counter() - t0 < t: time.sleep(0.0005)
    f.observe(time.perf_counter(), m)
time.sleep(0.5); f.stop()
strong = np.array([t - t0 for t, ch, m, v in cap.on if ch == 0 and v >= 90]); ioi = np.diff(strong)
allb = np.array([t - t0 for t, ch, m, v in cap.on if ch == 2]) ; 
print(f"сильных долей {len(strong)}; интервал медиана {np.median(ioi)*1000:.0f} мс, разброс MAD {np.median(abs(ioi-np.median(ioi)))*1000:.0f} мс, мин {ioi.min()*1000:.0f}, макс {ioi.max()*1000:.0f}")
dev = np.array([np.min(abs(ref - b)) for b in strong]); print(f"сильная доля ансамбля vs ближайшая доля записи: медиана {np.median(dev)*1000:.0f} мс, 90% {np.percentile(dev,90)*1000:.0f} мс, первая доля ансамбля в {strong[0]:.2f} с")
