"""Manual harness for the Blender ``edit`` slot (``tentacle/slots/blender/edit.py``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/edit_slot_check.py

Drives the real ``Edit`` slot methods with stubbed sb/widget objects (the slot's Qt/UI layer
can't load headless): Mesh-Cleanup option routing, mode-aware Delete-Selected (FACE vs VERT
dispatch — deleting by VERT in face mode would nuke neighboring faces), Create-Primitive and
Convert list handlers, and the cmb000 Transfer menu (UVs / Vertex Colors / Vertex Group
Weights / Custom Normals / Material Slots — real per-vertex/per-loop data copied source-object
-> target-object via native Data-Transfer, not just "no exception").
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


def _op_exists(module, name):
    """hasattr(bpy.ops.<module>, name) is NOT a reliable existence check -- bpy.ops lazily
    constructs a wrapper for any attribute name asked of it, so hasattr returns True even for
    operator ids that don't really exist. get_rna_type() is the only reliable check."""
    import bpy

    op = getattr(getattr(bpy.ops, module, None), name, None)
    if op is None:
        return False
    try:
        op.get_rna_type()
    except Exception:
        return False
    return True


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


def list_item(text, parent=""):
    return NS(item_text=lambda: text, parent_item_text=lambda: parent)


try:
    import bpy
    import blendertk as btk
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.blender.edit import Edit

    slot = make_slot(Edit)

    # list000 Create Primitive: every mapped operator exists on bpy.ops.mesh
    missing = [
        f"{cat}/{label}"
        for cat, items in Edit._PRIMITIVES.items()
        for label, op in items.items()
        if not _op_exists("mesh", op)
    ]
    check("list000 primitive ops all exist", missing == [], f"missing={missing}")

    # list000 creates a cube
    reset()
    slot.list000(list_item("Cube", "Polygon"))
    check("list000 'Cube' creates a mesh object",
          len(bpy.data.objects) == 1 and bpy.data.objects[0].type == "MESH",
          f"objects={[o.name for o in bpy.data.objects]}")

    # list000 invoked while the user is in Edit Mode on an unrelated mesh: unlike Maya's
    # primitive commands (always create a new DAG node regardless of component-select mode),
    # Blender's mesh/curve/surface primitive-add ops MERGE into the currently-edited mesh
    # instead of making a new object when called from Edit Mode (verified live) -- list000 must
    # force Object Mode first so "click Create -> get a new object" holds here too.
    reset()
    bpy.ops.mesh.primitive_plane_add()  # 4 verts
    other = bpy.context.active_object
    v0 = len(other.data.vertices)
    bpy.ops.object.mode_set(mode="EDIT")
    slot.list000(list_item("Cube", "Polygon"))
    other.update_from_editmode()
    check(
        "list000 forces Object Mode so Create doesn't merge into the edited mesh",
        bpy.context.object.mode == "OBJECT" and len(other.data.vertices) == v0
        and len(bpy.data.objects) == 2,
        f"mode={bpy.context.object.mode} plane_verts={v0}->{len(other.data.vertices)} "
        f"objects={[o.name for o in bpy.data.objects]}",
    )

    # list001 Convert: bezier circle -> Mesh
    reset()
    bpy.ops.curve.primitive_bezier_circle_add()
    o = bpy.context.active_object
    slot.list001(list_item("Mesh"))
    check("list001 'Mesh' converts curve -> MESH", o.type == "MESH", f"type={o.type}")

    # list000 Create Primitive — NURBS/Curve/Helper/Light/Control categories (parity fix:
    # these were entirely absent before). Every mapped op/preset must exist AND actually
    # create the expected object type when clicked.
    missing = [
        f"Curve/{label}" for label, op in Edit._CURVE_PRIMITIVES.items()
        if not _op_exists("curve", op)
    ] + [
        f"NURBS/{label}" for label, op in Edit._NURBS_SURFACES.items()
        if not _op_exists("surface", op)
    ] + [
        f"Control/{label}" for label, shape in Edit._CONTROLS.items()
        if shape not in btk.Controls.shapes()
    ]
    check("list000 curve/surface ops + control presets all exist", missing == [], f"missing={missing}")

    reset()
    slot.list000(list_item("Sun", "Light"))  # not a real label -> no-op, no crash
    check("list000 unknown Light item is a safe no-op", len(bpy.data.objects) == 0)

    reset()
    slot.list000(list_item("Directional", "Light"))
    o = bpy.data.objects[0] if bpy.data.objects else None
    check("list000 Light/Directional creates a SUN light", o is not None and o.type == "LIGHT"
          and o.data.type == "SUN", f"objects={[ob.name for ob in bpy.data.objects]}")

    reset()
    slot.list000(list_item("Locator", "Helper"))
    o = bpy.data.objects[0] if bpy.data.objects else None
    check("list000 Helper/Locator creates a PLAIN_AXES empty", o is not None and o.type == "EMPTY"
          and o.empty_display_type == "PLAIN_AXES")

    reset()
    n_coll_before = len(bpy.data.collections)
    slot.list000(list_item("Set", "Helper"))
    check("list000 Helper/Set links a new Collection",
          len(bpy.data.collections) == n_coll_before + 1)

    reset()
    slot.list000(list_item("Path", "Curve"))
    o = bpy.data.objects[0] if bpy.data.objects else None
    check("list000 Curve/Path creates a CURVE object", o is not None and o.type == "CURVE")

    reset()
    slot.list000(list_item("Torus", "NURBS"))
    o = bpy.data.objects[0] if bpy.data.objects else None
    check("list000 NURBS/Torus creates a SURFACE object", o is not None and o.type == "SURFACE")

    reset()
    slot.list000(list_item("Circle", "Control"))
    o = bpy.data.objects[0] if bpy.data.objects else None
    check("list000 Control/Circle creates a curve control (wires up blendertk.Controls)",
          o is not None and o.type == "CURVE" and bpy.context.view_layer.objects.active is o)

    # list001 Convert — 2 of the 3 newly-exposed native targets convert a plain MESH source
    # (Point Cloud, Grease Pencil); "Hair Curves" (CURVES) does not — verified live that
    # bpy.ops.object.convert(target="CURVES") on a bare mesh (even one with a hair particle
    # system added but never combed/baked) silently no-ops (FINISHED, object unchanged), matching
    # Blender's own Convert-To menu, which lists all 5 targets unconditionally with no
    # per-source-type graying. So "Hair Curves" is exercised from a source it actually converts:
    # an existing Curve object (Blender's real legacy-Curve -> new-Curves-data upgrade path).
    for label, expect_type in (("Point Cloud", "POINTCLOUD"), ("Grease Pencil", "GREASEPENCIL")):
        reset()
        bpy.ops.mesh.primitive_cube_add()
        o = bpy.context.active_object
        slot.list001(list_item(label))
        check(f"list001 '{label}' converts mesh -> {expect_type}", o.type == expect_type,
              f"type={o.type}")

    reset()
    bpy.ops.curve.primitive_bezier_curve_add()
    o = bpy.context.active_object
    slot.list001(list_item("Hair Curves"))
    check("list001 'Hair Curves' converts a Curve object -> CURVES", o.type == "CURVES",
          f"type={o.type}")

    reset()
    bpy.ops.mesh.primitive_cube_add()
    src = bpy.context.active_object
    bpy.ops.object.select_all(action="DESELECT")
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate_move_linked()  # a real linked duplicate (shared mesh data)
    dup = bpy.context.active_object
    shared_before = dup.data == src.data
    bpy.ops.object.select_all(action="DESELECT")
    dup.select_set(True)
    bpy.context.view_layer.objects.active = dup
    slot.list001(list_item("Instance to Object"))
    check("list001 'Instance to Object' gives the linked duplicate unique data",
          shared_before and dup.data != src.data,
          f"shared_before={shared_before} shared_after={dup.data == src.data}")

    # tb000 Mesh Cleanup option routing (chk024/chk032/chk033/chk028/chk029 + s000)
    reset()
    import bmesh

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bm.verts.ensure_lookup_table()
    bm.verts.new(bm.verts[0].co.copy())  # loose double
    me = bpy.data.meshes.new("M"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Clean", me)
    bpy.context.collection.objects.link(o)
    o.select_set(True); bpy.context.view_layer.objects.active = o
    v0 = len(o.data.vertices)

    def chk(state):
        return NS(isChecked=lambda s=state: s)

    def cmb(data):
        return NS(currentData=lambda d=data: d)

    # tb000 reads cmb_mode/cmb_scope + chk022/023/025 unconditionally (repair mode +
    # object-duplicate scope) plus every _DIAGNOSTIC_CRITERIA checkbox (built into `criteria`
    # before the repair/select branch), even though this repair-mode run never selects by them.
    menu = NS(
        cmb_mode=cmb("repair"), cmb_scope=cmb("selected"),  # Repair mode, Selected scope
        chk022=chk(False), chk023=chk(False),  # skip the object-duplicate branch
        chk025=chk(False),  # skip the overlapping-faces pass
        chk002=chk(False), chk011=chk(False), chk003=chk(False), chk017=chk(False),
        chk010=chk(False), chk013=chk(False), chk014=chk(False), chk015=chk(False),
        s006=NS(value=lambda: 0.00001), s007=NS(value=lambda: 0.00001),
        s008=NS(value=lambda: 0.00001),
        chk024=chk(True), s000=NS(value=lambda: 0.001), chk032=chk(True),
        chk033=chk(True), chk028=chk(True), chk029=chk(False),
    )
    slot.tb000(NS(option_box=NS(menu=menu)))
    # the loose double welds into the corner vert (9 -> 8); nothing loose remains after
    check("tb000 cleanup merges the loose double", len(o.data.vertices) == v0 - 1,
          f"{v0}->{len(o.data.vertices)}")

    # tb000 Select mode must survive bpy.context.window is None (the Qt event-pump state tentacle
    # drives slots in): the reported RuntimeError was _show_problem_components entering Edit Mode
    # via object.mode_set, whose poll reads the *window* context. It now runs under
    # window_context_override (as @_object_mode already did). Repro the window=None state with a
    # real n-gon so find_problem_geometry has something to flag and reveal.
    reset()
    bpy.ops.mesh.primitive_circle_add(vertices=6, fill_type="NGON")  # one 6-gon face
    o = bpy.context.active_object
    o.select_set(True); bpy.context.view_layer.objects.active = o
    sel_menu = NS(
        cmb_mode=cmb("select"), cmb_scope=cmb("selected"),
        chk022=chk(False), chk023=chk(False), chk025=chk(False),
        chk002=chk(True),  # N-Gons — the only active criterion
        chk011=chk(False), chk003=chk(False), chk017=chk(False),
        chk010=chk(False), chk013=chk(False), chk014=chk(False), chk015=chk(False),
        s006=NS(value=lambda: 0.00001), s007=NS(value=lambda: 0.00001),
        s008=NS(value=lambda: 0.00001),
    )
    msgs = []
    slot.sb = NS(message_box=lambda s, *a, **k: msgs.append(s))
    try:
        with bpy.context.temp_override(window=None):  # simulate the Qt event-pump window=None state
            slot.tb000(NS(option_box=NS(menu=sel_menu)))
    finally:
        slot.sb = NS(message_box=lambda *a, **k: None)
    reported = msgs[-1] if msgs else ""
    # tb000 wraps its body in try/except now, so a crash would surface as a "failed" popup rather
    # than an unhandled traceback — assert the SUCCESS summary, and that the reveal reached Edit Mode.
    check("tb000 Select survives window=None (reports success, not failure)",
          bool(msgs) and "failed" not in reported.lower() and "Select" in reported,
          f"msg={reported!r}")
    check("tb000 Select reveal entered Edit Mode under window=None", o.mode == "EDIT",
          f"mode={o.mode}")
    if o.mode != "OBJECT":  # restore for the cases below
        with bpy.context.temp_override(window=bpy.context.window_manager.windows[0]):
            bpy.ops.object.mode_set(mode="OBJECT")

    # tb002 Delete Selected in FACE mode: middle face of a 3x3 grid -> 8 faces remain.
    # (The old VERT-typed delete removed the face's verts, nuking all 8 neighbors too.)
    reset()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=3, y_subdivisions=3)
    o = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(o.data)
    bm.faces.ensure_lookup_table()
    center = min(bm.faces, key=lambda f: f.calc_center_median().length)
    center.select_set(True)
    bmesh.update_edit_mesh(o.data)
    slot.tb002(None)
    bpy.ops.object.mode_set(mode="OBJECT")
    check("tb002 FACE-mode delete keeps neighbors (9->8)", len(o.data.polygons) == 8,
          f"faces={len(o.data.polygons)}")

    # tb002 in OBJECT mode deletes the selected object
    reset()
    bpy.ops.mesh.primitive_cube_add()
    slot.tb002(None)
    check("tb002 object-mode delete removes object", len(bpy.data.objects) == 0,
          f"objects={len(bpy.data.objects)}")

    # tb004 Object Lock — Blender analogue of Maya node lock: toggle hide_select (make
    # objects unselectable). Lock acts on the selection; Unlock clears every object.
    def lock_widget(text):
        return NS(option_box=NS(menu=NS(cmb_lock=NS(currentText=lambda t=text: t))))

    reset()
    bpy.ops.mesh.primitive_cube_add()
    a = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    b = bpy.context.active_object
    bpy.ops.object.select_all(action="DESELECT")
    a.select_set(True)
    b.select_set(True)
    slot.tb004(lock_widget("Lock Objects"))
    check("tb004 Lock makes the selection unselectable (hide_select) and deselects it",
          a.hide_select and b.hide_select and not a.select_get(),
          f"a.hide_select={a.hide_select} b.hide_select={b.hide_select} a.selected={a.select_get()}")

    # a third, unlocked object present: Unlock must clear hide_select on ALL objects (a locked
    # object can't be selected to unlock it individually).
    bpy.ops.mesh.primitive_cube_add(location=(6, 0, 0))
    slot.tb004(lock_widget("Unlock Objects"))
    check("tb004 Unlock clears hide_select on every object",
          not any(o.hide_select for o in bpy.data.objects),
          f"still_locked={[o.name for o in bpy.data.objects if o.hide_select]}")

    # Lock with nothing selected is a guarded no-op (warns, changes nothing).
    reset()
    bpy.ops.mesh.primitive_cube_add()
    only = bpy.context.active_object
    bpy.ops.object.select_all(action="DESELECT")
    slot.tb004(lock_widget("Lock Objects"))
    check("tb004 Lock with empty selection is a guarded no-op",
          not only.hide_select, f"hide_select={only.hide_select}")

    # cmb000 Transfer: active object = source, other selected object = target (real data
    # copied per data type, driven through the actual combo dispatch, not the bare bpy.ops call).
    transfer_labels = list(Edit._TRANSFER_OPS)
    transfer_widget = NS(items=transfer_labels)

    def make_transfer_pair():
        bpy.ops.mesh.primitive_cube_add()
        source = bpy.context.active_object
        bpy.ops.mesh.primitive_cube_add()  # coincident cube -> unambiguous nearest-vertex match
        target = bpy.context.active_object
        target.select_set(True)
        source.select_set(True)
        bpy.context.view_layer.objects.active = source
        return source, target

    # UVs
    reset()
    source, target = make_transfer_pair()
    for loop in source.data.uv_layers.active.data:
        loop.uv = (0.123, 0.456)
    before = [tuple(loop.uv) for loop in target.data.uv_layers.active.data]
    slot.cmb000(transfer_labels.index("UVs"), transfer_widget)
    after = [tuple(loop.uv) for loop in target.data.uv_layers.active.data]
    check(
        "cmb000 'UVs' copies real per-loop UV data",
        before != after
        and all(abs(u - 0.123) < 1e-4 and abs(v - 0.456) < 1e-4 for u, v in after),
        f"{before[0]} -> {after[0]}",
    )

    # Vertex Colors
    reset()
    source, target = make_transfer_pair()
    bpy.ops.geometry.color_attribute_add()  # point-domain color attr on the active (source)
    for elem in source.data.color_attributes.active_color.data:
        elem.color = (1.0, 0.0, 0.0, 1.0)
    had_none = len(target.data.color_attributes) == 0
    slot.cmb000(transfer_labels.index("Vertex Colors"), transfer_widget)
    got_layer = len(target.data.color_attributes) > 0
    colors = (
        [tuple(elem.color) for elem in target.data.color_attributes.active_color.data]
        if got_layer else []
    )
    check(
        "cmb000 'Vertex Colors' copies real per-vertex color data",
        had_none and got_layer
        and all(abs(c[0] - 1.0) < 1e-3 and abs(c[1]) < 1e-3 for c in colors),
        f"before=none after={colors[:1]}",
    )

    # Vertex Group Weights
    reset()
    source, target = make_transfer_pair()
    vg = source.vertex_groups.new(name="Grp")
    vg.add(range(len(source.data.vertices)), 0.75, 'REPLACE')
    had_none = len(target.vertex_groups) == 0
    slot.cmb000(transfer_labels.index("Vertex Group Weights"), transfer_widget)
    got_group = "Grp" in target.vertex_groups
    weights = (
        [target.vertex_groups["Grp"].weight(i) for i in range(len(target.data.vertices))]
        if got_group else []
    )
    check(
        "cmb000 'Vertex Group Weights' copies real per-vertex weight data",
        had_none and got_group and all(abs(w - 0.75) < 1e-3 for w in weights),
        f"before=none after={weights[:3]}",
    )

    # Custom Normals
    reset()
    source, target = make_transfer_pair()
    source.data.normals_split_custom_set([(0.0, 0.0, 1.0)] * len(source.data.loops))
    had_none = not target.data.has_custom_normals
    slot.cmb000(transfer_labels.index("Custom Normals"), transfer_widget)
    got_normals = target.data.has_custom_normals
    normals = [tuple(cn.vector) for cn in target.data.corner_normals] if got_normals else []
    check(
        "cmb000 'Custom Normals' copies real per-loop normal data",
        had_none and got_normals
        and all(abs(n[0]) < 0.05 and abs(n[1]) < 0.05 and n[2] > 0.9 for n in normals),
        f"before=none after={normals[:1]}",
    )

    # Material Slots
    reset()
    source, target = make_transfer_pair()
    source.data.materials.append(bpy.data.materials.new("MatA"))
    source.data.materials.append(bpy.data.materials.new("MatB"))
    had_none = len(target.data.materials) == 0
    slot.cmb000(transfer_labels.index("Material Slots"), transfer_widget)
    check(
        "cmb000 'Material Slots' copies real material-slot assignments",
        had_none and list(target.data.materials) == list(source.data.materials),
        f"after={[m.name if m else None for m in target.data.materials]}",
    )

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-EDIT-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
