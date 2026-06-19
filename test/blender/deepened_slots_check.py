"""Manual harness for the deepened (stub → real) Blender slots across domains.

Covers the implementations that replaced deferred-message stubs once their Blender primitive
existed: selection list000 (select-by-type), transform cmb002 (object.align), normals b002 +
uv b000 (Data-Transfer), uv b003/b004 (texel density), uv b029 (pin toggle), uv tb022 (cut
hard edges), uv cmb002 (UV transform), polygons b043 (target-weld toggle), animation
tb002/tb004/tb007/tb008 (key spacing / transfer / align / visibility keys), transform
chk024/chk025 (constraints -> snap elements), selection cmb005 (one-shot constraints),
rigging cmb002 (Rigify quick rig), nurbs b056 (image tracer), the manager-panel routing,
main list000 (workspace browser = the current .blend's dir contents, files + folders),
editors buttons + list (every entry opens a real editor; no-analogue buttons relabel).

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

    # ---- transform tb004/chk023: increment snap -----------------------------------------------
    slot = make_slot(TransformSlots)
    slot.tb004(option_box(chk021=chk(True), chk022=chk(False)))
    move_on = ts.use_snap and ts.use_snap_translate and not ts.use_snap_scale
    slot.chk023(True, None)
    rot_on = ts.use_snap_rotate
    slot.tb004(option_box(chk021=chk(False), chk022=chk(False)))
    slot.chk023(False, None)
    check("transform tb004/chk023 drive tool-settings snap",
          move_on and rot_on and not ts.use_snap,
          f"move={move_on} rot={rot_on} off={not ts.use_snap}")

    # ---- crease b002: transfer crease (Data-Transfer CREASE) ----------------------------------
    reset()
    src = add_cube("CSrc"); tgt = add_cube("CTgt", (3, 0, 0))
    from tentacle.slots.blender.crease import Crease

    cslot = make_slot(Crease)
    btk.crease_edges(src, amount=10)  # full crease on every edge (object mode)
    src.select_set(True); tgt.select_set(True)
    bpy.context.view_layer.objects.active = src
    cslot.b002(None)
    crease_attr = tgt.data.attributes.get("crease_edge")
    creased = (
        sum(1 for d in crease_attr.data if d.value > 0.99) if crease_attr else 0
    )
    check("crease b002 transfers edge creases", creased == 12, f"creased={creased}")

    # ---- subdivision b028: quad draw = poly build tool ----------------------------------------
    from tentacle.slots.blender.subdivision import Subdivision

    sslot = make_slot(Subdivision)
    sslot.b028()  # headless has no tool context — must not raise (slot catches + messages)
    check("subdivision b028 poly-build activation is safe headless", True)

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

    # ---- transform b002 Un-Freeze (restore_transforms round trip through the slot)
    from tentacle.slots.blender.transform import TransformSlots

    reset()
    o = add_cube("Frozen", location=(4, 0, 0))
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    btk.freeze_transforms(o, location=True, rotation=False, scale=False)
    slot = make_slot(TransformSlots)
    slot.b002()
    check("transform b002 un-freezes (location restored)",
          abs(o.location.x - 4.0) < 1e-4, f"x={o.location.x:.3f}")
    msgs = []
    slot.sb = NS(message_box=msgs.append)
    slot.b002()  # bakes consumed -> nothing-to-restore message
    check("transform b002 reports when nothing stored",
          msgs and "Nothing to restore" in msgs[-1])

    # ---- transform tb001 Scale Connected Edges (slot reads option-box s001)
    reset()
    o = add_cube("Edges")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    import bmesh as _bmesh

    bm = _bmesh.from_edit_mesh(o.data)
    for e in bm.edges:
        e.select = all(abs(v.co.z - 1.0) < 1e-4 for v in e.verts)  # top ring only
    _bmesh.update_edit_mesh(o.data)
    slot = make_slot(TransformSlots)
    slot.tb001(option_box(s001=spin(2.0)))
    bm = _bmesh.from_edit_mesh(o.data)
    top_x = sorted(round(v.co.x, 2) for v in bm.verts if abs(v.co.z - 1.0) < 1e-4)
    check("transform tb001 scales the selected ring", top_x == [-2.0, -2.0, 2.0, 2.0],
          f"{top_x}")
    bpy.ops.object.mode_set(mode="OBJECT")
    msgs = []
    slot.sb = NS(message_box=msgs.append)
    slot.tb001(option_box(s001=spin(2.0)))  # object mode -> nothing scaled message
    check("transform tb001 reports when nothing scaled",
          msgs and "No connected edges" in msgs[-1])

    # ---- polygons b000/b053 extension wrap: factory startup has no LoopTools ->
    #      the wrap-if-present path must point at the extension, not crash
    from tentacle.slots.blender.polygons import PolygonsSlots

    reset()
    msgs = []
    slot = make_slot(PolygonsSlots)
    slot.sb = NS(message_box=msgs.append)
    slot.b000()
    check("polygons b000 points at LoopTools when absent",
          msgs and "LoopTools" in msgs[-1], f"{msgs[-1:]}")
    slot.b053()
    check("polygons b053 points at the edge-flow add-on when absent",
          len(msgs) == 2 and "add-on" in msgs[-1], f"{msgs[-1:]}")

    # ---- polygons tb009 Snap Closest Verts (other mesh snaps onto the ACTIVE)
    reset()
    a = add_cube("A", location=(0.05, 0, 0))
    b = add_cube("B", location=(0, 0, 0))
    a.select_set(True)
    b.select_set(True)
    bpy.context.view_layer.objects.active = b
    slot = make_slot(PolygonsSlots)
    slot.tb009(option_box(s005=spin(0.2)))
    pos_a = sorted(tuple(round(c, 4) for c in (a.matrix_world @ v.co)) for v in a.data.vertices)
    pos_b = sorted(tuple(round(c, 4) for c in (b.matrix_world @ v.co)) for v in b.data.vertices)
    check("polygons tb009 snaps onto the active mesh", pos_a == pos_b)

    # ---- polygons b034 Wedge (edit mode, face + hinge edge)
    reset()
    import bmesh as _bm

    o = add_cube("W")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bm = _bm.from_edit_mesh(o.data)
    for f in bm.faces:
        f.select = False
    for e in bm.edges:
        e.select = False
    top = next(f for f in bm.faces if all(abs(v.co.z - 1.0) < 1e-4 for v in f.verts))
    top.select = True
    next(iter(top.edges)).select = True
    _bm.update_edit_mesh(o.data)
    f0 = len(bm.faces)
    slot = make_slot(PolygonsSlots)
    slot.b034()
    bm = _bm.from_edit_mesh(o.data)
    check("polygons b034 wedges the selected face", len(bm.faces) > f0,
          f"{f0}->{len(bm.faces)}")
    bpy.ops.object.mode_set(mode="OBJECT")

    # ---- display b013 Explode View toggle
    from tentacle.slots.blender.display import DisplaySlots

    reset()
    a = add_cube("A", location=(0.5, 0, 0))
    b = add_cube("B", location=(-0.5, 0, 0))
    a.select_set(True)
    b.select_set(True)
    locs = {o.name: tuple(o.location) for o in (a, b)}
    slot = make_slot(DisplaySlots)
    slot.b013()
    check("display b013 explodes apart", btk.is_exploded([a, b]))
    slot.b013()
    check("display b013 toggles back to the exact locations",
          all(tuple(o.location) == locs[o.name] for o in (a, b))
          and not btk.is_exploded([a, b]))

    # ---- uv tb005/tb006/b030 (shell ops through the slot readers)
    from tentacle.slots.blender.uv import Uv

    def uv_quads(rects, name="Q"):
        bm = _bm.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        for n, (u0, v0, u1, v1) in enumerate(rects):
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

    reset()
    o = uv_quads([(0.0, 0.0, 0.2, 0.2), (0.6, 0.6, 0.8, 0.8)])
    slot = make_slot(Uv)
    slot.b030(None)  # stack
    snap_after_stack = btk.get_uv_coords([o])
    slot.b030(None)  # unstack (same selection -> restore)
    check("uv b030 stack/unstack round-trips",
          btk.get_uv_coords([o])[o.name] != snap_after_stack[o.name]
          and round(btk.get_uv_coords([o])[o.name][0][0], 3) == 0.0)

    reset()
    o = uv_quads([(0.0, 0.0, 0.2, 0.2), (0.2, 0.0, 0.4, 0.2), (0.8, 0.0, 1.0, 0.2)])
    slot = make_slot(Uv)
    slot.tb006(option_box(chk023=chk(True), chk024=chk(False)))
    from blendertk.uv_utils._uv_utils import _uv_islands, _island_bbox_center
    bm = _bm.new()
    bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    centers = sorted(round(_island_bbox_center(isl, uvl)[0], 3) for isl in _uv_islands(bm, uvl))
    bm.free()
    check("uv tb006 distributes shells evenly", centers == [0.1, 0.5, 0.9], f"{centers}")

    reset()
    bpy.ops.mesh.primitive_plane_add()
    o = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bm = _bm.from_edit_mesh(o.data)
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for loop in f.loops:
            if loop[uvl].uv.x > 0.5 and loop[uvl].uv.y < 0.5:
                loop[uvl].uv.y = 0.1
    for e in bm.edges:
        e.select = True
    _bm.update_edit_mesh(o.data)
    slot = make_slot(Uv)
    slot.tb005(option_box(s001=spin(30), chk018=chk(True), chk019=chk(False)))
    bm = _bm.from_edit_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    bottom = sorted(round(l[uvl].uv.y, 3) for f in bm.faces for l in f.loops if l[uvl].uv.y < 0.5)
    check("uv tb005 straightens the skewed edge", bottom == [0.05, 0.05], f"{bottom}")
    bpy.ops.object.mode_set(mode="OBJECT")

    # ---- scene b005 / cameras b007: headless has no window / 3D view -> message, no crash
    from tentacle.slots.blender.scene import SceneSlots
    from tentacle.slots.blender.cameras import Cameras

    reset()
    msgs = []
    slot = make_slot(SceneSlots)
    slot.sb = NS(message_box=msgs.append)
    slot.b005()
    check("scene b005 fails soft without a window", len(msgs) <= 1)

    msgs = []
    slot = make_slot(Cameras)
    slot.sb = NS(message_box=msgs.append)
    slot.b007()
    check("cameras b007 fails soft without a 3D view", len(msgs) == 1, f"{msgs}")

    # ---- transform chk024/chk025: constraints -> snap-to-element ---------------------------
    reset()
    ts = bpy.context.scene.tool_settings
    ts.use_snap = False
    slot = make_slot(TransformSlots, ui=NS(tb003=NS(init_slot=lambda: None)))
    slot.chk024(True, None)
    check("transform chk024 enables EDGE snap",
          ts.use_snap and ts.use_snap_translate and slot._snap_elements() == {"EDGE"},
          f"snap={ts.use_snap} elems={slot._snap_elements()}")
    slot.chk025(True, None)  # single-element like Maya: surface replaces edge
    check("transform chk025 replaces with FACE snap",
          ts.use_snap and slot._snap_elements() == {"FACE"},
          f"elems={slot._snap_elements()}")
    slot.chk025(False, None)
    check("transform constraint off disables snap", not ts.use_snap)

    # ---- selection cmb005: one-shot constraint expansion -----------------------------------
    reset()
    o = add_cube("C5")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.select_mode(type="VERT")
    bm = _bm.from_edit_mesh(o.data)
    bm.verts.ensure_lookup_table()
    bm.verts[0].select = True
    _bm.update_edit_mesh(o.data)
    slot = make_slot(Selection)
    items = ["OFF", "Angle", "Border", "Edge Loop", "Edge Ring", "Shell"]
    slot.cmb005(5, NS(items=items))  # Shell -> whole connected mesh
    bm = _bm.from_edit_mesh(o.data)
    check("selection cmb005 Shell expands to the whole shell",
          all(v.select for v in bm.verts),
          f"selected={sum(v.select for v in bm.verts)}/8")
    slot.cmb005(0, NS(items=items))  # OFF -> no-op, no message
    bpy.ops.object.mode_set(mode="OBJECT")

    # ---- rigging cmb002: Rigify quick rig ---------------------------------------------------
    from tentacle.slots.blender.rigging import Rigging

    reset()
    slot = make_slot(Rigging)
    rig_items = ["Human Meta-Rig", "Basic Human Meta-Rig", "Generate Rig"]
    slot.cmb002(0, NS(items=rig_items))
    meta = bpy.context.view_layer.objects.active
    check("rigging cmb002 adds the human meta-rig",
          meta is not None and meta.type == "ARMATURE",
          f"active={meta and meta.name}")
    slot.cmb002(2, NS(items=rig_items))  # generate on the active meta-rig
    rig = bpy.context.view_layer.objects.active
    check("rigging cmb002 generates the control rig",
          rig is not None and rig.name == "rig" and rig is not meta,
          f"active={rig and rig.name}")
    msgs = []
    reset()
    slot.sb = NS(message_box=msgs.append)
    slot.cmb002(2, NS(items=rig_items))  # nothing active -> message
    check("rigging cmb002 generate without a meta-rig messages", len(msgs) == 1, f"{msgs}")

    # ---- nurbs b056: image tracer resolves real ops -----------------------------------------
    from tentacle.slots.blender.nurbs import Nurbs

    reset()
    msgs = []
    slot = make_slot(Nurbs)
    slot.sb = NS(message_box=msgs.append)
    slot.b056()  # no image empty -> SVG import path (headless: dialog may fail soft)
    check("nurbs b056 svg path resolves (no 'not available')",
          all("not available" not in m for m in msgs), f"{msgs}")
    bpy.ops.object.empty_add(type="IMAGE")
    msgs.clear()
    slot.b056()  # image empty -> trace path
    check("nurbs b056 trace path resolves (no 'not available')",
          all("not available" not in m for m in msgs), f"{msgs}")

    # ---- scene b001 / lighting b000: route to the new manager panels ------------------------
    from tentacle.slots.blender.lighting import Lighting

    shown = []
    mm = NS(marking_menu=NS(show=shown.append))
    slot = make_slot(SceneSlots)
    slot.sb = NS(handlers=mm)
    slot.b001()
    slot = make_slot(Lighting)
    slot.sb = NS(handlers=mm)
    slot.b000()
    check("scene b001 / lighting b000 open the manager panels",
          shown == ["reference_manager", "hdr_manager"], f"{shown}")

    # ---- scene b004: native Outliner window (headless: no GUI window -> fails soft) ---------
    msgs = []
    slot = make_slot(SceneSlots)
    slot.sb = NS(message_box=msgs.append)
    slot.b004()
    check("scene b004 Outliner fails soft headless", len(msgs) <= 1, f"{msgs}")

    # ---- deformation tb001: routes to the curtain panel -------------------------------------
    from tentacle.slots.blender.deformation import Deformation

    shown = []
    slot = make_slot(Deformation)
    slot.sb = NS(handlers=NS(marking_menu=NS(show=shown.append)))
    slot.tb001(None)
    check("deformation tb001 opens the curtain panel", shown == ["curtain"], f"{shown}")

    # ---- main list000: workspace browser = the current .blend's dir CONTENTS ----------------
    # (files + sub-folders, not just sub-folders) — Blender's analogue of Maya's project tree.
    import os as _os
    import shutil as _shutil
    import tempfile as _tempfile
    from tentacle.slots.blender.main import Main

    class _SubStub:
        def __init__(self):
            self.added = []
        def add(self, text, data=None):
            child = _SubItem(text, data)
            self.added.append(child)
            return child

    class _SubItem:
        def __init__(self, text, data):
            self.text, self.data = text, data
            self.sublist = _SubStub()

    proj = _tempfile.mkdtemp(prefix="ws_proj_")
    _os.makedirs(_os.path.join(proj, "textures", "wood"))
    _os.makedirs(_os.path.join(proj, "exports"))
    for fn in ("scene.blend", "ref.png", "notes.txt"):
        open(_os.path.join(proj, fn), "w").close()
    bpy.ops.wm.save_as_mainfile(filepath=_os.path.join(proj, "scene.blend"))

    check("main workspace resolves to the saved .blend's dir",
          btk.get_env_info("workspace") == proj, f"ws={btk.get_env_info('workspace')}")

    slot = make_slot(Main)
    root = _SubStub()
    slot._populate_dir_contents(root, proj, max_depth=2)
    names = [i.text for i in root.added]
    check("workspace lists files alongside folders",
          {"exports", "textures", "scene.blend", "ref.png", "notes.txt"}.issubset(names),
          f"names={names}")
    check("workspace lists folders before files",
          names.index("exports") < names.index("notes.txt"), f"names={names}")
    nested = next((i for i in root.added if i.text == "textures"), None)
    check("workspace recurses sub-folders",
          nested is not None and [c.text for c in nested.sublist.added] == ["wood"],
          f"textures->{nested and [c.text for c in nested.sublist.added]}")

    # restore an unsaved state so we don't leave the temp file as the 'open' doc
    bpy.ops.wm.read_homefile(use_empty=True)
    _shutil.rmtree(proj, ignore_errors=True)

    # ---- editors: every button + list entry opens a REAL editor (no dead links) ------------
    from tentacle.slots.blender.editors import Editors

    valid = set(btk.get_editor_types())
    bad_buttons = {b: e for b, e in Editors._BUTTON_EDITORS.items() if e not in valid}
    check("every editor button opens a real editor", not bad_buttons, f"{bad_buttons}")
    bad_list = [e for items in Editors._EDITORS.values() for e in items if e not in valid]
    check("every editors-list entry opens a real editor", not bad_list, f"{bad_list}")

    # relabel: the five no-analogue Maya buttons show their substitute editor's name
    class _Btn:
        def __init__(self, name):
            self._n, self.text_ = name, None
        def objectName(self):
            return self._n
        def setText(self, t):
            self.text_ = t
        def setToolTip(self, t):
            pass

    eslot = make_slot(Editors)
    relabeled = {}
    for bn in Editors._RELABELED:
        btn = _Btn(bn)
        getattr(eslot, bn + "_init")(btn)
        relabeled[bn] = btn.text_
    check("substituted buttons relabel to their editor",
          relabeled == {b: Editors._BUTTON_EDITORS[b] for b in Editors._RELABELED},
          f"{relabeled}")
    # each substitute editor must be unique across all 14 buttons (distinct from the kept
    # buttons AND from each other) — count==1 in the full value list proves both.
    vals = list(Editors._BUTTON_EDITORS.values())
    subs = [Editors._BUTTON_EDITORS[b] for b in Editors._RELABELED]
    check("each substitute editor is unique among the buttons",
          all(vals.count(e) == 1 for e in subs), f"{subs}")

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-DEEPENED-SLOTS===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
