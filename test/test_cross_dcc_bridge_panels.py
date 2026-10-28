#!/usr/bin/python
# coding=utf-8
"""The cross-DCC send pair: Blender Bridge (a Maya tool) and Maya Bridge (a
Blender tool), each one Slots class on ``HostBridge``.

Each library ships the bridge named after its TARGET app, so the two tools never
share a host: ``BlenderBridgeSlots`` (``slots/tools/blender_bridge.py``) drives
``mtk.BlenderBridge``, ``MayaBridgeSlots`` (``slots/tools/maya_bridge.py``) drives
``btk.MayaBridge``, and ``tentacle.slots.tools.HOSTS`` registers each on its one
host. Both reach the host only through ``self.tk``: the engine (its registry,
template folder and ``(template, mode)`` list), ``BridgeHost`` for the Scope, and
(Blender Bridge's save dialog) ``EnvUtils`` for the scene's name. A fake toolkit
stands in for ``mtk`` / ``btk`` and records what each panel asks of it.

The unit cases run each panel's methods on an instance never built (``__new__``);
then each loads for real through an offscreen Switchboard over the fake toolkit,
and in Maya the Blender Bridge drives the real ``mtk`` (no Blender launches: the
engine's send is stood in for). The engines' own side is the libraries'
(``test_blender_bridge.py`` in mayatk, ``test_maya_bridge.py`` in blendertk).
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
from tentacle.slots.tools.blender_bridge import BlenderBridgeSlots
from tentacle.slots.tools.maya_bridge import MayaBridgeSlots

UI_DIR = Path(tentacle.__file__).resolve().parent / "ui" / "tools"


# ---------------------------------------------------------------------------
# The fake toolkit
# ---------------------------------------------------------------------------


class _Log:
    """A bridge logger that keeps what it was told, by level."""

    def __init__(self):
        self.records = []

    def __getattr__(self, level):  # info / warning / error / success / the redirect
        if level.startswith("__"):
            raise AttributeError(level)
        return lambda msg="", *a, **k: self.records.append((level, str(msg)))

    def said(self, level):
        return [msg for lvl, msg in self.records if lvl == level]


class _Registry:
    """The engine's parameter registry (a ``uitk.bridge.ParamRegistry``)."""

    PARAMS = {"SCOPE": None, "CLEAR_SCENE": None}


class _BlenderEngine:
    """``mtk.BlenderBridge``'s surface: a script-launch engine with blocking modes.

    ``bake_lightmaps`` derives its artifact (``BRIDGE_OUTPUT = auto``),
    ``save_blend`` asks for it, ``save_usd`` declares an extension the engine
    cannot write.
    """

    TEMPLATE_DIR = Path("templates")
    save_extensions = (".blend", ".json")
    run_spec = types.SimpleNamespace(modes=("save_as", "round_trip"))
    DECLARED = {
        "import": {},
        "bake_lightmaps": {
            "BRIDGE_OUTPUT": "auto",
            "BRIDGE_OUTPUT_EXT": ".lightmaps.json",
            "BRIDGE_TIMEOUT": 3600.0,
        },
        "save_blend": {},
        "save_usd": {"BRIDGE_OUTPUT_EXT": ".usd"},
    }
    NOT_FOUND = "Blender executable not found."

    def __init__(self):
        self.logger = _Log()
        self.app_path = "C:/Blender/blender.exe"
        self.app_spec = types.SimpleNamespace(not_found_message=self.NOT_FOUND)
        self.calls = []

    @classmethod
    def params_registry(cls):
        return _Registry

    @classmethod
    def list_template_modes(cls):
        return [
            ("import", "send_to"),
            ("bake_lightmaps", "round_trip"),
            ("save_blend", "save_as"),
        ]

    @staticmethod
    def template_path(stem):
        return Path("templates") / f"{stem}.py"

    @classmethod
    def template_output_mode(cls, path):
        return cls.DECLARED[Path(path).stem].get("BRIDGE_OUTPUT", "prompt")

    @classmethod
    def template_output_ext(cls, path):
        return cls.DECLARED[Path(path).stem].get(
            "BRIDGE_OUTPUT_EXT", cls.save_extensions[0]
        )

    @classmethod
    def template_timeout(cls, path):
        return cls.DECLARED[Path(path).stem].get("BRIDGE_TIMEOUT")

    def default_output_path(self, template):
        return f"C:/temp/{template}.lightmaps.json"

    def send(self, **kwargs):
        self.calls.append(("send", kwargs))
        return {}

    def save_as(self, out_path, **kwargs):
        self.calls.append(("save_as", out_path, kwargs))
        return {"output": out_path}

    def round_trip(self, **kwargs):
        self.calls.append(("round_trip", kwargs))
        return {"output": kwargs["out"], "reassembled": ["|a", "|b"]}


class _MayaEngine(_BlenderEngine):
    """``btk.MayaBridge``'s surface: one interactive import template."""

    save_extensions = (".ma", ".mb")
    run_spec = types.SimpleNamespace(modes=("save_as",))
    NOT_FOUND = "Maya executable not found."

    @classmethod
    def list_template_modes(cls):
        return [("import", "send_to")]


def _toolkit(name):
    """``mtk`` / ``btk`` as the panels reach them: by name, nothing else. Each
    library carries only the engine for the OTHER app."""
    tk = types.SimpleNamespace(
        __name__=name,
        BridgeHost=mock.MagicMock(name="BridgeHost"),
        EnvUtils=mock.MagicMock(name="EnvUtils"),
    )
    if name == "mayatk":
        tk.BlenderBridge = _BlenderEngine
    else:
        tk.MayaBridge = _MayaEngine
    return tk


#: The two tools: (Slots class, its one host's toolkit name, its engine, button).
TOOLS = (
    (BlenderBridgeSlots, "mayatk", _BlenderEngine, "Send to Blender"),
    (MayaBridgeSlots, "blendertk", _MayaEngine, "Send to Maya"),
)


def _stub(cls, params=None, pair=("import", "send_to"), objects=("|a",)):
    """A *cls* panel never built, over the attributes its methods read; the
    Scope resolves to *objects* and ships them as they are."""
    _cls, host, engine, _label = next(t for t in TOOLS if t[0] is cls)
    slots = cls.__new__(cls)
    slots.sb = mock.MagicMock(name="switchboard")
    slots.sb.tk = _toolkit(host)
    slots._bridge = engine()
    slots._output_dir_edit = None
    slots._selected_template_mode = lambda: pair
    slots.collect_param_values = lambda: dict(params or {})
    slots.resolved_output_dir = lambda: ""
    bridge_host = slots.sb.tk.BridgeHost
    bridge_host.resolve_scope.return_value = list(objects)
    bridge_host.scope_closure.side_effect = lambda found, p: list(found)
    return slots


# ---------------------------------------------------------------------------
# Shape and engine
# ---------------------------------------------------------------------------


class TestCrossDccBridgeShape(unittest.TestCase):
    def test_each_is_one_class_on_the_bridge_base(self):
        for cls, _host, _engine, _label in TOOLS:
            with self.subTest(tool=cls.__name__):
                self.assertEqual(cls.__bases__, (HostBridge,))
                self.assertFalse(cls.REQUIRE_OUTPUT_DIR)
                self.assertEqual(cls.LOG_TAG, cls.UI_NAME)

    def test_each_is_named_after_its_target_app(self):
        self.assertEqual(BlenderBridgeSlots.UI_NAME, "blender_bridge")
        self.assertEqual(MayaBridgeSlots.UI_NAME, "maya_bridge")
        self.assertEqual(BlenderBridgeSlots.HELP_SPEC["title"], "Blender Bridge")
        self.assertEqual(MayaBridgeSlots.HELP_SPEC["title"], "Maya Bridge")

    def test_the_help_names_the_button_the_ui_shows(self):
        for cls, _host, _engine, label in TOOLS:
            with self.subTest(tool=cls.__name__):
                root = ET.parse(UI_DIR / f"{cls.UI_NAME}.ui").getroot()
                text = root.find(
                    ".//widget[@name='b000']/property[@name='text']/string"
                ).text
                self.assertEqual(text, label)
                self.assertIn(f"<b>{label}</b>", " ".join(cls.HELP_SPEC["steps"]))


class TestCrossDccBridgeAsksItsHost(unittest.TestCase):
    def test_the_engine_is_the_hosts_bridge_to_the_other_app(self):
        for cls, _host, engine, _label in TOOLS:
            with self.subTest(tool=cls.__name__):
                slots = _stub(cls)
                self.assertIs(slots.bridge_class, engine)
                self.assertIsInstance(slots.make_bridge(), engine)
                self.assertIs(slots.params_module, _Registry)
                self.assertEqual(slots.template_dir, engine.TEMPLATE_DIR)
                self.assertEqual(
                    slots.list_template_modes(), engine.list_template_modes()
                )

    def test_presets_stay_where_each_host_kept_them(self):
        self.assertEqual(
            _stub(BlenderBridgeSlots).PRESETS_ROOT, Path("mayatk") / "blender_bridge"
        )
        self.assertEqual(
            _stub(MayaBridgeSlots).PRESETS_ROOT, Path("blendertk") / "maya_bridge"
        )

    def test_the_scope_resolves_and_closes_through_the_host(self):
        for cls, _host, _engine, _label in TOOLS:
            with self.subTest(tool=cls.__name__):
                slots = _stub(cls, objects=["|grp"])
                params = {"SCOPE": "selected"}
                self.assertEqual(slots.scoped_objects(params), ["|grp"])
                host = slots.tk.BridgeHost
                host.resolve_scope.assert_called_once_with("selected", slots._bridge)
                host.scope_closure.assert_called_once_with(["|grp"], params)


# ---------------------------------------------------------------------------
# b000: the interactive send (both)
# ---------------------------------------------------------------------------


class TestCrossDccBridgeSend(unittest.TestCase):
    def test_sends_the_scope_with_the_chosen_template(self):
        for cls, _host, _engine, _label in TOOLS:
            with self.subTest(tool=cls.__name__):
                params = {"SCOPE": "selected", "CLEAR_SCENE": True}
                slots = _stub(cls, params=params, objects=["|a", "|b"])
                slots.b000()
                self.assertEqual(
                    slots._bridge.calls,
                    [
                        (
                            "send",
                            {
                                "objects": ["|a", "|b"],
                                "template": "import",
                                "mode": "send_to",
                                "params": params,
                            },
                        )
                    ],
                )
                self.assertIn(
                    "--- import (send_to) on 2 object(s) ---",
                    slots._bridge.logger.said("info"),
                )
                self.assertEqual(slots._bridge.logger.said("error"), [])

    def test_an_empty_scope_sends_nothing(self):
        for cls, _host, _engine, _label in TOOLS:
            with self.subTest(tool=cls.__name__):
                slots = _stub(cls, objects=[])
                slots.b000()
                self.assertEqual(slots._bridge.calls, [])

    def test_no_template_asks_for_one(self):
        for cls, _host, _engine, _label in TOOLS:
            with self.subTest(tool=cls.__name__):
                slots = _stub(cls, pair=None)
                slots.b000()
                self.assertEqual(slots._bridge.calls, [])
                self.assertIn(
                    "No template chosen", slots._bridge.logger.said("warning")[0]
                )

    def test_a_missing_target_app_shows_the_engines_sentence(self):
        for cls, _host, engine, _label in TOOLS:
            with self.subTest(tool=cls.__name__):
                slots = _stub(cls)
                slots._bridge.app_path = None
                slots.b000()
                self.assertEqual(slots._bridge.calls, [])
                self.assertEqual(slots._bridge.logger.said("error"), [engine.NOT_FOUND])

    def test_an_engine_error_lands_in_the_log(self):
        for cls, _host, _engine, _label in TOOLS:
            with self.subTest(tool=cls.__name__):
                slots = _stub(cls)
                slots._bridge.send = mock.MagicMock(side_effect=RuntimeError("boom"))
                slots.b000()
                error = slots._bridge.logger.said("error")[0]
                self.assertTrue(error.startswith("Bridge raised:"), error)
                self.assertIn("boom", error)

    def test_the_blender_send_reports_progress(self):
        slots = _stub(BlenderBridgeSlots)
        slots.b000()
        slots.sb.progress.assert_called_once_with(
            text="Working: Send to Blender (import)"
        )


# ---------------------------------------------------------------------------
# b000: Blender Bridge's blocking routes (save_as, round_trip)
# ---------------------------------------------------------------------------


class TestBlenderBridgeBlocking(unittest.TestCase):
    def test_an_auto_round_trip_derives_its_artifact_and_reports_the_return(self):
        """The bake: no save dialog, the template's own timeout, and the bindings
        the return leg wired are reported."""
        params = {"SCOPE": "selected"}
        slots = _stub(
            BlenderBridgeSlots, params=params, pair=("bake_lightmaps", "round_trip")
        )
        slots.b000()
        slots.sb.save_file_dialog.assert_not_called()
        self.assertEqual(
            slots._bridge.calls,
            [
                (
                    "round_trip",
                    {
                        "out": "C:/temp/bake_lightmaps.lightmaps.json",
                        "objects": ["|a"],
                        "template": "bake_lightmaps",
                        "params": params,
                        "timeout": 3600.0,
                    },
                )
            ],
        )
        log = slots._bridge.logger
        self.assertIn(
            "Artifact: C:/temp/bake_lightmaps.lightmaps.json", log.said("info")
        )
        self.assertEqual(
            log.said("success"), ["2 lightmap binding(s) wired into the scene."]
        )
        slots.sb.progress.assert_called_once_with(
            text="Working: bake_lightmaps (this can take minutes)"
        )

    def test_a_prompted_save_as_asks_where_seeded_from_the_scene(self):
        slots = _stub(BlenderBridgeSlots, pair=("save_blend", "save_as"))
        slots.tk.EnvUtils.get_env_info.return_value = "C:/work/room.ma"
        slots.sb.save_file_dialog.return_value = "C:/work/room.blend"
        slots.b000()
        slots.tk.EnvUtils.get_env_info.assert_called_once_with("scene")
        kwargs = slots.sb.save_file_dialog.call_args.kwargs
        self.assertEqual(Path(kwargs["start_dir"]), Path("C:/work/room.blend"))
        self.assertEqual(kwargs["file_types"], ["*.blend", "*.json"])
        verb, out_path, sent = slots._bridge.calls[0]
        self.assertEqual((verb, out_path), ("save_as", "C:/work/room.blend"))
        self.assertIsNone(sent["timeout"])
        self.assertEqual(
            slots._bridge.logger.said("success"), ["Wrote C:/work/room.blend"]
        )

    def test_an_unsaved_scene_seeds_untitled(self):
        slots = _stub(BlenderBridgeSlots, pair=("save_blend", "save_as"))
        slots.tk.EnvUtils.get_env_info.return_value = ""
        slots.sb.save_file_dialog.return_value = ""
        slots.b000()
        start = Path(slots.sb.save_file_dialog.call_args.kwargs["start_dir"])
        self.assertEqual(start.name, "untitled.blend")

    def test_a_cancelled_save_dialog_sends_nothing(self):
        slots = _stub(BlenderBridgeSlots, pair=("save_blend", "save_as"))
        slots.tk.EnvUtils.get_env_info.return_value = ""
        slots.sb.save_file_dialog.return_value = None
        slots.b000()
        self.assertEqual(slots._bridge.calls, [])
        self.assertIn("Cancelled.", slots._bridge.logger.said("info"))

    def test_an_extension_the_engine_cannot_write_falls_back(self):
        """``resolve_save_path`` would append ``.blend`` to a ``.usd`` name, so the
        dialog offers what the engine writes and says why."""
        slots = _stub(BlenderBridgeSlots, pair=("save_usd", "save_as"))
        slots.tk.EnvUtils.get_env_info.return_value = "C:/work/room.ma"
        slots.sb.save_file_dialog.return_value = ""
        slots.b000()
        start = Path(slots.sb.save_file_dialog.call_args.kwargs["start_dir"])
        self.assertEqual(start.name, "room.blend")
        self.assertIn(
            "BRIDGE_OUTPUT_EXT '.usd'", slots._bridge.logger.said("warning")[0]
        )

    def test_a_blocking_run_with_no_artifact_is_an_error(self):
        slots = _stub(BlenderBridgeSlots, pair=("bake_lightmaps", "round_trip"))
        slots._bridge.round_trip = mock.MagicMock(return_value=None)
        slots.b000()
        self.assertEqual(
            slots._bridge.logger.said("error"),
            ["bake_lightmaps produced no file -- see the log above."],
        )

    def test_a_mode_the_run_spec_does_not_serve_launches_interactively(self):
        """``send_to`` is the interactive spec's; only the run spec's modes block."""
        slots = _stub(BlenderBridgeSlots, pair=("import", "send_to"))
        slots.b000()
        self.assertEqual([c[0] for c in slots._bridge.calls], ["send"])
        slots.sb.save_file_dialog.assert_not_called()


# ---------------------------------------------------------------------------
# Each panel loaded for real on its host (offscreen Qt, no DCC)
# ---------------------------------------------------------------------------


def _qt_toolkit(name, templates: Path):
    """The fake toolkit, its engine over real templates and a real registry: the
    built panel makes real rows and shows a template's own."""
    from uitk import AttributeSpec, Parameters, ParamRegistry

    class _Rows(ParamRegistry):
        PARAMS = {
            "SCOPE": Parameters.scope_spec(),
            "CLEAR_SCENE": AttributeSpec(
                key="CLEAR_SCENE", label="Clear Scene First", kind="bool", default=False
            ),
            "QUALITY": AttributeSpec(
                key="QUALITY", label="Quality", kind="int", default=1
            ),
        }

    (templates / "import.py").write_text(
        '"""Import the payload."""\nCLEAR = __CLEAR_SCENE__\n', encoding="utf-8"
    )
    (templates / "bake_lightmaps.py").write_text(
        '"""Bake the lightmaps."""\nQUALITY = __QUALITY__\n', encoding="utf-8"
    )
    tk = _toolkit(name)
    base = tk.BlenderBridge if name == "mayatk" else tk.MayaBridge

    class _Engine(base):
        TEMPLATE_DIR = templates

        @classmethod
        def params_registry(cls):
            return _Rows

    if name == "mayatk":
        tk.BlenderBridge = _Engine
    else:
        tk.MayaBridge = _Engine
    return tk


class TestCrossDccBridgePanelsLoad(unittest.TestCase):
    """Each panel built through a real (offscreen) Switchboard over its host's
    fake toolkit: the combo lists the engine's pairs and the rows follow the
    template."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from qtpy import QtWidgets
        except Exception as error:  # noqa: BLE001 - no Qt binding
            raise unittest.SkipTest(f"Qt unavailable: {error}") from error
        from uitk.testing import TestSandbox

        TestSandbox.activate()  # the panels' settings and presets stay off the live stores
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.templates = Path(tempfile.mkdtemp(prefix="cross_dcc_templates_"))
        self.addCleanup(shutil.rmtree, self.templates, True)

    def _load(self, cls, host):
        from uitk import Switchboard

        sb = Switchboard(ui_source=str(UI_DIR / f"{cls.UI_NAME}.ui"), slot_source=cls)
        sb.tk = _qt_toolkit(host, self.templates)  # set before any panel is built
        ui = sb.get_ui(cls.UI_NAME)
        slots = sb.get_slots_instance(ui)
        self.assertIsInstance(slots, cls)
        return ui, slots

    def test_the_blender_bridge_lists_its_engines_templates(self):
        ui, slots = self._load(BlenderBridgeSlots, "mayatk")
        slots._populate_template_combo(ui.cmb000)  # cmb000 fills on first show
        labels = [ui.cmb000.itemText(i) for i in range(ui.cmb000.count())]
        self.assertEqual(
            labels,
            ["import (send_to)", "bake_lightmaps (round_trip)", "save_blend (save_as)"],
        )
        ui.cmb000.setCurrentIndex(0)
        self.assertEqual(slots._relevant_param_keys(), {"CLEAR_SCENE"})
        ui.cmb000.setCurrentIndex(1)
        self.assertEqual(slots._relevant_param_keys(), {"QUALITY"})
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "blender_bridge")
        self.assertEqual(ui.b000.text(), "Send to Blender")

    def test_the_maya_bridge_lists_its_engines_templates(self):
        ui, slots = self._load(MayaBridgeSlots, "blendertk")
        slots._populate_template_combo(ui.cmb000)
        labels = [ui.cmb000.itemText(i) for i in range(ui.cmb000.count())]
        self.assertEqual(labels, ["import (send_to)"])
        ui.cmb000.setCurrentIndex(0)
        self.assertEqual(slots._relevant_param_keys(), {"CLEAR_SCENE"})
        self.assertEqual(slots.PRESETS_ROOT, Path("blendertk") / "maya_bridge")
        self.assertEqual(ui.b000.text(), "Send to Maya")


# ---------------------------------------------------------------------------
# In Maya: the Blender Bridge over the real mtk
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestBlenderBridgePanelInMaya(unittest.TestCase):
    """The Blender Bridge's host calls against the real ``mtk`` on a real scene.
    Built with ``__new__`` (a batch mayapy cannot host the Qt rows ``__init__``
    builds); the engine's send is stood in for, so no Blender launches."""

    def setUp(self):
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _panel(self, **kwargs):
        slots = _stub(BlenderBridgeSlots, **kwargs)
        slots.sb.tk = self.mtk
        slots._bridge = self.mtk.BlenderBridge(blender_path="not-used.exe")
        return slots

    def test_the_panel_reads_mayatks_engine(self):
        slots = self._panel()
        engine = self.mtk.BlenderBridge
        self.assertIs(slots.bridge_class, engine)
        self.assertIs(slots.params_module, engine.params_registry())
        self.assertIn("SCOPE", slots.params_module.PARAMS)
        self.assertTrue((slots.template_dir / "import.py").is_file())
        pairs = dict(slots.list_template_modes())
        self.assertEqual(pairs["import"], "send_to")
        self.assertEqual(pairs["bake_lightmaps"], "round_trip")
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "blender_bridge")

    def test_send_hands_the_selection_to_the_engine(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="blenderPanelCube")[0]
        cmds.polySphere(name="blenderPanelOther")
        cmds.select(cube, replace=True)
        params = {"SCOPE": "selected"}
        slots = self._panel(params=params)
        with mock.patch.object(slots._bridge, "send") as send:
            slots.b000()
        send.assert_called_once_with(
            objects=cmds.ls(cube, long=True),
            template="import",
            mode="send_to",
            params=params,
        )

    def test_the_save_dialog_is_seeded_from_the_scene_name(self):
        tmp = Path(tempfile.mkdtemp(prefix="blender_panel_scene_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        self.cmds.file(rename=str(tmp / "bridgeRoom.ma"))
        slots = self._panel()
        slots.sb.save_file_dialog.return_value = ""
        self.assertEqual(slots._prompt_save_path("import"), "")
        start = Path(slots.sb.save_file_dialog.call_args.kwargs["start_dir"])
        self.assertEqual(start.name, "bridgeRoom.blend")
        # Maya spells the scene path its own way (slashes, case): compare the
        # folder by name, not by spelling.
        self.assertEqual(start.parent.name, tmp.name)


if __name__ == "__main__":
    unittest.main()
