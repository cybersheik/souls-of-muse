# -*- coding: utf-8 -*-
"""Опоздание ансамбля на синтетическом солисте по «К Элизе» при ЗАДАННОМ темпе (без звука, в реальном времени).
Солист играет MELODY ровно (sec_per_eighth = spe) с пропусками и дрожанием, как со зрения. Для каждой доли e,
которую ансамбль объявил («доля e»), считаем: момент объявления − истинный момент этой же восьмой у солиста.
Плюс к «доле» меряем бас (ch 0) на сильных долях — это то, что слышит руководитель.
  .venv-mlx/bin/python ensemble/measure_lag_synth.py --spe 0.857 [--passes 2 --miss 0.35 --jitter 0.025 --latency 0 --seed 1]
  --spe: секунд на восьмую (60 восьмых/мин = 1.0; 80 = 0.75; 120 = 0.5; 150 = 0.4).
  --latency: задержка между истинным нажатием и observe() (зрение: кадр + подтверждение), секунд."""
import sys, time, random, argparse, statistics as S; sys.path.insert(0, "ensemble")
import fur_elise as score; from follower import Follower

ap = argparse.ArgumentParser()
ap.add_argument("--spe", type=float, default=0.857); ap.add_argument("--passes", type=int, default=2)
ap.add_argument("--miss", type=float, default=0.35); ap.add_argument("--jitter", type=float, default=0.025)
ap.add_argument("--latency", type=float, default=0.0); ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--init", type=float, default=None, help="стартовое sec_per_eighth следящего (по умолчанию как в air_keys: 0.6)")
ap.add_argument("--quiet", action="store_true")
a = ap.parse_args(); random.seed(a.seed)

class Cap:
    def __init__(self): self.on = []
    def note_on(self, ch, m, v): self.on.append((time.perf_counter(), ch, m, v))
    def note_off(self, ch, m): pass
cap = Cap(); logs = []
kw = {} if a.init is None else {"sec_per_eighth": a.init}
f = Follower(score, cap, log=lambda m: logs.append((time.perf_counter(), m)), **kw)
notes = [(st + k * score.LENGTH, m) for k in range(a.passes) for (st, m, _) in sorted(score.MELODY)]
sched = [(st * a.spe + a.latency + random.gauss(0, a.jitter), st, m) for st, m in notes if random.random() >= a.miss]
sched.sort()
f.start(); t0 = time.perf_counter() + 0.3
for t_rel, st, m in sched:
    while time.perf_counter() - t0 < t_rel: time.sleep(0.0005)
    f.observe(time.perf_counter(), m)
time.sleep(min(1.0, 2 * a.spe)); f.stop()

total_e = int(notes[-1][0]) + 1
rows = []                                    # (e, lag_sec) по объявленным долям
for tt, m in logs:
    if m.startswith("доля"):
        e = int(m.split()[1]); rows.append((e, (tt - t0) - e * a.spe))
bass = [((tt - t0), m, v) for tt, ch, m, v in cap.on if ch == 0 and v >= 90]
brows = []                                   # бас на сильной доле: ближайшая по партитуре сильная восьмая (кратная BAR)
bar = getattr(score, "BAR", 3)
for tt, m, v in bass:
    e = round(tt / a.spe / bar) * bar; brows.append((e, tt - e * a.spe))
def rep(name, rs, unit):
    if not rs: print(f"{name}: нет событий"); return
    lag = [r[1] for r in rs]; q = 2 * a.spe
    med = S.median(lag); p10, p90 = sorted(lag)[int(0.1 * (len(lag) - 1))], sorted(lag)[int(0.9 * (len(lag) - 1))]
    print(f"{name}: n={len(rs)}, медиана {med*1000:+.0f} мс ({med/q:+.2f} четв.), 10–90 % {p10*1000:+.0f}…{p90*1000:+.0f} мс, "
          f"мин {min(lag)*1000:+.0f}, макс {max(lag)*1000:+.0f}; |откл.| ≤150 мс у {100*sum(1 for x in lag if abs(x) <= 0.15)/len(lag):.0f} %")
print(f"темп {60/a.spe:.0f} восьмых/мин ({60/a.spe/2:.0f} четвертей/мин), spe={a.spe:.3f}; нот подано {len(sched)} из {len(notes)}, "
      f"сопоставлено {f.matches}; темп следящего в конце {f.T*1000:.0f} мс/восьмую (истина {a.spe*1000:.0f})")
rep("доли (все)", rows, "с")
first = [r for r in rows if r[0] < score.LENGTH]; later = [r for r in rows if r[0] >= score.LENGTH]
rep("  первый проход", first, "с"); rep("  со второго прохода", later, "с")
rep("бас на сильной доле", brows, "с")
if rows: print(f"первая доля ансамбля: e={rows[0][0]} в {rows[0][1] + rows[0][0]*a.spe:.2f} с (солист начал в 0, первая нота партитуры в {sorted(score.MELODY)[0][0]*a.spe:.2f} с)")
if not a.quiet: print("по долям (e, мс):", [(e, int(l * 1000)) for e, l in rows[::3]])
