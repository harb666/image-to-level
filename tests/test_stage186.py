"""Stage 186 (user): the roof pods ride round the bend (one path per tube, a skinned rig with a bone per pod) instead
of vanishing into the drums under it; the transport tubes' drums get a plated industrial texture (no repeating red
stripes)."""
import json, math, os, struct, sys, unittest
import numpy as np
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "pipeline", "modules"))
import materials
from factory import pod_pose, POD_LEN_EXTRA

LV = os.path.join(ROOT, "levels", "assembly_ascent")


def _load(p):
    with open(p) as f: return json.load(f)


class PodPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = _load(os.path.join(LV, "level.json")); cls.by = {o["name"]: o for o in cls.L["objects"]}
        cls.E = {e["id"]: e for e in _load(os.path.join(LV, "effects.json"))["effects"]}; cls.D = cls.E["Pod_Export_Pods"]["pod_path"]

    def inside(self, box, lo, hi):
        p, s = box["position"], box["size"]; a = [p[0] - s[0] / 2, p[1], p[2] - s[2] / 2]; b = [p[0] + s[0] / 2, p[1] + s[1], p[2] + s[2] / 2]
        return all(a[i] - 1e-6 <= lo[i] and hi[i] <= b[i] + 1e-6 for i in range(3))

    def test_pose(self):
        P = dict(origin=[0.0, 0.0, 0.0], rise=10.0, radius=4.0, run=20.0)
        self.assertEqual(pod_pose(P, 5.0), ([0.0, 5.0, 0.0], 0.0))
        q, th = pod_pose(P, 10 + 4 * math.pi / 4); self.assertAlmostEqual(th, math.pi / 4); self.assertAlmostEqual(q[0], 4 - 4 * math.cos(math.pi / 4)); self.assertAlmostEqual(q[1], 10 + 4 * math.sin(math.pi / 4))
        q, th = pod_pose(P, 10 + 2 * math.pi + 3.0); self.assertAlmostEqual(q[0], 7.0); self.assertAlmostEqual(q[1], 14.0); self.assertAlmostEqual(th, math.pi / 2)
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read()
        self.assertIn("fx.category==='pod_path'", v); self.assertIn("static func pod_pose", gd); self.assertIn("_update_pod_paths()", gd)

    def test_pods_appear_and_vanish_out_of_sight(self):
        self.assertEqual(len(self.D["paths"]), 3); SK = self.L["skeletons"][self.D["skeleton"]]; joints = {j["name"]: j for j in SK["joints"]}
        for k, P in enumerate(self.D["paths"], 1):
            pods = sorted(P["pods"], key=lambda p: p["s0"]); S = P["spacing"]
            for a_, b_ in zip(pods, pods[1:]): self.assertAlmostEqual(b_["s0"] - a_["s0"], S, places=3)  # evenly spaced: each takes its neighbour's place on the wrap
            for pd in pods:  # rest pivot = the pose at s0; the pod's parts are bound to its bone
                self.assertTrue(np.allclose(joints[pd["joint"]]["pivot"], pod_pose(P, pd["s0"])[0], atol=1e-3))
            first = self.by[f"Pod_Export_Pod_{k}_1_Base"]; cap = self.by[f"Pod_Export_Pod_{k}_1_Cap"]; pl = cap["position"][1] + cap["size"][1] - first["position"][1]; r = cap["size"][0] / 2
            self.assertEqual(first.get("rotation", [0, 0, 0]), [0, 0, 0])  # (the first pod: upright at rest, in the riser)
            c0 = pod_pose(P, pods[0]["s0"])[0]; col = self.by[f"Pod_Export_{k}_Collar"]
            self.assertTrue(self.inside(col, [c0[0] - r, c0[1] - pl / 2, c0[2] - r], [c0[0] + r, c0[1] + pl / 2, c0[2] + r]))  # appears inside the roof collar
            cv, th = pod_pose(P, pods[-1]["s0"] + S); self.assertAlmostEqual(th, math.pi / 2)  # the last vanishes lying along the run ...
            self.assertTrue(self.inside(self.by["Pod_Export_Tower"], [cv[0] - pl / 2, cv[1] - r, cv[2] - r], [cv[0] + pl / 2, cv[1] + r, cv[2] + r]))  # ... inside the tower
            for pd in pods: self.assertEqual(self.by[f"Pod_Export_Pod_{k}_{pods.index(pd) + 1}_Fluid"]["mobile"]["joint"], pd["joint"])

    def test_rig_in_mobile_glb(self):
        b = open(os.path.join(LV, "mobile", "level_mobile.glb"), "rb").read(); n = struct.unpack("<I", b[12:16])[0]; G = json.loads(b[20:20 + n])
        sk = [s for s in G.get("skins", []) if s.get("name") == self.D["skeleton"]]; self.assertEqual(len(sk), 1)
        self.assertEqual(len(sk[0]["joints"]), sum(len(P["pods"]) for P in self.D["paths"]))
        self.assertTrue(any(nd.get("name", "").startswith(self.D["group"] + "__") and "skin" in nd for nd in G["nodes"]))


class PlatedDrums(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = _load(os.path.join(LV, "level.json")); cls.by = {o["name"]: o for o in cls.L["objects"]}

    def test_texture(self):
        m = self.L["materials"]["tube_drum"]; self.assertEqual(m["type"], "drum_plate"); d = materials.maps(dict(m, res=128))
        self.assertLess(float(d["emit"].mean()), 0.02)  # one small status lamp - not stripes of light
        rows = d["emit"].max(1); self.assertLess(float((rows > 0).mean()), 0.1)

    def test_transport_tubes_use_it(self):
        for n, o in self.by.items():
            if n.startswith(("Pod_Export_", "Pod_Tube_", "Reactor_Catwalk_")) and "Tube" in n or n.startswith("Pod_Export_"):
                self.assertNotEqual(o.get("material"), "tube_band", n)
        dr = [o for n, o in self.by.items() if o.get("material") == "tube_drum"]; self.assertGreater(len(dr), 20)
        for o in dr: self.assertEqual(o["type"], "pole"); self.assertEqual(o.get("uv_mode"), "band")
        for k in (1, 2, 3): self.assertTrue(self.by[f"Pod_Tube_{k}_DrumPlate_04"].get("open"))

    def test_budget(self):
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")) / 1024, 4000)


if __name__ == "__main__":
    unittest.main()
