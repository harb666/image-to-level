"""Stage 16: expanded slime factory. Wall windows (sill + frame, several per side in the side's own coordinates),
factory dressing (vat / claw / gallery / blast_door), the factory_interior background seen through the windows, and the
size savings (16-bit indices, no normal / ORM maps on toon materials, pick data out of the GLB, --game package)."""
import json, os, shutil, subprocess, sys, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


def _spec():
    s = small_spec(); s["arena"]["size"] = [40, 40]; s["arena"]["walls"] = {"height": 14, "thickness": 2,
        "openings": [{"side": "north", "at": a, "width": 12, "sill": 7, "height": 12} for a in (-11, 11)]}
    s["arena"]["ceiling"] = {"opening": 4.0}; s["art_style"] = "alien_cartoon"
    s["structures"] = [{"id": "Vat_1", "kind": "vat", "position": [12, 12], "size": [5, 10, 5]},
                       {"id": "Claw_1", "kind": "claw", "position": [6, 6], "length": 4},
                       {"id": "Gal_N", "kind": "gallery", "from": [-8, -18.5], "to": [8, -18.5], "y": 10},
                       {"id": "Door_N", "kind": "blast_door", "position": [0, 0, -19.7], "facing": "south", "size": [4, 5, 0.5]}]
    s["background"] = {"layers": [{"id": "F_" + p, "type": "factory_interior", "part": p, "inner": 26, "outer": 70, "roof_y": 30, "towers": 4,
                                   "decks": 4, "gantries": 2, "pillars": 4, "pipes": 2, **({"cutaway": True} if p == "shell" else {})} for p in ("hull", "glass", "lights", "shell")]}
    return s


def _gen(spec, name="fac"):
    import spec_to_level
    d = tmp_level(name=name); spec_to_level.run(write_spec(d, spec), d, verbose=False); return d, json.load(open(os.path.join(d, "level.json")))


class Windows(unittest.TestCase):
    def test_two_windows_on_one_side_stay_where_asked(self):
        _, L = _gen(_spec()); by = {o["name"]: o for o in L["objects"]}
        sills = sorted(by[n]["position"][0] for n in by if n.startswith("OuterWall_North_Op") and n.endswith("_Sill"))
        self.assertEqual([round(x) for x in sills], [-11, 11])
        segs = [o for o in L["objects"] if o["name"].startswith("OuterWall_North_0") and o["type"] == "group"]
        self.assertEqual(len(segs), 3)  # left, middle, right of the two windows
        mull = [n for n in by if "_Frame_Mullion" in n]; self.assertTrue(mull and all(by[n]["collision"] is False for n in mull))


class Dressing(unittest.TestCase):
    def test_vat_claw_gallery_door(self):
        _, L = _gen(_spec()); by = {o["name"]: o for o in L["objects"]}
        g = by["Vat_1_Glass"]; self.assertEqual(g["material"], "glass"); self.assertTrue(g["collision"])  # see-through (Stage 20), solid, not a hazard area
        self.assertNotIn("Vat_1_Glass", L["hazards"])
        self.assertLess(by["Vat_1_Plinth"]["position"][1], 0.5)  # reaches into the slime
        ceil = L["environment"]["indoor"]["ceiling_y"]; ch = by["Claw_1_Chain_1"]; tr = by["Claw_1_Trolley_Body"]
        self.assertAlmostEqual(ch["position"][1] + ch["size"][1], tr["position"][1] + 0.05, 2)  # hangs from its trolley (Stage 31)
        hs = [o for o in L["objects"] if o["name"].startswith("CraneRail_01_Hanger_")]
        self.assertTrue(hs and all(abs(o["position"][1] + o["size"][1] - ceil) < 0.15 for o in hs))  # the rail hangs from the roof
        self.assertTrue(all(o.get("collision") is False for o in L["objects"] if o["name"].startswith(("Claw_1_", "Gal_N_"))))
        self.assertIn("Door_N_Frame", by)

    def test_factory_background_only_indoor_types(self):
        _, L = _gen(_spec()); ids = [l["id"] for l in L["environment"]["background"]]
        self.assertEqual(ids, ["F_hull", "F_glass", "F_lights", "F_shell"])  # no hover satellites from the style preset
        import backdrop
        for p in ("hull", "glass", "lights", "shell"):
            m = backdrop.factory_interior(dict(id="F", part=p, inner=26, outer=70, roof_y=30, towers=4), backdrop.QUALITY["balanced"])
            inside = (np.abs(m.vertices[:, 0]) < 26) & (np.abs(m.vertices[:, 2]) < 26) & (m.vertices[:, 1] > -7) & (m.vertices[:, 1] < 29)
            self.assertFalse(inside.any(), f"{p}: geometry inside the playable hall")


class Slim(unittest.TestCase):
    def test_slim_keeps_geometry_and_shrinks(self):
        import trimesh, glb_tools
        sc = trimesh.Scene()
        for i in range(3):
            b = trimesh.creation.box([1, 1, 1]); b.apply_translation([i * 2, 0, 0]); sc.add_geometry(b, node_name=f"B{i}")
        d = tmp_level(name="slim"); p = os.path.join(d, "t.glb"); sc.export(p)
        a, b = glb_tools.slim(p); self.assertLess(b, a)
        g, _ = glb_tools._read(p); comp = {g["accessors"][pr["indices"]]["componentType"] for m in g["meshes"] for pr in m["primitives"]}
        self.assertEqual(comp, {5123})  # 16-bit
        t = trimesh.load(p, force="scene"); self.assertEqual(sum(len(x.faces) for x in t.geometry.values()), 36)

    @unittest.skipUnless(FULL, "QUICK=1")
    def test_mobile_export_and_game_package(self):
        import package, glb_tools
        d, L = _gen(_spec(), "facb")
        subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        g, _ = glb_tools._read(os.path.join(d, "mobile", "level_mobile.glb"))
        toon = {k for k, v in L["materials"].items() if v.get("toon")}
        for m in g["materials"]:
            if m["name"].split("__")[0] in toon: self.assertNotIn("normalTexture", m, m["name"])
        self.assertFalse(any("source_bounds" in n.get("extras", {}) for n in g["nodes"]))
        self.assertTrue(os.path.exists(os.path.join(d, "mobile", "pick.json")))
        self.assertTrue(os.path.exists(os.path.join(d, "mobile", "background_mobile.glb")))
        out = os.path.join(os.path.dirname(d), "pkg"); r = package.build(d, out_root=out, verbose=False, game=True)
        self.assertTrue(r["valid"], r["errors"]); lv = os.path.join(out, "levels", os.path.basename(d))
        for f in ("level.glb", "background.glb", "mobile/pick.json"): self.assertFalse(os.path.exists(os.path.join(lv, f)), f)
        self.assertTrue(os.path.exists(os.path.join(lv, "mobile", "level_mobile.glb")))


class Level(unittest.TestCase):
    def test_slime_arena_spec(self):
        from scene_spec import validate
        s = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "scene_spec.json"))); self.assertEqual(validate(s)[0], [])
        kinds = [x["kind"] for x in s["structures"]]
        for k in ("vat", "claw", "gallery", "blast_door", "elevator_arrival", "conveyor", "robot_arm", "conduit"): self.assertIn(k, kinds)
        self.assertNotIn("lattice", kinds)  # Stage 55: the user had the maintenance scaffolding removed
        self.assertEqual(s["arena"]["size"], [112, 112])
        self.assertTrue(all(op["sill"] - s["arena"]["walkway"]["y"] > 3 for op in s["arena"]["walls"]["openings"] if op.get("sill")))  # out of reach
        vats = [tuple(x["size"]) for x in s["structures"] if x["kind"] == "vat"]; self.assertEqual(len(vats), len(set(vats)))  # no two vats alike


if __name__ == "__main__":
    unittest.main()
