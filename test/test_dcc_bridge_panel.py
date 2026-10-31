#!/usr/bin/python
# coding=utf-8
"""The DCC Bridge (``slots/tools/dcc_bridge.py``): one Slots class on ``HostBridge``
that sends to the other DCC -- the Blender Bridge in Maya, the Maya Bridge in
Blender.

Each library ships the bridge named after its TARGET app, so the engine is the
host's bridge to the other app (``EnvUtils.foreign_scene_bridge``): mayatk's
``BlenderBridge``, blendertk's ``MayaBridge``. The panel reaches the host only
through ``self.tk``: the engine (its registry, template folder, ``(template,
mode)`` list and app name), ``BridgeHost`` for the Scope, and (the save dialog)
``EnvUtils`` for the scene's name. A fake toolkit per host stands in for ``mtk`` /
``btk`` and records what the panel asks of it.

The unit cases run the panel's methods on an instance never built (``__new__``);
then it loads for real through an offscreen Switchboard over each host's fake
toolkit, and in Maya it drives the real ``mtk`` (no Blender launches: the
engine's send is stood in for). The engines' own side is the libraries'
(``test_blender_bridge.py`` in mayatk, ``test_maya_bridge.py`` in blendertk).
"""

import os
import shutil
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots.tools._app_bridge.host_bridge import HostBridge
from tentacle.slots.tools.dcc_bridge import DccBridgeSlots

UI_FILE = Path(tentacle.__file__).resolve().parent / "ui" / "tools" / "dcc_bridge.ui"


# ---------------------------------------------------------------------------
# The fake toolkits
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


class _Engine:
    """What both hosts' bridges to the other app share: a script-launch engine
    over a template folder, with an app name and a run spec."""

    APP = ""
    TEMPLATE_DIR = Path("templates")
    save_extensions = ()
    run_spec = types.SimpleNamespace(modes=("save_as",))

    def __init__(self):
        self.logger = _Log()
        self.app_path = f"C:/{self.APP}/{self.APP.lower()}.exe"
        self.app_spec = types.SimpleNamespace(not_found_message=self.not_found())
        self.calls = []

    @classmethod
    def not_found(cls):
        return f"{cls.APP} executable not found."

    @classmethod
    def params_registry(cls):
        return _Registry

    @classmethod
    def list_template_modes(cls):
        return [("import", "send_to")]

    def send(self, **kwargs):
        self.calls.append(("send", kwargs))
        return {}

    def save_as(self, out_path, **kwargs):
        self.calls.append(("save_as", out_path, kwargs))
        return {"output": out_path}

    def round_trip(self, **kwargs):
        self.calls.append(("round_trip", kwargs))
        return {"output": kwargs["out"], "reassembled": ["|a", "|b"]}


class _BlenderEngine(_Engine):
    """``mtk.BlenderBridge``'s surface: blocking modes read off each template's
    declarations. ``bake_lightmaps`` derives its artifact (``BRIDGE_OUTPUT =
    auto``), ``save_blend`` asks for it, ``save_usd`` declares an extension the
    engine cannot write."""

    APP = "Blender"
    spec = types.SimpleNamespace(app=types.SimpleNamespace(name="Blender"))
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


class _MayaEngine(_Engine):
    """``btk.MayaBridge``'s surface: one interactive import template; its run spec
    serves ``save_as``, but it reads no template declarations."""

    APP = "Maya"
    spec = types.SimpleNamespace(app=types.SimpleNamespace(name="Maya"))
    save_extensions = (".ma", ".mb")


#: Per host: (its toolkit's name, its bridge to the other app, the Send label).
HOSTS = {
    "maya": ("mayatk", _BlenderEngine, "Send to Blender"),
    "blender": ("blendertk", _MayaEngine, "Send to Maya"),
}


#: What the panel may ask ``EnvUtils``: names BOTH libraries serve, so a call
#: only one host answers fails here instead of in the other host's session.
ENV_UTILS_ASKED = ("foreign_scene_bridge", "saved_scene_path")


def _toolkit(host, engine=None):
    """``mtk`` / ``btk`` as the panel reaches them: by name, nothing else. Each
    library's bridge to the other app is the one ``EnvUtils`` names."""
    name, default_engine, _label = HOSTS[host]
    tk = types.SimpleNamespace(
        __name__=name,
        BridgeHost=mock.MagicMock(name="BridgeHost"),
        EnvUtils=mock.MagicMock(name="EnvUtils", spec=list(ENV_UTILS_ASKED)),
    )
    tk.EnvUtils.foreign_scene_bridge.return_value = engine or default_engine
    return tk


def _stub(host, params=None, pair=("import", "send_to"), objects=("|a",)):
    """The panel in *host*, never built, over the attributes its methods read;
    the Scope resolves to *objects* and ships them as they are."""
    slots = DccBridgeSlots.__new__(DccBridgeSlots)
    slots.sb = mock.MagicMock(name="switchboard")
    slots.sb.tk = _toolkit(host)
    slots._bridge = HOSTS[host][1]()
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


class TestDccBridgeShape(unittest.TestCase):
    def test_one_class_on_the_bridge_base(self):
        self.assertEqual(DccBridgeSlots.__bases__, (HostBridge,))
        self.assertFalse(DccBridgeSlots.REQUIRE_OUTPUT_DIR)
        self.assertEqual(DccBridgeSlots.UI_NAME, "dcc_bridge")
        self.assertEqual(DccBridgeSlots.LOG_TAG, DccBridgeSlots.UI_NAME)

    def test_the_ui_names_no_app(self):
        """The ``.ui`` is shared: what names the target is set from the engine."""
        root = ET.parse(UI_FILE).getroot()
        text = " ".join(s.text or "" for s in root.iter("string"))
        for app in ("Blender", "Maya"):
            self.assertNotIn(f"Send to {app}", text)
        self.assertNotIn("BLENDER BRIDGE", text)
        self.assertNotIn("MAYA BRIDGE", text)


class TestDccBridgeAsksItsHost(unittest.TestCase):
    def test_the_engine_is_the_hosts_bridge_to_the_other_app(self):
        for host, (_name, engine, _label) in HOSTS.items():
            with self.subTest(host=host):
                slots = _stub(host)
                self.assertIs(slots.bridge_class, engine)
                self.assertIsInstance(slots.make_bridge(), engine)
                self.assertIs(slots.params_module, _Registry)
                self.assertEqual(slots.template_dir, engine.TEMPLATE_DIR)
                self.assertEqual(
                    slots.list_template_modes(), engine.list_template_modes()
                )
                self.assertEqual(slots.target_app, engine.APP)

    def test_what_the_panel_asks_envutils_both_libraries_serve(self):
        """``ENV_UTILS_ASKED`` specs the fake, so it must hold of both real
        libraries: each name callable on ``mtk.EnvUtils`` and ``btk.EnvUtils``
        (both import without their host)."""
        mono = Path(tentacle.__file__).resolve().parents[2]
        for repo in ("mayatk", "blendertk"):
            path = str(mono / repo)
            if path not in sys.path:
                sys.path.insert(0, path)
        import blendertk
        import mayatk

        for lib in (mayatk, blendertk):
            for name in ENV_UTILS_ASKED:
                with self.subTest(lib=lib.__name__, name=name):
                    self.assertTrue(callable(getattr(lib.EnvUtils, name, None)))

    def test_presets_stay_where_each_host_kept_them(self):
        """Under the per-host panel names the bridges had before they merged."""
        self.assertEqual(_stub("maya").PRESETS_ROOT, Path("mayatk") / "blender_bridge")
        self.assertEqual(
            _stub("blender").PRESETS_ROOT, Path("blendertk") / "maya_bridge"
        )

    def test_the_scope_resolves_and_closes_through_the_host(self):
        for host in HOSTS:
            with self.subTest(host=host):
                slots = _stub(host, objects=["|grp"])
                params = {"SCOPE": "selected"}
                self.assertEqual(slots.scoped_objects(params), ["|grp"])
                bridge_host = slots.tk.BridgeHost
                bridge_host.resolve_scope.assert_called_once_with(
                    "selected", slots._bridge
                )
                bridge_host.scope_closure.assert_called_once_with(["|grp"], params)


class TestDccBridgeHelp(unittest.TestCase):
    """Each host reads its own bridge's help: the title, the Send button and the
    sections of the templates its engine ships."""

    def test_the_help_names_the_target_and_its_send_button(self):
        for host, (_name, engine, label) in HOSTS.items():
            with self.subTest(host=host):
                spec = _stub(host).help_spec()
                self.assertEqual(spec["title"], f"{engine.APP} Bridge")
                self.assertIn(f"<b>{label}</b>", " ".join(spec["steps"]))
                other = "Maya" if engine.APP == "Blender" else "Blender"
                self.assertNotIn(f"fresh {other}", spec["body"])

    def test_the_bake_section_shows_where_the_engine_ships_the_bake(self):
        titles = {
            host: [title for title, _ in _stub(host).help_spec()["sections"]]
            for host in HOSTS
        }
        bake = DccBridgeSlots.TEMPLATE_HELP["bake_lightmaps"][0]
        self.assertIn(bake, titles["maya"])
        self.assertNotIn(bake, titles["blender"])


# ---------------------------------------------------------------------------
# b000: the interactive send (both hosts)
# ---------------------------------------------------------------------------


class TestDccBridgeSend(unittest.TestCase):
    def test_sends_the_scope_with_the_chosen_template(self):
        for host in HOSTS:
            with self.subTest(host=host):
                params = {"SCOPE": "selected", "CLEAR_SCENE": True}
                slots = _stub(host, params=params, objects=["|a", "|b"])
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
        for host in HOSTS:
            with self.subTest(host=host):
                slots = _stub(host, objects=[])
                slots.b000()
                self.assertEqual(slots._bridge.calls, [])

    def test_no_template_asks_for_one(self):
        for host in HOSTS:
            with self.subTest(host=host):
                slots = _stub(host, pair=None)
                slots.b000()
                self.assertEqual(slots._bridge.calls, [])
                self.assertIn(
                    "No template chosen", slots._bridge.logger.said("warning")[0]
                )

    def test_a_missing_target_app_shows_the_engines_sentence(self):
        for host, (_name, engine, _label) in HOSTS.items():
            with self.subTest(host=host):
                slots = _stub(host)
                slots._bridge.app_path = None
                slots.b000()
                self.assertEqual(slots._bridge.calls, [])
                self.assertEqual(
                    slots._bridge.logger.said("error"), [engine.not_found()]
                )

    def test_an_engine_error_lands_in_the_log(self):
        for host in HOSTS:
            with self.subTest(host=host):
                slots = _stub(host)
                slots._bridge.send = mock.MagicMock(side_effect=RuntimeError("boom"))
                slots.b000()
                error = slots._bridge.logger.said("error")[0]
                self.assertTrue(error.startswith("Bridge raised:"), error)
                self.assertIn("boom", error)

    def test_the_send_reports_progress_naming_the_target(self):
        for host, (_name, engine, _label) in HOSTS.items():
            with self.subTest(host=host):
                slots = _stub(host)
                slots.b000()
                slots.sb.progress.assert_called_once_with(
                    text=f"Working: Send to {engine.APP} (import)"
                )

    def test_an_engine_that_reads_no_declarations_sends_every_template(self):
        """``MayaBridge``'s run spec serves ``save_as``, but it reads no template's
        output declarations, so its templates take the interactive route (as the
        Maya Bridge's did) instead of failing on a declaration it cannot read."""
        slots = _stub("blender", pair=("save_ma", "save_as"))
        self.assertEqual(slots._blocking_modes(), ())
        slots.b000()
        self.assertEqual([c[0] for c in slots._bridge.calls], ["send"])
        slots.sb.save_file_dialog.assert_not_called()


# ---------------------------------------------------------------------------
# b000: the blocking routes (an engine with them: the Blender target)
# ---------------------------------------------------------------------------


class TestDccBridgeBlocking(unittest.TestCase):
    def test_an_auto_round_trip_derives_its_artifact_and_reports_the_return(self):
        """The bake: no save dialog, the template's own timeout, and the bindings
        the return leg wired are reported."""
        params = {"SCOPE": "selected"}
        slots = _stub("maya", params=params, pair=("bake_lightmaps", "round_trip"))
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
        slots = _stub("maya", pair=("save_blend", "save_as"))
        slots.tk.EnvUtils.saved_scene_path.return_value = "C:/work/room.ma"
        slots.sb.save_file_dialog.return_value = "C:/work/room.blend"
        slots.b000()
        slots.tk.EnvUtils.saved_scene_path.assert_called_once_with()
        kwargs = slots.sb.save_file_dialog.call_args.kwargs
        self.assertEqual(Path(kwargs["start_dir"]), Path("C:/work/room.blend"))
        self.assertEqual(kwargs["file_types"], ["*.blend", "*.json"])
        self.assertEqual(kwargs["filter_description"], "Blender bridge output")
        verb, out_path, sent = slots._bridge.calls[0]
        self.assertEqual((verb, out_path), ("save_as", "C:/work/room.blend"))
        self.assertIsNone(sent["timeout"])
        self.assertEqual(
            slots._bridge.logger.said("success"), ["Wrote C:/work/room.blend"]
        )

    def test_an_unsaved_scene_seeds_untitled(self):
        slots = _stub("maya", pair=("save_blend", "save_as"))
        slots.tk.EnvUtils.saved_scene_path.return_value = ""
        slots.sb.save_file_dialog.return_value = ""
        slots.b000()
        start = Path(slots.sb.save_file_dialog.call_args.kwargs["start_dir"])
        self.assertEqual(start.name, "untitled.blend")

    def test_a_cancelled_save_dialog_sends_nothing(self):
        slots = _stub("maya", pair=("save_blend", "save_as"))
        slots.tk.EnvUtils.saved_scene_path.return_value = ""
        slots.sb.save_file_dialog.return_value = None
        slots.b000()
        self.assertEqual(slots._bridge.calls, [])
        self.assertIn("Cancelled.", slots._bridge.logger.said("info"))

    def test_an_extension_the_engine_cannot_write_falls_back(self):
        """``resolve_save_path`` would append ``.blend`` to a ``.usd`` name, so the
        dialog offers what the engine writes and says why."""
        slots = _stub("maya", pair=("save_usd", "save_as"))
        slots.tk.EnvUtils.saved_scene_path.return_value = "C:/work/room.ma"
        slots.sb.save_file_dialog.return_value = ""
        slots.b000()
        start = Path(slots.sb.save_file_dialog.call_args.kwargs["start_dir"])
        self.assertEqual(start.name, "room.blend")
        warning = slots._bridge.logger.said("warning")[0]
        self.assertIn("BRIDGE_OUTPUT_EXT '.usd'", warning)
        self.assertIn("_BlenderEngine.save_extensions", warning)

    def test_a_blocking_run_with_no_artifact_is_an_error(self):
        slots = _stub("maya", pair=("bake_lightmaps", "round_trip"))
        slots._bridge.round_trip = mock.MagicMock(return_value=None)
        slots.b000()
        self.assertEqual(
            slots._bridge.logger.said("error"),
            ["bake_lightmaps produced no file -- see the log above."],
        )

    def test_a_mode_the_run_spec_does_not_serve_launches_interactively(self):
        """``send_to`` is the interactive spec's; only the run spec's modes block."""
        slots = _stub("maya", pair=("import", "send_to"))
        slots.b000()
        self.assertEqual([c[0] for c in slots._bridge.calls], ["send"])
        slots.sb.save_file_dialog.assert_not_called()


# ---------------------------------------------------------------------------
# The panel loaded for real in each host (offscreen Qt, no DCC)
# ---------------------------------------------------------------------------


def _qt_toolkit(host, templates: Path):
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

    class _Real(HOSTS[host][1]):
        TEMPLATE_DIR = templates

        @classmethod
        def params_registry(cls):
            return _Rows

    return _toolkit(host, engine=_Real)


class TestDccBridgePanelLoads(unittest.TestCase):
    """The panel built through a real (offscreen) Switchboard over each host's
    fake toolkit: the chrome names the target, the combo lists the engine's
    pairs and the rows follow the template."""

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
        self.templates = Path(tempfile.mkdtemp(prefix="dcc_bridge_templates_"))
        self.addCleanup(shutil.rmtree, self.templates, True)

    def _load(self, host):
        from uitk import Switchboard

        sb = Switchboard(
            ui_source=str(UI_FILE), slot_source=DccBridgeSlots, context_tags={host}
        )
        sb.tk = _qt_toolkit(host, self.templates)  # set before any panel is built
        ui = sb.get_ui("dcc_bridge")
        slots = sb.get_slots_instance(ui)
        self.assertIsInstance(slots, DccBridgeSlots)
        return ui, slots

    def _labels(self, ui, slots):
        slots._populate_template_combo(ui.cmb000)  # cmb000 fills on first show
        return [ui.cmb000.itemText(i) for i in range(ui.cmb000.count())]

    def test_in_maya_it_is_the_blender_bridge(self):
        ui, slots = self._load("maya")
        self.assertEqual(
            self._labels(ui, slots),
            ["import (send_to)", "bake_lightmaps (round_trip)", "save_blend (save_as)"],
        )
        ui.cmb000.setCurrentIndex(0)
        self.assertEqual(slots._relevant_param_keys(), {"CLEAR_SCENE"})
        ui.cmb000.setCurrentIndex(1)
        self.assertEqual(slots._relevant_param_keys(), {"QUALITY"})
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "blender_bridge")
        self.assertEqual(ui.b000.text(), "Send to Blender")
        self.assertEqual(ui.header.title(), "BLENDER BRIDGE")
        self.assertIn("mayatk's Blender bridge", ui.cmb000.toolTip())

    def test_in_blender_it_is_the_maya_bridge(self):
        ui, slots = self._load("blender")
        self.assertEqual(self._labels(ui, slots), ["import (send_to)"])
        ui.cmb000.setCurrentIndex(0)
        self.assertEqual(slots._relevant_param_keys(), {"CLEAR_SCENE"})
        self.assertEqual(slots.PRESETS_ROOT, Path("blendertk") / "maya_bridge")
        self.assertEqual(ui.b000.text(), "Send to Maya")
        self.assertEqual(ui.header.title(), "MAYA BRIDGE")
        self.assertIn("blendertk's Maya bridge", ui.cmb000.toolTip())


# ---------------------------------------------------------------------------
# In Maya: the Blender Bridge over the real mtk
# ---------------------------------------------------------------------------


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestDccBridgePanelInMaya(unittest.TestCase):
    """The panel's host calls against the real ``mtk`` on a real scene. Built
    with ``__new__`` (a batch mayapy cannot host the Qt rows ``__init__`` builds);
    the engine's send is stood in for, so no Blender launches."""

    def setUp(self):
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)

    def _panel(self, **kwargs):
        slots = _stub("maya", **kwargs)
        slots.sb.tk = self.mtk
        slots._bridge = self.mtk.BlenderBridge(blender_path="not-used.exe")
        return slots

    def test_the_panel_reads_mayatks_bridge_to_blender(self):
        slots = self._panel()
        engine = self.mtk.BlenderBridge
        self.assertIs(slots.bridge_class, engine)
        self.assertEqual(slots.target_app, "Blender")
        self.assertIs(slots.params_module, engine.params_registry())
        self.assertIn("SCOPE", slots.params_module.PARAMS)
        self.assertTrue((slots.template_dir / "import.py").is_file())
        pairs = dict(slots.list_template_modes())
        self.assertEqual(pairs["import"], "send_to")
        self.assertEqual(pairs["bake_lightmaps"], "round_trip")
        self.assertEqual(slots.PRESETS_ROOT, Path("mayatk") / "blender_bridge")
        self.assertIn("round_trip", slots._blocking_modes())

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
