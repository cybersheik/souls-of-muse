"""Слышимая проба: синтетический солист играет мелодию «К Элизе» (GM фортепиано) с разгоном темпа и пропусками,
следящий ансамбль (бас + струнные) идёт за ним. Запуск: .venv-mlx/bin/python ensemble/demo_synthetic.py [проходов]"""
import sys, time, random; sys.path.insert(0, "ensemble"); sys.path.insert(0, "keys")
import fur_elise as score; from follower import Follower; from player import EnsemblePlayer; from gm_synth import GMSynth
random.seed(3)
passes = int(sys.argv[1]) if len(sys.argv) > 1 else 2
solo = GMSynth(0, volume=0.9); ens = EnsemblePlayer()
print('голоса ансамбля:', ens.programs)
f = Follower(score, ens, sec_per_eighth=0.6, log=lambda m: None); f.start()
notes = [(st + k * score.LENGTH, m, d) for k in range(passes) for (st, m, d) in sorted(score.MELODY)]
T0, T1 = 0.70, 0.56; total = notes[-1][0]; tt = 0.0; prev = 0.0; sched = []
for st, m, d in notes:
    T = T0 + (T1 - T0) * (st / total); tt += (st - prev) * T; prev = st; sched.append((tt, m, d * T, st))
start = time.perf_counter() + 0.5; seen = 0
for t_rel, m, dur, st in sched:
    while time.perf_counter() - start < t_rel: time.sleep(0.001)
    solo.note_on(m, 100)                                             # солист звучит всегда
    if random.random() > 0.3: f.observe(time.perf_counter(), m); seen += 1   # ансамбль «видит» 70 % нот
    time.sleep(min(dur * 0.9, 0.3)); solo.note_off(m)
time.sleep(1.0); f.stop()
print(f"солист сыграл {len(sched)} нот, ансамбль видел {seen}, сопоставил {f.matches}; темп в конце {60/(f.T*2):.0f} bpm")
