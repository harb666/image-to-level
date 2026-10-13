"""Stage 29: wall textures merge - plates keep their own textures but get a worn ragged outline almost flush with the
wall (no straight texture edge), and world-space planar UVs (uv_space "world") so patterns run on across parts."""
import json, os, re, unittest
import numpy as np
from _util import tmp_level, small_spec, write_spec


def _gen():
    import spec_to_level
    s = small_spec(); s["art_style"] = "alien_cartoon"; s["arena"]["size"] = [80, 80]
    s["arena"]["walls"] = {"height": 22, "thickness": 3, "dressing": "varied", "dress_y": 5,
                           "openings": [{"side": "north", "at": a, "width": 8, "sill": 9, "height": 18} for a in (-15, 15)]}
    d = tmp_level(name="seam"); spec_to_level.run(write_spec(d, s), d, verbose=False); return d, json.load(open(os.path.join(d, "level.json")))


class Seamless(unittest.TestCase):
    def test_plates_keep_their_textures_with_ragged_edges(self):
        import shapes
        _, L = _gen(); plates = [o for o in L["objects"] if o["name"].endswith("_Plate")]
        self.assertTrue(plates)
        self.assertTrue(all(o["type"] == "panel" and o["cut"] == "ragged" and o["uv_space"] == "world" for o in plates))
        self.assertGreater(len({o["material"] for o in plates}), 1)  # the variety stays (several plate textures)
        m = shapes.cut_panel(8.0, 10.0, "ragged", seed=3)
        self.assertLess(m.area, 0.97 * 80); self.assertGreater(m.area, 0.6 * 80)  # eaten in from the edges, still a plate
        self.assertGreater(len(m.faces), 40); self.assertTrue((m.face_normals[:, 2] > 0).all())

    def test_world_uvs_line_up(self):
        import trimesh, subprocess, sys
        from _util import PIPE
        d, L = _gen()
        subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sc = trimesh.load(os.path.join(d, "level.glb"), force="scene"); tile = None; pts = {}
        for n in ("OuterWall_North_01_Body", "OuterWall_North_02_Body"):
            M, g = sc.graph[n]; m = sc.geometry[g]; uv = m.visual.uv; v = trimesh.transform_points(m.vertices, M)
            tile = L["materials"][next(o for o in L["objects"] if o["name"] == n)["material"]].get("tile_m", 4.0)
            f = np.abs(m.face_normals[:, 2]) > 0.9; vi = np.unique(m.faces[f])
            pts[n] = (v[vi], uv[vi])
        for n, (v, uv) in pts.items():
            self.assertAlmostEqual(np.polyfit(v[:, 0], uv[:, 0], 1)[1], 0.0, 3)  # u = x / tile from the world origin: segments line up

if __name__ == "__main__":
    unittest.main()
