"""Stage 11: reusable art-style presets (alien_cartoon): opt-in merge, toon materials, outline shells (ignored by
checks / navigation / colliders), alien satellites, hover satellites, striped planet + stylised clouds."""
import json, os, subprocess, sys, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


class Preset(unittest.TestCase):
    def test_opt_in_only(self):
        import styles
        s = small_spec(); self.assertEqual(styles.apply(s), s)  # no art_style -> untouched

    def test_spec_wins_over_preset(self):
        import styles
        s = small_spec(art_style="alien_cartoon", materials={"roles": {"deck": {"type": "concrete", "color": [1, 0, 0], "tile_m": 2}}})
        out = styles.apply(s)
        self.assertEqual(out["materials"]["roles"]["deck"]["color"], [1, 0, 0])            # explicit spec value kept
        self.assertTrue(out["materials"]["roles"]["wall"]["toon"])                          # preset fills the rest
        self.assertTrue(out["atmosphere"]["sky_overrides"]["planet"]["stripes"])           # striped planet
        self.assertIn("outline", out["style"])

    def test_scatter_trees_become_satellites(self):
        import styles
        s = small_spec(art_style="alien_cartoon", world={"size": [100, 100], "scatter": [{"id": "T", "kinds": ["conifer", {"kind": "bush", "weight": 0.5}], "density": 2.0}]})
        sc = styles.apply(s)["world"]["scatter"][0]
        self.assertEqual(sc["kinds"][0], "sat_spire"); self.assertEqual(sc["kinds"][1]["kind"], "sat_pod"); self.assertEqual(sc["style"], "alien_cartoon")


class Pieces(unittest.TestCase):
    def test_toon_material_is_flat_matte_and_inked(self):
        import materials
        a = materials.maps({"type": "hull_plating", "color": [0.3, 0.25, 0.4], "res": 64})
        b = materials.maps({"type": "hull_plating", "color": [0.3, 0.25, 0.4], "res": 64, "toon": True})
        self.assertEqual(float(b["metal"].max()), 0.0); self.assertGreater(float(b["rough"].min()), 0.8)
        self.assertLess(float(b["alb"].min()), float(a["alb"].min()) + 0.02)  # dark ink present

    def test_outline_hull_is_inverted_and_larger(self):
        import trimesh, build_level
        m = trimesh.creation.box([2, 2, 2]); h = build_level.outline_hull(m, 0.1)
        self.assertLess(h.volume, 0); self.assertAlmostEqual(float(h.bounds[1][0]), 1.0 + 0.1 / np.sqrt(1) * 1, delta=0.1)

    def test_satellites_and_hover_layer(self):
        import scatter, backdrop
        for k in ("sat_dish", "sat_pod", "sat_spire"):
            for parts, meta in scatter.variants(k, "alien_cartoon", 3):
                n = sum(len(m.faces) for m in parts.values()); self.assertLess(n, 400, k)
                self.assertTrue({"light", "light_b"} & set(parts), k + ": needs glowing lights")
        m = backdrop.hover_satellites(dict(id="H", radius=[200, 400], count=8, elevation=[60, 120], seed=2), backdrop.QUALITY["balanced"])
        self.assertGreater(m.bounds[0][1], 30)  # hovering, not standing on the ground

    def test_striped_planet_is_kept_and_visible(self):
        import sky
        cfg = {"preset": "sunset", "planet": {"azimuth_deg": 0, "elevation_deg": 30, "size_deg": 30, "color": [1.0, 0.3, 0.6],
                                               "stripes": {"strength": 0.6, "frequency": 300, "color": [1, 0.8, 0.9]}, "over_clouds": True}}
        img, _ = sky.render(cfg, 512); H, W = img.shape[:2]
        col = img[int(H * (0.5 - 30 / 180)) - 8: int(H * (0.5 - 30 / 180)) + 8, int(W * 0.25)]  # az 0 = north = -z -> u = 0.25
        self.assertGreater(float(np.ptp(col[:, 1])), 0.08, "stripes must stay visible")


@unittest.skipUnless(FULL, "QUICK=1")
class Build(unittest.TestCase):
    def test_outlines_do_not_change_gameplay(self):
        import spec_to_level
        from gameplay import analyse
        d0, d1 = tmp_level(name="plain"), tmp_level(name="zim")
        for d, s in ((d0, small_spec()), (d1, small_spec(art_style="alien_cartoon"))):
            spec_to_level.run(write_spec(d, s), d, verbose=False)
            subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import trimesh
        nodes = trimesh.load(os.path.join(d1, "level.glb"), force="scene").graph.nodes_geometry
        self.assertTrue(any(n.endswith("__ol") for n in nodes))
        a, b = analyse(d0, write=False, verbose=False), analyse(d1, write=False, verbose=False)
        self.assertAlmostEqual(a["reachable_area_m2"], b["reachable_area_m2"], delta=1.0)
        ca = json.load(open(os.path.join(d0, "mobile", "collision.json")))["colliders"]; cb = json.load(open(os.path.join(d1, "mobile", "collision.json")))["colliders"]
        self.assertEqual(len(ca), len(cb)); self.assertFalse(any(c["name"].endswith("__ol") for c in cb))
        E = json.load(open(os.path.join(d1, "environment.json"))); self.assertEqual(E["style"]["name"], "alien_cartoon")


if __name__ == "__main__":
    unittest.main()
