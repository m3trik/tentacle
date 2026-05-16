#!/usr/bin/python
# coding=utf-8
"""Regression tests for the primitive/convert dispatchers in
tentacle.slots.maya.edit.

The existing test_edit.py covers tb001 (delete-history) in depth — the
instance-sibling regression. This file fills in the other heavy-logic
units: list000 (Create primitives) and list001 (Convert), which dispatch
to multiple downstream paths based on parent + leaf text.

What gets tested here:
- The class-level command-table constants exist and are dict-shaped.
- list000 routes Control / Curve / Helper / Polygon paths correctly.
- list001 maps known conversion labels to their MEL commands.
- Both dispatchers no-op cleanly when item is a parent (has sublist).
"""
import unittest

try:
    import maya.cmds as cmds
    import maya.mel as mel
    from tentacle.slots.maya import edit as edit_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    mel = None
    edit_module = None
    _MAYA_AVAILABLE = False


class _FakeItem:
    """Stand-in for the sublist item — exposes item_text/parent_item_text."""

    def __init__(self, text, parent_text=None, has_sublist=False):
        self._text = text
        self._parent_text = parent_text
        if has_sublist:
            self.sublist = _FakeSublistWithItems()
        # No .sublist attribute when not a parent — list000/list001 use getattr.

    def item_text(self):
        return self._text

    def parent_item_text(self):
        return self._parent_text


class _FakeSublistWithItems:
    def get_items(self):
        return ["a", "b"]


class _FakeSublistEmpty:
    def get_items(self):
        return []


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestCommandTableConstants(unittest.TestCase):
    """The class-level command tables underpin list000/list001 dispatch.
    Verify their shape so a typo in a dict literal can't silently break
    one of the toolbar's most-used buttons.
    """

    def test_curve_commands_is_dict_of_str_to_mel_str(self):
        commands = edit_module.Edit._CURVE_COMMANDS
        self.assertIsInstance(commands, dict)
        self.assertGreater(len(commands), 0)
        for label, mel_str in commands.items():
            self.assertIsInstance(label, str)
            self.assertIsInstance(mel_str, str)
            # Each value should be a MEL statement.
            self.assertTrue(mel_str.rstrip().endswith(";"))

    def test_curve_commands_includes_known_entries(self):
        commands = edit_module.Edit._CURVE_COMMANDS
        for required in ("Ep Curve Tool", "CV Curve Tool", "Bezier Curve Tool"):
            self.assertIn(required, commands)

    def test_helper_commands_values_are_callable(self):
        helpers = edit_module.Edit._HELPER_COMMANDS
        self.assertIsInstance(helpers, dict)
        for label, fn in helpers.items():
            self.assertTrue(callable(fn), f"{label!r} must be callable")

    def test_helper_commands_includes_known_entries(self):
        helpers = edit_module.Edit._HELPER_COMMANDS
        for required in ("Null Group", "Locator", "Set"):
            self.assertIn(required, helpers)

    def test_convert_commands_is_dict_of_str_to_mel_str(self):
        commands = edit_module.Edit._CONVERT_COMMANDS
        self.assertIsInstance(commands, dict)
        self.assertGreater(len(commands), 0)
        for label, mel_str in commands.items():
            self.assertIsInstance(label, str)
            self.assertIsInstance(mel_str, str)
            self.assertTrue(mel_str.rstrip().endswith(";"))

    def test_convert_commands_includes_known_entries(self):
        commands = edit_module.Edit._CONVERT_COMMANDS
        for required in (
            "NURBS to Polygons",
            "Smooth Mesh Preview to Polygons",
            "Polygon Edges to Curve",
        ):
            self.assertIn(required, commands)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestList000Dispatch(unittest.TestCase):
    """list000 routes to the right downstream call based on parent_text."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = edit_module.Edit.__new__(edit_module.Edit)

        # Capture downstream calls.
        self.helper_calls = []
        self.mel_calls = []
        self.primitive_calls = []
        self.control_calls = []

        # Patch _HELPER_COMMANDS values to record invocation rather than
        # actually create scene nodes.
        self._orig_helpers = edit_module.Edit._HELPER_COMMANDS
        edit_module.Edit._HELPER_COMMANDS = {
            "Null Group": lambda: self.helper_calls.append("Null Group"),
            "Locator": lambda: self.helper_calls.append("Locator"),
            "Set": lambda: self.helper_calls.append("Set"),
        }

        # Patch mel.eval and the downstream mtk functions.
        self._orig_mel_eval = mel.eval
        mel.eval = lambda cmd: self.mel_calls.append(cmd)

        import mayatk as mtk
        self._orig_primitive = mtk.Primitives.create_default_primitive
        self._orig_control = mtk.Controls.create
        mtk.Primitives.create_default_primitive = lambda parent, text: self.primitive_calls.append((parent, text))
        mtk.Controls.create = lambda preset, name=None, **kwargs: self.control_calls.append(preset) or "stub_ctrl"

        # Patch cmds.select / selectMode to no-op.
        self._orig_select = cmds.select
        self._orig_selectMode = cmds.selectMode
        cmds.select = lambda *a, **kw: None
        cmds.selectMode = lambda **kw: None

    def tearDown(self):
        edit_module.Edit._HELPER_COMMANDS = self._orig_helpers
        mel.eval = self._orig_mel_eval
        import mayatk as mtk
        mtk.Primitives.create_default_primitive = self._orig_primitive
        mtk.Controls.create = self._orig_control
        cmds.select = self._orig_select
        cmds.selectMode = self._orig_selectMode
        cmds.file(new=True, force=True)

    def test_parent_item_with_sublist_short_circuits(self):
        item = _FakeItem("Polygon", parent_text=None, has_sublist=True)
        self.instance.list000(item)
        # No downstream call should fire.
        self.assertEqual(self.helper_calls, [])
        self.assertEqual(self.mel_calls, [])
        self.assertEqual(self.primitive_calls, [])
        self.assertEqual(self.control_calls, [])

    def test_polygon_routes_to_primitives(self):
        item = _FakeItem("Cube", parent_text="Polygon")
        self.instance.list000(item)
        self.assertEqual(self.primitive_calls, [("Polygon", "Cube")])

    def test_nurbs_routes_to_primitives(self):
        item = _FakeItem("Sphere", parent_text="NURBS")
        self.instance.list000(item)
        self.assertEqual(self.primitive_calls, [("NURBS", "Sphere")])

    def test_control_routes_to_controls_create(self):
        item = _FakeItem("Diamond", parent_text="Control")
        self.instance.list000(item)
        self.assertEqual(self.control_calls, ["diamond"])

    def test_control_unknown_preset_no_op(self):
        """Unknown Control text doesn't match the map — no downstream call."""
        item = _FakeItem("Bogus", parent_text="Control")
        self.instance.list000(item)
        self.assertEqual(self.control_calls, [])

    def test_curve_routes_to_mel(self):
        item = _FakeItem("Ep Curve Tool", parent_text="Curve")
        self.instance.list000(item)
        # mel.eval should have been called with the Ep Curve Tool MEL command.
        self.assertEqual(len(self.mel_calls), 1)
        self.assertEqual(self.mel_calls[0], "EPCurveToolOptions;")

    def test_curve_unknown_no_op(self):
        item = _FakeItem("Bogus Curve", parent_text="Curve")
        self.instance.list000(item)
        self.assertEqual(self.mel_calls, [])

    def test_helper_routes_to_helper_callable(self):
        item = _FakeItem("Locator", parent_text="Helper")
        self.instance.list000(item)
        self.assertEqual(self.helper_calls, ["Locator"])

    def test_helper_unknown_no_op(self):
        item = _FakeItem("Bogus Helper", parent_text="Helper")
        self.instance.list000(item)
        self.assertEqual(self.helper_calls, [])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestList001Convert(unittest.TestCase):
    """list001 looks up text in _CONVERT_COMMANDS and dispatches via mel.eval."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = edit_module.Edit.__new__(edit_module.Edit)
        self.mel_calls = []
        self._orig_mel_eval = mel.eval
        mel.eval = lambda cmd: self.mel_calls.append(cmd)

    def tearDown(self):
        mel.eval = self._orig_mel_eval
        cmds.file(new=True, force=True)

    def test_parent_item_with_sublist_short_circuits(self):
        item = _FakeItem("Convert", parent_text=None, has_sublist=True)
        self.instance.list001(item)
        self.assertEqual(self.mel_calls, [])

    def test_known_conversion_dispatches_mel(self):
        item = _FakeItem("NURBS to Polygons")
        self.instance.list001(item)
        self.assertEqual(self.mel_calls, ["performnurbsToPoly 0;"])

    def test_unknown_conversion_no_op(self):
        item = _FakeItem("Bogus to Bogus")
        self.instance.list001(item)
        self.assertEqual(self.mel_calls, [])

    def test_each_known_entry_dispatches_its_mapped_mel(self):
        """Every entry in the convert table should route to exactly its MEL."""
        for label, expected_mel in edit_module.Edit._CONVERT_COMMANDS.items():
            self.mel_calls.clear()
            item = _FakeItem(label)
            self.instance.list001(item)
            self.assertEqual(
                self.mel_calls,
                [expected_mel],
                f"Mismatch for label {label!r}",
            )


if __name__ == "__main__":
    unittest.main()
