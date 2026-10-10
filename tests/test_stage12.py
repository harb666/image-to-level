"""Stage 12: liquids flow the right way (flow_uv), fly-by ships fade in/out (no popping), holed blocks and the
elevator_shaft structure (real hole, shaft dressing, level_exit trigger -> collision.json triggers)."""
import json, os, subprocess, sys, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


def _shaft_spec(style=None, shape="circle"):
    s = small_spec(); p = {"id": "A", "shape": shape, "center": [0, 0], "size": [14, 14], "top": 4}
    if style: p["style"] = style
    s["platforms"][0] = p; s["structures"] = [{"id": "Lift", "kind": "elevator_shaft", "on": "A", "radius": 3, "target": "level_2"}]
    return s


class Flow(unittest.TestCase):
    def test_flow_uv_points_downstream_in_gltf_uv(self):
        import trimesh, effects
        # vertical quad, trimesh v grows upward -> glTF v (= 1 - v) grows downward -> falling liquid flows +v in glTF
        m = trimesh.Trimesh([[0, 0, 0], [4, 0, 0], [4, 10, 0], [0, 10, 0]], [[0, 1, 2], [0, 2, 3]], process=False)
        m.visual = trimesh.visual.TextureVisuals(uv=np.array([[0, 0], [1, 0], [1, 1], [0, 1.0]]))
        sc = trimesh.Scene(); sc.add_geometry(m, node_name="Fall", geom_name="Fall")
        f = effects.flow_uv(sc, "Fall", None, {}); self.assertAlmostEqual(float(f[0]), 0.0, 3); self.assertAlmostEqual(float(f[1]), 1.0, 3)
        m.visual.uv[:, 1] = 1 - m.visual.uv[:, 1]  # flipped mapping -> flow flips too
        f = effects.flow_uv(sc, "Fall", None, {}); self.assertAlmostEqual(float(f[1]), -1.0, 3)

    def test_runtimes_scroll_along_flow_uv(self):
        gd = open(os.path.join(PIPE, "godot_fx", "liquid_flow.gdshader")).read(); js = open(os.path.join(PIPE, "viewer.html")).read()
        ap = open(os.path.join(PIPE, "godot_fx", "apply_effects.gd")).read()
        self.assertIn("uv -= flow_dir * TIME * uv_speed", gd)  # sample at uv - f t -> the pattern moves +f (downstream)
        self.assertIn('"flow_dir"', ap); self.assertIn("fx.flow_uv", js)

    def test_streaky_falls_material(self):
        import materials
        a = materials.maps({"type": "toxic", "color": [0.4, 1, 0.2], "res": 64, "streaks": True})["alb"].astype(float).mean(2)
        self.assertGreater(float(np.std(a.mean(0))), 2 * float(np.std(a.mean(1))))  # varies across, smooth along the fall


class Flyby(unittest.TestCase):
    def test_ships_shrink_away_instead_of_popping(self):
        for f in ("viewer.html", os.path.join("godot_fx", "apply_effects.gd")):
            src = open(os.path.join(PIPE, f)).read(); self.assertIn("env", src); self.assertIn("(1-env)" if f.endswith("html") else "(1.0 - env)", src)
        import effects
        self.assertIn("shrink", effects.flyby_paths.__doc__)


class Holes(unittest.TestCase):
    def test_holed_blocks_are_watertight_and_keep_their_outline(self):
        import shapes
        for o in ({"type": "cylinder", "size": [14, 1, 14], "sections": 24}, {"type": "cylinder", "size": [14, 1, 14], "sections": 8},
                  {"type": "box", "size": [12, 1, 8]}, {"type": "frustum", "size": [14, 2, 14], "sections": 8, "bottom_scale": 0.5}):
            m = shapes.make(dict(o, hole=3.0)); self.assertTrue(m.is_watertight, o); self.assertGreater(m.volume, 0, o)
            self.assertAlmostEqual(float(m.extents[2 if o["type"] == "box" else 0]), o["size"][2 if o["type"] == "box" else 0], delta=1.2)
            r = np.hypot(m.vertices[:, 0], m.vertices[:, 2]); self.assertAlmostEqual(float(r.min()), 3.0, 3)  # the hole is round
        box = shapes.make({"type": "box", "size": [12, 1, 8], "hole": 3.0})
        self.assertAlmostEqual(float(box.volume), 12 * 8 - 12 * 9 * np.sin(2 * np.pi / 24), delta=0.5)  # rect, not round
        with self.assertRaises(ValueError): shapes.make({"type": "box", "size": [6, 1, 6], "hole": 3.0})


class Elevator(unittest.TestCase):
    def test_shaft_cuts_every_platform_style(self):
        import spec_to_level
        for style, shape in ((None, "circle"), ("sky_pylon", "circle"), ("industrial_pillar", "octagon"), ("stone_plinth", "rect")):
            d = tmp_level(name="lift"); spec_to_level.run(write_spec(d, _shaft_spec(style, shape)), d, verbose=False)
            L = json.load(open(os.path.join(d, "level.json"))); by = {o["name"]: o for o in L["objects"]}
            (ex,) = L["exits"]; self.assertEqual((ex["id"], ex["target"], ex["type"]), ("Lift_Exit", "level_2", "level_exit"))
            floor = by.get("A_Floor") or by["A_Cap"]; self.assertEqual(floor["hole"], 3.4); self.assertTrue(floor["collision_mesh"])
            yb = by["Lift_Liner"]["position"][1]; self.assertGreaterEqual(yb, 1.3 - 1e-6, style)  # above the hazard floor (y 1)
            for o in L["objects"]:  # nothing solid left inside the shaft between its floor and the deck
                if o["name"].startswith("A") and o.get("size") and not o.get("hole") and o["type"] in ("box", "cylinder", "frustum"):
                    self.assertLessEqual(o["position"][1] + o["size"][1], yb + 0.01, f"{style}: {o['name']} blocks the shaft")
            self.assertTrue(any(n.startswith("Lift_Panel") for n in by)); self.assertLess(ex["center"][1] + ex["height"] / 2, 4.0)

    def test_off_centre_shaft_is_skipped(self):
        import spec_to_level
        s = _shaft_spec(); s["structures"][0]["offset"] = [2, 0]; d = tmp_level(name="off")
        spec_to_level.run(write_spec(d, s), d, verbose=False); L = json.load(open(os.path.join(d, "level.json")))
        self.assertFalse(L.get("exits")); self.assertFalse(any(o.get("hole") for o in L["objects"]))

    @unittest.skipUnless(FULL, "QUICK=1")
    def test_build_exports_trigger_and_open_shaft(self):
        import spec_to_level
        from gameplay import analyse
        d = tmp_level(name="liftb"); spec_to_level.run(write_spec(d, _shaft_spec("sky_pylon")), d, verbose=False)
        subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        C = json.load(open(os.path.join(d, "mobile", "collision.json")))
        self.assertEqual([t["id"] for t in C["triggers"]], ["Lift_Exit"])
        kinds = {c["name"]: c.get("shape") or c.get("type") for c in C["colliders"]}
        self.assertEqual(kinds.get("A_Floor"), "mesh")  # concave collider keeps the hole open
        import trimesh
        sc = trimesh.load(os.path.join(d, "mobile", "collision.glb"), force="scene").dump(concatenate=True)
        T = sc.triangles[sc.triangles[:, :, 1].min(1) > 2.0][:, :, [0, 2]]  # collision triangles at deck height, in plan
        cr = lambda a, b: (a[:, 0] - b[:, 0]) * (0 - b[:, 1]) - (a[:, 1] - b[:, 1]) * (0 - b[:, 0])
        s0, s1, s2 = cr(T[:, 0], T[:, 1]), cr(T[:, 1], T[:, 2]), cr(T[:, 2], T[:, 0])
        inside = ((s0 > 1e-9) & (s1 > 1e-9) & (s2 > 1e-9)) | ((s0 < -1e-9) & (s1 < -1e-9) & (s2 < -1e-9))
        self.assertFalse(inside.any(), "nothing at deck height may cover the shaft axis")
        self.assertGreater(analyse(d, write=False, verbose=False)["reachable_area_m2"], 50)
        self.assertIn("level_exit", open(os.path.join(d, "mobile", "apply_mobile.gd")).read())


if __name__ == "__main__":
    unittest.main()
