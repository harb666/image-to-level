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
        for n in ("Pipe_South_Plate", "Pipe_South_Collar", "Pipe_South_Bolt_4", "W_Run_North_End1_Plate", "W_Broken_Plate", "W_Broken_Collar"): self.assertIn(n, by)


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
        fx = [e for e in L["effects"] if e["type"] == "point_light"]; self.assertEqual(len(fx), 1); self.assertEqual(len(fx[0]["positions"]), len(glows) + len([n for n in by if re.search(r"_Lamp_\d+_Bulb$", n)]))  # fans + catwalk lamps (Stage 57)
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
    def test_pods_launch_up_the_columns(self):  # Stage 49 replaced the Stage 43 barrel trains
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        cols = [o["name"] for o in L["objects"] if o["name"].startswith("Column_") and o["type"] == "group"]
        for c in cols:
            for k in ("_Pod_Cap", "_Pod_Shell", "_Pod_Fluid", "_Pod_Bar_3"): self.assertIn(c + k, by)
            self.assertEqual(by[c + "_Pod_Fluid"]["material"], "hazard")
            self.assertLess(by[c + "_Pod_Cap"]["position"][1] + 0.45, 3.9)  # hidden in the plinth at rest
            self.assertFalse([n for n in by if n.startswith(c + "_Barrel")])
            self.assertFalse(any(by[n].get("tube") and by[n].get("bubbles", True) for n in by if n.startswith(c + "_Glass")))
        E = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "effects_mobile.json")))
        fx = [e for e in E["effects"] if e["type"] == "tube_pods"][0]
        self.assertEqual(fx["category"], "launch"); self.assertEqual(len(fx["launches"]), len(cols))
        self.assertEqual(len({l["period"] for l in fx["launches"]}), len(cols))  # never in step
        self.assertTrue(all(l["targets"] and all(t.startswith(l["group"] + "__") for t in l["targets"]) for l in fx["launches"]))
        self.assertGreater(fx["quality"]["balanced"]["params"]["speed"], 20)
        hz = [e for e in E["effects"] if e["type"] == "liquid_surface" and e["id"] == "Hazard_Surface"][0]
        self.assertTrue(10 <= len(hz["ripples"]) <= 24 and any(q[2] == 1.0 for q in hz["ripples"]))

class Stage46(unittest.TestCase):
    def test_sloped_bridges_dressed(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        decks = [n[:-5] for n, o in by.items() if n.endswith("_Deck") and abs((o.get("rotation") or [0])[0]) > 1]
        self.assertTrue(decks)
        for d in decks:
            for k in ("_Clad_L", "_Clad_R", "_CladLight_L", "_Threshold_Lo", "_Threshold_Hi", "_Support_Head", "_Support_Footing"): self.assertIn(d + k, by)
            self.assertEqual(by[d + "_Threshold_Hi"]["material"], "stripe")


class Stage48(unittest.TestCase):
    def test_vat_insides_and_bubbles(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        for k in ("_Diffuser", "_DiffuserGrate", "_Nozzle_7", "_Hood", "_HoodGrate"): self.assertIn("Vat_01" + k, by)
        self.assertFalse([n for n in by if n.startswith(("Pipe_NE", "Pipe_SW"))])
        E = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "effects_mobile.json")))
        fx = [e for e in E["effects"] if e["type"] == "tube_bubbles"]
        self.assertEqual(len(fx), 1); self.assertEqual(len(fx[0]["tubes"]), 16)  # the 16 vats; none in the columns (Stage 49)
        self.assertFalse([e for e in E["effects"] if e["type"] == "tube_blobs"])


class Stage50(unittest.TestCase):
    def test_ducts_end_before_columns_and_vats(self):
        import re, sys, numpy as np
        sys.path.insert(0, os.path.join(ROOT, "pipeline"))
        from architecture import _aabb_all
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json")))
        class C: objects = L["objects"]
        B = _aabb_all(C)
        ducts = [n for n in B if re.search(r"Ceil_Duct_\d+[a-z]?$", n)]; self.assertTrue(ducts)
        solid = [n for n in B if re.match(r"(Column_|Vat_|Purifier_|Proc_Tower|Core_Vat)", n)]
        for d in ducts:
            lo, hi = B[d]
            for n in solid:
                a, b = B[n]; self.assertTrue((np.minimum(hi, b) - np.maximum(lo, a) <= 0.01).any(), (d, n))
            self.assertTrue([n for n in B if n.startswith(d + "_Hanger_")], d)


class Stage52(unittest.TestCase):
    def test_screens_differ_and_easter_egg(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json")))
        for role in ("screen", "bigscreen"):
            sc = [o for o in L["objects"] if o.get("material") == role]
            ids = [o.get("uv_shift") for o in sc]
            self.assertTrue(sc and all(ids) and len(set(ids)) == len(ids), role)  # every screen its own id
            self.assertGreaterEqual(len({o["uv_region"] for o in sc}), 3, role)  # several picture variants
        tvs = {o["uv_shift"]: o for o in L["objects"] if o.get("material") == "screen"}
        self.assertFalse([o for o in tvs.values() if o["uv_region"] == "d"])  # the egg cell is never a TV's normal picture
        E = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "effects_mobile.json")))
        p = [e for e in E["effects"] if e["type"] == "tv_static" and e["target_material"] == "screen"][0]["quality"]["balanced"]["params"]
        self.assertIn(int(p["egg_id"]), tvs); self.assertEqual(p["egg_rect"], [0.5, 0.5, 0.5, 0.5])
        self.assertTrue(os.path.exists(os.path.join(ROOT, "levels", "slime_arena", "references", "tv_easter_egg.jpg")))


class Stage57(unittest.TestCase):
    def test_west_catwalk_and_warm_capsules(self):  # Stage 56's industrial rock face was reverted: the rocks are gone
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        self.assertFalse([n for n in by if n.startswith("Rock_West")])
        for k in ("W_Cat_West_Deck", "W_Cat_West_In_Deck", "W_Cat_West_Lamp_5_Bulb", "West_Landing_N_Floor"): self.assertIn(k, by)
        self.assertTrue([n for n in by if n.startswith("W_Cat_West_Rail")])
        self.assertEqual(by["W_Cat_West_Lamp_1_Bulb"]["material"], "glow_yellow")
        caps = [o for n, o in by.items() if "Capsule_" in n and not any(t in n for t in ("_Band", "_Hanger"))]
        self.assertTrue(caps and all(o["material"] == "glow_yellow" for o in caps))
        E = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "effects.json")))
        fl = [e for e in E["effects"] if e["id"] == "Fan_Lights"][0]; self.assertGreaterEqual(len(fl.get("emitters") or fl.get("positions") or []), 8)


class Stage58(unittest.TestCase):
    def test_conduit_spine_drops_into_the_slime(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "pipeline"))
        from architecture import _aabb_all
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json")))
        class C: objects = L["objects"]
        B = _aabb_all(C)
        drop, walk = B["Conduit_SpineDrop"], B["Conduit_Walk_Floor"] if "Conduit_Walk_Floor" in B else None
        self.assertLess(drop[0][1], 1.0)  # its bottom is under the liquid surface (y 1): it vanishes into it
        self.assertIn("Conduit_SpineJoint", B)
        if walk: self.assertTrue(drop[0][2] > walk[1][2] or drop[1][2] < walk[0][2])  # outside the walkway's footprint


class Stage59(unittest.TestCase):
    def test_portal_and_laser_gate(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        for k in ("Gate_Works_Pillar_L", "Gate_Works_Pillar_R", "Gate_Works_Header", "Gate_Works_TrapLight", "Gate_Works_LampLight", "Gate_Works_Panel_R1"):
            self.assertIn(k, by)
        self.assertEqual(by["Gate_Works_Pillar_L"]["type"], "prism")
        beams = [n for n in by if n.startswith("Gate_Works_Laser_Beam_")]; self.assertEqual(len(beams), 7)
        self.assertTrue(all(by[n]["collision"] is False and by[n]["mobile"]["group"] == "Gate_Works_Laser" for n in beams))  # navigation sees the doorway open
        g = L["gates"][0]; self.assertEqual(g["opens_on"]["encounter"], "Hall_Waves"); self.assertTrue(g["closed_at_start"])
        self.assertEqual(L["encounters"][0]["opens"], "Gate_Works_Laser")
        self.assertFalse([n for n in by if n.startswith("Gallery_North_Strut_0") and n[-1] in "234"])  # struts the portal covers
        C = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "collision.json"))); self.assertEqual(C["gates"][0]["id"], "Gate_Works_Laser")
        gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_mobile.gd")).read(); self.assertIn("func open_gate", gd); self.assertIn("signal gate_opened", gd)


class Stage60(unittest.TestCase):
    def test_conveyor_rollers_face_the_pool(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "pipeline"))
        from architecture import _aabb_all
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json")))
        class C: objects = L["objects"]
        B = _aabb_all(C)
        for conv, out in (("Conv_West", -1), ("Conv_East", 1)):  # rollers stick out on the pool side, away from the walkway (x = 0)
            for k in (1, 2):
                lo, hi = B[f"{conv}_Roller_{k}"]; bed_lo, bed_hi = B[conv + "_Bed"]
                self.assertTrue(lo[0] < bed_lo[0] - 0.5 if out < 0 else hi[0] > bed_hi[0] + 0.5, (conv, k))


class Stage61(unittest.TestCase):
    def test_working_assembly_lines(self):
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        for c in ("Conv_East", "Conv_West"):
            for k in ("_In_Housing", "_In_Mouth", "_In_Hopper", "_Out_Housing", "_Out_Stack", "_Parcel_01", "_Item1_01", "_Item2_01_L"): self.assertIn(c + k, by)
            ps = [o for n, o in by.items() if n.startswith(c + "_Parcel_")]
            self.assertTrue(len({tuple(o["size"]) for o in ps}) == 1 and all(not any(o.get("rotation", [0, 0, 0])) for o in ps))  # identical: the loop is seamless
        for a, t in (("Arm_1", "add"), ("Arm_2", "add"), ("Arm_3", "inspect"), ("Arm_4", "inspect")):
            self.assertEqual(by[a + "_Link1"]["mobile"]["group"], a + "_Upper"); self.assertIn(a + ("_Held" if t == "add" else "_Scan"), by)
        E = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "effects_mobile.json")))
        lines = [e for e in E["effects"] if e["type"] == "assembly_line"]; self.assertEqual(len(lines), 2)
        for e in lines:
            l = e["line"]; self.assertEqual(len(l["stations"]), 2)
            for st in l["stations"]:
                self.assertTrue(3 < st["angle_deg"] < 15 and 0 <= st["t0"] < st["period"] and st["window"] <= 0.7 * st["period"] + 1e-6)
        M = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "mobile_manifest.json")))
        self.assertTrue(any(n["node"].startswith("Conv_East_Parcels__") for n in M["nodes"]))
        for f in ("assembly_reveal.gdshader", "apply_effects.gd"): self.assertTrue(os.path.exists(os.path.join(ROOT, "pipeline", "godot_fx", f)))
