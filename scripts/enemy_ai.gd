class_name EnemyAI
extends RefCounted
## Simple greedy AI: ranged units fire first, others advance on the best-scored hex,
## then attack; money is spent on units in free cities.

const ORDER := {"artillery": 0, "air_defense": 1, "drone": 2, "tank": 3, "infantry": 4}


func take_turn(g: Node) -> void:
	var side: int = g.current_side
	var id: int = g.game_id
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
	var target := _best_target(g, u, u.pos)
	if target:
		g.attack(u, target)
		await g.ai_pause()
		return
	var best_pos: Vector2i = u.pos
	var best_score := _score_tile(g, u, u.pos)
	var reach: Dictionary = g.compute_reachable(u)
	for h in reach:
		var s := _score_tile(g, u, h)
		if s > best_score:
			best_score = s
			best_pos = h
	if best_pos != u.pos:
		g.move_unit(u, best_pos)
		await g.ai_pause()
		if g.winner >= 0 or g.game_id != id:
			return
	if u.can_fire():
		target = _best_target(g, u, u.pos)
		if target:
			g.attack(u, target)
			await g.ai_pause()


## Prefer targets we can kill, then the most damage relative to their remaining HP.
func _best_target(g: Node, u: Unit, from: Vector2i) -> Unit:
	if not u.can_fire():
		return null
	var best: Unit = null
	var best_val := -INF
	for t in g.targets_from(u, from):
		var dmg: int = g.calc_damage(u, t)
		var val: float = float(mini(dmg, t.hp)) / t.max_hp() + (1.0 if dmg >= t.hp else 0.0)
		if g.can_attack(t, u, t.pos) and dmg < t.hp:
			val -= float(g.calc_damage(t, u, true)) / u.max_hp() * 0.5
		val += float(Rules.UNITS[t.type]["cost"]) / 1000.0
		if val > best_val:
			best_val = val
			best = t
	return best


func _score_tile(g: Node, u: Unit, h: Vector2i) -> float:
	var side := u.side
	var score := 0.0
	var ranged: bool = u.data()["min_range"] > 1
	var wounded := u.hp < u.max_hp() * 0.35
	var fires_after_move: bool = u.data().get("fire_after_move", true)

	var can_shoot_there := u.can_fire() if h == u.pos else fires_after_move
	if can_shoot_there:
		var t := _best_target(g, u, h)
		if t:
			score += 40.0 + float(g.calc_damage(u, t)) / t.max_hp() * 40.0

	var terrain_def: int = Rules.TERRAIN[g.terrain[h]]["def"]
	if not u.is_flying():
		score += terrain_def * 0.15
		if g.city_owner.has(h) and g.city_owner[h] != side:
			score += 500.0 if h == g.capitals[1 - side] else 60.0

	# Distance to the closest objective: enemy units, capturable cities, threats near home.
	var best_d := 99.0
	for e in g.units:
		if e.side == side or (e.is_flying() and not u.data().get("hits_air", false)):
			continue
		var d := float(Hex.distance(h, e.pos))
		if ranged:
			d = absf(d - u.data()["range"]) + (6.0 if d < u.data()["min_range"] else 0.0)
		if Hex.distance(e.pos, g.capitals[side]) <= 3:
			d -= 3.0
		best_d = minf(best_d, d)
	if not u.is_flying():
		for c in g.city_owner:
			if g.city_owner[c] != side:
				best_d = minf(best_d, Hex.distance(h, c) - 1.0)
	if wounded:
		best_d = 99.0
		for c in g.cities_of(side):
			var occ: Unit = g.unit_at(c)
			if occ == null or occ == u:
				best_d = minf(best_d, Hex.distance(h, c))
	score -= best_d * 6.0

	if ranged and g.in_enemy_zoc(h, side):
		score -= 30.0
	return score


func _build(g: Node, side: int) -> void:
	var enemy_drones := 0
	for e in g.units:
		if e.side != side and e.type == "drone":
			enemy_drones += 1
	var my_ad := 0
	for u in g.units_of(side):
		if u.type == "air_defense":
			my_ad += 1
	var cities: Array[Vector2i] = g.cities_of(side)
	# Capital first, then frontline cities (closest to the enemy capital).
	cities.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		return Hex.distance(a, g.capitals[1 - side]) < Hex.distance(b, g.capitals[1 - side]))
	for c in cities:
		if g.unit_at(c):
			continue
		var type := "infantry"
		if enemy_drones > my_ad:
			type = "air_defense"
		else:
			var roll: float = g.rng.randf()
			if roll < 0.35:
				type = "tank"
			elif roll < 0.55:
				type = "artillery"
			elif roll < 0.65:
				type = "drone"
		if g.money[side] < Rules.UNITS[type]["cost"]:
			type = "infantry"
		if g.money[side] < Rules.UNITS[type]["cost"]:
			return
		if g.build(c, type) and type == "air_defense":
			my_ad += 1
