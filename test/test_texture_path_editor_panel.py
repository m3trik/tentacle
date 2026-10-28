#!/usr/bin/python
# coding=utf-8
"""The Texture Path Editor panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` and composes the host's
``TexturePathEditor`` engine, so a fake toolkit stands in for ``mtk`` / ``btk``
here and records what the panel asks of it: plain unittest, no DCC, no widgets
loaded. In Maya, the same class drives the real ``mtk``. The engine's own
behavior (Set Directory, Normalize Paths, Find & Copy, the renames and Keep
Names In Sync, the lightmap records) is tested in mayatk's and blendertk's
``test_texture_path_editor.py``.

The panel-level suites moved here with the panel: mayatk's menu-state,
truncation, Keep Names In Sync, over-long-path, option-flag, footer and
undo-refresh readers, the Find & Copy form (rows, accept text, validator,
re-seed, Apply) and the lightmap rows' scope; blendertk's row-menu fit, fact
columns, material-cell lock and its Qt panel-load checks.
"""

import os
import unittest
from types import SimpleNamespace
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.texture_path_editor import TexturePathEditorSlots

MAYA_LABELS = {
    "shader": "Shader",
    "file_node": "File Node",
    "texture_dir": "Source Images",
    "select_file_node": "Select File Node",
    "graph": "Show in Hypershade",
    "delete": "Delete File Node",
}
BLENDER_LABELS = {
    "shader": "Material",
    "file_node": "Texture",
    "texture_dir": "Textures Folder",
    "select_file_node": "Select Texture Node",
    "graph": "Show in Shader Editor",
    "delete": "Remove Texture",
}
SCENE_EVENTS = (
    ("SceneOpened", False),
    ("NewSceneOpened", False),
    ("Undo", True),
    ("Redo", True),
)


def _engine(
    sb, labels=MAYA_LABELS, exclude_arnold=True, texture_dir="C:/proj/sourceimages"
):
    """Shape the fake toolkit's ``TexturePathEditor`` engine (a MagicMock)."""
    engine = sb.tk.TexturePathEditor.return_value
    engine.LABELS = dict(labels)
    engine.EXCLUDE_ARNOLD = exclude_arnold
    engine.SCENE_EVENTS = SCENE_EVENTS
    engine.FILE_TYPES = ("*.png", "*.*")
    engine.RESOLVE_STRATEGY_ORDER = ("stem", "texture", "fuzzy")
    engine.previous_paths = {}
    engine.active_logger = None
    engine.texture_dir.return_value = texture_dir
    engine.node_exists.return_value = True
    engine.stored_path.side_effect = lambda node: f"C:/ext/{node}.png"
    engine.unresolved_file_nodes.return_value = []
    engine.file_nodes.return_value = ["file1", "file2"]
    engine.rows.return_value = []
    engine.lightmap_dependencies.return_value = []
    engine.lightmap_labels.side_effect = lambda dep: (
        "",
        os.path.splitext(dep["map"])[0],
    )
    engine.resolve_path.side_effect = lambda path, node=None: (True, f"C:/abs/{path}")
    engine.delete_consequences.return_value = []
    return engine


def _panel(selection=(), tk=None, **engine_kwargs):
    """A Slots instance over a mock ui and a mock toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is); returns it and the
    switchboard. The table's selection is *selection*."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        _engine(sb, **engine_kwargs)
    sb.message_box.return_value = None
    ui = sb.loaded_ui.texture_path_editor
    ui.tbl000.get_selection.return_value = list(selection)
    return TexturePathEditorSlots(sb), sb


def _row(file_node="", shader="", path="", row=0):
    """A selection entry, as the table hands one to a row action."""
    return SimpleNamespace(
        row=row, values={"shader": shader, "path": path, "file_node": file_node}
    )


def _check(state):
    return None if state is None else SimpleNamespace(isChecked=lambda: state)


def _combo(index):
    return SimpleNamespace(currentIndex=lambda: index)


def _button(**members):
    """An option-box button whose flyout holds *members*."""
    return SimpleNamespace(option_box=SimpleNamespace(menu=SimpleNamespace(**members)))


def _table():
    """A table widget double the refresh can drive: no rows yet, six columns,
    the fact columns hidden."""
    widget = mock.MagicMock()
    widget.rowCount.return_value = 0
    widget.columnCount.return_value = 6
    widget.blockSignals.return_value = False
    widget.horizontalHeader.return_value.isSectionHidden.return_value = True
    return widget


def _header(slots, **menu_items):
    """Give the panel a built header menu holding *menu_items*."""
    slots.ui.header = SimpleNamespace(menu=SimpleNamespace(**menu_items))
    return slots.ui.header.menu


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestComposition(_PanelCase):
    def test_the_engine_is_composed_never_inherited(self):
        slots, sb = _panel()
        sb.tk.TexturePathEditor.assert_called_once_with()
        self.assertIs(slots.engine, sb.tk.TexturePathEditor.return_value)
        for name in ("set_texture_directory", "rows", "find_and_copy_textures"):
            self.assertFalse(hasattr(TexturePathEditorSlots, name), name)

    def test_the_runtime_widgets_are_the_option_box_buttons(self):
        inits = {
            name[: -len("_init")]
            for name in vars(TexturePathEditorSlots)
            if name.endswith("_init") and name.startswith("tb_")
        }
        self.assertEqual(set(TexturePathEditorSlots.RUNTIME_WIDGETS), inits)

    def test_the_headers_are_the_hosts_words(self):
        for labels, first, node in (
            (MAYA_LABELS, "Shader", "File Node"),
            (BLENDER_LABELS, "Material", "Texture"),
        ):
            with self.subTest(host=first):
                slots, _sb = _panel(labels=labels)
                self.assertEqual(
                    slots._headers(),
                    (
                        first,
                        "Texture Path",
                        node,
                        "File Size",
                        "Dimensions",
                        "Image Type",
                    ),
                )


class TestHeaderMenu(_PanelCase):
    def _built(self, **engine_kwargs):
        slots, sb = _panel(**engine_kwargs)
        header = mock.MagicMock()
        added = {}

        def _add(kind, **kwargs):
            widget = mock.MagicMock()
            added[kwargs.get("setObjectName") or kind] = (widget, kwargs)
            return widget

        header.menu.add.side_effect = _add
        slots.header_init(header)
        return slots, header, added

    def test_every_saved_name_is_built(self):
        _slots, header, added = self._built()
        for name in (
            "btn_open_source_images",
            "btn_reload_scene_textures",
            "chk_truncate_paths",
            "chk_warn_path_length",
            "chk_exclude_arnold",
            "chk_show_lightmaps",
            "chk_sync_names",
            "tb_set_texture_directory",
            "tb_find_and_copy_textures",
            "tb_normalize_paths",
            "btn_make_paths_absolute",
            "tb_resolve_missing_textures",
            "btn_select_textures_for_objects",
            "btn_select_broken_paths",
            "btn_select_absolute_paths",
        ):
            self.assertIn(name, added)
        header.set_help_text.assert_called_once()

    def test_exclude_arnold_is_offered_only_where_there_is_arnold(self):
        _slots, _header_, added = self._built(exclude_arnold=False)
        self.assertNotIn("chk_exclude_arnold", added)

    def test_the_open_folder_item_names_the_hosts_folder(self):
        for labels, text in (
            (MAYA_LABELS, "Open Source Images"),
            (BLENDER_LABELS, "Open Textures Folder"),
        ):
            with self.subTest(text=text):
                _slots, _h, added = self._built(labels=labels)
                self.assertEqual(added["btn_open_source_images"][1]["setText"], text)

    def test_keep_names_in_sync_and_truncate_have_their_option_boxes(self):
        _slots, _h, added = self._built()
        sync = added["chk_sync_names"][0]
        names = [
            call.kwargs.get("setObjectName")
            for call in sync.option_box.menu.add.call_args_list
        ]
        self.assertEqual(names, ["txt_shader_affix", "txt_file_node_suffix"])
        spin = added["chk_truncate_paths"][0].option_box.menu.add.call_args.kwargs
        self.assertEqual(
            (spin["setValue"], spin["setMinimum"], spin["setMaximum"]), (96, 24, 400)
        )

    def test_set_directory_offers_its_mode_and_allow_missing_targets(self):
        slots, _sb = _panel()
        button = mock.MagicMock()
        slots.tb_set_texture_directory_init(button)
        calls = {
            c.kwargs["setObjectName"]: c.kwargs
            for c in button.option_box.menu.add.call_args_list
        }
        self.assertEqual(
            calls["cmb_relocate_mode"]["addItems"],
            [label for label, _ in TexturePathEditorSlots._RELOCATE_MODE_ITEMS],
        )
        self.assertFalse(calls["chk_allow_missing"]["setChecked"], "off by default")

    def test_resolve_missing_offers_the_three_strategies_on(self):
        slots, _sb = _panel()
        button = mock.MagicMock()
        slots.tb_resolve_missing_textures_init(button)
        calls = [c.kwargs for c in button.option_box.menu.add.call_args_list]
        self.assertEqual(
            [c["setObjectName"] for c in calls],
            ["chk_stem", "chk_texture", "chk_fuzzy"],
        )
        self.assertTrue(all(c["setChecked"] for c in calls))

    def test_the_affix_hint_follows_the_mode(self):
        slots, _sb = _panel()
        field = mock.MagicMock()
        field.option_box.affix_mode = "convention"
        slots._apply_shader_affix_hint(field)
        field.setPlaceholderText.assert_called_with("Scene Convention")
        field.option_box.affix_mode = "prefix"
        slots._apply_shader_affix_hint(field)
        field.setPlaceholderText.assert_called_with("Shader Prefix")


class TestMenuStateReaders(_PanelCase):
    """Every toggle reads safely before ``header_init`` built the menu."""

    def test_exclude_arnold(self):
        slots, _sb = _panel()
        _header(slots, chk_exclude_arnold=_check(False))
        self.assertFalse(slots._exclude_arnold())
        _header(slots, chk_exclude_arnold=_check(True))
        self.assertTrue(slots._exclude_arnold())
        _header(slots)
        self.assertFalse(slots._exclude_arnold(), "unbuilt: off")

    def test_exclude_arnold_is_off_where_the_engine_has_none(self):
        slots, _sb = _panel(exclude_arnold=False)
        _header(slots, chk_exclude_arnold=_check(True))
        self.assertFalse(slots._exclude_arnold())

    def test_normalize_mode_by_index(self):
        read = TexturePathEditorSlots._read_combo_mode
        items = TexturePathEditorSlots._NORMALIZE_MODE_ITEMS
        for index, expected in (
            (0, "rewrite"),
            (1, "copy"),
            (2, "move"),
            (7, "rewrite"),
        ):
            with self.subTest(index=index):
                button = _button(cmb_external_mode=_combo(index))
                self.assertEqual(read(button, "cmb_external_mode", items), expected)
        self.assertEqual(read(None, "cmb_external_mode", items), "rewrite")

    def test_relocate_mode_by_index(self):
        read = TexturePathEditorSlots._read_combo_mode
        items = TexturePathEditorSlots._RELOCATE_MODE_ITEMS
        for index, expected in (
            (0, "rewrite"),
            (1, "copy"),
            (2, "move"),
            (-1, "rewrite"),
        ):
            with self.subTest(index=index):
                button = _button(cmb_relocate_mode=_combo(index))
                self.assertEqual(read(button, "cmb_relocate_mode", items), expected)

    def test_resolve_modes_keep_the_safest_first_order(self):
        slots, _sb = _panel()
        for flags, expected in (
            ((True, True, True), ["stem", "texture", "fuzzy"]),
            ((False, True, True), ["texture", "fuzzy"]),
            ((True, False, True), ["stem", "fuzzy"]),
            ((False, False, False), []),
        ):
            with self.subTest(flags=flags):
                button = _button(
                    chk_stem=_check(flags[0]),
                    chk_texture=_check(flags[1]),
                    chk_fuzzy=_check(flags[2]),
                )
                self.assertEqual(slots._read_resolve_modes(button), expected)
        self.assertEqual(slots._read_resolve_modes(None), ["stem", "texture", "fuzzy"])

    def test_option_flag_reader(self):
        read = TexturePathEditorSlots._read_option_flag
        button = _button(
            chk_allow_missing=_check(True), chk_truncate_paths=_check(False)
        )
        self.assertTrue(read(button, "chk_allow_missing", False))
        self.assertFalse(read(button, "chk_truncate_paths", True))
        self.assertFalse(read(_button(), "chk_allow_missing", False))
        self.assertTrue(read(None, "chk_warn_path_length", True))

    def test_over_long_paths_warn_by_default(self):
        slots, _sb = _panel()
        _header(slots)
        self.assertTrue(slots._warn_path_length_enabled())
        _header(slots, chk_warn_path_length=_check(False))
        self.assertFalse(slots._warn_path_length_enabled())

    def test_keep_names_in_sync_readers(self):
        slots, _sb = _panel()
        _header(slots)
        self.assertFalse(slots._sync_names_enabled())
        self.assertIsNone(slots._sync())
        self.assertEqual(
            slots._sync_affixes(),
            (ptk.NamingConvention.affix_parts("material"), ("", "")),
        )
        flyout = SimpleNamespace(
            txt_shader_affix=SimpleNamespace(
                option_box=SimpleNamespace(resolve_affix=lambda default: ("M_", ""))
            ),
            txt_file_node_suffix=SimpleNamespace(text=lambda: "file"),
        )
        _header(
            slots,
            chk_sync_names=SimpleNamespace(
                isChecked=lambda: True, option_box=SimpleNamespace(menu=flyout)
            ),
        )
        self.assertTrue(slots._sync_names_enabled())
        self.assertEqual(slots._sync(), (("M_", ""), ("", "_file")))


class TestPathTruncation(_PanelCase):
    def _slot(self, checked, length=None):
        slots, _sb = _panel()
        chk = _check(checked)
        if chk is not None and length is not None:
            chk.option_box = SimpleNamespace(
                menu=SimpleNamespace(
                    spn_truncate_length=SimpleNamespace(value=lambda: length)
                )
            )
        _header(slots, chk_truncate_paths=chk)
        return slots

    def test_enabled_truncates_the_path_column(self):
        slots = self._slot(True)
        slots._apply_path_truncation()
        slots.ui.tbl000.set_column_truncation.assert_called_once_with(
            1, length=96, mode="path", insert="…", head=1
        )

    def test_the_option_box_sets_the_length(self):
        slots = self._slot(True, length=140)
        slots._apply_path_truncation()
        self.assertEqual(
            slots.ui.tbl000.set_column_truncation.call_args.kwargs["length"], 140
        )

    def test_disabled_or_unbuilt_clears_it(self):
        for checked in (False, None):
            with self.subTest(checked=checked):
                slots = self._slot(checked)
                slots._apply_path_truncation()
                self.assertIsNone(
                    slots.ui.tbl000.set_column_truncation.call_args.kwargs["length"]
                )

    def test_no_table_yet_is_a_no_op(self):
        slots = self._slot(True)
        slots.ui = SimpleNamespace(header=slots.ui.header)
        slots._apply_path_truncation()  # no AttributeError


class TestFooter(_PanelCase):
    def _text(self, path):
        slots, sb = _panel()
        sb.tk.TexturePathEditor.return_value.texture_dir.return_value = path
        return slots._footer_status_text()

    def test_the_label_is_the_folder_name(self):
        self.assertEqual(
            self._text("C:/proj/sourceimages"), "SOURCEIMAGES: C:/proj/sourceimages"
        )
        self.assertEqual(self._text("C:/proj/textures"), "TEXTURES: C:/proj/textures")

    def test_no_project_is_an_empty_footer_and_a_root_the_path(self):
        self.assertEqual(self._text(""), "")
        self.assertEqual(self._text("C:/"), "C:/")


class TestScope(_PanelCase):
    LIGHTMAP = {
        "map": "x.exr",
        "dir": "C:/lm",
        "objects": ["cube"],
        "path": None,
        "found_by": None,
        "note": "",
    }

    def test_no_selection_is_every_texture_the_table_shows(self):
        slots, sb = _panel()
        _header(slots, chk_exclude_arnold=_check(True))
        nodes, label = slots._get_scope_nodes()
        self.assertEqual(nodes, ["file1", "file2"])
        self.assertIn("all 2", label)
        sb.tk.TexturePathEditor.return_value.file_nodes.assert_called_with(
            exclude_arnold=True
        )

    def test_selected_rows_are_the_scope(self):
        slots, _sb = _panel(selection=[_row("file9", "lam"), _row("file9", "lam2")])
        nodes, label = slots._get_scope_nodes()
        self.assertEqual(nodes, ["file9"])
        self.assertIn("1 selected", label)

    def test_a_stale_selection_is_never_escalated_to_everything(self):
        slots, sb = _panel(selection=[_row("gone")])
        sb.tk.TexturePathEditor.return_value.node_exists.return_value = False
        nodes, _label = slots._get_scope_nodes()
        self.assertEqual(nodes, [])

    def test_a_selected_lightmap_row_is_a_scope_of_its_own(self):
        path = TexturePathEditorSlots._lightmap_row_path(self.LIGHTMAP)
        self.assertEqual(path, "C:/lm/x.exr")
        slots, _sb = _panel(selection=[_row(path=path, shader="<lightmap>")])
        slots._lightmap_rows = {path: self.LIGHTMAP}
        self.assertEqual(slots._get_scope_lightmaps(), [self.LIGHTMAP])
        nodes, label = slots._get_scope_nodes()
        self.assertEqual(nodes, [])
        self.assertIn("lightmap", label)
        self.assertEqual(slots._get_selected_contexts(), [], "node commands see none")

    def test_no_selection_scopes_to_every_lightmap_row_shown(self):
        slots, _sb = _panel()
        slots._lightmap_rows = {"y.exr": self.LIGHTMAP}
        self.assertEqual(slots._get_scope_lightmaps(), [self.LIGHTMAP])

    def test_a_row_of_several_materials_stands_for_all_of_them(self):
        """Blender's row of two materials carries none in its cell (it renames
        none); a scene selection follows both."""
        slots, _sb = _panel(selection=[_row("shared.png", shader="")])
        slots._node_materials = {"shared.png": ["A", "B"]}
        (context,) = slots._get_selected_contexts()
        self.assertEqual(context["materials"], ["A", "B"])
        self.assertIsNone(context["shader_node"])


class TestTable(_PanelCase):
    ROWS = [
        {
            "shader": "rock_MAT",
            "shader_node": "rock_MAT",
            "materials": ["rock_MAT"],
            "shader_editable": True,
            "path": "C:/tex/rock_Normal.png",
            "file_node": "rock_Normal.png",
            "exists": True,
            "abspath": "C:/tex/rock_Normal.png",
        },
        {
            "shader": "A, B",
            "shader_node": "",
            "materials": ["A", "B"],
            "shader_editable": False,
            "path": "C:/tex/shared.png",
            "file_node": "shared.png",
            "exists": False,
            "abspath": "C:/tex/shared.png",
        },
    ]

    def _refreshed(self, rows=None, lightmaps=()):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.rows.return_value = list(self.ROWS if rows is None else rows)
        engine.lightmap_dependencies.return_value = list(lightmaps)
        _header(slots, chk_exclude_arnold=_check(False))
        widget = _table()
        slots._refresh_table_content(widget)
        return slots, widget, engine

    def test_rows_carry_their_names_in_user_role(self):
        _slots, widget, engine = self._refreshed()
        engine.rows.assert_called_once_with(exclude_arnold=False)
        rows = widget.add.call_args.args[0]
        self.assertEqual(
            rows[0][:3],
            [
                ("rock_MAT", "rock_MAT"),
                "C:/tex/rock_Normal.png",
                ("rock_Normal.png", "rock_Normal.png"),
            ],
        )
        self.assertEqual(rows[1][0], ("A, B", ""))
        self.assertEqual(widget.add.call_args.kwargs["headers"][0], "Shader")

    def test_a_lightmap_row_keeps_its_path_and_no_node(self):
        dep = {"map": "room_LightMap.exr", "dir": "C:/lm", "objects": [], "path": None}
        slots, widget, _engine = self._refreshed(rows=[], lightmaps=[dep])
        rows = widget.add.call_args.args[0]
        self.assertEqual(
            rows[0][:3],
            [
                ("<lightmap>", ""),
                ("C:/lm/room_LightMap.exr",) * 2,
                ("room_LightMap", ""),
            ],
        )
        self.assertEqual(slots._lightmap_rows, {"C:/lm/room_LightMap.exr": dep})

    def test_an_empty_scene_says_so(self):
        _slots, widget, _engine = self._refreshed(rows=[])
        rows = widget.add.call_args.args[0]
        self.assertEqual(rows[0][2], ("No textures found", ""))

    def test_the_toggle_hides_the_lightmap_rows(self):
        slots, sb = _panel()
        _header(slots, chk_show_lightmaps=_check(False))
        self.assertEqual(slots._lightmap_dependencies(), [])
        sb.tk.TexturePathEditor.return_value.lightmap_dependencies.assert_not_called()

    def test_the_shader_cell_is_editable_only_where_the_engine_allows(self):
        """Blender: a row of one local material renames it; a row of two none."""
        slots, _widget, _engine = self._refreshed()
        self.assertEqual(slots._editable_shaders, {"rock_MAT"})
        Qt = slots.sb.QtCore.Qt
        Qt.UserRole, Qt.ItemIsEditable = 256, 2
        cells = {0: mock.MagicMock(), 1: mock.MagicMock()}
        cells[0].data.return_value = "rock_MAT"
        cells[1].data.return_value = ""
        cells[0].flags.return_value = cells[1].flags.return_value = 3
        widget = mock.MagicMock()
        widget.rowCount.return_value = 2
        widget.item.side_effect = lambda row, col: cells[row]
        slots._lock_shader_cells(widget)
        cells[0].setFlags.assert_not_called()
        cells[1].setFlags.assert_called_once_with(1)

    def test_the_optional_columns_start_hidden(self):
        slots, _sb = _panel()
        widget = _table()
        widget.is_initialized = False
        slots.tbl000_init(widget)
        self.assertEqual(
            widget.enable_column_config.call_args.kwargs["hidden_by_default"],
            (2, 3, 4, 5),
        )
        names = [c.kwargs.get("setObjectName") for c in widget.menu.add.call_args_list]
        for name in (
            "row_browse_for_file",
            "row_rename_file",
            "select_material",
            "select_file_node",
            "row_show_in_hypershade",
            "delete_file_node",
        ):
            self.assertIn(name, names)

    def test_only_the_fact_columns_that_show_are_read(self):
        slots, _sb = _panel()
        filled = {}
        hidden = {2, 4, 5}
        cells = {
            1: SimpleNamespace(text=lambda: "rock.png", data=lambda role: None),
            2: SimpleNamespace(text=lambda: "rock", data=lambda role: "rock"),
        }
        widget = SimpleNamespace(
            horizontalHeader=lambda: SimpleNamespace(
                isSectionHidden=lambda c: c in hidden
            ),
            columnCount=lambda: 6,
            rowCount=lambda: 1,
            item=lambda _row, column: cells.get(column),
            isSortingEnabled=lambda: False,
            setSortingEnabled=lambda _on: None,
            blockSignals=lambda _on: False,
            set_sorted_cell=lambda row, column, text, key: (
                filled.__setitem__(column, text)
                or SimpleNamespace(setToolTip=lambda _tip: None)
            ),
        )
        with mock.patch.object(
            ptk.ImgUtils, "texture_facts", return_value={"bytes": 2048, "tiles": 1}
        ) as facts:
            slots._fill_info_columns(widget)
        self.assertEqual(sorted(filled), [3])
        facts.assert_called_once_with("C:/abs/rock.png", ("bytes",))

    def test_the_fact_texts(self):
        fmt = TexturePathEditorSlots._format_fact
        self.assertEqual(fmt("mode", {})[0], "")
        text, tip, key = fmt("dimensions", {"dimensions": (4, 2), "tiles": 3})
        self.assertEqual((text, key), ("4 x 2", 8))
        self.assertIn("first of 3 tiles", tip)
        self.assertEqual(fmt("bytes", {"bytes": 10, "tiles": 1})[2], 10)


class TestRowMenu(_PanelCase):
    def _buttons(self):
        buttons = {}
        for name in ("delete_file_node", "row_browse_for_file", "row_rename_file"):
            button = SimpleNamespace(text="", enabled=True)
            button.setText = lambda text, b=button: setattr(b, "text", text)
            button.setEnabled = lambda on, b=button: setattr(b, "enabled", on)
            buttons[name] = button
        return buttons

    def test_the_row_menu_fits_the_selection(self):
        for labels in (MAYA_LABELS, BLENDER_LABELS):
            slots, sb = _panel(labels=labels)
            buttons = self._buttons()
            lightmap = _row(path="x/a.exr")
            texture = _row("b", "m", "y/b.png")
            slots._lightmap_rows = {"x/a.exr": {"map": "a.exr"}}
            for label, rows, browse, rename, delete in (
                (
                    "a texture row",
                    [texture],
                    "Browse for File...",
                    True,
                    labels["delete"],
                ),
                (
                    "a texture and a lightmap row",
                    [texture, lightmap],
                    "Browse for Folder...",
                    False,
                    labels["delete"],
                ),
                (
                    "a lightmap row",
                    [lightmap],
                    "Browse for File...",
                    True,
                    "Revert to Source...",
                ),
            ):
                with self.subTest(host=labels["shader"], rows=label):
                    widget = SimpleNamespace(
                        get_selection=lambda columns=None, include_current=True, r=rows: (
                            r
                        ),
                        menu=SimpleNamespace(
                            findChild=lambda _t, name: buttons.get(name)
                        ),
                    )
                    slots._fit_row_menu(widget)
                    self.assertEqual(buttons["row_browse_for_file"].text, browse)
                    self.assertIs(buttons["row_rename_file"].enabled, rename)
                    self.assertEqual(buttons["delete_file_node"].text, delete)

    def test_rename_file_opens_the_path_cell_on_the_file_name(self):
        slots, sb = _panel()
        sb.tk.TexturePathEditor.return_value.stored_path.side_effect = lambda node: (
            "//textures/rock_Normal.png"
        )
        slots.row_rename_file([_row("rock_Normal.png", "rock_MAT", row=3)])
        args = slots.ui.tbl000.edit_cell_as.call_args.args
        self.assertEqual(args[:3], (3, 1, "rock_Normal.png"))

    def test_rename_file_wants_one_row(self):
        slots, sb = _panel()
        slots.row_rename_file([_row("a"), _row("b")])
        slots.ui.tbl000.edit_cell_as.assert_not_called()
        self.assertIn("single row", sb.message_box.call_args.args[0])

    def test_a_rename_passes_keep_names_in_sync(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        _header(slots)
        self.assertTrue(slots._rename_texture({"file_node": "n"}, "x.png"))
        engine.rename_texture.assert_called_with({"file_node": "n"}, "x.png", sync=None)
        engine.rename_texture.side_effect = FileExistsError("taken.png exists")
        self.assertFalse(slots._rename_texture({"file_node": "n"}, "taken.png"))
        self.assertIn("taken.png", sb.message_box.call_args.args[0])

    def test_browse_on_several_rows_repoints_each_in_one_folder(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.set_texture_directory.return_value = 1
        sb.dir_dialog.return_value = "C:/moved"
        slots._do_browse_for_file([_row("rock_Normal"), _row("rock_Base_Color")])
        engine.set_texture_directory.assert_called_once_with(
            ["rock_Normal", "rock_Base_Color"], "C:/moved"
        )
        self.assertIn("1</hl> of 2", sb.message_box.call_args.args[0])

    def test_browse_on_one_row_stores_the_pick_relative(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        sb.file_dialog.return_value = "C:/new/wood.png"
        slots._do_browse_for_file([_row("wood")])
        engine.set_texture_path.assert_called_once_with(
            "wood", "C:/new/wood.png", relative=True
        )

    def test_delete_confirms_with_what_it_unwires(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.delete_consequences.return_value = [
            "Connected to 1 material(s): lam_wired.",
            "Those connections will be broken.",
        ]
        sb.message_box.return_value = "No"
        slots.delete_file_node([_row("tex_wired")])
        question = sb.message_box.call_args_list[0].args[0]
        self.assertIn("tex_wired", question)
        self.assertIn("lam_wired", question)
        engine.delete_file_nodes.assert_not_called()
        sb.message_box.return_value = "Yes"
        slots.delete_file_node([_row("tex_wired")])
        engine.delete_file_nodes.assert_called_once_with(["tex_wired"])

    def test_delete_on_a_lightmap_row_reverts_its_objects(self):
        dep = {"map": "lm_cube_Lightmap.exr", "objects": ["lm_cube"], "path": None}
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.lightmap_revert_scope.return_value = (["lm_cube"], [])
        engine.revert_lightmaps.return_value = ["lm_cube"]
        slots._lightmap_rows = {"x/lm_cube_Lightmap.exr": dep}
        sb.message_box.return_value = "Yes"
        slots.delete_file_node([{"path": "x/lm_cube_Lightmap.exr"}])
        engine.revert_lightmaps.assert_called_once_with(["lm_cube"])
        self.assertIn("lm_cube_Lightmap.exr", sb.message_box.call_args_list[0].args[0])
        engine.delete_file_nodes.assert_not_called()

    def test_a_linked_librarys_lightmap_is_never_reverted(self):
        dep = {"map": "crate_Lightmap.exr", "objects": ["crate_GEO"], "path": "x"}
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.lightmap_revert_scope.return_value = ([], ["crate_GEO"])
        self.assertEqual(slots._remove_lightmaps([dep]), 0)
        engine.revert_lightmaps.assert_not_called()
        self.assertIn("linked", sb.message_box.call_args.args[0])


class TestCellEdits(_PanelCase):
    class _Cell:
        def __init__(self, text, role=None):
            self.value, self.role = text, role

        def text(self):
            return self.value

        def setText(self, value):
            self.value = value

        def data(self, _role):
            return self.role

        def setData(self, _role, value):
            self.role = value

    def _edit(self, col, text, sync=False, shader="rock_MAT", node="rock_Normal"):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.rename_file_node.return_value = text
        engine.rename_shader.return_value = text
        if sync:
            flyout = SimpleNamespace(
                txt_shader_affix=SimpleNamespace(
                    option_box=SimpleNamespace(
                        resolve_affix=lambda default: ("", "_MAT")
                    )
                ),
                txt_file_node_suffix=SimpleNamespace(text=lambda: "_file"),
            )
            _header(
                slots,
                chk_sync_names=SimpleNamespace(
                    isChecked=lambda: True, option_box=SimpleNamespace(menu=flyout)
                ),
            )
        else:
            _header(slots)
        cells = {
            0: self._Cell(shader, shader),
            1: self._Cell("C:/tex/rock_Normal.png"),
            2: self._Cell(node, node),
        }
        cells[col].setText(text)
        slots.ui.tbl000 = SimpleNamespace(
            item=lambda _row, column: cells.get(column),
            blockSignals=lambda _on: False,
            apply_formatting=lambda: None,
        )
        slots._footer_controller = None
        slots.handle_cell_edit(0, col)
        return engine, cells, sb

    def test_a_typed_path_goes_to_the_engine_with_its_row(self):
        engine, _cells, _sb = self._edit(1, "C:/tex/stone_Normal.png")
        engine.apply_path_edit.assert_called_once_with(
            "rock_Normal", "C:/tex/stone_Normal.png", shader="rock_MAT", sync=None
        )

    def test_a_node_cell_renames_the_node(self):
        engine, cells, _sb = self._edit(2, "stone_file")
        engine.rename_file_node.assert_called_once_with("rock_Normal", "stone_file")
        self.assertEqual(cells[2].role, "stone_file")

    def test_with_sync_a_node_cell_hands_the_affixes_over_and_snaps_back(self):
        engine, cells, _sb = self._edit(2, "stone_Normal", sync=True)
        engine.rename_file_node.assert_called_once_with(
            "rock_Normal",
            "stone_Normal",
            shader="rock_MAT",
            sync=(("", "_MAT"), ("", "_file")),
        )
        self.assertEqual(
            cells[2].text(), "rock_Normal", "the refresh shows what landed"
        )

    def test_a_shader_cell_renames_the_shader(self):
        engine, _cells, _sb = self._edit(0, "boulder_MAT")
        engine.rename_shader.assert_called_once_with(
            "rock_MAT", "boulder_MAT", sync=None
        )

    def test_a_refused_rename_puts_the_cell_back_and_says_why(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.rename_file_node.side_effect = RuntimeError("locked")
        _header(slots)
        cells = {0: self._Cell("", ""), 1: self._Cell("p"), 2: self._Cell("x2", "x")}
        slots.ui.tbl000 = SimpleNamespace(
            item=lambda _row, column: cells.get(column), blockSignals=lambda _on: False
        )
        slots.handle_cell_edit(0, 2)
        self.assertEqual(cells[2].text(), "x")
        self.assertIn("locked", sb.message_box.call_args.args[0])

    def test_a_fact_cell_is_no_edit(self):
        slots, sb = _panel()
        slots.handle_cell_edit(0, 4)
        sb.tk.TexturePathEditor.return_value.apply_path_edit.assert_not_called()


class TestCommands(_PanelCase):
    def test_set_directory_hands_the_option_box_over(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.set_texture_directory.return_value = 2
        sb.dir_dialog.return_value = "C:/dest"
        button = _button(cmb_relocate_mode=_combo(1), chk_allow_missing=_check(True))
        slots.tb_set_texture_directory(button)
        engine.set_texture_directory.assert_called_once_with(
            ["file1", "file2"], "C:/dest", relocate_mode="copy", allow_missing=True
        )
        self.assertIn("DESTINATION", sb.dir_dialog.call_args.kwargs["title"])

    def test_set_directory_says_how_to_bring_the_rest_along(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.set_texture_directory.return_value = 0
        sb.dir_dialog.return_value = "C:/empty"
        slots.tb_set_texture_directory(_button(cmb_relocate_mode=_combo(0)))
        self.assertIn("Allow Missing Targets", sb.message_box.call_args.args[0])

    def test_a_cancelled_picker_does_nothing(self):
        slots, sb = _panel()
        sb.dir_dialog.return_value = ""
        slots.tb_set_texture_directory(None)
        sb.tk.TexturePathEditor.return_value.set_texture_directory.assert_not_called()

    def test_normalize_reads_the_external_mode(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.normalize_paths.return_value = 1
        engine.normalize_lightmaps.return_value = 0
        slots.tb_normalize_paths(_button(cmb_external_mode=_combo(2)))
        engine.normalize_paths.assert_called_once_with(
            ["file1", "file2"], external_mode="move"
        )
        engine.normalize_lightmaps.assert_called_once_with([], relative=True)

    def test_make_absolute_says_why_it_cannot(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.make_paths_absolute.side_effect = ValueError("Save the .blend first")
        slots.make_paths_absolute()
        self.assertIn("Save the .blend first", sb.message_box.call_args.args[0])
        engine.normalize_lightmaps.assert_not_called()

    def test_resolve_missing_hands_the_strategies_over(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.resolve_missing_textures.return_value = 3
        button = _button(
            chk_stem=_check(True), chk_texture=_check(False), chk_fuzzy=_check(True)
        )
        slots.tb_resolve_missing_textures(button)
        engine.resolve_missing_textures.assert_called_once_with(
            ["stem", "fuzzy"], file_nodes=["file1", "file2"]
        )
        self.assertIn("3</hl>", sb.message_box.call_args.args[0])

    def test_resolve_missing_with_no_strategy_runs_nothing(self):
        slots, sb = _panel()
        button = _button(
            chk_stem=_check(False), chk_texture=_check(False), chk_fuzzy=_check(False)
        )
        slots.tb_resolve_missing_textures(button)
        sb.tk.TexturePathEditor.return_value.resolve_missing_textures.assert_not_called()

    def test_select_textures_for_objects(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        engine.selected_file_nodes.return_value = None
        slots.select_textures_for_objects()
        self.assertIn("Select object(s) first", sb.message_box.call_args.args[0])
        engine.selected_file_nodes.return_value = ["ns:file1"]
        slots._select_rows_by_predicate = mock.MagicMock()
        slots.select_textures_for_objects()
        predicate = slots._select_rows_by_predicate.call_args.args[0]
        self.assertTrue(predicate("p", "|grp|ns:file1"))
        self.assertFalse(predicate("p", "file2"))

    def test_select_broken_and_absolute_paths(self):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        slots._path_state = {"gone.png": (False, "C:/gone.png"), "ok.png": (True, "")}
        slots._lightmap_rows = {"lm.exr": {"path": None}, "lm2.exr": {"path": "x"}}
        slots._select_rows_by_predicate = mock.MagicMock()
        slots.select_broken_paths()
        broken = slots._select_rows_by_predicate.call_args.args[0]
        self.assertEqual(
            [broken(p, None) for p in ("gone.png", "ok.png", "lm.exr", "lm2.exr")],
            [True, False, True, False],
        )
        engine.is_absolute_path.side_effect = lambda path: path.startswith("C:")
        slots.select_absolute_paths()
        absolute = slots._select_rows_by_predicate.call_args.args[0]
        self.assertTrue(absolute("C:/a.png", None))
        self.assertFalse(absolute("//a.png", None))

    def test_open_folder_without_a_project_says_so(self):
        slots, sb = _panel(texture_dir="")
        with mock.patch.object(ptk.FileUtils, "open_explorer") as opened:
            slots.open_source_images()
        opened.assert_not_called()
        self.assertIn("save the scene first", sb.message_box.call_args.args[0])


class TestSceneChanges(_PanelCase):
    def test_the_engines_events_are_subscribed(self):
        slots, sb = _panel()
        widget = mock.MagicMock()
        slots._setup_scene_change_callback(widget)
        manager = sb.tk.ScriptJobManager.instance.return_value
        events = [c.args[0] for c in manager.subscribe.call_args_list]
        self.assertEqual(events, [e for e, _v in SCENE_EVENTS])
        self.assertTrue(
            all(c.kwargs["owner"] is slots for c in manager.subscribe.call_args_list)
        )
        manager.connect_cleanup.assert_called_once_with(widget, owner=slots)

    def _queued(self):
        slots, sb = _panel()
        queued, refreshed = [], []
        sb.QtCore.QTimer.singleShot.side_effect = lambda _ms, fn: queued.append(fn)
        slots._refresh_table_content = refreshed.append
        return slots, queued, refreshed

    def test_an_undo_refreshes_a_shown_table_only(self):
        slots, queued, refreshed = self._queued()
        hidden = SimpleNamespace(isVisible=lambda: False)
        shown = SimpleNamespace(isVisible=lambda: True)
        for widget, visible_only in ((hidden, True), (shown, True), (hidden, False)):
            slots._on_scene_change(widget, visible_only=visible_only)
            while queued:
                queued.pop(0)()
        self.assertEqual(refreshed, [shown, hidden])

    def test_a_waiting_undo_does_not_swallow_a_scene_event(self):
        slots, queued, refreshed = self._queued()
        hidden = SimpleNamespace(isVisible=lambda: False)
        slots._on_scene_change(hidden, visible_only=True)
        slots._on_scene_change(hidden)
        self.assertEqual(len(queued), 1, "one refresh per idle")
        queued.pop()()
        self.assertEqual(refreshed, [hidden])

    def test_a_scene_change_forgets_the_previous_paths(self):
        slots, queued, _refreshed = self._queued()
        slots.engine.previous_paths["n"] = "old.png"
        slots._on_scene_change(SimpleNamespace(isVisible=lambda: True))
        queued.pop()()
        self.assertEqual(slots.engine.previous_paths, {})


class TestFindAndCopyForm(_PanelCase):
    def _open(
        self,
        nodes=("tex_a",),
        unresolved=(),
        lightmaps=(),
        texture_dir="C:/proj/sourceimages",
    ):
        slots, sb = _panel(texture_dir=texture_dir)
        engine = sb.tk.TexturePathEditor.return_value
        engine.unresolved_file_nodes.return_value = list(unresolved)
        slots._find_and_copy_workflow(list(nodes), lightmaps=list(lightmaps))
        return slots, sb, engine

    def _fields(self, sb, index=0):
        return {f["name"]: f for f in sb.form_panel.call_args_list[index].args[0]}

    def test_one_form_carries_both_folders_in_reading_order(self):
        _slots, sb, _engine = self._open()
        fields = sb.form_panel.call_args.args[0]
        self.assertEqual(
            [f["name"] for f in fields], ["mode", "source_dir", "dest_dir"]
        )
        self.assertEqual([f["name"] for f in fields[0]["inline"]], ["dry_run"])
        named = self._fields(sb)
        self.assertIn("Search in", named["source_dir"]["label"])
        self.assertIn(
            TexturePathEditorSlots._DIALOG_MARK_SOURCE, named["source_dir"]["label"]
        )
        self.assertIn("Copy into", named["dest_dir"]["label"])
        self.assertIn(
            TexturePathEditorSlots._DIALOG_MARK_DEST, named["dest_dir"]["label"]
        )
        self.assertIn("land HERE", named["dest_dir"]["hint"])

    def test_the_destination_prefills_to_the_texture_folder(self):
        _slots, sb, _engine = self._open()
        self.assertEqual(self._fields(sb)["dest_dir"]["value"], "C:/proj/sourceimages")
        _slots, sb, _engine = self._open(texture_dir="")
        self.assertEqual(self._fields(sb)["dest_dir"]["value"], "")

    def test_the_source_row_is_disabled_with_its_reason_when_all_resolve(self):
        _slots, sb, _engine = self._open()
        source = self._fields(sb)["source_dir"]
        self.assertFalse(source["enabled"])
        self.assertIn("nothing needs finding", source["hint"])
        self.assertEqual(source["placeholder"], "No path requires a search dir")

    def test_the_source_row_names_what_is_missing(self):
        _slots, sb, _engine = self._open(
            nodes=("tex_g", "tex_x"), unresolved=("tex_x",)
        )
        source = self._fields(sb)["source_dir"]
        self.assertTrue(source["enabled"])
        self.assertIn("tex_x.png", source["hint"])
        self.assertIn("1 unresolved", source["hint"])
        self.assertIn("skip them and relocate the 1", source["hint"])
        self.assertEqual(source["placeholder"], "1 path(s) require a search dir")

    def test_missing_lightmaps_switch_the_search_on(self):
        dep = {"map": "hinted_LightMap.exr", "path": None}
        _slots, sb, _engine = self._open(nodes=(), lightmaps=[dep])
        source = self._fields(sb)["source_dir"]
        self.assertTrue(source["enabled"])
        self.assertIn("hinted_LightMap.exr", source["hint"])
        self.assertNotIn("relocate the 0", source["hint"])
        names = [f["name"] for f in sb.form_panel.call_args.args[0]]
        self.assertNotIn("include_lightmaps", names, "the scope decides")

    def test_a_lightmap_only_scope_that_resolves_counts_no_nodes(self):
        _slots, sb, _engine = self._open(
            nodes=(), lightmaps=[{"map": "f.exr", "path": "x"}]
        )
        source = self._fields(sb)["source_dir"]
        self.assertFalse(source["enabled"])
        self.assertIn("Nothing in scope needs finding", source["hint"])

    def test_the_accept_text_names_the_operation_and_the_count(self):
        slots, _sb, _engine = self._open(nodes=("a", "b"))
        ok = slots._find_and_copy_ok_text
        self.assertEqual(ok({"mode": "Move"}), "Move 2 texture(s)")
        self.assertEqual(ok({"mode": "Copy", "dry_run": True}), "Preview 2 texture(s)")
        slots._find_copy_lightmaps = [{"map": "x"}]
        self.assertEqual(ok({"mode": "Copy"}), "Copy 2 texture(s) + 1 lightmap(s)")
        slots._find_copy_nodes = []
        self.assertEqual(ok({"mode": "Copy"}), "Copy 1 lightmap(s)")

    def test_the_form_is_wired(self):
        slots, sb, _engine = self._open()
        kwargs = sb.form_panel.call_args.kwargs
        self.assertIs(kwargs["parent"], slots.ui)
        self.assertIs(
            kwargs["validate"], TexturePathEditorSlots._validate_find_and_copy
        )
        self.assertEqual(
            kwargs["on_run"].__func__, TexturePathEditorSlots._run_find_and_copy
        )
        self.assertTrue(callable(kwargs["ok_text"]))

    def test_reopening_re_seeds_instead_of_rebuilding(self):
        slots, sb, _engine = self._open(nodes=("one",))
        panel = sb.form_panel.return_value
        slots._find_and_copy_workflow(["one", "two"])
        self.assertEqual(sb.form_panel.call_count, 1, "the panel was rebuilt")
        reseeded = {f["name"]: f for f in panel.set_fields.call_args.args[0]}
        self.assertIn("2 texture(s) land HERE", reseeded["dest_dir"]["hint"])
        self.assertEqual(panel.present.call_count, 2)
        self.assertEqual(
            slots._find_and_copy_ok_text({"mode": "Copy"}), "Copy 2 texture(s)"
        )

    def test_the_validator(self):
        validate = TexturePathEditorSlots._validate_find_and_copy
        self.assertIn(
            "nothing would move", validate({"source_dir": "C:/x", "dest_dir": "C:/x"})
        )
        self.assertIn(
            "nothing would move",
            validate({"source_dir": "C:\\X".lower(), "dest_dir": "c:/x/"}),
        )
        self.assertIn(
            "destination", validate({"source_dir": "C:/x", "dest_dir": ""}).lower()
        )
        self.assertEqual(validate({"source_dir": "C:/x", "dest_dir": "C:/y"}), "")
        self.assertEqual(validate({"source_dir": "", "dest_dir": "C:/y"}), "")


class TestFindAndCopyRun(_PanelCase):
    def _run(self, planned, dry_run):
        slots, sb = _panel()
        engine = sb.tk.TexturePathEditor.return_value
        lent = []

        def _find(nodes, values, **kwargs):
            lent.append(engine.active_logger)
            return planned

        engine.find_and_copy_textures.side_effect = _find
        slots._find_and_copy_workflow(["tex_a"], lightmaps=[{"map": "m.exr"}])
        commit = slots._run_find_and_copy(
            {"source_dir": "", "dest_dir": "C:/d", "mode": "Copy", "dry_run": dry_run}
        )
        return slots, sb, engine, commit, lent

    def test_the_engine_reports_into_the_panel_for_the_run(self):
        _slots, sb, engine, _commit, lent = self._run(True, False)
        self.assertEqual(lent, [sb.form_panel.return_value.logger])
        self.assertIsNone(engine.active_logger, "handed back after the run")
        call = engine.find_and_copy_textures.call_args
        self.assertEqual(call.args[0], ["tex_a"])
        self.assertEqual(call.kwargs["lightmaps"], [{"map": "m.exr"}])
        self.assertFalse(call.kwargs["dry_run"])

    def test_a_dry_run_arms_apply_with_the_call_that_commits_it(self):
        slots, _sb, engine, commit, _lent = self._run(True, True)
        self.assertTrue(callable(commit))
        slots._find_copy_lightmaps = []  # the scope moved on behind the window
        self.assertIsNone(commit(), "the plan is spent: nothing re-arms")
        call = engine.find_and_copy_textures.call_args
        self.assertFalse(call.kwargs["dry_run"])
        self.assertEqual(call.kwargs["lightmaps"], [{"map": "m.exr"}], "as previewed")

    def test_a_live_run_or_an_empty_preview_arms_nothing(self):
        self.assertIsNone(self._run(True, False)[3])
        self.assertIsNone(self._run(False, True)[3])


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestTexturePathEditorPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")
        store = ptk.TempArtifacts("tpe_panel", policy="scoped")
        self.addCleanup(store.cleanup, True)
        self.dir = store.dir_path().replace("\\", "/")

    def _texture(self, folder, name):
        path = os.path.join(self.dir, folder, name).replace("\\", "/")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"DATA")
        return path

    def _file_node(self, name, path, shader=None):
        cmds = self.cmds
        node = cmds.shadingNode("file", asTexture=True, name=name)
        self.mtk.Attributes.set_plug_literal(f"{node}.fileTextureName", path)
        if shader:
            mat = cmds.shadingNode("lambert", asShader=True, name=shader)
            cmds.connectAttr(f"{node}.outColor", f"{mat}.color", force=True)
            # The editor reads a texture's shader through its shading group, as a
            # material assigned to anything has one.
            sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                           name=f"{shader}SG")
            cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader", force=True)
        return node

    def test_the_real_engine_is_composed(self):
        slots, _sb = _panel(tk=self.mtk)
        self.assertIsInstance(slots.engine, self.mtk.TexturePathEditor)
        self.assertEqual(slots.labels["file_node"], "File Node")
        self.assertTrue(slots.engine.EXCLUDE_ARNOLD)

    def test_the_table_lists_a_real_file_node(self):
        node = self._file_node(
            "tex_listed", self._texture("a", "wood.png"), "lam_listed"
        )
        slots, _sb = _panel(tk=self.mtk)
        _header(slots)
        widget = _table()
        slots._refresh_table_content(widget)
        rows = widget.add.call_args.args[0]
        listed = [r for r in rows if r[2] == (node, node)]
        self.assertEqual(len(listed), 1, rows)
        self.assertEqual(listed[0][0], ("lam_listed", "lam_listed"))
        self.assertTrue(slots._path_state[listed[0][1]][0], "the file is there")

    def test_set_directory_repaths_through_the_panel(self):
        node = self._file_node("tex_moved", self._texture("a", "wood.png"))
        self._texture("b", "wood.png")
        slots, sb = _panel(tk=self.mtk)
        _header(slots)  # no Exclude Arnold Nodes: the scope is every file node
        sb.dir_dialog.return_value = f"{self.dir}/b"
        slots.tb_set_texture_directory(_button(cmb_relocate_mode=_combo(0)))
        self.assertTrue(
            self.cmds.getAttr(f"{node}.fileTextureName").endswith("b/wood.png"),
            self.cmds.getAttr(f"{node}.fileTextureName"),
        )
        self.assertIn(node, slots.engine.previous_paths)

    def test_the_delete_confirm_names_the_material(self):
        node = self._file_node("tex_wired", self._texture("a", "w.png"), "lam_wired")
        slots, sb = _panel(tk=self.mtk)
        sb.message_box.return_value = "No"
        slots.delete_file_node([_row(node, "lam_wired")])
        self.assertIn("lam_wired", sb.message_box.call_args_list[0].args[0])
        self.assertTrue(self.cmds.objExists(node), "No is no")

    def test_keep_names_in_sync_from_a_node_cell(self):
        """A file node of the set given a new base renames the whole material."""
        cmds = self.cmds
        self.addCleanup(cmds.workspace, cmds.workspace(q=True, rd=True), o=True)
        cmds.workspace(self.dir, openWorkspace=True)
        node = self._file_node(
            "rock_Normal_file", self._texture("", "rock_Normal.png"), "rock_MAT"
        )
        slots, _sb = _panel(tk=self.mtk)
        flyout = SimpleNamespace(
            txt_shader_affix=SimpleNamespace(
                option_box=SimpleNamespace(resolve_affix=lambda default: ("", "_MAT"))
            ),
            txt_file_node_suffix=SimpleNamespace(text=lambda: "_file"),
        )
        _header(
            slots,
            chk_sync_names=SimpleNamespace(
                isChecked=lambda: True, option_box=SimpleNamespace(menu=flyout)
            ),
        )
        cells = {
            0: TestCellEdits._Cell("rock_MAT", "rock_MAT"),
            1: TestCellEdits._Cell(cmds.getAttr(f"{node}.fileTextureName")),
            2: TestCellEdits._Cell("stone_Normal", node),
        }
        slots.ui.tbl000 = SimpleNamespace(
            item=lambda _row, column: cells.get(column), blockSignals=lambda _on: False
        )
        slots.handle_cell_edit(0, 2)
        self.assertTrue(cmds.objExists("stone_MAT"))
        self.assertTrue(cmds.objExists("stone_Normal_file"))
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "stone_Normal.png")))


if __name__ == "__main__":
    unittest.main()
