#!/usr/bin/python
# coding=utf-8
"""The Unity Bridge panel's one Slots class, and the bridge panels' shared base.

``UnityBridgeSlots`` (``slots/tools/unity_bridge.py``) sits on ``HostBridge``
(``slots/tools/_app_bridge/``), uitk's ``BridgeSlotsBase`` over the host toolkit. It
reaches its host only through ``self.tk``: the engine and its parameter registry
(``UnityBridge``), the Scope reads and the optional-package install
(``BridgeHost``), the Bake Source row (``BakeSourceSet``). A fake toolkit stands in
for ``mtk`` / ``btk`` and records what the panel asks of it.

A bridge panel builds real Qt rows in its ``__init__``, so the unit cases run the
panel's own methods on an instance that was never built (``__new__``: the bridge
base is a plain class, not a ``QObject``), with only the attributes those methods
read. Then the panel loads for real through an offscreen Switchboard over the fake
toolkit, with and without the optional unitytk, and in Maya the same methods drive
the real ``mtk`` on a real scene (``Unity Bridge`` sends into a temp project). The
engines' own side is the libraries': ``test_unity_bridge.py`` in each, and
``BridgeHost`` / ``BakeSet`` in mayatk's ``test_maya_bridge_slots_base.py``.
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools._app_bridge.host_bridge import HostBridge
from tentacle.slots.tools._unity_bridge._unity_panel import UnityPanelMixin
from tentacle.slots.tools.unity_bridge import UnityBridgeSlots

UI_PATH = Path(tentacle.__file__).resolve().parent / "ui" / "tools" / "unity_bridge.ui"
#: The optional distribution behind the engine (``mayatk[unity]``, ``blendertk[unity]``).
UNITYTK = importlib.util.find_spec("unitytk") is not None


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

    PARAMS = {"SCOPE": None, "ASSETS_SUBDIR": None}


class _FakeBridge:
    """The engine surface the panel and its base read."""

    TEMPLATE_DIR = "templates"

    def __init__(self):
        self.logger = _Log()
        self.project_path = None
        self.sent = None

    @classmethod
    def params_registry(cls):
        return _Registry

    @staticmethod
    def list_template_modes():
        return [("bake", "send_to")]

    def send(self, **kwargs):
        self.sent = kwargs
        return {}


class _BakeRegistry:
    """A bake bridge's registry: it declares the Bake Source row."""

    PARAMS = {"SCOPE": None, "BAKE_SOURCE_SET": None}


class _BakeBridge(_FakeBridge):
    @classmethod
    def params_registry(cls):
        return _BakeRegistry


def _toolkit(name="mayatk"):
    """``mtk`` / ``btk`` as the bridge panels reach them: by name, nothing else."""
    bake_set = mock.MagicMock(name="BakeSourceSet")
    bake_set.SET_NAME = "bakeBridge_source"
    return types.SimpleNamespace(
        __name__=name,
        UnityBridge=_FakeBridge,
        ProbeBridge=_BakeBridge,
        BridgeHost=mock.MagicMock(name="BridgeHost"),
        BakeSourceSet=bake_set,
    )


class _ProbeBridgeSlots(HostBridge):
    """A later bridge's panel as it plugs in: a name, an engine, a send."""

    UI_NAME = "probe_bridge"

    @property
    def bridge_class(self):
        return self.tk.ProbeBridge

    def b000(self):
        pass


def _stub(cls=UnityBridgeSlots, tk=None, params=None, project="C:/proj", template=None):
    """A *cls* panel never built, over the attributes its methods read."""
    slots = cls.__new__(cls)
    slots.sb = mock.MagicMock(name="switchboard")
    slots.sb.tk = tk or _toolkit()
    slots._bridge = _FakeBridge()
    slots._output_dir_edit = None
    slots._selected_template_mode = lambda: (template or UnityPanelMixin.MODE_COPY, "")
    slots.collect_param_values = lambda: dict(params or {})
    slots.resolved_output_dir = lambda: project
    slots._refresh_param_enablement = mock.MagicMock(name="_refresh_param_enablement")
    return slots


def _scoped(slots, objects):
    """The host resolves the Scope to *objects*; a Maya closure ships them as-is."""
    host = slots.tk.BridgeHost
    host.resolve_scope.return_value = list(objects)
    host.scope_closure.side_effect = lambda found, params: list(found)
    return host


# ---------------------------------------------------------------------------
# The panel's shape
# ---------------------------------------------------------------------------


class TestUnityBridgeShape(unittest.TestCase):
    def test_one_class_for_both_hosts_on_the_bridge_base(self):
        """The mixin first, so its hooks win over the base's; the base is uitk's
        bridge base with ``Slots``' own ``tk`` -- the same property, and no
        ``QObject`` (``BridgeSlotsBase.__init__`` never chains to one)."""
        mro = UnityBridgeSlots.__mro__
        self.assertEqual(UnityBridgeSlots.__bases__, (UnityPanelMixin, HostBridge))
        self.assertLess(mro.index(UnityPanelMixin), mro.index(Slots.BridgeSlotsBase))
        self.assertTrue(issubclass(HostBridge, Slots.BridgeSlotsBase))
        self.assertIs(vars(HostBridge)["tk"], vars(Slots)["tk"])
        qobject = Slots.__mro__[1]
        self.assertFalse(issubclass(HostBridge, qobject))

    def test_the_mixins_hooks_win(self):
        for name in ("template_dir", "list_template_modes", "default_output_dir"):
            with self.subTest(hook=name):
                self.assertIs(
                    getattr(UnityBridgeSlots, name), vars(UnityPanelMixin)[name]
                )
        self.assertFalse(UnityBridgeSlots.TEMPLATE_MENU)
        self.assertTrue(UnityBridgeSlots.REQUIRE_OUTPUT_DIR)
        self.assertEqual(UnityBridgeSlots.OUTPUT_DIR_LABEL, "Unity Project:")

    def test_two_modes_and_no_studio(self):
        """Copy to Project, plus the panel-native Manage Unity Scripts flow. Unity
        Studio is a separate, browser-based product, not this desktop hand-off."""
        S = UnityBridgeSlots
        self.assertEqual(S.MODE_COPY, "copy_to_assets")
        self.assertEqual(S.MODE_MANAGE, "manage_scripts")
        self.assertEqual(
            S.MODE_LABELS,
            {S.MODE_COPY: "Copy to Project", S.MODE_MANAGE: "Manage Unity Scripts"},
        )
        self.assertEqual(
            _stub().list_template_modes(), [(S.MODE_COPY, ""), (S.MODE_MANAGE, "")]
        )
        self.assertEqual(S.SCRIPT_PARAM_KEYS, frozenset({"SCRIPTS", "SCRIPTS_ACTION"}))
        for gone in (
            "MODE_STUDIO",
            "MODE_EXISTING",
            "MODE_PARAM_KEYS",
            "_deploy_unity_scripts",
        ):
            self.assertFalse(hasattr(S, gone), gone)

    def test_it_pairs_with_the_unity_bridge_ui(self):
        self.assertEqual(UnityBridgeSlots.UI_NAME, "unity_bridge")
        self.assertEqual(UnityBridgeSlots.HELP_SPEC["title"], "Unity Bridge")


# ---------------------------------------------------------------------------
# What the panel asks of its host
# ---------------------------------------------------------------------------


class TestUnityBridgeAsksItsHost(unittest.TestCase):
    def test_the_engine_is_the_hosts_unity_bridge(self):
        slots = _stub()
        self.assertIs(slots.bridge_class, slots.tk.UnityBridge)
        with mock.patch.object(
            UnityBridgeSlots, "optional_package_available", return_value=True
        ) as available:
            self.assertIsInstance(slots.make_bridge(), _FakeBridge)
        available.assert_called_once_with("unitytk")

    def test_without_unitytk_the_engine_is_absent_and_silent(self):
        """``make_bridge`` runs from ``__init__``: no prompt, just no engine."""
        slots = _stub()
        with mock.patch.object(
            UnityBridgeSlots, "optional_package_available", return_value=False
        ):
            self.assertIsNone(slots.make_bridge())
        slots.sb.message_box.assert_not_called()

    def test_the_registry_is_the_engines(self):
        self.assertIs(_stub().params_module, _Registry)

    def test_presets_stay_in_each_hosts_folder(self):
        """Where each host's panel kept them before the move: saved user presets."""
        for name in ("mayatk", "blendertk"):
            with self.subTest(host=name):
                root = _stub(tk=_toolkit(name)).PRESETS_ROOT
                self.assertEqual(root, Path(name) / "unity_bridge")

    def test_the_scope_resolves_through_the_host_with_the_engine(self):
        slots = _stub()
        _scoped(slots, ["|pCube1"])
        self.assertEqual(slots.resolve_scope_objects("visible"), ["|pCube1"])
        slots.tk.BridgeHost.resolve_scope.assert_called_once_with(
            "visible", slots._bridge
        )

    def test_without_an_engine_the_scope_resolves_without_one(self):
        """Entire Scene then falls back to the scene's meshes (the host's rule)."""
        slots = _stub()
        slots._bridge = None
        _scoped(slots, ["|mesh"])
        with mock.patch.object(
            UnityBridgeSlots, "optional_package_available", return_value=False
        ):
            slots.resolve_scope_objects("all")
        slots.tk.BridgeHost.resolve_scope.assert_called_once_with("all", None)

    def test_the_host_closes_a_scope_over_what_ships(self):
        slots = _stub()
        host = slots.tk.BridgeHost
        host.resolve_scope.return_value = ["|grp"]
        host.scope_closure.return_value = ["|grp", "|grp|child"]
        params = {"SCOPE": "all"}
        self.assertEqual(slots.scoped_objects(params), ["|grp", "|grp|child"])
        host.scope_closure.assert_called_once_with(["|grp"], params)

    def test_an_empty_scope_is_reported_not_closed(self):
        slots = _stub()
        _scoped(slots, [])
        self.assertEqual(slots.scoped_objects({"SCOPE": "visible"}), [])
        slots.tk.BridgeHost.scope_closure.assert_not_called()
        self.assertEqual(
            slots._bridge.logger.said("warning"),
            ["No visible mesh geometry to export."],
        )

    def test_an_optional_package_installs_where_the_host_imports(self):
        slots = _stub()
        slots._install_optional_package("unitytk>=0.1.0")
        slots.tk.BridgeHost.install_package.assert_called_once_with("unitytk>=0.1.0")


# ---------------------------------------------------------------------------
# b000: the send
# ---------------------------------------------------------------------------


class TestUnityBridgeSend(unittest.TestCase):
    def test_copies_the_scope_into_the_project(self):
        params = {"SCOPE": "selected", "ASSETS_SUBDIR": "Models"}
        slots = _stub(params=params, project="C:/proj")
        _scoped(slots, ["|pCube1"])
        slots.b000()
        bridge = slots._bridge
        self.assertEqual(bridge.project_path, "C:/proj")
        self.assertEqual(
            bridge.sent,
            {
                "objects": ["|pCube1"],
                "template": "copy_to_assets",
                "mode": "",
                "params": params,
            },
        )
        slots.sb.progress.assert_called_once_with(text="Working: Send to Unity")
        self.assertEqual(bridge.logger.said("error"), [])

    def test_the_header_names_the_scope_it_collected_under(self):
        """REGRESSION (2026-08-18): the header read an undefined ``scope`` and
        raised before the bridge ran, on every send past the project guard."""
        slots = _stub(params={"SCOPE": "visible"})
        _scoped(slots, ["|a"])
        slots.b000()
        header = next(
            m for m in slots._bridge.logger.said("info") if m.startswith("--- ")
        )
        self.assertIn("(visible)", header)
        self.assertIn("1 object(s)", header)

    def test_a_panel_without_a_scope_row_names_the_selection(self):
        slots = _stub(params={})
        _scoped(slots, ["|a"])
        slots.b000()
        header = next(
            m for m in slots._bridge.logger.said("info") if m.startswith("--- ")
        )
        self.assertIn("(selected)", header)

    def test_no_project_asks_for_one_and_sends_nothing(self):
        slots = _stub(project="")
        _scoped(slots, ["|a"])
        slots._output_dir_edit = mock.MagicMock(name="project_field")
        slots.b000()
        self.assertIsNone(slots._bridge.sent)
        self.assertIn(
            "Set the Unity Project folder", slots._bridge.logger.said("error")[0]
        )
        slots._output_dir_edit.setFocus.assert_called_once_with()

    def test_an_empty_scope_sends_nothing(self):
        slots = _stub()
        _scoped(slots, [])
        slots.b000()
        self.assertIsNone(slots._bridge.sent)

    def test_manage_mode_runs_the_scripts_action_instead(self):
        slots = _stub(
            params={"SCRIPTS_ACTION": "install"}, template=UnityBridgeSlots.MODE_MANAGE
        )
        slots._manage_unity_scripts = mock.MagicMock(name="_manage_unity_scripts")
        slots.b000()
        slots._manage_unity_scripts.assert_called_once_with("install")
        slots.tk.BridgeHost.resolve_scope.assert_not_called()
        self.assertIsNone(slots._bridge.sent)

    def test_an_engine_error_lands_in_the_log(self):
        slots = _stub()
        _scoped(slots, ["|a"])
        slots._bridge.send = mock.MagicMock(side_effect=RuntimeError("copy failed"))
        slots.b000()
        error = slots._bridge.logger.said("error")[0]
        self.assertTrue(error.startswith("Bridge raised:"), error)
        self.assertIn("copy failed", error)


# ---------------------------------------------------------------------------
# The shared base: what a later bridge plugs into
# ---------------------------------------------------------------------------


class TestHostBridgeDefaults(unittest.TestCase):
    def test_a_bridge_reads_its_registry_templates_and_modes_off_its_engine(self):
        probe = _stub(_ProbeBridgeSlots)
        self.assertIs(probe.params_module, _BakeRegistry)
        self.assertEqual(probe.template_dir, "templates")
        self.assertEqual(probe.list_template_modes(), [("bake", "send_to")])
        self.assertIsInstance(probe.make_bridge(), _BakeBridge)
        self.assertEqual(probe.PRESETS_ROOT, Path("mayatk") / "probe_bridge")

    def test_a_panel_must_name_its_engine(self):
        bare = HostBridge.__new__(HostBridge)
        with self.assertRaises(NotImplementedError):
            bare.bridge_class  # noqa: B018 - the property is the assertion


class TestHostBridgeBakeSource(unittest.TestCase):
    """The Bake Source row's three buttons and its live member list, once for
    every bake bridge, over the host's ``BakeSourceSet``."""

    def setUp(self):
        self.probe = _stub(_ProbeBridgeSlots)
        self.bake_set = self.probe.tk.BakeSourceSet
        self.log = self.probe._bridge.logger

    def test_the_row_lists_the_sets_members_live(self):
        self.bake_set.member_names.return_value = ["source_mesh"]
        provider = self.probe.live_param_tooltip_blocks()["BAKE_SOURCE_SET"]
        self.assertIn("source_mesh", provider())
        self.bake_set.member_names.return_value = ["other_mesh"]
        self.assertIn("other_mesh", provider())  # read on each hover

    def test_only_a_bridge_with_the_row_lists_it(self):
        self.assertNotIn("BAKE_SOURCE_SET", _stub().live_param_tooltip_blocks())

    def test_the_member_list_never_raises_into_qt(self):
        self.bake_set.member_names.side_effect = RuntimeError("no scene")
        self.assertEqual(self.probe._bake_source_tooltip(), "")

    def test_set_from_selection_defines_the_set(self):
        self.bake_set.define.return_value = ["|a", "|b"]
        self.probe.set_bake_source_from_selection()
        self.bake_set.define.assert_called_once_with()
        self.probe._refresh_param_enablement.assert_called_once_with()
        self.assertEqual(
            self.log.said("info"),
            [
                "Bake Source set: 2 object(s) -> bakeBridge_source. "
                "Sends now ship it as the companion bake source."
            ],
        )

    def test_a_bridge_says_what_the_set_means_for_its_sends(self):
        self.probe.BAKE_SOURCE_DEFINED_NOTE = (
            "Bake sends now export it as the bake source."
        )
        self.bake_set.define.return_value = ["|a"]
        self.probe.set_bake_source_from_selection()
        self.assertTrue(
            self.log.said("info")[0].endswith("export it as the bake source.")
        )

    def test_set_from_nothing_clears_and_says_so(self):
        self.bake_set.define.return_value = []
        self.probe.set_bake_source_from_selection()
        self.assertEqual(
            self.log.said("warning"),
            ["Nothing selected; the bake-source set was cleared."],
        )

    def test_select_counts_what_the_host_could_not_select(self):
        self.bake_set.members.return_value = ["a", "b", "c"]
        self.bake_set.select.return_value = ["a", "b"]
        self.probe.select_bake_source()
        self.assertEqual(
            self.log.said("info"),
            [
                "Selected 2 bake-source object(s). 1 could not be selected (hidden, "
                "or not selectable here); they still export."
            ],
        )

    def test_select_of_every_member_says_only_that(self):
        self.bake_set.members.return_value = ["a"]
        self.bake_set.select.return_value = ["a"]
        self.probe.select_bake_source()
        self.assertEqual(self.log.said("info"), ["Selected 1 bake-source object(s)."])

    def test_select_without_a_set_selects_nothing(self):
        self.bake_set.members.return_value = []
        self.probe.select_bake_source()
        self.bake_set.select.assert_not_called()
        self.assertEqual(self.log.said("warning"), ["No bake-source set is defined."])

    def test_clear_removes_the_set_and_says_what_follows(self):
        self.bake_set.exists.return_value = True
        self.probe.BAKE_SOURCE_CLEARED_NOTE = "Pairing falls back to the suffixes."
        self.probe.clear_bake_source()
        self.bake_set.clear.assert_called_once_with()
        self.assertEqual(
            self.log.said("info"),
            ["Bake-source set cleared. Pairing falls back to the suffixes."],
        )

    def test_clear_without_a_set_touches_nothing(self):
        self.bake_set.exists.return_value = False
        self.probe.clear_bake_source()
        self.bake_set.clear.assert_not_called()
        self.assertEqual(self.log.said("warning"), ["No bake-source set is defined."])


class TestEditorVersionCombo(unittest.TestCase):
    @unittest.skipUnless(
        UNITYTK, "unitytk is not installed (the optional 'unity' extra)"
    )
    def test_versions_rank_numerically_not_as_strings(self):
        """A string sort ranked ``2022.3.9f1`` above ``2022.3.10f1``, so the
        "newest" at the top of the list was an older Editor."""
        from unitytk import UnityFinder

        added = []
        combo = types.SimpleNamespace(addItem=lambda text, data: added.append(text))
        host = types.SimpleNamespace(_param_widgets={"UNITY_VERSION": combo})
        editors = {"2022.3.9f1": "a", "2022.3.10f1": "b", "6000.0.2f1": "c"}
        with mock.patch.object(UnityFinder, "find_editors", return_value=editors):
            UnityBridgeSlots._populate_unity_versions(host)
        self.assertEqual(added, ["6000.0.2f1", "2022.3.10f1", "2022.3.9f1"])


# ---------------------------------------------------------------------------
# The panel loaded for real (offscreen Qt, no DCC)
# ---------------------------------------------------------------------------


def _qt_toolkit(name="mayatk"):
    """The fake toolkit, its engine carrying a real registry of the rows the Unity
    panel acts on (each library's own is its ``unity_bridge/parameters.py``): the
    built panel makes real widgets from it."""
    from uitk import AttributeSpec, Parameters, ParamRegistry

    def choice(key, default, choices, section):
        return AttributeSpec(
            key=key,
            label=key.title(),
            kind="choice",
            default=default,
            choices=choices,
            section=section,
        )

    class _UnityRegistry(ParamRegistry):
        PARAMS = {
            "SCOPE": Parameters.scope_spec(),
            "UNITY_VERSION": choice(
                "UNITY_VERSION", "", [("Auto (newest)", "")], "Unity"
            ),
            "SCRIPTS": AttributeSpec(
                key="SCRIPTS",
                label="Scripts",
                kind="check_list",
                default=[],
                choices=[],
                section="Unity Scripts",
            ),
            "SCRIPTS_ACTION": choice(
                "SCRIPTS_ACTION", "status", [("Status", "status")], "Unity Scripts"
            ),
        }

    class _Engine(_FakeBridge):
        @classmethod
        def params_registry(cls):
            return _UnityRegistry

    tk = _toolkit(name)
    tk.UnityBridge = _Engine
    return tk


class _BlockUnitytk:
    """An import hook that makes unitytk absent, as a host without the extra is."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "unitytk" or fullname.startswith("unitytk."):
            raise ImportError("unitytk blocked: the engine-missing panel")
        return None


class TestUnityBridgePanelLoads(unittest.TestCase):
    """The panel built through a real (offscreen) Switchboard over the fake
    toolkit: the regression surface of the 2026-07-29 live failure, where
    ``make_bridge`` prompted from ``__init__`` and stranded the modal. With and
    without unitytk the panel builds, with no dialog."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from qtpy import QtWidgets
        except Exception as error:  # noqa: BLE001 - no Qt binding
            raise unittest.SkipTest(f"Qt unavailable: {error}") from error
        from uitk.testing import TestSandbox

        TestSandbox.activate()  # the panel's settings and presets stay off the live stores
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _load(self, tk):
        from uitk import Switchboard

        sb = Switchboard(ui_source=str(UI_PATH), slot_source=UnityBridgeSlots)
        sb.tk = tk  # as the host entry point sets it, before any panel is built
        ui = sb.get_ui("unity_bridge")
        slots = sb.get_slots_instance(ui)
        self.assertIsInstance(slots, UnityBridgeSlots)
        return ui, slots

    @unittest.skipUnless(
        UNITYTK, "unitytk is not installed (the optional 'unity' extra)"
    )
    def test_with_unitytk_the_panel_offers_both_modes_and_every_script(self):
        from unitytk import TemplateDeployer

        ui, slots = self._load(_qt_toolkit())
        self.assertIsInstance(slots.peek_bridge(), _FakeBridge)
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "unity_bridge")
        combo = ui.cmb000
        slots._populate_template_combo(combo)  # cmb000 fills on first show
        labels = [combo.itemText(i) for i in range(combo.count())]
        self.assertEqual(labels, ["Copy to Project", "Manage Unity Scripts"])
        combo.setCurrentIndex(1)
        self.assertEqual(slots._relevant_param_keys(), {"SCRIPTS", "SCRIPTS_ACTION"})
        combo.setCurrentIndex(0)
        keys = slots._relevant_param_keys()
        self.assertFalse(keys & {"SCRIPTS", "SCRIPTS_ACTION"})
        self.assertIn("SCOPE", keys)
        expected = [c for c in TemplateDeployer.components() if not c.required]
        checklist = slots._param_widgets["SCRIPTS"]
        rows = [checklist.item(i).text() for i in range(checklist.count())]
        self.assertEqual(rows, [c.label for c in expected])
        self.assertEqual(slots._script_selection(), [c.key for c in expected])
        self.assertGreater(slots._param_rows["SCRIPTS"].maximumHeight(), 19)

    def test_without_unitytk_the_panel_still_opens_and_reports(self):
        saved = {
            name: module
            for name, module in sys.modules.items()
            if name == "unitytk" or name.startswith("unitytk.")
        }
        blocker = _BlockUnitytk()
        for name in saved:
            del sys.modules[name]
        sys.meta_path.insert(0, blocker)
        self.addCleanup(sys.modules.update, saved)
        self.addCleanup(sys.meta_path.remove, blocker)
        with mock.patch.object(
            UnityBridgeSlots, "optional_package_available", return_value=False
        ):
            ui, slots = self._load(_qt_toolkit("blendertk"))
            self.assertIsNone(slots.peek_bridge())
            self.assertEqual(slots._param_widgets["SCRIPTS"].count(), 0)
            self.assertIsNone(slots._script_selection())  # None = the full set
            slots._output_dir_edit.setText(tempfile.gettempdir())
            slots._manage_unity_scripts("status")
        self.assertIn("not installed", ui.txt000.toPlainText())


# ---------------------------------------------------------------------------
# In Maya: the real mtk
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestUnityBridgePanelInMaya(unittest.TestCase):
    """The panel's host calls against the real ``mtk`` on a real scene. Built
    with ``__new__`` like the unit cases: the panel's ``__init__`` builds Qt rows,
    which a batch mayapy cannot host (``_host.qt_widgets_available``)."""

    def setUp(self):
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _panel(self, engine=False, **kwargs):
        slots = _stub(tk=self.mtk, **kwargs)
        if engine:
            slots._bridge = self.mtk.UnityBridge()
        return slots

    def _long(self, node):
        return self.cmds.ls(node, long=True)[0]

    def test_the_panel_reads_mayatks_engine_registry_and_preset_folder(self):
        slots = self._panel()
        self.assertIs(slots.bridge_class, self.mtk.UnityBridge)
        registry = self.mtk.UnityBridge.params_registry()
        self.assertIs(slots.params_module, registry)
        self.assertIn("SCOPE", registry.PARAMS)
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "unity_bridge")

    def test_scope_selected_ships_the_selection_as_is(self):
        """Maya's export-selection writes a group's subtree: no closure needed."""
        cmds = self.cmds
        group = cmds.group(cmds.polyCube(name="unitySelCube")[0], name="unitySelGroup")
        cmds.polySphere(name="unityOtherSphere")
        cmds.select(group, replace=True)
        resolved = self._panel().scoped_objects({"SCOPE": "selected"})
        self.assertEqual(resolved, [self._long(group)])

    def test_an_unknown_scope_never_widens(self):
        self.cmds.polyCube()
        self.cmds.select(clear=True)
        self.assertEqual(self._panel().resolve_scope_objects("bogus"), [])

    @unittest.skipUnless(
        UNITYTK, "the engine needs unitytk (the optional 'unity' extra)"
    )
    def test_entire_scene_returns_roots_so_the_hierarchy_travels(self):
        cmds = self.cmds
        group = cmds.group(
            cmds.polyCube(name="unityRootCube")[0], name="unityRootGroup"
        )
        cmds.select(clear=True)
        resolved = self._panel(engine=True).resolve_scope_objects("all")
        self.assertIn(self._long(group), resolved)

    def test_entire_scene_without_an_engine_falls_back_to_the_meshes(self):
        self.cmds.polyCube(name="unityFallbackCube")
        self.cmds.select(clear=True)
        slots = self._panel()
        slots._bridge = None
        with mock.patch.object(
            UnityBridgeSlots, "optional_package_available", return_value=False
        ):
            resolved = slots.resolve_scope_objects("all")
        self.assertTrue(resolved)
        self.assertTrue(
            all(self.cmds.objectType(o) == "mesh" for o in resolved), resolved
        )

    def test_visible_only_leaves_the_hidden_out(self):
        cmds = self.cmds
        cmds.polyCube(name="unityVisibleCube")
        hidden = cmds.polyCube(name="unityHiddenCube")[0]
        cmds.setAttr(f"{hidden}.visibility", 0)
        cmds.select(clear=True)
        resolved = [str(o) for o in self._panel().resolve_scope_objects("visible")]
        self.assertTrue(any("unityVisibleCube" in o for o in resolved), resolved)
        self.assertFalse(any("unityHiddenCube" in o for o in resolved), resolved)

    def test_the_bake_source_row_drives_the_scene_set(self):
        cmds, bake_set = self.cmds, self.mtk.BakeSourceSet
        cube = self._long(cmds.polyCube(name="unityBakeSource")[0])
        cmds.setAttr(f"{cube}.visibility", 0)  # a hidden member still selects in Maya
        slots = self._panel()
        cmds.select(cube, replace=True)
        slots.set_bake_source_from_selection()
        self.assertTrue(bake_set.exists())
        self.assertIn("unityBakeSource", slots._bake_source_tooltip())
        cmds.select(clear=True)
        slots.select_bake_source()
        self.assertEqual(cmds.ls(selection=True, long=True), [cube])
        self.assertIn(
            "Selected 1 bake-source object(s).", slots._bridge.logger.said("info")
        )
        slots.clear_bake_source()
        self.assertFalse(bake_set.exists())
        self.assertTrue(cmds.objExists(cube))

    @unittest.skipUnless(
        UNITYTK, "the engine needs unitytk (the optional 'unity' extra)"
    )
    def test_send_copies_the_fbx_into_the_projects_assets(self):
        cmds = self.cmds
        tmp = Path(tempfile.mkdtemp(prefix="unity_panel_test_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        project = tmp / "UnityProj"
        (project / "Assets").mkdir(parents=True)
        cmds.select(cmds.polyCube(name="unityPanelHero")[0], replace=True)
        params = {"SCOPE": "selected", "ASSETS_SUBDIR": "Models", "ASSET_NAME": ""}
        slots = self._panel(engine=True, params=params, project=str(project))
        slots.b000()
        dest = project / "Assets" / "Models" / "unityPanelHero.fbx"
        self.assertTrue(dest.is_file(), f"no FBX at {dest}")
        self.assertGreater(dest.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
