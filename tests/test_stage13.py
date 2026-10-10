"""Stage 13: pennant banners with an emblem (atlas material), organic terrain waterfalls that keep clear of the cliff,
slime leak decals on some structures (visual only, no extra material)."""
import json, os, subprocess, sys, types, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec

ATLAS = {"banner": [0, 0, 0.75, 1], "drip": [0.78, 0.52, 0.98, 0.98], "puddle": [0.78, 0.02, 0.98, 0.48]}


class Banner(unittest.TestCase):
    def test_pennant_keeps_the_emblem_aspect(self):
        import shapes
        for w, h, at in ((2.0, 10.0, None), (1.4, 8.0, 0.55), (2.6, 13.0, 0.6)):
            m = shapes.cut_panel(w, h, "pennant", 0, (1.5, (0.2, 0.8), at)); uv = m.metadata["uv"]; V = m.vertices
            self.assertTrue((m.face_normals[:, 2] > 0).all())
            self.assertTrue(np.any(np.isclose(V[:, 0], 0) & (V[:, 1] > 0.5)))  # swallowtail notch vertex
            band = V[np.isclose(uv[:, 1], 0.2) | np.isclose(uv[:, 1], 0.8), 1]; self.assertAlmostEqual(float(np.ptp(band)), w * 1.5, delta=0.01)
            if at: self.assertAlmostEqual(float(band.mean()), at * h, delta=0.01)

    def test_atlas_texture_has_emblem_and_slime_cells(self):
        import materials
        d = materials.maps({"type": "banner", "color": [0.78, 0.05, 0.1], "res": 128, "emissive": [1, 1, 1], "atlas": ATLAS})
        S = d["S"]; e = d["emit"]; a = d["alb"]
        self.assertGreater(float(e[int(0.35 * S):int(0.65 * S), int(0.3 * S):int(0.45 * S)].max()), 0.9)  # emblem glows
        drip = a[int(0.1 * S):int(0.4 * S), int(0.82 * S):int(0.95 * S)].reshape(-1, 3).mean(0); self.assertGreater(drip[1], drip[0] + 0.2)  # green

    def test_emblem_from_image(self):
        import materials
        from PIL import Image
        d = tmp_level(name="emb"); p = os.path.join(d, "e.png"); im = np.full((60, 40, 3), 245, np.uint8); im[10:50, 15:25] = [128, 0, 0]
        Image.fromarray(im).save(p); k = materials.emblem_mask(p, 20, 40)
        self.assertGreater(k.mean(), 0.15); self.assertLess(k[:, :3].max(), 0.1)  # the bar, fitted, background empty


class Falls(unittest.TestCase):
    """Synthetic plateau with a DIAGONAL cliff edge and a rock ledge bulging out below the lip."""
    @staticmethod
    def H(X, Z):
        X, Z = np.asarray(X, float), np.asarray(Z, float); e = Z - 0.3 * X  # edge at z = 0.3 x
        return np.where(e < 0, 30.0, np.maximum(0.0, 30.0 - 9.0 * e + 6.0 * np.exp(-((e - 2.5) ** 2) / 0.5)))

    def ctx(self):
        H = self.H; TR = types.SimpleNamespace(height=H, height_at=lambda x, z: float(H(x, z)), water_y=lambda X, Z: np.full(len(np.atleast_1d(X)), -np.inf))
        return types.SimpleNamespace(TR=TR)

    def test_sheet_hugs_each_lip_and_clears_the_rock(self):
        from modules.natural import _fall_grid
        G = _fall_grid(self.ctx(), {"id": "F"}, 0.0, 0.0, 0.0, 14.0, 29.85, 0.0)
        R, C = G.shape[:2]; self.assertGreaterEqual(C, 4)
        lip = [G[:, j][np.argmax(np.diff(G[:, j, 1]) < -1.0), 2] for j in range(C)]  # z where each column goes over
        self.assertGreater(np.corrcoef(G[0, :, 0], lip)[0, 1], 0.9)  # follows the diagonal edge
        for j in range(C):  # every segment of every column (and between columns) stays out of the rock (centre surface within half the 0.35 m thickness; the end dips into the floor)
            for i in range(R - 1):
                for f in np.linspace(0, 1, 9):
                    for P in (G[i, j] * (1 - f) + G[i + 1, j] * f,) + ((0.5 * (G[i, j] + G[i, j + 1]) * (1 - f) + 0.5 * (G[i + 1, j] + G[i + 1, j + 1]) * f,) if j < C - 1 else ()):
                        if P[1] > 0.9: self.assertLess(float(self.H(P[0], P[2])), P[1] + 0.17, f"col {j} row {i}: sheet inside the rock at {P.round(2)}")
        self.assertLess(float(np.ptp(G[-1, :, 2])), 12); self.assertGreater(float(np.ptp(G[0, :, 2] - 0.3 * G[0, :, 0])), 0.5)  # ragged, rounded top edge (not a straight cut)

    def test_grid_streams_have_their_own_flowing_uvs(self):
        import shapes
        from modules.natural import _fall_grid
        G = _fall_grid(self.ctx(), {"id": "F"}, 0.0, 0.0, 0.0, 10.0, 29.85, 0.0); G = G - G[0, G.shape[1] // 2]
        m = shapes.stream(10, 30, 0.35, {"grid": G.tolist()}); uv = m.metadata["uv"]  # default: one surface facing out / up
        self.assertGreater(float(np.mean(m.face_normals[:, 1] + m.face_normals[:, 2])), 0); self.assertEqual(len(m.faces), 2 * (G.shape[0] - 1) * (G.shape[1] - 1))
        k = shapes.stream(10, 30, 0.35, {"grid": G.tolist(), "closed": True}); k.merge_vertices(merge_tex=True, merge_norm=True)
        self.assertTrue(k.is_watertight); self.assertGreater(k.volume, 0)
        hi, lo = np.argmax(m.vertices[:, 1]), np.argmin(m.vertices[:, 1]); self.assertGreater(uv[hi, 1], uv[lo, 1])  # v runs along the flow
        P = shapes.stream_path(30, {"grid": G.tolist()}); self.assertLess(P[-1][0][1], P[0][0][1] - 20)


class Leaks(unittest.TestCase):
    def _level(self, **leaks):
        import spec_to_level
        s = small_spec(art_style="alien_cartoon", leaks=leaks); s["structures"] = [{"id": f"T{i}", "kind": "tower", "on": "A", "offset": [(-1) ** i * 2.5, 0],
                                                                                    "size": [2.4, 10, 2.4], "decor": ["banners", "glow_strips", "bands", "pipes"]} for i in range(2)]
        d = tmp_level(name="leak"); spec_to_level.run(write_spec(d, s), d, verbose=False); return d, json.load(open(os.path.join(d, "level.json")))

    def test_chance_and_visual_only(self):
        _, L0 = self._level(chance=0.0); _, L1 = self._level(chance=1.0); _, L2 = self._level(chance=1.0)
        dec = [o for o in L1["objects"] if "_Leak_" in o["name"] or "_Puddle_" in o["name"]]
        self.assertFalse([o for o in L0["objects"] if "_Leak_" in o["name"]]); self.assertTrue(dec)
        self.assertEqual(dec, [o for o in L2["objects"] if "_Leak_" in o["name"] or "_Puddle_" in o["name"]])  # reproducible
        for o in dec:
            self.assertEqual((o["type"], o["material"], o["collision"]), ("panel", "accent", False)); self.assertIn(o["uv_region"], ("drip", "puddle"))
        self.assertEqual(set(L0["materials"]), set(L1["materials"]))  # no new material -> no new draw call

    @unittest.skipUnless(FULL, "QUICK=1")
    def test_build_uses_atlas_and_keeps_gameplay(self):
        from gameplay import analyse
        out = []
        for ch in (0.0, 1.0):
            d, L = self._level(chance=ch)
            subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out.append((d, analyse(d, write=False, verbose=False), json.load(open(os.path.join(d, "mobile", "collision.json")))["colliders"]))
        self.assertAlmostEqual(out[0][1]["reachable_area_m2"], out[1][1]["reachable_area_m2"], delta=0.5)
        self.assertEqual(len(out[0][2]), len(out[1][2]))
        import trimesh
        sc = trimesh.load(os.path.join(out[1][0], "level.glb"), force="scene")
        uv = np.vstack([sc.geometry[sc.graph[k][1]].visual.uv for k in sc.graph.nodes_geometry if "_Leak_" in k])
        self.assertGreater(float(uv[:, 0].min()), 0.77)  # drips sample the slime cell of the atlas only


if __name__ == "__main__":
    unittest.main()
