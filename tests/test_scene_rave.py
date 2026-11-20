"""Stage 191 (user): Scene Rave - a hyper-chromatic scenecore / Y2K emo-rave experiment level (no reference image:
the prompt's environment, palette and lighting sections). New: scenecore texture kernels, the scene_rave style
preset, sticker3d / gem / ribbon shapes, the scene.py structures and the "swing" effect."""
import json, math, os, sys, unittest
import numpy as np
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import materials, shapes

LV = os.path.join(ROOT, "levels", "scene_rave")


def _load(p):
    with open(p) as f: return json.load(f)


class SceneRave(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = _load(os.path.join(LV, "level.json")); cls.by = {o["name"]: o for o in cls.L["objects"]}
        cls.E = {e["id"]: e for e in _load(os.path.join(LV, "effects.json"))["effects"]}

    def test_spec_and_checks(self):
        from scene_spec import validate
        E, W = validate(_load(os.path.join(LV, "scene_spec.json"))); self.assertEqual(E, [])
        R = _load(os.path.join(LV, "checks", "report.json")); self.assertEqual(R["counts"]["error"], 0)
        N = _load(os.path.join(LV, "checks", "navigation.json"))
        for a in N["intended_areas"]: self.assertGreaterEqual(a["reachable_fraction"], 0.99, a["name"])
        sp = _load(os.path.join(LV, "scene_spec.json")); self.assertEqual(sp["art_style"], "scene_rave")
        self.assertTrue(any("No reference image" in a for a in sp["interpretation"]["assumptions"]))

    def test_palette(self):
        M = self.L["materials"]; hexes = json.dumps(M)
        for h in ("#FF1493", "#00F5FF", "#B6FF00", "#9D00FF"): self.assertIn(h, hexes)
        self.assertEqual(M["deck"]["type"], "neon_checker"); self.assertEqual(M["wall"]["type"], "sticker_wall")
        for k in ("zebra", "leopard", "holo", "rainbow_trail", "psy_spiral", "glitch_screen"): self.assertIn(k, {m["type"] for m in M.values()}, k)
        env = _load(os.path.join(LV, "environment.json")); lit = json.dumps(env)
        self.assertNotIn('"sun_color": [1.0, 0.62', lit)  # near-white sun: the colour lives in the materials

    def test_kernels(self):
        for t, extra in (("neon_checker", {"accent": "#FF1493"}), ("zebra", {}), ("leopard", {}), ("psy_spiral", {}), ("holo", {}), ("rainbow_trail", {}), ("glitch_screen", {}), ("neon_text", {"text": "RAWR"})):
            d = materials.maps(dict({"type": t, "color": [1, 1, 1], "res": 128}, **extra)); self.assertEqual(d["alb"].shape, (128, 128, 3), t); self.assertIsNotNone(d["emit"], t)
        d = materials.maps({"type": "sticker_wall", "color": [1, 1, 1], "res": 256}); a = d["alb"]
        seam = np.abs(a[:, 0] - a[:, -1]).mean(); mid = np.abs(a[:, 127] - a[:, -1]).mean(); self.assertLess(seam, mid)  # tiles: the edges meet

    def test_shapes_closed(self):
        for ic in ("heart", "star", "bolt", "wing", "diamond2d"):
            m = shapes.sticker3d(3, 3, 0.6, {"icon": ic}); self.assertTrue(m.is_watertight, ic); self.assertGreater(m.volume, 0, ic)
        g = shapes.gem(3, 3.6, 3, {}); self.assertTrue(g.is_watertight)
        r = shapes.ribbon(1.5, 0, 0, {"path": [[0, 0, 0], [5, 2, 3], [10, 1, 0]], "tile": 6}); self.assertEqual(r.metadata["uv"].shape[1], 2)

    def test_dressing(self):
        n = lambda p: [k for k in self.by if k.startswith(p)]
        self.assertGreaterEqual(len([k for k in self.by if k.endswith("_Icon") or k.endswith("_Gem") or k.endswith("_Cranium")]), 20)  # floating icons + skulls
        self.assertGreaterEqual(len([k for k in self.by if "_Bead_" in k]), 150)  # kandi
        self.assertEqual(len(n("Rainbows_")), 4); self.assertTrue(n("DJ_Spiral")); self.assertGreaterEqual(len(n("TV_")), 12)
        self.assertEqual(self.by["DJ_Spiral"]["mobile"], {"merge": False}); self.assertTrue(self.by["DJ_Spiral"].get("spin"))
        for p in ("Zebra_Deck", "Heart_Loft", "Halo_Deck"): self.assertTrue(p + "_Edge" in self.by, p)  # (the 1 m floors have no room for the band)

    def test_swing_motion(self):
        S = [e for e in self.E.values() if e["type"] == "swing"]; self.assertGreaterEqual(len(S), 30)
        wings = [e["swing"] for e in S if "_Wing" in e["swing"]["group"]]; self.assertEqual(len(wings), 20)
        for w in wings: self.assertIn("pre", w); self.assertAlmostEqual(abs(w["pre"]["amp"]), 38.0)
        L_, R_ = [w for w in wings if w["group"].endswith("WingL")], [w for w in wings if w["group"].endswith("WingR")]
        self.assertEqual({w["pre"]["amp"] > 0 for w in L_} & {w["pre"]["amp"] > 0 for w in R_}, set())  # opposite flaps
        self.assertIn("Rainbows_Flow", self.E); self.assertIn("Floor_Beat", self.E)
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read()
        self.assertIn("fx.category==='swing'", v); self.assertIn("_swings", gd); self.assertIn("static func _turn_about", gd)

    def test_budget(self):
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")) / 1024, 4000)


if __name__ == "__main__":
    unittest.main()
