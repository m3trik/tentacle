#!/usr/bin/python
# coding=utf-8
"""The Tube Rig panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``. The selection API it calls (``TubeRig.MODES``,
``selected_tubes``, ``for_build``, ``undo_step``, ``create_joints`` and the
``*_from_selection`` steps) is the libraries': mayatk's ``test_tube_rig.py``
(``TestPanelSelectionApi``), blendertk's ``test_tube_rig.py``.
"""

import contextlib
import os
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest import mock

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.tube_rig import TubeRigSlots

UI_FILE = os.path.join(os.path.dirname(tentacle.__file__), "ui", "tools", "tube_rig.ui")


def _mode(name, strategy, **overrides):
    """A ``TubeRig.MODES`` entry (the libraries' ``RigModeConfig``)."""
    values = dict(
        name=name,
        strategy=strategy,
        num_joints=-1,
        num_controls=3,
        enable_stretch=True,
        enable_squash=True,
        enable_volume=True,
        enable_auto_bend=True,
        enable_twist=True,
        num_joints_editable=True,
        num_controls_editable=True,
        stretch_editable=True,
        squash_editable=True,
        volume_editable=True,
        auto_bend_editable=True,
        twist_editable=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


_OFF = dict.fromkeys(
    ("enable_squash", "enable_volume", "enable_auto_bend", "enable_twist"), False
)
_LOCKED = dict.fromkeys(
    ("squash_editable", "volume_editable", "auto_bend_editable", "twist_editable"),
    False,
)
MODES = [
    _mode("Spline (Hose/Cable)", "spline"),
    _mode(
        "Anchor (Piston/Hydraulic)",
        "anchor",
        num_joints=2,
        num_controls=2,
        num_joints_editable=False,
        num_controls_editable=False,
        **_OFF,
        **_LOCKED,
    ),
    _mode(
        "FK Chain (Tail/Tentacle)",
        "fk",
        num_controls=5,
        enable_stretch=False,
        stretch_editable=False,
        **_OFF,
        **_LOCKED,
    ),
]

#: The Step 2 page's toggles, and the engine keywords they become.
TOGGLES = {
    "chk_stretch": ("enable_stretch", True),
    "chk_squash": ("enable_squash", False),
    "chk_volume": ("enable_volume", False),
    "chk_twist": ("enable_twist", True),
    "chk_auto_bend": ("enable_auto_bend", False),
}
DEFORM = {key: value for key, value in TOGGLES.values()}


def _panel(mode=0, joints=-1, controls=3, size=-1.0, name="", reverse=False, tk=None):
    """A Slots instance over a mock ui (the given page values) and a mock
    toolkit, or *tk* (handed over before the panel is built, as ``Slots.tk``
    is). The footer's ``update`` is ``sb.footer_update``: it answers True (go
    on) unless a test gives it a ``side_effect``."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.TubeRig.MODES = MODES
        sb.tk.TubeRig.undo_step.side_effect = lambda name: contextlib.nullcontext()
        sb.tk.TubeRig.selected_edges.return_value = None
        sb.tk.TubeRig.for_build.return_value.rig_name = "tube_RIG"
    ui = sb.loaded_ui.tube_rig
    ui.cmb_preset.currentIndex.return_value = mode
    ui.s000.value.return_value = joints
    ui.s001.value.return_value = controls
    ui.s002.value.return_value = size
    ui.txt000.text.return_value = name
    ui.chk000.isChecked.return_value = reverse
    for box, (_, value) in TOGGLES.items():
        getattr(ui, box).isChecked.return_value = value
    sb.footer_update = mock.MagicMock(return_value=True)
    ui.footer.progress.return_value.__enter__.return_value = sb.footer_update
    return TubeRigSlots(sb), sb


def _rigs(*names):
    """Mock rigs keyed by tube: ``for_build(tube)`` hands back ``<tube>_RIG``."""
    return {n: mock.MagicMock(rig_name=f"{n}_RIG") for n in names}


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

    def message(self, sb):
        sb.message_box.assert_called_once()
        return sb.message_box.call_args.args[0]


class TestTubeRigModes(_PanelCase):
    def test_the_mode_combo_lists_the_hosts_modes_in_order(self):
        """The combo saves an index: its order is the library's table."""
        slots, sb = _panel()
        ui = sb.loaded_ui.tube_rig
        self.assertEqual(
            ui.cmb_preset.addItem.call_args_list,
            [mock.call(m.name, m.strategy) for m in MODES],
        )
        self.assertEqual(slots.get_strategy(), "spline")

    def test_auto_values_display_as_auto(self):
        _, sb = _panel()
        ui = sb.loaded_ui.tube_rig
        ui.s000.setCustomDisplayValues.assert_called_once_with(-1, "Auto")
        ui.s002.setCustomDisplayValues.assert_called_once_with(-1, "Auto")

    def test_a_mode_presets_and_gates_its_options(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.tube_rig
        slots.apply_mode(1)  # Anchor
        ui.s000.setValue.assert_called_with(2)
        ui.s000.setEnabled.assert_called_with(False)
        ui.s001.setEnabled.assert_called_with(False)
        ui.chk_stretch.setEnabled.assert_called_with(True)
        for box in ("chk_squash", "chk_volume", "chk_twist"):
            getattr(ui, box).setChecked.assert_called_with(False)
            getattr(ui, box).setEnabled.assert_called_with(False)

    def test_auto_bend_needs_the_three_control_spline(self):
        slots, sb = _panel(controls=4)
        ui = sb.loaded_ui.tube_rig
        ui.chk_auto_bend.reset_mock()
        slots._sync_auto_bend_gate()
        ui.chk_auto_bend.setEnabled.assert_called_once_with(False)
        ui.chk_auto_bend.setChecked.assert_called_once_with(False)

        ui.s001.value.return_value = 3
        ui.chk_auto_bend.reset_mock()
        slots._sync_auto_bend_gate()
        ui.chk_auto_bend.setEnabled.assert_called_once_with(True)
        ui.chk_auto_bend.setChecked.assert_not_called()

    def test_an_unset_combo_reads_the_first_mode(self):
        slots, _ = _panel(mode=-1)
        self.assertEqual(slots.get_strategy(), "spline")


class TestTubeRigReverseIsGlobal(unittest.TestCase):
    """Reverse Direction belongs to EVERY build, One-Click included.

    Regression: the toggle lived on the Step 1 page while the panel opens on
    One-Click, so a user building in one click never saw it and could not root
    a plug at the end it unplugs from.
    """

    def test_reverse_sits_outside_the_step_pages(self):
        root = ET.parse(UI_FILE).getroot()
        toolbox = root.find(".//widget[@name='toolbox_steps']")
        self.assertIsNotNone(root.find(".//widget[@name='chk000']"))
        self.assertIsNone(toolbox.find(".//widget[@name='chk000']"))
        macro = toolbox.find("widget[@name='page_macro']")
        self.assertIsNotNone(macro.find(".//widget[@name='b000']"))


class TestTubeRigOneClick(_PanelCase):
    def _run(self, tubes=("hoseA", "hoseB"), **values):
        slots, sb = _panel(**values)
        rigs = _rigs(*tubes)
        sb.tk.TubeRig.selected_tubes.return_value = list(tubes)
        sb.tk.TubeRig.for_build.side_effect = lambda tube, rig_name=None: rigs[tube]
        slots.b000()
        return sb, rigs

    def test_each_tube_builds_with_the_page_values_in_one_undo_step(self):
        sb, rigs = self._run(joints=12, controls=4, size=0.5, reverse=True)
        sb.tk.TubeRig.undo_step.assert_called_once_with("Tube Rig: Full Rig")
        for tube, rig in rigs.items():
            sb.tk.TubeRig.for_build.assert_any_call(tube, rig_name=None)
            rig.build.assert_called_once_with(
                strategy="spline",
                progress=mock.ANY,
                num_joints=12,
                num_controls=4,
                radius=0.5,
                reverse=True,
                edges=None,
                **DEFORM,
            )
        self.assertEqual(
            self.message(sb), "Tube rig (spline) created: hoseA_RIG, hoseB_RIG"
        )

    def test_the_selected_edges_reach_the_build(self):
        slots, sb = _panel()
        sb.tk.TubeRig.selected_tubes.return_value = ["hose"]
        sb.tk.TubeRig.selected_edges.return_value = ["hose.e[1]", "hose.e[2]"]
        slots.b000()
        build = sb.tk.TubeRig.for_build.return_value.build
        self.assertEqual(build.call_args.kwargs["edges"], ["hose.e[1]", "hose.e[2]"])

    def test_a_typed_name_is_suffixed_per_tube_in_a_batch(self):
        sb, _ = self._run(name="hose")
        self.assertEqual(
            [c.kwargs["rig_name"] for c in sb.tk.TubeRig.for_build.call_args_list],
            ["hose_01", "hose_02"],
        )
        sb, _ = self._run(tubes=("only",), name="hose")
        sb.tk.TubeRig.for_build.assert_called_once_with("only", rig_name="hose")

    def test_each_tube_is_announced_and_its_phases_carry_the_counter(self):
        """The viewport shows nothing while a rig builds: the footer is the
        only sign of life, and the engine cannot know the batch counter."""
        sb, rigs = self._run()
        self.assertEqual(
            sb.footer_update.call_args_list,
            [
                mock.call(None, "[1/2] Rigging hoseA…"),
                mock.call(None, "[2/2] Rigging hoseB…"),
            ],
        )
        hook = rigs["hoseB"].build.call_args.kwargs["progress"]
        hook(None, 0, "binding skin…")
        sb.progress_adapter.return_value.assert_called_with(
            None, 0, "[2/2] binding skin…"
        )

    def test_a_single_tube_has_no_counter(self):
        sb, rigs = self._run(tubes=("hose",))
        sb.footer_update.assert_called_once_with(None, "Rigging hose…")
        self.assertIs(
            rigs["hose"].build.call_args.kwargs["progress"],
            sb.progress_adapter.return_value,
        )

    def test_a_failing_tube_is_reported_and_the_batch_goes_on(self):
        slots, sb = _panel()
        rigs = _rigs("hoseA", "hoseB")
        rigs["hoseA"].build.side_effect = ValueError("not a polygon mesh")
        sb.tk.TubeRig.selected_tubes.return_value = ["hoseA", "hoseB"]
        sb.tk.TubeRig.for_build.side_effect = lambda tube, rig_name=None: rigs[tube]
        slots.b000()
        rigs["hoseB"].build.assert_called_once()
        self.assertEqual(
            self.message(sb),
            "Tube rig (spline) created: hoseB_RIG\n"
            "Failed:\n  hoseA: not a polygon mesh",
        )

    def test_a_cancel_stops_before_the_next_tube_and_says_undo_is_one_step(self):
        slots, sb = _panel()
        rigs = _rigs("hoseA", "hoseB")
        sb.tk.TubeRig.selected_tubes.return_value = ["hoseA", "hoseB"]
        sb.tk.TubeRig.for_build.side_effect = lambda tube, rig_name=None: rigs[tube]
        sb.footer_update.side_effect = [True, False]  # Esc during the first tube
        slots.b000()
        rigs["hoseA"].build.assert_called_once()
        rigs["hoseB"].build.assert_not_called()
        text = self.message(sb)
        self.assertIn("created: hoseA_RIG", text)
        self.assertIn("Cancelled with 1 left", text)
        self.assertIn("one step", text)

    def test_nothing_selected_is_refused_before_any_undo_step(self):
        slots, sb = _panel()
        sb.tk.TubeRig.selected_tubes.return_value = []
        slots.b000()
        sb.tk.TubeRig.undo_step.assert_not_called()
        self.assertIn("Select one or more", self.message(sb))

    def test_the_mode_names_the_strategy(self):
        slots, sb = _panel(mode=2)
        sb.tk.TubeRig.selected_tubes.return_value = ["tail"]
        slots.b000()
        build = sb.tk.TubeRig.for_build.return_value.build
        self.assertEqual(build.call_args.kwargs["strategy"], "fk")


class TestTubeRigSteps(_PanelCase):
    def test_step1_creates_joints_on_each_tube_in_the_mode(self):
        slots, sb = _panel(mode=1, joints=2, size=0.25, reverse=True)
        sb.tk.TubeRig.selected_tubes.return_value = ["piston"]
        engine = sb.tk.TubeRig.for_build.return_value
        engine.create_joints.return_value = ["piston_start_jnt", "piston_end_jnt"]
        slots.b001()
        sb.tk.TubeRig.undo_step.assert_called_once_with("Tube Rig: Create Joints")
        engine.create_joints.assert_called_once_with(
            "anchor", num_joints=2, radius=0.25, reverse=True, edges=None
        )
        self.assertEqual(self.message(sb), "Joints created: 2")

    def test_step1_batch_names_each_tubes_count(self):
        slots, sb = _panel()
        sb.tk.TubeRig.selected_tubes.return_value = ["hoseA", "hoseB"]
        sb.tk.TubeRig.for_build.return_value.create_joints.side_effect = [
            ["j1", "j2", "j3"],
            ValueError("Failed to extract a valid centerline from the tube mesh."),
        ]
        slots.b001()
        self.assertEqual(
            self.message(sb),
            "Joints created: 3 (hoseA)\nFailed:\n  hoseB: Failed to extract a "
            "valid centerline from the tube mesh.",
        )

    def test_step1_cancelled_before_the_first_tube_still_says_so(self):
        slots, sb = _panel()
        sb.tk.TubeRig.selected_tubes.return_value = ["hose"]
        sb.footer_update.return_value = False
        slots.b001()
        self.assertIn("No joints created.", self.message(sb))

    def test_step2_hands_the_mode_and_toggles_to_the_host(self):
        slots, sb = _panel(controls=3, name="hose")
        sb.tk.TubeRig.create_controls_from_selection.return_value = (
            "Spline IK",
            ["j1", "j2", "j3", "j4"],
            ["hose_start_CTRL", "hose_mid_CTRL", "hose_end_CTRL"],
        )
        slots.b002()
        sb.tk.TubeRig.create_controls_from_selection.assert_called_once_with(
            "spline", num_controls=3, rig_name="hose", **DEFORM
        )
        self.assertEqual(
            self.message(sb),
            "Spline IK controls created on 4 joints.\n"
            "Controls: hose_start_CTRL, hose_mid_CTRL, hose_end_CTRL",
        )

    def test_step2_refusal_reaches_the_message_box(self):
        slots, sb = _panel()
        sb.tk.TubeRig.create_controls_from_selection.side_effect = ValueError(
            "Select the root joint created in Step 1."
        )
        slots.b002()
        self.assertEqual(self.message(sb), "Select the root joint created in Step 1.")

    def test_step3_reports_the_bind(self):
        slots, sb = _panel(mode=2)
        sb.tk.TubeRig.bind_from_selection.return_value = ("hose", 6, "hose_skinCluster")
        slots.b003()
        sb.tk.TubeRig.bind_from_selection.assert_called_once_with("fk", rig_name=None)
        self.assertEqual(
            self.message(sb), "Skinned 'hose' to 6 joints (hose_skinCluster)."
        )

    def test_step3_refusals_reach_the_message_box(self):
        for error in (ValueError("select the mesh last"), RuntimeError("bind failed")):
            with self.subTest(error=type(error).__name__):
                slots, sb = _panel()
                sb.tk.TubeRig.bind_from_selection.side_effect = error
                slots.b003()
                self.assertEqual(self.message(sb), str(error))

    def test_end_constraints_report_each_end(self):
        slots, sb = _panel()
        sb.tk.TubeRig.constrain_ends_from_selection.return_value = [
            ("start", "plugA", "hose_anchor_start_jnt"),
            ("end", "plugB", None),
        ]
        slots.b004()
        call = sb.tk.TubeRig.constrain_ends_from_selection.call_args
        self.assertEqual(call.args, ("spline",))
        self.assertIs(call.kwargs["progress"], sb.progress_adapter.return_value)
        self.assertEqual(
            self.message(sb),
            "End constraints added:\n"
            "  start <- plugA: hose_anchor_start_jnt\n"
            "  end <- plugB: failed",
        )

    def test_end_constraints_refusal_reaches_the_message_box(self):
        slots, sb = _panel()
        sb.tk.TubeRig.constrain_ends_from_selection.side_effect = ValueError(
            "Both anchors sit nearest the tube's start end"
        )
        slots.b004()
        self.assertIn("Both anchors", self.message(sb))


class TestTubeRigUtility(_PanelCase):
    @staticmethod
    def _blender_like():
        """A toolkit whose TubeRig has no rig registry yet: no teardown,
        rename or rebind (blendertk today)."""
        tk = mock.MagicMock()
        tk.TubeRig.MODES = MODES
        for name in ("teardown", "rename", "rebind_skin"):
            delattr(tk.TubeRig, name)
        return tk

    @staticmethod
    def _hidden(sb, widget) -> bool:
        """Whether the panel hid *widget* as one this host cannot serve
        (``Slots.hide_unless``), never leaving it showing disabled."""
        hidden = mock.call(widget, False) in (
            sb.FieldVisibility.set_widget_visible.call_args_list
        )
        if hidden:
            assert widget.hidden_by_policy == "requires", widget
            widget.setEnabled.assert_not_called()
        return hidden

    def test_a_host_without_the_operation_hides_its_button(self):
        _, sb = _panel(tk=self._blender_like())
        ui = sb.loaded_ui.tube_rig
        for button in ("b005", "b006", "b007"):
            self.assertTrue(self._hidden(sb, getattr(ui, button)), button)

    def test_a_host_with_them_keeps_them_shown(self):
        _, sb = _panel()
        ui = sb.loaded_ui.tube_rig
        for button in ("b005", "b006", "b007"):
            self.assertFalse(self._hidden(sb, getattr(ui, button)), button)

    def test_remove_tears_down_each_selected_rig_in_one_undo_step(self):
        slots, sb = _panel()
        rigs = [mock.MagicMock(rig_name="r1"), mock.MagicMock(rig_name="r2")]
        sb.tk.TubeRig.selected_rigs.return_value = rigs
        slots.b005()
        sb.tk.TubeRig.undo_step.assert_called_once_with("Tube Rig: Remove")
        for rig in rigs:
            rig.teardown.assert_called_once_with(progress=mock.ANY)
        self.assertEqual(self.message(sb), "Rig removed: r1, r2")

    def test_remove_with_no_rig_says_what_to_select(self):
        slots, sb = _panel()
        sb.tk.TubeRig.selected_rigs.return_value = []
        slots.b005()
        sb.tk.TubeRig.undo_step.assert_not_called()
        self.assertIn("Select the tube mesh", self.message(sb))

    def test_rename_needs_a_name_and_one_rig(self):
        slots, sb = _panel(name="")
        slots.b006()
        self.assertIn("Type the new name", self.message(sb))

        slots, sb = _panel(name="pipe")
        sb.tk.TubeRig.selected_rigs.return_value = [mock.MagicMock(), mock.MagicMock()]
        slots.b006()
        self.assertEqual(self.message(sb), "Select one rig at a time (got 2).")

        slots, sb = _panel(name="pipe")
        rig = mock.MagicMock(rig_name="hose")
        rig.rename.return_value = "pipe"
        sb.tk.TubeRig.selected_rigs.return_value = [rig]
        slots.b006()
        rig.rename.assert_called_once_with("pipe")
        self.assertEqual(self.message(sb), "Rig renamed: hose -> pipe")

    def test_rebind_pairs_the_mesh_the_host_resolves(self):
        slots, sb = _panel()
        rig = mock.MagicMock(rig_name="hose")
        sb.tk.TubeRig.selected_rebind_targets.return_value = ([rig], "|grp|hose")
        slots.b007()
        sb.tk.TubeRig.undo_step.assert_called_once_with("Tube Rig: Rebind Skin")
        rig.rebind_skin.assert_called_once_with(mesh="|grp|hose")
        self.assertEqual(self.message(sb), "Skin rebound: hose")

    def test_rebind_refusal_reaches_the_message_box(self):
        slots, sb = _panel()
        sb.tk.TubeRig.selected_rebind_targets.side_effect = ValueError(
            "Can't tell which mesh belongs to which rig"
        )
        slots.b007()
        self.assertIn("Can't tell", self.message(sb))


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestTubeRigPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")

    def _real(self, strategy, **values):
        index = [m.strategy for m in self.mtk.TubeRig.MODES].index(strategy)
        return _panel(mode=index, tk=self.mtk, **values)

    def _cable(self):
        """An 8-unit capped cable standing on the origin, root-agnostic."""
        cmds = self.cmds
        tube = cmds.polyCylinder(r=0.2, h=8.0, sy=6, sx=6, name="panelCable")[0]
        cmds.move(0, 4.0, 0, tube)
        cmds.makeIdentity(tube, apply=True, t=1, r=1, s=1, n=0, pn=1)
        return tube

    def test_one_click_roots_the_chain_at_the_reversed_end(self):
        """Reverse Direction reaches the One-Click build (it once read on the
        Step 1 page only)."""
        cmds = self.cmds
        om = maya_module("maya.api.OpenMaya")
        roots = []
        for reverse in (False, True):
            cmds.file(new=True, force=True)
            tube = self._cable()
            cmds.select(tube)
            slots, sb = self._real("fk", controls=3, reverse=reverse)
            slots.b000()
            self.assertIn("created", self.message(sb))
            rig = self.mtk.TubeRig.for_node(tube)
            self.assertIsNotNone(rig)
            roots.append(
                om.MVector(*cmds.xform(rig.joints[0], q=True, ws=True, t=True))
            )
        self.assertGreater((roots[0] - roots[1]).length(), 7.0)

    def test_the_steps_build_and_bind_a_rig(self):
        cmds = self.cmds
        tube = self._cable()
        cmds.select(tube)
        slots, sb = self._real("spline", joints=6, controls=3)
        slots.b001()
        self.assertIn("Joints created", sb.message_box.call_args.args[0])
        rig = self.mtk.TubeRig.for_node(tube)
        root = f"{rig.rig_name}_jnt_1"

        cmds.select(root)
        slots.b002()
        self.assertIn("Spline IK controls created", sb.message_box.call_args.args[0])

        cmds.select(root, tube)
        slots.b003()
        self.assertIn("Skinned", sb.message_box.call_args.args[0])
        self.assertTrue(cmds.ls(cmds.listHistory(tube) or [], type="skinCluster"))

        cmds.select(tube)  # any part of the rig: Remove takes it all back
        slots.b005()
        self.assertIn("Rig removed", sb.message_box.call_args.args[0])
        self.assertFalse(cmds.ls(cmds.listHistory(tube) or [], type="skinCluster"))


if __name__ == "__main__":
    unittest.main()
