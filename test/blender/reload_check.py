"""Manual harness for the guarded reload (``tcl_blender.reload()`` — settings tb001).

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/test/blender/reload_check.py

Verifies the full reload contract headlessly: register stands up the host + keymap; ``reload()``
tears the bridge down, reloads the ecosystem packages in place, and schedules re-registration;
the re-registered module restores the operator/keymap/instance; and the event pump's generation
token supersedes the old pump (no double-pumping after a reload). The deferred timer is invoked
directly (background Blender doesn't spin the timer loop for us).
"""
import importlib
import sys
import os
import traceback
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


try:
    import bpy
    from tentacle import tcl_blender as tb

    tb.register()
    from qtpy import QtWidgets

    app = QtWidgets.QApplication.instance()
    token0 = getattr(app, "_tentacle_pump_token", None)
    check("register stands up the operator",
          hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"))
    check("register wires a live instance", tb._KeymapBridge.tcl is not None)
    check("pump token stamped", token0 is not None)

    n = tb.reload()
    check("reload reloads modules", n > 0, f"n={n}")
    check("reload tears down the operator",
          not hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"))
    check("reload clears the live instance", tb._KeymapBridge.tcl is None)

    # Background Blender doesn't run the timer loop for us — drive the deferred step.
    fresh = importlib.import_module("tentacle.tcl_blender")
    check("module reloaded in place (same sys.modules entry)",
          fresh is sys.modules["tentacle.tcl_blender"])
    fresh.register()
    check("re-register restores the operator",
          hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"))
    check("re-register restores a live instance", fresh._KeymapBridge.tcl is not None)
    check("re-register restores the keymap", len(fresh._KeymapBridge.keymaps) > 0,
          f"items={len(fresh._KeymapBridge.keymaps)}")
    token1 = getattr(app, "_tentacle_pump_token", None)
    check("pump token superseded (old pump retires itself)",
          token1 is not None and token1 is not token0)

    fresh.unregister()
    check("teardown after reload is clean",
          not hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"))

except Exception:
    traceback.print_exc()
    lines.append("FAIL unhandled exception")

print("\n".join(lines))
ok = all(l.startswith("OK") for l in lines) and lines
print(f"===RESULT: {'PASS' if ok else 'FAIL'}=== ({sum(1 for l in lines if l.startswith('OK'))}/{len(lines)})")
