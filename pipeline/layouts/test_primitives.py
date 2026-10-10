"""Stage 3 test fixture (not a game map): every new primitive + prefab, plus two deliberate completeness faults
(no surrounding world -> void at the edges; a free-standing single-sided sign -> back face) for validate_level --fix.
python3 pipeline/layouts/test_primitives.py && python3 pipeline/build_level.py levels/test_primitives"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import prefabs as P

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "levels", "test_primitives")
o = []
add = lambda **k: o.append(dict(k, rotation=k.get("rotation", [0, 0, 0])))
add(name="Yard_Floor", type="box", material="pf_concrete", position=[0, -0.4, 0], size=[44, 0.4, 44])
for nm, x, z in (("Platform_A", -12, -8), ("Platform_B", 12, -8)):
    add(name=nm, type="group", position=[x, 0, z])
    add(name=nm + "_Base", parent=nm, type="box", material="pf_metal", position=[0, 0, 0], size=[8, 4, 8])
o += P.catwalk("Catwalk_01", start=[-8, 4, -8], end=[8, 4, -8], width=2.4)
o += P.railing_along("Rail_A_North", [-15.5, 4, -11.9], [-8.5, 4, -11.9]) + P.railing_along("Rail_B_North", [8.5, 4, -11.9], [15.5, 4, -11.9])
add(name="Stairs_A", type="stairs", material="pf_grating", position=[-12, 0, -2], rotation=[0, 180, 0], size=[2.4, 4, 4])
o += P.gate("Gate_West", [-21, 0, 6], yaw=90, width=8, height=7, depth=2.5)
add(name="Cliff_North", type="cliff", material="pf_rock", position=[0, 0, -21], size=[40, 14, 6], seed=4)
o += P.rock_cluster("Rocks_East", [16, 0, 10], radius=4, count=5, seed=2)
o += P.pipe_run("Pipe_South", [[-18, 1.2, 19], [6, 1.2, 19], [6, 5.5, 19], [16, 5.5, 19]], radius=0.55)
o += P.machinery_bank("Machines_01", [2, 0, 12], yaw=0, seed=3)
add(name="Beam_Overhead", type="ibeam", material="pf_metal", position=[0, 7.5, 2], size=[20, 0.7, 0.4])
add(name="Elbow_Demo", type="pipe_elbow", material="pf_pipe", position=[-6, 0, 16], size=[1.0, 2.0, 1.0])
add(name="Sign_01", type="panel", material="pf_machine", position=[4, 1.0, 2], size=[3, 2, 0])  # deliberate: single-sided, free-standing
mats = {k: v for k, v in P.DEFAULT_MATERIALS.items()}
L = dict(version=1, units="metres, y-up; position = centre of object's base, in parent space; rotation = degrees XYZ",
         source="Stage 3 primitive/prefab test fixture", sky_color=[0.55, 0.6, 0.65], spawn=dict(position=[0, 0, 8], yaw_deg=0),
         bounds=dict(min=[-22, 0, -22], max=[22, 14, 22]), materials=mats, objects=o,
         walkable=[dict(min=[-21, -21], max=[21, 21], y=0.0), dict(min=[-16, -12], max=[-8, -4], y=4.0), dict(min=[8, -12], max=[16, -4], y=4.0)])
os.makedirs(OUT, exist_ok=True); json.dump(L, open(os.path.join(OUT, "level.json"), "w"), indent=1)
print(len(o), "objects ->", OUT)
