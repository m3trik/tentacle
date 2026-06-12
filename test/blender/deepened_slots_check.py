"""Manual harness for the deepened (stub → real) Blender slots across domains.

Covers the implementations that replaced deferred-message stubs once their Blender primitive
existed: selection list000 (select-by-type), transform cmb002 (object.align), normals b002 +
uv b000 (Data-Transfer), uv b003/b004 (texel density), uv b029 (pin toggle), uv tb022 (cut
hard edges), uv cmb002 (UV transform), polygons b043 (target-weld toggle), animation
tb002/tb004/tb007/tb008 (key spacing / transfer / align / visibility keys).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/deepened_slots_check.py
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


def make_slot(cls, **attrs):
    """Instance without the UI-loading __init__ (headless: no loaded_ui)."""
    slot = cls.__new__(cls)
    slot.sb = NS(message_box=lambda *a, **k: None)
    for k, v in attrs.items():
        setattr(slot, k, v)
    return slot


def reset():
    import bpy

    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def add_cube(name, location=(0, 0, 0)):
    import bpy

    bpy.ops.mesh.primitive_cube_add(location=location)
    o = bpy.context.active_object
    o.name = name
    return o


def option_box(**widgets):
    return NS(option_box=NS(menu=NS(**widgets)))


def chk(state):
    return NS(isChecked=lambda s=state: s)


def spin(v):
    return NS(value=lambda v=v: v)


try:
    import bpy
    import bmesh
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.blender.selection import Selection
    from tentacle.slots.blender.transform import TransformSlots
    from tentacle.slots.blender.normals import Normals
    from tentacle.slots.blender.polygons import PolygonsSlots
    from tentacle.slots.blender.uv import Uv
    from tentacle.slots.blender.animation import Animation
    import blendertk as btk

    # ---- selection list000: select by type --------------------------------------------------
    reset()
    add_cube("M")
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    slot = make_slot(Selection)
    slot.list000(NS(item_text=lambda: "Mesh", sublist=None))
    sel = [o.name for o in bpy.context.selected_objects]
    check("selection list000 'Mesh' selects only meshes", sel == ["M"], f"sel={sel}")
    slot.list000(NS(item_text=lambda: "Empty", sublist=None))
    sel = [o.type for o in bpy.context.selected_objects]
    check("selection list000 'Empty' selects the empty", sel == ["EMPTY"], f"sel={sel}")

    # ---- transform cmb002: align to active --------------------------------------------------
    reset()
    a = add_cube("A", (5, 1, 2))
    b = add_cube("B", (0, 0, 0))  # active
    a.select_set(True)
    slot = make_slot(TransformSlots)
    items = list(TransformSlots._ALIGN_AXES)
    slot.cmb002(items.index("Align X to Active"), NS(items=items))
    bpy.context.view_layer.update()
    check("transform cmb002 aligns X to active",
          abs(a.location.x - b.location.x) < 1e-4 and abs(a.location.y - 1) < 1e-4,
          f"a={tuple(a.location)}")

    # ---- normals b002 / uv b000: data transfer ----------------------------------------------
    reset()
    src = add_cube("Src")
    tgt = add_cube("Tgt", (3, 0, 0))
    # give the source distinct UVs to detect on the target
    btk.move_uvs(src, du=2.0)
    src.select_set(True); tgt.select_set(True)
    bpy.context.view_layer.objects.active = src
    slot = make_slot(Uv)
    slot.b000(None)

    def min_u(o):
        bm = bmesh.new(); bm.from_mesh(o.data); uvl = bm.loops.layers.uv.active
        v = min(loop[uvl].uv.x for f in bm.faces for loop in f.loops)
        bm.free()
        return v

    check("uv b000 transfers UVs (active -> selected)", min_u(tgt) >= 2.0 - 1e-4,
          f"tgt min_u={min_u(tgt):.2f}")

    slot = make_slot(Normals)
    slot.b002()
    check("normals b002 transfers custom split normals", tgt.data.has_custom_normals)

    # ---- uv b003/b004: texel density via the cmb003/s003 inputs ------------------------------
    reset()
    bpy.ops.mesh.primitive_plane_add(size=1.0)  # unit plane: density == map size
    readout = {}
    ui = NS(cmb003=NS(currentText=lambda: "1024"),
            s003=NS(value=lambda: 512.0, setValue=lambda v: readout.__setitem__("d", v)))
    slot = make_slot(Uv, ui=ui)
    slot.b003()
    check("uv b003 reads density into s003", abs(readout.get("d", 0) - 1024.0) < 1e-3,
          f"d={readout.get('d')}")
    slot.b004()  # set to s003.value()=512 against map 1024
    o = bpy.context.active_object
    check("uv b004 sets density from s003", abs(btk.get_texel_density(o, 1024) - 512.0) < 1e-3,
          f"d={btk.get_texel_density(o, 1024):.3f}")

    # ---- uv b029: pin dual-state toggle ------------------------------------------------------
    def pin_count(obj):
        bm = bmesh.new(); bm.from_mesh(obj.data); uvl = bm.loops.layers.uv.active
        n = sum(1 for f in bm.faces for loop in f.loops if loop[uvl].pin_uv)
        bm.free()
        return n

    slot = make_slot(Uv, ui=ui, _b029_pinned=False, _b029_last_selection=None)
    slot.b029(None)
    pinned_after_first = pin_count(o)
    slot.b029(None)
    check("uv b029 toggle: pin then unpin",
          pinned_after_first == 4 and pin_count(o) == 0,
          f"first={pinned_after_first} second={pin_count(o)}")

    # ---- uv tb022: cut hard edges -------------------------------------------------------------
    reset()
    o = add_cube("Hard")  # every cube edge is 90 degrees
    slot = make_slot(Uv, ui=ui)
    slot.tb022(option_box(s017=spin(70.0)))
    seams = sum(1 for e in o.data.edges if e.use_seam)
    check("uv tb022 seams all 12 sharp cube edges", seams == 12, f"seams={seams}")

    # ---- uv cmb002: transform routing ---------------------------------------------------------
    reset()
    bpy.ops.mesh.primitive_plane_add(size=1.0); o = bpy.context.active_object
    btk.move_uvs(o, du=1.0)
    before = min_u(o)
    slot = make_slot(Uv, ui=ui)
    slot.cmb002(0, NS(items=["Flip U", "Flip V", "Rotate 45"]))  # flip about own center
    check("uv cmb002 Flip U keeps bounds (mirror about center)",
          abs(min_u(o) - before) < 1e-4, f"{before} -> {min_u(o)}")

    # ---- uv tb008: mirror UVs -----------------------------------------------------------------
    before = min_u(o)
    slot.tb008(option_box(chk031=chk(True), chk032=chk(False)))  # Mirror U about own center
    check("uv tb008 Mirror U keeps bounds (flip about center)",
          abs(min_u(o) - before) < 1e-4, f"{before} -> {min_u(o)}")

    # ---- polygons b043: target-weld toggle ----------------------------------------------------
    ts = bpy.context.scene.tool_settings
    ts.use_snap = False; ts.use_mesh_automerge = False
    slot = make_slot(PolygonsSlots)
    slot.b043()
    on = ts.use_snap and ts.use_mesh_automerge
    slot.b043()
    check("polygons b043 toggles snap+automerge on/off",
          on and not ts.use_snap and not ts.use_mesh_automerge)

    # ---- animation tb002/tb004/tb007/tb008 ----------------------------------------------------
    reset()
    a = add_cube("A"); b = add_cube("B", (3, 0, 0))

    def key_obj(o, frames):
        for f in frames:
            o.location.x = float(f)
            o.keyframe_insert(data_path="location", index=0, frame=f)

    def key_times(o):
        return sorted(k.co.x for fc in btk.get_fcurves(o) for k in fc.keyframe_points)

    key_obj(a, (10, 20))
    a.select_set(True); b.select_set(True)
    bpy.context.view_layer.objects.active = a

    slot = make_slot(Animation)
    slot.tb002(option_box(s002=spin(15), s003=spin(5)))  # shift keys >= 15 by +5
    check("animation tb002 adjusts spacing", key_times(a) == [10.0, 25.0], f"{key_times(a)}")

    slot.tb004(None)  # transfer active(a) -> b
    check("animation tb004 transfers keys to targets",
          key_times(b) == key_times(a)
          and b.animation_data.action is not a.animation_data.action,
          f"b={key_times(b)}")

    slot.tb005(option_box(chk027=chk(False)))  # add intermediates: 11..24 sampled in
    check("animation tb005 adds intermediate keys", len(key_times(a)) == 16,
          f"n={len(key_times(a))}")
    slot.tb005(option_box(chk027=chk(True)))  # remove -> endpoints only
    check("animation tb005 remove keeps endpoints", key_times(a) == [10.0, 25.0],
          f"{key_times(a)}")

    slot.tb013(option_box(cmb041=NS(currentText=lambda: "Range"),
                          s012=spin(20), s013=spin(30)))
    sel = [k.co.x for fc in btk.get_fcurves(a) for k in fc.keyframe_points
           if k.select_control_point]
    check("animation tb013 selects keys in range", sel == [25.0], f"sel={sel}")

    for k in [k for fc in btk.get_fcurves(a) for k in fc.keyframe_points]:
        k.select_control_point = True
    slot.tb007(option_box(chk013=chk(True)))  # align all selected to earliest (10)
    # co-located keys on one fcurve merge — a single key at the target is the correct result
    check("animation tb007 aligns selected keys (merged at target)",
          key_times(a) == [10.0], f"{key_times(a)}")

    slot.tb008(option_box(chk015=chk(False)))  # key hidden at current frame
    vis = [fc.data_path for fc in btk.get_fcurves(a) if fc.data_path.startswith("hide_")]
    check("animation tb008 keys visibility", sorted(vis) == ["hide_render", "hide_viewport"]
          and a.hide_render, f"vis={vis}")

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-DEEPENED-SLOTS===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
