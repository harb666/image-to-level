// image-to-level Stage 26: TV static on screens (UNTESTED in Godot here).
// Applied by apply_effects.gd as a material_override on every mesh whose material is the effect's target_material;
// albedo_tex = the GLB's base colour texture (the screen picture). Snow cells change fps times a second, a dark bar
// rolls down, and every signal_every seconds the picture breaks through for signal_len seconds.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, unshaded;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float amount = 0.85;        // share of static over the picture (0 = clean picture, 1 = only snow)
uniform float grain = 120.0;        // snow cells per UV unit (vertical); x gets 3x (atlas halves are half as wide)
uniform float fps = 18.0;
uniform float signal_every = 6.0;   // seconds
uniform float signal_len = 1.4;     // seconds the picture comes through
uniform float roll_speed = 0.25;    // rolling bar, screens per second
uniform float glow = 1.0;
uniform float seed = 0.0;

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void fragment() {
	vec3 pic = texture(albedo_tex, UV).rgb;
	float f = mod(floor(TIME * fps), 997.0);  // bounded: sin() hash stays precise on mobile GPUs
	vec2 cell = floor(UV * vec2(grain * 3.0, grain));
	float n = hash(cell + vec2(f * 13.1, f * 7.7) + seed);
	float line = 0.75 + 0.25 * hash(vec2(cell.y, f + seed));  // horizontal line jitter
	float ph = mod(TIME + seed * 1.7, signal_every);
	float sig = smoothstep(0.0, 0.25, ph) * (1.0 - smoothstep(signal_len - 0.25, signal_len, ph));
	float m = amount * (1.0 - 0.8 * sig);
	float bar = smoothstep(0.0, 0.08, abs(fract(UV.y + TIME * roll_speed) - 0.5));
	vec3 col = mix(pic, vec3(n * line), m) * mix(0.65, 1.0, bar);
	ALBEDO = col * glow;
}
