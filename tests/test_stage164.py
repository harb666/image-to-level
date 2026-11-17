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


class BubbleNozzles(unittest.TestCase):
    """Stage 165: the bubbles come out of nozzles and go into intake tubes - at the tube_bubbles shader's own spots."""
    def test_nozzles_and_intakes_line_up_with_the_bubbles(self):
        L = json.load(open(os.path.join(LV, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}["Tube_Bubbles"]
        self.assertTrue(all(q["params"]["nozzles"] >= 0.85 for q in E["quality"].values()))
        g = by["Reactor_VatGlass"]; r = g["size"][0] / 2; cx, cz = g["position"][0], g["position"][2]
        t = next(t_ for t_ in E["tubes"] if abs(t_[0] - cx) < 0.1 and abs(t_[2] - cz) < 0.1); self.assertAlmostEqual(t[4], r, places=2)
        spots = [(cx + math.cos(math.radians(60 * k)) * 0.44 * r, cz + math.sin(math.radians(60 * k)) * 0.44 * r) for k in range(6)] + [(cx, cz)]
        for k in range(7):
            nz, it = by[f"Reactor_Nozzle_{k + 1}"], by[f"Reactor_Intake_{k + 1}"]
            self.assertTrue(any(math.hypot(nz["position"][0] - a, nz["position"][2] - b) < 0.02 for a, b in spots))
            self.assertAlmostEqual(nz["position"][0], it["position"][0], places=3); self.assertAlmostEqual(nz["position"][2], it["position"][2], places=3)
            self.assertAlmostEqual(nz["position"][1] + nz["size"][1], t[1], places=2)  # bubbles start at the nozzle tips...
            self.assertAlmostEqual(it["position"][1], t[1] + t[3], places=2)  # ...and end at the intake mouths
            self.assertEqual(by[f"Reactor_NozzleHole_{k + 1}"]["material"], "void")
        sv = by["Showcase_TankGlass"]; rs = sv["size"][0] / 2  # the showcase vat's nozzles sit on the same ring
        for k in range(6):
            o = by[f"Showcase_TankNozzle_{k + 1}"]; self.assertAlmostEqual(math.hypot(o["position"][0] - sv["position"][0], o["position"][2] - sv["position"][2]), 0.44 * rs, places=2)


if __name__ == "__main__":
    unittest.main()
