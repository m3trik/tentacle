#!/usr/bin/python
# coding=utf-8
"""Tests for the scene module's workspace-in-footer pattern.

The Set Workspace button (tb000) used to display the current workspace
name as its label, which made the button look like a status indicator
rather than an action. The current design keeps tb000 labeled
"Set Workspace" and routes the workspace name to the MainWindow footer
via FooterStatusController, driven by Maya's workspaceChanged scriptJob.

These checks are AST-based so they can run without a Maya runtime.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE_PY = ROOT / "tentacle" / "slots" / "maya" / "scene.py"


class SceneModuleAST:
    """Cached AST of scene.py and helpers for inspecting it."""

    def __init__(self, source: str):
        self.source = source
        self.tree = ast.parse(source)

    def find_method(self, class_name: str, method_name: str) -> ast.FunctionDef:
        for cls in ast.walk(self.tree):
            if isinstance(cls, ast.ClassDef) and cls.name == class_name:
                for fn in cls.body:
                    if (
                        isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and fn.name == method_name
                    ):
                        return fn
        raise AssertionError(f"{class_name}.{method_name} not found")

    def imported_names(self) -> set[str]:
        names: set[str] = set()
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
        cls.mod = SceneModuleAST(SCENE_PY.read_text(encoding="utf-8"))

    def test_imports_footer_status_controller(self):
        """scene.py must import FooterStatusController from uitk."""
        self.assertIn(
            "FooterStatusController",
            self.mod.imported_names(),
            "scene.py must import FooterStatusController",
        )

    def test_tb000_init_does_not_set_button_text(self):
        """tb000_init must not setText() the workspace name onto the button.

        Anti-pattern: the button used to display the current workspace as
        its label. The button label is now static ("Set Workspace") and
        the workspace name lives in the footer.
        """
        fn = self.mod.find_method("SceneSlots", "tb000_init")
        for call in ast.walk(fn):
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if isinstance(func, ast.Attribute) and func.attr == "setText":
                # Reject: setText on the widget arg with workspace text.
                self.fail(
                    "tb000_init still calls setText — workspace name must go "
                    "to the footer, not the button label."
                )

    def test_has_footer_controller_factory(self):
        """SceneSlots must define _create_footer_controller and resolver."""
        for name in ("_create_footer_controller", "_resolve_workspace_text"):
            try:
                self.mod.find_method("SceneSlots", name)
            except AssertionError:
                self.fail(f"SceneSlots must define {name}")

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

    def test_workspace_changed_handler_exists_and_wired(self):
        """cmb000_init's scriptJob must target _on_workspace_changed.

        That handler is the single fan-out point that refreshes both the
        scenes dropdown and the footer status when Maya's workspace flips.
        """
        try:
            self.mod.find_method("SceneSlots", "_on_workspace_changed")
        except AssertionError:
            self.fail("SceneSlots must define _on_workspace_changed")

        fn = self.mod.find_method("SceneSlots", "cmb000_init")
        src = ast.get_source_segment(self.mod.source, fn) or ""
        self.assertIn(
            "workspaceChanged",
            src,
            "cmb000_init must register a workspaceChanged scriptJob",
        )
        self.assertIn(
            "_on_workspace_changed",
            src,
            "workspaceChanged scriptJob must call _on_workspace_changed",
        )

    def test_workspace_setters_update_footer(self):
        """tb000, lbl005, _open_recent_workspace must refresh the footer.

        The workspaceChanged scriptJob normally fires too, but explicit
        updates after each setter guarantee the footer never lags the
        actual workspace state if the scriptJob is suppressed.
        """
        for method in ("tb000", "lbl005", "_open_recent_workspace"):
            fn = self.mod.find_method("SceneSlots", method)
            src = ast.get_source_segment(self.mod.source, fn) or ""
            self.assertIn(
                "_footer_controller",
                src,
                f"{method} must update self._footer_controller",
            )


if __name__ == "__main__":
    unittest.main()
