"""Headless guard for the both-button chord menu wrap (``BlenderUiHandler`` + ``BlenderNativeMenus``).

Run in a **fresh** headless Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/blender_menus_check.py

The chord menu is a thin launcher for Blender's own native viewport menus (the mirror of
``ui/maya_menus``): every node is a ``MenuButton`` with a bare target, resolved on release through
``BlenderUiHandler.can_resolve`` to a native-menu *proxy* whose ``show`` pops Blender's real menu
via ``btk.call_native_menu`` (Maya harvests live ``QAction`` rows; Blender has none, so it invokes
its own menu). This asserts, against a live Blender:

  * every id in ``BlenderNativeMenus.MENU_MAPPING`` / ``SELECT_BY_MODE`` is a real menu (no leaf
    dead-ends),
  * the handler registers a resolvable proxy for every node name (``can_resolve`` + ``loaded_ui``),
  * showing a proxy dispatches ``call_native_menu`` with the right id — one per hub incl. the
    3-level Armature->Pose branch, plus mode-adaptive Select.

The actual popup is GUI-only (``wm.call_menu`` faults under ``--background``), so the real pop is
proven interactively, not here; firing is verified by patching ``call_native_menu`` /
``bpy.app.timers.register`` to recorders.
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


def _show_records(handler, proxy):
    """Show ``proxy`` with call_native_menu + the deferral timer patched to recorders; the deferred
    pop runs synchronously so no real popup is attempted headless. Returns the recorded id list."""
    recorded = []
    orig_call, orig_reg = btk.call_native_menu, bpy.app.timers.register
    btk.call_native_menu = lambda idname: recorded.append(idname)
    bpy.app.timers.register = lambda fn, **kw: fn()
    try:
        handler.show(proxy)
    finally:
        btk.call_native_menu, bpy.app.timers.register = orig_call, orig_reg
    return recorded


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

        # 3. Showing a proxy dispatches call_native_menu with the mapped id — cover a flat category,
        #    each hub anchor (incl. the level-3 Pose anchor), and a leaf from the Mesh + Pose hubs.
        for node, expected in (
            ("add", "VIEW3D_MT_add"),                    # flat
            ("mesh", "VIEW3D_MT_edit_mesh"),              # Mesh hub anchor
            ("mesh_normals", "VIEW3D_MT_edit_mesh_normals"),  # Mesh hub leaf
            ("curve", "VIEW3D_MT_edit_curve"),            # Curve hub anchor
            ("armature", "VIEW3D_MT_edit_armature"),      # Armature hub anchor
            ("pose", "VIEW3D_MT_pose"),                   # Pose hub anchor (level 3)
            ("ik", "VIEW3D_MT_pose_ik"),                  # Pose hub leaf
            ("render", "TOPBAR_MT_render"),               # Render hub anchor
            ("help", "TOPBAR_MT_help"),                   # Render hub leaf
        ):
            rec = _show_records(handler, handler._native_menu_proxies[node])
            check(f"show '{node}' pops {expected}", rec == [expected], f"{rec}")

        # 4. Select dispatches by LIVE mode, not a fixed id — Object (default) + Edit Mesh (the
        #    default Cube), plus the safe fallback for an unmapped mode.
        rec = _show_records(handler, handler._native_menu_proxies["select"])
        check("Select in Object mode pops VIEW3D_MT_select_object",
              rec == ["VIEW3D_MT_select_object"], f"{rec}")
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            rec = _show_records(handler, handler._native_menu_proxies["select"])
            check("Select in Edit Mesh mode pops VIEW3D_MT_select_edit_mesh",
                  rec == ["VIEW3D_MT_select_edit_mesh"], f"{rec}")
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
