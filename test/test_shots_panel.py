#!/usr/bin/python
# coding=utf-8
"""The Shots panel's one Slots class (and its controller), shared by both hosts.

It reaches its host only through ``self.tk`` -- the host library's
``ShotSequencer`` and that class's ``STORE_CLASS`` -- so a fake toolkit stands
in for ``mtk`` / ``btk`` here, over pythontk's pure ``ShotStore``, and records
what the panel asks of the engine: plain unittest, no DCC. The ``.ui`` is read
as XML. Over ``btk`` the panel loads through a real (offscreen) Qt /
Switchboard / ``BlenderUiHandler`` stack (no bpy: the store's scene hooks stand
in for the file); in Maya it drives the real ``mtk`` -- a bare controller in any
Maya, the loaded panel in a GUI Maya. The engine's own behavior is the
libraries' (``test_sequencer.py`` / ``test_shot_sequencer.py``), the panel's
words pythontk's (``test_shot_report.py``).
"""

import ast
import contextlib
import inspect
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pythontk as ptk
from pythontk import (
    ActiveShotChanged,
    BatchComplete,
    SettingsChanged,
    ShotBlock,
    ShotBoundaryConflict,
    ShotDefined,
    ShotRemoved,
    ShotsEdited,
    ShotUpdated,
)
from qtpy import QtWidgets

import tentacle
from _host import MAYA_AVAILABLE, maya_module, qt_widgets_available
from tentacle.slots._slots import Slots
from tentacle.slots.tools import shots as shots_module
from tentacle.slots.tools._shots.controller import ShotsController
from tentacle.slots.tools.shots import ShotsSlots

PKG = Path(tentacle.__file__).resolve().parent
MONO = PKG.parents[1]
UI_PATH = PKG / "ui" / "tools" / "shots.ui"
SLOTS_PATH = PKG / "slots" / "tools" / "shots.py"
CONTROLLER_PATH = PKG / "slots" / "tools" / "_shots" / "controller.py"

#: Every button the panel's groups and option boxes own. Pressing each one is
#: the cheapest guard against a slot that cannot reach what it reads.
BUTTONS = (
    "btn_apply_gap",
    "btn_shift_all",
    "btn_trim_all",
    "btn_trim_all_leading",
    "btn_trim_all_trailing",
    "btn_trim_all_both",
    "btn_move_shot",
    "btn_swap_shot",
    "btn_trim_empty",
    "btn_trim_leading",
    "btn_trim_trailing",
    "btn_trim_both",
    "btn_add_leading_space",
    "btn_add_trailing_space",
    "btn_delete_shots",
)


class _Store(ptk.ShotStore):
    """The pure model as a host's store class: no scene, no persistence."""


def _fake_tk(store_cls=_Store):
    """A toolkit double: its ``ShotSequencer`` is a mock class (an instance
    records the engine calls) whose ``STORE_CLASS`` is *store_cls*."""
    tk = mock.MagicMock()
    tk.ShotSequencer.STORE_CLASS = store_cls
    tk.ShotSequencer.SWAP_FIELDS = ptk.ShotSequencer.SWAP_FIELDS
    return tk


def _bare(tk=None, store=None, **values):
    """A controller built without its ``__init__`` (no widget wired): its host
    is *tk* (a fake by default), its active store *store* (else the store
    class's), its ui a mock whose named widgets hold *values*. What it puts in
    the footer collects in ``_said``."""
    ctrl = ShotsController.__new__(ShotsController)
    ctrl.sb = mock.MagicMock()
    ctrl.ui = mock.MagicMock()
    ctrl.tk = tk if tk is not None else _fake_tk()
    ctrl.logger = mock.MagicMock()
    ctrl._refreshing_editor = False
    ctrl._said = []
    ctrl._set_footer = ctrl._said.append
    if store is not None:
        ctrl._active_store = lambda: store
    for name, value in values.items():
        widget = getattr(ctrl.ui, name)
        widget.value.return_value = value
        widget.isChecked.return_value = value
        widget.currentData.return_value = value
    return ctrl


def _store(*bounds):
    """A pure store with a shot per ``(name, start, end)``, the first active."""
    store = _Store()
    for name, start, end in bounds:
        store.define_shot(name, start, end)
    if store.shots:
        store.set_active_shot(store.sorted_shots()[0].shot_id)
    return store


@contextlib.contextmanager
def _answer(button, asked=None):
    """Answer every question with *button*, keeping its text in *asked*.
    Patched with a function, never a bare MagicMock: a QObject subclass faults
    natively on a mock attribute (uitk/CLAUDE.md)."""

    def question(*args, **kwargs):
        if asked is not None:
            asked.append(args[2])
        return button

    with mock.patch.object(
        QtWidgets.QMessageBox, "question", new=staticmethod(question)
    ):
        yield


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


def _slots():
    """A ``ShotsSlots`` over a mock switchboard and a fake toolkit, its
    controller a mock: ``(slots, sb, the controller class)``."""
    sb = mock.MagicMock()
    sb.tk = _fake_tk()
    with mock.patch.object(shots_module, "ShotsController") as controller_cls:
        slots = ShotsSlots(sb)
    return slots, sb, controller_cls


# ---------------------------------------------------------------------- the .ui


class TestShotsUi(_PanelCase):
    """The ``.ui`` is the libraries' (mayatk's and blendertk's twins were
    identical): its saved names, its combos' order and its labels hold."""

    @classmethod
    def setUpClass(cls):
        root = ET.parse(UI_PATH).getroot()
        cls.widgets = {w.get("name"): w for w in root.iter("widget")}

    def _items(self, name):
        return [
            item.find("./property[@name='text']/string").text
            for item in self.widgets[name].findall("item")
        ]

    def _text(self, name):
        return self.widgets[name].find("./property[@name='text']/string").text

    def test_the_saved_names_hold(self):
        for name in (
            "shots",
            "header",
            "footer",
            "detection",
            "build",
            "shot_editor",
            "all_shots",
            "cmb_detection_mode",
            "spn_detection",
            "spn_initial_length",
            "chk_snap_whole_frames",
            "cmb_fit_mode",
            "cmb_shot_select",
            "txt_shot_name",
            "spn_shot_start",
            "spn_shot_end",
            "txt_shot_desc",
            "spn_move_to",
            "btn_swap_shot",
            "spn_space",
            "btn_trim_empty",
            "b000",
            "btn_apply_gap",
            "btn_shift_all",
            "btn_trim_all",
            "btn_delete_shots",
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.widgets)

    def test_the_combos_keep_the_engines_order(self):
        """A combo saves an index, and the controller maps it onto the store's
        modes by position."""
        self.assertEqual(
            self._items("cmb_detection_mode"),
            ["Auto-Detect", "All Keys", "Skip Zero-Value", "Zero = Shot End"],
        )
        self.assertEqual(
            ptk.ShotStore.DETECTION_MODES, ("auto", "all", "skip_zero", "zero_as_end")
        )
        self.assertEqual(
            self._items("cmb_fit_mode"), ["Extend Only", "Shrink & Extend to Fit"]
        )
        self.assertEqual(ptk.ShotStore.FIT_MODES, ("extend_only", "fit_contents"))

    def test_no_runtime_row_is_declared_by_the_ui(self):
        self.assertEqual(set(ShotsSlots.RUNTIME_WIDGETS) & set(self.widgets), set())

    def test_the_help_names_each_button_by_its_label_for_either_host(self):
        slots, sb, _cls = _slots()
        slots.header_init(mock.MagicMock())
        sections = sb.tooltip.fmt.call_args.kwargs["sections"]
        text = " ".join(line for _title, lines in sections for line in lines)
        for name in (
            "btn_swap_shot",
            "btn_trim_empty",
            "b000",
            "btn_apply_gap",
            "btn_shift_all",
            "btn_trim_all",
        ):
            with self.subTest(button=name):
                self.assertIn(f"<b>{self._text(name)}</b>", text)
        for host in ("Maya", "Blender"):
            self.assertNotIn(host, text)


# ---------------------------------------------------------------------- the slots


class TestShotsSlotsRouting(_PanelCase):
    """Each widget reaches its controller call."""

    def test_the_panel_is_the_shots_ui_and_its_controller(self):
        slots, sb, controller_cls = _slots()
        self.assertIs(slots.ui, sb.loaded_ui.shots)
        self.assertIs(slots.tk, sb.tk)
        controller_cls.assert_called_once_with(slots)
        self.assertIs(slots.controller, controller_cls.return_value)

    def test_each_widget_reaches_its_controller_call(self):
        slots, _sb, _cls = _slots()
        ctrl = slots.controller
        cases = (
            (lambda: slots.spn_detection(3.0), ctrl.on_detection_changed, (3.0,)),
            (lambda: slots.cmb_detection_mode(2), ctrl.on_detection_mode_changed, (2,)),
            (lambda: slots.spn_initial_length(50.0), ctrl.on_initial_length_changed, (50.0,)),
            (lambda: slots.cmb_fit_mode(1), ctrl.on_fit_mode_changed, (1,)),
            (lambda: slots.chk_snap_whole_frames(True), ctrl.on_snap_whole_frames_changed, (True,)),
            (lambda: slots.cmb_shot_select(4), ctrl.on_shot_selected, (4,)),
            (lambda: slots.spn_shot_start(10.0), ctrl.on_shot_start_changed, (10.0,)),
            (lambda: slots.spn_shot_end(90.0), ctrl.on_shot_end_changed, (90.0,)),
            (lambda: slots.chk_drop_stale_shots(True), ctrl.on_drop_stale_shots_changed, (True,)),
            (slots.b000, ctrl.on_delete_shot, ()),
            (slots.btn_move_shot, ctrl.on_move_shot, ()),
            (slots.btn_swap_shot, ctrl.on_swap_shot, ()),
            (slots.btn_trim_empty, ctrl.on_trim_empty, ("both",)),
            (slots.btn_trim_leading, ctrl.on_trim_empty, ("leading",)),
            (slots.btn_trim_trailing, ctrl.on_trim_empty, ("trailing",)),
            (slots.btn_trim_both, ctrl.on_trim_empty, ("both",)),
            (slots.btn_trim_all, ctrl.on_trim_all_shots, ("both",)),
            (slots.btn_trim_all_leading, ctrl.on_trim_all_shots, ("leading",)),
            (slots.btn_trim_all_trailing, ctrl.on_trim_all_shots, ("trailing",)),
            (slots.btn_trim_all_both, ctrl.on_trim_all_shots, ("both",)),
            (slots.btn_add_leading_space, ctrl.on_add_space, ("leading",)),
            (slots.btn_add_trailing_space, ctrl.on_add_space, ("trailing",)),
        )
        for i, (press, call, args) in enumerate(cases):
            with self.subTest(case=i):
                call.reset_mock()
                press()
                call.assert_called_once_with(*args)

    def test_the_text_fields_push_their_own_text(self):
        """The switchboard debounces them: the field's text, not the signal's."""
        slots, sb, _cls = _slots()
        ui = sb.loaded_ui.shots
        ui.txt_shot_name.text.return_value = "Intro"
        ui.txt_shot_desc.text.return_value = "notes"
        slots.txt_shot_name("stale")
        slots.txt_shot_desc()
        slots.controller.on_shot_name_changed.assert_called_once_with("Intro")
        slots.controller.on_shot_desc_changed.assert_called_once_with("notes")

    def test_a_picked_option_relabels_its_button(self):
        slots, _sb, _cls = _slots()
        slots.cmb_delete_scope(1)
        slots.controller.label_delete_shots.assert_called_once_with()
        slots.cmb_swap_with(0)
        slots.cmb_swap_mode(1)
        self.assertEqual(slots.controller.label_swap_shot.call_count, 2)

    def test_delete_shots_takes_the_picked_scope(self):
        slots, _sb, _cls = _slots()
        slots.controller.delete_scope.return_value = "empty"
        slots.btn_delete_shots()
        slots.controller.on_delete_shots.assert_called_once_with("empty")

    def test_apply_gap_reads_its_option_box(self):
        """The amount, the scope, and Override Locked Gaps arriving as
        ``respect_locks``, inverted."""
        slots, sb, _cls = _slots()
        ui, ctrl = sb.loaded_ui.shots, slots.controller
        ui.spn_gap.value.return_value = 12.0
        ui.cmb_gap_scope.currentData.return_value = "start"
        for override in (True, False):
            ctrl._option_checked.return_value = override
            slots.btn_apply_gap()
            ctrl.on_gap_changed.assert_called_with(
                12.0, scope="start", respect_locks=not override
            )
        ctrl._option_checked.assert_called_with("chk_override_locks", False)

    def test_shift_to_reads_its_frame(self):
        slots, sb, _cls = _slots()
        sb.loaded_ui.shots.spn_shift_all.value.return_value = 24
        slots.btn_shift_all()
        slots.controller.on_shift_all_shots.assert_called_once_with(24.0)


# ---------------------------------------------------------------------- the host seams


class TestTheHostSeams(unittest.TestCase):
    """The store and the engine are the host's, reached through ``self.tk``."""

    def test_the_engine_is_the_hosts_sequencer_and_the_store_its_store_class(self):
        tk = _fake_tk()
        ctrl = _bare(tk)
        self.assertIs(ctrl._sequencer_cls(), tk.ShotSequencer)
        self.assertIs(ctrl._store_cls(), _Store)

    def test_the_active_store_is_the_store_classs_or_none(self):
        store_cls = mock.MagicMock()
        ctrl = _bare(_fake_tk(store_cls))
        self.assertIs(ctrl._active_store(), store_cls.active.return_value)
        store_cls.active.side_effect = RuntimeError("no scene")
        self.assertIsNone(ctrl._active_store())

    def test_the_modes_map_by_the_engines_order(self):
        ctrl = _bare()
        self.assertEqual(ctrl._mode_to_index("skip_zero"), 2)
        self.assertEqual(ctrl._mode_to_index("unknown"), 0)
        self.assertEqual(ctrl._index_to_mode(3), "zero_as_end")
        self.assertEqual(ctrl._index_to_mode(9), "auto")

    def test_neither_module_imports_a_host(self):
        """No host library, host API or uitk import: the host is ``self.tk``,
        uitk the switchboard."""
        banned = {"mayatk", "blendertk", "maya", "bpy", "uitk"}
        for path in (SLOTS_PATH, CONTROLLER_PATH):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    with self.subTest(module=path.name, name=name):
                        self.assertNotIn(name.split(".")[0], banned)


class TestTheLabels(unittest.TestCase):
    def test_a_shots_row_names_it_and_its_range(self):
        shot = ShotBlock(1, "Intro", 1, 100)
        self.assertEqual(ShotsController.shot_label(shot), "Intro  [1–100]")

    def test_a_shots_row_is_found_by_its_id(self):
        cmb = mock.MagicMock()
        cmb.count.return_value = 3
        cmb.itemData.side_effect = [4, 7, 9]
        self.assertEqual(ShotsController._shot_row(cmb, 7), 1)
        cmb.itemData.side_effect = [4, 7, 9]
        self.assertEqual(ShotsController._shot_row(cmb, 8), -1)

    def test_the_delete_scopes_are_shotreports(self):
        """The picker's rows and the button's word are pythontk's, the words
        the Shot Sequencer's shot list uses too."""
        ctrl = _bare(cmb_delete_scope="empty")
        self.assertEqual(ctrl.delete_scope(), "empty")
        ctrl.label_delete_shots()
        ctrl.ui.btn_delete_shots.setText.assert_called_once_with("Delete Empty Shots")
        self.assertEqual(_bare(cmb_delete_scope=None).delete_scope(), "stale")


# ---------------------------------------------------------------------- the edits


class TestEditsAskTheEngine(unittest.TestCase):
    """Each edit asks the host's ``ShotSequencer``, built over the active
    store, for one engine call inside one ``scene_edit``."""

    def setUp(self):
        self.store = _store(("A", 0, 20), ("B", 30, 50), ("C", 60, 80))
        self.a, self.b, self.c = self.store.sorted_shots()
        self.tk = _fake_tk()
        self.seq = self.tk.ShotSequencer.return_value
        self.seq.sorted_shots.return_value = self.store.sorted_shots()

    def _ctrl(self, **values):
        return _bare(self.tk, self.store, **values)

    def test_apply_gap_respaces_with_the_options(self):
        self._ctrl().on_gap_changed(12, scope="start", respect_locks=False)
        self.tk.ShotSequencer.assert_called_with(store=self.store)
        self.seq.apply_gap.assert_called_once_with(
            12.0, scope="start", shot_id=self.a.shot_id, respect_locks=False
        )
        self.assertEqual(self.store.gap, 12.0)

    def test_a_refused_gap_puts_the_setting_back_and_says_why(self):
        self.store.gap = 5.0
        self.seq.apply_gap.side_effect = ShotBoundaryConflict([])
        ctrl = self._ctrl()
        ctrl.on_gap_changed(12)
        self.assertEqual(self.store.gap, 5.0, "the panel shows what the scene is")
        self.assertTrue(ctrl._said, "the refusal reaches the footer")

    def test_the_start_field_moves_the_shot(self):
        self._ctrl().on_shot_start_changed(5.0)
        self.seq.move_shot.assert_called_once_with(self.a.shot_id, 5.0)

    def test_an_unchanged_start_asks_nothing(self):
        self._ctrl().on_shot_start_changed(0.0)
        self.seq.move_shot.assert_not_called()

    def test_the_end_field_moves_the_bound_and_ripples_the_rest(self):
        self._ctrl().on_shot_end_changed(25.0)
        self.assertEqual(self.store.shot_by_id(self.a.shot_id).end, 25.0)
        self.seq.ripple_downstream.assert_called_once_with(self.a.shot_id, 20.0, 5.0)

    def test_a_field_set_by_a_sync_asks_nothing(self):
        ctrl = self._ctrl()
        ctrl._refreshing_editor = True
        ctrl.on_shot_start_changed(5.0)
        ctrl.on_shot_end_changed(25.0)
        self.seq.move_shot.assert_not_called()
        self.seq.ripple_downstream.assert_not_called()

    def test_move_to_reorders_the_active_shot(self):
        self._ctrl(spn_move_to=3).on_move_shot()
        self.seq.move_shot_to_position.assert_called_once_with(self.a.shot_id, 3)

    def test_swap_with_trades_places_keeping_the_checked_fields(self):
        values = {"cmb_swap_mode": "swap", "cmb_swap_with": self.c.shot_id}
        for field in ptk.ShotSequencer.SWAP_FIELDS:
            values[f"chk_swap_retain_{field}"] = field in ("name", "locked")
        ctrl = self._ctrl(**values)
        ctrl.on_swap_shot()
        self.seq.swap_shots.assert_called_once_with(
            self.a.shot_id, self.c.shot_id, retain=["name", "locked"]
        )
        self.assertIn("Swapped A and C", ctrl._said[-1])

    def test_copy_over_copies_the_animation_onto_the_picked_shot(self):
        ctrl = self._ctrl(cmb_swap_mode="copy", cmb_swap_with=self.b.shot_id)
        ctrl.on_swap_shot()
        self.seq.copy_shot_content.assert_called_once_with(
            self.a.shot_id, self.b.shot_id
        )
        self.seq.swap_shots.assert_not_called()

    def test_trim_asks_for_one_edge_of_the_active_shot(self):
        self.seq.trim_shot_to_content.return_value = (2.0, 0.0)
        ctrl = self._ctrl()
        ctrl.on_trim_empty("leading")
        self.seq.trim_shot_to_content.assert_called_once_with(
            self.a.shot_id, edge="leading"
        )
        self.assertEqual(ctrl._said[-1], "Trimmed: 2f head, 0f tail")

    def test_a_trim_that_moved_nothing_leaves_no_restore_point(self):
        """A dead restore point would make the next undo visibly do nothing."""
        self.seq.trim_shot_to_content.return_value = (0.0, 0.0)
        ctrl = self._ctrl()
        ctrl.on_trim_empty("both")
        self.assertFalse(self.store.has_boundary_snapshot())
        self.assertEqual(ctrl._said[-1], "Trimmed: nothing to do")

    def test_trim_all_trims_every_shot_at_the_edge(self):
        self.seq.trim_shot_to_content.return_value = (1.0, 0.0)
        self._ctrl().on_trim_all_shots("trailing")
        calls = self.seq.trim_shot_to_content.call_args_list
        self.assertEqual(
            sorted(c.args[0] for c in calls),
            sorted(s.shot_id for s in (self.a, self.b, self.c)),
        )
        self.assertTrue(all(c.kwargs == {"edge": "trailing"} for c in calls))

    def test_shift_to_moves_the_first_shot_and_the_rest_ride(self):
        ctrl = self._ctrl()
        ctrl.on_shift_all_shots(100)
        self.seq.move_shot.assert_called_once_with(self.a.shot_id, 100.0)
        self.assertEqual(ctrl._said[-1], "Shifted all shots by +100f")

    def test_shift_to_where_the_first_shot_starts_asks_nothing(self):
        ctrl = self._ctrl()
        ctrl.on_shift_all_shots(0)
        self.seq.move_shot.assert_not_called()
        self.assertEqual(ctrl._said[-1], "All shots already start at 0")

    def test_add_space_pads_one_edge_by_the_frames_set(self):
        self.seq.add_shot_space.return_value = (0.0, 10.0)
        self._ctrl(spn_space=10).on_add_space("trailing")
        self.seq.add_shot_space.assert_called_once_with(
            self.a.shot_id, 10.0, edge="trailing"
        )

    def test_no_frames_set_adds_nothing(self):
        ctrl = self._ctrl(spn_space=0)
        ctrl.on_add_space("leading")
        self.seq.add_shot_space.assert_not_called()
        self.assertIn("set a frame count", ctrl._said[-1])

    def test_new_shot_appends_one_and_makes_it_active(self):
        made = ShotBlock(7, "Shot_4", 90, 290)

        def new_shot():
            self.store.shots.append(made)
            return made

        self.seq.new_shot.side_effect = new_shot
        ctrl = self._ctrl()
        ctrl.on_new_shot()
        self.assertEqual(self.store.active_shot_id, 7)
        self.assertEqual(ctrl._said[-1], "Created Shot_4 · 90–290")

    def test_delete_asks_then_cuts_with_the_armed_options(self):
        self.seq.delete_shot.return_value = {"name": "A", "curves_cut": 3, "closed": 0}
        ctrl = self._ctrl(chk_delete_contents=True, chk_close_gap=False)
        asked = []
        with _answer(QtWidgets.QMessageBox.Yes, asked):
            ctrl.on_delete_shot()
        self.assertIn('"A" [0–20]', asked[0])
        self.assertIn("its keyframes, leaving the space", asked[0])
        self.seq.delete_shot.assert_called_once_with(
            self.a.shot_id, delete_contents=True, close_gap=False
        )
        self.assertEqual(ctrl._said[-1], "Deleted A · 3 curve(s) cleared")

    def test_a_declined_delete_asks_nothing_of_the_engine(self):
        with _answer(QtWidgets.QMessageBox.Cancel):
            self._ctrl().on_delete_shot()
        self.seq.delete_shot.assert_not_called()

    def test_delete_shots_asks_shotreports_question_and_drops_the_records(self):
        expected = ptk.ShotReport.removal_question([self.a, self.b, self.c], "all")
        ctrl = self._ctrl()
        asked = []
        with _answer(QtWidgets.QMessageBox.Yes, asked):
            ctrl.on_delete_shots("all")
        self.assertEqual(asked, [expected[1]])
        self.assertEqual(self.store.shots, [])
        self.assertEqual(ctrl._said[-1], "Deleted 3 shot(s)")

    def test_delete_shots_with_none_in_scope_says_so(self):
        """The pure store holds every member: nothing is stale."""
        ctrl = self._ctrl()
        asked = []
        with _answer(QtWidgets.QMessageBox.Yes, asked):
            ctrl.on_delete_shots("stale")
        self.assertEqual((asked, len(self.store.shots)), ([], 3))
        self.assertEqual(ctrl._said[-1], "No stale shots")


# ---------------------------------------------------------------------- refusals


class _GuardStore:
    """What ``_boundary_edit`` reaches on a store, counting restore points."""

    def __init__(self):
        self.pushed = 0
        self.discarded = 0

    def push_boundary_snapshot(self, *args, **kwargs):
        self.pushed += 1

    def discard_boundary_snapshot(self, *args, **kwargs):
        self.discarded += 1

    @contextlib.contextmanager
    def scene_edit(self, label="edit", snapshot=True):
        # The real bracket's contract: the restore point is pushed on entry.
        if snapshot:
            self.push_boundary_snapshot()
        yield


def _refuse():
    raise ShotBoundaryConflict([])


class TestBoundaryEditRefusesInsteadOfCrashing(unittest.TestCase):
    """A refused boundary edit is an answer, not a crash.

    ``_reconcile_boundaries`` raises :class:`ShotBoundaryConflict` when two
    shots would have to share a sample whose two poses disagree, and every
    boundary-mutating edit can reach it.
    """

    def test_a_refusal_does_not_propagate(self):
        self.assertFalse(_bare()._boundary_edit(_GuardStore(), "reorder", _refuse))

    def test_a_refusal_keeps_the_restore_point_its_step_pairs_with(self):
        """A refused edit can have written first (a "both" Add Space slides
        the head before the tail ripple refuses), and ``scene_edit`` pushed
        its undo step and tagged this point to it: undoing the step must put
        the bounds back with the keys. mayatk's twin discarded it here."""
        store = _GuardStore()
        _bare()._boundary_edit(store, "reorder", _refuse)
        self.assertEqual((store.pushed, store.discarded), (1, 0))

    def test_a_refusal_is_reported_to_the_user(self):
        ctrl = _bare()
        ctrl._boundary_edit(_GuardStore(), "reorder", _refuse)
        self.assertTrue(ctrl._said, "a refusal must reach the footer")
        ctrl.logger.warning.assert_called_once()

    def test_a_successful_edit_runs_and_keeps_its_restore_point(self):
        store, calls = _GuardStore(), []
        self.assertTrue(_bare()._boundary_edit(store, "gap", calls.append, "ran"))
        self.assertEqual(calls, ["ran"], "args must reach the callable")
        self.assertEqual((store.pushed, store.discarded), (1, 0))

    def test_an_unrelated_error_still_propagates(self):
        def _boom():
            raise ValueError("unrelated")

        with self.assertRaises(ValueError):
            _bare()._boundary_edit(_GuardStore(), "gap", _boom)


def _refusing_engine_calls():
    """Public ``ShotSequencer`` methods whose call graph reaches the refusal.

    DERIVED from pythontk's orchestration and each host's engine on disk (one
    class hierarchy: a name defined in several contributes every body), never
    listed: a stale list stops covering the newest way to be refused.
    """
    paths = [Path(inspect.getsourcefile(ptk.ShotSequencer))]
    for pkg in ("mayatk", "blendertk"):
        engine = (
            MONO / pkg / pkg / "anim_utils" / "shots" / "shot_sequencer" / "_shot_sequencer.py"
        )
        if engine.is_file():
            paths.append(engine)
    graph = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for fn in cls.body:
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    graph.setdefault(fn.name, set()).update(
                        c.func.attr
                        for c in ast.walk(fn)
                        if isinstance(c, ast.Call)
                        and isinstance(c.func, ast.Attribute)
                        and isinstance(c.func.value, ast.Name)
                        and c.func.value.id == "self"
                    )
    reach, changed = {"_reconcile_boundaries"}, True
    while changed:
        changed = False
        for name, calls in graph.items():
            if name not in reach and calls & reach:
                reach.add(name)
                changed = True
    return {n for n in reach if not n.startswith("_")}


class TestEveryRefusableEditUsesTheGuard(unittest.TestCase):
    """A source check over the controller: what regressed before was CALL
    SITES each bracketing an edit by hand (ten in blendertk's twin, three in
    mayatk's)."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(CONTROLLER_PATH.read_text(encoding="utf-8"))
        cls.refusing = _refusing_engine_calls()

    def _methods(self):
        for cls in [n for n in ast.walk(self.tree) if isinstance(n, ast.ClassDef)]:
            for fn in cls.body:
                if isinstance(fn, ast.FunctionDef) and fn.name != "_boundary_edit":
                    yield fn

    def test_the_refusing_set_resolves(self):
        self.assertLessEqual(
            {"apply_gap", "move_shot", "trim_shot_to_content", "swap_shots"},
            self.refusing,
        )

    def test_every_method_calling_a_refusing_engine_call_uses_the_guard(self):
        offenders = []
        for fn in self._methods():
            calls = {
                c.func.attr
                for c in ast.walk(fn)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            }
            hit = calls & self.refusing
            if hit and "_boundary_edit" not in calls:
                offenders.append(f"{fn.name} (line {fn.lineno}) calls {sorted(hit)}")
        self.assertEqual(offenders, [], "these edits escape _boundary_edit")

    def test_no_method_pushes_a_restore_point_by_hand(self):
        offenders = [
            f"{fn.name} (line {call.lineno})"
            for fn in self._methods()
            for call in ast.walk(fn)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "push_boundary_snapshot"
        ]
        self.assertEqual(offenders, [])


# ---------------------------------------------------------------------- following the store


class TestStoreEvents(unittest.TestCase):
    """The panel follows the store.

    Bug: ShotRemoved only called _populate_shot_combobox + _sync_footer, never
    re-syncing the detection widgets: deleting the last shot left them
    disabled. ShotDefined was unhandled entirely.
    Fixed: 2026-04-07
    """

    def setUp(self):
        self.ctrl = _bare(store=_store())
        for name in (
            "_sync_from_store",
            "_sync_shot_editor",
            "_sync_footer",
            "_relabel_shot_row",
        ):
            setattr(self.ctrl, name, mock.MagicMock())

    def test_a_structural_event_resyncs_the_whole_panel(self):
        shot = ShotBlock(1, "A01", 1, 30)
        for event in (
            ShotDefined(shot=shot),
            ShotRemoved(shot_id=1),
            BatchComplete(),
            SettingsChanged(),
            # A Shot Sequencer trim or drag writes the bounds directly; its
            # scene_edit announcement is all this panel hears of it.
            ShotsEdited(label="trim"),
        ):
            with self.subTest(event=type(event).__name__):
                self.ctrl._sync_from_store.reset_mock()
                self.ctrl._on_store_event(event)
                self.ctrl._sync_from_store.assert_called_once_with()

    def test_a_shot_update_relabels_its_row_only(self):
        shot = ShotBlock(1, "A01", 1, 30)
        self.ctrl._on_store_event(ShotUpdated(shot=shot))
        self.ctrl._sync_from_store.assert_not_called()
        self.ctrl._sync_shot_editor.assert_called_once_with()
        self.ctrl._relabel_shot_row.assert_called_once_with(shot)

    def test_a_pick_elsewhere_syncs_the_editor(self):
        self.ctrl._on_store_event(ActiveShotChanged(shot_id=1))
        self.ctrl._sync_from_store.assert_not_called()
        self.ctrl._relabel_shot_row.assert_not_called()
        self.ctrl._sync_shot_editor.assert_called_once_with()


class TestRefreshState(unittest.TestCase):
    """``refresh_state`` decides every widget's enabled state in one place
    (the Shot Manifest calls it after a Build)."""

    def _refresh(self, store, animated=True):
        ctrl = _bare(store=store)
        with mock.patch.object(_Store, "has_animation", return_value=animated):
            ctrl.refresh_state()
        return ctrl.ui

    def test_no_shots_and_animation_offers_detection(self):
        ui = self._refresh(_store())
        ui.cmb_detection_mode.setEnabled.assert_called_with(True)
        ui.spn_detection.setEnabled.assert_called_with(True)
        for name in ("btn_apply_gap", "btn_shift_all", "btn_trim_all", "btn_delete_shots"):
            getattr(ui, name).setEnabled.assert_called_with(False)

    def test_shots_close_detection_and_open_all_shots(self):
        ui = self._refresh(_store(("S01", 0, 100)))
        ui.cmb_detection_mode.setEnabled.assert_called_with(False)
        ui.spn_detection.setEnabled.assert_called_with(False)
        for name in ("btn_apply_gap", "btn_shift_all", "btn_trim_all", "btn_delete_shots"):
            getattr(ui, name).setEnabled.assert_called_with(True)
        ui.btn_delete_shots.setText.assert_called_with("Delete Stale Shots")

    def test_auto_detect_with_no_animation_disables_min_gap(self):
        ui = self._refresh(_store(), animated=False)
        ui.cmb_detection_mode.setEnabled.assert_called_with(True)
        ui.spn_detection.setEnabled.assert_called_with(False)

    def test_zero_as_end_never_reads_min_gap(self):
        store = _store()
        store.detection_mode = "zero_as_end"
        ui = self._refresh(store)
        ui.spn_detection.setEnabled.assert_called_with(False)


# ---------------------------------------------------------------------- the loaded panel


class _LoadedPanelCases:
    """Cases for the panel loaded through a host's real handler: ``self.ui``,
    ``self.slots`` and ``self._store()`` come from the host's class."""

    def _three_shots(self):
        store = self._store()
        store.shots = [
            ShotBlock(1, "A", 0, 20, []),
            ShotBlock(2, "B", 30, 50, []),
            ShotBlock(3, "C", 60, 80, []),
        ]
        store.set_active_shot(1)
        self.slots.controller._sync_from_store()
        return store

    def _rows(self):
        cmb = self.ui.cmb_shot_select
        return [(cmb.itemData(i), cmb.itemText(i)) for i in range(cmb.count())]

    def _clear(self, store):
        store.set_active_shot(None)
        store.shots = []

    def test_the_tool_binds_tentacles_slots(self):
        self.assertIsInstance(self.slots, ShotsSlots)
        self.assertEqual(type(self.slots.controller).__name__, "ShotsController")
        self.assertIs(
            self.slots.controller._store_cls(), self.slots.tk.ShotSequencer.STORE_CLASS
        )

    def test_the_ui_carries_every_widget_the_slots_reach_for(self):
        missing = [
            name
            for name in ("header", "footer", *BUTTONS, *ShotsSlots.RUNTIME_WIDGETS)
            if getattr(self.ui, name, None) is None
        ]
        self.assertEqual(missing, [])

    def test_store_owned_settings_never_restore_from_qsettings(self):
        """Bug: the detection threshold and mode also persisted in per-user
        QSettings, and the panel restores them AFTER its store sync -- through
        the slot that writes the store -- so opening the panel replaced this
        scene's settings with the last ones set in any scene.
        Fixed: 2026-10-03
        """
        for name in (
            "spn_detection",
            "cmb_detection_mode",
            "spn_initial_length",
            "cmb_fit_mode",
            "chk_snap_whole_frames",
            "spn_gap",
            "spn_shift_all",
            "cmb_swap_with",
            "chk_drop_stale_shots",
        ):
            with self.subTest(name=name):
                self.assertFalse(getattr(self.ui, name).restore_state)

    def test_every_button_survives_being_pressed(self):
        """An empty store, so this is about each slot's own attribute access:
        a helper reached through the wrong object raises only when pressed."""
        self._store().shots = []
        for name in BUTTONS:
            slot = getattr(self.slots, name, None)
            self.assertIsNotNone(slot, f"{name} has no slot method")
            with self.subTest(button=name):
                slot()

    def test_the_scope_and_gap_pickers_offer_every_scope(self):
        cmb = self.ui.cmb_delete_scope
        self.assertEqual(
            [cmb.itemData(i) for i in range(cmb.count())], ["stale", "empty", "all"]
        )
        cmb = self.ui.cmb_gap_scope
        self.assertEqual(
            [cmb.itemData(i) for i in range(cmb.count())],
            ["all", "start", "end", "start_end"],
        )

    def test_shift_to_is_a_button_naming_the_frame_in_its_option_box(self):
        """2026-10-10: "shift to should be a pushbutton in the same style as
        gap and delete buttons" -- Apply Gap's shape."""
        btn = self.ui.btn_shift_all
        self.assertIsInstance(btn, QtWidgets.QPushButton)
        self.assertTrue(self.ui.all_shots.isAncestorOf(btn))
        self.assertTrue(btn.option_box.menu.isAncestorOf(self.ui.spn_shift_all))
        self.assertAlmostEqual(self.ui.spn_shift_all.value(), 0.0)
        try:
            self.ui.spn_shift_all.setValue(24)
            self.assertEqual(btn.text(), "Shift To: 24")
        finally:
            self.ui.spn_shift_all.setValue(0)
        self.assertEqual(btn.text(), "Shift To: 0")

    def test_the_gap_amount_lives_in_apply_gaps_option_box(self):
        """Apply Gap is the group's button; the amount is one of its options
        (2026-10-07), named on the button and owned by the store."""
        btn = self.ui.btn_apply_gap
        self.assertIsInstance(btn, QtWidgets.QPushButton)
        self.assertTrue(btn.option_box.menu.isAncestorOf(self.ui.spn_gap))
        self.assertTrue(btn.option_box.menu.isAncestorOf(self.ui.cmb_gap_scope))
        self.assertFalse(self.ui.chk_override_locks.isChecked(), "locks honoured")
        store = self._store()
        store.shots = [ShotBlock(1, "A", 0, 20, []), ShotBlock(2, "B", 32, 50, [])]
        old_gap = store.gap
        try:
            store.gap = 12.0
            self.slots.controller._sync_from_store()
            self.assertEqual(self.ui.spn_gap.value(), 12)
            self.assertEqual(btn.text(), "Apply Gap: 12")
            self.ui.spn_gap.setValue(5)
            self.assertEqual(btn.text(), "Apply Gap: 5")
        finally:
            store.gap = old_gap
            store.shots = []

    def test_override_locked_gaps_reaches_the_controller(self):
        """The checkbox has to arrive as ``respect_locks``, inverted."""
        seen = {}
        ctrl = self.slots.controller
        real = ctrl.on_gap_changed
        ctrl.on_gap_changed = lambda v, **kw: seen.update(kw)
        try:
            self.ui.chk_override_locks.setChecked(True)
            self.slots.btn_apply_gap()
            self.assertIs(seen.get("respect_locks"), False, seen)
            self.ui.chk_override_locks.setChecked(False)
            self.slots.btn_apply_gap()
            self.assertIs(seen.get("respect_locks"), True, seen)
        finally:
            ctrl.on_gap_changed = real
            self.ui.chk_override_locks.setChecked(False)

    def test_leave_stale_shots_out_is_the_files_own_setting(self):
        """Delete Shots' option box holds Leave Stale Shots Out of Exports
        (``ShotStore.drop_stale_shots``): off unless the file says so,
        toggling it writes the store, and the store's value is what it shows."""
        ctrl = self.slots.controller
        store = ctrl._active_store()
        chk = self.ui.chk_drop_stale_shots
        self.assertFalse(chk.isChecked(), "off unless the file says so")
        try:
            chk.setChecked(True)
            self.assertTrue(store.drop_stale_shots)
            for value in (False, True):
                store.drop_stale_shots = value
                ctrl._sync_from_store()
                self.assertEqual(chk.isChecked(), value)
        finally:
            store.drop_stale_shots = False
            ctrl._sync_from_store()

    def test_the_dropdown_follows_a_shot_picked_elsewhere(self):
        """2026-10-10: "the shots combobox doesn't update properly and is often
        missing shots during editing". A pick in the Shot Sequencer relabelled
        the row the dropdown still showed with the active shot: C was listed
        twice and A was gone."""
        store = self._three_shots()
        try:
            store.set_active_shot(3)  # the Sequencer's pick
            self.assertEqual(
                self._rows(),
                [(1, "A  [0–20]"), (2, "B  [30–50]"), (3, "C  [60–80]")],
            )
            self.assertEqual(self.ui.cmb_shot_select.currentData(), 3)
            store.update_shot(1, name="A2")  # a shot that is not the active one
            self.assertEqual(self._rows()[0], (1, "A2  [0–20]"))
        finally:
            self._clear(store)

    def test_previous_and_next_step_through_the_shots(self):
        """2026-10-10: the Shot Sequencer dropdown's option-box buttons."""
        store = self._three_shots()
        ctrl = self.slots.controller
        nav = self.ui.cmb_shot_select._shots_nav_options
        try:
            self.assertEqual(sorted(nav), ["new", "next", "prev"])
            self.assertFalse(nav["prev"].widget.isEnabled(), "first shot")
            self.assertTrue(nav["next"].widget.isEnabled())
            ctrl.on_navigate_shot(1)
            ctrl.on_navigate_shot(1)
            self.assertEqual(store.active_shot_id, 3)
            self.assertEqual(self.ui.cmb_shot_select.currentData(), 3)
            self.assertFalse(nav["next"].widget.isEnabled(), "last shot")
            ctrl.on_navigate_shot(1)  # past the end: nothing
            self.assertEqual(store.active_shot_id, 3)
            ctrl.on_navigate_shot(-1)
            self.assertEqual(store.active_shot_id, 2)
        finally:
            self._clear(store)

    def test_shift_all_reports_a_sequence_already_where_it_is_asked_for(self):
        store = self._store()
        store.shots = [ShotBlock(1, "A", 0, 20, [])]
        try:
            self.ui.spn_shift_all.setValue(0)
            self.slots.btn_shift_all()
            self.assertEqual(
                [(s.start, s.end) for s in store.sorted_shots()], [(0, 20)]
            )
        finally:
            self._clear(store)

    def test_the_retain_options_are_the_engines_swap_fields(self):
        """One checkbox per ``ShotSequencer.SWAP_FIELDS``: a field the engine
        adds must not go missing from the option box."""
        ctrl = self.slots.controller
        self.assertEqual(
            [field for field, _label, _tip in ctrl._SWAP_RETAIN],
            list(ctrl._sequencer_cls().SWAP_FIELDS),
        )

    def test_swap_with_picks_the_next_shot_and_names_it(self):
        """2026-10-14: "swap shot positions with a 'Swap With x' button" --
        the other shot and the options in its option box, the pick named on
        the button."""
        store = self._three_shots()
        ui = self.ui
        try:
            ui.cmb_swap_mode.setCurrentIndex(0)
            self.assertTrue(ui.btn_swap_shot.isEnabled())
            rows = [
                ui.cmb_swap_with.itemData(i) for i in range(ui.cmb_swap_with.count())
            ]
            self.assertEqual(rows, [2, 3], "every shot but the selected one")
            self.assertEqual(ui.cmb_swap_with.currentData(), 2, "the next shot")
            self.assertEqual(ui.btn_swap_shot.text(), "Swap With: B")
            store.set_active_shot(3)  # the last: the one before it
            self.assertEqual(ui.cmb_swap_with.currentData(), 2)
            ui.cmb_swap_with.setCurrentIndex(0)
            self.assertEqual(ui.btn_swap_shot.text(), "Swap With: A")
            ui.cmb_swap_mode.setCurrentIndex(1)
            self.assertEqual(ui.btn_swap_shot.text(), "Copy To: A")
            self.assertFalse(ui.chk_swap_retain_name.isEnabled(), "a swap's option")
        finally:
            ui.cmb_swap_mode.setCurrentIndex(0)
            self._clear(store)

    def test_a_name_the_export_would_respell_is_refused_where_it_is_typed(self):
        """The name IS the exported clip name. Typed into the field, one the
        export would respell is never stored: the field says why, and Enter
        gives the shot its own name back. A legal one is stored as typed.

        Typed with ``keyClicks`` and handed to the field's slot directly, as
        the switchboard's debounce would: nothing here spins the event loop,
        so no idle-time work can land mid-test.
        """
        from qtpy import QtCore, QtTest

        txt = self.ui.txt_shot_name
        store = self._store()
        store.shots = []
        shot = store.define_shot("Intro", 0, 10)
        store.set_active_shot(shot.shot_id)

        def type_name(text):
            txt.selectAll()
            QtTest.QTest.keyClicks(txt, text)
            self.slots.txt_shot_name()

        try:
            self.slots.controller._sync_shot_editor(store)
            self.assertEqual(txt.text(), "Intro")
            type_name("Intro 2")
            self.assertEqual(shot.name, "Intro")
            self.assertEqual(txt.property("actionState"), "invalid")
            self.assertIn("a space", txt.toolTip())
            QtTest.QTest.keyClick(txt, QtCore.Qt.Key_Return)
            self.assertEqual(txt.text(), "Intro")
            self.assertNotEqual(txt.property("actionState"), "invalid")
            type_name("Intro__2")
            self.assertEqual(shot.name, "Intro__2")
            self.assertNotEqual(txt.property("actionState"), "invalid")
        finally:
            self._clear(store)


@unittest.skipIf(MAYA_AVAILABLE, "real Qt widgets and real Maya crash in one process")
@unittest.skipIf(not qt_widgets_available(), "Qt widgets unavailable")
class TestShotsPanelLoadsOverBtk(_LoadedPanelCases, unittest.TestCase):
    """The panel loaded through a real (offscreen) Qt / Switchboard /
    ``BlenderUiHandler`` stack over ``btk`` -- no bpy: the store's in-memory
    fallback, its scene hooks stubbed where a case needs the file (the former
    blendertk ``test_shots_slots`` panel cases)."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        blendertk_repo = os.path.join(MONO, "blendertk")
        if os.path.isdir(blendertk_repo) and blendertk_repo not in sys.path:
            sys.path.insert(0, blendertk_repo)
        try:
            import blendertk
            from blendertk.ui_utils.blender_ui_handler import BlenderUiHandler
        except Exception as error:  # noqa: BLE001 -- the Blender side absent
            raise unittest.SkipTest(f"blendertk unavailable: {error}") from error
        from uitk import Switchboard
        from uitk.testing import TestSandbox

        from tentacle.tcl import Tcl

        TestSandbox.activate()  # the panel's settings stay off the live stores
        cls.btk = blendertk
        cls.store_cls = blendertk.ShotSequencer.STORE_CLASS
        # The cross-scene prefs and the class singleton: off the real config.
        cls._prefs = tempfile.TemporaryDirectory(prefix="tcl_shots_panel_")
        cls.store_cls._prefs_dir_override = cls._prefs.name
        cls.store_cls.clear_active()
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        handler = BlenderUiHandler(switchboard=Switchboard())
        # A process singleton: in a run that built it earlier it keeps ITS
        # switchboard, which is the one holding the UIs.
        cls.sb = handler.sb
        Tcl.register_shared(cls.sb)
        cls.ui = handler.get("shots")
        for _ in range(5):
            cls.app.processEvents()
        cls.slots = cls.sb.get_slots_instance(cls.ui)

    @classmethod
    def tearDownClass(cls):
        cls.slots.controller.remove_callbacks()
        cls.store_cls.clear_active()
        cls.store_cls._prefs_dir_override = None
        cls._prefs.cleanup()

    def _store(self):
        return self.slots.controller._active_store()

    def test_the_host_is_blenders(self):
        self.assertIs(self.slots.tk, self.btk)
        self.assertIs(self.slots.controller._sequencer_cls(), self.btk.ShotSequencer)

    def test_the_defaults_are_a_fresh_stores(self):
        self.assertAlmostEqual(self.ui.spn_detection.value(), 5.0)
        self.assertAlmostEqual(self.ui.spn_initial_length.value(), 200.0)

    def test_delete_shots_is_offered_while_the_store_has_shots(self):
        """All Shots > Delete Shots on its default scope, Stale: enabled while
        the store holds a shot, and the click decides. Deleting an object
        raises no store event, so a state judged at the last one went stale --
        the export's Open Shots link opened the panel with the button greyed
        out. With none stale it says so and deletes nothing; with one it asks
        with the names and deletes records only. The store's two scene hooks
        stand in for the file."""
        ctrl = self.slots.controller
        store = self._store()
        store.shots = [
            ShotBlock(1, "Live", 0, 20, ["Held"]),
            ShotBlock(2, "Gone", 40, 60, ["Lost"]),
        ]
        held = {"Held", "Lost"}
        store._existing_objects = lambda names: {n for n in names if n in held}
        store._keyed_windows = lambda windows: [False] * len(windows)
        asked = []
        try:
            ctrl.refresh_state()
            self.ui.cmb_delete_scope.setCurrentIndex(0)
            self.assertTrue(self.ui.btn_delete_shots.isEnabled())
            with _answer(QtWidgets.QMessageBox.Yes, asked):
                self.slots.btn_delete_shots()  # nothing stale yet
                self.assertEqual((asked, len(store.shots)), ([], 2))
                held.discard("Lost")  # deleted from the file: no store event
                self.slots.btn_delete_shots()
            self.assertIn("Gone [40–60]", asked[0])
            self.assertEqual([s.name for s in store.shots], ["Live"])
            store.shots = []
            ctrl.refresh_state()
            self.assertFalse(self.ui.btn_delete_shots.isEnabled())
        finally:
            del store._existing_objects, store._keyed_windows
            self._clear(store)

    def test_the_scope_decides_what_delete_shots_takes(self):
        """One button, three scopes, picked in its option box and named on the
        button (2026-10-07). "Held" exists, nothing is keyed but inside Live."""
        store = self._store()
        store._existing_objects = lambda names: {n for n in names if n == "Held"}
        store._keyed_windows = lambda windows: [False] * len(windows)
        # "Gone" resolves to nothing (2026-10-10: Empty is what holds nothing,
        # whatever it names).
        store._members_keyed_windows = lambda entries: [
            True if "Held" in names else None for names, _w in entries
        ]
        cmb = self.ui.cmb_delete_scope
        try:
            for scope, label, left in (
                ("empty", "Delete Empty Shots", ["Live"]),
                ("all", "Delete All Shots", []),
            ):
                store.shots = [
                    ShotBlock(1, "Live", 0, 20, ["Held"]),
                    ShotBlock(2, "Empty", 40, 60),
                    ShotBlock(3, "Cleared", 70, 90, ["Gone"]),
                ]
                cmb.setCurrentIndex(cmb.findData(scope))
                self.assertEqual(self.ui.btn_delete_shots.text(), label)
                with _answer(QtWidgets.QMessageBox.Yes):
                    self.slots.btn_delete_shots()
                self.assertEqual([s.name for s in store.shots], left, scope)
        finally:
            del store._existing_objects, store._keyed_windows
            del store._members_keyed_windows
            cmb.setCurrentIndex(0)
            self._clear(store)


# ---------------------------------------------------------------------- in Maya


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestShotsPanelInMaya(unittest.TestCase):
    """The controller over the real ``mtk`` (no widgets: any Maya)."""

    def setUp(self):
        self.cmds = cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        cmds.file(new=True, force=True)
        state = cmds.undoInfo(q=True, state=True)
        cmds.undoInfo(state=True, infinity=True)
        self.addCleanup(cmds.undoInfo, state=state)
        store_cls = self.mtk.ShotSequencer.STORE_CLASS
        store_cls.clear_active()
        self.addCleanup(store_cls.clear_active)
        self.store = store_cls.active()
        self.store.define_shot("A", 0, 50)
        self.store.define_shot("B", 60, 100)
        loc = cmds.spaceLocator(name="shots_panel_loc")[0]
        for t in (3, 10, 20, 70, 90):
            cmds.setKeyframe(loc, at="translateX", t=t, v=float(t))
        self.ctrl = _bare(self.mtk)

    def test_the_host_is_mayas(self):
        self.assertIs(self.ctrl._sequencer_cls(), self.mtk.ShotSequencer)
        self.assertIs(self.ctrl._store_cls(), self.mtk.ShotStore)
        self.assertIs(self.ctrl._active_store(), self.store)

    def test_an_end_field_resize_is_undone_with_its_bounds(self):
        """The End field moves the bound and ripples the keys after it; Maya's
        Ctrl+Z undid the keys and kept the bound (no Sequencer open)."""
        a = self.store.shot_by_name("A")
        self.store.set_active_shot(a.shot_id)
        before = (a.end, self.store.shot_by_name("B").start)
        self.ctrl.on_shot_end_changed(40.0)
        self.assertEqual(self.store.shot_by_id(a.shot_id).end, 40.0)
        self.cmds.undo()
        self.assertEqual(
            (a.end, self.store.shot_by_name("B").start), before, "bounds undone"
        )
        self.cmds.redo()
        self.assertEqual(self.store.shot_by_id(a.shot_id).end, 40.0)


@unittest.skipUnless(
    MAYA_AVAILABLE and qt_widgets_available(), "needs a GUI Maya (--in-maya)"
)
class TestShotsPanelLoadsInMaya(_LoadedPanelCases, unittest.TestCase):
    """The panel loaded the way a bare host handler stands it up
    (``MayaUiHandler`` with tentacle's shared roots), driving the real ``mtk``
    on a real scene (the former mayatk ``test_shots_panel``)."""

    @classmethod
    def setUpClass(cls):
        cls.cmds = maya_module("maya.cmds")
        cls.mtk = maya_module("mayatk")
        from mayatk.ui_utils.maya_ui_handler import MayaUiHandler
        from tentacle.tcl import Tcl

        handler = MayaUiHandler.instance()
        Tcl.register_shared(handler.sb)
        cls.ui = handler.get("shots")
        cls.slots = cls.ui.slots
        app = QtWidgets.QApplication.instance()
        for _ in range(50):
            app.processEvents()

    @classmethod
    def tearDownClass(cls):
        # The handler keeps the panel for the process, as a Maya session does,
        # but its store subscriptions end with this class: a live panel
        # re-syncs every store a later module invalidates.
        cls.slots.controller.remove_callbacks()

    def setUp(self):
        self.cmds.file(new=True, force=True)

    def _store(self):
        return self.slots.controller._active_store()

    def test_the_host_is_mayas(self):
        self.assertEqual(type(self.slots).__module__, "tentacle.slots.tools.shots")
        self.assertIs(self.slots.tk, self.mtk)

    def test_delete_shots_is_offered_while_the_store_has_shots(self):
        """All Shots > Delete Shots, on its default scope (Stale): with none
        stale it says so and deletes nothing; with one (every member gone,
        nothing keyed in its frames) it asks with the names and deletes that
        record only -- the live shot and its keys stay."""
        cmds = self.cmds
        live = cmds.ls(cmds.polyCube(name="panelLive")[0], long=True)[0]
        gone = cmds.ls(cmds.polyCube(name="panelGone")[0], long=True)[0]
        for node, (first, last) in ((live, (1, 20)), (gone, (40, 60))):
            for t, v in ((first, 0), (last, 5)):
                cmds.setKeyframe(node, attribute="translateX", t=t, v=v)
        store = self._store()
        store.shots = [
            ShotBlock(1, "Live", 0, 20, [live]),
            ShotBlock(2, "Gone", 40, 60, [gone]),
        ]
        ctrl = self.slots.controller
        asked = []
        try:
            ctrl.refresh_state()
            self.ui.cmb_delete_scope.setCurrentIndex(0)
            self.assertTrue(self.ui.btn_delete_shots.isEnabled())
            with _answer(QtWidgets.QMessageBox.Yes, asked):
                self.slots.btn_delete_shots()  # nothing stale yet
                self.assertEqual((asked, len(store.shots)), ([], 2))
                cmds.delete(gone)  # its keys go with it; no store event
                self.slots.btn_delete_shots()
            self.assertIn("Gone [40–60]", asked[0])
            self.assertEqual([s.name for s in store.shots], ["Live"])
            self.assertEqual(
                cmds.keyframe(live, query=True, timeChange=True), [1.0, 20.0]
            )
            store.shots = []
            ctrl.refresh_state()
            self.assertFalse(self.ui.btn_delete_shots.isEnabled())
        finally:
            self._clear(store)

    def test_the_scope_decides_what_delete_shots_takes(self):
        cmds = self.cmds
        live = cmds.ls(cmds.polyCube(name="scopeLive")[0], long=True)[0]
        cmds.setKeyframe(live, attribute="translateX", t=1, v=0)
        cmds.setKeyframe(live, attribute="translateX", t=20, v=5)
        store = self._store()
        cmb = self.ui.cmb_delete_scope
        try:
            for scope, label, left in (
                ("empty", "Delete Empty Shots", ["Live"]),
                ("all", "Delete All Shots", []),
            ):
                store.shots = [
                    ShotBlock(1, "Live", 0, 20, [live]),
                    ShotBlock(2, "Empty", 40, 60),
                ]
                cmb.setCurrentIndex(cmb.findData(scope))
                self.assertEqual(self.ui.btn_delete_shots.text(), label)
                with _answer(QtWidgets.QMessageBox.Yes):
                    self.slots.btn_delete_shots()
                self.assertEqual([s.name for s in store.shots], left, scope)
                self.assertEqual(
                    cmds.keyframe(live, query=True, timeChange=True), [1.0, 20.0]
                )
        finally:
            cmb.setCurrentIndex(0)
            self._clear(store)

    def test_new_shot_appends_one_initial_length_long(self):
        """The Shot Sequencer's New Shot, here: the gap after the last shot,
        Initial Length long, and it becomes the active shot. Clickable with no
        shot at all -- the dropdown is disabled then."""
        store = self._store()
        old = (store.gap, store.initial_shot_length)
        nav = self.ui.cmb_shot_select._shots_nav_options
        try:
            store.shots = []
            self.slots.controller._sync_from_store()
            self.assertFalse(self.ui.cmb_shot_select.isEnabled())
            self.assertTrue(nav["new"].widget.isEnabled())
            store.gap, store.initial_shot_length = 10.0, 50.0
            self.slots.controller.on_new_shot()
            self.slots.controller.on_new_shot()
            first, second = store.sorted_shots()
            self.assertEqual(second.start - first.end, 10.0)
            self.assertEqual(second.end - second.start, 50.0)
            self.assertEqual(store.active_shot_id, second.shot_id)
            self.assertEqual(self.ui.cmb_shot_select.currentData(), second.shot_id)
        finally:
            store.gap, store.initial_shot_length = old
            self._clear(store)

    def test_swap_with_trades_places_and_retains_the_checked_fields(self):
        store = self._three_shots()
        ui = self.ui
        try:
            ui.cmb_swap_mode.setCurrentIndex(0)
            ui.cmb_swap_with.setCurrentIndex(1)  # C
            ui.chk_swap_retain_name.setChecked(True)
            self.slots.btn_swap_shot()
            self.assertEqual(
                [(s.shot_id, s.name) for s in store.sorted_shots()],
                [(3, "A"), (2, "B"), (1, "C")],
            )
            self.assertEqual(store.active_shot_id, 1, "the selection rides along")
        finally:
            ui.chk_swap_retain_name.setChecked(False)
            self._clear(store)

    def test_copy_over_takes_the_selected_shots_length(self):
        store = self._three_shots()
        store.update_shot(3, end=70)  # C: 10 frames
        store.set_active_shot(3)
        ui = self.ui
        try:
            ui.cmb_swap_mode.setCurrentIndex(1)
            ui.cmb_swap_with.setCurrentIndex(0)  # A
            self.slots.btn_swap_shot()
            self.assertEqual(
                [(s.name, s.start, s.end) for s in store.sorted_shots()],
                [("A", 0, 10), ("B", 20, 40), ("C", 50, 60)],
            )
        finally:
            ui.cmb_swap_mode.setCurrentIndex(0)
            self._clear(store)


if __name__ == "__main__":
    unittest.main()
