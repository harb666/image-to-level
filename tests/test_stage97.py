"""Stage 97: Assembly Ascent - Construct Error map 3 (levels/assembly_ascent, from the level 3 concept image)."""
import json, math, os, sys, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


def _load(name):
    with open(os.path.join(LV, name)) as f: return json.load(f)


class AssemblyAscent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = _load("level.json"); cls.by = {o["name"]: o for o in cls.L["objects"]}

    def test_route_is_reachable_end_to_end(self):
        """Start deck -> yard ramp -> robot ring -> pillars + press pad -> belt landing -> belts -> upper deck -> stairs ->
        exit deck: every floor of the route is in a reachable nav component, and the walk check finds no errors."""
        N = _load("checks/navigation.json"); areas = {a["name"]: a["reachable_fraction"] for a in N["intended_areas"]}
        for n in ("Start_Deck", "Robot_Ring", "Belt_Landing", "Upper_Deck", "Exit_Deck", "Spinner_Deck"): self.assertEqual(areas.get(n), 1.0, n)
        cut = {o for c in N["component_list"] if not c.get("reachable") for o in c.get("objects", [])}  # (component object lists are samples: test the unreachable side)
        for n in ["Yard_Bridge_Deck", "Spike_Press_Pad", "Belt_A_Deck", "Belt_B_Deck"] + [f"Pillars_{k}_Cap" for k in range(1, 8)]:
            self.assertIn(n, self.by); self.assertNotIn(n, cut, n)
        T = _load("checks/traverse.json"); self.assertTrue(T["passed"], [f["message"] for f in T["findings"] if f["severity"] == "error"])

    def test_saws_chop_across_the_walkway(self):
        """Two saw arms; at angle 0 each blade is over the yard ramp at a height that hits a player standing on it, and the
        two swing half a period apart."""
        S = {s["id"]: s for s in self.L["saws"]}; self.assertEqual(set(S), {"Saw_West", "Saw_East"})
        ramp = self.by["Yard_Bridge_Deck"]
        for s in S.values():
            self.assertTrue(self.by[s["id"] + "_Saw"]["type"] == "saw_blade" and self.by[s["id"] + "_Saw"]["mobile"]["group"] == s["blade"])
            self.assertLess(abs(s["center"][0] - (-31.95)), 0.6)  # over the ramp's centre line
            self.assertTrue(0.0 < s["center"][1] - s["radius"] - 6.0 < 1.8)  # the blade's lower edge is within a player's height of the deck
            self.assertAlmostEqual(math.hypot(*s["axis"]), 1.0, places=3)
        self.assertAlmostEqual(abs(S["Saw_West"]["phase"] - S["Saw_East"]["phase"]), S["Saw_West"]["period"] / 2, places=3)
        for s in S.values():  # Stage 101: jointed - shoulder, elbow, wrist each pivot (own groups), the outer ones lagging
            J = s["joints"]; self.assertEqual(len(J), 3); self.assertEqual([j["group"] for j in J], [s["id"] + "_Arm", s["id"] + "_Fore", s["id"] + "_Wrist"])
            self.assertEqual(s["spin"], s["id"] + "_Blade")  # Stage 102: only the blade spins (motor + guard ride the wrist)
            self.assertGreater(J[0]["pivot"][1], 20.0); self.assertIn(s["id"] + "_Plate", self.by)  # hangs from the ceiling, nothing stands in the pool
            self.assertFalse([n for n in self.by if n.startswith(s["id"] + "_Pedestal")])
            self.assertEqual(self.by[s["id"] + "_Hub" if s["id"] + "_Hub" in self.by else s["id"] + "_Flange"]["mobile"]["group"], s["id"] + "_Blade")
            self.assertTrue(J[0]["lag"] < J[1]["lag"] < J[2]["lag"]); self.assertTrue(all(j["amp"] > 0 for j in J))
            self.assertEqual(self.by[s["id"] + "_Elbow"]["mobile"]["group"], s["id"] + "_Fore")
        for s in S.values(): self.assertEqual(s["slots"], ["Yard_Bridge"]); self.assertGreaterEqual(s["slot"], 0.8)  # Stage 99/100: each blade cuts its own (jumped) slot
        self.assertEqual(sum(1 for n in self.by if "_SlotEdge_" in n), 4)  # hazard stripes on both lips of both openings
        self.assertFalse([n for n in self.by if n.startswith("Yard_Bridge_Threshold")])  # ... instead of at the bridge's ends
        decks = sorted(n for n in self.by if n.startswith("Yard_Bridge_Deck") and "_SlotEdge_" not in n); self.assertEqual(len(decks), 3)
        ends = sorted(abs(self.by[n]["position"][2]) for n in decks); self.assertTrue(all(self.by[n]["size"][2] > 1.0 for n in decks))
        self.assertEqual(ramp["type"], "box")

    def test_belts_run_against_the_climb_over_spike_pits(self):
        B = {b["id"]: b for b in self.L["belts"]}; self.assertEqual(set(B), {"Belt_A", "Belt_B"})
        K = {k["id"]: k for k in self.L["kills"]}
        for b in B.values():
            self.assertLess(b["speed"], 0); self.assertGreater(b["axis"][1], 0.2)  # uphill axis, belt runs down it
            self.assertIn(b["id"] + "_Pit", K); self.assertEqual(b["kill"]["id"], b["id"] + "_Pit")
            self.assertEqual(self.by[b["id"] + "_Deck"].get("approach"), "jump_foot")
            self.assertTrue(any(n.startswith(b["chevrons"]) for n in self.by))
        C = _load("mobile/collision.json"); self.assertEqual({k["id"] for k in C["kills"]}, set(K)); self.assertEqual(len(C["belts"]), 2); self.assertEqual(len(C["saws"]), 2)

    def test_spiked_press_and_laser_gates(self):
        c = next(c for c in self.L["crushers"] if c["id"] == "Spike_Press")
        self.assertAlmostEqual(c["travel"], 5.4 - 0.02, places=3)  # Stage 125: the head lands on the pad, the teeth sink into sockets
        self.assertEqual((c["period"], c["phase"]), (4.0, 0.0))  # the slam cycle survives into effects (viewer / Godot need it)
        O = {o["name"]: o for o in self.L["objects"]}
        teeth = sorted((round(o["position"][0], 3), round(o["position"][2], 3)) for k, o in O.items() if k.startswith("Spike_Press_Spike_"))
        socks = {k: o for k, o in O.items() if k.startswith("Spike_Press_Socket_")}
        self.assertEqual(sorted((round(o["position"][0], 3), round(o["position"][2], 3)) for o in socks.values()), teeth)  # one socket under every tooth
        for o in socks.values():
            self.assertGreater(o["size"][0], O["Spike_Press_Spike_01"]["size"][0])  # the tooth fits inside its socket
        self.assertTrue(any(k.startswith("Spike_Press_PadTop_") for k in O))  # the pad's top layer is split round the sockets
        self.assertGreaterEqual(sum(1 for n in self.by if n.startswith("Spike_Press_Spike_")), 4)
        G = {g["id"]: g for g in self.L["gates"]}
        self.assertEqual(G["Yard_Laser"]["opens_on"], {"type": "terminal", "terminal": "Jet_Screen_Button"})  # Stage 119: the jetpack screen's big red button (on the arena)
        self.assertEqual(G["Exit_Laser"]["opens_on"], {"type": "waves_cleared", "encounter": "Deck_Waves"})

    def test_entrance_exit_and_campaign(self):
        S = _load("scene_spec.json"); self.assertEqual(S["campaign"]["previous"], "slime_arena")
        E = self.L["entrances"]; self.assertEqual(E[0]["type"], "doorway"); self.assertEqual(E[0]["comes_from"], "slime_arena")
        self.assertEqual([x["target"] for x in self.L["exits"]], ["level2_part1"])
        sig = self.L["materials"]["signs"]; self.assertEqual(set(sig["atlas"]), {"a", "b", "c", "d"})
        self.assertTrue(os.path.exists(os.path.join(ROOT, sig["grid"][0][0]["image"])))
        self.assertEqual(self.L["materials"]["stripe"]["type"], "chevron"); self.assertGreater(self.L["materials"]["stripe"]["color"][1], 0.6)  # yellow stripes

    def test_mobile_budget_and_runtimes(self):
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")), 4000 * 1024)
        E = _load("effects.json")["effects"]; t = {e["type"] for e in E}; self.assertTrue({"saw", "belt"} <= t)
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")) as f: gd = f.read()
        self.assertIn("func _update_saws", gd); self.assertIn("cb.move_and_collide(u * float(b[\"speed\"]) * delta)", gd)
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_mobile.gd")) as f: self.assertIn('col.get("kills", [])', f.read())
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: v = f.read()
        self.assertIn("fx.category==='saw'", v); self.assertIn("window.belts", v)
        self.assertIn("'pointercancel','lostpointercapture'", v); self.assertIn("-webkit-touch-callout:none", v)  # Stage 107: up / down never stick on iOS


class SpinnerDeck(unittest.TestCase):
    def test_spinner_gates_the_yard(self):
        """Stage 98: the spinner deck (from the user's concept) sits east of the start deck; its four arms sweep at shin
        height (a bar can be jumped, a ball cannot); the control terminal on its far pad opens the yard's laser gate, so the
        pillars can only be reached after crossing it. Deck, pads and terminal pad are reachable."""
        L = _load("level.json"); by = {o["name"]: o for o in L["objects"]}; G = _load("gameplay.json") if os.path.exists(os.path.join(LV, "gameplay.json")) else None
        sw = next(s for s in L["sweepers"] if s["id"] == "Spinner"); self.assertEqual(len(sw["arms"]), 4)
        jump = (G or {}).get("player", {}).get("jump_height", 1.2)
        self.assertLess(sw["bar_y"] + sw["bar_half"], jump - 0.2)  # bar top clears with a jump
        self.assertGreater(sw["ball_y"] + sw["ball_r"], jump + 0.15)  # a ball does not
        self.assertAlmostEqual(sw["ball_y"], sw["bar_y"]); self.assertGreater(sw["ball_y"] - sw["ball_r"], 0.0)  # Stage 104: each mace sits on its pole's axis, clear of the deck
        for k in range(1, 5):
            self.assertEqual(by[f"Spinner_Rotor_Ball_{k}"]["type"], "mace"); self.assertEqual(by[f"Spinner_Rotor_Tips_{k}"]["type"], "mace_tips")
            self.assertEqual(by[f"Spinner_Rotor_Arm_{k}"]["type"], "pole"); self.assertIn(f"Spinner_Rotor_Socket_{k}", by)  # Stage 106: own wrap-around UVs
            self.assertEqual(L["materials"][by[f"Spinner_Rotor_Arm_{k}"]["material"]]["type"], "hazard_wrap")
            for sd in "LR":  # Stage 106: the pad bridges' side rails run from the deck's edge to the pad's edge
                rl = by[f"Spinner_Pad_{k}_BridgeRail_{sd}"]; d = math.hypot(rl["position"][0] - sw["center"][0], rl["position"][2] - sw["center"][2])
                inner = (d ** 2 - 1.38 ** 2) ** 0.5 - rl["size"][2] / 2; outer = inner + rl["size"][2]
                self.assertLess(inner, 11.15 * math.cos(math.pi / 8)); self.assertGreater(outer, 18.0 - 4.0 * math.cos(math.pi / 8) - 0.3)  # (Stage 124: up to the floating pad's gap)
                self.assertIn(f"Spinner_Pad_{k}_BridgePost0_{sd}", by); self.assertIn(f"Spinner_Pad_{k}_BridgePost1_{sd}", by)
        c = sw["center"]; posts = [o for n, o in by.items() if n.startswith("Spinner_Post_")]
        self.assertGreater(min(math.hypot(o["position"][0] - c[0], o["position"][2] - c[2]) - 0.33 for o in posts), sw["r1"] + sw["ball_r"] + 0.1)  # the maces clear the lamp posts
        self.assertEqual(by["Spinner_Skirt"]["material"], "arm_yellow"); self.assertNotEqual(by["Spinner_CrownBand"]["material"], "stripe")  # painted, not chevrons
        FX = {e["id"]: e for e in _load("effects.json")["effects"]}
        for n in ("Spinner_GlandJets", "Spinner_HeadJets", "Spinner_CrownJets"):  # Stage 105: jets out of nozzles on the press, synced to its cycle
            self.assertEqual(FX[n]["type"], "steam_jet"); self.assertEqual(FX[n]["sync"]["period"], sw["drive"]["period"]); self.assertEqual(len(FX[n]["emitters"]), 4)
            for e in FX[n]["emitters"]: self.assertAlmostEqual(math.hypot(*e["dir"]), 1.0, places=2)
        self.assertEqual(FX["Spinner_HeadJets"]["sync"]["at"], [sw["drive"]["slam"]]); self.assertTrue(all(n in by for n in ("Spinner_GlandNozzle_1", "Spinner_HeadNozzle_1", "Spinner_CrownVent_1")))
        self.assertEqual(by["Spinner_HeadNozzle_1"]["mobile"]["group"], sw["drive"]["press"])
        self.assertEqual(by["Spinner_Deck_Floor"]["material"], "deck_scraped"); M = L["materials"]["deck_scraped"]  # Stage 105: plain deck scored by the maces
        self.assertEqual(M["type"], "scrape_rings"); self.assertAlmostEqual(M["tile_m"], by["Spinner_Deck_Floor"]["size"][0], places=3)
        self.assertTrue(any(r0 <= sw["r1"] <= r1 and s_ >= 0.9 for r0, r1, s_ in M["rings"]))  # the heaviest wear is under the mace heads
        D = sw["drive"]  # Stage 103: a ceiling press drives it - slam, fast spin, coast to a stop, a still gap to cross
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); from modules.assembly import press_profile
        P = D["period"]; self.assertGreaterEqual(D["still"], 3.0); self.assertGreater(D["peak_rpm"], 30)
        self.assertGreaterEqual(D["still"] * (G or {}).get("player", {}).get("walk_speed", 5.0), 14.0)  # time to cross pad-to-pad (14.9 m chord) at walking speed
        for k in range(3):  # always stops in the same pose; still (and the press up) through the still window
            a0 = press_profile(D, k * P + P - D["still"] + 0.05 - D["phase"]); a1 = press_profile(D, k * P + P - 0.05 - D["phase"])
            self.assertAlmostEqual(a0[1], a1[1], places=3); self.assertAlmostEqual(a0[1] / 360.0, round(a0[1] / 360.0), places=4)
            self.assertEqual(a1[0], 0.0)
        off, _ = press_profile(D, D["slam"] + 0.5 - D["phase"]); self.assertAlmostEqual(off, -D["travel"])  # pressed
        self.assertAlmostEqual(by["Spinner_Striker"]["position"][1] - D["travel"], by["Spinner_Strike"]["position"][1] + by["Spinner_Strike"]["size"][1], places=3)  # lands on the red strike plate
        self.assertAlmostEqual(by["Spinner_PressPlate"]["position"][1] + by["Spinner_PressPlate"]["size"][1], 34.5, places=3)  # hangs from the ceiling
        self.assertEqual([s["frac"] for s in D["stages"]], [0.5, 1.0]); self.assertEqual(by["Spinner_Head"]["mobile"]["group"], D["press"])
        self.assertFalse([n for n in by if n.startswith("Spinner_PipeUp_")])  # nothing on the cap for the head to hit
        self.assertFalse([t_ for t_ in L.get("terminals", []) if t_["id"] == "Spinner_Terminal"])  # Stage 119: the gate's key is now the jet screen's button
        pad = by["Spinner_Pad_2_Deck"]
        N = _load("checks/navigation.json"); cut = {o for c in N["component_list"] if not c.get("reachable") for o in c.get("objects", [])}
        self.assertEqual({a["name"]: a["reachable_fraction"] for a in N["intended_areas"]}["Spinner_Deck"], 1.0)
        for n in ("Spinner_Deck_Floor", "Spinner_Ramp_Deck", "Spinner_Pad_1_Deck", "Spinner_Pad_2_Deck", "Spinner_Pad_3_Deck", "Spinner_Pad_4_Deck"): self.assertIn(n, by); self.assertNotIn(n, cut, n)
        self.assertEqual(pad["type"], "cylinder")
        E = {e["type"] for e in _load("effects.json")["effects"]}; self.assertIn("sweeper", E)
        self.assertEqual(len(_load("mobile/collision.json")["sweepers"]), 1)
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: self.assertIn("fx.category==='sweeper'", f.read())
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")) as f: gd = f.read()
        self.assertIn("func _sweeper", gd); self.assertIn("static func press_profile", gd)
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: v = f.read()
        self.assertIn("window.camShake", v); self.assertIn("isBurst&&fx.sync", v); self.assertIn("p.damping", v); self.assertIn("EMISSION_SHAPE_DIRECTED_POINTS", gd); self.assertIn('if b.size() > 4:  # Stage 104: synced vents', gd)


class CornerOverlook(unittest.TestCase):
    def test_overlook_and_lift_pad(self):
        """Stage 108: a corner balcony 8 m above the spinner deck, reached by the spinner's NE hover pad, which lifts
        players up to its gantry (and comes when called from either end). Reachable in the nav check via the lift link;
        the pad's colliders are the runtime's (not static); the pads' octagon flats face their bridges."""
        L = _load("level.json"); by = {o["name"]: o for o in L["objects"]}
        lf = next(l for l in L["lifts"] if l["id"] == "Spinner_Pad_1_Lift"); self.assertAlmostEqual(lf["travel"], 8.0); self.assertEqual({c["at"] for c in lf["calls"]}, {"bottom", "top"})
        dk = by["Overlook_Deck"]; self.assertAlmostEqual(dk["position"][1] + dk["size"][1], lf["top"]); self.assertGreater(lf["top"] - 7.5, 6.0)  # well above the spinner deck
        g = by["Overlook_Gantry"]; gx0 = g["position"][0] - g["size"][0] / 2
        self.assertAlmostEqual(gx0, lf["center"][0] + lf["deck_radius"] * math.cos(math.pi / 8) + 0.15, delta=0.1)  # the raised pad docks at its end (Stage 124: a 0.15 m gap - it floats)
        self.assertAlmostEqual(g["position"][1] + g["size"][1], lf["top"])
        for n in ("Spinner_Pad_1_Deck", "Spinner_Pad_1_Hull"): self.assertEqual(by[n]["mobile"]["group"], lf["group"]); self.assertEqual(by[n]["lift"], lf["id"])
        self.assertAlmostEqual(by["Spinner_Pad_2_Deck"]["rotation"][1] % 45, 22.5, places=3)  # flats (not corners) face the bridges
        N = _load("checks/navigation.json"); A = {a["name"]: a["reachable_fraction"] for a in N["intended_areas"]}
        self.assertEqual(A.get("Overlook_Deck"), 1.0); self.assertEqual(A.get("Overlook_Gantry"), 1.0)
        self.assertEqual(sorted(l_["dy"] for l_ in N["links"] if l_.get("kind") == "lift"), [-8.0, 8.0])
        C = _load("mobile/collision.json"); self.assertEqual(len(C["lifts"]), 1)
        lp = {n for n, o in by.items() if o.get("lift")}; self.assertIn("Spinner_Pad_1_Deck", lp)
        self.assertFalse([c for c in C["colliders"] if c["source"] in lp])  # no static collider left at the bottom stop
        self.assertTrue([c for c in C["colliders"] if c["source"] == "Spinner_Pad_1_Bridge"])  # (the bridge stays put)
        self.assertTrue([c for c in C["colliders"] if c["source"] == "Overlook_Deck"])
        self.assertIn("lift", {e["type"] for e in _load("effects.json")["effects"]})
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")) as f: gd = f.read()
        self.assertIn("func _update_lifts", gd); self.assertIn("AnimatableBody3D.new()", gd)
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: v = f.read()
        self.assertIn("fx.category==='lift'", v); self.assertIn("window.__teleport", v)
        for n in by:  # railings: top rail above a jump
            if n.startswith("Overlook_Rail") and n.endswith("_High"): self.assertGreater(by[n]["position"][1] - lf["top"], 1.2)


class FloatingPads(unittest.TestCase):
    def test_spinner_pads_float_like_the_screen(self):
        """Stage 123: the spinner's hover pads bob and sway (and their jets flicker) like the jet screen - one skinned
        rig for the three plain pads (a bone per pad + per flame), the lift pad bobbing on top of its travel; their deck
        colliders move with them in Godot (no static colliders exported), and the bob stays small for the bridges."""
        L = _load("level.json"); by = {o["name"]: o for o in L["objects"]}
        F = next(f for f in L["floaters"] if f["id"] == "Spinner_FloatRig"); self.assertEqual(len(F["pads"]), 3)
        self.assertIn("Spinner_Float", L["skeletons"]); self.assertEqual(len({p["phase"] for p in F["pads"]}), 3)  # each on its own rhythm
        for p in F["pads"]: self.assertLessEqual(p["bob"][0], 0.35); self.assertLessEqual(p["tilt"], 3.0)
        for k in (2, 3, 4):
            self.assertEqual(by[f"Spinner_Pad_{k}_Deck"]["mobile"]["group"], F["group"]); self.assertEqual(by[f"Spinner_Pad_{k}_Jet"]["mobile"]["joint"], f"Spinner_Pad_{k}_FF")
        lf = L["lifts"][0]; self.assertIn("bob", lf); self.assertEqual(lf["flame"], "Spinner_Pad_1_Flame")
        for k in (1, 2, 3, 4):  # Stage 124: the bridges stop short of the (moving) pads - a small gap, an easy step
            p = by[f"Spinner_Pad_{k}_Deck"]["position"]; br = by[f"Spinner_Pad_{k}_Bridge"]; bc = br["position"]
            d_end = math.hypot(bc[0] - p[0], bc[2] - p[2]) - br["size"][2] / 2; edge = 4.0 * math.cos(math.pi / 8)
            self.assertTrue(0.08 < d_end - edge < 0.3, (k, d_end - edge))
        C = _load("mobile/collision.json"); self.assertFalse([c for c in C["colliders"] if c["source"].startswith(("Spinner_Pad_2_Deck", "Spinner_Pad_3_Deck", "Spinner_Pad_4_Deck"))])
        self.assertEqual(len(C["floaters"]), 1)
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: v = f.read()
        self.assertIn("fx.category==='floater'", v); self.assertIn("const floatPose=(F,t)=>", v)
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")) as f: gd = f.read()
        self.assertIn("func _update_floaters", gd); self.assertIn("static func float_pose", gd)


class GearDecal(unittest.TestCase):
    def test_gear_emblem_has_no_background_tile(self):
        """Stage 122: the grinning gear on the start deck is a cut-out decal (transparent round the cog)."""
        L = _load("level.json"); d = next(o for o in L["objects"] if o["name"] == "Gear_Emblem_Decal")
        M = L["materials"][d["material"]]; self.assertEqual(M["type"], "image_decal"); self.assertGreater(M["cutout"], 0)
        from PIL import Image
        im = Image.open(os.path.join(ROOT, M["image"])).convert("RGBA"); self.assertEqual(im.getpixel((5, 5))[3], 0); self.assertEqual(im.getpixel((im.width // 2, im.height // 2))[3], 255)


class SouthWallFans(unittest.TestCase):
    def test_banners_and_fake_door_became_fans_and_a_vent(self):
        """Stage 120: arena walls module_overrides - the two red banners and the sealed door behind the spinner's NE pad
        are two big spinning wall fans with an air vent between them; the slots either side are untouched."""
        L = _load("level.json"); names = {o["name"] for o in L["objects"]}
        for gone in ("OuterWall_South_M03Emblem", "OuterWall_South_M04Door", "OuterWall_South_M05Emblem"): self.assertFalse([n for n in names if n.startswith(gone)], gone)
        for k in ("M03Fan_Rotor", "M05Fan_Rotor", "M04Vent"): self.assertIn("OuterWall_South_" + k, names)
        self.assertTrue([n for n in names if n.startswith("OuterWall_South_M02Pipes")] and [n for n in names if n.startswith("OuterWall_South_M06Pipes")])
        spin = next(e for e in _load("effects.json")["effects"] if e["type"] == "spin")
        self.assertTrue({"OuterWall_South_M03Fan_Rotor", "OuterWall_South_M05Fan_Rotor"} <= set(spin["targets"]))


class JetScreen(unittest.TestCase):
    def test_jetpack_screen_and_big_red_button(self):
        """Stage 119: the big grin screen floats on a jetpack (no chains), bobbing; when the player reaches the arena it
        flies over (goofy: double take, barrel roll, overshoot), opens a drawer with a big red button at hand height in
        front of the player; the button is a terminal - live only once the screen has arrived - that opens the yard's
        laser gate; then the screen spins and flies home."""
        L = _load("level.json"); by = {o["name"]: o for o in L["objects"]}
        self.assertFalse([n for n in by if n.startswith("Sign_Grin_Big")])
        J = next(j for j in L["jets"] if j["id"] == "Jet_Screen"); self.assertEqual(J["trigger"]["name"], "Arena_Deck")
        for k in ("Panel", "Thruster" + "L", "Nozzle" + "R", "Flame" + "L", "Garage", "Drawer", "Button", "ButtonRing"): self.assertIn("Jet_Screen_" + k, by)
        self.assertFalse([n for n in by if n.startswith("Jet_Screen_") and by[n].get("collision", True) is not False and by[n]["type"] != "group"])  # never solid
        self.assertEqual(by["Jet_Screen_Button"]["mobile"]["group"], J["cap"]); self.assertEqual(by["Jet_Screen_Button"]["material"], "glow")  # red
        T = next(t_ for t_ in L["terminals"] if t_["id"] == J["button"]); self.assertEqual(T["activates"], ["Yard_Laser"]); self.assertEqual(T["requires"], "Jet_Screen")
        self.assertTrue(1.0 < T["button"][1] - J["trigger"]["y"] < 2.6)  # within reach (a jump at most) over the arena floor
        tr = J["trigger"]; self.assertTrue(tr["min"][0] < T["center"][0] < tr["max"][0] and tr["min"][1] < T["center"][2] < tr["max"][1])
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); from modules.assembly import jet_pose
        TM = J["times"]; ys = [jet_pose(J, "home", i * 0.1)[0][1] for i in range(60)]; self.assertGreater(max(ys) - min(ys), 0.6)  # bobs
        P = [jet_pose(J, "fly", i * 0.05) for i in range(int((TM["take"] + TM["fly"] + TM["settle"]) / 0.05))]
        self.assertTrue(any(160 < p[3] < 200 for p in P))  # barrel roll
        self.assertGreater(max(p[0][1] for p in P), J["home"][1] + 1.0)  # swoops up
        end = jet_pose(J, "fly", TM["take"] + TM["fly"] + TM["settle"] + 2.0); self.assertLess(math.dist(end[0], J["arrive"]), 0.5); self.assertEqual(end[4], 1.0)  # arrived, drawer open
        self.assertGreater(max(jet_pose(J, "press", i * 0.02)[5] for i in range(15)), 0.9)  # the cap goes down
        back = jet_pose(J, "back", TM["back"] + 0.1); self.assertLess(math.dist(back[0], J["home"]), 0.01); self.assertEqual(back[4], 0.0)
        # Stage 121: it hovers off the arena's south-west corner, tilted down at the players, and no part of it ever comes
        # near the arena floor (arrived, in flight, pressed, flying home); the button reaches in over the corner tile
        self.assertGreater(J["arrive_pitch"], 5.0); R = next(r for r in L["risers"] if r["id"] == "Arena")
        xs = [p["center"][0] for p in R["pads"]]; zs = [p["center"][2] for p in R["pads"]]; x0, x1, z0, z1 = min(xs) - 2, max(xs) + 2, min(zs) - 2, max(zs) + 2
        self.assertFalse(x0 < J["arrive"][0] < x1 and z0 < J["arrive"][2] < z1)  # the screen itself is off the arena
        self.assertTrue(x0 + 0.5 < T["button"][0] < x1 and z0 + 0.5 < T["button"][2] < z1)
        from anchors import world_matrices
        from build_level import shape
        import numpy as np
        Wm, _ = world_matrices(L); groups = (J["body"], J["flame"], J["hatch"], J["cap"]); V = {}
        for o in L["objects"]:
            g = (o.get("mobile") or {}).get("group")
            if g in groups: m = shape(o); V.setdefault(g, []).append(np.c_[m.vertices, np.ones(len(m.vertices))] @ Wm[o["name"]].T)
        V = {k: np.vstack(v) for k, v in V.items()}
        def M_(tr=None, ry=0.0, rx=0.0, rz=0.0):
            a, b, c = (math.radians(q) for q in (ry, rx, rz)); Y = np.array([[math.cos(a), 0, math.sin(a), 0], [0, 1, 0, 0], [-math.sin(a), 0, math.cos(a), 0], [0, 0, 0, 1]])
            X = np.array([[1, 0, 0, 0], [0, math.cos(b), -math.sin(b), 0], [0, math.sin(b), math.cos(b), 0], [0, 0, 0, 1]]); Z = np.array([[math.cos(c), -math.sin(c), 0, 0], [math.sin(c), math.cos(c), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
            Tt = np.eye(4); Tt[:3, 3] = tr if tr is not None else [0, 0, 0]; return Tt @ Y @ X @ Z
        Linv = np.linalg.inv(M_(J["home"], J["yaw0"])); floor = J["trigger"]["y"]
        def clearance(ph, t_):
            p, yw, pt, rl, h, c, fs = jet_pose(J, ph, t_); P = M_(p, yw, pt, rl); lo = 99.0
            for g, Vg in V.items():
                X = M_([0, -c * J["press"] if g == J["cap"] else 0.0, h * J["slide"] if g in (J["hatch"], J["cap"]) else 0.0])
                Q = (Vg @ (P @ X @ Linv).T)[:, :3]; over = (Q[:, 0] > x0 + 2) & (Q[:, 0] < x1 - 2) & (Q[:, 2] > z0 + 2) & (Q[:, 2] < z1 - 2)
                if over.any(): lo = min(lo, float(Q[over, 1].min()) - floor)
            return lo
        cl = [clearance("wait", 3.0)] + [clearance("fly", i * 0.1) for i in range(int((TM["take"] + TM["fly"] + TM["settle"]) / 0.1))]
        cl += [clearance("press", i * 0.1) for i in range(16)] + [clearance("back", i * 0.2) for i in range(18)]
        self.assertGreater(min(cl), 1.0)
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: v = f.read()
        for s_ in ("fx.category==='jet'", "if(m.t.requires&&!(window.jetReady||{})[m.t.requires])continue;", "K.trigger(pos.x", "window.gateOpen"): self.assertIn(s_, v)
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")) as f: gd = f.read()
        for s_ in ("static func jet_pose", "func _update_jets", '"terminal_activated"'): self.assertIn(s_, gd)


class OverlookScreens(unittest.TestCase):
    def test_wall_tvs_moved_up_onto_the_overlook(self):
        """Stage 117/118: the two wall TVs under the overlook are gone from there; two framed screens are built into the
        walls above the overlook deck, facing straight out of the wall (not angled), raised clear of heads."""
        L = _load("level.json"); by = {o["name"]: o for o in L["objects"]}
        for u in ("OuterWall_East_M12Monitor", "OuterWall_South_M01Monitor"):
            self.assertFalse([n for n in by if n.startswith(u + "_") and n[len(u) + 1:].split("_")[0] in ("Body", "Screen", "Arm", "Cable")], u)
        self.assertFalse([n for n in by if n.startswith("Overlook_Screen_")])  # no free-standing (angled) screens
        top = by["Overlook_Deck"]["position"][1] + by["Overlook_Deck"]["size"][1]
        for k, (yaw, wall) in ((1, (180.0, ("z", 65.0))), (2, (270.0, ("x", 50.0)))):
            b = by[f"Overlook_WallScreen_{k}_Body"]; self.assertEqual(by[f"Overlook_WallScreen_{k}_Glass"]["material"], "screen")
            self.assertAlmostEqual(b["rotation"][1] % 360, yaw); self.assertGreater(b["position"][1] - top, 2.0)
            i = 2 if wall[0] == "z" else 0; self.assertLess(abs(b["position"][i] - wall[1]), 0.1)  # back against the wall face
            for p in ("FrameT", "FrameB", "FrameL", "FrameR", "TrimT", "Ledge", "Header", "SpeakerL", "SpeakerR"): self.assertIn(f"Overlook_WallScreen_{k}_{p}", by)


class RisingArena(unittest.TestCase):
    def test_arena_rises_at_the_open_edge(self):
        """Stage 109-111: the overlook's north edge is open; walking to it raises a symmetric gladiator floor out of the
        slime: a 5 x 5 grid of equal square tiles with even seams, docked against the overlook (same height), rising
        ring by ring from the centre. Each tile rises goofily (peeks out, looks around, ducks, pops past its height,
        squashes and sways); personalities and delays are symmetric. A wave encounter runs on it."""
        L = _load("level.json"); by = {o["name"]: o for o in L["objects"]}; S = _load("scene_spec.json")
        self.assertFalse([n for n in by if n.startswith("Overlook_RailN")])  # open edge
        R = next(r for r in L["risers"] if r["id"] == "Arena"); ov = by["Overlook_Deck"]; top = ov["position"][1] + ov["size"][1]
        P = R["pads"]; self.assertEqual(len(P), 25); self.assertTrue(all(abs(p["center"][1] - top) < 1e-6 and p["size"] == 4.0 for p in P))
        xs = sorted({p["center"][0] for p in P}); zs = sorted({p["center"][2] for p in P}); self.assertEqual((len(xs), len(zs)), (5, 5))
        for v in (xs, zs): self.assertTrue(all(abs((b - a) - 4.2) < 1e-3 for a, b in zip(v, v[1:])))  # equal tiles, equal seams
        caps = [by[n] for n in by if n.startswith("Arena_Tile_") and n.endswith("_Cap")]; self.assertEqual(len(caps), 25)
        self.assertLess(abs(max(c["position"][2] + c["size"][2] / 2 for c in caps) - (ov["position"][2] - ov["size"][2] / 2)), 0.3)  # docked
        c = R["trigger"]["center"]; self.assertLess(abs(c[2] - (ov["position"][2] - ov["size"][2] / 2)), 2.0)  # at the open edge
        joints = {p["joint"]: p for p in P}; on = [o["name"] for o in L["objects"] if (o.get("mobile") or {}).get("joint") in joints]
        self.assertFalse([n for n in on if not n.endswith(("_Column", "_Bowl", "_Band", "_Cap", "_Rim"))])  # nothing on them (yet)
        for o in L["objects"]:  # sunk deep enough: no part pokes out of the slime before the rise
            j = (o.get("mobile") or {}).get("joint")
            if j in joints and o.get("size"): self.assertLess(o["position"][1] + o["size"][1] - joints[j]["rise"], R["liquid"], o["name"])
        g = {tuple(p["grid"]): p for p in P}
        for (i, j), p in g.items():  # symmetric under a quarter turn and a mirror: same delay, same personality (bar its sway direction)
            for (a, b) in ((j, 4 - i), (i, 4 - j)):
                q = g[(a, b)]; self.assertEqual(p["delay"], q["delay"]); self.assertEqual({k: v for k, v in p["goof"].items() if k != "dir"}, {k: v for k, v in q["goof"].items() if k != "dir"})
        self.assertEqual(g[(2, 2)]["delay"], 0.0); self.assertLess(g[(2, 1)]["delay"], g[(2, 0)]["delay"])  # centre first, outer ring last
        self.assertEqual(by["Arena_Tile_33_Cap"]["material"], by["Arena_Tile_11_Cap"]["material"]); self.assertNotEqual(by["Arena_Tile_33_Cap"]["material"], by["Arena_Tile_32_Cap"]["material"])
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); from modules.assembly import goofy_pose, rust_grow
        self.assertEqual(R["style"], "goofy")
        sk = L["skeletons"]["Arena"]; par = {j["name"]: j.get("parent") for j in sk["joints"]}
        for p in P:  # Stage 112: round supports; green rust on its own bone (child of the tile's) creeping up once it has settled
            col = by[f"Arena_Tile_{p['grid'][0] + 1}{p['grid'][1] + 1}_Column"]; self.assertEqual(col["type"], "cylinder")
            ru = by[f"Arena_Tile_{p['grid'][0] + 1}{p['grid'][1] + 1}_Rust"]; self.assertEqual(ru["material"], "corrosion"); self.assertEqual(ru["mobile"]["joint"], p["rust"]["bone"])
            self.assertEqual(par[p["rust"]["bone"]], p["joint"]); self.assertLess(ru["position"][1], R["liquid"]); self.assertGreater(ru["position"][1] + ru["size"][1], R["liquid"] + 1.0)
            settle = 0.45 + p["goof"]["peek"] + 0.22 + R["rise_s"]
            self.assertEqual(rust_grow(p, settle, R["rise_s"]), 0.0); self.assertEqual(rust_grow(p, settle + p["rust"]["delay"] + p["rust"]["grow"] + 0.1, R["rise_s"]), 1.0)
        for p in (g[(2, 2)], g[(2, 1)], g[(1, 1)], g[(0, 2)]):
            ts = [i * 0.02 for i in range(500)]; Q = [goofy_pose(p, t_, R["rise_s"], R["liquid"]) for t_ in ts]
            self.assertAlmostEqual(p["center"][1] + Q[0][0], R["liquid"] - 1.0, places=3)  # starts under the slime
            peek = max(p["center"][1] + q[0] for q, t_ in zip(Q, ts) if t_ < 0.45 + p["goof"]["peek"])
            self.assertTrue(R["liquid"] + 0.6 < peek < R["liquid"] + 1.2)  # just its top peeks out ...
            self.assertGreater(max(abs(q[1]) for q in Q), 5.0)  # ... and looks around
            self.assertGreater(max(q[0] for q in Q), 1.0)  # pops up past its rest height
            self.assertGreater(max(q[3] for q in Q), 1.1); self.assertGreater(max(abs(q[2]) for q in Q), 1.5)  # squashes, sways
            self.assertEqual(Q[-1][:4], (0.0, 0.0, 0.0, 1.0)); self.assertTrue(Q[-1][4])  # settled, colliders live
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: v = f.read()
        self.assertIn("const goofy=(pd,tk)=>", v); self.assertIn("pd.delay!=null", v); self.assertIn("if(pd.rust)", v)
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")) as f: gd = f.read()
        self.assertIn("static func goofy_pose", gd); self.assertIn('pd.get("delay"', gd); self.assertIn('if pd.has("rust"):', gd)
        E = next(e for e in S["encounters"] if e["id"] == "Arena_Waves"); self.assertEqual(E["trigger"], "enter:Arena_Deck")
        sp = next(s for s in L["spawns"] if s["id"] == "enemy_arena")["position"]; self.assertTrue(any(abs(sp[0] - p["center"][0]) < 1 and abs(sp[2] - p["center"][2]) < 1 for p in P))
        N = _load("checks/navigation.json"); self.assertEqual({a["name"]: a["reachable_fraction"] for a in N["intended_areas"]}.get("Arena_Deck"), 1.0)


class GlassDome(unittest.TestCase):
    """Stage 126: a massive glass dome in the roof over the north half, soft yellow light coming through it."""
    @classmethod
    def setUpClass(cls):
        cls.L = _load("level.json"); cls.by = {o["name"]: o for o in cls.L["objects"]}

    def test_roof_has_a_round_hole_with_the_dome_over_it(self):
        D = _load("scene_spec.json")["arena"]["ceiling"]["dome"]; (dx, dz), R = D["at"], D["radius"]
        slab = self.by["Ceiling_Slab"]; self.assertEqual(slab["hole"], R); self.assertEqual([slab["position"][0], slab["position"][2]], [dx, dz])
        for k in "WENS": self.assertIn("Ceiling_Slab_" + k, self.by)  # the rest of the roof, edge to edge with the holed square
        g = self.by["Dome_Glass"]; self.assertEqual(g["type"], "dome_shell"); self.assertTrue(g["double_sided"])
        self.assertLess(self.L["materials"][g["material"]]["alpha"], 0.5)  # see-through
        self.assertGreater(self.by["Dome_Sky"]["size"][0], g["size"][0])  # the glowing sky sits behind the glass
        self.assertGreaterEqual(sum(1 for n in self.by if n.startswith("Dome_Rib_")), D["ribs"] * 6)
        for n, o in self.by.items():
            if n.startswith("Dome_") and not n.startswith("Dome_Shaft"): self.assertTrue(o.get("cutaway"), n)

    def test_light_is_soft_yellow_like_the_fans(self):
        M = self.L["materials"]
        for m in ("dome_sky", "sunbeam"):
            c = M[m]["color"]; self.assertTrue(c[0] >= c[1] > c[2], m)  # warm yellow (the sky golden toward the rim)
        self.assertLess(M["sunbeam"]["alpha"], 0.15)  # faint shafts
        E = {e["id"]: e for e in _load("effects.json")["effects"]}
        dl, fl = E["Dome_Light"], E["Fan_Lights"]; self.assertEqual(dl["type"], "point_light")
        c1, c2 = (e["quality"]["balanced"]["params"]["color"] for e in (dl, fl)); self.assertLess(max(abs(a - b) for a, b in zip(c1, c2)), 0.1)
        self.assertGreaterEqual(len(dl["emitters"]), 3)

    def test_sky_shows_through_clear_glass(self):
        """Stage 127: the glass is nearly clear and behind it is a sky (clouds, blue overhead, golden rim) mapped flat from
        below, kept under the background factory's roof so nothing dark covers it."""
        M = self.L["materials"]; g, sk = self.by["Dome_Glass"], self.by["Dome_Sky"]
        self.assertLessEqual(M[g["material"]]["alpha"], 0.12)
        self.assertEqual(M[sk["material"]]["type"], "sky_dome"); self.assertEqual(sk["uv"], "planar")
        roof = min(l["roof_y"] for l in _load("scene_spec.json")["background"]["layers"] if "roof_y" in l)
        self.assertLess(sk["position"][1] + sk["size"][1], roof); self.assertGreater(sk["position"][1] + sk["size"][1], g["position"][1] + g["size"][1] + 3)

    def test_light_shafts_never_show_where_they_start(self):
        """Stage 127: open shafts with an alpha ramp - faded out well below the glass and faded in at the floor."""
        M = self.L["materials"]; sh = [o for n, o in self.by.items() if n.startswith("Dome_Shaft_")]; self.assertTrue(sh)
        for o in sh: self.assertEqual(o["type"], "beam_cone")
        m = M[sh[0]["material"]]; self.assertEqual(m["type"], "beam_fade"); self.assertLess(m["fade_out"][1], 1.0); self.assertGreater(m["fade_in"], 0)
        import sys; sys.path.insert(0, os.path.join(ROOT, "pipeline")); import materials
        a = materials.maps(m)["alpha"]; self.assertEqual(a[0].max(), 0.0); self.assertLess(a[-1].max(), 0.1); self.assertGreater(a[a.shape[0] // 2].min(), 0.9)

    def test_ceiling_dressing_keeps_clear_of_the_dome(self):
        D = _load("scene_spec.json")["arena"]["ceiling"]["dome"]; (dx, dz), R = D["at"], D["radius"]
        for n, o in self.by.items():
            if n.startswith(("Ceil_Pod", "Ceil_Fan", "Ceil_Step", "Ceil_Red", "Ceil_Cable")) and o.get("size"):
                self.assertGreater(math.hypot(o["position"][0] - dx, o["position"][2] - dz), R, n)
            if n.startswith("Ceil_LampRail_") and "Hanger" not in n and abs(o["position"][2] - dz) < R:
                x0, x1 = o["position"][0] - o["size"][0] / 2, o["position"][0] + o["size"][0] / 2; ch = math.sqrt(R * R - (o["position"][2] - dz) ** 2)
                self.assertTrue(x1 < dx - ch or x0 > dx + ch, n)  # rails stop either side of it


if __name__ == "__main__":
    unittest.main()
