# -*- coding: utf-8 -*-
"""Три варіанти надбудов над корпусом «Змія» (тест, поверх поточної моделі).
blender -b --factory-startup --python concepts/masts_m123.py -- <out_dir>
M1: портал (арка) з профільної труби 50×50 над передньою частиною палуби: Starlink, камера, штирі.
M2: відкидна телескопічна щогла ззаду (піднята), поворотна голова + mesh-антена; Starlink на лотку над носом.
M3: Т-пілон спереду з коробчастого профілю: платформа зі Starlink, камера під нею, штирі на кінцях.
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
ZT, ZW, SX, WT = P['deck_z'], P['wall_z1'], P['side_x'], P['wall_t']
XI = SX - WT                                   # внутрішня грань бортика


def cyl(g, name, p0, p1, r, mat, segs=24):
    bm = bmesh.new()
    zb.bm_cyl(bm, Vector(p0), Vector(p1), r, segs)
    zb.bm_to_part(g, name, bm, [mat], angle=40.0)


def lens(g, x, y_face, z, r, depth=0.010, axis=Vector((0, 1, 0))):
    p0 = Vector((x, y_face, z))
    cyl(g, "Lens_Bezel", p0 - axis * 0.002, p0 + axis * depth, r + 0.006, 'paint')
    cyl(g, "Lens_Glass", p0 + axis * depth, p0 + axis * (depth + 0.0015), r, 'lens')


def whip(g, base, length=0.36):
    b = Vector(base)
    cyl(g, "Whip_Base", b, b + Vector((0, 0, 0.012)), 0.020, 'zinc')
    cyl(g, "Whip_Spring", b + Vector((0, 0, 0.012)), b + Vector((0, 0, 0.055)), 0.011, 'dark')
    cyl(g, "Whip_Rod", b + Vector((0, 0, 0.055)), b + Vector((0, 0, 0.055 + length)), 0.004, 'dark', 10)
    cyl(g, "Whip_Tip", b + Vector((0, 0, 0.055 + length)), b + Vector((0, 0, 0.065 + length)), 0.006, 'dark', 10)


def starlink(g, cx, cy, z0):
    zb.box(g, "Starlink_Cover", cx - 0.158, cx + 0.158, cy - 0.138, cy + 0.138, z0, z0 + 0.046,
           mat='cover', bev=0.012, segs=3)


def cam_head(g, cx, y_back, y_front, z0, z1, w=0.10):
    """Блок камери (денна/нічна + тепловізор + LED), об'єктиви дивляться вперед (+Y)."""
    zb.box(g, "Cam_Body", cx - w, cx + w, y_back, y_front, z0, z1, bev=0.008, segs=2)
    zc = (z0 + z1) / 2 + 0.008
    lens(g, cx - 0.040, y_front, zc, 0.020)
    lens(g, cx + 0.040, y_front, zc, 0.017)
    for s in (-1, 1):
        zb.box(g, "Cam_LED", cx + s * 0.080 - 0.014, cx + s * 0.080 + 0.014, y_front, y_front + 0.0015,
               z0 + 0.010, z0 + 0.026, mat='led', bev=0.002, segs=1)


def tri(g, name, pts_yz, x0, t=0.006):
    zb.plate(g, name, pts_yz, (), t=t, M=zb.frame((x0, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.0012)


def base_flange(g, cx, cy, wx, wy):
    zb.box(g, "Base_Flange", cx - wx / 2, cx + wx / 2, cy - wy / 2, cy + wy / 2, ZT, ZT + 0.008, bev=0.002, segs=1)
    zb.fasteners(g, "Base_Bolts", [(Vector((cx + sx * (wx / 2 - 0.018), cy + sy * (wy / 2 - 0.018), ZT + 0.008)),
                                    Vector((0, 0, 1))) for sx in (-1, 1) for sy in (-1, 1)])


# ------------------------------------------------------------------ M1 портал
def mast_portal():
    g = 'M1'
    yc, zt, a = 0.400, 1.300, 0.050           # площина порталу, верх, профіль 50×50
    for s in (-1, 1):
        x0, x1 = sorted((s * (XI - a), s * XI))
        zb.box(g, "Arch_Post", x0, x1, yc - a / 2, yc + a / 2, ZT, zt, bev=0.004, segs=1)
        # косинка назад — тримає портал від розгойдування вперед-назад
        tri(g, "Arch_Gusset", [(yc - a / 2, ZT), (yc - a / 2, 1.120), (yc - 0.260, ZT)],
            (s * (XI - a / 2) - 0.003))
        x0, x1 = sorted((s * (XI - a - 0.010), s * (XI + 0.0)))
        zb.box(g, "Arch_Foot", x0, x1, yc - 0.060, yc + 0.060, ZT, ZT + 0.008, bev=0.002, segs=1)
    zb.box(g, "Arch_Beam", -XI, XI, yc - a / 2, yc + a / 2, zt - a, zt, bev=0.004, segs=1)
    zb.box(g, "Arch_Tray", -0.175, 0.175, yc - 0.150, yc + 0.150, zt, zt + 0.006, bev=0.002, segs=1)
    starlink(g, 0.0, yc, zt + 0.006)
    cam_head(g, 0.0, yc + a / 2, yc + a / 2 + 0.090, zt - a - 0.080, zt - a)
    for s in (-1, 1):
        whip(g, (s * (XI - a / 2), yc, zt))


# ------------------------------------------------------------------ M2 відкидна щогла (піднята)
def mast_folding():
    g = 'M2'
    hy, hz = -0.740, 0.985                    # вісь шарніра
    for s in (-1, 1):                         # щоки шарніра на кронштейні ззаду
        x0 = 0.045 if s > 0 else -0.053
        zb.plate(g, "Hinge_Cheek", [(-0.810, ZT), (-0.670, ZT), (-0.690, 1.010), (-0.790, 1.010)], (), t=0.008,
                 M=zb.frame((x0, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.0015)
    base_flange(g, 0.0, -0.740, 0.180, 0.200)
    cyl(g, "Hinge_Pin", (-0.075, hy, hz), (0.075, hy, hz), 0.012, 'zinc')
    zb.box(g, "Mast_Outer", -0.035, 0.035, hy - 0.035, hy + 0.035, hz - 0.030, 1.900, bev=0.004, segs=1)
    zb.box(g, "Mast_Collar", -0.042, 0.042, hy - 0.042, hy + 0.042, 1.880, 1.930, bev=0.004, segs=1)
    zb.box(g, "Mast_Inner", -0.026, 0.026, hy - 0.026, hy + 0.026, 1.900, 2.380, bev=0.003, segs=1)
    # лінійний актуатор: кронштейн на палубі → вушко на щоглі
    a0, a1 = Vector((0, -0.420, ZT + 0.040)), Vector((0, hy + 0.040, 1.420))
    zb.box(g, "Act_Lug", -0.030, 0.030, -0.450, -0.390, ZT, ZT + 0.060, bev=0.003, segs=1)
    mid = a0.lerp(a1, 0.55)
    cyl(g, "Act_Body", a0, mid, 0.024, 'paint')
    cyl(g, "Act_Rod", mid, a1, 0.012, 'zinc')
    # верх: поворотна голова + mesh-антена
    top = 2.380
    cyl(g, "PTZ_Ring", (0, hy, top), (0, hy, top + 0.025), 0.065, 'paint', 32)
    zb.box(g, "PTZ_Body", -0.075, 0.075, hy - 0.065, hy + 0.075, top + 0.050, top + 0.165, bev=0.014, segs=3)
    lens(g, -0.032, hy + 0.075, top + 0.110, 0.020)
    lens(g, 0.032, hy + 0.075, top + 0.110, 0.018)
    for s in (-1, 1):
        zb.box(g, "PTZ_Yoke", *sorted((s * 0.075, s * 0.087)), hy - 0.020, hy + 0.020, top + 0.025, top + 0.150,
               bev=0.003, segs=1)
    whip(g, (0.0, hy - 0.020, top + 0.165), length=0.30)
    # транспортний ложемент спереду: сюди лягає щогла у складеному стані
    for s in (-1, 1):
        tri(g, "Cradle_Side", [(0.480, ZT), (0.560, ZT), (0.560, 1.020), (0.480, 1.020)], s * 0.045 - (0.006 if s < 0 else 0))
    zb.box(g, "Cradle_Pad", -0.045, 0.045, 0.480, 0.560, 0.950, 0.960, mat='dark', bev=0.002, segs=1)
    base_flange(g, 0.0, 0.520, 0.140, 0.120)
    # Starlink на лотку над носом (як у варіанті A), подалі від щогли
    cheek = [(0.662, 0.871), (0.712, 0.803), (0.800, 0.858), (0.900, 1.000), (0.662, 1.000)]
    for s in (-1, 1):
        tri(g, "Nose_Cheek", cheek, 0.144 if s > 0 else -0.150)
    zb.box(g, "Nose_Tray", -0.165, 0.165, 0.664, 0.936, 1.000, 1.006, bev=0.002, segs=1)
    starlink(g, 0.0, 0.800, 1.006)
    cam_head(g, 0.0, 0.668, 0.792, 0.880, 0.960, w=0.144)


# ------------------------------------------------------------------ M3 Т-пілон
def mast_pylon():
    g = 'M3'
    yc, zt = 0.520, 1.220
    base_flange(g, 0.0, yc, 0.240, 0.200)
    zb.box(g, "Pylon", -0.060, 0.060, yc - 0.045, yc + 0.045, ZT, zt, bev=0.005, segs=1)
    # косинка під платформою ззаду (спереду платформу підпирає корпус камери); косинки біля основи
    tri(g, "Pylon_Gusset_Top", [(yc - 0.045, zt - 0.160), (yc - 0.045, zt), (yc - 0.170, zt)], -0.003)
    for s in (-1, 1):
        tri(g, "Pylon_Gusset_Base", [(yc + s * 0.045, ZT + 0.008), (yc + s * 0.045, ZT + 0.110),
                                     (yc + s * 0.110, ZT + 0.008)], -0.003)
    zb.box(g, "Pylon_Arm", -0.360, 0.360, yc - 0.030, yc + 0.030, zt - 0.040, zt, bev=0.003, segs=1)
    zb.box(g, "Pylon_Deck", -0.180, 0.180, yc - 0.150, yc + 0.175, zt, zt + 0.008, bev=0.002, segs=1)
    starlink(g, 0.0, yc + 0.010, zt + 0.008)
    cam_head(g, 0.0, yc + 0.045, yc + 0.160, zt - 0.100, zt)
    for s in (-1, 1):
        whip(g, (s * 0.330, yc, zt), length=0.30)


mast_portal()
mast_folding()
mast_pylon()
objs = {}
for k in ('M1', 'M2', 'M3'):
    ob = zb.join_group(k, zb.PARTS.pop(k))
    ob.parent = root
    objs[k] = ob

# ------------------------------------------------------------------ рендери
sc = bpy.context.scene
mine = {o.name for o in bpy.data.collections["Zmiy_Logistic"].all_objects}
for o in sc.objects:
    if o.name not in mine or o.name.startswith(('Module_', 'UCX_')):
        o.hide_render = True
cam = ze.setup_stage()
sc.render.resolution_x, sc.render.resolution_y = 1200, 1200
VIEWS = {
    'p34': ((-3.5, 3.9, 2.05), (0.0, -0.05, 1.08), 46, None),
    'side': ((6.0, -0.02, 1.32), None, None, 3.10),
}
for k in objs:
    for k2, ob in objs.items():
        ob.hide_render = k2 != k
    for v, (loc, tgt, lens_mm, ortho) in VIEWS.items():
        cd = cam.data
        if ortho:
            cd.type, cd.ortho_scale = 'ORTHO', ortho
            cam.location = loc
            cam.rotation_euler = (math.radians(90), 0, math.radians(90))
        else:
            cd.type, cd.lens = 'PERSP', lens_mm
            cam.location = loc
            cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        ze.aim_sun(cam)
        sc.render.image_settings.file_format = 'JPEG'
        sc.render.filepath = os.path.join(OUT, "%s_%s.jpg" % (k, v))
        bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "zmiy_masts.blend"))
print("MASTS DONE")
