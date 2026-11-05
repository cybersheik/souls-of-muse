# -*- coding: utf-8 -*-
"""Привязка настоящего пианино по кадрам с замком по партитуре и якорем над клавишами.

Рисунок чёрных повторяется каждую октаву: по одним чёрным октава (а при закрытом руками ряде и сдвиг на клавишу)
не определяется, и слежение без абсолютной опоры за минуту уползает. Партитура известна, значит известна первая
ожидаемая нота. PianoTracker:
  • скан чёрных один раз, дальше метки наследуются по близости чёрных между кадрами (cardboard.fit_piano(prev=…));
  • на первом подтверждённом нажатии клавиша под кончиком объявляется ожидаемой нотой: разница кратна 12 → сдвиг
    меток; иначе пересканировать с сильной подсказкой, не вышло — ближайшая октава;
  • при замке запоминается якорь: самый фактурный участок полосы над чёрными (табличка, замок, узор) и его
    координата в единицах чертежа; каждый кадр якорь ищется шаблоном, и если метки уехали больше чем на полклавиши,
    чертёж пересканируется с подсказкой от якоря.
"""
from __future__ import annotations
import os
import numpy as np, cv2
import cardboard
LOCKED_HINT_W = float(os.environ.get("SOM_LOCKED_HINT_W", "1.0"))   # вес подсказки центра после замка (0.3 = как в прогоне 9/9)

def key_at(keys, x, y):
    for kind in ("black", "white"):
        for k in keys:
            if k["kind"] == kind and cv2.pointPolygonTest(np.array(k["poly"], dtype=np.int32), (float(x), float(y)), False) >= 0: return k
    return None

def _axis(info):
    a, b = info["axis"]; e = np.array([1.0, a]); e /= np.linalg.norm(e); o = np.array([0.0, b]); nrm = np.array([-e[1], e[0]])
    return o, e, nrm

def _t_of_u(f, u, near=None):
    """обратная к u = f(t): корень квадратного, ближе к near (или в пределах чертежа)."""
    c = np.array(f, dtype=np.float64).copy(); c[-1] -= u
    roots = np.roots(c); roots = roots[np.abs(roots.imag) < 1e-6].real if len(roots) else roots
    if len(roots) == 0: return None
    if near is not None: return float(roots[np.argmin(np.abs(roots - near))])
    ok = [r for r in roots if -6 <= r <= 60]
    return float(ok[0]) if ok else float(roots[0])

class PianoTracker:
    def __init__(self, hint: int | None = 64, track: bool = True, use_anchor: bool = False):
        # use_anchor: якорь над клавишами ставится при замке. По умолчанию выключен: с ракурса очков шаблон попадает на
        # периодический рисунок клавиш и притягивается к соседней октаве (регрессия 03.11: −7 белых сразу после замка)
        self.hint, self.track, self.use_anchor = hint, track, use_anchor
        self.prev = None; self.delta = 0; self.keys = None; self.info = None; self.n_scan = 0; self.n_track = 0; self.locked = False
        self.anchor = None; self.n_anchor_fix = 0; self.anchor_log = None

    # ---------------------------------------------------------------- шаг
    def step(self, polys, W, H, frame=None, anchor=None):
        """→ (keys с учётом замка или None, info/причина). frame — для якоря-шаблона (после замка, если use_anchor);
        anchor=(xy, t0) — внешний жёсткий якорь: например, кончик пальца на подтверждённой ноте, пока нота держится."""
        hw = LOCKED_HINT_W if self.locked else (0.3 if self.prev is not None else 0.0)
        anc = anchor if anchor is not None else (self._anchor_find(frame) if (self.anchor is not None and frame is not None) else None)   # (xy, t0)
        keys, info = cardboard.fit_piano(polys, W, H, hint_midi=self.hint, hint_weight=hw, prev=self.prev if self.track else None, anchor=anc)
        if keys is not None and anc is not None:
            k = self._drift(anc, info)
            if k is not None and abs(k) > 0.5:
                # слежение унаследовало сдвинутые метки: скан с жёстким якорем
                k2, i2 = cardboard.fit_piano(polys, W, H, hint_midi=self.hint, hint_weight=0.0, prev=None, anchor=anc)
                if k2 is not None:
                    kk = self._drift(anc, i2)
                    if kk is not None and abs(kk) <= abs(k):
                        keys, info = k2, i2; self.n_anchor_fix += 1
                        self.anchor_log = f"якорь: метки уехали на {k:+.1f} белых, скан с якорем → расхождение {kk:+.1f}"
        if keys is not None:
            self.prev = info; self.hint = info["center_midi"]; self.info = info
            self.keys = cardboard.relabel(keys, self.delta)
            if info.get("tracked"): self.n_track += 1
            else: self.n_scan += 1
        return (self.keys if keys is not None else None), info

    # ---------------------------------------------------------------- якорь
    def _strip(self, frame, info):
        """полоса над верхами чёрных: от 1 до 4 ширин белой выше оси; → (gray, y0, y1, wpx, o, e)"""
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        o, e, nrm = _axis(info); wpx = float(info["white_px"])
        return g, o, e, nrm, wpx

    def set_anchor(self, frame, info):
        g, o, e, nrm, wpx = self._strip(frame, info); H, W = g.shape[:2]
        tw, th = int(5 * wpx), int(3 * wpx)
        best = None
        for x in range(int(0.5 * wpx), W - tw, max(8, int(wpx / 2))):
            # центр окна на расстоянии 2,5 ширины белой над осью в точке x
            p = o + ((x + tw / 2) - o[0]) / e[0] * e - 2.5 * wpx * nrm
            x0, y0 = int(p[0] - tw / 2), int(p[1] - th / 2)
            if x0 < 0 or y0 < 0 or x0 + tw > W or y0 + th > H: continue
            patch = g[y0:y0 + th, x0:x0 + tw]
            tex = float(cv2.Laplacian(patch, cv2.CV_32F).var())
            if best is None or tex > best[0]: best = (tex, x0, y0, patch.copy())
        if best is None: return False
        tex, x0, y0, patch = best
        c = np.array([x0 + tw / 2, y0 + th / 2]); u0 = float((c - o) @ e); t0 = _t_of_u(info["f"], u0, near=26.0)
        if t0 is None: return False
        self.anchor = {"tpl": patch, "x": x0, "y": y0, "t": t0, "tex": tex, "wpx": wpx}
        return True

    def _anchor_find(self, frame):
        """найти якорь шаблоном рядом с прошлым местом → ((x, y) центра, t0) или None"""
        a = self.anchor; g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame; H, W = g.shape[:2]
        th, tw = a["tpl"].shape; r = int(8 * a["wpx"])
        x0, y0 = max(0, a["x"] - r), max(0, a["y"] - r); x1, y1 = min(W, a["x"] + tw + r), min(H, a["y"] + th + r)
        if x1 - x0 < tw + 2 or y1 - y0 < th + 2: return None
        res = cv2.matchTemplate(g[y0:y1, x0:x1], a["tpl"], cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(res)
        if mx < 0.55: return None
        a["x"], a["y"] = x0 + loc[0], y0 + loc[1]
        return (float(a["x"] + tw / 2), float(a["y"] + th / 2)), a["t"]

    def _drift(self, anc, info):
        """→ на сколько белых метки привязки info сдвинуты относительно якоря"""
        o, e, _ = _axis(info); u = float((np.array(anc[0]) - o) @ e); t = _t_of_u(info["f"], u, near=anc[1])
        return None if t is None else t - anc[1]

    # ---------------------------------------------------------------- замок
    def lock(self, polys, W, H, tip, expected: int, frame=None):
        """Первое подтверждённое нажатие: под кончиком tip должна быть нота expected. → (совпало, что было под пальцем)."""
        if self.keys is None: return False, None
        k = key_at(self.keys, *tip)
        if k is None: return False, None
        self.locked = True
        d = expected - k["midi"]; ok = True
        if d == 0: pass
        elif d % 12 == 0:
            self.delta += d; self.keys = cardboard.relabel(self.keys, d)
        else:
            # рисунок сдвинут на клавишу: пересканировать с жёстким якорем «под этим кончиком лежит ожидаемая нота»
            # (точная физическая опора; октава = 7 белых штрафуется на 42 очка, ошибиться на клавишу тоже дорого)
            keys2, info2 = cardboard.fit_piano(polys, W, H, hint_midi=None, hint_weight=0.0, prev=None,
                                               anchor=(tip, cardboard.template_t(expected)))
            k2 = key_at(keys2, *tip) if keys2 is not None else None
            if k2 is not None and (expected - k2["midi"]) % 12 == 0:
                self.prev = info2; self.info = info2; self.hint = info2["center_midi"]
                self.delta = expected - k2["midi"]; self.keys = cardboard.relabel(keys2, self.delta)
            else:
                dd = 12 * int(round(d / 12)); self.delta += dd; self.keys = cardboard.relabel(self.keys, dd); ok = False
        if self.use_anchor and frame is not None and self.info is not None: self.set_anchor(frame, self.info)
        return ok, k["midi"]
