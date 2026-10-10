"""Stage 10 (Sky Citadel refinement): slope-following railings + post validation/repair, layered cloud effects,
hull/chevron materials, tower decor kit, per-level mobile overrides. Generic rules on synthetic scenes."""
import json, math, os, subprocess, sys, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


def build(d):
    subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def findings(d, check):
    import geometry_check
    R = geometry_check.run(d, verbose=False, write=False)
    return [f for f in R["findings"] if f["check"] == check]


class Railings(unittest.TestCase):
    def test_posts_follow_a_polyline(self):
        import shapes
        pts = [[0, 0, 0], [0, 1.5, 8], [3, 1.5, 10]]
        P = shapes.rail_posts(pts, 1.6)
        self.assertTrue(np.allclose(P[0], pts[0]) and np.allclose(P[-1], pts[-1]))
        self.assertTrue(any(np.allclose(p, pts[1]) for p in P), "corner / slope change must carry a post")
        gaps = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2])); self.assertLessEqual(gaps.max(), 1.6 + 1e-6)
        k = np.flatnonzero(np.isclose(P[:, 2], 4.8))[0]; self.assertAlmostEqual(P[k, 1], 0.9, 3)  # on the slope line

    def test_rail_run_mesh_slopes_with_vertical_posts(self):
        import shapes
        m = shapes.make({"type": "rail_run", "size": [8, 1.05, 0.07], "points": [[0, 0, 0], [0, 2, 8]]})
        lo, hi = m.bounds
        self.assertAlmostEqual(lo[1], -0.02, 2)              # posts sunk 2 cm into the floor, not floating
        self.assertAlmostEqual(hi[1], 2 + 1.05, 1)           # top rail follows the slope up to the high end
        near_lo = m.vertices[m.vertices[:, 2] < 0.1]; self.assertLess(near_lo[:, 1].max(), 1.2)  # low end stays low

    @unittest.skipUnless(FULL, "QUICK=1")
    def test_floating_legacy_railing_is_detected_and_snapped(self):
        from test_stage8 import mini, GROUND
        import geometry_repair
        # a 6 m ramp rising 2 m along z and a horizontal (legacy) railing along its edge: floats at one end, sunk at the other
        d = mini([GROUND, dict(name="Deck", type="box", position=[0, 0, -7], size=[8, 2, 4], material="a"),
                  dict(name="Ramp_1", type="ramp", position=[0, 0, -2], rotation=[0, 180, 0], size=[3, 2, 6], material="b"),
                  dict(name="Rail_1", type="railing", position=[1.4, 1.0, -2], rotation=[0, 90, 0], size=[5, 1.05, 0.06], material="b")])
        E = findings(d, "railing"); self.assertTrue(E and "Rail_1" in E[0]["message"], E)
        self.assertEqual(E[0]["repair"]["action"], "snap_rail")
        geometry_repair.repair(d, verbose=False)
        self.assertFalse(findings(d, "railing"))
        o = next(o for o in json.load(open(os.path.join(d, "level.json")))["objects"] if o["name"] == "Rail_1")
        self.assertEqual(o["type"], "rail_run"); ys = [p[1] for p in o["points"]]; self.assertGreater(max(ys) - min(ys), 1.0)

    @unittest.skipUnless(FULL, "QUICK=1")
    def test_generated_ramp_rails_stand_on_the_deck(self):
        import spec_to_level
        d = tmp_level(name="rails")
        s = small_spec(connections=[{"id": "Br_AB", "from": "A", "to": "B", "rails": True}, {"id": "Ln_AC", "from": "A", "to": "C", "rails": True, "kind": "ramp"}])
        spec_to_level.run(write_spec(d, s), d, verbose=False); build(d)
        L = json.load(open(os.path.join(d, "level.json"))); R = [o for o in L["objects"] if o["type"] == "rail_run"]
        self.assertTrue(R); self.assertFalse(any(o["type"] == "railing" for o in L["objects"]))
        self.assertFalse(findings(d, "railing"))


class Clouds(unittest.TestCase):
    def test_puff_rings_surround_targets_deterministically(self):
        import effects
        e = dict(id="C", type="cloud_puffs", around_points=[[10, -5, 20, 2, 6, 8]], size=[6, 8])
        a = effects._puff_rings(e, {}, effects.TYPES["cloud_puffs"]["defaults"]); b = effects._puff_rings(e, {}, effects.TYPES["cloud_puffs"]["defaults"])
        self.assertEqual(a, b); self.assertEqual(len(a), 8)
        for p in a:
            r = math.hypot(p["pos"][0] - 10, p["pos"][2] + 5); self.assertTrue(15 <= r <= 27, r); self.assertTrue(2 <= p["pos"][1] <= 6)
        boxes = {"Col_1": np.array([[0, -10, 0], [2, 30, 2]], float)}
        r2 = effects._puff_rings(dict(id="K", type="cloud_puffs", around_targets_glob=["Col_*"], y=[0, 12], size=[4, 6]), boxes, effects.TYPES["cloud_puffs"]["defaults"])
        self.assertTrue(r2 and all(0 <= p["pos"][1] <= 12 for p in r2))

    @unittest.skipUnless(FULL, "QUICK=1")
    def test_cloud_effects_stay_below_the_decks(self):
        import spec_to_level
        d = tmp_level(name="clouds")
        s = small_spec(atmosphere={"sky": "sunset", "height_fog": {"height": 1.0, "density": 0.05},
                                   "clouds": {"layers": [{"y": 50, "radius": 200}], "collars": {"glob": ["*_Body"], "y": [0, 50]}, "horizon": [150]}})
        spec_to_level.run(write_spec(d, s), d, verbose=False); build(d)
        F = json.load(open(os.path.join(d, "effects.json"))); by = {e["id"]: e for e in F["effects"]}
        lay = by["Cloud_Layer_1"]["quality"]["balanced"]["params"]; self.assertLessEqual(lay["y"], 4 - 6 + 1e-6)  # clamped under the lowest deck
        self.assertEqual(by["Cloud_Layer_1"]["category"], "cloud_layer")
        dist = by["Cloud_Distant"]; self.assertEqual(dist["quality"]["balanced"]["cost_estimate"]["extra_draw_calls"], 1)  # one instanced draw
        perf = len(dist["emitters_by_quality"]["performance"]); bal = len(dist["emitters_by_quality"]["balanced"]); self.assertLess(perf, bal)
        self.assertTrue(os.path.exists(os.path.join(d, "fx", "cloud.png")))
        E = json.load(open(os.path.join(d, "environment.json"))); self.assertAlmostEqual(E["fog"]["height_density"], 0.05)


class MaterialsAndDetail(unittest.TestCase):
    def test_new_material_kinds(self):
        import materials
        for m in ({"type": "hull_plating", "color": [0.3, 0.28, 0.27], "res": 64}, {"type": "chevron", "color": [0.9, 0.7, 0.1], "res": 64}):
            d = materials.maps(m)
            for k in ("alb", "rough", "metal"): self.assertTrue(np.isfinite(d[k]).all(), (m["type"], k))
            self.assertGreater(float(np.std(d["rough"])), 0.02, m["type"] + ": roughness must vary (not uniformly glossy)")
        a = materials.maps({"type": "scifi_floor", "color": [0.5, 0.5, 0.5], "res": 64}); b = materials.maps({"type": "scifi_floor", "color": [0.5, 0.5, 0.5], "res": 64, "gloss": 0.5, "metallic": 0.45})
        self.assertLess(float(b["rough"].mean()), float(a["rough"].mean())); self.assertGreater(float(b["metal"].mean()), float(a["metal"].mean()))

    def test_tower_decor_kit_uses_shared_materials(self):
        import spec_to_level
        s = small_spec(structures=[{"id": "T", "kind": "tower", "on": "A", "size": [3, 14, 3], "decor": ["bands", "pipes", "boxes", "hazard", "antenna"]}])
        d = tmp_level(name="decor"); L, _ = spec_to_level.run(write_spec(d, s), d, verbose=False, dry=True)
        names = {o["name"] for o in L["objects"]}
        for part in ("T_Band_1", "T_Pipe_02L", "T_Box_02", "T_Plinth", "T_Chevron_01", "T_Mast_1", "T_Beacon_1"): self.assertIn(part, names)
        mats = {o.get("material") for o in L["objects"] if o["name"].startswith("T_")}
        self.assertLessEqual(mats - {"wall", "structure_b", "frame", "machine", "trim", "stripe", "accent", "glow"}, set())

    def test_mobile_overrides_reach_level_json(self):
        import spec_to_level
        d = tmp_level(name="mob"); L, _ = spec_to_level.run(write_spec(d, small_spec(mobile={"cell": 64})), d, verbose=False, dry=True)
        self.assertEqual(L["mobile"]["cell"], 64)


if __name__ == "__main__":
    unittest.main()
