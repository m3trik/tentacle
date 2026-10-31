#!/usr/bin/python
# coding=utf-8
"""The Bridge panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``.
"""

import os
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.bridge import BridgeSlots

#: The panel's defaults, as its .ui sets them.
_DEFAULTS = {
    "cmb000": 0,
    "s000": 0,
    "s001": 6.0,
    "s002": 0.0,
    "s003": 1.0,
    "s004": 0.0,
    "chk001": False,
}

#: What a host whose bridge is linear only names (as blendertk's ``Bridge`` does).
_LINEAR_ONLY = {
    name: f"No {name} here."
    for name in ("blend", "curve", "taper", "twist", "cleanup_curves")
}


def _panel(values=None, unsupported=None):
    """A Slots instance over a mock ui (*values* set on its widgets) and a mock
    toolkit whose ``Bridge`` cannot honor *unsupported*."""
    sb = mock.MagicMock()
    sb.tk.Bridge.UNSUPPORTED_OPTIONS = dict(unsupported or {})
    ui = sb.loaded_ui.bridge
    for name, value in (values or {}).items():
        widget = getattr(ui, name)
        widget.value.return_value = value
        widget.isChecked.return_value = value
        widget.currentIndex.return_value = value
    return BridgeSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestBridgePanel(_PanelCase):
    def test_previews_through_the_host_toolkit(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.bridge
        sb.tk.Preview.assert_called_once_with(
            slots,
            ui.chk000,
            ui.b000,
            message_func=sb.message_box,
            enable_on_show=True,
            undo_message="Bridge",
        )

    def test_the_preview_turns_on_as_the_panel_opens(self):
        """Asked of the Preview itself, which hooks the panel window's show in
        both hosts (one uitk controller), never patched on after it is built."""
        _slots, sb = _panel()
        self.assertIs(sb.tk.Preview.call_args.kwargs["enable_on_show"], True)

    def test_the_operation_reads_the_panel_into_the_host_engine(self):
        values = {
            "cmb000": 2,
            "s000": 3,
            "s001": 30.0,
            "s002": 1.0,
            "s003": 0.5,
            "s004": 15.0,
            "chk001": True,
        }
        slots, sb = _panel(values)
        # Maya's Preview passes a contract, Blender's none: both are accepted.
        slots.perform_operation(["brg.e[0:23]"], None)
        slots.perform_operation(["brg.e[0:23]"])
        sb.tk.Bridge.bridge.assert_called_with(
            ["brg.e[0:23]"],
            curve_type="curve",
            divisions=3,
            smoothing_angle=30.0,
            offset=1.0,
            taper=0.5,
            twist=15.0,
            cleanup_curves=True,
        )

    def test_each_type_item_names_its_curve_type(self):
        for index, curve_type in enumerate(("linear", "blend", "curve")):
            with self.subTest(index=index):
                slots, sb = _panel({**_DEFAULTS, "cmb000": index})
                slots.perform_operation(["brg.e[0]"])
                kwargs = sb.tk.Bridge.bridge.call_args.kwargs
                self.assertEqual(kwargs["curve_type"], curve_type)

    def test_an_unknown_type_index_bridges_linear(self):
        slots, sb = _panel({**_DEFAULTS, "cmb000": -1})
        slots.perform_operation(["brg.e[0]"])
        self.assertEqual(sb.tk.Bridge.bridge.call_args.kwargs["curve_type"], "linear")

    def test_a_host_that_honors_every_option_disables_nothing(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.bridge
        for name in ("s003", "s004", "chk001"):
            getattr(ui, name).setEnabled.assert_not_called()
        ui.cmb000.model.return_value.item.assert_not_called()

    def test_what_the_host_cannot_build_is_disabled_with_its_reason(self):
        slots, sb = _panel(unsupported=_LINEAR_ONLY)
        ui = sb.loaded_ui.bridge
        for option, name in BridgeSlots.OPTION_WIDGETS.items():
            widget = getattr(ui, name)
            widget.setEnabled.assert_called_once_with(False)
            widget.setToolTip.assert_called_once_with(_LINEAR_ONLY[option])
        model = ui.cmb000.model.return_value
        # Blend and Curve go; Linear stays selectable.
        self.assertEqual([c.args[0] for c in model.item.call_args_list], [1, 2])
        item = model.item.return_value
        self.assertEqual(item.setFlags.call_count, 2)
        self.assertEqual(
            [c.args[0] for c in item.setToolTip.call_args_list],
            [_LINEAR_ONLY["blend"], _LINEAR_ONLY["curve"]],
        )

    def test_the_options_disable_before_the_reset_buttons_wrap_them(self):
        """add_reset_buttons reparents the widgets; disabling after it would
        address the stale wrappers."""
        calls = []
        sb = mock.MagicMock()
        sb.tk.Bridge.UNSUPPORTED_OPTIONS = _LINEAR_ONLY
        sb.loaded_ui.bridge.s003.setEnabled.side_effect = lambda *a: calls.append(
            "disable"
        )
        sb.add_reset_buttons.side_effect = lambda *a: calls.append("reset")
        BridgeSlots(sb)
        self.assertEqual(calls, ["disable", "reset"])

    def test_preserves_geometry_for_the_preview(self):
        """polyBridgeEdge on a historyless mesh leaves an orig-shape the
        node-diff rollback deletes, baking the bridge in: without the snapshot
        the next refresh fails on a closed border (moved here from mayatk's
        test_edit_bridge with the panel)."""
        self.assertTrue(getattr(BridgeSlots, "PRESERVE_GEOMETRY", False))

    def test_the_type_combo_lists_the_curve_types_in_order(self):
        """The combo saves an index, so its item order is the curve-type order."""
        path = os.path.join(
            os.path.dirname(tentacle.__file__), "ui", "tools", "bridge.ui"
        )
        combo = next(
            w for w in ET.parse(path).iter("widget") if w.get("name") == "cmb000"
        )
        labels = [item.find("property/string").text for item in combo.findall("item")]
        self.assertEqual(
            [label.split()[-1].lower() for label in labels],
            list(BridgeSlots.CURVE_TYPES),
        )


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestBridgePanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)

    def _facing_loops(self):
        """Two open cylinders combined into one mesh, and its two facing border loops."""
        cmds = self.cmds
        parts = []
        for name, height in (("brgPanelA", 0), ("brgPanelB", 4)):
            cyl = cmds.polyCylinder(name=name, r=1, h=2, sx=12, sy=1, ch=False)[0]
            cmds.delete(f"{cyl}.f[12:]")  # both caps: two open border loops
            cmds.move(0, height, 0, cyl)
            parts.append(cyl)
        mesh = cmds.polyUnite(*parts, ch=False, mergeUVSets=True)[0]
        cmds.select(mesh, replace=True)
        cmds.polySelectConstraint(mode=3, type=0x8000, where=1)  # border edges
        border = cmds.ls(selection=True, flatten=True) or []
        cmds.polySelectConstraint(disable=True)
        cmds.select(clear=True)
        rows = {}
        for edge in border:
            verts = cmds.ls(
                cmds.polyListComponentConversion(edge, fromEdge=True, toVertex=True),
                flatten=True,
            )
            y = sum(cmds.pointPosition(v, world=True)[1] for v in verts) / len(verts)
            rows.setdefault(round(y, 2), []).append(edge)
        ys = sorted(rows)  # -1, +1, +3, +5: the facing pair is +1 and +3
        return mesh, rows[ys[1]] + rows[ys[2]]

    def test_bridges_the_facing_loops(self):
        mesh, loops = self._facing_loops()
        faces = self.cmds.polyEvaluate(mesh, face=True)
        slots, sb = _panel(_DEFAULTS)
        sb.tk = maya_module("mayatk")
        slots.perform_operation(loops, None)
        self.assertGreater(self.cmds.polyEvaluate(mesh, face=True), faces)

    def test_maya_builds_every_option(self):
        mtk = maya_module("mayatk")
        self.assertEqual(mtk.Bridge.UNSUPPORTED_OPTIONS, {})
        self.assertEqual(tuple(mtk.Bridge.CURVE_TYPES), BridgeSlots.CURVE_TYPES)


if __name__ == "__main__":
    unittest.main()
