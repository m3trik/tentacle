"""Manual harness for the Blender ``uv`` slot (``tentacle/slots/blender/uv.py``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/uv_slot_check.py

Drives the real ``UvSlots`` slot methods with a stubbed option-box menu (mirrors the fake widget
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
    import contextlib

    slot = cls.__new__(cls)
    # progress(): the footer task marquee the long UV slots wrap their engine call in.
    slot.sb = NS(
        message_box=lambda *a, **k: None,
        progress=lambda *a, **k: contextlib.nullcontext(lambda *a, **k: True),
    )
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
    from tentacle.slots.blender.uv import UvSlots

    slot = make_slot(UvSlots)

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
        cmb015=combo(data=(1.0, 1.0)),  # Tile Coverage: Full
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
    menu = NS(cmb009=combo(data=0), s_pack_margin=spin(0.001), chk_pack_rotate=chk(True), s004=spin(1001),
                cmb015=combo(data=(1.0, 1.0)))
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
    menu = NS(cmb009=combo(data=1), s_pack_margin=spin(0.001), chk_pack_rotate=chk(True), s004=spin(1001),
                cmb015=combo(data=(1.0, 1.0)))
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

    # ---- b000 Source: All But Active / Auto -- a target JOINED from its sources.
    # Pairing runs the real btk engine (pair_sources / find_combined); only
    # TextureTransfer.transfer is captured, and transfer_uvs counted.
    import blendertk as btk

    captured, uv_calls, messages, names = [], [], [], []

    class Capturing(btk.TextureTransfer):
        def transfer(self, targets, source=None, **kwargs):
            captured.append(([t.name for t in targets], [s.name for s in source or []]))
            names.append(kwargs.get("output_name"))
            return {}

    real_tt, real_uvs = btk.TextureTransfer, btk.transfer_uvs
    btk.TextureTransfer = Capturing
    btk.transfer_uvs = lambda *a, **k: uv_calls.append(a)
    slot.sb.message_box = lambda *a, **k: messages.append(a[0] if a else "")

    def text(s):
        return NS(text=lambda v=s: v)

    def b000_menu(mode, transfer="textures", name="hero"):
        return NS(
            cmb_tt_source=combo(data=mode), cmb014=combo(data="order"),
            cmb_tt_transfer=combo(data=transfer), t_tt_name=text(name), t_tt_src_uvset=text(""),
            t_tt_dst_uvset=text(""), t_tt_output=text(""), cmb025=combo(data=0),
            cmb026=combo(data=2), s025=spin(-1), chk050=chk(True),
        )

    def joined_scene():
        """srcA (cube), srcB (sphere) and 'comb' = B joined with A (B active)."""
        reset()
        bpy.ops.mesh.primitive_cube_add()
        a = bpy.context.active_object
        a.name = "srcA"
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4, location=(3, 0, 0))
        b = bpy.context.active_object
        b.name = "srcB"
        copies = []
        for o in (b, a):
            c = o.copy()
            c.data = o.data.copy()
            bpy.context.collection.objects.link(c)
            copies.append(c)
        with bpy.context.temp_override(active_object=copies[0], selected_editable_objects=copies):
            bpy.ops.object.join()
        copies[0].name = "comb"
        return a, b, copies[0]

    def select(objs, active):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = active

    try:
        a, b, c = joined_scene()
        select([a, b, c], active=c)
        slot.b000(option_box(b000_menu("last")))
        check("b000 All But Active: the active mesh takes every other mesh's maps",
              captured == [(["comb"], ["srcA", "srcB"])], f"{captured} {messages[-1:]}")

        del captured[:]
        select([a, b, c], active=c)
        slot.b000(option_box(b000_menu("last", transfer="uvs")))
        check("b000 All But Active refuses the UV pass onto a joined target",
              not uv_calls and "one source per target" in messages[-1], messages[-1])

        del captured[:]
        select([a, b, c], active=a)  # the joined mesh is NOT the active one
        slot.b000(option_box(b000_menu("auto")))
        check("b000 Source: Auto finds the joined target whatever is active",
              captured == [(["comb"], ["srcA", "srcB"])] and "Source: Auto" in messages[-1],
              f"{captured} {messages[-1:]}")

        del captured[:]
        select([a], active=a)
        slot.b000(option_box(b000_menu("auto")))
        check("b000 Source: Auto reads one mesh as its own UV maps",
              captured == [(["srcA"], [])], f"{captured} {messages[-1:]}")

        # A source GROUP (an empty parenting two meshes) made active, a target
        # group of their copies selected: the groups pair mesh to mesh, and a
        # blank Output Name is named after the source group.
        reset()
        groups = {}
        for gname in ("kit_GRP", "out_GRP"):
            root = bpy.data.objects.new(gname, None)
            bpy.context.collection.objects.link(root)
            groups[gname] = root
            for i, part in enumerate(("partA", "partB")):
                bpy.ops.mesh.primitive_cube_add(location=(i * 3, 0, 0))
                o = bpy.context.active_object
                o.name = part
                o.parent = root
        del captured[:], names[:]
        select(list(groups.values()), active=groups["kit_GRP"])
        slot.b000(option_box(b000_menu("first", name="")))
        src_names = sorted(c.name for c in groups["kit_GRP"].children)
        tgt_names = sorted(c.name for c in groups["out_GRP"].children)
        check("b000 First Selected pairs a source group with a target group",
              len(captured) == 1 and sorted(captured[0][1]) == src_names
              and sorted(captured[0][0]) == tgt_names, f"{captured} {messages[-1:]}")
        check("b000 a blank Output Name is named after the source group",
              names == ["kit"], f"{names}")

        # A deselected object stays ACTIVE in Blender. It is no side of the
        # transfer: read as one, it made a mesh nobody picked the source (First,
        # Auto's First) or the TARGET (All But Active). The pick hint fires instead.
        reset()
        meshes = []
        for i, name in enumerate(("selA", "selB", "deselC")):
            bpy.ops.mesh.primitive_cube_add(location=(i * 3, 0, 0))
            o = bpy.context.active_object
            o.name = name
            meshes.append(o)
        for mode, hint in (
            ("first", "Make the source active"),
            ("auto", "Make the source active"),
            ("last", "Make the target mesh active"),
        ):
            del captured[:], uv_calls[:], messages[:]
            select(meshes[:2], active=meshes[2])  # deselC active, not selected
            slot.b000(option_box(b000_menu(mode)))
            check(f"b000 Source {mode}: a deselected active object is no side of it",
                  not meshes[2].select_get() and not captured and not uv_calls
                  and hint in messages[-1], f"{captured} {messages[-1:]}")
    finally:
        btk.TextureTransfer, btk.transfer_uvs = real_tt, real_uvs

except Exception:
    traceback.print_exc()
    lines.append("FAIL unhandled exception")

print("\n".join(lines))
ok = all(line.startswith("OK") for line in lines) and lines
print(f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({sum(1 for line in lines if line.startswith('OK'))}/{len(lines)})")
