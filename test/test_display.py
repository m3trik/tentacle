#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.display, the one Display Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- every Display row calls its one ``DisplayUtils`` toggle and words the
  state it left (or that there was nothing to act on);
- the rows one host serves carry ``requires`` and go through uitk's
  visibility policy;
- in Maya, the xRay trio's set arithmetic over real meshes (the highest-risk
  chain: operating on the wrong subset silently affects the wrong objects).
The toggles themselves are tested in mayatk and blendertk.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.display import DisplaySlots


def _row(label, category):
    """A leaf of the Display list, as ``on_item_interacted`` hands it over."""
    item = mock.MagicMock()
    item.sublist = None
    item.item_text.return_value = label
    item.parent_item_text.return_value = category
    return item


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = DisplaySlots(self.sb)
        self.display = self.sb.tk.DisplayUtils

    def _run(self, category, label):
        """Click a row; return the message it showed (None when silent)."""
        self.sb.message_box.reset_mock()
        self.slots.list000(_row(label, category))
        call = self.sb.message_box.call_args
        return call.args[0] if call else None


class TestRows(_SlotsCase):
    """Each row: one toolkit call, and the state it left in the message."""

    CASES = (
        # category, label, toolkit op, its answer, the message contains
        ("View", "Hide Selected", "hide_objects", ["a", "b"], "<hl>2</hl> object(s)"),
        ("View", "Hide Selected", "hide_objects", [], "nothing selected"),
        ("View", "Show Selected", "show_objects", ["a"], "<hl>1</hl> object(s)"),
        ("View", "Component ID", "cycle_component_ids", "uv", "<hl>UV</hl>"),
        ("View", "Component ID", "cycle_component_ids", None, "select a polygon mesh"),
        ("View", "Mat Override", "toggle_material_override", True, "<hl>On</hl>"),
        ("View", "Mat Override", "toggle_material_override", None, "no 3D viewport"),
        ("Wireframe", "Wireframe Selected", "toggle_wireframe", False, "<hl>Off</hl>"),
        ("Wireframe", "Wireframe Selected", "toggle_wireframe", [], "nothing selected"),
        (
            "Wireframe",
            "Wireframe Inactive",
            "toggle_wireframe_inactive",
            True,
            "<hl>On</hl>",
        ),
        (
            "Wireframe",
            "Template Selected",
            "toggle_template",
            (True, ["a"]),
            "1</hl> object(s) templated",
        ),
        (
            "Wireframe",
            "Template Selected",
            "toggle_template",
            (False, ["a", "b"]),
            "2</hl> object(s) released",
        ),
        ("Wireframe", "Template Selected", "toggle_template", [], "nothing selected"),
        (
            "XRay",
            "Xray Selected",
            "toggle_xray",
            (True, 3),
            "Xray Selected (3): <hl>On</hl>",
        ),
        ("XRay", "Xray Selected", "toggle_xray", [], "nothing selected"),
        ("XRay", "Xray Selected", "toggle_xray", None, "nothing selected"),
        (
            "XRay",
            "Xray Other",
            "toggle_xray_others",
            (False, 2),
            "Xray Other (2): <hl>Off</hl>",
        ),
        ("XRay", "Xray Other", "toggle_xray_others", None, "nothing to toggle"),
        ("UV", "Display UV Border", "toggle_uv_border_edges", True, "<hl>On</hl>"),
        ("UV", "Borders", "toggle_uv_border_edges", None, "no polygon mesh"),
        ("UV", "Borders", "toggle_uv_border_edges", [], "nothing selected"),
        ("UV", "Checkered", "toggle_uv_checker", None, "no UV editor open"),
        ("UV", "Distortion", "toggle_uv_distortion", "angle", "<hl>Angle</hl>"),
        (
            "Normals",
            "Display Normal",
            "cycle_normals_display",
            "tangent",
            "<hl>Tangent</hl>",
        ),
        (
            "Normals",
            "Soft Edge Display",
            "toggle_soft_edge_display",
            False,
            "<hl>Off</hl>",
        ),
    )

    def test_each_row_calls_its_toggle_and_words_the_state(self):
        for category, label, op, answer, words in self.CASES:
            with self.subTest(label=label, answer=answer):
                getattr(self.display, op).reset_mock()
                getattr(self.display, op).return_value = answer
                message = self._run(category, label)
                getattr(self.display, op).assert_called_once()
                self.assertIn(words, message)

    def test_selection_rows_pass_none_for_the_selection(self):
        for category, label, op in (
            ("View", "Hide Selected", "hide_objects"),
            ("Wireframe", "Wireframe Selected", "toggle_wireframe"),
            ("Wireframe", "Template Selected", "toggle_template"),
            ("XRay", "Xray Selected", "toggle_xray"),
            ("XRay", "Xray Other", "toggle_xray_others"),
            ("UV", "Display UV Border", "toggle_uv_border_edges"),
        ):
            with self.subTest(label=label):
                getattr(self.display, op).return_value = []  # nothing selected
                self._run(category, label)
                self.assertEqual(getattr(self.display, op).call_args.args, (None,))

    def test_show_geometry_shows_every_mesh(self):
        self.assertIn("visible", self._run("View", "Show Geometry"))
        self.display.set_visibility.assert_called_once_with("mesh", True)

    def test_shaded_selected_sets_the_selection_shaded(self):
        self.display.set_wireframe.return_value = ["a"]
        self.assertIn("<hl>1</hl>", self._run("Wireframe", "Shaded Selected"))
        self.display.set_wireframe.assert_called_once_with(None, False)

    def test_un_xray_all(self):
        self.assertIn("cleared", self._run("XRay", "Un-Xray All"))
        self.display.clear_xray.assert_called_once_with()

    def test_set_wireframe_color_opens_the_hosts_palette(self):
        self.sb.tk.UiUtils.open_editor.return_value = "objectColorPalette"
        self.assertIn("palette opened", self._run("Wireframe", "Set Wireframe Color"))
        self.sb.tk.UiUtils.open_editor.assert_called_once_with("Wireframe Color")
        self.sb.tk.UiUtils.open_editor.return_value = None
        self.assertIn("could not open", self._run("Wireframe", "Set Wireframe Color"))

    def test_a_category_row_only_navigates(self):
        item = _row("View", "Display")
        item.sublist = mock.MagicMock()
        item.sublist.get_items.return_value = [mock.MagicMock()]
        self.slots.list000(item)
        self.sb.message_box.assert_not_called()
        self.assertEqual(self.display.method_calls, [])

    def test_every_row_names_a_handler(self):
        for category, rows in DisplaySlots._LIST000_ITEMS.items():
            for label, handler, requires in rows:
                with self.subTest(row=label):
                    self.assertTrue(callable(getattr(self.slots, handler, None)))
                    self.assertIn(requires, (None, "maya", "blender"))


class TestListBuild(_SlotsCase):
    """The rows one host serves go through uitk's visibility policy."""

    def _build(self):
        widget = mock.MagicMock()
        widget.ui.has_tags.return_value = False
        added = {}

        def add_rows(labels):
            items = [mock.MagicMock(name=label) for label in labels]
            added.update(zip(labels, items))
            return items

        root = widget.add.return_value
        root.sublist.add.return_value.sublist.add.side_effect = add_rows
        self.slots.list000_init(widget)
        return added

    def test_host_only_rows_are_tagged_and_policed(self):
        added = self._build()
        tagged = {
            label
            for label, item in added.items()
            if mock.call("requires", "maya") in item.setProperty.call_args_list
        }
        self.assertEqual(
            tagged,
            {"Show Selected", "Set Wireframe Color", "Display UV Border", "Borders"},
        )
        policed = {c.args[0] for c in self.sb.apply_visibility_policy.call_args_list}
        self.assertEqual(policed, {added[label] for label in tagged})

    def test_rows_both_hosts_serve_are_left_alone(self):
        added = self._build()
        added["Xray Selected"].setProperty.assert_not_called()


class TestButtons(_SlotsCase):
    def test_b013_b014_open_their_panels(self):
        self.slots.b013()
        self.slots.b014()
        shown = [c.args[0] for c in self.sb.handlers.marking_menu.show.call_args_list]
        self.assertEqual(shown, ["exploded_view", "color_id"])


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestDisplayInMaya(_SlotsCase):
    """The same class over the real ``mtk``: hide/show and the xRay trio."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.a = self.cmds.polyCube(name="xr_a")[0]
        self.b = self.cmds.polyCube(name="xr_b")[0]
        self.c = self.cmds.polyCube(name="xr_c")[0]
        self.cmds.select(clear=True)

    def tearDown(self):
        self.cmds.file(new=True, force=True)

    def _xray(self, node):
        result = self.cmds.displaySurface(node, xRay=True, query=True)
        return bool(result[0]) if result else False

    def test_hide_then_show_the_selection(self):
        self.cmds.select(self.a)
        self._run("View", "Hide Selected")
        self.assertFalse(self.cmds.getAttr(f"{self.a}.visibility"))
        self.cmds.select(self.a)
        self._run("View", "Show Selected")
        self.assertTrue(self.cmds.getAttr(f"{self.a}.visibility"))

    def test_hide_with_nothing_selected_changes_nothing(self):
        self.assertIn("nothing selected", self._run("View", "Hide Selected"))
        self.assertTrue(self.cmds.getAttr(f"{self.a}.visibility"))

    def test_xray_selected_toggles_only_the_selection(self):
        self.cmds.select([self.a, self.b])
        self.assertIn("On", self._run("XRay", "Xray Selected"))
        self.assertTrue(self._xray(self.a) and self._xray(self.b))
        self.assertFalse(self._xray(self.c))
        self.assertIn("Off", self._run("XRay", "Xray Selected"))
        self.assertFalse(self._xray(self.a))

    def test_xray_selected_unifies_a_mixed_selection(self):
        """A mesh that lost its xray (topology ops drop it) among xray'd others:
        ONE press turns all on, never a per-object invert."""
        self.cmds.displaySurface(self.a, xRay=True)
        self.cmds.select([self.a, self.b])
        self._run("XRay", "Xray Selected")
        self.assertTrue(self._xray(self.a) and self._xray(self.b))

    def test_xray_selected_resolves_groups_and_components(self):
        self.cmds.group(self.a, name="xr_grp")
        self.cmds.select(["xr_grp", f"{self.b}.f[0]"])
        self._run("XRay", "Xray Selected")
        self.assertTrue(self._xray(self.a) and self._xray(self.b))
        self.assertFalse(self._xray(self.c))

    def test_xray_other_and_un_xray_all(self):
        self.cmds.select(self.a)
        self._run("XRay", "Xray Other")
        self.assertEqual(
            [self._xray(n) for n in (self.a, self.b, self.c)], [False, True, True]
        )
        self._run("XRay", "Un-Xray All")
        self.assertFalse(any(self._xray(n) for n in (self.a, self.b, self.c)))

    def test_xray_other_with_nothing_selected_toggles_everything(self):
        self._run("XRay", "Xray Other")
        self.assertTrue(all(self._xray(n) for n in (self.a, self.b, self.c)))


if __name__ == "__main__":
    unittest.main()
