"""Фінальна збірка тіла: квад-меш (OBJ) + ваги з Body_src + риг + волосся/очі з оригіналу → рендери + GLB.
blender -b -P body_final.py -- <body_build.blend> <body_quad.obj> <out_dir>"""
import bpy, sys, os, math, bmesh
from mathutils import Vector, Euler
argv=sys.argv[sys.argv.index('--')+1:]; blend,quad_obj,out=argv[0],argv[1],argv[2]; os.makedirs(out,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]; src=bpy.data.objects['Body_src']
for o in list(bpy.data.objects):
    if o.name in ('Body','Body.001') or o.name.startswith('Vox'): bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=quad_obj); body=bpy.context.selected_objects[0]; body.name='Body'; body.data.name='Body'
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=0.003); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.shade_smooth()
bm=bmesh.new(); bm.from_mesh(body.data); print('BODY faces',len(bm.faces),'quads',sum(1 for f in bm.faces if len(f.verts)==4),'tris-equiv',sum(len(f.verts)-2 for f in bm.faces),'non-manifold',sum(1 for e in bm.edges if not e.is_manifold)); bm.free()
# ваги
dt=body.modifiers.new('dt','DATA_TRANSFER'); dt.object=src; dt.use_vert_data=True; dt.data_types_verts={'VGROUP_WEIGHTS'}; dt.vert_mapping='POLYINTERP_NEAREST'; dt.layers_vgroup_select_src='ALL'; dt.mix_mode='REPLACE'
bpy.ops.object.datalayout_transfer(modifier='dt'); bpy.ops.object.modifier_apply(modifier='dt')
bpy.ops.object.vertex_group_limit_total(limit=4); bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT'); bpy.ops.object.vertex_group_smooth(group_select_mode='ALL',factor=0.5,repeat=2); bpy.ops.object.mode_set(mode='OBJECT')
body.parent=arm; body.matrix_parent_inverse=arm.matrix_world.inverted(); am=body.modifiers.new('Armature','ARMATURE'); am.object=arm
m=bpy.data.materials.new('Skin'); m.use_nodes=True; n=m.node_tree.nodes['Principled BSDF']; n.inputs['Base Color'].default_value=(0.93,0.80,0.72,1); n.inputs['Roughness'].default_value=1
body.data.materials.clear(); body.data.materials.append(m)
# класифікація частин голови: волосся / очі / інше
BODY=['tripo_part_%d'%i for i in (0,2,1,3,5,4,9,6,8,7,10,16,17,12,11)]
EYES=['tripo_part_35','tripo_part_40']
hair=[]; eyes=[]; other=[]
for o in bpy.data.objects:
    if o.type!='MESH' or o.name=='Body' or o.name=='Body_src': continue
    if o.name in BODY: bpy.data.objects.remove(o); continue
    if o.name in EYES: eyes.append(o)
    elif o.name=='tripo_part_41': other.append(o)
    else: hair.append(o)
bpy.data.objects.remove(src)
# злити волосся в один меш, очі в один
def join(objs,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]; bpy.ops.object.join(); j=bpy.context.active_object; j.name=name; j.data.name=name; return j
hairo=join(hair,'Hair'); eyeo=join(eyes,'Eyes')
for o in other: o.name='Misc'
for o in (hairo,eyeo)+tuple(other):
    for ms in o.material_slots:
        if ms.material and ms.material.use_nodes:
            for nd in ms.material.node_tree.nodes:
                if nd.type=='BSDF_PRINCIPLED':
                    nd.inputs['Roughness'].default_value=1
                    for k in ('Specular IOR Level','Specular'):
                        if k in nd.inputs: nd.inputs[k].default_value=0
print('HAIR tris',sum(len(p.vertices)-2 for p in hairo.data.polygons),'EYES tris',sum(len(p.vertices)-2 for p in eyeo.data.polygons))
# сцена
objs=[o for o in bpy.data.objects if o.type=='MESH']
lo=Vector((1e9,)*3); hi=Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); lo=Vector(map(min,lo,w)); hi=Vector(map(max,hi,w))
H=hi.z-lo.z; center=(lo+hi)/2; d=max(hi-lo)*3; cm=H/170
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.device='CPU'; sc.render.film_transparent=True
sc.view_settings.view_transform='Standard'; sc.render.resolution_x=800; sc.render.resolution_y=1280
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
cd=bpy.data.cameras.new('C'); cd.type='ORTHO'; cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
def shot(name,x,y,rz,z=None,scale=None):
    cd.ortho_scale=scale or H*1.15; cam.location=Vector((center.x+x*d,center.y+y*d,center.z if z is None else z)); cam.rotation_euler=(math.pi/2,0,rz)
    sc.render.filepath=os.path.join(out,name+'.png'); bpy.ops.render.render(write_still=True)
shot('rest_front',0,-1,0); shot('rest_side',-1,0,-math.pi/2)
wire=body.copy(); wire.data=body.data.copy(); bpy.context.scene.collection.objects.link(wire); wire.parent=arm; wire.matrix_parent_inverse=body.matrix_parent_inverse.copy()
mod=wire.modifiers.new('wire','WIREFRAME'); mod.thickness=cm*0.1; mod.use_replace=True; wm=bpy.data.materials.new('wire'); wm.use_nodes=True; wm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.02,0.02,0.02,1)
wire.data.materials.clear(); wire.data.materials.append(wm); hairo.hide_render=True; eyeo.hide_render=True
shot('wire_front',0,-1,0); shot('wire_upper',0,-1,0,z=lo.z+H*0.78,scale=H*0.45); shot('wire_hand',0,-1,0,z=lo.z+H*0.5,scale=H*0.2)
bpy.data.objects.remove(wire); hairo.hide_render=False; eyeo.hide_render=False
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='POSE')
def rot(name,x=0,y=0,z=0):
    pb=arm.pose.bones[name]; pb.rotation_mode='XYZ'; pb.rotation_euler=Euler((math.radians(x),math.radians(y),math.radians(z)),'XYZ')
rot('J_Bip_L_UpperArm',z=-40); rot('J_Bip_R_UpperArm',z=40); rot('J_Bip_L_LowerArm',y=-70); rot('J_Bip_R_LowerArm',y=70)
rot('J_Bip_C_Head',y=30,x=10); rot('J_Bip_C_Neck',y=10); rot('J_Bip_L_UpperLeg',x=-40); rot('J_Bip_L_LowerLeg',x=50); rot('J_Bip_C_Spine',z=10)
for f in ('Index','Middle','Ring','Little'):
    for s in (1,2,3): rot(f'J_Bip_R_{f}{s}',x=45)
bpy.ops.object.mode_set(mode='OBJECT')
shot('pose_front',0,-1,0); shot('pose_side',-1,0,-math.pi/2); shot('pose_upper',0,-1,0,z=lo.z+H*0.78,scale=H*0.45); shot('pose_hand',1,0,math.pi/2,z=lo.z+H*0.5,scale=H*0.2)
# скинути позу і експортувати
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT'); bpy.ops.pose.transforms_clear(); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,'rin_body_v1.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in (arm,body,hairo,eyeo)+tuple(other): o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(out,'rin_body_v1.glb'),use_selection=True,export_format='GLB',export_skins=True,export_animations=False,export_yup=True)
print('done')
