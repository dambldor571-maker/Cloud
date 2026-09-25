class_name Hud
extends CanvasLayer
## Touch-friendly UI built in code: status bar, info/build panel, game-over dialog.

signal end_turn_pressed
signal build_pressed(unit_type: String)
signal restart_pressed
signal move_confirmed
signal move_cancelled

var status_label: Label
var end_turn_btn: Button
var info_label: Label
var build_box: HBoxContainer
var top_panel: PanelContainer
var bottom_panel: PanelContainer
var over_center: CenterContainer
var over_label: Label
var move_box: HBoxContainer
var move_btn: Button


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = _make_theme()
	add_child(root)

	top_panel = _panel()
	top_panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	root.add_child(top_panel)
	var top_row := HBoxContainer.new()
	top_row.add_theme_constant_override("separation", 16)
	top_panel.add_child(top_row)
	status_label = Label.new()
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	status_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	top_row.add_child(status_label)
	end_turn_btn = Button.new()
	end_turn_btn.text = "Кінець ходу"
	end_turn_btn.custom_minimum_size = Vector2(200, 60)
	end_turn_btn.pressed.connect(func() -> void: end_turn_pressed.emit())
	top_row.add_child(end_turn_btn)

	bottom_panel = _panel()
	bottom_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bottom_panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	root.add_child(bottom_panel)
	var bottom_col := VBoxContainer.new()
	bottom_panel.add_child(bottom_col)
	info_label = Label.new()
	info_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	bottom_col.add_child(info_label)
	build_box = HBoxContainer.new()
	build_box.add_theme_constant_override("separation", 10)
	bottom_col.add_child(build_box)
	bottom_panel.hide()

	over_center = CenterContainer.new()
	over_center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	over_center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(over_center)
	var over_panel := _panel()
	over_center.add_child(over_panel)
	var over_col := VBoxContainer.new()
	over_col.add_theme_constant_override("separation", 20)
	over_panel.add_child(over_col)
	over_label = Label.new()
	over_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	over_label.add_theme_font_size_override("font_size", 36)
	over_col.add_child(over_label)
	var restart_btn := Button.new()
	restart_btn.text = "Нова гра"
	restart_btn.custom_minimum_size = Vector2(260, 70)
	restart_btn.pressed.connect(func() -> void: restart_pressed.emit())
	over_col.add_child(restart_btn)
	over_center.hide()

	# "Рух / Скасувати" floating under the planned destination.
	move_box = HBoxContainer.new()
	move_box.add_theme_constant_override("separation", 12)
	root.add_child(move_box)
	move_btn = _action_button("Рух", Color(0.18, 0.55, 0.24))
	move_btn.pressed.connect(func() -> void: move_confirmed.emit())
	move_box.add_child(move_btn)
	var cancel_btn := _action_button("Скасувати", Color(0.59, 0.2, 0.18))
	cancel_btn.pressed.connect(func() -> void: move_cancelled.emit())
	move_box.add_child(cancel_btn)
	move_box.hide()


func set_status(text: String, player_turn: bool) -> void:
	status_label.text = text
	end_turn_btn.disabled = not player_turn


func show_info(text: String) -> void:
	_clear_build()
	info_label.text = text
	bottom_panel.visible = text != ""
	_shrink_bottom()


## options: Array of {type, name, cost, enabled}
func show_build(text: String, options: Array) -> void:
	_clear_build()
	info_label.text = text
	for o in options:
		var b := Button.new()
		b.text = "%s\n%d $" % [o["name"], o["cost"]]
		b.custom_minimum_size = Vector2(150, 80)
		b.disabled = not o["enabled"]
		var t: String = o["type"]
		b.pressed.connect(func() -> void: build_pressed.emit(t))
		build_box.add_child(b)
	bottom_panel.show()
	_shrink_bottom()


func show_move_confirm(steps: int) -> void:
	move_btn.text = "Рух (%d кл.)" % steps
	move_box.show()
	move_box.reset_size()


func place_move_confirm(p: Vector2) -> void:
	if not move_box.visible:
		return
	var vp := move_box.get_viewport_rect().size
	var pos := p - Vector2(move_box.size.x / 2.0, 0)
	move_box.position = pos.clamp(Vector2.ZERO, vp - move_box.size)


func hide_move_confirm() -> void:
	move_box.hide()


func show_game_over(text: String) -> void:
	over_label.text = text
	over_center.show()


func hide_game_over() -> void:
	over_center.hide()


## Touch events reach the map even when a button handles the emulated mouse
## click, so the map asks the HUD whether a point is covered by UI.
func is_over_ui(p: Vector2) -> bool:
	if top_panel.get_global_rect().has_point(p):
		return true
	if bottom_panel.visible and bottom_panel.get_global_rect().has_point(p):
		return true
	if move_box.visible and move_box.get_global_rect().has_point(p):
		return true
	return over_center.visible


## Collapse to zero height; the container re-grows upward to fit its content.
func _shrink_bottom() -> void:
	bottom_panel.offset_top = bottom_panel.offset_bottom


func _action_button(text: String, color: Color) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(170, 60)
	for state in ["normal", "hover", "pressed", "focus"]:
		var sb := StyleBoxFlat.new()
		sb.bg_color = color.lightened(0.15) if state == "hover" else (color.darkened(0.2) if state == "pressed" else color)
		sb.set_corner_radius_all(12)
		sb.set_border_width_all(3)
		sb.border_color = Color(1, 1, 1, 0.9)
		sb.shadow_size = 6
		sb.shadow_color = Color(0, 0, 0, 0.45)
		b.add_theme_stylebox_override(state, sb)
	b.add_theme_color_override("font_color", Color.WHITE)
	return b


func _clear_build() -> void:
	for c in build_box.get_children():
		build_box.remove_child(c)
		c.queue_free()


func _panel() -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.07, 0.10, 0.82)
	sb.set_content_margin_all(12)
	sb.set_corner_radius_all(6)
	p.add_theme_stylebox_override("panel", sb)
	return p


func _make_theme() -> Theme:
	var t := Theme.new()
	t.default_font_size = 24
	return t
