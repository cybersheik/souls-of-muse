#!/usr/bin/env python3
"""Офлайн-разбор экспорта Record3D (PLY-последовательность): плоскость картонки,
маска руки, высота кончиков пальцев над плоскостью. Без внешних зависимостей кроме numpy/opencv.

  .venv-lidar/bin/python lidar/ply_probe.py --plane clips/lidar_spike/take1 --takes clips/lidar_spike/take2 clips/lidar_spike/take3
Папка или zip с *.ply (ascii или binary_little_endian, x y z [r g b]).
"""
import argparse, os, sys, zipfile, io, glob
import numpy as np, cv2

def read_ply(buf: bytes):
    hdr_end = buf.index(b"end_header\n") + len(b"end_header\n")
    hdr = buf[:hdr_end].decode("ascii", "replace").splitlines()
    fmt = next(l.split()[1] for l in hdr if l.startswith("format"))
    n = next(int(l.split()[2]) for l in hdr if l.startswith("element vertex"))
    props = []
    in_vertex = False
    for l in hdr:
        if l.startswith("element"): in_vertex = l.split()[1] == "vertex"
        elif l.startswith("property") and in_vertex:
            t, name = l.split()[1], l.split()[-1]
            props.append((name, t))
    tmap = {"float": "f4", "float32": "f4", "double": "f8", "uchar": "u1", "uint8": "u1", "int": "i4", "uint": "u4", "short": "i2", "ushort": "u2"}
    if fmt == "ascii":
        arr = np.loadtxt(io.BytesIO(buf[hdr_end:]), max_rows=n, dtype=np.float64)
        names = [p[0] for p in props]
        return {nm: arr[:, i] for i, nm in enumerate(names)}
    dt = np.dtype([(nm, ("<" if fmt.endswith("little_endian") else ">") + tmap[t]) for nm, t in props])
    arr = np.frombuffer(buf[hdr_end:hdr_end + n * dt.itemsize], dtype=dt)
    return {nm: arr[nm].astype(np.float64) for nm, _ in props}

def iter_frames(path):
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = sorted(n for n in z.namelist() if n.lower().endswith(".ply"))
            for n in names: yield n, read_ply(z.read(n))
    else:
        for f in sorted(glob.glob(os.path.join(path, "**", "*.ply"), recursive=True)):
            yield os.path.basename(f), read_ply(open(f, "rb").read())

def fit_plane_ransac(P, iters=300, tol=0.004, seed=0):
    rng = np.random.default_rng(seed); best = None
    for _ in range(iters):
        i = rng.choice(len(P), 3, replace=False); a, b, c = P[i]
        nrm = np.cross(b - a, c - a); nn = np.linalg.norm(nrm)
        if nn < 1e-9: continue
        nrm /= nn; d = -nrm @ a
        inl = np.abs(P @ nrm + d) < tol
        if best is None or inl.sum() > best[0]: best = (inl.sum(), inl)
    inl = best[1]; Q = P[inl]; cen = Q.mean(0)
    u, s, vt = np.linalg.svd(Q - cen, full_matrices=False); nrm = vt[2]
    if nrm[2] > 0: nrm = -nrm   # нормаль «к камере» (камера смотрит вдоль -z в ARKit)
    return nrm, -nrm @ cen, inl.mean()

def height(P, nrm, d):  # положительно = над плоскостью, к камере
    return P @ nrm + d

ap = argparse.ArgumentParser()
ap.add_argument("--plane", required=True, help="дубль 1: пустая картонка (папка или zip)")
ap.add_argument("--takes", nargs="*", default=[], help="дубли с рукой")
ap.add_argument("--tau", type=float, default=0.010, help="порог маски руки, м")
ap.add_argument("--out", default="out/lidar/ply")
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)

# 1. плоскость по дублю 1
pts = []
for i, (name, v) in enumerate(iter_frames(a.plane)):
    P = np.stack([v["x"], v["y"], v["z"]], 1); P = P[np.isfinite(P).all(1)]
    if i == 0: print(f"[plane] {name}: {len(P)} точек, z med {np.median(P[:,2]):.3f} м, поля {list(v)}")
    pts.append(P)
    if i >= 29: break
P = np.concatenate(pts); nrm, d, frac = fit_plane_ransac(P[::max(1, len(P)//200000)])
h = height(P, nrm, d)
print(f"[plane] кадров {len(pts)}, inliers {frac:.2f}, нормаль {np.round(nrm,3)}, шум глубины на плоскости: "
      f"std {h[np.abs(h)<0.02].std()*1000:.1f} мм, p95 {np.percentile(np.abs(h[np.abs(h)<0.02]),95)*1000:.1f} мм")
np.save(f"{a.out}/plane.npy", np.r_[nrm, d])

# 2. дубли с рукой: маска руки и высоты
for tk in a.takes:
    tag = os.path.splitext(os.path.basename(tk.rstrip("/")))[0]
    rows = []
    for i, (name, v) in enumerate(iter_frames(tk)):
        P = np.stack([v["x"], v["y"], v["z"]], 1); ok = np.isfinite(P).all(1); P = P[ok]
        h = height(P, nrm, d); hand = h > a.tau
        if hand.sum() < 30:
            rows.append((i, 0, np.nan, np.nan, np.nan)); continue
        hh = h[hand]
        # «кончики»: точки руки, ближайшие к плоскости среди компонент; берём 5-й перцентиль высоты
        rows.append((i, int(hand.sum()), np.percentile(hh, 5)*1000, np.median(hh)*1000, hh.max()*1000))
        if i % 10 == 0:
            # картинка: проекция на плоскость (x,y) с цветом по высоте, только область руки + плоскость
            xy = P[:, :2]; lo, hi = np.percentile(xy, [1, 99], axis=0)
            W, H = 640, 480; img = np.zeros((H, W, 3), np.uint8)
            u = ((xy[:, 0]-lo[0])/(hi[0]-lo[0]+1e-9)*(W-1)).astype(int).clip(0, W-1)
            w = ((xy[:, 1]-lo[1])/(hi[1]-lo[1]+1e-9)*(H-1)).astype(int).clip(0, H-1)
            col = np.clip(h / 0.04, 0, 1); cm = cv2.applyColorMap((col*255).astype(np.uint8), cv2.COLORMAP_JET)[:, 0]
            img[H-1-w, u] = cm
            cv2.imwrite(f"{a.out}/{tag}_{i:04d}.png", img)
    R = np.array(rows, dtype=float)
    valid = R[R[:, 1] > 0]
    print(f"[{tag}] кадров {len(R)}, с рукой {len(valid)}; высота низшей точки руки над плоскостью (мм): "
          f"min {np.nanmin(valid[:,2]):.1f}, med {np.nanmedian(valid[:,2]):.1f}, max {np.nanmax(valid[:,2]):.1f}" if len(valid) else f"[{tag}] рука не найдена (tau={a.tau})")
    np.savetxt(f"{a.out}/{tag}_heights.csv", R, fmt="%.2f", delimiter=",", header="frame,hand_pts,low_mm,med_mm,max_mm", comments="")
print("готово ->", a.out)
