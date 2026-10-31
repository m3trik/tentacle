#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.scene, the one Scene Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it here and
records what each slot asks of it (plain unittest), and in Maya the same class drives
the real ``mtk`` (``run_tests.py --in-maya``). Pinned at this layer:

- the Import / Export lists: this panel's rows and the host's own commands
  (``EnvUtils.get_file_commands``) in one order, a row only one host serves tagged, the
  other DCC named off its bridge -- both directions of the scene hand-off and the
  shared formats (USD, glTF) under the same labels in either host;
- Recent Files / Autosave through ``EnvUtils.open_scene``;
- the Tools leaves: the launchers, the host-only rows and their reports;
- Get Scene Info over the host's analyzer (the flows Export Scene, Fix Non-Orthogonal
  Axes and the pull rows share are ``test_scene_mixin.py``'s).
The operations themselves are tested in mayatk and blendertk.
"""

import contextlib
import functools
import os
import unittest
from types import SimpleNamespace as NS
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # before any widget is built

from _host import (  # noqa: E402
    MAYA_AVAILABLE,
    maya_module,
    qt_widgets_available,
)
from tentacle.slots._slots import Slots  # noqa: E402
from tentacle.slots.scene import SceneSlots  # noqa: E402

#: The host commands each toolkit answers ``get_file_commands`` with, as mayatk /
#: blendertk list them (pinned there).
MAYA_COMMANDS = {
    "import": ["Import File", "Import Options", "FBX Import Presets", "OBJ Import Presets"],
    "export": [
        "Export Selection",
        "Export All",
        "Send to Unreal",
        "Send to Unity",
        "Export to Offline File",
        "Export Options",
        "FBX Export Presets",
        "OBJ Export Presets",
    ],
}
BLENDER_COMMANDS = {
    "import": ["Import OBJ", "Append from .blend", "Link from .blend"],
    "export": ["Export Selection", "Export FBX", "Export OBJ", "Export glTF"],
}


def _bridge(app, extensions):
    return NS(spec=NS(app=NS(name=app)), save_extensions=tuple(extensions))


def _toolkit(host="maya"):
    """A MagicMock toolkit answering like *host*'s: the other DCC's bridge, the host's
    own file commands, an unsaved scene in a workspace."""
    tk = mock.MagicMock()
    if host == "maya":
        bridge, commands, scene_exts = (
            _bridge("Blender", (".blend", ".json")),
            MAYA_COMMANDS,
            (".blend",),
        )
    else:
        bridge, commands, scene_exts = (
            _bridge("Maya", (".ma", ".mb")),
            BLENDER_COMMANDS,
            (".ma", ".mb"),
        )
    tk.EnvUtils.foreign_scene_bridge.return_value = bridge
    tk.EnvUtils.foreign_scene_import.return_value.SCENE_EXTENSIONS = scene_exts
    tk.EnvUtils.get_file_commands.side_effect = lambda direction: list(
        commands[direction]
    )
    tk.EnvUtils.saved_scene_path.return_value = ""
    tk.EnvUtils.workspace_root.return_value = "W:/proj"
    tk.CoreUtils.selected_objects.return_value = []
    return tk


def _make(sb):
    """A ``SceneSlots`` through its real ``__init__`` (no legacy-shortcut migration);
    *sb* needs ``loaded_ui.scene`` -- a window with no footer subscribes nothing."""
    migrated = Slots._legacy_repeat_last_migrated
    Slots._legacy_repeat_last_migrated = True
    try:
        return SceneSlots(sb)
    finally:
        Slots._legacy_repeat_last_migrated = migrated


class _SlotsCase(unittest.TestCase):
    HOST = "maya"

    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.sb.tk = _toolkit(self.HOST)
        self.sb.loaded_ui.scene.footer = None
        self.slots = SceneSlots(self.sb)
        self.tk = self.sb.tk

    def _message(self):
        (text, *_), _kwargs = self.sb.message_box.call_args
        return text


class _FakeList:
    """Stand-in for uitk's ExpandableList (the surface the list inits touch)."""

    def __init__(self, submenu=False):
        self.ui = NS(has_tags=lambda *tags: submenu)
        self.items = []
        self.preset = None
        self.fixed_item_height = None
        self.visible = None

    def apply_preset(self, name):
        self.preset = name

    def setVisible(self, state):
        self.visible = state

    def get_items(self):
        return list(self.items)

    def add(self, item, data=None, **kwargs):
        if isinstance(item, zip):
            return [self.add(text, data=value) for text, value in item]
        row = NS(text=item, data=data, sublist=_FakeList(), properties={}, kwargs=kwargs)
        row.setProperty = row.properties.__setitem__
        row.item_data = lambda r=row: r.data
        self.items.append(row)
        return row


def _labels(rows):
    return [label for label, _action, _requires in rows]


class TestListRows(_SlotsCase):
    """``_list_rows``: one table, each host's own commands, the other DCC named."""

    def test_maya_s_import_list(self):
        rows = self.slots._list_rows(SceneSlots._IMPORT_ROWS, "import")
        self.assertEqual(
            _labels(rows),
            [
                "Import File",
                "Import Options",
                "Import FBX",
                "Import Blender Scene",
                "Import glTF",
                "Import USD",
                "FBX Import Presets",
                "OBJ Import Presets",
            ],
        )
        # Blender's FBX row is hidden in Maya (its Import File imports FBX).
        self.assertEqual(
            [label for label, _, req in rows if req], ["Import FBX"]
        )

    def test_maya_s_export_list(self):
        rows = self.slots._list_rows(SceneSlots._EXPORT_ROWS, "export")
        self.assertEqual(
            _labels(rows),
            [
                "Export Selection",
                "Export .blend",
                "Export USD",
                "Export glTF",
                "Export All",
                "Send to Unreal",
                "Send to Unity",
                "Export to Offline File",
                "Export Options",
                "FBX Export Presets",
                "OBJ Export Presets",
            ],
        )

    def test_a_command_row_runs_the_host_command_and_a_method_row_its_method(self):
        rows = dict(
            (label, action)
            for label, action, _ in self.slots._list_rows(
                SceneSlots._IMPORT_ROWS, "import"
            )
        )
        rows["Import File"]()
        self.tk.EnvUtils.run_file_command.assert_called_once_with("Import File")
        self.assertEqual(rows["Import USD"], self.slots._import_usd)

    def test_a_host_command_the_table_does_not_name_follows_the_rows(self):
        self.tk.EnvUtils.get_file_commands.side_effect = lambda d: [
            "Import File",
            "Import From Cloud",
        ]
        rows = self.slots._list_rows(SceneSlots._IMPORT_ROWS, "import")
        self.assertEqual(_labels(rows)[-1], "Import From Cloud")
        self.assertNotIn("Import Options", _labels(rows))  # not offered: not listed

    def test_a_refused_command_reaches_the_user_as_text(self):
        self.tk.EnvUtils.run_file_command.side_effect = RuntimeError(
            "Could not load the <fbxmaya> plug-in"
        )
        self.slots._run_file_command("FBX Import Presets")
        self.assertIn("&lt;fbxmaya&gt;", self._message())
        self.tk.EnvUtils.run_file_command.side_effect = ValueError("needs a selection")
        self.slots._run_file_command("Export Selection")
        self.assertIn("needs a selection", self._message())


class TestSceneHandoffSymmetry(unittest.TestCase):
    """Each host's Scene panel BOTH reads and writes the other DCC's native format --
    and USD and glTF under the same labels on each side.

    The push direction (``save_as``) exists because the pull alone left the Import list
    able to reach a foreign scene while the Export list could not produce one. These
    rows are built at runtime, so the panel parity sweep (which diffs widgets) cannot
    see a missing one.
    """

    PAIRS = {
        "maya": ("Import Blender Scene", "Export .blend"),
        "blender": ("Import Maya Scene", "Export .ma"),
    }
    SHARED = (("Import USD", "Export USD"), ("Import glTF", "Export glTF"))

    def test_both_directions_and_the_shared_formats_in_each_host(self):
        for host, pair in self.PAIRS.items():
            with self.subTest(host=host):
                slots = _make(
                    NS(tk=_toolkit(host), loaded_ui=NS(scene=NS(), scene_submenu=NS()))
                )
                imports = slots._list_rows(SceneSlots._IMPORT_ROWS, "import")
                exports = slots._list_rows(SceneSlots._EXPORT_ROWS, "export")
                for import_label, export_label in (pair, *self.SHARED):
                    self.assertIn(import_label, _labels(imports))
                    self.assertIn(export_label, _labels(exports))
                # Every row runs something callable (a missing method raises here).
                self.assertTrue(all(callable(a) for _, a, _ in imports + exports))


class TestListInits(_SlotsCase):
    """list001 / list002 build their rows with the action as each item's data."""

    def test_import_rows_carry_their_action_and_one_host_rows_their_tag(self):
        widget = _FakeList(submenu=True)
        self.slots.list001_init(widget)
        self.assertEqual(widget.preset, "expand_overlay")
        rows = widget.items[0].sublist.items
        fbx = next(r for r in rows if r.text == "Import FBX")
        self.assertEqual(fbx.properties, {"requires": "blender"})
        self.sb.apply_visibility_policy.assert_any_call(fbx)
        usd = next(r for r in rows if r.text == "Import USD")
        self.assertEqual(usd.data, self.slots._import_usd)

    def test_the_export_tools_sit_nearest_the_trigger_in_both_layouts(self):
        added = []
        self.slots.add_slot_widget = lambda sublist, **kw: added.append(
            (len(sublist.items), kw["setObjectName"])
        )
        panel = _FakeList(submenu=False)
        self.slots.list002_init(panel)
        rows = panel.items[0].sublist.items
        # Panel: Export Scene first, the Scene Exporter, then the one-shots.
        self.assertEqual(added, [(0, "tb003")])
        self.assertEqual(rows[0].text, "Scene Exporter")
        self.assertEqual(rows[1].text, "Export Selection")

        added.clear()
        submenu = _FakeList(submenu=True)
        self.slots.list002_init(submenu)
        rows = submenu.items[0].sublist.items
        # Submenu (expands up): the one-shots reversed, the Scene Exporter, then
        # Export Scene LAST -- nearest the trigger.
        self.assertEqual(rows[0].text, "OBJ Export Presets")
        self.assertEqual(rows[-1].text, "Scene Exporter")
        self.assertEqual(added, [(len(rows), "tb003")])

    def test_dispatch_runs_the_item_s_action_and_skips_a_category(self):
        calls = []
        self.slots.list001(NS(item_data=lambda: lambda: calls.append("row")))
        self.slots.list002(NS(item_data=lambda: None))  # the category row
        self.assertEqual(calls, ["row"])

    def test_the_scene_exporter_row_opens_the_panel(self):
        self.slots._open_scene_exporter()
        self.sb.handlers.marking_menu.show.assert_called_once_with("scene_exporter")
        # The Export list is its only route: the header's b002 button left (a
        # re-added method would mean it crept back onto the header menu).
        self.assertFalse(hasattr(SceneSlots, "b002"))


class TestRecentFilesAndAutosave(_SlotsCase):
    """Recent Files / Autosave open through ``EnvUtils.open_scene``."""

    def test_recent_files_list_and_hide_when_empty(self):
        self.tk.EnvUtils.get_recent_files.return_value = ["P:/a.ma", "P:/b.ma"]
        widget = _FakeList()
        self.slots.list000_init(widget)
        self.tk.EnvUtils.get_recent_files.assert_called_once_with(slice(0, 11))
        self.assertEqual(
            [r.data for r in widget.items[0].sublist.items], ["P:/a.ma", "P:/b.ma"]
        )
        self.assertTrue(widget.visible)
        self.tk.EnvUtils.get_recent_files.return_value = []
        widget = _FakeList()
        self.slots.list000_init(widget)
        self.assertFalse(widget.visible)

    def test_a_file_row_opens_and_the_category_row_does_not(self):
        self.tk.EnvUtils.open_scene.return_value = True
        self.slots.list000(NS(item_data=lambda: None))
        self.tk.EnvUtils.open_scene.assert_not_called()
        self.slots.list000(NS(item_data=lambda: "P:/scenes/foo.ma"))
        self.tk.EnvUtils.open_scene.assert_called_once_with("P:/scenes/foo.ma")
        self.sb.message_box.assert_not_called()

    def test_a_scene_that_will_not_open_says_so(self):
        self.tk.EnvUtils.open_scene.return_value = False
        self.slots.list000(NS(item_data=lambda: "P:/scenes/foo.ma"))
        self.assertIn("Could not open", self._message())

    def test_autosaves_list_newest_first_and_open(self):
        self.tk.EnvUtils.get_recent_autosave.return_value = [
            ("P:/autosave/a.0001.ma", "10:00:00")
        ]
        widget = mock.MagicMock()
        self.slots.cmb002_init(widget)
        self.tk.EnvUtils.get_recent_autosave.assert_called_once_with(
            filter_time=24, timestamp_format="%H:%M:%S"
        )
        (items,), kwargs = widget.add.call_args
        self.assertEqual(list(items.values()), ["P:/autosave/a.0001.ma"])
        self.assertEqual(kwargs["header"], "Autosave:")
        self.tk.EnvUtils.open_scene.return_value = True
        self.slots.cmb002(0, NS(items=["P:/autosave/a.0001.ma"]))
        self.tk.EnvUtils.open_scene.assert_called_once_with("P:/autosave/a.0001.ma")


class TestToolsLaunchers(_SlotsCase):
    """The Tools leaves that open a tool panel or another app."""

    def _shown(self, *slots):
        for name in slots:
            getattr(self.slots, name)()
        return [c.args[0] for c in self.sb.handlers.marking_menu.show.call_args_list]

    def test_the_shared_tool_panels(self):
        self.assertEqual(
            self._shown("b001", "b004", "b005", "b003", "b015", "b016"),
            [
                "reference_manager",
                "hierarchy_sync",
                "naming",
                "audio_clips",
                "blendshape_animator",
                "unity_bridge",
            ],
        )

    def test_the_other_dcc_s_bridge_is_the_one_dcc_bridge(self):
        """One tool in both hosts: its engine, the host's bridge to the other app,
        names the target (``test_dcc_bridge_panel.py``)."""
        self.assertEqual(self._shown("b010"), ["dcc_bridge"])
        self.sb.tk = _toolkit("blender")
        self.sb.handlers.marking_menu.show.reset_mock()
        self.assertEqual(self._shown("b010"), ["dcc_bridge"])

    def test_the_mesh_converter_starts_beside_the_scene_and_reads_fbx_references(self):
        self.tk.EnvUtils.saved_scene_path.return_value = "P:/proj/scenes/a.ma"
        ui = self.sb.handlers.external_app.launch.return_value
        self.slots.b013()
        self.sb.handlers.external_app.launch.assert_called_once_with(
            "mesh_convert", show=False
        )
        self.assertEqual(ui.slots.source_dir, "P:/proj/scenes")
        provider = ui.slots.fbx_provider
        self.assertIsInstance(provider, functools.partial)
        provider()
        self.tk.ReferenceManager.selected_reference_paths.assert_called_once_with(
            (".fbx",)
        )
        self.sb.handlers.marking_menu.show.assert_called_once_with(ui)

    def test_scene_metadata_shows_the_data_nodes(self):
        self.slots.b017()
        args, kwargs = self.sb.data_view_dialog.call_args
        self.assertIs(args[0], self.tk.DataNodes.dump.return_value)
        self.tk.EnvUtils.scene_artifact_path.assert_called_once_with(
            "_scene_metadata.json"
        )


class TestToolsFixes(_SlotsCase):
    """The Fix leaves: one library call each, the result worded here."""

    def test_fix_color_spaces_lists_the_changes(self):
        self.tk.Diagnostics.fix_missing_color_spaces.return_value = {
            "changes": [{"node": "rock_N", "from": "sRGB", "to": "Raw <lin>"}]
        }
        self.slots.b011()
        self.tk.Diagnostics.fix_missing_color_spaces.assert_called_once_with(
            force_update=True
        )
        message = self._message()
        self.assertIn("updated <hl>1</hl> texture(s)", message)
        self.assertIn("rock_N: sRGB → Raw &lt;lin&gt;", message)
        self.tk.Diagnostics.fix_missing_color_spaces.return_value = {"changes": []}
        self.slots.b011()
        self.assertIn("nothing to change", self._message())

    def test_fix_color_spaces_caps_a_long_list(self):
        self.tk.Diagnostics.fix_missing_color_spaces.return_value = {
            "changes": [{"node": f"n{i}", "from": "a", "to": "b"} for i in range(25)]
        }
        self.slots.b011()
        self.assertIn("… and 5 more", self._message())

    def test_cleanup_unknown_says_what_it_removed(self):
        self.tk.Diagnostics.cleanup_scene.return_value = {
            "unknown": {"nodes": ["a", "b"], "plugins": ["p"]},
            "xgen_removed": 0,
        }
        self.slots.b006()
        self.assertIn("<hl>2</hl> unknown node(s), <hl>1</hl> plugin(s)", self._message())
        self.tk.Diagnostics.cleanup_scene.return_value = {
            "unknown": {"nodes": [], "plugins": []},
            "xgen_removed": 0,
        }
        self.slots.b006()
        self.assertIn("nothing to remove", self._message())

    def test_scene_cleanup_is_blenders_one_purge(self):
        """Scene Cleanup runs the purge Optimize runs (``purge_unused_data``,
        Blender's own), not a second hand-rolled one."""
        self.tk.CoreUtils.purge_unused_data.return_value = 3
        self.slots.b_cleanup()
        self.tk.CoreUtils.purge_unused_data.assert_called_once_with()
        self.assertIn("purged <hl>3</hl> unused data-block(s)", self._message())
        self.tk.CoreUtils.purge_unused_data.return_value = 0
        self.slots.b_cleanup()
        self.assertIn("nothing to purge", self._message())

    def test_mangled_names_repair_the_selection_or_the_scene(self):
        self.tk.Diagnostics.repair_mangled_names.return_value = {
            "renamed": ["a"],
            "shapes_conformed": 2,
        }
        self.slots.b018()
        self.tk.Diagnostics.repair_mangled_names.assert_called_once_with(objects=None)
        self.assertIn("<hl>1</hl> mangled name(s)", self._message())

    def test_command_ports_report_their_state(self):
        self.tk.MayaConnection.toggle_command_ports.return_value = (
            True,
            {":7001": "mel"},
        )
        self.slots.b012()
        self.assertIn("OPENED", self._message())


class TestRecoverToOriginal(_SlotsCase):
    """Save to Original Scene (Maya's): never initialized where the policy hid it."""

    def test_a_leaf_hidden_for_this_host_is_left_alone(self):
        widget = mock.MagicMock(hidden_by_policy="requires")
        self.slots.b014_init(widget)
        self.tk.EnvUtils.find_original_for_autosave.assert_not_called()
        widget.setEnabled.assert_not_called()

    def test_an_open_autosave_names_its_original(self):
        self.tk.EnvUtils.saved_scene_path.return_value = "P:/autosave/shot.0003.ma"
        self.tk.EnvUtils.matches_autosave_pattern.return_value = True
        self.tk.EnvUtils.find_original_for_autosave.return_value = "P:/scenes/shot.ma"
        widget = mock.MagicMock(hidden_by_policy=None, is_initialized=False)
        self.slots.b014_init(widget)
        widget.setEnabled.assert_called_once_with(True)
        self.assertTrue(widget.setText.call_args.args[0].startswith("Save to: "))
        self.tk.ScriptJobManager.instance.return_value.subscribe.assert_any_call(
            "SceneOpened", self.slots._on_scene_changed, owner=self.slots
        )

    def test_not_an_autosave_disables_it(self):
        self.tk.EnvUtils.saved_scene_path.return_value = "P:/scenes/shot.ma"
        self.tk.EnvUtils.matches_autosave_pattern.return_value = False
        widget = mock.MagicMock(hidden_by_policy=None, is_initialized=True)
        self.slots.b014_init(widget)
        widget.setEnabled.assert_called_once_with(False)
        widget.setText.assert_called_once_with("Save to Original Scene")

    def test_the_save_asks_then_saves(self):
        self.tk.EnvUtils.find_original_for_autosave.return_value = "P:/scenes/shot.ma"
        self.tk.EnvUtils.save_autosave_to_original.return_value = "P:/scenes/shot.ma"
        self.sb.message_box.return_value = "Save"
        self.slots.b014()
        self.tk.EnvUtils.save_autosave_to_original.assert_called_once_with(
            "P:/scenes/shot.ma"
        )
        self.assertIn("shot.ma", self._message())


class _Combo:
    def __init__(self, data):
        self.data = data

    def currentData(self):
        return self.data


class _Check:
    def __init__(self, on):
        self.on = on

    def isChecked(self):
        return self.on


def _scene_info_widget(keys, scope="all", unchecked=()):
    """A tb001 widget whose option box answers like the one tb001_init builds."""
    menu = NS(cmb_scope1=_Combo(scope), cmb_profile=_Combo(True))
    for key in keys:
        setattr(menu, f"chk_section_{key}", _Check(key not in unchecked))
    return NS(option_box=NS(menu=menu))


class _Sections:
    """Stand-in for a host's ``SceneInfoSection``: one label carries an "&"."""

    ALL = ("summary", "assumptions")
    LABELS = {"summary": "Executive Summary", "assumptions": "Notes & Assumptions"}


class TestGetSceneInfo(unittest.TestCase):
    """tb001 over the host's analyzer, section vocabulary and link dispatcher."""

    def _host(self, selected=True):
        self.calls, self.views, self.messages = [], [], []
        self.adapter = object()
        tk = NS(
            SceneAnalyzer=NS(
                format_audit_html=lambda **kw: self.calls.append(kw)
                or {"_header": "<h1>Scene Info</h1>", "summary": "<p>ok</p>"}
            ),
            SceneInfoSection=_Sections,
            UiUtils=NS(dispatch_log_link=lambda url, logger=None: True),
            CoreUtils=NS(selected_objects=lambda: ["obj"] if selected else []),
        )
        return _make(
            NS(
                tk=tk,
                loaded_ui=NS(scene=NS(), scene_submenu=NS()),
                message_box=lambda text, *a, **k: self.messages.append(text),
                text_view_dialog=lambda text, *a, **k: self.views.append((text, k)),
                progress=lambda **k: contextlib.nullcontext(None),
                progress_adapter=lambda update: self.adapter,
                logger=mock.Mock(),
            )
        )

    def test_the_run_hands_the_engine_scope_sections_and_progress(self):
        slots = self._host()
        slots.tb001(_scene_info_widget(_Sections.ALL, "all", unchecked=("summary",)))
        (kwargs,) = self.calls
        self.assertEqual(kwargs["scope"], "all")
        self.assertEqual(kwargs["sections"], ["assumptions"])
        self.assertIs(kwargs["adaptive"], True)
        self.assertIs(kwargs["progress_callback"], self.adapter)
        ((html, view),) = self.views
        self.assertTrue(html.startswith("<h1>Scene Info</h1>"))
        handler = view["link_handler"]
        self.assertIsInstance(handler, functools.partial)
        self.assertIs(handler.func, slots.tk.UiUtils.dispatch_log_link)
        self.assertIs(handler.keywords["logger"], slots.sb.logger)

    def test_selection_scope_needs_a_selection(self):
        slots = self._host(selected=False)
        slots.tb001(_scene_info_widget(_Sections.ALL, "selection"))
        self.assertEqual(self.calls, [])
        self.assertIn("Nothing selected", self.messages[0])
        slots.tb001(_scene_info_widget(_Sections.ALL, "all"))  # Entire Scene needs none
        self.assertEqual(len(self.calls), 1)

    def test_no_sections_is_a_message_not_a_report(self):
        slots = self._host()
        slots.tb001(_scene_info_widget(_Sections.ALL, unchecked=_Sections.ALL))
        self.assertEqual(self.calls, [])
        self.assertIn("No sections selected", self.messages[0])

    def test_every_section_of_both_hosts_has_a_tooltip(self):
        """The hosts share one section vocabulary (mayatk's ``audit_records``,
        blendertk's ``scene_audit``, drift-tested there)."""
        self.assertEqual(
            set(SceneSlots._TB001_SECTION_TIPS),
            {
                "overview",
                "summary",
                "fix_first",
                "pareto",
                "offenders",
                "materials",
                "textures",
                "pipeline",
                "assumptions",
            },
        )

    @unittest.skipUnless(qt_widgets_available(), "QWidget construction aborts here")
    def test_an_ampersand_label_stays_literal_and_binds_no_mnemonic(self):
        from qtpy import QtGui, QtWidgets
        from uitk.widgets.label import Label
        from uitk.widgets.menu import Menu

        QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        slots = self._host()
        slots.sb.registered_widgets = NS(Label=Label)
        menu = Menu()
        slots.tb001_init(NS(option_box=NS(menu=menu)))
        box = menu.chk_section_assumptions
        # "&&" draws one "&"; a lone "&" drew none and bound Alt+Space.
        self.assertEqual(box.text(), "Notes && Assumptions")
        self.assertTrue(QtGui.QKeySequence.mnemonic(box.text()).isEmpty())
        self.assertEqual(menu.chk_section_summary.text(), "Executive Summary")
        for key in _Sections.ALL:
            self.assertTrue(getattr(menu, f"chk_section_{key}").toolTip(), key)
        self.assertEqual(
            [menu.cmb_profile.itemData(i) for i in range(menu.cmb_profile.count())],
            [True, False],
        )


# --------------------------------------------------------------------- in Maya
cmds = maya_module("maya.cmds")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class _InMaya(unittest.TestCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        cmds.file(new=True, force=True)
        self.addCleanup(cmds.file, new=True, force=True)
        self.mtk = maya_module("mayatk")
        self.sb = mock.MagicMock()
        self.sb.tk = self.mtk
        self.sb.loaded_ui.scene.footer = None  # no workspace subscription under test
        self.slots = SceneSlots(self.sb)


class TestListsInMaya(_InMaya):
    def test_maya_lists_its_own_commands_and_the_blender_hand_off(self):
        imports = _labels(self.slots._list_rows(SceneSlots._IMPORT_ROWS, "import"))
        exports = self.slots._list_rows(SceneSlots._EXPORT_ROWS, "export")
        tagged = [(label, requires) for label, _, requires in exports]
        self.assertEqual(imports[:2], ["Import File", "Import Options"])
        self.assertIn("Import Blender Scene", imports)
        self.assertIn(("Export .blend", None), tagged)
        self.assertIn(("Export glTF", "maya"), tagged)
        self.assertNotIn("Export FBX", _labels(exports))

    def test_the_footer_reads_the_workspace_name(self):
        self.assertIsInstance(self.slots._workspace_status(), str)


class TestRecentFilesInMaya(_InMaya):
    def test_a_saved_scene_reopens_from_its_row(self):
        import pythontk as ptk

        store = ptk.TempArtifacts.scoped("tentacle_scene_recent")
        self.addCleanup(store.cleanup)
        path = os.path.join(store.dir_path(), "recent.ma")
        cmds.polyCube(name="recent_cube")
        cmds.file(rename=path)
        cmds.file(save=True, type="mayaAscii", force=True)
        cmds.file(new=True, force=True)
        self.slots.list000(NS(item_data=lambda: path))
        self.assertTrue(cmds.objExists("recent_cube"))
        self.sb.message_box.assert_not_called()


class TestConfirmDenseExportInMaya(_InMaya):
    """The dense-export gate over ``mtk.EnvUtils.scene_triangle_count``."""

    def test_no_warning_when_tangents_off_or_below_threshold(self):
        cmds.select(cmds.polyCube()[0])
        self.sb.message_box.return_value = "No"
        self.assertTrue(self.slots._confirm_dense_export(True, False))
        self.assertTrue(self.slots._confirm_dense_export(True, True))
        self.sb.message_box.assert_not_called()

    def test_warns_when_dense_and_respects_choice(self):
        cmds.select(cmds.polySphere(sx=20, sy=20)[0])
        with mock.patch.object(SceneSlots, "_DENSE_TRI_THRESHOLD", 100):
            self.sb.message_box.return_value = "No"
            self.assertFalse(self.slots._confirm_dense_export(True, True))
            self.sb.message_box.return_value = "Yes"
            self.assertTrue(self.slots._confirm_dense_export(True, True))


class TestGetSceneInfoInMaya(_InMaya):
    """tb001 hands mtk's analyzer its scope and the viewer its link handler.

    Regression: Entire Scene passed ``cmds.ls(type="mesh")`` -- one name per SHAPE --
    so every instance past the first went uncounted, and the report's object names
    were inert text.
    """

    def setUp(self):
        super().setUp()
        self.views = []
        self.sb.progress = lambda **kwargs: contextlib.nullcontext(lambda *a, **k: None)
        self.sb.progress_adapter = lambda update: None
        self.sb.text_view_dialog = lambda text, *b, **k: self.views.append((text, k))
        cube = cmds.polyCube(name="info_cube")[0]
        cmds.instance(cube)
        cmds.select(clear=True)

    def _widget(self, scope="all", unchecked=()):
        return _scene_info_widget(self.mtk.SceneInfoSection.ALL, scope, unchecked)

    def test_entire_scene_counts_instances_and_links_names(self):
        self.slots.tb001(self._widget("all"))
        ((html, kwargs),) = self.views
        self.assertIn("2 instances of 1 unique shape", html)
        self.assertIn("action://select", html)
        # A name deleted since the report ran: the click says so, not nothing.
        url = NS(
            scheme=lambda: "action", host=lambda: "select", query=lambda: "node=gone"
        )
        self.assertFalse(kwargs["link_handler"](url))
        self.sb.logger.warning.assert_called_once_with("Object not found: gone")

    def test_unticked_sections_are_not_rendered(self):
        self.slots.tb001(self._widget("all", unchecked=("overview", "assumptions")))
        html = self.views[0][0]
        self.assertNotIn("Scene Overview", html)
        self.assertNotIn("Notes &amp; Assumptions", html)
        self.assertIn("Executive Summary", html)

    def test_a_selected_object_set_is_a_selection(self):
        # The audit resolves a set to its members; the guard reads the whole
        # selection, a set included.
        cmds.select(cmds.sets("info_cube", name="info_set"), noExpand=True)
        self.slots.tb001(self._widget("selection"))
        self.sb.message_box.assert_not_called()
        self.assertEqual(len(self.views), 1)


class TestFixNonOrthogonalInMaya(_InMaya):
    """tb002 over mtk: an inherited shear, Entire Scene, fixed in one click."""

    def test_an_inherited_shear_is_fixed(self):
        parent = cmds.group(empty=True, name="skew_parent")
        cmds.setAttr(f"{parent}.scaleY", 3.0)
        child = cmds.polyCube(name="skew_child")[0]
        cmds.parent(child, parent)
        cmds.setAttr(f"{child}.rotateZ", 40.0)
        self.sb.progress = lambda **kwargs: contextlib.nullcontext(lambda *a, **k: None)
        self.sb.message_box.return_value = "Yes"
        menu = NS(
            cmb_scope2=_Combo("all"),
            chk_dry_run=_Check(False),
            chk_break_connections=_Check(False),
        )
        self.slots.tb002(NS(option_box=NS(menu=menu)))
        self.assertEqual(
            self.mtk.Diagnostics.get_non_orthogonal(
                cmds.ls(transforms=True, long=True)
            ),
            [],
        )
        self.assertIn("Fixed <hl>1</hl>", self.sb.message_box.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
