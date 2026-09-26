"""Build the hill preset library (approved look: Emmental hills, soft, grassy).
Same format as the mountain presets. Usage: make_hill_presets.py out_dir"""
import json, sys
import numpy as np
from PIL import Image
from mountains_lib import Grid, group, hw, massif, STEP

OUT = sys.argv[1]
COUNTS = {6: 2, 5: 3, 4: 4, 3: 5, 2: 6}  # big groups first: they need the most room
HMAX = 3.2
g = Grid(11, 5)
used = []
index = []
for n, cnt in COUNTS.items():
    for v in range(cnt):
        hexes = group(2, 2, n)
        cen = np.array([hw(c, r) for c, r in hexes]).mean(0)
        h, info = massif(g, hexes, "emmental", used, hmax=HMAX, km_per_hex=1.6,
                         fade_r=0.95, fade_sig=0.55, smooth=2.0, base_pct=20)
        ys, xs = np.nonzero(h > 0.005)
        y0, y1, x0, x1 = ys.min() - 2, ys.max() + 3, xs.min() - 2, xs.max() + 3
        crop = h[y0:y1, x0:x1]
        name = f"h2x{n}_{v + 1:02d}"
        Image.fromarray((np.clip(crop / HMAX, 0, 1) * 65535).astype(np.uint16)).save(f"{OUT}/{name}.png")
        index.append({"id": name, "size": [2, n], "hmax": HMAX, "step": STEP,
                      "origin": [round(g.x0 + x0 * STEP - cen[0], 3), round(g.z0 + y0 * STEP - cen[1], 3)],
                      "shape": list(crop.shape), **info})
        print(name, info, flush=True)
index.sort(key=lambda e: (e["size"][1], e["id"]))
json.dump(index, open(f"{OUT}/index.json", "w"), indent=1)
