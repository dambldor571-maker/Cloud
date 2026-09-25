// Paint and weathering for vehicle models. The base is either the model's own
// texture or our own paint (flat colour, rubber tyres on road wheels, track
// links). Weathering on top: faded paint, rain streaks on vertical faces, dust
// on top surfaces, mud on the running gear and lower hull, chipped paint.
// Masks come from world-space noise, so no extra UV work is needed on imported
// models. Heights are in metres (ground = 0).
shader_type spatial;
render_mode diffuse_burley, cull_disabled;  // AI-generated meshes may have flipped faces

uniform bool has_albedo = true;
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform vec3 base_color = vec3(1.0);  // linear; used when has_albedo is false
// Road wheel: dark rubber band beyond tyre_radius from the wheel axis (local Z).
uniform bool rubber_tyre = false;
uniform vec3 wheel_center = vec3(0.0);
uniform float tyre_radius = 0.3;
uniform vec3 rubber_color = vec3(0.012, 0.012, 0.011);
// Track: links along UV.x (the track loop), grousers across.
uniform bool track_links = false;
uniform float links_per_uv = 75.0;
// Painted-on detail for top surfaces (see tools/models/make_t72_hull_detail.py):
// a top-down map in model coordinates. R = height, G = cavity, B = bare metal.
uniform bool has_detail = false;
uniform sampler2D detail_tex : filter_linear_mipmap;
uniform vec4 detail_rect = vec4(-1.0, -1.0, 1.0, 1.0);  // x0, z0, x1, z1 in model units
uniform float detail_height = 0.05;
// Extra light for parts that face away from the sun but must stay readable
// (running gear on the sprite's visible side); fraction of the albedo.
uniform float lift = 0.0;  // metres of relief for the full 0..1 height range
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap, repeat_enable;
uniform bool has_normal = false;
uniform float normal_depth = 1.8;  // exaggerate panel lines and small details
uniform vec3 tint = vec3(1.0);
uniform sampler2D noise_lo : filter_linear_mipmap, repeat_enable;  // big blotches
uniform sampler2D noise_hi : filter_linear_mipmap, repeat_enable;  // fine grain

// Colours are linear (defaults written here are not sRGB-converted).
uniform vec3 mud_color = vec3(0.035, 0.025, 0.013);
uniform vec3 dry_mud_color = vec3(0.11, 0.08, 0.045);
uniform vec3 dust_color = vec3(0.12, 0.105, 0.07);
uniform vec3 chip_color = vec3(0.02, 0.019, 0.017);
uniform float mud_height = 1.45;
uniform float mud_amount : hint_range(0.0, 1.0) = 0.85;
uniform float dust_amount : hint_range(0.0, 1.0) = 0.55;
uniform float chip_amount : hint_range(0.0, 1.0) = 0.8;
uniform float streak_amount : hint_range(0.0, 1.0) = 0.7;

varying vec3 wpos;
varying vec3 wnrm;
varying vec3 opos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	opos = VERTEX;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

float tri(sampler2D t, vec3 p, vec3 n, float s) {
	vec3 b = pow(abs(n), vec3(4.0));
	b /= (b.x + b.y + b.z);
	return texture(t, p.zy * s).r * b.x + texture(t, p.xz * s).r * b.y + texture(t, p.xy * s).r * b.z;
}

void fragment() {
	vec3 n = normalize(wnrm);
	vec3 base = has_albedo ? texture(albedo_tex, UV).rgb * tint : base_color;
	// Detail relief on surfaces facing up: bend the normal by the height slope
	// (so the sun lights and shades it in any facing) and darken cavities.
	float detail_w = 0.0;
	float metal_mask = 0.0;
	if (has_detail) {
		vec2 duv = (opos.xz - detail_rect.xy) / (detail_rect.zw - detail_rect.xy);
		detail_w = smoothstep(0.6, 0.9, n.y) * step(0.0, duv.x) * step(duv.x, 1.0) * step(0.0, duv.y) * step(duv.y, 1.0);
		if (detail_w > 0.0) {
			vec2 texel = 1.0 / vec2(textureSize(detail_tex, 0));
			vec3 d = texture(detail_tex, duv).rgb;
			float hx = texture(detail_tex, duv + vec2(texel.x, 0.0)).r - texture(detail_tex, duv - vec2(texel.x, 0.0)).r;
			float hz = texture(detail_tex, duv + vec2(0.0, texel.y)).r - texture(detail_tex, duv - vec2(0.0, texel.y)).r;
			vec2 metres_per_texel = (detail_rect.zw - detail_rect.xy) * texel;
			vec3 n_obj = normalize(vec3(-hx * detail_height / (2.0 * metres_per_texel.x), 1.0,
				-hz * detail_height / (2.0 * metres_per_texel.y)));
			vec3 n_view = normalize((VIEW_MATRIX * MODEL_MATRIX * vec4(n_obj, 0.0)).xyz);
			NORMAL = normalize(mix(NORMAL, n_view, detail_w));
			metal_mask = d.b * detail_w;
			base = mix(base, base * 0.55, metal_mask);  // grille mesh reads darker than paint
			base *= mix(1.0, d.g, detail_w);  // baked cavity shading in seams and corners
		}
	}
	float rubber = 0.0;
	if (rubber_tyre) {
		rubber = smoothstep(tyre_radius - 0.01, tyre_radius + 0.01, length((opos - wheel_center).xy));
		base = mix(base, rubber_color, rubber);
	}
	float link_gap = 0.0;
	if (track_links) {
		float f = fract(UV.x * links_per_uv);
		link_gap = 1.0 - smoothstep(0.0, 0.12, f) * smoothstep(1.0, 0.82, f);  // dark gap between links
		float grouser = smoothstep(0.35, 0.45, f) * smoothstep(0.65, 0.55, f);  // raised bar mid-link
		base *= mix(1.0, 0.35, link_gap) * mix(1.0, 1.35, grouser);
	}
	float lo = tri(noise_lo, wpos, n, 0.3);
	float hi = tri(noise_hi, wpos, n, 1.8);

	// Uneven, sun-faded paint.
	base *= mix(0.93, 1.05, lo);

	// Rain streaks running down vertical faces.
	float vertical = 1.0 - abs(n.y);
	float streak = texture(noise_hi, vec2((wpos.x + wpos.z) * 2.5, wpos.y * 0.12)).r;
	base *= mix(1.0, mix(0.72, 1.08, streak), vertical * streak_amount);

	// Dust settled on surfaces facing up.
	float up = smoothstep(0.45, 0.95, n.y);
	// Fine grain, gathered a little more in some areas; no big pale blotches.
	float dust = up * (smoothstep(0.62, 0.9, hi) * 0.6 + smoothstep(0.55, 0.85, lo) * 0.2);
	base = mix(base, dust_color, dust * dust_amount);

	// Mud: thick near the ground, ragged upper edge, dry and pale at its top.
	float h = clamp(1.0 - wpos.y / mud_height, 0.0, 1.0);
	float mud = smoothstep(0.3, 0.65, h + (lo - 0.5) * 0.7 + (hi - 0.5) * 0.35) * mud_amount;
	vec3 mud_col = mix(dry_mud_color, mud_color, smoothstep(0.3, 0.6, h)) * mix(0.8, 1.15, hi);
	base = mix(base, mud_col, mud);

	// Chipped paint showing dark metal, mostly on raised, exposed spots.
	float grain = tri(noise_hi, wpos * 3.1, n, 1.8);
	float chips = smoothstep(0.68, 0.74, grain * 0.8 + hi * 0.2) * (1.0 - mud) * chip_amount;
	base = mix(base, chip_color, chips);

	ALBEDO = base;
	EMISSION = base * lift;
	ROUGHNESS = clamp(mix(0.82, 0.97, mud) - chips * 0.4 + rubber * 0.1, 0.0, 1.0);
	METALLIC = chips * 0.55 + (track_links ? 0.35 * (1.0 - mud) : 0.0);
	if (has_normal) {
		NORMAL_MAP = texture(normal_tex, UV).rgb;
		NORMAL_MAP_DEPTH = normal_depth;
	}
}
