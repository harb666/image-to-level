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
        self.assertEqual(by["Elevator_Shaft_Lip"]["material"], "structure_b")
        for n in ("Elevator_Shaft_OuterRing", "Elevator_Shaft_Emblem_1", "Elevator_Shaft_Emblem_2"): self.assertIn(n, by)
        strips = [o for o in L["objects"] if o["name"].startswith("Elevator_Shaft_Strip_")]
        self.assertTrue(strips and all(o["size"][1] < 2.5 for o in strips))
        vents = [n for n in by if re.search(r"_M\d\dVent$", n)]
        self.assertTrue(vents and all(n + "_Duct" in by and n + "_FrameLow" in by and n + "_Slat_3" in by for n in vents))
