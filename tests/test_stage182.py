"""Stage 182: no hazard-stripe mats on Assembly Ascent's ramps (user: messy)."""
import json, os, unittest
from _util import ROOT


class NoRampStripes(unittest.TestCase):
    def test_ramps_have_no_threshold_mats(self):
        L = json.load(open(os.path.join(ROOT, "levels", "assembly_ascent", "level.json")))
        self.assertFalse([o["name"] for o in L["objects"] if o["name"].endswith(("_Threshold_Lo", "_Threshold_Hi"))])
        self.assertIn("Exit_Stairs_Deck", {o["name"] for o in L["objects"]})


if __name__ == "__main__":
    unittest.main()
