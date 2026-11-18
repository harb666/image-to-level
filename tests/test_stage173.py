"""Stage 173: the boss lift - the car parked in the roof shaft comes down onto the showcase dais with the mini boss."""
import json, os, re, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class BossLift(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}; cls.B = cls.L["boss_lifts"][0]

    def test_car_moves_on_its_own(self):
        car = [o for o in self.L["objects"] if o["name"].startswith("BossShaft_Car")]; self.assertGreaterEqual(len(car), 7)
        for o in car: self.assertEqual(o["mobile"], {"group": self.B["group"]})
        self.assertAlmostEqual(self.B["top"], self.by["BossShaft_Car"]["position"][1], places=3)

    def test_lands_docked_on_the_dais(self):
        off = self.B["bottom"] - self.B["top"]; dais = self.by["Showcase_Dais"]; dtop = dais["position"][1] + dais["size"][1]
        lights = self.by["BossShaft_CarLights"]; self.assertGreater(lights["position"][1] + off, dtop + 0.05)  # its underside clears the dais
        under = self.by["BossShaft_CarUnder"]; self.assertGreater(under["position"][1] + off, dtop)
        for k in range(1, 5):  # its clamp arms dock on the floor clamps' caps (contact, no overlap)
            c = self.by[f"BossShaft_CarClamp_{k}"]; cap = self.by[f"Showcase_LiftClampCap_{k}"]
            self.assertAlmostEqual(c["position"][1] + off, cap["position"][1] + cap["size"][1], delta=0.03)
        self.assertAlmostEqual(self.B["center"][0], dais["position"][0], places=2); self.assertAlmostEqual(self.B["center"][2], dais["position"][2], places=2)
        self.assertEqual(self.B["boss_spawn"][1], self.B["deck_y"])

    def test_triggered_and_wired(self):
        self.assertEqual(self.B["trigger"]["name"], "Showcase_Deck")
        E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}; self.assertEqual(E["BossShaft_Lift_Descent"]["category"], "boss_lift")
        C = json.load(open(os.path.join(LV, "mobile", "collision.json"))); self.assertEqual(C["boss_lifts"][0]["id"], self.B["id"])
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read()
        self.assertIn("window.bossLifts", v); self.assertNotIn("/Math.max(r,1e-3);pos.x=BL.center[0]", v)  # (a player at the dead centre was flung 10 km) self.assertIn("fx.category==='boss_lift'", v)
        for k in ("signal boss_lift_landed", "func start_boss_lift", "func _update_boss_lifts", "_update_boss_lifts()"): self.assertIn(k, gd)


if __name__ == "__main__":
    unittest.main()
