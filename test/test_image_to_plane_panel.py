#!/usr/bin/python
# coding=utf-8
"""The Image to Plane panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``. The engine (planes, materials, the selected
result, one undo step each) is the libraries': mayatk's and blendertk's
``test_image_to_plane.py``.
"""

import os
import struct
import unittest
import zlib
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.image_to_plane import ImageToPlaneSlots

#: mayatk's ``ImageToPlane.MAT_TYPES``; blendertk's lists its one.
MAYA_MAT_TYPES = (("Stingray PBS", "stingray"), ("Standard Surface", "standard"))


def _queue(paths):
    """A list-widget stand-in holding *paths*."""
    files = mock.MagicMock()
    files.count.return_value = len(paths)
    files.item.side_effect = lambda i: mock.Mock(text=mock.Mock(return_value=paths[i]))
    return files


def _panel(
    paths=(), mat_types=MAYA_MAT_TYPES, affix=("", "_MAT"), mode="auto", tk=None
):
    """A Slots instance over a mock ui and a mock toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is)."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.ImageToPlane.MAT_TYPES = mat_types
    ui = sb.loaded_ui.image_to_plane
    ui.lst_files = _queue(list(paths))
    ui.cmb_mat_type.currentData.return_value = "standard"
    ui.spn_height.value.return_value = 4.0
    ui.header.menu.chk_group_result.isChecked.return_value = False
    ui.txt_suffix.option_box.resolve_affix.return_value = affix
    ui.txt_suffix.option_box.affix_mode = mode
    return ImageToPlaneSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestImageToPlanePanelSetup(_PanelCase):
    def test_the_combo_lists_the_hosts_material_types(self):
        _, sb = _panel()
        combo = sb.loaded_ui.image_to_plane.cmb_mat_type
        combo.clear.assert_called_once_with()
        self.assertEqual(
            combo.addItem.call_args_list,
            [
                mock.call("Stingray PBS", "stingray"),
                mock.call("Standard Surface", "standard"),
            ],
        )
        combo.setEnabled.assert_called_once_with(True)

    def test_a_host_with_one_material_type_disables_the_combo(self):
        """Blender: one Principled BSDF, nothing to choose."""
        _, sb = _panel(mat_types=(("Principled BSDF", "standard"),))
        combo = sb.loaded_ui.image_to_plane.cmb_mat_type
        combo.addItem.assert_called_once_with("Principled BSDF", "standard")
        combo.setEnabled.assert_called_once_with(False)

    def test_the_header_offers_group_result(self):
        slots, _ = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        names = [c.kwargs.get("setObjectName") for c in header.menu.add.call_args_list]
        self.assertEqual(names, ["chk_group_result"])
        header.set_help_text.assert_called_once()

    def test_the_affix_placeholder_follows_the_mode(self):
        for mode, placeholder in (
            ("prefix", "Material Prefix"),
            ("suffix", "Material Suffix"),
            ("convention", "Scene Convention"),
            ("auto", "Material Affix"),
        ):
            with self.subTest(mode=mode):
                widget = mock.MagicMock()
                widget.option_box.affix_mode = mode
                ImageToPlaneSlots._apply_affix_placeholder(widget)
                widget.setPlaceholderText.assert_called_once_with(placeholder)

    def test_the_affix_field_gets_its_mode_picker(self):
        slots, _ = _panel()
        widget = mock.MagicMock()
        widget.option_box.affix_mode = "auto"
        slots.txt_suffix_init(widget)
        kwargs = widget.option_box.set_affix.call_args.kwargs
        self.assertEqual(
            (kwargs["default"], kwargs["convention_key"]), ("auto", "material")
        )
        widget.setPlaceholderText.assert_called_once_with("Material Affix")


class TestImageToPlanePanelActions(_PanelCase):
    def test_create_builds_through_the_host_engine(self):
        slots, sb = _panel(["C:/art/wide.png", "C:/art/tall.png"])
        sb.tk.ImageToPlane.create.return_value = {"wide": "p1", "tall": "p2"}
        slots.b001()
        sb.tk.ImageToPlane.create.assert_called_once_with(
            ["C:/art/wide.png", "C:/art/tall.png"],
            mat_type="standard",
            suffix="_MAT",
            prefix="",
            plane_height=4.0,
            group=False,
        )
        sb.loaded_ui.image_to_plane.footer.setText.assert_called_with(
            "Created 2 plane(s): wide, tall"
        )

    def test_the_group_is_not_counted_as_a_plane(self):
        slots, sb = _panel(["C:/art/wide.png"])
        sb.loaded_ui.image_to_plane.header.menu.chk_group_result.isChecked.return_value = True
        sb.tk.ImageToPlane.create.return_value = {"wide": "p1", "__group__": "grp"}
        slots.b001()
        self.assertIs(sb.tk.ImageToPlane.create.call_args.kwargs["group"], True)
        sb.loaded_ui.image_to_plane.footer.setText.assert_called_with(
            "Created 1 plane(s): wide"
        )

    def test_a_long_result_is_summarized(self):
        names = [f"img{i}" for i in range(7)]
        slots, sb = _panel([f"C:/art/{n}.png" for n in names])
        sb.tk.ImageToPlane.create.return_value = dict.fromkeys(names, "p")
        slots.b001()
        sb.loaded_ui.image_to_plane.footer.setText.assert_called_with(
            "Created 7 plane(s): img0, img1, img2, img3, img4 … (+2 more)"
        )

    def test_an_empty_queue_is_said_before_the_host_runs(self):
        slots, sb = _panel([])
        slots.b001()
        sb.tk.ImageToPlane.create.assert_not_called()
        self.assertIn(
            "No images queued",
            sb.loaded_ui.image_to_plane.footer.setText.call_args.args[0],
        )

    def test_no_plane_made_is_said(self):
        slots, sb = _panel(["C:/art/missing.png"])
        sb.tk.ImageToPlane.create.return_value = {}
        slots.b001()
        self.assertIn(
            "No planes created",
            sb.loaded_ui.image_to_plane.footer.setText.call_args.args[0],
        )

    def test_an_engine_error_is_shown_in_the_footer(self):
        slots, sb = _panel(["C:/art/wide.png"])
        sb.tk.ImageToPlane.create.side_effect = RuntimeError("boom")
        slots.b001()
        sb.loaded_ui.image_to_plane.footer.setText.assert_called_with("Error: boom")

    def test_an_empty_affix_follows_the_naming_convention(self):
        token = ptk.NamingConvention.affix("material").strip("_")
        for mode, expected in (
            ("auto", ("", f"_{token}")),
            ("suffix", ("", f"_{token}")),
            ("prefix", (f"{token}_", "")),
        ):
            with self.subTest(mode=mode):
                slots, sb = _panel(["C:/art/wide.png"], affix=("", ""), mode=mode)
                sb.tk.ImageToPlane.create.return_value = {"wide": "p1"}
                slots.b001()
                kwargs = sb.tk.ImageToPlane.create.call_args.kwargs
                self.assertEqual((kwargs["prefix"], kwargs["suffix"]), expected)

    def test_remove_selected_removes_through_the_host(self):
        slots, sb = _panel()
        sb.tk.CoreUtils.selected_objects.return_value = ["p1", "p2"]
        sb.tk.ImageToPlane.remove.return_value = 2
        slots.b002()
        sb.tk.ImageToPlane.remove.assert_called_once_with(["p1", "p2"])
        sb.loaded_ui.image_to_plane.footer.setText.assert_called_with(
            "Removed 2 plane(s)."
        )

    def test_remove_with_nothing_selected_is_said(self):
        slots, sb = _panel()
        sb.tk.CoreUtils.selected_objects.return_value = []
        slots.b002()
        sb.tk.ImageToPlane.remove.assert_not_called()
        sb.loaded_ui.image_to_plane.footer.setText.assert_called_with(
            "Select planes to remove."
        )

    def test_clear_empties_the_queue(self):
        slots, sb = _panel(["C:/art/wide.png"])
        slots.b004()
        sb.loaded_ui.image_to_plane.lst_files.clear.assert_called_once_with()

    def test_browse_queues_new_paths_once(self):
        slots, sb = _panel(["C:/art/b.png"])
        picked = (["C:/art/a.png", "C:/art/b.png", "C:/art/a.png"], "")
        with mock.patch(
            "qtpy.QtWidgets.QFileDialog.getOpenFileNames", return_value=picked
        ):
            slots.b000()
        sb.loaded_ui.image_to_plane.lst_files.addItem.assert_called_once_with(
            "C:/art/a.png"
        )

    def test_a_cancelled_browse_changes_nothing(self):
        slots, sb = _panel()
        with mock.patch(
            "qtpy.QtWidgets.QFileDialog.getOpenFileNames", return_value=([], "")
        ):
            slots.b000()
        sb.loaded_ui.image_to_plane.lst_files.addItem.assert_not_called()
        sb.loaded_ui.image_to_plane.footer.setText.assert_not_called()


def _write_png(path, width, height):
    """A plain 8-bit RGB PNG (stdlib only)."""
    row = b"\x00" + b"\x80\x40\x20" * width  # filter byte + pixels

    def chunk(kind, data):
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(row * height))
            + chunk(b"IEND", b"")
        )


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestImageToPlanePanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        artifacts = ptk.TempArtifacts("image_to_plane_panel", policy="scoped")
        self.addCleanup(artifacts.cleanup)
        self.scratch = artifacts.dir_path()

    def test_create_then_remove_the_planes(self):
        cmds = self.cmds
        path = os.path.join(self.scratch, "itpWide.png")
        _write_png(path, 4, 2)
        slots, sb = _panel([path], tk=maya_module("mayatk"))
        footer = sb.loaded_ui.image_to_plane.footer
        combo = sb.loaded_ui.image_to_plane.cmb_mat_type
        self.assertEqual(
            combo.addItem.call_count, 2
        )  # Maya: Stingray PBS, Standard Surface

        slots.b001()
        footer.setText.assert_called_with("Created 1 plane(s): itpWide")
        plane = cmds.ls(selection=True)  # the engine leaves the result selected
        self.assertEqual(plane, ["itpWide"])
        self.assertTrue(cmds.objExists("itpWide_MAT"))

        slots.b002()
        footer.setText.assert_called_with("Removed 1 plane(s).")
        self.assertFalse(cmds.objExists("itpWide"))
        self.assertFalse(cmds.objExists("itpWide_MAT"))


if __name__ == "__main__":
    unittest.main()
