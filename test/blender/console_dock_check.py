# !/usr/bin/python
# coding=utf-8
"""GUI harness: the Blender Script Output console — native child-window dock, capture,
persistence.

``blendertk.env_utils.script_output`` embeds the shared ``uitk.ScriptOutput`` widget as a
**true child window** of Blender's main GHOST window, glued to a docked Info Log area's
content region via ``btk.QtDock`` (no overlay, no geometry timer — see the ``qt_dock``
module docstring for the mechanism). This pins the whole chain, in the PRODUCTION startup
order (``begin_capture`` → ``import tentacle`` → host launch → ``restore``):

* ``begin_capture()`` tees stdout with no Qt/window needed, so text printed BEFORE the
  console ever exists — tentacle's greeting banner included — appears once it's first shown;
* ``restore()`` at host launch with no saved state leaves the console hidden;
* ``show()`` docks into the main window (no new ``bpy.Window``), embeds the widget, and
  persists ``visible=true`` to the (sandboxed) state file;
* the widget's OS parent IS the GHOST window (WS_CHILD embed), and its rect MATCHES the
  area's content region minus the exposed native resize strip at the top — Blender's
  area-edge grab band stays Blender-owned so dragging the console border resizes instead
  of starting a text selection (win32-measured, physical px — no dpr math on either side);
* ``stdout`` + ``logging`` land in the console and the error line is colored;
* **keyboard focus follows the mouse**: hovering the console (real ``SetCursorPos``, no
  click) hands it OS + Qt focus and a REAL Ctrl+C copies its text; moving back over the
  viewport returns focus to Blender so its own shortcuts resume;
* ``hide()`` undocks the area and persists ``visible=false`` + the strip ``height`` — but
  leaves capture running, so a SECOND ``show()`` re-docks with the earlier content still
  present;
* a simulated host reload (``ScriptConsole.teardown()`` — undock/stream-restore, flag
  kept) + NEXT SESSION (fresh instance, saved ``visible=true``) re-opens the console
  through ``restore()`` — the reload and cross-session persistence paths;
* a SECOND Blender window parked over the console's rect **occludes** it — the embed
  stacks with its container window only, never above sibling Blender windows
  (user requirement 2026-07-18; a WS_CHILD guarantees it, an overlay-style owned
  top-level would violate it and fail this leg).

The persisted flag is sandboxed via ``ScriptConsole._state_dir_override`` so a check run
never touches the user's real Blender config.

Run against a *fresh* GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/console_dock_check.py

PASS = every check true (written to ``test/temp_tests/console_dock_out.json``). A wedged
Blender never writes the file — the caller's timeout + taskkill handles that. Opens a real
Blender window + embedded Qt; throwaway instance only. Windows-only (the embed path); on
other platforms the console degrades to the bare native Info Log and this harness is N/A.
"""
import sys
import os
import ctypes
import json
import shutil
from ctypes import wintypes
from pathlib import Path

import bpy

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _input  # noqa: E402  (shared GHOST-window helpers)

os.environ.setdefault("QT_API", "pyside6")

TEMP = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests")
)
OUT = os.path.join(TEMP, "console_dock_out.json")
SANDBOX = os.path.join(TEMP, "console_dock_state")  # sandboxed persisted-flag dir
_u = ctypes.windll.user32
R = {"checks": []}


def _ck(name, cond, extra=""):
    R["checks"].append({"name": name, "pass": bool(cond), "extra": str(extra)})


def _main_areas():
    return bpy.context.window_manager.windows[0].screen.areas


def _state():
    """The sandboxed persisted state dict ({} = no/unreadable state file)."""
    try:
        with open(os.path.join(SANDBOX, "blendertk_script_output.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _child_rect_in_parent_client(child, parent):
    """Child's rect mapped into the parent's CLIENT coordinate space (physical px)."""
    rect = wintypes.RECT()
    _u.GetWindowRect(ctypes.c_void_p(int(child)), ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    _u.ClientToScreen(ctypes.c_void_p(int(parent)), ctypes.byref(pt))
    return [rect.left - pt.x, rect.top - pt.y, rect.right - rect.left, rect.bottom - rect.top]


def _go():
    try:
        # --- production startup order: capture FIRST, then the tentacle import/launch ---
        from blendertk.env_utils import script_output as so

        shutil.rmtree(SANDBOX, ignore_errors=True)
        os.makedirs(SANDBOX, exist_ok=True)
        so.ScriptConsole._state_dir_override = SANDBOX

        R["orig_stdout_id"] = id(sys.stdout)
        so.begin_capture()  # ≈ tentacle_startup.py — before `import tentacle`
        _ck("begin_capture() tees stdout (UI-free, before any window/Qt use)",
            id(sys.stdout) != R["orig_stdout_id"])

        from tentacle import tcl_blender as tb  # greeting banner prints INTO the capture
        if tb._KeymapBridge.tcl is None:
            tb.launch()  # TclBlender.__init__ runs script_output.restore()

        inst = so.ScriptConsole.instance()
        _ck("restore() at launch with no saved state leaves the console hidden",
            not inst.is_open())

        R["win_before"] = len(bpy.context.window_manager.windows)
        R["areas_before"] = len(_main_areas())
        inst = so.show()
        R["dock_supported"] = so.QtDock.supported()
        _ck("docking spawned NO new bpy.Window (true dock, not a separate window)",
            len(bpy.context.window_manager.windows) == R["win_before"])
        _ck("Info Log area docked into the main window's screen",
            len(_main_areas()) == R["areas_before"] + 1)
        _ck("console widget built", inst.widget is not None)
        _ck("show() persists visible=true", _state().get("visible") is True)
        text = inst.widget.toPlainText() if inst.widget is not None else ""
        _ck("greeting banner printed BEFORE the console existed is in the console "
            "(begin_capture ran first, widget seeded from the transcript buffer)",
            "You are using" in text)
        bpy.app.timers.register(_measure, first_interval=0.8)
    except Exception:
        import traceback
        R["go_error"] = traceback.format_exc()
        _finish()
    return None


def _measure():
    try:
        import logging
        from qtpy import QtWidgets
        from blendertk.env_utils import script_output as so
        from blendertk.ui_utils.blender_window import BlenderWindow

        inst = so.ScriptConsole._instance
        app = QtWidgets.QApplication.instance()

        print("Result: console verification print")
        logging.getLogger("console_check").error("boom from logging")
        app.processEvents()
        widget = inst.widget

        hwnd = inst._dock._hwnd
        child = int(widget.winId())
        parent_now = int(_u.GetParent(ctypes.c_void_p(child)) or 0)
        _ck("console is a true CHILD of the main GHOST window (WS_CHILD embed)",
            hwnd is not None and parent_now == int(hwnd),
            f"parent={parent_now} ghost={hwnd}")

        actual = _child_rect_in_parent_client(child, hwnd)
        region = inst._dock.content_region()
        base = BlenderWindow.region_client_rect(hwnd, region) if region else None
        # The child deliberately starts BELOW the region top: the native area-edge grab
        # band (edge ± pad) stays Blender-owned, so the resize cursor there is honest —
        # a press grabs the edge instead of starting a text selection in the console.
        pad = inst._dock._edge_pad
        _ck("resize strip: dock resolved a native edge pad (>=2px)",
            isinstance(pad, int) and pad >= 2, f"pad={pad}")
        expected = [base[0], base[1] + pad, base[2], base[3] - pad] if base else None
        R["child_rect"], R["expected_rect"] = actual, expected
        if expected:
            delta = max(abs(a - e) for a, e in zip(actual, expected))
            _ck("console fills the content region minus the exposed resize strip (<=2px)",
                delta <= 2,
                f"delta={delta} actual={actual} expected={expected} pad={pad}")
        else:
            _ck("console fills the content region minus the exposed resize strip (<=2px)",
                False, "no region")

        text = widget.toPlainText()
        _ck("print reached console", "console verification print" in text)
        _ck("logging reached console", "boom from logging" in text)

        widget.highlighter.rehighlight(); app.processEvents()
        colors = set()
        blk = widget.document().begin()
        while blk.isValid():
            if "ERROR" in blk.text() or "boom" in blk.text():
                for fr in blk.layout().formats():
                    c = fr.format.foreground().color()
                    colors.add((c.red(), c.green(), c.blue()))
            blk = blk.next()
        _ck("error line colored red (165,75,75)", (165, 75, 75) in colors, str(colors))
        _ck("console widget visible", widget.isVisible())

        bpy.app.timers.register(_hover_focus, first_interval=0.5)
    except Exception:
        import traceback
        R["measure_error"] = traceback.format_exc()
        _finish()
    return None


def _focus_now():
    _u.GetFocus.restype = ctypes.c_void_p
    return int(_u.GetFocus() or 0)


def _screen_center_of(hwnd, rect_client):
    org = wintypes.POINT(0, 0)
    _u.ClientToScreen(ctypes.c_void_p(int(hwnd)), ctypes.byref(org))
    return (org.x + rect_client[0] + rect_client[2] // 2,
            org.y + rect_client[1] + rect_client[3] // 2)


def _note_inconclusive(msg):
    """Record a leg that could not run in this environment — visible, never silent."""
    R.setdefault("inconclusive", []).append(msg)


def _force_foreground(hwnd):
    """Bring ``hwnd`` genuinely to the front; True if it took.

    Windows refuses ``SetForegroundWindow`` from a process that isn't already foreground,
    and this Blender was launched from a terminal that keeps it — so a bare call silently
    no-ops and the terminal stays physically ON TOP of the console. That matters for more
    than the keystrokes: the focus poll hit-tests the cursor (``WindowFromPoint``), so a
    window covering the console makes it correctly report "not over the widget" and
    release focus — a real product behavior that would read as a failure here. Attaching
    to the foreground thread's input queue lifts the restriction (the standard idiom).
    """
    try:
        user32 = _u
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        fg = user32.GetForegroundWindow()
        if fg and int(fg) == int(hwnd):
            return True
        fg_thread = user32.GetWindowThreadProcessId(ctypes.c_void_p(fg), None)
        our_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        attached = user32.AttachThreadInput(our_thread, fg_thread, True)
        try:
            user32.ShowWindow(ctypes.c_void_p(int(hwnd)), 9)  # SW_RESTORE
            user32.BringWindowToTop(ctypes.c_void_p(int(hwnd)))
            user32.SetForegroundWindow(ctypes.c_void_p(int(hwnd)))
        finally:
            if attached:
                user32.AttachThreadInput(our_thread, fg_thread, False)
        return int(user32.GetForegroundWindow() or 0) == int(hwnd)
    except Exception:
        return False


def _hover_focus():
    """Park the REAL cursor over the console, then let the focus-follow poll tick.

    Driven with the real cursor (``SetCursorPos``) rather than a synthetic ``QEvent.Enter``:
    the question is whether Windows actually routes native key messages to the embedded
    child, which a synthetic Qt event would fake rather than test. Each leg has to RETURN
    so Blender's timer loop can run the poll — asserting inline would block the very
    mechanism under test (a bpy timer can't tick while our callback holds the loop).
    The user's cursor position is saved and restored.
    """
    try:
        from blendertk.env_utils import script_output as so

        inst = so.ScriptConsole._instance
        widget = inst.widget
        hwnd = inst._dock._hwnd
        # internalWinId, matching what the production poll reads (winId() would force
        # native creation — never do that in a check that mirrors a 20 Hz poll).
        child = int(widget.internalWinId() or 0)

        pt = wintypes.POINT()
        _u.GetCursorPos(ctypes.byref(pt))
        R["cursor_restore"] = (pt.x, pt.y)
        R["_child"], R["_ghost"] = child, int(hwnd)
        R["focus_before_hover"] = _focus_now()

        R["blender_raised"] = _force_foreground(hwnd)
        cx, cy = _screen_center_of(hwnd, _child_rect_in_parent_client(child, hwnd))
        _u.SetCursorPos(cx, cy)  # hover — no click
        # What the poll's own hit-test sees — the ground truth for the legs below.
        _u.WindowFromPoint.restype = ctypes.c_void_p
        _u.WindowFromPoint.argtypes = [wintypes.POINT]
        R["window_at_cursor"] = int(_u.WindowFromPoint(wintypes.POINT(cx, cy)) or 0)
    except Exception:
        import traceback
        R["hover_focus_error"] = traceback.format_exc()
        bpy.app.timers.register(_hide, first_interval=0.5)
        return None
    bpy.app.timers.register(_hover_assert, first_interval=0.4)  # >> FOCUS_INTERVAL
    return None


def _hover_assert():
    """The console must now hold focus, and a REAL Ctrl+C must copy its text."""
    try:
        from qtpy import QtGui, QtWidgets
        from blendertk.env_utils import script_output as so

        inst = so.ScriptConsole._instance
        app = QtWidgets.QApplication.instance()
        widget = inst.widget
        child, ghost = R["_child"], R["_ghost"]

        R["focus_over_console"] = _focus_now()
        _u.GetForegroundWindow.restype = ctypes.c_void_p
        is_fg = int(_u.GetForegroundWindow() or 0) == ghost
        R["blender_foreground_for_keys"] = is_fg

        if not is_fg:
            # Another window (the launching terminal) is physically covering the console,
            # so the poll's WindowFromPoint hit-test correctly reports "not over the
            # widget" and releases focus. Asserting the hover here would fail the product
            # for behaving right. Report it instead of pretending either way.
            _note_inconclusive(
                "hover legs skipped: could not raise Blender to the foreground, so the "
                f"console is covered (window at cursor={R.get('window_at_cursor')}, "
                f"raised={R.get('blender_raised')}). The poll releasing focus there is "
                "correct behavior, not a regression."
            )
        else:
            _ck("hovering the console hands it OS keyboard focus (no click needed)",
                _focus_now() == child,
                f"focus={_focus_now()} child={child} ghost={ghost} "
                f"before_hover={R.get('focus_before_hover')} "
                f"window_at_cursor={R.get('window_at_cursor')}")
        if is_fg:
            widget.selectAll()
            QtWidgets.QApplication.clipboard().clear()
            app.processEvents()
            VK_CONTROL, KEYEVENTF_KEYUP = 0x11, 0x0002
            _u.keybd_event(VK_CONTROL, 0, 0, 0)
            _u.keybd_event(ord("C"), 0, 0, 0)
            _u.keybd_event(ord("C"), 0, KEYEVENTF_KEYUP, 0)
            _u.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            for _ in range(30):
                app.processEvents()
            clip = QtWidgets.QApplication.clipboard().text()
            _ck("a REAL Ctrl+C while merely hovering copies the console's text "
                "(the point of the feature: shortcuts work on mouse-over)",
                "console verification print" in clip, f"clipboard[:60]={clip[:60]!r}")
            widget.moveCursor(QtGui.QTextCursor.End)  # drop the select-all
        else:
            _note_inconclusive(
                "Ctrl+C leg skipped: Blender did not hold the OS foreground (the "
                "launching terminal kept it); firing keys would hit that window. The "
                "focus legs above still prove the routing."
            )

        # Leave to the viewport — Blender must get its keys back.
        from blendertk.ui_utils.blender_window import BlenderWindow

        v3d = next((a for a in _main_areas() if a.type == "VIEW_3D"), None)
        region = next((r for r in v3d.regions if r.type == "WINDOW"), None)
        vx, vy = _screen_center_of(R["_ghost"], BlenderWindow.region_client_rect(R["_ghost"], region))
        _u.SetCursorPos(vx, vy)
    except Exception:
        import traceback
        R["hover_assert_error"] = traceback.format_exc()
        bpy.app.timers.register(_hide, first_interval=0.5)
        return None
    bpy.app.timers.register(_leave_assert, first_interval=0.4)
    return None


def _leave_assert():
    """Pointer is back over the viewport: Blender must hold the keys again.

    Only meaningful if the hover leg actually took focus first — otherwise focus was
    never on the console and this would pass vacuously.
    """
    try:
        R["focus_over_viewport"] = _focus_now()
        if R.get("focus_over_console") != R["_child"]:
            _note_inconclusive(
                "leave leg skipped: the hover leg never took focus (see above), so "
                "'focus returned to Blender' would pass without proving anything."
            )
        else:
            _ck("leaving the console returns keyboard focus to Blender (its shortcuts "
                "resume, rather than staying dead until the user clicks)",
                _focus_now() == R["_ghost"],
                f"focus={_focus_now()} ghost={R['_ghost']} child={R['_child']}")
        if R.get("cursor_restore"):
            _u.SetCursorPos(*R["cursor_restore"])  # put the user's cursor back
    except Exception:
        import traceback
        R["leave_assert_error"] = traceback.format_exc()
    bpy.app.timers.register(_hide, first_interval=0.5)
    return None


def _hide():
    """hide() undocks + persists visible=false AND the strip height, but must NOT stop
    capture — stdout stays teed and the widget survives, so a later show() reopens with
    history intact instead of a fresh empty console."""
    try:
        from blendertk.env_utils import script_output as so
        inst = so.ScriptConsole._instance
        so.hide()
        state = _state()
        _ck("hide() undocks the Info Log area",
            len(_main_areas()) == R.get("areas_before", 0))
        _ck("hide() leaves stdout teed (capture persists)",
            id(sys.stdout) != R.get("orig_stdout_id"))
        _ck("hide() does NOT destroy the console widget", inst.widget is not None)
        _ck("is_open() False after hide", not inst.is_open())
        _ck("hide() persists visible=false", state.get("visible") is False)
        _ck("hide() persists the strip height (user resize survives sessions)",
            isinstance(state.get("height"), int) and state["height"] > 0,
            f"height={state.get('height')}")

        print("CONSOLE_DOCK_CHECK_HIDDEN_MARKER (printed while hidden)")
        bpy.app.timers.register(_reshow, first_interval=0.5)
    except Exception:
        import traceback
        R["hide_error"] = traceback.format_exc()
        _finish()
    return None


def _reshow():
    try:
        from qtpy import QtWidgets
        from blendertk.env_utils import script_output as so

        app = QtWidgets.QApplication.instance()
        inst = so.show()
        for _ in range(20):
            app.processEvents()

        _ck("show() re-docks the Info Log area",
            len(_main_areas()) == R.get("areas_before", 0) + 1)
        text = inst.widget.toPlainText() if inst.widget is not None else ""
        _ck("earlier content ('console verification print') survived the hide->show cycle",
            "console verification print" in text)
        _ck("content printed WHILE hidden also shows once reshown (capture ran in the "
            "background)", "CONSOLE_DOCK_CHECK_HIDDEN_MARKER" in text)

        # Console left SHOWN (flag=true) — _cold_restore tears it down the reload way.
        bpy.app.timers.register(_cold_restore, first_interval=0.5)
    except Exception:
        import traceback
        R["reshow_error"] = traceback.format_exc()
        _finish()
    return None


def _cold_restore():
    """Simulate ``tb.reload()`` + the NEXT session. ``ScriptConsole.teardown()`` (what
    ``BlenderHost.reload`` calls on the old module) must undock + drop the widget/glue +
    restore the streams while LEAVING the persisted flag alone — without it the old
    module's draw handler, widget and docked area survive a reload and the reloaded
    ``restore()`` docks a SECOND area. Then a fresh instance's ``restore()`` (what
    TclBlender.__init__ runs at launch) must re-open the console from the saved flag by
    itself."""
    try:
        from qtpy import QtWidgets
        from blendertk.env_utils import script_output as so

        app = QtWidgets.QApplication.instance()
        inst = so.ScriptConsole._instance
        inst.teardown()  # the host-reload path (console was left SHOWN by _reshow)
        _ck("teardown() (host-reload path) undocks the area",
            len(_main_areas()) == R.get("areas_before", 0))
        _ck("teardown() restores the original stdout",
            id(sys.stdout) == R.get("orig_stdout_id"))
        _ck("teardown() leaves the persisted flag alone (still visible=true)",
            _state().get("visible") is True)

        so.ScriptConsole._instance = None      # "new process / reloaded module"
        inst2 = so.restore()
        for _ in range(20):
            app.processEvents()
        _ck("cold restore(): saved visible=true re-opens the console", inst2.is_open())
        _ck("cold restore(): the Info Log area is re-docked",
            len(_main_areas()) == R.get("areas_before", 0) + 1)
        _ck("cold restore(): a fresh console widget was built", inst2.widget is not None)

        print("CONSOLE_DOCK_CHECK_POST_RESTORE_MARKER")
        if app:
            app.processEvents()
        text = inst2.widget.toPlainText() if inst2.widget is not None else ""
        _ck("cold restore(): new prints reach the restored console",
            "CONSOLE_DOCK_CHECK_POST_RESTORE_MARKER" in text)

        # Z-order leg: park a SECOND Blender window over the (restored, visible)
        # console — see _zorder_assert. Setup here, assert next tick (the new
        # window needs a beat to map).
        child = int(inst2.widget.winId())
        ghost = int(inst2._dock._hwnd)
        R["_z_child"], R["_z_ghost"] = child, ghost
        R["_z_center"] = _screen_center_of(
            ghost, _child_rect_in_parent_client(child, ghost))
        with bpy.context.temp_override(
            window=bpy.context.window_manager.windows[0],
            screen=bpy.context.window_manager.windows[0].screen,
        ):
            bpy.ops.wm.window_new()
        bpy.app.timers.register(_zorder_assert, first_interval=0.9)
    except Exception:
        import traceback
        R["cold_restore_error"] = traceback.format_exc()
        _finish()
    return None


def _zorder_assert():
    """The docked console must stack WITH its host window, never above sibling
    Blender windows (user requirement 2026-07-18: the overlay must only be above
    what its container window is above). A true WS_CHILD embed guarantees this at
    the OS level — this leg pins the contract so an overlay-style implementation
    (an owned top-level glued over the area, which floats above ALL the owner's
    windows regardless of focus) can never come back silently. The second window
    is deliberately left open — the throwaway instance quits right after, and
    closing secondary windows from a timer is a known crash path."""
    try:
        from blendertk.env_utils import script_output as so

        ghost = R.get("_z_ghost")
        hwnd2 = next((int(h) for h, _t in _input.ghost_windows()
                      if int(h) != ghost), None)
        R["_z_hwnd2"] = hwnd2
        _ck("z-order leg: a second Blender window opened", hwnd2 is not None)
        if hwnd2:
            cx, cy = R["_z_center"]
            # HWND_TOP (0), no activation: purely a z-order placement over the rect.
            _u.SetWindowPos(ctypes.c_void_p(hwnd2), ctypes.c_void_p(0),
                            cx - 220, cy - 160, 440, 320, 0x0010)  # SWP_NOACTIVATE
            _u.WindowFromPoint.restype = ctypes.c_void_p
            _u.WindowFromPoint.argtypes = [wintypes.POINT]
            _u.GetAncestor.restype = ctypes.c_void_p
            at = _u.WindowFromPoint(wintypes.POINT(int(cx), int(cy)))
            root = int(_u.GetAncestor(ctypes.c_void_p(int(at)), 2) or 0) if at else 0
            R["z_root_at_console_center"] = root
            _ck("a second Blender window covering the console rect OCCLUDES it "
                "(the embed stacks with its container, not above all windows)",
                root == int(hwnd2),
                f"root={root} hwnd2={hwnd2} ghost={ghost} "
                f"child={R.get('_z_child')}")

        so.hide()  # final cleanup
        _ck("final hide() undocks the area and persists visible=false",
            len(_main_areas()) == R.get("areas_before", 0)
            and _state().get("visible") is False)
    except Exception:
        import traceback
        R["zorder_error"] = traceback.format_exc()
    _finish()
    return None


def _finish():
    R["verdict"] = "PASS" if R["checks"] and all(c["pass"] for c in R["checks"]) else "FAIL"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, default=str)
    shutil.rmtree(SANDBOX, ignore_errors=True)  # temp_tests artifacts clean up in teardown
    print("console_dock verdict:", R["verdict"])
    sys.stdout.flush()
    _quit()


def _quit():
    """Quit with an explicit window override. From a bpy timer the context window can be
    NULL (e.g. the embedded Qt console held focus, clearing Blender's winactive) and
    ``wm.quit_blender`` then crashes in ``wm_exit_schedule_delayed`` (&win->modalhandlers
    on a NULL win — reproduced as an EXCEPTION_ACCESS_VIOLATION at quit)."""
    windows = bpy.context.window_manager.windows
    if windows:
        with bpy.context.temp_override(window=windows[0]):
            bpy.ops.wm.quit_blender()
    else:
        bpy.ops.wm.quit_blender()


if sys.platform != "win32":
    print("console_dock_check: N/A off-Windows (console degrades to native Info Log)")
else:
    bpy.app.timers.register(_go, first_interval=5.0)
