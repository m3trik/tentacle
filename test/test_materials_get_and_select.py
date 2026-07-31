#!/usr/bin/python
# coding=utf-8
"""Tests for the materials submenu's "Get + Select" one-shot (``b003``).

The submenu button gets the material off the current selection and selects every object
using it. Copying the main panel's "Select" button (``tb000``) into the submenu would not
give that: uitk mirrors same-named widget values across a panel and its ``#submenu``
surface (``MainWindow.sync_widget_values``), so the copy IS the configurable button — it
runs with whatever the user last set, and only "gets" the material when "Get and Select"
happens to be ticked. Temporarily overwriting ``tb000``'s stored option state around the
call was the other option (it also fires the toggles' own connections, and needs new uitk
state API for no behavioral gain). Instead the search body was extracted into a
parameterized per-DCC primitive,
``select_by_mat(shell, in_selection, get_first, add)``. ``tb000`` reads its option box and
delegates; the submenu's ``b003`` (defined ONCE on the DCC-agnostic ``MaterialsMixin``)
calls the same primitive with fixed values.

The "get the material off the selection" half became shared the same way:
``_adopt_selection_mat(on_failure)`` on the mixin over a ``_selection_mats()`` DCC hook,
serving both "Get Material" (``b002``, which stops on failure) and ``get_first`` (which
carries on with the current material and says so).

The mixin half runs without any DCC; the per-DCC halves are pinned by AST (no
``maya.cmds`` / ``bpy`` needed) plus an XML/text check that the widget really exists in the
submenu .ui and its compiled ``_ui.py``.
"""
import ast
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots._materials import MaterialsMixin  # noqa: E402

MAYA_FILE = ROOT / "tentacle" / "slots" / "maya" / "materials.py"
BLENDER_FILE = ROOT / "tentacle" / "slots" / "blender" / "materials.py"
SUBMENU_UI = ROOT / "tentacle" / "ui" / "materials#submenu.ui"
SUBMENU_UI_PY = ROOT / "tentacle" / "ui" / "materials#submenu_ui.py"

DCC_FILES = (MAYA_FILE, BLENDER_FILE)
PRIMITIVE = "select_by_mat"
PRIMITIVE_PARAMS = ("shell", "in_selection", "get_first", "add", "unassigned")


class _Host(MaterialsMixin):
    """Minimal host recording the ``select_by_mat`` hook the mixin calls."""

    def __init__(self, result=("obj1",), mats=("matA",)):
        self.calls = []
        self.messages = []
        self._result = list(result)
        self._mats = None if mats is None else list(mats)
        self.sb = type("_SB", (), {"message_box": lambda _s, m: self.messages.append(m)})()

    def _selection_mats(self):
        return self._mats

    def select_by_mat(
        self, shell=False, in_selection=False, get_first=False, add=False, unassigned=False
    ):
        self.calls.append(
            {
                "shell": shell,
                "in_selection": in_selection,
                "get_first": get_first,
                "add": add,
                "unassigned": unassigned,
            }
        )
        return self._result


class TestB003DelegatesWithFixedArgs(unittest.TestCase):
    """b003 is a one-shot: get from the selection, whole objects, whole scene, replace."""

    def test_calls_the_primitive_once(self):
        host = _Host()
        host.b003()
        self.assertEqual(len(host.calls), 1)

    def test_gets_the_material_first(self):
        host = _Host()
        host.b003()
        self.assertTrue(host.calls[0]["get_first"])

    def test_selects_whole_objects(self):
        host = _Host()
        host.b003()
        self.assertTrue(host.calls[0]["shell"])

    def test_searches_the_whole_scene_and_replaces_the_selection(self):
        """The configurable form is tb000's option box — b003 must not inherit either."""
        host = _Host()
        host.b003()
        self.assertFalse(host.calls[0]["in_selection"])
        self.assertFalse(host.calls[0]["add"])

    def test_returns_the_primitive_result(self):
        host = _Host(result=["a", "b"])
        self.assertEqual(host.b003(), ["a", "b"])

    def test_accepts_a_widget_arg(self):
        """Slot dispatch passes the widget to slots that accept one."""
        host = _Host()
        host.b003(object())
        self.assertEqual(len(host.calls), 1)

    def test_normal_path_is_not_an_unassigned_search(self):
        host = _Host()
        host.b003()
        self.assertFalse(host.calls[0]["unassigned"])


class TestB003UnassignedFallthrough(unittest.TestCase):
    """A selection with NO material gets the analogous search, not a failure."""

    def test_materialless_selection_searches_for_unassigned(self):
        host = _Host(mats=[])
        host.b003()
        self.assertTrue(host.calls[0]["unassigned"])
        self.assertTrue(host.calls[0]["shell"])

    def test_fallthrough_does_not_try_to_adopt_a_material(self):
        """"No material" must never become cmb002's current material."""
        host = _Host(mats=[])
        host.b003()
        self.assertFalse(host.calls[0]["get_first"])

    def test_fallthrough_says_what_it_is_doing(self):
        host = _Host(mats=[])
        host.b003()
        self.assertEqual(len(host.messages), 1)
        self.assertIn("no material", host.messages[0].lower())

    def test_empty_selection_does_not_fall_through(self):
        """Nothing selected is a different problem — the adopt path reports it."""
        host = _Host(mats=None)
        host.b003()
        self.assertFalse(host.calls[0]["unassigned"])
        self.assertTrue(host.calls[0]["get_first"])
        self.assertEqual(host.messages, [])

    def test_multi_material_selection_does_not_fall_through(self):
        host = _Host(mats=["matA", "matB"])
        host.b003()
        self.assertFalse(host.calls[0]["unassigned"])
        self.assertTrue(host.calls[0]["get_first"])


class _FakeCombo:
    """cmb002 stand-in. ``items`` mimics the list filters: a value that isn't in
    it resolves to index 0, exactly as ``ComboBox.setAsCurrent`` does."""

    def __init__(self, current=None, items=None):
        self.current = current
        self.items = items
        self.init_calls = 0

    def currentData(self):
        return self.current

    def init_slot(self):
        self.init_calls += 1

    def setAsCurrent(self, value):
        if self.items is not None and value not in self.items:
            self.current = self.items[0] if self.items else None
            return
        self.current = value


class _AdoptHost(MaterialsMixin):
    """Host for the shared adopt path — ``_selection_mats`` is the DCC hook."""

    def __init__(self, mats, current=None, items=None):
        self._mats = mats
        self.messages = []
        self.ui = type("_UI", (), {})()
        self.ui.cmb002 = _FakeCombo(current, items)
        self.sb = type("_SB", (), {"message_box": lambda _s, m: self.messages.append(m)})()

    def _selection_mats(self):
        return self._mats


class TestAdoptSelectionMat(unittest.TestCase):
    """One material -> adopt it; anything else -> a reason, and cmb002 untouched."""

    def test_single_material_is_adopted(self):
        host = _AdoptHost(["matA"])
        self.assertEqual(host._adopt_selection_mat(), "matA")
        self.assertEqual(host.ui.cmb002.current, "matA")
        self.assertEqual(host.messages, [])

    def test_combo_is_repopulated_before_selecting(self):
        """The material may be missing from a stale list, so the combo refreshes first."""
        host = _AdoptHost(["matA"])
        host._adopt_selection_mat()
        self.assertEqual(host.ui.cmb002.init_calls, 1)

    def test_nothing_selected_reports_and_leaves_the_combo(self):
        host = _AdoptHost(None)
        self.assertIsNone(host._adopt_selection_mat())
        self.assertIsNone(host.ui.cmb002.current)
        self.assertIn("Nothing selected", host.messages[0])

    def test_no_material_reports(self):
        host = _AdoptHost([])
        self.assertIsNone(host._adopt_selection_mat())
        self.assertIn("No material found", host.messages[0])

    def test_multiple_materials_reports(self):
        host = _AdoptHost(["matA", "matB"])
        self.assertIsNone(host._adopt_selection_mat())
        self.assertIn("Multiple materials", host.messages[0])

    def test_on_failure_text_is_appended(self):
        """get_first carries on with the current material and says so; b002 doesn't."""
        host = _AdoptHost(None)
        host._adopt_selection_mat(" Proceeding with current material.")
        self.assertTrue(host.messages[0].endswith(" Proceeding with current material."))

    def test_no_failure_text_by_default(self):
        host = _AdoptHost([])
        host._adopt_selection_mat()
        self.assertNotIn("Proceeding", host.messages[0])


class TestAdoptRejectsAFilteredMaterial(unittest.TestCase):
    """``ComboBox.setAsCurrent`` falls back to INDEX 0 for a missing item.

    A cmb002 list filter ("Hide Default Materials" / "Hide Arnold Shaders") can
    drop the found material from the list — Maya's default shader is exactly the
    material an unshaded object reports — so adopting it would silently leave an
    unrelated material current and then select by THAT.
    """

    def _host(self):  # 'matA' is filtered out of the list; 'matZ' is current
        return _AdoptHost(["matA"], current="matZ", items=["matB", "matZ"])

    def test_filtered_material_is_not_adopted(self):
        self.assertIsNone(self._host()._adopt_selection_mat())

    def test_previous_material_is_restored(self):
        host = self._host()
        host._adopt_selection_mat()
        self.assertEqual(host.ui.cmb002.current, "matZ")

    def test_the_filter_is_reported(self):
        host = self._host()
        host._adopt_selection_mat()
        self.assertEqual(len(host.messages), 1)
        self.assertIn("matA", host.messages[0])
        self.assertIn("filter", host.messages[0].lower())

    def test_unfiltered_material_still_adopts(self):
        host = _AdoptHost(["matA"], current="matZ", items=["matA", "matZ"])
        self.assertEqual(host._adopt_selection_mat(), "matA")
        self.assertEqual(host.messages, [])

    def test_message_says_what_the_caller_does_next(self):
        """get_first carries on with the current material — every failure reason
        has to say so, or the message misdescribes the outcome."""
        host = self._host()
        host._adopt_selection_mat(" Proceeding with current material.")
        self.assertTrue(host.messages[0].endswith(" Proceeding with current material."))


class _AstMixin:
    """AST lookup helpers (import-free — the DCC modules need maya.cmds / bpy)."""

    def _classdef(self, path, name="MaterialsSlots"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return next(
            (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == name),
            None,
        )

    def _method(self, classdef, name):
        return next(
            (
                b
                for b in classdef.body
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and b.name == name
            ),
            None,
        )

    def _self_calls(self, node):
        """Names of ``self.<name>(...)`` calls made inside *node*."""
        return {
            n.func.attr
            for n in ast.walk(node)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "self"
        }


class TestBothDccsImplementThePrimitive(_AstMixin, unittest.TestCase):
    """Each DCC supplies ``select_by_mat`` with the same plain-value signature."""

    def test_primitive_exists_with_the_shared_signature(self):
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                method = self._method(self._classdef(path), PRIMITIVE)
                self.assertIsNotNone(method, f"{PRIMITIVE} not found in {path.name}")
                params = [a.arg for a in method.args.args if a.arg != "self"]
                self.assertEqual(
                    params,
                    list(PRIMITIVE_PARAMS),
                    f"{path.name} {PRIMITIVE} must take the shared parameters in order — "
                    "the mixin's b003 calls it by keyword against this contract.",
                )
                self.assertEqual(
                    [getattr(d, "value", "?") for d in method.args.defaults],
                    [False] * len(PRIMITIVE_PARAMS),
                    f"{path.name} {PRIMITIVE}: every parameter defaults to False.",
                )

    def test_primitive_returns_a_value(self):
        """b003 hands the result back to its caller, so the hook must return one."""
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                method = self._method(self._classdef(path), PRIMITIVE)
                self.assertTrue(
                    any(
                        isinstance(n, ast.Return) and n.value is not None
                        for n in ast.walk(method)
                    ),
                    f"{path.name} {PRIMITIVE} must return the selected objects.",
                )


class TestTb000DelegatesInsteadOfDuplicating(_AstMixin, unittest.TestCase):
    """tb000 stays a thin option-box reader over the shared primitive."""

    def test_tb000_calls_the_primitive(self):
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                tb000 = self._method(self._classdef(path), "tb000")
                self.assertIsNotNone(tb000, f"tb000 not found in {path.name}")
                self.assertIn(
                    PRIMITIVE,
                    self._self_calls(tb000),
                    f"{path.name} tb000 must delegate to self.{PRIMITIVE}.",
                )

    def test_tb000_holds_no_search_body(self):
        """The search must live in one place — a second copy is how the two entry
        points drift apart."""
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                tb000 = self._method(self._classdef(path), "tb000")
                names = {
                    n.func.attr
                    for n in ast.walk(tb000)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                }
                self.assertNotIn(
                    "find_by_mat_id",
                    names,
                    f"{path.name} tb000 must not re-implement the search — "
                    f"that body belongs to {PRIMITIVE}.",
                )


class TestUnassignedModeIsWiredInBothDccs(_AstMixin, unittest.TestCase):
    """The no-material search runs through the engines, never through cmb002."""

    def test_primitive_uses_the_engine_finder(self):
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                method = self._method(self._classdef(path), PRIMITIVE)
                names = {
                    n.func.attr
                    for n in ast.walk(method)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                }
                self.assertIn(
                    "find_unassigned",
                    names,
                    f"{path.name} {PRIMITIVE} must delegate the no-material search to "
                    "the engine (mtk/btk find_unassigned), not re-implement it.",
                )

    def test_option_box_exposes_it(self):
        """tb000 is the configurable form — the mode must be reachable there too."""
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                cls = self._classdef(path)
                init_src = ast.unparse(self._method(cls, "tb000_init"))
                self.assertIn("chk009", init_src, f"{path.name} tb000_init lacks chk009.")
                tb000_src = ast.unparse(self._method(cls, "tb000"))
                self.assertIn(
                    "unassigned=",
                    tb000_src,
                    f"{path.name} tb000 must pass the option-box value through.",
                )


class TestB003IsDefinedOnlyOnce(_AstMixin, unittest.TestCase):
    """The one-shot itself is DCC-agnostic, so it lives on the mixin alone."""

    def test_mixin_defines_b003(self):
        self.assertTrue(callable(getattr(MaterialsMixin, "b003", None)))

    def test_dcc_slots_do_not_redefine_b003(self):
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                self.assertIsNone(
                    self._method(self._classdef(path), "b003"),
                    f"{path.name} must inherit b003 from MaterialsMixin, not redefine it.",
                )


class TestAdoptPathIsSharedNotForked(_AstMixin, unittest.TestCase):
    """Only the lookup forks: each DCC supplies ``_selection_mats``, nothing else."""

    def test_mixin_owns_the_adopt_path(self):
        self.assertTrue(callable(getattr(MaterialsMixin, "_adopt_selection_mat", None)))
        self.assertEqual(
            set(MaterialsMixin._GET_MAT_FAILURES),
            {"empty", "none", "multiple", "filtered"},
        )

    def test_each_dcc_supplies_the_lookup_hook(self):
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                self.assertIsNotNone(
                    self._method(self._classdef(path), "_selection_mats"),
                    f"{path.name} must supply the _selection_mats hook.",
                )

    def test_dcc_slots_do_not_redefine_the_shared_parts(self):
        for path in DCC_FILES:
            for name in ("_adopt_selection_mat", "_GET_MAT_FAILURES"):
                with self.subTest(path=path.name, name=name):
                    cls = self._classdef(path)
                    self.assertIsNone(self._method(cls, name))
                    assigned = {
                        t.id
                        for b in cls.body
                        if isinstance(b, ast.Assign)
                        for t in b.targets
                        if isinstance(t, ast.Name)
                    }
                    self.assertNotIn(name, assigned, f"{path.name} redefines {name}.")

    def test_b002_and_get_first_both_route_through_it(self):
        """The two entry points differ only in their failure message."""
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                cls = self._classdef(path)
                for method_name in ("b002", PRIMITIVE):
                    method = self._method(cls, method_name)
                    self.assertIn(
                        "_adopt_selection_mat",
                        self._self_calls(method),
                        f"{path.name} {method_name} must use the shared adopt path.",
                    )


class TestSubmenuCarriesTheButton(unittest.TestCase):
    """A slot with no widget never fires — pin the .ui and its compiled twin."""

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
