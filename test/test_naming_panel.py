#!/usr/bin/python
# coding=utf-8
"""The Naming panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. The fake engine
carries a real pythontk logger, so the report the panel writes into its output
pane is read back as text; the file scopes rename real files in a temp
directory. In Maya, the same class drives the real ``mtk``. The engines
themselves are the libraries' (mayatk's and blendertk's ``test_naming.py``), the
Suffix By Type editor uitk's (``test_naming_convention_editor.py``).
"""

import itertools
import os
import shutil
import tempfile
import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.naming import NamingSlots

_ENGINES = itertools.count()

#: The editor methods once copied into each host's panel; uitk owns them now.
_RETIRED_COPIES = (
    "_convention_rows",
    "_wire_convention_field",
    "_save_convention",
    "_add_convention_row",
    "_build_convention_only_rows",
    "_convention_fields",
    "_apply_convention_preset",
    "_wire_convention_presets",
)


def _engine_logger():
    """A real, quiet pythontk logger of its own (one class each, so one panel's
    redirect never reaches another's pane)."""
    engine = type(f"FakeNaming{next(_ENGINES)}", (ptk.LoggingMixin,), {})
    logger = engine.logger
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    return logger


def _report(ui):
    """The output pane's text since it was last cleared: the redirect writes
    into the stand-in pane as a stream."""
    text = []
    for name, args, _kwargs in ui.txt002.mock_calls:
        if name == "clear":
            text = []
        elif name == "write":
            text.append(args[0])
    return "".join(text)


def _set_scope(ui, scope="Selection", dry_run=False, base_names=False):
    menu = ui.header.menu
    menu.cmb_scope.currentText.return_value = scope
    menu.chk_dry_run.isChecked.return_value = dry_run
    menu.chk_base_names.isChecked.return_value = base_names


def _panel(tk=None, scope="Selection", dry_run=False, selection=("|a", "|b")):
    """A Slots instance over a mock ui and a mock toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is). The fake host's selection
    scope reads *selection*."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.Naming.logger = _engine_logger()
        sb.tk.Naming.scope_objects.side_effect = lambda scene=False: (
            ["|s1", "|s2", "|s3"] if scene else list(selection)
        )
        sb.tk.Naming.select_link.side_effect = lambda o: f"link:{o}"
        sb.tk.Naming.UNSUPPORTED_TYPES = {"ikHandle": "No IK handles here."}
        sb.tk.Naming.SUFFIX_BINDINGS = tuple(
            (kw, f"ck_{kw}", f"tk_{kw}") for kw in NamingSlots.SUFFIX_FIELDS
        )
        sb.tk.EnvUtils.workspace_root.return_value = ""
    ui = sb.loaded_ui.naming
    # The stand-in pane takes the redirect as a stream; it is no terminal.
    ui.txt002.isatty.return_value = False
    _set_scope(ui, scope, dry_run)
    for box in ("chk000", "chk001", "chk007"):
        getattr(ui.txt000.option_box.menu, box).isChecked.return_value = False
    for box in ("chk002", "chk008"):
        getattr(ui.txt001.option_box.menu, box).isChecked.return_value = False
    ui.footer.add_action_button.return_value = mock.MagicMock(name="apply")
    return NamingSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestNamingPanelSetup(_PanelCase):
    def test_the_output_pane_carries_the_engines_report(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.naming
        ui.txt002.setText.assert_called_once_with(NamingSlots.msg_intro)
        self.assertIn("Dry Run", NamingSlots.msg_intro)
        self.assertIs(ui.txt002.restore_state, False)
        self.assertIs(slots.logger, sb.tk.Naming.logger)
        slots.logger.result("wired")
        self.assertIn("wired", _report(ui))
        ui.txt002.anchorClicked.connect.assert_called_once_with(
            slots._on_log_link_clicked
        )

    def test_log_links_go_to_the_host(self):
        slots, sb = _panel()
        slots._on_log_link_clicked("action://select?node=a")
        sb.tk.UiUtils.dispatch_log_link.assert_called_once_with(
            "action://select?node=a", slots.logger
        )

    def test_the_footer_apply_button_starts_hidden(self):
        slots, sb = _panel()
        footer = sb.loaded_ui.naming.footer
        footer.add_action_button.assert_called_once_with(
            text="Apply",
            icon_name="check",
            tooltip="Apply the changes the last dry run previewed.",
            callback=slots._apply_dry_run,
        )
        slots._apply_btn.setVisible.assert_called_once_with(False)

    def test_the_header_builds_scope_base_names_and_dry_run(self):
        slots, sb = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        header.config_buttons.assert_called_once_with("menu", "collapse", "pin")
        added = {
            c.kwargs.get("setObjectName"): c for c in header.menu.add.call_args_list
        }
        self.assertEqual(
            added["cmb_scope"].kwargs["addItems"], list(NamingSlots.SCOPES)
        )
        self.assertEqual(
            NamingSlots.SCOPES, ("Selection", "Scene", "Directory", "Files")
        )
        self.assertIn("chk_base_names", added)
        self.assertIn("chk_dry_run", added)
        header.menu.cmb_scope.currentTextChanged.connect.assert_called_once_with(
            slots._on_scope_changed
        )
        header.set_help_text.assert_called_once()

    def test_base_names_is_gated_on_a_file_scope(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.naming
        ui.header.menu.chk_base_names.isChecked.return_value = True
        for scope, enabled in (
            ("Selection", False),
            ("Scene", False),
            ("Directory", True),
            ("Files", True),
        ):
            with self.subTest(scope=scope):
                ui.header.menu.cmb_scope.currentText.return_value = scope
                slots._on_scope_changed()
                ui.header.menu.chk_base_names.setEnabled.assert_called_with(enabled)
                # Ticked but out of scope: the property, not the widget, is the gate.
                self.assertIs(slots.base_names, enabled)


class TestNamingPanelConvention(_PanelCase):
    def test_the_edit_only_rows_are_the_conventions_artifacts(self):
        """A typo in CONVENTION_GROUPS would render an empty row that writes a
        junk entry into the shared convention on first edit; a missing one
        leaves an entry editable only by hand."""
        keys = {ck for _g, rows in NamingSlots.CONVENTION_GROUPS for ck, _n in rows}
        self.assertEqual(keys, set(ptk.NamingConvention.ARTIFACT_KEYS))
        self.assertLessEqual(keys, set(ptk.NamingConvention.DEFAULTS))

    def test_row_object_names_are_unique(self):
        """They are persisted user settings; a collision silently shares state."""
        names = list(NamingSlots.SUFFIX_FIELDS.values()) + [
            n for _g, rows in NamingSlots.CONVENTION_GROUPS for _k, n in rows
        ]
        self.assertEqual(len(NamingSlots.SUFFIX_FIELDS), 19)
        self.assertEqual(len(names), len(set(names)))

    def test_the_rows_map_through_the_hosts_bindings(self):
        slots, sb = _panel()
        groups = slots._convention_groups()
        self.assertEqual(groups[-1], NamingSlots.CONVENTION_GROUPS[0])
        transforms = dict(groups[0][1])
        self.assertEqual(transforms["ck_group_suffix"], "tb003_txt000")

    def test_the_editor_is_uitks_fed_the_hosts_data(self):
        slots, sb = _panel()
        widget = mock.MagicMock()
        slots.tb003_init(widget)
        menu = widget.option_box.menu
        sb.NamingConventionEditor.assert_called_once_with(
            menu,
            slots._convention_groups(),
            tooltip=NamingSlots._convention_tooltip,
            disabled={"ikHandle": "No IK handles here."},
            logger=slots.logger,
        )
        added = [c.kwargs.get("setObjectName") for c in menu.add.call_args_list]
        self.assertEqual(added[1:], ["tb003_chk004", "tb003_chk002", "tb003_chk003"])
        for name in _RETIRED_COPIES:
            self.assertFalse(hasattr(NamingSlots, name), name)

    def test_tooltips_tell_an_artifact_row_from_a_node_row(self):
        artifact = next(iter(ptk.NamingConvention.ARTIFACT_KEYS))
        self.assertIn("Not a", NamingSlots._convention_tooltip(artifact, "Lightmap"))
        self.assertIn("Leave empty", NamingSlots._convention_tooltip("mesh", "Mesh"))

    def test_valid_suffixes_read_the_fields(self):
        slots, sb = _panel()
        menu = sb.loaded_ui.naming.tb003.option_box.menu
        for i, name in enumerate(NamingSlots.SUFFIX_FIELDS.values()):
            getattr(menu, name).text.return_value = "" if i else "_GRP"
        self.assertEqual(slots.valid_suffixes, ["_GRP"])


class TestNamingPanelScene(_PanelCase):
    def _find(self, slots, sb, text, **boxes):
        ui = sb.loaded_ui.naming
        ui.txt000.text.return_value = text
        for box, on in boxes.items():
            getattr(ui.txt000.option_box.menu, box).isChecked.return_value = on
        slots.txt000(ui.txt000)
        return ui

    def test_find_selects_through_the_host_and_reports(self):
        slots, sb = _panel()
        sb.tk.Naming.select_by_name.return_value = (["|pCube1", "|pCube2"], 40)
        ui = self._find(slots, sb, "pCube*", chk000=True, chk001=True)
        sb.tk.Naming.select_by_name.assert_called_once_with(
            "pCube*", regex=True, ignore_case=True, locators_only=False
        )
        out = _report(ui)
        self.assertIn("Find — 2 of 40 objects matching 'pCube*'", out)
        self.assertIn("link:|pCube1", out)
        ui.footer.setText.assert_called_with("Found 2 objects matching 'pCube*'")

    def test_find_locators_only(self):
        slots, sb = _panel()
        sb.tk.Naming.select_by_name.return_value = ([], 3)
        ui = self._find(slots, sb, "loc*", chk007=True)
        self.assertIs(
            sb.tk.Naming.select_by_name.call_args.kwargs["locators_only"], True
        )
        self.assertIn("No locators matching 'loc*' (searched 3).", _report(ui))
        ui.footer.setText.assert_called_with("No locators matching 'loc*'")

    def test_find_with_no_pattern_does_nothing_in_a_scene_scope(self):
        slots, sb = _panel()
        self._find(slots, sb, "")
        sb.tk.Naming.select_by_name.assert_not_called()

    def test_rename_is_one_undo_step_on_the_selection(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.naming
        ui.txt000.text.return_value = "*Cube*"
        ui.txt001.text.return_value = "*Box*"
        slots.txt001(ui.txt001)
        sb.tk.Naming.scope_objects.assert_called_once_with(scene=False)
        sb.tk.Naming.rename.assert_called_once_with(
            ["|a", "|b"],
            "*Box*",
            "*Cube*",
            dry_run=False,
            regex=False,
            ignore_case=False,
            retain_suffix=False,
            valid_suffixes=None,
        )
        sb.tk.CoreUtils.undo_chunk.assert_called_once_with("Rename")
        sb.tk.CoreUtils.undo_chunk.return_value.__enter__.assert_called_once()

    def test_ignore_find_renames_every_object_in_scope(self):
        slots, sb = _panel(scope="Scene")
        ui = sb.loaded_ui.naming
        ui.txt000.text.return_value = "*Cube*"
        ui.txt001.option_box.menu.chk008.isChecked.return_value = True
        slots.txt001(ui.txt001)
        sb.tk.Naming.scope_objects.assert_called_once_with(scene=True)
        args = sb.tk.Naming.rename.call_args.args
        self.assertEqual(args, (["|s1", "|s2", "|s3"], ui.txt001.text.return_value, ""))

    def test_nothing_in_scope_is_said(self):
        for scope, said in (
            ("Selection", "Nothing selected."),
            ("Scene", "The scene has no renameable objects."),
        ):
            with self.subTest(scope=scope):
                slots, sb = _panel(scope=scope, selection=())
                sb.tk.Naming.scope_objects.side_effect = None
                sb.tk.Naming.scope_objects.return_value = []
                ui = sb.loaded_ui.naming
                slots.tb000(ui.tb000)
                self.assertIn(said, _report(ui))
                sb.tk.Naming.set_case.assert_not_called()

    def test_the_scene_operations_read_their_option_boxes(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.naming
        ui.tb000.option_box.menu.cmb001.currentText.return_value = "upper"
        slots.tb000(ui.tb000)
        sb.tk.Naming.set_case.assert_called_once_with(
            ["|a", "|b"], "upper", dry_run=False
        )

        menu = ui.tb002.option_box.menu
        menu.s000.value.return_value = 2
        menu.cmb002.currentText.return_value = "Leading"
        slots.tb002(ui.tb002)
        sb.tk.Naming.strip_chars.assert_called_once_with(
            ["|a", "|b"], dry_run=False, num_chars=2, trailing=False
        )

        menu = ui.tb001.option_box.menu
        menu.cmb_reference.currentText.return_value = "First Object"
        for box, on in (("chk005", True), ("chk002", False), ("chk003", True)):
            getattr(menu, box).isChecked.return_value = on
        for box in ("chk004", "chk007"):
            getattr(menu, box).isChecked.return_value = False
        slots.tb001(ui.tb001)
        args, kwargs = sb.tk.Naming.append_location_based_suffix.call_args
        self.assertEqual(args, (["|a", "|b"],))
        self.assertEqual(
            {k: v for k, v in kwargs.items() if k != "valid_suffixes"},
            {
                "dry_run": False,
                "first_obj_as_ref": True,
                "alphabetical": True,
                "strip_trailing_ints": False,
                "strip_defined_suffixes": True,
                "reverse": False,
                "independent_groups": False,
            },
        )
        self.assertEqual(
            [c.args for c in sb.tk.CoreUtils.undo_chunk.call_args_list],
            [("Convert Case",), ("Strip Chars",), ("Suffix By Location",)],
        )

    def test_suffix_by_type_passes_spelling_and_placement(self):
        slots, sb = _panel()
        menu = sb.loaded_ui.naming.tb003.option_box.menu
        for name in NamingSlots.SUFFIX_FIELDS.values():
            getattr(menu, name).text.return_value = f"_{name[-3:]}"
            getattr(menu, name).option_box.affix_mode = "auto"
        menu.tb003_txt003.option_box.affix_mode = "prefix"
        for box, on in (
            ("tb003_chk002", True),
            ("tb003_chk003", False),
            ("tb003_chk004", True),
        ):
            getattr(menu, box).isChecked.return_value = on
        slots.tb003(sb.loaded_ui.naming.tb003)
        args, kwargs = sb.tk.Naming.suffix_by_type.call_args
        self.assertEqual(args, (["|a", "|b"],))
        self.assertEqual(kwargs["mesh_suffix"], "_003")
        self.assertEqual(kwargs["affix_modes"]["mesh_suffix"], "prefix")
        self.assertEqual(kwargs["affix_modes"]["group_suffix"], "auto")
        self.assertEqual(
            (
                kwargs["strip_trailing_ints"],
                kwargs["strip_trailing_underscores"],
                kwargs["strip_trailing_padding"],
                kwargs["dry_run"],
            ),
            (True, False, True, False),
        )
        sb.tk.CoreUtils.undo_chunk.assert_called_once_with("Suffix By Type")

    def test_a_scene_dry_run_records_nothing_and_arms_apply(self):
        slots, sb = _panel(dry_run=True)
        ui = sb.loaded_ui.naming
        ui.txt001.text.return_value = "**_v2"
        slots.txt001(ui.txt001)
        self.assertIs(sb.tk.Naming.rename.call_args.kwargs["dry_run"], True)
        sb.tk.CoreUtils.undo_chunk.assert_not_called()
        slots._apply_btn.setVisible.assert_called_with(True)
        ui.footer.setText.assert_called_with(
            "Dry run — Apply to commit", level="warning"
        )

        # Apply commits the previewed call, frozen: a field edit and a new
        # selection since the preview change nothing.
        ui.txt001.text.return_value = "**_WRONG"
        sb.tk.Naming.scope_objects.side_effect = lambda scene=False: ["|other"]
        slots._apply_dry_run()
        args, kwargs = sb.tk.Naming.rename.call_args
        self.assertEqual(args, (["|a", "|b"], "**_v2", ui.txt000.text.return_value))
        self.assertIs(kwargs["dry_run"], False)
        sb.tk.CoreUtils.undo_chunk.assert_called_once_with("Rename")
        self.assertIsNone(slots._pending)
        slots._apply_btn.setVisible.assert_called_with(False)

    def test_scene_only_operations_report_in_a_file_scope(self):
        for button, engine, label in (
            ("tb001", "append_location_based_suffix", "Suffix By Location"),
            ("tb003", "suffix_by_type", "Suffix By Type"),
        ):
            with self.subTest(button=button):
                slots, sb = _panel(scope="Files")
                ui = sb.loaded_ui.naming
                getattr(slots, button)(getattr(ui, button))
                self.assertIn(f"{label} applies to scene objects only", _report(ui))
                getattr(sb.tk.Naming, engine).assert_not_called()
                sb.tk.Naming.scope_objects.assert_not_called()


class TestNamingPanelFiles(_PanelCase):
    """The file scopes end to end on a temp directory (pythontk's FileNaming)."""

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp(prefix="naming_panel_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._write("pCube1.png", "pCube2.PNG", "sphere.txt")

    def _write(self, *names):
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        for name in names:
            with open(os.path.join(self.tmp, name), "wb") as f:
                f.write(b"x")

    def listing(self):
        return sorted(os.listdir(self.tmp))

    def _directory_panel(self, dry_run=False, base_names=False):
        slots, sb = _panel(scope="Directory", dry_run=dry_run)
        _set_scope(sb.loaded_ui.naming, "Directory", dry_run, base_names)
        self.browsed = []
        sb.dir_dialog.side_effect = lambda *a, **k: (self.browsed.append(k), self.tmp)[
            1
        ]
        return slots, sb, sb.loaded_ui.naming

    def _find(self, slots, ui, text):
        ui.txt000.text.return_value = text
        slots.txt000(ui.txt000)

    def _rename(self, slots, ui, to):
        ui.txt001.text.return_value = to
        slots.txt001(ui.txt001)

    def test_directory_scope_workflow(self):
        slots, sb, ui = self._directory_panel()
        self.assertTrue(slots.file_scope)
        self._find(slots, ui, "pCube*")
        self.assertEqual(len(self.browsed), 1)
        self.assertEqual(self.browsed[0]["start_dir"], "", "the host's workspace root")
        self.assertEqual(
            sorted(os.path.basename(f) for f in slots._files),
            ["pCube1.png", "pCube2.PNG"],
        )
        out = _report(ui)
        self.assertIn("Find — 2 of 3 files", out)
        self.assertIn("Directory:", out)

        _set_scope(ui, "Directory", dry_run=True)
        self._rename(slots, ui, "*box*")
        out = _report(ui)
        self.assertIn("DRY RUN", out)
        self.assertIn("pCube1 → box1", out)
        self.assertEqual(self.listing(), ["pCube1.png", "pCube2.PNG", "sphere.txt"])
        self.assertEqual(len(self.browsed), 1, "the operations reuse the working set")

        _set_scope(ui, "Directory", dry_run=False)
        self._rename(slots, ui, "*box*")
        self.assertEqual(self.listing(), ["box1.png", "box2.PNG", "sphere.txt"])
        self.assertEqual(
            sorted(os.path.basename(f) for f in slots._files), ["box1.png", "box2.PNG"]
        )
        sb.tk.CoreUtils.undo_chunk.assert_not_called()  # a file rename is no scene step

        ui.tb000.option_box.menu.cmb001.currentText.return_value = "upper"
        slots.tb000(ui.tb000)
        self.assertEqual(self.listing(), ["BOX1.png", "BOX2.PNG", "sphere.txt"])

        ui.tb002.option_box.menu.s000.value.return_value = 1
        ui.tb002.option_box.menu.cmb002.currentText.return_value = "Leading"
        slots.tb002(ui.tb002)
        self.assertEqual(self.listing(), ["OX1.png", "OX2.PNG", "sphere.txt"])
        sb.tk.Naming.rename.assert_not_called()

    def test_a_browse_starts_where_the_last_one_ended(self):
        slots, sb, ui = self._directory_panel()
        sb.tk.EnvUtils.workspace_root.return_value = "/host/project"
        self._find(slots, ui, "")
        self.assertEqual(self.browsed[-1]["start_dir"], "/host/project")
        self._find(slots, ui, "")
        self.assertEqual(
            os.path.normpath(self.browsed[-1]["start_dir"]), os.path.normpath(self.tmp)
        )

    def test_files_scope_and_a_cancelled_browser(self):
        slots, sb = _panel(scope="Files")
        ui = sb.loaded_ui.naming
        picked = [os.path.join(self.tmp, "sphere.txt")]
        sb.file_dialog.return_value = picked
        self._find(slots, ui, "")
        self.assertEqual(slots._files, picked, "an empty Find keeps every chosen file")

        sb.file_dialog.return_value = []
        self._find(slots, ui, "")
        self.assertEqual(slots._files, [])
        self.assertIn("No files chosen", _report(ui))

    def test_rename_on_base_names_carries_the_texture_set(self):
        self._write("rock_Normal.png", "rock_AO.png", "rock_ORM.1001.png", "note.txt")
        slots, sb, ui = self._directory_panel(base_names=True)
        self._find(slots, ui, "rock")
        self.assertEqual(
            sorted(os.path.basename(f) for f in slots._files),
            ["rock_AO.png", "rock_Normal.png", "rock_ORM.1001.png"],
        )
        self._rename(slots, ui, "stone")
        self.assertEqual(
            self.listing(),
            ["note.txt", "stone_AO.png", "stone_Normal.png", "stone_ORM.1001.png"],
        )

    def test_apply_commits_the_previewed_plan(self):
        self._write("rock_Normal.png", "rock_AO.png", "rock_ORM.1001.png", "note.txt")
        slots, sb, ui = self._directory_panel(dry_run=True, base_names=True)
        self._find(slots, ui, "")
        self._rename(slots, ui, "**_v2")
        self.assertIn("DRY RUN", _report(ui))
        self.assertEqual(
            self.listing(),
            ["note.txt", "rock_AO.png", "rock_Normal.png", "rock_ORM.1001.png"],
        )
        slots._apply_btn.setVisible.assert_called_with(True)

        ui.txt001.text.return_value = "**_WRONG"  # the armed call is frozen
        slots._apply_dry_run()
        self.assertIsNone(slots._pending)
        self.assertEqual(
            self.listing(),
            [
                "note_v2.txt",
                "rock_v2_AO.png",
                "rock_v2_Normal.png",
                "rock_v2_ORM.1001.png",
            ],
        )
        # The working set and the report follow, exactly as a live run's do.
        self.assertEqual(
            sorted(os.path.basename(f) for f in slots._files), self.listing()
        )
        self.assertIn("Directory:", _report(ui))

    def test_a_scope_change_or_an_aborted_operation_disarms_apply(self):
        for stale in ("scope change", "aborted operation"):
            with self.subTest(stale=stale):
                self._write("rock_AO.png")
                slots, sb, ui = self._directory_panel(dry_run=True)
                self._find(slots, ui, "")
                self._rename(slots, ui, "**_v2")
                self.assertIsNotNone(slots._pending)
                if stale == "scope change":
                    _set_scope(ui, "Selection")
                    slots._on_scope_changed()
                else:  # the working set is gone and the browser is cancelled
                    self._write()
                    sb.dir_dialog.side_effect = lambda *a, **k: ""
                    self._rename(slots, ui, "**_v2")
                self.assertIsNone(slots._pending)
                slots._apply_btn.setVisible.assert_called_with(False)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestNamingPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")
        # The panel redirects the engine's class logger into its (stand-in)
        # pane; give the logger back as it was.
        logger = self.mtk.Naming.logger
        handlers, level = list(logger.handlers), logger.level
        self.addCleanup(setattr, logger, "handlers", handlers)
        self.addCleanup(logger.setLevel, level)

    def _real(self, scope="Selection"):
        slots, sb = _panel(tk=self.mtk, scope=scope)
        return slots, sb, sb.loaded_ui.naming

    def test_a_rename_is_one_undo_step(self):
        cmds = self.cmds
        a = cmds.polyCube(name="nmPanelCubeA")[0]
        b = cmds.polyCube(name="nmPanelCubeB")[0]
        cmds.select([a, b])
        slots, sb, ui = self._real()
        ui.txt000.text.return_value = "*Cube*"
        ui.txt001.text.return_value = "*Box*"
        cmds.undoInfo(state=True, infinity=True)
        slots.txt001(ui.txt001)
        self.assertTrue(cmds.objExists("nmPanelBoxA") and cmds.objExists("nmPanelBoxB"))
        cmds.undo()
        self.assertTrue(
            cmds.objExists("nmPanelCubeA") and cmds.objExists("nmPanelCubeB")
        )

    def test_find_selects_the_matches(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="nmFindMe")[0]
        loc = cmds.spaceLocator(name="nmFindLoc")[0]
        slots, sb, ui = self._real()
        ui.txt000.text.return_value = "nmFindMe|nmFindLoc"  # exact terms: no shapes
        slots.txt000(ui.txt000)
        self.assertEqual(sorted(cmds.ls(selection=True)), sorted([cube, loc]))
        ui.txt000.text.return_value = "nmFind*"
        ui.txt000.option_box.menu.chk007.isChecked.return_value = True
        slots.txt000(ui.txt000)
        self.assertEqual(cmds.ls(selection=True), [loc])

    def test_suffix_by_location_skips_what_has_no_location(self):
        cmds = self.cmds
        near = cmds.polyCube(name="nmRow")[0]
        far = cmds.polyCube(name="nmRow")[0]  # Maya names it nmRow1
        cmds.move(5, 0, 0, far)
        material = cmds.shadingNode("lambert", asShader=True, name="nmRowMat")
        cmds.select([far, near, material])
        slots, sb, ui = self._real()
        fields = ui.tb003.option_box.menu
        for name in NamingSlots.SUFFIX_FIELDS.values():
            getattr(fields, name).text.return_value = ""  # no defined suffixes
        menu = ui.tb001.option_box.menu
        menu.cmb_reference.currentText.return_value = "Scene Origin"
        for box in ("chk005", "chk003", "chk004", "chk007"):
            getattr(menu, box).isChecked.return_value = False
        menu.chk002.isChecked.return_value = True  # Strip Trailing Integers
        slots.tb001(ui.tb001)
        self.assertTrue(cmds.objExists("nmRow_01") and cmds.objExists("nmRow_02"))
        self.assertTrue(cmds.objExists("nmRowMat"), "a material has no location")

    def test_the_editor_rows_cover_the_whole_convention(self):
        slots, sb, ui = self._real()
        keys = [k for _g, rows in slots._convention_groups() for k, _n in rows]
        self.assertEqual(sorted(keys), sorted(ptk.NamingConvention.DEFAULTS))
        self.assertEqual(
            self.mtk.Naming.UNSUPPORTED_TYPES, {}, "Maya applies every row"
        )


if __name__ == "__main__":
    unittest.main()
