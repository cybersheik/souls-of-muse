"""Прогон записанных нот (json [[t, midi],...]) через следящий механизм в ускоренном «сухом» режиме."""
import sys, json; sys.path.insert(0, "ensemble")
import importlib; score = importlib.import_module(sys.argv[2] if len(sys.argv) > 2 else "fur_elise"); from follower import Follower
notes = json.load(open(sys.argv[1]))
logs = []; f = Follower(score, None, sec_per_eighth=float(sys.argv[3]) if len(sys.argv) > 3 else 0.6, log=logs.append)
errs = []; matched = []
for t, m in notes:
    p = f.predicted(t); i = f.observe(t, m)
    if i is not None and p is not None: errs.append(abs(p - f.pos))
    matched.append(i is not None)
print(f"нот {len(notes)}, сопоставлено {sum(matched)}; ошибка предсказания позиции: медиана {sorted(errs)[len(errs)//2]:.2f} восьмых, 90% {sorted(errs)[int(len(errs)*0.9)]:.2f}" if errs else "ничего не сопоставлено")
print("темп в конце:", f"{f.T*1000:.0f} мс/восьмую = {60/(f.T*2):.0f} bpm четвертями")
print("\n".join(logs[:2]))
print("последняя позиция в партитуре:", f.pos, "восьмых; кругов:", (f.pos or 0) // score.LENGTH)
