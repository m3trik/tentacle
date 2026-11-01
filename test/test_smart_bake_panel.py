#!/usr/bin/python
# coding=utf-8
"""The Smart Bake panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of its engine: plain pytest, no DCC, no widgets loaded. The ``.ui``
is read as XML for the controls and defaults the panel relies on. In Maya, the
same class drives the real ``mtk.SmartBake`` end to end. The engines' own side
(mayatk's option keywords on Blender's ``SmartBake``, ``BakeResult.describe`` /
``restorable``) is the libraries': ``test_smart_bake.py`` in each.
"""

import os
import types
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.smart_bake import SmartBakeSlots

UI_PATH = os.path.join(os.path.dirname(tentacle.__file__), "ui", "tools", "smart_bake.ui")

#: The panel's defaults, as its .ui and _initialize_ui set them.
DEFAULTS = {
    "cmb_scope": 0,  # Auto (Whole Scene)
    "spn_sample_by": 1,
    "chk_preserve_outside": True,
    "chk_optimize": False,
    "chk_bake_blendshapes": True,
    "cmb_bake_layer": "Override Layer",
    "chk_delete_inputs": False,
    "chk_mute_drivers": False,
    "cmb_backup": 0,  # Auto
}


def _panel(values=None, tk=None):
    """A Slots instance over a mock ui (*values* set on its widgets) and a mock
    toolkit (or *tk*, handed over before the panel is built, as ``Slots.tk``
    is), initialized as the deferred timer would."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.SmartBake.list_sessions.return_value = []
    ui = sb.loaded_ui.smart_bake
    for name, value in {**DEFAULTS, **(values or {})}.items():
        widget = getattr(ui, name)
        widget.value.return_value = value
        widget.isChecked.return_value = value
        widget.currentIndex.return_value = value
        widget.currentText.return_value = value
    slots = SmartBakeSlots(sb)
    slots._initialize_ui()
    return slots, sb, ui


def _result(**fields):
    """A stand-in for a host ``BakeResult``: what the report reads off one."""
    base = dict(
        success=True,
        baked_count=1,
        time_range=(1, 10),
        session_id="s1",
        restorable=True,
        lines=["|cube: tx, ty"],
    )
    base.update(fields)
    lines = base.pop("lines")
    return types.SimpleNamespace(describe=lambda: list(lines), **base)


def _footer(ui):
    """The footer's last message and level."""
    call = ui.footer.setText.call_args
    return call.args[0], call.kwargs.get("level")


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        # The class logger is shared, and the panel redirects it into its
        # output pane: a fake here keeps the run's records (and handlers) off it.
        self.logger = mock.MagicMock()
        patcher = mock.patch.object(SmartBakeSlots, "logger", self.logger)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestSmartBakePanelSetup(_PanelCase):
    def test_setup_streams_the_log_and_waits_for_the_widgets(self):
        sb = mock.MagicMock()
        slots = SmartBakeSlots(sb)
        ui = sb.loaded_ui.smart_bake
        self.logger.set_text_handler.assert_called_once_with(
            sb.registered_widgets.TextEditLogHandler
        )
        self.logger.setup_logging_redirect.assert_called_once_with(
            ui.txt000, level=self.logger.level
        )
        sb.QtCore.QTimer.singleShot.assert_called_once_with(0, slots._initialize_ui)
        ui.cmb_bake_layer.add.assert_not_called()

    def test_the_bake_layer_is_a_named_choice_override_first(self):
        """The combo saves an index: Override Layer stays first (the default)."""
        slots, sb, ui = _panel()
        sb.add_reset_buttons.assert_called_once_with(ui)
        ui.cmb_bake_layer.add.assert_called_once_with(["Override Layer", "Base Layer"])
        ui.cmb_bake_layer.setAsCurrent.assert_called_once_with("Override Layer")
        ui.cmb_bake_layer.currentTextChanged.connect.assert_called_once_with(
            slots._on_bake_layer_changed
        )
        ui.chk_delete_inputs.setDisabled.assert_called_with(True)

    def test_delete_inputs_is_base_layer_only(self):
        slots, sb, ui = _panel()
        slots._on_bake_layer_changed("Base Layer")
        ui.chk_delete_inputs.setDisabled.assert_called_with(False)
        slots._on_bake_layer_changed("Override Layer")
        ui.chk_delete_inputs.setDisabled.assert_called_with(True)

    def test_scope_and_backup_combos_keep_their_order(self):
        slots, sb, ui = _panel()
        scope, backup = mock.MagicMock(), mock.MagicMock()
        slots.cmb_scope_init(scope)
        slots.cmb_backup_init(backup)
        scope.add.assert_called_once_with(["Auto (Whole Scene)", "Selected"])
        backup.add.assert_called_once_with(["Auto", "Always", "Never"])

    def test_the_backup_index_maps_onto_the_engine_value(self):
        # Index is the source of truth: Auto -> None, Always -> True, Never -> False.
        slots, sb, ui = _panel()
        for index, expected in enumerate((None, True, False)):
            ui.cmb_backup.currentIndex.return_value = index
            self.assertIs(slots._backup_value(), expected)

    def test_unbake_follows_the_hosts_pending_sessions(self):
        slots, sb, ui = _panel()
        ui.b001.setEnabled.assert_called_with(False)
        ui.b001.setToolTip.assert_called_with("No bakes pending restore.")
        sb.tk.SmartBake.list_sessions.return_value = ["a", "b"]
        slots._refresh_session_state()
        ui.b001.setEnabled.assert_called_with(True)
        ui.b001.setToolTip.assert_called_with(
            "Restore the most recent of 2 pending bake(s)."
        )

    def test_header_offers_refresh_reset_and_help(self):
        slots, sb, ui = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        header.config_buttons.assert_called_once_with(
            "refresh", "menu", "collapse", "hide"
        )
        header.refresh_requested.connect.assert_called_once_with(
            slots._refresh_session_state
        )
        header.menu.add.assert_called_once_with(
            "QPushButton", setText="Reset to Defaults", setObjectName="reset_defaults"
        )
        # Reset speaks uitk's shared grammar (Shift / Ctrl+Shift+Click).
        sb.ResetGesture.assert_called_once_with(header.menu.add.return_value)
        self.assertEqual(sb.tooltip.fmt.call_args.kwargs["title"], "Smart Bake")


class TestSmartBakePanelBake(_PanelCase):
    def _bake(self, slots, sb, requires_bake=True, result=None):
        baker = sb.tk.SmartBake.return_value
        baker.analyze.return_value = {
            "|cube": types.SimpleNamespace(requires_bake=requires_bake)
        }
        baker.bake.return_value = result if result is not None else _result()
        slots.b000(None)
        return baker

    def test_bake_reads_the_panel_into_the_host_engine(self):
        values = {
            "spn_sample_by": 2,
            "chk_optimize": True,
            "chk_mute_drivers": True,
            "cmb_backup": 2,
        }
        slots, sb, ui = _panel(values)
        baker = self._bake(slots, sb)
        sb.tk.SmartBake.assert_called_once_with(
            objects=None,  # Auto: the whole scene
            sample_by=2,
            preserve_outside_keys=True,
            delete_inputs=False,
            optimize_keys=True,
            bake_blend_shapes=True,
            use_override_layer=True,
            mute_drivers=True,
            backup_file=False,
        )
        baker.bake.assert_called_once_with(baker.analyze.return_value)

    def test_base_layer_and_delete_inputs_reach_the_engine(self):
        slots, sb, ui = _panel(
            {"cmb_bake_layer": "Base Layer", "chk_delete_inputs": True}
        )
        self._bake(slots, sb)
        kwargs = sb.tk.SmartBake.call_args.kwargs
        self.assertIs(kwargs["use_override_layer"], False)
        self.assertIs(kwargs["delete_inputs"], True)

    def test_selected_scope_bakes_the_hosts_selection(self):
        slots, sb, ui = _panel({"cmb_scope": 1})
        sb.tk.CoreUtils.selected_objects.return_value = ["cube"]
        self._bake(slots, sb)
        self.assertEqual(sb.tk.SmartBake.call_args.kwargs["objects"], ["cube"])

    def test_selected_scope_with_nothing_selected_never_bakes_the_scene(self):
        slots, sb, ui = _panel({"cmb_scope": 1})
        sb.tk.CoreUtils.selected_objects.return_value = []
        slots.b000(None)
        sb.tk.SmartBake.assert_not_called()
        self.assertEqual(_footer(ui)[1], "warning")
        self.assertIn("Nothing selected", _footer(ui)[0])

    def test_nothing_driven_is_said_and_nothing_baked(self):
        slots, sb, ui = _panel()
        baker = self._bake(slots, sb, requires_bake=False)
        baker.bake.assert_not_called()
        self.assertIn("Nothing to bake", _footer(ui)[0])

    def test_the_report_is_the_hosts_account_plus_the_session(self):
        slots, sb, ui = _panel()
        self._bake(slots, sb)
        summary = "Baked 1 object(s), range 1-10."
        self.assertEqual(_footer(ui), (summary, "success"))
        self.logger.log_group.assert_called_once_with(
            summary,
            [
                "|cube: tx, ty",
                "Restorable — session 's1'. Click Unbake to reverse.",
            ],
            level="SUCCESS",
        )
        # Unbake is enabled from the host's sessions after every bake.
        self.assertEqual(sb.tk.SmartBake.list_sessions.call_count, 2)

    def test_a_delete_inputs_session_is_not_called_restorable(self):
        slots, sb, ui = _panel()
        self._bake(slots, sb, result=_result(restorable=False))
        details = self.logger.log_group.call_args.args[1]
        self.assertIn("cannot be fully reversed", details[-1])
        self.assertNotIn("Restorable", details[-1])
        self._bake(slots, sb, result=_result(session_id=None))
        self.assertEqual(self.logger.log_group.call_args.args[1][-1], "Not restorable.")

    def test_a_bake_with_no_output_warns(self):
        slots, sb, ui = _panel()
        self._bake(slots, sb, result=_result(success=False))
        self.assertEqual(_footer(ui), ("Bake produced no output.", "warning"))


class TestSmartBakePanelUnbake(_PanelCase):
    def test_unbake_restores_through_the_host(self):
        slots, sb, ui = _panel()
        sb.tk.SmartBake.restore.return_value = types.SimpleNamespace(
            success=True, session_id="s1", warnings=["a driver came back muted"]
        )
        slots.b001(None)
        sb.tk.SmartBake.restore.assert_called_once_with()
        self.assertEqual(_footer(ui), ("Restored session 's1'.", "success"))
        self.logger.log_group.assert_called_once_with(
            "Restored session 's1'.",
            ["a driver came back muted"],
            level="SUCCESS",
            item_color=SmartBakeSlots.LOG_COLORS["WARNING"],
        )

    def test_a_refused_unbake_says_why(self):
        slots, sb, ui = _panel()
        sb.tk.SmartBake.restore.return_value = types.SimpleNamespace(
            success=False, session_id=None, warnings=["destructive session"]
        )
        slots.b001(None)
        self.assertEqual(_footer(ui), ("destructive session", "warning"))
        sb.tk.SmartBake.restore.return_value.warnings = []
        slots.b001(None)
        self.assertEqual(_footer(ui), ("Nothing to restore.", "warning"))


class TestSmartBakePanelUi(unittest.TestCase):
    """The ``.ui``: the controls the panel reads and the defaults it bakes with."""

    @classmethod
    def setUpClass(cls):
        root = ET.parse(UI_PATH).getroot()
        cls.widgets = {w.get("name"): w for w in root.iter("widget")}

    def _prop(self, name, prop):
        return self.widgets[name].find(f"property[@name='{prop}']")

    def test_every_widget_the_panel_uses_exists(self):
        for name in (
            "header", "cmb_scope", "options_group", "spn_sample_by",
            "chk_preserve_outside", "chk_optimize", "chk_bake_blendshapes",
            "safety_group", "cmb_bake_layer", "chk_delete_inputs",
            "chk_mute_drivers", "cmb_backup", "b000", "b001", "output_grp",
            "txt000", "footer",
        ):
            self.assertIn(name, self.widgets, name)

    def test_checkbox_defaults(self):
        for name, checked in (
            ("chk_preserve_outside", True),
            ("chk_bake_blendshapes", True),
            ("chk_optimize", False),
            ("chk_delete_inputs", False),
            ("chk_mute_drivers", False),
        ):
            prop = self._prop(name, "checked")
            value = prop is not None and prop.findtext("bool") == "true"
            self.assertIs(value, checked, name)

    def test_the_bake_layer_is_a_combo(self):
        """A choice between two named layers (was a checkbox): an index persists."""
        self.assertEqual(self.widgets["cmb_bake_layer"].get("class"), "ComboBox")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestSmartBakePanelInMaya(_PanelCase):
    """The panel over the real ``mtk.SmartBake`` and a real scene (the widgets
    stay mocks, set to the options under test)."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)
        self.cmds.playbackOptions(minTime=1, maxTime=10)

    def _constrained_scene(self, prefix="panel"):
        cube = self.cmds.polyCube(name=f"{prefix}_cube")[0]
        loc = self.cmds.spaceLocator(name=f"{prefix}_loc")[0]
        self.cmds.setKeyframe(loc, attribute="translateX", time=1, value=0)
        self.cmds.setKeyframe(loc, attribute="translateX", time=10, value=5)
        constraint = self.cmds.parentConstraint(loc, cube)[0]
        self.cmds.select(cube)
        return cube, constraint

    def test_bake_then_unbake_through_the_panel(self):
        cube, _ = self._constrained_scene()
        slots, sb, ui = _panel(tk=self.mtk)
        slots.b000(None)
        self.assertEqual(_footer(ui)[1], "success")
        self.assertTrue(self.mtk.SmartBake.list_sessions())
        ui.b001.setEnabled.assert_called_with(True)
        details = self.logger.log_group.call_args.args[1]
        self.assertTrue(details[-1].startswith("Restorable"), details)
        self.cmds.currentTime(10)
        self.assertAlmostEqual(self.cmds.getAttr(f"{cube}.tx"), 5.0, places=3)

        slots.b001(None)
        self.assertEqual(_footer(ui)[1], "success")
        self.assertIn("Restored", _footer(ui)[0])
        ui.b001.setEnabled.assert_called_with(False)

    def test_nothing_driven_warns_and_records_no_session(self):
        self.cmds.select(self.cmds.polyCube(name="plain_cube")[0])
        slots, sb, ui = _panel(tk=self.mtk)
        slots.b000(None)
        self.assertEqual(_footer(ui)[1], "warning")
        self.assertIn("Nothing to bake", _footer(ui)[0])
        self.assertEqual(self.mtk.SmartBake.list_sessions(), [])

    def test_selected_scope_with_nothing_selected_bakes_nothing(self):
        self._constrained_scene(prefix="unselected")
        self.cmds.select(clear=True)
        slots, sb, ui = _panel({"cmb_scope": 1}, tk=self.mtk)
        slots.b000(None)
        self.assertIn("Nothing selected", _footer(ui)[0])
        self.assertEqual(self.mtk.SmartBake.list_sessions(), [])

    def test_a_delete_inputs_bake_is_destructive_and_says_so(self):
        _, constraint = self._constrained_scene(prefix="destructive")
        slots, sb, ui = _panel(
            {
                "cmb_bake_layer": "Base Layer",
                "chk_delete_inputs": True,
                "cmb_backup": 2,  # Never: keep the test off the disk
            },
            tk=self.mtk,
        )
        slots.b000(None)
        self.assertEqual(_footer(ui)[1], "success")
        self.assertFalse(self.cmds.objExists(constraint))  # deleted, not muted
        details = self.logger.log_group.call_args.args[1]
        self.assertIn("cannot be fully reversed", details[-1])
        # The non-restorable session stays clickable: the click says so and
        # pops the dead entry.
        ui.b001.setEnabled.assert_called_with(True)
        slots.b001(None)
        self.assertEqual(_footer(ui)[1], "warning")
        self.assertIn("destructive", _footer(ui)[0])
        ui.b001.setEnabled.assert_called_with(False)


if __name__ == "__main__":
    unittest.main()
