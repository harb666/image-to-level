"""Stage 176: the pod tubes' bores look bottomless - a lightless black core the pods wait inside and rise out of."""
import json, os, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class BottomlessBores(unittest.TestCase):
    def test_pods_hide_in_a_black_core(self):
        L = json.load(open(os.path.join(LV, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        tubes = [n[:-len("_Plinth")] for n in by if n.endswith("_Tube_Plinth") or (n.startswith("Pod_Tube_") and n.endswith("_Plinth"))]
        self.assertEqual(len(tubes), 6)
        for t in tubes:
            ab = by[t + "_Abyss"]; self.assertEqual(ab["material"], "void"); top = ab["position"][1] + ab["size"][1]
            g = by[t + "_Glass_01"]; self.assertGreater(top, g["position"][1])  # covers the first glass section's bottom face
            self.assertLess(top, by[t + "_Plinth"]["position"][1] + by[t + "_Plinth"]["size"][1])  # under the rim
            cap = by[t + "_Pod_Cap"]; self.assertLess(cap["position"][1] + cap["size"][1], top)  # the waiting pod is hidden inside it
            self.assertLess(ab["size"][0] / 2, by[t + "_Plinth"]["hole"])
        v = L["materials"]["void"]; self.assertEqual(v["color"], [0.0, 0.0, 0.0]); self.assertEqual(v["ao_mul"], 0.0)


if __name__ == "__main__":
    unittest.main()
