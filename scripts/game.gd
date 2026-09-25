extends Node2D
## Main game controller: map, units, rules, input and rendering.

const MAP_W := 16
const MAP_H := 10  # must stay even: the map is point-symmetric for fairness
const SIDE_COLORS: Array[Color] = [Color(0.18, 0.44, 0.84), Color(0.84, 0.23, 0.18)]
const NEUTRAL_COLOR := Color(0.75, 0.75, 0.75)
const SIDE_NAMES: Array[String] = ["Синя коаліція", "Червоний альянс"]
const AI_DELAY := 0.35
const MOVE_ANIM_TIME := 0.25
const MIN_ZOOM := 0.5
const MAX_ZOOM := 2.5
const AUTOTEST_GAMES := 5
const AUTOTEST_TURN_LIMIT := 80

var terrain: Dictionary = {}  # Vector2i -> Rules.Terrain
var city_owner: Dictionary = {}  # Vector2i -> side, -1 = neutral
var capitals: Array[Vector2i] = [Vector2i.ZERO, Vector2i.ZERO]
var units: Array[Unit] = []
var money: Array[int] = [0, 0]
var turn := 1
var current_side := 0
var human_sides: Array[bool] = [true, false]
var winner := -1
var busy := false
var autotest := false
var rng := RandomNumberGenerator.new()

var selected: Unit = null
var reachable: Dictionary = {}  # Vector2i -> movement cost
var attackable: Dictionary = {}  # Vector2i -> true
var build_city: Variant = null  # Vector2i of the city whose build menu is open
var effects: Array[Dictionary] = []

var _touches: Dictionary = {}
var _drag_start := Vector2.ZERO
var _dragging := false
var _pinch_dist := 0.0
var _autotest_games := 0
var game_id := 0  # bumped on restart so a running AI coroutine stops

var hud: Hud
var ai := EnemyAI.new()
@onready var camera: Camera2D = $Camera2D


func _ready() -> void:
	autotest = "--autotest" in OS.get_cmdline_user_args()
	if autotest:
		human_sides = [false, false]
	hud = Hud.new()
	add_child(hud)
	hud.end_turn_pressed.connect(_on_end_turn_pressed)
	hud.build_pressed.connect(_on_build_pressed)
	hud.restart_pressed.connect(func() -> void: new_game())
	new_game(1 if autotest else -1)


# --- Game setup -------------------------------------------------------------

func new_game(seed_value: int = -1) -> void:
	if seed_value < 0:
		seed_value = randi()
	rng.seed = seed_value
	game_id += 1
	terrain.clear()
	city_owner.clear()
	units.clear()
	effects.clear()
	money = [Rules.START_MONEY, Rules.START_MONEY]
	turn = 1
	current_side = 0
	winner = -1
	busy = false
	_deselect()
	_generate_map(seed_value)
	_spawn_start_units()
	_fit_camera()
	hud.hide_game_over()
	_start_turn()


## 180° rotation of the rectangular map (exact in axial coords for even MAP_H).
func _mirror(h: Vector2i) -> Vector2i:
	return Hex.offset_to_axial(MAP_W - 1, MAP_H - 1) - h


func _set_sym(h: Vector2i, t: Rules.Terrain) -> void:
	terrain[h] = t
	terrain[_mirror(h)] = t


func _generate_map(seed_value: int) -> void:
	var noise := FastNoiseLite.new()
	noise.seed = seed_value
	noise.frequency = 0.14
	for row in MAP_H / 2:
		for col in MAP_W:
			var n := noise.get_noise_2d(col, row) + noise.get_noise_2d(col, MAP_H - 1 - row)
			var t := Rules.Terrain.PLAIN
			if n < -0.45:
				t = Rules.Terrain.WATER
			elif n > 0.45:
				t = Rules.Terrain.HILLS
			elif n > 0.12:
				t = Rules.Terrain.FOREST
			_set_sym(Hex.offset_to_axial(col, row), t)

	capitals[0] = Hex.offset_to_axial(1, MAP_H / 2 - 1)
	capitals[1] = _mirror(capitals[0])
	var cities: Array[Vector2i] = [capitals[0], capitals[1]]
	var tries := 0
	while cities.size() < 14 and tries < 400:
		tries += 1
		var h := Hex.offset_to_axial(rng.randi_range(1, MAP_W - 2), rng.randi_range(0, MAP_H - 1))
		var ok := Hex.distance(h, _mirror(h)) >= 3
		for c in cities:
			if Hex.distance(c, h) < 3:
				ok = false
				break
		if ok:
			cities.append(h)
			cities.append(_mirror(h))

	for c in cities:
		var col := Hex.axial_to_offset(c).x
		var owner := -1
		if col < MAP_W / 4:
			owner = 0
		elif col >= MAP_W - MAP_W / 4:
			owner = 1
		city_owner[c] = owner
	# Roads over water so every city is reachable by land.
	for c in cities:
		for h in Hex.line(c, capitals[0]):
			if terrain[h] == Rules.Terrain.WATER:
				_set_sym(h, Rules.Terrain.PLAIN)
	for c in capitals:
		for n in Hex.neighbors(c):
			if terrain.has(n) and terrain[n] == Rules.Terrain.WATER:
				_set_sym(n, Rules.Terrain.PLAIN)
	for c in cities:
		terrain[c] = Rules.Terrain.CITY


func _spawn_start_units() -> void:
	var types: Array[String] = ["infantry", "infantry", "tank", "artillery"]
	var spots := Hex.neighbors(capitals[0])
	for i in types.size():
		units.append(Unit.new(types[i], 0, spots[i]))
		units.append(Unit.new(types[i], 1, _mirror(spots[i])))


## Zoom so the whole map fits below the top bar.
func _fit_camera() -> void:
	var r := _map_rect()
	var vp := get_viewport_rect().size
	var bar := hud.top_panel.get_combined_minimum_size().y
	var z := clampf(minf(vp.x / r.size.x, (vp.y - bar) / r.size.y), MIN_ZOOM, MAX_ZOOM)
	camera.zoom = Vector2(z, z)
	camera.position = r.get_center() - Vector2(0, bar / 2.0 / z)


func _map_rect() -> Rect2:
	var r := Rect2(Hex.to_pixel(Hex.offset_to_axial(0, 0)), Vector2.ZERO)
	for h in terrain:
		r = r.expand(Hex.to_pixel(h))
	return r.grow(Hex.SIZE)


# --- Queries ----------------------------------------------------------------

func unit_at(h: Vector2i) -> Unit:
	for u in units:
		if u.pos == h:
			return u
	return null


func units_of(side: int) -> Array[Unit]:
	var res: Array[Unit] = []
	for u in units:
		if u.side == side:
			res.append(u)
	return res


func cities_of(side: int) -> Array[Vector2i]:
	var res: Array[Vector2i] = []
	for c in city_owner:
		if city_owner[c] == side:
			res.append(c)
	return res


func income(side: int) -> int:
	var total := 0
	for c in cities_of(side):
		total += Rules.INCOME_CAPITAL if c in capitals else Rules.INCOME_CITY
	return total


func move_cost(u: Unit, h: Vector2i) -> int:
	if not terrain.has(h):
		return -1
	if u.is_flying():
		return 1
	var cost: int = Rules.TERRAIN[terrain[h]]["cost"]
	if cost > 1 and u.data().get("heavy", false):
		cost += 1
	return cost


func in_enemy_zoc(h: Vector2i, side: int) -> bool:
	for n in Hex.neighbors(h):
		var o := unit_at(n)
		if o and o.side != side and not o.is_flying():
			return true
	return false


## Dijkstra over movement points; entering an enemy zone of control ends movement.
func compute_reachable(u: Unit) -> Dictionary:
	var result := {}
	if not u.can_move():
		return result
	var mp: int = u.data()["move"]
	var cost := {u.pos: 0}
	var open: Array[Vector2i] = [u.pos]
	while not open.is_empty():
		var best := 0
		for i in open.size():
			if cost[open[i]] < cost[open[best]]:
				best = i
		var cur: Vector2i = open[best]
		open.remove_at(best)
		if cur != u.pos and not u.is_flying() and in_enemy_zoc(cur, u.side):
			continue
		for n in Hex.neighbors(cur):
			var c := move_cost(u, n)
			if c < 0:
				continue
			var other := unit_at(n)
			if other and other.side != u.side:
				continue
			var nc: int = cost[cur] + c
			if nc > mp or (cost.has(n) and cost[n] <= nc):
				continue
			cost[n] = nc
			if not open.has(n):
				open.append(n)
	for h in cost:
		if h != u.pos and unit_at(h) == null:
			result[h] = cost[h]
	return result


func can_attack(att: Unit, target: Unit, from: Vector2i) -> bool:
	if target.side == att.side:
		return false
	if target.is_flying() and not att.data().get("hits_air", false):
		return false
	var d := Hex.distance(from, target.pos)
	return d >= att.data()["min_range"] and d <= att.data()["range"]


func targets_from(att: Unit, from: Vector2i) -> Array[Unit]:
	var res: Array[Unit] = []
	for u in units:
		if can_attack(att, u, from):
			res.append(u)
	return res


func is_done(u: Unit) -> bool:
	return not u.can_move() and (not u.can_fire() or targets_from(u, u.pos).is_empty())


func calc_damage(att: Unit, target: Unit, counter: bool = false) -> int:
	var ad := att.data()
	var atk: float = ad.get("air_atk", ad["atk"]) if target.is_flying() else ad["atk"]
	var strength := atk * (0.5 + 0.5 * float(att.hp) / att.max_hp())
	var defense: float = target.data()["def"]
	if not target.is_flying():
		defense += Rules.TERRAIN[terrain[target.pos]]["def"]
	var dmg := strength * 100.0 / (100.0 + defense * 1.5)
	if counter:
		dmg *= Rules.COUNTER_FACTOR
	return maxi(1, roundi(dmg))


# --- Actions ----------------------------------------------------------------

func move_unit(u: Unit, to: Vector2i) -> void:
	var from_px := u.draw_pos
	u.pos = to
	u.moved = true
	if terrain[to] == Rules.Terrain.CITY and not u.is_flying() and city_owner[to] != u.side:
		city_owner[to] = u.side
		_add_effect(Hex.to_pixel(to), "Захоплено!", Color.GOLD)
	var to_px := Hex.to_pixel(to)
	if autotest:
		u.draw_pos = to_px
	else:
		var tw := create_tween()
		tw.tween_method(func(p: Vector2) -> void:
			u.draw_pos = p
			queue_redraw(), from_px, to_px, MOVE_ANIM_TIME)
	_check_game_over()
	_after_action()


func attack(att: Unit, target: Unit) -> void:
	var dmg := roundi(calc_damage(att, target) * rng.randf_range(0.9, 1.1))
	_damage(target, dmg)
	if target.hp > 0 and can_attack(target, att, target.pos):
		_damage(att, roundi(calc_damage(target, att, true) * rng.randf_range(0.9, 1.1)))
	att.moved = true
	att.attacked = true
	_check_game_over()
	_after_action()


func build(city: Vector2i, type: String) -> bool:
	var cost: int = Rules.UNITS[type]["cost"]
	if city_owner.get(city, -1) != current_side or unit_at(city) or money[current_side] < cost:
		return false
	money[current_side] -= cost
	var u := Unit.new(type, current_side, city)
	u.moved = true
	u.attacked = true
	units.append(u)
	_after_action()
	return true


func _damage(u: Unit, dmg: int) -> void:
	u.hp -= maxi(1, dmg)
	_add_effect(Hex.to_pixel(u.pos), "-%d" % dmg, Color(1, 0.35, 0.3))
	if u.hp <= 0:
		units.erase(u)
		_add_effect(Hex.to_pixel(u.pos) + Vector2(0, 22), "Знищено", Color.ORANGE)
		if u == selected:
			_deselect()


func _after_action() -> void:
	_update_status()
	if selected and units.has(selected) and not is_done(selected):
		_select(selected)
	else:
		_deselect()
	queue_redraw()


func _check_game_over() -> void:
	if winner >= 0:
		return
	for s in 2:
		if city_owner[capitals[1 - s]] == s:
			_finish(s, "Столицю захоплено!")
			return
	for s in 2:
		if units_of(s).is_empty() and cities_of(s).is_empty():
			_finish(1 - s, "Армію знищено!")
			return


func _finish(side: int, reason: String) -> void:
	winner = side
	busy = false
	if autotest:
		print("[autotest] game %d: winner=%s turn=%d (%s)" % [_autotest_games + 1, SIDE_NAMES[side], turn, reason])
		_next_autotest_game()
		return
	var title := "ПЕРЕМОГА!" if human_sides[side] else "ПОРАЗКА"
	hud.show_game_over("%s\n%s\nПереможець: %s" % [title, reason, SIDE_NAMES[side]])


func _next_autotest_game() -> void:
	_autotest_games += 1
	if _autotest_games >= AUTOTEST_GAMES:
		print("[autotest] done")
		get_tree().quit()
	else:
		new_game.call_deferred(_autotest_games + 1)


# --- Turn flow --------------------------------------------------------------

func _start_turn() -> void:
	money[current_side] += income(current_side)
	for u in units_of(current_side):
		u.moved = false
		u.attacked = false
		if city_owner.get(u.pos, -1) == current_side:
			u.hp = mini(u.max_hp(), u.hp + Rules.HEAL_IN_CITY)
	_update_status()
	queue_redraw()
	if human_sides[current_side]:
		busy = false
	else:
		busy = true
		_run_ai.call_deferred()


func end_turn() -> void:
	if winner >= 0:
		return
	_deselect()
	current_side = 1 - current_side
	if current_side == 0:
		turn += 1
		if autotest and turn > AUTOTEST_TURN_LIMIT:
			print("[autotest] game %d: draw by turn limit, units %d/%d, cities %d/%d" % [
				_autotest_games + 1, units_of(0).size(), units_of(1).size(),
				cities_of(0).size(), cities_of(1).size()])
			winner = 2
			_next_autotest_game()
			return
	_start_turn()


func _run_ai() -> void:
	var side := current_side
	var id := game_id
	await ai.take_turn(self)
	if winner < 0 and current_side == side and id == game_id:
		end_turn()


func ai_pause() -> void:
	if not autotest:
		await get_tree().create_timer(AI_DELAY).timeout


func _update_status() -> void:
	var who := "Ваш хід" if human_sides[current_side] else "Хід противника…"
	hud.set_status("Хід %d · %s · %s · Кошти: %d $ (+%d)" % [
		turn, SIDE_NAMES[current_side], who, money[current_side], income(current_side)],
		human_sides[current_side] and not busy and winner < 0)


# --- Player input -----------------------------------------------------------

func _on_end_turn_pressed() -> void:
	if not busy and winner < 0 and human_sides[current_side]:
		end_turn()


func _on_build_pressed(type: String) -> void:
	if build_city != null and human_sides[current_side] and not busy:
		build(build_city, type)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed:
			_touches[event.index] = event.position
			_pinch_dist = 0.0
			if _touches.size() == 1:
				_drag_start = event.position
				_dragging = false
		else:
			if _touches.size() == 1 and not _dragging:
				_on_tap(event.position)
			_touches.erase(event.index)
			_pinch_dist = 0.0
			if _touches.size() > 0:
				_dragging = true  # finishing a pinch must not produce a tap
	elif event is InputEventScreenDrag:
		_touches[event.index] = event.position
		if _touches.size() == 1:
			if not _dragging and event.position.distance_to(_drag_start) > 14.0:
				_dragging = true
			if _dragging:
				_pan(-event.relative / camera.zoom.x)
		elif _touches.size() == 2:
			_dragging = true
			var pts := _touches.values()
			var d: float = pts[0].distance_to(pts[1])
			if _pinch_dist > 0.0:
				_zoom(d / _pinch_dist)
			_pinch_dist = d
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom(1.1)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom(1.0 / 1.1)
	elif event is InputEventMagnifyGesture:
		_zoom(event.factor)


func _pan(delta: Vector2) -> void:
	var r := _map_rect()
	camera.position = (camera.position + delta).clamp(r.position, r.end)


func _zoom(factor: float) -> void:
	var z := clampf(camera.zoom.x * factor, MIN_ZOOM, MAX_ZOOM)
	camera.zoom = Vector2(z, z)


func _on_tap(screen_pos: Vector2) -> void:
	if hud.is_over_ui(screen_pos) or busy or winner >= 0 or not human_sides[current_side]:
		return
	var h := Hex.from_pixel(get_canvas_transform().affine_inverse() * screen_pos)
	if not terrain.has(h):
		_deselect()
		return
	var u := unit_at(h)
	if selected:
		if attackable.has(h) and u:
			attack(selected, u)
			return
		if reachable.has(h):
			move_unit(selected, h)
			return
	if u and u.side == current_side and u != selected:
		_select(u)
		return
	_deselect()
	if u:
		hud.show_info(_unit_text(u) + "\n" + _terrain_text(h))
	elif city_owner.get(h, -1) == current_side:
		_open_build(h)
	else:
		hud.show_info(_terrain_text(h))


func _select(u: Unit) -> void:
	selected = u
	build_city = null
	reachable = compute_reachable(u)
	attackable.clear()
	if u.can_fire():
		for t in targets_from(u, u.pos):
			attackable[t.pos] = true
	hud.show_info(_unit_text(u) + "\n" + _terrain_text(u.pos))
	queue_redraw()


func _deselect() -> void:
	selected = null
	build_city = null
	reachable.clear()
	attackable.clear()
	if hud:
		hud.show_info("")
	queue_redraw()


func _open_build(city: Vector2i) -> void:
	build_city = city
	var options := []
	for t in Rules.BUILD_ORDER:
		var cost: int = Rules.UNITS[t]["cost"]
		options.append({"type": t, "name": Rules.UNITS[t]["name"], "cost": cost,
			"enabled": money[current_side] >= cost})
	hud.show_build("Мобілізація у місті (кошти: %d $):" % money[current_side], options)
	queue_redraw()


func _unit_text(u: Unit) -> String:
	var d := u.data()
	var rng_text := str(d["range"]) if d["min_range"] == d["range"] else "%d–%d" % [d["min_range"], d["range"]]
	return "%s [%s] · HP %d/%d · Атака %d · Захист %d · Хід %d · Дальність %s" % [
		d["name"], SIDE_NAMES[u.side], u.hp, u.max_hp(), d["atk"], d["def"], d["move"], rng_text]


func _terrain_text(h: Vector2i) -> String:
	var t: Dictionary = Rules.TERRAIN[terrain[h]]
	var s := "Місцевість: %s (захист +%d%%)" % [t["name"], t["def"]]
	if city_owner.has(h):
		var o: int = city_owner[h]
		s += " · %s: %s" % ["Столиця" if h in capitals else "Місто", SIDE_NAMES[o] if o >= 0 else "нейтральне"]
	return s


# --- Rendering --------------------------------------------------------------

func _add_effect(p: Vector2, text: String, color: Color) -> void:
	if not autotest:
		effects.append({"pos": p, "text": text, "color": color, "t": 0.0})


func _process(delta: float) -> void:
	if effects.is_empty():
		return
	for e in effects:
		e["t"] += delta
	effects = effects.filter(func(e: Dictionary) -> bool: return e["t"] < 1.2)
	queue_redraw()


func _draw() -> void:
	for h in terrain:
		_draw_hex(h)
	for h in reachable:
		draw_colored_polygon(Hex.corners(Hex.to_pixel(h), Hex.SIZE - 3), Color(1, 1, 1, 0.28))
	for h in attackable:
		draw_colored_polygon(Hex.corners(Hex.to_pixel(h), Hex.SIZE - 3), Color(1, 0.15, 0.1, 0.45))
	var ring: Variant = selected.pos if selected else build_city
	if ring != null:
		var pts := Hex.corners(Hex.to_pixel(ring), Hex.SIZE - 2)
		pts.append(pts[0])
		draw_polyline(pts, Color.YELLOW, 4.0)
	for u in units:
		_draw_unit(u)
	var font := ThemeDB.fallback_font
	for e in effects:
		var t: float = e["t"]
		var c: Color = e["color"]
		c.a = clampf(1.2 - t, 0.0, 1.0)
		var p: Vector2 = e["pos"] + Vector2(-80, -30 - 40 * t)
		draw_string_outline(font, p, e["text"], HORIZONTAL_ALIGNMENT_CENTER, 160, 26, 6, Color(0, 0, 0, c.a))
		draw_string(font, p, e["text"], HORIZONTAL_ALIGNMENT_CENTER, 160, 26, c)


func _draw_hex(h: Vector2i) -> void:
	var c := Hex.to_pixel(h)
	var t: Rules.Terrain = terrain[h]
	var base: Color = Rules.TERRAIN[t]["color"]
	var pts := Hex.corners(c)
	draw_colored_polygon(pts, base)
	pts.append(pts[0])
	draw_polyline(pts, base.darkened(0.35), 1.5)
	match t:
		Rules.Terrain.FOREST:
			for o in [Vector2(-16, 4), Vector2(0, -12), Vector2(16, 4)]:
				var p: Vector2 = c + o
				draw_colored_polygon(PackedVector2Array([p + Vector2(0, -12), p + Vector2(9, 8), p + Vector2(-9, 8)]),
					base.darkened(0.35))
		Rules.Terrain.HILLS:
			for o in [Vector2(-12, 6), Vector2(10, 0)]:
				var p: Vector2 = c + o
				draw_polyline(PackedVector2Array([p + Vector2(-14, 8), p + Vector2(0, -10), p + Vector2(14, 8)]),
					base.darkened(0.4), 3.0)
		Rules.Terrain.WATER:
			for y in [-8, 8]:
				draw_arc(c + Vector2(-8, y), 8, PI, TAU, 8, base.lightened(0.3), 2.0)
				draw_arc(c + Vector2(8, y), 8, 0, PI, 8, base.lightened(0.3), 2.0)
		Rules.Terrain.CITY:
			var o: int = city_owner.get(h, -1)
			var oc := SIDE_COLORS[o] if o >= 0 else NEUTRAL_COLOR
			var inner := Hex.corners(c, Hex.SIZE - 5)
			inner.append(inner[0])
			draw_polyline(inner, oc, 5.0 if h in capitals else 3.0)
			for b in [Rect2(-22, -4, 12, 22), Rect2(-8, -18, 14, 36), Rect2(8, -8, 12, 26)]:
				draw_rect(Rect2(c + b.position, b.size), Color(0.35, 0.37, 0.4))
			if h in capitals:
				_draw_star(c + Vector2(0, -30), 10, oc)


func _draw_star(c: Vector2, r: float, color: Color) -> void:
	var pts := PackedVector2Array()
	for i in 10:
		var a := -PI / 2 + i * PI / 5
		pts.append(c + Vector2(cos(a), sin(a)) * (r if i % 2 == 0 else r * 0.45))
	draw_colored_polygon(pts, color)


## Units use simplified NATO map symbols.
func _draw_unit(u: Unit) -> void:
	var c := u.draw_pos + Vector2(0, -4)
	var col := SIDE_COLORS[u.side]
	if u.side == current_side and human_sides[u.side] and is_done(u):
		col = col.darkened(0.5)
	var rect := Rect2(c - Vector2(24, 16), Vector2(48, 32))
	draw_rect(rect, col)
	draw_rect(rect, Color.WHITE, false, 2.0)
	var w := Color.WHITE
	var i := rect.grow(-4)
	match u.type:
		"infantry":
			draw_line(i.position, i.end, w, 2.0)
			draw_line(Vector2(i.position.x, i.end.y), Vector2(i.end.x, i.position.y), w, 2.0)
		"tank":
			var pts := PackedVector2Array()
			for k in 21:
				var a := TAU * k / 20.0
				pts.append(c + Vector2(cos(a) * 15, sin(a) * 8))
			draw_polyline(pts, w, 2.0)
		"artillery":
			draw_circle(c, 6, w)
		"air_defense":
			draw_arc(c + Vector2(0, 10), 14, PI, TAU, 12, w, 2.0)
			draw_circle(c + Vector2(0, 4), 3, w)
		"drone":
			draw_polyline(PackedVector2Array([c + Vector2(-16, -6), c + Vector2(0, 6), c + Vector2(16, -6)]), w, 2.5)
			draw_line(c + Vector2(0, 6), c + Vector2(0, -8), w, 2.0)
	var frac := float(u.hp) / u.max_hp()
	var bar := Rect2(c + Vector2(-24, 19), Vector2(48, 6))
	draw_rect(bar, Color(0, 0, 0, 0.7))
	var hp_col := Color(0.3, 0.9, 0.3) if frac > 0.6 else (Color(0.95, 0.8, 0.2) if frac > 0.3 else Color(0.95, 0.25, 0.2))
	draw_rect(Rect2(bar.position, Vector2(48 * frac, 6)), hp_col)
