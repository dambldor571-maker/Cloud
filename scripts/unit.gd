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
## 1 = sprite faces right, -1 = left; follows the last move or attack.
var facing := 1


func _init(p_type: String, p_side: int, p_pos: Vector2i) -> void:
	type = p_type
	side = p_side
	pos = p_pos
	hp = max_hp()
	draw_pos = Hex.to_pixel(pos)
	facing = 1 if side == 0 else -1


func face_towards(x: float) -> void:
	if absf(x - draw_pos.x) > 1.0:
		facing = 1 if x > draw_pos.x else -1


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
