# !/usr/bin/python
# coding=utf-8
"""Does a standalone tentacle tool window over Blender take a single click? (FINDING: yes.)

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/first_click_check.py

Written to chase a "every tentacle button over Blender needs two clicks" report. The
hypothesis was a universal first-click-lost to window **activation** (Qt pumped from a
``bpy.app.timers`` tick over a non-Qt host, so a freshly-shown window isn't OS-foreground and
Windows eats the activating click). This harness **disproved that for standalone tool windows**:
a single injected click both activates the window and fires the slot, even in the faithful
post-gesture state (GHOST holding foreground, the panel visible-but-inactive). Kept as the
regression guard for that fact — if it ever starts needing two clicks, the window-activation
path regressed. (The marking-menu overlay surface is covered by ``hover_nav_check.py`` and
``grab_policy_check.py``.)

It shows a real standalone window (``selection`` — opened via the live ``tcl.show`` →
``_show_window`` path), wires a recorder to the first clickable slot button, makes GHOST the
foreground window, then injects ONE click and records whether the button's ``clicked`` fired.
Scenarios differ only in how activation is (or isn't) clawed back to the panel before the click:

  * ``repro_ghost_fg`` — GHOST foreground, nothing forced (the as-shipped path).
  * ``fix_activate``   — then ``win.raise_()`` + ``activateWindow()`` (the gentle Qt way).
  * ``fix_setfg``      — then Win32 ``SetForegroundWindow`` on the window.

All three fire on click #1; the scenarios remain as a differential probe should the finding change.

Steals foreground + moves the real mouse for a few seconds — throwaway instance only. Report
goes to stdout and ``../temp_tests/first_click_out.txt``.
"""
import sys
import os
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender --python doesn't
import _input  # noqa: E402

MONO = Path(__file__).resolve().parents[3]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "first_click_out.txt")

_u = _input.user32
_lines = []


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _first_button(window):
    """A real, clickable tentacle slot button in *window* (the recorder target).

    Prefer the slot buttons (b###/tb###/chk###) over chrome like collapse arrows
    and header pins, so the click lands on something whose `clicked` runs a slot.
    """
    from qtpy import QtWidgets

    candidates = [
        b for b in window.findChildren(QtWidgets.QAbstractButton)
        if b.isVisible() and b.isEnabled() and b.width() > 8 and b.height() > 8
    ]
    preferred = [
        b for b in candidates
        if (b.objectName() or "").lower().startswith(("b0", "tb0", "chk", "b1", "b2"))
    ]
    return (preferred or candidates or [None])[0]


def _button_screen_center(btn):
    """Screen-pixel (x, y) of the button's center."""
    gp = btn.mapToGlobal(btn.rect().center())
    return int(gp.x()), int(gp.y())


class _Recorder:
    """Counts MousePress reaching the button and `clicked` emissions."""

    def __init__(self, btn):
        self.presses = 0
        self.clicks = 0
        btn.clicked.connect(self._on_clicked)
        self._filter = self._make_filter()
        btn.installEventFilter(self._filter)

    def _on_clicked(self, *a):
        self.clicks += 1

    def _make_filter(self):
        from qtpy import QtCore

        rec = self

        class _F(QtCore.QObject):
            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    rec.presses += 1
                return False

        return _F()


def _fg_hwnd():
    return _u.GetForegroundWindow()


def _active_window_name():
    from qtpy import QtWidgets

    app = QtWidgets.QApplication.instance()
    w = app.activeWindow() if app else None
    if w is None:
        return None
    try:
        return w.objectName() or w.__class__.__name__
    except Exception:
        return repr(w)


def _run_scenario(tb, tcl, name, fix=None):
    """fix: None (repro), 'activate' (win.activateWindow), or 'setfg' (Win32 SetForegroundWindow)."""
    from qtpy import QtWidgets

    _log(f"\n=== scenario: {name} (fix={fix}) ===")
    app = QtWidgets.QApplication.instance()

    # Show a real standalone tentacle window through the live dispatcher.
    win = tcl.show("selection")
    for _ in range(40):
        app.processEvents()
    if win is None or not win.isVisible():
        _log("  FAIL: 'selection' window did not show:", repr(win))
        return
    _log(f"  window: objectName={win.objectName()!r} class={win.__class__.__name__} "
         f"isWindow={win.isWindow()}")

    # Pin so it survives the gesture/hide bookkeeping, and move to a known on-screen
    # spot so the injected coordinates are predictable (not centered on a roaming cursor).
    try:
        win.set_pinned(True)
    except Exception:
        pass
    win.move(120, 120)
    win.raise_()
    for _ in range(20):
        app.processEvents()

    btn = _first_button(win)
    if btn is None:
        _log("  FAIL: no clickable button found in window")
        return
    rec = _Recorder(btn)
    _log(f"  button: {btn.objectName()!r} ({btn.__class__.__name__}) "
         f"win_geo={win.geometry().getRect()}")

    ghost = _input.main_ghost_hwnd()
    # Faithfully reproduce the user's state after a gesture: GHOST holds OS foreground
    # (what `_restore_blender_foreground` does), the tentacle window visible-but-inactive.
    # allow_minimize=False: GHOST owns the visible tool window, so minimizing it to grab
    # foreground would hide the very window we're about to click.
    got_fg = _input.force_foreground(ghost, allow_minimize=False)
    for _ in range(20):
        app.processEvents()
    _log(f"  ghost_foreground established: {got_fg}")

    # Candidate fixes — applied AFTER GHOST has foreground, the way a real fix would have to
    # claw activation back to the just-shown tool window.
    if fix == "activate":
        win.raise_()
        win.activateWindow()
    elif fix == "setfg":
        try:
            _u.SetForegroundWindow(int(win.winId()))
        except Exception as e:
            _log("  setfg error:", repr(e))
    if fix:
        for _ in range(20):
            app.processEvents()

    x, y = _button_screen_center(btn)
    hit = QtWidgets.QApplication.widgetAt(x, y)
    hit_name = (hit.objectName() or hit.__class__.__name__) if hit else None
    _log(f"  before click  : fg_is_ghost={_fg_hwnd() == ghost} active_win={_active_window_name()!r} "
         f"cursor_target=({x},{y}) widgetAt={hit_name!r}")

    # Click #1
    _input.click_and_pump(app, x, y)
    _log(f"  after click #1 : presses={rec.presses} clicks={rec.clicks} "
         f"fg_is_ghost={_fg_hwnd() == ghost} active_win={_active_window_name()!r}")
    first_click_fired = rec.clicks > 0

    if not first_click_fired:
        _input.click_and_pump(app, x, y)
        _log(f"  after click #2 : presses={rec.presses} clicks={rec.clicks} "
             f"active_win={_active_window_name()!r}")

    _log(f"  VERDICT: first-click fired = {first_click_fired}  "
         f"(clicks needed = {1 if first_click_fired else 2 if rec.clicks else '>2'})")

    # Tear the window down for the next scenario.
    try:
        win.set_pinned(False)
    except Exception:
        pass
    win.hide()
    for _ in range(20):
        app.processEvents()


def _go():
    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from tentacle import tcl_blender as tb

    tcl = tb._KeymapBridge.tcl or tb.launch()

    try:
        _run_scenario(tb, tcl, "repro_ghost_fg", fix=None)
        _run_scenario(tb, tcl, "fix_activate", fix="activate")
        _run_scenario(tb, tcl, "fix_setfg", fix="setfg")
    except Exception as error:
        import traceback
        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
    finally:
        _finish()
    return None


def _finish():
    report = "\n".join(_lines)
    os.makedirs(os.path.dirname(os.path.normpath(OUT)), exist_ok=True)
    with open(os.path.normpath(OUT), "w", encoding="utf-8") as f:
        f.write(report)
    print("\n[written to]", os.path.normpath(OUT))
    sys.stdout.flush()

    def _quit():
        bpy.ops.wm.quit_blender()
        return None

    bpy.app.timers.register(_quit, first_interval=1.0)


# Defer until the UI + tentacle startup module have settled.
bpy.app.timers.register(_go, first_interval=4.0)
