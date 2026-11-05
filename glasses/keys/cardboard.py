# -*- coding: utf-8 -*-
"""Картонная клавиатура Камилы как известное устройство: чертёж + привязка чертежа к кадру.

Чертёж: 24 белых клавиши по 30 мм от C, 17 чёрных 17×95 мм, центры чёрных на границах
после C, D, F, G, A (как в keyboard_template.pdf). Ноты заданы чертежом, из картинки
ничего не угадывается. В кадре SAM находит только чёрные клавиши (их он берёт чисто),
по ним считается гомография чертёж → кадр, и все 41 клавиша переносятся в кадр целиком:
без дыр, с правильными нотами, и карта следует за головой, пока видны хотя бы 4 чёрных.
"""
from __future__ import annotations
import math
import numpy as np
import cv2

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
WHITE_PCS = [0, 2, 4, 5, 7, 9, 11]

# Профили устройств. Единицы чертежа: ширина белой = 1.
# cardboard — картонка Камилы (24 белых от C{base_octave}, 17 чёрных 17×95 мм, белая 30×150 мм).
# piano — стандартная клавиатура: 52 белых от A0 (midi 21), белая 23,5×150 мм, чёрная 11×95 мм.
PROFILES = {
    "cardboard": dict(white_mm=30.0, white_len_mm=150.0, black_mm=17.0, black_len_mm=95.0, n_white=24, start_midi=None),
    "piano": dict(white_mm=23.5, white_len_mm=150.0, black_mm=11.0, black_len_mm=95.0, n_white=52, start_midi=21),
}


def dims(profile: str = "cardboard"):
    """→ (WHITE_W, WHITE_L, BLACK_W, BLACK_L, N_WHITE, start_midi) в единицах чертежа."""
    d = PROFILES[profile]; w = d["white_mm"]
    return 1.0, d["white_len_mm"] / w, d["black_mm"] / w, d["black_len_mm"] / w, d["n_white"], d["start_midi"]


# совместимость: константы картонки, как раньше
WHITE_W, WHITE_L, BLACK_W, BLACK_L, N_WHITE, _ = dims("cardboard")


def template(base_octave: int = 4, profile: str = "cardboard"):
    """→ (whites, blacks): списки dict(kind, midi, name, rect=(x0,y0,x1,y1)) в единицах чертежа.
    y=0 — дальний край (где чёрные), y растёт к играющему. Картонка начинается с C{base_octave}, пианино — с A0."""
    ww, wl, bw, bl, n_white, start = dims(profile)
    if start is None: start = 12 * (base_octave + 1)
    whites, blacks = [], []; midi = start
    for i in range(n_white):
        while midi % 12 not in WHITE_PCS: midi += 1
        pc = midi % 12
        whites.append({"kind": "white", "midi": midi, "name": NOTE_NAMES[pc] + str(midi // 12 - 1),
                       "rect": (i * ww, 0.0, (i + 1) * ww, wl)})
        if pc in (0, 2, 5, 7, 9) and i + 1 < n_white:
            bx = (i + 1) * ww
            blacks.append({"kind": "black", "midi": midi + 1, "name": NOTE_NAMES[pc + 1] + str(midi // 12 - 1),
                           "rect": (bx - bw / 2, 0.0, bx + bw / 2, bl), "cx": bx})
        midi += 1
    return whites, blacks


# группы чёрных в чертеже слева направо: 2,3,2,3,2,3,2 (всего 17)
def _groups(xs, w=None):
    """Разбиение по зазорам с учётом перспективы: зазор между группами ≈ вдвое больше соседних зазоров."""
    n = len(xs)
    if n < 2: return [[0]] if n else []
    g = [xs[i + 1] - xs[i] for i in range(n - 1)]
    out = [[0]]
    for i, gap in enumerate(g):
        nb = [g[j] for j in (i - 1, i + 1) if 0 <= j < len(g)]
        ref = min(nb) if nb else (w or gap)
        if w is not None and not nb: ref = w
        (out.append([i + 1]) if gap > 1.5 * ref else out[-1].append(i + 1))
    return out


def _nearest_row(det, k=1.2):
    """Отражение в лаке даёт второй ряд чёрных выше настоящего. Оставляем ближний (нижний) ряд из ≥3 клавиш."""
    if len(det) < 4: return det
    hs = [max(q[1] for q in d["poly"]) - min(q[1] for q in d["poly"]) for d in det]
    bh = float(np.median(hs))
    srt = sorted(det, key=lambda d: d["c"][1]); rows = [[srt[0]]]
    for d in srt[1:]:
        (rows[-1].append(d) if d["c"][1] - rows[-1][-1]["c"][1] <= k * bh else rows.append([d]))
    good = [r for r in rows if len(r) >= 3]
    return good[-1] if good else det


def fit(black_polys, W, H, base_octave: int = 4, max_err: float = 8.0, gray=None,
        profile: str = "cardboard", hint_midi: int | None = None, hint_weight: float = 0.0):
    """black_polys: список полигонов чёрных клавиш в кадре [(x,y),...]. → (keys, info) или (None, why).
    keys — как в air_keys: kind, poly, cx, cy, midi, name.
    profile: "cardboard" | "piano". hint_midi: какая нота примерно в центре кадра (для пианино рисунок чёрных
    повторяется каждую октаву, и без подсказки октава не определяется; по умолчанию 64 = E4, середина)."""
    if profile == "piano":
        return fit_piano(black_polys, W, H, hint_midi if hint_midi is not None else 64, hint_weight=hint_weight)
    if len(black_polys) < 3:
        return None, f"чёрных найдено {len(black_polys)}, нужно ≥3"
    det = []
    for poly in black_polys:
        P = np.array(poly, dtype=np.float32)
        cx, cy = P[:, 0].mean(), P[:, 1].mean()
        # верх/низ клавиши: средние точки 20 % самых верхних и самых нижних вершин
        # (проверено 02.11: вариант «по доле высоты» ронял AUC DINO с 0,85 до 0,75 — кропы клавиш плавали)
        ys = P[:, 1]; order = np.argsort(ys); k = max(1, len(P) // 5)
        top = P[order[:k]].mean(0); bot = P[order[-k:]].mean(0)
        det.append({"c": (cx, cy), "top": tuple(top), "bot": tuple(bot), "poly": poly})
    det = _nearest_row(det)
    det.sort(key=lambda d: d["c"][0])
    # SAM иногда отдаёт две маски на одну чёрную: сливаем пересекающиеся рамки (IoU > 0.3), оставляем большую
    # SAM иногда отдаёт две маски на одну чёрную: сливаем, когда пересекаются и рамки (IoU > 0.3), и сами
    # полигоны (IoU > 0.15) — у наклонённых перспективой соседних чёрных рамки пересекаются, а полигоны нет
    def bbox(d):
        P = np.array(d["poly"]); return P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()
    def iou_box(a, b):
        ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
        inter = ix * iy; ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
        return inter / ua if ua > 0 else 0.0
    def hull(d):
        return cv2.convexHull(np.array(d["poly"], np.float32).reshape(-1, 1, 2)).reshape(-1, 2).astype(np.float32)
    def iou_poly(a, b):
        inter, _ = cv2.intersectConvexConvex(a, b); ua = cv2.contourArea(a) + cv2.contourArea(b) - inter
        return inter / ua if ua > 0 else 0.0
    kept = []
    for d in det:
        bd, hd = bbox(d), hull(d); dup = None
        for i, (k, bk, hk) in enumerate(kept):
            if iou_box(bd, bk) > 0.3 and iou_poly(hd, hk) > 0.15: dup = i; break
        if dup is None: kept.append((d, bd, hd))
        elif cv2.contourArea(hd) > cv2.contourArea(kept[dup][2]): kept[dup] = (d, bd, hd)
    det = [d for d, _, _ in kept]
    xs = [d["c"][0] for d in det]
    dg = _groups(xs)                         # группы индексов det
    inner = [xs[i + 1] - xs[i] for grp in dg for i in grp[:-1]]
    w = float(np.median(inner)) if inner else float(np.median(np.diff(xs)) / 2 if len(xs) > 1 else 1.0)
    if w < 3:
        return None, "чёрные слишком близко — не клавиатура"
    whites_t, blacks_t = template(base_octave, profile)
    _, WHITE_L, _, BLACK_L, _, _ = dims(profile)
    if hint_midi is None: hint_midi = 64 if profile == "piano" else None
    tg = _groups([b["cx"] for b in blacks_t])   # группы индексов чертежа: [0,1],[2,3,4],...
    best = None
    import itertools
    # перебираем, какой группе чертежа соответствует первая группа кадра;
    # неполные группы (SAM пропустил чёрную или край кадра) — обе прижимки, лишнее отсеет RANSAC
    for off in range(len(tg)):
        if off + len(dg) > len(tg): continue
        opts = []
        for j, grp in enumerate(dg):
            tgrp = tg[off + j]; n, m = len(grp), len(tgrp)
            if n > m: opts = None; break
            if n == m: opts.append([0])
            elif j == 0 and len(dg) > 1: opts.append([m - n])          # первая неполная: видны последние чёрные
            elif j == len(dg) - 1 and len(dg) > 1: opts.append([0])    # последняя неполная: видны первые
            else: opts.append(list(range(m - n + 1)))                   # внутри или одна группа: все сдвиги
        if opts is None: continue
        combos = list(itertools.product(*opts))
        if len(combos) > 64: combos = combos[:64]
        for combo in combos:
            src, dst = [], []
            for j, grp in enumerate(dg):
                tgrp = tg[off + j]
                for q, di in enumerate(grp):
                    b = blacks_t[tgrp[combo[j] + q]]; d = det[di]
                    src += [(b["cx"], BLACK_L / 2), (b["cx"], 0.0), (b["cx"], BLACK_L)]
                    dst += [d["c"], d["top"], d["bot"]]
            src = np.array(src, np.float32); dst = np.array(dst, np.float32)
            if len(src) < 6: continue
            Hm, mask = cv2.findHomography(src, dst, cv2.RANSAC, max_err)
            if Hm is None: continue
            proj = cv2.perspectiveTransform(src.reshape(-1, 1, 2), Hm).reshape(-1, 2)
            err = np.linalg.norm(proj - dst, axis=1)
            inl = int(mask.sum()) if mask is not None else 0
            bright = 0
            if gray is not None:                                   # сколько белых чертежа легли на светлое
                pts = np.array([[(x0 + x1) / 2, WHITE_L * 0.8] for (x0, _, x1, _) in (k["rect"] for k in whites_t)], np.float32)
                pw = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), Hm).reshape(-1, 2)
                pb = cv2.perspectiveTransform(np.array([[b["cx"], BLACK_L / 2] for b in blacks_t], np.float32).reshape(-1, 1, 2), Hm).reshape(-1, 2)
                def val(P):
                    out = []
                    for x, y in P:
                        if 0 <= x < W and 0 <= y < H: out.append(float(gray[int(y), int(x)]))
                    return out
                vw, vb = val(pw), val(pb)
                if vw and vb:
                    thr = (np.median(vw) + np.median(vb)) / 2
                    bright = sum(v > thr for v in vw) + sum(v < thr for v in vb)
            hint = 0.0
            if hint_midi is not None:                                # какая белая чертежа легла в центр кадра
                cw = cv2.perspectiveTransform(np.array([[(x0 + x1) / 2, WHITE_L * 0.6] for (x0, _, x1, _) in (k["rect"] for k in whites_t)], np.float32).reshape(-1, 1, 2), Hm).reshape(-1, 2)
                ic = int(np.argmin(np.abs(cw[:, 0] - W / 2) + np.abs(cw[:, 1] - H / 2) * 0.25))
                hint = -abs(whites_t[ic]["midi"] - hint_midi)
            score = (inl, bright, -round(float(np.median(err))), hint, -float(np.median(err)))
            if best is None or score > best[0]:
                best = (score, Hm, len(src) // 3, float(np.median(err)), off)
    if best is None:
        return None, "не удалось сопоставить чёрные с чертежом"
    score, Hm, n_used, med_err, off = best
    if med_err > max_err or score[0] < 6:
        return None, f"привязка плохая: ошибка {med_err:.1f} px, опорных точек {score[0]}"
    keys = []
    for k in whites_t + blacks_t:
        x0, y0, x1, y1 = k["rect"]
        pts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32).reshape(-1, 1, 2)
        P = cv2.perspectiveTransform(pts, Hm).reshape(-1, 2)
        # клавиши, целиком вне кадра, не нужны
        if P[:, 0].max() < 0 or P[:, 0].min() > W or P[:, 1].max() < 0 or P[:, 1].min() > H: continue
        poly = [(float(x), float(y)) for x, y in P]
        keys.append({"kind": k["kind"], "poly": poly, "cx": float(P[:, 0].mean()), "cy": float(P[:, 1].mean()),
                     "midi": k["midi"], "name": k["name"], "conf": 1.0, "layout": profile})
    info = {"blacks_matched": n_used, "err_px": med_err, "first_group": off, "white_px": w,
            "H": Hm.tolist(), "in_frame": len(keys), "profile": profile}
    return keys, info


def draw(img, keys, color_w=(0, 200, 255), color_b=(255, 160, 0)):
    for k in keys:
        P = np.array(k["poly"], np.int32)
        cv2.polylines(img, [P], True, color_b if k["kind"] == "black" else color_w, 1)
        cv2.putText(img, k["name"], (int(k["cx"]) - 10, int(k["cy"]) + (4 if k["kind"] == "black" else 30)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
    return img


if __name__ == "__main__":
    import sys, time
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import air_keys as ak
    sam = ak.LocalSam()
    for f in sys.argv[1:]:
        fr = cv2.imread(f); H, W = fr.shape[:2]
        t0 = time.perf_counter()
        bl = sam.masks(fr, "black piano key", 1008, 0.3)
        polys = []
        for conf, m in bl:
            if m.shape != (H, W): m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
            p = ak.poly_from_mask(m)
            if p is not None: polys.append(p)
        keys, info = fit(polys, W, H, gray=cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY))
        dt = time.perf_counter() - t0
        if keys is None:
            print(f"{f}: НЕТ — {info} ({dt:.2f} с, чёрных масок {len(polys)})"); continue
        print(f"{f}: {len(keys)} клавиш в кадре, чёрных сопоставлено {info['blacks_matched']}, ошибка {info['err_px']:.1f} px, "
              f"первая группа #{info['first_group']}, {dt:.2f} с → {[k['name'] for k in keys if k['kind']=='white']}")
        out = Path(f).with_suffix(".cardboard.jpg"); cv2.imwrite(str(out), draw(fr.copy(), keys)); print("  →", out)


# ---------------------------------------------------------------------------------------------
# Настоящее пианино (02.11.2026, запись с очков). Гомография по маскам чёрных здесь не держится:
# широкий угол гнёт клавиатуру дугой, SAM сливает соседние чёрные, руки закрывают часть ряда.
# Одномерная модель: ось клавиатуры — прямая по верхам чёрных; положение вдоль оси u — гладкая
# (квадратичная) функция координаты чертежа t; глубина клавиш и наклон их краёв — из самих чёрных.
# ---------------------------------------------------------------------------------------------

def _split_fused(black_polys):
    """SAM часто сливает две соседние чёрные в одну маску (ширина ≈ 2 обычных): режем по x и вынимаем контуры."""
    if len(black_polys) < 4: return black_polys
    ws = [max(q[0] for q in p) - min(q[0] for q in p) for p in black_polys]
    med = float(np.median(ws)); out = []
    for p, w in zip(black_polys, ws):
        n = int(round(w / med)) if w > 1.6 * med else 1
        if n <= 1: out.append(p); continue
        P = np.array(p, np.float32); x0, y0 = P.min(0); x1, y1 = P.max(0)
        m = np.zeros((int(y1 - y0) + 3, int(x1 - x0) + 3), np.uint8)
        cv2.fillPoly(m, [np.round(P - [x0 - 1, y0 - 1]).astype(np.int32)], 255)
        step = m.shape[1] / n
        for i in range(n):
            part = np.zeros_like(m); a, b = int(i * step), int((i + 1) * step); part[:, a:b] = m[:, a:b]
            cnts, _ = cv2.findContours(part, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cnts: continue
            c = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(c) < 40: continue
            q = cv2.approxPolyDP(c, 0.01 * cv2.arcLength(c, True), True).reshape(-1, 2).astype(np.float32) + [x0 - 1, y0 - 1]
            out.append([(float(x), float(y)) for x, y in q])
    return out


def _robust_line(P, rounds=3):
    """y = a x + b по точкам (N,2), отбрасывая выбросы > 2.5 медианных остатков. → (a, b, good)"""
    P = np.asarray(P, np.float64); A = np.c_[P[:, 0], np.ones(len(P))]; good = np.ones(len(P), bool)
    for _ in range(rounds):
        coef, *_ = np.linalg.lstsq(A[good], P[good, 1], rcond=None)
        e = np.abs(P[:, 1] - A @ coef); thr = max(2.0, 2.5 * float(np.median(e[good])))
        new = e <= thr
        if new.sum() < 3 or np.array_equal(new, good): break
        good = new
    return float(coef[0]), float(coef[1]), good


def fit_piano(black_polys, W, H, hint_midi: int | None = 64, max_err_frac: float = 0.25, hint_weight: float = 0.0, prev=None, anchor=None):
    """Настоящая клавиатура (52 белых от A0). → (keys, info) или (None, why). keys — как в fit().
    hint_midi: нота примерно в центре кадра; при hint_weight=0 решает только ничьи (октава), при >0 штрафует
    гипотезы за каждый полутон отклонения центра (слежение: подавать центр предыдущего кадра с весом ~0.3).
    prev: info предыдущей удачной привязки → метки чёрных наследуются по близости центров (скан не нужен,
    рисунок не прыгает между кадрами); при потере слежения (<4 унаследованных) — обычный скан.
    anchor: (xy якоря в кадре, t0 его координата в чертеже в ширинах белой) — жёсткое ограничение: гипотеза
    штрафуется на 6 очков за каждую белую, на которую якорь уехал от t0 (октава = 7 белых → её не перепутать)."""
    whites_t, blacks_t = template(4, "piano")
    _, WL, _, BL, _, _ = dims("piano")
    polys = _split_fused(black_polys)
    if len(polys) < 4: return None, f"чёрных найдено {len(polys)}, нужно ≥4"
    det = []
    for poly in polys:
        P = np.array(poly, dtype=np.float32); ys = P[:, 1]; order = np.argsort(ys); k = max(1, len(P) // 5)
        det.append({"c": P.mean(0), "top": P[order[:k]].mean(0), "bot": P[order[-k:]].mean(0), "poly": poly})
    det = _nearest_row(det); det.sort(key=lambda d: d["c"][0])
    if len(det) < 4: return None, "после отбора ближнего ряда чёрных < 4"
    # ось: прямая по верхам чёрных
    a, b, good = _robust_line([d["top"] for d in det])
    e = np.array([1.0, a]); e /= np.linalg.norm(e); nrm = np.array([-e[1], e[0]])      # nrm смотрит вниз (к играющему)
    o = np.array([0.0, b])
    def to_u(p): return float((np.asarray(p, np.float64) - o) @ e)
    def on_axis(u): return o + u * e
    # положение каждой чёрной на оси: главная ось полигона (моменты) продолжена до прямой верхов.
    # центр маски лежит на половине глубины и при сходящихся краях смещён вбок, верх маски шумит
    for d in det:
        P = np.array(d["poly"], np.float32); m = cv2.moments(P.reshape(-1, 1, 2))
        c0 = np.array([m["m10"], m["m01"]]) / max(m["m00"], 1e-6)
        mu = np.array([[m["mu20"], m["mu11"]], [m["mu11"], m["mu02"]]]) / max(m["m00"], 1e-6)
        evals, evecs = np.linalg.eigh(mu); v = evecs[:, int(np.argmax(evals))]
        if v @ nrm < 0: v = -v
        den = v[1] - a * v[0]
        sline = (a * c0[0] + b - c0[1]) / den if abs(den) > 1e-6 else 0.0
        d["axis_pt"] = c0 + sline * v; d["dir"] = v; d["ang"] = float(np.arctan2(float(v @ e), float(v @ nrm)))
    us = np.array([to_u(d["axis_pt"]) for d in det]); n = len(us)
    u_anc, t_anc = (to_u(anchor[0]), float(anchor[1])) if anchor is not None else (None, None)
    cxt = np.array([bb["cx"] for bb in blacks_t]); bmidi = np.array([bb["midi"] for bb in blacks_t])
    u_center = to_u([W / 2, H / 2])
    # 1. перебор сдвига и масштаба (аффинно), допуск растёт с удалением от якоря (перспектива, дисторсия)
    hyps = []; tracked = False
    if prev is not None and len(prev.get("blacks", [])) >= 4:
        PP = np.array([[x, y] for x, y, _ in prev["blacks"]], np.float64); pm = [int(m) for _, _, m in prev["blacks"]]
        ti_of = {int(m): i for i, m in enumerate(bmidi)}; wpx = float(prev["white_px"])
        # голова двинулась — все чёрные сдвинулись почти одинаково: голосуем за общий сдвиг (самый плотный кластер
        # разностей центров, окно 3×3 ячейки по 0,4 ширины белой), потом пары по близости с учётом сдвига
        C = np.array([d["c"] for d in det], np.float64)
        D = (C[:, None, :] - PP[None, :, :]).reshape(-1, 2); B = np.round(D / (0.4 * wpx)).astype(int)
        from collections import Counter
        cnt = Counter(map(tuple, B))
        def votes(b): return sum(cnt.get((b[0] + i, b[1] + j), 0) for i in (-1, 0, 1) for j in (-1, 0, 1))
        ranked = sorted(((b, votes(b)) for b in cnt), key=lambda kv: (-kv[1], abs(kv[0][0]) + abs(kv[0][1])))
        bb, nv = ranked[0]
        # соседний сдвиг на одну клавишу собирает почти столько же голосов, когда чёрных мало (руки закрыли ряд):
        # без запаса в 2 голоса над ближайшим конкурентом слежению не верим — лучше скан с подсказкой, чем уползти
        rival = max((v for b, v in ranked[1:] if abs(b[0] - bb[0]) > 1 or abs(b[1] - bb[1]) > 1), default=0)
        if nv >= 4 and nv >= rival + TRACK_MARGIN:
            sel = (np.abs(B[:, 0] - bb[0]) <= 1) & (np.abs(B[:, 1] - bb[1]) <= 1); shift = D[sel].mean(0)
            pairs = {}
            for di, d in enumerate(det):
                dd = np.linalg.norm(PP + shift - d["c"], axis=1); j = int(dd.argmin())
                if dd[j] < 0.5 * wpx and pm[j] in ti_of:
                    ti = ti_of[pm[j]]
                    if ti not in pairs or dd[j] < np.linalg.norm(PP[j] + shift - det[pairs[ti]]["c"]): pairs[ti] = di
            if len(pairs) >= 4: hyps = [((1e9, 0, 0), pairs, wpx)]; tracked = True
    gaps = np.diff(us); gaps = gaps[gaps > 3]
    if len(gaps) == 0: return None, "чёрные слиплись"
    base = float(np.median(gaps))
    anchors = sorted(set([n // 2, n // 4, 3 * n // 4]))
    for sc in (np.linspace(base / 2.2, base * 1.05, 36) if not tracked else []):
        for ti0 in range(len(cxt)):
            for i0 in anchors:
                pred = us[i0] + (cxt - cxt[ti0]) * sc
                inside = (pred > us[0] - 0.5 * sc) & (pred < us[-1] + 0.5 * sc)
                if inside.sum() < 3: continue
                dd = np.abs(us[:, None] - pred[None, :]); j = dd.argmin(1); dm = dd[np.arange(n), j]
                tol = 0.3 * sc + 0.05 * np.abs(us - us[i0])
                pairs = {}
                for i in np.where(dm < tol)[0]:
                    if j[i] not in pairs or dm[i] < dm[pairs[j[i]]]: pairs[j[i]] = i
                if len(pairs) < 4: continue
                missing = int(inside.sum()) - len(pairs)
                # найденные чёрные там, где у чертежа чёрных нет (границы B/C, E/F): сдвиг рисунка на клавишу
                # теряет мало пар, но даёт много таких «лишних»
                extra = n - len(pairs)
                mean_dm = float(np.mean([dm[i] for i in pairs.values()]))
                hint = -abs(int(bmidi[int(np.argmin(np.abs(pred - u_center)))]) - hint_midi) if hint_midi is not None else 0
                anc = -6.0 * abs((u_anc - us[i0]) / sc + cxt[ti0] - t_anc) if u_anc is not None else 0.0
                hyps.append(((len(pairs) - 0.5 * missing - 0.7 * extra + anc, -round(mean_dm / sc, 1), hint), pairs, sc))
    if not hyps: return None, "не удалось сопоставить чёрные с чертежом"
    hyps.sort(key=lambda h: h[0], reverse=True)
    # 2. уточнение: квадратичная u = f(t) по парам, пересбор пар, ещё раз
    best = None; seen = set()
    for _, pairs, sc in (hyps[:1] if tracked else hyps[:10]):
        key = tuple(sorted(pairs.items()))
        if key in seen: continue
        seen.add(key)
        cur = dict(pairs)
        for _ in range(3):
            t = np.array([cxt[ti] for ti in cur]); u = np.array([us[di] for di in cur.values()])
            deg = 2 if len(cur) >= 6 else 1
            f = np.polyfit(t, u, deg); pred = np.polyval(f, cxt); scale = np.abs(np.polyval(np.polyder(f), cxt))
            inside = (pred > us[0] - 0.5 * scale) & (pred < us[-1] + 0.5 * scale)
            dd = np.abs(us[:, None] - pred[None, :]); j = dd.argmin(1); dm = dd[np.arange(n), j]
            new = {}
            for i in np.where(dm < 0.3 * scale[j])[0]:
                if j[i] not in new or dm[i] < dm[new[j[i]]]: new[j[i]] = i
            if len(new) < 4: break
            cur = new
        if len(cur) < 4: continue
        t = np.array([cxt[ti] for ti in cur]); u = np.array([us[di] for di in cur.values()])
        f = np.polyfit(t, u, 2 if len(cur) >= 6 else 1); pred = np.polyval(f, cxt); scale = np.abs(np.polyval(np.polyder(f), cxt))
        inside = (pred > us[0] - 0.5 * scale) & (pred < us[-1] + 0.5 * scale)
        resid = np.array([abs(us[di] - pred[ti]) for ti, di in cur.items()]); rel = float(np.median(resid / scale[list(cur)]))
        missing = int(inside.sum()) - len(cur); extra = n - len(cur)
        ic = int(np.argmin(np.abs(pred - u_center)))
        hint = -abs(int(bmidi[ic]) - hint_midi) if hint_midi is not None else 0
        anc = 0.0
        if u_anc is not None:
            cc = np.array(f, dtype=np.float64).copy(); cc[-1] -= u_anc
            rts = np.roots(cc); rts = rts[np.abs(rts.imag) < 1e-6].real
            anc = -6.0 * float(np.min(np.abs(rts - t_anc))) if len(rts) else 0.0
        score = (len(cur) - 0.5 * missing - 0.7 * extra + hint_weight * hint + anc, hint, -rel)
        if best is None or score > best[0]: best = (score, f, cur, rel, ic)
    if best is None: return None, "не удалось сопоставить чёрные с чертежом"
    score, f, cur, rel, ic = best
    if rel > max_err_frac or len(cur) < 6:
        return None, f"привязка плохая: ошибка {rel:.2f} ширины белой, чёрных сопоставлено {len(cur)}"
    # 3. глубина и наклон краёв по сопоставленным чёрным
    idx = list(cur.values())
    tops = np.array([det[i]["top"] for i in idx], np.float64); bots = np.array([det[i]["bot"] for i in idx], np.float64)
    ab, bb_, _ = _robust_line(bots)                                          # прямая по низам чёрных
    def depth_black(u):
        # от точки оси до прямой низов вдоль nrm: p = on_axis(u) + s*nrm, y = ab x + bb_
        p = on_axis(u); s = (ab * p[0] + bb_ - p[1]) / (nrm[1] - ab * nrm[0]) if abs(nrm[1] - ab * nrm[0]) > 1e-6 else 0.0
        return float(s)
    # наклон краёв: направление (bot - top) каждой чёрной как угол к nrm, линейно по u
    ang = [det[i]["ang"] for i in idx]; uu = [us[i] for i in idx]
    uu = np.array(uu); ang = np.array(ang)
    ca = np.polyfit(uu, ang, 1) if len(uu) >= 4 else np.array([0.0, float(np.median(ang))])
    def edge_dir(u):
        th = float(np.polyval(ca, u)); return nrm * np.cos(th) + e * np.sin(th)
    keys = []
    for kk in whites_t + blacks_t:
        x0, _, x1, _ = kk["rect"]; u0, u1 = float(np.polyval(f, x0)), float(np.polyval(f, x1))
        if max(u0, u1) < -50 or min(u0, u1) > W + 50: continue
        d = depth_black((u0 + u1) / 2) * (WL / BL if kk["kind"] == "white" else 1.0)
        P0, P1 = on_axis(u0), on_axis(u1); P3, P2 = P0 + edge_dir(u0) * d, P1 + edge_dir(u1) * d
        P = np.array([P0, P1, P2, P3], np.float64)
        if P[:, 0].max() < 0 or P[:, 0].min() > W or P[:, 1].max() < 0 or P[:, 1].min() > H: continue
        keys.append({"kind": kk["kind"], "poly": [(float(x), float(y)) for x, y in P], "cx": float(P[:, 0].mean()),
                     "cy": float(P[:, 1].mean()), "midi": kk["midi"], "name": kk["name"], "conf": 1.0, "layout": "piano"})
    wpx = float(abs(np.polyval(np.polyder(f), cxt[ic])))
    info = {"blacks_matched": len(cur), "blacks_seen": len(det), "err_px": rel * wpx, "err_frac": rel, "match": "piano1d",
            "white_px": wpx, "f": [float(v) for v in f], "axis": [float(a), float(b)], "in_frame": len(keys),
            "profile": "piano", "center_midi": int(bmidi[ic]), "H": None, "tracked": tracked,
            "blacks": [[float(det[di]["c"][0]), float(det[di]["c"][1]), int(bmidi[ti])] for ti, di in cur.items()]}
    return keys, info


import os as _os
TRACK_MARGIN = int(_os.environ.get("SOM_TRACK_MARGIN", "2"))   # запас голосов слежения над соседним сдвигом (0 = как в прогоне 9/9 от 03.11 08:00)


def template_t(midi: int, profile: str = "piano"):
    """координата центра клавиши midi в чертеже (в ширинах белой): белая — середина, чёрная — cx; None, если нет такой"""
    whites, blacks = template(4, profile)
    for k in whites:
        if k["midi"] == midi: return (k["rect"][0] + k["rect"][2]) / 2
    for k in blacks:
        if k["midi"] == midi: return float(k["cx"])
    return None


def relabel(keys, delta: int):
    """Сдвиг меток на delta полутонов (замок октавы: delta кратен 12, геометрия не меняется)."""
    if not delta: return keys
    out = []
    for k in keys:
        m = k["midi"] + delta; out.append({**k, "midi": m, "name": NOTE_NAMES[m % 12] + str(m // 12 - 1)})
    return out
