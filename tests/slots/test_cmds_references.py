#!/usr/bin/python
# coding=utf-8
"""Every cmds.X(...) call site in the migrated slots resolves on maya.cmds.

This is the highest-value migration test: the most likely class of error
introduced by the PyMEL → cmds migration is a typoed or non-existent
function name (e.g. cmds.displayInfo, which doesn't exist — the correct
form is om.MGlobal.displayInfo).

We AST-walk each slot file, collect every `cmds.X(...)` call, and assert
that `hasattr(maya.cmds, X)` is True. Failures point at the exact slot
file + line number.
"""
import unittest

from _helpers import find_cmds_calls, slot_files
from _host import MAYA_AVAILABLE


# Plugins loaded lazily by individual slots at __init__ time. To validate
# the cmds.* surface those plugins expose, we have to load them up-front
# in the test session.
_REQUIRED_PLUGINS = ("Unfold3D",)


@unittest.skipUnless(MAYA_AVAILABLE, "Requires maya.cmds (run via mayapy)")
class TestCmdsReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import maya.cmds as cmds

        for plugin in _REQUIRED_PLUGINS:
            try:
                if not cmds.pluginInfo(plugin, query=True, loaded=True):
                    cmds.loadPlugin(plugin, quiet=True)
            except RuntimeError as exc:
                # Don't blow up the suite — surface as a per-test note instead.
                print(f"[setUp] could not load plugin {plugin!r}: {exc}")

    def test_every_cmds_call_resolves(self):
        import maya.cmds as cmds  # noqa: WPS433 (local on purpose)

        unresolved = []  # list[tuple[file, line, name]]
        for f in slot_files():
            try:
                source = f.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                self.fail(f"{f.name}: encoding error: {e}")

            for line_no, name in find_cmds_calls(source):
                if not hasattr(cmds, name):
                    unresolved.append((f.name, line_no, name))

        if unresolved:
            lines = [
                f"  {fname}:{line}  cmds.{name}  ← not on maya.cmds"
                for fname, line, name in unresolved
            ]
            self.fail(
                "Found cmds.* references that do not resolve "
                f"({len(unresolved)} total):\n" + "\n".join(lines)
            )


if __name__ == "__main__":
    unittest.main()
