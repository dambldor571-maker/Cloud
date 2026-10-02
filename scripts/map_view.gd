class_name MapView
extends Node2D
## Draws the map as continuous painted terrain (the hex grid is only a faint
## dashed overlay) plus territory borders in the owners' colours.
## Gameplay still runs on hexes; this node is purely visual.

const GROUND_SCALE := 4.0  # world pixels per ground-texture pixel
const WARP := 14.0  # how far terrain edges wander from the hex edges
const GROUND_COLORS := {
	Rules.Terrain.PLAIN: Color(0.52, 0.58, 0.33),
	Rules.Terrain.FOREST: Color(0.36, 0.46, 0.24),
	Rules.Terrain.HILLS: Color(0.60, 0.55, 0.36),
	Rules.Terrain.CITY: Color(0.55, 0.54, 0.40),
	Rules.Terrain.WATER: Color(0.23, 0.40, 0.52),
	Rules.Terrain.MOUNTAIN: Color(0.45, 0.42, 0.36),
}
const EDGE := 0.866  # hex centre to edge midpoint, in hex radii
const BLEND := 0.45  # half-width of the transition band around hex edges, in hex radii
const BLEND_DEPTH := 0.15  # height blend softness: smaller = sharper, more ragged edges
## Surface relief per terrain: [noise type, frequency, max height, shading strength].
## A higher max height lets the terrain push further into its neighbours.
const DETAIL := {
	Rules.Terrain.PLAIN: [FastNoiseLite.TYPE_SIMPLEX, 0.03, 0.45, 0.10],
	Rules.Terrain.FOREST: [FastNoiseLite.TYPE_CELLULAR, 0.04, 0.8, 0.18],
	Rules.Terrain.HILLS: [FastNoiseLite.TYPE_SIMPLEX_SMOOTH, 0.025, 0.6, 0.15],
	Rules.Terrain.CITY: [FastNoiseLite.TYPE_SIMPLEX, 0.05, 0.3, 0.06],
	Rules.Terrain.WATER: [FastNoiseLite.TYPE_SIMPLEX_SMOOTH, 0.02, 0.2, 0.08],
	Rules.Terrain.MOUNTAIN: [FastNoiseLite.TYPE_SIMPLEX, 0.03, 0.8, 0.18],
}
const GRID_COLOR := Color(1, 1, 1, 0.13)
const NEUTRAL_BORDER := Color(0.85, 0.85, 0.85, 0.5)

var game: Node
var territory: Dictionary = {}  # Vector2i -> side (-1 neutral), nearest city's owner
var _ground: ImageTexture
var _ground_rect := Rect2()
var _decor: Array[Dictionary] = []  # {kind, pos, s}, sorted top to bottom
## Pre-rendered map (tools/references/bake_map.gd): [{tex, rect}] in world pixels.
var _baked: Array[Dictionary] = []


func _init(p_game: Node) -> void:
	game = p_game
	show_behind_parent = true
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS  # baked map is zoomed far out


## Call after the map is generated. The ground texture is skipped in headless autotests.
func rebuild(seed_value: int, with_ground: bool) -> void:
	_baked.clear()
	_ground = _build_ground(seed_value) if with_ground else null
	_build_decor(seed_value)
	update_territory()


## Use a pre-rendered map instead of the painted ground and decor.
func set_baked(tiles: Array[Dictionary]) -> void:
	_baked = tiles
	_ground = null
	_decor.clear()
	update_territory()


func update_territory() -> void:
	territory.clear()
	for h in game.terrain:
		var best_d := 1 << 20
		var best_c := Vector2i.ZERO
		for c in game.city_owner:
			var d := Hex.distance(h, c)
			if d < best_d or (d == best_d and (c.x < best_c.x or (c.x == best_c.x and c.y < best_c.y))):
				best_d = d
				best_c = c
		territory[h] = game.city_owner.get(best_c, -1)
	queue_redraw()


func _build_ground(seed_value: int) -> ImageTexture:
	var r: Rect2 = game._map_rect()
	var w := int(ceil(r.size.x / GROUND_SCALE))
	var hgt := int(ceil(r.size.y / GROUND_SCALE))
	var img := Image.create(w, hgt, false, Image.FORMAT_RGBA8)
	var warp := FastNoiseLite.new()
	warp.seed = seed_value + 11
	warp.frequency = 0.012
	var tint := FastNoiseLite.new()
	tint.seed = seed_value + 23
	tint.frequency = 0.02
	tint.fractal_octaves = 3
	var detail := _detail_noises(seed_value)
	for y in hgt:
		for x in w:
			var p := r.position + Vector2(x + 0.5, y + 0.5) * GROUND_SCALE
			var wp := p + Vector2(warp.get_noise_2d(p.x, p.y), warp.get_noise_2d(p.y + 913.0, p.x - 377.0)) * WARP
			if not game.terrain.has(Hex.from_pixel(wp)):
				continue
			var c := _blend_ground(p, _terrain_weights(wp), detail)
			var n := tint.get_noise_2d(p.x, p.y) * 0.22
			c = c.lightened(n) if n > 0.0 else c.darkened(-n)
			img.set_pixel(x, y, c)
	_ground_rect = Rect2(r.position, Vector2(w, hgt) * GROUND_SCALE)
	return ImageTexture.create_from_image(img)


## Share of each terrain at a (warped) point: the hex it is in and its six
## neighbours, by distance to their centres. Only a band of BLEND around the
## hex edges is mixed; hex centres keep their own terrain.
func _terrain_weights(wp: Vector2) -> Dictionary:  # Rules.Terrain -> weight, sums to 1
	var h0 := Hex.from_pixel(wp)
	var w := {}
	var total := 0.0
	for h in [h0] + Hex.neighbors(h0):
		if not game.terrain.has(h):
			continue
		var d := wp.distance_to(Hex.to_pixel(h)) / Hex.SIZE  # 0 centre, 0.87 edge, 1 corner
		var k := clampf(1.0 - (d - (EDGE - BLEND)) / (2.0 * BLEND), 0.0, 1.0)
		if k == 0.0:
			continue
		k = k * k * (3.0 - 2.0 * k)
		var t: int = game.terrain[h]
		w[t] = w.get(t, 0.0) + k
		total += k
	for t in w:
		w[t] /= total
	return w


## Per-terrain "relief" of the surface texture (tree clumps, rocks, ripples),
## 0..1. Where terrains meet, the one standing higher wins (height blend), so
## edges get ragged like a forest edge or a shoreline instead of a soft fade.
func _detail_noises(seed_value: int) -> Dictionary:
	var res := {}
	for t in DETAIL:
		var cfg: Array = DETAIL[t]
		var n := FastNoiseLite.new()
		n.seed = seed_value + 101 + int(t) * 17
		n.noise_type = cfg[0]
		n.frequency = cfg[1]
		n.fractal_octaves = 3
		if cfg[0] == FastNoiseLite.TYPE_CELLULAR:
			n.cellular_return_type = FastNoiseLite.RETURN_DISTANCE
			n.fractal_type = FastNoiseLite.FRACTAL_NONE
		res[t] = n
	return res


func _blend_ground(p: Vector2, weights: Dictionary, detail: Dictionary) -> Color:
	var heights := {}
	var top := -INF
	for t in weights:
		var cfg: Array = DETAIL[t]
		var n: FastNoiseLite = detail[t]
		var v := n.get_noise_2d(p.x, p.y)
		if cfg[0] == FastNoiseLite.TYPE_CELLULAR:
			v = -v  # distance noise is -1 at cell centres, ~0 at borders: round clumps (tree crowns)
		else:
			v = 0.5 + 0.5 * v
		var hh := clampf(v, 0.0, 1.0) * float(cfg[2])
		heights[t] = hh
		top = maxf(top, hh + weights[t])
	var c := Color(0, 0, 0)
	var bsum := 0.0
	for t in weights:
		var b: float = maxf(heights[t] + weights[t] - (top - BLEND_DEPTH), 0.0)
		if b == 0.0:
			continue
		var base: Color = GROUND_COLORS[t]
		# The relief also shades the terrain's own colour, so the texture reads.
		var s: float = (heights[t] / maxf(float(DETAIL[t][2]), 0.001) - 0.5) * float(DETAIL[t][3])
		base = base.lightened(s) if s > 0.0 else base.darkened(-s)
		c += base * b
		bsum += b
	return c / bsum


func _build_decor(seed_value: int) -> void:
	_decor.clear()
	var rng := RandomNumberGenerator.new()
	for h in game.terrain:
		rng.seed = hash(Vector3i(h.x, h.y, seed_value))
		var c := Hex.to_pixel(h)
		var t: Rules.Terrain = game.terrain[h]
		match t:
			Rules.Terrain.FOREST:
				for i in 9:
					_decor.append({"kind": "tree", "pos": c + _rand_in_hex(rng, 0.8), "s": rng.randf_range(0.8, 1.2)})
			Rules.Terrain.HILLS:
				for i in 3:
					_decor.append({"kind": "hill", "pos": c + _rand_in_hex(rng, 0.55), "s": rng.randf_range(0.8, 1.2)})
			Rules.Terrain.PLAIN:
				for i in 3:
					_decor.append({"kind": "grass", "pos": c + _rand_in_hex(rng, 0.85), "s": rng.randf_range(0.7, 1.1)})
				if rng.randf() < 0.25:
					_decor.append({"kind": "tree", "pos": c + _rand_in_hex(rng, 0.7), "s": 0.8})
			Rules.Terrain.WATER:
				for i in 2:
					_decor.append({"kind": "wave", "pos": c + _rand_in_hex(rng, 0.5), "s": 1.0})
			Rules.Terrain.CITY:
				_decor.append({"kind": "city", "pos": c, "hex": h, "s": 1.0})
	_decor.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a["pos"].y < b["pos"].y)


func _rand_in_hex(rng: RandomNumberGenerator, spread: float) -> Vector2:
	var a := rng.randf() * TAU
	var d := sqrt(rng.randf()) * Hex.SIZE * spread * 0.85
	return Vector2(cos(a), sin(a)) * d


func _draw() -> void:
	if not _baked.is_empty():
		for t in _baked:
			draw_texture_rect(t["tex"], t["rect"], false)
		_draw_grid()
		return
	if _ground:
		draw_texture_rect(_ground, _ground_rect, false)
	else:
		for h in game.terrain:
			draw_colored_polygon(Hex.corners(Hex.to_pixel(h)), GROUND_COLORS[game.terrain[h]])
	_draw_grid()
	for d in _decor:
		_draw_decor(d)
	_draw_borders()


## Faint dashed hex lines, each edge drawn once.
func _draw_grid() -> void:
	for h in game.terrain:
		var pts := Hex.corners(Hex.to_pixel(h))
		for i in 6:
			if i < 3 or not game.terrain.has(h + Hex.DIRS[i]):
				draw_dashed_line(pts[(6 - i) % 6], pts[(7 - i) % 6], GRID_COLOR, 1.5, 5.0)


## Each territory draws its own colour along edges it shares with a different
## owner, slightly inset, so rival borders appear as a red/blue double line.
func _draw_borders() -> void:
	for h in game.terrain:
		var o: int = territory[h]
		var center := Hex.to_pixel(h)
		var pts := Hex.corners(center, Hex.SIZE - 3.0)
		for i in 6:
			var n: Vector2i = h + Hex.DIRS[i]
			if game.terrain.has(n) and territory[n] == o:
				continue
			if o < 0 and not game.terrain.has(n):
				continue
			var a := pts[(6 - i) % 6]
			var b := pts[(7 - i) % 6]
			if o < 0:
				draw_line(a, b, NEUTRAL_BORDER, 2.0)
			else:
				var col: Color = game.SIDE_COLORS[o]
				draw_line(a, b, Color(0, 0, 0, 0.35), 8.0)
				draw_line(a, b, col.lightened(0.15), 5.0)


func _draw_decor(d: Dictionary) -> void:
	var p: Vector2 = d["pos"]
	var s: float = d["s"]
	match d["kind"]:
		"tree":
			draw_circle(p + Vector2(2, 3) * s, 6 * s, Color(0, 0, 0, 0.18))
			draw_colored_polygon(PackedVector2Array([p + Vector2(0, -13) * s, p + Vector2(7, 3) * s,
				p + Vector2(-7, 3) * s]), Color(0.17, 0.30, 0.15))
			draw_colored_polygon(PackedVector2Array([p + Vector2(0, -13) * s, p + Vector2(7, 3) * s,
				p + Vector2(0, 3) * s]), Color(0.12, 0.23, 0.11))
		"hill":
			var arc := PackedVector2Array()
			for k in 9:
				var a := PI + PI * k / 8.0
				arc.append(p + Vector2(cos(a) * 18, sin(a) * 11) * s)
			draw_colored_polygon(arc, Color(0.52, 0.46, 0.30))
			draw_polyline(arc, Color(0.36, 0.31, 0.20), 2.0)
			draw_line(p + Vector2(-4, -10) * s, p + Vector2(4, -4) * s, Color(0.72, 0.66, 0.48), 2.0)
		"grass":
			var g := Color(0.38, 0.45, 0.22, 0.8)
			draw_line(p, p + Vector2(-3, -6) * s, g, 1.5)
			draw_line(p, p + Vector2(0, -8) * s, g, 1.5)
			draw_line(p, p + Vector2(3, -6) * s, g, 1.5)
		"wave":
			var wc := Color(0.55, 0.70, 0.80, 0.6)
			draw_arc(p + Vector2(-6, 0), 6, PI, TAU, 6, wc, 1.5)
			draw_arc(p + Vector2(6, 0), 6, 0, PI, 6, wc, 1.5)
		"city":
			_draw_city(d["hex"], p)


func _draw_city(h: Vector2i, c: Vector2) -> void:
	var o: int = game.city_owner.get(h, -1)
	var oc: Color = game.SIDE_COLORS[o] if o >= 0 else game.NEUTRAL_COLOR
	var capital: bool = h in game.capitals
	draw_circle(c + Vector2(0, 8), 26, Color(0, 0, 0, 0.18))
	var blocks := [Rect2(-22, -2, 12, 18), Rect2(-9, -16, 13, 32), Rect2(6, -8, 12, 24), Rect2(-14, 8, 30, 10)]
	for b in blocks:
		var r := Rect2(c + b.position, b.size)
		draw_rect(r, Color(0.78, 0.76, 0.70))
		draw_rect(Rect2(r.position + Vector2(r.size.x * 0.6, 0), Vector2(r.size.x * 0.4, r.size.y)),
			Color(0.60, 0.58, 0.54))
		draw_rect(r, Color(0.30, 0.28, 0.26), false, 1.5)
	# Flag in the owner's colour.
	var pole := c + Vector2(16, -14)
	draw_line(pole, pole + Vector2(0, -26), Color(0.2, 0.2, 0.2), 2.0)
	draw_rect(Rect2(pole + Vector2(1, -26), Vector2(18, 12)), oc)
	draw_rect(Rect2(pole + Vector2(1, -26), Vector2(18, 12)), Color(0, 0, 0, 0.5), false, 1.0)
	if capital:
		_draw_star(pole + Vector2(10, -20), 5, Color.WHITE)


func _draw_star(c: Vector2, r: float, color: Color) -> void:
	var pts := PackedVector2Array()
	for i in 10:
		var a := -PI / 2 + i * PI / 5
		pts.append(c + Vector2(cos(a), sin(a)) * (r if i % 2 == 0 else r * 0.45))
	draw_colored_polygon(pts, color)
