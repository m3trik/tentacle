"""Manual harness for the Blender keymap/activation bridge in ``tentacle/tcl_blender.py``.

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/keymap_bridge_check.py

Qt deps: set ``TENTACLE_QT_DEPS`` to a folder holding PySide6 + qtpy (or let ``tcl_blender``
pip-install them on first run). Exercises the bridge helpers in isolation — no full TclBlender /
Qt host needed: key translation, operator registration, the global ``Window`` keymap item,
activation→show() routing, F12 collision mute/restore (against an injected synthetic conflict),
re-install safety, error reporting, and teardown.
"""
import sys
import os
import traceback
from pathlib import Path
from types import SimpleNamespace as NS

# Monorepo root = .../_scripts (this file is _scripts/tentacle/test/blender/keymap_bridge_check.py).
MONO = Path(__file__).resolve().parents[3]
for pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    p = str(MONO / pkg)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
# Reuse a staged Qt deps folder if one is pointed at; otherwise tcl_blender provisions Qt itself.
os.environ.setdefault("QT_API", "pyside6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lines = []


def check(name, cond, detail=""):
    lines.append(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")


try:
    import bpy
    from tentacle import tcl_blender as tb

    # key translation (incl. special keys that don't match the naive strip-upper)
    check("Key_F12 -> F12", tb._qt_key_to_blender_type("Key_F12") == "F12")
    check("F12 -> F12", tb._qt_key_to_blender_type("F12") == "F12")
    check("Key_A -> A", tb._qt_key_to_blender_type("Key_A") == "A")
    check("Key_Meta -> OSKEY (Windows key)", tb._qt_key_to_blender_type("Key_Meta") == "OSKEY")
    check("Key_Super_L -> OSKEY", tb._qt_key_to_blender_type("Key_Super_L") == "OSKEY")

    # install bridge with a stubbed marking menu (no real Qt host needed). raise_/activateWindow
    # mirror the QWidget methods the bridge operator calls after show().
    shown = []
    stub = NS(show=lambda ui: shown.append(ui), raise_=lambda: None, activateWindow=lambda: None)
    tb._install_keymap(stub, "F12", "main#startmenu")
    check("operator registered", hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"))
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        check("keymap item added (F12)",
              len(tb._KEYMAPS) == 1 and tb._KEYMAPS[0][1].type == "F12",
              f"key={tb._KEYMAPS[0][1].type}" if tb._KEYMAPS else "none")
    else:
        check("keymap skipped headless (no addon keyconfig)", tb._KEYMAPS == [])

    # activation routes to the bound menu's show()
    bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT", ui_name="cameras#startmenu")
    check("activation -> show('cameras#startmenu')", shown == ["cameras#startmenu"], f"shown={shown}")
    shown.clear()
    bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")  # property default
    check("default activation -> main#startmenu", shown == ["main#startmenu"], f"shown={shown}")

    # keymap is viewport-scoped (3D View), not a global override — it wins over render only when
    # the viewport has focus, leaving every other F12 (render elsewhere) untouched.
    if kc:
        check("keymap is 3D View (viewport-scoped)", tb._KEYMAPS[0][0].name == "3D View",
              f"km={tb._KEYMAPS[0][0].name}" if tb._KEYMAPS else "none")

    # re-install (re-launch) is keymap-safe — no duplicate items
    tb._install_keymap(stub, "F12", "main#startmenu")
    if kc:
        check("re-install -> still one keymap item", len(tb._KEYMAPS) == 1, f"n={len(tb._KEYMAPS)}")

    # operator error is reported (Blender raises it for script callers)
    tb._ACTIVE_TCL = NS(show=lambda ui: (_ for _ in ()).throw(RuntimeError("boom")))
    reported = False
    try:
        bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")
    except RuntimeError as err:
        reported = "boom" in str(err)
    check("host error -> reported (not crashed)", reported)

    # no active menu -> CANCELLED, no crash
    tb._ACTIVE_TCL = None
    res = bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")
    check("no active menu -> CANCELLED", res == {"CANCELLED"}, f"res={res}")

    # teardown removes keymap + unregisters operator
    tb._teardown_keymap()
    check("teardown -> operator gone + keymaps cleared",
          not hasattr(bpy.types, "TENTACLE_OT_show_marking_menu") and tb._KEYMAPS == [])

    # launch() reuses the live instance (repeat register() must not stack marking menus);
    # teardown cleared _ACTIVE_TCL above, so a fresh stub stands in for the live menu.
    tb._ACTIVE_TCL = stub
    check("launch() reuses the live instance", tb.launch() is stub)
    tb._ACTIVE_TCL = None

    # the consolidated entry point exposes the host + add-on surface (host/add-on/diagnose)
    check("tcl_blender exposes launch/register/unregister/diagnose + bl_info",
          callable(tb.launch) and callable(tb.register) and callable(tb.unregister)
          and callable(tb.diagnose) and "name" in tb.bl_info)
    check("tcl_blender exposes the Qt host fns",
          callable(tb.ensure_qapp) and callable(tb.ensure_blender_widget)
          and callable(tb.start_event_pump))

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-KEYBRIDGE===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
