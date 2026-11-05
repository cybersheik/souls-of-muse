"""Ведение масок SAM от кадра к кадру (04.11, по «Go» Айдара).
Локальный порт SAM 3.1 (MLX) объект по рамке не ведёт: на 4–5 рамок отдаёт 80–110 масок, и после отсева они
ложатся не на свои рамки. Видеослежение с номерами есть только в облачном sam-3.1 (2 с/кадр). Поэтому ведём сами:
каждый кадр захват по слову («finger», 0,1 с), отсев дублей по IoU, затем сопоставление с дорожками прошлого
кадра по IoU масок (жадно, лучшие пары первыми). Дорожка живёт при пропуске до `max_missed` кадров,
новая маска получает новый номер. Наружу: список дорожек с id, маской, рамкой, центром, возрастом.

MaskTracker().update(masks) -> [track]; track = dict(id, score, mask, box, c, age, missed)
"""
from __future__ import annotations
import numpy as np


def dedupe(masks, iou: float = 0.4, k: int = 8, min_area: int = 40):
    """masks: [(score, mask uint8)] → без дублей, не больше k, по убыванию score."""
    kept = []
    for s, m in sorted(masks, key=lambda t: -t[0]):
        if int(m.sum()) < min_area: continue
        if any(np.logical_and(m, q).sum() / max(1, np.logical_or(m, q).sum()) > iou for _, q in kept): continue
        kept.append((s, m))
        if len(kept) >= k: break
    return kept


def _box(m):
    ys, xs = np.nonzero(m)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())), (float(xs.mean()), float(ys.mean()))


class MaskTracker:
    def __init__(self, match_iou: float = 0.25, max_missed: int = 2, dedupe_iou: float = 0.4, k: int = 8):
        self.match_iou, self.max_missed, self.dedupe_iou, self.k = match_iou, max_missed, dedupe_iou, k
        self.tracks: list[dict] = []; self._next = 1

    def update(self, masks):
        det = dedupe(masks, self.dedupe_iou, self.k)
        pairs = []
        for i, (s, m) in enumerate(det):
            for j, t in enumerate(self.tracks):
                inter = np.logical_and(m, t["mask"]).sum()
                if inter == 0: continue
                iou = inter / max(1, np.logical_or(m, t["mask"]).sum())
                if iou >= self.match_iou: pairs.append((iou, i, j))
        pairs.sort(reverse=True); used_i, used_j = set(), set(); new = []
        for iou, i, j in pairs:
            if i in used_i or j in used_j: continue
            used_i.add(i); used_j.add(j); s, m = det[i]; t = self.tracks[j]
            box, c = _box(m)
            t.update(score=s, mask=m, box=box, c=c, age=t["age"] + 1, missed=0); new.append(t)
        for j, t in enumerate(self.tracks):
            if j in used_j: continue
            t["missed"] += 1
            if t["missed"] <= self.max_missed: new.append(t)
        for i, (s, m) in enumerate(det):
            if i in used_i: continue
            box, c = _box(m)
            new.append({"id": self._next, "score": s, "mask": m, "box": box, "c": c, "age": 1, "missed": 0}); self._next += 1
        self.tracks = new
        return [t for t in new if t["missed"] == 0]
