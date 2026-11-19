"""Stage 184: industrial cog towers - spoked gunmetal cogs with hub bolts, bearings, a riveted plate frame, gearbox fins + gauge."""
import json, os, sys, unittest
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import shapes

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class IndustrialCogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}

    def test_spoked_gear_shape(self):
        solid = shapes.gear(3.4, 0.32, 3.4, {"teeth": 16}); sp = shapes.gear(3.4, 0.32, 3.4, {"teeth": 16, "spokes": 5})
        self.assertGreater(len(sp.faces), 2 * len(solid.faces))  # rim + spokes + hub + bolts: far more detail
        self.assertAlmostEqual(float(sp.bounds[1][0]), float(solid.bounds[1][0]), places=3)  # same tip circle -> still meshes
        self.assertIn("uv", sp.metadata)

    def test_towers(self):
        for t in "ab":
            gears = [self.by[f"Showcase_Cogs_{t}_Gear_{i}"] for i in (1, 2, 3)]
            for g in gears:
                self.assertEqual(g["material"], "cog_steel"); self.assertGreaterEqual(g["spokes"], 4); self.assertTrue(g.get("spin"))
            for i in (1, 2, 3): self.assertIn(f"Showcase_Cogs_{t}_Bearing_{i}", self.by)
            for k in ("Gauge", "GaugeFace", "PlateEdge_1", "PlateEdge_4"): self.assertIn(f"Showcase_Cogs_{t}_{k}", self.by)  # (Stage 187: fins / rivets made way for the pump)
        m = self.L["materials"]["cog_steel"]; self.assertTrue(m.get("plain")); self.assertLess(max(m["color"]), 0.3)

    def test_mobile_budget(self):
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")) / 1024, 4000)


if __name__ == "__main__":
    unittest.main()
