#!/usr/bin/python
# coding=utf-8
"""Regression guard for the Maya both-button chord menu's release, with no Slots class.

``ui/maya_menus/`` is a thin launcher for Maya's own menus: every node is a
:class:`MenuButton` with a bare target (``"key"``, ``"mesh_display"``), hover opens its
``<target>#submenu`` page, and a release opens Maya's own menu as a Switchboard window,
built by mayatk's ``MayaUiHandler`` (``MayaNativeMenus`` lifts the live menu's
``QAction`` rows). The pages carry no Slots class: the switchboard resolves a release's
target through the UI handler (``can_resolve`` names it, ``get`` builds it). Until
tentacle 0.17.0 a near-empty Slots class per page built the menu on hover, and was the
only thing that made the release resolve; now the menu builds on its first release and
a hover builds nothing.

Offscreen (no Maya): the real ``.ui`` files, the real switchboard and the real
``MayaUiHandler``; only ``MayaNativeMenus.get_menu`` is faked, as it reads Maya's menu
bar. The real build and window are proven in a GUI Maya (mayatk's
``test_native_menu_window``, tentacle's ``test_marking_menu_gui``). The Blender mirror is
``test_blender_menu_nav.py``.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")

_UI_DIR = Path(__file__).resolve().parents[1] / "tentacle" / "ui"
_MAYA_UI_DIR = _UI_DIR / "maya_menus"

try:
    from qtpy import QtWidgets
    from uitk import Switchboard, MarkingMenu
    from uitk.widgets.menuButton import MenuButton
    from mayatk.ui_utils import maya_native_menus
    from mayatk.ui_utils.maya_ui_handler import MayaUiHandler

    _QT_OK = maya_native_menus is not None
except Exception:  # pragma: no cover - environment without a Qt binding / mayatk
    _QT_OK = False

from _host import qt_widgets_available as _can_create_widgets

_QT_OK = _QT_OK and _can_create_widgets()


class _Nav:
    """Borrows the marking menu's real release-resolution methods to drive them offscreen."""

    if _QT_OK:
        _cached_ui = MarkingMenu._cached_ui
        _resolve_button_menu = MarkingMenu._resolve_button_menu

    def __init__(self, sb):
        self.sb = sb
        self._submenu_cache = {}


@unittest.skipUnless(_QT_OK, "needs a Qt binding (qtpy/PySide6) + mayatk")
class MayaChordMenuRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.builds = []

        class _Menu(QtWidgets.QWidget):
            def fit_to_window(self):
                pass

        def get_menu(native, key):
            cls.builds.append(key)
            native.menus[key] = widget = _Menu()
            return widget

        for patcher in (
            mock.patch.object(maya_native_menus.MayaNativeMenus, "get_menu", get_menu),
            mock.patch(
                "mayatk.ui_utils._ui_utils.UiUtils.get_main_window", return_value=None
            ),
        ):
            patcher.start()
            cls.addClassCleanup(patcher.stop)

        # context_tags={'maya'} mirrors TclMaya, so the nav visibility policy runs as live.
        cls.sb = Switchboard(
            ui_source=[str(_UI_DIR), str(_MAYA_UI_DIR)],
            log_level="ERROR",
            context_tags={"maya"},
        )
        # A handler is a singleton: a fresh one, bound to this switchboard.
        MayaUiHandler.reset_instance()
        cls.addClassCleanup(MayaUiHandler.reset_instance)
        cls.sb.register_handler("ui", MayaUiHandler(switchboard=cls.sb))
        cls.pages = sorted(p.stem for p in _MAYA_UI_DIR.glob("*.ui"))
        cls.targets = sorted(
            {
                b.target
                for page in cls.pages
                for b in cls.sb.get_ui(page).findChildren(MenuButton)
            }
        )

    def _hover(self, target):
        """Hover a ``target`` launcher: its ``<target>#submenu`` page loads and registers."""
        page = self.sb.get_ui(f"{target}#submenu")
        page.register_children()
        return page

    def _anchor(self, page, target):
        return next(b for b in page.findChildren(MenuButton) if b.target == target)

    def test_every_target_is_a_native_menu_the_handler_claims(self):
        self.assertTrue(self.targets, "no MenuButton targets found in ui/maya_menus")
        for target in self.targets:
            with self.subTest(target=target):
                self.assertIn(target, maya_native_menus.MayaNativeMenus.MENU_MAPPING)
                self.assertTrue(self.sb.ui_name_resolves(target))

    def test_hover_builds_no_menu_and_runs_no_slots_class(self):
        builds = len(self.builds)
        for target in self.targets:
            self._hover(target)
        self.assertEqual(self.builds[builds:], [], "a hover built a native menu")
        self.assertEqual(sorted(self.sb.slot_instances.keys()), [])

    def test_release_opens_the_native_menu_built_once(self):
        nav = _Nav(self.sb)
        for target in self.targets:
            with self.subTest(target=target):
                anchor = self._anchor(self._hover(target), target)
                self.assertEqual(self.sb.menu_button_target_name(anchor), target)
                menu = nav._resolve_button_menu(anchor)
                self.assertIsNotNone(menu, f"releasing {target} opened nothing")
                self.assertEqual(menu.objectName(), target)
                self.assertTrue(menu.has_tags("maya_menu"), f"{target}: not the native wrap")
                # A native menu is a standalone window, never a stacked submenu.
                self.assertFalse(menu.has_tags(["startmenu", "submenu"]))
                # A later release (a fresh gesture: no submenu cache) gets the same window.
                self.assertIs(_Nav(self.sb)._resolve_button_menu(anchor), menu)
                self.assertEqual(self.builds.count(target), 1)


if __name__ == "__main__":
    unittest.main()
