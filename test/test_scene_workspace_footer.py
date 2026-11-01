#!/usr/bin/python
# coding=utf-8
"""Tests for the Scene panel's workspace *footer*.

The workspace *controls* (Set Dir / Auto Set / Open Root / recent history) live in
the main lower submenu's Workspace list (see ``slots/main.py`` and
``test_main_workspace.py``). What remains in the Scene panel is the *status footer*:
the current workspace's name routed to the MainWindow footer.

One wiring for both hosts (``SceneSlots._create_footer_controller``): subscribe the
host's ``ScriptJobManager.WORKSPACE_EVENTS`` (Maya's ``workspaceChanged``; Blender has
none, so its scene open / save) to the refresh, own the controller, refresh on each
event. The controller comes off the footer widget (``footer.status_controller``)
rather than an imported ``FooterStatusController``: slots reach uitk through the
switchboard's windows only.
"""

import ast
import unittest
from pathlib import Path
from unittest import mock

from tentacle.slots._slots import Slots
from tentacle.slots.scene import SceneSlots

SCENE_PY = Path(__file__).resolve().parent.parent / "tentacle" / "slots" / "scene.py"


def _slots(events, footer=True):
    """A ``SceneSlots`` over a toolkit whose workspace events are *events*."""
    migrated = Slots._legacy_repeat_last_migrated
    Slots._legacy_repeat_last_migrated = True
    try:
        sb = mock.MagicMock()
        sb.tk.ScriptJobManager.WORKSPACE_EVENTS = tuple(events)
        if not footer:
            sb.loaded_ui.scene.footer = None
        return SceneSlots(sb)
    finally:
        Slots._legacy_repeat_last_migrated = migrated


class TestFooterWiring(unittest.TestCase):
    """The host's workspace events refresh the footer -- one wiring, no host branch."""

    def test_each_workspace_event_is_subscribed_to_the_refresh(self):
        for events in (("workspaceChanged",), ("SceneOpened", "SceneSaved")):
            with self.subTest(events=events):
                slots = _slots(events)
                footer = slots.ui.footer
                mgr = slots.tk.ScriptJobManager.instance.return_value
                self.assertEqual(
                    mgr.subscribe.call_args_list,
                    [
                        mock.call(event, slots._on_workspace_changed, owner=footer)
                        for event in events
                    ],
                )
                mgr.connect_cleanup.assert_called_once_with(footer, owner=footer)

    def test_the_controller_comes_from_the_footer_widget(self):
        slots = _slots(("workspaceChanged",))
        footer = slots.ui.footer
        footer.status_controller.assert_called_once_with(
            resolver=slots._workspace_status,
            default_text="No workspace set",
            truncate_kwargs=SceneSlots.FOOTER_TRUNCATE,
        )
        self.assertIs(slots._footer_controller, footer.status_controller.return_value)

    def test_a_window_without_a_footer_subscribes_nothing(self):
        slots = _slots(("workspaceChanged",), footer=False)
        self.assertIsNone(slots._footer_controller)
        slots.tk.ScriptJobManager.instance.assert_not_called()

    def test_an_event_refreshes_the_controller(self):
        slots = _slots(("workspaceChanged",))
        slots._on_workspace_changed()
        slots._footer_controller.update.assert_called_once_with()
        slots._footer_controller = None
        slots._on_workspace_changed()  # before the controller exists: no error


class TestWorkspaceStatus(unittest.TestCase):
    """The footer's text: the workspace folder's name, "" with none."""

    def test_the_folder_name_of_the_workspace_root(self):
        slots = _slots(())
        slots.tk.EnvUtils.workspace_root.return_value = "P:/projects/hero_shot/"
        self.assertEqual(slots._workspace_status(), "hero_shot")
        slots.tk.EnvUtils.workspace_root.return_value = ""
        self.assertEqual(slots._workspace_status(), "")


class TestFooterSurface(unittest.TestCase):
    """AST guards on the composed module."""

    @classmethod
    def setUpClass(cls):
        cls.source = SCENE_PY.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.methods = {
            fn.name
            for node in ast.walk(cls.tree)
            if isinstance(node, ast.ClassDef) and node.name == "SceneSlots"
            for fn in node.body
            if isinstance(fn, ast.FunctionDef)
        }

    def test_the_controller_class_is_not_imported(self):
        imported = {
            alias.asname or alias.name
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("FooterStatusController", imported)

    def test_the_moved_workspace_controls_stay_gone(self):
        # list001 is deliberately NOT here: the objectName was recycled for the
        # submenu's Import list. The workspace move is pinned by its helper names.
        for gone in (
            "tb000_init",
            "tb000",
            "lbl004",
            "lbl005",
            "_open_recent_workspace",
            "_set_workspace_interactive",
            "_auto_set_workspace",
            "_set_workspace_from_path",
            "cmb000_init",
            "cmb000",
            "txt000",
        ):
            self.assertNotIn(gone, self.methods, f"{gone} belongs to slots/main.py")


if __name__ == "__main__":
    unittest.main()
