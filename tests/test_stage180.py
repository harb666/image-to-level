"""Stage 180: slime splashes as the arena's platforms break the surface and launch, drips off their rims as they climb."""
import json, os, sys, unittest
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "pipeline", "modules"))
import assembly as A


class RiserSplash(unittest.TestCase):
    def test_splash_timed_to_the_rise(self):
        R = json.load(open(os.path.join(ROOT, "levels", "assembly_ascent", "level.json")))["risers"][0]
        self.assertIn("splash", R); self.assertGreater(R["splash"]["burst"], 40)
        for pd in R["pads"]:
            t_surf, t_launch = pd["splash"]
            self.assertLess(pd["center"][1] + A.goofy_pose(pd, t_surf - 0.006, R["rise_s"], R["liquid"])[0], R["liquid"])  # still under just before...
            self.assertGreaterEqual(pd["center"][1] + A.goofy_pose(pd, t_surf, R["rise_s"], R["liquid"])[0], R["liquid"])  # ...out at the splash
            self.assertAlmostEqual(t_launch, 0.45 + pd["goof"]["peek"] + 0.22, places=3)  # the launch out of its duck
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read()
        self.assertIn("const SPL=R.splash?", v); self.assertIn("func _riser_splash", gd); self.assertIn("_riser_splash(rec[0], _t - rec[4])", gd)


if __name__ == "__main__":
    unittest.main()
