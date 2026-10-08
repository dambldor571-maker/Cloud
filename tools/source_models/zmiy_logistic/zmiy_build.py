# -*- coding: utf-8 -*-
"""
НРК «Змій Логістичний» (Rovertech, 2026) — hero-asset для гри, Blender 4.2+ (перевірено на 4.5 LTS).

Будує повну геометрію (без текстур) у колекції "Zmiy_Logistic":
    Zmiy_Logistic (empty, на землі під центром)
    ├─ Body      — корпус, кузов-«ванна», ніс, корма, фаркоп, болти
    ├─ Cage      — дуга каркаса, поручні, кронштейни
    ├─ Camera    — блок камери (дочірній до Cage не робимо: камера окремо для рушія)
    ├─ Wheel_FL / Wheel_FR / Wheel_RL / Wheel_RR — півот у центрі колеса, вісь обертання = локальна X
    ├─ Decal_*   — логотип і напис Rovertech (окремо, товарний знак — можна вимкнути)
    └─ Module_*  — опційні модулі (Starlink, вантаж, вила-концепт), сховані за замовчуванням

Запуск у Blender: Scripting → Open → Run Script.  Без GUI:
    blender -b --factory-startup --python zmiy_build.py
Текстури, розгортка й експорт — окремі скрипти (zmiy_texture.py, zmiy_export.py), див. README.md.

Координати: X праворуч, Y вперед (ніс), Z вгору, метри, 1 юніт = 1 м.
Розміри уточнено по фото з калібруванням камер (див. README.md, розділ «Розміри»).
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

# =================================================================== параметри
P = dict(
    # --- колеса (шина 25x10-12 класу ATV/R-1; обід 12" сталевий, глибокий)
    tire_r=0.325, tire_w=0.245, carcass_r=0.300,
    rim_r=0.1524, rim_lip_r=0.171, rim_hw=0.103,
    disc_w=-0.052,            # площина диска відносно центру колеса (від'ємно = всередину)
    wheel_x=0.635, axle_f=0.150, axle_r=-0.600, wheel_z=0.325,
    lugs=22, wheel_segs=128,
    # --- нижній корпус (вузький короб між колесами)
    hull_x=0.455, hull_z0=0.230, hull_y0=-0.865, hull_y1=0.490,
    # --- кузов-«ванна» над колесами
    deck_z=0.745, deck_t=0.004, side_x=0.780, wall_t=0.005,
    wall_z0=0.690, wall_z1=0.830, tub_y0=-0.900, tub_y1=0.290,
    # --- ніс (лобовий лист, що звисає з передньої «губи» палуби)
    nose_top_y=0.585,         # верхня кромка лобового листа (під губою)
    nose_lip_z0=0.700,        # низ «губи» по периметру переду палуби
    nose_top_hw=0.640,        # півширина верху лобового листа
    chin_y=0.720, chin_z=0.360, chin_hw=0.560, chin_cut=0.075,
    nose_bot_y=0.620, nose_bot_z=0.250, nose_bot_hw=0.480,
    nose_back_y=0.495,        # задня стінка носа (перед передніми шинами)
    # --- каркас
    hoop_y=0.310, hoop_x=0.690, hoop_top=1.360, hoop_r=0.0225, hoop_bend=0.160,
    brace_r=0.011, brace_top_x=0.270, brace_low_z=1.070,
    rail_x=0.748, rail_r=0.020, rail_z=0.945, rail_z2=1.070, rail_y_rear=-0.800,
    rail_step_y0=-0.020, rail_step_y1=0.140, rail_posts=(-0.450, -0.080),
    # --- корма
    gate_hw=0.505, gate_z0=0.600, gate_z1=0.900, gate_cut=0.075,
    rear_hw=0.400, rear_z0=0.260, rear_z1=0.575,
    hitch_z=0.410,
)

COLL_NAME = "Zmiy_Logistic"
MAT_DEF = {
    # ключ: (назва, sRGB hex, roughness, metallic)
    'paint': ("Zmiy_Paint_Olive", "#434A37", 0.74, 0.0),
    'tube': ("Zmiy_Tube_Black", "#1A1A1A", 0.45, 0.0),
    'rubber': ("Zmiy_Rubber", "#1C1C1C", 0.90, 0.0),
    'rim': ("Zmiy_Rim_Black", "#151515", 0.50, 0.0),
    'zinc': ("Zmiy_Bolt_Zinc", "#8A8A85", 0.35, 1.0),
    'steel': ("Zmiy_Steel_Bare", "#5E5E5A", 0.38, 1.0),
    'glass': ("Zmiy_Glass", "#050505", 0.05, 0.0),
    'cam': ("Zmiy_Camera_Housing", "#2A2A2A", 0.55, 0.0),
    'orange': ("Zmiy_Knob_Orange", "#C8561E", 0.45, 0.0),
    'decal': ("Zmiy_Decal_Logo", "#111111", 0.80, 0.0),
}


# =================================================================== службове
def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def make_material(name, hexcol, rough, metal):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    h = hexcol.lstrip("#")
    rgb = [srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)]
    bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*rgb, 1.0)
    m.roughness = rough
    m.metallic = metal
    return m


def reset_collection(name):
    coll = bpy.data.collections.get(name)
    if coll:
        def purge(c):
            for ch in list(c.children):
                purge(ch)
                bpy.data.collections.remove(ch)
            for ob in list(c.objects):
                data = ob.data
                bpy.data.objects.remove(ob, do_unlink=True)
                if data is not None and data.users == 0:
                    if isinstance(data, bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
                    elif isinstance(data, bpy.types.Curve):
                        bpy.data.curves.remove(data)
        purge(coll)
    else:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


COLL = None
MAT = {}
PARTS = {}          # група -> [object]


def V(*a):
    return Vector(a)


def finalize_mesh(me, angle=32.0):
    """Гладке затінення + гострі ребра за кутом (Blender 4.1+)."""
    try:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(angle))
    except AttributeError:          # Blender < 4.1
        for p in me.polygons:
            p.use_smooth = True
        me.use_auto_smooth = True
        me.auto_smooth_angle = math.radians(angle)


def add_part(group, name, me, mat_keys):
    for k in mat_keys:
        me.materials.append(MAT[k])
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    PARTS.setdefault(group, []).append(ob)
    return ob


def bm_to_part(group, name, bm, mat_keys, angle=32.0, recalc=True):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    finalize_mesh(me, angle)
    return add_part(group, name, me, mat_keys)


def evaluated_mesh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    return bpy.data.meshes.new_from_object(ob.evaluated_get(dg))


def curve_object_to_mesh(name, cu):
    tmp = bpy.data.objects.new(name + "_tmp", cu)
    COLL.objects.link(tmp)
    me = evaluated_mesh(tmp)
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    me.name = name
    return me


def frame(origin, u, v):
    """Матриця з локальними осями u (X), v (Y), n = u×v (Z) у точці origin."""
    u = Vector(u).normalized()
    v = Vector(v)
    v = (v - u * v.dot(u)).normalized()
    n = u.cross(v)
    m = Matrix((
        (u.x, v.x, n.x, origin[0]),
        (u.y, v.y, n.y, origin[1]),
        (u.z, v.z, n.z, origin[2]),
        (0, 0, 0, 1)))
    return m


# ------------------------------------------------------------------ 2D-контури
def rrect(cx, cy, w, h, r, seg=4):
    """Прямокутник із заокругленими кутами (центр, ширина, висота, радіус)."""
    r = min(r, w / 2, h / 2)
    pts = []
    for (qx, qy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                         (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + qx + r * math.cos(a), cy + qy + r * math.sin(a)))
    return pts


def circle(cx, cy, r, seg=16):
    return [(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]


def chamfer_poly(pts, cuts):
    """Зрізає кути багатокутника: cuts — dict індекс→довжина фаски."""
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        c = cuts.get(i, 0)
        if not c:
            out.append(p)
            continue
        p = Vector(p)
        a = Vector(pts[i - 1]) - p
        b = Vector(pts[(i + 1) % n]) - p
        out.append(tuple(p + a.normalized() * c))
        out.append(tuple(p + b.normalized() * c))
    return out


def round_poly(pts, cuts, seg=4):
    """Заокруглює кути багатокутника (dict індекс→радіус)."""
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        r = cuts.get(i, 0)
        if not r:
            out.append(p)
            continue
        p = Vector(p)
        a = (Vector(pts[i - 1]) - p).normalized()
        b = (Vector(pts[(i + 1) % n]) - p).normalized()
        ang = a.angle(b)
        t = r / math.tan(ang / 2)
        pa, pb = p + a * t, p + b * t
        for k in range(seg + 1):
            s = k / seg
            q = (1 - s) ** 2 * pa + 2 * (1 - s) * s * p + s * s * pb
            out.append((q.x, q.y))
    return out


# ------------------------------------------------------------------ листовий метал
def plate_mesh(name, outline, holes=(), t=0.005, bev=0.0011, res=1):
    """Лист товщиною t з отворами (2D у площині XY, товщина по Z від 0 до t), з фасками."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    b = min(bev, t * 0.45)
    cu.extrude = max(t / 2 - b, 1e-5)
    cu.bevel_mode = 'ROUND'
    cu.bevel_depth = b
    cu.bevel_resolution = res
    cu.offset = -b
    for loop in [outline] + list(holes):
        sp = cu.splines.new('POLY')
        sp.points.add(len(loop) - 1)
        for i, (x, y) in enumerate(loop):
            sp.points[i].co = (x, y, 0.0, 1.0)
        sp.use_cyclic_u = True
    me = curve_object_to_mesh(name, cu)
    me.transform(Matrix.Translation((0, 0, t / 2)))
    return me


def plate(group, name, outline, holes=(), t=0.005, M=Matrix.Identity(4), mat='paint', bev=0.0011, angle=32.0):
    me = plate_mesh(name, outline, holes, t, bev)
    me.transform(M)
    finalize_mesh(me, angle)
    return add_part(group, name, me, [mat])


# ------------------------------------------------------------------ труби
def fillet_arcs(pts, radius, seg_per_rad=9):
    """Ламана → шлях із дугами кола заданого радіуса в кутах."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        d0, d1 = (p0 - p1), (p2 - p1)
        if d0.length < 1e-6 or d1.length < 1e-6:
            continue
        d0.normalize()
        d1.normalize()
        ang = d0.angle(d1)
        if ang > math.pi - 1e-3 or radius <= 0:
            out.append(p1)
            continue
        t = radius / math.tan(ang / 2)
        t = min(t, (p0 - p1).length * 0.5, (p2 - p1).length * 0.5)
        rr = t * math.tan(ang / 2)
        a, b = p1 + d0 * t, p1 + d1 * t
        c = p1 + (d0 + d1).normalized() * (rr / math.sin(ang / 2))
        va, vb = a - c, b - c
        th = va.angle(vb)
        n = max(2, int(th * seg_per_rad) + 1)
        for k in range(n + 1):
            s = k / n
            v = (math.sin((1 - s) * th) * va + math.sin(s * th) * vb) / math.sin(th)
            out.append(c + v)
    out.append(pts[-1])
    # прибрати дублікати
    clean = [out[0]]
    for p in out[1:]:
        if (p - clean[-1]).length > 1e-5:
            clean.append(p)
    return clean


def tube_mesh(name, pts, radius, bend=0.0, res=4, caps=True):
    path = fillet_arcs(pts, bend) if bend else [Vector(p) for p in pts]
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.twist_mode = 'MINIMUM'
    cu.bevel_mode = 'ROUND'
    cu.bevel_depth = radius
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    sp = cu.splines.new('POLY')
    sp.points.add(len(path) - 1)
    for i, p in enumerate(path):
        sp.points[i].co = (p.x, p.y, p.z, 1.0)
    return curve_object_to_mesh(name, cu)


def tube(group, name, pts, radius, bend=0.0, mat='tube', res=4, caps=True):
    me = tube_mesh(name, pts, radius, bend, res, caps)
    finalize_mesh(me, 40.0)
    return add_part(group, name, me, [mat])


# ------------------------------------------------------------------ bmesh-примітиви
def bm_box(bm, x0, x1, y0, y1, z0, z1, bev=0.0, segs=2):
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res["verts"]
    for v in vs:
        v.co = Vector((x0 + (v.co.x + 0.5) * (x1 - x0), y0 + (v.co.y + 0.5) * (y1 - y0), z0 + (v.co.z + 0.5) * (z1 - z0)))
    if bev > 0:
        edges = list({e for v in vs for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=vs + edges, offset=bev, segments=segs, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    return vs


def bm_lathe(bm, prof, segs, M=Matrix.Identity(4), closed=False, cap=False):
    """Тіло обертання профілю [(r, h)] навколо локальної осі Z (h уздовж осі)."""
    axis = {}                                   # точки на осі — одна вершина, а не кільце з нулів
    rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for i, (r, h) in enumerate(prof):
            if abs(r) < 1e-9:
                if i not in axis:
                    axis[i] = bm.verts.new(M @ Vector((0.0, 0.0, h)))
                ring.append(axis[i])
            else:
                ring.append(bm.verts.new(M @ Vector((r * ca, r * sa, h))))
        rings.append(ring)
    n = len(prof)
    m = n if closed else n - 1
    faces = []
    for k in range(segs):
        r0, r1 = rings[k], rings[(k + 1) % segs]
        for i in range(m):
            j = (i + 1) % n
            quad = []
            for v in (r0[i], r0[j], r1[j], r1[i]):
                if v not in quad:
                    quad.append(v)
            if len(quad) < 3:
                continue
            try:
                faces.append(bm.faces.new(quad))
            except ValueError:
                pass
    if cap and not closed:
        for idx in (0, n - 1):
            if prof[idx][0] > 1e-6:
                try:
                    faces.append(bm.faces.new([rings[k][idx] for k in range(segs)]))
                except ValueError:
                    pass
    return faces


def bm_cyl(bm, p0, p1, r, segs=16, r1=None):
    """Циліндр/конус між точками p0 і p1 (із кришками)."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = p1 - p0
    q = ax.normalized().to_track_quat('Z', 'Y')
    M = Matrix.Translation(p0) @ q.to_matrix().to_4x4()
    r1 = r if r1 is None else r1
    return bm_lathe(bm, [(0, 0), (r, 0), (r1, ax.length), (0, ax.length)], segs, M)


def bm_from_pydata(bm, verts, faces):
    vv = [bm.verts.new(v) for v in verts]
    out = []
    for f in faces:
        try:
            out.append(bm.faces.new([vv[i] for i in f]))
        except ValueError:
            pass
    return out


# ------------------------------------------------------------------ кріплення
def _lathe_template(prof, segs):
    verts, faces = [], []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        for (r, h) in prof:
            verts.append((r * math.cos(a), r * math.sin(a), h))
    n = len(prof)
    for k in range(segs):
        k2 = (k + 1) % segs
        for i in range(n - 1):
            a, b = k * n + i, k * n + i + 1
            c, d = k2 * n + i + 1, k2 * n + i
            if prof[i][0] < 1e-7 and prof[i + 1][0] < 1e-7:
                continue
            faces.append((a, b, c, d))
    return verts, faces


BOLT_DOME = _lathe_template([(0.0, 0.0), (0.0115, 0.0), (0.0115, 0.0022), (0.0090, 0.0024), (0.0088, 0.0034),
                             (0.0080, 0.0050), (0.0064, 0.0062), (0.0040, 0.0070), (0.0, 0.0073)], 14)

def _hex_nut_template(af=0.017, h=0.012, washer=0.0125):
    verts, faces = [], []
    # шайба
    wv, wf = _lathe_template([(0.0, 0.0), (washer, 0.0), (washer, 0.002), (af * 0.55, 0.002), (0.0, 0.002)], 16)
    verts += wv
    faces += wf
    o = len(verts)
    R = af / math.sqrt(3)
    ring0 = [(R * math.cos(math.radians(30 + 60 * k)), R * math.sin(math.radians(30 + 60 * k)), 0.002) for k in range(6)]
    ring1 = [(x, y, 0.002 + h) for (x, y, _z) in ring0]
    ring2 = [(x * 0.82, y * 0.82, 0.002 + h + 0.0015) for (x, y, _z) in ring0]
    verts += ring0 + ring1 + ring2
    for k in range(6):
        k2 = (k + 1) % 6
        faces.append((o + k, o + k2, o + 6 + k2, o + 6 + k))
        faces.append((o + 6 + k, o + 6 + k2, o + 12 + k2, o + 12 + k))
    faces.append(tuple(o + 12 + k for k in range(6)))
    return verts, faces


NUT_HEX = _hex_nut_template()
STUD = _lathe_template([(0.0, 0.0), (0.0045, 0.0), (0.0045, 0.022), (0.0035, 0.024), (0.0, 0.024)], 10)


def fasteners(group, name, items, template=BOLT_DOME, mat='zinc', scale=1.0):
    """items: [(точка, нормаль), ...] → один меш з усіма кріпленнями."""
    verts, faces = [], []
    tv, tf = template
    for pos, nrm in items:
        q = Vector(nrm).normalized().to_track_quat('Z', 'Y')
        M = Matrix.Translation(Vector(pos)) @ q.to_matrix().to_4x4() @ Matrix.Scale(scale, 4)
        o = len(verts)
        verts += [tuple(M @ Vector(v)) for v in tv]
        faces += [tuple(o + i for i in f) for f in tf]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    finalize_mesh(me, 50.0)
    return add_part(group, name, me, [mat])


def bm_append_mesh(bm, me, mat_index=0, M=None, remove=True):
    """Копіює геометрію меша в bmesh (з індексом матеріалу)."""
    tmp = bmesh.new()
    tmp.from_mesh(me)
    if M is not None:
        bmesh.ops.transform(tmp, matrix=M, verts=tmp.verts[:])
    vmap = {v: bm.verts.new(v.co) for v in tmp.verts}
    for f in tmp.faces:
        try:
            nf = bm.faces.new([vmap[v] for v in f.verts])
            nf.material_index = mat_index
            nf.smooth = f.smooth
        except ValueError:
            pass
    for e in tmp.edges:
        if not e.smooth:
            ne = bm.edges.get([vmap[e.verts[0]], vmap[e.verts[1]]])
            if ne:
                ne.smooth = False
    tmp.free()
    if remove:
        bpy.data.meshes.remove(me)


def set_mat(faces, idx):
    for f in faces:
        f.material_index = idx


# =================================================================== колесо
TIRE_HALF = [  # (w, r) від центру протектора до борту (зовнішня половина), м
    (0.000, 0.3025), (0.030, 0.3020), (0.060, 0.3010), (0.080, 0.2990), (0.095, 0.2940),
    (0.106, 0.2860), (0.114, 0.2740), (0.119, 0.2580), (0.121, 0.2380), (0.119, 0.2150),
    (0.114, 0.1920), (0.106, 0.1720), (0.098, 0.1600)]


def _half_profile_dense(n=200):
    pts = [Vector(p) for p in TIRE_HALF]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg)
    out = []
    for k in range(n + 1):
        s = total * k / n
        acc = 0.0
        for i, L in enumerate(seg):
            if acc + L >= s or i == len(seg) - 1:
                t = (s - acc) / L if L else 0
                out.append((s, pts[i].lerp(pts[i + 1], min(max(t, 0), 1))))
                break
            acc += L
    return out, total


def tire_surface(sigma, dense):
    """(w, r) і зовнішня нормаль (nw, nr) у точці профілю на відстані sigma від центру."""
    for i in range(len(dense) - 1):
        s0, p0 = dense[i]
        s1, p1 = dense[i + 1]
        if s1 >= sigma or i == len(dense) - 2:
            t = 0 if s1 == s0 else (sigma - s0) / (s1 - s0)
            p = p0.lerp(p1, min(max(t, 0), 1))
            d = (p1 - p0).normalized()
            return p, Vector((-d.y, d.x)).normalized()     # поворот на +90°: назовні
    return dense[-1][1], Vector((1, 0))


def build_wheel_mesh(name, mirror=False):
    p = P
    segs = p['wheel_segs']
    bm = bmesh.new()
    Mx = Vector((1, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4()   # локальна Z → X (вісь колеса)

    # --- каркас шини (обертання профілю навколо осі X)
    half = TIRE_HALF
    prof = [(-w, r) for (w, r) in reversed(half)] + [(w, r) for (w, r) in half[1:]]
    tire_faces = bm_lathe(bm, [(r, w) for (w, r) in prof], segs, Mx)
    set_mat(tire_faces, 0)

    # --- ґрунтозачепи R-1 («ялинка»): по 'lugs' на кожну половину, зі зсувом на півкроку
    dense, total = _half_profile_dense()
    sig_shoulder = None
    for s, q in dense:
        if q.y < 0.262:
            sig_shoulder = s
            break
    n_sec = 12
    pitch = 2 * math.pi / p['lugs']
    tan_main, tan_sh = math.tan(math.radians(36)), math.tan(math.radians(14))
    lug_faces = []
    for side in (1, -1):
        for k in range(p['lugs']):
            th0 = k * pitch + (0 if side > 0 else pitch / 2)
            secs = []
            th = th0
            sig_prev = 0.010
            for i in range(n_sec + 1):
                t = i / n_sec
                sig = 0.010 + t * (sig_shoulder - 0.010)
                (w, r), (nw, nr) = tire_surface(sig, dense)
                if i:
                    rate = tan_main if w < 0.096 else tan_sh
                    th += rate * (sig - sig_prev) / max(r, 0.2)
                sig_prev = sig
                ws = w * side
                S = Vector((ws, r * math.cos(th), r * math.sin(th)))
                N = Vector((nw * side, nr * math.cos(th), nr * math.sin(th))).normalized()
                secs.append((S, N, w))
            rings = []
            for i, (S, N, w) in enumerate(secs):
                if i == 0:
                    T = secs[1][0] - S
                elif i == n_sec:
                    T = S - secs[i - 1][0]
                else:
                    T = secs[i + 1][0] - secs[i - 1][0]
                B = T.cross(N).normalized()
                taper = 1.0 if w < 0.10 else max(0.55, 1.0 - (w - 0.10) * 22)
                h = 0.0235 * taper
                wb, wm, wt = 0.031, 0.026, 0.018
                sink = 0.004
                ring = [S - N * sink - B * wb / 2, S + N * h * 0.35 - B * wm / 2, S + N * h - B * wt / 2,
                        S + N * h + B * wt / 2, S + N * h * 0.35 + B * wm / 2, S - N * sink + B * wb / 2]
                rings.append([bm.verts.new(v) for v in ring])
            for i in range(n_sec):
                a, b = rings[i], rings[i + 1]
                for j in range(6):
                    j2 = (j + 1) % 6
                    lug_faces.append(bm.faces.new((a[j], a[j2], b[j2], b[j])))
            lug_faces.append(bm.faces.new(rings[0][::-1]))
            lug_faces.append(bm.faces.new(rings[-1]))
    set_mat(lug_faces, 0)

    # --- обід: тонкостінна оболонка 3 мм уздовж осьової лінії
    cl = [(0.1040, 0.1700), (0.1010, 0.1630), (0.0985, 0.1555), (0.0700, 0.1555), (0.0610, 0.1515),
          (0.0520, 0.1430), (0.0420, 0.1385), (-0.0420, 0.1385), (-0.0520, 0.1430), (-0.0610, 0.1515),
          (-0.0700, 0.1555), (-0.0985, 0.1555), (-0.1010, 0.1630), (-0.1040, 0.1700)]
    cl = [Vector(c) for c in cl]
    th_r = 0.0016
    outer, inner = [], []
    for i, c in enumerate(cl):
        a = cl[max(i - 1, 0)]
        b = cl[min(i + 1, len(cl) - 1)]
        d = (b - a).normalized()
        n = Vector((-d.y, d.x))
        if n.y < 0:
            n = -n
        outer.append(c + n * th_r)
        inner.append(c - n * th_r)
    # закруглені кромки (закатка)
    def lip(c, d_out):
        return [c + d_out * 0.0022]
    loop = outer + lip(cl[-1], (cl[-1] - cl[-2]).normalized()) + inner[::-1] + lip(cl[0], (cl[0] - cl[1]).normalized())
    rim_faces = bm_lathe(bm, [(q.y, q.x) for q in loop], segs, Mx, closed=True)
    set_mat(rim_faces, 1)

    # --- диск із 6 трапецієподібними вирізами
    holes = []
    for k in range(6):
        a0 = math.radians(30 + 60 * k)
        ri, ro = 0.079, 0.121
        hi, ho = math.radians(11.5), math.radians(15.5)
        quad = [(ri * math.cos(a0 - hi), ri * math.sin(a0 - hi)), (ro * math.cos(a0 - ho), ro * math.sin(a0 - ho)),
                (ro * math.cos(a0 + ho), ro * math.sin(a0 + ho)), (ri * math.cos(a0 + hi), ri * math.sin(a0 + hi))]
        holes.append(round_poly(quad, {0: 0.007, 1: 0.009, 2: 0.009, 3: 0.007}, 3))
    holes.append(circle(0, 0, 0.034, 24))
    disc = plate_mesh(name + "_disc", circle(0, 0, 0.1372, 96), holes, t=0.0045, bev=0.0008)
    wd = p['disc_w']
    Md = frame((wd - 0.00225, 0, 0), (0, 1, 0), (0, 0, 1))
    bm_append_mesh(bm, disc, 1, Md)
    # приварне кільце (ступиця диска) і фланець маточини
    ring_prof = [(0.0345, 0.0), (0.071, 0.0), (0.071, 0.004), (0.066, 0.0075), (0.0345, 0.0075)]
    rf = bm_lathe(bm, [(r, h) for (r, h) in ring_prof], 64, Matrix.Translation((wd + 0.002, 0, 0)) @ Mx, closed=True)
    set_mat(rf, 1)
    # маточина й піввісь (обертається разом із колесом), до бобишки корпусу
    hub_prof = [(0.0, -0.150), (0.046, -0.150), (0.046, -0.080), (0.072, -0.074), (0.072, -0.062),
                (0.034, -0.060), (0.034, wd - 0.002), (0.0, wd - 0.002)]
    hf = bm_lathe(bm, [(r, h) for (r, h) in hub_prof], 48, Mx)
    set_mat(hf, 1)
    # ковпачок маточини (кільця, як на фото)
    cap_prof = [(0.0, wd + 0.010), (0.031, wd + 0.010), (0.031, wd + 0.022), (0.028, wd + 0.026),
                (0.0225, wd + 0.026), (0.0205, wd + 0.020), (0.0150, wd + 0.020), (0.0140, wd + 0.031),
                (0.0105, wd + 0.034), (0.0, wd + 0.034)]
    cf = bm_lathe(bm, [(r, h) for (r, h) in cap_prof], 48, Mx)
    set_mat(cf, 2)
    # 5 гайок на кільці
    for k in range(5):
        a = math.radians(90 + 72 * k)
        pos = Vector((wd + 0.0095, 0.050 * math.cos(a), 0.050 * math.sin(a)))
        q = Vector((1, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4()
        M = Matrix.Translation(pos) @ q
        for tmpl in (NUT_HEX, STUD):
            vv, ff = tmpl
            fs = bm_from_pydata(bm, [tuple(M @ Vector(v)) for v in vv], ff)
            set_mat(fs, 2)
    # вентиль
    va = math.radians(-58)
    vb = Vector((0.050, 0.140 * math.cos(va), 0.140 * math.sin(va)))
    vt = vb + Vector((0.030, 0.012 * math.cos(va), 0.012 * math.sin(va)))
    set_mat(bm_cyl(bm, vb, vt, 0.0042, 10, 0.0036), 2)
    set_mat(bm_cyl(bm, vt, vt + (vt - vb).normalized() * 0.007, 0.0040, 10), 0)

    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    triangulate(bm)
    if mirror:
        bmesh.ops.scale(bm, vec=(-1, 1, 1), verts=bm.verts[:])
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    finalize_mesh(me, 38.0)
    for k in ('rubber', 'rim', 'zinc'):
        me.materials.append(MAT[k])
    return me


def build_wheels(root):
    p = P
    me_r = build_wheel_mesh("Zmiy_Wheel_R", mirror=False)
    me_l = build_wheel_mesh("Zmiy_Wheel_L", mirror=True)
    out = {}
    for nm, sx, y in (("Wheel_FL", -1, p['axle_f']), ("Wheel_FR", 1, p['axle_f']),
                      ("Wheel_RL", -1, p['axle_r']), ("Wheel_RR", 1, p['axle_r'])):
        ob = bpy.data.objects.new(nm, me_r if sx > 0 else me_l)
        COLL.objects.link(ob)
        ob.parent = root
        ob.location = (sx * p['wheel_x'], y, p['wheel_z'])
        out[nm] = ob
    return out


# =================================================================== допоміжні тіла корпусу
def convex_solid(group, name, pts, mat='paint', bev=0.006, segs=2, cutters=()):
    """Опукле тіло з набору точок (листова «коробка»), з фасками на ребрах."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    for g in res.get('geom_interior', []) + res.get('geom_unused', []):
        if isinstance(g, bmesh.types.BMVert) and g.is_valid and not g.link_faces:
            bm.verts.remove(g)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.6), verts=bm.verts[:], edges=bm.edges[:])
    if bev:
        bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=bev, segments=segs, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4 and not _is_planar(f)])
    ob = bm_to_part(group, name, bm, [mat], angle=30.0)
    for c in cutters:
        boolean_cut(ob, c)
    return ob


def _is_planar(f, tol=1e-5):
    n = f.normal
    c = f.verts[0].co
    return all(abs((v.co - c).dot(n)) < tol for v in f.verts)


def boolean_cut(ob, cutter_me, op='DIFFERENCE'):
    """Застосовує булеву операцію з тимчасовим мешем-різцем (EXACT)."""
    cut = bpy.data.objects.new(ob.name + "_cut", cutter_me)
    COLL.objects.link(cut)
    mod = ob.modifiers.new("cut", 'BOOLEAN')
    mod.operation = op
    mod.object = cut
    mod.solver = 'EXACT'
    me_new = evaluated_mesh(ob)
    bm = bmesh.new()
    bm.from_mesh(me_new)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me_new)
    bm.free()
    ob.modifiers.clear()
    old = ob.data
    mats = list(old.materials)
    ob.data = me_new
    me_new.materials.clear()
    for m in mats:
        me_new.materials.append(m)
    finalize_mesh(me_new, 30.0)
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cut, do_unlink=True)
    bpy.data.meshes.remove(cutter_me)


def drop_faces(ob, pred):
    """Видаляє невидимі грані (закриті іншими деталями) — економить місце в текстурі."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    dead = [f for f in bm.faces if pred(f)]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(ob.data)
    bm.free()


def cyl_mesh(p0, p1, r, segs=24):
    bm = bmesh.new()
    bm_cyl(bm, p0, p1, r, segs)
    me = bpy.data.meshes.new("cyl")
    bm.to_mesh(me)
    bm.free()
    return me


def strip_path(group, name, path, z0, z1, t=0.005, mat='paint', bev=0.0012, inward=True):
    """Вертикальна смуга (лист t) уздовж ламаної в плані XY з митровими кутами, Z z0..z1."""
    pts = [Vector((x, y)) for (x, y) in path]
    n = len(pts)
    off_a, off_b = [], []
    for i in range(n):
        if i == 0:
            d = (pts[1] - pts[0]).normalized()
            nrm = Vector((-d.y, d.x))
            m = nrm
            k = 1.0
        elif i == n - 1:
            d = (pts[-1] - pts[-2]).normalized()
            nrm = Vector((-d.y, d.x))
            m = nrm
            k = 1.0
        else:
            d0 = (pts[i] - pts[i - 1]).normalized()
            d1 = (pts[i + 1] - pts[i]).normalized()
            n0, n1 = Vector((-d0.y, d0.x)), Vector((-d1.y, d1.x))
            m = (n0 + n1).normalized()
            k = 1.0 / max(m.dot(n0), 0.3)
        a = pts[i]
        b = pts[i] + m * t * k * (1 if inward else -1)
        off_a.append(a)
        off_b.append(b)
    bm = bmesh.new()
    ring = []
    for i in range(n):
        ring.append([bm.verts.new((off_a[i].x, off_a[i].y, z0)), bm.verts.new((off_b[i].x, off_b[i].y, z0)),
                     bm.verts.new((off_b[i].x, off_b[i].y, z1)), bm.verts.new((off_a[i].x, off_a[i].y, z1))])
    for i in range(n - 1):
        a, b = ring[i], ring[i + 1]
        for j in range(4):
            j2 = (j + 1) % 4
            bm.faces.new((a[j], a[j2], b[j2], b[j]))
    bm.faces.new(ring[0][::-1])
    bm.faces.new(ring[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    sharp = [e for e in bm.edges if e.calc_face_angle(0) > math.radians(30)]
    if bev and sharp:
        bmesh.ops.bevel(bm, geom=list({v for e in sharp for v in e.verts}) + sharp, offset=bev, segments=1,
                        profile=0.5, affect='EDGES', clamp_overlap=True)
    return bm_to_part(group, name, bm, [mat], angle=30.0)


def box(group, name, x0, x1, y0, y1, z0, z1, mat='paint', bev=0.004, segs=2):
    bm = bmesh.new()
    bm_box(bm, x0, x1, y0, y1, z0, z1, bev, segs)
    return bm_to_part(group, name, bm, [mat], angle=30.0)


# =================================================================== нижній корпус
def build_hull():
    p = P
    hx, z0 = p['hull_x'], p['hull_z0']
    ztop = p['deck_z'] - p['deck_t']
    y0, y1 = p['hull_y0'], p['hull_y1']
    side = [(y0, z0 + 0.075), (y0 + 0.075, z0), (y1 - 0.02, z0), (y1, z0 + 0.02), (y1, ztop - 0.002), (y0, ztop - 0.002)]
    M = frame((-hx, 0, 0), (0, 1, 0), (0, 0, 1))
    hull = plate('Body', "Body_Hull", side, (), t=2 * hx, M=M, bev=0.010)
    # верх корпусу закритий палубою, перед — задньою стінкою носа: ці грані не видно, прибираємо
    drop_faces(hull, lambda f: (f.normal.z > 0.99 and f.calc_center_median().z > ztop - 0.02) or
               (f.normal.y > 0.99 and f.calc_center_median().y > y1 - 0.005))
    # бобишки моторів-коліс на бортах + болти по колу
    bm = bmesh.new()
    bolts = []
    for s in (-1, 1):
        for y in (p['axle_f'], p['axle_r']):
            x0 = s * hx
            bm_lathe(bm, [(0.0, 0.0), (0.088, 0.0), (0.088, 0.010), (0.084, 0.014), (0.062, 0.014), (0.062, 0.026),
                          (0.058, 0.030), (0.0, 0.030)], 40,
                     Matrix.Translation((x0, y, p['wheel_z'])) @ Vector((s, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
            for k in range(6):
                a = math.radians(30 + 60 * k)
                bolts.append((Vector((x0 + s * 0.014, y + 0.075 * math.cos(a), p['wheel_z'] + 0.075 * math.sin(a))),
                              Vector((s, 0, 0))))
    bm_to_part('Body', "Body_MotorBosses", bm, ['paint'], angle=35.0)
    fasteners('Body', "Body_MotorBolts", bolts, NUT_HEX, scale=0.75)
    # захисний лист днища з болтами
    sk = [(y0 + 0.11, -hx + 0.03), (y1 - 0.06, -hx + 0.03), (y1 - 0.06, hx - 0.03), (y0 + 0.11, hx - 0.03)]
    Msk = frame((0, 0, z0 - 0.006), (0, 1, 0), (-1, 0, 0))
    skid = plate('Body', "Body_SkidPlate", [(a, b) for (a, b) in sk], (), t=0.006, M=Msk, bev=0.0015)
    drop_faces(skid, lambda f: f.normal.z > 0.99)          # верх листа притиснутий до днища
    bolts = []
    for yy in [y0 + 0.14 + k * 0.2 for k in range(7)]:
        if yy > y1 - 0.08:
            break
        for s in (-1, 1):
            bolts.append((Vector((s * (hx - 0.06), yy, z0 - 0.006)), Vector((0, 0, -1))))
    fasteners('Body', "Body_SkidBolts", bolts)


# =================================================================== кузов-«ванна»
SLOT_TYPES = {'L': (0.062, 0.024), 'M': (0.040, 0.015), 'S': (0.026, 0.012)}


def wall_holes(y0, y1, zc):
    holes, y, k = [], y0, 0
    cycle = ['M', 'h', 'L', 'h']
    while y < y1:
        t = cycle[k % len(cycle)]
        if t == 'h':
            holes.append(circle(y, zc - 0.002, 0.0055, 14))
        else:
            w, h = SLOT_TYPES[t]
            holes.append(rrect(y, zc, w, h, h * 0.5 - 0.0005, 4))
        y += 0.074
        k += 1
    return holes


def lip_path():
    p = P
    yl = p['nose_top_y'] + 0.012
    x = p['side_x']
    return [(-x, p['tub_y1'] - 0.01), (-x, yl - 0.062), (-x + 0.062, yl), (x - 0.062, yl), (x, yl - 0.062),
            (x, p['tub_y1'] - 0.01)]


def build_tub():
    p = P
    zt = p['deck_z']
    sx, wt = p['side_x'], p['wall_t']
    y0, y1 = p['tub_y0'], p['tub_y1']

    # --- палуба (один лист від корми до губи носа)
    lp = lip_path()
    yl = lp[2][1]
    deck = [(-sx + wt, y0), (sx - wt, y0), (sx - wt, yl - 0.064), (sx - 0.064, yl - wt),
            (-sx + 0.064, yl - wt), (-sx + wt, yl - 0.064)]
    tie = []
    for yy in (-0.70, -0.40, -0.10):
        for xx in (-0.30, 0.30):
            tie.append(rrect(xx, yy, 0.050, 0.020, 0.0095, 4))
    plate('Body', "Body_Deck", deck, tie, t=p['deck_t'], M=Matrix.Translation((0, 0, zt - p['deck_t'])), bev=0.0009)

    # --- бортові стінки з прорізами
    z0, z1 = p['wall_z0'], p['wall_z1']
    outline = [(y0, z0), (y1, z0), (y1, zt - 0.003), (y1 - 0.082, z1), (y0 + 0.050, z1), (y0, z1 - 0.050)]
    holes = wall_holes(y0 + 0.085, y1 - 0.12, z1 - 0.034)
    bolts = []
    pair_y = [p['rail_y_rear']] + list(p['rail_posts']) + [-0.640, -0.265, y1 - 0.120]
    for s in (-1, 1):
        x0 = sx - wt if s > 0 else -sx
        M = frame((x0, 0, 0), (0, 1, 0), (0, 0, 1))
        plate('Body', "Body_Wall_" + ("L" if s < 0 else "R"), outline, holes, t=wt, M=M, bev=0.0012)
        for yy in pair_y:
            for dy in (-0.021, 0.021):
                bolts.append((Vector((s * sx, yy + dy, z0 + 0.036)), Vector((s, 0, 0))))
    fasteners('Body', "Body_WallBolts", bolts)

    # --- губа по периметру верху носа (вертикальна смуга)
    strip_path('Body', "Body_NoseLip", lp, p['nose_lip_z0'], zt + 0.003, t=wt)
    bolts = []
    yl = lp[2][1]
    for xx in (-0.52, -0.26, 0.0, 0.26, 0.52):
        bolts.append((Vector((xx, yl, (p['nose_lip_z0'] + zt) / 2)), Vector((0, 1, 0))))
    for s in (-1, 1):
        for yy in (y1 + 0.06, (y1 + yl) / 2 + 0.02):
            bolts.append((Vector((s * sx, yy, (p['nose_lip_z0'] + zt) / 2)), Vector((s, 0, 0))))
    fasteners('Body', "Body_LipBolts", bolts)
    # вушка для підйому на передніх кутах губи
    for s in (-1, 1):
        c = Vector((s * (sx - 0.031), yl - 0.031, zt - 0.018))
        d = Vector((s, 1, 0)).normalized()
        o = c + d * 0.004
        tab = round_poly([(0, -0.024), (0.040, -0.024), (0.040, 0.024), (0, 0.024)], {1: 0.022, 2: 0.022}, 5)
        M = frame(o, d, (0, 0, 1)) @ Matrix.Translation((0, 0, -0.004))
        plate('Body', "Body_LiftTab_" + ("L" if s < 0 else "R"), tab, [circle(0.020, 0, 0.0105, 16)], t=0.008, M=M)

    # --- кормові кути палуби (між відкидною плитою і бортами)
    for s in (-1, 1):
        w = sx - wt - p['gate_hw']
        pts = [(0, 0.655), (w, 0.655), (w, zt), (0, zt)]
        M = frame((-sx + wt if s < 0 else p['gate_hw'], y0, 0), (1, 0, 0), (0, 0, 1))
        plate('Body', "Body_RearCorner_" + ("L" if s < 0 else "R"), pts, (), t=wt, M=M)


def build_rear():
    p = P
    y0 = p['tub_y0']
    gw, g0, g1, gc = p['gate_hw'], p['gate_z0'], p['gate_z1'], p['gate_cut']
    # --- відкидна плита (борт) з фасками на верхніх кутах
    gate = [(-gw, g0), (gw, g0), (gw, g1 - gc), (gw - gc, g1), (-gw + gc, g1), (-gw, g1 - gc)]
    gate = round_poly(gate, {2: 0.01, 3: 0.01, 4: 0.01, 5: 0.01}, 3)
    M = frame((0, y0, 0), (1, 0, 0), (0, 0, 1))
    plate('Body', "Body_Tailgate", gate, [circle(gw - 0.040, g1 - gc - 0.035, 0.008, 14),
                                         circle(-gw + 0.040, g1 - gc - 0.035, 0.008, 14)], t=0.005, M=M)
    # ребро жорсткості (відгин) по низу
    box('Body', "Body_TailgateRib", -gw + 0.03, gw - 0.03, y0 - 0.026, y0 - 0.004, g0 + 0.004, g0 + 0.024, bev=0.003)
    # завіса знизу (кулачки + вісь)
    bm = bmesh.new()
    zc = g0 - 0.004
    for k in range(9):
        xa = -gw + 0.04 + k * (2 * gw - 0.08) / 9
        bm_cyl(bm, (xa + 0.002, y0 - 0.010, zc), (xa + (2 * gw - 0.08) / 9 - 0.002, y0 - 0.010, zc), 0.0105, 16)
    bm_to_part('Body', "Body_GateHinge", bm, ['paint'], angle=40.0)
    # засувки (шпінгалети) і ручка-кнопка
    for s in (-1, 1):
        x0 = s * 0.300
        bx0, bx1 = sorted((x0, x0 + s * 0.140))
        box('Body', "Body_Latch_Base_" + ("L" if s < 0 else "R"), bx0, bx1, y0 - 0.010, y0 - 0.005,
            0.680, 0.715, mat='zinc', bev=0.0015)
        tube('Body', "Body_Latch_Bolt_" + ("L" if s < 0 else "R"),
             [(x0 + s * 0.010, y0 - 0.017, 0.6975), (x0 + s * 0.205, y0 - 0.017, 0.6975)], 0.0068, mat='zinc', res=3)
        tube('Body', "Body_Latch_Handle_" + ("L" if s < 0 else "R"),
             [(x0 + s * 0.055, y0 - 0.017, 0.6975), (x0 + s * 0.055, y0 - 0.040, 0.6975),
              (x0 + s * 0.055, y0 - 0.040, 0.735)], 0.0045, bend=0.008, mat='zinc', res=3)
        # скоби-приймачі на кутах
        box('Body', "Body_Latch_Keeper_" + ("L" if s < 0 else "R"), *sorted((s * 0.565, s * 0.590)),
            y0 - 0.028, y0 - 0.002, 0.684, 0.711, mat='zinc', bev=0.002)
    bm = bmesh.new()
    bm_cyl(bm, (-0.205, y0 - 0.005, 0.735), (-0.205, y0 - 0.030, 0.735), 0.006, 12)
    bm_lathe(bm, [(0.0, 0.0), (0.011, 0.0), (0.0135, 0.010), (0.0135, 0.026), (0.010, 0.034), (0.0, 0.036)], 20,
             Matrix.Translation((-0.205, y0 - 0.028, 0.735)) @ Vector((0, -1, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    bm_to_part('Body', "Body_Knob", bm, ['orange'], angle=40.0)

    # --- поличка під бортом і нижня кормова панель
    hy0 = p['hull_y0']
    box('Body', "Body_RearShelf", -gw + 0.02, gw - 0.02, hy0 - 0.004, y0 + 0.002, p['rear_z1'], p['rear_z1'] + 0.006,
        bev=0.0015)
    rw, r0, r1 = p['rear_hw'], p['rear_z0'], p['rear_z1']
    panel = chamfer_poly([(-rw, r0), (rw, r0), (rw, r1), (-rw, r1)], {0: 0.035, 1: 0.035})
    M = frame((0, hy0, 0), (1, 0, 0), (0, 0, 1))
    plate('Body', "Body_RearPanel", panel, (), t=0.005, M=M)
    bolts = [(Vector((xx, hy0 - 0.005, zz)), Vector((0, -1, 0)))
             for xx in (-rw + 0.03, rw - 0.03) for zz in (r0 + 0.045, r1 - 0.03)]
    bolts += [(Vector((xx, hy0 - 0.005, r0 + 0.030)), Vector((0, -1, 0))) for xx in (-0.12, 0.12)]
    # бічні замки-клямки нижньої панелі
    for s in (-1, 1):
        xx = s * 0.330
        box('Body', "Body_DrawLatch_Base_" + ("L" if s < 0 else "R"), xx - 0.018, xx + 0.018, hy0 - 0.011, hy0 - 0.005,
            0.400, 0.520, mat='zinc', bev=0.0015)
        tube('Body', "Body_DrawLatch_Lever_" + ("L" if s < 0 else "R"),
             [(xx, hy0 - 0.016, 0.515), (xx, hy0 - 0.026, 0.470), (xx, hy0 - 0.018, 0.405)], 0.0055, bend=0.02,
             mat='zinc', res=3)
        tube('Body', "Body_DrawLatch_Loop_" + ("L" if s < 0 else "R"),
             [(xx - 0.010, hy0 - 0.012, 0.400), (xx - 0.010, hy0 - 0.014, 0.355), (xx + 0.010, hy0 - 0.014, 0.355),
              (xx + 0.010, hy0 - 0.012, 0.400)], 0.0028, bend=0.006, mat='zinc', res=2)
        bolts += [(Vector((xx, hy0 - 0.011, zz)), Vector((0, -1, 0))) for zz in (0.418, 0.502)]
    # --- фаркоп: монтажна плита, вигнутий хвостовик, куля 50 мм; дві проушини під шакли
    hz = p['hitch_z']
    box('Body', "Body_HitchPlate", -0.060, 0.060, hy0 - 0.017, hy0 - 0.005, hz - 0.050, hz + 0.040, bev=0.003)
    bolts += [(Vector((xx, hy0 - 0.017, zz)), Vector((0, -1, 0))) for xx in (-0.040, 0.040) for zz in (hz - 0.032, hz + 0.022)]
    tube('Body', "Body_HitchShank", [(0, hy0 - 0.015, hz - 0.010), (0, hy0 - 0.075, hz - 0.010),
                                     (0, hy0 - 0.112, hz + 0.030), (0, hy0 - 0.112, hz + 0.052)],
         0.0135, bend=0.028, mat='steel', res=4)
    bm = bmesh.new()
    prof = [(0.0, 0.0), (0.016, 0.0), (0.016, 0.006), (0.0125, 0.010), (0.0125, 0.022)]
    prof += [(0.025 * math.sin(math.radians(a)), 0.047 + 0.025 * math.cos(math.radians(a))) for a in range(150, -1, -15)]
    bm_lathe(bm, prof, 32, Matrix.Translation((0, hy0 - 0.112, hz + 0.050)))
    bm_to_part('Body', "Body_HitchBall", bm, ['steel'], angle=40.0)
    for s in (-1, 1):
        tab = round_poly([(0, -0.035), (0.062, -0.035), (0.062, 0.035), (0, 0.035)], {1: 0.030, 2: 0.030}, 6)
        M = frame((s * 0.135 - 0.006, hy0 - 0.004, hz), (0, -1, 0), (0, 0, 1))
        plate('Body', "Body_ShackleTab_" + ("L" if s < 0 else "R"), tab, [circle(0.036, 0.0, 0.0115, 18)], t=0.012, M=M)
    fasteners('Body', "Body_RearBolts", bolts)


# =================================================================== ніс
def nose_geometry():
    p = P
    zt = p['deck_z'] - p['deck_t']
    yt, zl = p['nose_top_y'], p['nose_lip_z0']
    top = Vector((yt, zl))
    chin = Vector((p['chin_y'], p['chin_z']))
    d = (chin - top)
    L = d.length
    dn = d.normalized()
    Wt, Wc, cut = p['nose_top_hw'], p['chin_hw'], p['chin_cut']

    def on_plate(s, x):
        q = top + dn * s
        return Vector((x, q.x, q.y))

    def hw_at(s):
        return Wt + (Wc - Wt) * s / L
    ext = (zt - zl) / max(-dn.y, 1e-6)
    pts = []
    for sgn in (-1, 1):
        pts += [on_plate(-ext, sgn * hw_at(-ext)), Vector((sgn * Wt, p['nose_back_y'], zt)),
                on_plate(L - cut, sgn * hw_at(L - cut)), on_plate(L, sgn * (Wc - cut)),
                Vector((sgn * p['nose_bot_hw'], p['nose_bot_y'], p['nose_bot_z'])),
                Vector((sgn * p['nose_bot_hw'], p['nose_back_y'], p['nose_bot_z']))]
    nrm = Vector((0, -dn.y, dn.x))         # нормаль лобового листа (назовні-вперед-вгору)
    if nrm.y < 0:
        nrm = -nrm
    return dict(pts=pts, on_plate=on_plate, hw_at=hw_at, L=L, n=nrm, dn=Vector((0.0, dn.x, dn.y)))


def build_nose():
    p = P
    g = nose_geometry()
    on, L, n = g['on_plate'], g['L'], g['n']
    # буксирувальні отвори в нижніх кутах лобового листа (глухі, 30 мм)
    cutters = []
    for s in (-1, 1):
        c = on(L - 0.105, s * (p['chin_hw'] - 0.115))       # подалі від скошеного кута
        cutters.append(cyl_mesh(c + n * 0.02, c - n * 0.016, 0.0165, 24))
    nose = convex_solid('Body', "Body_Nose", g['pts'], bev=0.007, segs=2, cutters=cutters)
    zt = p['deck_z'] - p['deck_t']
    drop_faces(nose, lambda f: f.normal.z > 0.99 and f.calc_center_median().z > zt - 0.003)
    # П-ручка біля «підборіддя»
    a, b = on(L - 0.040, -0.115), on(L - 0.040, 0.115)
    up = g['dn'] * -1
    tube('Body', "Body_NoseHandle", [a - n * 0.005, a + n * 0.050 + up * 0.012, b + n * 0.050 + up * 0.012, b - n * 0.005],
         0.0095, bend=0.022, mat='tube', res=4)
    # вертикальний стрижень (фіксатор/тримач антени) праворуч і гак ліворуч
    rt, rb = on(0.020, 0.400), on(0.235, 0.385)
    tube('Body', "Body_NoseRod", [rt + n * 0.022, rb + n * 0.022], 0.0062, mat='tube', res=3)
    tube('Body', "Body_NoseRodTip", [rt + n * 0.022 - g['dn'] * 0.010, rt + n * 0.022 - g['dn'] * 0.026], 0.0090,
         mat='tube', res=3)
    for s_ in (0.045, 0.200):
        q = on(s_, 0.400 - 0.015 * s_ / 0.235)
        bm = bmesh.new()
        bm_box(bm, -0.012, 0.012, -0.010, 0.010, 0.0, 0.026, 0.002, 1)
        bmesh.ops.transform(bm, matrix=frame(q, (1, 0, 0), -g['dn']), verts=bm.verts[:])
        bm_to_part('Body', "Body_NoseRodTab", bm, ['paint'])
    hk = on(0.085, -0.330)
    bm = bmesh.new()
    bm_box(bm, -0.025, 0.025, -0.022, 0.022, 0.0, 0.006, 0.0015, 1)
    bmesh.ops.transform(bm, matrix=frame(hk, (1, 0, 0), -g['dn']), verts=bm.verts[:])
    bm_to_part('Body', "Body_NoseHookPlate", bm, ['paint'])
    tube('Body', "Body_NoseHook", [hk + n * 0.006 + g['dn'] * 0.012, hk + n * 0.034 + g['dn'] * 0.012,
                                   hk + n * 0.034 - g['dn'] * 0.020, hk + n * 0.020 - g['dn'] * 0.030],
         0.0055, bend=0.010, mat='tube', res=3)
    # болти по верху лобового листа і на бортах носа
    bolts = [(on(0.032, xx) + n * 0.0, n) for xx in (-0.48, -0.16, 0.16, 0.48)]
    yb = p['nose_back_y']
    for s in (-1, 1):
        for (yy, zz) in ((yb + 0.035, 0.62), (yb + 0.035, 0.40), (yb + 0.090, 0.30)):
            x = _nose_side_x(g, yy, zz) * s
            bolts.append((Vector((x, yy, zz)), Vector((s, 0, 0))))
    fasteners('Body', "Body_NoseBolts", bolts)
    # кронштейн із гаком на бортах носа
    for s in (-1, 1):
        yy, zz = p['nose_back_y'] + 0.075, 0.50
        x = _nose_side_x(g, yy, zz) * s
        box('Body', "Body_NoseSideBracket_" + ("L" if s < 0 else "R"), *sorted((x, x + s * 0.010)),
            yy - 0.030, yy + 0.030, zz - 0.022, zz + 0.022, bev=0.002)
        tube('Body', "Body_NoseSideHook_" + ("L" if s < 0 else "R"),
             [(x + s * 0.010, yy - 0.012, zz), (x + s * 0.034, yy - 0.012, zz), (x + s * 0.034, yy + 0.020, zz - 0.010)],
             0.0050, bend=0.008, mat='tube', res=3)


def _nose_side_x(g, y, z):
    """Півширина борту носа на висоті z (лінійно між верхом і низом)."""
    p = P
    zt = p['deck_z'] - p['deck_t']
    t = (zt - z) / (zt - p['nose_bot_z'])
    return p['nose_top_hw'] + (p['nose_bot_hw'] - p['nose_top_hw']) * t + 0.002


# =================================================================== каркас і поручні
def build_cage():
    p = P
    hx, hy, ht, r = p['hoop_x'], p['hoop_y'], p['hoop_top'], p['hoop_r']
    zd = p['deck_z']
    zf = zd + 0.008
    tube('Cage', "Cage_Hoop", [(-hx, hy, zf), (-hx, hy, ht), (hx, hy, ht), (hx, hy, zf)], r, bend=p['hoop_bend'], res=6)
    # діагональні тяги в площині дуги (від верхньої труби до стійок)
    for s in (-1, 1):
        a = Vector((s * p['brace_top_x'], hy, ht - r * 0.55))
        b = Vector((s * (hx - r * 0.55), hy, p['brace_low_z']))
        tube('Cage', "Cage_Brace_" + ("L" if s < 0 else "R"), [a, b], p['brace_r'], res=3)
        for c, d in ((a, Vector((0, 0, 1))), (b, Vector((s, 0, 0)))):
            bm = bmesh.new()
            bm_lathe(bm, [(0.0, -0.006), (p['brace_r'] + 0.006, -0.006), (p['brace_r'] + 0.004, 0.004),
                          (p['brace_r'] + 0.0005, 0.008)], 16,
                     Matrix.Translation(c) @ (b - a if c is a else a - b).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4())
            bm_to_part('Cage', "Cage_BraceWeld", bm, ['tube'], angle=50.0)
    # опорні пластини під стійками дуги: косинки, зварний шов, 4 болти
    bolts = []
    for s in (-1, 1):
        x = s * hx
        box('Cage', "Cage_FootPlate", x - 0.052, x + 0.052, hy - 0.066, hy + 0.066, zd, zf, mat='tube', bev=0.0025)
        for dy in (-1, 1):
            tri = [(0, 0), (0.062, 0), (0, 0.075)]
            M = frame((x - 0.003, hy + dy * (r - 0.004), zf), (0, dy, 0), (0, 0, 1))
            plate('Cage', "Cage_Gusset", round_poly(tri, {1: 0.006, 2: 0.004}, 2), (), t=0.006, M=M, mat='tube')
        bm = bmesh.new()
        bm_lathe(bm, [(r - 0.001, 0.0), (r + 0.0065, 0.0), (r + 0.004, 0.004), (r + 0.0005, 0.0075)], 24,
                 Matrix.Translation((x, hy, zf)))
        bm_to_part('Cage', "Cage_FootWeld", bm, ['tube'], angle=50.0)
        for bx in (-0.036, 0.036):
            for by in (-0.048, 0.048):
                bolts.append((Vector((x + bx, hy + by, zf)), Vector((0, 0, 1))))
    # поручні вздовж бортів: задня нога → горизонталь → сходинка вгору → до стійки дуги
    rz, rz2 = p['rail_z'], p['rail_z2']
    for s in (-1, 1):
        x = s * p['rail_x']
        side = "L" if s < 0 else "R"
        pts = [(x, p['rail_y_rear'], zd + 0.002), (x, p['rail_y_rear'], rz), (x, p['rail_step_y0'], rz),
               (x, p['rail_step_y1'], rz2), (s * (hx + 0.010), hy - 0.014, rz2)]
        tube('Cage', "Cage_Rail_" + side, pts, p['rail_r'], bend=0.075, res=5)
        for yy in p['rail_posts']:
            tube('Cage', "Cage_RailPost_" + side, [(x, yy, zd + 0.002), (x, yy, rz - 0.004)], 0.0165, res=4)
        # зварні шви поручня на стійці дуги
        bm = bmesh.new()
        c = Vector((s * (hx + 0.010), hy - 0.014, rz2))
        bm_lathe(bm, [(p['rail_r'] - 0.001, -0.004), (p['rail_r'] + 0.005, -0.004), (p['rail_r'] + 0.003, 0.004),
                      (p['rail_r'], 0.007)], 18,
                 Matrix.Translation(c) @ Vector((-s * 0.05, -1, 0)).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4())
        bm_to_part('Cage', "Cage_RailWeld", bm, ['tube'], angle=50.0)
    fasteners('Cage', "Cage_FootBolts", bolts, NUT_HEX, scale=0.85)
    # кріплення камери: хомути на верхній трубі + монтажна пластина + вилка
    bm = bmesh.new()
    for xx in (-0.075, 0.075):
        prof = [(r + 0.0005, -0.014), (r + 0.006, -0.014), (r + 0.006, 0.014), (r + 0.0005, 0.014)]
        bm_lathe(bm, prof, 24, Matrix.Translation((xx, hy, ht)) @ Vector((1, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4(),
                 closed=True)
    bm_box(bm, -0.105, 0.105, hy - 0.050, hy + 0.060, ht - r - 0.010, ht - r - 0.002, 0.0015, 1)
    for xx in (-0.124, 0.118):
        bm_box(bm, xx, xx + 0.006, hy - 0.030, hy + 0.045, ht - 0.115, ht - r - 0.008, 0.0012, 1)
    bm_to_part('Cage', "Cage_CamMount", bm, ['tube'], angle=40.0)


# =================================================================== камера
def build_camera():
    p = P
    hy, ht, r = p['hoop_y'], p['hoop_top'], p['hoop_r']
    x0, x1 = -0.117, 0.117
    y0, y1 = hy - 0.070, hy + 0.250
    z1 = ht - r - 0.012
    z0 = z1 - 0.122
    zc = (z0 + z1) / 2
    box('Camera', "Camera_Housing", x0, x1, y0, y1, z0, z1, mat='cam', bev=0.008, segs=3)
    # передня рамка, об'єктив із блендою, друге віконце (тепловізор/датчик)
    box('Camera', "Camera_Bezel", x0 + 0.010, x1 - 0.010, y1 - 0.002, y1 + 0.006, z0 + 0.012, z1 - 0.012, mat='cam',
        bev=0.003)
    bm = bmesh.new()
    lx = -0.050
    q = Vector((0, 1, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bm_lathe(bm, [(0.0, 0.0), (0.036, 0.0), (0.036, 0.004), (0.031, 0.006), (0.031, 0.022), (0.0345, 0.024),
                  (0.0345, 0.036), (0.0310, 0.036), (0.0300, 0.026), (0.0255, 0.024), (0.0255, 0.020)], 40,
             Matrix.Translation((lx, y1 + 0.006, zc)) @ q, closed=False)
    bm_to_part('Camera', "Camera_Lens", bm, ['cam'], angle=40.0)
    bm = bmesh.new()
    bm_lathe(bm, [(0.0, 0.0), (0.0256, 0.0), (0.0230, 0.0035), (0.0, 0.0050)], 40,
             Matrix.Translation((lx, y1 + 0.006 + 0.0185, zc)) @ q)
    bm_to_part('Camera', "Camera_Glass", bm, ['glass'], angle=60.0)
    box('Camera', "Camera_Window", 0.032, 0.088, y1 + 0.004, y1 + 0.009, zc - 0.016, zc + 0.016, mat='glass', bev=0.002)
    # кабельний ввід / антена знизу
    bm = bmesh.new()
    bm_lathe(bm, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.014), (0.0105, 0.016), (0.0105, 0.088), (0.0085, 0.098),
                  (0.0, 0.100)], 20,
             Matrix.Translation((0.035, hy + 0.035, z0 + 0.002)) @ Vector((0, 0, -1)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    bm_to_part('Camera', "Camera_Antenna", bm, ['cam'], angle=40.0)
    bolts = []
    for s in (-1, 1):
        for yy in (y0 + 0.03, y1 - 0.03):
            for zz in (z0 + 0.025, z1 - 0.025):
                bolts.append((Vector((s * x1, yy, zz)), Vector((s, 0, 0))))
        bolts.append((Vector((s * x1, hy + 0.005, zc)), Vector((s, 0, 0))))
    fasteners('Camera', "Camera_Bolts", bolts, scale=0.6)


# =================================================================== декалі (товарний знак — окремо)
def decal(name, center, u, v, w, h, img_key):
    """Площина-наліпка з UV 0..1; матеріал Zmiy_Decal_<img_key> (текстура додається в zmiy_texture.py)."""
    c, u, v = Vector(center), Vector(u).normalized(), Vector(v).normalized()
    n = u.cross(v)
    c = c + n * 0.0012
    vs = [c - u * w / 2 - v * h / 2, c + u * w / 2 - v * h / 2, c + u * w / 2 + v * h / 2, c - u * w / 2 + v * h / 2]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(x) for x in vs], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, co in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = co
    m = bpy.data.materials.get("Zmiy_Decal_" + img_key) or make_material("Zmiy_Decal_" + img_key, "#111111", 0.8, 0.0)
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    return ob


def build_decals(body):
    p = P
    g = nose_geometry()
    out = []
    c = g['on_plate'](0.43 * g['L'], 0.0)
    out.append(decal("Decal_Logo_Nose", c, (-1, 0, 0), -g['dn'], 0.170, 0.150, "Logo"))
    y = p['tub_y0'] - 0.005
    out.append(decal("Decal_Logo_Rear", (-0.215, y, 0.790), (1, 0, 0), (0, 0, 1), 0.085, 0.075, "Logo"))
    out.append(decal("Decal_Text_Rear", (0.055, y, 0.782), (1, 0, 0), (0, 0, 1), 0.400, 0.070, "Text"))
    for ob in out:
        ob.parent = body
    return out


# =================================================================== опційні модулі
def build_modules(root):
    """Starlink Mini на дузі, вантаж на палубі, вила (концепт без референсів). Сховані за замовчуванням."""
    p = P
    mods = []
    # --- Starlink Mini (298×259×38.5 мм) на кронштейні над верхньою трубою
    hy, ht, r = p['hoop_y'], p['hoop_top'], p['hoop_r']
    PARTS['Module_Starlink'] = []
    box('Module_Starlink', "SL_Dish", -0.1295, 0.1295, -0.149, 0.149, 0.0, 0.0385, mat='paint', bev=0.006, segs=3)
    sl = PARTS['Module_Starlink'][-1]
    sl.data.materials.clear()
    sl.data.materials.append(make_material("Zmiy_Starlink_White", "#D8D8D2", 0.55, 0.0))
    box('Module_Starlink', "SL_Kick", -0.020, 0.020, -0.050, 0.010, -0.050, 0.002, mat='tube', bev=0.003)
    tube('Module_Starlink', "SL_Mast", [(0, -0.02, -0.05), (0, -0.02, -0.11)], 0.012, mat='tube')
    for ob in PARTS['Module_Starlink']:
        ob.data.transform(Matrix.Translation((0, hy - 0.02, ht + r + 0.115)) @ Matrix.Rotation(math.radians(-20), 4, 'X'))
    bm = bmesh.new()
    bm_lathe(bm, [(r + 0.0005, -0.016), (r + 0.006, -0.016), (r + 0.006, 0.016), (r + 0.0005, 0.016)], 24,
             Matrix.Translation((0, hy, ht)) @ Vector((1, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4(), closed=True)
    bm_to_part('Module_Starlink', "SL_Clamp", bm, ['tube'])
    # --- вантаж: два ящики й каністра, стягнуті ременем
    PARTS['Module_Cargo'] = []
    zd = p['deck_z']
    box('Module_Cargo', "Cargo_Box1", -0.62, -0.06, -0.80, -0.42, zd, zd + 0.30, bev=0.012, segs=2)
    box('Module_Cargo', "Cargo_Box2", 0.04, 0.60, -0.78, -0.40, zd, zd + 0.26, bev=0.012, segs=2)
    box('Module_Cargo', "Cargo_Box3", -0.40, 0.20, -0.32, 0.02, zd, zd + 0.22, bev=0.012, segs=2)
    tube('Module_Cargo', "Cargo_Strap", [(-0.70, -0.62, zd), (-0.62, -0.62, zd + 0.305), (0.60, -0.62, zd + 0.265),
                                         (0.70, -0.62, zd)], 0.004, bend=0.03, mat='tube', res=2)
    # --- вила (концепт: каретка на лобовому листі + 2 зубці + притискна лапа)
    PARTS['Module_Forks'] = []
    g = nose_geometry()
    on, n = g['on_plate'], g['n']
    for s in (-1, 1):
        a = on(0.08, s * 0.33)
        b = on(g['L'] - 0.03, s * 0.33)
        tube('Module_Forks', "Forks_Upright", [a + n * 0.03, b + n * 0.03], 0.022, mat='tube')
        root_pt = b + n * 0.03
        tine = [root_pt, root_pt + Vector((0, 0.05, -0.17)), root_pt + Vector((0, 0.95, -0.17)),
                root_pt + Vector((0, 1.02, -0.13))]
        tube('Module_Forks', "Forks_Tine", tine, 0.020, bend=0.05, mat='tube')
        arm = [a + n * 0.05, a + n * 0.05 + Vector((0, 0.35, 0.18)), a + n * 0.05 + Vector((0, 0.80, 0.02)),
               a + n * 0.05 + Vector((0, 0.86, -0.12))]
        tube('Module_Forks', "Forks_ClampArm", arm, 0.017, bend=0.12, mat='tube')
    tube('Module_Forks', "Forks_CrossBar", [on(0.10, -0.36) + n * 0.03, on(0.10, 0.36) + n * 0.03], 0.024, mat='tube')
    tube('Module_Forks', "Forks_CrossBar", [on(g['L'] - 0.05, -0.36) + n * 0.03, on(g['L'] - 0.05, 0.36) + n * 0.03],
         0.024, mat='tube')
    for key in ('Module_Starlink', 'Module_Cargo', 'Module_Forks'):
        ob = join_group(key, PARTS.pop(key))
        ob.parent = root
        ob.hide_render = True
        ob.hide_set(True)
        mods.append(ob)
    return mods


def build_collision(root):
    """Прості опуклі колізії (UCX_ для Unreal), окрема колекція, у GLB не йдуть."""
    p = P
    coll = bpy.data.collections.get("Zmiy_Collision") or bpy.data.collections.new("Zmiy_Collision")
    if coll.name not in COLL.children:
        COLL.children.link(coll)
    out = []

    def add(name, bm):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.parent = root
        ob.display_type = 'WIRE'
        ob.hide_render = True
        out.append(ob)
    bm = bmesh.new()
    bm_box(bm, -p['side_x'], p['side_x'], p['tub_y0'], p['nose_top_y'], p['wall_z0'] - 0.02, p['wall_z1'])
    add("UCX_Zmiy_Logistic_00", bm)
    bm = bmesh.new()
    bm_box(bm, -p['hull_x'], p['hull_x'], p['hull_y0'], p['nose_back_y'], p['hull_z0'], p['wall_z0'] - 0.02)
    add("UCX_Zmiy_Logistic_01", bm)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in nose_geometry()['pts']]
    bmesh.ops.convex_hull(bm, input=vs)
    add("UCX_Zmiy_Logistic_02", bm)
    k = 3
    for sx in (-1, 1):
        for y in (p['axle_f'], p['axle_r']):
            bm = bmesh.new()
            x = sx * p['wheel_x']
            bm_cyl(bm, (x - p['tire_w'] / 2, y, p['wheel_z']), (x + p['tire_w'] / 2, y, p['wheel_z']), p['tire_r'], 12)
            add("UCX_Zmiy_Logistic_%02d" % k, bm)
            k += 1
    coll.hide_render = True
    return out


# =================================================================== збірка
def triangulate(bm):
    """Фінальні меші — трикутники: база дотичних у рушії збігається з тією, що була при запіканні нормалей."""
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')


def join_group(name, objs, pivot=(0, 0, 0)):
    """Об'єднує частини в один меш-об'єкт (матеріали зводяться в спільний список)."""
    bm = bmesh.new()
    mats = []
    for ob in objs:
        me = ob.data
        remap = {}
        for i, m in enumerate(me.materials):
            if m not in mats:
                mats.append(m)
            remap[i] = mats.index(m)
        tmp = bmesh.new()
        tmp.from_mesh(me)
        bmesh.ops.transform(tmp, matrix=Matrix.Translation(-Vector(pivot)) @ ob.matrix_world, verts=tmp.verts[:])
        vmap = {v: bm.verts.new(v.co) for v in tmp.verts}
        for f in tmp.faces:
            try:
                nf = bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = remap.get(f.material_index, 0)
            nf.smooth = f.smooth
        for e in tmp.edges:
            if not e.smooth:
                ne = bm.edges.get([vmap[e.verts[0]], vmap[e.verts[1]]])
                if ne:
                    ne.smooth = False
        tmp.free()
    triangulate(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for ob in objs:
        old = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if old.users == 0:
            bpy.data.meshes.remove(old)
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    ob.location = pivot
    return ob


RESERVED = ("Zmiy_Logistic", "Body", "Cage", "Camera", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR",
            "Module_Starlink", "Module_Cargo", "Module_Forks")


def claim_names():
    """Звільняє імена ієрархії: чужі об'єкти з такими іменами (напр. стандартна камера сцени
    «Camera») перейменовуються на «<ім'я>.scene»."""
    for nm in RESERVED:
        ob = bpy.data.objects.get(nm)
        if ob and not any(c.name == COLL_NAME for c in ob.users_collection):
            ob.name = nm + ".scene"


def build_all():
    global COLL
    COLL = reset_collection(COLL_NAME)
    claim_names()
    PARTS.clear()
    MAT.clear()
    for k, v in MAT_DEF.items():
        MAT[k] = make_material(*v)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0

    root = bpy.data.objects.new("Zmiy_Logistic", None)
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = 0.5
    COLL.objects.link(root)

    build_hull()
    build_tub()
    build_rear()
    build_nose()
    build_cage()
    build_camera()

    body = join_group("Body", PARTS.pop('Body'))
    cage = join_group("Cage", PARTS.pop('Cage'))
    cam = join_group("Camera", PARTS.pop('Camera'), pivot=(0.0, P['hoop_y'], P['hoop_top'] - P['hoop_r']))
    for ob in (body, cage, cam):
        ob.parent = root
    build_wheels(root)
    build_decals(body)
    build_modules(root)
    build_collision(root)
    return root


if __name__ == "__main__":
    build_all()
    print("Zmiy_Logistic: готово")
