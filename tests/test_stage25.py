"""Stage 25: smallest mobile / game files. WebP textures (EXT_texture_webp), untextured outline meshes without UVs
(welded), mesh extras and GLB merge lists dropped, faces covered by solid boxes culled, the game package minified and
trimmed - and the empty environment.tres bug (package opened the file for writing before reading it) fixed."""
import json, os, unittest
import numpy as np, trimesh
from _util import ROOT, tmp_level


def _scene_glb(path):
    from PIL import Image
    sc = trimesh.Scene(); tex = Image.fromarray((np.random.default_rng(1).random((64, 64, 3)) * 255).astype(np.uint8))
    a = trimesh.creation.box([1, 1, 1]); a.visual = trimesh.visual.TextureVisuals(uv=np.random.default_rng(2).random((len(a.vertices), 2)),
                                                                                   material=trimesh.visual.material.PBRMaterial(name="tex", baseColorTexture=tex))
    b = trimesh.creation.box([1, 1, 1]).subdivide(); b.unmerge_vertices(); b.apply_translation([3, 0, 0])  # split vertices (like a UV-seamed hull)
    b.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(b.vertices), 2)), material=trimesh.visual.material.PBRMaterial(name="ink", baseColorFactor=[0, 0, 0, 255]))
    sc.add_geometry(a, node_name="A"); sc.add_geometry(b, node_name="B"); sc.export(path)


class Slim(unittest.TestCase):
    def test_webp_and_untextured_weld(self):
        import glb_tools
        d = tmp_level(name="s25"); p = os.path.join(d, "t.glb"); _scene_glb(p)
        g0, _ = glb_tools._read(p); v0 = sum(g0["accessors"][pr["attributes"]["POSITION"]]["count"] for m in g0["meshes"] for pr in m["primitives"])
        a, b = glb_tools.slim(p, webp=80); self.assertLess(b, a)
        g, _ = glb_tools._read(p)
        self.assertIn("EXT_texture_webp", g["extensionsRequired"]); self.assertTrue(all(im["mimeType"] == "image/webp" for im in g["images"]))
        self.assertTrue(all("source" not in t and "EXT_texture_webp" in t["extensions"] for t in g["textures"]))
        prims = [pr for m in g["meshes"] for pr in m["primitives"]]
        ink = [pr for pr in prims if g["materials"][pr["material"]]["name"].startswith("ink")]
        self.assertTrue(ink and all("TEXCOORD_0" not in pr["attributes"] for pr in ink))
        self.assertTrue(all("extras" not in m for m in g["meshes"]))
        v1 = sum(g["accessors"][pr["attributes"]["POSITION"]]["count"] for pr in prims); self.assertLess(v1, v0)
        s = trimesh.load(p, force="scene"); self.assertEqual(sum(len(x.faces) for x in s.geometry.values()), 12 + 48)  # same triangles


class Hidden(unittest.TestCase):
    def test_pressed_faces_go_free_faces_stay(self):
        from export_mobile import _hidden
        R = np.eye(3); occ = [("Wall", np.array([0.0, 1.0, 0.0]), np.array([2.0, 1.0, 0.5]), R)]
        m = trimesh.creation.box([1, 1, 1]); m.apply_translation([0, 1, -1.0])  # its +z face is pressed against the wall's -z face
        hid = _hidden(m, occ, "Crate"); n = m.face_normals
        self.assertTrue(hid[n[:, 2] > 0.9].all()); self.assertFalse(hid[n[:, 2] < 0.9].any())
        self.assertFalse(_hidden(m, [("Crate",) + occ[0][1:]], "Crate").any())  # never culled by its own box


class Package(unittest.TestCase):
    def test_game_package_tres_and_trim(self):
        import package
        lv = tmp_level("slime_arena", "slime_arena"); out = os.path.join(os.path.dirname(lv), "pkg")
        r = package.build(lv, out_root=out, verbose=False, game=True); self.assertTrue(r["valid"], r["errors"])
        d = os.path.join(out, "levels", "slime_arena")
        tres = open(os.path.join(d, "environment.tres")).read(); self.assertIn("[gd_resource", tres)
        self.assertIn("res://levels/slime_arena/sky/panorama.jpg", tres)
        L = json.load(open(os.path.join(d, "level.json"))); self.assertNotIn("objects", L); self.assertGreater(L["omitted"]["objects"], 100)
        self.assertIn("exits", L); self.assertIn("entrances", L)
        self.assertFalse(os.path.exists(os.path.join(d, "scene_spec.json")))
        self.assertNotIn("\n ", open(os.path.join(d, "mobile", "collision.json")).read())  # minified
        M = json.load(open(os.path.join(d, "mobile", "mobile_manifest.json"))); self.assertFalse(any("source_objects" in n for n in M["nodes"]))


if __name__ == "__main__":
    unittest.main()
