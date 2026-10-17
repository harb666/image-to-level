"""Stage 92: external character / prop models in a level - a source GLB (skinned or not) baked into a small STATIC
"parts" GLB the build can place: rest pose (node transforms, skin ignored), feet at y = 0, one mesh per part (source
materials grouped into level material roles), each part decimated to a triangle budget (fast_simplification) - for
mobile memory. The build's object type "model" (build_level.shape) loads one part, scaled so the model's height is
the object's size[1].

  python3 pipeline/model_asset.py <source.glb> <out_parts.glb> '<json: {"part": {"materials": [...], "tris": N}}>'

Example (GIR, Stage 92): the source is the timesplitters-clone gir.glb ("Robot Gir - Invader Zim" by Rui Barbosa,
CC BY 4.0, rigged by that repo's scripts/gir/build_gir.mjs) -> levels/slime_arena/assets/gir_parts.glb."""
import json, sys
import numpy as np
import trimesh


def bake(src, out, parts):
    sc = trimesh.load(src, force="scene"); geoms = sc.dump()
    allv = np.vstack([g.vertices for g in geoms]); y0, H = float(allv[:, 1].min()), float(np.ptp(allv[:, 1]))
    cx, cz = float((allv[:, 0].min() + allv[:, 0].max()) / 2), float((allv[:, 2].min() + allv[:, 2].max()) / 2)
    res = trimesh.Scene(); stats = {}
    for name, p in parts.items():
        gs = [g for g in geoms if getattr(getattr(g.visual, "material", None), "name", None) in p["materials"]]
        if not gs: continue
        pcs = []
        for g in gs:  # each source piece on its own (Stage 92b): a small piece (a 20-triangle chest panel) never melts into a big one
            m = trimesh.Trimesh(g.vertices, g.faces, process=False); m.merge_vertices(merge_tex=True, merge_norm=True); pcs.append(m)
        n0 = sum(len(m.faces) for m in pcs); tgt = int(p.get("tris", n0)); keep = int(p.get("keep", 120))
        if tgt < n0:  # budget left after the kept pieces, shared by surface area (big flat shells need more than tiny dense claws)
            import fast_simplification
            big = [m for m in pcs if len(m.faces) > keep]; left = max(tgt - sum(len(m.faces) for m in pcs if len(m.faces) <= keep), len(big) * keep)
            A = sum(m.area for m in big) or 1.0
            for i, m in enumerate(pcs):
                if len(m.faces) <= keep: continue
                k = int(np.clip(left * m.area / A, keep, len(m.faces)))
                if k < len(m.faces):
                    v, f = fast_simplification.simplify(m.vertices.astype(np.float32), m.faces.astype(np.int32), target_reduction=1.0 - k / len(m.faces), agg=float(p.get("agg", 4)))
                    pcs[i] = trimesh.Trimesh(v, f, process=True)
        m = trimesh.util.concatenate(pcs)
        m.apply_translation([-cx, -y0, -cz]); m.apply_scale(1.0 / H)  # unit height, feet at y 0, centred on x / z
        m.fix_normals(); res.add_geometry(m, geom_name=name, node_name=name); stats[name] = [n0, len(m.faces)]
    res.export(out); return stats


if __name__ == "__main__":
    print(json.dumps(bake(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]))))
