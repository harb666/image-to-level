"""Stage 34: column rings are hollow (the glass pipe's bore runs on through drums, neck and capital), robot arms pick
a pose clear of the objects around them, pedestals stand in the liquid, corrosion is on by default and reaches
everything in or standing on the liquid."""
import json, os, unittest
from _util import ROOT, tmp_level, small_spec, write_spec


class Stage34(unittest.TestCase):
    def test_slime_arena(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        drums = [o for o in L["objects"] if "_Drum_" in o["name"] and o["name"].startswith("Column")]
        self.assertTrue(drums and all(o.get("hole") for o in drums))
        caps = [o for o in L["objects"] if o["name"].startswith("Column") and o["name"].endswith(("_Neck", "_Capital", "_Plinth"))]
        self.assertTrue(caps and all(o.get("hole") for o in caps))
        ped = by["Arm_1_Pedestal"]; self.assertLess(7.0 + ped["position"][1], 1.0)  # bottom below the liquid surface (y 1)
        self.assertIn("Corrosion_Band", by)
        import re
        for p in [o for o in L["objects"] if re.search(r"Pod_\d+$", o["name"])]:  # pods: no cage bar through the glass, glass lids hidden in cap / base
            bars = [by[n] for n in by if n.startswith(p["name"] + "_Bar_")]; r = p["size"][0] / 2
            self.assertTrue(bars and all(abs(b["size"][0] - 0.14) < 1e-6 and abs(b["size"][2] - 0.14) < 1e-6 for b in bars))
            self.assertTrue(all(((b["position"][0] - p["position"][0]) ** 2 + (b["position"][2] - p["position"][2]) ** 2) ** 0.5 > r for b in bars))
            cap, base = by[p["name"] + "_Cap"], by[p["name"] + "_Base"]
            self.assertLess(p["position"][1], base["position"][1] + base["size"][1]); self.assertGreater(p["position"][1] + p["size"][1], cap["position"][1])

    def test_corrosion_on_by_default(self):
        import spec_to_level
        s = small_spec(); s["art_style"] = "alien_cartoon"; s.pop("corrosion", None)
        d = tmp_level(name="c34"); spec_to_level.run(write_spec(d, s), d, verbose=False)
        L = json.load(open(os.path.join(d, "level.json"))); self.assertTrue([o for o in L["objects"] if o["type"] == "band"])

    def test_arm_pose_clears_a_box(self):
        from modules.factory import _clear_pose, _arm_points
        from architecture import local
        class C: pass
        ctx = C(); ctx.notes = []; ctx.hazards = []
        ctx.objects = [{"name": "Blk", "type": "box", "position": [0, 0, 2.5], "size": [3, 2, 3], "rotation": [0, 0, 0]}]
        sh, el = _clear_pose(ctx, "Arm", (0, 0, 0), 0, 1.0, 45, 100)
        self.assertNotEqual((sh, el), (45, 100))
        for lx, ly, lz, r in _arm_points(sh, el, 1.0):  # every sample point clear of the box by its radius + 0.25
            x, z = local(lx, lz, 0)
            self.assertFalse(-1.5 - r - 0.25 < x < 1.5 + r + 0.25 and ly < 2 + r + 0.25 and 1 - r - 0.25 < z < 4 + r + 0.25, (lx, ly, lz))

if __name__ == "__main__":
    unittest.main()


class Stage35(unittest.TestCase):
    def test_shaft_like_skyforge_and_real_vents(self):
        import re
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        self.assertEqual(by["Elevator_Shaft_Collar"]["material"], "structure_b")  # Stage 42: collar replaces lip + insignia plates
        for n in ("Elevator_Shaft_OuterRing", "Elevator_Shaft_Clamp_4", "Elevator_Shaft_Strut_4", "Elevator_Shaft_Tri_8", "Elevator_Shaft_OuterLight_1"): self.assertIn(n, by)
        self.assertFalse([n for n in by if n.startswith("Elevator_Shaft_Emblem") or n == "Elevator_Shaft_Lip"])
        strips = [o for o in L["objects"] if o["name"].startswith("Elevator_Shaft_Strip_")]
        self.assertTrue(strips and all(o["size"][1] < 2.5 for o in strips))
        vents = [n for n in by if re.search(r"_M\d\dVent$", n)]
        self.assertTrue(vents and all(n + "_Duct" in by and n + "_FrameLow" in by and n + "_Slat_3" in by for n in vents))


class Stage36(unittest.TestCase):
    def test_no_overlapping_crates_and_wall_fittings(self):
        import sys, numpy as np
        from anchors import world_matrices
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); W, by = world_matrices(L)
        cr = [o for o in L["objects"] if o["type"] == "box" and o.get("faces")]
        def bb(o):
            w, h, d = o["size"]; C = np.array([[sx * w / 2, y, sz * d / 2, 1] for sx in (-1, 1) for y in (0, h) for sz in (-1, 1)]) @ W[o["name"]].T
            return C[:, :3].min(0), C[:, :3].max(0)
        B = [bb(o) for o in cr]
        for i in range(len(B)):
            for j in range(i + 1, len(B)):
                self.assertFalse((np.minimum(B[i][1], B[j][1]) - np.maximum(B[i][0], B[j][0]) > 0.02).all(), (cr[i]["name"], cr[j]["name"]))
        for n in ("Pipe_North_Plate", "Pipe_North_Collar", "Pipe_North_Bolt_4", "Pipe_NE_Boot", "W_Run_North_End1_Plate"): self.assertIn(n, by)


class Stage37(unittest.TestCase):
    def test_fans_vents_clear_piers_and_no_red_caps(self):
        import re, numpy as np
        from anchors import world_matrices
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); W, by = world_matrices(L)
        self.assertFalse([n for n in by if re.search(r"(Monitor_Corner_|_Op\d_Cap_)", n)])
        heads = [n for n in by if re.search(r"Support_\d\d_Head$", n)]; self.assertTrue(heads)
        for h in heads: self.assertIn(h[:-5] + "_Footing", by); self.assertIn(h[:-5] + "_Rib_00", by)
        def bb(o):
            w, h_, d = o["size"]; C = np.array([[sx * w / 2, y, sz * d / 2, 1] for sx in (-1, 1) for y in (0, h_) for sz in (-1, 1)]) @ W[o["name"]].T
            return C[:, :3].min(0), C[:, :3].max(0)
        B = {o["name"]: bb(o) for o in L["objects"] if o.get("size") and o["type"] not in ("group", "band")}
        thin = [n for n in B if any(t in n for t in ("Hanger", "Cable", "Clamp", "Bracket", "Strut", "Rod"))]
        for u in [n for n in B if re.search(r"(Ceil_Fan_\d+|_M\d\dFan|_M\d\dVent)$", n)]:
            parts = [p for p in B if p.startswith(u)]; lo = np.min([B[p][0] for p in parts], 0); hi = np.max([B[p][1] for p in parts], 0)
            for n in thin:
                if not n.startswith(u): self.assertTrue((np.minimum(hi, B[n][1]) - np.maximum(lo, B[n][0]) <= 0.07).any(), (u, n))


class Stage38(unittest.TestCase):
    def test_crane_rails_keep_off_screens(self):
        import re, numpy as np
        from anchors import world_matrices
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); W, by = world_matrices(L)
        def bb(n):
            o = by[n]; w, h, d = o["size"]; C = np.array([[sx * w / 2, y, sz * d / 2, 1] for sx in (-1, 1) for y in (0, h) for sz in (-1, 1)]) @ W[n].T
            return C[:, :3].min(0), C[:, :3].max(0)
        rails = [n for n in by if re.match(r"CraneRail_\d+_Beam$", n)]
        units = [n for n in by if re.search(r"(_Op\d_Screen|_M\d\d(Monitor_Body|Fan|Vent))$", n)]
        for r in rails:
            a = bb(r)
            for u in units:
                b = bb(u); b = (b[0] - 2.0, b[1] + 2.0)  # 2 m clear
                self.assertFalse((np.minimum(a[1], b[1]) - np.maximum(a[0], b[0]) > 0).all(), (r, u))


class Stage39(unittest.TestCase):
    def test_yellow_fan_glow_and_light(self):
        import re
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        glows = [n for n in by if re.match(r".*Ceil_Fan_\d+_Glow$", n)]
        self.assertTrue(glows and all(by[n]["material"] == "glow_yellow" for n in glows))
        self.assertGreater(L["materials"]["glow_yellow"]["color"][1], 0.7)
        fx = [e for e in L["effects"] if e["type"] == "point_light"]; self.assertEqual(len(fx), 1); self.assertEqual(len(fx[0]["positions"]), len(glows))
        gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read(); self.assertIn("OmniLight3D", gd)


class Stage40(unittest.TestCase):
    def test_shaft_band_and_bottomless(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        b = by["Elevator_Shaft_Band"]; self.assertEqual(b["material"], "frame"); self.assertTrue(b.get("hole"))
        v = by["Elevator_Shaft_Void"]; self.assertEqual((v["cut"], v["uv_region"]), ("sleeve", "void")); self.assertNotIn("Elevator_Shaft_Winch", by)
        car_r = next(e for e in L["entrances"] if e["id"] == "Elevator")["radius"]; self.assertGreater(v["size"][0] / 2, car_r)  # the car passes inside it


class Stage41(unittest.TestCase):
    def test_dim_wall_fans_and_no_overhanging_machinery(self):
        import re
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        wf = [n for n in by if re.search(r"_M\d\dFan_Glow$", n)]
        self.assertTrue(wf and all(by[n]["material"] == "glow_dim" for n in wf))
        self.assertLess(max(L["materials"]["glow_dim"]["emissive"]), 0.4)
        self.assertNotIn("Valve_A_Vent", by); self.assertIn("Valve_A_Unit", by)


class Stage43(unittest.TestCase):
    def test_barrels_shoot_up_the_columns(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        cols = [o["name"] for o in L["objects"] if o["name"].startswith("Column_") and o["type"] == "group"]
        for c in cols:
            ys = sorted(by[n]["position"][1] for n in by if n.startswith(c + "_Barrel_") and "_Hoop_" not in n)
            self.assertTrue(len(ys) >= 2 and ys[0] + by[c + "_Barrel_1"]["size"][1] < 3.9, c)  # first one hidden in the plinth
            self.assertTrue(all(abs(b - a - 7.0) < 1e-3 for a, b in zip(ys, ys[1:])), c)  # exact spacing: the loop is seamless
        E = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "effects_mobile.json")))
        fx = [e for e in E["effects"] if e["type"] == "tube_travel"]
        self.assertEqual(fx[0]["category"], "translate_loop"); self.assertTrue(all(t.startswith("Tube_Barrels__") for t in fx[0]["targets"]))


class Stage46(unittest.TestCase):
    def test_sloped_bridges_dressed(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        decks = [n[:-5] for n, o in by.items() if n.endswith("_Deck") and abs((o.get("rotation") or [0])[0]) > 1]
        self.assertTrue(decks)
        for d in decks:
            for k in ("_Clad_L", "_Clad_R", "_CladLight_L", "_Threshold_Lo", "_Threshold_Hi", "_Support_Head", "_Support_Footing"): self.assertIn(d + k, by)
            self.assertEqual(by[d + "_Threshold_Hi"]["material"], "stripe")
