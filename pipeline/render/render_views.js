// Headless screenshots of a self-contained level preview (make_preview.py output).
//   node pipeline/render/render_views.js <preview.html> <views.json> <out_dir> [width height]
// views.json: [{name, eye:[x,y,z], target:[x,y,z], fov}] -> <out_dir>/<name>.png + render_log.json (page errors = asset problems).
// Renders with the page's own three.js viewer (software WebGL / SwiftShader on CPU) under an artifact-like CSP.
const path = require('path'), fs = require('fs');
let chromium; try { ({chromium} = require('playwright')); } catch (e) { ({chromium} = require('/opt/node22/lib/node_modules/playwright')); }
const [html, viewsFile, outDir, W = '640', H = '360'] = process.argv.slice(2);
const THREE_DIR = [path.join(__dirname, 'node_modules/three'), path.join(process.cwd(), 'node_modules/three')].find(p => fs.existsSync(p));
const CSP = "default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'unsafe-inline'; img-src data:; connect-src 'none'";
(async () => {
  const views = JSON.parse(fs.readFileSync(viewsFile)); fs.mkdirSync(outDir, {recursive: true});
  const log = {errors: [], warnings: [], views: [], three: THREE_DIR ? 'local' : 'cdn'};
  const b = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']});
  const p = await b.newPage({viewport: {width: +W, height: +H}});
  p.on('pageerror', e => log.errors.push(String(e.message).slice(0, 300)));
  p.on('console', m => { const t = m.text(); if (m.type() === 'error' && !/blob:|Content Security Policy/.test(t)) log.errors.push(t.slice(0, 300)); });
  await p.route('**/*', r => {
    const u = r.request().url();
    if (THREE_DIR && u.includes('cdn.jsdelivr.net/npm/three@0.160.0/')) return r.fulfill({path: path.join(THREE_DIR, u.split('three@0.160.0/')[1]), contentType: 'application/javascript'});
    if (u === 'http://level/') return r.fulfill({body: '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + fs.readFileSync(html, 'utf8') + '</body></html>', contentType: 'text/html', headers: {'Content-Security-Policy': CSP}});
    if (!THREE_DIR && u.startsWith('https://cdn.jsdelivr.net/')) return r.continue();
    return r.abort();
  });
  const t0 = Date.now(); await p.goto('http://level/');
  try { await p.waitForFunction(() => typeof window.lookFrom === 'function', null, {timeout: 90000}); } catch (e) { log.errors.push('viewer did not finish loading: ' + e.message); }
  log.load_seconds = (Date.now() - t0) / 1000;
  await p.addStyleTag({content: '#hud,#stick,#vert,#jumpb,#info,#sel{display:none!important}'});
  for (const v of views) {
    try {
      await p.evaluate(v => window.lookFrom(...v.eye, ...v.target, v.fov || 60), v); await p.waitForTimeout(v.wait || 500);
      const f = path.join(outDir, v.name + '.png'); await p.screenshot({path: f}); log.views.push({name: v.name, file: f});
    } catch (e) { log.errors.push(`${v.name}: ${e.message}`); }
  }
  log.renderer = await p.evaluate(() => { const c = document.createElement('canvas').getContext('webgl2'); const d = c && c.getExtension('WEBGL_debug_renderer_info'); return d ? c.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'unknown'; });
  fs.writeFileSync(path.join(outDir, 'render_log.json'), JSON.stringify(log, null, 1)); await b.close();
  console.log(JSON.stringify({views: log.views.length, errors: log.errors.length, load_seconds: log.load_seconds, renderer: log.renderer}));
})();
