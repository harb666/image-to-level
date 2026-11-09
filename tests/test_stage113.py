"""Stage 113: the level previews show Construct Error's player character (the Grinch) instead of the blue capsule:
a preview copy made by pipeline/player_preview.py from the game's character glb (the game repo is only read)."""
import json, os, struct, unittest
from _util import ROOT

A = os.path.join(ROOT, "assets", "characters", "grinch_preview")


class PlayerCharacterPreview(unittest.TestCase):
    def test_preview_copy(self):
        b = open(A + ".glb", "rb").read(); n = struct.unpack("<I", b[12:16])[0]; J = json.loads(b[20:20 + n])
        M = json.load(open(A + ".json")); self.assertIn("CONSTRUCT-ERROR_V1", M["source"])
        names = {a["name"] for a in J["animations"]}; self.assertEqual(names, set(M["clips"].values()))  # only the clips the preview plays
        self.assertFalse(J.get("images")); self.assertEqual(len(J["skins"]), 1)  # no embedded images (data: URI texture instead), still skinned
        self.assertLess(len(b), 6 * 1024 * 1024); self.assertTrue(os.path.getsize(A + ".jpg") < 1024 * 1024)
        for k in ("idle", "walk", "run", "jump", "fall"): self.assertIn(k, M["clips"])

    def test_embedded_and_driven(self):
        with open(os.path.join(ROOT, "pipeline", "make_preview.py")) as f: mp = f.read()
        self.assertIn('glob["PLAYER"]', mp); self.assertIn('"PLAYERTEX"', mp)
        with open(os.path.join(ROOT, "pipeline", "viewer.html")) as f: v = f.read()
        self.assertIn("const playerAnim=(dt)=>", v); self.assertIn("playerAnim(dt);", v); self.assertIn("avatar.visible=false", v)
        p = os.path.join(ROOT, "dist", "assembly_ascent", "preview_mobile.html")
        if os.path.exists(p):
            with open(p) as f: self.assertIn("window.PLAYER=", f.read(400000000))


if __name__ == "__main__":
    unittest.main()
