#!/usr/bin/env python3
"""Souls of Muse · «Картонные клавиши»: нарисованная клавиатура → SAM 3.1 размечает клавиши один раз →
локальный трекер цветных меток на кончиках пальцев → нота → звук (встроенный синтезатор) и MIDI (виртуальный порт).

Источники кадров:
  --source webcam [--cam 0]                 веб-камера Mac
  --source screen --region X,Y,W,H          область экрана (например окно звонка WhatsApp)
  --source window --window WhatsApp         окно приложения по имени владельца (границы берутся через Quartz)
  --source video --file clip.mp4            файл, для отладки

Режимы:
  --calibrate      снять кадр, спросить SAM 3.1 «white key» и «black key», сохранить keys.json и keys_calib.jpg
  (без флага)      играть: трекер → ноты. Клавиши берутся из keys.json.
  --tracker marker цветные метки на пальцах (HSV, быстро)        --tracker sam  локальный SAM 3.1 (MLX) ищет пальцы сам
  --sam local|cloud  кем калибровать клавиши (локальный MLX или api.meta.ai);  --sam-res 336  вход SAM для пальцев
  --press strike|contact  удар (палец шёл вниз и остановился на клавише) | касание (кончик внутри клавиши)

Примеры:
  .venv/bin/python keys/air_keys.py --source webcam --calibrate --env-file ~/.hermes/profiles/jack/.env
  .venv/bin/python keys/air_keys.py --source webcam --marker green
  .venv/bin/python keys/air_keys.py --source window --window WhatsApp --marker pink
Клавиши: q — выход, c — перекалибровать по текущему кадру, m — показать маску меток, +/- — порог срабатывания.
"""
from __future__ import annotations

import argparse, asyncio, json, math, sys, threading, time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import importlib.util
sys.path.insert(0, str(Path(__file__).resolve().parent))
_spec = importlib.util.spec_from_file_location("samtest", ROOT / "sam_fret_test.py")
samtest = importlib.util.module_from_spec(_spec); sys.modules["samtest"] = samtest; _spec.loader.exec_module(samtest)

# ----------------------------------------------------------------------------- источники кадров

class Source:
    def read(self):  # -> frame BGR or None
        raise NotImplementedError
    def release(self): pass

class WebcamSource(Source):
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720):
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.cap.isOpened():
            raise SystemExit("веб-камера не открылась: дайте приложению доступ к камере (Системные настройки → Конфиденциальность → Камера)")
    def read(self):
        ok, f = self.cap.read(); return f if ok else None
    def release(self): self.cap.release()

class VideoSource(Source):
    def __init__(self, path: str, start: float = 0.0, step: int = 1):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened(): raise SystemExit(f"не открыть {path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0; self.step = max(1, step)
        if start > 0: self.cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)
    def read(self):
        for _ in range(self.step - 1): self.cap.grab()
        ok, f = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0); ok, f = self.cap.read()
        time.sleep(1.0 / self.fps)
        return f if ok else None
    def release(self): self.cap.release()

class ScreenSource(Source):
    """Захват области экрана через mss (нужно разрешение «Запись экрана» для приложения-хоста)."""
    def __init__(self, region: tuple[int, int, int, int] | None = None, window: str | None = None):
        import mss
        self.sct = mss.mss()
        self.window = window
        self.region = region
        if window and not region:
            self.region = self.find_window(window)
            waited = 0
            while not self.region and waited < 3600:         # ждём, пока появится окно звонка (до часа)
                if waited % 30 == 0: print(f"жду окно «{window}» на экране… ({waited} с)", flush=True)
                time.sleep(1); waited += 1
                self.region = self.find_window(window)
            if not self.region: raise SystemExit(f"окно «{window}» не найдено (оно должно быть открыто и видно)")
        if not self.region:
            m = self.sct.monitors[1]; self.region = (m["left"], m["top"], m["width"], m["height"])
        print(f"захват экрана: {self.region} окно «{self.win_name}» id={self.win_id}", flush=True)
    @staticmethod
    def find_window(owner_substr: str):
        """→ (x, y, w, h); в self.win_id кладём номер окна. Предпочитаем окно звонка («call» в имени), затем самое большое."""
        try:
            import Quartz
        except Exception:
            return None
        wins = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll | Quartz.kCGWindowListExcludeDesktopElements, Quartz.kCGNullWindowID)
        best = None
        for w in wins:
            if owner_substr.lower() in str(w.get("kCGWindowOwnerName", "")).lower():
                b = w.get("kCGWindowBounds", {}); name = str(w.get("kCGWindowName") or "")
                is_call = "call" in name.lower() or "звонок" in name.lower()
                if owner_substr.lower() == "whatsapp" and not is_call:
                    continue                                   # главное окно чатов нам не нужно — ждём именно окно звонка
                # окно звонка WhatsApp временами ужимается до миниатюры — это не конец звонка, держим его при любом размере
                if (b.get("Width", 0) < 480 or b.get("Height", 0) < 360) and not (is_call and b.get("Width", 0) >= 60):
                    continue
                score = (1, b["Width"] * b["Height"])
                if best is None or score > best[0]:
                    best = (score, (int(b["X"]), int(b["Y"]), int(b["Width"]), int(b["Height"])), int(w["kCGWindowNumber"]), name)
        if best:
            ScreenSource.win_id, ScreenSource.win_name = best[2], best[3]
            return best[1]
        return None
    win_id = None; win_name = ""; _vbox = None
    def _video_box(self, fr):
        """Область живого видео в окне звонка: сплошной не-чёрный блок столбцов/строк вокруг центра."""
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY); H, W = g.shape
        top, bot = 24, max(25, H - 56)
        gg = g[top:bot]
        cols = (gg > 6).mean(0) > 0.15; rows = (gg > 6).mean(1) > 0.15
        def run(mask, c):
            if c >= len(mask) or not mask[c]: return None
            a = b = c
            while a > 0 and mask[a - 1]: a -= 1
            while b < len(mask) - 1 and mask[b + 1]: b += 1
            return a, b
        cx = run(cols, W // 2); ry = run(rows, len(rows) // 2)
        if not cx or not ry or cx[1] - cx[0] < 120 or ry[1] - ry[0] < 120: return None
        return cx[0], ry[0] + top, cx[1] + 1, ry[1] + 1 + top
    def grab_window(self):
        import Quartz
        img = Quartz.CGWindowListCreateImage(Quartz.CGRectNull, Quartz.kCGWindowListOptionIncludingWindow, self.win_id,
                                             Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageNominalResolution)
        if img is None: return None
        W, H = Quartz.CGImageGetWidth(img), Quartz.CGImageGetHeight(img); bpr = Quartz.CGImageGetBytesPerRow(img)
        if W < 16 or H < 16: return None
        data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(img))
        return np.frombuffer(data, dtype=np.uint8).reshape(H, bpr // 4, 4)[:, :W, :3].copy()
    def read(self):
        if self.window:                                   # окно могло переехать или уйти со сцены — раз в 2 с сверяем границы
            now = time.perf_counter()
            if now - getattr(self, "_t_chk", 0) > 2.0:
                self._t_chk = now
                r = self.find_window(self.window)
                if r and r != self.region:
                    print(f"окно переехало: {self.region} → {r} «{self.win_name}»", flush=True); self.region = r
                elif not r:
                    if getattr(self, "_lost", 0) == 0: print("окно звонка пропало — жду его снова…", flush=True)
                    self._lost = getattr(self, "_lost", 0) + 1
                    self.win_id = None
                    while True:                                # ждём новый звонок, не выходя
                        time.sleep(1); r = self.find_window(self.window)
                        if r: self.region = r; self._lost = 0; self._vbox = None; print(f"окно звонка снова есть: {r} «{self.win_name}»", flush=True); break
            if self.win_id:
                fr = self.grab_window()                         # содержимое самого окна, даже если его закрыли другим окном
                if fr is not None:
                    if now - getattr(self, "_t_box", 0) > 2.0:
                        self._t_box = now; vb = self._video_box(fr)
                        if vb and vb != self._vbox: print(f"область видео в окне: {vb}", flush=True); self._vbox = vb
                    if self._vbox:
                        x0, y0, x1, y1 = self._vbox
                        if y1 <= fr.shape[0] and x1 <= fr.shape[1]: return fr[y0:y1, x0:x1]
                    return fr
        x, y, w, h = self.region
        img = np.array(self.sct.grab({"left": x, "top": y, "width": w, "height": h}))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def make_source(args) -> Source:
    if args.source == "webcam": return WebcamSource(args.cam)
    if args.source == "video": return VideoSource(args.file, args.video_start, args.video_step)
    if args.source == "screen":
        region = tuple(int(v) for v in args.region.split(",")) if args.region else None
        return ScreenSource(region=region)
    if args.source == "window": return ScreenSource(window=args.window)
    raise SystemExit("неизвестный источник")

# ----------------------------------------------------------------------------- калибровка клавиш через SAM 3.1

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
WHITE_PCS = [0, 2, 4, 5, 7, 9, 11]

def poly_from_mask(mask: np.ndarray):
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts: return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 80: return None
    eps = 0.01 * cv2.arcLength(c, True)
    return cv2.approxPolyDP(c, eps, True).reshape(-1, 2).tolist()

class LocalSam:
    """SAM 3.1 на MLX (mlx-community/sam3.1-bf16). Грузится лениво, ~1.5 с; один промпт при 336 px ≈ 0.1 с на M4 Max."""
    def __init__(self, model="mlx-community/sam3.1-bf16", threshold=0.45):
        from mlx_vlm.utils import load_model, get_model_path
        from mlx_vlm.models.sam3.generate import Sam3Predictor
        from mlx_vlm.models.sam3_1.processing_sam3_1 import Sam31Processor
        mp = get_model_path(model); self.model = load_model(mp)
        self.proc = Sam31Processor.from_pretrained(str(mp))
        self.pred = Sam3Predictor(self.model, self.proc, score_threshold=threshold)
    def masks(self, frame_bgr: np.ndarray, prompt: str, res: int, threshold: float | None = None):
        """→ список (score, mask uint8 в размере кадра)"""
        from PIL import Image
        H, W = frame_bgr.shape[:2]
        self.proc.image_size = res
        r = self.pred.predict(Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)), text_prompt=prompt, score_threshold=threshold)
        out = []
        for i in range(len(r.scores)):
            m = r.masks[i]
            m = (m > 0).astype(np.uint8)
            if m.shape != (H, W): m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
            out.append((float(r.scores[i]), m))
        return out

def fingertips_from_masks(masks, max_n: int = 10):
    """Кончик каждого пальца: конец главной оси маски, дальний от общего центра всех пальцев (ладони)."""
    items = []
    for score, m in masks:
        ys, xs = np.nonzero(m[::4, ::4])          # прореживание: SVD на 1/16 точек, кончик тот же с точностью до 4 px
        if len(xs) < 8: continue
        pts = np.stack([xs, ys], 1).astype(np.float32) * 4.0
        c = pts.mean(0)
        _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
        ax = vt[0]; proj = (pts - c) @ ax
        a, b = pts[proj.argmin()], pts[proj.argmax()]
        items.append((score, c, a, b))
    if not items: return []
    palm = np.mean([c for _, c, _, _ in items], axis=0)
    tips = []
    for score, c, a, b in sorted(items, key=lambda t: -t[0])[:max_n]:
        tip = a if np.linalg.norm(a - palm) > np.linalg.norm(b - palm) else b
        tips.append((float(tip[0]), float(tip[1])))
    return tips

def whites_from_blacks(bk, white_union, W, H):
    """Белые клавиши по геометрии чёрных: на нарисованной клавиатуре SAM берёт чёрные чисто, а белые часто сливает.
    Чёрные идут группами 2 (C# D#) и 3 (F# G# A#), шаг внутри группы = ширина белой w, между группами 2w.
    → прямоугольники белых между чёрными. Возвращает список клавиш kind=white (без нот) или None."""
    bk = sorted(bk, key=lambda k: k["cx"])
    if len(bk) < 4: return None
    xs = [k["cx"] for k in bk]; d = sorted(np.diff(xs))
    w = float(np.median(d[:max(1, int(len(d) * 0.6))]))
    if w < 4: return None
    groups = [[bk[0]]]
    for k in bk[1:]:
        (groups[-1].append(k) if k["cx"] - groups[-1][-1]["cx"] < 1.5 * w else groups.append([k]))
    sizes = [len(g) for g in groups]
    full = [i for i, n in enumerate(sizes) if n in (2, 3)]
    if not full: return None
    i0 = full[0]; t0 = sizes[i0]
    types = [t0 if (i - i0) % 2 == 0 else 5 - t0 for i in range(len(groups))]
    tops = [min(p[1] for p in k["poly"]) for k in bk]; bots = [max(p[1] for p in k["poly"]) for k in bk]
    y_top = float(np.median(tops)); bh = float(np.median(bots)) - y_top
    whites = []
    for gi, (g, t) in enumerate(zip(groups, types)):
        n = len(g)
        if n == t: a = g[0]["cx"]
        elif gi == 0: a = g[-1]["cx"] - w * (t - 1)          # обрезано слева: видны последние чёрные группы
        else: a = g[0]["cx"]                                  # обрезано справа: видны первые
        pcs = [0, 2, 4] if t == 2 else [5, 7, 9, 11]
        edges = [a - w + w * j for j in range(len(pcs) + 1)]
        for pc, x0, x1 in zip(pcs, edges[:-1], edges[1:]):
            x0c, x1c = max(0.0, x0), min(float(W), x1)
            if x1c - x0c < 0.4 * w: continue
            band = white_union[int(y_top):min(H, int(y_top + 4 * bh)), int(x0c):max(int(x0c) + 1, int(x1c))]
            ys = np.nonzero(band.any(axis=1))[0]
            y_bot = y_top + (float(np.percentile(ys, 95)) if len(ys) else 2.2 * bh)
            poly = [(x0c, y_top), (x1c, y_top), (x1c, y_bot), (x0c, y_bot)]
            whites.append({"kind": "white", "poly": poly, "cx": (x0c + x1c) / 2, "cy": (y_top + y_bot) / 2,
                           "area": (x1c - x0c) * (y_bot - y_top), "conf": 0.5, "pc": pc})
    # убрать дубли по x (соседние группы делят край), оставить по порядку
    whites.sort(key=lambda k: k["cx"]); out = []
    for k in whites:
        if out and abs(k["cx"] - out[-1]["cx"]) < 0.5 * w: continue
        out.append(k)
    return out if len(out) >= 3 else None

def keys_from_masks(whites, blacks, W, H, base_octave):
    """whites/blacks: списки (conf, mask HxW uint8) → список клавиш с полигонами и нотами."""
    keys = []
    def add(masks, kind):
        for conf, m in masks:
            if m.shape != (H, W): m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
            poly = poly_from_mask(m)
            if poly is None: continue
            xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
            keys.append({"kind": kind, "poly": poly, "cx": float(np.mean(xs)), "cy": float(np.mean(ys)),
                         "area": float(cv2.contourArea(np.array(poly, dtype=np.int32))), "conf": conf})
    add(whites, "white"); add(blacks, "black")
    # убрать дубли (SAM иногда отдаёт и клавишу, и всю клавиатуру): выкидываем маски, площадь которых > 4 медиан
    if keys:
        med = float(np.median([k["area"] for k in keys]))
        keys = [k for k in keys if k["area"] <= 4 * med]
    # отражение в лаке крышки даёт второй ряд клавиш выше настоящего: оставляем только ближний (нижний) ряд
    wk_all = sorted([k for k in keys if k["kind"] == "white"], key=lambda k: k["cy"])
    if len(wk_all) >= 6:
        kh = float(np.median([max(p[1] for p in k["poly"]) - min(p[1] for p in k["poly"]) for k in wk_all]))
        # режем белые на ряды по зазорам больше 0,8 высоты клавиши; берём самый нижний ряд, где хотя бы 5 белых
        rows = [[wk_all[0]]]
        for k in wk_all[1:]:
            if k["cy"] - rows[-1][-1]["cy"] <= 0.8 * kh: rows[-1].append(k)
            else: rows.append([k])
        good = [r for r in rows if len(r) >= 5]
        if len(rows) > 1 and good:
            r = good[-1]; lo, hi = r[0]["cy"] - 1.5 * kh, r[-1]["cy"] + 1.5 * kh
            before = len(keys)
            keys = [k for k in keys if lo <= k["cy"] <= hi]
            print(f"калибровка: рядов белых {len(rows)} ({[len(x) for x in rows]}), оставлен нижний: {before} → {len(keys)}", flush=True)
    # белые слиплись (тонкие линии между ними), а чёрных достаточно → строим белые по чёрным
    bk0 = [k for k in keys if k["kind"] == "black"]; wk0 = [k for k in keys if k["kind"] == "white"]
    derived = None
    wid = [max(p[0] for p in k["poly"]) - min(p[0] for p in k["poly"]) for k in wk0]
    merged = bool(wid) and max(wid) > 1.8 * float(np.median(wid))     # одна «белая» шириной в несколько — слиплись
    if len(bk0) >= 4:
        wu = np.zeros((H, W), np.uint8)
        for _, m in whites:
            if m.shape != (H, W): m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
            wu |= m
        derived = whites_from_blacks(bk0, wu, W, H)
        if derived and not (merged or len(wk0) < 0.85 * len(derived)):
            derived = None                                     # SAM нашёл белые сам и в нужном количестве — верим ему
        if derived:
            print(f"калибровка: белых найдено {len(wk0)} при {len(bk0)} чёрных — белые построены по чёрным: {len(derived)}", flush=True)
            keys = bk0 + derived
    # назначение нот: белые слева направо от C базовой октавы; чёрные — по положению между белыми
    wk = sorted([k for k in keys if k["kind"] == "white"], key=lambda k: k["cx"])
    bk = sorted([k for k in keys if k["kind"] == "black"], key=lambda k: k["cx"])
    if derived:
        octave = base_octave
        for i, k in enumerate(wk):
            if i > 0 and k["pc"] < wk[i - 1]["pc"]: octave += 1     # перешли через C (даже если сама C не видна)
            k["midi"] = 12 * (octave + 1) + k["pc"]
    else:
        for i, k in enumerate(wk):
            octave = base_octave + i // 7
            k["midi"] = 12 * (octave + 1) + WHITE_PCS[i % 7]
    for k in bk:
        left = [w for w in wk if w["cx"] < k["cx"]]
        if left:
            w = left[-1]; pc = w["midi"] % 12
            k["midi"] = w["midi"] + 1 if pc in (0, 2, 5, 7, 9) else w["midi"]  # после E и B чёрных нет
        else:
            k["midi"] = None
    keys = [k for k in wk + bk if k.get("midi") is not None and k["midi"] <= 108]  # выше C8 на рояле нет
    for k in keys:
        k["name"] = NOTE_NAMES[k["midi"] % 12] + str(k["midi"] // 12 - 1)
    return keys

def calibrate_local(frame, sam: "LocalSam", base_octave: int = 4, res: int = 1008):
    H, W = frame.shape[:2]
    t0 = time.perf_counter()
    whites = sam.masks(frame, "white piano key", res, 0.3); blacks = sam.masks(frame, "black piano key", res, 0.3)
    return keys_from_masks(whites, blacks, W, H, base_octave), time.perf_counter() - t0

async def calibrate_async(frame: np.ndarray, env_file: str | None, base_octave: int = 4, max_side: int = 1280):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=samtest.load_key(env_file))
    H, W = frame.shape[:2]
    url = samtest.jpeg_data_url(frame, max_side=max_side)
    scale = min(1.0, max_side / max(H, W)); Hs, Ws = int(H * scale), int(W * scale)
    t0 = time.perf_counter()
    whites, blacks = await asyncio.gather(
        samtest.segment_image(client, url, "white piano key", (Hs, Ws)),
        samtest.segment_image(client, url, "black piano key", (Hs, Ws)),
    )
    dt = time.perf_counter() - t0
    def up(ms):
        return [(conf, cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST) if scale < 1.0 else m) for _, m, conf in ms]
    keys = keys_from_masks(up(whites), up(blacks), W, H, base_octave)
    return keys, dt

def calibrate(frame, env_file, base_octave):
    return asyncio.run(calibrate_async(frame, env_file, base_octave))

def draw_keys(img, keys, active: set[int], expect: int | None = None):
    for k in keys:
        pts = np.array(k["poly"], dtype=np.int32)
        col = (90, 200, 255) if k["kind"] == "white" else (255, 160, 60)
        if k["midi"] in active:
            cv2.fillPoly(img, [pts], (60, 220, 120))
        elif expect is not None and k["midi"] == expect:
            ov = img.copy(); cv2.fillPoly(ov, [pts], (0, 220, 255)); cv2.addWeighted(ov, 0.45, img, 0.55, 0, img); col = (0, 220, 255)
        cv2.polylines(img, [pts], True, col, 2)
        cv2.putText(img, k["name"], (int(k["cx"]) - 14, int(k["cy"])), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, k["name"], (int(k["cx"]) - 14, int(k["cy"])), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

# ----------------------------------------------------------------------------- трекер меток

MARKERS = {   # диапазоны HSV (OpenCV: H 0..180)
    "green":  [((40, 80, 70), (85, 255, 255))],
    "pink":   [((140, 70, 90), (175, 255, 255))],
    "blue":   [((95, 90, 70), (130, 255, 255))],
    "yellow": [((20, 90, 110), (38, 255, 255))],
    "orange": [((5, 120, 120), (20, 255, 255))],
    "red":    [((0, 120, 90), (8, 255, 255)), ((170, 120, 90), (180, 255, 255))],
}

def find_markers(frame, marker: str, min_area: int = 40, max_n: int = 6):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = None
    for lo, hi in MARKERS[marker]:
        m = cv2.inRange(hsv, np.array(lo), np.array(hi))
        mask = m if mask is None else cv2.bitwise_or(mask, m)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a < min_area: continue
        M = cv2.moments(c)
        blobs.append((a, M["m10"] / M["m00"], M["m01"] / M["m00"]))
    blobs.sort(reverse=True)
    return [(x, y) for _, x, y in blobs[:max_n]], mask

@dataclass
class Track:
    x: float; y: float
    vy: float = 0.0
    key: int | None = None
    pressed: bool = False
    last_seen: float = 0.0
    dip: tuple | None = None          # сустав перед кончиком (ось пальца) — для касания по тени
    touch: int = 0                    # подряд кадров «касается» (по тени)
    untouch: int = 0                  # подряд кадров «не касается»
    shadow: str = "none"              # последний ответ детектора тени

def key_at(keys, x, y):
    # чёрные проверяем первыми: они лежат поверх белых
    for k in sorted(keys, key=lambda k: 0 if k["kind"] == "black" else 1):
        if cv2.pointPolygonTest(np.array(k["poly"], dtype=np.int32), (float(x), float(y)), False) >= 0:
            return k["midi"]
    return None

# ----------------------------------------------------------------------------- звук и MIDI

class Synth:
    """Полифонический синтезатор: затухающий тон с обертонами, без внешних зависимостей кроме sounddevice."""
    def __init__(self, sr: int = 44100, volume: float = 0.35, device: str | None = None, instrument: str | None = None):
        import sounddevice as sd
        self.gm = None
        if instrument:                                        # штатный GM-синтезатор macOS: саксофон, труба, орган… (см. gm_synth.py)
            from gm_synth import GMSynth, GM_NAMES
            prog = int(instrument) if instrument.isdigit() else {v: k for k, v in GM_NAMES.items()}.get(instrument.lower().replace("sax", "alto sax") if instrument.lower() == "sax" else instrument.lower())
            if prog is None: raise SystemExit(f"инструмент «{instrument}» не знаю; есть: {', '.join(GM_NAMES.values())} или номер GM 0..127")
            self.gm = GMSynth(prog, volume=min(1.0, volume * 2.5), device=device)   # --audio-out направляет и GM (иначе он идёт в системный выход — может быть Bluetooth)
            print(f"инструмент: {GM_NAMES.get(prog, prog)} (GM {prog}) → {self.gm.device or 'системный вывод звука'}", flush=True)
        dev = None
        if device and not self.gm:                            # подстрока имени устройства вывода, например "Teams" → виртуальный кабель в звонок
            cands = [i for i, d in enumerate(sd.query_devices()) if device.lower() in d["name"].lower() and d["max_output_channels"] > 0]
            if not cands: raise SystemExit(f"аудиоустройство «{device}» не найдено: " + ", ".join(d["name"] for d in sd.query_devices()))
            dev = cands[0]; sr = int(sd.query_devices(dev)["default_samplerate"]) or sr
            print(f"звук → «{sd.query_devices(dev)['name']}» @ {sr} Гц", flush=True)
        self.sr = sr; self.volume = volume
        self.voices: dict[int, dict] = {}
        self.lock = threading.Lock()
        self.stream = None
        if not self.gm:                                       # свой тон-генератор — только без GM (раньше при --audio-out он дублировал GM вторым тембром)
            self.stream = sd.OutputStream(device=dev, samplerate=sr, channels=1, dtype="float32", blocksize=256, callback=self._cb, latency="low")
            self.stream.start()
        self.midi_out = None
        try:
            import rtmidi
            self.midi_out = rtmidi.MidiOut(); self.midi_out.open_virtual_port("Souls of Muse Air Keys")
            print("MIDI: виртуальный порт «Souls of Muse Air Keys» открыт (виден в GarageBand/Logic)")
        except Exception as e:
            print("MIDI недоступен:", e)
    def note_on(self, midi: int, vel: int = 100):
        if self.gm: self.gm.note_on(midi, vel)
        if self.stream:
            with self.lock:
                self.voices[midi] = {"f": 440.0 * 2 ** ((midi - 69) / 12), "t": 0, "amp": vel / 127, "rel": False, "phase": 0.0}
        if self.midi_out: self.midi_out.send_message([0x90, midi, vel])
    def note_off(self, midi: int):
        if self.gm: self.gm.note_off(midi)
        if self.stream:
            with self.lock:
                v = self.voices.get(midi)
                if v: v["rel"] = True
        if self.midi_out: self.midi_out.send_message([0x80, midi, 0])
    def set_instrument(self, name: str):
        if not self.gm: return None
        from gm_synth import GM_NAMES
        prog = int(name) if name.isdigit() else {v: k for k, v in GM_NAMES.items()}.get("alto sax" if name == "sax" else name)
        return self.gm.program(prog) if prog is not None else None
    def _cb(self, out, frames, time_info, status):
        buf = np.zeros(frames, dtype=np.float32)
        t = np.arange(frames, dtype=np.float32) / self.sr
        with self.lock:
            dead = []
            for midi, v in self.voices.items():
                env_t = (v["t"] + np.arange(frames)) / self.sr
                env = np.exp(-env_t * 1.6)                      # естественное затухание
                if v["rel"]:
                    env *= np.exp(-(np.arange(frames)) / (0.06 * self.sr))  # быстрый спад после отпускания
                ph = v["phase"] + 2 * np.pi * v["f"] * t
                wave = np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph) + 0.08 * np.sin(4 * ph)
                buf += (v["amp"] * env * wave * 0.5).astype(np.float32)
                v["phase"] = float((ph[-1] + 2 * np.pi * v["f"] / self.sr) % (2 * np.pi))
                v["t"] += frames
                if v["rel"] and env[-1] < 1e-3 or v["t"] > self.sr * 6: dead.append(midi)
                if v["rel"]: v["amp"] *= float(np.exp(-frames / (0.06 * self.sr)))
            for d in dead: self.voices.pop(d, None)
        out[:, 0] = np.tanh(buf * self.volume * 2.5)

# ----------------------------------------------------------------------------- главный цикл

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["webcam", "screen", "window", "video"], default="webcam")
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--file", default=None)
    ap.add_argument("--region", default=None)
    ap.add_argument("--window", default="WhatsApp")
    ap.add_argument("--keys", default=str(Path(__file__).parent / "keys.json"))
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--base-octave", type=int, default=4)
    ap.add_argument("--marker", choices=list(MARKERS), default="green")
    ap.add_argument("--tracker", choices=["marker", "sam", "hands"], default="marker", help="hands = Apple Vision, поза рук, ~5 мс/кадр")
    ap.add_argument("--sam", choices=["local", "cloud"], default="local", help="кем калибровать клавиши")
    ap.add_argument("--sam-res", type=int, default=336, help="вход SAM при поиске пальцев (336 ≈ 0.1 с, 504 ≈ 0.2 с)")
    ap.add_argument("--sam-prompt", default="finger")
    ap.add_argument("--press", choices=["strike", "contact", "shadow", "score"], default="strike",
                    help="shadow: касание по тени от низкого бокового света (keys/touch_shadow.py); где тени не видно — как strike")
    ap.add_argument("--score", default=None, help="режим score: партитура солиста из ensemble/ (fur_elise): ожидаемая клавиша подсвечена, стенд подтверждает «палец лёг на неё» и звучит её нота; первая нота партитуры замыкает октаву")
    ap.add_argument("--tip-anchor", action="store_true", help="piano: пока подтверждённая нота держится, привязка держится за кончик пальца (по умолчанию выключено: кончик на краю клавиши сбивает скан на полклавиши)")
    ap.add_argument("--anchor", action="store_true", help="piano: якорь над клавишами (шаблон таблички) против дрейфа; по умолчанию выключен — с ракурса очков цепляется за соседнюю октаву")
    ap.add_argument("--dino-thr", type=float, default=0.15, help="режим score: порог DINO «вид клавиши изменился» (0 = только кончик внутри клавиши); на картонке настоящие нажатия давали 0,19–0,31")
    ap.add_argument("--video-start", type=float, default=0.0, help="--source video: с какой секунды")
    ap.add_argument("--max-side", type=int, default=1408, help="кадр крупнее этого по длинной стороне уменьшать (0 = не трогать)")
    ap.add_argument("--video-step", type=int, default=1, help="--source video: брать каждый N-й кадр")
    ap.add_argument("--layout", choices=["auto", "cardboard", "piano"], default="auto", help="cardboard = картонка Камилы как известное устройство: чертёж 24+17, привязка по чёрным, ноты из чертежа; piano = настоящая клавиатура 52+36 от A0")
    ap.add_argument("--hint", type=int, default=None, help="piano: midi ноты примерно в центре кадра (октаву по чёрным не отличить; по умолчанию 64 = E4)")
    ap.add_argument("--log", action="store_true", help="печатать ноты в stdout")
    ap.add_argument("--record", default=None, help="писать события ON в json [[t, midi], ...] — первый прогон солиста для learn_score")
    ap.add_argument("--auto", action="store_true", help="ждать, пока SAM увидит клавиши в кадре, калиброваться самому, при потере клавиш снова ждать")
    ap.add_argument("--min-keys", type=int, default=5, help="сколько белых клавиш нужно видеть, чтобы считать, что клавиатура в кадре")
    ap.add_argument("--snap-every", type=float, default=0.0, help="в headless: писать оверлей в out/live/latest.jpg каждые N с")
    ap.add_argument("--settle", type=float, default=0.0, help="секунд подождать перед калибровкой (навести очки на клавиши)")
    ap.add_argument("--press-vy", type=float, default=2.0, help="мин. скорость вниз (px/кадр) перед остановкой = нажатие")
    ap.add_argument("--side-cam", type=int, default=None, help="второй взгляд: номер веб-камеры (iPhone как Continuity Camera) с торца картонки, объектив у стола")
    ap.add_argument("--side-file", default=None, help="второй взгляд из видеофайла (проба без камеры)")
    ap.add_argument("--side-end", default="treble", choices=["treble", "bass"], help="с какого торца стоит боковая камера: treble (справа, ближняя кисть = правая) или bass")
    ap.add_argument("--side-rotate", type=int, default=0, help="поворот бокового кадра: 0, 90, -90, 180")
    ap.add_argument("--side-mode", default="sam", choices=["sam", "pose"], help="боковой вид: sam (маски пальцев и картонки, касание = палец на полосе картонки) или pose (ключевые точки Vision, высота кончика)")
    ap.add_argument("--side-gap", type=float, default=0.02, help="«палец опущен»: ниже второго кончика кисти не меньше чем на долю высоты кадра")
    ap.add_argument("--no-free-sound", action="store_true", help="режим score: НЕ озвучивать клавиши мимо партитуры (по умолчанию любая тронутая клавиша звучит)")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--audio-out", default=None, help="устройство вывода звука (подстрока имени), напр. Teams — виртуальный кабель, который WhatsApp берёт как микрофон")
    ap.add_argument("--volume", type=float, default=0.35)
    ap.add_argument("--ensemble", default=None, help="следящий ансамбль по партитуре: fur_elise (бас + подклад идут за темпом солиста)")
    ap.add_argument("--ensemble-latency", type=float, default=0.15, help="секунд от нажатия до события зрения (обработка кадра + подтверждение); ансамбль вычитает")
    ap.add_argument("--ensemble-free", action="store_true", help="ансамбль без метра: аккорд и бас меняются по нотам солиста (свободная игра, рубато)")
    ap.add_argument("--voices", default=None, help="голоса ансамбля GM: bass=33,pad=29,pluck=107 (30 жёсткий перегруз, 108 калимба, 114 стил-драм, 106 сямисэн)")
    ap.add_argument("--instrument", default=None, help="звук через GM-синтезатор macOS: sax, piano, trumpet, flute, organ, guitar, violin… или номер GM 0..127")
    ap.add_argument("--headless", action="store_true", help="без окна (для тестов)")
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()

    src = make_source(args)
    side = None
    if args.side_cam is not None or args.side_file:
        if args.side_mode == "sam":
            from side_sam import SideSam
            side = SideSam(cam=args.side_cam, file=args.side_file, end=args.side_end, rotate=args.side_rotate)
        else:
            from side_view import SideView
            side = SideView(cam=args.side_cam, file=args.side_file, end=args.side_end, rotate=args.side_rotate, gap=args.side_gap)
        if not args.side_file: side.start()   # живая камера крутится в своём потоке
        print(f"боковой вид: {'файл ' + args.side_file if args.side_file else 'камера ' + str(args.side_cam)}, торец {args.side_end}", flush=True)
    sam = LocalSam() if (args.tracker == "sam" or args.sam == "local") else None
    hands = None
    if args.tracker == "hands":
        from hand_pose import VisionHands
        hands = VisionHands(max_hands=2, min_conf=0.3)
    ptrack = None; last_polys = [[]]; tip_anchor = [None]   # (xy кончика, координата ноты в чертеже) пока подтверждённая нота держится
    if args.layout == "piano":
        from score_lock import PianoTracker
        ptrack = PianoTracker(hint=args.hint if args.hint is not None else 64, use_anchor=args.anchor)   # скан один раз, дальше слежение по чёрным
    def cardboard_fit(frame, res=1008):
        import cardboard
        H_, W_ = frame.shape[:2]; polys = []
        for conf, m in sam.masks(frame, "black piano key", res, 0.3):
            if m.shape != (H_, W_): m = cv2.resize(m, (W_, H_), interpolation=cv2.INTER_NEAREST)
            pp = poly_from_mask(m)
            if pp is not None: polys.append(pp)
        last_polys[0] = polys
        if ptrack is not None:
            r = ptrack.step(polys, W_, H_, frame, anchor=tip_anchor[0])
            if ptrack.anchor_log: print(ptrack.anchor_log, flush=True); ptrack.anchor_log = None
            return r
        return cardboard.fit(polys, W_, H_, args.base_octave, gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                             profile=args.layout, hint_midi=args.hint)
    def do_calibrate(frame):
        if args.layout in ("cardboard", "piano"):
            t0 = time.perf_counter(); ks, info = cardboard_fit(frame)
            if ks is None:
                print(f"чертёж не лёг: {info}", flush=True); return [], time.perf_counter() - t0
            print(f"чертёж лёг: чёрных сопоставлено {info['blacks_matched']}, ошибка {info['err_px']:.1f} px, клавиш в кадре {info['in_frame']}", flush=True)
            return ks, time.perf_counter() - t0
        if args.sam == "local":
            return calibrate_local(frame, sam, args.base_octave)
        return calibrate(frame, args.env_file, args.base_octave)
    keys = []
    kp = Path(args.keys)
    if args.auto:
        keys = []; print("авторежим: жду, пока в кадре появятся клавиши…", flush=True)
    elif args.calibrate or not kp.exists():
        frame = None
        if args.settle > 0:
            t_end = time.perf_counter() + args.settle
            while time.perf_counter() < t_end:
                frame = src.read(); left = int(t_end - time.perf_counter())
                print(f"наведи очки на клавиши, калибровка через {left} с…", end="\r", flush=True)
                if not args.headless and frame is not None:
                    v = frame.copy(); cv2.putText(v, f"calibration in {left}s - look at the keys", (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                    cv2.imshow("Souls of Muse · Air Keys", v); cv2.waitKey(1)
            print()
        for _ in range(10):
            frame = src.read()
        if frame is None: raise SystemExit("нет кадра для калибровки")
        cv2.imwrite(str(kp.with_name("keys_preview.jpg")), frame); print("кадр перед калибровкой:", kp.with_name("keys_preview.jpg"))
        print(f"калибровка ({args.sam}): спрашиваю SAM 3.1 про белые и чёрные клавиши…")
        keys, dt = do_calibrate(frame)
        print(f"клавиш найдено: {len(keys)} за {dt:.1f} с → {[k['name'] for k in keys]}")
        kp.write_text(json.dumps(keys, ensure_ascii=False, indent=1))
        vis = frame.copy(); draw_keys(vis, keys, set()); cv2.imwrite(str(kp.with_name("keys_calib.jpg")), vis)
        print("сохранено:", kp, kp.with_name("keys_calib.jpg"))
        if args.calibrate and args.headless:
            return
    else:
        keys = json.loads(kp.read_text())
        print(f"клавиши из {kp}: {len(keys)}")

    sys.path.insert(0, str(Path(__file__).parent))
    synth = None if args.no_sound else Synth(device=args.audio_out, volume=args.volume, instrument=args.instrument)
    score_notes = []; dino = None; key_crop = None
    if args.press == "score":
        if not args.score: raise SystemExit("--press score требует --score <партитура из ensemble/>, напр. fur_elise")
        sys.path.insert(0, str(ROOT / "ensemble")); import importlib
        score_notes = [m for _, m, _ in importlib.import_module(args.score).MELODY]
        if args.dino_thr > 0:
            from dino_probe import Dino; from press_dino import key_crop
            dino = Dino(size=112)
        print(f"по партитуре {args.score}: {len(score_notes)} нот солиста, первая {NOTE_NAMES[score_notes[0] % 12]}{score_notes[0] // 12 - 1}; DINO порог {args.dino_thr}", flush=True)
    follower = None
    if args.ensemble:
        sys.path.insert(0, str(ROOT / "ensemble")); import importlib
        from follower import Follower
        score = importlib.import_module(args.ensemble)
        from player import EnsemblePlayer
        voices = {kv.split("=")[0]: (int(kv.split("=")[1]) if kv.split("=")[1].isdigit() else kv.split("=")[1]) for kv in args.voices.split(",")} if args.voices else None
        follower = Follower(score, None if args.no_sound else EnsemblePlayer(voices), meter=not args.ensemble_free, log=lambda m: print("[ансамбль]", m, flush=True),
                            input_latency=args.ensemble_latency)   # нота солиста приходит после SAM и подтверждения: постоянный сдвиг, ансамбль его вычитает
        follower.start(); print(f"ансамбль: партитура {args.ensemble} ({score.KEY}), жду солиста…", flush=True)
    tracks: list[Track] = []
    show_mask = False
    shadow_det = None
    if args.press == "shadow":
        from touch_shadow import ShadowTouch
        shadow_det = ShadowTouch(); print("касание по тени: лампа низко СБОКУ от картонки (слева или справа), не из-за спины", flush=True)
    def finger_px(keys):
        wk = [max(p[0] for p in k["poly"]) - min(p[0] for p in k["poly"]) for k in keys if k["kind"] == "white"]
        return 0.6 * float(np.median(wk)) if wk else 16.0            # палец ≈ 0,6 ширины белой клавиши (18 мм против 30)
    active: set[int] = set()
    n = 0; t_last = time.perf_counter(); fps = 0.0
    while True:
        frame = src.read()
        if frame is None: break
        if args.max_side and max(frame.shape[:2]) > args.max_side:
            sc_ = args.max_side / max(frame.shape[:2]); frame = cv2.resize(frame, None, fx=sc_, fy=sc_, interpolation=cv2.INTER_AREA)
        n += 1
        now = time.perf_counter()
        if args.auto:
            # WAIT: раз в секунду смотрим, есть ли клавиши; две проверки подряд → калибровка. PLAY: раз в 3 с проверяем, что клавиши ещё видны.
            st = getattr(main, "_auto", {"seen": 0, "miss": 0, "t": 0.0})
            if not keys and now - st["t"] > 1.0:
                st["t"] = now
                wm = sam.masks(frame, "black piano key" if args.layout in ("cardboard", "piano") else "white piano key", 504, 0.3); nk = len(wm)
                H_, W_ = frame.shape[:2]; ok = False; why = ""
                if nk >= args.min_keys:
                    u = np.zeros((H_, W_), np.uint8)
                    for _, m in wm: u |= m
                    ys, xs = np.nonzero(u); span = (xs.max() - xs.min()) / W_; cxy = (xs.mean() / W_, ys.mean() / H_)
                    prev = st.get("prev")
                    stable = prev is not None and abs(prev[0] - nk) <= max(3, 0.25 * nk) and math.hypot(prev[1][0] - cxy[0], prev[1][1] - cxy[1]) < 0.04
                    st["prev"] = (nk, cxy)
                    if span < 0.35: why = f"клавиатура мелкая ({span:.0%} ширины кадра) — подойди/наклонись"
                    elif not stable: why = "кадр ещё движется — замри на 2 с"
                    else: ok = True
                else:
                    st["prev"] = None
                st["seen"] = st["seen"] + 1 if ok else 0
                print(f"жду клавиши: белых видно {nk}" + (f"; {why}" if why else ""), flush=True)
                if st["seen"] >= 2:
                    keys, dt = do_calibrate(frame)
                    if len([k for k in keys if k["kind"] == "white"]) < args.min_keys:
                        print(f"калибровка дала {len(keys)} клавиш — мало, жду дальше", flush=True); keys = []; st["seen"] = 0; continue
                    kp.write_text(json.dumps(keys, ensure_ascii=False, indent=1))
                    vis = frame.copy(); draw_keys(vis, keys, set()); cv2.imwrite(str(kp.with_name("keys_calib.jpg")), vis)
                    cv2.imwrite(str(kp.with_name("keys_preview.jpg")), frame)
                    print(f"КЛАВИШИ В КАДРЕ: {len(keys)} за {dt:.1f} с → {[k['name'] for k in keys]}", flush=True)
                    st["seen"] = 0; st["miss"] = 0; st["cal_cxy"] = cxy; st["shape"] = frame.shape[:2]; st["drift"] = 0
                    if synth: synth.note_on(84, 70); time.sleep(0.12); synth.note_off(84)   # короткий сигнал «готов»
            elif keys and args.layout in ("cardboard", "piano") and now - st["t"] > (0.35 if ptrack is not None else 0.7):
                # картонка: чертёж привязываем заново каждые 0,7 с, с руками в кадре тоже (хватает части чёрных)
                st["t"] = now
                ks, info = cardboard_fit(frame, res=504)
                if ks:
                    keys = ks; st["miss"] = 0; st["nfit"] = st.get("nfit", 0) + 1
                    if shadow_det is not None:
                        import cardboard
                        if info.get("H") is not None: shadow_det.set_layout(info["H"], [b["rect"] for b in cardboard.template(args.base_octave, args.layout)[1]])
                    if st["nfit"] % 15 == 1:
                        print(f"чертёж: чёрных {info['blacks_matched']}, ошибка {info['err_px']:.1f} px, клавиш {info['in_frame']}", flush=True)
                else:
                    st["miss"] += 1
                    if st["miss"] >= 6:
                        print(f"клавиатура пропала из кадра ({info}) — жду снова", flush=True); keys = []
                        for tr in tracks:
                            if tr.pressed and synth: synth.note_off(tr.key)
                        tracks = []; active = set()
            elif keys and now - st["t"] > (1.5 if not tracks else 3.0):
                st["t"] = now
                wm = sam.masks(frame, "white piano key", 336, 0.3); nk = len(wm)
                st["miss"] = st["miss"] + 1 if nk < max(2, args.min_keys // 2) else 0
                if st["miss"] >= 3:
                    print("клавиши пропали из кадра — жду снова", flush=True); keys = []
                    for tr in tracks:
                        if tr.pressed and synth: synth.note_off(tr.key)
                    tracks = []; active = set()
                elif nk >= args.min_keys and not tracks:
                    # карта клавиш привязана к кадру: если голова повернулась (клавиатура уехала) или окно сменило размер,
                    # а рук в кадре нет — переразмечаем сами, две проверки подряд
                    H_, W_ = frame.shape[:2]; u = np.zeros((H_, W_), np.uint8)
                    for _, m in wm: u |= m
                    ys, xs = np.nonzero(u); cxy = (xs.mean() / W_, ys.mean() / H_)
                    ref = st.get("cal_cxy"); moved = ref is not None and math.hypot(cxy[0] - ref[0], cxy[1] - ref[1]) > 0.06
                    resized = st.get("shape") is not None and st["shape"] != frame.shape[:2]
                    st["drift"] = st.get("drift", 0) + 1 if (moved or resized) else 0
                    if st["drift"] >= 2:
                        why = "окно сменило размер" if resized else f"клавиатура уехала на {math.hypot(cxy[0]-ref[0], cxy[1]-ref[1]):.0%} кадра"
                        new_keys, dt = do_calibrate(frame)
                        if len([k for k in new_keys if k["kind"] == "white"]) >= args.min_keys:
                            keys = new_keys; kp.write_text(json.dumps(keys, ensure_ascii=False, indent=1))
                            vis = frame.copy(); draw_keys(vis, keys, set()); cv2.imwrite(str(kp.with_name("keys_calib.jpg")), vis)
                            print(f"ПЕРЕРАЗМЕТКА ({why}): {len(keys)} клавиш за {dt:.1f} с → {[k['name'] for k in keys]}", flush=True)
                            st["cal_cxy"] = cxy; st["shape"] = frame.shape[:2]; st["drift"] = 0
                            if synth: synth.note_on(84, 70); time.sleep(0.12); synth.note_off(84)
                        else:
                            print(f"переразметка ({why}) дала {len(new_keys)} клавиш — оставляю прежнюю карту", flush=True); st["drift"] = 0
            main._auto = st
            if not keys:
                if args.snap_every and now - getattr(main, "_t_snap", 0) > args.snap_every:
                    main._t_snap = now; vis = frame.copy()
                    cv2.putText(vis, "waiting for piano keys...", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    d = ROOT / "out" / "live"; d.mkdir(parents=True, exist_ok=True); cv2.imwrite(str(d / "latest.jpg"), vis)
                time.sleep(0.05); continue
        if args.tracker == "sam":
            # ведение пальцев: захват по слову каждый кадр, дорожки по перекрытию масок; кончик берём только у дорожки,
            # дубли одной кисти отсеиваются по IoU
            ftrk = getattr(main, "_ftrk", None)
            if ftrk is None:
                from mask_track import MaskTracker
                ftrk = main._ftrk = MaskTracker(match_iou=0.1, max_missed=1, dedupe_iou=0.4, k=10)
            # при 2 кадрах/с из очков рука за кадр уходит дальше своей ширины — возраст дорожки не требуем, берём отсев дублей и номера
            _tr = ftrk.update(sam.masks(frame, args.sam_prompt, args.sam_res))
            pts = fingertips_from_masks([(t["score"], t["mask"]) for t in _tr]); mask = None
        elif args.tracker == "hands":
            # кончики пальцев + смещение запястья той же руки: скорость считаем относительно кисти,
            # иначе при ударе одним пальцем «нажимают» и соседние, а качание головы в очках даёт ложные удары
            pts = []; wr = getattr(main, "_wrist", {}); main._wrist = wr; _hl = []
            for hd in hands.detect(frame):
                ch = hd["chirality"]; wp = hd["points"].get("VNHLKWRI")
                dyw = 0.0
                if wp is not None:
                    if ch in wr: dyw = wp[1] - wr[ch]
                    wr[ch] = wp[1]
                dipk = {"thumb": "VNHLKTIP", "index": "VNHLKIDIP", "middle": "VNHLKMDIP", "ring": "VNHLKRDIP", "little": "VNHLKPDIP"}
                for short, (x, y, c) in hd["tips"].items():
                    dp = hd["points"].get(dipk.get(short, ""))
                    pts.append((x, y, dyw, (dp[0], dp[1]) if dp is not None else None))
                if hd["tips"]: _hl.append((float(np.mean([t[0] for t in hd["tips"].values()])), ch, [(x, y, short) for short, (x, y, c) in hd["tips"].items()]))
            # кончики с именем пальца и ролью кисти для склейки с боковым видом; роль по положению: левее в кадре очков = левая
            _hl.sort(key=lambda h: h[0]); main._named = []
            for i_, (mx_, ch_, tl_) in enumerate(_hl):
                role_ = ("left" if i_ == 0 else "right") if len(_hl) > 1 else (ch_ if ch_ in ("left", "right") else "right")
                main._named += [(x, y, role_, nm) for x, y, nm in tl_]
            mask = None
        else:
            pts, mask = find_markers(frame, args.marker)
        now = time.perf_counter()
        # скорость считаем в пикселях на 0,1 с, чтобы пороги --press-vy не зависели от частоты кадров трекера
        dt_scale = 0.1 / max(now - getattr(main, "_t_prev_frame", now - 0.1), 1e-3); main._t_prev_frame = now
        # сопоставление меток с треками по ближайшему соседу
        new_tracks = []
        for pt in pts:
            x, y = pt[0], pt[1]; dyw = pt[2] if len(pt) > 2 else 0.0; dip = pt[3] if len(pt) > 3 else None
            best = None
            for tr in tracks:
                d = math.hypot(tr.x - x, tr.y - y)
                if d < 60 and (best is None or d < best[0]): best = (d, tr)
            if best:
                tr = best[1]; tracks.remove(tr)
                tr.vy = 0.6 * tr.vy + 0.4 * ((y - tr.y) - dyw) * dt_scale; tr.x, tr.y = x, y
            else:
                tr = Track(x, y)
            tr.last_seen = now; tr.dip = dip
            new_tracks.append(tr)
        # отпускаем ноты у пропавших меток
        for tr in tracks:
            if tr.pressed and synth: synth.note_off(tr.key)
            if tr.pressed: active.discard(tr.key)
        tracks = new_tracks
        # логика нажатия: метка внутри клавиши и движение вниз остановилось → нажатие; вышла из клавиши или пошла вверх → отпускание
        for tr in tracks:
            k = key_at(keys, tr.x, tr.y)
            peak = getattr(tr, "_peak_vy", 0.0)
            # нажатие: метка над клавишей, перед этим шла вниз быстрее порога и теперь остановилась
            last_on = getattr(main, "_last_on", {}); main._last_on = last_on
            strike_ok = abs(tr.vy) < 1.0 and peak >= args.press_vy
            if shadow_det is not None and k is not None:
                # тень смотрим только у кончиков над клавишами; без чертежа чёрные клавиши исключаем по их полигонам
                if shadow_det.Hinv is None and getattr(shadow_det, "_keys_id", None) != id(keys):
                    shadow_det.blacks_poly = [np.array(kk["poly"], dtype=np.int32) for kk in keys if kk["kind"] == "black"]; shadow_det._keys_id = id(keys)
                dip = tr.dip or (tr.x, tr.y + 40)
                r = shadow_det.classify(frame, (tr.x, tr.y), dip, finger_px(keys)); tr.shadow = r["state"]
                if r["state"] == "touch": tr.touch += 1; tr.untouch = 0
                elif r["state"] in ("hover", "unsure"): tr.untouch += 1; tr.touch = 0
                else: tr.touch = 0                                    # тени нет — решает удар
            elif shadow_det is not None:
                tr.touch = 0; tr.untouch += 1; tr.shadow = "none"
            if args.press == "shadow":
                press_ok = tr.touch >= 2 or (tr.shadow == "none" and strike_ok)
            else:
                press_ok = args.press == "contact" or (args.press != "score" and strike_ok)
            hit = (k is not None and not tr.pressed and now - last_on.get(k, 0.0) > 0.25 and press_ok)
            if hit:
                tr.pressed = True; tr.key = k; active.add(k); last_on[k] = now
                if synth: synth.note_on(k, int(min(127, max(112, 60 + 20 * peak))))
                if follower: follower.observe(now, k)
                if args.record:
                    rec = getattr(main, "_rec", None)
                    if rec is None: rec = main._rec = []
                    rec.append((now, int(k))); json.dump(rec, open(args.record, "w"))
                if args.log: print(f"{now:.3f} f{n} ON  {NOTE_NAMES[k % 12]}{k // 12 - 1} at ({tr.x:.0f},{tr.y:.0f})" + (f" тень={tr.shadow}" if shadow_det else ""), flush=True)
                tr._peak_vy = 0.0
            elif tr.pressed and now - last_on.get(tr.key, 0.0) > 0.15 and (k != tr.key or (args.press == "strike" and tr.vy < -1.5)
                                                                           or (args.press == "shadow" and (tr.untouch >= 3 or (tr.shadow == "none" and tr.vy < -1.5)))):
                if synth: synth.note_off(tr.key)
                if args.log: print(f"{now:.3f} f{n} OFF {NOTE_NAMES[tr.key % 12]}{tr.key // 12 - 1}", flush=True)
                active.discard(tr.key); tr.pressed = False; tr.key = None
            if not tr.pressed:
                tr._peak_vy = max(getattr(tr, "_peak_vy", 0.0) * 0.9, tr.vy)
        if args.press == "score" and keys:
            sc = getattr(main, "_score", None)
            if sc is None: sc = main._score = {"i": 0, "on": 0, "last": None, "held": None, "t_held": 0.0, "locked": ptrack is None, "calm": {}, "base": {}, "t_hint": 0.0}
            H_, W_ = frame.shape[:2]; delta = ptrack.delta if ptrack is not None else 0
            raw = lambda m: m - delta
            crop = lambda k: key_crop(frame, k["poly"], (64, 160) if k["kind"] == "white" else (40, 120))
            tips_xy = [(p[0], p[1]) for p in pts]
            if dino is not None and n % 3 == 0:
                # спокойный вид клавиш копим, пока рядом нет кончиков (до 12 векторов на клавишу)
                wk = finger_px(keys) / 0.6
                def near(k): return any(abs(x - k["cx"]) < 1.5 * wk and abs(y - k["cy"]) < 1.2 * (max(yy for _, yy in k["poly"]) - min(yy for _, yy in k["poly"])) for x, y in tips_xy)
                todo = [k for k in keys if 0 <= k["cx"] < W_ and 0 <= k["cy"] < H_ and len(sc["calm"].get(raw(k["midi"]), [])) < 12 and not near(k)]
                if todo:
                    for k, v in zip(todo, dino.embed([crop(k) for k in todo])):
                        L = sc["calm"].setdefault(raw(k["midi"]), []); L.append(v)
                        if len(L) >= 3: b = np.median(np.stack(L), 0); sc["base"][raw(k["midi"])] = b / (np.linalg.norm(b) + 1e-9)
            def dino_score(k):
                b = sc["base"].get(raw(k["midi"]))
                if dino is None or b is None: return None
                return 1.0 - float(dino.embed([crop(k)])[0] @ b)
            under = {}
            for x, y in tips_xy:
                m = key_at(keys, x, y)
                if m is not None: under.setdefault(m, (x, y))
            byid = {k["midi"]: k for k in keys}
            target = None
            exp_now = score_notes[sc["i"]] if sc["i"] < len(score_notes) else None
            side_r = (side.step() if side.is_file else side.current()) if side is not None else None
            down_keys = set(); side_hands = side_r["hands"] if side_r else 0
            if side_r and "pressed_ranks" in side_r:
                # SAM-режим: ранг нажатого пальца от ближнего торца → тот же ранг среди кончиков над клавишами (очки)
                over = [(x_, y_, m_) for x_, y_ in tips_xy for m_ in [key_at(keys, x_, y_)] if m_ is not None]
                over.sort(key=lambda t: -t[0] if args.side_end == "treble" else t[0])   # ближний к камере торец первым
                nS, nG = side_r["n"], len(over)
                for r_ in side_r["pressed_ranks"]:
                    if nG == 0: break
                    j_ = r_ if nS == nG else int(round(r_ * (nG - 1) / max(1, nS - 1)))
                    if 0 <= j_ < nG: down_keys.add(over[j_][2])
            elif side_r:
                down_set = {(r_, f_) for r_, f_, _ in side_r["down"]}
                for x_, y_, r_, f_ in getattr(main, "_named", []):
                    if (r_, f_) in down_set:
                        m_ = key_at(keys, x_, y_)
                        if m_ is not None: down_keys.add(m_)
                if n % 2 == 0:
                    d_ = ROOT / "out" / "live"; d_.mkdir(parents=True, exist_ok=True); cv2.imwrite(str(d_ / "side.jpg"), side_r["vis"])
            if sc["i"] < len(score_notes):
                exp = score_notes[sc["i"]]
                if not sc["locked"]:
                    # замок: первое нажатие — клавиша под кончиком, чей вид изменился сильнее всех; она и есть первая нота партитуры
                    cands = {m: dino_score(byid[m]) for m in under}
                    strong = {m: v for m, v in cands.items() if v is not None and v > args.dino_thr}
                    if under and not strong and (dino is None or all(v is None for v in cands.values())):
                        # спокойного вида клавиш ещё нет (руки в кадре с самого начала): берём самый дальний кончик —
                        # нажимающий палец вытянут к чёрным дальше остальных (y меньше), а не первый попавшийся
                        m_top = min(under, key=lambda m: under[m][1]); strong = {m_top: 1.0}
                    if strong:
                        m0 = max(strong, key=strong.get); sc["on"] = sc["on"] + 1 if sc["last"] == m0 else 1; sc["last"] = m0
                        if sc["on"] >= 2:
                            ok, was = ptrack.lock(last_polys[0], W_, H_, under[m0], exp, frame); keys = ptrack.keys; sc["locked"] = True
                            print(f"{now:.3f} f{n} ЗАМОК: палец на {NOTE_NAMES[was % 12]}{was // 12 - 1}, ожидалась {NOTE_NAMES[exp % 12]}{exp // 12 - 1} → сдвиг меток {ptrack.delta:+d}" + ("" if ok else " (не октава, взял ближайшую)"), flush=True)
                            target = exp
                    else: sc["on"] = 0; sc["last"] = None
                elif sc["held"] is None:
                    if exp in under:
                        v = dino_score(byid[exp]) if exp in byid else None
                        # кончик должен замереть на клавише (нажатие), а не проезжать над ней (наведение): сдвиг между
                        # кадрами меньше 0,3 ширины белой; иначе рука, пролетающая над картонкой, «подтверждает» ноты
                        # движение кончика считаем ОТНОСИТЕЛЬНО клавиши (кадр очков едет вместе с головой), не в кадре
                        kx_ = byid[exp]; p_ = (under[exp][0] - kx_["cx"], under[exp][1] - kx_["cy"]); pv = sc.get("tip_prev"); wk_ = finger_px(keys) / 0.6
                        still = pv is not None and abs(p_[0] - pv[0]) + abs(p_[1] - pv[1]) < 0.6 * wk_   # дрожание Vision ~0,3 ширины, пролёт руки ≥ 1 ширина за кадр
                        sc["tip_prev"] = p_
                        sc["on"] = sc["on"] + 1 if ((v is None or v > args.dino_thr) and (still or sc["on"] == 0)) else 0
                        if args.log and dino is not None:   # диагностика порога: что DINO видит на ожидаемой клавише под кончиком
                            print(f"{now:.3f} f{n} кончик на ожидаемой {NOTE_NAMES[exp % 12]}{exp // 12 - 1}: DINO " + (f"{v:.2f}" if v is not None else "нет базы (клавиша всё время под пальцами)") + f", порог {args.dino_thr}, {'замер' if still else 'движется'}, подряд {sc['on']}", flush=True)
                    else: sc["on"] = 0; sc["tip_prev"] = None
                    if side_hands > 0: sc["on"] = 2 if exp in down_keys else 0       # второй взгляд: палец на ожидаемой должен быть опущен
                    if sc["on"] >= 2: target = exp; sc["tip_conf"] = under.get(exp)   # кончик проверенно внутри ожидаемой
                    elif ptrack is not None and under and now - sc.get("t_conf", now) > 2.5:
                        # застряли: ожидаемая не подтверждается, а какая-то клавиша под пальцем явно нажата (DINO) —
                        # метки уползли; перезамыкаем на неё как на ожидаемую ноту
                        cands = {m: dino_score(byid[m]) for m in under}; strong = {m: v for m, v in cands.items() if v is not None and v > args.dino_thr}
                        if strong:
                            m0 = max(strong, key=strong.get); sc["re"] = sc.get("re", 0) + 1 if sc.get("re_last") == m0 else 1; sc["re_last"] = m0
                            if sc["re"] >= 2:
                                sc["re"] = 0
                                if (exp - m0) % 12 == 0:
                                    # метки уехали ровно на октавы — перезамыкаем и подтверждаем; иначе не угадываем
                                    ok, was = ptrack.lock(last_polys[0], W_, H_, under[m0], exp, frame); keys = ptrack.keys
                                    print(f"{now:.3f} f{n} ПЕРЕЗАМОК: нажата {NOTE_NAMES[was % 12]}{was // 12 - 1}, ожидалась {NOTE_NAMES[exp % 12]}{exp // 12 - 1} → сдвиг меток {ptrack.delta:+d}", flush=True)
                                    target = exp
                                elif args.log: print(f"{now:.3f} f{n} застряли: нажата {NOTE_NAMES[m0 % 12]}{m0 // 12 - 1}, жду {NOTE_NAMES[exp % 12]}{exp // 12 - 1} (не октава, не перезамыкаю)", flush=True)
                        else: sc["re"] = 0
                    elif under and args.log and now - sc["t_hint"] > 1.0:
                        sc["t_hint"] = now; m = next(iter(under))
                        print(f"{now:.3f} f{n} палец на {NOTE_NAMES[m % 12]}{m // 12 - 1}, жду {NOTE_NAMES[exp % 12]}{exp // 12 - 1}", flush=True)
                if target is not None:
                    sc["held"] = exp; sc["t_held"] = now; sc["t_conf"] = now; sc["i"] += 1; sc["on"] = 0; active.add(exp)
                    tc = sc.pop("tip_conf", None)
                    if args.tip_anchor and ptrack is not None and tc is not None:    # не при замке: там палец мог лежать не на ожидаемой
                        import cardboard as _cb
                        t_ = _cb.template_t(exp - ptrack.delta)
                        if t_ is not None: tip_anchor[0] = (tc, t_)   # пока нота держится, привязка держится за палец
                    if synth: synth.note_on(exp, 100)
                    if follower: follower.observe(now, exp)
                    print(f"{now:.3f} f{n} ПОДТВЕРЖДЕНО {NOTE_NAMES[exp % 12]}{exp // 12 - 1} ({sc['i']}/{len(score_notes)})", flush=True)
            # виртуальная MIDI-клавиатура не молчит: кончик замер на ЛЮБОЙ клавише два кадра подряд — звучит её нота,
            # даже если это не ожидаемая по партитуре и даже если привязка ошиблась (Айдар, съёмка 03.11). Партитура остаётся
            # подсветкой и счётчиком; повторно та же клавиша звучит только после того, как палец её покинул.
            if not args.no_free_sound and side is not None:
                fr = sc.setdefault("free", {}); fh = sc.setdefault("free_held", [])
                for m_ in list(fr):
                    if m_ not in down_keys: del fr[m_]
                fired = 0
                for m_ in sorted(down_keys):
                    if m_ in fr or fired >= 1: continue
                    fr[m_] = {"done": True}; fired += 1
                    if m_ == exp_now and (target is not None or sc["held"] == m_): continue
                    if synth: synth.note_on(m_, 100)
                    fh.append((m_, now)); active.add(m_)
                    print(f"{now:.3f} f{n} ЗВУК {NOTE_NAMES[m_ % 12]}{m_ // 12 - 1} (опущен палец, боковой вид)", flush=True)
                for m_, t_ in list(fh):
                    if now - t_ > 0.5:
                        if synth and sc["held"] != m_: synth.note_off(m_)
                        active.discard(m_); fh.remove((m_, t_))
            elif not args.no_free_sound:
                fr = sc.setdefault("free", {}); fh = sc.setdefault("free_held", [])
                for m_ in list(fr):
                    if m_ not in under: del fr[m_]
                wk_ = finger_px(keys) / 0.6
                fired = 0   # не больше одной новой ноты за кадр: посадка всей кисти не должна давать кластер
                for m_, (x_, y_) in sorted(under.items(), key=lambda kv: -kv[1][1]):   # сначала самый ближний к играющему кончик
                    k_ = byid.get(m_)
                    if k_ is None: continue
                    p_ = (x_ - k_["cx"], y_ - k_["cy"]); st = fr.get(m_)
                    if st is None: fr[m_] = {"p": p_, "on": 1, "done": False}; continue
                    still = abs(p_[0] - st["p"][0]) + abs(p_[1] - st["p"][1]) < 0.6 * wk_
                    st["on"] = st["on"] + 1 if still else 1; st["p"] = p_
                    if st["on"] >= 2 and not st["done"]:
                        st["done"] = True            # все пальцы, легшие в этот кадр, дальше считаются лежащими
                        if fired >= 1: continue      # звучит только один; новая нота — когда палец оторвался и лёг снова
                        fired += 1
                        if m_ == exp_now and (target is not None or sc["held"] == m_): continue   # уже прозвучала по партитуре
                        if synth: synth.note_on(m_, 100)
                        fh.append((m_, now)); active.add(m_)
                        print(f"{now:.3f} f{n} ЗВУК {NOTE_NAMES[m_ % 12]}{m_ // 12 - 1} (клавиатура, не по партитуре)", flush=True)
                for m_, t_ in list(fh):
                    if now - t_ > 0.5:
                        if synth and sc["held"] != m_: synth.note_off(m_)
                        active.discard(m_); fh.remove((m_, t_))
            # все ноты одинаковые по силе (100) и длительности (0,5 с), от нажатия не зависят — Камиле так проще ориентироваться
            if sc["held"] is not None and now - sc["t_held"] > 0.5:
                if synth: synth.note_off(sc["held"])
                active.discard(sc["held"]); sc["held"] = None; tip_anchor[0] = None
            main._expect = score_notes[sc["i"]] if sc["i"] < len(score_notes) else None
            if target is not None: sc.setdefault("events", []).append([round(now, 2), int(exp), n])
            if n % 2 == 0 or target is not None:
                # состояние для страницы приложения (app/server.py → /keys)
                st_path = ROOT / "out" / "live" / "status.json"; st_path.parent.mkdir(parents=True, exist_ok=True)
                nm_ = lambda m: NOTE_NAMES[m % 12] + str(m // 12 - 1)
                json.dump({"t": now, "frame": n, "fps": round(fps, 1), "layout": args.layout, "keys": len(keys), "tips": len(pts),
                           "score": args.score, "i": sc["i"], "total": len(score_notes), "notes": [nm_(m) for m in score_notes],
                           "expected": nm_(main._expect) if main._expect is not None else None, "held": nm_(sc["held"]) if sc["held"] is not None else None,
                           "locked": sc["locked"], "delta": ptrack.delta if ptrack is not None else 0,
                           "events": [[t_, nm_(m_), f_] for t_, m_, f_ in sc.get("events", [])[-12:]],
                           "under": [nm_(m) for m in under][:6],
                           "side": ({"hands": side_hands, "down": ([[r_, f_] for r_, f_, _ in side_r["down"]] if "down" in side_r else [["ранг", r_] for r_ in side_r["pressed_ranks"]]), "n": side_r.get("n"), "keys": [nm_(m) for m in sorted(down_keys)]} if side_r else None)}, open(st_path, "w"), ensure_ascii=False)
        if n % 10 == 0:
            fps = 10 / (now - t_last); t_last = now
            if args.headless and args.log and n % 50 == 0:
                print(f"{now:.3f} f{n} status {fps:4.1f} fps tips={len(pts)} keys={len(keys)} tracker={args.tracker}", flush=True)
        if args.headless and args.snap_every and now - getattr(main, "_t_snap", 0) > args.snap_every:
            main._t_snap = now
            vis = frame.copy(); draw_keys(vis, keys, active, getattr(main, '_expect', None))
            for tr in tracks: cv2.circle(vis, (int(tr.x), int(tr.y)), 9, (0, 0, 255) if tr.pressed else (255, 255, 255), 2)
            cv2.putText(vis, f"{fps:4.1f} fps keys={len(keys)} active={sorted(active)}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            d = ROOT / "out" / "live"; d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / "latest.jpg"), vis); cv2.imwrite(str(d / f"f{n:06d}.jpg"), vis)
        if not args.headless:
            vis = frame.copy()
            draw_keys(vis, keys, active, getattr(main, "_expect", None))
            for tr in tracks:
                cv2.circle(vis, (int(tr.x), int(tr.y)), 9, (0, 0, 255) if tr.pressed else (255, 255, 255), 2)
            cv2.putText(vis, f"{fps:4.1f} fps  tracker={args.tracker}  keys={len(keys)}  active={sorted(active)}", (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.imshow("Souls of Muse · Air Keys", vis)
            if show_mask and mask is not None: cv2.imshow("marker mask", mask)
            kcode = cv2.waitKey(1) & 0xFF
            if kcode == ord("q"): break
            if kcode == ord("m"): show_mask = not show_mask
            if kcode == ord("c"):
                keys, dt = do_calibrate(frame); kp.write_text(json.dumps(keys, ensure_ascii=False, indent=1))
                print(f"перекалибровка: {len(keys)} клавиш за {dt:.1f} с")
            if kcode == ord("+"): args.press_vy += 0.5; print("press_vy", args.press_vy)
            if kcode == ord("-"): args.press_vy = max(0.5, args.press_vy - 0.5); print("press_vy", args.press_vy)
        if args.headless and synth and (ROOT / "out" / "live" / "INSTRUMENT").exists():
            name = (ROOT / "out" / "live" / "INSTRUMENT").read_text().strip(); (ROOT / "out" / "live" / "INSTRUMENT").unlink()
            print(f"инструмент → {synth.set_instrument(name) or 'не знаю ' + name}", flush=True)
        if args.headless and (ROOT / "out" / "live" / "RECALIBRATE").exists():
            (ROOT / "out" / "live" / "RECALIBRATE").unlink()
            keys, dt = do_calibrate(frame); kp.write_text(json.dumps(keys, ensure_ascii=False, indent=1))
            vis = frame.copy(); draw_keys(vis, keys, set()); cv2.imwrite(str(kp.with_name("keys_calib.jpg")), vis)
            print(f"перекалибровка: {len(keys)} клавиш за {dt:.1f} с → {[k['name'] for k in keys]}", flush=True)
            if args.auto:   # опорная точка для авто-переразметки
                _wm = sam.masks(frame, "white piano key", 336, 0.3); _u = np.zeros(frame.shape[:2], np.uint8)
                for _, _m in _wm: _u |= _m
                if _u.any():
                    _ys, _xs = np.nonzero(_u); main._auto["cal_cxy"] = (_xs.mean() / frame.shape[1], _ys.mean() / frame.shape[0])
                main._auto["shape"] = frame.shape[:2]; main._auto["drift"] = 0
        if args.max_frames and n >= args.max_frames: break
    if follower: follower.stop()
    src.release()
    if not args.headless: cv2.destroyAllWindows()
    print(f"кадров {n}, последний fps {fps:.1f}")

if __name__ == "__main__":
    main()
