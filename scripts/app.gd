extends Node
## Game shell: main menu and help; starts or continues the campaign on the global
## map. `-- --autotest` plays the campaign AI vs AI and checks save/load.

var ui: CanvasLayer
var page: Control
var battle: Battle
var autotest := false
var _autotest_stage := 0  # campaigns finished


func _ready() -> void:
	autotest = "--autotest" in OS.get_cmdline_user_args()
	if autotest:
		_run_autotest()
		return
	ui = CanvasLayer.new()
	add_child(ui)
	_show_main()


# --- Pages ------------------------------------------------------------------

func _new_page() -> VBoxContainer:
	if page:
		page.queue_free()
	page = Control.new()
	page.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	page.theme = UiKit.theme()
	ui.add_child(page)
	var bg := Backdrop.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	page.add_child(bg)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 28)
	page.add_child(margin)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 14)
	margin.add_child(col)
	return col


func _show_main() -> void:
	var col := _new_page()
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 48)
	col.add_child(row)
	var icon := TextureRect.new()
	icon.texture = load("res://assets/branding/icon_512.png")
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.custom_minimum_size = Vector2(300, 300)
	row.add_child(icon)
	var menu := VBoxContainer.new()
	menu.alignment = BoxContainer.ALIGNMENT_CENTER
	menu.add_theme_constant_override("separation", 14)
	row.add_child(menu)
	var title := UiKit.label("HEXFRONT", 72, UiKit.SAND)
	title.autowrap_mode = TextServer.AUTOWRAP_OFF
	menu.add_child(title)
	menu.add_child(UiKit.label("Modern War · покрокова стратегія", 26, Color(1, 1, 1, 0.7)))
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 12)
	menu.add_child(gap)
	var save := Battle.read_save()
	if not save.is_empty():
		var cont := UiKit.button("Продовжити · хід %d" % int(save["turn"]), Vector2(420, 72), UiKit.GOOD)
		cont.pressed.connect(func() -> void: _start_campaign(save))
		menu.add_child(cont)
	var fresh := UiKit.button("Нова кампанія", Vector2(420, 68), UiKit.BASE if not save.is_empty() else UiKit.GOOD)
	fresh.pressed.connect(func() -> void:
		if save.is_empty():
			_start_campaign({})
		else:
			_confirm_new())
	menu.add_child(fresh)
	var help := UiKit.button("Як грати", Vector2(420, 64))
	help.pressed.connect(_show_help)
	menu.add_child(help)


func _confirm_new() -> void:
	var col := _new_page()
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	var box := UiKit.panel(24)
	box.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	col.add_child(box)
	var inner := VBoxContainer.new()
	inner.add_theme_constant_override("separation", 16)
	box.add_child(inner)
	inner.add_child(UiKit.label("Почати нову кампанію?\nПоточне збереження буде втрачено.", 28))
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	inner.add_child(row)
	var yes := UiKit.button("Так, почати", Vector2(240, 66), UiKit.BAD)
	yes.pressed.connect(func() -> void: _start_campaign({}))
	row.add_child(yes)
	var no := UiKit.button("Назад", Vector2(240, 66))
	no.pressed.connect(_show_main)
	row.add_child(no)


func _show_help() -> void:
	var col := _new_page()
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 16)
	col.add_child(head)
	var back := UiKit.button("‹ Назад", Vector2(150, 60))
	back.pressed.connect(_show_main)
	head.add_child(back)
	head.add_child(UiKit.label("Як грати", 36, UiKit.GOLD))
	var sc := ScrollContainer.new()
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(sc)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 10)
	sc.add_child(list)
	var lines := [
		"• Одна велика кампанія на глобальній карті без обмеження ходів. Мета — захопити всі ключові точки противника (міста з зіркою на прапорі). Втратите свої — поразка.",
		"• Тап по своєму юніту — вибір. Білі гекси — куди можна піти, червоні — кого атакувати, зелені — кого відремонтувати. Тап по клітинці → «Рух».",
		"• Спершу рух, потім атака. Після атаки рухатися не можна (крім ударного вертольота). САУ та РСЗВ стріляють лише з місця.",
		"• Піхота, танк, БМП і бронемашина відповідають вогнем. Артилерія, вертоліт і логістика — ні.",
		"• Міста захоплює тільки піхота. Тап по своєму порожньому місту — купівля військ (одна покупка на місто за хід). Вертольоти й штурмовики — лише на аеродромах.",
		"• Дохід: %d $ щоходу гарантовано плюс міста. Армія має ліміт (%d + %d за кожне місто); понад ліміт дохід зменшується." % [
			Rules.BASE_INCOME, Rules.ARMY_LIMIT_BASE, Rules.ARMY_LIMIT_PER_CITY],
		"• ППО не б'є по наземних цілях, але автоматично перехоплює авіацію, що атакує в зоні її дії.",
		"• РСЗВ уражає й сусідні гекси — обережно зі своїми.",
		"• Піхота, що цілий хід стояла й не стріляла, окопується: +%d захисту." % Rules.ENTRENCH_DEF,
		"• Юніти набирають досвід: до трьох зірок ветерана, кожна +%d%% атаки й захисту." % roundi(Rules.STAR_BONUS * 100),
		"• «Засоби» — оперативні засоби за очки командування: +%d за хід, максимум %d." % [Rules.CP_PER_TURN, Rules.CP_MAX],
		"• «Штаб» — наймання й підвищення командирів за медалі. Медалі дають за захоплені міста (%d), ключові точки (%d) і знищені юніти (%d). Командира призначають вибраному юніту кнопкою «Командир…»." % [
			Rules.MEDALS_CITY, Rules.MEDALS_KEY_POINT, Rules.MEDALS_KILL],
		"• Гра зберігається автоматично на початку кожного вашого ходу.",
		"• Перетягування — рух карти, два пальці або колесо миші — масштаб.",
	]
	for l in lines:
		list.add_child(UiKit.label(l, 23))


# --- Campaign ---------------------------------------------------------------

func _start_campaign(save: Dictionary) -> void:
	if page:
		page.queue_free()
		page = null
	_end_battle()
	battle = Battle.new()
	battle.saved_state = save
	battle.autotest = autotest
	battle.leave_requested.connect(_on_leave)
	battle.new_campaign_requested.connect(func() -> void: _start_campaign.call_deferred({}))
	battle.finished.connect(_on_finished)
	add_child(battle)


func _end_battle() -> void:
	if battle:
		battle.game_id += 1  # stops a running AI coroutine
		battle.queue_free()
		battle = null


func _on_leave() -> void:
	if battle and battle.winner < 0 and battle.human_sides[battle.current_side] and not battle.busy:
		battle.save_state()
	_end_battle()
	_show_main()


func _on_finished(result: Dictionary) -> void:
	if not autotest:
		return
	var who := "Сині" if result["won"] else ("нічия" if battle.winner == 2 else "Червоні")
	print("[autotest] campaign %d: %s, хід %d (%s) · юніти %d/%d · міста %d/%d" % [_autotest_stage + 1, who,
		result["turn"], result["reason"], battle.units_of(0).size(), battle.units_of(1).size(),
		battle.cities_of(0).size(), battle.cities_of(1).size()])
	_check_save_load.call_deferred()


## Restores the final state into a fresh campaign and compares it.
func _check_save_load() -> void:
	var d := battle.to_dict()
	var cities := battle.cities_of(0).size()
	_start_campaign(JSON.parse_string(JSON.stringify(d)))
	battle.finished.disconnect(_on_finished)
	var ok: bool = battle.units.size() == d["units"].size() and battle.cities_of(0).size() == cities \
		and battle.turn == int(d["turn"]) and battle.to_dict()["units"] == d["units"]
	print("[autotest] save/load: %s (turn %d, units %d)" % ["ok" if ok else "MISMATCH", battle.turn, battle.units.size()])
	if not ok:
		push_error("save/load mismatch")
	_end_battle()
	_autotest_stage += 1
	_run_autotest.call_deferred()


## Two full AI-vs-AI campaigns, each followed by a save/load check.
func _run_autotest() -> void:
	if _autotest_stage >= 2:
		print("[autotest] done")
		get_tree().quit()
		return
	_start_campaign({})


## Dark field with a faint hex pattern behind the menus.
class Backdrop extends Control:
	func _draw() -> void:
		var r := get_rect()
		draw_rect(r, Color(0.07, 0.09, 0.12))
		var s := 46.0
		var w := s * sqrt(3.0)
		var row := 0
		var y := 0.0
		while y < r.size.y + s:
			var x := (w / 2.0) if row % 2 == 1 else 0.0
			while x < r.size.x + w:
				var pts := Hex.corners(Vector2(x, y), s - 3)
				pts.append(pts[0])
				var k := 0.03 + 0.03 * sin(x * 0.01 + y * 0.013)
				draw_polyline(pts, Color(0.92, 0.87, 0.72, k), 1.5)
				x += w
			y += s * 1.5
			row += 1
		draw_rect(Rect2(0, r.size.y * 0.55, r.size.x, r.size.y * 0.45), Color(0, 0, 0, 0.25))
