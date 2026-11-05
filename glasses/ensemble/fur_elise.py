"""«К Элизе» (Бетховен, WoO 59), часть A — опорная партитура для следящего ансамбля.
Размер 3/8, счёт в восьмых; темп ~ 120–150 восьмых/мин (Poco moto). Мелодия правой руки записана
в шестнадцатых = 0.5 восьмой. Сетка аккордов — по тактам, в восьмых от начала пьесы (такт 0 = затакт из двух шестнадцатых).
Используется только для СЛЕЖЕНИЯ (где солист, какой темп) и для партий аккомпанемента; мелодию ансамбль не играет.
"""
from __future__ import annotations

E5, Ds5, B4, D5, C5, A4, C4, E4, Gs4, B3, E3, A3, Gs3, Ds4 = 76, 75, 71, 74, 72, 69, 60, 64, 68, 59, 52, 57, 56, 63

# (время в восьмых от начала, midi, длительность в восьмых)
# Затакт: E5 D#5 | такт1: E5 D#5 E5 B4 D5 C5 | такт2: A4 . (левая рука A2 E3 A3) C4 E4 A4 | такт3: B4 . (E2 E3 G#3) E4 G#4 B4 |
# такт4: C5 . (A2 E3 A3) E4 E5 D#5 | такт5: E5 D#5 E5 B4 D5 C5 | такт6: A4 . C4 E4 A4 | такт7: B4 . E4 C5 B4 | такт8: A4 . .
_S = 0.5
MELODY: list[tuple[float, int, float]] = []
def _bar(bar: int, notes: list[int | None]):
    t = bar * 3.0
    for i, m in enumerate(notes):
        if m is not None: MELODY.append((t + i * _S, m, _S))
_bar(0, [None, None, None, None, E5, Ds5])                 # затакт на последних двух шестнадцатых «нулевого» такта
_bar(1, [E5, Ds5, E5, B4, D5, C5])
_bar(2, [A4, None, C4, E4, A4, None])
_bar(3, [B4, None, E4, Gs4, B4, None])
_bar(4, [C5, None, E4, E5, Ds5, None])
_bar(5, [E5, Ds5, E5, B4, D5, C5])
_bar(6, [A4, None, C4, E4, A4, None])
_bar(7, [B4, None, E4, C5, B4, None])
_bar(8, [A4, None, None, None, E5, Ds5])                    # … и по кругу (повтор A)

# Сетка аккордов: (начало в восьмых, длительность, корень midi-класс, тип)
CHORDS: list[tuple[float, float, int, str]] = [
    (0, 3, 4, "E7"),      # затакт — доминанта
    (3, 3, 9, "Am"), (6, 3, 9, "Am"), (9, 3, 4, "E7"), (12, 3, 9, "Am"),
    (15, 3, 9, "Am"), (18, 3, 9, "Am"), (21, 3, 4, "E7"), (24, 3, 9, "Am"),
]
LENGTH = 27.0                     # восьмых в одном проходе части A (повторяется)
KEY = "A minor"

CHORD_TONES = {"Am": [0, 3, 7], "E7": [0, 4, 7, 10], "C": [0, 4, 7], "G": [0, 4, 7], "F": [0, 4, 7], "Dm": [0, 3, 7]}

def chord_at(t_eighths: float):
    t = t_eighths % LENGTH
    for s, d, root, kind in CHORDS:
        if s <= t < s + d: return root, kind
    return CHORDS[-1][2], CHORDS[-1][3]
