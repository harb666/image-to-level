"""Stage 14: nothing floats. Scatter props are whole (every part touches another part or the ground), stand on the
RENDERED terrain (mesh_height = LOD0 triangles) and never on a ledge; terrain waterfalls pour off the visible rim."""
import json, os, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, write_spec


class Props(unittest.TestCase):
    def test_satellites_have_no_floating_parts(self):
        import scatter, trimesh
        from scipy.spatial import cKDTree
        for k in ("sat_dish", "sat_pod", "sat_spire"):
            for parts, meta in scatter.variants(k, "alien_cartoon", 6):
                comps = trimesh.util.concatenate(list(parts.values())).split(only_watertight=False)
                P = [np.vstack([trimesh.sample.sample_surface_even(c, 300)[0], c.vertices]) for c in comps]
                for i, c in enumerate(comps):
                    if c.bounds[0][1] < 0.05: continue  # stands on the ground
                    d = cKDTree(np.vstack([P[j] for j in range(len(P)) if j != i])).query(P[i])[0].min()
                    self.assertLess(d, 0.12, f"{k}: a part floats {d:.2f} m away at {c.bounds.mean(0).round(2)}")


class RenderedGround(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from terrain import Terrain
        L = json.load(open(os.path.join(ROOT, "levels", "skyforge_arena", "level.json")))
        cls.TR = Terrain(L["terrain"], os.path.join(ROOT, "levels", "skyforge_arena")); cls.L = L

    def test_mesh_height_is_the_grid_surface(self):
        G = self.TR.grid(); i, j = 40, 50
        self.assertAlmostEqual(float(self.TR.mesh_height(G["X"][i, j], G["Z"][i, j])), float(G["H"][i, j]), 5)
        c = self.TR.cell; x, z = G["X"][i, j] + c / 2, G["Z"][i, j] + c / 2  # cell centre lies on one of the two diagonals
        h = float(self.TR.mesh_height(x, z)); q = [G["H"][i, j], G["H"][i, j + 1], G["H"][i + 1, j + 1], G["H"][i + 1, j]]
        self.assertTrue(min(q) - 1e-6 <= h <= max(q) + 1e-6)

    def test_scatter_stands_on_visible_ground_away_from_ledges(self):
        import scatter
        for sc in self.L["terrain"].get("scatter", []):
            for kind, var, x, y, z, yaw, s in scatter.place(self.TR, self.L, sc, []):
                g = float(self.TR.mesh_height(x, z)); self.assertLess(abs(y + scatter.SINK[kind] * s - g), 0.01)
                ring = [float(self.TR.mesh_height(x + 1.6 * np.cos(a), z + 1.6 * np.sin(a))) for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)]
                self.assertGreater(min(ring), g - 0.8, f"{kind} at ({x}, {z}) stands on a ledge")

    def test_terrain_falls_start_on_the_visible_rim(self):
        for o in self.L["objects"]:
            if o["type"] != "stream" or not o.get("grid"): continue
            G = np.asarray(o["grid"]); a = np.radians(o["rotation"][1]); p = np.asarray(o["position"])
            for P in G[0]:  # first row lies on the rendered ground (0.3 m flow depth), not in the air
                wx = p[0] + P[0] * np.cos(a) + P[2] * np.sin(a); wz = p[2] - P[0] * np.sin(a) + P[2] * np.cos(a)
                self.assertLess(abs(p[1] + P[1] - 0.3 - float(self.TR.mesh_height(wx, wz))), 0.6, o["name"])


if __name__ == "__main__":
    unittest.main()
