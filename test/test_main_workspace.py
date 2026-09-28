#!/usr/bin/python
# coding=utf-8
"""Tests for the main lower submenu's Workspace list (slots/maya/main.py).

The workspace controls (Set Dir / Auto Set / Open Root + recent-workspace
history) live in the Main slot's ``list000`` — the existing Workspace Browser —
with the current workspace's directory browser below them. Dir-browser rows
carry a folder icon (``IconManager.set_label_icon``) that sets them apart from
the action rows. Recent workspaces are backed by a shared ``RecentValuesStore``
(valid Maya workspaces only).

AST checks run without Maya; the workspace.mel validation is exercised against a
real Maya when available.
"""

import ast
import os
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN_PY = ROOT / "tentacle" / "slots" / "maya" / "main.py"
MAIN_MIXIN_PY = ROOT / "tentacle" / "slots" / "_main.py"

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
main_module = maya_module("tentacle.slots.maya.main")


class ModuleAST:
    def __init__(self, source: str):
        self.source = source
        self.tree = ast.parse(source)

    def _find(self, class_name, method_name):
        for cls in ast.walk(self.tree):
            if isinstance(cls, ast.ClassDef) and cls.name == class_name:
                for fn in cls.body:
                    if (
                        isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and fn.name == method_name
                    ):
                        return fn
        return None

    def has_method(self, class_name, method_name):
        return self._find(class_name, method_name) is not None

    def method_source(self, class_name, method_name):
        fn = self._find(class_name, method_name)
        return ast.get_source_segment(self.source, fn) or "" if fn else ""


class TestMainMixinStructure(unittest.TestCase):
    """The browse → offer → build → open flow lives ONCE in ``slots/_main.py``
    (``MainMixin``); each fork supplies only the engine hooks."""

    @classmethod
    def setUpClass(cls):
        cls.mod = ModuleAST(MAIN_MIXIN_PY.read_text(encoding="utf-8"))

    def test_shared_flow_and_hooks_declared(self):
        for name in (
            "_set_workspace_interactive",
            "_set_workspace_from_path",
            # hooks — declared (raise NotImplementedError) so a fork that forgets
            # one fails loudly instead of silently inheriting a wrong default
            "_current_workspace_root",
            "_current_scene_path",
            "_browse_workspace_dir",
            "_is_workspace",
            "_create_default_workspace",
            "_switch_to_workspace",
        ):
            self.assertTrue(
                self.mod.has_method("MainMixin", name), f"MainMixin must define {name}"
            )

    def test_set_workspace_offers_then_builds_then_opens(self):
        """Set Workspace on a folder that is not a project must OFFER to build a
        default workspace there from the shared template — marker AND rule folders.

        Regression: Maya's row was a bare ``mel.eval("SetProject")``. Maya's own
        "Create default workspace" answer calls
        ``sp_createAndSetDefaultProject($path, false)`` — the ``false`` is
        *createDirectories* — so it writes a lone ``workspace.mel`` and no
        ``scenes/``, ``sourceimages/`` … folders; Blender's twin just pinned the
        pick. The shared flow: browse → offer (never build unasked; Retry
        re-browses) → build via the fork's ``_create_default_workspace`` → open.
        """
        src = self.mod.method_source("MainMixin", "_set_workspace_interactive")
        for needle in (
            "_browse_workspace_dir",
            "_is_workspace",
            "message_box",
            '"Retry"',
            "_create_default_workspace",
            "_switch_to_workspace",
        ):
            self.assertIn(needle, src, f"_set_workspace_interactive must use {needle}")
        self.assertNotIn("SetProject", src)

    def test_recent_selection_validates(self):
        src = self.mod.method_source("MainMixin", "_set_workspace_from_path")
        self.assertIn("_is_workspace", src)
        self.assertIn("_switch_to_workspace", src)


class TestMainWorkspaceStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = ModuleAST(MAIN_PY.read_text(encoding="utf-8"))

    def test_workspace_methods_present(self):
        for name in (
            "list000_init",
            "list000",
            "_is_workspace",
            "_auto_set_workspace",
            "_switch_to_workspace",
            # MainMixin hooks
            "_current_workspace_root",
            "_current_scene_path",
            "_browse_workspace_dir",
            "_create_default_workspace",
        ):
            self.assertTrue(
                self.mod.has_method("MainSlots", name), f"MainSlots must define {name}"
            )

    def test_list000_adds_scene_dir_row(self):
        self.assertIn(
            "self._add_scene_dir_row(widget)",
            self.mod.method_source("MainSlots", "list000_init"),
        )

    def test_scene_path_hook_ignores_batch_phantom(self):
        """The hook reads ``mtk.EnvUtils.saved_scene_path`` (behavior pinned by
        mayatk's ``TestSavedScenePath``), not ``sceneName``: batch Maya reports
        an unsaved scene as a phantom ``<project>/untitled`` whose folder exists,
        so the Scene Directory row would offer the project root."""
        src = self.mod.method_source("MainSlots", "_current_scene_path")
        self.assertIn("mtk.EnvUtils.saved_scene_path()", src)
        self.assertNotIn('get_env_info("scene")', src)

    def test_does_not_reimplement_shared_flow(self):
        for name in (
            "_set_workspace_interactive",
            "_set_workspace_from_path",
            "_add_scene_dir_row",
        ):
            self.assertFalse(
                self.mod.has_method("MainSlots", name),
                f"{name} belongs to MainMixin — the fork must not re-implement it",
            )
        self.assertIn("class MainSlots(MainMixin, SlotsMaya)", self.mod.source)

    def test_hooks_use_the_shared_template_and_native_browser(self):
        """The build hook is ``mtk.create_workspace`` (the same template Workspace
        Map ▸ New Project builds from); the browser is Maya's ``fileDialog2``."""
        self.assertIn(
            "mtk.create_workspace",
            self.mod.method_source("MainSlots", "_create_default_workspace"),
        )
        self.assertIn(
            "fileDialog2", self.mod.method_source("MainSlots", "_browse_workspace_dir")
        )

    def test_list000_builds_store_and_actions(self):
        """list000_init must build the store, add the editing actions, render the
        store's recent values, and icon the dir-browser row."""
        init = self.mod.method_source("MainSlots", "list000_init")
        for needle in (
            "RecentValuesStore",
            "workspace_recent_projects",  # shared key → history carries over
            "__set_dir__",
            "__auto__",
            'set_label_icon(w, "folder_filled")',  # dir-browser root row gets a folder icon
            "valid_values",
            "display_map",
        ):
            self.assertIn(needle, init, f"list000_init must reference {needle}")

    def test_no_separator_between_actions_and_browser(self):
        """The old titled separator is gone — the folder icon on the dir rows is the
        differentiator now, so no Separator widget should be constructed or imported."""
        init = self.mod.method_source("MainSlots", "list000_init")
        self.assertNotIn("Separator(", init, "no Separator widget should be added")
        self.assertNotIn("widgets.separator", init, "no Separator import should remain")

    def test_dir_browser_rows_get_folder_icon(self):
        """Every dir-browser row (root + each nested folder) is marked with the
        folder icon so it reads as a directory, not an action."""
        init = self.mod.method_source("MainSlots", "list000_init")
        self.assertIn('set_label_icon(w, "folder_filled")', init)
        populate = self.mod.method_source("MainSlots", "_populate_dir_sublist")
        self.assertIn('set_label_icon(item, "folder_filled")', populate)

    def test_auto_and_recents_nest_under_set_workspace(self):
        """Auto Set + Recent Workspaces live in the Set Workspace flyout, not at
        the root — the root holds only Set Workspace and the dir browser."""
        init = self.mod.method_source("MainSlots", "list000_init")
        # Both the auto action and the recents sub-flyout are added to the Set
        # Workspace sublist (captured as ``set_ws``), not directly to ``widget``.
        self.assertIn('set_ws.sublist.add("Auto Set Workspace"', init)
        self.assertIn('set_ws.sublist.add("Recent Workspaces")', init)

    def test_list000_dispatches_all_row_kinds(self):
        # The fork keeps the decorated handler; the body is MainMixin's, shared
        # with the Blender fork.
        self.assertIn(
            "self._dispatch_workspace_item(item)",
            self.mod.method_source("MainSlots", "list000"),
        )
        src = ModuleAST(MAIN_MIXIN_PY.read_text(encoding="utf-8")).method_source(
            "MainMixin", "_dispatch_workspace_item"
        )
        for needle in (
            "_set_workspace_interactive",
            "_auto_set_workspace",
            "_set_workspace_from_path",
            "__recent__",
            "isdir",  # directory-browser entries (incl. workspace root) open in explorer
        ):
            self.assertIn(needle, src, f"list000 must handle {needle}")

    def test_switch_opens_through_native_setproject(self):
        """``_switch_to_workspace`` opens via MEL ``setProject "<path>"`` (the
        no-popup form) rather than a raw ``workspace -o`` so recent projects /
        project-window refresh / browser prefs behave exactly as Maya's own
        Set Project — the flow this slot replaced. (Headless it falls back to a
        plain ``workspace -o`` — ``setProject``'s ``savePrefs`` tail is GUI-only.)"""
        src = self.mod.method_source("MainSlots", "_switch_to_workspace")
        self.assertIn('setProject "', src)
        self.assertIn("about(batch=True)", src)

    def test_editor_row_opens_native_project_window(self):
        """The Edit Workspace row opens Maya's native Project Window (blendertk's
        twin row opens its own workspace_editor panel)."""
        init = self.mod.method_source("MainSlots", "list000_init")
        self.assertIn('widget.add("Edit Workspace", data="__editor__")', init)
        dispatch = ModuleAST(MAIN_MIXIN_PY.read_text(encoding="utf-8")).method_source(
            "MainMixin", "_dispatch_workspace_item"
        )
        self.assertIn("__editor__", dispatch)
        src = self.mod.method_source("MainSlots", "_open_workspace_editor")
        self.assertIn("ProjectWindow", src)


class _StubRow:
    """An ExpandableList row: what ``add()`` was given, readable back through
    ``item_data()`` the way the dispatcher reads a clicked row."""

    def __init__(self, label, data, kwargs):
        self.label, self.data, self.kwargs = label, data, kwargs

    def item_data(self):
        return self.data


class _StubList:
    def __init__(self):
        self.rows = []

    def add(self, label, data=None, **kwargs):
        row = _StubRow(label, data, kwargs)
        self.rows.append(row)
        return row


class TestSceneDirRow(unittest.TestCase):
    """``MainMixin._add_scene_dir_row`` — the Workspace tab's link to the open
    scene's folder. Present (folder icon, full path as tooltip) only when the
    scene is saved and its folder exists; a click opens it through the
    dispatcher's directory branch. DCC-free: the scene comes from the fork's
    ``_current_scene_path`` hook, stubbed here."""

    def setUp(self):
        import pythontk as ptk
        from tentacle.slots._main import MainMixin

        self.tmp = ptk.TempArtifacts("tentacle_main_scene_dir", policy="scoped")
        self.root = self.tmp.dir_path()
        self.icons = []
        self.scene = ""
        self.inst = MainMixin()
        self.inst._current_scene_path = lambda: self.scene
        self.inst.sb = types.SimpleNamespace(
            IconManager=types.SimpleNamespace(
                set_label_icon=lambda w, name: self.icons.append((w, name))
            ),
            handlers=types.SimpleNamespace(
                marking_menu=types.SimpleNamespace(hide=lambda: None)
            ),
        )
        self.list = _StubList()

    def tearDown(self):
        self.tmp.cleanup()

    def test_saved_scene_adds_folder_row(self):
        # Maya's ``file -q -sceneName`` is forward-slashed; the row's data must
        # be native so the system file browser opens it reliably.
        self.scene = os.path.join(self.root, "shot_010.ma").replace("\\", "/")
        self.inst._add_scene_dir_row(self.list)
        (row,) = self.list.rows
        self.assertEqual(row.label, "Scene Directory")
        self.assertEqual(row.data, os.path.normpath(self.root))
        self.assertEqual(row.kwargs.get("setToolTip"), os.path.normpath(self.root))
        self.assertEqual(self.icons, [(row, "folder_filled")])

    def test_click_opens_scene_folder_in_explorer(self):
        from unittest import mock

        import pythontk as ptk

        self.scene = os.path.join(self.root, "shot_010.ma")
        self.inst._add_scene_dir_row(self.list)
        with mock.patch.object(ptk.FileUtils, "open_explorer") as open_explorer:
            self.inst._dispatch_workspace_item(self.list.rows[0])
        open_explorer.assert_called_once_with(os.path.normpath(self.root))

    def test_unsaved_scene_adds_nothing(self):
        self.inst._add_scene_dir_row(self.list)
        self.assertEqual(self.list.rows, [])

    def test_missing_folder_adds_nothing(self):
        self.scene = os.path.join(self.root, "moved_away", "shot_010.ma")
        self.inst._add_scene_dir_row(self.list)
        self.assertEqual(self.list.rows, [])


class _StubSb:
    def __init__(self, choice=None):
        self.choice = choice
        self.messages = []
        # Setters call self.sb.handlers.marking_menu.hide(); stub it out.
        self.handlers = types.SimpleNamespace(
            marking_menu=types.SimpleNamespace(hide=lambda: None)
        )

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))
        return self.choice


class _StubStore:
    def __init__(self):
        self.recorded = []

    def record(self, value):
        self.recorded.append(value)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestSetWorkspaceFromPath(unittest.TestCase):
    """MainSlots._set_workspace_from_path validates workspace.mel before switching."""

    def setUp(self):
        import pythontk as ptk

        cmds.file(new=True, force=True)
        self._before = cmds.workspace(query=True, rd=True)
        self.inst = main_module.MainSlots.__new__(main_module.MainSlots)
        self.inst.sb = _StubSb()
        self.inst._workspace_store = _StubStore()
        self.tmp = ptk.TempArtifacts("tentacle_main_ws", policy="scoped")
        self.root = self.tmp.dir_path()

    def tearDown(self):
        # Restore the workspace BEFORE removing the folder Maya may be pointed at —
        # a leaked switch bleeds into every later test's "current workspace".
        cmds.workspace(self._before, openWorkspace=True)
        self.tmp.cleanup()
        cmds.file(new=True, force=True)

    def test_rejects_path_with_no_workspace_mel(self):
        before = cmds.workspace(query=True, rd=True)
        self.inst._set_workspace_from_path(self.root)
        self.assertEqual(before, cmds.workspace(query=True, rd=True))
        self.assertTrue(self.inst.sb.messages, "Expected a user-visible warning")
        self.assertEqual(self.inst._workspace_store.recorded, [])

    def test_accepts_path_with_workspace_mel(self):
        with open(os.path.join(self.root, "workspace.mel"), "w") as f:
            f.write("//Maya workspace stub\n")
        self.inst._set_workspace_from_path(self.root)
        new_ws = cmds.workspace(query=True, rd=True)
        self.assertEqual(
            os.path.normpath(new_ws).lower(), os.path.normpath(self.root).lower()
        )
        # Selecting a recent workspace bumps it to most-recent in the store.
        self.assertIn(self.root, self.inst._workspace_store.recorded)

    def test_message_shows_real_name_for_trailing_slash_path(self):
        """A stored recent-workspace entry with a trailing separator (what
        Maya's raw ``workspace -q -rd`` returns, and what a stale
        pre-normpath history entry may still carry) must still show the
        real workspace name — not collapse to a bare period.

        Regression: ``os.path.basename()`` on a trailing-slash path returns
        ``""``, so ``f"Workspace set to {name}."`` rendered as literally
        "Workspace set to ." with the sentence's own period misread as the
        workspace name.
        """
        with open(os.path.join(self.root, "workspace.mel"), "w") as f:
            f.write("//Maya workspace stub\n")
        trailing = self.root + os.sep
        self.inst._set_workspace_from_path(trailing)
        text = self.inst.sb.messages[-1][0][0]
        expected_name = os.path.basename(os.path.normpath(self.root))
        self.assertIn(expected_name, text)
        self.assertNotIn("set to .", text)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestSetWorkspaceInteractive(unittest.TestCase):
    """MainSlots._set_workspace_interactive: browse → (offer + build) → open.

    The directory browser is stubbed at ``main_module.cmds.fileDialog2`` (the
    slot's own reference); the offer is answered through ``_StubSb.choice``.
    """

    def setUp(self):
        import pythontk as ptk

        cmds.file(new=True, force=True)
        self._before = cmds.workspace(query=True, rd=True)
        self.inst = main_module.MainSlots.__new__(main_module.MainSlots)
        self.inst.sb = _StubSb()
        self.inst._workspace_store = _StubStore()
        self.tmp = ptk.TempArtifacts("tentacle_main_ws", policy="scoped")
        self.root = self.tmp.dir_path()
        self._orig_dialog = main_module.cmds.fileDialog2

    def tearDown(self):
        main_module.cmds.fileDialog2 = self._orig_dialog
        cmds.workspace(self._before, openWorkspace=True)
        self.tmp.cleanup()
        cmds.file(new=True, force=True)

    def _pick(self, path):
        main_module.cmds.fileDialog2 = lambda *a, **k: [path] if path else None

    def _same(self, a, b):
        return os.path.normcase(os.path.normpath(a)) == os.path.normcase(
            os.path.normpath(b)
        )

    def test_unmarked_folder_offer_accepted_builds_marker_and_rule_folders(self):
        """THE bug: accepting the offer must leave the standard rule folders on
        disk (not just workspace.mel), and Maya must be switched to it."""
        import pythontk as ptk

        self._pick(self.root)
        self.inst.sb.choice = "Yes"
        self.inst._set_workspace_interactive()
        ws = ptk.Workspace.load(self.root)
        self.assertTrue(ws.is_marked, "workspace.mel must be written")
        rule_dirs = {
            v
            for v in ptk.DEFAULT_FILE_RULES.values()
            if v != "." and not os.path.isabs(v)
        }
        for rel in rule_dirs:
            self.assertTrue(
                os.path.isdir(os.path.join(self.root, rel)),
                f"missing rule folder {rel}",
            )
        self.assertTrue(self._same(cmds.workspace(query=True, rd=True), self.root))
        self.assertTrue(
            any(self._same(r, self.root) for r in self.inst._workspace_store.recorded)
        )

    def test_unmarked_folder_offer_declined_creates_nothing(self):
        self._pick(self.root)
        self.inst.sb.choice = "Cancel"
        self.inst._set_workspace_interactive()
        self.assertEqual(os.listdir(self.root), [], "nothing may be written on Cancel")
        self.assertTrue(self._same(cmds.workspace(query=True, rd=True), self._before))
        self.assertEqual(self.inst._workspace_store.recorded, [])

    def test_marked_folder_opens_without_offer(self):
        with open(os.path.join(self.root, "workspace.mel"), "w") as f:
            f.write('//Maya Project Definition\n\nworkspace -fr "scene" "scenes";\n')
        self._pick(self.root)
        self.inst.sb.choice = "Cancel"  # would abort if an offer were (wrongly) made
        self.inst._set_workspace_interactive()
        self.assertTrue(self._same(cmds.workspace(query=True, rd=True), self.root))
        # A project's own rules win — no template folders imposed on an existing one.
        self.assertFalse(os.path.isdir(os.path.join(self.root, "sourceimages")))

    def test_dismissed_browser_is_a_noop(self):
        self._pick(None)
        self.inst._set_workspace_interactive()
        self.assertEqual(os.listdir(self.root), [])
        self.assertTrue(self._same(cmds.workspace(query=True, rd=True), self._before))
        self.assertEqual(self.inst.sb.messages, [])


if __name__ == "__main__":
    unittest.main()
