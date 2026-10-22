"""Тест рига: рендер у спокої і в тестовій позі + позиції кісток.
blender -b -P rig_test.py -- <model.glb> <out_dir>"""
import bpy, sys, os, math, json
from mathutils import Vector, Euler
argv=sys.argv[sys.argv.index('--')+1:]; src,out=argv[0],argv[1]; os.makedirs(out,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
objs=[o for o in bpy.data.objects if o.type=='MESH']; arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
lo=Vector((1e9,)*3); hi=Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); lo=Vector(map(min,lo,w)); hi=Vector(map(max,hi,w))
dim=hi-lo; H=dim.z; center=(lo+hi)/2
# матеріали без блиску
for o in objs:
    for ms in o.material_slots:
        if ms.material and ms.material.use_nodes:
            for n in ms.material.node_tree.nodes:
                if n.type=='BSDF_PRINCIPLED':
                    n.inputs['Roughness'].default_value=1
                    for k in ('Specular IOR Level','Specular'):
                        if k in n.inputs: n.inputs[k].default_value=0
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.device='CPU'; sc.render.film_transparent=True
sc.view_settings.view_transform='Standard'; sc.render.resolution_x=800; sc.render.resolution_y=1280
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
cd=bpy.data.cameras.new('C'); cd.type='ORTHO'; cd.ortho_scale=H*1.15; cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
d=max(dim)*3
def shot(name,x,y,rz,z=None,scale=None):
    cd.ortho_scale=scale or H*1.15
    cam.location=Vector((center.x+x*d,center.y+y*d,center.z if z is None else z)); cam.rotation_euler=(math.pi/2,0,rz)
    sc.render.filepath=os.path.join(out,name+'.png'); bpy.ops.render.render(write_still=True)
# кістки у світових координатах (спокій)
bones={}
for pb in arm.pose.bones:
    h=arm.matrix_world@pb.head; t=arm.matrix_world@pb.tail; bones[pb.name]=[list(h),list(t)]
json.dump({'bones':bones,'lo':list(lo),'hi':list(hi),'ortho':H*1.15,'center':list(center)},open(os.path.join(out,'bones.json'),'w'))
shot('rest_front',0,-1,0); shot('rest_face',0,-1,0,z=lo.z+H*0.9,scale=H*0.24); shot('rest_side',-1,0,-math.pi/2)
# тестова поза
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='POSE')
def rot(name,x=0,y=0,z=0):
    pb=arm.pose.bones.get(name)
    if not pb: print('no bone',name); return
    pb.rotation_mode='XYZ'; pb.rotation_euler=Euler((math.radians(x),math.radians(y),math.radians(z)),'XYZ')
# руки вниз і лікті зігнуті, голова повернута, нога вперед і коліно
rot('J_Bip_L_UpperArm',z=-40); rot('J_Bip_R_UpperArm',z=40)
rot('J_Bip_L_LowerArm',y=-70); rot('J_Bip_R_LowerArm',y=70)
rot('J_Bip_C_Head',y=30,x=10); rot('J_Bip_C_Neck',y=10)
rot('J_Bip_L_UpperLeg',x=-40); rot('J_Bip_L_LowerLeg',x=50)
rot('J_Bip_C_Spine',z=10)
bpy.ops.object.mode_set(mode='OBJECT')
shot('pose_front',0,-1,0); shot('pose_side',-1,0,-math.pi/2); shot('pose_face',0,-1,0,z=lo.z+H*0.9,scale=H*0.3)
print('done')
