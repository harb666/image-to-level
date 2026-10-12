"""Stage 21: ceilings from the user's ceiling reference - ceiling_works texture (seeded per room), hazard-striped beam
ends, warm pill lights under beams, conduit bundles on brackets, green capsule tubes along the walls, recessed fans."""
import json, os, re, unittest
import numpy as np
from _util import ROOT, PIPE, tmp_level, small_spec, write_spec


class Ceiling(unittest.TestCase):
    def test_texture_layouts_differ_per_seed(self):
        import materials
        a = materials.maps({"type": "ceiling_works", "color": [0.4, 0.42, 0.3], "res": 256, "seed": 1})["h"]
        b = materials.maps({"type": "ceiling_works", "color": [0.4, 0.42, 0.3], "res": 256, "seed": 2})["h"]
        self.assertGreater(float(np.abs(a - b).mean()), 0.05)  # another room, another plate layout
        self.assertGreater(float(np.std(a)), 0.05)

    def test_details(self):
        import spec_to_level
        s = small_spec(); s["art_style"] = "alien_cartoon"; s["arena"]["size"] = [60, 60]; s["arena"]["walls"]["height"] = 20
        s["arena"]["ceiling"] = {"style": "varied", "seed": 5, "material": "ceiling"}
        d = tmp_level(name="ceil"); spec_to_level.run(write_spec(d, s), d, verbose=False); L = json.load(open(os.path.join(d, "level.json")))
        names = [o["name"] for o in L["objects"]]; by = {o["name"]: o for o in L["objects"]}
        self.assertEqual(by["Ceiling_Slab"]["material"], "ceiling"); self.assertEqual(L["materials"]["ceiling"]["type"], "ceiling_works")
        for k in ("_StripeA", "_Lamp_", "Ceil_Conduit_", "Ceil_Capsule_"): self.assertTrue(any(k in n for n in names), k)
        self.assertTrue(all(by[n].get("cutaway") and by[n].get("collision") is False for n in names if n.startswith("Ceil_")))


if __name__ == "__main__":
    unittest.main()
