"""Self-contained single-file preview (for claude.ai artifacts / sharing): python3 pipeline/make_preview.py levels/<name> "Title" out.html
Embeds level.json, the glb and its textures (as data: URIs, since sandboxed pages block blob: texture loads)."""
import base64, io, json, os, sys, trimesh

lvl, title, out = sys.argv[1:4]
s = open(os.path.join(os.path.dirname(__file__), "viewer.html")).read()
s = s.replace('<!doctype html>\n<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">\n', '')
s = s.replace('<title>Level Viewer</title>', f'<title>{title}</title>').replace(':root{--bg:#111;--fg:#eee}', ':root{--bg:#111;--fg:#eee;color-scheme:dark}')
s = s.replace('</head><body>\n', '').replace('</body></html>', '')
s = s.replace('#hud{position:fixed;top:8px', '#hud{position:fixed;top:calc(8px + env(safe-area-inset-top,0px))')
glb = open(os.path.join(lvl, "level.glb"), "rb").read()
tex = {}
for g in trimesh.load(os.path.join(lvl, "level.glb")).geometry.values():
    m = getattr(g.visual, "material", None); img = getattr(m, "baseColorTexture", None)
    if img is not None and m.name not in tex:
        b = io.BytesIO(); img.convert("RGB").save(b, "JPEG", quality=85)
        tex[m.name] = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
s = s.replace("const meta=await (await fetch(base+'/level.json')).json();", "const meta=" + open(os.path.join(lvl, "level.json")).read() + ";")
s = s.replace("const gltf=await new GLTFLoader().loadAsync(base+'/level.glb');",
              "const buf=Uint8Array.from(atob(GLB),c=>c.charCodeAt(0)).buffer;const gltf=await new GLTFLoader().parseAsync(buf,'');")
s = s.replace('<script type="module">', '<script>const GLB="' + base64.b64encode(glb).decode() + '";window.TEX=' + json.dumps(tex) + ';</script>\n<script type="module">', 1)
assert "parseAsync" in s and "const meta={" in s and "<html" not in s
open(out, "w").write(s)
print(f"{out}: {len(s) // 1024} KB, {len(tex)} textures")
