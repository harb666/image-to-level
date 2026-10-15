// Stage 61: parts added on a working assembly line (effect "assembly_line"): the part sits on every parcel but only
// shows once its parcel has passed the station's arm - fragments behind the world plane (dot(world, plane.xyz) < plane.w)
// are discarded. Emissive parts, so unshaded: albedo = texture * tint, like the glow materials.
shader_type spatial;
render_mode unshaded, cull_back;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform vec4 tint : source_color = vec4(1.0);
uniform vec4 plane = vec4(0.0, 0.0, 1.0, 0.0);
uniform float glow = 1.0;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	if (dot(wpos, plane.xyz) < plane.w) discard;
	ALBEDO = texture(albedo_tex, UV).rgb * tint.rgb * glow;
}
