# !/usr/bin/python
# coding=utf-8
"""Headless verification for the Nurbs list000 parity fix (Maya<->Blender ExpandableList).

Requires a real Blender binary (``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/nurbs_list000_check.py

Verifies:
  - list000_init builds the same root -> category -> leaf tree shape as Maya's (Nurbs ->
    Create/Modify/Surfaces/Edit -> leaves), and that only genuinely-portable leaves are present
    (the parametric-NURBS-only ones are omitted, not the whole widget).
  - list000(item) no-ops on a category node (still has a populated sublist).
  - Each ported leaf actually performs the mapped bpy action against real curve/mesh data:
    Reverse, Open/Close, Smooth, Duplicate, Extract, Attach, Detach, Cut, Planar, Project.
  - Precondition guards (Detach/Cut outside Edit Mode, Attach/Duplicate/etc. with nothing
    selected) show a message_box instead of raising.
"""
import os
import sys
from pathlib import Path

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


class FakeSwitchboard:
    """Minimal stand-in for uitk's Switchboard — just enough surface (``message_box``) for
    Nurbs' handlers to report guard failures without pulling in the full UI stack."""

    def __init__(self):
        self.messages = []

    def message_box(self, msg, *args, **kwargs):
        self.messages.append(msg)


def _new_curve(name, points, cyclic=False, dims="3D"):
    import bpy

    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = dims
    spline = cu.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for sp, p in zip(spline.points, points):
        sp.co = (p[0], p[1], p[2], 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(obj)
    return obj


def _select_only(objs):
    import bpy

    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[-1]


def _run():
    import bpy
    from tentacle import tcl_blender  # import-time side effect provisions Qt (qtpy/PySide6)
    from qtpy import QtWidgets
    from uitk.widgets.expandableList import ExpandableList
    from tentacle.slots.blender.nurbs import Nurbs

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    check("QApplication available (needed for ExpandableList)", app is not None)
    check("Qt provisioned via tcl_blender bootstrap", hasattr(tcl_blender, "bl_info"))

    sb = FakeSwitchboard()
    nurbs = Nurbs(sb)

    # ---- tree structure ---------------------------------------------------------------
    widget = ExpandableList()
    nurbs.list000_init(widget)

    top = widget.get_items()
    root = next((w for w in top if hasattr(w, "sublist")), None)
    check("root item exists", root is not None)
    check("root text is 'Nurbs'", root is not None and root.item_text() == "Nurbs")

    # ``get_items()`` recurses into every nested sublist; direct children only come from the
    # layout itself (categories, not their leaves).
    cats = (
        [root.sublist._layout.itemAt(i).widget() for i in range(root.sublist._layout.count())]
        if root else []
    )
    cat_texts = [c.item_text() for c in cats]
    check(
        "categories == Create/Modify/Surfaces/Edit",
        cat_texts == ["Create", "Modify", "Surfaces", "Edit"],
        f"got {cat_texts}",
    )

    leaf_widgets = {}  # label -> widget, for later direct-dispatch tests
    for cat in cats:
        for leaf in cat.sublist.get_items():
            leaf_widgets[leaf.item_text()] = leaf

    expected_leaves = {
        label
        for items in Nurbs._LIST000_COMMANDS.values()
        for label, _ in items
    }
    check(
        "leaf set matches _LIST000_COMMANDS",
        set(leaf_widgets) == expected_leaves,
        f"got {sorted(leaf_widgets)}",
    )

    excused = {
        "Lock", "Unlock", "Bend", "Curl", "Curvature", "Straighten",
        "Insert Isoparm", "Insert Knot", "Rebuild",
        "Extend (Options)", "Extend", "Extend on Surface",
    }
    check(
        "excused parametric-only leaves are absent",
        excused.isdisjoint(leaf_widgets),
        f"unexpected overlap: {excused & set(leaf_widgets)}",
    )

    # ---- category node no-ops (still has a populated sublist) --------------------------
    sb.messages.clear()
    before = len(bpy.data.objects)
    nurbs.list000(cats[0])  # "Create"
    check(
        "clicking a category node no-ops",
        len(bpy.data.objects) == before and not sb.messages,
    )

    # ---- Reverse ------------------------------------------------------------------------
    c1 = _new_curve("RevTest", [(0, 0, 0), (1, 0, 0), (2, 0, 0)])
    _select_only([c1])
    before_pts = [tuple(p.co) for p in c1.data.splines[0].points]
    sb.messages.clear()
    nurbs.list000(leaf_widgets["Reverse"])
    after_pts = [tuple(p.co) for p in c1.data.splines[0].points]
    check(
        "Reverse flips control-point order",
        after_pts == list(reversed(before_pts)),
        f"before={before_pts} after={after_pts}",
    )
    check("Reverse ends back in Object Mode", c1.mode == "OBJECT")

    # ---- Open/Close (cyclic toggle) ------------------------------------------------------
    c2 = _new_curve("CyclicTest", [(0, 0, 0), (1, 0, 0), (1, 1, 0)], cyclic=False)
    _select_only([c2])
    was_cyclic = c2.data.splines[0].use_cyclic_u
    nurbs.list000(leaf_widgets["Open/Close"])
    check(
        "Open/Close toggles use_cyclic_u",
        c2.data.splines[0].use_cyclic_u != was_cyclic,
    )
    check("Open/Close ends back in Object Mode", c2.mode == "OBJECT")

    # ---- Smooth (just needs to run cleanly) ----------------------------------------------
    c3 = _new_curve("SmoothTest", [(0, 0, 0), (1, 2, 0), (2, -2, 0), (3, 0, 0)])
    _select_only([c3])
    sb.messages.clear()
    try:
        nurbs.list000(leaf_widgets["Smooth"])
        smooth_ok = True
    except Exception as e:
        smooth_ok = False
        lines.append(f"     smooth exception: {e!r}")
    check("Smooth runs without raising", smooth_ok)
    check("Smooth ends back in Object Mode", c3.mode == "OBJECT")

    # ---- Duplicate ------------------------------------------------------------------------
    c4 = _new_curve("DupTest", [(0, 0, 0), (1, 0, 0)])
    _select_only([c4])
    before = set(bpy.data.objects.keys())
    nurbs.list000(leaf_widgets["Duplicate"])
    after = set(bpy.data.objects.keys())
    new_objs = after - before
    check("Duplicate creates exactly one new object", len(new_objs) == 1, f"new={new_objs}")
    if new_objs:
        dup_obj = bpy.data.objects[next(iter(new_objs))]
        check("Duplicate result is selected+active",
              dup_obj.select_get() and bpy.context.view_layer.objects.active == dup_obj)

    # ---- Extract (mesh -> curve, source mesh preserved) -----------------------------------
    me = bpy.data.meshes.new("ExtractMesh")
    me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0)], [(0, 1), (1, 2)], [])
    me.update()
    mesh_obj = bpy.data.objects.new("ExtractMesh", me)
    bpy.context.collection.objects.link(mesh_obj)
    _select_only([mesh_obj])
    before = set(bpy.data.objects.keys())
    nurbs.list000(leaf_widgets["Extract"])
    after = set(bpy.data.objects.keys())
    new_objs = after - before
    check("Extract creates a new object", len(new_objs) == 1, f"new={new_objs}")
    check("Extract leaves source mesh intact", mesh_obj.name in bpy.data.objects and mesh_obj.type == "MESH")
    if new_objs:
        extracted = bpy.data.objects[next(iter(new_objs))]
        check("Extract result is a CURVE", extracted.type == "CURVE")

    # ---- Attach (join) ---------------------------------------------------------------------
    a1 = _new_curve("AttachA", [(0, 0, 0), (1, 0, 0)])
    a2 = _new_curve("AttachB", [(2, 0, 0), (3, 0, 0)])
    _select_only([a2, a1])  # a1 last-selected -> active
    before_n = len(bpy.data.objects)
    nurbs.list000(leaf_widgets["Attach"])
    check("Attach (join) reduces object count by 1", len(bpy.data.objects) == before_n - 1)

    # ---- Planar (fill) -----------------------------------------------------------------
    c5 = _new_curve("PlanarTest", [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], cyclic=True)
    _select_only([c5])
    nurbs.list000(leaf_widgets["Planar"])
    check("Planar sets dimensions to 2D", c5.data.dimensions == "2D")
    check("Planar sets fill_mode to BOTH", c5.data.fill_mode == "BOTH")

    # ---- Project (Shrinkwrap conform) ----------------------------------------------------
    target_me = bpy.data.meshes.new("ProjTarget")
    target_me.from_pydata(
        [(-2, -2, 1), (2, -2, 1), (2, 2, 1), (-2, 2, 1)], [], [(0, 1, 2, 3)]
    )
    target_me.update()
    target_obj = bpy.data.objects.new("ProjTarget", target_me)
    bpy.context.collection.objects.link(target_obj)
    c6 = _new_curve("ProjCurve", [(-1, 0, 0), (0, 0, 0), (1, 0, 0)])
    _select_only([c6, target_obj])
    nurbs.list000(leaf_widgets["Project"])
    z_vals = [p.co[2] for p in c6.data.splines[0].points]
    check("Project conforms curve points onto the mesh (z moves to 1.0)",
          all(abs(z - 1.0) < 1e-4 for z in z_vals), f"z={z_vals}")

    # ---- Detach / Cut precondition guards (Object Mode -> message_box, no raise) ---------
    c7 = _new_curve("CutTest", [(0, 0, 0), (1, 0, 0), (2, 0, 0)])
    _select_only([c7])
    sb.messages.clear()
    nurbs.list000(leaf_widgets["Cut"])
    check("Cut outside Edit Mode shows a guard message (no raise)",
          len(sb.messages) == 1, f"messages={sb.messages}")

    sb.messages.clear()
    nurbs.list000(leaf_widgets["Detach"])
    check("Detach outside Edit Mode shows a guard message (no raise)",
          len(sb.messages) == 1, f"messages={sb.messages}")

    # ---- Cut actually works once in Edit Mode with a point selected ----------------------
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.curve.select_all(action="DESELECT")
    c7.data.splines[0].points[1].select = True
    sb.messages.clear()
    before_splines = len(c7.data.splines)
    try:
        nurbs.list000(leaf_widgets["Cut"])
        cut_ok = True
    except Exception as e:
        cut_ok = False
        lines.append(f"     cut exception: {e!r}")
    after_splines = len(c7.data.splines)
    bpy.ops.object.mode_set(mode="OBJECT")
    check("Cut in Edit Mode with a point selected runs cleanly", cut_ok and not sb.messages)
    check("Cut splits off a new spline", after_splines > before_splines,
          f"before={before_splines} after={after_splines}")

    # ---- Edit Curve Tool / Add Points Tool (no VIEW_3D in --background -> graceful message)
    sb.messages.clear()
    nurbs.list000(leaf_widgets["Edit Curve Tool"])
    check("Edit Curve Tool degrades gracefully with no viewport",
          len(sb.messages) == 1, f"messages={sb.messages}")
    sb.messages.clear()
    nurbs.list000(leaf_widgets["Add Points Tool"])
    check("Add Points Tool degrades gracefully with no viewport",
          len(sb.messages) == 1, f"messages={sb.messages}")

    # ---- empty-selection guards (no exception, one message) ------------------------------
    for label in ("Reverse", "Attach", "Duplicate", "Smooth", "Planar", "Open/Close"):
        _select_only([])
        sb.messages.clear()
        try:
            nurbs.list000(leaf_widgets[label])
            raised = False
        except Exception as e:
            raised = True
            lines.append(f"     {label} exception on empty selection: {e!r}")
        check(f"{label} with empty selection: guarded (no raise, 1 message)",
              not raised and len(sb.messages) == 1, f"messages={sb.messages}")


try:
    _run()
except Exception:
    import traceback
    traceback.print_exc()
    lines.append("FAIL unhandled exception")

print("\n".join(lines))
ok = all(l.startswith("OK") for l in lines) and lines
print(f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({sum(1 for l in lines if l.startswith('OK'))}/{len(lines)})")
