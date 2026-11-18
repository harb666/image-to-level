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

    def test_lands_flush_in_the_ring(self):
        """Stage 177 (user): the landed car lines up with the ground - it drops into the dais's steel ring, its deck 1-3 cm
        over the dais top (covering it and its decal) and under the ring's lip; everything below its deck is hidden."""
        off = self.B["bottom"] - self.B["top"]; dais = self.by["Showcase_Dais"]; dtop = dais["position"][1] + dais["size"][1]
        car = self.by["BossShaft_Car"]; top = car["position"][1] + off + car["size"][1]; self.assertAlmostEqual(top, self.B["deck_y"], places=3)
        self.assertGreater(top, self.by["Showcase_Logo"]["position"][1] + 0.01); self.assertLess(top - dtop, 0.05)
        ring = self.by["Showcase_LiftRingInner"]; self.assertLess(top, ring["position"][1] + ring["size"][1])
        self.assertLess(car["size"][0] / 2, ring["hole"]); self.assertGreater(car["size"][0] / 2, dais["size"][0] / 2)  # in the ring's bore, over the whole dais
        for n in ("BossShaft_CarUnder", "BossShaft_CarLights") + tuple(f"BossShaft_CarClamp_{k}" for k in range(1, 5)):
            o = self.by[n]; self.assertLess(o["position"][1] + off + o["size"][1], ring["position"][1] + 0.001, n)  # hidden under the deck / in the floor
        em = self.by["BossShaft_CarEmblem"]; self.assertEqual(em["material"], "gear_decal"); self.assertAlmostEqual(em["position"][1] + off, top + 0.012, places=3)
        self.assertEqual(em["mobile"], {"group": self.B["group"]}); self.assertAlmostEqual(em["position"][2] - em["size"][1] / 2, dais["position"][2], places=2)
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
