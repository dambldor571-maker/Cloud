"""Перевірка квад-тіла на шипи/перевернуті грані, виправлення, рендери з чистої пози, експорт.
blender -b -P body_check_fix.py -- <rin_body_v1.blend> <voxel_union.obj> <out_dir>"""
import bpy, sys, os, math, bmesh
from mathutils import Vector, Euler
from mathutils.bvhtree import BVHTree
argv=sys.argv[sys.argv.index('--')+1:]; blend,vox_obj,out=argv[0],argv[1],argv[2]; os.makedirs(out,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]; body=bpy.data.objects['Body']; hair=bpy.data.objects['Hair']; eyes=bpy.data.objects['Eyes']
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT'); bpy.ops.pose.transforms_clear(); bpy.ops.object.mode_set(mode='OBJECT')
# еталон: воксельна поверхня
bpy.ops.wm.obj_import(filepath=vox_obj); vox=bpy.context.selected_objects[0]
bvh=BVHTree.FromObject(vox,bpy.context.evaluated_depsgraph_get())
bm=bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
H=0.98; cm=H/170
dists=[]
for v in bm.verts:
    loc,n,i,dist=bvh.find_nearest(v.co); dists.append(dist)
import statistics
print('dist to voxel surface: median %.4f cm, max %.3f cm, >0.5cm: %d, >1cm: %d'%(statistics.median(dists)/cm,max(dists)/cm,sum(1 for d in dists if d>0.5*cm),sum(1 for d in dists if d>1*cm)))
# перевернуті грані: нормаль грані проти нормалі еталона
flipped=0
for f in bm.faces:
    loc,n,i,dist=bvh.find_nearest(f.calc_center_median())
    if f.normal.dot(n)<0: flipped+=1
print('faces with normal opposite to reference:',flipped,'of',len(bm.faces))
# виправлення: вершини-шипи притягнути до еталона
fixed=0
for v,dd in zip(bm.verts,dists):
    if dd>0.5*cm:
        loc,n,i,dist=bvh.find_nearest(v.co); v.co=loc; fixed+=1
bm.to_mesh(body.data); bm.free(); body.data.update(); print('snapped spike verts',fixed)
bpy.data.objects.remove(vox)
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
# рендери
objs=[o for o in bpy.data.objects if o.type=='MESH']
lo=Vector((1e9,)*3); hi=Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); lo=Vector(map(min,lo,w)); hi=Vector(map(max,hi,w))
H=hi.z-lo.z; center=(lo+hi)/2; d=max(hi-lo)*3; cm=H/170
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.device='CPU'; sc.render.film_transparent=True
sc.view_settings.view_transform='Standard'; sc.render.resolution_x=800; sc.render.resolution_y=1280
if not sc.world:
    w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
cam=sc.camera
if not cam:
    cd=bpy.data.cameras.new('C'); cd.type='ORTHO'; cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
cd=cam.data
def shot(name,x,y,rz,z=None,scale=None,x0=None):
    cd.ortho_scale=scale or H*1.15; cam.location=Vector(((center.x if x0 is None else x0)+x*d,center.y+y*d,center.z if z is None else z)); cam.rotation_euler=(math.pi/2,0,rz)
    sc.render.filepath=os.path.join(out,name+'.png'); bpy.ops.render.render(write_still=True)
# положення правої кисті у спокої
hand=arm.matrix_world@arm.pose.bones['J_Bip_R_Hand'].head
shot('rest_front',0,-1,0); shot('rest_side',-1,0,-math.pi/2); shot('rest_upper',0,-1,0,z=lo.z+H*0.8,scale=H*0.45); shot('rest_hand',0,-1,0,z=hand.z,scale=H*0.14,x0=hand.x)
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='POSE')
def rot(name,x=0,y=0,z=0):
    pb=arm.pose.bones[name]; pb.rotation_mode='XYZ'; pb.rotation_euler=Euler((math.radians(x),math.radians(y),math.radians(z)),'XYZ')
rot('J_Bip_L_UpperArm',z=-40); rot('J_Bip_R_UpperArm',z=40); rot('J_Bip_L_LowerArm',y=-70); rot('J_Bip_R_LowerArm',y=70)
rot('J_Bip_C_Head',y=30,x=10); rot('J_Bip_C_Neck',y=10); rot('J_Bip_L_UpperLeg',x=-40); rot('J_Bip_L_LowerLeg',x=50); rot('J_Bip_C_Spine',z=10)
for f in ('Index','Middle','Ring','Little'):
    for s in (1,2,3): rot(f'J_Bip_R_{f}{s}',x=50)
rot('J_Bip_R_Thumb2',x=30)
bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()
hand=arm.matrix_world@arm.pose.bones['J_Bip_R_Hand'].head
shot('pose_front',0,-1,0); shot('pose_side',-1,0,-math.pi/2); shot('pose_upper',0,-1,0,z=lo.z+H*0.8,scale=H*0.45); shot('pose_hand',0,-1,0,z=hand.z,scale=H*0.14,x0=hand.x)
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT'); bpy.ops.pose.transforms_clear(); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,'rin_body_v1.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in [arm]+objs: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(out,'rin_body_v1.glb'),use_selection=True,export_format='GLB',export_skins=True,export_animations=False,export_yup=True)
print('done')
