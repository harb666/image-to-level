"""Stage 20: see-through tubes with blobs of slime rising through them now and then (glass material with alpha,
tube_blobs particle effect, one system per height group), and less green on the wall textures."""
import json, os, unittest
import numpy as np
from _util import ROOT, PIPE, tmp_level, small_spec, write_spec


class Tubes(unittest.TestCase):
    def test_glass_tubes_and_rising_blobs(self):
        import spec_to_level
        s = small_spec(); s["art_style"] = "alien_cartoon"; s["arena"]["ceiling"] = {}; s["arena"]["walls"]["height"] = 20
        s["structures"] = [{"id": "VatA", "kind": "vat", "position": [10, 10], "size": [4, 12, 4]}, {"id": "Col", "kind": "column", "position": [-10, 10], "radius": 1.5}]
        d = tmp_level(name="tubes"); spec_to_level.run(write_spec(d, s), d, verbose=False); L = json.load(open(os.path.join(d, "level.json")))
        self.assertLess(L["materials"]["glass"]["alpha"], 0.5)
        glass = [o for o in L["objects"] if o.get("tube")]
        self.assertTrue(glass and all(o["material"] == "glass" and o["double_sided"] and o["collision"] for o in glass))
        blobs = [e for e in L["effects"] if e["type"] == "tube_blobs"]
        self.assertEqual(sum(len(e["positions"]) for e in blobs), 2)  # one emitter per structure (the column's sections are one shaft)
        for e in blobs: self.assertGreater(e["lifetime"], 0.5)
        import materials
        m, _ = materials.make_material("glass", L["materials"]["glass"]); self.assertEqual(m.alphaMode, "BLEND")


class LessSlime(unittest.TestCase):
    def test_slimed_wall_is_mostly_plate(self):
        import materials
        d = materials.maps({"type": "wall_slimed", "color": [0.3, 0.25, 0.35], "res": 256, "toon": True, "emissive": [1, 1, 1]})
        self.assertLess(float((d["emit"] > 0.3).mean()), 0.06)  # glowing slime covers only a small part of the plate


if __name__ == "__main__":
    unittest.main()
