class_name MapBackdrop
extends Control
## The map under the preview, drawn like the game draws it: top-down grass from
## the baked test map, dashed hex grid and the side ring, at the scale of the
## 3D camera above it (origin = the centre of the middle hex).

const GAME_PX_PER_M := 48.0 / 5.5  # Hex.SIZE / hex radius: the game's map scale at zoom 1
const GRID_COLOR := Color(1, 1, 1, 0.13)  # scripts/map_view.gd
const RING_PX := 34.0  # scripts/game.gd RING_RADIUS at zoom 1

var zoom_m := 22.0
var side := 0
var show_grid := true
var _grass: ImageTexture
var _grass_m := 0.0


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	# Mirror the grass 2 x 2 so it tiles without seams.
	var img: Image = (load("res://assets/grass.jpg") as Texture2D).get_image()
	img.convert(Image.FORMAT_RGB8)
	var big := UnitStudio._mirrored(img)
	big.generate_mipmaps()
	_grass = ImageTexture.create_from_image(big)
	_grass_m = UnitStudio.GRASS_M * 2.0
	resized.connect(queue_redraw)


## Screen pixels per metre on the ground (same horizontal scale as the 3D view).
func px_per_m() -> float:
	return size.y / (zoom_m * sin(deg_to_rad(UnitStudio.ELEVATION)))


func _draw() -> void:
	var s := px_per_m()
	var c := size / 2.0
	var k := s / GAME_PX_PER_M  # line widths scale like the game's world-space lines
	var texel := _grass_m / _grass.get_width() * s
	draw_set_transform(c, 0.0, Vector2(texel, texel))
	var half := size / 2.0 / texel
	var tw := float(_grass.get_width())
	var start := Vector2(floorf(-half.x / tw) * tw, floorf(-half.y / tw) * tw)
	draw_texture_rect(_grass, Rect2(start, Vector2(ceilf(size.x / texel / tw) + 2, ceilf(size.y / texel / tw) + 2) * tw), true)
	draw_set_transform(Vector2.ZERO)
	if show_grid:
		var r := UnitStudio.HEX_R
		var w := sqrt(3.0) * r
		var rows := ceili(size.y / s / (1.5 * r) / 2.0) + 1
		var cols := ceili(size.x / s / w / 2.0) + 1
		for row in range(-rows, rows + 1):
			for q in range(-cols, cols + 1):
				var hc := Vector2(w * (q + 0.5 * (absi(row) % 2)), 1.5 * r * row)
				for i in 6:
					var a0 := deg_to_rad(60.0 * i - 90.0)
					var a1 := deg_to_rad(60.0 * (i + 1) - 90.0)
					draw_dashed_line(c + (hc + Vector2(cos(a0), sin(a0)) * r) * s,
						c + (hc + Vector2(cos(a1), sin(a1)) * r) * s, GRID_COLOR, 1.5 * k, 5.0 * k)
	var squash := sin(deg_to_rad(UnitStudio.ELEVATION))
	var pts := PackedVector2Array()
	for i in 49:
		var a := TAU * i / 48.0
		pts.append(c + Vector2(cos(a), sin(a) * squash) * RING_PX * k)
	draw_polyline(pts, UnitStudio.SIDE_COLORS[side], 3.0 * k, true)
