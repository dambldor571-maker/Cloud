extends RefCounted
## Mesh-building helpers for procedural unit models (used only by tools/).
## Units: 1.0 = 1 metre. Vehicles face +X, Y is up.

var _mats := {}


func mat(c: Color, rough := 0.8, metal := 0.0, grime: Texture2D = null) -> StandardMaterial3D:
	var key := [c, rough, metal, grime]
	if not _mats.has(key):
		var m := StandardMaterial3D.new()
		m.albedo_color = c
		m.roughness = rough
		m.metallic = metal
		if grime:
			m.albedo_texture = grime
			m.uv1_triplanar = true
			m.uv1_scale = Vector3(0.6, 0.6, 0.6)
		_mats[key] = m
	return _mats[key]


## Seamless grey noise (values around 1.0) that makes paint look worn and dirty.
static func grime_texture(seed_value: int, lo := 0.72, hi := 1.08, freq := 0.03) -> ImageTexture:
	var n := FastNoiseLite.new()
	n.seed = seed_value
	n.frequency = freq
	n.fractal_octaves = 5
	var img := n.get_seamless_image(256, 256)
	img.convert(Image.FORMAT_RGB8)
	for y in 256:
		for x in 256:
			var v := lerpf(lo, hi, img.get_pixel(x, y).r)
			img.set_pixel(x, y, Color(v, v, v))
	return ImageTexture.create_from_image(img)


func add(parent: Node3D, mesh: Mesh, m: Material, pos := Vector3.ZERO, rot := Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = m
	mi.position = pos
	mi.rotation_degrees = rot
	parent.add_child(mi)
	return mi


func box(p: Node3D, size: Vector3, pos: Vector3, m: Material, rot := Vector3.ZERO) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	return add(p, mesh, m, pos, rot)


## Cylinder along local Y; use rot to lay it down (Z=90 -> along X, X=90 -> along Z).
func cyl(p: Node3D, r: float, h: float, pos: Vector3, m: Material, rot := Vector3.ZERO,
		r_top := -1.0, segments := 24) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.bottom_radius = r
	mesh.top_radius = r if r_top < 0.0 else r_top
	mesh.height = h
	mesh.radial_segments = segments
	mesh.rings = 1
	return add(p, mesh, m, pos, rot)


func sphere(p: Node3D, r: float, pos: Vector3, m: Material, scale := Vector3.ONE) -> MeshInstance3D:
	var mesh := SphereMesh.new()
	mesh.radius = r
	mesh.height = r * 2.0
	var mi := add(p, mesh, m, pos)
	mi.scale = scale
	return mi


## Prism from a side profile (polygon in X/Y) extruded across Z from z0 to z1. Flat shaded.
func extrude(p: Node3D, profile: PackedVector2Array, z0: float, z1: float, m: Material,
		pos := Vector3.ZERO) -> MeshInstance3D:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var tris := Geometry2D.triangulate_polygon(profile)
	for cap in [[z1, false], [z0, true]]:
		var z: float = cap[0]
		for i in range(0, tris.size(), 3):
			var a := profile[tris[i]]
			var b := profile[tris[i + 1]]
			var c := profile[tris[i + 2]]
			var order := [a, c, b] if cap[1] else [a, b, c]
			if Geometry2D.is_polygon_clockwise(profile):
				order.reverse()
			for v in order:
				st.add_vertex(Vector3(v.x, v.y, z))
	var n := profile.size()
	var cw := Geometry2D.is_polygon_clockwise(profile)
	for i in n:
		var a := profile[i]
		var b := profile[(i + 1) % n]
		var quad := [Vector3(a.x, a.y, z0), Vector3(b.x, b.y, z0), Vector3(b.x, b.y, z1), Vector3(a.x, a.y, z1)]
		if cw:
			quad.reverse()
		for k in [0, 1, 2, 0, 2, 3]:
			st.add_vertex(quad[k])
	st.generate_normals()
	return add(p, st.commit(), m, pos)


## Closed smooth surface from rings: rings[i] is a loop of points; first/last rings get capped.
func loft(p: Node3D, rings: Array, m: Material, pos := Vector3.ZERO, smooth := true) -> MeshInstance3D:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	if smooth:
		st.set_smooth_group(0)
	else:
		st.set_smooth_group(-1)
	var seg: int = rings[0].size()
	for i in rings.size() - 1:
		var r0: PackedVector3Array = rings[i]
		var r1: PackedVector3Array = rings[i + 1]
		for j in seg:
			var j1 := (j + 1) % seg
			for v in [r0[j], r1[j], r1[j1], r0[j], r1[j1], r0[j1]]:
				st.add_vertex(v)
	st.set_smooth_group(-1)
	# Caps: fan around the ring centroid.
	for cap in [[rings[0], true], [rings[rings.size() - 1], false]]:
		var ring: PackedVector3Array = cap[0]
		var c := Vector3.ZERO
		for v in ring:
			c += v
		c /= ring.size()
		for j in seg:
			var j1 := (j + 1) % seg
			if cap[1]:
				for v in [c, ring[j1], ring[j]]:
					st.add_vertex(v)
			else:
				for v in [c, ring[j], ring[j1]]:
					st.add_vertex(v)
	st.generate_normals()
	return add(p, st.commit(), m, pos)
