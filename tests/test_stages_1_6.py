"""Regression tests: Stages 1-6 still work (materials, sky/background, shapes, build, effects, mobile, edits, preview)."""
import json, os, subprocess, sys, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level


class Stage1Materials(unittest.TestCase):
    def test_every_pbr_kind_makes_maps(self):
        from materials import PBR, maps
        for k in PBR:
            d = maps({"type": k, "color": [0.5, 0.5, 0.5], "res": 32})
            for key in ("alb", "h", "rough", "metal"):
                self.assertEqual(np.asarray(d[key]).shape[:2], (32, 32), f"{k}.{key}")
                self.assertTrue(np.isfinite(d[key]).all(), f"{k}.{key} finite")

    def test_legacy_kinds_still_work(self):
        from materials import maps
        for k in ("cobblestone", "stone_brick", "wood", "plaster", "roof_tiles", "window"):
            self.assertEqual(np.asarray(maps({"type": k, "color": [0.6, 0.5, 0.4], "res": 32})["alb"]).shape[:2], (32, 32))


class Stage2Sky(unittest.TestCase):
    def test_presets_render_seamless(self):
        import sky
        for p in sky.PRESETS:
            img, info = sky.render({"preset": p}, 128)
            self.assertEqual(img.shape, (64, 128, 3))
            self.assertLess(np.abs(img[:, 0] - img[:, -1]).mean(), 0.06, f"{p}: seam")
            self.assertIn("horizon_rgb", info)

    def test_background_generators(self):
        from backdrop import GENERATORS, QUALITY
        q = QUALITY["performance"]
        for t, L in (("ground", dict(radius=[0, 300], flat_radius=40)), ("mountain_ring", dict(radius=300, depth=50, height=[30, 80])),
                     ("spires", dict(radius=[90, 200], count=6, height=[20, 50])), ("skyline", dict(radius=200, count=8)), ("factory", dict(azimuth_deg=40, distance=150))):
            m = GENERATORS[t](dict(L, id=t, type=t), q); self.assertGreater(len(m.faces), 10, t)
        from backdrop import _spire  # open-based spires must face outward (culled in Godot otherwise)
        m = _spire(np.random.default_rng(2), 40, 6); c = m.triangles_center; ax = c * [0, 1, 0]
        self.assertGreater((np.einsum("ij,ij->i", m.face_normals, c - ax) > 0).mean(), 0.75)


class Stage3Shapes(unittest.TestCase):
    def test_closed_primitives(self):
        import shapes
        for t in shapes.SHAPES:
            m = shapes.make({"type": t, "size": [4, 3, 2], "seed": 3})
            bodies = m.split(only_watertight=False)
            self.assertTrue(all(b.is_watertight for b in bodies), f"{t}: open body")


class Stages3to6Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tmp_level("test_primitives")
        subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), cls.d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_build_outputs(self):
        import trimesh
        L = json.load(open(os.path.join(self.d, "level.json"))); s = trimesh.load(os.path.join(self.d, "level.glb"), force="scene")
        names = set(s.graph.nodes)
        for o in L["objects"]:
            if o["type"] != "terrain": self.assertIn(o["name"], names)
        for f in ("background.glb", "environment.json", "environment.tres", "mobile/level_mobile.glb", "mobile/collision.json", "mobile/mobile_manifest.json"):
            self.assertTrue(os.path.exists(os.path.join(self.d, f)), f)

    def test_mobile_fewer_draw_calls(self):
        M = json.load(open(os.path.join(self.d, "mobile", "mobile_manifest.json")))["metrics"]
        self.assertLess(M["mobile"]["level"]["draw_calls_unbatched"], M["dev"]["level"]["draw_calls_unbatched"])
        self.assertGreater(json.load(open(os.path.join(self.d, "mobile", "collision.json")))["colliders"].__len__(), 0)

    @unittest.skipUnless(FULL, "QUICK=1")
    def test_camera_validator_passes_on_fixed_fixture(self):
        from validate_level import validate
        self.assertTrue(validate(self.d, verbose=False)["passed"])

    def test_preview_embeds_everything(self):
        out = os.path.join(self.d, "p.html")
        subprocess.run([sys.executable, os.path.join(PIPE, "make_preview.py"), self.d, "T", out], check=True, stdout=subprocess.DEVNULL)
        s = open(out).read()
        for k in ("window.GLB=", "window.TEX=", "window.GAMEPLAY=", "const meta={"): self.assertIn(k, s)


class Stage6Edits(unittest.TestCase):
    def test_edit_undo_restores_exactly(self):
        import edit_level as E
        d = tmp_level("toxic_arena"); orig = json.load(open(os.path.join(d, "level.json")))
        E.edit(d, "resize", ["Central_Platform", "1.25", "1", "1.25"]); E.edit(d, "rename", ["Central_Tower", "Hub_Tower"])
        E.edit(d, "material", ["OuterWall_North", "metal_grate"])
        L = json.load(open(os.path.join(d, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        self.assertEqual(by["Central_Platform_Base"]["size"][0], 27.5); self.assertIn("Hub_Tower_Body", by)
        for _ in range(3): E.edit(d, "undo", [])
        self.assertEqual(json.load(open(os.path.join(d, "level.json"))), orig)

    def test_invalid_edit_refused(self):
        import edit_level as E
        d = tmp_level("toxic_arena"); orig = json.load(open(os.path.join(d, "level.json")))
        with self.assertRaises(SystemExit): E.edit(d, "set", ["Central_Tower_Body", "size=[1,2]"])  # wrong size shape
        with self.assertRaises(SystemExit): E.edit(d, "material", ["OuterWall_North", "no_such_material"])
        self.assertEqual(json.load(open(os.path.join(d, "level.json"))), orig)

    def test_apply_ops_schema(self):
        import edit_level as E
        d = tmp_level("toxic_arena")
        with self.assertRaises(SystemExit): E.apply_ops(d, [{"op": "resize", "target": "Central_Platform"}])  # missing scale
        sc = E.apply_ops(d, [{"op": "resize", "target": "Platform_North_01", "scale": [2, 1, 1]}, {"op": "env", "values": {"sky.preset": "alien"}}])
        self.assertEqual(sc, "full"); L = json.load(open(os.path.join(d, "level.json")))
        self.assertEqual(L["environment"]["sky"]["preset"], "alien")


if __name__ == "__main__":
    unittest.main()
