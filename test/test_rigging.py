#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.rigging, the one Rigging Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- each control's call into the toolkit: the selection handed on, the option
  box's values as the operation's arguments, the message each answer becomes;
- the host's own lists building the pickers (utility nodes, auto-riggers, lock
  scopes) and Quick Rig's tool-panel names (a fragile string contract);
- the controls one host serves tagged ``requires`` (and the Maya-only display
  scale wired only where it is served).
The operations themselves are tested in mayatk and blendertk.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.rigging import RiggingSlots


def _widget(**values):
    """A widget whose option-box menu answers ``values``: a bool for a
    checkbox, a str for a line edit, ``("text", data)`` for a combo, a number
    for a spinbox."""
    widget = mock.MagicMock()
    menu = widget.option_box.menu
    for name, value in values.items():
        control = getattr(menu, name)
        if isinstance(value, bool):
            control.isChecked.return_value = value
        elif isinstance(value, str):
            control.text.return_value = value
        elif isinstance(value, tuple):
            control.currentText.return_value, control.currentData.return_value = value
        else:
            control.value.return_value = value
    return widget


def _affix_fields(menu, mode="convention", text=""):
    for name in ("t000", "t001", "t002"):
        field = getattr(menu, name)
        field.option_box.affix_mode = mode
        field.text.return_value = text


def _recording_menu():
    """A menu whose ``add`` records each widget by objectName (``made``)."""
    menu = mock.MagicMock()
    made = {}

    def add(kind, **kwargs):
        widget = mock.MagicMock(name=kwargs.get("setObjectName", kind))
        made[kwargs.get("setObjectName", kind)] = widget
        return widget

    menu.add.side_effect = add
    return menu, made


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.sb.apply_visibility_policy.return_value = False  # served (Maya)
        self.sb.ShortcutManager.host_namespace_suffix.return_value = "_maya"
        self.slots = RiggingSlots(self.sb)
        self.tk = self.sb.tk
        self.tk.CoreUtils.leaf_name.side_effect = lambda n: str(n).rsplit("|", 1)[-1]

    def message(self):
        return self.sb.message_box.call_args.args[0]


class TestRebindSkinClusters(_SlotsCase):
    def _summary(self, **buckets):
        summary = {"rebound": [], "no_skin_cluster": [], "wrong_type": [], "failed": []}
        summary.update(buckets)
        self.tk.RigUtils.rebind_skin_clusters.return_value = summary

    def test_nothing_selected_warns_and_skips_the_operation(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.b020()
        self.tk.RigUtils.rebind_skin_clusters.assert_not_called()
        self.assertIn("Nothing selected", self.message())

    def test_the_selection_is_rebound_and_counted(self):
        self.tk.CoreUtils.selected_objects.return_value = ["body"]
        self._summary(rebound=["body"])
        self.slots.b020()
        self.tk.RigUtils.rebind_skin_clusters.assert_called_once_with(["body"])
        self.assertIn("Rebound <hl>1</hl>", self.message())

    def test_each_failure_names_its_reason(self):
        self.tk.CoreUtils.selected_objects.return_value = ["x"]
        for buckets, words in (
            ({"no_skin_cluster": ["x"]}, "no skin"),
            ({"wrong_type": ["x"]}, "Incorrect object type"),
            ({"failed": [("x", "boom")]}, "Failed"),
        ):
            with self.subTest(words=words):
                self._summary(**buckets)
                self.slots.b020()
                self.assertIn(words, self.message())

    def test_a_partial_success_tallies_each_bucket(self):
        self.tk.CoreUtils.selected_objects.return_value = ["a", "b", "c"]
        self._summary(rebound=["a"], no_skin_cluster=["b"], wrong_type=["c"])
        self.slots.b020()
        msg = self.message()
        for words in ("Rebound", "without a skin", "wrong type", "See the console"):
            self.assertIn(words, msg)


class TestCreateUtilityNode(_SlotsCase):
    def test_the_host_lists_its_utility_nodes(self):
        self.tk.RigUtils.UTILITY_NODES = ("Cluster", "IK Handle", "Joints", "Lattice")
        widget = mock.MagicMock()
        self.slots.cmb001_init(widget)
        widget.add.assert_called_once_with(
            ["Cluster", "IK Handle", "Joints", "Lattice"], header="Utility Node:"
        )

    def test_a_pick_creates_that_node(self):
        self.slots.cmb001(1, mock.MagicMock(items=["Armature", "Empty"]))
        self.tk.RigUtils.create_utility_node.assert_called_once_with("Empty")

    def test_a_refusal_is_shown(self):
        self.tk.RigUtils.create_utility_node.side_effect = RuntimeError("no objects")
        self.slots.cmb001(0, mock.MagicMock(items=["Lattice"]))
        self.assertIn("no objects", self.message())


class TestQuickRig(_SlotsCase):
    """The procedural rigs open their tool panels by name (a fragile string
    contract); the host's own auto-riggers follow them."""

    PANELS = {
        "Tube Rig": "tube_rig",
        "Articulated Rig": "articulated_rig",
        "Wheel Rig": "wheel_rig",
        "Shadow Rig": "shadow_rig",
        "Telescope Rig": "telescope_rig",
    }

    def test_the_items_are_the_rigs_then_the_hosts_auto_riggers(self):
        self.tk.RigUtils.AUTO_RIGS = ("Quick Rig", "HumanIK")
        widget = mock.MagicMock()
        self.slots.cmb002_init(widget)
        widget.add.assert_called_once_with(
            list(self.PANELS) + ["Quick Rig", "HumanIK"], header="Quick Rig:"
        )

    def test_each_procedural_rig_opens_its_panel(self):
        items = list(self.PANELS)
        for index, text in enumerate(items):
            self.slots.cmb002(index, mock.MagicMock(items=items))
        shown = [c.args[0] for c in self.sb.handlers.marking_menu.show.call_args_list]
        self.assertEqual(shown, list(self.PANELS.values()))
        self.tk.RigUtils.auto_rig.assert_not_called()

    def test_a_host_rigger_runs_through_the_toolkit(self):
        self.slots.cmb002(0, mock.MagicMock(items=["Human Meta-Rig"]))
        self.tk.RigUtils.auto_rig.assert_called_once_with("Human Meta-Rig")
        self.sb.handlers.marking_menu.show.assert_not_called()

    def test_a_riggers_refusal_is_shown(self):
        self.tk.RigUtils.auto_rig.side_effect = ValueError("needs a meta-rig")
        self.slots.cmb002(0, mock.MagicMock(items=["Generate Rig"]))
        self.assertIn("needs a meta-rig", self.message())


class TestLocalRotationAxes(_SlotsCase):
    def test_the_joints_option_picks_what_toggles(self):
        for joints in (True, False):
            with self.subTest(joints=joints):
                self.tk.DisplayUtils.toggle_local_axes.return_value = True
                self.slots.tb000(_widget(chk000=joints))
                self.tk.DisplayUtils.toggle_local_axes.assert_called_with(
                    None, joints=joints
                )
                self.assertIn("On", self.message())

    def test_nothing_to_toggle_says_why(self):
        self.tk.DisplayUtils.toggle_local_axes.return_value = None
        self.slots.tb000(_widget(chk000=True))
        self.assertIn("No joints", self.message())
        self.slots.tb000(_widget(chk000=False))
        self.assertIn("Select the objects", self.message())

    def test_the_display_scale_is_mayas_and_mirrors_it(self):
        menu, made = _recording_menu()
        widget = mock.MagicMock()
        widget.option_box.menu = menu
        self.tk.DisplayUtils.joint_display_scale.return_value = 1.5
        self.slots.tb000_init(widget)
        for name in ("s000", "chk004", "chk001", "chk002"):
            made[name].setProperty.assert_called_once_with("requires", "maya")
            self.assertIs(made[name].restore_state, False)
        made["chk000"].setProperty.assert_not_called()  # both hosts
        made["s000"].setValue.assert_called_with(1.5)  # the live value, seeded

    def test_where_it_is_hidden_the_display_scale_is_never_read(self):
        self.sb.apply_visibility_policy.return_value = True  # Blender
        widget = mock.MagicMock()
        widget.option_box.menu, _made = _recording_menu()
        self.slots.tb000_init(widget)
        self.tk.DisplayUtils.joint_display_scale.assert_not_called()


class TestConstraintSwitch(_SlotsCase):
    def _menu(self, switch="sw", anchor="", weighted=False):
        return _widget(t003=switch, t004=anchor, chk003=weighted)

    def test_nothing_selected_warns_and_skips_the_operation(self):
        self.tk.CoreUtils.active_object.return_value = None
        self.slots.tb001(self._menu())
        self.tk.RigUtils.connect_switch_to_constraint.assert_not_called()
        self.assertIn("Nothing selected", self.message())

    def test_the_options_reach_the_operation(self):
        self.tk.CoreUtils.active_object.return_value = "con1"
        self.tk.RigUtils.connect_switch_to_constraint.return_value = {
            "switch_attr": "cube.mySwitch"
        }
        self.slots.tb001(self._menu("mySwitch", " worldLoc ", True))
        self.tk.RigUtils.connect_switch_to_constraint.assert_called_once_with(
            constraint_node="con1",
            attr_name="mySwitch",
            weighted=True,
            overwrite_existing=True,
            anchor="worldLoc",
        )
        self.assertIn("cube.mySwitch", self.message())

    def test_a_refusal_is_shown_with_the_hint(self):
        self.tk.CoreUtils.active_object.return_value = "cube"
        self.tk.RigUtils.connect_switch_to_constraint.side_effect = TypeError(
            "'cube' is not a constraint node."
        )
        self.slots.tb001(self._menu())
        self.assertIn("not a constraint", self.message())

    def test_nothing_built_points_at_the_console(self):
        self.tk.CoreUtils.active_object.return_value = "con1"
        self.tk.RigUtils.connect_switch_to_constraint.return_value = {}
        self.slots.tb001(self._menu())
        self.assertIn("Could not create", self.message())


class TestCreateLocator(_SlotsCase):
    def _widget(self, order="zyx", scale=2.0, display="ring"):
        widget = _widget(
            s001=scale,
            cmb011=(f"Rotate Order: {order}", order),
            cmb012=(f"Group Display: {display}", display),
            **{f"chk00{i}": False for i in range(5, 10)},
        )
        _affix_fields(widget.option_box.menu)
        return widget

    def test_nothing_selected_adds_a_lone_locator(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb003(self._widget())
        self.tk.RigUtils.add_locator.assert_called_once_with(size=2.0, rotate_order="zyx")
        self.tk.RigUtils.create_locator_at_object.assert_not_called()

    def test_the_selection_is_rigged_with_the_options(self):
        self.tk.CoreUtils.selected_objects.return_value = ["crate"]
        self.slots.tb003(self._widget())
        args, kwargs = self.tk.RigUtils.create_locator_at_object.call_args
        self.assertEqual(args, (["crate"],))
        self.assertEqual(kwargs["rotate_order"], "zyx")
        self.assertEqual(kwargs["group_display"], "ring")
        self.assertEqual(kwargs["loc_scale"], 2.0)
        # Scene mode hands the spelling and placement to the convention.
        for key in ("grp", "loc", "obj"):
            self.assertIsNone(kwargs[f"{key}_suffix"])
            self.assertEqual(kwargs[f"{key}_affix_mode"], "auto")

    def test_a_literal_affix_keeps_its_placement(self):
        self.tk.CoreUtils.selected_objects.return_value = ["crate"]
        widget = self._widget()
        _affix_fields(widget.option_box.menu, mode="prefix", text="X_")
        self.slots.tb003(widget)
        kwargs = self.tk.RigUtils.create_locator_at_object.call_args.kwargs
        self.assertEqual((kwargs["obj_suffix"], kwargs["obj_affix_mode"]), ("X_", "prefix"))

    def test_a_refusal_is_shown(self):
        self.tk.CoreUtils.selected_objects.return_value = ["crate"]
        self.tk.RigUtils.create_locator_at_object.side_effect = ValueError("bad order")
        self.slots.tb003(self._widget())
        self.assertIn("bad order", self.message())

    def test_the_group_display_is_blenders_and_the_affix_keys_per_host(self):
        widget = mock.MagicMock()
        widget.option_box.menu, made = _recording_menu()
        self.slots.tb003_init(widget)
        made["cmb012"].setProperty.assert_called_once_with("requires", "blender")
        data = [c.args[1] for c in made["cmb011"].addItem.call_args_list]
        self.assertEqual(data, list(RiggingSlots.ROTATE_ORDERS))  # saved index order
        keys = {
            name: made[name].option_box.set_affix.call_args.kwargs["settings_key"]
            for name in ("t000", "t001", "t002")
        }
        self.assertEqual(
            keys,
            {
                "t002": "rigging_create_locator_grp_affix_maya",
                "t000": "rigging_create_locator_loc_affix_maya",
                "t001": "rigging_create_locator_obj_affix_maya",
            },
        )

    def test_the_scene_affix_previews_the_active_objects_type(self):
        self.tk.CoreUtils.active_object.return_value = "cam1"
        self.tk.Naming.type_key.return_value = "camera"
        self.assertEqual(self.slots._locator_child_type_key(), "camera")
        self.tk.CoreUtils.active_object.return_value = None
        self.assertEqual(self.slots._locator_child_type_key(), "mesh")


class TestFixRotateOrder(_SlotsCase):
    def test_the_message_reports_each_change_and_what_kept(self):
        before = {"|a": "xyz", "|b": "zyx"}
        after = {"|a": "yzx", "|b": "zyx"}
        self.tk.XformUtils.get_rotate_order.side_effect = [before, after]
        self.slots._fix_rotate_order()
        self.tk.XformUtils.set_rotate_order.assert_called_once_with(["|a", "|b"], "auto")
        self.assertEqual(self.tk.XformUtils.get_rotate_order.call_args_list[0].args, (None,))
        msg = self.message()
        self.assertIn("a: xyz → yzx", msg)
        self.assertIn("Unchanged (b)", msg)

    def test_nothing_selected_says_so(self):
        self.tk.XformUtils.get_rotate_order.return_value = {}
        self.slots._fix_rotate_order()
        self.tk.XformUtils.set_rotate_order.assert_not_called()
        self.assertIn("Select the locator", self.message())


class TestRemoveLocator(_SlotsCase):
    def test_the_selection_is_handed_on(self):
        self.tk.CoreUtils.selected_objects.return_value = ["loc"]
        self.tk.RigUtils.remove_locator.return_value = ["|loc"]
        self.slots._remove_locator()
        self.tk.RigUtils.remove_locator.assert_called_once_with(["loc"])
        self.sb.message_box.assert_not_called()

    def test_no_rig_removed_says_so(self):
        self.tk.RigUtils.remove_locator.return_value = []
        self.slots._remove_locator()
        self.assertIn("No locator rig", self.message())


class TestLockUnlock(_SlotsCase):
    def test_the_host_lists_its_scopes(self):
        self.tk.RigUtils.LOCK_SCOPES = ("all", "translate", "rotate", "scale")
        widget = mock.MagicMock()
        widget.option_box.menu, made = _recording_menu()
        self.slots.tb004_init(widget)
        items = [c.args for c in made["cmb010"].addItem.call_args_list]
        self.assertEqual(
            items,
            [
                ("Attrs: All", "all"),
                ("Attrs: Translate", "translate"),
                ("Attrs: Rotate", "rotate"),
                ("Attrs: Scale", "scale"),
            ],
        )

    def test_the_options_reach_the_operation(self):
        self.tk.RigUtils.lock_transforms.return_value = (["|a", "|b"], ["rx", "ry", "rz"])
        self.slots.tb004(_widget(cmb_lock=("Lock", None), cmb010=("Attrs: Rotate", "rotate")))
        self.tk.RigUtils.lock_transforms.assert_called_once_with(
            None, lock=True, scope="rotate"
        )
        self.assertIn("Locked <hl>3</hl> attr(s) on <hl>2</hl>", self.message())

    def test_nothing_selected_and_refusals_are_shown(self):
        self.tk.RigUtils.lock_transforms.return_value = ([], [])
        self.slots.tb004(_widget(cmb_lock=("Unlock", None), cmb010=("Attrs: All", "all")))
        self.assertIn("Nothing selected", self.message())
        self.tk.RigUtils.lock_transforms.side_effect = ValueError("No attributes selected")
        self.slots.tb004(_widget(cmb_lock=("Lock", None), cmb010=("x", "channel_box")))
        self.assertIn("No attributes selected", self.message())


class TestAddToSkin(_SlotsCase):
    def test_needs_two_selected(self):
        self.tk.CoreUtils.selected_objects.return_value = ["bolt"]
        self.slots.tb005(_widget())
        self.tk.SkinUtils.add_to_skin.assert_not_called()
        self.assertIn("skinned mesh", self.message())

    def test_the_last_selected_is_the_skin(self):
        self.tk.CoreUtils.selected_objects.return_value = ["bolt", "nut", "|body"]
        self.slots.tb005(
            _widget(cmb_skin_mode=("Merge Into Skinned Mesh", True), chk_skin_rigid=True)
        )
        self.tk.SkinUtils.add_to_skin.assert_called_once_with(
            "|body", ["bolt", "nut"], combine=True, rigid=True
        )
        self.assertIn("Added <hl>2</hl> mesh(es) to <hl>body</hl>", self.message())


class TestRenderEffects(_SlotsCase):
    def test_opens_the_shared_panel(self):
        self.slots.b004()
        self.sb.handlers.marking_menu.show.assert_called_once_with("render_effects")


# ----------------------------------------------------------------------- in Maya
cmds = maya_module("maya.cmds")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestRiggingInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.tk = self.sb.tk

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_joints_and_ik_arm_their_tools_and_a_lattice_is_built(self):
        tools, lattices = [], []
        with mock.patch.object(cmds, "setToolTo", side_effect=tools.append), mock.patch.object(
            cmds, "lattice", side_effect=lambda *a, **k: lattices.append(k) or []
        ):
            items = list(self.tk.RigUtils.UTILITY_NODES)
            for text in ("Joints", "IK Handle", "Lattice"):
                self.slots.cmb001(items.index(text), mock.MagicMock(items=items))
        self.assertEqual(tools, ["jointContext", "ikHandleContext"])
        self.assertEqual(lattices[0].get("divisions"), [2, 5, 2])

    def test_no_joints_says_so(self):
        self.slots.tb000(_widget(chk000=True))
        self.assertIn("No joints", self.message())

    def test_a_constraint_gets_its_switch(self):
        src = cmds.spaceLocator(name="cs_src")[0]
        driven = cmds.polyCube(name="cs_cube")[0]
        con = cmds.parentConstraint(src, driven)[0]
        cmds.select(con)
        self.slots.tb001(_widget(t003="mySwitch", t004="", chk003=False))
        self.assertTrue(cmds.attributeQuery("mySwitch", node=driven, exists=True))
        self.assertIn("created", self.message())

    def test_a_non_constraint_is_refused(self):
        cmds.select(cmds.polyCube(name="plain_cube")[0])
        self.slots.tb001(_widget(t003="sw", t004="", chk003=False))
        self.assertIn("not a constraint", self.message())

    def test_rebind_names_why_nothing_was_rebound(self):
        cmds.select(cmds.polyCube(name="rb_cube")[0])
        self.slots.b020()
        self.assertIn("no skin", self.message())
        cmds.select(cmds.spaceLocator(name="rb_loc")[0])
        self.slots.b020()
        self.assertIn("Incorrect object type", self.message())

    def test_lock_and_unlock(self):
        cube = cmds.polyCube(name="lk_cube")[0]
        cmds.select(cube)
        self.slots.tb004(_widget(cmb_lock=("Lock", None), cmb010=("Attrs: All", "all")))
        self.assertTrue(cmds.getAttr(f"{cube}.tx", lock=True))
        self.assertTrue(cmds.getAttr(f"{cube}.sz", lock=True))
        self.slots.tb004(_widget(cmb_lock=("Unlock", None), cmb010=("Attrs: All", "all")))
        self.assertFalse(cmds.getAttr(f"{cube}.tx", lock=True))

    def _locator_widget(self, scale=1.0):
        widget = _widget(
            s001=scale,
            cmb011=("Rotate Order: zyx", "zyx"),
            cmb012=("Group Display: None", "none"),
            **{f"chk00{i}": False for i in range(5, 10)},
        )
        _affix_fields(widget.option_box.menu)
        return widget

    def _one_zyx_locator(self):
        locs = cmds.listRelatives(cmds.ls(type="locator"), parent=True) or []
        self.assertEqual(len(locs), 1)
        self.assertEqual(cmds.getAttr(f"{locs[0]}.rotateOrder", asString=True), "zyx")
        return locs[0]

    def test_the_rotate_order_reaches_the_rig(self):
        """The SOCKET_WRENCH bug: in xyz a Z spin after an X tilt keys all three."""
        cmds.select(cmds.polyCube(name="wrench")[0])
        self.slots.tb003(self._locator_widget())
        self.sb.message_box.assert_not_called()
        self._one_zyx_locator()

    def test_a_lone_locator_is_display_sized_and_ordered(self):
        cmds.select(clear=True)
        self.slots.tb003(self._locator_widget(scale=2.5))
        loc = self._one_zyx_locator()
        shape = cmds.listRelatives(loc, shapes=True, fullPath=True)[0]
        self.assertEqual(
            [round(v, 6) for v in cmds.getAttr(f"{shape}.localScale")[0]], [2.5] * 3
        )
        self.assertEqual([round(v, 6) for v in cmds.getAttr(f"{loc}.scale")[0]], [1.0] * 3)

    def test_fix_rotate_order_reads_the_turn_off_the_keys(self):
        """A locator lifted on X then turned about its own Y (SOCKET_WRENCH)
        gets a Y-first order, and the message says so."""
        loc = cmds.spaceLocator(name="wrench_LOC")[0]
        cmds.setKeyframe(loc, attribute="rotate", time=1)
        cmds.currentTime(10)
        cmds.setAttr(f"{loc}.rotate", 98.3, -6.4, -0.15)
        cmds.setKeyframe(loc, attribute="rotate", time=10)
        cmds.currentTime(20)
        cmds.rotate(0, 60, 0, loc, relative=True, objectSpace=True, forceOrderXYZ=True)
        cmds.setKeyframe(loc, attribute="rotate", time=20)
        cmds.select(loc)
        self.slots._fix_rotate_order()
        order = cmds.getAttr(f"{loc}.rotateOrder", asString=True)
        self.assertEqual(order[0], "y", order)
        self.assertIn(f"xyz → {order}", self.message())

    def test_remove_locator_dissolves_the_selected_rig(self):
        cmds.select(cmds.polyCube(name="rm_cube")[0])
        self.slots.tb003(self._locator_widget())
        loc = self._one_zyx_locator()
        cmds.select(loc)
        self.slots._remove_locator()
        self.assertFalse(cmds.ls(type="locator"))


if __name__ == "__main__":
    unittest.main()
