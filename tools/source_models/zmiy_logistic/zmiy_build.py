# -*- coding: utf-8 -*-
"""
НРК «Змій Логістичний» (Rovertech, 2026) — hero-asset для гри, Blender 4.2+ (перевірено на 4.5 LTS і 5.2).

Будує повну геометрію (без текстур) у колекції "Zmiy_Logistic":
    Zmiy_Logistic (empty, на землі під центром)
    ├─ Body      — корпус, кузов-«ванна» з бортовими стінками, ніс, корма, фаркоп, кріплення
    ├─ Wheel_FL / Wheel_FR / Wheel_RL / Wheel_RR — півот у центрі колеса, вісь обертання = локальна X
    ├─ Decal_*   — логотип і напис Rovertech (окремо, товарний знак — можна вимкнути)
    └─ Module_*  — опційні модулі (Starlink, вантаж), сховані за замовчуванням
Трубчастих надбудов (дуга, поручні, щогла камери) немає — за вимогою.

Запуск у Blender: Scripting → Open → Run Script.  Без GUI:
    blender -b --factory-startup --python zmiy_build.py
Текстури, розгортка й експорт — окремі скрипти (zmiy_texture.py, zmiy_export.py), див. README.md.

Координати: X праворуч, Y вперед (ніс), Z вгору, метри, 1 юніт = 1 м.
Габарити взято з референсу (обліт моделі пожежної версії «Змія», ArtStation) — див. README.md, «Розміри».
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

# =================================================================== параметри
P = dict(
    # --- колеса: шина KABAT IMP 10.0/75-15.3 (Ø 0,77, профіль 0,287), обід 15,3" сталевий, глибокий
    tire_r=0.385, tire_w=0.287,
    disc_w=0.040,             # площина диска відносно центру колеса (+ = назовні)
    wheel_x=0.5565, axle_f=0.345, axle_r=-0.528, wheel_z=0.385,      # колія по шинах 1,40 м, база 0,873 м
    lugs=24, wheel_segs=128,
    # --- нижній корпус (вузький короб між колесами)
    hull_x=0.365, hull_z0=0.295, hull_y0=-0.891, hull_y1=0.620,
    # --- кузов-«ванна»: палуба й бортові стінки з прорізами (ширина по стінках 1,23 м)
    deck_z=0.862, deck_t=0.004, side_x=0.615, wall_t=0.005,
    wall_z0=0.848, wall_z1=0.990,
    wall_y0=-0.926, wall_y0_top=-0.780, wall_z0_ch=0.897,
    wall_y1_top=0.549, wall_y1_ch=0.658, wall_z1_ch=0.931, wall_y1=0.676,
    deck_y1=0.660,            # передня кромка палуби = верх похилого листа носа
    # --- ніс: похилий верхній лист (трапеція між стінками) → лобовий лист (лого) → нижній лист
    nose_up_z=0.875,          # верхня кромка похилого листа
    nose_top_hw=0.466, nose_top_y=0.715, nose_top_z=0.800,          # злам: верх лобового листа
    nose_mid_hw=0.500, nose_mid_t=0.74,      # найширше місце лобового листа (частка довжини від верху)
    chin_hw=0.376, chin_y=0.925, chin_z=0.455,
    nose_bot_y=0.743, nose_bot_z=0.291,
    nose_side_hw=0.480, nose_side_y=0.790, nose_side_z=0.400,
    # --- корма (як у попередній версії): відкидний борт на рівні кінців стінок, під ним нижня панель
    tub_y0=-0.931,            # площина борту = задній край палуби й кінці бортових стінок
    gate_hw=0.400, gate_z0=0.700, gate_z1=1.030, gate_cut=0.075,
    rear_hw=0.330, rear_z0=0.330, rear_z1=0.675,
    hitch_z=0.490,
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
# Шина KABAT IMP 10.0/75-15.3 (як на референсі): Ø 0,77 м, профіль ~0,29 м, обід 15,3".
TIRE_HALF = [  # (w, r) поверхні каркаса (дно канавок) від центру протектора до борту, м
    (0.000, 0.3720), (0.040, 0.3718), (0.080, 0.3705), (0.105, 0.3670), (0.122, 0.3600),
    (0.134, 0.3490), (0.141, 0.3350), (0.1450, 0.3150), (0.1462, 0.2900), (0.1448, 0.2660),
    (0.1468, 0.2600), (0.1468, 0.2540), (0.1430, 0.2460), (0.1380, 0.2340), (0.1300, 0.2230),
    (0.1210, 0.2150), (0.1150, 0.2115)]


def _half_profile_dense(n=240):
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


def _tread_blocks(pitches):
    """Блоки протектора: [(side, theta0, [(sigma, s_lo, s_hi), ...], h0)], s — дуга по окружності (м)."""
    out = []
    P_arc = 2 * math.pi * 0.372 / pitches
    rnd = __import__('random').Random(7)
    for k in range(pitches):
        th = 2 * math.pi * k / pitches
        for side in (1, -1):
            off = 0.0 if side > 0 else P_arc / 2
            j = rnd.uniform(-0.003, 0.003)
            # внутрішній блок (біля центральної зигзаг-канавки)
            inner = [(0.007, -0.031 + j, 0.027), (0.020, -0.039, 0.036 + j), (0.040, -0.041, 0.039),
                     (0.058, -0.038 + j, 0.035), (0.066, -0.029, 0.028 - j)]
            out.append((side, th + off / 0.372, inner, 0.015))
            # плечовий блок (заходить на боковину), через один — довгий/короткий
            lng = (k % 2 == 0)
            e = 0.172 if lng else 0.158
            sh = [(0.077, -0.034 - j, 0.032), (0.095, -0.041, 0.038 + j), (0.125, -0.042, 0.040),
                  (0.150, -0.039 + j, 0.037), (e, -0.030, 0.030 - j)]
            out.append((side, th + (off + P_arc / 2) / 0.372, sh, 0.015))
    return out


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

    # --- блоковий протектор (шашки), шахове розташування
    dense, total = _half_profile_dense()
    tread = []
    for side, th0, secs, h0 in _tread_blocks(p['lugs']):
        rings = []
        for (sig, s_lo, s_hi) in secs:
            (w, r), (nw, nr) = tire_surface(sig, dense)
            h = h0 if sig < 0.10 else h0 * max(0.45, 1.0 - (sig - 0.10) * 7.5)
            ring = []
            for (ss, lift, ins) in ((s_lo, -0.003, 0.0), (s_lo, h, 0.0022), (s_hi, h, -0.0022), (s_hi, -0.003, 0.0)):
                th = th0 + (ss + ins) / 0.372
                rr = r + nr * lift
                ww = (w + nw * lift) * side
                ring.append(bm.verts.new((ww, rr * math.cos(th), rr * math.sin(th))))
            rings.append(ring)
        for i in range(len(rings) - 1):
            a, b = rings[i], rings[i + 1]
            for q in range(4):
                q2 = (q + 1) % 4
                try:
                    tread.append(bm.faces.new((a[q], a[q2], b[q2], b[q])))
                except ValueError:
                    pass
        tread.append(bm.faces.new(rings[0][::-1]))
        tread.append(bm.faces.new(rings[-1]))
    set_mat(tread, 0)

    # --- обід 15,3": тонкостінна оболонка уздовж осьової лінії (w, r)
    cl = [(0.1225, 0.2130), (0.1190, 0.2045), (0.1160, 0.1960), (0.0950, 0.1945), (0.0820, 0.1920),
          (0.0700, 0.1760), (0.0550, 0.1720), (-0.0500, 0.1720), (-0.0650, 0.1760), (-0.0780, 0.1920),
          (-0.0950, 0.1945), (-0.1160, 0.1960), (-0.1190, 0.2045), (-0.1225, 0.2130)]
    cl = [Vector(c) for c in cl]
    th_r = 0.0018
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

    def lip(c, d_out):
        return [c + d_out * 0.0025]
    loop = outer + lip(cl[-1], (cl[-1] - cl[-2]).normalized()) + inner[::-1] + lip(cl[0], (cl[0] - cl[1]).normalized())
    rim_faces = bm_lathe(bm, [(q.y, q.x) for q in loop], segs, Mx, closed=True)
    set_mat(rim_faces, 1)

    # --- глибокий суцільний диск зі штампованим кільцем (замкнений профіль (r, w))
    wd = p['disc_w']
    t = 0.006
    disc = [(0.1735, wd - 0.012), (0.1735, wd - 0.012 + t), (0.1520, wd + t), (0.1440, wd + 0.010 + t),
            (0.0700, wd + 0.010 + t), (0.0620, wd + 0.016 + t), (0.0380, wd + 0.016 + t),
            (0.0380, wd + 0.016), (0.0600, wd + 0.016), (0.0680, wd + 0.010), (0.1430, wd + 0.010),
            (0.1500, wd), (0.1700, wd - 0.012)]
    df = bm_lathe(bm, [(r, w) for (r, w) in disc], 96, Mx, closed=True)
    set_mat(df, 1)
    # маточина й піввісь до бобишки корпусу
    hub_prof = [(0.0, -0.170), (0.048, -0.170), (0.048, -0.090), (0.075, -0.084), (0.075, -0.070),
                (0.036, -0.068), (0.036, wd + 0.016), (0.0, wd + 0.016)]
    set_mat(bm_lathe(bm, [(r, h) for (r, h) in hub_prof], 48, Mx), 1)
    # ковпачок маточини
    cap_prof = [(0.0, wd + 0.020), (0.034, wd + 0.020), (0.034, wd + 0.030), (0.030, wd + 0.034),
                (0.0235, wd + 0.034), (0.0215, wd + 0.029), (0.0160, wd + 0.029), (0.0150, wd + 0.042),
                (0.0110, wd + 0.046), (0.0, wd + 0.046)]
    set_mat(bm_lathe(bm, [(r, h) for (r, h) in cap_prof], 48, Mx), 2)
    # 5 гайок на PCD 135
    for k in range(5):
        a = math.radians(90 + 72 * k)
        pos = Vector((wd + 0.016 + t, 0.0675 * math.cos(a), 0.0675 * math.sin(a)))
        q = Vector((1, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4()
        M = Matrix.Translation(pos) @ q @ Matrix.Scale(1.15, 4)
        for tmpl in (NUT_HEX, STUD):
            vv, ff = tmpl
            set_mat(bm_from_pydata(bm, [tuple(M @ Vector(v)) for v in vv], ff), 2)
    # вентиль у колодязі обода
    va = math.radians(-58)
    vb = Vector((0.03, 0.172 * math.cos(va), 0.172 * math.sin(va)))
    vt = vb + Vector((0.034, -0.010 * math.cos(va), -0.010 * math.sin(va)))
    set_mat(bm_cyl(bm, vb, vt, 0.0045, 10, 0.0038), 2)
    set_mat(bm_cyl(bm, vt, vt + (vt - vb).normalized() * 0.008, 0.0042, 10), 0)

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
    side = [(y0, z0 + 0.06), (y0 + 0.06, z0), (y1 - 0.02, z0), (y1, z0 + 0.02), (y1, ztop - 0.002), (y0, ztop - 0.002)]
    M = frame((-hx, 0, 0), (0, 1, 0), (0, 0, 1))
    hull = plate('Body', "Body_Hull", side, (), t=2 * hx, M=M, bev=0.010)
    # верх закритий палубою, перед — носом: ці грані не видно
    drop_faces(hull, lambda f: (f.normal.z > 0.99 and f.calc_center_median().z > ztop - 0.02) or
               (f.normal.y > 0.99 and f.calc_center_median().y > y1 - 0.005))
    # вертикальні ребра жорсткості на бортах корпусу (видно між колесами)
    for s in (-1, 1):
        for yy in (-0.755, -0.455, -0.160, 0.145, 0.445):
            x0, x1 = sorted((s * hx, s * (hx + 0.006)))
            box('Body', "Body_HullRib", x0, x1, yy - 0.020, yy + 0.020, z0 + 0.03, ztop - 0.004, bev=0.0015, segs=1)
        x0, x1 = sorted((s * hx, s * (hx + 0.004)))
        box('Body', "Body_HullSeam", x0, x1, y0 + 0.02, y1 - 0.02, 0.566, 0.572, bev=0.001, segs=1)
    # бобишки моторів-коліс на бортах + болти по колу
    bm = bmesh.new()
    bolts = []
    for s in (-1, 1):
        for y in (p['axle_f'], p['axle_r']):
            x0 = s * (hx + 0.006)
            bm_lathe(bm, [(0.0, 0.0), (0.092, 0.0), (0.092, 0.012), (0.088, 0.016), (0.064, 0.016), (0.064, 0.030),
                          (0.060, 0.034), (0.0, 0.034)], 40,
                     Matrix.Translation((x0, y, p['wheel_z'])) @ Vector((s, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
            for k in range(6):
                a = math.radians(30 + 60 * k)
                bolts.append((Vector((x0 + s * 0.016, y + 0.078 * math.cos(a), p['wheel_z'] + 0.078 * math.sin(a))),
                              Vector((s, 0, 0))))
    bm_to_part('Body', "Body_MotorBosses", bm, ['paint'], angle=35.0)
    fasteners('Body', "Body_MotorBolts", bolts, NUT_HEX, scale=0.75)
    # захисний лист днища з болтами
    sk = [(y0 + 0.09, -hx + 0.03), (y1 - 0.06, -hx + 0.03), (y1 - 0.06, hx - 0.03), (y0 + 0.09, hx - 0.03)]
    Msk = frame((0, 0, z0 - 0.006), (0, 1, 0), (-1, 0, 0))
    skid = plate('Body', "Body_SkidPlate", [(a, b) for (a, b) in sk], (), t=0.006, M=Msk, bev=0.0015)
    drop_faces(skid, lambda f: f.normal.z > 0.99)
    bolts = []
    yy = y0 + 0.12
    while yy < y1 - 0.08:
        for s in (-1, 1):
            bolts.append((Vector((s * (hx - 0.06), yy, z0 - 0.006)), Vector((0, 0, -1))))
        yy += 0.2
    fasteners('Body', "Body_SkidBolts", bolts)


# =================================================================== кузов-«ванна»
def octagon(cx, cy, w, h, c):
    """Видовжений восьмикутник (проріз бортової стінки): ширина w, висота h, фаска c."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def wall_holes(y0, y1, zc):
    """Ряд прорізів: великий восьмикутник, овал, малий отвір над ними — як на референсі."""
    holes, y, k = [], y0, 0
    while y < y1:
        if k % 2 == 0:
            holes.append(octagon(y, zc - 0.004, 0.088, 0.044, 0.014))
        else:
            holes.append(rrect(y, zc - 0.006, 0.074, 0.026, 0.0125, 4))
        holes.append(circle(y + 0.084, zc + 0.030, 0.0055, 14))
        y += 0.168
        k += 1
    return holes


def build_tub():
    p = P
    zt = p['deck_z']
    sx, wt = p['side_x'], p['wall_t']
    ty0 = p['tub_y0']
    gw = p['gate_hw']

    # --- палуба: від кормового борту до похилого верхнього листа носа
    dy1 = p['deck_y1']
    deck = [(-sx + wt, ty0), (sx - wt, ty0), (sx - wt, dy1), (-sx + wt, dy1)]
    tie = []
    for yy in (-0.62, -0.30, 0.02, 0.34):
        for xx in (-0.30, 0.30):
            tie.append(rrect(xx, yy, 0.050, 0.020, 0.0095, 4))
    plate('Body', "Body_Deck", deck, tie, t=p['deck_t'], M=Matrix.Translation((0, 0, zt - p['deck_t'])), bev=0.0009)

    # --- бортові стінки з прорізами (профіль у площині YZ)
    z0, z1 = p['wall_z0'], p['wall_z1']
    y0, y0t, y1t, y1c, z1c, y1 = (p['wall_y0'], p['wall_y0_top'], p['wall_y1_top'], p['wall_y1_ch'],
                                  p['wall_z1_ch'], p['wall_y1'])
    outline = [(y0, z0), (y1, z0), (y1, z1c - 0.012), (y1c, z1c), (y1t, z1), (y0t, z1), (y0, p['wall_z0_ch'])]
    outline = round_poly(outline, {3: 0.01, 4: 0.012, 5: 0.012}, 3)
    holes = wall_holes(y0t + 0.075, y1t - 0.05, (z0 + z1) / 2 + 0.008)
    # похилий проріз і отвір на скосах (як на референсі)
    for (yy, zz, ang) in ((y0 + 0.075, z0 + 0.075, 33), (y1c - 0.028, z1c - 0.040, -33)):
        sl = rrect(0, 0, 0.060, 0.020, 0.0095, 4)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        holes.append([(yy + x * ca - y * sa, zz + x * sa + y * ca) for (x, y) in sl])
    bolts = []
    for s in (-1, 1):
        x0 = sx - wt if s > 0 else -sx
        M = frame((x0, 0, 0), (0, 1, 0), (0, 0, 1))
        plate('Body', "Body_Wall_" + ("L" if s < 0 else "R"), outline, holes, t=wt, M=M, bev=0.0012)
        for yy in (-0.755, -0.455, -0.160, 0.145, 0.445):
            for dz in (0.0,):
                bolts.append((Vector((s * sx, yy, z0 + 0.014 + dz)), Vector((s, 0, 0))))
        # кутові косинки під палубою біля стінки
        for yy in (-0.755, -0.160, 0.445):
            tri = [(0, 0), (0.055, 0), (0, -0.045)]
            Mg = frame((s * (sx - wt - 0.003), yy - 0.003, zt - p['deck_t']), (-s, 0, 0), (0, 0, 1))
            plate('Body', "Body_DeckGusset", tri, (), t=0.006, M=Mg)
    fasteners('Body', "Body_WallBolts", bolts)
    # кормові кути (смуги між відкидним бортом і бортовими стінками, під палубою)
    for s in (-1, 1):
        w = sx - wt - gw
        pts = [(0, zt - 0.100), (w, zt - 0.100), (w, zt), (0, zt)]
        M = frame((-sx + wt if s < 0 else gw, ty0, 0), (1, 0, 0), (0, 0, 1))
        plate('Body', "Body_RearCorner", pts, (), t=wt, M=M)


def build_rear():
    p = P
    y0 = p['tub_y0']
    gw, g0, g1, gc = p['gate_hw'], p['gate_z0'], p['gate_z1'], p['gate_cut']
    # --- відкидний борт: прямокутник зі скошеними верхніми кутами (лицем назад)
    gate = [(-gw, g0), (gw, g0), (gw, g1 - gc), (gw - gc, g1), (-gw + gc, g1), (-gw, g1 - gc)]
    gate = round_poly(gate, {2: 0.01, 3: 0.01, 4: 0.01, 5: 0.01}, 3)
    M = frame((0, y0, 0), (1, 0, 0), (0, 0, 1))
    plate('Body', "Body_Tailgate", gate, [circle(gw - 0.040, g1 - gc - 0.035, 0.008, 14),
                                         circle(-gw + 0.040, g1 - gc - 0.035, 0.008, 14)], t=0.005, M=M)
    # ребро жорсткості (відгин) по низу
    box('Body', "Body_TailgateRib", -gw + 0.03, gw - 0.03, y0 - 0.026, y0 - 0.004, g0 + 0.004, g0 + 0.024, bev=0.003)
    # завіса знизу (кулачки)
    bm = bmesh.new()
    zc = g0 - 0.004
    n = 9
    step = (2 * gw - 0.08) / n
    for k in range(n):
        xa = -gw + 0.04 + k * step
        bm_cyl(bm, (xa + 0.002, y0 - 0.010, zc), (xa + step - 0.002, y0 - 0.010, zc), 0.0105, 16)
    bm_to_part('Body', "Body_GateHinge", bm, ['paint'], angle=40.0)
    # засувки (шпінгалети) з ручками і скоби-приймачі на кормових кутах
    zl = g0 + 0.100
    for s in (-1, 1):
        x0 = s * 0.240
        bx0, bx1 = sorted((x0, x0 + s * 0.115))
        box('Body', "Body_Latch_Base", bx0, bx1, y0 - 0.010, y0 - 0.005, zl - 0.0175, zl + 0.0175, mat='zinc', bev=0.0015)
        tube('Body', "Body_Latch_Bolt", [(x0 + s * 0.010, y0 - 0.017, zl), (x0 + s * 0.200, y0 - 0.017, zl)],
             0.0068, mat='zinc', res=3)
        tube('Body', "Body_Latch_Handle", [(x0 + s * 0.050, y0 - 0.017, zl), (x0 + s * 0.050, y0 - 0.040, zl),
                                           (x0 + s * 0.050, y0 - 0.040, zl + 0.0375)], 0.0045, bend=0.008, mat='zinc', res=3)
        box('Body', "Body_Latch_Keeper", *sorted((s * (gw + 0.025), s * (gw + 0.050))),
            y0 - 0.028, y0 - 0.002, zl - 0.0135, zl + 0.0135, mat='zinc', bev=0.002)
    bm = bmesh.new()
    kx, kz = -0.165, zl + 0.040
    bm_cyl(bm, (kx, y0 - 0.005, kz), (kx, y0 - 0.030, kz), 0.006, 12)
    bm_lathe(bm, [(0.0, 0.0), (0.011, 0.0), (0.0135, 0.010), (0.0135, 0.026), (0.010, 0.034), (0.0, 0.036)], 20,
             Matrix.Translation((kx, y0 - 0.028, kz)) @ Vector((0, -1, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    bm_to_part('Body', "Body_Knob", bm, ['orange'], angle=40.0)

    # --- поличка під бортом і нижня кормова панель на задній стінці корпусу
    hy0 = p['hull_y0']
    box('Body', "Body_RearShelf", -gw + 0.02, gw - 0.02, hy0 - 0.004, y0 + 0.002, p['rear_z1'], p['rear_z1'] + 0.006,
        bev=0.0015)
    rw, r0, r1 = p['rear_hw'], p['rear_z0'], p['rear_z1']
    panel = chamfer_poly([(-rw, r0), (rw, r0), (rw, r1), (-rw, r1)], {0: 0.035, 1: 0.035})
    M = frame((0, hy0, 0), (1, 0, 0), (0, 0, 1))
    plate('Body', "Body_RearPanel", panel, (), t=0.005, M=M)
    bolts = [(Vector((xx, hy0 - 0.005, zz)), Vector((0, -1, 0)))
             for xx in (-rw + 0.03, rw - 0.03) for zz in (r0 + 0.045, r1 - 0.03)]
    bolts += [(Vector((xx, hy0 - 0.005, r0 + 0.030)), Vector((0, -1, 0))) for xx in (-0.10, 0.10)]
    # бічні замки-клямки нижньої панелі
    za, zb = r0 + 0.155, r0 + 0.285
    for s in (-1, 1):
        xx = s * (rw - 0.065)
        box('Body', "Body_DrawLatch_Base", xx - 0.018, xx + 0.018, hy0 - 0.011, hy0 - 0.005, za, zb,
            mat='zinc', bev=0.0015)
        tube('Body', "Body_DrawLatch_Lever", [(xx, hy0 - 0.016, zb - 0.005), (xx, hy0 - 0.026, (za + zb) / 2),
                                              (xx, hy0 - 0.018, za + 0.005)], 0.0055, bend=0.02, mat='zinc', res=3)
        tube('Body', "Body_DrawLatch_Loop", [(xx - 0.010, hy0 - 0.012, za), (xx - 0.010, hy0 - 0.014, za - 0.045),
                                             (xx + 0.010, hy0 - 0.014, za - 0.045), (xx + 0.010, hy0 - 0.012, za)],
             0.0028, bend=0.006, mat='zinc', res=2)
        bolts += [(Vector((xx, hy0 - 0.011, zz)), Vector((0, -1, 0))) for zz in (za + 0.018, zb - 0.018)]
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
        M = frame((s * 0.125 - 0.006, hy0 - 0.004, hz), (0, -1, 0), (0, 0, 1))
        plate('Body', "Body_ShackleTab", tab, [circle(0.036, 0.0, 0.0115, 18)], t=0.012, M=M)
    fasteners('Body', "Body_RearBolts", bolts)


# =================================================================== ніс
def nose_geometry():
    """Ключові точки носа: похилий верхній лист (трапеція), лобовий лист (лого), нижній лист, боковини."""
    p = P
    zt = p['deck_z']
    top = Vector((p['nose_top_y'], p['nose_top_z']))
    chin = Vector((p['chin_y'], p['chin_z']))
    d = chin - top
    L = d.length
    dn = d.normalized()

    def on_plate(s, x):
        q = top + dn * s
        return Vector((x, q.x, q.y))

    def hw_at(s):
        t = s / L
        tm = p['nose_mid_t']
        if t <= tm:
            return p['nose_top_hw'] + (p['nose_mid_hw'] - p['nose_top_hw']) * t / tm
        return p['nose_mid_hw'] + (p['chin_hw'] - p['nose_mid_hw']) * (t - tm) / (1 - tm)
    nrm = Vector((0, -dn.y, dn.x))
    if nrm.y < 0:
        nrm = -nrm
    sm = L * p['nose_mid_t']
    sw, sy, sz = p['nose_side_hw'], p['nose_side_y'], p['nose_side_z']
    pts = []
    for sg in (-1, 1):
        pts += [on_plate(0.0, sg * p['nose_top_hw']), on_plate(sm, sg * p['nose_mid_hw']),
                on_plate(L, sg * p['chin_hw']),
                Vector((sg * p['chin_hw'], p['nose_bot_y'], p['nose_bot_z'])),
                Vector((sg * sw, sy, sz)),
                Vector((sg * sw, p['nose_top_y'] - 0.03, p['nose_top_z'] - 0.005)),
                Vector((sg * p['hull_x'], p['hull_y1'] - 0.02, p['nose_bot_z'])),
                Vector((sg * p['hull_x'], p['hull_y1'] - 0.02, zt - 0.010)),
                Vector((sg * p['nose_top_hw'], p['deck_y1'] - 0.01, zt - 0.010))]
    xin = p['side_x'] - p['wall_t']
    upper = [Vector((-xin, p['deck_y1'], p['nose_up_z'])), Vector((xin, p['deck_y1'], p['nose_up_z'])),
             on_plate(0.0, p['nose_top_hw']), on_plate(0.0, -p['nose_top_hw'])]
    return dict(pts=pts, upper=upper, on_plate=on_plate, hw_at=hw_at, L=L, n=nrm, dn=Vector((0.0, dn.x, dn.y)))


def wheel_arch_cutter(y, s, r=0.418):
    """Циліндр-вибірка навколо переднього колеса (зазор до шини)."""
    p = P
    x = s * p['wheel_x']
    hw = p['tire_w'] / 2 + 0.03
    return cyl_mesh((x - hw, y, p['wheel_z']), (x + hw, y, p['wheel_z']), r, 48)


def build_nose():
    p = P
    g = nose_geometry()
    on, L, n = g['on_plate'], g['L'], g['n']
    cutters = [wheel_arch_cutter(p['axle_f'], s) for s in (-1, 1)]
    # овальні буксирувальні отвори в нижніх кутах лобового листа
    for s in (-1, 1):
        c = on(L - 0.085, s * (p['chin_hw'] + 0.035))
        me = cyl_mesh(c + n * 0.03, c - n * 0.02, 0.018, 24)
        me.transform(Matrix.Translation(c) @ _scale_along(Vector((1, 0, 0)), 2.1) @ Matrix.Translation(-c))
        cutters.append(me)
    convex_solid('Body', "Body_Nose", g['pts'], bev=0.006, segs=2, cutters=cutters)
    # похилий верхній лист: трапеція від стінок (на рівні палуби) до зламу лобового листа
    u = g['upper']
    o = (u[0] + u[1]) / 2
    vdir = ((u[2] + u[3]) / 2 - o)
    Lv = vdir.length
    xin = p['side_x'] - p['wall_t']
    hw = p['nose_top_hw']
    outline = [(-xin, 0.0), (xin, 0.0), (hw, Lv + 0.004), (-hw, Lv + 0.004)]
    M = frame(o, (1, 0, 0), vdir) @ Matrix.Translation((0, 0, -0.005))
    plate('Body', "Body_NoseUpper", outline, (), t=0.005, M=M, bev=0.0012)
    # вертикальна смужка між палубою і верхньою кромкою похилого листа
    box('Body', "Body_NoseLip", -xin, xin, p['deck_y1'] - 0.004, p['deck_y1'], p['deck_z'] - 0.02, p['nose_up_z'],
        bev=0.0012, segs=1)
    # П-ручка біля «підборіддя»
    a, b = on(L - 0.050, -0.085), on(L - 0.050, 0.085)
    up = -g['dn']
    tube('Body', "Body_NoseHandle", [a - n * 0.005, a + n * 0.045 + up * 0.010, b + n * 0.045 + up * 0.010, b - n * 0.005],
         0.0095, bend=0.020, mat='paint', res=4)
    # вертикальний стрижень-фіксатор ліворуч і гак праворуч (як на референсі)
    rt, rb = on(0.030, -0.330), on(0.240, -0.330)
    tube('Body', "Body_NoseRod", [rt + n * 0.022, rb + n * 0.022], 0.0062, mat='paint', res=3)
    tube('Body', "Body_NoseRodTip", [rt + n * 0.022 - g['dn'] * 0.010, rt + n * 0.022 - g['dn'] * 0.026], 0.0090,
         mat='paint', res=3)
    for s_ in (0.050, 0.205):
        q = on(s_, -0.330)
        bm = bmesh.new()
        bm_box(bm, -0.012, 0.012, -0.010, 0.010, 0.0, 0.026, 0.002, 1)
        bmesh.ops.transform(bm, matrix=frame(q, (1, 0, 0), -g['dn']), verts=bm.verts[:])
        bm_to_part('Body', "Body_NoseRodTab", bm, ['paint'])
    hk = on(0.120, 0.300)
    bm = bmesh.new()
    bm_box(bm, -0.025, 0.025, -0.022, 0.022, 0.0, 0.006, 0.0015, 1)
    bmesh.ops.transform(bm, matrix=frame(hk, (1, 0, 0), -g['dn']), verts=bm.verts[:])
    bm_to_part('Body', "Body_NoseHookPlate", bm, ['paint'])
    tube('Body', "Body_NoseHook", [hk + n * 0.006 + g['dn'] * 0.012, hk + n * 0.034 + g['dn'] * 0.012,
                                   hk + n * 0.034 - g['dn'] * 0.020, hk + n * 0.020 - g['dn'] * 0.030],
         0.0055, bend=0.010, mat='zinc', res=3)
    # буксирувальні вушка по боках «підборіддя»
    for s in (-1, 1):
        c = on(L - 0.030, s * (p['chin_hw'] - 0.010))
        tab = round_poly([(0, -0.025), (0.055, -0.025), (0.055, 0.025), (0, 0.025)], {1: 0.024, 2: 0.024}, 6)
        M = Matrix.Translation(c + Vector((-0.004, 0, 0))) @ Matrix.Rotation(math.radians(-25), 4, 'X') @ \
            frame((0, 0, 0), (0, 1, 0), (0, 0, 1))
        plate('Body', "Body_ChinTab", tab, [circle(0.030, 0.0, 0.010, 16)], t=0.008, M=M)
    # болти по верху лобового листа
    bolts = [(on(0.030, xx), n) for xx in (-0.20, -0.07, 0.07, 0.20)]
    fasteners('Body', "Body_NoseBolts", bolts)


def _scale_along(axis, k):
    a = Vector(axis).normalized()
    M = Matrix.Identity(3)
    for i in range(3):
        for j in range(3):
            M[i][j] += (k - 1.0) * a[i] * a[j]
    return M.to_4x4()


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
    c = g['on_plate'](0.47 * g['L'], 0.0)
    out.append(decal("Decal_Logo_Nose", c, (-1, 0, 0), -g['dn'], 0.150, 0.135, "Logo"))
    y = p['tub_y0'] - 0.005
    zc = p['gate_z0'] + 0.62 * (p['gate_z1'] - p['gate_z0'])
    out.append(decal("Decal_Logo_Rear", (-0.170, y, zc + 0.004), (1, 0, 0), (0, 0, 1), 0.075, 0.068, "Logo"))
    out.append(decal("Decal_Text_Rear", (0.045, y, zc), (1, 0, 0), (0, 0, 1), 0.320, 0.056, "Text"))
    for ob in out:
        ob.parent = body
    return out


# =================================================================== опційні модулі
def build_modules(root):
    """Опційні модулі (сховані): Starlink Mini на низькій підставці на палубі, вантаж на палубі."""
    p = P
    mods = []
    zd = p['deck_z']
    # --- Starlink Mini (298×259×38,5 мм) на складаній підставці в передній частині палуби
    PARTS['Module_Starlink'] = []
    box('Module_Starlink', "SL_Dish", -0.1295, 0.1295, -0.149, 0.149, 0.0, 0.0385, mat='paint', bev=0.006, segs=3)
    sl = PARTS['Module_Starlink'][-1]
    sl.data.materials.clear()
    sl.data.materials.append(make_material("Zmiy_Starlink_White", "#D8D8D2", 0.55, 0.0))
    box('Module_Starlink', "SL_Kick", -0.020, 0.020, -0.060, 0.010, -0.075, 0.002, mat='tube', bev=0.003)
    for ob in PARTS['Module_Starlink']:
        ob.data.transform(Matrix.Translation((0.30, 0.33, zd + 0.095)) @ Matrix.Rotation(math.radians(-25), 4, 'X'))
    box('Module_Starlink', "SL_Base", 0.22, 0.38, 0.24, 0.40, zd, zd + 0.012, mat='tube', bev=0.003)
    # --- вантаж: три ящики, стягнуті ременем
    PARTS['Module_Cargo'] = []
    box('Module_Cargo', "Cargo_Box1", -0.58, -0.04, -0.76, -0.38, zd, zd + 0.30, bev=0.012, segs=2)
    box('Module_Cargo', "Cargo_Box2", 0.04, 0.58, -0.74, -0.36, zd, zd + 0.26, bev=0.012, segs=2)
    box('Module_Cargo', "Cargo_Box3", -0.40, 0.20, -0.28, 0.06, zd, zd + 0.22, bev=0.012, segs=2)
    tube('Module_Cargo', "Cargo_Strap", [(-0.64, -0.58, zd), (-0.58, -0.58, zd + 0.305), (0.58, -0.58, zd + 0.265),
                                         (0.64, -0.58, zd)], 0.004, bend=0.03, mat='tube', res=2)
    for key in ('Module_Starlink', 'Module_Cargo'):
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
    bm_box(bm, -p['side_x'], p['side_x'], p['tub_y0'] - 0.005, p['wall_y1'], p['wall_z0'] - 0.02, p['wall_z1'])
    add("UCX_Zmiy_Logistic_00", bm)
    bm = bmesh.new()
    bm_box(bm, -p['hull_x'], p['hull_x'], p['hull_y0'], p['hull_y1'], p['hull_z0'], p['wall_z0'] - 0.02)
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


RESERVED = ("Zmiy_Logistic", "Body", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR",
            "Module_Starlink", "Module_Cargo")


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

    body = join_group("Body", PARTS.pop('Body'))
    body.parent = root
    build_wheels(root)
    build_decals(body)
    build_modules(root)
    build_collision(root)
    return root


if __name__ == "__main__":
    build_all()
    print("Zmiy_Logistic: готово")
