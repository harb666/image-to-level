"""Stage 185 (user): the roof pod tubes BEND (a quarter-torus elbow) from the riser into the run - no box housing with
pods poking out of its top. The pods' wrap points stay out of sight inside the opaque bend / drums."""
import json, math, os, sys, unittest
import numpy as np
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import shapes
from build_level import node_matrix

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class BentPodTubes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}
        cls.E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}

    def elbow(self, k):
        o = self.by[f"Pod_Export_{k}_Elbow"]; m = shapes.pipe_elbow(*o["size"], o); m.apply_transform(node_matrix(o)); return o, m

    def test_bend_joins_riser_and_run(self):  # (Stage 186: a GLASS bend the pods ride round, between plated drums)
        for k in (1, 2, 3):
            o, m = self.elbow(k); self.assertEqual(o["type"], "pipe_elbow"); self.assertTrue(o.get("open")); self.assertNotIn(f"Pod_Export_{k}_ElbowCap", self.by)
            self.assertEqual(o["material"], self.by[f"Pod_Export_{k}_Riser_Glass_01"]["material"])
            inl, ou = self.by[f"Pod_Export_{k}_Inlet"], self.by[f"Pod_Export_{k}_Outlet"]; r = o["size"][0] / 2
            tx, ye, tz = inl["position"][0], inl["position"][1] + inl["size"][1] - 0.05, inl["position"][2]
            (x0, y0_, z0), (x1, y1, z1) = m.bounds
            self.assertAlmostEqual(x0, tx - r, places=2); self.assertAlmostEqual(y0_, ye, places=2); self.assertAlmostEqual((z0 + z1) / 2, tz, places=2)  # starts on the inlet drum
            self.assertAlmostEqual(x1, ou["position"][0] + 0.05, places=2); self.assertAlmostEqual(y1 - r, ou["position"][1], places=2)  # ends on the outlet drum
            self.assertEqual(ou["rotation"], [0, 0, -90]); self.assertGreater(inl["size"][0] / 2, r)  # the drums sleeve the glass

    def test_budget(self):
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")) / 1024, 4000)


if __name__ == "__main__":
    unittest.main()
