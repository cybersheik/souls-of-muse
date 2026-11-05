"""Боковой вид (второй взгляд) для стенда клавиш: телефон с торца картонки, объектив на 3–5 см над столом,
смотрит вдоль клавиш. Отсюда видна высота пальцев: нажимающий касается картонки, остальные приподняты.
Сверху (очки) этого не видно: «лежит» и «нажата» выглядят одинаково (JUDGE 03.11: 75 % ложных среди лежащих).

Правило «палец опущен» (03.11, по клипу IMG_1692): внутри кисти самый нижний в кадре кончик, если он ниже второго
не меньше чем на gap (доля высоты кадра; перспектива вдоль клавиш даёт ~17 px на 10 см глубины при 960 px, нажатие
2–3 см даёт ~50 px). Роль кисти по близости к камере: с дискантового торца (end=treble) ближняя кисть = правая.
Хиральность Vision в этом ракурсе ненадёжна — не используем.

SideView(cam=1 | file=path, end="treble", rotate=0, gap=0.02).step() ->
  {"hands": n, "down": [(role, finger, gap_px)], "tips": {role: {finger: (x, y)}}, "vis": кадр с разметкой} | None
"""
from __future__ import annotations
import time, threading
import cv2
import numpy as np

FINGERS = ["thumb", "index", "middle", "ring", "little"]
RU = {"thumb": "большой", "index": "указательный", "middle": "средний", "ring": "безымянный", "little": "мизинец"}


class SideView:
    def __init__(self, cam: int | None = None, file: str | None = None, end: str = "treble", rotate: int = 0,
                 gap: float = 0.02, min_conf: float = 0.3, max_side: int = 960, hold: int = 2):
        from hand_pose import VisionHands
        self.cap = cv2.VideoCapture(file if file else int(cam if cam is not None else 1))
        if not self.cap.isOpened(): raise RuntimeError(f"боковая камера не открылась: cam={cam} file={file}")
        self.is_file = bool(file); self.end = end; self.rotate = rotate; self.gap = gap; self.max_side = max_side
        self.hands = VisionHands(max_hands=2, min_conf=min_conf)
        self.last = None; self.t_hands = 0.0; self.n = 0
        self.hold = hold; self._run = {}; self.latest = None; self._thr = None; self._stop = False

    def read(self):
        if not self.is_file:
            for _ in range(2): self.cap.grab()          # сбросить буфер, взять свежий кадр
        ok, fr = self.cap.read()
        if not ok or fr is None: return None
        if self.rotate == 90: fr = cv2.rotate(fr, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotate == -90: fr = cv2.rotate(fr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif self.rotate == 180: fr = cv2.rotate(fr, cv2.ROTATE_180)
        h, w = fr.shape[:2]; s = self.max_side / max(h, w)
        if s < 1: fr = cv2.resize(fr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        return fr

    def step(self):
        fr = self.read()
        if fr is None: return None
        self.n += 1; H = fr.shape[0]
        det = self.hands.detect(fr)
        hands = []
        for hd in det:
            tips = {k: (x, y) for k, (x, y, c) in hd["tips"].items()}
            if not tips: continue
            wr = hd["points"].get("VNHLKWRI")
            near = wr[1] if wr is not None else float(np.mean([y for _, y in tips.values()]))   # больше y = ближе к камере
            hands.append({"tips": tips, "near": near})
        hands.sort(key=lambda h: -h["near"])                    # первая = ближняя
        roles = ["right", "left"] if self.end == "treble" else ["left", "right"]
        down, out_tips = [], {}
        vis = fr.copy()
        for i, hd in enumerate(hands[:2]):
            role = roles[i] if len(hands) > 1 else roles[0]
            out_tips[role] = hd["tips"]
            ys = sorted(((y, k) for k, (x, y) in hd["tips"].items()), reverse=True)
            for k, (x, y) in hd["tips"].items():
                cv2.circle(vis, (int(x), int(y)), 5, (255, 200, 0), 2)
            if len(ys) >= 2:
                g = ys[0][0] - ys[1][0]
                need = self.gap * H * (2.0 if ys[0][1] == "thumb" else 1.0)
                if g >= need:
                    down.append((role, ys[0][1], float(g)))
                    x, y = hd["tips"][ys[0][1]]
                    cv2.circle(vis, (int(x), int(y)), 12, (0, 220, 0), 3)
                    cv2.putText(vis, f"{role} {ys[0][1]} v{g:.0f}", (int(x) + 10, int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 0), 2)
        cur = {(r_, f_) for r_, f_, _ in down}
        self._run = {k: (self._run.get(k, 0) + 1) for k in cur}
        down = [d for d in down if self._run[(d[0], d[1])] >= self.hold]
        if hands: self.t_hands = time.time()
        cv2.putText(vis, f"side: hands={len(hands)} down={[d[1] for d in down]}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        res = {"hands": len(hands), "down": down, "tips": out_tips, "vis": vis, "t": time.time()}
        self.latest = res
        return res

    def start(self):
        """живая камера: крутить step() в своём потоке (10–20 к/с), стенд читает self.latest; так удержание hold кадров
        стоит 0,1–0,2 с, а не два шага медленного цикла SAM"""
        def loop():
            while not self._stop:
                try:
                    if self.step() is None: time.sleep(0.05)
                except Exception as e:
                    print(f"боковой вид: ошибка {e}", flush=True); time.sleep(0.2)
        self._thr = threading.Thread(target=loop, daemon=True); self._thr.start(); return self

    def current(self):
        """последний результат живого потока; None, если кадра не было дольше 1 с"""
        r = self.latest
        return r if r and time.time() - r["t"] < 1.0 else None


if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser(description="проба бокового вида на файле/камере: печатает опущенный палец по кадрам")
    ap.add_argument("--file"); ap.add_argument("--cam", type=int); ap.add_argument("--end", default="treble", choices=["treble", "bass"])
    ap.add_argument("--rotate", type=int, default=0); ap.add_argument("--gap", type=float, default=0.02)
    ap.add_argument("--step", type=int, default=8, help="файл: брать каждый N-й кадр"); ap.add_argument("--max-frames", type=int, default=60)
    ap.add_argument("--save", help="папка для кадров с разметкой")
    a = ap.parse_args()
    sv = SideView(cam=a.cam, file=a.file, end=a.end, rotate=a.rotate, gap=a.gap)
    i = 0
    while i < a.max_frames:
        if a.file:
            for _ in range(a.step - 1): sv.cap.grab()
        r = sv.step()
        if r is None: break
        i += 1
        print(f"{i:03d} руки={r['hands']} опущен={[(d[0], d[1], round(d[2])) for d in r['down']]}")
        if a.save:
            import os; os.makedirs(a.save, exist_ok=True); cv2.imwrite(f"{a.save}/s{i:03d}.jpg", r["vis"])
