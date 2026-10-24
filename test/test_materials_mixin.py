#!/usr/bin/python
# coding=utf-8
"""Tests for the materials panel's shared half, ``MaterialsMixin`` (DCC-agnostic).

The panel is a material table (``tbl000``): one row per material, its swatch and name,
optional Type / Users / Textures columns, then Status / Select / Assign icon columns, a
filter field (``txt000``) and + (``b006``) above it, a summary in the footer. The table,
the current material, the row menu, the status fixes and the header menu all live on the
mixin; each DCC fork supplies only the data hooks.

Two halves here:

- AST / XML pins (import-free — the DCC modules need ``maya.cmds`` / ``bpy``): both forks
  mix the shared class in, supply every hook, and no longer reach for the retired
  ``cmb002`` combo; the ``.ui`` carries the table and the submenu keeps its Assign list.
- The table itself, acted on in offscreen Qt over a fake DCC host: the cells are clicked,
  the filter typed into, a name edited, the row menu fitted, as a user would.

Added: 2026-10-22 (replaces the combo-era cmb002 wiring tests).
"""
import ast
import os
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tentacle.slots._materials import MaterialsMixin  # noqa: E402

MAYA_FILE = ROOT / "tentacle" / "slots" / "maya" / "materials.py"
BLENDER_FILE = ROOT / "tentacle" / "slots" / "blender" / "materials.py"
MIXIN_FILE = ROOT / "tentacle" / "slots" / "_materials.py"
UI_DIR = ROOT / "tentacle" / "ui"

#: What each fork supplies the mixin.
HOOKS = (
    "_material_rows",
    "_material_icon",
    "_script_job_manager",
    "_material_facts",
    "_duplicate_pairs",
    "_selected_mat_names",
    "_selection_mats",
    "_assign_named",
    "_delete_materials",
    "_merge_duplicates",
    "_rename_current",
    "select_by_mat",
    "lbl004",
    "lbl006",
    "b010",
)


def _classdef(path, name="MaterialsSlots"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(
        (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == name),
        None,
    )


def _method(classdef, name):
    return next(
        (
            b
            for b in classdef.body
            if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and b.name == name
        ),
        None,
    )


class TestForksSupplyTheHooks(unittest.TestCase):
    """Both forks mix the shared class in and supply every hook it calls."""

    def test_both_mix_in_the_shared_class(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                bases = {b.id for b in _classdef(path).bases if isinstance(b, ast.Name)}
                self.assertIn("MaterialsMixin", bases)

    def test_every_hook_is_supplied(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            cls = _classdef(path)
            for hook in HOOKS:
                with self.subTest(path=path.name, hook=hook):
                    self.assertIsNotNone(_method(cls, hook), f"{path.name} lacks {hook}")

    def test_rename_current_returns_the_name(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                method = _method(_classdef(path), "_rename_current")
                self.assertTrue(
                    any(isinstance(n, ast.Return) and n.value is not None
                        for n in ast.walk(method))
                )

    def test_the_shared_parts_are_not_forked(self):
        """The table, the row menu and the header are the mixin's alone."""
        for path in (MAYA_FILE, BLENDER_FILE):
            cls = _classdef(path)
            for name in ("tbl000_init", "header_init", "lbl002", "b003", "list001_init",
                         "_adopt_selection_mat", "_set_current", "_current_mat",
                         "b014", "_material_details", "_material_issue"):
                with self.subTest(path=path.name, name=name):
                    self.assertIsNone(_method(cls, name), f"{path.name} forks {name}")

    def test_the_forks_report_facts_and_never_word_an_issue(self):
        """The issue's precedence and wording live once, on the mixin.
        Added: 2026-10-24"""
        for path in (MAYA_FILE, BLENDER_FILE):
            text = path.read_text(encoding="utf-8")
            for wording in ("is missing", "A duplicate of", "Nothing uses it", "more)"):
                with self.subTest(path=path.name, wording=wording):
                    self.assertNotIn(wording, text)

    def test_no_slot_reaches_for_the_retired_combo(self):
        for path in (MAYA_FILE, BLENDER_FILE, MIXIN_FILE):
            with self.subTest(path=path.name):
                self.assertNotIn("cmb002", path.read_text(encoding="utf-8"))


class TestPanelUi(unittest.TestCase):
    """The panel carries the table; the submenu keeps its compact surface."""

    @staticmethod
    def _names(ui_name):
        return {w.get("name") for w in ET.parse(UI_DIR / ui_name).getroot().iter("widget")}

    def test_the_panel_is_a_filtered_table(self):
        names = self._names("materials.ui")
        self.assertLessEqual({"header", "txt000", "b006", "tbl000", "footer"}, names)
        for retired in ("cmb002", "b002", "tb000", "list000", "list001", "group000"):
            self.assertNotIn(retired, names, retired)

    def test_the_submenu_keeps_assign_get_and_tools(self):
        self.assertLessEqual({"list000", "list001", "b003"}, self._names("materials#submenu.ui"))

    def test_the_compiled_twin_is_in_sync(self):
        compiled = UI_DIR / "materials_ui.py"
        if not compiled.exists():
            self.skipTest("materials_ui.py not built in this checkout")
        text = compiled.read_text(encoding="utf-8")
        self.assertIn("tbl000", text, "run `python -m uitk.compile tentacle/ui/materials.ui`")
        self.assertNotIn("cmb002", text)


class _FakeListWidget:
    class _Surface:
        def __init__(self, tags):
            self._tags = tags

        def has_tags(self, tag):
            return tag in self._tags

    def __init__(self, submenu):
        self.ui = self._Surface({"submenu"} if submenu else set())


class TestAssignRootText(unittest.TestCase):
    """The submenu's Assign root names the current material by its leaf."""

    def _host(self, current):
        host = MaterialsMixin()
        host._current = current
        return host

    def test_names_the_current_material(self):
        host = self._host("metal_mat")
        self.assertEqual(host._assign_root_text(_FakeListWidget(True)), "Assign: metal_mat")

    def test_by_its_leaf(self):
        host = self._host("grp|metal_mat")
        self.assertEqual(host._assign_root_text(_FakeListWidget(True)), "Assign: metal_mat")

    def test_falls_back_with_nothing_current(self):
        self.assertEqual(self._host(None)._assign_root_text(_FakeListWidget(True)), "Assign")

    def test_list000_init_builds_the_root_through_it(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(path=path.name):
                init = _method(_classdef(path), "list000_init")
                calls = {
                    n.func.attr for n in ast.walk(init)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                }
                self.assertIn("_assign_root_text", calls)


def _facts(missing=(), duplicate_of=None, unused=False):
    return {"type": "lambert", "users": 0, "textures": len(missing),
            "missing": list(missing), "duplicate_of": duplicate_of, "unused": unused}


class TestTheIssueIsJudgedOnce(unittest.TestCase):
    """The forks report raw facts; the mixin picks the one issue to show -- a
    missing texture, then a duplicate, then nothing using it -- and words it.
    Added: 2026-10-24 (both forks carried a copy of this)."""

    @staticmethod
    def issue(facts):
        return MaterialsMixin._material_issue(facts)

    def test_nothing_wrong_is_no_issue(self):
        self.assertIsNone(self.issue(_facts()))

    def test_a_missing_texture_comes_first(self):
        self.assertEqual(
            self.issue(_facts(["a.png", "b.png", "c.png"], duplicate_of="X", unused=True)),
            ("missing", "a.png is missing (and 2 more)", None),
        )
        self.assertEqual(
            self.issue(_facts(["a.png"])), ("missing", "a.png is missing", None)
        )

    def test_then_a_duplicate_then_unused(self):
        self.assertEqual(
            self.issue(_facts(duplicate_of="Crate", unused=True)),
            ("duplicate", "A duplicate of Crate", "Crate"),
        )
        self.assertEqual(self.issue(_facts(unused=True)), ("unused", "Nothing uses it", None))

    def test_the_details_carry_the_judged_issue(self):
        class _Host(MaterialsMixin):
            def _material_facts(self, names):
                return {n: _facts(duplicate_of="Crate") for n in names}

        details = _Host()._material_details(["Crate1"])
        self.assertEqual(details["Crate1"]["issue"], ("duplicate", "A duplicate of Crate", "Crate"))
        self.assertEqual(details["Crate1"]["type"], "lambert")


class TestRemoveDuplicateMaterials(unittest.TestCase):
    """The header's Remove Duplicate Materials (``b014``), shared: it reports what
    the merge removed, not what the finder found -- a merge can refuse a pair
    (Maya: the original has no shading engine; a merge that fails only warns).
    Added: 2026-10-24"""

    class _Host(MaterialsMixin):
        def __init__(self, pairs, merged):
            self.pairs, self.merged, self.calls, self.messages = pairs, merged, [], []
            self.ui = type("_UI", (), {})()
            self.sb = type("_SB", (), {"message_box": lambda _s, m: self.messages.append(m)})()

        def _duplicate_pairs(self, names=None):
            self.calls.append(("find", names))
            return dict(self.pairs)

        def _merge_duplicates(self, pairs):
            self.calls.append(("merge", dict(pairs)))
            return self.merged

    def test_it_reports_what_the_merge_removed(self):
        host = self._Host({"Crate1": "Crate", "Crate2": "Crate"}, merged=1)
        host.b014()
        self.assertEqual(
            host.calls,
            [("find", None), ("merge", {"Crate1": "Crate", "Crate2": "Crate"})],
        )
        self.assertEqual(host.messages, ["Removed <hl>1</hl> duplicate material."])

    def test_none_found_merges_nothing(self):
        host = self._Host({}, merged=0)
        host.b014()
        self.assertEqual(host.calls, [("find", None)])
        self.assertEqual(host.messages, ["No duplicate-texture materials found."])


try:
    from qtpy import QtCore, QtTest, QtWidgets

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from uitk.widgets.expandableList import ExpandableList
    from uitk.widgets.footer import Footer
    from uitk.widgets.header import Header
    from uitk.widgets.lineEdit import LineEdit
    from uitk.managers.icon_manager import IconManager
    from uitk.widgets.tableWidget import TableWidget

    from tentacle.slots._slots import Slots

    HAVE_QT = True
except Exception:  # noqa: BLE001 -- the import-free half still runs
    HAVE_QT = False


if HAVE_QT:

    class _Window(QtWidgets.QMainWindow):
        """The panel window: what the mixin reads off ``self.ui``."""

        on_activated = QtCore.Signal()

        def has_tags(self, tag):
            return False

    class _Jobs:
        """A ScriptJobManager stand-in: records subscriptions, fires events."""

        def __init__(self):
            self.subs = []

        def instance(self):
            return self

        def subscribe(self, event, callback, owner=None, ephemeral=False):
            self.subs.append((event, callback, owner))

        def unsubscribe_all(self, owner):
            self.subs = [s for s in self.subs if s[2] is not owner]

        def connect_cleanup(self, widget, owner):
            pass

        def fire(self, event):
            for name, callback, _owner in list(self.subs):
                if name == event:
                    callback()

    class _PanelHost(MaterialsMixin):
        """A fake DCC fork: four materials, each with what it needs to show.

        ``Crate`` is fine, ``Crate1`` duplicates it, ``Old`` is unused, ``Wood``
        misses a texture. Every hook records what it was asked.
        """

        _TOOLS_ITEMS = {
            "Setup": [("Texture Path Editor", "b010", "")],
            "Utilities": [("Reload Scene Textures", "b013", "")],
        }
        _EXTERNAL_APP_GATES = {}

        def __init__(self):
            self.calls = []
            self.messages = []
            self.jobs = _Jobs()
            self.on_selection = {"Crate"}
            self.unused = {"Old"}
            self.ui = _Window()
            central = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(central)
            self.ui.txt000 = LineEdit()
            self.ui.tbl000 = TableWidget()
            self.ui.footer = Footer()
            for widget in (self.ui.txt000, self.ui.tbl000, self.ui.footer):
                layout.addWidget(widget)
            self.ui.setCentralWidget(central)
            self.ui.resize(320, 260)
            self.ui.tbl000.is_initialized = False
            self.sb = type(
                "_SB",
                (),
                {
                    "QtWidgets": QtWidgets,
                    "QtCore": QtCore,
                    "IconManager": IconManager,
                    "registered_widgets": type(
                        "_W", (), {"ExpandableList": ExpandableList}
                    ),
                    "message_box": lambda _s, m: self.messages.append(m),
                },
            )()
            self.rows = ["Crate", "Crate1", "Old", "Wood"]

        # -- the DCC hooks
        def _material_rows(self):
            return [{"name": n, "label": n} for n in self.rows]

        def _material_icon(self, name):
            return None

        def _script_job_manager(self):
            return self.jobs

        def _material_facts(self, names):
            return {
                n: {"type": "lambert", "users": 0 if n == "Old" else 2, "textures": 1,
                    "missing": ["Wood_BaseColor.png"] if n == "Wood" else [],
                    "duplicate_of": "Crate" if n == "Crate1" else None,
                    "unused": n in self.unused}
                for n in names
            }

        def _duplicate_pairs(self, names=None):
            return {"Crate1": "Crate"} if "Crate1" in self.rows else {}

        def _selected_mat_names(self):
            return sorted(self.on_selection)

        def _selection_mats(self):
            return sorted(self.on_selection)

        def _assign_named(self, name):
            self.calls.append(("assign", name))
            self._set_current(name)

        def _delete_materials(self, names):
            self.calls.append(("delete", list(names)))
            self.rows = [n for n in self.rows if n not in names]

        def _merge_duplicates(self, pairs):
            self.calls.append(("merge", dict(pairs)))
            self.rows = [n for n in self.rows if n not in pairs]
            return len(pairs)

        def _rename_current(self, text):
            self.calls.append(("rename", self._current_mat(), text))
            self.rows = [text if n == self._current_mat() else n for n in self.rows]
            self._current = text
            self._refresh_material_lists()
            return text

        def select_by_mat(self, shell=False, in_selection=False, get_first=False,
                          add=False, unassigned=False):
            if get_first and not unassigned:  # as both forks do
                self._adopt_selection_mat()
            self.calls.append(("select", self._current_mat(), dict(
                shell=shell, in_selection=in_selection, add=add, unassigned=unassigned)))
            return []

        def lbl004(self, widget=None):
            self.calls.append(("node", self._current_mat()))

        def lbl006(self, widget=None):
            self.calls.append(("editor", self._current_mat()))

        def b010(self, widget=None):
            self.calls.append(("texture_path_editor", self._current_mat()))

        def b013(self, widget=None):
            self.calls.append(("reload",))

        def b004(self, widget=None):
            self.calls.append(("random",))

        def _new_mat(self):
            self.calls.append(("new",))

        # -- what tentacle's Slots base supplies
        _call_slot = staticmethod(Slots._call_slot)

        def add_slot_widget(self, sublist, **kwargs):
            return sublist.add(kwargs.get("setText", ""))

        def gate_on_app(self, widget, resolve_spec):
            return True


@unittest.skipUnless(HAVE_QT, "Qt / uitk unavailable")
class TestMaterialTable(unittest.TestCase):
    """The table, acted on: what a click, a keystroke and an edit do."""

    def setUp(self):
        self.host = _PanelHost()
        self.table = self.host.ui.tbl000
        self.host.txt000_init(self.host.ui.txt000)
        self.host.tbl000_init(self.table)
        self.host.ui.show()
        self._settle()

    def tearDown(self):
        self.host.ui.close()
        self.host.ui.deleteLater()
        self._settle()

    @staticmethod
    def _settle():
        app = QtWidgets.QApplication.instance()
        for _ in range(3):
            app.processEvents()

    def _row(self, name):
        return self.host._row_of(name)

    def _click(self, name, col, modifier=QtCore.Qt.NoModifier):
        index = self.table.model().index(self._row(name), col)
        self.table.scrollTo(index)
        point = self.table.visualRect(index).center()
        QtTest.QTest.mouseClick(self.table.viewport(), QtCore.Qt.LeftButton, modifier, point)
        self._settle()

    def test_each_material_is_a_row_and_the_details_follow(self):
        names = [self.table.item(r, 0).text() for r in range(self.table.rowCount())]
        self.assertEqual(names, ["Crate", "Crate1", "Old", "Wood"])
        self.assertEqual(self.table.item(self._row("Old"), self.host.COL_USERS).text(), "0")
        self.assertEqual(
            self.host._ICON_HEADERS,
            {c: self.table.horizontalHeaderItem(c).toolTip() for c in (4, 5, 6)},
            "an icon column is named by its header tooltip in the column menu",
        )

    def test_the_status_column_flags_only_what_needs_attention(self):
        states = {
            name: self.table.actions.get(self._row(name), self.host.COL_STATUS)
            for name in self.host.rows
        }
        self.assertEqual(
            states, {"Crate": None, "Crate1": "duplicate", "Old": "unused", "Wood": "missing"}
        )
        tip = self.table.item(self._row("Crate1"), self.host.COL_STATUS).toolTip()
        self.assertIn("A duplicate of Crate", tip)
        footer = self.host.ui.footer
        self.assertEqual(
            footer._status_text, "4 materials · 1 missing · 1 duplicate · 1 unused"
        )
        self.assertEqual(footer._status_level, "error", "a missing texture is red")

    def test_the_assign_icon_assigns_that_rows_material(self):
        self._click("Old", self.host.COL_ASSIGN)
        self.assertEqual(self.host.calls, [("assign", "Old")])

    def test_alt_assign_assigns_a_new_random_material(self):
        self._click("Old", self.host.COL_ASSIGN, QtCore.Qt.AltModifier)
        self.assertEqual(self.host.calls, [("random",)])

    def test_the_new_button_makes_a_new_material_and_alt_a_random_one(self):
        button = QtWidgets.QPushButton()
        button.clicked.connect(lambda: self.host.b006(button))
        for modifier, expected in (
            (QtCore.Qt.NoModifier, ("new",)),
            (QtCore.Qt.AltModifier, ("random",)),
        ):
            with self.subTest(modifier=modifier):
                self.host.calls.clear()
                QtTest.QTest.mouseClick(button, QtCore.Qt.LeftButton, modifier)
                self._settle()
                self.assertEqual(self.host.calls, [expected])

    def _names(self):
        return [self.table.item(r, 0).text() for r in range(self.table.rowCount())]

    def _wait_for_refill(self):
        QtTest.QTest.qWait(self.host._REFILL_DELAY_MS * 3)
        self._settle()

    def test_an_undo_or_a_scene_opened_refills_it(self):
        for event in ("Undo", "Redo", "SceneOpened", "NewSceneOpened"):
            with self.subTest(event=event):
                self.host.rows = self.host.rows + [event]
                self.host.jobs.fire(event)
                self._wait_for_refill()
                self.assertEqual(self._names()[-1], event)

    def test_an_undo_burst_refills_once(self):
        """A held Ctrl+Z: one refill when the burst settles, not one per step.
        Added: 2026-10-24"""
        fills = []
        fill = self.host._fill_materials
        self.host._fill_materials = lambda *a, **k: (fills.append(1), fill(*a, **k))
        self.host.rows = ["Crate", "Wood"]
        for _ in range(5):
            self.host.jobs.fire("Undo")
            self._settle()
        self.assertEqual(fills, [], "not while the burst lasts")
        self._wait_for_refill()
        self.assertEqual(len(fills), 1)
        self.assertEqual(self._names(), ["Crate", "Wood"])

    def test_hidden_it_waits_for_the_next_show(self):
        self.host.ui.hide()
        self.host.rows = ["Crate"]
        self.host.jobs.fire("Undo")
        self._wait_for_refill()
        self.assertEqual(len(self._names()), 4)

    def test_an_actions_report_survives_the_activation_its_menu_hands_back(self):
        """A row menu closing hands activation back to the panel, before or after
        the refill's queued details pass runs: the action's report stays, until
        the next refill brings the summary back.
        Added: 2026-10-24 (the activation's re-read replaced the report)."""
        for activation_first in (True, False):
            with self.subTest(activation_first=activation_first):
                self.host.rows = ["Crate", "Crate1", "Old", "Wood"]
                self.host._refresh_material_lists()
                self._settle()
                self.host._set_current("Old")
                self.host.lbl002()  # Delete, from the row menu
                if activation_first:
                    self.host.ui.on_activated.emit()
                    self._settle()
                else:
                    self._settle()
                    self.host.ui.on_activated.emit()
                    self._settle()
                footer = self.host.ui.footer
                self.assertEqual(footer.statusText(), "Deleted 1 material (Undo restores).")
                self.host._refresh_material_lists()
                self._settle()
                self.assertTrue(footer.statusText().startswith("3 materials"))

    def test_an_activation_after_the_report_still_rereads_the_rows(self):
        """Keeping the report keeps the footer only: the status catches up."""
        self.host._set_current("Wood")
        self.host.lbl002()
        self._settle()
        self.host.unused = set()  # Old got assigned from the viewport
        self.host.ui.on_activated.emit()
        self._settle()
        self.assertIsNone(self.table.actions.get(self._row("Old"), self.host.COL_STATUS))
        self.assertEqual(
            self.host.ui.footer.statusText(), "Deleted 1 material (Undo restores)."
        )

    def test_the_mark_follows_the_selection(self):
        self.host.on_selection = {"Wood"}
        self.host.jobs.fire("SelectionChanged")
        bold = [n for n in self.host.rows
                if self.table.item(self._row(n), 0).font().bold()]
        self.assertEqual(bold, ["Wood"])

    def test_activation_refills_a_changed_set(self):
        """A material another tool made meanwhile."""
        self.host.rows = self.host.rows + ["FromHypershade"]
        self.host.ui.on_activated.emit()
        self.assertIn("FromHypershade", self._names())

    def test_activation_rereads_the_details_in_place(self):
        """The same set: rows stay put (the activating click lands where it
        aimed), the status catches up."""
        item = self.table.item(0, 0)
        self.host.unused = set()  # Old got assigned from the viewport
        self.host.ui.on_activated.emit()
        self.assertIs(self.table.item(0, 0), item, "not rebuilt")
        self.assertIsNone(self.table.actions.get(self._row("Old"), self.host.COL_STATUS))

    def test_the_header_refresh_button_refills(self):
        header = Header()
        self.host.header_init(header)
        self.host.rows = ["Crate"]
        header.refresh_requested.emit()
        self.assertEqual(self._names(), ["Crate"])

    def test_the_select_icon_selects_its_users_and_shift_adds(self):
        self._click("Wood", self.host.COL_SELECT)
        self._click("Crate", self.host.COL_SELECT, QtCore.Qt.ShiftModifier)
        selects = [c for c in self.host.calls if c[0] == "select"]
        self.assertEqual([(c[1], c[2]["add"]) for c in selects], [("Wood", False), ("Crate", True)])

    def test_a_status_icon_fixes_what_it_flags(self):
        self._click("Wood", self.host.COL_STATUS)
        self._click("Crate1", self.host.COL_STATUS)
        self._click("Old", self.host.COL_STATUS)
        self.assertEqual(
            self.host.calls,
            [
                ("texture_path_editor", "Wood"),
                ("merge", {"Crate1": "Crate"}),
                ("delete", ["Old"]),
            ],
        )
        self.assertEqual(self.host.rows, ["Crate", "Wood"], "the table refills")
        self.assertEqual(
            self.host.ui.footer._status_text,
            "Deleted 1 material (Undo restores).",
            "the action's own report, not the refill's summary",
        )

    def test_a_merge_the_verification_refuses_says_so(self):
        self.host._merge_duplicates = lambda pairs: 0
        self._click("Crate1", self.host.COL_STATUS)
        self.assertEqual(
            self.host.ui.footer._status_text,
            "Nothing merged: on a closer look the textures differ.",
        )

    def test_a_row_with_nothing_to_fix_does_nothing(self):
        self._click("Crate", self.host.COL_STATUS)
        self.assertEqual(self.host.calls, [])

    def test_the_filter_hides_what_it_does_not_match(self):
        QtTest.QTest.keyClicks(self.host.ui.txt000, "cra")
        shown = [n for n in self.host.rows if not self.table.isRowHidden(self._row(n))]
        self.assertEqual(shown, ["Crate", "Crate1"])
        self.host.ui.txt000.clear()
        self.assertFalse(any(self.table.isRowHidden(r) for r in range(4)))

    def test_no_list_filters_no_option_box(self):
        """Blender has none: an empty option box would be a dead button."""
        self.assertIsNone(self.host.ui.txt000.option_box.get_menu(create=False))

    def test_a_list_filter_narrows_the_list(self):
        """Maya's Hide Default Materials shape: a checkbox in the filter field's
        option box, read back by the rows hook, refilling when toggled."""

        class _Filtered(_PanelHost):
            def _list_filters(self):
                return (("chk_hide_old", "Hide Old", "Hide the old one."),)

            def _material_rows(self):
                rows = super()._material_rows()
                hide = self._list_option("chk_hide_old")
                return [r for r in rows if not (hide and r["name"] == "Old")]

        host = _Filtered()
        host.txt000_init(host.ui.txt000)
        host.tbl000_init(host.ui.tbl000)
        chk = host.ui.txt000.option_box.menu.chk_hide_old
        chk.setChecked(True)
        self._settle()
        table = host.ui.tbl000
        names = [table.item(r, 0).text() for r in range(table.rowCount())]
        self.assertEqual(names, ["Crate", "Crate1", "Wood"])
        host.ui.deleteLater()

    def test_the_optional_columns_start_hidden(self):
        header = self.table.horizontalHeader()
        hidden = [c for c in range(7) if header.isSectionHidden(c)]
        self.assertEqual(hidden, list(self.host._OPTIONAL_COLUMNS))

    def test_highlighting_a_row_makes_it_current(self):
        self._click("Wood", self.host.COL_NAME)
        self.assertEqual(self.host._current_mat(), "Wood")

    def test_a_refill_keeps_the_current_material_highlighted(self):
        self.host._set_current("Old")
        self.host._refresh_material_lists()
        self._settle()
        self.assertEqual(self.host._highlighted_mats(), ["Old"])

    def test_merge_is_offered_only_on_a_duplicate(self):
        menu = self.table.menu
        merge = menu.findChild(QtWidgets.QPushButton, "b032")
        assign = menu.findChild(QtWidgets.QPushButton, "b028")
        self.table.clearSelection()
        self.table.context_menu_about_to_show.emit()
        self.assertFalse(assign.isEnabled(), "nothing highlighted")
        self._click("Crate", self.host.COL_NAME)
        self.table.context_menu_about_to_show.emit()
        self.assertTrue(merge.isHidden())
        self.assertTrue(assign.isEnabled())
        self._click("Crate1", self.host.COL_NAME)
        self.table.context_menu_about_to_show.emit()
        self.assertFalse(merge.isHidden())
        self.host.b032()
        self.assertIn(("merge", {"Crate1": "Crate"}), self.host.calls)

    def test_the_row_menu_acts_on_the_highlighted_material(self):
        self._click("Wood", self.host.COL_NAME)
        self.host.b030()
        self.host.b031()
        self.host.lbl002()
        self.assertEqual(
            self.host.calls,
            [
                ("select", "Wood", dict(shell=True, in_selection=False, add=False, unassigned=False)),
                ("select", "Wood", dict(shell=False, in_selection=True, add=False, unassigned=False)),
                ("delete", ["Wood"]),
            ],
        )

    def test_editing_a_name_renames_that_material(self):
        item = self.table.item(self._row("Old"), self.host.COL_NAME)
        item.setText("Retired")
        self._settle()
        self.assertEqual(self.host.calls, [("rename", "Old", "Retired")])
        self.assertIsNotNone(self._row("Retired"), "the table refills with the new name")

    def test_restyling_a_row_is_no_rename(self):
        """A label the DCC shortens its own way (a namespace kept) must not
        read as edited when a mark restyles its cell."""
        self.host.rows = ["ns:Crate", "Old"]
        self.host._refresh_material_lists()
        self._settle()
        self.host.on_selection = {"ns:Crate"}
        self.host.ui.on_activated.emit()
        self._settle()
        self.assertEqual(self.host.calls, [])

    def test_the_selections_materials_are_marked_on_activation(self):
        bold = lambda: {
            n for n in self.host.rows
            if self.table.item(self._row(n), self.host.COL_NAME).font().bold()
        }
        self.assertEqual(bold(), {"Crate"})
        self.host.on_selection = {"Wood"}
        self.host.ui.on_activated.emit()
        self.assertEqual(bold(), {"Wood"})
        self.assertEqual(self.host._current_mat(), None, "a mark, never the current")

    def test_get_and_select_adopts_and_highlights(self):
        self.host.b003()
        self.assertEqual(self.host._highlighted_mats(), ["Crate"])
        self.assertEqual(self.host.calls[-1][:2], ("select", "Crate"))


@unittest.skipUnless(HAVE_QT, "Qt / uitk unavailable")
class TestCallSlot(unittest.TestCase):
    """Slots._call_slot: the widget when the slot takes one, else bare --
    read off the signature, never by retrying on a TypeError."""

    def test_the_widget_reaches_a_slot_that_takes_it(self):
        got = []
        Slots._call_slot(lambda widget: got.append(widget), "w")
        Slots._call_slot(lambda widget=None: got.append(widget), "w")
        self.assertEqual(got, ["w", "w"])

    def test_a_bare_slot_is_called_bare(self):
        got = []
        Slots._call_slot(lambda: got.append("bare"), "w")
        self.assertEqual(got, ["bare"])

    def test_a_type_error_inside_the_slot_surfaces_after_one_run(self):
        runs = []

        def slot(widget=None):
            runs.append(widget)
            raise TypeError("the slot's own")

        with self.assertRaisesRegex(TypeError, "the slot's own"):
            Slots._call_slot(slot, "w")
        self.assertEqual(runs, ["w"])


@unittest.skipUnless(HAVE_QT, "Qt / uitk unavailable")
class TestHeaderMenu(unittest.TestCase):
    """Tools in the header: its categories are the roots, flying out on hover."""

    @staticmethod
    def _roots(tools):
        return [w.item_text() for w in tools.get_items() if w.parent_item_text() is None]

    def test_the_header_holds_tools_and_the_scene_wide_verbs(self):
        host = _PanelHost()
        header = Header()
        host.header_init(header)
        tools = header.menu.findChild(ExpandableList, "list001")
        self.assertIsNotNone(tools)
        names = {
            b.objectName() for b in header.menu.findChildren(QtWidgets.QPushButton)
        }
        self.assertLessEqual({"b033", "b014", "b015"}, names)
        self.assertNotIn("b004", names, "random is Alt + New or an Assign icon")
        self.assertIn("refresh", header.buttons)
        tools.ui = host.ui
        host.list001_init(tools)
        self.assertEqual(self._roots(tools), ["Setup", "Utilities"])

    def test_the_submenu_keeps_a_tools_root(self):
        host = _PanelHost()
        tools = ExpandableList()
        tools.ui = _FakeListWidget._Surface({"submenu"})
        host.list001_init(tools)
        self.assertEqual(self._roots(tools), ["Tools"])


if __name__ == "__main__":
    unittest.main()
