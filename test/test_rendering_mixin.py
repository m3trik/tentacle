#!/usr/bin/python
# coding=utf-8
"""Tests for the rendering panel's shared rules (tentacle.slots.rendering).

The Maya and Blender forks and their ``RenderingMixin`` are one class now
(``RenderingSlots``, both hosts, over ``self.tk``); what the mixin pinned is
pinned here against it: the playblast encoder guard, the default output path
and the output field that shows it without holding it.

And the structural rule the WebXR move was worth doing for: the panel launches
the shared ``webxr_preview`` panel and never grows its own copy of the preview
again. That rule is checked against the source rather than by running it,
because a re-grown push flow is exactly the drift that is invisible until the
two hosts disagree. The preview's own behaviour is tested with it, in
``test_webxr_preview_panel.py``.
"""

import ast
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pythontk as ptk  # noqa: E402
from tentacle.slots._slots import Slots  # noqa: E402
from tentacle.slots.rendering import RenderingSlots  # noqa: E402

SLOTS_FILE = ROOT / "tentacle" / "slots" / "rendering.py"
UI_FILE = ROOT / "tentacle" / "ui" / "rendering.ui"
SUBMENU_FILE = ROOT / "tentacle" / "ui" / "rendering#submenu.ui"

#: The preview is a LAUNCH. A slot defining any of these is re-growing the flow
#: the shared panel replaced.
MUST_NOT_DEFINE = (
    "webxr_init",
    "webxr_push",
    "_webxr_push_scene",
    "_webxr_publish_external",
    "_webxr_texture_tool_ready",
)

#: objectNames retired with tentacle's WebXR option box. NEVER reused for a new
#: control in these panels: QSettings is keyed by objectName, so a new row
#: under one of these would silently inherit whatever the old control stored.
#: ``chk062`` was retired earlier still, with the Open In Browser row.
RETIRED_OBJECT_NAMES = (
    "tb002",
    "cmb061",
    "cmb062",
    "chk061",
    "chk062",
    "chk063",
    "chk064",
    "chk065",
    "chk066",
)


def _tree():
    return ast.parse(SLOTS_FILE.read_text(encoding="utf-8"))


def _defined():
    return {n.name for n in ast.walk(_tree()) if isinstance(n, ast.FunctionDef)}


def _slots(answer="Yes", workspace=None, name="ShotA"):
    """The class over a fake switchboard and toolkit: the modal answers
    *answer*; the scene's project is *workspace* and its name *name*."""
    migrated = Slots._legacy_repeat_last_migrated
    Slots._legacy_repeat_last_migrated = True
    try:
        sb = mock.MagicMock()
        slots = RenderingSlots(sb)
    finally:
        Slots._legacy_repeat_last_migrated = migrated
    sb.messages = []

    def message_box(text, *buttons):
        sb.messages.append(text)
        return answer if buttons else None

    sb.message_box.side_effect = message_box
    sb.tk.DataNodes.scene_workspace.return_value = workspace
    sb.tk.PlayblastExporter.scene_name.return_value = name
    return slots


class TestThePreviewStaysALaunch(unittest.TestCase):
    """The panel never reimplements the preview."""

    def test_no_retired_preview_method_is_defined(self):
        defined = _defined()
        for name in MUST_NOT_DEFINE:
            with self.subTest(method=name):
                self.assertNotIn(name, defined)

    def test_the_preview_slot_uses_the_plain_button_prefix(self):
        """``tb`` means a tool BUTTON -- one that carries an option box. The
        preview has none, so it is ``b000``; a ``tb`` name with no option box
        reads as a control whose menu failed to build."""
        defined = _defined()
        self.assertIn("b000", defined, "the preview slot should be b000")
        self.assertNotIn("tb002", defined, "the tb-prefixed name is retired")
        self.assertNotIn("b000_init", defined)

    def test_the_ui_agrees_with_the_renamed_slot(self):
        # A slot whose objectName is absent from the .ui never fires, and
        # nothing raises: the button simply does nothing when pressed.
        for ui in (UI_FILE, SUBMENU_FILE):
            source = ui.read_text(encoding="utf-8")
            with self.subTest(ui=ui.name):
                self.assertIn('name="b000"', source)
                self.assertNotIn('name="tb002"', source)

    def test_it_launches_the_shared_panel_with_the_hosts_bridge_class(self):
        slots = _slots()
        ui = slots.sb.handlers.external_app.launch.return_value
        slots.b000(None)
        # The entry-point NAME is the contract between the host and the panel;
        # show=False hands the widget back before it is shown, so the bridge
        # can be set.
        slots.sb.handlers.external_app.launch.assert_called_once_with(
            "webxr_preview", show=False
        )
        # The CLASS, not an instance: the port and an open page outlive the panel.
        self.assertIs(ui.slots.engine, slots.tk.WebXrPreview)
        slots.sb.handlers.marking_menu.show.assert_called_once_with(ui)

    def test_retired_object_names_are_not_reused(self):
        source = SLOTS_FILE.read_text(encoding="utf-8")
        for name in RETIRED_OBJECT_NAMES:
            with self.subTest(objectName=name):
                self.assertNotIn(f'"{name}"', source)


class TestFfmpegGate(unittest.TestCase):
    """The encoder guard must OFFER the install, never dead-end in a log line:
    an encoded playblast follows a capture that takes minutes."""

    def test_an_already_present_ffmpeg_says_nothing(self):
        slots = _slots()
        with mock.patch("pythontk.VidUtils.ensure_ffmpeg", return_value=None):
            self.assertTrue(slots._ffmpeg_ready())
        self.assertEqual(slots.sb.messages, [])

    def test_an_installed_ffmpeg_reports_where_it_landed(self):
        slots = _slots()
        with mock.patch(
            "pythontk.VidUtils.ensure_ffmpeg", return_value="C:/tools/ffmpeg.exe"
        ):
            self.assertTrue(slots._ffmpeg_ready())
        self.assertEqual(len(slots.sb.messages), 1)
        self.assertIn("ffmpeg.exe", slots.sb.messages[0])

    def test_the_consent_callable_reads_the_modal_back_correctly(self):
        captured = {}

        def _capture(prompt=None):
            captured["answer"] = prompt("Install ffmpeg?")
            return None

        for answer, expected in (("Yes", True), ("No", False)):
            with self.subTest(answer=answer):
                slots = _slots(answer)
                with mock.patch("pythontk.VidUtils.ensure_ffmpeg", side_effect=_capture):
                    slots._ffmpeg_ready()
                self.assertIs(captured["answer"], expected)

    def test_a_declined_or_failed_install_stops_with_the_fix_shaped_error(self):
        slots = _slots()
        error = FileNotFoundError("ffmpeg not found; install it from https://...")
        with mock.patch("pythontk.VidUtils.ensure_ffmpeg", side_effect=error):
            self.assertFalse(slots._ffmpeg_ready())
        # The primitive's refusal names the manual install, so it IS the message.
        self.assertEqual(slots.sb.messages, [str(error)])


class TestDefaultPlayblastPath(unittest.TestCase):
    """The playblast default is the scene project's movie folder, one rule for
    both hosts."""

    def _project(self, rules=None):
        tmp = ptk.TempArtifacts.scoped("tentacle_test_movie")
        self.addCleanup(tmp.cleanup)
        root = tmp.dir_path()
        return root, ptk.Workspace(root, rules or {})

    def test_lands_in_the_scene_project_movie_folder(self):
        root, ws = self._project()
        path = _slots(workspace=ws)._default_playblast_path()
        self.assertEqual(path, os.path.join(root, "movies", "ShotA"))

    def test_honors_the_project_movie_rule(self):
        root, ws = self._project({"movie": "deliver/clips"})
        path = _slots(workspace=ws, name="v1.test")._default_playblast_path()
        self.assertEqual(path, os.path.join(root, "deliver", "clips", "v1.test"))

    def test_asking_creates_no_folder(self):
        root, ws = self._project()
        _slots(workspace=ws)._default_playblast_path()
        self.assertFalse(os.path.exists(os.path.join(root, "movies")))

    def test_without_a_project_falls_back_to_the_desktop(self):
        path = _slots()._default_playblast_path()
        desktop = os.path.normpath(os.path.expanduser(os.path.join("~", "Desktop")))
        self.assertEqual(path, os.path.join(desktop, "ShotA"))


class _Field:
    def __init__(self, text=""):
        self.text, self.placeholder = text, ""

    def setPlaceholderText(self, text):
        self.placeholder = text


class TestPlayblastFieldDefault(unittest.TestCase):
    """The output field shows the default; it never holds it. A value written
    at build time persists, so the panel kept the FIRST scene's path forever."""

    def test_the_default_is_the_placeholder_and_the_text_is_untouched(self):
        field = _Field()
        slots = _slots(name="ShotA")
        slots._show_playblast_default(field)
        self.assertEqual(field.placeholder, slots._default_playblast_path())
        self.assertEqual(field.text, "")
        # A re-show over another scene follows it.
        slots.tk.PlayblastExporter.scene_name.return_value = "ShotB"
        slots._show_playblast_default(field)
        self.assertEqual(os.path.basename(field.placeholder), "ShotB")

    def test_the_field_is_built_empty_and_refreshed_on_every_show(self):
        tree = _tree()
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and any(
                k.arg == "setObjectName"
                and isinstance(k.value, ast.Constant)
                and k.value.value == "t000"
                for k in node.keywords
            )
        ]
        init = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "tb000_init"
        )
        self.assertEqual(len(calls), 1)
        self.assertNotIn("setText", {k.arg for k in calls[0].keywords})
        init_source = ast.unparse(init)
        self.assertIn("refresh_on_show = True", init_source)
        self.assertIn("_show_playblast_default(menu.t000)", init_source)


if __name__ == "__main__":
    unittest.main()
