"""Manual harness for the Blender keymap/activation bridge in ``tentacle/tcl_blender.py``.

Requires a real Blender binary (it ``import bpy``), so it is **not** a CI/unittest target — the
``blender/`` subdir and the non-``test_`` name keep it out of auto-discovery. Run it against a
*fresh* Blender (never an existing session)::

    blender --background --factory-startup --python tentacle/tests/blender/keymap_bridge_check.py

Qt deps: set ``TENTACLE_QT_DEPS`` to a folder holding PySide6 + qtpy (or let ``tcl_blender``
pip-install them on first run). Exercises the bridge helpers in isolation — no full the marking menu /
Qt host needed: key translation, operator registration, the viewport-scoped ``3D View`` keymap
item, activation→show() routing (no mouse grab on a bare key-hold), re-install safety, error
reporting, no-active-menu pass-through, and teardown.
"""
import sys
import os
import traceback
from pathlib import Path
from types import SimpleNamespace as NS

# Monorepo root = .../_scripts (this file is _scripts/tentacle/tests/blender/keymap_bridge_check.py).
MONO = Path(__file__).resolve().parents[3]
for pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    p = str(MONO / pkg)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
# Reuse a staged Qt deps folder if one is pointed at; otherwise tcl_blender provisions Qt itself.
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


try:
    import bpy
    from tentacle import tcl_blender as tb
    import blendertk as btk  # noqa: E402

    # key translation (incl. special keys that don't match the naive strip-upper)
    check("Key_F12 -> F12", btk.KeymapBridge.qt_key_to_blender_type("Key_F12") == "F12")
    check("F12 -> F12", btk.KeymapBridge.qt_key_to_blender_type("F12") == "F12")
    check("Key_A -> A", btk.KeymapBridge.qt_key_to_blender_type("Key_A") == "A")
    check("Key_Meta -> OSKEY (Windows key)", btk.KeymapBridge.qt_key_to_blender_type("Key_Meta") == "OSKEY")
    check("Key_Super_L -> OSKEY", btk.KeymapBridge.qt_key_to_blender_type("Key_Super_L") == "OSKEY")

    # install bridge with a stubbed marking menu (no real Qt host needed). The operator drives the
    # Maya interaction state machine through the menu's public surface: activate on key-down,
    # release on key-up; raise_/activateWindow mirror the QWidget methods it nudges after press. The bridge
    # must NOT grab the mouse on the no-button key-hold (an explicit grab kills hover-nav and
    # re-reads clicks as the F12+LMB chord — the "buttons need several clicks" bug); the grab is
    # established by the shared _transfer_mouse_control only when a button is held (the chord),
    # so a `grab` event appearing here on a bare press is a regression.
    events = []
    stub = NS(
        activate=lambda buttons=None: events.append("press"),
        release=lambda: events.append("release"),
        grabMouse=lambda: events.append("grab"),
        raise_=lambda: None,
        activateWindow=lambda: None,
    )
    btk.KeymapBridge.install_keymap(stub, "F12")
    check("operator registered", hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"))
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        check("keymap items added (F12 PRESS+RELEASE)",
              len(btk.KeymapBridge.keymaps) == 2
              and {k.value for _, k in btk.KeymapBridge.keymaps} == {"PRESS", "RELEASE"}
              and all(k.type == "F12" for _, k in btk.KeymapBridge.keymaps),
              f"items={[k.value for _, k in btk.KeymapBridge.keymaps]}")
    else:
        check("keymap skipped headless (no addon keyconfig)", btk.KeymapBridge.keymaps == [])

    # key-down drives the press state machine but does NOT grab the mouse (no-button path) — the
    # overlay stays ungrabbed so child enter/leave events fire (hover-nav) and clicks reach buttons.
    bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")  # phase defaults to "press"
    check("press -> menu.activate, no grab on key-hold", events == ["press"], f"events={events}")
    events.clear()
    # key-up drives the release (completes/hides, releases the grab)
    bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT", phase="release")
    check("release -> menu.release", events == ["release"], f"events={events}")
    events.clear()

    # keymap is viewport-scoped (3D View), not a global override — it wins over render only when
    # the viewport has focus, leaving every other F12 (render elsewhere) untouched.
    if kc:
        check("keymap is 3D View (viewport-scoped)", btk.KeymapBridge.keymaps[0][0].name == "3D View",
              f"km={btk.KeymapBridge.keymaps[0][0].name}" if btk.KeymapBridge.keymaps else "none")

    # re-install (re-launch) is keymap-safe — no duplicate items (still exactly PRESS+RELEASE)
    btk.KeymapBridge.install_keymap(stub, "F12")
    if kc:
        check("re-install -> still PRESS+RELEASE (no dupes)", len(btk.KeymapBridge.keymaps) == 2, f"n={len(btk.KeymapBridge.keymaps)}")

    # operator error is reported (Blender raises it for script callers)
    btk.KeymapBridge.menu = NS(
        activate=lambda buttons=None: (_ for _ in ()).throw(RuntimeError("boom")),
        grabMouse=lambda: None, raise_=lambda: None, activateWindow=lambda: None,
    )
    reported = False
    try:
        bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")
    except RuntimeError as err:
        reported = "boom" in str(err)
    check("host error -> reported (not crashed)", reported)

    # no active menu -> press CANCELLED (passes F12 through to render); release FINISHED (harmless)
    btk.KeymapBridge.menu = None
    res = bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")
    check("no active menu (press) -> CANCELLED", res == {"CANCELLED"}, f"res={res}")
    res = bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT", phase="release")
    check("no active menu (release) -> CANCELLED", res == {"CANCELLED"}, f"res={res}")

    # teardown removes keymap + unregisters operator
    btk.KeymapBridge.teardown()
    check("teardown -> operator gone + keymaps cleared",
          not hasattr(bpy.types, "TENTACLE_OT_show_marking_menu") and btk.KeymapBridge.keymaps == [])

    # launch() reuses the live instance (repeat register() must not stack marking menus);
    # teardown cleared KeymapBridge.menu above, so a fresh stub stands in for the live menu.
    btk.KeymapBridge.menu = stub
    check("launch() reuses the live instance", tb.launch() is stub)
    btk.KeymapBridge.menu = None

    # the add-on stub exposes the add-on + console surface; the Qt host is blendertk's
    check("tcl_blender exposes launch/register/unregister/reload/diagnose + bl_info",
          callable(tb.launch) and callable(tb.register) and callable(tb.unregister)
          and callable(tb.reload) and callable(tb.diagnose) and "name" in tb.bl_info)
    check("blendertk exposes the Qt host + the marking-menu host",
          callable(btk.QtRuntime.ensure_qapp) and callable(btk.QtRuntime.ensure_widget)
          and callable(btk.QtRuntime.start_pump)
          and callable(btk.BlenderMarkingMenuHost().start))

except Exception as e:
    lines.append(f"FAIL setup: {e!r}")
    lines.append(traceback.format_exc())

ok = all(line.startswith("OK") for line in lines)
print("\n===BLENDER-KEYBRIDGE===")
print("\n".join(lines))
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
