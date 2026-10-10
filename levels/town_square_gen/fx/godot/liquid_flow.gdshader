// image-to-level Stage 4: liquid flowing down a fall / along a pipe (UNTESTED in Godot here).
// uv_speed = flow speed (m/s) / material tile size (m). If it flows the wrong way, negate uv_speed.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float uv_speed = 0.25;
uniform float wobble = 0.02;
uniform float glow_energy = 1.2;
uniform vec3 glow_tint : source_color = vec3(1.0);

void fragment() {
	vec2 uv = UV;
	uv.x += sin(uv.y * 9.0 + TIME * 3.0) * wobble;
	uv.y -= TIME * uv_speed;
	vec3 col = texture(albedo_tex, uv).rgb;
	ALBEDO = col;
	ROUGHNESS = 0.1;
	EMISSION = col * glow_tint * glow_energy;
}
