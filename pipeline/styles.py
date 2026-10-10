"""Reusable ART STYLE presets (opt-in per level: scene_spec "art_style": "<name>").

A preset is a scene-spec FRAGMENT deep-merged UNDER the level's own spec (the spec always wins), plus a few
operations a plain merge cannot express. Levels without "art_style" are untouched, so existing styles keep working.

  materials.roles       palette + flags for every material role (e.g. "toon": true -> flat, inked, non-metallic)
  world.materials       terrain layer palette        world.scatter_replace   kind -> kind (e.g. trees -> alien satellites)
  world.scatter_style   prop palette for scatter     atmosphere              sky / planet / clouds / fog / lighting
  background_types      per background layer TYPE overrides (colours, fades, options); background_add: extra layers
  structures_decor      decor kit added to structures of a kind (towers get antennas, ...)
  render                level.json "style": toon shading + outline shells (build_level / viewer / Godot metadata)

  python3 pipeline/styles.py                      # list presets
"""
import copy, json

ALIEN_CARTOON = {
    "description": "Invader-Zim-like alien-industrial cartoon: purple-black inked structures, red accents, hot-pink sky, "
                   "striped pink planet, radioactive-green abyss / falls, alien satellites instead of trees.",
    "materials": {"variation": False, "roles": {
        "deck":        {"type": "scifi_floor", "color": [0.33, 0.28, 0.42], "tile_m": 4.0, "wear": 0.0, "toon": True, "toon_flatten": 0.05},
        "structure":   {"type": "machinery_panel", "color": [0.33, 0.26, 0.42], "tile_m": 4.0, "accent": [1.0, 0.1, 0.18], "emissive": [1, 1, 1], "toon": True},
        "structure_b": {"type": "hull_plating", "color": [0.3, 0.23, 0.4], "tile_m": 4.0, "wear": 0.2, "toon": True},
        "wall":        {"type": "hull_plating", "color": [0.36, 0.28, 0.46], "tile_m": 4.0, "wear": 0.2, "toon": True},
        "frame":       {"type": "industrial_metal", "color": [0.2, 0.15, 0.26], "tile_m": 3.0, "toon": True},
        "trim":        {"type": "trim_light", "color": [0.22, 0.17, 0.28], "tile_m": 1.2, "accent": [1.0, 0.08, 0.2], "emissive": [1, 1, 1], "toon": True},
        "glow":        {"type": "glow", "color": [1.0, 0.16, 0.3], "tile_m": 2.0, "emissive": [1.0, 0.12, 0.25]},
        "accent":      {"type": "banner", "color": [0.82, 0.06, 0.12], "tile_m": 2.0, "emissive": [0.55, 0.04, 0.1], "toon": True},
        "rail":        {"type": "painted_metal", "color": [0.85, 0.08, 0.1], "tile_m": 2.0, "res": 128, "wear": 0.02, "toon": True},
        "grate":       {"type": "grating", "color": [0.36, 0.3, 0.46], "tile_m": 2.0, "toon": True},
        "machine":     {"type": "machinery_panel", "color": [0.3, 0.24, 0.38], "tile_m": 2.0, "accent": [0.45, 1.0, 0.2], "emissive": [1, 1, 1], "toon": True},
        "stripe":      {"type": "chevron", "color": [0.95, 0.12, 0.25], "tile_m": 1.5, "res": 128, "dark": [0.08, 0.05, 0.1], "wear": 0.1, "toon": True},
        "water":       {"type": "toxic", "color": [0.45, 1.0, 0.2], "tile_m": 3.0, "emissive": [0.42, 1.0, 0.15]},
    }},
    "world": {
        "materials": {"rock":  {"type": "rock", "color": [0.3, 0.23, 0.38], "tile_m": 10.0, "res": 128, "toon": True},
                      "grass": {"type": "moss", "color": [0.3, 0.24, 0.38], "tile_m": 5.0, "res": 128, "toon": True},
                      "sand":  {"type": "toxic", "color": [0.4, 0.95, 0.2], "tile_m": 6.0, "res": 128, "emissive": [0.3, 0.8, 0.12]}},
        "scatter_replace": {"conifer": "sat_spire", "broadleaf": "sat_dish", "bush": "sat_pod", "palm": "sat_dish", "dead_tree": "sat_spire",
                            "alien_plant": "sat_pod"},
        "scatter_style": "alien_cartoon", "scatter_density_mult": 0.5, "scatter_scale": [1.4, 2.1],
    },
    "atmosphere": {
        "sky": "sunset",
        "sky_overrides": {"zenith": [0.2, 0.03, 0.22], "upper": [0.62, 0.08, 0.42], "horizon": [1.0, 0.42, 0.42], "below": [0.18, 0.3, 0.12],
                          "clouds": {"coverage": 0.5, "scale": 2.2, "stretch": 3.0, "lit": [1.0, 0.3, 0.6], "dark": [0.36, 0.06, 0.3], "layers": 2, "wisps": 0.6, "posterize": 3, "angular": 0.75},
                          "smog": {"strength": 0.55, "color": [0.6, 1.0, 0.35], "height_deg": 5},
                          "planet": {"color": [1.0, 0.32, 0.6], "stripes": {"strength": 0.6, "frequency": 300, "color": [1.0, 0.78, 0.9]}, "ring": False, "over_clouds": True},
                          "sun": {"color": [1.0, 0.55, 0.65], "glow": 0.5}},
        "fog_color": [0.62, 0.95, 0.4], "fog_start": 380, "fog_end": 1400, "height_fog": {"height": 24, "density": 0.05},
        "clouds": {"color": [0.6, 1.0, 0.32], "shade": [0.12, 0.34, 0.12], "glow": [0.85, 1.0, 0.45]},
        "lighting": {"sun_energy": 2.2, "sun_color": [1.0, 0.62, 0.8], "ambient_energy": 1.35, "exposure": 1.0, "contrast": 1.15, "saturation": 1.2,
                     "glow": {"enabled": True, "intensity": 1.0, "bloom": 0.1, "hdr_threshold": 0.8}},
    },
    "background_types": {
        "mountain_ring": {"toon": True, "color": [0.24, 0.16, 0.32], "fade": 0.0},
        "spires": {"toon": True, "color": [0.12, 0.09, 0.17], "fade": 0.05},
        "skyline": {"toon": True, "color": [0.12, 0.09, 0.16], "fade": 0.05, "glow": [0.55, 1.0, 0.25], "lit": 0.22, "setbacks": True, "masts": 0.7, "spikes": 0.6, "tile_m": 26.0},
        "ring_structure": {"toon": True, "color": [0.16, 0.12, 0.22], "fade": 0.05, "glow": [1.0, 0.25, 0.7]},
    },
    "background_add": [{"id": "Hover_Satellites", "type": "hover_satellites", "radius": [190, 520], "count": 16, "elevation": [55, 150],
                        "size": [10, 26], "color": [0.1, 0.08, 0.14], "toon": True, "glow": [1.0, 0.15, 0.25], "fade": 0.05, "seed": 21}],
    "structures_decor": {"tower": ["antenna"]},
    "render": {"name": "alien_cartoon", "toon": {"steps": 3, "floor": 0.55, "godot": {"diffuse_mode": "toon", "specular_mode": "disabled", "metallic": 0.0}},
               "outline": {"color": [0.03, 0.01, 0.05], "width": [0.07, 0.24], "rel": 0.016, "min_size": 0.25,
                           "skip_materials": ["glow", "water", "accent"], "skip_types": ["panel", "terrain", "boundary", "stream"]}},
}

PRESETS = {"alien_cartoon": ALIEN_CARTOON}


def _deep_under(base, top):
    """top wins; dicts merged recursively; lists / scalars from top replace."""
    if not isinstance(base, dict) or not isinstance(top, dict): return copy.deepcopy(top)
    out = copy.deepcopy(base)
    for k, v in top.items(): out[k] = _deep_under(out.get(k), v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def apply(spec):
    """spec with its art_style preset applied (unchanged when the spec has none)."""
    name = spec.get("art_style")
    if not name: return spec
    if name not in PRESETS: raise SystemExit(f"art_style '{name}' unknown (have {sorted(PRESETS)})")
    P = PRESETS[name]; s = copy.deepcopy(spec)
    s["materials"] = _deep_under(P["materials"], s.get("materials", {}))
    s["atmosphere"] = _deep_under(P["atmosphere"], s.get("atmosphere", {}))
    if s.get("world"):
        W = s["world"]; PW = P["world"]
        W["materials"] = _deep_under(PW["materials"], W.get("materials", {}))
        for sc in W.get("scatter", []):
            if sc.get("style_locked"): continue
            kinds = [k if isinstance(k, dict) else {"kind": k} for k in sc["kinds"]]
            new = [dict(k, kind=PW["scatter_replace"].get(k["kind"], k["kind"])) for k in kinds]
            if any(a["kind"] != b["kind"] for a, b in zip(kinds, new)):
                sc["kinds"] = [k if len(k) > 1 else k["kind"] for k in new]; sc["density"] = round(sc.get("density", 1.0) * PW["scatter_density_mult"], 3)
                if PW.get("scatter_scale"): sc.setdefault("scale", PW["scatter_scale"])
            sc.setdefault("style", PW["scatter_style"])
    bg = s.get("background", {})
    if "layers" in bg:
        bg["layers"] = [_deep_under(P["background_types"].get(l["type"], {}), l) for l in bg["layers"]]
        ids = {l["id"] for l in bg["layers"]}; bg["layers"] += [copy.deepcopy(l) for l in P["background_add"] if l["id"] not in ids]
    for st in s.get("structures", []):
        add = P["structures_decor"].get(st.get("kind"))
        if add and "decor" in st: st["decor"] = list(dict.fromkeys(list(st["decor"]) + [d for d in add if d not in st["decor"]]))
    s["style"] = _deep_under(P["render"], s.get("style", {}))
    return s


if __name__ == "__main__":
    for k, v in PRESETS.items(): print(f"{k}: {v['description']}")
