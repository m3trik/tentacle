# !/usr/bin/python
# coding=utf-8
"""The Blender harnesses (``test/blender/*_check.py``) keep their runs off live stores.

Each harness runs in a fresh Blender launched by hand and builds tentacle's real
UI there: a marking menu persists its bindings as it is constructed, and panels
persist widget state, into the developer's ``HKCU\\Software\\uitk`` and presets
root. None of them sandboxed those stores. Every harness now activates
``uitk.testing.TestSandbox`` ahead of its tentacle import.

Static: running the harnesses means real GUI windows and, for most, real OS
input, which no automated suite may send.
"""

import ast
import unittest
from pathlib import Path

HARNESSES = sorted((Path(__file__).parent / "blender").glob("*_check.py"))


def _own_nodes(scope):
    """The nodes of *scope*'s own body, not of the functions nested in it."""
    nested = (ast.FunctionDef, ast.AsyncFunctionDef)
    stack = [node for node in scope.body if not isinstance(node, nested)]
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, nested):
                stack.append(child)


def _activations_and_imports(scope):
    """Line numbers of ``TestSandbox.activate()`` calls and tentacle imports."""
    activations, imports = [], []
    for node in _own_nodes(scope):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "activate"
            and getattr(node.func.value, "id", None) == "TestSandbox"
        ):
            activations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "tentacle"
        ):
            imports.append(node.lineno)
        elif isinstance(node, ast.Import) and any(
            alias.name.startswith("tentacle") for alias in node.names
        ):
            imports.append(node.lineno)
    return activations, imports


class TestEveryHarnessIsSandboxed(unittest.TestCase):
    def test_there_are_harnesses(self):
        self.assertGreater(len(HARNESSES), 30)

    def test_each_activates_the_sandbox_before_its_tentacle_import(self):
        """In the scope that activates it (module or function), a tentacle
        import comes after. A function the harness schedules later is out of a
        static check's reach; the activation leads the flow that schedules it."""
        unsandboxed = []
        for path in HARNESSES:
            source = path.read_text(encoding="utf-8-sig")  # one carries a BOM
            tree = ast.parse(source)
            scopes = [tree] + [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            activated = "from uitk.testing import TestSandbox" in source
            found = False
            for scope in scopes:
                activations, imports = _activations_and_imports(scope)
                if activations:
                    found = True
                    if imports and min(imports) < min(activations):
                        activated = False
            if not (activated and found):
                unsandboxed.append(path.name)
        self.assertEqual(unsandboxed, [])

    def test_one_run_on_a_developer_profile_activates_before_any_timer(self):
        """A harness documented to run WITHOUT ``--factory-startup`` gets the
        developer's profile, whose tentacle add-on builds the UI against the
        live stores from its own launch timer -- before any harness timer
        fires -- and the harness then reuses it. So it activates at module
        level, before Blender's event loop runs anything."""
        late = []
        for path in HARNESSES:
            source = path.read_text(encoding="utf-8-sig")  # one carries a BOM
            launch = next(
                (
                    ln
                    for ln in source.splitlines()
                    if "blender" in ln and "--python" in ln
                ),
                "",
            )
            if "--factory-startup" in launch:
                continue
            activations, _ = _activations_and_imports(ast.parse(source))
            if not activations:
                late.append(path.name)
        self.assertEqual(late, [])


if __name__ == "__main__":
    unittest.main()
