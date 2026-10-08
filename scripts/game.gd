class_name Battle
extends Node2D
## The campaign: one continuous global map (canon §1.2), units, rules, input
## and rendering. Created by App; `saved_state` continues a saved campaign.

signal finished(result: Dictionary)  # {won: bool, reason: String, turn: int}
signal leave_requested
signal new_campaign_requested

const MAP_PATH := "res://assets/maps/global.json"
const SAVE_PATH := "user://hexfront_campaign.json"
const AUTOTEST_TURN_LIMIT := 160

const SIDE_COLORS: Array[Color] = [Color(0.18, 0.44, 0.84), Color(0.84, 0.23, 0.18)]
const NEUTRAL_COLOR := Color(0.75, 0.75, 0.75)
const SIDE_NAMES: Array[String] = ["Сині", "Червоні"]
const AI_DELAY := 0.35
const MOVE_STEP_TIME := 0.32  # seconds per hex
const HULL_TURN_SPEED := 160.0  # degrees per second
const TURRET_TURN_SPEED := 120.0
const SCAN_SPEED := 15.0  # idle turret scan, degrees per second
const SCAN_RANGE := 45.0  # idle scan swings at most this far either side
const SCAN_PAUSE := Vector2(1.5, 4.5)  # seconds between scan moves
const RECOIL_KICK := 0.04  # gun slams back (seconds at full recoil)
const RECOIL_RETURN := 0.5  # then runs out again
const SHOT_DELAY := 0.3  # pause between the shots of one exchange
const MIN_ZOOM := 0.3
const MAX_ZOOM := 2.5
const STRIKE_DAMAGE := 40
const STRIKE_SPLASH := 15
const REPAIR_CARD := 40

var mission: Dictionary = {}  # the global map file (map rows, names, start units, money)
var autotest := false
var saved_state: Dictionary = {}  # set by App to continue a campaign
var city_names: Dictionary = {}  # Vector2i -> name
var medals := 0  # player's medals for commanders, earned in this campaign
var terrain: Dictionary = {}  # Vector2i -> Rules.Terrain
var ground_height: Dictionary = {}  # kept for the sprite lift code; campaign maps are flat
var city_owner: Dictionary = {}  # Vector2i -> side, -1 = neutral
var hq: Array = [[], []]  # per side: Array of HQ hexes
var airfields: Dictionary = {}  # Vector2i -> true
var units: Array[Unit] = []
var money: Array[int] = [0, 0]
var cp: Array[int] = [Rules.CP_START, Rules.CP_START]
var turn := 1
var current_side := 0
var human_sides: Array[bool] = [true, false]
var winner := -1  # -1 playing, 0/1 side, 2 draw (autotest)
var busy := false
var rng := RandomNumberGenerator.new()
var used_commanders: Dictionary = {}  # commander id -> true once assigned this battle

var selected: Unit = null
var reachable: Dictionary = {}  # Vector2i -> movement cost
var attackable: Dictionary = {}  # Vector2i -> true
var repairable: Dictionary = {}  # Vector2i -> true (logistics)
var card_targets: Dictionary = {}  # Vector2i -> true while a card is being aimed
var card := ""  # card being aimed
var build_city: Variant = null  # Vector2i of the city whose build menu is open
var route_parents: Dictionary = {}
var route: Array[Vector2i] = []
var _moving := 0
var effects: Array[Dictionary] = []
var blasts: Array[Dictionary] = []  # {pos, t} explosion rings
var _stars_seen: Dictionary = {}  # Unit -> stars already announced
var _occ: Dictionary = {}  # Vector2i -> Unit (see unit_at)
var _occ_dirty := true
var _built_here: Dictionary = {}  # cities that already produced a unit this turn

var _touches: Dictionary = {}
var _drag_start := Vector2.ZERO
var _dragging := false
var _pinch_dist := 0.0
var game_id := 0

var hud: Hud
var map_view: MapView
var camera: Camera2D
var sprites: Dictionary = {}
var fx_rng := RandomNumberGenerator.new()
var ai := EnemyAI.new()


func _ready() -> void:
	fx_rng.randomize()
	mission = JSON.parse_string(FileAccess.get_file_as_string(MAP_PATH))
	if autotest:
		human_sides = [false, false]
	camera = Camera2D.new()
	add_child(camera)
	_load_sprites()
	map_view = MapView.new(self)
	add_child(map_view)
	hud = Hud.new()
	add_child(hud)
	hud.end_turn_pressed.connect(_on_end_turn_pressed)
	hud.choice.connect(_on_choice)
	hud.move_confirmed.connect(_confirm_move)
	hud.move_cancelled.connect(_clear_route)
	hud.cards_pressed.connect(_open_cards)
	hud.menu_pressed.connect(_open_pause)
	hud.hq_pressed.connect(_open_hq)
	start()


# --- Setup ------------------------------------------------------------------

func _load_sprites() -> void:
	for type in Rules.SPRITES:
		var base: String = "res://assets/units/" + Rules.SPRITES[type]
		if not FileAccess.file_exists(base + ".json"):
			continue
		var meta = JSON.parse_string(FileAccess.get_file_as_string(base + ".json"))
		if not meta is Dictionary:
			continue
		var spr := {
			"hull_px": float(meta.get("hull_offset_m", 0.0)) * float(meta["px_per_m"]),
			"squash": sin(deg_to_rad(float(meta.get("elevation", 90.0)))),
			"layers": meta.get("layers", false),
		}
		if spr["layers"]:
			var hull: Array[Texture2D] = []
			var turret: Array = []
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


func start() -> void:
	game_id += 1
	rng.randomize()
	terrain.clear()
	city_owner.clear()
	hq = [[], []]
	airfields.clear()
	units.clear()
	_occ_dirty = true
	effects.clear()
	blasts.clear()
	_stars_seen.clear()
	used_commanders.clear()
	var m: Array = mission["money"]
	money = [int(m[0]), int(m[1])]
	cp = [Rules.CP_START, Rules.CP_START]
	turn = 1
	current_side = 0
	winner = -1
	busy = false
	_deselect()
	_load_map()
	if saved_state.is_empty():
		Profile.new_campaign()
		medals = 0
	else:
		_restore(saved_state)
	map_view.rebuild(7, not autotest)
	_focus_camera()
	hud.hide_overlay()
	if not autotest:
		hud.show_banner("Хід %d\n%s" % [turn, objective_text()])
	if saved_state.is_empty():
		_start_turn()
	else:
		_update_status()
		queue_redraw()
		if not human_sides[current_side]:
			busy = true
			_run_ai.call_deferred()


func _load_map() -> void:
	var rows: Array = mission["map"]
	var land := {".": Rules.Terrain.PLAIN, "f": Rules.Terrain.FOREST, "h": Rules.Terrain.HILLS,
		"m": Rules.Terrain.MOUNTAIN, "w": Rules.Terrain.WATER}
	var owners := {"c": -1, "a": -1, "b": 0, "B": 0, "p": 0, "P": 0, "r": 1, "R": 1, "q": 1, "Q": 1}
	for row in rows.size():
		var line: String = rows[row]
		for col in line.length():
			var h := Hex.offset_to_axial(col, row)
			var ch := line[col]
			if land.has(ch):
				terrain[h] = land[ch]
				continue
			terrain[h] = Rules.Terrain.CITY
			city_owner[h] = owners.get(ch, -1)
			if ch in ["B", "P"]:
				hq[0].append(h)
			elif ch in ["R", "Q"]:
				hq[1].append(h)
			if ch in ["a", "p", "q", "P", "Q"]:
				airfields[h] = true
	for key in mission["names"]:
		var p: PackedStringArray = key.split(",")
		city_names[Hex.offset_to_axial(int(p[0]), int(p[1]))] = mission["names"][key]
	if saved_state.is_empty():
		for d in mission["units"]:
			var u := Unit.new(d["t"], int(d["s"]), Hex.offset_to_axial(int(d["at"][0]), int(d["at"][1])))
			u.guard = d.get("g", false)
			units.append(u)


func objective_text() -> String:
	var left := 0
	for h in hq[1]:
		if city_owner[h] != 0:
			left += 1
	return "Мета: захопити ключові точки противника (залишилось %d з %d)" % [left, hq[1].size()]


## Opens on the player's capital at a readable zoom.
func _focus_camera() -> void:
	camera.zoom = Vector2(0.75, 0.75)
	var sum := Vector2.ZERO
	var mine := units_of(0)
	for u in mine:
		sum += Hex.to_pixel(u.pos)
	camera.position = sum / maxf(1.0, mine.size()) + Vector2(220, 0)
	_pan(Vector2.ZERO)


func _map_rect() -> Rect2:
	var r := Rect2(Hex.to_pixel(Hex.offset_to_axial(0, 0)), Vector2.ZERO)
	for h in terrain:
		r = r.expand(Hex.to_pixel(h))
	return r.grow(Hex.SIZE)


func ground_lift(_p: Vector2) -> float:
	return 0.0


func is_hq(h: Vector2i) -> bool:
	return h in hq[0] or h in hq[1]


# --- Queries ----------------------------------------------------------------

## Units by hex, rebuilt lazily after anything moves, appears or dies.
func unit_at(h: Vector2i) -> Unit:
	if _occ_dirty:
		_occ.clear()
		for u in units:
			_occ[u.pos] = u
		_occ_dirty = false
	return _occ.get(h)


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


func city_income(c: Vector2i) -> int:
	if is_hq(c):
		return Rules.INCOME_HQ
	return Rules.INCOME_AIRFIELD if airfields.has(c) else Rules.INCOME_CITY


func income(side: int) -> int:
	var total := Rules.BASE_INCOME
	for c in cities_of(side):
		total += city_income(c)
	var over := army_points(side) - army_limit(side)
	if over > 0:
		total = maxi(Rules.BASE_INCOME, roundi(total * (1.0 - Rules.OVER_LIMIT_PENALTY * over)))
	return total


func army_points(side: int) -> int:
	var n := 0
	for u in units:
		if u.side == side:
			n += int(u.data().get("points", 1))
	return n


func army_limit(side: int) -> int:
	return Rules.ARMY_LIMIT_BASE + Rules.ARMY_LIMIT_PER_CITY * cities_of(side).size()


func move_points(u: Unit) -> int:
	var mp: int = u.data()["move"]
	if u.has_perk("move"):
		mp += 1
	if u.has_perk("move2"):
		mp += 2
	return mp


func max_range(u: Unit) -> int:
	var r: int = u.data()["range"]
	if u.has_perk("range") or (u.has_perk("support") and u.type == "sam"):
		r += 1
	return r


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
func compute_reachable(u: Unit, parents: Dictionary = {}) -> Dictionary:
	var result := {}
	if not u.can_move():
		return result
	var mp := move_points(u)
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


func attack_value(att: Unit, target: Unit) -> int:
	return int(att.data()["atk"][target.target_class()])


func can_attack(att: Unit, target: Unit, from: Vector2i) -> bool:
	if att == target or att.side == target.side or attack_value(att, target) <= 0:
		return false
	var d := Hex.distance(from, target.pos)
	return d >= att.data()["min_range"] and d <= max_range(att)


func targets_from(att: Unit, from: Vector2i) -> Array[Unit]:
	var res: Array[Unit] = []
	for u in units:
		if can_attack(att, u, from):
			res.append(u)
	return res


func repair_targets(u: Unit, from: Vector2i) -> Array[Unit]:
	var res: Array[Unit] = []
	if not u.is_support():
		return res
	for n in Hex.neighbors(from):
		var o := unit_at(n)
		if o and o.side == u.side and o.hp < o.max_hp():
			res.append(o)
	return res


func is_done(u: Unit) -> bool:
	if u.can_move():
		return false
	if not u.can_fire():
		return true
	return targets_from(u, u.pos).is_empty() and repair_targets(u, u.pos).is_empty()


func defense_of(u: Unit) -> float:
	var d: float = u.data()["def"] * (1.0 + Rules.STAR_BONUS * u.stars() + Rules.CMD_DEF_PER_RANK * u.cmd_level())
	if not u.is_flying():
		d += Rules.TERRAIN[terrain[u.pos]]["def"]
		if u.entrenched:
			d += Rules.ENTRENCH_DEF * (2 if u.has_perk("dig") else 1)
	return d


func calc_damage(att: Unit, target: Unit, counter: bool = false) -> int:
	var base := attack_value(att, target)
	if base <= 0:
		return 0
	var strength := base * (0.5 + 0.5 * float(att.hp) / att.max_hp())
	strength *= 1.0 + Rules.STAR_BONUS * att.stars() + Rules.CMD_ATK_PER_RANK * att.cmd_level()
	var dmg := strength * 100.0 / (100.0 + defense_of(target) * 1.3)
	if counter and not att.has_perk("counter"):
		dmg *= Rules.COUNTER_FACTOR
	return maxi(1, roundi(dmg))


## Enemy air defence that will fire at a flying attacker before its strike.
func interceptors(att: Unit) -> Array[Unit]:
	var res: Array[Unit] = []
	if not att.is_flying():
		return res
	for s in units:
		if s.side != att.side and s.data().get("intercept", false) and not s.countered \
				and can_attack(s, att, s.pos):
			res.append(s)
	return res


# --- Actions ----------------------------------------------------------------

func move_unit(u: Unit, to: Vector2i, path: Array[Vector2i] = []) -> void:
	if path.is_empty():
		path = path_to(u, to)
	if path.size() < 2:
		path = [u.pos, to]
	u.pos = to
	_occ_dirty = true
	u.moved = true
	u.entrenched = false
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
		var dir := Hex.DIRS.find(b - a)
		var target := 60.0 * dir
		var dh := wrapf(target - heading, -180.0, 180.0)
		var dt := wrapf(target - aim, -180.0, 180.0) if turret else dh
		var th := absf(dh) / HULL_TURN_SPEED
		var tt := absf(dt) / TURRET_TURN_SPEED if turret else th
		var dur := maxf(th, tt)
		if dur > 0.001 and turret:
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
		busy = _moving > 0 or not human_sides[current_side] or winner >= 0
		if human_sides[current_side] and units.has(u) and not is_done(u):
			selected = u
		_after_action())


func _arrive(u: Unit, to: Vector2i) -> void:
	if city_owner.has(to) and u.data().get("capture", false) and city_owner[to] != u.side:
		city_owner[to] = u.side
		map_view.update_territory()
		var name: String = city_names.get(to, "")
		_add_effect(Hex.to_pixel(to), ("Ключова точка: " if is_hq(to) else "Захоплено: ") + name, Color.GOLD)
		if u.side == 0:
			_award(Rules.MEDALS_KEY_POINT if is_hq(to) else Rules.MEDALS_CITY, Hex.to_pixel(to))
	_check_game_over()


## Air defence first, then the strike (with splash), then return fire.
func attack(att: Unit, target: Unit) -> void:
	att.attacked = true
	if not att.data().get("move_after_attack", false):
		att.moved = true
	att.entrenched = false
	var sams := interceptors(att)
	if autotest:
		_aim_now(att, target.draw_pos)
		_resolve_exchange(att, target, sams)
		_after_action()
		return
	_moving += 1
	busy = true
	_deselect()
	var tw := create_tween().set_parallel(true)
	tw.tween_interval(0.05)
	_aim(tw, att, target.draw_pos)
	for s in sams:
		tw.chain().tween_callback(func() -> void:
			if units.has(s) and units.has(att):
				s.countered = true
				_add_effect(Hex.to_pixel(s.pos) + Vector2(0, -26), "Перехоплення!", Color(0.6, 0.9, 1.0))
				_shot(s, att, 1.0, false))
		tw.chain().tween_interval(SHOT_DELAY)
	tw.chain().tween_callback(func() -> void:
		att.turret_rest = att.turret_angle
		att.scan_target = att.turret_rest
		if units.has(att) and units.has(target):
			att.recoil_time = 0.0
			_main_strike(att, target))
	tw.chain().tween_interval(SHOT_DELAY)
	tw.chain().tween_callback(func() -> void:
		if units.has(att) and units.has(target):
			_return_fire(target, att))
	tw.chain().tween_interval(RECOIL_KICK + RECOIL_RETURN)
	tw.chain().tween_callback(func() -> void:
		att.animating = false
		_moving -= 1
		busy = _moving > 0 or not human_sides[current_side] or winner >= 0
		_check_game_over()
		if human_sides[current_side] and units.has(att) and not is_done(att):
			selected = att
		_after_action())


func _resolve_exchange(att: Unit, target: Unit, sams: Array[Unit]) -> void:
	for s in sams:
		if units.has(att):
			s.countered = true
			_shot(s, att, 1.0, false)
	if units.has(att) and units.has(target):
		_main_strike(att, target)
	if units.has(att) and units.has(target):
		_return_fire(target, att)
	_check_game_over()


func _main_strike(att: Unit, target: Unit) -> void:
	var center := target.pos
	_shot(att, target, 1.0, false)
	var splash: float = att.data().get("splash", 0.0)
	if splash > 0.0:
		_add_blast(Hex.to_pixel(center))
		for n in Hex.neighbors(center):
			var o := unit_at(n)
			if o and o != att and attack_value(att, o) > 0:
				_shot(att, o, splash, false)


func _return_fire(target: Unit, att: Unit) -> void:
	if target.data().get("counter", false) and not target.countered and can_attack(target, att, target.pos):
		target.countered = true
		_shot(target, att, 1.0, true)


## One shot: damage with ±10% spread; experience = damage actually dealt.
func _shot(shooter: Unit, target: Unit, factor: float, counter: bool) -> void:
	var dmg := maxi(1, roundi(calc_damage(shooter, target, counter) * factor * rng.randf_range(0.9, 1.1)))
	shooter.xp += mini(dmg, target.hp)
	_damage(target, dmg)
	_announce_star(shooter)


func _announce_star(u: Unit) -> void:
	var s := u.stars()
	if s > int(_stars_seen.get(u, 0)) and units.has(u):
		_stars_seen[u] = s
		_add_effect(Hex.to_pixel(u.pos) + Vector2(0, -40), "Ветеран %s" % "★".repeat(s), Color(1, 0.9, 0.4))


func repair(u: Unit, target: Unit) -> void:
	var amount: int = u.data()["repair"] + (20 if u.has_perk("support") else 0)
	_heal(target, amount)
	u.attacked = true
	u.moved = true
	_after_action()


func _award(n: int, at: Vector2) -> void:
	medals += n
	_add_effect(at + Vector2(0, 44), "+%d мед." % n, Color(1, 0.85, 0.4))


func _heal(u: Unit, amount: int) -> void:
	var before := u.hp
	u.hp = mini(u.max_hp(), u.hp + amount)
	if u.hp > before:
		_add_effect(Hex.to_pixel(u.pos), "+%d" % (u.hp - before), Color(0.4, 1.0, 0.5))


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


static func _bearing(from: Vector2, to: Vector2) -> float:
	var d := to - from
	return rad_to_deg(atan2(-d.y, d.x))


func _recoil_step(u: Unit, steps: int) -> int:
	if u.recoil_time < 0.0 or steps < 2:
		return 0
	if u.recoil_time < RECOIL_KICK:
		return steps - 1
	var k := 1.0 - (u.recoil_time - RECOIL_KICK) / RECOIL_RETURN
	return clampi(roundi(k * (steps - 1)), 0, steps - 1)


func can_build_at(city: Vector2i, type: String, side: int) -> bool:
	if city_owner.get(city, -1) != side or unit_at(city) or _built_here.has(city):
		return false
	if Rules.UNITS[type].get("airfield", false) and not airfields.has(city):
		return false
	return money[side] >= Rules.UNITS[type]["cost"]


func build(city: Vector2i, type: String) -> bool:
	var side: int = city_owner.get(city, -1)
	if side != current_side or not can_build_at(city, type, side):
		return false
	money[side] -= Rules.UNITS[type]["cost"]
	_spawn(type, side, city)
	_built_here[city] = true
	_after_action()
	return true


func _spawn(type: String, side: int, h: Vector2i) -> Unit:
	var u := Unit.new(type, side, h)
	u.moved = true
	u.attacked = true
	units.append(u)
	_occ_dirty = true
	return u


func assign_commander(u: Unit, id: String) -> void:
	if used_commanders.has(id) or u.commander != "":
		return
	used_commanders[id] = true
	u.commander = id
	u.cmd_rank = int(Profile.ranks.get(id, 1))
	_add_effect(Hex.to_pixel(u.pos) + Vector2(0, -30), Rules.COMMANDERS[id]["name"], Color(1, 0.9, 0.5))
	_after_action()


func commander_slots_left() -> int:
	return Rules.COMMANDER_SLOTS - used_commanders.size()


## Valid target hexes for a card of the given side.
func card_hexes(id: String, side: int) -> Dictionary:
	var res := {}
	match id:
		"strike":
			for u in units:
				if u.side != side:
					res[u.pos] = true
		"repair":
			for u in units_of(side):
				if u.hp < u.max_hp():
					res[u.pos] = true
		"reserve":
			for c in cities_of(side):
				if unit_at(c) == null:
					res[c] = true
	return res


func use_card(id: String, side: int, h: Vector2i) -> bool:
	var cost: int = Rules.CARDS[id]["cp"]
	if cp[side] < cost or not card_hexes(id, side).has(h):
		return false
	cp[side] -= cost
	match id:
		"strike":
			_add_blast(Hex.to_pixel(h))
			_add_effect(Hex.to_pixel(h) + Vector2(0, -30), "Ракетний удар", Color.ORANGE)
			var center := unit_at(h)
			var hit: Array[Unit] = []
			for n in Hex.neighbors(h):
				var o := unit_at(n)
				if o:
					hit.append(o)
			if center:
				_damage(center, STRIKE_DAMAGE)
			for o in hit:
				if units.has(o):
					_damage(o, STRIKE_SPLASH)
		"repair":
			_heal(unit_at(h), REPAIR_CARD)
		"reserve":
			_spawn("infantry", side, h)
			_add_effect(Hex.to_pixel(h) + Vector2(0, -30), "Резерв прибув", Color(0.6, 1, 0.6))
	_check_game_over()
	_after_action()
	return true


func _damage(u: Unit, dmg: int) -> void:
	u.hp -= maxi(1, dmg)
	_add_effect(Hex.to_pixel(u.pos), "-%d" % dmg, Color(1, 0.35, 0.3))
	if u.hp <= 0:
		units.erase(u)
		_occ_dirty = true
		if u.side == 1:
			_award(Rules.MEDALS_KILL, Hex.to_pixel(u.pos))
		_add_blast(Hex.to_pixel(u.pos))
		_add_effect(Hex.to_pixel(u.pos) + Vector2(0, 22), "Знищено", Color.ORANGE)
		if u == selected:
			_deselect()


func _after_action() -> void:
	_update_status()
	if selected and units.has(selected) and not is_done(selected) and controllable(selected):
		_select(selected)
	elif card == "":
		_deselect()
	queue_redraw()


func controllable(u: Unit) -> bool:
	return u.side == current_side and human_sides[current_side]


# --- Victory ----------------------------------------------------------------

## A side loses when the enemy holds all its key points (canon §23.1) or it has
## neither units nor cities left.
func _check_game_over() -> void:
	if winner >= 0:
		return
	for side in 2:
		var lost: bool = not hq[side].is_empty()
		for h in hq[side]:
			if city_owner[h] == side:
				lost = false
		if lost:
			_finish(1 - side, "Усі ключові точки %s захоплено" % ["Синіх", "Червоних"][side])
			return
		if units_of(side).is_empty() and cities_of(side).is_empty():
			_finish(1 - side, "Армію %s знищено" % ["Синіх", "Червоних"][side])
			return


func _finish(side: int, reason: String) -> void:
	winner = side
	busy = side < 2
	_deselect()
	var result := {"won": side == 0, "reason": reason, "turn": turn}
	if autotest:
		finished.emit(result)
		return
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(SAVE_PATH)
	_show_result.call_deferred(result)


func _show_result(result: Dictionary) -> void:
	var body := "%s\nХід %d · міст під контролем: %d" % [result["reason"], result["turn"], cities_of(0).size()]
	hud.show_overlay("ПЕРЕМОГА" if result["won"] else "ПОРАЗКА", body, [
		{"id": "result_new", "label": "Нова кампанія"},
		{"id": "result_menu", "label": "Головне меню"},
	])
	finished.emit(result)


# --- Turn flow --------------------------------------------------------------

func _start_turn() -> void:
	var side := current_side
	_built_here.clear()
	money[side] += income(side)
	if turn > 1 or side == 1:
		cp[side] = mini(Rules.CP_MAX, cp[side] + Rules.CP_PER_TURN)
	for u in units_of(side):
		u.entrenched = u.data().get("dig", false) and not u.moved and not u.attacked
		u.moved = false
		u.attacked = false
		u.countered = false
		if city_owner.get(u.pos, -1) == side:
			_heal(u, Rules.HEAL_IN_CITY)
		if u.has_perk("regen"):
			_heal(u, 10)
	_update_status()
	queue_redraw()
	if human_sides[side]:
		busy = false
		save_state()
	else:
		busy = true
		_run_ai.call_deferred()


func end_turn() -> void:
	if winner >= 0:
		return
	_deselect()
	if current_side == 1:
		turn += 1
		if autotest and turn % 20 == 0:
			print("[autotest]   turn %d · %d ms · units %d/%d · cities %d/%d" % [turn, Time.get_ticks_msec(),
				units_of(0).size(), units_of(1).size(), cities_of(0).size(), cities_of(1).size()])
		if autotest and turn > AUTOTEST_TURN_LIMIT:
			_finish(2, "ліміт ходів автотесту")
			return
	current_side = 1 - current_side
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
	if hud == null:
		return
	var who := "" if human_sides[current_side] else " · Хід противника…"
	var army := "%d/%d" % [army_points(0), army_limit(0)]
	if army_points(0) > army_limit(0):
		army += "(!)"
	hud.set_status("Хід %d%s · %d $ (+%d) · КП %d · Медалі %d · Армія %s" % [turn, who,
		money[0], income(0), cp[0], medals, army], human_sides[current_side] and not busy and winner < 0)


# --- Player input -----------------------------------------------------------

func _on_end_turn_pressed() -> void:
	if not busy and winner < 0 and human_sides[current_side]:
		end_turn()


func _on_choice(id: String) -> void:
	if id.begins_with("result_") or id.begins_with("pause_"):
		_on_menu_choice(id)
		return
	if busy or winner >= 0 or not human_sides[current_side]:
		return
	var parts := id.split(":")
	match parts[0]:
		"build":
			if build_city != null:
				build(build_city, parts[1])
		"card":
			_aim_card(parts[1])
		"cmd":
			if selected:
				_open_commanders(selected)
		"assign":
			if selected:
				assign_commander(selected, parts[1])
		"hire":
			var cost := Profile.upgrade_cost(parts[1])
			var r := int(Profile.ranks.get(parts[1], 0))
			if medals >= cost and r < Rules.COMMANDER_MAX_RANK:
				medals -= cost
				Profile.ranks[parts[1]] = r + 1
				for u in units:
					if u.commander == parts[1]:
						u.cmd_rank = r + 1
				_update_status()
				_open_hq()
		"cancel":
			_deselect()


func _on_menu_choice(id: String) -> void:
	match id:
		"pause_resume":
			hud.hide_overlay()
		"pause_leave", "result_menu":
			leave_requested.emit()
		"result_new":
			new_campaign_requested.emit()


func _open_pause() -> void:
	if winner >= 0:
		return
	hud.show_overlay("Пауза", "Хід %d\n%s\nКампанія зберігається автоматично на початку кожного вашого ходу." % [
		turn, objective_text()], [
		{"id": "pause_resume", "label": "Продовжити"},
		{"id": "pause_leave", "label": "Головне меню"},
	])


## Headquarters: hire and promote commanders with medals earned in the campaign.
func _open_hq() -> void:
	if busy or winner >= 0 or not human_sides[current_side]:
		return
	_deselect()
	var options := []
	for id in Rules.COMMANDER_ORDER:
		var c: Dictionary = Rules.COMMANDERS[id]
		var r := int(Profile.ranks.get(id, 0))
		var cost := Profile.upgrade_cost(id)
		var label := "%s%s\n%s" % [c["name"], (" ★%d" % r) if r > 0 else "", Rules.BRANCH_NAMES[c["branch"]]]
		if r >= Rules.COMMANDER_MAX_RANK:
			label += " · макс."
		else:
			label += " · %s %d мед." % ["найняти" if r == 0 else "↑", cost]
		if used_commanders.has(id):
			label += " · у строю"
		options.append({"id": "hire:" + id, "label": label,
			"enabled": r < Rules.COMMANDER_MAX_RANK and medals >= cost})
	options.append({"id": "cancel", "label": "Закрити"})
	hud.show_panel("Штаб · медалі: %d · командирів у строю: %d/%d. Медалі дають за захоплені міста й знищені юніти. Кожен ранг: +%d%% атаки, +%d%% захисту своєму роду військ; з 3-го рангу — навичка. Призначення — через вибір юніта." % [
		medals, used_commanders.size(), Rules.COMMANDER_SLOTS,
		roundi(Rules.CMD_ATK_PER_RANK * 100), roundi(Rules.CMD_DEF_PER_RANK * 100)], options)


func _open_cards() -> void:
	if busy or winner >= 0 or not human_sides[current_side]:
		return
	_deselect()
	var options := []
	for id in Rules.CARD_ORDER:
		var c: Dictionary = Rules.CARDS[id]
		options.append({"id": "card:" + id, "label": "%s\n%d КП" % [c["name"], c["cp"]],
			"enabled": cp[0] >= c["cp"] and not card_hexes(id, 0).is_empty()})
	options.append({"id": "cancel", "label": "Закрити"})
	var lines := []
	for id in Rules.CARD_ORDER:
		lines.append("%s — %s" % [Rules.CARDS[id]["name"], Rules.CARDS[id]["text"]])
	hud.show_panel("Оперативні засоби · очки командування: %d (+%d за хід)\n%s" % [
		cp[0], Rules.CP_PER_TURN, "\n".join(lines)], options)


func _aim_card(id: String) -> void:
	_deselect()
	card = id
	card_targets = card_hexes(id, 0)
	hud.show_panel("%s: оберіть ціль на карті" % Rules.CARDS[id]["name"],
		[{"id": "cancel", "label": "Скасувати"}])
	queue_redraw()


func _open_commanders(u: Unit) -> void:
	var options := []
	for id in Profile.unlocked_commanders():
		if used_commanders.has(id):
			continue
		var c: Dictionary = Rules.COMMANDERS[id]
		var fits: bool = c["branch"] == "any" or c["branch"] == u.data()["branch"]
		options.append({"id": "assign:" + id, "label": "%s ★%d\n%s%s" % [c["name"], int(Profile.ranks[id]),
			Rules.BRANCH_NAMES[c["branch"]], "" if fits else " ✗"], "enabled": true})
	options.append({"id": "cancel", "label": "Скасувати"})
	hud.show_panel("Призначити командира до «%s» (залишилось місць: %d). Бонус діє лише для свого роду військ (✗ — без бонусу)." % [
		u.display_name(), commander_slots_left()], options)


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
				_dragging = true
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
	if card != "":
		if card_targets.has(h):
			var id := card
			_deselect()
			use_card(id, 0, h)
		return
	if not terrain.has(h):
		_deselect()
		return
	var u := unit_at(h)
	if selected:
		if attackable.has(h) and u:
			_clear_route()
			attack(selected, u)
			return
		if repairable.has(h) and u:
			repair(selected, u)
			return
		if reachable.has(h):
			if not route.is_empty() and route.back() == h:
				_confirm_move()
			else:
				_plan_route(h)
			return
	if u and controllable(u) and u != selected:
		_select(u)
		return
	_deselect()
	if u:
		hud.show_info(_unit_text(u) + "\n" + _terrain_text(h))
	elif city_owner.get(h, -1) == current_side:
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


func _place_move_confirm() -> void:
	if route.is_empty():
		return
	var below := Hex.to_pixel(route.back()) + Vector2(0, Hex.SIZE * 0.95)
	hud.place_move_confirm(get_canvas_transform() * below)


func _select(u: Unit) -> void:
	_clear_route()
	selected = u
	build_city = null
	card = ""
	card_targets.clear()
	route_parents = {}
	reachable = compute_reachable(u, route_parents)
	attackable.clear()
	repairable.clear()
	if u.can_fire():
		for t in targets_from(u, u.pos):
			attackable[t.pos] = true
		for t in repair_targets(u, u.pos):
			repairable[t.pos] = true
	var options := []
	if u.commander == "" and commander_slots_left() > 0 and _free_commanders() > 0:
		options.append({"id": "cmd", "label": "Командир…"})
	hud.show_panel(_unit_text(u) + "\n" + _terrain_text(u.pos), options)
	queue_redraw()


func _free_commanders() -> int:
	var n := 0
	for id in Profile.unlocked_commanders():
		if not used_commanders.has(id):
			n += 1
	return n


func _deselect() -> void:
	_clear_route()
	selected = null
	build_city = null
	card = ""
	card_targets.clear()
	reachable.clear()
	attackable.clear()
	repairable.clear()
	if hud:
		hud.show_info("")
	queue_redraw()


func _open_build(city: Vector2i) -> void:
	build_city = city
	var options := []
	for t in Rules.BUILD_ORDER:
		var d: Dictionary = Rules.UNITS[t]
		if d.get("airfield", false) and not airfields.has(city):
			continue
		options.append({"id": "build:" + t, "label": "%s\n%d $" % [d["name"], d["cost"]],
			"enabled": can_build_at(city, t, current_side)})
	var over := army_points(current_side) >= army_limit(current_side)
	hud.show_panel("Мобілізація · %s · кошти: %d $ · армія %d/%d%s" % [city_names.get(city, ""), money[current_side],
		army_points(current_side), army_limit(current_side),
		" — понад ліміт дохід зменшується" if over else ""], options)
	queue_redraw()


func _unit_text(u: Unit) -> String:
	var d := u.data()
	var mr := max_range(u)
	var rng_text := str(mr) if d["min_range"] == mr else "%d–%d" % [d["min_range"], mr]
	var atk: Dictionary = d["atk"]
	var parts := []
	for k in ["inf", "light", "heavy", "heli", "air"]:
		if int(atk[k]) > 0:
			parts.append("%s %d" % [Rules.CLASS_NAMES[k], atk[k]])
	var line1 := "%s [%s] · HP %d/%d" % [d["name"], SIDE_NAMES[u.side], u.hp, u.max_hp()]
	if u.stars() > 0:
		line1 += " · " + "★".repeat(u.stars())
	if u.commander != "":
		line1 += " · %s (ранг %d)" % [Rules.COMMANDERS[u.commander]["name"], u.cmd_rank]
	if u.entrenched:
		line1 += " · окопано"
	var line2 := "Атака: %s · Захист %d · Рух %d · Дальність %s" % [
		", ".join(parts) if not parts.is_empty() else "—", d["def"], move_points(u), rng_text]
	if u.is_support():
		line2 = "Ремонт сусіднього юніта +%d HP · Захист %d · Рух %d" % [d["repair"], d["def"], move_points(u)]
	return line1 + "\n" + line2


func _terrain_text(h: Vector2i) -> String:
	var t: Dictionary = Rules.TERRAIN[terrain[h]]
	var s := "Місцевість: %s (захист +%d)" % [t["name"], t["def"]]
	if city_owner.has(h):
		var o: int = city_owner[h]
		var kind := "Ключова точка" if is_hq(h) else ("Аеродром" if airfields.has(h) else "Місто")
		s += " · %s «%s»: %s, дохід %d $" % [kind, city_names.get(h, "?"), SIDE_NAMES[o] if o >= 0 else "нейтральне", city_income(h)]
	return s


# --- Rendering --------------------------------------------------------------

func _add_effect(p: Vector2, text: String, color: Color) -> void:
	if not autotest:
		effects.append({"pos": p, "text": text, "color": color, "t": 0.0})


func _add_blast(p: Vector2) -> void:
	if not autotest:
		blasts.append({"pos": p, "t": 0.0})


func _process(delta: float) -> void:
	_place_move_confirm()
	if autotest:
		return
	var scanned := _scan_turrets(delta)
	var recoiling := _advance_recoil(delta)
	if scanned or recoiling:
		queue_redraw()
	if effects.is_empty() and blasts.is_empty():
		return
	for e in effects:
		e["t"] += delta
	effects = effects.filter(func(e: Dictionary) -> bool: return e["t"] < 1.4)
	for b in blasts:
		b["t"] += delta
	blasts = blasts.filter(func(b: Dictionary) -> bool: return b["t"] < 0.6)
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
	for h in repairable:
		_draw_highlight(h, Color(0.2, 1, 0.4, 0.3), Color(0.4, 1, 0.5, 0.9))
	for h in card_targets:
		_draw_highlight(h, Color(1, 0.6, 0.1, 0.3), Color(1, 0.7, 0.2, 0.95))
	var ring: Variant = selected.pos if selected else build_city
	if ring != null:
		var pts := Hex.corners(Hex.to_pixel(ring), Hex.SIZE - 2)
		pts.append(pts[0])
		draw_polyline(pts, Color.YELLOW, 4.0)
	_draw_route()
	var order := units.duplicate()
	order.sort_custom(func(a: Unit, b: Unit) -> bool: return a.draw_pos.y < b.draw_pos.y)
	for u in order:
		_draw_unit(u)
	for b in blasts:
		var k: float = b["t"] / 0.6
		draw_circle(b["pos"], 10 + 40 * k, Color(1, 0.6, 0.15, 0.55 * (1.0 - k)))
		draw_arc(b["pos"], 14 + 50 * k, 0, TAU, 24, Color(1, 0.9, 0.5, 1.0 - k), 3.0)
	var font := UiKit.bold()
	for e in effects:
		var t: float = e["t"]
		var c: Color = e["color"]
		c.a = clampf(1.4 - t, 0.0, 1.0)
		var p: Vector2 = e["pos"] + Vector2(-110, -30 - 40 * t)
		draw_string_outline(font, p, e["text"], HORIZONTAL_ALIGNMENT_CENTER, 220, 24, 6, Color(0, 0, 0, c.a))
		draw_string(font, p, e["text"], HORIZONTAL_ALIGNMENT_CENTER, 220, 24, c)


const ROUTE_COLOR := Color(1.0, 0.84, 0.25)


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
const RING_RADIUS := 34.0


func _draw_unit_sprite(u: Unit, spr: Dictionary, tint: Color) -> void:
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
		var a := deg_to_rad(360.0 * hi / n)
		var hull_pos := c + Vector2(cos(a), -sin(a) * squash) * hull_px
		draw_set_transform(hull_pos, 0.0, Vector2.ONE * SPRITE_SCALE)
		draw_texture(hull_frames[hi], -spr["hull_anchor"], tint)
		var offsets: Array[Vector2] = spr["turret_offsets"]
		draw_set_transform(hull_pos + offsets[hi] * SPRITE_SCALE, 0.0, Vector2.ONE * SPRITE_SCALE)
		draw_texture(turret_frames[ti], -spr["turret_anchor"], tint)
	else:
		var frames: Array[Texture2D] = spr["frames"]
		var a := deg_to_rad(60.0 * u.facing)
		draw_set_transform(c + Vector2(cos(a), -sin(a) * squash) * hull_px, 0.0, Vector2.ONE * SPRITE_SCALE)
		draw_texture(frames[u.facing % frames.size()], -spr["anchor"], tint)
	draw_set_transform(Vector2.ZERO)
	_draw_badges(u, c + Vector2(-24, ring.y + 4))


func _draw_ellipse(c: Vector2, r: Vector2, color: Color, width := -1.0) -> void:
	var pts := PackedVector2Array()
	for k in 33:
		var a := TAU * k / 32.0
		pts.append(c + Vector2(cos(a) * r.x, sin(a) * r.y))
	if width < 0.0:
		draw_colored_polygon(pts, color)
	else:
		draw_polyline(pts, color, width, true)


## HP bar, veteran stars, commander chevron, entrenchment.
func _draw_badges(u: Unit, top_left: Vector2) -> void:
	var frac := float(u.hp) / u.max_hp()
	var bar := Rect2(top_left, Vector2(48, 6))
	draw_rect(bar, Color(0, 0, 0, 0.7))
	var hp_col := Color(0.3, 0.9, 0.3) if frac > 0.6 else (Color(0.95, 0.8, 0.2) if frac > 0.3 else Color(0.95, 0.25, 0.2))
	draw_rect(Rect2(bar.position, Vector2(48 * frac, 6)), hp_col)
	for i in u.stars():
		_draw_star(top_left + Vector2(6 + 12 * i, 14), 6.0, Color(1, 0.85, 0.3))
	if u.commander != "":
		var p := top_left + Vector2(52, -38)
		draw_colored_polygon(PackedVector2Array([p, p + Vector2(8, 6), p + Vector2(16, 0), p + Vector2(16, 6),
			p + Vector2(8, 12), p + Vector2(0, 6)]), Color(1, 0.85, 0.3))
	if u.entrenched:
		var p := top_left + Vector2(24, -2)
		for k in 3:
			draw_circle(p + Vector2(-14 + 14 * k, 0), 6, Color(0.66, 0.58, 0.40))
			draw_arc(p + Vector2(-14 + 14 * k, 0), 6, PI, TAU, 8, Color(0.3, 0.26, 0.18), 1.5)


func _draw_star(c: Vector2, r: float, color: Color) -> void:
	var pts := PackedVector2Array()
	for i in 10:
		var a := -PI / 2 + i * PI / 5
		pts.append(c + Vector2(cos(a), sin(a)) * (r if i % 2 == 0 else r * 0.45))
	draw_colored_polygon(pts, color)
	pts.append(pts[0])
	draw_polyline(pts, Color(0, 0, 0, 0.6), 1.0)


## Units are drawn as NATO-style map symbols (the tank uses its rendered sprite).
func _draw_unit(u: Unit) -> void:
	var done := u.side == current_side and human_sides[u.side] and is_done(u)
	var tint := Color(0.6, 0.6, 0.6) if done else Color.WHITE
	if sprites.has(u.type):
		_draw_unit_sprite(u, sprites[u.type], tint)
		return
	var c := u.draw_pos + Vector2(0, -4)
	var col := SIDE_COLORS[u.side] * tint
	col.a = 1.0
	if u.is_flying():
		draw_circle(u.draw_pos + Vector2(6, 18), 18, Color(0, 0, 0, 0.25))  # shadow below the aircraft
		c += Vector2(0, -10)
	var rect := Rect2(c - Vector2(24, 16), Vector2(48, 32))
	draw_rect(rect, col)
	draw_rect(rect, Color.WHITE, false, 2.0)
	var w := Color.WHITE
	var i := rect.grow(-4)
	match u.type:
		"infantry":
			draw_line(i.position, i.end, w, 2.0)
			draw_line(Vector2(i.position.x, i.end.y), Vector2(i.end.x, i.position.y), w, 2.0)
		"recon":
			draw_line(Vector2(i.position.x, i.end.y), Vector2(i.end.x, i.position.y), w, 2.0)
			_draw_ellipse(c, Vector2(9, 5), w, 2.0)
		"ifv":
			_draw_ellipse(c, Vector2(15, 8), w, 2.0)
			draw_line(i.position, i.end, w, 2.0)
			draw_line(Vector2(i.position.x, i.end.y), Vector2(i.end.x, i.position.y), w, 2.0)
		"tank":
			_draw_ellipse(c, Vector2(15, 8), w, 2.0)
		"artillery":
			draw_circle(c, 5, w)
			_draw_ellipse(c, Vector2(15, 8), w, 2.0)
		"mlrs":
			draw_circle(c + Vector2(-7, 0), 4, w)
			draw_circle(c + Vector2(7, 0), 4, w)
			draw_line(c + Vector2(-14, -9), c + Vector2(14, -9), w, 2.0)
		"sam":
			draw_arc(c + Vector2(0, 12), 15, PI, TAU, 12, w, 2.0)
			draw_line(c + Vector2(0, -4), c + Vector2(0, -12), w, 2.0)
		"logistics":
			draw_line(Vector2(i.position.x, c.y), Vector2(i.end.x, c.y), w, 3.0)
			draw_circle(c + Vector2(-9, 7), 3, w)
			draw_circle(c + Vector2(9, 7), 3, w)
		"heli":
			draw_line(c + Vector2(-16, -9), c + Vector2(16, 9), w, 2.0)
			draw_line(c + Vector2(-16, 9), c + Vector2(16, -9), w, 2.0)
			draw_circle(c, 4, w)
		"jet":
			draw_colored_polygon(PackedVector2Array([c + Vector2(0, -11), c + Vector2(15, 7), c + Vector2(0, 2),
				c + Vector2(-15, 7)]), w)
	_draw_badges(u, c + Vector2(-24, 19))


# --- Save / load --------------------------------------------------------------

## Autosave (canon §23.3): the whole campaign state as JSON.
func save_state() -> void:
	if autotest:
		return
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(to_dict()))


func to_dict() -> Dictionary:
	var owners := []
	for c in city_owner:
		owners.append([c.x, c.y, city_owner[c]])
	var list := []
	for u in units:
		list.append({"t": u.type, "s": u.side, "q": u.pos.x, "r": u.pos.y, "hp": u.hp, "xp": u.xp,
			"cmd": u.commander, "rank": u.cmd_rank, "dig": u.entrenched, "mv": u.moved, "at": u.attacked,
			"g": u.guard, "f": u.facing})
	return {"version": 1, "turn": turn, "side": current_side, "money": money, "cp": cp, "medals": medals,
		"owners": owners, "units": list, "ranks": Profile.ranks, "used": used_commanders.keys()}


func _restore(d: Dictionary) -> void:
	turn = int(d["turn"])
	current_side = int(d.get("side", 0))
	money = [int(d["money"][0]), int(d["money"][1])]
	cp = [int(d["cp"][0]), int(d["cp"][1])]
	medals = int(d["medals"])
	for o in d["owners"]:
		city_owner[Vector2i(int(o[0]), int(o[1]))] = int(o[2])
	units.clear()
	for e in d["units"]:
		var u := Unit.new(e["t"], int(e["s"]), Vector2i(int(e["q"]), int(e["r"])))
		u.hp = int(e["hp"])
		u.xp = int(e["xp"])
		u.commander = e["cmd"]
		u.cmd_rank = int(e["rank"])
		u.entrenched = e["dig"]
		u.moved = e["mv"]
		u.attacked = e["at"]
		u.guard = e["g"]
		u.set_facing(int(e["f"]))
		units.append(u)
		_stars_seen[u] = u.stars()
	_occ_dirty = true
	Profile.ranks = {}
	for k in d["ranks"]:
		Profile.ranks[k] = int(d["ranks"][k])
	for id in d["used"]:
		used_commanders[id] = true


static func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


static func read_save() -> Dictionary:
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH)) if has_save() else null
	return d if d is Dictionary and int(d.get("version", 0)) == 1 else {}
