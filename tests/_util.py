"""Shared test helpers: pipeline/ on sys.path, temp copies of levels, synthetic specs."""
import json, os, shutil, sys, tempfile, warnings
warnings.simplefilter("ignore", ResourceWarning)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PIPE = os.path.join(ROOT, "pipeline")
if PIPE not in sys.path: sys.path.insert(0, PIPE)
FULL = os.environ.get("QUICK") != "1"  # QUICK=1 skips the slow builds / camera validation / headless renders


def tmp_level(src=None, name="lvl"):
    d = os.path.join(tempfile.mkdtemp(prefix="i2l_"), name)
    if src: shutil.copytree(os.path.join(ROOT, "levels", src), d, ignore=shutil.ignore_patterns(".history", "checks", "references"))
    else: os.makedirs(d)
    return d


def small_spec(**over):
    """Synthetic 30x30 hazard arena: A (centre) - B (east, bridge) - C (north, ramp, a bit higher); D (west) is high and NOT connected."""
    s = {"spec_version": 1, "name": "synthetic", "title": "Synthetic test arena", "theme": "industrial", "detail": "low",
         "interpretation": {"summary": "synthetic fixture", "visible": ["n/a"], "inferred": ["everything"]},
         "arena": {"shape": "rect", "size": [30, 30], "floor": {"kind": "hazard", "y": 1.0}, "walls": {"height": 9, "thickness": 2}},
         "platforms": [{"id": "A", "center": [0, 0], "size": [8, 8], "top": 4},
                       {"id": "B", "center": [10, 0], "size": [6, 6], "top": 4},
                       {"id": "C", "center": [0, -10], "size": [6, 6], "top": 5.0},
                       {"id": "D", "center": [-10, 0], "size": [5, 5], "top": 8}],
         "connections": [{"id": "Br_AB", "from": "A", "to": "B"}, {"id": "Ln_AC", "from": "A", "to": "C"}],
         "structures": [{"id": "Mast", "kind": "tower", "on": "A", "size": [2, 6, 2], "decor": []}],
         "atmosphere": {"sky": "overcast"}, "background": {"mountains": "far", "factories": 0, "skyline": False, "spires": False},
         "effects": "auto", "spawns": [{"id": "spawn", "on": "B"}], "profile": "performance", "refine": {"max_passes": 2}}
    s.update(over); return s


def write_spec(d, spec):
    p = os.path.join(d, "scene_spec.json"); json.dump(spec, open(p, "w"), indent=1); return p
