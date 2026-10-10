"""Stage 7: ONE COMMAND from scene spec to validated, previewed, packaged level.

  python3 pipeline/generate.py levels/<name>/scene_spec.json [--max-passes N] [--no-render] [--force] [--fast]

Claude's part (needs judgement, done BEFORE this command - see GENERATE.md):
  references.py split/plan/grid -> look at the panels -> write levels/<name>/scene_spec.json
This command's part (deterministic CPU, reproducible from the spec):
  1. validate the spec (scene_spec.py)                     5. headless renders -> checks/views/contact_sheet.jpg
  2. spec -> level.json (spec_to_level.py, keeps edits)    6. final checks report (checks/report.json + .md)
  3. build: level.glb, sky, background, effects, mobile    7. self-contained previews dist/<name>/preview*.html
  4. refine loop: checks -> safe fixes -> rebuild (bounded) 8. export package dist/<name>/<name>.zip (+ validation)
Writes levels/<name>/checks/summary.md. Claude then LOOKS at the contact sheet, compares it with the reference and
applies targeted edits (edit_level.py) - a regenerate with the same spec keeps those edits.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def step(name, fn, log):
    t = time.time(); print(f"== {name}", flush=True); r = fn(); log.append(dict(step=name, seconds=round(time.time() - t, 1))); return r


def main(spec_path, max_passes=None, render=True, force=False, fast=False):
    import spec_to_level, refine, checks, package
    d = os.path.dirname(os.path.abspath(spec_path)); name = os.path.basename(d); log = []; t0 = time.time()
    _, summ = step("spec -> level.json", lambda: spec_to_level.run(spec_path, d, force=force, verbose=False), log)
    step("build (glb, sky, background, effects, mobile)", lambda: subprocess.run([sys.executable, os.path.join(HERE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL), log)
    R = step("refine (checks -> safe fixes)", lambda: refine.refine(d, 0 if fast else max_passes, render=render), log) if not fast else None
    if fast: step("checks (fast)", lambda: checks.run(d, fast=True), log)
    rep = json.load(open(os.path.join(d, "checks", "report.json")))
    dist = os.path.join(ROOT, "dist", name); os.makedirs(dist, exist_ok=True)

    def previews():
        for mob, f in ((False, "preview.html"), (True, "preview_mobile.html")):
            subprocess.run([sys.executable, os.path.join(HERE, "make_preview.py"), d, json.load(open(spec_path)).get("title", name) + (" (mobile)" if mob else ""),
                            os.path.join(dist, f)] + (["--mobile"] if mob else []), check=True, stdout=subprocess.DEVNULL)
    step("previews", previews, log)
    pk = step("export package", lambda: package.build(d, make_zip=True, verbose=False), log)
    P = rep.get("performance", {}); m = P.get("mobile", {}); nav = rep.get("navigation", {})
    md = [f"# {name}: generation summary", "", f"Spec: {os.path.relpath(spec_path, ROOT)} · {summ['objects']} objects · {summ['materials']} materials · {summ['effects']} effects",
          f"Checks: {'PASSED' if rep['passed'] else 'NOT PASSED'} ({rep['counts']}) · refine passes: {len(R['passes']) if R else 0}",
          f"Mobile ({m.get('profile')}): {m.get('glb_kb')} KB · {m.get('triangles')} tris · {m.get('draw_calls')} draw calls · ~{m.get('visible_draw_calls_est')} visible (estimate) · ~{m.get('tex_mem_gpu_mb_est')} MB GPU textures (estimate)",
          f"Navigation: {nav.get('reachable_area_m2')} m² reachable of {nav.get('standable_area_m2')} m² standable",
          f"Package: {os.path.relpath(pk['package'], ROOT)} ({pk['files']} files, {pk['mb']} MB) valid={pk['valid']}",
          f"Previews: dist/{name}/preview.html, preview_mobile.html · renders: levels/{name}/checks/views/contact_sheet.jpg", "",
          "## Needs Claude's judgement"] + [f"- {i['severity']}: {i['message']}" for i in rep["issues"] if i["severity"] != "info"][:25] + \
         ["- visual comparison of the renders with the reference image(s) (not automatic)", "", "## Generator notes"] + [f"- {n}" for n in summ.get("notes", [])] + \
         ["", "## Timing"] + [f"- {s['step']}: {s['seconds']} s" for s in log] + [f"- total: {round(time.time() - t0, 1)} s"]
    open(os.path.join(d, "checks", "summary.md"), "w").write("\n".join(md) + "\n"); print("\n".join(md))
    return rep


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    mp = int(sys.argv[sys.argv.index("--max-passes") + 1]) if "--max-passes" in sys.argv else None
    if mp is not None: a = [x for x in a if x != str(mp)]
    rep = main(a[0], mp, render="--no-render" not in sys.argv, force="--force" in sys.argv, fast="--fast" in sys.argv)
    sys.exit(0 if rep["passed"] else 1)
