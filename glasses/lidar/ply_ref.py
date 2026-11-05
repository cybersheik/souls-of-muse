#!/usr/bin/env python3
"""Разбор одной записи Record3D (PLY-последовательность) с настоящей клавиатурой:
плоскость по первому кадру, опорная поверхность = медиана высоты по клетке (4 мм) по всей записи,
рука = точки выше опоры на tau. На выход CSV по кадрам и картинки высоты над опорой.

  .venv-lidar/bin/python lidar/ply_ref.py clips/lidar_spike/take_... --step 3 --ref-step 30
"""
import argparse, os, glob, csv, time
import numpy as np, cv2
src = open(os.path.join(os.path.dirname(__file__), 'ply_probe.py')).read().split('ap = argparse.ArgumentParser()')[0]
exec(src)  # read_ply, fit_plane_ransac

ap = argparse.ArgumentParser()
ap.add_argument('take'); ap.add_argument('--step', type=int, default=3); ap.add_argument('--ref-step', type=int, default=30)
ap.add_argument('--near', type=float, default=1.1, help='радиус от камеры, м'); ap.add_argument('--cell', type=float, default=0.004)
ap.add_argument('--tau', type=float, default=0.010); ap.add_argument('--press', type=float, default=0.006, help='клавиша утоплена: ниже опоры на столько, м'); ap.add_argument('--min-blob', type=int, default=150, help='минимум клеток в пятне руки'); ap.add_argument('--roi', type=int, nargs=4, default=None, metavar=('R0','R1','C0','C1'), help='зона клавиш в клетках: строки и столбцы'); ap.add_argument('--out', default='out/lidar/ref'); ap.add_argument('--img-every', type=int, default=150); ap.add_argument('--img-frames', type=int, nargs='*', default=[])
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
files = sorted(glob.glob(os.path.join(a.take, '*.ply'))); print('frames', len(files), flush=True)
def load(f):
    d = read_ply(open(f, 'rb').read()); P = np.c_[d['x'], d['y'], d['z']]
    near = np.linalg.norm(P, axis=1) < a.near; return P[near]
P0 = load(files[0]); nrm, dd, frac = fit_plane_ransac(P0[::3], iters=400, tol=0.004)
h0 = P0 @ nrm + dd; print('plane frame0: normal', nrm.round(4), 'inliers', round(frac, 3), 'noise std mm', round(float(h0[np.abs(h0) < 0.004].std() * 1000), 2), flush=True)
u = np.cross(nrm, [1, 0, 0]); u /= np.linalg.norm(u); v = np.cross(nrm, u)
def proj(P):
    return P @ u, P @ v, P @ nrm + dd
# границы клеток по первому кадру с запасом
pu, pv, _ = proj(P0); u0, v0 = pu.min() - 0.05, pv.min() - 0.05; W = int((pu.max() - u0 + 0.05) / a.cell) + 1; H = int((pv.max() - v0 + 0.05) / a.cell) + 1
def cells(pu, pv):
    xi = np.clip(((pu - u0) / a.cell).astype(int), 0, W - 1); yi = np.clip(((pv - v0) / a.cell).astype(int), 0, H - 1); return yi * W + xi
# опорная поверхность: медиана по клетке
t = time.time(); ids = []; hs = []
for f in files[::a.ref_step]:
    P = load(f); pu, pv, h = proj(P); ids.append(cells(pu, pv)); hs.append(h.astype(np.float32))
ids = np.concatenate(ids); hs = np.concatenate(hs); order = np.argsort(ids, kind='stable'); ids, hs = ids[order], hs[order]
ref = np.full(W * H, np.nan, np.float32); cnt = np.zeros(W * H, np.int32)
starts = np.r_[0, np.flatnonzero(np.diff(ids)) + 1, len(ids)]
for s, e in zip(starts[:-1], starts[1:]):
    ref[ids[s]] = np.median(hs[s:e]); cnt[ids[s]] = e - s
print('ref built from', len(files[::a.ref_step]), 'frames in', round(time.time() - t, 1), 's; cells with data', int((cnt > 0).sum()), 'of', W * H, flush=True)
refimg = ref.reshape(H, W); vis = np.nan_to_num(refimg, nan=-0.02); vis = cv2.applyColorMap(np.clip((vis + 0.02) / 0.08 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_JET); vis[np.isnan(refimg)] = 0
cv2.imwrite(os.path.join(a.out, 'ref_height.jpg'), vis)
# покадровый разбор
rows = []; t = time.time()
with open(os.path.join(a.out, 'frames.csv'), 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['frame', 'pts', 'drift_mm', 'noise_mm', 'hand_pts', 'hand_low_mm', 'hand_p50_mm', 'hand_max_mm', 'blob_col', 'blob_row', 'blob_area', 'press_cells', 'press_min_mm'])
    for k, f in enumerate(files[::a.step]):
        i = k * a.step; P = load(f); pu, pv, h = proj(P); c = cells(pu, pv); r = ref[c]; ok = ~np.isnan(r)
        if a.roi:
            yy, xx = c // W, c % W; ok &= (yy >= a.roi[0]) & (yy < a.roi[1]) & (xx >= a.roi[2]) & (xx < a.roi[3])
        dh = h[ok] - r[ok]
        surf = np.abs(dh) < a.tau; drift = float(np.median(dh[surf])) * 1000 if surf.any() else float('nan')
        if surf.sum() > 100:  # поправка плоскостью: сдвиг и наклон опоры в этом кадре (два прохода, второй без выбросов)
            cu, cv_ = (c[ok] % W).astype(float), (c[ok] // W).astype(float); A = np.c_[cu, cv_, np.ones(len(cu))]
            for _ in range(2):
                coef, *_ = np.linalg.lstsq(A[surf], dh[surf], rcond=None); dh = dh - A @ coef; surf = np.abs(dh) < 0.006
        noise = float(dh[surf].std()) * 1000 if surf.any() else float('nan')
        # сетка клеток: средняя высота над опорой, маска руки = порог + открытие + крупные связные пятна
        cc = c[ok]; grid_sum = np.bincount(cc, weights=dh, minlength=W * H); grid_cnt = np.bincount(cc, minlength=W * H)
        gh = np.where(grid_cnt > 0, grid_sum / np.maximum(grid_cnt, 1), np.nan).reshape(H, W)
        mask = (np.nan_to_num(gh, nan=-1) > a.tau).astype(np.uint8); mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        nlab, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8); keep = np.zeros_like(mask, bool)
        for j in range(1, nlab):
            if stats[j, cv2.CC_STAT_AREA] >= a.min_blob: keep |= lab == j
        n = int(keep.sum()); hv = gh[keep]
        # прямой признак нажатия: клетки клавиатуры, ушедшие ниже опоры (клавиша утоплена)
        g2 = np.nan_to_num(gh, nan=1); pm = ((g2 < -a.press) & (g2 > -0.020)).astype(np.uint8); pm = cv2.morphologyEx(pm, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        npress = int(pm.sum()); pmin = round(float(np.nanmin(gh[pm.astype(bool)])) * 1000, 1) if npress else float('nan')
        big = max(range(1, nlab), key=lambda j: stats[j, cv2.CC_STAT_AREA], default=0)
        bc = (int(stats[big, cv2.CC_STAT_LEFT] + stats[big, cv2.CC_STAT_WIDTH] / 2), int(stats[big, cv2.CC_STAT_TOP] + stats[big, cv2.CC_STAT_HEIGHT] / 2), int(stats[big, cv2.CC_STAT_AREA])) if big and stats[big, cv2.CC_STAT_AREA] >= a.min_blob else ('', '', 0)
        if n > 0: low, p50, mx = (np.nanpercentile(hv, [5, 50, 100]) * 1000).round(1)
        else: low = p50 = mx = float('nan')
        w.writerow([i, len(P), round(drift, 2), round(noise, 2), n, low, p50, mx, *bc, npress, pmin]); rows.append((i, n, low, npress))
        if i % a.img_every == 0 or i in a.img_frames:
            img = np.zeros(W * H, np.float32); img[c[ok]] = np.clip(dh * 1000, -10, 90); img = img.reshape(H, W)
            img[keep] = np.maximum(img[keep], 95); img[pm.astype(bool)] = -10  # пятна руки красным, утопленные клетки тёмно-синим
            vis = cv2.applyColorMap(np.clip((img + 10) / 110 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_JET); m = np.zeros(W * H, bool); m[c[ok]] = True; vis[~m.reshape(H, W)] = 0
            cv2.imwrite(os.path.join(a.out, f'dh_{i:05d}.jpg'), vis)
        if k % 200 == 0: print(f'frame {i} hand_pts {n} low {low} drift {drift:.1f} ({time.time() - t:.0f}s)', flush=True)
rows = np.array(rows, float); print('done', len(rows), 'frames in', round(time.time() - t), 's', flush=True)
with_hand = rows[rows[:, 1] > 0]
print('frames with hand', len(with_hand), 'of', len(rows), '| hand_low_mm p5/p25/p50/p75', np.nanpercentile(with_hand[:, 2], [5, 25, 50, 75]).round(1) if len(with_hand) else '-')

# график: самая низкая точка руки по времени
import math
T = rows[:, 0] / 60.0; L = rows[:, 2]; Wp, Hp = 1600, 400; g = np.full((Hp, Wp, 3), 20, np.uint8)
for mm in range(0, 80, 10):
    y = Hp - 20 - int(mm / 80 * (Hp - 40)); cv2.line(g, (50, y), (Wp - 10, y), (60, 60, 60), 1); cv2.putText(g, f'{mm} mm', (2, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
for sec in range(0, int(T.max()) + 1, 5):
    x = 50 + int(sec / T.max() * (Wp - 60)); cv2.line(g, (x, 20), (x, Hp - 20), (60, 60, 60), 1); cv2.putText(g, f'{sec}s', (x - 8, Hp - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
prev = None
for t, n, low, _n in rows:
    if math.isnan(low): prev = None; continue
    x = 50 + int(t / 60 / T.max() * (Wp - 60)); y = Hp - 20 - int(min(low, 80) / 80 * (Hp - 40))
    if prev: cv2.line(g, prev, (x, y), (80, 220, 255), 1)
    prev = (x, y)
prev = None
for t, n, low, npress in rows:
    x = 50 + int(t / 60 / T.max() * (Wp - 60)); y = Hp - 20 - int(min(npress, 400) / 400 * (Hp - 40))
    if prev: cv2.line(g, prev, (x, y), (90, 90, 255), 1)
    prev = (x, y)
cv2.putText(g, 'yellow: lowest hand point above keys, mm   red: depressed key cells (0..400)', (60, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
cv2.imwrite(os.path.join(a.out, 'hand_low_timeline.png'), g); print('timeline saved')
