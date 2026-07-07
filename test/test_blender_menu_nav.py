#!/usr/bin/python
# coding=utf-8
"""Regression guard for the Blender both-button chord menu — structure + navigation resolution.

The chord menu (``ui/blender_menus/``) is a **thin launcher** for Blender's own native viewport
menus — the exact mirror of ``ui/maya_menus/``, NOT part of tentacle's custom marking-menu system.
It mirrors maya_menus on every axis:

* **Pure MenuButtons.** Every node — startmenu, hub, and leaf — is a :class:`MenuButton`; there
  are **no** plain ``QPushButton``s anywhere (maya_menus has none either).
* **Flat filenames.** Each node's ``target`` is a **bare** name (``"mesh"``, ``"select"``,
  ``"vertex"`` …) and gets its own flat ``<name>#submenu.ui`` — exactly Maya's
  ``edit_mesh#submenu.ui`` / ``select#submenu.ui``. No nested ``blender#mesh#vertex#submenu``.
* **Each node its own submenu.** A hub file lists self + child MenuButtons; a leaf file holds one
  self-referencing MenuButton. Hover opens ``<target>#submenu``; release resolves the bare target.

**Wrapped, not recreated.** On release the bare target resolves through
``BlenderUiHandler.can_resolve`` (membership in :class:`BlenderNativeMenus`) to a native-menu
*proxy*, whose ``show`` pops Blender's real menu via ``wm.call_menu`` — the Blender analogue of
Maya harvesting its live ``QAction`` rows. The resolution table lives in **blendertk**
(``BlenderNativeMenus``), so these MenuButtons carry no tentacle slots — like maya_menus.

This suite is **offscreen (no bpy)**: it loads the real ``.ui`` files and drives the marking
menu's real release-resolution methods against a proxy handler built from the real
``BlenderNativeMenus`` mapping. The real ``BlenderUiHandler`` registration + the actual native
pop (which need bpy) are proven under a live Blender by ``test/blender/blender_menus_check.py``.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")

_UI_DIR = Path(__file__).resolve().parents[1] / "tentacle" / "ui"
_BLENDER_UI_DIR = _UI_DIR / "blender_menus"

try:
    from qtpy import QtWidgets  # noqa: F401
    from uitk import Switchboard
    from uitk.widgets.menuButton import MenuButton
    from uitk.widgets.marking_menu._marking_menu import MarkingMenu
    from blendertk.ui_utils.blender_native_menus import BlenderNativeMenus
    from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler

    _QT_OK = True
except Exception:  # pragma: no cover - environment without a Qt binding / blendertk
    _QT_OK = False


# The full flat tree — file -> [bare node targets it contains]. Startmenu + 5 hubs are branch
# files (self + children); everything else is a one-button leaf. Mirrors ui/maya_menus' shape
# (8 top categories, hub clustering, one 3-level branch: Armature -> Pose) with Blender domains.
_BRANCH_FILES = {
    "blender#startmenu": ["view", "select", "add", "object", "mesh", "curve", "armature", "render"],
    "mesh#submenu": ["mesh", "vertex", "edge", "face", "mesh_uv", "mesh_normals"],
    "curve#submenu": ["curve", "ctrl_points", "segments", "surface"],
    "armature#submenu": ["armature", "pose"],
    "pose#submenu": ["pose", "constraints", "ik"],
    "render#submenu": ["render", "window", "help"],
}
# Every node that is not a hub gets a one-button leaf file (self-referencing MenuButton).
_LEAF_NODES = [
    "view", "select", "add", "object", "vertex", "edge", "face", "mesh_uv", "mesh_normals",
    "ctrl_points", "segments", "surface", "constraints", "ik", "window", "help",
]
_HUB_NODES = ["mesh", "curve", "armature", "pose", "render"]


@unittest.skipUnless(_QT_OK, "needs a Qt binding (qtpy/PySide6) + blendertk")
class BlenderChordMenuStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        # context_tags={'blender'} mirrors TclBlender so the nav visibility policy runs as live.
        cls.sb = Switchboard(
            ui_source=[str(_UI_DIR), str(_BLENDER_UI_DIR)],
            log_level="ERROR",
            context_tags={"blender"},
        )
        # Exercise the REAL BlenderUiHandler native-menu wrap offscreen: bypass __init__ (it scans
        # the blendertk package + needs a resolvable package __file__, neither relevant here) and
        # drive only the native-menu methods — the same pattern test/blender/blender_menus_check.py
        # uses. Held on the class so its strong proxy refs survive (loaded_ui is weak).
        cls._handler = object.__new__(BlenderUiHandler)
        cls._handler.sb = cls.sb
        cls._handler._register_native_menu_proxies()
        cls.sb.handlers.ui = cls._handler
        cls.nav = _Nav(cls.sb)

    # ── file-graph shape ────────────────────────────────────────────────
    def test_file_set_is_exactly_the_flat_tree(self):
        """The blender_menus dir holds exactly startmenu + 5 hubs + 16 leaves — no stray
        (old nested ``blender#...#submenu``) files, none missing."""
        on_disk = {p.stem for p in _BLENDER_UI_DIR.glob("*.ui")}
        expected = {"blender#startmenu"}
        expected |= {f"{h}#submenu" for h in _HUB_NODES}
        expected |= {f"{leaf}#submenu" for leaf in _LEAF_NODES}
        self.assertEqual(on_disk, expected, f"unexpected: {on_disk ^ expected}")
        self.assertEqual(len(expected), 22)

    def test_filenames_are_flat_like_maya_menus(self):
        """Every submenu file is a flat ``<name>#submenu`` (two segments, no ``blender#`` prefix,
        no nesting) — only the startmenu is ``blender#startmenu``. Guards the exact regression the
        earlier build introduced (``blender#mesh#vertex#submenu``)."""
        for p in _BLENDER_UI_DIR.glob("*.ui"):
            stem = p.stem
            if stem == "blender#startmenu":
                continue
            parts = stem.split("#")
            self.assertEqual(
                len(parts), 2, f"{stem} is not a flat <name>#submenu (parts={parts})"
            )
            self.assertEqual(parts[1], "submenu", f"{stem} must end in #submenu")
            self.assertNotEqual(parts[0], "blender", f"{stem} must not carry the blender# prefix")

    # ── every node is a MenuButton with a bare target + its own submenu ──
    def test_branch_files_contain_only_menubuttons(self):
        for file_name, nodes in _BRANCH_FILES.items():
            with self.subTest(file=file_name):
                ui = self.sb.get_ui(file_name)
                self.assertIsNotNone(ui, f"{file_name} failed to load")
                buttons = ui.findChildren(QtWidgets.QAbstractButton)
                self.assertEqual(len(buttons), len(nodes), f"{file_name} button count")
                for w in buttons:
                    self.assertIsInstance(
                        w, MenuButton,
                        f"{file_name}.{w.objectName()} ('{w.text()}') is a plain button — "
                        "maya_menus has none; every node must be a MenuButton",
                    )

    def test_every_menubutton_has_bare_target_and_flat_submenu(self):
        for file_name, nodes in _BRANCH_FILES.items():
            ui = self.sb.get_ui(file_name)
            for w in ui.findChildren(MenuButton):
                target = w.target
                with self.subTest(file=file_name, node=target):
                    self.assertIn(target, nodes)
                    self.assertNotIn("#", target, "target must be a bare node name")
                    # Hover opens <target>#submenu — the flat file must be registered.
                    self.assertTrue(
                        self.sb.is_registered_ui(f"{target}#submenu"),
                        f"{target}#submenu (hover destination) not registered",
                    )

    def test_release_resolves_to_native_menu_and_is_visible(self):
        """Release resolution: the bare target resolves (via the handler) to its native-menu proxy
        — NOT the ``#submenu`` overlay — and the button is not auto-hidden. A bare ``"blender"``
        UI must NOT be registered (else a target-``blender`` scheme would resolve there)."""
        self.assertFalse(self.sb.is_registered_ui("blender"))
        for file_name, nodes in _BRANCH_FILES.items():
            ui = self.sb.get_ui(file_name)
            for w in ui.findChildren(MenuButton):
                target = w.target
                with self.subTest(file=file_name, node=target):
                    self.assertEqual(self.sb.menu_button_target_name(w), target)
                    menu = self.nav._resolve_button_menu(w)
                    self.assertIsNotNone(menu, f"{target} did not resolve to a native proxy")
                    self.assertEqual(
                        getattr(menu, BlenderUiHandler._NATIVE_MENU_ATTR, None), target,
                        f"{target} resolved to the wrong proxy",
                    )
                    # A native menu is a standalone target, never a stacked (marking-menu) submenu.
                    self.assertFalse(menu.has_tags(["startmenu", "submenu"]))
                    self.assertTrue(w.isVisibleTo(ui), f"{file_name}.{target} auto-hidden")

    def test_leaf_files_hold_one_self_referencing_menubutton(self):
        for leaf in _LEAF_NODES:
            with self.subTest(leaf=leaf):
                ui = self.sb.get_ui(f"{leaf}#submenu")
                self.assertIsNotNone(ui, f"{leaf}#submenu failed to load")
                buttons = ui.findChildren(QtWidgets.QAbstractButton)
                self.assertEqual(len(buttons), 1, f"{leaf}#submenu must hold exactly one button")
                w = buttons[0]
                self.assertIsInstance(w, MenuButton, f"{leaf}#submenu button must be a MenuButton")
                self.assertEqual(w.target, leaf, f"{leaf}#submenu must self-reference target {leaf}")

    def test_node_set_equals_blender_native_menus(self):
        """The union of every target across every file equals ``BlenderNativeMenus.names()`` — no
        node without a native-menu mapping, no mapping entry without a node."""
        targets = set()
        for file_name in list(_BRANCH_FILES) + [f"{n}#submenu" for n in _LEAF_NODES]:
            ui = self.sb.get_ui(file_name)
            targets |= {w.target for w in ui.findChildren(MenuButton)}
        self.assertEqual(targets, BlenderNativeMenus.names())


class _Nav:
    """Borrows the marking menu's real release-resolution methods to drive them offscreen."""

    _cached_ui = MarkingMenu._cached_ui
    _resolve_button_menu = MarkingMenu._resolve_button_menu

    def __init__(self, sb):
        self.sb = sb
        self._submenu_cache = {}


if __name__ == "__main__":
    unittest.main()
