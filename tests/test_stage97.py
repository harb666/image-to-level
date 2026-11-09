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
        self.assertAlmostEqual(c["travel"], 5.4 - 0.9, places=3)  # the spike tips (not the head) reach the pad
        self.assertGreaterEqual(sum(1 for n in self.by if n.startswith("Spike_Press_Spike_")), 4)
        G = {g["id"]: g for g in self.L["gates"]}
        self.assertEqual(G["Yard_Laser"]["opens_on"], {"type": "terminal", "terminal": "Spinner_Terminal"})  # Stage 98: unlocked from the spinner deck
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
                self.assertLess(inner, 11.15 * math.cos(math.pi / 8)); self.assertGreater(outer, 18.0 - 4.0 * math.cos(math.pi / 8))
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
        T = next(t_ for t_ in L["terminals"] if t_["id"] == "Spinner_Terminal"); self.assertEqual(T["activates"], ["Yard_Laser"])
        pad = by["Spinner_Pad_2_Deck"]; self.assertLess(math.hypot(T["center"][0] - 17.7, T["center"][2] - 27.3), 3.0)  # on the far (north-east) pad
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


if __name__ == "__main__":
    unittest.main()
