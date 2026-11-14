#!/usr/bin/python
# coding=utf-8
"""The Shell Xform panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: that each arrow moves the axis and sign it names by the
scope's step, that each snap mode resolves to the offset it claims, and that
every button hands the host's ``UvUtils`` the arguments its options say. A
swapped ``b024``/``b025`` or an inverted snap passes every engine test and still
ships a broken panel. Plain pytest, no DCC, no widgets loaded. In Maya, the
same class drives the real ``mtk``.
"""

import os
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace as NS
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.shell_xform import ShellXformSlots

#: The tile border the panel keeps clear (its _border_margin).
MARGIN = ptk.MathUtils.uv_tile_margin(ShellXformSlots._MAP_SIZE)

SELECTION = ["plane"]


def _panel(selection=SELECTION, bounds=(0.0, 0.0, 1.0, 1.0), neighbors=()):
    """A Slots instance over a mock ui and a mock toolkit whose selection, UV
    bounds and neighbouring shells are *selection*, *bounds* and *neighbors*."""
    sb = mock.MagicMock()
    sb.tk.CoreUtils.selected_objects.return_value = list(selection)
    sb.tk.UvUtils.get_uv_bounds.return_value = bounds
    sb.tk.UvUtils.get_neighbor_shell_bounds.return_value = list(neighbors)
    return ShellXformSlots(sb), sb


def _scope(slots, scope, snap=ShellXformSlots._SNAP_OFF):
    """Stand in for the panel's ``cmb_move_scope`` + its option-box snap button.

    The step is looked up in the real ``_MOVE_SCOPES`` table (the one
    ``cmb_move_scope_init`` populates the combo from), so a scope renamed there
    fails these tests loudly instead of silently testing a stale label.
    """
    slots.ui.cmb_move_scope.currentData.return_value = ShellXformSlots._MOVE_SCOPES[
        scope
    ]
    slots._snap_action = NS(current_state=snap)


def _offset(sb):
    """The ``(u, v)`` offset the last move asked of the host."""
    args = sb.tk.UvUtils.move_to_uv_space.call_args.args
    return args[1], args[2]


def _options(**values):
    """A button whose option-box menu widgets read *values* (checked / value / text)."""
    widget = mock.MagicMock()
    for name, value in values.items():
        control = getattr(widget.option_box.menu, name)
        control.isChecked.return_value = value
        control.value.return_value = value
        control.currentText.return_value = value
    return widget


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestShellXformMovePad(_PanelCase):
    """The four move-to-UV-space arrows, across every scope and snap state."""

    def test_arrows_move_the_axis_and_sign_they_name(self):
        for button, expected in (
            ("b023", (-1.0, 0.0)),  # left
            ("b024", (0.0, -1.0)),  # down
            ("b025", (0.0, 1.0)),  # up
            ("b026", (1.0, 0.0)),  # right
        ):
            with self.subTest(button=button):
                slots, sb = _panel()
                _scope(slots, "Tile")
                getattr(slots, button)()
                sb.tk.UvUtils.move_to_uv_space.assert_called_once_with(
                    SELECTION, *expected
                )

    def test_scope_sets_the_step(self):
        for scope, step in (("Tile", 1.0), ("Half Tile", 0.5), ("Quarter Tile", 0.25)):
            with self.subTest(scope=scope):
                slots, sb = _panel()
                _scope(slots, scope)
                slots.b025()
                self.assertEqual(_offset(sb), (0.0, step))

    def test_selection_bounds_scope_steps_by_the_selections_own_size(self):
        slots, sb = _panel(bounds=(0.2, 0.5, 0.6, 0.9))  # a 0.4 x 0.4 box
        _scope(slots, "Selection Bounds")
        slots.b026()
        du, dv = _offset(sb)
        self.assertAlmostEqual(du, 0.4, places=9)
        self.assertEqual(dv, 0.0)

    def test_a_collapsed_axis_steps_a_whole_tile(self):
        slots, sb = _panel(bounds=(0.2, 0.5, 0.2, 0.9))  # zero width
        _scope(slots, "Selection Bounds")
        slots.b026()
        self.assertEqual(_offset(sb)[0], 1.0)

    def test_snap_lands_an_off_grid_shell_on_the_padded_grid(self):
        """A shell sitting in one half of a UDIM steps to the next half line,
        rather than carrying its sub-tile drift along. It lands one border
        margin *inside* the line: a shell flush against a tile seam bleeds
        across it at render time."""
        slots, sb = _panel(bounds=(0.0, 0.6, 1.0, 1.6))
        _scope(slots, "Half Tile", snap=ShellXformSlots._SNAP_GRID)
        slots.b025()
        self.assertAlmostEqual(0.6 + _offset(sb)[1], 1.0 + MARGIN, places=9)

    def test_snap_is_reversible_from_a_padded_position(self):
        """Padding the *result* rather than the anchor would strand the reverse
        press on the margin it had just added, and the arrow would read as dead."""
        v_min = 1.0 + MARGIN
        slots, sb = _panel(bounds=(0.0, v_min, 1.0, v_min + 1.0))
        _scope(slots, "Half Tile", snap=ShellXformSlots._SNAP_GRID)
        slots.b024()
        self.assertAlmostEqual(v_min + _offset(sb)[1], 0.5 + MARGIN, places=9)

    def test_snap_off_preserves_sub_tile_drift(self):
        slots, sb = _panel(bounds=(0.0, 0.6, 1.0, 1.6))
        _scope(slots, "Half Tile")
        slots.b025()
        self.assertEqual(_offset(sb), (0.0, 0.5))
        sb.tk.UvUtils.get_neighbor_shell_bounds.assert_not_called()

    def test_shell_snap_parks_against_the_neighbor(self):
        slots, sb = _panel(neighbors=[(0.0, 3.0, 1.0, 4.0)])
        _scope(slots, "Tile", snap=ShellXformSlots._SNAP_SHELL)
        slots.b025()
        sb.tk.UvUtils.get_neighbor_shell_bounds.assert_called_once_with(SELECTION)
        # Its top edge lands one margin under the neighbour's bottom.
        self.assertAlmostEqual(1.0 + _offset(sb)[1], 3.0 - MARGIN, places=9)

    def test_shell_snap_ignores_the_scope(self):
        """The neighbour sets the distance, so every scope lands identically."""
        landings = set()
        for scope in ShellXformSlots._MOVE_SCOPES:
            slots, sb = _panel(neighbors=[(0.0, 3.0, 1.0, 4.0)])
            _scope(slots, scope, snap=ShellXformSlots._SNAP_SHELL)
            slots.b025()
            landings.add(round(_offset(sb)[1], 9))
        self.assertEqual(len(landings), 1, landings)

    def test_shell_snap_falls_back_to_the_grid_with_no_neighbor(self):
        """Nothing ahead must still move the shell: a dead arrow reads as a bug."""
        slots, sb = _panel(bounds=(0.0, 0.6, 1.0, 1.6))
        _scope(slots, "Half Tile", snap=ShellXformSlots._SNAP_SHELL)
        slots.b025()
        self.assertAlmostEqual(0.6 + _offset(sb)[1], 1.0 + MARGIN, places=9)

    def test_shell_snap_ignores_a_neighbor_out_of_the_lane(self):
        slots, sb = _panel(
            bounds=(0.0, 0.6, 1.0, 1.6), neighbors=[(3.0, 3.0, 4.0, 4.0)]
        )
        _scope(slots, "Half Tile", snap=ShellXformSlots._SNAP_SHELL)
        slots.b025()
        self.assertAlmostEqual(0.6 + _offset(sb)[1], 1.0 + MARGIN, places=9)

    def test_shell_snap_walks_past_a_parked_neighbor(self):
        parked = 3.0 - MARGIN  # the top edge, one margin under the neighbour
        slots, sb = _panel(
            bounds=(0.0, parked - 1.0, 1.0, parked), neighbors=[(0.0, 3.0, 1.0, 4.0)]
        )
        _scope(slots, "Tile", snap=ShellXformSlots._SNAP_SHELL)
        slots.b025()  # clears it rather than sitting still
        self.assertAlmostEqual(parked - 1.0 + _offset(sb)[1], 4.0 + MARGIN, places=9)

    def test_an_empty_selection_warns_and_moves_nothing(self):
        slots, sb = _panel(selection=())
        _scope(slots, "Tile")
        slots.b025()
        sb.message_box.assert_called_once()
        sb.tk.UvUtils.move_to_uv_space.assert_not_called()

    def test_a_selection_without_uvs_warns_and_moves_nothing(self):
        slots, sb = _panel(bounds=None)
        _scope(slots, "Tile")
        slots.b025()
        self.assertIn("No UVs", sb.message_box.call_args.args[0])
        sb.tk.UvUtils.move_to_uv_space.assert_not_called()

    def test_scope_table_shape(self):
        """The combo is built from this table, so it is the panel's item list.

        Exactly one scope carries the ``None`` sentinel (derive from selection);
        a second would make ``_move_step`` read bounds for a fixed-step scope.
        """
        scopes = ShellXformSlots._MOVE_SCOPES
        self.assertEqual(
            list(scopes), ["Tile", "Half Tile", "Quarter Tile", "Selection Bounds"]
        )
        self.assertEqual(
            [k for k, v in scopes.items() if v is None], ["Selection Bounds"]
        )
        self.assertTrue(all(v > 0 for v in scopes.values() if v is not None))

    def test_the_ui_ships_no_static_scope_items(self):
        """``cmb_move_scope_init`` is the combo's single source: a static item in
        the .ui would carry no step data, and its arrow would derive the step
        from the selection instead."""
        path = os.path.join(
            os.path.dirname(tentacle.__file__), "ui", "tools", "shell_xform.ui"
        )
        combo = next(
            w
            for w in ET.parse(path).iter("widget")
            if w.get("name") == "cmb_move_scope"
        )
        self.assertEqual(combo.findall("item"), [])

    def test_scope_init_builds_the_items_and_the_snap_button(self):
        slots, sb = _panel()
        combo = mock.MagicMock(is_initialized=False)
        slots.cmb_move_scope_init(combo)
        combo.add.assert_called_once_with(ShellXformSlots._MOVE_SCOPES)
        kwargs = combo.option_box.set_action.call_args.kwargs
        self.assertEqual(kwargs["settings_key"], "shell_xform_move_snap_mode")
        self.assertEqual(kwargs["states"], slots._snap_states())
        self.assertIs(slots._snap_action, combo.option_box.set_action.return_value)

        initialized = mock.MagicMock(is_initialized=True)
        slots.cmb_move_scope_init(initialized)
        initialized.add.assert_not_called()

    def test_snap_mode_defaults_off_when_unset(self):
        """A slots instance that never ran ``cmb_move_scope_init`` must not crash."""
        slots, sb = _panel()
        self.assertEqual(slots._snap_mode(), ShellXformSlots._SNAP_OFF)

    def test_snap_states_match_the_mode_constants(self):
        """The cycle index IS the mode, so the states must be in ``_SNAP_*``
        order, each tinted, no two sharing a tint, and shell snap its own icon."""
        slots, sb = _panel()
        states = slots._snap_states()
        self.assertEqual(
            (
                ShellXformSlots._SNAP_OFF,
                ShellXformSlots._SNAP_GRID,
                ShellXformSlots._SNAP_SHELL,
            ),
            (0, 1, 2),
        )
        self.assertEqual(len(states), 3)
        colors = [s["color"] for s in states]
        self.assertTrue(all(colors))
        self.assertEqual(len(set(colors)), 3)
        self.assertNotEqual(
            states[ShellXformSlots._SNAP_SHELL]["icon"],
            states[ShellXformSlots._SNAP_GRID]["icon"],
        )
        self.assertTrue(all(s["tooltip"] for s in states))


class TestShellXformOps(_PanelCase):
    """Every other button: what it asks of the host's ``UvUtils``."""

    def test_gather_to_tile_uses_the_panels_map_size(self):
        for moved, message in ((2, None), (0, "Nothing to gather"), (None, "No UVs")):
            with self.subTest(moved=moved):
                slots, sb = _panel()
                sb.tk.UvUtils.gather_to_udim.return_value = moved
                slots.gather_to_udim()
                sb.tk.UvUtils.gather_to_udim.assert_called_once_with(
                    SELECTION, map_size=ShellXformSlots._MAP_SIZE
                )
                if message is None:
                    sb.message_box.assert_not_called()
                else:
                    self.assertIn(message, sb.message_box.call_args.args[0])

    def test_flip_mirrors_each_shell_about_its_own_center(self):
        for button, axis in (("b034", "u"), ("b035", "v")):
            with self.subTest(button=button):
                slots, sb = _panel()
                getattr(slots, button)()
                sb.tk.UvUtils.mirror_uvs.assert_called_once_with(
                    SELECTION, axis=axis, per_shell=True, preserve_position=False
                )

    def test_rotate_turns_by_the_angle_field(self):
        slots, sb = _panel()
        slots.ui.s041.value.return_value = 15
        slots.b036()  # counter-clockwise
        sb.tk.UvUtils.rotate_uvs.assert_called_with(SELECTION, 15)
        slots.b037()  # clockwise
        sb.tk.UvUtils.rotate_uvs.assert_called_with(SELECTION, -15)
        sb.message_box.assert_not_called()

        sb.tk.UvUtils.rotate_uvs.return_value = 0
        slots.b036()
        self.assertIn("No UVs", sb.message_box.call_args.args[0])

    def test_straighten_reads_its_option_box_in_one_undo_step(self):
        slots, sb = _panel()
        widget = _options(chk018=True, chk019=False, s001=45, chk020=True)
        slots.tb005(widget)
        uv = sb.tk.UvUtils
        uv.straighten_uvs.assert_called_once_with(SELECTION, u=True, v=False, angle=45)
        uv.straighten_uv_shells.assert_called_once_with(SELECTION)
        sb.tk.CoreUtils.undo_chunk.assert_called_once_with("Straighten UVs")
        sb.tk.CoreUtils.undo_chunk.return_value.__enter__.assert_called_once()
        sb.message_box.assert_not_called()

    def test_straighten_shell_runs_only_when_ticked(self):
        slots, sb = _panel()
        sb.tk.UvUtils.straighten_uvs.return_value = 0
        slots.tb005(_options(chk018=True, chk019=True, s001=30, chk020=False))
        sb.tk.UvUtils.straighten_uv_shells.assert_not_called()
        self.assertIn("Nothing straightened", sb.message_box.call_args.args[0])

    def test_distribute_leaves_the_panels_tile_spacing_between_shells(self):
        """A hardcoded 0 butts every shell against its neighbour: the row bleeds
        across its own seams. The gap is the same margin Snap and Gather use."""
        for u, axis in ((True, "u"), (False, "v")):
            with self.subTest(axis=axis):
                slots, sb = _panel()
                slots.tb006(_options(chk023=u, chk024=not u))
                sb.tk.UvUtils.distribute_uv_shells.assert_called_once_with(
                    SELECTION, axis=axis, spacing=MARGIN
                )

    def test_distribute_follows_the_panels_spacing_rather_than_a_constant(self):
        slots, sb = _panel()
        slots._border_margin = lambda: 0.05
        slots.tb006(_options(chk023=True, chk024=False))
        self.assertEqual(
            sb.tk.UvUtils.distribute_uv_shells.call_args.kwargs["spacing"], 0.05
        )

    def test_mirror_reads_its_option_box(self):
        slots, sb = _panel()
        slots.tb008(
            _options(
                chk031=False,
                chk032=True,
                chk033=False,
                cmb_mirror_mode="Geometric Mirror",
            )
        )
        sb.tk.UvUtils.mirror_uvs.assert_called_once_with(
            SELECTION, axis="v", per_shell=False, preserve_position=False
        )
        slots, sb = _panel()
        slots.tb008(
            _options(
                chk031=True,
                chk032=False,
                chk033=True,
                cmb_mirror_mode="Preserve Footprint",
            )
        )
        sb.tk.UvUtils.mirror_uvs.assert_called_once_with(
            SELECTION, axis="u", per_shell=True, preserve_position=True
        )

    def test_each_align_button_runs_its_axis_and_mode(self):
        """A mislabeled ``align_v_min`` would move U, which the engine test can't catch."""
        for button, axis, mode in (
            ("align_u_min", "u", "min"),
            ("align_u_avg", "u", "avg"),
            ("align_u_max", "u", "max"),
            ("align_v_min", "v", "min"),
            ("align_v_avg", "v", "avg"),
            ("align_v_max", "v", "max"),
            ("linear_align", "u", "linear"),
        ):
            with self.subTest(button=button):
                slots, sb = _panel()
                getattr(slots, button)()
                sb.tk.UvUtils.align_uvs.assert_called_once_with(
                    SELECTION, axis=axis, mode=mode
                )
                sb.message_box.assert_not_called()

    def test_orient_shells_and_to_edges(self):
        slots, sb = _panel()
        slots.orient_shells()
        sb.tk.UvUtils.orient_shells.assert_called_once_with(SELECTION)
        slots.orient_edges()
        sb.tk.UvUtils.orient_shells.assert_called_with(SELECTION, to_edge=True)
        sb.message_box.assert_not_called()

        sb.tk.UvUtils.orient_shells.return_value = 0  # no edge in the selection
        slots.orient_edges()
        self.assertIn("No edge selected", sb.message_box.call_args.args[0])

    def test_randomize_advances_the_seed_per_click(self):
        """Each click re-shuffles rather than re-applying one offset."""
        slots, sb = _panel()
        for _ in range(3):
            slots.randomize_shells()
        self.assertEqual(
            [
                c.kwargs["seed"]
                for c in sb.tk.UvUtils.randomize_uv_shells.call_args_list
            ],
            [0, 1, 2],
        )

    def test_a_tool_that_finds_nothing_to_do_says_so(self):
        for button, engine in (
            ("align_u_min", "align_uvs"),
            ("gather_shells", "gather_uv_shells"),
            ("randomize_shells", "randomize_uv_shells"),
            ("orient_shells", "orient_shells"),
        ):
            with self.subTest(button=button):
                slots, sb = _panel()
                getattr(sb.tk.UvUtils, engine).return_value = 0
                getattr(slots, button)()
                self.assertIn("Nothing", sb.message_box.call_args.args[0])

    def test_nothing_selected_runs_nothing(self):
        buttons = {
            "gather_to_udim": "gather_to_udim",
            "b034": "mirror_uvs",
            "b036": "rotate_uvs",
            "align_u_min": "align_uvs",
            "orient_shells": "orient_shells",
            "orient_edges": "orient_shells",
            "gather_shells": "gather_uv_shells",
            "randomize_shells": "randomize_uv_shells",
        }
        for button, engine in buttons.items():
            with self.subTest(button=button):
                slots, sb = _panel(selection=())
                getattr(slots, button)()
                getattr(sb.tk.UvUtils, engine).assert_not_called()
                sb.message_box.assert_called_once()
        for button, engine in (
            ("tb005", "straighten_uvs"),
            ("tb006", "distribute_uv_shells"),
            ("tb008", "mirror_uvs"),
        ):
            with self.subTest(button=button):
                slots, sb = _panel(selection=())
                getattr(slots, button)(_options())
                getattr(sb.tk.UvUtils, engine).assert_not_called()

    def test_open_uv_editor_through_the_host(self):
        slots, sb = _panel()
        slots.open_uv_editor()
        sb.tk.UiUtils.open_editor.assert_called_once_with("UV Editor")
        sb.message_box.assert_not_called()

        sb.tk.UiUtils.open_editor.return_value = None
        slots.open_uv_editor()
        self.assertIn("Could not open", sb.message_box.call_args.args[0])

    def test_the_arrow_icons_install_on_the_next_tick(self):
        """The switchboard wires the child widgets after ``__init__``."""
        slots, sb = _panel()
        sb.QtCore.QTimer.singleShot.assert_called_once_with(0, slots._initialize_ui)
        slots._initialize_ui()
        installed = [c.args[1] for c in sb.IconManager.set_icon.call_args_list]
        self.assertEqual(
            sorted(installed), sorted(ShellXformSlots._MOVE_ICONS.values())
        )


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestShellXformPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        sb = mock.MagicMock()
        self.slots = ShellXformSlots(sb)
        sb.tk = self.mtk
        self.sb = sb

    def plane(self, u=0.0, v=0.0, select=True):
        """A 0-1 UV plane, optionally nudged off the origin (and selected)."""
        plane = self.cmds.polyPlane(width=1, height=1, sx=1, sy=1)[0]
        if u or v:
            self.mtk.UvUtils.move_to_uv_space(plane, u, v)
        if select:
            self.cmds.select(plane)
        return plane

    def bounds(self, node):
        return self.mtk.UvUtils.get_uv_bounds(node)

    def test_opposite_arrows_cancel(self):
        plane = self.plane()
        before = self.bounds(plane)
        _scope(self.slots, "Half Tile")
        self.slots.b023()
        self.slots.b026()
        self.slots.b024()
        self.slots.b025()
        for a, b in zip(self.bounds(plane), before):
            self.assertAlmostEqual(a, b, places=5)

    def test_snap_lands_an_off_grid_shell_on_the_padded_grid(self):
        plane = self.plane(v=0.6)  # V 0.6 .. 1.6
        _scope(self.slots, "Half Tile", snap=ShellXformSlots._SNAP_GRID)
        self.slots.b025()
        self.assertAlmostEqual(self.bounds(plane)[1], 1.0 + MARGIN, places=5)
        self.slots.b024()
        self.assertAlmostEqual(self.bounds(plane)[1], 0.5 + MARGIN, places=5)

    def test_shell_snap_parks_against_the_neighbor(self):
        neighbor = self.plane(v=3.0, select=False)  # V 3.0 .. 4.0
        plane = self.plane()
        _scope(self.slots, "Tile", snap=ShellXformSlots._SNAP_SHELL)
        self.slots.b025()
        self.assertAlmostEqual(self.bounds(plane)[3], 3.0 - MARGIN, places=5)
        self.assertAlmostEqual(self.bounds(neighbor)[1], 3.0, places=5)

    def test_gather_pulls_a_stray_into_the_majority_tile(self):
        residents = [self.plane(select=False), self.plane(select=False)]
        stray = self.plane(u=3.0, v=2.0, select=False)
        self.cmds.select(residents + [stray])
        self.slots.gather_to_udim()
        u_min, v_min, _, _ = self.bounds(stray)
        self.assertAlmostEqual(u_min, 0.0, places=5)
        self.assertAlmostEqual(v_min, 0.0, places=5)

    def test_distribute_leaves_the_tile_margin_between_shells(self):
        planes = [self.plane(u=i * 3.0, select=False) for i in range(3)]
        self.cmds.select([f"{p}.f[*]" for p in planes], replace=True)
        self.slots.tb006(_options(chk023=True, chk024=False))
        spans = sorted((b[0], b[2]) for b in (self.bounds(p) for p in planes))
        gaps = [spans[i + 1][0] - spans[i][1] for i in range(len(spans) - 1)]
        self.assertEqual(len(gaps), 2)
        for gap in gaps:
            self.assertAlmostEqual(gap, MARGIN, places=6)

    def test_rotate_turns_and_turns_back(self):
        plane = self.plane()
        corner = f"{plane}.map[0]"
        start = self.cmds.polyEditUV(corner, query=True)
        self.slots.ui.s041.value.return_value = 90
        self.slots.b036()
        self.assertNotAlmostEqual(
            sum(
                abs(a - b)
                for a, b in zip(self.cmds.polyEditUV(corner, query=True), start)
            ),
            0.0,
            places=3,
        )
        self.slots.b037()
        for a, b in zip(self.cmds.polyEditUV(corner, query=True), start):
            self.assertAlmostEqual(a, b, places=5)

    def test_flip_keeps_the_shells_box(self):
        plane = self.plane(u=0.25)
        before = self.bounds(plane)
        self.slots.b034()
        for a, b in zip(self.bounds(plane), before):
            self.assertAlmostEqual(a, b, places=5)

    def test_align_u_min_lines_the_uvs_up_on_the_minimum(self):
        plane = self.plane(u=0.2)  # U 0.2 .. 1.2
        self.slots.align_u_min()
        u_min, v_min, u_max, v_max = self.bounds(plane)
        self.assertAlmostEqual(u_min, 0.2, places=5)
        self.assertAlmostEqual(u_max, 0.2, places=5)
        self.assertAlmostEqual(v_max - v_min, 1.0, places=5)  # V untouched

    def test_an_empty_selection_warns_instead_of_raising(self):
        self.cmds.select(clear=True)
        self.slots.b025()
        self.sb.message_box.assert_called_once()


if __name__ == "__main__":
    unittest.main()
