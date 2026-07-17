"""Manual harness for mode-gated viewport tools (``SlotsBlender.set_viewport_tool``).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/viewport_tool_check.py

Pins the mode gate end-to-end through the REAL slot classes. Blender resolves a workspace tool
by (space_type, *context mode*), so activating an Edit-Mode-only tool while the object is in
Object Mode logs "Warning: Tool 'builtin.knife' not found for space 'VIEW_3D'" and changes
nothing — the reported bug. Note it is a ``self.report({'WARNING'})``, **not** an exception, so
the caller's try/except never saw it; the tool just silently stayed put.
``set_viewport_tool(..., edit_type=...)`` enters the mode first, the way Maya's counterparts do
implicitly. Checks, each from **Object Mode** (the state that reproduced it):

1. **The bug reproduces** — knife is genuinely absent from OBJECT's tool list, so the checks
   below pin a real gate rather than a no-op.
2. **Mesh tools** (Multi-Cut / Insert Edgeloop / Quad Draw) enter Edit Mode, after which the
   tool is present in the live tool list (the lookup that emits the warning when it fails).
3. **Curve tools** (Edit Curve / Add Points) do the same for EDIT_CURVE.
4. **The selection fall-back** — a tool works when its object is selected but *not* active
   (Maya's component tools act on the selection; ``btk.target_weld`` falls back the same way).
5. **A friendly message**, not a Blender-internal error, when there is nothing of the type.
6. **Mode-agnostic tools** (Measure) still work with no ``edit_type`` and do NOT force a mode.

**Background caveat:** Blender only turns a tool's ``keymap`` callback into a named keymap
during GUI keyconfig init, so under ``--background`` the final ``tool.setup()`` raises
("Function.keymap expected a string type, not function") for keymap-bearing tools (knife /
loop_cut / …) and the active-tool id stays empty — a harness artifact, not a product failure.
The gate under test is still fully pinned: resolving the tool for the mode is the lookup that
emits the warning, and it runs before ``setup()``. The active-tool id is additionally asserted
outside ``--background``, so a GUI-hosted run pins the real activation too.
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
    """Instance without the UI-loading __init__ (headless: no loaded_ui). ``sb.message_box``
    records toasts so a check can assert the *absence* of an error one."""
    slot = cls.__new__(cls)
    slot.toasts = []
    slot.sb = NS(message_box=lambda msg, *a, **k: slot.toasts.append(msg))
    return slot


def reset():
    import bpy

    active = bpy.context.view_layer.objects.active
    if active and active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def add_cube():
    import bpy

    bpy.ops.mesh.primitive_cube_add()
    return bpy.context.view_layer.objects.active


def add_curve():
    import bpy

    bpy.ops.curve.primitive_bezier_curve_add()
    return bpy.context.view_layer.objects.active


def active_tool(context_mode):
    """idname of the workspace tool currently active for ``context_mode``, or ''."""
    import bpy

    tool = bpy.context.workspace.tools.from_space_view3d_mode(context_mode, create=False)
    return getattr(tool, "idname", "") or ""


def tool_available(context_mode, tool_id):
    """Is ``tool_id`` in VIEW_3D's tool list for ``context_mode``? This is the same lookup
    ``wm.tool_set_by_id`` performs — when it misses, Blender logs "not found for space"."""
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
    import bpy

    cls = ToolSelectPanelHelper._tool_class_from_space_type("VIEW_3D")
    return any(
        getattr(item, "idname", None) == tool_id
        for item in ToolSelectPanelHelper._tools_flatten(
            cls.tools_from_context(bpy.context, context_mode)
        )
        if item is not None
    )


def tool_landed(context_mode, tool_id):
    """The tool resolved for its mode — plus, outside ``--background``, actually became the
    active tool. Returns (ok, detail).

    Blender only turns a tool's ``keymap`` callback into a named keymap during GUI keyconfig
    init, so under ``--background`` ``tool.setup()`` raises ("expected a string type, not
    function") and the active-tool id stays empty for every keymap-bearing tool. The mode gate
    (the bug under test) is still fully pinned there: resolving the tool for the mode is the
    lookup that emits "not found for space", and it happens before ``setup()``.
    """
    import bpy

    if not tool_available(context_mode, tool_id):
        return False, f"{tool_id} not found for space VIEW_3D in mode {context_mode}"
    if not bpy.app.background and active_tool(context_mode) != tool_id:
        return False, f"active tool is {active_tool(context_mode)!r}, expected {tool_id!r}"
    return True, ""


def main():
    import bpy
    from tentacle import tcl_blender  # noqa: F401 — provisions Qt (qtpy/PySide6) for the slot imports
    from tentacle.slots.blender.polygons import PolygonsSlots

    # State which assertion level ran: a strict check that silently degrades reads exactly like
    # one that passed, so say it out loud rather than leaving a GUI-only leg invisibly skipped.
    lines.append(
        "#    assertion level: "
        + (
            "mode gate only (--background: tool keymaps are never built, so setup() cannot land)"
            if bpy.app.background
            else "mode gate + active-tool id (GUI: full activation)"
        )
    )
    from tentacle.slots.blender.subdivision import Subdivision
    from tentacle.slots.blender.nurbs import Nurbs
    from tentacle.slots.blender.utilities import Utilities

    # -- 1. the bug reproduces: knife is absent from OBJECT mode's tool list -----------------
    # It surfaces as a report WARNING (not an exception), which is why the tool silently stayed
    # put rather than the caller's try/except catching anything — assert the gate itself.
    reset()
    add_cube()
    check(
        "repro: knife is not resolvable from Object Mode",
        not tool_available("OBJECT", "builtin.knife")
        and tool_available("EDIT_MESH", "builtin.knife"),
        f"resolvable in OBJECT={tool_available('OBJECT', 'builtin.knife')} "
        f"EDIT_MESH={tool_available('EDIT_MESH', 'builtin.knife')}",
    )

    # -- 2. mesh tools: Object Mode -> Edit Mode, tool resolvable ----------------------------
    for cls, method, tool_id, label in (
        (PolygonsSlots, "b012", "builtin.knife", "Multi-Cut"),
        (PolygonsSlots, "b047", "builtin.loop_cut", "Insert Edgeloop"),
        (Subdivision, "b028", "builtin.poly_build", "Quad Draw"),
    ):
        reset()
        obj = add_cube()
        slot = make_slot(cls)
        getattr(slot, method)()
        landed, why = tool_landed("EDIT_MESH", tool_id)
        check(
            f"{label} ({method}) from Object Mode",
            obj.mode == "EDIT" and landed,
            f"mode={obj.mode} {why}".strip(),
        )

    # -- 3. curve tools: Object Mode -> Edit Mode, tool resolvable ---------------------------
    for method, tool_id, label in (
        ("_edit_curve_tool", "builtin.pen", "Edit Curve Tool"),
        ("_add_points_tool", "builtin.draw", "Add Points Tool"),
    ):
        reset()
        obj = add_curve()
        slot = make_slot(Nurbs)
        getattr(slot, method)()
        landed, why = tool_landed("EDIT_CURVE", tool_id)
        check(
            f"{label} ({method}) from Object Mode",
            obj.mode == "EDIT" and landed,
            f"mode={obj.mode} {why}".strip(),
        )

    # -- 4. selection fall-back: right-type object selected but NOT active -------------------
    reset()
    cube = add_cube()
    curve = add_curve()  # curve is left active; the cube is only selected
    cube.select_set(True)
    bpy.context.view_layer.objects.active = curve
    slot = make_slot(PolygonsSlots)
    slot.b012()
    landed, why = tool_landed("EDIT_MESH", "builtin.knife")
    check(
        "Multi-Cut falls back to the selected (non-active) mesh",
        cube.mode == "EDIT"
        and bpy.context.view_layer.objects.active is cube
        and landed,
        f"cube.mode={cube.mode} active={bpy.context.view_layer.objects.active.name} {why}".strip(),
    )

    # -- 5. no mesh at all: a clean message, not a Blender internal error --------------------
    reset()
    add_curve()  # a curve is active; Multi-Cut has no mesh to work on
    slot = make_slot(PolygonsSlots)
    slot.b012()
    check(
        "Multi-Cut with no mesh reports a friendly message",
        slot.toasts and "mesh object" in slot.toasts[-1] and "not found for space" not in slot.toasts[-1],
        f"toasts={slot.toasts}",
    )

    # -- 6. mode-agnostic tool: works with no edit_type and forces no mode change ------------
    reset()
    obj = add_cube()
    slot = make_slot(Utilities)
    slot.b000()  # Measure
    landed, why = tool_landed("OBJECT", "builtin.measure")
    check(
        "Measure works from Object Mode without forcing Edit Mode",
        obj.mode == "OBJECT" and landed,
        f"mode={obj.mode} {why}".strip(),
    )


try:
    main()
except Exception:  # noqa: BLE001 - report the trace through the sentinel, don't hide it
    lines.append("FAIL harness raised | " + traceback.format_exc())

print("\n".join(lines))
# Count only check lines — notes//headers in `lines` must never pad the score.
results = [line for line in lines if line.startswith(("OK  ", "FAIL"))]
failed = sum(1 for line in results if line.startswith("FAIL"))
print(f"===RESULT=== {len(results) - failed}/{len(results)} passed")
sys.exit(1 if failed else 0)
