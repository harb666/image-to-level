"""Stage 18: immersive, non-repeating dressing. "varied" ceilings (irregular beams / trusses, stepped sections, ducts
on hangers, fans, caged lamp pods with headroom, sagging cables, red light pairs - no grid) and "varied" walls
(random-width slots, never the same module twice in a row), slime-tank windows, reactor columns, rock faces."""
import json, math, os, re, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


def _spec():
    s = small_spec(); s["arena"]["size"] = [60, 60]; s["art_style"] = "alien_cartoon"
    s["arena"]["walls"] = {"height": 22, "thickness": 3, "dressing": "varied", "dress_y": 5,
                           "openings": [{"side": "east", "at": 0, "width": 10, "sill": 10, "height": 18, "fill": "slime"}]}
    s["arena"]["ceiling"] = {"style": "varied", "opening": 3.0, "seed": 4}
    s["structures"] = [{"id": "Col", "kind": "column", "position": [20, 20], "radius": 2.0},
                       {"id": "Rock", "kind": "rock_face", "from": [-27, -20], "to": [-27, 20], "height": 18, "depth": 5}]
    return s


def _gen(spec, name="dress"):
    import spec_to_level
    d = tmp_level(name=name); spec_to_level.run(write_spec(d, spec), d, verbose=False); return d, json.load(open(os.path.join(d, "level.json")))


class Ceiling(unittest.TestCase):
    def test_no_grid_and_pods_keep_headroom(self):
        _, L = _gen(_spec()); objs = L["objects"]; names = [o["name"] for o in objs]
        self.assertFalse(any("Ceiling_Lamp_" in n or "Ceiling_Beam_NS" in n for n in names))  # the old grid is gone
        beams = sorted({round(o["position"][2], 1) for o in objs if re.match(r"Ceil_Beam_\d+_1(_T)?$", o["name"])})
        gaps = np.diff(beams); self.assertGreater(len(gaps), 1); self.assertGreater(float(gaps.max() - gaps.min()), 1.0)  # irregular spacing
        for k in ("Ceil_Step_", "Ceil_Duct_", "Ceil_Fan_", "Ceil_Pod_", "Ceil_Red_"): self.assertTrue(any(n.startswith(k) for n in names), k)
        top = max(w["y"] for w in L["walkable"])
        for o in objs:
            if re.match(r"Ceil_Pod_\d+$", o["name"]): self.assertGreater(o["position"][1], L["environment"]["indoor"]["ceiling_y"] - 14)
        ducts = [o for o in objs if re.match(r"Ceil_Duct_\d+$", o["name"])]
        self.assertTrue(all(any(n.startswith(d["name"] + "_Hanger") for n in names) for d in ducts))  # hung, not floating
        self.assertTrue(all(o.get("cutaway") and o.get("collision") is False for o in objs if o["name"].startswith("Ceil_")))


class Walls(unittest.TestCase):
    def test_modules_never_repeat_back_to_back(self):
        _, L = _gen(_spec()); names = [o["name"] for o in L["objects"]]
        for wall in {re.sub(r"_M\d\d.*", "", n) for n in names if re.search(r"_M\d\d", n)}:
            seq = []
            for n in names:
                m = re.match(re.escape(wall) + r"_M(\d\d)([A-Z][a-z]+)", n)
                if m and (not seq or seq[-1][0] != m.group(1)): seq.append((m.group(1), m.group(2)))
            kinds = [k for _, k in seq]; self.assertGreater(len(set(kinds)), 1, wall)
            self.assertTrue(all(a != b for a, b in zip(kinds, kinds[1:])), (wall, kinds))
        self.assertFalse(any("_Pilaster_" in n for n in names if n.startswith("OuterWall")))

    def test_slime_window_column_rock(self):
        _, L = _gen(_spec()); by = {o["name"]: o for o in L["objects"]}
        g = by["OuterWall_East_Op1_Slime"]; self.assertEqual(g["material"], "hazard"); self.assertTrue(g["collision"])
        self.assertTrue(any(n.startswith("Col_Glass") for n in by)); self.assertIn("Col_Capital", by)
        self.assertTrue(any(n.startswith("Rock_Slab") for n in by))
        self.assertFalse(set(L["hazards"]) & {n for n in by if "_Glass" in n or "_Slime" in n})



if __name__ == "__main__":
    unittest.main()
