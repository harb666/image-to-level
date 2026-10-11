"""Stage 19: spinning fans with smooth blades (fan_rotor + "spin" effect), the wall_works / wall_slimed textures from
the user's fan reference, and wall dressing on the INNER face of the walls (it used to sit on the outside)."""
import json, math, os, re, unittest
import numpy as np
from _util import ROOT, PIPE, FULL, tmp_level, small_spec, write_spec


def _gen():
    import spec_to_level
    s = small_spec(); s["arena"]["size"] = [60, 60]; s["art_style"] = "alien_cartoon"
    s["arena"]["walls"] = {"height": 22, "thickness": 3, "dressing": "varied", "dress_y": 5}; s["arena"]["ceiling"] = {"style": "varied", "seed": 3}
    d = tmp_level(name="fans"); spec_to_level.run(write_spec(d, s), d, verbose=False); return d, json.load(open(os.path.join(d, "level.json")))


class Rotor(unittest.TestCase):
    def test_smooth_closed_centred(self):
        import shapes
        m = shapes.make({"type": "fan_rotor", "size": [6, 0.8, 6], "blades": 8})
        self.assertTrue(m.is_volume); self.assertLess(len(m.faces), 900)
        self.assertLess(abs(float(m.bounds.mean(0)[0])), 0.2); self.assertLess(abs(float(m.bounds.mean(0)[2])), 0.2)  # spins about its node origin
        self.assertIn("uv", m.metadata)  # own UVs -> vertices stay shared -> smooth shading


class Spin(unittest.TestCase):
    def test_every_rotor_spins_and_stays_its_own_node(self):
        _, L = _gen(); rot = [o for o in L["objects"] if o["type"] == "fan_rotor"]
        self.assertTrue(rot); (e,) = [e for e in L["effects"] if e["type"] == "spin"]
        self.assertEqual(sorted(e["targets"]), sorted(o["name"] for o in rot))
        for o in rot: self.assertIs(o["mobile"]["merge"], False); self.assertNotEqual(o["spin"], 0); self.assertIs(o["outline"], False)
        gd = open(os.path.join(PIPE, "godot_fx", "apply_effects.gd")).read(); self.assertIn("rotate_object_local", gd)
        self.assertIn("transform_animation", open(os.path.join(PIPE, "viewer.html")).read())

    def test_dressing_on_the_inner_face(self):
        from anchors import world_matrices
        _, L = _gen(); W, by = world_matrices(L)
        mods = [n for n in by if re.search(r"^OuterWall_\w+_M\d\d[A-Z]", n) and by[n]["type"] != "group"]
        self.assertTrue(mods)
        for n in mods:
            p = W[n][:3, 3]; self.assertLess(max(abs(p[0]), abs(p[2])), 30.2, f"{n} sits outside the wall at {p.round(1)}")


class Textures(unittest.TestCase):
    def test_wall_textures(self):
        import materials
        for k, emit in (("wall_works", 0.001), ("wall_slimed", 0.01)):
            d = materials.maps({"type": k, "color": [0.3, 0.25, 0.35], "res": 256, "toon": True, "emissive": [1, 1, 1]})
            self.assertEqual(d["alb"].shape, (256, 256, 3)); self.assertGreater(float(d["emit"].mean()), emit, k)
            self.assertGreater(float(np.std(d["h"])), 0.05, k)  # plates / seams / vents in the height field


if __name__ == "__main__":
    unittest.main()
