extends RefCounted
## T-72B main battle tank (with Kontakt-1 ERA), roughly to scale in metres.
## Faces +X; the camera sees its right side (+Z), where the fender tanks,
## commander's cupola and IR searchlight are.

const Kit := preload("res://tools/models/kit.gd")

const HULL_W := 2.2  # lower hull between the tracks
const TRACK_Z := 1.42  # track centre line
const TRACK_W := 0.58
const WHEEL_R := 0.375
const WHEEL_Y := 0.42
const WHEEL_X := [2.3, 1.38, 0.46, -0.46, -1.38, -2.3]

var k := Kit.new()
var paint: Material
var paint_dark: Material
var steel: Material
var track: Material
var rubber: Material
var era: Material
var glass: Material
var wood: Material


func build(root: Node3D) -> void:
	var grime := Kit.grime_texture(72, 0.7, 1.05, 0.09)
	var grime_heavy := Kit.grime_texture(73, 0.55, 1.05, 0.12)
	paint = k.mat(Color(0.24, 0.28, 0.16), 0.85, 0.0, grime)
	paint_dark = k.mat(Color(0.17, 0.20, 0.12), 0.9, 0.0, grime)
	era = k.mat(Color(0.27, 0.30, 0.18), 0.8, 0.0, grime)
	steel = k.mat(Color(0.20, 0.20, 0.19), 0.55, 0.5, grime)
	track = k.mat(Color(0.24, 0.21, 0.18), 0.75, 0.45, grime_heavy)
	rubber = k.mat(Color(0.08, 0.08, 0.08), 0.95)
	glass = k.mat(Color(0.35, 0.45, 0.50), 0.15, 0.3)
	wood = k.mat(Color(0.42, 0.32, 0.20), 0.95, 0.0, grime_heavy)

	_hull(root)
	for side in [-1, 1]:
		_running_gear(root, side)
	_fenders(root)
	_rear(root)
	var turret := Node3D.new()
	turret.position = Vector3(0.25, 1.5, 0)
	root.add_child(turret)
	_turret(turret)


func _hull(root: Node3D) -> void:
	# Lower hull between the tracks.
	var lower := PackedVector2Array([
		Vector2(-3.35, 0.5), Vector2(2.95, 0.5), Vector2(3.45, 1.0),
		Vector2(1.7, 1.5), Vector2(-3.4, 1.5), Vector2(-3.45, 0.8)])
	k.extrude(root, lower, -HULL_W / 2, HULL_W / 2, paint)
	# Upper hull over the tracks (sponsons), same roof line.
	var upper := PackedVector2Array([
		Vector2(-3.4, 1.12), Vector2(3.2, 1.12), Vector2(3.4, 1.05),
		Vector2(3.45, 1.0), Vector2(1.7, 1.5), Vector2(-3.4, 1.5)])
	k.extrude(root, upper, -1.72, 1.72, paint)
	# Upper glacis: Kontakt-1 bricks in rows, V-shaped splash board.
	var slope_deg := -rad_to_deg(atan2(0.5, 1.75))
	for t in [0.22, 0.46, 0.7]:
		for col in 7:
			var p := Vector3(3.45 - 1.75 * t, 1.0 + 0.5 * t + 0.045, -1.38 + col * 0.46)
			k.box(root, Vector3(0.36, 0.07, 0.42), p, era, Vector3(0, 0, slope_deg))
	for s in [-1, 1]:
		k.box(root, Vector3(0.04, 0.1, 1.2), Vector3(2.0, 1.44, s * 0.5), paint_dark, Vector3(0, s * 40, 0))
	# Driver's hatch and periscope.
	k.cyl(root, 0.24, 0.06, Vector3(1.75, 1.52, 0), paint_dark)
	k.box(root, Vector3(0.12, 0.08, 0.22), Vector3(1.95, 1.52, 0), glass)
	# Headlights with guards on the front fenders.
	for s in [-1, 1]:
		var hp := Vector3(3.05, 1.3, s * 1.45)
		k.cyl(root, 0.09, 0.14, hp, paint_dark, Vector3(0, 0, 90))
		k.cyl(root, 0.07, 0.02, hp + Vector3(0.08, 0, 0), glass, Vector3(0, 0, 90))
		k.box(root, Vector3(0.28, 0.03, 0.03), hp + Vector3(0, 0.13, 0), steel)
	# Engine deck grilles.
	for i in 5:
		k.box(root, Vector3(0.12, 0.03, 1.6), Vector3(-1.4 - i * 0.28, 1.52, 0), paint_dark)


func _running_gear(root: Node3D, side: int) -> void:
	var z := side * TRACK_Z
	for x in WHEEL_X:
		_road_wheel(root, Vector3(x, WHEEL_Y, z), side)
	for x in [1.5, 0.0, -1.5]:
		k.cyl(root, 0.12, 0.2, Vector3(x, 0.98, z), steel, Vector3(90, 0, 0), -1.0, 16)
	# Idler (front) and drive sprocket (rear).
	var idler := Vector3(3.08, 0.56, z)
	k.cyl(root, 0.3, 0.5, idler, paint_dark, Vector3(90, 0, 0))
	k.cyl(root, 0.12, 0.54, idler, steel, Vector3(90, 0, 0), -1.0, 12)
	var sprocket := Vector3(-3.18, 0.6, z)
	k.cyl(root, 0.32, 0.5, sprocket, paint_dark, Vector3(90, 0, 0), -1.0, 14)
	for i in 12:
		var a := TAU * i / 12.0
		k.box(root, Vector3(0.08, 0.1, 0.5), sprocket + Vector3(cos(a), sin(a), 0) * 0.34, steel,
			Vector3(0, 0, rad_to_deg(a)))
	_track_loop(root, z, idler, sprocket)


func _road_wheel(root: Node3D, c: Vector3, side: int) -> void:
	k.cyl(root, WHEEL_R, 0.46, c, rubber, Vector3(90, 0, 0), -1.0, 28)
	var face := c + Vector3(0, 0, side * 0.235)
	k.cyl(root, WHEEL_R - 0.05, 0.03, face, paint, Vector3(90, 0, 0), -1.0, 28)
	# Pressed-steel wheel: raised ring, lightening holes, hub cap.
	k.cyl(root, 0.24, 0.035, face + Vector3(0, 0, side * 0.01), paint_dark, Vector3(90, 0, 0), -1.0, 24)
	for i in 8:
		var a := TAU * i / 8.0 + 0.2
		k.cyl(root, 0.045, 0.04, face + Vector3(cos(a) * 0.17, sin(a) * 0.17, side * 0.012), rubber,
			Vector3(90, 0, 0), -1.0, 10)
	k.cyl(root, 0.1, 0.1, face + Vector3(0, 0, side * 0.04), steel, Vector3(90, 0, 0), 0.07, 16)


## Individual track links wrapped around wheels, idler and sprocket.
func _track_loop(root: Node3D, z: float, idler: Vector3, sprocket: Vector3) -> void:
	var pts: Array[Vector2] = []
	var r_top := 1.12
	var ground := 0.06
	# Bottom run under the road wheels, rise to idler, top run over rollers, down to sprocket.
	pts.append(Vector2(sprocket.x + 0.25, ground + 0.12))
	pts.append(Vector2(WHEEL_X[5], ground))
	pts.append(Vector2(WHEEL_X[0], ground))
	for i in 9:
		var a := -PI / 2 + PI * i / 8.0
		pts.append(Vector2(idler.x, idler.y) + Vector2(cos(a), sin(a)) * 0.36)
	pts.append(Vector2(1.5, r_top))
	pts.append(Vector2(0.0, r_top))
	pts.append(Vector2(-1.5, r_top))
	for i in 9:
		var a := PI / 2 + PI * i / 8.0
		pts.append(Vector2(sprocket.x, sprocket.y) + Vector2(cos(a), sin(a)) * 0.38)
	pts.append(pts[0])
	var link := 0.17
	var carry := 0.0
	for i in pts.size() - 1:
		var a: Vector2 = pts[i]
		var b: Vector2 = pts[i + 1]
		var seg := a.distance_to(b)
		var dir := (b - a).normalized()
		var d := carry
		while d < seg:
			var p := a + dir * d
			var ang := rad_to_deg(atan2(dir.y, dir.x))
			k.box(root, Vector3(link - 0.025, 0.07, TRACK_W), Vector3(p.x, p.y, z), track, Vector3(0, 0, ang))
			k.box(root, Vector3(0.05, 0.05, TRACK_W * 0.8), Vector3(p.x, p.y, z) + Vector3(-dir.y, dir.x, 0) * -0.05,
				track, Vector3(0, 0, ang))  # grouser
			d += link
		carry = d - seg


func _fenders(root: Node3D) -> void:
	for s in [-1, 1]:
		k.box(root, Vector3(6.8, 0.04, 0.62), Vector3(-0.05, 1.13, s * 1.72), paint)
		# Rubber side skirt panels hanging from the fender edge.
		for i in 8:
			k.box(root, Vector3(0.78, 0.3, 0.03), Vector3(2.75 - i * 0.8, 0.97, s * 2.02), rubber)
		k.box(root, Vector3(0.6, 0.35, 0.04), Vector3(3.05, 1.0, s * 1.98), paint, Vector3(0, s * 12, 0))
	# Right fender: external fuel tanks and stowage boxes.
	var zr := 1.72
	for x in [1.9, 1.05]:
		k.box(root, Vector3(0.78, 0.32, 0.5), Vector3(x, 1.32, zr), paint)
		k.box(root, Vector3(0.8, 0.03, 0.52), Vector3(x, 1.49, zr), paint_dark)
	for x in [0.1, -0.75, -1.6]:
		k.cyl(root, 0.24, 0.8, Vector3(x, 1.39, zr), paint, Vector3(0, 0, 90), -1.0, 20)
		k.cyl(root, 0.05, 0.05, Vector3(x, 1.64, zr), steel)
	k.box(root, Vector3(1.1, 0.34, 0.5), Vector3(-2.6, 1.32, zr), paint)
	# Left fender: stowage boxes.
	for x in [1.6, 0.4, -0.9, -2.2]:
		k.box(root, Vector3(1.0, 0.3, 0.5), Vector3(x, 1.3, -zr), paint)


func _rear(root: Node3D) -> void:
	# Two 200-litre drums and the unditching log across the back.
	for s in [-1, 1]:
		var drum := Vector3(-3.72, 1.55, s * 0.5)
		k.cyl(root, 0.3, 0.9, drum, paint, Vector3(90, 0, 0), -1.0, 24)
		for dz in [-0.28, 0.0, 0.28]:
			k.cyl(root, 0.31, 0.03, drum + Vector3(0, 0, dz), paint_dark, Vector3(90, 0, 0), -1.0, 24)
		k.box(root, Vector3(0.35, 0.05, 0.05), drum + Vector3(0.2, -0.28, s * 0.4), steel)
	k.cyl(root, 0.14, 3.3, Vector3(-3.6, 1.95, 0), wood, Vector3(90, 0, 0), -1.0, 12)
	k.box(root, Vector3(0.05, 0.6, 3.2), Vector3(-3.45, 1.15, 0), paint_dark)


func _turret(t: Node3D) -> void:
	# Cast dome: wide, low, bulged at the front, tapering to the rear.
	var rings := []
	var seg := 48
	var steps := 12
	for i in steps + 1:
		var u := float(i) / steps  # 0 = base, 1 = roof
		var ring := PackedVector3Array()
		var scale_r := pow(1.0 - pow(u, 2.6), 0.5) * (1.0 - 0.1 * u)
		var y := u * 0.82
		if i == steps:
			scale_r = 0.0
			y = 0.82
		for j in seg:
			var phi := TAU * j / seg
			var fwd := cos(phi)
			var r := 1.08 + 0.3 * maxf(fwd, 0.0) - 0.2 * maxf(-fwd, 0.0)
			ring.append(Vector3(cos(phi) * r * scale_r, y, sin(phi) * r * 0.98 * scale_r))
		rings.append(ring)
	rings.reverse()
	k.loft(t, rings, paint)
	k.cyl(t, 1.2, 0.08, Vector3(0, 0.02, 0), paint_dark, Vector3.ZERO, -1.0, 48)  # turret ring

	# Kontakt-1 ERA: two rows of bricks around the front arc (not over the gun).
	for row in 2:
		for i in 7:
			var deg := -64.0 + i * 11.0
			for s in [-1, 1]:
				var phi := deg_to_rad(s * absf(deg))
				if absf(deg) < 14.0:
					continue
				var rr := 1.36 - row * 0.18
				var p := Vector3(cos(phi) * rr, 0.24 + row * 0.2, sin(phi) * rr)
				k.box(t, Vector3(0.1, 0.18, 0.26), p, era, Vector3(0, -rad_to_deg(phi), -18 - row * 20))
	# Roof ERA row.
	for s in [-1, 1]:
		for i in 3:
			k.box(t, Vector3(0.26, 0.06, 0.2), Vector3(0.75 - i * 0.05, 0.56, s * (0.3 + i * 0.22)), era,
				Vector3(0, 0, -14))

	# Mantlet and 125 mm 2A46 gun with thermal sleeve and fume extractor.
	k.box(t, Vector3(0.4, 0.36, 0.55), Vector3(1.28, 0.32, 0), paint_dark)
	var gy := 0.33
	k.cyl(t, 0.1, 0.5, Vector3(1.6, gy, 0), paint_dark, Vector3(0, 0, -90), 0.09)
	var x := 1.85
	for seg_i in 4:
		var seg_len := 1.05
		var r := 0.085 - seg_i * 0.006
		k.cyl(t, r, seg_len, Vector3(x + seg_len / 2, gy, 0), paint, Vector3(0, 0, -90), r, 20)
		k.cyl(t, r + 0.012, 0.05, Vector3(x + seg_len, gy, 0), paint_dark, Vector3(0, 0, -90), -1.0, 20)
		x += seg_len
		if seg_i == 1:
			k.cyl(t, 0.13, 0.62, Vector3(x + 0.31, gy, 0), paint, Vector3(0, 0, -90), 0.12, 24)
			x += 0.62
	k.cyl(t, 0.07, 0.12, Vector3(x + 0.06, gy, 0), steel, Vector3(0, 0, -90), -1.0, 16)

	# IR searchlight to the right of the gun.
	var sl := Vector3(1.05, 0.62, 0.52)
	k.box(t, Vector3(0.12, 0.3, 0.05), sl + Vector3(0, -0.12, 0), steel)
	k.cyl(t, 0.17, 0.28, sl + Vector3(0.05, 0.06, 0), paint_dark, Vector3(0, 0, -90), -1.0, 20)
	k.cyl(t, 0.14, 0.02, sl + Vector3(0.2, 0.06, 0), glass, Vector3(0, 0, -90), -1.0, 20)

	# Commander's cupola (right) with NSVT 12.7 mm machine gun; gunner's hatch (left).
	var cup := Vector3(-0.2, 0.58, 0.42)
	k.cyl(t, 0.38, 0.14, cup, paint_dark, Vector3.ZERO, 0.34, 28)
	k.cyl(t, 0.3, 0.06, cup + Vector3(0, 0.09, 0), paint, Vector3.ZERO, -1.0, 24)
	for i in 4:
		var a := deg_to_rad(20 + i * 30)
		k.box(t, Vector3(0.1, 0.06, 0.06), cup + Vector3(cos(a) * 0.37, 0.03, -sin(a) * 0.37), glass,
			Vector3(0, rad_to_deg(a), 0))
	var mg := cup + Vector3(0.15, 0.3, -0.05)
	k.box(t, Vector3(0.05, 0.22, 0.05), mg + Vector3(0, -0.12, 0), steel)
	k.box(t, Vector3(0.5, 0.1, 0.1), mg, steel)
	k.cyl(t, 0.025, 0.9, mg + Vector3(0.65, 0.01, 0), steel, Vector3(0, 0, -90), -1.0, 10)
	k.box(t, Vector3(0.14, 0.14, 0.1), mg + Vector3(-0.05, -0.02, -0.12), paint_dark)  # ammo box
	var gh := Vector3(0.0, 0.58, -0.45)
	k.cyl(t, 0.3, 0.08, gh, paint_dark, Vector3.ZERO, 0.28, 24)
	k.box(t, Vector3(0.18, 0.12, 0.14), gh + Vector3(0.35, 0.02, 0), paint_dark)  # gunner's sight

	# Smoke grenade launchers (902A) on both front cheeks.
	for s in [-1, 1]:
		for i in 4:
			var phi := deg_to_rad(s * (58 + i * 8))
			var p := Vector3(cos(phi) * 1.15, 0.42, sin(phi) * 1.15)
			k.cyl(t, 0.045, 0.3, p, paint_dark, Vector3(0, -rad_to_deg(phi), -60), -1.0, 10)

	# Snorkel tube (left rear), stowage bin, antenna.
	k.cyl(t, 0.09, 1.6, Vector3(-0.75, 0.35, -0.95), paint, Vector3(0, 30, 90), -1.0, 14)
	k.box(t, Vector3(0.5, 0.35, 1.4), Vector3(-1.15, 0.28, 0.0), paint, Vector3(0, 0, 8))
	k.box(t, Vector3(0.52, 0.03, 1.42), Vector3(-1.13, 0.46, 0.0), paint_dark, Vector3(0, 0, 8))
	k.cyl(t, 0.04, 0.12, Vector3(-0.85, 0.66, -0.45), steel)
	k.cyl(t, 0.008, 2.2, Vector3(-0.95, 1.75, -0.45), steel, Vector3(0, 0, 8), 0.004, 6)
