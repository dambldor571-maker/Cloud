extends Control
## Unit Workshop: set up a 3D model as a game unit and render its sprites.
## Left: the live preview (the same scene the sprites are rendered from).
## Right: settings. Command line render (no window work needed):
##   UnitWorkshop.exe -- --model=T72.glb --config=t72.unit.json --out=D:/sprites

const SETTINGS := "user://workshop.cfg"

var studio := UnitStudio.new()
var vp := SubViewport.new()
var backdrop := MapBackdrop.new()
var ui := {}  # controls by id
var parts_box: GridContainer
var status: Label
var hud: Label
var overlay: Label
var play_timer := Timer.new()
var prefs := ConfigFile.new()
var dlg_model: FileDialog
var dlg_load: FileDialog
var dlg_save: FileDialog
var dlg_out: FileDialog
var dlg_tex: FileDialog
var tex_target := UnitStudio.ALL_PARTS
var _tex_map := ""


func _ready() -> void:
	prefs.load(SETTINGS)
	add_child(studio)
	_build_ui()
	studio.setup(vp)
	studio.progress.connect(_on_progress)
	_sync()
	var args := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and "=" in a:
			args[a.substr(2).get_slice("=", 0)] = a.get_slice("=", 1)
	if args.has("out"):
		_cli_render.call_deferred(args)
	elif args.has("shot"):
		_cli_shot.call_deferred(args)


# --- Layout ---------------------------------------------------------------------

func _build_ui() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var th := Theme.new()
	th.default_font_size = 15
	theme = th
	var bg := ColorRect.new()
	bg.color = Color(0.11, 0.12, 0.09)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var split := HSplitContainer.new()
	split.set_anchors_preset(Control.PRESET_FULL_RECT)
	split.add_theme_constant_override("separation", 8)
	add_child(split)

	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	split.add_child(left)
	var stage := Control.new()
	stage.size_flags_vertical = Control.SIZE_EXPAND_FILL
	stage.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	stage.clip_contents = true
	left.add_child(stage)
	backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	stage.add_child(backdrop)
	var svc := SubViewportContainer.new()
	svc.stretch = true
	svc.set_anchors_preset(Control.PRESET_FULL_RECT)
	svc.gui_input.connect(_on_view_input)
	stage.add_child(svc)
	vp.handle_input_locally = false
	svc.add_child(vp)
	hud = Label.new()
	hud.position = Vector2(10, 8)
	hud.add_theme_color_override("font_shadow_color", Color.BLACK)
	stage.add_child(hud)
	overlay = Label.new()
	overlay.set_anchors_preset(Control.PRESET_CENTER)
	overlay.add_theme_font_size_override("font_size", 22)
	overlay.add_theme_color_override("font_shadow_color", Color.BLACK)
	overlay.visible = false
	stage.add_child(overlay)
	var bar := HBoxContainer.new()
	left.add_child(bar)
	_button(bar, "play", "▶ Оберти", _on_play, true)
	_button(bar, "fire", "Постріл", _on_fire)
	_button(bar, "side", "Синя сторона", _on_side)
	_button(bar, "grid", "Сітка", func():
		backdrop.show_grid = ui["grid"].button_pressed
		backdrop.queue_redraw(), true)
	ui["grid"].set_pressed_no_signal(true)
	var zl := Label.new()
	zl.text = "   Огляд, м"
	bar.add_child(zl)
	_slider(bar, "zoom", 8, 45, 1, func(v): _set_zoom(v), 160)
	play_timer.wait_time = 0.28
	play_timer.timeout.connect(func():
		studio.hull_deg = fmod(studio.hull_deg + 20.0, 360.0)
		_sync())
	add_child(play_timer)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(470, 0)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	split.add_child(scroll)
	var panel := VBoxContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.add_theme_constant_override("separation", 6)
	scroll.add_child(panel)

	var s := _section(panel, "Модель")
	var row := HBoxContainer.new()
	s.add_child(row)
	_button(row, "open", "Відкрити модель…", func(): dlg_model.popup_centered_ratio(0.7))
	_button(row, "load", "Відкрити налаштування…", func(): dlg_load.popup_centered_ratio(0.7))
	_field(s, "name", "Назва (латиницею)", func(t): studio.unit_name = _clean_name(t))
	status = Label.new()
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.text = "Відкрийте модель: glb, gltf, fbx або obj."
	s.add_child(status)

	s = _section(panel, "Розмір і напрям")
	_slider_row(s, "length", "Довжина, м", 2, 16, 0.05, func(v): studio.length_m = v; studio.refit())
	_slider_row(s, "yaw", "Поворот моделі, °", -180, 180, 1, func(v): studio.yaw = v; studio.refit(); studio.auto_hull_offset())
	row = HBoxContainer.new()
	s.add_child(row)
	var hint := Label.new()
	hint.text = "Гармата дивиться праворуч:"
	row.add_child(hint)
	for y in [0, 90, 180, -90]:
		_button(row, "yaw%d" % y, "%d°" % y, func(): studio.yaw = y; studio.refit(); studio.auto_hull_offset(); _sync())
	_slider_row(s, "offset", "Зсув корпусу, м", -3, 3, 0.01, func(v): studio.hull_offset_m = v; studio.apply_pose())
	_button(s, "auto_offset", "Зсув автоматично (центр корпусу на центрі клітинки)",
		func(): studio.auto_hull_offset(); _sync())

	s = _section(panel, "Фарба і зношеність")
	row = HBoxContainer.new()
	s.add_child(row)
	_button(row, "own", "Наша фарба", func(): _set_paint(true), true)
	_button(row, "file", "Текстура файлу", func(): _set_paint(false), true)
	var tint_row := HBoxContainer.new()
	s.add_child(tint_row)
	var tl := Label.new()
	tl.text = "Відтінок текстури"
	tl.custom_minimum_size.x = 170
	tint_row.add_child(tl)
	var tint := ColorPickerButton.new()
	tint.custom_minimum_size = Vector2(80, 28)
	tint.color_changed.connect(func(c): studio.tint = c; studio.apply_materials())
	tint_row.add_child(tint)
	ui["tint"] = tint
	ui["tint_row"] = tint_row
	_slider_row(s, "rough", "Матовість", 0.3, 1.0, 0.01, func(v): studio.roughness = v; studio.apply_materials())
	_slider_row(s, "wear", "Зношеність", 0, 1, 0.01, func(v): studio.weathering = v; studio.apply_materials())
	_slider_row(s, "mud", "Бруд до висоти, м", 0, 2.5, 0.05, func(v): studio.mud_height = v; studio.apply_materials())

	_build_textures(panel)
	_build_look(panel)

	s = _section(panel, "Частини")
	parts_box = GridContainer.new()
	parts_box.columns = 4
	parts_box.add_theme_constant_override("h_separation", 8)
	s.add_child(parts_box)
	var note := Label.new()
	note.text = "Башта і гармата крутяться окремо від корпусу. «Прибрати» ховає деталь з рендера. Прапорець — деталь відкидає тінь."
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.modulate = Color(1, 1, 1, 0.7)
	s.add_child(note)
	_slider_row(s, "recoil", "Відкат, м", 0, 0.8, 0.01, func(v): studio.recoil_m = v; studio.apply_pose())

	s = _section(panel, "Перевірка")
	_slider_row(s, "hull", "Корпус, °", 0, 340, 20, func(v): studio.hull_deg = v; studio.apply_pose(); _update_hud())
	_slider_row(s, "turret", "Башта, °", 0, 340, 20, func(v): studio.turret_deg = v; studio.apply_pose(); _update_hud())
	var follow := CheckBox.new()
	follow.text = "Башта разом з корпусом"
	follow.toggled.connect(func(on):
		studio.turret_follows = on
		if not on:
			studio.turret_deg = studio.hull_deg
		_sync())
	s.add_child(follow)
	ui["follow"] = follow
	var n2 := Label.new()
	n2.text = "18 напрямків по 20°, як у грі: 0° — схід, далі проти годинникової стрілки. Колесо миші — наближення."
	n2.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	n2.modulate = Color(1, 1, 1, 0.7)
	s.add_child(n2)

	s = _section(panel, "Збереження і рендер")
	row = HBoxContainer.new()
	s.add_child(row)
	_button(row, "save", "Зберегти налаштування…", func():
		dlg_save.current_file = studio.unit_name + ".unit.json"
		dlg_save.popup_centered_ratio(0.7))
	_button(row, "render", "Рендер спрайтів…", func(): dlg_out.popup_centered_ratio(0.7))
	var bar2 := ProgressBar.new()
	bar2.visible = false
	s.add_child(bar2)
	ui["progress"] = bar2

	dlg_model = _dialog(FileDialog.FILE_MODE_OPEN_FILE, ["*.glb, *.gltf, *.fbx, *.obj ; 3D-моделі"], "model_dir",
		func(p): _open_model(p))
	dlg_load = _dialog(FileDialog.FILE_MODE_OPEN_FILE, ["*.unit.json ; Налаштування юніта"], "cfg_dir",
		func(p): _open_config(p))
	dlg_save = _dialog(FileDialog.FILE_MODE_SAVE_FILE, ["*.unit.json ; Налаштування юніта"], "cfg_dir",
		func(p): _save_config(p))
	dlg_out = _dialog(FileDialog.FILE_MODE_OPEN_DIR, [], "out_dir", func(p): _render(p))


func _section(parent: Control, title: String) -> VBoxContainer:
	var pc := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.16, 0.18, 0.13)
	sb.set_corner_radius_all(4)
	sb.set_content_margin_all(10)
	pc.add_theme_stylebox_override("panel", sb)
	parent.add_child(pc)
	var v := VBoxContainer.new()
	pc.add_child(v)
	var l := Label.new()
	l.text = title.to_upper()
	l.add_theme_color_override("font_color", Color(0.72, 0.8, 0.5))
	v.add_child(l)
	return v


func _button(parent: Control, id: String, text: String, cb: Callable, toggle := false) -> Button:
	var b := Button.new()
	b.text = text
	b.toggle_mode = toggle
	if toggle:
		b.toggled.connect(func(_on): cb.call())
	else:
		b.pressed.connect(cb)
	parent.add_child(b)
	ui[id] = b
	return b


func _field(parent: Control, id: String, label: String, cb: Callable) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	var l := Label.new()
	l.text = label
	l.custom_minimum_size.x = 170
	row.add_child(l)
	var e := LineEdit.new()
	e.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	e.text_changed.connect(cb)
	e.focus_exited.connect(func(): e.text = studio.unit_name)
	row.add_child(e)
	ui[id] = e


func _slider(parent: Control, id: String, lo: float, hi: float, step: float, cb: Callable, width := 0) -> HSlider:
	var sl := HSlider.new()
	sl.min_value = lo
	sl.max_value = hi
	sl.step = step
	sl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sl.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	if width > 0:
		sl.custom_minimum_size.x = width
	sl.value_changed.connect(func(v):
		if not _syncing:
			cb.call(v)
			_sync())
	parent.add_child(sl)
	ui[id] = sl
	return sl


func _slider_row(parent: Control, id: String, label: String, lo: float, hi: float, step: float, cb: Callable) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	var l := Label.new()
	l.text = label
	l.custom_minimum_size.x = 170
	row.add_child(l)
	_slider(row, id, lo, hi, step, cb)
	var sp := SpinBox.new()
	sp.min_value = lo
	sp.max_value = hi
	sp.step = step
	sp.custom_minimum_size.x = 96
	sp.value_changed.connect(func(v):
		if not _syncing:
			ui[id].value = v)
	row.add_child(sp)
	ui[id + "_spin"] = sp


func _dialog(mode: FileDialog.FileMode, filters: Array, pref_key: String, cb: Callable) -> FileDialog:
	var d := FileDialog.new()
	d.file_mode = mode
	d.access = FileDialog.ACCESS_FILESYSTEM
	d.use_native_dialog = true
	d.filters = PackedStringArray(filters)
	d.current_dir = prefs.get_value("dirs", pref_key, OS.get_system_dir(OS.SYSTEM_DIR_DOCUMENTS))
	var remember := func(p: String):
		prefs.set_value("dirs", pref_key, p if mode == FileDialog.FILE_MODE_OPEN_DIR else p.get_base_dir())
		prefs.save(SETTINGS)
		cb.call(p)
	d.file_selected.connect(remember)
	d.dir_selected.connect(remember)
	add_child(d)
	return d


# --- State <-> controls ------------------------------------------------------------

var _syncing := false


func _sync() -> void:
	_syncing = true
	var vals := {"length": studio.length_m, "yaw": studio.yaw, "offset": studio.hull_offset_m,
		"rough": studio.roughness, "wear": studio.weathering, "mud": studio.mud_height, "recoil": studio.recoil_m,
		"hull": studio.hull_deg, "turret": studio.turret_deg if not studio.turret_follows else studio.hull_deg,
		"zoom": studio.zoom_m}
	for k in vals:
		ui[k].value = vals[k]
		if ui.has(k + "_spin"):
			ui[k + "_spin"].value = vals[k]
	ui["turret"].editable = not studio.turret_follows
	ui["follow"].set_pressed_no_signal(studio.turret_follows)
	ui["own"].set_pressed_no_signal(studio.own_paint)
	ui["file"].set_pressed_no_signal(not studio.own_paint)
	ui["tint"].color = studio.tint
	ui["tint_row"].visible = not studio.own_paint
	if not ui["name"].has_focus():
		ui["name"].text = studio.unit_name
	_sync_textures()
	_syncing = false
	studio.apply_pose()
	_update_hud()


func _update_hud() -> void:
	var t := studio.hull_deg if studio.turret_follows else studio.turret_deg
	var f := studio.file_path.get_file() if studio.file_path != "" else "модель не відкрита"
	hud.text = "%s    корпус %d° · башта %d°" % [f, studio.hull_deg, t]


func _rebuild_parts() -> void:
	for c in parts_box.get_children():
		c.queue_free()
	for h in ["Деталь", "Роль", "Колір", "Тінь"]:
		var l := Label.new()
		l.text = h
		l.modulate = Color(1, 1, 1, 0.6)
		parts_box.add_child(l)
	for g in studio.groups:
		var l := Label.new()
		l.text = "%s ×%d" % [g["key"], g["meshes"].size()] if g["meshes"].size() > 1 else g["key"]
		l.custom_minimum_size.x = 150
		l.clip_text = true
		l.tooltip_text = g["key"]
		l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		parts_box.add_child(l)
		var ob := OptionButton.new()
		for r in UnitStudio.ROLES:
			ob.add_item(UnitStudio.ROLE_NAMES[r])
		ob.selected = UnitStudio.ROLES.find(g["role"])
		parts_box.add_child(ob)
		var cp := ColorPickerButton.new()
		cp.custom_minimum_size = Vector2(56, 26)
		cp.color = g["color"]
		cp.disabled = not studio.own_paint
		parts_box.add_child(cp)
		var cb := CheckBox.new()
		cb.button_pressed = g["shadow"]
		parts_box.add_child(cb)
		ob.item_selected.connect(func(i):
			g["role"] = UnitStudio.ROLES[i]
			g["color"] = UnitStudio.ROLE_COLORS[g["role"]]
			g["shadow"] = g["role"] != "gun"
			cp.color = g["color"]
			cb.set_pressed_no_signal(g["shadow"])
			studio.apply_materials()
			studio.refit())
		cp.color_changed.connect(func(c):
			g["color"] = c
			studio.apply_materials())
		cb.toggled.connect(func(on):
			g["shadow"] = on
			studio.apply_materials())


func _set_paint(own: bool) -> void:
	studio.own_paint = own
	studio.apply_materials()
	_rebuild_parts()
	_sync()


static func _clean_name(t: String) -> String:
	var re := RegEx.create_from_string("[^a-z0-9_-]+")
	return re.sub(t.strip_edges().to_lower(), "_", true)


# --- Actions ---------------------------------------------------------------------------

func _open_model(path: String) -> bool:
	status.text = "Відкриваю %s…" % path.get_file()
	await get_tree().process_frame
	var err := studio.load_model(path)
	if err != "":
		status.text = "Не вдалося відкрити %s: %s. glTF з окремими файлами краще зберегти як .glb." % [path.get_file(), err]
		return false
	studio.unit_name = _clean_name(path.get_file().get_basename())
	var n := 0
	for g in studio.groups:
		n += g["meshes"].size()
	status.text = "%s: %d деталей, %d груп." % [path.get_file(), n, studio.groups.size()]
	_rebuild_parts()
	_sync()
	return true


func _open_config(path: String) -> void:
	var cfg = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not cfg is Dictionary:
		status.text = "Файл налаштувань пошкоджений: %s" % path.get_file()
		return
	var model_path: String = cfg.get("file", "")
	if studio.model == null or studio.file_path != model_path:
		if model_path == "" or not FileAccess.file_exists(model_path):
			status.text = "Модель %s не знайдена. Відкрийте її, потім знову налаштування." % model_path.get_file()
			return
		if not await _open_model(model_path):
			return
	studio.from_config(cfg)
	_rebuild_parts()
	_sync()
	status.text = "Налаштування «%s» застосовано." % studio.unit_name


func _save_config(path: String) -> void:
	if not path.ends_with(".unit.json"):
		path = path.get_basename() + ".unit.json"
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		status.text = "Не вдалося записати %s" % path
		return
	f.store_string(JSON.stringify(studio.to_config(), "  "))
	status.text = "Збережено: %s" % path


func _render(dir: String) -> void:
	if studio.model == null:
		status.text = "Спочатку відкрийте модель."
		return
	if studio.busy:
		return
	if ui["play"].button_pressed:
		ui["play"].button_pressed = false
	overlay.text = "Рендер…"
	overlay.visible = true
	ui["progress"].visible = true
	for k in ["open", "load", "render", "save"]:
		ui[k].disabled = true
	var err: String = await studio.render_sprites(dir)
	for k in ["open", "load", "render", "save"]:
		ui[k].disabled = false
	overlay.visible = false
	ui["progress"].visible = false
	status.text = err if err != "" else "Готово: %s (кадри, %s.json, %s_sheet.png)" % [dir, studio.unit_name, studio.unit_name]
	if err == "":
		OS.shell_open(dir)


func _on_progress(done: int, total: int, text: String) -> void:
	ui["progress"].max_value = total
	ui["progress"].value = done
	overlay.text = "Рендер: %s" % text


func _on_play() -> void:
	if ui["play"].button_pressed:
		ui["play"].text = "■ Стоп"
		play_timer.start()
	else:
		ui["play"].text = "▶ Оберти"
		play_timer.stop()


func _on_fire() -> void:
	# The game shows recoil frames 3, 2, 1, 0 after a shot.
	for st in [3, 3, 2, 1, 0]:
		studio.recoil_step = st
		studio.apply_pose()
		await get_tree().create_timer(0.11).timeout


func _on_side() -> void:
	backdrop.side = 1 - backdrop.side
	backdrop.queue_redraw()
	ui["side"].text = "Червона сторона" if backdrop.side else "Синя сторона"


func _set_zoom(v: float) -> void:
	studio.zoom_m = v
	studio.update_camera()
	backdrop.zoom_m = v
	backdrop.queue_redraw()


func _on_view_input(ev: InputEvent) -> void:
	if ev is InputEventMouseButton and ev.pressed:
		var d := 0.0
		if ev.button_index == MOUSE_BUTTON_WHEEL_UP:
			d = -2.0
		elif ev.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			d = 2.0
		if d != 0.0:
			_set_zoom(clampf(studio.zoom_m + d, 8.0, 45.0))
			_sync()


## --model=... [--config=...] [--hull=deg --turret=deg] --shot=FILE.png: window screenshot and quit.
func _cli_shot(args: Dictionary) -> void:
	if args.has("model"):
		await _open_model(args["model"])
	if args.has("config"):
		await _open_config(args["config"])
	if args.has("hull"):
		studio.hull_deg = float(args["hull"])
	if args.has("turret"):
		studio.turret_follows = false
		studio.turret_deg = float(args["turret"])
	if args.has("zoom"):
		_set_zoom(float(args["zoom"]))
	_sync()
	for i in 20:
		await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(args["shot"])
	get_tree().quit()


## --model=... [--config=...] --out=DIR: render and quit.
func _cli_render(args: Dictionary) -> void:
	var cfg := {}
	if args.has("config"):
		var parsed = JSON.parse_string(FileAccess.get_file_as_string(args["config"]))
		if parsed is Dictionary:
			cfg = parsed
	var path: String = args.get("model", cfg.get("file", ""))
	if not await _open_model(path):
		printerr(status.text)
		get_tree().quit(1)
		return
	if not cfg.is_empty():
		studio.from_config(cfg)
	if args.has("name"):
		studio.unit_name = args["name"]
	DirAccess.make_dir_recursive_absolute(args["out"])
	var err: String = await studio.render_sprites(args["out"])
	print("render: ", err if err != "" else "done " + args["out"])
	get_tree().quit(0 if err == "" else 1)


# --- Textures and light ------------------------------------------------------------

const MAP_NAMES := {"albedo": "Колір", "normal": "Нормалі", "ao": "Запечені тіні (AO)",
	"roughness": "Шорсткість", "metallic_map": "Металевість"}
const LOOK_ROWS := [
	["ao_intensity", "Тіні дрібних деталей", 0.0, 16.0, 0.1],
	["ao_radius", "Радіус тіней деталей, м", 0.05, 1.5, 0.01],
	["ao_power", "Різкість тіней деталей", 0.5, 4.0, 0.05],
	["ao_light_affect", "Тіні деталей на сонці", 0.0, 1.0, 0.01],
	["sun_energy", "Сонце", 0.5, 4.0, 0.05],
	["sun_blur", "М'якість тіні сонця", 0.0, 3.0, 0.05],
	["shadow_opacity", "Тінь на землі", 0.0, 1.0, 0.01],
	["fill_energy", "Підсвітка з тіні", 0.0, 1.5, 0.01],
	["ambient", "Розсіяне світло", 0.0, 1.0, 0.01],
	["exposure", "Експозиція", 0.5, 2.0, 0.01],
	["contrast", "Контраст", 0.5, 2.0, 0.01],
	["saturation", "Насиченість", 0.0, 2.0, 0.01]]


func _build_textures(panel: Control) -> void:
	var s := _section(panel, "Текстури")
	var row := HBoxContainer.new()
	s.add_child(row)
	var l := Label.new()
	l.text = "Для частини"
	l.custom_minimum_size.x = 170
	row.add_child(l)
	var target := OptionButton.new()
	target.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	target.item_selected.connect(func(i):
		tex_target = target.get_item_metadata(i)
		_sync())
	row.add_child(target)
	ui["tex_target"] = target
	for m in UnitStudio.TEXTURE_MAPS:
		row = HBoxContainer.new()
		s.add_child(row)
		l = Label.new()
		l.text = MAP_NAMES[m]
		l.custom_minimum_size.x = 170
		row.add_child(l)
		var pick := Button.new()
		pick.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		pick.clip_text = true
		pick.pressed.connect(func():
			_tex_map = m
			dlg_tex.popup_centered_ratio(0.7))
		row.add_child(pick)
		ui["tex_" + m] = pick
		var clear := Button.new()
		clear.text = "✕"
		clear.tooltip_text = "Прибрати"
		clear.pressed.connect(func(): _set_tex_field(m, null))
		row.add_child(clear)
	row = HBoxContainer.new()
	s.add_child(row)
	l = Label.new()
	l.text = "Відтінок текстури"
	l.custom_minimum_size.x = 170
	row.add_child(l)
	var tint := ColorPickerButton.new()
	tint.custom_minimum_size = Vector2(80, 28)
	tint.color_changed.connect(func(c): _set_tex_field("tint", UnitStudio._rgb(c)))
	row.add_child(tint)
	ui["tex_tint"] = tint
	_slider_row(s, "tex_normal_strength", "Сила нормалей", 0, 6, 0.05,
		func(v): _set_tex_field("normal_strength", v))
	_slider_row(s, "tex_ao_strength", "Сила запечених тіней", 0, 1, 0.01,
		func(v): _set_tex_field("ao_strength", v))
	_slider_row(s, "tex_metallic", "Металевість", 0, 1, 0.01, func(v): _set_tex_field("metallic", v))
	_slider_row(s, "tex_uv_scale", "Масштаб текстури", 0.1, 8, 0.05, func(v): _set_tex_field("uv_scale", v))
	var flip := CheckBox.new()
	flip.text = "Нормалі у форматі DirectX (перевернути зелений)"
	flip.toggled.connect(func(on):
		if not _syncing:
			_set_tex_field("flip_green", on))
	s.add_child(flip)
	ui["tex_flip"] = flip
	var chk := CheckBox.new()
	chk.text = "Шахова сітка: перевірка розгортки (UV)"
	chk.toggled.connect(func(on):
		studio.checker = on
		studio.apply_materials())
	s.add_child(chk)
	var note := Label.new()
	note.text = "Набір «Вся модель» діє на всі частини; набір частини його доповнює. PNG, JPG, WebP, TGA."
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.modulate = Color(1, 1, 1, 0.7)
	s.add_child(note)
	dlg_tex = _dialog(FileDialog.FILE_MODE_OPEN_FILE, ["*.png, *.jpg, *.jpeg, *.webp, *.tga, *.bmp ; Текстури"],
		"tex_dir", func(p):
			if studio.load_texture(p) == null:
				status.text = "Не вдалося прочитати текстуру %s" % p.get_file()
				return
			_set_tex_field(_tex_map, p))


func _set_tex_field(field: String, value) -> void:
	if _syncing:
		return
	var t: Dictionary = studio.textures.get(tex_target, {})
	if value == null:
		t.erase(field)
	else:
		t[field] = value
	if t.is_empty():
		studio.textures.erase(tex_target)
	else:
		studio.textures[tex_target] = t
	studio.apply_materials()
	_sync()


func _build_look(panel: Control) -> void:
	var s := _section(panel, "Світло і тіні")
	for r in LOOK_ROWS:
		var key: String = r[0]
		_slider_row(s, "look_" + key, r[1], r[2], r[3], r[4], func(v):
			studio.look[key] = v
			studio.apply_look())
	_button(s, "look_reset", "Стандартні значення", func():
		studio.look = UnitStudio.LOOK_DEFAULTS.duplicate()
		studio.apply_look()
		_sync())
	var note := Label.new()
	note.text = "Світло однакове для прев'ю і рендера. Для всіх юнітів гри краще тримати однакові значення."
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.modulate = Color(1, 1, 1, 0.7)
	s.add_child(note)


func _sync_textures() -> void:
	var target: OptionButton = ui["tex_target"]
	var keys := [UnitStudio.ALL_PARTS]
	for g in studio.groups:
		keys.append(g["key"])
	if not tex_target in keys:
		tex_target = UnitStudio.ALL_PARTS
	target.clear()
	for i in keys.size():
		target.add_item("Вся модель" if keys[i] == UnitStudio.ALL_PARTS else keys[i])
		target.set_item_metadata(i, keys[i])
		if keys[i] == tex_target:
			target.select(i)
	var own: Dictionary = studio.textures.get(tex_target, {})
	var t := studio.texture_set(tex_target)
	for m in UnitStudio.TEXTURE_MAPS:
		var path: String = t.get(m, "")
		var b: Button = ui["tex_" + m]
		b.text = "Вибрати…" if path == "" else path.get_file() + ("" if own.has(m) else "  (вся модель)")
		b.tooltip_text = path
	ui["tex_tint"].color = UnitStudio._color(t["tint"])
	for k in ["normal_strength", "ao_strength", "metallic", "uv_scale"]:
		ui["tex_" + k].value = t[k]
		ui["tex_" + k + "_spin"].value = t[k]
	ui["tex_flip"].set_pressed_no_signal(t["flip_green"])
	for r in LOOK_ROWS:
		ui["look_" + r[0]].value = studio.look[r[0]]
		ui["look_" + r[0] + "_spin"].value = studio.look[r[0]]
