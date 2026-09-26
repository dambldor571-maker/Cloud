"""Mountains of any hex group (a row, 2x2, 2x3 ...) from real elevation data.
The group is split into its rows; every row gets a real ridge from the DEM (fitted
along the row, as in the approved v2 look), the ridges merge into one massif and the
saddles between rows are filled so the group reads as one mountain.
Usage: make_dem_mountains.py config.json area out_dir
config: {"groups": [[[col,row], ...], ...], "hmax": 15, "km_per_hex": 3}"""
import json, math, sys
import numpy as np
from scipy import ndimage
from PIL import Image
cfg = json.load(open(sys.argv[1])); area = sys.argv[2]; OUT = sys.argv[3]
dem = np.load(f"dem/{area}.npy"); mpp = float(open(f"dem/{area}.mpp").read())
R = 5.5; STEP = 0.1
HMAX = cfg.get("hmax", 15)
x0, z0 = -R * 1.2, -R * 1.2
x1 = R * math.sqrt(3) * 11.5 + R * 0.2; z1 = R * 1.5 * 7 + R * 1.2
nx, nz = int((x1 - x0) / STEP) + 1, int((z1 - z0) / STEP) + 1
X, Z = np.meshgrid(x0 + np.arange(nx) * STEP, z0 + np.arange(nz) * STEP)
hw = lambda c, r: np.array([R * math.sqrt(3) * (c + 0.5 * (r & 1)), R * 1.5 * r])
rots = {ang: ndimage.rotate(dem, ang, reshape=False, order=1, mode="nearest") for ang in range(0, 180, 10)}
rng = np.random.default_rng(cfg.get("seed", 5))
used = []


def ridge(a, b, nhex, height, width=2.0):
    """one real ridge from the DEM laid from a to b (v2 method)"""
    Lf = np.linalg.norm(b - a) + R * 1.7
    Wf = R * width
    lw = int(cfg.get("km_per_hex", 3.0) * nhex * 1000 / mpp); ww = int(lw * Wf / Lf)
    best = None
    for ang, rot in rots.items():
        n = rot.shape[0]
        for cy in range(ww, n - ww, 8):
            for cx in range(lw // 2 + n // 6, n - lw // 2 - n // 6, 8):
                if any(abs(cx - ux) < lw and abs(cy - uy) < ww and ua == ang for ux, uy, ua in used):
                    continue
                win = rot[cy - ww // 2:cy + ww // 2, cx - lw // 2:cx + lw // 2]
                q = ww // 4
                mid = win[ww // 2 - q // 2:ww // 2 + q // 2].mean()
                edge = 0.5 * (win[:q].mean() + win[-q:].mean())
                prof = win[ww // 2 - q // 2:ww // 2 + q // 2].mean(axis=0)
                score = (mid - edge) - 0.3 * np.std(np.diff(prof[::max(1, lw // 10)]))
                if best is None or score > best[0]:
                    best = (score, ang, cx, cy, win.copy())
    sc, ang, cx, cy, win = best
    used.append((cx, cy, ang))
    d = (b - a) / np.linalg.norm(b - a); nrm = np.array([-d[1], d[0]])
    c = (a + b) / 2
    s = ((X - c[0]) * d[0] + (Z - c[1]) * d[1]) / Lf + 0.5
    t = ((X - c[0]) * nrm[0] + (Z - c[1]) * nrm[1]) / Wf + 0.5
    inside = (s > 0) & (s < 1) & (t > 0) & (t < 1)
    hv = ndimage.map_coordinates(win, [np.clip(t, 0, 1) * (win.shape[0] - 1), np.clip(s, 0, 1) * (win.shape[1] - 1)], order=3)
    hv = np.clip(hv - np.percentile(win, 35), 0, None)
    e = np.abs(2 * s - 1) ** 3 + np.abs(2 * t - 1) ** 1.6
    fade = np.clip(1 - e, 0, 1)
    fade = fade * fade * (3 - 2 * fade)
    hv = np.where(inside, hv * fade, 0)
    return hv * height / max(hv.max(), 1e-6)


Hm = np.zeros((nz, nx))
for gi, hexes in enumerate(cfg["groups"]):
    rows = {}
    for c, r in hexes:
        rows.setdefault(r, []).append(c)
    runs = []
    for r, cols in rows.items():
        cols.sort()
        run = [cols[0]]
        for c in cols[1:]:
            if c == run[-1] + 1:
                run.append(c)
            else:
                runs.append((r, run)); run = [c]
        runs.append((r, run))
    top = rng.integers(0, len(runs))  # one row carries the highest summit
    G = np.zeros((nz, nx))
    for k, (r, run) in enumerate(runs):
        a, b = hw(run[0], r), hw(run[-1], r)
        if len(run) == 1:
            a, b = a - np.array([R * 0.45, 0]), b + np.array([R * 0.45, 0])
        hgt = HMAX * (1.0 if k == top else rng.uniform(0.7, 0.9))
        G = np.maximum(G, ridge(a, b, max(len(run), 1.5), hgt, 2.0 if len(runs) == 1 else 2.9))
        print(area, "group", gi, "row", r, "hexes", len(run))
    Hm = np.maximum(Hm, G)
Hm = Hm.astype(np.float32)
Hm.tofile(OUT + "/mountain_h.f32")
gz_, gx_ = np.gradient(Hm, STEP)
nm = np.dstack([-gx_, np.ones_like(Hm), -gz_]); nm /= np.linalg.norm(nm, axis=2, keepdims=True)
cav = np.clip((Hm - ndimage.gaussian_filter(Hm, 6)) / 0.4, -1, 1)
img = np.dstack([nm[..., 0] * 0.5 + 0.5, nm[..., 2] * 0.5 + 0.5, cav * 0.5 + 0.5, np.ones_like(Hm)])
Image.fromarray((img * 255).clip(0, 255).astype(np.uint8), "RGBA").save(OUT + "/mountain_nc.png")
json.dump({"x0": x0, "z0": z0, "step": STEP, "nx": nx, "nz": nz, "max": float(Hm.max())}, open(OUT + "/mountain.json", "w"))
