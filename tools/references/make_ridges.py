"""Continuous mountain ranges (Civ5-like): one crest line runs through all hexes of
a range (2+ hexes), the crest height rises and falls along it (summits and saddles,
never one peak per hex), spurs run down the flanks and droplet erosion cuts the
gullies. Usage: make_ridges.py config.json out_dir [drops]
config: {"ranges": [[[col,row], ...], ...], "hmax": 11}
Writes mountain_h.f32, mountain_nc.png, mountain.json (grid header)."""
import json, math, sys
import numpy as np
from scipy import ndimage
from PIL import Image

cfg = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
DROPS = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
R = 5.5
STEP = 0.1
x0, z0 = -R * 1.2, -R * 1.2
x1 = R * math.sqrt(3) * 11.5 + R * 0.2
z1 = R * 1.5 * 7 + R * 1.2
nx, nz = int((x1 - x0) / STEP) + 1, int((z1 - z0) / STEP) + 1
X, Z = np.meshgrid(x0 + np.arange(nx) * STEP, z0 + np.arange(nz) * STEP)
rng = np.random.default_rng(cfg.get("seed", 3))


def hw(c, r):
    return np.array([R * math.sqrt(3) * (c + 0.5 * (r & 1)), R * 1.5 * r])


def fbm(octaves, base_cells, gain=0.5, seed=0, ridged=False):
    r = np.random.default_rng(seed)
    out = np.zeros((nz, nx))
    amp, tot, cells = 1.0, 0.0, base_cells
    for o in range(octaves):
        gx, gz = max(2, int(nx / cells) + 3), max(2, int(nz / cells) + 3)
        n = ndimage.zoom(r.uniform(-1, 1, (gz, gx)), (nz / (gz - 3), nx / (gx - 3)), order=3)[:nz, :nx]
        if ridged:
            n = (1.0 - np.abs(n)) ** 2
        out += amp * n
        tot += amp
        amp *= gain
        cells /= 2.1
    return out / tot


def chaikin(p, it):
    for _ in range(it):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        q.append(p[-1])
        p = q
    return p


def noise1d(n, seed, cells):
    r = np.random.default_rng(seed)
    k = max(4, int(n / cells) + 4)
    return ndimage.zoom(r.uniform(-1, 1, k), n / (k - 3), order=3)[:n]


spurs = fbm(4, 45, gain=0.5, seed=2, ridged=True)
lat_rng = np.random.default_rng(7)
LAT = lat_rng.uniform(-1, 1, (64, 1024))


def vnoise(a, b):
    # smooth value noise at arbitrary (a, b) coordinates, a wraps over 1024 cells
    a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
    return ndimage.map_coordinates(LAT, [np.mod(b, 60) + 2, np.mod(a, 1020)], order=3, mode="wrap")


Hm = np.zeros((nz, nx))
for ri, rng_hexes in enumerate(cfg["ranges"]):
    pts = [hw(c, r) for c, r in rng_hexes]
    # extend half a hex beyond both ends so the range fills its end hexes
    d0 = pts[0] - pts[1]
    d1 = pts[-1] - pts[-2]
    pts = [pts[0] + d0 / np.linalg.norm(d0) * R * 0.75] + pts + [pts[-1] + d1 / np.linalg.norm(d1) * R * 0.75]
    # the crest wanders a little around the hex centres
    for i in range(1, len(pts) - 1):
        a = pts[i + 1] - pts[i - 1]
        nrm = np.array([-a[1], a[0]]) / np.linalg.norm(a)
        pts[i] = pts[i] + nrm * rng.uniform(-1.2, 1.2)
    crest = np.array(chaikin(pts, 4))
    seg_len = np.linalg.norm(crest[1:] - crest[:-1], axis=1)
    s_at = np.concatenate([[0], np.cumsum(seg_len)])
    L = s_at[-1]
    # distance to the crest polyline and arc length of the closest point
    best = np.full((nz, nx), 1e9)
    sbest = np.zeros((nz, nx))
    for i in range(len(crest) - 1):
        a, b = crest[i], crest[i + 1]
        ab = b - a
        t = np.clip(((X - a[0]) * ab[0] + (Z - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        d = np.hypot(X - a[0] - ab[0] * t, Z - a[1] - ab[1] * t)
        m = d < best
        best[m] = d[m]
        sbest[m] = s_at[i] + t[m] * seg_len[i]
    # crest height along the range: summits and saddles, tapering at the ends
    ns = 400
    prof_s = 0.72 + 0.28 * noise1d(ns, 10 + ri, 60)
    Hc = cfg.get("hmax", 11.0) * np.interp(sbest / L, np.linspace(0, 1, ns), prof_s)
    taper = np.clip(sbest / (R * 1.1), 0, 1) * np.clip((L - sbest) / (R * 1.1), 0, 1)
    taper = taper * taper * (3 - 2 * taper)
    # flank width varies along the range
    wid = R * (0.85 + 0.2 * np.interp(sbest / L, np.linspace(0, 1, ns), noise1d(ns, 20 + ri, 80)))
    wid = wid * (0.35 + 0.65 * taper)  # flanks narrow towards the ends: pointed, not square
    u = best / wid
    prof = np.clip(1 - u, 0, 1)
    side = np.sign((X - 0) * 0 + 1)  # placeholder, both flanks share the pattern
    h = Hc * taper * prof ** 0.95
    # flank sculpting in ridge coordinates (s along the crest, u down the slope):
    # main spurs every ~4 m and dense gullies every ~1.2 m running straight down
    sw = sbest + 1.4 * vnoise(sbest * 0.15 + 300 * ri, u * 1.5 + 5) + 0.15 * vnoise(sbest * 0.5 + 350 * ri, u * 2.0 + 9)  # gullies wander and merge
    spur = 1.0 - np.abs(vnoise(sw / 4.0 + 100 * ri, u * 0.6 + 20))
    # dense regular fluting (period ~0.7 m, varying), like Civ5 mountain walls
    period = 0.8 * (1 + 0.2 * vnoise(sbest * 0.25 + 700 + 100 * ri, 50))
    flute = 0.5 - 0.5 * np.cos(2 * np.pi * (sw / period))
    depth = 0.55 + 0.45 * vnoise(sw / 2.5 + 900 + 100 * ri, u * 1.5 + 30)
    slope_w = np.clip(u * 4, 0, 1) * np.clip((1 - u) * 3, 0, 1)  # not on the crest or the foot
    h -= Hc * taper * slope_w * (0.14 * (1 - spur) + 0.08 * flute ** 1.5 * depth)
    # jagged crest and rough rock
    h += Hc * taper * prof ** 3 * 0.10 * vnoise(sbest / 1.3 + 1100 + 100 * ri, 10)
    h += 0.35 * (spurs - 0.5) * taper * np.clip(prof * 3, 0, 1)
    Hm = np.maximum(Hm, h)


def erode(hm, n_drops, mask):
    h = hm.copy()
    ys, xs_ = np.nonzero(mask)
    idx = rng.integers(0, len(ys), n_drops)
    inertia, cap_k, min_slope, dep_k, ero_k, evap, grav = 0.05, 4.0, 0.01, 0.2, 0.3, 0.03, 9.0
    rad = 2
    bw = []
    for dz in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            d = math.hypot(dx, dz)
            if d <= rad:
                bw.append((dz, dx, rad - d))
    s = sum(b[2] for b in bw)
    bw = [(a, b, c / s) for a, b, c in bw]
    H_, W_ = h.shape
    for k in range(n_drops):
        py = ys[idx[k]] + rng.random()
        px = xs_[idx[k]] + rng.random()
        dx = dy = 0.0
        vel, water, sed = 1.0, 1.0, 0.0
        for step in range(60):
            ix, iy = int(px), int(py)
            if ix < 3 or iy < 3 or ix >= W_ - 4 or iy >= H_ - 4:
                break
            fx, fy = px - ix, py - iy
            h00, h10, h01, h11 = h[iy, ix], h[iy, ix + 1], h[iy + 1, ix], h[iy + 1, ix + 1]
            gx = (h10 - h00) * (1 - fy) + (h11 - h01) * fy
            gy = (h01 - h00) * (1 - fx) + (h11 - h10) * fx
            hcur = h00 * (1 - fx) * (1 - fy) + h10 * fx * (1 - fy) + h01 * (1 - fx) * fy + h11 * fx * fy
            dx = dx * inertia - gx * (1 - inertia)
            dy = dy * inertia - gy * (1 - inertia)
            ln = math.hypot(dx, dy)
            if ln < 1e-9:
                break
            dx /= ln
            dy /= ln
            npx, npy = px + dx, py + dy
            jx, jy = int(npx), int(npy)
            if jx < 3 or jy < 3 or jx >= W_ - 4 or jy >= H_ - 4:
                break
            gfx, gfy = npx - jx, npy - jy
            hnew = (h[jy, jx] * (1 - gfx) * (1 - gfy) + h[jy, jx + 1] * gfx * (1 - gfy)
                    + h[jy + 1, jx] * (1 - gfx) * gfy + h[jy + 1, jx + 1] * gfx * gfy)
            dh = hnew - hcur
            cap = max(-dh, min_slope) * vel * water * cap_k
            if sed > cap or dh > 0:
                dep = min(dh, sed) if dh > 0 else (sed - cap) * dep_k
                sed -= dep
                h[iy, ix] += dep * (1 - fx) * (1 - fy)
                h[iy, ix + 1] += dep * fx * (1 - fy)
                h[iy + 1, ix] += dep * (1 - fx) * fy
                h[iy + 1, ix + 1] += dep * fx * fy
            else:
                er = min((cap - sed) * ero_k, -dh)
                for bz, bx, bwt in bw:
                    h[iy + bz, ix + bx] -= er * bwt
                sed += er
            vel = math.sqrt(max(vel * vel - dh * grav, 0.01))
            water *= 1 - evap
            px, py = npx, npy
    return h


print("pre-erosion max", Hm.max())
H0 = Hm.copy()
if DROPS > 0:
    Hm = erode(Hm, DROPS, Hm > 0.3)
# erosion only cuts gullies: no sediment fans spreading over the plain
Hm = np.where(H0 > 0.02, np.clip(Hm, H0 - 1.6 * np.clip(H0 / 3.0, 0, 1), H0 + 0.15), 0.0)
Hm = np.maximum(ndimage.gaussian_filter(Hm, 0.7), 0.0).astype(np.float32)
Hm.tofile(OUT + "/mountain_h.f32")
Hu = Hm
gz_, gx_ = np.gradient(Hu, STEP)
nrm = np.dstack([-gx_, np.ones_like(Hu), -gz_])
nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
cav = np.clip((Hu - ndimage.gaussian_filter(Hu, 6)) / 0.4, -1, 1)
img = np.dstack([nrm[..., 0] * 0.5 + 0.5, nrm[..., 2] * 0.5 + 0.5, cav * 0.5 + 0.5, np.ones_like(Hu)])
Image.fromarray((img * 255).clip(0, 255).astype(np.uint8), "RGBA").save(OUT + "/mountain_nc.png")
json.dump({"x0": x0, "z0": z0, "step": STEP, "nx": nx, "nz": nz, "max": float(Hm.max())}, open(OUT + "/mountain.json", "w"))
print("grid", nx, nz, "max h", Hm.max())
