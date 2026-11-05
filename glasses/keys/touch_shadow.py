# -*- coding: utf-8 -*-
"""Касание по тени (картонная клавиатура, низкий боковой свет).
Сверху не видно, касается палец картона или висит: силуэт один и тот же. Зато при лампе низко сбоку у висящего пальца
между его краем и его тенью есть светлая щель (ширина ≈ высота над картоном / tg высоты лампы), а у касающегося
тень примыкает к кончику без щели. Здесь: лучи от края кончика в три стороны (влево, вправо, вперёд по оси пальца),
по каждому — профиль яркости относительно уровня белой бумаги рядом; кожу отличаем по насыщенности цвета;
первая тёмная полоса на белой клавише — тень; расстояние от края пальца до неё — щель.
Чёрные клавиши и всё вне полоски исключаются через чертёж (обратная гомография кадр → чертёж).

  from touch_shadow import ShadowTouch
  st = ShadowTouch(); st.set_layout(H_template_to_frame, blacks_rects)   # из cardboard.fit: info["H"], template()[1]
  r = st.classify(frame_bgr, tip=(x, y), dip=(x2, y2), w=finger_px)      # → {"state": touch|hover|unsure|none, "gap": px, "side": L|R|F}
"""
from __future__ import annotations
import math
import numpy as np
import cv2

STRIP_W, STRIP_L = 24.0, 5.0        # чертёж: 24 белых × ширина 1, длина 5 (см. cardboard.py)

class ShadowTouch:
    def __init__(self, dark: float = 0.62, sat_skin: float = 0.22, reach: float = 2.5, touch_gap: float = 0.12, hover_gap: float = 0.28):
        self.dark, self.sat_skin, self.reach = dark, sat_skin, reach
        self.touch_gap, self.hover_gap = touch_gap, hover_gap
        self.Hinv = None; self.blacks = []; self.blacks_poly = []      # blacks_poly: полигоны чёрных в кадре, когда чертежа нет
    def set_layout(self, H, blacks_rects=None):
        self.Hinv = np.linalg.inv(np.asarray(H, dtype=np.float64)) if H is not None else None
        self.blacks = [tuple(r) for r in (blacks_rects or [])]
    # ---- что ожидается в точке кадра: 1 белая бумага, 0 чёрная клавиша, None вне полоски / чертёж неизвестен
    def expected(self, x, y):
        if self.Hinv is None:
            for pp in self.blacks_poly:
                if cv2.pointPolygonTest(pp, (float(x), float(y)), True) >= -2: return 0
            return 1
        v = self.Hinv @ np.array([x, y, 1.0]); 
        if abs(v[2]) < 1e-9: return None
        xt, yt = v[0] / v[2], v[1] / v[2]
        if not (0 <= xt <= STRIP_W and 0 <= yt <= STRIP_L): return None
        for x0, y0, x1, y1 in self.blacks:
            if x0 - 0.06 <= xt <= x1 + 0.06 and y0 <= yt <= y1 + 0.06: return 0
        return 1
    def _white_level(self, gray, sat, cx, cy, w):
        r = int(max(8, 2.2 * w)); H, W = gray.shape
        x0, x1, y0, y1 = max(0, int(cx - r)), min(W, int(cx + r)), max(0, int(cy - r)), min(H, int(cy + r))
        g = gray[y0:y1, x0:x1]; s = sat[y0:y1, x0:x1]
        if g.size == 0: return None
        cand = g[(s < self.sat_skin)]
        if cand.size < 20: return None
        return float(np.percentile(cand, 85))                       # яркая бумага рядом (тень и кожа в верхний хвост не попадают)
    def _ray(self, gray, sat, x0, y0, dx, dy, length, white):
        """Профиль вдоль луча: → (gap_px, dark_len_px, min_ratio) или None, если тени нет / луч неинформативен."""
        H, W = gray.shape; gap = None; dark_len = 0; mn = 9.0; seen_bright = 0; finger = 0
        for i in range(int(length)):
            x, y = x0 + dx * i, y0 + dy * i
            if not (0 <= x < W - 1 and 0 <= y < H - 1): break
            xi, yi = int(x), int(y)
            if sat[yi, xi] >= self.sat_skin:                          # ещё кожа — край пальца дальше, чем думали
                if gap is None and dark_len == 0: finger += 1; continue
                else: break
            e = self.expected(x, y)
            if e is None: break
            if e == 0: continue                                       # чёрная клавиша: не считаем ни щелью, ни тенью
            r = gray[yi, xi] / max(white, 1.0); mn = min(mn, r)
            if r < self.dark:
                if gap is None: gap = seen_bright
                dark_len += 1
            else:
                if gap is not None:
                    if dark_len >= 3: break                           # тень кончилась
                    gap = None; dark_len = 0                          # шум в 1–2 px — не тень
                seen_bright += 1
        if gap is None or dark_len < 3: return None
        return gap, dark_len, mn, finger
    def _prep(self, frame_bgr):
        """Насыщенность и сглаженная яркость считаются один раз на кадр (несколько кончиков на кадр)."""
        if getattr(self, "_fid", None) is not id(frame_bgr) or self._fshape != frame_bgr.shape:
            hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV); self._sat = hsv[..., 1].astype(np.float32) / 255.0
            self._gray = cv2.GaussianBlur(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32), (3, 3), 0)
            self._fid, self._fshape = id(frame_bgr), frame_bgr.shape
        return self._gray, self._sat
    def classify(self, frame_bgr, tip, dip, w: float):
        gray, sat = self._prep(frame_bgr)
        tx, ty = tip; dxv, dyv = tx - dip[0], ty - dip[1]; L = math.hypot(dxv, dyv) or 1.0
        d = (dxv / L, dyv / L); n = (-d[1], d[0])
        white = self._white_level(gray, sat, tx, ty, w)
        if white is None: return {"state": "none", "why": "нет белой бумаги рядом"}
        half = 0.5 * w
        # стартовые точки: по бокам кончика (чуть позади самого острия, где палец шире), и впереди острия
        starts = {"L": ((tx - 0.3 * w * d[0] - half * n[0], ty - 0.3 * w * d[1] - half * n[1]), (-n[0], -n[1])),
                  "R": ((tx - 0.3 * w * d[0] + half * n[0], ty - 0.3 * w * d[1] + half * n[1]), n),
                  "F": ((tx + 0.15 * w * d[0], ty + 0.15 * w * d[1]), d)}
        res = {}
        for side, ((sx, sy), (ux, uy)) in starts.items():
            r = self._ray(gray, sat, sx, sy, ux, uy, self.reach * w, white)
            if r: res[side] = r
        # луч вперёд (F) только для диагностики: при лампе за спиной тень пальца тянется вперёд сплошняком и щели
        # не бывает даже у висящего пальца; при лампе спереди тень уходит под кисть. Решает только боковая тень.
        lr = {k: v for k, v in res.items() if k in ("L", "R")}
        if not lr: return {"state": "none", "white": white, "front_shadow": "F" in res}
        res = lr
        side = max(res, key=lambda s: (res[s][1], -res[s][2]))     # где тень длиннее и темнее
        gap, dl, mn, finger = res[side]
        g = gap / max(w, 1.0)
        state = "touch" if g <= self.touch_gap else ("hover" if g >= self.hover_gap else "unsure")
        return {"state": state, "gap": gap, "gap_w": g, "side": side, "dark_len": dl, "min_ratio": mn, "white": white, "skin_px": finger}


# ------------------------------------------------------------------------------------------------ синтетическая проверка
def _synth(seed: int, gap_w: float, side: str, w: float = 22.0, persp: float = 0.15):
    """Картонка по чертежу под гомографией, палец, тень со щелью gap_w·w сбоку (side L/R) или впереди (F)."""
    rnd = np.random.RandomState(seed)
    import sys, os; sys.path.insert(0, os.path.dirname(__file__)); import cardboard
    whites, blacks = cardboard.template(4)
    W, H = 640, 360; ppu = 26.0                                            # px на единицу чертежа
    src = np.float32([[0, 0], [STRIP_W, 0], [STRIP_W, STRIP_L], [0, STRIP_L]])
    jit = lambda a: a + rnd.uniform(-persp, persp) * ppu * 3
    dst = np.float32([[jit(8), jit(60)], [jit(632), jit(60)], [jit(632), jit(190)], [jit(8), jit(190)]])
    Hm = cv2.getPerspectiveTransform(src, dst)
    img = np.full((H, W, 3), 60, np.uint8)                                 # стол
    paper = int(rnd.uniform(205, 245))
    cv2.fillPoly(img, [dst.astype(np.int32)], (paper, paper, paper))
    for i in range(1, int(STRIP_W)):                                       # линии между белыми (карандаш)
        p = cv2.perspectiveTransform(np.float32([[[i, 0]], [[i, STRIP_L]]]), Hm).reshape(-1, 2)
        cv2.line(img, tuple(p[0].astype(int)), tuple(p[1].astype(int)), (120, 120, 120), 1)
    for b in blacks:
        x0, y0, x1, y1 = b["rect"]; q = cv2.perspectiveTransform(np.float32([[[x0, y0]], [[x1, y0]], [[x1, y1]], [[x0, y1]]]), Hm).reshape(-1, 2)
        cv2.fillPoly(img, [q.astype(np.int32)], (25, 25, 25))
    # палец: кончик на случайной белой клавише в нижней половине
    k = whites[rnd.randint(0, len(whites))]; x0, y0, x1, y1 = k["rect"]
    tipt = np.float32([[[(x0 + x1) / 2 + rnd.uniform(-0.25, 0.25), rnd.uniform(3.3, 4.6)]]])
    tip = cv2.perspectiveTransform(tipt, Hm).reshape(2)
    ang = math.radians(-90 + rnd.uniform(-30, 30))                          # палец приходит снизу (от играющего), ±30°
    d = np.array([math.cos(ang), math.sin(ang)]); n = np.array([-d[1], d[0]])
    L = 4.0 * w
    def finger_poly(off):
        a = tip + off; b = tip - d * L + off
        pts = [a + n * 0.5 * w, b + n * 0.5 * w, b - n * 0.5 * w, a - n * 0.5 * w]
        poly = np.array(pts, np.int32)
        return poly, (a, w)
    # тень: та же форма, сдвинутая в сторону лампы противоположную; щель = gap_w·w
    sgn = {"L": -1, "R": 1, "F": 0}[side]
    if side == "F": off = d * (w * (1.0 + gap_w))                            # тень впереди: при касании начинается у острия
    else: off = n * sgn * (w * (1.0 + gap_w))
    shadow = img.copy(); poly_s, (a_s, _) = finger_poly(off)
    cv2.fillPoly(shadow, [poly_s], (0, 0, 0)); cv2.circle(shadow, tuple(a_s.astype(int)), int(0.5 * w), (0, 0, 0), -1)
    alpha = rnd.uniform(0.45, 0.65)
    img = cv2.addWeighted(img, 1 - alpha, shadow, alpha, 0)
    img = cv2.GaussianBlur(img, (0, 0), rnd.uniform(1.0, 2.5))
    poly_f, (a_f, _) = finger_poly(np.zeros(2))
    skin = (int(rnd.uniform(120, 170)), int(rnd.uniform(140, 185)), int(rnd.uniform(190, 235)))   # BGR
    cv2.fillPoly(img, [poly_f], skin); cv2.circle(img, tuple(a_f.astype(int)), int(0.5 * w), skin, -1)
    img = cv2.GaussianBlur(img, (0, 0), 0.8)
    img = np.clip(img.astype(np.float32) + rnd.normal(0, 4, img.shape), 0, 255).astype(np.uint8)
    vtip = tip - d * 0.2 * w + rnd.normal(0, 2, 2)                           # Vision ставит кончик чуть внутрь и с шумом
    dip = tip - d * 1.6 * w + rnd.normal(0, 2, 2)
    return img, Hm, [b["rect"] for b in blacks], tuple(vtip), tuple(dip), w

if __name__ == "__main__":
    import sys, os, collections
    out = os.path.join(os.path.dirname(__file__), "..", "out", "shadow_synth"); os.makedirs(out, exist_ok=True)
    st = ShadowTouch(); conf = collections.Counter(); rows = []
    cases = [("touch", 0.0), ("touch", 0.06), ("hover", 0.4), ("hover", 0.7), ("hover", 1.2)]
    seed = 0
    for truth, g in cases:
        for side in ("L", "R", "F"):
            for rep in range(12 if side != "F" else 6):
                seed += 1
                img, Hm, blacks, tip, dip, w = _synth(seed, g, side)
                st.set_layout(Hm, blacks)
                r = st.classify(img, tip, dip, 0.6 * 26.0)                  # ширина пальца из чертежа: 0,6 ширины белой
                conf[(truth, g, side, r["state"])] += 1
                if rep < 2:
                    vis = img.copy(); cv2.circle(vis, (int(tip[0]), int(tip[1])), 5, (0, 0, 255), 2)
                    cv2.putText(vis, f"{truth} gap={g} {side} -> {r['state']} {r.get('gap','')}", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
                    cv2.imwrite(os.path.join(out, f"{truth}_{g}_{side}_{rep}.jpg"), vis)
    print("истина | щель (доли ширины пальца) | сторона лампы → ответы")
    for truth, g in cases:
        for side in ("L", "R", "F"):
            ans = {s: conf[(truth, g, side, s)] for s in ("touch", "hover", "unsure", "none") if conf[(truth, g, side, s)]}
            print(f"{truth:5s} {g:4.2f} {side}: {ans}")
    tot = sum(conf.values()); ok = sum(v for (t, g, s, a), v in conf.items() if a == t)
    bad = sum(v for (t, g, s, a), v in conf.items() if a in ("touch", "hover") and a != t)
    print(f"всего {tot}: верно {ok} ({100*ok/tot:.0f} %), перепутано касание/висит {bad} ({100*bad/tot:.0f} %), остальное unsure/none; картинки в out/shadow_synth/")
