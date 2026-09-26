"""Place mountain presets on a map and stitch touching mountains (A2).
config: {"cols": 11, "rows": 8, "mountains": [{"at": [col,row], "n": 3, "preset": "m2x3_04"?}, ...]}
A mountain is 2 rows x n hexes with its top-left hex at `at`. Presets are made for an
even top row; on odd rows they are mirrored. Without "preset" one is chosen so that
the same preset repeats as late as possible.
Usage: compose_mountains.py config.json presets_dir out_dir"""
import json, sys, zlib
import numpy as np
from PIL import Image
from mountains_lib import Grid, group, hw, stitch, save_field, STEP

cfg = json.load(open(sys.argv[1])); PD = sys.argv[2]; OUT = sys.argv[3]
lib = {e["id"]: e for e in json.load(open(PD + "/index.json"))}
g = Grid(cfg.get("cols", 11), cfg.get("rows", 8))
use = {}
parts = []
for m in cfg["mountains"]:
    c0, r0 = m["at"]; n = m["n"]
    pid = m.get("preset")
    if pid is None:  # least used preset of this size; ties broken by position
        cands = sorted((use.get(e, 0), zlib.crc32(f"{e}{c0},{r0}".encode()), e) for e in lib if lib[e]["size"][1] == n)
        pid = cands[0][2]
    use[pid] = use.get(pid, 0) + 1
    e = lib[pid]
    h = np.asarray(Image.open(f"{PD}/{pid}.png")).astype(np.float32) / 65535 * e["hmax"]
    ox, oz = e["origin"]
    if r0 & 1:  # odd top row: mirror across the group's centre
        h = h[:, ::-1]
        ox = -(ox + (h.shape[1] - 1) * STEP)
    hexes = group(c0, r0, n)
    P = np.array([hw(c, r) for c, r in hexes])
    cen = P.mean(0)
    ix = int(round((cen[0] + ox - g.x0) / STEP)); iz = int(round((cen[1] + oz - g.z0) / STEP))
    H = np.zeros((g.nz, g.nx))
    y0, x0 = max(iz, 0), max(ix, 0)
    y1, x1 = min(iz + h.shape[0], g.nz), min(ix + h.shape[1], g.nx)
    H[y0:y1, x0:x1] = h[y0 - iz:y1 - iz, x0 - ix:x1 - ix]
    parts.append((H, P))
    print(pid, "at", c0, r0, "mirrored" if r0 & 1 else "")
save_field(stitch(g, parts), g, OUT)
