"""Следящий ансамбль: по потоку нажатий солиста (момент, midi) оценивает позицию в партитуре и темп,
и играет партии аккомпанемента (бас, подклад) на предсказанные доли. Пропуски нот допустимы —
сопоставляются только увиденные ноты.

  from follower import Follower
  f = Follower(score=fur_elise, out=player)   # player.note_on(ch, midi, vel) / note_off(ch, midi)
  f.observe(t_sec, midi)                       # из air_keys при каждом ON
  f.start(); ... f.stop()
"""
from __future__ import annotations
import math, threading, time

class Follower:
    def __init__(self, score, out=None, sec_per_eighth: float = 0.6, log=print, min_matches: int = 4, window: int = 10,
                 meter: bool = True, low_note: int = 55, input_latency: float = 0.0, lead: float | None = None):
        self.score = score
        self.meter = meter                            # False = режим без метра: аккорд и бас идут по нотам солиста, а не по долям
        self.low_note = low_note                      # ноты солиста ниже этой бас дублирует в его же момент
        self.melody = sorted(score.MELODY)            # (t, midi, dur)
        self.out = out; self.log = log
        self.T = sec_per_eighth                       # сек на восьмую (темп); стартовое значение — лишь догадка, см. warmup ниже
        self.n_tempo = 0                              # сколько раз темп уже оценён по наблюдениям (разгон: первые 6 оценок без тормоза 6 %)
        self.input_latency = input_latency            # задержка входа (зрение: кадр + подтверждение), сек: observe(t) получает t − latency
        # упреждение выдачи долей: задержка синтезатора (player.latency, ~12 мс у AVAudioEngine) + 30 мс на цикл планировщика
        self.lead = lead if lead is not None else 0.03 + float(getattr(out, "latency", 0.0) or 0.0)
        self.pos = None                               # позиция партитуры (восьмые, без свёртки по кругу)
        self.t_pos = None                             # реальное время, в которое pos была верна
        self.idx = None                               # индекс последней сопоставленной ноты (с учётом кругов: idx = k*len + j)
        self.matches = 0; self.min_matches = min_matches; self.window = window
        self.lock = threading.Lock(); self._run = False
        self._bass_last = None; self._pad = []; self._pad_chord = None; self._next_eighth = None; self.hist = []; self._pluck_last = None

    # ---------- слежение
    def _score_time(self, idx):
        n = len(self.melody); k, j = divmod(idx, n)
        return self.melody[j][0] + k * self.score.LENGTH
    def predicted(self, now: float):
        if self.pos is None: return None
        return self.pos + (now - self.t_pos) / self.T
    def observe(self, t: float, midi: int):
        n = len(self.melody); pc = midi % 12; t = t - self.input_latency
        with self.lock:
            if self.idx is None:
                # старт: первая нота с нужным классом высоты — предпочитаем начало фразы (E5/D#5 затакта)
                cands = [j for j in range(n) if self.melody[j][1] % 12 == pc]
                if not cands: return None
                j = min(cands, key=lambda j: (abs(self.melody[j][1] - midi), self.melody[j][0]))
                self.idx, self.pos, self.t_pos, self.matches = j, self.melody[j][0], t, 1; self.hist = [(self.melody[j][0], t)]
                self.log(f"старт слежения: нота {midi} → индекс {j}, t={self.melody[j][0]:.1f}"); return j
            pred = self.predicted(t)
            best = None
            d = -3
            while True:                                               # кандидаты: чуть назад и вперёд по партитуре — не меньше window нот
                d += 1; i = self.idx + d                              # и все ноты до горизонта pred + 3 восьмых (пропуски зрения режут не по счёту нот, а по времени)
                if i < 0: continue
                st = self._score_time(i)
                if d > self.window and st - pred > 3.0: break
                m = self.melody[i % n][1]
                if m % 12 != pc: continue
                err = abs(st - pred)                                  # ошибка во времени партитуры (восьмых)
                cost = err + (0.0 if m == midi else 0.7) + 0.05 * max(0, d)
                if best is None or cost < best[0]: best = (cost, i, st, err)
            if best is None or best[3] > 3.0:
                return None                                           # не похоже на партитуру — игнорируем (украшение, ошибка, чужая нота)
            cost, i, st, err = best
            slope = None                                              # наклон регрессии по hist (сек/восьмую), если есть
            # нота легла дальше ¾ восьмой от предсказания — это не дрожание, а перестановка (старт замкнулся на похожую
            # фразу E–D#–E на восьмую раньше, фермата, пропуск). Старую историю не смешиваем с новой: иначе регрессия
            # по двум разным выравниваниям даёт ложный темп и тянет позицию на полвосьмой целый проход
            realign = pred is not None and err > 0.75
            if realign: self.hist = []
            if i > self.idx:
                self.hist.append((st, t)); self.hist = self.hist[-12:]
                T_obs = None
                if len(self.hist) >= 3:                               # темп = наклон МНК по последним сопоставлениям (устойчив к дрожанию)
                    xs = [a for a, _ in self.hist]; ys = [b for _, b in self.hist]
                    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
                    vxx = sum((x - mx) ** 2 for x in xs); vxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                    if vxx >= 0.4: T_obs = slope = vxy / vxx            # три шестнадцатых подряд (разброс 0,5) уже дают наклон
                elif len(self.hist) == 2 and self.n_tempo < 6:        # разгон: уже интервал между двумя соседними нотами даёт темп (и после сброса hist)
                    (s0, t0), (s1, t1) = self.hist
                    if 0.5 <= s1 - s0 <= 2.0: T_obs = (t1 - t0) / (s1 - s0)
                if T_obs is not None:
                    warm = self.n_tempo < 6                           # стартовый темп — догадка (air_keys даёт 0,6 с); медленный ученик может играть вдвое медленнее
                    lo, hi = (0.35, 3.0) if warm else (0.5, 2.0)
                    if lo * self.T <= T_obs <= hi * self.T:
                        if warm:
                            T_new = 0.2 * self.T + 0.8 * T_obs; step = 2.0 if len(self.hist) >= 3 else 1.5   # разгон: верим наблюдению (по одному интервалу — осторожнее)
                        else:
                            T_new = 0.6 * self.T + 0.4 * T_obs; step = 1.06            # потом: не дёргать темп больше чем на 6 % за ноту
                        self.T = min(self.T * step, max(self.T / step, T_new)); self.n_tempo += 1
            else:
                self.hist = []
            # позиция: из той же регрессии (время партитуры → реальное время) по последним сопоставлениям,
            # чтобы дрожание отдельных нот (рубато, украшения, квантование сетки) не дёргало ансамбль
            if len(self.hist) >= 4 and pred is not None and abs(st - pred) < 1.5:
                xs = [a for a, _ in self.hist]; ys = [b for _, b in self.hist]
                mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
                # реальное время, соответствующее st по линии: my + slope*(st - mx) → позиция в момент t.
                # Наклон берём из самой регрессии (а не сглаженный T): иначе при ещё не сошедшемся T линия
                # отклоняется от точек и позиция убегает на восьмые вперёд. Сдвиг от только что увиденной ноты ≤ 0,5 восьмой.
                t_line = my + (slope if slope is not None else self.T) * (st - mx)
                self.pos = st + max(-0.5, min(0.5, (t - t_line) / self.T))
            elif pred is not None and not realign:
                self.pos = pred + 0.5 * (st - pred)
            else:
                self.pos = st
            self.idx, self.t_pos = i, t
            self.matches += 1
            if not self.meter and self.matches >= self.min_matches: self._on_note_free(t, midi, st)
            return i

    # ---------- аккомпанемент
    def _emit_pad(self, root, kind, now):
        if self.out is None: return
        for m in self._pad: self.out.note_off(1, m)
        r = 48 + (root % 12)
        self._pad = [r, r + 7, r + 12]                                 # квинта и октава: под перегруз чисто, без грязи от терции
        for m in self._pad: self.out.note_on(1, m, 50)
    def _emit_bass(self, root, now, strong: bool):
        if self.out is None: return
        if self._bass_last is not None: self.out.note_off(0, self._bass_last)
        self._bass_last = 36 + (root % 12)                           # бас C2–B2
        self.out.note_on(0, self._bass_last, 95 if strong else 70)
    # ---------- режим без метра (R-04): смена аккорда и бас привязаны к нотам солиста, долей ансамбль не считает
    def _on_note_free(self, t, midi, st):
        root, kind = self.score.chord_at(st)
        changed = (root, kind) != self._pad_chord
        if changed:
            self._emit_pad(root, kind, t); self._pad_chord = (root, kind)
            if self.out is not None:                                         # щипок тоники на смене аккорда — мягкая отметка
                if self._pluck_last is not None: self.out.note_off(2, self._pluck_last)
                self._pluck_last = 60 + (root % 12); self.out.note_on(2, self._pluck_last, 64)
        if midi < self.low_note:
            self._emit_bass(midi, t, strong=True)                           # солист ушёл вниз — бас с ним, в его момент
        elif changed:
            self._emit_bass(root, t, strong=True)                           # иначе бас только на смене аккорда
        if changed: self.log(f"аккорд {kind if kind[:1].isalpha() else root} по ноте {midi} (позиция {st:.1f})")

    def _loop(self):
        while self._run:
            now = time.perf_counter()
            with self.lock:
                # тишина, если солист молчит дольше двух тактов (6 восьмых), но не меньше 4 с — на медленном темпе паузы длиннее
                # вступаем после min_matches сопоставлений, из них ≥3 подряд вперёд (есть наклон для темпа), иначе часы долей стартуют на угаданном темпе
                p = self.predicted(now); ok = self.matches >= self.min_matches and len(self.hist) >= 3 and self.t_pos is not None and now - self.t_pos < max(4.0, 6.0 * self.T)
            if (not ok or p is None) or not self.meter:
                if not self.meter and ok and p is not None:
                    time.sleep(0.01); continue                                  # без метра: всё делает observe(), тут только тишина при паузе
                if self._pad or self._bass_last is not None:
                    if self.out:
                        for m in self._pad: self.out.note_off(1, m)
                        if self._bass_last is not None: self.out.note_off(0, self._bass_last)
                    self._pad, self._bass_last, self._pad_chord, self._next_eighth = [], None, None, None; self._pluck_last = None
                time.sleep(0.01); continue
            # часы долей расходятся с предсказанием больше чем на полвосьмой (сбой темпа на старте, скачок позиции) —
            # перезамыкаем жёстко: мягкая подтяжка по 25 % доли за долю догоняла бы 4 восьмых целый проход
            if self._next_eighth is not None and abs(p - (self._next_eighth - (self._t_next - now) / self.T)) > 0.5:
                self.log(f"часы долей перезамкнуты: были на {self._next_eighth - (self._t_next - now) / self.T:.2f}, солист на {p:.2f}")
                self._next_eighth = None
            if self._next_eighth is None:
                self._next_eighth = math.ceil(p); self._t_next = now + (self._next_eighth - p) * self.T
            # часы долей: следующая доля через T после предыдущей, фаза подтягивается к предсказанию не быстрее 25 % доли за долю;
            # выдаём с упреждением lead (цикл планировщика + задержка синтезатора), чтобы звук лёг на долю, а не после неё
            while now + self.lead >= self._t_next:
                e = self._next_eighth; root, kind = self.score.chord_at(e)
                err = (p - e) * self.T                                    # насколько предсказание опережает наши часы (сек)
                self._next_eighth += 1
                self._t_next = self._t_next + self.T - max(-0.25 * self.T, min(0.25 * self.T, err))
                if (root, kind) != self._pad_chord: self._emit_pad(root, kind, now); self._pad_chord = (root, kind)
                bar = getattr(self.score, "BAR", 3); ph = int(e) % bar
                if ph == 0: self._emit_bass(root, now, strong=True)
                elif ph == (2 if bar == 3 else bar // 2): self._emit_bass(root + 7, now, strong=False)   # квинта на середине такта
                if ph != 0 and self.out is not None:                                   # щипок на слабых долях: тоны аккорда по очереди
                    tones = self.score.CHORD_TONES.get(kind, [0, 4, 7]); iv = tones[(int(e) // bar + ph) % len(tones)]
                    m = 60 + ((root + iv) % 12) + (12 if int(e) % 2 else 0)
                    if self._pluck_last is not None: self.out.note_off(2, self._pluck_last)
                    self.out.note_on(2, m, 72); self._pluck_last = m
                self.log(f"доля {e:.0f} ({kind}) темп {60/self.T:.0f} единиц/мин")
            time.sleep(0.005)
    def start(self):
        self._run = True; threading.Thread(target=self._loop, daemon=True).start()
    def stop(self):
        self._run = False; time.sleep(0.03)
        if self.out:
            for m in self._pad: self.out.note_off(1, m)
            if self._bass_last is not None: self.out.note_off(0, self._bass_last)
            if self._pluck_last is not None: self.out.note_off(2, self._pluck_last)
