"""Headless guard for the both-button chord menu wrap (``BlenderUiHandler`` + ``BlenderNativeMenus``).

Run in a **fresh** headless Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/blender_menus_check.py

The chord menu wraps Blender's own native viewport menus (the mirror of ``ui/maya_menus``):
every node is a ``MenuButton`` with a bare target, resolved on release through
``BlenderUiHandler.can_resolve`` to a proxy whose ``show`` presents the **harvested Qt clone**
of the native menu in a Switchboard ``MainWindow`` (header + pin, hides on ``key_show``
release — Maya parity). Maya lifts live ``QAction`` rows; Blender menus are Python classes,
so ``menu_harvest`` executes their ``draw`` against a recorder layout and rebuilds the rows as
``QAction``s. This asserts, against a live Blender:

  * every id in ``BlenderNativeMenus.MENU_MAPPING`` / ``SELECT_BY_MODE`` is a real menu (no leaf
    dead-ends),
  * the handler registers a resolvable proxy for every node name (``can_resolve`` + ``loaded_ui``),
  * ``_wrap_native_menu`` returns a ``MainWindow`` hosting a populated ``QMenu`` (header attached,
    tagged, window identity cached; content re-harvested per call so it tracks the live mode),
  * mode-dependent draws that deref ``context.edit_object`` (``VIEW3D_MT_edit_armature``,
    ``VIEW3D_MT_edit_curve_ctrlpoints``) wrap OUT of mode too, poll-greyed, via the harvest's
    active-object-as-``edit_object`` injection; only with no active object at all does the wrap
    degrade to the overlay fallback (None on this bare switchboard),
  * macro-operator draws (edit-mesh Vertices/Edges: ``props.MESH_OT_rip.use_fill = ...``) harvest
    via ``_OpProps``'s nested recording — these were dead buttons in every mode before it,
  * triggering a row schedules the deferred ``bpy.ops`` invoke (one timer),
  * ``show(proxy)`` routes through the wrap, and Select resolves per live mode.

The real on-screen presentation (position, pin behavior, hide on ``key_show``) is the shared
marking-menu window path and is proven interactively, not here.
"""
import sys
import os
import traceback
from pathlib import Path

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

import bpy
from tentacle import tcl_blender  # noqa: F401 — provisions qtpy so the Switchboard import resolves
from qtpy import QtWidgets
from uitk import Switchboard
from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler
from blendertk.ui_utils.blender_native_menus import BlenderNativeMenus
import blendertk as btk

lines = []


def log(*a):
    print(*a)
    sys.stdout.flush()


def check(name, cond, detail=""):
    lines.append(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")


def _rows(window):
    """Non-separator actions of the wrapped window's hosted QMenu."""
    menu = getattr(window.centralWidget(), "menu", None)
    return [a for a in menu.actions() if not a.isSeparator()] if menu else []


def main():
    try:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841
        mapping = BlenderNativeMenus.MENU_MAPPING
        select_by_mode = BlenderNativeMenus.SELECT_BY_MODE

        # 1. No dead links — every mapped id (fixed leaves + Select's per-mode map) is a real menu.
        bad = sorted({i for i in mapping.values() if not btk.menu_exists(i)})
        check("every fixed leaf maps to a real Blender menu", not bad, f"{bad}")
        bad_sel = sorted({i for i in select_by_mode.values() if not btk.menu_exists(i)})
        check("every Select-by-mode id is a real Blender menu", not bad_sel, f"{bad_sel}")
        bad_adaptive = sorted({
            i
            for by_mode, fallback in BlenderNativeMenus.MODE_ADAPTIVE.values()
            for i in list(by_mode.values()) + [fallback]
            if not btk.menu_exists(i)
        })
        check("every mode-adaptive id (Select + Rig) is a real Blender menu",
              not bad_adaptive, f"{bad_adaptive}")
        check("menu_exists rejects a bogus id", not btk.menu_exists("VIEW3D_MT_does_not_exist"))

        # 2. The handler registers a resolvable proxy per node name (bypass the heavy package scan
        #    in __init__; exercise only the native-menu wrap).
        sb = Switchboard()
        handler = object.__new__(BlenderUiHandler)
        handler.sb = sb
        handler._register_native_menu_proxies()
        names = BlenderNativeMenus.names()
        check("proxy registered for every node name", set(handler._native_menu_proxies) == names,
              f"{sorted(set(names) ^ set(handler._native_menu_proxies))}")
        unresolved = sorted(n for n in names if not handler.can_resolve(n))
        check("can_resolve True for every node name", not unresolved, f"{unresolved}")
        check("can_resolve False for a non-node name", not handler.can_resolve("definitely_not_a_menu"))
        # get_ui returns the proxy (the release path relies on this), tagged menu (standalone).
        proxy = sb.get_ui("mesh")
        check("get_ui('mesh') returns the native proxy",
              getattr(proxy, handler._NATIVE_MENU_ATTR, None) == "mesh")
        check("proxy is a standalone target (not a stacked submenu)",
              not proxy.has_tags(["startmenu", "submenu"]))

        cube = bpy.context.view_layer.objects.active  # factory default Cube

        # 3. The wrap: a MainWindow hosting the harvested QMenu, Maya's hosting pipeline.
        w_add = handler._wrap_native_menu("add")
        check("'add' wraps to a window", w_add is not None, f"{type(w_add)}")
        check("'add' hosts a populated QMenu", len(_rows(w_add)) >= 5, f"{len(_rows(w_add))} rows")
        check("'add' window has the uitk header", hasattr(w_add, "header"))
        check("'add' window tagged as a blender menu",
              w_add.has_tags(["blender", "menu"]) and w_add.has_tags(["blender_menu"]))
        check("get_ui now resolves to the wrapper", sb.get_ui("add") is w_add)
        w_add2 = handler._wrap_native_menu("add")
        check("re-wrap reuses the window (content refreshed)", w_add2 is w_add)

        w_obj = handler._wrap_native_menu("object")
        obj_rows = _rows(w_obj)
        check("'object' menu harvests its rows", len(obj_rows) >= 10, f"{len(obj_rows)}")
        check("'object' harvests nested submenus",
              any(a.menu() is not None for a in obj_rows))
        check("'object' has live rows in Object mode",
              any(a.isEnabled() for a in obj_rows))

        # 3b. Mode-dependent draws out of mode: the harvest injects the ACTIVE object as
        #     edit_object (VIEW3D_MT_edit_armature / _edit_curve_ctrlpoints hard-deref it),
        #     so these open poll-greyed in Object mode — Maya's menus are likewise always
        #     openable. This was the live "dead buttons" report.
        w_arm_obj = handler._wrap_native_menu("armature")
        arm_rows = _rows(w_arm_obj) if w_arm_obj else []
        check("'armature' wraps OUT of mode via edit_object injection",
              w_arm_obj is not None and len(arm_rows) >= 3, f"{len(arm_rows)} rows")
        check("'armature' out-of-mode leaf rows are poll-greyed",
              any(not a.isEnabled() for a in arm_rows if a.menu() is None))
        w_cp = handler._wrap_native_menu("ctrl_points")
        check("'ctrl_points' wraps OUT of mode",
              w_cp is not None and len(_rows(w_cp)) >= 1,
              f"{len(_rows(w_cp)) if w_cp else 0} rows")

        # With NO active object the injection has nothing to offer — overlay fallback; on
        # this bare switchboard no '<name>#submenu' overlay is registered, so the wrap
        # returns None (production tentacle registers the overlays).
        bpy.context.view_layer.objects.active = None
        try:
            check("'armature' with no active object -> overlay-or-None, no crash",
                  handler._wrap_native_menu("armature") is None)
        finally:
            bpy.context.view_layer.objects.active = cube

        # 3b2. The Animation -> Rigging chain (mirror of Maya's Key -> Skeleton): the startmenu
        #      Animation node wraps the Object > Animation menu; Rig is mode-adaptive
        #      (Pose menu in Pose mode, Edit Armature otherwise — greyed out of mode).
        w_anim = handler._wrap_native_menu("object_animation")
        check("'object_animation' wraps (startmenu Animation node)",
              w_anim is not None and len(_rows(w_anim)) >= 4,
              f"{len(_rows(w_anim)) if w_anim else 0} rows")
        check("'rig' resolves to Edit Armature outside pose/armature modes",
              BlenderNativeMenus.resolve("rig") == "VIEW3D_MT_edit_armature")
        w_rig = handler._wrap_native_menu("rig")
        check("'rig' wraps out of mode (poll-greyed armature menu)",
              w_rig is not None and len(_rows(w_rig)) >= 3,
              f"{len(_rows(w_rig)) if w_rig else 0} rows")
        for node, expected_rows in (
            ("object_constraints", 3),
            ("modifiers", 2),
            ("quick_effects", 3),
        ):
            w_new = handler._wrap_native_menu(node)
            check(f"'{node}' wraps", w_new is not None and len(_rows(w_new)) >= expected_rows,
                  f"{len(_rows(w_new)) if w_new else 0} rows")

        # 3c. The same nodes wrap normally IN their mode — per family.
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            w_mesh = handler._wrap_native_menu("mesh")
            mesh_rows = _rows(w_mesh)
            check("'mesh' wraps in Edit Mesh", w_mesh is not None and len(mesh_rows) >= 10,
                  f"{len(mesh_rows)} rows")
            check("'mesh' has enabled rows in Edit Mesh", any(a.isEnabled() for a in mesh_rows))
            # Regression: these draws configure MACRO operators via nested prop groups
            # (props.MESH_OT_rip.use_fill = ...) — the harvest raised on them until
            # _OpProps grew nested recording, leaving dead buttons in every mode.
            for node in ("vertex", "edge"):
                w_leaf = handler._wrap_native_menu(node)
                check(f"'{node}' wraps in Edit Mesh (macro-props draw)",
                      w_leaf is not None and len(_rows(w_leaf)) >= 8,
                      f"{len(_rows(w_leaf)) if w_leaf else 0} rows")
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

        bpy.ops.object.armature_add()
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            w_arm = handler._wrap_native_menu("armature")
            check("'armature' wraps in Edit Armature",
                  w_arm is not None and len(_rows(w_arm)) >= 3,
                  f"{len(_rows(w_arm)) if w_arm else 0} rows")
            bpy.ops.object.mode_set(mode="POSE")
            check("'rig' resolves to the Pose menu in Pose mode",
                  BlenderNativeMenus.resolve("rig") == "VIEW3D_MT_pose")
            w_pose = handler._wrap_native_menu("pose")
            check("'pose' wraps in Pose mode",
                  w_pose is not None and len(_rows(w_pose)) >= 3,
                  f"{len(_rows(w_pose)) if w_pose else 0} rows")
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

        # 3d. Row wiring: triggering an enabled leaf row schedules the deferred bpy.ops invoke.
        fired = []
        orig_reg = bpy.app.timers.register
        bpy.app.timers.register = lambda fn, **kw: fired.append(fn)
        try:
            target = next(a for a in _rows(w_obj) if a.isEnabled() and a.menu() is None)
            target.trigger()
        finally:
            bpy.app.timers.register = orig_reg
        check("triggering a row schedules the deferred operator", len(fired) == 1, f"{len(fired)}")

        # 3e. show() routes a native proxy through the wrap.
        routed = []
        handler._wrap_native_menu = lambda name: (routed.append(name), None)[1]
        try:
            result = handler.show(sb.get_ui("mesh"))
        finally:
            del handler._wrap_native_menu  # drop the instance shadow; method restored
        check("show(proxy) routes through _wrap_native_menu",
              routed == ["mesh"] and result is None, f"{routed}")

        # 4. Select resolves by LIVE mode (content follows through the same wrap).
        bpy.ops.object.select_all(action="DESELECT")
        cube.select_set(True)
        bpy.context.view_layer.objects.active = cube
        check("Select resolves per mode (Object)",
              BlenderNativeMenus.resolve("select") == "VIEW3D_MT_select_object")
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            check("Select resolves per mode (Edit Mesh)",
                  BlenderNativeMenus.resolve("select") == "VIEW3D_MT_select_edit_mesh")
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
        fallback = BlenderNativeMenus.SELECT_BY_MODE.get("SCULPT", "VIEW3D_MT_select_object")
        check("unmapped mode falls back to VIEW3D_MT_select_object", fallback == "VIEW3D_MT_select_object")
    except Exception as error:
        lines.append(f"FAIL setup: {error!r}")
        lines.append(traceback.format_exc())
    finally:
        for line in lines:
            log(line)
        ok = all(line.startswith(("OK", "note")) for line in lines) and lines
        log(f"===RESULT: {'PASS' if ok else 'FAIL'}===")


main()
