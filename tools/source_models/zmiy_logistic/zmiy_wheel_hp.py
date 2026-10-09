# -*- coding: utf-8 -*-
"""Детальне (high-poly) колесо «Змія» — джерело для майбутнього low-poly і запікання текстур.
blender -b --factory-startup --python zmiy_wheel_hp.py -- [папка]      → <папка>/zmiy_wheel_high.blend
Основну модель не змінює. Праве колесо, вісь — X (назовні +X), центр у нулі; ліве колесо в моделі має бути
тим самим мешем, поверненим на 180° навколо Z (не дзеркальним — інакше написи на боковині навиворіт).

Шина 10.0/75-15.3 (Ø 0,77 м) з протектором як на референсі ArtStation: 28 кроків, 4 колонки шашок —
центральні скошені шестикутники з вістрям до осьової, ліва й права колонки заходять одна між одну
(зигзаг-канавка); плечові — великі, з уступом біля внутрішнього кута, заходять на боковину (через одну
довга/коротка); шашки з ухилом стінок 7°, заокругленою кромкою й переходом у дно канавки, каменевикидачі
в поперечних канавках, перемички між плечовими шашками, «вусики» від прес-форми. Боковина: захисне
кільце над ободом, кільце центрування, декоративні кільця, рельєфні написи (без назви виробника).
Обід 9.00×15.3 зі справжнім профілем (закраїни з підгином, полиці з виступами, монтажний струмок),
суцільний штампований диск, приварений переривчастими швами, 5 шпильок з різьбою і гайок із шайбами,
ковпак маточини на болтах із пробкою для мастила, кутовий вентиль із захисною скобою, маркування диска.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

MODEL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MODEL)
import zmiy_build as zb      # noqa: E402

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 1 else MODEL

RUBBER, RIM, ZINC, DARK = range(4)
N_SEG = 256                       # сегментів по колу для тіл обертання
R_CROWN = 0.372                   # радіус каркаса під протектором (дно канавок)
PITCHES = 28                      # крок ~84 мм — як на референсі
P_ARC = 2 * math.pi * R_CROWN / PITCHES
H_TREAD = 0.016                   # глибина протектора
DRAFT = math.tan(math.radians(7))


# =================================================================== загальні примітиви (вісь колеса — X)
def lathe_x(bm, prof, segs=N_SEG, closed=False, mat=RUBBER, a0=0.0):
    """Тіло обертання профілю [(w, r)] навколо осі X: точка (w, r·cos a, r·sin a)."""
    rings = []
    for k in range(segs):
        a = a0 + 2 * math.pi * k / segs
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((w, r * ca, r * sa)) for (w, r) in prof])
    n = len(prof)
    m = n if closed else n - 1
    faces = []
    for k in range(segs):
        r0, r1 = rings[k], rings[(k + 1) % segs]
        for i in range(m):
            j = (i + 1) % n
            try:
                f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
                f.material_index = mat
                faces.append(f)
            except ValueError:
                pass
    return faces


def cyl(bm, p0, p1, r, segs=16, mat=ZINC, r1=None):
    zb.set_mat(zb.bm_cyl(bm, Vector(p0), Vector(p1), r, segs, r1), mat)


def lathe_local(bm, prof, segs, M, mat):
    """Тіло обертання профілю [(r, h)] навколо локальної Z, перенесене матрицею M."""
    zb.set_mat(zb.bm_lathe(bm, prof, segs, M), mat)


def chaikin(pts, it=2, closed=False):
    """Згладжування ламаної (заокруглені згини листа): кінці відкритої ламаної лишаються на місці."""
    pts = [Vector(p) for p in pts]
    for _ in range(it):
        out = [] if closed else [pts[0]]
        n = len(pts)
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            a, b = pts[i], pts[(i + 1) % n]
            out += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


def resample(pts, step):
    """Рівномірна перевибірка ламаної за довжиною дуги."""
    pts = [Vector(p) for p in pts]
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    n = max(2, int(L[-1] / step) + 1)
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / (n - 1)
        while j < len(L) - 2 and L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(L[j + 1] - L[j], 1e-12)
        out.append(pts[j].lerp(pts[j + 1], min(max(t, 0.0), 1.0)))
    return out


def offset_open(cl, t):
    """Оболонка товщини t навколо осьової лінії листа [(w, r)] → замкнений контур (зовнішня + внутрішня)."""
    a, b = [], []
    for i, c in enumerate(cl):
        p0, p1 = cl[max(i - 1, 0)], cl[min(i + 1, len(cl) - 1)]
        d = (p1 - p0).normalized()
        n = Vector((-d.y, d.x))
        a.append(c + n * t / 2)
        b.append(c - n * t / 2)
    return a + b[::-1]


def sweep(bm, path, radius, sides=8, mat=RIM):
    """Валик (зварний шов) уздовж шляху з точок; кінці закриті."""
    rings = []
    for i, p in enumerate(path):
        d = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        q = d.to_track_quat('Z', 'Y').to_matrix()
        rings.append([bm.verts.new(p + q @ Vector((radius * math.cos(2 * math.pi * k / sides),
                                                    radius * math.sin(2 * math.pi * k / sides), 0)))
                      for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            k1 = (k + 1) % sides
            bm.faces.new((r0[k], r0[k1], r1[k1], r1[k])).material_index = mat
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        bm.faces.new(ring[::-1] if rev else ring).material_index = mat


# =================================================================== каркас шини
BASE_HALF = [(0.000, 0.3720), (0.040, 0.3718), (0.080, 0.3705), (0.105, 0.3670), (0.122, 0.3600),
             (0.134, 0.3490), (0.141, 0.3350), (0.1450, 0.3150), (0.1462, 0.2900), (0.1460, 0.2700),
             (0.1450, 0.2560), (0.1420, 0.2460), (0.1375, 0.2340), (0.1300, 0.2230), (0.1210, 0.2150),
             (0.1168, 0.2110)]
BEAD = [(0.1162, 0.2040), (0.1158, 0.1995), (0.1080, 0.1990), (0.0990, 0.1990)]   # борт на полиці обода
SIDE_BUMPS = [  # (r центру, висота, напівширина): кільця й захисний пояс на боковині
    (0.2960, 0.0010, 0.0016),     # кільце під кінцями плечових шашок
    (0.2430, 0.0008, 0.0012),     # нижня межа поля написів
    (0.2290, 0.0035, 0.0065),     # захисний пояс над закраїною обода
    (0.2175, 0.0006, 0.0007),     # кільце центрування (контроль посадки шини на обід)
]


def carcass_half():
    """Половина профілю каркаса (від осьової до полиці обода), згладжена й рівномірна, з кільцями боковини."""
    pts = resample(chaikin(BASE_HALF, 3), 0.0018)
    out = []
    for i, p in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        d = (b - a).normalized()
        n = Vector((-d.y, d.x))                       # обхід від осьової до борту → нормаль назовні
        disp = 0.0
        if p.y < 0.31:
            for rc, h, hw in SIDE_BUMPS:
                x = abs(p.y - rc) / hw
                if x < 1:
                    disp += h * 0.5 * (1 + math.cos(math.pi * x))
        out.append(p + n * disp)
    # дрібніше там, де кільця (щоб валики були круглі)
    return out + [Vector(q) for q in BEAD]


class Profile:
    """Поверхня каркаса під протектором: σ (дуга від осьової) → (w, r), нормаль."""

    def __init__(self):
        pts = resample(chaikin(BASE_HALF, 3), 0.0010)
        self.s, self.p = [0.0], pts
        for a, b in zip(pts, pts[1:]):
            self.s.append(self.s[-1] + (b - a).length)

    def at(self, sig):
        sg = -1.0 if sig < 0 else 1.0
        sig = abs(sig)
        i = 0
        while i < len(self.s) - 2 and self.s[i + 1] < sig:
            i += 1
        t = (sig - self.s[i]) / max(self.s[i + 1] - self.s[i], 1e-12)
        p = self.p[i].lerp(self.p[i + 1], min(max(t, 0.0), 1.0))
        d = (self.p[i + 1] - self.p[i]).normalized()
        n = Vector((-d.y, d.x))
        return Vector((sg * p.x, p.y)), Vector((sg * n.x, n.y))


PROF = Profile()


def tread_point(u, s, h, th0):
    """(σ поперек, s уздовж по колу, висота над каркасом) → 3D. Кут — за дугою на радіусі R_CROWN."""
    p, n = PROF.at(u)
    w, r = p.x + n.x * h, p.y + n.y * h
    th = th0 + s / R_CROWN
    return Vector((w, r * math.cos(th), r * math.sin(th)))


# =================================================================== шашки протектора
def ccw(pts):
    a = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else pts[::-1]


def rounded(pts, r_cvx=0.0065, r_ccv=0.0040, seg=4):
    """Заокруглені кути (опуклі/увігнуті); радіус обмежено довжиною сусідніх ребер."""
    pts = ccw([tuple(p) for p in pts])
    cuts = {}
    n = len(pts)
    for i in range(n):
        a, p, b = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        cross = (p - a).x * (b - p).y - (p - a).y * (b - p).x
        r = r_cvx if cross > 0 else r_ccv
        ang = (a - p).angle(b - p)
        lim = 0.45 * min((a - p).length, (b - p).length) * math.tan(ang / 2)
        cuts[i] = min(r, lim)
    out = [Vector(q) for q in zb.round_poly(pts, cuts, seg)]
    # довгі ребра дрібнимо (≤ 4 мм), щоб стінки й верх шашки згиналися разом із плечем шини
    fine = []
    for i, q in enumerate(out):
        nx = out[(i + 1) % len(out)]
        k = max(1, int((nx - q).length / 0.004 + 0.999))
        fine += [q.lerp(nx, j / k) for j in range(k)]
    return fine


def build_block(bm, poly, th0, hfun, mat=RUBBER, draft=DRAFT, flare=True, top_round=True, spew=None):
    """Шашка: основа з галтеллю в дно канавки → стінки з ухилом → заокруглена кромка → верх (дрібна сітка).
    poly — [(σ, s)] у координатах протектора; hfun(σ) — висота шашки."""
    base = rounded(poly)
    n = len(base)
    hs = [hfun(p.x) for p in base]
    # напрям і масштаб зсуву кожної вершини (мітра)
    mit = []
    for i in range(n):
        a, p, b = base[i - 1], base[i], base[(i + 1) % n]
        e0, e1 = (p - a).normalized(), (b - p).normalized()
        n0, n1 = Vector((e0.y, -e0.x)), Vector((e1.y, -e1.x))
        m = n0 + n1
        m = n0 if m.length < 1e-6 else m.normalized()
        mit.append(m / max(0.4, m.dot(n0)))
    z_wall = 0.0032 if flare else 0.0

    def ring(kind):
        out = []
        for i in range(n):
            h = hs[i]
            if kind == 'b0':
                d, z = (0.0030, -0.0020) if flare else (0.0, -0.0015)
            elif kind == 'b1':
                d, z = 0.0011, 0.0010
            elif kind == 'b2':
                d, z = 0.0, 0.0032
            elif kind == 't0':
                z = h - 0.0022
                d = -draft * max(z - z_wall, 0.0)
            elif kind == 't1':
                z = h - 0.0006
                d = -draft * max(z - z_wall, 0.0) - 0.0013
            else:                                      # верх
                z = h
                d = -draft * max(z - z_wall, 0.0) - (0.0024 if top_round else 0.0)
            out.append((base[i] + mit[i] * d, z))
        return out
    kinds = (['b0', 'b1', 'b2'] if flare else ['b0']) + (['t0', 't1', 'top'] if top_round else ['top'])
    loops = [ring(k) for k in kinds]
    vl = [[bm.verts.new(tread_point(q.x, q.y, z, th0)) for q, z in lp] for lp in loops]
    bm.faces.new(vl[0][::-1]).material_index = mat     # дно в товщі каркаса: шашка — замкнене тіло (нормалі назовні)
    for a, b in zip(vl[:-2], vl[1:-1]):              # пояси стінки (крім останнього)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    for i in range(n):                                # останній пояс стінки
        j = (i + 1) % n
        a, b = vl[-2], vl[-1]
        bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    # верх: концентричні кільця до центроїда (рівні чотирикутники, без довгих трикутників) — гладко після
    # вигину по кривій поверхні
    top2d = [q for q, _ in loops[-1]]
    zs = [z for _, z in loops[-1]]
    c2 = sum(top2d, Vector((0, 0))) / n
    hc = sum(zs) / n
    prev = vl[-1]
    K = 4
    dome = 0.0008                                     # верх злегка опуклий
    for k in range(1, K):
        t = k / K
        cur = []
        for i in range(n):
            q = top2d[i].lerp(c2, t)
            cur.append(bm.verts.new(tread_point(q.x, q.y, hfun(q.x) + dome * (1 - (1 - t) ** 2), th0)))
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((prev[i], prev[j], cur[j], cur[i])).material_index = mat
        prev = cur
    cv = bm.verts.new(tread_point(c2.x, c2.y, hfun(c2.x) + dome, th0))
    for i in range(n):
        bm.faces.new((prev[i], prev[(i + 1) % n], cv)).material_index = mat
    if spew:
        cx = sum(q.x for q in top2d) / n + spew[0]
        cy = sum(q.y for q in top2d) / n + spew[1]
        cyl(bm, tread_point(cx, cy, hc - 0.0005, th0), tread_point(cx, cy, hc + 0.0045, th0), 0.0006, 6, mat,
            r1=0.0004)


def h_center(u):
    return H_TREAD


def h_shoulder(u):
    return H_TREAD if u < 0.112 else H_TREAD - (u - 0.112) * 0.11


def tread_layout():
    """Контури шашок правої половини (σ ≥ 0), s — уздовж кола відносно центру шашки. Ліва половина —
    поворот на 180° зі зсувом на півкроку (ненапрямлений малюнок)."""
    # центральна: скошений шестикутник, вістря (σ = 0) трохи нижче середини — заходить між шашками лівої колонки
    center = [(-0.003, -0.010), (0.016, 0.027), (0.054, 0.039), (0.060, 0.033), (0.060, -0.022), (0.052, -0.032),
              (0.026, -0.042), (0.010, -0.036)]
    # плечова: велика, з уступом біля внутрішнього нижнього кута; закінчення на боковині довге/коротке
    def shoulder(e):
        return [(0.070, -0.028), (0.070, 0.022), (0.082, 0.034), (0.140, 0.032), (e, 0.024), (e, -0.032),
                (0.140, -0.040), (0.094, -0.042), (0.090, -0.032)]
    return center, shoulder(0.172), shoulder(0.158)


def edge_s(poly, u, top=True):
    """s краю багатокутника (верхнього/нижнього) на заданому σ."""
    best = None
    n = len(poly)
    for i in range(n):
        (u0, s0), (u1, s1) = poly[i], poly[(i + 1) % n]
        if (u0 - u) * (u1 - u) <= 0 and abs(u1 - u0) > 1e-9:
            s = s0 + (s1 - s0) * (u - u0) / (u1 - u0)
            if best is None or (top and s > best) or (not top and s < best):
                best = s
    return best


def build_tread(bm):
    center, sh_long, sh_short = tread_layout()
    rnd = random.Random(11)
    for k in range(PITCHES):
        for side in (1, -1):
            # ліва половина — поворот правої на 180° (σ→−σ, s→−s) зі зсувом на півкроку: ненапрямлений малюнок
            th = 2 * math.pi * (k + (0.0 if side > 0 else 0.5)) / PITCHES
            mapc = (lambda pts, sd=side: [(sd * u, sd * s) for u, s in pts])
            sp = (rnd.uniform(-0.008, 0.008), rnd.uniform(-0.008, 0.008))
            build_block(bm, mapc(center), th, lambda u: h_center(abs(u)), spew=sp)
            shp = sh_long if k % 2 == 0 else sh_short
            th_s = th + side * (0.25 * P_ARC) / R_CROWN   # плечові зсунуті на чверть кроку
            sp = (rnd.uniform(-0.010, 0.010), rnd.uniform(-0.008, 0.008))
            build_block(bm, mapc(shp), th_s, lambda u: h_shoulder(abs(u)), spew=sp)
            # каменевикидач у поперечній канавці між центральними шашками (σ 0,037)
            u = 0.037
            s_top = edge_s(center, u, True)
            s_bot = edge_s(center, u, False) + P_ARC
            sm = (s_top + s_bot) / 2
            ej = [(u - 0.009, sm + 0.0009), (u + 0.009, sm + 0.0021), (u + 0.009, sm - 0.0007), (u - 0.009, sm - 0.0019)]
            build_block(bm, mapc(ej), th, lambda _u: 0.0035, flare=False, top_round=False, draft=0.0)
            # перемичка між плечовими шашками біля плеча (σ 0,118…0,136), нижче шашок
            nxt = sh_short if k % 2 == 0 else sh_long
            u0, u1 = 0.118, 0.136
            tb = [(u0, edge_s(shp, u0, True) - 0.002), (u1, edge_s(shp, u1, True) - 0.002),
                  (u1, edge_s(nxt, u1, False) + P_ARC + 0.002), (u0, edge_s(nxt, u0, False) + P_ARC + 0.002)]
            build_block(bm, mapc(tb), th_s, lambda _u: 0.0055, flare=False, top_round=True, draft=0.15)


# =================================================================== написи (рельєф)
def font():
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"):
        if os.path.exists(path):
            return bpy.data.fonts.load(path, check_existing=True)
    return None


def text_mesh(txt, size, condense=0.86):
    cu = bpy.data.curves.new("txt", 'FONT')
    cu.body = txt
    cu.size = size
    cu.align_x = 'CENTER'
    cu.resolution_u = 3
    cu.extrude = 0.0005
    f = font()
    if f:
        cu.font = f
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(cu)
    tb = bmesh.new()
    tb.from_mesh(me)
    bpy.data.meshes.remove(me)
    for v in tb.verts:
        v.co.x *= condense
    # дрібнимо довгі ребра, щоб літери лягли на кривину боковини
    for _ in range(3):
        long_e = [e for e in tb.edges if e.calc_length() > 0.003]
        if not long_e:
            break
        bmesh.ops.subdivide_edges(tb, edges=long_e, cuts=1)
    bmesh.ops.triangulate(tb, faces=tb.faces[:])
    return tb


def place_text(bm, txt, size, r_base, ang, surf_w, height=0.0007, mat=RUBBER):
    """Рельєфний напис по дузі: верх літер — назовні по радіусу, читається ззовні колеса (з +X).
    surf_w(r) — w поверхні на радіусі r; низ літер — на 0,3 мм у товщі."""
    tb = text_mesh(txt, size)
    zmax = max((v.co.z for v in tb.verts), default=0.0)
    vmap = {}
    for v in tb.verts:
        x, y, z = v.co
        R = r_base + y
        a = ang + x / r_base
        X = surf_w(R) + (height if z > zmax - 1e-6 else -0.0003)
        vmap[v] = bm.verts.new((X, R * math.sin(a), R * math.cos(a)))
    for f in tb.faces:
        try:
            bm.faces.new([vmap[v] for v in f.verts]).material_index = mat
        except ValueError:
            pass
    tb.free()


def side_surface(half):
    """w поверхні боковини як функція r (ділянка нижче плеча; профіль там монотонний за r)."""
    pts = sorted([(p.y, p.x) for p in half if 0.205 < p.y < 0.31])

    def w_at(r):
        for (r0, w0), (r1, w1) in zip(pts, pts[1:]):
            if r0 <= r <= r1:
                return w0 + (w1 - w0) * (r - r0) / max(r1 - r0, 1e-12)
        return pts[0][1] if r < pts[0][0] else pts[-1][1]
    return w_at


# =================================================================== обід, диск, кріплення
RIM_CL = [(0.1290, 0.2128), (0.1250, 0.2142), (0.1215, 0.2125), (0.1196, 0.2085), (0.1172, 0.1985),
          (0.1150, 0.1962), (0.0985, 0.1950), (0.0950, 0.1956), (0.0915, 0.1938), (0.0840, 0.1890),
          (0.0700, 0.1765), (0.0600, 0.1722), (0.0000, 0.1720)]
RIM_T = 0.0045


def build_rim(bm):
    half = [Vector(p) for p in RIM_CL]
    full = half + [Vector((-p.x, p.y)) for p in reversed(half[:-1])]
    cl = resample(chaikin(full, 3), 0.0015)
    loop = offset_open(cl, RIM_T)
    lathe_x(bm, [(q.x, q.y) for q in loop], closed=True, mat=RIM)


# осьова лінія диска (w, r): осьовий фланець у колодязі обода → конус → штампований пояс → посадкова площина
DISC_CL = [(0.0100, 0.1672), (0.0300, 0.1672), (0.0380, 0.1620), (0.0440, 0.1500), (0.0500, 0.1420),
           (0.0500, 0.1280), (0.0530, 0.1230), (0.0530, 0.1130), (0.0500, 0.1080), (0.0500, 0.1030),
           (0.0590, 0.0950), (0.0590, 0.0420)]
DISC_T = 0.006
W_FACE = 0.0590 + DISC_T / 2          # зовнішня посадкова площина під гайки
W_BAND = 0.0500 + DISC_T / 2          # зовнішня площина штампованого поля (маркування)


def build_disc(bm):
    cl = resample(chaikin([Vector(p) for p in DISC_CL], 2), 0.0012)
    loop = offset_open(cl, DISC_T)
    lathe_x(bm, [(q.x, q.y) for q in loop], segs=192, closed=True, mat=RIM)
    # маточина за диском (фланець і цапфа)
    hub = [(-0.170, 0.0), (-0.170, 0.048), (0.030, 0.048), (0.034, 0.078), (0.0555, 0.078), (0.0555, 0.036),
           (0.0640, 0.036), (0.0640, 0.0)]
    lathe_x(bm, hub, segs=96, mat=RIM)
    # переривчасті шви диска з ободом: 8 × 26° з обох боків осьового фланця
    r_w = 0.1697
    for w in (0.0335, 0.0100):
        for k in range(8):
            a0 = math.radians(k * 45 + 7)
            path = [Vector((w, r_w * math.sin(a), r_w * math.cos(a)))
                    for a in (a0 + math.radians(26) * i / 18 for i in range(19))]
            sweep(bm, path, 0.0028, 8, RIM)


def hex_nut(bm, M, af=0.024, h=0.014, flange_r=0.016, flange_h=0.003, mat=ZINC):
    """Гайка з пресшайбою: фланець (конічна посадка) + шестигранник із фаскою зверху."""
    lathe_local(bm, [(0.0, 0.0), (flange_r - 0.0015, 0.0), (flange_r, 0.0012), (flange_r, flange_h),
                     (0.0, flange_h)], 40, M, mat)
    R = af / math.sqrt(3)
    Mh = M @ Matrix.Translation((0, 0, flange_h)) @ Matrix.Rotation(math.radians(30), 4, 'Z')
    lathe_local(bm, [(0.0, 0.0), (R, 0.0), (R, h - 0.0022), (R * 0.86, h), (0.0, h)], 6, Mh, mat)


def stud(bm, M, r=0.008, L=0.013, pitch=0.0015, mat=ZINC):
    """Шпилька з різьбою (кільця за кроком) і фаскою на кінці."""
    prof = [(0.0, 0.0), (r * 0.92, 0.0)]
    z = 0.0
    while z + pitch < L - 0.0015:
        prof += [(r, z + pitch * 0.35), (r, z + pitch * 0.55), (r * 0.88, z + pitch)]
        z += pitch
    prof += [(r * 0.92, L - 0.0012), (r * 0.70, L), (0.0, L)]
    lathe_local(bm, prof, 24, M, mat)


def build_fasteners(bm):
    ax = Vector((1, 0, 0)).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    for k in range(5):
        a = math.radians(90 + 72 * k)
        c = Vector((W_FACE, 0.0675 * math.sin(a), 0.0675 * math.cos(a)))
        M = Matrix.Translation(c) @ ax
        hex_nut(bm, M)
        stud(bm, M @ Matrix.Translation((0, 0, 0.017)))
    # ковпак маточини: фланець на 4 болтах M6, купол, пробка для мастила
    cap = [(0.0620, 0.0), (0.0620, 0.0460), (0.0660, 0.0460), (0.0660, 0.0365), (0.0820, 0.0320),
           (0.0880, 0.0280), (0.0880, 0.0)]
    lathe_x(bm, cap, segs=96, mat=RIM)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        c = Vector((0.0660, 0.0412 * math.sin(a), 0.0412 * math.cos(a)))
        M = Matrix.Translation(c) @ ax @ Matrix.Scale(0.55, 4)
        vv, ff = zb.BOLT_DOME
        zb.set_mat(zb.bm_from_pydata(bm, [tuple(M @ Vector(v)) for v in vv], ff), ZINC)
    hex_nut(bm, Matrix.Translation((0.0880, 0, 0)) @ ax, af=0.014, h=0.006, flange_r=0.0085, flange_h=0.0015)


def build_valve(bm):
    """Кутовий вентиль у колодязі обода (поза диском) і захисна скоба, приварена до колодязя."""
    a = math.radians(205)
    rad = Vector((0, math.sin(a), math.cos(a)))       # радіальний напрям
    tan = Vector((0, math.cos(a), -math.sin(a)))      # дотичний
    X = Vector((1, 0, 0))
    r_in = 0.1720 - RIM_T / 2                         # внутрішня поверхня колодязя
    b0 = X * 0.047 + rad * r_in
    nut_M = Matrix.Translation(b0) @ (-rad).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    hex_nut(bm, nut_M, af=0.016, h=0.005, flange_r=0.010, flange_h=0.0015)
    b1 = X * 0.047 + rad * (r_in - 0.010)
    cyl(bm, b0, b1, 0.0050, 16, ZINC)                 # корпус
    cyl(bm, b1 + X * -0.004, b1 + X * 0.024, 0.0040, 16, ZINC)   # стрижень після згину (уздовж осі назовні)
    b2 = b1 + X * 0.024
    cyl(bm, b2, b2 + X * 0.010, 0.0052, 16, DARK)     # ковпачок
    # скоба: дві ніжки від колодязя вниз і місток над вентилем, 3 мм смуга шириною 18 мм
    for sg in (-1, 1):
        c = X * 0.069 + rad * (r_in - 0.0085) + tan * (sg * 0.016)
        _box(bm, c, rad, tan, X, (0.017, 0.003, 0.018), RIM)
    _box(bm, X * 0.069 + rad * (r_in - 0.0185) + tan * 0.0, rad, tan, X, (0.003, 0.035, 0.018), RIM)
    for sg in (-1, 1):                                # шви ніжок до колодязя
        p0 = X * 0.060 + rad * (r_in - 0.0005) + tan * (sg * 0.0175)
        sweep(bm, [p0, p0 + X * 0.018], 0.0022, 8, RIM)


def _box(bm, c, ex, ey, ez, size, mat):
    """Брусок size=(вздовж ex, ey, ez) з центром c."""
    sx, sy, sz = (q / 2 for q in size)
    v = {}
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                v[i, j, k] = bm.verts.new(c + ex * (i * sx) + ey * (j * sy) + ez * (k * sz))
    quads = [((-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1)), ((1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1)),
             ((-1, -1, -1), (-1, -1, 1), (1, -1, 1), (1, -1, -1)), ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)),
             ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)), ((-1, -1, 1), (-1, 1, 1), (1, 1, 1), (1, -1, 1))]
    for q in quads:
        bm.faces.new([v[t] for t in q]).material_index = mat


def disc_marking(bm):
    """Вибите маркування на штампованому полі диска: типорозмір і дата."""
    def flat(_r):
        return W_BAND
    for txt, ang in (("9.00x15.3  ET 0", math.radians(0)), ("05 25", math.radians(180))):
        place_text(bm, txt, 0.0085, 0.1285, ang, flat, height=0.0004, mat=RIM)


# =================================================================== збірка
def build_wheel_high():
    bm = bmesh.new()
    half = carcass_half()
    prof = [(-p.x, p.y) for p in reversed(half)] + [(p.x, p.y) for p in half[1:]]
    lathe_x(bm, prof, closed=True, mat=RUBBER)          # замкнене тіло (дно — на полиці обода): нормалі назовні
    build_tread(bm)
    w_at = side_surface(half)
    texts = [("10.0/75-15.3", 0.026, 0.2585, 0.0), ("IMPLEMENT", 0.019, 0.2600, math.pi),
             ("14 PR", 0.015, 0.2620, math.radians(62)), ("TUBELESS", 0.012, 0.2625, math.radians(-64)),
             ("DOT  X7MK  1225", 0.0085, 0.2510, math.radians(124))]
    for txt, size, rb, ang in texts:
        place_text(bm, txt, size, rb, ang, w_at)
    build_rim(bm)
    build_disc(bm)
    build_fasteners(bm)
    build_valve(bm)
    disc_marking(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=2e-6)
    zb.triangulate(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("Zmiy_Wheel_High")
    bm.to_mesh(me)
    bm.free()
    zb.finalize_mesh(me, 35.0)
    for k in ('rubber', 'rim', 'zinc', 'dark'):
        me.materials.append(zb.MAT[k])
    return me


def main():
    zb.MAT.clear()
    for k, v in zb.MAT_DEF.items():
        zb.MAT[k] = zb.make_material(*v)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    me = build_wheel_high()
    coll = bpy.data.collections.get("Zmiy_Wheel_High") or bpy.data.collections.new("Zmiy_Wheel_High")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    ob = bpy.data.objects.new("Wheel_High", me)
    coll.objects.link(ob)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print("WHEEL_HIGH tris", tris, "verts", len(me.vertices))
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "zmiy_wheel_high.blend"))
    return ob


if __name__ == "__main__":
    main()
