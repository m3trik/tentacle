#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.edit."""

import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import edit as edit_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    edit_module = None
    _MAYA_AVAILABLE = False


class _FakeCheck:
    def __init__(self, value):
        self._v = value

    def isChecked(self):
        return self._v


class _FakeMenu:
    def __init__(self, **checks):
        for name, val in checks.items():
            setattr(self, name, _FakeCheck(val))


class _FakeOptionBox:
    def __init__(self, **checks):
        self.menu = _FakeMenu(**checks)


class _FakeWidget:
    def __init__(self, **checks):
        self.option_box = _FakeOptionBox(**checks)


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


if __name__ == "__main__":
    unittest.main()
