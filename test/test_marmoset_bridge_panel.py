#!/usr/bin/python
# coding=utf-8
"""The Marmoset Bridge panel's one Slots class.

``MarmosetBridgeSlots`` (``slots/tools/marmoset_bridge.py``) sits on ``HostBridge``
(``slots/tools/_app_bridge/``) and reaches its host only through ``self.tk``: the
engine with its registry, template folder and ``(template, mode)`` list
(``MarmosetBridge``), the Scope (``BridgeHost``), and the scene's Bake Source set
(``BakeSourceSet``), which also greys the suffix-fallback rows. A fake toolkit
stands in for ``mtk`` / ``btk`` and records what the panel asks of it. The shared
base's own cases (Scope, closure, the Bake Source row's three actions) are
``test_unity_bridge_panel.py``'s; these pin what this bridge adds.

The unit cases run the panel's methods on an instance never built (``__new__``:
the bridge base is a plain class, not a ``QObject``). Then the panel loads for
real through an offscreen Switchboard over a fake engine with a real registry,
and in Maya the same methods drive the real ``mtk`` on a real scene. The engine's
own side is the libraries': ``test_mat_marmoset_bridge.py`` (mayatk) and
``test_bridges.py`` (blendertk).
"""

import os
import shutil
import tempfile
import types
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots.tools._app_bridge.host_bridge import HostBridge
from tentacle.slots.tools.marmoset_bridge import MarmosetBridgeSlots

UI_PATH = (
    Path(tentacle.__file__).resolve().parent / "ui" / "tools" / "marmoset_bridge.ui"
)
SUFFIX_KEYS = ("HIGH_SUFFIX", "LOW_SUFFIX", "SUFFIX_INCLUDE_CHILDREN")
BAKE_ROUNDTRIP = ("bake", ptk.ROUND_TRIP)


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

    PARAMS = dict.fromkeys(("SCOPE", "BAKE_SOURCE_SET") + SUFFIX_KEYS)


class _FakeMarmoset:
    """The engine surface the panel and its base read."""

    TEMPLATE_DIR = Path("templates")
    APP = types.SimpleNamespace(not_found_message="Marmoset Toolbag was not found.")

    def __init__(self):
        self.logger = _Log()
        self.toolbag_path = "C:/Toolbag/toolbag.exe"
        self.sent = None

    @classmethod
    def params_registry(cls):
        return _Registry

    @staticmethod
    def list_template_modes():
        return [("import", ptk.SEND_TO), ("bake", ptk.SEND_TO), BAKE_ROUNDTRIP]

    def send(self, **kwargs):
        self.sent = kwargs
        return {}


def _toolkit(name="mayatk", has_set=False):
    """``mtk`` / ``btk`` as the panel reaches them: by name, nothing else."""
    bake_set = mock.MagicMock(name="BakeSourceSet")
    bake_set.SET_NAME = "bakeBridge_source"
    bake_set.exists.return_value = has_set
    return types.SimpleNamespace(
        __name__=name,
        MarmosetBridge=_FakeMarmoset,
        BridgeHost=mock.MagicMock(name="BridgeHost"),
        BakeSourceSet=bake_set,
    )


def _stub(tk=None, params=None, output_dir="", pair=BAKE_ROUNDTRIP):
    """A panel never built, over the attributes its methods read; the rows it
    greys land in ``slots.enabled`` as ``{key: (enabled, reason)}``."""
    slots = MarmosetBridgeSlots.__new__(MarmosetBridgeSlots)
    slots.sb = mock.MagicMock(name="switchboard")
    slots.sb.tk = tk or _toolkit()
    slots._bridge = _FakeMarmoset()
    slots._output_dir_edit = None
    slots._param_widgets = {}
    slots._selected_template_mode = lambda: pair
    slots.collect_param_values = lambda: dict(
        {"SCOPE": "selected"} if params is None else params
    )
    slots.resolved_output_dir = lambda: output_dir
    slots.enabled = {}
    slots.set_param_enabled = lambda key, on, reason="": slots.enabled.__setitem__(
        key, (on, reason)
    )
    return slots


def _scoped(slots, objects):
    """The host resolves the Scope to *objects* and ships them as they are."""
    host = slots.tk.BridgeHost
    host.resolve_scope.return_value = list(objects)
    host.scope_closure.side_effect = lambda found, params: list(found)
    return host


# ---------------------------------------------------------------------------
# The panel's shape
# ---------------------------------------------------------------------------


class TestMarmosetBridgeShape(unittest.TestCase):
    def test_one_class_for_both_hosts_on_the_bridge_base(self):
        self.assertEqual(MarmosetBridgeSlots.__bases__, (HostBridge,))
        self.assertEqual(MarmosetBridgeSlots.UI_NAME, "marmoset_bridge")
        self.assertEqual(MarmosetBridgeSlots.LOG_TAG, "marmoset_bridge")
        self.assertEqual(MarmosetBridgeSlots.HELP_SPEC["title"], "Marmoset Bridge")

    def test_the_help_names_the_send_button_the_ui_carries(self):
        root = ElementTree.parse(UI_PATH).getroot()
        button = next(w for w in root.iter("widget") if w.get("name") == "b000")
        label = next(p.find("string").text for p in button if p.get("name") == "text")
        self.assertEqual(label, "Send to Marmoset")
        self.assertIn(f"<b>{label}</b>", MarmosetBridgeSlots.HELP_SPEC["steps"][-1])

    def test_holding_esc_cancels_the_send(self):
        """The Send runs inside the dispatcher's CancelScope (``@Cancelable``),
        the scope a hidden roundtrip polls: without it Esc held over a stuck
        bake did nothing. Moved from mayatk's ``test_mat_marmoset_bridge.py``
        (added 2026-10-19)."""
        meta = getattr(MarmosetBridgeSlots.b000, "_cancelable_meta", None) or {}
        self.assertGreater(meta.get("timeout") or 0, 0)
        self.assertEqual(meta.get("message"), "Marmoset Toolbag run")

    def test_a_blank_output_dir_leaves_every_mode_to_the_bridge(self):
        """Blank means the bridge's own rule in every mode (scratch for the
        hand-off, project folders for what is kept), never a scene-folder
        default. Moved from mayatk (added 2026-10-13)."""
        self.assertEqual(
            set(MarmosetBridgeSlots.TRANSIENT_OUTPUT_MODES),
            {ptk.SEND_TO, ptk.ROUND_TRIP},
        )
        self.assertEqual(MarmosetBridgeSlots.default_output_dir(None), "")
        for mode in (ptk.SEND_TO, ptk.ROUND_TRIP):
            with self.subTest(mode=mode):
                slots = _stub()
                self.assertEqual(slots.require_output_dir(mode), "")
                self.assertEqual(slots._bridge.logger.said("error"), [])


# ---------------------------------------------------------------------------
# What the panel asks of its host
# ---------------------------------------------------------------------------


class TestMarmosetBridgeAsksItsHost(unittest.TestCase):
    def test_the_engine_registry_templates_and_modes_are_the_hosts(self):
        slots = _stub()
        self.assertIs(slots.bridge_class, slots.tk.MarmosetBridge)
        self.assertIsInstance(slots.make_bridge(), _FakeMarmoset)
        self.assertIs(slots.params_module, _Registry)
        self.assertEqual(slots.template_dir, Path("templates"))
        self.assertEqual(
            slots.list_template_modes(), _FakeMarmoset.list_template_modes()
        )

    def test_presets_stay_in_each_hosts_folder(self):
        """Where each host's panel kept them before the move: saved user presets."""
        for name in ("mayatk", "blendertk"):
            with self.subTest(host=name):
                root = _stub(tk=_toolkit(name)).PRESETS_ROOT
                self.assertEqual(root, Path(name) / "marmoset_bridge")

    def test_the_combo_opens_on_the_bake_roundtrip(self):
        slots = _stub()
        pairs = _FakeMarmoset.list_template_modes()
        self.assertEqual(slots.select_initial_template_index(pairs), 2)
        no_roundtrip = [("import", ptk.SEND_TO), ("bake", ptk.SEND_TO)]
        self.assertEqual(slots.select_initial_template_index(no_roundtrip), 1)
        self.assertEqual(
            slots.select_initial_template_index([("lookdev", ptk.SEND_TO)]), 0
        )


# ---------------------------------------------------------------------------
# The Bake Source set: this bridge's sentence and its suffix rows
# ---------------------------------------------------------------------------


class TestMarmosetBridgeBakeSource(unittest.TestCase):
    """While the scene has a Bake Source set the name-suffix fallback is moot,
    so its rows grey (with the reason) -- re-evaluated on every refresh and at
    once after the row's own actions."""

    def test_a_defined_set_greys_the_suffix_rows(self):
        slots = _stub(tk=_toolkit(has_set=True))
        slots._refresh_param_enablement()
        self.assertEqual(set(slots.enabled), set(SUFFIX_KEYS))
        for key in SUFFIX_KEYS:
            on, reason = slots.enabled[key]
            self.assertFalse(on, key)
            self.assertIn("Bake Source set", reason)

    def test_without_a_set_they_are_live(self):
        slots = _stub(tk=_toolkit(has_set=False))
        slots._refresh_param_enablement()
        self.assertEqual(slots.enabled, {key: (True, "") for key in SUFFIX_KEYS})

    def test_a_host_library_without_its_scene_reads_as_no_set(self):
        """blendertk loads outside Blender (no ``bpy``) while the panel is built:
        the rows stay live instead of the panel failing to open."""
        tk = _toolkit()
        tk.BakeSourceSet.exists.side_effect = ImportError("No module named 'bpy'")
        slots = _stub(tk=tk)
        slots._refresh_param_enablement()
        self.assertEqual(slots.enabled, {key: (True, "") for key in SUFFIX_KEYS})

    def test_defining_the_set_names_this_bridges_send_and_greys_at_once(self):
        slots = _stub(tk=_toolkit(has_set=True))
        slots.tk.BakeSourceSet.define.return_value = ["|hi_poly"]
        slots.set_bake_source_from_selection()
        message = slots._bridge.logger.said("info")[0]
        self.assertIn("Bake sends now export it as the bake source", message)
        self.assertIn("Suffix fallback is inactive", message)
        self.assertTrue(all(not slots.enabled[k][0] for k in SUFFIX_KEYS))

    def test_clearing_says_pairing_falls_back_and_frees_the_rows(self):
        slots = _stub()
        slots.tk.BakeSourceSet.exists.side_effect = [True, False]  # guard, refresh
        slots.clear_bake_source()
        slots.tk.BakeSourceSet.clear.assert_called_once_with()
        self.assertEqual(
            slots._bridge.logger.said("info"),
            [
                "Bake-source set cleared. Pairing falls back to the "
                "Source/Target Suffix convention."
            ],
        )
        self.assertEqual(slots.enabled, {key: (True, "") for key in SUFFIX_KEYS})


# ---------------------------------------------------------------------------
# b000: the send
# ---------------------------------------------------------------------------


class TestMarmosetBridgeSend(unittest.TestCase):
    def test_sends_the_scope_with_the_chosen_template_and_mode(self):
        params = {"SCOPE": "selected", "BAKE_SIZE": 2048}
        slots = _stub(params=params)
        _scoped(slots, ["|pCube1"])
        slots.b000()
        self.assertEqual(
            slots._bridge.sent,
            {
                "objects": ["|pCube1"],
                "template": "bake",
                "mode": ptk.ROUND_TRIP,
                "output_dir": "",
                "params": params,
            },
        )
        slots.sb.progress.assert_called_once_with(
            text=f"Working: Marmoset bake ({ptk.ROUND_TRIP})"
        )
        self.assertIn(
            f"--- bake ({ptk.ROUND_TRIP}) on 1 object(s) ---",
            slots._bridge.logger.said("info"),
        )
        self.assertEqual(slots._bridge.logger.said("error"), [])

    def test_a_named_output_dir_wins(self):
        slots = _stub(output_dir="C:/handoff")
        _scoped(slots, ["|a"])
        slots.b000()
        self.assertEqual(slots._bridge.sent["output_dir"], "C:/handoff")

    def test_an_empty_scope_sends_nothing_and_says_why(self):
        slots = _stub()
        _scoped(slots, [])
        slots.b000()
        self.assertIsNone(slots._bridge.sent)
        self.assertTrue(slots._bridge.logger.said("warning"))

    def test_no_template_sends_nothing(self):
        slots = _stub(pair=None)
        _scoped(slots, ["|a"])
        slots.b000()
        self.assertIsNone(slots._bridge.sent)
        self.assertIn("No template chosen", slots._bridge.logger.said("warning")[0])

    def test_without_toolbag_the_apps_own_sentence_is_logged(self):
        slots = _stub()
        _scoped(slots, ["|a"])
        slots._bridge.toolbag_path = None
        slots.b000()
        self.assertIsNone(slots._bridge.sent)
        self.assertEqual(
            slots._bridge.logger.said("error"),
            [_FakeMarmoset.APP.not_found_message],
        )

    def test_an_engine_error_lands_in_the_log(self):
        slots = _stub()
        _scoped(slots, ["|a"])
        slots._bridge.send = mock.MagicMock(side_effect=RuntimeError("bake failed"))
        slots.b000()
        error = slots._bridge.logger.said("error")[0]
        self.assertTrue(error.startswith("Bridge raised:"), error)
        self.assertIn("bake failed", error)


# ---------------------------------------------------------------------------
# The panel loaded for real (offscreen Qt, no DCC)
# ---------------------------------------------------------------------------

#: Two templates: ``bake`` references every row, ``import`` only the Scope.
_TEMPLATES = {
    "bake": '"""Bake maps from the source onto the target."""\n'
    "SIZE = __BAKE_SIZE__\nSCOPE = __SCOPE__\nPAIRING = (__BAKE_SOURCE_SET__, "
    "__HIGH_SUFFIX__, __LOW_SUFFIX__, __SUFFIX_INCLUDE_CHILDREN__)\n"
    "MAPS = (__MAP_NORMAL__, __MAP_AO__, __MAP_CURVATURE__)\n",
    "import": '"""Import the selection."""\nSCOPE = __SCOPE__\n',
}


def _qt_toolkit(template_dir, has_set=False):
    """The fake toolkit, its engine carrying a real registry of the rows the
    panel acts on (each library's own is its ``marmoset_bridge/parameters.py``)
    and a real template folder: the built panel makes real widgets from them."""
    from uitk import AttributeSpec, Parameters, ParamRegistry

    def flag(key):
        return AttributeSpec(key=key, label=key.title(), kind="bool", default=True)

    def choice(key, choices):
        return AttributeSpec(
            key=key,
            label=key.title(),
            kind="choice",
            default=choices[0][1],
            choices=choices,
        )

    class _MarmosetRegistry(ParamRegistry):
        PARAMS = {
            "SCOPE": Parameters.scope_spec(),
            "BAKE_SIZE": choice("BAKE_SIZE", [("2048", 2048), ("4096", 4096)]),
            "BAKE_SOURCE_SET": AttributeSpec(
                key="BAKE_SOURCE_SET",
                label="Bake Source",
                kind="action",
                choices=[
                    ("Set From Selection", "set_bake_source_from_selection", "Set."),
                    ("Select", "select_bake_source", "Select.", "select"),
                    ("Clear", "clear_bake_source", "Clear.", "clear"),
                ],
            ),
            "HIGH_SUFFIX": choice("HIGH_SUFFIX", [("_source", "_source")]),
            "LOW_SUFFIX": choice("LOW_SUFFIX", [("(none)", "")]),
            "SUFFIX_INCLUDE_CHILDREN": flag("SUFFIX_INCLUDE_CHILDREN"),
            "MAP_NORMAL": flag("MAP_NORMAL"),
            "MAP_AO": flag("MAP_AO"),
            "MAP_CURVATURE": flag("MAP_CURVATURE"),
        }

    class _Engine(_FakeMarmoset):
        TEMPLATE_DIR = Path(template_dir)

        @classmethod
        def params_registry(cls):
            return _MarmosetRegistry

    tk = _toolkit(has_set=has_set)
    tk.MarmosetBridge = _Engine
    return tk


class TestMarmosetBridgePanelLoads(unittest.TestCase):
    """The panel built through a real (offscreen) Switchboard over the fake
    toolkit: its rows, its Bake Source buttons, the suffix greying on real
    widgets, and the window following the active template's rows."""

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
        self.templates = Path(tempfile.mkdtemp(prefix="marmoset_panel_test_"))
        self.addCleanup(shutil.rmtree, self.templates, True)
        for stem, body in _TEMPLATES.items():
            (self.templates / f"{stem}.py").write_text(body, encoding="utf-8")

    def _load(self, has_set=False):
        from uitk import Switchboard

        sb = Switchboard(ui_source=str(UI_PATH), slot_source=MarmosetBridgeSlots)
        sb.tk = _qt_toolkit(self.templates, has_set)  # before any panel is built
        ui = sb.get_ui("marmoset_bridge")
        slots = sb.get_slots_instance(ui)
        self.assertIsInstance(slots, MarmosetBridgeSlots)
        return ui, slots

    def test_the_panel_builds_its_rows_and_opens_on_the_bake(self):
        ui, slots = self._load()
        self.assertIsInstance(slots.peek_bridge(), _FakeMarmoset)
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "marmoset_bridge")
        slots._populate_template_combo(ui.cmb000)  # cmb000 fills on first show
        self.assertEqual(slots._selected_template_mode(), BAKE_ROUNDTRIP)
        self.assertTrue(set(SUFFIX_KEYS) <= set(slots._param_widgets))

    def test_the_bake_source_buttons_reach_the_bridge_base(self):
        """An action id with no same-named method is disabled at build: every
        button here is live, so the registry's ids are the base's methods."""
        _ui, slots = self._load()
        buttons = slots._param_widgets["BAKE_SOURCE_SET"]._action_buttons
        self.assertEqual(
            set(buttons),
            {
                "set_bake_source_from_selection",
                "select_bake_source",
                "clear_bake_source",
            },
        )
        for action_id, button in buttons.items():
            with self.subTest(action=action_id):
                self.assertTrue(button.isEnabled())

    def test_a_defined_set_greys_the_real_suffix_rows(self):
        _ui, slots = self._load(has_set=True)
        slots._refresh_param_enablement()
        for key in SUFFIX_KEYS:
            with self.subTest(row=key):
                self.assertFalse(slots._param_widgets[key].isEnabled())
                self.assertIn("Bake Source set", slots._param_rows[key].toolTip())
        slots.tk.BakeSourceSet.exists.return_value = False
        slots._refresh_param_enablement()
        for key in SUFFIX_KEYS:
            with self.subTest(row=key):
                self.assertTrue(slots._param_widgets[key].isEnabled())
                self.assertEqual(slots._param_rows[key].toolTip(), "")

    def test_the_window_follows_the_templates_rows(self):
        """Switching templates hides/shows rows and the window follows. Moved
        from mayatk's ``TestMarmosetBridgeUiResize``: the panel loads the way a
        host shows it (``loaded_ui``, then ``show()`` runs its inits)."""
        from uitk import Switchboard

        QtWidgets = self.QtWidgets
        sb = Switchboard(ui_source=str(UI_PATH), slot_source=MarmosetBridgeSlots)
        sb.tk = _qt_toolkit(self.templates)
        ui = sb.loaded_ui.marmoset_bridge
        ui.restore_window_size = False
        ui.show()
        self.addCleanup(ui.close)
        QtWidgets.QApplication.processEvents()
        cmb = ui.cmb000

        def index_for_stem(stem):
            for i in range(cmb.count()):
                data = cmb.itemData(i)
                if isinstance(data, (tuple, list)) and data[0] == stem:
                    return i
            raise AssertionError(f"No combo entry for template stem '{stem}'.")

        cmb.setCurrentIndex(index_for_stem("bake"))
        QtWidgets.QApplication.processEvents()
        ui.resize(ui.width(), 800)
        QtWidgets.QApplication.processEvents()
        height_many = ui.height()

        cmb.setCurrentIndex(index_for_stem("import"))
        for _ in range(5):
            QtWidgets.QApplication.processEvents()
        height_few = ui.height()
        self.assertLess(
            height_few,
            height_many,
            f"Window did not shrink: bake @ {height_many}px -> import @ {height_few}px",
        )


# ---------------------------------------------------------------------------
# In Maya: the real mtk
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestMarmosetBridgePanelInMaya(unittest.TestCase):
    """The panel's host calls against the real ``mtk`` on a real scene. Built
    with ``__new__`` like the unit cases: the panel's ``__init__`` builds Qt rows,
    which a batch mayapy cannot host (``_host.qt_widgets_available``)."""

    def setUp(self):
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)

    def test_the_panel_reads_mayatks_engine_registry_templates_and_modes(self):
        slots = _stub(tk=self.mtk)
        engine = self.mtk.MarmosetBridge
        self.assertIs(slots.bridge_class, engine)
        registry = engine.params_registry()
        self.assertIs(slots.params_module, registry)
        self.assertTrue((slots.template_dir / "bake.py").is_file())
        modes = slots.list_template_modes()
        self.assertIn(BAKE_ROUNDTRIP, modes)
        self.assertEqual(
            modes[slots.select_initial_template_index(modes)], BAKE_ROUNDTRIP
        )
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "marmoset_bridge")

    def test_the_rows_the_panel_drives_are_the_registrys(self):
        """``set_param_enabled`` ignores an unknown key, so a suffix key renamed in
        the registry would silently stay live; an action id with no method is a
        dead button."""
        params = self.mtk.MarmosetBridge.params_registry().PARAMS
        for key in SUFFIX_KEYS:
            self.assertIn(key, params)
        for choice in params["BAKE_SOURCE_SET"].choices:
            with self.subTest(action=choice[1]):
                self.assertTrue(callable(getattr(MarmosetBridgeSlots, choice[1], None)))

    def test_the_scene_set_greys_the_suffix_rows_and_clearing_frees_them(self):
        cmds = self.cmds
        cube = cmds.ls(cmds.polyCube(name="marmosetPanelSource")[0], long=True)[0]
        slots = _stub(tk=self.mtk)
        cmds.select(cube, replace=True)
        slots.set_bake_source_from_selection()
        self.assertTrue(self.mtk.BakeSourceSet.exists())
        self.assertTrue(all(not slots.enabled[k][0] for k in SUFFIX_KEYS))
        self.assertIn(
            "Bake sends now export it as the bake source",
            slots._bridge.logger.said("info")[0],
        )
        slots.clear_bake_source()
        self.assertFalse(self.mtk.BakeSourceSet.exists())
        self.assertEqual(slots.enabled, {key: (True, "") for key in SUFFIX_KEYS})
        self.assertTrue(cmds.objExists(cube))

    def test_an_empty_selection_sends_nothing(self):
        self.cmds.polyCube(name="marmosetPanelIdle")
        self.cmds.select(clear=True)
        slots = _stub(tk=self.mtk)
        slots.b000()
        self.assertIsNone(slots._bridge.sent)
        self.assertIn("Nothing selected", slots._bridge.logger.said("warning")[0])


if __name__ == "__main__":
    unittest.main()
