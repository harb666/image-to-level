"""Stage 190 (user): the conveyor ramps are industrial machines - a link belt, cleats under comb plates, drum sprockets,
drive motors - running faster than anyone can sprint up them, until the mini boss is defeated (then they spin down)."""
import json, math, os, sys, unittest
from _util import ROOT

LV = os.path.join(ROOT, "levels", "assembly_ascent")


def _load(p):
    with open(p) as f: return json.load(f)


class MechanicalBelts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = _load(os.path.join(LV, "level.json")); cls.by = {o["name"]: o for o in cls.L["objects"]}; cls.B = {b["id"]: b for b in cls.L["belts"]}
        sys.path.insert(0, os.path.join(ROOT, "pipeline")); import gameplay; cls.G = gameplay.load_gameplay(LV)

    def test_too_fast_to_run_up(self):
        sprint = float(self.G["movement"]["sprint_speed"])
        for b in self.B.values():
            push = abs(b["speed"]) * math.hypot(b["axis"][0], b["axis"][2]); self.assertGreater(push, sprint * 1.1)  # pushes back even a sprint
            self.assertLess(b["speed"], 0)

    def test_stops_when_the_mini_boss_is_defeated(self):
        for b in self.B.values(): self.assertEqual(b["stops_on"]["type"], "boss_defeated"); self.assertGreater(b["stop_time"], 0.5)
        v = open(os.path.join(ROOT, "pipeline", "viewer.html")).read(); gd = open(os.path.join(ROOT, "pipeline", "godot_fx", "apply_effects.gd")).read()
        for k in ("window.bossDefeated=", "K.b.speed*(K.k??1)*dt", "P+=B.speed*K.k*dt", 'id="bossb"'): self.assertIn(k, v)
        for k in ("func boss_defeated(", "func _update_belts(", 'float(b["speed"]) * float(br[4]["k"]) * delta', "uv1_offset = Vector3(0.0, fposmod(-float(st[\"p\"])"): self.assertIn(k, gd)

    def test_machine_parts(self):
        for n, b in self.B.items():
            for k in ("CombFoot", "CombHead", "SprocketFoot", "SprocketHead", "Motor", "Frame_1", "Frame_2"): self.assertIn(f"{n}_{k}", self.by)
            self.assertEqual(self.by[f"{n}_Frame_1"]["material"], "machine")  # steel channels, no hazard stripes
            self.assertEqual({r["node"] for r in b["rollers"]}, {f"{n}_SprocketFoot", f"{n}_SprocketHead"})
            for r in b["rollers"]: self.assertAlmostEqual(abs(r["sign"]), 1.0, places=3); self.assertNotIn("spin", self.by[r["node"]])  # turned by the belt (stops with it)
            # cleats: the bottom one vanishes and the top one appears under the comb plates (the wrap never shows)
            cl = sorted([o for k, o in self.by.items() if k.startswith(f"{n}_Chev_")], key=lambda o: -o["position"][1])
            u = b["axis"]; foot = [b["center"][i] - u[i] * b["length"] / 2 for i in range(3)]
            s_ = lambda o: sum((o["position"][i] - foot[i]) * u[i] for i in range(3))
            sb, st = min(s_(o) for o in cl), max(s_(o) for o in cl); comb = self.by[f"{n}_CombFoot"]["size"][2]
            self.assertGreater(sb - b["spacing"] - 0.1, 0.0); self.assertLess(sb + 0.1, comb)  # bottom: under the foot comb, before and after the shift
            self.assertGreater(st - 0.1, b["length"] - comb); self.assertLess(st + 0.1, b["length"])
            self.assertAlmostEqual(len(cl) - 1, (st - sb) / b["spacing"], places=2)
        M = self.L["materials"]["belt"]; b = self.B["Belt_A"]
        self.assertEqual(M["type"], "belt_links"); self.assertAlmostEqual(M["tile_m"], b["spacing"] * math.cos(math.radians(b["pitch"])), places=2)  # one link per cleat

    def test_budget(self):
        self.assertLess(os.path.getsize(os.path.join(LV, "mobile", "level_mobile.glb")) / 1024, 4000)


if __name__ == "__main__":
    unittest.main()
