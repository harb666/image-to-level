"""Stage 7: scene spec -> level, gameplay navigation, edit-preserving regeneration, refine, checks, package, references,
renders and the iPhone preview. Synthetic fixtures are clearly synthetic; the real-image runs live in levels/*_gen."""
import copy, json, os, shutil, subprocess, sys, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


def build(d):
    subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Spec(unittest.TestCase):
    def test_real_specs_valid(self):
        from scene_spec import validate
        for n in ("toxic_arena_gen", "town_square_gen"):
            E, W = validate(json.load(open(os.path.join(ROOT, "levels", n, "scene_spec.json")))); self.assertEqual(E, [], n)

    def test_errors_are_specific(self):
        from scene_spec import validate
        s = small_spec(); s["connections"].append({"id": "X", "from": "A", "to": "Nope"}); s["platforms"][0]["top"] = "high"
        s["structures"].append({"id": "Y", "kind": "spaceship", "position": [0, 0]})
        E, _ = validate(s); txt = "\n".join(E)
        self.assertIn("spec.platforms[0].top: expected number", txt)
        E, _ = validate(dict(small_spec(), connections=[{"id": "X", "from": "A", "to": "Nope"}])); self.assertTrue(any("unknown platform 'Nope'" in e for e in E))
        E, _ = validate(dict(small_spec(), structures=[{"id": "Y", "kind": "spaceship", "position": [0, 0]}])); self.assertTrue(any("spaceship" in e for e in E))
        s = small_spec(); del s["arena"]; self.assertTrue(any("missing required 'arena'" in e for e in validate(s)[0]))
        _, W = validate(dict(small_spec(), heigth=3)); self.assertTrue(any("heigth" in w for w in W))


class Generate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import spec_to_level
        cls.d = tmp_level(name="synthetic"); cls.spec_p = write_spec(cls.d, small_spec())
        cls.L, cls.summary = spec_to_level.run(cls.spec_p, cls.d, verbose=False); build(cls.d)

    def test_named_objects_and_roles(self):
        names = {o["name"] for o in self.L["objects"]}
        for n in ("HazardFluid", "A_Base", "A_Floor", "B_Floor", "Br_AB_Deck", "Mast_Body", "OuterWall_North_Body"): self.assertIn(n, names)
        used = {o.get("material") for o in self.L["objects"] if o.get("material")}
        self.assertEqual(set(self.L["materials"]), used, "only used role materials are defined")
        self.assertTrue(all(o.get("gen") and o.get("source") in ("visible", "inferred") for o in self.L["objects"]))

    def test_connection_kinds(self):
        by = {o["name"]: o for o in self.L["objects"]}
        self.assertIn("Br_AB_Deck", by)                         # same height -> flat bridge
        self.assertIn("Ln_AC_Deck", by)                         # +1 m over a gap, elevated -> sloped bridge
        self.assertLess(by["Ln_AC_Deck"]["rotation"][0], 0)

    def test_effects_and_environment(self):
        ids = {e["id"] for e in self.L["effects"]}
        self.assertTrue({"Hazard_Surface", "Hazard_Bubbles", "Sky_Drift"} <= ids)
        self.assertEqual(self.L["environment"]["sky"]["preset"], "overcast")
        self.assertTrue(os.path.exists(os.path.join(self.d, "mobile", "level_mobile.glb")))

    def test_navigation(self):
        from gameplay import analyse
        N = analyse(self.d, verbose=False); areas = {a["name"]: a for a in N["intended_areas"]}
        for n in ("A", "B", "C"): self.assertGreaterEqual(areas[n]["reachable_fraction"], 0.5, n)
        self.assertEqual(areas["D"]["reachable_fraction"], 0.0)
        self.assertTrue(any(i["kind"] == "unreachable_platform" and i["object"] == "D" for i in N["issues"]))
        self.assertTrue(N["spawns"][0]["standable"])

    def test_jump_height_comes_from_config(self):
        from gameplay import analyse, load_gameplay
        G = load_gameplay(self.d); G["player"]["jump_height"] = 9.0; G["player"]["jump_distance"] = 12.0
        N = analyse(self.d, G, write=False, verbose=False)
        self.assertGreater({a["name"]: a for a in N["intended_areas"]}["D"]["reachable_fraction"], 0.5, "super jump reaches D")

    def test_checks_report(self):
        import checks
        R = checks.run(self.d, fast=True, verbose=False)
        self.assertIn("performance", R); self.assertIn("mobile", R["performance"])
        self.assertTrue(any(i["kind"] == "unreachable_platform" for i in R["issues"]))
        self.assertFalse(R["passed"])
        self.assertTrue(os.path.exists(os.path.join(self.d, "checks", "report.md")))


class Regenerate(unittest.TestCase):
    def test_manual_edits_survive(self):
        import spec_to_level, edit_level as E
        d = tmp_level(name="regen"); sp = write_spec(d, small_spec()); spec_to_level.run(sp, d, verbose=False)
        E.edit(d, "resize", ["B", "1.5", "1", "1.5"])                         # edited generated group
        E.edit(d, "add", [json.dumps({"name": "My_Crate", "type": "box", "position": [0, 4, 2], "size": [1, 1, 1], "material": "deck"})])  # manual
        E.edit(d, "remove", ["Mast"])                                          # deleted generated object (+children)
        E.edit(d, "mat", ["deck", "color=[0.6,0.2,0.2]"])                       # edited material
        s2 = small_spec(); s2["platforms"].append({"id": "E", "center": [0, 10], "size": [6, 6], "top": 4})
        s2["connections"].append({"id": "Br_AE", "from": "A", "to": "E"}); write_spec(d, s2)
        L, rep = spec_to_level.run(sp, d, verbose=False); by = {o["name"]: o for o in L["objects"]}
        self.assertIn("My_Crate", by); self.assertNotIn("Mast_Body", by); self.assertIn("E_Floor", by); self.assertIn("Br_AE_Deck", by)
        self.assertEqual(by["B_Floor"]["size"][0], round((6 + 0.3) * 1.5, 3))
        self.assertEqual(L["materials"]["deck"]["color"], [0.6, 0.2, 0.2])
        self.assertTrue(rep["kept_manual"] and rep["kept_edited"] and rep["kept_deleted"])
        E.edit(d, "undo", [])  # regeneration itself is undoable
        self.assertNotIn("E_Floor", {o["name"] for o in json.load(open(os.path.join(d, "level.json")))["objects"]})

    def test_refuses_to_overwrite_hand_level(self):
        import spec_to_level
        d = tmp_level("toxic_arena"); sp = write_spec(d, small_spec())
        with self.assertRaises(SystemExit): spec_to_level.run(sp, d, verbose=False)


@unittest.skipUnless(FULL, "QUICK=1")
class RefineAndPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import spec_to_level, refine
        cls.d = tmp_level(name="refine"); sp = write_spec(cls.d, small_spec()); spec_to_level.run(sp, cls.d, verbose=False); build(cls.d)
        cls.log = refine.refine(cls.d, 2, render=False, verbose=False)

    def test_refine_connects_unreachable_and_is_bounded(self):
        self.assertLessEqual(len([p for p in self.log["passes"] if isinstance(p.get("n"), int)]), 2)
        fixes = [f for p in self.log["passes"] for f in p.get("fixes", [])]
        self.assertTrue(any("connected" in f and "-> D" in f for f in fixes), fixes)
        N = json.load(open(os.path.join(self.d, "checks", "navigation.json")))
        self.assertGreaterEqual({a["name"]: a for a in N["intended_areas"]}["D"]["reachable_fraction"], 0.5)

    def test_package_valid_and_tamper_detected(self):
        import package
        out = os.path.join(os.path.dirname(self.d), "pkg"); r = package.build(self.d, out, verbose=False)
        self.assertTrue(r["valid"], r["errors"])
        for f in ("level.json", "level.glb", "mobile/level_mobile.glb", "gameplay/spawns.json", "gameplay/hazards.json", "environment.tres", "IMPORT_GODOT.md", "level_manifest.json"):
            self.assertTrue(os.path.exists(os.path.join(out, "levels", "refine", f)), f)
        open(os.path.join(out, "levels", "refine", "level.json"), "a").write(" ")
        self.assertTrue(any("checksum" in e for e in package.check(out, verbose=False)))


class References(unittest.TestCase):
    def test_split_concept_sheet(self):
        from PIL import Image, ImageDraw
        import references
        d = tmp_level(name="refs"); im = Image.new("RGB", (900, 600), (12, 12, 12)); dr = ImageDraw.Draw(im); rng = np.random.default_rng(1)
        for b in ([0, 0, 590, 390], [600, 0, 900, 390], [0, 400, 290, 600], [300, 400, 590, 600], [600, 400, 900, 600]):
            arr = (rng.random((b[3] - b[1], b[2] - b[0], 3)) * 255).astype("uint8"); im.paste(Image.fromarray(arr), b[:2])
        p = os.path.join(d, "sheet.png"); im.save(p)
        self.assertEqual(len(references.split(p, os.path.join(d, "panels"))["panels"]), 5)
        im2 = Image.new("RGB", (400, 300), (90, 120, 60)); im2.save(os.path.join(d, "one.png"))
        self.assertEqual(len(references.split(os.path.join(d, "one.png"), os.path.join(d, "p2"))["panels"]), 1)

    def test_plan_regions_in_metres(self):
        from PIL import Image, ImageDraw
        import references
        d = tmp_level(name="plan"); im = Image.new("RGB", (400, 400), (40, 160, 40)); dr = ImageDraw.Draw(im)
        dr.rectangle([150, 150, 249, 249], fill=(200, 190, 160)); dr.rectangle([300, 20, 379, 99], fill=(200, 190, 160))
        p = os.path.join(d, "plan.png"); im.save(p); R = references.plan(p, d, [80, 80], k=2)
        tan = [r for r in R["regions"] if r["colour"][0] > 150]; c = sorted(r["center"] for r in tan)
        self.assertEqual(len(tan), 2)
        self.assertTrue(np.allclose(sorted(c)[0], [0, 0], atol=1.5) and np.allclose(sorted(c)[1], [28, -28], atol=1.5), c)
        self.assertTrue(any(abs(r["size"][0] - 20) < 1.5 for r in tan))


@unittest.skipUnless(FULL and shutil.which("node"), "needs node + playwright (QUICK=1 skips)")
class BrowserPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import spec_to_level
        cls.d = tmp_level(name="ui"); sp = write_spec(cls.d, small_spec()); spec_to_level.run(sp, cls.d, verbose=False); build(cls.d)

    def test_headless_renders(self):
        from render_views import render
        r = render(self.d); self.assertGreaterEqual(r["views"], 12); self.assertEqual(r["errors"], [])
        self.assertTrue(os.path.exists(os.path.join(self.d, "checks", "views", "contact_sheet.jpg")))

    def test_iphone_viewport_ui(self):
        import checks
        checks.run(self.d, fast=True, verbose=False); html = os.path.join(self.d, "p.html")
        subprocess.run([sys.executable, os.path.join(PIPE, "make_preview.py"), self.d, "UI test", html], check=True, stdout=subprocess.DEVNULL)
        r = subprocess.run(["node", os.path.join(ROOT, "tests", "ui_check.js"), html], capture_output=True, text=True, timeout=240)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); res = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(res["errors"], []); self.assertTrue(res["picked"]); self.assertGreater(res["issues_button"], 0); self.assertTrue(res["jump_visible"])


if __name__ == "__main__":
    unittest.main()
