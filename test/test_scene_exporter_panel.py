#!/usr/bin/python
# coding=utf-8
"""The Scene Exporter panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here. Its ``SceneExporter`` is
pythontk's real ``SceneExporterBase`` -- the run configuration, the retired-row
notes, the legacy RegEx fold and the check-failure dialog body are the shell
both hosts share -- over a stub task manager, with the host half (presets,
scope, the write) recording what the panel asks: plain pytest, no DCC, no
widgets loaded. The ``.ui`` is read as XML. In Maya, the same class drives the
real ``mtk.SceneExporter``: an export through the panel, the Output Filename's
live preview, the rows built from Maya's own definitions. The engines' side
(the presets scan, the embedding, ``objects_to_export``) is the libraries':
``test_scene_exporter.py`` in each, and pythontk's for the shell.
"""

import contextlib
import inspect
import os
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.scene_exporter import SceneExporterSlots

UI_PATH = os.path.join(
    os.path.dirname(tentacle.__file__), "ui", "tools", "scene_exporter.ui"
)


class _Tasks:
    """The slice of a host TaskManager the panel and the shell read."""

    def __init__(self, logger, task_definitions=None, check_definitions=None):
        self.logger = logger
        self.task_definitions = dict(task_definitions or {})
        self.check_definitions = dict(check_definitions or {})


class _FakeExporter(ptk.SceneExporterBase):
    """A host engine: pythontk's real shell, the host half recorded."""

    TASK_MANAGER_CLASS = _Tasks
    EXPORT_PRESET_DIR = "fakehost/scene_exporter"
    EXCLUDE_HDR_IN_VISIBLE_SCOPE = False

    def __init__(self, *args, **kwargs):
        self.calls = []
        self.preset_scan = {"None": None, "alpha": "/presets/alpha.preset"}
        self.preset_dir = "/presets"
        self.restored = None
        self.export_result = True
        self.cancel = False
        self.exported_objects = None
        super().__init__(*args, **kwargs)

    @property
    def presets(self):
        return dict(self.preset_scan)

    def fbx_preset_dir(self):
        return self.preset_dir

    def refresh_fbx_presets(self):
        self.calls.append(("refresh_fbx_presets",))
        return self.presets

    def fbx_preset_metadata(self, preset):
        self.calls.append(("fbx_preset_metadata", preset))
        return {"fbx_preset_name": "alpha"} if preset else {}

    def restore_fbx_preset(self, metadata):
        self.calls.append(("restore_fbx_preset", metadata))
        return self.restored

    def edit_fbx_preset(self, preset=None):
        self.calls.append(("edit_fbx_preset", preset))

    @staticmethod
    def objects_to_export(export_mode="visible"):
        return [f"<{export_mode}>"]

    def perform_export(self, **kwargs):
        self.calls.append(("perform_export", kwargs))
        # The run resolves the scope itself, from the callable it was handed.
        self.exported_objects = kwargs["objects"]()
        self._export_cancelled = self.cancel
        return self.export_result


def _exporter(task_definitions=None, check_definitions=None, **attrs):
    """A ``_FakeExporter`` class whose task manager carries these definitions
    (the shell reads them once, so they are fixed before the panel is built)."""

    def tasks(logger):
        return _Tasks(logger, task_definitions, check_definitions)

    return type(
        "_Exporter",
        (_FakeExporter,),
        {"TASK_MANAGER_CLASS": staticmethod(tasks), **attrs},
    )


def _panel(exporter_class=_FakeExporter, tk=None):
    """A Slots instance over a mock switchboard whose toolkit builds
    *exporter_class* (or is *tk*, handed over before the panel is built, as
    ``Slots.tk`` is)."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.SceneExporter = exporter_class
    slots = SceneExporterSlots(sb)
    return slots, sb, sb.loaded_ui.scene_exporter


class _Widget:
    """Stands in for every widget ``b000`` reads -- one accessor per role."""

    def __init__(self, value=None, checked=False):
        self._value = value
        self._checked = checked
        self.texts = []

    def text(self):
        return self._value or ""

    def currentData(self):
        return self._value

    def isChecked(self):
        return self._checked

    def setChecked(self, state):
        self._checked = bool(state)

    def setText(self, text, **kwargs):
        self.texts.append((text, kwargs.get("level")))

    def clear(self):
        pass


def _export_ui(**extra):
    """The widgets ``b000`` reads, Override Checks armed; *extra* adds rows."""
    widgets = dict(
        txt000=_Widget("/out"),
        txt001=_Widget("asset"),
        txt003=_Widget(),
        b009=_Widget(checked=True),
        cmb000=_Widget("/presets/alpha.preset"),
        cmb004=_Widget("fbx"),
        footer=_Widget(),
    )
    widgets.update(extra)
    return types.SimpleNamespace(**widgets)


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        # The class logger is shared, and the panel redirects it into its log
        # pane: a fake keeps the run's records (and handlers) off it. The
        # engine adopts the same fake, so its notes land here too.
        self.logger = mock.MagicMock()
        patcher = mock.patch.object(SceneExporterSlots, "logger", self.logger)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _said(self, level):
        return [str(c.args[0]) for c in getattr(self.logger, level).call_args_list]


class TestSceneExporterPanelSetup(_PanelCase):
    def test_the_engine_is_built_over_the_panels_logger_and_dialogs(self):
        """The panel composes the host's engine: the engine and its task
        manager log through the panel's logger (so every task's line reaches
        the log pane), its two seams are the panel's dialogs, and the panel's
        INFO level is left alone."""
        slots, sb, ui = _panel()
        exporter = slots.exporter
        self.assertIsInstance(exporter, _FakeExporter)
        self.assertIs(exporter.logger, self.logger)
        self.assertIs(exporter.task_manager.logger, self.logger)
        self.assertEqual(exporter.confirm, slots.confirm)
        self.assertEqual(exporter.decide_check_failure, slots.decide_check_failure)
        self.logger.setLevel.assert_called_once_with("INFO")

    def test_the_log_pane_takes_the_run_and_its_links(self):
        slots, sb, ui = _panel()
        ui.txt001.setText.assert_called_with("")
        ui.txt003.setText.assert_called_with("")
        self.logger.hide_logger_name.assert_called_once_with(True)
        self.logger.set_text_handler.assert_called_once_with(
            sb.registered_widgets.TextEditLogHandler
        )
        self.logger.setup_logging_redirect.assert_called_once_with(ui.txt003)
        ui.txt003.anchorClicked.connect.assert_called_once_with(
            slots._on_log_link_clicked
        )

    def test_opening_says_the_retired_state_and_folds_the_regex_field(self):
        """Wired in ``__init__`` with the window's own settings store: the
        retired rows' saved state is said once, and a saved RegEx field folds
        into the Output Filename's SAVED value through the state manager."""
        with (
            mock.patch.object(
                _FakeExporter, "note_retired_panel_state", autospec=True
            ) as note,
            mock.patch.object(
                _FakeExporter, "migrate_legacy_regex", autospec=True
            ) as fold,
        ):
            slots, sb, ui = _panel()
        note.assert_called_once_with(slots.exporter, ui.settings)
        args = fold.call_args.args
        self.assertEqual(
            args[:3], (slots.exporter, ui.settings, ui.txt001.objectName())
        )
        args[3]("WIP_*")
        ui.state.save.assert_called_once_with(ui.txt001, "WIP_*")

    def test_override_checks_never_restores_its_armed_state(self):
        """A per-run escape hatch must not ride QSettings into the next
        session: a registered widget persists by default and its restore runs
        AFTER the slots ``__init__``, which used to re-arm the toggle right
        over the ``setChecked(False)`` there."""
        slots, sb, ui = _panel()
        self.assertFalse(ui.b009.restore_state)
        ui.b009.setChecked.assert_called_with(False)
        ui.b009.setEnabled.assert_called_with(True)

    def test_a_saved_regex_field_folds_into_the_restored_output_filename(self):
        """REGRESSION (2026-10-19): the retired RegEx field was read as
        ``settings.value("txt002")``, but the switchboard saves a widget under
        ``<objectName>/<signal>``, so a saved rule was never migrated; folded
        into the widget at ``txt001_init`` it would not have survived either --
        the switchboard restores the field's saved pattern right after. Opened
        here in the switchboard's order over a real ``StateManager``."""
        import uuid

        from qtpy import QtWidgets
        from uitk.managers.settings_manager import SettingsManager
        from uitk.managers.state_manager import StateManager
        from uitk.testing import TestSandbox

        if not TestSandbox.is_active():
            self.skipTest("uitk's settings sandbox is not active: refusing to write")

        class _Field:
            """``txt001`` as ``MainWindow.register_widget`` registers it, over
            the slice of a line edit the state manager reads and writes."""

            restore_state = True
            derived_type = QtWidgets.QLineEdit

            def __init__(self):
                self._text, self._blocked, self._props = "", False, {}
                self.tooltip, self.option_box = mock.MagicMock(), mock.MagicMock()

            def objectName(self):
                return "txt001"

            def default_signals(self):
                return "textChanged"

            def text(self):
                return self._text

            def setText(self, text):
                self._text = text

            def blockSignals(self, block):
                was, self._blocked = self._blocked, block
                return was

            def signalsBlocked(self):
                return self._blocked

            def property(self, name):
                return self._props.get(name)

            def setProperty(self, name, value):
                self._props[name] = value

            def update(self):
                pass

        def open_panel(store):
            field = _Field()
            sb = mock.MagicMock()
            sb.tk.SceneExporter = _FakeExporter
            ui = sb.loaded_ui.scene_exporter
            ui.settings, ui.state, ui.txt001 = store, StateManager(store), field
            slots = SceneExporterSlots(sb)
            slots.txt001_init(field)
            ui.state.capture_default(field)
            ui.state.load(field)
            return field, ui.state

        for pattern, regex, folded in (
            ("WIP_*", "test_|prod_", "WIP_{scene:test_->prod_}"),
            (None, "_bar.*", "{scene:_bar.*->}"),  # no pattern saved: the name
        ):
            with self.subTest(pattern=pattern, regex=regex):
                self.logger.reset_mock()
                store = SettingsManager(
                    namespace=f"switchboard/test_scene_exporter_{uuid.uuid4().hex[:8]}"
                )
                self.addCleanup(store.clear)
                if pattern is not None:
                    store.setValue("txt001/textChanged", pattern)
                store.setValue("txt002/textChanged", regex)

                field, state = open_panel(store)
                self.assertEqual(field.text(), folded, "the restore shows the rule")
                self.assertTrue(
                    any("RegEx field is retired" in m for m in self._said("info"))
                )
                self.assertEqual(store.keys(), ["txt001/textChanged"])
                self.assertEqual(
                    state.default_for(field), "", "a reset still empties it"
                )

                field, _ = open_panel(store)  # and the next session
                self.assertEqual(field.text(), folded)


class TestSceneExporterPanelRules(_PanelCase):
    def _rules(self, exporter_class=_FakeExporter):
        slots, sb, ui = _panel(exporter_class)
        sb.enable_when.assert_not_called()  # hidden, never greyed (2026-09-14)
        return {c.args[1]: c.args[2:] for c in sb.show_when.call_args_list}

    def test_irrelevant_settings_hide_on_one_rule_each(self):
        """Every "irrelevant unless" relationship is ONE ``sb.show_when`` rule
        -- hidden rather than greyed, no per-trigger slot. Pins the dependants,
        their triggers and the conditions; the rule engine is uitk's."""
        rules = self._rules()
        # No size-dial rule: the ceiling rides the Optimize Textures combo.
        self.assertNotIn("texture_max_size", rules)
        # Texture File Type is NOT gated: a GLB re-encodes to it regardless.
        self.assertNotIn("texture_file_type", rules)
        self.assertEqual(rules["texture_write_back"][0], ["texture_optimize", "cmb005"])
        written_back = rules["texture_write_back"][1]
        self.assertEqual(
            (written_back(1, None), written_back(0, "glTF"), written_back(0, None)),
            (True, True, False),
        )
        # A USD deliverable: the FBX-only knobs, the FBX/GLB verifier and the
        # rig-helper pass go.
        trigger, usd = rules[
            "cmb000,animation_clips,bake_range,verify_deliverables,drop_rig_apparatus"
        ]
        self.assertEqual(trigger, "cmb004")
        self.assertEqual((usd("fbx"), usd("glb"), usd("usd")), (True, True, False))
        # The GLB-only dials.
        self.assertEqual(rules["secondary_max_size"], ("cmb004", {"glb", "fbx_glb"}))
        trigger, rdo = rules["uastc_rdo"]
        self.assertEqual(trigger, ["cmb004", "texture_file_type"])
        self.assertEqual(
            (rdo("glb", "ktx2"), rdo("fbx_glb", "ktx2+fallback"), rdo("fbx", "ktx2")),
            (True, True, False),
        )
        self.assertFalse(rdo("glb", "png"), "RDO is a KTX2 encode dial")
        trigger, keys = rules["glb_key_tolerance"]
        self.assertEqual(trigger, ["cmb004", "optimize_level"])
        self.assertEqual(
            (keys("glb", "extremes"), keys("glb", None), keys("fbx", "extremes")),
            (True, False, False),
        )

    def test_exclude_hdr_hides_under_visible_only_where_it_cannot_act(self):
        """Maya's visible geometry never holds a skydome, so the row hides
        under the Visible scope; Blender's exclusion also strips a visible mesh
        dome, so it stays. The engine says which, not a host branch."""
        trigger, condition = self._rules()["exclude_hdr"]
        self.assertEqual(trigger, "export_visible_objects")
        self.assertEqual(
            (condition("visible"), condition("selected"), condition("all")),
            (False, True, True),
        )
        kept = _exporter(EXCLUDE_HDR_IN_VISIBLE_SCOPE=True)
        self.assertNotIn("exclude_hdr", self._rules(kept))


class TestSceneExporterPanelDialogs(_PanelCase):
    def test_confirm_survives_the_rich_text_engine(self):
        """``sb.message_box`` hands its string to Qt's rich-text engine, which
        collapses a newline to a space -- so the seam's plain text arrived as
        one run-on paragraph, the KTX2 install prompt included."""
        slots, sb, ui = _panel()
        sb.message_box.return_value = "Yes"
        self.assertTrue(slots.confirm("line one\n\nline two & <three>"))
        body, *buttons = sb.message_box.call_args.args
        self.assertIn("<br><br>", body)
        self.assertNotIn("\n", body)
        self.assertIn("&amp;", body)
        self.assertNotIn("<three>", body)
        self.assertEqual(buttons, ["Yes", "No"])
        sb.message_box.return_value = "No"
        self.assertFalse(slots.confirm("again?"))

    def test_a_failed_check_asks_with_three_named_buttons_and_cancel_on_enter(self):
        """Override All / Override / Cancel, mapped back to the runner's
        answers; Enter is Cancel, and anything unexpected stops the run."""
        slots, sb, ui = _panel()
        for reply, answer in (
            ("Override All", ptk.TaskFactory.CHECK_OVERRIDE_ALL),
            ("Override", ptk.TaskFactory.CHECK_OVERRIDE),
            ("Cancel", ptk.TaskFactory.CHECK_ABORT),
            (None, ptk.TaskFactory.CHECK_ABORT),
        ):
            sb.message_box.return_value = reply
            got = slots.decide_check_failure(
                "check_path_length", ["too long"], ["check_valid_paths"]
            )
            self.assertEqual(got, answer, reply)
        call = sb.message_box.call_args
        self.assertEqual(call.args[1:], ("Override All", "Override", "Cancel"))
        self.assertEqual(call.kwargs["default"], "Cancel")
        self.assertIsNone(call.kwargs["timeout"], "a question must not time out")
        self.assertIn("Path Length", call.args[0])
        self.assertIn("Valid Paths", call.args[0], "the remaining checks show")

    def test_a_show_link_opens_the_panel_it_names_and_the_rest_go_to_the_host(self):
        slots, sb, ui = _panel()
        show = types.SimpleNamespace(
            scheme=lambda: "action", host=lambda: "show", query=lambda: "ui=shots"
        )
        slots._on_log_link_clicked(show)
        sb.handlers.marking_menu.show.assert_called_once_with("shots")
        sb.tk.UiUtils.dispatch_log_link.assert_not_called()
        other = types.SimpleNamespace(scheme=lambda: "action", host=lambda: "open")
        slots._on_log_link_clicked(other)
        sb.tk.UiUtils.dispatch_log_link.assert_called_once_with(other, self.logger)

    def test_the_workspace_is_the_hosts_and_its_absence_is_said(self):
        slots, sb, ui = _panel()
        sb.tk.EnvUtils.workspace_root.return_value = "/proj"
        self.assertEqual(slots.workspace, "/proj")
        self.logger.error.assert_not_called()
        sb.tk.EnvUtils.workspace_root.return_value = ""
        self.assertEqual(slots.workspace, "")
        self.logger.error.assert_called_once()


class TestSceneExporterPanelFbxPresets(_PanelCase):
    def _combo(self, current=None, text=""):
        combo = mock.MagicMock()
        combo.is_initialized = False
        combo.count.return_value = 2 if current or text else 0
        combo.currentData.return_value = current
        combo.currentText.return_value = text
        return combo

    def test_the_combo_lists_the_hosts_presets_by_name(self):
        """Persisted by NAME: the list is rebuilt from a scan each show."""
        slots, sb, ui = _panel()
        combo = self._combo()
        slots.cmb000_init(combo)
        self.assertEqual(combo.restore_by, "text")
        self.assertTrue(combo.refresh_on_show)
        combo.add.assert_called_once_with(slots.exporter.presets, clear=True)
        names = [
            c.kwargs["setObjectName"] for c in combo.option_box.menu.add.call_args_list
        ]
        self.assertEqual(names, ["b007", "b008"])
        self.assertEqual(
            combo.option_box.add_action.call_args.kwargs["callback"],
            slots._refresh_presets,
        )
        ui.txt003.setHtml.assert_not_called()

    def test_the_selection_survives_a_rescan(self):
        slots, sb, ui = _panel()
        combo = self._combo(current="/presets/alpha.preset")
        slots.cmb000_init(combo)
        combo.setCurrentText.assert_called_once_with("alpha")
        combo = self._combo(text="alpha")
        slots.cmb000_init(combo)
        combo.setCurrentText.assert_called_once_with("alpha")

    def test_a_missing_directory_or_an_empty_one_is_said(self):
        slots, sb, ui = _panel()
        slots.exporter.preset_dir = None
        slots.cmb000_init(self._combo())
        self.assertIn("not found", ui.txt003.setHtml.call_args.args[0])
        slots.exporter.preset_dir = "/presets"
        slots.exporter.preset_scan = {"None": None}
        slots.cmb000_init(self._combo())
        self.assertIn("No presets found", ui.txt003.setHtml.call_args.args[0])

    def test_refresh_rescans_then_repopulates(self):
        slots, sb, ui = _panel()
        slots._refresh_presets()
        self.assertEqual(slots.exporter.calls, [("refresh_fbx_presets",)])
        ui.cmb000.init_slot.assert_called_once_with()

    def test_open_directory_opens_the_hosts_preset_folder(self):
        slots, sb, ui = _panel()
        with mock.patch.object(ptk.FileUtils, "open_explorer") as opened:
            slots.b007()
            opened.assert_called_once_with(
                "/presets", create_dir=True, logger=self.logger
            )
            slots.exporter.preset_dir = None
            slots.b007()
        self.assertEqual(opened.call_count, 1)
        self.assertTrue(self._said("error"))

    def test_edit_hands_the_selected_preset_to_the_host(self):
        slots, sb, ui = _panel()
        ui.cmb000.currentData.return_value = "/presets/alpha.preset"
        slots.b008()
        self.assertEqual(
            slots.exporter.calls, [("edit_fbx_preset", "/presets/alpha.preset")]
        )

    def test_an_export_preset_embeds_and_restores_the_fbx_preset(self):
        slots, sb, ui = _panel()
        ui.cmb000.currentData.return_value = "/presets/alpha.preset"
        self.assertEqual(
            slots._fbx_preset_metadata_provider(), {"fbx_preset_name": "alpha"}
        )
        slots._on_fbx_preset_metadata_loaded({"fbx_preset_name": "here"})
        ui.cmb000.init_slot.assert_not_called()  # nothing restored: nothing to show
        slots.exporter.restored = "/presets/beta.preset"
        slots._on_fbx_preset_metadata_loaded({"fbx_preset_name": "beta"})
        ui.cmb000.init_slot.assert_called_once_with()

    def test_no_add_or_delete_preset_slots(self):
        """Presets are added and deleted in the directory Open FBX Preset
        Directory opens: the one-shot Add (b003) / Delete (b004) are gone."""
        for name in ("b003", "b004"):
            self.assertFalse(hasattr(SceneExporterSlots, name), name)


class TestSceneExporterPanelExportPreset(_PanelCase):
    class _Selector:
        """cmb007: ``cmb007_init`` wires ``activated``; ``emit`` is a pick."""

        def __init__(self, names=()):
            self.names = list(names)
            self._slots = []
            self.activated = types.SimpleNamespace(
                connect=self._slots.append, emit=self._pick
            )

        def _pick(self, index):
            for slot in self._slots:
                slot(index)

        def itemText(self, index):
            return self.names[index]

    def test_the_manager_adopts_the_panel_logger_before_the_restore(self):
        """The manager's user-facing warnings reach the log pane only through
        the panel's logger, and its active-preset restore (``wire_combo``) is
        exactly the load that warns -- so the adoption comes first."""
        slots, sb, ui = _panel()
        mgr = ui.presets
        slots.cmb007_init(self._Selector())
        names = [c[0] for c in mgr.method_calls]
        self.assertLess(names.index("use_logger"), names.index("wire_combo"))
        mgr.use_logger.assert_called_once_with(self.logger)
        mgr.setup.assert_called_once_with(
            preset_dir="fakehost/scene_exporter",
            metadata_provider=slots._fbx_preset_metadata_provider,
            on_metadata_loaded=slots._on_fbx_preset_metadata_loaded,
        )
        self.assertEqual(mgr.scope, "window")
        mgr.exclude.assert_called_once_with("txt000", "txt001", "txt003")

    def test_a_preset_asking_for_a_retired_naming_row_says_so(self):
        """A preset saved while the Version row and the Timestamp checkbox
        existed loads with both keys ignored, and a series it versioned stops
        versioning without a word: picking it warns and names the spelling that
        replaces each; a preset storing them empty stays quiet."""
        stored = {
            "legacy": {"version": "{stem}_v{n:03d}", "chk004": True},
            "current": {"version": "", "chk004": False},
        }
        slots, sb, ui = _panel()
        ui.presets.read.side_effect = stored.get
        combo = self._Selector(stored)
        with mock.patch.object(
            _FakeExporter, "note_retired_preset_rows", autospec=True
        ) as rows:
            slots.cmb007_init(combo)
            combo.activated.emit(0)
            said = "\n".join(self._said("warning"))
            for expected in ("'legacy'", "*_v{n:03d}", "*_{date}_{time}"):
                self.assertIn(expected, said)
            self.logger.warning.reset_mock()
            combo.activated.emit(1)
            self.assertEqual(self._said("warning"), [])
        # Every pick is also read for the rows retired 2026-10-19 (the shell).
        self.assertEqual(
            [c.args[1:] for c in rows.call_args_list],
            [("legacy", stored["legacy"]), ("current", stored["current"])],
        )

    def test_the_retired_naming_rows_are_never_built(self):
        """Named only as retired preset keys: the Output Filename spells both
        (*_v{n:03d}, *_{date}_{time})."""
        layout = [n for _, names in SceneExporterSlots._SETTINGS_LAYOUT for n in names]
        self.assertNotIn("version", layout)
        self.assertIn("chk004", SceneExporterSlots._RETIRED_NAMING_KEYS)
        self.assertNotIn(
            'setObjectName="chk004"', inspect.getsource(SceneExporterSlots)
        )


class _Built:
    """A widget the row builders made: the attributes they set on it."""

    def __init__(self, **kwargs):
        self.attrs = dict(kwargs)


class _Separator(_Built):
    pass


def _record_builders(slots):
    """Give *slots* the row builders' slice of the switchboard and ui, which
    records what each widget is set to (no Qt widget is made)."""
    slots.sb = types.SimpleNamespace(
        QtWidgets=types.SimpleNamespace(QCheckBox=_Built, QLineEdit=_Built),
        registered_widgets=types.SimpleNamespace(
            Separator=_Separator, ComboBox=_Built, SpinBox=_Built, Header=_Built
        ),
        convert_to_legal_name=lambda name: name,
    )
    slots.ui = types.SimpleNamespace(
        set_attributes=lambda widget, **kw: widget.attrs.update(kw)
    )


class TestSceneExporterPanelRows(_PanelCase):
    def test_definition_rows_separate_each_group_and_skip_settings_rows(self):
        definitions = {
            "a": {"group": "One", "setText": "A"},
            "b": {
                "group": "One",
                "widget_type": "ComboBox",
                "value_method": "currentData",
            },
            "s": {"panel": "settings", "group": "Scope"},
            "c": {"group": "Two", "object_name": "chk_c"},
        }
        slots, sb, ui = _panel()
        _record_builders(slots)
        rows = slots._definition_rows(definitions)
        self.assertEqual([label for _w, label in rows], ["One", "a", "b", "Two", "c"])
        self.assertEqual(
            [w.attrs["title"] for w, _l in rows if isinstance(w, _Separator)],
            ["One", "Two"],
        )
        built = dict((label, w) for w, label in rows)
        for meta in ("widget_type", "panel", "group", "value_method", "object_name"):
            self.assertNotIn(meta, built["b"].attrs)
        self.assertEqual(built["a"].attrs["setObjectName"], "a")
        self.assertEqual(built["c"].attrs["setObjectName"], "chk_c")

    def test_a_definitions_restore_by_reaches_the_widget(self):
        """``restore_by`` is a widget attribute, not a meta key: a registry-
        derived combo persists by value only if the factory hands it on."""
        slots, sb, ui = _panel()
        _record_builders(slots)
        widget = slots._make_definition_widget(
            "texture_file_type",
            {"widget_type": "ComboBox", "restore_by": "text", "group": "Textures"},
        )
        self.assertEqual(widget.attrs["restore_by"], "text")
        with self.assertRaises(ValueError):
            slots._make_definition_widget("x", {"widget_type": "NoSuchWidget"})

    def test_the_settings_combo_lays_out_the_hosts_settings_rows(self):
        """``_SETTINGS_LAYOUT`` in order: the two UI-only rows under their
        saved objectNames, a definition the host lacks (blendertk: no
        set_workspace) skipped, and no Textures section."""
        defs = {
            "set_linear_unit": {"panel": "settings", "widget_type": "ComboBox"},
            "export_visible_objects": {"panel": "settings", "widget_type": "ComboBox"},
        }
        slots, sb, ui = _panel(_exporter(task_definitions=defs))
        _record_builders(slots)
        combo = mock.MagicMock()
        slots.cmb008_init(combo)
        rows = combo.add.call_args.args[0]
        self.assertEqual(
            [label for _w, label in rows],
            [
                "Output",
                "cmb000",
                "cmb004",
                "set_linear_unit",
                "Scope",
                "export_visible_objects",
            ],
        )
        self.assertEqual(
            combo.add.call_args.kwargs, {"header": "Settings", "clear": True}
        )
        self.assertEqual(
            set(SceneExporterSlots._SETTINGS_WIDGETS), {"cmb000", "cmb004"}
        )
        self.assertNotIn("Textures", dict(SceneExporterSlots._SETTINGS_LAYOUT))

    def test_tasks_and_checks_build_from_the_hosts_definitions(self):
        slots, sb, ui = _panel(
            _exporter(
                task_definitions={"t": {"group": "G"}},
                check_definitions={"check_c": {"group": "H"}},
            )
        )
        tasks, checks = mock.MagicMock(), mock.MagicMock()
        with mock.patch.object(
            slots, "_definition_rows", side_effect=lambda d: list(d)
        ):
            slots.cmb001_init(tasks)
            slots.cmb002_init(checks)
        tasks.add.assert_called_once_with(["t"], header="Tasks", clear=True)
        checks.add.assert_called_once_with(
            ["check_c"], header="Validation Checks", clear=True
        )

    def test_the_format_and_template_combos_keep_their_order(self):
        """Both persist by index: Format is pythontk's append-only table, the
        template "As Authored" first, then the registry's profiles in order."""
        slots, sb, ui = _panel()
        fmt, template = mock.MagicMock(), mock.MagicMock()
        fmt.is_initialized = template.is_initialized = False
        template.count.return_value = 0
        slots.cmb004_init(fmt)
        fmt.add.assert_called_once_with(
            dict(ptk.ExportProfile.OUTPUT_FORMATS), clear=True
        )
        slots.cmb005_init(template)
        items = template.add.call_args.args[0]
        self.assertEqual(list(items)[0], "As Authored")
        self.assertIsNone(items["As Authored"])
        self.assertEqual(
            list(items)[1:], [name for name, _ in ptk.OutputTemplates.profile_choices()]
        )

    def test_the_ignore_row_carries_its_case_toggle(self):
        slots, sb, ui = _panel()
        self.assertFalse(slots._ignore_groups_case_sensitive())  # the task's default
        row = mock.MagicMock()
        row.is_initialized = False
        slots.ignore_groups_init(row)
        kwargs = row.option_box.set_toggle.call_args.kwargs
        self.assertEqual(
            kwargs["settings_key"], "scene_exporter_ignore_groups_case_sensitive"
        )
        self.assertIs(kwargs["initial"], False)
        row.option_box.find_option.assert_called_once_with(sb.ToggleOption)
        row.option_box.find_option.return_value.is_on = True
        self.assertTrue(slots._ignore_groups_case_sensitive())
        row.is_initialized = True
        slots.ignore_groups_init(row)
        row.option_box.set_toggle.assert_called_once()

    def test_the_data_node_row_gets_one_viewer_action(self):
        """Added once (a repeat init must not stack a second button), with an
        icon uitk ships."""
        slots, sb, ui = _panel()
        row = mock.MagicMock()
        row.is_initialized = False
        slots.export_data_node_init(row)
        row.is_initialized = True
        slots.export_data_node_init(row)
        row.option_box.add_action.assert_called_once()
        kwargs = row.option_box.add_action.call_args.kwargs
        self.assertEqual(kwargs["callback"], slots._show_data_node)
        icons = os.path.join(os.path.dirname(__import__("uitk").__file__), "icons")
        self.assertTrue(os.path.isfile(os.path.join(icons, f"{kwargs['icon']}.svg")))

    def test_the_viewer_shows_the_hosts_data_node_dump(self):
        slots, sb, ui = _panel()
        nodes = sb.tk.DataNodes
        nodes.EXPORT = "data_export"
        nodes.dump_export_nodes.return_value = {"|data_export": {"a": 1}}
        sb.tk.EnvUtils.scene_artifact_path.return_value = "/cache/x_data_export.json"
        slots._show_data_node()
        sb.tk.EnvUtils.scene_artifact_path.assert_called_once_with("_data_export.json")
        call = sb.data_view_dialog.call_args
        self.assertEqual(call.args, ({"|data_export": {"a": 1}},))
        self.assertEqual(call.kwargs["save_path"], "/cache/x_data_export.json")
        self.assertIn("data_export", call.kwargs["empty_message"])


class TestSceneExporterPanelExport(_PanelCase):
    def _export(self, exporter_class=_FakeExporter, **ui_rows):
        slots, sb, ui = _panel(exporter_class)
        sb.progress = mock.MagicMock(
            return_value=contextlib.nullcontext(lambda *a: True)
        )
        slots.ui = _export_ui(**ui_rows)
        slots._recent_dirs_option = mock.MagicMock()
        slots._recent_names_option = mock.MagicMock()
        return slots, sb

    def _run(self, slots):
        slots.b000()
        ((name, kwargs),) = [
            c for c in slots.exporter.calls if c[0] == "perform_export"
        ]
        return kwargs

    def test_the_run_reads_the_panel_into_the_hosts_engine(self):
        slots, sb = self._export()
        kwargs = self._run(slots)
        self.assertEqual(kwargs["export_dir"], "/out")
        self.assertEqual(kwargs["output_name"], "asset")
        self.assertEqual(kwargs["preset_file"], "/presets/alpha.preset")
        self.assertIs(kwargs["export_visible"], True)
        self.assertEqual(kwargs["tasks"]["output_format"], "fbx")
        # The scope resolves inside the run, through the host's object set.
        self.assertEqual(slots.exporter.exported_objects, ["<visible>"])
        sb.progress.assert_called_once_with(
            ui=slots.ui, text="Export: preparing…", busy=True
        )

    def test_the_scope_row_picks_the_hosts_object_set(self):
        defs = {
            "export_visible_objects": {
                "widget_type": "ComboBox",
                "value_method": "currentData",
                "panel": "settings",
            }
        }
        slots, sb = self._export(
            _exporter(task_definitions=defs),
            export_visible_objects=_Widget("selected"),
        )
        kwargs = self._run(slots)
        self.assertEqual(slots.exporter.exported_objects, ["<selected>"])
        self.assertIs(kwargs["export_visible"], False)

    def test_every_export_keeps_the_run_log_and_sets_no_level(self):
        """No log options (2026-10-14): every run keeps the scene's run log and
        leaves the level to the panel's own INFO."""
        slots, sb = self._export()
        kwargs = self._run(slots)
        self.assertIs(kwargs["create_log_file"], True)
        self.assertNotIn("log_level", kwargs)

    def test_a_successful_export_disarms_the_override_and_records_the_names(self):
        slots, sb = self._export()
        self._run(slots)
        self.assertFalse(slots.ui.b009.isChecked(), "the next export is validated")
        self.assertEqual(slots.ui.footer.texts, [("Export complete", "success")])
        slots._recent_dirs_option.record.assert_called_once_with(
            ptk.format_path("/out")
        )
        slots._recent_names_option.record.assert_called_once_with("asset")

    def test_a_failed_export_leaves_the_override_armed(self):
        slots, sb = self._export()
        slots.exporter.export_result = False
        self._run(slots)
        self.assertTrue(slots.ui.b009.isChecked(), "a retry must not need a re-arm")
        self.assertEqual(
            slots.ui.footer.texts, [("Export aborted — see the log", "warning")]
        )

    def test_a_cancelled_export_says_so(self):
        slots, sb = self._export()
        slots.exporter.export_result = False
        slots.exporter.cancel = True
        self._run(slots)
        self.assertEqual(slots.ui.footer.texts, [("Export cancelled", "warning")])

    def test_the_armed_override_skips_the_checks_on_the_run_that_disarms_it(self):
        """Disarming happens AFTER the run -- the run itself still overrides.
        The unarmed control is what makes the armed assertion mean anything."""
        checks = {"check_framerate": {"object_name": "check_framerate"}}
        exporter_class = _exporter(check_definitions=checks)
        control, _ = self._export(exporter_class, check_framerate=_Widget(checked=True))
        control.ui.b009.setChecked(False)
        self.assertIn("check_framerate", self._run(control)["tasks"])

        armed, _ = self._export(exporter_class, check_framerate=_Widget(checked=True))
        self.assertNotIn("check_framerate", self._run(armed)["tasks"])
        self.assertFalse(armed.ui.b009.isChecked())


class TestSceneExporterPanelUi(unittest.TestCase):
    """The ``.ui``: the controls the panel reads."""

    @classmethod
    def setUpClass(cls):
        root = ET.parse(UI_PATH).getroot()
        cls.widgets = {w.get("name"): w for w in root.iter("widget")}

    def test_every_widget_the_panel_uses_exists(self):
        for name in (
            "header",
            "txt000",
            "txt001",
            "cmb007",
            "cmb008",
            "cmb001",
            "cmb002",
            "b000",
            "b009",
            "output_grp",
            "txt003",
            "footer",
        ):
            self.assertIn(name, self.widgets, name)

    def test_every_read_and_init_is_a_ui_widget_or_a_runtime_row(self):
        """The structural rule (``test_slot_method_coverage``) with this panel's
        runtime rows: every ``self.ui.<name>`` it reads and every ``<name>_init``
        names a widget its .ui declares, a window attribute, or one of
        ``RUNTIME_WIDGETS`` -- which the .ui must NOT declare (a stale entry
        would excuse a widget the .ui really has)."""
        import ast
        import sys

        root = ET.parse(UI_PATH).getroot()
        declared = {
            node.get("name")
            for tag in ("widget", "layout")
            for node in root.iter(tag)
            if node.get("name")
        }
        runtime = set(SceneExporterSlots.RUNTIME_WIDGETS)
        self.assertEqual(runtime & declared, set())
        path = sys.modules[SceneExporterSlots.__module__].__file__
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        reads = {
            n.attr
            for n in ast.walk(tree)
            if isinstance(n, ast.Attribute)
            and id(n) not in called
            and ast.unparse(n.value) == "self.ui"
        }
        inits = {
            n.name[: -len("_init")]
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.endswith("_init")
        }
        window = {"settings", "state", "sb", "presets"}
        self.assertEqual(sorted(reads - declared - runtime - window), [])
        self.assertEqual(sorted(inits - declared - runtime), [])

    def test_override_checks_is_a_toggle(self):
        prop = self.widgets["b009"].find("property[@name='checkable']")
        self.assertIsNotNone(prop)
        self.assertEqual(prop.findtext("bool"), "true")

    def test_the_row_combos_are_widget_combos(self):
        for name in ("cmb001", "cmb002", "cmb008"):
            self.assertEqual(self.widgets[name].get("class"), "WidgetComboBox", name)
        self.assertEqual(self.widgets["txt003"].get("class"), "QTextBrowser")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestSceneExporterPanelInMaya(unittest.TestCase):
    """The panel over the real ``mtk.SceneExporter`` and a real scene (the
    widgets stay stand-ins, set to what each case reads). The panel's real
    logger, its widget redirect patched out."""

    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)
        self.temp_dir = tempfile.mkdtemp(prefix="scene_exporter_panel_")
        logger = SceneExporterSlots.logger
        self.addCleanup(logger.setLevel, logger.level)
        for name in ("set_text_handler", "setup_logging_redirect", "hide_logger_name"):
            patcher = mock.patch.object(logger, name)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _panel(self):
        slots, sb, ui = _panel(tk=self.mtk)
        return slots, sb

    def _preview(self, pattern, output_format="fbx"):
        slots, sb = self._panel()
        slots.sb = types.SimpleNamespace(tooltip=ptk.TooltipFormat)
        slots.ui = types.SimpleNamespace(
            txt000=_Widget(self.temp_dir),
            txt001=_Widget(pattern),
            cmb004=_Widget(output_format),
        )
        return slots

    def test_an_export_through_the_panel_writes_the_file(self):
        self.cmds.polyCube(name="panelExportCube")
        slots, sb = self._panel()
        slots.ui = _export_ui(
            txt000=_Widget(self.temp_dir),
            txt001=_Widget("panel_export"),
            cmb000=_Widget(None),
        )
        slots.b000()
        self.assertEqual(slots.ui.footer.texts, [("Export complete", "success")])
        self.assertTrue(
            os.path.isfile(os.path.join(self.temp_dir, "panel_export.fbx")),
            os.listdir(self.temp_dir),
        )
        self.assertFalse(slots.ui.b009.isChecked(), "a shipped export disarms")

    def test_the_field_tooltip_previews_the_path_the_export_would_write(self):
        """The hover resolves through the same call as the write, so the two
        cannot drift -- and QUIETLY: it renders the diagnostics itself, and a
        hover must not file a warning per mouse-over."""
        self.cmds.file(rename=os.path.join(self.temp_dir, "test_scene.ma"))
        slots = self._preview("WIP_*_{nope}")
        with self.assertLogs(slots.logger, level="WARNING") as caught:
            slots.logger.warning("only this one")  # assertLogs needs a record
            html = slots.output_name_preview()
        self.assertEqual(len(caught.records), 1)
        self.assertIn(">*</td>", html)
        for token in slots.exporter.NAME_TOKENS:
            self.assertIn("{" + token + "}", html)
        self.assertIn("unknown", html)  # {nope} is flagged, not silently kept
        self.assertIn(os.path.join(self.temp_dir, "WIP_test_scene_{nope}.fbx"), html)

    def test_the_preview_writes_line_is_the_file_the_export_writes(self):
        """The regex on {scene}, the resolved counter and every file the format
        ships -- the "writes" line names exactly what the next export writes."""
        self.cmds.file(rename=os.path.join(self.temp_dir, "test_scene.ma"))
        open(os.path.join(self.temp_dir, "prod_scene_v004.glb"), "w").close()
        slots = self._preview("{scene:test_->prod_}_v{n:03d}", output_format="fbx_glb")
        html = slots.output_name_preview()
        self.assertIn(
            os.path.join(self.temp_dir, "prod_scene_v005.fbx") + " + .glb", html
        )
        self.assertNotIn("unknown", html)

    def test_a_failed_check_reads_its_label_from_mayas_rows(self):
        slots, sb = self._panel()
        sb.message_box.return_value = "Override"
        self.assertEqual(
            slots.decide_check_failure("check_path_length", ["too long"], []),
            ptk.TaskFactory.CHECK_OVERRIDE,
        )
        # Maya's row label, not the name made legible ("Path Length").
        self.assertIn("Max Path Length", sb.message_box.call_args.args[0])

    def test_the_viewer_gets_every_shipped_carrier_decoded(self):
        """A referenced module's ``NS:data_export`` included; never the
        private data_internal records; a view creates nothing."""
        DataNodes = self.mtk.DataNodes
        slots, sb = self._panel()
        slots._show_data_node()
        self.assertEqual(sb.data_view_dialog.call_args.args[0], {})
        self.assertFalse(self.cmds.objExists(DataNodes.EXPORT))

        DataNodes.write(ptk.Scope.DELIVERABLE, "probe_channel", '{"a": [1, 2]}')
        DataNodes.write(ptk.Scope.PRIVATE, "private_probe", "internal-only")
        self.cmds.namespace(add="MODULE")
        module = self.cmds.createNode("transform", name="MODULE:data_export")
        self.cmds.addAttr(module, longName="module_channel", dataType="string")
        self.cmds.setAttr(f"{module}.module_channel", '{"b": 3}', type="string")
        slots._show_data_node()
        call = sb.data_view_dialog.call_args
        self.assertEqual(
            call.args[0],
            {
                "|data_export": {"probe_channel": {"a": [1, 2]}},
                "|MODULE:data_export": {"module_channel": {"b": 3}},
            },
        )
        self.assertTrue(call.kwargs["save_path"].endswith("_data_export.json"))

    def test_the_rows_build_from_mayas_definitions(self):
        """Group captions in definition order, settings-tagged rows left to the
        Settings combo, captions on the row (not repeated in the option text),
        and the Textures group's gate row first."""
        slots, sb = self._panel()
        definitions = slots.exporter.task_manager.task_definitions
        checks = slots.exporter.task_manager.check_definitions
        _record_builders(slots)
        rows = slots._definition_rows(definitions)
        labels = [label for _w, label in rows]
        self.assertEqual(
            [w.attrs["title"] for w, _l in rows if isinstance(w, _Separator)],
            ["Materials", "Textures", "Animation", "Hierarchy"],
        )
        self.assertNotIn("export_visible_objects", labels)  # settings-tagged
        by_label = {label: w for w, label in rows}
        self.assertEqual(by_label["smart_bake"].attrs["setObjectName"], "smart_bake")
        self.assertEqual(
            by_label["optimize_textures"].attrs["set_row_label"], "Optimize Textures"
        )
        start = labels.index("Textures")
        self.assertEqual(
            labels[start : start + 5],
            [
                "Textures",
                "texture_write_back",
                "convert_textures",
                "optimize_textures",
                "texture_file_type",
            ],
        )
        check_rows = slots._definition_rows(checks)
        self.assertEqual(
            [w.attrs["title"] for w, _l in check_rows if isinstance(w, _Separator)][-1],
            "Deliverable (after the write)",
        )
        # The registry-derived combos persist by value through the factory.
        for key in ("texture_file_type", "optimize_textures"):
            self.assertEqual(by_label[key].attrs.get("restore_by"), "text", key)

    def test_the_settings_layout_covers_every_settings_tagged_definition(self):
        """A task tagged ``panel: settings`` leaves the Tasks popup -- so it
        must have a slot in ``_SETTINGS_LAYOUT`` or it renders nowhere; and
        every layout name resolves to a widget spec or a definition."""
        slots, sb = self._panel()
        defs = slots.exporter.task_manager.task_definitions
        laid_out = {
            n for _g, names in SceneExporterSlots._SETTINGS_LAYOUT for n in names
        }
        tagged = {n for n, p in defs.items() if p.get("panel") == "settings"}
        self.assertEqual(tagged - laid_out, set())
        for name in laid_out:
            self.assertTrue(
                name in SceneExporterSlots._SETTINGS_WIDGETS or name in defs, name
            )

    def test_a_preset_asking_for_a_retired_check_row_names_the_fix(self):
        """The released default for the pair retired 2026-10-19 -- the check
        row on, its fix off -- would lose the check without a word; picking
        such a preset names the fix to turn on (pythontk's notes over Maya's
        rows)."""
        slots, sb = self._panel()
        stored = {"snap_keys_to_frame": False, "check_floating_point_keys": True}
        sb.loaded_ui.scene_exporter.presets.read.return_value = stored
        combo = TestSceneExporterPanelExportPreset._Selector(["released"])
        slots.ui = sb.loaded_ui.scene_exporter
        slots.cmb007_init(combo)
        with self.assertLogs(slots.logger, level="WARNING") as caught:
            combo.activated.emit(0)
        said = "\n".join(caught.output)
        for expected in ("'released'", "Floating Point Keys", "Snap Keys To Frame"):
            self.assertIn(expected, said)

    def test_the_runtime_rows_are_rows_maya_builds(self):
        """Each name the panel reads or initializes outside its .ui is a row
        Maya's definitions (or the panel's UI-only Settings rows) build."""
        slots, sb = self._panel()
        defs = slots.exporter.task_manager.task_definitions
        built = set(SceneExporterSlots._SETTINGS_WIDGETS)
        built |= {spec.get("object_name", name) for name, spec in defs.items()}
        self.assertEqual(set(SceneExporterSlots.RUNTIME_WIDGETS) - built, set())

    def test_a_note_link_opens_the_panel_it_names(self):
        from qtpy import QtCore

        slots, sb = self._panel()
        slots._on_log_link_clicked(QtCore.QUrl("action://show?ui=shots"))
        sb.handlers.marking_menu.show.assert_called_once_with("shots")


if __name__ == "__main__":
    unittest.main()
