"""Stage 9: universal terrain + environment generation. Synthetic worlds test the GENERAL rules (any biome / theme);
the three engineering environments (levels/test_valley, test_urban, test_hybrid) must stay valid and different."""
import copy, json, os, subprocess, sys, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, write_spec


def small_world(**over):
    s = {"spec_version": 1, "name": "world_t", "title": "Synthetic world", "theme": "medieval_town", "detail": "low", "seed": 5, "profile": "performance",
         "interpretation": {"summary": "synthetic", "visible": ["n/a"], "inferred": ["everything"]},
         "world": {"size": [128, 128], "seed": 5, "relief": "gentle", "biome": "temperate", "cell": 2.0, "chunk": 16,
                   "boundary": {"shape": "organic", "margin": 16, "height": 12},
                   "features": [{"id": "Hill", "type": "hill", "center": [-30, -30], "radius": 18, "height": 7},
                                {"id": "Brook", "type": "river", "points": [[-64, 20], [0, 14], [64, 22]], "width": 7, "depth": 1.2},
                                {"id": "Lane", "type": "road", "points": [[10, -60], [6, 0], [12, 60]], "width": 5}],
                   "scatter": [{"id": "Trees", "kinds": ["conifer", "rock_small"], "density": 1.0, "cluster": 0.4, "slope_max": 25}],
                   "spawn_regions": [{"id": "Player_Start", "team": "player", "center": [-20, -5], "radius": 8, "count": 3},
                                     {"id": "Enemy", "team": "enemy", "center": [30, -20], "radius": 8, "count": 3}]},
         "structures": [{"id": "Hall", "kind": "house", "position": [-35, 0], "size": [8, 6, 6], "style": "plaster"},
                        {"id": "Arch", "kind": "rock_arch", "position": [30, 40], "size": [10, 7, 3]}],
         "atmosphere": {"sky": "clear_day", "ambient": "none"}, "effects": "auto"}
    s.update(over); return s


def terrain_def(spec=None):
    import architecture as A, world as WM
    spec = spec or small_world(); W = spec["world"]; ext = WM.extent_of(W); b = WM.boundary_points(W, ext, W["seed"])
    return WM.terrain_def(spec, W, ext, b, spec["theme"])


class TerrainCore(unittest.TestCase):
    """Deterministic feature heightfield, seamless chunks at every LOD, edit locality, feature behaviour."""
    @classmethod
    def setUpClass(cls):
        from terrain import Terrain
        cls.T = terrain_def(); cls.TR = Terrain(cls.T)

    def test_deterministic(self):
        from terrain import Terrain
        a = Terrain(copy.deepcopy(self.T)).grid()["H"]; b = Terrain(copy.deepcopy(self.T)).grid()["H"]
        self.assertTrue(np.array_equal(a, b))

    def test_chunk_borders_match_at_every_lod(self):
        TR = self.TR; edges = {}
        for i, j in TR.chunk_ids():
            b = TR.chunk_bounds(i, j)
            for lod in (0, 1, 2):
                V = np.vstack([m.vertices for m in TR.chunk_mesh(i, j, lod, broad=lod > 0, far=lod == 2).values()])
                edges[(i, j, lod)] = (np.unique(np.round(V[np.isclose(V[:, 0], b[2])], 5), axis=0), np.unique(np.round(V[np.isclose(V[:, 0], b[0])], 5), axis=0))
        for i, j in TR.chunk_ids():
            if j + 1 < TR.ncx:
                for la in (0, 1, 2):
                    for lb in (0, 1, 2):
                        A, B = edges[(i, j, la)][0], edges[(i, j + 1, lb)][1]
                        self.assertEqual(A.shape, B.shape); self.assertTrue(np.allclose(A, B), (i, j, la, lb))

    def test_lod_meshes_are_manifold_patches(self):
        import trimesh
        for lod in (0, 1, 2):
            m = trimesh.util.concatenate([trimesh.Trimesh(p.vertices, p.faces) for p in self.TR.chunk_mesh(1, 1, lod).values()]); m.merge_vertices()
            u, c = np.unique(m.edges_sorted, axis=0, return_counts=True)
            self.assertEqual(int((c == 1).sum()), 4 * self.TR.C, lod)  # only the chunk border is open
            self.assertTrue((m.face_normals[:, 1] > 0).all())

    def test_middle_ring_welds_to_the_near_grid(self):
        import trimesh
        from terrain import middle_ring, middle_radius
        ring, info = middle_ring(self.TR); parts = [self.TR.chunk_mesh(i, j, 0) for i, j in self.TR.chunk_ids()]
        ms = [m for p in parts for m in p.values()] + list(ring.values())
        m = trimesh.util.concatenate([trimesh.Trimesh(x.vertices, x.faces) for x in ms]); m.merge_vertices(digits_vertex=3)
        u, c = np.unique(m.edges_sorted, axis=0, return_counts=True); open_e = u[c == 1]
        R, _ = middle_radius(self.TR); cen = np.array([(self.TR.x0 + self.TR.x1) / 2, (self.TR.z0 + self.TR.z1) / 2])
        rad = np.linalg.norm(m.vertices[open_e][:, :, [0, 2]] - cen, axis=2).min(1)
        self.assertTrue((rad > R * 0.97).all(), "open edges inside the world (crack / hole)")

    def test_edit_locality(self):
        from terrain import Terrain
        T2 = copy.deepcopy(self.T); next(f for f in T2["features"] if f["id"] == "Hill")["height"] = 11
        TR2 = Terrain(T2); changed = [c for c in self.TR.chunk_ids() if self.TR.chunk_hash(*c) != TR2.chunk_hash(*c)]
        self.assertTrue(0 < len(changed) < len(self.TR.chunk_ids()), changed)
        for c in self.TR.chunk_ids():
            if c not in changed:  # untouched chunks: bit-identical meshes
                a = self.TR.chunk_mesh(*c); b = TR2.chunk_mesh(*c)
                self.assertEqual(sorted(a), sorted(b)); self.assertTrue(all(np.array_equal(a[k].vertices, b[k].vertices) for k in a))

    def test_features_shape_the_ground(self):
        from terrain import Terrain
        base = copy.deepcopy(self.T); base["features"] = []; T0 = Terrain(base)
        self.assertGreater(self.TR.height_at(-30, -30) - T0.height_at(-30, -30), 4.0)  # hill
        p = self.TR._prof["Brook"]; self.assertTrue((np.diff(p["water"]) <= 1e-9).all())  # never flows uphill
        q = self.TR._prof["Lane"]; g = np.abs(np.diff(q["y"])) / 2.0; self.assertLessEqual(float(g.max()), 0.1 + 1e-6)  # grade-limited profile
        W = self.TR.water_y(np.array([0.0]), np.array([14.0]))[0]; self.assertTrue(np.isfinite(W)); self.assertGreater(W, self.TR.height_at(0, 14))

    def test_pad_and_lower_modes(self):
        from terrain import Terrain
        T = copy.deepcopy(self.T); T["features"] += [dict(id="P", type="pad", center=[-30, -30], size=[8, 8], y=1.0, margin=3),
                                                     dict(id="Lw", type="pad", mode="lower", center=[40, -40], size=[6, 6], y=50.0, margin=3)]
        TR = Terrain(T); self.assertAlmostEqual(TR.height_at(-30, -30), 1.0, 3)
        self.assertAlmostEqual(TR.height_at(40, -40), self.TR.height_at(40, -40), 5)  # "lower" never raises the ground


    def test_image_heightmap_and_mask(self):
        from terrain import Terrain
        from PIL import Image
        d = tmp_level(name="img"); a = np.zeros((32, 32), np.uint8); a[8:24, 8:24] = 255; Image.fromarray(a).save(os.path.join(d, "hm.png"))
        T = copy.deepcopy(self.T); T["features"] += [dict(id="HM", type="heightmap", image="hm.png", area=[30, 30, 62, 62], height=[0, 6], mode="add"),
                                                     dict(id="MK", type="mask", image="hm.png", area=[-62, 30, -30, 62], name="road")]
        TR = Terrain(T, d); self.assertAlmostEqual(TR.height_at(46, 46) - self.TR.height_at(46, 46), 6.0, 1)  # layout from an image
        _, M = TR._eval(np.array([-46.0, -33.0]), np.array([46.0, 33.0])); self.assertGreater(M["road"][0], 0.9); self.assertLess(M["road"][1], 0.1)


class ScatterAndModules(unittest.TestCase):
    def test_scatter_deterministic_and_avoids_masks(self):
        from terrain import Terrain
        import scatter
        T = terrain_def(); TR = Terrain(T); L = dict(terrain=T, objects=[], spawn=dict(position=[0, 0, 0]))
        a = scatter.place(TR, L, T["scatter"][0], []); b = scatter.place(TR, L, T["scatter"][0], [])
        self.assertEqual(a, b); self.assertGreater(len(a), 20)
        X = np.array([i[2] for i in a]); Z = np.array([i[4] for i in a]); _, M = TR._eval(X, Z)
        for k in ("road", "river"): self.assertFalse((M.get(k, np.zeros(len(X))) > 0.5).any(), k)

    def test_props_closed_low_poly(self):
        import scatter
        for k in scatter.PROPS:
            for parts, meta in scatter.variants(k, "cartoon", 2):
                for m in parts.values(): self.assertTrue(m.is_watertight, k); self.assertLess(len(m.faces), 400, k)

    def test_natural_shapes_closed(self):
        import shapes
        for t, sz, o in (("rock_arch", [12, 8, 4], {}), ("cave", [12, 8, 14], {}), ("overhang", [14, 6, 6], {}), ("crystals", [4, 5, 4], {}),
                         ("berm", [20, 3, 10], dict(heights=[[1, 2, 1], [1, 3, 1], [1, 2, 1]], xs=[-5, 0, 5], zs=[-4, 0, 4]))):
            m = shapes.SHAPES[t](*sz, o)
            if t != "crystals": self.assertTrue(m.is_watertight, t)
            self.assertGreater(m.volume, 0, t)

    def test_module_registry_is_pluggable(self):
        import architecture as A
        from modules import structure, INFO
        for k in ("bridge", "tunnel", "street", "futuristic_tower", "factory", "cave", "rock_arch", "ruins", "cliff_face"): self.assertIn(k, A.STRUCTURES)
        @structure("test_obelisk", pad=True, needs_size=True)
        def test_obelisk(ctx, s, x, y, z, yaw):
            ctx.add(s["id"], "spire", [x, y, z], s["size"], "stone", rot=[0, yaw, 0])
        self.assertTrue(INFO["test_obelisk"]["pad"]); self.assertIs(A.STRUCTURES["test_obelisk"], test_obelisk)
        import spec_to_level
        from gameplay import load_gameplay
        spec = small_world(); spec["structures"].append({"id": "Obelisk", "kind": "test_obelisk", "position": [20, -40], "size": [2, 9, 2]})
        L = spec_to_level.generate(spec, load_gameplay())
        self.assertTrue(any(o["name"] == "Obelisk" for o in L["objects"])); self.assertTrue(any(f["id"] == "Pad_Obelisk" for f in L["terrain"]["features"]))
        del A.STRUCTURES["test_obelisk"]; del INFO["test_obelisk"]

    def test_schema(self):
        from scene_spec import validate
        E, W = validate(small_world()); self.assertEqual(E, [])
        bad = small_world(); bad["world"]["features"].append({"id": "X", "type": "volcano", "center": [0, 0]}); E, _ = validate(bad)
        self.assertTrue(any("volcano" in e for e in E))
        bad = small_world(); bad["world"]["features"].append({"id": "Y", "type": "river"}); E, _ = validate(bad)
        self.assertTrue(any("needs 'points'" in e for e in E))
        bad = small_world(); del bad["world"]; E, _ = validate(bad); self.assertTrue(any("arena" in e and "world" in e for e in E))


@unittest.skipUnless(FULL, "QUICK=1")
class WorldEndToEnd(unittest.TestCase):
    """Small open world: generate + build + mobile LOD export + collision + world validation, then fault injection."""
    @classmethod
    def setUpClass(cls):
        import spec_to_level
        cls.d = tmp_level(name="world"); p = write_spec(cls.d, small_world()); spec_to_level.run(p, cls.d, verbose=False)
        subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), cls.d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def check(self):
        import geometry_check
        return geometry_check.run(self.d, verbose=False, write=False)

    def test_builds_validates_and_exports(self):
        R = self.check(); self.assertEqual(R["counts"]["ERROR"], 0, [f["message"] for f in R["findings"] if f["cls"] == "ERROR"])
        TJ = json.load(open(os.path.join(self.d, "terrain.json"))); self.assertEqual(len(TJ["chunks"]), 16); self.assertTrue(TJ["instances"])
        M = json.load(open(os.path.join(self.d, "mobile", "mobile_manifest.json")))
        lods = [n for n in M["nodes"] if n["kind"].startswith("terrain_lod")]; self.assertTrue({0, 1, 2} <= {int(n["kind"][-1]) for n in lods})
        for n in lods:  # complementary visibility ranges per chunk
            self.assertTrue(n["visibility_range_end"] == 0 or n["visibility_range_end"] > n["visibility_range_begin"])
        C = json.load(open(os.path.join(self.d, "mobile", "collision.json")))["colliders"]
        self.assertEqual(sum(c["shape"] == "heightmap" for c in C), 16); self.assertTrue(any(c["shape"] == "mesh" for c in C))  # arch: concave
        self.assertFalse(any(c["name"].startswith("TRM_") for c in C))  # middle zone never collides
        L = json.load(open(os.path.join(self.d, "level.json"))); self.assertEqual(L["generator"]["mode"], "open")
        self.assertTrue(any(o["name"].startswith("Bridge_Lane_Brook") for o in L["objects"]))  # road x river -> bridge
        self.assertTrue(any(o["name"] == "Hall_Foundation" for o in L["objects"]))
        self.assertGreaterEqual(len([r for r in L["spawn_regions"] if r["team"] == "enemy" and r["points"]]), 1)

    def test_fault_injection_and_repair(self):
        import geometry_repair
        lp = os.path.join(self.d, "level.json"); L0 = json.load(open(lp)); L = copy.deepcopy(L0)
        f = next(o for o in L["objects"] if o["name"] == "Hall_Foundation"); f["position"][1] += 3.0  # foundation floats
        L["terrain"]["features"] = [x for x in L["terrain"]["features"] if x["id"] != "Pad_Hall"]
        json.dump(L, open(lp, "w"), indent=1)
        subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), self.d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        R = self.check(); self.assertTrue(any(x["check"] == "foundations" and x["cls"] == "ERROR" for x in R["findings"]), [x["message"] for x in R["findings"]])
        geometry_repair.repair(self.d, max_passes=2, verbose=False)
        R = self.check(); self.assertFalse(any(x["check"] == "foundations" and x["cls"] == "ERROR" for x in R["findings"]))
        json.dump(L0, open(lp, "w"), indent=1)
        subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), self.d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_terrain_edit_command_is_local_and_undoable(self):
        import edit_level
        lp = os.path.join(self.d, "level.json"); L0 = json.load(open(lp))
        edit_level.edit(self.d, "terrain", ["set", "Hill", "height=12"])
        L1 = json.load(open(lp)); self.assertEqual(next(f for f in L1["terrain"]["features"] if f["id"] == "Hill")["height"], 12)
        from terrain import Terrain
        a, b = Terrain(L0["terrain"]), Terrain(L1["terrain"]); ch = [c for c in a.chunk_ids() if a.chunk_hash(*c) != b.chunk_hash(*c)]
        self.assertTrue(0 < len(ch) < 16, ch)
        with self.assertRaises(SystemExit): edit_level.edit(self.d, "terrain", ["set", "Hill", 'type="volcano"'])  # refused, nothing changes
        edit_level.edit(self.d, "undo", []); self.assertEqual(json.load(open(lp))["terrain"], L0["terrain"])

    def test_missing_bridge_is_an_error(self):
        lp = os.path.join(self.d, "level.json"); L0 = json.load(open(lp)); L = copy.deepcopy(L0)
        L["objects"] = [o for o in L["objects"] if not o["name"].startswith("Bridge_")]; L["relations"] = [r for r in L["relations"] if not r["a"].startswith("Bridge_")]
        json.dump(L, open(lp, "w"), indent=1)
        try:
            import terrain_check, geometry_check
            from gameplay import load_gameplay
            out = []; terrain_check.check_roads(self.d, L, __import__("terrain").Terrain(L["terrain"], self.d), load_gameplay(self.d, L), out)
            self.assertTrue(any("without a bridge" in f["message"] for f in out))
        finally: json.dump(L0, open(lp, "w"), indent=1)


class EngineeringEnvironments(unittest.TestCase):
    """levels/test_valley (A, open rocky valley), test_urban (B, futuristic city), test_hybrid (C, compound in terrain)."""
    LV = ("test_valley", "test_urban", "test_hybrid")

    def load(self, n):
        return json.load(open(os.path.join(ROOT, "levels", n, "level.json")))

    def test_genuinely_different(self):
        Ls = [self.load(n) for n in self.LV]
        self.assertEqual([L["generator"]["mode"] for L in Ls], ["open", "open", "hybrid"])
        self.assertEqual(len({L["terrain"]["biome"] for L in Ls}), 3)
        feats = [{f["type"] for f in L["terrain"]["features"]} for L in Ls]; kinds = [{o.get("gen") for o in L["objects"]} for L in Ls]
        self.assertTrue(all(len(a ^ b) >= 3 for a in feats for b in feats if a is not b))
        mats = [set(L["materials"]) for L in Ls]; self.assertTrue(all(len(a ^ b) >= 5 for a in mats for b in mats if a is not b))
        from PIL import Image
        ims = [np.asarray(Image.open(os.path.join(ROOT, "levels", n, "topdown.png")).convert("RGB").resize((96, 96)), float) for n in self.LV]
        for i in range(3):
            for j in range(i + 1, 3): self.assertGreater(np.abs(ims[i] - ims[j]).mean(), 12)

    def test_reports_pass(self):
        for n in self.LV:
            p = os.path.join(ROOT, "levels", n, "checks", "geometry.json")
            if not os.path.exists(p): self.skipTest("run generate.py first")
            R = json.load(open(p)); self.assertEqual(R["counts"]["ERROR"], 0, (n, [f["message"] for f in R["findings"] if f["cls"] == "ERROR"]))


if __name__ == "__main__":
    unittest.main()
