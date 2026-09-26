extends SceneTree
## Run: OUT=/path/out.png xvfb-run godot --path . --rendering-method forward_plus -s res://tools/references/map_style_ew_modern.gd
## Reference diorama #2: European War-like muted palette, rivers, roads with
## bridges, a railway and modern objects (industrial zone, airfield, wind
## turbines, farms with silos), rendered with the unit camera (orthographic,
## 65 degrees) and sun (north-east, 75 degrees).

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
const C := 6  # city / town
const A := 7  # farmland
const I := 8  # industrial zone
const E := 9  # airfield

# rows top (north) to bottom (south); odd-r offset like the game
var MAP := [
	[G, F, F, G, P, P, H, M, M, M, H],
	[G, F, F, A, A, P, H, H, M, M, H],
	[F, F, A, C, C, A, G, H, H, P, P],
	[G, A, A, C, I, A, G, G, F, F, F],
	[W, G, A, A, G, G, P, E, E, F, G],
	[W, W, G, G, F, G, P, P, G, A, A],
	[W, W, W, G, H, G, A, C, A, G, G],
	[W, W, W, W, G, G, A, A, G, F, G],
]
# hexes where the reference tanks stand (kept clear of props)
const UNIT_HEXES := ["2,4", "6,3", "2,5", "8,5", "6,6"]

var noise := FastNoiseLite.new()
var noise2 := FastNoiseLite.new()
var centers := []  # [pos2d, terrain]
var rng := RandomNumberGenerator.new()
var river := []  # [Vector2 point, width]
var roads := []  # [PackedVector2Array, width, kind] kind 0 asphalt, 1 street
var rail := PackedVector2Array()
var unit_pts := []


func hw(col: float, row: int) -> Vector2:
	return Vector2(R * sqrt(3.0) * (col + 0.5 * (row & 1)), R * 1.5 * row)


func _initialize() -> void:
	_run.call_deferred()


func _chaikin(pts: PackedVector2Array, iters: int) -> PackedVector2Array:
	var p := pts
	for k in iters:
		var o := PackedVector2Array([p[0]])
		for i in p.size() - 1:
			o.append(p[i].lerp(p[i + 1], 0.25))
			o.append(p[i].lerp(p[i + 1], 0.75))
		o.append(p[p.size() - 1])
		p = o
	return p


func _layout() -> void:
	# river from the hills in the north-east down to the sea in the south-west
	var rp := _chaikin(PackedVector2Array([
		Vector2(73, 5), Vector2(66, 12), Vector2(60, 15), Vector2(55, 21), Vector2(50, 23.5),
		Vector2(47, 29), Vector2(41, 34), Vector2(38.5, 40), Vector2(33, 45), Vector2(27, 46),
		Vector2(22, 52), Vector2(17, 56)]), 3)
	for i in rp.size():
		river.append([rp[i], lerpf(0.7, 2.0, float(i) / (rp.size() - 1))])
	# highway from the west edge to the city, then south-east to the town and off east
	roads.append([_chaikin(PackedVector2Array([
		Vector2(-8, 17), hw(1, 2) + Vector2(0, 2.5), hw(2, 2) + Vector2(0, 1), hw(3, 2), hw(3, 3),
		hw(4, 4), hw(4, 5) + Vector2(-1.5, 0), hw(5, 5) + Vector2(0, 3), hw(6, 6), hw(7, 6),
		hw(8, 6) + Vector2(0, 2), hw(9, 6), Vector2(108, 52)]), 2), 1.0, 0])
	# city - river bridge - airfield
	roads.append([_chaikin(PackedVector2Array([
		hw(4, 2), hw(4, 2) + Vector2(4, 4), hw(5, 3), hw(6, 3) + Vector2(0, -2.0), Vector2(64.5, 28.0), Vector2(66.6, 29.9)]), 3), 0.8, 0])
	# north road from the city to the farms and off map
	roads.append([_chaikin(PackedVector2Array([
		hw(4, 2), hw(3, 1) + Vector2(2, 1.5), hw(4, 0), Vector2(45, -8)]), 3), 0.7, 0])
	# town - farms in the south
	roads.append([_chaikin(PackedVector2Array([hw(7, 6), hw(7, 7) + Vector2(-1, 0), Vector2(70, 66)]), 2), 0.6, 0])
	# streets in city and town hexes
	for c in centers:
		if c[1] == C:
			for a in [0.2, 0.2 + PI / 2.0]:
				var d := Vector2(cos(a), -sin(a)) * R * 0.85
				roads.append([PackedVector2Array([c[0] - d, c[0] + d]), 0.55, 1])
	# railway from the industrial zone to the west edge
	rail = _chaikin(PackedVector2Array([hw(4, 3) + Vector2(-1, 2.5), hw(3, 3) + Vector2(0, 4.5),
		hw(2, 3) + Vector2(0, 4.5), hw(1, 3) + Vector2(0, 3), Vector2(-8, 26)]), 3)
	for key in UNIT_HEXES:
		var cr: PackedStringArray = key.split(",")
		unit_pts.append(hw(int(cr[0]), int(cr[1])))


func _run() -> void:
	noise.seed = 7
	noise.frequency = 0.08
	noise.fractal_octaves = 4
	noise2.seed = 21
	noise2.frequency = 0.35
	rng.seed = 5
	for row in ROWS:
		for col in COLS:
			centers.append([hw(col, row), MAP[row][col]])
	_layout()

	var vp := SubViewport.new()
	vp.size = OUT * SS
	vp.own_world_3d = true
	vp.msaa_3d = Viewport.MSAA_4X
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(vp)

	var mid := Vector2(R * sqrt(3.0) * (COLS - 0.5) / 2.0, R * 1.5 * (ROWS - 1) / 2.0)
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
	_bridges(vp)
	for c in centers:
		match c[1]:
			F:
				_forest(vp, c[0], 42)
			C:
				if c[0] == hw(7, 6):
					_town(vp, c[0])
				else:
					_city(vp, c[0])
			A:
				_farm(vp, c[0])
			I:
				_industry(vp, c[0])
			H:
				if c[0].y < 20 and c[0].x > 60:
					_turbine(vp, c[0] + Vector2(1.5, -1.0))
			G, P:
				if rng.randf() < 0.4:
					_forest(vp, c[0], rng.randi_range(2, 5))
	_airfield(vp, (hw(7, 4) + hw(8, 4)) / 2.0)
	_riverbank_trees(vp)
	for i in 6:
		await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	img.resize(OUT.x, OUT.y, Image.INTERPOLATE_LANCZOS)
	img.save_png(OS.get_environment("OUT"))
	var marks := {}
	for k in UNIT_HEXES.size():
		var p: Vector2 = unit_pts[k]
		var s := cam.unproject_position(Vector3(p.x, height(p.x, p.y), p.y)) / SS
		marks[UNIT_HEXES[k]] = [s.x, s.y]
	print("MARKS ", JSON.stringify(marks))
	quit()


# --- terrain field ------------------------------------------------------------

func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> Array:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
	return [p.distance_to(a + ab * t), t]


func river_dist(p: Vector2) -> Vector2:
	# (distance to the river centre line, river width there)
	var best := Vector2(1e9, 1.0)
	for i in river.size() - 1:
		var a: Vector2 = river[i][0]
		var b: Vector2 = river[i + 1][0]
		if absf(p.x - a.x) > 12.0 or absf(p.y - a.y) > 12.0:
			continue
		var r := _seg_dist(p, a, b)
		if r[0] < best.x:
			best = Vector2(r[0], lerpf(river[i][1], river[i + 1][1], r[1]))
	return best


func weights(x: float, z: float) -> Dictionary:
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
	return acc


func height(x: float, z: float) -> float:
	var acc := weights(x, z)
	var n := noise.get_noise_2d(x, z)
	var h := 0.15 * n
	h -= 1.6 * smoothstep(0.25, 0.75, acc.get(W, 0.0))
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
	# airfield and industry are levelled
	h = lerpf(h, 0.0, smoothstep(0.2, 0.55, acc.get(E, 0.0) + acc.get(I, 0.0)))
	# river channel
	var rd := river_dist(p)
	var bank := rd.y * 0.5
	var cut := 1.0 - smoothstep(bank, bank + 0.9 + 0.25 * h, rd.x)
	h = lerpf(h, -1.1, cut)
	return h


func ground_color(x: float, z: float, h: float, nrm: Vector3) -> Color:
	var acc := weights(x, z)
	var n := noise.get_noise_2d(x * 2.0, z * 2.0)
	var n2 := noise.get_noise_2d(x * 0.6 + 40.0, z * 0.6)
	# European War-like muted olive land with khaki and greener patches
	var olive := Color(0.215, 0.232, 0.12)
	var khaki := Color(0.265, 0.258, 0.15)
	var green := Color(0.20, 0.25, 0.11)
	var grass := olive.lerp(green, smoothstep(-0.2, 0.4, n2)).lerp(khaki, smoothstep(0.1, 0.6, -n2) * 0.8)
	grass = grass.lerp(grass.darkened(0.15), 0.5 + 0.5 * n)
	var plains := khaki.lerp(Color(0.25, 0.25, 0.14), 0.5 + 0.5 * n)
	var forest_floor := Color(0.14, 0.16, 0.075)
	var hill := Color(0.26, 0.255, 0.15)
	var rock := Color(0.27, 0.25, 0.21).lerp(Color(0.20, 0.19, 0.17), 0.5 + 0.5 * n)
	var city := Color(0.27, 0.25, 0.20)
	var concrete := Color(0.30, 0.295, 0.27).lerp(Color(0.24, 0.23, 0.21), 0.5 + 0.5 * n)
	var c := Color(0, 0, 0)
	c += grass * (acc.get(G, 0.0) + acc.get(A, 0.0))
	c += plains * (acc.get(P, 0.0) + acc.get(E, 0.0))
	c += forest_floor * acc.get(F, 0.0)
	c += hill * acc.get(H, 0.0)
	c += rock * acc.get(M, 0.0)
	c += city * acc.get(C, 0.0)
	c += concrete * acc.get(I, 0.0)
	c += Color(0.30, 0.28, 0.20) * acc.get(W, 0.0)  # sea bed
	c.a = 1.0
	var steep := 1.0 - nrm.y
	c = c.lerp(rock, smoothstep(0.25, 0.55, steep))
	c = c.lerp(rock, smoothstep(1.5, 3.0, h))
	c = c.lerp(Color(0.80, 0.81, 0.82), smoothstep(6.6, 7.6, h + 1.2 * n))
	var sand := smoothstep(0.2, 0.35, acc.get(W, 0.0)) * (1.0 - smoothstep(0.5, 0.75, acc.get(W, 0.0)))
	c = c.lerp(Color(0.40, 0.37, 0.25), sand)
	# muddy river banks
	var rd := river_dist(Vector2(x, z))
	c = c.lerp(Color(0.19, 0.18, 0.11), 1.0 - smoothstep(rd.y * 0.5, rd.y * 0.5 + 1.1, rd.x))
	c.a = acc.get(A, 0.0) * (1.0 - smoothstep(0.25, 0.55, steep))  # farmland weight for the shader
	return c


func _ground() -> MeshInstance3D:
	var x0 := -R * 1.2
	var z0 := -R * 1.2
	var x1 := R * sqrt(3.0) * (COLS + 0.5) + R * 0.2
	var z1 := R * 1.5 * (ROWS - 1) + R * 1.2
	var step := 0.4
	var nx := int((x1 - x0) / step)
	var nz := int((z1 - z0) / step)
	var hs := PackedFloat32Array()
	hs.resize((nx + 1) * (nz + 1))
	for j in nz + 1:
		for i in nx + 1:
			hs[j * (nx + 1) + i] = height(x0 + i * step, z0 + j * step)
	var st := SurfaceTool.new()
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
uniform vec4 road_seg[160];
uniform vec2 road_info[160];  // width, kind
uniform int road_n = 0;
uniform vec4 rail_seg[48];
uniform int rail_n = 0;
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
	vec3 pal[5] = vec3[5](vec3(0.36, 0.31, 0.15), vec3(0.21, 0.26, 0.11), vec3(0.27, 0.20, 0.12), vec3(0.31, 0.30, 0.165), vec3(0.25, 0.25, 0.12));
	vec3 col = pal[int(h * 5.0) % 5];
	col *= 1.0 - 0.10 * (0.5 + 0.5 * sin(v * 14.0));  // furrows
	float eu = min(mod(u, 2.6), 2.6 - mod(u, 2.6));
	float ev = min(mod(v, 1.8), 1.8 - mod(v, 1.8));
	float edge = min(eu, ev);
	col = mix(vec3(0.13, 0.16, 0.07), col, smoothstep(0.03, 0.10, edge));  // hedgerows
	return col;
}
vec2 hex_round(vec2 qr) {
	vec3 c = vec3(qr.x, qr.y, -qr.x - qr.y);
	vec3 r = round(c);
	vec3 d = abs(r - c);
	if (d.x > d.y && d.x > d.z) r.x = -r.y - r.z; else if (d.y > d.z) r.y = -r.x - r.z;
	return r.xy;
}
// distance to segment and position along it (metres from a)
vec2 seg(vec2 p, vec4 s) {
	vec2 a = s.xy;
	vec2 ab = s.zw - s.xy;
	float l = length(ab);
	float t = clamp(dot(p - a, ab) / max(l * l, 1e-6), 0.0, 1.0);
	return vec2(length(p - a - ab * t), t * l);
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
	// railway: ballast, sleepers, two rails
	for (int i = 0; i < rail_n; i++) {
		vec2 s = seg(p, rail_seg[i]);
		if (s.x < 0.45) {
			vec3 rc = mix(vec3(0.30, 0.28, 0.25), col, smoothstep(0.30, 0.45, s.x));
			if (s.x < 0.26 && fract(s.y / 0.22) < 0.45) rc = vec3(0.22, 0.17, 0.12);
			if (abs(s.x - 0.12) < 0.025) rc = vec3(0.42, 0.42, 0.42);
			col = rc;
		}
	}
	// roads: asphalt with pale shoulders and a dashed centre line; streets plain
	float rmin = 1e9;
	for (int i = 0; i < road_n; i++) {
		vec2 s = seg(p, road_seg[i]);
		float w = road_info[i].x * 0.5;
		if (s.x < w + 0.12) {
			vec3 rc = road_info[i].y > 0.5 ? vec3(0.19, 0.19, 0.18) : vec3(0.15, 0.15, 0.145);
			rc = mix(rc, vec3(0.34, 0.32, 0.26), smoothstep(w - 0.08, w, s.x));  // shoulder
			if (road_info[i].y < 0.5 && s.x < 0.03 && fract(s.y / 0.9) < 0.5) rc = vec3(0.62, 0.60, 0.52);
			float a = 1.0 - smoothstep(w, w + 0.12, s.x);
			if (s.x < rmin) { col = mix(col, rc, a); rmin = s.x; }
		}
	}
	col = pow(col, vec3(2.2));  // vertex colours are sRGB
	vec3 L = normalize(vec3(0.5, 0.55, -0.5));
	float shade = clamp(dot(normalize(wn), L), 0.0, 1.0);
	col *= mix(0.62, 1.08, smoothstep(0.35, 0.95, shade));
	vec2 g = floor(wp.xz * 6.0);
	float grain = fract(sin(dot(g, vec2(12.9898, 78.233))) * 43758.5453);
	col *= 0.93 + 0.14 * grain;
	ALBEDO = mix(col, col * 0.55, line * 0.45);
	ROUGHNESS = 0.95;
}
"""
	sm.shader = sh
	var segs := []
	var info := []
	for rd in roads:
		var pts: PackedVector2Array = rd[0]
		for i in pts.size() - 1:
			segs.append(Vector4(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y))
			info.append(Vector2(rd[1], rd[2]))
	assert(segs.size() <= 160)
	sm.set_shader_parameter("road_seg", segs)
	sm.set_shader_parameter("road_info", info)
	sm.set_shader_parameter("road_n", segs.size())
	var rs := []
	for i in rail.size() - 1:
		rs.append(Vector4(rail[i].x, rail[i].y, rail[i + 1].x, rail[i + 1].y))
	sm.set_shader_parameter("rail_seg", rs)
	sm.set_shader_parameter("rail_n", rs.size())
	print("road segments ", segs.size(), " rail ", rs.size())
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
	ALBEDO = pow(mix(vec3(0.05, 0.105, 0.135), vec3(0.065, 0.13, 0.16), 0.5 + 0.25 * w), vec3(2.2));
	ROUGHNESS = 0.25;
	METALLIC = 0.1;
	NORMAL_MAP = normalize(vec3(0.5 + 0.08 * cos(wp.x * 1.3), 0.5 + 0.08 * sin(wp.z * 1.9), 1.0));
	ALPHA = 0.96;
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


## Walls with rows of windows (local box coordinates, so they follow rotation).
func _bmat(c: Color, floor_h := 0.4, win := 0.34) -> ShaderMaterial:
	var sm := ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
uniform vec3 wall;
uniform float floor_h;
uniform float win;
varying vec3 lp;
varying vec3 ln;
void vertex() { lp = VERTEX; ln = NORMAL; }
void fragment() {
	vec3 col = wall;
	if (abs(ln.y) < 0.5) {
		float u = abs(ln.x) > 0.5 ? lp.z : lp.x;
		float fy = fract((lp.y + 50.0) / floor_h);
		float fx = fract((u + 50.0) / win);
		if (fy > 0.40 && fy < 0.72 && fx > 0.28 && fx < 0.66) col = mix(col, vec3(0.16, 0.18, 0.20), 0.8);
	}
	ALBEDO = pow(col, vec3(2.2));
	ROUGHNESS = 0.85;
}
"""
	sm.shader = sh
	sm.set_shader_parameter("wall", Vector3(c.r, c.g, c.b))
	sm.set_shader_parameter("floor_h", floor_h)
	sm.set_shader_parameter("win", win)
	return sm


func _place(parent: Node, mesh: Mesh, mat: Material, pos: Vector3, rot_y := 0.0, scale := Vector3.ONE) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.rotation.y = rot_y
	mi.scale = scale
	parent.add_child(mi)
	return mi


func _box(parent: Node, size: Vector3, mat: Material, p: Vector2, y: float, rot := 0.0) -> MeshInstance3D:
	var b := BoxMesh.new()
	b.size = size
	return _place(parent, b, mat, Vector3(p.x, y + size.y / 2.0, p.y), rot)


func _cyl(parent: Node, r_top: float, r_bot: float, hgt: float, mat: Material, p: Vector2, y: float) -> MeshInstance3D:
	var c := CylinderMesh.new()
	c.top_radius = r_top
	c.bottom_radius = r_bot
	c.height = hgt
	c.radial_segments = 24
	return _place(parent, c, mat, Vector3(p.x, y + hgt / 2.0, p.y))


func _clear(p: Vector2, r := 2.8) -> bool:
	for u in unit_pts:
		if p.distance_to(u) < r:
			return false
	for rd in roads:
		var pts: PackedVector2Array = rd[0]
		for i in pts.size() - 1:
			if _seg_dist(p, pts[i], pts[i + 1])[0] < rd[1] * 0.5 + 0.5:
				return false
	for i in rail.size() - 1:
		if _seg_dist(p, rail[i], rail[i + 1])[0] < 0.8:
			return false
	var rd := river_dist(p)
	return rd.x > rd.y * 0.5 + 0.6


func _in_hex(c: Vector2, spread: float) -> Vector2:
	while true:
		var p := Vector2(rng.randf_range(-1, 1), rng.randf_range(-1, 1)) * R * spread
		if p.length() < R * spread * 0.95:
			return c + p
	return c


var _tree_mats := {}


func _tree(vp: Node, p: Vector2, s: float) -> void:
	if _tree_mats.is_empty():
		_tree_mats["bark"] = _mat(Color(0.20, 0.15, 0.10))
		_tree_mats["pine"] = [_mat(Color(0.07, 0.12, 0.05)), _mat(Color(0.09, 0.14, 0.06)), _mat(Color(0.06, 0.10, 0.05))]
		_tree_mats["leaf"] = [_mat(Color(0.13, 0.17, 0.06)), _mat(Color(0.16, 0.19, 0.07)), _mat(Color(0.19, 0.20, 0.08))]
	var trunk := CylinderMesh.new()
	trunk.top_radius = 0.07
	trunk.bottom_radius = 0.1
	trunk.height = 0.7
	var h := height(p.x, p.y)
	_place(vp, trunk, _tree_mats["bark"], Vector3(p.x, h + 0.35 * s, p.y), 0, Vector3.ONE * s)
	if rng.randf() < 0.55:
		var cone := CylinderMesh.new()
		cone.top_radius = 0.0
		cone.bottom_radius = 0.55
		cone.height = 1.6
		_place(vp, cone, _tree_mats["pine"][rng.randi() % 3], Vector3(p.x, h + 1.4 * s, p.y), 0, Vector3.ONE * s)
	else:
		var ball := SphereMesh.new()
		ball.radius = 0.6
		ball.height = 1.1
		_place(vp, ball, _tree_mats["leaf"][rng.randi() % 3], Vector3(p.x, h + 1.05 * s, p.y), 0, Vector3.ONE * s)


func _forest(vp: Node, c: Vector2, n: int) -> void:
	for i in n:
		var p := _in_hex(c, 0.85)
		if _clear(p, 3.2):
			_tree(vp, p, rng.randf_range(0.8, 1.3))


func _riverbank_trees(vp: Node) -> void:
	for i in range(0, river.size() - 1, 2):
		var a: Vector2 = river[i][0]
		var b: Vector2 = river[i + 1][0]
		var nrm := (b - a).orthogonal().normalized()
		for side in [-1.0, 1.0]:
			if rng.randf() < 0.45:
				var p: Vector2 = a + nrm * side * (river[i][1] * 0.5 + rng.randf_range(1.1, 1.8))
				if _clear(p, 3.0):
					_tree(vp, p, rng.randf_range(0.7, 1.0))


func _house(vp: Node, p: Vector2, rot: float, w: float, d: float, hgt: float, wall: Material, roof: Material) -> void:
	var h := height(p.x, p.y)
	_box(vp, Vector3(w, hgt, d), wall, p, h, rot)
	var pr := PrismMesh.new()
	pr.size = Vector3(w * 1.08, hgt * 0.55, d * 1.08)
	_place(vp, pr, roof, Vector3(p.x, h + hgt + hgt * 0.275, p.y), rot)


func _block(vp: Node, p: Vector2, rot: float, size: Vector3, wall: Material) -> void:
	var h := height(p.x, p.y) - 0.1
	_box(vp, size, wall, p, h, rot)
	_box(vp, Vector3(size.x + 0.06, 0.08, size.z + 0.06), _mat(Color(0.20, 0.20, 0.20)), p, h + size.y, rot)
	_box(vp, Vector3(size.x * 0.25, 0.25, size.z * 0.35), _mat(Color(0.35, 0.34, 0.32)), p + Vector2(size.x * 0.2, 0).rotated(-rot), h + size.y, rot)


func _roof_mats() -> Array:
	return [_mat(Color(0.45, 0.22, 0.13)), _mat(Color(0.38, 0.20, 0.13)), _mat(Color(0.30, 0.24, 0.18)), _mat(Color(0.50, 0.28, 0.15))]


func _wall_mats() -> Array:
	return [_mat(Color(0.62, 0.58, 0.50)), _mat(Color(0.56, 0.52, 0.45)), _mat(Color(0.66, 0.63, 0.57)), _mat(Color(0.52, 0.44, 0.35))]


func _city(vp: Node, c: Vector2) -> void:
	var blocks := [_bmat(Color(0.60, 0.59, 0.56)), _bmat(Color(0.52, 0.54, 0.55)), _bmat(Color(0.64, 0.60, 0.52)), _bmat(Color(0.48, 0.47, 0.45))]
	var walls := _wall_mats()
	var roofs := _roof_mats()
	# panel blocks in the four quarters between the streets, low houses at the rim
	var rot := 0.2
	for qx in [-1, 1]:
		for qz in [-1, 1]:
			var o := Vector2(qx * 1.9, qz * 1.9).rotated(-rot)
			var tall := rng.randf() < 0.35
			var size := Vector3(rng.randf_range(1.6, 2.2), rng.randf_range(4.5, 7.0) if tall else rng.randf_range(2.0, 3.2), rng.randf_range(0.9, 1.2))
			if rng.randf() < 0.5:
				size = Vector3(size.z, size.y, size.x)
			_block(vp, c + o, rot, size, blocks[rng.randi() % 4])
	for i in 18:
		var p := _in_hex(c, 0.85)
		if p.distance_to(c) < R * 0.55 or not _clear(p, 2.5):
			continue
		_house(vp, p, rot + (PI / 2.0 if rng.randf() < 0.5 else 0.0), rng.randf_range(0.8, 1.2), rng.randf_range(0.6, 0.9),
			rng.randf_range(0.6, 0.9), walls[rng.randi() % 4], roofs[rng.randi() % 4])
	for i in 4:
		var p := _in_hex(c, 0.8)
		if _clear(p, 2.5):
			_tree(vp, p, 0.7)


func _town(vp: Node, c: Vector2) -> void:
	var walls := _wall_mats()
	var roofs := _roof_mats()
	var rot := 0.2
	for i in 26:
		var p := _in_hex(c, 0.88)
		if not _clear(p, 0.0) or p.distance_to(c) < 1.0:
			continue
		_house(vp, p, rot + (PI / 2.0 if rng.randf() < 0.5 else 0.0), rng.randf_range(0.8, 1.3), rng.randf_range(0.6, 0.9),
			rng.randf_range(0.6, 0.9), walls[rng.randi() % 4], roofs[rng.randi() % 4])
	_block(vp, c + Vector2(1.9, 1.9).rotated(-rot), rot, Vector3(1.8, 1.6, 0.9), _bmat(Color(0.62, 0.58, 0.50)))
	# church
	var cp := c + Vector2(-1.9, -1.9).rotated(-rot)
	_house(vp, cp, rot, 1.0, 1.8, 1.2, walls[2], roofs[2])
	var tp := cp + Vector2(-0.3, -1.1).rotated(-rot)
	var th := height(tp.x, tp.y)
	_box(vp, Vector3(0.55, 2.0, 0.55), walls[2], tp, th, rot)
	_cyl(vp, 0.0, 0.34, 1.6, roofs[2], tp, th + 2.0)
	# telecom mast
	var mp := c + Vector2(-2.3, 1.6)
	var mh := height(mp.x, mp.y)
	var red := _mat(Color(0.55, 0.12, 0.10))
	var white := _mat(Color(0.75, 0.75, 0.72))
	for k in 5:
		_cyl(vp, 0.10 - 0.015 * (k + 1), 0.10 - 0.015 * k, 1.1, red if k % 2 == 0 else white, mp, mh + 1.1 * k)


func _farm(vp: Node, c: Vector2) -> void:
	if rng.randf() < 0.75:
		var p := _in_hex(c, 0.45)
		if _clear(p, 3.0) and _clear(p + Vector2(1.4, 0.6), 3.0):
			var walls := _wall_mats()
			var roofs := _roof_mats()
			_house(vp, p, 0.35, 1.1, 0.75, 0.75, walls[0], roofs[0])
			# modern barn and grain silos
			var bp := p + Vector2(1.5, 0.6)
			_house(vp, bp, 0.35, 1.9, 1.0, 0.8, _mat(Color(0.42, 0.40, 0.36)), _mat(Color(0.28, 0.29, 0.28)))
			var steel := _mat(Color(0.62, 0.62, 0.60), 0.4)
			for k in 2:
				var sp := p + Vector2(-0.9 + 0.75 * k, 0.9)
				var sh := height(sp.x, sp.y)
				_cyl(vp, 0.32, 0.32, 1.3, steel, sp, sh)
				_cyl(vp, 0.0, 0.34, 0.35, steel, sp, sh + 1.3)
	for i in rng.randi_range(0, 3):
		var p := _in_hex(c, 0.9)
		if _clear(p, 3.0):
			_tree(vp, p, 0.9)


func _industry(vp: Node, c: Vector2) -> void:
	var rot := 0.2
	var hall := _mat(Color(0.50, 0.52, 0.53))
	var hall2 := _mat(Color(0.56, 0.52, 0.44))
	var roof := _mat(Color(0.33, 0.35, 0.36))
	var glass := _mat(Color(0.30, 0.36, 0.38), 0.3)
	var y := height(c.x, c.y) - 0.05
	# factory hall with a saw-tooth roof
	var hp := c + Vector2(-1.2, -1.6).rotated(-rot)
	_box(vp, Vector3(4.0, 1.2, 2.2), hall, hp, y, rot)
	for k in 5:
		var o := hp + Vector2(-1.6 + 0.8 * k, 0).rotated(-rot)
		var pr := PrismMesh.new()
		pr.left_to_right = 1.0
		pr.size = Vector3(0.8, 0.45, 2.2)
		_place(vp, pr, roof if k % 2 == 0 else glass, Vector3(o.x, y + 1.2 + 0.225, o.y), rot)
	# warehouse
	var wp := c + Vector2(1.6, 1.4).rotated(-rot)
	_box(vp, Vector3(2.6, 1.0, 1.5), hall2, wp, y, rot)
	_box(vp, Vector3(2.7, 0.1, 1.6), roof, wp, y + 1.0, rot)
	# chimneys with red and white bands
	var red := _mat(Color(0.52, 0.14, 0.10))
	var white := _mat(Color(0.72, 0.72, 0.70))
	for cp in [c + Vector2(1.6, -2.0), c + Vector2(2.4, -1.2)]:
		for k in 6:
			_cyl(vp, 0.24 - 0.02 * (k + 1), 0.24 - 0.02 * k, 0.8, white if k < 4 or k == 5 else red, cp, y + 0.8 * k)
		_cyl(vp, 0.15, 0.15, 0.25, red, cp, y + 4.6)
	# storage tanks
	var tank := _mat(Color(0.66, 0.66, 0.64), 0.45)
	for k in 3:
		var tp := c + Vector2(-2.6 + 1.2 * k, 1.9)
		_cyl(vp, 0.5, 0.5, 0.9, tank, tp, y)
		_cyl(vp, 0.15, 0.5, 0.12, tank, tp, y + 0.9)
	# small office block
	_block(vp, c + Vector2(-2.6, 0.2), rot, Vector3(1.0, 1.3, 0.8), _bmat(Color(0.58, 0.56, 0.52)))


func _turbine(vp: Node, p: Vector2) -> void:
	var y := height(p.x, p.y)
	var white := _mat(Color(0.78, 0.78, 0.76), 0.5)
	var hub_h := 5.0
	_cyl(vp, 0.08, 0.16, hub_h, white, p, y)
	# nacelle facing the prevailing wind (south-west, towards the viewer's left)
	var yaw := deg_to_rad(35.0)
	var nb := BoxMesh.new()
	nb.size = Vector3(0.6, 0.25, 0.25)
	_place(vp, nb, white, Vector3(p.x, y + hub_h, p.y), yaw)
	var fwd := Vector3(-cos(yaw), 0, sin(yaw))
	var hub := Vector3(p.x, y + hub_h, p.y) + fwd * 0.35
	for k in 3:
		var bl := BoxMesh.new()
		bl.size = Vector3(0.12, 2.2, 0.04)
		var mi := MeshInstance3D.new()
		mi.mesh = bl
		mi.material_override = white
		var a := deg_to_rad(20.0 + 120.0 * k)
		var basis := Basis(Vector3.UP, yaw + PI / 2.0) * Basis(Vector3.FORWARD, a)
		mi.transform = Transform3D(basis, hub + basis * Vector3(0, 1.1, 0))
		vp.add_child(mi)


func _airfield(vp: Node, c: Vector2) -> void:
	var y := 0.02
	var L := 15.0
	var Wd := 1.6
	var rp := c + Vector2(0, 1.2)
	var sm := ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
uniform float L;
uniform float W;
varying vec3 lp;
void vertex() { lp = VERTEX; }
void fragment() {
	vec3 col = vec3(0.17, 0.17, 0.165);
	float x = abs(lp.x);
	float z = abs(lp.z);
	if (z < 0.035 && fract(lp.x / 1.1) < 0.5 && x < L * 0.5 - 1.3) col = vec3(0.70, 0.70, 0.66);
	if (x > L * 0.5 - 1.0 && x < L * 0.5 - 0.35 && z < W * 0.5 - 0.15 && fract(lp.z / 0.18) < 0.5) col = vec3(0.70, 0.70, 0.66);
	if (z > W * 0.5 - 0.08 && z < W * 0.5 - 0.03) col = vec3(0.62, 0.62, 0.58);
	ALBEDO = pow(col, vec3(2.2));
	ROUGHNESS = 0.9;
}
"""
	sm.shader = sh
	sm.set_shader_parameter("L", L)
	sm.set_shader_parameter("W", Wd)
	_box(vp, Vector3(L, 0.12, Wd), sm, rp, y)
	var tarmac := _mat(Color(0.21, 0.21, 0.20))
	var apron := _mat(Color(0.30, 0.30, 0.28))
	# taxiway and apron north of the runway
	_box(vp, Vector3(L - 3.0, 0.1, 0.5), tarmac, rp + Vector2(0, -2.1), y)
	for x in [-5.5, 5.5]:
		_box(vp, Vector3(0.5, 0.1, 2.1), tarmac, rp + Vector2(x, -1.05), y)
	_box(vp, Vector3(8.0, 0.1, 2.6), apron, rp + Vector2(-1.0, -4.3), y)
	# hangars (half cylinders)
	var hang := _mat(Color(0.40, 0.42, 0.38), 0.6)
	for k in 3:
		var hp := rp + Vector2(-4.2 + 2.3 * k, -6.6)
		var cm := CylinderMesh.new()
		cm.top_radius = 0.8
		cm.bottom_radius = 0.8
		cm.height = 1.9
		cm.radial_segments = 24
		var mi := MeshInstance3D.new()
		mi.mesh = cm
		mi.material_override = hang
		mi.transform = Transform3D(Basis(Vector3.FORWARD, PI / 2.0), Vector3(hp.x, y + 0.05, hp.y))
		vp.add_child(mi)
	# control tower
	var tp := rp + Vector2(4.3, -5.6)
	var tw := _mat(Color(0.62, 0.60, 0.55))
	_box(vp, Vector3(1.4, 0.7, 0.9), _bmat(Color(0.60, 0.58, 0.53)), tp + Vector2(0.9, 0.3), y)
	_cyl(vp, 0.25, 0.3, 2.4, tw, tp, y)
	_cyl(vp, 0.5, 0.42, 0.4, _mat(Color(0.18, 0.24, 0.27), 0.2), tp, y + 2.4)
	_cyl(vp, 0.55, 0.55, 0.08, _mat(Color(0.25, 0.25, 0.25)), tp, y + 2.8)
	# parked jets on the apron
	for k in 3:
		_jet(vp, rp + Vector2(-4.0 + 2.1 * k, -4.2), y + 0.12)


func _jet(vp: Node, p: Vector2, y: float) -> void:
	var grey := _mat(Color(0.33, 0.35, 0.35), 0.6)
	# nose points south (towards the taxiway)
	var fus := CylinderMesh.new()
	fus.top_radius = 0.05
	fus.bottom_radius = 0.16
	fus.height = 2.2
	var mi := MeshInstance3D.new()
	mi.mesh = fus
	mi.material_override = grey
	mi.transform = Transform3D(Basis(Vector3.RIGHT, PI / 2.0), Vector3(p.x, y + 0.25, p.y + 0.1))
	vp.add_child(mi)
	var wing := PrismMesh.new()
	wing.size = Vector3(1.4, 0.9, 0.04)
	var wm := MeshInstance3D.new()
	wm.mesh = wing
	wm.material_override = grey
	wm.transform = Transform3D(Basis(Vector3.RIGHT, PI / 2.0), Vector3(p.x, y + 0.24, p.y - 0.1))
	vp.add_child(wm)
	_box(vp, Vector3(0.04, 0.4, 0.35), grey, p + Vector2(0, -0.8), y + 0.25)
	_box(vp, Vector3(0.14, 0.08, 0.3), _mat(Color(0.12, 0.14, 0.16), 0.2), p + Vector2(0, 0.55), y + 0.33)


func _bridges(vp: Node) -> void:
	var deck := _mat(Color(0.42, 0.41, 0.38))
	var asphalt := _mat(Color(0.16, 0.16, 0.15))
	for rd in roads:
		var pts: PackedVector2Array = rd[0]
		for i in pts.size() - 1:
			for j in river.size() - 1:
				var x = Geometry2D.segment_intersects_segment(pts[i], pts[i + 1], river[j][0], river[j + 1][0])
				if x == null:
					continue
				var dir: Vector2 = (pts[i + 1] - pts[i]).normalized()
				var rot := atan2(-dir.y, dir.x)
				var span: float = river[j][1] + 2.4
				var w: float = rd[1] + 0.2
				_box(vp, Vector3(span, 0.18, w), deck, x, 0.12, rot)
				_box(vp, Vector3(span, 0.02, w - 0.2), asphalt, x, 0.30, rot)
				var nrm := dir.orthogonal()
				for s in [-1.0, 1.0]:
					_box(vp, Vector3(span, 0.16, 0.06), deck, x + nrm * s * (w * 0.5 - 0.03), 0.30, rot)
				_box(vp, Vector3(0.3, 1.0, w * 0.8), deck, x, -0.9, rot)
	# railway bridge is not needed: the railway stays west of the river
