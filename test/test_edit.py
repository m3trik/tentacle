#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.edit, the one Edit Slots class: its
buttons (Mesh Cleanup, Delete History / Optimize, Delete, Lock / Unlock). The
Create / Convert / Transfer menus are test_edit_dispatchers.py's.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- tb000 (Mesh Cleanup): the option box reaches ``Diagnostics.cleanup_meshes``
  as keywords; the report is worded per case (duplicates, no mesh, nothing to
  look for, select per check or in all, repair counts, a failure); the
  options only one host serves are tagged ``requires``.
- tb001 (Delete History, Maya): the scope and cleanups reach
  ``NodeUtils.delete_history_in_scope``; in Maya, the empty-group sweep spares
  instances, rig nodes and connected transforms but not filed junk, the scope
  scopes, and Optimize Scene leaves the environment as it found it.
- tb005 (Optimize, Blender), tb002 (Delete), tb004 (Lock / Unlock).
The operations themselves are tested in mayatk and blendertk.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.edit import EditSlots


def _widget(**values):
    """A widget whose option-box menu holds fakes answering *values*."""
    widget = mock.MagicMock()
    for name, value in values.items():
        child = getattr(widget.option_box.menu, name)
        child.value.return_value = value
        child.isChecked.return_value = value
        child.currentData.return_value = value
        child.currentText.return_value = value
    return widget


#: tb000's option box at its defaults.
CLEANUP_DEFAULTS = dict(
    cmb_scope="selected",
    cmb_mode="select",
    chk026=True,
    chk024=False,
    s000=0.0001,
    chk032=True,
    chk033=True,
    chk028=True,
    chk029=False,
    chk002=True,
    chk017=True,
    chk010=False,
    chk011=False,
    chk003=False,
    chk012=False,
    chk018=True,
    chk016=False,
    chk015=False,
    s008=0.00001,
    chk013=True,
    s006=0.00001,
    chk014=True,
    s007=0.00001,
    chk025=False,
    chk022=False,
    chk023=False,
)


def _report(**overrides):
    """A ``cleanup_meshes`` report."""
    report = dict(
        objects=["mesh"],
        checks=["ngons"],
        duplicates=None,
        overlapping_faces=0,
        problems={},
        selected=0,
        repairs=[],
        vertices=(0, 0),
        faces=(0, 0),
    )
    report.update(overrides)
    return report


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = EditSlots(self.sb)
        self.tk = self.sb.tk

    def _message(self):
        call = self.sb.message_box.call_args
        return call.args[0] if call else None

    def _console(self):
        return [c.args[0] for c in self.sb.logger.log_raw.call_args_list]


class TestTb000MeshCleanup(_SlotsCase):
    def _run(self, report=None, **values):
        self.tk.Diagnostics.cleanup_meshes.return_value = report or _report()
        self.slots.tb000(_widget(**dict(CLEANUP_DEFAULTS, **values)))

    def test_the_option_box_reaches_cleanup_meshes(self):
        self._run(cmb_scope="visible", cmb_mode="repair", chk010=True, chk024=True)
        self.tk.Diagnostics.cleanup_meshes.assert_called_once_with(
            "visible",
            True,
            checks=[
                "ngons",
                "quads",
                "zero_area_faces",
                "zero_length_edges",
                "nonmanifold",
                "lamina",
            ],
            area_tolerance=0.00001,
            edge_length_tolerance=0.00001,
            uv_area_tolerance=0.00001,
            merge_vertices=True,
            merge_distance=0.0001,
            delete_history=True,
            delete_loose=True,
            dissolve_degenerate=True,
            recalculate_normals=True,
            fill_holes=False,
            overlapping_faces=False,
            overlapping_objects=False,
            omit_selected=False,
        )

    def test_overlapping_objects_report_their_count(self):
        self._run(_report(duplicates=2), cmb_mode="repair", chk022=True)
        self.assertIn("<hl>2</hl> overlapping duplicate objects deleted", self._message())

    def test_no_mesh_in_scope_says_so(self):
        self._run(_report(objects=[]))
        self.assertIn("No mesh found for scope", self._message())

    def test_select_with_nothing_to_look_for_asks_for_a_check(self):
        self._run(_report(checks=[]))
        self.assertIn("Enable a check", self._message())

    def test_select_reports_each_check_and_the_overlaps(self):
        self._run(
            _report(problems={"ngons": 3, "concave": 2}, selected=5, overlapping_faces=1),
            chk025=True,
        )
        message = self._message()
        self.assertIn("<hl>6</hl> total", message)
        self.assertIn("<hl>3</hl> N-Gons", message)
        self.assertIn("<hl>1</hl> Overlapping Faces", message)
        self.assertIn("#   total problem components: 6", self._console())

    def test_select_reports_matches_in_all_when_not_broken_down(self):
        self._run(_report(problems={}, selected=4))
        self.assertIn("<hl>4</hl> Problem components", self._message())

    def test_repair_reports_the_counts_and_passes(self):
        self._run(
            _report(vertices=(10, 8), faces=(6, 5), repairs=["merge vertices"]),
            cmb_mode="repair",
        )
        message = self._message()
        self.assertIn("<hl>2</hl> verts removed", message)
        self.assertIn("<hl>1</hl> faces removed", message)
        self.assertIn("#   operations: merge vertices", self._console())

    def test_a_failure_is_reported_not_raised(self):
        self.tk.Diagnostics.cleanup_meshes.side_effect = RuntimeError("boom")
        self.slots.tb000(_widget(**CLEANUP_DEFAULTS))
        self.assertIn("Mesh Cleanup failed", self._message())
        self.assertIn("boom", self._message())
        self.assertIn("# Mesh Cleanup — Select — FAILED", self._console())

    def test_the_options_one_host_serves_are_tagged(self):
        made = {}

        def add(_kind, **kwargs):
            child = mock.MagicMock()
            if "setObjectName" in kwargs:
                made[kwargs["setObjectName"]] = child
            return child

        widget = mock.MagicMock()
        widget.option_box.menu.add.side_effect = add
        self.slots.tb000_init(widget)
        tags = {
            name: child.setProperty.call_args.args
            for name, child in made.items()
            if child.setProperty.called
        }
        self.assertEqual(
            tags,
            {
                **{n: ("requires", "maya") for n in ("chk026", "chk012", "chk018", "chk016")},
                **{n: ("requires", "blender") for n in ("chk032", "chk033", "chk028", "chk029")},
            },
        )
        self.assertEqual(self.sb.apply_visibility_policy.call_count, 8)
        self.assertEqual(
            sorted(made),
            sorted(
                [
                    "cmb_scope", "cmb_mode", "chk026", "chk024", "s000", "chk032",
                    "chk033", "chk028", "chk029", "chk002", "chk017", "chk010",
                    "chk011", "chk003", "chk012", "chk018", "chk016", "chk015",
                    "s008", "chk013", "s006", "chk014", "s007", "chk025", "chk022",
                    "chk023",
                ]
            ),
        )


class TestDeleteOptimizeLock(_SlotsCase):
    def test_tb001_reaches_delete_history_in_scope(self):
        self.tk.NodeUtils.delete_history_in_scope.return_value = ["a"]
        self.slots.tb001(
            _widget(cmb_del_scope="visible", chk019=True, chk020=False, chk030=True)
        )
        self.tk.NodeUtils.delete_history_in_scope.assert_called_once_with(
            "visible", preserve_deformers=True, delete_unused=True, optimize_scene=True
        )
        self.assertEqual(self._message(), "<hl>Delete non-deformer history</hl>")

    def test_tb001_an_empty_scope_says_so(self):
        self.tk.NodeUtils.delete_history_in_scope.return_value = []
        self.slots.tb001(
            _widget(cmb_del_scope="selected", chk019=False, chk020=True, chk030=False)
        )
        self.assertIn("no objects in scope", self._message())

    def test_tb005_purges_unused_data(self):
        self.tk.CoreUtils.purge_unused_data.return_value = 7
        self.slots.tb005(_widget(chk_purge_recursive=True, chk_purge_linked=False))
        self.tk.CoreUtils.purge_unused_data.assert_called_once_with(
            recursive=True, linked=False
        )
        self.assertIn("<hl>7</hl>", self._message())

    def test_tb002_deletes_the_selection(self):
        self.slots.tb002(None)
        self.tk.EditUtils.delete_selected.assert_called_once_with()
        self.sb.message_box.assert_not_called()

    def test_tb002_a_refusal_reaches_the_user(self):
        self.tk.EditUtils.delete_selected.side_effect = RuntimeError("Edit Mode")
        self.slots.tb002(None)
        self.sb.message_box.assert_called_once_with("Edit Mode")

    def test_tb004_locks_and_counts(self):
        self.tk.NodeUtils.lock_nodes.return_value = ["a", "b", "c"]
        self.slots.tb004(_widget(cmb_lock="Lock"))
        self.tk.NodeUtils.lock_nodes.assert_called_once_with(None, lock=True)
        self.assertEqual(self._message(), "<hl>Locked</hl> 3 object(s).")

    def test_tb004_nothing_to_lock_or_unlock_says_so(self):
        self.tk.NodeUtils.lock_nodes.return_value = []
        self.slots.tb004(_widget(cmb_lock="Lock"))
        self.assertEqual(self._message(), "Select the object(s) to lock.")
        self.slots.tb004(_widget(cmb_lock="Unlock"))
        self.assertEqual(self._message(), "Nothing to unlock.")

    def test_tb004_init_names_both_states(self):
        widget = mock.MagicMock()
        combo = widget.option_box.menu.add.return_value
        combo.currentText.return_value = "Unlock"
        self.slots.tb004_init(widget)
        combo.addItems.assert_called_once_with(["Unlock", "Lock"])
        widget.setText.assert_called_once_with("Unlock")

    def test_the_launchers_open_their_panels(self):
        self.slots.b_channels()
        self.slots.b000()
        shown = [c.args[0] for c in self.sb.handlers.marking_menu.show.call_args_list]
        self.assertEqual(shown, ["channels", "cut_on_axis"])

    def test_the_header_lists_the_lists_and_launchers(self):
        widget = mock.MagicMock()
        self.slots.header_init(widget)
        names = [c.kwargs["setObjectName"] for c in widget.menu.add.call_args_list]
        self.assertEqual(names, ["list000", "list001", "b_channels", "b000"])
        self.assertTrue(widget.menu.hide_on_trigger)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestEditInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    ENV = "MAYA_TESTING_CLEANUP"

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.mel = maya_module("maya.mel")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")

    def tearDown(self):
        self.cmds.file(new=True, force=True)

    def _tb001(self, scope="all", unused=True, deformers=False, optimize=False):
        self.slots.tb001(
            _widget(
                cmb_del_scope=scope, chk019=unused, chk020=deformers, chk030=optimize
            )
        )

    # ---- Delete Unused Nodes: the empty-group sweep
    def test_delete_unused_preserves_shape_instances(self):
        """Regression: instanced transforms listed one DAG path, so a sibling
        instance read as an empty group and was deleted."""
        cube = self.cmds.polyCube(name="pCubeOrig")[0]
        inst = self.cmds.instance(cube, name="pCubeInst")[0]
        self._tb001()
        self.assertTrue(self.cmds.objExists(cube) and self.cmds.objExists(inst))

    def test_delete_unused_preserves_transform_instances(self):
        group = self.cmds.group(empty=True, name="grp_orig")
        cube = self.cmds.polyCube(name="pCubeInGroup")[0]
        self.cmds.parent(cube, group)
        inst = self.cmds.instance(group, name="grp_inst")[0]
        self._tb001()
        self.assertTrue(self.cmds.objExists(group) and self.cmds.objExists(inst))

    def test_delete_unused_removes_an_empty_group(self):
        self.cmds.polyCube(name="pKeep")
        empty = self.cmds.group(empty=True, name="grp_empty")
        self._tb001()
        self.assertFalse(self.cmds.objExists(empty))

    def test_delete_unused_removes_a_filed_empty_group(self):
        """Display-layer and set membership file a node; they don't depend on it."""
        self.cmds.polyCube(name="pKeepFiled")
        layered = self.cmds.group(empty=True, name="grp_empty_layered")
        layer = self.cmds.createDisplayLayer(name="tmpLayer", empty=True)
        self.cmds.editDisplayLayerMembers(layer, layered, noRecurse=True)
        in_set = self.cmds.group(empty=True, name="grp_empty_in_set")
        self.cmds.sets(in_set, name="tmpSet")
        self._tb001()
        self.assertFalse(self.cmds.objExists(layered) or self.cmds.objExists(in_set))

    def test_delete_unused_preserves_rig_nodes(self):
        """Regression: ``ls -dag -exactType transform`` matched joints, ikHandles
        and constraints, and a production scene lost all of them."""
        self.cmds.polyCube(name="pKeepRig")
        start = self.cmds.joint(name="jntStart", position=(0, 0, 0))
        self.cmds.joint(name="jntMid", position=(0, 5, 0))
        end = self.cmds.joint(name="jntEnd", position=(0, 10, 0))
        handle, effector = self.cmds.ikHandle(sj=start, ee=end, solver="ikRPsolver")[:2]
        driver = self.cmds.spaceLocator(name="locDriver")[0]
        driven = self.cmds.spaceLocator(name="locDriven")[0]
        constraint = self.cmds.parentConstraint(driver, driven, maintainOffset=False)[0]
        self._tb001()
        for node in (handle, effector, constraint, end):
            self.assertTrue(self.cmds.objExists(node), f"{node} was deleted")

    def test_delete_unused_preserves_a_connected_empty_transform(self):
        cube = self.cmds.polyCube(name="pKeepMtx")[0]
        source = self.cmds.group(empty=True, name="grp_matrix_source")
        mult = self.cmds.createNode("multMatrix", name="mtxConsumer")
        self.cmds.connectAttr(f"{source}.worldMatrix[0]", f"{mult}.matrixIn[0]")
        self.cmds.connectAttr(f"{mult}.matrixSum", f"{cube}.offsetParentMatrix")
        self._tb001()
        self.assertTrue(self.cmds.objExists(source))

    # ---- the scope
    def test_selected_scope_limits_deletion_to_the_selection(self):
        a = self.cmds.polyCube(name="histA")[0]
        self.cmds.polyCube(name="histB")
        self.cmds.select(a)
        self._tb001("selected", unused=False, deformers=True)
        self.assertEqual(len(self.cmds.ls(type="polyCube")), 1)

    def test_all_scope_deletes_history_everywhere(self):
        self.cmds.polyCube(name="histA")
        self.cmds.polyCube(name="histB")
        self.cmds.select(clear=True)
        self._tb001("all", unused=False, deformers=True)
        self.assertEqual(self.cmds.ls(type="polyCube"), [])

    def test_visible_scope_skips_hidden_meshes(self):
        self.cmds.polyCube(name="visCube")
        hidden = self.cmds.polyCube(name="hidCube")[0]
        self.cmds.setAttr(f"{hidden}.visibility", 0)
        self.cmds.select(clear=True)
        self._tb001("visible", unused=False, deformers=True)
        self.assertEqual(len(self.cmds.ls(type="polyCube")), 1)

    # ---- Optimize Scene's dialog suppression leaves the environment as found
    def test_optimize_restores_a_preexisting_env_value(self):
        saved = self.mel.eval(f'getenv "{self.ENV}"')
        self.addCleanup(self.mel.eval, f'putenv "{self.ENV}" "{saved}";')
        self.mel.eval(f'putenv "{self.ENV}" "preexisting";')
        self._tb001(unused=False, optimize=True)
        self.assertEqual(self.mel.eval(f'getenv "{self.ENV}"'), "preexisting")

    def test_optimize_leaks_no_env_value(self):
        saved = self.mel.eval(f'getenv "{self.ENV}"')
        self.addCleanup(self.mel.eval, f'putenv "{self.ENV}" "{saved}";')
        self.mel.eval(f'putenv "{self.ENV}" "";')
        self._tb001(unused=False, optimize=True)
        self.assertEqual(self.mel.eval(f'getenv "{self.ENV}"'), "")

    # ---- Lock / Unlock, Mesh Cleanup
    def test_lock_then_unlock_the_selection(self):
        cube = self.cmds.polyCube(name="ln_cube")[0]
        self.cmds.select(cube)
        self.slots.tb004(_widget(cmb_lock="Lock"))
        self.assertTrue(self.cmds.lockNode(cube, query=True, lock=True)[0])
        self.cmds.select(cube)
        self.slots.tb004(_widget(cmb_lock="Unlock"))
        self.assertFalse(self.cmds.lockNode(cube, query=True, lock=True)[0])

    def test_mesh_cleanup_selects_an_ngon(self):
        cube = self.cmds.polyCube(name="cleanNgon")[0]
        self.cmds.polyDelEdge(f"{cube}.e[0]", cleanVertices=False)  # a six-sided face
        self.cmds.select(cube)
        self.slots.tb000(_widget(**dict(CLEANUP_DEFAULTS, chk026=False)))
        self.assertIn("Problem components", self._message())
        self.assertTrue(self.cmds.ls(selection=True, flatten=True))


if __name__ == "__main__":
    unittest.main()
