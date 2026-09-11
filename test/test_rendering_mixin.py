#!/usr/bin/python
# coding=utf-8
"""Tests for the shared rendering-panel behavior (DCC-agnostic).

``tentacle/slots/_rendering.py`` is down to one thing: the playblast encoder
guard. The WebXR Preview option box and push flow used to live here and are
gone -- the preview is one panel now (``extapps``'s ``webxr_preview``), which
each fork LAUNCHES rather than reimplements. Its own behaviour is tested with
it, in ``extapps/test/test_webxr_preview.py``.

So what is pinned here is the guard, plus the structural rule that made the
move worth doing: neither fork may grow its own copy of the preview again.
That rule is checked against the source rather than by running it, because a
fork re-growing a push flow is exactly the drift that is invisible until the
two DCCs disagree.
"""

import ast
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots._rendering import RenderingMixin  # noqa: E402

MAYA_FILE = ROOT / "tentacle" / "slots" / "maya" / "rendering.py"
BLENDER_FILE = ROOT / "tentacle" / "slots" / "blender" / "rendering.py"
UI_FILE = ROOT / "tentacle" / "ui" / "rendering.ui"
SUBMENU_FILE = ROOT / "tentacle" / "ui" / "rendering#submenu.ui"

#: The preview is a LAUNCH now. A fork defining any of these is re-growing the
#: flow the shared panel replaced -- and the first symptom would be the two
#: DCCs quietly disagreeing again, which is what the move exists to end.
FORK_MUST_NOT_DEFINE = (
    "webxr_init",
    "webxr_push",
    "_webxr_push_scene",
    "_webxr_publish_external",
    "_webxr_texture_tool_ready",
)

#: objectNames retired with tentacle's WebXR option box. NEVER reused for a new
#: control in these panels: QSettings is keyed by objectName, so a new row
#: under one of these would silently inherit whatever the old control stored --
#: a checkbox coming up ticked because a *different* checkbox once was.
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


def _fork_sources():
    for path in (MAYA_FILE, BLENDER_FILE):
        yield path, ast.parse(path.read_text(encoding="utf-8"))


class _FakeSwitchboard:
    """Just enough switchboard to answer the guard's modal."""

    def __init__(self, answer="Yes"):
        self.answer = answer
        self.messages = []

    def message_box(self, text, *buttons):
        self.messages.append(text)
        return self.answer if buttons else None


class _Host(RenderingMixin):
    def __init__(self, answer="Yes"):
        self.sb = _FakeSwitchboard(answer)


class TestForksStayThin(unittest.TestCase):
    """Neither DCC fork may reimplement the preview."""

    def test_no_fork_defines_a_retired_preview_method(self):
        for path, tree in _fork_sources():
            defined = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            }
            for name in FORK_MUST_NOT_DEFINE:
                with self.subTest(fork=path.name, method=name):
                    self.assertNotIn(name, defined)

    def test_the_mixin_no_longer_carries_the_preview(self):
        for name in FORK_MUST_NOT_DEFINE:
            with self.subTest(method=name):
                self.assertFalse(hasattr(RenderingMixin, name))

    def test_the_preview_slot_uses_the_plain_button_prefix(self):
        """``tb`` means a tool BUTTON -- one that carries an option box.

        The preview no longer has one, so it is ``b000``. The prefix is the
        only signal of which kind a slot is: both are ``PushButton`` in the
        .ui, and the option box is attached at run time by the ``_init`` hook.
        A ``tb`` name with no option box reads as a control whose menu failed
        to build.
        """
        for path, tree in _fork_sources():
            defined = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            }
            with self.subTest(fork=path.name):
                self.assertIn("b000", defined, "the preview slot should be b000")
                self.assertNotIn("tb002", defined, "the tb-prefixed name is retired")
                # No _init means no option box is ever attached, which is what
                # makes the plain prefix the correct one.
                self.assertNotIn("b000_init", defined)

    def test_the_ui_agrees_with_the_renamed_slot(self):
        # A slot whose objectName is absent from the .ui never fires, and
        # nothing raises -- the button simply does nothing when pressed.
        for ui in (UI_FILE, SUBMENU_FILE):
            source = ui.read_text(encoding="utf-8")
            with self.subTest(ui=ui.name):
                self.assertIn('name="b000"', source)
                self.assertNotIn('name="tb002"', source)

    def test_each_fork_launches_the_shared_panel_by_name(self):
        for path, _tree in _fork_sources():
            source = path.read_text(encoding="utf-8")
            with self.subTest(fork=path.name):
                # The entry-point NAME is the contract between the host and
                # extapps -- a host never imports the app's slot class.
                self.assertIn('launch("webxr_preview"', source)
                # show=False is what makes injection possible at all: it hands
                # back the widget before it is shown, so the bridge can be set.
                self.assertIn("show=False", source)
                self.assertIn("WebXrPreview", source)

    def test_each_fork_injects_the_bridge_class_not_an_instance(self):
        # A class keeps construction lazy AND keeps the deliverer a class
        # attribute, which is what lets the port and an open page outlive the
        # panel. Injecting `mtk.WebXrPreview()` would quietly end both.
        for path, _tree in _fork_sources():
            source = path.read_text(encoding="utf-8")
            with self.subTest(fork=path.name):
                self.assertNotIn("engine = mtk.WebXrPreview()", source)
                self.assertNotIn("engine = btk.WebXrPreview()", source)

    def test_retired_object_names_are_not_reused(self):
        for path, _tree in _fork_sources():
            source = path.read_text(encoding="utf-8")
            for name in RETIRED_OBJECT_NAMES:
                with self.subTest(fork=path.name, objectName=name):
                    self.assertNotIn(f'"{name}"', source)


class TestFfmpegGate(unittest.TestCase):
    """The encoder guard must OFFER the install, never dead-end in a log line.

    An encoded playblast follows a viewport capture that takes minutes, so a
    refusal discovered at the encode step costs the whole capture. The engine's
    own pre-flight can only refuse; a panel has a user to ask.
    """

    def setUp(self) -> None:
        self.host = _Host()

    def test_an_already_present_ffmpeg_says_nothing(self):
        with mock.patch("pythontk.VidUtils.ensure_ffmpeg", return_value=None):
            self.assertTrue(self.host._ffmpeg_ready())
        self.assertEqual(self.host.sb.messages, [])

    def test_an_installed_ffmpeg_reports_where_it_landed(self):
        with mock.patch(
            "pythontk.VidUtils.ensure_ffmpeg", return_value="C:/tools/ffmpeg.exe"
        ):
            self.assertTrue(self.host._ffmpeg_ready())
        self.assertEqual(len(self.host.sb.messages), 1)
        self.assertIn("ffmpeg.exe", self.host.sb.messages[0])

    def test_the_primitive_is_handed_the_panels_own_consent(self):
        seen = {}

        def _capture(prompt=None):
            seen["prompt"] = prompt
            return None

        with mock.patch("pythontk.VidUtils.ensure_ffmpeg", side_effect=_capture):
            self.host._ffmpeg_ready()
        # The panel supplies the modal; the primitive owns the decision. Both
        # DCCs then answer the same environment the same way.
        self.assertTrue(callable(seen["prompt"]))

    def test_the_consent_callable_reads_the_modal_back_correctly(self):
        captured = {}

        def _capture(prompt=None):
            captured["answer"] = prompt("Install ffmpeg?")
            return None

        for answer, expected in (("Yes", True), ("No", False)):
            with self.subTest(answer=answer):
                host = _Host(answer)
                with mock.patch(
                    "pythontk.VidUtils.ensure_ffmpeg", side_effect=_capture
                ):
                    host._ffmpeg_ready()
                self.assertIs(captured["answer"], expected)

    def test_a_declined_or_failed_install_stops_with_the_fix_shaped_error(self):
        error = FileNotFoundError("ffmpeg not found; install it from https://…")
        with mock.patch("pythontk.VidUtils.ensure_ffmpeg", side_effect=error):
            self.assertFalse(self.host._ffmpeg_ready())
        # The primitive's refusal names the manual install, so it IS the
        # message -- rewording it here would drop the actionable half.
        self.assertEqual(self.host.sb.messages, [str(error)])


if __name__ == "__main__":
    unittest.main()
