extends RefCounted
## T-72A main battle tank, roughly to scale in metres, modelled after reference
## renders: riveted side skirts over the upper road wheels, down-curved front
## mudguards, smooth cast turret with smoke dischargers, grilled engine deck.
## Faces +X; the camera sees its right side (+Z).

const Kit := preload("res://tools/models/kit.gd")

const HULL_W := 2.2  # lower hull between the tracks
const SIDE_Z := 1.74  # outer edge of fenders / side skirts
const TRACK_Z := 1.42  # track centre line
const TRACK_W := 0.58
const WHEEL_R := 0.375
const WHEEL_Y := 0.42
const WHEEL_X := [2.3, 1.38, 0.46, -0.46, -1.38, -2.3]
const ROOF_Y := 1.47

var k := Kit.new()
var paint: Material
var paint_dark: Material
var steel: Material
var track: Material
var rubber: Material
var glass: Material
var canvas: Material


func build(root: Node3D) -> void:
	var grime := Kit.grime_texture(72, 0.82, 1.04, 0.1)
	var grime_heavy := Kit.grime_texture(73, 0.55, 1.0, 0.14)
	paint = k.mat(Color(0.27, 0.33, 0.21), 0.55, 0.05, grime)
	paint_dark = k.mat(Color(0.19, 0.24, 0.15), 0.65, 0.05, grime)
	canvas = k.mat(Color(0.25, 0.29, 0.19), 0.95, 0.0, grime_heavy)
	steel = k.mat(Color(0.12, 0.12, 0.12), 0.45, 0.6, grime)
	track = k.mat(Color(0.20, 0.18, 0.16), 0.8, 0.4, grime_heavy)
	rubber = k.mat(Color(0.07, 0.07, 0.07), 0.95)
	glass = k.mat(Color(0.75, 0.78, 0.72), 0.1, 0.4)

	_hull(root)
	for side in [-1, 1]:
		_running_gear(root, side)
		_side_skirt(root, side)
		_front_mudguard(root, side)
	_engine_deck(root)
	var turret := Node3D.new()
	turret.position = Vector3(0.1, ROOF_Y, 0)
	turret.scale = Vector3(1.18, 1.12, 1.18)
	root.add_child(turret)
	_turret(turret)


func _hull(root: Node3D) -> void:
	var lower := PackedVector2Array([
		Vector2(-3.35, 0.48), Vector2(2.95, 0.48), Vector2(3.38, 0.98),
		Vector2(1.72, ROOF_Y), Vector2(-3.42, ROOF_Y), Vector2(-3.47, 0.78)])
	k.extrude(root, lower, -HULL_W / 2, HULL_W / 2, paint)
	# Sponsons over the tracks share the roof line.
	var upper := PackedVector2Array([
		Vector2(-3.42, 1.12), Vector2(2.9, 1.12), Vector2(1.72, ROOF_Y), Vector2(-3.42, ROOF_Y)])
	k.extrude(root, upper, -SIDE_Z, SIDE_Z, paint)
	# Fender tops with flat stowage lids.
	for s in [-1, 1]:
		for x in [1.25, 0.1, -1.1, -2.35]:
			k.box(root, Vector3(0.95, 0.05, 0.5), Vector3(x, ROOF_Y + 0.025, s * 1.43), paint)
			k.box(root, Vector3(0.9, 0.012, 0.03), Vector3(x, ROOF_Y + 0.05, s * 1.43), paint_dark)
	# Glacis: transverse ribs, headlights with round guards.
	var slope := rad_to_deg(atan2(ROOF_Y - 0.98, 3.38 - 1.72))
	for s in [-1, 1]:
		var hp := Vector3(2.8, 1.25, s * 1.25)
		k.cyl(root, 0.08, 0.14, hp, paint_dark, Vector3(0, 0, -90), -1.0, 16)
		k.cyl(root, 0.065, 0.02, hp + Vector3(0.08, 0, 0), glass, Vector3(0, 0, -90), -1.0, 16)
		k.cyl(root, 0.14, 0.03, hp + Vector3(0.02, 0, 0), steel, Vector3(90, 0, 0), -1.0, 20)
	for i in 4:
		var x := 3.1 - i * 0.35
		k.box(root, Vector3(0.03, 0.03, 1.9), Vector3(x, 0.98 + (3.38 - x) * 0.295 + 0.02, 0), paint_dark,
			Vector3(0, 0, -slope))
	k.cyl(root, 0.22, 0.05, Vector3(1.55, ROOF_Y + 0.02, 0), paint_dark, Vector3.ZERO, -1.0, 20)  # driver hatch
	k.box(root, Vector3(0.1, 0.07, 0.22), Vector3(1.8, ROOF_Y + 0.03, 0), glass)


func _front_mudguard(root: Node3D, side: int) -> void:
	# The fender runs past the glacis and curves down over the idler.
	var c := Vector2(2.85, 0.72)
	var r := 0.42
	var steps := 7
	for i in steps:
		var a0 := deg_to_rad(90.0 - i * 100.0 / steps)
		var a1 := deg_to_rad(90.0 - (i + 1) * 100.0 / steps)
		var p0 := c + Vector2(cos(a0), sin(a0)) * r
		var p1 := c + Vector2(cos(a1), sin(a1)) * r
		var mid := (p0 + p1) / 2
		var ang := rad_to_deg(atan2(p1.y - p0.y, p1.x - p0.x))
		k.box(root, Vector3(p0.distance_to(p1) + 0.02, 0.05, 0.62), Vector3(mid.x, mid.y, side * 1.43), paint,
			Vector3(0, 0, ang))
		k.box(root, Vector3(p0.distance_to(p1) + 0.02, 0.12, 0.04), Vector3(mid.x, mid.y - 0.04, side * SIDE_Z),
			paint, Vector3(0, 0, ang))


func _side_skirt(root: Node3D, side: int) -> void:
	# Two rows of riveted panels covering the upper half of the road wheels.
	var z := side * (SIDE_Z + 0.02)
	var x0 := -3.3
	var x1 := 2.75
	var panels := 7
	var w := (x1 - x0) / panels
	for row in 2:
		var y := 0.97 - row * 0.3
		for i in panels:
			var x := x0 + w * (i + 0.5)
			k.box(root, Vector3(w - 0.02, 0.28, 0.035), Vector3(x, y, z), paint)
			for rx in [-0.42, 0.0, 0.42]:
				for ry in [-0.1, 0.1]:
					k.cyl(root, 0.015, 0.02, Vector3(x + rx * w, y + ry, z + side * 0.02), paint_dark,
						Vector3(90, 0, 0), -1.0, 6)
	k.box(root, Vector3(x1 - x0, 0.04, 0.05), Vector3((x0 + x1) / 2, 1.12, z), paint_dark)  # top rail


func _running_gear(root: Node3D, side: int) -> void:
	var z := side * TRACK_Z
	for x in WHEEL_X:
		_road_wheel(root, Vector3(x, WHEEL_Y, z), side)
	var idler := Vector3(3.05, 0.55, z)
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
	# Six spoke recesses and a hub, as on the pressed-steel T-72 wheel.
	for i in 6:
		var a := TAU * i / 6.0
		k.box(root, Vector3(0.13, 0.07, 0.03), face + Vector3(cos(a), sin(a), 0) * 0.19 + Vector3(0, 0, side * 0.006),
			paint_dark, Vector3(0, 0, rad_to_deg(a)))
	k.cyl(root, 0.1, 0.1, face + Vector3(0, 0, side * 0.04), paint_dark, Vector3(90, 0, 0), 0.08, 16)


## Individual track links wrapped around wheels, idler and sprocket.
func _track_loop(root: Node3D, z: float, idler: Vector3, sprocket: Vector3) -> void:
	var pts: Array[Vector2] = []
	var ground := 0.06
	pts.append(Vector2(sprocket.x + 0.25, ground + 0.12))
	pts.append(Vector2(WHEEL_X[5], ground))
	pts.append(Vector2(WHEEL_X[0], ground))
	for i in 9:
		var a := -PI / 2 + PI * i / 8.0
		pts.append(Vector2(idler.x, idler.y) + Vector2(cos(a), sin(a)) * 0.36)
	pts.append(Vector2(0.0, 1.0))
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
			k.box(root, Vector3(0.05, 0.05, TRACK_W * 0.8), Vector3(p.x, p.y, z) + Vector3(dir.y, -dir.x, 0) * 0.05,
				track, Vector3(0, 0, ang))  # grouser
			d += link
		carry = d - seg


func _engine_deck(root: Node3D) -> void:
	# Two big mesh grilles over the engine and transmission.
	for cx in [-1.75, -2.8]:
		var gw := 0.95
		k.box(root, Vector3(gw + 0.08, 0.04, 1.9), Vector3(cx, ROOF_Y + 0.02, 0), paint_dark)
		for i in 9:
			k.box(root, Vector3(0.02, 0.04, 1.8), Vector3(cx - gw / 2 + gw * (i + 0.5) / 9, ROOF_Y + 0.04, 0), paint)
		for j in 14:
			k.box(root, Vector3(gw, 0.035, 0.02), Vector3(cx, ROOF_Y + 0.045, -0.9 + 1.8 * (j + 0.5) / 14), paint)
	# Louvred panel between the turret and the grilles.
	k.box(root, Vector3(0.7, 0.05, 1.7), Vector3(-0.95, ROOF_Y + 0.025, 0), paint)
	for i in 8:
		k.box(root, Vector3(0.6, 0.02, 0.05), Vector3(-0.95, ROOF_Y + 0.055, -0.7 + i * 0.2), paint_dark)
	# Rear: cross pipe, four curved drum brackets, mud flaps.
	k.cyl(root, 0.1, 3.0, Vector3(-3.55, 1.22, 0), paint, Vector3(90, 0, 0), -1.0, 16)
	for i in 4:
		var z := -1.05 + i * 0.7
		for j in 5:
			var a := deg_to_rad(200.0 + j * 30.0)
			var p := Vector3(-3.72 + cos(a) * 0.3, 1.62 + sin(a) * 0.3, z)
			k.box(root, Vector3(0.13, 0.05, 0.06), p, paint, Vector3(0, 0, rad_to_deg(a) + 90))
	for s in [-1, 1]:
		k.box(root, Vector3(0.04, 0.4, 0.55), Vector3(-3.55, 0.95, s * 1.45), paint_dark, Vector3(0, 0, -25))


func _turret(t: Node3D) -> void:
	# Smooth cast dome: wide and low, bulged at the front, tapering to the rear.
	var rings := []
	var seg := 56
	var steps := 16
	var height := 0.8
	for i in steps + 1:
		var u := float(i) / steps
		var ring := PackedVector3Array()
		var f := sqrt(maxf(0.0, 1.0 - pow(u, 2.3)))
		if i == steps:
			f = 0.0
		for j in seg:
			var phi := TAU * j / seg
			var fwd := cos(phi)
			var r := 1.12 + 0.2 * maxf(fwd, 0.0) - 0.18 * maxf(-fwd, 0.0)
			ring.append(Vector3(cos(phi) * r * f, u * height, sin(phi) * 1.12 * f))
		rings.append(ring)
	rings.reverse()
	k.loft(t, rings, paint)
	k.cyl(t, 1.16, 0.08, Vector3(0, 0.02, 0), paint_dark, Vector3.ZERO, 1.1, 48)  # turret ring

	# Gun mantlet with canvas cover.
	k.box(t, Vector3(0.55, 0.42, 0.5), Vector3(1.28, 0.36, 0), canvas, Vector3(0, 0, -6))
	k.cyl(t, 0.16, 0.25, Vector3(1.6, 0.36, 0), canvas, Vector3(0, 0, -90), 0.13, 16)
	# 125 mm 2A46: thermal sleeve bands, fume extractor at one third.
	var gy := 0.36
	var x := 1.72
	for seg_i in 5:
		var seg_len := 0.95
		var r := 0.085 - seg_i * 0.004
		k.cyl(t, r, seg_len, Vector3(x + seg_len / 2, gy, 0), paint, Vector3(0, 0, -90), r, 20)
		k.cyl(t, r + 0.01, 0.05, Vector3(x + seg_len, gy, 0), paint_dark, Vector3(0, 0, -90), -1.0, 20)
		x += seg_len
		if seg_i == 1:
			k.cyl(t, 0.12, 0.55, Vector3(x + 0.275, gy, 0), paint, Vector3(0, 0, -90), 0.12, 24)
			x += 0.55
	k.cyl(t, 0.09, 0.14, Vector3(x + 0.07, gy, 0), paint_dark, Vector3(0, 0, -90), -1.0, 20)

	# IR searchlight on the right of the mantlet.
	var sl := Vector3(1.0, 0.66, 0.45)
	k.cyl(t, 0.13, 0.22, sl, paint_dark, Vector3(0, 0, -90), -1.0, 18)
	k.cyl(t, 0.11, 0.02, sl + Vector3(0.12, 0, 0), glass, Vector3(0, 0, -90), -1.0, 18)

	# Smoke dischargers: rows of short tubes around both front cheeks.
	for s in [-1, 1]:
		for i in 8:
			var phi := deg_to_rad(s * (32.0 + i * 7.5))
			var rr := 1.22 - i * 0.012
			var p := Vector3(cos(phi) * rr, 0.36 + (i % 2) * 0.1, sin(phi) * rr)
			k.cyl(t, 0.04, 0.24, p, paint_dark, Vector3(0, -rad_to_deg(phi), -65), -1.0, 10)

	# Commander's cupola (right) with NSVT 12.7 mm MG; gunner's hatch and sight (left).
	var cup := Vector3(-0.15, 0.7, 0.42)
	k.cyl(t, 0.36, 0.12, cup, paint, Vector3.ZERO, 0.33, 28)
	k.cyl(t, 0.28, 0.05, cup + Vector3(0, 0.08, 0), paint_dark, Vector3.ZERO, -1.0, 24)
	k.cyl(t, 0.07, 0.1, cup + Vector3(0.1, 0.15, 0.18), paint_dark, Vector3(0, 0, -90), -1.0, 12)  # cupola light
	var mg := cup + Vector3(0.1, 0.3, -0.12)
	k.box(t, Vector3(0.05, 0.22, 0.05), mg + Vector3(0, -0.12, 0), steel)
	k.box(t, Vector3(0.45, 0.09, 0.09), mg, steel)
	k.cyl(t, 0.022, 0.85, mg + Vector3(0.62, 0.01, 0), steel, Vector3(0, 0, -90), -1.0, 10)
	k.box(t, Vector3(0.14, 0.14, 0.1), mg + Vector3(-0.02, -0.02, -0.12), paint_dark)
	var gh := Vector3(0.05, 0.72, -0.42)
	k.cyl(t, 0.28, 0.06, gh, paint, Vector3.ZERO, 0.27, 24)
	k.box(t, Vector3(0.3, 0.16, 0.16), gh + Vector3(0.42, 0.02, 0.05), paint)  # gunner's sight box
	k.box(t, Vector3(0.04, 0.1, 0.12), gh + Vector3(0.58, 0.05, 0.05), glass)
	k.cyl(t, 0.03, 0.2, Vector3(-0.55, 0.78, 0.0), paint_dark)  # antenna base
	k.cyl(t, 0.008, 0.9, Vector3(-0.55, 1.3, 0.0), steel, Vector3.ZERO, 0.004, 6)

	# Rear: angled stowage box and snorkel tube.
	k.box(t, Vector3(0.45, 0.32, 1.3), Vector3(-1.05, 0.28, 0.2), paint, Vector3(0, 0, 10))
	for i in 5:
		k.box(t, Vector3(0.46, 0.015, 1.31), Vector3(-1.05, 0.16 + i * 0.05, 0.2), paint_dark, Vector3(0, 0, 10))
	k.cyl(t, 0.1, 1.4, Vector3(-1.05, 0.12, -0.45), paint, Vector3(90, 0, 0), -1.0, 16)
