#!/usr/bin/python
# coding=utf-8
"""The Substance Bridge panel's one Slots class.

``SubstanceBridgeSlots`` (``slots/tools/substance_bridge.py``) sits on
``HostBridge`` (``slots/tools/_app_bridge/``) and reaches its host only through
``self.tk``: the engine with its registry, template folder, ``(template, mode)``
list and template metadata (``SubstanceBridge``), the Scope (``BridgeHost``) and
the Bake Source row (``BakeSourceSet``). A fake toolkit stands in for ``mtk`` /
``btk`` and records what the panel asks of it. The shared base's own cases
(Scope, closure, the Bake Source row's three actions) are
``test_unity_bridge_panel.py``'s; these pin what this bridge adds: a template
that exports nothing needs no selection, the Output Dir row starts blank and
clears, and Texture Affix greys while Include Textures is off.

The unit cases run the panel's methods on an instance never built (``__new__``:
the bridge base is a plain class, not a ``QObject``). Then the panel loads for
real through an offscreen Switchboard over a fake engine with a real registry,
and in Maya the same methods drive the real ``mtk`` on a real scene. The engine's
own side is the libraries': ``test_substance_bridge.py`` (mayatk) and
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
from tentacle.slots.tools.substance_bridge import SubstanceBridgeSlots

UI_PATH = (
    Path(tentacle.__file__).resolve().parent / "ui" / "tools" / "substance_bridge.ui"
)
IMPORT = ("import", ptk.SEND_TO)
RENDER = ("render", ptk.SEND_TO)


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

    PARAMS = dict.fromkeys(
        (
            "SCOPE",
            "BAKE_SOURCE_SET",
            "PAINTER_INCLUDE_TEXTURES",
            "PAINTER_TEXTURE_AFFIX",
        )
    )


class _FakeSubstance:
    """The engine surface the panel and its base read."""

    TEMPLATE_DIR = Path("templates")
    APP = types.SimpleNamespace(not_found_message="Substance Painter was not found.")
    #: What ``parse_template`` answers, by template stem (``render`` targets the
    #: project already open in Painter).
    META = {"import": {"EXPORT_FBX": True}, "render": {"EXPORT_FBX": False}}
    #: Every template path the panel asked about (a fresh list per toolkit).
    parsed = []

    def __init__(self):
        self.logger = _Log()
        self.painter_path = "C:/Painter/painter.exe"
        self.sent = None

    @classmethod
    def params_registry(cls):
        return _Registry

    @staticmethod
    def list_template_modes():
        return [
            ("bake_lighting", ptk.SEND_TO),
            IMPORT,
            ("reimport", ptk.SEND_TO),
            RENDER,
        ]

    @classmethod
    def parse_template(cls, template_path):
        cls.parsed.append(Path(template_path))
        return dict(cls.META.get(Path(template_path).stem, {}))

    def send(self, **kwargs):
        self.sent = kwargs
        return {}


def _toolkit(name="mayatk"):
    """``mtk`` / ``btk`` as the panel reaches them: by name, nothing else."""
    engine = type("_Engine", (_FakeSubstance,), {"parsed": []})
    return types.SimpleNamespace(
        __name__=name,
        SubstanceBridge=engine,
        BridgeHost=mock.MagicMock(name="BridgeHost"),
        BakeSourceSet=mock.MagicMock(name="BakeSourceSet"),
    )


def _stub(tk=None, params=None, output_dir="", pair=IMPORT, widgets=None):
    """A panel never built, over the attributes its methods read; the rows it
    greys land in ``slots.enabled`` as ``{key: (enabled, reason)}``."""
    slots = SubstanceBridgeSlots.__new__(SubstanceBridgeSlots)
    slots.sb = mock.MagicMock(name="switchboard")
    slots.sb.tk = tk or _toolkit()
    slots._bridge = _FakeSubstance()
    slots._output_dir_edit = None
    slots._param_widgets = dict(widgets or {})
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


class TestSubstanceBridgeShape(unittest.TestCase):
    def test_one_class_for_both_hosts_on_the_bridge_base(self):
        self.assertEqual(SubstanceBridgeSlots.__bases__, (HostBridge,))
        self.assertEqual(SubstanceBridgeSlots.UI_NAME, "substance_bridge")
        self.assertEqual(SubstanceBridgeSlots.LOG_TAG, "substance_bridge")
        self.assertEqual(SubstanceBridgeSlots.HELP_SPEC["title"], "Substance Bridge")

    def test_the_help_names_the_send_button_the_ui_carries(self):
        root = ElementTree.parse(UI_PATH).getroot()
        button = next(w for w in root.iter("widget") if w.get("name") == "b000")
        label = next(p.find("string").text for p in button if p.get("name") == "text")
        self.assertEqual(label, "Send to Painter")
        self.assertIn(f"<b>{label}</b>", SubstanceBridgeSlots.HELP_SPEC["steps"][-1])

    def test_a_blank_output_dir_is_the_bridges_call_every_session(self):
        """Blank leaves both modes to the bridge (the project cache for the mesh,
        temp for the rest), and the field starts blank each session: a restored
        path would silently outrank that per-run default."""
        self.assertFalse(SubstanceBridgeSlots.OUTPUT_DIR_PERSISTS)
        self.assertEqual(
            set(SubstanceBridgeSlots.TRANSIENT_OUTPUT_MODES),
            {ptk.SEND_TO, ptk.ROUND_TRIP},
        )
        for mode in (ptk.SEND_TO, ptk.ROUND_TRIP):
            with self.subTest(mode=mode):
                slots = _stub()
                self.assertEqual(slots.require_output_dir(mode), "")
                self.assertEqual(slots._bridge.logger.said("error"), [])

    def test_the_output_dir_field_carries_a_clear_button(self):
        """Blank is a real setting here, so the field offers the way back to it
        beside the base's history and browse buttons."""
        edit = mock.MagicMock(name="output_dir_edit")
        _stub()._configure_output_dir_options(edit)
        self.assertIs(edit.option_box.clear_option, True)
        edit.option_box.set_action.assert_called_once()  # the base's browse button


# ---------------------------------------------------------------------------
# What the panel asks of its host
# ---------------------------------------------------------------------------


class TestSubstanceBridgeAsksItsHost(unittest.TestCase):
    def test_the_engine_registry_templates_and_modes_are_the_hosts(self):
        slots = _stub()
        engine = slots.tk.SubstanceBridge
        self.assertIs(slots.bridge_class, engine)
        self.assertIsInstance(slots.make_bridge(), engine)
        self.assertIs(slots.params_module, _Registry)
        self.assertEqual(slots.template_dir, Path("templates"))
        self.assertEqual(slots.list_template_modes(), engine.list_template_modes())

    def test_presets_stay_in_each_hosts_folder(self):
        """Where each host's panel kept them before the move: saved user presets."""
        for name in ("mayatk", "blendertk"):
            with self.subTest(host=name):
                root = _stub(tk=_toolkit(name)).PRESETS_ROOT
                self.assertEqual(root, Path(name) / "substance_bridge")

    def test_the_combo_opens_on_import(self):
        slots = _stub()
        pairs = _FakeSubstance.list_template_modes()
        self.assertEqual(slots.select_initial_template_index(pairs), 1)
        self.assertEqual(slots.select_initial_template_index([RENDER]), 0)


# ---------------------------------------------------------------------------
# Texture Affix follows Include Textures
# ---------------------------------------------------------------------------


class TestSubstanceBridgeTextureAffix(unittest.TestCase):
    def _wired(self, include_on):
        include, affix = mock.MagicMock(name="include"), mock.MagicMock(name="affix")
        slots = _stub(
            widgets={
                "PAINTER_INCLUDE_TEXTURES": include,
                "PAINTER_TEXTURE_AFFIX": affix,
            }
        )
        kinds = slots.sb.KindFactory
        kinds.read_value.return_value = include_on
        slots._wire_texture_affix_dependency()
        return slots, kinds, include

    def test_the_affix_greys_while_include_textures_is_off(self):
        slots, kinds, include = self._wired(include_on=False)
        on, reason = slots.enabled["PAINTER_TEXTURE_AFFIX"]
        self.assertFalse(on)
        self.assertIn("Include Textures", reason)
        kinds.read_value.assert_called_with(include)

    def test_it_follows_the_toggle(self):
        slots, kinds, include = self._wired(include_on=False)
        (widget, sync), _ = kinds.connect_changed.call_args
        self.assertIs(widget, include)
        kinds.read_value.return_value = True
        sync(True)
        self.assertEqual(slots.enabled["PAINTER_TEXTURE_AFFIX"], (True, ""))

    def test_a_registry_without_the_rows_wires_nothing(self):
        slots = _stub(widgets={"PAINTER_INCLUDE_TEXTURES": mock.MagicMock()})
        slots._wire_texture_affix_dependency()
        slots.sb.KindFactory.connect_changed.assert_not_called()
        self.assertEqual(slots.enabled, {})


# ---------------------------------------------------------------------------
# b000: the send
# ---------------------------------------------------------------------------


class TestSubstanceBridgeSend(unittest.TestCase):
    def test_sends_the_scope_with_the_chosen_template_and_mode(self):
        params = {"SCOPE": "selected", "PAINTER_RESOLUTION": 2048}
        slots = _stub(params=params)
        _scoped(slots, ["|pCube1"])
        slots.b000()
        self.assertEqual(
            slots.tk.SubstanceBridge.parsed, [Path("templates") / "import.py"]
        )
        self.assertEqual(
            slots._bridge.sent,
            {
                "objects": ["|pCube1"],
                "template": "import",
                "mode": ptk.SEND_TO,
                "output_dir": "",
                "params": params,
            },
        )
        slots.sb.progress.assert_called_once_with(
            text=f"Working: Substance import ({ptk.SEND_TO})"
        )
        self.assertEqual(slots._bridge.logger.said("error"), [])

    def test_a_template_that_exports_nothing_needs_no_selection(self):
        """``render`` works on the project open in Painter: an empty Scope is no
        reason to stop, nor to warn."""
        slots = _stub(pair=RENDER)
        _scoped(slots, [])
        slots.b000()
        self.assertEqual(slots._bridge.logger.said("warning"), [])
        self.assertEqual(slots._bridge.sent["objects"], [])
        self.assertEqual(slots._bridge.sent["template"], "render")

    def test_an_export_with_nothing_scoped_sends_nothing_and_says_why(self):
        slots = _stub(pair=IMPORT)
        _scoped(slots, [])
        slots.b000()
        self.assertIsNone(slots._bridge.sent)
        self.assertTrue(slots._bridge.logger.said("warning"))

    def test_no_template_sends_nothing(self):
        slots = _stub(pair=None)
        slots.b000()
        self.assertIsNone(slots._bridge.sent)
        self.assertIn("No template chosen", slots._bridge.logger.said("warning")[0])
        slots.tk.BridgeHost.resolve_scope.assert_not_called()

    def test_without_painter_the_apps_own_sentence_is_logged(self):
        slots = _stub()
        _scoped(slots, ["|a"])
        slots._bridge.painter_path = None
        slots.b000()
        self.assertIsNone(slots._bridge.sent)
        self.assertEqual(
            slots._bridge.logger.said("error"),
            [_FakeSubstance.APP.not_found_message],
        )

    def test_a_named_output_dir_wins(self):
        slots = _stub(output_dir="C:/handoff")
        _scoped(slots, ["|a"])
        slots.b000()
        self.assertEqual(slots._bridge.sent["output_dir"], "C:/handoff")

    def test_an_engine_error_lands_in_the_log(self):
        slots = _stub()
        _scoped(slots, ["|a"])
        slots._bridge.send = mock.MagicMock(side_effect=RuntimeError("no painter"))
        slots.b000()
        error = slots._bridge.logger.said("error")[0]
        self.assertTrue(error.startswith("Bridge raised:"), error)
        self.assertIn("no painter", error)


# ---------------------------------------------------------------------------
# The panel loaded for real (offscreen Qt, no DCC)
# ---------------------------------------------------------------------------

_TEMPLATES = {
    "import": '"""Open the selection in a new Painter project."""\n'
    "ARGS = (__SCOPE__, __BAKE_SOURCE_SET__, __PAINTER_INCLUDE_TEXTURES__, "
    "__PAINTER_TEXTURE_AFFIX__)\n",
    "render": '"""Render the open project."""\nEXPORT_FBX = False\n',
}


def _qt_toolkit(template_dir):
    """The fake toolkit, its engine carrying a real registry of the rows the
    panel acts on (each library's own is its ``substance_bridge/parameters.py``)
    and a real template folder: the built panel makes real widgets from them."""
    from uitk import AttributeSpec, Parameters, ParamRegistry

    class _SubstanceRegistry(ParamRegistry):
        PARAMS = {
            "SCOPE": Parameters.scope_spec(),
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
            "PAINTER_INCLUDE_TEXTURES": AttributeSpec(
                key="PAINTER_INCLUDE_TEXTURES",
                label="Include Textures",
                kind="bool",
                default=True,
            ),
            "PAINTER_TEXTURE_AFFIX": AttributeSpec(
                key="PAINTER_TEXTURE_AFFIX",
                label="Texture Affix",
                kind="affix",
                default={"text": "", "mode": "auto"},
            ),
        }

    tk = _toolkit()
    engine = tk.SubstanceBridge
    engine.TEMPLATE_DIR = Path(template_dir)
    engine.params_registry = classmethod(lambda cls: _SubstanceRegistry)
    return tk


class TestSubstanceBridgePanelLoads(unittest.TestCase):
    """The panel built through a real (offscreen) Switchboard over the fake
    toolkit: its rows, its Output Dir row, and the Texture Affix row following
    the Include Textures toggle on real widgets."""

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

    def setUp(self):
        self.templates = Path(tempfile.mkdtemp(prefix="substance_panel_test_"))
        self.addCleanup(shutil.rmtree, self.templates, True)
        for stem, body in _TEMPLATES.items():
            (self.templates / f"{stem}.py").write_text(body, encoding="utf-8")

    def _load(self):
        from uitk import Switchboard

        sb = Switchboard(ui_source=str(UI_PATH), slot_source=SubstanceBridgeSlots)
        sb.tk = _qt_toolkit(self.templates)  # before any panel is built
        ui = sb.get_ui("substance_bridge")
        slots = sb.get_slots_instance(ui)
        self.assertIsInstance(slots, SubstanceBridgeSlots)
        return ui, slots

    def test_the_panel_builds_and_opens_on_import(self):
        ui, slots = self._load()
        self.assertIsInstance(slots.peek_bridge(), _FakeSubstance)
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "substance_bridge")
        slots._populate_template_combo(ui.cmb000)  # cmb000 fills on first show
        self.assertEqual(slots._selected_template_mode(), IMPORT)
        self.assertEqual(slots.resolved_output_dir(), "")

    def test_the_affix_row_follows_include_textures(self):
        _ui, slots = self._load()
        affix = slots._param_widgets["PAINTER_TEXTURE_AFFIX"]
        row = slots._param_rows["PAINTER_TEXTURE_AFFIX"]
        self.assertTrue(affix.isEnabled())  # Include Textures defaults on
        slots._write_param("PAINTER_INCLUDE_TEXTURES", False)
        self.assertFalse(affix.isEnabled())
        self.assertIn("Include Textures", row.toolTip())
        slots._write_param("PAINTER_INCLUDE_TEXTURES", True)
        self.assertTrue(affix.isEnabled())
        self.assertEqual(row.toolTip(), "")


# ---------------------------------------------------------------------------
# In Maya: the real mtk
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestSubstanceBridgePanelInMaya(unittest.TestCase):
    """The panel's host calls against the real ``mtk`` on a real scene. Built
    with ``__new__`` like the unit cases: the panel's ``__init__`` builds Qt rows,
    which a batch mayapy cannot host (``_host.qt_widgets_available``)."""

    def setUp(self):
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _panel(self, pair=IMPORT):
        slots = _stub(tk=self.mtk, pair=pair)
        slots._bridge.painter_path = None  # never launch Painter from a test
        return slots

    def test_the_panel_reads_mayatks_engine_registry_templates_and_modes(self):
        slots = self._panel()
        engine = self.mtk.SubstanceBridge
        self.assertIs(slots.bridge_class, engine)
        self.assertIs(slots.params_module, engine.params_registry())
        self.assertTrue((slots.template_dir / "import.py").is_file())
        modes = slots.list_template_modes()
        self.assertEqual(modes[slots.select_initial_template_index(modes)], IMPORT)
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "substance_bridge")

    def test_the_rows_the_panel_drives_are_the_registrys(self):
        params = self.mtk.SubstanceBridge.params_registry().PARAMS
        for key in ("PAINTER_INCLUDE_TEXTURES", "PAINTER_TEXTURE_AFFIX"):
            self.assertIn(key, params)
        for choice in params["BAKE_SOURCE_SET"].choices:
            with self.subTest(action=choice[1]):
                self.assertTrue(
                    callable(getattr(SubstanceBridgeSlots, choice[1], None))
                )

    def test_render_reads_its_template_and_needs_no_selection(self):
        """The real ``render.py`` exports no FBX: with nothing selected the send
        goes on (to the missing-Painter stop here) without a scope warning."""
        self.cmds.select(clear=True)
        slots = self._panel(pair=RENDER)
        slots.b000()
        self.assertEqual(slots._bridge.logger.said("warning"), [])
        self.assertEqual(
            slots._bridge.logger.said("error"), [_FakeSubstance.APP.not_found_message]
        )

    def test_import_with_nothing_selected_stops_and_says_why(self):
        self.cmds.polyCube(name="substancePanelIdle")
        self.cmds.select(clear=True)
        slots = self._panel(pair=IMPORT)
        slots.b000()
        self.assertIn("Nothing selected", slots._bridge.logger.said("warning")[0])
        self.assertEqual(slots._bridge.logger.said("error"), [])


if __name__ == "__main__":
    unittest.main()
