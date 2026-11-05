#!/usr/bin/env python3
"""Souls of Muse · Ray-Ban Meta · стенд фазы 1.

Берёт видео (снятое очками), выбирает кадры, просит SAM 3.1 (Meta Model API)
обвести гриф и пальцы, и для каждого пальца считает две цифры:

  * contact_angle  — угол (0..90°) между последней частью пальца и продольной
                     осью грифа. Около 90° = палец стоит («квадрат»),
                     заметно меньше = палец лёг («треугольник»).
  * corners        — число вершин упрощённого контура пальца. Арка даёт больше
                     вершин, чем прямой клин.

Результат: размеченные кадры в out/<clip>/frame_XXXX.jpg, таблица out/<clip>/metrics.csv
и общий контактный лист out/<clip>/sheet.jpg. Это проверка осуществимости, не продукт.

Запуск:
  MODEL_API_KEY=... .venv/bin/python sam_fret_test.py clips/правильно.mp4 clips/неправильно.mp4
Опции: --fps 1 --max-frames 20 --prompts "guitar fretboard" "finger" --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# ----------------------------------------------------------------------------
# Геометрия (чистые функции, без API)
# ----------------------------------------------------------------------------

def principal_axis(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Центр, единичный вектор главной оси и длина проекции маски вдоль неё."""
    ys, xs = np.nonzero(mask)
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    center = pts.mean(axis=0)
    cov = np.cov((pts - center).T)
    vals, vecs = np.linalg.eigh(cov)
    axis = vecs[:, np.argmax(vals)]
    proj = (pts - center) @ axis
    return center, axis, float(proj.max() - proj.min())


def angle_between(a: np.ndarray, b: np.ndarray) -> float:
    """Острый угол между двумя направлениями, градусы 0..90."""
    cosv = abs(float(np.dot(a, b)) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosv))))


@dataclass
class FingerMetrics:
    object_id: str
    contact_angle: float | None
    corners: int
    contact_xy: tuple[int, int] | None
    verdict: str
    overlap: float | None = None      # доля пикселей пальца на полосе грифа (лежащий палец → большая)
    elongation: float | None = None   # доля ширины грифа, перекрытая пальцем (лежащий палец → ближе к 1)


def finger_metrics(finger: np.ndarray, neck: np.ndarray | None, object_id: str,
                   ok_deg: float = 60.0) -> FingerMetrics:
    """Считает угол последней фаланги к оси грифа и число углов контура."""
    if finger.sum() < 50:
        return FingerMetrics(object_id, None, 0, None, "мало пикселей")

    # Контур и число вершин упрощённого многоугольника
    contours, _ = cv2.findContours(finger.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnt = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(cnt, True)
    poly = cv2.approxPolyDP(cnt, 0.04 * peri, True)
    corners = int(len(poly))

    if neck is None or neck.sum() < 50:
        return FingerMetrics(object_id, None, corners, None, "нет маски грифа")

    center, axis, length = principal_axis(finger)
    _, neck_axis, _ = principal_axis(neck)

    # Точка контакта: пиксель пальца, ближайший к грифу
    dist = cv2.distanceTransform((neck == 0).astype(np.uint8), cv2.DIST_L2, 3)
    ys, xs = np.nonzero(finger)
    i = int(np.argmin(dist[ys, xs]))
    contact = np.array([xs[i], ys[i]], dtype=np.float64)

    # Направление последней фаланги: от середины пальца к его концу у грифа.
    # Доля длины считается от конца, ближайшего к точке контакта.
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    proj = (pts - center) @ axis
    sign = 1.0 if (contact - center) @ axis >= 0 else -1.0
    frac = (sign * proj - (sign * proj).min()) / (length + 1e-9)   # 0 = дальний конец, 1 = конец у грифа
    tip = pts[frac >= 0.75]
    mid = pts[(frac >= 0.45) & (frac < 0.75)]
    if len(tip) < 10 or len(mid) < 10:
        tip, mid = pts[frac >= 0.5], pts[frac < 0.5]
    distal_axis = tip.mean(axis=0) - mid.mean(axis=0)
    if np.linalg.norm(distal_axis) < 1e-6:
        distal_axis = axis

    ang = angle_between(distal_axis, neck_axis)

    # Признаки для ракурса от первого лица: лежащий палец длинный и лежит поверх струн,
    # согнутый — короткий и касается грифа в одной точке.
    # Маска грифа у SAM вырезана там, где лежат пальцы, поэтому берём выпуклую оболочку грифа:
    # она заполняет «дыры» от пальцев и даёт полосу грифа целиком.
    ncnts, _ = cv2.findContours(neck.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull_mask = np.zeros_like(neck, dtype=np.uint8)
    if ncnts:
        hull = cv2.convexHull(np.vstack(ncnts))
        cv2.fillConvexPoly(hull_mask, hull, 1)
    inside = np.logical_and(finger > 0, hull_mask > 0)
    overlap = float(inside.sum()) / float(max(1, finger.sum()))          # доля пальца, лежащая на полосе грифа
    # Доля ширины грифа, которую палец перекрывает (проекция на ось поперёк грифа)
    cross = np.array([-neck_axis[1], neck_axis[0]])
    hy, hx = np.nonzero(hull_mask)
    hproj = np.stack([hx, hy], axis=1).astype(np.float64) @ cross
    neck_w = float(np.percentile(hproj, 97) - np.percentile(hproj, 3)) if len(hproj) else 0.0
    iy, ix = np.nonzero(inside)
    if len(ix) >= 10 and neck_w > 1:
        fproj = np.stack([ix, iy], axis=1).astype(np.float64) @ cross
        elongation = float((np.percentile(fproj, 97) - np.percentile(fproj, 3)) / neck_w)  # здесь: покрытие ширины грифа
    else:
        elongation = 0.0

    verdict = "стоит ✓" if ang >= ok_deg else "лёг ✗"
    return FingerMetrics(object_id, round(ang, 1), corners, (int(contact[0]), int(contact[1])), verdict,
                         overlap=round(overlap, 3), elongation=round(elongation, 2))


# ----------------------------------------------------------------------------
# SAM 3.1 через Meta Model API
# ----------------------------------------------------------------------------

def jpeg_data_url(frame_bgr: np.ndarray, max_side: int = 896) -> str:
    h, w = frame_bgr.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        frame_bgr = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("jpeg encode failed")
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


async def segment_image(client, data_url: str, prompt: str, shape: tuple[int, int]) -> list[tuple[str, np.ndarray, float | None]]:
    """Возвращает [(object_id, full-frame mask uint8, confidence)] для одного промпта."""
    from meta_sam_parser import (decode_mask_to_raster, image_segmentation_format,
                                 parse_responses_stream, SegmentationMaskRecord)

    stream = await client.responses.create(
        model="sam-3.1",
        stream=True,
        metadata={"include_confidence": "true", "mask_encoding": "one_bit"},
        input=[{
            "type": "message", "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": data_url},
            ],
        }],
    )

    parsed = parse_responses_stream(stream, image_segmentation_format())
    try:
        result = await parsed.final_result()
    finally:
        try:
            await stream.close()
        except Exception:
            pass
    H, W = shape
    out = []
    for rec in result.records:
        if not isinstance(rec, SegmentationMaskRecord):
            continue
        raster = np.frombuffer(decode_mask_to_raster(rec.mask), dtype=np.uint8)
        raster = raster.reshape(rec.mask.height, rec.mask.width)
        b = rec.bounds
        x0, y0, x1, y1 = int(round(b.left)), int(round(b.top)), int(round(b.right)), int(round(b.bottom))
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, max(x0 + 1, x1)), min(H, max(y0 + 1, y1))
        patch = cv2.resize(raster, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
        full = np.zeros((H, W), dtype=np.uint8)
        full[y0:y1, x0:x1] = patch
        out.append((rec.object_id, full, rec.confidence))
    return out


# ----------------------------------------------------------------------------
# Кадры, отрисовка, отчёт
# ----------------------------------------------------------------------------

def sample_frames(video: Path, fps: float, max_frames: int, max_side: int):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"не открыть видео: {video}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(src_fps / fps)))
    idx, taken = 0, 0
    while taken < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            h, w = frame.shape[:2]
            scale = min(1.0, max_side / max(h, w))
            if scale < 1.0:
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            yield idx, idx / src_fps, frame
            taken += 1
        idx += 1
    cap.release()


COLORS = [(60, 200, 60), (60, 60, 230), (230, 160, 40), (200, 60, 200), (40, 200, 230), (120, 120, 240)]


def draw(frame: np.ndarray, neck: np.ndarray | None, fingers: list[tuple[str, np.ndarray, float | None]],
         metrics: list[FingerMetrics]) -> np.ndarray:
    vis = frame.copy()
    if neck is not None:
        vis[neck > 0] = (0.55 * vis[neck > 0] + 0.45 * np.array([200, 200, 60])).astype(np.uint8)
    for k, ((oid, m, conf), fm) in enumerate(zip(fingers, metrics)):
        col = COLORS[k % len(COLORS)]
        vis[m > 0] = (0.5 * vis[m > 0] + 0.5 * np.array(col)).astype(np.uint8)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, col, 2)
        if fm.contact_xy:
            cv2.circle(vis, fm.contact_xy, 6, (255, 255, 255), 2)
        label = f"#{oid} {fm.contact_angle if fm.contact_angle is not None else '-'}° c{fm.corners} {fm.verdict}"
        ys, xs = np.nonzero(m)
        if len(xs):
            org = (int(xs.min()), max(15, int(ys.min()) - 6))
            cv2.putText(vis, label, org, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(vis, label, org, cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    return vis


def contact_sheet(images: list[np.ndarray], cols: int = 4, thumb_w: int = 480) -> np.ndarray | None:
    if not images:
        return None
    thumbs = []
    for im in images:
        h, w = im.shape[:2]
        thumbs.append(cv2.resize(im, (thumb_w, int(h * thumb_w / w))))
    th = max(t.shape[0] for t in thumbs)
    rows = math.ceil(len(thumbs) / cols)
    sheet = np.full((rows * th, cols * thumb_w, 3), 30, dtype=np.uint8)
    for i, t in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet[r * th:r * th + t.shape[0], c * thumb_w:c * thumb_w + t.shape[1]] = t
    return sheet


async def process_clip(client, video: Path, out_dir: Path, args) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, vis_frames = [], []
    neck_prompt, finger_prompt = args.prompts[0], args.prompts[1]
    for idx, t, frame in sample_frames(video, args.fps, args.max_frames, args.max_side):
        H, W = frame.shape[:2]
        if args.dry_run:
            neck, fingers = None, []
        else:
            url = jpeg_data_url(frame, max_side=args.max_side)
            necks = await segment_image(client, url, neck_prompt, (H, W))
            neck = max(necks, key=lambda x: int(x[1].sum()))[1] if necks else None
            fingers = await segment_image(client, url, finger_prompt, (H, W))
            fingers = [f for f in fingers if f[1].sum() >= 50]
            # Оставляем только пальцы, которые касаются грифа (близко к маске грифа):
            # большой палец за грифом и чужие руки отбрасываем.
            if neck is not None and neck.sum() >= 50 and fingers:
                dist = cv2.distanceTransform((neck == 0).astype(np.uint8), cv2.DIST_L2, 3)
                near = [f for f in fingers if float(dist[f[1] > 0].min()) <= args.contact_px]
                fingers = near if near else fingers
            fingers = fingers[:6]
        metrics = [finger_metrics(m, neck, oid, args.ok_deg) for oid, m, _ in fingers]
        for (oid, _, conf), fm in zip(fingers, metrics):
            rows.append({"clip": video.name, "frame": idx, "t_sec": round(t, 2), "finger": oid,
                         "conf": conf, "contact_angle": fm.contact_angle, "corners": fm.corners,
                         "overlap": fm.overlap, "elongation": fm.elongation, "verdict": fm.verdict})
        vis = draw(frame, neck, fingers, metrics)
        cv2.putText(vis, f"{video.name} f{idx} t={t:.1f}s neck={'yes' if neck is not None else 'no'} fingers={len(fingers)}",
                    (8, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(str(out_dir / f"frame_{idx:05d}.jpg"), vis)
        vis_frames.append(vis)
        print(f"{video.name} f{idx:05d} t={t:5.1f}s neck={'+' if neck is not None else '-'} fingers={len(fingers)} "
              + " ".join(f"[{fm.object_id}:{fm.contact_angle}° ov={fm.overlap} el={fm.elongation} {fm.verdict}]" for fm in metrics), flush=True)
    ovs = [r["overlap"] for r in rows if r["overlap"] is not None]
    els = [r["elongation"] for r in rows if r["elongation"] is not None]
    if ovs:
        print(f"== {video.name}: overlap медиана {np.median(ovs):.2f} (p25 {np.percentile(ovs,25):.2f}, p75 {np.percentile(ovs,75):.2f}); "
              f"elongation медиана {np.median(els):.2f} (p25 {np.percentile(els,25):.2f}, p75 {np.percentile(els,75):.2f})")
    with open(out_dir / "metrics.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["clip", "frame", "t_sec", "finger", "conf", "contact_angle", "corners", "overlap", "elongation", "verdict"])
        w.writeheader(); w.writerows(rows)
    sheet = contact_sheet(vis_frames)
    if sheet is not None:
        cv2.imwrite(str(out_dir / "sheet.jpg"), sheet)
    angles = [r["contact_angle"] for r in rows if r["contact_angle"] is not None]
    if angles:
        print(f"== {video.name}: кадров {len(vis_frames)}, пальцев {len(rows)}, "
              f"угол медиана {np.median(angles):.0f}°, доля «стоит» {np.mean([a >= args.ok_deg for a in angles]):.0%}")


def load_key(env_file: str | None) -> str:
    key = os.environ.get("MODEL_API_KEY", "")
    if not key and env_file:
        for line in Path(env_file).expanduser().read_text().splitlines():
            if line.startswith("MODEL_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        raise SystemExit("нет MODEL_API_KEY: задайте переменную окружения или --env-file")
    return key


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--fps", type=float, default=1.0, help="кадров в секунду для выборки")
    ap.add_argument("--max-frames", type=int, default=20)
    ap.add_argument("--max-side", type=int, default=896)
    ap.add_argument("--prompts", nargs=2, default=["guitar fretboard", "finger"], metavar=("NECK", "FINGER"))
    ap.add_argument("--ok-deg", type=float, default=60.0, help="порог угла «палец стоит»")
    ap.add_argument("--contact-px", type=float, default=12.0, help="макс. расстояние пальца до грифа, чтобы считать его зажимающим")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out")
    ap.add_argument("--env-file", default=None, help="файл с MODEL_API_KEY=... (ключ не печатается)")
    ap.add_argument("--dry-run", action="store_true", help="только нарезка кадров, без вызовов API")
    args = ap.parse_args()

    client = None
    if not args.dry_run:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=load_key(args.env_file))
    for video in args.videos:
        await process_clip(client, video, args.out / video.stem, args)


if __name__ == "__main__":
    asyncio.run(main())
