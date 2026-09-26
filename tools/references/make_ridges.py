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
# gently bent coordinates so faces are not perfectly flat
WX = X + 0.9 * (fbm(3, 90, seed=31) * 2)
WZ = Z + 0.9 * (fbm(3, 90, seed=32) * 2)
def pyramid(cx, cz, height, radius, faces, rot, rs):
    """faceted peak: planar faces meeting in sharp aretes; every face its own slope"""
    d = np.full((nz, nx), -1e9)
    for k in range(faces):
        a = rot + 2 * np.pi * k / faces + rs.uniform(-0.2, 0.2)
        rk = radius * rs.uniform(0.85, 1.15)
        d = np.maximum(d, ((WX - cx) * np.cos(a) + (WZ - cz) * np.sin(a)) / rk)
    d = 0.7 * d + 0.3 * np.hypot(WX - cx, WZ - cz) / radius  # pyramid, slightly rounded
    t = np.clip(1 - d, 0, 1)
    return height * t ** rs.uniform(1.6, 2.1)  # concave faces: sharp tip, wide foot


for ri, rng_hexes in enumerate(cfg["ranges"]):
    rs = np.random.default_rng(100 + ri * 17 + cfg.get("seed", 3))
    pts = [hw(c, r) for c, r in rng_hexes]
    d0 = pts[0] - pts[1]
    d1 = pts[-1] - pts[-2]
    pts = [pts[0] + d0 / np.linalg.norm(d0) * R * 0.35] + pts + [pts[-1] + d1 / np.linalg.norm(d1) * R * 0.35]
    crest = np.array(chaikin(pts, 3))
    seg = np.linalg.norm(crest[1:] - crest[:-1], axis=1)
    s_at = np.concatenate([[0], np.cumsum(seg)])
    L = s_at[-1]

    def at(sv):
        i = min(np.searchsorted(s_at, sv) - 1, len(seg) - 1)
        i = max(i, 0)
        t = (sv - s_at[i]) / max(seg[i], 1e-6)
        p = crest[i] * (1 - t) + crest[i + 1] * t
        tan = (crest[i + 1] - crest[i]) / max(seg[i], 1e-6)
        return p, np.array([-tan[1], tan[0]])

    h = np.zeros((nz, nx))
    hmax = cfg.get("hmax", 11.0)
    # main peaks along the crest: uneven spacing and sizes, one of them the summit
    sv = rs.uniform(0.3, 0.8) * R
    main = []
    while sv < L - 0.3 * R:
        main.append(sv)
        sv += rs.uniform(0.8, 1.3) * R
    top = rs.integers(0, len(main))
    for j, sv in enumerate(main):
        p, nrm = at(sv)
        p = p + nrm * rs.uniform(-1.3, 1.3)
        end = min(sv, L - sv) / (R * 0.9)
        size = (1.0 if j == top else rs.uniform(0.55, 0.85)) * min(1.0, 0.55 + 0.45 * end)
        hgt = hmax * size
        rad = R * rs.uniform(1.05, 1.35) * (0.8 + 0.2 * size)
        h = np.maximum(h, pyramid(p[0], p[1], hgt, rad, int(rs.integers(4, 7)), rs.uniform(0, 2 * np.pi), rs))
        # a lower shoulder peak on one flank now and then
        if rs.random() < 0.45:
            side = rs.choice([-1, 1])
            q = p + nrm * side * rs.uniform(0.35, 0.6) * R + (crest[-1] - crest[0]) / L * rs.uniform(-1.5, 1.5)
            h = np.maximum(h, pyramid(q[0], q[1], hgt * rs.uniform(0.35, 0.6), rad * rs.uniform(0.5, 0.7),
                                      int(rs.integers(4, 7)), rs.uniform(0, 2 * np.pi), rs))
    # rock roughness: stronger on the faces than at the foot
    h += h / hmax * 0.9 * (spurs - 0.5)
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
