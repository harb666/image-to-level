"""Stage 28: corroded band where the toxic liquid meets walls - one "band" object (material "corrosion", a small
cut-out texture), strips facing out of the solids at the liquid line, not between pressed-together parts."""
import json, os, unittest
import numpy as np
from _util import tmp_level, small_spec, write_spec


def _gen(corr=True):
    import spec_to_level
    s = small_spec(); s["art_style"] = "alien_cartoon"
    if corr: s["corrosion"] = {"height": 1.0}
    d = tmp_level(name="corr"); spec_to_level.run(write_spec(d, s), d, verbose=False); return json.load(open(os.path.join(d, "level.json")))


class Corrosion(unittest.TestCase):
    def test_band_object(self):
        L = _gen(); b = [o for o in L["objects"] if o["type"] == "band"]
        self.assertEqual(len(b), 1); b = b[0]
        self.assertEqual(b["material"], "corrosion"); self.assertFalse(b["collision"]); self.assertEqual(b["mobile"]["group"], "Corrosion")
        self.assertTrue(b["segments"]); self.assertEqual(L["materials"]["corrosion"]["cutout"], 0.5)
        for s in b["segments"]: self.assertLess(s["y0"], 1.0); self.assertGreater(s["y1"], 1.0)
        self.assertFalse([o for o in _gen(False)["objects"] if o["type"] == "band"])  # opt-in

    def test_strips_face_out_of_their_solid(self):
        import shapes
        L = _gen(); b = next(o for o in L["objects"] if o["type"] == "band"); m = shapes.make(b)
        c = m.triangles.mean(1); near = np.max(np.abs(c[:, [0, 2]]), 1) < 4.5  # strips round platform A (8 x 8 at the origin)
        self.assertTrue(near.any())
        out = np.einsum("ij,ij->i", m.face_normals[near][:, [0, 2]], c[near][:, [0, 2]])
        self.assertTrue((out > 0).all())  # normals point away from the platform centre
        self.assertIn("uv", m.metadata); self.assertEqual(len(m.metadata["uv"]), len(m.vertices))

    def test_texture_is_cutout(self):
        import materials, architecture
        d = materials.maps(dict(architecture.CORROSION, res=64)); a = d["alpha"]
        self.assertLess(a[:8].mean(), 0.2); self.assertGreater(a[-8:].mean(), 0.9)  # bare at the top, solid at the liquid
        mat, _ = materials.make_material("corrosion", architecture.CORROSION); self.assertEqual(mat.alphaMode, "MASK")


if __name__ == "__main__":
    unittest.main()
