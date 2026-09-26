#!/usr/bin/env python3
"""Terrain generator for Frontline: mountain and hill presets (2 x N hexes) from real
elevation data, preset galleries and whole baked game maps.

  terrain_gen.py fetch                              download elevation data (once)
  terrain_gen.py mountains --size 2x3 --count 5     add new mountain presets (+ gallery)
  terrain_gen.py hills --size 2x4 --count 2         add new hill presets (+ gallery)
  terrain_gen.py replace m2x3_07 [--pick 2]         regenerate one preset, keep its id
  terrain_gen.py gallery mountains [--size 3]       render the preset galleries into docs/
  terrain_gen.py map test_40x20                     compose + bake tools/maps/<name>*.json
                                                    into assets/maps/<name>/ for the game

Presets are deterministic: a preset remembers where in the elevation data it comes
from (area, place, rotation), so the same library always gives the same maps.
Rendering needs Godot 4.3 (env GODOT) and xvfb-run.
"""
import argparse, io, json, math, os, shutil, subprocess, sys, tempfile, urllib.request, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import terrain_lib as tl  # noqa: E402

GODOT = os.environ.get("GODOT", shutil.which("godot") or "godot")
TEXTURES = os.path.join(HERE, "textures")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Elevation data areas (lat, lon); 32 x 32 km each.
AREAS = {
    "alps": (46.55, 8.0), "montblanc": (45.87, 6.90), "valais": (46.02, 7.78), "bernina": (46.38, 9.92),
    "ecrins": (44.93, 6.33), "dolomites": (46.48, 11.85), "grossglockner": (47.07, 12.69),
    "ortler": (46.51, 10.54), "paradiso": (45.52, 7.27), "silvretta": (46.85, 10.10),
    "todi": (46.81, 8.91), "zillertal": (47.03, 11.80), "otztal": (46.85, 10.85),
    "emmental": (46.95, 7.75),
}

# Approved looks. Hills: Emmental, low and soft; mountains: Alpine massifs.
KINDS = {
    "mountains": {"dir": "tools/mountain_presets", "prefix": "m", "hmax": 15.0,
                  "areas": [a for a in AREAS if a != "emmental"],
                  "massif": {"km_per_hex": 2.5}},
    "hills": {"dir": "tools/hill_presets", "prefix": "h", "hmax": 3.2, "areas": ["emmental"],
              "massif": {"km_per_hex": 1.6, "fade_r": 0.95, "fade_sig": 0.55, "smooth": 2.0, "base_pct": 20}},
}


def run(cmd, env=None):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


# --- elevation data -----------------------------------------------------------

def fetch(_args):
    os.makedirs(tl.DEM_DIR, exist_ok=True)
    z = 12

    def tile(x, y):
        url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
        a = np.asarray(Image.open(io.BytesIO(urllib.request.urlopen(url, timeout=60).read())).convert("RGB"))
        a = a.astype(np.float64)
        return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768

    for name, (lat, lon) in AREAS.items():
        path = os.path.join(tl.DEM_DIR, name + ".npy")
        if os.path.exists(path):
            continue
        n = 2 ** z
        fx = (lon + 180) / 360 * n
        fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
        mpp = 40075016.7 * math.cos(math.radians(lat)) / n / 256
        half = 32 * 1000 / 2 / mpp / 256
        x0, x1, y0, y1 = int(fx - half), int(fx + half), int(fy - half), int(fy + half)
        big = np.vstack([np.hstack([tile(x, y) for x in range(x0, x1 + 1)]) for y in range(y0, y1 + 1)])
        cx, cy, hp = int((fx - x0) * 256), int((fy - y0) * 256), int(32 * 1000 / 2 / mpp)
        a = big[cy - hp:cy + hp, cx - hp:cx + hp]
        m = ndimage.median_filter(a, 7)  # the data has a few spikes
        bad = np.abs(a - m) > 150
        a[bad] = m[bad]
        np.save(path, a)
        open(os.path.join(tl.DEM_DIR, name + ".mpp"), "w").write(str(mpp))
        print(name, a.shape, round(a.min()), round(a.max()))


# --- presets ---------------------------------------------------------------------

LIB_OVERRIDE = None  # --lib: work on another library folder (e.g. a test set)


def lib_path(kind, main=False):
    if LIB_OVERRIDE and not main:
        return os.path.join(ROOT, LIB_OVERRIDE)
    return os.path.join(ROOT, KINDS[kind]["dir"])


def load_index(kind):
    p = os.path.join(lib_path(kind), "index.json")
    return json.load(open(p)) if os.path.exists(p) else []


def save_index(kind, index):
    index.sort(key=lambda e: (e["size"][1], e["id"]))
    json.dump(index, open(os.path.join(lib_path(kind), "index.json"), "w"), indent=1)


def used_places(kind, index, area):
    """DEM places already taken in this area (also in the main library when --lib is
    used), so new presets are always different mountains."""
    k = KINDS[kind]["massif"]["km_per_hex"]
    mpp = float(open(os.path.join(tl.DEM_DIR, area + ".mpp")).read())
    res = []
    if LIB_OVERRIDE:
        p = os.path.join(lib_path(kind, main=True), "index.json")
        index = index + (json.load(open(p)) if os.path.exists(p) else [])
    for e in index:
        if e["area"] == area:
            n = e["size"][1]
            ln = e.get("dem_len") or int(k * 1000 * ((n - 1) + 1.9 / math.sqrt(3)) / mpp)
            res.append((e["dem_xy"][0], e["dem_xy"][1], ln))
    return res


def make_preset(kind, n, area, pick, used):
    """Render one 2 x n preset. Returns (heights crop, index entry without id)."""
    K = KINDS[kind]
    g = tl.Grid(n + 7, 5)
    hexes = tl.group(2, 2, n)
    cen = np.array([tl.hw(c, r) for c, r in hexes]).mean(0)
    h, info = tl.massif(g, hexes, area, used, hmax=K["hmax"], pick=pick, **K["massif"])
    ys, xs = np.nonzero(h > 0.005)
    y0, y1, x0, x1 = ys.min() - 2, ys.max() + 3, xs.min() - 2, xs.max() + 3
    crop = h[y0:y1, x0:x1]
    entry = {"size": [2, n], "hmax": K["hmax"], "step": tl.STEP,
             "origin": [round(g.x0 + x0 * tl.STEP - cen[0], 3), round(g.z0 + y0 * tl.STEP - cen[1], 3)],
             "shape": list(crop.shape), "pick": pick, **info}
    return crop, entry


def write_preset(kind, pid, crop, entry):
    K = KINDS[kind]
    Image.fromarray((np.clip(crop / K["hmax"], 0, 1) * 65535).astype(np.uint16)).save(
        os.path.join(lib_path(kind), pid + ".png"))
    entry["id"] = pid


def add_presets(args):
    kind = args.kind
    K = KINDS[kind]
    n = int(args.size.lower().split("x")[1])
    if int(args.size.lower().split("x")[0]) != 2 or n < 2:
        sys.exit("size must be 2xN with N >= 2")
    os.makedirs(lib_path(kind), exist_ok=True)
    index = load_index(kind)
    taken = {e["id"] for e in index}
    new_ids = []
    for i in range(args.count):
        if args.area:
            area = args.area
        else:  # the area with the fewest presets of this kind
            counts = {a: sum(1 for e in index if e["area"] == a) for a in K["areas"]}
            area = min(K["areas"], key=lambda a: (counts[a], K["areas"].index(a)))
        v = 1
        while f"{K['prefix']}2x{n}_{v:02d}" in taken:
            v += 1
        pid = f"{K['prefix']}2x{n}_{v:02d}"
        crop, entry = make_preset(kind, n, area, args.pick, used_places(kind, index, area))
        write_preset(kind, pid, crop, entry)
        index.append(entry)
        taken.add(pid)
        new_ids.append(pid)
        save_index(kind, index)
        print(pid, entry["area"], "angle", entry["angle"], flush=True)
    if not args.no_gallery:
        gallery_render(kind, new_ids, os.path.join(ROOT, "docs", f"{kind}_new.png"))


def replace_preset(args):
    pid = args.id
    kind = "mountains" if pid.startswith("m") else "hills"
    index = load_index(kind)
    old = next(e for e in index if e["id"] == pid)
    rest = [e for e in index if e["id"] != pid]
    pick = args.pick if args.pick is not None else old.get("pick", 0) + 1
    area = args.area or old["area"]
    crop, entry = make_preset(kind, old["size"][1], area, pick, used_places(kind, rest, area))
    write_preset(kind, pid, crop, entry)
    save_index(kind, rest + [entry])
    print(pid, "->", area, "pick", pick)
    if not args.no_gallery:
        gallery_render(kind, [pid], os.path.join(ROOT, "docs", f"{kind}_replaced.png"))


# --- composing and rendering ---------------------------------------------------

def compose(cfg, kind, out_dir):
    """Place presets on a map (2 x N groups, top-left hex `at`) and stitch touching ones."""
    pd = lib_path(kind)
    lib = {e["id"]: e for e in load_index(kind)}
    g = tl.Grid(cfg.get("cols", 11), cfg.get("rows", 8))
    use, parts = {}, []
    fs, hs = cfg.get("footprint_scale", 1.0), cfg.get("height_scale", 1.0)
    for m in cfg["mountains"]:
        (c0, r0), n = m["at"], m["n"]
        pid = m.get("preset")
        if pid is None:  # least used preset of this size; ties broken by position
            pid = sorted((use.get(e, 0), zlib.crc32(f"{e}{c0},{r0}".encode()), e)
                         for e in lib if lib[e]["size"][1] == n)[0][2]
        use[pid] = use.get(pid, 0) + 1
        e = lib[pid]
        h = np.asarray(Image.open(os.path.join(pd, pid + ".png"))).astype(np.float32) / 65535 * e["hmax"]
        ox, oz = e["origin"]
        if fs != 1.0:
            h = np.asarray(Image.fromarray(h).resize((max(2, round(h.shape[1] * fs)), max(2, round(h.shape[0] * fs))),
                                                     Image.BILINEAR))
            ox, oz = ox * fs, oz * fs
        h = h * hs
        if r0 & 1:  # presets are made for an even top row; mirror on odd rows
            h = h[:, ::-1]
            ox = -(ox + (h.shape[1] - 1) * tl.STEP)
        P = np.array([tl.hw(c, r) for c, r in tl.group(c0, r0, n)])
        cen = P.mean(0)
        ix, iz = int(round((cen[0] + ox - g.x0) / tl.STEP)), int(round((cen[1] + oz - g.z0) / tl.STEP))
        H = np.zeros((g.nz, g.nx))
        y0, x0 = max(iz, 0), max(ix, 0)
        y1, x1 = min(iz + h.shape[0], g.nz), min(ix + h.shape[1], g.nx)
        H[y0:y1, x0:x1] = h[y0 - iz:y1 - iz, x0 - ix:x1 - ix]
        parts.append((H, P))
    os.makedirs(out_dir, exist_ok=True)
    H = tl.stitch(g, parts, hs) if kind == "mountains" else np.max([p[0] for p in parts] + [np.zeros((g.nz, g.nx))], axis=0)
    tl.save_field(H, g, out_dir)


def godot(script, env_extra):
    """Run one of the render scripts (copied into the project root for res:// access)."""
    tmp = os.path.join(ROOT, "_terrain_tmp.gd")
    shutil.copy(os.path.join(HERE, script), tmp)
    env = dict(os.environ, TEX=TEXTURES, EW="1", **env_extra)
    try:
        run(["xvfb-run", "-a", "-s", "-screen 0 640x480x24", GODOT, "--path", ROOT, "--rendering-method",
             "forward_plus", "--rendering-driver", "vulkan", "-s", "res://_terrain_tmp.gd"], env)
    finally:
        os.remove(tmp)


GALLERY_COLS = {2: [1, 4, 7], 3: [0, 4, 8], 4: [1, 6], 5: [0, 6], 6: [2]}


def gallery_render(kind, ids, out_png):
    """Render presets on open grassland, labelled, into one sheet."""
    lib = {e["id"]: e for e in load_index(kind)}
    by_n = {}
    for pid in ids:
        by_n.setdefault(lib[pid]["size"][1], []).append(pid)
    font = ImageFont.truetype(FONT, 34)
    R = tl.R
    mid = (R * math.sqrt(3) * 10.5 / 2, R * 1.5 * 7 / 2)
    se = math.sin(math.radians(65))
    shots = []
    with tempfile.TemporaryDirectory() as tmp:
        for n, lst in sorted(by_n.items()):
            slots = [(c, r) for r in (1, 5) for c in GALLERY_COLS.get(n, [1])]
            for i in range(0, len(lst), len(slots)):
                chunk = lst[i:i + len(slots)]
                if len(chunk) == 1:  # a single preset in the middle of the scene
                    slots = [((11 - n) // 2, 3)]
                cfg = {"cols": 11, "rows": 8, "mountains": [{"at": list(s), "n": n, "preset": p}
                                                            for s, p in zip(slots, chunk)]}
                fdir = os.path.join(tmp, f"f{n}_{i}")
                compose(cfg, kind, fdir)
                png = os.path.join(tmp, f"g{n}_{i}.png")
                env = {"MTN": fdir, "OUT": png}
                if kind == "hills":
                    env["HILLS"] = "1"
                godot("render_scene.gd", env)
                im = Image.open(png).convert("RGB")
                d = ImageDraw.Draw(im)
                for m in cfg["mountains"]:
                    (c0, r0) = m["at"]
                    P = [tl.hw(c, r) for c, r in tl.group(c0, r0, n)]
                    x = sum(p[0] for p in P) / len(P)
                    z = max(p[1] for p in P) + R * 0.9
                    sx, sy = 800 + (x - mid[0]) * 17.45, min(500 + (z - mid[1]) * se * 17.45, 955)
                    t = m["preset"].replace(KINDS[kind]["prefix"] + "2x", "2×").replace("_", " №")
                    d.text((sx - d.textlength(t, font=font) / 2, sy), t, font=font, fill=(255, 255, 255),
                           stroke_width=4, stroke_fill=(0, 0, 0))
                shots.append(im.resize((800, 500), Image.LANCZOS))
    cols = 1 if len(shots) == 1 else 2
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 810 - 10, rows * 510 - 10), (20, 20, 20))
    for k, im in enumerate(shots):
        sheet.paste(im, ((k % cols) * 810, (k // cols) * 510))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sheet.save(out_png)
    print("gallery:", os.path.relpath(out_png, ROOT))


def gallery(args):
    index = load_index(args.kind)
    sizes = [args.size] if args.size else sorted({e["size"][1] for e in index})
    outs = []
    for n in sizes:
        ids = [e["id"] for e in index if e["size"][1] == n]
        out = os.path.join(ROOT, "docs", f"{args.kind[:-1]}_presets_2x{n}.png")
        if args.one:
            out = os.path.join(tempfile.gettempdir(), f"_gal_{args.kind}_{n}.png")
        gallery_render(args.kind, ids, out)
        outs.append((n, out))
    if args.one:  # everything in one tall image, a title above each size
        font = ImageFont.truetype(FONT, 44)
        sheets = [(n, Image.open(o).convert("RGB")) for n, o in outs]
        W = max(s.width for _, s in sheets)
        H = sum(s.height + 80 for _, s in sheets)
        big = Image.new("RGB", (W, H), (20, 20, 20))
        y = 0
        for n, s in sheets:
            ImageDraw.Draw(big).text((20, y + 16), f"2×{n}", font=font, fill=(255, 255, 255))
            big.paste(s, (0, y + 80))
            y += s.height + 80
        big.save(os.path.join(ROOT, args.one))
        print("gallery:", args.one)


# --- whole maps ---------------------------------------------------------------------

def bake_map(args):
    name = args.name
    mdir = os.path.join(ROOT, "tools", "maps")
    layout_path = os.path.join(mdir, name + ".json")
    layout = json.load(open(layout_path))
    dst = os.path.join(ROOT, "assets", "maps", name)
    with tempfile.TemporaryDirectory() as tmp:
        empty = {"cols": layout["cols"], "rows": layout["rows"], "mountains": []}
        for kind, suffix in (("mountains", "_mountains.json"), ("hills", "_hills.json")):
            p = os.path.join(mdir, name + suffix)
            compose(json.load(open(p)) if os.path.exists(p) else empty, kind, os.path.join(tmp, kind))
        out = os.path.join(tmp, "out")
        os.makedirs(out)
        godot("bake_map.gd", {"LAYOUT": layout_path, "MTN": os.path.join(tmp, "mountains"),
                              "HILL": os.path.join(tmp, "hills"), "OUT": out})
        meta = json.load(open(os.path.join(out, "map.json")))
        im = Image.open(os.path.join(out, "map.png")).convert("RGB")
    # cut into tiles for the game (<= 2048 px, JPG) and write the game's map.json
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(dst):
        if f.startswith("tile_") and f.endswith(".jpg"):
            os.remove(os.path.join(dst, f))
    ppm, (ox, oz) = meta["px_per_m"], meta["origin_m"]
    W, H = im.size
    nx, ny = math.ceil(W / 2048), math.ceil(H / 2048)
    tw, th = math.ceil(W / nx), math.ceil(H / ny)
    tiles = []
    for j in range(ny):
        for i in range(nx):
            x0, y0 = i * tw, j * th
            x1, y1 = min(W, x0 + tw), min(H, y0 + th)
            f = f"tile_{i}_{j}.jpg"
            im.crop((x0, y0, x1, y1)).save(os.path.join(dst, f), quality=88, optimize=True)
            tiles.append({"file": f, "rect_m": [round(ox + x0 / ppm, 4), round(oz + y0 / ppm, 4),
                                                round((x1 - x0) / ppm, 4), round((y1 - y0) / ppm, 4)]})
    game_meta = {"cols": layout["cols"], "rows": layout["rows"], "terrain": layout["terrain"],
                 "units": [dict({"type": "tank"}, **u) for u in layout["units"]], "hex_r_m": meta["hex_r_m"],
                 "heights_m": meta["heights_m"], "tiles": tiles}
    json.dump(game_meta, open(os.path.join(dst, "map.json"), "w"))
    im.resize((2000, round(2000 * H / W)), Image.LANCZOS).save(os.path.join(ROOT, "docs", f"map_{name}.png"))
    # import the tiles with mipmaps (the map is shown far zoomed out)
    run([GODOT, "--headless", "--path", ROOT, "--import"])
    for f in os.listdir(dst):
        if f.endswith(".jpg.import"):
            p = os.path.join(dst, f)
            s = open(p).read()
            if "mipmaps/generate=false" in s:
                open(p, "w").write(s.replace("mipmaps/generate=false", "mipmaps/generate=true"))
    run([GODOT, "--headless", "--path", ROOT, "--import"])
    print(f"map: assets/maps/{name}/ ({len(tiles)} tiles), preview docs/map_{name}.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch").set_defaults(func=fetch)
    for kind in ("mountains", "hills"):
        p = sub.add_parser(kind)
        p.add_argument("--size", required=True, help="2xN, e.g. 2x3")
        p.add_argument("--count", type=int, default=1)
        p.add_argument("--area", choices=KINDS[kind]["areas"])
        p.add_argument("--pick", type=int, default=0, help="0 = best fitting place, k = k-th alternative")
        p.add_argument("--no-gallery", action="store_true")
        p.set_defaults(func=add_presets, kind=kind)
    p = sub.add_parser("replace")
    p.add_argument("id")
    p.add_argument("--pick", type=int)
    p.add_argument("--area")
    p.add_argument("--no-gallery", action="store_true")
    p.set_defaults(func=replace_preset)
    p = sub.add_parser("gallery")
    p.add_argument("kind", choices=["mountains", "hills"])
    p.add_argument("--size", type=int)
    p.add_argument("--one", metavar="FILE", help="all sizes in one image, e.g. docs/all.png")
    p.set_defaults(func=gallery)
    p = sub.add_parser("map")
    p.add_argument("name")
    p.set_defaults(func=bake_map)
    ap.add_argument("--lib", help="library folder instead of the default (e.g. tools/mountain_presets_test)")
    args = ap.parse_args()
    global LIB_OVERRIDE
    LIB_OVERRIDE = args.lib
    args.func(args)


if __name__ == "__main__":
    main()
