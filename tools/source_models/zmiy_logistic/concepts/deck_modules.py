# -*- coding: utf-8 -*-
"""Тестові змінні модулі на палубу «Змія» поверх поточної моделі (основну модель не змінюють).
blender -b --factory-startup --python concepts/deck_modules.py -- <out_dir>
Спільне для всіх: рама-піддон 1,19 × 1,40 м із кутника 40×40 лягає в палубу між бортиками й кріпиться
8 болтами M10 крізь наявні отвори Ø11 у бортиках — палуба лишається гладкою, модуль міняють за ~10 хв.
L1 «Припаси»: каністри, ящики, цинки під стяжними ременями.
L2 «Евакуація»: двоє нош на низьких поперечках, поранені в евакуаційних мішках.
B1 «Бойовий»: дистанційний кулеметний модуль 12,7 мм — окремий об'єкт Turret (обертання).
B2 «Мінування»: касета на 27 протитанкових мін і відкидний жолоб назад.
B3 «РЕБ / ретранслятор»: апаратний ящик із ребрами охолодження, 4 секторні панельні антени.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # папка моделі
sys.path.insert(0, MODEL)
import zmiy_build as zb      # noqa: E402
import zmiy_export as ze     # noqa: E402

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else "/tmp"
os.makedirs(OUT, exist_ok=True)

root = zb.build_all()
P = zb.P
for key, (name, col, rough, metal) in {
        'crate': ("Mod_Crate", "#3B4232", 0.80, 0.0),     # дерев'яні ящики, фарбовані темною оливою
        'can': ("Mod_AmmoCan", "#4E573B", 0.55, 0.3),     # металеві цинки
        'coyote': ("Mod_Coyote", "#7A6A4A", 0.85, 0.0),   # каністри, евакуаційні мішки
        'strap': ("Mod_Strap", "#1A1A18", 0.85, 0.0),     # ремені, гумові ручки
        'alu': ("Mod_Alu", "#9A9C98", 0.40, 1.0),         # жердини нош
        'canvas': ("Mod_Canvas", "#2F3529", 0.90, 0.0),   # полотно нош
        'gun': ("Mod_Gun", "#2A2C29", 0.45, 0.6),         # кулемет
        'lens': ("Mod_Lens", "#0B0D0E", 0.12, 0.0),
        'mine': ("Mod_Mine", "#55603F", 0.70, 0.0),
        'radome': ("Mod_Radome", "#6E7362", 0.75, 0.0),   # обтічники панельних антен
}.items():
    zb.MAT[key] = zb.make_material(name, col, rough, metal)

ZT, ZW = P['deck_z'], P['wall_z1']            # верх палуби 0,862, верх бортиків 0,990
SX, WT = P['side_x'], P['wall_t']
XI = SX - WT                                   # внутрішня площина бортика
PX, PY0, PY1, PH = 0.595, -0.900, 0.500, 0.040  # рама-піддон: ±X, задній і передній край, висота кутника
ZP = ZT + PH                                   # верх рами 0,902
HOLES_Y = (-0.621, -0.285, 0.051, 0.387)       # отвори Ø11 у бортиках (z 0,956), крізь них — болти M10
ZH = 0.956


def cyl(group, name, p0, p1, r, mat, segs=24):
    bm = bmesh.new()
    zb.bm_cyl(bm, Vector(p0), Vector(p1), r, segs)
    return zb.bm_to_part(group, name, bm, [mat], angle=40.0)


def lathe(group, name, prof, M, mat, segs=32):
    bm = bmesh.new()
    zb.bm_lathe(bm, prof, segs, M)
    return zb.bm_to_part(group, name, bm, [mat], angle=40.0)


def rot_box(group, name, size, M, mat, bev=0.004, segs=2):
    """Брусок size=(x, y, z) з центром у нулі, перенесений матрицею M."""
    bm = bmesh.new()
    sx, sy, sz = (s / 2 for s in size)
    zb.bm_box(bm, -sx, sx, -sy, sy, -sz, sz, bev, segs)
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    return zb.bm_to_part(group, name, bm, [mat], angle=30.0)


def strap(group, y, prof):
    """Стяжний ремінь поперек вантажу: prof — [(x, z)], кінці на рамі-піддоні."""
    zb.tube(group, "Strap", [(x, y, z) for x, z in prof], 0.006, bend=0.012, mat='strap', res=2)


# ------------------------------------------------------------------ спільна рама-піддон
def pallet():
    g = 'Pal'
    t = 0.004
    for s in (-1, 1):                            # поздовжні кутники
        x0, x1 = sorted((s * (PX - t), s * PX))
        zb.box(g, "Pal_SideV", x0, x1, PY0, PY1, ZT, ZP, bev=0.001, segs=1)
        x0, x1 = sorted((s * (PX - 0.040), s * PX))
        zb.box(g, "Pal_SideH", x0, x1, PY0, PY1, ZT, ZT + t, bev=0.001, segs=1)
    for yy, d in ((PY0, 1), (PY1, -1)):          # торцеві кутники
        y0, y1 = sorted((yy, yy + d * t))
        zb.box(g, "Pal_EndV", -PX, PX, y0, y1, ZT, ZP, bev=0.001, segs=1)
        y0, y1 = sorted((yy, yy + d * 0.040))
        zb.box(g, "Pal_EndH", -PX, PX, y0, y1, ZT, ZT + t, bev=0.001, segs=1)
    for yc in (-0.620, -0.200, 0.220):            # поперечки з труби 60×40 — під кріплення модулів
        zb.box(g, "Pal_Cross", -PX + t, PX - t, yc - 0.030, yc + 0.030, ZT, ZP, bev=0.002, segs=1)
    bolts, nuts = [], []
    for s in (-1, 1):                             # вушка рами до бортиків: 8 × M10 крізь отвори Ø11
        for yh in HOLES_Y:
            x0, x1 = sorted((s * (XI - 0.006), s * XI))
            zb.box(g, "Pal_Tab", x0, x1, yh - 0.030, yh + 0.030, ZT + 0.012, ZH + 0.022, bev=0.002, segs=1)
            x0, x1 = sorted((s * PX, s * (XI - 0.006)))
            zb.box(g, "Pal_TabFoot", x0, x1, yh - 0.030, yh + 0.030, ZT + 0.004, ZP, bev=0.001, segs=1)
            bolts.append((Vector((s * SX, yh, ZH)), Vector((s, 0, 0))))
            nuts.append((Vector((s * (XI - 0.006), yh, ZH)), Vector((-s, 0, 0))))
    zb.fasteners(g, "Pal_Bolts", bolts, scale=1.1)
    zb.fasteners(g, "Pal_Nuts", nuts, zb.NUT_HEX, scale=0.8)


# ------------------------------------------------------------------ L1 «Припаси»
def jerrycan(g, xc, y0, z0):
    """Каністра 20 л: 165 × 345 × 470 мм, три ручки зверху, горловина."""
    zb.box(g, "Jerry", xc - 0.0825, xc + 0.0825, y0, y0 + 0.345, z0, z0 + 0.470, mat='coyote', bev=0.014, segs=2)
    for dy in (0.090, 0.150, 0.210):
        zb.box(g, "Jerry_Handle", xc - 0.012, xc + 0.012, y0 + dy - 0.012, y0 + dy + 0.012, z0 + 0.470,
               z0 + 0.500, mat='coyote', bev=0.006, segs=1)
    cyl(g, "Jerry_Cap", (xc, y0 + 0.300, z0 + 0.462), (xc, y0 + 0.300, z0 + 0.505), 0.024, 'strap', 16)


def crate(g, x0, x1, y0, y1, z0, z1):
    zb.box(g, "Crate", x0, x1, y0, y1, z0, z1, mat='crate', bev=0.008, segs=1)
    for xx in (x0 + 0.06, x1 - 0.06):             # планки кришки
        zb.box(g, "Crate_Batten", xx - 0.022, xx + 0.022, y0 + 0.004, y1 - 0.004, z1, z1 + 0.012, mat='crate',
               bev=0.003, segs=1)
    for yy, d in ((y0, -1), (y1, 1)):             # ручки на торцях
        a, b = sorted((yy, yy + d * 0.025))
        zb.box(g, "Crate_Handle", (x0 + x1) / 2 - 0.07, (x0 + x1) / 2 + 0.07, a, b, z1 - 0.10, z1 - 0.07,
               mat='strap', bev=0.005, segs=1)


def ammo_can(g, xc, y0, z0):
    """Цинк 155 × 305 × 190 мм із ручкою на кришці."""
    zb.box(g, "AmmoCan", xc - 0.0775, xc + 0.0775, y0, y0 + 0.305, z0, z0 + 0.190, mat='can', bev=0.006, segs=1)
    zb.box(g, "AmmoCan_Lid", xc - 0.080, xc + 0.080, y0 - 0.003, y0 + 0.308, z0 + 0.170, z0 + 0.190, mat='can',
           bev=0.004, segs=1)
    zb.box(g, "AmmoCan_Handle", xc - 0.010, xc + 0.010, y0 + 0.090, y0 + 0.215, z0 + 0.190, z0 + 0.205,
           mat='strap', bev=0.004, segs=1)


def variant_l1():
    g = 'L1'
    for i in range(6):                            # ззаду: 6 каністр (120 л)
        jerrycan(g, -0.4375 + i * 0.175, -0.855, ZT)
    crate(g, -0.575, -0.015, -0.480, -0.060, ZT, ZT + 0.300)
    crate(g, 0.015, 0.575, -0.480, -0.060, ZT, ZT + 0.300)
    crate(g, -0.420, 0.300, -0.430, -0.110, ZT + 0.300, ZT + 0.500)
    for layer in range(2):                        # спереду: 12 цинків у два яруси
        for i in range(6):
            ammo_can(g, -0.4325 + i * 0.173, 0.100, ZT + layer * 0.192)
    zj, zc0, zc1, za = ZT + 0.472, ZT + 0.302, ZT + 0.502, ZT + 0.386
    for y in (-0.835, -0.575):
        strap(g, y, [(-0.59, ZP), (-0.53, zj), (0.53, zj), (0.59, ZP)])
    for y in (-0.380, -0.160):
        strap(g, y, [(-0.59, ZP), (-0.578, zc0), (-0.424, zc0), (-0.424, zc1), (0.304, zc1), (0.304, zc0),
                     (0.578, zc0), (0.59, ZP)])
    for y in (0.150, 0.355):
        strap(g, y, [(-0.59, ZP), (-0.52, za), (0.52, za), (0.59, ZP)])


# ------------------------------------------------------------------ L2 «Евакуація»
def casualty(g, xc, zc, y0=-1.070, y1=0.670):
    """Поранений в евакуаційному мішку: суцільний «кокон», звужений до ніг і до голови."""
    bm = bmesh.new()
    zb.bm_box(bm, -0.215, 0.215, y0, y1, 0.0, 0.200, 0.085, 4)
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.y - e.verts[1].co.y) > 0.5],
                              cuts=12, use_grid_fill=False)
    for v in bm.verts:
        y = v.co.y
        f = 1.0
        if y < -0.350:                            # ноги: ширина й висота до 70 %
            f = 1.0 - 0.30 * min(1.0, (-0.350 - y) / (-0.350 - y0))
        elif y > 0.300:                           # плечі → голова: до 80 %
            f = 1.0 - 0.20 * min(1.0, (y - 0.300) / (y1 - 0.300))
        v.co.x *= f
        v.co.z *= f
    bmesh.ops.transform(bm, matrix=Matrix.Translation((xc, 0, zc)), verts=bm.verts[:])
    zb.bm_to_part(g, "Casualty", bm, ['coyote'], angle=40.0)


def variant_l2():
    g = 'L2'
    zbm0, zbm1 = ZW + 0.005, ZW + 0.045           # поперечки над бортиками (ноші ширші за міжбортовий простір)
    for yb in (-0.780, 0.360):
        zb.box(g, "Evac_Beam", -0.60, 0.60, yb - 0.020, yb + 0.020, zbm0, zbm1, bev=0.003, segs=1)
        for s in (-1, 1):
            x0, x1 = sorted((s * 0.555, s * 0.595))
            zb.box(g, "Evac_Post", x0, x1, yb - 0.020, yb + 0.020, ZT + 0.004, zbm0, bev=0.002, segs=1)
    y0, y1 = -1.300, 0.900                        # ноші 2,2 м — звис ~0,37 м за палубою спереду й ззаду
    zp = zbm1 + 0.016
    for xc in (-0.290, 0.290):
        for dx in (-0.265, 0.265):
            x = xc + dx
            cyl(g, "Litter_Pole", (x, y0, zp), (x, y1, zp), 0.016, 'alu', 16)
            for ya, yb_ in ((y0 - 0.002, y0 + 0.150), (y1 - 0.150, y1 + 0.002)):
                cyl(g, "Litter_Grip", (x, ya, zp), (x, yb_, zp), 0.019, 'strap', 16)
            for yb in (-0.780, 0.360):            # затискачі на поперечках
                zb.box(g, "Litter_Clamp", x - 0.030, x + 0.030, yb - 0.030, yb + 0.030, zbm1, zp + 0.022,
                       mat='strap', bev=0.006, segs=1)
        zb.box(g, "Litter_Canvas", xc - 0.255, xc + 0.255, y0 + 0.200, y1 - 0.200, zp - 0.012, zp - 0.006,
               mat='canvas', bev=0.002, segs=1)
        for yy in (y0 + 0.240, y1 - 0.240):       # розпірки
            cyl(g, "Litter_Spreader", (xc - 0.265, yy, zp - 0.020), (xc + 0.265, yy, zp - 0.020), 0.009, 'alu', 12)
        zc = zp - 0.006
        casualty(g, xc, zc)
        for yy in (-0.750, -0.200, 0.300):        # фіксаційні ремені
            zb.tube(g, "Casualty_Strap", [(xc - 0.268, yy, zp), (xc - 0.200, yy, zc + 0.206),
                                           (xc + 0.200, yy, zc + 0.206), (xc + 0.268, yy, zp)],
                    0.006, bend=0.03, mat='strap', res=2)


# ------------------------------------------------------------------ B1 «Бойовий»
YR, ZR = -0.300, ZP + 0.070                    # центр погона й верх нерухомої частини


def variant_b1():
    g, t = 'B1', 'B1T'
    zb.box(g, "RWS_BasePlate", -0.360, 0.360, -0.660, 0.060, ZP, ZP + 0.010, bev=0.003, segs=1)
    cyl(g, "RWS_RingHousing", (0, YR, ZP + 0.010), (0, YR, ZR), 0.240, 'paint', 48)
    zb.fasteners(g, "RWS_PlateBolts", [(Vector((x, y, ZP + 0.010)), Vector((0, 0, 1)))
                                       for x in (-0.320, 0.320) for y in (-0.620, -0.300, 0.020)])
    # обертова частина (окремий об'єкт Turret, півот у центрі погона)
    cyl(t, "RWS_Turntable", (0, YR, ZR), (0, YR, ZR + 0.025), 0.230, 'paint', 48)
    zb.box(t, "RWS_Body", -0.200, 0.200, YR - 0.220, YR + 0.200, ZR + 0.025, ZR + 0.130, bev=0.020, segs=2)
    za = 1.240                                    # вісь ствола
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.100, s * 0.120))
        zb.box(t, "RWS_Cheek", x0, x1, YR - 0.150, YR + 0.180, ZR + 0.130, za + 0.070, bev=0.012, segs=2)
        cyl(t, "RWS_Trunnion", (s * 0.120, YR + 0.050, za), (s * 0.140, YR + 0.050, za), 0.034, 'paint')
    zb.box(t, "RWS_Receiver", -0.055, 0.055, YR - 0.320, YR + 0.220, za - 0.070, za + 0.080, mat='gun', bev=0.008,
           segs=1)
    cyl(t, "RWS_Jacket", (0, YR + 0.220, za), (0, YR + 0.420, za), 0.032, 'gun', 20)
    cyl(t, "RWS_Barrel", (0, YR + 0.420, za), (0, 0.920, za), 0.017, 'gun', 16)
    cyl(t, "RWS_Muzzle", (0, 0.920, za), (0, 1.000, za), 0.024, 'gun', 16)
    zb.box(t, "RWS_AmmoBox", -0.320, -0.150, YR - 0.200, YR + 0.140, ZR + 0.130, za + 0.080, bev=0.010, segs=1)
    zb.box(t, "RWS_Feed", -0.150, -0.055, YR + 0.020, YR + 0.090, za + 0.020, za + 0.060, mat='strap', bev=0.006,
           segs=1)
    yf = YR + 0.220                               # блок прицілу: камера + тепловізор
    zb.box(t, "RWS_Sight", 0.150, 0.310, YR - 0.060, yf, za - 0.080, za + 0.080, bev=0.015, segs=2)
    for xx, r in ((0.190, 0.026), (0.272, 0.030)):
        cyl(t, "RWS_LensBezel", (xx, yf - 0.002, za), (xx, yf + 0.012, za), r + 0.007, 'paint')
        cyl(t, "RWS_Lens", (xx, yf + 0.012, za), (xx, yf + 0.014, za), r, 'lens')


# ------------------------------------------------------------------ B2 «Мінування»
MINE = [(0.0, 0.0), (0.160, 0.0), (0.160, 0.085), (0.150, 0.100), (0.055, 0.100), (0.055, 0.118), (0.0, 0.118)]


def variant_b2():
    g = 'B2'
    zf = ZP + 0.008
    zb.box(g, "Mine_Floor", -0.555, 0.555, -0.800, 0.280, ZP, zf, bev=0.002, segs=1)
    for x in (-0.370, 0.0, 0.370):                # 3 × 3 касети по 3 міни (27 шт.)
        for y in (-0.620, -0.260, 0.100):
            for k in range(3):
                lathe(g, "Mine", MINE, Matrix.Translation((x, y, zf + k * 0.120)), 'mine')
    for s in (-1, 1):
        for y0 in (-0.820, 0.260):                # кутові стійки
            x0, x1 = sorted((s * 0.530, s * 0.570))
            zb.box(g, "Rack_Post", x0, x1, y0, y0 + 0.040, ZP, 1.300, bev=0.002, segs=1)
        x0, x1 = sorted((s * 0.530, s * 0.570))
        for z0 in (1.060, 1.260):                 # поздовжні рейки
            zb.box(g, "Rack_Rail", x0, x1, -0.820, 0.300, z0, z0 + 0.040, bev=0.002, segs=1)
        x0, x1 = sorted((s * 0.183, s * 0.187))   # низькі перегородки між касетами
        zb.box(g, "Rack_Divider", x0, x1, -0.800, 0.280, zf, zf + 0.130, bev=0.001, segs=1)
    for y0 in (-0.820, 0.260):
        zb.box(g, "Rack_Rail", -0.570, 0.570, y0, y0 + 0.040, 1.260, 1.300, bev=0.002, segs=1)
    zb.box(g, "Rack_Front", -0.570, 0.570, 0.260, 0.300, ZP, 1.060, bev=0.002, segs=1)
    # лоток над заднім краєм палуби (над фартухом — 4,5 см) і відкидний жолоб на шарнірі за ним:
    # міна з нижнього ярусу сповзає на ґрунт; на марші жолоб складають угору
    hw = 0.185
    zb.box(g, "Chute_Tray", -hw, hw, -0.960, -0.800, zf - 0.004, zf, bev=0.001, segs=1)
    for s in (-1, 1):
        x0, x1 = sorted((s * hw, s * (hw + 0.004)))
        zb.box(g, "Chute_TraySide", x0, x1, -0.960, -0.800, zf - 0.004, zf + 0.070, bev=0.001, segs=1)
    a, b = Vector((0, -0.960, zf)), Vector((0, -1.300, 0.560))
    d = (b - a).normalized()
    L = (b - a).length
    up = Vector((0, -d.z, d.y))                   # нормаль дна жолоба (вгору-назад)
    if up.z < 0:
        up = -up
    zb.plate(g, "Chute_Bottom", [(-hw, 0), (hw, 0), (hw, L), (-hw, L)], (), t=0.004,
             M=zb.frame(a - up * 0.004, (1, 0, 0), d), bev=0.001)
    for s in (-1, 1):
        o = a + Vector((s * hw, 0, 0)) - up * 0.004
        zb.plate(g, "Chute_Side", [(0, 0), (L, 0), (L, 0.070), (0, 0.070)], (), t=0.004,
                 M=zb.frame(o if s < 0 else o - Vector((0.004, 0, 0)), d, up), bev=0.001)
        zb.tube(g, "Chute_Stay", [(s * 0.420, -0.820, 1.260), (s * (hw + 0.010), -1.150, 0.720)], 0.007,
                mat='strap', res=2)
    cyl(g, "Chute_Hinge", (-hw - 0.010, a.y, a.z - 0.010), (hw + 0.010, a.y, a.z - 0.010), 0.014, 'strap', 16)
    q = a + d * 0.200                             # одна міна на жолобі
    lathe(g, "Mine_Chute", MINE, Matrix.Translation(q) @ up.to_track_quat('Z', 'Y').to_matrix().to_4x4(), 'mine')


# ------------------------------------------------------------------ B3 «РЕБ / ретранслятор»
def variant_b3():
    g = 'B3'
    zc1 = ZP + 0.280
    zb.box(g, "EW_Cabinet", -0.460, 0.460, -0.840, -0.180, ZP, zc1, bev=0.012, segs=2)
    zb.box(g, "EW_LidSeam", -0.464, 0.464, -0.844, -0.176, zc1 - 0.060, zc1 - 0.050, mat='strap', bev=0.002, segs=1)
    for i in range(13):                           # ребра охолодження вздовж руху (обдув)
        x = -0.420 + i * 0.070
        zb.box(g, "EW_Fin", x - 0.003, x + 0.003, -0.800, -0.220, zc1, zc1 + 0.045, bev=0.001, segs=1)
    for s in (-1, 1):
        for y in (-0.700, -0.320):
            x0, x1 = sorted((s * 0.460, s * 0.478))
            zb.box(g, "EW_Latch", x0, x1, y - 0.030, y + 0.030, zc1 - 0.120, zc1 - 0.040, mat='strap', bev=0.004,
                   segs=1)
        whip_base = Vector((s * 0.400, -0.780, zc1 + 0.045))
        cyl(g, "Whip_Spring", whip_base, whip_base + Vector((0, 0, 0.050)), 0.011, 'strap', 12)
        cyl(g, "Whip_Rod", whip_base + Vector((0, 0, 0.050)), whip_base + Vector((0, 0, 0.420)), 0.004, 'strap', 8)
    # щогла-обрубок на поперечці й 4 секторні панельні антени (кругова діаграма)
    yc = 0.200
    zb.box(g, "EW_MastBase", -0.150, 0.150, yc - 0.120, yc + 0.120, ZP, ZP + 0.012, bev=0.003, segs=1)
    zp0, zp1 = 1.060, 1.520
    cyl(g, "EW_Mast", (0, yc, ZP + 0.012), (0, yc, zp1 + 0.005), 0.045, 'paint', 24)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        c = Vector((0.175 * math.cos(a), yc + 0.175 * math.sin(a), (zp0 + zp1) / 2))
        Mr = Matrix.Translation(c) @ Matrix.Rotation(a - math.radians(90), 4, 'Z')
        rot_box(g, "EW_Panel", (0.180, 0.060, zp1 - zp0), Mr, 'radome', bev=0.012, segs=2)
        for zz in (zp0 + 0.080, zp1 - 0.080):
            m = Vector((0.090 * math.cos(a), yc + 0.090 * math.sin(a), zz))
            rot_box(g, "EW_Arm", (0.020, 0.150, 0.030), Matrix.Translation(m) @ Matrix.Rotation(a - math.radians(90), 4, 'Z'),
                    'paint', bev=0.003, segs=1)
    cyl(g, "EW_Cap", (0, yc, zp1 + 0.005), (0, yc, zp1 + 0.025), 0.070, 'paint', 32)
    zb.tube(g, "EW_Cable", [(0.0, -0.180, ZP + 0.150), (0.0, 0.020, ZP + 0.060), (0.0, yc - 0.050, ZP + 0.060),
                            (0.0, yc - 0.045, ZP + 0.150)], 0.012, bend=0.04, mat='strap', res=2)


pallet()
variant_l1()
variant_l2()
variant_b1()
variant_b2()
variant_b3()
objs = {}
for key, name in (('Pal', 'Var_Pallet'), ('L1', 'Var_L1'), ('L2', 'Var_L2'), ('B1', 'Var_B1'), ('B2', 'Var_B2'),
                  ('B3', 'Var_B3')):
    ob = zb.join_group(name, zb.PARTS.pop(key))
    ob.parent = root
    objs[name] = ob
tur = zb.join_group("Var_B1_Turret", zb.PARTS.pop('B1T'), pivot=(0, YR, ZR))
tur.parent = root
objs['Var_B1_Turret'] = tur
for k, ob in objs.items():
    print("MOD", k, sum(len(p.vertices) - 2 for p in ob.data.polygons), "tris",
          [round(max((ob.matrix_world @ Vector(c))[i] for c in ob.bound_box), 3) for i in range(3)],
          [round(min((ob.matrix_world @ Vector(c))[i] for c in ob.bound_box), 3) for i in range(3)])

# ------------------------------------------------------------------ рендери
if os.environ.get("MOD_NO_RENDER"):                 # лише геометрія (швидка перевірка)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "zmiy_deck_modules.blend"))
    sys.exit(0)
sc = bpy.context.scene
mine = {o.name for o in bpy.data.collections["Zmiy_Logistic"].all_objects}
for o in sc.objects:
    if o.name not in mine or o.name.startswith(('Module_', 'UCX_')):
        o.hide_render = True
cam = ze.setup_stage()
ze.REN = OUT
SHOW = {'base': [], 'L1': ['Var_Pallet', 'Var_L1'], 'L2': ['Var_Pallet', 'Var_L2'],
        'B1': ['Var_Pallet', 'Var_B1', 'Var_B1_Turret'], 'B2': ['Var_Pallet', 'Var_B2'], 'B3': ['Var_Pallet', 'Var_B3']}
ze.VIEWS['m34'] = ((-3.6, 3.9, 1.85), (0.0, -0.05, 0.70), 50, None)
ze.VIEWS['mrear34'] = ((3.4, -3.9, 1.90), (0.0, -0.20, 0.70), 50, None)


def show(tag):
    for k, ob in objs.items():
        ob.hide_render = k not in SHOW[tag]


def sprite(tag):
    """Вигляд як у грі: орто-камера 65° над горизонтом, 29,09 px/м (у грі ще ×0,3)."""
    cd = cam.data
    cd.type = 'ORTHO'
    px = 160
    cd.ortho_scale = px / (320 / 11)
    sc.render.resolution_x = sc.render.resolution_y = px
    sc.render.resolution_percentage = 100
    el, az = math.radians(65), math.radians(-120)
    tgt = Vector((0, -0.03, 0.45))
    d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
    cam.location = tgt + d * 10
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sun = bpy.data.objects["Stage_Sun"]
    sun.rotation_euler = (math.radians(15), 0, math.radians(-160))
    g = bpy.data.objects["Stage_Ground"]
    g.hide_render = True
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = os.path.join(OUT, "sprite_%s.png" % tag)
    bpy.ops.render.render(write_still=True)
    g.hide_render = False
    sc.render.film_transparent = False
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = int(os.environ.get("ZMIY_RES_PCT", "100"))
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.color_mode = 'RGB'


for tag in ('L1', 'L2', 'B1', 'B2', 'B3', 'base'):
    show(tag)
    if tag != 'base':
        ze.render_views(cam, ["m34", "mrear34"], "_" + tag)
    sprite(tag)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "zmiy_deck_modules.blend"))
print("MODULES DONE")
