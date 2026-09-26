extends SceneTree
## Run: OUT=/path/out.png xvfb-run godot --path . --rendering-method forward_plus -s res://tools/references/map_style_civ5.gd
## Reference diorama of a Civ5-style pseudo-3D map, rendered with the unit
## camera (orthographic, 65 degrees) and sun (north-east, 75 degrees).

const R := 5.5  # hex radius in metres (48 px in game at 8.73 px/m)
const COLS := 11
const ROWS := 8
const PX_PER_M := 17.45  # 2x the in-game unit scale
const OUT := Vector2i(1600, 1000)
const SS := 2
const ELEV := 65.0

# terrain codes
const G := 0  # grassland
const P := 1  # plains (drier)
const F := 2  # forest
const H := 3  # hills
const M := 4  # mountains
const W := 5  # water
const C := 6  # city
const A := 7  # farmland

# rows top (north) to bottom (south); odd-r offset like the game
var MAP := [
	[G, F, F, G, P, P, H, M, M, M, H],
	[G, F, F, F, A, P, H, H, M, M, H],
	[F, F, G, A, A, C, A, P, H, H, P],
	[G, G, A, A, C, C, A, G, P, F, F],
	[W, G, G, A, A, A, G, G, F, F, F],
	[W, W, G, G, H, G, P, G, G, F, G],
	[W, W, W, G, H, H, G, W, W, G, G],
	[W, W, W, W, G, G, G, W, W, G, G],
]

var noise := FastNoiseLite.new()
var noise2 := FastNoiseLite.new()
var centers := []  # [pos2d, terrain]
var rng := RandomNumberGenerator.new()


func axial_to_world(q: int, r: int) -> Vector2:
	return Vector2(R * sqrt(3.0) * (q + r / 2.0), R * 1.5 * r)


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	noise.seed = 7
	noise.frequency = 0.08
	noise.fractal_octaves = 4
	noise2.seed = 21
	noise2.frequency = 0.35
	rng.seed = 5
	for row in ROWS:
		for col in COLS:
			var q := col - ((row - (row & 1)) >> 1)
			centers.append([axial_to_world(q, row), MAP[row][col]])

	var vp := SubViewport.new()
	vp.size = OUT * SS
	vp.own_world_3d = true
	vp.msaa_3d = Viewport.MSAA_4X
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(vp)

	var mid := axial_to_world(0, 0) + Vector2(R * sqrt(3.0) * (COLS - 0.5) / 2.0, R * 1.5 * (ROWS - 1) / 2.0)
	var look := Vector3(mid.x, 0, mid.y)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = OUT.y / PX_PER_M
	cam.far = 500
	var e := deg_to_rad(ELEV)
	cam.position = look + Vector3(0, sin(e), cos(e)) * 120.0
	vp.add_child(cam)
	cam.look_at(look)

	var sun := DirectionalLight3D.new()
	sun.light_energy = 2.3
	sun.light_color = Color(1.0, 0.95, 0.85)
	var az := deg_to_rad(45.0)
	var el := deg_to_rad(75.0)
	vp.add_child(sun)
	sun.look_at_from_position(look + Vector3(cos(el) * sin(az), sin(el), -cos(el) * cos(az)) * 50.0, look)
	sun.shadow_enabled = true
	sun.shadow_blur = 0.8
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 250.0
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.1, 0.12, 0.15)
	var sky := Sky.new()
	sky.sky_material = ProceduralSkyMaterial.new()
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.4
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	env.ssao_radius = 1.2
	env.ssao_intensity = 2.5
	env.adjustment_enabled = true
	env.adjustment_saturation = 0.9
	env.adjustment_contrast = 1.06
	var we := WorldEnvironment.new()
	we.environment = env
	vp.add_child(we)

	vp.add_child(_ground())
	vp.add_child(_water())
	for c in centers:
		match c[1]:
			F:
				_forest(vp, c[0], 26)
			C:
				_city(vp, c[0])
			A:
				_farm(vp, c[0])
			G:
				if rng.randf() < 0.35:
					_forest(vp, c[0], rng.randi_range(1, 3))
	for i in 6:
		await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	img.resize(OUT.x, OUT.y, Image.INTERPOLATE_LANCZOS)
	img.save_png(OS.get_environment("OUT"))
	# screen positions (at output resolution) of some hex centres for unit overlays
	var marks := {}
	for key in ["3,4", "6,4", "7,3", "2,5", "5,6"]:
		var cr: PackedStringArray = key.split(",")
		var col := int(cr[0])
		var row := int(cr[1])
		var q := col - ((row - (row & 1)) >> 1)
		var p := axial_to_world(q, row)
		var hh := height(p.x, p.y)
		var s := cam.unproject_position(Vector3(p.x, hh, p.y)) / SS
		marks[key] = [s.x, s.y]
	print("MARKS ", JSON.stringify(marks))
	quit()


# --- terrain field ------------------------------------------------------------

func weights(x: float, z: float) -> Array:
	# soft membership of the point in each terrain type
	var acc := {}
	var total := 0.0
	var p := Vector2(x, z)
	for c in centers:
		var d: float = p.distance_to(c[0])
		if d > R * 2.2:
			continue
		var w := exp(-pow(d / (R * 0.62), 2.0))
		acc[c[1]] = acc.get(c[1], 0.0) + w
		total += w
	for k in acc:
		acc[k] /= total
	return [acc, total]


func height(x: float, z: float) -> float:
	var acc: Dictionary = weights(x, z)[0]
	var n := noise.get_noise_2d(x, z)
	var h := 0.15 * n
	h -= 1.6 * smoothstep(0.25, 0.75, acc.get(W, 0.0))
	# hills: a couple of rounded bumps per hill hex; mountains: one rocky peak each
	var p := Vector2(x, z)
	var hill := 0.0
	var mount := 0.0
	for c in centers:
		if c[1] != H and c[1] != M:
			continue
		var d: float = p.distance_to(c[0])
		if d > R * 1.3:
			continue
		if c[1] == H:
			for k in 3:
				var o: Vector2 = c[0] + Vector2(cos(k * 2.1 + c[0].x), sin(k * 2.1 + c[0].y)) * R * 0.38
				var dd := p.distance_to(o) / (R * 0.62)
				hill = maxf(hill, (3.2 - 0.4 * k) * exp(-dd * dd * 1.6))
		else:
			var ridge := 1.0 - absf(noise2.get_noise_2d(x * 0.7, z * 0.7))
			var t := clampf(1.0 - d / (R * 1.05), 0.0, 1.0)
			mount = maxf(mount, 9.5 * pow(t, 1.35) * (0.7 + 0.45 * ridge))
	h += hill * (0.85 + 0.3 * noise2.get_noise_2d(x * 0.5, z * 0.5))
	h += mount
	return h


func ground_color(x: float, z: float, h: float, nrm: Vector3) -> Color:
	var acc: Dictionary = weights(x, z)[0]
	var n := noise.get_noise_2d(x * 2.0, z * 2.0)
	var grass := Color(0.33, 0.44, 0.20).lerp(Color(0.40, 0.49, 0.22), 0.5 + 0.5 * n)
	var plains := Color(0.55, 0.52, 0.32).lerp(Color(0.48, 0.48, 0.28), 0.5 + 0.5 * n)
	var forest_floor := Color(0.22, 0.31, 0.14)
	var hill := Color(0.44, 0.44, 0.26)
	var rock := Color(0.42, 0.39, 0.35).lerp(Color(0.31, 0.29, 0.26), 0.5 + 0.5 * n)
	var city := Color(0.48, 0.46, 0.40)
	var fields := grass  # the field patchwork itself is drawn per pixel in the shader
	var c := Color(0, 0, 0)
	c += grass * acc.get(G, 0.0)
	c += plains * acc.get(P, 0.0)
	c += forest_floor * acc.get(F, 0.0)
	c += hill * acc.get(H, 0.0)
	c += rock * acc.get(M, 0.0)
	c += city * acc.get(C, 0.0)
	c += fields * acc.get(A, 0.0)
	c += Color(0.60, 0.56, 0.40) * acc.get(W, 0.0)  # shore sand / sea bed
	c.a = 1.0
	# steep slopes show rock, high peaks carry snow, the beach is sandy
	var steep := 1.0 - nrm.y
	c = c.lerp(rock, smoothstep(0.25, 0.55, steep))
	c = c.lerp(rock, smoothstep(1.5, 3.0, h))
	c = c.lerp(Color(0.90, 0.91, 0.93), smoothstep(6.6, 7.6, h + 1.2 * n))
	var sand := smoothstep(0.15, 0.35, acc.get(W, 0.0)) * (1.0 - smoothstep(0.55, 0.8, acc.get(W, 0.0)))
	c = c.lerp(Color(0.80, 0.74, 0.52), sand)
	c.a = acc.get(A, 0.0) * (1.0 - smoothstep(0.25, 0.55, steep))  # farmland weight for the shader
	return c


func _field_color(x: float, z: float) -> Color:
	# patchwork of fields in a slightly rotated grid
	var a := 0.35
	var u := x * cos(a) - z * sin(a)
	var v := x * sin(a) + z * cos(a)
	var cell := Vector2(floor(u / 2.6), floor(v / 1.8))
	var hsh := fposmod(sin(cell.x * 12.9898 + cell.y * 78.233) * 43758.5453, 1.0)
	var pal := [Color(0.66, 0.58, 0.28), Color(0.38, 0.50, 0.20), Color(0.47, 0.36, 0.22), Color(0.56, 0.55, 0.28), Color(0.33, 0.44, 0.18)]
	var col: Color = pal[int(hsh * pal.size()) % pal.size()]
	# furrows
	col = col.darkened(0.08 * (0.5 + 0.5 * sin(v * 12.0)))
	# hedges between fields
	var edge := minf(minf(fposmod(u, 2.6), 2.6 - fposmod(u, 2.6)), minf(fposmod(v, 1.8), 1.8 - fposmod(v, 1.8)))
	return col.lerp(Color(0.25, 0.36, 0.14), 1.0 - smoothstep(0.03, 0.12, edge))


func _ground() -> MeshInstance3D:
	var x0 := -R * 1.2
	var z0 := -R * 1.2
	var x1 := R * sqrt(3.0) * (COLS + 0.5) + R * 0.2
	var z1 := R * 1.5 * (ROWS - 1) + R * 1.2
	var step := 0.45
	var nx := int((x1 - x0) / step)
	var nz := int((z1 - z0) / step)
	var hs := PackedFloat32Array()
	hs.resize((nx + 1) * (nz + 1))
	for j in nz + 1:
		for i in nx + 1:
			hs[j * (nx + 1) + i] = height(x0 + i * step, z0 + j * step)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var verts := PackedVector3Array()
	var cols := PackedColorArray()
	for j in nz + 1:
		for i in nx + 1:
			var x := x0 + i * step
			var z := z0 + j * step
			var h := hs[j * (nx + 1) + i]
			var hl := hs[j * (nx + 1) + maxi(i - 1, 0)]
			var hr := hs[j * (nx + 1) + mini(i + 1, nx)]
			var hu := hs[maxi(j - 1, 0) * (nx + 1) + i]
			var hd := hs[mini(j + 1, nz) * (nx + 1) + i]
			var nrm := Vector3(hl - hr, 2.0 * step, hu - hd).normalized()
			verts.append(Vector3(x, h, z))
			cols.append(ground_color(x, z, h, nrm))
	var idx := PackedInt32Array()
	for j in nz:
		for i in nx:
			var a := j * (nx + 1) + i
			idx.append_array([a, a + 1, a + nx + 1, a + 1, a + nx + 2, a + nx + 1])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_COLOR] = cols
	arr[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	st.create_from(m, 0)
	st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var sm := ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode diffuse_burley;
uniform float hex_r = 5.5;
varying vec3 wp;
varying vec3 wn;
void vertex() {
	wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}
vec3 fields(vec2 p) {
	float a = 0.35;
	float u = p.x * cos(a) - p.y * sin(a);
	float v = p.x * sin(a) + p.y * cos(a);
	vec2 cell = floor(vec2(u / 2.6, v / 1.8));
	float h = fract(sin(dot(cell, vec2(12.9898, 78.233))) * 43758.5453);
	vec3 pal[5] = vec3[5](vec3(0.66, 0.58, 0.28), vec3(0.38, 0.50, 0.20), vec3(0.47, 0.36, 0.22), vec3(0.56, 0.55, 0.28), vec3(0.33, 0.44, 0.18));
	vec3 col = pal[int(h * 5.0) % 5];
	col *= 1.0 - 0.07 * (0.5 + 0.5 * sin(v * 14.0));  // furrows
	float eu = min(mod(u, 2.6), 2.6 - mod(u, 2.6));
	float ev = min(mod(v, 1.8), 1.8 - mod(v, 1.8));
	float edge = min(eu, ev);
	col = mix(vec3(0.22, 0.32, 0.13), col, smoothstep(0.03, 0.10, edge));  // hedgerows
	return col;
}
vec2 hex_round(vec2 qr) {
	vec3 c = vec3(qr.x, qr.y, -qr.x - qr.y);
	vec3 r = round(c);
	vec3 d = abs(r - c);
	if (d.x > d.y && d.x > d.z) r.x = -r.y - r.z; else if (d.y > d.z) r.y = -r.x - r.z;
	return r.xy;
}
void fragment() {
	vec2 p = wp.xz;
	float q = (sqrt(3.0) / 3.0 * p.x - p.y / 3.0) / hex_r;
	float r = (2.0 / 3.0 * p.y) / hex_r;
	vec2 h = hex_round(vec2(q, r));
	vec2 c = vec2(hex_r * sqrt(3.0) * (h.x + h.y / 2.0), hex_r * 1.5 * h.y);
	vec2 d = p - c;
	float m = 0.0;
	for (int i = 0; i < 3; i++) {
		float a = radians(float(i) * 60.0);
		m = max(m, abs(dot(d, vec2(cos(a), sin(a)))));
	}
	float edge = hex_r * sqrt(3.0) / 2.0 - m;
	float line = 1.0 - smoothstep(0.03, 0.12, edge);
	vec3 col = mix(COLOR.rgb, fields(wp.xz), smoothstep(0.35, 0.7, COLOR.a));
	col = pow(col, vec3(2.2));  // vertex colours are sRGB
	// cartographic hillshade from the same north-east sun, lower, so relief reads
	vec3 L = normalize(vec3(0.5, 0.55, -0.5));
	float shade = clamp(dot(normalize(wn), L), 0.0, 1.0);
	col *= mix(0.62, 1.08, smoothstep(0.35, 0.95, shade));
	// fine painterly grain so large areas are not flat colour
	vec2 g = floor(wp.xz * 6.0);
	float grain = fract(sin(dot(g, vec2(12.9898, 78.233))) * 43758.5453);
	col *= 0.93 + 0.14 * grain;
	ALBEDO = mix(col, col * 0.55, line * 0.6);
	ROUGHNESS = 0.95;
}
"""
	sm.shader = sh
	mi.material_override = sm
	return mi


func _water() -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(300, 300)
	mi.mesh = pm
	mi.position = Vector3(40, -0.55, 25)
	var sm := ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode blend_mix, diffuse_burley, specular_schlick_ggx;
varying vec3 wp;
void vertex() { wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
void fragment() {
	float w = sin(wp.x * 1.3 + wp.z * 0.7) * 0.5 + sin(wp.x * -0.6 + wp.z * 1.9) * 0.5;
	ALBEDO = pow(mix(vec3(0.10, 0.30, 0.40), vec3(0.16, 0.40, 0.50), 0.5 + 0.25 * w), vec3(2.2));
	ROUGHNESS = 0.18;
	METALLIC = 0.1;
	NORMAL_MAP = normalize(vec3(0.5 + 0.08 * cos(wp.x * 1.3), 0.5 + 0.08 * sin(wp.z * 1.9), 1.0));
	ALPHA = 0.88;
}
"""
	sm.shader = sh
	mi.material_override = sm
	return mi


# --- props --------------------------------------------------------------------

func _mat(c: Color, rough := 0.85) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	return m


func _place(parent: Node, mesh: Mesh, mat: Material, pos: Vector3, rot_y := 0.0, scale := Vector3.ONE) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.rotation.y = rot_y
	mi.scale = scale
	parent.add_child(mi)


func _in_hex(c: Vector2, spread: float) -> Vector2:
	while true:
		var p := Vector2(rng.randf_range(-1, 1), rng.randf_range(-1, 1)) * R * spread
		if p.length() < R * spread * 0.95:
			return c + p
	return c


func _forest(vp: Node, c: Vector2, n: int) -> void:
	var trunk := CylinderMesh.new()
	trunk.top_radius = 0.07
	trunk.bottom_radius = 0.1
	trunk.height = 0.7
	var cone := CylinderMesh.new()
	cone.top_radius = 0.0
	cone.bottom_radius = 0.55
	cone.height = 1.6
	var ball := SphereMesh.new()
	ball.radius = 0.6
	ball.height = 1.1
	var bark := _mat(Color(0.30, 0.22, 0.14))
	var pine := [_mat(Color(0.12, 0.26, 0.12)), _mat(Color(0.15, 0.30, 0.13)), _mat(Color(0.10, 0.22, 0.12))]
	var leaf := [_mat(Color(0.25, 0.42, 0.14)), _mat(Color(0.32, 0.46, 0.16)), _mat(Color(0.40, 0.46, 0.14))]
	for i in n:
		var p := _in_hex(c, 0.82)
		var h := height(p.x, p.y)
		var s := rng.randf_range(0.8, 1.35)
		_place(vp, trunk, bark, Vector3(p.x, h + 0.35 * s, p.y), 0, Vector3.ONE * s)
		if rng.randf() < 0.6:
			_place(vp, cone, pine[rng.randi() % 3], Vector3(p.x, h + (0.6 + 0.8) * s, p.y), 0, Vector3.ONE * s)
		else:
			_place(vp, ball, leaf[rng.randi() % 3], Vector3(p.x, h + 1.05 * s, p.y), 0, Vector3.ONE * s)


func _house(vp: Node, p: Vector2, rot: float, w: float, d: float, hgt: float, wall: Material, roof: Material) -> void:
	var h := height(p.x, p.y)
	var box := BoxMesh.new()
	box.size = Vector3(w, hgt, d)
	_place(vp, box, wall, Vector3(p.x, h + hgt / 2.0, p.y), rot)
	var pr := PrismMesh.new()
	pr.size = Vector3(w * 1.08, hgt * 0.55, d * 1.08)
	_place(vp, pr, roof, Vector3(p.x, h + hgt + hgt * 0.275, p.y), rot)


func _city(vp: Node, c: Vector2) -> void:
	var walls := [_mat(Color(0.86, 0.82, 0.72)), _mat(Color(0.78, 0.74, 0.66)), _mat(Color(0.90, 0.88, 0.84)), _mat(Color(0.72, 0.62, 0.50))]
	var roofs := [_mat(Color(0.55, 0.22, 0.15)), _mat(Color(0.42, 0.20, 0.14)), _mat(Color(0.30, 0.30, 0.32)), _mat(Color(0.48, 0.30, 0.18))]
	var concrete := [_mat(Color(0.72, 0.72, 0.70)), _mat(Color(0.62, 0.64, 0.66)), _mat(Color(0.80, 0.78, 0.74))]
	var road := _mat(Color(0.33, 0.33, 0.33))
	# two crossing streets
	for a in [0.2, 0.2 + PI / 2.0]:
		var b := BoxMesh.new()
		b.size = Vector3(R * 1.7, 0.05, 0.7)
		_place(vp, b, road, Vector3(c.x, height(c.x, c.y) + 0.03, c.y), a)
	# apartment blocks near the centre, houses around
	for i in 3:
		var p := _in_hex(c, 0.35)
		var h := height(p.x, p.y)
		var b := BoxMesh.new()
		var hg := rng.randf_range(3.0, 5.5)
		b.size = Vector3(rng.randf_range(1.4, 2.0), hg, rng.randf_range(1.0, 1.4))
		_place(vp, b, concrete[i % 3], Vector3(p.x, h + hg / 2.0, p.y), 0.2)
		var top := BoxMesh.new()
		top.size = Vector3(b.size.x * 0.4, 0.3, b.size.z * 0.4)
		_place(vp, top, _mat(Color(0.5, 0.5, 0.5)), Vector3(p.x, h + hg + 0.15, p.y), 0.2)
	for i in 16:
		var p := _in_hex(c, 0.8)
		if p.distance_to(c) < R * 0.25:
			continue
		_house(vp, p, 0.2 + (PI / 2.0 if rng.randf() < 0.5 else 0.0), rng.randf_range(0.9, 1.4), rng.randf_range(0.7, 1.0),
			rng.randf_range(0.7, 1.1), walls[rng.randi() % 4], roofs[rng.randi() % 4])
	# church with a spire
	var cp := c + Vector2(R * 0.3, -R * 0.35)
	_house(vp, cp, 0.2, 1.0, 2.0, 1.4, walls[2], roofs[2])
	var sp := CylinderMesh.new()
	sp.top_radius = 0.0
	sp.bottom_radius = 0.35
	sp.height = 2.2
	var tw := BoxMesh.new()
	tw.size = Vector3(0.6, 2.2, 0.6)
	var th := height(cp.x, cp.y)
	_place(vp, tw, walls[2], Vector3(cp.x - 0.9, th + 1.1, cp.y - 0.4), 0.2)
	_place(vp, sp, roofs[2], Vector3(cp.x - 0.9, th + 3.3, cp.y - 0.4), 0.2)


func _farm(vp: Node, c: Vector2) -> void:
	if rng.randf() < 0.6:
		var walls := _mat(Color(0.84, 0.80, 0.70))
		var roof := _mat(Color(0.52, 0.24, 0.16))
		var p := _in_hex(c, 0.5)
		_house(vp, p, 0.35, 1.2, 0.8, 0.8, walls, roof)
		_house(vp, p + Vector2(1.3, 0.6), 0.35, 1.6, 0.9, 0.9, _mat(Color(0.55, 0.40, 0.28)), _mat(Color(0.35, 0.33, 0.30)))
	for i in rng.randi_range(0, 3):
		_forest(vp, _in_hex(c, 0.9), 1)
