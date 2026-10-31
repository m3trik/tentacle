#!/usr/bin/python
# coding=utf-8
"""Each slot module under tentacle.slots.* imports cleanly inside Maya.

Catches: dead imports, syntax errors that AST parse missed (rare), broken
module-level code, missing dependencies.

Skipped automatically when run outside a Maya runtime so the regular
tentacle test suite isn't affected.
"""
import importlib
import unittest

from _helpers import slot_files, slot_module_name
from _host import MAYA_AVAILABLE


@unittest.skipUnless(MAYA_AVAILABLE, "Requires maya.cmds (run via mayapy)")
class TestSlotModulesImport(unittest.TestCase):
    """Subtests over every slot module so a single failure doesn't mask the rest."""

    def test_all_slots_import(self):
        for f in slot_files():
            module_name = slot_module_name(f)
            with self.subTest(module=module_name):
                # One the run already imported has imported cleanly; a reload
                # would fork its classes from the ones the run's switchboards hold.
                if module_name not in importlib.sys.modules:
                    importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
