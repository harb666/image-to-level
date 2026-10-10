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


def _repack(g, binary, new_views):
    """Rebuild the binary chunk; new_views: {bufferView index: replacement bytes}."""
    out, bvs = bytearray(), g["bufferViews"]
    for i, bv in enumerate(bvs):
        out += b"\0" * (-len(out) % 4); chunk = new_views.get(i, _view(binary, bv))
        bv["byteOffset"] = len(out); bv["byteLength"] = len(chunk); out += chunk
    g["buffers"] = [{"byteLength": len(out) + (-len(out) % 4)}]
    return bytes(out)


def downscale_images(path, max_px, quality=82):
    """Cap every embedded image at max_px (keeps aspect, re-encodes JPEG). Returns number of images changed."""
    import io
    from PIL import Image
    g, binary = _read(path); new = {}
    for im in g.get("images", []):
        bv = g["bufferViews"][im["bufferView"]]; img = Image.open(io.BytesIO(_view(binary, bv)))
        if max(img.size) <= max_px: continue
        s = max_px / max(img.size); img = img.convert("RGB").resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
        b = io.BytesIO(); img.save(b, "JPEG", quality=quality); new[im["bufferView"]] = b.getvalue(); im["mimeType"] = "image/jpeg"
    if new: _write(path, g, _repack(g, binary, new))
    return len(new)


def set_node_extras(path, extras):
    """glTF node "extras" (Godot can import them as node metadata): {node name: dict}."""
    g, binary = _read(path)
    for n in g.get("nodes", []):
        if n.get("name") in extras: n["extras"] = extras[n["name"]]
    _write(path, g, binary)


def restore_images(path, ref_glb):
    """Replace re-encoded images (e.g. trimesh re-saving JPEGs as PNG after a load/export round trip) with the exact
    original bytes from ref_glb, matched by decoded pixels. Lossless; returns number of images restored."""
    import hashlib, io
    import numpy as np
    from PIL import Image
    key = lambda raw: hashlib.sha1(np.asarray(Image.open(io.BytesIO(raw)).convert("RGB")).tobytes()).hexdigest()
    rg, rb = _read(ref_glb); orig = {}
    for im in rg.get("images", []):
        raw = _view(rb, rg["bufferViews"][im["bufferView"]]); orig[key(raw)] = (raw, im.get("mimeType", "image/jpeg"))
    g, binary = _read(path); new = {}
    for im in g.get("images", []):
        k = key(_view(binary, g["bufferViews"][im["bufferView"]]))
        if k in orig: new[im["bufferView"]] = orig[k][0]; im["mimeType"] = orig[k][1]
    if new: _write(path, g, _repack(g, binary, new))
    return len(new)


FAR_MATERIAL = dict(name="ter_far", pbrMetallicRoughness=dict(baseColorFactor=[1, 1, 1, 1], metallicFactor=0.0, roughnessFactor=0.95),
                    extras=dict(note="Stage 9 distant terrain: albedo = vertex colour (COLOR_0, linear). Godot import enables vertex_color_use_as_albedo."))


def far_material(path, prefixes=("TRM_",), suffixes=("_far",)):
    """Primitives of vertex-coloured distant terrain meshes (no material from trimesh) get one shared matte material
    (the glTF default would be fully metallic). Returns the number of primitives patched."""
    g, binary = _read(path); names = {}
    for n in g.get("nodes", []):
        if "mesh" in n and (n.get("name", "").startswith(prefixes) or n.get("name", "").endswith(suffixes)): names[n["mesh"]] = True
    if not names: return 0
    g.setdefault("materials", []).append(dict(FAR_MATERIAL)); mi = len(g["materials"]) - 1; k = 0
    for i in names:
        for pr in g["meshes"][i]["primitives"]:
            if "material" not in pr and "COLOR_0" in pr["attributes"]: pr["material"] = mi; k += 1
    _write(path, g, binary); return k
