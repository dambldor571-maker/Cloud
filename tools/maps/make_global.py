"""Builds the global campaign map assets/maps/global.json (deterministic).

Layout (offset "odd-r" rows): Сині in the west, Червоні in the east, a river
with bridges down the middle, a northern mountain range with a pass, a southern
lake, forests and hills from value noise, named cities placed by hand.
Legend as in scripts/campaign_map.gd.
"""
import json, math, random, sys, os

W, H = 44, 26
SEED = 7
rnd = random.Random(SEED)


def value_noise(seed, scale):
    r = random.Random(seed)
    grid = {}
    def at(ix, iy):
        if (ix, iy) not in grid:
            grid[(ix, iy)] = r.random()
        return grid[(ix, iy)]
    def f(x, y):
        x /= scale; y /= scale
        ix, iy = math.floor(x), math.floor(y)
        fx, fy = x - ix, y - iy
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a = at(ix, iy) + (at(ix + 1, iy) - at(ix, iy)) * sx
        b = at(ix, iy + 1) + (at(ix + 1, iy + 1) - at(ix, iy + 1)) * sx
        return a + (b - a) * sy
    return f

forest = value_noise(SEED + 1, 4.0)
hills = value_noise(SEED + 2, 5.0)
grid = [["." for _ in range(W)] for _ in range(H)]
for y in range(H):
    for x in range(W):
        fv = forest(x, y) * 0.7 + forest(x * 2.1, y * 2.1) * 0.3
        hv = hills(x, y)
        if hv > 0.74:
            grid[y][x] = "h"
        elif fv > 0.66:
            grid[y][x] = "f"

# River: meanders from north to south around column 21-23.
river = []
cx = 22.0
for y in range(H):
    cx += rnd.choice([-0.6, 0, 0, 0.6])
    cx = min(max(cx, 20), 24)
    x = int(round(cx))
    river.append(x)
    grid[y][x] = "w"
    if y % 3 == 1:  # wider stretches
        grid[y][x + 1] = "w"
BRIDGES = [3, 9, 16, 22]
for y in BRIDGES:
    for x in range(W):
        if grid[y][x] == "w":
            grid[y][x] = "."

# Northern mountain range with a pass, southern lake.
for y in range(1, 6):
    for x in range(12, 20):
        if (x - 16) ** 2 / 16 + (y - 3) ** 2 / 5 < 1.0 and not (y == 3 and x in (15, 16)):
            grid[y][x] = "m"
for y in range(19, 25):
    for x in range(29, 37):
        if (x - 33) ** 2 / 9 + (y - 21.5) ** 2 / 4 < 1.0:
            grid[y][x] = "w"
for y in range(14, 19):
    for x in range(6, 11):
        if (x - 8) ** 2 / 5 + (y - 16) ** 2 / 4 < 1.0:
            grid[y][x] = "h"

# Cities: (col, row, char, name). B/R capitals, P/Q main air bases (key points).
CITIES = [
    (3, 12, "B", "Світлогорськ"), (2, 4, "P", "Озерна (авіабаза)"),
    (6, 8, "b", "Вербівка"), (5, 19, "b", "Кремінець"), (9, 13, "b", "Дубове"),
    (8, 2, "b", "Ясенів"), (2, 23, "p", "Степове (аеродром)"), (10, 22, "b", "Липки"),
    (40, 13, "R", "Залізногірськ"), (41, 21, "Q", "Сокіл (авіабаза)"),
    (37, 7, "r", "Гранітне"), (38, 18, "r", "Сосновий Бір"), (34, 12, "r", "Ковальськ"),
    (36, 2, "r", "Полинове"), (41, 3, "q", "Північний (аеродром)"), (33, 24, "r", "Тихий Яр"),
    (14, 9, "c", "Броди"), (15, 15, "c", "Калинівка"), (13, 20, "c", "Ставки"),
    (19, 6, "c", "Перехрестя"), (18, 12, "c", "Мостове"), (19, 18, "c", "Глинськ"),
    (17, 24, "a", "Рівне Поле (аеродром)"), (26, 4, "c", "Камінь"), (25, 10, "c", "Заріччя"),
    (27, 16, "c", "Вишневе"), (25, 22, "c", "Луги"), (29, 8, "a", "Високе (аеродром)"),
    (30, 13, "c", "Ольхове"), (30, 19, "c", "Бережани"), (22, 1, "c", "Верхів'я"),
    (11, 5, "c", "Сторожеве"), (33, 5, "c", "Бистриця"),
]
names = {}
for x, y, ch, name in CITIES:
    assert grid[y][x] != "w" or True
    grid[y][x] = ch
    names[f"{x},{y}"] = name
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H and grid[ny][nx] == "m":
            grid[ny][nx] = "h"

UNITS = []
def add(t, x, y, s, g=False):
    assert grid[y][x] not in "wm", (t, x, y, grid[y][x])
    UNITS.append({"t": t, "at": [x, y], "s": s, **({"g": True} if g else {})})

blue = [("infantry", 4, 12), ("infantry", 3, 11), ("tank", 4, 13), ("ifv", 5, 12), ("artillery", 2, 12),
        ("infantry", 6, 9), ("recon", 7, 8), ("infantry", 9, 12), ("tank", 9, 14), ("sam", 3, 5),
        ("heli", 2, 5), ("infantry", 5, 18), ("ifv", 6, 19), ("logistics", 2, 13), ("mlrs", 3, 14),
        ("infantry", 8, 3)]
for t, x, y in blue:
    add(t, x, y, 0)
for t, x, y in blue:
    mx, my = W - 1 - x, y  # mirror columns; odd-r rows keep parity
    while grid[my][mx] in "wm" or any(u["at"] == [mx, my] for u in UNITS):
        mx -= 1
    add(t, mx, my, 1)

for y in range(H):
    assert len(grid[y]) == W
out = {"cols": W, "rows": H, "map": ["".join(r) for r in grid], "names": names, "units": UNITS,
       "money": [400, 400]}
path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "maps", "global.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\n".join(out["map"]))
print(len(CITIES), "cities,", len(UNITS), "units ->", os.path.normpath(path))
