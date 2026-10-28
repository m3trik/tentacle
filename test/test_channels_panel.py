#!/usr/bin/python
# coding=utf-8
"""The Channels panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` -- either host's shape: Maya's
engine with its channel box, keyable / visibility flags, Shape / History
selection, enums and per-node callbacks, or Blender's without them -- and
records what the panel asks of it, the undo chunks it opens included. The
widgets are mocks. Then the panel loads for real through Blender's handler (Qt,
no bpy) over ``btk``, and in Maya drives the real ``mtk`` on a real scene. The
engines' own side is the libraries' (``test_channels.py`` in each).
"""

import contextlib
import os
import sys
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

from qtpy import QtCore

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools import channels as channels_module
from tentacle.slots.tools._channels.attribute_form import AttributeForm
from tentacle.slots.tools._channels.inline_rename import InlineRename
from tentacle.slots.tools.channels import ChannelsSlots

Qt = QtCore.Qt
MONO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(tentacle.__file__)))
)

#: What only Maya's engine has; the Blender-shaped fake drops them, as blendertk
#: does (no channel box, keyable / visibility flag, shape node, enum property,
#: per-object callback).
MAYA_ONLY = (
    "toggle_keyable",
    "hide_attrs",
    "show_attrs",
    "lock_and_hide_attrs",
    "get_shape_nodes",
    "get_history_nodes",
    "link_channel_box",
    "unlink_channel_box",
    "channel_box_selection",
    "select_in_channel_box",
    "watch_nodes",
    "get_enum_fields",
)

#: Each host's declared panel constants (the engines' class attributes).
HOSTS = {
    "maya": dict(
        FILTER_MAP={"Custom": {}, "Keyable": {}, "Channel Box": {}, "All": {}},
        KEYABLE_STATES=frozenset(
            {"none", "keyframe", "keyframe_active", "keyframe_changed"}
        ),
        SCRUBBABLE_TYPES=frozenset({"double", "doubleLinear", "long", "short"}),
        INTEGER_TYPES=frozenset({"long", "short"}),
        CREATE_TYPES=("float", "int", "bool", "string", "enum", "double3"),
        EDITORS={
            "channel_control": ("Channel Control", "Open Maya's Channel Control."),
            "connection_editor": ("Connection Editor", "Open the Connection Editor."),
        },
    ),
    "blender": dict(
        FILTER_MAP={"Custom": "custom", "Keyable": "keyable", "All": "all"},
        KEYABLE_STATES=frozenset(
            {
                "none",
                "keyframe",
                "keyframe_active",
                "keyframe_changed",
                "constraint",
                "muted",
            }
        ),
        SCRUBBABLE_TYPES=frozenset({"float", "int"}),
        INTEGER_TYPES=frozenset({"int"}),
        CREATE_TYPES=("float", "int", "bool", "string", "vector"),
        EDITORS={
            "properties": ("Properties Editor", "Open the Properties editor."),
            "drivers": ("Drivers Editor", "Open the Drivers editor."),
            "graph": ("Graph Editor", "Open the Graph editor."),
        },
    ),
}

ROWS = [
    ["translateX", "", "", "0", "doubleLinear"],
    ["translateY", "", "", "2", "doubleLinear"],
    ["weight", "", "", "1", "double"],
]
STATES = [(False, "none"), (True, "keyframe"), (False, "none")]


def _engine(host, nodes):
    """A host's ``Channels`` class (a mock): its instance is the controller."""
    cls = mock.MagicMock(name=f"{host}.Channels")
    if host == "blender":
        for name in MAYA_ONLY:
            delattr(cls, name)
    ctl = cls.return_value
    for name, value in HOSTS[host].items():
        setattr(ctl, name, value)
    ctl.single_object_mode = False
    ctl.is_pinned = False
    ctl.get_selected_nodes.return_value = list(nodes)
    # As the engine: a pin is what it reports as the targets from then on;
    # pinning None clears it, back to the selection.
    ctl.pin_targets.side_effect = lambda targets: setattr(
        ctl.get_selected_nodes,
        "return_value",
        list(nodes) if targets is None else list(targets),
    )
    ctl.node_name.side_effect = lambda n, full=False: (
        None if n is None else (n if full else n.rsplit("|", 1)[-1])
    )
    ctl.get_filter_kwargs.side_effect = lambda key, invert=False: {
        "filter": key,
        "invert": invert,
    }
    ctl.build_table_data.return_value = ([list(r) for r in ROWS], list(STATES))
    ctl.get_custom_attrs.return_value = ["weight"]
    ctl.collect_value_strings.side_effect = lambda ns, names: {
        n: ("1.5", "keyframe_changed") for n in names
    }
    ctl.get_attr_type.return_value = sorted(HOSTS[host]["SCRUBBABLE_TYPES"])[0]
    ctl.get_numeric_values.side_effect = lambda ns, attr: {
        n: float(i + 1) for i, n in enumerate(ns)
    }
    ctl.format_value.side_effect = str
    ctl.defer.side_effect = lambda fn: fn()
    ctl.can_freeze_selection.return_value = True
    ctl.has_unfreeze_info.return_value = True
    ctl.open_editor.return_value = True
    ctl.rename_node.side_effect = lambda node, name: f"|{name}"
    return cls


def _item(text, column=0, data=None):
    item = mock.MagicMock(name=f"item:{text}")
    item.text.return_value = text
    item.column.return_value = column
    item.data.return_value = data
    return item


def _rows(table, names, states=None, value_text="0"):
    """Give the mock *table* rows named *names* (icon states *states*)."""
    items = {
        (row, col): _item(name if col == 0 else value_text, col)
        for row, name in enumerate(names)
        for col in range(5)
    }
    table.item.side_effect = lambda row, col: items.get((row, col))
    table.rowCount.return_value = len(names)
    table.cellWidget.return_value = None
    if states is not None:
        table.actions.get.side_effect = lambda row, col: states[row]
    return items


def _panel(host="maya", tk=None, nodes=("|grp|cube",)):
    """A ChannelsSlots over mock widgets and a fake *host* toolkit (or *tk*,
    handed over before the panel is built, as ``Slots.tk`` is). The fake's undo
    chunks land in ``sb.events``."""
    sb = mock.MagicMock()
    sb.events = []
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.Channels = _engine(host, nodes)

        @contextlib.contextmanager
        def undo_chunk(name=""):
            sb.events.append(("open", name))
            try:
                yield
            finally:
                sb.events.append(("close", name))

        sb.tk.CoreUtils.undo_chunk.side_effect = undo_chunk
    ui = sb.loaded_ui.channels
    # No footer: its inline rename builds a real QLineEdit (the loaded panel's
    # test covers it), and a QWidget needs a QApplication.
    ui.footer = None
    table = ui.tbl000
    table.is_initialized = False
    table._ch_scrub_conns = {}
    table.rowCount.return_value = 0
    table.selectedItems.return_value = []
    table.signalsBlocked.return_value = False
    table.cellWidget.return_value = None
    header = table.verticalHeader.return_value
    header.defaultSectionSize.return_value = 22
    header.minimumSectionSize.return_value = 20
    ui.txt000.text.return_value = ""
    ui.cmb000.currentText.return_value = "Custom"
    slots = ChannelsSlots(sb)
    return slots, sb


def _added_names(menu):
    return [c.kwargs.get("setObjectName") for c in menu.add.call_args_list]


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

    def modifiers(self, value):
        """Hold *value* as the live keyboard modifiers for this test."""
        patcher = mock.patch.object(
            ChannelsSlots, "_keyboard_modifiers", return_value=value
        )
        patcher.start()
        self.addCleanup(patcher.stop)


# ---------------------------------------------------------------------------
# Setup, header, filter
# ---------------------------------------------------------------------------


class TestChannelsPanelSetup(_PanelCase):
    def test_the_engine_is_the_hosts(self):
        slots, sb = _panel()
        sb.tk.Channels.assert_called_once_with()
        self.assertIs(slots.controller, sb.tk.Channels.return_value)

    def test_the_filter_combo_lists_the_hosts_filters(self):
        for host in HOSTS:
            with self.subTest(host=host):
                slots, sb = _panel(host)
                combo = mock.MagicMock()
                slots.cmb000_init(combo)
                combo.addItems.assert_called_once_with(list(HOSTS[host]["FILTER_MAP"]))
                combo.option_box.add_action.assert_called_once()

    def test_the_header_keeps_its_saved_names_and_builds_the_hosts_editors(self):
        expected = {
            "maya": ["hdr_channel_control", "hdr_connection_editor"],
            "blender": ["hdr_properties", "hdr_drivers", "hdr_graph"],
        }
        for host, editors in expected.items():
            with self.subTest(host=host):
                slots, sb = _panel(host)
                header = mock.MagicMock()
                slots.header_init(header)
                names = _added_names(header.menu)
                for name in (
                    "show_create_menu",
                    "chk_show_type",
                    "chk_compact_view",
                    "chk_auto_fit",
                    *editors,
                ):
                    self.assertIn(name, names)
                header.set_help_text.assert_called_once()

    def test_an_editor_button_opens_through_the_engine(self):
        slots, sb = _panel("blender")
        header = mock.MagicMock()
        buttons = {}
        header.menu.add.side_effect = lambda kind, **kw: buttons.setdefault(
            kw.get("setObjectName"), mock.MagicMock()
        )
        slots.header_init(header)
        click = buttons["hdr_graph"].clicked.connect.call_args.args[0]
        click(False)
        slots.controller.open_editor.assert_called_once_with("graph")
        slots.controller.open_editor.return_value = False
        click(False)
        sb.message_box.assert_called_once_with("Could not open Graph Editor.")

    def test_the_help_names_the_footer_helpers_only_where_they_exist(self):
        for host, footer in (("maya", True), ("blender", False)):
            with self.subTest(host=host):
                slots, sb = _panel(host)
                slots._help_text()
                sections = sb.tooltip.fmt.call_args.kwargs["sections"]
                titles = [title for title, _lines in sections]
                self.assertEqual("Selection helpers (footer)" in titles, footer)
                body = sb.tooltip.fmt.call_args.kwargs["body"]
                self.assertNotIn("Maya node", body)

    def test_launch_config_pins_filters_and_searches(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.channels
        slots.apply_launch_config(
            targets=["|carrier"], filter="Custom", search="clip_*"
        )
        slots.controller.pin_targets.assert_called_once_with(["|carrier"])
        ui.cmb000.setCurrentText.assert_called_once_with("Custom")
        ui.txt000.setText.assert_called_once_with("clip_*")
        ui.cmb000.setCurrentText.reset_mock()
        with self.assertLogs(channels_module._log, "WARNING"):
            slots.apply_launch_config(filter="No Such Filter")
        ui.cmb000.setCurrentText.assert_not_called()

    def test_launch_shows_the_panel_and_configures_it(self):
        sb = mock.MagicMock()
        ui = ChannelsSlots.launch(sb, targets=["|a"], filter="Keyable")
        sb.handlers.marking_menu.show.assert_called_once_with("channels")
        self.assertIs(ui, sb.handlers.marking_menu.show.return_value)
        sb.get_slots_instance.return_value.apply_launch_config.assert_called_once_with(
            targets=["|a"], filter="Keyable", search=None
        )


# ---------------------------------------------------------------------------
# The table: refresh, rows, context menu
# ---------------------------------------------------------------------------


class TestChannelsPanelTable(_PanelCase):
    def test_a_refresh_asks_the_engine_for_the_filtered_rows(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        slots._filter_invert = True
        slots._refresh_table(table)
        ctl = slots.controller
        ctl.get_filter_kwargs.assert_called_with("Custom", True)
        ctl.build_table_data.assert_called_with(
            ["|grp|cube"], {"filter": "Custom", "invert": True}
        )
        table.add.assert_called_with(ROWS, headers=ChannelsSlots.HEADERS)
        table.actions.set.assert_any_call(1, ChannelsSlots.COL_LOCK, "locked")
        table.actions.set.assert_any_call(1, ChannelsSlots.COL_CONN, "keyframe")

    def test_no_targets_show_one_placeholder_row(self):
        slots, sb = _panel(nodes=())
        table = sb.loaded_ui.channels.tbl000
        slots._refresh_table(table)
        table.add.assert_called_with(
            [["No selection", "", "", "", ""]], headers=ChannelsSlots.HEADERS
        )
        slots.controller.build_table_data.assert_not_called()

    def test_a_host_with_no_scene_reads_as_no_selection(self):
        """Blender's handler loads the panel without bpy: the engine raises."""
        slots, sb = _panel("blender")
        slots.controller.get_selected_nodes.side_effect = ImportError("bpy")
        table = sb.loaded_ui.channels.tbl000
        slots._refresh_table(table)
        table.add.assert_called_with(
            [["No selection", "", "", "", ""]], headers=ChannelsSlots.HEADERS
        )

    def test_the_name_filter_keeps_the_wildcard_matches(self):
        slots, sb = _panel()
        sb.loaded_ui.channels.txt000.text.return_value = "translate*"
        rows, states = slots._apply_name_filter(ROWS, STATES)
        self.assertEqual([r[0] for r in rows], ["translateX", "translateY"])
        self.assertEqual(states, STATES[:2])
        slots._filter_enabled = False
        self.assertEqual(slots._apply_name_filter(ROWS, STATES), (ROWS, STATES))

    def test_a_refresh_during_a_refresh_runs_once_after_it(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        slots._refreshing = True
        slots._refresh_table(table)  # queued, not run
        self.assertTrue(slots._refresh_queued)
        slots.controller.build_table_data.assert_not_called()
        slots._refreshing = False
        slots._refresh_table(table)  # runs, then the queued one through defer
        self.assertEqual(slots.controller.build_table_data.call_count, 2)
        self.assertFalse(slots._refresh_queued)

    def test_only_a_lone_targets_custom_names_are_editable(self):
        """A rename across several targets has no single outcome."""
        slots, sb = _panel()
        table = mock.MagicMock()
        items = _rows(table, ["translateX", "weight"])
        for row in range(2):
            items[(row, 0)].flags.return_value = Qt.ItemIsEnabled

        def editable():
            return [
                bool(items[(row, 0)].setFlags.call_args.args[0] & Qt.ItemIsEditable)
                for row in range(2)
            ]

        slots._set_name_editability(table, ["|a"])
        self.assertEqual(editable(), [False, True])
        items[(1, 0)].setData.assert_called_once_with(Qt.UserRole, "weight")
        slots.controller.get_custom_attrs.reset_mock()
        slots._set_name_editability(table, ["|a", "|b"])
        self.assertEqual(editable(), [False, False])
        slots.controller.get_custom_attrs.assert_not_called()

    def test_the_context_menu_drops_what_the_host_lacks(self):
        maya_only = {"ctx_toggle_keyable", "ctx_hide", "ctx_show", "ctx_lock_and_hide"}
        for host in HOSTS:
            with self.subTest(host=host):
                slots, sb = _panel(host)
                table = mock.MagicMock()
                slots._build_context_menu(table)
                names = {n for n in _added_names(table.menu) if n}
                self.assertIn("ctx_freeze_transforms", names)
                self.assertEqual(maya_only <= names, host == "maya")
                self.assertEqual(bool(maya_only & names), host == "maya")

    def test_menu_handlers_and_icons_rebind_on_every_init(self):
        """The table can outlive a slots instance: a second init (the widget
        already initialized) re-binds, and builds the menu items only once."""
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        slots.tbl000_init(table)
        first = table.register_menu_action.call_count
        builds = table.menu.add.call_count
        table.is_initialized = True
        slots.tbl000_init(table)
        self.assertEqual(table.register_menu_action.call_count, 2 * first)
        self.assertEqual(table.menu.add.call_count, builds)
        self.assertEqual(table.actions.add.call_count, 4)  # 2 columns x 2 inits
        allowed = {
            c.args[0]
            for c in table.register_menu_action.call_args_list
            if c.kwargs["allow_empty"]
        }
        self.assertEqual(allowed, set(ChannelsSlots._NODE_LEVEL_ACTIONS))

    def test_menu_rows_reach_the_engine_by_name(self):
        slots, sb = _panel()
        rows = [{"name": "translateX"}, {"name": "weight"}]
        nodes = ["|grp|cube"]
        ctl = slots.controller
        for handler, method, args in (
            ("_ctx_lock", "set_lock", (True,)),
            ("_ctx_unlock", "set_lock", (False,)),
            ("_ctx_reset_default", "reset_to_default", ()),
            ("_ctx_toggle_keyable", "toggle_keyable", ()),
            ("_ctx_hide", "hide_attrs", ()),
            ("_ctx_breakdown", "set_breakdown_key", ()),
            ("_ctx_mute", "mute_attrs", ()),
            ("_ctx_unmute", "unmute_attrs", ()),
            ("_ctx_delete", "delete_attributes", ()),
        ):
            with self.subTest(handler=handler):
                getattr(slots, handler)(rows)
                getattr(ctl, method).assert_called_with(
                    nodes, ["translateX", "weight"], *args
                )

    def test_copy_reports_and_paste_needs_no_row(self):
        slots, sb = _panel()
        slots.controller.copy_attr_values.return_value = {"translateX": 1.0}
        slots._ctx_copy_values([{"name": "translateX"}])
        sb.message_box.assert_called_once_with("Result: Copied 1 attribute value(s).")
        slots._ctx_paste_values([])
        slots.controller.paste_attr_values.assert_called_once_with(["|grp|cube"])

    def test_freeze_with_no_row_freezes_everything(self):
        slots, sb = _panel()
        slots._ctx_freeze_transforms([])
        slots.controller.freeze_transforms.assert_called_once_with(
            ["|grp|cube"], attrs=None
        )
        slots._ctx_unfreeze_transforms([{"name": "translateX"}])
        slots.controller.unfreeze_transforms.assert_called_once_with(
            ["|grp|cube"], attrs=["translateX"]
        )

    def test_freeze_is_gated_on_whole_groups(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        table.get_selection.return_value = [{"name": "translateX"}]
        ctl = slots.controller
        ctl.can_freeze_selection.return_value = False
        slots._update_context_menu_state()
        ctl.can_freeze_selection.assert_called_once_with(["translateX"])
        table.menu.ctx_freeze_transforms.setEnabled.assert_called_once_with(False)
        table.menu.ctx_unfreeze_transforms.setToolTip.assert_called_once_with(
            ChannelsSlots._UNFREEZE_TIP_BAD_SELECTION
        )

    def test_select_connection_says_when_nothing_drives_the_row(self):
        slots, sb = _panel()
        slots.controller.select_connections.return_value = False
        slots._ctx_select_connection([{"name": "weight"}])
        slots.controller.select_connections.assert_called_once_with(
            ["|grp|cube"], "weight"
        )
        sb.message_box.assert_called_once_with("Warning: Nothing drives 'weight'.")


# ---------------------------------------------------------------------------
# Lock / Key icon cells
# ---------------------------------------------------------------------------


class TestChannelsPanelIcons(_PanelCase):
    """A click on a Lock / Key icon toggles it; a drag SETS every row it
    crosses (Alt clears, Ctrl breaks), as ONE undo step with one refresh."""

    def _icons(self, state, host="maya", names=("translateX",), modifiers=None):
        self.modifiers(Qt.NoModifier if modifiers is None else modifiers)
        slots, sb = _panel(host)
        table = sb.loaded_ui.channels.tbl000
        _rows(table, list(names), [state] * len(names))
        slots._refresh_table = mock.Mock()
        return slots, sb

    def test_a_click_toggles_the_lock(self):
        for state, lock in (("locked", False), ("unlocked", True)):
            slots, sb = self._icons(state)
            slots._on_icon_cell_clicked(0, ChannelsSlots.COL_LOCK)
            slots.controller.set_lock.assert_called_once_with(
                ["|grp|cube"], ["translateX"], lock
            )
            slots._refresh_table.assert_called_once()

    def test_alt_click_unlocks(self):
        slots, sb = self._icons("unlocked", modifiers=Qt.AltModifier)
        slots._on_icon_cell_clicked(0, ChannelsSlots.COL_LOCK)
        slots.controller.set_lock.assert_called_once_with(
            ["|grp|cube"], ["translateX"], False
        )

    def test_a_click_toggles_the_key_and_keys_a_changed_value(self):
        for state, keyed in (
            ("keyframe_active", False),
            ("none", True),
            ("keyframe", True),
            ("keyframe_changed", True),
        ):
            with self.subTest(state=state):
                slots, sb = self._icons(state)
                slots._on_icon_cell_clicked(0, ChannelsSlots.COL_CONN)
                slots.controller.set_key_at_current_time.assert_called_once_with(
                    ["|grp|cube"], "translateX", keyed=keyed
                )

    def test_alt_click_removes_the_key(self):
        slots, sb = self._icons("keyframe_active", modifiers=Qt.AltModifier)
        slots._on_icon_cell_clicked(0, ChannelsSlots.COL_CONN)
        slots.controller.set_key_at_current_time.assert_called_once_with(
            ["|grp|cube"], "translateX", keyed=False
        )

    def test_ctrl_click_breaks_and_never_keys(self):
        slots, sb = self._icons("keyframe", modifiers=Qt.ControlModifier)
        slots._on_icon_cell_clicked(0, ChannelsSlots.COL_CONN)
        slots.controller.break_connections.assert_called_once_with(
            ["|grp|cube"], "translateX"
        )
        slots.controller.set_key_at_current_time.assert_not_called()
        slots, sb = self._icons("none", modifiers=Qt.ControlModifier)
        slots._on_icon_cell_clicked(0, ChannelsSlots.COL_CONN)
        slots.controller.break_connections.assert_not_called()  # nothing to break

    def test_the_hosts_keyable_states_decide_a_plain_click(self):
        """A constrained channel keys in Blender (the constraint applies over
        it); in Maya the constraint drives the plug, so only Ctrl breaks it."""
        for host, keys in (("maya", False), ("blender", True)):
            with self.subTest(host=host):
                slots, sb = self._icons("constraint", host)
                slots._on_icon_cell_clicked(0, ChannelsSlots.COL_CONN)
                self.assertEqual(slots.controller.set_key_at_current_time.called, keys)

    def test_a_drag_sets_every_row_in_one_chunk_and_refreshes_once(self):
        names = ("translateX", "translateY", "translateZ")
        slots, sb = self._icons("locked", names=names)
        slots._on_icon_cells_dragged([0, 1, 2], ChannelsSlots.COL_LOCK)
        self.assertEqual(
            [c.args[1:] for c in slots.controller.set_lock.call_args_list],
            [([n], True) for n in names],
        )
        self.assertEqual(
            sb.events, [("open", "Channels Drag"), ("close", "Channels Drag")]
        )
        slots._refresh_table.assert_called_once()

    def test_a_drag_keys_every_row_and_alt_drag_removes_them(self):
        names = ("translateX", "translateY", "translateZ")
        for modifiers, keyed in ((Qt.NoModifier, True), (Qt.AltModifier, False)):
            with self.subTest(keyed=keyed):
                slots, sb = self._icons(
                    "keyframe_active", names=names, modifiers=modifiers
                )
                slots._on_icon_cells_dragged([0, 1, 2], ChannelsSlots.COL_CONN)
                calls = slots.controller.set_key_at_current_time.call_args_list
                self.assertEqual([c.kwargs["keyed"] for c in calls], [keyed] * 3)

    def test_a_ctrl_drag_breaks_every_crossed_row(self):
        names = ("translateX", "translateY", "translateZ")
        slots, sb = self._icons("keyframe", names=names, modifiers=Qt.ControlModifier)
        slots._on_icon_cells_dragged([0, 1, 2], ChannelsSlots.COL_CONN)
        self.assertEqual(
            [c.args[1] for c in slots.controller.break_connections.call_args_list],
            list(names),
        )
        slots.controller.set_key_at_current_time.assert_not_called()

    def test_the_key_column_states_and_their_tooltips(self):
        for host in HOSTS:
            with self.subTest(host=host):
                slots, sb = _panel(host)
                table = mock.MagicMock()
                slots._setup_action_columns(table)
                conn = next(
                    c.kwargs["states"]
                    for c in table.actions.add.call_args_list
                    if c.args[0] == ChannelsSlots.COL_CONN
                )
                changed = conn["keyframe_changed"]
                self.assertEqual(changed["color"], "#f08080")
                self.assertEqual(changed["action"], slots._on_icon_cell_clicked)
                keyable = HOSTS[host]["KEYABLE_STATES"]
                for state, config in conn.items():
                    self.assertEqual(
                        "click to key" in config["tooltip"]
                        or "click to remove" in config["tooltip"],
                        state in keyable,
                        (state, config["tooltip"]),
                    )


# ---------------------------------------------------------------------------
# Editing: typed values, renames, drag-fill, scrub, wheel
# ---------------------------------------------------------------------------


class TestChannelsPanelEditing(_PanelCase):
    def test_a_value_edit_sets_every_target_and_shows_what_was_stored(self):
        slots, sb = _panel(nodes=("|a", "|b"))
        table = sb.loaded_ui.channels.tbl000
        items = _rows(table, ["translateX"], ["keyframe"], value_text="7")
        slots._handle_cell_edit(0, ChannelsSlots.COL_VALUE)
        ctl = slots.controller
        ctl.set_attribute_value.assert_called_once_with(["|a", "|b"], "translateX", "7")
        ctl.collect_value_strings.assert_called_once_with(["|a", "|b"], ["translateX"])
        items[(0, ChannelsSlots.COL_VALUE)].setText.assert_called_once_with("1.5")
        table.actions.set.assert_called_with(
            0, ChannelsSlots.COL_CONN, "keyframe_changed"
        )

    def test_a_name_edit_renames_the_custom_attribute(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        item = _item("heft", data="weight")
        table.item.side_effect = lambda row, col: item
        slots._handle_cell_edit(0, ChannelsSlots.COL_NAME)
        slots.controller.rename_attribute.assert_called_once_with(
            ["|grp|cube"], "weight", "heft"
        )

    def test_a_drag_fill_is_one_chunk(self):
        slots, sb = _panel()
        slots._on_edit_batch_started()
        slots._on_edit_batch_started()  # a nested emission opens nothing more
        slots._on_edit_batch_finished()
        slots._on_edit_batch_finished()  # an unmatched finish closes nothing
        self.assertEqual(
            sb.events, [("open", "Channels Edit"), ("close", "Channels Edit")]
        )
        self.assertIsNone(slots._edit_chunk)

    def _numeric(self, host="maya", nodes=("|a", "|b")):
        self.modifiers(Qt.NoModifier)
        slots, sb = _panel(host, nodes=nodes)
        _rows(sb.loaded_ui.channels.tbl000, ["translateX"], ["none"])
        return slots, sb

    def test_a_scrub_is_one_chunk_from_its_first_move_to_its_release(self):
        slots, sb = self._numeric()
        col = ChannelsSlots.COL_VALUE
        slots._on_scrub_started(0, col)
        self.assertEqual(sb.events, [], "a press alone opens nothing")
        slots._on_scrub_moved(0, col, 10, 0)
        slots._on_scrub_moved(0, col, 20, 0)
        self.assertEqual(sb.events, [("open", "Scrub translateX")])
        slots._on_scrub_finished(0, col)
        self.assertEqual(sb.events[-1], ("close", "Scrub translateX"))
        # start + delta per target, never accumulated: 20px x 0.01.
        last = slots.controller.set_numeric_values.call_args.args
        self.assertEqual(last[1], "translateX")
        self.assertEqual(
            {k: round(v, 4) for k, v in last[0].items()}, {"|a": 1.2, "|b": 2.2}
        )

    def test_a_scrub_that_never_moved_pushes_nothing(self):
        slots, sb = self._numeric()
        slots._on_scrub_started(0, ChannelsSlots.COL_VALUE)
        slots._on_scrub_finished(0, ChannelsSlots.COL_VALUE)
        self.assertEqual(sb.events, [])
        slots.controller.set_numeric_values.assert_not_called()

    def test_a_lost_release_is_closed_by_the_next_press(self):
        slots, sb = self._numeric()
        col = ChannelsSlots.COL_VALUE
        slots._on_scrub_started(0, col)
        slots._on_scrub_moved(0, col, 10, 0)
        slots._on_scrub_started(0, ChannelsSlots.COL_CONN)  # no scrub here
        self.assertEqual(
            sb.events, [("open", "Scrub translateX"), ("close", "Scrub translateX")]
        )
        self.assertIsNone(slots._scrub_state)

    def test_an_int_scrub_steps_whole_units(self):
        slots, sb = self._numeric("blender")
        slots.controller.get_attr_type.return_value = "int"
        slots._on_scrub_started(0, ChannelsSlots.COL_VALUE)
        slots._on_scrub_moved(0, ChannelsSlots.COL_VALUE, 9, 0)  # 9px / 4 -> 2
        values = slots.controller.set_numeric_values.call_args.args[0]
        self.assertEqual(values, {"|a": 3, "|b": 4})

    def test_a_non_numeric_row_does_not_scrub(self):
        slots, sb = self._numeric()
        slots.controller.get_attr_type.return_value = "string"
        slots._on_scrub_started(0, ChannelsSlots.COL_VALUE)
        self.assertIsNone(slots._scrub_state)

    def test_a_wheel_notch_steps_every_target_as_one_chunk(self):
        slots, sb = self._numeric()
        slots._on_wheel_scrolled(0, ChannelsSlots.COL_VALUE, 1, Qt.NoModifier)
        self.assertEqual(
            sb.events, [("open", "Wheel translateX"), ("close", "Wheel translateX")]
        )
        values, attr = slots.controller.set_numeric_values.call_args.args
        self.assertEqual(attr, "translateX")
        self.assertEqual(
            {k: round(v, 4) for k, v in values.items()}, {"|a": 1.1, "|b": 2.1}
        )

    def test_alt_on_an_int_consumes_the_notch(self):
        slots, sb = self._numeric()
        slots.controller.get_attr_type.return_value = "long"
        slots._on_wheel_scrolled(0, ChannelsSlots.COL_VALUE, 1, Qt.AltModifier)
        slots.controller.set_numeric_values.assert_not_called()
        self.assertEqual(sb.events, [])

    def test_the_wheel_ladder(self):
        slots, sb = _panel()
        step = slots._wheel_step
        self.assertEqual(step(Qt.NoModifier, False), 0.1)
        self.assertEqual(step(Qt.ControlModifier, False), 1.0)
        self.assertEqual(step(Qt.ControlModifier | Qt.ShiftModifier, False), 10.0)
        self.assertEqual(step(Qt.AltModifier, False), 0.01)
        self.assertEqual(step(Qt.ControlModifier | Qt.AltModifier, False), 0.0001)
        self.assertEqual(step(Qt.ControlModifier, True), 10)
        self.assertEqual(step(Qt.AltModifier, True), 0)
        self.assertEqual(step(Qt.NoModifier, True), 1)

    def test_the_batch_signals_reach_the_panel(self):
        slots, sb = _panel()
        widget = mock.MagicMock()
        widget._ch_scrub_conns = {}
        slots._wire_table_signals(widget)
        widget.editBatchStarted.connect.assert_called_once_with(
            slots._on_edit_batch_started
        )
        widget.editBatchFinished.connect.assert_called_once_with(
            slots._on_edit_batch_finished
        )
        widget.cellWheelScrolled.connect.assert_called_once_with(
            slots._on_wheel_scrolled
        )


# ---------------------------------------------------------------------------
# Target, rename, create
# ---------------------------------------------------------------------------


class TestChannelsPanelTarget(_PanelCase):
    def test_the_target_field_shows_one_or_many(self):
        slots, sb = _panel()
        txt = sb.loaded_ui.channels.txt001
        slots._update_target_display(["|grp|cube"])
        txt.setText.assert_called_with("cube")
        self.assertEqual(slots._current_target, "|grp|cube")
        slots._update_target_display(["|a", "|b"])
        txt.setText.assert_called_with("Multi-selection (2)")
        self.assertIsNone(slots._current_target)

    def test_a_rename_keeps_a_pin_on_the_renamed_target(self):
        slots, sb = _panel()
        ctl = slots.controller
        ctl.is_pinned = True
        slots._current_target = "|grp|cube"
        slots._rename_target("box")
        ctl.rename_node.assert_called_once_with("|grp|cube", "box")
        ctl.pin_targets.assert_called_once_with(["|box"])
        self.assertEqual(slots._current_target, "|box")

    def test_a_handle_that_survives_its_rename_is_not_re_pinned(self):
        """Blender: the object is its own handle through a rename."""
        slots, sb = _panel("blender")
        ctl = slots.controller
        ctl.is_pinned = True
        target = object()
        ctl.rename_node.side_effect = lambda node, name: node
        slots._current_target = target
        slots._rename_target("Box")
        ctl.pin_targets.assert_not_called()

    def test_a_target_the_host_dropped_reads_as_none(self):
        slots, sb = _panel("blender")
        slots._current_target = "|gone"
        slots.controller.node_name.side_effect = lambda n, full=False: None
        self.assertIsNone(slots._target_label())
        self.assertIsNone(slots._current_target)

    def test_the_inline_rename_commits_only_an_edit(self):
        field = mock.MagicMock()
        renamed = mock.Mock()
        rename = InlineRename(field, lambda full=False: "cube", renamed)
        field.isReadOnly.return_value = True
        rename._finished()  # focus loss in display mode
        renamed.assert_not_called()
        field.isReadOnly.return_value = False
        field.text.return_value = "box "
        rename._finished()
        renamed.assert_called_once_with("box")
        field.setReadOnly.assert_called_with(True)

    def test_create_attribute_validates_then_reaches_the_engine(self):
        slots, sb = _panel()
        self.assertFalse(slots._create_attribute("", "float"))
        sb.message_box.assert_called_once_with(
            "Warning: Attribute name cannot be empty."
        )
        self.assertTrue(slots._create_attribute("weight", "float", keyable=True))
        slots.controller.create_attribute.assert_called_once_with(
            ["|grp|cube"], "weight", "float", keyable=True
        )
        slots.controller.create_attribute.side_effect = RuntimeError("exists")
        self.assertFalse(slots._create_attribute("weight", "float"))
        sb.message_box.assert_called_with("Error: exists")

    def test_the_form_offers_the_hosts_types_and_keyable_flag(self):
        for host, keyable in (("maya", True), ("blender", False)):
            with self.subTest(host=host):
                slots, sb = _panel(host)
                with mock.patch.object(AttributeForm, "show") as show:
                    slots.show_create_menu()
                show.assert_called_once_with(
                    sb,
                    sb.loaded_ui.channels,
                    HOSTS[host]["CREATE_TYPES"],
                    slots._create_attribute,
                    keyable=keyable,
                )


class TestAttributeForm(unittest.TestCase):
    def _form(self, types, keyable=True, on_create=None):
        sb = mock.MagicMock()
        widgets = {}

        def add(kind, **kwargs):
            key = (
                kwargs.get("setObjectName")
                or kwargs.get("setText")
                or (f"{kind}:{len(widgets)}")
            )
            return widgets.setdefault(key, mock.MagicMock(name=key))

        menu = sb.registered_widgets.Menu.return_value
        menu.add.side_effect = add
        on_create = on_create or mock.Mock(return_value=True)
        AttributeForm.show(sb, "parent", types, on_create, keyable=keyable)
        return sb, menu, widgets, on_create

    def test_enum_names_show_only_for_a_host_with_enums(self):
        _sb, _menu, widgets, _ = self._form(HOSTS["maya"]["CREATE_TYPES"])
        self.assertIn("le_enum_names", widgets)
        _sb, _menu, widgets, _ = self._form(HOSTS["blender"]["CREATE_TYPES"])
        self.assertNotIn("le_enum_names", widgets)

    def test_the_range_shows_for_the_ranged_types_only(self):
        sb, _menu, _widgets, _ = self._form(HOSTS["blender"]["CREATE_TYPES"])
        fields = sb.FieldVisibility.return_value
        defined = [c.args[0] for c in fields.define.call_args_list]
        self.assertEqual(defined, ["float", "int", "vector"])

    def test_without_a_keyable_flag_the_box_is_checked_and_disabled(self):
        _sb, _menu, widgets, _ = self._form(HOSTS["blender"]["CREATE_TYPES"], False)
        widgets["chk_keyable"].setEnabled.assert_called_once_with(False)

    def test_create_hands_the_values_over_and_closes_on_success(self):
        _sb, menu, widgets, on_create = self._form(HOSTS["maya"]["CREATE_TYPES"])
        widgets["le_attr_name"].text.return_value = " my attr "
        widgets["cmb_attr_type"].currentText.return_value = "enum"
        widgets["le_enum_names"].text.return_value = "A:B"
        widgets["chk_keyable"].isChecked.return_value = False
        for key, value in (("spn_min", -1.0), ("spn_max", 5.0), ("spn_default", 2.0)):
            widgets[key].value.return_value = value
        widgets["Create"].clicked.connect.call_args.args[0]()
        on_create.assert_called_once_with(
            name="my_attr",
            attr_type="enum",
            keyable=False,
            min_val=-1.0,
            max_val=5.0,
            default_val=2.0,
            enum_names="A:B",
        )
        menu.hide.assert_called_once()


# ---------------------------------------------------------------------------
# Live updates
# ---------------------------------------------------------------------------


class TestChannelsPanelLive(_PanelCase):
    def test_the_scene_is_watched_once_per_instance(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        slots.tbl000_init(table)
        table.is_initialized = True
        slots.tbl000_init(table)
        ctl = slots.controller
        ctl.watch_scene.assert_called_once()
        args, kwargs = ctl.watch_scene.call_args
        self.assertIs(args[0], slots)
        self.assertIs(kwargs["widget"], table)

    def test_maya_links_its_channel_box_and_watches_the_targets(self):
        slots, sb = _panel()
        slots.tbl000_init(sb.loaded_ui.channels.tbl000)
        ctl = slots.controller
        ctl.link_channel_box.assert_called_once_with(
            slots._on_cb_selection_changed, slots._selected_channel_rows
        )
        self.assertEqual(ctl.watch_nodes.call_args.args[:2], (slots, ["|grp|cube"]))

    def test_blender_has_no_channel_box_and_no_per_object_callbacks(self):
        slots, sb = _panel("blender")
        slots.tbl000_init(sb.loaded_ui.channels.tbl000)
        ctl = slots.controller
        ctl.watch_scene.assert_called_once()
        ctl.link_channel_box.assert_not_called()
        ctl.watch_nodes.assert_not_called()
        ctl.channel_box_selection.assert_not_called()

    def test_cleanup_ends_every_subscription(self):
        slots, sb = _panel()
        slots._attr_change_tokens = [7]
        slots.cleanup_scene_callbacks()
        slots.controller.unlink_channel_box.assert_called_once_with()
        slots.controller.unwatch.assert_called_once_with(owner=slots)
        self.assertTrue(slots._destroyed)
        self.assertFalse(slots._watching)

    def test_a_burst_of_scene_events_is_one_deferred_rebuild(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        deferred = []
        slots.controller.defer.side_effect = deferred.append
        slots._refresh_table = mock.Mock()
        for _ in range(3):
            slots._on_scene_change(table)
        self.assertEqual(len(deferred), 1)
        deferred[0]()
        slots._refresh_table.assert_called_once_with(table)
        slots._on_scene_change(table)
        self.assertEqual(len(deferred), 2, "the next event schedules again")

    def test_attribute_changes_coalesce_into_one_flush(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        deferred = []
        slots.controller.defer.side_effect = deferred.append
        slots._on_attr_changed(table, "translateX", False, True)
        slots._on_attr_changed(table, "translateY", True, True)
        slots._on_attr_changed(table, "translateX", False, True)
        self.assertEqual(len(deferred), 1)
        self.assertEqual(slots._pending_value_attrs, {"translateX", "translateY"})
        self.assertEqual(slots._pending_lock_attrs, {"translateY"})
        _rows(table, ["translateX", "translateY"], ["none", "none"])
        deferred[0]()
        self.assertEqual(slots._pending_value_attrs, set())
        slots.controller.is_locked.assert_called_once_with("|grp|cube", "translateY")

    def test_a_values_refresh_from_a_worker_thread_is_posted(self):
        """Maya fires the matrix callback on Evaluation Manager threads, where a
        ``QTimer`` never fires: the pass is posted to the GUI thread."""
        posted = []
        slots = SimpleNamespace(
            _destroyed=False,
            _values_refresh_pending=False,
            _gui_thread=SimpleNamespace(post=posted.append),
            _is_widget_alive=lambda w: True,
            _update_values_only=mock.Mock(),
        )
        worker = threading.Thread(
            target=lambda: ChannelsSlots._schedule_values_only_refresh(slots, "tbl")
        )
        worker.start()
        worker.join(timeout=5)
        self.assertEqual(len(posted), 1, "the refresh never reached the GUI thread")
        ChannelsSlots._schedule_values_only_refresh(slots, "tbl")  # coalesced
        self.assertEqual(len(posted), 1)
        posted[0]()
        slots._update_values_only.assert_called_once_with("tbl")
        self.assertFalse(slots._values_refresh_pending)

    def test_the_values_pass_updates_text_and_key_icons_in_place(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        items = _rows(table, ["translateX", "weight"], ["none", "none"])
        slots._update_values_only(table)
        slots.controller.collect_value_strings.assert_called_once_with(
            ["|grp|cube"], ["translateX", "weight"]
        )
        items[(1, ChannelsSlots.COL_VALUE)].setText.assert_called_once_with("1.5")
        table.actions.set.assert_any_call(1, ChannelsSlots.COL_CONN, "keyframe_changed")
        table.add.assert_not_called()  # no rebuild: selection and scroll kept

    def test_the_channel_box_selection_selects_rows_and_rows_push_back(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        _rows(table, ["translateX", "weight"])
        slots._on_cb_selection_changed({"weight"})
        self.assertEqual(slots._last_cb_selection, {"weight"})
        table.selectionModel.return_value.select.assert_called_once()
        table.selectedItems.return_value = [_item("translateX", 0)]
        slots._on_table_selection_changed()
        slots.controller.select_in_channel_box.assert_called_once_with(["translateX"])

    def test_a_hidden_panel_stands_in_with_no_rows(self):
        slots, sb = _panel()
        table = sb.loaded_ui.channels.tbl000
        table.selectedItems.return_value = [_item("translateX", 0)]
        table.isVisible.return_value = False
        self.assertEqual(slots._selected_channel_rows(), [])
        table.isVisible.return_value = True
        self.assertEqual(slots._selected_channel_rows(), ["translateX"])


# ---------------------------------------------------------------------------
# The panel for real: Blender's handler over btk (Qt, no bpy)
# ---------------------------------------------------------------------------


def _qt_widgets():
    try:
        from qtpy import QtWidgets

        return QtWidgets
    except Exception:  # noqa: BLE001 -- Qt absent
        return None


class _FakeEngine:
    """Enough of an engine for the value paths of the loaded panel (no bpy)."""

    SCRUBBABLE_TYPES = frozenset({"float", "int"})
    INTEGER_TYPES = frozenset({"int"})

    def __init__(self, values):
        self.vals = dict(values)

    def get_selected_nodes(self):
        return list(self.vals)

    def get_attr_type(self, node, attr):
        return "float"

    def get_numeric_values(self, nodes, attr):
        return {n: self.vals[n] for n in nodes}

    def set_numeric_values(self, values, attr):
        self.vals.update(values)

    def format_value(self, value):
        return str(value)

    def collect_value_strings(self, nodes, names):
        return {}


@unittest.skipIf(MAYA_AVAILABLE, "real Qt widgets and real Maya crash in one process")
@unittest.skipIf(_qt_widgets() is None, "Qt not available")
class TestChannelsPanelLoads(unittest.TestCase):
    """The shared panel loaded through a real (offscreen) Qt / Switchboard /
    ``BlenderUiHandler`` stack over ``btk``: compact view, the footer, and the
    table's signals surviving a slots rebuild (the former
    ``test_blender_ui_handler`` channels block)."""

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

        TestSandbox.activate()  # the panel's settings stay off the live stores
        QtWidgets = _qt_widgets()
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.btk = blendertk
        handler = BlenderUiHandler(switchboard=Switchboard())
        cls.sb = handler.sb
        Tcl.register_shared(cls.sb)
        cls.ui = handler.get("channels")
        for _ in range(5):
            cls.app.processEvents()
        cls.slots = cls.sb.get_slots_instance(cls.ui)
        cls.table = cls.ui.tbl000

    def _one_row(self, name="location_x"):
        blocked = self.table.blockSignals(True)
        try:
            self.table.add(
                [[name, "", "", "1.0", "float"]], headers=ChannelsSlots.HEADERS
            )
        finally:
            self.table.blockSignals(blocked)

    def test_the_tool_binds_tentacles_slots_over_btk(self):
        self.assertIsInstance(self.slots, ChannelsSlots)
        self.assertIs(self.slots.tk, self.btk)
        self.assertIsInstance(self.slots.controller, self.btk.Channels)

    def test_compact_view_collapses_rows_and_hides_the_column_header(self):
        slots, table = self.slots, self.table
        vh = table.verticalHeader()
        slots._on_toggle_compact_view(False)
        base = vh.defaultSectionSize()
        slots._on_toggle_compact_view(True)
        compact = vh.defaultSectionSize()
        self.assertLess(compact, base)
        self.assertTrue(table.horizontalHeader().isHidden())
        slots._on_toggle_compact_view(False)
        self.assertEqual(vh.defaultSectionSize(), base)
        self.assertFalse(table.horizontalHeader().isHidden())

    def test_the_header_wires_compact_view_and_the_footer_its_toggle(self):
        chk = getattr(self.slots, "_chk_compact", None)
        self.assertIsNotNone(chk)
        self.assertEqual(chk.objectName(), "chk_compact_view")
        self.assertIsNotNone(self.slots._footer_compact_btn)
        self.assertIsNotNone(self.slots._footer_rename)
        self.assertGreater(self.slots._footer_rename.page, 0)

    def test_no_maya_only_control_is_built(self):
        names = {
            w.objectName()
            for w in self.table.menu.findChildren(self.sb.QtWidgets.QPushButton)
        }
        self.assertIn("ctx_freeze_transforms", names)
        self.assertFalse(
            {"ctx_toggle_keyable", "ctx_hide", "ctx_show", "ctx_lock_and_hide"} & names
        )

    def test_a_scrub_and_a_wheel_notch_step_each_object(self):
        slots = self.slots
        saved = slots.controller
        self.addCleanup(setattr, slots, "controller", saved)
        slots.controller = _FakeEngine({"a": 1.0, "b": 2.0})
        self._one_row()
        col = ChannelsSlots.COL_VALUE
        slots._on_scrub_started(0, col)
        slots._on_scrub_moved(0, col, 10, 0)  # 10px x 0.01
        slots._on_scrub_finished(0, col)
        self.assertEqual(
            {k: round(v, 4) for k, v in slots.controller.vals.items()},
            {"a": 1.1, "b": 2.1},
        )
        slots._on_wheel_scrolled(0, col, 1, Qt.NoModifier)
        self.assertEqual(
            {k: round(v, 4) for k, v in slots.controller.vals.items()},
            {"a": 1.2, "b": 2.2},
        )

    def test_a_rebuilt_instance_takes_over_the_tables_signals(self):
        """Regression (wheel / edits dead after a UI reload): the table
        outlives its slots instance, so tbl000_init re-wires on EVERY init,
        not only the first."""
        self.table.is_initialized = True
        rebuilt = ChannelsSlots(self.sb)
        self.addCleanup(rebuilt.cleanup_scene_callbacks)
        # Drop every binding first, so only tbl000_init's re-wire (not the
        # best-effort pass in __init__) can make the wheel live again.
        try:
            self.table.cellWheelScrolled.disconnect()
        except (RuntimeError, TypeError):
            pass
        rebuilt.tbl000_init(self.table)  # already initialized: must still re-wire
        rebuilt.controller = _FakeEngine({"a": 9.0})
        self._one_row()
        self.table.cellWheelScrolled.emit(0, ChannelsSlots.COL_VALUE, 1, Qt.NoModifier)
        self.app.processEvents()
        self.assertEqual(round(rebuilt.controller.vals["a"], 4), 9.1)


# ---------------------------------------------------------------------------
# Maya: the real mtk
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestChannelsPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")
        prev = self.cmds.undoInfo(q=True, state=True)
        self.cmds.undoInfo(state=True, infinity=True)
        self.addCleanup(self.cmds.undoInfo, state=prev)

    def _real(self, names=()):
        self.modifiers(Qt.NoModifier)
        slots, sb = _panel(tk=self.mtk)
        _rows(sb.loaded_ui.channels.tbl000, list(names), ["unlocked"] * len(names))
        slots._refresh_table = mock.Mock()
        return slots, sb

    def test_maya_offers_every_capability_the_panel_gates(self):
        slots, sb = self._real()
        for name in MAYA_ONLY:
            with self.subTest(name=name):
                self.assertTrue(slots._host_has(name))
        for name, value in HOSTS["maya"].items():
            self.assertTrue(getattr(self.mtk.Channels, name), name)

    def test_one_undo_reverts_a_whole_icon_drag(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="chDragCube")[0]
        cmds.select(cube)
        attrs = ("translateX", "translateY", "translateZ")
        slots, sb = self._real(attrs)
        cmds.flushUndo()
        slots._on_icon_cells_dragged([0, 1, 2], ChannelsSlots.COL_LOCK)
        self.assertEqual(
            [cmds.getAttr(f"{cube}.{a}", lock=True) for a in attrs], [True] * 3
        )
        cmds.undo()
        self.assertEqual(
            [cmds.getAttr(f"{cube}.{a}", lock=True) for a in attrs], [False] * 3
        )

    def test_one_undo_reverts_a_whole_fill(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="chFillCube")[0]
        cmds.select(cube)
        attrs = ("scaleX", "scaleY", "scaleZ")
        slots, sb = self._real(attrs)
        cmds.flushUndo()
        slots._on_edit_batch_started()
        for attr in attrs:  # one cellChanged per cell, as the fill delivers them
            slots.controller.set_attribute_value([cube], attr, "2.5")
        slots._on_edit_batch_finished()
        self.assertEqual([cmds.getAttr(f"{cube}.{a}") for a in attrs], [2.5] * 3)
        cmds.undo()
        self.assertEqual([cmds.getAttr(f"{cube}.{a}") for a in attrs], [1.0] * 3)

    def test_one_undo_reverts_a_wheel_notch_over_two_objects(self):
        cmds = self.cmds
        a = cmds.polyCube(name="chWheelA")[0]
        b = cmds.polyCube(name="chWheelB")[0]
        cmds.setAttr(f"{b}.translateX", 3)
        cmds.select([a, b])
        slots, sb = self._real(("translateX",))
        cmds.flushUndo()
        slots._on_wheel_scrolled(0, ChannelsSlots.COL_VALUE, 2, Qt.NoModifier)
        self.assertAlmostEqual(cmds.getAttr(f"{a}.translateX"), 0.2)
        self.assertAlmostEqual(cmds.getAttr(f"{b}.translateX"), 3.2)
        cmds.undo()
        self.assertAlmostEqual(cmds.getAttr(f"{a}.translateX"), 0.0)
        self.assertAlmostEqual(cmds.getAttr(f"{b}.translateX"), 3.0)

    def test_one_undo_reverts_a_scrub(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="chScrubCube")[0]
        cmds.select(cube)
        slots, sb = self._real(("translateY",))
        cmds.flushUndo()
        col = ChannelsSlots.COL_VALUE
        slots._on_scrub_started(0, col)
        for dx in (40, 80, 100):
            slots._on_scrub_moved(0, col, dx, 0)
        slots._on_scrub_finished(0, col)
        self.assertAlmostEqual(cmds.getAttr(f"{cube}.translateY"), 1.0)
        cmds.undo()
        self.assertAlmostEqual(cmds.getAttr(f"{cube}.translateY"), 0.0)

    def test_a_rename_keeps_the_pin_on_the_renamed_node(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="chPinCube")[0]
        long_name = cmds.ls(cube, long=True)[0]
        slots, sb = self._real()
        slots.controller.pin_targets([long_name])
        slots._current_target = long_name
        slots._rename_target("chPinBox")
        self.assertEqual(slots.controller.get_selected_nodes(), ["|chPinBox"])
        self.assertEqual(slots._current_target, "|chPinBox")


if __name__ == "__main__":
    unittest.main()
