"""Stage 188 (user): the pink mascot monitors beside the vat are gone; the cogs are two-tone industrial castings -
machined steel (toothed rim, hub, ribs, bolts, crank pin) over a dark cast-iron web, turning together."""
import json, math, os, sys, unittest
import numpy as np
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import shapes

LV = os.path.join(ROOT, "levels", "assembly_ascent")


def _load(p):
    with open(p) as f: return json.load(f)


class IndustrialCogs2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = _load(os.path.join(LV, "level.json")); cls.by = {o["name"]: o for o in cls.L["objects"]}

    def test_monitors_removed(self):
        self.assertFalse([n for n in self.by if n.startswith("Showcase_Monitor")])
        sp = _load(os.path.join(LV, "scene_spec.json")); self.assertIn("screen", sp["materials"]["roles"]["ce_signs"]["blank"])

    def test_two_parts_turn_together(self):
        for t in "ab":
            for i in (1, 2, 3):
                g, w = self.by[f"Showcase_Cogs_{t}_Gear_{i}"], self.by[f"Showcase_Cogs_{t}_Gear_{i}_Web"]
                self.assertEqual((g["part"], w["part"]), ("machined", "cast"))
                for k in ("position", "rotation", "size", "teeth", "phase", "spin", "spokes"): self.assertEqual(g[k], w[k], k)
                self.assertEqual(w["mobile"], {"merge": False})
        M = self.L["materials"]; self.assertLess(max(M["cog_steel"]["color"]), 0.1); self.assertGreater(max(M["cog_machined"]["color"]), 0.18)

    def test_rim_mesh(self):  # one inner vertex per tooth, ear-clipped faces: exact areas, closed
        for N, w in ((16, 3.4), (11, 2.4), (8, 1.8)):
            m = shapes.gear(w, 0.32, w, {"teeth": N, "spokes": 5, "part": "machined", "depth": 0.22, "bolts": 0})
            rim = max(m.split(only_watertight=False), key=lambda q: q.area); self.assertTrue(rim.is_watertight); self.assertTrue(rim.is_winding_consistent)
            up, dn = rim.face_normals[:, 1] > 0.9, rim.face_normals[:, 1] < -0.9; self.assertAlmostEqual(rim.area_faces[up].sum(), rim.area_faces[dn].sum(), places=6)
            self.assertAlmostEqual(rim.volume, rim.area_faces[up].sum() * 0.32, places=4)  # no folded triangles
            web = shapes.gear(w, 0.32, w, {"teeth": N, "spokes": 5, "part": "cast", "depth": 0.22})
            self.assertLess(web.bounds[1][1] - web.bounds[0][1], 0.32 * 0.5)  # the web is recessed

    def test_budget(self):
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")) / 1024, 4000)


if __name__ == "__main__":
    unittest.main()
