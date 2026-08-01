#!/usr/bin/python
# coding=utf-8
"""Tests for the scene module's workspace *footer*.

The workspace *controls* (Set Dir / Auto Set / Open Root / recent history) used
to live here as a docked "Set Workspace" button; they now live in the main
lower submenu's Workspace list (see ``slots/maya/main.py`` and
``test_main_workspace.py``). What remains in the scene module is the *status
footer*: the current workspace name routed to the MainWindow footer via
FooterStatusController.

The *wiring* (subscribe → own the controller → refresh) is identical on both
DCCs and so lives once in ``slots/_scene.py``'s ``SceneMixin``; each fork
supplies only its hooks — ``FOOTER_EVENTS`` (Maya has a real
``workspaceChanged``, Blender settles for scene open/save),
``_script_job_manager`` and ``_resolve_workspace_text``. The controller is
obtained from the footer widget (``footer.status_controller(...)``) rather than
by importing ``FooterStatusController``: slots reach uitk through the
Switchboard only.

These checks are AST-based so they can run without a Maya runtime.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE_MIXIN_PY = ROOT / "tentacle" / "slots" / "_scene.py"
SCENE_PY = ROOT / "tentacle" / "slots" / "maya" / "scene.py"
SCENE_BLENDER_PY = ROOT / "tentacle" / "slots" / "blender" / "scene.py"


class ModuleAST:
    """Cached AST of a slot module and helpers for inspecting it."""

    def __init__(self, source: str):
        self.source = source
        self.tree = ast.parse(source)

    def find_method(self, class_name: str, method_name: str) -> ast.FunctionDef:
        fn = self._maybe_find_method(class_name, method_name)
        if fn is None:
            raise AssertionError(f"{class_name}.{method_name} not found")
        return fn

    def has_method(self, class_name: str, method_name: str) -> bool:
        return self._maybe_find_method(class_name, method_name) is not None

    def _maybe_find_method(self, class_name: str, method_name: str):
        for cls in ast.walk(self.tree):
            if isinstance(cls, ast.ClassDef) and cls.name == class_name:
                for fn in cls.body:
                    if (
                        isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and fn.name == method_name
                    ):
                        return fn
        return None

    def method_source(self, class_name: str, method_name: str) -> str:
        return ast.get_source_segment(
            self.source, self.find_method(class_name, method_name)
        ) or ""

    def imported_names(self) -> set:
        names = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                for a in node.names:
                    names.add(a.asname or a.name)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    names.add(a.asname or a.name.split(".", 1)[0])
        return names

    def class_attr_source(self, class_name: str, attr: str) -> str:
        """Source of a class-level ``attr = ...`` assignment (raises if absent)."""
        for cls in ast.walk(self.tree):
            if isinstance(cls, ast.ClassDef) and cls.name == class_name:
                for node in cls.body:
                    if isinstance(node, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == attr for t in node.targets
                    ):
                        return ast.get_source_segment(self.source, node) or ""
        raise AssertionError(f"{class_name}.{attr} not found")


class TestSceneFooterWiringIsShared(unittest.TestCase):
    """The footer wiring lives ONCE in SceneMixin — the Maya and Blender forks
    differ only by their hooks. A fork that re-implements
    _create_footer_controller is the duplication this consolidation removed."""

    @classmethod
    def setUpClass(cls):
        cls.mixin = ModuleAST(SCENE_MIXIN_PY.read_text(encoding="utf-8"))

    def test_mixin_owns_the_wiring(self):
        for name in (
            "_create_footer_controller",
            "_on_workspace_changed",
            "_script_job_manager",
            "_resolve_workspace_text",
        ):
            self.assertTrue(
                self.mixin.has_method("SceneMixin", name),
                f"SceneMixin must define {name}",
            )

    def test_wiring_subscribes_declared_events_to_the_handler(self):
        """_create_footer_controller must subscribe the DCC's FOOTER_EVENTS to
        _on_workspace_changed, which refreshes the footer status when the
        workspace flips (including changes made from the main Workspace list).
        The subscription must NOT ride a widget _init — the old host (the
        Workspace-Scenes combo's cmb000_init) went dead when that widget left
        scene.ui, and the footer silently stopped refreshing."""
        src = self.mixin.method_source("SceneMixin", "_create_footer_controller")
        self.assertIn("FOOTER_EVENTS", src)
        self.assertIn("subscribe(", src)
        self.assertIn("_on_workspace_changed", src)
        self.assertIn("connect_cleanup", src)
        handler = self.mixin.method_source("SceneMixin", "_on_workspace_changed")
        self.assertIn("_footer_controller", handler)

    def test_controller_comes_from_the_footer_widget(self):
        """The controller is built by the footer itself, not by an imported class:
        a slot's uitk access goes through the Switchboard (``self.ui.footer``)."""
        src = self.mixin.method_source("SceneMixin", "_create_footer_controller")
        self.assertIn("footer.status_controller(", src)
        self.assertNotIn(
            "FooterStatusController",
            self.mixin.imported_names(),
            "the mixin must not import FooterStatusController",
        )

    def test_default_status_text(self):
        self.assertIn("No workspace set", self.mixin.source)


class TestSceneWorkspaceFooter(unittest.TestCase):
    """Maya fork: hooks only."""

    @classmethod
    def setUpClass(cls):
        cls.mod = ModuleAST(SCENE_PY.read_text(encoding="utf-8"))

    def test_declares_maya_footer_event(self):
        self.assertIn(
            "workspaceChanged", self.mod.class_attr_source("SceneSlots", "FOOTER_EVENTS")
        )

    def test_supplies_hooks(self):
        for name in ("_script_job_manager", "_resolve_workspace_text"):
            self.assertTrue(
                self.mod.has_method("SceneSlots", name),
                f"SceneSlots must define {name}",
            )
        self.assertIn(
            "mtk.ScriptJobManager",
            self.mod.method_source("SceneSlots", "_script_job_manager"),
        )

    def test_does_not_reimplement_shared_wiring(self):
        for name in ("_create_footer_controller", "_on_workspace_changed"):
            self.assertFalse(
                self.mod.has_method("SceneSlots", name),
                f"{name} belongs to SceneMixin — the fork must not re-implement it",
            )

    def test_footer_controller_initialized_in_ctor(self):
        """__init__ must assign self._footer_controller."""
        init = self.mod.find_method("SceneSlots", "__init__")
        assigns = [
            n
            for n in ast.walk(init)
            if isinstance(n, ast.Assign)
            and any(
                isinstance(t, ast.Attribute) and t.attr == "_footer_controller"
                for t in n.targets
            )
        ]
        self.assertTrue(
            assigns, "SceneSlots.__init__ must set self._footer_controller"
        )


class TestWorkspaceControlsLeftScene(unittest.TestCase):
    """The Set Workspace button + its logic must no longer be in the scene
    module — they moved to the main lower submenu's Workspace list."""

    @classmethod
    def setUpClass(cls):
        cls.mod = ModuleAST(SCENE_PY.read_text(encoding="utf-8"))

    def test_old_and_moved_surface_absent(self):
        # NOTE: list001/list001_init are deliberately NOT in this list — the
        # objectName was recycled 2026-07-16 for the submenu's Import
        # expandable list (unrelated to the old Workspace list this test
        # pins). The workspace move is still pinned by its helper names below.
        for gone in (
            "tb000_init",
            "tb000",
            "lbl004",
            "lbl005",
            "_open_recent_workspace",
            "_set_workspace_interactive",
            "_auto_set_workspace",
            "_set_workspace_from_path",
            # dead Workspace-Scenes cluster (widgets removed from scene.ui;
            # deleted 2026-07-02 — the footer subscription moved to
            # _create_footer_controller):
            "cmb000_init",
            "cmb000",
            "txt000",
        ):
            self.assertFalse(
                self.mod.has_method("SceneSlots", gone),
                f"{gone} should no longer be in scene.py (moved to main.py)",
            )


class TestSceneWorkspaceFooterBlender(unittest.TestCase):
    """Blender fork: the same shared wiring over ``btk.get_env_info("workspace_dir")``,
    refreshed on scene open/save via blendertk's ScriptJobManager (Blender has no
    ``workspaceChanged`` event — a session-pin change shows on the next file event)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = ModuleAST(SCENE_BLENDER_PY.read_text(encoding="utf-8"))

    def test_declares_blender_footer_events(self):
        src = self.mod.class_attr_source("SceneSlots", "FOOTER_EVENTS")
        self.assertIn("SceneOpened", src)
        self.assertIn("SceneSaved", src)

    def test_does_not_reimplement_shared_wiring(self):
        for name in ("_create_footer_controller", "_on_workspace_changed"):
            self.assertFalse(
                self.mod.has_method("SceneSlots", name),
                f"{name} belongs to SceneMixin — the fork must not re-implement it",
            )

    def test_ctor_initializes_controller(self):
        src = self.mod.method_source("SceneSlots", "__init__")
        self.assertIn("_create_footer_controller", src)

    def test_supplies_hooks(self):
        self.assertIn(
            "btk.ScriptJobManager",
            self.mod.method_source("SceneSlots", "_script_job_manager"),
        )
        self.assertIn(
            'get_env_info("workspace_dir")',
            self.mod.method_source("SceneSlots", "_resolve_workspace_text"),
        )


if __name__ == "__main__":
    unittest.main()
