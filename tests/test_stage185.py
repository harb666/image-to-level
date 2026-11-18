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

    def test_bend_joins_riser_and_run(self):
        for k in (1, 2, 3):
            o, m = self.elbow(k); self.assertEqual(o["type"], "pipe_elbow"); self.assertNotIn(f"Pod_Export_{k}_ElbowCap", self.by)
            inl, ou = self.by[f"Pod_Export_{k}_Inlet"], self.by[f"Pod_Export_{k}_Outlet"]; rk = inl["size"][0] / 2
            tx, ye, tz = inl["position"][0], inl["position"][1] + inl["size"][1] - 0.05, inl["position"][2]
            (x0, y0_, z0), (x1, y1, z1) = m.bounds
            self.assertAlmostEqual(x0, tx - rk, places=2); self.assertAlmostEqual(y0_, ye, places=2); self.assertAlmostEqual((z0 + z1) / 2, tz, places=2)  # starts on the inlet
            self.assertAlmostEqual(x1, ou["position"][0] + 0.05, places=2); self.assertAlmostEqual(y1 - rk, ou["position"][1], places=2)  # ends on the outlet drum
            self.assertEqual(ou["rotation"], [0, 0, -90])

    def test_wrapped_pods_stay_inside_the_bend(self):
        up = self.E["Pod_Export_Up_Run"]["line"]
        for k in (1, 2, 3):
            o, m = self.elbow(k); inl = self.by[f"Pod_Export_{k}_Inlet"]; rk = inl["size"][0] / 2; tx = inl["position"][0]; ye = m.bounds[0][1]
            R = max(o["size"][1], o["size"][0]); cx = tx + R  # the bend's centre (x, ye)
            ris = sorted([b for n, b in self.by.items() if n.startswith(f"Pod_Export_RiserPod_{k}_") and n.endswith("_Base")], key=lambda b: b["position"][1])
            cap = self.by[ris[-1]["name"][:-5] + "_Cap"]; top = cap["position"][1] + cap["size"][1] - ris[-1]["position"][1] + ris[-1]["position"][1] + up["spacing"]
            rp = cap["size"][0] / 2 / math.cos(math.pi / 6)  # hex corner
            dy = max(0.0, top - ye)
            for xx in (tx - rp, tx + rp):  # the pod's sides at its top, inside the torus wall
                self.assertLess(abs(math.hypot(cx - xx, dy) - R), rk - 0.1)
            run = min([b for n, b in self.by.items() if n.startswith(f"Pod_Export_RunPod_{k}_") and n.endswith("_Base")], key=lambda b: b["position"][0])
            dx = max(0.0, cx - run["position"][0]); jc = run["position"][1]  # the first run pod's rear, back in the bend
            for yy in (jc - rp, jc + rp): self.assertLess(abs(math.hypot(dx, yy - ye) - R), rk - 0.1)

    def test_budget(self):
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")) / 1024, 4000)


if __name__ == "__main__":
    unittest.main()
