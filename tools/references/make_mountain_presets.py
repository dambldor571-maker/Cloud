"""Build the mountain preset library: real Alpine massifs for 2x2 ... 2x6 groups.
Each preset is stored relative to its group's centre (canonical group starts on an
even row; for odd rows compose_mountains.py mirrors it). Heights: 16-bit PNG, 0.1 m/px.
Usage: make_mountain_presets.py out_dir worker n_workers"""
import json, sys
import numpy as np
from PIL import Image
from mountains_lib import Grid, group, hw, massif, STEP

OUT, WORKER, NW = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
COUNTS = {2: 16, 3: 12, 4: 10, 5: 8, 6: 6}
AREAS = ["alps", "montblanc", "valais", "bernina", "ecrins", "dolomites", "grossglockner",
         "ortler", "paradiso", "silvretta", "todi", "zillertal", "otztal"]
HMAX = 15.0
jobs = []
k = 0
for n, cnt in COUNTS.items():
    for v in range(cnt):
        jobs.append((n, v, AREAS[k % len(AREAS)]))
        k += 1
mine = [j for j in jobs if AREAS.index(j[2]) % NW == WORKER]
mine.sort(key=lambda j: (j[2], -j[0]))  # per area, big groups first (they need the most room)
g = Grid(11, 5)
used = {}
index = []
for n, v, area in mine:
    hexes = group(2, 2, n)
    P = np.array([hw(c, r) for c, r in hexes])
    cen = P.mean(0)
    h, info = massif(g, hexes, area, used.setdefault(area, []), hmax=HMAX)
    ys, xs = np.nonzero(h > 0.01)
    y0, y1, x0, x1 = ys.min() - 2, ys.max() + 3, xs.min() - 2, xs.max() + 3
    crop = h[y0:y1, x0:x1]
    name = f"m2x{n}_{v + 1:02d}"
    Image.fromarray((np.clip(crop / HMAX, 0, 1) * 65535).astype(np.uint16)).save(f"{OUT}/{name}.png")
    index.append({"id": name, "size": [2, n], "hmax": HMAX, "step": STEP,
                  "origin": [round(g.x0 + x0 * STEP - cen[0], 3), round(g.z0 + y0 * STEP - cen[1], 3)],
                  "shape": list(crop.shape), **info})
    print(name, info, flush=True)
json.dump(index, open(f"{OUT}/index_{WORKER}.json", "w"), indent=1)
