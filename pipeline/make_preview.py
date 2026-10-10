"""Self-contained single-file preview (for claude.ai artifacts / sharing): python3 pipeline/make_preview.py levels/<name> "Title" out.html
Embeds level.json, level.glb, background.glb + environment.json + sky panorama when present, and every texture as a
data: URI (sandboxed pages block the blob: URLs GLTFLoader would use for textures inside a .glb)."""
import base64, json, os, sys
from glb_tools import _read, _view

lvl, title, out = sys.argv[1:4]
MOB = "--mobile" in sys.argv  # preview the Stage 5 mobile export (mobile/level_mobile.glb, background_mobile.glb, effects_mobile.json)
P = (lambda f: os.path.join(lvl, "mobile", {"level.glb": "level_mobile.glb", "background.glb": "background_mobile.glb", "effects.json": "effects_mobile.json"}[f])) if MOB \
    else (lambda f: os.path.join(lvl, f))
s = open(os.path.join(os.path.dirname(__file__), "viewer.html")).read()
s = s.replace('<!doctype html>\n<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">\n', '')
s = s.replace('<title>Level Viewer</title>', f'<title>{title}</title>').replace(':root{--bg:#111;--fg:#eee}', ':root{--bg:#111;--fg:#eee;color-scheme:dark}')
s = s.replace('</head><body>\n', '').replace('</body></html>', '')
s = s.replace('#hud{position:fixed;top:8px', '#hud{position:fixed;top:calc(8px + env(safe-area-inset-top,0px))')
pool, uri_id, tex = [], {}, {}


def add_glb_textures(path):
    """Exact image bytes from the glb (no re-encode), pooled so shared maps are embedded once."""
    g, binary = _read(path)
    def uri(ti):
        im = g["images"][g["textures"][ti]["source"]]
        u = f"data:{im.get('mimeType', 'image/jpeg')};base64," + base64.b64encode(_view(binary, g["bufferViews"][im["bufferView"]])).decode()
        if u not in uri_id: uri_id[u] = len(pool); pool.append(u)
        return uri_id[u]
    for mat in g.get("materials", []):
        pbr = mat.get("pbrMetallicRoughness", {}); e = {}
        for key, src in (("base", pbr.get("baseColorTexture")), ("orm", pbr.get("metallicRoughnessTexture")),
                         ("normal", mat.get("normalTexture")), ("emis", mat.get("emissiveTexture"))):
            if src: e[key] = uri(src["index"])
        if e: tex[mat["name"]] = e


b64 = lambda p: base64.b64encode(open(p, "rb").read()).decode()
glob = {"GLB": b64(P("level.glb"))}; add_glb_textures(P("level.glb"))
envp = os.path.join(lvl, "environment.json")
if os.path.exists(envp):
    env = json.load(open(envp)); glob["ENV"] = env
    glob["SKY"] = "data:image/jpeg;base64," + b64(os.path.join(lvl, env["sky"]["image"]))
    if env["files"].get("background"):
        glob["BGGLB"] = b64(P("background.glb")); add_glb_textures(P("background.glb"))
fxp = P("effects.json")
if os.path.exists(fxp):  # Stage 4: effects metadata + particle sprites
    fx = json.load(open(fxp)); glob["FX"] = fx
    glob["FXTEX"] = {k: "data:image/png;base64," + b64(os.path.join(lvl, v)) for k, v in fx["textures"].items()}
glob.update(TEXP=pool, TEX=tex)
import hashlib, time  # footer: which build this is (so an old cached page is obvious) + the triangle count of what is shown
glob["BUILD_ID"] = "build " + time.strftime("%m-%d %H:%M") + " " + hashlib.sha1(open(P("level.glb"), "rb").read()).hexdigest()[:6]
if MOB and os.path.exists(os.path.join(lvl, "mobile", "mobile_manifest.json")):
    glob["TRIS_LABEL"] = f"{json.load(open(os.path.join(lvl, 'mobile', 'mobile_manifest.json')))['metrics']['mobile']['level']['triangles']} tris (mobile)"
from gameplay import load_gameplay  # Stage 7: player/camera numbers + validation issues for the overlay
glob["GAMEPLAY"] = {k: v for k, v in load_gameplay(lvl).items() if k in ("player", "camera", "design")}
rp = os.path.join(lvl, "checks", "report.json")
if os.path.exists(rp) and "--no-issues" not in sys.argv:
    glob["ISSUES"] = [i for i in json.load(open(rp)).get("issues", []) if i.get("pos")][:80]
s = s.replace("const meta=await (await fetch(base+'/level.json')).json();", "const meta=" + open(os.path.join(lvl, "level.json")).read() + ";")
s = s.replace('<script type="module">', "<script>" + "".join(f"window.{k}={json.dumps(v)};" for k, v in glob.items()) + "</script>\n<script type=\"module\">", 1)
assert "window.GLB=" in s and "const meta={" in s and "<html" not in s
open(out, "w").write(s)
print(f"{out}: {len(s) // 1024} KB, {len(tex)} materials, {len(pool)} images, env={'ENV' in glob}, fx={'FX' in glob}")
