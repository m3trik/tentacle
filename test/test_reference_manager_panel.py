#!/usr/bin/python
# coding=utf-8
"""The Reference Manager panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk``: the controller composes the host
toolkit's ``ReferenceManager`` engine, so a fake toolkit (with a fake engine whose
host facts are Maya's or Blender's) stands in for ``mtk`` / ``btk`` here and records
what the panel asks of it -- plain unittest, no DCC, no Qt widgets (a small table
fake stands in for uitk's ``TableWidget``). In Maya, the same class drives the real
``mtk`` (``TestReferenceManagerPanelInMaya``).

The panel-level suites of mayatk's and blendertk's ``test_reference_manager.py``
moved here with the panel: the listing and its filters, selection as the reference
set, the row toggles, the unsaved-changes prompt, the Naming conventions, the delete
prompt, the workspace history, the conversion prompts and progress, unlink and
un-reference. The engines' own behavior stays in those library tests.
"""

import contextlib
import inspect
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools import reference_manager as panel_module
from tentacle.slots.tools._reference_manager.listing import SceneListing
from tentacle.slots.tools.reference_manager import ReferenceManagerSlots


# ----------------------------------------------------------------------------- fakes
class _Qt:
    UserRole = 256
    ItemIsSelectable = 1
    ItemIsEditable = 2
    ItemIsEnabled = 32


class _Item:
    """Enough ``QTableWidgetItem``."""

    def __init__(self, text=""):
        self._text = text
        self._data = {}
        self._flags = _Qt.ItemIsSelectable | _Qt.ItemIsEnabled
        self._selected = False
        self.tooltip = ""
        self._row = self._col = 0

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text

    def data(self, role):
        return self._data.get(role)

    def setData(self, role, value):
        self._data[role] = value

    def flags(self):
        return self._flags

    def setFlags(self, flags):
        self._flags = flags

    def setSelected(self, state):
        self._selected = bool(state)

    def isSelected(self):
        return self._selected

    def setToolTip(self, text):
        self.tooltip = text

    def row(self):
        return self._row

    def column(self):
        return self._col


class _Index:
    def __init__(self, row, col):
        self._row, self._col = row, col

    def row(self):
        return self._row

    def column(self):
        return self._col

    def isValid(self):
        return self._row >= 0


class _Actions:
    def __init__(self):
        self.states = {}
        self.columns = {}

    def set(self, row, col, state):
        self.states[(row, col)] = state

    def add(self, col, states):
        self.columns[col] = states


class _Table:
    """Enough uitk ``TableWidget`` for the controller: items by (row, col), the
    action-icon states, row visibility and selection."""

    ACTION_COLOR_MAP = {"current": ("#6898b8",)}

    def __init__(self):
        self._items = {}
        self._rows = 0
        self.actions = _Actions()
        self.hidden_rows = set()
        self.hidden_columns = {}
        self.formatted = []
        self.blocked = False
        self.has_menu = False
        self.menu = SimpleNamespace(btn_open_scene=mock.MagicMock())
        self.edited = []
        self.current = None
        self.sorting = True

    def setRowCount(self, n):
        self._rows = n
        self._items = {k: v for k, v in self._items.items() if k[0] < n}
        self.hidden_rows = {r for r in self.hidden_rows if r < n}

    def rowCount(self):
        return self._rows

    def item(self, row, col):
        return self._items.get((row, col))

    def setItem(self, row, col, item):
        item._row, item._col = row, col
        self._items[(row, col)] = item

    def setUpdatesEnabled(self, state):
        pass

    def isSortingEnabled(self):
        return self.sorting

    def setSortingEnabled(self, state):
        self.sorting = state

    def apply_formatting(self):
        pass

    def format_item(self, item, key=None, italic=False):
        self.formatted.append((item.text(), key, italic))

    def setRowHidden(self, row, hidden):
        (self.hidden_rows.add if hidden else self.hidden_rows.discard)(row)

    def isRowHidden(self, row):
        return row in self.hidden_rows

    def blockSignals(self, state):
        old, self.blocked = self.blocked, state
        return old

    def clearSelection(self):
        for item in self._items.values():
            item.setSelected(False)

    def selectedIndexes(self):
        return [
            _Index(r, c) for (r, c), item in self._items.items() if item.isSelected()
        ]

    def indexAt(self, pos):
        return _Index(pos, 0)

    def editItem(self, item):
        self.edited.append(item)

    def currentItem(self):
        return self.current

    def setColumnHidden(self, col, hidden):
        self.hidden_columns[col] = hidden


class _Combo:
    """Enough uitk ``ComboBox`` for the workspace combo (items are (text, data))."""

    def __init__(self):
        self.items = []
        self.index = -1

    def add(self, items):
        self.items.extend(items)
        if self.items and self.index == -1:
            self.index = 0

    def clear(self):
        self.items, self.index = [], -1

    def count(self):
        return len(self.items)

    def currentIndex(self):
        return self.index

    def setCurrentIndex(self, i):
        if 0 <= i < len(self.items):
            self.index = i

    def itemText(self, i):
        return self.items[i][0] if 0 <= i < len(self.items) else ""

    def itemData(self, i):
        return self.items[i][1] if 0 <= i < len(self.items) else None

    def blockSignals(self, state):
        return False


class _Field:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text


class _Check:
    def __init__(self, checked=False):
        self.checked = checked

    def isChecked(self):
        return self.checked


class _Footer:
    def __init__(self):
        self.text = None
        self.status = []

    def setText(self, text, level=None):
        self.text = (text, level)

    def setStatusText(self, text, level=None):
        self.status.append((text, level))


class _Settings(dict):
    def value(self, key, default=None):
        return self.get(key, default)

    def setValue(self, key, value):
        self[key] = value


class _Ref:
    """A reference as the engine answers it."""

    def __init__(self, path, namespace=None):
        self.path = path
        self.namespace = namespace or os.path.splitext(os.path.basename(path))[0]
        self.label = self.namespace


#: The host facts mayatk's engine declares; blendertk's override below.
MAYA_FACTS = dict(
    NATIVE_EXTENSIONS=(".ma", ".mb", ".fbx", *ptk.USD_EXTENSIONS),
    FOREIGN_EXTENSIONS=(".blend",),
    IMPORT_EXTENSIONS=(".blend", *ptk.USD_EXTENSIONS),
    INCLUDE_DEFAULTS=(".ma", ".mb"),
    SCENE_SAVE_EXTENSION=".ma",
    NAMESPACE_MODES=("remove", "keep", "root"),
    RIG_MODES=("rig", "bake"),
    PRESET_DIR="mayatk/reference_manager",
)
BLENDER_FACTS = dict(
    NATIVE_EXTENSIONS=(".blend",),
    FOREIGN_EXTENSIONS=(".ma", ".mb", ".fbx", *ptk.USD_EXTENSIONS),
    IMPORT_EXTENSIONS=(".ma", ".mb", ".fbx", *ptk.USD_EXTENSIONS),
    INCLUDE_DEFAULTS=(".blend",),
    SCENE_SAVE_EXTENSION=".blend",
    NAMESPACE_MODES=("remove",),
    RIG_MODES=("rig", "bake", "raw"),
    PRESET_DIR="blendertk/reference_manager",
)


def _norm(path):
    return os.path.normcase(os.path.normpath(path)) if path else ""


def _engine(facts=MAYA_FACTS, refs=(), current="", bakes=None):
    """A fake engine: *refs* are the scene's references, *current* the open scene,
    *bakes* ``{bake path: source}`` (a bake-backed reference's row is its source)."""
    engine = mock.MagicMock()
    for name, value in facts.items():
        setattr(engine, name, value)
    bakes = {_norm(k): v for k, v in (bakes or {}).items()}
    engine.current_references = list(refs)
    engine.bake_source.side_effect = lambda p: bakes.get(_norm(p))
    engine.row_key.side_effect = lambda p: _norm(bakes.get(_norm(p)) or p)
    engine.is_foreign.side_effect = lambda p: (
        bool(p) and os.path.splitext(p)[1].lower() in engine.FOREIGN_EXTENSIONS
    )
    engine.needs_conversion.side_effect = engine.is_foreign.side_effect
    engine.current_scene.return_value = current
    engine.is_current.side_effect = lambda p, current=None: (
        bool(engine.current_scene()) and _norm(p) == _norm(engine.current_scene())
    )
    engine.scene_modified.return_value = False
    engine.get_reference_display_mode.return_value = "off"
    engine.set_reference_display_mode.return_value = True
    engine.add_reference.return_value = True
    engine.remove_references.return_value = []
    engine.scene_has_complex_animation.return_value = False
    engine.workspace_files = {}
    engine.recursive_search = True
    engine.ignore_empty_workspaces = True
    engine.find_foreign_scenes.return_value = []
    engine.find_available_workspaces.return_value = []
    engine.current_working_dir = ""
    engine.current_workspace = ""
    return engine


def _header_menu(case="None", suffix="", structure="{scenes}", **checks):
    menu = SimpleNamespace(
        cmb_case_style=SimpleNamespace(currentText=lambda: case),
        txt_suffix=_Field(suffix),
        txt_subfolder_structure=_Field(structure),
        cmb_conversion_route=SimpleNamespace(currentText=lambda: "Convert via FBX"),
    )
    for name in (
        "chk_filter_suffix",
        "chk_filter_folder_structure",
        "chk_hide_suffix",
        "chk_hide_extension",
        "chk_show_notes_column",
    ):
        setattr(menu, name, _Check(checks.get(name, False)))
    for t in ("ma", "mb", "fbx", "usd", "blend"):
        setattr(
            menu,
            f"chk_include_{t}",
            _Check(checks.get(f"chk_include_{t}", t in ("ma", "mb"))),
        )
    return menu


def _panel(engine=None, tk=None, answers=(), inputs=(), menu=None):
    """A Slots instance over a fake ui and toolkit (or *tk*, handed over before the
    panel is built, as ``Slots.tk`` is). ``sb.boxes`` records each message box;
    *answers* / *inputs* script the dialogs."""
    sb = mock.MagicMock()
    sb.QtCore.Qt = _Qt
    sb.QtWidgets.QTableWidgetItem = _Item
    sb.boxes = []
    replies = iter(answers)
    typed = iter(inputs)

    def _box(text, *buttons):
        sb.boxes.append(text)
        return next(replies, None)

    sb.message_box.side_effect = _box
    sb.input_dialog.side_effect = lambda *a, **k: next(typed, None)
    sb.defer_with_timer.side_effect = lambda fn, ms=0: None
    sb.busy_cursor.side_effect = lambda: contextlib.nullcontext()
    sb.bar = []

    @contextlib.contextmanager
    def _progress(ui=None, total=None, text="", busy=None):
        sb.bar.append(("start", total, text))
        yield lambda value=None, message=None: sb.bar.append((value, message)) or True

    sb.progress.side_effect = _progress
    sb.progress_adapter.side_effect = lambda update: (
        lambda current, total, message: update(current, message)
    )
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.ReferenceManager.return_value = engine or _engine()
    ui = sb.loaded_ui.reference_manager
    ui.tbl000 = _Table()
    ui.cmb000 = _Combo()
    ui.txt000 = _Field("")
    ui.footer = _Footer()
    ui.settings = _Settings()
    ui.header.menu = menu if menu is not None else _header_menu()
    ui.txt001.option_box.menu = SimpleNamespace(
        chk_ignore_case=_Check(True),
        cmb_filter_target=SimpleNamespace(currentText=lambda: "Filter: All"),
    )
    slots = ReferenceManagerSlots(sb)
    return slots, sb


def _list(slots, files, workspace="C:/proj", notes=None):
    """Browse *workspace* holding *files* and list them (a real engine's scan cache
    is seeded, a fake's answered; the folders of a fake need not exist)."""
    c = slots.controller
    c.ui.cmb000.items = [(os.path.basename(workspace), workspace)]
    c.ui.cmb000.index = 0
    cache = {workspace: list(files)}
    real = not isinstance(c.engine, mock.Mock)
    if real:
        c.engine._workspace_files = cache
    else:
        c.engine.workspace_files = cache
    notes = notes or {}
    isdir = (
        contextlib.nullcontext()
        if real
        else mock.patch.object(os.path, "isdir", return_value=True)
    )
    with mock.patch.object(type(c), "note", lambda self, p: notes.get(p, "")), isdir:
        c.refresh_file_list()
    return c.ui.tbl000


def _row(table, name):
    for (r, col), item in table._items.items():
        if col == 0 and os.path.basename(item.data(_Qt.UserRole) or "") == name:
            return r, item
    raise AssertionError(f"no row for {name}")


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


# ----------------------------------------------------------------------------- tests
class TestComposition(_PanelCase):
    def test_the_engine_is_composed_with_the_panels_collaborators(self):
        slots, sb = _panel()
        c = slots.controller
        sb.tk.ReferenceManager.assert_called_once_with(
            progress=c.files.conversion_progress,
            bake_for_reference=c.files.bake_foreign_path,
            report=c.report,
        )
        self.assertIs(c.engine, sb.tk.ReferenceManager.return_value)

    def test_a_scene_opened_anywhere_relists(self):
        slots, sb = _panel()
        mgr = sb.tk.ScriptJobManager.instance.return_value
        event, callback = mgr.subscribe.call_args.args
        self.assertEqual(event, "SceneOpened")
        self.assertIs(mgr.subscribe.call_args.kwargs["owner"], slots)
        mgr.connect_cleanup.assert_called_once_with(slots.ui, owner=slots)
        callback()
        sb.defer_with_timer.assert_any_call(slots.controller.refresh_file_list, ms=0)

    def test_the_engines_report_is_escaped(self):
        slots, sb = _panel()
        slots.controller.report("Can't read </World>\nUnlink and Import it instead.")
        self.assertEqual(
            sb.boxes[-1], "Can't read &lt;/World&gt;<br>Unlink and Import it instead."
        )

    def test_the_module_imports_no_host(self):
        source = inspect.getsource(panel_module)
        for host in ("mayatk", "blendertk", "maya.", "bpy"):
            self.assertNotIn(f"import {host}", source)


class TestListing(_PanelCase):
    def test_rows_carry_their_path_label_and_full_name(self):
        slots, _ = _panel()
        table = _list(slots, ["C:/proj/scenes/hero_v01.ma", "C:/proj/scenes/set.mb"])
        self.assertEqual(table.rowCount(), 2)
        _r, item = _row(table, "hero_v01.ma")
        self.assertEqual(item.text(), "hero_v01.ma")
        self.assertEqual(item.tooltip, "hero_v01.ma")
        self.assertTrue(item.flags() & _Qt.ItemIsEditable)
        self.assertTrue(item.flags() & _Qt.ItemIsSelectable)

    def test_include_types_filter_the_cached_scan(self):
        slots, _ = _panel()
        table = _list(slots, ["C:/proj/a.ma", "C:/proj/b.fbx", "C:/proj/c.usda"])
        self.assertEqual(table.rowCount(), 1, "only the host's defaults list")
        slots.ui.header.menu.chk_include_usd.checked = True
        table = _list(slots, ["C:/proj/a.ma", "C:/proj/b.fbx", "C:/proj/c.usda"])
        self.assertEqual(table.rowCount(), 2, "usd lists every USD spelling")

    def test_without_a_menu_the_engines_defaults_list(self):
        slots, _ = _panel()
        slots.ui.header = None
        self.assertEqual(
            slots.controller.included_extensions(), set(MAYA_FACTS["INCLUDE_DEFAULTS"])
        )

    def test_a_foreign_row_toggles_like_a_native_row_but_is_never_selected(self):
        engine = _engine(
            refs=[_Ref("C:/proj/cache/bridge/abc.ma", "room")],
            bakes={"C:/proj/cache/bridge/abc.ma": "C:/proj/scenes/room.blend"},
        )
        engine.find_foreign_scenes.return_value = ["C:/proj/scenes/room.blend"]
        slots, _ = _panel(engine)
        slots.ui.header.menu.chk_include_blend.checked = True
        table = _list(slots, ["C:/proj/scenes/hero.ma"])
        row, item = _row(table, "room.blend")
        self.assertEqual(table.actions.states[(row, 1)], "referenced")
        self.assertFalse(item.flags() & _Qt.ItemIsSelectable)
        self.assertFalse(item.flags() & _Qt.ItemIsEditable)
        self.assertFalse(item.isSelected(), "a foreign row stays out of the selection")

    def test_a_referenced_bake_is_listed_by_its_source_row_not_as_external(self):
        engine = _engine(
            refs=[_Ref("C:/proj/cache/bridge/abc.ma", "shots")],
            bakes={"C:/proj/cache/bridge/abc.ma": "C:/proj/scenes/shots.fbx"},
        )
        slots, _ = _panel(engine)
        slots.ui.header.menu.chk_include_fbx.checked = True
        table = _list(slots, ["C:/proj/scenes/shots.fbx"])
        self.assertEqual(table.rowCount(), 1)
        row, item = _row(table, "shots.fbx")
        self.assertEqual(item.text(), "shots.fbx")
        self.assertEqual(table.actions.states[(row, 1)], "referenced")
        self.assertTrue(
            item.isSelected(), "the selection shows the row the bake stands for"
        )

    def test_an_external_reference_is_listed_first_and_tagged(self):
        slots, _ = _panel(_engine(refs=[_Ref("D:/elsewhere/prop.ma")]))
        table = _list(slots, ["C:/proj/scenes/hero.ma"])
        self.assertEqual(table.item(0, 0).text(), "prop.ma (External)")

    def test_the_current_scene_is_marked_and_cannot_be_selected(self):
        slots, _ = _panel(_engine(current="C:/proj/scenes/hero.ma"))
        table = _list(slots, ["C:/proj/scenes/hero.ma"])
        row, item = _row(table, "hero.ma")
        self.assertFalse(item.flags() & _Qt.ItemIsSelectable)
        self.assertEqual(table.actions.states[(row, 2)], "current")
        self.assertIn(("hero.ma", "current", True), table.formatted)

    def test_a_reused_foreign_item_becomes_editable_for_a_native_row(self):
        slots, _ = _panel()
        slots.ui.header.menu.chk_include_blend.checked = True
        _list(slots, ["C:/proj/a.blend"])
        table = _list(slots, ["C:/proj/b.ma"])
        self.assertTrue(table.item(0, 0).flags() & _Qt.ItemIsEditable)
        self.assertEqual(
            table.item(0, 0).tooltip, "b.ma", "the tooltip follows the reuse"
        )

    def test_the_text_filter_reads_names_and_notes(self):
        slots, _ = _panel()
        files = ["C:/proj/hero_ACTION.ma", "C:/proj/set.ma", "C:/proj/other.ma"]
        notes = {"C:/proj/set.ma": "Layout, Speedrun"}
        slots.controller.filter_text = "*ACTION*, Speedrun"
        table = _list(slots, files, notes=notes)
        visible = {
            os.path.basename(table.item(r, 0).data(_Qt.UserRole))
            for r in range(table.rowCount())
            if not table.isRowHidden(r)
        }
        self.assertEqual(visible, {"hero_ACTION.ma", "set.ma"})
        slots.controller.filter_text = ""
        table = _list(slots, files, notes=notes)
        self.assertEqual(table.hidden_rows, set())
        self.assertIn("3 file(s)", slots.ui.footer.text[0])

    def test_files_only_ignores_the_notes(self):
        slots, _ = _panel()
        slots.ui.txt001.option_box.menu.cmb_filter_target = SimpleNamespace(
            currentText=lambda: "Filter: Files"
        )
        slots.controller.filter_text = "Speedrun"
        table = _list(slots, ["C:/proj/set.ma"], notes={"C:/proj/set.ma": "Speedrun"})
        self.assertEqual(table.hidden_rows, {0})
        self.assertIn("hidden by the filters", slots.ui.footer.text[0])

    def test_a_refresh_follows_the_bakes_before_it_lists(self):
        engine = _engine()
        order = []
        engine.follow_bake_sources.side_effect = lambda: order.append("follow") or []
        type(engine).workspace_files = mock.PropertyMock(
            side_effect=lambda: order.append("list") or {}
        )
        slots, _ = _panel(engine)
        slots.ui.cmb000.items = [("proj", "C:/proj")]
        slots.ui.cmb000.index = 0
        with mock.patch.object(os.path, "isdir", return_value=True):
            slots.controller.refresh_file_list()
        self.assertEqual(order[:2], ["follow", "list"])

    def test_the_notes_column_shows_only_when_asked(self):
        slots, _ = _panel()
        slots.controller.apply_notes_column_visibility()
        self.assertTrue(slots.ui.tbl000.hidden_columns[4])
        slots.ui.header.menu.chk_show_notes_column.checked = True
        slots.controller.apply_notes_column_visibility()
        self.assertFalse(slots.ui.tbl000.hidden_columns[4])


class TestNotes(_PanelCase):
    def test_notes_kept_in_the_panels_settings_move_into_the_project_store(self):
        slots, _ = _panel()
        slots.ui.settings["reference_notes"] = {"C:/proj/a.ma": "lighting"}
        with mock.patch.object(ptk.SceneNotes, "import_notes", return_value={}) as imp:
            slots.controller.migrate_settings_notes()
        imp.assert_called_once_with({"C:/proj/a.ma": "lighting"})
        self.assertEqual(slots.ui.settings["reference_notes"], {})

    def test_a_note_edit_is_saved_by_its_rows_path(self):
        slots, _ = _panel()
        item = _Item("  lighting pass ")
        item._col = 4
        item.setData(_Qt.UserRole, "C:/proj/a.ma")
        with mock.patch.object(ptk.SceneNotes, "set") as set_note:
            slots.controller.item_changed(item)
        set_note.assert_called_once_with("C:/proj/a.ma", "lighting pass")

    def test_a_store_that_cannot_be_written_is_said(self):
        slots, _ = _panel()
        with (
            mock.patch.object(
                ptk.SceneNotes, "set", side_effect=PermissionError(13, "denied")
            ),
            mock.patch.object(
                ptk.SceneNotes, "store_path", return_value="C:/proj/x.json"
            ),
        ):
            slots.controller.set_note("C:/proj/a.ma", "x")
        self.assertIn("read-only", slots.ui.footer.text[0])


class TestSelectionIsTheReferenceSet(_PanelCase):
    def test_selecting_references_and_deselecting_removes(self):
        engine = _engine(refs=[_Ref("C:/proj/b.ma", "b")])
        slots, _ = _panel(engine)
        table = _list(slots, ["C:/proj/a.ma", "C:/proj/b.ma"])
        _ra, a = _row(table, "a.ma")
        _rb, b = _row(table, "b.ma")
        a.setSelected(True)
        b.setSelected(False)
        slots.controller.handle_item_selection()
        engine.add_reference.assert_called_once_with("a.ma", "C:/proj/a.ma")
        engine.remove_references.assert_called_once_with(["b"])

    def test_a_reference_no_row_lists_survives_a_click(self):
        """An FBX the Include Types hide is in the scan but no row: a click on an
        unrelated row never un-references it."""
        engine = _engine(refs=[_Ref("C:/proj/prop.fbx", "prop")])
        slots, _ = _panel(engine)
        table = _list(slots, ["C:/proj/a.ma", "C:/proj/prop.fbx"])
        self.assertEqual(table.rowCount(), 1)
        _ra, a = _row(table, "a.ma")
        a.setSelected(True)
        slots.controller.handle_item_selection()
        engine.remove_references.assert_not_called()

    def test_a_failed_reference_is_deselected(self):
        engine = _engine()
        engine.add_reference.return_value = False
        slots, _ = _panel(engine)
        table = _list(slots, ["C:/proj/a.ma"])
        _r, a = _row(table, "a.ma")
        a.setSelected(True)
        slots.controller.handle_item_selection()
        self.assertFalse(a.isSelected())

    def test_a_link_error_is_shown(self):
        engine = _engine()
        engine.add_reference.side_effect = RuntimeError("bad <file>")
        slots, sb = _panel(engine)
        table = _list(slots, ["C:/proj/a.ma"])
        _r, a = _row(table, "a.ma")
        a.setSelected(True)
        slots.controller.handle_item_selection()
        self.assertIn("bad &lt;file&gt;", sb.boxes[-1])


class TestRowToggles(_PanelCase):
    def test_a_referenced_rows_icon_removes_every_reference_it_stands_for(self):
        engine = _engine(refs=[_Ref("C:/proj/a.ma", "a"), _Ref("C:/proj/a.ma", "a1")])
        slots, _ = _panel(engine)
        table = _list(slots, ["C:/proj/a.ma"])
        row, item = _row(table, "a.ma")
        slots.controller.references.toggle_reference_at_row(row)
        engine.remove_references.assert_called_once_with(["a", "a1"])
        self.assertFalse(item.isSelected())

    def test_referencing_the_open_scene_closes_it_and_sticks_in_one_click(self):
        engine = _engine(current="C:/proj/a.ma")
        engine.new_scene.side_effect = lambda: (
            engine.current_scene.configure_mock(return_value="") or True
        )
        slots, _ = _panel(engine)
        table = _list(slots, ["C:/proj/a.ma"])
        row, _item = _row(table, "a.ma")
        slots.controller.references.toggle_reference_at_row(row)
        engine.new_scene.assert_called_once_with()
        engine.add_reference.assert_called_once_with("a.ma", "C:/proj/a.ma")

    def test_unsaved_work_declined_keeps_the_open_scene(self):
        engine = _engine(current="C:/proj/a.ma")
        engine.scene_modified.return_value = True
        slots, _ = _panel(engine, answers=("Cancel",))
        table = _list(slots, ["C:/proj/a.ma"])
        row, _item = _row(table, "a.ma")
        slots.controller.references.toggle_reference_at_row(row)
        engine.new_scene.assert_not_called()
        engine.add_reference.assert_not_called()

    def test_a_foreign_row_references_its_bake_under_the_sources_stem(self):
        engine = _engine()
        engine.bake_project_root.return_value = "C:/proj"
        engine.bake_scene.return_value = "C:/proj/cache/bridge/abc.ma"
        engine.find_foreign_scenes.return_value = ["C:/proj/scenes/room.blend"]
        slots, sb = _panel(engine)
        slots.ui.header.menu.chk_include_blend.checked = True
        table = _list(slots, [])
        row, _item = _row(table, "room.blend")
        slots.controller.references.toggle_reference_at_row(row)
        kwargs = engine.bake_scene.call_args.kwargs
        self.assertEqual(kwargs["project"], "C:/proj")
        self.assertEqual((kwargs["via"], kwargs["rig_mode"]), ("fbx", "auto"))
        engine.add_reference.assert_called_once_with(
            "room", "C:/proj/cache/bridge/abc.ma"
        )

    def test_the_display_icon_cycles_the_rows_references(self):
        engine = _engine(refs=[_Ref("C:/proj/a.ma")])
        slots, _ = _panel(engine)
        table = _list(slots, ["C:/proj/a.ma"])
        row, _item = _row(table, "a.ma")
        slots.controller.references.cycle_display_mode_at_row(row)
        engine.set_reference_display_mode.assert_called_once_with(
            engine.current_references[0], "reference"
        )
        self.assertEqual(table.actions.states[(row, 3)], "reference")

    def test_a_display_click_without_a_reference_shows_the_truth(self):
        slots, _ = _panel()
        table = _list(slots, ["C:/proj/a.ma"])
        row, _item = _row(table, "a.ma")
        slots.controller.references.cycle_display_mode_at_row(row)
        self.assertEqual(table.actions.states[(row, 3)], "unavailable")

    def test_the_open_icon_closes_the_open_scene(self):
        engine = _engine(current="C:/proj/a.ma")
        engine.new_scene.return_value = True
        slots, _ = _panel(engine)
        table = _list(slots, ["C:/proj/a.ma"])
        row, _item = _row(table, "a.ma")
        slots.controller.files.open_scene_at_row(row)
        engine.new_scene.assert_called_once_with()
        engine.open_scene.assert_not_called()

    def test_the_open_icon_opens_another_row_guarded(self):
        engine = _engine()
        slots, _ = _panel(engine)
        table = _list(slots, ["C:/proj/b.ma"])
        row, _item = _row(table, "b.ma")
        slots.controller.files.open_scene_at_row(row)
        engine.open_scene.assert_called_once_with("C:/proj/b.ma")

    def test_an_open_error_is_shown_escaped(self):
        engine = _engine()
        engine.open_scene.side_effect = RuntimeError("bad </World>")
        slots, sb = _panel(engine)
        self.assertFalse(slots.controller.files.open_path("C:/proj/R&D.ma"))
        self.assertIn("R&amp;D.ma", sb.boxes[-1])
        self.assertIn("&lt;/World&gt;", sb.boxes[-1])

    def test_a_foreign_open_says_what_it_opened(self):
        engine = _engine()
        engine.open_scene.return_value = True
        slots, _ = _panel(engine)
        slots.controller.files.open_path("C:/proj/room.blend")
        text, level = slots.ui.footer.text
        self.assertIn("room.blend", text)
        self.assertEqual(level, "success")


class TestContextMenu(_PanelCase):
    def test_the_open_action_reads_reopen_on_the_open_scenes_row(self):
        slots, _ = _panel(_engine(current="C:/proj/a.ma"))
        table = _list(slots, ["C:/proj/a.ma", "C:/proj/b.ma"])
        table.has_menu = True
        ra, _a = _row(table, "a.ma")
        rb, _b = _row(table, "b.ma")
        slots.controller.capture_context_row(ra)
        table.menu.btn_open_scene.setText.assert_called_with("Reopen")
        slots.controller.capture_context_row(rb)
        table.menu.btn_open_scene.setText.assert_called_with("Open")

    def test_a_menuless_table_is_left_alone(self):
        slots, _ = _panel()
        table = _list(slots, ["C:/proj/a.ma"])
        table.has_menu = False
        table.menu = None
        slots.controller.capture_context_row(0)  # must not touch table.menu

    def test_empty_space_targets_nothing(self):
        slots, sb = _panel()
        _list(slots, ["C:/proj/a.ma"])
        slots.controller.capture_context_row(-1)
        self.assertIsNone(slots.controller.context_row())
        slots.btn_copy_path()
        self.assertEqual(sb.boxes[-1], "No scene selected.")

    def test_copy_path_puts_the_rows_path_on_the_clipboard(self):
        slots, sb = _panel()
        _list(slots, ["C:/proj/a.ma"])
        slots.controller.capture_context_row(0)
        slots.btn_copy_path()
        sb.QtWidgets.QApplication.clipboard.return_value.setText.assert_called_once_with(
            os.path.normpath("C:/proj/a.ma")
        )


class TestUnsavedChangesPrompt(_PanelCase):
    def _files(self, modified=True, answers=(), saved=True, **kw):
        engine = _engine(**kw)
        engine.scene_modified.return_value = modified
        if isinstance(saved, Exception):
            engine.save_open_scene.side_effect = saved
        else:
            engine.save_open_scene.return_value = saved
        slots, sb = _panel(engine, answers=answers)
        return slots.controller.files, engine, sb

    def test_a_clean_scene_asks_nothing(self):
        files, _engine_, sb = self._files(modified=False)
        self.assertTrue(files.confirm_discard_unsaved())
        self.assertEqual(sb.boxes, [])

    def test_cancel_aborts_and_discard_proceeds(self):
        files, engine, _sb = self._files(answers=("Cancel",))
        self.assertFalse(files.confirm_discard_unsaved())
        files, engine, _sb = self._files(answers=("Discard",))
        self.assertTrue(files.confirm_discard_unsaved())
        engine.save_open_scene.assert_not_called()

    def test_save_flushes_in_place(self):
        files, engine, _sb = self._files(answers=("Save",))
        self.assertTrue(files.confirm_discard_unsaved())
        engine.save_open_scene.assert_called_once_with()

    def test_a_reopen_declined_keeps_the_open_scene(self):
        files, engine, _sb = self._files(answers=("Cancel",), current="C:/proj/a.ma")
        self.assertFalse(files.open_path("C:/proj/a.ma"))
        engine.open_scene.assert_not_called()

    def test_a_failed_save_aborts(self):
        files, _engine_, sb = self._files(answers=("Save",), saved=RuntimeError("disk"))
        self.assertFalse(files.confirm_discard_unsaved())
        self.assertIn("Failed to save the open scene", sb.boxes[-1])

    def test_a_scene_that_cannot_save_in_place_goes_through_save_to_workspace(self):
        files, engine, _sb = self._files(answers=("Save",), saved=None)
        with mock.patch.object(type(files), "save_to_workspace") as save:
            self.assertFalse(files.confirm_discard_unsaved(), "still modified: abort")
        save.assert_called_once_with()


class TestNaming(_PanelCase):
    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp(prefix="tentacle_rm_naming_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.ws = os.path.join(self.root, "proj")
        os.makedirs(os.path.join(self.ws, "scenes"))

    def _slots(
        self, facts=MAYA_FACTS, current="", suffix="_v01", structure="{scenes}/{name}"
    ):
        slots, sb = _panel(
            _engine(facts, current=current),
            menu=_header_menu("None", suffix, structure),
        )
        slots.ui.cmb000.items = [("proj", self.ws)]
        slots.ui.cmb000.index = 0
        return slots, sb

    def test_the_save_target_is_workspace_structure_and_suffixed_name(self):
        slots, _ = self._slots()
        target = slots.controller.files.resolve_save_target(
            "hero", "None", "_v01", "{scenes}/{name}"
        )
        self.assertEqual(
            target,
            os.path.normpath(os.path.join(self.ws, "scenes", "hero", "hero_v01.ma")),
        )

    def test_blenders_engine_saves_a_blend(self):
        slots, _ = self._slots(facts=BLENDER_FACTS)
        target = slots.controller.files.resolve_save_target("hero", "None", "", "")
        self.assertTrue(target.endswith("hero.blend"))

    def test_an_invalid_workspace_is_refused(self):
        slots, _ = self._slots()
        slots.ui.cmb000.items = [("gone", os.path.join(self.root, "gone"))]
        with self.assertRaises(ValueError):
            slots.controller.files.resolve_save_target("hero", "None", "", "")

    def test_the_default_save_name_drops_every_trailing_suffix_and_keeps_dots(self):
        slots, _ = self._slots(current="C:/x/hero.rig_v01_v01.ma")
        self.assertEqual(
            slots.controller.files.default_save_name("None", "_v01"), "hero.rig"
        )

    def test_save_writes_a_typed_suffix_once(self):
        engine = _engine()
        slots, _ = _panel(
            engine, inputs=("villain_v01",), menu=_header_menu("None", "_v01")
        )
        slots.ui.cmb000.items = [("proj", self.ws)]
        slots.ui.cmb000.index = 0
        slots.controller.files.save_to_workspace()
        path = engine.save_scene.call_args.args[0]
        self.assertEqual(os.path.basename(path), "villain_v01.ma")
        self.assertEqual(os.path.basename(os.path.dirname(path)), "scenes")

    def test_the_scene_typo_reads_as_scenes(self):
        slots, _ = self._slots()
        self.assertEqual(
            slots.controller.files.normalize_structure_pattern(" {scene}/{name} "),
            "{scenes}/{name}",
        )

    def test_the_save_preview_shows_the_exact_path(self):
        slots, sb = self._slots(
            current=os.path.join(self.ws, "scenes", "villain_v01_v01.ma")
        )
        slots.controller.files.save_scene_preview()
        rows = sb.tooltip.fmt.call_args.kwargs["rows"]
        self.assertIn(
            os.path.normpath(
                os.path.join(self.ws, "scenes", "villain", "villain_v01.ma")
            ),
            rows[0][1],
        )

    def test_rename_prefills_without_the_suffix_and_moves_the_folder_without_it(self):
        old = os.path.join(self.ws, "scenes", "hero", "hero_v01.ma")
        os.makedirs(os.path.dirname(old))
        open(old, "w").close()
        engine = _engine()
        engine.rename_scene_file.return_value = os.path.join(
            self.ws, "scenes", "villain", "villain_v01.ma"
        )
        slots, sb = _panel(
            engine,
            inputs=("villain_v01",),
            menu=_header_menu("None", "_v01", "{scenes}/{name}"),
        )
        slots.ui.cmb000.items = [("proj", self.ws)]
        slots.ui.cmb000.index = 0
        slots.ui.tbl000.setRowCount(1)
        item = _Item("hero")
        item.setData(_Qt.UserRole, old)
        slots.ui.tbl000.setItem(0, 0, item)
        slots.controller.context_menu_row = 0
        with mock.patch.object(ptk.SceneNotes, "move") as move:
            slots.controller.files.rename_scene()
        self.assertEqual(sb.input_dialog.call_args.args[2], "hero")
        engine.rename_scene_file.assert_called_once_with(
            old, os.path.join(os.path.dirname(old), "villain_v01.ma"), folder="villain"
        )
        move.assert_called_once()

    def test_an_unchanged_answer_renames_nothing(self):
        old = os.path.join(self.ws, "scenes", "hero_v01.ma")
        open(old, "w").close()
        engine = _engine()
        slots, _ = _panel(engine, inputs=("hero",), menu=_header_menu("None", "_v01"))
        slots.ui.tbl000.setRowCount(1)
        item = _Item("hero")
        item.setData(_Qt.UserRole, old)
        slots.ui.tbl000.setItem(0, 0, item)
        slots.controller.context_menu_row = 0
        slots.controller.files.rename_scene()
        engine.rename_scene_file.assert_not_called()

    def test_an_inline_rename_passes_the_typed_stem_less_the_suffix(self):
        old = os.path.join(self.ws, "scenes", "hero", "hero_v01.ma")
        os.makedirs(os.path.dirname(old))
        open(old, "w").close()
        engine = _engine()
        engine.rename_scene_file.return_value = None
        slots, _ = _panel(engine, menu=_header_menu("None", "_v01", "{scenes}/{name}"))
        item = _Item("villain_v01.ma")
        item.setData(_Qt.UserRole, old)
        item.setData(_Qt.UserRole + 2, "hero_v01.ma")
        slots.controller.editing_item = item
        slots.controller.item_changed(item)
        engine.rename_scene_file.assert_called_once_with(
            old, os.path.join(os.path.dirname(old), "villain_v01.ma"), folder="villain"
        )
        self.assertEqual(
            item.text(), "hero_v01.ma", "a refused rename restores the label"
        )

    def test_a_naming_edit_refilters_only_when_a_filter_reads_it(self):
        slots, _ = _panel()
        with mock.patch.object(type(slots.controller), "refresh_file_list") as refresh:
            slots.txt_suffix("_v02")
            refresh.assert_not_called()
            slots.ui.header.menu.chk_hide_suffix.checked = True
            slots.txt_subfolder_structure("{scenes}/{name}")
            refresh.assert_called_once_with(invalidate=False)

    def test_a_folder_kept_report_reaches_the_user(self):
        slots, sb = _panel()
        slots.controller.report(
            "Renamed the scene, but its folder kept the old name:\nX"
        )
        self.assertIn("kept the old name", sb.boxes[-1])


class TestDelete(_PanelCase):
    def _delete(self, answers, removed, can_trash=True, structure="{scenes}/{name}"):
        engine = _engine()
        engine.remove_scene_file.side_effect = list(removed)
        slots, sb = _panel(
            engine, answers=answers, menu=_header_menu(structure=structure)
        )
        root = tempfile.mkdtemp(prefix="tentacle_rm_delete_")
        self.addCleanup(shutil.rmtree, root, True)
        path = os.path.join(root, "hero_v01.ma")
        open(path, "w").close()
        slots.ui.tbl000.setRowCount(1)
        item = _Item("hero")
        item.setData(_Qt.UserRole, path)
        slots.ui.tbl000.setItem(0, 0, item)
        slots.controller.context_menu_row = 0
        with (
            mock.patch.object(ptk.FileUtils, "can_trash", return_value=can_trash),
            mock.patch.object(ptk.SceneNotes, "remove") as notes,
        ):
            slots.controller.files.delete_scene()
        return engine, sb, notes, path

    def test_no_keeps_the_file(self):
        engine, sb, _notes, _path = self._delete(("No",), [])
        engine.remove_scene_file.assert_not_called()
        self.assertIn("hero_v01.ma", sb.boxes[0])

    def test_yes_trashes_it_and_drops_its_note(self):
        engine, sb, notes, path = self._delete(("Yes",), [True])
        engine.remove_scene_file.assert_called_once_with(
            path, permanent=False, use_folder=True
        )
        self.assertIn(ptk.FileUtils.trash_name(), sb.boxes[0])
        notes.assert_called_once_with(path)

    def test_a_drive_with_no_trash_asks_as_permanent(self):
        engine, sb, _notes, path = self._delete(("Yes",), [True], can_trash=False)
        self.assertIn("permanently", sb.boxes[0])
        engine.remove_scene_file.assert_called_once_with(
            path, permanent=True, use_folder=True
        )

    def test_a_trash_that_refuses_asks_again_before_anything_is_lost(self):
        engine, sb, notes, path = self._delete(("Yes", "No"), [None])
        self.assertEqual(len(sb.boxes), 2)
        self.assertIn("permanently", sb.boxes[1])
        notes.assert_not_called()
        engine, _sb, _notes, path = self._delete(("Yes", "Yes"), [None, True])
        self.assertEqual(engine.remove_scene_file.call_args.kwargs["permanent"], True)

    def test_a_flat_structure_keeps_the_folder(self):
        engine, _sb, _notes, path = self._delete(("Yes",), [True], structure="{scenes}")
        self.assertFalse(engine.remove_scene_file.call_args.kwargs["use_folder"])

    def test_a_failed_delete_is_said(self):
        _engine_, sb, notes, _path = self._delete(("Yes",), [False])
        self.assertIn("Could not delete", sb.boxes[-1])
        notes.assert_not_called()


class TestListingRules(unittest.TestCase):
    def test_a_suffix_hides_only_at_the_end_of_the_stem(self):
        self.assertEqual(
            SceneListing.display_name("C:/p/ITA_LOCKHANDLE.ma", False, "_LOC"),
            "ITA_LOCKHANDLE.ma",
        )
        self.assertEqual(
            SceneListing.display_name("C:/p/hero_LOC.ma", False, "_LOC"), "hero.ma"
        )
        self.assertEqual(
            SceneListing.display_name("C:/p/hero_LOC.ma", True, "_LOC"), "hero"
        )
        self.assertEqual(
            SceneListing.display_name("C:/p/hero.ma", False, ""), "hero.ma"
        )

    def test_notes_match_whole_or_by_segment(self):
        m = SceneListing.matches_notes_filter
        self.assertTrue(m("Layout, Speedrun", "*Speed*"))
        self.assertTrue(m("Layout, Speedrun", "Layout*"))
        self.assertTrue(m("Layout; Speedrun", "Speedrun"))
        self.assertTrue(m("layout", "LAYOUT"))
        self.assertFalse(m("layout", "LAYOUT", ignore_case=False))
        self.assertTrue(m("Layout", "nope, Layout"))
        self.assertFalse(m("", "*"))
        self.assertFalse(m("Layout", ""))

    def test_the_folder_structure_resolves_scenes(self):
        kept = SceneListing.filter_by_folder_structure(
            ["C:/proj/scenes/hero/hero_v01.ma", "C:/proj/loose.ma"],
            "C:/proj",
            "{scenes}/{name}",
            "_v01",
            "scenes",
        )
        self.assertEqual(kept, ["C:/proj/scenes/hero/hero_v01.ma"])

    def test_the_delete_prompt_names_and_caps(self):
        trash = ptk.FileUtils.trash_name()
        self.assertIn("hero.ma", SceneListing.delete_prompt(["C:/p/hero.ma"]))
        self.assertIn(trash, SceneListing.delete_prompt(["C:/p/hero.ma"]))
        gone = SceneListing.delete_prompt(["C:/p/a.ma"], ["C:/p/a.ma"])
        self.assertIn("permanently", gone)
        self.assertIn("cannot be undone", gone)
        mixed = SceneListing.delete_prompt(["C:/p/a.ma", "C:/p/b.ma"], ["C:/p/b.ma"])
        self.assertIn("b.ma (permanently", mixed)
        self.assertNotIn("a.ma (permanently", mixed)
        many = [f"C:/p/{i}.ma" for i in range(SceneListing.DELETE_PROMPT_MAX_NAMES + 3)]
        self.assertIn("...and 3 more", SceneListing.delete_prompt(many))

    def test_format_name_keeps_the_suffix_out_of_the_case(self):
        self.assertEqual(SceneListing.format_name("hero", "upper", "_v01"), "HERO_v01")
        self.assertEqual(SceneListing.format_name("hero", "Case: upper"), "HERO")
        self.assertEqual(SceneListing.format_name("hero", "None", ""), "hero")


class TestWorkspaces(_PanelCase):
    def test_history_is_per_root_and_capped(self):
        slots, _ = _panel()
        w = slots.controller.workspaces
        w.save_workspace_selection("C:/Root/", "a")
        w.save_workspace_selection("D:/other", "b")
        history = slots.ui.settings["workspace_history"]
        self.assertEqual(history[_norm("C:/Root")], "a")
        for i in range(60):
            w.save_workspace_selection(f"C:/r{i}", "x")
        self.assertEqual(
            len(slots.ui.settings["workspace_history"]), w.WORKSPACE_HISTORY_MAX
        )

    def test_the_combo_prefers_memory_then_history_then_the_first(self):
        engine = _engine()
        engine.find_available_workspaces.return_value = [
            ("a", "C:/r/a"),
            ("b", "C:/r/b"),
        ]
        slots, _ = _panel(engine)
        slots.ui.txt000.setText("C:/r")
        w = slots.controller.workspaces
        with mock.patch.object(os.path, "isdir", return_value=True):
            w.save_workspace_selection("C:/r", "b")
            w.update_workspace_combo()
            self.assertEqual(slots.ui.cmb000.currentIndex(), 1, "history")
            slots.ui.settings.clear()
            w.update_workspace_combo()
            self.assertEqual(slots.ui.cmb000.currentIndex(), 1, "in-memory")
            slots.ui.cmb000.clear()
            w.update_workspace_combo()
            self.assertEqual(slots.ui.cmb000.currentIndex(), 0, "first")

    def test_the_combo_lists_the_roots_workspaces_not_the_selected_ones(self):
        engine = _engine()
        engine.find_available_workspaces.return_value = [("a", "C:/r/a")]
        slots, _ = _panel(engine)
        slots.ui.txt000.setText("C:/r")
        engine.current_working_dir = "C:/r/a"
        with mock.patch.object(os.path, "isdir", return_value=True):
            slots.controller.workspaces.update_workspace_combo()
        engine.find_available_workspaces.assert_called_with("C:/r")

    def test_a_trailing_separator_is_no_change(self):
        engine = _engine()
        engine.current_working_dir = os.path.normpath("C:/r")
        slots, _ = _panel(engine)
        w = slots.controller.workspaces
        w._last_dir_valid = True
        with (
            mock.patch.object(os.path, "isdir", return_value=True),
            mock.patch.object(type(w), "update_workspace_combo") as repopulate,
        ):
            w.update_current_dir("C:/r/")
            repopulate.assert_not_called()
            w.update_current_dir("C:/elsewhere")
            repopulate.assert_called_once()

    def test_set_project_commits_the_browsed_workspace(self):
        tk = mock.MagicMock()
        tk.ReferenceManager.return_value = _engine()
        tk.EnvUtils.workspace_root.return_value = "C:/old"
        slots, _ = _panel(tk=tk)
        slots.ui.cmb000.items = [("proj", "C:/proj")]
        slots.ui.cmb000.index = 0
        with mock.patch.object(os.path, "isdir", return_value=True):
            self.assertTrue(slots.controller.workspaces.set_project())
        tk.EnvUtils.set_current_workspace.assert_called_once_with("C:/proj")

    def test_set_project_refuses_an_invalid_workspace(self):
        slots, sb = _panel()
        self.assertFalse(slots.controller.workspaces.set_project())
        self.assertIn("valid workspace", sb.boxes[-1])

    def test_a_new_workspace_is_made_under_the_root(self):
        tk = mock.MagicMock()
        tk.ReferenceManager.return_value = _engine()
        slots, _ = _panel(tk=tk)
        slots.ui.txt000.setText("C:/r")
        slots.sb.input_dialog.side_effect = lambda *a: "shot"
        with mock.patch.object(os.path, "isdir", return_value=True):
            slots.controller.workspaces.new_workspace()
        tk.EnvUtils.create_workspace.assert_called_once_with(
            os.path.join("C:/r", "shot")
        )


class TestForeignConversions(_PanelCase):
    def test_a_bake_reports_into_the_footer_and_a_stop_is_no_failure(self):
        engine = _engine()

        def _bake(path, progress=None, project=None, **conv):
            progress(40, 100, "Blender: Writing the FBX")
            raise ptk.OperationCancelled("stop")

        engine.bake_scene.side_effect = _bake
        slots, sb = _panel(engine)
        self.assertIsNone(
            slots.controller.files.bake_foreign_path("C:/proj/mesh.blend")
        )
        self.assertIn((40, "Blender: Writing the FBX"), sb.bar)
        self.assertEqual(sb.bar[0][1], 100)
        self.assertIn("mesh.blend", sb.bar[0][2])
        self.assertEqual(sb.boxes, [], "a stop is not an error box")
        self.assertIn("Stopped converting mesh.blend", slots.ui.footer.text[0])

    def test_a_finished_bake_returns_its_path(self):
        engine = _engine()
        engine.bake_scene.return_value = "C:/cache/mesh.ma"
        slots, _ = _panel(engine)
        self.assertEqual(
            slots.controller.files.bake_foreign_path("C:/p/mesh.blend"),
            "C:/cache/mesh.ma",
        )

    def test_a_missing_converter_is_named(self):
        engine = _engine()
        engine.bake_scene.side_effect = FileNotFoundError("Blender not found")
        slots, sb = _panel(engine)
        slots.controller.files.bake_foreign_path("C:/p/mesh.blend")
        self.assertIn("Blender not found", sb.boxes[-1])

    def test_the_rig_prompt_offers_the_engines_modes(self):
        for facts, answer, expected, offers_raw in (
            (MAYA_FACTS, "Yes", "rig", False),
            (MAYA_FACTS, "No", "bake", False),
            (MAYA_FACTS, "Cancel", None, False),
            (BLENDER_FACTS, "Ignore", "raw", True),
        ):
            with self.subTest(facts=facts["PRESET_DIR"], answer=answer):
                engine = _engine(facts)
                engine.scene_has_complex_animation.return_value = True
                slots, sb = _panel(engine, answers=(answer,))
                self.assertEqual(
                    slots.controller.files.resolve_rig_mode("C:/p/rig.ma"), expected
                )
                self.assertEqual("Ignore" in sb.message_box.call_args.args, offers_raw)

    def test_no_rig_logic_asks_nothing(self):
        slots, sb = _panel()
        self.assertEqual(
            slots.controller.files.resolve_rig_mode("C:/p/a.blend"), "auto"
        )
        self.assertEqual(sb.boxes, [])

    def test_the_route_is_fbx_unless_usd_is_picked(self):
        slots, _ = _panel()
        self.assertEqual(slots.controller.foreign_route(), "fbx")
        slots.ui.header.menu.cmb_conversion_route = SimpleNamespace(
            currentText=lambda: "Convert via USD"
        )
        self.assertEqual(slots.controller.foreign_route(), "usd")
        slots.ui.header = None
        self.assertEqual(slots.controller.foreign_route(), "fbx")

    def test_the_route_combo_selects_fbx_after_its_items(self):
        source = inspect.getsource(ReferenceManagerSlots.header_init)
        block = source[
            source.index('addItems=["Convert via USD", "Convert via FBX"]') :
        ]
        block = block[: block.index('setObjectName="cmb_conversion_route"')]
        self.assertIn("setCurrentIndex=1", block, "the default sits on the FBX item")

    def test_an_unreferenced_usd_row_imports_without_a_question(self):
        engine = _engine()
        engine.import_scene.return_value = ["a"]
        slots, sb = _panel(engine)
        slots.controller.files.import_paths(["C:/p/set.usdc", "C:/p/shot.ma"])
        engine.import_scene.assert_called_once()
        self.assertEqual(engine.import_scene.call_args.args[0], "C:/p/set.usdc")
        self.assertEqual(sb.boxes, [])

    def test_an_import_error_reaches_the_box_as_text(self):
        engine = _engine()
        engine.import_scene.side_effect = RuntimeError("read </World/Crate> & skipped")
        slots, sb = _panel(engine)
        slots.controller.files.import_paths(["C:/p/R&D set.usda"])
        self.assertIn("&lt;/World/Crate&gt;", sb.boxes[-1])
        self.assertIn("R&amp;D set.usda", sb.boxes[-1])


class TestUnlinkAndRemove(_PanelCase):
    def test_the_namespace_action_follows_the_engines_modes(self):
        slots, _ = _panel()
        button = mock.MagicMock()
        slots.controller.references.add_unlink_namespace_action(button)
        states = button.option_box.set_action.call_args.kwargs["states"]
        self.assertEqual(len(states), 3)
        slots, _ = _panel(_engine(BLENDER_FACTS))
        button = mock.MagicMock()
        slots.controller.references.add_unlink_namespace_action(button)
        button.option_box.set_action.assert_not_called()

    def test_the_mode_defaults_to_remove_without_a_menu(self):
        slots, _ = _panel()
        slots.ui.header = None
        self.assertEqual(slots.controller.references.unlink_namespace_mode(), "remove")

    def test_unlink_all_forwards_the_mode_and_asks_about_scene_data(self):
        engine = _engine(refs=[_Ref("C:/p/a.ma")])
        slots, sb = _panel(engine, answers=("Yes",))
        slots.ui.header = None
        slots.controller.references.unlink_all()
        engine.import_references.assert_called_once_with(
            namespace_mode="remove",
            scene_data=slots.controller.references.ask_scene_data,
        )
        self.assertIn("removed", sb.boxes[0])

    def test_blender_names_no_namespace_and_declining_imports_nothing(self):
        engine = _engine(BLENDER_FACTS, refs=[_Ref("C:/p/a.blend")])
        slots, sb = _panel(engine, answers=("No",))
        slots.controller.references.unlink_all()
        self.assertNotIn("namespace", sb.boxes[0])
        engine.import_references.assert_not_called()

    def test_scene_data_answers(self):
        for answer, expected in (("Yes", "merge"), ("No", "discard"), ("Cancel", None)):
            slots, _ = _panel(answers=(answer,))
            self.assertEqual(
                slots.controller.references.ask_scene_data(["shots: 2"], "kit"),
                expected,
            )

    def test_the_rows_unlink_makes_its_references_local_or_imports_it(self):
        engine = _engine(refs=[_Ref("C:/p/a.ma", "a")])
        slots, _ = _panel(engine, answers=("Yes",))
        table = _list(slots, ["C:/p/a.ma"], workspace="C:/p")
        slots.controller.context_menu_row = _row(table, "a.ma")[0]
        slots.controller.references.unlink_import_row()
        self.assertEqual(engine.import_references.call_args.kwargs["namespaces"], ["a"])
        for path, imports in (("C:/p/set.usdc", True), ("C:/p/shot.ma", False)):
            engine = _engine()
            slots, sb = _panel(engine)
            slots.ui.header.menu.chk_include_usd.checked = True
            table = _list(slots, [path], workspace="C:/p")
            slots.controller.context_menu_row = 0
            with mock.patch.object(type(slots.controller.files), "import_paths") as imp:
                slots.controller.references.unlink_import_row()
            self.assertEqual(imp.called, imports, path)

    def test_unreference_all_confirms_and_names_what_stayed(self):
        stuck = _Ref("C:/p/b.ma", "b")
        engine = _engine(refs=[_Ref("C:/p/a.ma"), stuck])
        engine.remove_references.return_value = [stuck]
        slots, sb = _panel(engine, answers=("Yes",))
        slots.controller.references.unreference_all()
        engine.remove_references.assert_called_once_with()
        self.assertIn("could not be removed", sb.boxes[-1])
        self.assertIn("b", sb.boxes[-1])

    def test_unreference_all_with_nothing_says_so(self):
        slots, sb = _panel()
        slots.controller.references.unreference_all()
        self.assertEqual(sb.boxes, ["No references to remove."])

    def test_assemblies_are_the_hosts_that_have_them(self):
        tk = mock.MagicMock(spec=["ReferenceManager", "ScriptJobManager", "EnvUtils"])
        tk.ReferenceManager.return_value = _engine(BLENDER_FACTS)
        slots, sb = _panel(tk=tk, answers=("Yes",))
        slots.controller.references.convert_to_assembly()
        self.assertEqual(sb.boxes, [], "no assemblies: nothing to ask")
        slots, sb = _panel(answers=("Yes",))
        slots.controller.references.convert_to_assembly()
        sb.tk.AssemblyManager.convert_references_to_assemblies.assert_called_once_with()


class TestHeaderAndFooter(_PanelCase):
    def _header(self, tk=None):
        slots, sb = _panel(tk=tk)
        header = mock.MagicMock()
        header.is_initialized = False
        added = []

        def _add(kind, **kwargs):
            added.append(kwargs.get("setObjectName") or kwargs.get("setTitle") or kind)
            return mock.MagicMock()

        header.menu.add.side_effect = _add
        slots.header_init(header)
        return slots, header, added

    def test_tap_to_pin_presets_and_naming_before_the_filters(self):
        slots, header, added = self._header()
        self.assertTrue(header.pin_on_tap)
        self.assertEqual(header.menu.presets.preset_dir, "mayatk/reference_manager")
        self.assertLess(added.index("Naming:"), added.index("chk_filter_suffix"))
        self.assertIn("btn_convert_assembly", added)
        header.set_help_text.assert_called_once()

    def test_a_host_without_assemblies_builds_no_button(self):
        tk = mock.MagicMock(spec=["ReferenceManager", "ScriptJobManager", "EnvUtils"])
        tk.ReferenceManager.return_value = _engine(BLENDER_FACTS)
        slots, header, added = self._header(tk=tk)
        self.assertNotIn("btn_convert_assembly", added)
        self.assertEqual(header.menu.presets.preset_dir, "blendertk/reference_manager")

    def test_the_include_row_defaults_to_the_hosts_own_types(self):
        slots, header, _added = self._header()
        items = header.menu.add_row.call_args.args[0]
        checked = {kw["setObjectName"]: kw["setChecked"] for _kind, kw in items}
        self.assertEqual(
            checked,
            {
                "chk_include_ma": True,
                "chk_include_mb": True,
                "chk_include_fbx": False,
                "chk_include_usd": False,
                "chk_include_blend": False,
            },
        )

    def test_the_footer_is_built_once_and_rewired_on_reload(self):
        sb = mock.MagicMock()
        sb.tk.ReferenceManager.return_value = _engine()
        footer = mock.MagicMock()
        footer._rm_actions_built = False
        footer.height.return_value = 20
        sb.loaded_ui.reference_manager.footer = footer
        sb.loaded_ui.reference_manager.txt000 = _Field("")
        sb.loaded_ui.reference_manager.cmb000 = _Combo()
        buttons = []

        def _button(text, parent):
            b = mock.MagicMock()
            b.text = text
            buttons.append(b)
            return b

        sb.QtWidgets.QPushButton.side_effect = _button
        with mock.patch.object(ReferenceManagerSlots, "_rewire_signal") as rewire:
            ReferenceManagerSlots(sb)
            ReferenceManagerSlots(sb)
        self.assertEqual(
            [b.text for b in buttons], ["Un-Reference All", "Save To Workspace"]
        )
        self.assertEqual(rewire.call_count, 4, "both buttons rewired on each build")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestReferenceManagerPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")
        project = self.cmds.workspace(q=True, rd=True)
        self.addCleanup(self.cmds.workspace, project, openWorkspace=True)
        self.addCleanup(self.cmds.file, new=True, force=True)
        self.root = tempfile.mkdtemp(prefix="tentacle_rm_maya_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.ws = os.path.join(self.root, "proj")
        os.makedirs(os.path.join(self.ws, "scenes"))
        self.mtk.EnvUtils.create_workspace(self.ws, create_dirs=False)
        self.prop = os.path.join(self.ws, "scenes", "prop.ma")
        self.cmds.polyCube(name="crate")
        self.cmds.file(rename=self.prop)
        self.cmds.file(save=True, type="mayaAscii")
        self.cmds.file(new=True, force=True)

    def _slots(self):
        slots, _sb = _panel(tk=self.mtk)
        # The real scriptJob subscription outlives the fake window: drop it.
        self.addCleanup(self.mtk.ScriptJobManager.instance().unsubscribe_all, slots)
        return slots

    def test_the_real_engine_is_composed_with_the_panels_collaborators(self):
        slots = self._slots()
        engine = slots.controller.engine
        self.assertIsInstance(engine, self.mtk.ReferenceManager)
        self.assertEqual(engine.SCENE_SAVE_EXTENSION, ".ma")

    def test_the_rows_icon_references_and_removes_the_scene(self):
        slots = self._slots()
        table = _list(slots, [self.prop], workspace=self.ws)
        row, _item = _row(table, "prop.ma")
        slots.controller.references.toggle_reference_at_row(row)
        self.assertEqual(len(self.mtk.ReferenceManager().current_references), 1)
        slots.controller.references.toggle_reference_at_row(row)
        self.assertEqual(self.mtk.ReferenceManager().current_references, [])

    def test_the_open_icon_opens_and_closes_the_scene(self):
        slots = self._slots()
        table = _list(slots, [self.prop], workspace=self.ws)
        row, _item = _row(table, "prop.ma")
        slots.controller.files.open_scene_at_row(row)
        self.assertTrue(slots.controller.engine.is_current(self.prop))
        slots.controller.files.open_scene_at_row(row)
        self.assertEqual(slots.controller.engine.current_scene(), "")


if __name__ == "__main__":
    unittest.main()
