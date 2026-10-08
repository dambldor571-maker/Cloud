class_name UiKit
extends RefCounted
## Shared look for menus and the battle HUD.

const BASE := Color(0.20, 0.27, 0.34)
const ACCENT := Color(0.62, 0.45, 0.16)
const GOOD := Color(0.18, 0.50, 0.26)
const BAD := Color(0.55, 0.20, 0.18)
const GOLD := Color(1.0, 0.85, 0.40)
const SAND := Color(0.92, 0.87, 0.72)
const PANEL := Color(0.05, 0.07, 0.10, 0.86)


static var _font: Font
static var _bold: Font


static func font() -> Font:
	if _font == null:
		_font = load("res://assets/fonts/DejaVuSans.ttf")
	return _font


static func bold() -> Font:
	if _bold == null:
		_bold = load("res://assets/fonts/DejaVuSans-Bold.ttf")
	return _bold


static func theme() -> Theme:
	var t := Theme.new()
	t.default_font = font()
	t.default_font_size = 22
	return t


static func panel(margin := 12) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = PANEL
	sb.set_content_margin_all(margin)
	sb.set_corner_radius_all(10)
	sb.border_color = Color(SAND, 0.25)
	sb.set_border_width_all(1)
	p.add_theme_stylebox_override("panel", sb)
	return p


static func button(text: String, min_size := Vector2(200, 64), color := BASE) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = min_size
	b.focus_mode = Control.FOCUS_NONE
	for state in ["normal", "hover", "pressed", "disabled"]:
		var sb := StyleBoxFlat.new()
		match state:
			"hover":
				sb.bg_color = color.lightened(0.15)
			"pressed":
				sb.bg_color = color.darkened(0.25)
			"disabled":
				sb.bg_color = color.darkened(0.55)
			_:
				sb.bg_color = color
		sb.set_corner_radius_all(10)
		sb.set_border_width_all(2)
		sb.border_color = Color(SAND, 0.15 if state == "disabled" else 0.7)
		sb.set_content_margin_all(8)
		b.add_theme_stylebox_override(state, sb)
	b.add_theme_color_override("font_color", Color.WHITE)
	b.add_theme_color_override("font_disabled_color", Color(1, 1, 1, 0.35))
	return b


static func label(text: String, size := 24, color := Color.WHITE) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	if size >= 30:
		l.add_theme_font_override("font", bold())
	l.add_theme_color_override("font_color", color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l
