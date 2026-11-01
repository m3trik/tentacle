#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.uv, the one UV Slots class.

It reaches its host only through ``self.tk``: a fake toolkit (a MagicMock
switchboard's ``tk``) records what each slot asks of it (plain pytest), and in
Maya the same class drives the real ``mtk`` (``run_tests.py --in-maya``).
Pinned here: each slot's call and arguments, how it words an empty result or a
refusal, the option boxes' host tags and the Pack gates, the Pin / Stack
toggles, and in Maya the behaviors worth a real scene -- Cut / Sew routing,
Unfold's guards and non-manifold strategy, Cut Cylinder's camera, Auto
Unwrap's dispatch, Pack's u3dLayout / xatlas plumbing, Stack / Unstack. The
operations themselves are tested in mayatk and blendertk (``test_uv_utils``).
"""

import os
import unittest
from types import SimpleNamespace
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.uv import UvSlots

cmds = maya_module("maya.cmds")
mel = maya_module("maya.mel")
mtk = maya_module("mayatk")

#: mayatk's pack table, as the fake toolkit's (the gates and the sent options).
MAYA_PACK_ENGINES = {
    "standard": (
        "pre_rotate",
        "rotate_step",
        "rotate_min",
        "rotate_max",
        "mutations",
        "scale_mode",
        "tiles",
        "skip_instances",
    ),
    "xatlas": ("rotate", "brute_force", "skip_instances"),
}
BLENDER_PACK_ENGINES = {"standard": ("rotate", "margin")}


def _value(v):
    """A widget answering isChecked(), value(), currentText() and currentData()."""
    return SimpleNamespace(
        isChecked=lambda: v, value=lambda: v, currentText=lambda: v, currentData=lambda: v
    )


def _widget(**values):
    """An option-box widget whose menu holds *values* by objectName."""
    menu = SimpleNamespace(**{name: _value(v) for name, v in values.items()})
    return SimpleNamespace(option_box=SimpleNamespace(menu=menu))


#: Every option-box value the slots read, at the option boxes' defaults.
PACK_DEFAULTS = dict(
    cmb019="standard", chk044=True, chk043=False, cmb009=1, s_pack_margin=0.001,
    cmb010=0, s011=90, s012=0, s013=0, s014=1, s004=1001, cmb015=(1.0, 1.0),
    cmb018=2, s019=1, s020=1, chk016=True,
)
UNFOLD_DEFAULTS = dict(
    chk017=True, chk007=True, chk022=True, s000=1.0, cmb013="select",
    cmb_unfold_method="Angle Based", s_unfold_margin=0.0,
)
CYLINDER_DEFAULTS = dict(
    s021=20, s022=60, s023=12, s016=45, chk045=True, chk040=False, chk046=False,
    chk041=True, chk042=True,
)


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = UvSlots(self.sb)
        self.slots.ui = SimpleNamespace(
            cmb003=SimpleNamespace(currentText=lambda: "2048"), s003=mock.MagicMock()
        )
        self.tk = self.sb.tk
        self.tk.CoreUtils.selected_objects.return_value = ["pCube1"]
        self.tk.UvUtils.PACK_ENGINES = MAYA_PACK_ENGINES

    def messages(self):
        return [c.args[0] for c in self.sb.message_box.call_args_list]


class TestMapSize(_SlotsCase):
    def test_returns_int_from_combo_text(self):
        for size in (256, 512, 1024, 2048, 4096):
            self.slots.ui.cmb003 = SimpleNamespace(currentText=lambda s=size: str(s))
            self.assertEqual(self.slots.get_map_size(), size)

    def test_non_numeric_text_raises(self):
        """Contract: garbage in cmb003 raises ValueError (no silent fallback)."""
        self.slots.ui.cmb003 = SimpleNamespace(currentText=lambda: "not_a_number")
        with self.assertRaises(ValueError):
            self.slots.get_map_size()


class TestLaunchersAndWindows(_SlotsCase):
    def test_tools_open_their_shared_panels(self):
        for slot, panel in (
            ("b000", "texture_combine"),
            ("b032", "rizom_bridge"),
            ("b033", "shell_xform"),
        ):
            with self.subTest(slot=slot):
                getattr(self.slots, slot)()
                self.sb.handlers.marking_menu.show.assert_called_with(panel)

    def test_b000_init_builds_no_option_box(self):
        widget = mock.MagicMock()
        self.slots.b000_init(widget)
        widget.setText.assert_called_once_with("Texture Combine...")
        self.assertFalse(widget.option_box.menu.add.called)

    def test_b031_and_the_header_entry_open_the_uv_editor(self):
        self.tk.UiUtils.open_editor.return_value = "TextureViewWindow"
        self.slots.b031()
        self.slots.uv_editor()
        self.assertEqual(
            self.tk.UiUtils.open_editor.call_args_list, [mock.call("UV Editor")] * 2
        )
        self.assertEqual(self.messages(), [])

    def test_b031_says_so_when_the_editor_cannot_open(self):
        self.tk.UiUtils.open_editor.return_value = None
        self.slots.b031()
        self.assertIn("UV Editor", self.messages()[0])

    def test_uv_snapshot_is_the_hosts_dialog_and_shows_a_refusal(self):
        self.tk.UvUtils.export_uv_image.side_effect = ValueError("needs a UV map")
        self.slots.uv_snapshot()
        self.tk.UvUtils.export_uv_image.assert_called_once_with()
        self.assertEqual(self.messages(), ["needs a UV map"])

    def test_header_gates_the_rizom_bridge_on_its_app(self):
        widget = mock.MagicMock()
        with mock.patch.object(UvSlots, "gate_on_app") as gate:
            self.slots.header_init(widget)
        target, resolve = gate.call_args.args
        self.assertIs(target, widget.menu.btn_rizom_bridge)
        self.assertIs(resolve(), self.tk.RizomUVBridge.APP)
        names = [c.kwargs.get("setObjectName") for c in widget.menu.add.call_args_list]
        self.assertEqual(names, ["uv_snapshot", "uv_editor", "btn_rizom_bridge"])


class TestPack(_SlotsCase):
    def setUp(self):
        super().setUp()
        # The summary formats the measured density as a number.
        self.tk.UvUtils.get_texel_density.return_value = 512.0

    def _result(self, **overrides):
        fields = dict(
            succeeded=["a", "b"], failed=[], tiles=(1, 1), targets=["a", "b"],
            objects=["a", "b"],
        )
        fields.update(overrides)
        return SimpleNamespace(**fields)

    def test_standard_sends_only_the_options_u3dlayout_honors(self):
        self.tk.UvUtils.pack_uvs.return_value = self._result()
        self.tk.UvUtils.get_texel_density.return_value = 512.0
        self.slots.tb000(_widget(**PACK_DEFAULTS))
        self.tk.UvUtils.pack_uvs.assert_called_once_with(
            ["pCube1"],
            engine="standard",
            map_size=2048,
            udim=1001,
            coverage=(1.0, 1.0),
            preserve_3d=True,
            pre_rotate=0,
            rotate_step=90,
            rotate_min=0,
            rotate_max=0,
            mutations=1,
            scale_mode=2,
            tiles=(1, 1),
            skip_instances=True,
        )
        text = self.messages()[0]
        self.assertIn("Successfully packed 2 mesh(es)", text)
        self.assertIn("512.0 px/unit", text)
        self.assertIn("Target UDIM:</b> 1001", text)

    def test_xatlas_sends_its_own_options(self):
        self.tk.UvUtils.pack_uvs.return_value = self._result()
        self.slots.tb000(_widget(**dict(PACK_DEFAULTS, cmb019="xatlas")))
        kwargs = self.tk.UvUtils.pack_uvs.call_args.kwargs
        self.assertEqual(kwargs["engine"], "xatlas")
        self.assertEqual(
            {k for k in kwargs if k not in ("engine", "map_size", "udim", "coverage", "preserve_3d")},
            {"rotate", "brute_force", "skip_instances"},
        )

    def test_one_packer_hosts_send_rotate_and_margin(self):
        """Blender: one packer, the method combo hidden; whatever it holds packs
        with the host's own."""
        self.tk.UvUtils.PACK_ENGINES = BLENDER_PACK_ENGINES
        self.tk.UvUtils.pack_uvs.return_value = self._result()
        self.slots.tb000(_widget(**dict(PACK_DEFAULTS, cmb019="xatlas")))
        kwargs = self.tk.UvUtils.pack_uvs.call_args.kwargs
        self.assertEqual(kwargs["engine"], "standard")
        self.assertEqual((kwargs["rotate"], kwargs["margin"]), (True, 0.001))
        self.assertNotIn("tiles", kwargs)

    def test_a_clamped_grid_and_skipped_meshes_are_reported(self):
        self.tk.UvUtils.pack_uvs.return_value = self._result(
            failed=[("c", "non-manifold vertices")], tiles=(1, 2)
        )
        self.slots.tb000(_widget(**dict(PACK_DEFAULTS, s004=1010, s019=2, s020=2)))
        text = self.messages()[0]
        self.assertIn("Skipped: 1", text)
        self.assertIn("1010-1020 (1 × 2)", text)
        self.assertIn("clamped", text)

    def test_a_refusal_is_shown_with_the_engine_note(self):
        self.tk.UvUtils.pack_uvs.side_effect = RuntimeError("pip install --user xatlas")
        self.slots.tb000(_widget(**dict(PACK_DEFAULTS, cmb019="xatlas")))
        self.assertIn("xatlas pack unavailable", self.messages()[0])
        self.assertIn("pip install", self.messages()[0])

    def test_nothing_selected_packs_nothing(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb000(_widget(**PACK_DEFAULTS))
        self.tk.UvUtils.pack_uvs.assert_not_called()
        self.assertEqual(self.messages(), [Slots.NOTHING_SELECTED])


class TestOptionBoxes(_SlotsCase):
    def _init(self, name, **values):
        """Run ``<name>_init`` on a fake option box; the created controls are on
        the menu by objectName, spin boxes answering *values*."""
        menu = mock.MagicMock()
        widget = SimpleNamespace(option_box=SimpleNamespace(menu=menu))

        def add(*args, **kwargs):
            control = mock.MagicMock()
            control.value.return_value = values.get(kwargs.get("setObjectName"), 1)
            setattr(menu, kwargs.get("setObjectName"), control)
            return control

        menu.add.side_effect = add
        getattr(self.slots, f"{name}_init")(widget)
        return menu

    @staticmethod
    def _tag(control):
        calls = [c.args for c in control.setProperty.call_args_list if c.args[0] == "requires"]
        return calls[0][1] if calls else None

    def test_pack_tags(self):
        menu = self._init("tb000")
        maya = ("cmb019", "chk043", "cmb010", "s011", "s012", "s013", "s014", "cmb018", "s019", "s020", "chk016")
        for name in maya:
            self.assertEqual(self._tag(getattr(menu, name)), "maya", name)
        self.assertEqual(self._tag(menu.s_pack_margin), "blender")
        for name in ("chk044", "cmb009", "s004", "cmb015"):
            self.assertIsNone(self._tag(getattr(menu, name)), name)

    def test_pack_gates_follow_the_packers_table(self):
        menu = self._init("tb000")
        menu.cmb019.currentData.return_value = "xatlas"
        menu.cmb019.currentIndexChanged.connect.call_args.args[0]()
        menu.chk044.setEnabled.assert_called_with(True)
        menu.cmb010.setEnabled.assert_called_with(False)
        menu.s_pack_margin.setEnabled.assert_called_with(False)
        self.tk.UvUtils.PACK_ENGINES = BLENDER_PACK_ENGINES
        menu.cmb019.currentIndexChanged.connect.call_args.args[0]()
        menu.chk044.setEnabled.assert_called_with(True)
        menu.s_pack_margin.setEnabled.assert_called_with(True)
        menu.s019.setEnabled.assert_called_with(False)

    def test_rotate_step_needs_a_range_and_a_grid_locks_coverage(self):
        menu = self._init("tb000", s012=0, s013=180, s019=2, s020=1)
        menu.cmb019.currentData.return_value = "standard"
        menu.cmb019.currentIndexChanged.connect.call_args.args[0]()
        menu.s011.setEnabled.assert_called_with(True)
        menu.cmb015.setEnabled.assert_called_with(False)

    def test_auto_unwrap_and_unfold_tags(self):
        menu = self._init("tb001")
        self.assertEqual(self._tag(menu.cmb012), "maya")
        self.assertEqual(self._tag(menu.s_smart_angle), "blender")
        self.assertEqual(self._tag(menu.s_smart_margin), "blender")
        self.assertIsNone(self._tag(menu.cmb011))
        menu = self._init("tb004")
        self.assertEqual(self._tag(menu.cmb013), "maya")
        self.assertEqual(self._tag(menu.cmb_unfold_method), "blender")
        self.assertEqual(self._tag(menu.s_unfold_margin), "blender")
        for name in ("chk017", "chk007", "chk022", "s000"):
            self.assertIsNone(self._tag(getattr(menu, name)), name)

    def test_cut_cylinder_knobs_are_maya_s(self):
        menu = self._init("tb009")
        for name in ("s021", "s022", "s023", "chk045", "chk040", "chk046"):
            self.assertEqual(self._tag(getattr(menu, name)), "maya", name)
        for name in ("s016", "chk041", "chk042"):
            self.assertIsNone(self._tag(getattr(menu, name)), name)

    def test_combo_item_orders_are_kept(self):
        menu = self._init("tb000")
        self.assertEqual(
            [c.args[1] for c in menu.cmb009.addItem.call_args_list], [0, 1]
        )
        self.assertEqual(
            [c.args[1] for c in menu.cmb018.addItem.call_args_list], [2, 1, 3]
        )
        menu = self._init("tb001")
        self.assertEqual(
            [c.args[1] for c in menu.cmb011.addItem.call_args_list],
            ["standard", "hard", "organic"],
        )


class TestAutoUnwrap(_SlotsCase):
    def test_engine_modes_run_auto_unwrap(self):
        self.tk.UvUtils.auto_unwrap.return_value = SimpleNamespace(
            engine="mof", succeeded=["pCube1"], failed=[]
        )
        self.slots.tb001(_widget(cmb011="hard"))
        self.tk.UvUtils.auto_unwrap.assert_called_once_with(
            ["pCube1"], method="hard", map_size=2048
        )
        self.tk.UvUtils.auto_project.assert_not_called()

    def test_a_missing_engine_is_reported_not_raised(self):
        self.tk.UvUtils.auto_unwrap.side_effect = FileNotFoundError(
            "not installed: https://example/download"
        )
        self.slots.tb001(_widget(cmb011="organic"))
        self.assertIn("https://", self.messages()[0])

    def test_standard_runs_the_hosts_projection(self):
        self.tk.UvUtils.auto_project.return_value = SimpleNamespace(
            engine="standard", succeeded=["pCube1"], failed=[]
        )
        self.slots.tb001(
            _widget(cmb011="standard", cmb012=1, s_smart_angle=66, s_smart_margin=0.0)
        )
        kwargs = self.tk.UvUtils.auto_project.call_args.kwargs
        self.assertEqual(
            (kwargs["map_size"], kwargs["scale_mode"], kwargs["angle_limit"], kwargs["margin"]),
            (2048, 1, 66, 0.0),
        )
        self.assertTrue(callable(kwargs["progress_callback"]))
        self.assertEqual(self.messages(), [])  # quiet on a clean run

    def test_standard_failures_are_listed(self):
        self.tk.UvUtils.auto_project.return_value = SimpleNamespace(
            engine="standard", succeeded=[], failed=[("pCube1", "boom")]
        )
        self.slots.tb001(
            _widget(cmb011="standard", cmb012=1, s_smart_angle=66, s_smart_margin=0.0)
        )
        self.assertIn("Standard", self.messages()[0])
        self.assertIn("boom", self.messages()[0])

    def test_no_selection_warns(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb001(_widget(cmb011="hard"))
        self.tk.UvUtils.auto_unwrap.assert_not_called()
        self.assertEqual(self.messages(), [Slots.NOTHING_SELECTED])


class TestUnfold(_SlotsCase):
    def _result(self, **fields):
        base = dict(unfolded=["pCube1"], repaired=None, blocked=None, components=[])
        base.update(fields)
        return SimpleNamespace(**base)

    def test_sends_every_option(self):
        self.tk.UvUtils.unfold_uvs.return_value = self._result()
        self.slots.tb004(_widget(**UNFOLD_DEFAULTS))
        self.tk.UvUtils.unfold_uvs.assert_called_once_with(
            ["pCube1"],
            optimize=True,
            orient=True,
            stack_similar=True,
            tolerance=1.0,
            map_size=2048,
            repair=False,
            method="angle_based",
            margin=0.0,
        )
        self.assertEqual(self.messages(), [])

    def test_blocked_explains_and_points_at_repair(self):
        self.tk.UvUtils.unfold_uvs.return_value = self._result(
            unfolded=[], blocked="geometry", components=["a.vtx[1]"]
        )
        self.slots.tb004(_widget(**dict(UNFOLD_DEFAULTS, cmb013="repair")))
        self.assertTrue(self.tk.UvUtils.unfold_uvs.call_args.kwargs["repair"])
        text = self.messages()[0]
        self.assertIn("non-manifold geometry", text)
        self.assertIn("<b>1</b> problem vertex selected in vertex mode", text)

    def test_blocked_by_uvs_says_uvs(self):
        self.tk.UvUtils.unfold_uvs.return_value = self._result(
            unfolded=[], blocked="uvs", components=["a.map[1]", "a.map[2]"]
        )
        self.slots.tb004(_widget(**UNFOLD_DEFAULTS))
        self.assertIn("non-manifold UVs", self.messages()[0])
        self.assertIn("2</b> problem UVs", self.messages()[0])

    def test_a_repair_that_worked_is_noted(self):
        self.tk.UvUtils.unfold_uvs.return_value = self._result(
            repaired={"total": 3, "fixed": 3, "remaining": 0}
        )
        self.slots.tb004(_widget(**UNFOLD_DEFAULTS))
        self.assertIn("auto-repaired", self.messages()[0])
        self.assertIn("<b>3</b> components fixed", self.messages()[0])

    def test_a_refusal_is_shown(self):
        self.tk.UvUtils.unfold_uvs.side_effect = RuntimeError("Unfold failed: boom.")
        self.slots.tb004(_widget(**UNFOLD_DEFAULTS))
        self.assertEqual(self.messages(), ["Unfold failed: boom."])

    def test_b021_unfolds_then_packs_in_one_undo_step(self):
        order = []
        self.slots.ui.tb004 = SimpleNamespace(call_slot=lambda: order.append("tb004"))
        self.slots.ui.tb000 = SimpleNamespace(call_slot=lambda: order.append("tb000"))
        self.slots.b021(None)
        self.tk.CoreUtils.undo_chunk.assert_called_once_with("Unfold + Pack")
        self.assertEqual(order, ["tb004", "tb000"])


class TestCleanupUvSets(_SlotsCase):
    def test_reports_each_mesh_in_mayatk_s_field_names(self):
        self.tk.Diagnostics.cleanup_uv_sets.return_value = [
            SimpleNamespace(
                shape="aShape", error=None, initial_sets=["uv", "x"], primary_set="uv",
                final_name="map1", sets_to_delete=["x"],
            ),
            SimpleNamespace(
                shape="bShape", error="no UV sets", initial_sets=[], primary_set=None,
                final_name=None, sets_to_delete=[],
            ),
        ]
        self.slots.tb007(
            _widget(chk029=True, chk035=True, chk036=False, chk037=True, chk038=False, chk030=False)
        )
        self.tk.Diagnostics.cleanup_uv_sets.assert_called_once_with(
            ["pCube1"],
            remove_empty=True,
            keep_only_primary=False,
            rename_to_map1=True,
            force_rename=False,
            prefer_largest_area=True,
            dry_run=False,
        )
        text = self.messages()[0]
        self.assertIn("Cleanup Complete", text)
        self.assertIn("Kept '<b>uv</b>' → renamed to '<b>map1</b>', deleted 1 others", text)
        self.assertIn("bShape</b>: no UV sets", text)

    def test_dry_run_says_would(self):
        self.tk.Diagnostics.cleanup_uv_sets.return_value = [
            SimpleNamespace(
                shape="a", error=None, initial_sets=["map1"], primary_set="map1",
                final_name="map1", sets_to_delete=[],
            )
        ]
        self.slots.tb007(
            _widget(chk029=True, chk035=True, chk036=False, chk037=True, chk038=False, chk030=True)
        )
        self.assertIn("Dry Run Report", self.messages()[0])
        self.assertIn("Would keep", self.messages()[0])


class TestCutCylinder(_SlotsCase):
    def test_options_pass_through(self):
        self.tk.UvUtils.unwrap_cylinder.return_value = ["pCube1"]
        self.slots.tb009(_widget(**dict(CYLINDER_DEFAULTS, chk046=True, s023=8)))
        kwargs = self.tk.UvUtils.unwrap_cylinder.call_args.kwargs
        self.assertIs(kwargs["camera"], True)  # the active view's camera
        self.assertFalse(kwargs["sew"])
        self.assertAlmostEqual(kwargs["trim_ratio"], 0.08)
        self.assertEqual(
            (kwargs["angle"], kwargs["taper_angle"], kwargs["flat_angle"], kwargs["map_size"]),
            (45, 20, 60, 2048),
        )

    def test_hide_off_sends_no_camera(self):
        self.tk.UvUtils.unwrap_cylinder.return_value = ["pCube1"]
        self.slots.tb009(_widget(**dict(CYLINDER_DEFAULTS, chk045=False)))
        self.assertIsNone(self.tk.UvUtils.unwrap_cylinder.call_args.kwargs["camera"])

    def test_no_seams_found_is_said(self):
        self.tk.UvUtils.unwrap_cylinder.return_value = []
        self.slots.tb009(_widget(**CYLINDER_DEFAULTS))
        self.assertIn("No cylinder seams found", self.messages()[0])


class TestEditOperations(_SlotsCase):
    def test_cut_and_sew_take_the_selection(self):
        for slot, op in (("b005", "cut_uvs"), ("b011", "sew_uvs")):
            with self.subTest(slot=slot):
                getattr(self.tk.UvUtils, op).return_value = ["e"]
                getattr(self.slots, slot)()
                getattr(self.tk.UvUtils, op).assert_called_once_with(None)
        self.assertEqual(self.messages(), [])

    def test_cut_with_nothing_to_cut_says_so(self):
        self.tk.UvUtils.cut_uvs.return_value = []
        self.slots.b005()
        self.assertIn("Nothing selected", self.messages()[0])

    def test_cut_outside_edit_mode_shows_the_refusal(self):
        self.tk.UvUtils.sew_uvs.side_effect = ValueError("Select edges in Edit Mode")
        self.slots.b011()
        self.assertEqual(self.messages(), ["Select edges in Edit Mode"])

    def test_cut_hard_edges_sends_its_band(self):
        self.tk.UvUtils.cut_hard_edges.return_value = ["pCube1"]
        self.slots.tb022(_widget(s017=60.0, s018=170.0, chk025=True, chk026=False))
        self.tk.UvUtils.cut_hard_edges.assert_called_once_with(
            None, low_angle=60.0, high_angle=170.0, uv_borders=True, auto_seams=False
        )

    def test_texel_density_get_and_set(self):
        self.tk.UvUtils.get_texel_density.return_value = 256.0
        self.slots.b003()
        self.slots.ui.s003.setValue.assert_called_once_with(256.0)
        self.slots.ui.s003.value.return_value = 512.0
        self.slots.b004()
        self.tk.UvUtils.set_texel_density.assert_called_once_with(
            ["pCube1"], density=512.0, map_size=2048
        )


class TestToggles(_SlotsCase):
    def test_pin_toggles_on_one_scope_and_starts_over_on_a_new_one(self):
        self.tk.UvUtils.uv_scope_key.return_value = ("a",)
        self.tk.UvUtils.pin_uvs.return_value = ["a.map[0:3]"]
        for _ in range(3):
            self.slots.b029(None)
        self.tk.UvUtils.uv_scope_key.return_value = ("b",)
        self.slots.b029(None)
        pins = [c.kwargs["pin"] for c in self.tk.UvUtils.pin_uvs.call_args_list]
        self.assertEqual(pins, [True, False, True, True])

    def test_pin_with_no_uvs_says_so_and_keeps_the_state(self):
        self.tk.UvUtils.pin_uvs.return_value = []
        self.slots.b029(None)
        self.assertIn("No UVs", self.messages()[0])
        self.assertIsNone(self.slots._b029_key)

    def _stack(self, mode="similar", pin=False):
        self.slots.b030(_widget(cmb020=mode, s024=1.0, chk047=pin))

    def test_stack_then_unstack(self):
        self.tk.UvUtils.uv_scope_key.return_value = ("a",)
        self.tk.UvUtils.get_uv_coords.return_value = {"a.map[0]": (0.0, 0.0, 0.0)}
        self.tk.UvUtils.stack_uv_shells.return_value = ["a.map[0]"]
        self._stack(pin=True)
        self.tk.UvUtils.stack_uv_shells.assert_called_once_with(
            ["pCube1"], tolerance=1.0, pin=True
        )
        self._stack(pin=True)  # same scope: Unstack
        self.tk.UvUtils.set_uv_coords.assert_called_once_with(
            ["pCube1"], {"a.map[0]": (0.0, 0.0, 0.0)}
        )
        self._stack(mode="center")  # stacks again, all shells
        self.assertIsNone(self.tk.UvUtils.stack_uv_shells.call_args.kwargs["tolerance"])

    def test_similar_with_no_match_reports_and_stays_unstacked(self):
        self.tk.UvUtils.get_uv_coords.return_value = {"a.map[0]": (0.0, 0.0, 0.0)}
        self.tk.UvUtils.stack_uv_shells.return_value = []
        self._stack()
        self.assertIn("No similar shells", self.messages()[0])
        self.assertIsNone(self.slots._b030_snapshot)

    def test_center_with_nothing_moved_reports(self):
        self.tk.UvUtils.get_uv_coords.return_value = {"o": [(0.0, 0.0, False)]}
        self.tk.UvUtils.stack_uv_shells.return_value = 0  # Blender: a count
        self._stack(mode="center")
        self.assertIn("No UV shells stacked", self.messages()[0])

    def test_no_uvs_stacks_nothing(self):
        self.tk.UvUtils.get_uv_coords.return_value = {}
        self._stack()
        self.tk.UvUtils.stack_uv_shells.assert_not_called()
        self.assertIn("No UVs", self.messages()[0])


class TestUvSlotSurface(unittest.TestCase):
    """Source-level pins: the Auto Unwrap option box was trimmed to three modes
    on 2026-07-28 and the Cut Cylinder algorithm picker was replaced by per-mesh
    detection; these keep the removed widgets from creeping back."""

    ENGINE_LABELS = ("Hard Surface (Ministry of Flat)", "Organic (BFF)")
    REMOVED = ("cmb016", "cmb017", "chk000", "chk_pack_rotate")

    @staticmethod
    def _source():
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tentacle",
            "slots",
            "uv.py",
        )
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_engine_labels_are_the_shared_ones(self):
        source = self._source()
        for label in self.ENGINE_LABELS:
            self.assertIn(label, source)

    def test_removed_widgets_are_gone(self):
        source = self._source()
        for name in self.REMOVED:
            self.assertNotIn(name, source, f"{name} should have been removed")


# --------------------------------------------------------------------------- in Maya
class _RecordedProgress:
    """The slice of ``Switchboard.progress`` a slot uses; records the texts."""

    def __init__(self, log, text):
        self._log = log
        self._text = text

    def __enter__(self):
        self._log.append(self._text)
        return self._tick

    def _tick(self, value=None, text=None):
        if text:
            self._log.append(text)
        return True  # never cancelled

    def __exit__(self, *exc):
        return False


class _RecordedSb:
    """A switchboard over the real ``mtk``."""

    def __init__(self):
        self.messages = []
        self.progress_texts = []
        self.tk = mtk

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))

    def progress(self, ui=None, total=None, text=""):
        return _RecordedProgress(self.progress_texts, text)


def _maya_slots():
    """The composed class over the real ``mtk``, without the UI-loading init."""
    instance = UvSlots.__new__(UvSlots)
    instance.sb = _RecordedSb()
    instance.ui = SimpleNamespace(cmb003=SimpleNamespace(currentText=lambda: "2048"))
    return instance


def _text(instance):
    return " ".join(str(args) for args, _ in instance.sb.messages)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class _MayaCase(unittest.TestCase):
    #: u3d commands a case stubs: loaded first, so the plug-in's own load (inside
    #: the operation) cannot put the real command back over a stub.
    STUBS = ()

    def setUp(self):
        cmds.file(new=True, force=True)
        cmds.loadPlugin("Unfold3D", quiet=True)
        self.instance = _maya_slots()
        self._saved = {name: getattr(cmds, name) for name in self.STUBS}
        self.addCleanup(self._restore)

    def _restore(self):
        for name, command in self._saved.items():
            setattr(cmds, name, command)
        cmds.file(new=True, force=True)


class TestCutSewInMaya(_MayaCase):
    """b005 / b011 route to polyMapCut / polyMapSew: the selected edges, else
    every edge of each selected mesh (by full path: two transforms sharing a
    leaf name make their shapes' short names ambiguous)."""

    STUBS = ("polyMapCut", "polyMapSew")

    def setUp(self):
        super().setUp()
        self.cut, self.cut_kwargs, self.sewn = [], [], []

        def _fake_cut(*args, **kwargs):
            self.cut.append(args[0] if args else None)
            self.cut_kwargs.append(kwargs)

        cmds.polyMapCut = _fake_cut
        cmds.polyMapSew = lambda *a, **k: self.sewn.append(a[0])

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.b005()
        self.instance.b011()
        self.assertEqual((self.cut, self.sewn), ([], []))
        self.assertIn("nothing selected", _text(self.instance).lower())

    def test_edge_selection_cuts_with_history(self):
        cube = cmds.polyCube(name="uv_cut_cube")[0]
        cmds.select(f"{cube}.e[0:3]")
        self.instance.b005()
        self.assertTrue(self.cut)
        self.assertTrue(all(k.get("constructionHistory") for k in self.cut_kwargs))

    def test_transform_selection_cuts_all_mesh_edges(self):
        cube = cmds.polyCube(name="uv_cut_all")[0]
        cmds.select(cube)
        self.instance.b005()
        self.assertIn(".e[", " ".join(str(c) for c in self.cut))

    def test_sews_meshes_with_colliding_short_shape_names(self):
        g1 = cmds.group(empty=True, name="grpA")
        cmds.parent(cmds.polyCylinder(name="dupCyl")[0], g1)
        g2 = cmds.group(empty=True, name="grpB")
        cmds.parent(cmds.polyCylinder(name="dupCyl")[0], g2)
        cmds.select([f"{g1}|dupCyl", f"{g2}|dupCyl"])
        self.instance.b011()
        self.assertEqual(len(self.sewn), 2)
        self.assertTrue(all(s.startswith("|grp") and ".e[*]" in s for s in self.sewn))


class _UnfoldMayaCase(_MayaCase):
    STUBS = ("u3dUnfold", "u3dOptimize", "polyUVStackSimilarShells")

    def setUp(self):
        super().setUp()
        self.unfold_calls, self.optimize_calls, self.stack_calls = [], [], []
        cmds.u3dUnfold = lambda *a, **k: self.unfold_calls.append((a, k))
        cmds.u3dOptimize = lambda *a, **k: self.optimize_calls.append((a, k))
        cmds.polyUVStackSimilarShells = lambda *a, **k: self.stack_calls.append((a, k))

    def unfold(self, **options):
        self.instance.tb004(_widget(**dict(UNFOLD_DEFAULTS, **options)))

    @staticmethod
    def raise_non_manifold(*args, **kwargs):
        raise RuntimeError(
            "Mesh has non-manifold vertices. Clean up the mesh before using unfold."
        )


class TestUnfoldInMaya(_UnfoldMayaCase):
    def test_non_manifold_refusal_is_caught_and_stops(self):
        cmds.select(cmds.polyCube()[0])
        cmds.u3dUnfold = self.raise_non_manifold
        self.unfold()
        self.assertIn("non-manifold", _text(self.instance).lower())
        self.assertEqual((self.optimize_calls, self.stack_calls), ([], []))

    def test_a_successful_unfold_runs_the_passes(self):
        cmds.select(cmds.polyCube()[0])
        self.unfold(chk007=False)  # orient is MEL over GUI selection masks
        self.assertEqual(self.instance.sb.messages, [])
        self.assertEqual((len(self.optimize_calls), len(self.stack_calls)), (1, 1))

    def test_nothing_selected_reports_instead_of_raising(self):
        """Regression: the orient pass is MEL (texOrientShells ->
        texCheckSelection) and raised on an empty selection."""
        cmds.select(clear=True)
        self.unfold()
        self.assertIn("nothing selected", _text(self.instance).lower())
        self.assertEqual(self.unfold_calls, [])

    def test_b021_reports_once_and_skips_both_steps(self):
        called = []
        self.instance.ui.tb004 = SimpleNamespace(call_slot=lambda: called.append("tb004"))
        self.instance.ui.tb000 = SimpleNamespace(call_slot=lambda: called.append("tb000"))
        cmds.select(clear=True)
        self.instance.b021(None)
        self.assertEqual(len(self.instance.sb.messages), 1)
        self.assertEqual(called, [])

    def test_a_seamless_mesh_gets_no_new_seams(self):
        """Regression: Unfold relaxes the existing UVs only -- seaming is Cut
        Cylinder's job; a sewn single-shell cylinder keeps its shell count."""
        mesh = cmds.polyCylinder(name="seamlessCyl")[0]
        cmds.polyMapSew(f"{mesh}.e[*]", constructionHistory=True)
        cmds.select(mesh, replace=True)
        before = cmds.polyEvaluate(mesh, uvShell=True)
        with (
            mock.patch.object(mtk.UvUtils, "unwrap_cylinder") as unwrap,
            mock.patch.object(cmds, "polyMapCut") as map_cut,
        ):
            self.unfold(chk007=False, chk022=False)
        unwrap.assert_not_called()
        map_cut.assert_not_called()
        self.assertEqual(cmds.polyEvaluate(mesh, uvShell=True), before)

    def test_component_mode_is_left_for_object_mode(self):
        """The whole-object unfold must not run scoped to a leftover component
        selection (the regression made the repair need a second click)."""
        mesh = cmds.polyPlane(w=1, h=1, sx=2, sy=2)[0]
        cmds.polyAutoProjection(mesh, ch=False)
        cmds.select(mesh, r=True)
        switched = []
        original = cmds.selectMode
        self.addCleanup(setattr, cmds, "selectMode", original)

        def spy(*args, **kwargs):
            if kwargs.get("object"):
                switched.append(True)
            return original(*args, **kwargs)

        cmds.selectMode = spy
        self.unfold(chk017=False, chk007=False, chk022=False)
        self.assertTrue(switched)
        self.assertEqual(len(self.unfold_calls), 1)
        self.assertEqual(self.instance.sb.messages, [])


class TestUnfoldNonManifoldInMaya(_UnfoldMayaCase):
    """Warn + Select vs Repair + Retry over a real bowtie mesh; only u3dUnfold
    is stubbed."""

    def setUp(self):
        super().setUp()
        p1 = cmds.polyPlane(w=1, h=1, sx=1, sy=1)[0]
        p2 = cmds.polyPlane(w=1, h=1, sx=1, sy=1)[0]
        cmds.move(1, 0, 1, p2)
        self.mesh = cmds.polyUnite(p1, p2, ch=False)[0]
        cmds.polyMergeVertex(self.mesh, d=0.001, ch=False)
        self.shape = cmds.listRelatives(self.mesh, shapes=True, ni=True)[0]
        cmds.select(self.mesh)
        cmds.u3dUnfold = self.raise_non_manifold

    def bare_unfold(self, mode):
        self.unfold(cmb013=mode, chk017=False, chk007=False, chk022=False)

    def selected_vertices(self):
        return [s for s in cmds.ls(sl=True, flatten=True) or [] if ".vtx[" in s]

    def test_select_mode_selects_and_warns(self):
        self.bare_unfold("select")
        self.assertTrue(self.selected_vertices())
        text = _text(self.instance).lower()
        self.assertIn("non-manifold", text)
        self.assertIn("vertex mode", text)

    def test_does_not_preempt_unfold_on_the_polyinfo_flag(self):
        """u3dUnfold's rejection is narrower than polyInfo's flag: when it
        accepts the mesh, the unfold proceeds -- no warning, no reselect."""
        self.assertTrue(mtk.Diagnostics.find_non_manifold_vertices([self.mesh]))
        cmds.u3dUnfold = lambda *a, **k: None
        self.bare_unfold("select")
        self.assertEqual(self.instance.sb.messages, [])
        self.assertEqual(self.selected_vertices(), [])

    def test_repair_mode_repairs_and_retries(self):
        calls = {"n": 0}

        def unfold(*args, **kwargs):
            calls["n"] += 1
            if cmds.polyInfo(self.shape, nonManifoldVertices=True):
                self.raise_non_manifold()

        cmds.u3dUnfold = unfold
        self.bare_unfold("repair")
        self.assertEqual(calls["n"], 2)
        self.assertIsNone(cmds.polyInfo(self.shape, nonManifoldVertices=True))
        self.assertIn("repair", _text(self.instance).lower())

    def test_repair_mode_falls_back_when_unrepairable(self):
        with mock.patch.object(mtk.MeshDiagnostics, "clean_geometry", lambda *a, **k: None):
            self.bare_unfold("repair")
        self.assertTrue(self.selected_vertices())
        self.assertIn("non-manifold", _text(self.instance).lower())

    def test_repair_mode_survives_a_cleanup_error(self):
        def boom(*args, **kwargs):
            raise RuntimeError("polyCleanup failed")

        with mock.patch.object(mtk.MeshDiagnostics, "clean_geometry", boom):
            self.bare_unfold("repair")  # must not raise
        self.assertIn("non-manifold", _text(self.instance).lower())


class TestCutCylinderInMaya(_MayaCase):
    """tb009 hands the option box to mtk.UvUtils.unwrap_cylinder."""

    def setUp(self):
        super().setUp()
        self.mesh = cmds.polyCylinder(name="cutCyl")[0]
        cmds.select(self.mesh, replace=True)

    def test_the_options_reach_unwrap_cylinder(self):
        with mock.patch.object(
            mtk.UvUtils, "unwrap_cylinder", return_value=[self.mesh]
        ) as unwrap:
            self.instance.tb009(_widget(**dict(CYLINDER_DEFAULTS, s016=30, chk040=True)))
        kwargs = unwrap.call_args.kwargs
        self.assertEqual((kwargs["angle"], kwargs["invert_seam"]), (30, True))
        self.assertIs(kwargs["camera"], True)
        self.assertEqual(self.instance.sb.messages, [])

    def test_nothing_selected_reports_and_stops(self):
        cmds.select(clear=True)
        with mock.patch.object(mtk.UvUtils, "unwrap_cylinder") as unwrap:
            self.instance.tb009(_widget(**CYLINDER_DEFAULTS))
        unwrap.assert_not_called()
        self.assertEqual(len(self.instance.sb.messages), 1)


class TestAutoUnwrapInMaya(_MayaCase):
    """tb001 routes the engine modes to UvUtils.auto_unwrap, Standard to the
    host's projection."""

    def setUp(self):
        super().setUp()
        self.calls = []

        def fake(objects, method=None, map_size=None, **kwargs):
            self.calls.append((objects, method, map_size))
            return SimpleNamespace(engine="mof", succeeded=list(objects), failed=[])

        patcher = mock.patch.object(mtk.UvUtils, "auto_unwrap", side_effect=fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_mode(self, mode):
        self.instance.tb001(
            _widget(cmb011=mode, cmb012=1, s_smart_angle=66, s_smart_margin=0.0)
        )

    def test_hard_mode_calls_the_engine_with_the_selection_and_map_size(self):
        cube = cmds.polyCube(name="tb001_hard")[0]
        cmds.select(cube)
        self.run_mode("hard")
        objects, method, map_size = self.calls[0]
        self.assertEqual((method, map_size), ("hard", 2048))
        self.assertIn(cube, objects)

    def test_standard_projects_without_the_engine(self):
        cube = cmds.polyCube(name="tb001_standard")[0]
        cmds.select(cube)
        self.run_mode("standard")
        self.assertEqual(self.calls, [])
        u0, v0, u1, v1 = mtk.UvUtils.get_uv_bounds(cube)
        self.assertGreaterEqual(min(u0, v0), -1e-4)
        self.assertLessEqual(max(u1, v1), 1.0 + 1e-4)

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.run_mode("hard")
        self.assertEqual(self.calls, [])
        self.assertTrue(self.instance.sb.messages)


def _pack_widget(**overrides):
    return _widget(**dict(PACK_DEFAULTS, **overrides))


class TestPackInMaya(_MayaCase):
    """tb000 over mtk.UvUtils.pack_uvs, pinned against behavior verified live in
    Maya 2025: packBox anchors at the UDIM; layoutScaleMode omitted == Uniform,
    1 keeps the shell scale; tileU/tileV distribute across a grid; a single-mesh
    failure reports with no probe pass; both methods pack exactly the selection."""

    def bbox2d(self, obj):
        return cmds.polyEvaluate(obj, boundingBox2d=True)

    def test_default_pack_fills_the_target_tile(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        b = cmds.polyCube(name="packB", ch=False)[0]
        cmds.select(a, b)
        self.instance.tb000(_pack_widget())
        for obj in (a, b):
            (u0, u1), (v0, v1) = self.bbox2d(obj)
            self.assertGreaterEqual(min(u0, v0), 0.0)
            self.assertLessEqual(max(u1, v1), 1.0)
        self.assertIn("UV Pack Complete", _text(self.instance))

    def test_udim_anchor_offsets_the_pack_box(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        cmds.select(a)
        self.instance.tb000(_pack_widget(s004=1002))
        (u0, u1), _ = self.bbox2d(a)
        self.assertGreaterEqual(u0, 1.0)
        self.assertLessEqual(u1, 2.0)

    def test_scale_mode_off_preserves_the_shell_scale(self):
        a = cmds.polyPlane(name="packA", sx=1, sy=1, ch=False)[0]
        uvs = cmds.polyListComponentConversion(a, fromFace=True, toUV=True)
        cmds.polyEditUV(uvs, pivotU=0.0, pivotV=0.0, scaleU=0.3, scaleV=0.3)
        cmds.select(a)
        self.instance.tb000(_pack_widget(cmb009=0, cmb018=1))
        (u0, u1), (v0, v1) = self.bbox2d(a)
        self.assertAlmostEqual(u1 - u0, 0.3, places=3)
        self.assertAlmostEqual(v1 - v0, 0.3, places=3)

    def test_tile_grid_spans_udims_and_reports_the_range(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        b = cmds.polyCube(name="packB", ch=False)[0]
        cmds.select(a, b)
        self.instance.tb000(_pack_widget(s019=2))
        u_maxes = [self.bbox2d(obj)[0][1] for obj in (a, b)]
        u_mins = [self.bbox2d(obj)[0][0] for obj in (a, b)]
        self.assertGreater(max(u_maxes), 1.0)
        self.assertLess(min(u_mins), 1.0)
        self.assertIn("1001-1002", _text(self.instance))

    @staticmethod
    def _mixed_content():
        """16 primitives at mixed scales plus two cut meshes: content on which
        u3dLayout's own Distribute grid mode stacks shells. Seeded."""
        import random

        rng = random.Random(11)
        makers = [
            cmds.polySphere, cmds.polyCylinder, cmds.polyTorus, cmds.polyCone,
            cmds.polyCube, cmds.polyPipe, cmds.polyHelix,
        ]
        out = []
        for _ in range(14):
            obj = rng.choice(makers)(ch=False)[0]
            scale = rng.uniform(0.1, 3.0)
            cmds.xform(obj, s=(scale, scale * rng.uniform(0.3, 3), scale))
            out.append(obj)
        cube = cmds.polyCube(ch=False)[0]
        cmds.polyMapCut(f"{cube}.e[*]", ch=False)
        sphere = cmds.polySphere(sx=16, sy=12, ch=False)[0]
        cmds.polyMapCut(cmds.ls(f"{sphere}.e[*]", flatten=True)[::4], ch=False)
        return out + [cube, sphere]

    def test_tile_grid_never_stacks_shells(self):
        """User-reported: Pack left overlapping shells with Tiles U/V > 1."""
        objs = self._mixed_content()
        cmds.select(objs)
        self.instance.tb000(_pack_widget(s019=2, s020=2))
        faces = cmds.polyListComponentConversion(objs, toFace=True)
        overlapping = cmds.ls(cmds.polyUVOverlap(faces, oc=True) or [], flatten=True)
        self.assertEqual(overlapping, [])

    def test_tile_grid_clamps_to_the_udim_row_end(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        cmds.select(a)
        self.instance.tb000(_pack_widget(s004=1010, s019=2))
        (u0, u1), _ = self.bbox2d(a)
        self.assertGreaterEqual(u0, 9.0)
        self.assertLessEqual(u1, 10.0)
        text = _text(self.instance)
        self.assertIn("Target UDIM:</b> 1010", text)
        self.assertIn("clamped", text)

    def test_single_mesh_failure_reports_without_a_probe_pass(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        cmds.select(a)
        calls = []

        def boom(*args, **kwargs):
            calls.append((args, kwargs))
            raise RuntimeError("u3dLayout: non-manifold vertices")

        with mock.patch.object(cmds, "u3dLayout", side_effect=boom):
            self.instance.tb000(_pack_widget())
        self.assertEqual(len(calls), 1)
        text = _text(self.instance)
        self.assertIn("Skipped: 1", text)
        self.assertIn("non-manifold", text)

    @staticmethod
    def _parked_cube():
        cube = cmds.polyCube(name="packA", ch=False)[0]
        cmds.polyMapCut(f"{cube}.e[*]", ch=False)  # six separate shells
        cmds.polyEditUV(f"{cube}.map[*]", u=5.0, v=5.0)  # park the map off-tile
        return cube, cmds.polyEditUV(f"{cube}.map[*]", query=True)

    @staticmethod
    def _moved(before, after):
        return {
            i
            for i in range(len(before) // 2)
            if abs(before[2 * i] - after[2 * i]) > 1e-6
            or abs(before[2 * i + 1] - after[2 * i + 1]) > 1e-6
        }

    @staticmethod
    def _uv_ids(components):
        return {
            int(c.split("[")[1].rstrip("]"))
            for c in cmds.ls(cmds.polyListComponentConversion(components, toUV=True), flatten=True)
        }

    def test_xatlas_packs_into_the_target_tile(self):
        import pythontk as ptk

        if not ptk.UvPack.available():
            self.skipTest("xatlas not installed in this interpreter")
        a = cmds.polyCube(name="packA", ch=False)[0]
        b = cmds.polyCube(name="packB", ch=False)[0]
        cmds.select(a, b)
        with mock.patch.object(cmds, "u3dLayout", side_effect=AssertionError("native ran")):
            self.instance.tb000(_pack_widget(cmb019="xatlas", s004=1002))
        for obj in (a, b):
            (u0, u1), (v0, v1) = self.bbox2d(obj)
            self.assertGreaterEqual(u0, 1.0)
            self.assertLessEqual(u1, 2.0)
        self.assertIn("UV Pack Complete", _text(self.instance))

    def test_xatlas_honors_a_face_selection(self):
        import pythontk as ptk

        if not ptk.UvPack.available():
            self.skipTest("xatlas not installed in this interpreter")
        cube, before = self._parked_cube()
        scoped = self._uv_ids(f"{cube}.f[0:2]")
        cmds.select(f"{cube}.f[0:2]")
        self.instance.tb000(_pack_widget(cmb019="xatlas"))
        after = cmds.polyEditUV(f"{cube}.map[*]", query=True)
        self.assertEqual(self._moved(before, after), scoped)

    def test_standard_honors_a_face_selection(self):
        cube, before = self._parked_cube()
        scoped = self._uv_ids(f"{cube}.f[0:2]")
        cmds.select(f"{cube}.f[0:2]")
        self.instance.tb000(_pack_widget())
        moved = self._moved(before, cmds.polyEditUV(f"{cube}.map[*]", query=True))
        self.assertTrue(moved)
        self.assertTrue(moved <= scoped, "the pack reached outside the selection")

    def test_standard_widens_uv_edge_and_vertex_selections(self):
        for pick in ("uvs", "edge", "vertex"):
            with self.subTest(pick=pick):
                cmds.file(new=True, force=True)
                cube, before = self._parked_cube()
                selection = {
                    "uvs": cmds.polyListComponentConversion(f"{cube}.f[0]", toUV=True),
                    "edge": [f"{cube}.e[0]"],
                    "vertex": [f"{cube}.vtx[0]"],
                }[pick]
                scoped = self._uv_ids(cmds.polyListComponentConversion(selection, toFace=True))
                self.instance.sb = _RecordedSb()
                cmds.select(selection)
                self.instance.tb000(_pack_widget())
                moved = self._moved(before, cmds.polyEditUV(f"{cube}.map[*]", query=True))
                self.assertTrue(moved, _text(self.instance))
                self.assertTrue(moved <= scoped, "the pack reached outside")
                # One object, however many face ranges the pick widened to.
                self.assertIn("packed 1 mesh(es)", _text(self.instance))

    def test_a_missing_engine_reports_the_install_note(self):
        a = cmds.polyCube(name="packA", ch=False)[0]
        cmds.select(a)
        before = self.bbox2d(a)
        with mock.patch.object(
            mtk.UvUtils, "pack_uvs", side_effect=RuntimeError("pip install --user xatlas")
        ):
            self.instance.tb000(_pack_widget(cmb019="xatlas"))
        self.assertEqual(self.bbox2d(a), before)
        self.assertIn("pip install", _text(self.instance))


class TestStackInMaya(_MayaCase):
    """b030: Similar is polyUVStackSimilarShells (rotates identical shells into
    exact overlap), All shells texStackShells (translate only); the second
    click restores positions and prior pin weights."""

    def setUp(self):
        super().setUp()
        # texStackShells is MEL over GUI-only selection-mask queries (fails
        # headless): the call is captured instead -- the command is Maya's.
        self.mel_calls = []
        original = mel.eval
        self.addCleanup(setattr, mel, "eval", original)
        mel.eval = lambda command: self.mel_calls.append(command)

    @staticmethod
    def twins(rotate=37.0, scale=1.0):
        """Two identical 2x2 planes; B's shell rotated / scaled / moved off A's."""
        a = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="stackA")[0]
        b = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="stackB")[0]
        cmds.polyEditUV(f"{a}.map[*]", pu=0.5, pv=0.5, su=0.3, sv=0.3, r=True)
        cmds.polyEditUV(f"{a}.map[*]", u=-0.3, v=-0.3, r=True)
        cmds.polyEditUV(f"{b}.map[*]", pu=0.5, pv=0.5, su=0.3 * scale, sv=0.3 * scale, r=True)
        cmds.polyEditUV(f"{b}.map[*]", pu=0.5, pv=0.5, a=rotate, r=True)
        cmds.polyEditUV(f"{b}.map[*]", u=0.3, v=0.2, r=True)
        return a, b

    @staticmethod
    def uvs(obj):
        n = cmds.polyEvaluate(obj, uv=True)
        return [tuple(cmds.polyEditUV(f"{obj}.map[{i}]", q=True)) for i in range(n)]

    @staticmethod
    def max_dist(pa, pb):
        return max(((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2) ** 0.5 for x, y in zip(pa, pb))

    @staticmethod
    def pin(uv):
        return (cmds.polyPinUV(uv, q=True, value=True) or [0.0])[0]

    def stack(self, mode="similar", tolerance=1.0, pin=False):
        self.instance.b030(_widget(cmb020=mode, s024=tolerance, chk047=pin))

    def test_similar_rotates_twins_into_overlap_and_unstack_restores(self):
        a, b = self.twins()
        before_b = self.uvs(b)
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        self.stack()
        self.assertLess(self.max_dist(self.uvs(a), self.uvs(b)), 1e-5)
        self.assertEqual(self.instance.sb.messages, [])
        self.assertEqual(self.mel_calls, [])  # not the translate-only path
        self.stack()  # the same selection: Unstack
        self.assertLess(self.max_dist(self.uvs(b), before_b), 1e-6)
        self.assertIsNone(self.instance._b030_snapshot)

    def test_similar_matches_a_scaled_copy_too(self):
        a, b = self.twins(rotate=90.0, scale=0.5)
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        self.stack()
        self.assertLess(self.max_dist(self.uvs(a), self.uvs(b)), 1e-5)

    def test_an_object_selection_widens_to_faces(self):
        """polyUVStackSimilarShells ignores whole objects; the operation widens
        them to .f[*] as Maya's toolkit does, skipping a non-mesh."""
        a, b = self.twins()
        curve = cmds.circle(ch=False, name="stackCurve")[0]
        cmds.select(a, b, curve)
        self.stack()
        self.assertLess(self.max_dist(self.uvs(a), self.uvs(b)), 1e-5)
        self.assertEqual(self.instance.sb.messages, [])

    def test_similar_with_no_match_reports_and_stays_unstacked(self):
        a = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="lone2x2")[0]
        c = cmds.polyPlane(w=1, h=1, sx=3, sy=1, ch=False, name="lone3x1")[0]
        cmds.polyEditUV(f"{c}.map[*]", u=0.5, v=0.5, r=True)
        before = self.uvs(a) + self.uvs(c)
        cmds.select(f"{a}.f[*]", f"{c}.f[*]")
        self.stack(tolerance=0.1)
        self.assertEqual(before, self.uvs(a) + self.uvs(c))
        self.assertIn("No similar shells", _text(self.instance))
        self.assertIsNone(self.instance._b030_snapshot)  # the next click stacks again

    def test_all_shells_runs_texStackShells_on_the_uvs(self):
        a, b = self.twins()
        cmds.select(a, b)
        seen = []
        mel.eval = lambda command: seen.append((command, cmds.ls(sl=True)))
        self.stack(mode="center")
        self.assertEqual([command for command, _ in seen], ["texStackShells {}"])
        self.assertTrue(all(".map[" in item for item in seen[0][1]), seen[0][1])
        self.assertEqual(cmds.ls(sl=True), [a, b])  # the selection given back
        self.assertTrue(self.instance._b030_snapshot)

    def test_pin_after_stack_pins_and_unstack_restores_prior_weights(self):
        a, b = self.twins()
        cmds.polyPinUV(f"{a}.map[0]", value=1.0)  # a pin the user set beforehand
        before_b = self.uvs(b)
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        self.stack(pin=True)
        self.assertEqual((self.pin(f"{a}.map[4]"), self.pin(f"{b}.map[4]")), (1.0, 1.0))
        self.stack(pin=True)  # Unstack: positions back although pinned meanwhile
        self.assertLess(self.max_dist(self.uvs(b), before_b), 1e-6)
        self.assertEqual(self.pin(f"{a}.map[0]"), 1.0)  # the user's pin survives
        self.assertEqual((self.pin(f"{a}.map[4]"), self.pin(f"{b}.map[4]")), (0.0, 0.0))

    def test_unstack_moves_back_uvs_the_user_had_pinned(self):
        a, b = self.twins()
        cmds.polyPinUV(f"{b}.map[2]", value=1.0)
        before_b = self.uvs(b)
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        self.stack()
        self.assertGreater(self.max_dist(self.uvs(b), before_b), 0.01)
        self.stack()  # Unstack
        self.assertLess(self.max_dist(self.uvs(b), before_b), 1e-6)
        self.assertEqual(self.pin(f"{b}.map[2]"), 1.0)  # the weight restored

    def test_a_selection_change_resets_the_toggle(self):
        a, b = self.twins()
        cmds.select(f"{a}.f[*]", f"{b}.f[*]")
        self.stack()
        c, d = self.twins()
        cmds.select(f"{c}.f[*]", f"{d}.f[*]")
        self.stack()  # a fresh selection stacks (not Unstack)
        self.assertTrue(self.instance._b030_snapshot)
        self.assertLess(self.max_dist(self.uvs(c), self.uvs(d)), 1e-5)


# The cmb002 "UV Transform" menu, tb005 / tb006 / tb008 and the transfer option
# box moved to the shared tools (Shell Xform, Texture Combine): their coverage is
# test_shell_xform_panel.py / test_texture_combine_panel.py and the engines'
# test_uv_utils (mayatk unittest, blendertk check).


if __name__ == "__main__":
    unittest.main()
