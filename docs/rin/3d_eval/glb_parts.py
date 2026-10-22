"""Рендер GLB з частинами різного кольору: 4 ракурси + обличчя; список частин з габаритами.
blender -b -P glb_parts.py -- <model.glb> <out_dir>"""
import bpy, sys, os, math, colorsys
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]; src,out=argv[0],argv[1]; os.makedirs(out,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
objs=[o for o in bpy.data.objects if o.type=='MESH']
lo=Vector((1e9,)*3); hi=Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); lo=Vector(map(min,lo,w)); hi=Vector(map(max,hi,w))
dim=hi-lo; H=dim.z; center=(lo+hi)/2
with open(os.path.join(out,'parts.txt'),'w') as f:
    for i,o in enumerate(sorted(objs,key=lambda o:-len(o.data.vertices))):
        bl=Vector((1e9,)*3); bh=Vector((-1e9,)*3)
        for c in o.bound_box:
            w=o.matrix_world@Vector(c); bl=Vector(map(min,bl,w)); bh=Vector(map(max,bh,w))
        tris=sum(len(p.vertices)-2 for p in o.data.polygons); quads=sum(1 for p in o.data.polygons if len(p.vertices)==4)
        hue=(i*0.137)%1.0; r,g,b_=colorsys.hsv_to_rgb(hue,0.75,0.95)
        m=bpy.data.materials.new(f'p{i}'); m.use_nodes=True
        n=m.node_tree.nodes['Principled BSDF']; n.inputs['Base Color'].default_value=(r,g,b_,1); n.inputs['Roughness'].default_value=1
        o.data.materials.clear(); o.data.materials.append(m)
        f.write(f'{i:2d} {o.name:16s} verts {len(o.data.vertices):6d} tris {tris:6d} quads {quads:6d} | z {(bl.z-lo.z)/H:.2f}..{(bh.z-lo.z)/H:.2f} x {bl.x/dim.x*2:+.2f}..{bh.x/dim.x*2:+.2f} y {bl.y/dim.y*2:+.2f}..{bh.y/dim.y*2:+.2f} | colour hue {hue:.2f}\n')
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.device='CPU'; sc.render.film_transparent=True
sc.view_settings.view_transform='Standard'; sc.render.resolution_x=800; sc.render.resolution_y=1280
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
cd=bpy.data.cameras.new('C'); cd.type='ORTHO'; cd.ortho_scale=H*1.1; cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
d=max(dim)*3
for name,(x,y,rz) in {'front':(0,-1,0),'back':(0,1,math.pi),'left':(-1,0,-math.pi/2),'right':(1,0,math.pi/2)}.items():
    cam.location=center+Vector((x,y,0))*d; cam.rotation_euler=(math.pi/2,0,rz); sc.render.filepath=os.path.join(out,name+'.png'); bpy.ops.render.render(write_still=True)
cd.ortho_scale=H*0.24; sc.render.resolution_y=800
for name,(x,y,rz) in {'face':(0,-1,0),'face_side':(-1,0,-math.pi/2),'face_back':(0,1,math.pi)}.items():
    cam.location=Vector((center.x+x*d,center.y+y*d,lo.z+H*0.9)); cam.rotation_euler=(math.pi/2,0,rz); sc.render.filepath=os.path.join(out,name+'.png'); bpy.ops.render.render(write_still=True)
print('done')
