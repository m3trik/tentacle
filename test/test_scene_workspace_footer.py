#!/usr/bin/python
# coding=utf-8
"""Tests for the scene module's workspace *footer*.

The workspace *controls* (Set Dir / Auto Set / Open Root / recent history) used
to live here as a docked "Set Workspace" button; they now live in the main
lower submenu's Workspace list (see ``slots/maya/main.py`` and
``test_main_workspace.py``). What remains in the scene module is the *status
footer*: the current workspace name routed to the MainWindow footer via
FooterStatusController, driven by Maya's workspaceChanged scriptJob.

These checks are AST-based so they can run without a Maya runtime.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE_PY = ROOT / "tentacle" / "slots" / "maya" / "scene.py"


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


class TestSceneWorkspaceFooter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = ModuleAST(SCENE_PY.read_text(encoding="utf-8"))

    def test_imports_footer_status_controller(self):
        """scene.py must import FooterStatusController from uitk."""
        self.assertIn(
            "FooterStatusController",
            self.mod.imported_names(),
            "scene.py must import FooterStatusController",
        )

    def test_has_footer_controller_factory(self):
        """SceneSlots must define _create_footer_controller and resolver."""
        for name in ("_create_footer_controller", "_resolve_workspace_text"):
            self.assertTrue(
                self.mod.has_method("SceneSlots", name),
                f"SceneSlots must define {name}",
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

    def test_workspace_changed_handler_updates_footer(self):
        """cmb000_init's scriptJob must target _on_workspace_changed, which
        refreshes both the scenes dropdown and the footer status when Maya's
        workspace flips (including changes made from the main Workspace list)."""
        self.assertTrue(
            self.mod.has_method("SceneSlots", "_on_workspace_changed"),
            "SceneSlots must define _on_workspace_changed",
        )
        src = self.mod.method_source("SceneSlots", "cmb000_init")
        self.assertIn("workspaceChanged", src)
        self.assertIn("_on_workspace_changed", src)
        handler = self.mod.method_source("SceneSlots", "_on_workspace_changed")
        self.assertIn("_footer_controller", handler)


class TestWorkspaceControlsLeftScene(unittest.TestCase):
    """The Set Workspace button + its logic must no longer be in the scene
    module — they moved to the main lower submenu's Workspace list."""

    @classmethod
    def setUpClass(cls):
        cls.mod = ModuleAST(SCENE_PY.read_text(encoding="utf-8"))

    def test_old_and_moved_surface_absent(self):
        for gone in (
            "tb000_init",
            "tb000",
            "lbl004",
            "lbl005",
            "_open_recent_workspace",
            "list001_init",
            "list001",
            "_set_workspace_interactive",
            "_auto_set_workspace",
            "_set_workspace_from_path",
        ):
            self.assertFalse(
                self.mod.has_method("SceneSlots", gone),
                f"{gone} should no longer be in scene.py (moved to main.py)",
            )


if __name__ == "__main__":
    unittest.main()
