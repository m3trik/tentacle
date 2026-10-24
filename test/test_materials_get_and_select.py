#!/usr/bin/python
# coding=utf-8
"""Tests for the materials submenu's "Get + Select" one-shot (``b003``).

The submenu button gets the material off the current selection and selects every object
using it. The search body is one parameterized per-DCC primitive,
``select_by_mat(shell, in_selection, get_first, add, unassigned)``: the panel's material
table (its Select icon, its row menu), the header's Objects Without Material and the
submenu's ``b003`` (defined ONCE on the DCC-agnostic ``MaterialsMixin``) all call it with
plain values.

The "get the material off the selection" half is shared the same way:
``_adopt_selection_mat(on_failure)`` on the mixin over a ``_selection_mats()`` DCC hook,
serving ``get_first`` (which carries on with the current material and says so). The
current material is a name (``_current_mat``), not a list entry, so a material the table
filters out is adopted all the same.

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
        """The configurable forms are the table's row menu — b003 inherits neither."""
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
        """"No material" must never become the current material."""
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


class _AdoptHost(MaterialsMixin):
    """Host for the shared adopt path — ``_selection_mats`` is the DCC hook. No
    table: the current material exists without one."""

    def __init__(self, mats, current=None):
        self._mats = mats
        self._current = current
        self.messages = []
        self.ui = type("_UI", (), {})()
        self.sb = type("_SB", (), {"message_box": lambda _s, m: self.messages.append(m)})()

    def _selection_mats(self):
        return self._mats


class TestAdoptSelectionMat(unittest.TestCase):
    """One material -> it is current; anything else -> a reason, current untouched."""

    def test_single_material_is_adopted(self):
        host = _AdoptHost(["matA"])
        self.assertEqual(host._adopt_selection_mat(), "matA")
        self.assertEqual(host._current_mat(), "matA")
        self.assertEqual(host.messages, [])

    def test_a_material_no_list_shows_is_adopted_all_the_same(self):
        """The combo could only make current what it listed (a filter, or a
        shader ``cmds.ls(materials=True)`` misses, dead-ended "Get"); a name
        can be current whatever the table shows."""
        host = _AdoptHost(["|grp|matA"], current="matZ")
        self.assertEqual(host._adopt_selection_mat(), "|grp|matA")
        self.assertEqual(host._current_mat(), "|grp|matA")

    def test_nothing_selected_reports_and_keeps_the_current(self):
        host = _AdoptHost(None, current="matZ")
        self.assertIsNone(host._adopt_selection_mat())
        self.assertEqual(host._current_mat(), "matZ")
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
        """get_first carries on with the current material and says so."""
        host = _AdoptHost(None)
        host._adopt_selection_mat(" Proceeding with current material.")
        self.assertTrue(host.messages[0].endswith(" Proceeding with current material."))

    def test_no_failure_text_by_default(self):
        host = _AdoptHost([])
        host._adopt_selection_mat()
        self.assertNotIn("Proceeding", host.messages[0])


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


class TestMayaListFiltersAreDeclaredOnce(_AstMixin, unittest.TestCase):
    """The list filters live in txt000's option box, each declared once and read
    off the widget (a hand-kept copy of a label is free to drift from it)."""

    def test_each_filter_is_declared_once(self):
        source = MAYA_FILE.read_text(encoding="utf-8")
        for label in ("Hide Default Materials", "Hide Arnold Shaders"):
            with self.subTest(label=label):
                self.assertEqual(source.count(f'"{label}"'), 1)

    def test_the_rows_read_both_filters(self):
        src = ast.unparse(self._method(self._classdef(MAYA_FILE), "_material_rows"))
        for name in ("chk_hide_defaults", "chk_hide_arnold"):
            self.assertIn(name, src)


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


class TestUnassignedModeIsWiredInBothDccs(_AstMixin, unittest.TestCase):
    """The no-material search runs through the engines, never the current material."""

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

    def test_the_header_offers_it(self):
        """Objects Without Material (b033, the header menu) is the panel's form."""
        host = _Host()
        host.b033()
        self.assertEqual(len(host.calls), 1)
        self.assertTrue(host.calls[0]["unassigned"])


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
            {"empty", "none", "multiple"},
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

    def test_get_first_routes_through_it(self):
        for path in DCC_FILES:
            with self.subTest(path=path.name):
                method = self._method(self._classdef(path), PRIMITIVE)
                self.assertIn(
                    "_adopt_selection_mat",
                    self._self_calls(method),
                    f"{path.name} {PRIMITIVE} must use the shared adopt path.",
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
