# -*- coding: utf-8 -*-
"""Надбудова-портал над палубою для Starlink, камер і антен — три концепти футуристичного дизайну
поверх готової моделі (основну модель не змінюють):
    blender -b zmiy_logistic.blend --python concepts/superstructure.py
Додає об'єкти Top_A / Top_B / Top_C (дочірні до Zmiy_Logistic) і пакує сторінку перегляду разом із ними
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
          Starlink на вершині.
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


def sweep(group, name, path, w, d, mat='paint', bev=0.004):
    """Стрічка: прямокутний переріз w (у площині XZ) × d (уздовж Y) уздовж ламаної в площині y = YC,
    стики — під кутом (мітра)."""
    pts = [Vector((x, YC, z)) for x, z in path]
    ny = Vector((0, 1, 0))
    rings = []
    bm = bmesh.new()
    for i, p in enumerate(pts):
        tans = []
        if i > 0:
            tans.append((p - pts[i - 1]).normalized())
        if i < len(pts) - 1:
            tans.append((pts[i + 1] - p).normalized())
        ns = [t.cross(ny).normalized() for t in tans]
        m = (sum(ns, Vector()) / len(ns)).normalized()
        k = 1.0 / max(m.dot(ns[0]), 0.3)
        rings.append([bm.verts.new(p + m * (sw * w / 2 * k) + ny * (sd * d / 2))
                      for sw, sd in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new([a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]])
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=2, affect='EDGES', clamp_overlap=True)
    return zb.bm_to_part(group, name, bm, [mat], angle=35.0)


def starlink(group, cx, cy, z0, along_x=False):
    """Starlink Mini горизонтально: корпус 259 × 298 × 38,5 мм на тонкій рамці (along_x — довгим боком уздовж X)."""
    hx, hy = (0.149, 0.1295) if along_x else (0.1295, 0.149)
    solid(group, "SL_Frame", [(cx + sx * (hx + 0.011), cy + sy * (hy + 0.011), z) for sx in (-1, 1) for sy in (-1, 1)
                              for z in (z0, z0 + 0.008)], mat='tube', bev=0.002, segs=1)
    zb.box(group, "SL_Dish", cx - hx, cx + hx, cy - hy, cy + hy, z0 + 0.008, z0 + 0.0465,
           mat='radome', bev=0.008, segs=3)


def whip(group, x, y, z, lean=0.0, h=0.42):
    """Штирова антена: пружинна основа + штир (лише трохи відхилений назовні)."""
    cyl(group, "Ant_Base", (x, y, z), (x, y, z + 0.035), 0.013, 'dark', 16)
    cyl(group, "Ant_Spring", (x, y, z + 0.035), (x, y, z + 0.075), 0.008, 'tube', 12)
    cyl(group, "Ant_Whip", (x, y, z + 0.075), (x + lean * h, y, z + 0.075 + h), 0.0035, 'tube', 8)


def gnss(group, x, y, z):
    bm = bmesh.new()
    zb.bm_lathe(bm, [(0.0, 0.0), (0.045, 0.0), (0.045, 0.010), (0.038, 0.022), (0.020, 0.030), (0.0, 0.032)], 24,
                Matrix.Translation((x, y, z)))
    zb.bm_to_part(group, "GNSS", bm, ['dark'], angle=40.0)


def saddles(group):
    """Сідла на бортиках (лист 6 мм, П-подібні) + 3 болти M10 крізь отвори Ø11 + проушини шарніра."""
    y0, y1 = HOLES[0] - 0.040, HOLES[-1] + 0.040
    bolts, nuts = [], []
    for s in (-1, 1):
        xo, xi = s * P['side_x'], s * (P['side_x'] - P['wall_t'])
        for xa, xb in ((xo, xo + s * 0.006), (xi - s * 0.006, xi)):
            x0, x1 = sorted((xa, xb))
            zb.box(group, "Saddle_Cheek", x0, x1, y0, y1, 0.938, ZW + 0.006, bev=0.0015, segs=1)
        x0, x1 = sorted((xi - s * 0.006, xo + s * 0.006))
        zb.box(group, "Saddle_Top", x0, x1, y0, y1, ZW, ZW + 0.006, bev=0.0015, segs=1)
        for yy in HOLES:
            bolts.append((Vector((xo + s * 0.006, yy, 0.956)), Vector((s, 0, 0))))
            nuts.append((Vector((xi - s * 0.006, yy, 0.956)), Vector((-s, 0, 0))))
        # проушини шарніра (вісь уздовж X) і палець; вузол ноги сидить між ними
        for dx in (-0.034, 0.034):
            xa = s * XW + dx
            solid(group, "Hinge_Lug", [(xa + e, YC + a, z) for e in (-0.004, 0.004)
                                       for a, z in ((-0.045, ZW + 0.006), (0.045, ZW + 0.006), (0.030, ZH + 0.016),
                                                    (-0.030, ZH + 0.016))], bev=0.0015, segs=1)
        cyl(group, "Hinge_Pin", (s * XW - 0.046, YC, ZH), (s * XW + 0.046, YC, ZH), 0.010, 'zinc', 16)
        cyl(group, "Hinge_Lock", (s * XW, YC - 0.075, ZW + 0.030), (s * XW, YC - 0.075 + 0.0, ZW + 0.050), 0.006,
            'zinc', 12)
    zb.fasteners(group, "Saddle_Bolts", bolts, scale=1.3)
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


# =================================================================== B «Ореол»
def variant_b():
    g = 'Top_B'
    saddles(g)
    zt = 1.700
    path = [(-XW, ZH - 0.010), (-0.565, 1.450), (-0.380, zt), (0.380, zt), (0.565, 1.450), (XW, ZH - 0.010)]
    sweep(g, "Halo", path, 0.050, 0.150, bev=0.005)
    # сенсорні вузли на плечах: гранчасте «яйце» навколо стрічки з кільцевим склом (камери на 360°)
    for s in (-1, 1):
        a, b = Vector((s * 0.565, 1.450)), Vector((s * 0.380, zt))
        m = (a + b) / 2
        d = (b - a).normalized()
        nrm = Vector((-d.y, d.x)) * (-1 if s > 0 else 1)     # назовні від порталу
        def P3(u, v, y):                          # u — уздовж стрічки, v — від неї назовні, y — уздовж Y
            q = m + d * u + nrm * v
            return (q.x, YC + y, q.y)
        pod = [P3(u, v, y) for u in (-0.085, 0.085) for v in (-0.045, 0.060)
               for y in (-0.100, 0.100)] + [P3(0.0, v, y) for v in (-0.050, 0.075) for y in (-0.120, 0.120)]
        solid(g, "Pod", pod, bev=0.006)
        ring = [P3(u, v, y) for u in (-0.020, 0.020) for v in (-0.052, 0.078) for y in (-0.123, 0.123)]
        solid(g, "Pod_Glass", ring, mat='glass', bev=0.002, segs=1)
        top = P3(0.050, 0.060, -0.040)
        whip(g, top[0], top[1], top[2] - 0.010, lean=s * 0.08, h=0.38)
    # вершина: Starlink на низькому гранчастому п'єдесталі
    solid(g, "Plinth", [(x, YC + y, zt + z) for x, y in octo(0.0, 0.0, 0.150, 0.165, 0.050)
                        for z in (0.020, 0.040)] + [(x, YC + y, zt + 0.020) for x, y in
                                                    octo(0.0, 0.0, 0.110, 0.080, 0.030)], bev=0.003)
    starlink(g, 0.0, YC, zt + 0.040)
    # передня камера під вершиною
    solid(g, "Cam_Front", [(x, YC + y, z) for x in (-0.050, 0.050)
                           for y, z in ((0.075, zt - 0.025), (0.110, zt - 0.040), (0.110, zt - 0.090),
                                        (0.060, zt - 0.100), (-0.020, zt - 0.025), (-0.020, zt - 0.090))],
          bev=0.004)
    solid(g, "Cam_FrontGlass", [(x, YC + y, z) for x in (-0.034, 0.034)
                                for y, z in ((0.1105, zt - 0.048), (0.1135, zt - 0.048), (0.1105, zt - 0.082),
                                             (0.1135, zt - 0.082))], mat='glass', bev=0.001, segs=1)
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
    for nm in ('Top_A', 'Top_B', 'Top_C'):
        old = bpy.data.objects.get(nm)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    tops = [variant_a(), variant_b(), variant_c()]
    if os.environ.get("ZMIY_NO_PACK") != "1":
        import pack_viewer                      # noqa: E402
        pack_viewer.pack([o.name for o in tops])
