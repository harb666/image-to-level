"""Stage 17: the Toxic Works - annexes (extra roofed wings sharing a wall with the arena), the map's zone kit
(conveyor, robot_arm, lattice, conduit), the open exit door with a level_exit trigger, the background keeping clear of
every room, and the size settings (bevel_min, outline min_thickness, centred mobile cells)."""
import json, math, os, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


def _spec():
    s = small_spec(); s["arena"]["walls"] = {"height": 12, "thickness": 2, "openings": [{"side": "north", "at": 0, "width": 6, "height": 9}]}
    s["arena"]["ceiling"] = {}; s["art_style"] = "alien_cartoon"
    s["annexes"] = [{"id": "Wing", "center": [0, -40], "size": [30, 46], "walls": {"height": 12, "thickness": 2, "skip": ["south"]}, "ceiling": {}}]
    s["platforms"].append({"id": "W1", "center": [0, -30], "size": [8, 16], "top": 4})
    s["connections"].append({"id": "Ln_CW", "from": "C", "to": "W1"})
    s["structures"] = [{"id": "Belt", "kind": "conveyor", "from": [-2.5, -24], "to": [-2.5, -34], "y": 4},
                       {"id": "Arm", "kind": "robot_arm", "position": [6, 4, -30], "pedestal": 3},
                       {"id": "Shaft", "kind": "lattice", "position": [8, 1, -50], "size": [8, 10, 8]},
                       {"id": "Tube", "kind": "conduit", "from": [0, -24], "to": [0, -36], "y": 4, "width": 9},
                       {"id": "Out", "kind": "blast_door", "position": [0, 4, -62.7], "facing": "south", "size": [4, 5, 0.6], "open": True, "target": "next_part"}]
    s["background"] = {"layers": [{"id": "F", "type": "factory_interior", "part": "hull", "extent": [-80, -120, 80, 60],
                                   "clear": [[-17, -17, 17, 17], [-17, -65, 17, -15]], "roof_y": 30, "towers": 6, "decks": 6, "gantries": 4, "pillars": 6, "pipes": 4}]}
    return s


def _gen(spec, name="works"):
    import spec_to_level
    d = tmp_level(name=name); spec_to_level.run(write_spec(d, spec), d, verbose=False); return d, json.load(open(os.path.join(d, "level.json")))


class Annex(unittest.TestCase):
    def test_wing_has_floor_walls_roof_and_shares_the_doorway_wall(self):
        from scene_spec import validate
        self.assertEqual(validate(_spec())[0], [])
        _, L = _gen(_spec()); by = {o["name"]: o for o in L["objects"]}
        self.assertIn("Wing_HazardFluid", L["hazards"]); self.assertIn("Wing_Ceiling_Slab", by)
        self.assertFalse(any(n.startswith("Wing_Wall_South") for n in by))  # shared side: the arena's north wall
        self.assertTrue(any(n.startswith("Wing_Wall_North") for n in by))
        a, w = by["Ceiling_Slab"], by["Wing_Ceiling_Slab"]  # slabs meet edge to edge, no overlap (no z-fighting)
        self.assertAlmostEqual(a["position"][2] - a["size"][2] / 2, w["position"][2] + w["size"][2] / 2, 2)
        self.assertTrue(any(n.startswith("OuterWall_North_Lintel") or n.startswith("OuterWall_North_Op1") for n in by))

    def test_exit_door_trigger(self):
        _, L = _gen(_spec()); (ex,) = L["exits"]
        self.assertEqual((ex["id"], ex["target"], ex["type"]), ("Out_Exit", "next_part", "level_exit"))
        self.assertGreater(ex["center"][2], -62.7)  # in front of the door, on the room side
        self.assertIn("Out_Dark", {o["name"] for o in L["objects"]})


class Kit(unittest.TestCase):
    def test_zone_kinds(self):
        _, L = _gen(_spec()); by = {o["name"]: o for o in L["objects"]}
        self.assertTrue(any(n.startswith("Belt_Parcel") for n in by) or "Belt_Bed" in by)
        self.assertEqual(by["Belt_Bed"]["size"][1], 0.75)  # low cover
        self.assertIn("Arm_Pedestal", by); self.assertIn("Shaft_Ladder", by); self.assertTrue(any(n.startswith("Tube_Rib_") for n in by))
        for n in ("Arm_Link1", "Shaft_Post_1", "Tube_Rib_01"): self.assertIs(by[n]["collision"], False)

    def test_background_avoids_every_room(self):
        import backdrop
        s = _spec(); lay = s["background"]["layers"][0]
        for p in ("hull", "glass", "lights", "shell"):
            m = backdrop.factory_interior(dict(lay, part=p), backdrop.QUALITY["balanced"]); v = m.vertices
            for x0, z0, x1, z1 in lay["clear"]:
                inside = (v[:, 0] > x0 + 0.5) & (v[:, 0] < x1 - 0.5) & (v[:, 2] > z0 + 0.5) & (v[:, 2] < z1 - 0.5) & (v[:, 1] > -7) & (v[:, 1] < 29)
                self.assertFalse(inside.any(), f"{p}: geometry inside {x0, z0, x1, z1}")


class Size(unittest.TestCase):
    def test_bevel_min_and_thin_outlines(self):
        from build_level import _outlined
        OL = {"min_size": 0.25, "min_thickness": 0.45}
        self.assertFalse(_outlined({"type": "box", "size": [0.3, 6, 0.3], "material": "frame"}, OL))  # chain / mullion
        self.assertTrue(_outlined({"type": "box", "size": [2, 1, 2], "material": "frame"}, OL))
        src = open(os.path.join(PIPE, "build_level.py")).read(); self.assertIn("bevel_min", src)
        self.assertIn("centred on the level", open(os.path.join(PIPE, "export_mobile.py")).read())


if __name__ == "__main__":
    unittest.main()
