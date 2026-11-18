"""Stage 168: the showcase's banner became a wall monitor showing a dissection scan of the vat specimen."""
import json, os, unittest
from PIL import Image
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class ScanMonitor(unittest.TestCase):
    def test_monitor_replaces_the_banner(self):
        L = json.load(open(os.path.join(LV, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        self.assertNotIn("Showcase_Banner", by); self.assertNotIn("Showcase_BannerRod", by)
        sc = by["Showcase_Scan"]; m = L["materials"][sc["material"]]
        self.assertEqual(m["type"], "image_decal"); self.assertTrue(m["image"].endswith("specimen_schematic.png"))
        im = Image.open(os.path.join(ROOT, m["image"])); self.assertAlmostEqual(im.size[0] / im.size[1], sc["size"][0] / sc["size"][1], delta=0.05)  # not stretched
        h = by["Showcase_ScanHousing"]; self.assertGreater(sc["position"][2], h["position"][2] + h["size"][2] / 2)  # the picture is on the housing's face
        for k in ("Top", "Low", "L", "R"): self.assertIn(f"Showcase_ScanBezel_{k}", by)
        E = {e["id"] for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}; self.assertIn("Screen_Pulse_specimen_scan", E)

    def test_scan_is_drawn_from_her_mesh(self):
        src = open(os.path.join(ROOT, "pipeline", "make_specimen_schematic.py")).read()
        self.assertIn("cyber_girl.glb", src); self.assertIn("JOINTS_0", src)  # the parts come from her skin weights, not a drawing
        im = Image.open(os.path.join(LV, "references", "specimen_schematic.png")).convert("RGB").resize((220, 100))
        px = list(im.getdata()); cyan = sum(1 for r, g, b in px if b > 150 and g > 120 and r < 140)
        self.assertGreater(cyan, 300)  # plenty of cyan wire on the dark grid


if __name__ == "__main__":
    unittest.main()
