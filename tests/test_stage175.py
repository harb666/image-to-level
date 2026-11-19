"""Stage 175: the pod tubes carry on outside over the roof - risers, junction boxes, a pipe bridge east to a transfer
tower - with pods streaming through (seen through the glass dome). Every conveyor starts and ends inside an opaque box."""
import json, os, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class RoofPodPipes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}
        cls.E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}

    def inside(self, box, lo, hi):  # [lo, hi] (3-vectors) within the (unrotated) box object
        p, s = box["position"], box["size"]
        a = [p[0] - s[0] / 2, p[1], p[2] - s[2] / 2]; b = [p[0] + s[0] / 2, p[1] + s[1], p[2] + s[2] / 2]
        return all(a[i] - 1e-6 <= lo[i] and hi[i] <= b[i] + 1e-6 for i in range(3))

    def test_same_tube_outside(self):  # (Stage 186: the pods' wrap points - the pod path - are checked in test_stage186)
        hall = self.by["Pod_Tube_2_Glass_01"]; out = self.by["Pod_Export_2_Riser_Glass_01"]  # Stage 183: the same tube outside as in the hall
        self.assertEqual(out["material"], hall["material"]); self.assertAlmostEqual(out["size"][0], hall["size"][0], places=2)
        for k in (1, 2, 3): self.assertIn(f"Pod_Export_{k}_Collar", self.by); self.assertIn(f"Pod_Export_{k}_Run_Glass_01", self.by)
        self.assertIn("Pod_Export_Tower", self.by)

    def test_cutaway_and_budget(self):
        for n, o in self.by.items():
            if n.startswith("Pod_Export_") and o["type"] != "group": self.assertTrue(o.get("cutaway"), n); self.assertEqual(o.get("collision"), False)
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")), 4000 * 1024)


if __name__ == "__main__":
    unittest.main()
