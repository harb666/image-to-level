"""Stage 170: the jet screen (floating monitor) flies a collision-free show - planned against the finished level."""
import json, os, sys, types, unittest
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "pipeline", "modules"))
import assembly as A

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class JetClearance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        L = json.load(open(os.path.join(LV, "level.json"))); cls.L = L
        E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}
        cl = [dict(id=k[:-4], group=e["line"]["move"][0]) for k, e in E.items() if k.endswith("_Run") and e.get("category") == "assembly"]
        cls.ctx = types.SimpleNamespace(objects=L["objects"], hazards=list(L.get("hazards", [])), risers=L.get("risers", []),
                                        lifts=L.get("lifts", []), sweepers=L.get("sweepers", []), saws=L.get("saws", []), claw_lines=cl, launches=[])

    def test_whole_show_is_clear(self):
        for J in self.L["jets"]:
            J = dict(J, _plan=dict(half=[4.95, 3.0]))  # (the screen's 9 m x 6 m size, as jet_screen builds it)
            GR = A._obstacle_grid(self.ctx, J["id"]); c = A.jet_collisions(J, GR)
            self.assertEqual(c, {"home": 0, "fly": 0, "wait": 0, "press": 0, "back": 0}, c)
            self.assertEqual(J["clearance"], c)
            self.assertIn("back1", J); self.assertIn("back2", J)  # the return is planned too (not the old high arc through the claw lane)

    def test_button_reachable_from_the_deck(self):
        for J in self.L["jets"]:
            tm = next(t for t in self.L["terminals"] if t["id"] == J["button"]); tr = J["trigger"]
            self.assertTrue(tr["min"][0] < tm["button"][0] < tr["max"][0] and tr["min"][1] < tm["button"][2] < tr["max"][1])

    def test_runtimes_use_the_planned_return(self):
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read()
        self.assertIn("J.back1||", v); self.assertIn('J.get("back1"', gd)


if __name__ == "__main__":
    unittest.main()
