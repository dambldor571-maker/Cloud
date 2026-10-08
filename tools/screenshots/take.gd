extends SceneTree
## Dev tool: renders the main menu and the campaign map to PNG files.
## xvfb-run godot --path . --rendering-driver opengl3 --resolution 1280x720 \
##   --script res://tools/screenshots/take.gd -- <out_dir>

func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var out: String = OS.get_cmdline_user_args()[0] if OS.get_cmdline_user_args().size() > 0 else "/tmp"
	var app: Node = load("res://scenes/main.tscn").instantiate()
	root.add_child(app)
	await _frames(5)
	await _shot(out + "/01_main.png")
	app._show_help()
	await _frames(3)
	await _shot(out + "/02_help.png")
	app._start_campaign({})
	await _frames(10)
	var b: Battle = app.battle
	b.hud.banner.hide()
	await _shot(out + "/03_campaign.png")
	for u in b.units_of(0):
		if u.type == "ifv":
			b._select(u)
			break
	await _frames(3)
	await _shot(out + "/04_select.png")
	b._open_hq()
	await _frames(3)
	await _shot(out + "/05_hq.png")
	b._open_cards()
	await _frames(3)
	await _shot(out + "/06_cards.png")
	b._deselect()
	b._open_build(b.hq[0][0])
	await _frames(3)
	await _shot(out + "/07_build.png")
	b.camera.zoom = Vector2(0.3, 0.3)
	b.camera.position = b._map_rect().get_center()
	b._deselect()
	await _frames(3)
	await _shot(out + "/08_overview.png")
	quit()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _shot(path: String) -> void:
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(path)
	print("saved ", path)
