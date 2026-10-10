"""Stage 7: automatic visual validation renders -> levels/<name>/checks/views/ (+ contact_sheet.jpg).

  python3 pipeline/render_views.py levels/<name> [--mobile] [--size 640x360]

Builds a self-contained preview (make_preview.py) and renders it headless with Chromium + SwiftShader (CPU WebGL) from
viewpoints computed from level.json: bird's-eye, overview, four compass views at player height from the spawn, the
third-person spawn camera, the largest platforms, background-facing views over each side, and the tallest structure.
These are REAL renders of the browser preview (three.js) - close to, but not identical with, Godot. If Chromium /
Playwright is unavailable the script says so and exits non-zero; it never fabricates images.
Claude inspects contact_sheet.jpg (and single views) after every generation / refinement pass.
"""
import json, math, os, shutil, subprocess, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))


def viewpoints(L, G):
    b0, b1 = L["bounds"]["min"], L["bounds"]["max"]; cx, cz = (b0[0] + b1[0]) / 2, (b0[2] + b1[2]) / 2
    ext = max(b1[0] - b0[0], b1[2] - b0[2]); top = b1[1]; eye_h = G["player"]["eye_height"]
    sp = L["spawn"]["position"]; yaw = math.radians(L["spawn"]["yaw_deg"]); f = (-math.sin(yaw), -math.cos(yaw))
    V = [dict(name="01_birdseye", eye=[cx, ext * 1.25, cz + 0.01], target=[cx, 0, cz], fov=50),
         dict(name="02_overview_se", eye=[cx + ext * 0.55, top + ext * 0.45, cz + ext * 0.75], target=[cx, top * 0.2, cz], fov=55),
         dict(name="03_overview_west_low", eye=[cx - ext * 0.85, top * 0.8 + ext * 0.12, cz + ext * 0.25], target=[cx, top * 0.25, cz], fov=55)]
    arm = G["camera"]["arm_length"]; head = [sp[0], sp[1] + eye_h + G["camera"]["pivot_above_eye"], sp[2]]
    V.append(dict(name="04_third_person_spawn", eye=[head[0] - f[0] * arm, head[1] + 1.2, head[2] - f[1] * arm], target=[head[0] + f[0] * 10, head[1] - 0.5, head[2] + f[1] * 10], fov=70))
    for k, (nm, d) in enumerate((("north", (0, -1)), ("east", (1, 0)), ("south", (0, 1)), ("west", (-1, 0)))):
        V.append(dict(name=f"{5 + k:02d}_player_{nm}", eye=[sp[0], sp[1] + eye_h, sp[2]], target=[sp[0] + d[0] * 30, sp[1] + eye_h - 2, sp[2] + d[1] * 30], fov=75))
    named = [w for w in L.get("walkable", []) if w.get("name") and w["name"] not in ("Ground",)]
    pref = [w for w in named if not w["name"].startswith(("Walkway", "Bridge", "Ramp"))] or named
    plats = sorted(pref, key=lambda w: -(w["max"][0] - w["min"][0]) * (w["max"][1] - w["min"][1]))[:3]
    for k, w in enumerate(plats):
        px, pz = (w["min"][0] + w["max"][0]) / 2, (w["min"][1] + w["max"][1]) / 2; dx, dz = cx - px, cz - pz; d = math.hypot(dx, dz) or 1
        e = [px + dx / d * 16 + 4, w["y"] + 9, pz + dz / d * 16 + 4] if d > 2 else [px + 12, w["y"] + 10, pz + 14]
        V.append(dict(name=f"{9 + k:02d}_platform_{w['name']}", eye=e, target=[px, w["y"], pz], fov=60))
    hi = top - 6 if top > 12 else top
    for k, (nm, d) in enumerate((("north", (0, -1)), ("east", (1, 0)), ("south", (0, 1)), ("west", (-1, 0)))):  # over the walls at the world beyond
        V.append(dict(name=f"{12 + k:02d}_background_{nm}", eye=[cx + d[0] * ext * 0.3, hi + 2, cz + d[1] * ext * 0.3], target=[cx + d[0] * 250, hi * 0.4, cz + d[1] * 250], fov=70))
    groups = [o for o in L["objects"] if o["type"] == "group" and not o.get("parent")]
    cand = [o for o in L["objects"] if o.get("size") and o["type"] not in ("boundary", "terrain", "panel") and not o["name"].startswith(("Hazard", "OuterWall", "Boundary", "Ground"))] or L["objects"]
    tall = max(cand, key=lambda o: o["size"][1])
    tp = _world_pos(L, tall); h = tall["size"][1]
    V.append(dict(name="16_detail_" + tall["name"], eye=[tp[0] + 9, tp[1] + h * 0.6, tp[2] + 11], target=[tp[0], tp[1] + h * 0.45, tp[2]], fov=60))
    if isinstance(L.get("terrain"), dict): V += world_viewpoints(L, G)
    return V


def world_viewpoints(L, G):
    """Stage 9: third-person cameras at the playable boundary looking OUT in each compass direction (world limits must
    stay hidden), the highest playable point, and a high overview of the near / middle / far zones."""
    import numpy as np
    from terrain import Terrain
    TR = Terrain(L["terrain"]); B = np.asarray((L["terrain"].get("boundary") or {}).get("points") or [[TR.x0, TR.z0], [TR.x1, TR.z0], [TR.x1, TR.z1], [TR.x0, TR.z1]], float)
    c = B.mean(0); eye = G["player"]["eye_height"]; arm = G["camera"]["arm_length"]; V = []
    for k, (nm, d) in enumerate((("north", (0, -1)), ("east", (1, 0)), ("south", (0, 1)), ("west", (-1, 0)))):
        p = B[np.argmax((B - c) @ np.array(d))]; p = p + (c - p) / np.linalg.norm(c - p) * 8; y = TR.height_at(*p)
        V.append(dict(name=f"{17 + k:02d}_edge_{nm}_3rd", eye=[float(p[0] - d[0] * arm), y + eye + 1.4, float(p[1] - d[1] * arm)], target=[float(p[0] + d[0] * 60), y + eye - 1, float(p[1] + d[1] * 60)], fov=70))
    G_ = TR.grid(); from terrain import inside_poly
    ins = inside_poly(B, G_["X"], G_["Z"]); i, j = np.unravel_index(np.argmax(np.where(ins, G_["H"], -1e9)), G_["H"].shape)
    hp = [float(G_["X"][i, j]), float(G_["H"][i, j]), float(G_["Z"][i, j])]
    V.append(dict(name="21_hilltop_view", eye=[hp[0], hp[1] + eye + 1.2, hp[2]], target=[float(c[0]), hp[1] - 6, float(c[1])], fov=75))
    R = float(np.linalg.norm(B - c, axis=1).max())
    V.append(dict(name="22_zones_overview", eye=[float(c[0]) + R * 1.3, R * 0.9, float(c[1]) + R * 1.6], target=[float(c[0]), 0, float(c[1])], fov=60))
    return V


def inspection_viewpoints(L, max_views=16):
    """Stage 8: close-ups of junctions (connector ends), stair/ramp landings, pipe outlets and liquid impacts, plus a
    third-person view at the first junctions. Derived from anchors/relations, so they work for any level."""
    import numpy as np
    from anchors import world_matrices, world_anchor, infer_relations
    W, by = world_matrices(L); rel = infer_relations(L); V, seen = [], set()
    for r in rel:
        if r["type"] != "walkable_connection" or r["a"] not in by: continue
        a = world_anchor(W, by[r["a"]], r.get("a_anchor"))
        if a is None: continue
        E = a["pos"]; key = tuple(np.round(E, 0))
        if key in seen: continue
        seen.add(key); u = a["dir"].copy(); u[1] = 0; u /= (np.linalg.norm(u) or 1); v = np.array([-u[2], 0, u[0]])
        eye = E + v * 5.5 - u * 2.0 + [0, 3.2, 0]
        V.append(dict(name=f"j_{r['a']}_{r.get('a_anchor')}", eye=eye.round(2).tolist(), target=(E + [0, -0.3, 0]).round(2).tolist(), fov=55))
    for r in rel:
        if r["type"] != "emits_from" or r["b"] not in by: continue
        a = world_anchor(W, by[r["b"]], r.get("b_anchor") or "outlet")
        if a is None: continue
        O, D = a["pos"], a["dir"]; side = np.cross(D, [0, 1, 0]); side = side / (np.linalg.norm(side) or 1)
        V.append(dict(name=f"o_{r['b']}", eye=(O + side * 6 + D * 4 + [0, 0.5, 0]).round(2).tolist(), target=(O + D * 1.2 + [0, -2.5, 0]).round(2).tolist(), fov=60))
    # third-person camera at junctions: player standing on the connector end, camera behind at arm length
    from gameplay import load_gameplay
    G = load_gameplay(None, L); tp = []
    for r in [r for r in rel if r["type"] == "walkable_connection" and r["a"] in by][:12:3]:
        a = world_anchor(W, by[r["a"]], r.get("a_anchor"))
        if a is None: continue
        u = a["dir"].copy(); u[1] = 0; u /= (np.linalg.norm(u) or 1); head = a["pos"] - u * 1.0 + [0, G["player"]["eye_height"] + G["camera"]["pivot_above_eye"], 0]
        tp.append(dict(name=f"t_{r['a']}_{r.get('a_anchor')}", eye=(head - u * G["camera"]["arm_length"] + [0, 1.0, 0]).round(2).tolist(), target=(head + u * 6 - [0, 1.2, 0]).round(2).tolist(), fov=70))
    kinds = {}  # variety: one of each connector kind first (bridge / ramp / stairs / deck), then outlets, then third-person
    for v in V:
        if v["name"].startswith("j_"):
            k = next((t for t in ("Bridge", "Ramp", "Stairs", "Deck", "Link") if t in v["name"]), "other"); kinds.setdefault(k, []).append(v)
    js = []
    while len(js) < 6 and any(kinds.values()):
        for k in list(kinds):
            if kinds[k] and len(js) < 6: js.append(kinds[k].pop(0))
    os_ = [v for v in V if v["name"].startswith("o_")][:6]
    out = js + os_ + tp[:4] + [v for v in V if v not in js and v not in os_]
    return out[:max_views]


def inspect(level_dir, views_file=None, out_name="inspect", mobile=False, size=(640, 360)):
    """Render inspection close-ups (same cameras when views_file is given -> before/after comparisons)."""
    L = json.load(open(os.path.join(level_dir, "level.json")))
    V = json.load(open(views_file)) if views_file else inspection_viewpoints(L)
    return render(level_dir, mobile, size, V, out_name)


def _world_pos(L, o):
    by = {x["name"]: x for x in L["objects"]}; p = list(o["position"]); par = o.get("parent")
    while par:  # rotation of parents ignored for this camera aim (good enough to frame it)
        q = by[par]["position"]; p = [p[0] + q[0], p[1] + q[1], p[2] + q[2]]; par = by[par].get("parent")
    return p


def render(level_dir, mobile=False, size=(640, 360), views=None, out_name="views"):
    from gameplay import load_gameplay
    L = json.load(open(os.path.join(level_dir, "level.json"))); G = load_gameplay(level_dir, L)
    out = os.path.join(level_dir, "checks", out_name); shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    html = os.path.join(out, "_preview.html")
    subprocess.run([sys.executable, os.path.join(HERE, "make_preview.py"), level_dir, "render", html, "--no-issues"] + (["--mobile"] if mobile else []), check=True, stdout=subprocess.DEVNULL)
    V = views or viewpoints(L, G); vf = os.path.join(out, "_views.json"); json.dump(V, open(vf, "w"), indent=1)
    if not shutil.which("node"): raise SystemExit("render_views: node is not installed - no screenshots (use the geometric checks + preview)")
    r = subprocess.run(["node", os.path.join(HERE, "render", "render_views.js"), html, vf, out, str(size[0]), str(size[1])], capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit("render_views: headless browser failed:\n" + r.stderr[-1500:])
    os.remove(html); log = json.load(open(os.path.join(out, "render_log.json")))
    files = [v for v in V if os.path.exists(os.path.join(out, v["name"] + ".png"))]
    cols = 4; tw, th = size[0] // 2, size[1] // 2; rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 16)), (20, 20, 20)); dr = ImageDraw.Draw(sheet)
    for i, v in enumerate(files):
        im = Image.open(os.path.join(out, v["name"] + ".png")).convert("RGB").resize((tw, th)); x, y = (i % cols) * tw, (i // cols) * (th + 16)
        sheet.paste(im, (x, y + 16)); dr.text((x + 4, y + 2), v["name"], fill=(255, 255, 255))
    sheet.save(os.path.join(out, "contact_sheet.jpg"), quality=85)
    res = dict(views=len(files), errors=log["errors"], load_seconds=log.get("load_seconds"), renderer=log.get("renderer"),
               contact_sheet=os.path.relpath(os.path.join(out, "contact_sheet.jpg"), level_dir), note="browser preview renders (three.js, SwiftShader) - not Godot")
    json.dump(res, open(os.path.join(level_dir, "checks", "render.json" if out_name == "views" else f"render_{out_name}.json"), "w"), indent=1); print(json.dumps(res)); return res


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    sz = tuple(int(v) for v in sys.argv[sys.argv.index("--size") + 1].split("x")) if "--size" in sys.argv else (640, 360)
    if "--size" in sys.argv: a = [x for x in a if x != sys.argv[sys.argv.index("--size") + 1]]
    if "--inspect" in sys.argv:
        vf = sys.argv[sys.argv.index("--views") + 1] if "--views" in sys.argv else None
        if vf: a = [x for x in a if x != vf]
        inspect(a[0], vf, sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "inspect", "--mobile" in sys.argv, sz)
    else: render(a[0], "--mobile" in sys.argv, sz)
