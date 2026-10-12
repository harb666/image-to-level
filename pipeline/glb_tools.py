"""Small in-place GLB post-processing (no external tools).
dedupe_images(path): identical embedded images (e.g. the ORM map used for both metallicRoughness and occlusion,
which trimesh writes twice) become one image/texture, and the binary chunk is repacked without the duplicates."""
import hashlib, json, os, struct


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


def slim(path, plain_materials=(), drop_extras=(), weld_untextured=True, webp=None, mesh_meta=True):
    """Smaller GLB, same look where it matters (Stage 16):
      - 16-bit index buffers wherever a primitive has < 65536 vertices (trimesh always writes 32-bit),
      - materials named in plain_materials (e.g. toon materials) lose their normal / occlusion / metallic-roughness maps
        (base colour + emissive kept; flat toon shading never shows them) and the images nobody uses any more,
      - node extras keys in drop_extras are removed (e.g. preview-only pick data),
      - weld_untextured (Stage 25): primitives whose material has no texture (ink outlines) lose TEXCOORD_0 and their
        vertices are welded by position (fewer vertices, same shape),
      - webp=quality (Stage 25): images re-encoded as WebP behind EXT_texture_webp (Godot 4 reads it natively,
        three.js too); alpha kept,
      - mesh extras (trimesh metadata, sometimes whole UV lists) are dropped; mesh_meta=False also drops mesh names
        (collision.glb: Godot names the shapes after the nodes),
      - the binary chunk is rebuilt from the buffer views still in use (4-byte aligned).
    Returns (bytes before, bytes after)."""
    import numpy as np
    before = os.path.getsize(path); g, binary = _read(path)
    for m in g.get("materials", []):
        if m.get("name", "").split("__")[0] in plain_materials:
            for k in ("normalTexture", "occlusionTexture"): m.pop(k, None)
            pbr = m.get("pbrMetallicRoughness", {})
            if pbr.pop("metallicRoughnessTexture", None) is not None: pbr["metallicFactor"] = 0.0; pbr.setdefault("roughnessFactor", 1.0)
    for n in g.get("nodes", []):
        if "extras" in n:
            for k in drop_extras: n["extras"].pop(k, None)
            if not n["extras"]: n.pop("extras")
    used_tex = sorted({t["index"] for m in g.get("materials", []) for t in _tex_refs(m)})  # drop unreferenced textures / images
    tmap = {o: i for i, o in enumerate(used_tex)}; g["textures"] = [g["textures"][i] for i in used_tex] if used_tex else []
    for m in g.get("materials", []):
        for t in _tex_refs(m): t["index"] = tmap[t["index"]]
    src_of = lambda t: t["source"] if "source" in t else t["extensions"]["EXT_texture_webp"]["source"]
    used_img = sorted({src_of(t) for t in g["textures"]}); imap = {o: i for i, o in enumerate(used_img)}
    g["images"] = [g["images"][i] for i in used_img] if used_img else []
    for t in g["textures"]:
        if "source" in t: t["source"] = imap[t["source"]]
        else: t["extensions"]["EXT_texture_webp"]["source"] = imap[src_of(t)]
    for k in ("textures", "images"):
        if not g[k]: g.pop(k)
    if not g.get("textures"): g.pop("samplers", None)
    views = {}  # rebuild the buffer: bufferView index -> new bytes
    for me in g.get("meshes", []):
        me.pop("extras", None)  # trimesh metadata (units, per-vertex uv copies of shapes): nothing reads it
        if not mesh_meta: me.pop("name", None)
    if weld_untextured:
        for me in g.get("meshes", []):
            for p in me["primitives"]:
                mat = g["materials"][p["material"]] if "material" in p else {}
                if _tex_refs(mat) or "TEXCOORD_0" not in p["attributes"] or set(p["attributes"]) - {"POSITION", "TEXCOORD_0"} or "indices" not in p: continue
                pa, ia = g["accessors"][p["attributes"]["POSITION"]], g["accessors"][p["indices"]]
                if g["bufferViews"][pa["bufferView"]].get("byteStride") or pa["bufferView"] in views or ia["bufferView"] in views: continue
                if sum(a.get("bufferView") in (pa["bufferView"], ia["bufferView"]) for a in g["accessors"]) != 2: continue  # views shared with other data
                P_ = np.frombuffer(_view(binary, g["bufferViews"][pa["bufferView"]]), dtype="<f4", count=pa["count"] * 3, offset=pa.get("byteOffset", 0)).reshape(-1, 3)
                dt = {5121: "<u1", 5123: "<u2", 5125: "<u4"}[ia["componentType"]]
                I_ = np.frombuffer(_view(binary, g["bufferViews"][ia["bufferView"]]), dtype=dt, count=ia["count"], offset=ia.get("byteOffset", 0))
                uq, inv = np.unique(P_, axis=0, return_inverse=True); inv = inv.ravel()
                views[pa["bufferView"]] = uq.astype("<f4").tobytes(); pa["count"] = len(uq); pa.pop("byteOffset", None)
                views[ia["bufferView"]] = inv[I_].astype("<u4").tobytes(); ia["componentType"] = 5125; ia.pop("byteOffset", None)
                p["attributes"].pop("TEXCOORD_0")
    idx_acc = {p["indices"] for me in g.get("meshes", []) for p in me["primitives"] if "indices" in p}
    for ai in idx_acc:
        a = g["accessors"][ai]; bv = g["bufferViews"][a["bufferView"]]
        if a["componentType"] != 5125: continue
        data = np.frombuffer(views[a["bufferView"]], dtype="<u4") if a["bufferView"] in views else np.frombuffer(_view(binary, bv), dtype="<u4", count=a["count"], offset=a.get("byteOffset", 0))
        if data.size and data.max() < 65535:
            views[a["bufferView"]] = data.astype("<u2").tobytes(); a["componentType"] = 5123; a.pop("byteOffset", None)
            a.pop("max", None); a.pop("min", None)
    if webp and g.get("images"):
        from PIL import Image
        import io
        for im in g["images"]:
            if "bufferView" not in im or im.get("mimeType") == "image/webp": continue
            pic = Image.open(io.BytesIO(_view(binary, g["bufferViews"][im["bufferView"]]))); buf = io.BytesIO()
            pic = pic.convert("RGBA" if "A" in pic.getbands() or "transparency" in pic.info else "RGB")
            if pic.mode == "RGBA" and pic.getchannel("A").getextrema() == (255, 255): pic = pic.convert("RGB")
            pic.save(buf, "WEBP", quality=int(webp), method=6); new = buf.getvalue()
            if len(new) < g["bufferViews"][im["bufferView"]]["byteLength"]: views[im["bufferView"]] = new; im["mimeType"] = "image/webp"
        wi = {i for i, im in enumerate(g["images"]) if im.get("mimeType") == "image/webp"}
        for t in g.get("textures", []):
            if t.get("source") in wi: t.setdefault("extensions", {})["EXT_texture_webp"] = {"source": t.pop("source")}
        if wi:
            for k in ("extensionsUsed", "extensionsRequired"): g[k] = sorted(set(g.get(k, [])) | {"EXT_texture_webp"})
    keep = sorted({a["bufferView"] for a in g.get("accessors", []) if "bufferView" in a} | {i["bufferView"] for i in g.get("images", []) if "bufferView" in i})
    vmap, out, seen = {}, bytearray(), {}  # identical buffer views (e.g. every box collider's index list) are stored once
    for vi in keep:
        bv = dict(g["bufferViews"][vi]); data = views.get(vi, _view(binary, g["bufferViews"][vi]))
        if vi in views: bv.pop("byteStride", None)
        key = (bytes(data), bv.get("byteStride"), bv.get("target"))
        if key in seen: vmap[vi] = seen[key]; continue
        out += b"\0" * (-len(out) % 4); bv["byteOffset"] = len(out); bv["byteLength"] = len(data); bv["buffer"] = 0
        out += data; vmap[vi] = seen[key] = len(g.setdefault("_nv", [])); g["_nv"].append(bv)
    g["bufferViews"] = g.pop("_nv", [])
    for a in g.get("accessors", []):
        if "bufferView" in a: a["bufferView"] = vmap[a["bufferView"]]
    for i in g.get("images", []):
        if "bufferView" in i: i["bufferView"] = vmap[i["bufferView"]]
    amap, uniq, akey = {}, [], {}  # ... and so are accessors that became identical
    for ai, a in enumerate(g.get("accessors", [])):
        k = json.dumps(a, sort_keys=True); amap[ai] = akey.setdefault(k, len(uniq))
        if amap[ai] == len(uniq): uniq.append(a)
    if g.get("accessors"):
        g["accessors"] = uniq
        for me in g.get("meshes", []):
            for p in me["primitives"]:
                p["attributes"] = {k: amap[v] for k, v in p["attributes"].items()}
                if "indices" in p: p["indices"] = amap[p["indices"]]
                for t in p.get("targets", []): t.update({k: amap[v] for k, v in t.items()})
        for sk in g.get("skins", []):
            if "inverseBindMatrices" in sk: sk["inverseBindMatrices"] = amap[sk["inverseBindMatrices"]]
        for an in g.get("animations", []):
            for smp in an.get("samplers", []): smp["input"], smp["output"] = amap[smp["input"]], amap[smp["output"]]
    g["buffers"] = [{"byteLength": len(out) + (-len(out) % 4)}]
    _write(path, g, bytes(out)); return before, os.path.getsize(path)


def _tex_refs(m):
    pbr = m.get("pbrMetallicRoughness", {})
    return [t for t in (pbr.get("baseColorTexture"), pbr.get("metallicRoughnessTexture"), m.get("normalTexture"), m.get("occlusionTexture"), m.get("emissiveTexture")) if t]
