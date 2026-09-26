"""Cut a baked map (bake_map.gd output) into JPG tiles for the game and write the
game's map.json: terrain letters per hex, start units, ground height per hex and
where each tile goes (metres; the game scales by Hex.SIZE / hex_r_m).
Usage: export_game_map.py <bake out dir> <layout.json> <assets/maps/NAME>"""
import json, math, os, sys
from PIL import Image

src, layout_path, dst = sys.argv[1:4]
meta = json.load(open(os.path.join(src, "map.json")))
layout = json.load(open(layout_path))
im = Image.open(os.path.join(src, "map.png")).convert("RGB")
os.makedirs(dst, exist_ok=True)
for f in os.listdir(dst):
    if f.startswith("tile_"):
        os.remove(os.path.join(dst, f))
ppm = meta["px_per_m"]
ox, oz = meta["origin_m"]
W, H = im.size
nx, ny = math.ceil(W / 2048), math.ceil(H / 2048)
tw, th = math.ceil(W / nx), math.ceil(H / ny)
tiles = []
for j in range(ny):
    for i in range(nx):
        x0, y0 = i * tw, j * th
        x1, y1 = min(W, x0 + tw), min(H, y0 + th)
        name = f"tile_{i}_{j}.jpg"
        im.crop((x0, y0, x1, y1)).save(os.path.join(dst, name), quality=88, optimize=True)
        tiles.append({"file": name, "rect_m": [round(ox + x0 / ppm, 4), round(oz + y0 / ppm, 4),
                                               round((x1 - x0) / ppm, 4), round((y1 - y0) / ppm, 4)]})
out = {"cols": layout["cols"], "rows": layout["rows"], "terrain": layout["terrain"],
       "units": [dict(u, type="tank") for u in layout["units"]], "hex_r_m": meta["hex_r_m"],
       "heights_m": meta["heights_m"], "tiles": tiles}
json.dump(out, open(os.path.join(dst, "map.json"), "w"))
print(len(tiles), "tiles", tw, "x", th)
