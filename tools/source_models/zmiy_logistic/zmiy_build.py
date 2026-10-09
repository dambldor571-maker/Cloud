# -*- coding: utf-8 -*-
"""
НРК «Змій Логістичний» (Rovertech, 2026) — hero-asset для гри, Blender 4.2+ (перевірено на 4.5 LTS і 5.2).

Будує повну геометрію (без текстур) у колекції "Zmiy_Logistic":
    Zmiy_Logistic (empty, на землі під центром)
    ├─ Hull      — корпус: короб між колесами, ребра, фланці під піддон, бобишки моторів-коліс
    ├─ Nose      — ніс між передніми колесами, похилий лист із крилами над колесами
    ├─ Rear      — корма: поличка й задня панель на болтах
    ├─ SkidPlate — захисний лист днища на болтах
    ├─ FrontGuard — накладна захисна плита спереду на втулках, бокові кронштейни
    ├─ Deck      — піддон-палуба: окрема гнута деталь, кріпиться зверху на корпус (шпильки M8 знизу)
    ├─ Wheel_FL / Wheel_FR / Wheel_RL / Wheel_RR — півот у центрі колеса, вісь обертання = локальна X
    └─ Module_*  — опційні модулі (Starlink, вантаж), сховані за замовчуванням
Трубчастих надбудов (дуга, поручні, щогла камери) немає — за вимогою. Відкидного борту, фаркопа,
логотипів і дрібних деталей носа теж немає: далі модель розвивається як власний дизайн.

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
    # --- піддон-палуба: один гнутий лист 4 мм — палуба, бортики вгору (прорізи), кормовий відгин униз;
    #     ширина по бортиках 1,23 м; лежить на фланцях корпусу
    deck_z=0.862, deck_t=0.004, side_x=0.615, wall_t=0.004,
    bend_r=0.006,             # внутрішній радіус згину (1,5 товщини)
    wall_z1=0.990,
    wall_y0=-0.920, wall_y0_top=-0.780, wall_z0_ch=0.897,
    wall_y1_top=0.527, wall_y1_ch=0.636, wall_z1_ch=0.931, wall_y1=0.654,   # перед бортика = край палуби
    deck_y1=0.660,            # передня кромка палуби = верхня кромка лобового листа носа
    # --- ніс: ОДИН плаский лобовий лист від верхньої кромки над палубою до «підборіддя» (ширина носа = корпус,
    #     ±hull_x, без скосів кутів); угорі в тій самій площині — крила до бортиків піддона з відбортовкою;
    #     боковини вертикальні, ніс між колесами (до шини 4,8 см); нижній лист — назад до днища
    nose_up_z=0.875,          # верхня кромка лобового листа (на 13 мм вище палуби — упор для вантажу)
    chin_y=0.925, chin_z=0.455,
    nose_bot_y=0.743, nose_bot_z=0.291,
    nose_wing_s=0.070,        # крила: від кутів бортиків до ширини носа на цій відстані вздовж листа
    # --- накладна захисна плита спереду (окрема складова FrontGuard): паралельно лобовому листу
    guard_gap=0.025, guard_t=0.008,          # проміжок до лобового листа (рознесений захист) і товщина
    guard_side_z=0.580, guard_bot_hw=0.450,  # до цієї висоти боки вертикальні (±side_x), далі скоси до ±0,45 внизу
    guard_bracket_z=0.720,                   # бокові кронштейни: висота (над шиною ~9 см)
    front_lights=False,                      # фари + ІЧ у козирках на плиті з кабелями (поки вимкнено — рішення власника)
    rear_lights=False,                       # задні ліхтарі на нижній кормовій панелі (поки вимкнено — рішення власника)
    # --- корма: задній край палуби з фартухом, під ним поличка й нижня панель на задній стінці корпусу
    tub_y0=-0.931,            # задній край палуби й кінці бортових стінок
    rear_hw=0.330, rear_z0=0.450, rear_z1=0.675,   # нижня задня панель — над заднім скосом корпусу
    hull_rear_ch=0.150,       # скіс заднього низу корпусу 15×15 см: рампа при русі заднім ходом через перешкоду
    # сервісні люки на бортах корпусу між колесами (доступ до контролерів моторів): центр, ширина, висота
    hatch_yc=-0.0075, hatch_zc=0.715, hatch_w=0.240, hatch_h=0.210,
)

COLL_NAME = "Zmiy_Logistic"
MAT_DEF = {
    # ключ: (назва, sRGB hex, roughness, metallic)
    'paint': ("Zmiy_Paint_Olive", "#434A37", 0.74, 0.0),
    'tube': ("Zmiy_Tube_Black", "#1A1A1A", 0.45, 0.0),
    'rubber': ("Zmiy_Rubber", "#1C1C1C", 0.90, 0.0),
    'rim': ("Zmiy_Rim_Black", "#151515", 0.50, 0.0),
    'zinc': ("Zmiy_Bolt_Zinc", "#8A8A85", 0.35, 1.0),
    'dark': ("Zmiy_Plastic_Black", "#1E1F1C", 0.60, 0.0),   # роз'єм, кришка, вимикач, корпус кнопки
    'red': ("Zmiy_EStop_Red", "#A82A1E", 0.45, 0.0),        # аварійна кнопка (стандартно червона)
    'yellow': ("Zmiy_EStop_Yellow", "#C9A227", 0.55, 0.0),  # фон аварійної кнопки (стандартно жовтий)
    'lens': ("Zmiy_Lens_Clear", "#C2C6BE", 0.06, 0.0),      # скло фар і ліхтаря заднього ходу
    'lens_red': ("Zmiy_Lens_Red", "#8C1C16", 0.10, 0.0),    # габарит/стоп
    'lens_ir': ("Zmiy_Lens_IR", "#1C0F0E", 0.08, 0.0),      # ІЧ-прожектор (фільтр майже чорний)
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


WELD_R = 0.0028     # зварний шов: валик Ø5,6 мм (катет ≈ 4 мм), вісь — на лінії стику деталей


def welds(group, name, lines, r=WELD_R):
    """Кутові/стикові шви: [(A, B), ...] — валик уздовж лінії стику (назовні видно чверть-півкола)."""
    bm = bmesh.new()
    for a, b in lines:
        bm_cyl(bm, Vector(a), Vector(b), r, 8)
    return bm_to_part(group, name, bm, ['paint'], angle=50.0)


def weld_ring(bm, center, axis, radius, r=WELD_R, segs=40):
    """Кільцевий шов навколо приварної деталі (бобишки, штуцера)."""
    M = Matrix.Translation(Vector(center)) @ Vector(axis).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    prof = [(radius + r * math.cos(a), r * math.sin(a)) for a in (2 * math.pi * k / 8 for k in range(8))]
    bm_lathe(bm, prof, segs, M, closed=True)


# =================================================================== нижній корпус
def build_hull():
    p = P
    hx, z0 = p['hull_x'], p['hull_z0']
    ztop = p['deck_z'] - p['deck_t']
    y0, y1 = p['hull_y0'], p['hull_y1']
    ch = p['hull_rear_ch']
    side = [(y0, z0 + ch), (y0 + ch, z0), (y1 - 0.02, z0), (y1, z0 + 0.02), (y1, ztop - 0.002), (y0, ztop - 0.002)]
    M = frame((-hx, 0, 0), (0, 1, 0), (0, 0, 1))
    plate('Hull', "Hull_Box", side, (), t=2 * hx, M=M, bev=0.010)   # закритий короб: без носа й піддона теж цілий
    # вертикальні ребра жорсткості на бортах корпусу (видно між колесами); вгорі підпирають фланці.
    # Борт зварений із двох листів (стиковий шов на zs); ребра над швом перервані — виріз 24 мм,
    # щоб не наварювати ребро на шов (інакше перегрів і тріщини в місці перетину швів)
    zs = 0.569
    wl = []
    for s in (-1, 1):
        for yy in (-0.755, -0.455, -0.160, 0.145, 0.445):
            x0, x1 = sorted((s * hx, s * (hx + 0.006)))
            zr = max(z0 + 0.03, z0 + (y0 + ch) - (yy - 0.020) + 0.010)   # над заднім скосом
            pieces = [(zr, zs - 0.012), (zs + 0.012, ztop - 0.006)] if zr < zs - 0.03 else [(zr, ztop - 0.006)]
            for za, zz in pieces:
                box('Hull', "Hull_Rib", x0, x1, yy - 0.020, yy + 0.020, za, zz, bev=0.0015, segs=1)
                wl += [((s * hx, yy + d, za), (s * hx, yy + d, zz)) for d in (-0.020, 0.020)]
        # фланець по верху борту: на нього лягає піддон, крізь нього — шпильки піддона (гайки знизу)
        x0, x1 = sorted((s * hx, s * (hx + 0.035)))
        box('Hull', "Hull_Flange", x0, x1, y0 + 0.03, y1 - 0.03, ztop - 0.006, ztop, bev=0.0015, segs=1)
        wl.append(((s * hx, y0 + 0.03, ztop - 0.006), (s * hx, y1 - 0.03, ztop - 0.006)))   # шов під фланцем
    welds('Hull', "Hull_Welds", wl)
    welds('Hull', "Hull_SeamWeld", [((s * hx, y0 + 0.02, zs), (s * hx, y1 - 0.02, zs)) for s in (-1, 1)], r=0.0035)
    # сервісні люки між колесами (там до борту можна дістатися під звисом палуби): кришка 3 мм на 8 болтах M6
    hy, hz, hw, hh = p['hatch_yc'], p['hatch_zc'], p['hatch_w'], p['hatch_h']
    lid = round_poly([(hy - hw / 2, hz - hh / 2), (hy + hw / 2, hz - hh / 2), (hy + hw / 2, hz + hh / 2),
                      (hy - hw / 2, hz + hh / 2)], {0: 0.015, 1: 0.015, 2: 0.015, 3: 0.015}, 3)
    hb = []
    for s in (-1, 1):
        plate('Hull', "Hull_Hatch", lid, (), t=0.003, bev=0.0008,
              M=frame((hx if s > 0 else -hx - 0.003, 0, 0), (0, 1, 0), (0, 0, 1)))
        for dy, dz in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
            hb.append((Vector((s * (hx + 0.003), hy + dy * (hw / 2 - 0.018), hz + dz * (hh / 2 - 0.018))),
                       Vector((s, 0, 0))))
    fasteners('Hull', "Hull_HatchBolts", hb, scale=0.7)
    # бобишки моторів-коліс на бортах + болти по колу
    bm = bmesh.new()
    bolts = []
    for s in (-1, 1):
        for y in (p['axle_f'], p['axle_r']):
            x0 = s * hx
            bm_lathe(bm, [(0.0, 0.0), (0.092, 0.0), (0.092, 0.018), (0.088, 0.022), (0.064, 0.022), (0.064, 0.036),
                          (0.060, 0.040), (0.0, 0.040)], 40,
                     Matrix.Translation((x0, y, p['wheel_z'])) @ Vector((s, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4())
            weld_ring(bm, (x0, y, p['wheel_z']), (s, 0, 0), 0.092)
            for k in range(6):
                a = math.radians(30 + 60 * k)
                bolts.append((Vector((x0 + s * 0.022, y + 0.078 * math.cos(a), p['wheel_z'] + 0.078 * math.sin(a))),
                              Vector((s, 0, 0))))
    bm_to_part('Hull', "Hull_MotorBosses", bm, ['paint'], angle=35.0)
    fasteners('Hull', "Hull_MotorBolts", bolts, NUT_HEX, scale=0.75)
    # сапун — мембранний клапан вирівнювання тиску: герметичний корпус «дихає» при нагріванні/охолодженні,
    # не втягуючи воду й пил. Найвища доступна точка — лівий борт під фланцем, під звисом палуби (захист зверху)
    out = Vector((-1, 0, 0))
    bp = Vector((-hx, -0.300, 0.812))
    bm = bmesh.new()
    bm_cyl(bm, bp, bp + out * 0.006, 0.019, 24)                  # приварна бобишка з різьбою
    weld_ring(bm, bp, out, 0.019)
    bm_to_part('Hull', "Hull_BreatherBoss", bm, ['paint'], angle=40.0)
    fasteners('Hull', "Hull_BreatherBody", [(bp + out * 0.006, out)], NUT_HEX, scale=1.25)
    bm = bmesh.new()
    bm_lathe(bm, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.006), (0.013, 0.012), (0.007, 0.015), (0.0, 0.016)], 28,
             Matrix.Translation(bp + out * 0.0254) @ out.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    bm_to_part('Hull', "Hull_BreatherCap", bm, ['dark'], angle=40.0)
    # зливні пробки конденсату в днищі: з внутрішнім шестигранником, урівень із захисним листом (у його отворах)
    drains = ((0.0, -0.550), (0.0, 0.400))
    bm, bs = bmesh.new(), bmesh.new()
    for x, y in drains:
        bm_lathe(bm, [(0.0, 0.0), (0.019, 0.0), (0.019, -0.0045), (0.017, -0.0055), (0.0, -0.0055)], 28,
                 Matrix.Translation((x, y, z0)))
        bm_lathe(bs, [(0.0, 0.0), (0.0069, 0.0), (0.0069, 0.0006), (0.0, 0.0006)], 6,
                 Matrix.Translation((x, y, z0 - 0.0060)))
    bm_to_part('Hull', "Hull_DrainPlugs", bm, ['zinc'], angle=40.0)
    bm_to_part('Hull', "Hull_DrainSockets", bs, ['dark'], angle=40.0)
    # захисний лист днища з болтами (отвори Ø50 під зливні пробки)
    sk = [(y0 + ch + 0.02, -hx + 0.03), (y1 - 0.06, -hx + 0.03), (y1 - 0.06, hx - 0.03), (y0 + ch + 0.02, hx - 0.03)]
    Msk = frame((0, 0, z0 - 0.006), (0, 1, 0), (-1, 0, 0))
    skid = plate('SkidPlate', "Skid_Plate", [(a, b) for (a, b) in sk], [circle(y, -x, 0.025, 28) for x, y in drains],
                 t=0.006, M=Msk, bev=0.0015)
    drop_faces(skid, lambda f: f.normal.z > 0.99)
    bolts = []
    yy = y0 + ch + 0.05
    while yy < y1 - 0.08:
        for s in (-1, 1):
            bolts.append((Vector((s * (hx - 0.06), yy, z0 - 0.006)), Vector((0, 0, -1))))
        yy += 0.2
    fasteners('SkidPlate', "Skid_Bolts", bolts)


# =================================================================== піддон-палуба (окрема деталь)
def octagon(cx, cy, w, h, c):
    """Видовжений восьмикутник (проріз бортика): ширина w, висота h, фаска c."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def wall_holes(y0, y1, zc):
    """Ряд прорізів: великий восьмикутник, овал, малий отвір над ними."""
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


def sheet_part(group, name, verts, faces, t, mat='paint', bev=0.0008):
    """Гнутий лист: серединна поверхня → товщина t (Solidify) + фаски по кромках (Bevel)."""
    me = bpy.data.meshes.new(name + "_mid")
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    tmp = bpy.data.objects.new(name + "_tmp", me)
    COLL.objects.link(tmp)
    so = tmp.modifiers.new("solid", 'SOLIDIFY')
    so.thickness, so.offset, so.use_even_offset = t, 0.0, True
    bv = tmp.modifiers.new("bevel", 'BEVEL')
    bv.width, bv.segments, bv.limit_method, bv.angle_limit = bev, 2, 'ANGLE', math.radians(40.0)
    out = evaluated_mesh(tmp)
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(me)
    out.name = name
    finalize_mesh(out, 35.0)
    return add_part(group, name, out, [mat])


def build_deck():
    """Піддон-палуба — окрема деталь, що кладеться на корпус зверху.
    Один лист 4 мм: палуба, бортики загнуті вгору (R 6 мм), кормовий відгин униз (фартух), у кутах —
    розвантажувальні вирізи. Знизу приварені ребра звису, кронштейни між колесами і шпильки M8:
    шпильки проходять крізь фланці корпусу, гайки затягуються знизу з колісних ніш — палуба гладка."""
    p = P
    t, ri = p['deck_t'], p['bend_r']
    ro, rm = ri + t, ri + t / 2
    sx, zt = p['side_x'], p['deck_z']
    zb, zm = zt - t, zt - t / 2
    xr = sx - ro                      # вісь бічного згину
    yr = p['tub_y0'] + ro             # вісь кормового згину
    yf = p['deck_y1'] - 0.006         # передня кромка: зазор 2 мм до смужки носа
    zf = zb + ro                      # низ прямої частини бортика (кінець згину)
    g = 0.003                         # розвантажувальні вирізи в кутах між згинами
    n = 6

    # --- лист: серединна поверхня (палуба + бічні згини з початком бортиків + кормовий згин із фартухом)
    verts, faces, idx = [], [], {}

    def v(x, y, z):
        k = (round(x, 6), round(y, 6), round(z, 6))
        if k not in idx:
            idx[k] = len(verts)
            verts.append(k)
        return idx[k]
    faces.append([v(-xr, yr, zm), v(-xr + g, yr, zm), v(xr - g, yr, zm), v(xr, yr, zm),
                  v(xr, yr + g, zm), v(xr, yf, zm), v(-xr, yf, zm), v(-xr, yr + g, zm)])
    side = [(xr + rm * math.cos(a), zf + rm * math.sin(a))
            for a in (math.radians(-90 + 90 * k / n) for k in range(n + 1))]
    side.append((xr + rm, zf + 0.003))          # заходить у бортик на 3 мм (стик схований)
    for s in (-1, 1):
        for (x0, z0), (x1, z1) in zip(side, side[1:]):
            faces.append([v(s * x0, yr + g, z0), v(s * x0, yf, z0), v(s * x1, yf, z1), v(s * x1, yr + g, z1)])
    zr = zt - ro
    rear = [(yr + rm * math.cos(b), zr + rm * math.sin(b))
            for b in (math.radians(90 + 90 * k / n) for k in range(n + 1))]
    rear.append((yr - rm, zt - 0.100))          # фартух 100 мм
    for (y0, z0), (y1, z1) in zip(rear, rear[1:]):
        faces.append([v(-xr + g, y0, z0), v(xr - g, y0, z0), v(xr - g, y1, z1), v(-xr + g, y1, z1)])
    sheet_part('Deck', "Deck_Sheet", verts, faces, t)

    # --- бортики (пряма частина відгину) з прорізами, профіль у площині YZ
    wt, z1 = p['wall_t'], p['wall_z1']
    y0, y0t, y1t, y1c, z1c, y1 = (p['wall_y0'], p['wall_y0_top'], p['wall_y1_top'], p['wall_y1_ch'],
                                  p['wall_z1_ch'], p['wall_y1'])
    outline = [(y0, zf), (y1, zf), (y1, z1c - 0.012), (y1c, z1c), (y1t, z1), (y0t, z1), (y0, p['wall_z0_ch'])]
    outline = round_poly(outline, {3: 0.01, 4: 0.012, 5: 0.012}, 3)
    holes = wall_holes(y0t + 0.075, y1t - 0.05, (zt + z1) / 2)
    for (yy, zz, ang) in ((y0 + 0.075, p['wall_z0_ch'] + 0.026, 33), (y1c - 0.028, z1c - 0.040, -33)):
        sl = rrect(0, 0, 0.060, 0.020, 0.0095, 4)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        holes.append([(yy + x * ca - y * sa, zz + x * sa + y * ca) for (x, y) in sl])
    for s in (-1, 1):
        x0 = sx - wt if s > 0 else -sx
        plate('Deck', "Deck_Wall_" + ("L" if s < 0 else "R"), outline, holes, t=wt,
              M=frame((x0, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.0012)

    # --- знизу: ребра звису над колесами (вищі біля корпусу, де найбільший згинальний момент; над шиною ≥ 5 см),
    #     кронштейни між колесами (кріпляться до борту корпусу двома болтами), шпильки з гайками
    hx = p['hull_x']
    xh = hx + 0.035                   # кромка фланця корпусу
    xs = hx + 0.006                   # зовнішня площина накладки кронштейна
    gy = -0.092                       # проміжок між колесами
    rib = [(xh + 0.002, zb), (xr - 0.002, zb), (xr - 0.002, zb - 0.015), (xh + 0.002, zb - 0.040)]
    gus = [(xs, 0.700), (xs, zb - 0.008), (xh + 0.002, zb - 0.008), (xh + 0.002, zb), (xr - 0.002, zb),
           (xr - 0.002, zb - 0.018), (xs + 0.045, 0.700)]
    tab = round_poly([(gy - 0.035, 0.705), (gy + 0.035, 0.705), (gy + 0.035, 0.845), (gy - 0.035, 0.845)],
                     {0: 0.006, 1: 0.006, 2: 0.006, 3: 0.006}, 2)
    bolts, nuts = [], []
    wl = []
    bm = bmesh.new()
    for s in (-1, 1):
        for yy in (-0.755, -0.455, 0.145, 0.445):          # над ребрами корпусу — одна лінія навантаження
            plate('Deck', "Deck_Rib", rib, (), t=0.005,
                  M=frame((0, yy + s * 0.0025, 0), (s, 0, 0), (0, 0, 1)))
            wl += [((s * (xh + 0.002), yy + d, zb), (s * (xr - 0.002), yy + d, zb)) for d in (-0.0025, 0.0025)]
        wl += [((s * (xh + 0.002), gy + d, zb), (s * (xr - 0.002), gy + d, zb)) for d in (-0.003, 0.003)]
        wl += [((s * xs, gy + d, 0.705), (s * xs, gy + d, 0.845)) for d in (-0.003, 0.003)]
        plate('Deck', "Deck_Bracket", gus, [circle(0.470, 0.805, 0.024, 20)], t=0.006,
              M=frame((0, gy + s * 0.003, 0), (s, 0, 0), (0, 0, 1)))
        plate('Deck', "Deck_BracketTab", tab, (), t=0.006,
              M=frame((hx if s > 0 else -xs, 0, 0), (0, 1, 0), (0, 0, 1)))
        bolts += [(Vector((s * xs, gy + d, 0.775)), Vector((s, 0, 0))) for d in (-0.020, 0.020)]
        for yy in (-0.800, -0.500, -0.205, 0.100, 0.400):  # поруч із ребрами корпусу
            q = Vector((s * (hx + 0.020), yy, zb - 0.006))
            nuts.append((q, Vector((0, 0, -1))))
            bm_cyl(bm, q, q - Vector((0, 0, 0.013)), 0.004, 12)
    fasteners('Deck', "Deck_BracketBolts", bolts)
    # петлі для підйому краном: 4 вушка з листа 10 мм на верху бортиків, симетрично відносно центру ваги
    # (y ≈ −0,12); навантаження: бортик → палуба → 10 шпильок M8 → фланці корпусу
    zw = p['wall_z1']
    lug = round_poly([(-0.045, -0.010), (0.045, -0.010), (0.045, 0.030), (0.020, 0.055), (-0.020, 0.055),
                      (-0.045, 0.030)], {2: 0.015, 3: 0.012, 4: 0.012, 5: 0.015}, 4)
    for sg in (-1, 1):
        xl = sg * (sx - wt / 2) - 0.005
        for yl in (0.450, -0.690):
            plate('Deck', "Deck_LiftLug", [(yl + a, zw + b) for a, b in lug], [circle(yl, zw + 0.028, 0.015, 20)],
                  t=0.010, M=frame((xl, 0, 0), (0, 1, 0), (0, 0, 1)), bev=0.0015)
            wl += [((xf, yl - 0.045, zw - 0.010), (xf, yl + 0.045, zw - 0.010)) for xf in (sg * (sx - wt), sg * sx)]
    welds('Deck', "Deck_Welds", wl)
    fasteners('Deck', "Deck_Nuts", nuts, NUT_HEX, scale=0.75)
    bm_to_part('Deck', "Deck_Studs", bm, ['zinc'])


# =================================================================== корма
def build_rear():
    p = P
    y0 = p['tub_y0']
    # --- поличка під палубою і нижня кормова панель на задній стінці корпусу
    hy0 = p['hull_y0']
    box('Rear', "Rear_Shelf", -0.380, 0.380, hy0 - 0.004, y0 + 0.002, p['rear_z1'], p['rear_z1'] + 0.006,
        bev=0.0015)
    rw, r0, r1 = p['rear_hw'], p['rear_z0'], p['rear_z1']
    panel = chamfer_poly([(-rw, r0), (rw, r0), (rw, r1), (-rw, r1)], {0: 0.035, 1: 0.035})
    M = frame((0, hy0, 0), (1, 0, 0), (0, 0, 1))
    plate('Rear', "Rear_Panel", panel, (), t=0.005, M=M)
    bolts = [(Vector((xx, hy0 - 0.005, zz)), Vector((0, -1, 0)))
             for xx in (-rw + 0.03, rw - 0.03) for zz in (r0 + 0.045, r1 - 0.03)]
    bolts += [(Vector((xx, hy0 - 0.005, r0 + 0.030)), Vector((0, -1, 0))) for xx in (-0.10, 0.10)]
    fasteners('Rear', "Rear_Bolts", bolts)

    # --- сервісна панель під поличкою (поличка — козирок від дощу): заряджання, вимикач батареї, аварійна кнопка;
    # усе, що виступає, — не далі за задній край палуби (y −0,931), щоб заднім ходом першою била палуба
    yf, zc = hy0 - 0.005, (r0 + r1) / 2            # зовнішня площина панелі, середина по висоті
    back = Vector((0, -1, 0))
    to_back = back.to_track_quat('Z', 'Y').to_matrix().to_4x4()

    def cyl_part(name, x, z, d0, d1, r, mat, segs=24):
        bm = bmesh.new()
        bm_cyl(bm, Vector((x, yf - d0, z)), Vector((x, yf - d1, z)), r, segs)
        bm_to_part('Rear', name, bm, [mat], angle=40.0)
    # роз'єм заряджання з кришкою на завісі
    xc = -0.190
    box('Rear', "Svc_ChargeFlange", xc - 0.0425, xc + 0.0425, yf - 0.005, yf, zc - 0.0425, zc + 0.0425, bev=0.003, segs=1)
    cyl_part("Svc_ChargeSocket", xc, zc, 0.005, 0.024, 0.030, 'dark')
    cyl_part("Svc_ChargeCap", xc, zc, 0.024, 0.034, 0.034, 'dark')
    box('Rear', "Svc_ChargeHinge", xc - 0.012, xc + 0.012, yf - 0.034, yf - 0.005, zc + 0.030, zc + 0.040,
        mat='dark', bev=0.002, segs=1)
    fasteners('Rear', "Svc_ChargeScrews", [(Vector((xc + dx, yf - 0.005, zc + dz)), back)
                                           for dx in (-0.031, 0.031) for dz in (-0.031, 0.031)], scale=0.45)
    # головний вимикач батареї: поворотна Т-подібна ручка
    box('Rear', "Svc_SwitchBase", -0.032, 0.032, yf - 0.006, yf, zc - 0.038, zc + 0.038, bev=0.003, segs=1)
    cyl_part("Svc_SwitchBoss", 0.0, zc, 0.006, 0.018, 0.018, 'dark')
    box('Rear', "Svc_SwitchHandle", -0.036, 0.036, yf - 0.034, yf - 0.018, zc - 0.007, zc + 0.007,
        mat='dark', bev=0.003, segs=1)
    # аварійна кнопка «стоп»: червоний «грибок» на жовтому кільці, захисні щоки від гілок
    xe = 0.190
    cyl_part("Svc_EStopRing", xe, zc, 0.000, 0.003, 0.042, 'yellow', 32)
    cyl_part("Svc_EStopBody", xe, zc, 0.003, 0.018, 0.020, 'dark')
    bm = bmesh.new()
    bm_lathe(bm, [(0.0, 0.0), (0.024, 0.0), (0.024, 0.005), (0.020, 0.011), (0.012, 0.015), (0.0, 0.016)], 28,
             Matrix.Translation((xe, yf - 0.018, zc)) @ to_back)
    bm_to_part('Rear', "Svc_EStopHead", bm, ['red'], angle=40.0)
    for sg in (-1, 1):
        x0, x1 = sorted((xe + sg * 0.045, xe + sg * 0.050))   # зовні жовтого кільця
        box('Rear', "Svc_EStopGuard", x0, x1, yf - 0.036, yf, zc - 0.040, zc + 0.040, bev=0.002, segs=1)
    # задні ліхтарі по краях панелі між її болтами, під поличкою: угорі габарит/стоп (червоний), унизу задній
    # хід (білий); кабель — крізь панель і задню стінку корпусу просто за ліхтарем, ззовні дротів немає
    for sg in ((-1, 1) if p['rear_lights'] else ()):    # власник: поки прибрати (v15)
        xl = sg * 0.285
        box('Rear', "Rear_LampBody", xl - 0.026, xl + 0.026, yf - 0.024, yf, 0.522, 0.628, mat='dark', bev=0.004, segs=2)
        box('Rear', "Rear_LampRed", xl - 0.020, xl + 0.020, yf - 0.0262, yf - 0.020, 0.579, 0.621, mat='lens_red',
            bev=0.002, segs=1)
        box('Rear', "Rear_LampWhite", xl - 0.020, xl + 0.020, yf - 0.0262, yf - 0.020, 0.529, 0.571, mat='lens',
            bev=0.002, segs=1)


# =================================================================== ніс
def nose_geometry():
    """Ніс: плаский лобовий лист (верхня кромка над палубою → «підборіддя»), коробка позаду нього
    з вертикальними боковинами в лінію з бортами корпусу, нижній лист назад до днища."""
    p = P
    zt = p['deck_z']
    top = Vector((p['deck_y1'], p['nose_up_z']))      # зовнішня верхня кромка лобового листа (y, z)
    chin = Vector((p['chin_y'], p['chin_z']))
    d = chin - top
    L = d.length
    dn = d.normalized()
    nrm = Vector((0, -dn.y, dn.x))                    # зовнішня нормаль листа (вперед-угору)
    if nrm.y < 0:
        nrm = -nrm
    dn3 = Vector((0.0, dn.x, dn.y))
    t = 0.005                                         # товщина лобового листа

    def on_plate(s, x):
        """Точка на зовнішній поверхні лобового листа: s — від верхньої кромки вниз, x — поперек."""
        q = top + dn * s
        return Vector((x, q.x, q.y))

    def inner(s, x):
        return on_plate(s, x) - nrm * t
    W = p['hull_x'] - 0.0005                          # боковини коробки (на 0,5 мм усередині кромки листа)
    yr = p['hull_y1'] - 0.02                          # задня грань носа (стик із корпусом)
    zc = zt + 0.010                                   # верх: над палубою зрізається (deck_clear)
    pts = []
    for sg in (-1, 1):
        pts += [inner(0.0, sg * W), inner(L, sg * W),
                Vector((sg * W, p['nose_bot_y'], p['nose_bot_z'])),
                Vector((sg * W, yr, p['nose_bot_z'])), Vector((sg * W, yr, zc))]
    return dict(pts=pts, on_plate=on_plate, inner=inner, L=L, n=nrm, dn=dn3, t=t,
                ytop=p['deck_y1'] - 0.004)


def build_nose():
    """Ніс — зварна коробка між передніми колесами: один плаский лобовий лист від верхньої кромки над
    палубою до «підборіддя» з крилами над колесами (у тій самій площині, з відбортовкою по косих кромках),
    вертикальні боковини в лінію з бортами корпусу, нижній лист назад до днища."""
    p = P
    g = nose_geometry()
    # місце під передню кромку піддона: верх носа позаду ytop опускається до низу палуби (піддон лягає на ніс)
    bm = bmesh.new()
    bm_box(bm, -0.75, 0.75, 0.50, g['ytop'] - 0.0005, p['deck_z'] - p['deck_t'], 1.0)
    me = bpy.data.meshes.new("deck_clear")
    bm.to_mesh(me)
    bm.free()
    convex_solid('Nose', "Nose_Box", g['pts'], bev=0.006, segs=2, cutters=[me])
    # лобовий лист: шестикутник — крила від кутів бортиків до ширини носа, далі прямо до «підборіддя»
    xo, wn, sw, L, t = p['side_x'], p['hull_x'], p['nose_wing_s'], g['L'], g['t']
    outline = [(-xo, 0.0), (xo, 0.0), (wn, sw), (wn, L), (-wn, L), (-wn, sw)]
    M = frame(g['inner'](0.0, 0.0), (1, 0, 0), g['dn'])          # локальна z = зовнішня нормаль листа
    plate('Nose', "Nose_Front", outline, (), t=t, M=M, bev=0.0012)
    # відбортовка 25 мм по косих кромках крил: кромка жорстка, щілини над колесом немає;
    # задній кінець підрізаний вертикально, щоб не заходити під піддон
    down = -g['n']
    t_l, b0, b1 = 0.005, t, t + 0.025
    y_min = g['ytop'] + 0.001
    for s in (-1, 1):
        R = g['on_plate'](0.0, s * xo)
        F = g['on_plate'](sw, s * wn)
        ue = F - R
        Le = ue.length
        ue.normalize()
        w = ue.cross(down).normalized()
        if w.x * s > 0:
            w = -w                                    # товщина — всередину

        def at(a, b):
            return R + ue * a + down * b

        def a_min(b):
            return max(0.0, (y_min - R.y - b * down.y) / ue.y)
        quad = [at(a_min(b0), b0), at(Le, b0), at(Le, b1), at(a_min(b1), b1)]
        bm = bmesh.new()
        vo = [bm.verts.new(q) for q in quad]
        vi = [bm.verts.new(q + w * t_l) for q in quad]
        bm.faces.new(vo)
        bm.faces.new(list(reversed(vi)))
        for k in range(4):
            k1 = (k + 1) % 4
            bm.faces.new([vo[k], vi[k], vi[k1], vo[k1]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.001, segments=1, affect='EDGES', clamp_overlap=True)
        bm_to_part('Nose', "Nose_Fender", bm, ['paint'])
    # вертикальна смужка між передньою кромкою палуби і верхньою кромкою лобового листа
    box('Nose', "Nose_Lip", -xo, xo, p['deck_y1'] - 0.004, p['deck_y1'], p['deck_z'] - 0.02, p['nose_up_z'],
        bev=0.0012, segs=1)
    # шви: лобовий лист — боковини (кутове з'єднання, під крилами — таврове) і лобовий лист — нижній лист
    inner = g['inner']
    welds('Nose', "Nose_Welds", [(inner(0.030, s * wn), inner(L, s * wn)) for s in (-1, 1)] +
          [(inner(L, -wn), inner(L, wn))])


# =================================================================== накладна захисна плита
def guard_outline():
    """Контур плити в координатах лобового листа (x, s): угорі на всю ширину палуби, боки вертикальні
    до висоти guard_side_z, далі скоси до ±guard_bot_hw на рівні «підборіддя»."""
    p = P
    g = nose_geometry()
    s_side = (p['nose_up_z'] - p['guard_side_z']) / -g['dn'].z
    xo, xb = p['side_x'], p['guard_bot_hw']
    return [(-xo, 0.0), (xo, 0.0), (xo, s_side), (xb, g['L']), (-xb, g['L']), (-xo, s_side)]


def build_front_guard():
    """Накладна захисна плита 8 мм паралельно лобовому листу на дистанційних втулках (проміжок 25 мм —
    рознесений захист від уламків), 6 болтів крізь лобовий лист носа; крайні частини плити (поза носом)
    тримають горизонтальні косинки до боковин носа, прикручені двома болтами (плита знімна)."""
    p = P
    g = nose_geometry()
    on, n, dn = g['on_plate'], g['n'], g['dn']
    gap, t = p['guard_gap'], p['guard_t']
    plate('FrontGuard', "Guard_Plate", guard_outline(), (), t=t, M=frame(on(0.0, 0.0) + n * gap, (1, 0, 0), dn),
          bev=0.002)
    pts = [(x, s) for x in (-0.280, 0.0, 0.280) for s in (0.080, 0.400)]
    bm = bmesh.new()
    for x, s in pts:
        q = on(s, x)
        bm_cyl(bm, q, q + n * gap, 0.016, 16)
    bm_to_part('FrontGuard', "Guard_Spacers", bm, ['paint'])
    fasteners('FrontGuard', "Guard_Bolts", [(on(s, x) + n * (gap + t), n) for x, s in pts], scale=1.15)
    # бокові кронштейни: косинка в горизонтальній площині від задньої поверхні плити до боковини носа
    zg, tb, depth = p['guard_bracket_z'], 0.008, 0.150
    s_b = (p['nose_up_z'] + n.z * gap - zg) / -dn.z
    yb = (on(s_b, 0.0) + n * gap).y                   # задня поверхня плити на висоті zg
    xn = p['hull_x']
    bolts = []
    for sg in (-1, 1):
        tri = [(xn, yb), (p['side_x'] - 0.030, yb), (xn, yb - depth)]
        plate('FrontGuard', "Guard_Bracket", tri, (), t=tb, bev=0.0015,
              M=frame((0, 0, zg - sg * tb / 2), (sg, 0, 0), (0, 1, 0)))
        tab = [(yb - depth, zg - 0.045), (yb - 0.020, zg - 0.045), (yb - 0.020, zg + 0.045), (yb - depth, zg + 0.045)]
        plate('FrontGuard', "Guard_BracketTab", tab, (), t=0.006, bev=0.0012,
              M=frame((xn if sg > 0 else -xn - 0.006, 0, 0), (0, 1, 0), (0, 0, 1)))
        ym = yb - depth / 2 - 0.010
        bolts += [(Vector((sg * (xn + 0.006), ym, zg + dz)), Vector((sg, 0, 0))) for dz in (-0.026, 0.026)]
    fasteners('FrontGuard', "Guard_BracketBolts", bolts)
    # шви косинок: до плити і до накладки (зверху й знизу косинки)
    wl = []
    for sg in (-1, 1):
        for dz in (-tb / 2, tb / 2):
            wl.append(((sg * xn, yb, zg + dz), (sg * (p['side_x'] - 0.030), yb, zg + dz)))
            wl.append(((sg * (xn + 0.006), yb - depth + 0.006, zg + dz), (sg * (xn + 0.006), yb - 0.020, zg + dz)))

    if p['front_lights']:                             # власник: фари поки прибрати (v14)
        # --- фари: у кожному верхньому куті плити (поза носом) — зварний сталевий корпус-клин: задня грань лягає
        #     на похилу плиту, фронт вертикальний (вісь світла горизонтальна); козирок і щоки виступають на 30 мм
        #     перед склом. Зовні — світлодіодна фара, ближче до центру — ІЧ-прожектор для нічних камер
        def G(s, x):
            return on(s, x) + n * (gap + t)                # зовнішня поверхня плити
        q0 = G(0.0, 0.0)
        k = dn.y / -dn.z                                   # зсув поверхні вперед на 1 м зниження

        def yg(z):
            return q0.y + (q0.z - z) * k
        zl0, zl1, dep, vis, tv, zc = 0.745, 0.835, 0.070, 0.030, 0.005, 0.790
        bm_d, bm_l, bm_ir, bm_z = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
        glands, glands_nose = [], []
        for sg in (-1, 1):
            x0, x1 = sorted((sg * 0.385, sg * 0.595))
            yf = yg(zl0) + dep
            back = [Vector((x, yg(z), z)) - n * 0.002 for x in (x0, x1) for z in (zl0, zl1)]
            convex_solid('FrontGuard', "Light_Housing", back + [Vector((x, yf, z)) for x in (x0, x1) for z in (zl0, zl1)],
                         bev=0.003, segs=2)
            box('FrontGuard', "Light_Visor", x0, x1, yg(zl1 + tv) - 0.003, yf + vis, zl1, zl1 + tv, bev=0.0015, segs=1)
            for xa, xb in ((x0, x0 + tv), (x1 - tv, x1)):
                box('FrontGuard', "Light_Cheek", xa, xb, yf - 0.005, yf + vis, zl0, zl1, bev=0.0015, segs=1)
            wl += [((x0, yg(zl1 + tv), zl1 + tv), (x1, yg(zl1 + tv), zl1 + tv)), ((x0, yg(zl0), zl0), (x1, yg(zl0), zl0))]
            wl += [((x, yg(zl0), zl0), (x, yg(zl1), zl1)) for x in (x0, x1)]
            # світлодіодна фара 110 × 55 мм: рамка, скло, три лінзи-рефлектори
            xh_ = sg * 0.532
            bm_box(bm_d, xh_ - 0.057, xh_ + 0.057, yf - 0.002, yf + 0.012, zc - 0.031, zc + 0.031, 0.004, 1)
            bm_box(bm_l, xh_ - 0.050, xh_ + 0.050, yf + 0.010, yf + 0.0135, zc - 0.024, zc + 0.024, 0.002, 1)
            for dx in (-0.033, 0.0, 0.033):
                bm_cyl(bm_z, Vector((xh_ + dx, yf + 0.0130, zc)), Vector((xh_ + dx, yf + 0.0145, zc)), 0.013, 20)
            # ІЧ-прожектор Ø56
            xi = sg * 0.425
            bm_cyl(bm_d, Vector((xi, yf - 0.002, zc)), Vector((xi, yf + 0.014, zc)), 0.034, 28)
            bm_cyl(bm_ir, Vector((xi, yf + 0.012, zc)), Vector((xi, yf + 0.0155, zc)), 0.028, 28)
            # кабель: гермоввід на задній поверхні плити → металорукав Ø16 над колесом → гермоввід у боковині носа
            sc = (q0.z - zc) / -dn.z
            gb = on(sc, sg * 0.490) + n * gap               # задня поверхня плити за фарою
            glands.append((gb, -n))
            p1 = gb - n * 0.040
            yn = (g['inner'](sc, 0.0)).y - 0.085          # ввід у боковину — вище й далі від накладки косинки
            zn = p1.z + 0.015
            p3 = Vector((sg * (xn + 0.018), yn, zn))
            tube('FrontGuard', "Light_Conduit", [gb - n * 0.012, p1, Vector((sg * 0.398, p1.y - 0.010, p1.z)), p3],
                 0.008, bend=0.025, res=2)
            glands_nose.append((Vector((sg * xn, yn, zn)), Vector((sg, 0, 0))))
        bm_to_part('FrontGuard', "Light_Bezels", bm_d, ['dark'], angle=40.0)
        bm_to_part('FrontGuard', "Light_LensLED", bm_l, ['lens'], angle=40.0)
        bm_to_part('FrontGuard', "Light_LensIR", bm_ir, ['lens_ir'], angle=40.0)
        bm_to_part('FrontGuard', "Light_Reflectors", bm_z, ['zinc'], angle=40.0)
        fasteners('FrontGuard', "Light_Glands", glands, NUT_HEX, scale=0.9)
        fasteners('Nose', "Nose_CableGlands", glands_nose, NUT_HEX, scale=0.9)
    welds('FrontGuard', "Guard_Welds", wl)


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
    bm_box(bm, -p['side_x'], p['side_x'], p['tub_y0'] - 0.005, p['wall_y1'], p['deck_z'] - 0.035, p['wall_z1'])
    add("UCX_Zmiy_Logistic_00", bm)
    bm = bmesh.new()
    bm_box(bm, -p['hull_x'], p['hull_x'], p['hull_y0'], p['hull_y1'], p['hull_z0'], p['deck_z'] - 0.035)
    add("UCX_Zmiy_Logistic_01", bm)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in nose_geometry()['pts']]
    bmesh.ops.convex_hull(bm, input=vs)
    add("UCX_Zmiy_Logistic_02", bm)
    g = nose_geometry()
    bm = bmesh.new()                                     # накладна плита спереду (додається в кінці списку)
    gv = [g['on_plate'](sv, xv) + g['n'] * (p['guard_gap'] + dz) for xv, sv in guard_outline()
          for dz in (0.0, p['guard_t'])]
    vs = [bm.verts.new(v) for v in gv]
    bmesh.ops.convex_hull(bm, input=vs)
    guard_bm = bm
    k = 3
    for sx in (-1, 1):
        for y in (p['axle_f'], p['axle_r']):
            bm = bmesh.new()
            x = sx * p['wheel_x']
            bm_cyl(bm, (x - p['tire_w'] / 2, y, p['wheel_z']), (x + p['tire_w'] / 2, y, p['wheel_z']), p['tire_r'], 12)
            add("UCX_Zmiy_Logistic_%02d" % k, bm)
            k += 1
    add("UCX_Zmiy_Logistic_%02d" % k, guard_bm)
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


RESERVED = ("Zmiy_Logistic", "Hull", "Nose", "Rear", "SkidPlate", "FrontGuard", "Deck", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR",
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
    build_deck()
    build_rear()
    build_nose()
    build_front_guard()

    # головні складові; півот кожної — на площині кріплення до корпусу
    p = P
    pivots = {
        'Hull': (0, 0, 0),
        'Nose': (0, p['hull_y1'] - 0.02, p['nose_bot_z']),             # стик із передом корпусу
        'Rear': (0, p['hull_y0'], p['rear_z0']),                         # задня стінка корпусу
        'SkidPlate': (0, (p['hull_y0'] + p['hull_y1']) / 2, p['hull_z0']),  # дно корпусу
        'Deck': (0, 0, p['deck_z'] - p['deck_t']),                       # верх фланців корпусу
        'FrontGuard': tuple(nose_geometry()['on_plate'](0.25, 0.0) + nose_geometry()['n'] * p['guard_gap']),
    }
    for key, pv in pivots.items():
        join_group(key, PARTS.pop(key), pivot=pv).parent = root
    build_wheels(root)
    build_modules(root)
    build_collision(root)
    return root


if __name__ == "__main__":
    build_all()
    print("Zmiy_Logistic: готово")
