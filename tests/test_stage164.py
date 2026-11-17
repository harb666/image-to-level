"""Stage 164: the slime reactor in the east pool (the user's concept, without its drawing)."""
import json, math, os, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class Reactor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}
        cls.R = {n: o for n, o in cls.by.items() if n.startswith("Reactor")}
        cls.E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}

    def test_parts(self):
        for k in ("Reactor_Plinth", "Reactor_Deck", "Reactor_VatGlass", "Reactor_Cap", "Reactor_PipeMain", "Reactor_Pipe_1", "Reactor_Pipe_2", "Reactor_Catwalk_3_Pier"): self.assertIn(k, self.R)
        g = self.R["Reactor_VatGlass"]; self.assertTrue(g.get("tube")); self.assertNotEqual(g.get("collision"), False)
        self.assertEqual(self.L["materials"][g["material"]]["type"], "glow")  # glowing slime glass, no drawing in it
        self.assertFalse([n for n, o in self.R.items() if self.L["materials"].get(o.get("material"), {}).get("type") in ("chevron", "hazard_wrap")])  # no hazard stripes (user)

    def test_falls_clear_of_the_deck(self):
        """The spouts pour past the deck's edge (seen, not hidden under it); they are pours with splashes."""
        c = self.R["Reactor_Plinth"]["position"]; D = self.R["Reactor_Deck"]
        for k in (1, 2):
            n = f"Reactor_Spout_{k}_Fall"; self.assertIn(n, self.R); self.assertEqual(self.R[n]["material"], "fall")
            self.assertGreater(self.R[n]["position"][2], D["size"][0] / 2)  # (local z, in its spout group)
        self.assertIn("Reactor_Steam", self.E)

    def test_clear_of_the_route_and_the_ceiling_rigs(self):
        P = self.R["Reactor_Plinth"]["position"]
        for n, o in self.by.items():
            if n.startswith("Pillars_") or n.startswith("Arena_Tile"):
                self.assertGreater(math.hypot(o["position"][0] - P[0], o["position"][2] - P[2]), 12.0, n)
        beam = self.by["CraneRail_01_Beam"]
        for n in ("Reactor_PipeTop_1", "Reactor_PipeTop_2"):
            self.assertGreater(abs(self.R[n]["position"][2] - beam["position"][2]), 1.2)  # the pipes miss the crane runway
        rip = self.E["Hazard_Surface"]["ripples"]; self.assertLessEqual(len(rip), 24)
        self.assertTrue(any(math.hypot(r[0] - P[0], r[1] - P[2]) < 1 for r in rip))  # rings round the reactor's base

    def test_preview_fits(self):
        p = os.path.join(ROOT, "dist", "assembly_ascent", "preview_mobile.html")
        if os.path.exists(p): self.assertLess(os.path.getsize(p), 16 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
