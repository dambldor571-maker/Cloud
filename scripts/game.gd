extends Node2D
## Main game controller: map, units, rules, input and rendering.

const MAP_W := 16
const MAP_H := 10  # must stay even: the map is point-symmetric for fairness
const SIDE_COLORS: Array[Color] = [Color(0.18, 0.44, 0.84), Color(0.84, 0.23, 0.18)]
const NEUTRAL_COLOR := Color(0.75, 0.75, 0.75)
const SIDE_NAMES: Array[String] = ["Синя коаліція", "Червоний альянс"]
const AI_DELAY := 0.35
const MOVE_STEP_TIME := 0.5  # seconds per hex
const HULL_TURN_SPEED := 120.0  # degrees per second
const TURRET_TURN_SPEED := 90.0
const SCAN_SPEED := 15.0  # idle turret scan, degrees per second
const SCAN_RANGE := 45.0  # idle scan swings at most this far either side
const SCAN_PAUSE := Vector2(1.5, 4.5)  # seconds between scan moves
const RECOIL_KICK := 0.04  # gun slams back (seconds at full recoil)
const RECOIL_RETURN := 0.5  # then runs out again
const COUNTER_DELAY := 0.35  # defender fires back after this
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
## Prototype sandbox: no opponent, the player moves every unit of both sides,
## any unit may attack any other, and nobody dies. Off in the AI autotest.
var sandbox := true
var rng := RandomNumberGenerator.new()

var selected: Unit = null
var reachable: Dictionary = {}  # Vector2i -> movement cost
var attackable: Dictionary = {}  # Vector2i -> true
var build_city: Variant = null  # Vector2i of the city whose build menu is open
var route_parents: Dictionary = {}  # hex -> previous hex on the cheapest path of `selected`
var route: Array[Vector2i] = []  # planned path (start first) waiting for "Рух"
var _moving := 0  # move animations in progress
var effects: Array[Dictionary] = []

var _touches: Dictionary = {}
var _drag_start := Vector2.ZERO
var _dragging := false
var _pinch_dist := 0.0
var _autotest_games := 0
var game_id := 0  # bumped on restart so a running AI coroutine stops

var hud: Hud
var map_view: MapView
var sprites: Dictionary = {}  # unit type -> sprite set (see _load_sprites)
var fx_rng := RandomNumberGenerator.new()  # visual-only randomness (turret scan)
var ai := EnemyAI.new()
@onready var camera: Camera2D = $Camera2D


func _ready() -> void:
	fx_rng.randomize()
	autotest = "--autotest" in OS.get_cmdline_user_args()
	if autotest:
		human_sides = [false, false]
		sandbox = false
	elif sandbox:
		human_sides = [true, true]
	_load_sprites()
	map_view = MapView.new(self)
	add_child(map_view)
	hud = Hud.new()
	add_child(hud)
	hud.end_turn_pressed.connect(_on_end_turn_pressed)
	hud.build_pressed.connect(_on_build_pressed)
	hud.restart_pressed.connect(func() -> void: new_game())
	hud.move_confirmed.connect(_confirm_move)
	hud.move_cancelled.connect(_clear_route)
	new_game(1 if autotest else -1)


# --- Game setup -------------------------------------------------------------

func _load_sprites() -> void:
	for type in Rules.SPRITES:
		var base: String = "res://assets/units/" + Rules.SPRITES[type]
		var meta = JSON.parse_string(FileAccess.get_file_as_string(base + ".json"))
		if not meta is Dictionary:
			continue
		var spr := {
			# hull offset in sprite pixels, and how much the camera tilt squashes depth
			"hull_px": float(meta.get("hull_offset_m", 0.0)) * float(meta["px_per_m"]),
			"squash": sin(deg_to_rad(float(meta.get("elevation", 90.0)))),
			"layers": meta.get("layers", false),
		}
		if spr["layers"]:
			# Separate hull and turret layers, N headings each (tools/render_units.gd).
			var hull: Array[Texture2D] = []
			var turret: Array = []  # [recoil step][heading], step 0 = gun forward
			var offsets: Array[Vector2] = []
			for k in int(meta.get("recoil_steps", 1)):
				turret.append([] as Array[Texture2D])
			for i in int(meta["frames"]):
				hull.append(load("%s_hull_%d.png" % [base, i]) as Texture2D)
				for k in turret.size():
					var file := "%s_turret_%d.png" % [base, i] if k == 0 else "%s_turret_%d_r%d.png" % [base, i, k]
					turret[k].append(load(file) as Texture2D)
				offsets.append(Vector2(meta["turret_offsets"][i][0], meta["turret_offsets"][i][1]))
			spr["hull"] = hull
			spr["turret"] = turret
			spr["turret_offsets"] = offsets
			spr["hull_anchor"] = Vector2(meta["hull_anchor"][0], meta["hull_anchor"][1])
			spr["turret_anchor"] = Vector2(meta["turret_anchor"][0], meta["turret_anchor"][1])
		else:
			var frames: Array[Texture2D] = []
			for d in int(meta.get("directions", 6)):
				frames.append(load("%s_%d.png" % [base, d]) as Texture2D)
			spr["frames"] = frames
			spr["anchor"] = Vector2(meta["anchor"][0], meta["anchor"][1])
		sprites[type] = spr


func has_turret(u: Unit) -> bool:
	return sprites.has(u.type) and sprites[u.type]["layers"]


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
	map_view.rebuild(seed_value, not autotest)
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
## Fills `parents` (hex -> previous hex) so the cheapest path can be rebuilt.
func compute_reachable(u: Unit, parents: Dictionary = {}) -> Dictionary:
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
			parents[n] = cur
			if not open.has(n):
				open.append(n)
	for h in cost:
		if h != u.pos and unit_at(h) == null:
			result[h] = cost[h]
	return result


## Cheapest path from the unit to `to`, start included; empty if unreachable.
func path_to(u: Unit, to: Vector2i, parents: Dictionary = {}) -> Array[Vector2i]:
	if parents.is_empty():
		compute_reachable(u, parents)
	var path: Array[Vector2i] = []
	var h := to
	while h != u.pos:
		if not parents.has(h):
			return []
		path.push_front(h)
		h = parents[h]
	path.push_front(u.pos)
	return path


func is_hostile(a: Unit, b: Unit) -> bool:
	return a != b and (sandbox or a.side != b.side)


func controllable(u: Unit) -> bool:
	return sandbox or u.side == current_side


func can_attack(att: Unit, target: Unit, from: Vector2i) -> bool:
	if not is_hostile(att, target):
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

## Moves hex by hex along the cheapest path (or the given one), turning the
## hull towards each step. Game state changes at once; the animation follows.
func move_unit(u: Unit, to: Vector2i, path: Array[Vector2i] = []) -> void:
	if path.is_empty():
		path = path_to(u, to)
	if path.size() < 2:
		path = [u.pos, to]
	u.pos = to
	u.moved = true
	if autotest:
		u.face_step(path[path.size() - 2], to)
		u.draw_pos = Hex.to_pixel(to)
		_arrive(u, to)
		_after_action()
		return
	_moving += 1
	busy = true
	_deselect()
	var tw := create_tween()
	u.animating = true
	var turret := has_turret(u)
	var heading := u.hull_angle
	var aim := u.turret_angle if turret else heading
	for i in path.size() - 1:
		var a: Vector2i = path[i]
		var b: Vector2i = path[i + 1]
		# Turn on the spot first (the turret swings to the same heading at the
		# same time), then drive.
		var dir := Hex.DIRS.find(b - a)
		var target := 60.0 * dir
		var dh := wrapf(target - heading, -180.0, 180.0)
		var dt := wrapf(target - aim, -180.0, 180.0) if turret else dh
		var th := absf(dh) / HULL_TURN_SPEED
		var tt := absf(dt) / TURRET_TURN_SPEED if turret else th
		var dur := maxf(th, tt)
		if dur > 0.001:
			var h0 := heading
			var t0 := aim
			tw.tween_method(func(elapsed: float) -> void:
				u.hull_angle = h0 + dh * (1.0 if th <= 0.0 else minf(1.0, elapsed / th))
				u.turret_angle = t0 + dt * (1.0 if tt <= 0.0 else minf(1.0, elapsed / tt))
				u.facing = posmod(roundi(u.hull_angle / 60.0), 6)
				queue_redraw(), 0.0, dur, dur)
		tw.tween_callback(func() -> void: u.set_facing(dir))
		heading = target
		aim = target
		tw.tween_method(func(p: Vector2) -> void:
			u.draw_pos = p
			queue_redraw(), Hex.to_pixel(a), Hex.to_pixel(b), MOVE_STEP_TIME)
	tw.tween_callback(func() -> void:
		u.animating = false
		_arrive(u, to)
		_moving -= 1
		busy = _moving > 0 or not human_sides[current_side]
		if human_sides[current_side] and units.has(u) and not is_done(u):
			selected = u
		_after_action())


## Effects of ending a move on a hex: capturing a city (possibly winning).
func _arrive(u: Unit, to: Vector2i) -> void:
	if terrain[to] == Rules.Terrain.CITY and not u.is_flying() and city_owner[to] != u.side:
		city_owner[to] = u.side
		map_view.update_territory()
		_add_effect(Hex.to_pixel(to), "Захоплено!", Color.GOLD)
	_check_game_over()


## Units with a turret keep their hull and swing the turret onto the target;
## the shot lands once it has turned. Only the attacker turns: the defender
## keeps its hull and turret as they are. Units without a turret simply face
## the target.
func attack(att: Unit, target: Unit) -> void:
	att.moved = true
	att.attacked = true
	var fires_back := can_attack(target, att, target.pos)
	if autotest:
		_aim_now(att, target.draw_pos)
		_resolve_attack(att, target)
		_after_action()
		return
	_moving += 1
	busy = true
	_deselect()
	var tw := create_tween().set_parallel(true)
	tw.tween_interval(0.05)
	_aim(tw, att, target.draw_pos)
	# Fire once on target (the gun recoils). The defender does not turn its turret;
	# if it can, it still returns fire a moment later (damage only, no recoil).
	tw.chain().tween_callback(func() -> void:
		att.turret_rest = att.turret_angle
		att.scan_target = att.turret_rest
		_fire(att, target, false))
	if fires_back:
		tw.chain().tween_interval(COUNTER_DELAY)
		tw.chain().tween_callback(func() -> void:
			if units.has(target) and target.hp > 0 and can_attack(target, att, target.pos):
				_fire(target, att, true, false))
	tw.chain().tween_interval(RECOIL_KICK + RECOIL_RETURN)
	tw.chain().tween_callback(func() -> void:
		att.animating = false
		_check_game_over()
		_moving -= 1
		busy = _moving > 0 or not human_sides[current_side]
		if human_sides[current_side] and units.has(att) and not is_done(att):
			selected = att
		_after_action())


## One shot: the shooter's gun recoils and the hit lands on the target.
func _fire(shooter: Unit, target: Unit, counter: bool, recoil := true) -> void:
	if recoil:
		shooter.recoil_time = 0.0
	_damage(target, roundi(calc_damage(shooter, target, counter) * rng.randf_range(0.9, 1.1)))


## Which recoil sprite to show: slammed back for RECOIL_KICK, then easing out.
func _recoil_step(u: Unit, steps: int) -> int:
	if u.recoil_time < 0.0 or steps < 2:
		return 0
	if u.recoil_time < RECOIL_KICK:
		return steps - 1
	var k := 1.0 - (u.recoil_time - RECOIL_KICK) / RECOIL_RETURN
	return clampi(roundi(k * (steps - 1)), 0, steps - 1)


func _resolve_attack(att: Unit, target: Unit) -> void:
	var dmg := roundi(calc_damage(att, target) * rng.randf_range(0.9, 1.1))
	_damage(target, dmg)
	if target.hp > 0 and can_attack(target, att, target.pos):
		_damage(att, roundi(calc_damage(target, att, true) * rng.randf_range(0.9, 1.1)))
	_check_game_over()


static func _bearing(from: Vector2, to: Vector2) -> float:
	var d := to - from
	return rad_to_deg(atan2(-d.y, d.x))


## Adds the turret swing towards p to the (parallel) tween.
func _aim(tw: Tween, u: Unit, p: Vector2) -> void:
	if not has_turret(u):
		u.face_towards(p)
		return
	u.animating = true
	var t0 := u.turret_angle
	var dt := wrapf(_bearing(u.draw_pos, p) - t0, -180.0, 180.0)
	tw.tween_method(func(k: float) -> void:
		u.turret_angle = t0 + dt * k
		queue_redraw(), 0.0, 1.0, maxf(absf(dt) / TURRET_TURN_SPEED, 0.05))


func _aim_now(u: Unit, p: Vector2) -> void:
	if has_turret(u):
		u.turret_angle = _bearing(u.draw_pos, p)
		u.turret_rest = u.turret_angle
		u.scan_target = u.turret_rest
	else:
		u.face_towards(p)


func build(city: Vector2i, type: String) -> bool:
	var cost: int = Rules.UNITS[type]["cost"]
	var side: int = city_owner.get(city, -1)
	if side < 0 or (side != current_side and not sandbox) or unit_at(city) or money[side] < cost:
		return false
	money[side] -= cost
	var u := Unit.new(type, side, city)
	u.moved = true
	u.attacked = true
	units.append(u)
	_after_action()
	return true


func _damage(u: Unit, dmg: int) -> void:
	u.hp -= maxi(1, dmg)
	_add_effect(Hex.to_pixel(u.pos), "-%d" % dmg, Color(1, 0.35, 0.3))
	if sandbox:
		u.hp = maxi(1, u.hp)  # immortal in the sandbox
		return
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
	if winner >= 0 or sandbox:
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
	var sides := [0, 1] if sandbox else [current_side]
	for side in sides:
		money[side] += income(side)
		for u in units_of(side):
			u.moved = false
			u.attacked = false
			if city_owner.get(u.pos, -1) == side:
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
	if sandbox:
		turn += 1
		_start_turn()
		return
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
		while _moving > 0:
			await get_tree().process_frame


func _update_status() -> void:
	if sandbox:
		hud.set_status("Пісочниця · Хід %d · Сині: %d $ (+%d) · Червоні: %d $ (+%d)" % [
			turn, money[0], income(0), money[1], income(1)], not busy)
		return
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
			_clear_route()
			attack(selected, u)
			return
		if reachable.has(h):
			if not route.is_empty() and route.back() == h:
				_confirm_move()  # second tap on the destination = "Рух"
			else:
				_plan_route(h)
			return
	if u and controllable(u) and u != selected:
		_select(u)
		return
	_deselect()
	if u:
		hud.show_info(_unit_text(u) + "\n" + _terrain_text(h))
	elif city_owner.get(h, -1) == current_side or (sandbox and city_owner.get(h, -1) >= 0):
		_open_build(h)
	else:
		hud.show_info(_terrain_text(h))


func _plan_route(dest: Vector2i) -> void:
	route = path_to(selected, dest, route_parents)
	if route.is_empty():
		return
	hud.show_move_confirm(route.size() - 1)
	_place_move_confirm()
	queue_redraw()


func _confirm_move() -> void:
	if route.is_empty() or selected == null or busy:
		return
	var path := route.duplicate()
	var u := selected
	_clear_route()
	move_unit(u, path.back(), path)


func _clear_route() -> void:
	route.clear()
	if hud:
		hud.hide_move_confirm()
	queue_redraw()


## Keeps the "Рух / Скасувати" buttons just under the destination hex.
func _place_move_confirm() -> void:
	if route.is_empty():
		return
	var below := Hex.to_pixel(route.back()) + Vector2(0, Hex.SIZE * 0.95)
	hud.place_move_confirm(get_canvas_transform() * below)


func _select(u: Unit) -> void:
	_clear_route()
	selected = u
	build_city = null
	route_parents = {}
	reachable = compute_reachable(u, route_parents)
	attackable.clear()
	if u.can_fire():
		for t in targets_from(u, u.pos):
			attackable[t.pos] = true
	hud.show_info(_unit_text(u) + "\n" + _terrain_text(u.pos))
	queue_redraw()


func _deselect() -> void:
	_clear_route()
	selected = null
	build_city = null
	reachable.clear()
	attackable.clear()
	if hud:
		hud.show_info("")
	queue_redraw()


func _open_build(city: Vector2i) -> void:
	build_city = city
	var side: int = city_owner[city]
	var options := []
	for t in Rules.BUILD_ORDER:
		var cost: int = Rules.UNITS[t]["cost"]
		options.append({"type": t, "name": Rules.UNITS[t]["name"], "cost": cost,
			"enabled": money[side] >= cost})
	hud.show_build("Мобілізація · %s (кошти: %d $):" % [SIDE_NAMES[side], money[side]], options)
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
	_place_move_confirm()
	if not autotest:
		var scanned := _scan_turrets(delta)
		var recoiling := _advance_recoil(delta)  # both must run every frame
		if scanned or recoiling:
			queue_redraw()
	if effects.is_empty():
		return
	for e in effects:
		e["t"] += delta
	effects = effects.filter(func(e: Dictionary) -> bool: return e["t"] < 1.2)
	queue_redraw()


func _advance_recoil(delta: float) -> bool:
	var active := false
	for u in units:
		if u.recoil_time >= 0.0:
			u.recoil_time += delta
			if u.recoil_time > RECOIL_KICK + RECOIL_RETURN:
				u.recoil_time = -1.0
			active = true
	return active


## Idle turrets now and then swing slowly left or right, at most SCAN_RANGE
## from where they last aimed, and pause between swings.
func _scan_turrets(delta: float) -> bool:
	var changed := false
	for u in units:
		if u.animating or not has_turret(u):
			continue
		if u.scan_wait > 0.0:
			u.scan_wait -= delta
			continue
		var d := wrapf(u.scan_target - u.turret_angle, -180.0, 180.0)
		var step := SCAN_SPEED * delta
		if absf(d) <= step:
			u.turret_angle = u.scan_target
			u.scan_wait = fx_rng.randf_range(SCAN_PAUSE.x, SCAN_PAUSE.y)
			var back := fx_rng.randf() < 0.3
			u.scan_target = u.turret_rest + (0.0 if back else fx_rng.randf_range(-SCAN_RANGE, SCAN_RANGE))
		else:
			u.turret_angle += signf(d) * step
		changed = true
	return changed


func _draw() -> void:
	for h in reachable:
		_draw_highlight(h, Color(1, 1, 0.85, 0.22), Color(1, 1, 0.85, 0.55))
	for h in attackable:
		_draw_highlight(h, Color(1, 0.15, 0.1, 0.35), Color(1, 0.3, 0.2, 0.9))
	var ring: Variant = selected.pos if selected else build_city
	if ring != null:
		var pts := Hex.corners(Hex.to_pixel(ring), Hex.SIZE - 2)
		pts.append(pts[0])
		draw_polyline(pts, Color.YELLOW, 4.0)
	_draw_route()
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


const ROUTE_COLOR := Color(1.0, 0.84, 0.25)


## Planned path: line through hex centres, a dot per step, arrow and target ring.
func _draw_route() -> void:
	if route.size() < 2:
		return
	var pts := PackedVector2Array()
	for h in route:
		pts.append(Hex.to_pixel(h))
	var end := pts[pts.size() - 1]
	var dir := (end - pts[pts.size() - 2]).normalized()
	var line := pts.duplicate()
	line[line.size() - 1] = end - dir * 30.0
	draw_polyline(line, Color(0, 0, 0, 0.45), 9.0, true)
	draw_polyline(line, ROUTE_COLOR, 5.0, true)
	for i in range(1, pts.size() - 1):
		draw_circle(pts[i], 6.0, Color(0, 0, 0, 0.5))
		draw_circle(pts[i], 4.5, ROUTE_COLOR)
	var tip := end - dir * 18.0
	var side := Vector2(-dir.y, dir.x)
	draw_colored_polygon(PackedVector2Array([tip, tip - dir * 18 + side * 10, tip - dir * 18 - side * 10]),
		ROUTE_COLOR)
	_draw_ellipse(end, Vector2(RING_RADIUS, RING_RADIUS * 0.9), ROUTE_COLOR, 4.0)


func _draw_highlight(h: Vector2i, fill: Color, edge: Color) -> void:
	var pts := Hex.corners(Hex.to_pixel(h), Hex.SIZE - 2)
	draw_colored_polygon(pts, fill)
	pts.append(pts[0])
	draw_polyline(pts, edge, 2.0)


const SPRITE_SCALE := 0.3
const RING_RADIUS := 34.0  # the hull (6.9 x 3.5 m, corners included) just fits inside


## EW-style figure: the hull stands on the hex centre inside a team-coloured ring
## drawn at the same camera angle as the sprite. The cast shadow (sun from the
## north-east, 75 degrees high) is part of the sprite itself.
func _draw_unit_sprite(u: Unit, spr: Dictionary) -> void:
	var c := u.draw_pos
	var squash: float = spr["squash"]
	var ring := Vector2(RING_RADIUS, RING_RADIUS * squash)
	_draw_ellipse(c, ring, SIDE_COLORS[u.side], 3.0)
	var hull_px: float = spr["hull_px"] * SPRITE_SCALE
	if spr["layers"]:
		var hull_frames: Array[Texture2D] = spr["hull"]
		var steps: Array = spr["turret"]
		var turret_frames: Array[Texture2D] = steps[_recoil_step(u, steps.size())]
		var n := hull_frames.size()
		var hi := posmod(roundi(u.hull_angle * n / 360.0), n)
		var ti := posmod(roundi(u.turret_angle * n / 360.0), n)
		# Shift forward along the heading so the hull, not hull + gun, is centred.
		var a := deg_to_rad(360.0 * hi / n)
		var hull_pos := c + Vector2(cos(a), -sin(a) * squash) * hull_px
		draw_set_transform(hull_pos, 0.0, Vector2.ONE * SPRITE_SCALE)
		draw_texture(hull_frames[hi], -spr["hull_anchor"])
		var offsets: Array[Vector2] = spr["turret_offsets"]
		draw_set_transform(hull_pos + offsets[hi] * SPRITE_SCALE, 0.0, Vector2.ONE * SPRITE_SCALE)
		draw_texture(turret_frames[ti], -spr["turret_anchor"])
	else:
		var frames: Array[Texture2D] = spr["frames"]
		var a := deg_to_rad(60.0 * u.facing)
		draw_set_transform(c + Vector2(cos(a), -sin(a) * squash) * hull_px, 0.0, Vector2.ONE * SPRITE_SCALE)
		draw_texture(frames[u.facing % frames.size()], -spr["anchor"])
	draw_set_transform(Vector2.ZERO)
	_draw_hp_bar(u, c + Vector2(-24, ring.y + 4))


## Filled when width < 0, otherwise an outline.
func _draw_ellipse(c: Vector2, r: Vector2, color: Color, width := -1.0) -> void:
	var pts := PackedVector2Array()
	for k in 33:
		var a := TAU * k / 32.0
		pts.append(c + Vector2(cos(a) * r.x, sin(a) * r.y))
	if width < 0.0:
		draw_colored_polygon(pts, color)
	else:
		draw_polyline(pts, color, width, true)


func _draw_hp_bar(u: Unit, top_left: Vector2) -> void:
	var frac := float(u.hp) / u.max_hp()
	var bar := Rect2(top_left, Vector2(48, 6))
	draw_rect(bar, Color(0, 0, 0, 0.7))
	var hp_col := Color(0.3, 0.9, 0.3) if frac > 0.6 else (Color(0.95, 0.8, 0.2) if frac > 0.3 else Color(0.95, 0.25, 0.2))
	draw_rect(Rect2(bar.position, Vector2(48 * frac, 6)), hp_col)


## Units use simplified NATO map symbols.
func _draw_unit(u: Unit) -> void:
	if sprites.has(u.type):
		_draw_unit_sprite(u, sprites[u.type])
		return
	var c := u.draw_pos + Vector2(0, -4)
	var col := SIDE_COLORS[u.side]
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
	_draw_hp_bar(u, c + Vector2(-24, 19))
