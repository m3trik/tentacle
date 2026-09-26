#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.scene.

Most of SceneSlots is a thin shell around MEL/cmds calls (Export, Import,
SetProject menus). Those are too thin to unit-test meaningfully. This
covers the units with branching logic:

- _ensure_fbx_plugin      — graceful fail when plugin missing
- _resolve_workspace_text — env fallback
- _confirm_dense_export   — dense-mesh tangent-export confirmation gate
- tb001 Get Scene Info    — the body both forks share (``SceneMixin``), driven
  Maya-free with a stand-in engine, and the Maya fork against mayatk's
"""

import ast
import contextlib
import functools
import os
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # before any widget is built

from _host import (  # noqa: E402
    MAYA_AVAILABLE as _MAYA_AVAILABLE,
    maya_module,
    qt_widgets_available,
)
from tentacle.slots._scene import SceneMixin  # noqa: E402

cmds = maya_module("maya.cmds")
scene_module = maya_module("tentacle.slots.maya.scene")

SLOTS_ROOT = Path(__file__).resolve().parent.parent / "tentacle" / "slots"


class _Combo:
    def __init__(self, data):
        self.data = data

    def currentData(self):
        return self.data


class _Check:
    def __init__(self, on):
        self.on = on

    def isChecked(self):
        return self.on


def _scene_info_widget(keys, scope="all", unchecked=()):
    """A tb001 widget whose option box answers like the one tb001_init builds."""
    menu = NS(cmb_scope1=_Combo(scope), cmb_profile=_Combo(True))
    for key in keys:
        setattr(menu, f"chk_section_{key}", _Check(key not in unchecked))
    return NS(option_box=NS(menu=menu))


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

    def test_usd_entry_dispatches_to_the_shared_usd_export(self):
        calls = []
        self.inst._export_usd = lambda: calls.append("usd")
        self.inst.list002(self._Item("Export USD"))
        self.assertEqual(calls, ["usd"])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestGltfImportEntry(unittest.TestCase):
    """ "Import glTF" on the Import list, and the pull path it shares with .blend.

    Maya ships no glTF importer, so this entry is the ONLY route a .glb has into a
    Maya scene -- and it reaches it through the same ``mtk.BlenderSceneImport`` bridge
    the .blend entry uses. Both therefore run one body (``_pull_scene``): the carrier
    choice, the wait cursor and the failure report cannot be allowed to drift between
    two hand-copied methods. list001 looks the label up by text, so a typo'd key would
    strand the entry with no compile-time error.
    """

    class _Item:
        def __init__(self, text):
            self._text = text

        def item_text(self):
            return self._text

    def setUp(self):
        self.inst = scene_module.SceneSlots.__new__(scene_module.SceneSlots)
        self.calls = []
        self.inst._pull_scene = lambda *a, **kw: self.calls.append((a, kw))

    def test_entry_is_registered(self):
        self.assertIn("Import glTF", scene_module.SceneSlots._IMPORTERS)

    def test_entry_dispatches_to_the_gltf_pull(self):
        self.inst.list001(self._Item("Import glTF"))
        self.assertEqual(len(self.calls), 1)
        globs = self.calls[0][0][0]
        self.assertEqual(sorted(globs), ["*.glb", "*.gltf"])

    def test_blend_entry_shares_the_same_pull(self):
        self.inst.list001(self._Item("Import Blender Scene"))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0][0], ["*.blend"])

    def test_usd_entry_shares_the_same_pull(self):
        self.inst.list001(self._Item("Import USD"))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(
            self.calls[0][0][0],
            [f"*{ext}" for ext in scene_module.ptk.USD_EXTENSIONS],
        )

    def test_unknown_label_is_a_noop(self):
        self.inst.list001(self._Item("Import"))  # the category row
        self.assertEqual(self.calls, [])

    def test_carrier_choice_is_read_once_in_the_shared_body(self):
        # The Transfer-via combo must reach BOTH entries. If a future edit
        # re-inlines one of them, this catches the copy that forgot the carrier.
        import inspect

        src = inspect.getsource(scene_module.SceneSlots._pull_scene)
        self.assertIn("_transfer_carrier()", src)
        for name in ("_import_gltf", "_import_blender_scene", "_import_usd"):
            body = inspect.getsource(getattr(scene_module.SceneSlots, name))
            self.assertIn("_pull_scene", body)
            self.assertNotIn("import_scene(", body)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestGetSceneInfo(unittest.TestCase):
    """tb001 hands the analyzer its scope and the viewer its link handler.

    Regression: Entire Scene passed ``cmds.ls(type="mesh")`` -- one name per
    SHAPE -- so every instance past the first went uncounted, and the report's
    object names were inert text.
    """

    class _Sb(_RecordedSb):
        def __init__(self):
            super().__init__()
            self.views = []
            self.logger = mock.Mock()

        def progress(self, **kwargs):
            return contextlib.nullcontext(lambda *a, **k: None)

        def progress_adapter(self, update):
            return None

        def text_view_dialog(self, text, *buttons, **kwargs):
            self.views.append((text, buttons, kwargs))

    @staticmethod
    def _widget(scope="all", unchecked=()):
        return _scene_info_widget(
            scene_module.mtk.SceneInfoSection.ALL, scope, unchecked
        )

    def setUp(self):
        cmds.file(new=True, force=True)
        self.inst = scene_module.SceneSlots.__new__(scene_module.SceneSlots)
        self.inst.sb = self._Sb()
        cube = cmds.polyCube(name="info_cube")[0]
        cmds.instance(cube)
        cmds.select(clear=True)

    def test_entire_scene_counts_instances_and_links_names(self):
        self.inst.tb001(self._widget("all"))
        ((html, _buttons, kwargs),) = self.inst.sb.views
        self.assertIn("2 instances of 1 unique shape", html)
        self.assertIn("action://select", html)
        # A name deleted since the report ran: the click says so, not nothing.
        url = NS(
            scheme=lambda: "action", host=lambda: "select", query=lambda: "node=gone"
        )
        self.assertFalse(kwargs["link_handler"](url))
        self.inst.sb.logger.warning.assert_called_once_with("Object not found: gone")

    def test_selection_scope_needs_a_selection(self):
        self.inst.tb001(self._widget("selection"))
        self.assertEqual(self.inst.sb.views, [])
        self.assertIn("Nothing selected", self.inst.sb.messages[0][0][0])

    def test_unticked_sections_are_not_rendered(self):
        self.inst.tb001(self._widget("all", unchecked=("overview", "assumptions")))
        html = self.inst.sb.views[0][0]
        self.assertNotIn("Scene Overview", html)
        self.assertNotIn("Notes &amp; Assumptions", html)
        self.assertIn("Executive Summary", html)

    def test_no_sections_is_a_message_not_a_report(self):
        keys = tuple(scene_module.mtk.SceneInfoSection.ALL)
        self.inst.tb001(self._widget("all", unchecked=keys))
        self.assertEqual(self.inst.sb.views, [])
        self.assertIn("No sections selected", self.inst.sb.messages[0][0][0])

    def test_every_section_has_a_tooltip(self):
        self.assertEqual(
            set(scene_module.SceneSlots._TB001_SECTION_TIPS),
            set(scene_module.mtk.SceneInfoSection.ALL),
        )

    def test_a_selected_object_set_is_a_selection(self):
        # The audit resolves a set to its members; a set has no transform, so
        # the shared guard must not read the Maya fork's _selected_objects.
        cmds.select(cmds.sets("info_cube", name="info_set"), noExpand=True)
        self.inst.tb001(self._widget("selection"))
        self.assertEqual(self.inst.sb.messages, [])
        self.assertEqual(len(self.inst.sb.views), 1)


class _Sections:
    """Stand-in for an engine's ``SceneInfoSection``: one label carries an "&"."""

    ALL = ("summary", "assumptions")
    LABELS = {"summary": "Executive Summary", "assumptions": "Notes & Assumptions"}


class _UiUtils:
    @staticmethod
    def dispatch_log_link(url, logger=None):
        return True


class _SceneInfoHost(SceneMixin):
    """The shared Get Scene Info body over a stand-in engine (no DCC needed)."""

    def __init__(self, selected=True):
        self.calls, self.views, self.messages, self.selected = [], [], [], selected
        self.adapter = object()  # what the switchboard hands the analyzer
        self.sb = NS(
            message_box=lambda text, *a, **k: self.messages.append(text),
            text_view_dialog=lambda text, *a, **k: self.views.append((text, k)),
            progress=lambda **k: contextlib.nullcontext(None),
            progress_adapter=lambda update: self.adapter,
            logger=mock.Mock(),
        )

    def _scene_analyzer(self):
        host = self

        class _Analyzer:
            @staticmethod
            def format_audit_html(**kwargs):
                host.calls.append(kwargs)
                return {"_header": "<h1>Scene Info</h1>", "summary": "<p>ok</p>"}

        return _Analyzer

    def _scene_info_sections(self):
        return _Sections

    def _ui_utils(self):
        return _UiUtils

    def _selected_objects(self):
        return ["obj"] if self.selected else []


class TestGetSceneInfoShared(unittest.TestCase):
    """tb001 / tb001_init live once, on ``SceneMixin``; both forks supply hooks.

    Regression: the Maya and Blender forks carried near-identical copies that
    differed only by engine namespace -- and had drifted (the Blender copy's
    Generic tooltip claimed a 100k budget; the engine's is 20k).
    """

    FORKS = (SLOTS_ROOT / "maya" / "scene.py", SLOTS_ROOT / "blender" / "scene.py")
    HOOKS = ("_scene_analyzer", "_scene_info_sections", "_ui_utils")
    SHARED = ("tb001", "tb001_init", "_TB001_SCOPES", "_TB001_PROFILES")
    #: The sections whose content is each DCC's own -- the rows a fork words.
    FORK_TIPS = {"overview", "fix_first", "pipeline"}

    @staticmethod
    def _class(path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name == "SceneSlots"
        )

    def test_forks_supply_the_hooks_and_carry_no_copy(self):
        for path in self.FORKS:
            cls = self._class(path)
            defs = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
            assigned = {
                t.id
                for n in cls.body
                if isinstance(n, ast.Assign)
                for t in n.targets
                if isinstance(t, ast.Name)
            }
            with self.subTest(fork=path.parent.name):
                self.assertTrue(set(self.HOOKS) <= defs, defs)
                self.assertFalse((defs | assigned) & set(self.SHARED))

    def test_forks_extend_the_shared_tips_with_their_own_rows(self):
        shared = set(SceneMixin._TB001_SECTION_TIPS)
        for path in self.FORKS:
            node = next(
                n.value
                for n in self._class(path).body
                if isinstance(n, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "_TB001_SECTION_TIPS"
                    for t in n.targets
                )
            )
            spread = [v for k, v in zip(node.keys, node.values) if k is None]
            own = {k.value for k in node.keys if k is not None}
            with self.subTest(fork=path.parent.name):
                self.assertEqual(
                    [ast.unparse(v) for v in spread],
                    ["SceneMixin._TB001_SECTION_TIPS"],
                )
                self.assertEqual(own, self.FORK_TIPS)
                self.assertFalse(own & shared)

    @unittest.skipUnless(qt_widgets_available(), "QWidget construction aborts here")
    def test_an_ampersand_label_stays_literal_and_binds_no_mnemonic(self):
        from qtpy import QtGui, QtWidgets
        from uitk.widgets.label import Label
        from uitk.widgets.menu import Menu

        QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        host = _SceneInfoHost()
        host.sb.registered_widgets = NS(Label=Label)
        menu = Menu()
        host.tb001_init(NS(option_box=NS(menu=menu)))
        box = menu.chk_section_assumptions
        # "&&" draws one "&"; a lone "&" drew none and bound Alt+Space.
        self.assertEqual(box.text(), "Notes && Assumptions")
        self.assertTrue(QtGui.QKeySequence.mnemonic(box.text()).isEmpty())
        self.assertEqual(menu.chk_section_summary.text(), "Executive Summary")
        for key in _Sections.ALL:
            self.assertTrue(getattr(menu, f"chk_section_{key}").toolTip(), key)
        self.assertEqual(
            [menu.cmb_profile.itemData(i) for i in range(menu.cmb_profile.count())],
            [True, False],
        )

    def test_the_run_hands_the_engine_scope_sections_and_progress(self):
        host = _SceneInfoHost()
        host.tb001(_scene_info_widget(_Sections.ALL, "all", unchecked=("summary",)))
        (kwargs,) = host.calls
        self.assertEqual(kwargs["scope"], "all")
        self.assertEqual(kwargs["sections"], ["assumptions"])
        self.assertIs(kwargs["adaptive"], True)
        self.assertIs(kwargs["progress_callback"], host.adapter)
        ((html, view),) = host.views
        self.assertTrue(html.startswith("<h1>Scene Info</h1>"))
        handler = view["link_handler"]
        self.assertIsInstance(handler, functools.partial)
        self.assertIs(handler.func, _UiUtils.dispatch_log_link)
        self.assertIs(handler.keywords["logger"], host.sb.logger)

    def test_selection_scope_needs_a_selection(self):
        host = _SceneInfoHost(selected=False)
        host.tb001(_scene_info_widget(_Sections.ALL, "selection"))
        self.assertEqual(host.calls, [])
        self.assertIn("Nothing selected", host.messages[0])
        host.tb001(_scene_info_widget(_Sections.ALL, "all"))  # Entire Scene needs none
        self.assertEqual(len(host.calls), 1)

    def test_no_sections_is_a_message_not_a_report(self):
        host = _SceneInfoHost()
        host.tb001(_scene_info_widget(_Sections.ALL, unchecked=_Sections.ALL))
        self.assertEqual(host.calls, [])
        self.assertIn("No sections selected", host.messages[0])


if __name__ == "__main__":
    unittest.main()
