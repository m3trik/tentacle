#!/usr/bin/python
# coding=utf-8
"""Every shared tool (``ui/tools/`` + ``slots/tools/``) loads in Blender's handler.

Needs **Qt, not bpy**: a real (offscreen) Qt / Switchboard / BlenderUiHandler
stack with tentacle's shared roots registered, the way ``tcl_blender`` stands
it up. Each tool's ``.ui`` compiles and binds to its one tentacle Slots class
over blendertk (``Slots.tk``); a Preview panel's Create button is enabled (the
``.ui`` ships it disabled and Preview takes it over); the panel opens sticky by
the panel tag. Maya's twin is ``test_marking_menu_gui.py`` (fresh GUI Maya).
"""

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")

HERE = os.path.dirname(os.path.abspath(__file__))
# blendertk is no install of the workspace Python: its repo goes on the path.
_BLENDERTK = os.path.join(os.path.dirname(os.path.dirname(HERE)), "blendertk")
if os.path.isdir(_BLENDERTK) and _BLENDERTK not in sys.path:
    sys.path.insert(0, _BLENDERTK)

try:
    from qtpy import QtWidgets
except Exception:  # pragma: no cover - Qt absent
    QtWidgets = None

if QtWidgets is not None:
    # Keep the panels' settings off the developer's live uitk stores.
    from uitk.testing import TestSandbox

    TestSandbox.activate()

#: Tools whose Slots class reads the scene as it loads (its ``__init__`` or an
#: ``*_init`` calls ``bpy``): they load in a real Blender only
#: (``test/blender/menus_load_check.py``).
NEEDS_BPY = frozenset()


@unittest.skipIf(QtWidgets is None, "Qt not available")
class TestEverySharedToolLoadsInBlender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from uitk import Switchboard

        import blendertk
        from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler
        from tentacle.tcl import Tcl
        import tentacle

        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.btk = blendertk
        cls.handler = BlenderUiHandler(switchboard=Switchboard())
        # A process singleton: in a run that built it earlier (another panel
        # module) it keeps ITS switchboard, which is the one holding the UIs.
        cls.sb = cls.handler.sb
        Tcl.register_shared(cls.sb)
        cls.tools_dir = Path(tentacle.__file__).resolve().parent / "ui" / "tools"
        cls.names = sorted(p.stem for p in cls.tools_dir.glob("*.ui"))

    def test_each_tool_binds_its_tentacle_slots_over_blendertk(self):
        self.assertIn("duplicate_radial", self.names)
        for name in self.names:
            if name in NEEDS_BPY:
                continue
            with self.subTest(tool=name):
                ui = self.handler.get(name)
                for _ in range(3):
                    self.app.processEvents()
                self.assertIsNotNone(ui, f"{name} failed to load")
                filepath = self.sb.registry.ui_registry.get(
                    filename=name, return_field="filepath"
                )
                self.assertTrue(
                    Path(filepath).resolve().is_relative_to(self.tools_dir), filepath
                )
                slots = self.sb.get_slots_instance(ui)
                self.assertEqual(type(slots).__module__, f"tentacle.slots.tools.{name}")
                self.assertIs(slots.tk, self.btk)
                if hasattr(slots, "preview"):
                    self.assertIsInstance(slots.preview, self.btk.Preview)
                    self.assertTrue(
                        ui.b000.isEnabled(), "Create stays dead: Preview never took it"
                    )
                self.assertEqual(
                    self.handler.default_persistence(ui),
                    self.handler.PERSISTENCE_STICKY,
                )


if __name__ == "__main__":
    unittest.main()
