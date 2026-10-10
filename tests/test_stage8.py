"""Stage 8: connection anchors, geometry validation, safe repair, pipe -> liquid attachment, stairs/ramps, terrain.
Synthetic scenes test the GENERAL rules (any theme); Toxic Arena is the regression level."""
import copy, json, os, shutil, subprocess, sys, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level


def build(d):
    subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def gen_yard():
    import spec_to_level
    d = tmp_level(name="yard"); spec = json.load(open(os.path.join(ROOT, "levels", "test_connections", "scene_spec.json")))
    spec["profile"] = "performance"; p = os.path.join(d, "scene_spec.json"); json.dump(spec, open(p, "w"))
    spec_to_level.run(p, d, verbose=False); build(d); return d


def findings(d, cls=None, check=None):
    import geometry_check
    R = geometry_check.run(d, verbose=False)
    return R, [f for f in R["findings"] if (cls is None or f["cls"] == cls) and (check is None or f["check"] == check)]


def mutate(d, fn):
    L = json.load(open(os.path.join(d, "level.json"))); fn({o["name"]: o for o in L["objects"]}, L)
    json.dump(L, open(os.path.join(d, "level.json"), "w"), indent=1); build(d)


@unittest.skipUnless(FULL, "QUICK=1")
class ConstructionRules(unittest.TestCase):
    """The generator builds every rule correctly on a synthetic yard (junctions, gap, ramp, stairs, 5 outlet types, terrain)."""
    @classmethod
    def setUpClass(cls): cls.d = gen_yard(); cls.R, _ = findings(cls.d)

    def test_clean_except_intentional_gap(self):
        self.assertEqual(self.R["counts"]["ERROR"], 0, [f["message"] for f in self.R["findings"]])
        self.assertEqual(self.R["counts"]["WARNING"], 0, [f["message"] for f in self.R["findings"]])
        intent = [f for f in self.R["findings"] if f["cls"] == "INTENTIONAL"]
        self.assertEqual(len(intent), 1); self.assertIn("jumpable", intent[0]["message"]); self.assertTrue(intent[0]["measured"]["jumpable"])

    def test_streams_leave_the_real_openings(self):
        from anchors import world_matrices, world_anchor
        L = json.load(open(os.path.join(self.d, "level.json"))); W, by = world_matrices(L)
        expect = {"Out_Round_Fall": "circle", "Out_Vertical_Fall": "circle", "Out_Broken_Fall": "circle", "Out_Drain_Fall": "rect", "Out_Spill_Fall": "rect"}
        for s, sec in expect.items():
            self.assertEqual(by[s]["type"], "stream"); self.assertEqual(by[s].get("section"), sec, s)
            r = next(r for r in L["relations"] if r["type"] == "emits_from" and r["a"] == s)
            O = world_anchor(W, by[r["b"]], r["b_anchor"]); S = world_anchor(W, by[s], "source"); K = world_anchor(W, by[s], "sink")
            self.assertLess(np.linalg.norm(O["pos"] - S["pos"]), 0.05, s)
            self.assertGreater(np.dot(O["dir"], S["dir"]), np.cos(np.radians(25)), s)
            self.assertLess(K["pos"][1], 0.5, f"{s} ends below the pool surface")
        self.assertLess(world_anchor(W, by["Out_Vertical_Fall"], "source")["dir"][1], -0.99)  # vertical drain falls straight down

    def test_everything_reachable_including_the_jump(self):
        from gameplay import analyse
        N = analyse(self.d, verbose=False, write=False)
        for a in N["intended_areas"]: self.assertGreaterEqual(a["reachable_fraction"], 0.5, a["name"])

    def test_fluid_metadata_and_hazards(self):
        FX = json.load(open(os.path.join(self.d, "effects.json"))); att = {a["stream"]: a for a in FX["fluid_attachments"]}
        self.assertEqual(len(att), 5); self.assertEqual(att["Out_Round_Fall"]["source_object"], "Out_Round"); self.assertEqual(att["Out_Round_Fall"]["receiving"], "Pool")
        C = json.load(open(os.path.join(self.d, "mobile", "collision.json")))
        hz = {h["name"] for h in C["hazards"]}; self.assertTrue({"Pool", "Out_Round_Fall", "Out_Drain_Fall"} <= hz)
        self.assertFalse(any(c["source"].endswith("_Fall") for c in C["colliders"]), "liquid is never a solid collider")

    def test_terrain_grounding(self):
        L = json.load(open(os.path.join(self.d, "level.json")))
        self.assertTrue(any(o["type"] == "terrain" for o in L["objects"]))
        self.assertFalse([f for f in self.R["findings"] if f["check"] == "support"])  # rocks / tree / tank grounded on the island


@unittest.skipUnless(FULL, "QUICK=1")
class DetectAndRepair(unittest.TestCase):
    """Deliberate construction failures are detected (ERROR/WARNING) and repaired deterministically, touching only the
    named object; intentional gaps are never filled; undo restores the broken state."""
    @classmethod
    def setUpClass(cls): cls.base = gen_yard()

    def fresh(self):
        d = os.path.join(os.path.dirname(self.base), f"case_{self._testMethodName}"); shutil.rmtree(d, ignore_errors=True); shutil.copytree(self.base, d); return d

    def repair_and_check(self, d, obj):
        import geometry_repair
        before = {o["name"]: o for o in json.load(open(os.path.join(d, "level.json")))["objects"]}
        rep = geometry_repair.repair(d, max_passes=3, verbose=False)
        after = {o["name"]: o for o in json.load(open(os.path.join(d, "level.json")))["objects"]}
        changed = {n for n in after if after[n] != before.get(n)}
        self.assertIn(obj, changed); self.assertTrue(changed <= {x["object"] for x in rep["repairs"] if x.get("object")}, changed)
        self.assertEqual(rep["remaining"]["ERROR"], 0, rep["needs_review"])
        self.assertEqual(after["P2_Bridged"]["position"], before["P2_Bridged"]["position"]); self.assertEqual(after["P3_JumpTarget"]["position"], before["P3_JumpTarget"]["position"])
        return rep

    def test_short_bridge(self):
        d = self.fresh()
        def f(by, L): o = by["Bridge_P1_P2_Deck"]; o["size"][2] -= 1.6
        mutate(d, f); _, E = findings(d, "ERROR", "connection"); self.assertTrue(any("short" in e["message"] or "overhang" in e["message"] for e in E), E)
        self.repair_and_check(d, "Bridge_P1_P2_Deck")

    def test_stairs_missing_landing(self):
        d = self.fresh()
        def f(by, L):  # flight pulled back 1.5 m at the top (bottom stays): the top step no longer reaches the landing
            import math
            o = by["Stairs_P3_P5"]; yw = math.radians(o["rotation"][1]); o["size"][2] -= 1.5
            o["position"][0] -= math.sin(yw) * 0.75; o["position"][2] -= math.cos(yw) * 0.75
        mutate(d, f); _, E = findings(d, "ERROR", "connection"); self.assertTrue(any("Stairs_P3_P5" in e["message"] for e in E), E)
        self.repair_and_check(d, "Stairs_P3_P5")

    def test_stream_offset_from_pipe(self):
        d = self.fresh()
        def f(by, L): by["Out_Round_Fall"]["position"][0] += 0.8; by["Out_Round_Fall"]["position"][1] -= 0.6
        mutate(d, f); _, E = findings(d, "ERROR", "outlet"); self.assertTrue(any("Out_Round_Fall" in e["message"] for e in E), E)
        self.repair_and_check(d, "Out_Round_Fall")

    def test_rectangular_block_under_round_pipe(self):
        d = self.fresh()
        def f(by, L):
            o = by["Out_Round_Fall"]; x, y, z = o["position"]
            for k in ("section", "speed", "pitch", "inset"): o.pop(k, None)
            o.update(type="box", position=[x, 0.5, z + 0.6], size=[1.3, y - 0.9, 1.0])
        mutate(d, f); _, E = findings(d, "ERROR", "outlet"); self.assertTrue(any("rectangular" in e["message"] for e in E), E)
        self.repair_and_check(d, "Out_Round_Fall")
        L = json.load(open(os.path.join(d, "level.json"))); self.assertEqual({o["name"]: o for o in L["objects"]}["Out_Round_Fall"]["type"], "stream")

    def test_hovering_prop_dropped_and_undo(self):
        import edit_level
        d = self.fresh()
        crate = "P1_Start_Cover_01"
        def f(by, L): by[crate]["position"][1] += 0.2  # a cover crate lifted off the deck
        mutate(d, f); broken = json.load(open(os.path.join(d, "level.json")))
        _, Wn = findings(d, "WARNING", "support"); self.assertTrue(any(crate in w["message"] and "hovers" in w["message"] for w in Wn), Wn)
        self.repair_and_check(d, crate)
        edit_level.edit(d, "undo", [])
        self.assertEqual(json.load(open(os.path.join(d, "level.json")))["objects"], broken["objects"])


def mini(objs, mats=None, **kw):
    d = tmp_level(name="mini"); L = dict(version=1, units="m", sky_color=[0.5, 0.6, 0.7], spawn=dict(position=[0, 0, 0], yaw_deg=0), hazards=[],
                                          bounds=dict(min=[-20, 0, -20], max=[20, 10, 20]), walkable=[], effects=[],
                                          materials=mats or {"a": {"type": "concrete", "color": [0.5, 0.5, 0.5], "tile_m": 2, "res": 32},
                                                             "b": {"type": "industrial_metal", "color": [0.3, 0.3, 0.3], "tile_m": 2, "res": 32},
                                                             "liq": {"type": "toxic", "color": [0.4, 1, 0.1], "tile_m": 4, "res": 32}},
                                          objects=[{"rotation": [0, 0, 0], **o} for o in objs], mobile={"export": False}, **kw)
    json.dump(L, open(os.path.join(d, "level.json"), "w")); build(d); return d


GROUND = dict(name="Ground", type="box", position=[0, -0.5, 0], size=[40, 0.5, 40], material="a")


class GenericRules(unittest.TestCase):
    """Theme-independent rules on tiny hand-made levels."""

    def test_zfight_detected_and_nudged(self):
        d = mini([GROUND, dict(name="Plate", type="box", position=[0, -0.2, 0], size=[4, 0.2, 4], material="b")])
        _, Wn = findings(d, "WARNING", "overlap"); self.assertTrue(Wn)
        import geometry_repair
        rep = geometry_repair.repair(d, verbose=False); _, Wn = findings(d, "WARNING", "overlap"); self.assertFalse(Wn, rep)

    def test_blocked_arch(self):
        d = mini([GROUND, dict(name="Gate", type="round_arch", position=[0, 0, 0], size=[6, 5, 2], material="a"), dict(name="Crate", type="box", position=[0, 0, 0], size=[1.5, 1.5, 1.5], material="b")])
        _, E = findings(d, "ERROR", "openings"); self.assertTrue(any("Crate" in e["message"] for e in E), E)

    def test_railing_across_a_ramp_landing(self):
        d = mini([GROUND, dict(name="Deck", type="box", position=[0, 0, -6], size=[8, 2, 4], material="a"),
                  dict(name="Ramp_1", type="ramp", position=[0, 0, -1], rotation=[0, 180, 0], size=[3, 2, 6.06], material="b"),
                  dict(name="Rail_1", type="railing", position=[0, 2, -4.6], size=[6, 1.05, 0.06], material="b")])
        _, E = findings(d, "ERROR", "connection"); self.assertTrue(any("Rail_1" in e["message"] and "landing" in e["message"] for e in E), E)

    def test_too_steep(self):
        d = mini([GROUND, dict(name="Deck", type="box", position=[0, 0, -4], size=[8, 3, 4], material="a"),
                  dict(name="Ramp_X", type="ramp", position=[0, 0, -1], size=[3, 3, 2.06], material="b"),
                  dict(name="Stairs_X", type="stairs", position=[5, 0, -1], size=[3, 3, 2.06], material="b")])
        _, E = findings(d, "ERROR", "stairs_ramps"); m = " ".join(e["message"] for e in E)
        self.assertIn("Ramp_X: ramp slope", m)

    def test_liquid_covering_floor(self):
        d = mini([GROUND, dict(name="Pool", type="box", position=[0, 0, 0], size=[10, 1.0, 10], material="liq"),
                  dict(name="Sunken", type="box", position=[2, 0, 2], size=[3, 0.6, 3], material="a")],
                 )
        L = json.load(open(os.path.join(d, "level.json"))); L["hazards"] = ["Pool"]; L["walkable"] = [dict(name="Sunken", min=[0.5, 0.5], max=[3.5, 3.5], y=0.6)]
        json.dump(L, open(os.path.join(d, "level.json"), "w")); build(d)
        _, E = findings(d, "ERROR", "flow"); self.assertTrue(any("covers walkable Sunken" in e["message"] for e in E), E)

    def test_terrain_crack(self):
        h1 = [[0, 0, 0], [0, 1, 0], [0, 0, 0]]; h2 = [[0.6, 0.6, 0.6], [0.6, 1, 0.6], [0.6, 0.6, 0.6]]
        d = mini([GROUND, dict(name="T1", type="terrain", position=[-4, 0, 0], heights=h1, cell=2, material="a", skirt=1),
                  dict(name="T2", type="terrain", position=[0, 0, 0], heights=h2, cell=2, material="a", skirt=1)])
        _, Wn = findings(d, "WARNING", "terrain"); self.assertTrue(Wn)

    def test_relation_schema(self):
        d = mini([GROUND], relations=[dict(type="supported_by", a="Ground", b="Nope"), dict(type="flies_to", a="Ground", b="Ground")])
        _, E = findings(d, "ERROR", "relations"); self.assertEqual(len(E), 2)


@unittest.skipUnless(FULL, "QUICK=1")
class ToxicArenaRegression(unittest.TestCase):
    def test_arena_clean_and_hazards_kept(self):
        d = os.path.join(ROOT, "levels", "toxic_arena")
        R, _ = findings(d) if False else (json.load(open(os.path.join(d, "checks", "geometry.json"))), None)
        self.assertEqual(R["counts"]["ERROR"], 0); self.assertEqual(R["counts"]["WARNING"], 0)
        L = json.load(open(os.path.join(d, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        falls = [n for n in by if n.endswith("_Fall")]; self.assertEqual(len(falls), 8)
        self.assertTrue(all(by[n]["type"] == "stream" and by[n]["material"] == "toxic" for n in falls))
        C = json.load(open(os.path.join(d, "mobile", "collision.json"))); hz = {h["name"] for h in C["hazards"]}
        self.assertTrue({"HazardFluid", *falls} <= hz)
        self.assertEqual(L["hazards"], ["HazardFluid"])


if __name__ == "__main__":
    unittest.main()
