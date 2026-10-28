#!/usr/bin/python
# coding=utf-8
"""The Hierarchy Sync panel's one Slots class (and its controller, tree
renderer and path matcher), shared by both hosts.

It reaches its host only through ``self.tk`` -- the host library's
``HierarchySyncSession`` -- so a fake session stands in for ``mtk`` / ``btk``
here and records what the panel asks of it: plain unittest, no DCC. The panel
cases run over a mock ui; the controller, renderer and matcher cases build
real (offscreen) Qt trees. The hosts differ only in what the session answers:
how a path is cleaned (Maya drops namespaces, Blender keeps the path) and what
a tree item's node is (Maya's DAG path string, Blender's object), so a case is
written in the vocabulary it is about. The ``.ui`` is read as XML. In Maya, the
panel drives the real ``mtk`` on real nodes. The session's own behavior is the
libraries': each ``test_hierarchy_sync.py``.
"""

import os
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pythontk as ptk
from qtpy import QtCore, QtWidgets

import tentacle
from _host import MAYA_AVAILABLE, maya_module, qt_widgets_available
from tentacle.slots._slots import Slots
from tentacle.slots.tools._hierarchy_sync.controller import HierarchySyncController
from tentacle.slots.tools._hierarchy_sync.tree_matcher import (
    PLACEHOLDERS,
    TreePathMatcher,
)
from tentacle.slots.tools._hierarchy_sync.tree_renderer import (
    ORIG_TOOLTIP_ROLE,
    HierarchyTreeRenderer,
)
from tentacle.slots.tools.hierarchy_sync import HierarchySyncSlots

UI_PATH = os.path.join(
    os.path.dirname(tentacle.__file__), "ui", "tools", "hierarchy_sync.ui"
)
ROLE = QtCore.Qt.UserRole

if qt_widgets_available():  # items, fonts and trees need the application
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _fake_tk():
    """A toolkit double whose ``HierarchySyncSession`` answers in Maya's
    vocabulary: a node is its DAG path; a path is cleaned of namespaces."""
    tk = mock.MagicMock()
    session = tk.HierarchySyncSession.return_value
    session.diff_result = None
    session.fuzzy_matching = True
    session.SCENE_FILE_TYPES = ("*.ma", "*.mb", "*.fbx")
    session.loggers.return_value = []
    session.scene_path.return_value = ""
    session.workspace.return_value = "/project"
    session.reference_formats.return_value = [".ma", ".mb", ".fbx"]
    session.clean_path.side_effect = ptk.HierarchyPath.strip_namespaces
    session.node_path.side_effect = lambda n: n if isinstance(n, str) else ""
    session.node_name.side_effect = lambda n: str(n).split("|")[-1].split(":")[-1]
    session.node_alive.side_effect = lambda n: (
        isinstance(n, str) and bool(n) and n not in PLACEHOLDERS
    )
    session.is_loaded.return_value = False
    session.current_scene_nodes.return_value = []
    session.hierarchy_structure.return_value = ({}, [])
    session.load_reference.return_value = []
    tk.NodeIcons.get_icon.return_value = None
    return tk


def _panel(tk=None):
    """A Slots instance over a mock switchboard whose toolkit is *tk* (handed
    over before the panel is built, as ``Slots.tk`` is) or a fake."""
    sb = mock.MagicMock()
    sb.tk = tk if tk is not None else _fake_tk()
    slots = HierarchySyncSlots(sb)
    return slots, sb, sb.loaded_ui.hierarchy_sync


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        # The class logger is shared and the panel redirects it into its log
        # pane: a fake keeps the run's records (and handlers) off it. The
        # controller and the renderer adopt the same fake.
        self.logger = mock.MagicMock()
        patcher = mock.patch.object(HierarchySyncSlots, "logger", self.logger)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _said(self, level):
        return [str(c.args[0]) for c in getattr(self.logger, level).call_args_list]


def _item(text, data=None, parent=None):
    item = (
        QtWidgets.QTreeWidgetItem(parent, [text])
        if parent
        else (QtWidgets.QTreeWidgetItem([text]))
    )
    if data is not None:
        item.setData(0, ROLE, data)
    return item


class _Tree(QtWidgets.QTreeWidget):
    """A ``TreeWidget`` stand-in: what the renderer calls on a uitk tree."""

    def __init__(self):
        super().__init__()
        self.setColumnCount(1)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.selection_style = "border"

    def create_item(self, text, data=None, parent=None):
        item = QtWidgets.QTreeWidgetItem(
            parent or self, text if isinstance(text, list) else [text]
        )
        if data is not None:
            item.setData(0, ROLE, data)
        return item


class _Settings:
    def __init__(self):
        self.store = {}

    def value(self, key, default=None):
        return self.store.get(key, default)

    def setValue(self, key, value):
        self.store[key] = value


def _fill(tree, hierarchy, parent=None):
    """Add ``{"GRP": {"child": {}}}`` to *tree* (no node payloads)."""
    for name, children in hierarchy.items():
        item = QtWidgets.QTreeWidgetItem(parent or tree, [name])
        _fill(tree, children, item)


# ---------------------------------------------------------------------- the .ui


class TestHierarchySyncUi(unittest.TestCase):
    def test_the_ui_is_the_libraries_panel(self):
        """mayatk's and blendertk's twins were identical; the saved names hold."""
        root = ET.parse(UI_PATH).getroot()
        widgets = {w.get("name"): w for w in root.iter("widget")}
        for name in (
            "tree000",
            "tree001",
            "tb001",
            "tb002",
            "tb003",
            "cmb_diff_options",
            "cmb_pull_options",
            "txt003",
            "footer",
            "header",
        ):
            self.assertIn(name, widgets)
        labels = {
            name: widgets[name].find("./property[@name='text']/string").text
            for name in ("tb001", "tb002", "tb003")
        }
        self.assertEqual(labels, {"tb001": "Diff", "tb002": "Pull", "tb003": "Fix"})

    def test_no_runtime_row_is_declared_by_the_ui(self):
        names = {w.get("name") for w in ET.parse(UI_PATH).getroot().iter("widget")}
        self.assertEqual(set(HierarchySyncSlots.RUNTIME_WIDGETS) & names, set())


# ---------------------------------------------------------------------- the panel


class TestHierarchySyncPanelSetup(_PanelCase):
    def test_the_host_session_is_built_and_its_loggers_reach_the_log(self):
        tk = _fake_tk()
        engine_logger = mock.MagicMock()
        tk.HierarchySyncSession.return_value.loggers.return_value = [engine_logger]
        slots, sb, ui = _panel(tk)
        tk.HierarchySyncSession.assert_called_once_with()
        self.assertIs(slots.session, tk.HierarchySyncSession.return_value)
        for logger in (self.logger, engine_logger):
            logger.hide_logger_name.assert_called_once_with(True)
            logger.set_text_handler.assert_called_once_with(
                sb.registered_widgets.TextEditLogHandler
            )
            logger.setup_logging_redirect.assert_called_once_with(ui.txt003)
        ui.txt003.anchorClicked.connect.assert_called_once_with(
            slots._on_log_link_clicked
        )

    def test_scene_changes_and_hiding_are_followed(self):
        tk = _fake_tk()
        slots, sb, ui = _panel(tk)
        jobs = tk.ScriptJobManager.instance.return_value
        events = [c.args[0] for c in jobs.subscribe.call_args_list]
        self.assertEqual(events, ["SceneOpened", "NewSceneOpened"])
        jobs.connect_cleanup.assert_called_once_with(ui, owner=slots)
        ui.on_hide.connect.assert_called_once_with(slots.controller.on_window_hidden)

    def test_the_log_links_go_to_the_host(self):
        tk = _fake_tk()
        slots, sb, ui = _panel(tk)
        slots._on_log_link_clicked("action://select?node=GRP")
        tk.UiUtils.dispatch_log_link.assert_called_once_with(
            "action://select?node=GRP", self.logger
        )

    def test_a_scene_change_drops_the_analysis_and_the_ignored_paths(self):
        tk = _fake_tk()
        slots, sb, ui = _panel(tk)
        slots.controller._ignored_cur_paths.add("GRP")
        ui.isVisible.return_value = False
        slots._on_scene_changed()
        tk.HierarchySyncSession.return_value.clear_analysis.assert_called_once_with()
        self.assertEqual(slots.controller._ignored_cur_paths, set())


class TestHierarchySyncPanelRows(_PanelCase):
    def test_the_header_menu_and_help(self):
        slots, sb, ui = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        added = {
            c.kwargs.get("setObjectName"): c for c in header.menu.add.call_args_list
        }
        self.assertEqual(list(added), ["chk002", "cmb001", "chk_hide_ignored"])
        self.assertTrue(added["chk002"].kwargs["setChecked"])  # dry run by default
        self.assertEqual(added["cmb001"].kwargs["setCurrentIndex"], 1)  # INFO
        self.assertEqual(
            list(added["cmb001"].kwargs["add"]),
            [
                "Log Level: DEBUG",
                "Log Level: INFO",
                "Log Level: WARNING",
                "Log Level: ERROR",
            ],
        )
        help_kwargs = sb.tooltip.fmt.call_args.kwargs
        steps = " ".join(help_kwargs["steps"])
        self.assertIn(".ma / .mb / .fbx", steps)  # the host's reference formats
        for label in ("Diff", "Pull", "Fix"):
            self.assertIn(f"<b>{label}</b>", steps)
        text = " ".join(
            [help_kwargs["body"], steps, *help_kwargs["notes"]]
            + [row for _, rows in help_kwargs["sections"] for row in rows]
        )
        for word in ("Maya", "Blender", "transform", ".blend"):
            self.assertNotIn(word, text)

    @staticmethod
    def _distinct_rows(sb):
        """Each ``ComboBox()`` / ``CheckBox()`` a new widget, as uitk's are."""
        for name in ("ComboBox", "CheckBox"):
            getattr(sb.registered_widgets, name).side_effect = lambda *a, **k: (
                mock.MagicMock()
            )

    def test_the_diff_options_keep_their_names_and_order(self):
        slots, sb, ui = _panel()
        self._distinct_rows(sb)
        widget = mock.MagicMock()
        slots.cmb_diff_options_init(widget)
        rows = widget.add.call_args.args[0]
        names = [w.setObjectName.call_args.args[0] for w, _ in rows]
        self.assertEqual(
            names,
            [
                "cmb_selection_mode",
                "chk_expand_diff",
                "chk_force_reanalysis",
                "chk_fuzzy_matching",
                "chk_filter_meshes",
                "chk_filter_cameras",
                "chk_filter_lights",
                "chk_ignore_quarantine",
            ],
        )
        self.assertNotIn("cmb_diff_mode", names)  # dead in both hosts: dropped
        selection = rows[0][0].add.call_args.args[0]
        self.assertEqual(
            list(selection.values()), ["all", "root_only", "leaves_only", "none"]
        )
        defaults = {
            w.setObjectName.call_args.args[0]: w.setChecked.call_args.args[0]
            for w, _ in rows[1:]
        }
        self.assertEqual(
            defaults,
            {
                "chk_expand_diff": True,
                "chk_force_reanalysis": False,
                "chk_fuzzy_matching": True,
                "chk_filter_meshes": False,
                "chk_filter_cameras": False,
                "chk_filter_lights": False,
                "chk_ignore_quarantine": True,
            },
        )
        self.assertTrue(widget.add_defaults_button)

    def test_the_pull_options_keep_their_names_and_order(self):
        slots, sb, ui = _panel()
        self._distinct_rows(sb)
        widget = mock.MagicMock()
        slots.cmb_pull_options_init(widget)
        rows = widget.add.call_args.args[0]
        mode, children = rows[0][0], rows[1][0]
        mode.setObjectName.assert_called_once_with("cmb_pull_mode")
        self.assertEqual(
            list(mode.add.call_args.args[0].values()),
            ["Add to Scene", "Merge Hierarchies"],
        )
        children.setObjectName.assert_called_once_with("chk_pull_children")
        children.setChecked.assert_called_once_with(True)

    def test_the_fix_option_box(self):
        slots, sb, ui = _panel()
        widget = mock.MagicMock()
        slots.tb003_init(widget)
        names = [
            c.kwargs["setObjectName"] for c in widget.option_box.menu.add.call_args_list
        ]
        self.assertEqual(
            names,
            [
                "chk_fix_stubs",
                "chk_fix_quarantine",
                "txt_quarantine_name",
                "chk_skip_animated",
                "chk_fix_reparented",
                "chk_fix_fuzzy_renames",
            ],
        )


def _diff_panel(values=None, tk=None):
    """A panel whose Diff / Pull / Fix rows read *values*, and whose renderer
    is a mock (these cases are about what the panel asks)."""
    slots, sb, ui = _panel(tk)
    defaults = {
        "chk002": True,
        "cmb_selection_mode": "all",
        "chk_expand_diff": True,
        "chk_force_reanalysis": False,
        "chk_fuzzy_matching": True,
        "chk_filter_meshes": False,
        "chk_filter_cameras": True,
        "chk_filter_lights": False,
        "chk_ignore_quarantine": False,
        "cmb_pull_mode": "Add to Scene",
        "chk_pull_children": True,
    }
    for name, value in {**defaults, **(values or {})}.items():
        widget = getattr(ui, name)
        widget.isChecked.return_value = value
        widget.currentData.return_value = value
    menu = ui.tb003.option_box.menu
    for name in (
        "chk_fix_stubs",
        "chk_fix_quarantine",
        "chk_skip_animated",
        "chk_fix_reparented",
        "chk_fix_fuzzy_renames",
    ):
        getattr(menu, name).isChecked.return_value = True
    menu.txt_quarantine_name.text.return_value = ""
    slots.controller.tree = mock.MagicMock()
    slots.controller.tree.condense_to_roots.side_effect = (
        HierarchyTreeRenderer.condense_to_roots
    )
    slots.controller.tree.count_tree_items.return_value = 3
    # After an analysis the reference is the session's (``is_loaded``).
    slots.session.is_loaded.return_value = True
    return slots, sb, ui


class TestHierarchySyncDiff(_PanelCase):
    def setUp(self):
        super().setUp()
        handle, self.reference = tempfile.mkstemp(suffix=".ma")
        os.close(handle)
        self.addCleanup(os.remove, self.reference)

    def test_without_a_reference_nothing_is_analyzed(self):
        slots, sb, ui = _diff_panel()
        slots.tb001()
        slots.session.analyze.assert_not_called()
        self.assertIn("Please specify a reference scene path.", self._said("error"))

    def test_diff_analyzes_with_the_options_and_shows_the_result(self):
        slots, sb, ui = _diff_panel({"chk_force_reanalysis": True})
        session = slots.session
        slots.controller._reference_path = self.reference
        session.analyze.return_value = True
        session.diff_result = {
            "missing": ["GRP|a", "GRP|b"],
            "extra": ["X"],
            "reparented": [],
            "fuzzy_matches": [{"current_name": "GRP1", "target_name": "GRP"}],
        }
        slots.tb001()
        session.clear_analysis.assert_called_once_with()  # force re-analysis
        session.analyze.assert_called_once_with(
            self.reference,
            dry_run=True,
            fuzzy_matching=True,
            filter_meshes=False,
            filter_cameras=True,
            filter_lights=False,
        )
        renderer = slots.controller.tree
        renderer.apply_difference_formatting.assert_called_once_with(
            ui.tree001, ui.tree000
        )
        renderer.apply_diff_options.assert_called_once_with(
            ui.tree001,
            ui.tree000,
            True,
            True,
            select_root_only=False,
            select_leaves_only=False,
        )
        ui.footer.setText.assert_called_with("Diff: 2 missing, 1 extra, 1 renamed.")

    def test_diff_counts_leave_the_ignored_paths_out(self):
        slots, sb, ui = _diff_panel(
            {"cmb_selection_mode": "none", "chk_expand_diff": False}
        )
        session = slots.session
        slots.controller._reference_path = self.reference
        session.analyze.return_value = True
        session.diff_result = {
            "missing": ["GRP|a"],
            "extra": [],
            "reparented": [],
            "fuzzy_matches": [],
        }
        slots.controller._ignored_ref_paths.add("GRP")
        slots.tb001()
        slots.controller.tree.apply_diff_options.assert_not_called()
        ui.footer.setText.assert_called_with("Diff: hierarchies match.")

    def test_a_failed_analysis_stops_there(self):
        slots, sb, ui = _diff_panel()
        slots.controller._reference_path = self.reference
        slots.session.analyze.return_value = False
        slots.tb001()
        slots.controller.tree.apply_difference_formatting.assert_not_called()


class TestHierarchySyncPull(_PanelCase):
    def setUp(self):
        super().setUp()
        handle, self.reference = tempfile.mkstemp(suffix=".fbx")
        os.close(handle)
        self.addCleanup(os.remove, self.reference)

    def test_pull_hands_the_selected_nodes_to_the_host(self):
        slots, sb, ui = _diff_panel({"cmb_pull_mode": "Merge Hierarchies"})
        slots.controller._reference_path = self.reference
        targets = ["|ns:GRP", "|ns:GRP|ns:child", "|ns:OTHER"]
        slots.controller.tree.selected_item_keys.return_value = targets
        slots.session.pull.return_value = True
        slots.controller.refresh_trees = mock.MagicMock()
        slots.tb002()
        slots.controller.tree.selected_item_keys.assert_called_once_with(ui.tree000)
        slots.session.pull.assert_called_once_with(
            targets,
            self.reference,
            fuzzy_matching=True,
            dry_run=True,
            pull_children=True,
            pull_mode="Merge Hierarchies",
        )
        slots.controller.refresh_trees.assert_called_once_with(restore_selection=False)
        # Two roots (the child rides its parent), dry run.
        ui.footer.setText.assert_called_with(
            "Dry run: Pulled 2 hierarchies (Merge Hierarchies)"
        )

    def test_nothing_selected_pulls_nothing(self):
        slots, sb, ui = _diff_panel()
        slots.controller._reference_path = self.reference
        slots.controller.tree.selected_item_keys.return_value = []
        slots.tb002()
        slots.session.pull.assert_not_called()

    def test_a_failed_pull_refreshes_nothing(self):
        slots, sb, ui = _diff_panel({"chk002": False, "chk_pull_children": False})
        slots.controller._reference_path = self.reference
        slots.controller.tree.selected_item_keys.return_value = ["|A"]
        slots.session.pull.return_value = False
        slots.controller.refresh_trees = mock.MagicMock()
        slots.tb002()
        slots.controller.refresh_trees.assert_not_called()


class TestHierarchySyncFix(_PanelCase):
    def test_fix_repairs_the_effective_diff_with_the_options(self):
        slots, sb, ui = _diff_panel({"chk002": False})
        session = slots.session
        session.diff_result = {
            "missing": ["GRP|a", "SKIP|b"],
            "extra": [],
            "reparented": [],
            "fuzzy_matches": [],
        }
        slots.controller._ignored_ref_paths.add("SKIP")
        menu = ui.tb003.option_box.menu
        menu.chk_fix_quarantine.isChecked.return_value = False
        menu.txt_quarantine_name.text.return_value = " _HOLD "
        session.repair.return_value = True
        slots.controller.refresh_trees = mock.MagicMock()
        slots.tb003()
        args, kwargs = session.repair.call_args
        self.assertEqual(args[0]["missing"], ["GRP|a"])  # ignored left out
        self.assertEqual(
            kwargs,
            dict(
                create_stubs=True,
                quarantine_extras=False,
                quarantine_group="_HOLD",
                skip_animated=True,
                fix_reparented=True,
                fix_fuzzy_renames=True,
                dry_run=False,
            ),
        )
        slots.controller.refresh_trees.assert_called_once_with(restore_selection=False)
        ui.footer.setText.assert_called_with("Fix: repairs applied")

    def test_fix_needs_a_diff(self):
        slots, sb, ui = _diff_panel()
        slots.tb003()
        slots.session.repair.assert_not_called()

    def test_a_dry_fix_says_so(self):
        slots, sb, ui = _diff_panel()
        slots.session.diff_result = {"missing": ["A"]}
        slots.session.repair.return_value = True
        slots.controller.refresh_trees = mock.MagicMock()
        slots.tb003()
        slots.controller.refresh_trees.assert_not_called()
        ui.footer.setText.assert_called_with("Fix: DRY-RUN complete")
        self.assertEqual(
            slots.session.repair.call_args.kwargs["quarantine_group"], "_QUARANTINE"
        )


class TestHierarchySyncDialogs(_PanelCase):
    def test_the_reference_browser_offers_every_host_format_at_once(self):
        """One glob list (never a pre-formatted multi-entry Qt filter, which
        once hid every format but the first)."""
        slots, sb, ui = _panel()
        sb.file_dialog.return_value = []
        slots.b003()
        kwargs = sb.file_dialog.call_args.kwargs
        self.assertEqual(kwargs["file_types"], ["*.ma", "*.mb", "*.fbx"])
        self.assertEqual(kwargs["start_dir"], "/project")
        self.assertTrue(kwargs["filter_description"])

    def test_a_picked_reference_is_set_and_remembered(self):
        slots, sb, ui = _panel()
        sb.file_dialog.return_value = ["/refs/a.ma"]
        with (
            mock.patch.object(
                type(slots.controller), "reference_path", new_callable=mock.PropertyMock
            ) as reference,
            mock.patch.object(slots.controller, "save_recent_reference_scene") as save,
        ):
            slots.b003()
        reference.assert_called_once_with("/refs/a.ma")
        save.assert_called_once_with("/refs/a.ma")

    def test_the_scene_browser_opens_through_the_host(self):
        slots, sb, ui = _panel()
        sb.file_dialog.return_value = ["/scenes/b.ma"]
        slots._open_scene_dialog()
        self.assertEqual(
            sb.file_dialog.call_args.kwargs["file_types"], ["*.ma", "*.mb", "*.fbx"]
        )
        slots.session.open_scene.assert_called_once_with("/scenes/b.ma")

    def test_a_scene_that_fails_to_open_says_why(self):
        slots, sb, ui = _panel()
        slots.session.open_scene.side_effect = RuntimeError("cannot open")
        slots._open_scene("/scenes/broken.ma")
        sb.message_box.assert_called_once_with("cannot open")


@unittest.skipUnless(qt_widgets_available(), "builds Qt items")
class TestHierarchySyncSceneEdits(_PanelCase):
    """The current-scene tree's edits: the panel reads each node off its item
    and the host's session edits the scene."""

    def test_select_objects_takes_the_items_nodes(self):
        slots, sb, ui = _panel()
        ui.tree001.selectedItems.return_value = [
            _item("A", "|A"),
            _item("Open Scene", "open_scene_placeholder"),
        ]
        slots.b006()
        slots.session.select_nodes.assert_called_once_with(["|A"])

    def test_delete_takes_the_live_nodes_and_refreshes(self):
        slots, sb, ui = _panel()
        ui.tree001.selectedItems.return_value = [
            _item("A", "|A"),
            _item("Open Scene", "open_scene_placeholder"),
        ]
        slots.session.delete_nodes.return_value = ["|A"]
        slots.controller.refresh_trees = mock.MagicMock()
        slots.b018()
        slots.session.delete_nodes.assert_called_once_with(["|A"])
        slots.controller.refresh_trees.assert_called_once_with()
        self.assertIn("Deleted 1 object(s) (selected: A)", self._said("info"))

    def test_delete_with_no_node_selected_warns(self):
        slots, sb, ui = _panel()
        ui.tree001.selectedItems.return_value = [
            _item("Open Scene", "open_scene_placeholder")
        ]
        slots.controller.refresh_trees = mock.MagicMock()
        slots.b018()
        slots.session.delete_nodes.assert_not_called()
        slots.controller.refresh_trees.assert_not_called()
        self.assertTrue(self._said("warning"))

    def test_a_failed_delete_refreshes_nothing(self):
        slots, sb, ui = _panel()
        ui.tree001.selectedItems.return_value = [_item("A", "|A")]
        slots.session.delete_nodes.side_effect = RuntimeError("locked")
        slots.controller.refresh_trees = mock.MagicMock()
        slots.b018()
        slots.controller.refresh_trees.assert_not_called()
        self.assertIn("Delete failed: locked", self._said("error"))

    def test_a_drop_reparents_through_the_host_then_rebuilds_once(self):
        slots, sb, ui = _panel()
        slots.session.reparent_nodes.return_value = 2
        slots.controller.refresh_trees = mock.MagicMock()
        parent = _item("P", "|P")
        slots._on_tree001_drop_reparent(
            [
                (_item("A", "|A"), parent),
                (_item("B", "|B"), None),
                (_item("C", "|C"), _item("Open Scene", "open_scene_placeholder")),
            ]
        )
        slots.session.reparent_nodes.assert_called_once_with(
            [("|A", "|P"), ("|B", None)]
        )
        slots.controller.refresh_trees.assert_called_once_with()
        self.assertTrue(self._said("warning"))  # C's target is no node

    def test_a_drop_nothing_moves_on_rebuilds_nothing(self):
        slots, sb, ui = _panel()
        slots.session.reparent_nodes.return_value = 0
        slots.controller.refresh_trees = mock.MagicMock()
        slots._on_tree001_drop_reparent([(_item("A", "|A"), _item("P", "|P"))])
        slots.controller.refresh_trees.assert_not_called()

    def test_an_edited_name_renames_the_node_and_its_path_follows(self):
        """A renamed DAG path re-points the item and its descendants' paths."""
        slots, sb, ui = _panel()
        slots.session.rename_nodes.return_value = ["|NEW"]
        parent = _item("NEW", "|OLD")
        child = _item("child", "|OLD|child", parent)
        slots._on_current_tree_item_renamed(parent, 0)
        slots.session.rename_nodes.assert_called_once_with([("|OLD", "NEW")])
        self.assertEqual(parent.data(0, ROLE), "|NEW")
        self.assertEqual(parent._raw_name, "NEW")
        self.assertEqual(child.data(0, ROLE), "|NEW|child")

    def test_a_refused_name_is_put_back(self):
        slots, sb, ui = _panel()
        slots.session.rename_nodes.return_value = [None]
        item = _item("bad name", "|OLD")
        slots._on_current_tree_item_renamed(item, 0)
        self.assertEqual(item.text(0), "OLD")

    def test_an_unchanged_name_renames_nothing(self):
        slots, sb, ui = _panel()
        slots._on_current_tree_item_renamed(_item("SAME", "|ns:SAME"), 0)
        slots.session.rename_nodes.assert_not_called()

    def test_an_object_node_follows_its_rename_by_itself(self):
        """Blender: the item holds the object, which the rename keeps."""
        slots, sb, ui = _panel()
        obj = types.SimpleNamespace(name="Cube.001")
        session = slots.session
        session.node_alive.side_effect = lambda n: n is obj
        session.node_name.side_effect = lambda n: n.name
        session.rename_nodes.side_effect = lambda pairs: [
            setattr(obj, "name", pairs[0][1]) or obj
        ]
        item = _item("Cube", obj)
        slots._on_current_tree_item_renamed(item, 0)
        self.assertIs(item.data(0, ROLE), obj)
        self.assertEqual(obj.name, "Cube")

    def test_rename_from_reference_pairs_by_selection_order(self):
        slots, sb, ui = _panel()
        cur = [_item("a", "|a"), _item("b", "|b")]
        ref = [_item("A"), _item("B"), _item("C")]
        ui.tree001.selectedItems.return_value = cur
        ui.tree000.selectedItems.return_value = ref
        slots.session.rename_nodes.return_value = ["|A", None]
        slots.b017()
        slots.session.rename_nodes.assert_called_once_with([("|a", "A"), ("|b", "B")])
        self.assertEqual(cur[0].text(0), "A")
        self.assertEqual(cur[1].text(0), "b")
        self.assertIn(
            "Renamed 1 object(s) from reference names.", self._said("success")
        )


@unittest.skipUnless(qt_widgets_available(), "builds real widgets")
class TestHierarchySyncFuzzyRename(_PanelCase):
    def test_rename_from_reference_applies_the_last_diffs_fuzzy_matches(self):
        slots, sb, ui = _panel()
        ui.tree000 = _Tree()  # nothing selected: the fuzzy matches rename
        tree = _Tree()
        root = tree.create_item(["GRP1"], "|GRP1")
        tree.create_item(["arm2"], "|GRP1|arm2", root)
        ui.tree001 = tree
        slots.session.diff_result = {
            "fuzzy_matches": [
                {"current_name": "GRP1", "target_name": "GRP"},
                {"current_name": "GRP1|arm2", "target_name": "GRP|arm"},
            ]
        }
        slots.session.rename_nodes.return_value = ["|GRP", "|GRP|arm"]
        slots.b017()
        slots.session.rename_nodes.assert_called_once_with(
            [("|GRP1", "GRP"), ("|GRP1|arm2", "arm")]
        )


# ------------------------------------------------------------- controller / renderer


def _controller(tk=None):
    """A controller over real trees and a fake session."""
    tk = tk or _fake_tk()
    ui = types.SimpleNamespace(
        tree000=_Tree(), tree001=_Tree(), txt003=mock.MagicMock(), settings=_Settings()
    )
    slots = types.SimpleNamespace(
        sb=mock.MagicMock(), ui=ui, tk=tk, logger=mock.MagicMock()
    )
    return HierarchySyncController(slots)


@unittest.skipUnless(qt_widgets_available(), "builds real widgets")
class _QtCase(unittest.TestCase):
    def setUp(self):
        self.ctrl = _controller()
        self.session = self.ctrl.session
        self.tree000 = self.ctrl.ui.tree000
        self.tree001 = self.ctrl.ui.tree001


class TestIgnoredPaths(_QtCase):
    def test_a_path_is_ignored_with_its_descendants_but_not_its_namesakes(self):
        self.ctrl._ignored_ref_paths.add("GRP")
        self.assertTrue(self.ctrl.is_path_ignored(self.tree000, "GRP"))
        self.assertTrue(self.ctrl.is_path_ignored(self.tree000, "GRP|child|leaf"))
        self.assertFalse(self.ctrl.is_path_ignored(self.tree000, "GRP2"))
        self.assertFalse(self.ctrl.is_path_ignored(self.tree000, "GRP2|child"))

    def test_each_tree_has_its_own_ignored_paths(self):
        self.ctrl._ignored_ref_paths.add("shared")
        self.ctrl._ignored_cur_paths.add("other")
        self.assertTrue(self.ctrl.is_path_ignored(self.tree000, "shared"))
        self.assertFalse(self.ctrl.is_path_ignored(self.tree001, "shared"))
        self.assertTrue(self.ctrl.is_path_ignored(self.tree001, "other"))
        self.assertEqual(self.ctrl.ignored_set(object()), set())

    def test_the_effective_diff_leaves_the_ignored_paths_out(self):
        self.session.diff_result = {
            "missing": ["GRP|a", "GRP|b"],
            "extra": ["X|e1", "X|e2"],
            "reparented": [
                {"leaf": "n", "current_path": "A|n", "reference_path": "B|n"},
                {"leaf": "m", "current_path": "C|m", "reference_path": "D|m"},
            ],
            "fuzzy_matches": [{"current_name": "F1", "target_name": "F"}],
        }
        self.ctrl._ignored_ref_paths.update({"GRP|a", "D"})
        self.ctrl._ignored_cur_paths.update({"X|e1", "F1"})
        effective = self.ctrl.effective_diff()
        self.assertEqual(effective["missing"], ["GRP|b"])
        self.assertEqual(effective["extra"], ["X|e2"])
        self.assertEqual([r["leaf"] for r in effective["reparented"]], ["n"])
        self.assertEqual(effective["fuzzy_matches"], [])

    def test_no_analysis_has_no_differences(self):
        self.assertEqual(
            self.ctrl.effective_diff(),
            {"missing": [], "extra": [], "reparented": [], "fuzzy_matches": []},
        )

    def test_clearing_the_analysis_forgets_the_ignored_paths(self):
        self.ctrl._ignored_ref_paths.add("GRP")
        self.ctrl._ignored_cur_paths.add("OTHER")
        self.ctrl.clear_analysis()
        self.session.clear_analysis.assert_called_once_with()
        self.assertEqual(
            self.ctrl._ignored_ref_paths | self.ctrl._ignored_cur_paths, set()
        )

    def test_a_direct_ignore_strikes_through_and_an_inherited_one_is_italic(self):
        _fill(self.tree000, {"GRP": {"child": {"leaf": {}}, "other": {}}})
        root = self.tree000.topLevelItem(0)
        child, other = root.child(0), root.child(1)
        leaf = child.child(0)
        self.ctrl._ignored_ref_paths.add("GRP|child")
        self.ctrl.tree.apply_ignore_styling(self.tree000)
        self.assertTrue(child.font(0).strikeOut())
        self.assertFalse(child.font(0).italic())
        self.assertTrue(leaf.font(0).italic())
        self.assertFalse(leaf.font(0).strikeOut())
        self.assertFalse(other.font(0).strikeOut() or other.font(0).italic())
        # Unignored: the styling clears.
        self.ctrl._ignored_ref_paths.clear()
        self.ctrl.tree.apply_ignore_styling(self.tree000)
        self.assertFalse(child.font(0).strikeOut() or leaf.font(0).italic())

    def test_hide_ignored_hides_them_and_shows_them_again(self):
        _fill(self.tree000, {"Grp": {"Child": {}}, "Other": {}})
        grp = self.tree000.topLevelItem(0)
        child, other = grp.child(0), self.tree000.topLevelItem(1)
        self.ctrl._ignored_ref_paths.add("Grp")
        self.ctrl.hide_ignored = True
        self.ctrl.tree.apply_ignore_styling(self.tree000)
        self.assertTrue(grp.isHidden() and child.isHidden())
        self.assertFalse(other.isHidden())
        self.ctrl.hide_ignored = False
        self.ctrl.tree.apply_ignore_styling(self.tree000)
        self.assertFalse(grp.isHidden() or child.isHidden())

    def test_the_hide_toggle_restyles_both_trees(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        with mock.patch.object(HierarchySyncSlots, "logger", mock.MagicMock()):
            slots, sb, ui = _panel()
        slots.controller.tree = mock.MagicMock()
        slots._on_hide_ignored_toggled(True)
        self.assertTrue(slots.controller.hide_ignored)
        self.assertEqual(slots.controller.tree.apply_ignore_styling.call_count, 2)


class TestRenderer(_QtCase):
    def test_the_prompts(self):
        renderer = self.ctrl.tree
        renderer.show_reference_placeholder(self.tree000, "My Reference")
        self.assertEqual(self.tree000.headerItem().text(0), "My Reference")
        item = self.tree000.topLevelItem(0)
        self.assertEqual(item.text(0), "Browse for Reference Scene")
        self.assertTrue(item.font(0).underline())
        self.assertEqual(item.data(0, ROLE), "browse_placeholder")
        renderer.show_reference_error(self.tree000, "Ref", "Import failed")
        self.assertEqual(self.tree000.topLevelItemCount(), 1)
        self.assertEqual(self.tree000.topLevelItem(0).text(0), "Import failed")

    def test_an_empty_scene_shows_the_open_scene_prompt(self):
        self.session.scene_path.return_value = "/scenes/shot.ma"
        self.ctrl.tree.populate_current_scene_tree(self.tree001)
        self.assertEqual(self.tree001.headerItem().text(0), "shot")
        self.assertEqual(
            self.tree001.topLevelItem(0).data(0, ROLE), "open_scene_placeholder"
        )

    def test_the_reference_tree_shows_names_without_their_namespace(self):
        """Maya: a reference node's display name drops its namespace; its own
        name (``_raw_name``) and its node stay."""
        self.session.hierarchy_structure.return_value = (
            {
                "|ns:Root": {
                    "object": "|ns:Root",
                    "short_name": "ns:Root",
                    "display_name": "Root",
                    "node_name": "|ns:Root",
                    "type": "transform",
                    "parent": None,
                },
                "|ns:Root|ns:Child": {
                    "object": "|ns:Root|ns:Child",
                    "short_name": "ns:Child",
                    "display_name": "Child",
                    "node_name": "|ns:Root|ns:Child",
                    "type": "transform",
                    "parent": "|ns:Root",
                },
            },
            ["|ns:Root"],
        )
        self.tree000.create_item(["stale"])
        self.ctrl.tree.populate_reference_tree(self.tree000, ["n"], "Ref")
        self.assertEqual(self.tree000.topLevelItemCount(), 1)
        root = self.tree000.topLevelItem(0)
        self.assertEqual(root.text(0), "Root")
        self.assertEqual(root._raw_name, "ns:Root")
        self.assertEqual(root.child(0).data(0, ROLE), "|ns:Root|ns:Child")
        self.assertIn("Full Name: |ns:Root", root.toolTip(0))
        self.ctrl.tk.NodeIcons.get_icon.assert_any_call("|ns:Root|ns:Child")

    def test_the_diff_colours_and_tooltips_and_their_clearing(self):
        renderer = self.ctrl.tree
        item = self.tree001.create_item(["ref_item"])
        item.setToolTip(0, "Full Name: |root|child")
        renderer._apply_diff_color(item, "missing", "Missing — not in current scene")
        self.assertNotEqual(item.background(0).style(), QtCore.Qt.NoBrush)
        self.assertIn("Full Name", item.toolTip(0))
        self.assertEqual(item.toolTip(0).count("Missing"), 1)
        renderer.clear_tree_colors(self.tree001)
        self.assertEqual(item.background(0).style(), QtCore.Qt.NoBrush)
        self.assertEqual(item.toolTip(0), "Full Name: |root|child")
        self.assertIsNone(item.data(0, ORIG_TOOLTIP_ROLE))
        renderer._apply_diff_color(item, "missing", "Missing — not in current scene")
        self.assertEqual(item.toolTip(0).count("Missing"), 1)  # no stale stacking
        renderer._apply_diff_color(item, "nonexistent")  # unknown: a no-op

    def test_formatting_tints_the_selection_and_clearing_borders_it(self):
        self.session.diff_result = {
            "missing": [],
            "extra": ["X"],
            "reparented": [],
            "fuzzy_matches": [],
        }
        extra = self.tree001.create_item(["X"])
        self.ctrl.tree.apply_difference_formatting(self.tree001, self.tree000)
        self.assertEqual(self.tree001.selection_style, "tint")
        self.assertIn("Extra", extra.toolTip(0))
        self.ctrl.tree.clear_tree_colors(self.tree001)
        self.assertEqual(self.tree001.selection_style, "border")

    def test_clearing_strips_the_old_transparent_selection_block(self):
        self.tree001.setStyleSheet(
            "QTreeWidget { background: #333; }"
            "\n QTreeWidget {\n selection-background-color: transparent;\n }"
            "\n QTreeWidget::item:selected {\n background-color: transparent;\n }"
            "\n QTreeWidget::item:hover:!selected {\n background-color: none;\n }\n"
        )
        self.ctrl.tree.clear_tree_colors(self.tree001)
        style = self.tree001.styleSheet()
        self.assertNotIn("selection-background-color: transparent", style)
        self.assertIn("background: #333", style)

    def test_every_diff_category_has_a_colour(self):
        for key in ("missing", "extra", "fuzzy", "reparented"):
            fg, bg = HierarchyTreeRenderer.DIFF_COLORS.get(key)
            self.assertTrue(fg and bg, key)

    def test_the_diff_selects_missing_in_the_reference_and_extras_in_the_scene(self):
        _fill(self.tree000, {"GRP": {"a": {"deep": {}}, "b": {}, "skip": {}}})
        _fill(self.tree001, {"GRP": {"b": {}}, "EXTRA": {}})
        self.session.fuzzy_matching = False
        self.session.diff_result = {
            "missing": ["GRP|a", "GRP|skip"],
            "extra": ["EXTRA"],
            "reparented": [],
            "fuzzy_matches": [],
        }
        self.ctrl._ignored_ref_paths.add("GRP|skip")
        self.ctrl.tree.apply_diff_options(self.tree001, self.tree000, True, True)
        ref = {self.ctrl.tree.build_item_path(i) for i in self.tree000.selectedItems()}
        cur = {self.ctrl.tree.build_item_path(i) for i in self.tree001.selectedItems()}
        self.assertEqual(ref, {"GRP|a", "GRP|a|deep"})  # its subtree rides along
        self.assertEqual(cur, {"EXTRA"})

    def test_root_only_and_leaves_only(self):
        paths = ["A", "A|b", "A|b|c", "D"]
        self.assertEqual(HierarchyTreeRenderer.condense_to_roots(paths), ["A", "D"])
        self.assertEqual(
            sorted(HierarchyTreeRenderer.filter_to_leaves(paths)), ["A|b|c", "D"]
        )

    def test_a_refresh_keeps_the_selection_when_the_hierarchy_holds(self):
        nodes = {
            "|A": {
                "object": "|A",
                "short_name": "A",
                "display_name": "A",
                "node_name": "|A",
                "type": "transform",
                "parent": None,
            }
        }
        self.session.current_scene_nodes.return_value = ["|A"]
        self.session.hierarchy_structure.return_value = (nodes, ["|A"])
        self.ctrl.tree.populate_current_scene_tree(self.tree001)
        self.tree001.topLevelItem(0).setSelected(True)
        self.ctrl.refresh_trees()
        self.assertEqual([i.text(0) for i in self.tree001.selectedItems()], ["A"])
        self.ctrl.refresh_trees(restore_selection=False)
        self.assertEqual(self.tree001.selectedItems(), [])

    def test_a_new_reference_drops_the_analysis(self):
        self.session.is_loaded.return_value = False
        self.ctrl._ignored_ref_paths.add("GRP")
        self.ctrl.populate_reference_tree(self.tree000, "/nowhere/ref.ma")
        self.session.clear_analysis.assert_called_once_with()
        self.assertEqual(self.ctrl._ignored_ref_paths, set())
        self.assertEqual(self.tree000.topLevelItem(0).text(0), "File Not Found")

    def test_the_held_reference_keeps_the_analysis(self):
        handle, path = tempfile.mkstemp(suffix=".ma")
        os.close(handle)
        self.addCleanup(os.remove, path)
        self.session.is_loaded.return_value = True
        self.session.load_reference.return_value = ["|Root"]
        self.ctrl.populate_reference_tree(self.tree000, path)
        self.session.clear_analysis.assert_not_called()
        self.session.load_reference.assert_called_once_with(path)
        self.assertFalse(self.ctrl.importing_reference)


class TestRecentReferences(_QtCase):
    def test_a_bare_string_setting_reads_as_a_list(self):
        this_file = os.path.abspath(__file__)
        self.ctrl.ui.settings.store["recent_reference_scenes"] = this_file
        self.assertEqual(self.ctrl.get_recent_reference_scenes(), [this_file])

    def test_saving_keeps_a_list_with_the_newest_last(self):
        this_file = os.path.abspath(__file__)
        other = os.path.abspath(UI_PATH)
        self.ctrl.ui.settings.store["recent_reference_scenes"] = this_file
        self.ctrl.save_recent_reference_scene(other)
        stored = self.ctrl.ui.settings.store["recent_reference_scenes"]
        self.assertIsInstance(stored, list)
        self.assertEqual(stored[-1], str(Path(other).resolve()))
        self.assertIn(this_file, stored)

    def test_the_diff_report_lists_every_difference(self):
        path = HierarchySyncController.write_diff_report(
            ["GRP|a"],
            ["X"],
            [{"leaf": "n", "reference_path": "B|n", "current_path": "A|n"}],
            [{"current_name": "F1", "target_name": "F", "score": 0.8}],
        )
        self.addCleanup(os.remove, path)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for line in (
            "  - GRP|a",
            "  + X",
            "      reference: B|n",
            "F1  <->  F  (80% match)",
        ):
            self.assertIn(line, text)


class TestTreePathMatcher(_QtCase):
    def test_the_stored_dag_path_wins_over_the_leaf_name(self):
        item = _item("LEAF", "|GRP_A|LEAF")
        item._raw_name = "LEAF"
        self.assertEqual(TreePathMatcher().item_key(item), "|GRP_A|LEAF")

    def test_an_object_payload_is_named_by_the_hosts_node_path(self):
        """Blender: the item holds the object; its hierarchy path names it,
        whatever the display text says."""
        grp = types.SimpleNamespace(name="Grp", parent=None)
        child = types.SimpleNamespace(name="Child", parent=grp)

        def build_path(obj):
            parts = []
            while obj is not None:
                parts.insert(0, obj.name)
                obj = obj.parent
            return "|".join(parts)

        matcher = TreePathMatcher(node_path=build_path)
        parent = _item("DISPLAY_Grp")
        item = _item("DISPLAY_Child", child, parent)
        self.assertEqual(matcher.item_key(item), "Grp|Child")

    def test_a_prompt_row_is_no_node(self):
        for token in ("browse_placeholder", "open_scene_placeholder"):
            self.assertEqual(TreePathMatcher().item_key(_item("Browse", token)), "")

    def test_without_a_node_the_name_then_the_display_path(self):
        a = _item("A")
        b = _item("B", parent=a)
        self.assertEqual(TreePathMatcher().item_key(b), "A|B")
        b._raw_name = "ns:B"
        self.assertEqual(TreePathMatcher().item_key(b), "ns:B")

    def test_the_selected_keys_leave_ignored_and_prompt_rows_out(self):
        root = self.tree000.create_item(["Root"], "|ns:Root")
        child = self.tree000.create_item(["Child"], "|ns:Root|ns:Child", root)
        prompt = self.tree000.create_item(["Browse"], "browse_placeholder")
        for item in (root, child, prompt):
            item.setSelected(True)
        self.ctrl._ignored_ref_paths.add("Root|Child")
        self.assertEqual(self.ctrl.tree.selected_item_keys(self.tree000), ["|ns:Root"])

    def test_a_namespaced_path_finds_its_item_through_the_hosts_cleaning(self):
        root = self.tree000.create_item(["Root"], "|ns:Root")
        root._raw_name = "ns:Root"
        child = self.tree000.create_item(["Child"], "|ns:Root|ns:Child", root)
        child._raw_name = "ns:Child"
        maya = TreePathMatcher(clean_path=ptk.HierarchyPath.strip_namespaces)
        index = maya.build_tree_index(self.tree000)
        found, strategy = maya.find_path_matches(
            "Root|Child", *index, prefer_cleaned=True
        )
        self.assertEqual((found, strategy), ([child], "clean_full"))
        found, strategy = maya.find_path_matches("ns:Root|ns:Child", *index)
        self.assertEqual((found, strategy), ([child], "full"))

    def test_without_cleaning_a_colon_is_part_of_the_name(self):
        """Blender: ``mixamorig:Hips`` is a name, not a namespace."""
        root = self.tree000.create_item(["Armature"])
        self.tree000.create_item(["mixamorig:Hips"], None, root)
        blender = TreePathMatcher()
        index = blender.build_tree_index(self.tree000)
        found, _ = blender.find_path_matches("Armature|Hips", *index, strict=True)
        self.assertEqual(found, [])
        found, strategy = blender.find_path_matches(
            "Armature|mixamorig:Hips", *index, strict=True
        )
        self.assertEqual(strategy, "full")

    def test_the_leaf_name_is_the_last_resort_unless_strict(self):
        root = self.tree000.create_item(["A"])
        leaf = self.tree000.create_item(["leaf"], None, root)
        matcher = TreePathMatcher()
        index = matcher.build_tree_index(self.tree000)
        self.assertEqual(matcher.find_path_matches("Z|leaf", *index), ([leaf], "last"))
        self.assertEqual(
            matcher.find_path_matches("Z|leaf", *index, strict=True), ([], "none")
        )


# ---------------------------------------------------------------------- in Maya


@unittest.skipUnless(
    MAYA_AVAILABLE and qt_widgets_available(), "needs a GUI Maya (--in-maya)"
)
class TestHierarchySyncPanelInMaya(unittest.TestCase):
    """The panel's tree edits over the real ``mtk.HierarchySyncSession``."""

    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)
        # The panel redirects these loggers into its (mock) log pane.
        for logger in (
            HierarchySyncSlots.logger,
            *self.mtk.HierarchySyncSession.loggers(),
        ):
            for name in (
                "set_text_handler",
                "setup_logging_redirect",
                "hide_logger_name",
            ):
                patcher = mock.patch.object(logger, name)
                patcher.start()
                self.addCleanup(patcher.stop)
        self.slots, self.sb, self.ui = _panel(tk=self.mtk)
        # Its scene-change subscriptions go with the test.
        self.addCleanup(
            self.mtk.ScriptJobManager.instance().unsubscribe_all, self.slots
        )
        self.slots.controller.refresh_trees = mock.MagicMock()

    def _long(self, node):
        return self.cmds.ls(node, long=True)[0]

    def test_the_host_session_is_mayas(self):
        self.assertIsInstance(self.slots.session, self.mtk.HierarchySyncSession)

    def test_delete_takes_the_nodes_and_a_locked_stub(self):
        cmds = self.cmds
        stub = cmds.createNode("transform", name="HSP_STUB")
        self.mtk.HierarchySync._finalize_stub_node(stub)  # locks it
        plain = cmds.group(empty=True, name="HSP_PLAIN")
        self.ui.tree001.selectedItems.return_value = [
            _item("HSP_STUB", self._long(stub)),
            _item("HSP_PLAIN", self._long(plain)),
            _item("Open Scene", "open_scene_placeholder"),
        ]
        self.slots.b018()
        self.assertFalse(cmds.objExists("HSP_STUB"))
        self.assertFalse(cmds.objExists("HSP_PLAIN"))
        self.slots.controller.refresh_trees.assert_called_once_with()

    def test_a_drop_reparents_under_a_node_and_to_the_world(self):
        cmds = self.cmds
        parent = cmds.group(empty=True, name="HSP_PAR")
        a = cmds.group(empty=True, name="HSP_A")
        b = cmds.group(empty=True, name="HSP_B", parent=parent)
        parent_item = _item("HSP_PAR", self._long(parent))
        self.slots._on_tree001_drop_reparent(
            [
                (_item("HSP_A", self._long(a)), parent_item),
                (_item("HSP_B", self._long(b)), None),
            ]
        )
        self.assertEqual(cmds.listRelatives("HSP_A", parent=True), ["HSP_PAR"])
        self.assertIsNone(cmds.listRelatives("HSP_B", parent=True))
        self.slots.controller.refresh_trees.assert_called_once_with()

    def test_a_nested_drop_moves_parent_and_child(self):
        cmds = self.cmds
        a = cmds.group(empty=True, name="HSP_NA")
        b = cmds.group(empty=True, name="HSP_NB", parent=a)
        target = cmds.group(empty=True, name="HSP_TGT")
        target_item = _item("HSP_TGT", self._long(target))
        self.slots._on_tree001_drop_reparent(
            [
                (_item("HSP_NA", self._long(a)), target_item),
                (_item("HSP_NB", self._long(b)), target_item),
            ]
        )
        for name in ("HSP_NA", "HSP_NB"):
            self.assertEqual(cmds.listRelatives(name, parent=True), ["HSP_TGT"])

    def test_an_edited_name_renames_the_node(self):
        cmds = self.cmds
        node = cmds.group(empty=True, name="HSP_OLD")
        item = _item("HSP_NEW", self._long(node))
        self.slots._on_current_tree_item_renamed(item, 0)
        self.assertTrue(cmds.objExists("HSP_NEW"))
        self.assertFalse(cmds.objExists("HSP_OLD"))
        self.assertIn("HSP_NEW", item.data(0, ROLE))

    def test_rename_from_reference_renames_a_parent_and_its_child(self):
        cmds = self.cmds
        parent = cmds.group(empty=True, name="HSP_RP")
        child = cmds.group(empty=True, name="HSP_RC", parent=parent)
        self.ui.tree001.selectedItems.return_value = [
            _item("HSP_RP", self._long(parent)),
            _item("HSP_RC", self._long(child)),
        ]
        self.ui.tree000.selectedItems.return_value = [
            _item("HSP_RP2"),
            _item("HSP_RC2"),
        ]
        self.slots.b017()
        self.assertTrue(cmds.objExists("HSP_RP2"))
        self.assertTrue(cmds.objExists("HSP_RC2"))

    def test_select_objects_selects_the_nodes(self):
        cmds = self.cmds
        node = cmds.group(empty=True, name="HSP_SEL")
        cmds.select(clear=True)
        self.ui.tree001.selectedItems.return_value = [
            _item("HSP_SEL", self._long(node))
        ]
        self.slots.b006()
        self.assertEqual(cmds.ls(selection=True), ["HSP_SEL"])


if __name__ == "__main__":
    unittest.main()
