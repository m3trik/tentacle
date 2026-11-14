#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.editors, the one Editors Slots class.

It reaches its host only through ``self.tk``: a fake toolkit records what each
slot asks of it (plain pytest), and in Maya the same class drives the real
``mtk``. What's worth pinning at this layer:

- the All Editors list is the host's own grouping, and a row opens its editor
  (a category row only expands; a failed open says so);
- each button names the editor or docked strip it opens, by mayatk's name;
- the ``.ui`` hides each host's buttons from the other (``requires``).

The registries and the Time & Range toggle rule are tested in mayatk and
blendertk (``UiUtils.get_editor_categories`` / ``toggle_editor``).
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.editors import EditorsSlots

UI = Path(__file__).resolve().parents[1] / "tentacle" / "ui" / "editors#startmenu.ui"


class _Item:
    def __init__(self, text, children=()):
        self._text = text
        self.sublist = mock.Mock(get_items=mock.Mock(return_value=list(children)))

    def item_text(self):
        return self._text


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = EditorsSlots(self.sb)
        self.ui_utils = self.sb.tk.UiUtils
        self.ui_utils.get_editor_types.return_value = {"UV Editor": "x", "Outliner": "y"}


class TestEditorsList(_SlotsCase):
    def test_the_list_is_the_hosts_grouping_sorted(self):
        self.ui_utils.get_editor_categories.return_value = {
            "General Editors": ["Outliner", "Attribute Editor"],
            "Empty": [],
        }
        widget = mock.MagicMock()
        self.slots.list000_init(widget)
        widget.add.assert_called_once_with("General Editors")
        widget.add.return_value.sublist.add.assert_called_once_with(
            ["Attribute Editor", "Outliner"]
        )

    def test_an_editor_row_opens_its_editor(self):
        self.ui_utils.open_editor.return_value = "ok"
        self.slots.list000(_Item("UV Editor"))
        self.ui_utils.open_editor.assert_called_once_with("UV Editor")
        self.sb.message_box.assert_not_called()

    def test_a_category_row_only_expands(self):
        self.slots.list000(_Item("Modeling Editors", children=["UV Editor"]))
        self.slots.list000(_Item("Modeling Editors"))  # not an editor name either
        self.ui_utils.open_editor.assert_not_called()

    def test_a_failed_open_is_reported(self):
        self.ui_utils.open_editor.return_value = None
        self.slots.list000(_Item("Outliner"))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("Outliner", message)


class TestButtons(_SlotsCase):
    #: button -> the editor it opens, by mayatk's name
    OPENS = {
        "b000": "Attribute Editor",
        "b001": "Outliner",
        "b002": "Tool Settings",
        "b003": "Layer Editor",
        "b004": "Channel Box",
        "b005": "Node Editor",
        "b006": "Hypergraph: Hierarchy",
        "b014": "Geometry Nodes",
        "b015": "UV Editor",
        "b016": "Image Editor",
        "b017": "Graph Editor",
        "b018": "Text Editor",
    }
    #: button -> the docked strip it toggles
    TOGGLES = {
        "b007": "Status Line",
        "b008": "Shelf",
        "b009": "Timeline",
        "b011": "Command Line",
        "b012": "Help Line",
        "b013": "Tool Box",
    }

    def test_each_editor_button_opens_its_editor(self):
        for button, editor in self.OPENS.items():
            with self.subTest(button=button):
                getattr(self.slots, button)()
                self.ui_utils.open_editor.assert_called_with(editor)

    def test_each_strip_button_toggles_its_strip(self):
        for button, editor in self.TOGGLES.items():
            with self.subTest(button=button):
                getattr(self.slots, button)()
                self.ui_utils.toggle_editor.assert_called_with(editor)

    def test_a_refused_toggle_says_why(self):
        self.ui_utils.toggle_editor.side_effect = ValueError("no such strip")
        self.slots.b011()
        self.sb.message_box.assert_called_once_with("no such strip")

    def test_script_output_toggles_the_console_bare(self):
        self.slots.b010()
        self.sb.tk.ScriptConsole.toggle.assert_called_once_with()


class TestEachHostsButtonsAreTagged(unittest.TestCase):
    """The ``.ui`` is shared: Maya's chrome toggles and Dependency Graph are hidden
    in Blender, Blender's editor row in Maya (``requires``; uitk's
    ``apply_visibility_policy``), and every button has its slot."""

    MAYA = {"b006", "b007", "b008", "b012", "b013"}
    BLENDER = {"b014", "b015", "b016", "b017", "b018"}

    def setUp(self):
        self.buttons = {
            w.get("name"): w
            for w in ET.parse(UI).getroot().iter("widget")
            if w.get("class") == "QPushButton"
        }

    def _requires(self, name):
        node = self.buttons[name].find("property[@name='requires']/string")
        return node.text if node is not None else None

    def test_each_hosts_buttons_carry_its_tag(self):
        for name in self.buttons:
            expected = (
                "maya" if name in self.MAYA else "blender" if name in self.BLENDER else None
            )
            with self.subTest(button=name):
                self.assertEqual(self._requires(name), expected)

    def test_each_blender_button_sits_where_its_maya_button_does(self):
        for maya, blender in zip(sorted(self.MAYA), sorted(self.BLENDER)):
            rect = [
                self.buttons[n].find("property[@name='geometry']/rect") for n in (maya, blender)
            ]
            with self.subTest(pair=(maya, blender)):
                self.assertEqual(
                    [e.text for e in rect[0]], [e.text for e in rect[1]]
                )

    def test_every_button_has_a_slot(self):
        missing = [n for n in self.buttons if not callable(getattr(EditorsSlots, n, None))]
        self.assertEqual(missing, [])


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestEditorsInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.mtk = maya_module("mayatk")
        self.sb.tk = self.mtk
        self.ui_module = maya_module("mayatk.ui_utils._ui_utils")

    def test_the_list_holds_every_maya_editor(self):
        widget = mock.MagicMock()
        rows = []
        widget.add.return_value.sublist.add.side_effect = rows.extend
        self.slots.list000_init(widget)
        self.assertEqual(len(rows), 59)
        self.assertEqual(set(rows) - set(self.mtk.UiUtils.get_editor_types()), set())

    def _run(self, button, visible=()):
        """The commands *button* runs, with the components in *visible* showing."""
        ran = []

        def fake(command):
            if command.startswith("isUIComponentVisible"):
                return command.split('"')[1] in visible
            ran.append(command)
            return None

        with mock.patch.object(self.ui_module.mel, "eval", side_effect=fake):
            getattr(self.slots, button)()
        return ran

    def test_time_and_range_hides_what_shows_and_shows_both_when_hidden(self):
        self.assertEqual(
            self._run("b009", {"Time Slider"}), ["ToggleTimeSlider"]
        )
        self.assertEqual(
            self._run("b009"), ["ToggleTimeSlider", "ToggleRangeSlider"]
        )

    def test_the_buttons_open_mayas_windows(self):
        self.assertEqual(self._run("b000"), ["AttributeEditor"])
        self.assertEqual(self._run("b001"), ["OutlinerWindow"])
        self.assertEqual(self._run("b005"), ["NodeEditorWindow"])
        self.assertEqual(self._run("b006"), ["HypergraphHierarchyWindow"])
        self.assertEqual(self._run("b007"), ["ToggleStatusLine"])


if __name__ == "__main__":
    unittest.main()
