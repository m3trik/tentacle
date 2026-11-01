#!/usr/bin/python
# coding=utf-8
"""Tests for the materials submenu's "Get + Select" one-shot (``b003``) and the
select-by-material primitive behind every select entry point.

``MaterialsSlots.select_by_mat(shell, in_selection, get_first, add, unassigned)``: the
panel's material table (its Select icon, its row menu), the header's Objects Without
Material and the submenu's ``b003`` all call it with plain values, and it asks the host
toolkit (``self.tk``) for one operation -- ``MatUtils.select_by_mat`` or
``MatUtils.select_unassigned`` -- reporting what came back.

The "get the material off the selection" half is ``_adopt_selection_mat(on_failure)``
over ``_selection_mats()`` (the first selected object's material names, through
``MatUtils.get_mat_names``), serving ``get_first`` (which carries on with the current
material and says so). The current material is a name (``_current_mat``), not a list
entry, so a material the table filters out is adopted all the same.

A fake toolkit stands in for the host here (a MagicMock switchboard whose ``.tk``
records the calls); the operations themselves are tested in mayatk and blendertk.
"""
import inspect
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots._slots import Slots  # noqa: E402
from tentacle.slots.materials import MaterialsSlots  # noqa: E402

SUBMENU_UI = ROOT / "tentacle" / "ui" / "materials#submenu.ui"
SUBMENU_UI_PY = ROOT / "tentacle" / "ui" / "materials#submenu_ui.py"

PRIMITIVE_PARAMS = ("shell", "in_selection", "get_first", "add", "unassigned")


class _SlotsCase(unittest.TestCase):
    """A MaterialsSlots over a fake toolkit: one object selected, carrying
    ``matA``; the host finds ``obj1`` using any material."""

    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = MaterialsSlots(self.sb)
        self.slots.ui = SimpleNamespace()  # no table: the current material stands alone
        self.slots._refresh_material_lists = mock.Mock()
        self.tk = self.sb.tk
        self.tk.CoreUtils.selected_objects.return_value = ["obj1"]
        self.tk.MatUtils.get_mat_names.return_value = ["matA"]
        self.tk.MatUtils.select_by_mat.return_value = ["obj1"]
        self.tk.MatUtils.select_unassigned.return_value = ["obj2"]

    def messages(self):
        return [c.args[0] for c in self.sb.message_box.call_args_list]


class _OneShotCase(_SlotsCase):
    """``select_by_mat`` replaced by a recorder: b003's arguments are the point."""

    def setUp(self):
        super().setUp()
        self.slots.select_by_mat = mock.Mock(return_value=["obj1"])

    def call(self):
        return self.slots.select_by_mat.call_args.kwargs


class TestB003DelegatesWithFixedArgs(_OneShotCase):
    """b003 is a one-shot: get from the selection, whole objects, whole scene, replace."""

    def test_calls_the_primitive_once(self):
        self.slots.b003()
        self.slots.select_by_mat.assert_called_once()

    def test_gets_the_material_first_and_selects_whole_objects(self):
        self.slots.b003()
        self.assertTrue(self.call()["get_first"])
        self.assertTrue(self.call()["shell"])

    def test_searches_the_whole_scene_and_replaces_the_selection(self):
        """The configurable forms are the table's row menu -- b003 inherits neither."""
        self.slots.b003()
        self.assertFalse(self.call().get("in_selection", False))
        self.assertFalse(self.call().get("add", False))

    def test_returns_the_primitive_result(self):
        self.slots.select_by_mat.return_value = ["a", "b"]
        self.assertEqual(self.slots.b003(), ["a", "b"])

    def test_accepts_a_widget_arg(self):
        """Slot dispatch passes the widget to slots that accept one."""
        self.slots.b003(object())
        self.slots.select_by_mat.assert_called_once()

    def test_normal_path_is_not_an_unassigned_search(self):
        self.slots.b003()
        self.assertFalse(self.call().get("unassigned", False))


class TestB003UnassignedFallthrough(_OneShotCase):
    """A selection with NO material gets the analogous search, not a failure."""

    def test_materialless_selection_searches_for_unassigned(self):
        self.tk.MatUtils.get_mat_names.return_value = []
        self.slots.b003()
        self.assertTrue(self.call()["unassigned"])
        self.assertTrue(self.call()["shell"])
        self.assertFalse(self.call().get("get_first", False), "no material is never current")

    def test_fallthrough_says_what_it_is_doing(self):
        self.tk.MatUtils.get_mat_names.return_value = []
        self.slots.b003()
        self.assertEqual(len(self.messages()), 1)
        self.assertIn("no material", self.messages()[0].lower())

    def test_empty_selection_does_not_fall_through(self):
        """Nothing selected is a different problem -- the adopt path reports it."""
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.b003()
        self.assertFalse(self.call().get("unassigned", False))
        self.assertTrue(self.call()["get_first"])
        self.assertEqual(self.messages(), [])

    def test_multi_material_selection_does_not_fall_through(self):
        self.tk.MatUtils.get_mat_names.return_value = ["matA", "matB"]
        self.slots.b003()
        self.assertFalse(self.call().get("unassigned", False))
        self.assertTrue(self.call()["get_first"])


class TestAdoptSelectionMat(_SlotsCase):
    """One material -> it is current; anything else -> a reason, current untouched."""

    def test_the_first_selected_objects_materials_are_read(self):
        self.tk.CoreUtils.selected_objects.return_value = ["obj1", "obj2"]
        self.slots._adopt_selection_mat()
        self.tk.MatUtils.get_mat_names.assert_called_once_with(["obj1"])

    def test_single_material_is_adopted(self):
        self.assertEqual(self.slots._adopt_selection_mat(), "matA")
        self.assertEqual(self.slots._current_mat(), "matA")
        self.assertEqual(self.messages(), [])

    def test_a_material_no_list_shows_is_adopted_all_the_same(self):
        """A name can be current whatever the table shows (a filtered-out one)."""
        self.slots._current = "matZ"
        self.tk.MatUtils.get_mat_names.return_value = ["ns:matA"]
        self.assertEqual(self.slots._adopt_selection_mat(), "ns:matA")
        self.assertEqual(self.slots._current_mat(), "ns:matA")

    def test_nothing_selected_reports_and_keeps_the_current(self):
        self.slots._current = "matZ"
        self.tk.CoreUtils.selected_objects.return_value = []
        self.assertIsNone(self.slots._adopt_selection_mat())
        self.assertEqual(self.slots._current_mat(), "matZ")
        self.assertIn("Nothing selected", self.messages()[0])
        self.tk.MatUtils.get_mat_names.assert_not_called()

    def test_no_material_reports(self):
        self.tk.MatUtils.get_mat_names.return_value = []
        self.assertIsNone(self.slots._adopt_selection_mat())
        self.assertIn("No material found", self.messages()[0])

    def test_multiple_materials_reports(self):
        self.tk.MatUtils.get_mat_names.return_value = ["matA", "matB"]
        self.assertIsNone(self.slots._adopt_selection_mat())
        self.assertIn("Multiple materials", self.messages()[0])

    def test_on_failure_text_is_appended(self):
        """get_first carries on with the current material and says so."""
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots._adopt_selection_mat(" Proceeding with current material.")
        self.assertTrue(self.messages()[0].endswith(" Proceeding with current material."))

    def test_no_failure_text_by_default(self):
        self.tk.MatUtils.get_mat_names.return_value = []
        self.slots._adopt_selection_mat()
        self.assertNotIn("Proceeding", self.messages()[0])


class TestSelectByMatAsksTheHost(_SlotsCase):
    """One host operation per search, with the current material's NAME."""

    def test_the_signature_is_plain_values_all_off(self):
        params = inspect.signature(MaterialsSlots.select_by_mat).parameters
        self.assertEqual([p for p in params if p != "self"], list(PRIMITIVE_PARAMS))
        self.assertTrue(all(params[p].default is False for p in PRIMITIVE_PARAMS))

    def test_the_current_material_across_the_scene(self):
        self.slots._current = "matA"
        self.assertEqual(self.slots.select_by_mat(shell=True), ["obj1"])
        self.tk.MatUtils.select_by_mat.assert_called_once_with(
            "matA", None, shell=True, add=False
        )

    def test_within_the_selection_and_added(self):
        self.slots._current = "matA"
        self.slots.select_by_mat(in_selection=True, add=True)
        self.tk.MatUtils.select_by_mat.assert_called_once_with(
            "matA", ["obj1"], shell=False, add=True
        )

    def test_within_an_empty_selection_is_the_whole_scene(self):
        self.slots._current = "matA"
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.select_by_mat(in_selection=True)
        self.assertIsNone(self.tk.MatUtils.select_by_mat.call_args.args[1])

    def test_get_first_adopts_then_searches_the_adopted(self):
        self.slots._current = "matZ"
        self.slots.select_by_mat(get_first=True)
        self.assertEqual(self.tk.MatUtils.select_by_mat.call_args.args[0], "matA")

    def test_the_unassigned_search_is_the_hosts(self):
        self.slots._current = "matA"
        self.assertEqual(self.slots.select_by_mat(unassigned=True, add=True), ["obj2"])
        self.tk.MatUtils.select_unassigned.assert_called_once_with(None, add=True)
        self.tk.MatUtils.select_by_mat.assert_not_called()
        self.assertEqual(self.slots._current_mat(), "matA", "no material is never current")

    def test_the_header_offers_it(self):
        """Objects Without Material (b033, the header menu) is the panel's form."""
        self.slots.b033()
        self.tk.MatUtils.select_unassigned.assert_called_once_with(None, add=False)

    def test_no_current_material_asks_for_one(self):
        self.assertEqual(self.slots.select_by_mat(), [])
        self.tk.MatUtils.select_by_mat.assert_not_called()
        self.assertIn("No current material", self.messages()[0])

    def test_a_failed_get_first_is_said_once(self):
        """The adopt path said why; no second box for the missing current."""
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.select_by_mat(get_first=True)
        self.assertEqual(len(self.messages()), 1)

    def test_nothing_found_says_so(self):
        self.slots._current = "matA"
        self.tk.MatUtils.select_by_mat.return_value = []
        self.assertEqual(self.slots.select_by_mat(), [])
        self.assertIn("No matches", self.messages()[0])
        self.assertIn("matA", self.messages()[0])

    def test_a_material_gone_refills_the_list(self):
        self.slots._current = "matA"
        self.tk.MatUtils.select_by_mat.side_effect = ValueError("No material named 'matA'.")
        self.assertEqual(self.slots.select_by_mat(), [])
        self.assertIn("no longer exists", self.messages()[0])
        self.slots._refresh_material_lists.assert_called_once_with()

    def test_the_hosts_refusal_is_shown(self):
        """Blender: every user outside the active view layer."""
        self.slots._current = "matA"
        self.tk.MatUtils.select_by_mat.side_effect = RuntimeError("nothing selectable.")
        self.assertEqual(self.slots.select_by_mat(), [])
        self.assertEqual(self.messages(), ["nothing selectable."])


class TestSubmenuCarriesTheButton(unittest.TestCase):
    """A slot with no widget never fires -- pin the .ui and its compiled twin."""

    def test_ui_declares_b003(self):
        names = {w.get("name") for w in ET.parse(SUBMENU_UI).getroot().iter("widget")}
        self.assertIn("b003", names, f"{SUBMENU_UI.name} must declare the b003 button.")

    def test_ui_button_is_labeled_and_tooltipped(self):
        button = next(
            w
            for w in ET.parse(SUBMENU_UI).getroot().iter("widget")
            if w.get("name") == "b003"
        )
        props = {p.get("name"): (p.findtext("string") or "") for p in button.findall("property")}
        self.assertTrue(props.get("text", "").strip(), "b003 needs visible text.")
        self.assertTrue(props.get("toolTip", "").strip(), "b003 needs a tooltip.")

    def test_compiled_ui_is_in_sync(self):
        """The generated _ui.py is what actually builds the panel under the compiled
        loader. It's gitignored (built on demand), so only check it when present."""
        if not SUBMENU_UI_PY.exists():
            self.skipTest(f"{SUBMENU_UI_PY.name} not built in this checkout")
        self.assertIn(
            "b003",
            SUBMENU_UI_PY.read_text(encoding="utf-8"),
            f"{SUBMENU_UI_PY.name} is stale — run `python -m uitk.compile "
            f"\"tentacle/ui/{SUBMENU_UI.name}\"`.",
        )


if __name__ == "__main__":
    unittest.main()
