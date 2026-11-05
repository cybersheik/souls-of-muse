"""Кончики пальцев через Apple Vision (VNDetectHumanHandPoseRequest), без моделей и загрузок.
VisionHands().detect(frame_bgr) -> [{"chirality": "left|right|?", "tips": {"thumb": (x,y,conf), ...}, "points": {...}}]
Координаты в пикселях кадра, (0,0) слева сверху."""
import time, sys
import numpy as np
import cv2
import Vision, Quartz
from Foundation import NSDictionary

TIP_KEYS = {
    "thumb": Vision.VNHumanHandPoseObservationJointNameThumbTip,
    "index": Vision.VNHumanHandPoseObservationJointNameIndexTip,
    "middle": Vision.VNHumanHandPoseObservationJointNameMiddleTip,
    "ring": Vision.VNHumanHandPoseObservationJointNameRingTip,
    "little": Vision.VNHumanHandPoseObservationJointNameLittleTip,
}

def _cgimage(frame_bgr):
    rgba = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGBA)
    h, w = rgba.shape[:2]
    data = rgba.tobytes()
    provider = Quartz.CGDataProviderCreateWithData(None, data, len(data), None)
    cs = Quartz.CGColorSpaceCreateDeviceRGB()
    return Quartz.CGImageCreate(w, h, 8, 32, w * 4, cs,
                                Quartz.kCGImageAlphaNoneSkipLast | Quartz.kCGBitmapByteOrderDefault,
                                provider, None, False, Quartz.kCGRenderingIntentDefault)

class VisionHands:
    def __init__(self, max_hands=2, min_conf=0.3):
        self.max_hands, self.min_conf = max_hands, min_conf

    def detect(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        img = _cgimage(frame_bgr)
        req = Vision.VNDetectHumanHandPoseRequest.alloc().init()
        req.setMaximumHandCount_(self.max_hands)
        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, NSDictionary.dictionary())
        ok, err = handler.performRequests_error_([req], None)
        if not ok:
            raise RuntimeError(str(err))
        hands = []
        for obs in (req.results() or []):
            pts, err = obs.recognizedPointsForJointsGroupName_error_(Vision.VNHumanHandPoseObservationJointsGroupNameAll, None)
            if pts is None: continue
            points = {}
            for name, p in pts.items():
                loc = p.location()
                points[str(name)] = (float(loc.x) * w, (1.0 - float(loc.y)) * h, float(p.confidence()))
            tips = {}
            for short, key in TIP_KEYS.items():
                p = pts.get(key)
                if p is not None and p.confidence() >= self.min_conf:
                    loc = p.location()
                    tips[short] = (float(loc.x) * w, (1.0 - float(loc.y)) * h, float(p.confidence()))
            try:
                ch = {-1: "left", 1: "right"}.get(int(obs.chirality()), "?")
            except Exception:
                ch = "?"
            hands.append({"chirality": ch, "tips": tips, "points": points, "conf": float(obs.confidence())})
        return hands

def draw(frame, hands):
    out = frame.copy()
    for hd in hands:
        for name, (x, y, c) in hd["points"].items():
            cv2.circle(out, (int(x), int(y)), 3, (0, 200, 255), -1)
        for short, (x, y, c) in hd["tips"].items():
            cv2.circle(out, (int(x), int(y)), 9, (0, 0, 255), 2)
            cv2.putText(out, f"{short[0]}{c:.2f}", (int(x) + 8, int(y) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        if hd["points"]:
            x, y, _ = next(iter(hd["points"].values()))
            cv2.putText(out, hd["chirality"], (int(x), int(y) + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    return out

if __name__ == "__main__":
    vh = VisionHands()
    files = sys.argv[1:]
    for res in (None, 672, 336):
        times, found = [], 0
        for f in files:
            fr = cv2.imread(f)
            if res:
                s = res / max(fr.shape[:2]); fr = cv2.resize(fr, None, fx=s, fy=s)
            t0 = time.perf_counter(); hands = vh.detect(fr); times.append(time.perf_counter() - t0)
            ntips = sum(len(h["tips"]) for h in hands); found += ntips > 0
            if res is None:
                cv2.imwrite(f.replace(".jpg", ".hands.jpg"), draw(fr, hands))
                print(f"{f}: hands={len(hands)} tips={ntips} " + " ".join(f"{h['chirality']}:{len(h['tips'])}" for h in hands))
        times = np.array(times[1:]) if len(times) > 1 else np.array(times)
        print(f"res={res or 'full'}: median {np.median(times)*1000:.1f} ms, max {times.max()*1000:.1f} ms, frames with hands {found}/{len(files)}")
