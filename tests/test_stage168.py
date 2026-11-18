"""Stage 168: the showcase's banner became a wall monitor showing a dissection scan of the vat specimen."""
import json, os, unittest
from PIL import Image
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class ScanMonitor(unittest.TestCase):
    def test_monitor_replaces_the_banner(self):
        L = json.load(open(os.path.join(LV, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        self.assertNotIn("Showcase_Banner", by); self.assertNotIn("Showcase_BannerRod", by)
        l_, r_ = by["Showcase_Scan_L"], by["Showcase_Scan_R"]; m = L["materials"][l_["material"]]  # Stage 178: two panels, halves stacked in one atlas
        self.assertEqual(m["type"], "screen_atlas"); self.assertEqual((l_["uv_region"], r_["uv_region"]), ("l", "r"))
        self.assertAlmostEqual(r_["position"][0] - l_["position"][0], l_["size"][0], places=3)  # side by side, no gap
        for half, part in (("l", "_L"), ("r", "_R")):
            im = Image.open(os.path.join(ROOT, f"levels/assembly_ascent/references/specimen_schematic{part}.png")); self.assertAlmostEqual(im.size[0] / im.size[1], l_["size"][0] / l_["size"][1], delta=0.05)
        h = by["Showcase_ScanHousing"]; self.assertGreater(l_["position"][2], h["position"][2] + h["size"][2] / 2)
        for k in ("Top", "Low", "L", "R"): self.assertIn(f"Showcase_ScanBezel_{k}", by)
        E = {e["id"] for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}; self.assertIn("Screen_Pulse_specimen_scan", E)
        self.assertEqual(L["mobile"]["hd_textures"]["specimen_scan"][0], 768)  # kept sharper than the 512 cap in the mobile export

    def test_scan_is_drawn_from_her_mesh(self):
        src = open(os.path.join(ROOT, "pipeline", "make_specimen_schematic.py")).read()
        self.assertIn("cyber_girl.glb", src); self.assertIn("JOINTS_0", src)  # the parts come from her skin weights, not a drawing
        im = Image.open(os.path.join(LV, "references", "specimen_schematic.png")).convert("RGB").resize((220, 100))
        px = list(im.getdata()); cyan = sum(1 for r, g, b in px if b > 150 and g > 120 and r < 140)
        self.assertGreater(cyan, 300)  # plenty of cyan wire on the dark grid


if __name__ == "__main__":
    unittest.main()
