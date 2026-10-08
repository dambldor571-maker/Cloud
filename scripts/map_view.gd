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
	for y in hgt:
		for x in w:
			var p := r.position + Vector2(x + 0.5, y + 0.5) * GROUND_SCALE
			var wp := p + Vector2(warp.get_noise_2d(p.x, p.y), warp.get_noise_2d(p.y + 913.0, p.x - 377.0)) * WARP
			var h := Hex.from_pixel(wp)
			if not game.terrain.has(h):
				continue
			var c: Color = GROUND_COLORS[game.terrain[h]]
			var n := tint.get_noise_2d(p.x, p.y) * 0.22
			c = c.lightened(n) if n > 0.0 else c.darkened(-n)
			img.set_pixel(x, y, c)
	_ground_rect = Rect2(r.position, Vector2(w, hgt) * GROUND_SCALE)
	return ImageTexture.create_from_image(img)


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
	var capital: bool = game.is_hq(h)
	draw_circle(c + Vector2(0, 8), 30, Color(0, 0, 0, 0.18))
	if game.airfields.has(h):
		# Runway with centre-line dashes and a small hangar.
		var rw := PackedVector2Array([c + Vector2(-34, 10), c + Vector2(26, -22), c + Vector2(34, -12), c + Vector2(-26, 20)])
		draw_colored_polygon(rw, Color(0.36, 0.37, 0.38))
		for k in 5:
			var t := (k + 0.5) / 5.0
			var p := (c + Vector2(-30, 15)).lerp(c + Vector2(30, -17), t)
			draw_line(p, p + Vector2(5, -2.7), Color(0.95, 0.95, 0.9), 2.0)
		draw_rect(Rect2(c + Vector2(-22, -18), Vector2(16, 12)), Color(0.70, 0.68, 0.62))
		draw_rect(Rect2(c + Vector2(-22, -18), Vector2(16, 12)), Color(0.30, 0.28, 0.26), false, 1.5)
	else:
		var blocks := [Rect2(-22, -2, 12, 18), Rect2(-9, -16, 13, 32), Rect2(6, -8, 12, 24), Rect2(-14, 8, 30, 10)]
		if capital:
			blocks.append(Rect2(-30, 4, 9, 12))
		for b in blocks:
			var r := Rect2(c + b.position, b.size)
			draw_rect(r, Color(0.78, 0.76, 0.70))
			draw_rect(Rect2(r.position + Vector2(r.size.x * 0.6, 0), Vector2(r.size.x * 0.4, r.size.y)),
				Color(0.60, 0.58, 0.54))
			draw_rect(r, Color(0.30, 0.28, 0.26), false, 1.5)
	# Flag in the owner's colour; HQs carry a star.
	var pole := c + Vector2(16, -14)
	draw_line(pole, pole + Vector2(0, -28), Color(0.2, 0.2, 0.2), 2.0)
	var flag := Rect2(pole + Vector2(1, -28), Vector2(22, 14) if capital else Vector2(18, 12))
	draw_rect(flag, oc)
	draw_rect(flag, Color(0, 0, 0, 0.5), false, 1.0)
	if capital:
		_draw_star(flag.get_center(), 6, Color.WHITE)
	var name: String = game.city_names.get(h, "")
	if name != "":
		var font := UiKit.bold()
		var p := c + Vector2(-90, 40)
		draw_string_outline(font, p, name, HORIZONTAL_ALIGNMENT_CENTER, 180, 15, 5, Color(0, 0, 0, 0.75))
		draw_string(font, p, name, HORIZONTAL_ALIGNMENT_CENTER, 180, 15, Color(1, 0.97, 0.88) if not capital else UiKit.GOLD)


func _draw_star(c: Vector2, r: float, color: Color) -> void:
	var pts := PackedVector2Array()
	for i in 10:
		var a := -PI / 2 + i * PI / 5
		pts.append(c + Vector2(cos(a), sin(a)) * (r if i % 2 == 0 else r * 0.45))
	draw_colored_polygon(pts, color)
