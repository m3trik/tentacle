#!/usr/bin/python
# coding=utf-8
"""Regression tests for the Edit menus in tentacle.slots.edit: Create
(``list000``), Convert (``list001``) and Transfer (``cmb000``). Each lists what
the host's library offers and dispatches one call; the buttons are
test_edit.py's.

A fake toolkit stands in for the host here (plain pytest); in Maya the same
class drives the real ``mtk``. Pinned at this layer:

- Create: the host's primitive categories, then a Control category of the
  shapes its ``Controls`` registers; a leaf dispatches to
  ``Primitives.create`` or ``Controls.create(..., select=True)``; a category
  row only expands; a refusal reaches the user.
- Convert: the host's conversions; an unknown row does nothing; an empty
  selection and a refusal reach the user.
- Transfer: the host's transfers; the header emission does nothing; a bad
  selection, a refusal, an interactive tool and a run are each worded.
The operations and their catalogs are tested in mayatk and blendertk.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.edit import EditSlots


class _FakeItem:
    """A list row: its text, its parent's, and a sublist when it is a category."""

    def __init__(self, text, parent_text=None, has_sublist=False):
        self._text = text
        self._parent_text = parent_text
        if has_sublist:
            self.sublist = mock.MagicMock()
            self.sublist.get_items.return_value = ["a", "b"]

    def item_text(self):
        return self._text

    def parent_item_text(self):
        return self._parent_text


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = EditSlots(self.sb)
        self.tk = self.sb.tk

    def _message(self):
        call = self.sb.message_box.call_args
        return call.args[0] if call else None


class TestCreate(_SlotsCase):
    def test_init_lists_the_hosts_categories_then_its_controls(self):
        self.tk.Primitives.get_primitive_types.return_value = {
            "Polygon": ["Cube", "Sphere"],
            "Light": [],
        }
        self.tk.Controls.shapes.return_value = ["ball", "cube", "two_way_arrow", "text"]
        widget = mock.MagicMock()
        widget.ui.has_tags.return_value = False
        added = {}

        def add_category(name):
            row = mock.MagicMock()
            added[name] = row
            return row

        widget.add.return_value.sublist.add.side_effect = add_category
        self.slots.list000_init(widget)
        widget.apply_preset.assert_called_once_with("hover_menu")
        self.assertEqual(list(added), ["Polygon", "Control"])  # an empty one is left out
        added["Polygon"].sublist.add.assert_called_once_with(["Cube", "Sphere"])
        # the offered shapes the host registers, in menu order: no alias, no text
        added["Control"].sublist.add.assert_called_once_with(["Two Way Arrow", "Ball"])

    def test_a_category_row_only_expands(self):
        self.slots.list000(_FakeItem("Polygon", has_sublist=True))
        self.tk.Primitives.create.assert_not_called()
        self.tk.Controls.create.assert_not_called()

    def test_a_primitive_row_creates_it(self):
        self.slots.list000(_FakeItem("Cube", "Polygon"))
        self.tk.Primitives.create.assert_called_once_with("Polygon", "Cube")
        self.sb.message_box.assert_not_called()

    def test_a_control_row_creates_and_selects_it(self):
        self.slots.list000(_FakeItem("Two Way Arrow", "Control"))
        self.tk.Controls.create.assert_called_once_with(
            "two_way_arrow", name="TwoWayArrow", select=True
        )
        self.tk.Primitives.create.assert_not_called()

    def test_a_refusal_reaches_the_user(self):
        self.tk.Primitives.create.side_effect = ValueError("mtoa is not installed")
        self.slots.list000(_FakeItem("Skydome", "Arnold"))
        self.assertIn("Error creating Arnold Skydome", self._message())
        self.assertIn("mtoa", self._message())


class TestConvert(_SlotsCase):
    def setUp(self):
        super().setUp()
        self.tk.EditUtils.get_conversion_types.return_value = {"Mesh": "MESH"}

    def test_init_lists_the_hosts_conversions(self):
        widget = mock.MagicMock()
        widget.ui.has_tags.return_value = True
        self.slots.list001_init(widget)
        widget.apply_preset.assert_called_once_with("expand_down")
        widget.add.return_value.sublist.add.assert_called_once_with(["Mesh"])

    def test_the_root_row_and_an_unknown_row_do_nothing(self):
        self.slots.list001(_FakeItem("Convert", has_sublist=True))
        self.slots.list001(_FakeItem("Bogus"))
        self.tk.EditUtils.convert_objects.assert_not_called()

    def test_a_row_converts_the_selection(self):
        self.tk.EditUtils.convert_objects.return_value = ["obj"]
        self.slots.list001(_FakeItem("Mesh"))
        self.tk.EditUtils.convert_objects.assert_called_once_with(None, "Mesh")
        self.sb.message_box.assert_not_called()

    def test_nothing_selected_says_so(self):
        self.tk.EditUtils.convert_objects.return_value = []
        self.slots.list001(_FakeItem("Mesh"))
        self.assertEqual(self._message(), "Convert requires a selection.")

    def test_a_refusal_reaches_the_user(self):
        self.tk.EditUtils.convert_objects.side_effect = RuntimeError("poll failed")
        self.slots.list001(_FakeItem("Mesh"))
        self.assertIn("Convert 'Mesh' failed: poll failed", self._message())


class TestTransfer(_SlotsCase):
    TYPES = {"Shading Sets": "Shader assignments.", "Maps": "Add surfaces, then bake."}

    def setUp(self):
        super().setUp()
        self.tk.Components.get_transfer_types.return_value = dict(self.TYPES)
        self.tk.CoreUtils.leaf_name.side_effect = lambda o: str(o).rsplit("|", 1)[-1]
        self.widget = mock.MagicMock()
        self.widget.items = list(self.TYPES)

    def test_init_lists_the_hosts_transfers_under_a_header(self):
        widget = mock.MagicMock()
        self.slots.cmb000_init(widget)
        widget.add.assert_called_once_with(list(self.TYPES), header="Transfer:")

    def test_the_header_emission_does_nothing(self):
        self.slots.cmb000(-1, self.widget)
        self.tk.Components.transfer.assert_not_called()
        self.sb.message_box.assert_not_called()

    def test_a_run_reports_the_source_and_targets(self):
        self.tk.Components.transfer.return_value = ["|grp|src", "tgt1", "tgt2"]
        self.slots.cmb000(0, self.widget)
        self.tk.Components.transfer.assert_called_once_with(None, "Shading Sets")
        self.assertIn("Transferred Shading Sets", self._message())
        self.assertIn("<hl>src</hl> → 2 targets", self._message())
        self.sb.logger.log_raw.assert_called_once_with(
            "# Transfer 'Shading Sets': source=<src> target(s)=['tgt1', 'tgt2']"
        )

    def test_an_interactive_transfer_says_what_to_do(self):
        self.tk.Components.transfer.return_value = None
        self.slots.cmb000(1, self.widget)
        self.assertEqual(self._message(), "<b>Maps</b><br>Add surfaces, then bake.")

    def test_nothing_selected_asks_for_a_source_and_target(self):
        self.tk.Components.transfer.return_value = []
        self.slots.cmb000(0, self.widget)
        self.assertIn("needs a source and at least one target", self._message())

    def test_a_bad_selection_reaches_the_user(self):
        self.tk.Components.transfer.side_effect = ValueError("(1 of 2 selected)")
        self.slots.cmb000(0, self.widget)
        self.assertEqual(self._message(), "<b>Shading Sets</b>: (1 of 2 selected)")

    def test_a_refusal_reaches_the_user(self):
        self.tk.Components.transfer.side_effect = RuntimeError("kaboom")
        self.slots.cmb000(0, self.widget)
        self.assertIn("failed", self._message())
        self.assertIn("kaboom", self._message())


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestEditMenusInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")

    def tearDown(self):
        self.cmds.file(new=True, force=True)

    def test_create_a_polygon_cube(self):
        self.slots.list000(_FakeItem("Cube", "Polygon"))
        self.sb.message_box.assert_not_called()
        self.assertTrue(self.cmds.ls(type="polyCube"))

    def test_create_a_control_leaves_it_selected(self):
        self.slots.list000(_FakeItem("Diamond", "Control"))
        self.sb.message_box.assert_not_called()
        selected = self.cmds.ls(selection=True)
        self.assertEqual(len(selected), 1)
        self.assertTrue(self.cmds.listRelatives(selected[0], shapes=True, type="nurbsCurve"))

    def test_convert_with_nothing_selected_says_so(self):
        self.cmds.select(clear=True)
        self.slots.list001(_FakeItem("NURBS to Polygons"))
        self.assertEqual(self._message(), "Convert requires a selection.")

    def test_transfer_with_one_surface_asks_for_a_target(self):
        self.cmds.select(self.cmds.polySphere(name="xferOne")[0])
        widget = mock.MagicMock()
        widget.items = list(self.sb.tk.Components.get_transfer_types())
        self.slots.cmb000(widget.items.index("Shading Sets"), widget)
        self.assertIn("1 of 2", self._message())


if __name__ == "__main__":
    unittest.main()
