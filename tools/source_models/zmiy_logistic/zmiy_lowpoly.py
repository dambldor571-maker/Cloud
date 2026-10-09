# -*- coding: utf-8 -*-
"""
НРК «Змій Логістичний» — low-poly і LOD. Запускати після zmiy_build.py (і перед zmiy_texture.py):
    blender -b --factory-startup --python zmiy_build.py --python zmiy_lowpoly.py --python zmiy_texture.py --python zmiy_export.py

Для кожної складової з атрибутом граней zmiy_detail (його ставить zmiy_build.join_group за назвою частини):
    <Ім'я>_HP  — детальна копія (колекція Zmiy_HighPoly): джерело запікання, у файли гри не йде;
    <Ім'я>     — low-poly без дрібниць (шви, болти, гайки, шайби, шпильки, гермовводи…) — вони переходять
                 у карти нормалей, кольору й AO через запікання selected→active (zmiy_texture.py).
LOD1 / LOD2 (колекція Zmiy_LOD) — <Ім'я>_LOD1/_LOD2 зі спрощенням Decimate (LOD_RATIOS) для складових і коліс;
ті самі UV і матеріали, тож текстури спільні. Їх робить lods() з zmiy_export.py (після текстур) і пише
окремими файлами zmiy_logistic_LOD1/_LOD2 (.glb, .fbx).
"""
import math

import bmesh
import bpy

PARTS = ['Hull', 'Rear', 'FrontGuard', 'Deck']
WHEELS = ['Wheel_FL', 'Wheel_FR', 'Wheel_RL', 'Wheel_RR']
LOD_RATIOS = (0.5, 0.22)
COLL_NAME = "Zmiy_Logistic"


def log(*a):
    print("[zmiy_lowpoly]", *a, flush=True)


def sub_collection(name, hide=True):
    parent = bpy.data.collections[COLL_NAME]
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in parent.children:
        parent.children.link(c)
    return c


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def split(ob, hp_coll):
    """ob стає low-poly, повертає детальну копію <ім'я>_HP (або None, якщо позначок немає)."""
    me = ob.data
    if me.attributes.get("zmiy_detail") is None:
        return None
    old = bpy.data.objects.get(ob.name + "_HP")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    bm = bmesh.new()                     # нормалі назовні (для запікання selected→active це важливо)
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    hp = ob.copy()
    hp.data = me.copy()
    hp.name = hp.data.name = ob.name + "_HP"
    for c in hp.users_collection:
        c.objects.unlink(hp)
    hp_coll.objects.link(hp)
    hp.hide_render = True
    hp.hide_set(True)
    bm = bmesh.new()
    bm.from_mesh(me)
    lay = bm.faces.layers.int.get("zmiy_detail")
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay]], context='FACES')
    bm.to_mesh(me)
    bm.free()
    me.attributes.remove(me.attributes["zmiy_detail"])
    log("%-10s HP %6d → LP %6d трикутників" % (ob.name, tris(hp.data), tris(me)))
    return hp


def decimated(me, ratio, name):
    tmp = bpy.data.objects.new("_dec_tmp", me)
    bpy.context.scene.collection.objects.link(tmp)
    mod = tmp.modifiers.new("dec", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    out = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    out.name = name
    bpy.data.objects.remove(tmp, do_unlink=True)
    try:
        out.set_sharp_from_angle(angle=math.radians(35.0))
    except AttributeError:
        pass
    return out


def make_lods(lod_coll):
    for o in list(lod_coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    wheel_lods = {}
    for k, ratio in enumerate(LOD_RATIOS, 1):
        for nm in PARTS + WHEELS:
            src = bpy.data.objects.get(nm)
            if src is None:
                continue
            if nm in WHEELS:
                if (k, src.data.name) not in wheel_lods:
                    wheel_lods[(k, src.data.name)] = decimated(src.data, ratio, "%s_LOD%d" % (src.data.name, k))
                me = wheel_lods[(k, src.data.name)]
            else:
                me = decimated(src.data, ratio, "%s_LOD%d" % (nm, k))
            lod = bpy.data.objects.new("%s_LOD%d" % (nm, k), me)
            lod_coll.objects.link(lod)
            lod.parent = src.parent
            lod.matrix_world = src.matrix_world.copy()
            lod.hide_render = True
            lod.hide_set(True)
        tot = sum(tris(bpy.data.objects["%s_LOD%d" % (n, k)].data) for n in PARTS + WHEELS
                  if bpy.data.objects.get("%s_LOD%d" % (n, k)))
        log("LOD%d (%.0f %%): %d трикутників" % (k, ratio * 100, tot))


def run():
    hp_coll = sub_collection("Zmiy_HighPoly")
    for nm in PARTS:
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            split(ob, hp_coll)
    tot = sum(tris(bpy.data.objects[n].data) for n in PARTS + WHEELS if bpy.data.objects.get(n))
    log("LOD0: %d трикутників" % tot)


def lods():
    """LOD1/LOD2 — після розгортки й текстур (zmiy_export.py викликає перед експортом)."""
    make_lods(sub_collection("Zmiy_LOD"))


if __name__ == "__main__":
    run()
