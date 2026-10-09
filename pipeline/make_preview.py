"""Self-contained single-file preview (for claude.ai artifacts / sharing): python3 pipeline/make_preview.py levels/<name> "Title" out.html
Embeds level.json, the glb and its textures (as data: URIs, since sandboxed pages block blob: texture loads)."""
import base64, json, os, sys

lvl, title, out = sys.argv[1:4]
s = open(os.path.join(os.path.dirname(__file__), "viewer.html")).read()
s = s.replace('<!doctype html>\n<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">\n', '')
s = s.replace('<title>Level Viewer</title>', f'<title>{title}</title>').replace(':root{--bg:#111;--fg:#eee}', ':root{--bg:#111;--fg:#eee;color-scheme:dark}')
s = s.replace('</head><body>\n', '').replace('</body></html>', '')
s = s.replace('#hud{position:fixed;top:8px', '#hud{position:fixed;top:calc(8px + env(safe-area-inset-top,0px))')
glb = open(os.path.join(lvl, "level.glb"), "rb").read()
# exact image bytes from the glb (no re-encode), pooled so shared maps are embedded once
from glb_tools import _read, _view
g, binary = _read(os.path.join(lvl, "level.glb")); pool, uri_id, tex = [], {}, {}
def img_uri(ti):
    im = g["images"][g["textures"][ti]["source"]]
    u = f"data:{im.get('mimeType', 'image/jpeg')};base64," + base64.b64encode(_view(binary, g["bufferViews"][im["bufferView"]])).decode()
    if u not in uri_id: uri_id[u] = len(pool); pool.append(u)
    return uri_id[u]
for mat in g.get("materials", []):
    pbr = mat.get("pbrMetallicRoughness", {}); e = {}
    for key, src in (("base", pbr.get("baseColorTexture")), ("orm", pbr.get("metallicRoughnessTexture")),
                     ("normal", mat.get("normalTexture")), ("emis", mat.get("emissiveTexture"))):
        if src: e[key] = img_uri(src["index"])
    if e: tex[mat["name"]] = e
s = s.replace("const meta=await (await fetch(base+'/level.json')).json();", "const meta=" + open(os.path.join(lvl, "level.json")).read() + ";")
s = s.replace("const gltf=await new GLTFLoader().loadAsync(base+'/level.glb');",
              "const buf=Uint8Array.from(atob(GLB),c=>c.charCodeAt(0)).buffer;const gltf=await new GLTFLoader().parseAsync(buf,'');")
s = s.replace('<script type="module">', '<script>const GLB="' + base64.b64encode(glb).decode() + '";window.TEXP=' + json.dumps(pool) + ';window.TEX=' + json.dumps(tex) + ';</script>\n<script type="module">', 1)
assert "parseAsync" in s and "const meta={" in s and "<html" not in s
open(out, "w").write(s)
print(f"{out}: {len(s) // 1024} KB, {len(tex)} materials, {len(pool)} images")
