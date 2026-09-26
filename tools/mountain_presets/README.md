# Mountain presets (2 x N hexes)

Real Alpine massifs (elevation data: AWS Terrain Tiles / Terrarium, 13 areas), cut to fit
2 x N hex mountains. Approved look: "A2" — presets + wide rocky saddles where mountains touch.

- `m2x{N}_{NN}.png` — 16-bit heightmap, 0.1 m per pixel, value 65535 = `hmax` metres.
- `index.json` — per preset: size, hmax, `origin` (top-left of the PNG relative to the
  group's centre, metres), source area / angle.
- Presets are made for a mountain whose top row is even; on odd rows they are mirrored.

Counts: 2x2: 16, 2x3: 12, 2x4: 10, 2x5: 8, 2x6: 6 (x2 with mirroring).

Pipeline (tools/references): `dem_fetch2.py` (download areas) → `make_mountain_presets.py`
(build library) → `compose_mountains.py` (place on a map + stitch) → render.
