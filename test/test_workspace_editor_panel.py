#!/usr/bin/python
# coding=utf-8
"""The Workspaces panel's editor part (``slots/tools/_workspaces/editor.py``),
the former Workspace Editor; which host builds it is ``test_workspaces_panel.py``.

It reaches its host only through ``self.tk`` (``EnvUtils``: the current
workspace, the template rules, building a project); the workspace model is
pythontk's. So a fake toolkit stands in for ``btk`` and records what the part
asks of it: plain unittest, no DCC. Then the panel loads for real through
Blender's handler (Qt, no bpy) over ``btk`` and runs its write-through loop on a
scratch project (what blendertk's handler suite drove before the panel moved).
Blender's part (its group ``requires="blender"``): Maya's own Project Window is
Maya's, so there is no Maya-run case.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE
from tentacle.slots._slots import Slots
from tentacle.slots.tools import HOSTS
from tentacle.slots.tools._workspaces.editor import WorkspaceEditorPart
from tentacle.slots.tools.workspaces import WorkspacesSlots

MONO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(tentacle.__file__))))


def _panel(tk=None):
    """The editor part of a ``WorkspacesSlots`` built as Blender builds it (the
    map's group hidden) over a mock ui and *tk* (a fake by default), handed over
    before the panel is built, as ``Slots.tk`` is."""
    sb = mock.MagicMock()
    sb.tk = tk if tk is not None else mock.MagicMock()
    hidden = sb.loaded_ui.workspaces.grp_map
    sb.apply_visibility_policy.side_effect = lambda group: group is hidden
    return WorkspacesSlots(sb).editor, sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestWorkspaceEditorPanel(_PanelCase):
    def test_the_panel_serves_both_hosts_and_the_editor_is_blenders(self):
        """The Workspaces tool registers everywhere; Maya's own Project Window is
        Maya's editor, so the part is Blender's (the map's host is Maya)."""
        self.assertNotIn("workspaces", HOSTS)
        editor, _sb = _panel()
        self.assertIsInstance(editor, WorkspaceEditorPart)

    def test_a_typed_nice_name_resolves_to_its_rule_key(self):
        """A row added in Nice Names view has no stored key, so its typed text is
        the key candidate; without the reverse lookup the label went into
        workspace.mel verbatim (``workspace -fr "Render Data" ...``)."""
        key = WorkspaceEditorPart._key_for_label
        self.assertEqual(key("Render Data"), "renderData")
        self.assertEqual(key("  source images "), "sourceImages")  # case-insensitive
        self.assertEqual(key("myCustomRule"), "myCustomRule")  # a custom rule
        self.assertEqual(key("scene"), "scene")  # a raw key
        self.assertEqual(key("   "), "")

    def test_a_rebuilt_panel_replaces_the_dead_instances_handler(self):
        """The table and the root field outlive a Slots instance, so the handler a
        dead instance bound must be replaced, not joined: a stale one carries a
        stale removal baseline and would delete rules on the next edit."""

        class _Signal:
            def __init__(self):
                self.handlers = []

            def connect(self, handler):
                self.handlers.append(handler)

            def disconnect(self, handler):
                if handler not in self.handlers:
                    raise TypeError("not connected")
                self.handlers.remove(handler)

        widget = mock.Mock(spec=["itemChanged"])
        widget.itemChanged = _Signal()

        def first():
            pass

        def second():
            pass

        rewire = WorkspaceEditorPart._rewire
        rewire(widget, "itemChanged", first)
        self.assertEqual(widget.itemChanged.handlers, [first])
        rewire(widget, "itemChanged", second)  # the rebuilt instance
        self.assertEqual(widget.itemChanged.handlers, [second])
        rewire(widget, "itemChanged", second)  # the same instance, re-shown
        self.assertEqual(widget.itemChanged.handlers, [second])

    def test_the_root_field_opens_on_the_current_workspace(self):
        slots, sb = _panel()
        sb.tk.EnvUtils.current_workspace.return_value = mock.MagicMock(root="/proj")
        sb.loaded_ui.workspaces.settings.value.return_value = "/last"
        field = mock.MagicMock(is_initialized=True)
        field.text.return_value = ""
        slots.txt002_init(field)
        field.setText.assert_called_once_with("/proj")

    def test_the_root_field_falls_back_to_the_last_root(self):
        slots, sb = _panel()
        sb.tk.EnvUtils.current_workspace.return_value = None
        sb.loaded_ui.workspaces.settings.value.return_value = "/last"
        field = mock.MagicMock(is_initialized=True)
        field.text.return_value = ""
        slots.txt002_init(field)
        field.setText.assert_called_once_with("/last")

    def test_the_templates_combo_reads_the_shared_store(self):
        """The store both hosts read (``ptk.WorkspaceTemplates``), not a host's."""
        slots, sb = _panel()
        header = mock.MagicMock()
        store = mock.MagicMock(user_dir="/templates")
        with mock.patch.object(ptk.WorkspaceTemplates, "store", return_value=store):
            slots.header_init(header)
        sb.PresetManager.assert_called_once_with(
            preset_dir="/templates",
            value_provider=slots._gather,
            value_applier=slots._apply_template,
        )
        combo = next(
            c for c in header.menu.add.call_args_list
            if c.kwargs.get("setObjectName") == "cmb_template"
        )
        self.assertIs(combo.args[0], sb.ComboBox)
        sb.PresetManager.return_value.wire_combo.assert_called_once_with(
            header.menu.add.return_value, placeholder="Templates…"
        )
        names = [c.kwargs.get("setObjectName") for c in header.menu.add.call_args_list]
        for name in ("btn_create", "btn_add_rule", "chk_raw_names", "btn_reset", "btn_clear"):
            self.assertIn(name, names)

    def test_create_project_builds_through_the_host_and_makes_it_current(self):
        root = tempfile.mkdtemp(prefix="ws_editor_")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        slots, sb = _panel()
        ui = sb.loaded_ui.workspaces
        ui.txt002.text.return_value = root
        ui.tbl000 = None  # no table to reload: the build is the point
        slots.create_project()
        sb.tk.EnvUtils.create_workspace.assert_called_once_with(root)
        sb.tk.EnvUtils.set_current_workspace.assert_called_once_with(root)
        ui.footer.setStatusText.assert_called_with(f"Created {os.path.basename(root)}")

    def test_create_project_needs_a_root(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.workspaces
        ui.txt002.text.return_value = "  "
        slots.create_project()
        sb.tk.EnvUtils.create_workspace.assert_not_called()
        ui.footer.setStatusText.assert_called_with("Set a project root first.")


def _qt_widgets():
    try:
        from qtpy import QtWidgets

        return QtWidgets
    except Exception:  # noqa: BLE001 -- Qt absent
        return None


@unittest.skipIf(MAYA_AVAILABLE, "real Qt widgets and real Maya crash in one process")
@unittest.skipIf(_qt_widgets() is None, "Qt not available")
class TestWorkspaceEditorPanelLoads(unittest.TestCase):
    """The panel loaded through a real (offscreen) Qt / Switchboard /
    ``BlenderUiHandler`` stack over ``btk``, the way ``tcl_blender`` stands it
    up: one root field, a RULE / LOCATION table with per-row reset and remove
    icons, and rule edits that write through to ``workspace.mel`` at once. The
    template store is sandboxed (``TestSandbox``)."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        blendertk_repo = os.path.join(MONO, "blendertk")
        if os.path.isdir(blendertk_repo) and blendertk_repo not in sys.path:
            sys.path.insert(0, blendertk_repo)
        try:
            import blendertk
            from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler
        except Exception as error:  # noqa: BLE001 -- the Blender side absent
            raise unittest.SkipTest(f"blendertk unavailable: {error}") from error
        from uitk import Switchboard
        from uitk.testing import TestSandbox

        from tentacle.tcl import Tcl

        TestSandbox.activate()  # the panel's settings and templates stay off the live stores
        QtWidgets = _qt_widgets()
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.QtWidgets = QtWidgets
        cls.btk = blendertk
        handler = BlenderUiHandler(switchboard=Switchboard())
        cls.sb = handler.sb
        Tcl.register_shared(cls.sb)
        cls.ui = handler.get("workspaces")
        for _ in range(3):
            cls.app.processEvents()
        cls.slots = cls.sb.get_slots_instance(cls.ui)
        cls.editor = cls.slots.editor
        # Offscreen loading may skip the *_init entry points: drive them. The two
        # field inits re-run safely (they re-fire on every show); the header's once.
        if cls.editor._preset_mgr is None:
            cls.slots.header_init(cls.ui.header)
        cls.slots.txt002_init(cls.ui.txt002)
        cls.slots.tbl000_init(cls.ui.tbl000)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tcl_ws_editor_")
        self.project = os.path.join(self.tmp, "rt_proj")
        self.marker = os.path.join(self.project, "workspace.mel")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(self.btk.EnvUtils.set_current_workspace, None)
        self.addCleanup(self._set_root, "")
        self._set_root(self.project)

    def _set_root(self, path):
        """Point the panel at *path* and reload, with no debounce left pending."""
        field = self.ui.txt002
        blocked = field.blockSignals(True)
        try:
            field.setText(path)
        finally:
            field.blockSignals(blocked)
        self.editor._load()

    def _rules(self):
        return ptk.Workspace.parse_workspace_mel(self.marker) if os.path.isfile(self.marker) else {}

    def _row(self, key):
        table = self.ui.tbl000
        return next(r for r in range(table.rowCount()) if self.editor._key_at(r) == key)

    def test_binds_tentacles_slots_over_btk(self):
        self.assertIsInstance(self.slots, WorkspacesSlots)
        self.assertIs(self.slots.tk, self.btk)
        self.assertIsInstance(self.editor, WorkspaceEditorPart)
        self.assertIsNotNone(self.slots.map)  # the map serves Blender too

    def test_the_header_holds_the_editing_verbs_and_the_templates(self):
        menu = self.ui.header.menu
        self.assertTrue(hasattr(menu, "btn_add_rule"))
        for retired in ("btn_set_current", "btn_remove_rule", "btn_save_template"):
            self.assertFalse(hasattr(menu, retired), retired)
        self.assertIsNotNone(self.editor._preset_mgr)
        self.assertIsNotNone(getattr(menu, "cmb_template", None))
        buttons = set(getattr(self.ui.header, "buttons", {}))
        self.assertIn("hide", buttons)
        self.assertNotIn("pin", buttons)

    def test_a_fresh_path_shows_the_template_and_writes_nothing(self):
        self.assertFalse(os.path.exists(self.marker))
        self.assertEqual(self.ui.tbl000.rowCount(), len(self.btk.EnvUtils.workspace_template_rules()))
        self.assertEqual(self.ui.tbl000.actions.get(0, 2), "reset")
        self.assertEqual(self.ui.tbl000.actions.get(0, 3), "remove")
        header = self.ui.tbl000.horizontalHeader()
        mode = self.QtWidgets.QHeaderView
        self.assertEqual(header.sectionResizeMode(1), mode.Stretch)
        self.assertEqual(header.sectionResizeMode(2), mode.Fixed)
        self.assertEqual(header.sectionResizeMode(3), mode.Fixed)

    def test_the_first_edit_builds_the_project_and_makes_it_current(self):
        self.ui.tbl000.item(self._row("scene"), 1).setText("shots")  # itemChanged: write
        self.assertEqual(self._rules().get("scene"), "shots")
        self.assertTrue(os.path.isdir(os.path.join(self.project, "shots")))
        current = self.btk.EnvUtils.current_workspace()
        self.assertIsNotNone(current)
        self.assertEqual(
            os.path.normcase(os.path.normpath(current.root)),
            os.path.normcase(os.path.normpath(self.project)),
        )

    def test_row_reset_and_remove_write_through(self):
        defaults = self.btk.EnvUtils.workspace_template_rules()
        self.ui.tbl000.item(self._row("scene"), 1).setText("shots")
        self.editor.reset_row(self._row("scene"))
        self.assertEqual(self._rules().get("scene"), defaults["scene"])
        self.editor.remove_row(self._row("images"))
        self.assertNotIn("images", self._rules())

    def test_clear_and_reset_settings_write_through(self):
        self.ui.tbl000.item(self._row("scene"), 1).setText("shots")
        self.editor.clear_rules()
        self.assertTrue(os.path.isfile(self.marker))  # the marker survives
        self.assertEqual(self._rules(), {})
        self.editor.reset_rules()
        self.assertEqual(self._rules(), self.btk.EnvUtils.workspace_template_rules())

    def test_a_combo_saved_template_round_trips_through_the_host(self):
        """The combo (PresetManager) wraps the rules with a ``_meta`` block; the
        host's template reader strips it."""
        self.editor._preset_mgr.save("suite_tpl")
        self.addCleanup(self.btk.EnvUtils.delete_workspace_template, "suite_tpl")
        self.assertEqual(
            self.btk.EnvUtils.workspace_template_rules("suite_tpl"), self.editor._gather()
        )


if __name__ == "__main__":
    unittest.main()
