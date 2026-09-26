"""Test map 40 x 20 (landscape): one mountain massif + one ridge (2xN mountain presets,
stitched), several 2xN hill groups (hill presets), forests, fields, plains. No rivers.
Writes layout.json (gameplay terrain per hex), mountains.json and hills.json (composer input)."""
import json
import numpy as np
COLS, ROWS = 40, 20
T = [["G"] * COLS for _ in range(ROWS)]
mountains = [(15, 1, 5), (20, 1, 4), (17, 3, 4), (27, 15, 5), (32, 15, 3)]
# north massif as approved; south-east ridge: both from the Mont Blanc area so they match
MTN_PRESETS = ["m2x5_02", "m2x4_07", "m2x4_03", "m2x5_03", "m2x3_12"]
hills = [(4, 4, 3), (6, 13, 4), (12, 8, 2), (24, 6, 3), (30, 9, 2), (35, 3, 3), (19, 16, 3), (1, 17, 2)]
def mark(groups, ch):
    for c0, r0, n in groups:
        for r in (r0, r0 + 1):
            for c in range(c0, c0 + n):
                assert T[r][c] == "G", (c, r, T[r][c])
                T[r][c] = ch
mark(mountains, "M")
mark(hills, "H")
def put(cells, ch):
    for c, r in cells:
        if T[r][c] == "G":
            T[r][c] = ch
forest = [(9, 1), (10, 1), (9, 2), (10, 2), (11, 2), (10, 3),
          (26, 11), (27, 11), (26, 12), (27, 12), (28, 12), (27, 13),
          (14, 12), (15, 12), (14, 13), (15, 13), (16, 13),
          (36, 16), (37, 16), (36, 17), (37, 17), (38, 17), (37, 18),
          (1, 8), (2, 8), (1, 9), (0, 10), (33, 1), (34, 1), (38, 7), (38, 8), (22, 9), (8, 17), (29, 5)]
fields = [(5, 8), (6, 8), (7, 8), (5, 9), (6, 9), (7, 9), (8, 9), (6, 10), (7, 10),
          (22, 12), (23, 12), (24, 12), (22, 13), (23, 13), (24, 13), (23, 11),
          (32, 6), (33, 6), (34, 6), (32, 7), (33, 7), (34, 7), (35, 7),
          (10, 17), (11, 17), (12, 17), (11, 18), (12, 18), (13, 18),
          (1, 13), (2, 13), (2, 14)]
put(forest, "F")

rng = np.random.default_rng(3)
for r in range(ROWS):
    for c in range(COLS):
        if T[r][c] == "G" and rng.random() < 0.18:
            T[r][c] = "P"
units = [{"side": 0, "hex": [6, 11]}, {"side": 1, "hex": [33, 10]}]
for u in units:
    assert T[u["hex"][1]][u["hex"][0]] in "GP"
json.dump({"cols": COLS, "rows": ROWS, "terrain": ["".join(r) for r in T], "units": units},
          open("tools/maps/test_40x20.json", "w"), indent=1)
json.dump({"cols": COLS, "rows": ROWS, "footprint_scale": 0.85, "height_scale": 0.6,
           "mountains": [{"at": [c, r], "n": n, "preset": p} for (c, r, n), p in zip(mountains, MTN_PRESETS)]}, open("tools/maps/test_40x20_mountains.json", "w"))
json.dump({"cols": COLS, "rows": ROWS, "mountains": [{"at": [c, r], "n": n} for c, r, n in hills]},
          open("tools/maps/test_40x20_hills.json", "w"))
print("\n".join("".join(r) for r in T))
