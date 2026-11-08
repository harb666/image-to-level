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
        self.assertGreater(sw["ball_y"] + sw["ball_r"], jump + 0.3)  # a ball does not
        self.assertTrue(0 < sw["rpm"] <= 8)
        T = next(t_ for t_ in L["terminals"] if t_["id"] == "Spinner_Terminal"); self.assertEqual(T["activates"], ["Yard_Laser"])
        pad = by["Spinner_Pad_2_Deck"]; self.assertLess(math.hypot(T["center"][0] - 17.7, T["center"][2] - 27.3), 3.0)  # on the far (north-east) pad
        N = _load("checks/navigation.json"); cut = {o for c in N["component_list"] if not c.get("reachable") for o in c.get("objects", [])}
        self.assertEqual({a["name"]: a["reachable_fraction"] for a in N["intended_areas"]}["Spinner_Deck"], 1.0)
        for n in ("Spinner_Deck_Floor", "Spinner_Ramp_Deck", "Spinner_Pad_1_Deck", "Spinner_Pad_2_Deck", "Spinner_Pad_3_Deck", "Spinner_Pad_4_Deck"): self.assertIn(n, by); self.assertNotIn(n, cut, n)
        self.assertEqual(pad["type"], "cylinder")
        E = {e["type"] for e in _load("effects.json")["effects"]}; self.assertIn("sweeper", E)
        self.assertEqual(len(_load("mobile/collision.json")["sweepers"]), 1)
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: self.assertIn("fx.category==='sweeper'", f.read())
        with open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")) as f: self.assertIn("func _sweeper", f.read())


if __name__ == "__main__":
    unittest.main()
