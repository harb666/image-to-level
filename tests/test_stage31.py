"""Stage 31: nothing hangs from bare ceiling - claws ride trolleys on wall-to-wall I-beam runways (shared per line,
hung on rods), overhead pipe runs hang on rods, vertical outlet pipes are fed from the roof."""
import json, os, unittest
import numpy as np
from _util import tmp_level, small_spec, write_spec


def _gen():
    import spec_to_level
    s = small_spec(); s["arena"]["size"] = [40, 40]; s["arena"]["walls"] = {"height": 16, "thickness": 2}
    s["arena"]["ceiling"] = {"opening": 3.0}
    s["structures"] += [{"id": "Cl_A", "kind": "claw", "position": [10, 6], "length": 5},
                        {"id": "Cl_B", "kind": "claw", "position": [-10, 6], "length": 6},
                        {"id": "Cl_C", "kind": "claw", "position": [4, -12], "length": 5}]
    s["pipes"] = [{"id": "Run", "kind": "run", "points": [[-20, 12, -6], [10, 12, -6]], "radius": 0.5},
                  {"id": "Hang", "position": [5, 10, 8], "outlet": "vertical", "radius": 0.6, "length": 3}]
    d = tmp_level(name="crane"); spec_to_level.run(write_spec(d, s), d, verbose=False); return json.load(open(os.path.join(d, "level.json")))


class Cranes(unittest.TestCase):
    def test_claws_ride_rails(self):
        import sys
        L = _gen(); by = {o["name"]: o for o in L["objects"]}
        from anchors import world_matrices
        W, _ = world_matrices(L); cy = L["environment"]["indoor"]["ceiling_y"]
        rails = [o for o in L["objects"] if o["name"].startswith("CraneRail_") and o["type"] == "group"]
        self.assertEqual(len(rails), 2)  # Cl_A and Cl_B share the line z = 6
        for r in rails:
            b = by[r["name"] + "_Beam"]; self.assertEqual(b["type"], "ibeam"); self.assertGreater(b["size"][0], 39)  # wall to wall
            hs = [o for o in L["objects"] if o["name"].startswith(r["name"] + "_Hanger_")]
            self.assertTrue(hs and all(abs(W[o["name"]][1, 3] + o["size"][1] - cy) < 0.15 for o in hs))  # rods reach the roof
        for c in ("Cl_A", "Cl_B", "Cl_C"):
            ch, tr = by[c + "_Chain_1"], by[c + "_Trolley_Body"]
            self.assertAlmostEqual(W[c + "_Chain_1"][1, 3] + ch["size"][1], W[c + "_Trolley_Body"][1, 3] + 0.05, 3)  # chain into the trolley

    def test_pipes_hang_from_the_roof(self):
        L = _gen(); names = {o["name"] for o in L["objects"]}
        self.assertTrue(any(n.startswith("Run_Hanger_") for n in names))
        self.assertIn("Hang_Feed", names); self.assertIn("Hang_RoofPlate", names)


if __name__ == "__main__":
    unittest.main()


class LampRails(unittest.TestCase):
    def test_slime_arena_pods_hang_from_rails_mostly_in_the_hall(self):
        import re
        L = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "levels", "slime_arena", "level.json")))
        by = {o["name"]: o for o in L["objects"]}
        pods = [o for o in L["objects"] if re.search(r"Pod_\d+$", o["name"])]
        hall = [o for o in pods if not o["name"].startswith("Works")]; self.assertGreater(len(hall), 2 * (len(pods) - len(hall)))
        tops = [o["position"][1] for o in L["objects"] if re.search(r"Ceil_LampRail_\d+$", o["name"])]
        for p in pods:  # every cable ends at a lamp rail's underside
            c = by[p["name"] + "_Cable"]; self.assertTrue(any(abs(c["position"][1] + c["size"][1] - 0.05 - t) < 0.02 for t in tops), p["name"])


class Stage33(unittest.TestCase):
    def test_arm_claw_and_glass_pods(self):
        L = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "levels", "slime_arena", "level.json")))
        by = {o["name"]: o for o in L["objects"]}
        for part in ("_Shoulder_Disc", "_Elbow_Disc", "_Spike", "_Wrist", "_Finger_1_Tip", "_Hose_1_1", "_Link1_Strip_0"):
            self.assertIn("Arm_1" + part, by)
        self.assertEqual(by["Arm_1_Link1"]["type"], "frustum")
        self.assertIn("Claw_1_Finger_3_Tip", by); self.assertNotIn("Claw_1_Prong_1", by)
        pods = [o for o in L["objects"] if o["name"].endswith("Pod_01")]
        self.assertTrue(pods and all(o["material"] == "glass_clear" and o["name"] + "_Core" not in by for o in pods))  # clear, nothing green inside
