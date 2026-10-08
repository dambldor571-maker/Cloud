class_name Hud
extends CanvasLayer
## Battle UI built in code: status bar, info/choice panel, move confirm,
## mission banner and a modal overlay (pause / result).

signal end_turn_pressed
signal cards_pressed
signal menu_pressed
signal hq_pressed
signal choice(id: String)
signal move_confirmed
signal move_cancelled

var status_label: Label
var end_turn_btn: Button
var cards_btn: Button
var hq_btn: Button
var info_label: Label
var choice_box: HFlowContainer
var top_panel: PanelContainer
var bottom_panel: PanelContainer
var overlay: ColorRect
var over_title: Label
var over_body: Label
var over_buttons: VBoxContainer
var move_box: HBoxContainer
var move_btn: Button
var banner: Label


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UiKit.theme()
	add_child(root)

	top_panel = UiKit.panel()
	top_panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	root.add_child(top_panel)
	var top_row := HBoxContainer.new()
	top_row.add_theme_constant_override("separation", 12)
	top_panel.add_child(top_row)
	var menu_btn := UiKit.button("☰", Vector2(64, 56))
	menu_btn.pressed.connect(func() -> void: menu_pressed.emit())
	top_row.add_child(menu_btn)
	status_label = Label.new()
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	status_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	top_row.add_child(status_label)
	hq_btn = UiKit.button("Штаб", Vector2(110, 56))
	hq_btn.pressed.connect(func() -> void: hq_pressed.emit())
	top_row.add_child(hq_btn)
	cards_btn = UiKit.button("Засоби", Vector2(130, 56), UiKit.ACCENT)
	cards_btn.pressed.connect(func() -> void: cards_pressed.emit())
	top_row.add_child(cards_btn)
	end_turn_btn = UiKit.button("Кінець ходу", Vector2(180, 56), UiKit.GOOD)
	end_turn_btn.pressed.connect(func() -> void: end_turn_pressed.emit())
	top_row.add_child(end_turn_btn)

	bottom_panel = UiKit.panel()
	bottom_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bottom_panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	root.add_child(bottom_panel)
	var bottom_col := VBoxContainer.new()
	bottom_col.add_theme_constant_override("separation", 8)
	bottom_panel.add_child(bottom_col)
	info_label = Label.new()
	info_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	info_label.add_theme_font_size_override("font_size", 21)
	bottom_col.add_child(info_label)
	choice_box = HFlowContainer.new()
	choice_box.add_theme_constant_override("h_separation", 8)
	choice_box.add_theme_constant_override("v_separation", 8)
	bottom_col.add_child(choice_box)
	bottom_panel.hide()

	move_box = HBoxContainer.new()
	move_box.add_theme_constant_override("separation", 12)
	root.add_child(move_box)
	move_btn = UiKit.button("Рух", Vector2(170, 60), UiKit.GOOD)
	move_btn.pressed.connect(func() -> void: move_confirmed.emit())
	move_box.add_child(move_btn)
	var cancel_btn := UiKit.button("Скасувати", Vector2(170, 60), UiKit.BAD)
	cancel_btn.pressed.connect(func() -> void: move_cancelled.emit())
	move_box.add_child(cancel_btn)
	move_box.hide()

	banner = Label.new()
	banner.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner.grow_horizontal = Control.GROW_DIRECTION_BOTH
	banner.grow_vertical = Control.GROW_DIRECTION_BOTH
	banner.add_theme_font_size_override("font_size", 38)
	banner.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	banner.add_theme_constant_override("outline_size", 12)
	banner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(banner)
	banner.hide()

	overlay = ColorRect.new()
	overlay.color = Color(0, 0, 0, 0.6)
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(overlay)
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.add_child(center)
	var over_panel := UiKit.panel(24)
	over_panel.custom_minimum_size = Vector2(520, 0)
	center.add_child(over_panel)
	var over_col := VBoxContainer.new()
	over_col.add_theme_constant_override("separation", 16)
	over_panel.add_child(over_col)
	over_title = Label.new()
	over_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	over_title.add_theme_font_size_override("font_size", 44)
	over_title.add_theme_color_override("font_color", UiKit.GOLD)
	over_col.add_child(over_title)
	over_body = Label.new()
	over_body.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	over_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	over_col.add_child(over_body)
	over_buttons = VBoxContainer.new()
	over_buttons.add_theme_constant_override("separation", 10)
	over_col.add_child(over_buttons)
	overlay.hide()


func set_status(text: String, player_turn: bool) -> void:
	status_label.text = text
	end_turn_btn.disabled = not player_turn
	cards_btn.disabled = not player_turn
	hq_btn.disabled = not player_turn


func show_info(text: String) -> void:
	show_panel(text, [])


## options: Array of {id, label, enabled?}
func show_panel(text: String, options: Array) -> void:
	for c in choice_box.get_children():
		choice_box.remove_child(c)
		c.queue_free()
	info_label.text = text
	for o in options:
		var cancel: bool = o["id"] == "cancel"
		var b := UiKit.button(o["label"], Vector2(150, 72), UiKit.BAD if cancel else UiKit.BASE)
		b.disabled = not o.get("enabled", true)
		var id: String = o["id"]
		b.pressed.connect(func() -> void: choice.emit(id))
		choice_box.add_child(b)
	bottom_panel.visible = text != "" or not options.is_empty()
	bottom_panel.offset_top = bottom_panel.offset_bottom  # re-grow upward to fit


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


func show_banner(text: String) -> void:
	banner.text = text
	banner.show()
	banner.modulate.a = 1.0
	var tw := create_tween()
	tw.tween_interval(2.2)
	tw.tween_property(banner, "modulate:a", 0.0, 0.8)
	tw.tween_callback(banner.hide)


## Modal dialog; buttons: Array of {id, label}.
func show_overlay(title: String, body: String, buttons: Array) -> void:
	over_title.text = title
	over_body.text = body
	for c in over_buttons.get_children():
		over_buttons.remove_child(c)
		c.queue_free()
	for o in buttons:
		var b := UiKit.button(o["label"], Vector2(0, 66))
		var id: String = o["id"]
		b.pressed.connect(func() -> void: choice.emit(id))
		over_buttons.add_child(b)
	overlay.show()


func hide_overlay() -> void:
	overlay.hide()


## Touch events reach the map even when a button handles the emulated mouse
## click, so the map asks the HUD whether a point is covered by UI.
func is_over_ui(p: Vector2) -> bool:
	if overlay.visible or top_panel.get_global_rect().has_point(p):
		return true
	if bottom_panel.visible and bottom_panel.get_global_rect().has_point(p):
		return true
	return move_box.visible and move_box.get_global_rect().has_point(p)
