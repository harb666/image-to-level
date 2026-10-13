"""Stage 30: drains / spillways that leave a wall get a real mouth (housing in the wall's texture, dark tunnel back),
and wall dressing (TVs, machines, ...) never hangs in front of a pour."""
import json, os, re, unittest
import numpy as np
from _util import tmp_level, small_spec, write_spec


def _gen():
    import spec_to_level
    s = small_spec(); s["art_style"] = "alien_cartoon"; s["arena"]["size"] = [80, 80]
    s["arena"]["walls"] = {"height": 22, "thickness": 3, "dressing": "varied", "dress_y": 5}
    s["pipes"] = [{"id": "Sp", "position": [-40, 12, 0], "yaw": 90, "outlet": "spillway", "length": 6, "width": 5},
                  {"id": "Dr", "position": [0, 10, -41.5], "yaw": 0, "outlet": "drain", "radius": 1.0, "length": 10}]
    d = tmp_level(name="mouth"); spec_to_level.run(write_spec(d, s), d, verbose=False); return json.load(open(os.path.join(d, "level.json")))


class Mouths(unittest.TestCase):
    def test_mouths_and_clear_walls(self):
        import sys
        L = _gen(); by = {o["name"]: o for o in L["objects"]}
        for n in ("Sp", "Dr"):
            self.assertIn(n + "_Mouth_Lintel", by); self.assertEqual(by[n + "_Mouth_Dark"]["uv_region"], "void")
            self.assertTrue(by[n + "_Mouth_Jamb_0"]["material"].startswith("wall"))  # the wall's own texture
        self.assertAlmostEqual(by["Dr_Mouth"]["position"][2], -40.0, 2)  # on the wall face although the channel starts inside the wall
        from anchors import world_matrices
        W, _ = world_matrices(L)
        falls = [W[n][:3, 3] for n in ("Sp_Fall", "Dr_Fall")]
        for o in L["objects"]:
            if re.search(r"_M\d\d(Monitor|Machine|Fan|Vent|Emblem|Door)", o["name"]) and o["type"] != "group":
                q = W[o["name"]][:3, 3]
                for P in falls: self.assertFalse(np.hypot(q[0] - P[0], q[2] - P[2]) < 3.0 and q[1] < P[1] + 4, o["name"])


if __name__ == "__main__":
    unittest.main()
