"""Stage 24: the green slime windows become viewscreens - a "broadcast" propaganda screen and a "specimen"
tank (k_bigscreen; robots since Stage 25), both packed into one screen_atlas material (one draw call), plus the wall monitors
sharing the "screen" atlas (uv_region a / b)."""
import json, os, unittest
import numpy as np
from _util import tmp_level, small_spec, write_spec


class Viewscreens(unittest.TestCase):
    def test_bigscreen_modes_differ_and_glow(self):
        import materials
        a = materials.maps({"type": "bigscreen", "mode": "broadcast", "color": [1, 1, 1], "res": 256, "emissive": [1, 1, 1]})
        b = materials.maps({"type": "bigscreen", "mode": "specimen", "color": [1, 1, 1], "res": 256, "emissive": [1, 1, 1]})
        self.assertGreater(float(np.abs(a["alb"] - b["alb"]).mean()), 0.03)
        self.assertGreater(float(b["alb"][..., 1].mean()), float(b["alb"][..., 0].mean()))  # green tank
        self.assertEqual(float(a["emit"].min()), 1.0)

    def test_screen_atlas_halves(self):
        import materials
        m = {"type": "screen_atlas", "color": [1, 1, 1], "res": 256, "emissive": [1, 1, 1],
             "left": {"type": "bigscreen", "mode": "broadcast"}, "right": {"type": "bigscreen", "mode": "specimen"}}
        d = materials.maps(m); alb = d["alb"]; self.assertEqual(alb.shape[:2], (256, 256))
        self.assertGreater(float(np.abs(alb[:, :128] - alb[:, 128:]).mean()), 0.03)

    def test_window_fills(self):
        import spec_to_level
        s = small_spec(); s["art_style"] = "alien_cartoon"; s["arena"]["size"] = [40, 40]
        s["arena"]["walls"] = {"height": 14, "thickness": 2, "openings": [
            {"side": "north", "at": -9, "width": 10, "sill": 6, "height": 12, "fill": "screen", "frame": False},
            {"side": "north", "at": 9, "width": 10, "sill": 6, "height": 12, "fill": "specimen", "frame": False}]}
        d = tmp_level(name="vs"); spec_to_level.run(write_spec(d, s), d, verbose=False); L = json.load(open(os.path.join(d, "level.json")))
        scr = sorted((o for o in L["objects"] if o["name"].endswith("_Screen") and o.get("material") == "bigscreen"), key=lambda o: o["position"][0])
        self.assertEqual([o["uv_region"] for o in scr], ["a", "b"])
        self.assertTrue(all(o["collision"] is False for o in scr))
        backs = [o for o in L["objects"] if o["name"].startswith("OuterWall_North_Op") and o["name"].endswith("_Back")]
        self.assertEqual(len(backs), 2); self.assertTrue(all(o["collision"] for o in backs))  # the hole stays closed
        self.assertTrue(any(e["type"] in ("flicker", "tv_static") and e.get("target_material") == "bigscreen" for e in L["effects"]))
        self.assertFalse(any(o.get("material") == "slime" and "_Op" in o["name"] for o in L["objects"]))


if __name__ == "__main__":
    unittest.main()
