"""Класифікація частин ригованої моделі за домінантною кісткою і положенням → parts.json
blender -b -P classify_parts.py -- <model.glb> <out.json>"""
import bpy, sys, json
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]; src,out=argv[0],argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
objs=[o for o in bpy.data.objects if o.type=='MESH']; arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
lo=Vector((1e9,)*3); hi=Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); lo=Vector(map(min,lo,w)); hi=Vector(map(max,hi,w))
H=hi.z-lo.z
res=[]
for o in objs:
    m=o.data; vg={g.index:g.name for g in o.vertex_groups}; tot={}
    for v in m.vertices:
        for g in v.groups:
            if g.weight>0.05: tot[vg[g.group]]=tot.get(vg[g.group],0)+g.weight
    top=sorted(tot.items(),key=lambda x:-x[1])[:3]
    bl=Vector((1e9,)*3); bh=Vector((-1e9,)*3)
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); bl=Vector(map(min,bl,w)); bh=Vector(map(max,bh,w))
    tris=sum(len(p.vertices)-2 for p in m.polygons)
    imgs=[n.image.name for ms in o.material_slots if ms.material for n in ms.material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
    res.append({'name':o.name,'verts':len(m.vertices),'tris':tris,'bones':[b for b,_ in top],'z':[round((bl.z-lo.z)/H,3),round((bh.z-lo.z)/H,3)],'x':[round(bl.x,3),round(bh.x,3)],'y':[round(bl.y,3),round(bh.y,3)],'images':imgs,'img_size':[list(bpy.data.images[i].size) for i in imgs]})
json.dump({'H':H,'lo':list(lo),'hi':list(hi),'parts':res},open(out,'w'),indent=1)
print('parts',len(res))
