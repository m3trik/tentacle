# !/usr/bin/python
# coding=utf-8
"""Panel tests for the shared Shot Manifest tool, in Blender's handler.

Needs **Qt, not bpy**: loads ``ui/tools/shot_manifest.ui`` and wires
``ShotManifestSlots`` through a real (offscreen) Qt / Switchboard /
BlenderUiHandler stack with tentacle's shared roots registered, so the panel
reaches Blender through blendertk as its ``tk``. None of the controller's build
path touches Blender -- ``ShotStore.active()`` falls back to an
in-memory store, detection degrades to no-regions (``_active_scene`` returns
``None`` headless), and the mapping combo reads the shipped built-in templates.
Proves the ``.ui`` compiles, the controller builds (CSV widgets, header/mapping
menus, store binding, footer action-button relocation), and the mapping combo
is populated -- plus the controller's own rules (store events, re-apply
reporting, template migration, the playhead).

The functional engine behaviour (CSV -> shots + native fades + VSE audio +
assess, which needs a real scene) is blendertk's ``test_shot_manifest.py``
under the Blender harness.
"""

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")

HERE = os.path.dirname(os.path.abspath(__file__))
# blendertk is no install of the workspace Python: its repo goes on the path.
_BLENDERTK = os.path.join(os.path.dirname(os.path.dirname(HERE)), "blendertk")
if os.path.isdir(_BLENDERTK) and _BLENDERTK not in sys.path:
    sys.path.insert(0, _BLENDERTK)

try:
    from qtpy import QtWidgets
except Exception:  # pragma: no cover - Qt absent
    QtWidgets = None

if QtWidgets is not None:
    # Keep the panel's settings off the developer's live uitk stores.
    from uitk.testing import TestSandbox

    TestSandbox.activate()


@unittest.skipIf(QtWidgets is None, "Qt not available (Blender headless Python)")
class TestShotManifestPanelLoads(unittest.TestCase):
    """The Shot Manifest panel loads through the real discovery + compile path."""

    @classmethod
    def setUpClass(cls):
        import pythontk as ptk
        from blendertk import ShotStore

        # The panel's store is pure here, whatever host runs the suite (an
        # --in-maya run resolves Maya's, which would write that scene and open
        # its undo chunks); the host, its source and the prefs folder go back.
        cls._store_state = (
            ShotStore._host,
            ShotStore._host_source,
            ShotStore._prefs_dir_override,
        )
        ShotStore.set_host(ptk.PureShotsHost())
        # Isolate cross-scene prefs + class singleton so the load can't touch real config.
        cls._prefs_tmp = tempfile.mkdtemp(prefix="btk_manifest_panel_")
        ShotStore._prefs_dir_override = cls._prefs_tmp
        ShotStore.clear_active()

        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        from uitk import Switchboard
        from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler

        from tentacle.tcl import Tcl

        cls.sb = Switchboard()
        cls.handler = BlenderUiHandler(switchboard=cls.sb)
        # A process singleton: in a run that built it earlier (another panel
        # module) it keeps ITS switchboard, which is the one holding the UIs.
        cls.sb = cls.handler.sb
        Tcl.register_shared(cls.sb)
        cls.ui = cls.handler.get("shot_manifest")
        for _ in range(5):
            cls.app.processEvents()

    @classmethod
    def tearDownClass(cls):
        from blendertk import ShotStore

        # The panel lives on in the process's one handler: its store and
        # invalidation followers must not reach the next module's stores.
        ctrl = getattr(getattr(cls.ui, "slots", None), "controller", None)
        if ctrl is not None:
            ctrl.remove_callbacks()
        ShotStore.clear_active()
        (
            ShotStore._host,
            ShotStore._host_source,
            ShotStore._prefs_dir_override,
        ) = cls._store_state

    def test_ui_loads(self):
        self.assertIsNotNone(self.ui, "shot_manifest UI failed to load")

    def test_a_build_never_builds_a_closed_shots_panel(self):
        """Bug: every Build / Assess read ``loaded_ui.shots``, which BUILDS the
        Shots panel -- a hidden window and a controller following the store
        (the test_shots_panel failures after this module: its controller was
        that one, left on a store the next module dropped) -- and
        ``slot_instances`` (a NamespaceHandler, not a dict) never answered, so
        an open panel was never asked to refresh. Fixed: 2026-10-31"""
        from unittest import mock

        class _Loaded:
            def peek(self, name):
                return None

            def __getattr__(self, name):
                raise AssertionError(f"built the {name} panel")

        class _Registry:  # slot_instances: peek, never a resolve
            def __init__(self, items):
                self._items = items

            def peek(self, name, default=None):
                return self._items.get(name, default)

        ctrl = self.ui.slots.controller
        shots = mock.MagicMock()
        with mock.patch.object(ctrl, "sb") as sb:
            sb.loaded_ui = _Loaded()
            sb.slot_instances = _Registry({})
            ctrl._sync_detection_widgets()  # nothing open: nothing to do
            sb.slot_instances = _Registry({"shots": shots})
            ctrl._sync_detection_widgets()
        shots.controller.refresh_state.assert_called_once_with()

    def test_teardown_survives_a_timer_already_deleted(self):
        """Bug: the panel's ``ui.destroyed`` teardown (``remove_callbacks``)
        stopped a re-assess timer whose C++ object was gone -- "Internal C++
        object (PySide6.QtCore.QTimer) already deleted" at the end of a run.
        Fixed: 2026-10-31"""
        from qtpy import QtCore

        ctrl = self.ui.slots.controller
        self.addCleanup(setattr, ctrl, "_reassess_timer", ctrl._reassess_timer)
        ctrl._reassess_soon()
        timer = ctrl._reassess_timer
        timer.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(timer, QtCore.QEvent.DeferredDelete)
        ctrl._stop_reassess_timer()  # remove_callbacks' stop: no RuntimeError
        self.assertIsNone(ctrl._reassess_timer)
        ctrl._reassess_soon()  # a later edit builds a fresh one
        self.assertTrue(ctrl._reassess_timer.isActive())
        ctrl._reassess_timer.stop()

    def test_resolves_to_slots_class(self):
        self.assertEqual(type(self.ui.slots).__name__, "ShotManifestSlots")

    def test_controller_built(self):
        ctrl = getattr(self.ui.slots, "controller", None)
        self.assertIsNotNone(ctrl)
        self.assertEqual(type(ctrl).__name__, "ShotManifestController")

    def test_static_widgets_exist(self):
        expected = [
            "header",
            "footer",
            "txt_csv_path",
            "tbl_steps",
            "b002",
            "b003",
        ]
        missing = [w for w in expected if not hasattr(self.ui, w)]
        self.assertEqual(missing, [])

    def test_export_sits_before_assess_and_opens_its_preview(self):
        """Export (2026-10-10, in place of the header menu's Copy Asset Names)
        sits in the footer before Assess and Build; it has no option menu --
        a click opens a live preview whose rows set the options (2026-10-11)."""
        from unittest import mock

        footer, ctrl = self.ui.footer, self.ui.slots.controller

        def place(widget):
            while widget.parentWidget() is not footer:
                widget = widget.parentWidget()
            return footer.main_layout.indexOf(widget)

        self.assertLess(place(self.ui.b004), place(self.ui.b002))
        self.assertLess(place(self.ui.b002), place(self.ui.b003))
        self.assertIsNone(getattr(self.ui.b004, "_option_box_manager", None))
        self.assertIsNone(getattr(self.ui, "btn_copy_asset_names", None))
        with mock.patch.object(ctrl, "export") as export:
            self.ui.b004.click()
        export.assert_called_once_with()

    def test_header_menu_widgets_exist(self):
        """The controller's _setup_header_menu builds the option-box actions,
        which uitk registers on the ui by objectName; the view row (Select ...
        Show) is the .ui's, and the CSV mapping has its own popup on the
        build sheet field."""
        missing = [
            name
            for name in (
                "btn_manifest_colors",
                "btn_audio_clips",
                "btn_render_effects",
                "btn_settings",
                "cmb_select",
                "cmb_expand",
                "cmb_collapse",
                "cmb_hide",
                "cmb_show",
            )
            if getattr(self.ui, name, None) is None
        ]
        self.assertEqual(missing, [])
        ctrl = self.ui.slots.controller
        menu = ctrl._mapping_menu
        self.assertIsNot(menu, self.ui.header.menu)
        self.assertIs(
            menu.findChild(QtWidgets.QComboBox, "cmb_csv_mapping"), ctrl._cmb_mapping
        )
        for gone in ("btn_expand_missing", "btn_expand_extra", "chk_hide_missing"):
            self.assertIsNone(
                self.ui.header.menu.findChild(QtWidgets.QWidget, gone), gone
            )

    def test_render_effects_entry_opens_its_panel(self):
        """The header's Render Effects entry opens that panel the way Audio
        Clips and Shots open theirs -- through the host's panel registry, so
        the window is the one tentacle's own menus show."""
        from unittest import mock

        ctrl = self.ui.slots.controller
        with mock.patch.object(ctrl, "sb") as sb:
            self.ui.btn_render_effects.released.emit()
        sb.handlers.marking_menu.show.assert_called_once_with("render_effects")

    def test_mapping_combo_populated(self):
        """The mapping combo lists the shipped built-in templates ('(none)' + default…)."""
        cmb = self.ui.slots.controller._cmb_mapping
        self.assertIsNotNone(cmb)
        data = [cmb.itemData(i) for i in range(cmb.count())]
        self.assertIn(None, data, f"expected a '(none)' entry: {data}")
        self.assertIn(
            "default", data, f"expected the built-in 'default' mapping: {data}"
        )

    def test_tbl_steps_headers(self):
        """The tree carries the unified 6-column layout."""
        from tentacle.slots.tools._shot_manifest.manifest_data import HEADERS

        self.assertIsNotNone(self.ui.tbl_steps)
        # populate_table sets header labels; before first populate the column
        # count may be default — assert the constant is the 6-col contract.
        self.assertEqual(len(HEADERS), 6)
        self.assertEqual(HEADERS[0], "Step")

    def test_template_options_render_and_apply(self):
        """The template declares its settings: the default's options appear as
        rows in its popup, and acting on one changes the template in
        effect -- no option is hard-coded in the panel."""
        ctrl = self.ui.slots.controller
        ctrl._apply_mapping("default", persist=False)
        menu = ctrl._mapping_menu
        find = lambda name: menu.findChild(QtWidgets.QWidget, name)  # noqa: E731
        for name in ("opt_step_ids", "opt_audio", "opt_fill_missing_assets"):
            self.assertIsNotNone(find(name), name)

        self.addCleanup(ctrl._apply_mapping, "default", False)  # runs second
        self.addCleanup(ctrl._settings.setValue, "mapping_options/default", "")
        fill, ids = find("opt_fill_missing_assets"), find("opt_step_ids")
        fill.setChecked(True)
        ids.setCurrentIndex(ids.findData("numbered"))

        self.assertTrue(ctrl._active_mapping.get("fill_missing_assets"))
        self.assertIn("step_pattern", ctrl._active_mapping["columns"])
        # Saved per template: a rebuild shows the values just chosen.
        ctrl._build_option_rows()
        self.assertTrue(find("opt_fill_missing_assets").isChecked())

    def test_a_sheets_options_are_the_scenes_a_new_sheet_takes_the_users(self):
        """Bug: a sheet's template options were kept per user, so a scene
        reopened on its sheet read it another way than it was built.
        Fixed: 2026-10-12 (maintainer) -- per sheet, on the scene; the user's
        own only seed a sheet the scene never read (mirror of mayatk's
        ``TestTheSheetsOptionsLiveOnTheScene``)."""
        import pythontk as ptk
        from blendertk import ShotStore

        ctrl = self.ui.slots.controller
        ShotStore.clear_active()
        store = ShotStore.active()
        self.addCleanup(ShotStore.clear_active)
        self.addCleanup(setattr, ctrl, "_store", ctrl._store)
        ctrl._store = store
        ctrl._apply_mapping("default", persist=False)
        self.addCleanup(ctrl._apply_mapping, "default", False)  # runs second
        self.addCleanup(ctrl._settings.setValue, "mapping_options/default", "")
        ctrl._settings.setValue("mapping_options/default", "")

        def names():
            return [o.name for o in ctrl._steps[0].objects]

        with ptk.TempArtifacts(prefix="btk_sheet_options") as tmp:
            sheets = []
            for name in ("sheet.csv", "other.csv"):
                path = os.path.join(tmp.dir_path(), name)
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(
                        "Step,Step Contents,Asset Names\nA01.),Red Door fades in,\n"
                    )
                sheets.append(path)
            sheet, other = sheets
            self.assertTrue(ctrl._load_csv(sheet))
            self.assertEqual(names(), ["Red_Door"])
            ctrl._on_option_changed("object_case", "upper")
            self.assertEqual(
                store.manifest_options[sheet]["values"]["object_case"], "upper"
            )
            ctrl._settings.setValue("mapping_options/default", "")  # reset since
            self.assertTrue(ctrl._load_csv(sheet))
            self.assertEqual(names(), ["RED_DOOR"], "read as the scene reads it")
            self.assertTrue(ctrl._load_csv(other))
            self.assertEqual(names(), ["Red_Door"], "a new sheet: the user's own")

    SHEET_CSV = "Step,Step Contents,Asset Names\nA01.),Red Door fades in,\n"

    def _sheet_options_case(self):
        """The controller on a fresh scene store, the default template and no
        options of the user's, a sheet beside a scratch folder: ``(ctrl,
        store, sheet, folder)``.  What the cases below change is put back."""
        import pythontk as ptk
        from blendertk import ShotStore

        ctrl = self.ui.slots.controller
        ShotStore.clear_active()
        store = ShotStore.active()
        self.addCleanup(ShotStore.clear_active)
        for attr in ("_store", "_csv_path", "_source", "_sheet_values"):
            self.addCleanup(setattr, ctrl, attr, getattr(ctrl, attr))
        ctrl._store = store
        field = ctrl.ui.txt_csv_path
        self.addCleanup(field.setText, field.text())
        ctrl._apply_mapping("default", persist=False)
        self.addCleanup(ctrl._apply_mapping, "default", False)  # runs late
        self.addCleanup(ctrl._settings.setValue, "mapping_options/default", "")
        ctrl._settings.setValue("mapping_options/default", "")
        tmp = ptk.TempArtifacts("btk_sheet_options", policy="scoped")
        self.addCleanup(tmp.cleanup)
        folder = tmp.dir_path()
        sheet = os.path.join(folder, "sheet.csv")
        with open(sheet, "w", encoding="utf-8", newline="") as fh:
            fh.write(self.SHEET_CSV)
        return ctrl, store, sheet, folder

    @staticmethod
    def _user(ctrl, values):
        """The user's own options for the default template."""
        import json

        ctrl._settings.setValue("mapping_options/default", json.dumps(values))

    def _open(self, ctrl, sheet):
        """The panel opening on *sheet*: the default template, read with the
        user's options as they are now (mayatk's fresh controller)."""
        ctrl._apply_mapping("default", persist=False)
        self.assertTrue(ctrl._load_csv(sheet))

    @staticmethod
    def _other_sheet(ctrl, folder, text):
        """A second sheet beside the first, browsed to as the user would."""
        path = os.path.join(folder, "other.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        ctrl.ui.txt_csv_path.setText(path)  # the field holds it
        return path

    def test_a_sheet_the_scene_never_read_takes_the_users_template(self):
        """Bug: a template switched in for one sheet's record stayed current,
        so the next sheet -- one the scene had never read -- was read with it,
        not with the user's own (mirror of mayatk's).
        Fixed: 2026-10-12"""
        import shutil
        import pythontk as ptk
        from pythontk.core_utils.engines.shots.manifest import mapping

        ctrl, store, sheet, folder = self._sheet_options_case()
        templates = os.path.join(folder, "templates")
        os.makedirs(templates)
        default = os.path.join(os.path.dirname(mapping.__file__), "default.json")
        for name in ("mine", "theirs"):
            shutil.copy(default, os.path.join(templates, f"{name}.json"))
        self.addCleanup(setattr, ctrl, "_mapping_dir", ctrl._mapping_dir)
        ctrl._mapping_dir = templates
        ctrl._apply_mapping("mine", persist=False)
        ptk.ManifestEdits.set_sheet_options(store, sheet, "theirs", {})
        self.assertTrue(ctrl._load_csv(sheet))
        self.assertEqual(ctrl._mapping_name, "theirs", "precondition: its record")

        self.assertTrue(ctrl._load_csv(self._other_sheet(ctrl, folder, self.SHEET_CSV)))
        self.assertEqual(ctrl._mapping_name, "mine")

    def test_a_sheet_that_fails_to_load_leaves_the_shown_sheets_record(self):
        """Bug: a sheet that read no step was refused, but its own options
        stayed adopted, so a Build then recorded them on the sheet still
        shown (Object Case upper -> As written) (mirror of mayatk's).
        Fixed: 2026-10-12"""
        ctrl, store, sheet, folder = self._sheet_options_case()
        self._user(ctrl, {"object_case": "upper"})
        self._open(ctrl, sheet)
        # What a Build records on the sheet it read (Build itself needs bpy).
        ctrl._record_sheet_options(store)
        self._user(ctrl, {})  # the user's own since: As written
        other = self._other_sheet(ctrl, folder, "Step,Step Contents,Asset Names\n")
        self.assertFalse(ctrl._load_csv(other), "precondition: no step read")
        ctrl._record_sheet_options(store)
        self.assertEqual(
            store.manifest_options[sheet]["values"].get("object_case"), "upper"
        )

    def test_an_option_set_after_a_sheet_read_no_step_reads_that_sheet(self):
        """Bug: the field said to set the sheet's Step IDs, but the option
        change read the sheet shown before again and recorded it there
        (mirror of mayatk's).
        Fixed: 2026-10-12"""
        ctrl, store, sheet, folder = self._sheet_options_case()
        self._user(ctrl, {"step_ids": "classic"})  # reads the A01.) sheet shown
        self._open(ctrl, sheet)
        other = self._other_sheet(
            ctrl, folder, "Step,Step Contents,Asset Names\nIN_01,Red Door fades in,\n"
        )
        self.assertFalse(ctrl._load_csv(other), "precondition: no step read")
        ctrl._on_option_changed("step_ids", "numbered")
        self.assertEqual(ctrl._csv_path, other)
        self.assertEqual([s.step_id for s in ctrl._steps], ["IN_01"])
        self.assertNotIn(sheet, store.manifest_options, "not that sheet's")

    def test_the_preview_follows_a_shot_moved_in_the_sequencer(self):
        """Bug: an open export preview kept the frames it opened with when a
        shot moved (``_refresh_timing``) or a range was typed
        (``_refresh_ranges``) (mirror of mayatk's).
        Fixed: 2026-10-12"""
        from pythontk import BuilderObject, BuilderStep

        ctrl = self.ui.slots.controller
        store = self._fresh_store(ctrl)
        self.addCleanup(
            ctrl._settings.setValue,
            "export_options",
            ctrl._settings.value("export_options"),
        )
        ctrl._settings.setValue("export_options", "")
        self.addCleanup(setattr, ctrl, "_active_mapping", ctrl._active_mapping)
        ctrl._active_mapping = None
        store.define_shot("A01_1", 0, 111, objects=["KEYS"], metadata={"step": "A01"})
        store.define_shot("A02", 241, 321, objects=["obj_A02"])
        steps = [
            BuilderStep(sid, "A", "Section A", "", [BuilderObject(f"obj_{sid}")])
            for sid in ("A01", "A02", "A03")
        ]
        ctrl._load_data(steps, csv_path="X:/sheet.csv")
        for _ in range(3):
            self.app.processEvents()
        ctrl._set_export_option("columns", ["step", "start"])
        ctrl.export()
        preview = ctrl._export_preview
        self.addCleanup(preview.close)
        self.assertIn("A02,241", preview.text_edit.toPlainText())
        shot = store.shot_by_name("A02")
        store.update_shot(shot.shot_id, start=251, end=331)
        ctrl._refresh_timing()
        self.assertIn("A02,251", preview.text_edit.toPlainText())

    def test_object_name_pickers_offer_the_strutils_cases_and_rules(self):
        """The case and legal-name pickers list exactly what pythontk's
        StrUtils applies, and picking one reshapes the names the sheet's
        prose gives."""
        import pythontk as ptk

        ctrl = self.ui.slots.controller
        ctrl._apply_mapping("default", persist=False)
        self.addCleanup(ctrl._apply_mapping, "default", False)  # runs second
        self.addCleanup(ctrl._settings.setValue, "mapping_options/default", "")
        find = lambda name: ctrl._mapping_menu.findChild(QtWidgets.QWidget, name)  # noqa: E731
        case, rule = find("opt_object_case"), find("opt_object_name_rule")
        self.assertEqual(
            [case.itemData(i) for i in range(case.count())],
            ["keep", *ptk.StrUtils.CASES],
        )
        self.assertEqual(
            sorted(rule.itemData(i) for i in range(rule.count())),
            sorted(["keep", *ptk.StrUtils.NAME_RULES]),
        )
        case.setCurrentIndex(case.findData("lower"))
        self.assertEqual(ctrl._active_mapping["columns"]["object_case"], "lower")

    def test_empty_source_shows_the_scenes_shots_with_descriptions(self):
        """No build sheet: the table lists the store's own shots, descriptions
        included, instead of re-detecting blank steps from animation."""
        from blendertk import ShotStore
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_DESC

        ctrl = self.ui.slots.controller
        ShotStore.clear_active()
        store = ShotStore.active()
        store.define_shot(
            "intro", 1, 40, objects=["Arm"], description="Arm reaches out"
        )
        self.addCleanup(ShotStore.clear_active)
        self.addCleanup(setattr, ctrl, "_store", ctrl._store)
        ctrl._store = store
        self.ui.txt_csv_path.setText("")
        ctrl._populate_from_source()

        self.assertEqual(ctrl._source, "scene")
        tree = self.ui.tbl_steps
        self.assertEqual(tree.topLevelItemCount(), 1)
        self.assertEqual(tree.topLevelItem(0).text(COL_DESC), "Arm reaches out")
        self.assertTrue(self.ui.txt_csv_path.isEnabled())

    def _populate_one_step(self, ctrl):
        """Load one synthetic step into the tree (shared by the presenter tests)."""
        from pythontk import BuilderStep, BuilderObject

        ctrl._steps = [
            BuilderStep(
                step_id="A01",
                section="A",
                section_title="Test",
                description="step one",
                objects=[BuilderObject(name="Obj1", behaviors=[])],
            )
        ]
        ctrl._populate_table()

    def test_additional_object_row_matches_column_count(self):
        """Additional-object rows mirror the mayatk reference shape (6 texts, EMPTY
        Behaviors cell — table_presenter.py:705 uses ["", "", display, "", "", ""];
        a stray 'scene' tag landed in the Behaviors column here)."""
        from pythontk.core_utils.engines.shots.manifest.manifest_model import (
            StepStatus,
        )
        from tentacle.slots.tools._shot_manifest.manifest_data import (
            HEADERS,
            COL_DESC,
        )

        ctrl = self.ui.slots.controller
        self._populate_one_step(ctrl)
        ctrl._apply_assessment(
            [
                StepStatus(
                    step_id="A01",
                    built=True,
                    objects=[],
                    additional_objects=["ExtraObj"],
                )
            ]
        )
        tree = self.ui.tbl_steps
        parent = tree.topLevelItem(0)
        extra = next(
            (
                parent.child(j)
                for j in range(parent.childCount())
                if parent.child(j).text(COL_DESC) == "ExtraObj"
            ),
            None,
        )
        self.assertIsNotNone(extra, "additional-object row not created")
        texts = [extra.text(c) for c in range(len(HEADERS))]
        self.assertEqual(texts, ["", "", "ExtraObj", "", "", ""])

    def test_expand_missing_uses_logger_and_footer(self):
        """expand_missing reports through the logger + footer exactly as the mayatk
        reference (table_presenter.py:764-765) — never bare print()."""
        import io
        from contextlib import redirect_stdout
        from pythontk.core_utils.engines.shots.manifest.manifest_model import (
            StepStatus,
        )

        ctrl = self.ui.slots.controller
        self._populate_one_step(ctrl)
        ctrl._last_results = [StepStatus(step_id="A01", built=False, objects=[])]
        footers = []
        orig_footer = ctrl._set_footer
        ctrl._set_footer = lambda *a, **kw: footers.append(a[0] if a else "")
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                ctrl.expand_missing()
        finally:
            ctrl._set_footer = orig_footer
            ctrl._last_results = []
        self.assertEqual(buf.getvalue(), "", "expand_missing must not print to stdout")
        self.assertTrue(
            any("expanded" in m for m in footers),
            f"expected the mayatk-style footer feedback, got {footers}",
        )

    # -- controller behaviour (mirrors mayatk's test_shot_manifest) ---------

    def _fresh_store(self, ctrl, listen: bool = False):
        """A fresh active store for *ctrl* (``listen``: bound to it, as the
        panel is to the scene's), restored to a fresh one afterwards."""
        from blendertk import ShotStore

        def restore(first_shown=ctrl._first_shown, steps=list(ctrl._steps)):
            ctrl._unbind_store_listener()
            ShotStore.clear_active()
            ctrl._store = None
            ctrl._bind_store_listener()
            ctrl._first_shown = first_shown
            ctrl._load_data(steps)

        self.addCleanup(restore)
        ctrl._unbind_store_listener()
        ShotStore.clear_active()
        # Built, not ``active()``: under Blender ``active()`` re-attaches the
        # scene record, so one test's shots persisted into the next (a
        # second ``define_shot('intro')`` refused, a table one row long).
        store = ShotStore()
        ShotStore.set_active(store)
        ctrl._store = store
        if listen:
            ctrl._bind_store_listener()
        return store

    def _footers(self, ctrl) -> list:
        """Every footer *ctrl* sets from here on."""
        from unittest import mock

        footers = []
        patcher = mock.patch.object(
            ctrl, "_set_footer", side_effect=lambda text, **_kw: footers.append(text)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return footers

    def test_a_recipe_change_keeps_the_detected_steps_and_typed_ranges(self):
        """Bug: ``update_effect_recipe`` fires the same bare ``SettingsChanged``
        a detection setting does, so a Render Effects spinbox tick re-ran
        ``detect()`` -- the steps regenerated, a typed range gone.
        Fixed: 2026-10-04
        """
        from unittest import mock
        from pythontk import BuilderStep, StepStatus

        ctrl = self.ui.slots.controller
        store = self._fresh_store(ctrl, listen=True)
        regions = [{"name": "Shot 1", "start": 10.0, "end": 50.0, "objects": ["Cube"]}]
        steps, ranges = BuilderStep.from_detection(regions)
        ctrl._load_data(steps, ranges=dict(ranges))  # detect mode
        ctrl._first_shown = True
        ctrl._user_ranges["Shot 1"] = (12.0, 60.0)  # typed by the user
        ctrl._last_results = [StepStatus(step_id="Shot 1", built=False)]
        ctrl._update_build_button()
        self.assertTrue(self.ui.b003.isEnabled())  # that Assess wants a Build

        with (
            mock.patch.object(ctrl, "_detect_regions", return_value=regions) as det,
            mock.patch.object(ctrl, "_reassess_soon") as soon,
        ):
            store.update_effect_recipe(fade_frames=20)
            soon.assert_called_once_with()  # ...run again once settled (mayatk)
            det.assert_not_called()
            self.assertEqual(ctrl._steps, steps)
            self.assertEqual(ctrl._user_ranges["Shot 1"], (12.0, 60.0))
            # ...but the last Assess judged keys the recipe no longer makes.
            self.assertEqual(ctrl._last_results, [])
            self.assertFalse(self.ui.b003.isEnabled())

            store.detection_threshold = 9.0  # a detection input does re-detect
            store.notify_settings_changed()
            det.assert_called_once()

    def test_shots_deleted_elsewhere_empty_the_table_without_asking(self):
        """Bug: the scene's shots all deleted in another panel, the store event
        reloaded them, found none and fell through to the interactive
        ``detect()`` -- whose selected-keys mode pops a modal "No keys
        selected" for an action taken elsewhere.
        Fixed: 2026-10-04
        """
        from unittest import mock
        from pythontk import ShotRemoved

        ctrl = self.ui.slots.controller
        store = self._fresh_store(ctrl)
        store.define_shot("intro", 1, 40, objects=["Arm"])
        store.detection_mode = "skip_zero"  # a selected-keys mode
        ctrl._first_shown = True
        ctrl._load_scene_shots()
        for shot in list(store.shots):
            store.remove_shot(shot.shot_id)
        footers = self._footers(ctrl)
        with (
            mock.patch.object(ctrl, "_detect_regions", return_value=[]) as det,
            mock.patch.object(ctrl, "sb") as sb,
        ):
            ctrl._on_store_event(ShotRemoved(shot_id=1))
        sb.message_box.assert_not_called()
        det.assert_not_called()
        self.assertEqual(ctrl._steps, [])
        self.assertEqual(ctrl._source, "scene")  # still following the store
        self.assertIn("no shots", footers[-1].lower())

    def test_a_bound_edit_made_elsewhere_reaches_a_sheets_built_row(self):
        """A bound edit written straight onto the shot (no ShotUpdated) is
        announced by its ``scene_edit`` (``ShotsEdited``), and a sheet's built
        row follows it (mayatk 2026-10-07: "the manifest doesn't refresh
        properly on many actions")."""
        from pythontk import BuilderObject, BuilderStep
        from tentacle.slots.tools._shot_manifest.manifest_data import (
            COL_END,
            COL_START,
        )

        ctrl = self.ui.slots.controller
        store = self._fresh_store(ctrl, listen=True)
        store.define_shot("A01", 10, 50, metadata={"step": "A01"})
        step = BuilderStep("A01", "A", "t", "", [BuilderObject("Arm")])
        ctrl._load_data([step], csv_path="X:/sheet.csv")
        ctrl._first_shown = True
        tree = ctrl.ui.tbl_steps

        def cells():
            row = tree.topLevelItem(0)
            return row.text(COL_START), row.text(COL_END)

        self.assertEqual(cells(), ("10", "50"), "a built row shows its shot")
        with store.scene_edit("Trim"):
            store.shot_by_name("A01").end = 40.0
            store.mark_dirty()
        self.assertEqual(cells(), ("10", "40"))

    def test_a_shot_deleted_or_added_elsewhere_reshapes_a_sheet(self):
        """A sheet follows the pairing, not only the ranges: a deleted shot's
        step reads unbuilt, an added shot is listed "not in doc" and its range
        follows (mayatk mirror)."""
        from pythontk import BuilderObject, BuilderStep
        from tentacle.slots.tools._shot_manifest.manifest_data import (
            COL_END,
            COL_START,
        )

        ctrl = self.ui.slots.controller
        store = self._fresh_store(ctrl, listen=True)
        store.define_shot("A01", 10, 50, metadata={"step": "A01"})
        step = BuilderStep("A01", "A", "t", "", [BuilderObject("Arm")])
        ctrl._load_data([step], csv_path="X:/sheet.csv")
        ctrl._first_shown = True
        tree = ctrl.ui.tbl_steps

        def cells(name):
            for i in range(tree.topLevelItemCount()):
                row = tree.topLevelItem(i)
                if row.text(0) == name:
                    return row.text(COL_START), row.text(COL_END)
            return None

        store.remove_shot(store.shot_by_name("A01").shot_id)
        self.assertEqual(cells("A01"), ("", ""))
        extra = store.define_shot("Extra", 300, 340)
        self.assertEqual(cells("Extra"), ("300", "340"))
        with store.scene_edit("Trim"):
            extra.end = 330.0
            store.mark_dirty()
        self.assertEqual(cells("Extra"), ("300", "330"))

    def test_build_options_reach_the_engine(self):
        """Edits' Keep / Rebuild Hand-Edited Shots (Keep by default) and the
        Key / Marker / Off choice per behavior (Off by default; mayatk
        mirror), kept per user."""
        from blendertk.anim_utils.shots.shot_manifest.behaviors import Behaviors

        ctrl = self.ui.slots.controller
        self.addCleanup(ctrl._settings.clear, "rebuild_edited")
        self.addCleanup(ctrl._settings.clear, "keyed_behaviors")
        self.addCleanup(ctrl._settings.clear, "marked_behaviors")
        every = frozenset(Behaviors.list_behaviors())
        edits = ctrl._editor._cmb_edits
        self.assertEqual(edits.currentData(), "keep")
        modes = ctrl._behavior_modes
        self.assertEqual(sorted(modes), sorted(every))
        self.assertEqual({c.currentData() for c in modes.values()}, {"off"})
        edits.setCurrentIndex(edits.findData("rebuild"))
        modes["highlight"].setCurrentIndex(modes["highlight"].findData("key"))
        modes["fade_in"].setCurrentIndex(modes["fade_in"].findData("marker"))
        try:
            mani = ctrl._manifest()
            self.assertTrue(mani.rebuild_edited)
            self.assertEqual(mani.disabled_behaviors, every - {"highlight", "fade_in"})
            self.assertEqual(mani.marked_behaviors, frozenset({"fade_in"}))
        finally:
            edits.setCurrentIndex(edits.findData("keep"))
            for name in ("highlight", "fade_in"):
                modes[name].setCurrentIndex(modes[name].findData("off"))
        mani = ctrl._manifest()
        self.assertFalse(mani.rebuild_edited)
        self.assertEqual(mani.disabled_behaviors, every)
        self.assertEqual(mani.marked_behaviors, frozenset())

    def test_a_reapply_that_keys_nothing_says_so_and_the_focused_key_raises(self):
        """Bug: ``_reapply_behavior`` ignored ``reapply_object``'s ``False``
        and re-assessed as if it had worked; the focused Key's ``apply`` then
        reported "Re-applied ..." whatever happened.
        Fixed: 2026-10-04
        """
        from unittest import mock
        from pythontk import BuilderObject, BuilderStep

        ctrl = self.ui.slots.controller
        store = self._fresh_store(ctrl)
        store.define_shot("A01", 1, 40)
        ctrl._load_data(
            [BuilderStep(step_id="A01", section="A", section_title="", description="")]
        )
        obj = BuilderObject(name="ghost", behaviors=["fade_in"])
        builder = mock.MagicMock()
        builder.reapply_object.return_value = False
        footers = self._footers(ctrl)
        with (
            mock.patch.object(ctrl, "_manifest", return_value=builder),
            mock.patch.object(ctrl, "assess") as assess,
            mock.patch.object(ctrl, "sb") as sb,
        ):
            self.assertIs(ctrl._reapply_behavior("A01", obj), False)
            assess.assert_not_called()
            self.assertIn("'ghost' is not in the scene", footers[-1])

            ctrl._open_effect("A01", obj, "opacity")
            apply = sb.get_slots_instance.return_value.focus.call_args.kwargs["apply"]
            with self.assertRaises(RuntimeError):
                apply()
            builder.reapply_object.return_value = True
            self.assertEqual(apply(), "Re-applied ghost's behaviors in A01.")
            assess.assert_called_once_with(skip_key_check=True)

    def test_set_range_to_current_frame_keeps_the_subframe(self):
        """Bug: read ``scene.frame_current`` -- an int -- though the playhead
        keeps sub-frames (mayatk's ``currentTime`` keeps the fraction).
        Fixed: 2026-10-04
        """
        import types
        from unittest import mock
        from pythontk import BuilderStep

        ctrl = self.ui.slots.controller
        self.addCleanup(setattr, ctrl, "_user_ranges", dict(ctrl._user_ranges))
        self.addCleanup(setattr, ctrl, "_steps", list(ctrl._steps))
        ctrl._steps = [
            BuilderStep(step_id="A01", section="A", section_title="", description="")
        ]
        scene = types.SimpleNamespace(frame_current=12, frame_current_final=12.5)
        # A real module, not a namespace: an import hook reads its __name__
        # (shiboken's does inside Maya, at the host's ``import bpy``).
        bpy = types.ModuleType("bpy")
        bpy.context = types.SimpleNamespace(scene=scene)
        with (
            mock.patch.dict(sys.modules, {"bpy": bpy}),
            mock.patch.object(ctrl, "_refresh_ranges"),
        ):
            ctrl._set_range_to_current_frame(None, "A01")
        self.assertEqual(ctrl._user_ranges["A01"], (12.5, None))


@unittest.skipIf(QtWidgets is None, "Qt not available (Blender headless Python)")
class TestShotManifestLocalEdits(unittest.TestCase):
    """Local Edits, acted out on the real panel: double-click a cell, type,
    press Return; trigger the context menu's own actions.  The sheet is never
    changed, the edits live on the scene's store, and Build follows them."""

    SHEET = "local_edits_sheet.csv"  # a source key only: nothing reads it

    @classmethod
    def setUpClass(cls):
        TestShotManifestPanelLoads.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        TestShotManifestPanelLoads.tearDownClass.__func__(cls)

    @staticmethod
    def _sheet():
        from pythontk import BuilderStep, BuilderObject

        return [
            BuilderStep(
                "A01",
                "A",
                "Access",
                "Open the door " * 12,
                [
                    BuilderObject("door", behaviors=["fade_in"]),
                    BuilderObject("bolt01"),
                ],
            ),
            BuilderStep("A02", "A", "Access", "Unhook", [BuilderObject("latch")]),
        ]

    def setUp(self):
        from blendertk import ShotStore

        self.ctrl = ctrl = self.ui.slots.controller
        self.tree = self.ui.tbl_steps
        self.addCleanup(ShotStore.clear_active)
        self.addCleanup(setattr, ctrl, "_store", ctrl._store)
        ShotStore.clear_active()
        self.store = ShotStore()
        ShotStore.set_active(self.store)
        ctrl._store = self.store
        self.addCleanup(self._mode, "keep")
        self.footers = []
        from unittest import mock

        patcher = mock.patch.object(
            ctrl,
            "_set_footer",
            side_effect=lambda text, **_kw: self.footers.append(text),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _mode(self, mode: str):
        """Pick the header menu's Edits *mode* (``keep``, ``rebuild``,
        ``compare``)."""
        cmb = self.ctrl._editor._cmb_edits
        cmb.setCurrentIndex(cmb.findData(mode))
        self._settle()

    def _load(self, on: bool = True):
        """Load the sheet; *on* False compares to the original sheet (the
        header menu's Edits > Compare to Original Sheet)."""
        self._mode("keep" if on else "compare")
        self.ctrl._load_data(self._sheet(), csv_path=self.SHEET)
        self._settle()

    def _settle(self):
        for _ in range(5):
            self.app.processEvents()

    def _row(self, step_id):
        from qtpy.QtCore import Qt

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            data = item.data(0, Qt.UserRole)
            if getattr(data, "step_id", None) == step_id:
                return item
        return None

    def _child(self, step_id, name):
        from qtpy.QtCore import Qt

        row = self._row(step_id)
        for j in range(row.childCount()):
            if getattr(row.child(j).data(0, Qt.UserRole), "name", None) == name:
                return row.child(j)
        return None

    def _type_into(self, item, column, text):
        """Double-click the cell (the tree's own signal: the panel is never
        shown here), type *text* over it, press Return."""
        from qtpy.QtCore import Qt
        from qtpy.QtTest import QTest

        self.tree.itemDoubleClicked.emit(item, column)
        self._settle()
        editor = self.tree.indexWidget(self.tree.indexFromItem(item, column))
        self.assertIsNotNone(editor, "the double-click opened no editor")
        editor.setText(text)
        QTest.keyClick(editor, Qt.Key_Return)
        self._settle()
        return editor

    def _actions(self, item, selected=()):
        """The Local Edits actions the row's context menu offers, by text."""
        from qtpy.QtWidgets import QMenu

        menu = QMenu(self.tree)
        self.addCleanup(menu.deleteLater)
        self.ctrl._editor.add_menu_actions(menu, item, list(selected))
        return {act.text(): act for act in menu.actions()}

    def _trigger(self, item, text, selected=()):
        """Trigger the row's menu action *text* (``"Menu > Action"`` for a
        submenu's), the menus held while it runs: a submenu action's wrapper
        dies with the wrapper of the menu it came from."""
        from qtpy.QtWidgets import QMenu

        menu = QMenu(self.tree)
        self.addCleanup(menu.deleteLater)
        self.ctrl._editor.add_menu_actions(menu, item, list(selected))
        top, _, leaf = text.partition(" > ")
        actions = menu.actions()
        act = next((a for a in actions if a.text() == top), None)
        self.assertIsNotNone(act, f"no '{top}' in the menu")
        if leaf:
            sub_menu = act.menu()
            subs = sub_menu.actions()
            act = next((a for a in subs if a.text() == leaf), None)
            self.assertIsNotNone(act, f"no '{leaf}' under '{top}'")
        act.trigger()
        self._settle()

    # ---- object rows: the menu acts on every selected one ---------------------

    def _object_menu(self, item, pick):
        """Right-click *item*; return the object actions' texts and run *pick*
        (a text) as if chosen."""
        from unittest import mock
        from qtpy.QtWidgets import QMenu

        seen = []

        def chosen(menu, *_args):
            actions = menu.actions()
            seen.extend(a.text() for a in actions)
            action = next((a for a in actions if a.text() == pick), None)
            if action is not None:
                action.trigger()  # as the real exec_ does
            return action

        with mock.patch.object(self.tree, "itemAt", return_value=item):
            with mock.patch.object(QMenu, "exec_", chosen):
                self.ctrl._show_item_menu(self.tree.visualItemRect(item).center())
        return seen

    def test_object_actions_take_every_selected_object_row(self):
        """Regression: the actions took the clicked row only -- selecting the
        objects a name several nodes share was one row at a time."""
        from unittest import mock
        from qtpy.QtWidgets import QApplication

        self._load(on=False)
        door, bolt = self._child("A01", "door"), self._child("A01", "bolt01")
        latch = self._child("A02", "latch")
        revealed = []
        # What the panel puts on the clipboard, read back in this process: the
        # OS one is shared with the desktop (and reads '' inside a GUI Maya).
        from _host import use_memory_clipboard

        use_memory_clipboard(self)
        with mock.patch.object(self.ctrl, "_show_in_outliner", revealed.append):
            self.tree.clearSelection()
            for item in (door, bolt, latch):
                item.setSelected(True)
            texts = self._object_menu(door, "Show 3 Objects in Outliner")
            self.assertIn("Copy 3 Names to Clipboard", texts)
            self.assertEqual(revealed, [["door", "bolt01", "latch"]])
            self._object_menu(bolt, "Copy 3 Names to Clipboard")
            self.assertEqual(QApplication.clipboard().text(), "door\nbolt01\nlatch")
            # A row outside the selection acts on itself alone.
            door.setSelected(False)
            self._object_menu(door, "Show 'door' in Outliner")
            self.assertEqual(revealed[-1], ["door"])

    # ---- the option ----------------------------------------------------------

    def test_in_force_by_default_and_the_original_view_edits_nothing(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_STEP

        self.assertTrue(self.ctrl._editor.enabled)
        cmb = self.ctrl._editor._cmb_edits
        self.assertEqual(cmb.currentData(), "keep")
        self.assertEqual(
            [cmb.itemText(i) for i in range(cmb.count())],
            [
                "Keep All Edits",
                "Rebuild Hand-Edited Shots",
                "Compare to Original Sheet",
            ],
        )
        self._load(on=False)
        self.assertIs(self.ctrl._steps, self.ctrl._sheet_steps)
        row = self._row("A01")
        self.assertTrue(self.ctrl._editor.begin_edit(row, COL_STEP))
        self.assertIsNone(self.ctrl._editor._pending, "no editor opened")
        self.assertEqual(self._actions(row), {})
        self.assertFalse(self.ctrl._editor._btn_reset.isEnabled())

    def test_the_original_view_shows_the_sheet_and_back_restores_every_edit(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_STEP

        self._load()
        self._type_into(self._row("A01"), COL_STEP, "Door_Open")
        self.assertEqual(self._row("A01").text(COL_STEP), "Door_Open")
        self.assertTrue(self.ctrl._editor._btn_reset.isEnabled())

        self._mode("compare")
        self.assertEqual(self._row("A01").text(COL_STEP), "A01")
        self.assertEqual(self.ctrl._steps, self._sheet())
        self.assertFalse(self.ctrl._editor._btn_reset.isEnabled())
        self.assertFalse(self.ui.b003.isEnabled(), "Build is off in the view")

        self._mode("keep")
        self.assertEqual(self._row("A01").text(COL_STEP), "Door_Open")

    def test_edits_live_on_the_scene_and_survive_a_reload(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_DESC

        self._load()
        self._type_into(self._child("A01", "bolt01"), COL_DESC, "bolt_01")
        saved = self.store.manifest_edits[self.SHEET]
        self.assertEqual(saved["objects"], {"A01": {"bolt01": {"name": "bolt_01"}}})
        self.ctrl._load_data(self._sheet(), csv_path=self.SHEET)  # re-parsed
        self.assertEqual(
            [o.name for o in self.ctrl._steps[0].objects], ["door", "bolt_01"]
        )
        # Another sheet has its own layer.
        self.ctrl._load_data(self._sheet(), csv_path="other.csv")
        self.assertEqual(self.ctrl._steps, self._sheet())

    def test_a_moved_sheet_keeps_its_edits_and_the_next_edit_re_keys_them(self):
        """Bug: the layer was found by the sheet's exact path, so a sheet
        moved or opened through another mount lost its edits silently.
        Fixed: 2026-10-11 -- the path, else the one layer of that file name;
        a save re-keys it to where the sheet is now."""
        from tentacle.slots.tools._shot_manifest.manifest_data import (
            COL_DESC,
            COL_STEP,
        )

        self._load()
        self._type_into(self._child("A01", "bolt01"), COL_DESC, "bolt_01")
        moved = "C:/moved/to/" + self.SHEET
        self.ctrl._load_data(self._sheet(), csv_path=moved)
        self.assertEqual(
            [o.name for o in self.ctrl._steps[0].objects], ["door", "bolt_01"]
        )
        self._type_into(self._row("A02"), COL_STEP, "Unhook")
        self.assertEqual(list(self.store.manifest_edits), [moved])
        self.assertEqual(
            self.store.manifest_edits[moved]["objects"],
            {"A01": {"bolt01": {"name": "bolt_01"}}},
        )

    def test_reset_drops_every_edit_and_the_scenes_record(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_STEP

        self._load()
        self._type_into(self._row("A02"), COL_STEP, "Unhook")
        self.ctrl._editor.reset(confirm=False)
        self._settle()
        self.assertNotIn(self.SHEET, self.store.manifest_edits)
        self.assertEqual(self._row("A02").text(COL_STEP), "A02")
        self.assertFalse(self.ctrl._editor._btn_reset.isEnabled())

    # ---- cells ---------------------------------------------------------------

    def test_a_renamed_built_step_builds_into_the_same_shot(self):
        import pythontk as ptk
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_STEP

        ptk.ShotManifest(self.store).update(self._sheet(), initial_shot_length=50)
        self._load()
        self._type_into(self._row("A01"), COL_STEP, "Door_Open")
        row = self._row("A01")
        self.assertTrue(row.font(COL_STEP).italic())
        self.assertIn("Sheet: A01", row.toolTip(COL_STEP))
        self.assertIn("Build renames its shot", self.footers[-1])
        ptk.ShotManifest(self.store).update(self.ctrl._steps, remove_missing=False)
        self.assertEqual(
            [s.name for s in self.store.sorted_shots()], ["Door_Open", "A02"]
        )
        self.assertEqual(self.store.shot_by_name("Door_Open").metadata["step"], "A01")

    def test_a_name_another_step_has_is_refused(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_STEP

        self._load()
        self._type_into(self._row("A01"), COL_STEP, "a02")
        self.assertFalse(self.ctrl._editor.edits.has_edits)
        self.assertIn("already names step", self.footers[-1])
        self.assertEqual(self._row("A01").text(COL_STEP), "A01")

    def test_an_object_rename_edits_the_full_name_and_marks_the_sheets(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_DESC

        self._load()
        editor = self._type_into(self._child("A01", "door"), COL_DESC, "red_door")
        self.assertIsNotNone(editor)
        child = self._child("A01", "red_door")
        self.assertTrue(child.font(COL_DESC).italic())
        self.assertIn("Sheet: door", child.toolTip(COL_DESC))
        self.assertEqual(self.ctrl._steps[0].objects[0].behaviors, ["fade_in"])

    def test_a_long_description_shows_in_full_in_its_tooltip(self):
        self._load()
        self.assertTrue(self.tree.elided_tooltips)
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_DESC

        index = self.tree.indexFromItem(self._row("A01"), COL_DESC)
        self.tree.header().resizeSection(COL_DESC, 80)
        self.assertTrue(self.tree.is_elided(index))
        self.assertIn(
            "Open the door Open the door", self.tree.item_tooltip(index, None)
        )

    # ---- the context menu ----------------------------------------------------

    def test_add_a_step_name_it_and_move_objects_into_it(self):
        import pythontk as ptk
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_STEP

        self._load()
        self._trigger(self._row("A02"), "Add Step After 'A02'")
        new = self.ctrl._steps[-1]
        self.assertEqual(new.step_id, "NEW_STEP")
        # The new row opens on its name: type it.
        editor = self.tree.indexWidget(
            self.tree.indexFromItem(self._row(new.step_id), COL_STEP)
        )
        self.assertIsNotNone(editor)
        editor.setText("Inspect")
        from qtpy.QtCore import Qt
        from qtpy.QtTest import QTest

        QTest.keyClick(editor, Qt.Key_Return)
        self._settle()
        self._trigger(self._child("A01", "door"), "Move 'door' To > Inspect")
        self.assertEqual(
            [(s.shot_name, [o.name for o in s.objects]) for s in self.ctrl._steps],
            [("A01", ["bolt01"]), ("A02", ["latch"]), ("Inspect", ["door"])],
        )
        self.assertIn(
            "Moved here from 'A01'", self._child("NEW_STEP", "door").toolTip(2)
        )
        actions = ptk.ShotManifest(self.store).update(
            self.ctrl._steps, initial_shot_length=50
        )
        self.assertEqual(actions["NEW_STEP"], "created")
        self.assertEqual(self.store.shot_by_name("Inspect").objects, ["door"])
        # Removing the added step puts the door back where the sheet has it.
        self._trigger(self._row("NEW_STEP"), "Remove 'Inspect'")
        self.assertEqual(
            [o.name for o in self.ctrl._steps[0].objects], ["door", "bolt01"]
        )

    def test_hide_and_show_objects_and_unbuilt_steps(self):
        import pythontk as ptk

        self._load()
        self._trigger(self._child("A01", "bolt01"), "Hide 'bolt01'")
        self.assertEqual([o.name for o in self.ctrl._steps[0].objects], ["door"])
        self._trigger(self._row("A01"), "Show Hidden Objects (1) > bolt01")
        self.assertEqual(
            [o.name for o in self.ctrl._steps[0].objects], ["door", "bolt01"]
        )

        self._trigger(self._row("A02"), "Hide > 'A02'")
        self.assertEqual([s.step_id for s in self.ctrl._steps], ["A01"])
        self._trigger(self._row("A01"), "Show Hidden Steps (1) > A02")
        self.assertEqual([s.step_id for s in self.ctrl._steps], ["A01", "A02"])

        # A built step stays: Build never removes a shot.
        ptk.ShotManifest(self.store).update(self.ctrl._steps, initial_shot_length=50)
        self.assertFalse(self._hide_actions(self._row("A01"))["'A01'"].isEnabled())

    def _hide_actions(self, item, selected=()):
        """The row's Hide flyout, by text -- its action held while the flyout
        is read: a menu taken off a dropped action's wrapper is dead."""
        self._hide_action = self._actions(item, selected)["Hide"]
        hide = self._hide_action.menu()
        return {act.text(): act for act in hide.actions() if act.text()}

    def test_the_hide_flyout_hides_the_selection_or_the_section(self):
        """2026-10-11: "a flyout from hide shot x that exposes more shot hide
        options" -- the step, the selected steps, its section."""
        import pythontk as ptk

        self._load()
        self.assertEqual(
            list(self._hide_actions(self._row("A01"), ["A01", "A02"])),
            [
                "'A01'",
                "2 Selected Steps",
                "Section 'A: Access'",
                "Steps Without a Shot",
            ],
        )
        self._trigger(self._row("A01"), "Hide > 2 Selected Steps", ["A01", "A02"])
        self.assertEqual(self.ctrl._steps, [])
        self.ctrl._editor.reset(confirm=False)
        self._settle()

        # A built step of the section stays; the flyout says so and hides the rest.
        ptk.ShotManifest(self.store).update(
            self.ctrl._steps[:1], initial_shot_length=50
        )
        self.ctrl._redraw()
        self._trigger(self._row("A02"), "Hide > Section 'A: Access' (1 not built)")
        self.assertEqual([s.step_id for s in self.ctrl._steps], ["A01"])

    def test_the_flyouts_steps_without_a_shot_is_the_view_rows(self):
        """The row's Hide flyout and the view row's Hide / Show turn the same
        view on and off."""
        self.addCleanup(self.ctrl._set_hide_missing, False)
        self._load()
        self._trigger(self._row("A01"), "Hide > Steps Without a Shot")
        self.assertTrue(self.ctrl._hide_missing)
        self.assertTrue(
            self._hide_actions(self._row("A01"))["Steps Without a Shot"].isChecked()
        )
        show = self.ui.cmb_show
        show.before_popup_shown.emit()
        index = next(
            i for i in range(show.count()) if show.itemText(i) == "Steps Without a Shot"
        )
        self.assertTrue(show.model().item(index).isEnabled())
        show.setCurrentIndex(index)
        self.assertFalse(self.ctrl._hide_missing)
        self.assertEqual(show.currentIndex(), -1, "its title again")

    def test_an_edit_runs_a_showing_assessment_again(self):
        """Bug: a Local Edit -- a hide above all -- left the last Assess up,
        judged over the old steps, and marked Build due whatever it said: the
        user re-ran Assess after every hide ("once I hide shots, I have to
        re-assess every time").
        Fixed: 2026-10-11"""
        from unittest import mock
        from pythontk import StepStatus

        self._load()
        with mock.patch.object(self.ctrl, "_reassess_soon") as soon:
            self._trigger(self._row("A02"), "Hide > 'A02'")
            soon.assert_not_called()  # none showing: nothing to keep current
            self.ctrl._last_results = [StepStatus(step_id="A01", built=False)]
            self._trigger(self._row("A01"), "Show Hidden Steps (1) > A02")
        soon.assert_called_once_with(note="Showed 1 step(s).")

    def test_a_reload_keeps_a_showing_assessment_and_a_scene_swap_drops_it(self):
        from unittest import mock
        from pythontk import StepStatus

        self._load()
        self.ctrl._last_results = [StepStatus(step_id="A01", built=False)]
        with mock.patch.object(self.ctrl, "_reassess_soon") as soon:
            self.ctrl._load_data(self._sheet(), csv_path=self.SHEET, footer="Read.")
        soon.assert_called_once_with(note="Read.")
        self.ctrl._last_results = [StepStatus(step_id="A01", built=False)]
        with (
            mock.patch.object(self.ctrl, "_reassess_soon") as soon,
            mock.patch.object(self.ctrl, "_open_scene_source"),
        ):
            self.ctrl._on_scene_changed()
        self.assertEqual(self.ctrl._last_results, [])
        soon.assert_not_called()

    def test_a_reassessment_owed_to_the_old_scene_is_dropped(self):
        """Bug: a re-assessment pending (or owed to a hidden panel) when the
        scene changed ran on the next scene, which opens unassessed (mirror
        of mayatk's).
        Fixed: 2026-10-12"""
        self.addCleanup(setattr, self.ctrl, "_first_shown", self.ctrl._first_shown)
        self.ctrl._first_shown = False  # no repopulate: only the drop is under test
        self.ctrl._reassess_soon(note="Hid 2 step(s).")
        self.ctrl._reassess_on_show = True

        self.ctrl._on_scene_changed()

        self.assertFalse(self.ctrl._reassess_timer.isActive(), "timer still pending")
        self.assertFalse(self.ctrl._reassess_on_show)
        self.assertEqual(self.ctrl._reassess_note, "")

    def test_a_reloaded_sheet_shows_an_added_steps_shot_range(self):
        """Bug: ``_load_csv`` seeded the built steps' Start/End from the
        sheet's steps alone, so a built step Local Edits added showed an
        auto-filled range instead of its shot's.
        Fixed: 2026-10-06"""
        from pythontk import ManifestEdits

        sheet = os.path.join(HERE, "temp_tests", "local_edits_reload.csv")
        os.makedirs(os.path.dirname(sheet), exist_ok=True)
        with open(sheet, "w", encoding="utf-8") as f:
            f.write(
                "SECTION A: Access\n"
                "Step,Step Contents,Asset Names\n"
                "A01.),Open the door,door\n"
                "A02.),Unhook,latch\n"
            )
        self.addCleanup(os.remove, sheet)
        edits = ManifestEdits()
        new = edits.add_step("A01")
        self.store.manifest_edits[sheet] = edits.to_dict()
        self.store.define_shot("A01", 1, 20, metadata={"step": "A01"})
        self.store.define_shot("Inspect", 30, 45, metadata={"step": new})
        self._mode("keep")
        self.assertTrue(self.ctrl._load_csv(sheet))
        self.assertEqual([s.step_id for s in self.ctrl._steps], ["A01", new, "A02"])
        self.assertEqual(self.ctrl._user_ranges[new], (30, 45))
        self.assertEqual(self.ctrl._user_ranges["A01"], (1, 20))
        self.assertNotIn("A02", self.ctrl._user_ranges)

    def test_rename_all_and_revert(self):
        from unittest import mock
        from pythontk import BuilderObject

        self._load()
        self.ctrl._sheet_steps[1].objects.append(BuilderObject("door"))
        self.ctrl._editor.refresh()
        with mock.patch.object(self.ctrl.sb, "input_dialog", return_value="red_door"):
            self._trigger(self._child("A02", "door"), "Rename All 'door'…")
        self.assertEqual(
            [[o.name for o in s.objects] for s in self.ctrl._steps],
            [["red_door", "bolt01"], ["latch", "red_door"]],
        )
        self._trigger(self._child("A01", "red_door"), "Revert 'red_door'")
        self.assertEqual(
            [[o.name for o in s.objects] for s in self.ctrl._steps],
            [["door", "bolt01"], ["latch", "red_door"]],
        )

    def test_behavior_ticks_are_edits_while_they_are_in_force(self):
        from unittest import mock

        self._load(on=False)
        obj = self.ctrl._steps[0].objects[0]
        box = mock.Mock(**{"isChecked.return_value": False})
        self.ctrl._on_behaviors_changed(obj, [box], step_id="A01")
        self._settle()
        self.assertEqual(self.ctrl._steps[0].objects[0].behaviors, ["fade_in"])
        self.assertFalse(self.ctrl._editor.edits.has_edits)  # the sheet's view

        self._load()
        obj = self.ctrl._steps[0].objects[0]
        self.ctrl._on_behaviors_changed(obj, [box], step_id="A01")
        self._settle()
        door = self.ctrl._steps[0].objects[0]  # the redrawn table's
        self.assertEqual(door.behaviors, [])
        self.assertEqual(door.sheet, {"behaviors": ["fade_in"]})
        self.assertEqual(
            self.store.manifest_edits[self.SHEET]["objects"]["A01"]["door"],
            {"behaviors": []},
        )
        self.assertEqual(self.ctrl._sheet_steps[0].objects[0].behaviors, ["fade_in"])


@unittest.skipIf(QtWidgets is None, "Qt not available (Blender headless Python)")
class TestShotManifestRowTags(unittest.TestCase):
    """Colour tags on the real panel: the ``.ui``'s tree carries the strip,
    a pick from a step row's context menu is kept on the scene's store under
    the sheet, and the template's ``color_by`` shows under the picks."""

    SHEET = "row_tags_sheet.csv"  # a source key only: nothing reads it

    @classmethod
    def setUpClass(cls):
        TestShotManifestPanelLoads.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        TestShotManifestPanelLoads.tearDownClass.__func__(cls)

    def setUp(self):
        from blendertk import ShotStore

        self.ctrl = ctrl = self.ui.slots.controller
        self.tree = self.ui.tbl_steps
        self.tags = ctrl._row_tags
        self.addCleanup(ShotStore.clear_active)
        self.addCleanup(setattr, ctrl, "_store", ctrl._store)
        self.addCleanup(setattr, ctrl, "_active_mapping", ctrl._active_mapping)
        ShotStore.clear_active()
        self.store = ShotStore()
        ShotStore.set_active(self.store)
        ctrl._store = self.store

    def _load(self):
        from pythontk import BuilderStep

        steps = [
            BuilderStep("A01", "A", "Access", "Open", []),
            BuilderStep("A02", "A", "Access", "Unhook", []),
            BuilderStep("B01", "B", "Repair", "Swap", []),
        ]
        self.ctrl._load_data(steps, csv_path=self.SHEET)
        for _ in range(5):
            self.app.processEvents()
        return [self.tree.topLevelItem(i) for i in range(len(steps))]

    def _pick(self, item, swatch):
        """Right-click step row *item*, click swatch *swatch* (0: clear)."""
        from unittest import mock

        from qtpy.QtCore import Qt
        from qtpy.QtTest import QTest
        from qtpy.QtWidgets import QMenu, QWidgetAction

        def chosen(menu, *_args):
            row = next(
                a.defaultWidget()
                for a in menu.actions()
                if isinstance(a, QWidgetAction)
            )
            QTest.mouseClick(row.swatches[swatch], Qt.LeftButton)
            return None

        with mock.patch.object(self.tree, "itemAt", return_value=item):
            with mock.patch.object(QMenu, "exec_", chosen):
                self.ctrl._show_item_menu(self.tree.visualItemRect(item).center())

    def test_the_trees_strip_is_attached(self):
        from uitk import RowTags

        self.assertIs(RowTags.of(self.tree), self.tags)

    def test_a_pick_is_kept_on_the_store_and_survives_a_reload(self):
        _a01, a02, _b01 = self._load()
        self.tree.clearSelection()
        self._pick(a02, 6)
        self.assertEqual(self.store.manifest_tags, {self.SHEET: {"A02": "tag6"}})
        _a01, a02, _b01 = self._load()
        self.assertEqual(self.tags.shown_tag(a02), "tag6")

    def test_a_closed_item_menu_is_not_kept(self):
        """Bug: every right-click parented a fresh ``QMenu`` to the tree and
        never deleted it, so each menu lived as long as the panel.
        Fixed: 2026-10-09"""
        from qtpy.QtCore import QCoreApplication, QEvent, Qt
        from qtpy.QtWidgets import QMenu

        a01, _a02, _b01 = self._load()
        for swatch in (1, 0):
            self._pick(a01, swatch)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.assertEqual(
            self.tree.findChildren(QMenu, "", Qt.FindDirectChildrenOnly), []
        )

    def test_color_by_section_colours_each_section(self):
        """The next section takes a far hue, never the neighbouring one
        (``Palette.contrast_order``: tag4 after tag1)."""
        self.ctrl._active_mapping = {"color_by": "section"}
        rows = self._load()
        self.assertEqual(
            [self.tags.shown_tag(row) for row in rows], ["tag1", "tag1", "tag4"]
        )


@unittest.skipIf(QtWidgets is None, "Qt not available (Blender headless Python)")
class TestShotManifestUnlistedShots(unittest.TestCase):
    """mayatk's ``TestShotsTheDocDoesNotList`` on the real panel: a shot no
    step pairs with sits where the timeline has it with its members under
    it, joins the manifest from its menu; a section locks; steps with no
    shot hide."""

    SHEET = "unlisted_sheet.csv"  # a source key only: nothing reads it

    @classmethod
    def setUpClass(cls):
        TestShotManifestPanelLoads.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        TestShotManifestPanelLoads.tearDownClass.__func__(cls)

    def setUp(self):
        from blendertk import ShotStore

        self.ctrl = ctrl = self.ui.slots.controller
        self.tree = self.ui.tbl_steps
        self.addCleanup(ShotStore.clear_active)
        self.addCleanup(setattr, ctrl, "_store", ctrl._store)
        self.addCleanup(setattr, ctrl, "_active_mapping", ctrl._active_mapping)
        self.addCleanup(
            ctrl._settings.setValue,
            "hide_missing",
            ctrl._settings.value("hide_missing"),
        )
        ShotStore.clear_active()
        self.store = ShotStore()
        ShotStore.set_active(self.store)
        ctrl._store = self.store
        ctrl._active_mapping = None
        self.store.define_shot(
            "A01_1", 0, 111, objects=["KEYS", "LOCK"], metadata={"step": "A01"}
        )
        self.store.define_shot("A01_2", 121, 231, objects=["LOCK_B"])
        self.store.define_shot("A02", 241, 321, objects=["DOOR"])

    def _load(self, hide_missing=False):
        from pythontk import BuilderStep

        self.ctrl._settings.setValue("hide_missing", hide_missing)
        steps = [
            BuilderStep("A01", "A", "Access", "Unlock", []),
            BuilderStep("A02", "A", "Access", "Open", []),
            BuilderStep("B01", "B", "Repair", "Swap", []),
        ]
        self.ctrl._load_data(steps, csv_path=self.SHEET)
        for _ in range(5):
            self.app.processEvents()

    def _names(self):
        return [
            self.tree.topLevelItem(i).text(0)
            for i in range(self.tree.topLevelItemCount())
        ]

    def _row(self, text):
        return next(
            self.tree.topLevelItem(i)
            for i in range(self.tree.topLevelItemCount())
            if self.tree.topLevelItem(i).text(0) == text
        )

    def _menu(self, item, pick):
        """Right-click *item*, trigger the entry starting with *pick*."""
        from unittest import mock

        from qtpy.QtWidgets import QMenu

        def run(menu, *_args):
            def walk(m):
                for a in m.actions():
                    if a.menu():
                        found = walk(a.menu())
                        if found:
                            return found
                    elif a.text().startswith(pick):
                        return a
                return None

            action = walk(menu)
            self.assertIsNotNone(action, pick)
            action.trigger()

        with mock.patch.object(self.tree, "itemAt", return_value=item):
            with mock.patch.object(QMenu, "exec_", run):
                self.ctrl._show_item_menu(self.tree.visualItemRect(item).center())
        for _ in range(5):
            self.app.processEvents()

    def test_a_split_shot_sits_where_the_timeline_has_it_with_its_members(self):
        self._load()
        self.assertEqual(self._names(), ["A01", "A01_2", "A02", "B01"])
        row = self._row("A01_2")
        self.assertEqual(
            [row.child(j).text(2) for j in range(row.childCount())], ["LOCK_B"]
        )
        a01 = self._row("A01")
        self.assertEqual(
            [a01.child(j).text(2) for j in range(a01.childCount())], ["KEYS", "LOCK"]
        )

    def test_a_split_shot_shows_the_section_of_the_step_it_was_split_from(self):
        """Bug: a split-off shot had no relation to its step: no section in
        its row or its export.  Linked by its ``A01_2`` name
        (``ShotPairing.links``), never paired.
        Fixed: 2026-10-11"""
        from tentacle.slots.tools._shot_manifest.manifest_data import (
            COL_SECTION,
        )

        self._load()
        self.assertEqual(self._row("A01_2").text(COL_SECTION), "A: Access")
        self.assertIn(
            self.store.shot_by_name("A01_2"), self.ctrl._orphan_shots(), "not paired"
        )

    def test_adding_the_shot_makes_it_a_step(self):
        self._load()
        self._menu(self._row("A01_2"), "Add 'A01_2'")
        self.assertEqual(self.store.shot_by_name("A01_2").metadata["step"], "A01_2")
        self.assertTrue(self.ctrl._step_is_built("A01_2"))
        self.assertEqual(self.ctrl._orphan_shots(), [])

    def test_a_section_locks(self):
        self._load()
        self._menu(self._row("A01"), "Lock Section 'A'")
        self.assertTrue(self.store.shot_by_name("A01_1").locked)
        self.assertTrue(self.store.shot_by_name("A02").locked)

    def test_steps_with_no_shot_hide(self):
        self._load(hide_missing=True)
        self.assertEqual(self._names(), ["A01", "A01_2", "A02"])


@unittest.skipIf(QtWidgets is None, "Qt not available (Blender headless Python)")
class TestShotManifestIncrementalPlacement(unittest.TestCase):
    """mayatk's ``TestIncrementalPlacement`` on the real panel: on a built
    timeline Build inserts a new step's shot in sheet order -- after its
    previous step's shot -- and the later shots move out of its way, after
    the user confirms how many move; the table previews where, and keeps
    previewing the timeline as it is.  The Build runs the twin controller
    over blendertk's ``BlenderShotManifest``; with no scene here (no
    ``bpy``) its inserts go through pythontk's bounds-only ``ShotSequencer``
    and the undo step is skipped -- ``test_shot_manifest.py`` moves real keys
    and strips through Blender's, under one undo.

    Bug: Build with Hide Missing Shots off left overlapping, zero-length,
    out-of-order shots (SOL: 37 new shots).
    Fixed: 2026-10-12
    """

    SHEET = "incremental_sheet.csv"  # a source key only: nothing reads it

    @classmethod
    def setUpClass(cls):
        TestShotManifestPanelLoads.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        TestShotManifestPanelLoads.tearDownClass.__func__(cls)

    def setUp(self):
        from unittest import mock

        from blendertk import ShotStore
        from blendertk.anim_utils.shots.shot_manifest.manifest_host import (
            ManifestHost,
        )

        self.ctrl = ctrl = self.ui.slots.controller
        self.tree = self.ui.tbl_steps
        self.addCleanup(ShotStore.clear_active)
        self.addCleanup(setattr, ctrl, "_store", ctrl._store)
        self.addCleanup(setattr, ctrl, "_active_mapping", ctrl._active_mapping)
        self.addCleanup(setattr, ctrl, "_first_shown", ctrl._first_shown)
        self.addCleanup(
            ctrl._settings.setValue,
            "hide_missing",
            ctrl._settings.value("hide_missing"),
        )
        ctrl._settings.setValue("hide_missing", False)
        ShotStore.clear_active()
        self.store = ShotStore()
        ShotStore.set_active(self.store)
        ctrl._store = self.store
        ctrl._active_mapping = None
        self.store.gap = 0.0
        self.store.define_shot("A01", 1, 100, objects=["obj_A01"])
        self.store.define_shot("A02", 100, 200, objects=["obj_A02"])
        self.store.define_shot("A03", 200, 300, objects=["obj_A03"])
        self.footers = []
        import contextlib

        import pythontk as ptk
        from blendertk.anim_utils.shots.shot_manifest._shot_manifest import (
            BlenderShotManifest,
        )

        for target, attr, kwargs in (
            (ManifestHost, "available", {"return_value": True}),  # no bpy here
            (  # Blender's moves keys and strips: no scene here, bounds only
                BlenderShotManifest,
                "_sequencer",
                {"new": lambda mani: ptk.ShotSequencer(store=mani.store)},
            ),
            (  # its undo step needs bpy
                self.store,
                "scene_edit",
                {"new": lambda *_a, **_k: contextlib.nullcontext()},
            ),
            (
                ctrl,
                "_set_footer",
                {"side_effect": lambda text, **_kw: self.footers.append(text)},
            ),
        ):
            patcher = mock.patch.object(target, attr, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.box = mock.patch.object(ctrl.sb, "message_box", return_value="Insert")
        self.message_box = self.box.start()
        self.addCleanup(self.box.stop)

    @staticmethod
    def _steps(*ids):
        from pythontk import BuilderObject, BuilderStep

        return [
            BuilderStep(
                sid, "A", "Access", f"Content for {sid}", [BuilderObject(f"obj_{sid}")]
            )
            for sid in ids
        ]

    def _load(self, *ids):
        self.ctrl._load_data(self._steps(*ids), csv_path=self.SHEET)
        for _ in range(3):
            self.app.processEvents()

    def _build(self, *ids, answer="Insert"):
        self._load(*ids)
        self.message_box.return_value = answer
        self.ctrl.build()

    def _layout(self):
        return [(s.name, s.start, s.end) for s in self.store.sorted_shots()]

    def _row(self, step_id):
        return self.ctrl._step_items([step_id])[0]

    def test_a_new_step_goes_after_its_previous_step_and_the_rest_ripple(self):
        length = self.ctrl._initial_shot_length
        self._build("A01", "A02", "B01", "A03")
        self.assertEqual(
            self._layout(),
            [
                ("A01", 1, 100),
                ("A02", 100, 200),
                ("B01", 200, 200 + length),
                ("A03", 200 + length, 300 + length),
            ],
        )
        self.message_box.assert_called_once()
        self.assertIn("1 existing shot(s)", self.message_box.call_args.args[0])

    def test_consecutive_new_steps_keep_their_sheet_order(self):
        length = self.ctrl._initial_shot_length
        self._build("A01", "B01", "B02", "A02", "A03")
        rows = self._layout()
        self.assertEqual([r[0] for r in rows], ["A01", "B01", "B02", "A02", "A03"])
        for (_a, _s, end), (_b, start, _e) in zip(rows, rows[1:]):
            self.assertLessEqual(end, start, "no overlap")
        self.assertEqual(rows[1][1:], (100, 100 + length))

    def test_a_new_first_step_takes_the_head(self):
        length = self.ctrl._initial_shot_length
        self._build("B01", "A01", "A02", "A03")
        self.assertEqual(
            self._layout()[:2],
            [("B01", 1, 1 + length), ("A01", 1 + length, 100 + length)],
        )

    def test_cancel_moves_nothing(self):
        before = self._layout()
        self._build("A01", "B01", "A02", "A03", answer="Cancel")
        self.assertEqual(self._layout(), before)

    def test_appending_after_the_last_shot_asks_nothing(self):
        self._build("A01", "A02", "A03", "B01")
        self.message_box.assert_not_called()
        self.assertEqual(self._layout()[-1][:2], ("B01", 300))

    def test_the_table_previews_where_build_inserts(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import (
            COL_END,
            COL_START,
        )

        length = self.ctrl._initial_shot_length
        self._load("A01", "A02", "B01", "A03")
        resolved = {r[0]: r for r in self.ctrl._refresh_ranges()}
        self.assertEqual(resolved["B01"], ("B01", 200, 200 + length, False))
        self.assertEqual(self.ctrl._projected, {"B01": "after shot 'A02'"})
        self.ctrl._redraw()
        row = self._row("B01")
        self.assertEqual(
            (row.text(COL_START), row.text(COL_END)), ("200", f"{200 + length:.0f}")
        )
        self.assertIn("after shot 'A02'", row.toolTip(COL_START))

    def test_a_step_whose_shot_was_deleted_is_inserted_not_put_back(self):
        self.ctrl._user_ranges["A02"] = self.ctrl._seeded_ranges["A02"] = (100, 200)
        self.ctrl._user_ranges["A04"] = (900, 950)  # typed
        self.assertEqual(self.ctrl._typed_ranges(), {"A04": (900, 950)})

    def test_after_a_build_the_table_shows_what_was_built(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_START

        length = self.ctrl._initial_shot_length
        self._load("A01", "A02", "B01", "A03")
        self.ctrl._refresh_ranges()
        self.ctrl.build()
        self.assertEqual(self._row("B01").toolTip(COL_START), f"{length:.0f}f")
        self.assertEqual(self._row("A01").toolTip(COL_START), "99f")
        self.assertEqual(self.ctrl._projected, {})

    def test_hidden_steps_mark_no_overlap(self):
        self.ctrl._settings.setValue("hide_missing", True)
        self._load("A01", "A02", "B01", "B02", "A03")
        self.ctrl._refresh_ranges()
        self.assertEqual(self.ctrl._range_issues, {})

    def test_a_shot_resized_elsewhere_moves_the_preview(self):
        from tentacle.slots.tools._shot_manifest.manifest_data import COL_START

        self.ctrl._first_shown = True
        self._load("A01", "A02", "B01", "A03")
        self.ctrl._refresh_ranges()
        self.store.update_shot(self.store.shot_by_name("A02").shot_id, end=250)
        self.ctrl._follow_store()
        self.assertEqual(self._row("B01").text(COL_START), "250")

    def test_a_typed_range_rides_the_inserts_before_it(self):
        """A range typed in the timeline's current frames moves with the
        shots an insert moves (maintainer 2026-10-12)."""
        self.store.gap = 10.0
        self.store.initial_shot_length = 50
        self.store.remove_shot(self.store.shot_by_name("A02").shot_id)
        self.store.update_shot(self.store.shot_by_name("A01").shot_id, start=0)
        self.store.update_shot(
            self.store.shot_by_name("A03").shot_id, start=110, end=210
        )
        self._load("A01", "A02", "A03", "A04")
        self.ctrl._user_ranges["A04"] = (220.0, 270.0)
        resolved = {r[0]: r for r in self.ctrl._refresh_ranges()}
        self.assertEqual(resolved["A04"], ("A04", 280, 330, True))
        self.ctrl.build()
        self.assertEqual(
            self._layout(),
            [("A01", 0, 100), ("A02", 110, 160), ("A03", 170, 270), ("A04", 280, 330)],
        )


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    )
    # Report the tally in the harness's (ok/attempted) form -- without it the
    # suite counts for zero checks in run_tests.py's totals. Skips are neither
    # passes nor failures, so they leave the ratio entirely (a fully skipped
    # suite reports 0/0, exactly what it contributed).
    _attempted = result.testsRun - len(result.skipped)
    _ok = _attempted - len(result.failures) - len(result.errors)
    _tally = f"{_ok}/{_attempted}" if _attempted else "skipped"
    print(f"===RESULT: {'PASS' if result.wasSuccessful() else 'FAIL'}=== ({_tally})")
