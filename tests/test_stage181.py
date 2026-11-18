"""Stage 181: cog towers instead of the X banners - meshing, turning gears; and the mobile slim drops dead UV data."""
import json, math, os, struct, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


class CogTowers(unittest.TestCase):
    def test_gears_mesh_and_turn_together(self):
        L = json.load(open(os.path.join(LV, "level.json"))); by = {o["name"]: o for o in L["objects"]}
        E = {e["id"]: e for e in json.load(open(os.path.join(LV, "effects.json")))["effects"]}; spd = E["Fan_Spin"]["speeds"]
        self.assertNotIn("Showcase_XBanner_a", by)
        for side in "ab":
            G = [by[f"Showcase_Cogs_{side}_Gear_{k}"] for k in (1, 2, 3)]
            for A, B in zip(G, G[1:]):
                rp = lambda g: g["teeth"] * 0.2 / 2
                d = math.hypot(B["position"][0] - A["position"][0], B["position"][1] - A["position"][1]); self.assertAlmostEqual(d, rp(A) + rp(B), places=2)  # pitch circles touch
                self.assertAlmostEqual(spd[B["name"]], -spd[A["name"]] * A["teeth"] / B["teeth"], places=2)  # opposite way, by the tooth ratio
                th = -math.atan2(B["position"][1] - A["position"][1], B["position"][0] - A["position"][0])  # contact direction (gear-local angles)
                for t in (0.0, 1.37, 5.0):  # a tooth of A at the contact <-> a gap of B there, at any moment
                    sa = (th - A["phase"] + math.radians(spd[A["name"]] * 6) * t) * A["teeth"] / (2 * math.pi)
                    sb = (th + math.pi - B["phase"] + math.radians(spd[B["name"]] * 6) * t) * B["teeth"] / (2 * math.pi)
                    self.assertAlmostEqual(((sa + sb - 0.5) + 0.5) % 1.0 - 0.5, 0.0, delta=0.01)  # (to a hundredth of a tooth: stored values are rounded)
            self.assertIn(f"Showcase_Cogs_{side}_Gearbox", by); self.assertIn(f"Showcase_Cogs_{side}_DrivePipe", by)

    def test_mobile_glb_has_no_dead_data(self):
        f = open(os.path.join(LV, "mobile", "level_mobile.glb"), "rb").read(); n = struct.unpack("<I", f[12:16])[0]; J = json.loads(f[20:20 + n])
        used = set()
        for m in J["meshes"]:
            for p in m["primitives"]: used |= set(p["attributes"].values()) | ({p["indices"]} if "indices" in p else set())
        for s in J.get("skins", []): used.add(s.get("inverseBindMatrices"))
        for A in J.get("animations", []):
            for s in A["samplers"]: used |= {s["input"], s["output"]}
        self.assertEqual([i for i in range(len(J["accessors"])) if i not in used], [])
        self.assertLess(len(f), 4000 * 1024)


if __name__ == "__main__":
    unittest.main()
