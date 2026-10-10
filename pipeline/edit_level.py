"""Stage 6: targeted, undoable edits of level.json by stable object name (+ minimal rebuild).

  python3 pipeline/edit_level.py levels/<name> <command> [args] [--no-build] [--validate]

Objects are addressed by NAME (stable id) or a glob ("Platform_*_01_Base"). Only what the command touches changes.
Commands:
  list [glob]                         names, types, materials, sizes
  info <name>                         one object (+ its children)
  set <name|glob> key=value ...       any field; JSON values; dotted keys: size.0=12  position.1=8  rotation=[0,45,0]
  move <name|glob> dx dy dz           add to position (groups move their children with them)
  resize <name|glob> sx sy sz         multiply size (groups: children sizes AND offsets scale)
  material <name|glob> <material>     assign an existing material
  mat <material> key=value ...        edit/create a material: type=industrial_metal color=[.3,.3,.3] tile_m=4 bevel=.1 ...
  remove <name|glob>                  delete (with children; references in effects/hazards cleaned)
  duplicate <name> <new_name> dx dy dz  deep copy incl. children (child names get new prefix)
  rename <old> <new>                  renames everywhere (children prefixes, parents, effects, hazards, validation)
  add '<json object>'                 add one object (name must be new)
  prefab <type> '<json kwargs>'       catwalk | railing_along | pipe_run | rock_cluster | gate | machinery_bank
  env <path>=<value> ...              environment: sky.preset=alien  atmosphere.fog_end=500  quality=performance
                                      background layers by id/glob: background.Mountains_Far.height=[120,240]
                                      background.Factory_*.detail=3  (env alone: list layers + current sky)
  fx <id> key=value ...               edit an effect;  fx-add '<json>';  fx-remove <id>
  connect <A> <B> [kind] [width]      bridge / ramp / stairs between two walkable areas or platforms (Stage 7; kind auto|bridge|
                                      catwalk|ramp|stairs), placed between their facing edges, slope from config/gameplay.json
  apply '<json list>' | ops.json      several structured edits in one go (schema-checked, see OPS below), one rebuild
  undo                                restore the state before the last edit (snapshots in levels/<name>/.history/)
  history                             list recent edits
Every edit is checked (checks.schema: names, parents, transforms, materials, references) before it is saved; an edit
that would break the level is refused with the reasons and nothing changes.
OPS (apply): {"op":"resize","target":"Platform_North","scale":[2,1,1]}  {"op":"move","target":..,"delta":[x,y,z]}
  {"op":"set","target":..,"values":{"size.0":12}}  {"op":"material","target":..,"material":..}  {"op":"mat","name":..,"values":{..}}
  {"op":"remove","target":..}  {"op":"duplicate","source":..,"name":..,"offset":[x,y,z]}  {"op":"rename","old":..,"new":..}
  {"op":"add","object":{..}}  {"op":"prefab","prefab":..,"args":{..}}  {"op":"env","values":{"sky.preset":"alien"}}
  {"op":"fx","id":..,"values":{..}}  {"op":"fx-add","effect":{..}}  {"op":"fx-remove","id":..}  {"op":"connect","from":..,"to":..,"kind":"auto","width":4}
Rebuild: environment-only edits -> environment + effects + mobile; effects-only -> effects + mobile; otherwise the full
build (level.glb, environment, effects, mobile). --no-build skips it, --validate runs the camera validator afterwards.
"""
import copy, fnmatch, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def load(d): return json.load(open(os.path.join(d, "level.json")))


def save(d, L): json.dump(L, open(os.path.join(d, "level.json"), "w"), indent=1)


def val(s):
    try: return json.loads(s)
    except ValueError: return s


def match(L, pat):
    names = [o["name"] for o in L["objects"]]
    out = [n for n in names if fnmatch.fnmatchcase(n, pat)]
    if not out: raise SystemExit(f"no object matches '{pat}'. Try: list '*{pat.strip('*')}*'")
    return out


def children(L, name):
    out, frontier = [], [name]
    while frontier:
        p = frontier.pop(); kids = [o["name"] for o in L["objects"] if o.get("parent") == p]; out += kids; frontier += kids
    return out


def setpath(obj, key, v):
    parts = key.split("."); cur = obj
    for k in parts[:-1]:
        k = int(k) if isinstance(cur, list) else k
        cur = cur[k] if (isinstance(cur, list) or k in cur) else cur.setdefault(k, {})
    last = parts[-1]
    if isinstance(cur, list): cur[int(last)] = v
    else: cur[last] = v


def snapshot(d, L, cmd):
    h = os.path.join(d, ".history"); os.makedirs(h, exist_ok=True)
    files = sorted(f for f in os.listdir(h) if f.endswith(".json"))
    for f in files[:-29]: os.remove(os.path.join(h, f))  # keep the last 30
    json.dump(dict(time=time.strftime("%Y-%m-%d %H:%M:%S"), cmd=cmd, level=L), open(os.path.join(h, f"{int(time.time() * 1000)}.json"), "w"))


def edit(d, cmd, args):
    L = load(d); before = copy.deepcopy(L); by = {o["name"]: o for o in L["objects"]}; msg = []
    if cmd == "list":
        pat = args[0] if args else "*"
        for o in L["objects"]:
            if fnmatch.fnmatchcase(o["name"], pat):
                print(f'{o["name"]:34s} {o["type"]:10s} {str(o.get("material", "")):16s} size={o.get("size", "")} pos={o.get("position")}' + (f' parent={o["parent"]}' if o.get("parent") else ""))
        return None
    if cmd == "info":
        n = match(L, args[0])[0]; print(json.dumps(by[n], indent=1))
        for c in children(L, n): print("  child:", c, by[c]["type"], by[c].get("material", ""))
        m = by[n].get("material")
        if m: print("material", m, json.dumps(L["materials"].get(m)))
        return None
    if cmd == "history":
        h = os.path.join(d, ".history")
        for f in sorted(os.listdir(h))[-15:] if os.path.isdir(h) else []: x = json.load(open(os.path.join(h, f))); print(x["time"], x["cmd"])
        return None
    if cmd == "undo":
        h = os.path.join(d, ".history"); files = sorted(os.listdir(h)) if os.path.isdir(h) else []
        if not files: raise SystemExit("nothing to undo")
        x = json.load(open(os.path.join(h, files[-1]))); save(d, x["level"]); os.remove(os.path.join(h, files[-1]))
        print("undid:", x["cmd"]); return ("full", before, x["level"])
    if cmd == "set":
        for n in match(L, args[0]):
            for kv in args[1:]:
                k, v = kv.split("=", 1); setpath(by[n], k, val(v))
            msg.append(n)
    elif cmd == "move":
        dx = [float(a) for a in args[1:4]]
        for n in match(L, args[0]): by[n]["position"] = [round(p + q, 3) for p, q in zip(by[n].get("position", [0, 0, 0]), dx)]; msg.append(n)
    elif cmd == "resize":
        s = [float(a) for a in args[1:4]]
        for n in match(L, args[0]):
            o = by[n]
            if o["type"] == "group":
                for c in children(L, n):
                    co = by[c]
                    if by.get(co.get("parent")) is o:  # direct children: scale offset; all descendants: scale size
                        co["position"] = [round(p * k, 3) for p, k in zip(co["position"], s)]
                    if "size" in co: co["size"] = [round(p * k, 3) for p, k in zip(co["size"], s)]
            elif "size" in o: o["size"] = [round(p * k, 3) for p, k in zip(o["size"], s)]
            msg.append(n)
    elif cmd == "material":
        if args[1] not in L["materials"]: raise SystemExit(f"unknown material {args[1]}; existing: {list(L['materials'])} (create with: mat {args[1]} type=... color=[r,g,b])")
        for n in match(L, args[0]):
            if "material" in by[n]: by[n]["material"] = args[1]; msg.append(n)
    elif cmd == "mat":
        m = L["materials"].setdefault(args[0], {"type": "industrial_metal", "color": [0.4, 0.4, 0.4], "tile_m": 2.0})
        for kv in args[1:]: k, v = kv.split("=", 1); setpath(m, k, val(v))
        import materials
        import inspect, re  # + the legacy stylised kinds (named in legacy_texture)
        known = set(materials.PBR) | set(materials.ALIASES) | set(re.findall(r'"([a-z_]+)"', inspect.getsource(materials.legacy_texture)))
        if m["type"] not in known:
            raise SystemExit(f"unknown material type {m['type']}; PBR types: {sorted(materials.PBR)}")
        msg.append("material " + args[0])
    elif cmd == "remove":
        gone = set()
        for n in match(L, args[0]): gone |= {n, *children(L, n)}
        L["objects"] = [o for o in L["objects"] if o["name"] not in gone]
        L["hazards"] = [h for h in L.get("hazards", []) if h not in gone]
        for e in L.get("effects", []):
            for k in ("target",):
                if e.get(k) in gone: e["enabled"] = False
        msg += sorted(gone)
    elif cmd == "duplicate":
        src, new = args[0], args[1]; dx = [float(a) for a in args[2:5]] if len(args) >= 5 else [0, 0, 0]
        if new in by: raise SystemExit(f"{new} already exists")
        group = [src] + children(L, src); clones = []
        for n in group:
            o = copy.deepcopy(by[n]); o["name"] = new + n[len(src):] if n.startswith(src) else f"{new}_{n}"
            if o.get("parent") in group: p = o["parent"]; o["parent"] = new + p[len(src):] if p.startswith(src) else f"{new}_{p}"
            if n == src: o["position"] = [round(p + q, 3) for p, q in zip(o.get("position", [0, 0, 0]), dx)]
            clones.append(o)
        clash = [c["name"] for c in clones if c["name"] in by]
        if clash: raise SystemExit(f"names already exist: {clash}")
        L["objects"] += clones; msg += [c["name"] for c in clones]
        from effects import globmatch  # clones join the effects their source had (e.g. a duplicated toxic fall flows+splashes)
        for e in L.get("effects", []):
            for k in ("targets_glob", "at_targets_glob"):
                if not e.get(k): continue
                add = [c["name"] for c, n in zip(clones, group) if globmatch(n, e[k]) and not globmatch(c["name"], e[k])]
                if add: e[k] = ([e[k]] if isinstance(e[k], str) else e[k]) + add; msg.append(f"effect {e['id']}")
    elif cmd == "rename":
        old, new = args
        if new in by: raise SystemExit(f"{new} already exists")
        ren = {n: new + n[len(old):] for n in [old] + [c for c in children(L, old) if c.startswith(old)]}
        for o in L["objects"]:
            o["name"] = ren.get(o["name"], o["name"])
            if o.get("parent"): o["parent"] = ren.get(o["parent"], o["parent"])
        L["hazards"] = [ren.get(h, h) for h in L.get("hazards", [])]
        for e in L.get("effects", []):
            if e.get("target"): e["target"] = ren.get(e["target"], e["target"])
            if e.get("area_from"): e["area_from"] = ren.get(e["area_from"], e["area_from"])
        v = L.get("validation", {}); v["ignore_objects"] = [ren.get(x, x) for x in v.get("ignore_objects", [])]
        msg += [f"{a} -> {b}" for a, b in ren.items()]
    elif cmd == "add":
        o = json.loads(args[0])
        if o["name"] in by: raise SystemExit(f"{o['name']} already exists")
        o.setdefault("rotation", [0, 0, 0]); L["objects"].append(o); msg.append(o["name"])
    elif cmd == "prefab":
        import prefabs
        save(d, L); snapshot(d, before, "prefab " + " ".join(args)); prefabs.add_to_level(d, args[0], json.loads(args[1]))
        return ("full", before, load(d))
    elif cmd == "env":
        env = L.setdefault("environment", {})
        if not args:
            print("sky:", json.dumps(env.get("sky")), " quality:", env.get("quality"), " atmosphere:", json.dumps(env.get("atmosphere", {})))
            for l in env.get("background", []): print(" ", json.dumps(l))
            return None
        for kv in args:
            k, v = kv.split("=", 1); parts = k.split(".")
            if parts[0] == "background" and len(parts) > 2:  # address background layers by id (or glob: Factory_*)
                lays = [l for l in env.get("background", []) if fnmatch.fnmatchcase(l["id"], parts[1])]
                if not lays: raise SystemExit(f"no background layer '{parts[1]}': {[l['id'] for l in env.get('background', [])]}")
                for lay in lays: setpath(lay, ".".join(parts[2:]), val(v))
            else: setpath(env, k, val(v))
            msg.append("environment." + k)
    elif cmd in ("fx", "fx-add", "fx-remove"):
        fx = L.setdefault("effects", [])
        if cmd == "fx-add":
            e = json.loads(args[0])
            if any(x["id"] == e["id"] for x in fx): raise SystemExit(f"effect {e['id']} exists")
            fx.append(e)
        elif cmd == "fx-remove": L["effects"] = [x for x in fx if x["id"] != args[0]]
        else:
            e = next((x for x in fx if x["id"] == args[0]), None)
            if e is None: raise SystemExit(f"no effect '{args[0]}': {[x['id'] for x in fx]}")
            for kv in args[1:]: k, v = kv.split("=", 1); setpath(e, k, val(v))
        msg.append("effects " + " ".join(args[:1]))
    elif cmd == "connect":
        msg += connect(L, args[0], args[1], args[2] if len(args) > 2 else "auto", float(args[3]) if len(args) > 3 else None)
    else:
        raise SystemExit(__doc__)
    problems = [i["message"] for i in _schema_errors(L)]
    if problems: raise SystemExit("edit refused (level would be invalid):\n  " + "\n  ".join(problems[:12]))
    snapshot(d, before, cmd + " " + " ".join(args)); save(d, L)
    print("changed:", ", ".join(msg[:12]) + (f" (+{len(msg) - 12} more)" if len(msg) > 12 else ""))
    scope = "env" if cmd == "env" else "fx" if cmd.startswith("fx") else "full"
    return (scope, before, L)


def _schema_errors(L):
    from checks import schema
    I = []; schema(L, I); return [i for i in I if i["severity"] == "error"]


def _area(L, name):
    """Walkable area (generator rect) or an object's footprint -> pseudo platform {id, center, size, top, shape}."""
    w = next((w for w in L.get("walkable", []) if w.get("name") == name), None)
    if w: return dict(id=name, center=[(w["min"][0] + w["max"][0]) / 2, (w["min"][1] + w["max"][1]) / 2], size=[w["max"][0] - w["min"][0], w["max"][1] - w["min"][1]], top=w["y"], shape="rect")
    from checks import world_positions
    by = {o["name"]: o for o in L["objects"]}
    if name not in by: raise SystemExit(f"connect: no walkable area or object '{name}' (areas: {[w.get('name') for w in L.get('walkable', [])][:20]})")
    o = by[name]; kids = [k for k in by.values() if k.get("parent") == name and k.get("size")] if o["type"] == "group" else [o]
    wp = world_positions(L); xs, zs, ys, ws, ds = [], [], [], [], []
    for k in kids:
        p = wp[k["name"]]; xs.append(p[0]); zs.append(p[2]); ys.append(p[1] + k["size"][1]); ws.append(k["size"][0]); ds.append(k["size"][2])
    return dict(id=name, center=[sum(xs) / len(xs), sum(zs) / len(zs)], size=[max(ws), max(ds)], top=max(ys), shape="rect")


def connect(L, a, b, kind="auto", width=None):
    """Adds a connection (architecture.connection) between two areas; missing role materials are added from the theme."""
    import architecture as A
    from gameplay import load_gameplay
    pa, pb = _area(L, a), _area(L, b); G = load_gameplay(None, L)
    theme = L.get("generator", {}).get("theme", "industrial"); spec = dict(theme=theme, detail=L.get("generator", {}).get("detail", "medium"), materials={"variation": False})
    ctx = A.Ctx(spec, G); ctx.names = {o["name"] for o in L["objects"]}; cid = f"Link_{a}_{b}"
    ctx.element = (cid, "inferred")
    fy = min([o["size"][1] for o in L["objects"] if o["name"] in L.get("hazards", [])] or [0.0])
    c = dict(id=cid, kind=kind, **({"width": width} if width else {}))
    A.connection(ctx, c, pa, pb, fy)
    if not ctx.objects: raise SystemExit(f"connect: nothing to add ({'; '.join(ctx.notes) or 'areas touch'})")
    for r in ctx.roles:
        if r not in L["materials"]: L["materials"][r] = A.role_material(theme if theme in A.THEMES else "industrial", r)
    L["objects"] += ctx.objects; L.setdefault("walkable", []).extend(w for w in ctx.walkable)
    return [o["name"] for o in ctx.objects] + ctx.notes


OPS = {"set": (["target", "values"], lambda o: [o["target"]] + [f"{k}={json.dumps(v)}" for k, v in o["values"].items()]),
       "move": (["target", "delta"], lambda o: [o["target"]] + [str(v) for v in o["delta"]]),
       "resize": (["target", "scale"], lambda o: [o["target"]] + [str(v) for v in o["scale"]]),
       "material": (["target", "material"], lambda o: [o["target"], o["material"]]),
       "mat": (["name", "values"], lambda o: [o["name"]] + [f"{k}={json.dumps(v)}" for k, v in o["values"].items()]),
       "remove": (["target"], lambda o: [o["target"]]),
       "duplicate": (["source", "name"], lambda o: [o["source"], o["name"]] + [str(v) for v in o.get("offset", [0, 0, 0])]),
       "rename": (["old", "new"], lambda o: [o["old"], o["new"]]),
       "add": (["object"], lambda o: [json.dumps(o["object"])]),
       "prefab": (["prefab", "args"], lambda o: [o["prefab"], json.dumps(o["args"])]),
       "env": (["values"], lambda o: [f"{k}={json.dumps(v)}" for k, v in o["values"].items()]),
       "fx": (["id", "values"], lambda o: [o["id"]] + [f"{k}={json.dumps(v)}" for k, v in o["values"].items()]),
       "fx-add": (["effect"], lambda o: [json.dumps(o["effect"])]),
       "fx-remove": (["id"], lambda o: [o["id"]]),
       "connect": (["from", "to"], lambda o: [o["from"], o["to"], o.get("kind", "auto")] + ([str(o["width"])] if o.get("width") else []))}


def apply_ops(d, ops):
    """Validate every op first (nothing changes if one is malformed), then apply in order; returns the rebuild scope."""
    errs = []
    if not isinstance(ops, list): raise SystemExit("apply: expected a JSON list of ops")
    for i, o in enumerate(ops):
        if not isinstance(o, dict) or o.get("op") not in OPS: errs.append(f"ops[{i}]: unknown op {o.get('op') if isinstance(o, dict) else o!r}; known: {sorted(OPS)}"); continue
        miss = [k for k in OPS[o["op"]][0] if k not in o]
        if miss: errs.append(f"ops[{i}] ({o['op']}): missing {miss}")
    if errs: raise SystemExit("apply refused:\n  " + "\n  ".join(errs))
    scopes = []
    for o in ops:
        r = edit(d, o["op"], OPS[o["op"]][1](o))
        if r: scopes.append(r[0])
    return "full" if "full" in scopes else "env" if "env" in scopes else "fx" if scopes else None


def rebuild(d, scope):
    py = sys.executable; run = lambda *a: subprocess.run([py, *a], check=True, stdout=subprocess.DEVNULL)
    t = time.time()
    if scope == "env":
        run(os.path.join(HERE, "environment.py"), d); run(os.path.join(HERE, "effects.py"), d); run(os.path.join(HERE, "export_mobile.py"), d)
    elif scope == "fx":
        run(os.path.join(HERE, "effects.py"), d); run(os.path.join(HERE, "export_mobile.py"), d)
    else:
        run(os.path.join(HERE, "build_level.py"), d)
    print(f"rebuilt ({scope}) in {time.time() - t:.1f} s")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) < 2: raise SystemExit(__doc__)
    if a[1] == "apply":
        src = a[2]; ops = json.load(open(src)) if os.path.exists(src) else json.loads(src)
        sc = apply_ops(a[0], ops); r = (sc,) if sc else None
    else: r = edit(a[0], a[1], a[2:])
    if r and r[0] and "--no-build" not in sys.argv:
        rebuild(a[0], r[0])
        if "--validate" in sys.argv: subprocess.run([sys.executable, os.path.join(HERE, "validate_level.py"), a[0]])
