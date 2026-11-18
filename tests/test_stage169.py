"""Stage 169: the crane claws ride the runway carrying green canisters, out of one wall hatch and into the other."""
import json, os, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class ClawLine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}
        cls.E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}

    def test_claws_move_as_one_seamless_line(self):
        ln = self.E["Claw_Line_Run"]["line"]; self.assertEqual(ln["move"], ["Claw_Line_Move"]); self.assertEqual(ln["stations"], [])
        S = ln["spacing"]; xs = [self.by[f"Claw_Line_{k}"]["position"][0] for k in range(1, 6)]
        self.assertTrue(all(abs((b - a) - S) < 1e-6 for a, b in zip(xs, xs[1:])))  # exactly a spacing apart: the wrap is invisible
        beam = self.by["CraneRail_01_Beam"]; half = beam["size"][0] / 2
        self.assertLess(xs[0] + 1.3, -half)  # the first claw starts hidden inside the west wall...
        self.assertGreater(xs[-1] + S - 1.3, half)  # ...and the last ends hidden inside the east wall
        for k in range(1, 6):
            for p in ("_Can", "_CanLug", "_Block", "_Trolley_Body"): self.assertEqual(self.by[f"Claw_Line_{k}{p}"]["mobile"], {"group": "Claw_Line_Move"})
        self.assertNotIn("Claw_Hang", self.by)

    def test_hatches_in_both_end_walls(self):
        beam = self.by["CraneRail_01_Beam"]; rail_z = self.by["CraneRail_01"]["position"][2]
        for sd in "WE":
            h = self.by[f"Claw_Line_Hatch_{sd}"]; self.assertEqual(h["material"], "void"); self.assertAlmostEqual(h["position"][2], rail_z, places=2)
            self.assertLess(h["position"][1], self.by["Claw_Line_1_Can"]["position"][1])  # tall enough for the canister...
            self.assertGreater(h["position"][1] + h["size"][1], beam["position"][1] + beam["size"][1])  # ...and the rail and trolley
            self.assertGreater(abs(h["position"][0]), beam["size"][0] / 2 - 0.2)


if __name__ == "__main__":
    unittest.main()
