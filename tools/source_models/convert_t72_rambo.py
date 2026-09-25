# Converts the owner's t72.obj into tools/source_models/t72_rambo.glb:
# names the parts, drops the floating label, removes the rear fuel drums, their
# mounts, the unditching log and the turret machine gun, fills the missing lower hull sides, and writes normals
# (split along sharp edges). Run from the folder with t72.obj:
#   python3 convert_t72_rambo.py <out.glb>
import trimesh, numpy as np, sys
sc = trimesh.load('t72.obj', force='scene', group_material=False, split_object=True, process=False)

def is_rear_drum_part(p):
    b = p.bounds  # file forward is -X, so the rear is at large +X
    return b[0][0] >= 3.3 and b[1][1] > 1.0


def is_log(p):
    # unditching log: a cylinder across the whole rear, low on the stern plate,
    # and the small brackets it hangs from
    b = p.bounds
    log = b[0][0] >= 3.4 and b[1][2] - b[0][2] > 2.5 and b[1][1] < 1.2
    brackets = b[0][0] >= 3.1 and b[1][1] < 1.05 and b[1][2] - b[0][2] < 0.7
    return log or brackets

def is_machine_gun(p):
    # NSVT on the commander's cupola (it points backwards in this model):
    # barrel, receiver, cradle and ammo box sit above the cupola, behind it.
    b = p.bounds
    return b[0][0] >= 0.88 and b[0][1] >= 2.2 and b[0][2] >= -1.06 and b[1][2] <= -0.5


out = trimesh.Scene()
removed = 0
for name, g in sc.geometry.items():
    b = g.bounds; c = b.mean(axis=0); nf = len(g.faces)
    if b[0][2] == 0 and b[1][2] == 0: continue          # floating "Text001" label
    side = 'R' if c[2] < 0 else 'L'
    if name.endswith('_11'): n = 'Turret'
    elif name.endswith('_15'): n = 'Gun'
    elif name.endswith('_12'): n = 'Hull'
    elif nf == 136: n = 'Track_' + side
    elif nf == 1552: n = 'Sprocket_' + side
    elif nf == 1082: n = 'Idler_' + side
    elif nf == 256: n = 'Wheel_%s_%+.1f' % (side, c[0])
    else: n = name
    uv = g.visual.uv if hasattr(g.visual, 'uv') else None
    m = trimesh.Trimesh(vertices=g.vertices, faces=g.faces,
        visual=trimesh.visual.TextureVisuals(uv=uv) if uv is not None else None, process=False)
    if n == 'Turret':
        m.merge_vertices()
        parts = m.split(only_watertight=False)
        keep = [p for p in parts if not is_machine_gun(p)]
        print("removed machine gun parts:", len(parts) - len(keep))
        m = trimesh.util.concatenate(keep)
    if n == 'Hull':
        m.merge_vertices()
        parts = m.split(only_watertight=False)
        keep = [p for p in parts if not is_rear_drum_part(p) and not is_log(p)]
        removed = len(parts) - len(keep)
        m = trimesh.util.concatenate(keep)
    m = trimesh.graph.smooth_shade(m, angle=np.radians(35))
    _ = m.vertex_normals
    out.add_geometry(m, node_name=n, geom_name=n)
# The game model has no lower hull sides behind the road wheels (the background
# showed through between them); fill that space with a plain box.
# Its rear face doubles as the stern plate, which the log used to hide.
lower = trimesh.creation.box(extents=[5.75, 0.7, 2.1])  # behind the wheels, clear of the glacis
lower.apply_translation([0.575, 0.65, 0.0])
lower.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(lower.vertices), 2)))
out.add_geometry(lower, node_name='HullLower', geom_name='HullLower')
out.export(sys.argv[1], include_normals=True)
print("removed rear drum parts:", removed)
