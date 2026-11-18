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
        """Stage 172: every corner of both pylon feet is on the round deck (its real 24-sided outline) - nothing hangs
        over the slime - and the deck has curved away behind each foot (no way round the gate)."""
        import sys; sys.path.insert(0, os.path.join(ROOT, "pipeline")); import architecture as A
        from anchors import world_matrices
        ring = next(p for p in json.load(open(os.path.join(LV, "scene_spec.json")))["platforms"] if p["id"] == "Robot_Ring"); poly = A.footprint_poly(ring)
        def inside(x, z):
            c = False
            for i in range(len(poly)):
                (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % len(poly)]
                if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1: c = not c
            return c
        Wm, _ = world_matrices({"objects": self.L["objects"]}); import numpy as np
        for t in "LR":
            f = self.by[f"Yard_Gate_Foot_{t}"]; w, h, d = f["size"]
            for lx in (-w / 2, w / 2):
                for lz in (-d / 2, d / 2):
                    p = Wm[f["name"]] @ np.array([lx, 0, lz, 1.0]); self.assertTrue(inside(p[0], p[2]), (t, round(p[0], 2), round(p[2], 2)))
        self.assertNotIn("Yard_Gate_FloorStrip_F", self.by); self.assertNotIn("Yard_Gate_FloorStrip_B", self.by)

if __name__ == "__main__":
    unittest.main()
