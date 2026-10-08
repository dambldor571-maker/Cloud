# -*- coding: utf-8 -*-
"""
НРК «Змій Логістичний» — експорт (.blend, .fbx, .glb) і рендери. Запускати після zmiy_build.py і zmiy_texture.py:
    blender -b --factory-startup --python zmiy_build.py --python zmiy_texture.py --python zmiy_export.py

Файли (поруч зі скриптом):
    zmiy_logistic.blend          — сцена з моделлю, модулями, колізіями; текстури — відносні шляхи textures/
    zmiy_logistic.fbx            — модель + колізії UCX_* (Unreal), текстури поряд у textures/
    zmiy_logistic.glb            — модель для Godot/веб (текстури вбудовані, 2048 px)
    zmiy_logistic_modules.glb    — опційні модулі (Starlink, вантаж, вила-концепт) у тих самих координатах
    renders/*.jpg                — 3/4 спереду, збоку, спереду, згори, ззаду, знизу + варіанти з модулями
Масштаб 1 юніт = 1 м. Ніс машини = +Y у Blender (= −Z у glTF, «вперед» у Godot).
"""
import math
import os
import shutil
import time

import bpy
from mathutils import Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = bpy.path.abspath("//")
OUT = os.environ.get("ZMIY_OUT", HERE)
REN = os.path.join(OUT, "renders")
GLB_TEX = 2048
BASE = ["Zmiy_Logistic", "Body", "Cage", "Camera", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR",
        "Decal_Logo_Nose", "Decal_Logo_Rear", "Decal_Text_Rear"]
MODULES = ["Module_Starlink", "Module_Cargo", "Module_Forks"]


def log(*a):
    print("[zmiy_export]", *a, flush=True)


def objs(names):
    return [bpy.data.objects[n] for n in names if n in bpy.data.objects]


def select(names):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    sel = objs(names)
    for o in sel:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = sel[0]
    return sel


def collision_names():
    c = bpy.data.collections.get("Zmiy_Collision")
    return [o.name for o in c.objects] if c else []


# =================================================================== експорт
def export_fbx(path):
    select(BASE + collision_names())
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'EMPTY', 'MESH'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z',
                             axis_up='Y', use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True,
                             add_leaf_bones=False, bake_anim=False, path_mode='RELATIVE', embed_textures=False)
    log("fbx", path, "%.1f MB" % (os.path.getsize(path) / 1e6))


def _downscaled_copies(size):
    """На час експорту GLB підміняє текстури >size копіями розміром size (тимчасові PNG)."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="zmiy_glb_")
    swaps = []
    for img in list(bpy.data.images):
        if img.source != 'FILE' or max(img.size) <= size:
            continue
        cp = img.copy()
        cp.scale(size, size)
        cp.filepath_raw = os.path.join(tmp, os.path.basename(bpy.path.abspath(img.filepath)))
        cp.file_format = 'PNG'
        cp.save()
        swaps.append((img, cp))
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        for n in mat.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                for img, cp in swaps:
                    if n.image == img:
                        n.image = cp
    return swaps


def _restore(swaps):
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        for n in mat.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                for img, cp in swaps:
                    if n.image == cp:
                        n.image = img
    for img, cp in swaps:
        bpy.data.images.remove(cp)


def export_glb(path, names):
    sel = select(names)
    for o in sel:
        o.hide_render = False
    swaps = _downscaled_copies(GLB_TEX)
    try:
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                                  export_yup=True, export_texcoords=True, export_normals=True,
                                  export_materials='EXPORT', export_image_format='AUTO', export_extras=False)
    finally:
        _restore(swaps)
    log("glb", path, "%.1f MB" % (os.path.getsize(path) / 1e6))


def save_blend(path):
    for img in bpy.data.images:
        if img.source == 'FILE' and img.filepath:
            img.filepath = bpy.path.relpath(bpy.path.abspath(img.filepath), start=os.path.dirname(path))
    for o in objs(MODULES):
        o.hide_set(True)
        o.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=path, relative_remap=True, compress=True)
    log("blend", path, "%.1f MB" % (os.path.getsize(path) / 1e6))


# =================================================================== рендери
def setup_stage():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = int(os.environ.get("ZMIY_SAMPLES", "160"))
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = int(os.environ.get("ZMIY_RES_PCT", "100"))
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.exposure = -0.35
    sc.view_settings.look = 'AgX - Base Contrast' if 'AgX - Base Contrast' in [
        i.name for i in bpy.types.ColorManagedViewSettings.bl_rna.properties['look'].enum_items] else 'None'
    w = bpy.data.worlds.get("Zmiy_Sky") or bpy.data.worlds.new("Zmiy_Sky")
    sc.world = w
    if bpy.app.version < (5, 0, 0):
        w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    # нейтральне небо: градієнт від світлого горизонту до блакитного зеніту
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.62, 0.64, 0.66, 1)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (0.28, 0.40, 0.60, 1)
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs[0])
    bg.inputs['Strength'].default_value = 0.9
    nt.links.new(bg.outputs[0], out.inputs[0])
    sun = bpy.data.objects.get("Stage_Sun")
    if not sun:
        sun = bpy.data.objects.new("Stage_Sun", bpy.data.lights.new("Stage_Sun", 'SUN'))
        sc.collection.objects.link(sun)
    sun.data.energy = 3.0
    sun.data.angle = math.radians(1.2)
    sun.rotation_euler = (math.radians(42), 0, math.radians(-128))
    # земля: ґрунт із легкою текстурою
    g = bpy.data.objects.get("Stage_Ground")
    if not g:
        me = bpy.data.meshes.new("Stage_Ground")
        r = 30
        me.from_pydata([(-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0)], [], [(0, 1, 2, 3)])
        g = bpy.data.objects.new("Stage_Ground", me)
        sc.collection.objects.link(g)
        m = bpy.data.materials.new("Stage_Ground")
        if bpy.app.version < (5, 0, 0):
            m.use_nodes = True
        t = m.node_tree
        b = t.nodes['Principled BSDF']
        noise = t.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 3.0
        noise.inputs['Detail'].default_value = 8.0
        ramp = t.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (0.060, 0.055, 0.042, 1)
        ramp.color_ramp.elements[1].color = (0.125, 0.115, 0.090, 1)
        t.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
        t.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.95
        me.materials.append(m)
    cam = bpy.data.objects.get("Stage_Camera")
    if not cam:
        cam = bpy.data.objects.new("Stage_Camera", bpy.data.cameras.new("Stage_Camera"))
        sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


VIEWS = {  # назва: (позиція камери, ціль, фокусна, орто-масштаб або None)
    "front34": ((-3.6, 3.9, 1.55), (0.0, 0.0, 0.62), 50, None),
    "side": ((0.0, 0.0, 0.70), (0.0, 0.0, 0.70), 50, 2.75),
    "front": ((0.0, 0.0, 0.70), (0.0, 0.0, 0.70), 50, 2.80),
    "top": ((0.0, -0.08, 6.0), (0.0, -0.08, 0.0), 50, 3.20),
    "bottom": ((0.0, -0.08, -4.0), (0.0, -0.08, 0.0), 50, 3.00),
    "rear34": ((3.4, -3.9, 1.6), (0.0, -0.1, 0.60), 50, None),
}


def aim_sun(cam):
    """Сонце світить з боку камери (зліва-згори від неї), щоб видима сторона не була в тіні."""
    sun = bpy.data.objects.get("Stage_Sun")
    if not sun:
        return
    d = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1))     # напрям погляду (matrix_world ще не оновлена)
    az = math.atan2(d.y, d.x) if abs(d.z) < 0.95 else math.radians(-90)
    sun.rotation_euler = (math.radians(45), 0, az - math.radians(135))   # світло ззаду-зліва від камери


def render_views(cam, names, suffix=""):
    os.makedirs(REN, exist_ok=True)
    sc = bpy.context.scene
    for v in names:
        loc, tgt, lens, ortho = VIEWS[v]
        cd = cam.data
        if ortho:
            cd.type = 'ORTHO'
            cd.ortho_scale = ortho
            if v == "side":
                cam.location = (6.0, -0.06, 0.62)
                cam.rotation_euler = (math.radians(90), 0, math.radians(90))
            elif v == "front":
                cam.location = (0.0, 6.0, 0.69)
                cam.rotation_euler = (math.radians(90), 0, math.radians(180))
            elif v == "bottom":
                cam.location = loc
                cam.rotation_euler = (math.radians(180), 0, math.radians(90))
            else:
                cam.location = loc
                cam.rotation_euler = (0, 0, math.radians(90))
        else:
            cd.type = 'PERSP'
            cd.lens = lens
            cam.location = loc
            cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        aim_sun(cam)
        sc.render.image_settings.file_format = 'JPEG'
        sc.render.image_settings.quality = 92
        sc.render.filepath = os.path.join(REN, "zmiy_%s%s.jpg" % (v, suffix))
        t = time.time()
        bpy.ops.render.render(write_still=True)
        log("render", sc.render.filepath, "%.0fs" % (time.time() - t))


def run():
    os.makedirs(OUT, exist_ok=True)
    tex_out = os.path.join(OUT, "textures")
    if os.path.abspath(tex_out) != os.path.abspath(os.path.join(HERE, "textures")):
        shutil.copytree(os.path.join(HERE, "textures"), tex_out, dirs_exist_ok=True)
    for o in objs(MODULES):
        o.hide_set(True)
        o.hide_render = True
    if os.environ.get("ZMIY_NO_EXPORT") != "1":
        export_fbx(os.path.join(OUT, "zmiy_logistic.fbx"))
        export_glb(os.path.join(OUT, "zmiy_logistic.glb"), BASE)
        export_glb(os.path.join(OUT, "zmiy_logistic_modules.glb"), MODULES)
    for o in objs(MODULES):
        o.hide_set(True)
        o.hide_render = True
    if os.environ.get("ZMIY_NO_RENDER") != "1":
        prev_cam, prev_world = bpy.context.scene.camera, bpy.context.scene.world
        hidden = []
        mine = {o.name for o in bpy.data.collections["Zmiy_Logistic"].all_objects}
        for o in bpy.context.scene.objects:          # чужі об'єкти сцени (куб, світло) — не в кадр
            if o.name not in mine and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
        cam = setup_stage()
        views = os.environ.get("ZMIY_VIEWS", "front34,side,front,top,rear34,bottom,modules,forks").split(",")
        render_views(cam, [v for v in ("front34", "side", "front", "top", "rear34") if v in views])
        g = bpy.data.objects.get("Stage_Ground")
        g.hide_render = True
        fill = bpy.data.objects.new("Stage_Fill", bpy.data.lights.new("Stage_Fill", 'SUN'))
        bpy.context.scene.collection.objects.link(fill)
        fill.data.energy = 2.0
        fill.rotation_euler = (math.radians(160), 0, math.radians(20))
        if "bottom" in views:
            render_views(cam, ["bottom"])
        bpy.data.objects.remove(fill, do_unlink=True)
        g.hide_render = False
        for o in objs(["Module_Starlink", "Module_Cargo"]):
            o.hide_render = False
        if "modules" in views:
            render_views(cam, ["front34"], "_modules")
        for o in objs(["Module_Starlink", "Module_Cargo"]):
            o.hide_render = True
        for o in objs(["Module_Forks"]):
            o.hide_render = False
        if "forks" in views:
            render_views(cam, ["front34"], "_forks_concept")
        for o in objs(["Module_Forks"]):
            o.hide_render = True
        for nm in ("Stage_Ground", "Stage_Sun", "Stage_Camera"):
            o = bpy.data.objects.get(nm)
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
        for o in hidden:
            o.hide_render = False
        bpy.context.scene.camera, bpy.context.scene.world = prev_cam, prev_world
    save_blend(os.path.join(OUT, "zmiy_logistic.blend"))


if __name__ == "__main__":
    run()
