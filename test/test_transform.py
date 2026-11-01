#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.transform, the one Transform Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- tb002 (Freeze Transforms): the combo index -> strategy mapping
  (connection 0="preserve", 1="disconnect", 2="delete"; instance 0="skip",
  1="preserve", 2="uninstance"). Index drift silently switches strategies.
  Store is never disabled: the bake history it stamps is what Un-Freeze reads.
- tb005 (Move To) / b001 (Match Scale): one library call on the selection,
  and the "needs two" message when it answers ``[]``.
- Snap / Constrain toggles apply live, and their boxes mirror the host's state
  without persisting it. Tb003 / tb004 label themselves through ``sb.text_from``
  on the OPTION BOX menu.
The operations themselves are tested in mayatk and blendertk.
"""
import ast
import unittest
from pathlib import Path
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.transform import TransformSlots

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tentacle" / "slots" / "transform.py"


class _FakeCheckBox:
    """Minimal QCheckBox stand-in: records whether the seed ran signal-blocked."""

    def __init__(self, name):
        self._name = name
        self._checked = None
        self._blocked = False
        self.blocked_during_seed = False
        self.restore_state = True

    def objectName(self):
        return self._name

    def blockSignals(self, block):
        was, self._blocked = self._blocked, block
        return was

    def setChecked(self, state):
        self._checked = state
        self.blocked_during_seed = self._blocked

    def setValue(self, value):
        self.setChecked(value)

    def isChecked(self):
        return self._checked


def _widget(**values):
    """A widget whose option-box menu holds fakes reading *values*."""
    widget = mock.MagicMock()
    for name, value in values.items():
        child = getattr(widget.option_box.menu, name)
        child.value.return_value = value
        child.isChecked.return_value = value
        child.currentIndex.return_value = value
        child.currentData.return_value = value
        child.currentText.return_value = value
    return widget


FREEZE = dict(
    chk032=True,
    chk033=False,
    chk034=True,
    chk038=False,
    chk039=False,
    chk040=False,
    chk_restore_rig_anchors=True,
    cmb_center_pivot=0,
    cmb_connection_strategy=0,
    cmb_instance_strategy=1,
)


class TestSourcePins(unittest.TestCase):
    """DCC-free source pins, because the failures they guard raise nothing.

    tb003 (Constrain) / tb004 (Snap) rename themselves from their own checkboxes.
    Both forks used to hand-wire this off ``widget.menu`` while the checkboxes
    live on ``widget.option_box.menu`` -- two different Menus by design -- so the
    wiring bound nothing. Both are ``sb.text_from`` rules on the option-box menu
    now; the rule's own behaviour is uitk's (``test_switchboard_toggle``).
    """

    @staticmethod
    def _flat():
        flat = " ".join(SOURCE.read_text(encoding="utf-8").split())
        return flat.replace("( ", "(").replace(" )", ")")

    def test_both_self_labellers_are_rules(self):
        self.assertEqual(self._flat().count("text_from("), 2)

    def test_no_label_is_hand_wired_off_the_context_menu(self):
        flat = self._flat()
        for call in ("connect_multi(widget.menu", "text_from(widget.menu"):
            self.assertNotIn(call, flat)

    def test_no_constraint_or_snap_box_is_seeded_from_a_literal(self):
        """The labels derive from these boxes, so a literal seed makes them lie
        about the scene ("Constrain: ON" on a fresh scene, the 2026-08-22 bug)."""
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        inits = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name in ("tb003_init", "tb004_init")
        }
        self.assertEqual(set(inits), {"tb003_init", "tb004_init"})
        for name, node in inits.items():
            for call in ast.walk(node):
                for kw in getattr(call, "keywords", ()):
                    if kw.arg == "setChecked":
                        with self.subTest(init=name):
                            self.assertNotIsInstance(kw.value, ast.Constant)


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = TransformSlots(self.sb)
        self.xf = self.sb.tk.XformUtils
        self.sb.tk.CoreUtils.selected_objects.return_value = ["pCube1"]

    def message(self):
        return self.sb.message_box.call_args.args[0]


class TestTb002Freeze(_SlotsCase):
    def _freeze(self, **overrides):
        self.slots.tb002(_widget(**dict(FREEZE, **overrides)))
        return self.sb.tk.RigUtils.freeze_and_reanchor.call_args

    def test_widget_values_reach_the_library(self):
        call = self._freeze()
        self.assertEqual(call.args, (["pCube1"],))
        self.assertEqual(
            call.kwargs,
            dict(
                center_pivot=0,
                translate=True,
                rotate=False,
                scale=True,
                force=True,  # one object: its locked channels unlock
                delete_history=False,
                freeze_children=False,
                connection_strategy="preserve",
                instance_strategy="preserve",
                from_channel_box=False,
                reanchor=True,
            ),
        )

    def test_connection_strategy_by_index(self):
        for index, expected in enumerate(("preserve", "disconnect", "delete")):
            with self.subTest(index=index):
                call = self._freeze(cmb_connection_strategy=index)
                self.assertEqual(call.kwargs["connection_strategy"], expected)

    def test_instance_strategy_by_index(self):
        for index, expected in enumerate(("skip", "preserve", "uninstance")):
            with self.subTest(index=index):
                call = self._freeze(cmb_instance_strategy=index)
                self.assertEqual(call.kwargs["instance_strategy"], expected)

    def test_store_is_never_disabled(self):
        self.assertNotIn("store", self._freeze().kwargs)

    def test_force_only_for_a_single_object(self):
        self.sb.tk.CoreUtils.selected_objects.return_value = ["a", "b"]
        self.assertFalse(self._freeze().kwargs["force"])

    def test_no_selection_warns(self):
        self.sb.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb002(_widget(**FREEZE))
        self.sb.tk.RigUtils.freeze_and_reanchor.assert_not_called()
        self.assertIn("requires a selection", self.message())


class TestB002UnFreeze(_SlotsCase):
    def test_channels_and_children(self):
        self.slots.b002(
            _widget(
                chk_unfreeze_t=True,
                chk_unfreeze_r=False,
                chk_unfreeze_s=True,
                chk_unfreeze_children=True,
            )
        )
        self.xf.restore_transforms.assert_called_once_with(
            ["pCube1"], channels=["translate", "scale"], traverse=True
        )

    def test_no_channel_and_nothing_restored_are_said(self):
        self.slots.b002(
            _widget(chk_unfreeze_t=False, chk_unfreeze_r=False, chk_unfreeze_s=False)
        )
        self.assertIn("at least one channel", self.message())
        self.xf.restore_transforms.return_value = []
        self.slots.b002(_widget(chk_unfreeze_t=True, chk_unfreeze_children=False))
        self.assertIn("Nothing to restore", self.message())

    def test_restore_axes_names_the_object(self):
        self.xf.restore_original_axes.return_value = "|grp|cube"
        self.sb.tk.CoreUtils.leaf_name.return_value = "cube"
        self.slots.b_restore_axes()
        self.assertIn("<hl>cube</hl>", self.message())
        self.xf.restore_original_axes.return_value = None
        self.slots.b_restore_axes()
        self.assertIn("Nothing to restore", self.message())


class TestMoveAndScale(_SlotsCase):
    def test_move_to_reads_its_options(self):
        self.slots.tb005(_widget(cmb005="xmax", chk036=False, chk_match_scale=True))
        self.xf.move_to_target.assert_called_once_with(
            None, pivot="xmax", all_to_last=False, match_scale=True
        )

    def test_move_to_with_too_few_says_so(self):
        self.xf.move_to_target.return_value = []
        self.slots.tb005(_widget(cmb005="center", chk036=True, chk_match_scale=False))
        self.assertIn("two or more", self.message())

    def test_match_scale_is_the_selections(self):
        self.xf.match_scale.return_value = [1.0, 1.0, 1.0]
        self.slots.b001()
        self.xf.match_scale.assert_called_once_with(None, None)
        self.sb.message_box.assert_not_called()
        self.xf.match_scale.return_value = []
        self.slots.b001()
        self.assertIn("two or more", self.message())

    def test_drop_to_grid_reads_its_options(self):
        self.xf.drop_to_grid.return_value = []
        self.slots.tb000(_widget(cmb004="Min", chk014=True, chk016=False, chk017=True))
        self.xf.drop_to_grid.assert_called_once_with(
            None, align="Min", origin=True, center_pivot=False, freeze_transforms=True
        )
        self.assertIn("requires a selection", self.message())

    def test_scale_connected_edges(self):
        self.xf.scale_connected_edges.return_value = 0
        self.slots.tb001(_widget(s001=1.5))
        self.xf.scale_connected_edges.assert_called_once_with(None, scale_factor=1.5)
        self.assertIn("No connected edges", self.message())


class TestAlignTo(_SlotsCase):
    def test_modes_are_the_hosts(self):
        self.xf.ALIGN_MODES = {"Align X to Active": ("X",), "Align Y to Active": ("Y",)}
        widget = mock.MagicMock()
        self.slots.cmb002_init(widget)
        widget.add.assert_called_once_with(
            ["Align X to Active", "Align Y to Active"], header="Align To"
        )

    def test_the_chosen_mode_runs_and_a_refusal_is_said(self):
        widget = mock.Mock(items=["Point to Point", "Align Objects"])
        self.slots.cmb002(1, widget)
        self.xf.align_to.assert_called_once_with("Align Objects")
        self.xf.align_to.side_effect = ValueError("Align needs two or more")
        self.slots.cmb002(0, widget)
        self.assertIn("two or more", self.message())


class TestSnapAndConstraints(_SlotsCase):
    def test_each_snap_box_sets_its_kind_and_gates_its_increment(self):
        menu = self.slots.ui.tb004.option_box.menu
        for name, kind, spin in (
            ("chk021", "move", "s021"),
            ("chk022", "scale", "s022"),
            ("chk023", "rotate", "s023"),
        ):
            with self.subTest(box=name):
                getattr(self.slots, name)(True, None)
                self.xf.set_transform_snap.assert_called_with(kind, True)
                getattr(menu, spin).setEnabled.assert_called_with(True)

    def test_increments(self):
        self.slots.s021(5.0, None)
        self.xf.set_transform_snap.assert_called_with("move", increment=5.0)
        self.slots.s023(15.0, None)
        self.xf.set_transform_snap.assert_called_with("rotate", increment=15.0)

    def test_each_constraint_box_sets_its_kind(self):
        for name, kind in (("chk024", "edge"), ("chk025", "surface"), ("chk026", "live")):
            with self.subTest(box=name):
                getattr(self.slots, name)(False, None)
                self.xf.set_transform_constraint.assert_called_with(kind, False)

    def test_boxes_mirror_the_host_and_never_persist(self):
        self.xf.get_transform_snap.return_value = {
            "move": {"enabled": False, "increment": None},
            "scale": {"enabled": False, "increment": None},
            "rotate": {"enabled": True, "increment": 15.0},
        }
        self.xf.get_transform_constraint.return_value = {
            "edge": False,
            "surface": True,
            "live": False,
        }
        for name, expect in (
            ("chk023", True),
            ("chk021", False),
            ("s023", 15.0),
            ("chk025", True),
            ("chk024", False),
        ):
            with self.subTest(widget=name):
                box = _FakeCheckBox(name)
                getattr(self.slots, f"{name}_init")(box)
                self.assertEqual(box.isChecked(), expect)
                self.assertTrue(box.blocked_during_seed)
                self.assertFalse(box.restore_state)
        box = _FakeCheckBox("s021")  # no move increment in this host: no seed
        self.slots.s021_init(box)
        self.assertIsNone(box.isChecked())
        self.assertFalse(box.restore_state)

    def test_snap_option_box_hides_the_increments_a_host_lacks(self):
        self.xf.get_transform_snap.return_value = {
            kind: {"enabled": False, "increment": None if kind != "rotate" else 5.0}
            for kind in ("move", "scale", "rotate")
        }
        widget = mock.MagicMock()
        added = {}

        def add(cls, **kwargs):
            item = mock.MagicMock(name=kwargs.get("setObjectName"))
            added[kwargs.get("setObjectName")] = (item, kwargs)
            return item

        widget.option_box.menu.add.side_effect = add
        self.slots.tb004_init(widget)
        self.assertEqual(
            sorted(added), ["chk021", "chk022", "chk023", "s021", "s022", "s023"]
        )
        for name in ("s021", "s022"):
            added[name][0].setProperty.assert_called_once_with("requires", "maya")
            self.assertNotIn("setValue", added[name][1])
        added["s023"][0].setProperty.assert_not_called()
        self.assertEqual(added["s023"][1]["setValue"], 5.0)


class TestHeader(_SlotsCase):
    def test_fix_non_orthogonal_axes_reports(self):
        self.sb.tk.Diagnostics.fix_non_orthogonal_axes.return_value = ["a", "b"]
        self.slots.fix_non_ortho_axes()
        self.sb.tk.Diagnostics.fix_non_orthogonal_axes.assert_called_once_with(["pCube1"])
        self.assertIn("<hl>2</hl>", self.message())
        self.sb.tk.Diagnostics.fix_non_orthogonal_axes.return_value = []
        self.slots.fix_non_ortho_axes()
        self.assertIn("No non-orthogonal", self.message())

    def test_snap_opens_the_shared_panel(self):
        self.slots.b_snap_ts()
        self.sb.handlers.marking_menu.show.assert_called_once_with("snap")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class _MayaCase(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _cube(self, name, x=0.0):
        cube = self.cmds.polyCube(name=name)[0]
        self.cmds.move(x, 0, 0, cube)
        return cube

    def _center_x(self, node):
        bb = self.cmds.exactWorldBoundingBox(node)
        return (bb[0] + bb[3]) / 2.0


class TestFreezeInMaya(_MayaCase):
    def test_freeze_stamps_bake_history_once(self):
        """The real engine: tb002 leaves restorable bake attrs, stamped once
        (a second store would double-compose and Un-Freeze would overshoot)."""
        cube = self._cube("freeze_store", 3)
        self.cmds.select(cube)
        self.slots.tb002(_widget(**dict(FREEZE, chk_restore_rig_anchors=False)))
        self.assertTrue(self.cmds.attributeQuery("original_T_bake", node=cube, exists=True))
        self.assertTrue(self.cmds.attributeQuery("original_S_bake", node=cube, exists=True))
        self.assertAlmostEqual(
            self.cmds.getAttr(f"{cube}.original_T_bake")[0][0], 3.0, delta=1e-4
        )

    def test_unfreeze_round_trip(self):
        cube = self._cube("unfreeze_rt", 3)
        self.cmds.select(cube)
        self.slots.tb002(_widget(**FREEZE))
        self.slots.b002(
            _widget(
                chk_unfreeze_t=True,
                chk_unfreeze_r=True,
                chk_unfreeze_s=True,
                chk_unfreeze_children=False,
            )
        )
        self.assertAlmostEqual(self.cmds.getAttr(f"{cube}.translateX"), 3.0, places=4)


class TestMoveToInMaya(_MayaCase):
    def setUp(self):
        super().setUp()
        # Move To reads the pick order (``ls -orderedSelection``): tracking on, so
        # the clicks below are recorded in order (tracking off: unmeasured, BACKLOG).
        self.cmds.selectPref(trackSelectionOrder=True)

    def _pick(self, *nodes):
        """Select *nodes* one at a time, as clicks do: a single ``select`` of a
        list records no click order."""
        self.cmds.select(clear=True)
        for node in nodes:
            self.cmds.select(node, add=True)

    def test_move_all_to_last(self):
        a, b, c = self._cube("mv_a", 0), self._cube("mv_b", 3), self._cube("mv_c", 9)
        self._pick(a, b, c)
        self.slots.tb005(_widget(cmb005="center", chk036=True, chk_match_scale=False))
        self.sb.message_box.assert_not_called()
        for node in (a, b):
            self.assertAlmostEqual(self._center_x(node), 9.0, places=3)

    def test_first_to_rest(self):
        a, b, c = self._cube("mv_d", 0), self._cube("mv_e", 4), self._cube("mv_f", 8)
        self._pick(a, b, c)
        self.slots.tb005(_widget(cmb005="center", chk036=False, chk_match_scale=False))
        self.assertAlmostEqual(self._center_x(a), 6.0, places=3)

    def test_one_object_warns(self):
        self.cmds.select(self._cube("mv_one"))
        self.slots.tb005(_widget(cmb005="center", chk036=True, chk_match_scale=False))
        self.assertIn("two or more", self.message())


class TestMatchScaleInMaya(_MayaCase):
    def test_first_selected_takes_the_others_size(self):
        self.cmds.selectPref(trackSelectionOrder=True)
        a, b = self._cube("ms_a"), self._cube("ms_b", 4)
        self.cmds.scale(2, 2, 2, b)
        self.cmds.select(a)
        self.cmds.select(b, add=True)
        self.slots.b001()
        self.sb.message_box.assert_not_called()
        bb = self.cmds.exactWorldBoundingBox(a)
        self.assertAlmostEqual(bb[3] - bb[0], 2.0, places=3)

    def test_nothing_selected_warns(self):
        self.cmds.select(clear=True)
        self.slots.b001()
        self.assertIn("two or more", self.message())


class TestSnapInMaya(_MayaCase):
    """chk021-023 map a checked box to relative snapping in the manipulator and
    UV contexts alike (``XformUtils.set_transform_snap``)."""

    def test_checked_box_turns_relative_snap_on(self):
        calls = []

        def fake(*args, **kwargs):
            calls.append((args, kwargs))
            return 0

        names = ("manipMoveContext", "manipScaleContext", "manipRotateContext",
                 "texMoveContext", "texScaleContext", "texRotateContext")
        patches = [mock.patch.object(self.cmds, name, fake) for name in names]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.slots.chk021(True, None)
        self.assertEqual(calls[0][0], ("Move",))
        self.assertTrue(calls[0][1]["snap"])
        self.assertTrue(calls[0][1]["snapRelative"])
        calls.clear()
        self.slots.chk023(False, None)
        self.assertEqual(calls[0][0], ("Rotate",))
        self.assertFalse(calls[0][1]["snap"])


if __name__ == "__main__":
    unittest.main()
