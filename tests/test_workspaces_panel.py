#!/usr/bin/python
# coding=utf-8
"""The Workspaces panel (``slots/tools/workspaces.py``): a facade over two parts,
the map (``_workspaces/map.py``, every host) and the editor
(``_workspaces/editor.py``, Blender's), each built only where the host serves
its group of the ``.ui`` (``requires``), and reached by its widgets' names.

Here: which part each host builds and shows, and the map's own behavior (the
editor's is ``test_workspace_editor_panel.py``). The map reaches its host only
through ``self.tk`` -- the host library's ``WorkspaceMap`` (the scan) and
``EnvUtils`` (switching project, publishing a template) -- so a fake toolkit
stands in for ``mtk`` and records what the panel asks of it: plain unittest, no
DCC. The tree is written through stand-in items (no Qt). In Maya the same part
scans real workspace folders through the real ``mtk``; then the panel loads for
real through an offscreen Switchboard in each host's context. The scan's own
behavior is mayatk's ``test_workspace.py``.
"""

import os
import shutil
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.workspaces import WorkspacesSlots

UI_FILE = Path(tentacle.__file__).resolve().parent / "ui" / "tools" / "workspaces.ui"


class _FakeItem:
    """Minimal QTreeWidgetItem stand-in (no Qt needed to pin the tree's shape)."""

    def __init__(self, parent=None):
        self.texts = {}
        self.values = {}
        self.children = []
        if parent is not None:
            parent.children.append(self)

    def setText(self, column, text):
        self.texts[column] = text

    def setData(self, column, role, value):
        self.values[column] = value

    def data(self, column, role):
        return self.values.get(column)


class _FakeTree(_FakeItem):
    def __init__(self):
        super().__init__()
        self.clear_calls = 0
        self.current = None

    def clear(self):
        self.clear_calls += 1
        self.children = []

    def expandAll(self):
        pass

    def currentItem(self):
        return self.current


TREE = {
    "projects": {
        "path": "/projects",
        "type": "directory",
        "workspaces": {
            "alpha": {
                "type": "workspace",
                "path": "/projects/alpha",
                "scene_count": 2,
                "size_mb": 1.5,
            },
            "beta": {
                "type": "workspace",
                "path": "/projects/beta",
                "scene_count": 0,
                "size_mb": 0,
            },
        },
    }
}


def _panel(tk=None, host="maya"):
    """A ``WorkspacesSlots`` over a mock ui (a stand-in tree) and *tk* (a fake
    whose scan answers :data:`TREE`), handed over before the panel is built, as
    ``Slots.tk`` is. *host* decides which group the visibility policy hides: the
    editor's in ``"maya"``, none in ``"blender"`` (or ``None``)."""
    sb = mock.MagicMock()
    if tk is None:
        tk = mock.MagicMock()
        engine = tk.WorkspaceMap.return_value
        engine.current_working_dir = "/projects"
        engine.current_workspace = "/projects/alpha"
        engine.recursive_search = True
        engine.get_workspace_tree_data.return_value = TREE
    sb.tk = tk
    sb.QtWidgets.QTreeWidgetItem = _FakeItem
    sb.QtCore.Qt.UserRole = 0
    ui = sb.loaded_ui.workspaces
    ui.tree000 = _FakeTree()
    hidden = {"maya": ui.grp_editor}.get(host)
    sb.apply_visibility_policy.side_effect = lambda group: group is hidden
    return WorkspacesSlots(sb), sb


def _rows(tree):
    """``(folder, workspace, scenes, size)`` per workspace row."""
    return [
        (folder.texts[0], row.texts[0], row.texts[1], row.texts[2])
        for folder in tree.children
        for row in folder.children
    ]


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.tmp = tempfile.mkdtemp(prefix="ws_map_panel_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Which part each host builds
# ---------------------------------------------------------------------------


class TestWorkspacesParts(_PanelCase):
    def test_the_ui_tags_each_part_with_the_host_it_serves(self):
        """Each part's widgets sit in its group, and the group names its host."""
        root = ET.parse(UI_FILE).getroot()
        groups = {
            w.get("name"): w
            for w in root.iter("widget")
            if w.get("name") in ("grp_map", "grp_editor")
        }

        def requires(group):
            prop = group.find("property[@name='requires']/string")
            return prop.text if prop is not None else None

        def names(group):
            return {w.get("name") for w in group.iter("widget")}

        self.assertIsNone(requires(groups["grp_map"]))  # every host
        self.assertEqual(requires(groups["grp_editor"]), "blender")
        self.assertLessEqual(
            {"txt000", "txt001", "tree000", "b000", "b001", "b002"},
            names(groups["grp_map"]),
        )
        self.assertLessEqual({"txt002", "tbl000"}, names(groups["grp_editor"]))

    def test_maya_builds_the_map_alone(self):
        slots, sb = _panel(host="maya")
        self.assertIsNotNone(slots.map)
        self.assertIsNone(slots.editor)
        self.assertEqual(slots.parts, [slots.map])
        sb.loaded_ui.workspaces.grp_editor.setVisible.assert_called_once_with(False)
        field, table = mock.MagicMock(), mock.MagicMock()
        slots.txt002_init(field)
        slots.tbl000_init(table)
        self.assertEqual(field.mock_calls, [])
        self.assertEqual(table.mock_calls, [])

    def test_blender_builds_both_parts_over_its_own_scan(self):
        slots, sb = _panel(host="blender")
        self.assertIsNotNone(slots.map)
        self.assertIsNotNone(slots.editor)
        self.assertEqual(slots.parts, [slots.map, slots.editor])
        sb.tk.WorkspaceMap.assert_called_once_with()

    def test_the_header_carries_the_served_parts_rows_and_one_help_card(self):
        """Maya keeps the map's chrome (no ``config_buttons``) and help; Blender
        gets both parts' rows under distinct titles, the editor's chrome
        (refresh / menu / collapse / hide) and one card with each part's steps
        as a section."""
        slots, sb = _panel(host="maya")
        header = mock.MagicMock()
        slots.header_init(header)
        header.config_buttons.assert_not_called()
        names = [c.kwargs.get("setObjectName") for c in header.menu.add.call_args_list]
        self.assertIn("new_project", names)
        self.assertNotIn("btn_create", names)
        self.assertEqual(sb.tooltip.fmt.call_args.kwargs["title"], "Workspace Map")
        header.set_help_text.assert_called_once_with(sb.tooltip.fmt.return_value)

        slots, sb = _panel(host="blender")
        header = mock.MagicMock()
        store = mock.MagicMock(user_dir="/templates")
        with mock.patch.object(ptk.WorkspaceTemplates, "store", return_value=store):
            slots.header_init(header)
        header.config_buttons.assert_called_once_with(
            "refresh", "menu", "collapse", "hide"
        )
        calls = header.menu.add.call_args_list
        names = [c.kwargs.get("setObjectName") for c in calls]
        self.assertIn("btn_create", names)
        self.assertIn("new_project", names)
        titles = [c.kwargs["setTitle"] for c in calls if "setTitle" in c.kwargs]
        self.assertEqual(len(titles), len(set(titles)), titles)
        card = sb.tooltip.fmt.call_args.kwargs
        self.assertEqual(card["title"], "Workspaces")
        self.assertEqual(
            [title for title, _ in card["sections"]][:2],
            ["Workspace Map", "Workspace Editor (Project Window)"],
        )

    def test_a_toolkit_without_the_scan_never_builds_the_map(self):
        """A switchboard that names no host shows every group (uitk's rule), so the
        part checks the toolkit too: one without a ``WorkspaceMap`` gets no map."""
        tk = types.SimpleNamespace(EnvUtils=mock.MagicMock())
        slots, sb = _panel(tk=tk, host=None)
        self.assertIsNone(slots.map)
        self.assertIsNotNone(slots.editor)
        sb.loaded_ui.workspaces.grp_map.setVisible.assert_called_once_with(False)


# ---------------------------------------------------------------------------
# The map part
# ---------------------------------------------------------------------------


class TestWorkspaceMap(_PanelCase):
    def test_opens_on_the_scan_root_and_scans_once_shown(self):
        slots, sb = _panel()
        sb.loaded_ui.workspaces.txt000.setText.assert_called_once_with("/projects")
        sb.defer_with_timer.assert_called_once()
        slots.map.engine.invalidate_workspace_data.assert_not_called()
        sb.defer_with_timer.call_args.args[0]()  # the deferred first scan
        slots.map.engine.invalidate_workspace_data.assert_called_once_with()

    def test_the_tree_has_a_row_per_folder_and_workspace(self):
        slots, sb = _panel()
        slots.map.update_tree()
        tree = sb.loaded_ui.workspaces.tree000
        self.assertEqual(
            _rows(tree),
            [("projects", "alpha", "2", "1.5 MB"), ("projects", "beta", "0", "0.0 MB")],
        )
        self.assertEqual(tree.children[0].values[0], TREE["projects"])

    def test_refilling_never_duplicates_rows(self):
        """Filtering refills on every keystroke: without the clear, one more copy
        of every row per character typed."""
        slots, sb = _panel()
        slots.map.update_tree()
        slots.map.update_tree()
        tree = sb.loaded_ui.workspaces.tree000
        self.assertEqual(len(_rows(tree)), 2)
        self.assertEqual(tree.clear_calls, 2)

    def test_the_filter_narrows_through_the_engine(self):
        slots, _sb = _panel()
        slots.map.filter_workspaces("alp")
        slots.map.engine.get_workspace_tree_data.assert_called_with("alp")

    def test_a_new_valid_root_rescans(self):
        slots, sb = _panel()
        sb.loaded_ui.workspaces.txt000.text.return_value = self.tmp
        slots.map.update_current_dir()
        self.assertEqual(
            slots.map.engine.current_working_dir, os.path.normpath(self.tmp)
        )
        sb.loaded_ui.workspaces.txt000.set_action_color.assert_called_with("reset")
        slots.map.engine.get_workspace_tree_data.assert_called_with(None)

    def test_an_invalid_root_clears_the_tree(self):
        slots, sb = _panel()
        slots.map.update_tree()
        missing = os.path.join(self.tmp, "missing")
        slots.map.update_current_dir(missing)
        self.assertEqual(sb.loaded_ui.workspaces.tree000.children, [])
        self.assertEqual(slots.map.engine.current_working_dir, "/projects")
        sb.loaded_ui.workspaces.txt000.set_action_color.assert_called_with("invalid")

    def test_the_buttons_browse_set_and_rescan(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.workspaces
        slots.b001()
        ui.txt000.setText.assert_called_with("/projects/alpha")
        slots.b002()
        slots.map.engine.invalidate_workspace_data.assert_called_once_with()
        slots.map._browse_option = mock.MagicMock()
        slots.b000()
        slots.map._browse_option.browse.assert_called_once_with()

    def test_the_menu_rows_dispatch_by_name_through_the_panel(self):
        """uitk dispatches a row by its objectName to the panel's slot (so
        repeat-last, shortcuts and the slot history see it): each row a part
        adds (the map's, the editor's) has a same-named panel slot that reaches
        the part, and no row is wired past that dispatch."""
        slots, _sb = _panel(host="blender")
        header, field, tree = (mock.MagicMock(is_initialized=False) for _ in range(3))
        store = mock.MagicMock(user_dir="/templates")
        with mock.patch.object(ptk.WorkspaceTemplates, "store", return_value=store):
            slots.header_init(header)
        slots.txt000_init(field)
        slots.tree000_init(tree)
        for widget in (header.menu, field.option_box.menu, tree.menu):
            returned = widget.add.return_value
            self.assertEqual(returned.clicked.connect.call_args_list, [])
            self.assertEqual(returned.toggled.connect.call_args_list, [])
        rows = {
            # row: (the part, its method, the args)
            "new_project": (slots.map, "new_project", ()),
            "mark_root": (slots.map, "mark_root", ()),
            "save_template": (slots.map, "save_template", ()),
            "set_to_workspace": (slots.map, "set_to_workspace", ()),
            "chk000": (slots.map, "chk000", (False,)),
            "btn_open_workspace": (slots.map, "btn_open_workspace", ()),
            "btn_explore_folder": (slots.map, "btn_explore_folder", ()),
            "btn_create": (slots.editor, "create_project", ()),
            "btn_add_rule": (slots.editor, "add_rule", ()),
            "chk_raw_names": (slots.editor, "_on_view_toggled", (True,)),
            "btn_reset": (slots.editor, "reset_rules", ()),
            "btn_clear": (slots.editor, "clear_rules", ()),
        }
        for name, (owner, method, args) in rows.items():
            with self.subTest(row=name), mock.patch.object(owner, method) as part:
                getattr(slots, name)(*args)
                part.assert_called_once_with(*args)

    def test_recursive_search_rescans_only_on_a_change(self):
        slots, _sb = _panel()
        slots.map.chk000(2)  # stateChanged's Qt.Checked: already on
        slots.map.chk000(True)
        slots.map.engine.invalidate_workspace_data.assert_not_called()
        slots.map.chk000(False)
        self.assertIs(slots.map.engine.recursive_search, False)
        self.assertEqual(slots.map.engine.invalidate_workspace_data.call_count, 1)

    def test_rechecking_recursive_search_turns_it_back_on(self):
        """``toggled`` sends a bool, which is an int: read as a check state,
        ``True == 2`` turned the search OFF, so it could never come back on."""
        slots, _sb = _panel()
        slots.map.chk000(False)
        slots.map.chk000(True)
        self.assertIs(slots.map.engine.recursive_search, True)
        self.assertEqual(slots.map.engine.invalidate_workspace_data.call_count, 2)

    def test_double_clicking_a_workspace_makes_it_the_project(self):
        slots, sb = _panel()
        tree = sb.loaded_ui.workspaces.tree000
        tree.current = _FakeItem()
        tree.current.setData(0, 0, {"type": "workspace", "path": self.tmp})
        sb.tk.EnvUtils.set_current_workspace.return_value = self.tmp
        slots.map.btn_open_workspace()
        sb.tk.EnvUtils.set_current_workspace.assert_called_once_with(self.tmp)
        self.assertIn(self.tmp, sb.message_box.call_args.args[0])

    def test_a_folder_row_opens_nothing(self):
        slots, sb = _panel()
        tree = sb.loaded_ui.workspaces.tree000
        tree.current = _FakeItem()
        tree.current.setData(0, 0, {"type": "directory", "path": self.tmp})
        slots.map.btn_open_workspace()
        sb.tk.EnvUtils.set_current_workspace.assert_not_called()

    def test_new_project_builds_from_the_active_template(self):
        slots, sb = _panel()
        sb.input_dialog.return_value = " shot_010 "
        slots.map.engine.create_project.return_value = mock.MagicMock(
            root="/projects/shot_010"
        )
        slots.map.new_project()
        slots.map.engine.create_project.assert_called_once_with("shot_010")
        self.assertIn("/projects/shot_010", sb.message_box.call_args.args[0])

    def test_an_empty_root_scans_nothing_and_reads_as_unset(self):
        """Blender with nothing saved or pinned has no session workspace: the
        root stays empty -- no retarget at the launch folder ('' normalizes to
        '.'), no scan, the tree cleared, and the field not coloured invalid."""
        slots, sb = _panel()
        ui = sb.loaded_ui.workspaces
        slots.map.engine.current_working_dir = ""
        ui.txt000.text.return_value = ""
        slots.map.update_current_dir()
        self.assertEqual(slots.map.engine.current_working_dir, "")
        slots.map.engine.get_workspace_tree_data.assert_not_called()
        self.assertGreaterEqual(ui.tree000.clear_calls, 1)
        ui.txt000.set_action_color.assert_called_with("reset")

    def test_mark_root_needs_a_root(self):
        """No root, nothing to mark: never the launch folder."""
        slots, sb = _panel()
        slots.map.engine.current_working_dir = ""
        slots.map.mark_root()
        slots.map.engine.mark_root_as_project.assert_not_called()
        self.assertIn("Set a valid root directory", sb.message_box.call_args.args[0])

    def test_marking_a_marked_root_says_so(self):
        with open(os.path.join(self.tmp, "workspace.mel"), "w", encoding="utf-8") as f:
            f.write('workspace -fr "scene" "scenes";\n')
        slots, sb = _panel()
        slots.map.engine.current_working_dir = self.tmp
        slots.map.mark_root()
        slots.map.engine.mark_root_as_project.assert_not_called()
        self.assertIn("already a project", sb.message_box.call_args.args[0])

    def test_save_template_publishes_through_the_host(self):
        slots, sb = _panel()
        sb.input_dialog.return_value = "studio"
        sb.tk.EnvUtils.save_workspace_template.return_value = "studio"
        slots.map.save_template()
        sb.tk.EnvUtils.save_workspace_template.assert_called_once_with("studio")
        sb.tk.EnvUtils.save_workspace_template.side_effect = ValueError("No file rules")
        slots.map.save_template()
        self.assertEqual(sb.message_box.call_args.args[0], "No file rules")


def _make_workspace(parent, name):
    """A marked workspace folder (``workspace.mel``) holding one scene."""
    root = os.path.join(parent, name)
    os.makedirs(os.path.join(root, "scenes"), exist_ok=True)
    with open(os.path.join(root, "workspace.mel"), "w", encoding="utf-8") as f:
        f.write('workspace -fr "scene" "scenes";\n')
    with open(os.path.join(root, "scenes", "scene1.ma"), "w", encoding="utf-8") as f:
        f.write("//Maya ASCII scene\n")
    return root


@unittest.skipUnless(MAYA_AVAILABLE, "needs a Maya runtime")
class TestWorkspaceMapInMaya(_PanelCase):
    """The map's tree over the real ``mtk.WorkspaceMap`` scan (the cases
    mayatk's ``TestWorkspaceMapTreePopulation`` held before the panel moved)."""

    def setUp(self):
        super().setUp()
        for name in ("alpha", "beta"):
            _make_workspace(self.tmp, name)
        self.slots, self.sb = _panel(tk=maya_module("mayatk"))
        self.map = self.slots.map
        self.map.engine.current_working_dir = self.tmp
        self.tree = self.sb.loaded_ui.workspaces.tree000

    def test_refilling_does_not_duplicate_rows(self):
        self.map.update_tree()
        first = len(_rows(self.tree))
        self.assertGreaterEqual(first, 2)
        self.map.update_tree()
        self.assertEqual(len(_rows(self.tree)), first)

    def test_the_filter_narrows_instead_of_appending(self):
        self.map.update_tree()
        self.map.update_tree(filter_text="alpha")
        self.assertEqual([row[1] for row in _rows(self.tree)], ["alpha"])


# ---------------------------------------------------------------------------
# The panel loaded for real in each host's context (offscreen Qt, no DCC)
# ---------------------------------------------------------------------------


def _qt_widgets():
    try:
        from qtpy import QtWidgets

        return QtWidgets
    except Exception:  # noqa: BLE001 -- Qt absent
        return None


class _FakeScan:
    """``mtk.WorkspaceMap``'s surface over an empty root."""

    def __init__(self, root):
        self.current_working_dir = root
        self.current_workspace = root
        self.recursive_search = True

    def get_workspace_tree_data(self, filter_text=None):
        return {}

    def invalidate_workspace_data(self):
        pass


@unittest.skipIf(MAYA_AVAILABLE, "real Qt widgets and real Maya crash in one process")
@unittest.skipIf(_qt_widgets() is None, "Qt not available")
class TestWorkspacesPanelLoads(unittest.TestCase):
    """The panel built through a real (offscreen) Switchboard in each host's
    context over a fake toolkit: uitk hides the editor's group in Maya (its
    ``requires``), and the panel builds only the parts the host serves."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from uitk.testing import TestSandbox

        TestSandbox.activate()  # the panel's settings and templates stay off the live stores
        QtWidgets = _qt_widgets()
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ws_panel_load_")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def _load(self, host):
        from uitk import Switchboard

        env = mock.MagicMock(name="EnvUtils")
        env.current_workspace.return_value = None
        env.workspace_template_rules.return_value = {"scene": "scenes"}
        tk = types.SimpleNamespace(
            __name__="mayatk" if host == "maya" else "blendertk", EnvUtils=env
        )
        tk.WorkspaceMap = lambda: _FakeScan(self.root)
        sb = Switchboard(
            ui_source=str(UI_FILE), slot_source=WorkspacesSlots, context_tags={host}
        )
        sb.tk = tk  # set before the panel is built
        ui = sb.get_ui("workspaces")
        slots = sb.get_slots_instance(ui)
        self.assertIsInstance(slots, WorkspacesSlots)
        return ui, slots

    def test_maya_shows_the_map_and_hides_the_editor(self):
        ui, slots = self._load("maya")
        self.assertEqual(getattr(ui.grp_editor, "hidden_by_policy", None), "requires")
        self.assertIsNone(getattr(ui.grp_map, "hidden_by_policy", None))
        self.assertTrue(ui.grp_editor.isHidden())
        self.assertFalse(ui.grp_map.isHidden())
        self.assertIsNotNone(slots.map)
        self.assertIsNone(slots.editor)

    def test_blender_shows_the_map_and_the_editor(self):
        ui, slots = self._load("blender")
        self.assertIsNone(getattr(ui.grp_map, "hidden_by_policy", None))
        self.assertIsNone(getattr(ui.grp_editor, "hidden_by_policy", None))
        self.assertFalse(ui.grp_map.isHidden())
        self.assertFalse(ui.grp_editor.isHidden())
        self.assertIsNotNone(slots.map)
        self.assertIsNotNone(slots.editor)


if __name__ == "__main__":
    unittest.main()
