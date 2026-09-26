"""Hill reference scene: 2xN hill groups from a real hilly area, soft transitions."""
import json, sys
import numpy as np
from mountains_lib import Grid, group, hw, massif, stitch, save_field
area, OUT = sys.argv[1], sys.argv[2]
g = Grid(11, 8)
used = []
parts = []
for (c0, r0, n) in [(1, 1, 2), (5, 1, 3), (1, 5, 4), (5, 5, 2), (8, 3, 2)]:
    hexes = group(c0, r0, n)
    h, info = massif(g, hexes, area, used, hmax=4.0, km_per_hex=1.6, fade_r=0.95, fade_sig=0.55, smooth=2.0, base_pct=20)
    parts.append((h, np.array([hw(c, r) for c, r in hexes])))
    print(area, c0, r0, n, info)
save_field(stitch(g, parts), g, OUT)
