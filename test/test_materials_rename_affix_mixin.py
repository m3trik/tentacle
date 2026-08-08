#!/usr/bin/python
# coding=utf-8
"""Tests for the shared ``cmb002`` wiring on ``MaterialsMixin`` (DCC-agnostic).

``tentacle/slots/_materials.py`` holds ``MaterialsMixin`` — the shared, DCC-agnostic
``materials`` slot behavior. Two features hang off the materials combo and are covered
here:

- the prefix/suffix affix option box mixed into both DCC Materials slots' "Rename" label
  (``_join_affix`` / ``_apply_rename_affix``);
- ``_refresh_assign_lists``, which re-inits the Assign list (``list000``) on BOTH the
  panel and the submenu when the current material changes, so each list keeps matching
  what releasing on it will assign, plus ``_assign_root_text``, the per-surface wording
  of that root row ("Assign: <current>" on the free-floating submenu; a bare "Assign
  Current" on the panel, where ``cmb002`` already names the material).

The mixin imports nothing DCC-specific, so both are exercised directly here (no
``maya.cmds`` / ``bpy`` needed — this runs everywhere). The per-DCC slots only supply
the ``_rename_current`` hook; AST checks pin that both actually mix the shared class in,
route ``cmb002_init`` through it, connect the combo's change signals to the shared
refresh, and return a value from ``_rename_current`` (the mixin clears the field only on
a truthy result).
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
    def __init__(self, value, log=None):
        self._value = value
        self.editable = None
        # Shared ordered log, so tests can assert the combo is re-populated
        # BEFORE the Assign lists that read currentData() off it.
        self.log = [] if log is None else log

    def currentData(self):
        return self._value

    def currentText(self):
        return self._value

    def setEditable(self, value):
        self.editable = value

    def init_slot(self, *args):
        self.log.append("cmb002")


class _Host(MaterialsMixin):
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

    join = staticmethod(MaterialsMixin._join_affix)

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


def _classdef(path, name="MaterialsSlots"):
    """The named ClassDef in *path*, or None."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(
        (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == name),
        None,
    )


def _method(classdef, name):
    """The named method on *classdef*, or None."""
    return next(
        (
            b
            for b in classdef.body
            if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and b.name == name
        ),
        None,
    )


class TestSlotsMixInTheSharedClass(unittest.TestCase):
    """Both DCC slots must mix the shared class in and route through it (AST, import-free)."""

    _classdef = staticmethod(_classdef)
    _method = staticmethod(_method)

    def test_both_slots_mix_in_and_route_through_shared_class(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                cls = self._classdef(path)
                self.assertIsNotNone(cls, f"MaterialsSlots not found in {path.name}")
                base_names = {b.id for b in cls.bases if isinstance(b, ast.Name)}
                self.assertIn(
                    "MaterialsMixin",
                    base_names,
                    f"{path.name} MaterialsSlots must mix in MaterialsMixin.",
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

    def test_both_slots_refresh_the_assign_lists_on_material_change(self):
        """cmb002's change signals must drive the shared _refresh_assign_lists.

        The original wiring connected them to ``self.submenu.list000.init_slot``,
        which refreshed only ONE of the two Assign lists — the panel hosts a
        ``list000`` too, and it is the surface sitting right under the combo. Pin
        both signals to the shared helper so neither root row can go stale.
        """
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                init = self._method(self._classdef(path), "cmb002_init")
                self.assertIsNotNone(init, f"cmb002_init not found in {path.name}")

                refreshed = {
                    n.func.value.attr
                    for n in ast.walk(init)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "connect"
                    and isinstance(n.func.value, ast.Attribute)
                    and len(n.args) == 1
                    and isinstance(n.args[0], ast.Attribute)
                    and n.args[0].attr == "_refresh_assign_lists"
                }
                for signal in ("currentIndexChanged", "on_editing_finished"):
                    self.assertIn(
                        signal,
                        refreshed,
                        f"{path.name} cmb002_init must connect {signal} to "
                        "self._refresh_assign_lists.",
                    )


class _FakeList:
    """Stand-in for an ExpandableList; records init_slot calls."""

    def __init__(self, name="list000", log=None):
        self.init_count = 0
        self._name = name
        self.log = [] if log is None else log

    def init_slot(self, *args):
        self.init_count += 1
        self.log.append(self._name)


def _assign_host(panel_list=True, submenu_list=True):
    """A mixin host with an Assign list on each surface, sharing one call log."""
    host = _Host()
    log = host.ui.cmb002.log
    if panel_list:
        host.ui.list000 = _FakeList("panel", log)
    host.submenu = type("_Submenu", (), {})()
    if submenu_list:
        host.submenu.list000 = _FakeList("submenu", log)
    return host


class TestRefreshAssignLists(unittest.TestCase):
    """_refresh_assign_lists re-inits every surface's Assign list, tolerating absence."""

    _host = staticmethod(_assign_host)

    def test_refreshes_both_surfaces(self):
        """The panel's own list000 is refreshed too — the bug was that only the
        submenu's was, leaving 'Assign: <old material>' above the changed combo."""
        host = self._host()
        host._refresh_assign_lists()
        self.assertEqual(host.ui.list000.init_count, 1)
        self.assertEqual(host.submenu.list000.init_count, 1)

    def test_swallows_signal_arguments(self):
        """Connected straight to currentIndexChanged(int) / on_editing_finished(str)."""
        host = self._host()
        host._refresh_assign_lists(3)
        host._refresh_assign_lists("lambert1")
        self.assertEqual(host.ui.list000.init_count, 2)
        self.assertEqual(host.submenu.list000.init_count, 2)

    def test_surface_without_an_assign_list_is_skipped(self):
        host = self._host(panel_list=False)
        host._refresh_assign_lists()  # must not raise
        self.assertEqual(host.submenu.list000.init_count, 1)


class TestRefreshMaterialLists(unittest.TestCase):
    """_refresh_material_lists is the 'the scene's materials changed' signal.

    Every create / delete / rename path must go through it: each Assign list
    carries a row per scene material, so a combo-only refresh left rows naming
    materials that no longer exist (a dead menu row — "Assign failed" in Maya,
    a silent no-op in Blender).
    """

    def test_repopulates_the_combo_and_both_lists(self):
        host = _assign_host()
        host._refresh_material_lists()
        self.assertEqual(host.ui.list000.init_count, 1)
        self.assertEqual(host.submenu.list000.init_count, 1)

    def test_combo_is_repopulated_before_the_lists(self):
        """The lists' root row is built from cmb002.currentData(), so the combo
        must be re-resolved against the new material set first."""
        host = _assign_host()
        host._refresh_material_lists()
        self.assertEqual(host.ui.cmb002.log, ["cmb002", "panel", "submenu"])


class TestMutatorsRefreshBothWidgets(unittest.TestCase):
    """No fork may re-populate cmb002 alone after changing the material set."""

    #: The one legitimate bare ``cmb002.init_slot()``: ``list000_init``
    #: bootstraps the combo so it can read ``currentData()``, and is already
    #: building the list it would otherwise be told to refresh.
    _BOOTSTRAP = "list000_init"

    def test_no_slot_repopulates_the_combo_alone(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            cls = _classdef(path)
            for method in cls.body:
                if not isinstance(method, ast.FunctionDef):
                    continue
                if method.name == self._BOOTSTRAP:
                    continue
                with self.subTest(path=path.name, method=method.name):
                    bare = [
                        n.lineno
                        for n in ast.walk(method)
                        if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "init_slot"
                        and isinstance(n.func.value, ast.Attribute)
                        and n.func.value.attr == "cmb002"
                    ]
                    self.assertEqual(
                        bare,
                        [],
                        f"{path.name}:{bare} {method.name} calls cmb002.init_slot() "
                        "directly — use self._refresh_material_lists() so the Assign "
                        "lists don't keep rows for materials that no longer exist.",
                    )


class _FakeListWidget:
    """Stand-in for a hosted ExpandableList: only its surface's tags matter."""

    class _Surface:
        def __init__(self, tags):
            self._tags = tags

        def has_tags(self, tag):
            return tag in self._tags

    def __init__(self, submenu):
        self.ui = self._Surface({"submenu"} if submenu else set())


class TestAssignRootText(unittest.TestCase):
    """The Assign list's root row is worded per surface.

    The submenu floats free of the panel, so its root is the only thing there
    naming what a release will assign. The panel's list sits directly under
    cmb002, which already shows the name — so the row states the action only.
    """

    def test_submenu_names_the_current_material(self):
        host = _Host(current="metal_mat")
        self.assertEqual(
            host._assign_root_text(_FakeListWidget(submenu=True)), "Assign: metal_mat"
        )

    def test_panel_omits_the_material_name(self):
        """cmb002 sits right above it — repeating the name is redundant."""
        host = _Host(current="metal_mat")
        text = host._assign_root_text(_FakeListWidget(submenu=False))
        self.assertEqual(text, "Assign Current")
        self.assertNotIn("metal_mat", text)

    def test_panel_wording_is_independent_of_the_current_material(self):
        """No material current -> still 'Assign Current' (the row is the action)."""
        host = _Host(current=None)
        self.assertEqual(
            host._assign_root_text(_FakeListWidget(submenu=False)), "Assign Current"
        )

    def test_submenu_falls_back_when_nothing_is_current(self):
        host = _Host(current=None)
        self.assertEqual(host._assign_root_text(_FakeListWidget(submenu=True)), "Assign")

    def test_submenu_names_the_material_the_way_the_combo_does(self):
        """cmb002's item text is the leaf, its data the full name — the row
        mirrors the combo, so it must not spell the same material differently."""
        host = _Host(current="grp|metal_mat")
        self.assertEqual(
            host._assign_root_text(_FakeListWidget(submenu=True)), "Assign: metal_mat"
        )


class TestForksBuildTheRootThroughTheMixin(unittest.TestCase):
    """Neither list000_init may re-inline the root label.

    Both forks built the same "Assign: <current>" string; the panel/submenu
    split now lives in the mixin, so a fork spelling its own root would let the
    two surfaces drift apart again.
    """

    def test_list000_init_calls_the_shared_helper(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                init = _method(_classdef(path), "list000_init")
                self.assertIsNotNone(init, f"list000_init not found in {path.name}")
                calls = {
                    n.func.attr
                    for n in ast.walk(init)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                }
                self.assertIn(
                    "_assign_root_text",
                    calls,
                    f"{path.name} list000_init must build the root row via "
                    "self._assign_root_text(widget).",
                )

    def test_no_fork_spells_its_own_root_label(self):
        """The root is ``widget.add(...)``: its label must be computed, not literal.

        Pinned on that call rather than on 'no Assign-ish string anywhere in the
        method', which would also fire on a legitimate sublist row — the leaves
        (``root.sublist.add("New")``) are literals by design.

        The argument is WALKED for string constants rather than type-checked at
        its root: the label both forks used to build was
        ``f"Assign: {current}" if current else "Assign"``, whose top-level node
        is an ``IfExp``, so a shallow check waved that exact regression through.
        """
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                init = _method(_classdef(path), "list000_init")
                literal_roots = [
                    n.lineno
                    for n in ast.walk(init)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "add"
                    and isinstance(n.func.value, ast.Name)
                    and n.func.value.id == "widget"
                    and n.args
                    and any(
                        isinstance(sub, ast.Constant) and isinstance(sub.value, str)
                        for sub in ast.walk(n.args[0])
                    )
                ]
                self.assertEqual(
                    literal_roots,
                    [],
                    f"{path.name}:{literal_roots} list000_init spells its own root "
                    "label — the wording belongs to the mixin's _assign_root_text.",
                )


class TestBothSurfacesHaveAnAssignList(unittest.TestCase):
    """_refresh_assign_lists skips a surface without a list000 — but both have one.

    The guard is there so the mixin can't crash on a surface that legitimately
    lacks the widget; it must not quietly paper over the widget going missing
    from a .ui, which would silently restore the stale-root-row bug.
    """

    UI_DIR = ROOT / "tentacle" / "ui"

    def test_list000_exists_in_both_materials_ui_files(self):
        for name in ("materials.ui", "materials#submenu.ui"):
            with self.subTest(ui=name):
                path = self.UI_DIR / name
                names = {
                    el.get("name")
                    for el in ET.parse(path).getroot().iter("widget")
                }
                self.assertIn(
                    "list000",
                    names,
                    f"{name} must host the Assign list (list000) — "
                    "_refresh_assign_lists keeps both surfaces' root rows in sync.",
                )


if __name__ == "__main__":
    unittest.main()
