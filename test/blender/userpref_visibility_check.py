# !/usr/bin/python
# coding=utf-8
"""Regression check for "Preferences ▸ Hotkeys (b008) needs multiple clicks" — userpref window
visibility through the real slot.

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/userpref_visibility_check.py

Established findings (2026-07-12, this harness + isolated probes): the dispatch layer is FINE for
this button — the 2026-07-04 click-debug capture shows PRESS→RELEASE→SLOT_CALL→SLOT_RUN on every
click — and in a clean same-process state ``bpy.ops.screen.userpref_show()`` opens the
Preferences window foregrounded on click 1, re-raising it even when buried (measured here). The
failure mode is **cross-process foreground** (user last in Maya, clicking straight onto the Qt
panel): Windows denies GHOST the foreground transfer, the window opens/reuses fully obscured, and
retries never raise it — an invisible success that reads as a dead button.
``Preferences._open_preferences`` now surfaces op failures and explicitly lifts the window
(``_raise_ghost_window``); this harness pins the whole path.

Flow: full tentacle startup, ``preferences`` shown as a standalone window holding OS foreground,
then programmatic ``b008`` clicks — clean click, redundant click, and a retry with the prefs
window deliberately buried. Around each it logs the Blender window count, the OS foreground
window, and this process's window z-order. Any state where the Preferences window ends below the
Qt panel (or never foregrounds) is a REPRODUCED verdict.

Steals foreground for a few seconds — throwaway instance only. Report to stdout and
``../temp_tests/userpref_visibility_out.txt``.
"""
import os
import sys
import time
import ctypes
from ctypes import wintypes

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _input  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "userpref_visibility_out.txt")
u32 = _input.user32
_lines = []
state = {"phase": "wait", "t0": time.time(), "clicks": 0, "ui": None, "btn": None}


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _fg():
    hwnd = u32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(128)
    u32.GetWindowTextW(hwnd, buf, 128)
    return f"{hwnd:#x}:{buf.value!r}"


def _zorder():
    """This process's visible top-level windows, topmost first: (z, class, title, hwnd)."""
    pid = os.getpid()
    rows = []
    z = 0
    hwnd = u32.GetTopWindow(0)
    while hwnd:
        wpid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and u32.IsWindowVisible(hwnd):
            cls = ctypes.create_unicode_buffer(64)
            u32.GetClassNameW(hwnd, cls, 64)
            title = ctypes.create_unicode_buffer(128)
            u32.GetWindowTextW(hwnd, title, 128)
            rows.append((z, cls.value, title.value, f"{hwnd:#x}"))
        z += 1
        hwnd = u32.GetWindow(hwnd, 2)  # GW_HWNDNEXT
    return rows


def _log_state(tag):
    wm = bpy.context.window_manager
    _log(f"  {tag}: blender_windows={len(wm.windows)} fg={_fg()}")
    for row in _zorder():
        _log(f"    z={row[0]:>3} {row[1]:<28} {row[2]!r} {row[3]}")


def _finish():
    report = "\n".join(_lines)
    os.makedirs(os.path.dirname(os.path.normpath(OUT)), exist_ok=True)
    with open(os.path.normpath(OUT), "w", encoding="utf-8") as f:
        f.write(report)
    print("\n[written to]", os.path.normpath(OUT))
    sys.stdout.flush()

    def _quit():
        wm = bpy.context.window_manager
        target = bpy.context.window or (wm.windows[0] if wm.windows else None)
        try:
            with bpy.context.temp_override(window=target):
                bpy.ops.wm.quit_blender()
        except Exception:
            os._exit(0)
        return None

    bpy.app.timers.register(_quit, first_interval=1.0)


def _step():
    elapsed = time.time() - state["t0"]
    if elapsed > 60:
        _log("TIMEOUT — aborting")
        _finish()
        return None
    try:
        if state["phase"] == "wait":
            tb = sys.modules.get("tentacle.tcl_blender")
            if tb is None or tb._KeymapBridge.tcl is None:
                return 0.5  # startup script hasn't registered yet
            state["tb"] = tb
            state["phase"] = "show"
            return 0.5

        if state["phase"] == "show":
            tcl = state["tb"]._KeymapBridge.tcl
            ui = tcl.sb.loaded_ui.preferences
            ui.show()
            state["ui"] = ui
            state["phase"] = "focus"
            return 0.5

        if state["phase"] == "focus":
            from qtpy import QtWidgets

            ui = state["ui"]
            if not ui.isVisible():
                _log("preferences window did not become visible")
                _finish()
                return None
            hwnd = int(ui.winId())
            got_fg = _input.force_foreground(hwnd, allow_minimize=False)
            if not got_fg:
                _log("note: force_foreground(panel) not granted — verdicts may be noisy")
            btn = next((b for b in ui.findChildren(QtWidgets.QAbstractButton)
                        if b.objectName() == "b008"), None)
            if btn is None:
                _log("b008 not found on preferences UI")
                _finish()
                return None
            state["btn"] = btn
            _log(f"=== state before any click (qt panel hwnd={hwnd:#x}) ===")
            _log_state("before")
            state["phase"] = "click"
            return 0.5

        if state["phase"] == "click":
            state["clicks"] += 1
            n = state["clicks"]
            _log(f"=== click {n} on b008 (Hotkeys) ===")
            state["btn"].click()  # synchronous: SlotWrapper -> Preferences.b008
            _log_state(f"after click {n}")
            if n >= 2:
                state["phase"] = "bury"
            return 1.5  # next step, like a user retrying

        if state["phase"] == "bury":
            # The persistent-dead-click half: the prefs window EXISTS but got covered/buried by
            # something (gesture foreground-restore, monitor layout, a one-off race). The user
            # refocuses the Qt panel and clicks Hotkeys again — does the REUSE path raise it?
            ghosts = _input.ghost_windows()
            pref_hwnds = [h for h, t in ghosts if "Preferences" in t]
            if not pref_hwnds:
                _log("VERDICT: NO Preferences window exists after 2 clicks — op failed outright")
                _finish()
                return None
            HWND_BOTTOM = 1
            SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE = 0x2, 0x1, 0x10
            u32.SetWindowPos(pref_hwnds[0], HWND_BOTTOM, 0, 0, 0, 0,
                             SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
            _input.force_foreground(int(state["ui"].winId()), allow_minimize=False)
            state["pref_hwnd"] = pref_hwnds[0]
            _log("=== prefs window sent to bottom; Qt panel refocused (simulates 'covered') ===")
            _log_state("buried")
            state["phase"] = "click3"
            return 1.0

        if state["phase"] == "click3":
            _log("=== click 3 on b008 (retry with existing-but-buried prefs window) ===")
            state["btn"].click()
            _log_state("after click 3")
            fg = u32.GetForegroundWindow()
            rows = _zorder()
            pref_z = next((z for z, _c, t, h in rows if int(h, 16) == state["pref_hwnd"]), None)
            panel_z = next((z for z, _c, _t, h in rows if int(h, 16) == int(state["ui"].winId())), None)
            if fg == state["pref_hwnd"] or (pref_z is not None and panel_z is not None and pref_z < panel_z):
                _log("VERDICT: reuse path RAISES the buried prefs window — not reproduced")
            else:
                _log("VERDICT: REPRODUCED — with the prefs window buried, a retry click runs the "
                     "slot but never raises/foregrounds it: a persistently 'dead' button")
            _finish()
            return None

    except Exception as error:
        import traceback

        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
        _finish()
        return None
    return 0.5


bpy.app.timers.register(_step, first_interval=3.0, persistent=True)
