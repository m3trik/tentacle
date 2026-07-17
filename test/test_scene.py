#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.scene.

Most of SceneSlots is a thin shell around MEL/cmds calls (Export, Import,
SetProject menus). Those are too thin to unit-test meaningfully. This
covers the units with branching logic:

- _ensure_fbx_plugin      — graceful fail when plugin missing
- _resolve_workspace_text — env fallback
- _confirm_dense_export   — dense-mesh tangent-export confirmation gate
"""
import unittest
from types import SimpleNamespace as NS

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


# NOTE: the workspace-setting controls (and their workspace.mel gate) moved to
# the main lower submenu's Workspace list — see test_main_workspace.py.


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


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestList000CategoryRowGuard(unittest.TestCase):
    """list000 must ignore items with no bound file path.

    Clicking the "Recent Files" category row emits on_item_interacted with a
    data-less label; the handler used to pass that None straight into
    ``cmds.file(None, open=True, force=True)`` (the Blender twin already
    guarded). Pin: no data ⇒ no file call; data ⇒ opened.
    """

    class _Item:
        def __init__(self, data):
            self._data = data

        def item_data(self):
            return self._data

    def setUp(self):
        self.inst = scene_module.SceneSlots.__new__(scene_module.SceneSlots)
        self.calls = []
        self._orig_file = cmds.file
        cmds.file = lambda *a, **kw: self.calls.append((a, kw))

    def tearDown(self):
        cmds.file = self._orig_file

    def test_category_row_is_a_noop(self):
        self.inst.list000(self._Item(None))
        self.assertEqual(self.calls, [])

    def test_file_item_opens(self):
        self.inst.list000(self._Item("scenes/foo.ma"))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], ("scenes/foo.ma",))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestSceneExporterOnExportList(unittest.TestCase):
    """Scene Exporter is reachable from the Export list.

    It used to be a header-menu button (b002) with its own slot method; both
    are gone, so ``_EXPORTERS`` is now the only route to the panel. Pin the
    entry and its dispatch — a typo'd key would strand the tool with no
    compile-time error, since list002 looks the label up by text.
    """

    class _Item:
        def __init__(self, text):
            self._text = text

        def item_text(self):
            return self._text

    def setUp(self):
        self.inst = scene_module.SceneSlots.__new__(scene_module.SceneSlots)
        self.shown = []
        self.inst.sb = NS(handlers=NS(marking_menu=NS(show=self.shown.append)))

    def test_entry_is_registered(self):
        cls = scene_module.SceneSlots
        self.assertIn(cls._SCENE_EXPORTER, cls._EXPORTERS)

    def test_entry_launches_the_panel(self):
        self.inst.list002(self._Item(scene_module.SceneSlots._SCENE_EXPORTER))
        self.assertEqual(self.shown, ["scene_exporter"])

    def test_header_no_longer_carries_the_button(self):
        # b002's removal is what makes the list the only route; a re-added
        # method would mean the button crept back onto the header menu.
        self.assertFalse(hasattr(scene_module.SceneSlots, "b002"))

    def test_unknown_label_is_a_noop(self):
        self.inst.list002(self._Item("Export"))  # the category row
        self.assertEqual(self.shown, [])


if __name__ == "__main__":
    unittest.main()
