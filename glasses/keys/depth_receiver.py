#!/usr/bin/env python3
"""Модуль глубины для стенда /keys: живой USB-поток Record3D (или офлайн PLY / реплей frames.csv)
→ события «палец на клавише / палец завис» в out/live/depth.json (атомарная запись каждый кадр).

Физика перенесена из lidar/ply_ref.py (разбор DC1 04.11: шум опоры 1,7–1,9 мм, дрейф ARKit ±8 мм —
поэтому поправка сдвига/наклона на каждом кадре). Опора = медиана высоты по клетке 4 мм по пустой
клавиатуре; маска руки dh>tau + открытие 3×3 + пятна ≥150 клеток; нажатие двумя каналами:
(а) низ руки <12 мм над опорой (отпуск >18 мм, гистерезис),
(б) клетки клавиши в −6..−20 мм под опорой не менее press-ms.
SAM/Vision в air_keys.py остаются основным трекером, глубина — второй канал подтверждения.
Клавиши из out/live/keys_piano.json проецируются в плоскость опоры лучами через интринсики
(режим --live, тот же телефон): blob_xy (м, координаты плоскости) → point-in-polygon → key/midi.

  .venv-lidar/bin/python keys/depth_receiver.py --live                   # USB-стрим Record3D
  .venv-lidar/bin/python keys/depth_receiver.py --ply clips/…/take/     # экспорт Record3D (первые calib-кадры пустые!)
  .venv-lidar/bin/python keys/depth_receiver.py --replay out/lidar/ref5/frames.csv
  .venv-lidar/bin/python keys/depth_receiver.py --selftest               # синтетика, без телефона
"""
import argparse
import json
import os
import sys
import time
from threading import Event

import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lidar"))
from plylib import fit_plane_ransac  # noqa: E402


# ---------- опорная поверхность и покадровый разбор (физика ply_ref.py) ----------

class Support:
    def __init__(self, cell=0.004, near=1.1):
        self.cell, self.near = cell, near
        self.ready = False

    def start(self, P0):
        self.nrm, self.dd, frac = fit_plane_ransac(P0[::3], iters=400, tol=0.004)
        self.u = np.cross(self.nrm, [1, 0, 0]); self.u /= np.linalg.norm(self.u)
        self.v = np.cross(self.nrm, self.u)
        pu, pv, _ = self.proj(P0)
        self.u0, self.v0 = pu.min() - 0.05, pv.min() - 0.05
        self.W = int((pu.max() - self.u0 + 0.05) / self.cell) + 1
        self.H = int((pv.max() - self.v0 + 0.05) / self.cell) + 1
        self.ref = np.full(self.W * self.H, np.nan, np.float32)
        self.cnt = np.zeros(self.W * self.H, np.int32)
        self._acc = []
        return frac

    def proj(self, P):
        return P @ self.u, P @ self.v, P @ self.nrm + self.dd

    def cells(self, pu, pv):
        xi = np.clip(((pu - self.u0) / self.cell).astype(int), 0, self.W - 1)
        yi = np.clip(((pv - self.v0) / self.cell).astype(int), 0, self.H - 1)
        return yi * self.W + xi

    def add_ref(self, P):
        pu, pv, h = self.proj(P)
        self._acc.append((self.cells(pu, pv), h.astype(np.float32)))

    def finish_ref(self):
        ids = np.concatenate([c for c, _ in self._acc]); hs = np.concatenate([h for _, h in self._acc])
        order = np.argsort(ids, kind="stable"); ids, hs = ids[order], hs[order]
        starts = np.r_[0, np.flatnonzero(np.diff(ids)) + 1, len(ids)]
        for s, e in zip(starts[:-1], starts[1:]):
            self.ref[ids[s]] = np.median(hs[s:e]); self.cnt[ids[s]] = e - s
        self._acc = []; self.ready = True
        return int((self.cnt > 0).sum())

    def analyze(self, P, tau, min_blob, press_band):
        """Кадр точек (камера, м) → метрики руки и утопленных клеток. dh считается от опоры
        с покадровой поправкой сдвига/наклона (2 прохода lstsq, как ply_ref)."""
        pu, pv, h = self.proj(P); c = self.cells(pu, pv); r = self.ref[c]; ok = ~np.isnan(r)
        dh = h[ok] - r[ok]
        surf = np.abs(dh) < tau
        drift = float(np.median(dh[surf])) * 1000 if surf.any() else float("nan")
        if surf.sum() > 100:
            cu = (c[ok] % self.W).astype(float); cvv = (c[ok] // self.W).astype(float)
            A = np.c_[cu, cvv, np.ones(len(cu))]
            for _ in range(2):
                coef, *_ = np.linalg.lstsq(A[surf], dh[surf], rcond=None)
                dh = dh - A @ coef; surf = np.abs(dh) < 0.006
        noise = float(dh[surf].std()) * 1000 if surf.any() else float("nan")
        cc = c[ok]
        gs = np.bincount(cc, weights=dh, minlength=self.W * self.H)
        gc = np.bincount(cc, minlength=self.W * self.H)
        gh = np.where(gc > 0, gs / np.maximum(gc, 1), np.nan).reshape(self.H, self.W)
        mask = (np.nan_to_num(gh, nan=-1) > tau).astype(np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        nlab, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        blobs = [j for j in range(1, nlab) if stats[j, cv2.CC_STAT_AREA] >= min_blob]
        keep = np.zeros(gh.shape, bool)
        for j in blobs:
            keep |= lab == j
        hv = gh[keep]
        low = float(np.nanpercentile(hv, 5)) * 1000 if hv.size else float("nan")
        blob_xy = None; blob_area = 0
        if blobs:
            big = max(blobs, key=lambda j: stats[j, cv2.CC_STAT_AREA])
            blob_area = int(stats[big, cv2.CC_STAT_AREA])
            br = stats[big, cv2.CC_STAT_TOP] + stats[big, cv2.CC_STAT_HEIGHT] / 2
            bc = stats[big, cv2.CC_STAT_LEFT] + stats[big, cv2.CC_STAT_WIDTH] / 2
            blob_xy = [round(self.u0 + (bc + 0.5) * self.cell, 4), round(self.v0 + (br + 0.5) * self.cell, 4)]
        g2 = np.nan_to_num(gh, nan=1)
        pm = ((g2 < -press_band[0]) & (g2 > -press_band[1])).astype(np.uint8)
        pm = cv2.morphologyEx(pm, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        npress = int(pm.sum())
        pmin = float(np.nanmin(gh[pm.astype(bool)])) * 1000 if npress else float("nan")
        return dict(low_mm=None if low != low else round(low, 1), hand_cells=int(keep.sum()),
                    blob_xy=blob_xy, blob_area=blob_area, drift_mm=None if drift != drift else round(drift, 2),
                    noise_mm=None if noise != noise else round(noise, 2),
                    press_cells=npress, press_min_mm=None if pmin != pmin else round(pmin, 1))


# ---------- машина состояний «нажата / завис / пусто» ----------

class PressState:
    def __init__(self, low_press=12.0, low_hover=18.0, cells_min=10, hold_ms=50.0):
        self.low_press, self.low_hover, self.cells_min = low_press, low_hover, cells_min
        self.hold = hold_ms / 1000
        self.state, self._pend, self._pend_t, self._cells_since = "none", None, 0.0, None

    def update(self, t, low_mm, press_cells, has_hand):
        raw = "none"
        if has_hand:
            a = low_mm == low_mm and low_mm < self.low_press
            if press_cells >= self.cells_min:
                if self._cells_since is None:
                    self._cells_since = t
            else:
                self._cells_since = None
            b = self._cells_since is not None and t - self._cells_since >= self.hold
            if a or b:
                raw = "press"
            elif self.state == "press" and low_mm == low_mm and low_mm <= self.low_hover:
                raw = "press"  # гистерезис: между порогами держим прежнее
            else:
                raw = "hover"
        else:
            self._cells_since = None
        if raw != self._pend:
            self._pend, self._pend_t = raw, t
        if raw != self.state and t - self._pend_t >= self.hold:
            self.state = raw
        return self.state


# ---------- клавиши: пиксели кадра → плоскость опоры ----------

def load_keys_plane(path, K, depth_shape, rgb_shape, sup):
    """keys_piano.json (полигоны в пикселях кадра того же телефона) → полигоны (u, v) в плоскости
    опоры: пиксель → масштаб к depth-сетке → луч через интринсики → пересечение с плоскостью."""
    try:
        keys = json.loads(open(path).read())
    except Exception as e:
        print(f"[keys] {path} не читается ({e}); сопоставление клавиш выключено", flush=True)
        return None
    sy = rgb_shape[0] / depth_shape[0]; sx = rgb_shape[1] / depth_shape[1]
    out, bad = [], 0
    for k in keys:
        poly = []
        for px, py in k.get("poly", []):
            c, r = px / sx, py / sy
            d = np.array([(c - K.tx) / K.fx, (r - K.ty) / K.fy, 1.0])
            denom = float(sup.nrm @ d)
            t = -sup.dd / denom if abs(denom) > 1e-9 else -1.0
            if t <= 0:
                poly = None; break
            pu, pv, _ = sup.proj((t * d)[None, :])
            poly.append((float(pu[0]), float(pv[0])))
        if poly:
            out.append(dict(k, poly_uv=poly))
        else:
            bad += 1
    if bad or not out:
        print(f"[keys] {len(out)} клавиш спроецировано, {bad} мимо плоскости", flush=True)
    return out or None


def match_key(blob_xy, keys_plane):
    if not blob_xy or not keys_plane:
        return None
    pt = (float(blob_xy[0]), float(blob_xy[1]))
    best = None
    for k in keys_plane:
        poly = np.array(k["poly_uv"], np.float32)
        if cv2.pointPolygonTest(poly, pt, False) >= 0:
            if best is None or len(k["poly"]) < len(best["poly"]):
                area = cv2.contourArea(poly)
                if best is None or area < best[0]:
                    best = (area, k)
    if not best:
        return None
    k = best[1]
    return {"name": k.get("name"), "midi": k.get("midi"), "kind": k.get("kind")}


# ---------- выход ----------

def emit(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(payload, fh)
    os.replace(tmp, path)


def backproject(depth, K, near, rgb_shape=None):
    """Depth-карта (м) → точки в камере. Внимание: get_intrinsic_mat отдаёт коэффициенты
    в масштабе RGB-кадра (проверено живьём 05.11: центр 723/961 = портрет 1440×1920),
    поэтому при передаче rgb_shape пересчитываем их в пиксели depth-сетки."""
    H, W = depth.shape
    fx, fy, tx, ty = K.fx, K.fy, K.tx, K.ty
    if rgb_shape is not None:
        sx = W / rgb_shape[1]; sy = H / rgb_shape[0]
        fx *= sx; tx *= sx; fy *= sy; ty *= sy
    rr, cc = np.mgrid[0:H, 0:W]
    z = depth.ravel().astype(np.float64)
    ok = np.isfinite(z) & (z > 0.05) & (z < near)
    z = z[ok]
    r = rr.ravel()[ok].astype(np.float64); c = cc.ravel()[ok].astype(np.float64)
    return np.c_[(c - tx) / fx * z, (r - ty) / fy * z, z]


# ---------- режимы ----------

def run_live(a):
    from record3d import Record3DStream
    sup, keys_plane = None, None
    if a.load_ref and os.path.exists(a.load_ref):
        sup = Support(a.cell, a.near); _load_ref(sup, a.load_ref)
        print(f"[ref] загружена {a.load_ref}: сетка {sup.W}×{sup.H}", flush=True)
    st = PressState(a.press_low, a.hover_high, a.press_cells, a.press_ms)
    n = 0; t0 = None; ivals = []; last_log = 0; calib = []; K = rgb_shape = None
    while True:  # реконнекты: приложение можно перезапускать, калибровка (sup) переживает
        devs = Record3DStream.get_connected_devices()
        if not devs:
            print("iPhone по USB не найден, жду 5 с (кабель/доверие?)…", flush=True)
            time.sleep(5); continue
        ev = Event(); stopped = [False]
        s = Record3DStream()
        s.on_new_frame = ev.set
        s.on_stream_stopped = lambda: (stopped.__setitem__(0, True), print("stream stopped", flush=True))
        try:
            s.connect(devs[0])
        except Exception as e:
            print("connect не прошёл:", e, "— повтор через 3 с", flush=True)
            time.sleep(3); continue
        print("connected; жду кадры (красная кнопка в Record3D)", flush=True)
        while True:
            if not ev.wait(5):
                print("нет кадров 5 с" if n == 0 else "поток прервался", flush=True)
                if n == 0:
                    break  # к кнопке не притронулись — на новый коннект (приложение могли перезапустить)
                if stopped[0] or not Record3DStream.get_connected_devices():
                    break
                continue
            if stopped[0] and not ev.wait(1):
                print("сессия закрыта приложением — переподключаюсь", flush=True)
                break
            ev.clear()
            now = time.time(); t0 = t0 or now; n += 1
            ivals.append(now); ivals = [t for t in ivals if now - t <= 3]
            depth = s.get_depth_frame()
            if n == 1:
                K = s.get_intrinsic_mat(); rgb_shape = s.get_rgb_frame().shape[:2]
                print(f"depth {depth.shape} {depth.dtype}  rgb {rgb_shape}  fx {K.fx:.1f} fy {K.fy:.1f} "
                      f"tx {K.tx:.1f} ty {K.ty:.1f}  device {s.get_device_type()}", flush=True)
            P = backproject(depth, K, a.near, rgb_shape)
            if not sup or not sup.ready:
                if sup is None:
                    sup = Support(a.cell, a.near)
                    frac = sup.start(P)
                    print(f"[calib] плоскость: инлаеры {frac:.2f}, нормаль {np.round(sup.nrm, 3)}; "
                          f"кинешу прочь — собираю опору {a.calib_sec:.0f} с", flush=True)
                calib.append((now, P)); sup.add_ref(P)
                if now - calib[0][0] >= a.calib_sec and len(calib) >= 30:
                    cells = sup.finish_ref()
                    print(f"[calib] опора готова: клеток с данными {cells} из {sup.W * sup.H}; "
                          f"сохраняю в {a.save_ref}", flush=True)
                    _save_ref(sup, a.save_ref)
                    keys_plane = load_keys_plane(a.keys, K, depth.shape, rgb_shape, sup)
                continue
            t = now - t0
            if t < a.drop_first:
                continue
            fps = (len(ivals) - 1) / max(ivals[-1] - ivals[0], 1e-6) if len(ivals) > 2 else 0.0
            m = sup.analyze(P, a.tau, a.min_blob, (a.press_band, 0.020))
            state = st.update(t, m["low_mm"] if m["low_mm"] is not None else float("nan"),
                              m["press_cells"], m["blob_area"] > 0)
            emit(a.out_json, dict(t=round(t, 3), state=state, src="live", fps=round(fps, 1), **m,
                                  key=match_key(m["blob_xy"], keys_plane)))
            if now - last_log >= a.log_every:
                print(f"t={t:5.1f}s frames={n} fps={fps:.0f} {state} low={m['low_mm']} "
                      f"cells={m['press_cells']} drift={m['drift_mm']}", flush=True)
                last_log = now
        time.sleep(1)


def run_ply(a):
    files = None
    sup = Support(a.cell, a.near)
    st = PressState(a.press_low, a.hover_high, a.press_cells, a.press_ms)
    n_total = 0; calib_n = int(a.calib_sec * 60); started = None; last_log = time.time()
    for name, d in iter_frames_u(a.ply):
        P = np.c_[d["x"], d["y"], d["z"]]; P = P[np.isfinite(P).all(1)]
        P = P[np.linalg.norm(P, axis=1) < a.near]
        if n_total == 0:
            frac = sup.start(P)
            print(f"[calib] {name}: плоскость инлаеры {frac:.2f}; первые {calib_n} кадров должны быть без руки", flush=True)
        n_total += 1
        if not sup.ready:
            sup.add_ref(P)
            if n_total >= calib_n:
                cells = sup.finish_ref()
                print(f"[calib] опора из {n_total} кадров: клеток {cells} из {sup.W * sup.H}", flush=True)
            continue
        t = (n_total - calib_n) / 60.0
        if t < a.drop_first:
            continue
        m = sup.analyze(P, a.tau, a.min_blob, (a.press_band, 0.020))
        state = st.update(t, m["low_mm"] if m["low_mm"] is not None else float("nan"),
                          m["press_cells"], m["blob_area"] > 0)
        emit(a.out_json, dict(t=round(t, 3), state=state, src="ply", fps=60.0, **m, key=None))
        if time.time() - last_log >= a.log_every:
            print(f"frame {n_total} t={t:5.1f}s {state} low={m['low_mm']} cells={m['press_cells']}", flush=True)
            last_log = time.time()
    print(f"[ply] кадров {n_total}, конец", flush=True)
    return 0


def run_replay(a):
    import csv
    rows = list(csv.DictReader(open(a.replay)))
    st = PressState(a.press_low, a.hover_high, a.press_cells, a.press_ms)
    events = []; counts = {"press": 0, "hover": 0, "none": 0}
    for r in rows:
        frame = int(r["frame"]); t = frame / 60.0
        if t < a.drop_first:
            continue
        low = r["hand_low_mm"]
        low = float(low) if low not in ("", "nan") else float("nan")
        cells = int(float(r["press_cells"] or 0))
        hand = int(float(r["hand_pts"] or 0)) > 0
        state = st.update(t, low, cells, hand)
        counts[state] += 1
        if events and events[-1][0] == state:
            events[-1] = (state, events[-1][1], round(t, 2))
        else:
            events.append((state, round(t, 2), round(t, 2)))
        emit(a.out_json, dict(t=round(t, 3), state=state, src="replay", fps=60.0,
                              low_mm=None if low != low else round(low, 1), press_cells=cells,
                              blob_xy=None, blob_area=int(float(r["blob_area"] or 0)),
                              drift_mm=float(r["drift_mm"]) if r["drift_mm"] not in ("", "nan") else None,
                              key=None))
    presses = [e for e in events if e[0] == "press"]
    false_early = [e for e in presses if e[1] < 16.0]
    print(f"[replay] кадров {len(rows)} (после drop {sum(counts.values())}); состояния {counts}; "
          f"press-отрезков {len(presses)}", flush=True)
    for e in events[:40]:
        print(f"  {e[0]:5s} {e[1]:7.2f} → {e[2]} s", flush=True)
    print(f"[replay] ложных press до 16-й секунды: {len(false_early)}", flush=True)
    return 0 if not false_early else 1


def run_selftest(a):
    rng = np.random.default_rng(0)
    sup = Support(a.cell, a.near)
    xs = np.linspace(-0.22, 0.22, 200); ys = np.linspace(-0.15, 0.15, 150)
    gx, gy = np.meshgrid(xs, ys)
    def plane_pts(shift=0.0, tilt=0.0):
        z = 0.70 + shift + tilt * gx.ravel() + rng.normal(0, 0.0015, gx.size)
        return np.c_[gx.ravel(), gy.ravel(), z]
    sup.start(plane_pts())
    for _ in range(30):
        sup.add_ref(plane_pts())
    sup.finish_ref()
    def finger_pts(h_mm, drift=0.004, tilt=0.01, sunk=False):
        P = plane_pts(drift, tilt)  # дрейф мира + наклон — поправка обязана их снять
        sel = (np.abs(P[:, 0] - 0.02) < 0.03) & (np.abs(P[:, 1] + 0.03) < 0.04)  # пятно ~60×80 мм = как ладонь
        P[sel, 2] -= h_mm / 1000.0
        if sunk:  # под рукой клавиша ушла вниз на 8 мм — канал (б) обязан это увидеть
            band = (P[:, 0] > -0.07) & (P[:, 0] < -0.03) & (P[:, 1] > -0.06) & (P[:, 1] < 0.0)
            P[band, 2] += 0.008
        return P
    st = PressState(a.press_low, a.hover_high, a.press_cells, a.press_ms)
    out = []
    for i in range(12):  # висим 25 мм
        out.append(st.update(i * 0.016, 25.0, 0, True))
    for i in range(12):  # нажали: верх пальца 7 мм + утопленные клетки
        out.append(st.update(0.2 + i * 0.016, 7.0, 40, True))
    for i in range(12):  # отпустили
        out.append(st.update(0.4 + i * 0.016, 22.0, 0, True))
    m_hover = sup.analyze(finger_pts(25), a.tau, a.min_blob, (a.press_band, 0.020))
    m_press = sup.analyze(finger_pts(7, drift=0.006, sunk=True), a.tau, a.min_blob, (a.press_band, 0.020))
    ok_states = (out[4] == out[5] == "hover" and out[16] == out[23] == "press"
                 and out[-1] == "hover" and out[0] == "none")  # hold 50 мс = 4 кадра по 16 мс
    found = m_hover["blob_area"] >= a.min_blob and m_press["blob_area"] >= a.min_blob
    sep = (m_hover["low_mm"] or 0.0) - (m_press["low_mm"] or 0.0)
    # low на крутой кромке демпфируется (~h/2 из-за смешения краевых клеток), но обязан быть
    # монотонным и различать вис/нажатие; точные пороги снимаются с живых данных (DC1: 12/18 мм)
    ok_low = sep >= 4.0
    ok_press = m_press["low_mm"] is not None and m_press["low_mm"] <= a.press_low
    ok_cells = m_press["press_cells"] >= 5  # канал (б): утопленная клавиша видна
    ok_drift = m_press["drift_mm"] is not None and 1 <= abs(m_press["drift_mm"]) <= 12  # дрейф виден, но не ломает low
    ok = ok_states and found and ok_low and ok_press and ok_cells and ok_drift
    print(f"[selftest] states={ok_states} found={found} hover low={m_hover['low_mm']} press low={m_press['low_mm']} "
          f"sep={sep:.1f} drift={m_press['drift_mm']} cells={m_press['press_cells']} → "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return 0 if ok else 1


def iter_frames_u(path):
    from plylib import iter_frames
    return iter_frames(path)


def _save_ref(sup, path):
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, nrm=sup.nrm, dd=sup.dd, u=sup.u, v=sup.v, u0=sup.u0, v0=sup.v0,
             W=sup.W, H=sup.H, ref=sup.ref)


def _load_ref(sup, path):
    z = np.load(path)
    sup.nrm, sup.dd, sup.u, sup.v = z["nrm"], float(z["dd"]), z["u"], z["v"]
    sup.u0, sup.v0, sup.W, sup.H = float(z["u0"]), float(z["v0"]), int(z["W"]), int(z["H"])
    assert sup.W * sup.H == len(z["ref"]), f"cell не совпадает с сохранённой опорой {path}"
    sup.ref = z["ref"]; sup.ready = True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="живой USB-стрим Record3D")
    mode.add_argument("--ply", metavar="DIR|ZIP", help="офлайн-экспорт Record3D (первые calib-кадры пустые)")
    mode.add_argument("--replay", metavar="CSV", help="реплей frames.csv из ply_ref (машина состояний)")
    mode.add_argument("--selftest", action="store_true", help="синтетический тест без телефона")
    ap.add_argument("--cell", type=float, default=0.004)
    ap.add_argument("--near", type=float, default=1.1, help="радиус от камеры, м")
    ap.add_argument("--tau", type=float, default=0.005, help="порог маски руки, м (5 мм живой, 10 безопасно)")
    ap.add_argument("--min-blob", type=int, default=150, help="мин. клеток в пятне руки")
    ap.add_argument("--press-low", type=float, default=12.0, help="низ руки ниже (мм) = press")
    ap.add_argument("--hover-high", type=float, default=18.0, help="низ руки выше (мм) = отпуск")
    ap.add_argument("--press-band", type=float, default=0.006, help="клавиша утоплена ниже опоры на (м)")
    ap.add_argument("--press-cells", type=int, default=10, help="мин. утопленных клеток для канала (б)")
    ap.add_argument("--press-ms", type=float, default=50.0, help="стабильность состояния, мс")
    ap.add_argument("--calib-sec", type=float, default=5.0, help="пустая клавиатура для опоры, с")
    ap.add_argument("--drop-first", type=float, default=1.0, help="выбросить первые N с после старта")
    ap.add_argument("--keys", default="out/live/keys_piano.json", help="раскладка (пиксели того же телефона)")
    ap.add_argument("--out-json", default="out/live/depth.json")
    ap.add_argument("--save-ref", default="out/lidar/ref_live.npz", help="куда сохранить опору (--live)")
    ap.add_argument("--load-ref", default="", help="загрузить сохранённую опору вместо калибровки")
    ap.add_argument("--log-every", type=float, default=5.0)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out_json) or ".", exist_ok=True)
    if a.selftest:
        sys.exit(run_selftest(a))
    if a.live:
        sys.exit(run_live(a))
    if a.ply:
        sys.exit(run_ply(a))
    if a.replay:
        sys.exit(run_replay(a))


if __name__ == "__main__":
    main()
