# -*- coding: utf-8 -*-
"""
НРК «Змій Логістичний» — розгортка UV і матеріали.

Запускати ПІСЛЯ zmiy_build.py у тій самій сесії Blender:
    blender -b --factory-startup --python zmiy_build.py --python zmiy_texture.py

Режими (змінна оточення ZMIY_TEX_MODE):
    simple (за замовчуванням) — лише UV-розгортка; лишаються прості однотонні PBR-матеріали з zmiy_build.py
                                 (олива, гума, диски, цинк), без запікання і текстурних карт;
    full                       — запікання масок у Cycles і складання PBR-текстур зі зносом:
                                 textures/Zmiy_<Set>_{BaseColor,Normal,ORM,AO,Roughness,Metallic}.png,
                                 матеріали Zmiy_<Set> (один на набір).

Набори текстур (один матеріал на набір):
    Body  — Hull (з носом), Rear, FrontGuard, Deck (TEX_RES['Body'], за замовчуванням 4096)
    Top   — надбудова-портал Top_B4 (2048), запікає concepts/superstructure.py у режимі full
Колеса тут не розгортаються: легке колесо має власну UV і запечені з детального колеса текстури
(zmiy_wheel_lp.py → textures/Zmiy_Wheel_*.png).
Карти: BaseColor (sRGB), Normal (OpenGL, +Y), ORM (R=AO, G=Roughness, B=Metallic) і ті самі канали
окремими сірими PNG — Unit Workshop гри читає AO/Roughness/Metallic з каналу R окремих файлів.
"""
import math
import os
import time

import bpy
import numpy as np

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = bpy.path.abspath("//")
TEX_DIR = os.path.join(HERE, "textures")
TEX_RES = {'Body': 4096, 'Wheel': 2048, 'Top': 2048}
_SC = float(os.environ.get('ZMIY_TEX_SCALE', '1'))
TEX_RES = {k: int(v * _SC) for k, v in TEX_RES.items()}
SETS = {'Body': ['Hull', 'Rear', 'FrontGuard', 'Deck'],
        'Top': ['Top_B4']}          # надбудова-портал (concepts/superstructure.py викликає run(['Top']))
SAMPLES = 24
MARGIN = 16
CAGE, RAY = 0.016, 0.040     # запікання з детальної копії (<ім'я>_HP) на low-poly: виступ клітки й промінь, м
TEX_MODE = os.environ.get('ZMIY_TEX_MODE', 'simple')

# ID матеріалів (ключ — суфікс назви з MAT_DEF у zmiy_build.py)
MID = {'Zmiy_Paint_Olive': 1, 'Zmiy_Tube_Black': 2, 'Zmiy_Rubber': 3, 'Zmiy_Rim_Black': 4, 'Zmiy_Bolt_Zinc': 5,
       'Zmiy_Steel_Bare': 6, 'Zmiy_Glass': 7, 'Zmiy_Camera_Housing': 8, 'Zmiy_Knob_Orange': 9,
       'Zmiy_Plastic_Black': 10, 'Zmiy_EStop_Red': 11, 'Zmiy_EStop_Yellow': 12, 'Zmiy_Lens_Clear': 7,
       'Top_Glass': 7, 'Top_Radome': 13}
AXLES = (0.345, -0.528)   # осі коліс (y) і висота осі — для бризок бруду від коліс
WHEEL_Z = 0.385


def log(*a):
    print("[zmiy_texture]", *a, flush=True)


# =================================================================== UV
def select_only(objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def unwrap(objs, margin):
    select_only(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    try:
        bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin_method='SCALED',
                                margin=margin, shape_method=os.environ.get('ZMIY_PACK', 'CONCAVE'))
    except TypeError:
        bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


# =================================================================== запікання
def new_image(name, res, float_buf=True):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=float_buf)
    img.colorspace_settings.name = 'Non-Color'
    return img


def _emit_material(name, img, build):
    m = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(build(nt), em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    nt.nodes.active = tex
    return m


def _swap(objs, mat_for):
    saved = []
    seen = set()
    for o in objs:
        me = o.data
        if me.name in seen:
            continue
        seen.add(me.name)
        for i, m in enumerate(me.materials):
            saved.append((me, i, m))
            me.materials[i] = mat_for(m)
    return saved


def _restore(saved):
    tmp = set()
    for me, i, m in saved:
        tmp.add(me.materials[i])
        me.materials[i] = m
    for t in tmp:
        if t and t.users == 0:
            bpy.data.materials.remove(t)


def _target_material(img):
    m = bpy.data.materials.new("BAKE_TARGET")
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    tex = m.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = img
    m.node_tree.nodes.active = tex
    return m


def bake(objs, img, kind, build=None, mat_for=None, samples=SAMPLES, pair=None):
    """kind: 'EMIT' (build(nt)->сокет кольору) або 'NORMAL' (mat_for(orig)->матеріал).
    pair = (low, high): запікання selected→active з детальної копії на low-poly (обидва — тимчасові об'єднані)."""
    sc = bpy.context.scene
    sc.cycles.samples = samples
    if mat_for is None:
        shared = _emit_material("BAKE_" + img.name, img, build)
        mat_for = lambda m: shared
    if pair:
        lo, hi = pair
        tgt = _target_material(img)
        saved = _swap([hi], mat_for) + _swap([lo], lambda m: tgt)
        for o in bpy.context.view_layer.objects:
            o.select_set(o in (lo, hi))
        bpy.context.view_layer.objects.active = lo
        extra = dict(use_selected_to_active=True, cage_extrusion=CAGE, max_ray_distance=RAY)
    else:
        saved = _swap(objs, mat_for)
        select_only(objs)
        extra = {}
    t = time.time()
    if kind == 'NORMAL':
        bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y',
                            normal_b='POS_Z', margin=MARGIN, use_clear=True, target='IMAGE_TEXTURES', **extra)
    else:
        bpy.ops.object.bake(type='EMIT', margin=MARGIN, use_clear=True, target='IMAGE_TEXTURES', **extra)
    log("  bake", img.name, "%.1fs" % (time.time() - t))
    _restore(saved)


def bake_pair(lows, highs):
    """Тимчасові об'єднані копії low-poly (з UV) і детальних; оригінали ховаються від рендера на час запікання."""
    def dup_join(objs, name):
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in objs:
            o.hide_set(False)
            o.hide_render = False
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.duplicate()
        if len(bpy.context.selected_objects) > 1:
            bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active
        j.name = name
        return j
    lo = dup_join(lows, "_BAKE_LOW")
    hi = dup_join(highs, "_BAKE_HIGH")
    for o in lows + highs:
        o.hide_render = True
    return lo, hi


def drop_pair(pair, lows, highs):
    for o in pair:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for o in lows:
        o.hide_render = False
    for o in highs:
        o.hide_render = True
        o.hide_set(True)


def b_position(nt):
    return nt.nodes.new('ShaderNodeNewGeometry').outputs['Position']


def b_normal(nt):
    return nt.nodes.new('ShaderNodeNewGeometry').outputs['Normal']


def b_ao(dist, local=False):
    def f(nt):
        ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
        ao.samples = 16
        ao.only_local = local
        ao.inputs['Distance'].default_value = dist
        return ao.outputs['AO']
    return f


def b_edge(radius):
    def f(nt):
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        bev = nt.nodes.new('ShaderNodeBevel')
        bev.samples = 8
        bev.inputs['Radius'].default_value = radius
        dot = nt.nodes.new('ShaderNodeVectorMath')
        dot.operation = 'DOT_PRODUCT'
        nt.links.new(bev.outputs['Normal'], dot.inputs[0])
        nt.links.new(geo.outputs['Normal'], dot.inputs[1])
        return dot.outputs['Value']
    return f


def mat_id_for(m):
    idx = MID.get(m.name if m else "", 0)
    img = BAKE_TARGET['img']

    def build(nt):
        rgb = nt.nodes.new('ShaderNodeRGB')
        rgb.outputs[0].default_value = (idx / 16.0, 0.0, 0.0, 1.0)
        return rgb.outputs[0]
    return _emit_material("BAKEID_%s" % (m.name if m else "none"), img, build)


def normal_mat_for(radius):
    def f(m):
        img = BAKE_TARGET['img']
        mm = bpy.data.materials.new("BAKEN")
        if bpy.app.version < (5, 0, 0):
            mm.use_nodes = True
        nt = mm.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        bev = nt.nodes.new('ShaderNodeBevel')
        bev.samples = 8
        bev.inputs['Radius'].default_value = radius
        nt.links.new(bev.outputs['Normal'], bsdf.inputs['Normal'])
        nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = img
        nt.nodes.active = tex
        return mm
    return f


BAKE_TARGET = {}


def read(img, ch=4):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(img.size[1], img.size[0], 4)
    return a[..., :ch] if ch < 4 else a


def emit_masks(local_ao=False):
    return {'pos': (b_position, 1), 'nrm': (b_normal, 1), 'aoL': (b_ao(0.55, local_ao), SAMPLES),
            'aoS': (b_ao(0.045, local_ao), SAMPLES), 'edge': (b_edge(0.0028), SAMPLES)}


def bake_emit(set_name, objs, res, key, local_ao=False, pair=None):
    fn, smp = emit_masks(local_ao)[key]
    img = new_image("M_%s_%s" % (set_name, key), res)
    bake(objs, img, 'EMIT', build=fn, samples=smp, pair=pair)
    out = read(img, 3)
    bpy.data.images.remove(img)
    return out


def bake_masks(set_name, objs, res, local_ao=False, pair=None):
    M = {}
    for key in emit_masks(local_ao):
        M[key] = bake_emit(set_name, objs, res, key, local_ao, pair)
    img = new_image("M_%s_id" % set_name, res)
    BAKE_TARGET['img'] = img
    bake(objs, img, 'EMIT', mat_for=mat_id_for, samples=1, pair=pair)
    M['id'] = np.rint(read(img, 1)[..., 0] * 16.0).astype(np.int8)
    bpy.data.images.remove(img)
    img = new_image("M_%s_nb" % set_name, res)
    BAKE_TARGET['img'] = img
    bake(objs, img, 'NORMAL', mat_for=normal_mat_for(0.0035 if set_name != 'Wheel' else 0.0025), samples=SAMPLES,
         pair=pair)
    M['nb'] = read(img, 3)
    bpy.data.images.remove(img)
    return M


# =================================================================== шум (numpy, 3D)
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761 & 0xffffffff)
    h = h & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    h = h ^ (h >> 16)
    return (h & 0xffff).astype(np.float32) / 65535.0


def vnoise(p, seed=0):
    i = np.floor(p).astype(np.int64)
    f = (p - i).astype(np.float32)
    u = f * f * (3.0 - 2.0 * f)
    x, y, z = i[:, 0], i[:, 1], i[:, 2]
    res = np.zeros(len(p), np.float32)
    for dx in (0, 1):
        wx = u[:, 0] if dx else 1.0 - u[:, 0]
        for dy in (0, 1):
            wy = u[:, 1] if dy else 1.0 - u[:, 1]
            for dz in (0, 1):
                wz = u[:, 2] if dz else 1.0 - u[:, 2]
                res += wx * wy * wz * _hash(x + dx, y + dy, z + dz, seed)
    return res


def fbm(p, scale, octaves=4, seed=0, gain=0.5, stretch=(1, 1, 1)):
    p = p * np.asarray(stretch, np.float32) * scale
    out = np.zeros(len(p), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * vnoise(p, seed + o * 17)
        tot += amp
        p = p * 2.03 + 11.7
        amp *= gain
    return out / tot


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def srgb(h):
    h = h.lstrip('#')
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def mix(a, b, t):
    t = t[:, None] if (np.ndim(t) == 1 and np.ndim(a) == 2) else t
    return a + (b - a) * t


# =================================================================== складання карт
def composite(set_name, M, origin=(0, 0, 0)):
    H, W = M['id'].shape
    valid = M['id'].reshape(-1) > 0
    idx = np.nonzero(valid)[0]
    pos = M['pos'].reshape(-1, 3)[idx] - np.asarray(origin, np.float32)
    nrm = M['nrm'].reshape(-1, 3)[idx]
    aoL = np.clip(M['aoL'].reshape(-1, 3)[idx, 0], 0, 1)
    aoS = np.clip(M['aoS'].reshape(-1, 3)[idx, 0], 0, 1)
    edge = np.clip((1.0 - M['edge'].reshape(-1, 3)[idx, 0]) * 12.0, 0, 1)
    mid = M['id'].reshape(-1)[idx]
    n = len(idx)
    log("  composite %s: %d px" % (set_name, n))
    up = np.clip(nrm[:, 2], -1, 1)
    convex = edge * smooth(0.55, 0.9, aoS)          # опуклі ребра (не затінені)
    cavity = smooth(0.85, 0.35, aoS)                # щілини, внутрішні кути

    base = np.zeros((n, 3), np.float32)
    rough = np.full(n, 0.7, np.float32)
    metal = np.zeros(n, np.float32)
    height = np.zeros(n, np.float32)

    def sel(*ids):
        return np.isin(mid, ids)

    # --- шуми (світові координати → безшовно між острівцями)
    big = fbm(pos, 1.3, 4, 1)
    mid_n = fbm(pos, 6.0, 4, 2)
    fine = fbm(pos, 38.0, 3, 3)
    chip_n = fbm(pos, 22.0, 4, 4) * 0.75 + fine * 0.25

    # --- базові кольори
    paint = sel(1)
    pc = srgb('#434A37') * (0.94 + 0.12 * big)[:, None]
    pc = mix(pc, srgb('#4A4939'), smooth(0.45, 0.75, mid_n) * 0.22)               # нерівний відтінок
    pc = mix(pc, pc * 1.08 + 0.006, smooth(0.6, 0.95, up) * 0.5)                  # вигорання згори
    base[paint] = pc[paint]
    rough[paint] = (0.70 + 0.10 * mid_n + 0.04 * fine)[paint]
    tubes = sel(2)
    base[tubes] = (srgb('#1A1A1A') * (0.92 + 0.16 * mid_n)[:, None])[tubes]
    rough[tubes] = (0.42 + 0.10 * mid_n)[tubes]
    rub = sel(3)
    base[rub] = (srgb('#1C1C1C') * (0.93 + 0.14 * mid_n)[:, None])[rub]
    rough[rub] = (0.88 + 0.06 * fine)[rub]
    rim = sel(4)
    base[rim] = (srgb('#151515') * (0.95 + 0.12 * mid_n)[:, None])[rim]
    rough[rim] = (0.48 + 0.08 * mid_n)[rim]
    zinc = sel(5)
    base[zinc] = (srgb('#8A8A85') * (0.85 + 0.25 * fine)[:, None])[zinc]
    rough[zinc] = (0.33 + 0.18 * mid_n)[zinc]
    metal[zinc] = 1.0
    steel = sel(6)
    base[steel] = (srgb('#5E5E5A') * (0.85 + 0.25 * fine)[:, None])[steel]
    rough[steel] = (0.30 + 0.20 * mid_n)[steel]
    metal[steel] = 1.0
    glass = sel(7)
    base[glass] = srgb('#050505')
    rough[glass] = 0.05
    camh = sel(8)
    base[camh] = (srgb('#2A2A2A') * (0.94 + 0.12 * mid_n)[:, None])[camh]
    rough[camh] = (0.55 + 0.06 * fine)[camh]
    knob = sel(9)
    base[knob] = srgb('#C8561E')
    rough[knob] = 0.45
    plast = sel(10)                                                     # роз'єм, вимикач, корпус кнопки
    base[plast] = (srgb('#1E1F1C') * (0.92 + 0.14 * mid_n)[:, None])[plast]
    rough[plast] = (0.58 + 0.08 * fine)[plast]
    red = sel(11)
    base[red] = (srgb('#A82A1E') * (0.94 + 0.10 * mid_n)[:, None])[red]
    rough[red] = 0.42
    dome = sel(13)                                                      # кришка Starlink (фарбований пластик)
    base[dome] = (srgb('#5E625A') * (0.95 + 0.08 * mid_n)[:, None])[dome]
    rough[dome] = (0.60 + 0.06 * fine)[dome]
    yel = sel(12)
    base[yel] = (srgb('#C9A227') * (0.92 + 0.12 * mid_n)[:, None])[yel]
    rough[yel] = 0.55

    # --- сколи фарби на опуклих ребрах: ґрунт → голий метал
    painted = paint | tubes | rim | camh | yel
    wear_amt = np.where(paint, 1.0, np.where(tubes, 0.8, np.where(rim, 0.7, 0.4))).astype(np.float32)
    w = convex * wear_amt + smooth(0.62, 0.9, mid_n) * 0.10 * paint
    rail_top = tubes & (up > 0.55) & (pos[:, 2] > 0.9)                           # затерті поручні
    w = w + rail_top * smooth(0.35, 0.8, mid_n) * 0.55
    chip = smooth(0.66, 0.73, w * 0.90 + chip_n * 0.55) * painted
    bare = smooth(0.86, 0.91, w * 0.90 + chip_n * 0.55) * painted
    primer = srgb('#3B3A35')
    steel_c = srgb('#66645E') * (0.85 + 0.3 * fine)[:, None]
    base = mix(base, primer, chip)
    base = mix(base, steel_c, bare)
    rough = mix(rough, 0.55, chip)
    rough = mix(rough, 0.30, bare)
    metal = np.maximum(metal, bare)
    height -= chip * 0.6 + bare * 0.4

    # --- іржа: частина голих сколів, рудий наліт у швах і щілинах фарбованого металу
    rust_n = fbm(pos, 14.0, 4, 51)
    rust = bare * smooth(0.40, 0.70, rust_n) * 0.9
    rust += paint * cavity * smooth(0.62, 0.80, rust_n) * 0.45
    rust = np.clip(rust, 0, 1)
    rust_c = mix(srgb('#5C3119')[None, :].repeat(n, 0), srgb('#8A4B22')[None, :].repeat(n, 0), fine)
    base = mix(base, rust_c, rust)
    rough = mix(rough, 0.88, rust)
    metal = metal * (1.0 - rust)
    height += rust * 0.15

    # --- подряпини на горизонтальних поверхнях (палуба)
    scr = fbm(pos, 9.0, 3, 9, stretch=(18.0, 1.0, 18.0))
    scratches = smooth(0.73, 0.78, scr) * smooth(0.7, 0.95, up) * paint * 0.7
    base = mix(base, primer * 1.25, scratches)
    rough = mix(rough, 0.5, scratches)
    height -= scratches * 0.25
    # затерта палуба: по ній ходять і тягають вантаж — фарба світліша й гладша посередині, місцями до ґрунту
    if set_name == 'Body':
        deck = paint & (up > 0.95) & (np.abs(pos[:, 2] - 0.862) < 0.004) & (np.abs(pos[:, 0]) < 0.60)
        lane = smooth(0.62, 0.15, np.abs(pos[:, 0])) * smooth(0.30, 0.75, fbm(pos, 2.2, 3, 61))
        scuff = smooth(0.74, 0.86, fbm(pos, 26.0, 3, 63, stretch=(1.0, 2.5, 1.0)) + lane * 0.12) * deck
        base = mix(base, base * 1.06 + 0.006, lane * deck * 0.30)
        rough = mix(rough, 0.58, lane * deck * 0.5)
        base = mix(base, primer * 1.12, scuff * 0.45)

    # --- потьоки на вертикальних поверхнях
    streak = fbm(pos, 7.0, 3, 21, stretch=(9.0, 9.0, 0.6)) if set_name != 'Wheel' else np.zeros(n, np.float32)
    vert = smooth(0.6, 0.25, np.abs(up))
    st = smooth(0.58, 0.75, streak) * vert * (paint | camh) * 0.35
    base = mix(base, base * 0.78 + srgb('#3a3226') * 0.10, st)

    # --- пил згори і в щілинах
    dust_c = srgb('#9A8F78')
    dust_n = fbm(pos, 3.0, 4, 31)
    dust = smooth(0.25, 0.8, up) * smooth(0.55, 0.85, dust_n * 0.6 + fine * 0.4 + cavity * 0.30) * 0.14
    dust += cavity * smooth(0.45, 0.70, dust_n) * 0.22
    dust *= ~glass
    dust *= np.where(tubes | camh, 0.45, 1.0)
    if set_name == 'Wheel':
        dust *= np.where(rim, 0.25, 0.5)
    dust = np.clip(dust, 0, 0.6)
    base = mix(base, dust_c, dust)
    rough = mix(rough, 0.93, dust)
    metal = metal * (1.0 - dust)

    # --- бруд знизу і бризки від коліс
    z = pos[:, 2]
    mud_n = fbm(pos, 4.5, 5, 41)
    splat = fbm(pos, 16.0, 3, 43)
    if set_name == 'Wheel':
        r = np.sqrt(pos[:, 1] ** 2 + pos[:, 2] ** 2)
        tread = smooth(0.27, 0.30, r)
        mud = (tread * cavity * smooth(0.45, 0.75, mud_n) * 0.6
               + smooth(0.14, 0.25, r) * cavity * smooth(0.55, 0.8, mud_n) * 0.30 * (rub | rim))
        lugtop = tread * smooth(0.6, 0.95, aoS) * edge * 0.6
        base = mix(base, srgb('#262523'), lugtop * rub)                            # обтерта гума на кромках
    else:
        low = smooth(0.62, 0.22, z)
        wheel_zone = np.zeros(n, np.float32)
        for ay in AXLES:
            d = np.sqrt((pos[:, 1] - ay) ** 2 + (pos[:, 2] - WHEEL_Z) ** 2)
            wheel_zone = np.maximum(wheel_zone, smooth(0.62, 0.36, d) * smooth(0.36, 0.40, np.abs(pos[:, 0])))
        mud = low * smooth(0.42, 0.78, mud_n + 0.2 * (1 - up)) * 0.85 + wheel_zone * smooth(0.57, 0.63, splat) * 0.55
        mud += smooth(0.5, 0.2, z) * smooth(-0.3, -0.8, up) * 0.5                 # днище
        mud *= ~glass
    mud = np.clip(mud, 0, 1)
    wet = smooth(0.45, 0.8, mud_n)
    dry_c, wet_c = (srgb('#5E574C'), srgb('#3A342C')) if set_name == 'Wheel' else (srgb('#675846'), srgb('#41372B'))
    mud_c = mix(dry_c[None, :].repeat(n, 0), wet_c[None, :].repeat(n, 0), wet)
    base = mix(base, mud_c, mud * 0.92)
    rough = mix(rough, 0.86 - 0.25 * wet, mud)
    metal = metal * (1.0 - mud)
    height += mud * (0.35 + 0.4 * splat)

    # --- AO у карту (м'який) і легка затінка кольору в глибоких щілинах
    ao = np.clip(aoL ** 0.75, 0, 1)
    base = base * (0.82 + 0.18 * aoS)[:, None]
    height += 0.03 * fine

    # --- у картинки
    def full(v, ch=1, fill=0.0):
        out = np.full((H * W, ch), fill, np.float32)
        out[idx] = v if ch > 1 else v[:, None]
        return out.reshape(H, W, ch)
    out = dict(base=full(base, 3, 0.05), rough=full(rough, 1, 0.8), metal=full(metal, 1, 0.0),
               ao=full(ao, 1, 1.0), height=full(height, 1, 0.0), valid=valid.reshape(H, W))
    out['normal'] = detail_normal(M['nb'], out['height'][..., 0], out['valid'], set_name)
    return out


def detail_normal(nb, h, valid, set_name):
    """Нормаль фасок (із запікання) + деталь із карти висот (градієнт у UV = дотичний простір)."""
    k = {'Body': 3.0, 'Wheel': 2.0}.get(set_name, 2.0)
    hv = np.where(valid, h, 0.0)
    gy, gx = np.gradient(hv)
    edge = ~(valid & np.roll(valid, 1, 0) & np.roll(valid, -1, 0) & np.roll(valid, 1, 1) & np.roll(valid, -1, 1))
    gx[edge] = 0
    gy[edge] = 0
    dn = np.stack([-gx * k, -gy * k, np.ones_like(gx)], -1)
    dn /= np.linalg.norm(dn, axis=-1, keepdims=True)
    b = nb * 2.0 - 1.0
    b[~valid] = (0, 0, 1)
    n = np.stack([b[..., 0] + dn[..., 0], b[..., 1] + dn[..., 1], b[..., 2] * dn[..., 2]], -1)
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    return n * 0.5 + 0.5


# =================================================================== запис і матеріали
def save_png(name, arr, mode='RGB', srgb_out=False):
    H, W = arr.shape[:2]
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, W, H, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if srgb_out else 'Non-Color'
    if arr.shape[2] == 1:
        arr = np.repeat(arr, 3, 2)
    rgba = np.concatenate([np.clip(arr, 0, 1), np.ones((H, W, 1), np.float32)], 2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    path = os.path.join(TEX_DIR, name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    sc = bpy.context.scene
    st = sc.render.image_settings
    old = (st.file_format, st.color_mode, st.color_depth, st.compression)
    st.file_format, st.color_mode, st.color_depth, st.compression = 'PNG', ('BW' if mode == 'BW' else 'RGB'), '8', 90
    img.save_render(path, scene=sc)
    st.file_format, st.color_mode, st.color_depth, st.compression = old
    bpy.data.images.remove(img)
    return path


def write_set(set_name, R):
    base = to_srgb(R['base'])
    paths = {}
    paths['BaseColor'] = save_png("Zmiy_%s_BaseColor" % set_name, base, srgb_out=True)
    paths['Normal'] = save_png("Zmiy_%s_Normal" % set_name, R['normal'])
    orm = np.concatenate([R['ao'], R['rough'], R['metal']], 2)
    paths['ORM'] = save_png("Zmiy_%s_ORM" % set_name, orm)
    paths['AO'] = save_png("Zmiy_%s_AO" % set_name, R['ao'], 'BW')
    paths['Roughness'] = save_png("Zmiy_%s_Roughness" % set_name, R['rough'], 'BW')
    paths['Metallic'] = save_png("Zmiy_%s_Metallic" % set_name, R['metal'], 'BW')
    return paths


def gltf_settings_group():
    g = bpy.data.node_groups.get("glTF Material Output")
    if g:
        return g
    g = bpy.data.node_groups.new("glTF Material Output", 'ShaderNodeTree')
    try:
        g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    except AttributeError:
        g.inputs.new('NodeSocketFloat', "Occlusion")
    return g


def load_img(path, non_color):
    img = bpy.data.images.load(path, check_existing=True)
    img.reload()
    img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    return img


def pbr_material(set_name, paths):
    name = "Zmiy_" + set_name
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (600, 0)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    tb = nt.nodes.new('ShaderNodeTexImage')
    tb.image = load_img(paths['BaseColor'], False)
    tb.location = (-400, 300)
    nt.links.new(tb.outputs['Color'], bsdf.inputs['Base Color'])
    to = nt.nodes.new('ShaderNodeTexImage')
    to.image = load_img(paths['ORM'], True)
    to.location = (-400, 0)
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    sep.location = (-100, 0)
    nt.links.new(to.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[1], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs[2], bsdf.inputs['Metallic'])
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = load_img(paths['Normal'], True)
    tn.location = (-400, -300)
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.location = (-100, -300)
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    grp = nt.nodes.new('ShaderNodeGroup')
    grp.node_tree = gltf_settings_group()
    grp.location = (300, -350)
    nt.links.new(sep.outputs[0], grp.inputs[0])
    return m


def assign_single(objs, mat):
    done = set()
    for o in objs:
        me = o.data
        if me.name in done:
            continue
        done.add(me.name)
        for p in me.polygons:
            p.material_index = 0
        me.materials.clear()
        me.materials.append(mat)


def run(sets=None):
    os.makedirs(TEX_DIR, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.render.bake.margin = MARGIN
    sets = sets or [k for k, names in SETS.items() if all(n in bpy.data.objects for n in names)]
    # модулі й колізії не повинні впливати на AO/пил під час запікання
    # і сторонні об'єкти сцени (стандартний куб тощо) — інакше вони затінюють AO
    model = set()
    coll = bpy.data.collections.get("Zmiy_Logistic")
    if coll:
        model = {o for o in coll.all_objects}
    hidden = [o for o in bpy.context.scene.objects if not o.hide_render and o.type == 'MESH' and
              (o.name.startswith(('Module_', 'UCX_')) or '_LOD' in o.name or (model and o not in model))]
    for o in hidden:
        o.hide_render = True
    for set_name in sets:
        t0 = time.time()
        objs = [bpy.data.objects[n] for n in SETS[set_name]]
        res = TEX_RES[set_name]
        log(set_name, "res", res)
        unwrap(objs, margin=0.0025 if res >= 4096 else 0.004)
        origin = (0, 0, 0)
        if TEX_MODE != 'full':
            log(set_name, "UV only (simple materials) %.0fs" % (time.time() - t0))
            continue
        highs = [bpy.data.objects.get(o.name + "_HP") for o in objs]
        use_hp = all(highs)
        cache = os.environ.get('ZMIY_MASK_CACHE')
        cfile = os.path.join(cache, "%s_%d%s.npz" % (set_name, res, "_lp" if use_hp else "")) if cache else None
        if cfile and os.path.exists(cfile):
            M = dict(np.load(cfile))
            log("  masks from cache", cfile)
            redo = [k for k in os.environ.get('ZMIY_REBAKE', '').split(',') if k]
            pair = bake_pair(objs, highs) if (redo and use_hp) else None
            for k in redo:                       # перепекти окремі маски поверх кешу (напр. ZMIY_REBAKE=aoL)
                M[k] = bake_emit(set_name, objs, res, k, local_ao=(set_name == 'Wheel'), pair=pair)
            if pair:
                drop_pair(pair, objs, highs)
            if redo:
                np.savez(cfile, **M)
        else:
            pair = bake_pair(objs, highs) if use_hp else None
            if pair:
                log("  selected→active: %s → low-poly" % ", ".join(h.name for h in highs))
            M = bake_masks(set_name, objs, res, local_ao=(set_name == 'Wheel'), pair=pair)
            if pair:
                drop_pair(pair, objs, highs)
            if cfile:
                os.makedirs(cache, exist_ok=True)
                np.savez(cfile, **M)
        R = composite(set_name, M, origin)
        paths = write_set(set_name, R)
        mat = pbr_material(set_name, paths)
        assign_single(objs, mat)
        log(set_name, "done %.0fs" % (time.time() - t0))
    for o in hidden:
        o.hide_render = False


if __name__ == "__main__":
    run()
