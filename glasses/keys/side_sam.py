"""Боковой вид через SAM 3.1 (ответ на «ты опять без SAM пытаешься увидеть?», 04.11 01:10).
Телефон с торца картонки, объектив у стола, смотрит вдоль клавиш. SAM сегментирует «палец» каждый кадр и «картонку»
раз в N кадров (камера неподвижна). Касание = нижняя точка маски пальца лежит на полосе картонки (не выше её верхнего
края в этом столбце больше чем на tol). Приподнятый палец при взгляде вдоль клавиш проецируется выше полосы:
подъём 3 см на 40 см даёт ~55 px при 960 px высоты, а вся глубина картонки в полосе ~20 px.
Имён пальцев нет: наружу отдаём ранг пальца от ближнего торца (по y нижней точки), стенд склеивает с видом очков
по тому же рангу среди кончиков над клавишами. SAM 3.1 MLX ≈ 0,1 с на промпт при 336 px → 3–5 кадров/с.

SideSam(cam=1 | file=..., end="treble").step() ->
  {"hands": 1|0, "n": пальцев, "fingers": [(x, y_low, pressed)], "pressed_ranks": [ранг от ближнего торца], "vis", "t"}
"""
from __future__ import annotations
import time, threading
import cv2
import numpy as np


class SideSam:
    def __init__(self, cam: int | None = None, file: str | None = None, end: str = "treble", rotate: int = 0,
                 res: int = 336, tol: float = 0.008, board_every: int = 10, max_side: int = 960, hold: int = 1,
                 finger_prompt: str = "finger", board_prompt: str = "cardboard piano keyboard"):
        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).parent))
        from air_keys import LocalSam
        self.sam = LocalSam()
        self.cap = cv2.VideoCapture(file if file else int(cam if cam is not None else 1))
        if not self.cap.isOpened(): raise RuntimeError(f"боковая камера не открылась: cam={cam} file={file}")
        self.is_file = bool(file); self.end = end; self.rotate = rotate; self.res = res; self.tol = tol
        self.board_every = board_every; self.max_side = max_side; self.hold = hold
        self.fp, self.bp = finger_prompt, board_prompt
        self.board = None; self.top = None; self.n = 0; self.latest = None; self._stop = False; self._thr = None
        self._run = {}; self.t_hands = 0.0
        from mask_track import MaskTracker
        self.trk = MaskTracker(match_iou=0.25, max_missed=2, dedupe_iou=0.4, k=6)   # ведение пальцев по перекрытию масок

    def read(self):
        if not self.is_file:
            for _ in range(2): self.cap.grab()
        ok, fr = self.cap.read()
        if not ok or fr is None: return None
        if self.rotate == 90: fr = cv2.rotate(fr, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotate == -90: fr = cv2.rotate(fr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif self.rotate == 180: fr = cv2.rotate(fr, cv2.ROTATE_180)
        h, w = fr.shape[:2]; s = self.max_side / max(h, w)
        if s < 1: fr = cv2.resize(fr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        return fr

    def _board_top(self, fr):
        ms = self.sam.masks(fr, self.bp, self.res, 0.3)
        if not ms: return
        # картонка белая: среди крупных масок (> 2 % кадра) берём самую светлую, иначе промпт цепляет чёрную подложку
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY); big = [t for t in ms if int(t[1].sum()) > 0.02 * g.size] or ms
        m = max(big, key=lambda t: float(g[t[1] > 0].mean()) if (t[1] > 0).any() else 0)[1]
        H, W = m.shape; top = np.full(W, -1, np.int32)
        ys, xs = np.nonzero(m)
        if len(xs) < 50: return
        for x in np.unique(xs):
            top[x] = ys[xs == x].min()
        # заполнить пропуски по соседям
        good = top >= 0
        if good.sum() < 20: return
        # верх картонки — прямая. Верх маски по столбцам не прямая: у дальнего торца крутой боковой край, а рука в маске
        # задирает верх. RANSAC по парам столбцов: лучшая прямая по числу столбцов в полосе ±6 px.
        xi = np.arange(W); x_ = xi[good].astype(np.float64); y_ = top[good].astype(np.float64)
        rng = np.random.default_rng(0); best = (0, 0.0, float(np.median(y_)))
        for _ in range(300):
            i, j = rng.choice(len(x_), 2, replace=False)
            if abs(x_[i] - x_[j]) < 40: continue
            a = (y_[j] - y_[i]) / (x_[j] - x_[i]); b = y_[i] - a * x_[i]
            n_in = int((np.abs(y_ - (a * x_ + b)) < 6).sum())
            if n_in > best[0]: best = (n_in, a, b)
        a, b = best[1], best[2]; inl = np.abs(y_ - (a * x_ + b)) < 6
        if inl.sum() >= 20: a, b = np.polyfit(x_[inl], y_[inl], 1)
        top = np.clip(a * xi + b, 0, H - 1).astype(np.int32)
        self.board = m; self.top = top; self.board_x = (int(xs.min()), int(xs.max()))

    def step(self):
        fr = self.read()
        if fr is None: return None
        self.n += 1; H, W = fr.shape[:2]
        # край картонки: первый кадр, затем раз в board_every кадров, пока в кадре нет пальцев (рука задирает край маски)
        if self.board is None or (self.n % self.board_every == 1 and not self.trk.tracks): self._board_top(fr)
        vis = fr.copy()
        if self.top is not None:
            pts = np.stack([np.arange(W), self.top], 1).reshape(-1, 1, 2).astype(np.int32)
            cv2.polylines(vis, [pts], False, (0, 200, 255), 2)
        fingers = []
        # захват по слову каждый кадр (0,1 с), дубли отсеиваются, дорожки сопоставляются с прошлым кадром по IoU
        tracks = self.trk.update(self.sam.masks(fr, self.fp, self.res, 0.5))
        for t_ in tracks:
            score, m, tid = t_["score"], t_["mask"], t_["id"]
            ys, xs = np.nonzero(m)
            i = ys.argmax(); x_low, y_low = int(xs[i]), int(ys[i])
            if self.top is None or not (self.board_x[0] - 20 <= x_low <= self.board_x[1] + 20): continue
            pressed = y_low >= self.top[x_low] - self.tol * H
            fingers.append((x_low, y_low, bool(pressed), float(score), tid))
            col = (0, 220, 0) if pressed else (255, 160, 0)
            cv2.drawContours(vis, cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0], -1, col, 2)
            cv2.circle(vis, (x_low, y_low), 7, col, -1); cv2.putText(vis, str(tid), (x_low + 8, y_low + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
        # ранг от ближнего торца: ближе = ниже в кадре (больше y)
        order = sorted(range(len(fingers)), key=lambda i: -fingers[i][1])
        rank = {i: r for r, i in enumerate(order)}
        cur = {f[4] for f in fingers if f[2]}; self._run = {i_: self._run.get(i_, 0) + 1 for i_ in cur}
        pressed_ranks = [rank[i] for i, f in enumerate(fingers) if f[2] and self._run[f[4]] >= self.hold]
        pressed_ids = [f[4] for f in fingers if f[2] and self._run[f[4]] >= self.hold]
        if fingers: self.t_hands = time.time()
        cv2.putText(vis, f"sam side: fingers={len(fingers)} pressed ranks={pressed_ranks}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        res = {"hands": 1 if fingers else 0, "n": len(fingers), "fingers": fingers, "pressed_ranks": pressed_ranks, "pressed_ids": pressed_ids, "vis": vis, "t": time.time()}
        self.latest = res
        return res

    def start(self):
        def loop():
            while not self._stop:
                try:
                    if self.step() is None: time.sleep(0.05)
                except Exception as e:
                    print(f"боковой SAM: ошибка {e}", flush=True); time.sleep(0.2)
        self._thr = threading.Thread(target=loop, daemon=True); self._thr.start(); return self

    def current(self):
        r = self.latest
        return r if r and time.time() - r["t"] < 1.5 else None


if __name__ == "__main__":
    import argparse, os
    ap = argparse.ArgumentParser()
    ap.add_argument("--file"); ap.add_argument("--cam", type=int); ap.add_argument("--end", default="treble")
    ap.add_argument("--rotate", type=int, default=0); ap.add_argument("--step", type=int, default=8); ap.add_argument("--max-frames", type=int, default=40)
    ap.add_argument("--save"); ap.add_argument("--tol", type=float, default=0.008); ap.add_argument("--finger-prompt", default="finger"); ap.add_argument("--board-prompt", default="cardboard piano keyboard")
    a = ap.parse_args()
    sv = SideSam(cam=a.cam, file=a.file, end=a.end, rotate=a.rotate, tol=a.tol, finger_prompt=a.finger_prompt, board_prompt=a.board_prompt)
    i = 0; t0 = time.time()
    while i < a.max_frames:
        if a.file:
            for _ in range(a.step - 1): sv.cap.grab()
        r = sv.step()
        if r is None: break
        i += 1
        print(f"{i:03d} пальцев={r['n']} нажаты(ранг)={r['pressed_ranks']} id={r['pressed_ids']} дорожки={[f[4] for f in r['fingers']]}")
        if a.save: os.makedirs(a.save, exist_ok=True); cv2.imwrite(f"{a.save}/m{i:03d}.jpg", r["vis"])
    print(f"{(time.time() - t0) / max(1, i):.2f} с/кадр")
