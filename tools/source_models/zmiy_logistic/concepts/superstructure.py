# -*- coding: utf-8 -*-
"""Надбудова-портал над палубою для Starlink, камер і антен — три концепти футуристичного дизайну
поверх готової моделі (основну модель не змінюють):
    blender -b zmiy_logistic.blend --python concepts/superstructure.py              # обраний варіант (B4)
    ZMIY_TOPS=all blender -b zmiy_logistic.blend --python concepts/superstructure.py  # усі концепти
Додає об'єкт Top_B4 (обраний; з ZMIY_TOPS=all — і решту Top_*; дочірні до Zmiy_Logistic) і пакує сторінку перегляду разом із ними
(viewer/pack_viewer.py) — у переглядачі варіанти перемикаються.

Спільне для всіх варіантів (інженерна частина):
- портал стоїть посередині палуби, на центрі ваги (y ≈ −0,12) — машина на схилі не перекидається від
  верхньої ваги, вантаж ставлять під портал і перед/за ним; висота над палубою ~0,7–0,8 м, борти вільні;
- кріплення без зварювання до палуби: на кожен бортик — сідло з листа 6 мм (П-подібне, обхоплює верх
  бортика) на 3 болтах M10 крізь наявні отвори Ø11 бортика (y = −0,285 / −0,117 / +0,051, z = 0,956);
- ноги на шарнірі (вісь уздовж X) — портал складається назад на палубу для перевезення й маскування:
  висота машини тоді ~1,1 м замість ~1,7 м; у робочому положенні — фіксатор (палець із кільцем);
- кабелі — всередині порожнистих ніг до гермовводу на сідлі, далі по бортику вниз у корпус;
- Starlink Mini (298 × 259 × 38,5 мм) лежить горизонтально в найвищій точці — небо без перешкод.

A «Крило»: дві гранчасті ноги-леза з нахилом усередину й назад і поперечина-крило з гранчастим профілем і
          стрілоподібними кінцями; уздовж передньої кромки — темна скляна смуга-«візор» з камерами,
          під кінцями крила — бокові камери, на кінцях — штирові антени, ззаду — GNSS.
B «Ореол»: суцільна гнута стрічка 160 × 50 мм з великими скосами на плечах (одна деталь від сідла до
          сідла); на плечах — гранчасті сенсорні вузли з кільцевим склом (камери на 360°) і антенами,
          Starlink на вершині. Власник обрав B і попросив трубчастий каркас — варіації (будуються зараз):
  B1 кругла труба Ø60 гнута;  B2 квадратна 60 × 60 зі зварними стиками;  B3 «драбина» з двох круглих Ø42;
  B4 квадратна 50 × 50 + круглі розкоси Ø30 назад;  B5 ферма з двох квадратних 40 × 40 і перфорованої стінки.
  Власник обрав B4 і попросив: прибрати поки Starlink, сенсорні вузли й камеру; раму — прямокутний портал (ноги
  майже вертикальні, пряма поперечина); портал — якнайдалі вперед з урахуванням отворів (див. variant_b4).
C «Козирок»: ноги й широкий плаский дах 1,2 × 0,7 м з гранчастими кромками, трохи нахилений уперед;
          Starlink урізаний у дах, спереду — скляний візор, по кутах — камерні купола, антени ззаду.
          Дах — каркас для сітки від FPV над вантажем (сітку не моделювали).
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # папка моделі
sys.path.insert(0, MODEL)
sys.path.insert(0, os.path.join(MODEL, "viewer"))
import zmiy_build as zb      # noqa: E402

P = zb.P
zb.COLL = bpy.data.collections["Zmiy_Logistic"]
zb.PARTS.clear()
for k, v in zb.MAT_DEF.items():
    zb.MAT[k] = bpy.data.materials.get(v[0]) or zb.make_material(*v)
zb.MAT['glass'] = zb.make_material("Top_Glass", "#0A0C0D", 0.08, 0.0)     # вікна камер, візори
zb.MAT['radome'] = zb.make_material("Top_Radome", "#5E625A", 0.62, 0.0)   # кришка Starlink (фарбована)
ROOT = bpy.data.objects["Zmiy_Logistic"]

YC = -0.117                          # площина порталу — центр ваги, середній отвір Ø11 бортика
XW = P['side_x'] - P['wall_t'] / 2   # серединна площина бортика
ZW = P['wall_z1']                    # верх бортика 0,990
ZH = 1.026                           # вісь шарніра ніг
HOLES = (-0.285, -0.117, 0.051)      # отвори Ø11 у бортиках на z 0,956


# =================================================================== допоміжне
def octo(cy, cz, a, b, c):
    """Восьмикутний переріз (y, z) або (x, y): півосі a, b, скоси c."""
    return [(cy + a, cz + b - c), (cy + a - c, cz + b), (cy - a + c, cz + b), (cy - a, cz + b - c),
            (cy - a, cz - b + c), (cy - a + c, cz - b), (cy + a - c, cz - b), (cy + a, cz - b + c)]


def solid(group, name, pts, mat='paint', bev=0.004, segs=2):
    return zb.convex_solid(group, name, [Vector(p) for p in pts], mat=mat, bev=bev, segs=segs)


def cyl(group, name, p0, p1, r, mat, segs=20):
    bm = bmesh.new()
    zb.bm_cyl(bm, Vector(p0), Vector(p1), r, segs)
    return zb.bm_to_part(group, name, bm, [mat], angle=40.0)


def miter_rings(path, w, d, yoff=0.0):
    """Кути прямокутного перерізу w (у площині XZ) × d (уздовж Y) у кожній вершині ламаної в площині
    y = YC + yoff; у внутрішніх вершинах — переріз по бісектрисі (зварний стик під кутом, «мітра»)."""
    pts = [Vector((x, YC + yoff, z)) for x, z in path]
    ny = Vector((0, 1, 0))
    rings = []
    for i, p in enumerate(pts):
        tans = []
        if i > 0:
            tans.append((p - pts[i - 1]).normalized())
        if i < len(pts) - 1:
            tans.append((pts[i + 1] - p).normalized())
        ns = [t.cross(ny).normalized() for t in tans]
        m = (sum(ns, Vector()) / len(ns)).normalized()
        k = 1.0 / max(m.dot(ns[0]), 0.3)
        rings.append([p + m * (sw * w / 2 * k) + ny * (sd * d / 2) for sw, sd in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    return rings


def sweep(group, name, path, w, d, mat='paint', bev=0.004, yoff=0.0):
    """Брус/стрічка/квадратна труба: прямокутний переріз уздовж ламаної, стики під кутом."""
    bm = bmesh.new()
    rings = [[bm.verts.new(q) for q in r] for r in miter_rings(path, w, d, yoff)]
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new([a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]])
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=2, affect='EDGES', clamp_overlap=True)
    return zb.bm_to_part(group, name, bm, [mat], angle=35.0)


def miter_welds(group, path, w, d, yoff=0.0):
    """Зварні шви по стиках квадратної труби (валик навколо перерізу у внутрішніх вершинах)."""
    for ring in miter_rings(path, w + 0.002, d + 0.002, yoff)[1:-1]:
        zb.tube(group, "Weld", ring + [ring[0]], 0.0032, mat='paint', res=1, caps=False)


def round_tube(group, name, path, r, bend, yoff=0.0):
    """Кругла труба, гнута з радіусом bend по осі (на трубогибі, без зварних стиків)."""
    return zb.tube(group, name, [(x, YC + yoff, z) for x, z in path], r, bend=bend, mat='paint', res=4)


def along(path, t):
    """Точка на ламаній за часткою довжини t (0…1)."""
    pts = [Vector(q) for q in path]
    seg = [(a - b).length for a, b in zip(pts[1:], pts)]
    L = sum(seg) * t
    for a, b, l in zip(pts, pts[1:], seg):
        if L <= l:
            return a.lerp(b, L / l)
        L -= l
    return pts[-1]


def starlink(group, cx, cy, z0, along_x=False):
    """Starlink Mini горизонтально: корпус 259 × 298 × 38,5 мм на тонкій рамці (along_x — довгим боком уздовж X)."""
    hx, hy = (0.149, 0.1295) if along_x else (0.1295, 0.149)
    solid(group, "SL_Frame", [(cx + sx * (hx + 0.011), cy + sy * (hy + 0.011), z) for sx in (-1, 1) for sy in (-1, 1)
                              for z in (z0, z0 + 0.008)], mat='tube', bev=0.002, segs=1)
    zb.box(group, "SL_Dish", cx - hx, cx + hx, cy - hy, cy + hy, z0 + 0.008, z0 + 0.0465,
           mat='radome', bev=0.008, segs=3)


def ring(group, name, c, r, rw, axis='Z', mat='zinc', segs=20):
    """Кільце (тор) радіуса r з дроту rw; axis — вісь кільця."""
    pts = []
    for k in range(segs + 1):
        a = 2 * math.pi * k / segs
        u, v = r * math.cos(a), r * math.sin(a)
        pts.append((c[0] + u, c[1] + v, c[2]) if axis == 'Z' else
                   (c[0], c[1] + u, c[2] + v) if axis == 'X' else (c[0] + u, c[1], c[2] + v))
    return zb.tube(group, name, pts, rw, mat=mat, res=1, caps=False)


def whip(group, x, y, z, lean=0.0, h=0.42):
    """Штирова антена: роз'єм N на основі, гумовий корпус, пружина (витки), штир із наконечником."""
    cyl(group, "Ant_Conn", (x, y, z), (x, y, z + 0.012), 0.011, 'zinc', 6)
    cyl(group, "Ant_Base", (x, y, z + 0.012), (x, y, z + 0.045), 0.013, 'dark', 16)
    cyl(group, "Ant_Spring", (x, y, z + 0.045), (x, y, z + 0.085), 0.0065, 'tube', 12)
    for k in range(6):
        ring(group, "Ant_Coil", (x, y, z + 0.049 + k * 0.0065), 0.0075, 0.0016, mat='tube', segs=12)
    tip = (x + lean * h, y, z + 0.085 + h)
    cyl(group, "Ant_Whip", (x, y, z + 0.085), tip, 0.0035, 'tube', 8)
    cyl(group, "Ant_Tip", tip, (tip[0], tip[1], tip[2] + 0.010), 0.0055, 'dark', 10)


def lug(group, name, x, yc, zc, z0, hw, r, t, hole, mat='paint'):
    """Проушина в площині YZ: основа ±hw на висоті z0, заокруглений верх радіуса r навколо (yc, zc), отвір."""
    pts = [(yc - hw, z0), (yc + hw, z0)] + [(yc + r * math.cos(a), zc + r * math.sin(a))
                                           for a in (math.pi * k / 12 for k in range(13))]
    return zb.plate(group, name, pts, [zb.circle(yc, zc, hole, 16)], t=t,
                    M=zb.frame((x - t / 2, 0, 0), (0, 1, 0), (0, 0, 1)), mat=mat, bev=0.0012)


def pin(group, name, x0, x1, y, z, r, head_at, clip=True):
    """Палець уздовж X: стрижень, головка з шайбою на кінці head_at, з іншого — шайба й шплінт-кільце."""
    cyl(group, name, (x0, y, z), (x1, y, z), r, 'zinc', 16)
    xo = x1 if head_at == 1 else x0
    xi = x0 if head_at == 1 else x1
    d = 1 if xo > xi else -1
    cyl(group, name + "_Head", (xo, y, z), (xo + d * 0.005, y, z), r * 1.7, 'zinc', 16)
    cyl(group, name + "_Washer", (xi, y, z), (xi - d * 0.002, y, z), r * 1.6, 'zinc', 16)
    if clip:
        ring(group, name + "_Clip", (xi - d * 0.006, y, z - r * 1.4), r * 1.3, 0.0013, axis='X', segs=14)


def gnss(group, x, y, z):
    bm = bmesh.new()
    zb.bm_lathe(bm, [(0.0, 0.0), (0.045, 0.0), (0.045, 0.010), (0.038, 0.022), (0.020, 0.030), (0.0, 0.032)], 24,
                Matrix.Translation((x, y, z)))
    zb.bm_to_part(group, "GNSS", bm, ['dark'], angle=40.0)


def saddles(group, holes=HOLES, yp=YC, y0=None, y1=None, bolt=1.3):
    """Сідла на бортиках (лист 6 мм, П-подібні) + болти M10 крізь отвори Ø11 + проушини шарніра в площині yp."""
    y0 = holes[0] - 0.040 if y0 is None else y0
    y1 = holes[-1] + 0.040 if y1 is None else y1
    bolts, nuts = [], []
    for s in (-1, 1):
        xo, xi = s * P['side_x'], s * (P['side_x'] - P['wall_t'])
        for xa, xb in ((xo, xo + s * 0.006), (xi - s * 0.006, xi)):
            x0, x1 = sorted((xa, xb))
            zb.box(group, "Saddle_Cheek", x0, x1, y0, y1, 0.938, ZW + 0.008, bev=0.0015, segs=1)
        x0, x1 = sorted((xi - s * 0.006, xo + s * 0.006))
        zb.box(group, "Saddle_Top", x0, x1, y0, y1, ZW + 0.002, ZW + 0.008, bev=0.0015, segs=1)
        x0, x1 = sorted((xi, xo))
        zb.box(group, "Saddle_Pad", x0, x1, y0 + 0.002, y1 - 0.002, ZW, ZW + 0.002, mat='dark', bev=0.0005, segs=1)
        for yy in holes:
            bolts.append((Vector((xo + s * 0.006, yy, 0.956)), Vector((s, 0, 0))))
            nuts.append((Vector((xi - s * 0.006, yy, 0.956)), Vector((-s, 0, 0))))
        # проушини шарніра (вісь уздовж X) і палець; вузол ноги сидить між ними
        for dx in (-0.034, 0.034):
            lug(group, "Hinge_Lug", s * XW + dx, yp, ZH, ZW + 0.006, 0.045, 0.028, 0.008, 0.0105)
        pin(group, "Hinge_Pin", s * XW - 0.042, s * XW + 0.042, yp, ZH, 0.010, head_at=1 if s > 0 else 0)
        cyl(group, "Hinge_Lock", (s * XW, yp - 0.075, ZW + 0.030), (s * XW, yp - 0.075, ZW + 0.050), 0.006,
            'zinc', 12)
    zb.fasteners(group, "Saddle_Bolts", bolts, scale=bolt)
    zb.fasteners(group, "Saddle_Nuts", nuts, zb.NUT_HEX, scale=1.2)


def leg(group, s, top_x, top_y, top_z, tx0, tx1, cy0, cy1, mat='paint'):
    """Нога-лезо від шарніра до верху: восьмикутний переріз — півтовщина tx уздовж X, півхорда cy уздовж Y;
    звужується догори (верх — у точці (±top_x, top_y, top_z))."""
    pts = [(s * XW + x, y, ZH - 0.010) for x, y in octo(0.0, YC, tx0, cy0, tx0 * 0.45)]
    pts += [(s * top_x + x, y, top_z) for x, y in octo(0.0, top_y, tx1, cy1, tx1 * 0.45)]
    return solid(group, "Leg", pts, mat=mat, bev=0.004)


def finish(group, pivot=(0.0, YC, ZW)):
    ob = zb.join_group(group, zb.PARTS.pop(group), pivot=pivot)
    ob.parent = ROOT
    print("[superstructure] %s: %d трикутників" % (group, len(ob.data.polygons)))
    return ob


# =================================================================== A «Крило»
def variant_a():
    g = 'Top_A'
    saddles(g)
    zt, zb_, zm = 1.615, 1.545, 1.582            # верх, низ, середина передньої кромки крила по центру
    SPAN = 0.66

    def sect(x, ys, k, dz):
        """Переріз крила в площині x: передня кромка — вертикальна грань (під візор), верх і низ — скоси."""
        yl, yt = YC + 0.230 * k + ys, YC - 0.170 * k + ys
        zt_, zb2, zm_ = zt - dz, zb_ + dz, zm - dz * 0.3
        return [(x, yl, zm_ + 0.012 * k), (x, yl, zm_ - 0.016 * k), (x, yl - 0.060 * k, zt_),
                (x, yt + 0.030 * k, zt_), (x, yt, zm_ - 0.004), (x, yt + 0.040 * k, zb2), (x, yl - 0.070 * k, zb2)]
    c = sect(0.0, 0.0, 1.0, 0.0)
    tips = {s: sect(s * SPAN, -0.130, 0.60, 0.018) for s in (-1, 1)}
    solid(g, "Wing", c + tips[-1] + tips[1], bev=0.004)
    # ноги-леза: нахилені всередину й назад, заходять у низ крила
    for s in (-1, 1):
        leg(g, s, 0.530, YC - 0.090, 1.585, 0.026, 0.020, 0.100, 0.068)
    # візор: темне скло на вертикальній передній кромці (стрілоподібний, дві половини), камери за ним
    for s in (-1, 1):
        vis = []
        for x in (0.0, s * 0.42):
            f = abs(x) / SPAN
            q = [Vector(a).lerp(Vector(b), f) for a, b in zip(c, tips[s])]
            for off in (0.0015, 0.0045):
                vis += [Vector((x, q[0].y + off, q[0].z - 0.004)), Vector((x, q[1].y + off, q[1].z + 0.004))]
        solid(g, "Visor", vis, mat='glass', bev=0.001, segs=1)
    # бокові камери під кінцями крила (дивляться вперед-убік)
    for s in (-1, 1):
        cx, cy, cz = s * 0.60, YC - 0.010, zb_ - 0.003
        solid(g, "Cam_Pod", [(cx + s * dx, cy + dy, cz + dz) for dx, dy, dz in (
            (-0.035, -0.050, 0.026), (0.035, -0.050, 0.026), (-0.035, 0.050, 0.026), (0.035, 0.060, 0.026),
            (-0.030, -0.040, -0.030), (0.030, -0.040, -0.030), (-0.030, 0.045, -0.030), (0.030, 0.060, -0.022))],
            bev=0.003)
        solid(g, "Cam_Glass", [(cx + s * dx, cy + 0.058 + dy, cz + dz) for dx in (-0.022, 0.022)
                               for dy, dz in ((0.004, 0.016), (0.0, -0.014), (0.007, 0.016), (0.003, -0.014))],
              mat='glass', bev=0.001, segs=1)
    starlink(g, 0.0, YC + 0.010, zt, along_x=True)
    for s in (-1, 1):
        whip(g, s * 0.60, YC - 0.170, zt - 0.017, lean=s * 0.05)
    gnss(g, 0.30, YC - 0.100, zt - 0.009)
    return finish(g)


# =================================================================== B «Ореол» і його трубчасті варіації
ZT = 1.700                                       # вісь верхньої поперечини
HALO = [(-0.565, 1.450), (-0.380, ZT), (0.380, ZT), (0.565, 1.450)]   # плечі й вершина (вісь каркаса)


def halo_path(z0):
    return [(-XW, z0)] + HALO + [(XW, z0)]


def feet(g, ys, yp=YC):
    """Башмак ноги на шарнірі: язик між проушинами із заокругленим низом навколо пальця (отвір під палець),
    труба приварена зверху."""
    pts = [(yp + ys * math.cos(a), ZH + ys * math.sin(a)) for a in (math.pi + math.pi * k / 14 for k in range(15))]
    pts += [(yp + ys, ZH + 0.040), (yp - ys, ZH + 0.040)]
    for s in (-1, 1):
        zb.plate(g, "Foot", pts, [zb.circle(yp, ZH, 0.0105, 16)], t=0.054,
                 M=zb.frame((s * XW - 0.027, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.003)


def halo_kit(g, r, ys):
    """Спільне для «Ореолу»: сенсорні вузли на плечах (кільцеве скло — камери на 360°, антени), Starlink на
    п'єдесталі на вершині, камера вперед під вершиною. r — півтовщина каркаса від осі (у площині порталу),
    ys — півширина каркаса вздовж Y."""
    py = max(ys + 0.030, 0.100)                  # півширина вузла вздовж Y
    for s in (-1, 1):
        a, b = Vector(HALO[0 if s < 0 else 3]), Vector(HALO[1 if s < 0 else 2])
        m = (a + b) / 2
        d = (b - a).normalized()
        nrm = Vector((-d.y, d.x)) * (-1 if s > 0 else 1)     # назовні від порталу

        def P3(u, v, y):                          # u — уздовж плеча, v — від осі назовні, y — уздовж Y
            q = m + d * u + nrm * v
            return (q.x, YC + y, q.y)
        lo, hi = -(r + 0.020), r + 0.035
        pod = [P3(u, v, y) for u in (-0.085, 0.085) for v in (lo, hi) for y in (-py, py)]
        pod += [P3(0.0, v, y) for v in (lo - 0.005, hi + 0.015) for y in (-py - 0.020, py + 0.020)]
        solid(g, "Pod", pod, bev=0.006)
        solid(g, "Pod_Glass", [P3(u, v, y) for u in (-0.020, 0.020) for v in (lo - 0.002, hi + 0.018)
                               for y in (-py - 0.023, py + 0.023)], mat='glass', bev=0.002, segs=1)
        top = P3(0.050, hi, -0.040)
        whip(g, top[0], top[1], top[2] - 0.010, lean=s * 0.08, h=0.38)
    zp = ZT + r - 0.004                          # п'єдестал Starlink лежить на поперечині
    solid(g, "Plinth", [(x, YC + y, zp + z) for x, y in octo(0.0, 0.0, 0.150, 0.165, 0.050)
                        for z in (0.0, 0.020)] + [(x, YC + y, zp) for x, y in
                                                  octo(0.0, 0.0, 0.110, max(0.080, ys + 0.010), 0.030)], bev=0.003)
    starlink(g, 0.0, YC, zp + 0.020)
    zc, yf = ZT - r + 0.002, YC + max(ys, 0.075) + 0.035   # камера вперед під вершиною
    solid(g, "Cam_Front", [(x, y, z) for x in (-0.050, 0.050)
                           for y, z in ((yf - 0.035, zc), (yf, zc - 0.015), (yf, zc - 0.065),
                                        (yf - 0.050, zc - 0.075), (YC - 0.020, zc), (YC - 0.020, zc - 0.065))],
          bev=0.004)
    solid(g, "Cam_FrontGlass", [(x, y, z) for x in (-0.034, 0.034)
                                for y, z in ((yf + 0.0005, zc - 0.023), (yf + 0.0035, zc - 0.023),
                                             (yf + 0.0005, zc - 0.057), (yf + 0.0035, zc - 0.057))],
          mat='glass', bev=0.001, segs=1)


def variant_b():
    """B — гнута стрічка 160 × 50 мм (перший варіант, для порівняння)."""
    g = 'Top_B'
    saddles(g)
    sweep(g, "Halo", halo_path(ZH - 0.010), 0.050, 0.150, bev=0.005)
    halo_kit(g, 0.025, 0.075)
    return finish(g)


def variant_b1():
    """B1 — одна кругла труба Ø60 × 3, гнута на трубогибі (R 160 мм по осі) — без зварних стиків."""
    g = 'Top_B1'
    saddles(g)
    feet(g, 0.045)
    round_tube(g, "Tube", halo_path(ZH + 0.035), 0.030, 0.160)
    halo_kit(g, 0.030, 0.030)
    return finish(g)


def variant_b2():
    """B2 — одна квадратна труба 60 × 60 × 3, стики під кутом, зварні (шви видно)."""
    g = 'Top_B2'
    saddles(g)
    feet(g, 0.045)
    path = halo_path(ZH + 0.035)
    sweep(g, "Tube", path, 0.060, 0.060, bev=0.004)
    miter_welds(g, path, 0.060, 0.060)
    halo_kit(g, 0.030, 0.030)
    return finish(g)


def variant_b3():
    """B3 — дві паралельні круглі труби Ø42 (крок 130 мм) з перемичками Ø25 — «драбина»: жорсткіша
    на скручування, між трубами проходять кабелі; п'єдестал Starlink лежить на обох трубах."""
    g = 'Top_B3'
    saddles(g)
    feet(g, 0.095)
    path = halo_path(ZH + 0.035)
    for yo in (-0.065, 0.065):
        round_tube(g, "Tube", path, 0.021, 0.150, yoff=yo)
    for t in (0.07, 0.16, 0.30, 0.42, 0.58, 0.70, 0.84, 0.93):
        q = along(path, t)
        cyl(g, "Rung", (q.x, YC - 0.065, q.y), (q.x, YC + 0.065, q.y), 0.0125, 'paint', 16)
    halo_kit(g, 0.021, 0.086)
    return finish(g)


# --- B4 (обраний власником): прямокутний портал із квадратної труби + круглі розкоси, якнайдалі вперед
YP = 0.350              # площина порталу: передні отвори Ø11 бортиків (0,051 / 0,219 / 0,387), перед вушком крана
ZT4 = 1.680             # вісь поперечини
B4_PATH = [(-XW, ZH + 0.035), (-0.560, ZT4), (0.560, ZT4), (XW, ZH + 0.035)]


def rect_weld(group, cx, cy, z, hx, hy):
    """Зварний валик по периметру прямокутного перерізу (труба до площини z)."""
    pts = [(cx + hx, cy + hy, z), (cx - hx, cy + hy, z), (cx - hx, cy - hy, z), (cx + hx, cy - hy, z)]
    zb.tube(group, "Weld", pts + [pts[0]], 0.003, mat='paint', res=1, caps=False)


def gland(group, pos, d, scale=0.8):
    """Кабельний гермоввід (гайка-шестигранник) на поверхні pos, вісь d назовні."""
    zb.fasteners(group, "Gland", [(Vector(pos), Vector(d))], zb.NUT_HEX, mat='dark', scale=scale)


ZBT = ZT4 + 0.025       # верх поперечини
SL_Y = 0.170            # центр Starlink — за поперечиною (вісь поперечини y = 0,35)
SL_Z = ZBT + 0.006 + 0.015 + 0.003   # низ Starlink: накладка хомута, демпфер, дно колиски


def starlink_mount(g):
    """Starlink Mini (298,5 × 259 × 38,5 мм) по центру поперечини, зміщений назад:
    - 2 хомути на квадратній трубі (верхня й нижня накладки 6 мм, по 4 болти M8 з обох боків труби) — хомути
      можна пересувати вздовж поперечини, свердлити трубу не треба;
    - від хомутів назад — 2 консолі з листа 6 мм (стінка вниз уздовж задньої грані труби бере момент), полегшувальні
      отвори;
    - 4 гумові віброізолятори між консолями й колискою — Starlink у русі не трясе;
    - колиска — гнутий лист 3 мм із бортиками 15 мм і полегшувальними вирізами, 4 кутові притискачі з
      барашками (Starlink знімається без інструмента), притискачі заходять лише на рамку, не на антенне поле;
    - кабель живлення — з торця Starlink крізь проріз у бортику колиски до гермовводу в задній грані поперечини,
      далі всередині труби."""
    for cx in (-0.110, 0.110):
        # хомут: верхня й нижня накладки + 4 болти M8 по боках труби
        for z0, z1 in ((ZBT, ZBT + 0.006), (ZT4 - 0.031, ZT4 - 0.025)):
            zb.box(g, "SL_Clamp", cx - 0.030, cx + 0.030, YP - 0.040, YP + 0.040, z0, z1, bev=0.0015, segs=1)
        heads, nuts = [], []
        for dx in (-0.018, 0.018):
            for yy in (YP - 0.0315, YP + 0.0315):
                cyl(g, "SL_ClampBolt", (cx + dx, yy, ZT4 - 0.036), (cx + dx, yy, ZBT + 0.011), 0.004, 'zinc', 10)
                heads.append((Vector((cx + dx, yy, ZBT + 0.006)), Vector((0, 0, 1))))
                nuts.append((Vector((cx + dx, yy, ZT4 - 0.031)), Vector((0, 0, -1))))
        zb.fasteners(g, "SL_ClampHeads", heads, zb.NUT_HEX, scale=0.55)
        zb.fasteners(g, "SL_ClampNuts", nuts, zb.NUT_HEX, scale=0.55)
        # консоль назад: верхня кромка — на рівні верху накладки, стінка вниз уздовж задньої грані труби
        yr = YP - 0.025
        arm = [(yr, ZBT + 0.006), (0.040, ZBT + 0.006), (0.040, ZBT - 0.014), (0.150, ZBT - 0.022),
               (yr, ZT4 - 0.022)]
        holes = [zb.circle(yy, ZBT - 0.010, 0.0065, 14) for yy in (0.105, 0.185, 0.255)]
        zb.plate(g, "SL_Arm", arm, holes, t=0.006, M=zb.frame((cx - 0.003, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.001)
        # віброізолятори: гума + шайба зверху
        for yy in (0.075, 0.265):
            cyl(g, "SL_Iso", (cx, yy, ZBT + 0.006), (cx, yy, ZBT + 0.021), 0.012, 'dark', 16)
            cyl(g, "SL_IsoWasher", (cx, yy, ZBT + 0.006), (cx, yy, ZBT + 0.008), 0.015, 'zinc', 16)
    # колиска: дно з вирізами + бортики (гнутий лист 3 мм)
    hx, hy = 0.149 + 0.004, 0.1295 + 0.004       # внутрішній розмір під Starlink з зазором 4 мм
    zc = ZBT + 0.021
    base = zb.rrect(0.0, SL_Y, 2 * hx + 0.006, 2 * hy + 0.006, 0.010, 3)
    cut = [zb.rrect(dx, SL_Y, 0.075, 0.150, 0.020, 3) for dx in (-0.080, 0.080)]
    zb.plate(g, "SL_Cradle", base, cut, t=0.003, M=Matrix.Translation((0, 0, zc)), bev=0.0008)
    for (x0, x1, y0, y1) in ((-hx - 0.003, -hx, SL_Y - hy + 0.012, SL_Y + hy - 0.012),
                             (hx, hx + 0.003, SL_Y - hy + 0.012, SL_Y + hy - 0.012),
                             (-hx + 0.012, hx - 0.012, SL_Y - hy - 0.003, SL_Y - hy),
                             (-hx + 0.012, -0.020, SL_Y + hy, SL_Y + hy + 0.003),     # спереду — проріз під кабель
                             (0.040, hx - 0.012, SL_Y + hy, SL_Y + hy + 0.003)):
        zb.box(g, "SL_CradleLip", x0, x1, y0, y1, zc, zc + 0.018, bev=0.0008, segs=1)
    # Starlink Mini
    zs = zc + 0.003
    zb.box(g, "SL_Dish", -0.149, 0.149, SL_Y - 0.1295, SL_Y + 0.1295, zs, zs + 0.0385, mat='radome', bev=0.009, segs=3)
    zb.box(g, "SL_Bezel", -0.139, 0.139, SL_Y - 0.1195, SL_Y + 0.1195, zs + 0.0385, zs + 0.0395, mat='radome',
           bev=0.0004, segs=1)
    # кутові притискачі з барашками: стійка на бортику, лапка лише на рамку корпусу Starlink
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hx + 0.0015), SL_Y + sy * (hy - 0.030)
            zb.box(g, "SL_Clip", x - 0.004, x + 0.004, y - 0.010, y + 0.010, zc, zs + 0.043, mat='dark', bev=0.001, segs=1)
            x0, x1 = sorted((x, x - sx * 0.016))
            zb.box(g, "SL_ClipJaw", x0, x1, y - 0.010, y + 0.010, zs + 0.0395, zs + 0.044, mat='dark', bev=0.001, segs=1)
            cyl(g, "SL_Knob", (x, y, zs + 0.044), (x, y, zs + 0.054), 0.007, 'dark', 6)
    # кабель живлення: з переднього торця Starlink — крізь проріз бортика — до гермовводу в задній грані поперечини
    xc, yf = 0.010, SL_Y + 0.1295
    zb.box(g, "SL_Plug", xc - 0.010, xc + 0.010, yf, yf + 0.014, zs + 0.010, zs + 0.026, mat='dark', bev=0.002, segs=1)
    zb.tube(g, "SL_Cable", [(xc, yf + 0.014, zs + 0.018), (xc, yf + 0.022, zs + 0.018), (xc, yf + 0.024, ZT4 + 0.002),
                            (xc, YP - 0.040, ZT4)], 0.0035, bend=0.010, mat='tube', res=2)
    gland(g, (xc, YP - 0.025, ZT4), (0, -1, 0))
    # закладні гайки M8 на верху поперечини — під майбутнє обладнання (камери, маячки)
    for x in (-0.36, -0.26, 0.26, 0.36):
        cyl(g, "Rivnut", (x, YP, ZBT), (x, YP, ZBT + 0.0015), 0.0075, 'zinc', 12)
        cyl(g, "Rivnut_Hole", (x, YP, ZBT + 0.0010), (x, YP, ZBT + 0.0018), 0.0042, 'dark', 10)


def variant_b4():
    """B4 — квадратна труба 50 × 50: дві ноги з легким нахилом усередину й пряма поперечина, два кутові зварні
    стики з косинками; круглі розкоси Ø30 назад до сідел на пальцях (вийняв пальці — портал складається назад
    на палубу). Стоїть якнайдалі вперед: сідла на трьох передніх отворах Ø11 бортика, передній край сідла — за
    7 мм до вушка для крана (y 0,405). Starlink Mini — по центру, зміщений назад, на демпфованій колисці (див.
    starlink_mount); антени на кутах поперечини на кронштейнах з U-болтами; кабелі — всередині труб."""
    g = 'Top_B4'
    holes = (0.051, 0.219, 0.387)
    saddles(g, holes, yp=YP, y0=0.000, y1=0.398, bolt=1.1)
    feet(g, 0.040, yp=YP)
    yo = YP - YC
    sweep(g, "Tube", B4_PATH, 0.050, 0.050, bev=0.004, yoff=yo)
    miter_welds(g, B4_PATH, 0.050, 0.050, yoff=yo)
    inner = offset_path(B4_PATH, [-0.025] * 4)
    M_gus = zb.frame((0.0, YP + 0.003, 0.0), (1, 0, 0), (0, 0, 1))      # косинки в площині порталу, 6 мм
    yb = 0.040                                   # нижня проушина розкосу — на задньому кінці сідла
    zbp = ZW + 0.040
    for s in (-1, 1):
        # шов труба — башмак
        rect_weld(g, s * XW, YP, ZH + 0.040, 0.026, 0.026)
        # косинка в куті: трикутник між внутрішніми гранями ноги й поперечини, з отвором
        c = Vector(inner[1 if s < 0 else 2])
        dl = (Vector(inner[0 if s < 0 else 3]) - c).normalized()
        db = (Vector(inner[2 if s < 0 else 1]) - c).normalized()
        tri = [c, c + dl * 0.110, c + db * 0.110]
        cen = (tri[0] + tri[1] + tri[2]) / 3
        zb.plate(g, "Gusset", [(q.x, q.y) for q in tri], [zb.circle(cen.x, cen.y, 0.010, 16)], t=0.006, M=M_gus,
                 bev=0.0012)
        # розкіс: вушко на задній грані ноги, на розкосі — приварні язики, болт M10 угорі, швидкознімний палець унизу
        a, b = Vector(B4_PATH[0 if s < 0 else -1]), Vector(B4_PATH[1 if s < 0 else -2])
        top = a.lerp(b, 0.55)
        yt, zt_ = YP - 0.058, top.y - 0.004
        zb.plate(g, "Brace_Tab", [(YP - 0.022, top.y - 0.040), (YP - 0.022, top.y + 0.040), (yt - 0.012, zt_ + 0.016),
                                  (yt - 0.018, zt_), (yt - 0.012, zt_ - 0.016)],
                 [zb.circle(yt, zt_, 0.0055, 14)], t=0.006, M=zb.frame((top.x - 0.003, 0, 0), (0, 1, 0), (0, 0, 1)),
                 bev=0.0012)
        xb = top.x + s * 0.009                   # вісь розкосу — поруч із вушком
        p_top, p_bot = Vector((xb, yt, zt_)), Vector((s * XW, yb, zbp))
        dvec = (p_bot - p_top).normalized()
        cyl(g, "Brace", p_top + dvec * 0.030, p_bot - dvec * 0.030, 0.015, 'paint', 18)
        for p0, sg in ((p_top, 1), (p_bot, -1)):
            zb.plate(g, "Brace_Tang", [(p0.y + dvec.y * 0.036 * sg + dvec.z * 0.012 * k, p0.z + dvec.z * 0.036 * sg
                                         - dvec.y * 0.012 * k) for k in (-1, 1)] +
                     [(p0.y + 0.014 * math.cos(t_), p0.z + 0.014 * math.sin(t_)) for t_ in
                      (math.atan2(-dvec.z * sg, -dvec.y * sg) + math.pi / 2 + math.pi * k / 8 for k in range(9))],
                     [zb.circle(p0.y, p0.z, 0.0055, 14)], t=0.006,
                     M=zb.frame((p0.x - 0.003, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.0012)
        zb.fasteners(g, "Brace_Bolt", [(Vector((xb + s * 0.003, yt, zt_)), Vector((s, 0, 0)))], scale=1.0)
        zb.fasteners(g, "Brace_Nut", [(Vector((top.x - s * 0.003, yt, zt_)), Vector((-s, 0, 0)))], zb.NUT_HEX, scale=0.9)
        for dx in (-0.020, 0.020):
            lug(g, "Brace_Lug", s * XW + dx, yb, zbp, ZW + 0.006, 0.030, 0.018, 0.006, 0.0075)
        pin(g, "Brace_Pin", s * XW - 0.026, s * XW + 0.026, yb, zbp, 0.007, head_at=1 if s > 0 else 0)
        # кронштейн антени: накладка на поперечині, 2 U-болти навколо труби, коаксіал — до гермовводу в трубі
        xa = s * 0.500
        zb.box(g, "Ant_Plate", xa - 0.035, xa + 0.035, YP - 0.035, YP + 0.035, ZBT, ZBT + 0.006, bev=0.0015, segs=1)
        nuts = []
        for dx in (-0.024, 0.024):
            zb.tube(g, "Ant_UBolt", [(xa + dx, YP - 0.031, ZBT + 0.012), (xa + dx, YP - 0.031, ZT4 - 0.031),
                                     (xa + dx, YP + 0.031, ZT4 - 0.031), (xa + dx, YP + 0.031, ZBT + 0.012)], 0.004,
                    bend=0.008, mat='zinc', res=2)
            nuts += [(Vector((xa + dx, yy, ZBT + 0.006)), Vector((0, 0, 1))) for yy in (YP - 0.031, YP + 0.031)]
        zb.fasteners(g, "Ant_Nuts", nuts, zb.NUT_HEX, scale=0.55)
        whip(g, xa, YP, ZBT + 0.006, lean=s * 0.06)
        zb.tube(g, "Ant_Coax", [(xa, YP - 0.012, ZBT + 0.030), (xa - s * 0.012, YP - 0.040, ZBT + 0.020),
                                (xa - s * 0.030, YP - 0.042, ZT4), (xa - s * 0.045, YP - 0.033, ZT4)], 0.003,
                bend=0.010, mat='tube', res=2)
        gland(g, (xa - s * 0.045, YP - 0.025, ZT4), (0, -1, 0), scale=0.6)
        # кабелі виходять з ноги над шарніром і петлею (запас на складання) йдуть до гермовводу в щоці сідла
        xl = s * (XW - 0.026 - 0.004)            # внутрішня грань ноги біля низу
        gland(g, (s * (XW - 0.026), YP - 0.012, ZH + 0.110), (-s, 0, 0), scale=0.7)
        xi = s * (P['side_x'] - P['wall_t'] - 0.006)
        zb.tube(g, "Cable_Loop", [(xl - s * 0.008, YP - 0.012, ZH + 0.110), (xl - s * 0.030, YP - 0.020, ZH + 0.080),
                                  (xl - s * 0.040, YP - 0.060, ZH + 0.010), (xi - s * 0.030, YP - 0.095, 0.975),
                                  (xi - s * 0.004, YP - 0.100, 0.968)], 0.0075, bend=0.030, mat='tube', res=2)
        gland(g, (xi, YP - 0.100, 0.968), (-s, 0, 0), scale=0.9)
    starlink_mount(g)
    return finish(g, pivot=(0.0, YP, ZW))


def offset_path(path, offs):
    """Ламана, зміщена в площині порталу на offs[i] у кожній вершині (по бісектрисі; + назовні)."""
    pts = [Vector((x, z)) for x, z in path]
    out = []
    for i, p in enumerate(pts):
        tans = []
        if i > 0:
            tans.append((p - pts[i - 1]).normalized())
        if i < len(pts) - 1:
            tans.append((pts[i + 1] - p).normalized())
        ns = [Vector((-t.y, t.x)) for t in tans]               # ліворуч від напрямку (портал іде зліва направо) = назовні
        m = (sum(ns, Vector((0.0, 0.0))) / len(ns)).normalized()
        k = 1.0 / max(m.dot(ns[0]), 0.3)
        q = p + m * offs[i] * k
        out.append((q.x, q.y))
    return out


def variant_b5():
    """B5 — ферма: дві квадратні труби 40 × 40 (зовнішній і внутрішній пояс) і стінка 4 мм між ними з
    восьмикутними вирізами, як на бортиках палуби; ноги звужуються до шарніра. Найжорсткіша при тій самій вазі."""
    g = 'Top_B5'
    saddles(g)
    feet(g, 0.040)
    path = halo_path(ZH + 0.035)
    offs = [0.010, 0.060, 0.060, 0.060, 0.060, 0.010]
    outer, inner = offset_path(path, offs), offset_path(path, [-o for o in offs])
    for nm, pth in (("Chord_Out", outer), ("Chord_In", inner)):
        sweep(g, nm, pth, 0.040, 0.040, bev=0.003)
        miter_welds(g, pth, 0.040, 0.040)
    M = zb.frame((0.0, YC + 0.002, 0.0), (1, 0, 0), (0, 0, 1))     # стінка в площині порталу, товщина вздовж −Y
    for i in range(len(path) - 1):
        quad = [inner[i], inner[i + 1], outer[i + 1], outer[i]]
        a, b = Vector(path[i]), Vector(path[i + 1])
        L, d = (b - a).length, (b - a).normalized()
        nrm = Vector((-d.y, d.x))
        holes = []
        nh = max(1, int(L / 0.13))
        for k in range(nh):
            t = (k + 0.5) / nh
            c = a.lerp(b, t)
            w = 2 * (offs[i] + (offs[i + 1] - offs[i]) * t) - 0.040        # просвіт між поясами
            if w < 0.055:
                continue
            hl, hw = min(0.075, L / nh - 0.035), w - 0.026
            holes.append([(c + d * u + nrm * v)[:] for u, v in octo(0.0, 0.0, hl / 2, hw / 2, min(hl, hw) * 0.3)])
        zb.plate(g, "Web", quad, holes, t=0.004, M=M, bev=0.0008)
    halo_kit(g, 0.080, 0.020)
    return finish(g)


# =================================================================== C «Козирок»
def variant_c():
    g = 'Top_C'
    saddles(g)
    zr = 1.520                                    # низ даху по центру
    for s in (-1, 1):
        leg(g, s, 0.560, YC - 0.020, zr + 0.010, 0.024, 0.020, 0.090, 0.075)
    yc, tilt = YC + 0.060, math.radians(4.0)

    def R(x, y, z):                               # дах нахилений уперед (передня кромка нижче)
        dy = y - yc
        return (x, yc + dy * math.cos(tilt), zr + z - dy * math.sin(tilt))
    roof = [R(x, yc + y, 0.0) for x, y in octo(0.0, 0.0, 0.600, 0.350, 0.120)]
    roof += [R(x, yc + y, z) for z in (0.018, 0.040) for x, y in octo(0.0, 0.0, 0.615, 0.365, 0.125)]
    roof += [R(x, yc + y, 0.058) for x, y in octo(0.0, 0.0, 0.570, 0.320, 0.110)]
    solid(g, "Roof", roof, bev=0.004)
    # візор: темне скло на вертикальній передній кромці даху (камери за ним)
    solid(g, "Visor", [R(x, yc + y, z) for x in (-0.42, 0.42) for y in (0.3665, 0.3695) for z in (0.022, 0.036)],
          mat='glass', bev=0.001, segs=1)
    # кутові камерні купола під дахом
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y, z = R(sx * 0.470, yc + sy * 0.230, 0.0)
            bm = bmesh.new()
            zb.bm_lathe(bm, [(0.0, 0.0), (0.045, 0.0), (0.045, -0.010), (0.040, -0.028), (0.026, -0.042),
                             (0.0, -0.047)], 24, Matrix.Translation((x, y, z)))
            zb.bm_to_part(g, "Dome", bm, ['glass'], angle=40.0)
            cyl(g, "Dome_Ring", (x, y, z), (x, y, z - 0.012), 0.050, 'dark', 24)
    # Starlink і GNSS на даху — будуються горизонтально й нахиляються разом із дахом
    n0 = len(zb.PARTS[g])
    starlink(g, 0.0, yc - 0.050, zr + 0.054)
    gnss(g, 0.330, yc - 0.250, zr + 0.056)
    M = Matrix.Translation((0, yc, zr)) @ Matrix.Rotation(-tilt, 4, 'X') @ Matrix.Translation((0, -yc, -zr))
    for ob in zb.PARTS[g][n0:]:
        ob.data.transform(M)
    for s in (-1, 1):
        x, y, z = R(s * 0.520, yc - 0.290, 0.053)
        whip(g, x, y, z, lean=s * 0.04)
    return finish(g)


if __name__ == "__main__":
    for nm in [o.name for o in bpy.data.objects if o.name.startswith('Top_')]:
        old = bpy.data.objects.get(nm)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    # обраний варіант; ZMIY_TOPS=all — разом із попередніми концептами для порівняння
    builders = [variant_b4]
    if os.environ.get("ZMIY_TOPS") == "all":
        builders = [variant_a, variant_b, variant_b1, variant_b2, variant_b3, variant_b4, variant_b5, variant_c]
    tops = [f() for f in builders]
    if os.environ.get("ZMIY_NO_PACK") != "1":
        import pack_viewer                      # noqa: E402
        pack_viewer.pack([o.name for o in tops])
