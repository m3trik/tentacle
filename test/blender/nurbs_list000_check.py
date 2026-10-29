# !/usr/bin/python
# coding=utf-8
"""Headless verification of the composed Nurbs list000 in Blender (``tentacle.slots.nurbs``).

Requires a real Blender binary (``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/nurbs_list000_check.py

Verifies:
  - list000_init builds Maya's root -> category -> leaf tree (Nurbs ->
    Create/Modify/Surfaces/Edit -> leaves), the parametric-NURBS-only leaves tagged
    ``requires="maya"`` and so hidden by the visibility policy (the fake switchboard below
    applies it as uitk does in Blender).
  - list000(item) no-ops on a category node (still has a populated sublist).
  - Each leaf performs its ``btk.NurbsUtils.curve_action`` against real curve/mesh data:
    Reverse, Open/Close, Smooth, Duplicate, Extract, Attach, Detach, Cut, Planar, Project.
  - Precondition guards (Detach/Cut outside Edit Mode, Attach/Duplicate/etc. with nothing
    selected) show one message_box instead of raising.
"""
import os
import sys
from types import SimpleNamespace as NS
from pathlib import Path

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


class FakeSwitchboard:
    """Minimal stand-in for uitk's Switchboard: ``message_box`` records, ``tk`` is the host
    toolkit (what the composed class calls), and the visibility policy hides what Blender
    cannot serve, as ``Switchboard.apply_visibility_policy`` does with ``context_tags``
    {"blender"}."""

    def __init__(self, tk):
        self.messages = []
        self.tk = tk

    def message_box(self, msg, *args, **kwargs):
        self.messages.append(msg)

    @staticmethod
    def apply_visibility_policy(widget):
        requires = widget.property("requires")
        if requires and "blender" not in str(requires):
            widget.setVisible(False)
            widget.hidden_by_policy = "requires"
            return True
        return False


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
    import blendertk as btk
    from tentacle.slots.nurbs import NurbsSlots

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    check("QApplication available (needed for ExpandableList)", app is not None)
    check("Qt provisioned via tcl_blender bootstrap", hasattr(tcl_blender, "bl_info"))

    sb = FakeSwitchboard(btk)
    nurbs = NurbsSlots.__new__(NurbsSlots)  # headless: no loaded_ui for __init__ to read
    nurbs.sb = sb

    # ---- tree structure ---------------------------------------------------------------
    widget = ExpandableList()
    # list000_init reads the host menu's tags (submenu -> expand overlay); a
    # standalone list has no host ui, so give it the startmenu's answer.
    widget.ui = NS(has_tags=lambda *_a, **_k: False)
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

    all_leaves = {}  # label -> widget, hidden ones included
    for cat in cats:
        for leaf in cat.sublist.get_items():
            all_leaves[leaf.item_text()] = leaf
    leaf_widgets = {
        t: w
        for t, w in all_leaves.items()
        if not (w.isHidden() or getattr(w, "hidden_by_policy", None))
    }

    expected_leaves = {
        label
        for rows in NurbsSlots._LIST000_ITEMS.values()
        for label, _action, requires in rows
        if requires is None
    }
    check(
        "visible leaves are the rows both hosts serve",
        set(leaf_widgets) == expected_leaves,
        f"got {sorted(leaf_widgets)}",
    )

    # The parametric-NURBS-only rows exist (one tree for both hosts) but are hidden here.
    excused = {
        "Lock", "Unlock", "Insert Isoparm", "Insert Knot",
        "Extend (Options)", "Extend on Surface",
    }
    check(
        "parametric-only leaves are present and hidden by the policy",
        excused <= set(all_leaves) and excused.isdisjoint(leaf_widgets),
        f"hidden={sorted(set(all_leaves) - set(leaf_widgets))}",
    )
    check(
        "every Blender-visible action is one btk serves",
        all(
            action in btk.NurbsUtils.CURVE_ACTIONS or action in NurbsSlots._TOOLS
            for rows in NurbsSlots._LIST000_ITEMS.values()
            for _label, action, requires in rows
            if requires is None
        ),
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

    # ---- Edit Curve Tool / Add Points Tool: Slots.activate_tool says what happened, once
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
ok = all(line.startswith("OK") for line in lines) and lines
print(f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({sum(1 for line in lines if line.startswith('OK'))}/{len(lines)})")
