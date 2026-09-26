extends SceneTree
## Run: python3 tools/references/make_ridges.py tools/references/ridges_test.json OUTDIR 0 && MTN=OUTDIR TEX=/path/to/textures EW=1 OUT=out.png xvfb-run godot --path . --rendering-method forward_plus -s res://tools/references/map_ridges_test.gd
## Test scene: continuous mountain ranges of 2, 3 and 5 hexes on open grassland.
## Reference diorama #3: ground from real photo textures (EW tint or natural),
## otherwise as #2: European War-like muted palette, rivers, roads with
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
	[G, P, G, G, P, G, G, P, G, G, G],
	[G, G, M, M, G, G, G, G, P, G, G],
	[P, G, G, G, G, P, G, G, G, G, G],
	[G, G, G, G, G, M, M, M, G, G, P],
	[G, P, G, G, G, G, G, G, G, G, G],
	[G, G, G, G, G, G, G, G, G, P, G],
	[G, G, M, M, M, M, M, G, G, G, G],
	[G, G, G, P, G, G, G, G, G, G, G],
]
# hexes where the reference tanks stand (kept clear of props)
const UNIT_HEXES := ["6,1"]

var noise := FastNoiseLite.new()
var noise2 := FastNoiseLite.new()
var ridged := FastNoiseLite.new()  # Civ5-like mountain ranges
var warp := FastNoiseLite.new()
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
	ridged.seed = 11
	ridged.noise_type = FastNoiseLite.TYPE_PERLIN
	ridged.fractal_type = FastNoiseLite.FRACTAL_RIDGED
	ridged.frequency = 0.11
	ridged.fractal_octaves = 6
	ridged.fractal_lacunarity = 2.2
	ridged.fractal_gain = 0.5
	warp.seed = 4
	warp.frequency = 0.04
	rng.seed = 5
	for row in ROWS:
		for col in COLS:
			centers.append([hw(col, row), MAP[row][col]])
	for key in UNIT_HEXES:  # test scene: no rivers, roads or rail
		var cr: PackedStringArray = key.split(",")
		unit_pts.append(hw(int(cr[0]), int(cr[1])))
	_load_mountains()

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
	var fill := DirectionalLight3D.new()
	fill.light_energy = 0.25
	fill.light_color = Color(1.0, 0.93, 0.82)
	fill.light_cull_mask = 2
	vp.add_child(fill)
	fill.look_at_from_position(look + Vector3(-0.3, 0.6, 1.0) * 50.0, look)
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

	var gnd := _ground()
	gnd.layers = 3
	vp.add_child(gnd)
	vp.add_child(_water())
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


var mtn := PackedFloat32Array()
var mtn_info := {}


func _load_mountains() -> void:
	var dir := OS.get_environment("MTN")
	mtn_info = JSON.parse_string(FileAccess.get_file_as_string(dir + "/mountain.json"))
	mtn = FileAccess.get_file_as_bytes(dir + "/mountain_h.f32").to_float32_array()


## Eroded Civ5-style mountain height (bilinear from the precomputed grid).
func mtn_h(x: float, z: float) -> float:
	var fx: float = (x - mtn_info["x0"]) / mtn_info["step"]
	var fz: float = (z - mtn_info["z0"]) / mtn_info["step"]
	var nx: int = mtn_info["nx"]
	var nz: int = mtn_info["nz"]
	var ix := clampi(int(fx), 0, nx - 2)
	var iz := clampi(int(fz), 0, nz - 2)
	var tx := clampf(fx - ix, 0.0, 1.0)
	var tz := clampf(fz - iz, 0.0, 1.0)
	var a := lerpf(mtn[iz * nx + ix], mtn[iz * nx + ix + 1], tx)
	var b := lerpf(mtn[(iz + 1) * nx + ix], mtn[(iz + 1) * nx + ix + 1], tx)
	return lerpf(a, b, tz)


func height(x: float, z: float) -> float:
	var acc := weights(x, z)
	var n := noise.get_noise_2d(x, z)
	var h := 0.15 * n
	h -= 1.6 * smoothstep(0.25, 0.75, acc.get(W, 0.0))
	var p := Vector2(x, z)
	var hill := 0.0
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
	h += hill * (0.85 + 0.3 * noise2.get_noise_2d(x * 0.5, z * 0.5))
	# mountains: eroded ranges (see make_mountains.py)
	h += mtn_h(x, z)
	# airfield and industry are levelled
	h = lerpf(h, 0.0, smoothstep(0.2, 0.55, acc.get(E, 0.0) + acc.get(I, 0.0)))
	# river channel
	var rd := river_dist(p)
	var bank := rd.y * 0.5
	var cut := 1.0 - smoothstep(bank, bank + 0.9 + 0.25 * h, rd.x)
	h = lerpf(h, -1.1, cut)
	return h


# --- textured ground ------------------------------------------------------------

# texture layers: [folder, file, tile size in metres, target colour (sRGB, EW palette)]
const LAYERS := [
	["aerial_grass_rock_1k.blend", "textures/aerial_grass_rock_diff_1k.jpg", 7.0, Color(0.215, 0.232, 0.12)],  # 0 grass
	["Grass004_1K-PNG", "Grass004_1K-PNG_Color.png", 3.5, Color(0.215, 0.24, 0.115)],  # 1 grass
	["Ground037_1K-PNG", "Ground037_1K-PNG_Color.png", 5.0, Color(0.265, 0.258, 0.15)],  # 2 plains
	["Ground013_1K-JPG", "Ground013_1K-JPG_Color.jpg", 5.0, Color(0.25, 0.25, 0.14)],  # 3 plains
	["forrest_ground_01_1k.blend", "textures/forrest_ground_01_diff_1k.jpg", 5.0, Color(0.15, 0.165, 0.08)],  # 4 forest
	["Ground048_1K-JPG", "Ground048_1K-JPG_Color.jpg", 4.0, Color(0.14, 0.13, 0.08)],  # 5 forest
	["rocky_terrain_02_1k.blend", "textures/rocky_terrain_02_diff_1k.jpg", 7.0, Color(0.25, 0.255, 0.14)],  # 6 hills
	["aerial_rocks_01_1k.blend", "textures/aerial_rocks_01_diff_1k.jpg", 7.0, Color(0.28, 0.27, 0.20)],  # 7 hills / rock
	["aerial_rocks_02_1k.blend", "textures/aerial_rocks_02_diff_1k.jpg", 9.0, Color(0.25, 0.23, 0.19)],  # 8 cliffs
	["aerial_rocks_04_1k.blend", "textures/aerial_rocks_04_diff_1k.jpg", 9.0, Color(0.24, 0.22, 0.18)],  # 9 rock
	["Snow006_1K-PNG", "Snow006_1K-PNG_Color.png", 8.0, Color(0.80, 0.81, 0.82)],  # 10 snow
	["aerial_beach_01_1k.blend", "textures/aerial_beach_01_diff_1k.jpg", 6.0, Color(0.40, 0.37, 0.25)],  # 11 sand
	["aerial_sand_1k.blend", "textures/aerial_sand_diff_1k.jpg", 6.0, Color(0.38, 0.35, 0.24)],  # 12 sand
	["aerial_ground_rock_1k.blend", "textures/aerial_ground_rock_diff_1k.jpg", 5.0, Color(0.19, 0.18, 0.11)],  # 13 mud
	["Ground030_1K-PNG", "Ground030_1K-PNG_Color.png", 6.0, Color(0.29, 0.28, 0.25)],  # 14 urban
]


## Weights of the ground classes at a point: grass, plains, forest, hills,
## rock, snow, sand, mud, urban, farm.
func _put(w: Array, k: int, t: float) -> void:
	for i in 9:
		w[i] *= 1.0 - t
	w[k] += t


func class_weights(x: float, z: float, h: float, nrm: Vector3) -> Array:
	var acc := weights(x, z)
	var n := noise.get_noise_2d(x * 2.0, z * 2.0)
	var w := [
		acc.get(G, 0.0) + acc.get(A, 0.0), acc.get(P, 0.0) + acc.get(E, 0.0), acc.get(F, 0.0), acc.get(H, 0.0),
		acc.get(M, 0.0), 0.0, acc.get(W, 0.0), 0.0, acc.get(C, 0.0) + acc.get(I, 0.0), 0.0]
	var steep := 1.0 - nrm.y
	var farm: float = acc.get(A, 0.0) * (1.0 - smoothstep(0.25, 0.55, steep))
	_put(w, 4, smoothstep(0.25, 0.55, steep))
	_put(w, 4, smoothstep(0.6, 2.6, mtn_h(x, z)))
	# snow only on the highest crests and not on cliffs
	_put(w, 5, smoothstep(13.3, 14.3, h + 0.5 * n) * (1.0 - smoothstep(0.3, 0.55, steep)))
	var rd := river_dist(Vector2(x, z))
	_put(w, 7, 1.0 - smoothstep(rd.y * 0.5, rd.y * 0.5 + 1.1, rd.x))
	w[9] = farm
	return w


func _layer_images() -> Array:
	var dir := OS.get_environment("TEX")
	var imgs := []
	var means := []
	for l in LAYERS:
		var img := Image.load_from_file(dir + "/" + l[0] + "/" + l[1])
		img.convert(Image.FORMAT_RGB8)
		if img.get_width() != 1024:
			img.resize(1024, 1024, Image.INTERPOLATE_LANCZOS)
		# mean colour in linear space (textures are sampled as sRGB)
		var s := img.duplicate() as Image
		s.resize(64, 64, Image.INTERPOLATE_BILINEAR)
		var m := Vector3.ZERO
		for y in 64:
			for x in 64:
				var c := s.get_pixel(x, y).srgb_to_linear()
				m += Vector3(c.r, c.g, c.b)
		means.append(m / 4096.0)
		img.generate_mipmaps()
		imgs.append(img)
	return [imgs, means]


func _ground() -> MeshInstance3D:
	var x0 := -R * 1.2
	var z0 := -R * 1.2
	var x1 := R * sqrt(3.0) * (COLS + 0.5) + R * 0.2
	var z1 := R * 1.5 * (ROWS - 1) + R * 1.2
	var step := 0.25
	var nx := int((x1 - x0) / step)
	var nz := int((z1 - z0) / step)
	var hs := PackedFloat32Array()
	hs.resize((nx + 1) * (nz + 1))
	for j in nz + 1:
		for i in nx + 1:
			hs[j * (nx + 1) + i] = height(x0 + i * step, z0 + j * step)
	var verts := PackedVector3Array()
	var nrms := PackedVector3Array()
	var c0 := PackedFloat32Array()
	var c1 := PackedFloat32Array()
	var uvs := PackedVector2Array()
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
			nrms.append(nrm)
			var w := class_weights(x, z, h, nrm)
			c0.append_array([w[0], w[1], w[2], w[3]])
			c1.append_array([w[4], w[5], w[6], w[7]])
			uvs.append(Vector2(w[8], w[9]))
	var idx := PackedInt32Array()
	for j in nz:
		for i in nx:
			var a := j * (nx + 1) + i
			idx.append_array([a, a + 1, a + nx + 1, a + 1, a + nx + 2, a + nx + 1])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = nrms
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_CUSTOM0] = c0
	arr[Mesh.ARRAY_CUSTOM1] = c1
	arr[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	var fmt := (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) | (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT)
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr, [], {}, fmt)
	var mi := MeshInstance3D.new()
	mi.mesh = m
	var sm := ShaderMaterial.new()
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode diffuse_burley;
uniform float hex_r = 5.5;
uniform sampler2DArray layers : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D macro : filter_linear, repeat_enable;
uniform vec3 mean_lin[15];
uniform vec3 target_lin[15];
uniform float tile[15];
uniform sampler2D mtn_nc : filter_linear;
uniform vec4 mtn_rect;  // x0, z0, width, depth
uniform float ew = 1.0;  // 1 = tinted to the EW palette, 0 = natural texture colours
uniform float detail = 0.85;  // texture contrast
uniform vec4 road_seg[160];
uniform vec2 road_info[160];  // width, kind
uniform int road_n = 0;
uniform vec4 rail_seg[48];
uniform int rail_n = 0;
varying vec3 wp;
varying vec3 wn;
varying vec4 w0;
varying vec4 w1;
varying vec2 w2;
void vertex() {
	wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	w0 = CUSTOM0;
	w1 = CUSTOM1;
	w2 = UV;
}
vec3 to_lin(vec3 c) { return pow(c, vec3(2.2)); }
vec3 to_srgb(vec3 c) { return pow(max(c, vec3(0.0)), vec3(1.0 / 2.2)); }
// one layer, with a second rotated sample blended in by macro noise to hide tiling,
// recoloured towards the target colour (EW) or only brightness-matched (natural)
vec3 layer(int l, vec2 p, vec3 target) {
	vec2 uv = p / tile[l];
	vec3 a = texture(layers, vec3(uv, float(l))).rgb;
	vec2 uv2 = mat2(vec2(0.8, -0.6), vec2(0.6, 0.8)) * uv * 0.71 + vec2(0.37, 0.11);
	vec3 b = texture(layers, vec3(uv2, float(l))).rgb;
	vec3 c = mix(a, b, smoothstep(0.35, 0.65, texture(macro, p * 0.013).r));
	vec3 m = mean_lin[l];
	c = m + (c - m) * detail;
	vec3 g_ew = target / max(m, vec3(1e-4));
	float lum_m = dot(m, vec3(0.3, 0.59, 0.11));
	float g_nat = dot(target, vec3(0.3, 0.59, 0.11)) / max(lum_m, 1e-4);
	return c * mix(vec3(g_nat), g_ew, ew);
}
vec3 lay(int l, vec2 p) { return layer(l, p, target_lin[l]); }
float hash1(vec2 c) { return fract(sin(dot(c, vec2(12.9898, 78.233))) * 43758.5453); }
vec2 hash2(vec2 c) { return fract(sin(vec2(dot(c, vec2(127.1, 311.7)), dot(c, vec2(269.5, 183.3)))) * 43758.5453); }
// Farmland: irregular blocks (Voronoi, ~6 m) bordered by hedgerows; every block has its
// own orientation and is cut into strips/plots of its own size; every plot its own crop.
vec3 fields(vec2 p) {
	vec2 g = floor(p / 6.0);
	float d1 = 1e9;
	float d2 = 1e9;
	vec2 id = vec2(0.0);
	vec2 id2 = vec2(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 c = g + vec2(float(i), float(j));
			vec2 q = (c + 0.15 + 0.7 * hash2(c)) * 6.0;
			float d = length(p - q);
			if (d < d1) { d2 = d1; id2 = id; d1 = d; id = c; } else if (d < d2) { d2 = d; id2 = c; }
		}
	}
	float border = (d2 - d1) * 0.5;  // distance to the block edge
	float hb = hash1(id + 7.1);
	float a = hash1(id) * 3.14159;
	if (hash1(id + 3.3) < 0.5) a = 0.35 + (hash1(id + 5.5) - 0.5) * 0.3;  // many blocks follow the main road grid
	float u = p.x * cos(a) - p.y * sin(a);
	float v = p.x * sin(a) + p.y * cos(a);
	float sw = mix(0.7, 2.4, hash1(id + 1.7));  // strip width
	float sl = mix(1.6, 6.0, hash1(id + 2.9));  // plot length along the strip
	float si = floor(u / sw);
	float vo = v + hash1(vec2(si, id.x)) * sl;  // staggered plot ends
	float pi = floor(vo / sl);
	vec2 pid = vec2(si, pi) + id * 17.0;
	float hp = hash1(pid);
	if (hb < 0.3) hp = hash1(id + 9.0);  // some blocks are one big field
	// crop types: layer, colour (EW palette), furrow strength, furrow spacing (m)
	int ls[7] = int[7](1, 2, 13, 3, 0, 1, 2);
	vec3 pal[7] = vec3[7](vec3(0.21, 0.26, 0.11), vec3(0.36, 0.31, 0.15), vec3(0.25, 0.19, 0.12),
		vec3(0.31, 0.30, 0.165), vec3(0.24, 0.25, 0.12), vec3(0.16, 0.21, 0.085), vec3(0.34, 0.33, 0.19));
	float fs[7] = float[7](0.08, 0.06, 0.22, 0.10, 0.0, 0.14, 0.04);
	float fp[7] = float[7](0.10, 0.08, 0.07, 0.12, 1.0, 0.16, 0.09);
	int k = int(hp * 7.0) % 7;
	vec3 tint = pal[k] * (0.9 + 0.2 * hash1(pid + 4.4));
	vec3 col = layer(ls[k], p + pid * 3.7, to_lin(tint));
	// furrows along the strip (or across it for some plots)
	float fu = hash1(pid + 8.8) < 0.3 ? v : u;
	col *= 1.0 - fs[k] * (0.5 + 0.5 * sin(fu * 6.2832 / fp[k]));
	// thin tracks between plots, hedgerows between blocks
	float eu = min(mod(u, sw), sw - mod(u, sw));
	float ev = min(mod(vo, sl), sl - mod(vo, sl));
	float inner = hb < 0.3 ? 1.0 : smoothstep(0.02, 0.06, min(eu, ev));
	col = mix(col * 0.72, col, inner);
	// about half of the block borders are hedgerows, the rest dirt field tracks
	vec2 pair = id + id2;
	if (hash1(pair * 0.37 + 1.1) < 0.5) {
		vec3 hedge = layer(4, p, to_lin(vec3(0.13, 0.16, 0.07)));
		return mix(hedge, col, smoothstep(0.05, 0.13, border));
	}
	vec3 track = layer(13, p, to_lin(vec3(0.33, 0.30, 0.20)));
	return mix(track, col, smoothstep(0.03, 0.08, border));
}
vec2 hex_round(vec2 qr) {
	vec3 c = vec3(qr.x, qr.y, -qr.x - qr.y);
	vec3 r = round(c);
	vec3 d = abs(r - c);
	if (d.x > d.y && d.x > d.z) r.x = -r.y - r.z; else if (d.y > d.z) r.y = -r.x - r.z;
	return r.xy;
}
vec2 seg(vec2 p, vec4 s) {
	vec2 a = s.xy;
	vec2 ab = s.zw - s.xy;
	float l = length(ab);
	float t = clamp(dot(p - a, ab) / max(l * l, 1e-6), 0.0, 1.0);
	return vec2(length(p - a - ab * t), t * l);
}
void fragment() {
	vec2 p = wp.xz;
	float mn = texture(macro, p * 0.02 + vec2(0.5, 0.2)).r;
	vec4 nc = texture(mtn_nc, (p - mtn_rect.xy) / mtn_rect.zw);
	vec2 nxz = nc.rg * 2.0 - 1.0;
	vec3 mnw = normalize(vec3(nxz.x, sqrt(max(1.0 - dot(nxz, nxz), 0.0)), nxz.y));
	float cav = nc.b * 2.0 - 1.0;
	float rkw = clamp(w1.x, 0.0, 1.0);
	vec3 nw = normalize(mix(normalize(wn), mnw, rkw));
	// ground classes -> texture layers (two layers per class mixed by macro noise)
	float wt[10] = float[10](w0.x, w0.y, w0.z, w0.w, w1.x, w1.y, w1.z, w1.w, w2.x, 0.0);
	int la[9] = int[9](0, 2, 4, 6, 9, 10, 11, 13, 14);
	int lb[9] = int[9](1, 3, 5, 7, 8, 10, 12, 13, 14);
	vec3 col = vec3(0.0);
	float tot = 0.0;
	for (int i = 0; i < 9; i++) {
		if (wt[i] < 0.01) continue;
		float t = smoothstep(0.3, 0.7, mn);
		if (i == 4) t = smoothstep(0.2, 0.5, 1.0 - nw.y);  // cliffs on steep rock
		vec3 c = la[i] == lb[i] ? lay(la[i], p) : mix(lay(la[i], p), lay(lb[i], p), t);
		if (i == 4) c = mix(target_lin[9], c, 0.45);  // calmer rock: the landform carries the detail
		col += c * wt[i];
		tot += wt[i];
	}
	col /= max(tot, 1e-4);
	float farm = smoothstep(0.35, 0.7, w2.y);
	if (farm > 0.0) col = mix(col, fields(p), farm);
	col = to_srgb(col);
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
	float rmin = 1e9;
	for (int i = 0; i < road_n; i++) {
		vec2 s = seg(p, road_seg[i]);
		float w = road_info[i].x * 0.5;
		if (s.x < w + 0.12) {
			vec3 rc = road_info[i].y > 0.5 ? vec3(0.19, 0.19, 0.18) : vec3(0.15, 0.15, 0.145);
			rc = mix(rc, vec3(0.34, 0.32, 0.26), smoothstep(w - 0.08, w, s.x));
			if (road_info[i].y < 0.5 && s.x < 0.03 && fract(s.y / 0.9) < 0.5) rc = vec3(0.62, 0.60, 0.52);
			float a = 1.0 - smoothstep(w, w + 0.12, s.x);
			if (s.x < rmin) { col = mix(col, rc, a); rmin = s.x; }
		}
	}
	col = to_lin(col);
	vec3 L = normalize(vec3(0.5, 0.55, -0.5));
	float shade = clamp(dot(nw, L), 0.0, 1.0);
	float rk = rkw;
	col *= mix(0.62, 1.08, smoothstep(0.35, 0.95, shade)) * (1.0 - rk) + rk;
	// rock: low raking light from the east so gully walls read as light/dark stripes (Civ5 look)
	float rake = clamp(dot(nw, normalize(vec3(0.85, 0.45, -0.1))), 0.0, 1.0);
	col *= mix(1.0, mix(0.42, 1.3, rake), rk);
	// gullies dark, crests and spurs light: the Civ5 fluted look
	col *= mix(1.0, mix(0.35, 1.3, smoothstep(-0.7, 0.6, cav)), rk);
	col *= 0.9 + 0.2 * mn;  // large-scale light/dark patches
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
	ALBEDO = mix(col, col * 0.55, line * 0.45);
	NORMAL = normalize(mix(NORMAL, (VIEW_MATRIX * vec4(mnw, 0.0)).xyz, rkw));
	ROUGHNESS = 0.95;
}
"""
	sm.shader = sh
	var li := _layer_images()
	var ta := Texture2DArray.new()
	ta.create_from_images(li[0])
	sm.set_shader_parameter("layers", ta)
	sm.set_shader_parameter("mean_lin", li[1])
	var targets := []
	var tiles := []
	for l in LAYERS:
		var t: Color = l[3].srgb_to_linear()
		targets.append(Vector3(t.r, t.g, t.b))
		tiles.append(l[2])
	sm.set_shader_parameter("target_lin", targets)
	sm.set_shader_parameter("tile", tiles)
	sm.set_shader_parameter("ew", float(OS.get_environment("EW")))
	var nci := Image.load_from_file(OS.get_environment("MTN") + "/mountain_nc.png")
	nci.generate_mipmaps()
	sm.set_shader_parameter("mtn_nc", ImageTexture.create_from_image(nci))
	var st: float = mtn_info["step"]
	sm.set_shader_parameter("mtn_rect", Vector4(mtn_info["x0"], mtn_info["z0"], (float(mtn_info["nx"]) - 1.0) * st, (float(mtn_info["nz"]) - 1.0) * st))
	var fn := FastNoiseLite.new()
	fn.seed = 3
	fn.frequency = 0.02
	fn.fractal_octaves = 3
	var mimg := fn.get_seamless_image(256, 256)
	sm.set_shader_parameter("macro", ImageTexture.create_from_image(mimg))
	var segs := []
	var info := []
	for rd in roads:
		var pts: PackedVector2Array = rd[0]
		for i in pts.size() - 1:
			segs.append(Vector4(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y))
			info.append(Vector2(rd[1], rd[2]))
	sm.set_shader_parameter("road_seg", segs)
	sm.set_shader_parameter("road_info", info)
	sm.set_shader_parameter("road_n", segs.size())
	var rs := []
	for i in rail.size() - 1:
		rs.append(Vector4(rail[i].x, rail[i].y, rail[i + 1].x, rail[i + 1].y))
	sm.set_shader_parameter("rail_seg", rs)
	sm.set_shader_parameter("rail_n", rs.size())
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
