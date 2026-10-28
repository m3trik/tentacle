#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.nurbs, the one NURBS Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- list000: each leaf names its curve action (or tool), a category row is
  navigation only, and a refusal reaches the user with the leaf's label.
  The parametric-NURBS-only rows carry ``requires="maya"``.
- tb000 (Revolve) / tb001 (Loft): widget values -> the library's keywords.
- b056 / b058: the shared tool panels they open.
The operations themselves are tested in mayatk and blendertk.
"""
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.nurbs import NurbsSlots


def _widget(**values):
    """A widget whose option-box menu holds fakes reading *values*."""
    widget = mock.MagicMock()
    for name, value in values.items():
        child = getattr(widget.option_box.menu, name)
        child.value.return_value = value
        child.isChecked.return_value = value
        child.currentText.return_value = value
    return widget


def _leaf(text, parent, sublist=None):
    """An ExpandableList item as list000 sees it."""
    return mock.Mock(
        item_text=mock.Mock(return_value=text),
        parent_item_text=mock.Mock(return_value=parent),
        sublist=sublist,
    )


REVOLVE = dict(
    s002=3,
    s003=10,
    s004=350,
    s005=16,
    cmb_screw_axis="Z",
    chk006=False,
    chk007=True,
    chk008=True,
    chk009=False,
    s006=0.001,
)

LOFT = dict(
    chk000=True,
    chk001=True,
    s000=5,
    chk002=True,
    s001=4,
    chk003=False,
    chk004=True,
    chk005=False,
    chk010=True,
    s007=8,
)


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = NurbsSlots(self.sb)
        self.nurbs = self.sb.tk.NurbsUtils


class TestList000Dispatch(_SlotsCase):
    def test_each_leaf_runs_its_curve_action_on_the_selection(self):
        self.slots.list000(_leaf("Reverse", "Edit"))
        self.nurbs.curve_action.assert_called_once_with("reverse")
        self.sb.message_box.assert_not_called()

    def test_tool_rows_activate_the_tool(self):
        self.slots.list000(_leaf("Edit Curve Tool", "Edit"))
        self.sb.tk.UiUtils.set_tool.assert_called_once_with("Edit Curve Tool")
        self.nurbs.curve_action.assert_not_called()

    def test_a_refusal_names_the_leaf(self):
        self.nurbs.curve_action.side_effect = RuntimeError(
            "ProjectCurveOnMesh: no target mesh"
        )
        self.slots.list000(_leaf("Project", "Create"))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("Project", message)
        self.assertIn("no target mesh", message)

    def test_a_wrong_selection_is_said_too(self):
        self.nurbs.curve_action.side_effect = ValueError("Select one or more curves.")
        self.slots.list000(_leaf("Smooth", "Modify"))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("Select one or more curves.", message)

    def test_category_click_is_a_noop(self):
        item = _leaf("Create", "Nurbs", sublist=mock.Mock(get_items=lambda: ["x"]))
        self.slots.list000(item)
        self.nurbs.curve_action.assert_not_called()
        self.sb.message_box.assert_not_called()

    def test_every_row_has_a_known_kind(self):
        """Every row is a tool or a curve action; only Maya's parametric-NURBS
        rows are host-tagged, and only as Maya's."""
        maya_only = set()
        for rows in NurbsSlots._LIST000_ITEMS.values():
            for label, action, requires in rows:
                self.assertIn(requires, (None, "maya"), label)
                if requires:
                    maya_only.add(action)
        self.assertEqual(
            maya_only,
            {
                "lock_length",
                "unlock_length",
                "insert_isoparm",
                "insert_knot",
                "extend_options",
                "extend_on_surface",
            },
        )

    def test_init_tags_maya_only_rows(self):
        widget = mock.MagicMock()
        widget.ui.has_tags.return_value = False
        rows = {}

        def add_labels(labels):
            items = [mock.MagicMock(name=label) for label in labels]
            rows.update(zip(labels, items))
            return items

        widget.add.return_value.sublist.add.return_value.sublist.add.side_effect = (
            add_labels
        )
        self.slots.list000_init(widget)
        rows["Lock"].setProperty.assert_called_once_with("requires", "maya")
        rows["Reverse"].setProperty.assert_not_called()
        self.sb.apply_visibility_policy.assert_any_call(rows["Insert Knot"])


class TestButtons(_SlotsCase):
    def test_extrude_is_a_curve_action(self):
        self.slots.b030()
        self.nurbs.curve_action.assert_called_once_with("extrude")

    def test_tool_panels(self):
        self.slots.b056()
        self.slots.b058()
        shown = [c.args[0] for c in self.sb.handlers.marking_menu.show.call_args_list]
        self.assertEqual(shown, ["image_tracer", "curve_to_tube"])


class TestTb000Revolve(_SlotsCase):
    def test_widget_values_reach_the_library(self):
        self.nurbs.revolve.return_value = ["surface"]
        self.slots.tb000(_widget(**REVOLVE))
        call = self.nurbs.revolve.call_args
        self.assertEqual(call.args, (None,))
        self.assertEqual(
            call.kwargs,
            dict(
                axis="Z",
                start_sweep=10,
                end_sweep=350,
                sections=16,
                degree=3,
                range_=False,
                polygon=True,
                use_tolerance=False,
                tolerance=0.001,
                auto_correct_normal=True,
            ),
        )
        self.sb.message_box.assert_not_called()

    def test_nothing_to_revolve_says_so(self):
        self.nurbs.revolve.return_value = []
        self.slots.tb000(_widget(**REVOLVE))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("Revolve", message)

    def test_a_refusal_is_said(self):
        self.nurbs.revolve.side_effect = RuntimeError("bad profile")
        self.slots.tb000(_widget(**REVOLVE))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("bad profile", message)


class TestTb001Loft(_SlotsCase):
    def test_widget_values_reach_the_library(self):
        self.nurbs.loft.return_value = ["loft1"]
        self.slots.tb001(_widget(**LOFT))
        self.assertEqual(
            self.nurbs.loft.call_args.kwargs,
            dict(
                uniform=True,
                close=True,
                degree=5,
                autoReverse=True,
                sectionSpans=4,
                range_=False,
                polygon=True,
                reverseSurfaceNormals=False,
                angle_loft_between_two_curves=True,
                angleLoftSpans=8,
            ),
        )
        self.sb.message_box.assert_not_called()

    def test_too_few_profiles_says_so(self):
        self.nurbs.loft.return_value = []
        self.slots.tb001(_widget(**LOFT))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("two or more", message)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestNurbsInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _profile(self):
        return self.cmds.curve(degree=1, point=[(1, 0, 0), (1, 2, 0)])

    def test_revolve_builds_a_surface_about_the_chosen_axis(self):
        self.cmds.select(self._profile())
        self.slots.tb000(_widget(**dict(REVOLVE, chk007=False)))
        self.sb.message_box.assert_not_called()
        surfaces = self.cmds.ls(selection=True)
        self.assertEqual(len(surfaces), 1)
        self.assertTrue(
            self.cmds.listRelatives(surfaces[0], shapes=True, type="nurbsSurface")
        )

    def test_revolve_with_nothing_selected_says_so(self):
        self.cmds.select(clear=True)
        self.slots.tb000(_widget(**REVOLVE))
        self.assertTrue(self.sb.message_box.called)

    def test_loft_with_one_profile_says_so(self):
        self.cmds.select(self.cmds.circle()[0])
        self.slots.tb001(_widget(**dict(LOFT, chk004=False, chk010=False)))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("two or more", message)

    def test_loft_two_circles(self):
        a = self.cmds.circle()[0]
        b = self.cmds.circle()[0]
        self.cmds.move(0, 0, 4, b)
        self.cmds.select(a, b)
        self.slots.tb001(_widget(**dict(LOFT, chk004=False, chk010=False)))
        self.sb.message_box.assert_not_called()

    def test_reverse_leaf_reverses_the_selected_curve(self):
        curve = self.cmds.curve(degree=1, point=[(0, 0, 0), (1, 0, 0), (3, 0, 0)])
        self.cmds.select(curve)
        self.slots.list000(_leaf("Reverse", "Edit"))
        self.sb.message_box.assert_not_called()
        start = self.cmds.pointPosition(f"{curve}.cv[0]", world=True)
        self.assertAlmostEqual(start[0], 3.0, places=4)


if __name__ == "__main__":
    unittest.main()
