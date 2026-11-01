# !/usr/bin/python
# coding=utf-8
"""Panel-wiring tests for the shared ``emissive_groups`` tool (``ui/tools/`` + ``slots/tools/``).

Maya-hosted, in a fresh GUI Maya (``run_tests.py --in-maya``): the panel hosts a
uitk ``TableWidget``, and Qt table classes hard-crash mayapy in batch. It loads
the way a bare host handler stands it up (``MayaUiHandler`` with tentacle's
shared roots), so its Slots class reaches Maya through ``Slots.tk``.

Where ``test_emissive_groups.py`` covers the tool, this covers what
the engine tests can't see: that the ``.ui`` parses and its uitk custom widgets
resolve, the ``tb000`` option box builds with its controls, the table
configures (columns / scrub / single-click edit) and re-wires its signals, and
every button path drives the engine end-to-end against a real scene.
"""

import os
import unittest

from _host import MAYA_AVAILABLE, maya_module, qt_widgets_available

cmds = maya_module("maya.cmds")
mtk = maya_module("mayatk")
EmissiveGroups = mtk.EmissiveGroups if mtk else None


@unittest.skipUnless(
    MAYA_AVAILABLE and qt_widgets_available(), "needs a GUI Maya (--in-maya)"
)
class _PanelCase(unittest.TestCase):
    """Load the panel once; each test gets a clean scene + registry."""

    @classmethod
    def setUpClass(cls):
        from mayatk.ui_utils.maya_ui_handler import MayaUiHandler
        from tentacle.tcl import Tcl

        handler = MayaUiHandler.instance()
        Tcl.register_shared(handler.sb)
        cls.ui = handler.get("emissive_groups")
        cls.slots = cls.ui.slots
        cls.sb = cls.slots.sb

    def setUp(self):
        cmds.file(new=True, force=True)  # drops the data nodes with the scene
        self.cube = cmds.polyCube(name="eg_panel_cube")[0]
        self.slots._refresh_table()

    def _add(self, name, face):
        cmds.select(f"{self.cube}.f[{face}]", replace=True)
        self.ui.txt000.setText(name)
        self.slots.b000()


class TestPanelSurface(_PanelCase):
    """The .ui parses and every widget the slots address exists."""

    def test_the_panel_drives_the_tool_in_this_host(self):
        self.assertEqual(
            type(self.slots).__module__,
            "tentacle.slots.tools.emissive_groups",
        )
        self.assertIs(self.slots.tk, mtk)
        self.assertIs(self.slots.engine, EmissiveGroups)

    def test_widgets_resolve(self):
        for name in (
            "header",
            "txt000",
            "b000",
            "b001",
            "b002",
            "b003",
            "tb000",
            "tbl000",
            "footer",
        ):
            self.assertIsNotNone(getattr(self.ui, name, None), name)

    def test_table_is_uitk_tablewidget(self):
        self.assertEqual(type(self.ui.tbl000).__name__, "TableWidget")

    def test_table_columns(self):
        table = self.ui.tbl000
        self.assertEqual(table.columnCount(), 4)
        self.assertEqual(
            [table.horizontalHeaderItem(i).text() for i in range(4)],
            list(self.slots.COLUMNS),
        )

    def test_weight_column_is_scrub_and_click_editable(self):
        table = self.ui.tbl000
        col = self.slots.WEIGHT_COL
        self.assertIn(col, table._scrub_columns)
        self.assertIn(col, table._single_click_edit_columns)

    def test_option_box_controls(self):
        """Shape and ranges only — NOT the factory values.

        uitk persists widget state to QSettings, so a spinbox carries
        whatever the last session (or an earlier test) left in it; asserting
        the authored default here fails depending on run order and history.
        """
        menu = self.ui.tb000.option_box.menu
        for name in ("cmb000", "s000", "s001", "chk000"):
            self.assertTrue(hasattr(menu, name), name)
        # A uitk class name here silently yields a QLabel — pin the real type.
        self.assertIsInstance(menu.cmb000, self.sb.QtWidgets.QComboBox)
        self.assertEqual(
            [menu.cmb000.itemText(i) for i in range(menu.cmb000.count())],
            ["Vertex Color", "Mask Texture"],
        )
        self.assertEqual((menu.s000.minimum(), menu.s000.maximum()), (64, 8192))
        self.assertEqual((menu.s001.minimum(), menu.s001.maximum()), (0, 64))
        self.assertIsInstance(menu.chk000, self.sb.QtWidgets.QCheckBox)

    def test_menu_items_have_slot_methods(self):
        """Every menu entry dispatches by objectName to a slot method."""
        for name in ("compact_slots", "republish_export"):
            self.assertTrue(hasattr(self.ui.header.menu, name), name)
            self.assertTrue(callable(getattr(self.slots, name, None)), name)
        for name in (
            "select_members",
            "remove_group",
            "weights_all_on",
            "weights_all_off",
            "make_weights_keyable",
            "key_weights",
            "remove_keyable_weights",
        ):
            self.assertTrue(hasattr(self.ui.tbl000.menu, name), name)
            self.assertTrue(callable(getattr(self.slots, name, None)), name)


class TestPanelWorkflow(_PanelCase):
    """Buttons drive the engine and the table reflects scene state."""

    def test_add_populates_row(self):
        self._add("headlights", 0)
        table = self.ui.tbl000
        self.assertEqual(table.rowCount(), 1)
        self.assertEqual(
            [table.item(0, c).text() for c in range(4)],
            ["headlights", "0", "1", "1"],
        )
        self.assertEqual(self.ui.txt000.text(), "")  # field cleared

    def test_add_without_name_autonames(self):
        cmds.select(f"{self.cube}.f[0]", replace=True)
        self.ui.txt000.clear()
        self.slots.b000()
        self.assertEqual(self.ui.tbl000.item(0, 0).text(), "group_0")

    def test_rows_are_slot_ordered(self):
        self._add("a", 0)
        self._add("b", 1)
        table = self.ui.tbl000
        self.assertEqual([table.item(r, 1).text() for r in range(2)], ["0", "1"])

    def test_weight_cell_edit_writes_through(self):
        self._add("headlights", 0)
        self.ui.tbl000.item(0, self.slots.WEIGHT_COL).setText("0.25")
        self.assertEqual(EmissiveGroups.list_groups()["headlights"]["default"], 0.25)

    def test_unparseable_weight_reverts(self):
        self._add("headlights", 0)
        self.ui.tbl000.item(0, self.slots.WEIGHT_COL).setText("bogus")
        self.assertEqual(EmissiveGroups.list_groups()["headlights"]["default"], 1.0)
        self.assertEqual(self.ui.tbl000.item(0, self.slots.WEIGHT_COL).text(), "1")

    def test_scrub_previews_then_commits_on_release(self):
        """Moves only repaint the cell; the scene write happens once, on release."""
        self._add("headlights", 0)
        col = self.slots.WEIGHT_COL
        # Scrub DOWN from the 1.0 default — scrubbing up would clamp and
        # prove nothing.
        self.slots._on_scrub_started(0, col)
        self.slots._on_scrub_moved(0, col, -self.slots.SCRUB_PX_PER_UNIT / 2, 0)
        # Cell previews the new value...
        self.assertEqual(self.ui.tbl000.item(0, col).text(), "0.5")
        # ...but nothing is committed until release.
        self.assertEqual(EmissiveGroups.list_groups()["headlights"]["default"], 1.0)
        self.slots._on_scrub_finished(0, col)
        self.assertAlmostEqual(
            EmissiveGroups.list_groups()["headlights"]["default"], 0.5, places=5
        )

    def test_scrub_clamps(self):
        self._add("headlights", 0)
        col = self.slots.WEIGHT_COL
        for dx, expected in ((10000, 1.0), (-10000, 0.0)):
            self.slots._on_scrub_started(0, col)
            self.slots._on_scrub_moved(0, col, dx, 0)
            self.slots._on_scrub_finished(0, col)
            self.assertEqual(
                EmissiveGroups.list_groups()["headlights"]["default"], expected
            )

    def test_scrub_without_movement_is_a_noop(self):
        """Click-through on the scrub column must not rewrite the weight."""
        self._add("headlights", 0)
        col = self.slots.WEIGHT_COL
        self.slots._on_scrub_started(0, col)
        self.slots._on_scrub_finished(0, col)
        self.assertEqual(EmissiveGroups.list_groups()["headlights"]["default"], 1.0)

    def test_weights_all_on_off(self):
        self._add("a", 0)
        self._add("b", 1)
        self.slots.weights_all_off()
        self.assertTrue(
            all(g["default"] == 0.0 for g in EmissiveGroups.list_groups().values())
        )
        self.slots.weights_all_on()
        self.assertTrue(
            all(g["default"] == 1.0 for g in EmissiveGroups.list_groups().values())
        )

    def test_select_members(self):
        self._add("headlights", 0)
        self.ui.tbl000.setCurrentCell(0, 0)
        self.slots.b002()
        self.assertEqual(cmds.ls(sl=True), [f"{self.cube}.f[0]"])

    def test_remove_group_updates_table(self):
        self._add("a", 0)
        self._add("b", 1)
        self.ui.tbl000.setCurrentCell(0, 0)
        self.slots.b001()
        self.assertEqual(self.ui.tbl000.rowCount(), 1)
        self.assertNotIn("a", EmissiveGroups.list_groups())

    def test_bake_vertex_colors_via_option_box(self):
        self._add("headlights", 0)
        menu = self.ui.tb000.option_box.menu
        menu.cmb000.setCurrentIndex(0)
        self.slots.tb000(self.ui.tb000)
        self.assertIn(
            "emissiveGroups",
            cmds.polyColorSet(self.cube, q=True, allColorSets=True) or [],
        )

    def test_bake_mask_via_option_box(self):
        import pythontk as ptk
        from mayatk.node_utils.data_nodes import DataNodes

        self._add("headlights", 0)
        menu = self.ui.tb000.option_box.menu
        menu.cmb000.setCurrentIndex(1)
        menu.s000.setValue(64)
        self.slots.tb000(self.ui.tb000)
        payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
        self.assertEqual(payload["encoding"], "channels")
        self.assertNotIn("resolution", payload)  # the mask states its own size
        # The button names no path, so the mask lands in the current project's
        # sourceimages -- which must be the run's sandbox, never the project the
        # user last had open (a GUI-pass Maya restores it from prefs: measured,
        # `untitled_EMask.png` of exactly this fixture in a production project).
        from pythontk.core_utils.test_sandbox import TestSandbox

        if TestSandbox.is_active():
            root = os.path.normcase(
                os.path.realpath(cmds.workspace(q=True, rootDirectory=True))
            )
            sandbox = os.path.normcase(os.path.realpath(TestSandbox.temp()))
            self.assertTrue(
                root.startswith(sandbox), f"wrote into a real project: {root}"
            )

    def test_table_signal_rewire_survives_a_new_slots_instance(self):
        """The QWidget outlives the slots instance; a re-init must rebind.

        Qt connects to a *bound method* without keeping the instance alive,
        so a table left wired to a dropped slots object goes inert — which
        is why ``tbl000_init`` re-wires unconditionally on every show. The
        fresh instance is kept referenced for the test's lifetime and the
        panel's own wiring is restored on cleanup, so this can't leave the
        shared table bound to a dead receiver for later tests.
        """
        self._add("headlights", 0)
        self.addCleanup(self.slots.tbl000_init, self.ui.tbl000)
        self._fresh = type(self.slots)(self.slots.sb)
        self._fresh.tbl000_init(self.ui.tbl000)
        self.ui.tbl000.item(0, self.slots.WEIGHT_COL).setText("0.5")
        self.assertEqual(EmissiveGroups.list_groups()["headlights"]["default"], 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
