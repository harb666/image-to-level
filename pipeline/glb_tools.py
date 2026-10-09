"""Small in-place GLB post-processing (no external tools).
dedupe_images(path): identical embedded images (e.g. the ORM map used for both metallicRoughness and occlusion,
which trimesh writes twice) become one image/texture, and the binary chunk is repacked without the duplicates."""
import hashlib, json, struct


def _read(path):
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + jlen]), data[20 + jlen + 8:]


def _write(path, g, binary):
    j = json.dumps(g, separators=(",", ":")).encode(); j += b" " * (-len(j) % 4); binary += b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(j) + 8 + len(binary)
    open(path, "wb").write(struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(j), 0x4E4F534A) + j
                           + struct.pack("<II", len(binary), 0x004E4942) + binary)


def _view(binary, bv):
    o = bv.get("byteOffset", 0); return binary[o:o + bv["byteLength"]]


def dedupe_images(path):
    g, binary = _read(path)
    imgs, bvs = g.get("images", []), g["bufferViews"]
    first, img_map = {}, {}
    for i, im in enumerate(imgs):
        h = hashlib.sha1(_view(binary, bvs[im["bufferView"]])).hexdigest()
        img_map[i] = first.setdefault(h, i)
    keep = sorted(set(img_map.values())); new_img = {old: k for k, old in enumerate(keep)}
    tex_map, texs, seen = {}, [], {}
    for i, t in enumerate(g.get("textures", [])):
        t = dict(t, source=new_img[img_map[t["source"]]]); key = json.dumps(t, sort_keys=True)
        if key not in seen: seen[key] = len(texs); texs.append(t)
        tex_map[i] = seen[key]
    def fix(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.endswith("Texture") and isinstance(v, dict) and "index" in v: v["index"] = tex_map[v["index"]]
                else: fix(v)
        elif isinstance(o, list):
            for v in o: fix(v)
    fix(g.get("materials", []))
    g["images"] = [imgs[i] for i in keep]; g["textures"] = texs
    # repack: keep only bufferViews still referenced (accessors + kept images), 4-byte aligned
    used = sorted({a["bufferView"] for a in g.get("accessors", []) if "bufferView" in a} | {im["bufferView"] for im in g["images"]})
    out, remap = bytearray(), {}
    for i in used:
        out += b"\0" * (-len(out) % 4); bv = dict(bvs[i]); chunk = _view(binary, bv)
        bv["byteOffset"] = len(out); out += chunk; remap[i] = len(remap); bvs[i] = bv
    g["bufferViews"] = [bvs[i] for i in used]
    for a in g.get("accessors", []):
        if "bufferView" in a: a["bufferView"] = remap[a["bufferView"]]
    for im in g["images"]: im["bufferView"] = remap[im["bufferView"]]
    g["buffers"] = [{"byteLength": len(out) + (-len(out) % 4)}]
    _write(path, g, bytes(out))
    return len(imgs) - len(keep)
