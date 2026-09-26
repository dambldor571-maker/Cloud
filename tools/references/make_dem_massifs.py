"""Mountain massifs for hex groups (2x2, 2x3 ...) from real Alpine elevation data
(the approved look): pick a window around a high summit massif whose inside is high
everywhere, rotate it along the group's long axis, fade it out to the group's hexes
(soft union of the hexes) and scale to hmax.
Usage: make_dem_massifs.py config.json out_dir
config: {"groups": [{"hexes": [[col,row],...], "area": "alps"}, ...], "hmax": 15, "km_per_hex": 2.5}"""
import json, math, sys
import numpy as np
from scipy import ndimage
from PIL import Image
cfg = json.load(open(sys.argv[1])); OUT = sys.argv[2]
R = 5.5; STEP = 0.1
x0, z0 = -R * 1.2, -R * 1.2
x1 = R * math.sqrt(3) * 11.5 + R * 0.2; z1 = R * 1.5 * 7 + R * 1.2
nx, nz = int((x1 - x0) / STEP) + 1, int((z1 - z0) / STEP) + 1
X, Z = np.meshgrid(x0 + np.arange(nx) * STEP, z0 + np.arange(nz) * STEP)
hw = lambda c, r: np.array([R * math.sqrt(3) * (c + 0.5 * (r & 1)), R * 1.5 * r])
cache = {}
used = {}


def area_rots(area):
    if area not in cache:
        cache.clear()
        dem = np.load(f"dem/{area}.npy").astype(np.float32)
        mpp = float(open(f"dem/{area}.mpp").read())
        cache[area] = (mpp, {ang: ndimage.rotate(dem, ang, reshape=False, order=1, mode="nearest") for ang in range(0, 180, 10)})
    return cache[area]


Hm = np.zeros((nz, nx))
for gi, grp in enumerate(cfg["groups"]):
    hexes, area = grp["hexes"], grp["area"]
    mpp, rots = area_rots(area)
    P = np.array([hw(c, r) for c, r in hexes])
    cen = P.mean(0)
    w, v = np.linalg.eigh(np.cov((P - cen).T) + np.eye(2) * 1e-6)
    d = v[:, 1]; nrm = np.array([-d[1], d[0]])
    al, ac = (P - cen) @ d, (P - cen) @ nrm
    Lf = al.max() - al.min() + R * 2.8
    Wf = ac.max() - ac.min() + R * 2.8
    c = cen + d * (al.max() + al.min()) / 2 + nrm * (ac.max() + ac.min()) / 2
    lw = int(cfg.get("km_per_hex", 2.5) * 1000 * (Lf - R * 0.9) / (R * math.sqrt(3)) / mpp)
    ww = int(lw * Wf / Lf)
    s = ((X - c[0]) * d[0] + (Z - c[1]) * d[1]) / Lf + 0.5
    t = ((X - c[0]) * nrm[0] + (Z - c[1]) * nrm[1]) / Wf + 0.5
    dmin = np.min([np.hypot(X - p[0], Z - p[1]) for p in P], axis=0)
    union = (dmin < R * 0.8).astype(float)
    f = np.clip(ndimage.gaussian_filter(union, R * 0.3 / STEP) * 1.6 - 0.3, 0, 1)
    fade = f * f * (3 - 2 * f)
    ws, wt = np.meshgrid(np.linspace(0, 1, lw), np.linspace(0, 1, ww))
    wx = c[0] + (ws - 0.5) * Lf * d[0] + (wt - 0.5) * Wf * nrm[0]
    wz = c[1] + (ws - 0.5) * Lf * d[1] + (wt - 0.5) * Wf * nrm[1]
    wd = np.min([np.hypot(wx - p[0], wz - p[1]) for p in P], axis=0)
    inner = wd < R * 0.6
    outer = wd > R * 1.1
    core = np.hypot(wx - cen[0], wz - cen[1]) < R * (0.5 if len(hexes) > 3 else 0.35)
    u = used.setdefault(area, [])
    for rank in range(grp.get("rank", 0) + 1):
      best = None
      for ang, rot in rots.items():
          n = rot.shape[0]
          for cy in range(ww // 2 + n // 8, n - ww // 2 - n // 8, 8):
              for cx in range(lw // 2 + n // 8, n - lw // 2 - n // 8, 8):
                  # distinct places: rotate the centre back to the unrotated DEM to compare
                  a = math.radians(ang)
                  ux = (cx - n / 2) * math.cos(a) - (cy - n / 2) * math.sin(a)
                  uy = (cx - n / 2) * math.sin(a) + (cy - n / 2) * math.cos(a)
                  if any(math.hypot(ux - px, uy - py) < 0.6 * max(lw, ww) for px, py in u):
                      continue
                  win = rot[cy - ww // 2:cy - ww // 2 + ww, cx - lw // 2:cx - lw // 2 + lw]
                  wi = win[inner]
                  score = win[core].mean() + 0.4 * wi.mean() + 0.3 * np.percentile(wi, 10) - 1.7 * win[outer].mean()
                  if best is None or score > best[0]:
                      best = (score, ang, cx, cy, ux, uy, win.copy())
      sc, ang, cx, cy, ux, uy, win = best
      u.append((ux, uy))
    print(area, "group", gi, len(hexes), "hexes, angle", ang, "score", round(sc))
    inside = (s > 0) & (s < 1) & (t > 0) & (t < 1)
    hv = ndimage.map_coordinates(win, [np.clip(t, 0, 1) * (ww - 1), np.clip(s, 0, 1) * (lw - 1)], order=3)
    hv = np.clip(hv - np.percentile(win, 35), 0, None)
    hv = np.where(inside, hv * fade, 0)
    hv *= cfg.get("hmax", 15) / max(hv.max(), 1e-6)
    Hm = np.maximum(Hm, hv)
Hm = Hm.astype(np.float32)
Hm.tofile(OUT + "/mountain_h.f32")
gz_, gx_ = np.gradient(Hm, STEP)
nm = np.dstack([-gx_, np.ones_like(Hm), -gz_]); nm /= np.linalg.norm(nm, axis=2, keepdims=True)
cav = np.clip((Hm - ndimage.gaussian_filter(Hm, 6)) / 0.4, -1, 1)
img = np.dstack([nm[..., 0] * 0.5 + 0.5, nm[..., 2] * 0.5 + 0.5, cav * 0.5 + 0.5, np.ones_like(Hm)])
Image.fromarray((img * 255).clip(0, 255).astype(np.uint8), "RGBA").save(OUT + "/mountain_nc.png")
json.dump({"x0": x0, "z0": z0, "step": STEP, "nx": nx, "nz": nz, "max": float(Hm.max())}, open(OUT + "/mountain.json", "w"))
