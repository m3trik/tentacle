#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.subdivision, the one Subdivision Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- Each one-click button is one library operation on the selection, and an
  empty answer (no mesh) is said.
- s000 (Division Level) / s001 (Tessellation Level): write the preview levels
  to the mesh SHAPES under the selection. These used to guard with
  ``attributeQuery(node=<transform>)``, always False for a shape attribute, so
  both spinboxes were silently inert on every mesh. A locked plug is reported,
  and the init mirrors the live level without persisting it.
- tb000 (Decimate) / b005 (Reduce): pass the selection through AS-IS, so a
  component selection scopes the reduce / dissolve to that region, and pass
  only the options the host's chosen algorithm honors
  (``EditUtils.DECIMATE_OPTIONS``), greying out the rest.
"""
import types
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.subdivision import SubdivisionSlots


class _FakeSpinBox:
    """Minimal QSpinBox stand-in: records whether the seed ran signal-blocked."""

    def __init__(self):
        self._value = None
        self._blocked = False
        self.blocked_during_seed = False
        self.restore_state = True

    def blockSignals(self, block):
        was, self._blocked = self._blocked, block
        return was

    def setValue(self, value):
        self._value = value
        self.blocked_during_seed = self._blocked

    def value(self):
        return self._value


class _FakeOption:
    """One option-box control: answers value()/isChecked()/currentData() alike."""

    def __init__(self, value):
        self._value = value
        self.enabled = None

    def value(self):
        return self._value

    def isChecked(self):
        return self._value

    def currentData(self):
        return self._value

    def setEnabled(self, state):
        self.enabled = state


def _decimate_widget(algorithm="reduce", percentage=50.0, angle=1.0):
    """A stand-in for tb000's option-box widget with the menu controls it reads."""
    menu = types.SimpleNamespace(
        cmb000=_FakeOption(algorithm),
        s010=_FakeOption(percentage),
        s011=_FakeOption(angle),
        chk010=_FakeOption(True),
        chk011=_FakeOption(True),
        chk012=_FakeOption(True),
        chk013=_FakeOption(True),
        chk014=_FakeOption(False),
    )
    return types.SimpleNamespace(option_box=types.SimpleNamespace(menu=menu))


#: A host whose reduce honors everything and whose planar honors the angle only
#: (mayatk's table), and one the other way round (blendertk's).
MAYA_OPTIONS = {
    "reduce": (
        "percentage",
        "preserve_borders",
        "preserve_hard_edges",
        "preserve_uv_borders",
        "preserve_quads",
        "symmetry",
    ),
    "planar": ("angle_tolerance",),
}
BLENDER_OPTIONS = {
    "reduce": ("percentage", "preserve_quads", "symmetry"),
    "planar": (
        "angle_tolerance",
        "preserve_borders",
        "preserve_hard_edges",
        "preserve_uv_borders",
    ),
}


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = SubdivisionSlots(self.sb)
        self.edit = self.sb.tk.EditUtils
        self.display = self.sb.tk.DisplayUtils
        self.edit.DECIMATE_OPTIONS = MAYA_OPTIONS


class TestButtons(_SlotsCase):
    def test_each_button_is_one_operation_on_the_selection(self):
        for slot_name, op in (
            ("b000", "quadrangulate"),
            ("b001", "triangulate"),
            ("b008", "subdivide_mesh"),
        ):
            with self.subTest(slot=slot_name):
                getattr(self.slots, slot_name)()
                getattr(self.edit, op).assert_called_once_with(None)
        self.sb.message_box.assert_not_called()

    def test_no_mesh_is_said(self):
        self.edit.quadrangulate.return_value = []
        self.slots.b000()
        self.sb.message_box.assert_called_once_with(SubdivisionSlots.NO_MESH)

    def test_convert_preview_reports_both_ways(self):
        self.edit.apply_subdivision.return_value = ["a", "b"]
        self.slots.b011()
        self.assertIn("<hl>2</hl>", self.sb.message_box.call_args.args[0])
        self.edit.apply_subdivision.return_value = []
        self.slots.b011()
        self.assertIn("No smooth preview", self.sb.message_box.call_args.args[0])

    def test_quad_draw_is_the_shared_tool(self):
        self.slots.b028()
        self.sb.tk.UiUtils.set_tool.assert_called_once_with("Quad Draw")

    def test_reduce_keeps_history_and_needs_a_selection(self):
        self.sb.tk.CoreUtils.selected_objects.return_value = ["pSphere1.f[0:9]"]
        self.slots.b005()
        self.edit.decimate.assert_called_once_with(
            None, percentage=50.0, delete_history=False
        )
        self.sb.tk.CoreUtils.selected_objects.return_value = []
        self.edit.decimate.reset_mock()
        self.slots.b005()
        self.edit.decimate.assert_not_called()


class TestSmoothLevel(_SlotsCase):
    def test_each_spinbox_sets_its_level(self):
        self.display.set_smooth_level.return_value = ["shape"]
        self.slots.s000(3, None)
        self.display.set_smooth_level.assert_called_with(None, level=3)
        self.slots.s001(4, None)
        self.display.set_smooth_level.assert_called_with(None, adaptive_level=4)
        self.assertIn("Tessellation Level", self.sb.message_box.call_args.args[0])

    def test_no_mesh_is_silent_and_a_locked_plug_is_said(self):
        self.display.set_smooth_level.return_value = []
        self.slots.s000(2, None)
        self.sb.message_box.assert_not_called()
        self.display.set_smooth_level.side_effect = ValueError("locked")
        self.slots.s000(2, None)
        self.assertIn("locked", self.sb.message_box.call_args.args[0])

    def test_init_mirrors_the_live_level(self):
        self.display.get_smooth_level.return_value = {"level": 4, "adaptive_level": 6}
        for name, expect in (("s000", 4), ("s001", 6)):
            widget = _FakeSpinBox()
            getattr(self.slots, f"{name}_init")(widget)
            self.assertEqual(widget.value(), expect)
            self.assertTrue(widget.blocked_during_seed)
            self.assertFalse(widget.restore_state)

    def test_init_without_a_mesh_leaves_the_ui_default(self):
        self.display.get_smooth_level.return_value = None
        widget = _FakeSpinBox()
        self.slots.s000_init(widget)
        self.assertIsNone(widget.value())
        self.assertFalse(widget.restore_state)


class TestDecimateOptions(_SlotsCase):
    def setUp(self):
        super().setUp()
        self.sb.tk.CoreUtils.selected_objects.return_value = ["pSphere1"]

    def test_reduce_passes_what_the_host_honors(self):
        self.edit.DECIMATE_OPTIONS = BLENDER_OPTIONS
        self.slots.tb000(_decimate_widget("reduce", 40.0))
        self.edit.decimate.assert_called_once_with(
            None, percentage=40.0, preserve_quads=True, symmetry=False
        )

    def test_planar_passes_what_the_host_honors(self):
        self.slots.tb000(_decimate_widget("planar", angle=2.0))
        self.edit.dissolve_coplanar.assert_called_once_with(None, angle_tolerance=2.0)
        self.edit.DECIMATE_OPTIONS = BLENDER_OPTIONS
        self.slots.tb000(_decimate_widget("planar", angle=2.0))
        self.edit.dissolve_coplanar.assert_called_with(
            None,
            angle_tolerance=2.0,
            preserve_borders=True,
            preserve_hard_edges=True,
            preserve_uv_borders=True,
        )

    def test_nothing_selected_and_no_mesh_are_said(self):
        self.sb.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb000(_decimate_widget())
        self.assertIn("Nothing selected", self.sb.message_box.call_args.args[0])
        self.edit.decimate.assert_not_called()
        self.sb.tk.CoreUtils.selected_objects.return_value = ["curve1"]
        self.edit.decimate.return_value = []
        self.slots.tb000(_decimate_widget())
        self.assertIn("No mesh in the selection", self.sb.message_box.call_args.args[0])

    def test_the_option_box_greys_out_what_the_algorithm_ignores(self):
        widget = mock.MagicMock()
        menu = widget.option_box.menu
        menu.cmb000.currentData.return_value = "planar"
        self.edit.DECIMATE_OPTIONS = BLENDER_OPTIONS
        self.slots.tb000_init(widget)
        menu.s011.setEnabled.assert_called_with(True)
        menu.chk010.setEnabled.assert_called_with(True)
        menu.s010.setEnabled.assert_called_with(False)
        menu.chk013.setEnabled.assert_called_with(False)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class _MayaCase(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.addCleanup(self.cmds.file, new=True, force=True)

    def messages(self):
        return [c.args[0] for c in self.sb.message_box.call_args_list]


class TestSmoothPreviewInMaya(_MayaCase):
    """s000/s001 drive the smooth-preview attrs on the selection's mesh shapes."""

    def _shape(self, transform):
        return self.cmds.listRelatives(transform, shapes=True, fullPath=True)[0]

    def test_plain_cube_gets_the_division_level(self):
        cube = self.cmds.polyCube(name="sub_plain")[0]
        self.cmds.select(cube)
        self.slots.s000(5, None)
        shape = self._shape(cube)
        self.assertEqual(self.cmds.getAttr(f"{shape}.smoothLevel"), 5)
        # The level is unobservable unless the preview itself is on.
        self.assertEqual(self.cmds.getAttr(f"{shape}.displaySmoothMesh"), 2)
        self.assertEqual(len(self.messages()), 1)
        self.assertIn("Division Level", self.messages()[0])

    def test_division_level_reaches_meshes_under_a_group(self):
        cube = self.cmds.polyCube(name="sub_grp_cube")[0]
        grp = self.cmds.group(cube, name="sub_grp")
        self.cmds.select(grp)
        self.slots.s000(4, None)
        self.assertEqual(
            self.cmds.getAttr(f"{self._shape(grp + '|sub_grp_cube')}.smoothLevel"), 4
        )

    def test_adaptive_level_switches_to_the_adaptive_draw_type(self):
        cube = self.cmds.polyCube(name="sub_adaptive")[0]
        self.cmds.select(cube)
        self.slots.s001(4, None)
        shape = self._shape(cube)
        self.assertEqual(self.cmds.getAttr(f"{shape}.smoothTessLevel"), 4)
        self.assertEqual(self.cmds.getAttr(f"{shape}.smoothDrawType"), 3)
        self.assertFalse(self.cmds.getAttr(f"{shape}.useGlobalSmoothDrawType"))
        self.assertIn("Tessellation Level", self.messages()[0])

    def test_non_mesh_selection_is_a_silent_no_op(self):
        curve = self.cmds.curve(name="sub_curve", degree=1, point=[(0, 0, 0), (1, 0, 0)])
        self.cmds.select(curve)
        self.slots.s000(3, None)
        self.slots.s001(3, None)
        self.assertEqual(self.messages(), [])

    def test_init_seeds_from_the_selection_and_opts_out_of_persistence(self):
        cube = self.cmds.polyCube(name="sub_init_cube")[0]
        self.cmds.setAttr(f"{self._shape(cube)}.smoothLevel", 4)
        self.cmds.select(cube)
        widget = _FakeSpinBox()
        self.slots.s000_init(widget)
        self.assertEqual(widget.value(), 4)
        self.assertFalse(widget.restore_state)
        self.assertTrue(widget.blocked_during_seed)


class TestDecimateInMaya(_MayaCase):
    """tb000 / b005 act on the selection as-is: whole meshes, or a component
    selection to reduce / dissolve only that region."""

    def _faces_where(self, obj, predicate):
        out = []
        for i in range(self.cmds.polyEvaluate(obj, face=True)):
            xyz = self.cmds.xform(f"{obj}.f[{i}]", q=True, ws=True, t=True)
            n = len(xyz) // 3
            if predicate(tuple(sum(xyz[k::3]) / n for k in range(3))):
                out.append(f"{obj}.f[{i}]")
        return out

    def _positions(self, obj, predicate):
        out = set()
        for i in range(self.cmds.polyEvaluate(obj, vertex=True)):
            pos = tuple(
                round(c, 5)
                for c in self.cmds.xform(f"{obj}.vtx[{i}]", q=True, ws=True, t=True)
            )
            if predicate(pos):
                out.add(pos)
        return out

    def test_face_selection_reduces_only_those_faces(self):
        sphere = self.cmds.polySphere(name="sub_dec_sphere", sx=40, sy=40, ch=False)[0]
        before = self.cmds.polyEvaluate(sphere, face=True)
        upper = self._faces_where(sphere, lambda c: c[1] > 0.0)
        lower_before = self._positions(sphere, lambda p: p[1] < -0.05)
        self.cmds.select(upper)
        self.slots.tb000(_decimate_widget("reduce", 50.0))
        self.assertEqual(self.messages(), [])
        after = self.cmds.polyEvaluate(sphere, face=True)
        self.assertLess(after, before)
        self.assertGreater(after, before - len(upper))  # the other half survives
        self.assertTrue(lower_before <= self._positions(sphere, lambda p: p[1] < -0.05))

    def test_planar_face_selection_dissolves_within_the_region(self):
        cube = self.cmds.polyCube(name="sub_dec_cube", sx=5, sy=5, sz=5, ch=False)[0]
        self.cmds.select(self._faces_where(cube, lambda c: c[1] > 0.49))
        self.slots.tb000(_decimate_widget("planar", angle=1.0))
        self.assertEqual(self.messages(), [])
        self.assertEqual(self.cmds.polyEvaluate(cube, face=True), 126)

    def test_b005_reduce_keeps_history(self):
        sphere = self.cmds.polySphere(name="sub_reduce", sx=40, sy=40, ch=False)[0]
        before = self.cmds.polyEvaluate(sphere, face=True)
        self.cmds.select(sphere)
        self.slots.b005()
        self.assertLess(self.cmds.polyEvaluate(sphere, face=True), before)
        self.assertIn("polyReduce", str(self.cmds.listHistory(sphere) or []))

    def test_non_mesh_selection_reports(self):
        curve = self.cmds.curve(name="sub_dec_curve", degree=1, point=[(0, 0, 0), (1, 0, 0)])
        self.cmds.select(curve)
        self.slots.tb000(_decimate_widget("reduce", 50.0))
        self.assertEqual(len(self.messages()), 1)
        self.assertIn("No mesh in the selection", self.messages()[0])

    def test_empty_selection_reports_nothing_selected(self):
        self.cmds.select(clear=True)
        self.slots.tb000(_decimate_widget("reduce", 50.0))
        self.assertEqual(len(self.messages()), 1)
        self.assertIn("Nothing selected", self.messages()[0])


class TestButtonsInMaya(_MayaCase):
    def test_triangulate_and_quadrangulate_the_selection(self):
        cube = self.cmds.polyCube(name="sub_btn_cube", ch=False)[0]
        self.cmds.select(cube)
        self.slots.b001()
        self.assertEqual(self.cmds.polyEvaluate(cube, face=True), 12)
        self.cmds.select(cube)
        self.slots.b000()
        self.assertEqual(self.cmds.polyEvaluate(cube, face=True), 6)
        self.assertEqual(self.messages(), [])

    def test_buttons_with_nothing_selected_say_so(self):
        self.cmds.select(clear=True)
        for name in ("b000", "b001", "b008"):
            getattr(self.slots, name)()
        self.assertEqual(self.messages(), [SubdivisionSlots.NO_MESH] * 3)


if __name__ == "__main__":
    unittest.main()
