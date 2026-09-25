class_name Hex
extends RefCounted
## Hex-grid math. Axial coordinates (q, r) stored in Vector2i, pointy-top hexes.

const SIZE := 48.0
const DIRS: Array[Vector2i] = [
	Vector2i(1, 0), Vector2i(1, -1), Vector2i(0, -1),
	Vector2i(-1, 0), Vector2i(-1, 1), Vector2i(0, 1),
]


static func to_pixel(h: Vector2i) -> Vector2:
	return Vector2(SIZE * sqrt(3.0) * (h.x + h.y / 2.0), SIZE * 1.5 * h.y)


static func from_pixel(p: Vector2) -> Vector2i:
	var q := (sqrt(3.0) / 3.0 * p.x - p.y / 3.0) / SIZE
	var r := (2.0 / 3.0 * p.y) / SIZE
	return axial_round(q, r)


static func axial_round(q: float, r: float) -> Vector2i:
	var s := -q - r
	var rq := roundf(q)
	var rr := roundf(r)
	var rs := roundf(s)
	var dq := absf(rq - q)
	var dr := absf(rr - r)
	var ds := absf(rs - s)
	if dq > dr and dq > ds:
		rq = -rr - rs
	elif dr > ds:
		rr = -rq - rs
	return Vector2i(int(rq), int(rr))


static func distance(a: Vector2i, b: Vector2i) -> int:
	var d := a - b
	return (absi(d.x) + absi(d.y) + absi(d.x + d.y)) >> 1


static func neighbors(h: Vector2i) -> Array[Vector2i]:
	var res: Array[Vector2i] = []
	for d in DIRS:
		res.append(h + d)
	return res


static func line(a: Vector2i, b: Vector2i) -> Array[Vector2i]:
	var n := distance(a, b)
	var res: Array[Vector2i] = []
	for i in n + 1:
		var t := 0.0 if n == 0 else float(i) / n
		res.append(axial_round(lerpf(a.x, b.x, t) + 1e-6, lerpf(a.y, b.y, t) + 1e-6))
	return res


## "odd-r" offset layout (rectangular map) -> axial.
static func offset_to_axial(col: int, row: int) -> Vector2i:
	return Vector2i(col - ((row - (row & 1)) >> 1), row)


static func axial_to_offset(h: Vector2i) -> Vector2i:
	return Vector2i(h.x + ((h.y - (h.y & 1)) >> 1), h.y)


static func corners(center: Vector2, size: float = SIZE) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in 6:
		var a := deg_to_rad(60.0 * i - 30.0)
		pts.append(center + Vector2(cos(a), sin(a)) * size)
	return pts
