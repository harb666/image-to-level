"""Stage 174: ceiling ducts never run through a rail (crane runway, lamp rail) or a ceiling beam hanging into them."""
import json, os, re, sys, unittest
import numpy as np
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from anchors import world_matrices


class DuctsClearRails(unittest.TestCase):
    def test_no_duct_through_a_rail(self):
        L = json.load(open(os.path.join(ROOT, "levels", "assembly_ascent", "level.json"))); Wm, _ = world_matrices({"objects": L["objects"]})
        def bb(o):
            w, h, d = o["size"]; C = np.array([[x, y, z, 1] for x in (-w / 2, w / 2) for y in (0, h) for z in (-d / 2, d / 2)]) @ Wm[o["name"]].T
            return C[:, :3].min(0), C[:, :3].max(0)
        objs = [o for o in L["objects"] if o.get("size") and o["type"] != "group"]
        rails = [o for o in objs if re.search(r"(CraneRail_\d+_(Beam|Stripe)|Ceil_LampRail_\d+[a-z]?|Ceil_Beam_\d+_\d+(_[A-Z])?)$", o["name"])]
        ducts = [o for o in objs if re.search(r"Ceil_Duct_\d+[a-z]?$", o["name"])]
        self.assertGreaterEqual(len(ducts), 2)
        for d in ducts:
            a, b = bb(d)
            for r in rails:
                p, q = bb(r); self.assertFalse((np.minimum(b, q) - np.maximum(a, p) > 0.01).all(), (d["name"], r["name"]))


if __name__ == "__main__":
    unittest.main()
