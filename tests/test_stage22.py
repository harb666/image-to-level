"""Stage 22: wall monitors from the user's reference - screen_ui texture (two seeded layouts) on framed screens with
angular red corners, top lights, side box and feed cable, replacing the green tank windows."""
import json, os, re, unittest
import numpy as np
from _util import tmp_level, small_spec, write_spec


class Monitors(unittest.TestCase):
    def test_screen_texture(self):
        import materials
        a = materials.maps({"type": "screen_ui", "color": [1, 1, 1], "res": 256, "seed": 1, "emissive": [1, 1, 1]})
        b = materials.maps({"type": "screen_ui", "color": [1, 1, 1], "res": 256, "seed": 2, "emissive": [1, 1, 1]})
        self.assertGreater(float(a["alb"][..., 2].mean()), float(a["alb"][..., 1].mean()))  # purple screen
        self.assertGreater(float(np.abs(a["alb"] - b["alb"]).mean()), 0.01)  # two different layouts
        self.assertEqual(float(a["emit"].min()), 1.0)

    def test_wall_monitors(self):
        import spec_to_level
        s = small_spec(); s["art_style"] = "alien_cartoon"; s["arena"]["size"] = [80, 80]
        s["arena"]["walls"] = {"height": 22, "thickness": 3, "dressing": "varied", "dress_y": 5}
        d = tmp_level(name="mon"); spec_to_level.run(write_spec(d, s), d, verbose=False); L = json.load(open(os.path.join(d, "level.json")))
        names = [o["name"] for o in L["objects"]]; by = {o["name"]: o for o in L["objects"]}
        self.assertFalse(any(re.search(r"_M\d\dTank", n) for n in names))
        scr = [n for n in names if n.endswith("Monitor_Screen")]; self.assertTrue(scr)
        for n in scr:
            self.assertIn(by[n]["material"], ("screen", "screen_b")); base = n[:-len("_Screen")]
            for part in ("_Frame", "_Cable", "_Box", "_Corner_00"): self.assertIn(base + part, by)


if __name__ == "__main__":
    unittest.main()
