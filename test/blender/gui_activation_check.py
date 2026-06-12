"""GUI activation harness for the Blender marking-menu key bridge.

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/gui_activation_check.py

Unlike the headless ``keymap_bridge_check.py``, this boots the full UI so the real keyconfig is
built (``render.render`` F12 actually exists to mute) and the event loop runs (Qt pump ticks).
After the UI settles it registers tentacle, prints the live activation state via ``diagnose()``,
tests that ``show()`` actually makes the menu visible, writes everything to a log, then quits.
"""
import sys
import os
from pathlib import Path

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

import bpy
from tentacle import tcl_blender as tb


def log(*args):
    print(*args)
    sys.stdout.flush()


def _quit():
    bpy.ops.wm.quit_blender()
    return None


def _run():
    try:
        log("=== GUI-ACTIVATION ===")
        log("blender:", bpy.app.version_string)
        tb.register()  # host + viewport-scoped 3D View keymap; UI is up so the keyconfig is real
        # Full dump of every F12 binding (incl. ours in the addon kc) so we can see which keymap each
        # lives in — ours must be in '3D View', and render stays in 'Screen' (evaluated after us).
        wm = bpy.context.window_manager
        seen = set()
        for kc in (wm.keyconfigs.addon, wm.keyconfigs.user, wm.keyconfigs.active, wm.keyconfigs.default):
            if kc is None or id(kc) in seen:
                continue
            seen.add(id(kc))
            for km in kc.keymaps:
                for kmi in km.keymap_items:
                    if kmi.type == "F12":
                        mods = "".join(
                            m for m, on in (("C", kmi.ctrl), ("A", kmi.alt), ("S", kmi.shift),
                                            ("O", kmi.oskey), ("any", kmi.any)) if on
                        )
                        log(f"  F12[{kc.name}/{km.name}] {kmi.idname} val={kmi.value} "
                            f"mods={mods or '-'} active={kmi.active}")
        tb.diagnose()
        # Does show() actually surface the Qt menu (independent of a real keypress)?
        try:
            from qtpy import QtWidgets

            tb._ACTIVE_TCL.show("main#startmenu")
            app = QtWidgets.QApplication.instance()
            for _ in range(30):
                app.processEvents()
            log("menu isVisible after show():", bool(tb._ACTIVE_TCL.isVisible()))

            # Closest proxy to a real F12 press: invoke the bridge operator itself.
            tb._ACTIVE_TCL.hide()
            for _ in range(10):
                app.processEvents()
            bpy.ops.tentacle.show_marking_menu("INVOKE_DEFAULT", ui_name="main#startmenu")
            for _ in range(30):
                app.processEvents()
            log("menu isVisible after operator invoke:", bool(tb._ACTIVE_TCL.isVisible()))
        except Exception as error:
            import traceback

            log("show() raised:", repr(error))
            log(traceback.format_exc())
    except Exception as error:
        import traceback

        log("HARNESS ERROR:", repr(error))
        log(traceback.format_exc())
    finally:
        log("=== END ===")
        sys.stdout.flush()
        bpy.app.timers.register(_quit, first_interval=1.0)
    return None


# Defer until the UI + keyconfig have settled (GUI main loop is required for the timer to fire).
bpy.app.timers.register(_run, first_interval=2.5)
