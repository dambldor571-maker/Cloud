class_name UnitStudio
extends Node
## The unit scene shared by the live preview and the sprite render: camera at
## 65 degrees, sun from the north-east, our weathering shader, and the same
## hull/turret layer render as tools/render_units.gd (the game's sprite format).
##
## Unit space: +X = the vehicle's front, +Y = up, metres, ground at y = 0.
## Map headings are degrees counter-clockwise from east (0 = east, 90 = north).

signal progress(done: int, total: int, text: String)

const HEX_R := 5.5
const ELEVATION := 65.0
const SUN_AZIMUTH := 45.0  # clockwise from north
const SUN_ELEVATION := 75.0
const FRAMES := 18
const SUPERSAMPLE := 4
const PX_PER_M := 320.0 / 11.0
const HULL_SIZE := Vector2i(320, 320)
const TURRET_SIZE := Vector2i(416, 416)
const SHADOW_OPACITY := 0.6
const RING_R := 34.0 / 0.3 / PX_PER_M  # the game's side ring, in metres
const GRASS_M := 30.0  # metres covered by assets/grass.jpg
const LAYER_PREVIEW := 2  # shadow catcher: seen only by the preview camera
const LAYER_SHADOW := 4  # white ground of the shadow pass

const ROLES := ["hull", "hull_lower", "turret", "gun", "wheel", "sprocket", "idler", "track", "other", "hide"]
const ROLE_NAMES := {"hull": "Корпус", "hull_lower": "Нижній корпус", "turret": "Башта", "gun": "Гармата",
	"wheel": "Катки", "sprocket": "Ведучі колеса", "idler": "Напрямні колеса", "track": "Гусениці",
	"other": "Інше", "hide": "Прибрати"}
## Default paint per role (sRGB), the T-72 colours of tools/render_units.gd.
const ROLE_COLORS := {"hull": Color(0.20, 0.205, 0.18), "hull_lower": Color(0.15, 0.145, 0.12),
	"turret": Color(0.20, 0.205, 0.18), "gun": Color(0.20, 0.205, 0.18), "wheel": Color(0.19, 0.185, 0.155),
	"sprocket": Color(0.20, 0.21, 0.17), "idler": Color(0.20, 0.21, 0.17), "track": Color(0.24, 0.22, 0.19),
	"other": Color(0.20, 0.205, 0.18), "hide": Color(0.20, 0.205, 0.18)}
const RUNNING_GEAR := ["wheel", "sprocket", "idler", "track"]  # no sun shadow on them, so they stay readable
const HULL_ROLES := ["hull", "hull_lower", "wheel", "sprocket", "idler", "track"]
const SIDE_COLORS := [Color(0.18, 0.44, 0.84), Color(0.84, 0.23, 0.18)]

## Settings; to_config()/from_config() turn them into the .unit.json format.
var unit_name := "unit"
var file_path := ""
var length_m := 9.35
var yaw := 0.0
var hull_offset_m := 0.0
var own_paint := true
var tint := Color(0.5, 0.56, 0.4)
var roughness := 0.82
var weathering := 0.6
var mud_height := 1.1
var recoil_m := 0.38
## Parts, one entry per name group: {key, role, color, shadow, meshes}
var groups: Array = []
## Preview state
var hull_deg := 0.0
var turret_deg := 0.0
var turret_follows := true
var recoil_step := 0
var zoom_m := 22.0

var viewport: SubViewport
var camera: Camera3D
var sun: DirectionalLight3D
var fill: DirectionalLight3D
var env: Environment
var shadow_ground: MeshInstance3D
var unit_root := Node3D.new()
var model_fix := Node3D.new()
var turret_pivot := Node3D.new()
var gun_slide := Node3D.new()
var model: Node3D
var pivot_m := Vector2.ZERO
var has_turret := false
var busy := false

var _noise_lo: ImageTexture
var _noise_hi: ImageTexture
var _shaders := {}
var _catcher: ShaderMaterial


## Builds the scene inside the preview viewport.
func setup(vp: SubViewport) -> void:
	viewport = vp
	vp.msaa_3d = Viewport.MSAA_4X
	vp.transparent_bg = true
	vp.positional_shadow_atlas_size = 0
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.cull_mask = 1 | LAYER_PREVIEW
	var e := deg_to_rad(ELEVATION)
	camera.position = Vector3(0, sin(e), cos(e)) * 40.0
	vp.add_child(camera)
	camera.look_at(Vector3.ZERO)
	camera.far = 200.0

	sun = DirectionalLight3D.new()
	sun.light_energy = 2.3
	sun.light_color = Color(1.0, 0.95, 0.85)
	var az := deg_to_rad(SUN_AZIMUTH)
	var el := deg_to_rad(SUN_ELEVATION)
	var to_sun := Vector3(cos(el) * sin(az), sin(el), -cos(el) * cos(az))
	vp.add_child(sun)
	sun.look_at_from_position(to_sun * 20.0, Vector3.ZERO)
	sun.shadow_enabled = true
	sun.shadow_blur = 0.4
	sun.shadow_bias = 0.03
	sun.shadow_normal_bias = 1.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 100.0
	fill = DirectionalLight3D.new()
	fill.light_energy = 0.4
	fill.light_color = Color(0.75, 0.82, 1.0)
	fill.rotation_degrees = Vector3(-25, 150, 0)
	fill.light_cull_mask = 0xFFFFF & ~LAYER_PREVIEW  # the map ground is lit by the sun only
	vp.add_child(fill)

	env = Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	var sky := Sky.new()
	sky.sky_material = ProceduralSkyMaterial.new()
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.32
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.05
	env.ssao_enabled = true
	env.ssao_radius = 0.25
	env.ssao_intensity = 7.0
	env.ssao_power = 2.2
	env.ssao_detail = 1.0
	env.ssao_light_affect = 0.25
	env.adjustment_enabled = true
	env.adjustment_saturation = 0.95
	env.adjustment_contrast = 1.12
	var we := WorldEnvironment.new()
	we.environment = env
	vp.add_child(we)

	_add_map_ground()
	shadow_ground = MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(60, 60)
	shadow_ground.mesh = plane
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color.WHITE
	gm.roughness = 1.0
	shadow_ground.material_override = gm
	shadow_ground.layers = LAYER_SHADOW
	shadow_ground.visible = false
	vp.add_child(shadow_ground)

	vp.add_child(unit_root)
	unit_root.add_child(model_fix)
	unit_root.add_child(turret_pivot)
	turret_pivot.add_child(gun_slide)
	_noise_lo = _noise_tex(11, 0.012, 4)
	_noise_hi = _noise_tex(12, 0.05, 5)
	apply_look()
	update_camera()


## Shadow catcher: the map itself is drawn in 2D under the preview (exactly the
## game's colours, no 3D tone mapping); here only the unit's shadow is laid on it.
func _add_map_ground() -> void:
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode blend_mix, depth_draw_never, ambient_light_disabled, specular_disabled, diffuse_lambert, cull_disabled;
uniform float shadow_opacity = 0.6;
void fragment() { ALBEDO = vec3(0.0); ALPHA = 1.0; }
void light() { ALPHA = (1.0 - ATTENUATION) * shadow_opacity; DIFFUSE_LIGHT = vec3(0.0); }
"""
	var mat := ShaderMaterial.new()
	mat.shader = sh
	mat.set_shader_parameter("shadow_opacity", SHADOW_OPACITY)
	_catcher = mat
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(160, 160)
	ground.mesh = plane
	ground.material_override = mat
	ground.layers = LAYER_PREVIEW
	ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	viewport.add_child(ground)


func update_camera() -> void:
	camera.size = zoom_m * sin(deg_to_rad(ELEVATION))


# --- Loading ------------------------------------------------------------------

## Loads a .glb/.gltf/.fbx/.obj file. Returns "" or an error text.
func load_model(path: String) -> String:
	var scene: Node3D
	var ext := path.get_extension().to_lower()
	if ext == "obj":
		scene = ObjLoader.load_obj(path)
		if scene == null:
			return "не вдалося прочитати OBJ"
	elif ext in ["glb", "gltf", "fbx"]:
		var doc: GLTFDocument = FBXDocument.new() if ext == "fbx" else GLTFDocument.new()
		var state: GLTFState = FBXState.new() if ext == "fbx" else GLTFState.new()
		var err := doc.append_from_file(path, state)
		if err != OK:
			return "помилка читання (%s)" % error_string(err)
		scene = doc.generate_scene(state) as Node3D
		if scene == null:
			return "у файлі немає 3D-сцени"
		_bake_importer_meshes(scene)
	else:
		return "непідтримуваний формат .%s" % ext
	_set_model(scene)
	file_path = path
	return ""


func _set_model(scene: Node3D) -> void:
	if model:
		model.queue_free()
	for c in turret_pivot.get_children():
		if c != gun_slide:
			c.queue_free()
	for c in gun_slide.get_children():
		c.queue_free()
	model = scene
	model_fix.add_child(model)
	var meshes: Array[MeshInstance3D] = []
	for n in model.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		if mi.mesh == null:
			continue
		mi.set_meta("home", mi.get_parent())
		meshes.append(mi)
	_build_groups(meshes)
	apply_materials()
	refit()
	auto_hull_offset()


## Parts are grouped by the first word of their name (Wheel_L_1, Wheel_R_2 -> Wheel).
func _build_groups(meshes: Array[MeshInstance3D]) -> void:
	var by_key := _group_by(meshes, true)
	if by_key.size() < 3 and meshes.size() > 3:
		by_key = _group_by(meshes, false)
	groups.clear()
	for key in by_key:
		var role := guess_role(key)
		groups.append({"key": key, "role": role, "color": ROLE_COLORS[role], "shadow": role != "gun",
			"meshes": by_key[key]})


func _group_by(meshes: Array[MeshInstance3D], first_word: bool) -> Dictionary:
	var out := {}
	var re := RegEx.create_from_string("[_.\\s:-]")
	for mi in meshes:
		var n := String(mi.name)
		var key := n
		if first_word:
			var m := re.search(n)
			if m and m.get_start() > 0:
				key = n.substr(0, m.get_start())
		if not out.has(key):
			out[key] = []
		out[key].append(mi)
	return out


static func guess_role(name: String) -> String:
	var n := name.to_lower()
	var rules := [["lower", "hull_lower"], ["нижн", "hull_lower"], ["turret", "turret"], ["tower", "turret"],
		["башт", "turret"], ["gun", "gun"], ["barrel", "gun"], ["cannon", "gun"], ["ствол", "gun"],
		["гармат", "gun"], ["mantlet", "gun"], ["sprocket", "sprocket"], ["idler", "idler"], ["track", "track"],
		["гусен", "track"], ["wheel", "wheel"], ["каток", "wheel"], ["колес", "wheel"], ["hull", "hull"],
		["body", "hull"], ["chassis", "hull"], ["корпус", "hull"]]
	for r in rules:
		if n.contains(r[0]):
			return r[1]
	return "other"


# --- Fitting and pose -----------------------------------------------------------

## Scales the model to length_m (longest horizontal side), turns it by yaw,
## stands it on the ground centred at the origin and rebuilds the turret pivot.
func refit() -> void:
	if model == null:
		return
	_reset_pose()
	_send_turret_home()
	model_fix.scale = Vector3.ONE
	model_fix.position = Vector3.ZERO
	model_fix.rotation_degrees = Vector3(0, yaw, 0)
	var box := _bounds(_visible_meshes())
	var s := length_m / maxf(maxf(box.size.x, box.size.z), 0.0001)
	model_fix.scale = Vector3.ONE * s
	box = _bounds(_visible_meshes())
	model_fix.position = -Vector3(box.get_center().x, box.position.y, box.get_center().z)
	_build_turret()
	apply_pose()


func _reset_pose() -> void:
	unit_root.position = Vector3.ZERO
	unit_root.rotation = Vector3.ZERO
	turret_pivot.rotation = Vector3.ZERO
	gun_slide.position = Vector3.ZERO


func _send_turret_home() -> void:
	for g in groups:
		for mi in g["meshes"]:
			var home: Node = mi.get_meta("home")
			if mi.get_parent() != home:
				mi.reparent(home, true)


## Turret and gun parts move under a pivot at the turret ring (the centre of
## the turret parts), the gun under a slide for the recoil.
func _build_turret() -> void:
	var turret: Array[MeshInstance3D] = []
	var guns: Array[MeshInstance3D] = []
	for g in groups:
		for mi in g["meshes"]:
			if g["role"] == "turret":
				turret.append(mi)
			elif g["role"] == "gun":
				guns.append(mi)
	has_turret = not (turret.is_empty() and guns.is_empty())
	if not has_turret:
		return
	var box := _bounds(turret if not turret.is_empty() else guns)
	var c := unit_root.global_transform.affine_inverse() * box.get_center()
	turret_pivot.position = Vector3(c.x, 0.0, c.z)
	pivot_m = Vector2(c.x, c.z)
	for mi in turret:
		mi.reparent(turret_pivot, true)
	for mi in guns:
		mi.reparent(gun_slide, true)


## Hull centre (hull and running gear, not the gun) behind the model centre.
func auto_hull_offset() -> void:
	if model == null:
		return
	var keep_p := unit_root.position
	var keep_r := unit_root.rotation
	var keep_t := turret_pivot.rotation
	_reset_pose()
	var hull: Array[MeshInstance3D] = []
	for g in groups:
		if g["role"] in HULL_ROLES:
			hull.append_array(g["meshes"])
	if not hull.is_empty():
		hull_offset_m = snappedf(-_bounds(hull).get_center().x, 0.01)
	unit_root.position = keep_p
	unit_root.rotation = keep_r
	turret_pivot.rotation = keep_t
	apply_pose()


## Map heading -> model yaw, corrected for the tilted camera so the projected
## heading matches the map direction (as in tools/render_units.gd).
static func yaw_for_angle(deg: float) -> float:
	var a := deg_to_rad(deg)
	return rad_to_deg(atan2(sin(a) / sin(deg_to_rad(ELEVATION)), cos(a)))


func apply_pose() -> void:
	var t_deg := hull_deg if turret_follows else turret_deg
	unit_root.rotation_degrees = Vector3(0, yaw_for_angle(hull_deg), 0)
	var a := deg_to_rad(hull_deg)
	# The game shifts the sprite forward so the hull, not hull + gun, sits on the hex centre.
	unit_root.position = Vector3(cos(a), 0, -sin(a)) * hull_offset_m
	turret_pivot.rotation_degrees = Vector3(0, yaw_for_angle(t_deg) - yaw_for_angle(hull_deg), 0)
	gun_slide.position = Vector3(-recoil_steps()[recoil_step], 0, 0)


func recoil_steps() -> Array:
	return [0.0, snappedf(recoil_m / 3.0, 0.001), snappedf(recoil_m * 2.0 / 3.0, 0.001), recoil_m]


func _visible_meshes() -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	for g in groups:
		if g["role"] != "hide":
			out.append_array(g["meshes"])
	return out


func _bounds(meshes: Array) -> AABB:
	var box := AABB()
	var first := true
	for mi in meshes:
		var b: AABB = (mi as MeshInstance3D).global_transform * (mi as MeshInstance3D).get_aabb()
		box = b if first else box.merge(b)
		first = false
	return box


# --- Materials --------------------------------------------------------------------

func apply_materials() -> void:
	var cache := {}
	for g in groups:
		var role: String = g["role"]
		for mi in g["meshes"]:
			var m := mi as MeshInstance3D
			m.visible = role != "hide"
			m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if g["shadow"] \
				else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			for i in m.mesh.get_surface_count():
				var mat: ShaderMaterial
				if own_paint:
					if role == "wheel":
						mat = _paint_material(g)  # tyre band needs this wheel's centre
						var box := m.get_aabb()
						mat.set_shader_parameter("rubber_tyre", true)
						mat.set_shader_parameter("wheel_center", box.get_center())
						mat.set_shader_parameter("tyre_radius", 0.78 * maxf(box.size.x, box.size.y) / 2.0)
					else:
						if not cache.has(g["key"]):
							cache[g["key"]] = _paint_material(g)
						mat = cache[g["key"]]
				else:
					mat = _file_material(m.mesh.surface_get_material(i), g)
				m.set_surface_override_material(i, mat)


func _paint_material(g: Dictionary) -> ShaderMaterial:
	var sm := ShaderMaterial.new()
	var role: String = g["role"]
	var no_shadow := role in RUNNING_GEAR
	sm.shader = _weathered_shader(no_shadow)
	var lin: Color = (g["color"] as Color).srgb_to_linear()
	sm.set_shader_parameter("has_albedo", false)
	sm.set_shader_parameter("base_color", Vector3(lin.r, lin.g, lin.b))
	if no_shadow:
		sm.set_shader_parameter("lift", 0.45)
	if role == "track":
		sm.set_shader_parameter("track_links", true)
	_weather_params(sm)
	_texture_params(sm, g["key"])
	return sm


func _file_material(src: Material, g: Dictionary) -> ShaderMaterial:
	var sm := ShaderMaterial.new()
	sm.shader = _weathered_shader(g["role"] in RUNNING_GEAR)
	var base := src as BaseMaterial3D
	var lin := tint.srgb_to_linear()
	if base and base.albedo_texture:
		sm.set_shader_parameter("albedo_tex", base.albedo_texture)
		sm.set_shader_parameter("tint", Vector3(lin.r, lin.g, lin.b) * Vector3(base.albedo_color.r,
			base.albedo_color.g, base.albedo_color.b))
		if base.normal_enabled and base.normal_texture:
			sm.set_shader_parameter("normal_tex", base.normal_texture)
			sm.set_shader_parameter("has_normal", true)
	else:
		var c := (base.albedo_color if base else Color(0.6, 0.6, 0.6)).srgb_to_linear()
		sm.set_shader_parameter("has_albedo", false)
		sm.set_shader_parameter("base_color", Vector3(c.r * lin.r, c.g * lin.g, c.b * lin.b))
	_weather_params(sm)
	_texture_params(sm, g["key"])
	return sm


# --- Own texture maps -----------------------------------------------------------------

const TEXTURE_MAPS := ["albedo", "normal", "ao", "roughness", "metallic_map"]
const TEXTURE_DEFAULTS := {"tint": [1.0, 1.0, 1.0], "normal_strength": 1.8, "flip_green": false,
	"ao_strength": 1.0, "metallic": 0.0, "uv_scale": 1.0}
const ALL_PARTS := "*"  # texture set for the whole model; a part's own set overrides it

## Texture sets by part key (or ALL_PARTS): map name -> file path, plus the
## TEXTURE_DEFAULTS values.
var textures := {}
var checker := false
var _tex_cache := {}


## The settings a part ends up with: whole-model set, then the part's own.
func texture_set(key: String) -> Dictionary:
	var out := TEXTURE_DEFAULTS.duplicate()
	out.merge(textures.get(ALL_PARTS, {}), true)
	out.merge(textures.get(key, {}), true)
	return out


func load_texture(path: String) -> Texture2D:
	if path == "":
		return null
	if not _tex_cache.has(path):
		var img := Image.load_from_file(path)
		if img == null or img.is_empty():
			return null
		img.generate_mipmaps()
		_tex_cache[path] = ImageTexture.create_from_image(img)
	return _tex_cache[path]


func _texture_params(sm: ShaderMaterial, key: String) -> void:
	var t := texture_set(key)
	sm.set_shader_parameter("checker", checker)
	sm.set_shader_parameter("uv_scale", Vector2.ONE * float(t["uv_scale"]))
	sm.set_shader_parameter("paint_metallic", float(t["metallic"]))
	var albedo := load_texture(t.get("albedo", ""))
	if albedo:
		var c := _color(t["tint"]).srgb_to_linear()
		sm.set_shader_parameter("has_albedo", true)
		sm.set_shader_parameter("albedo_tex", albedo)
		sm.set_shader_parameter("tint", Vector3(c.r, c.g, c.b))
	var normal := load_texture(t.get("normal", ""))
	if normal:
		sm.set_shader_parameter("normal_tex", normal)
		sm.set_shader_parameter("has_normal", true)
		sm.set_shader_parameter("flip_green", bool(t["flip_green"]))
	if sm.get_shader_parameter("has_normal"):
		sm.set_shader_parameter("normal_depth", float(t["normal_strength"]))
	var ao := load_texture(t.get("ao", ""))
	if ao:
		sm.set_shader_parameter("ao_tex", ao)
		sm.set_shader_parameter("has_ao", true)
		sm.set_shader_parameter("ao_strength", float(t["ao_strength"]))
	var rough := load_texture(t.get("roughness", ""))
	if rough:
		sm.set_shader_parameter("rough_tex", rough)
		sm.set_shader_parameter("has_rough_tex", true)
	var metal := load_texture(t.get("metallic_map", ""))
	if metal:
		sm.set_shader_parameter("metal_tex", metal)
		sm.set_shader_parameter("has_metal_tex", true)


# --- Light and shadows ----------------------------------------------------------------

## Scene lighting; the defaults are the look of tools/render_units.gd.
const LOOK_DEFAULTS := {"sun_energy": 2.3, "sun_blur": 0.4, "fill_energy": 0.4, "ambient": 0.32,
	"exposure": 1.05, "contrast": 1.12, "saturation": 0.95, "shadow_opacity": 0.6,
	"ao_intensity": 7.0, "ao_radius": 0.25, "ao_power": 2.2, "ao_detail": 1.0, "ao_light_affect": 0.25}
var look := LOOK_DEFAULTS.duplicate()


func apply_look() -> void:
	sun.light_energy = look["sun_energy"]
	sun.shadow_blur = look["sun_blur"]
	fill.light_energy = look["fill_energy"]
	env.ambient_light_energy = look["ambient"]
	env.tonemap_exposure = look["exposure"]
	env.adjustment_contrast = look["contrast"]
	env.adjustment_saturation = look["saturation"]
	env.ssao_intensity = look["ao_intensity"]
	env.ssao_radius = look["ao_radius"]
	env.ssao_power = look["ao_power"]
	env.ssao_detail = look["ao_detail"]
	env.ssao_light_affect = look["ao_light_affect"]
	if _catcher:
		_catcher.set_shader_parameter("shadow_opacity", look["shadow_opacity"])


func _weather_params(sm: ShaderMaterial) -> void:
	sm.set_shader_parameter("noise_lo", _noise_lo)
	sm.set_shader_parameter("noise_hi", _noise_hi)
	sm.set_shader_parameter("mud_height", maxf(mud_height, 0.01))
	sm.set_shader_parameter("paint_roughness", roughness)
	var amounts := {"mud_amount": 0.85, "dust_amount": 0.3, "chip_amount": 0.8, "streak_amount": 0.7}
	for p in amounts:
		var v: float = amounts[p] * weathering
		if p == "mud_amount" and mud_height <= 0.0:
			v = 0.0
		sm.set_shader_parameter(p, v)


func _weathered_shader(no_shadow: bool) -> Shader:
	if not _shaders.has(no_shadow):
		var sh: Shader = load("res://core/weathered.gdshader")
		if no_shadow:
			var copy := Shader.new()
			copy.code = sh.code.replace("render_mode diffuse_burley, cull_disabled;",
				"render_mode diffuse_burley, cull_disabled, shadows_disabled;")
			sh = copy
		_shaders[no_shadow] = sh
	return _shaders[no_shadow]


func _noise_tex(seed_value: int, freq: float, octaves: int) -> ImageTexture:
	var n := FastNoiseLite.new()
	n.seed = seed_value
	n.frequency = freq
	n.fractal_octaves = octaves
	var img := n.get_seamless_image(512, 512)
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


## FBX scenes come back with ImporterMeshInstance3D nodes, which don't render.
func _bake_importer_meshes(scene: Node) -> void:
	for n in scene.find_children("*", "ImporterMeshInstance3D", true, false):
		var imi := n as ImporterMeshInstance3D
		var mi := MeshInstance3D.new()
		mi.name = imi.name
		mi.transform = imi.transform
		mi.mesh = imi.mesh.get_mesh() if imi.mesh else null
		imi.get_parent().add_child(mi)
		imi.get_parent().move_child(mi, imi.get_index())
		for c in imi.get_children():
			c.reparent(mi, false)
		imi.free()


# --- Settings file ------------------------------------------------------------------

static func _rgb(c: Color) -> Array:
	return [snappedf(c.r, 0.001), snappedf(c.g, 0.001), snappedf(c.b, 0.001)]


static func _color(a: Array) -> Color:
	return Color(float(a[0]), float(a[1]), float(a[2]))


func to_config() -> Dictionary:
	var parts := {}
	var paint := {}
	var no_cast := []
	for g in groups:
		parts[g["key"]] = g["role"]
		paint[g["key"]] = _rgb(g["color"])
		if not g["shadow"] and g["role"] != "hide":
			no_cast.append(g["key"])
	var cfg := {"name": unit_name, "file": file_path, "length_m": length_m, "yaw": yaw,
		"hull_offset_m": hull_offset_m, "paint_source": "own" if own_paint else "file", "tint": _rgb(tint),
		"roughness": roughness, "weathering": weathering, "mud_height": mud_height,
		"parts": parts, "part_colors": paint, "no_cast": no_cast, "textures": textures, "look": look,
		"elevation": ELEVATION, "sun": {"azimuth": SUN_AZIMUTH, "elevation": SUN_ELEVATION}, "frames": FRAMES}
	if has_turret:
		cfg["turret"] = {"pivot_m": [snappedf(pivot_m.x, 0.001), snappedf(pivot_m.y, 0.001)],
			"recoil": {"steps_m": recoil_steps()}}
	return cfg


## Applies saved settings to the open model (parts are matched by name).
func from_config(cfg: Dictionary) -> void:
	unit_name = cfg.get("name", unit_name)
	length_m = float(cfg.get("length_m", length_m))
	yaw = float(cfg.get("yaw", yaw))
	own_paint = cfg.get("paint_source", "own") != "file"
	if cfg.has("tint"):
		tint = _color(cfg["tint"])
	roughness = float(cfg.get("roughness", roughness))
	weathering = float(cfg.get("weathering", weathering))
	mud_height = float(cfg.get("mud_height", mud_height))
	if cfg.has("turret"):
		recoil_m = float(cfg["turret"]["recoil"]["steps_m"].back())
	textures = cfg.get("textures", {}).duplicate(true)
	look = LOOK_DEFAULTS.duplicate()
	look.merge(cfg.get("look", {}), true)
	apply_look()
	var parts: Dictionary = cfg.get("parts", {})
	var colors: Dictionary = cfg.get("part_colors", {})
	var no_cast: Array = cfg.get("no_cast", [])
	for g in groups:
		if parts.has(g["key"]):
			g["role"] = parts[g["key"]]
		if colors.has(g["key"]):
			g["color"] = _color(colors[g["key"]])
		g["shadow"] = not (g["key"] in no_cast)
	apply_materials()
	refit()
	if cfg.has("hull_offset_m"):
		hull_offset_m = float(cfg["hull_offset_m"])
	else:
		auto_hull_offset()
	apply_pose()


# --- Sprite render ------------------------------------------------------------------

## Renders the game sprites into out_dir: <name>_hull_<i>.png, <name>_turret_<i>[_r<k>].png
## and <name>.json (as tools/render_units.gd), or <name>_<i>.png for a model without
## a turret; plus <name>_sheet.png with every heading on grass, and <name>.unit.json.
func render_sprites(out_dir: String) -> String:
	if model == null:
		return "модель не відкрита"
	busy = true
	var rvp := SubViewport.new()
	rvp.world_3d = viewport.find_world_3d()
	rvp.transparent_bg = true
	rvp.msaa_3d = Viewport.MSAA_4X
	rvp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(rvp)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.cull_mask = 1
	var e := deg_to_rad(ELEVATION)
	cam.position = Vector3(0, sin(e), cos(e)) * 30.0 + Vector3(0, 0.8, 0)
	rvp.add_child(cam)
	cam.look_at(Vector3(0, 0.8, 0))
	cam.current = true
	var keep := [hull_deg, turret_deg, turret_follows, recoil_step]
	_reset_pose()
	var base := out_dir.path_join(unit_name)
	var total := FRAMES * (1 + (recoil_steps().size() if has_turret else 0))
	var done := 0
	var hull_parts: Array[MeshInstance3D] = []
	var turret_parts: Array[MeshInstance3D] = []
	for g in groups:
		if g["role"] == "hide":
			continue
		for mi in g["meshes"]:
			if g["role"] in ["turret", "gun"]:
				turret_parts.append(mi)
			else:
				hull_parts.append(mi)
	var meta := {"frames": FRAMES, "px_per_m": PX_PER_M, "elevation": ELEVATION, "hull_offset_m": hull_offset_m}
	var hull_imgs: Array[Image] = []
	var turret_imgs: Array[Image] = []
	var offsets := []
	_set_size(rvp, cam, HULL_SIZE)
	for mi in turret_parts:
		mi.visible = false
	for i in FRAMES:
		unit_root.position = Vector3.ZERO
		unit_root.rotation_degrees = Vector3(0, yaw_for_angle(360.0 * i / FRAMES), 0)
		var img := await _frame(rvp, HULL_SIZE, 0.0, cam)
		hull_imgs.append(img)
		img.save_png("%s_%s%d.png" % [base, "hull_" if has_turret else "", i])
		var p := turret_pivot.global_position
		var d := (cam.unproject_position(Vector3(p.x, 0.0, p.z)) - cam.unproject_position(Vector3.ZERO)) / SUPERSAMPLE
		offsets.append([d.x, d.y])
		done += 1
		progress.emit(done, total, "корпус %d/%d" % [i + 1, FRAMES])
	var hull_anchor := cam.unproject_position(Vector3.ZERO) / SUPERSAMPLE
	for mi in turret_parts:
		mi.visible = true
	if has_turret:
		var deck_y := INF
		for mi in turret_parts:
			deck_y = minf(deck_y, (mi.global_transform * mi.get_aabb()).position.y)
		_set_size(rvp, cam, TURRET_SIZE)
		for mi in hull_parts:
			mi.visible = false
		var steps := recoil_steps()
		for i in FRAMES:
			unit_root.position = Vector3.ZERO
			unit_root.rotation_degrees = Vector3(0, yaw_for_angle(360.0 * i / FRAMES), 0)
			var p := turret_pivot.global_position
			unit_root.position = Vector3(-p.x, 0.0, -p.z)  # turret pivot on the frame's ground anchor
			for k in steps.size():
				gun_slide.position = Vector3(-float(steps[k]), 0, 0)
				var img := await _frame(rvp, TURRET_SIZE, deck_y, cam)
				if k == 0:
					turret_imgs.append(img)
					img.save_png("%s_turret_%d.png" % [base, i])
				else:
					img.save_png("%s_turret_%d_r%d.png" % [base, i, k])
				done += 1
				progress.emit(done, total, "башта %d/%d" % [i + 1, FRAMES])
		gun_slide.position = Vector3.ZERO
		for mi in hull_parts:
			mi.visible = true
		var turret_anchor := cam.unproject_position(Vector3.ZERO) / SUPERSAMPLE
		meta.merge({"layers": true, "hull_anchor": [hull_anchor.x, hull_anchor.y],
			"turret_anchor": [turret_anchor.x, turret_anchor.y], "turret_offsets": offsets,
			"recoil_steps": steps.size()})
	else:
		meta.merge({"anchor": [hull_anchor.x, hull_anchor.y], "directions": FRAMES})
	_save_json(base + ".json", meta)
	_save_json(base + ".unit.json", to_config())
	_save_sheet(base + "_sheet.png", hull_imgs, turret_imgs, meta)
	rvp.queue_free()
	hull_deg = keep[0]
	turret_deg = keep[1]
	turret_follows = keep[2]
	recoil_step = keep[3]
	apply_pose()
	busy = false
	progress.emit(total, total, "готово")
	return ""


func _save_json(path: String, data: Dictionary) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(JSON.stringify(data, "  "))


func _set_size(vp: SubViewport, cam: Camera3D, size: Vector2i) -> void:
	vp.size = size * SUPERSAMPLE
	cam.size = size.y / PX_PER_M


func _frame(vp: SubViewport, size: Vector2i, ground_y: float, cam: Camera3D) -> Image:
	for i in 4:
		await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	img.resize(size.x, size.y, Image.INTERPOLATE_LANCZOS)
	var shadow := await _shadow_pass(vp, ground_y, cam)
	return _under_shadow(img, shadow)


## The model's cast shadow on a white ground lit by the sun alone, as strength (L8).
func _shadow_pass(vp: SubViewport, ground_y: float, cam: Camera3D) -> Image:
	var saved := []
	for g in groups:
		for mi in g["meshes"]:
			var m := mi as MeshInstance3D
			saved.append([m, m.visible, m.cast_shadow])
			if m.visible:
				m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
				if not g["shadow"]:
					m.visible = false
	shadow_ground.position.y = ground_y
	shadow_ground.visible = true
	cam.cull_mask = 1 | LAYER_SHADOW
	fill.visible = false
	env.ambient_light_energy = 0.0
	env.ssao_enabled = false
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.adjustment_enabled = false
	for i in 4:
		await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	img.resize(vp.size.x / SUPERSAMPLE, vp.size.y / SUPERSAMPLE, Image.INTERPOLATE_LANCZOS)
	for sv in saved:
		sv[0].visible = sv[1]
		sv[0].cast_shadow = sv[2]
	shadow_ground.visible = false
	shadow_ground.position.y = 0.0
	cam.cull_mask = 1
	fill.visible = true
	env.ambient_light_energy = look["ambient"]
	env.ssao_enabled = true
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.adjustment_enabled = true
	img.convert(Image.FORMAT_RGBA8)
	var w := img.get_width()
	var h := img.get_height()
	var lit := 0.0
	for y in range(0, h, 4):
		for x in range(0, w, 4):
			lit = maxf(lit, img.get_pixel(x, y).get_luminance())
	var out := Image.create(w, h, false, Image.FORMAT_L8)
	for y in h:
		for x in w:
			var v := clampf(1.0 - img.get_pixel(x, y).get_luminance() / maxf(lit, 0.001), 0.0, 1.0)
			out.set_pixel(x, y, Color(v, v, v))
	return out


func _under_shadow(model_img: Image, shadow: Image) -> Image:
	model_img.convert(Image.FORMAT_RGBA8)
	var out := Image.create(model_img.get_width(), model_img.get_height(), false, Image.FORMAT_RGBA8)
	for y in out.get_height():
		for x in out.get_width():
			var sa := shadow.get_pixel(x, y).r * float(look["shadow_opacity"])
			var m := model_img.get_pixel(x, y)
			var a := m.a + sa * (1.0 - m.a)
			if a <= 0.0:
				continue
			var rgb := Color(m.r, m.g, m.b) * (m.a / a)
			out.set_pixel(x, y, Color(rgb.r, rgb.g, rgb.b, a))
	return out


## Every heading on grass, placed exactly as the game draws the sprites.
func _save_sheet(path: String, hull_imgs: Array[Image], turret_imgs: Array[Image], meta: Dictionary) -> void:
	var cell := Vector2i(340, 300)
	var cols := 6
	var rows := ceili(FRAMES / float(cols))
	var grass: Image = (load("res://assets/grass.jpg") as Texture2D).get_image()
	grass.convert(Image.FORMAT_RGBA8)
	grass = _mirrored(grass)
	var gs := PX_PER_M * GRASS_M * 2.0 / grass.get_width()
	grass.resize(roundi(grass.get_width() * gs), roundi(grass.get_height() * gs), Image.INTERPOLATE_BILINEAR)
	var sheet := Image.create(cell.x * cols, cell.y * rows, false, Image.FORMAT_RGBA8)
	for y in range(0, sheet.get_height(), grass.get_height()):
		for x in range(0, sheet.get_width(), grass.get_width()):
			sheet.blit_rect(grass, Rect2i(Vector2i.ZERO, grass.get_size()), Vector2i(x, y))
	var squash := sin(deg_to_rad(ELEVATION))
	var hull_px := hull_offset_m * PX_PER_M
	for i in FRAMES:
		var c := Vector2((i % cols) * cell.x + cell.x / 2.0, (i / cols) * cell.y + cell.y / 2.0)
		var a := deg_to_rad(360.0 * i / FRAMES)
		var hp := c + Vector2(cos(a), -sin(a) * squash) * hull_px
		if meta.get("layers", false):
			var ha: Array = meta["hull_anchor"]
			var ta: Array = meta["turret_anchor"]
			var off: Array = meta["turret_offsets"][i]
			var hi := hull_imgs[i]
			sheet.blend_rect(hi, Rect2i(Vector2i.ZERO, hi.get_size()), Vector2i(hp - Vector2(ha[0], ha[1])))
			var ti := turret_imgs[i]
			sheet.blend_rect(ti, Rect2i(Vector2i.ZERO, ti.get_size()),
				Vector2i(hp + Vector2(off[0], off[1]) - Vector2(ta[0], ta[1])))
		else:
			var an: Array = meta["anchor"]
			var img := hull_imgs[i]
			sheet.blend_rect(img, Rect2i(Vector2i.ZERO, img.get_size()), Vector2i(hp - Vector2(an[0], an[1])))
	sheet.save_png(path)


## 2 x 2 mirrored copy, so the grass tiles without seams.
static func _mirrored(img: Image) -> Image:
	var w := img.get_width()
	var h := img.get_height()
	var big := Image.create(w * 2, h * 2, false, img.get_format())
	var r := Rect2i(0, 0, w, h)
	big.blit_rect(img, r, Vector2i(0, 0))
	img.flip_x()
	big.blit_rect(img, r, Vector2i(w, 0))
	img.flip_y()
	big.blit_rect(img, r, Vector2i(w, h))
	img.flip_x()
	big.blit_rect(img, r, Vector2i(0, h))
	img.flip_y()
	return big
