"""Збірка тіла: закрити кожну частину → злити → voxel remesh → головна оболонка → Quadriflow (або decimate) → ваги → риг → тест пози.
blender -b -P body_build.py -- <model.glb> <out_dir> [target_quads]"""
import bpy, sys, os, math, time
from mathutils import Vector, Euler
argv=sys.argv[sys.argv.index('--')+1:]; src,out=argv[0],argv[1]; TARGET=int(argv[2]) if len(argv)>2 else 28000; os.makedirs(out,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
BODY=['tripo_part_%d'%i for i in (0,2,1,3,5,4,9,6,8,7,10,16,17,12,11)]
objs={o.name:o for o in bpy.data.objects if o.type=='MESH'}; arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
lo=Vector((1e9,)*3); hi=Vector((-1e9,)*3)
for o in objs.values():
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); lo=Vector(map(min,lo,w)); hi=Vector(map(max,hi,w))
H=hi.z-lo.z; cm=H/170.0
def sel(o): bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
copies=[]
for n in BODY:
    o=objs[n]; c=o.copy(); c.data=o.data.copy(); bpy.context.scene.collection.objects.link(c); c.parent=None
    c.matrix_world=o.matrix_world.copy()
    for m in list(c.modifiers): c.modifiers.remove(m)
    sel(c); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=cm*0.02)
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.fill_holes(sides=0); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.mesh.select_non_manifold(); nm=c.data.total_edge_sel; bpy.ops.object.mode_set(mode='OBJECT')
    print(f'part {n}: closed, non-manifold {nm}'); copies.append(c)
# джерело ваг — зліплені частини (без ремешу)
bpy.ops.object.select_all(action='DESELECT')
srcs=[]
for c in copies:
    s=c.copy(); s.data=c.data.copy(); bpy.context.scene.collection.objects.link(s); s.select_set(True); srcs.append(s)
bpy.context.view_layer.objects.active=srcs[0]; bpy.ops.object.join(); wsrc=bpy.context.active_object; wsrc.name='Body_src'; wsrc.hide_render=True
# злиття для ремешу
bpy.ops.object.select_all(action='DESELECT')
for c in copies: c.select_set(True)
bpy.context.view_layer.objects.active=copies[0]; bpy.ops.object.join(); body=bpy.context.active_object; body.name='Body'
t=time.time(); body.data.remesh_voxel_size=cm*0.3; body.data.use_remesh_fix_poles=True; body.data.use_remesh_preserve_volume=True
sel(body); bpy.ops.object.voxel_remesh()
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
parts=sorted([o for o in bpy.data.objects if o.name.startswith('Body') and o.name!='Body_src'],key=lambda o:-len(o.data.vertices))
print('voxel shells',len(parts),[len(p.data.vertices) for p in parts[:5]],'t=%.0fs'%(time.time()-t))
body=parts[0]; body.name='Body'
for p in parts[1:]: bpy.data.objects.remove(p)
sel(body); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.mesh.select_non_manifold(); print('voxel non-manifold',body.data.total_edge_sel); bpy.ops.object.mode_set(mode='OBJECT')
vox_faces=len(body.data.polygons)
t=time.time(); bpy.ops.object.quadriflow_remesh(target_faces=TARGET,use_mesh_symmetry=True,seed=1,mode='FACES')
method='quadriflow'
if len(body.data.polygons)==vox_faces:
    method='decimate'; dec=body.modifiers.new('dec','DECIMATE'); dec.use_symmetry=True; dec.symmetry_axis='X'; dec.ratio=(TARGET*2)/sum(len(p.vertices)-2 for p in body.data.polygons); bpy.ops.object.modifier_apply(modifier='dec')
print('remesh method',method,'faces',len(body.data.polygons),'quads',sum(1 for p in body.data.polygons if len(p.vertices)==4),'tris-equiv',sum(len(p.vertices)-2 for p in body.data.polygons),'t=%.0fs'%(time.time()-t))
# ваги
dt=body.modifiers.new('dt','DATA_TRANSFER'); dt.object=wsrc; dt.use_vert_data=True; dt.data_types_verts={'VGROUP_WEIGHTS'}; dt.vert_mapping='POLYINTERP_NEAREST'; dt.layers_vgroup_select_src='ALL'; dt.mix_mode='REPLACE'
bpy.ops.object.datalayout_transfer(modifier='dt'); bpy.ops.object.modifier_apply(modifier='dt')
bpy.ops.object.vertex_group_limit_total(limit=4); bpy.ops.object.vertex_group_normalize_all(lock_active=False)
# згладити ваги трохи
bpy.ops.object.mode_set(mode='WEIGHT_PAINT'); bpy.ops.object.vertex_group_smooth(group_select_mode='ALL',factor=0.5,repeat=2); bpy.ops.object.mode_set(mode='OBJECT')
body.parent=arm; body.matrix_parent_inverse=arm.matrix_world.inverted(); am=body.modifiers.new('arm','ARMATURE'); am.object=arm
m=bpy.data.materials.new('body'); m.use_nodes=True; n=m.node_tree.nodes['Principled BSDF']; n.inputs['Base Color'].default_value=(0.9,0.78,0.7,1); n.inputs['Roughness'].default_value=1
body.data.materials.clear(); body.data.materials.append(m)
for name in BODY: objs[name].hide_render=True
# рендер
vis=[o for o in bpy.data.objects if o.type=='MESH' and not o.hide_render]
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.device='CPU'; sc.render.film_transparent=True
sc.view_settings.view_transform='Standard'; sc.render.resolution_x=800; sc.render.resolution_y=1280
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
cd=bpy.data.cameras.new('C'); cd.type='ORTHO'; cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
center=(lo+hi)/2; d=max(hi-lo)*3
def shot(name,x,y,rz,z=None,scale=None):
    cd.ortho_scale=scale or H*1.15; cam.location=Vector((center.x+x*d,center.y+y*d,center.z if z is None else z)); cam.rotation_euler=(math.pi/2,0,rz)
    sc.render.filepath=os.path.join(out,name+'.png'); bpy.ops.render.render(write_still=True)
shot('rest_front',0,-1,0)
# wireframe
wire=body.copy(); wire.data=body.data.copy(); bpy.context.scene.collection.objects.link(wire); wire.parent=arm; wire.matrix_parent_inverse=body.matrix_parent_inverse.copy()
mod=wire.modifiers.new('wire','WIREFRAME'); mod.thickness=cm*0.08; mod.use_replace=True; wm=bpy.data.materials.new('wire'); wm.use_nodes=True; wm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.02,0.02,0.02,1)
wire.data.materials.clear(); wire.data.materials.append(wm)
shot('wire_front',0,-1,0); shot('wire_upper',0,-1,0,z=lo.z+H*0.8,scale=H*0.45); wire.hide_render=True
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='POSE')
def rot(name,x=0,y=0,z=0):
    pb=arm.pose.bones[name]; pb.rotation_mode='XYZ'; pb.rotation_euler=Euler((math.radians(x),math.radians(y),math.radians(z)),'XYZ')
rot('J_Bip_L_UpperArm',z=-40); rot('J_Bip_R_UpperArm',z=40); rot('J_Bip_L_LowerArm',y=-70); rot('J_Bip_R_LowerArm',y=70)
rot('J_Bip_C_Head',y=30,x=10); rot('J_Bip_C_Neck',y=10); rot('J_Bip_L_UpperLeg',x=-40); rot('J_Bip_L_LowerLeg',x=50); rot('J_Bip_C_Spine',z=10)
bpy.ops.object.mode_set(mode='OBJECT')
shot('pose_front',0,-1,0); shot('pose_side',-1,0,-math.pi/2); shot('pose_upper',0,-1,0,z=lo.z+H*0.8,scale=H*0.45)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,'body_build.blend')); print('done')
