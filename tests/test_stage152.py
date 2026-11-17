"""Stage 152: the specimen in the showcase vat - a re-rigged, animated Construct Error character (pipeline/specimen.py)."""
import json, math, os, struct, sys, unittest
import numpy as np
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import specimen as S

A = os.path.join(ROOT, "assets", "characters", "specimen", "cyber_girl")
LV = os.path.join(ROOT, "levels", "assembly_ascent")


class SpecimenAsset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.J, cls.BIN = S.read_glb(A + ".glb"); cls.meta = json.load(open(A + ".json"))
        cls.names = [n["name"] for n in cls.J["nodes"]]; cls.joints = [cls.names[j] for j in cls.J["skins"][0]["joints"]]

    def test_light_enough(self):
        self.assertLess(os.path.getsize(A + ".glb"), 2_000_000)  # source 8.9 MB
        self.assertLess(os.path.getsize(A + "_preview.glb"), 1_500_000)
        self.assertLess(sum(self.meta["triangles"].values()), 0.65 * self.meta["source_triangles"])
        Jp, _ = S.read_glb(A + "_preview.glb"); self.assertNotIn("images", Jp)  # the sandboxed preview applies the jpg itself

    def test_hair_is_its_own_mesh_on_its_own_bones(self):
        """The hair is a separate primitive driven only by Head + the two hair chains: never by an arm, leg or the spine."""
        prims = {p["extras"]["part"]: p for p in self.J["meshes"][0]["primitives"]}; self.assertEqual(set(prims), {"Body", "Hair", "Cables"})
        h = prims["Hair"]["attributes"]; Jn = S.accessor(self.J, self.BIN, h["JOINTS_0"]); W = S.accessor(self.J, self.BIN, h["WEIGHTS_0"])
        used = {self.joints[j] for j, w in zip(Jn.ravel(), W.ravel()) if w > 0}
        self.assertTrue(used <= {"mixamorig:Head"} | {f"Hair{s}_{k}" for s in "LR" for k in range(1, 6)}, used)
        self.assertTrue({"HairL_5", "HairR_5"} <= used)  # the tails really ride their chains to the tips

    def test_rig_additions(self):
        for n in ("FloatRoot", "WireAnchor", "HairL_1", "HairR_5"): self.assertIn(n, self.names)
        fr = self.names.index("FloatRoot"); hips = self.names.index("mixamorig:Hips"); self.assertIn(hips, self.J["nodes"][fr]["children"])
        self.assertNotIn(self.names.index("WireAnchor"), self.J["nodes"][fr].get("children", []))  # the cables' tops stay put while she floats
        c = next(p for p in self.J["meshes"][0]["primitives"] if p["extras"]["part"] == "Cables")
        Jn = S.accessor(self.J, self.BIN, c["attributes"]["JOINTS_0"]); W = S.accessor(self.J, self.BIN, c["attributes"]["WEIGHTS_0"])
        self.assertIn("WireAnchor", {self.joints[j] for j, w in zip(Jn.ravel(), W.ravel()) if w > 0.5})

    def test_clips_loop_seamlessly(self):
        an = {a["name"]: a for a in self.J["animations"]}; self.assertEqual(set(an), {"panic", "bang"})
        self.assertAlmostEqual(max(S.accessor(self.J, self.BIN, an["bang"]["samplers"][0]["input"])), S.BANG_DUR, places=2)  # Stage 156: the 4 s flurry + double slams
        for a in an.values():
            for ch in a["channels"]:
                v = S.accessor(self.J, self.BIN, a["samplers"][ch["sampler"]]["output"])
                if ch["target"]["path"] == "rotation": self.assertGreater(abs(float(np.dot(v[0], v[-1]))), 0.9999)
                else: self.assertLess(np.abs(v[0] - v[-1]).max(), 1e-5)


class SpecimenMotion(unittest.TestCase):
    """Every few frames of both clips, skinned in Python: inside the glass, joints inside anatomical ranges."""
    @classmethod
    def setUpClass(cls):
        cls.prep = S.prepare(os.path.join(ROOT, "assets", "characters", "source", "cyber_girl_source.glb")); cls.rep = S.clip_report(cls.prep, step=4)

    def test_inside_the_glass(self):
        apothem = 1.6 * math.cos(math.pi / 16)  # the tank glass: 16 flat sides, r 1.6
        for c, r in self.rep.items():
            for k in ("body", "hands", "hair", "cables"): self.assertLess(r[k], apothem - 0.004, (c, k))
            self.assertGreater(r["hair_min_y"], 0.3)  # hair floats, never trailing on the vat floor
        self.assertGreater(self.rep["panic"]["hands"], 1.53)  # the palms really press on the glass
        self.assertGreater(self.rep["bang"]["hands"], 1.5)  # and the fists reach it

    def test_anatomy(self):
        for c, r in self.rep.items():
            self.assertGreaterEqual(r["elbow"][0], 0); self.assertLessEqual(r["elbow"][1], 145, c)
            self.assertGreaterEqual(r["knee"][0], 0); self.assertLessEqual(r["knee"][1], 135, c)
            self.assertLessEqual(r["wrist"], 80, c); self.assertLessEqual(r["twist"], 92, c); self.assertLessEqual(r["yaw"], 75, c)


class SpecimenInLevel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = json.load(open(os.path.join(LV, "level.json"))); cls.by = {o["name"]: o for o in cls.L["objects"]}

    def test_placed_in_the_vat(self):
        ch = next(c for c in self.L["characters"] if c["id"] == "Showcase_Specimen"); meta = json.load(open(A + ".json"))
        g = self.by["Showcase_TankGlass"]; off = meta["vat"]["offset"]; b = self.by["Showcase_TankBase"]; fy = b["position"][1] + b["size"][1]  # the vat floor
        self.assertAlmostEqual(ch["position"][0], g["position"][0] + off[0], places=2); self.assertAlmostEqual(ch["position"][2], g["position"][2] + off[2], places=2)
        self.assertAlmostEqual(ch["position"][1], fy + off[1], places=2)
        self.assertLess(g["position"][1], fy - 0.05); self.assertGreater(g["position"][1] + g["size"][1], self.by["Showcase_TankCap"]["position"][1] + 0.05)  # Stage 156: ends sunk (no flicker)
        self.assertTrue(g.get("tube")); self.assertNotIn("Showcase_TankLiquid", self.by)
        self.assertNotIn("Showcase_TankMascot", self.by)  # the painted silhouette is gone
        self.assertEqual(ch["clips"], {"idle": "panic", "alert": "bang"}); self.assertGreater(ch["trigger"]["radius"], 5)

    def test_runtimes_and_package(self):
        E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}; self.assertEqual(E["Showcase_Specimen_Anim"]["category"], "character")
        C = json.load(open(os.path.join(LV, "mobile", "collision.json"))); self.assertEqual(C["characters"][0]["id"], "Showcase_Specimen")
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: v = f.read()
        self.assertIn("const charAnim=", v); self.assertIn("charAnim(dt,now/1000)", v)
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")) as f: gd = f.read()
        self.assertIn("func _update_characters", gd); self.assertIn('"character":', gd)
        pkg = os.path.join(ROOT, "dist", "assembly_ascent", "package", "levels", "assembly_ascent", "characters", "cyber_girl.glb")
        if os.path.exists(os.path.join(ROOT, "dist", "assembly_ascent", "package")): self.assertTrue(os.path.exists(pkg))
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")), 4000 * 1024)  # (she is her own file: the level budget is unchanged)


if __name__ == "__main__":
    unittest.main()
