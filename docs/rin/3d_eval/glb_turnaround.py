"""Рендер GLB з 4 ортографічних ракурсів + статистика сітки.
blender -b -P glb_turnaround.py -- <model.glb> <out_dir> [size]"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
src, out = argv[0], argv[1]
size = int(argv[2]) if len(argv) > 2 else 1024
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
objs = [o for o in bpy.data.objects if o.type == 'MESH']
if not objs:
    raise SystemExit('no mesh')

# --- габарити й статистика
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
tris = 0; verts = 0; quads = 0; ngons = 0
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    m = o.data; verts += len(m.vertices)
    for p in m.polygons:
        n = len(p.vertices); tris += n - 2
        quads += n == 4; ngons += n > 4
dim = hi - lo
center = (lo + hi) / 2
H = dim.z
with open(os.path.join(out, 'stats.txt'), 'w') as f:
    f.write(f'objects {len(objs)} verts {verts} tris {tris} quads {quads} ngons {ngons}\n')
    f.write(f'bbox lo {tuple(round(v,3) for v in lo)} hi {tuple(round(v,3) for v in hi)} dim {tuple(round(v,3) for v in dim)}\n')
    # компоненти і неманіфолд
    for o in objs:
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold(); bpy.ops.object.mode_set(mode='OBJECT')
        nm = sum(1 for e in o.data.edges if e.select)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
        parts = [p for p in bpy.data.objects if p.type == 'MESH']
        sizes = sorted((len(p.data.vertices) for p in parts), reverse=True)
        f.write(f'{o.name}: non-manifold edges {nm}; loose parts {len(parts)} sizes {sizes[:10]}\n')
        bpy.ops.object.select_all(action='DESELECT')
        for p in parts: p.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
        break

# --- сцена: плоске освітлення, ортокамера
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.use_denoising = False
sc.cycles.device = 'CPU'
sc.render.resolution_x = size; sc.render.resolution_y = int(size * 1.6)
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new('W'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 1.0
# матеріали → без спекуляру
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    for ms in o.material_slots:
        mt = ms.material
        if mt and mt.use_nodes:
            for n in mt.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Roughness'].default_value = 1.0
                    for k in ('Specular IOR Level', 'Specular'):
                        if k in n.inputs: n.inputs[k].default_value = 0.0
cam_data = bpy.data.cameras.new('C'); cam_data.type = 'ORTHO'; cam_data.ortho_scale = H * 1.1
cam = bpy.data.objects.new('C', cam_data); sc.collection.objects.link(cam); sc.camera = cam
views = {'front': (0, -1, 0, 0), 'back': (0, 1, 0, math.pi), 'left': (-1, 0, 0, -math.pi / 2), 'right': (1, 0, 0, math.pi / 2)}
d = max(dim) * 3
for name, (x, y, z, rz) in views.items():
    cam.location = center + Vector((x, y, z)) * d
    cam.rotation_euler = (math.pi / 2, 0, rz)
    sc.render.filepath = os.path.join(out, f'{name}.png'); bpy.ops.render.render(write_still=True)
# крупно обличчя
cam_data.ortho_scale = H * 0.22
cam.location = Vector((center.x, center.y - d, lo.z + H * 0.9)); cam.rotation_euler = (math.pi / 2, 0, 0)
sc.render.resolution_y = size
sc.render.filepath = os.path.join(out, 'face.png'); bpy.ops.render.render(write_still=True)
cam.location = Vector((center.x - d, center.y, lo.z + H * 0.9)); cam.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
sc.render.filepath = os.path.join(out, 'face_side.png'); bpy.ops.render.render(write_still=True)
# сітка (wireframe) фасу
for o in bpy.data.objects:
    if o.type == 'MESH':
        mod = o.modifiers.new('wire', 'WIREFRAME'); mod.thickness = H * 0.0008; mod.use_replace = True
        wm = bpy.data.materials.new('wire'); wm.use_nodes = True
        wm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1)
        o.data.materials.clear(); o.data.materials.append(wm)
cam_data.ortho_scale = H * 1.1; sc.render.resolution_y = int(size * 1.6)
cam.location = center + Vector((0, -d, 0)); cam.rotation_euler = (math.pi / 2, 0, 0)
sc.render.filepath = os.path.join(out, 'wire_front.png'); bpy.ops.render.render(write_still=True)
cam_data.ortho_scale = H * 0.22; sc.render.resolution_y = size
cam.location = Vector((center.x, center.y - d, lo.z + H * 0.9))
sc.render.filepath = os.path.join(out, 'wire_face.png'); bpy.ops.render.render(write_still=True)
print('done')
