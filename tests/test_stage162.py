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


if __name__ == "__main__":
    unittest.main()
