#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.edit."""

import unittest

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
mel = maya_module("maya.mel")
edit_module = maya_module("tentacle.slots.maya.edit")


class _FakeCheck:
    def __init__(self, value):
        self._v = value

    def isChecked(self):
        return self._v


class _FakeCombo:
    """Stand-in for the option_box QComboBox: currentText()."""

    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text


class _FakeDataCombo:
    """Stand-in for a value-carrier QComboBox read via currentData() (e.g. cmb_del_scope)."""

    def __init__(self, data):
        self._data = data

    def currentData(self):
        return self._data


class _FakeMenu:
    def __init__(self, **checks):
        for name, val in checks.items():
            setattr(self, name, _FakeCheck(val))


class _FakeOptionBox:
    def __init__(self, **checks):
        self.menu = _FakeMenu(**checks)


class _FakeWidget:
    def __init__(self, scope="all", **checks):
        self.option_box = _FakeOptionBox(**checks)
        # tb001 reads the Delete-History scope from cmb_del_scope (default "all" mirrors the
        # old dead-checkbox behaviour of acting on every mesh when nothing is selected).
        self.option_box.menu.cmb_del_scope = _FakeDataCombo(scope)


class _FakeSb:
    def message_box(self, *_args, **_kwargs):
        pass


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestDeleteHistoryUnusedNodes(unittest.TestCase):
    """Edit.tb001 with `Delete Unused Nodes` must not destroy instance siblings.

    Pre-fix bug: the empty-group sweep used cmds.ls without allPaths=True, so
    instanced shape/transform nodes only listed one of their DAG paths. The
    sibling instance transforms looked like empty groups and were deleted.
    """

    def setUp(self):
        cmds.file(new=True, force=True)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _run_tb001(self, *, unused_nodes=True, deformers=False, optimize=False):
        instance = edit_module.Edit.__new__(edit_module.Edit)
        instance.sb = _FakeSb()
        widget = _FakeWidget(
            chk019=unused_nodes,
            chk020=deformers,
            chk030=optimize,
        )
        instance.tb001(widget)

    def test_delete_unused_nodes_preserves_shape_instances(self):
        cube_xform, _ = cmds.polyCube(name="pCubeOrig")
        instance_xform = cmds.instance(cube_xform, name="pCubeInst")[0]

        self._run_tb001()

        self.assertTrue(
            cmds.objExists(cube_xform),
            f"Original cube transform '{cube_xform}' was deleted",
        )
        self.assertTrue(
            cmds.objExists(instance_xform),
            f"Instanced cube transform '{instance_xform}' was deleted",
        )

    def test_delete_unused_nodes_preserves_transform_instances(self):
        group_xform = cmds.group(empty=True, name="grp_orig")
        cube_xform, _ = cmds.polyCube(name="pCubeInGroup")
        cmds.parent(cube_xform, group_xform)
        instance_xform = cmds.instance(group_xform, name="grp_inst")[0]

        self._run_tb001()

        self.assertTrue(
            cmds.objExists(group_xform),
            f"Original group '{group_xform}' was deleted",
        )
        self.assertTrue(
            cmds.objExists(instance_xform),
            f"Instanced group '{instance_xform}' was deleted",
        )

    def test_delete_unused_nodes_still_removes_truly_empty_group(self):
        cmds.polyCube(name="pKeep")
        empty_grp = cmds.group(empty=True, name="grp_empty")

        self._run_tb001()

        self.assertFalse(
            cmds.objExists(empty_grp),
            f"Empty group '{empty_grp}' should have been removed",
        )

    def test_delete_unused_nodes_still_removes_filed_empty_group(self):
        """Display layer / set membership is not a dependency.

        The disposability guard asks whether anything depends on an empty
        transform. Membership of a display layer or an objectSet answers
        `listConnections`, but files the node rather than depending on it —
        counting it would retire the cleanup for any scene whose hierarchy is
        organised into layers, which is most of them.
        """
        cmds.polyCube(name="pKeepFiled")
        layered = cmds.group(empty=True, name="grp_empty_layered")
        layer = cmds.createDisplayLayer(name="tmpLayer", empty=True)
        cmds.editDisplayLayerMembers(layer, layered, noRecurse=True)
        in_set = cmds.group(empty=True, name="grp_empty_in_set")
        cmds.sets(in_set, name="tmpSet")

        self._run_tb001()

        for node, label in ((layered, "display layer"), (in_set, "objectSet")):
            self.assertFalse(
                cmds.objExists(node),
                f"Empty group '{node}' was spared because it is in a {label}; "
                "membership files a node, it does not depend on it",
            )

    def test_delete_unused_nodes_preserves_rig_nodes(self):
        """The sweep must not treat rig nodes as empty groups.

        Pre-fix bug: `ls -dag -exactType transform` is NOT exact — the DAG walk
        applies the type test with inheritance, so it also returned joints,
        ikHandles, ikEffectors and constraints. Each is a childless, shape-less
        DAG node, so every one matched the "empty group" test and was deleted.
        Measured on the VDATS_ASSEMBLY production scene: deleting history on 6
        selected meshes wiped all 7 ikHandles and all 224 constraints scene-wide.
        """
        cmds.polyCube(name="pKeepRig")
        start = cmds.joint(name="jntStart", position=(0, 0, 0))
        cmds.joint(name="jntMid", position=(0, 5, 0))
        end = cmds.joint(name="jntEnd", position=(0, 10, 0))
        handle, effector = cmds.ikHandle(sj=start, ee=end, solver="ikRPsolver")[:2]
        driver = cmds.spaceLocator(name="locDriver")[0]
        driven = cmds.spaceLocator(name="locDriven")[0]
        constraint = cmds.parentConstraint(driver, driven, maintainOffset=False)[0]

        self._run_tb001()

        for node, label in (
            (handle, "ikHandle"),
            (effector, "ikEffector"),
            (constraint, "parentConstraint"),
            (end, "leaf joint"),
        ):
            self.assertTrue(
                cmds.objExists(node),
                f"{label} '{node}' was deleted by the empty-group sweep",
            )

    def test_delete_unused_nodes_preserves_connected_empty_transform(self):
        """An empty transform that something depends on is not junk.

        Matrix-driven rigs use shapeless, childless transforms as matrix
        sources and space-switch pivots. They are structurally identical to a
        leftover empty group, so the sweep tells them apart by connections.
        """
        cube = cmds.polyCube(name="pKeepMtx")[0]
        source = cmds.group(empty=True, name="grp_matrix_source")
        mult = cmds.createNode("multMatrix", name="mtxConsumer")
        cmds.connectAttr(f"{source}.worldMatrix[0]", f"{mult}.matrixIn[0]")
        # The multMatrix has to drive something: MLdeleteUnused runs first and
        # would (rightly) remove a utility node that feeds nothing, which would
        # orphan the source transform for real rather than exercise the guard.
        cmds.connectAttr(f"{mult}.matrixSum", f"{cube}.offsetParentMatrix")

        self._run_tb001()

        self.assertTrue(
            cmds.objExists(source),
            f"Connected empty transform '{source}' was deleted; a matrix-driven "
            "rig is mostly empty transforms and the sweep must leave them alone",
        )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestDeleteHistoryScope(unittest.TestCase):
    """tb001's scope combobox (cmb_del_scope) must actually scope history deletion.

    The old chk031 'For All Objects' checkbox was declared in tb001_init but tb001 never read
    it — scope was silently auto-detected (selection-if-any-else-all). The combobox replaces it
    with a real, honored Selected / Visible / All Geometry choice.
    """

    def setUp(self):
        cmds.file(new=True, force=True)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _run(self, scope):
        instance = edit_module.Edit.__new__(edit_module.Edit)
        instance.sb = _FakeSb()
        # deformers=True -> full-history delete path; unused/optimize off to isolate scope.
        widget = _FakeWidget(scope=scope, chk019=False, chk020=True, chk030=False)
        instance.tb001(widget)

    def test_selected_scope_limits_deletion_to_selection(self):
        # Each polyCube leaves a `polyCube` construction-history node.
        a = cmds.polyCube(name="histA")[0]
        cmds.polyCube(name="histB")
        self.assertEqual(len(cmds.ls(type="polyCube")), 2)
        cmds.select(a)
        self._run("selected")
        self.assertEqual(
            len(cmds.ls(type="polyCube")),
            1,
            "Selected scope must delete history only on the selection (one cube's remains)",
        )

    def test_all_scope_deletes_history_everywhere(self):
        cmds.polyCube(name="histA")
        cmds.polyCube(name="histB")
        self.assertEqual(len(cmds.ls(type="polyCube")), 2)
        cmds.select(clear=True)
        self._run("all")
        self.assertEqual(
            cmds.ls(type="polyCube"),
            [],
            "All Geometry scope must delete history on every mesh",
        )

    def test_visible_scope_skips_hidden_meshes(self):
        cmds.polyCube(name="visCube")
        hidden = cmds.polyCube(name="hidCube")[0]
        cmds.setAttr(f"{hidden}.visibility", 0)
        self.assertEqual(len(cmds.ls(type="polyCube")), 2)
        cmds.select(clear=True)
        self._run("visible")
        self.assertEqual(
            len(cmds.ls(type="polyCube")),
            1,
            "Visible scope must skip hidden meshes (the hidden cube's history remains)",
        )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb004NodeLocking(unittest.TestCase):
    """tb004 reads the Lock/Unlock combobox (cmb_lock, replacing the old
    chk027 checkbox) and locks or unlocks the selected nodes."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = edit_module.Edit.__new__(edit_module.Edit)
        self.instance.sb = _FakeSb()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _widget(self, action):
        widget = _FakeWidget()
        widget.option_box.menu.cmb_lock = _FakeCombo(action)
        return widget

    def test_lock_nodes_locks_the_selection(self):
        cube = cmds.polyCube(name="ln_cube")[0]
        cmds.select(cube)
        self.instance.tb004(self._widget("Lock Nodes"))
        self.assertTrue(cmds.lockNode(cube, query=True, lock=True)[0])

    def test_unlock_nodes_unlocks_the_selection(self):
        cube = cmds.polyCube(name="ln_cube")[0]
        cmds.lockNode(cube, lock=True)
        cmds.select(cube)
        self.instance.tb004(self._widget("Unlock Nodes"))
        self.assertFalse(cmds.lockNode(cube, query=True, lock=True)[0])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestOptimizeScenePopupSuppression(unittest.TestCase):
    """tb001's Optimize Scene step must run silently (no confirmDialog) and must NOT leak the
    MAYA_TESTING_CLEANUP env var it toggles.

    Maya's `OptimizeScene` == `cleanUpScene 1` == performCleanUpScene(), which pops a
    non-undoable-op OK/Cancel confirmDialog unless the MAYA_TESTING_CLEANUP env var is set
    (Autodesk's own built-in suppression hook, verified in scripts/startup/cleanUpScene.mel).
    tb001 sets it around the call and restores the prior value. The dialog-suppression itself is
    a GUI concern (batch mode never shows it); what this regression guards is the code's env
    scoping — that it sets the flag for the call and leaves the environment exactly as it found
    it, never leaking a global testing flag into the rest of the session.
    """

    ENV = "MAYA_TESTING_CLEANUP"

    def setUp(self):
        cmds.file(new=True, force=True)
        self._saved = mel.eval(f'getenv "{self.ENV}"')

    def tearDown(self):
        mel.eval(f'putenv "{self.ENV}" "{self._saved}";')
        cmds.file(new=True, force=True)

    def _run_optimize(self):
        instance = edit_module.Edit.__new__(edit_module.Edit)
        instance.sb = _FakeSb()
        widget = _FakeWidget(chk019=False, chk020=False, chk030=True)
        instance.tb001(widget)  # optimize=True, others off

    def test_optimize_runs_without_raising(self):
        try:
            self._run_optimize()
        except Exception as exc:  # noqa: BLE001 - a raise here IS the failure
            self.fail(f"tb001 optimize step raised: {exc!r}")

    def test_preexisting_env_value_is_restored(self):
        mel.eval(f'putenv "{self.ENV}" "preexisting";')
        self._run_optimize()
        self.assertEqual(
            mel.eval(f'getenv "{self.ENV}"'),
            "preexisting",
            "tb001 must restore a pre-existing MAYA_TESTING_CLEANUP value",
        )

    def test_env_not_leaked_when_previously_unset(self):
        mel.eval(f'putenv "{self.ENV}" "";')  # emulate unset (getenv -> "")
        self._run_optimize()
        self.assertEqual(
            mel.eval(f'getenv "{self.ENV}"'),
            "",
            "tb001 must not leave MAYA_TESTING_CLEANUP set after the call",
        )


if __name__ == "__main__":
    # Direct `mayapy test_edit.py` runs need an initialized standalone session
    # — without it maya.cmds imports but carries no command attrs, erroring
    # every test with AttributeError instead of exercising anything.
    if _MAYA_AVAILABLE and not hasattr(cmds, "file"):
        import maya.standalone

        maya.standalone.initialize(name="python")
    unittest.main()
