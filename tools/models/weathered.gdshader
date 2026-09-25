// Weathering over a model's own textures: faded paint, rain streaks on
// vertical faces, dust on top surfaces, mud on the running gear and lower
// hull, chipped paint. Masks come from world-space noise, so no extra UV
// work is needed on imported models. Heights are in metres (ground = 0).
shader_type spatial;
render_mode diffuse_burley, cull_disabled;  // AI-generated meshes may have flipped faces

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap, repeat_enable;
uniform bool has_normal = false;
uniform float normal_depth = 1.8;  // exaggerate panel lines and small details
uniform vec3 tint = vec3(1.0);
uniform sampler2D noise_lo : filter_linear_mipmap, repeat_enable;  // big blotches
uniform sampler2D noise_hi : filter_linear_mipmap, repeat_enable;  // fine grain

// Colours are linear (defaults written here are not sRGB-converted).
uniform vec3 mud_color = vec3(0.035, 0.025, 0.013);
uniform vec3 dry_mud_color = vec3(0.11, 0.08, 0.045);
uniform vec3 dust_color = vec3(0.17, 0.15, 0.10);
uniform vec3 chip_color = vec3(0.02, 0.019, 0.017);
uniform float mud_height = 1.45;
uniform float mud_amount : hint_range(0.0, 1.0) = 0.85;
uniform float dust_amount : hint_range(0.0, 1.0) = 0.55;
uniform float chip_amount : hint_range(0.0, 1.0) = 0.8;
uniform float streak_amount : hint_range(0.0, 1.0) = 0.7;

varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

float tri(sampler2D t, vec3 p, vec3 n, float s) {
	vec3 b = pow(abs(n), vec3(4.0));
	b /= (b.x + b.y + b.z);
	return texture(t, p.zy * s).r * b.x + texture(t, p.xz * s).r * b.y + texture(t, p.xy * s).r * b.z;
}

void fragment() {
	vec3 n = normalize(wnrm);
	vec3 base = texture(albedo_tex, UV).rgb * tint;
	float lo = tri(noise_lo, wpos, n, 0.3);
	float hi = tri(noise_hi, wpos, n, 1.8);

	// Uneven, sun-faded paint.
	base *= mix(0.88, 1.08, lo);

	// Rain streaks running down vertical faces.
	float vertical = 1.0 - abs(n.y);
	float streak = texture(noise_hi, vec2((wpos.x + wpos.z) * 2.5, wpos.y * 0.12)).r;
	base *= mix(1.0, mix(0.72, 1.08, streak), vertical * streak_amount);

	// Dust settled on surfaces facing up.
	float up = smoothstep(0.45, 0.95, n.y);
	float dust = up * (smoothstep(0.5, 0.85, hi) * 0.5 + lo * 0.5);
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
	ROUGHNESS = clamp(mix(0.82, 0.97, mud) - chips * 0.4, 0.0, 1.0);
	METALLIC = chips * 0.55;
	if (has_normal) {
		NORMAL_MAP = texture(normal_tex, UV).rgb;
		NORMAL_MAP_DEPTH = normal_depth;
	}
}
