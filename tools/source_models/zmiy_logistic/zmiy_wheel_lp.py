# -*- coding: utf-8 -*-
"""Легке (low-poly) колесо «Змія» з власною UV-розгорткою + запікання текстур з детального колеса.

    blender -b --factory-startup --python zmiy_wheel_lp.py -- bake [2048]
        → textures/Zmiy_Wheel_{BaseColor,Normal,ORM,AO,Roughness,Metallic}.png  (чисті, без зносу)
          textures/Zmiy_Wheel_Mask_{ID,Edge}.png                               (маски для майбутнього зносу)

zmiy_build.build_wheels() бере звідси wheel_mesh() і wheel_material(): той самий меш на 4 колеса,
ліві — поворот на 180° навколо Z (не дзеркало: написи на боковині мають читатися).

Геометрія легкого колеса повторює детальне (zmiy_wheel_hp.py) — ті самі профілі й контури шашок:
каркас шини з захисним поясом над ободом, шашки протектора (прості контури з ухилом стінок), видима
поверхня обода із закраїнами, диск, маточина, ковпак, гайки й шпильки, вентиль зі скобою. Написи, кільця,
шви, різьба, заокруглення кромок, каменевикидачі, перемички, «вусики» — лише в карті нормалей.
UV будується в коді (детерміновано, без операторів Blender) і пакується полицями, без перекриттів.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import zmiy_wheel_hp as hp   # noqa: E402

TEX_DIR = os.path.join(HERE, "textures")
RUBBER, RIM, ZINC, DARK = hp.RUBBER, hp.RIM, hp.ZINC, hp.DARK
SEG_TYRE, SEG_RIM, SEG_DISC, SEG_SMALL = 48, 40, 32, 20
AX = Vector((1, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4()    # локальна Z → вісь колеса X
# параметри матеріалів (чисті, без зносу): колір sRGB, roughness, metallic
MATS = {RUBBER: ("#1C1C1C", 0.90, 0.0), RIM: ("#151515", 0.50, 0.0), ZINC: ("#8A8A85", 0.35, 1.0),
        DARK: ("#1E1F1C", 0.60, 0.0)}


# =================================================================== допоміжне
def simplify(pts, tol):
    """Дуглас—Пекер: лишає точки, де ламана відхиляється більше ніж на tol."""
    pts = [Vector(p) for p in pts]
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    L = ab.length
    best, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs(ab.x * (pts[i] - a).y - ab.y * (pts[i] - a).x) / L if L > 1e-12 else (pts[i] - a).length
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [a, b]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


class LP:
    """Накопичувач легкого мешу: вершини, грані з матеріалом, острів UV і UV кутів (у метрах острова)."""

    def __init__(self):
        self.v = []
        self.f = []                      # (індекси, матеріал, острів, [uv], частина)
        self.n_isl = 0

    def vert(self, p):
        self.v.append(Vector(p))
        return len(self.v) - 1

    def island(self):
        self.n_isl += 1
        return self.n_isl

    def face(self, idx, uvs, mat, isl, part, rev=False):
        idx, uvs = list(idx), list(uvs)
        if rev:
            idx, uvs = idx[::-1], uvs[::-1]
        self.f.append((tuple(idx), mat, isl, [Vector(u) for u in uvs], part))


def lathe(lp, prof, segs, M, mat, part, max_strip=0.32):
    """Тіло обертання профілю [(r, h)] навколо локальної Z (M — у світ). Обхід профілю: «зовні» праворуч
    (тоді грані дивляться назовні). UV: ділянки профілю, що торкаються осі, — плоска проєкція; решта —
    смуги (u = θ·r, v = довжина дуги), довгі смуги поділені на частини ≤ max_strip."""
    n = len(prof)
    ring = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        row = []
        for (r, h) in prof:
            if r < 1e-7:
                row.append(None)
            else:
                row.append(lp.vert(M @ Vector((r * math.cos(a), r * math.sin(a), h))))
        ring.append(row)
    axis = {i: lp.vert(M @ Vector((0.0, 0.0, h))) for i, (r, h) in enumerate(prof) if r < 1e-7}

    def V(k, i):
        return axis[i] if prof[i][0] < 1e-7 else ring[k % segs][i]
    # ділянки профілю: сегменти, що торкаються осі, — «кришки»; решта — смуги
    kinds = ['cap' if prof[i][0] < 1e-7 or prof[i + 1][0] < 1e-7 else 'strip' for i in range(n - 1)]
    runs = []
    for i, kd in enumerate(kinds):
        if runs and runs[-1][0][0] == kd and kd == 'strip':
            runs[-1].append((kd, i))
        else:
            runs.append([(kd, i)])
    for run in runs:
        kind = run[0][0]
        idxs = [i for _, i in run]
        if kind == 'cap':
            isl = lp.island()
            for i in idxs:
                for k in range(segs):
                    a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * (k + 1) / segs
                    quad = [(k, i), (k + 1, i), (k + 1, i + 1), (k, i + 1)]
                    uv = [(prof[ii][0] * math.cos(a), prof[ii][0] * math.sin(a))
                          for (kk, ii), a in zip(quad, (a0, a1, a1, a0))]
                    vi = [V(kk, ii) for kk, ii in quad]
                    keep = [j for j in range(4) if vi[j] not in vi[:j]]
                    lp.face([vi[j] for j in keep], [uv[j] for j in keep], mat, isl, part)
            continue
        arc = {idxs[0]: 0.0}
        for i in idxs:
            arc[i + 1] = arc[i] + (Vector(prof[i + 1]) - Vector(prof[i])).length
        rmax = max(prof[i][0] for i in idxs + [idxs[-1] + 1])
        parts = max(1, int(math.ceil(2 * math.pi * rmax / max_strip)))
        bounds = [round(segs * j / parts) for j in range(parts + 1)]
        for j in range(parts):
            isl = lp.island()
            k0 = bounds[j]
            for k in range(bounds[j], bounds[j + 1]):
                for i in idxs:
                    quad = [(k, i), (k + 1, i), (k + 1, i + 1), (k, i + 1)]
                    uv = [((kk - k0) * 2 * math.pi / segs * prof[ii][0], arc[ii]) for kk, ii in quad]
                    lp.face([V(kk, ii) for kk, ii in quad], uv, mat, isl, part)


def box(lp, c, ex, ey, ez, size, mat, part):
    """Брусок у базисі (ex, ey, ez); кожна грань — свій маленький острів."""
    s = [q / 2 for q in size]
    P = {}
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                P[i, j, k] = lp.vert(c + ex * (i * s[0]) + ey * (j * s[1]) + ez * (k * s[2]))
    quads = [((-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1)), ((1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1)),
             ((-1, -1, -1), (-1, -1, 1), (1, -1, 1), (1, -1, -1)), ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)),
             ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)), ((-1, -1, 1), (-1, 1, 1), (1, 1, 1), (1, -1, 1))]
    for q in quads:
        pts = [lp.v[P[t]] for t in q]
        e0 = (pts[1] - pts[0]).normalized()
        nrm = (pts[1] - pts[0]).cross(pts[3] - pts[0]).normalized()
        e1 = nrm.cross(e0)
        lp.face([P[t] for t in q], [((p - pts[0]).dot(e0), (p - pts[0]).dot(e1)) for p in pts], mat, lp.island(), part)


# =================================================================== частини
def tyre_carcass(lp):
    half = hp.carcass_half()                          # з захисним поясом і кільцями
    half = simplify([p for p in half if p.y >= 0.2035], 0.0010)   # нижче — схована під закраїною обода
    prof_wr = [Vector((-p.x, p.y)) for p in reversed(half)] + [Vector((p.x, p.y)) for p in half[1:]]
    lathe(lp, [(q.y, q.x) for q in prof_wr], SEG_TYRE, AX, RUBBER, 'tyre', max_strip=0.65)


def tread_blocks(lp):
    center, sh_long, sh_short = hp.tread_layout()

    def outline(poly, max_e):
        pts = [Vector(p) for p in hp.ccw([tuple(q) for q in poly])]
        out = []
        for i, q in enumerate(pts):
            nx = pts[(i + 1) % len(pts)]
            k = max(1, int((nx - q).length / max_e + 0.999))
            out += [q.lerp(nx, j / k) for j in range(k)]
        return out

    def block(poly, th0, hfun, inner_ring):
        base = outline(poly, 0.035)
        n = len(base)
        mit = []
        for i in range(n):
            a, p, b = base[i - 1], base[i], base[(i + 1) % n]
            e0, e1 = (p - a).normalized(), (b - p).normalized()
            n0, n1 = Vector((e0.y, -e0.x)), Vector((e1.y, -e1.x))
            m = n0 + n1
            m = n0 if m.length < 1e-6 else m.normalized()
            mit.append(m / max(0.4, m.dot(n0)))
        hs = [hfun(q.x) for q in base]
        top2 = [base[i] - mit[i] * (hp.DRAFT * hs[i]) for i in range(n)]
        vb = [lp.vert(hp.tread_point(q.x, q.y, -0.0015, th0)) for q in base]
        vt = [lp.vert(hp.tread_point(q.x, q.y, hs[i], th0)) for i, q in enumerate(top2)]
        # стінки: одна смуга навколо (u — периметр, v — висота)
        isl = lp.island()
        u = 0.0
        for i in range(n):
            j = (i + 1) % n
            L = (base[j] - base[i]).length
            hi, hj = hs[i] + 0.0015, hs[j] + 0.0015
            lp.face([vb[i], vb[j], vt[j], vt[i]], [(u, 0.0), (u + L, 0.0), (u + L, hj), (u, hi)], RUBBER, isl, 'tread', rev=True)
            u += L
        # верх: координати протектора (s уздовж кола, σ поперек) — без спотворень
        isl = lp.island()
        if inner_ring:
            c2 = sum(top2, Vector((0, 0))) / n
            mid2 = [q.lerp(c2, 0.5) for q in top2]
            vm = [lp.vert(hp.tread_point(q.x, q.y, hfun(q.x), th0)) for q in mid2]
            vc = lp.vert(hp.tread_point(c2.x, c2.y, hfun(c2.x), th0))
            for i in range(n):
                j = (i + 1) % n
                lp.face([vt[i], vt[j], vm[j], vm[i]], [(top2[i].y, top2[i].x), (top2[j].y, top2[j].x),
                                                     (mid2[j].y, mid2[j].x), (mid2[i].y, mid2[i].x)], RUBBER, isl, 'tread', rev=True)
                lp.face([vm[i], vm[j], vc], [(mid2[i].y, mid2[i].x), (mid2[j].y, mid2[j].x), (c2.y, c2.x)],
                        RUBBER, isl, 'tread', rev=True)
        else:
            for t in tessellate_polygon([[Vector((q.x, q.y, 0)) for q in top2]]):
                a, b, c = t
                # обхід як у контуру (проти годинникової в (σ, s)); rev=True розверне назовні
                pa, pb, pc = top2[a], top2[b], top2[c]
                if (pb - pa).x * (pc - pa).y - (pb - pa).y * (pc - pa).x < 0:
                    b, c = c, b
                lp.face([vt[a], vt[b], vt[c]], [(top2[x].y, top2[x].x) for x in (a, b, c)], RUBBER, isl, 'tread', rev=True)

    for k in range(hp.PITCHES):
        for side in (1, -1):
            th = 2 * math.pi * (k + (0.0 if side > 0 else 0.5)) / hp.PITCHES
            mapc = (lambda pts, sd=side: [(sd * uu, sd * ss) for uu, ss in pts])
            block(mapc(center), th, lambda uu: hp.h_center(abs(uu)), False)
            shp = sh_long if k % 2 == 0 else sh_short
            th_s = th + side * (0.25 * hp.P_ARC) / hp.R_CROWN
            block(mapc(shp), th_s, lambda uu: hp.h_shoulder(abs(uu)), True)


def rim_surface(lp):
    """Видима поверхня обода: бік до осі колеса + підгин закраїн (бік до шини схований шиною)."""
    half = [Vector(p) for p in hp.RIM_CL]
    full = half + [Vector((-p.x, p.y)) for p in reversed(half[:-1])]
    cl = hp.resample(hp.chaikin(full, 3), 0.0015)
    loop = hp.offset_open(cl, hp.RIM_T)              # a (бік до осі) + b у зворотному порядку
    m = len(cl)
    a, b_rev = loop[:m], loop[m:]
    # від кінчика підгину на внутрішньому боці (b) біля зовнішньої закраїни → a → до кінця підгину інший бік
    curl = [q for q in b_rev[-12:]]                  # кінець b_rev = початок b (зовнішня закраїна)
    curl_in = [q for q in b_rev[:12]]                # початок b_rev = кінець b (внутрішня закраїна)
    path = [q for q in curl if q.y > 0.2090] + a + [q for q in curl_in if q.y > 0.2090]
    path = simplify(path, 0.0010)
    lathe(lp, [(q.y, q.x) for q in path], SEG_RIM, AX, RIM, 'rim', max_strip=0.45)


def disc_hub_cap(lp):
    cl = hp.resample(hp.chaikin([Vector(p) for p in hp.DISC_CL], 2), 0.0012)
    loop = simplify(hp.offset_open(cl, hp.DISC_T) + [hp.offset_open(cl, hp.DISC_T)[0]], 0.0010)
    lathe(lp, [(q.y, q.x) for q in loop], SEG_DISC, AX, RIM, 'disc', max_strip=0.40)
    hub = [(0.0, -0.150), (0.048, -0.150), (0.048, 0.030), (0.078, 0.034), (0.078, 0.0555), (0.036, 0.0555),
           (0.036, 0.0640), (0.0, 0.0640)]
    lathe(lp, hub, SEG_SMALL, AX, RIM, 'hub')
    cap = [(0.0, 0.0620), (0.0460, 0.0620), (0.0460, 0.0660), (0.0365, 0.0660), (0.0320, 0.0820),
           (0.0280, 0.0880), (0.0, 0.0880)]
    lathe(lp, cap, SEG_SMALL, AX, RIM, 'cap')


def fasteners(lp):
    for k in range(5):
        a = math.radians(90 + 72 * k)
        c = Vector((hp.W_FACE, 0.0675 * math.sin(a), 0.0675 * math.cos(a)))
        M = Matrix.Translation(c) @ AX
        lathe(lp, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.003), (0.0, 0.003)], 12, M, ZINC, 'nut')
        R = 0.024 / math.sqrt(3)
        lathe(lp, [(0.0, 0.003), (R, 0.003), (R, 0.0148), (R * 0.86, 0.017), (0.0, 0.017)], 6,
              M @ Matrix.Rotation(math.radians(30), 4, 'Z'), ZINC, 'nut')
        lathe(lp, [(0.0, 0.017), (0.0080, 0.017), (0.0080, 0.0288), (0.0056, 0.030), (0.0, 0.030)], 8, M, ZINC, 'stud')
    lathe(lp, [(0.0, 0.0880), (0.0081, 0.0880), (0.0081, 0.0955), (0.0, 0.0955)], 6, AX, ZINC, 'plug')


def valve(lp):
    a = math.radians(205)
    rad = Vector((0, math.sin(a), math.cos(a)))
    tan = Vector((0, math.cos(a), -math.sin(a)))
    X = Vector((1, 0, 0))
    r_in = 0.1720 - hp.RIM_T / 2
    b0 = X * 0.047 + rad * r_in
    b1 = X * 0.047 + rad * (r_in - 0.010)
    Mr = Matrix.Translation(b0) @ (-rad).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    lathe(lp, [(0.0, -0.001), (0.0050, -0.001), (0.0050, 0.0105), (0.0, 0.0105)], 8, Mr, ZINC, 'valve')
    Mx = Matrix.Translation(b1 - X * 0.004) @ AX
    lathe(lp, [(0.0, 0.0), (0.0040, 0.0), (0.0040, 0.028), (0.0052, 0.028), (0.0052, 0.038), (0.0, 0.038)], 8, Mx,
          ZINC, 'valve')
    for sg in (-1, 1):
        box(lp, X * 0.069 + rad * (r_in - 0.0085) + tan * (sg * 0.016), rad, tan, X, (0.017, 0.003, 0.018), RIM, 'guard')
    box(lp, X * 0.069 + rad * (r_in - 0.0185), rad, tan, X, (0.003, 0.035, 0.018), RIM, 'guard')


# =================================================================== UV-пакування полицями
def pack_uv(lp, margin=0.006):
    """Острови → полиці в квадраті; масштаб однаковий для всіх (рівна щільність текселів)."""
    isl = {}
    for fi, f in enumerate(lp.f):
        isl.setdefault(f[2], []).append(fi)
    # острів, обійдений за годинниковою (дзеркальний), віддзеркалюємо по u — UV усюди «лицем»
    for i, fl in isl.items():
        area = 0.0
        for fi in fl:
            uv = lp.f[fi][3]
            area += sum(uv[j].x * uv[(j + 1) % len(uv)].y - uv[(j + 1) % len(uv)].x * uv[j].y for j in range(len(uv)))
        if area < 0:
            for fi in fl:
                idx, mat, ii, uv, part = lp.f[fi]
                lp.f[fi] = (idx, mat, ii, [Vector((-q.x, q.y)) for q in uv], part)
    boxes = []
    for i, fl in isl.items():
        pts = [p for fi in fl for p in lp.f[fi][3]]
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
        y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        rot = (y1 - y0) > (x1 - x0)                   # довгі острови — горизонтально (поворот на 90°)
        w, h = (y1 - y0, x1 - x0) if rot else (x1 - x0, y1 - y0)
        boxes.append((i, x0, x1, y0, y1, w, h, rot))
    boxes.sort(key=lambda b: (-round(b[6], 6), -round(b[5], 6), b[0]))
    area = sum((b[5] + margin) * (b[6] + margin) for b in boxes)
    side = math.sqrt(area) * 1.02
    while True:
        x = y = row_h = 0.0
        place = {}
        ok = True
        for b in boxes:
            w, h = b[5] + margin, b[6] + margin
            if w > side:
                ok = False
                break
            if x + w > side:
                x, y, row_h = 0.0, y + row_h, 0.0
            place[b[0]] = (x + margin / 2, y + margin / 2)
            x += w
            row_h = max(row_h, h)
        if ok and y + row_h <= side:
            break
        side *= 1.015
    info = {b[0]: b for b in boxes}
    for fi, (idx, mat, i, uv, part) in enumerate(lp.f):
        _, x0, x1, y0, y1, w, h, rot = info[i]
        px, py = place[i]
        new = []
        for p in uv:
            lx, ly = (y1 - p.y, p.x - x0) if rot else (p.x - x0, p.y - y0)
            new.append(Vector(((px + lx) / side, (py + ly) / side)))
        lp.f[fi] = (idx, mat, i, new, part)
    return side


# =================================================================== меш і матеріал
def build_low():
    lp = LP()
    tyre_carcass(lp)
    tread_blocks(lp)
    rim_surface(lp)
    disc_hub_cap(lp)
    fasteners(lp)
    valve(lp)
    side = pack_uv(lp)
    return lp, side


def wheel_mesh(name="Zmiy_Wheel", mats=None):
    """Легкий меш колеса з UV (UVMap) і слотами матеріалів [гума, обід, цинк, пластик]."""
    lp, side = build_low()
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in lp.v]
    uvl = bm.loops.layers.uv.new("UVMap")
    for idx, mat, _, uv, _ in lp.f:
        try:
            f = bm.faces.new([vs[i] for i in idx])
        except ValueError:
            continue
        f.material_index = mat
        for loop, t in zip(f.loops, uv):
            loop[uvl].uv = t
    # острови-тіла (закриті) — нормалі за bmesh; відкриті (каркас, обід) уже зорієнтовані обходом профілю
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    try:
        me.set_sharp_from_angle(angle=math.radians(40))
    except AttributeError:
        pass
    if mats:
        for m in mats:
            me.materials.append(m)
    me["uv_side_m"] = side
    return me


def textures_ready():
    return all(os.path.exists(os.path.join(TEX_DIR, "Zmiy_Wheel_%s.png" % k)) for k in ("BaseColor", "ORM", "Normal"))


def wheel_material():
    """PBR-матеріал колеса з запечених текстур (BaseColor sRGB, ORM, Normal OpenGL)."""
    m = bpy.data.materials.get("Zmiy_Wheel") or bpy.data.materials.new("Zmiy_Wheel")
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])

    def tex(kind, non_color):
        img = bpy.data.images.load(os.path.join(TEX_DIR, "Zmiy_Wheel_%s.png" % kind), check_existing=True)
        img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = img
        return n
    tb = tex("BaseColor", False)
    nt.links.new(tb.outputs['Color'], bsdf.inputs['Base Color'])
    to = tex("ORM", True)
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(to.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[1], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs[2], bsdf.inputs['Metallic'])
    tn = tex("Normal", True)
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", 'ShaderNodeTree')
        try:
            g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
        except AttributeError:
            g.inputs.new('NodeSocketFloat', "Occlusion")
    grp = nt.nodes.new('ShaderNodeGroup')
    grp.node_tree = g
    nt.links.new(sep.outputs[0], grp.inputs[0])
    return m


# =================================================================== запікання
def _srgb_lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def _emit(name, build):
    m = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(build(nt), em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def bake(res=2048):
    import numpy as np
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    hp.zb.MAT.clear()
    for k, v in hp.zb.MAT_DEF.items():
        hp.zb.MAT[k] = hp.zb.make_material(*v)
    mats = [hp.zb.MAT[k] for k in ('rubber', 'rim', 'zinc', 'dark')]
    hi = bpy.data.objects.new("Wheel_High", hp.build_wheel_high())
    lo = bpy.data.objects.new("Wheel_Low", wheel_mesh("Zmiy_Wheel", mats))
    for o in (hi, lo):
        sc.collection.objects.link(o)
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = False
    bk = sc.render.bake
    bk.use_selected_to_active = True
    bk.cage_extrusion = 0.006
    bk.max_ray_distance = 0.015
    bk.margin = 8
    # ціль запікання: один матеріал на легкому колесі з активним вузлом зображення
    tgt = bpy.data.materials.new("BAKE_TARGET")
    if bpy.app.version < (5, 0, 0):
        tgt.use_nodes = True
    tnode = tgt.node_tree.nodes.new('ShaderNodeTexImage')
    tgt.node_tree.nodes.active = tnode
    lo_mats = list(lo.data.materials)
    lo.data.materials.clear()
    lo.data.materials.append(tgt)
    for p in lo.data.polygons:
        p.material_index = 0
    hi_mats = list(hi.data.materials)

    def run(kind, img_name, hi_mat_for=None, samples=1, **kw):
        img = bpy.data.images.new(img_name, res, res, alpha=False, float_buffer=True)
        img.colorspace_settings.name = 'Non-Color'
        tnode.image = img
        if hi_mat_for:
            for i, m in enumerate(hi_mats):
                hi.data.materials[i] = hi_mat_for(i, m)
        sc.cycles.samples = samples
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        hi.select_set(True)
        lo.select_set(True)
        bpy.context.view_layer.objects.active = lo
        bpy.ops.object.bake(type=kind, use_selected_to_active=True, cage_extrusion=bk.cage_extrusion,
                            max_ray_distance=bk.max_ray_distance, margin=bk.margin, use_clear=True,
                            target='IMAGE_TEXTURES', **kw)
        for i, m in enumerate(hi_mats):
            hi.data.materials[i] = m
        a = np.empty(res * res * 4, np.float32)
        img.pixels.foreach_get(a)
        bpy.data.images.remove(img)
        return a.reshape(res, res, 4)[..., :3]
    print("[wheel_lp] bake normal", flush=True)
    nrm = run('NORMAL', "B_nrm", samples=1, normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y',
              normal_b='POS_Z')

    def ao_mat(i, m):
        def b(nt):
            ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
            ao.samples = 24
            ao.only_local = True
            ao.inputs['Distance'].default_value = 0.06
            return ao.outputs['AO']
        return _emit("BAKE_AO", b)
    print("[wheel_lp] bake ao", flush=True)
    ao = run('EMIT', "B_ao", ao_mat, samples=int(os.environ.get("WHEEL_AO_SAMPLES", "32")))[..., 0]

    def id_mat(i, m):
        def b(nt):
            rgb = nt.nodes.new('ShaderNodeRGB')
            rgb.outputs[0].default_value = ((i + 1) / 8.0, 0.0, 0.0, 1.0)
            return rgb.outputs[0]
        return _emit("BAKE_ID%d" % i, b)
    print("[wheel_lp] bake id", flush=True)
    idm = np.rint(run('EMIT', "B_id", id_mat, samples=1)[..., 0] * 8.0).astype(np.int8) - 1

    def edge_mat(i, m):
        def b(nt):
            geo = nt.nodes.new('ShaderNodeNewGeometry')
            bev = nt.nodes.new('ShaderNodeBevel')
            bev.samples = 8
            bev.inputs['Radius'].default_value = 0.0025
            dot = nt.nodes.new('ShaderNodeVectorMath')
            dot.operation = 'DOT_PRODUCT'
            nt.links.new(bev.outputs['Normal'], dot.inputs[0])
            nt.links.new(geo.outputs['Normal'], dot.inputs[1])
            return dot.outputs['Value']
        return _emit("BAKE_EDGE", b)
    print("[wheel_lp] bake edge", flush=True)
    edge = np.clip((1.0 - run('EMIT', "B_edge", edge_mat, samples=8)[..., 0]) * 4.0, 0, 1)   # кромки → 1
    # чисті карти з ID: колір, шорсткість, металевість
    base = np.zeros((res, res, 3), np.float32)
    rough = np.full((res, res), 0.8, np.float32)
    metal = np.zeros((res, res), np.float32)
    for k, (hexc, r, mt) in MATS.items():
        sel = idm == k
        base[sel] = [c for c in (int(hexc[1:][i:i + 2], 16) / 255 for i in (0, 2, 4))]
        rough[sel] = r
        metal[sel] = mt
    empty = idm < 0
    base[empty] = [c for c in (int(MATS[RUBBER][0][1:][i:i + 2], 16) / 255 for i in (0, 2, 4))]
    rough[empty] = MATS[RUBBER][1]
    ao[empty] = 1.0
    os.makedirs(TEX_DIR, exist_ok=True)

    def save(name, arr):
        """8-бітний PNG без перетворень кольору (значення пікселів записуються як є)."""
        arr = np.clip(arr, 0, 1)
        if arr.ndim == 2:
            arr = np.repeat(arr[..., None], 3, 2)
        img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False)
        img.colorspace_settings.name = 'Non-Color'
        img.pixels.foreach_set(np.concatenate([arr, np.ones((res, res, 1), np.float32)], 2).astype(np.float32).ravel())
        path = os.path.join(TEX_DIR, name + ".png")
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        bpy.data.images.remove(img)
        print("[wheel_lp] saved", path, flush=True)
    save("Zmiy_Wheel_BaseColor", base)                  # значення вже в sRGB (з hex); у матеріалі — sRGB
    save("Zmiy_Wheel_Normal", nrm)
    save("Zmiy_Wheel_ORM", np.stack([ao, rough, metal], 2))
    save("Zmiy_Wheel_AO", ao)
    save("Zmiy_Wheel_Roughness", rough)
    save("Zmiy_Wheel_Metallic", metal)
    save("Zmiy_Wheel_Mask_ID", (idm.astype(np.float32) + 1) / 8.0)
    save("Zmiy_Wheel_Mask_Edge", edge)
    lo.data.materials.clear()
    for m in lo_mats:
        lo.data.materials.append(m)
    return hi, lo


if __name__ == "__main__":
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if args and args[0] == 'bake':
        bake(int(args[1]) if len(args) > 1 else 2048)
