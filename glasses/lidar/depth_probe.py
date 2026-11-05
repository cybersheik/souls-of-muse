#!/usr/bin/env python3
"""S1-проба тракта Record3D по USB: fps, размеры, confidence, кадры в файлы.
Без окон: всё пишется в лог и в out/lidar/. Запуск: .venv-lidar/bin/python lidar/depth_probe.py --sec 30
"""
import argparse, time, sys, os
import numpy as np, cv2
from threading import Event
from record3d import Record3DStream

ap = argparse.ArgumentParser()
ap.add_argument("--sec", type=float, default=30)
ap.add_argument("--out", default="out/lidar")
ap.add_argument("--every", type=float, default=2.0, help="сохранять кадр раз в N секунд")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

devs = Record3DStream.get_connected_devices()
print("devices:", len(devs), flush=True)
if not devs:
    print("iPhone по USB не найден"); sys.exit(2)
for d in devs: print("  id", d.product_id, "udid", d.udid, flush=True)

ev = Event(); s = Record3DStream()
s.on_new_frame = ev.set
s.on_stream_stopped = lambda: print("stream stopped", flush=True)
s.connect(devs[0])
print("connected; жду кадры (нажата ли красная кнопка?)", flush=True)

t0 = None; n = 0; last_save = 0; last_log = 0; ts = []
while True:
    if not ev.wait(5):
        print("нет кадров 5 с" if n == 0 else "поток прервался", flush=True)
        if n == 0 and (time.time() - (t0 or time.time())) > 20: break
        if n == 0: continue
        break
    ev.clear()
    now = time.time(); t0 = t0 or now; n += 1; ts.append(now)
    depth = s.get_depth_frame(); rgb = s.get_rgb_frame(); conf = s.get_confidence_frame()
    if n == 1:
        K = s.get_intrinsic_mat()
        print(f"depth {depth.shape} {depth.dtype}  rgb {rgb.shape}  conf {conf.shape}  device_type {s.get_device_type()}  "
              f"fx {K.fx:.1f} fy {K.fy:.1f} tx {K.tx:.1f} ty {K.ty:.1f}", flush=True)
    if now - last_log >= 5:
        recent = [t for t in ts if now - t <= 5]
        d = depth[np.isfinite(depth) & (depth > 0)]
        print(f"t={now-t0:5.1f}s frames={n} fps5={len(recent)/5:.1f} depth min/med/max={d.min():.3f}/{np.median(d):.3f}/{d.max():.3f} m", flush=True)
        last_log = now
    if now - last_save >= a.every:
        tag = f"{now-t0:05.1f}".replace(".", "_")
        d = np.nan_to_num(depth, nan=0.0)
        lo, hi = np.percentile(d[d > 0], [2, 98]) if (d > 0).any() else (0, 1)
        vis = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
        vis = cv2.applyColorMap((255 - vis * 255).astype(np.uint8), cv2.COLORMAP_JET)
        vis[d <= 0] = 0
        cv2.imwrite(f"{a.out}/depth_{tag}.png", vis)
        cv2.imwrite(f"{a.out}/rgb_{tag}.jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
        np.save(f"{a.out}/depth_{tag}.npy", depth)
        if conf.size: cv2.imwrite(f"{a.out}/conf_{tag}.png", (conf.astype(np.uint8) * 120))
        last_save = now
    if now - t0 >= a.sec: break

if n:
    dt = np.diff(ts); print(f"итог: {n} кадров за {ts[-1]-ts[0]:.1f} с, средний fps {n/max(ts[-1]-ts[0],1e-6):.1f}, "
                            f"межкадровый интервал медиана {np.median(dt)*1000:.0f} мс, макс {dt.max()*1000:.0f} мс", flush=True)
