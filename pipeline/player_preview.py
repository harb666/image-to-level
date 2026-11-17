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



def slim(path, out, keep=0.4, tex=None, tex_size=768):
    """Stage 166: a lighter preview avatar - the skinned mesh simplified to ~keep of its faces (pipeline/specimen.py
    decimate_part: per-corner UVs from the closest original face, skin weights from the closest original vertex), the
    skeleton, skin and clips untouched; optionally the base-colour jpg resized. The preview page embeds it (it was 5.4 MB
    of base64 - a third of the page)."""
    import specimen as S_
    J, BIN = _read(path); pr = J["meshes"][0]["primitives"][0]; A = pr["attributes"]
    def get(i):
        a = J["accessors"][i]; v = J["bufferViews"][a["bufferView"]]; o = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a["componentType"]]; n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        return np.frombuffer(BIN[o:o + a["count"] * n * np.dtype(dt).itemsize], dt).reshape(a["count"], n) if n > 1 else np.frombuffer(BIN[o:o + a["count"] * np.dtype(dt).itemsize], dt)
    P = get(A["POSITION"]).astype(float); UV = get(A["TEXCOORD_0"]).astype(float); Jt = get(A["JOINTS_0"]); W = get(A["WEIGHTS_0"]); F = get(pr["indices"]).reshape(-1, 3).astype(np.int64)
    wn = J["accessors"][A["WEIGHTS_0"]].get("normalized", False); Wf = W.astype(float) / (255.0 if W.dtype == np.uint8 else 65535.0 if W.dtype == np.uint16 else 1.0)
    V, Fn, UVc, src = S_.decimate_part(P, UV, F, keep)
    N = S_.smooth_normals(V, Fn); vV, vN, vUV, vJ, vW, vF = S_.unweld_uv(V, Fn, UVc, N, (Jt[src].astype(int), Wf[src]))
    vW = np.asarray(vW, float); vW = vW / np.maximum(vW.sum(1, keepdims=True), 1e-9)
    # rebuild: drop the old mesh views, append the new arrays (positions / normals / uv float, joints u8|u16, weights u8 normalized, u32 indices)
    keep_acc = [i for i in range(len(J["accessors"])) if i not in set(A.values()) | {pr["indices"]}]
    blob = bytearray(); bvs = []; accs = []; amap = {}
    def put(arr, ctype, typ, normalized=False, target=None, minmax=False):
        while len(blob) % 4: blob.append(0)
        b = np.ascontiguousarray(arr).tobytes(); v = dict(buffer=0, byteOffset=len(blob), byteLength=len(b)); blob.extend(b)
        if target: v["target"] = target
        bvs.append(v); a = dict(bufferView=len(bvs) - 1, componentType=ctype, count=int(len(arr)), type=typ)
        if normalized: a["normalized"] = True
        if minmax: a["min"] = [float(x) for x in arr.min(0)]; a["max"] = [float(x) for x in arr.max(0)]
        accs.append(a); return len(accs) - 1
    for i in keep_acc:  # skeleton / animation data, byte-for-byte
        a = dict(J["accessors"][i]); v = J["bufferViews"][a["bufferView"]]; o = v.get("byteOffset", 0)
        while len(blob) % 4: blob.append(0)
        nv = {k: v[k] for k in v if k not in ("byteOffset", "buffer")}; nv.update(buffer=0, byteOffset=len(blob)); blob.extend(BIN[o:o + v["byteLength"]]); bvs.append(nv)
        a["bufferView"] = len(bvs) - 1; accs.append(a); amap[i] = len(accs) - 1
    jt = np.uint8 if int(np.max(vJ)) < 256 else np.uint16
    na = dict(POSITION=put(np.asarray(vV, np.float32), 5126, "VEC3", target=34962, minmax=True), NORMAL=put(np.asarray(vN, np.float32), 5126, "VEC3", target=34962),
              TEXCOORD_0=put(np.asarray(vUV, np.float32), 5126, "VEC2", target=34962), JOINTS_0=put(np.asarray(vJ, jt), 5121 if jt == np.uint8 else 5123, "VEC4", target=34962),
              WEIGHTS_0=put(np.clip(np.round(vW * 255), 0, 255).astype(np.uint8), 5121, "VEC4", normalized=True, target=34962))
    ia = put(np.asarray(vF, np.uint32).ravel(), 5125, "SCALAR", target=34963)
    pr["attributes"] = na; pr["indices"] = ia
    for sk in J.get("skins", []):
        if "inverseBindMatrices" in sk: sk["inverseBindMatrices"] = amap[sk["inverseBindMatrices"]]
    for an in J.get("animations", []):
        for s_ in an["samplers"]: s_["input"], s_["output"] = amap[s_["input"]], amap[s_["output"]]
    J["accessors"] = accs; J["bufferViews"] = bvs; J["buffers"] = [dict(byteLength=len(blob))]
    js = json.dumps(J, separators=(",", ":")).encode(); js += b" " * (-len(js) % 4); blob += b"\0" * (-len(blob) % 4)
    with open(out, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob))); f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(blob), 0x004E4942)); f.write(bytes(blob))
    if tex: Image.open(tex).convert("RGB").resize((tex_size, tex_size), Image.LANCZOS).save(tex, quality=86)
    return len(F), len(vF)

if __name__ == "__main__":
    a = sys.argv[1:]; size = int(a[a.index("--size") + 1]) if "--size" in a else 1024; name = a[a.index("--name") + 1] if "--name" in a else "grinch"
    print(json.dumps(reduce(a[0], a[1], size, name)))
