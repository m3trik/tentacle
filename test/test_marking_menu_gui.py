"""GUI-level integration tests for the tentacle marking menu.

Drives the gesture pipeline against the real ``TclMaya`` instance with
real ``cameras#startmenu`` / ``main#startmenu`` / ``animation#submenu``
.ui files. Verifies the user-facing flow end-to-end: each registered
menu actually loads, becomes visible, and lands on screen.

## Layered coverage

The geometry-persistence-loop primitive that caused the 200x100
cropped-cameras regression is unit-tested in uitk:

* ``uitk/test/test_mainwindow.py::TestMainWindowGeometry`` — the
  ``restore_window_size=False`` opt-out blocks both save-on-hide and
  restore-on-show.
* ``uitk/test/test_marking_menu.py::TestStackedMenuPersistenceOptOut``
  — ``MarkingMenu._init_ui`` correctly applies the opt-out for stacked
  startmenu / submenu UIs.

This file stays as the integration smoke test: it confirms the upstream
fix actually wires up correctly when bound to tentacle's TclMaya.

## Skip behaviour

Requires both an interactive-Qt context and a Maya runtime, since
``TclMaya`` imports ``maya.cmds`` at module load and the marking-menu
shows real ``QMainWindow`` widgets.

* Plain Python:                      skip — no Maya
* ``mayapy --include-slots`` (batch): skip — Qt is a stub, widgets crash
* ``run_tests.py --in-maya``:        runs — full Qt + Maya GUI

This is the same gating ``test_overlay_safety`` uses.
"""
from __future__ import annotations

import unittest
from typing import Optional


def _can_run_marking_menu_tests() -> bool:
    """True iff TclMaya can be instantiated and shown.

    Needs real-widget Qt (not the mayapy.standalone stub) and a Maya
    runtime — TclMaya imports maya.cmds at module load.
    """
    try:
        import maya.cmds as cmds
    except ImportError:
        return False
    try:
        if cmds.about(batch=True):
            return False
    except Exception:
        return False
    return True


_SKIP_REASON = (
    "Marking-menu GUI tests need an interactive-Qt + Maya context "
    "(run via run_tests.py --in-maya, not mayapy.standalone or plain Python)."
)


# Qt button mask values — avoid Qt import at module load so module
# discovery works even without Qt available.
_LEFT = 0x00000001
_RIGHT = 0x00000002
_MIDDLE = 0x00000004


@unittest.skipUnless(_can_run_marking_menu_tests(), _SKIP_REASON)
class MarkingMenuGuiTest(unittest.TestCase):
    """Drives the gesture pipeline against real widgets.

    Each test gets a fresh ``QMainWindow`` parent and ``TclMaya`` so that
    state (registry-persisted geometry, hover transitions, submenu cache)
    cannot leak between cases.
    """

    LEFT = _LEFT
    RIGHT = _RIGHT
    MIDDLE = _MIDDLE

    @classmethod
    def setUpClass(cls):
        from qtpy import QtWidgets

        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from qtpy import QtWidgets, QtGui
        from tentacle.tcl_maya import TclMaya

        self.parent = QtWidgets.QMainWindow()
        self.parent.resize(1920, 1080)
        self.parent.show()
        self._process()

        screen = self.parent.screen() if hasattr(self.parent, "screen") else None
        if screen is not None:
            ag = screen.availableGeometry()
            self.screen_geom = (ag.x(), ag.y(), ag.width(), ag.height())
        else:
            self.screen_geom = (0, 0, 1920, 1080)

        # Cursor parked at screen center → menu positioning is deterministic
        # regardless of where the host left the pointer.
        sx, sy, sw, sh = self.screen_geom
        QtGui.QCursor.setPos(sx + sw // 2, sy + sh // 2)
        self._process()

        self.mm = TclMaya(parent=self.parent)
        self._process()
        self.mm._activation_key_held = True

    def tearDown(self):
        try:
            self.mm._activation_key_held = False
            if self.mm._current_widget is not None:
                self.mm._current_widget.hide()
            self.mm.hide()
        except Exception:
            pass
        try:
            self.parent.hide()
            self.parent.deleteLater()
        except Exception:
            pass
        self._process()

    # ── helpers ─────────────────────────────────────────────────────

    def _process(self, times: int = 3) -> None:
        from qtpy import QtWidgets

        for _ in range(times):
            QtWidgets.QApplication.processEvents()

    def _wait(self, ms: int = 50) -> None:
        from qtpy.QtCore import QEventLoop, QTimer

        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec_()
        self._process()

    def _activate(self, buttons: int = 0, modifiers: int = 0):
        try:
            self.mm._sync_menu_to_state(buttons=buttons, modifiers=modifiers)
        except Exception as e:
            self.fail(f"_sync_menu_to_state raised: {type(e).__name__}: {e}")
        self._process(5)
        return self.mm._current_widget

    def _find_loaded_ui(self, name: str):
        if name in list(self.mm.sb.loaded_ui.keys()):
            return self.mm.sb.loaded_ui.raw(name)
        return None

    def _find_button(self, ui, accessible_name: str):
        from qtpy import QtWidgets

        for btn in ui.findChildren(QtWidgets.QPushButton):
            if btn.accessibleName() == accessible_name:
                return btn
        return None

    def _find_menu_button(self, ui, target: str):
        """Find a ``MenuButton`` in *ui* by its ``target`` property.

        The type-based nav widget carries no ``accessibleName`` (it reads
        ``target``/``filterTags``), so it can't be found via ``_find_button``.
        """
        from uitk.widgets.menuButton import MenuButton

        for btn in ui.findChildren(MenuButton):
            if btn.target == target:
                return btn
        return None

    def _hover_button(self, button) -> None:
        """Move cursor onto button and dispatch the enterEvent path.

        ``_perform_transition`` aborts silently if the cursor isn't over
        the target — moving the cursor first is required for the timer
        to fire the submenu reveal.
        """
        from qtpy import QtCore, QtGui

        center = button.mapToGlobal(button.rect().center())
        QtGui.QCursor.setPos(center)
        self._process(2)

        enter_event = QtGui.QEnterEvent(
            QtCore.QPointF(button.rect().center()),
            QtCore.QPointF(button.rect().center()),
            QtCore.QPointF(center),
        )
        self.mm.child_enterEvent(button, enter_event)
        self._process(5)
        # 8ms transition timer + a margin
        self._wait(80)

    # ── assertions ──────────────────────────────────────────────────

    def _assert_visible(self, name: str):
        ui = self._find_loaded_ui(name)
        self.assertIsNotNone(ui, f"UI not loaded: {name!r}")
        self.assertTrue(
            ui.isVisible(),
            f"{ui.objectName()} not visible "
            f"(geom=({ui.x()},{ui.y()},{ui.width()},{ui.height()}))",
        )
        return ui

    def _assert_on_screen(self, ui):
        from qtpy import QtCore, QtWidgets

        # Use GLOBAL geometry: the menu UI is a child of the MarkingMenu, so
        # ui.x()/y() are parent-relative, not screen coordinates.
        top_left = ui.mapToGlobal(QtCore.QPoint(0, 0))
        x, y, w, h = top_left.x(), top_left.y(), ui.width(), ui.height()

        # Check against the screen the menu actually opened on, not the host
        # window's screen. On multi-monitor the menu opens on the cursor's
        # screen (which need not match parent.screen()), and QCursor.setPos to
        # a secondary monitor isn't always honored — so pinning the assertion
        # to parent.screen() made it depend on the physical monitor layout.
        center = QtCore.QPoint(x + w // 2, y + h // 2)
        screen = (
            QtWidgets.QApplication.screenAt(center)
            or ui.screen()
            or self.parent.screen()
        )
        ag = screen.availableGeometry()
        sx, sy, sw, sh = ag.x(), ag.y(), ag.width(), ag.height()

        cropped = []
        if y < sy:
            cropped.append(f"top by {sy - y}px")
        if x < sx:
            cropped.append(f"left by {sx - x}px")
        if x + w > sx + sw:
            cropped.append(f"right by {(x + w) - (sx + sw)}px")
        if y + h > sy + sh:
            cropped.append(f"bottom by {(y + h) - (sy + sh)}px")
        if cropped:
            self.fail(
                f"{ui.objectName()} extends off-screen "
                f"({', '.join(cropped)}); geom=({x},{y},{w},{h}) "
                f"screen=({sx}, {sy}, {sw}, {sh})"
            )

    # ── tests ───────────────────────────────────────────────────────

    def test_cameras_lmb_shows_on_screen(self):
        """F12 + LMB presents cameras#startmenu fully on-screen."""
        self._activate(buttons=self.LEFT)
        ui = self._assert_visible("cameras#startmenu")
        self._assert_on_screen(ui)

    def test_main_rmb_shows_on_screen(self):
        """F12 + RMB presents main#startmenu fully on-screen."""
        self._activate(buttons=self.RIGHT)
        ui = self._assert_visible("main#startmenu")
        self._assert_on_screen(ui)

    def test_animation_submenu_appears_from_main(self):
        """Hovering 'animation' from main#startmenu reveals animation#submenu."""
        self._activate(buttons=self.RIGHT)
        main_ui = self._find_loaded_ui("main#startmenu")
        self.assertIsNotNone(main_ui, "main#startmenu did not load")

        btn = self._find_button(main_ui, "animation")
        self.assertIsNotNone(
            btn, "no button with accessibleName='animation' in main#startmenu"
        )

        self._hover_button(btn)
        ui = self._assert_visible("animation#submenu")
        self._assert_on_screen(ui)

    def test_default_F12_shows_hud(self):
        """F12 with no mouse button shows hud#startmenu."""
        self._activate(buttons=0)
        ui = self._assert_visible("hud#startmenu")
        self._assert_on_screen(ui)

    # ── chord-release tolerance (real imperfect L+R timing) ─────────────

    def _send_release(self, button_mask: int, buttons_after_mask: int) -> None:
        """Send a REAL mouse release to the MarkingMenu at the live cursor — the
        Maya grab path (``mouseReleaseEvent``). ``button_mask`` is the button just
        released; ``buttons_after_mask`` the buttons still physically held."""
        from qtpy import QtCore, QtGui, QtWidgets

        gp = QtGui.QCursor.pos()
        ev = QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QPointF(self.mm.mapFromGlobal(gp)),
            QtCore.QPointF(gp),
            QtCore.Qt.MouseButton(button_mask),
            QtCore.Qt.MouseButtons(buttons_after_mask),
            QtCore.Qt.NoModifier,
        )
        QtWidgets.QApplication.sendEvent(self.mm, ev)
        self._process(2)

    def test_imperfect_both_button_release_does_not_switch_menus(self):
        """Real-world imperfect L+R release: the two buttons lift a few ms apart,
        so the first release arrives with the other still held. The chord menu
        must NOT collapse to a single-button menu (the "stays open and shifts
        while the item under the cursor never clicks" regression) — the partial is
        deferred for the tolerance window, and the within-tolerance final release
        completes the both-buttons gesture.

        This is the case the offscreen instant-fire tests missed: it requires a
        real timing gap, so it drives real release events and a real wait.
        """
        self._activate(buttons=self.LEFT | self.RIGHT)
        self._assert_visible("maya#startmenu")
        tol = self.mm.CHORD_RELEASE_TOLERANCE_MS

        # R up first, with L still held — must be deferred (no immediate switch).
        self._send_release(self.RIGHT, self.LEFT)
        self.assertEqual(
            self.mm.sb.current_ui.objectName(),
            "maya#startmenu",
            "a partial chord release must be deferred — the menu must not switch "
            "to the remaining-button menu immediately (the shift)",
        )

        # L up within the tolerance → the both-buttons release completes.
        self._wait(int(tol * 0.4))
        self._send_release(self.LEFT, 0)
        self._process(3)

        cur = self.mm.sb.current_ui
        cur_name = cur.objectName() if cur else ""
        self.assertNotIn(
            cur_name,
            ("cameras#startmenu", "main#startmenu"),
            "an imperfect both-buttons release wrongly collapsed to a single-button "
            "menu — the 'menu stays open and shifts' regression",
        )

    def test_release_one_button_held_past_tolerance_switches(self):
        """Releasing ONE chord button and HOLDING the other past the tolerance is
        an intentional switch → the remaining-button menu appears. The tolerance
        is exactly what separates this from an imperfect both-buttons release."""
        self._activate(buttons=self.LEFT | self.RIGHT)
        self._assert_visible("maya#startmenu")
        tol = self.mm.CHORD_RELEASE_TOLERANCE_MS

        # Release R, keep L held, wait past the tolerance → switch to L (cameras).
        self._send_release(self.RIGHT, self.LEFT)
        self._wait(int(tol * 1.8))
        self._assert_visible("cameras#startmenu")

    def test_both_button_release_over_menu_button_registers_click(self):
        """THE reported bug. In maya#startmenu, hover the 'key' MenuButton (it
        reveals key#submenu and parks the cursor over its 'key' widget), then
        release BOTH buttons over it. The click must REGISTER (dispatch the nav)
        on the FIRST release — it must NOT be lost while the menu 'stays open and
        shifts'. A release over an owned item fires immediately, with NO wait for
        the tolerance window (the tolerance governs navigation over empty overlay
        only). The trailing release is swallowed by the latch, so the click
        dispatches exactly once."""
        self._activate(buttons=self.LEFT | self.RIGHT)
        maya_ui = self._assert_visible("maya#startmenu")

        key_btn = self._find_menu_button(maya_ui, "key")
        self.assertIsNotNone(
            key_btn, "no MenuButton with target='key' in maya#startmenu"
        )

        # Hover reveals key#submenu and centers its 'key' widget under the cursor.
        self._hover_button(key_btn)
        self._assert_visible("key#submenu")

        dispatched = []
        orig = self.mm._handle_widget_action

        def spy(widget, global_pos=None):
            dispatched.append(widget)
            return orig(widget, global_pos)

        self.mm._handle_widget_action = spy

        # R up first (partial), L still held — owned-item release fires NOW.
        self._send_release(self.RIGHT, self.LEFT)
        self.assertTrue(
            dispatched,
            "the click over the 'key' MenuButton was not registered on the "
            "both-button release (the dead-click / 'stays open and shifts' bug)",
        )

        # L up (final) — swallowed by the single-shot latch; no second dispatch.
        self._send_release(self.LEFT, 0)
        self.assertEqual(
            len(dispatched),
            1,
            "the both-button release must dispatch the click exactly once",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
