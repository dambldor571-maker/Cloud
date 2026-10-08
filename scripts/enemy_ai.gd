class_name EnemyAI
extends RefCounted
## Greedy AI: uses operational means, then ranged units fire, others advance on the
## best-scored hex and attack, logistics repairs; money is spent in free cities.

const ORDER := {
	"artillery": 0, "mlrs": 1, "sam": 2, "jet": 3, "heli": 4, "tank": 5, "ifv": 6,
	"recon": 7, "infantry": 8, "logistics": 9,
}
const GUARD_RADIUS := 4  # a guard leaves its post when an enemy comes this close


func take_turn(g: Node) -> void:
	var side: int = g.current_side
	var id: int = g.game_id
	_use_cards(g, side)
	if g.winner >= 0 or g.game_id != id:
		return
	await g.ai_pause()
	var mine: Array[Unit] = g.units_of(side)
	mine.sort_custom(func(a: Unit, b: Unit) -> bool: return ORDER[a.type] < ORDER[b.type])
	for u in mine:
		if g.winner >= 0 or g.game_id != id:
			return
		if not g.units.has(u):
			continue
		await _act(g, u)
	if g.winner < 0 and g.game_id == id:
		_build(g, side)


func _act(g: Node, u: Unit) -> void:
	var id: int = g.game_id
	if u.is_support():
		await _act_support(g, u)
		return
	var target := _best_target(g, u, u.pos)
	var ranged: bool = u.data()["min_range"] > 1
	if target and (ranged or not u.can_move() or _stay_and_fire(g, u)):
		g.attack(u, target)
		await g.ai_pause()
		if not g.units.has(u) or not u.can_move():
			return
	if u.guard and _nearest_enemy(g, u) > GUARD_RADIUS:
		return
	var best_pos: Vector2i = u.pos
	var best_score := _score_tile(g, u, u.pos)
	var reach: Dictionary = g.compute_reachable(u)
	for h in reach:
		var s := _score_tile(g, u, h)
		if s > best_score:
			best_score = s
			best_pos = h
	if best_pos != u.pos and u.can_move():
		g.move_unit(u, best_pos)
		await g.ai_pause()
		if g.winner >= 0 or g.game_id != id or not g.units.has(u):
			return
	if u.can_fire():
		target = _best_target(g, u, u.pos)
		if target:
			g.attack(u, target)
			await g.ai_pause()


## Units on a city or in good cover keep their spot when they can already shoot.
func _stay_and_fire(g: Node, u: Unit) -> bool:
	return g.city_owner.has(u.pos) or u.entrenched or Rules.TERRAIN[g.terrain[u.pos]]["def"] >= 20


func _act_support(g: Node, u: Unit) -> void:
	var t := _most_wounded(g.repair_targets(u, u.pos))
	if t and u.can_fire():
		g.repair(u, t)
		await g.ai_pause()
		return
	if not u.can_move():
		return
	var best_pos: Vector2i = u.pos
	var best_score := -INF
	var reach: Dictionary = g.compute_reachable(u)
	reach[u.pos] = 0
	for h in reach:
		var s := 0.0
		for n in Hex.neighbors(h):
			var o: Unit = g.unit_at(n)
			if o and o != u and o.side == u.side:
				s += float(o.max_hp() - o.hp)
		if g.in_enemy_zoc(h, u.side):
			s -= 60.0
		s -= _dist_to_friends(g, u, h) * 3.0
		if s > best_score:
			best_score = s
			best_pos = h
	if best_pos != u.pos:
		g.move_unit(u, best_pos)
		await g.ai_pause()
	if g.units.has(u) and u.can_fire():
		t = _most_wounded(g.repair_targets(u, u.pos))
		if t:
			g.repair(u, t)
			await g.ai_pause()


func _most_wounded(list: Array[Unit]) -> Unit:
	var best: Unit = null
	for o in list:
		if best == null or o.max_hp() - o.hp > best.max_hp() - best.hp:
			best = o
	return best


func _dist_to_friends(g: Node, u: Unit, h: Vector2i) -> float:
	var best := 99.0
	for o in g.units_of(u.side):
		if o != u and not o.is_support():
			best = minf(best, Hex.distance(h, o.pos))
	return best


func _nearest_enemy(g: Node, u: Unit) -> int:
	var best := 99
	for e in g.units:
		if e.side != u.side:
			best = mini(best, Hex.distance(u.pos, e.pos))
	return best


## Prefer targets we can kill, then the most damage relative to their remaining HP.
func _best_target(g: Node, u: Unit, from: Vector2i) -> Unit:
	if not u.can_fire():
		return null
	var best: Unit = null
	var best_val := -INF
	for t in g.targets_from(u, from):
		var dmg: int = g.calc_damage(u, t)
		var val: float = float(mini(dmg, t.hp)) / t.max_hp() + (1.0 if dmg >= t.hp else 0.0)
		if dmg < t.hp and t.data().get("counter", false) and g.can_attack(t, u, t.pos):
			val -= float(g.calc_damage(t, u, true)) / u.max_hp() * 0.5
		val -= float(g.interceptors(u).size()) * 0.4
		val += float(Rules.UNITS[t.type]["cost"]) / 1000.0
		if val > best_val:
			best_val = val
			best = t
	return best if best_val > -0.3 else null


func _score_tile(g: Node, u: Unit, h: Vector2i) -> float:
	var side := u.side
	var score := 0.0
	var ranged: bool = u.data()["min_range"] > 1
	var wounded := u.hp < u.max_hp() * 0.35
	var fires_after_move: bool = u.data().get("fire_after_move", true)
	var capturer: bool = u.data().get("capture", false)

	var can_shoot_there := u.can_fire() if h == u.pos else fires_after_move
	if can_shoot_there:
		var t := _best_target(g, u, h)
		if t:
			score += 40.0 + float(g.calc_damage(u, t)) / t.max_hp() * 40.0

	if not u.is_flying():
		score += Rules.TERRAIN[g.terrain[h]]["def"] * 0.15
		if g.city_owner.has(h) and g.city_owner[h] != side:
			if capturer:
				score += 600.0 if h in g.hq[1 - side] else 70.0
			else:
				score -= 250.0 if h in g.hq[1 - side] else 60.0  # leave it free for the infantry
	else:
		for s in g.units:
			if s.side != side and s.data().get("intercept", false) and Hex.distance(s.pos, h) <= g.max_range(s):
				score -= 45.0

	# Distance to the closest objective: enemies, cities to take, threats to our HQ.
	var best_d := 99.0
	for e in g.units:
		if e.side == side or g.attack_value(u, e) <= 0:
			continue
		var d := float(Hex.distance(h, e.pos))
		if ranged:
			d = absf(d - g.max_range(u)) + (6.0 if d < u.data()["min_range"] else 0.0)
		for own in g.hq[side]:
			if Hex.distance(e.pos, own) <= 3:
				d -= 3.0
		best_d = minf(best_d, d)
	if capturer:
		for c in g.city_owner:
			if g.city_owner[c] != side:
				var bonus := 3.0 if c in g.hq[1 - side] else 1.0
				best_d = minf(best_d, Hex.distance(h, c) - bonus)
	if wounded:
		best_d = 99.0
		for c in g.cities_of(side):
			var occ: Unit = g.unit_at(c)
			if occ == null or occ == u:
				best_d = minf(best_d, Hex.distance(h, c))
	score -= best_d * 6.0

	if (ranged or u.type == "sam") and g.in_enemy_zoc(h, side):
		score -= 35.0
	if u.type == "sam":
		score -= _dist_to_friends(g, u, h) * 4.0
	return score


# --- Operational means --------------------------------------------------------

func _use_cards(g: Node, side: int) -> void:
	if g.cp[side] >= Rules.CARDS["strike"]["cp"]:
		var best: Variant = null
		var best_val := 45.0
		for h in g.card_hexes("strike", side):
			var val := _strike_value(g, side, h)
			if val > best_val:
				best_val = val
				best = h
		if best != null:
			g.use_card("strike", side, best)
	if g.winner >= 0:
		return
	if g.cp[side] >= Rules.CARDS["repair"]["cp"]:
		for u in g.units_of(side):
			if u.hp < u.max_hp() * 0.45 and Rules.UNITS[u.type]["cost"] >= 250:
				g.use_card("repair", side, u.pos)
				break
	if g.cp[side] >= Rules.CP_MAX - 1:
		var spots: Dictionary = g.card_hexes("reserve", side)
		if not spots.is_empty():
			g.use_card("reserve", side, spots.keys()[0])


func _strike_value(g: Node, side: int, h: Vector2i) -> float:
	var val := 0.0
	var center: Unit = g.unit_at(h)
	if center:
		val += _hit_value(center, g.STRIKE_DAMAGE, side)
	for n in Hex.neighbors(h):
		var o: Unit = g.unit_at(n)
		if o:
			val += _hit_value(o, g.STRIKE_SPLASH, side)
	return val


func _hit_value(u: Unit, dmg: int, side: int) -> float:
	var v := float(mini(dmg, u.hp)) * (1.0 + float(Rules.UNITS[u.type]["cost"]) / 400.0)
	if dmg >= u.hp:
		v += 40.0
	return v if u.side != side else -v * 1.5


# --- Production ---------------------------------------------------------------

func _build(g: Node, side: int) -> void:
	var enemy_air := 0
	for e in g.units:
		if e.side != side and e.is_flying():
			enemy_air += 1
	var my_sam := 0
	var my_capture := 0
	var my_logistics := 0
	for u in g.units_of(side):
		if u.type == "sam":
			my_sam += 1
		if u.data().get("capture", false):
			my_capture += 1
		if u.is_support():
			my_logistics += 1
	var cities: Array[Vector2i] = g.cities_of(side)
	var target_hq: Array = g.hq[1 - side]
	cities.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		return _front_dist(a, target_hq) < _front_dist(b, target_hq))
	for c in cities:
		if g.unit_at(c):
			continue
		if g.army_points(side) >= g.army_limit(side):
			return  # stay within the army limit (canon §16.3)
		var type := _pick_type(g, c, side, enemy_air > my_sam, my_capture < 3, my_logistics == 0)
		if type == "":
			return
		if g.build(c, type):
			match type:
				"sam":
					my_sam += 1
				"infantry":
					my_capture += 1
				"logistics":
					my_logistics += 1


func _front_dist(c: Vector2i, targets: Array) -> int:
	var best := 99
	for t in targets:
		best = mini(best, Hex.distance(c, t))
	return best


func _pick_type(g: Node, c: Vector2i, side: int, need_sam: bool, need_inf: bool, need_log: bool) -> String:
	var wish := "infantry"
	if need_sam:
		wish = "sam"
	elif need_inf:
		wish = "infantry"
	elif g.airfields.has(c) and g.rng.randf() < 0.6:
		wish = "heli" if g.rng.randf() < 0.65 else "jet"
	elif need_log and g.rng.randf() < 0.3:
		wish = "logistics"
	else:
		var roll: float = g.rng.randf()
		if roll < 0.25:
			wish = "tank"
		elif roll < 0.45:
			wish = "ifv"
		elif roll < 0.58:
			wish = "artillery"
		elif roll < 0.66:
			wish = "mlrs"
		elif roll < 0.72:
			wish = "recon"
	for t in [wish, "ifv", "infantry"]:
		if g.can_build_at(c, t, side):
			return t
	return ""
