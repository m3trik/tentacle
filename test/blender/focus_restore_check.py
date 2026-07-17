# !/usr/bin/python
# coding=utf-8
"""GUI harness: foreground hand-back after a Qt popup strands OS focus (F12-dead repro).

The live bug: navigate the marking menu → open an option_box dropdown → release F12 while it's
open → dismiss it. The dropdown (a ``Qt.Tool`` window) took OS activation; on hide, uitk restores
focus Qt-side only — it cannot target Blender's foreign GHOST window — so the OS foreground is
stranded on a hidden Qt window. F12 then reaches neither Blender's keymap (GHOST unfocused) nor
Qt (hidden shortcut owner) until the user clicks the viewport. This drives that exact flow
against the real host and pins the two fixes:

* **no strand after the popup closes** — the foreground must land in an F12-alive state: GHOST
  (WM fallback or the key-poller's foreground watchdog, ``restore_foreground_if_stranded``) or
  a *visible* Qt window (e.g. the restored Script Output console; the plain-press path serves
  it) — never a hidden Qt window. Then the end-to-end contract: an injected F12 immediately
  after the popup closed opens the marking menu, with no intervening click.
* **never-steal** — a *visible* Qt window holding the foreground keeps it (pinned tool panel);
  the watchdog must not yank focus while the user works in one of our windows.
* **plain-key parity** — with a visible tentacle Qt window foreground (GHOST unfocused, keymap
  can't fire), a physical F12 still opens the menu via the poller's plain-press path (Maya's
  ``ApplicationShortcut`` equivalent), and key-up hides it and returns the foreground to GHOST.

Must run in a *fresh GUI* Blender (never an existing session — session-safety rule); OS focus
only exists under a real window manager::

    blender --factory-startup --python tentacle/test/blender/focus_restore_check.py

PASS = every check true (``test/temp_tests/focus_restore_out.json``). If another application
holds the OS foreground when the probe starts (someone is using the desktop), the verdict is
``FOREGROUND_UNAVAILABLE`` — rerun with the desktop idle. A wedged Blender never writes the
JSON — the caller's timeout + taskkill handles that.
"""
import sys
import os
import json
import ctypes
from pathlib import Path

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

import bpy

OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                 "focus_restore_out.json")
)
VK_F12 = 0x7B
KEYEVENTF_KEYUP = 0x0002
R = {"checks": []}
user32 = ctypes.windll.user32


def _ck(name, cond, extra=""):
    R["checks"].append({"name": name, "pass": bool(cond), "extra": str(extra)})
    print(("PASS " if cond else "FAIL "), name, extra)
    sys.stdout.flush()


user32.GetForegroundWindow.restype = ctypes.c_void_p  # don't sign-extend bit-31 handles


def _fg():
    return int(user32.GetForegroundWindow() or 0)


def _describe(hwnd):
    """Best-effort identity of ``hwnd`` for failure logs: ours (class/name/visible) or foreign."""
    if not hwnd:
        return "none"
    try:
        from qtpy import QtWidgets

        for w in QtWidgets.QApplication.topLevelWidgets():
            if int(w.internalWinId() or 0) == int(hwnd):
                return f"ours:{type(w).__name__}/{w.objectName() or '-'}/vis={w.isVisible()}"
    except Exception:
        pass
    from ctypes import wintypes

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
    buf = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(ctypes.c_void_p(hwnd), buf, 64)
    tag = "our-pid-native" if pid.value == os.getpid() else f"pid={pid.value}"
    return f"foreign:{tag} class={buf.value}"


def _fg_keeps_f12_alive(ghost):
    """True when the current foreground is a state F12 works from: Blender's GHOST window
    (keymap path) or one of our VISIBLE Qt windows (poller plain-press path). Only a
    foreground stranded on a hidden Qt window — the bug — is dead."""
    hwnd = _fg()
    if hwnd == ghost:
        return True
    try:
        from qtpy import QtWidgets

        for w in QtWidgets.QApplication.topLevelWidgets():
            if int(w.internalWinId() or 0) == int(hwnd):
                return w.isVisible()
    except Exception:
        pass
    return False  # foreign (desktop interference) — treat as not-alive so it surfaces


def _center_cursor_on(hwnd):
    """Park the physical cursor over the window's center (≈ the 3D viewport in the factory
    layout) so a GHOST-focused key press routes to the 3D View region keymap — ours — instead
    of wherever the desktop mouse happens to hover."""
    from ctypes import wintypes

    rect = wintypes.RECT()
    user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
    user32.SetCursorPos((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)


def _click():
    """One left click at the current cursor position (mouse_event down+up)."""
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP


def _fg_is_ours():
    from ctypes import wintypes

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value == os.getpid()


def _pump(n=30):
    from qtpy import QtWidgets

    app = QtWidgets.QApplication.instance()
    for _ in range(n):
        app.processEvents()


def _steps():
    """Sequential probe steps; each ``yield seconds`` waits (poller + pump keep ticking)."""
    from tentacle import tcl_blender as tb

    tb.register()  # stands up the Qt host — qtpy is only importable after this
    yield 2.0  # host + keymap settle
    from qtpy import QtWidgets
    tcl = tb._KeymapBridge.tcl
    nw = tb._NativeWindow
    nw.blender_window()  # cache the GHOST hwnd
    app = QtWidgets.QApplication.instance()
    ghost = int(getattr(app, "_blender_native_hwnd", 0))
    R["ghost_hwnd"] = ghost
    _ck("host up: live TclBlender + GHOST hwnd cached", tcl is not None and ghost != 0)
    _ck("poller installed (watchdog host)", tb._KeymapBridge.poller is not None)

    if not _fg_is_ours():
        user32.SetForegroundWindow(ctypes.c_void_p(ghost))
        yield 0.5
    if not _fg_is_ours():
        R["verdict"] = "FOREGROUND_UNAVAILABLE"
        R["note"] = "another application holds the OS foreground — rerun with the desktop idle"
        return

    # Dismiss the factory-startup splash with one click in the viewport — while it is open
    # Blender swallows key input, which would falsely fail the F12 checks. This is probe setup,
    # not part of the contract under test (in the real flow the user has long been working in
    # Blender; the bug's "requires a click" happens BETWEEN the popup closing and the F12).
    _center_cursor_on(ghost)
    _click()
    _pump()
    yield 0.5

    # --- A. the repro: popup steals activation, hides, foreground must return to GHOST ---
    from uitk.widgets.menu import Menu

    menu = Menu()
    menu.add("QLabel", setText="focus probe")
    menu_hwnd = 0
    _center_cursor_on(ghost)  # popup shows at cursorPos → over the viewport, like the real flow
    # A live desktop can snatch the foreground between steps (the WM then denies our
    # SetForegroundWindow) — retake GHOST and retry the steal a few times before judging.
    for _attempt in range(3):
        user32.SetForegroundWindow(ctypes.c_void_p(ghost))
        _pump()
        yield 0.3
        menu.show_as_popup(position="cursorPos")  # anchor-independent positioning
        _pump()
        yield 0.4
        menu_hwnd = int(menu.winId())
        if _fg() == menu_hwnd:
            break
        menu.hide(force=True)
        _pump()
        yield 0.3
    stole = _fg() == menu_hwnd
    _ck("A: popup took the OS foreground (steal precondition)", stole,
        f"fg={_fg():#x} ({_describe(_fg())}) menu={menu_hwnd:#x}")
    if stole:
        # Mirror the real flow: what was active before the popup is the (now hidden) overlay.
        menu._active_window_before_show = tcl
        menu.hide(force=True)
        _pump()
        yield 1.5  # several watchdog ticks
        # The foreground may land on GHOST (WM fallback or watchdog heal) or on a still-visible
        # tool window like the restored Script Output console (never-steal keeps it; the poller
        # plain-press serves F12 there). Only a hidden-window strand — the bug — is dead.
        _ck("A: foreground not stranded on a hidden window after the popup closed",
            _fg_keeps_f12_alive(ghost), f"fg={_fg():#x} ({_describe(_fg())}) ghost={ghost:#x}")
        # The user-visible contract, end to end: F12 pressed RIGHT AFTER the popup closed must
        # open the marking menu (before the fix it required a viewport click first).
        _center_cursor_on(ghost)
        user32.keybd_event(VK_F12, 0, 0, 0)
        yield 0.4
        shown_after_popup = bool(tcl.isVisible())
        user32.keybd_event(VK_F12, 0, KEYEVENTF_KEYUP, 0)
        _ck("A: F12 immediately after the popup closed opens the marking menu (the reported bug)",
            shown_after_popup)
        yield 1.0

    # --- B. never-steal: a VISIBLE Qt window keeps the foreground it holds ---
    panel = QtWidgets.QWidget()
    panel.setWindowTitle("focus probe panel")
    panel.resize(220, 90)
    panel.show()
    panel.raise_()
    panel.activateWindow()
    _pump()
    yield 0.3
    panel_hwnd = int(panel.winId())
    got_panel = _fg() == panel_hwnd
    _ck("B: visible panel took the OS foreground", got_panel, f"fg={_fg():#x}")
    yield 1.0  # give the watchdog every chance to misbehave
    if got_panel:
        _ck("B: watchdog left the visible panel's foreground alone (never-steal)",
            _fg() == panel_hwnd, f"fg={_fg():#x}")

    # --- C. plain-key parity: F12 over a focused tentacle Qt window opens the menu ---
    if got_panel:
        user32.keybd_event(VK_F12, 0, 0, 0)  # physical-equivalent key-down (GetAsyncKeyState sees it)
        yield 0.4
        shown = bool(tcl.isVisible())
        user32.keybd_event(VK_F12, 0, KEYEVENTF_KEYUP, 0)
        _ck("C: menu visible while F12 held over the focused Qt panel (poller plain-press)", shown)
        yield 1.0
        _ck("C: menu hidden after F12 release", not tcl.isVisible())
        # Post-gesture the foreground may legitimately sit on GHOST *or* on the still-visible
        # panel (never-steal keeps a visible tentacle window's focus) — what must NOT remain
        # is a strand on a hidden window (F12 dead). Either state keeps F12 functional
        # (keymap when GHOST, poller plain-press when the panel).
        _ck("C: foreground not stranded on a hidden window after the gesture",
            _fg() in (ghost, panel_hwnd), f"fg={_fg():#x} ghost={ghost:#x} panel={panel_hwnd:#x}")
    panel.hide()

    R["verdict"] = ("PASS" if R["checks"] and all(c["pass"] for c in R["checks"]) else "FAIL")


_gen = None


def _drive():
    global _gen
    try:
        if _gen is None:
            _gen = _steps()
        return next(_gen)  # seconds until the next step
    except StopIteration:
        pass
    except Exception:
        import traceback

        R["error"] = traceback.format_exc()
    _finish()
    return None


def _finish():
    R.setdefault("verdict", "FAIL")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, default=str)
    print("focus_restore verdict:", R["verdict"])
    sys.stdout.flush()
    windows = bpy.context.window_manager.windows
    if windows:
        with bpy.context.temp_override(window=windows[0]):
            bpy.ops.wm.quit_blender()
    else:
        bpy.ops.wm.quit_blender()


# Deferred so the GUI + keyconfig are fully up before the host registers.
bpy.app.timers.register(_drive, first_interval=3.0)
