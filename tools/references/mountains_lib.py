"""Shared code for the mountain pipeline (approved look: real Alpine massifs, A2).

Map grid: pointy-top hexes, R = 5.5 m, odd-r offset rows, heights on a 0.1 m grid.
Mountains are always 2 rows x N hexes (2x2, 2x3, ...).
"""
import json, math
import numpy as np
from scipy import ndimage
from PIL import Image

R = 5.5
STEP = 0.1
DEM_DIR = "dem32"


def hw(c, r):
    return np.array([R * math.sqrt(3) * (c + 0.5 * (r & 1)), R * 1.5 * r])


def group(c0, r0, n):
    """hexes of a 2 x n mountain whose top-left hex is (c0, r0)"""
    return [[c, r] for r in (r0, r0 + 1) for c in range(c0, c0 + n)]


class Grid:
    def __init__(self, cols, rows):
        self.x0, self.z0 = -R * 1.2, -R * 1.2
        x1 = R * math.sqrt(3) * (cols + 0.5) + R * 0.2
        z1 = R * 1.5 * (rows - 1) + R * 1.2
        self.nx, self.nz = int((x1 - self.x0) / STEP) + 1, int((z1 - self.z0) / STEP) + 1
        self.X, self.Z = np.meshgrid(self.x0 + np.arange(self.nx) * STEP, self.z0 + np.arange(self.nz) * STEP)


_cache = {}


def area_rots(area):
    if area not in _cache:
        _cache.clear()
        dem = np.load(f"{DEM_DIR}/{area}.npy").astype(np.float32)
        mpp = float(open(f"{DEM_DIR}/{area}.mpp").read())
        _cache[area] = (mpp, {ang: ndimage.rotate(dem, ang, reshape=False, order=1, mode="nearest")
                              for ang in range(0, 180, 10)})
    return _cache[area]


def footprint_fade(g, P, fade_r=0.8, fade_sig=0.3):
    """soft union of the group's hexes (1 inside, fading to 0 around)"""
    dmin = np.min([np.hypot(g.X - p[0], g.Z - p[1]) for p in P], axis=0)
    union = (dmin < R * fade_r).astype(float)
    f = np.clip(ndimage.gaussian_filter(union, R * fade_sig / STEP) * 1.6 - 0.3, 0, 1)
    return f * f * (3 - 2 * f)


def massif(g, hexes, area, used, hmax=15.0, km_per_hex=2.5, scan=10, fade_r=0.8, fade_sig=0.3, smooth=0.0, base_pct=35):
    """Find a real summit massif in the DEM area that fits the hex group and lay it
    onto grid g. `used` holds DEM places already taken in this area (kept distinct)."""
    mpp, rots = area_rots(area)
    P = np.array([hw(c, r) for c, r in hexes])
    cen = P.mean(0)
    w, v = np.linalg.eigh(np.cov((P - cen).T) + np.eye(2) * 1e-6)
    d = v[:, 1]
    nrm = np.array([-d[1], d[0]])
    al, ac = (P - cen) @ d, (P - cen) @ nrm
    Lf = al.max() - al.min() + R * 2.8
    Wf = ac.max() - ac.min() + R * 2.8
    c = cen + d * (al.max() + al.min()) / 2 + nrm * (ac.max() + ac.min()) / 2
    lw = int(km_per_hex * 1000 * (Lf - R * 0.9) / (R * math.sqrt(3)) / mpp)
    ww = int(lw * Wf / Lf)
    ws, wt = np.meshgrid(np.linspace(0, 1, lw), np.linspace(0, 1, ww))
    wx = c[0] + (ws - 0.5) * Lf * d[0] + (wt - 0.5) * Wf * nrm[0]
    wz = c[1] + (ws - 0.5) * Lf * d[1] + (wt - 0.5) * Wf * nrm[1]
    wd = np.min([np.hypot(wx - p[0], wz - p[1]) for p in P], axis=0)
    inner = wd < R * 0.6
    outer = wd > R * 1.1
    core = np.hypot(wx - cen[0], wz - cen[1]) < R * (0.5 if len(hexes) > 3 else 0.35)
    best = None
    for ang, rot in rots.items():
        n = rot.shape[0]
        a = math.radians(ang)
        for cy in range(ww // 2 + n // 10, n - ww // 2 - n // 10, scan):
            for cx in range(lw // 2 + n // 10, n - lw // 2 - n // 10, scan):
                ux = (cx - n / 2) * math.cos(a) - (cy - n / 2) * math.sin(a)
                uy = (cx - n / 2) * math.sin(a) + (cy - n / 2) * math.cos(a)
                if any(math.hypot(ux - px, uy - py) < 0.5 * (pl + lw) / 2 for px, py, pl in used):
                    continue
                win = rot[cy - ww // 2:cy - ww // 2 + ww, cx - lw // 2:cx - lw // 2 + lw]
                wi = win[inner]
                score = win[core].mean() + 0.4 * wi.mean() + 0.3 * np.percentile(wi, 10) - 1.7 * win[outer].mean()
                if best is None or score > best[0]:
                    best = (score, ang, cx, cy, ux, uy, win.copy())
    sc, ang, cx, cy, ux, uy, win = best
    used.append((ux, uy, lw))
    s = ((g.X - c[0]) * d[0] + (g.Z - c[1]) * d[1]) / Lf + 0.5
    t = ((g.X - c[0]) * nrm[0] + (g.Z - c[1]) * nrm[1]) / Wf + 0.5
    inside = (s > 0) & (s < 1) & (t > 0) & (t < 1)
    hv = ndimage.map_coordinates(win, [np.clip(t, 0, 1) * (ww - 1), np.clip(s, 0, 1) * (lw - 1)], order=3)
    if smooth > 0:
        win = ndimage.gaussian_filter(win, smooth)
    hv = ndimage.map_coordinates(win, [np.clip(t, 0, 1) * (ww - 1), np.clip(s, 0, 1) * (lw - 1)], order=3)
    hv = np.clip(hv - np.percentile(win, base_pct), 0, None)
    hv = np.where(inside, hv * footprint_fade(g, P, fade_r, fade_sig), 0)
    hv *= hmax / max(hv.max(), 1e-6)
    return hv, {"area": area, "angle": ang, "score": round(float(sc)), "dem_xy": [round(ux), round(uy)]}


def stitch(g, parts):
    """parts: [(heights, hex centres)]. Grow wide rocky saddles where groups touch."""
    H = np.zeros((g.nz, g.nx))
    for h, P in parts:
        H = np.maximum(H, h)
    k = int(R * 2.6 / STEP)
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            hi, Pi = parts[i]
            hj, Pj = parts[j]
            if min(np.hypot(*(a - b)) for a in Pi for b in Pj) > R * math.sqrt(3) * 1.05:
                continue
            fi, fj = footprint_fade(g, Pi), footprint_fade(g, Pj)
            si = ndimage.gaussian_filter(ndimage.maximum_filter(hi, size=k), k / 4)
            sj = ndimage.gaussian_filter(ndimage.maximum_filter(hj, size=k), k / 4)
            near = (np.clip(ndimage.gaussian_filter(fi, k / 3) * 4, 0, 1)
                    * np.clip(ndimage.gaussian_filter(fj, k / 3) * 4, 0, 1))
            rough = ndimage.gaussian_filter(np.random.default_rng(i * 7 + j).normal(size=H.shape), 6) * 8
            saddle = (0.75 * np.minimum(si, sj) + (hi + hj) * 0.25) * near
            H = np.maximum(H, saddle * (1 + 0.25 * rough))
    return H


def save_field(H, g, out_dir):
    H = H.astype(np.float32)
    H.tofile(out_dir + "/mountain_h.f32")
    gz_, gx_ = np.gradient(H, STEP)
    nm = np.dstack([-gx_, np.ones_like(H), -gz_])
    nm /= np.linalg.norm(nm, axis=2, keepdims=True)
    cav = np.clip((H - ndimage.gaussian_filter(H, 6)) / 0.4, -1, 1)
    img = np.dstack([nm[..., 0] * 0.5 + 0.5, nm[..., 2] * 0.5 + 0.5, cav * 0.5 + 0.5, np.ones_like(H)])
    Image.fromarray((img * 255).clip(0, 255).astype(np.uint8), "RGBA").save(out_dir + "/mountain_nc.png")
    json.dump({"x0": g.x0, "z0": g.z0, "step": STEP, "nx": g.nx, "nz": g.nz, "max": float(H.max())},
              open(out_dir + "/mountain.json", "w"))
