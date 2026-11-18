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

    def test_lines_hide_their_wrap(self):
        up, east = self.E["Pod_Export_Up_Run"]["line"], self.E["Pod_Export_East_Run"]["line"]
        self.assertEqual(up["axis"], [0.0, 1.0, 0.0]); self.assertEqual(east["axis"], [1.0, 0.0, 0.0])
        for k in (1, 2, 3):  # (Stage 183: the hall's pods - base .. cap; the base marks the pod's start)
            ris = sorted([o for n, o in self.by.items() if n.startswith(f"Pod_Export_RiserPod_{k}_") and n.endswith("_Base")], key=lambda o: o["position"][1])
            cap = lambda o: self.by[o["name"][:-5] + "_Cap"]; h = cap(ris[0])["position"][1] + cap(ris[0])["size"][1] - ris[0]["position"][1]; r = cap(ris[0])["size"][0] / 2
            col = self.by[f"Pod_Export_{k}_Collar"]; p0, p1 = ris[0]["position"], ris[-1]["position"]
            self.assertTrue(self.inside(col, [p0[0] - r, p0[1], p0[2] - r], [p0[0] + r, p0[1] + h, p0[2] + r]))  # first riser pod appears hidden in the roof collar
            self.assertAlmostEqual(p1[1] - p0[1], up["spacing"] * (len(ris) - 1), places=2)
            # Stage 185: offset = fmod(t v, spacing) - the LAST pod vanishes one spacing past its start: there it must be
            # out of sight (base in the opaque inlet drum, top a little way into the bend - the exact check: test_stage185)
            inl = self.by[f"Pod_Export_{k}_Inlet"]; yv = p1[1] + up["spacing"]
            self.assertGreaterEqual(yv, inl["position"][1]); self.assertLessEqual(yv + h, inl["position"][1] + inl["size"][1] + 1.6)
            run = sorted([o for n, o in self.by.items() if n.startswith(f"Pod_Export_RunPod_{k}_") and n.endswith("_Base")], key=lambda o: o["position"][0])
            q0, q1 = run[0]["position"], run[-1]["position"]; ou = self.by[f"Pod_Export_{k}_Outlet"]
            self.assertLessEqual(q0[0] + h, ou["position"][0] + ou["size"][1]); self.assertGreaterEqual(q0[0], ou["position"][0] - 1.6)  # appears in the outlet drum / bend (wall check: test_stage185)
            self.assertAlmostEqual(q1[0] - q0[0], east["spacing"] * (len(run) - 1), places=2)
            qv = q1[0] + east["spacing"]  # vanishes inside the transfer tower
            self.assertTrue(self.inside(self.by["Pod_Export_Tower"], [qv, q1[1] - r, q1[2] - r], [qv + h, q1[1] + r, q1[2] + r]))
            for o in ris + run: self.assertIn("floating", o.get("intentional", []))
        hall = self.by["Pod_Tube_2_Glass_01"]; out = self.by["Pod_Export_2_Riser_Glass_01"]  # Stage 183: the same tube outside as in the hall
        self.assertEqual(out["material"], hall["material"]); self.assertAlmostEqual(out["size"][0], hall["size"][0], places=2)

    def test_cutaway_and_budget(self):
        for n, o in self.by.items():
            if n.startswith("Pod_Export_") and o["type"] != "group": self.assertTrue(o.get("cutaway"), n); self.assertEqual(o.get("collision"), False)
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")), 4000 * 1024)


if __name__ == "__main__":
    unittest.main()
