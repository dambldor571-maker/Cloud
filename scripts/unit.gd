class_name Unit
extends RefCounted

var type: String
var side: int
var pos: Vector2i
var hp: int
var moved := false
var attacked := false
## Pixel position used for rendering (animated towards Hex.to_pixel(pos)).
var draw_pos := Vector2.ZERO
## Hex direction the unit faces (index into Hex.DIRS: 0 = east, then
## counter-clockwise); follows the last move or attack.
var facing := 0
## Continuous headings for sprites with a separate turret, in map degrees
## counter-clockwise from east: hull, turret, and the direction the turret's
## idle scan swings around (where it last aimed).
var hull_angle := 0.0
var turret_angle := 0.0
var turret_rest := 0.0
var animating := false  # a move or attack animation is turning this unit
var scan_target := 0.0
var scan_wait := 0.0


func _init(p_type: String, p_side: int, p_pos: Vector2i) -> void:
	type = p_type
	side = p_side
	pos = p_pos
	hp = max_hp()
	draw_pos = Hex.to_pixel(pos)
	set_facing(0 if side == 0 else 3)
	scan_wait = randf() * 3.0  # so turrets don't all start scanning together


## Snap hull and turret to a hex direction (no animation).
func set_facing(d: int) -> void:
	facing = d
	hull_angle = 60.0 * d
	turret_angle = hull_angle
	turret_rest = hull_angle
	scan_target = hull_angle


## Face the step from hex a to its neighbour b.
func face_step(a: Vector2i, b: Vector2i) -> void:
	var i := Hex.DIRS.find(b - a)
	if i >= 0:
		set_facing(i)


## Turn to the hex direction closest to the given map point.
func face_towards(p: Vector2) -> void:
	var d := p - draw_pos
	if d.length() > 1.0:
		set_facing(posmod(roundi(rad_to_deg(atan2(-d.y, d.x)) / 60.0), 6))


func data() -> Dictionary:
	return Rules.UNITS[type]


func max_hp() -> int:
	return data()["hp"]


func display_name() -> String:
	return data()["name"]


func is_flying() -> bool:
	return data().get("flying", false)


func can_move() -> bool:
	return not moved and not attacked


func can_fire() -> bool:
	return not attacked and (not moved or data().get("fire_after_move", true))
