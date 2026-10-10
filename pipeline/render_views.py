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
    return V


def _world_pos(L, o):
    by = {x["name"]: x for x in L["objects"]}; p = list(o["position"]); par = o.get("parent")
    while par:  # rotation of parents ignored for this camera aim (good enough to frame it)
        q = by[par]["position"]; p = [p[0] + q[0], p[1] + q[1], p[2] + q[2]]; par = by[par].get("parent")
    return p


def render(level_dir, mobile=False, size=(640, 360), views=None):
    from gameplay import load_gameplay
    L = json.load(open(os.path.join(level_dir, "level.json"))); G = load_gameplay(level_dir, L)
    out = os.path.join(level_dir, "checks", "views"); shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
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
    json.dump(res, open(os.path.join(level_dir, "checks", "render.json"), "w"), indent=1); print(json.dumps(res)); return res


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    sz = tuple(int(v) for v in sys.argv[sys.argv.index("--size") + 1].split("x")) if "--size" in sys.argv else (640, 360)
    if "--size" in sys.argv: a = [x for x in a if x != sys.argv[sys.argv.index("--size") + 1]]
    render(a[0], "--mobile" in sys.argv, sz)
