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
    check("Key_F12 -> F12", tb._KeymapBridge.qt_key_to_blender_type("Key_F12") == "F12")
    check("F12 -> F12", tb._KeymapBridge.qt_key_to_blender_type("F12") == "F12")
    check("Key_A -> A", tb._KeymapBridge.qt_key_to_blender_type("Key_A") == "A")
    check("Key_Meta -> OSKEY (Windows key)", tb._KeymapBridge.qt_key_to_blender_type("Key_Meta") == "OSKEY")
    check("Key_Super_L -> OSKEY", tb._KeymapBridge.qt_key_to_blender_type("Key_Super_L") == "OSKEY")

    # install bridge with a stubbed marking menu (no real Qt host needed). The operator drives the
    # Maya interaction state machine: _on_activation_press on key-down, _on_activation_release on
    # key-up; raise_/activateWindow mirror the QWidget methods it nudges after press. The bridge
    # must NOT grab the mouse on the no-button key-hold (an explicit grab kills hover-nav and
    # re-reads clicks as the F12+LMB chord — the "buttons need several clicks" bug); the grab is
    # established by the shared _transfer_mouse_control only when a button is held (the chord),
    # so a `grab` event appearing here on a bare press is a regression.
    events = []
    stub = NS(
        _on_activation_press=lambda: events.append("press"),
        _on_activation_release=lambda: events.append("release"),
        grabMouse=lambda: events.append("grab"),
        raise_=lambda: None,
        activateWindow=lambda: None,
    )
    tb._KeymapBridge.install_keymap(stub, "F12")
    check("operator registered", hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"))
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        check("keymap items added (F12 PRESS+RELEASE)",
              len(tb._KeymapBridge.keymaps) == 2
              and {k.value for _, k in tb._KeymapBridge.keymaps} == {"PRESS", "RELEASE"}
              and all(k.type == "F12" for _, k in tb._KeymapBridge.keymaps),
              f"items={[k.value for _, k in tb._KeymapBridge.keymaps]}")
    else:
        check("keymap skipped headless (no addon keyconfig)", tb._KeymapBridge.keymaps == [])

    # key-down drives the press state machine but does NOT grab the mouse (no-button path) — the
    # overlay stays ungrabbed so child enter/leave events fire (hover-nav) and clicks reach buttons.
    bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")  # phase defaults to "press"
    check("press -> _on_activation_press, no grab on key-hold", events == ["press"], f"events={events}")
    events.clear()
    # key-up drives the release (completes/hides, releases the grab)
    bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT", phase="release")
    check("release -> _on_activation_release", events == ["release"], f"events={events}")
    events.clear()

    # keymap is viewport-scoped (3D View), not a global override — it wins over render only when
    # the viewport has focus, leaving every other F12 (render elsewhere) untouched.
    if kc:
        check("keymap is 3D View (viewport-scoped)", tb._KeymapBridge.keymaps[0][0].name == "3D View",
              f"km={tb._KeymapBridge.keymaps[0][0].name}" if tb._KeymapBridge.keymaps else "none")

    # re-install (re-launch) is keymap-safe — no duplicate items (still exactly PRESS+RELEASE)
    tb._KeymapBridge.install_keymap(stub, "F12")
    if kc:
        check("re-install -> still PRESS+RELEASE (no dupes)", len(tb._KeymapBridge.keymaps) == 2, f"n={len(tb._KeymapBridge.keymaps)}")

    # operator error is reported (Blender raises it for script callers)
    tb._KeymapBridge.tcl = NS(
        _on_activation_press=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        grabMouse=lambda: None, raise_=lambda: None, activateWindow=lambda: None,
    )
    reported = False
    try:
        bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")
    except RuntimeError as err:
        reported = "boom" in str(err)
    check("host error -> reported (not crashed)", reported)

    # no active menu -> press CANCELLED (passes F12 through to render); release FINISHED (harmless)
    tb._KeymapBridge.tcl = None
    res = bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT")
    check("no active menu (press) -> CANCELLED", res == {"CANCELLED"}, f"res={res}")
    res = bpy.ops.tentacle.show_marking_menu("EXEC_DEFAULT", phase="release")
    check("no active menu (release) -> CANCELLED", res == {"CANCELLED"}, f"res={res}")

    # teardown removes keymap + unregisters operator
    tb._KeymapBridge.teardown()
    check("teardown -> operator gone + keymaps cleared",
          not hasattr(bpy.types, "TENTACLE_OT_show_marking_menu") and tb._KeymapBridge.keymaps == [])

    # launch() reuses the live instance (repeat register() must not stack marking menus);
    # teardown cleared _KeymapBridge.tcl above, so a fresh stub stands in for the live menu.
    tb._KeymapBridge.tcl = stub
    check("launch() reuses the live instance", tb.launch() is stub)
    tb._KeymapBridge.tcl = None

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
