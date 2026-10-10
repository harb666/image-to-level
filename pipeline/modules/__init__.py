"""Stage 9: pluggable structure modules for the scene-spec generator.

Every .py file in this folder is imported once (architecture.py calls load_all()). A file registers builders with

    from modules import structure
    @structure("kind_name", pad=True, needs_size=True, natural=False)
    def kind_name(ctx, s, x, y, z, yaw): ...      # same signature as architecture.STRUCTURES

so adding a file adds new spec "structures" kinds without touching the generator. pad=True: on open terrain the
generator flattens a pad under the footprint and adds a foundation (buildings meet the ground); pad=False: the
module grounds itself (rocks, trees, walls following the slope, bridges).
"""
import importlib, os, pkgutil

INFO = {}
BASE = dict(building=True, tower=True, house=True, stone_tower=True, fountain=True, gate=True, arch=True, machinery=True, tank=True,
            wall=False, pillar=False, lamp=False, crates=False, rocks=False, tree=False, banner=False)


def structure(kind, pad=True, needs_size=False, natural=False, doc="", terrain=None):
    """terrain(s, TR0) -> [terrain features] lets a module shape the ground before it is built (e.g. a tunnel trench)."""
    def deco(fn):
        import architecture as A
        A.STRUCTURES[kind] = fn
        INFO[kind] = dict(pad=pad, needs_size=needs_size, natural=natural, module=fn.__module__.split(".")[-1], terrain=terrain,
                          doc=doc or (fn.__doc__ or "").strip().split("\n")[0])
        return fn
    return deco


def pads(kind):
    return INFO[kind]["pad"] if kind in INFO else BASE.get(kind, True)


_loaded = False


def load_all():
    global _loaded
    if _loaded: return
    _loaded = True
    for m in sorted(pkgutil.iter_modules([os.path.dirname(os.path.abspath(__file__))]), key=lambda m: m.name):
        importlib.import_module("modules." + m.name)
