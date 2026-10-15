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
            self.assertGreater(l["spacing"], 6.0)  # scarce parcels (Stage 62)
            for st in l["stations"]:
                self.assertTrue(3 < st["angle_deg"] < 15 and 0 <= st["t0"] < st["period"] and st["window"] <= 0.7 * st["period"] + 1e-6)
                rv = st["reveal"]; self.assertAlmostEqual(((rv["s_arm"] - rv["s0"]) % rv["spacing"]) / l["speed"], st["t0"], places=3)  # the part shows as the claw lets go
        M = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "mobile_manifest.json")))
        self.assertTrue(any(n["node"].startswith("Conv_East_Parcels__") for n in M["nodes"]))
        self.assertEqual(by["Conv_East_Item1_02"]["uv_shift"], 20)  # parcel number in the part's UVs
        for f in ("assembly_reveal.gdshader", "apply_effects.gd"): self.assertTrue(os.path.exists(os.path.join(ROOT, "pipeline", "godot_fx", f)))


class Stage63(unittest.TestCase):
    def test_bins_scanners_wider_walkway_and_rust(self):
        import numpy as np
        L = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "level.json"))); by = {o["name"]: o for o in L["objects"]}
        self.assertEqual(abs(by["Conv_East"]["position"][0]), 4.7); self.assertEqual(abs(by["Conv_West"]["position"][0]), 4.7)  # 7.4 m between the belts
        for a in ("Arm_1", "Arm_2"):
            for k in ("_Bin_Body", "_Bin_Rim", "_Bin_Void", "_Bin_Can_5", "_Bin_Post"): self.assertIn(a + k, by)
        for a in ("Arm_3", "Arm_4"):
            for k in ("_Lens", "_Scan", "_Ring_4"): self.assertIn(a + k, by)
        E = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "mobile", "effects_mobile.json")))
        st = {s["arm"]: s for e in E["effects"] if e["type"] == "assembly_line" for s in e["line"]["stations"]}
        for a in ("Arm_1", "Arm_2"):
            s = st[a]; self.assertTrue(s["bin_angle_deg"] > 0 and abs(s["bin_yaw_deg"]) == 90)
            self.assertLess(s["window"] + 2 * s["turn"] + s["bin_window"], s["period"])  # the whole pick fits between parcels
        for a in ("Arm_3", "Arm_4"): self.assertEqual(st[a]["ring"], [a + "_Ring"])
        band = by["Corrosion_Band"]; pts = np.array([q for sg in band["segments"] for q in sg["pts"]])
        for a in ("Arm_1", "Arm_2", "Arm_3", "Arm_4"):  # rust round every arm pedestal in the slime (Stage 63: no frozen band)
            P = by[a]["position"]; self.assertLess(float(np.min(np.hypot(pts[:, 0] - P[0], pts[:, 1] - P[2]))), 1.0, a)
        G = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "gen_state.json")))["objects"]
        import sys; sys.path.insert(0, os.path.join(ROOT, "pipeline")); from spec_to_level import H
        self.assertFalse([o["name"] for o in L["objects"] if o["name"] in G and G[o["name"]] != H(o) and o["name"] == "Corrosion_Band"])


class Stage64(unittest.TestCase):
    def test_slim_weld_keeps_shared_index_lists_apart(self):
        """trimesh stores identical index lists once: two mirrored ink shells shared one. Welding the first rewrote the
        shared list and scrambled the second (black slabs on the west crane arms). Each primitive keeps its own triangles."""
        import tempfile, numpy as np, trimesh, sys
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); import glb_tools
        ink = trimesh.visual.material.PBRMaterial(name="ink", baseColorFactor=[10, 0, 10, 255])
        sc = trimesh.Scene()
        for k, sx in enumerate((1, -1)):  # the same index list twice, the second mirrored in x (other vertex order after a weld)
            m = trimesh.creation.box((0.6, 2.8, 0.5)); m.unmerge_vertices(); m.vertices[:, 0] = m.vertices[:, 0] * sx + 3 * k
            m.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(m.vertices), 2)), material=ink)
            sc.add_geometry(m, node_name=f"S{k}__ink", geom_name=f"S{k}__ink")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.glb"); sc.export(p)
            before = trimesh.load(p, force="scene", process=False)
            canon = lambda m: sorted(tuple(np.roll(t, -int(np.lexsort(t.T[::-1])[0]), 0).round(4).ravel()) for t in m.triangles)
            ref = {n: canon(before.geometry[before.graph[n][1]]) for n in ("S0__ink", "S1__ink")}
            glb_tools.slim(p)
            after = trimesh.load(p, force="scene", process=False)
            for n in ref:
                m = after.geometry[after.graph[n][1]]
                self.assertEqual(canon(m), ref[n], n); self.assertEqual(len(m.vertices), 8, n)  # welded, triangles unchanged


class Stage65(unittest.TestCase):
    def test_arms_skinned_and_dip_pose_lowers_claw_straight_down(self):
        """Every joint of the working arms moves: each arm is skinned to an 8-bone skeleton (same draw calls), and the dip
        pose the effect drives (IK through the exported skeleton, wrist = -(shoulder + elbow)) puts the canister on the moving parcel."""
        import numpy as np, trimesh, sys
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); import glb_tools
        lv = os.path.join(ROOT, "levels", "slime_arena"); L = json.load(open(os.path.join(lv, "level.json")))
        SK = L["skeletons"]; self.assertEqual(sorted(SK), ["Arm_1", "Arm_2", "Arm_3", "Arm_4"])
        for o in L["objects"]:
            if (o.get("mobile") or {}).get("group") in {gr for v in SK.values() for gr in v["groups"]}: self.assertIn("joint", o["mobile"], o["name"])
        g, b = glb_tools._read(os.path.join(lv, "mobile", "level_mobile.glb"))
        self.assertEqual(len(g["skins"]), 4); self.assertTrue(all(len(s["joints"]) == 8 for s in g["skins"]))
        for n in g["nodes"]:
            if "skin" in n:
                a = g["meshes"][n["mesh"]]["primitives"][0]["attributes"]; self.assertEqual(g["accessors"][a["JOINTS_0"]]["count"], g["accessors"][a["POSITION"]]["count"])
        E = json.load(open(os.path.join(lv, "mobile", "effects_mobile.json")))
        st = {s["arm"]: s for e in E["effects"] if e["type"] == "assembly_line" for s in e["line"]["stations"]}
        def rot(ax, a):
            ax = np.asarray(ax, float); ax /= np.linalg.norm(ax); K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
            return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
        s = trimesh.load(os.path.join(lv, "mobile", "level_mobile.glb"), force="scene", process=False)
        for arm in ("Arm_1", "Arm_2"):
            import arm_motion; r = st[arm]["rig"]; v = next(e["line"]["speed"] for e in E["effects"] if e["type"] == "assembly_line" and st[arm] in e["line"]["stations"])
            ang, _ = arm_motion.pose(r, r["program"], v, st[arm]["period"], st[arm]["t0"] - 0.3, st[arm]["t0"])  # setting the canister in (Stage 66)
            Wm = {}
            for j in SK[arm]["joints"]:  # forward kinematics: joint world = parent world * offset * own rotation
                role = j["name"].rsplit("_J", 1)[1].lower(); R = rot(r["axes"][role], ang.get(role, 0.0))
                if j["parent"]: PR, Pp, pp = Wm[j["parent"]]; Rw, pw = PR @ R, Pp + PR @ (np.subtract(j["pivot"], pp))
                else: Rw, pw = R, np.asarray(j["pivot"], float)
                Wm[j["name"]] = (Rw, pw, np.asarray(j["pivot"], float))
            Rw, pw, p0 = Wm[arm + "_JTwist"]
            self.assertLess(np.linalg.norm(Rw @ [0, 1, 0] - [0, 1, 0]), 1e-6, arm)  # the claw keeps hanging
            V = s.geometry[s.graph[arm + "_Held__fall"][1]].vertices; d = (pw + (V - p0) @ Rw.T).mean(0) - V.mean(0)
            want = np.multiply(r["axis"], -0.3 * v); h = next(g_ for g_ in r["program"]["segs"] if g_[0] <= -0.3 < g_[1])[3]["h"]
            self.assertLess(np.hypot(d[0] - want[0], d[2] - want[2]), 0.01, arm); self.assertLess(abs(d[1] - h), 0.01, arm)  # on the moving parcel


class Stage66(unittest.TestCase):
    """Real-machine arm motion: a program of jerk-limited servo moves through the joints only (no sway), the claw rides
    along with the parcel while it places / scans, and the preview runs the same maths as pipeline/arm_motion.py."""
    def _stations(self):
        lv = os.path.join(ROOT, "levels", "slime_arena")
        E = json.load(open(os.path.join(lv, "mobile", "effects_mobile.json")))
        return [(e["line"], s) for e in E["effects"] if e["type"] == "assembly_line" for s in e["line"]["stations"]]

    def test_tracking_smooth_and_still(self):
        import math, sys
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); import arm_motion as M
        for ln, s in self._stations():
            R, G, v, P = s["rig"], s["rig"]["program"], ln["speed"], s["period"]
            dt = 1 / 240.0; prev = prev2 = None; still = []
            for i in range(int(P / dt)):
                t = s["t0"] + G["start"] + i * dt; a, fl = M.pose(R, G, v, P, t, s["t0"]); q = [a[k] for k in ("yaw", "shoulder", "elbow", "wrist")]
                if prev is not None:
                    d = [x - y for x, y in zip(q, prev)]; self.assertLess(max(map(abs, d)), 0.03, (s["arm"], fl["tau"]))  # no jumps
                    if prev2 is not None: self.assertLess(max(abs(x - 2 * y + z) for x, y, z in zip(q, prev, prev2)), 1.5e-3, (s["arm"], fl["tau"]))  # no velocity jumps
                    if fl["tau"] > G["segs"][-1][0] + 0.01: still.append(max(map(abs, d)))
                prev2, prev = prev, q
            self.assertLess(max(still), 1e-9, s["arm"])  # waiting = standing still (no idle sway)
            if s["task"] == "add":  # while it sets the canister in, the claw tip is exactly over the moving parcel
                for tau in (-0.6, -0.3, 0.0):
                    a, _ = M.pose(R, G, v, P, s["t0"] + tau, s["t0"]); seg = next(g for g in G["segs"] if g[0] <= tau < g[1])
                    want = [R["tip"][0] + R["axis"][0] * v * tau, R["tip"][1] + seg[3]["h"], R["tip"][2] + R["axis"][2] * v * tau]
                    got = M.ik(R, want); self.assertLess(max(abs(a[k] - g_) for k, g_ in zip(("yaw", "shoulder", "elbow"), got)), 1e-9)

    def test_preview_matches_reference(self):
        import shutil, subprocess, sys
        if not shutil.which("node"): self.skipTest("node not installed")
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); import arm_motion as M
        html = open(os.path.join(ROOT, "pipeline", "viewer.html")).read()
        js = "\n".join(l for l in html.split("\n") if l.startswith(("const armSmoother", "const armKeyed", "const armTarget", "const armIK", "  D=Math.max", "  b2=Math.atan2", "const armJoints", "  if(mode==='lin')")))
        ln, s = self._stations()[0]; R, G = s["rig"], s["rig"]["program"]; P = s["period"]
        taus = [G["start"] + k * P / 50 for k in range(50)]
        out = subprocess.run(["node", "-e", js + f"\nconst R={json.dumps(R)};console.log(JSON.stringify({json.dumps(taus)}.map(t=>armJoints(R,R.program,t,{ln['speed']},{P}))));"],
                             capture_output=True, text=True, check=True).stdout
        for tau, j in zip(taus, json.loads(out)):
            a, _ = M.pose(R, G, ln["speed"], P, s["t0"] + tau, s["t0"])
            self.assertLess(max(abs(x - y) for x, y in zip(j, (a["yaw"], a["shoulder"], a["elbow"]))), 1e-9, tau)


class Stage67(unittest.TestCase):
    def test_every_arm_part_rigid_on_its_own_joint(self):
        """The arm parts shared one `mobile` dict, so the last joint written (the hose blend shoulder -> wrist) went to
        every part: the whole arm stretched like a piston. Each part now sits rigidly on its own joint - in level.json
        and in the exported vertex weights (one joint, weight 1)."""
        import numpy as np, sys
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); import glb_tools
        lv = os.path.join(ROOT, "levels", "slime_arena"); L = json.load(open(os.path.join(lv, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        want = {"Turret": "Yaw", "Shoulder": "Shoulder", "Link1": "Shoulder", "Elbow": "Elbow", "Link2": "Elbow", "Spike": "Elbow", "Wrist": "Wrist",
                "Collar": "Twist", "Finger_1": "Finger1", "Finger_2_Tip": "Finger2", "Finger_3_Knuckle": "Finger3"}
        for a in ("Arm_1", "Arm_2", "Arm_3", "Arm_4"):
            for p, j in want.items(): self.assertEqual(by[f"{a}_{p}"]["mobile"]["joint"], f"{a}_J{j}", (a, p))
            self.assertFalse([n for n in by if n.startswith(a + "_Hose")])  # no cable across a moving joint
        g, b = glb_tools._read(os.path.join(lv, "mobile", "level_mobile.glb"))
        def acc(i, dt, nc):
            a = g["accessors"][i]; bv = g["bufferViews"][a["bufferView"]]; o = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
            return np.frombuffer(b[o:o + a["count"] * nc * np.dtype(dt).itemsize], dtype=dt).reshape(-1, nc)
        for n in g["nodes"]:
            if "skin" in n:
                p = g["meshes"][n["mesh"]]["primitives"][0]["attributes"]; W = acc(p["WEIGHTS_0"], "<f4", 4); J = acc(p["JOINTS_0"], "<u1", 4)
                self.assertTrue(np.allclose(W[:, 0], 1.0), n["name"])
                if n["name"].endswith("Upper__structure_b"): self.assertGreaterEqual(len(set(J[:, 0].tolist())), 7, n["name"])  # yaw .. fingers all used


class Stage68(unittest.TestCase):
    def test_wall_fans_and_running_belts(self):
        """Two spinning fans (own rotor nodes, effect spin) with a louvred vent under each in the wall block over the Works
        gate; the working belts have their own material whose UVs scroll with the parcels (speed / tile, along the axis)."""
        lv = os.path.join(ROOT, "levels", "slime_arena"); L = json.load(open(os.path.join(lv, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        for i in (1, 2):
            self.assertTrue(by[f"Lintel_Fans_Fan_{i}_Rotor"].get("spin")); self.assertIn(f"Lintel_Fans_Vent_{i}_Slat_1", by)
        E = json.load(open(os.path.join(lv, "mobile", "effects_mobile.json")))
        self.assertTrue(all(any(t == f"Lintel_Fans_Fan_{i}_Rotor" for e in E["effects"] if e["type"] == "spin" for t in e["targets"]) for i in (1, 2)))
        self.assertEqual(by["Conv_East_Belt"]["material"], "belt"); self.assertIn("belt", L["materials"])
        for e in E["effects"]:
            if e["type"] == "assembly_line":
                ln = e["line"]; tile = L["materials"]["belt"]["tile_m"]
                self.assertAlmostEqual(ln["belt"]["scroll"][1], -ln["axis"][2] * ln["speed"] / tile, places=4)
        self.assertIn("uv1_offset", open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read())


class Stage69(unittest.TestCase):
    def test_slime_tunnels_through_the_north_wall(self):
        """Two arched slime tunnels (x -28 / +28) through the north wall and the hall walkway base under it: the bore is
        open (no solid box left across it below the crown), liquid runs through it, the walkway deck / walkable area
        is untouched and both mouths are dressed."""
        import sys, numpy as np
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); from anchors import world_matrices
        lv = os.path.join(ROOT, "levels", "slime_arena"); L = json.load(open(os.path.join(lv, "level.json"))); W, by = world_matrices(L)
        self.assertIn({"name": "Walkway_North", "min": [-56.0, -56.0], "max": [56.0, -51.0], "y": 7.0}, L["walkable"])
        self.assertEqual(by["Walkway_North_Floor"]["size"], [112.3, 0.3, 5.3])
        pool = by["HazardFluid_2"]; self.assertAlmostEqual(pool["position"][2] + pool["size"][2] / 2, -56.0, places=2)  # reaches the hall pool
        for tid, x in (("Tunnel_West", -28.0), ("Tunnel_East", 28.0)):
            for k in ("_MouthA_Voussoir_5", "_MouthB_Voussoir_5", "_MouthA_Keylight", "_Rib_1_Lamp"): self.assertIn(tid + k, by)
            self.assertTrue(by[f"{tid}_Bore_Walkway_North_Base" + ("" if x < 0 else "_R")]["waterway"])
            for o in L["objects"]:  # nothing solid left in the bore below the crown (3.3 m half width, crown 4.95)
                if o["type"] != "box" or o["name"] in L["hazards"] or o.get("collision") is False: continue
                M = np.asarray(W[o["name"]]); (cx, cy, cz), (w, h, d) = M[:3, 3], o["size"]
                if np.allclose(M[:3, :3], np.eye(3)) and abs(cx - x) < w / 2 + 3.0 and cz - d / 2 < -51.1 and cz + d / 2 > -59.9 and cy < 4.0 and cy + h > 1.2:
                    self.fail(f"{o['name']} blocks {tid}")
