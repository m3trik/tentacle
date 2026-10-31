#!/usr/bin/python
# coding=utf-8
"""Tests for the materials panel: ``MaterialsSlots``, one class for both hosts.

The panel is a material table (``tbl000``): one row per material, its swatch and name,
optional Type / Users / Textures columns, then Status / Select / Assign icon columns, a
filter field (``txt000``) and + (``b006``) above it, a summary in the footer. The table,
the current material, the row menu, the status fixes and the header menu are the class's;
every scene read and write is the host toolkit's ``MatUtils`` (``self.tk``), by name.

Three parts here:

- Pins on the module and the ``.ui``: no host import, no fork left, every widget the
  forks served still has its slot, the Tools rows well formed; the ``.ui`` carries the
  table and the submenu keeps its Assign list.
- The issue judgment and Remove Duplicate Materials over a recording toolkit.
- The table itself, acted on in offscreen Qt over a fake toolkit: the cells are
  clicked, the filter typed into, a name edited, the row menu fitted, as a user would.

(The module keeps its pre-composition name: it covered the shared mixin the class
replaced.) Added: 2026-10-22 (replaces the combo-era cmb002 wiring tests).
"""
import ast
import contextlib
import os
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy import QtCore, QtGui, QtTest, QtWidgets  # noqa: E402

QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
from uitk.managers.icon_manager import IconManager  # noqa: E402
from uitk.widgets.expandableList import ExpandableList  # noqa: E402
from uitk.widgets.footer import Footer  # noqa: E402
from uitk.widgets.header import Header  # noqa: E402
from uitk.widgets.lineEdit import LineEdit  # noqa: E402
from uitk.widgets.tableWidget import TableWidget  # noqa: E402

from tentacle.slots._slots import Slots  # noqa: E402
from tentacle.slots.materials import MaterialsSlots  # noqa: E402

SLOTS_DIR = ROOT / "tentacle" / "slots"
MODULE_FILE = SLOTS_DIR / "materials.py"
UI_DIR = ROOT / "tentacle" / "ui"

#: Every widget-named slot the per-host forks served (and their inits).
WIDGET_SLOTS = (
    "b003", "b004", "b006", "b006_init", "b007", "b008", "b009", "b010", "b011",
    "b013", "b014", "b015", "b016", "b018", "b019", "b020", "b021", "b022", "b023",
    "b024", "b025", "b026", "b027", "b028", "b029", "b030", "b031", "b032", "b033",
    "lbl002", "lbl004", "lbl006", "list000", "list000_init", "list001",
    "list001_init", "tb001", "tb001_init", "tb002", "tb002_init", "tbl000_init",
    "txt000_init", "header_init",
)


class _NoMigration(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestTheOneClass(unittest.TestCase):
    """One class serves both hosts, reaching them only through ``self.tk``."""

    def test_the_mixin_and_the_forks_are_gone(self):
        for rel in ("_materials.py", "maya/materials.py", "blender/materials.py"):
            with self.subTest(rel=rel):
                self.assertFalse((SLOTS_DIR / rel).exists(), rel)

    def test_no_host_is_imported_or_named(self):
        tree = ast.parse(MODULE_FILE.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & {"maya", "bpy", "mayatk", "blendertk"}, imported)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(names & {"cmds", "mel", "bpy", "mtk", "btk"}, names)

    def test_every_widget_the_forks_served_has_its_slot(self):
        for name in WIDGET_SLOTS:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(MaterialsSlots, name, None)), name)

    def test_no_slot_reaches_for_the_retired_combo(self):
        self.assertNotIn("cmb002", MODULE_FILE.read_text(encoding="utf-8"))

    def test_the_tools_rows_are_well_formed(self):
        """``(label, slot, tooltip[, requires])``: every slot defined, a host tag
        naming a host, and the one-host rows the ones the other host lacks."""
        tagged = {}
        for category, rows in MaterialsSlots._TOOLS_ITEMS.items():
            labels = [row[0] for row in rows]
            self.assertEqual(len(labels), len(set(labels)), category)
            for label, slot, *rest in rows:
                with self.subTest(row=label):
                    self.assertTrue(callable(getattr(MaterialsSlots, slot, None)), slot)
                    self.assertLessEqual(len(rest), 2)
                    if len(rest) == 2:
                        self.assertIn(rest[1], ("maya", "blender"))
                        tagged[slot] = rest[1]
        self.assertEqual(tagged, {"b026": "maya", "tb002": "maya"})

    def test_the_list_filters_are_mayas(self):
        """Blender has no built-in default materials and no Arnold shaders."""
        self.assertEqual(
            {row[0]: row[4] for row in MaterialsSlots._LIST_FILTERS},
            {"chk_hide_defaults": "maya", "chk_hide_arnold": "maya"},
        )


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


def _mock_slots():
    """A MaterialsSlots over a MagicMock switchboard (its ``.tk`` records)."""
    sb = mock.MagicMock()
    slots = MaterialsSlots(sb)
    slots.ui = type("_UI", (), {})()
    return slots, sb


class TestAssignRootText(_NoMigration):
    """The submenu's Assign root names the current material by its leaf."""

    def _slots(self, current):
        slots, _sb = _mock_slots()
        slots._current = current
        return slots

    def test_names_the_current_material(self):
        slots = self._slots("metal_mat")
        self.assertEqual(slots._assign_root_text(_FakeListWidget(True)), "Assign: metal_mat")

    def test_by_its_leaf(self):
        slots = self._slots("grp|metal_mat")
        self.assertEqual(slots._assign_root_text(_FakeListWidget(True)), "Assign: metal_mat")

    def test_falls_back_with_nothing_current(self):
        self.assertEqual(self._slots(None)._assign_root_text(_FakeListWidget(True)), "Assign")

    def test_the_assign_list_is_the_hosts_materials_but_defaults(self):
        slots, sb = _mock_slots()
        sb.tk.MatUtils.get_scene_mat_names.return_value = ["Crate", "Wood"]
        widget = ExpandableList()
        slots.list000_init(widget)
        sb.tk.MatUtils.get_scene_mat_names.assert_called_once_with(exclude_defaults=True)
        root = widget.get_items()[0]
        self.assertEqual(root.item_text(), "Assign")
        self.assertEqual(
            [w.item_text() for w in root.sublist.get_items()], ["New", "Random", "Crate", "Wood"]
        )


def _facts(missing=(), duplicate_of=None, unused=False):
    return {"type": "lambert", "users": 0, "textures": len(missing),
            "missing": list(missing), "duplicate_of": duplicate_of, "unused": unused}


class TestTheIssueIsJudgedOnce(_NoMigration):
    """The host reports raw facts (``MatUtils.get_mat_facts``); the panel picks the
    one issue to show -- a missing texture, then a duplicate, then nothing using
    it -- and words it, the same in both hosts.
    Added: 2026-10-24 (both forks carried a copy of this)."""

    @staticmethod
    def issue(facts):
        return MaterialsSlots._material_issue(facts)

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
        slots, sb = _mock_slots()
        sb.tk.MatUtils.get_mat_facts.side_effect = lambda names: {
            n: _facts(duplicate_of="Crate") for n in names
        }
        details = slots._material_details(["Crate1"])
        sb.tk.MatUtils.get_mat_facts.assert_called_once_with(["Crate1"])
        self.assertEqual(details["Crate1"]["issue"], ("duplicate", "A duplicate of Crate", "Crate"))
        self.assertEqual(details["Crate1"]["type"], "lambert")


class TestRemoveDuplicateMaterials(_NoMigration):
    """The header's Remove Duplicate Materials (``b014``): it reports what the
    merge removed, not what the finder found -- a merge can refuse a pair
    (Maya: the original has no shading engine; a merge that fails only warns).
    Added: 2026-10-24"""

    def _slots(self, pairs, merged):
        slots, sb = _mock_slots()
        slots._refresh_material_lists = mock.Mock()
        sb.tk.MatUtils.find_duplicate_materials.return_value = dict(pairs)
        sb.tk.MatUtils.merge_duplicate_materials.return_value = merged
        return slots, sb

    def test_it_reports_what_the_merge_removed(self):
        slots, sb = self._slots({"Crate1": "Crate", "Crate2": "Crate"}, merged=1)
        slots.b014()
        sb.tk.MatUtils.find_duplicate_materials.assert_called_once_with()
        sb.tk.MatUtils.merge_duplicate_materials.assert_called_once_with(
            {"Crate1": "Crate", "Crate2": "Crate"}
        )
        self.assertEqual(sb.message_box.call_args.args[0], "Removed <hl>1</hl> duplicate material.")

    def test_none_found_merges_nothing(self):
        slots, sb = self._slots({}, merged=0)
        slots.b014()
        sb.tk.MatUtils.merge_duplicate_materials.assert_not_called()
        self.assertEqual(sb.message_box.call_args.args[0], "No duplicate-texture materials found.")


class TestOneHostOnlyControls(_NoMigration):
    """A control only one host serves is hidden on the other (CODE_STANDARD
    section 15: hidden, never a stub)."""

    def test_exclude_default_materials_is_mayas(self):
        slots, sb = _mock_slots()
        made = {}

        def add(_kind, **kwargs):
            made[kwargs["setObjectName"]] = mock.MagicMock()
            return made[kwargs["setObjectName"]]

        widget = mock.MagicMock()
        widget.option_box.menu.add.side_effect = add
        slots.tb001_init(widget)
        made["chk_exclude_defaults"].setProperty.assert_called_once_with("requires", "maya")
        sb.apply_visibility_policy.assert_called_once_with(made["chk_exclude_defaults"])
        data = [c.args[1] for c in made["cmb_scope"].addItem.call_args_list]
        self.assertEqual(data, ["textures", "current", "all", "selected"])  # saved order

    def test_get_material_info_asks_the_host_in_mayatks_call(self):
        slots, sb = _mock_slots()
        menu = mock.MagicMock()
        menu.cmb_scope.currentData.return_value = "all"
        menu.cmb_scope.currentText.return_value = "All Materials"
        for name, checked in (
            ("chk_exclude_defaults", True), ("chk_exclude_unassigned", False),
            ("chk_include_textures", True), ("chk_include_metadata", True),
            ("chk_include_optimization", False),
        ):
            getattr(menu, name).isChecked.return_value = checked
        widget = mock.MagicMock()
        widget.option_box.menu = menu
        sb.tk.MatUtils.get_mat_info.return_value = [{"material": "Crate"}]
        slots.tb001(widget)
        kwargs = sb.tk.MatUtils.get_mat_info.call_args.kwargs
        self.assertEqual(
            {k: kwargs[k] for k in ("exclude_defaults", "exclude_unassigned",
                                    "include_textures", "optimize_check")},
            {"exclude_defaults": True, "exclude_unassigned": False,
             "include_textures": True, "optimize_check": False},
        )
        sb.text_view_dialog.assert_called_once()

    def test_the_current_material_report_drops_the_scope_filters(self):
        slots, sb = _mock_slots()
        slots._current = "Crate"
        menu = mock.MagicMock()
        menu.cmb_scope.currentData.return_value = "current"
        widget = mock.MagicMock()
        widget.option_box.menu = menu
        sb.tk.MatUtils.get_mat_info.return_value = [{"material": "Crate"}]
        slots.tb001(widget)
        kwargs = sb.tk.MatUtils.get_mat_info.call_args.kwargs
        self.assertEqual(kwargs["materials"], ["Crate"])
        self.assertNotIn("exclude_defaults", kwargs)

    def test_the_texture_report_filters_by_the_option_box(self):
        slots, sb = _mock_slots()
        menu = mock.MagicMock()
        menu.cmb_scope.currentData.return_value = "textures"
        menu.chk_exclude_defaults.isChecked.return_value = True
        menu.chk_exclude_unassigned.isChecked.return_value = True
        widget = mock.MagicMock()
        widget.option_box.menu = menu
        sb.tk.MatUtils.get_texture_info.return_value = []
        slots.tb001(widget)
        sb.tk.MatUtils.get_texture_info.assert_called_once_with(
            exclude_defaults=True, exclude_unassigned=True
        )
        self.assertIn("No textures", sb.message_box.call_args.args[0])

    def test_the_shader_editor_is_the_hypershade_by_name(self):
        slots, sb = _mock_slots()
        slots.b007()
        sb.tk.UiUtils.open_editor.assert_called_once_with("Hypershade")

    def test_the_converter_gets_the_hosts_scopes_and_a_picker(self):
        slots, sb = _mock_slots()
        ui = mock.MagicMock()
        sb.handlers.external_app.launch.return_value = ui
        sb.tk.EnvUtils.source_images_dir.return_value = "C:/proj/sourceimages"
        provider = mock.Mock()
        sb.tk.MatUtils.get_texture_scopes.return_value = {"Selected Objects": provider}
        slots.b016()
        sb.handlers.external_app.launch.assert_called_once_with("converter", show=False)
        self.assertEqual(ui.slots.source_dir, "C:/proj/sourceimages")
        labels = [c.args[0] for c in ui.slots.register_scope.call_args_list]
        self.assertEqual(labels, ["Selected Objects", "Choose Materials..."])
        sb.handlers.marking_menu.show.assert_called_once_with(ui)

    def test_a_failed_extapp_launch_is_said(self):
        slots, sb = _mock_slots()
        sb.handlers.external_app.launch.side_effect = RuntimeError("not installed")
        slots.b022()
        self.assertIn("not installed", sb.message_box.call_args.args[0])


class _Window(QtWidgets.QMainWindow):
    """The panel window: what the class reads off ``self.ui``."""

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


class _FakeMatUtils:
    """The host library's ``MatUtils`` as the panel calls it, over the host's
    rows: ``Crate`` is fine, ``Crate1`` duplicates it, ``Old`` is unused, ``Wood``
    misses a texture. Every write records what it was asked."""

    def __init__(self, host):
        self.host = host
        self.merged = None  # what a merge reports; None: every pair it was given

    def get_scene_mat_names(self, exclude_defaults=False, exc_renderer=None):
        rows = list(self.host.rows)
        return [n for n in rows if n != "Old"] if exclude_defaults else rows

    def get_mat_swatch_color(self, name):
        return {"Crate": (1.0, 0.0, 0.0)}.get(name)  # the rest: no colour to read

    def get_mat_facts(self, names):
        return {
            n: {"type": "lambert", "users": 0 if n == "Old" else 2, "textures": 1,
                "missing": ["Wood_BaseColor.png"] if n == "Wood" else [],
                "duplicate_of": "Crate" if n == "Crate1" else None,
                "unused": n in self.host.unused}
            for n in names
        }

    def find_duplicate_materials(self, materials=None):
        return {"Crate1": "Crate"} if "Crate1" in self.host.rows else {}

    def get_mat_names(self, objects=None):
        return sorted(self.host.on_selection)

    def assign_mat(self, objects, name, create=True):
        self.host.calls.append(("assign", name))

    def delete_mats(self, names):
        self.host.calls.append(("delete", list(names)))
        self.host.rows = [n for n in self.host.rows if n not in names]
        return list(names)

    def merge_duplicate_materials(self, pairs):
        self.host.calls.append(("merge", dict(pairs)))
        self.host.rows = [n for n in self.host.rows if n not in pairs]
        return len(pairs) if self.merged is None else self.merged

    def rename_mat(self, material, name):
        self.host.calls.append(("rename", material, name))
        self.host.rows = [name if n == material else n for n in self.host.rows]
        return name

    def select_by_mat(self, material, objects=None, shell=False, add=False):
        self.host.calls.append(("select", material, dict(
            shell=shell, in_selection=objects is not None, add=add, unassigned=False)))
        return []

    def select_unassigned(self, objects=None, add=False):
        self.host.calls.append(("select", None, dict(
            shell=True, in_selection=objects is not None, add=add, unassigned=True)))
        return []

    def show_mat_attributes(self, material):
        self.host.calls.append(("node", material))
        return [material]

    def graph_materials(self, material):
        self.host.calls.append(("editor", material))

    def assign_new_mat(self, objects=None):
        self.host.calls.append(("new",))
        return None  # Maya: its own window takes it from there

    def assign_random_mat(self, objects=None, previous=None):
        self.host.calls.append(("random",))
        return "Random1"


class _FakeCoreUtils:
    def __init__(self):
        self.selection = ["obj"]

    def selected_objects(self):
        return list(self.selection)

    @contextlib.contextmanager
    def undo_chunk(self, name=""):
        yield


class _PanelHost(MaterialsSlots):
    """The composed class over a fake toolkit and switchboard, its window real.

    *context* is the host the switchboard serves (``requires`` tags it hides);
    the Tools list is cut to two rows (their slots' panels open nowhere here).
    """

    _TOOLS_ITEMS = {
        "Setup": [("Texture Path Editor", "b010", "")],
        "Utilities": [("Reload Scene Textures", "b013", "")],
    }

    def __init__(self, context="maya"):
        window = _Window()
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        window.txt000 = LineEdit()
        window.tbl000 = TableWidget()
        window.footer = Footer()
        for widget in (window.txt000, window.tbl000, window.footer):
            layout.addWidget(widget)
        window.setCentralWidget(central)
        window.resize(320, 260)
        window.tbl000.is_initialized = False
        jobs, messages = _Jobs(), []
        tk = type("_Tk", (), {})()
        tk.CoreUtils = _FakeCoreUtils()
        tk.ScriptJobManager = jobs

        def policy(widget):
            requires = widget.property("requires")
            hidden = bool(requires) and requires != context
            if hidden:
                widget.setVisible(False)
            return hidden

        sb = type("_SB", (), {})()
        sb.QtWidgets, sb.QtCore, sb.QtGui = QtWidgets, QtCore, QtGui
        sb.IconManager = IconManager
        sb.registered_widgets = type("_W", (), {"ExpandableList": ExpandableList})
        sb.message_box = messages.append
        sb.loaded_ui = type("_L", (), {"materials": window, "materials_submenu": None})
        sb.tk = tk
        sb.apply_visibility_policy = policy
        sb.handlers = type("_H", (), {})()
        sb.handlers.marking_menu = type("_M", (), {})()
        sb.handlers.marking_menu.show = lambda name: self.calls.append(
            (name, self._current_mat())
        )
        super().__init__(sb)  # the QObject first: then the state it holds
        self.calls = []
        self.messages = messages
        self.jobs = jobs
        self.on_selection = {"Crate"}
        self.unused = {"Old"}
        self.rows = ["Crate", "Crate1", "Old", "Wood"]
        self.mat_utils = tk.MatUtils = _FakeMatUtils(self)

    # The Tools rows here are plain labels; gating is the base's, tested there.
    def add_slot_widget(self, sublist, **kwargs):
        return sublist.add(kwargs.get("setText", ""))

    def gate_on_app(self, widget, resolve_spec):
        return True


class _TableCase(_NoMigration):
    def setUp(self):
        super().setUp()
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

    def _names(self):
        return [self.table.item(r, 0).text() for r in range(self.table.rowCount())]

    def _wait_for_refill(self):
        QtTest.QTest.qWait(self.host._REFILL_DELAY_MS * 3)
        self._settle()


class TestMaterialTable(_TableCase):
    """The table, acted on: what a click, a keystroke and an edit do."""

    def test_each_material_is_a_row_and_the_details_follow(self):
        self.assertEqual(self._names(), ["Crate", "Crate1", "Old", "Wood"])
        self.assertEqual(self.table.item(self._row("Old"), self.host.COL_USERS).text(), "0")
        self.assertEqual(
            self.host._ICON_HEADERS,
            {c: self.table.horizontalHeaderItem(c).toolTip() for c in (4, 5, 6)},
            "an icon column is named by its header tooltip in the column menu",
        )

    def test_the_swatch_is_the_hosts_colour_painted_by_the_panel(self):
        """The library answers a colour (``MatUtils.get_mat_swatch_color``); the
        icon is the panel's, blank where the host has no colour to read."""

        def pixel(name):
            icon = self.table.item(self._row(name), self.host.COL_NAME).icon()
            return icon.pixmap(8, 8).toImage().pixelColor(4, 4)

        crate = pixel("Crate")
        self.assertEqual((crate.red(), crate.green(), crate.blue()), (255, 0, 0))
        self.assertEqual(pixel("Wood").alpha(), 0)

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
        self.host.mat_utils.merged = 0
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
        self.host.lbl004()
        self.host.lbl006()
        self.host.lbl002()
        self.assertEqual(
            self.host.calls,
            [
                ("select", "Wood", dict(shell=True, in_selection=False, add=False, unassigned=False)),
                ("select", "Wood", dict(shell=False, in_selection=True, add=False, unassigned=False)),
                ("node", "Wood"),
                ("editor", "Wood"),
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
        """A namespaced name (``ns:Crate``) must not read as edited when a mark
        restyles its cell."""
        self.host.rows = ["ns:Crate", "Old"]
        self.host._refresh_material_lists()
        self._settle()
        self.host.on_selection = {"ns:Crate"}
        self.host.ui.on_activated.emit()
        self._settle()
        self.assertEqual(self.host.calls, [])

    def test_the_selections_materials_are_marked_on_activation(self):
        def bold():
            return {
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


class TestTheListFilters(_NoMigration):
    """The filter field's option box holds the list filters the host serves."""

    class _Filtered(_PanelHost):
        _LIST_FILTERS = (
            ("chk_hide_old", "Hide Old", "Hide the old one.", {"exclude_defaults": True}, "maya"),
        )

    def _host(self, context):
        host = self._Filtered(context)
        host.txt000_init(host.ui.txt000)
        host.tbl000_init(host.ui.tbl000)
        self.addCleanup(host.ui.deleteLater)
        return host

    def test_a_list_filter_narrows_the_list(self):
        """A checkbox in the filter field's option box, its keywords passed to
        ``MatUtils.get_scene_mat_names``, the list refilled when toggled."""
        host = self._host("maya")
        host.ui.txt000.option_box.menu.chk_hide_old.setChecked(True)
        QtWidgets.QApplication.instance().processEvents()
        table = host.ui.tbl000
        names = [table.item(r, 0).text() for r in range(table.rowCount())]
        self.assertEqual(names, ["Crate", "Crate1", "Wood"])

    def test_a_host_serving_none_gets_no_option_box(self):
        """Blender has none: an empty option box would be a dead button."""
        host = self._host("blender")
        self.assertIsNone(host.ui.txt000.option_box.get_menu(create=False))
        self.assertEqual(host._list_filter_options(), {})


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


class TestHeaderMenu(_NoMigration):
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

    def test_a_row_one_host_serves_is_hidden_on_the_other(self):
        class _Host(_PanelHost):
            _TOOLS_ITEMS = {
                "Utilities": [
                    ("Reload Scene Textures", "b013", ""),
                    ("Arnold Preview Shader", "b026", "", "maya"),
                ],
            }

        for context, hidden in (("maya", False), ("blender", True)):
            with self.subTest(context=context):
                host = _Host(context)
                tools = ExpandableList()
                tools.ui = host.ui
                host.list001_init(tools)
                rows = {
                    w.item_text(): w
                    for w in tools.get_items()
                    if w.parent_item_text() == "Utilities"
                }
                self.assertFalse(rows["Reload Scene Textures"].isHidden())
                self.assertEqual(rows["Arnold Preview Shader"].isHidden(), hidden)


if __name__ == "__main__":
    unittest.main()
