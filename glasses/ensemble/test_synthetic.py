"""Синтетический солист: мелодия «К Элизе» с дрейфом темпа, пропусками 35 % нот и дрожанием 25 мс.
Проверяем: позиция удерживается, темп отслеживается, доли планируются вовремя."""
import sys, time, random; sys.path.insert(0, "ensemble")
import fur_elise as score; from follower import Follower
random.seed(1)
class DryOut:
    def __init__(self): self.events = []
    def note_on(self, ch, m, v): self.events.append((time.perf_counter(), ch, m, v))
    def note_off(self, ch, m): pass
out = DryOut(); logs = []
f = Follower(score, out, sec_per_eighth=0.25, log=logs.append)
passes = 3; T0, T1 = 0.26, 0.19                            # ускоряемся с ~115 до ~158 четвертей/мин... в восьмых: 0.26→0.19 с
notes = []
for k in range(passes):
    for (st, m, d) in sorted(score.MELODY):
        notes.append((st + k * score.LENGTH, m))
total = notes[-1][0]
t0 = time.perf_counter() + 0.3; real = []
for st, m in notes:
    T = T0 + (T1 - T0) * (st / total)
    real.append((st, T, m))
# интегрируем время: dt = T(st) * dst
tt = 0.0; prev = 0.0; sched = []
for st, T, m in real:
    tt += (st - prev) * T; prev = st
    if random.random() < 0.35: continue                      # пропуск (зрение не увидело)
    sched.append((tt + random.gauss(0, 0.025), st, m, T))
f.start(); errs = []; start = time.perf_counter()
for t_rel, st, m, T in sched:
    while time.perf_counter() - start < t_rel: time.sleep(0.001)
    now = time.perf_counter(); p = f.predicted(now)             # ошибка ПРЕДСКАЗАНИЯ до учёта этой ноты — это и чувствует слушатель
    f.observe(now, m)
    if p is not None: errs.append((st, p - st, f.T, T))
time.sleep(0.5); f.stop()
import statistics as S
print(f"нот подано {len(sched)} из {len(notes)}; сопоставлено {f.matches}")
late = [e for e in errs if e[0] > 10]
print(f"ошибка позиции после разгона: медиана {S.median(abs(e[1]) for e in late):.2f} восьмых, макс {max(abs(e[1]) for e in late):.2f}")
print(f"темп в конце: оценка {late[-1][2]*1000:.0f} мс/восьмую, истина {late[-1][3]*1000:.0f}")
beats = [e for e in logs if e.startswith("доля")]
print(f"долей сыграно {len(beats)}; первые: {beats[:3]}; последние: {beats[-2:]}")
print([l for l in logs if l.startswith("старт")])
