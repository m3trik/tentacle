#!/usr/bin/python
# coding=utf-8
"""Tests for the shared material-rename affix feature (DCC-agnostic).

``tentacle/slots/materials_rename_affix_mixin.py`` holds the prefix/suffix affix
option box mixed into both DCC Materials slots' "Rename" label. The mixin imports
nothing DCC-specific, so the join/validation logic (``_join_affix``) and the apply
handler (``_apply_rename_affix``) are exercised directly here (no ``maya.cmds`` /
``bpy`` needed — this runs everywhere). The per-DCC slots only supply the
``_rename_current`` hook; two AST checks pin that both actually mix the shared
class in, route ``cmb002_init`` through it, and return a value from
``_rename_current`` (the mixin clears the field only on a truthy result).
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots.materials_rename_affix_mixin import (  # noqa: E402
    MaterialsRenameAffixMixin,
)

MAYA_FILE = ROOT / "tentacle" / "slots" / "maya" / "materials.py"
BLENDER_FILE = ROOT / "tentacle" / "slots" / "blender" / "materials.py"


class _FakeField:
    """Stand-in for the affix LineEdit."""

    def __init__(self, text=""):
        self._text = text
        self.cleared = False

    def text(self):
        return self._text

    def clear(self):
        self.cleared = True


class _FakeCombo:
    def __init__(self, value):
        self._value = value
        self.editable = None

    def currentData(self):
        return self._value

    def currentText(self):
        return self._value

    def setEditable(self, value):
        self.editable = value


class _Host(MaterialsRenameAffixMixin):
    """Minimal host wiring the mixin's collaborators without any DCC."""

    def __init__(self, current="mat", rename_result="renamed", affix="", mode="Auto"):
        self._rename_affix = _FakeField(affix)
        self._rename_mode_combo = _FakeCombo(mode)
        self.ui = type("_UI", (), {"cmb002": _FakeCombo(current)})()
        self.rename_calls = []
        self.messages = []
        self._rename_result = rename_result
        self.sb = type(
            "_SB", (), {"message_box": lambda _s, m: self.messages.append(m)}
        )()

    def _rename_current(self, text):
        self.rename_calls.append(text)
        return self._rename_result


class TestJoinAffix(unittest.TestCase):
    """The pure join primitive: mode + underscore-edge convention."""

    join = staticmethod(MaterialsRenameAffixMixin._join_affix)

    def test_auto_leading_underscore_is_suffix(self):
        self.assertEqual(self.join("mat", "_lod0", "Auto"), "mat_lod0")

    def test_auto_trailing_underscore_is_prefix(self):
        self.assertEqual(self.join("mat", "metal_", "Auto"), "metal_mat")

    def test_auto_both_edges_is_none(self):
        self.assertIsNone(self.join("mat", "_x_", "Auto"))

    def test_auto_no_edge_is_none(self):
        self.assertIsNone(self.join("mat", "x", "Auto"))

    def test_prefix_inserts_one_separator(self):
        self.assertEqual(self.join("mat", "metal", "Prefix"), "metal_mat")

    def test_prefix_strips_user_underscores(self):
        # A user-typed underscore must not double up.
        self.assertEqual(self.join("mat", "metal_", "Prefix"), "metal_mat")
        self.assertEqual(self.join("mat", "_metal_", "Prefix"), "metal_mat")

    def test_suffix_inserts_one_separator(self):
        self.assertEqual(self.join("mat", "lod0", "Suffix"), "mat_lod0")

    def test_suffix_strips_user_underscores(self):
        self.assertEqual(self.join("mat", "_lod0", "Suffix"), "mat_lod0")

    def test_explicit_mode_only_underscores_is_none(self):
        self.assertIsNone(self.join("mat", "_", "Prefix"))
        self.assertIsNone(self.join("mat", "___", "Suffix"))


class TestApplyRenameAffix(unittest.TestCase):
    """The handler reads mode + field, commits, and clears only on success."""

    def test_auto_suffix_commits_and_clears(self):
        host = _Host(current="mat", affix="_lod0", mode="Auto")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, ["mat_lod0"])
        self.assertTrue(host._rename_affix.cleared)

    def test_prefix_mode_commits(self):
        host = _Host(current="mat", affix="metal", mode="Prefix")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, ["metal_mat"])

    def test_suffix_mode_commits(self):
        host = _Host(current="mat", affix="lod0", mode="Suffix")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, ["mat_lod0"])

    def test_auto_ambiguous_is_rejected_with_message(self):
        host = _Host(current="mat", affix="x", mode="Auto")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, [])
        self.assertEqual(len(host.messages), 1)

    def test_explicit_empty_token_is_rejected_with_message(self):
        host = _Host(current="mat", affix="_", mode="Prefix")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, [])
        self.assertEqual(len(host.messages), 1)

    def test_empty_field_is_a_noop(self):
        host = _Host(current="mat", affix="   ", mode="Auto")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, [])
        self.assertEqual(host.messages, [])

    def test_no_current_material_is_a_noop(self):
        host = _Host(current=None, affix="_lod0", mode="Auto")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, [])

    def test_failed_rename_keeps_affix(self):
        host = _Host(current="mat", rename_result=None, affix="_lod0", mode="Auto")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, ["mat_lod0"])
        self.assertFalse(host._rename_affix.cleared)

    def test_dag_path_uses_leaf_name(self):
        host = _Host(current="grp|mat", affix="_lod0", mode="Auto")
        host._apply_rename_affix()
        self.assertEqual(host.rename_calls, ["mat_lod0"])


class TestLbl005Trigger(unittest.TestCase):
    """The Rename label applies the affix when the field has text, else makes editable."""

    def test_click_with_affix_applies_it(self):
        host = _Host(current="mat", affix="_lod0", mode="Auto")
        host.lbl005()
        self.assertEqual(host.rename_calls, ["mat_lod0"])
        self.assertIsNone(host.ui.cmb002.editable)  # did NOT fall through to editable

    def test_click_without_affix_makes_editable(self):
        host = _Host(current="mat", affix="", mode="Auto")
        host.lbl005()
        self.assertEqual(host.rename_calls, [])
        self.assertTrue(host.ui.cmb002.editable)

    def test_click_with_whitespace_only_affix_makes_editable(self):
        host = _Host(current="mat", affix="   ", mode="Auto")
        host.lbl005()
        self.assertEqual(host.rename_calls, [])
        self.assertTrue(host.ui.cmb002.editable)


class TestSlotsMixInTheSharedClass(unittest.TestCase):
    """Both DCC slots must mix the shared class in and route through it (AST, import-free)."""

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

    def test_both_slots_mix_in_and_route_through_shared_class(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                cls = self._classdef(path)
                self.assertIsNotNone(cls, f"MaterialsSlots not found in {path.name}")
                base_names = {b.id for b in cls.bases if isinstance(b, ast.Name)}
                self.assertIn(
                    "MaterialsRenameAffixMixin",
                    base_names,
                    f"{path.name} MaterialsSlots must mix in MaterialsRenameAffixMixin.",
                )
                init = self._method(cls, "cmb002_init")
                self.assertIsNotNone(init, f"cmb002_init not found in {path.name}")
                calls = {
                    n.func.attr
                    for n in ast.walk(init)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                }
                self.assertIn(
                    "_add_rename_control",
                    calls,
                    f"{path.name} cmb002_init must build the control via self._add_rename_control.",
                )

    def test_both_rename_current_return_a_value(self):
        """The mixin clears the field only on a truthy _rename_current result, so each
        DCC's _rename_current must return the resulting name (not bare return/None)."""
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                cls = self._classdef(path)
                method = self._method(cls, "_rename_current")
                self.assertIsNotNone(method, f"_rename_current not found in {path.name}")
                self.assertTrue(
                    any(
                        isinstance(n, ast.Return) and n.value is not None
                        for n in ast.walk(method)
                    ),
                    f"{path.name} _rename_current must return the resulting name on success.",
                )


if __name__ == "__main__":
    unittest.main()
