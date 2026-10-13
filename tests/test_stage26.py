"""Stage 26: TV static on the screens - effect tv_static (category material_shader) for the screen roles, its spec
switch (screens.static, 0 = the old flicker), the Godot shader + apply_effects handler and the preview handler."""
import json, os, unittest
from _util import PIPE, tmp_level, small_spec, write_spec


def _gen(screens=None):
    import spec_to_level
    s = small_spec(); s["art_style"] = "alien_cartoon"; s["arena"]["size"] = [80, 80]
    s["arena"]["walls"] = {"height": 22, "thickness": 3, "dressing": "varied", "dress_y": 5}
    if screens is not None: s["screens"] = screens
    d = tmp_level(name="tv"); spec_to_level.run(write_spec(d, s), d, verbose=False); return json.load(open(os.path.join(d, "level.json")))


class Static(unittest.TestCase):
    def test_screens_get_static(self):
        L = _gen(); st = [e for e in L["effects"] if e["type"] == "tv_static"]
        self.assertTrue(st); self.assertTrue(all(e["target_material"] in ("screen", "bigscreen") and 0 < e["amount"] <= 1 for e in st))
        self.assertFalse([e for e in L["effects"] if e["type"] == "flicker" and e.get("target_material") == "screen"])
        L = _gen({"static": 0}); self.assertFalse([e for e in L["effects"] if e["type"] == "tv_static"])  # off -> CRT flicker as before
        self.assertTrue([e for e in L["effects"] if e["type"] == "flicker" and e.get("target_material") == "screen"])
        L = _gen({"static": 0.5, "signal_every": 3}); e = next(e for e in L["effects"] if e["type"] == "tv_static")
        self.assertEqual((e["amount"], e["signal_every"]), (0.5, 3))

    def test_runtime_pieces(self):
        import effects
        self.assertEqual(effects.TYPES["tv_static"]["category"], "material_shader")
        sh = open(os.path.join(PIPE, "godot_fx", "tv_static.gdshader")).read()
        for u in effects.TYPES["tv_static"]["defaults"]: self.assertIn(f"uniform float {u}", sh)
        gd = open(os.path.join(PIPE, "godot_fx", "apply_effects.gd")).read(); self.assertIn('"material_shader"', gd); self.assertIn("tv_static.gdshader", gd)
        self.assertIn("material_shader", open(os.path.join(PIPE, "viewer.html")).read())


if __name__ == "__main__":
    unittest.main()
