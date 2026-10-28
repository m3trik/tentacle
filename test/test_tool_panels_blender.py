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

    def _loaded(self, name):
        ui = self.handler.get(name)
        for _ in range(3):
            self.app.processEvents()
        return ui, self.sb.get_slots_instance(ui)

    def test_curtain_lists_the_hosts_built_in_presets(self):
        """The preset combo is uitk's PresetManager over blendertk's shipped
        presets (the combo and its builtin_dir work, not just "didn't error")."""
        ui, _slots = self._loaded("curtain")
        items = [ui.cmb000.itemText(i) for i in range(ui.cmb000.count())]
        self.assertIn("Stage Swag", items)
        self.assertIn("Shower Curtain", items)

    def test_naming_labels_every_convention_row_and_offers_presets(self):
        """Suffix By Type names each row's type in a label to the RIGHT of its
        field (the fields ship filled, so placeholders never show) and carries
        the convention preset combo. The picker wraps each field, so find the
        grid cell holding it."""
        import pythontk as ptk

        ui, slots = self._loaded("naming")
        menu = ui.tb003.option_box.menu
        if not (menu.gridLayout and menu.gridLayout.count()):
            slots.tb003_init(ui.tb003)
        grid = menu.gridLayout
        rows = list(slots._convention_editor.fields())
        unlabeled = []
        for key, field in rows:
            cell = None
            for i in range(grid.count()):
                held = grid.itemAt(i).widget()
                if held is not None and (held is field or held.isAncestorOf(field)):
                    cell = grid.getItemPosition(i)[:2]
                    break
            beside = grid.itemAtPosition(cell[0], 1) if cell and cell[1] == 0 else None
            text = beside.widget().text() if beside and beside.widget() else None
            if text != ptk.NamingConvention.label(key):
                unlabeled.append((key, cell, text))
        self.assertEqual(len(rows), 22)
        self.assertEqual(unlabeled, [])
        self.assertTrue(menu.add_presets)
        self.assertEqual(
            menu.presets.value_applier, slots._convention_editor.apply_preset
        )

    def test_scene_exporter_fbx_preset_row_keeps_its_option_box(self):
        """The FBX Preset row (cmb000) carries its own option box: the wrap swaps
        the combo for its container INSIDE a WidgetComboBox row (replaceWidget), a
        structure nothing else covers. The row stays, the menu holds Open / Edit,
        the Settings combo has no actions section, and the two preset stores sit
        in different folders (the 2026-08-19 window-template / FBX-store
        collision)."""
        ui, _slots = self._loaded("scene_exporter")
        ui.show()  # offscreen; drives row registration -> cmb000_init -> wrap
        self.addCleanup(ui.close)
        self.app.processEvents()
        self.assertIn(ui.cmb000, ui.cmb008._widget_items.values())
        buttons = sorted(
            b.text()
            for b in ui.cmb000.option_box.menu.findChildren(QtWidgets.QPushButton)
            if b.text()
        )
        self.assertIn("Open FBX Preset Directory", buttons)
        self.assertIn("Edit FBX Preset", buttons)
        self.assertFalse(ui.cmb008.actions)
        fbx = str(self.btk.SceneExporter._preset_store().user_dir).replace("\\", "/")
        templates = str(ui.presets.preset_dir).replace("\\", "/")
        self.assertTrue(fbx.endswith("blendertk/fbx_presets"), fbx)
        self.assertNotEqual(fbx, templates)

    def test_scene_exporter_preset_warnings_reach_the_panel_log(self):
        """The window PresetManager warns on its class-shared logger, which the
        panel's log redirect never wires, so the panel adopts it: loading a preset
        missing a covered key puts the schema-drift warning in txt003 (it was
        console-only)."""
        import json

        import pythontk as ptk

        ui, _slots = self._loaded("scene_exporter")
        ui.show()
        self.addCleanup(ui.close)
        self.app.processEvents()
        manager = ui.presets
        before = manager.preset_dir
        self.addCleanup(setattr, manager, "preset_dir", before)
        with ptk.TempArtifacts("tcl_se_presets", policy="scoped") as store:
            manager.preset_dir = store.dir_path()  # off the live store
            path = manager.save("stale_probe")
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            covered = [k for k in data if not k.startswith("_")]
            del data[covered[0]]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            ui.txt003.clear()
            manager.load("stale_probe")
            self.app.processEvents()
            log = ui.txt003.toPlainText()
        self.assertIn("doesn't cover", log)
        self.assertIn("Re-save the preset", log)


if __name__ == "__main__":
    unittest.main()
