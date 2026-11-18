"""Stage 171: the yard's laser gate rebuilt as the user's armoured security gate (concept art)."""
import json, os, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class SecurityGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}

    def test_parts(self):
        for t in "LR":
            for p in ("Foot", "Tower", "Cap", "Beacon", "BeaconBase", "Hose"): self.assertIn(f"Yard_Gate_{p}_{t}", self.by)
            for f in "FB":
                for p in ("Warn", "Panel", "Brace", "Strip", "Vent", "Hazard"): self.assertTrue(any(n.startswith(f"Yard_Gate_{p}_{t}{f}") for n in self.by), (p, t, f))
            self.assertEqual(len([n for n in self.by if n.startswith(f"Yard_Gate_Emitter_{t}_")]), 9)
        for f in "FB":
            sg = self.by[f"Yard_Gate_Sign_{f}"]; self.assertEqual(sg["uv_region"], "sign"); self.assertAlmostEqual(sg["size"][0] / sg["size"][1], 1024 / 300, places=2)
        M = self.L["materials"]; self.assertEqual(M["gate_atlas"]["type"], "screen_atlas"); self.assertEqual(set(M["gate_atlas"]["atlas"]), {"sign", "warn"})
        self.assertTrue(os.path.exists(os.path.join(ROOT, "levels", "assembly_ascent", "references", "laser_gate_atlas.png")))

    def test_still_a_working_gate(self):
        g = next(g for g in self.L["gates"] if g["id"] == "Yard_Laser"); self.assertTrue(g["closed_at_start"]); self.assertEqual(g["opens_on"]["terminal"], "Jet_Screen_Button")
        self.assertEqual(len([n for n in self.by if n.startswith("Yard_Laser_Beam_")]), 9)
        E = {e["id"] for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}; self.assertIn("Screen_Pulse_beacon_red", E)  # the beacons flash

    def test_pylons_stand_on_the_deck(self):
        """The gate fits the yard's round deck: its pylons stand on it (no tower hanging over the slime)."""
        import math
        ring = next(p for p in json.load(open(os.path.join(LV, "scene_spec.json")))["platforms"] if p["id"] == "Robot_Ring")
        cx, cz = ring.get("center", ring.get("position")); R = ring["size"][0] / 2; g = self.by["Yard_Gate"]
        for t, sd in (("L", -1), ("R", 1)):
            f = self.by[f"Yard_Gate_Foot_{t}"]; lx = f["position"][0]  # local x across the gate (yaw 90: world z)
            wz = g["position"][2] - lx  # yaw 90 maps local x -> world -z
            self.assertLess(math.hypot(g["position"][0] - cx, wz - cz), R + 0.2)


if __name__ == "__main__":
    unittest.main()
