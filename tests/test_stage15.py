"""Stage 15: indoor arenas and multi-part levels. arena.ceiling (roof slab with a shaft opening, girders, lamps, cutaway
tags, no sky / background / sun shadows), the elevator_arrival car (open between its posts, spawn on its floor,
level.json "entrances"), its own mobile nodes (movable in Godot) and the campaign link Skyforge -> Slime Arena."""
import json, math, os, subprocess, sys, unittest
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


def _indoor_spec():
    s = small_spec(); s["arena"]["walls"]["height"] = 16; s["arena"]["ceiling"] = {"opening": 4.0}
    s["platforms"][0]["size"] = [12, 12]; s["platforms"][0]["shape"] = "octagon"
    s["structures"] = [{"id": "Lift", "kind": "elevator_arrival", "on": "A", "radius": 3.6, "size": [7.2, 5, 7.2], "comes_from": "prev"}]
    s["spawns"] = [{"id": "player", "at": "Lift"}]; return s


def _gen(spec, name="indoor"):
    import spec_to_level
    d = tmp_level(name=name); spec_to_level.run(write_spec(d, spec), d, verbose=False); return d, json.load(open(os.path.join(d, "level.json")))


class Ceiling(unittest.TestCase):
    def test_roof_with_opening_and_no_sky(self):
        d, L = _gen(_indoor_spec()); by = {o["name"]: o for o in L["objects"]}
        slab = by["Ceiling_Slab"]; self.assertEqual(slab["hole"], 4.0); self.assertAlmostEqual(slab["position"][1], 16.5)
        self.assertTrue(slab["cutaway"] and slab["mobile"]["group"] == "Ceiling")
        for o in L["objects"]:  # girders keep clear of the shaft opening
            if o["name"].startswith("Ceiling_Beam"):
                off = abs(o["position"][0]) if "_NS_" in o["name"] else abs(o["position"][2]); self.assertGreater(off, 4.0, o["name"])
        self.assertEqual(L["environment"]["background"], []); self.assertEqual(L["environment"]["indoor"]["ceiling_y"], 16.5)
        ids = {e["id"] for e in L["effects"]}; self.assertNotIn("Sky_Drift", ids)

    def test_style_preset_adds_no_sky_layers_indoors(self):
        s = _indoor_spec(); s["art_style"] = "alien_cartoon"; s["background"] = {"layers": []}
        _, L = _gen(s, "styled"); self.assertEqual(L["environment"]["background"], [])


class Arrival(unittest.TestCase):
    def test_car_spawn_and_entrance(self):
        _, L = _gen(_indoor_spec()); by = {o["name"]: o for o in L["objects"]}
        (en,) = L["entrances"]; self.assertEqual((en["id"], en["type"], en["comes_from"], en["car"]), ("Lift", "elevator_arrival", "prev", "Lift_Car"))
        top = 4.0; self.assertEqual(en["rest_position"], [0.0, top, 0.0]); self.assertEqual(L["spawn"]["position"], [0.0, top + 0.25, 0.0])
        self.assertAlmostEqual(en["start_offset_y"], 16.5 + 1.0 + 0.3 - top, 2)  # starts just above the roof slab, inside the shaft
        self.assertLessEqual(top + en["start_offset_y"] + 4.8 + 1.35, en["shaft_top_y"])  # hidden in the shaft at its start height
        car = [o for o in L["objects"] if o.get("parent") == "Lift_Car"]
        self.assertTrue(car and all(o["mobile"]["group"] == "Lift_Car" for o in car))
        posts = [o for o in car if "_Post_" in o["name"]]; self.assertEqual(len(posts), 4)
        gap = 2 * math.pi * (3.6 - 0.3) / 4 - 0.5; self.assertGreater(gap, 3 * 1.0)  # walk-off openings between posts (m)
        self.assertTrue(all(by[n]["cutaway"] for n in by if n.startswith("Lift_Shaft_")))
        self.assertFalse(any(o.get("collision", True) and o["name"].startswith("Lift_Shaft") for o in L["objects"] if o["type"] != "group"))

    def test_spawn_at_unknown_arrival_is_an_error(self):
        from scene_spec import validate
        s = _indoor_spec(); s["spawns"] = [{"id": "player", "at": "Nope"}]
        self.assertTrue(any("elevator_arrival" in e for e in validate(s)[0]))

    @unittest.skipUnless(FULL, "QUICK=1")
    def test_mobile_keeps_the_car_movable(self):
        d, _ = _gen(_indoor_spec(), "indoorb")
        subprocess.run([sys.executable, os.path.join(PIPE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        M = json.load(open(os.path.join(d, "mobile", "mobile_manifest.json"))); C = json.load(open(os.path.join(d, "mobile", "collision.json")))
        car = [n for n in M["nodes"] if n.get("group") == "Lift_Car"]
        self.assertTrue(car and all(n["node"].startswith("Lift_Car__") for n in car))
        static = [s_ for n in M["nodes"] if n["kind"] == "static" for s_ in n["source_objects"]]
        self.assertFalse([s_ for s_ in static if s_.startswith(("Lift_Car", "Ceiling_"))], "car / ceiling parts leaked into the static cells")
        self.assertEqual([e["id"] for e in C["entrances"]], ["Lift"]); self.assertFalse(M["godot"]["directional_light"]["shadow_enabled"])
        gd = open(os.path.join(d, "mobile", "apply_mobile.gd")).read(); self.assertIn("func play_arrival", gd)
        self.assertFalse(json.load(open(os.path.join(d, "environment.json")))["sun"]["shadows"]["enabled"])


class Campaign(unittest.TestCase):
    def test_skyforge_leads_to_the_slime_arena(self):
        from scene_spec import validate
        sky = json.load(open(os.path.join(ROOT, "levels", "skyforge_arena", "level.json")))
        self.assertEqual(sky["exits"][0]["target"], "slime_arena"); self.assertEqual(sky["campaign"]["next"], "slime_arena")
        spec = json.load(open(os.path.join(ROOT, "levels", "slime_arena", "scene_spec.json"))); self.assertEqual(validate(spec)[0], [])
        self.assertEqual({k: spec["campaign"][k] for k in ("level", "part", "parts", "previous")}, {"level": 1, "part": 2, "parts": 3, "previous": "skyforge_arena"})
        self.assertFalse(any(s["kind"] == "tower" for s in spec["structures"]))
        self.assertEqual(next(s for s in spec["structures"] if s["kind"] == "elevator_arrival")["comes_from"], "skyforge_arena")

    def test_viewer_cuts_the_roof_away(self):
        js = open(os.path.join(PIPE, "viewer.html")).read(); self.assertIn("cutaway", js); self.assertIn("indoor", js)


if __name__ == "__main__":
    unittest.main()
