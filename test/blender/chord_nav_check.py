# !/usr/bin/python
# coding=utf-8
"""GUI harness: hover-drill the both-button chord tree through the Animation -> Rigging chain.

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --factory-startup --python tentacle/test/blender/chord_nav_check.py

Drives the REAL cursor over the real ``blender#startmenu`` and asserts each hover stacks the
expected ``<target>#submenu`` (``tcl.sb.current_ui``):

  * CONTROL: Mesh -> Vertex (the chain that predates the restructure) — if this fails, the
    harness gesture is at fault, not the tree.
  * Animation (``object_animation``) -> Rigging (``rig``) -> Pose — the chain the live
    "navigation is buggy / windows unreachable" report is about.
  * Object hub -> Modifiers.

At every level the visible MenuButton targets are logged, so a button auto-hidden by the
nav visibility policy (or a submenu that failed to stack) is explicit in the output. The log
file is written INCREMENTALLY (a hang still leaves evidence) and an unconditional failsafe
timer quits Blender after 90 s no matter what.

Steals foreground + moves the real mouse for ~40s — throwaway instance only. Report to
stdout and ``../temp_tests/chord_nav_out.txt``.
"""
import sys
import os
import time
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _input  # noqa: E402

MONO = Path(__file__).resolve().parents[3]
OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                 "chord_nav_out.txt")
)
_u = _input.user32


def _log(*args):
    msg = " ".join(str(a) for a in args)
    print(msg)
    sys.stdout.flush()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def _check(name, cond, detail=""):
    _log(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")
    return cond


_failed = []


def _tally(name, cond, detail=""):
    if not _check(name, cond, detail):
        _failed.append(name)
    return cond


def _failsafe_quit():
    """Absolute backstop: this instance must never outlive its usefulness."""
    _log("FAILSAFE QUIT (90s) — harness did not finish in time")
    _quit_blender()
    return None


def _quit_blender():
    try:
        import blendertk as btk

        win = btk.main_window()
        if win is not None:
            with bpy.context.temp_override(window=win):
                bpy.ops.wm.quit_blender()
            return
    except Exception:
        pass
    bpy.ops.wm.quit_blender()


def _hover_to(app, x, y, steps=14):
    """Glide the real cursor to (x, y) in small steps with relative jiggles so GHOST and Qt
    both generate the move/enter events hover-nav depends on, then dwell. Pumps Qt throughout."""
    pt = _input.wintypes.POINT()
    _u.GetCursorPos(_input.ctypes.byref(pt))
    sx, sy = pt.x, pt.y
    for i in range(1, steps + 1):
        cx = int(sx + (x - sx) * i / steps)
        cy = int(sy + (y - sy) * i / steps)
        _u.SetCursorPos(cx, cy)
        _u.mouse_event(_input.MOUSE_MOVE, 1, 0, 0, 0)   # nudge so GHOST refreshes hover
        _u.mouse_event(_input.MOUSE_MOVE, -1, 0, 0, 0)
        for _ in range(3):
            app.processEvents()
        time.sleep(0.03)
    t0 = time.time()
    while time.time() - t0 < 0.8:
        app.processEvents()
        time.sleep(0.02)


def _visible_targets(ui):
    from uitk.widgets.menuButton import MenuButton

    out = {}
    for b in ui.findChildren(MenuButton):
        if b.isVisibleTo(ui):
            out[b.property("target")] = b
    return out


def _drill(app, tcl, chain):
    """Hover each (target, expected_submenu) in turn; log visible targets per level."""
    from qtpy import QtGui

    for target, expected in chain:
        ui = tcl.sb.current_ui
        if ui is None:
            _tally(f"level for {target!r} has a current_ui", False)
            return False
        buttons = _visible_targets(ui)
        _log(f"    in {ui.objectName()!r}: visible targets={sorted(k for k in buttons if k)}")
        b = buttons.get(target)
        if not _tally(f"'{target}' button visible in {ui.objectName()!r}", b is not None):
            return False
        gp = b.mapToGlobal(b.rect().center())
        _hover_to(app, int(gp.x()), int(gp.y()))
        cur = tcl.sb.current_ui
        cur_name = cur.objectName() if cur else None
        if not _tally(f"hover '{target}' stacks {expected!r}", cur_name == expected,
                      f"current_ui={cur_name!r}"):
            return False
        # Alignment: the arriving submenu must slide its pair anchor (the
        # MenuButton sharing the launcher's ``target``) under the point where
        # the launcher was crossed — the regression the objectName-keyed
        # pairing silently broke on the freely-named Animation/Rigging files.
        # Compare against ``gp`` (the launcher center the glide targeted, ==
        # the transition's captured anchor), NOT the live cursor: this
        # harness shares the physical pointer with a live workstation, and a
        # mid-dwell nudge (or a GHOST warp) displaces QCursor.pos() while
        # leaving the software contract intact — measured live: one sporadic
        # 160-1140px cursor reading per run with pair_center == anchor_global
        # exact. Live cursor logged for context only.
        anchor_btn = _visible_targets(cur).get(target)
        if not _tally(f"'{target}' anchor present in {cur_name!r}",
                      anchor_btn is not None):
            return False
        ac = anchor_btn.mapToGlobal(anchor_btn.rect().center())
        cp = QtGui.QCursor.pos()
        dist = ((ac.x() - gp.x()) ** 2 + (ac.y() - gp.y()) ** 2) ** 0.5
        if not _tally(f"'{target}' anchor at trigger point in {cur_name!r}",
                      dist <= 12,
                      f"anchor=({ac.x()},{ac.y()}) trigger=({gp.x()},{gp.y()}) "
                      f"cursor=({cp.x()},{cp.y()}) dist={dist:.1f}px"):
            from uitk.widgets.menuButton import MenuButton

            for b in cur.findChildren(MenuButton):
                if b.property("target") == target:
                    c = b.mapToGlobal(b.rect().center())
                    _log(f"      [dup?] {b.objectName()!r} target={target!r} "
                         f"center=({c.x()},{c.y()}) visible={b.isVisibleTo(cur)}")
            return False
    return True


def _open_startmenu(tb, tcl, app):
    _u.SetCursorPos(760, 480)
    time.sleep(0.1)
    tcl._on_activation_press()
    for _ in range(30):
        app.processEvents()
    tcl.show("blender#startmenu", force=True)
    for _ in range(30):
        app.processEvents()
    ui = tcl.sb.current_ui
    return ui is not None and ui.objectName() == "blender#startmenu"


def _close(tb, tcl, app):
    try:
        tb._KeymapBridge.drive_release()
    except Exception:
        pass
    try:
        tcl.hide()
    except Exception:
        pass
    for _ in range(30):
        app.processEvents()
    time.sleep(0.2)


def _instrument():
    """Class-level logging shims on the hover-nav pipeline — installed BEFORE the
    MarkingMenu is constructed so even the timer-connected bound methods are wrapped.
    Logs every stage of a hover so a silently-swallowed hop is attributable."""
    from uitk.widgets.marking_menu._marking_menu import MarkingMenu

    from qtpy import QtGui

    orig_cached = MarkingMenu._cached_ui
    orig_set = MarkingMenu._set_submenu
    orig_perform = MarkingMenu._perform_transition
    orig_pos = MarkingMenu._position_submenu_smooth

    def cached_ui(self, name):
        ui = orig_cached(self, name)
        _log(f"      [cached_ui] {name!r} -> "
             f"{ui.objectName() if ui is not None else None!r}")
        return ui

    def set_submenu(self, ui, w):
        cp = QtGui.QCursor.pos()
        try:
            tl = w.mapToGlobal(w.rect().topLeft())
            rect = f"({tl.x()},{tl.y()})+{w.width()}x{w.height()}"
        except Exception:
            rect = "?"
        _log(f"      [set_submenu] ui={ui.objectName()!r} trigger={w.property('target')!r}"
             f" name={w.objectName()!r} cursor=({cp.x()},{cp.y()}) w_rect={rect}")
        return orig_set(self, ui, w)

    def position_smooth(self, ui, w, *, anchor_global=None):
        ag = f"({anchor_global.x()},{anchor_global.y()})" if anchor_global else None
        _log(f"      [pos] ui={ui.objectName()!r} w={w.objectName()!r}"
             f"/{w.property('target')!r} anchor_global={ag} ui_pos_before={ui.pos()}")
        result = orig_pos(self, ui, w, anchor_global=anchor_global)
        try:
            pair = self._find_pair_widget(ui, w)
            pc = pair.mapToGlobal(pair.rect().center()) if pair else None
            _log(f"      [pos] done pair={pair.objectName() if pair else None!r} "
                 f"pair_center={pc} ui_pos_after={ui.pos()}")
        except Exception as e:
            _log(f"      [pos] post-check error: {e!r}")
        return result

    MarkingMenu._position_submenu_smooth = position_smooth

    def perform_transition(self):
        ui = self._pending_transition_ui
        _log(f"      [transition] firing: pending={ui.objectName() if ui else None!r}")
        try:
            result = orig_perform(self)
        except Exception as e:
            import traceback

            _log(f"      [transition] RAISED {type(e).__name__}: {e}")
            _log(traceback.format_exc())
            raise
        _log(f"      [transition] done: current_ui="
             f"{self.sb.current_ui.objectName() if self.sb.current_ui else None!r}")
        return result

    MarkingMenu._cached_ui = cached_ui
    MarkingMenu._set_submenu = set_submenu
    MarkingMenu._perform_transition = perform_transition


def _run():
    try:
        for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
            _p = str(MONO / _pkg)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        os.environ.setdefault("QT_API", "pyside6")
        # tcl_blender first — it provisions qtpy/PySide6 for Blender's bundled Python.
        from tentacle import tcl_blender as tb
        from qtpy import QtWidgets

        _instrument()
        _log("harness: launching tentacle ...")
        tcl = tb._KeymapBridge.tcl or tb.launch()
        app = QtWidgets.QApplication.instance()
        _log("harness: tentacle up")

        for title, chain in (
            ("CONTROL: Mesh -> Vertex (pre-restructure chain)",
             [("mesh", "mesh#submenu"), ("vertex", "vertex#submenu")]),
            ("Animation -> Rigging -> Pose",
             [("object_animation", "object_animation#submenu"),
              ("rig", "rig#submenu"),
              ("pose", "pose#submenu")]),
            ("Object -> Modifiers",
             [("object", "object#submenu"), ("modifiers", "modifiers#submenu")]),
        ):
            _log(f"=== {title} ===")
            if _tally(f"startmenu opened for: {title}", _open_startmenu(tb, tcl, app)):
                _drill(app, tcl, chain)
            _close(tb, tcl, app)
    except Exception as error:
        import traceback

        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
        _failed.append("harness error")
    finally:
        _log(f"===RESULT: {'PASS' if not _failed else 'FAIL'}===")
        bpy.app.timers.register(_quit_blender, first_interval=1.0)
    return None


# Failsafe FIRST: whatever happens below, this instance exits.
bpy.app.timers.register(_failsafe_quit, first_interval=90.0)
bpy.app.timers.register(_run, first_interval=4.0)
