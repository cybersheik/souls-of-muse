#!/usr/bin/env python3
"""Общие PLY-функции, вынесенные из lidar/ply_probe.py (до его argparse-блока),
чтобы depth_receiver и будущие модули импортировали без exec. Источник физики — DC1 04.11.
"""
import io
import os
import glob
import zipfile

import numpy as np


def read_ply(buf: bytes):
    """PLY (ascii/binary_little_endian, x y z [r g b]) → dict колонок."""
    hdr_end = buf.index(b"end_header\n") + len(b"end_header\n")
    hdr = buf[:hdr_end].decode("ascii", "replace").splitlines()
    fmt = next(l.split()[1] for l in hdr if l.startswith("format"))
    n = next(int(l.split()[2]) for l in hdr if l.startswith("element vertex"))
    props = []
    in_vertex = False
    for l in hdr:
        if l.startswith("element"):
            in_vertex = l.split()[1] == "vertex"
        elif l.startswith("property") and in_vertex:
            t, name = l.split()[1], l.split()[-1]
            props.append((name, t))
    tmap = {"float": "f4", "float32": "f4", "double": "f8", "uchar": "u1", "uint8": "u1",
            "int": "i4", "uint": "u4", "short": "i2", "ushort": "u2"}
    if fmt == "ascii":
        arr = np.loadtxt(io.BytesIO(buf[hdr_end:]), max_rows=n, dtype=np.float64)
        names = [p[0] for p in props]
        return {nm: arr[:, i] for i, nm in enumerate(names)}
    dt = np.dtype([(nm, ("<" if fmt.endswith("little_endian") else ">") + tmap[t]) for nm, t in props])
    arr = np.frombuffer(buf[hdr_end:hdr_end + n * dt.itemsize], dtype=dt)
    return {nm: arr[nm].astype(np.float64) for nm, _ in props}


def iter_frames(path):
    """Папка или zip с *.ply → (имя, dict колонок) по кадрам в порядке сортировки."""
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = sorted(n for n in z.namelist() if n.lower().endswith(".ply"))
            for n in names:
                yield n, read_ply(z.read(n))
    else:
        for f in sorted(glob.glob(os.path.join(path, "**", "*.ply"), recursive=True)):
            yield os.path.basename(f), read_ply(open(f, "rb").read())


def fit_plane_ransac(P, iters=300, tol=0.004, seed=0):
    """RANSAC-плоскость по точкам: (нормаль к камере, смещение, доля инлаеров)."""
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(iters):
        i = rng.choice(len(P), 3, replace=False)
        a, b, c = P[i]
        nrm = np.cross(b - a, c - a)
        nn = np.linalg.norm(nrm)
        if nn < 1e-9:
            continue
        nrm /= nn
        d = -nrm @ a
        inl = np.abs(P @ nrm + d) < tol
        if best is None or inl.sum() > best[0]:
            best = (inl.sum(), inl)
    inl = best[1]
    Q = P[inl]
    cen = Q.mean(0)
    _u, _s, vt = np.linalg.svd(Q - cen, full_matrices=False)
    nrm = vt[2]
    if nrm[2] > 0:
        nrm = -nrm  # нормаль «к камере» (камера смотрит вдоль -z в ARKit)
    return nrm, -nrm @ cen, inl.mean()


def height(P, nrm, d):
    """Высота над плоскостью: положительно = к камере."""
    return P @ nrm + d
