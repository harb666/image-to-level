"""Stage 189 (user): the floating stepping platforms sink into the slime if a player stays on them too long, then rise
back - with steam, splashes, boiling slime and drips (viewer + apply_effects.gd, same maths as assembly.sink_*)."""
import json, os, sys, unittest
from _util import ROOT

sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "pipeline", "modules"))
import assembly as A

LV = os.path.join(ROOT, "levels", "assembly_ascent")


def _load(p):
    with open(p) as f: return json.load(f)


class SinkingPlatforms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = _load(os.path.join(LV, "level.json")); cls.F = {f["id"]: f for f in cls.L["floaters"]}; cls.P = cls.F["Pillars_FloatRig"]; cls.S = cls.P["sink"]

    def run_(self, on_until, T, dt=0.02):
        st, out = {"load": 0.0, "t0": None}, []
        for i in range(int(T / dt)):
            t = i * dt; A.sink_step(self.S, st, t < on_until, dt, t); out.append((t, dict(st)))
        return out

    def test_gives_way_only_after_hold(self):
        tr = self.run_(self.S["hold"] - 0.3, 6.0); self.assertTrue(all(s["t0"] is None for _, s in tr))  # stepped off in time: it holds
        self.assertEqual(tr[-1][1]["load"], 0.0)  # (and the load drains)
        tr = self.run_(99, 3.0); t0 = next(s["t0"] for _, s in tr if s["t0"] is not None); self.assertAlmostEqual(t0, self.S["hold"], delta=0.05)

    def test_full_cycle_and_back(self):
        S = self.S; cyc = S["sink"] + S["under"] + S["rise"]
        tr = self.run_(self.S["hold"] + 0.5, self.S["hold"] + cyc + 1.0); self.assertIsNone(tr[-1][1]["t0"])  # afloat again, ready for the next player
        d = [A.sink_profile(S, u)[0] for u in [k * 0.05 for k in range(int(cyc / 0.05) + 1)]]
        k1 = int(S["sink"] / 0.05); self.assertTrue(all(a <= b + 1e-9 for a, b in zip(d[:k1], d[1:k1 + 1])))  # sinks steadily ...
        self.assertLess(A.sink_profile(S, 0.3 * S["sink"])[0], 0.15)  # ... slowly at first
        self.assertEqual(A.sink_profile(S, S["sink"] + S["under"] / 2), (1.0, 0.0))  # under, thruster dead
        self.assertEqual(A.sink_profile(S, cyc + 0.01), (0.0, 1.0)); self.assertEqual(A.sink_profile(S, -1), (0.0, 1.0))
        for pd in self.P["pads"]:
            self.assertAlmostEqual(pd["center"][1] - pd["sink_depth"], S["liquid"] - 0.9, places=3)  # the deck ends 0.9 m under the slime
            self.assertLess(pd["center"][1] - S["jet_drop"], pd["center"][1])

    def test_only_the_stepping_platforms(self):
        self.assertNotIn("sink", self.F["Spinner_FloatRig"]); self.assertEqual(len(self.P["pads"]), 7)
        E = {e["id"]: e for e in _load(os.path.join(LV, "effects.json"))["effects"]}; self.assertIn("sink", E["Pillars_FloatRig_Bob"]["floater"])

    def test_runtimes(self):
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read()
        for k in ("const sinkProf=", "st.load>=SK.hold", "ring(pd,S.burst,1.0)", "steam(pd,26)"): self.assertIn(k, v)
        for k in ("static func sink_profile", "func _sink_fx", "func _player_on", "_player_on(st[\"on\"])"): self.assertIn(k, gd)


if __name__ == "__main__":
    unittest.main()
