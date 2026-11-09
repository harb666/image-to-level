"""Stage 113: a light preview copy of a Construct Error player character, for the level previews (viewer.html shows it
instead of the blue capsule). Reads the game's character GLB (e.g. CONSTRUCT-ERROR_V1 assets/characters/grinch/grinch.glb,
read-only - the game repo is never modified) and writes:

  <out>.glb   the same skinned mesh and skeleton, only the animation clips the preview uses, no images / textures
              (sandboxed preview pages block GLTFLoader's blob: texture URLs), no tangents; plain PBR factors
  <out>.jpg   the base-colour texture, resized (embedded by make_preview.py as a data: URI and applied by viewer.html)
  <out>.json  provenance + which clip plays for idle / walk / run / jump / fall

  python3 pipeline/player_preview.py <character.glb> <out_prefix> [--size 1024] [--name grinch]
"""
import io, json, struct, sys
import numpy as np
from PIL import Image

CLIPS = {"idle": "Idle 9", "walk": "Walking", "run": "Running", "sprint": "RunFast", "jump": "Regular Jump", "fall": "Fall1"}


def _read(path):
    b = open(path, "rb").read(); n = struct.unpack("<I", b[12:16])[0]; J = json.loads(b[20:20 + n]); o = 20 + n
    bl = struct.unpack("<I", b[o:o + 4])[0]; return J, b[o + 8:o + 8 + bl]


def reduce(src, out, size=1024, name="grinch", clips=CLIPS):
    J, BIN = _read(src); keep_anims = set(clips.values())
    mat = J["materials"][0]; pbr = mat.setdefault("pbrMetallicRoughness", {})
    base_img = J["images"][J["textures"][pbr["baseColorTexture"]["index"]]["source"]]
    v = J["bufferViews"][base_img["bufferView"]]; im = Image.open(io.BytesIO(BIN[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]])).convert("RGB")
    im.resize((size, size), Image.LANCZOS).save(out + ".jpg", quality=86)
    for m in J["materials"]:  # plain factors: the base colour map is applied by the viewer
        p = m.setdefault("pbrMetallicRoughness", {}); p.pop("baseColorTexture", None); p.pop("metallicRoughnessTexture", None)
        m.pop("normalTexture", None); m.pop("occlusionTexture", None); m.pop("emissiveTexture", None); p["metallicFactor"] = 0.0; p["roughnessFactor"] = 0.8
    for k in ("images", "textures", "samplers"): J.pop(k, None)
    for me in J["meshes"]:
        for pr in me["primitives"]: pr["attributes"].pop("TANGENT", None)
    J["animations"] = [a for a in J.get("animations", []) if a["name"] in keep_anims]
    used = set()  # accessors still referenced
    for me in J["meshes"]:
        for pr in me["primitives"]:
            used |= set(pr["attributes"].values())
            if "indices" in pr: used.add(pr["indices"])
    for sk in J.get("skins", []):
        if "inverseBindMatrices" in sk: used.add(sk["inverseBindMatrices"])
    for a in J["animations"]:
        for s in a["samplers"]: used |= {s["input"], s["output"]}
    amap = {}; acc = []; bvmap = {}; bvs = []; blob = bytearray()
    for i in sorted(used):
        a = dict(J["accessors"][i]); bi = a.get("bufferView")
        if bi is not None and bi not in bvmap:
            v = J["bufferViews"][bi]; o = v.get("byteOffset", 0); data = BIN[o:o + v["byteLength"]]
            while len(blob) % 4: blob.append(0)
            nv = {k: v[k] for k in v if k not in ("byteOffset", "buffer")}; nv.update(buffer=0, byteOffset=len(blob)); blob += data
            bvmap[bi] = len(bvs); bvs.append(nv)
        if bi is not None: a["bufferView"] = bvmap[bi]
        amap[i] = len(acc); acc.append(a)
    for me in J["meshes"]:
        for pr in me["primitives"]:
            pr["attributes"] = {k: amap[v] for k, v in pr["attributes"].items()}
            if "indices" in pr: pr["indices"] = amap[pr["indices"]]
            pr.pop("targets", None)
    for sk in J.get("skins", []):
        if "inverseBindMatrices" in sk: sk["inverseBindMatrices"] = amap[sk["inverseBindMatrices"]]
    for a in J["animations"]:
        for s in a["samplers"]: s["input"], s["output"] = amap[s["input"]], amap[s["output"]]
    while len(blob) % 4: blob.append(0)
    J["accessors"], J["bufferViews"], J["buffers"] = acc, bvs, [dict(byteLength=len(blob))]
    js = json.dumps(J, separators=(",", ":")).encode(); js += b" " * (-len(js) % 4)
    glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob)) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
    open(out + ".glb", "wb").write(glb)
    meta = dict(name=name, source=src, clips=clips, texture=out.split("/")[-1] + ".jpg", height_m=1.7,
                note="preview copy (Stage 113): skinned mesh + skeleton unchanged, clips filtered, base colour resized; the game uses the original")
    json.dump(meta, open(out + ".json", "w"), indent=1)
    return dict(glb_kb=len(glb) // 1024, jpg_kb=len(open(out + ".jpg", "rb").read()) // 1024, clips=[a["name"] for a in J["animations"]])


if __name__ == "__main__":
    a = sys.argv[1:]; size = int(a[a.index("--size") + 1]) if "--size" in a else 1024; name = a[a.index("--name") + 1] if "--name" in a else "grinch"
    print(json.dumps(reduce(a[0], a[1], size, name)))
