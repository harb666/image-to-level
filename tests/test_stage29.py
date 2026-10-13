"""Stage 29: seamless varied walls - one body texture per wall run, raised plates in the wall's own texture, and
world-space planar UVs (uv_space "world") so the pattern runs on across segments, plates and openings."""
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
    def test_one_texture_per_run_and_plates_match(self):
        _, L = _gen(); by = {o["name"]: o for o in L["objects"]}
        runs = {}
        for o in L["objects"]:
            m = re.match(r"(OuterWall_\w+?)(_\d+)?_Body$", o["name"])
            if m and o["type"] == "box": runs.setdefault(m.group(1), set()).add(o["material"])
        self.assertTrue(runs); self.assertTrue(all(len(v) == 1 for v in runs.values()), runs)
        for o in L["objects"]:
            if o["name"].endswith("_Plate"):
                seg = re.match(r"(.+)_M\d\d", o["name"]).group(1)
                self.assertEqual(o["material"], by[seg + "_Body"]["material"]); self.assertEqual(o["uv_space"], "world")

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
        for n, (v, uv) in pts.items():  # u follows world x (or -x) at the same scale on both segments
            k = np.polyfit(v[:, 0], uv[:, 0], 1); self.assertAlmostEqual(abs(k[0]), 1 / tile, 3)
        (va, ua), (vb, ub) = pts.values()
        fa, fb = np.polyfit(va[:, 0], ua[:, 0], 1), np.polyfit(vb[:, 0], ub[:, 0], 1)
        self.assertAlmostEqual(fa[1], fb[1], 3)  # same offset: the pattern continues from one segment to the next


if __name__ == "__main__":
    unittest.main()
