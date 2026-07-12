"""Manual harness for the Blender ``uv`` slot (``tentacle/slots/blender/uv.py``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/uv_slot_check.py

Drives the real ``Uv`` slot methods with a stubbed option-box menu (mirrors the fake widget
idiom in ``edit_slot_check.py`` / ``rendering_slot_check.py``) but everything downstream is live
``bpy``/bmesh state — this proves the widget objectNames the option boxes expose (tb000's
cmb009/s004, tb004's chk022/s000, tb022's chk026) are wired to the real underlying geometry
change, not just present in the .ui. (uv tb005/tb006/tb008 Straighten/Distribute/Mirror moved to
the blendertk shell_xform panel and are covered there.)
"""
import sys
import os
import traceback
from pathlib import Path
from types import SimpleNamespace as NS

MONO = Path(__file__).resolve().parents[3]
for pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    p = str(MONO / pkg)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("QT_API", "pyside6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lines = []


def check(name, cond, detail=""):
    lines.append(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")


def make_slot(cls):
    """Instance without the UI-loading __init__ (headless: no loaded_ui)."""
    slot = cls.__new__(cls)
    slot.sb = NS(message_box=lambda *a, **k: None)
    return slot


def reset():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def chk(state):
    return NS(isChecked=lambda s=state: s)


def spin(v):
    return NS(value=lambda x=v: x)


def combo(text="", data=None):
    return NS(currentText=lambda t=text: t, currentData=lambda d=data: d)


def option_box(menu):
    return NS(option_box=NS(menu=menu))


try:
    import bpy
    import bmesh
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt for the slot imports
    from tentacle.slots.blender.uv import Uv

    slot = make_slot(Uv)

    def uv_bounds(o):
        bm = bmesh.new()
        bm.from_mesh(o.data)
        uvl = bm.loops.layers.uv.active
        us = [loop[uvl].uv.x for f in bm.faces for loop in f.loops]
        vs = [loop[uvl].uv.y for f in bm.faces for loop in f.loops]
        bm.free()
        return min(us), max(us), min(vs), max(vs)

    def quads_object(uv_rects, name="UVQuads"):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        for n, (u0, v0, u1, v1) in enumerate(uv_rects):
            x = n * 3.0
            verts = [bm.verts.new((x + dx, dy, 0.0)) for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1))]
            face = bm.faces.new(verts)
            for loop, (lu, lv) in zip(face.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                loop[uvl].uv = (lu, lv)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(o)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        return o

    # ---- tb000 Pack UVs: s004 target-UDIM tile shifts the packed 0-1 layout into that tile
    reset()
    o = quads_object([(0.0, 0.0, 0.3, 0.3), (0.6, 0.6, 0.9, 0.9)])
    menu = NS(
        cmb009=combo(data=0),  # Pre-Scale: Preserve UV (skip the average-islands-scale pre-pass)
        s_pack_margin=spin(0.001), chk_pack_rotate=chk(True), s004=spin(1012),
    )
    slot.tb000(option_box(menu))
    b = uv_bounds(o)
    check(
        "tb000 s004 shifts the packed layout into UDIM 1012 (tile u=1,v=1)",
        1.0 - 1e-3 <= b[0] and b[1] <= 2.0 + 1e-3 and 1.0 - 1e-3 <= b[2] and b[3] <= 2.0 + 1e-3,
        f"bounds={b}",
    )

    # tb000 with the default tile (1001) leaves the pack in the 0-1 square
    reset()
    o = quads_object([(0.0, 0.0, 0.3, 0.3), (0.6, 0.6, 0.9, 0.9)])
    menu = NS(cmb009=combo(data=0), s_pack_margin=spin(0.001), chk_pack_rotate=chk(True), s004=spin(1001))
    slot.tb000(option_box(menu))
    b = uv_bounds(o)
    check(
        "tb000 s004=1001 (default tile) leaves the pack in 0-1",
        -1e-3 <= b[0] and b[1] <= 1.0 + 1e-3,
        f"bounds={b}",
    )

    # tb000 Pre-Scale "Preserve 3D" (cmb009=1) runs an average-islands-scale pre-pass before
    # packing; the result still fits the 0-1 square (proves the new cmb009 branch is wired).
    reset()
    o = quads_object([(0.0, 0.0, 0.3, 0.3), (0.6, 0.6, 0.9, 0.9)])
    menu = NS(cmb009=combo(data=1), s_pack_margin=spin(0.001), chk_pack_rotate=chk(True), s004=spin(1001))
    slot.tb000(option_box(menu))
    b = uv_bounds(o)
    check(
        "tb000 cmb009=Preserve 3D runs the pre-scale pass + packs into 0-1 (new branch wired)",
        -1e-3 <= b[0] and b[1] <= 1.0 + 1e-3 and -1e-3 <= b[2] and b[3] <= 1.0 + 1e-3,
        f"bounds={b}",
    )

    # ---- tb004 Unfold: chk022 Stack Similar + s000 tolerance groups same-size islands
    reset()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube_a = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(3, 0, 0))
    cube_b = bpy.context.active_object
    # a differently-shaped mesh (not just a differently-scaled cube: unwrap normalizes UV
    # space independent of 3D scale, so a bigger cube alone wouldn't produce a dissimilar
    # UV shape) -- an icosphere has a wholly different face count/topology, so its unwrap
    # island(s) can't coincidentally match the cubes' signature.
    bpy.ops.mesh.primitive_ico_sphere_add(location=(6, 0, 0))
    cube_c = bpy.context.active_object
    for c in (cube_a, cube_b, cube_c):
        c.select_set(True)
    bpy.context.view_layer.objects.active = cube_a
    menu = NS(
        cmb_unfold_method=combo("Angle Based"), s_unfold_margin=spin(0.0),
        chk017=chk(False), chk007=chk(False), chk022=chk(True), s000=spin(1.0),
    )
    slot.tb004(option_box(menu))
    bounds_a, bounds_b, bounds_c = uv_bounds(cube_a), uv_bounds(cube_b), uv_bounds(cube_c)
    check(
        "tb004 chk022 Stack Similar groups the two matching-shape cubes together",
        bounds_a == bounds_b, f"a={bounds_a} b={bounds_b}",
    )
    check(
        "tb004 chk022 Stack Similar leaves the dissimilar mesh untouched",
        bounds_c != bounds_a, f"c={bounds_c}",
    )

    # ---- (uv tb005 Straighten / tb008 Mirror were relocated to the blendertk shell_xform panel;
    # their coverage now lives there + in deepened_slots_check.py. The stale slot.tb005/tb008 calls
    # here raised AttributeError on the current Uv slot — removed 2026-07-11.)

    # ---- tb022 Cut Hard Edges: chk026 Include Auto Seams marks extra seams
    reset()
    bpy.ops.mesh.primitive_cube_add()
    o = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bm = bmesh.from_edit_mesh(o.data)
    seams_before = sum(1 for e in bm.edges if e.seam)
    bpy.ops.object.mode_set(mode="OBJECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    menu = NS(
        s017=spin(70), s018=spin(180), chk025=chk(False), chk026=chk(True),
    )
    slot.tb022(option_box(menu))
    bpy.ops.object.mode_set(mode="EDIT")
    bm2 = bmesh.from_edit_mesh(o.data)
    seams_after = sum(1 for e in bm2.edges if e.seam)
    check("tb022 chk026 Include Auto Seams marks new seams", seams_after > seams_before,
          f"{seams_before}->{seams_after}")
    bpy.ops.object.mode_set(mode="OBJECT")

except Exception:
    traceback.print_exc()
    lines.append("FAIL unhandled exception")

print("\n".join(lines))
ok = all(l.startswith("OK") for l in lines) and lines
print(f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({sum(1 for l in lines if l.startswith('OK'))}/{len(lines)})")
