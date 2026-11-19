"""Stage 187 (user): the cog tower WORKS something - a crank pin on the big cog drives a Scotch-yoke crosshead in guide
rails, its rod plunging a piston through a glowing glass pump barrel; steam out of the gearbox and a glow surge at the
bottom of each stroke. Compact: all within the backplate's width."""
import json, math, os, sys, unittest
import numpy as np
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import shapes
from build_level import node_matrix

LV = os.path.join(ROOT, "levels", "assembly_ascent")


def _load(p):
    with open(p) as f: return json.load(f)


class CogPump(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = _load(os.path.join(LV, "level.json")); cls.by = {o["name"]: o for o in cls.L["objects"]}
        cls.E = {e["id"]: e for e in _load(os.path.join(LV, "effects.json"))["effects"]}

    def pin(self, g, t):  # the crank pin's world (x, y) at time t: the gear turns about its axis (world +z) by spin * 2 pi / 60 * t
        rc, a0, _ = g["crank"]; a = a0 + g["spin"] * 2 * math.pi / 60 * t
        return g["position"][0] + rc * math.cos(a), g["position"][1] + rc * math.sin(a)

    def test_pin_on_a_spoke(self):
        for t in "ab":
            g = dict(self.by[f"Showcase_Cogs_{t}_Gear_1"]); rc, a0, L = g["crank"]
            plain = dict(g); plain.pop("crank"); m = shapes.gear(*g["size"], plain); o0 = dict(g, position=[0, 0, 0]); m.apply_transform(node_matrix(o0))
            hit = m.ray.intersects_location([[rc * math.cos(a0), rc * math.sin(a0), 5.0]], [[0, 0, -1]])[0]; self.assertTrue(len(hit))  # the pin stands on metal
            mc = shapes.gear(*g["size"], g); self.assertGreater(len(mc.faces), len(shapes.gear(*g["size"], plain).faces))

    def test_yoke_follows_the_pin(self):
        for t in "ab":
            g = self.by[f"Showcase_Cogs_{t}_Gear_1"]; B = self.E[f"Showcase_Cogs_{t}_Yoke_Bob"]["bob"]; top, bot = self.by[f"Showcase_Cogs_{t}_YokeTop"], self.by[f"Showcase_Cogs_{t}_YokeBottom"]
            self.assertEqual(B["sway"], 0.0)
            lo_, hi_ = bot["position"][1] + bot["size"][1], top["position"][1]  # the slot (rest)
            W = top["size"][0]; cx = top["position"][0]
            for k in range(48):
                tt = B["period"] * k / 48; d = B["amp"] * math.sin(2 * math.pi * (tt + B["phase"]) / B["period"]); px, py = self.pin(g, tt)
                self.assertLess(abs(py - (lo_ + hi_) / 2 - d), 1e-3)  # the pin rides the slot's centre line ...
                self.assertLess(abs(px - cx), W / 2 - 0.12 - 0.09)  # ... between the yoke's end plates
                pis = self.by[f"Showcase_Cogs_{t}_Piston"]; bar = self.by[f"Showcase_Cogs_{t}_Barrel"]; hd = self.by[f"Showcase_Cogs_{t}_PumpHead"]
                self.assertGreaterEqual(pis["position"][1] + d, bar["position"][1] - 1e-6); self.assertLessEqual(pis["position"][1] + pis["size"][1] + d, hd["position"][1] + 1e-6)  # the piston stays in the barrel
                self.assertGreater(bot["position"][1] + d, hd["position"][1] + hd["size"][1] + 0.05)  # the crosshead never hits the pump head ...
                self.assertLess(top["position"][1] + top["size"][1] + d, self.by[f"Showcase_Cogs_{t}_GuideTop"]["position"][1] - 0.02)  # ... or the rails' top bar
            yk = [o for n, o in self.by.items() if n.startswith(f"Showcase_Cogs_{t}_") and (o.get("mobile") or {}).get("group") == f"Showcase_Cogs_{t}_Yoke"]; self.assertEqual(len(yk), 6)

    def test_steam_and_glow_at_bottom_dead_centre(self):
        g = self.by["Showcase_Cogs_a_Gear_1"]; B = self.E["Showcase_Cogs_a_Yoke_Bob"]["bob"]; S = self.E["Cog_Pump_Steam"]["sync"]; P = self.E["Cog_Pump_Glow"]
        t_ = S["at"][0]; d = B["amp"] * math.sin(2 * math.pi * (t_ + B["phase"]) / B["period"]); self.assertAlmostEqual(d, -B["amp"], places=3)  # the blast: at the bottom
        Q = P["quality"]["balanced"]["params"]; self.assertAlmostEqual(math.sin(2 * math.pi * Q["speed"] * t_ + Q["phase"]), 1.0, places=3); self.assertEqual(S["period"], B["period"])
        self.assertEqual(len(self.E["Cog_Pump_Steam"]["emitters"]), 4)
        self.assertIn("Showcase_Cogs_b_BarrelGlow", P["targets"])

    def test_viewer_spin_absolute(self):
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); self.assertIn("multiply(qs.setFromAxisAngle(YA,r*6.283185/60*t))", v)

    def test_compact_and_budget(self):
        for t in "ab":
            pl = self.by[f"Showcase_Cogs_{t}_Plate"]; x0, x1 = pl["position"][0] - pl["size"][0] / 2, pl["position"][0] + pl["size"][0] / 2
            for n, o in self.by.items():
                if n.startswith(f"Showcase_Cogs_{t}_") and o["type"] in ("box", "cylinder") and n != f"Showcase_Cogs_{t}_Plate":
                    self.assertGreaterEqual(o["position"][0] - o["size"][0] / 2, x0 - 0.05, n); self.assertLessEqual(o["position"][0] + o["size"][0] / 2, x1 + 0.05, n)
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")) / 1024, 4000)


if __name__ == "__main__":
    unittest.main()
