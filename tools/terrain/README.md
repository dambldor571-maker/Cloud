# Terrain generator

One tool for the map terrain: mountain and hill presets (always 2 x N hexes) cut from
real elevation data, preset galleries, and whole baked maps for the game.

```
python3 tools/terrain/terrain_gen.py fetch                         # elevation data -> tools/terrain/.cache (once)
python3 tools/terrain/terrain_gen.py mountains --size 2x3 --count 5  # new presets + docs/mountains_new.png
python3 tools/terrain/terrain_gen.py hills --size 2x4 --count 2
python3 tools/terrain/terrain_gen.py replace m2x3_07              # swap one preset for the next best place
python3 tools/terrain/terrain_gen.py gallery mountains --size 3    # docs/mountain_presets_2x3.png
python3 tools/terrain/terrain_gen.py map test_40x20               # tools/maps/test_40x20*.json -> assets/maps/test_40x20/
```

- Libraries: `tools/mountain_presets/`, `tools/hill_presets/` (16-bit heightmaps + `index.json`).
  Each preset records its source (area, place, rotation, pick), so results are reproducible.
- Options: `--area` (e.g. `montblanc`, `dolomites`), `--pick k` (k-th best alternative place),
  `--no-gallery`.
- A map is `tools/maps/<name>.json` (terrain letters G P F H M, start units) plus
  `<name>_mountains.json` / `<name>_hills.json` (groups: `at` = top-left hex, `n`, optional `preset`,
  map-wide `footprint_scale` / `height_scale`). Touching mountains are joined by real ridges.
- Needs Python 3 with numpy, scipy, Pillow; Godot 4.3 (`GODOT=/path/to/godot`) and `xvfb-run`
  for rendering. Textures (CC0, Poly Haven / ambientCG) are in `textures/`.
