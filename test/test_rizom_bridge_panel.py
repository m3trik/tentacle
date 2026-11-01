#!/usr/bin/python
# coding=utf-8
"""The RizomUV Bridge panel's one Slots class (``slots/tools/rizom_bridge.py``).

``RizomBridgeSlots`` sits on ``HostBridge`` (``slots/tools/_app_bridge/``) and
reaches its host only through ``self.tk``: the engine ``RizomUVBridge`` (its preset
folder, the presets and rows the installed RizomUV runs, and ``run_preset`` for
Process), ``BridgeHost`` for the Scope and ``UiUtils.open_editor`` for the UV
Editor. A fake toolkit stands in for ``mtk`` / ``btk`` and records what the panel
asks of it.

A bridge panel builds real Qt rows in its ``__init__``, so the unit cases run the
panel's methods on an instance that was never built (``__new__``), with only the
attributes those methods read. Then the panel loads for real through an offscreen
Switchboard over the fake toolkit (rows follow the preset, the window follows the
rows), and in Maya the same methods drive the real ``mtk``. The engine's own side
is the libraries' (``test_uv_rizom_bridge.py`` in mayatk,
``test_rizom_construction.py`` in blendertk).
"""

import os
import shutil
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots.tools._app_bridge.host_bridge import HostBridge
from tentacle.slots.tools.rizom_bridge import RizomBridgeSlots

UI_PATH = Path(tentacle.__file__).resolve().parent / "ui" / "tools" / "rizom_bridge.ui"


# ---------------------------------------------------------------------------
# The fake toolkit
# ---------------------------------------------------------------------------


class _Log:
    """A bridge logger that keeps what it was told, by level."""

    def __init__(self):
        self.records = []

    def __getattr__(self, level):  # info / warning / error / the redirect hooks
        if level.startswith("__"):
            raise AttributeError(level)
        return lambda msg="", *a, **k: self.records.append((level, str(msg)))

    def said(self, level):
        return [msg for lvl, msg in self.records if lvl == level]


class _Registry:
    """The engine's parameter registry (a ``uitk.bridge.ParamRegistry``)."""

    PARAMS = {"SCOPE": None, "SPACING": None}
    SUPERSESSIONS = ()

    @staticmethod
    def referenced_keys(script_text):
        raise AssertionError("the panel's rows are the engine's, never the raw scan")


class _FakeRizom:
    """The engine surface the panel and its base read."""

    SCRIPT_DIR = Path("scripts")
    APP = types.SimpleNamespace(not_found_message="RizomUV not found. Install it.")

    def __init__(self):
        self.logger = _Log()
        self.rizom_path = "C:/RizomUV/Rizomuv_VS.exe"
        self.ran = None

    @classmethod
    def params_registry(cls):
        return _Registry

    def referenced_keys(self, script_text):
        return {"SPACING"} if "__SPACING__" in script_text else set()

    def list_template_modes(self):
        return [("pack", ""), ("send", "")]

    def run_preset(self, objects, preset, params=None):
        self.ran = (list(objects), preset, params)


def _toolkit(name="mayatk"):
    """``mtk`` / ``btk`` as the panel reaches them: by name, nothing else."""
    return types.SimpleNamespace(
        __name__=name,
        RizomUVBridge=_FakeRizom,
        BridgeHost=mock.MagicMock(name="BridgeHost"),
        UiUtils=mock.MagicMock(name="UiUtils"),
    )


def _stub(tk=None, params=None, preset="pack"):
    """A panel never built, over the attributes its methods read."""
    slots = RizomBridgeSlots.__new__(RizomBridgeSlots)
    slots.sb = mock.MagicMock(name="switchboard")
    slots.sb.tk = tk or _toolkit()
    slots._bridge = _FakeRizom()
    slots._output_dir_edit = None
    slots._selected_template_mode = lambda: (preset, "") if preset else None
    slots.collect_param_values = lambda: dict(params or {})
    slots._refresh_param_enablement = mock.MagicMock(name="_refresh_param_enablement")
    return slots


def _scoped(slots, objects):
    """The host resolves the Scope to *objects*; the closure ships them as-is."""
    host = slots.tk.BridgeHost
    host.resolve_scope.return_value = list(objects)
    host.scope_closure.side_effect = lambda found, params: list(found)
    return host


# ---------------------------------------------------------------------------
# The panel's shape
# ---------------------------------------------------------------------------


class TestRizomBridgeShape(unittest.TestCase):
    def test_one_class_for_both_hosts_on_the_bridge_base(self):
        self.assertEqual(RizomBridgeSlots.__bases__, (HostBridge,))
        self.assertEqual(RizomBridgeSlots.UI_NAME, "rizom_bridge")
        self.assertEqual(RizomBridgeSlots.HELP_SPEC["title"], "RizomUV Bridge")

    def test_lua_presets_and_no_output_dir(self):
        """A round trip goes through a temp FBX the engine owns: no Output Dir."""
        self.assertEqual(RizomBridgeSlots.TEMPLATE_EXTENSION, ".lua")
        self.assertFalse(RizomBridgeSlots.REQUIRE_OUTPUT_DIR)
        self.assertEqual(RizomBridgeSlots.LABEL_MIN_WIDTH, 80)

    def test_the_header_menu_keeps_its_names_and_handlers(self):
        items = {
            name: handler
            for _l, name, _t, handler in RizomBridgeSlots.HEADER_MENU_ITEMS
        }
        self.assertEqual(
            items,
            {
                "btn_open_uv_editor": "open_uv_editor",
                "btn_open_scripts": "open_templates_folder",
                "btn_refresh_scripts": "refresh_templates",
                "btn_clear_log": "clear_log",
            },
        )
        for handler in items.values():
            self.assertTrue(callable(getattr(RizomBridgeSlots, handler)), handler)

    def test_holding_esc_cancels_the_process_button(self):
        """Process runs inside the dispatcher's CancelScope (``@Cancelable``): the
        scope a hidden round trip polls. Without it, Esc held over a stuck run did
        nothing. Moved from mayatk's ``test_uv_rizom_bridge.py`` (2026-10-19)."""
        meta = getattr(RizomBridgeSlots.b000, "_cancelable_meta", None) or {}
        self.assertGreater(meta.get("timeout") or 0, 0)

    def test_the_help_names_the_button_the_ui_shows(self):
        root = ET.parse(UI_PATH).getroot()
        button = root.find(".//widget[@name='b000']/property[@name='text']/string")
        self.assertEqual(button.text, "Process Selected")
        self.assertIn(
            "<b>Process Selected</b>", " ".join(RizomBridgeSlots.HELP_SPEC["steps"])
        )


# ---------------------------------------------------------------------------
# What the panel asks of its host
# ---------------------------------------------------------------------------


class TestRizomBridgeAsksItsHost(unittest.TestCase):
    def test_the_engine_is_the_hosts_rizom_bridge(self):
        slots = _stub()
        self.assertIs(slots.bridge_class, slots.tk.RizomUVBridge)
        self.assertIsInstance(slots.make_bridge(), _FakeRizom)

    def test_the_templates_are_the_engines_lua_presets(self):
        self.assertEqual(_stub().template_dir, _FakeRizom.SCRIPT_DIR)

    def test_the_presets_listed_are_the_ones_the_installed_version_runs(self):
        """The engine leaves out a preset gated above the installed RizomUV."""
        self.assertEqual(_stub().list_template_modes(), [("pack", ""), ("send", "")])

    def test_the_rows_are_the_registrys_gated_by_the_installed_version(self):
        params = _stub().params_module
        self.assertIs(params.PARAMS, _Registry.PARAMS)
        self.assertEqual(params.SUPERSESSIONS, ())
        self.assertEqual(params.referenced_keys("Spacing=__SPACING__"), {"SPACING"})
        self.assertIsNone(getattr(params, "NOT_DECLARED", None))

    def test_presets_stay_in_each_hosts_folder(self):
        for name in ("mayatk", "blendertk"):
            with self.subTest(host=name):
                root = _stub(tk=_toolkit(name)).PRESETS_ROOT
                self.assertEqual(root, Path(name) / "rizom_bridge")

    def test_the_scope_resolves_through_the_host_with_the_engine(self):
        slots = _stub()
        _scoped(slots, ["|pCube1"])
        self.assertEqual(slots.resolve_scope_objects("visible"), ["|pCube1"])
        slots.tk.BridgeHost.resolve_scope.assert_called_once_with(
            "visible", slots._bridge
        )

    def test_the_uv_editor_is_the_hosts(self):
        slots = _stub()
        slots.open_uv_editor()
        slots.tk.UiUtils.open_editor.assert_called_once_with("UV Editor")
        self.assertEqual(slots._bridge.logger.said("error"), [])

    def test_a_uv_editor_that_will_not_open_is_reported(self):
        slots = _stub()
        slots.tk.UiUtils.open_editor.return_value = None
        slots.open_uv_editor()
        self.assertEqual(
            slots._bridge.logger.said("error"), ["Could not open the UV Editor."]
        )


# ---------------------------------------------------------------------------
# b000: Process
# ---------------------------------------------------------------------------


class TestRizomBridgeProcess(unittest.TestCase):
    def test_runs_the_chosen_preset_on_the_scope(self):
        params = {"SCOPE": "selected", "SPACING": 2.0}
        slots = _stub(params=params, preset="pack_into_existing")
        _scoped(slots, ["|a.map[0:3]", "|a.map[8:11]"])
        slots.b000()
        self.assertEqual(
            slots._bridge.ran,
            (["|a.map[0:3]", "|a.map[8:11]"], "pack_into_existing", params),
        )
        slots.sb.progress.assert_called_once_with(
            text="Working: RizomUV pack_into_existing"
        )
        self.assertEqual(slots._bridge.logger.said("error"), [])

    def test_no_preset_asks_for_one_and_reads_no_scope(self):
        slots = _stub(preset=None)
        slots.b000()
        self.assertIsNone(slots._bridge.ran)
        slots.tk.BridgeHost.resolve_scope.assert_not_called()
        self.assertIn("No preset chosen", slots._bridge.logger.said("warning")[0])

    def test_an_empty_scope_runs_nothing(self):
        slots = _stub()
        _scoped(slots, [])
        slots.b000()
        self.assertIsNone(slots._bridge.ran)

    def test_without_rizomuv_the_engines_sentence_is_shown(self):
        slots = _stub()
        _scoped(slots, ["|a"])
        slots._bridge.rizom_path = None
        slots.b000()
        self.assertIsNone(slots._bridge.ran)
        self.assertEqual(
            slots._bridge.logger.said("error"), [_FakeRizom.APP.not_found_message]
        )

    def test_an_engine_error_lands_in_the_log(self):
        slots = _stub()
        _scoped(slots, ["|a"])
        slots._bridge.run_preset = mock.MagicMock(side_effect=RuntimeError("no save"))
        slots.b000()
        error = slots._bridge.logger.said("error")[0]
        self.assertTrue(error.startswith("Bridge raised:"), error)
        self.assertIn("no save", error)


# ---------------------------------------------------------------------------
# The panel loaded for real (offscreen Qt, no DCC)
# ---------------------------------------------------------------------------


def _qt_toolkit(scripts: Path, name="mayatk"):
    """The fake toolkit over two real presets (one knob, four knobs) and a real
    registry, and a third preset the engine gates out."""
    from uitk import AttributeSpec, Parameters, ParamRegistry

    def number(key):
        return AttributeSpec(
            key=key, label=key.title(), kind="float", default=1.0, section="Pack"
        )

    class _RizomRegistry(ParamRegistry):
        PARAMS = {
            "SCOPE": Parameters.scope_spec(),
            **{k: number(k) for k in ("SPACING", "MARGIN", "MUTATIONS", "ITERATIONS")},
        }

    (scripts / "few.lua").write_text(
        "-- One knob.\nZomPack({Spacing=__SPACING__})\n", encoding="utf-8"
    )
    (scripts / "many.lua").write_text(
        "-- Four knobs.\nZomPack({Spacing=__SPACING__, Margin=__MARGIN__,\n"
        "  Mutations=__MUTATIONS__, Iterations=__ITERATIONS__})\n",
        encoding="utf-8",
    )
    (scripts / "gated.lua").write_text(
        "-- Needs a newer RizomUV.\nZomPack({Spacing=__SPACING__})\n", encoding="utf-8"
    )

    class _Engine(_FakeRizom):
        SCRIPT_DIR = scripts

        @classmethod
        def params_registry(cls):
            return _RizomRegistry

        def referenced_keys(self, script_text):
            return _RizomRegistry.referenced_keys(script_text)

        def list_template_modes(self):
            return [("few", ""), ("many", "")]  # "gated": above this version

    tk = _toolkit(name)
    tk.RizomUVBridge = _Engine
    return tk


class TestRizomBridgePanelLoads(unittest.TestCase):
    """The panel built through a real (offscreen) Switchboard over the fake
    toolkit: the combo lists what the engine runs, the rows follow the preset,
    and the window follows the rows."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from qtpy import QtWidgets
        except Exception as error:  # noqa: BLE001 - no Qt binding
            raise unittest.SkipTest(f"Qt unavailable: {error}") from error
        from uitk.testing import TestSandbox

        TestSandbox.activate()  # the panel's settings and presets stay off the live stores
        cls.QtWidgets = QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.scripts = Path(tempfile.mkdtemp(prefix="rizom_panel_scripts_"))
        self.addCleanup(shutil.rmtree, self.scripts, True)

    def _load(self, name="mayatk"):
        from uitk import Switchboard

        sb = Switchboard(ui_source=str(UI_PATH), slot_source=RizomBridgeSlots)
        sb.tk = _qt_toolkit(self.scripts, name)  # set before any panel is built
        ui = sb.get_ui("rizom_bridge")
        slots = sb.get_slots_instance(ui)
        self.assertIsInstance(slots, RizomBridgeSlots)
        return ui, slots

    def _pump(self, times=5):
        for _ in range(times):
            self.QtWidgets.QApplication.processEvents()

    def test_the_combo_lists_the_presets_the_engine_runs(self):
        ui, slots = self._load("blendertk")
        slots._populate_template_combo(ui.cmb000)
        labels = [ui.cmb000.itemText(i) for i in range(ui.cmb000.count())]
        self.assertEqual(labels, ["few", "many"])  # bare stems, the gated one absent
        self.assertEqual(slots.PRESETS_ROOT, Path("blendertk") / "rizom_bridge")

    def test_the_rows_follow_the_preset(self):
        ui, slots = self._load()
        slots._populate_template_combo(ui.cmb000)
        ui.cmb000.setCurrentIndex(0)
        self.assertEqual(slots._relevant_param_keys(), {"SPACING"})
        ui.cmb000.setCurrentIndex(1)
        self.assertEqual(
            slots._relevant_param_keys(),
            {"SPACING", "MARGIN", "MUTATIONS", "ITERATIONS"},
        )

    def test_window_height_tracks_visible_param_rows(self):
        """Switching presets hides / shows rows and the window follows. Moved
        from mayatk's ``test_uv_rizom_bridge.py`` (``TestRizomBridgeUiResize``): the
        panel loads the way a host shows it (``loaded_ui``, then ``show()`` runs its
        inits)."""
        from uitk import Switchboard

        sb = Switchboard(ui_source=str(UI_PATH), slot_source=RizomBridgeSlots)
        sb.tk = _qt_toolkit(self.scripts, "mayatk")
        ui = sb.loaded_ui.rizom_bridge
        # Don't load (or persist) a saved geometry: a controlled height.
        ui.restore_window_size = False
        ui.show()
        self._pump(1)
        self.addCleanup(ui.deleteLater)
        self.addCleanup(ui.close)

        cmb = ui.cmb000
        index = {cmb.itemText(i): i for i in range(cmb.count())}
        self.assertEqual(set(index), {"few", "many"})

        # Start on the wider preset, the window forced taller than any fit, so a
        # shrink is observable.
        cmb.setCurrentIndex(index["many"])
        self._pump(1)
        ui.resize(ui.width(), 800)
        self._pump(1)
        height_many = ui.height()

        cmb.setCurrentIndex(index["few"])
        self._pump()  # the fit is deferred (QTimer.singleShot); let it land
        height_few = ui.height()
        self.assertLess(
            height_few,
            height_many,
            f"Window did not shrink: 'many' @ {height_many}px -> 'few' @ {height_few}px.",
        )


# ---------------------------------------------------------------------------
# In Maya: the real mtk
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestRizomBridgePanelInMaya(unittest.TestCase):
    """The panel's host calls against the real ``mtk`` on a real scene. Built
    with ``__new__`` like the unit cases (a batch mayapy cannot host the Qt rows
    ``__init__`` builds), over an engine with a stand-in path: nothing launches
    RizomUV, and its unknown version gates every version-flagged knob off."""

    def setUp(self):
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _panel(self, **kwargs):
        slots = _stub(tk=self.mtk, **kwargs)
        slots._bridge = self.mtk.RizomUVBridge(rizom_path="not-used.exe")
        return slots

    def test_the_panel_reads_mayatks_engine(self):
        slots = self._panel()
        engine = self.mtk.RizomUVBridge
        self.assertIs(slots.bridge_class, engine)
        self.assertEqual(slots.template_dir, engine.SCRIPT_DIR)
        self.assertTrue((slots.template_dir / "pack.lua").is_file())
        self.assertIs(slots.params_module.PARAMS, engine.params_registry().PARAMS)
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "rizom_bridge")

    def test_the_presets_and_rows_are_the_installed_versions(self):
        slots = self._panel()
        listed = dict(slots.list_template_modes())
        self.assertIn("pack", listed)
        self.assertIn("send", listed)
        self.assertNotIn("unwrap_hybrid", listed)  # gated at 2022; version unknown
        pack = (slots.template_dir / "pack.lua").read_text(encoding="utf-8")
        keys = slots.params_module.referenced_keys(pack)
        self.assertEqual(keys, slots._bridge.referenced_keys(pack))
        self.assertLessEqual(keys, set(slots.params_module.PARAMS))

    def test_scope_selected_reads_the_selection(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="rizomPanelCube")[0]
        cmds.polySphere(name="rizomPanelOther")
        cmds.select(cube, replace=True)
        resolved = self._panel().scoped_objects({"SCOPE": "selected"})
        self.assertEqual(resolved, cmds.ls(cube, long=True))

    def test_pack_into_existing_without_a_layout_runs_nothing(self):
        """A mesh whose material no other mesh shares has no layout to pack
        into: Process warns and RizomUV never runs."""
        cmds = self.cmds
        cube = cmds.polyCube(name="rizomLoneCube")[0]
        shader = cmds.shadingNode("lambert", asShader=True, name="rizomLoneMat")
        group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True)
        cmds.connectAttr(f"{shader}.outColor", f"{group}.surfaceShader", force=True)
        cmds.sets(cube, edit=True, forceElement=group)
        cmds.select(cube, replace=True)
        slots = self._panel(params={"SCOPE": "selected"}, preset="pack_into_existing")
        bridge = slots._bridge
        with mock.patch.object(bridge, "process_with_rizomuv") as run:
            with mock.patch.object(bridge.logger, "warning") as warned:
                slots.b000()
        run.assert_not_called()
        self.assertIn("no existing layout", str(warned.call_args))


if __name__ == "__main__":
    unittest.main()
