#!/usr/bin/python
# coding=utf-8
"""The Image Tracer panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``; Blender's engine side (``use_blue_pencil``
refused, no ``open_blue_pencil``) is ``blendertk/test/test_image_tracer.py``.
"""

import os
import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.image_tracer import ImageTracerSlots

#: The four buttons and the tracer method each one runs.
BUILDS = (
    ("b002", "trace_curves"),
    ("b003", "create_mesh"),
    ("b004", "create_negative_space_mesh"),
    ("b005", "project_on_plane"),
)


def _panel(
    path="C:/art/logo.png",
    scale=0.5,
    simplify=2.0,
    blue_pencil=False,
    host_has_blue_pencil=True,
):
    """A Slots instance over a mock ui and a mock toolkit; returns it, the
    switchboard and the patched ``QTimer.singleShot``."""
    sb = mock.MagicMock()
    if not host_has_blue_pencil:
        del sb.tk.ImageTracer.open_blue_pencil  # Blender's ImageTracer has none
    ui = sb.loaded_ui.image_tracer
    ui.txt000.text.return_value = path
    ui.s000.value.return_value = scale
    ui.s001.value.return_value = simplify
    ui.header.menu.chk000.isChecked.return_value = blue_pencil
    with mock.patch("qtpy.QtCore.QTimer.singleShot") as later:
        slots = ImageTracerSlots(sb)
    return slots, sb, later


def _menu_entry(header, object_name):
    """The keyword arguments ``header.menu.add`` was given for *object_name*."""
    for call in header.menu.add.call_args_list:
        if call.kwargs.get("setObjectName") == object_name:
            return call.kwargs
    raise AssertionError(f"no {object_name} in the header menu")


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestImageTracerPanel(_PanelCase):
    def test_each_button_builds_through_the_host_tracer(self):
        for button, method in BUILDS:
            with self.subTest(button=button):
                slots, sb, _ = _panel()
                getattr(slots, button)()
                sb.tk.ImageTracer.assert_called_once_with(
                    "C:/art/logo.png", scale=0.5, simplify=2.0, use_blue_pencil=False
                )
                getattr(
                    sb.tk.ImageTracer.return_value, method
                ).assert_called_once_with()
                self.assertIn("<hl>", sb.message_box.call_args.args[0])

    def test_simplify_zero_keeps_every_point(self):
        slots, sb, _ = _panel(simplify=0.0)
        slots.b002()
        self.assertIsNone(sb.tk.ImageTracer.call_args.kwargs["simplify"])

    def test_no_image_is_said_before_the_host_runs(self):
        slots, sb, _ = _panel(path="")
        slots.b003()
        sb.tk.ImageTracer.assert_not_called()
        self.assertIn("Select an image", sb.message_box.call_args.args[0])

    def test_blue_pencil_needs_no_image(self):
        slots, sb, _ = _panel(path="", blue_pencil=True)
        slots.b002()
        sb.tk.ImageTracer.assert_called_once_with(
            "", scale=0.5, simplify=2.0, use_blue_pencil=True
        )

    def test_a_host_without_blue_pencil_never_asks_for_it(self):
        """Blender: a checked box (a stale setting) still traces the image."""
        slots, sb, _ = _panel(blue_pencil=True, host_has_blue_pencil=False)
        slots.b002()
        self.assertFalse(sb.tk.ImageTracer.call_args.kwargs["use_blue_pencil"])

        slots, sb, _ = _panel(path="", blue_pencil=True, host_has_blue_pencil=False)
        slots.b002()
        sb.tk.ImageTracer.assert_not_called()
        self.assertIn("Select an image", sb.message_box.call_args.args[0])

    def test_a_fixable_input_error_is_said_not_raised(self):
        """Maya's tracer refuses at construction, Blender's when it traces."""
        for error in (
            ImportError("OpenCV (cv2) is required for image tracing."),
            FileNotFoundError("Image not found: C:/art/logo.png"),
            NotImplementedError("Blue Pencil tracing is Maya's."),
        ):
            with self.subTest(error=type(error).__name__, at="construction"):
                slots, sb, _ = _panel()
                sb.tk.ImageTracer.side_effect = error
                slots.b003()
                self.assertEqual(sb.message_box.call_args.args[0], str(error))
            with self.subTest(error=type(error).__name__, at="build"):
                slots, sb, _ = _panel()
                sb.tk.ImageTracer.return_value.create_mesh.side_effect = error
                slots.b003()
                self.assertEqual(sb.message_box.call_args.args[0], str(error))

    def test_any_other_error_is_not_swallowed(self):
        slots, sb, _ = _panel()
        sb.tk.ImageTracer.return_value.trace_curves.side_effect = RuntimeError("bug")
        with self.assertRaises(RuntimeError):
            slots.b002()

    def test_no_contours_is_said(self):
        # Maya returns an empty list, Blender None.
        for empty in ([], None):
            with self.subTest(result=empty):
                slots, sb, _ = _panel()
                sb.tk.ImageTracer.return_value.trace_curves.return_value = empty
                slots.b002()
                self.assertEqual(sb.message_box.call_args.args[0], "No contours found.")

    def test_header_offers_blue_pencil_where_the_host_has_it(self):
        for has_it in (True, False):
            with self.subTest(host_has_blue_pencil=has_it):
                slots, sb, _ = _panel(host_has_blue_pencil=has_it)
                header = mock.MagicMock()
                slots.header_init(header)
                for name in ("chk000", "blue_pencil_button"):
                    self.assertIs(_menu_entry(header, name)["setEnabled"], has_it)
                header.set_help_text.assert_called_once()

    def test_open_blue_pencil_opens_the_host_tool(self):
        slots, sb, _ = _panel()
        slots.blue_pencil_button()
        sb.tk.ImageTracer.open_blue_pencil.assert_called_once_with()

        slots, sb, _ = _panel(host_has_blue_pencil=False)
        slots.blue_pencil_button()  # disabled there; a stray call is a no-op

    def test_use_blue_pencil_disables_the_path_field(self):
        slots, sb, later = _panel(blue_pencil=True)
        ui = sb.loaded_ui.image_tracer
        slots.chk000(True)
        ui.txt000.setEnabled.assert_called_with(False)
        # Once the settings have restored, the box's state is re-applied.
        later.assert_called_once_with(200, slots._sync_ui)
        ui.header.menu.chk000.isChecked.return_value = False
        slots._sync_ui()
        ui.txt000.setEnabled.assert_called_with(True)

    def test_the_path_field_browses_for_images(self):
        slots, _, _ = _panel()
        widget = mock.MagicMock()
        slots.txt000_init(widget)
        kwargs = widget.option_box.browse.call_args.kwargs
        self.assertIn("*.png", kwargs["file_types"])
        self.assertEqual(kwargs["mode"], "file")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestImageTracerPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        artifacts = ptk.TempArtifacts("image_tracer_panel", policy="scoped")
        self.addCleanup(artifacts.cleanup)
        self.scratch = artifacts.dir_path()

    def _real(self, path):
        slots, sb, _ = _panel(path=path, scale=0.1, simplify=1.0)
        sb.tk = maya_module("mayatk")
        return slots, sb

    def test_a_missing_image_is_said_not_raised(self):
        # No OpenCV or no file: either way the real tracer refuses, and it is said.
        slots, sb = self._real(os.path.join(self.scratch, "missing.png"))
        slots.b002()
        sb.message_box.assert_called_once()
        self.assertEqual(self.cmds.ls(type="nurbsCurve") or [], [])

    def test_traces_and_fills_a_drawn_square(self):
        try:
            import cv2
            import numpy
        except ImportError:
            self.skipTest("OpenCV is not installed in this Maya")
        path = os.path.join(self.scratch, "square.png")
        image = numpy.zeros((64, 64, 3), numpy.uint8)
        image[16:48, 16:48] = 255
        cv2.imwrite(path, image)

        slots, sb = self._real(path)
        slots.b002()
        self.assertTrue(self.cmds.ls(type="nurbsCurve"), "no curves traced")
        slots.b003()
        self.assertTrue(self.cmds.ls(type="mesh"), "no mesh filled")
        self.assertIn("<hl>", sb.message_box.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
