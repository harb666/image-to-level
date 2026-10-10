// iPhone-sized preview check (artifact-like CSP): loads, tap-identifies an object, issue overlay button, jump button.
const path = require('path'), fs = require('fs');
let chromium; try { ({chromium} = require('playwright')); } catch (e) { ({chromium} = require('/opt/node22/lib/node_modules/playwright')); }
const html = process.argv[2]; const THREE = path.join(__dirname, '..', 'pipeline', 'render', 'node_modules', 'three');
const CSP = "default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'unsafe-inline'; img-src data:; connect-src 'none'";
(async () => {
  const b = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader']}); const errors = [];
  const p = await b.newPage({viewport: {width: 390, height: 844}, deviceScaleFactor: 2, isMobile: true, hasTouch: true});
  p.on('pageerror', e => errors.push(e.message));
  await p.route('**/*', r => { const u = r.request().url();
    if (u.includes('three@0.160.0/')) return r.fulfill({path: path.join(THREE, u.split('three@0.160.0/')[1]), contentType: 'application/javascript'});
    if (u === 'http://art/') return r.fulfill({body: '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + fs.readFileSync(html, 'utf8') + '</body></html>', contentType: 'text/html', headers: {'Content-Security-Policy': CSP}});
    return r.abort(); });
  await p.goto('http://art/'); await p.waitForFunction(() => typeof window.lookFrom === 'function', null, {timeout: 120000});
  await p.evaluate(() => window.setMode(4)); await p.waitForTimeout(800);
  await p.evaluate(() => window.pickAt(195, 422)); await p.waitForTimeout(300);
  const picked = await p.evaluate(() => !document.getElementById('sel').hidden && document.querySelector('#sel h3') ? document.querySelector('#sel h3').textContent : '');
  const issues = await p.evaluate(() => { const b = document.getElementById('issb'); return b.hidden ? 0 : (window.ISSUES || []).length; });
  await p.evaluate(() => window.setMode(0)); const jump = await p.evaluate(() => !document.getElementById('jumpb').hidden);
  console.log(JSON.stringify({errors, picked, issues_button: issues, jump_visible: jump})); await b.close();
})();
