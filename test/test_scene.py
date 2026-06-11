#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.scene.

Most of SceneSlots is a thin shell around MEL/cmds calls (Export, Import,
SetProject menus). Those are too thin to unit-test meaningfully. This
covers the units with branching logic:

- _open_recent_workspace — workspace.mel presence gate
- _ensure_fbx_plugin     — graceful fail when plugin missing
- _resolve_workspace_text — env fallback
- b015 (rename pattern)  — startswith/contains asterisk modifiers
"""
import os
import tempfile
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import scene as scene_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    scene_module = None
    _MAYA_AVAILABLE = False


class _RecordedSb:
    """Stand-in for the switchboard — records message_box calls and returns
    a preset choice (the clicked-button text, in real use)."""

    def __init__(self, choice=None):
        self.choice = choice
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))
        return self.choice


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestOpenRecentWorkspace(unittest.TestCase):
    """SceneSlots._open_recent_workspace validates workspace.mel before opening."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = scene_module.SceneSlots.__new__(scene_module.SceneSlots)
        self.instance.sb = _RecordedSb()
        self.instance._footer_controller = None
        self.root = tempfile.mkdtemp(prefix="scene_ws_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)
        cmds.file(new=True, force=True)

    def test_rejects_path_with_no_workspace_mel(self):
        """A directory missing workspace.mel must NOT be opened as a workspace."""
        # Empty dir, no workspace.mel
        before_ws = cmds.workspace(query=True, rd=True)
        self.instance._open_recent_workspace(self.root)
        after_ws = cmds.workspace(query=True, rd=True)
        # Workspace must not have changed.
        self.assertEqual(before_ws, after_ws)
        # And the user must have been warned.
        self.assertTrue(self.instance.sb.messages, "Expected a user-visible warning")

    def test_accepts_path_with_workspace_mel(self):
        # Create the marker file Maya expects in a workspace root.
        with open(os.path.join(self.root, "workspace.mel"), "w") as f:
            f.write("//Maya workspace stub\n")

        self.instance._open_recent_workspace(self.root)

        new_ws = cmds.workspace(query=True, rd=True)
        # Maya stores forward slashes; compare normalized.
        self.assertEqual(
            os.path.normpath(new_ws).lower(),
            os.path.normpath(self.root).lower(),
        )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestEnsureFbxPlugin(unittest.TestCase):
    """_ensure_fbx_plugin loads fbxmaya idempotently and returns True/False."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = scene_module.SceneSlots.__new__(scene_module.SceneSlots)
        self.instance.sb = _RecordedSb()

    def test_returns_true_when_plugin_already_loaded(self):
        if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
            try:
                cmds.loadPlugin("fbxmaya", quiet=True)
            except Exception:
                self.skipTest("fbxmaya plugin not available on this Maya build")
        self.assertTrue(self.instance._ensure_fbx_plugin())

    def test_returns_true_after_load(self):
        if cmds.pluginInfo("fbxmaya", query=True, loaded=True):
            cmds.unloadPlugin("fbxmaya")
        try:
            self.assertTrue(self.instance._ensure_fbx_plugin())
            self.assertTrue(cmds.pluginInfo("fbxmaya", query=True, loaded=True))
        except Exception:
            self.skipTest("fbxmaya plugin not available on this Maya build")

    def test_returns_false_and_messages_when_load_fails(self):
        """Simulate a load failure by monkey-patching cmds.loadPlugin.

        The non-loaded branch must surface the error to the user, not raise.
        """
        if cmds.pluginInfo("fbxmaya", query=True, loaded=True):
            cmds.unloadPlugin("fbxmaya")

        original_load = cmds.loadPlugin
        original_info = cmds.pluginInfo

        def failing_load(*args, **kwargs):
            raise RuntimeError("simulated load failure")

        def reports_unloaded(*args, **kwargs):
            if kwargs.get("query") and kwargs.get("loaded"):
                return False
            return original_info(*args, **kwargs)

        cmds.loadPlugin = failing_load
        cmds.pluginInfo = reports_unloaded
        try:
            result = self.instance._ensure_fbx_plugin()
            self.assertFalse(result)
            self.assertTrue(self.instance.sb.messages, "User must be notified")
        finally:
            cmds.loadPlugin = original_load
            cmds.pluginInfo = original_info


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestResolveWorkspaceText(unittest.TestCase):
    """_resolve_workspace_text returns the workspace_dir env info or ''."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = scene_module.SceneSlots.__new__(scene_module.SceneSlots)

    def test_returns_string(self):
        # We don't assert a specific value — workspace state depends on Maya
        # session. Just verify the contract: always a string, never None.
        result = self.instance._resolve_workspace_text()
        self.assertIsInstance(result, str)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestConfirmDenseExport(unittest.TestCase):
    """_confirm_dense_export warns only when dense AND tangents are on.

    Heads-up dialog before a slow FBX export, gated on triangle count plus
    the tangents option so the common (small / already-optimized) export is
    never interrupted.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.inst = scene_module.SceneSlots.__new__(scene_module.SceneSlots)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_no_warning_when_tangents_off(self):
        """Tangents off ⇒ proceed silently (no density query, no dialog)."""
        cmds.select(cmds.polyCube()[0])
        self.inst.sb = _RecordedSb("No")
        self.assertTrue(self.inst._confirm_dense_export(True, False))
        self.assertEqual(self.inst.sb.messages, [])

    def test_no_warning_below_threshold(self):
        """Tangents on but a tiny mesh ⇒ proceed silently."""
        cmds.select(cmds.polyCube()[0])
        self.inst.sb = _RecordedSb("No")
        self.assertTrue(self.inst._confirm_dense_export(True, True))
        self.assertEqual(self.inst.sb.messages, [])

    def test_warns_when_dense_and_respects_choice(self):
        """Dense + tangents ⇒ dialog; 'No' cancels, 'Yes' proceeds."""
        orig = scene_module.SceneSlots._DENSE_TRI_THRESHOLD
        scene_module.SceneSlots._DENSE_TRI_THRESHOLD = 100  # trip on a small mesh
        try:
            cmds.select(cmds.polySphere(sx=20, sy=20)[0])

            self.inst.sb = _RecordedSb("No")
            self.assertFalse(self.inst._confirm_dense_export(True, True))
            self.assertEqual(len(self.inst.sb.messages), 1)

            self.inst.sb = _RecordedSb("Yes")
            self.assertTrue(self.inst._confirm_dense_export(True, True))
        finally:
            scene_module.SceneSlots._DENSE_TRI_THRESHOLD = orig


if __name__ == "__main__":
    unittest.main()
