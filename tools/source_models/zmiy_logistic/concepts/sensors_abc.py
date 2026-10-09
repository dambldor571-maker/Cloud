# -*- coding: utf-8 -*-
"""Тестові варіанти обладнання (сенсори, антени, Starlink) поверх поточної моделі «Змія».
blender -b --factory-startup --python concepts/sensors_abc.py -- <out_dir>
A: низька голова на носі + Starlink на ній (L2), задня камера, шайби + штирі на задніх кутах бортиків.
B: камери врізані в лобовий лист + 4 кутові, шайби, Starlink у низькій касеті на палубі (L1).
C: поворотна оптико-електронна голова на стійці (Turret), штирі, Starlink на задньому містку (L3).
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
zb.MAT['lens'] = zb.make_material("Var_Lens", "#0B0D0E", 0.12, 0.0)
zb.MAT['led'] = zb.make_material("Var_LED", "#D6D6CC", 0.22, 0.0)
zb.MAT['cover'] = zb.make_material("Var_Cover", "#3A4130", 0.80, 0.0)
zb.MAT['dark'] = zb.make_material("Var_Dark", "#1E1F1C", 0.60, 0.0)

ZT, ZW = P['deck_z'], P['wall_z1']            # верх палуби 0,862, верх бортиків 0,990
SX, WT = P['side_x'], P['wall_t']


def cyl(group, name, p0, p1, r, mat, segs=24):
    bm = bmesh.new()
    zb.bm_cyl(bm, Vector(p0), Vector(p1), r, segs)
    zb.bm_to_part(group, name, bm, [mat], angle=40.0)


def lens(group, x, y_face, z, r, depth=0.010, axis=Vector((0, 1, 0))):
    """Обідок (олива) + скло на передній грані."""
    p0 = Vector((x, y_face, z))
    cyl(group, "Lens_Bezel", p0 - axis * 0.002, p0 + axis * depth, r + 0.006, 'paint')
    cyl(group, "Lens_Glass", p0 + axis * depth, p0 + axis * (depth + 0.0015), r, 'lens')


def dome(group, name, c, r, h, mat='dark'):
    bm = bmesh.new()
    prof = [(0.0, 0.0), (r, 0.0), (r, h * 0.35)]
    prof += [(r * math.cos(math.radians(a)), h * 0.35 + (h * 0.65) * math.sin(math.radians(a))) for a in (25, 50, 70, 85)]
    prof += [(0.0, h)]
    zb.bm_lathe(bm, prof, 32, Matrix.Translation(Vector(c)))
    zb.bm_to_part(group, name, bm, [mat], angle=40.0)


def whip(group, base, length=0.36):
    """Штир на пружинній основі (пружина гне штир від гілок)."""
    b = Vector(base)
    cyl(group, "Whip_Base", b, b + Vector((0, 0, 0.012)), 0.020, 'zinc')
    cyl(group, "Whip_Spring", b + Vector((0, 0, 0.012)), b + Vector((0, 0, 0.055)), 0.011, 'dark')
    cyl(group, "Whip_Rod", b + Vector((0, 0, 0.055)), b + Vector((0, 0, 0.055 + length)), 0.004, 'dark', 10)
    cyl(group, "Whip_Tip", b + Vector((0, 0, 0.055 + length)), b + Vector((0, 0, 0.065 + length)), 0.006, 'dark', 10)


def starlink(group, cx, cy, z0, cover=True):
    """Starlink Mini 298×259×38,5 мм у захисному кожусі кольору олива."""
    hx, hy = 0.158, 0.138
    zb.box(group, "Starlink_Cover", cx - hx, cx + hx, cy - hy, cy + hy, z0, z0 + 0.046,
           mat='cover' if cover else 'led', bev=0.012, segs=3)


def rear_corner_brackets(group, pucks=True, whips=True):
    """Кронштейни на внутрішній стороні бортиків біля задніх кутів (найвища точка, метал палуби — «земля»)."""
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.500, s * (SX - WT)))
        zb.box(group, "Ant_Bracket", x0, x1, -0.770, -0.620, ZW - 0.006, ZW, bev=0.0015, segs=1)
        xt0, xt1 = sorted((s * (SX - WT - 0.006), s * (SX - WT)))
        zb.box(group, "Ant_Tab", xt0, xt1, -0.770, -0.620, ZW - 0.060, ZW, bev=0.0015, segs=1)
        if pucks:
            dome(group, "Ant_Puck", (s * 0.555, -0.735, ZW), 0.050, 0.028)
        if whips:
            whip(group, (s * 0.555, -0.648, ZW))


# ------------------------------------------------------------------ A
def variant_a():
    g = 'Var_A'
    # щоки-кронштейни на похилому листі носа: тримають голову й лоток Starlink (козирок над об'єктивами)
    cheek = [(0.662, 0.871), (0.712, 0.803), (0.800, 0.858), (0.900, 1.000), (0.662, 1.000)]
    for s in (-1, 1):
        x0 = 0.144 if s > 0 else -0.150
        zb.plate(g, "Head_Cheek", cheek, (), t=0.006, M=zb.frame((x0, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.0012)
    zb.box(g, "Head_Body", -0.144, 0.144, 0.668, 0.792, 0.870, 0.960, bev=0.008, segs=2)
    lens(g, -0.055, 0.792, 0.920, 0.024)              # денна/нічна камера
    lens(g, 0.055, 0.792, 0.920, 0.020)               # тепловізор
    for s in (-1, 1):                                 # LED-фари
        zb.box(g, "Head_LED", s * 0.115 - 0.026, s * 0.115 + 0.026, 0.792, 0.7935, 0.880, 0.906, mat='led', bev=0.002, segs=1)
    zb.box(g, "Head_IR", -0.020, 0.020, 0.792, 0.7935, 0.882, 0.898, mat='lens', bev=0.002, segs=1)
    zb.box(g, "Tray", -0.165, 0.165, 0.664, 0.936, 1.000, 1.006, bev=0.002, segs=1)
    starlink(g, 0.0, 0.800, 1.006)
    # задня камера на задній панелі корпусу
    y = P['hull_y0'] - 0.005
    zb.box(g, "RearCam", -0.045, 0.045, y - 0.060, y, 0.585, 0.645, bev=0.006, segs=2)
    zb.box(g, "RearCam_Visor", -0.050, 0.050, y - 0.080, y, 0.645, 0.649, bev=0.001, segs=1)
    lens(g, 0.0, y - 0.060, 0.615, 0.016, axis=Vector((0, -1, 0)))
    rear_corner_brackets(g, pucks=True, whips=True)


# ------------------------------------------------------------------ B
def variant_b():
    g = 'Var_B'
    ng = zb.nose_geometry()
    on, dn = ng['on_plate'], ng['dn']
    up = -dn

    def flush(name, s, x, w, h, mat, t):
        c = on(s, x)
        M = zb.frame(c, (-1, 0, 0), up)
        zb.plate(g, name, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], (), t=t, M=M,
                 mat=mat, bev=0.0008)
    flush("Win_Frame", 0.07, 0.0, 0.17, 0.075, 'paint', 0.004)      # бронескло камер у лобовому листі
    flush("Win_Glass", 0.07, 0.0, 0.15, 0.055, 'lens', 0.0045)
    for s in (-1, 1):
        flush("LED_Frame", 0.07, s * 0.27, 0.085, 0.045, 'paint', 0.004)
        flush("LED_Lens", 0.07, s * 0.27, 0.070, 0.030, 'led', 0.0045)
    # задня камера врізана в задню панель
    y = P['hull_y0'] - 0.005
    zb.box(g, "RearWin", -0.050, 0.050, y - 0.004, y, 0.590, 0.630, mat='paint', bev=0.001, segs=1)
    zb.box(g, "RearWin_Glass", -0.040, 0.040, y - 0.0045, y, 0.596, 0.624, mat='lens', bev=0.001, segs=1)
    # 4 кутові камери кругового огляду на зовнішніх гранях бортиків
    for s in (-1, 1):
        for yy, zc, sy in ((0.560, 0.930, 1), (-0.840, 0.900, -1)):
            x0, x1 = sorted((s * SX, s * (SX + 0.040)))
            zb.box(g, "CornerCam", x0, x1, yy - 0.030, yy + 0.030, zc - 0.022, zc + 0.022, bev=0.006, segs=2)
            d = Vector((s, sy, 0)).normalized()
            lens(g, s * (SX + 0.028), yy + sy * 0.022, zc, 0.009, depth=0.006, axis=d)
    rear_corner_brackets(g, pucks=True, whips=False)
    # Starlink у низькій касеті в передній частині палуби (вільна від вантажу зона)
    zb.box(g, "SL_Cassette", -0.168, 0.168, 0.322, 0.618, ZT, ZT + 0.012, bev=0.003, segs=1)
    zb.box(g, "SL_Lid", -0.154, 0.154, 0.336, 0.604, ZT + 0.012, ZT + 0.016, mat='cover', bev=0.002, segs=1)


# ------------------------------------------------------------------ C
def variant_c():
    g = 'Var_C'
    t = 'Var_C_Turret'
    cheek = [(0.662, 0.871), (0.712, 0.803), (0.785, 0.848), (0.785, 1.000), (0.662, 1.000)]
    for s in (-1, 1):
        x0 = 0.060 if s > 0 else -0.066
        zb.plate(g, "Ped_Cheek", cheek, (), t=0.006, M=zb.frame((x0, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.0012)
    zb.box(g, "Ped_Top", -0.090, 0.090, 0.664, 0.790, 0.994, 1.000, bev=0.0015, segs=1)
    yc = 0.730
    cyl(t, "PTZ_Ring", (0, yc, 1.000), (0, yc, 1.026), 0.075, 'paint', 40)
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.080, s * 0.092))
        zb.box(t, "PTZ_Yoke", x0, x1, yc - 0.024, yc + 0.024, 1.026, 1.170, bev=0.004, segs=1)
        cyl(t, "PTZ_Hub", (s * 0.092, yc, 1.145), (s * 0.100, yc, 1.145), 0.018, 'paint')
    zb.box(t, "PTZ_Body", -0.078, 0.078, yc - 0.070, yc + 0.070, 1.085, 1.205, bev=0.014, segs=3)
    zb.box(t, "PTZ_Hood", -0.082, 0.082, yc - 0.020, yc + 0.088, 1.205, 1.210, bev=0.002, segs=1)
    lens(t, -0.034, yc + 0.070, 1.150, 0.022)          # денна камера з трансфокатором
    lens(t, 0.034, yc + 0.070, 1.150, 0.020)           # тепловізор
    lens(t, 0.0, yc + 0.070, 1.108, 0.007, depth=0.006)  # лазерний далекомір
    # задній місток із гнутого швелера на бортиках: Starlink + штирі (рознесені на 40 см)
    y0, y1 = -0.770, -0.500
    zb.box(g, "Bridge_Top", -SX, SX, y0, y1, ZW, ZW + 0.006, bev=0.0015, segs=1)
    for yy in (y0, y1 - 0.004):
        zb.box(g, "Bridge_Flange", -(SX - WT - 0.002), SX - WT - 0.002, yy, yy + 0.004, ZW - 0.025, ZW, bev=0.001, segs=1)
    zb.fasteners(g, "Bridge_Bolts", [(Vector((s * (SX - 0.002), yy, ZW + 0.006)), Vector((0, 0, 1)))
                                     for s in (-1, 1) for yy in (y0 + 0.04, y1 - 0.04)])
    starlink(g, 0.0, (y0 + y1) / 2, ZW + 0.006)
    for s in (-1, 1):
        whip(g, (s * 0.530, -0.635, ZW + 0.006))


variant_a()
variant_b()
variant_c()
objs = {}
for key in ('Var_A', 'Var_B', 'Var_C'):
    ob = zb.join_group(key, zb.PARTS.pop(key))
    ob.parent = root
    objs[key] = ob
tur = zb.join_group("Var_C_Turret", zb.PARTS.pop('Var_C_Turret'), pivot=(0, 0.730, 1.000))
tur.parent = root
objs['Var_C_Turret'] = tur

# ------------------------------------------------------------------ рендери
sc = bpy.context.scene
mine = {o.name for o in bpy.data.collections["Zmiy_Logistic"].all_objects}
for o in sc.objects:
    if o.name not in mine:
        o.hide_render = True
for o in sc.objects:
    if o.name.startswith(('Module_', 'UCX_')):
        o.hide_render = True
cam = ze.setup_stage()
ze.REN = OUT
SHOW = {'base': [], 'A': ['Var_A'], 'B': ['Var_B'], 'C': ['Var_C', 'Var_C_Turret']}


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


for tag in ('A', 'B', 'C', 'base'):
    show(tag)
    if tag != 'base':
        ze.render_views(cam, ["front34", "rear34"], "_" + tag)
    sprite(tag)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "zmiy_variants.blend"))
print("VARIANTS DONE")
