"""Manual harness for the Edit panel in Blender (``tentacle/slots/edit.py``, one Slots
class for both hosts, over ``blendertk``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/edit_slot_check.py

Drives the real ``EditSlots`` slot methods with stubbed sb/widget objects (the slot's Qt/UI layer
can't load headless) and ``sb.tk`` the real ``blendertk``: Mesh-Cleanup option routing,
mode-aware Delete (FACE vs VERT dispatch — deleting by VERT in face mode would nuke neighboring
faces), the Create and Convert lists, Lock / Unlock, and the Transfer menu (UVs / Vertex Colors /
Vertex Group Weights / Custom Normals / Material Slots — real per-vertex/per-loop data copied
source-object -> target-object via native Data-Transfer, not just "no exception").
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
# A throwaway Blender: keep its settings off the developer's live uitk stores.
from uitk.testing import TestSandbox  # noqa: E402

try:
    TestSandbox.activate()
except ImportError:  # a first launch: tentacle provisions Qt as it imports
    from tentacle import tcl_blender  # noqa: E402, F401

    TestSandbox.activate()
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


def make_sb(messages=None):
    """A stub switchboard: the message box (recorded), the console, and ``tk``."""
    import blendertk as btk

    record = messages.append if messages is not None else (lambda *a, **k: None)
    return NS(
        message_box=lambda s, *a, **k: record(s),
        logger=NS(log_raw=lambda *a, **k: None),
        tk=btk,
    )


def make_slot(cls):
    """Instance without the UI-loading __init__ (headless: no loaded_ui)."""
    slot = cls.__new__(cls)
    slot.sb = make_sb()
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


def chk(state):
    return NS(isChecked=lambda s=state: s)


def cmb(data):
    return NS(currentData=lambda d=data: d)


def spin(value):
    return NS(value=lambda v=value: v)


def cleanup_menu(mode, **checked):
    """tb000's option box: every option the shared slot reads, off unless *checked*."""
    names = (
        "chk002 chk003 chk010 chk011 chk012 chk013 chk014 chk015 chk016 chk017 chk018 "
        "chk022 chk023 chk024 chk025 chk026 chk028 chk029 chk032 chk033"
    ).split()
    menu = {name: chk(checked.get(name, False)) for name in names}
    menu.update(
        cmb_mode=cmb(mode),
        cmb_scope=cmb(checked.get("scope", "selected")),
        s000=spin(checked.get("s000", 0.0001)),
        s006=spin(0.00001),
        s007=spin(0.00001),
        s008=spin(0.00001),
    )
    return NS(option_box=NS(menu=NS(**menu)))


try:
    import bpy
    import blendertk as btk
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.edit import EditSlots

    slot = make_slot(EditSlots)

    # Create: every operator the host's Create list names exists
    missing = [
        f"{group}/{label}"
        for group, table in (
            ("mesh", btk.Primitives._MESHES),
            ("surface", btk.Primitives._SURFACES),
            ("curve", btk.Primitives._CURVES),
        )
        for label, op in table.items()
        if not _op_exists(group, op)
    ]
    check("list000 primitive ops all exist", missing == [], f"missing={missing}")
    offered = {s for s in EditSlots._CONTROL_SHAPES if s in btk.Controls.shapes()}
    check(
        "list000 Control offers Blender's registered shapes (the six it had, at least)",
        {"circle", "square", "diamond", "box", "ball", "arrow"} <= offered,
        f"offered={sorted(offered)}",
    )

    # list000 creates a cube
    reset()
    slot.list000(list_item("Cube", "Polygon"))
    check("list000 'Cube' creates a mesh object",
          len(bpy.data.objects) == 1 and bpy.data.objects[0].type == "MESH",
          f"objects={[o.name for o in bpy.data.objects]}")

    # list000 invoked while the user is in Edit Mode on an unrelated mesh: unlike Maya's
    # primitive commands (always create a new DAG node regardless of component-select mode),
    # Blender's mesh/curve/surface primitive-add ops MERGE into the currently-edited mesh
    # instead of making a new object when called from Edit Mode (verified live) --
    # Primitives.create forces Object Mode first so "click Create -> get a new object" holds.
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

    reset()
    slot.list000(list_item("Sun", "Light"))  # not a real label -> refused, no object
    check("list000 unknown Light item makes nothing", len(bpy.data.objects) == 0)

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
    check("list000 Control/Circle creates a curve control, active",
          o is not None and o.type == "CURVE" and bpy.context.view_layer.objects.active is o)

    # list001 Convert — Point Cloud / Grease Pencil convert a plain MESH source; "Hair Curves"
    # (CURVES) does not (bpy.ops.object.convert(target="CURVES") on a bare mesh silently no-ops,
    # matching Blender's own Convert-To menu), so it is exercised from a Curve object.
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
    btk.CoreUtils.select([src])
    bpy.ops.object.duplicate_move_linked()  # a real linked duplicate (shared mesh data)
    dup = bpy.context.active_object
    shared_before = dup.data == src.data
    btk.CoreUtils.select([dup])
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
    me = bpy.data.meshes.new("M")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("Clean", me)
    bpy.context.collection.objects.link(o)
    btk.CoreUtils.select([o])
    v0 = len(o.data.vertices)
    slot.tb000(cleanup_menu("repair", chk024=True, s000=0.001, chk032=True, chk033=True,
                            chk028=True))
    # the loose double welds into the corner vert (9 -> 8); nothing loose remains after
    check("tb000 cleanup merges the loose double", len(o.data.vertices) == v0 - 1,
          f"{v0}->{len(o.data.vertices)}")

    # tb000 Select mode must survive bpy.context.window is None (the Qt event-pump state tentacle
    # drives slots in): the reported RuntimeError was entering Edit Mode via object.mode_set,
    # whose poll reads the *window* context; the library runs it under window_context_override.
    reset()
    bpy.ops.mesh.primitive_circle_add(vertices=6, fill_type="NGON")  # one 6-gon face
    o = bpy.context.active_object
    btk.CoreUtils.select([o])
    msgs = []
    slot.sb = make_sb(msgs)
    try:
        with bpy.context.temp_override(window=None):  # simulate the Qt event-pump window=None state
            slot.tb000(cleanup_menu("select", chk002=True))  # N-Gons, the only check
    finally:
        slot.sb = make_sb()
    reported = msgs[-1] if msgs else ""
    # a failure surfaces as a "failed" popup rather than a traceback: assert the SUCCESS summary
    check("tb000 Select survives window=None (reports success, not failure)",
          bool(msgs) and "failed" not in reported.lower() and "N-Gons" in reported,
          f"msg={reported!r}")
    check("tb000 Select reveal entered Edit Mode under window=None", o.mode == "EDIT",
          f"mode={o.mode}")
    if o.mode != "OBJECT":  # restore for the cases below
        with bpy.context.temp_override(window=bpy.context.window_manager.windows[0]):
            bpy.ops.object.mode_set(mode="OBJECT")

    # tb000 Select with only Maya's checks on (Holed / Lamina / Shared UVs, hidden here)
    msgs = []
    slot.sb = make_sb(msgs)
    slot.tb000(cleanup_menu("select", chk012=True, chk016=True, chk018=True))
    slot.sb = make_sb()
    check("tb000 Select with no Blender check asks for one",
          bool(msgs) and "Enable a check" in msgs[-1] and o.mode == "OBJECT",
          f"msgs={msgs}")

    # tb002 Delete in FACE mode: middle face of a 3x3 grid -> 8 faces remain.
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

    # tb004 Lock / Unlock — Blender's analogue of Maya's node lock: hide_select (make objects
    # unselectable). Lock acts on the selection; Unlock clears every object.
    def lock_widget(text):
        return NS(option_box=NS(menu=NS(cmb_lock=NS(currentText=lambda t=text: t))))

    reset()
    bpy.ops.mesh.primitive_cube_add()
    a = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    b = bpy.context.active_object
    btk.CoreUtils.select([a, b])
    slot.tb004(lock_widget("Lock"))
    check("tb004 Lock makes the selection unselectable (hide_select) and deselects it",
          a.hide_select and b.hide_select and not a.select_get(),
          f"a.hide_select={a.hide_select} b.hide_select={b.hide_select} a.selected={a.select_get()}")

    # a third, unlocked object present: Unlock must clear hide_select on ALL objects (a locked
    # object can't be selected to unlock it individually).
    bpy.ops.mesh.primitive_cube_add(location=(6, 0, 0))
    slot.tb004(lock_widget("Unlock"))
    check("tb004 Unlock clears hide_select on every object",
          not any(o.hide_select for o in bpy.data.objects),
          f"still_locked={[o.name for o in bpy.data.objects if o.hide_select]}")

    # Lock with nothing selected is a guarded no-op (warns, changes nothing).
    reset()
    bpy.ops.mesh.primitive_cube_add()
    only = bpy.context.active_object
    btk.CoreUtils.select([])
    msgs = []
    slot.sb = make_sb(msgs)
    slot.tb004(lock_widget("Lock"))
    slot.sb = make_sb()
    check("tb004 Lock with empty selection is a guarded no-op",
          not only.hide_select and msgs == ["Select the object(s) to lock."],
          f"hide_select={only.hide_select} msgs={msgs}")

    # tb005 Optimize: the unused data-blocks are purged
    reset()
    bpy.data.meshes.new("OrphanMesh")
    slot.tb005(NS(option_box=NS(menu=NS(chk_purge_recursive=chk(True),
                                         chk_purge_linked=chk(True)))))
    check("tb005 Optimize purges an unused mesh", "OrphanMesh" not in bpy.data.meshes)

    # cmb000 Transfer: active object = source, other selected object = target (real data
    # copied per data type, driven through the actual combo dispatch, not the bare bpy.ops call).
    transfer_labels = list(btk.Components.get_transfer_types())
    transfer_widget = NS(items=transfer_labels)

    def make_transfer_pair():
        bpy.ops.mesh.primitive_cube_add()
        source = bpy.context.active_object
        bpy.ops.mesh.primitive_cube_add()  # coincident cube -> unambiguous nearest-vertex match
        target = bpy.context.active_object
        btk.CoreUtils.select([source, target])  # replace: the first (source) is active
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

    # --- the Qt-pump state in a two-view-layer scene ---------------------------------------
    # The slots run windowless, where ``bpy.context.view_layer`` is the scene's DEFAULT layer
    # while the operators (under btk.window_context_override) act on the layer the window
    # shows. Each case sets a different selection per layer, runs windowless, and checks the
    # operation acted on the WINDOW's. Measured before the fix: Material Slots refused ("source
    # mesh active" read the default layer's active), Cleanup's "visible" pool read the default
    # layer's visibility, a created control was selected in the default layer, and
    # ensure_component_mode activated its fallback mesh in the default layer, so mode_set put
    # the window's active curve into Edit Mode instead.
    reset()
    win = bpy.context.window_manager.windows[0]
    default_vl = bpy.context.scene.view_layers[0]
    win_vl = bpy.context.scene.view_layers.new("WindowLayer")
    prior_win_vl = win.view_layer
    win.view_layer = win_vl
    try:
        bpy.ops.mesh.primitive_cube_add()
        source = bpy.context.active_object
        bpy.ops.mesh.primitive_cube_add()
        target = bpy.context.active_object
        bpy.ops.mesh.primitive_cube_add(location=(6, 0, 0))
        decoy = bpy.context.active_object
        bpy.ops.curve.primitive_bezier_curve_add(location=(9, 0, 0))
        crv = bpy.context.active_object

        def layer_state(vl, selected, active):
            for o in vl.objects:
                o.select_set(o in selected, view_layer=vl)
            vl.objects.active = active

        def pump_state(win_sel, win_active):
            layer_state(default_vl, [decoy], decoy)
            layer_state(win_vl, win_sel, win_active)

        def default_untouched():
            return default_vl.objects.active == decoy and [
                o for o in default_vl.objects if o.select_get(view_layer=default_vl)
            ] == [decoy]

        # Material Slots: the window's active source, its selected target
        source.data.materials.append(bpy.data.materials.new("PumpMat"))
        target.data.materials.clear()
        pump_state([source, target], source)
        with bpy.context.temp_override(window=None):
            slot.cmb000(transfer_labels.index("Material Slots"), transfer_widget)
        check(
            "pump: cmb000 'Material Slots' reads the window layer's active source",
            list(target.data.materials) == list(source.data.materials)
            and default_untouched(),
            f"target={[m.name for m in target.data.materials if m]}",
        )

        # Cleanup 'visible' pool: hidden in the window's layer only
        pump_state([source], source)
        target.hide_set(True, view_layer=win_vl)
        with bpy.context.temp_override(window=None):
            pool = btk.MeshDiagnostics._cleanup_pool("visible")
        target.hide_set(False, view_layer=win_vl)
        check(
            "pump: Cleanup's 'visible' pool reads the window layer's visibility",
            source in pool and target not in pool,
            f"pool={[o.name for o in pool]}",
        )

        # Create > Control: the new control is selected + active in the window's layer
        pump_state([source], source)
        with bpy.context.temp_override(window=None):
            slot.list000(list_item("Circle", "Control"))
        ctrl = win_vl.objects.active
        # (the default layer is checked on the objects it already had: a NEW object's base
        # there is synced lazily and inherits the select flag the window layer set)
        default_sel = [
            o
            for o in (source, target, decoy, crv)
            if o.select_get(view_layer=default_vl)
        ]
        check(
            "pump: a created control is selected + active in the window layer",
            ctrl is not None
            and ctrl not in (source, target, decoy, crv)
            and [o for o in win_vl.objects if o.select_get(view_layer=win_vl)] == [ctrl]
            and default_vl.objects.active == decoy
            and default_sel == [decoy],
            f"window active={getattr(ctrl, 'name', None)} "
            f"default active={default_vl.objects.active.name}",
        )

        # CoreUtils.ensure_component_mode: the window's active is a curve, a mesh is selected
        pump_state([crv, target], crv)
        with bpy.context.temp_override(window=None):
            got = btk.CoreUtils.ensure_component_mode("MESH")
        modes = (target.mode, crv.mode, decoy.mode)
        with btk.window_context_override():
            if win_vl.objects.active and win_vl.objects.active.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
        check(
            "pump: ensure_component_mode activates its fallback mesh in the window layer",
            got == target and modes == ("EDIT", "OBJECT", "OBJECT"),
            f"(target, curve, decoy) modes={modes}",
        )

        # World-Aligned Pivot's bake (btk.XformUtils.world_align_pivot, what the shared
        # Pivot panel calls): the rotation is applied to the applyable selection, and the
        # window layer's selection AND active come back -- the curve included
        source.rotation_euler = (0.0, 0.0, 0.5)
        pump_state([source, crv], crv)
        with bpy.context.temp_override(window=None):
            btk.XformUtils.world_align_pivot(None, pivot_type="object")
        win_sel = sorted(
            o.name for o in win_vl.objects if o.select_get(view_layer=win_vl)
        )
        check(
            "pump: Pivot's rotation bake restores the window layer's selection + active",
            abs(source.rotation_euler.z) < 1e-6
            and win_sel == sorted([source.name, crv.name])
            and win_vl.objects.active == crv
            and default_vl.objects.active == decoy,
            f"rot z={source.rotation_euler.z:.3f} window={win_sel} "
            f"active={getattr(win_vl.objects.active, 'name', None)}",
        )
    finally:
        win.view_layer = prior_win_vl
        bpy.context.scene.view_layers.remove(win_vl)

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-EDIT-SLOT===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
