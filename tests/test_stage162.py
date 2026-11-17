"""Stage 162: the preview's test player is invincible by default (God button) - hazards, maces, saws, spikes and crushers
report what would have killed them instead of respawning them. The game (apply_effects.gd) is unchanged."""
import os, re, unittest
from _util import ROOT


class GodMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read()

    def test_on_by_default_with_a_toggle(self):
        self.assertIn('<button id="godb">God: on</button>', self.v); self.assertIn("let god=true", self.v)
        self.assertIn("const kill=m=>{if(god)", self.v); self.assertIn("window.setGod=", self.v)

    def test_every_hazard_goes_through_kill(self):
        for m in ("☣ Slimed!", "🔺 Spiked!", "🌀 Swept!", "💥 Spiked!", "🪚 Sliced!", "💥 Crushed!"): self.assertIn(f"kill('{m}')", self.v)
        self.assertNotRegex(self.v, r"spawn\(\);say\(")  # no hazard respawns the player directly any more
        self.assertNotIn("startsWith('Hazard')&&pos.y-meta.eye_height<h.point.y+0.3){spawn();}", self.v)
        self.assertEqual(len(re.findall(r"kill_y\?\?-40\)\)spawn\(\)", self.v)), 1)  # falling out of the world still respawns (or they would fall for ever)


class TunnelMouth(unittest.TestCase):
    def test_no_hazard_kerb_and_no_gap(self):
        """Stage 163 (user): nothing marks the tunnel's mouth - no striped kerb; the slime runs on to where the pour starts."""
        import json
        L = json.load(open(os.path.join(ROOT, "levels", "assembly_ascent", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        self.assertFalse([n for n in by if n.startswith("East_SlimeTunnel") and by[n].get("material") in ("stripe", "trim")])
        lq, po = by["East_SlimeTunnel_Liquid"], by["East_SlimeTunnel_Pour"]
        self.assertGreaterEqual(lq["position"][2] + lq["size"][2] / 2, po["position"][2])  # (local z: out of the tunnel)


if __name__ == "__main__":
    unittest.main()
