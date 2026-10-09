"""Engine-independent GLB metrics: python3 pipeline/glb_stats.py levels/<name>/level.glb [--json]
Reads the glTF JSON + embedded images directly. All GPU numbers are ESTIMATES, not device benchmarks:
- draw_calls_unbatched: one per mesh primitive per node that uses it (what an engine issues with no batching)
- draw_calls_batched_min: one per distinct material (best case if the engine merges static meshes by material)
- tex_mem_uncompressed_mb: RGBA8 + full mip chain (x4/3)
- tex_mem_gpu_compressed_mb: ~1 byte/px (ASTC 4x4 / ETC2 RGBA8) + mips, i.e. after Godot's VRAM compression on import"""
import io, json, struct, sys
from PIL import Image


def stats(path):
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    g = json.loads(data[20:20 + jlen]); binary = data[20 + jlen + 8:]
    acc, bvs = g.get("accessors", []), g.get("bufferViews", [])
    mesh_prims = [m["primitives"] for m in g.get("meshes", [])]
    mesh_nodes = [n for n in g.get("nodes", []) if "mesh" in n]
    tris = 0; draws = 0
    for n in mesh_nodes:
        for p in mesh_prims[n["mesh"]]:
            draws += 1
            tris += (acc[p["indices"]]["count"] if "indices" in p else acc[p["attributes"]["POSITION"]]["count"]) // 3
    px = 0; imgs = []
    for im in g.get("images", []):
        bv = bvs[im["bufferView"]]; raw = binary[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        w, h = Image.open(io.BytesIO(raw)).size; px += w * h; imgs.append(f"{w}x{h} {im.get('mimeType', '?').split('/')[-1]}")
    slots = {}
    for m in g.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        for k in ("baseColorTexture", "metallicRoughnessTexture"):
            if k in pbr: slots[k] = slots.get(k, 0) + 1
        for k in ("normalTexture", "occlusionTexture", "emissiveTexture"):
            if k in m: slots[k] = slots.get(k, 0) + 1
    return dict(glb_kb=round(len(data) / 1024), triangles=tris, nodes=len(g.get("nodes", [])), mesh_nodes=len(mesh_nodes),
                unique_meshes=len(mesh_prims), materials=len(g.get("materials", [])), images=len(imgs),
                draw_calls_unbatched=draws, draw_calls_batched_min=len({p.get("material") for ps in mesh_prims for p in ps}),
                tex_mem_uncompressed_mb=round(px * 4 * 4 / 3 / 2 ** 20, 2), tex_mem_gpu_compressed_mb=round(px * 4 / 3 / 2 ** 20, 2),
                texture_slots=slots, image_sizes=sorted(set(imgs)))


if __name__ == "__main__":
    s = stats(sys.argv[1])
    print(json.dumps(s) if "--json" in sys.argv else "\n".join(f"{k}: {v}" for k, v in s.items()))
