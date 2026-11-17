"""Stage 155: the spinner tower redesign (concept art) - two plasma chambers driven by the ceiling press."""
import json, math, os, sys, unittest
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "modules"))
import materials

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class SpinnerTower(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}
        cls.sw = next(s for s in cls.L["sweepers"] if s["id"] == "Spinner"); cls.D = cls.sw["drive"]

    def test_plasma_chambers(self):
        T = self.sw["center"][1]
        for c in (1, 2):
            g = self.by[f"Spinner_Glass_{c}"]; self.assertEqual(g["material"], "glass_clear"); self.assertNotEqual(g.get("collision"), False)  # solid: nobody walks into the plasma
            for l_ in "ab":
                p = self.by[f"Spinner_Plasma_{c}{l_}"]; self.assertEqual(p["material"], self.D["plasma"]); self.assertEqual(p["type"], "pole")
                self.assertEqual(round(math.pi * p["size"][0] / p["uv_len"]), self.D["plasma_tiles"])  # both layers: the same tiles round -> they turn together
                self.assertLess(p["size"][0], g["size"][0]); self.assertGreaterEqual(p["position"][1], g["position"][1])
                self.assertLessEqual(p["position"][1] + p["size"][1], g["position"][1] + g["size"][1] + 1e-6)
        self.assertLess(self.by["Spinner_Glass_1"]["position"][1] + self.by["Spinner_Glass_1"]["size"][1], self.by["Spinner_Clamp_Collar"]["position"][1])
        self.assertAlmostEqual(self.by["Spinner_Strike"]["position"][1] + self.by["Spinner_Strike"]["size"][1], T + 6.0, places=3)  # the press still lands on it

    def test_plasma_material(self):
        m = self.L["materials"][self.D["plasma"]]; self.assertEqual(m["type"], "plasma_arc"); self.assertIsNotNone(m.get("alpha"))
        d = materials.maps(dict(m, res=64)); self.assertEqual(d["alpha"].shape, (64, 64)); self.assertGreater(d["alpha"].max(), 0.9); self.assertLess(d["alpha"].min(), 0.4)
        self.assertGreater(d["emit"].max(), 0.9)

    def test_clamp_rides_the_press(self):
        st = {s["group"]: s["frac"] for s in self.D["stages"]}; self.assertIn("Spinner_Clamp", st)
        drop = self.D["travel"] * st["Spinner_Clamp"]; c = self.by["Spinner_Clamp_Collar"]; b2 = self.by["Spinner_Band_2"]
        self.assertGreaterEqual(c["position"][1] - drop, b2["position"][1] + b2["size"][1] - 1e-3)  # pressed, it sits on the lower chamber's band
        for o in self.L["objects"]:
            if o["name"].startswith("Spinner_Clamp_"): self.assertEqual(o.get("collision"), False)

    def test_deck_rings_and_lamps(self):
        for k in (1, 2):
            r = self.by[f"Spinner_DeckRing_{k}"]; self.assertEqual(r.get("collision"), False); self.assertLess(r["size"][1], 0.05)
        self.assertEqual(len([n for n in self.by if n.startswith("Spinner_FootLamp_")]), 16)
        lamps = [self.by[f"Spinner_CrownLamp_{k}"]["material"] for k in range(1, 9)]; self.assertEqual(set(lamps), {"glow", "glow_green"})

    def test_runtimes(self):
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read()
        self.assertIn("D.plasma_tiles", v); self.assertIn("pmap.forEach", v)
        self.assertIn('sw["drive"].has("plasma")', gd); self.assertIn("uv1_offset", gd); self.assertIn("emission_energy_multiplier = float(pm[1]) * surge", gd)
        C = json.load(open(os.path.join(LV, "mobile", "collision.json")))
        sw = next(s for s in C.get("sweepers", []) if s["id"] == "Spinner") if C.get("sweepers") else None
        if sw: self.assertIn("plasma", sw["drive"])


if __name__ == "__main__":
    unittest.main()
