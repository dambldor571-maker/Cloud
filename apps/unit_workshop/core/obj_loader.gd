class_name ObjLoader
## Minimal Wavefront OBJ reader for the running program (Godot imports OBJ only
## in the editor): positions, normals, UVs, polygons; each o/g block becomes
## its own MeshInstance3D named after it. Materials are not read.


static func load_obj(path: String) -> Node3D:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return null
	var root := Node3D.new()
	root.name = path.get_file().get_basename()
	var v: PackedVector3Array = []
	var vt: PackedVector2Array = []
	var vn: PackedVector3Array = []
	var st: SurfaceTool = null
	var part := "Part"
	var has_normals := false
	var count := 0
	while not f.eof_reached():
		var line := f.get_line().strip_edges()
		if line.is_empty() or line.begins_with("#"):
			continue
		var t := line.split(" ", false)
		match t[0]:
			"v":
				v.append(Vector3(float(t[1]), float(t[2]), float(t[3])))
			"vt":
				vt.append(Vector2(float(t[1]), 1.0 - float(t[2])))
			"vn":
				vn.append(Vector3(float(t[1]), float(t[2]), float(t[3])))
			"o", "g":
				_flush(root, st, part, has_normals)
				st = null
				part = line.substr(2).strip_edges() if t.size() > 1 else "Part%d" % count
				count += 1
			"f":
				if st == null:
					st = SurfaceTool.new()
					st.begin(Mesh.PRIMITIVE_TRIANGLES)
					has_normals = true
				var corners := []
				for k in range(1, t.size()):
					var idx := t[k].split("/")
					var c := {"v": _index(idx[0], v.size())}
					if idx.size() > 1 and idx[1] != "":
						c["t"] = _index(idx[1], vt.size())
					if idx.size() > 2 and idx[2] != "":
						c["n"] = _index(idx[2], vn.size())
					else:
						has_normals = false
					corners.append(c)
				for k in range(1, corners.size() - 1):
					# OBJ winds counter-clockwise, Godot's front faces are clockwise
					for c in [corners[0], corners[k + 1], corners[k]]:
						if c.has("t"):
							st.set_uv(vt[c["t"]])
						if c.has("n"):
							st.set_normal(vn[c["n"]])
						st.add_vertex(v[c["v"]])
	_flush(root, st, part, has_normals)
	return root if root.get_child_count() > 0 else null


static func _index(s: String, n: int) -> int:
	var i := int(s)
	return i - 1 if i > 0 else n + i


static func _flush(root: Node3D, st: SurfaceTool, part: String, has_normals: bool) -> void:
	if st == null:
		return
	if not has_normals:
		st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.name = part.validate_node_name()
	mi.mesh = st.commit()
	if mi.mesh.get_surface_count() == 0:
		mi.free()
		return
	root.add_child(mi)
