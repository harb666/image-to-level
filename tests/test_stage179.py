"""Stage 179: the climb to the exit deck is a gentle ramp, not stairs."""
import json, os, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class ExitRamp(unittest.TestCase):
    def test_ramp(self):
        L = json.load(open(os.path.join(LV, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        d = by["Exit_Stairs_Deck"]; self.assertEqual(d["type"], "box"); self.assertLessEqual(abs(d["rotation"][0]), 24.5)
        self.assertFalse([o for o in L["objects"] if o["name"].startswith("Exit_Stairs") and o["type"] == "stairs"])
        N = json.load(open(os.path.join(LV, "checks", "navigation.json"))); A = {a["name"]: a["reachable_fraction"] for a in N["intended_areas"]}
        self.assertEqual(A["Exit_Deck"], 1.0)
        rep = open(os.path.join(LV, "checks", "report.md")).read(); self.assertNotIn("Exit_Stairs: walking up the right lane", rep)


if __name__ == "__main__":
    unittest.main()
