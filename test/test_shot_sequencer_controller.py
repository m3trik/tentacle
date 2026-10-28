# !/usr/bin/python
# coding=utf-8
"""The Shot Sequencer panel's controller over the real ``mtk``, in Maya.

The controller and its mixins are tentacle's (``slots/tools/_shot_sequencer/``,
one copy for both hosts); these are the tests that drove them from mayatk's
``test_sequencer.py`` and ``test_sequencer_gui.py`` before they moved, with
their assertions kept. Every controller built here -- bare (``__new__``),
subclassed, or from ``_FakeSlots`` -- is this module's
:class:`ShotSequencerController`, which reaches Maya through ``mtk`` (its
``tk``); a bare mixin host gets ``mtk.SequencerHost`` as its ``host``. The host
logic those tests used to reach through the panel (the undo walk, the
selection guards, the curve and tangent writers, the content rule of a keying
refresh) is mayatk's ``SequencerHost`` now and is tested there.

Most of it needs a GUI Maya (mayatk ran these files in one only:
``run_tests.GUI_REQUIRED``); three classes run anywhere (no host): the marker
dict, marker-mode navigation and a clip list read into sequences.

Run::

    python tentacle/test/run_tests.py test_shot_sequencer_controller --in-maya
"""

import logging
import unittest
from unittest import mock
from unittest.mock import patch

import pythontk as ptk
from qtpy import QtWidgets
from uitk import ComboBox, SequencerWidget

from _host import MAYA_AVAILABLE, maya_module, qt_widgets_available
from tentacle.slots.tools._shot_sequencer import controller as _controller
from tentacle.slots.tools._shot_sequencer.clip_motion import (
    ClipMotionMixin as _ClipMotionMixin,
)
from tentacle.slots.tools._shot_sequencer.marker_manager import MarkerManagerMixin
from tentacle.slots.tools._shot_sequencer.shot_nav import ShotNavMixin

cmds = maya_module("maya.cmds")
mtk = maya_module("mayatk")

#: The flag names the moved tests read: any Maya, and one that builds widgets.
HAS_MAYA = MAYA_AVAILABLE
HAS_QT = qt_widgets_available()
_SKIP_MSG = "needs a GUI Maya (--in-maya)"

if HAS_MAYA:
    from mayatk.anim_utils.shots.shot_manifest._shot_manifest import (
        BuilderObject,
        BuilderStep,
        ShotManifest,
    )
    from mayatk.audio_utils._audio_utils import AudioUtils

    ShotBlock = mtk.ShotBlock
    ShotSequencer = mtk.ShotSequencer
    ShotStore = mtk.ShotStore
else:  # the classes that read these skip without Maya
    BuilderObject = BuilderStep = ShotManifest = AudioUtils = None
    ShotBlock = ShotSequencer = ShotStore = None


class ShotSequencerController(_controller.ShotSequencerController):
    """The panel's controller over the real ``mtk`` (``None`` without Maya):
    every controller this module builds reaches the scene through it."""

    tk = mtk


class ClipMotionMixin(_ClipMotionMixin):
    """The panel's clip-motion mixin for a bare host: its ``host`` is the real
    ``mtk.SequencerHost``, as the controller's is."""

    @property
    def host(self):
        return mtk.SequencerHost


class _Switchboard:
    """The switchboard a controller reads: a public uitk name resolves to the
    real class (the panel builds real menus, rows and transport from them), any
    other name is a mock recorded on first use (``handlers``, ``input_dialog``)."""

    def __init__(self, tk=None):
        self.tk = tk

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name[:1].isupper():
            import uitk

            return getattr(uitk, name)
        value = mock.MagicMock(name=f"sb.{name}")
        setattr(self, name, value)
        return value


# =========================================================================
# Helpers (mayatk's test_sequencer.py / test_sequencer_gui.py)
# =========================================================================


def _new_scene():
    cmds.file(new=True, force=True)


def _make_cube(name, keys, attr="translateX"):
    cube = cmds.polyCube(name=name)[0]
    for frame, value in keys.items():
        cmds.setKeyframe(cube, attribute=attr, time=frame, value=value)
    return cube


def _process_events():
    QtWidgets.QApplication.processEvents()


#: Per-key tangent properties a move must carry through untouched.
TANGENT_PROPS = (
    "inAngle",
    "outAngle",
    "inWeight",
    "outWeight",
    "inTangentType",
    "outTangentType",
    "weightLock",
    "lock",
)


def snapshot_curve(crv):
    """Full per-key state of *crv* -- value, every tangent property, breakdown."""
    times = cmds.keyframe(crv, q=True) or []
    breakdowns = set(cmds.keyframe(crv, q=True, breakdown=True) or [])
    recs = []
    for t in times:
        rec = {
            "time": t,
            "value": cmds.keyframe(crv, q=True, time=(t, t), valueChange=True)[0],
            "breakdown": any(abs(t - b) < 1e-6 for b in breakdowns),
        }
        for name in TANGENT_PROPS:
            rec[name] = cmds.keyTangent(crv, q=True, time=(t, t), **{name: True})[0]
        recs.append(rec)
    return recs


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestKeysBatchAuditRegressions(unittest.TestCase):
    """Audit regressions: expansion order and same-curve gesture merging."""

    def setUp(self):
        cmds.file(new=True, force=True)

    class _Clip:
        def __init__(self, data):
            self.data = data

    class _Widget:
        def __init__(self, clips):
            self._clips = clips

        def get_clip(self, clip_id):
            return self._clips.get(clip_id)

    def _host(self, clips, seq):
        import logging

        outer = self

        class Host(ClipMotionMixin):
            def __init__(self):
                self.sequencer = seq
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._syncing = False
                self.logger = logging.getLogger("test.keys_audit_host")
                self.synced = []
                self.footers = []
                self._widget = outer._Widget(clips)

            def _get_sequencer_widget(self):
                return self._widget

            def _sync_to_widget(self, shot_id=None):
                self.synced.append(shot_id)

            def _sync_combobox(self):
                pass

            def _set_footer(self, text, *a, **k):
                self.footers.append(text)

        return Host()

    def test_expansion_cannot_double_move_a_landed_key(self):
        """The S1: at zero gap, a key dragged onto the NEXT shot's start on
        an object that is a member of BOTH shots.  Committing first and
        expanding after let the expansion's downstream ripple sweep the
        freshly-landed key a second time (the next shot's envelope starts at
        its .start).  Expansion now runs BEFORE the commit."""
        cube = cmds.polyCube(name="dm_shared")[0]
        # Keys in shot A (0-30) and in shot B (30-60) on the SAME object.
        for t, v in ((10, 0.0), (20, 1.0), (40, 2.0), (55, 3.0)):
            cmds.setKeyframe(cube, at="translateX", t=t, v=v)
        seq = ShotSequencer(
            [
                ShotBlock(0, "A", 0, 30, [cube]),
                ShotBlock(1, "B", 30, 60, [cube]),
            ]
        )
        clips = {1: self._Clip({"obj": cube, "attr_name": "translateX", "shot_id": 0})}
        host = self._host(clips, seq)

        # Drag A's key at 20 exactly onto B's start (30).
        host.on_keys_batch_moved([(1, [(20.0, 30.0)])])

        times = sorted(cmds.keyframe(cube, q=True, at="translateX") or [])
        self.assertIn(
            30.0,
            times,
            f"the landed key must sit AT 30, not swept further: {times}",
        )
        shot_a = seq.shot_by_id(0)
        self.assertGreaterEqual(shot_a.end, 30.0, "shot A grew to own the landed key")
        # B's own keys rippled right by A's expansion (0 here since 30 was
        # already A's end)… with a zero-delta expansion nothing else moves.
        self.assertEqual(
            times, [10.0, 30.0, 40.0, 55.0], f"no other key may move: {times}"
        )

    def test_expansion_past_the_boundary_ripples_but_never_double_moves(self):
        """Land at 35 — INSIDE B's territory.  A must grow to 35, B must
        ripple right by 5, and the landed key must sit exactly at 35."""
        cube = cmds.polyCube(name="dm_shared2")[0]
        for t, v in ((10, 0.0), (20, 1.0), (40, 2.0), (55, 3.0)):
            cmds.setKeyframe(cube, at="translateX", t=t, v=v)
        seq = ShotSequencer(
            [
                ShotBlock(0, "A", 0, 30, [cube]),
                ShotBlock(1, "B", 30, 60, [cube]),
            ]
        )
        clips = {1: self._Clip({"obj": cube, "attr_name": "translateX", "shot_id": 0})}
        host = self._host(clips, seq)

        host.on_keys_batch_moved([(1, [(20.0, 35.0)])])

        times = sorted(cmds.keyframe(cube, q=True, at="translateX") or [])
        self.assertIn(35.0, times, f"landed key must sit at 35: {times}")
        self.assertEqual(
            times,
            [10.0, 35.0, 45.0, 60.0],
            f"B's keys ride the +5 ripple exactly once: {times}",
        )
        self.assertAlmostEqual(seq.shot_by_id(0).end, 35.0)
        self.assertAlmostEqual(seq.shot_by_id(1).start, 35.0)

    def test_same_curve_two_clips_one_gesture_commits_once(self):
        """The S1: two clips backed by the SAME anim curve (split_static
        segments of one obj.attr).  Sequential per-clip commits let group
        1's landed key be re-grabbed or overwritten by group 2's window;
        the gesture is now merged per curve before any commit."""
        cube = cmds.polyCube(name="dm_samecurve")[0]
        for t, v in ((10, 0.0), (20, 5.0), (40, 5.0), (50, 9.0)):
            cmds.setKeyframe(cube, at="translateX", t=t, v=v)
        seq = ShotSequencer([ShotBlock(0, "A", 0, 100, [cube])])
        clips = {
            1: self._Clip({"obj": cube, "attr_name": "translateX", "shot_id": 0}),
            2: self._Clip({"obj": cube, "attr_name": "translateX", "shot_id": 0}),
        }
        host = self._host(clips, seq)

        # One drag, +20 on both clips' keys: clip 1 moves (10,20), clip 2
        # moves (40,50).  Clip 1's key at 20 lands at 40 — exactly clip 2's
        # origin.  Per-clip commits collapsed the two; merged they slide.
        host.on_keys_batch_moved(
            [(1, [(10.0, 30.0), (20.0, 40.0)]), (2, [(40.0, 60.0), (50.0, 70.0)])]
        )

        times = sorted(cmds.keyframe(cube, q=True, at="translateX") or [])
        vals = cmds.keyframe(cube, q=True, at="translateX", valueChange=True)
        self.assertEqual(
            times,
            [30.0, 40.0, 60.0, 70.0],
            f"all four keys must survive at +20: {times}",
        )
        self.assertEqual(
            sorted(vals), [0.0, 5.0, 5.0, 9.0], f"no value may be lost: {vals}"
        )

    def test_gesture_is_one_undo_step_and_syncing_guard_restores(self):
        cube = cmds.polyCube(name="dm_chunk")[0]
        for t in (10, 20):
            cmds.setKeyframe(cube, at="translateX", t=t, v=float(t))
        seq = ShotSequencer([ShotBlock(0, "A", 0, 100, [cube])])
        clips = {1: self._Clip({"obj": cube, "attr_name": "translateX", "shot_id": 0})}
        host = self._host(clips, seq)
        host.on_keys_batch_moved([(1, [(10.0, 15.0), (20.0, 25.0)])])
        self.assertFalse(host._syncing, "guard must restore after the commit")
        cmds.undo()
        self.assertEqual(
            sorted(cmds.keyframe(cube, q=True, at="translateX") or []),
            [10.0, 20.0],
            "one Ctrl+Z reverses the whole gesture",
        )


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestKeysBatchMoved(unittest.TestCase):
    """One key drag == one commit: a single undo chunk, a snapshot taken
    BEFORE the boundary follow-up, and the panel left showing the shot the
    drag started in."""

    def setUp(self):
        cmds.file(new=True, force=True)

    class _Clip:
        def __init__(self, data):
            self.data = data

    class _Widget:
        def __init__(self, clips):
            self._clips = clips

        def get_clip(self, clip_id):
            return self._clips.get(clip_id)

    def _host(self, clips, seq):
        import logging

        outer = self

        class Host(ClipMotionMixin):
            """Uses the REAL snapshot push/pop so ordering is observable."""

            def __init__(self):
                self.sequencer = seq
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._syncing = False
                self.logger = logging.getLogger("test.keys_batch_host")
                self.synced = []
                self.footers = []
                self._widget = outer._Widget(clips)

            def _get_sequencer_widget(self):
                return self._widget

            def _sync_to_widget(self, shot_id=None):
                self.synced.append(shot_id)

            def _sync_combobox(self):
                pass

            def _set_footer(self, text, *a, **k):
                self.footers.append(text)

        return Host()

    def _keyed_cube(self, name, times):
        cube = cmds.polyCube(name=name)[0]
        for i, t in enumerate(times):
            cmds.setKeyframe(cube, at="translateX", t=t, v=float(i))
        return str(cube)

    def test_snapshot_predates_the_boundary_expansion(self):
        """The snapshot must hold the PRE-drag bounds.

        The boundary follow-up runs inside the same commit, so a snapshot
        taken afterwards records the expanded bounds and undo would re-apply
        the very expansion it is meant to reverse.
        """
        cube = self._keyed_cube("kb_expand", (10, 20))
        seq = ShotSequencer([ShotBlock(0, "S0", 0, 30, [cube])])
        clips = {1: self._Clip({"obj": cube, "attr_name": "translateX", "shot_id": 0})}
        host = self._host(clips, seq)

        # Drag the key at 20 out to 60 — past the shot's end at 30.
        host.on_keys_batch_moved([(1, [(20.0, 60.0)])])

        self.assertGreaterEqual(
            seq.shot_by_id(0).end, 60.0, "the shot must follow the key out"
        )
        # The restore point lives on the store's ledger (scene_edit pushes it
        # before any mutation); assert it through behaviour, not internals.
        self.assertTrue(seq.store.has_boundary_snapshot())
        self.assertEqual(
            seq.store.peek_boundary_tag()[0],
            True,
            "a key commit reaches Maya's queue, so the restore point is paired",
        )
        self.assertTrue(seq.store.restore_boundary_snapshot())
        self.assertEqual(
            (seq.shot_by_id(0).start, seq.shot_by_id(0).end),
            (0.0, 30.0),
            "the snapshot must hold the PRE-drag bounds",
        )

    def test_noop_drag_leaves_no_snapshot_behind(self):
        cube = self._keyed_cube("kb_noop", (10, 20))
        seq = ShotSequencer([ShotBlock(0, "S0", 0, 30, [cube])])
        clips = {1: self._Clip({"obj": cube, "attr_name": "translateX", "shot_id": 0})}
        host = self._host(clips, seq)

        host.on_keys_batch_moved([(1, [(20.0, 20.0)])])  # zero delta

        self.assertFalse(
            seq.store.has_boundary_snapshot(),
            "a no-op must not leave a restore point for an edit that never happened",
        )
        self.assertEqual(host.synced, [], "and must not rebuild")

    def test_rebuild_targets_the_originating_shot(self):
        """A drag spanning two shots must not retarget the panel.

        The originating clip contributes nothing here (zero delta), so the
        only shot that RECORDS a change is the other one -- which is exactly
        the case where deriving the target from the changed set sends the
        panel to a shot the user was not looking at.
        """
        a = self._keyed_cube("kb_a", (10, 20))
        b = self._keyed_cube("kb_b", (110, 120))
        seq = ShotSequencer(
            [
                ShotBlock(0, "S0", 0, 50, [a]),
                ShotBlock(1, "S1", 100, 150, [b]),
            ]
        )
        clips = {
            1: self._Clip({"obj": a, "attr_name": "translateX", "shot_id": 0}),
            2: self._Clip({"obj": b, "attr_name": "translateX", "shot_id": 1}),
        }
        host = self._host(clips, seq)

        host.on_keys_batch_moved([(1, [(20.0, 20.0)]), (2, [(120.0, 125.0)])])

        self.assertEqual(
            host.synced,
            [0],
            "the shot on screen is the one the drag started in",
        )

    def test_whole_gesture_is_one_undo_chunk(self):
        a = self._keyed_cube("kb_c1", (10, 20))
        b = self._keyed_cube("kb_c2", (10, 20))
        seq = ShotSequencer([ShotBlock(0, "S0", 0, 50, [a, b])])
        clips = {
            1: self._Clip({"obj": a, "attr_name": "translateX", "shot_id": 0}),
            2: self._Clip({"obj": b, "attr_name": "translateX", "shot_id": 0}),
        }
        host = self._host(clips, seq)

        host.on_keys_batch_moved([(1, [(20.0, 25.0)]), (2, [(20.0, 25.0)])])
        self.assertEqual(cmds.keyframe(a, q=True, at="translateX"), [10.0, 25.0])
        self.assertEqual(cmds.keyframe(b, q=True, at="translateX"), [10.0, 25.0])

        cmds.undo()
        self.assertEqual(
            (
                cmds.keyframe(a, q=True, at="translateX"),
                cmds.keyframe(b, q=True, at="translateX"),
            ),
            ([10.0, 20.0], [10.0, 20.0]),
            "one Ctrl+Z must reverse the whole drag, not one curve of it",
        )

    def test_on_keys_moved_routes_through_the_batch_path(self):
        cube = self._keyed_cube("kb_single", (10, 20))
        seq = ShotSequencer([ShotBlock(0, "S0", 0, 50, [cube])])
        clips = {1: self._Clip({"obj": cube, "attr_name": "translateX", "shot_id": 0})}
        host = self._host(clips, seq)

        host.on_keys_moved(1, [(20.0, 25.0)])
        self.assertEqual(cmds.keyframe(cube, q=True, at="translateX"), [10.0, 25.0])
        self.assertEqual(host.synced, [0])


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestAKeyDraggedOntoTheSeamSplitsNothing(unittest.TestCase):
    """Dragging a key onto the next shot's start grows the shot to it and
    ripples the neighbour away.  Writing the grown bound BEFORE that ripple
    made the store read the two shots as contiguous for a moment, and the
    planner then "split" a shared sample that never was one -- re-keying the
    neighbour's opening pose at its new start.  Measured 2026-09-05: every
    FAILED_CMPT_LOC curve gained one key (31 -> 32).

    The handlers expand BEFORE the dragged keys land, so the key on B's start
    is B's own opening pose.  (Until 2026-09-22 this fixture modelled the
    dragged key as already landed there, which pinned that pose staying
    behind while B moved away -- see the class below.)"""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.loc = cmds.spaceLocator(name="seam_loc")[0]
        # 60 is B's opening pose; the dragged key has not landed yet
        for t, v in ((10, 0), (40, 5), (60, 7), (70, 9), (90, 9)):
            cmds.setKeyframe(self.loc, at="translateX", t=t, v=v)
        self.seq = ShotSequencer(
            [
                ShotBlock(0, "A", 0, 50, [self.loc]),
                ShotBlock(1, "B", 60, 100, [self.loc]),
            ]
        )

    def tearDown(self):
        ShotStore.clear_active()

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_the_neighbour_ripples_whole_and_gains_no_key(self):
        seq = self.seq

        class _Widget:
            ctrl_held_at_press = False
            shift_held_at_press = False

        class _Ctl(ShotSequencerController):
            def __init__(self):
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._audio_segments_cache = None
                self._syncing = False

            sequencer = seq

            def _get_sequencer_widget(self):
                return _Widget()

        _Ctl()._expand_shot_range(0, 0, 60)

        self.assertEqual(
            [(s.start, s.end) for s in seq.sorted_shots()], [(0.0, 60.0), (70.0, 110.0)]
        )
        self.assertEqual(
            cmds.keyframe(self.loc, q=True, at="translateX"),
            [10.0, 40.0, 70.0, 80.0, 100.0],
            "B moved whole, its opening pose included, and gained nothing",
        )


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestADragOntoAKeyedNeighbourLeavesItWhole(unittest.TestCase):
    """A drag that grows a shot ONTO a keyed neighbour's boundary, or into
    the neighbour, ripples that neighbour away WHOLE: its boundary pose goes
    with it.

    Measured 2026-09-22 (BACKLOG 2026-09-05): the handlers ripple before the
    dragged keys land, but the planner's carried window treated the sample on
    the new bound as the dragged shot's, so the neighbour's own pose stayed
    behind -- nudged a frame into the gap by the landing key -- and the
    neighbour opened on nothing.  On the production chain it read as
    ``FAILED_CMPT_LOC_opacity`` 16 -> 15 keys.  The clip paths landed FIRST
    and expanded after, which stacked the landed key and the pose on one
    frame instead."""

    _Clip = TestKeysBatchAuditRegressions._Clip
    _Widget = TestKeysBatchAuditRegressions._Widget
    _host = TestKeysBatchAuditRegressions._host

    def setUp(self):
        cmds.file(new=True, force=True)

    def tearDown(self):
        ShotStore.clear_active()

    @staticmethod
    def _keys(node):
        t = cmds.keyframe(node, q=True, at="translateX") or []
        v = cmds.keyframe(node, q=True, at="translateX", valueChange=True) or []
        return [(round(a, 3), round(b, 3)) for a, b in zip(t, v)]

    def _scene(self, shots, keys):
        node = cmds.polyCube(name="seamNb")[0]
        for t, v in keys:
            cmds.setKeyframe(node, at="translateX", t=t, v=v)
        seq = ShotSequencer(
            [ShotBlock(i, n, s, e, [node]) for i, (n, s, e) in enumerate(shots)]
        )
        return node, seq

    def _drag_keys(self, shots, keys, shot_id, changes):
        node, seq = self._scene(shots, keys)
        clips = {
            1: self._Clip({"obj": node, "attr_name": "translateX", "shot_id": shot_id})
        }
        self._host(clips, seq).on_keys_batch_moved([(1, changes)])
        return seq, self._keys(node)

    def test_a_key_onto_the_next_shot_s_keyed_start(self):
        seq, got = self._drag_keys(
            [("A", 0, 50), ("B", 65, 100)],
            ((10, 0), (40, 1), (65, 1), (80, 2)),
            0,
            [(40.0, 65.0)],
        )
        self.assertEqual(
            [(s.start, s.end) for s in seq.sorted_shots()],
            [(0.0, 65.0), (80.0, 115.0)],
        )
        self.assertEqual(got, [(10.0, 0.0), (65.0, 1.0), (80.0, 1.0), (95.0, 2.0)])

    def test_an_unequal_opening_pose_stays_on_the_neighbour_s_start(self):
        _seq, got = self._drag_keys(
            [("A", 0, 50), ("B", 65, 100)],
            ((10, 0), (40, 1), (65, 7), (80, 2)),
            0,
            [(40.0, 65.0)],
        )
        self.assertEqual(
            got,
            [(10.0, 0.0), (65.0, 1.0), (80.0, 7.0), (95.0, 2.0)],
            "B opens on its own pose at its new start",
        )

    def test_a_key_onto_the_previous_shot_s_keyed_end(self):
        seq, got = self._drag_keys(
            [("P", 0, 35), ("A", 50, 100)],
            ((5, 0), (35, 4), (60, 2), (90, 3)),
            1,
            [(60.0, 35.0)],
        )
        self.assertEqual(
            [(s.start, s.end) for s in seq.sorted_shots()],
            [(-15.0, 20.0), (35.0, 100.0)],
        )
        self.assertEqual(
            got,
            [(-10.0, 0.0), (20.0, 4.0), (35.0, 2.0), (90.0, 3.0)],
            "P closes on its own pose at its new end",
        )

    def test_a_key_dragged_inside_the_next_shot_moves_it_whole(self):
        _seq, got = self._drag_keys(
            [("A", 0, 50), ("B", 65, 100)],
            ((10, 0), (40, 1), (65, 1), (70, 2), (80, 3)),
            0,
            [(40.0, 70.0)],
        )
        self.assertEqual(
            got,
            [(10.0, 0.0), (70.0, 1.0), (85.0, 1.0), (90.0, 2.0), (100.0, 3.0)],
            "the keys the bound now covers are B's, not A's to keep",
        )

    def test_a_sub_row_clip_landing_on_the_keyed_start(self):
        node, seq = self._scene(
            [("A", 0, 50), ("B", 65, 100)],
            ((10, 0), (30, 5), (40, 1), (65, 7), (80, 2)),
        )
        clips = {
            1: self._Clip(
                {
                    "obj": node,
                    "attr_name": "translateX",
                    "shot_id": 0,
                    "orig_start": 30.0,
                    "orig_end": 40.0,
                }
            )
        }
        host = self._host(clips, seq)
        host._shifted_out_keys = {}
        host.on_clip_moved(1, 55.0)
        self.assertEqual(
            self._keys(node),
            [(10.0, 0.0), (55.0, 5.0), (65.0, 1.0), (80.0, 7.0), (95.0, 2.0)],
            "the clip lands after B has moved: nothing stacks on 65",
        )

    def test_a_stepped_clip_landing_on_the_keyed_start(self):
        node, seq = self._scene(
            [("A", 0, 50), ("B", 65, 100)], ((10, 0), (40, 1), (65, 7), (80, 2))
        )
        # A stepped clip is a held key: move_stepped_keys moves only those.
        cmds.keyTangent(node, at="translateX", time=(40, 40), outTangentType="step")
        clips = {
            1: self._Clip(
                {
                    "obj": node,
                    "shot_id": 0,
                    "orig_start": 40.0,
                    "orig_end": 40.0,
                    "is_stepped": True,
                }
            )
        }
        host = self._host(clips, seq)
        host._shifted_out_keys = {}
        host.on_clip_moved(1, 65.0)
        self.assertEqual(
            self._keys(node),
            [(10.0, 0.0), (65.0, 1.0), (80.0, 7.0), (95.0, 2.0)],
            "the stepped key lands after B has moved: B's pose is not overwritten",
        )

    def _clip_host(self, seq, data):
        host = self._host({1: self._Clip(data)}, seq)
        host._shifted_out_keys = {}
        host._audio_segments_cache = None
        return host

    # -- point (stepped) clips: the drag moves what the mark was drawn from --

    def _point_scene(self, build):
        """A flat member (every curve holds still in A) drawn as one point
        clip at 25.  Each curve carries an equal key before every shot (where no
        ripple reaches): a single-key curve is a zero-length SPAN, not a mark."""
        mover = cmds.spaceLocator(name="ptMover")[0]
        for t, v in ((0, 0.0), (50, 10.0), (60, 0.0), (100, 5.0)):
            cmds.setKeyframe(mover, at="translateX", t=t, v=v)
        hold = cmds.spaceLocator(name="ptHold")[0]
        build(hold)
        seq = ShotSequencer(
            [
                ShotBlock(0, "A", 0, 50, [mover, hold]),
                ShotBlock(1, "B", 60, 100, [mover]),
            ]
        )
        drawn = [s for s in seq.collect_object_segments(0) if s["obj"] == hold]
        self.assertEqual(
            [(s["start"], s.get("is_stepped")) for s in drawn],
            [(25.0, True)],
            "fixture: one point clip is drawn at 25",
        )
        return hold, seq

    def _drag_point(self, hold, seq, to):
        data = {
            "obj": hold,
            "shot_id": 0,
            "orig_start": 25.0,
            "orig_end": 25.0,
            "is_stepped": True,
            "stepped_key_time": 25.0,
        }
        self._clip_host(seq, data).on_clip_moved(1, to)

    @staticmethod
    def _plain(node):
        for t in (-300, 25):  # Move to Shot's lone arrival, flat to a far key
            cmds.setKeyframe(node, at="translateY", t=t, v=3.0)

    @staticmethod
    def _stepped(node):
        for t in (-300, 25):
            cmds.setKeyframe(node, at="visibility", t=t, v=1.0)
        cmds.keyTangent(f"{node}.visibility", e=True, outTangentType="step")

    @staticmethod
    def _times(node, attr):
        return cmds.keyframe(f"{node}.{attr}", q=True, timeChange=True) or []

    def test_a_point_clip_on_a_plain_key_moves_it(self):
        """BACKLOG 2026-10-04, reproduced in a fresh mayapy: the drag moved
        only keys with a ``step`` out-tangent, so a mark on a plain key -- a
        Move to Shot arrival -- moved nothing and snapped back."""
        hold, seq = self._point_scene(self._plain)
        self._drag_point(hold, seq, 30.0)
        self.assertEqual(self._times(hold, "translateY"), [-300.0, 30.0])

    def test_a_point_clip_dragged_past_the_end_lands_where_the_shot_grew(self):
        """The same drag past A's end grew A and rippled B -- for a key that
        then stayed where it was."""
        hold, seq = self._point_scene(self._plain)
        self._drag_point(hold, seq, 55.0)
        self.assertEqual(
            [(s.start, s.end) for s in seq.sorted_shots()],
            [(0.0, 55.0), (65.0, 105.0)],
        )
        self.assertEqual(self._times(hold, "translateY"), [-300.0, 55.0])

    def test_a_point_clip_moves_every_key_its_mark_was_drawn_from(self):
        """A stepped and a plain key share the mark: both go, so the mark
        does not split in two."""

        def build(node):
            self._stepped(node)
            self._plain(node)

        hold, seq = self._point_scene(build)
        self._drag_point(hold, seq, 30.0)
        self.assertEqual(self._times(hold, "visibility"), [-300.0, 30.0])
        self.assertEqual(self._times(hold, "translateY"), [-300.0, 30.0])

    def test_a_point_clip_keeps_its_keys_tangents(self):
        """The drag recreates the key twice (lifted clear, then landed), and
        restored only its tangent TYPES: a fixed, weighted tangent lost its
        angles and weights on the way.  Only stepped keys took this path
        before any mark could be dragged (review 2026-10-05)."""

        def build(node):
            self._plain(node)
            crv = cmds.listConnections(f"{node}.translateY", type="animCurve")[0]
            cmds.keyTangent(crv, e=True, weightedTangents=True)
            tt = (25, 25)
            cmds.keyTangent(crv, e=True, time=tt, lock=False, weightLock=False)
            cmds.keyTangent(crv, e=True, time=tt, itt="fixed", ott="fixed")
            cmds.keyTangent(crv, e=True, time=tt, inAngle=-10.0, outAngle=30.0)
            cmds.keyTangent(crv, e=True, time=tt, inWeight=4.0, outWeight=7.5)

        def record(node, t):
            flags = ("itt", "ott", "inAngle", "outAngle", "inWeight", "outWeight")
            out = []
            for flag in flags:
                got = cmds.keyTangent(
                    f"{node}.translateY", q=True, time=(t, t), **{flag: True}
                )[0]
                out.append(round(got, 3) if isinstance(got, float) else got)
            return out

        hold, seq = self._point_scene(build)
        before = record(hold, 25)
        self.assertEqual(before, ["fixed", "fixed", -10.0, 30.0, 4.0, 7.5], "fixture")
        self._drag_point(hold, seq, 30.0)
        self.assertEqual(self._times(hold, "translateY"), [-300.0, 30.0])
        self.assertEqual(record(hold, 30), before, "angles and weights arrive")

    def test_a_point_clip_on_a_stepped_key_moves_as_it_did(self):
        """Real stepped keys keep their established drag: the key and its
        ``step`` arrive together."""
        hold, seq = self._point_scene(self._stepped)
        self._drag_point(hold, seq, 30.0)
        self.assertEqual(self._times(hold, "visibility"), [-300.0, 30.0])
        self.assertEqual(
            cmds.keyTangent(
                f"{hold}.visibility", q=True, time=(30, 30), outTangentType=True
            ),
            ["step"],
        )

    def test_a_sub_row_clip_reaching_into_the_neighbour_moves_as_one(self):
        """Review 2026-09-22: a sub-row run can outlast its shot.  Made room
        for before it moved, the part inside the neighbour's envelope rode the
        neighbour's ripple (+17) instead of the drag (+2); the clip is now
        lifted out of every ripple window first."""
        node, seq = self._scene(
            [("A", 0, 50), ("B", 60, 100)],
            ((10, 0), (45, 1), (65, 2), (80, 3)),
        )
        data = {
            "obj": node,
            "attr_name": "translateX",
            "shot_id": 0,
            "orig_start": 45.0,
            "orig_end": 65.0,
        }
        self._clip_host(seq, data).on_clip_moved(1, 47.0)
        self.assertEqual(
            [(s.start, s.end) for s in seq.sorted_shots()],
            [(0.0, 67.0), (77.0, 117.0)],
        )
        self.assertEqual(
            self._keys(node), [(10.0, 0.0), (47.0, 1.0), (67.0, 2.0), (97.0, 3.0)]
        )

    def test_a_clip_dragged_far_back_is_not_met_by_the_ripple(self):
        """Dragged back past its shot's start, a clip grows the shot's head,
        and that ripples the shots before it back as far.  Lifted only below
        every shot's start, the clip sat where a long enough drag rippled the
        previous shot onto it -- the planner refused that ripple, and the drag
        came back declined."""
        node, seq = self._scene(
            [("A", 0, 50), ("B", 60, 100)], ((10, 0), (40, 1), (70, 5), (90, 6))
        )
        data = {
            "obj": node,
            "attr_name": "translateX",
            "shot_id": 1,
            "orig_start": 70.0,
            "orig_end": 90.0,
        }
        self._clip_host(seq, data).on_clip_moved(1, -980.0)
        self.assertEqual(
            [(s.start, s.end) for s in seq.sorted_shots()],
            [(-1040.0, -990.0), (-980.0, 100.0)],
        )
        self.assertEqual(
            self._keys(node),
            [(-1030.0, 0.0), (-1000.0, 1.0), (-980.0, 5.0), (-960.0, 6.0)],
        )

    def test_a_sub_row_clip_carries_its_keys_claims(self):
        """A claim is a (curve, time) pair, so it moves with its key -- as the
        key drag's always did.  The sub-row move shifted the keys alone, and
        the system could no longer find its own sample where it now sits."""
        node, seq = self._scene(
            [("A", 0, 50), ("B", 60, 100)], ((10, 0), (30, 5), (40, 1), (80, 2))
        )
        crv = cmds.listConnections(f"{node}.translateX", type="animCurve")[0]
        seq.ledger.record_key(crv, 40.0)
        data = {
            "obj": node,
            "attr_name": "translateX",
            "shot_id": 0,
            "orig_start": 30.0,
            "orig_end": 40.0,
        }
        self._clip_host(seq, data).on_clip_moved(1, 32.0)
        self.assertEqual(
            self._keys(node), [(10.0, 0.0), (32.0, 5.0), (42.0, 1.0), (80.0, 2.0)]
        )
        self.assertEqual(seq.ledger.key_times(crv), [42.0])

    def _audio_scene(self, shots, keys, track="vo"):
        seq = ShotSequencer(
            [ShotBlock(i, n, s, e, []) for i, (n, s, e) in enumerate(shots)]
        )
        AudioUtils.ensure_track_attr(track)
        for frame, value in keys:
            AudioUtils.write_key(track, frame, value=value)
        return seq

    def test_an_audio_clip_reaching_into_the_neighbour_moves_as_one(self):
        """Review 2026-09-22: an audio segment is track-wide -- its clip shows
        only the part inside the shot -- so its stop key can sit in the next
        shot's envelope, where the ripple moved it +17 while the drag was +2."""
        seq = self._audio_scene([("A", 0, 50), ("B", 60, 100)], ((45, 1), (65, 0)))
        data = {
            "is_audio": True,
            "audio_track_id": "vo",
            "shot_id": 0,
            "orig_start": 45.0,
            "orig_end": 65.0,
            "vis_start": 45.0,
        }
        self._clip_host(seq, data).on_clip_moved(1, 47.0)
        self.assertEqual(
            [(s.start, s.end) for s in seq.sorted_shots()],
            [(0.0, 67.0), (77.0, 117.0)],
        )
        self.assertEqual(AudioUtils.read_keys("vo"), [(47.0, 1.0), (67.0, 0.0)])

    def test_an_audio_clip_moves_by_what_its_visible_part_moved(self):
        """The clip draws the segment's part inside its shot and a drag
        reports where THAT landed; measured from the segment's own start the
        move was off by the part before the shot (+7 for a +2 drag here).  Nor
        does the shot grow back over that earlier part: enclosing the
        segment's own start (57) rippled the previous shot the other way."""
        seq = self._audio_scene(
            [("A", 0, 50), ("B", 60, 100)], ((55, 1), (70, 0)), track="sfx"
        )
        data = {
            "is_audio": True,
            "audio_track_id": "sfx",
            "shot_id": 1,
            "orig_start": 55.0,
            "orig_end": 70.0,
            "vis_start": 60.0,
        }
        self._clip_host(seq, data).on_clip_moved(1, 62.0)
        self.assertEqual(AudioUtils.read_keys("sfx"), [(57.0, 1.0), (72.0, 0.0)])
        self.assertEqual(
            [(s.start, s.end) for s in seq.sorted_shots()],
            [(0.0, 50.0), (60.0, 100.0)],
            "no shot moved",
        )


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestALandingOnAContiguousSeamGrowsItsShotAFrame(unittest.TestCase):
    """Two shots that touch share ONE sample, the preceding shot's, so a key
    landing on that frame takes the neighbour's opening pose.

    Measured 2026-09-23 through this handler (BACKLOG 2026-09-22): A [0,50]
    and B [50,100], A's key dragged 40 -> 60 grew A to 60 and rippled B to
    [60,110] -- the key landed on B's first frame, B opened on A's pose and its
    own slipped to 61; equal poses still left a duplicate. Decided by the
    maintainer: the shot grows ONE frame past the seam
    (``ShotStore.enclosing_bounds``), so the shots still touch and the
    neighbour keeps its pose. A landing on the existing seam also needed the
    push to MERGE the old seam pose into the neighbour's identical opening
    pose rather than shove both a frame on (``_clear_destination``)."""

    _Clip = TestKeysBatchAuditRegressions._Clip
    _Widget = TestKeysBatchAuditRegressions._Widget
    _host = TestKeysBatchAuditRegressions._host
    _keys = staticmethod(TestADragOntoAKeyedNeighbourLeavesItWhole._keys)
    _scene = TestADragOntoAKeyedNeighbourLeavesItWhole._scene
    _drag_keys = TestADragOntoAKeyedNeighbourLeavesItWhole._drag_keys

    KEYS = ((10, 0), (40, 5), (50, 3), (70, 9), (90, 2))
    SHOTS = [("A", 0, 50), ("B", 50, 100)]

    def setUp(self):
        cmds.file(new=True, force=True)

    def tearDown(self):
        ShotStore.clear_active()

    def _bounds(self, seq):
        return [(s.start, s.end) for s in seq.sorted_shots()]

    def test_a_key_past_the_end_leaves_the_neighbour_its_opening_pose(self):
        seq, got = self._drag_keys(self.SHOTS, self.KEYS, 0, [(40.0, 60.0)])
        self.assertEqual(self._bounds(seq), [(0.0, 61.0), (61.0, 111.0)])
        self.assertEqual(got, [(10, 0), (50, 3), (60, 5), (61, 3), (81, 9), (101, 2)])

    def test_equal_poses_keep_their_frames(self):
        keys = ((10, 0), (40, 5), (50, 5), (70, 9), (90, 2))
        seq, got = self._drag_keys(self.SHOTS, keys, 0, [(40.0, 60.0)])
        self.assertEqual(self._bounds(seq), [(0.0, 61.0), (61.0, 111.0)])
        self.assertEqual(got, [(10, 0), (50, 5), (60, 5), (61, 5), (81, 9), (101, 2)])

    def test_a_key_onto_the_existing_seam_leaves_the_neighbour_whole(self):
        """The old seam pose merges into the neighbour's identical opening
        pose; pushed instead, it shoved that pose a frame into B's motion."""
        seq, got = self._drag_keys(self.SHOTS, self.KEYS, 0, [(40.0, 50.0)])
        self.assertEqual(self._bounds(seq), [(0.0, 51.0), (51.0, 101.0)])
        self.assertEqual(got, [(10, 0), (50, 5), (51, 3), (71, 9), (91, 2)])

    def test_a_key_dragged_back_over_the_seam_mirrors_it(self):
        seq, got = self._drag_keys(self.SHOTS, self.KEYS, 1, [(70.0, 45.0)])
        self.assertEqual(self._bounds(seq), [(-6.0, 44.0), (44.0, 100.0)])
        self.assertEqual(got, [(4, 0), (34, 5), (44, 3), (45, 9), (50, 3), (90, 2)])

    def test_a_landing_off_the_seam_is_unchanged(self):
        seq, got = self._drag_keys(self.SHOTS, self.KEYS, 0, [(40.0, 59.5)])
        self.assertEqual(self._bounds(seq), [(0.0, 60.0), (60.0, 110.0)])
        self.assertEqual(got, [(10, 0), (50, 3), (59.5, 5), (60, 3), (80, 9), (100, 2)])

    def _drag_object_clip(self, shots, keys, orig, new_start):
        """A main-track (object) clip drag: ``move_object_in_shot``."""
        node, seq = self._scene(shots, keys)
        data = {"obj": node, "shot_id": 0, "orig_start": orig[0], "orig_end": orig[1]}
        host = self._host({1: self._Clip(data)}, seq)
        host._shifted_out_keys = {}
        host.on_clip_moved(1, new_start)
        return seq, self._keys(node)

    def test_an_object_clip_past_the_end_leaves_the_neighbour_its_opening_pose(self):
        """A main-track clip grows through ``move_object_in_shot``, which sized
        the bound itself -- rounded, never stepped -- so the same landing
        opened B on the dragged pose (in blendertk, one of the two was lost)."""
        seq, got = self._drag_object_clip(self.SHOTS, self.KEYS, (10.0, 40.0), 30.0)
        self.assertEqual(self._bounds(seq), [(0.0, 61.0), (61.0, 111.0)])
        self.assertEqual(got, [(30, 0), (60, 5), (61, 3), (81, 9), (101, 2)])

    def test_an_object_clip_onto_the_existing_seam_leaves_the_neighbour_whole(self):
        seq, got = self._drag_object_clip(self.SHOTS, self.KEYS, (10.0, 40.0), 20.0)
        self.assertEqual(self._bounds(seq), [(0.0, 51.0), (51.0, 101.0)])
        self.assertEqual(got, [(20, 0), (50, 5), (51, 3), (71, 9), (91, 2)])

    def test_an_object_clip_dragged_back_over_the_seam_mirrors_it(self):
        """B's clip back to 45: B grows to 44 and A ripples to [-6, 44], its
        closing pose -- left in B's landing zone -- pushed onto its new end."""
        node, seq = self._scene(self.SHOTS, self.KEYS)
        data = {"obj": node, "shot_id": 1, "orig_start": 70.0, "orig_end": 90.0}
        host = self._host({1: self._Clip(data)}, seq)
        host._shifted_out_keys = {}
        host.on_clip_moved(1, 45.0)
        self.assertEqual(self._bounds(seq), [(-6.0, 44.0), (44.0, 100.0)])
        self.assertEqual(self._keys(node), [(4, 0), (34, 5), (44, 3), (45, 9), (65, 2)])

    def test_an_object_clip_onto_an_unkeyed_seam_steps_nothing(self):
        seq, got = self._drag_object_clip(
            [("A", 0, 30), ("B", 30, 60)],
            ((10, 0), (20, 1), (40, 2), (55, 3)),
            (10.0, 20.0),
            20.0,
        )
        self.assertEqual(self._bounds(seq), [(0.0, 30.0), (30.0, 60.0)])
        self.assertEqual([t for t, _v in got], [20.0, 30.0, 40.0, 55.0])


class TestMoveToShotTakesEveryVisibleClip(unittest.TestCase):
    """ "Move to shot sometimes fails" (2026-08-29): the converter dropped
    stepped clips and clips of a non-active visible shot, so a selection made
    of those produced nothing to move -- "you cannot move a clip you can see".
    A stepped clip is one key and moves as one; a read-only clip is only
    read-only for DRAGS, which assume the active shot."""

    class _Clip:
        def __init__(self, **data):
            self.data = data

    class _Widget:
        def __init__(self, clips):
            self._clips = clips

        def get_clip(self, cid):
            return self._clips.get(cid)

    def _ctl(self):
        class _Ctl(ShotSequencerController):
            def __init__(self):
                pass

        return _Ctl()

    def test_stepped_and_read_only_clips_become_sequences(self):
        widget = self._Widget(
            {
                1: self._Clip(obj="a", orig_start=10.0, orig_end=30.0),
                2: self._Clip(obj="a", is_stepped=True, orig_start=45.0, orig_end=45.0),
                3: self._Clip(obj="b", read_only=True, orig_start=70.0, orig_end=90.0),
                4: self._Clip(obj="c", orig_start=5.0, orig_end=5.0),  # empty span
            }
        )
        ctl = self._ctl()
        seqs = ctl._clips_to_sequences(widget, [1, 2, 3, 4], include_read_only=True)
        self.assertEqual([q["obj"] for q in seqs], ["a", "a", "b"])
        stepped = seqs[1]
        self.assertEqual(
            (stepped["times"], stepped["start"], stepped["end"]), ([45.0], 45.0, 45.0)
        )
        self.assertNotIn("times", seqs[0], "a span moves as a span")

    def test_drags_still_leave_other_shots_clips_alone(self):
        widget = self._Widget(
            {3: self._Clip(obj="b", read_only=True, orig_start=70.0, orig_end=90.0)}
        )
        self.assertEqual(self._ctl()._clips_to_sequences(widget, [3]), [])


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestBoundHandleGrammar(unittest.TestCase):
    """The modifier grammar as the controller applies it.  The shot's own
    edge never moves the shot's keys: a plain drag moves the bound and the
    neighbours ripple with their keys (gaps kept); Ctrl moves the bound and
    nothing else (the shot grows into the gap over the keys there, or leaves
    keys behind); Shift retimes.  A gap's edge belongs to the shot beyond
    it: a plain drag slides that shot alone, Ctrl moves that bound only,
    Shift retimes it.  Set 2026-09-06, after a first cut made the plain
    edge drag slide the whole shot."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.a = cmds.spaceLocator(name="grammar_a")[0]
        self.b = cmds.spaceLocator(name="grammar_b")[0]
        for t, v in ((10, 0), (40, 5)):
            cmds.setKeyframe(self.a, at="translateX", t=t, v=v)
        for t, v in ((70, 0), (90, 5)):
            cmds.setKeyframe(self.b, at="translateX", t=t, v=v)
        self.seq = ShotSequencer(
            [ShotBlock(0, "A", 0, 50, [self.a]), ShotBlock(1, "B", 60, 100, [self.b])]
        )
        self.ctl = self._ctl()

    def tearDown(self):
        ShotStore.clear_active()

    def _ctl(self):
        seq = self.seq

        class _Widget:
            ctrl_held_at_press = False
            shift_held_at_press = False

        widget = _Widget()

        class _Ctl(ShotSequencerController):
            def __init__(self):  # bypass the panel's __init__
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._audio_segments_cache = None
                self._syncing = False

            sequencer = seq
            active_shot_id = 0

            def _get_sequencer_widget(self):
                return widget

            def _gap_edit_epilogue(self):
                pass

        ctl = _Ctl()
        ctl.widget = widget
        return ctl

    def _keys(self, obj):
        return cmds.keyframe(obj, q=True, at="translateX") or []

    def _bounds(self):
        return [(s.start, s.end) for s in self.seq.sorted_shots()]

    @staticmethod
    def _node(name):
        return cmds.ls(name, long=True)[0]

    def _members(self, shot_id):
        """The shot's members as long paths: one node may be listed short or long."""
        return cmds.ls(self.seq.shot_by_id(shot_id).objects, long=True) or []

    def _hold(self, ctrl=False, shift=False):
        self.ctl.widget.ctrl_held_at_press = ctrl
        self.ctl.widget.shift_held_at_press = shift

    # ---- the active shot's own edge (range highlight) ---------------------

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_plain_edge_drag_moves_the_bound_and_ripples_the_neighbours(self):
        self._hold()
        self.ctl.on_range_highlight_changed(0, 60)  # end +10, start untouched
        self.assertEqual(self._bounds(), [(0.0, 60.0), (70.0, 110.0)])
        self.assertEqual(self._keys(self.a), [10.0, 40.0], "the shot's keys stay")
        self.assertEqual(self._keys(self.b), [80.0, 100.0], "B rippled, gap kept")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_edge_drag_moves_the_bound_and_nothing_else(self):
        self._hold(ctrl=True)
        self.ctl.on_range_highlight_changed(0, 58)  # end +8, into the gap
        self.assertEqual(self._bounds(), [(0.0, 58.0), (60.0, 100.0)])
        self.assertEqual(self._keys(self.a), [10.0, 40.0])
        self.assertEqual(self._keys(self.b), [70.0, 90.0], "B did not move")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_edge_drag_pushes_into_the_next_shot(self):
        """Dragged past the neighbour's start, the bound takes the gap AND the
        neighbour's head: the neighbour's start gives way, every key stays,
        and the object moving in the frames taken becomes this shot's member.
        It used to hold at the neighbour, which at a gap of zero meant Ctrl
        could not grow the shot at all (2026-10-06: "neither holding shift or
        ctrl ... allows for me to drag to encompass keys in the adjacent
        shot so they become members of the current shot")."""
        self._hold(ctrl=True)
        self.ctl.on_range_highlight_changed(0, 75)
        self.assertEqual(self._bounds(), [(0.0, 75.0), (75.0, 100.0)])
        self.assertEqual(self._keys(self.a), [10.0, 40.0])
        self.assertEqual(self._keys(self.b), [70.0, 90.0], "no key moved")
        self.assertIn(self._node(self.b), self._members(0))
        self.assertIn(self._node(self.b), self._members(1), "still moves in B")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_edge_drag_at_a_zero_gap_moves_the_seam(self):
        """Flush shots share their bound, so Ctrl moves the seam: growing takes
        the neighbour's head, shrinking hands this shot's tail to it."""
        self.seq.shot_by_id(1).start = 50.0
        self._hold(ctrl=True)
        self.ctl.on_range_highlight_changed(0, 75)
        self.assertEqual(self._bounds(), [(0.0, 75.0), (75.0, 100.0)])
        self.ctl.on_range_highlight_changed(0, 30)
        self.assertEqual(self._bounds(), [(0.0, 30.0), (30.0, 100.0)])
        self.assertEqual(self._keys(self.a), [10.0, 40.0])
        self.assertIn(self._node(self.a), self._members(1), "A's tail went to B")
        self.assertIn(self._node(self.a), self._members(0), "A's head stayed")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_edge_drag_leaves_the_neighbour_a_frame(self):
        self._hold(ctrl=True)
        self.ctl.on_range_highlight_changed(0, 140)
        self.assertEqual(self._bounds(), [(0.0, 99.0), (99.0, 100.0)])

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_edge_drag_takes_the_keys_it_covers(self):
        """A key in the gap becomes this shot's once the bound covers it."""
        cmds.setKeyframe(self.b, at="translateX", t=55, v=1)  # a key in the gap
        self._hold(ctrl=True)
        self.ctl.on_range_highlight_changed(0, 58)
        self.assertEqual(self._bounds()[0], (0.0, 58.0))
        self.assertEqual(
            self.seq._source_shot_id_for({"start": 55.0, "end": 55.0}),
            0,
            "the covered key is this shot's now",
        )

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_shift_edge_drag_retimes_the_keys_into_the_new_span(self):
        self._hold(shift=True)
        self.ctl.on_range_highlight_changed(0, 100)  # doubled
        self.assertEqual(self._bounds()[0], (0.0, 100.0))
        self.assertEqual(self._keys(self.a), [20.0, 80.0])

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_band_body_drag_is_a_move_whatever_is_held(self):
        self._hold(ctrl=True)
        self.ctl.on_range_highlight_changed(5, 55)  # both edges +5
        self.assertEqual(self._bounds()[0], (5.0, 55.0))
        self.assertEqual(self._keys(self.a), [15.0, 45.0])

    # ---- a gap's edges, on a shot that is NOT active -----------------------

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_plain_gap_edge_drag_slides_the_shot_beyond_it(self):
        self._hold()
        self.ctl.on_gap_resized(60, 70)  # B's start dragged +10
        self.assertEqual(self._bounds(), [(0.0, 50.0), (70.0, 110.0)])
        self.assertEqual(self._keys(self.b), [80.0, 100.0])
        self.assertEqual(self._keys(self.a), [10.0, 40.0], "A untouched")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_plain_gap_edge_drag_moves_that_shot_alone(self):
        """A gap handle changes the gap and nothing else: the shot beyond it
        slides, the shots beyond THAT stay -- the ripple is the shot handle's."""
        c = cmds.spaceLocator(name="grammar_c")[0]
        cmds.setKeyframe(c, at="translateX", t=130, v=1)
        self.seq.store.define_shot("C", 120, 150, objects=[c])
        self._hold()
        self.ctl.on_gap_resized(60, 70)
        self.assertEqual(self._bounds(), [(0.0, 50.0), (70.0, 110.0), (120.0, 150.0)])
        self.assertEqual(self._keys(c), [130.0])
        self.ctl.on_gap_resized(70, 100)  # asked past C: clamped against it
        self.assertEqual(self._bounds()[1], (80.0, 120.0))

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_retime_scales_content_the_list_never_named(self):
        """Membership is a label: the Shift retime acts on what is keyed in
        the span, listed or not (the production pulse was not)."""
        loose = cmds.spaceLocator(name="grammar_loose")[0]
        for t, v in ((10, 0), (40, 1)):
            cmds.setKeyframe(loose, at="translateX", t=t, v=v)
        self._hold(shift=True)
        self.ctl.on_range_highlight_changed(0, 100)
        self.assertEqual(self._keys(loose), [20.0, 80.0])

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_set_shot_duration_ripples_before_it_scales(self):
        """The other two retimes share resize_shot's order: a key scaled past
        the old end into the neighbour's window must not ride the ripple."""
        self.seq.set_shot_duration(0, 100)
        self.assertEqual(self._bounds(), [(0.0, 100.0), (110.0, 150.0)])
        self.assertEqual(self._keys(self.a), [20.0, 80.0])
        self.assertEqual(self._keys(self.b), [120.0, 140.0])

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_resize_object_ripples_before_it_scales(self):
        self.seq.resize_object(0, self.a, 10, 40, 10, 80)
        self.assertEqual(self._bounds(), [(0.0, 80.0), (90.0, 130.0)])
        self.assertEqual(self._keys(self.a), [10.0, 80.0])
        self.assertEqual(self._keys(self.b), [100.0, 120.0])

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_gap_edge_drag_moves_that_bound_only(self):
        self._hold(ctrl=True)
        self.ctl.on_gap_resized(60, 70)
        self.assertEqual(self._bounds(), [(0.0, 50.0), (70.0, 100.0)])
        self.assertEqual(self._keys(self.b), [70.0, 90.0])

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_gap_edge_drag_pushes_past_the_shot_before(self):
        """The same Ctrl rule from the gap's side: B's start dragged over the
        whole gap and into A takes A's tail, A's end giving way."""
        self._hold(ctrl=True)
        self.ctl.on_gap_resized(60, 30)
        self.assertEqual(self._bounds(), [(0.0, 30.0), (30.0, 100.0)])
        self.assertEqual(self._keys(self.a), [10.0, 40.0])
        self.assertIn(self._node(self.a), self._members(1))

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_shift_gap_edge_drag_retimes_that_shot(self):
        self._hold(shift=True)
        self.ctl.on_gap_resized(60, 80)  # B [60,100] -> [80,100]: half as long
        self.assertEqual(self._bounds()[1], (80.0, 100.0))
        self.assertEqual(self._keys(self.b), [85.0, 95.0])

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_the_active_shot_follows_the_same_grammar_on_a_gap_edge(self):
        """The old inner/outer split -- the ACTIVE shot's edge was a bound
        move, any other shot slid -- is gone: the modifier decides."""
        self._hold()
        self.ctl.on_gap_left_resized(50, 60)  # A's end (A is active) +10
        self.assertEqual(self._bounds()[0], (10.0, 60.0))
        self.assertEqual(self._keys(self.a), [20.0, 50.0])

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_the_tail_cap_moves_the_last_shots_end_only(self):
        """The cap after the last shot is that shot's OWN bound, not a gap
        edge: a plain drag moves the bound and nothing else -- it used to
        slide the whole shot, which read as the border misbehaving
        (2026-09-09)."""
        self._hold()
        self.ctl.on_gap_left_resized(100, 110)  # B's end, nothing beyond it
        self.assertEqual(self._bounds(), [(0.0, 50.0), (60.0, 110.0)])
        self.assertEqual(self._keys(self.b), [70.0, 90.0], "B's keys stay")
        self.assertEqual(self._keys(self.a), [10.0, 40.0], "the timeline did not walk")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_tail_handle_drag_moves_the_end_only(self):
        self._hold(ctrl=True)
        self.ctl.on_gap_left_resized(100, 110)
        self.assertEqual(self._bounds()[1], (60.0, 110.0))
        self.assertEqual(self._keys(self.b), [70.0, 90.0])


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestABoundEnclosesFractionalContent(unittest.TestCase):
    """A key dragged past a shot's end grows the shot around it to a whole
    frame that ENCLOSES it (the panel's half of mayatk's
    ``TestABoundEnclosesFractionalContent``, whose engine rules -- the trim,
    the plain shrink, Move to Shot's grow -- stay there).
    Fixed: 2026-09-19
    """

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def setUp(self):
        cmds.file(new=True, force=True)
        self.a = cmds.polyCube(name="frA")[0]
        for t, v in ((10.6, 0), (25, 5), (40.4, 2)):
            cmds.setKeyframe(self.a, at="translateX", t=t, v=v)
        self.b = cmds.polyCube(name="frB")[0]
        for t, v in ((70, 0), (90, 5)):
            cmds.setKeyframe(self.b, at="translateX", t=t, v=v)
        self.seq = ShotSequencer(
            [
                ShotBlock(0, "A", 0, 50, [self.a]),
                ShotBlock(1, "B", 60, 100, [self.b]),
            ]
        )

    def tearDown(self):
        ShotStore.clear_active()

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_key_dragged_past_the_end_is_enclosed(self):
        # The drag landed a key at 50.4, past A's end: A grows around it.
        cmds.setKeyframe(self.a, at="translateX", t=50.4, v=3)
        TestBoundHandleGrammar._ctl(self)._expand_shot_range(0, 10.6, 50.4)
        self.assertEqual(
            [(s.start, s.end) for s in self.seq.sorted_shots()],
            [(0.0, 51.0), (61.0, 101.0)],
        )
        self.assertEqual(
            cmds.keyframe(self.b, q=True, at="translateX"),
            [71.0, 91.0],
            "B rode the ripple whole",
        )


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestACtrlEdgeDragMovesNoSample(unittest.TestCase):
    """Ctrl on a shot's edge: the bound moves and NOTHING else does -- not the
    animator's keys, and not the shot system's own samples either.

    Bug: the Ctrl path reconciled with the default rule, under which a claimed
    sample FOLLOWS its bound.  A respace pin is a shape-preserving insert on a
    ramp, so moving it re-times the ramp: measured on a synthetic curve, a
    Ctrl grow of 3 frames changed 27 frames of playback, and one dragged past
    a gap key slid the pin OVER that key, reordering the curve.  Nothing moves
    in a Ctrl drag, so nothing can be in a sample's way: it stays, disowned.
    Fixed: 2026-09-19
    """

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def setUp(self):
        from mayatk.anim_utils._anim_utils import AnimUtils

        cmds.file(new=True, force=True)
        self.cube = cmds.polyCube(name="ctrl_pin_cube")[0]
        # A's content 10..40, a key in A's gap at 55, B's content 70..90.
        for t, v in ((10, 0), (40, 5), (55, 1), (70, 2), (90, 8)):
            cmds.setKeyframe(self.cube, at="translateX", t=t, v=v)
        self.crv = cmds.listConnections(f"{self.cube}.translateX", type="animCurve")[0]
        self.seq = ShotSequencer(
            [
                ShotBlock(0, "A", 0, 50, [self.cube]),
                ShotBlock(1, "B", 60, 100, [self.cube]),
            ]
        )
        # A claimed shape pin on A's end, planted as the respace plants one.
        for crv, t in AnimUtils.insert_keys([self.crv], [50.0], report=True):
            self.seq.ledger.record_key(crv, t, 0, "end")
        self.seq._enforce_gap_holds()  # so only the gesture is measured
        self.before = self._play()
        self.ctl = TestBoundHandleGrammar._ctl(self)
        self.ctl.widget.ctrl_held_at_press = True

    def tearDown(self):
        ShotStore.clear_active()

    def _play(self):
        return [
            round(cmds.keyframe(self.crv, q=True, eval=True, time=(f, f))[0], 4)
            for f in range(0, 101)
        ]

    def _assert_nothing_moved(self, label):
        now = self._play()
        off = [f for f, (a, b) in enumerate(zip(self.before, now)) if a != b]
        self.assertEqual(off, [], f"{label}: the curve plays differently")
        self.assertIn(50.0, cmds.keyframe(self.crv, q=True), "the pin stayed")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_grow_moves_the_bound_and_no_sample(self):
        self.ctl.on_range_highlight_changed(0, 53)
        self.assertEqual(self.seq.shot_by_id(0).end, 53.0)
        self._assert_nothing_moved("ctrl grow")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_grow_over_a_gap_key_reorders_nothing(self):
        self.ctl.on_range_highlight_changed(0, 57)
        self.assertEqual(self.seq.shot_by_id(0).end, 57.0)
        self._assert_nothing_moved("ctrl grow over 55")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_shrink_moves_the_bound_and_no_sample(self):
        self.ctl.on_range_highlight_changed(0, 45)
        self.assertEqual(self.seq.shot_by_id(0).end, 45.0)
        self._assert_nothing_moved("ctrl shrink")

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def test_a_ctrl_gap_edge_drag_moves_no_sample_either(self):
        self.ctl.active_shot_id = 1
        self.ctl.on_gap_left_resized(50, 45)  # A's end, from B's gap handle
        self.assertEqual(self.seq.shot_by_id(0).end, 45.0)
        self._assert_nothing_moved("ctrl gap edge")


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestALockedGapDoesNotResize(unittest.TestCase):
    """A lock is a statement about a gap's WIDTH.

    Bug: the lock was consulted by the respace planner and the overlay
    drawing, but by none of the drag handlers — so a locked gap resized
    like any other.  Both edge handles now refuse; the body drag (constant
    width) and a shot resize (which ripples, so the width survives) are
    unaffected.
    Fixed: 2026-09-03
    """

    @unittest.skipUnless(HAS_MAYA, "requires Maya")
    def setUp(self):
        cmds.file(new=True, force=True)
        ShotStore.clear_active()
        self.store = ShotStore()
        ShotStore.set_active(self.store)
        self.seq = ShotSequencer(store=self.store)
        self.a = self.store.define_shot("A", 0, 100)
        self.b = self.store.define_shot("B", 115, 200)
        self.ctl = self._ctl()

    def tearDown(self):
        ShotStore.clear_active()

    def _ctl(self):
        seq = self.seq
        footers = []

        class _Ctl(ShotSequencerController):
            def __init__(self):  # bypass the panel's __init__
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._audio_segments_cache = None
                self._syncing = False

            sequencer = seq
            active_shot_id = None

            def _get_sequencer_widget(self):
                return None

            def _set_footer(self, text, **kw):
                footers.append(text)

            def _gap_edit_epilogue(self):
                pass

        ctl = _Ctl()
        ctl.footers = footers
        return ctl

    def _bounds(self):
        return [(s.start, s.end) for s in self.seq.sorted_shots()]

    def test_a_locked_gaps_right_edge_refuses(self):
        self.store.lock_gap(self.a.shot_id, self.b.shot_id)
        before = self._bounds()
        self.ctl.on_gap_resized(115, 130)
        self.assertEqual(self._bounds(), before)
        self.assertTrue(any("locked" in f for f in self.ctl.footers))

    def test_a_locked_gaps_left_edge_refuses(self):
        self.store.lock_gap(self.a.shot_id, self.b.shot_id)
        before = self._bounds()
        self.ctl.on_gap_left_resized(100, 85)
        self.assertEqual(self._bounds(), before)
        self.assertTrue(any("locked" in f for f in self.ctl.footers))

    def test_an_unlocked_gap_still_resizes(self):
        self.ctl.on_gap_resized(115, 130)
        self.assertNotEqual(self._bounds(), [(0, 100), (115, 200)])

    def test_the_tail_handle_flanks_no_gap_and_is_never_locked(self):
        """The overlay after the LAST shot has no right-hand shot."""
        self.store.lock_all_gaps()
        self.ctl.on_gap_left_resized(200, 190)
        self.assertAlmostEqual(self.seq.shot_by_id(self.b.shot_id).end, 190)

    def test_the_lock_is_recorded_even_when_the_overlay_frames_have_drifted(self):
        """Bug: each gap edge was matched against a shot frame on its own, so
        an overlay whose cached span had drifted by more than a rounding
        resolved to nothing — and a lock that resolves to nothing is never
        written.  The overlay drew itself "[Locked]" while the store stayed
        empty, so the next rebuild handed the lock straight back and the gap
        dragged like any other.
        Fixed: 2026-09-03
        """
        self.ctl.on_gap_lock_changed(100.4, 114.6, True)  # drifted by ~0.5
        self.assertTrue(
            self.store.is_gap_locked(self.a.shot_id, self.b.shot_id),
            "the nearest pair is the gap the overlay is standing on",
        )
        self.ctl.on_gap_lock_changed(100.4, 114.6, False)
        self.assertFalse(self.store.is_gap_locked(self.a.shot_id, self.b.shot_id))

    def test_a_recorded_lock_then_refuses_the_drag(self):
        """The two halves in one pass: record it, then try to drag it."""
        self.ctl.on_gap_lock_changed(100.0, 115.0, True)
        before = self._bounds()
        self.ctl.on_gap_resized(115, 130)
        self.assertEqual(self._bounds(), before)

    def test_a_single_shot_timeline_flanks_no_gap(self):
        self.store.remove_shot(self.b.shot_id)
        self.ctl.on_gap_lock_changed(100.0, 115.0, True)
        self.assertFalse(self.store.locked_gaps)

    def test_locking_does_not_freeze_a_shot_resize(self):
        """The ripple carries the gap along, so its width is never at risk."""
        self.store.lock_gap(self.a.shot_id, self.b.shot_id)
        self.seq.resize_shot_bounds(self.a.shot_id, 0, 80)
        shots = self.seq.sorted_shots()
        self.assertAlmostEqual(shots[1].start - shots[0].end, 15.0)


class TestMarkerPersistence(unittest.TestCase):
    """A widget marker serializes into the store's marker dict
    (``MarkerManagerMixin._marker_to_dict``) with every field it has.  The
    reverse -- a legacy dict read with defaults -- is
    ``test_sequencer_gui.TestToolMarkersOnTheTimeline``, through the real
    widget sync.

    Both tests asserted on a dict literal they had just built -- nothing under
    test ran (rewritten 2026-10-11)."""

    @staticmethod
    def _to_dict(md):
        return MarkerManagerMixin._marker_to_dict(md)

    def test_marker_dict_has_all_fields(self):
        from uitk.widgets.sequencer._data import MarkerData

        md = MarkerData(
            marker_id=0,
            time=10.0,
            note="test",
            color="#FF0000",
            draggable=False,
            style="bracket",
            line_style="solid",
            opacity=0.85,
        )
        self.assertEqual(
            self._to_dict(md),
            {
                "time": 10.0,
                "note": "test",
                "color": "#FF0000",
                "draggable": False,
                "style": "bracket",
                "line_style": "solid",
                "opacity": 0.85,
            },
        )

    def test_a_tools_payload_rides_along(self):
        """The Shot Manifest's owner tag survives the store rewrite every
        marker edit makes; a hand's marker gains no empty payload."""
        from uitk.widgets.sequencer._data import MarkerData

        tag = {"owner": "shot_manifest", "shot_id": 2}
        out = self._to_dict(MarkerData(marker_id=0, time=1.0, data=tag))
        self.assertEqual(out["data"], tag)
        self.assertIsNot(out["data"], tag)
        self.assertNotIn("data", self._to_dict(MarkerData(marker_id=1, time=2.0)))


class TestMarkerNavigation(unittest.TestCase):
    """Prev/next in markers mode must jump the playhead to the marker time —
    never feed the float marker time to select_shot, where the engine's
    ``==`` compare makes marker time 3.0 match an unrelated shot id 3."""

    class _FakeCombo:
        def __init__(self, items, index=0):
            self._items = list(items)
            self._index = index

        def currentIndex(self):
            return self._index

        def setCurrentIndex(self, index):
            self._index = index

        def count(self):
            return len(self._items)

        def itemData(self, index):
            return self._items[index][1]

        def blockSignals(self, block):
            pass

    class _FakeSignal:
        def __init__(self):
            self.emitted = []

        def emit(self, *args):
            self.emitted.append(args)

    class _FakeWidget:
        def __init__(self):
            self.playhead = None
            self.playhead_moved = TestMarkerNavigation._FakeSignal()

        def set_playhead(self, time):
            self.playhead = time

    def _make_host(self, cmb, widget, sequencer):
        import types

        class _Host(ShotNavMixin):
            def __init__(self):
                self.sequencer = sequencer
                self.ui = types.SimpleNamespace(cmb_shot=cmb)
                self._cmb_mode = "markers"
                self._cmb_mode_widget = None
                self._shifted_out_keys = {}
                self._prev_action = None
                self._next_action = None
                self._syncing = False
                self._playback_range_mode = "off"
                self._widget = widget
                self.synced = []

            def _sync_to_widget(self, frame=False):
                self.synced.append(frame)

            def _get_sequencer_widget(self):
                return self._widget

            def _visible_shots(self, shot):
                return [shot]

        return _Host()

    def test_marker_nav_does_not_select_shot_with_matching_id(self):
        # Shot id 3 is unrelated to the marker at time 3.0.
        seq = ptk.ShotSequencer([ptk.ShotBlock(3, "S3", 50, 60, ["cube1"])])
        seq.store.select_on_load = False
        selected = []
        seq.store.set_active_shot = lambda sid: selected.append(sid)

        cmb = self._FakeCombo([("@ 1", 1.0), ("@ 3", 3.0)], index=0)
        widget = self._FakeWidget()
        host = self._make_host(cmb, widget, seq)

        host._navigate_shot(+1)

        self.assertEqual(
            selected,
            [],
            "markers-mode nav must not route the marker time into shot selection",
        )
        self.assertEqual(
            widget.playhead, 3.0, "markers-mode nav must jump the playhead"
        )
        self.assertEqual(widget.playhead_moved.emitted, [(3.0,)])
        self.assertEqual(cmb.currentIndex(), 1)


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestKeyMoveTangentFidelity(unittest.TestCase):
    """A key dragged in the clip view must carry the FULL tangent state, not
    just value + type: hand-tuned angles, weights, lock flags and breakdown
    markers ride the move (the panel's half of mayatk's
    ``TestKeyMoveTangentFidelity``, whose ``move_object_keys`` cases stay
    there)."""

    def setUp(self):
        cmds.file(new=True, force=True)

    # -- fixtures ---------------------------------------------------------

    def _hand_tuned_cube(self, name="tanFidelity"):
        """A cube whose translateX curve carries deliberately non-default tangents.

        Keys at 1 / 5 / 10 with fixed weighted tangents at hand-set angles and
        weights, plus a breakdown key at 5.
        """
        cube = cmds.polyCube(name=name)[0]
        for t, v in ((1, 0.0), (5, 5.0), (10, 2.0)):
            cmds.setKeyframe(cube, attribute="translateX", time=t, value=v)
        crv = self._curve_of(cube)
        cmds.keyTangent(crv, edit=True, time=(1, 10), weightedTangents=True)
        cmds.keyTangent(
            crv,
            edit=True,
            time=(1, 1),
            lock=False,
            inTangentType="fixed",
            outTangentType="fixed",
            outAngle=37.5,
            outWeight=4.25,
        )
        cmds.keyTangent(
            crv,
            edit=True,
            time=(5, 5),
            lock=False,
            weightLock=False,
            inTangentType="fixed",
            outTangentType="fixed",
            inAngle=-22.0,
            outAngle=63.0,
            inWeight=3.5,
            outWeight=2.75,
        )
        cmds.keyTangent(
            crv,
            edit=True,
            time=(10, 10),
            lock=False,
            inTangentType="fixed",
            outTangentType="fixed",
            inAngle=11.25,
            inWeight=5.5,
        )
        cmds.keyframe(crv, edit=True, time=(5, 5), breakdown=True)
        return cube, crv

    @staticmethod
    def _curve_of(cube):
        return cmds.listConnections(
            f"{cube}.translateX", type="animCurve", s=True, d=False
        )[0]

    def _assert_shifted_identically(self, before, after, delta, msg="", props=None):
        self.assertEqual(
            len(before), len(after), f"{msg}: key count changed {before} -> {after}"
        )
        for b, a in zip(before, after):
            self.assertAlmostEqual(
                b["time"] + delta,
                a["time"],
                places=4,
                msg=f"{msg}: key {b['time']} did not land at {b['time'] + delta}",
            )
            self._assert_same_state(b, a, msg, props)

    def _assert_same_state(self, b, a, msg="", props=None):
        for name in props or TANGENT_PROPS + ("value", "breakdown"):
            bv, av = b[name], a[name]
            if isinstance(bv, float):
                self.assertAlmostEqual(
                    bv,
                    av,
                    places=4,
                    msg=f"{msg}: t={b['time']} {name} {bv!r} -> {av!r}",
                )
            else:
                self.assertEqual(
                    bv, av, msg=f"{msg}: t={b['time']} {name} {bv!r} -> {av!r}"
                )

    # -- clip_motion.on_keys_moved ----------------------------------------

    class _FakeClip:
        def __init__(self, data):
            self.data = data

    class _FakeWidget:
        def __init__(self, clip):
            self._clip = clip

        def get_clip(self, clip_id):
            return self._clip

    def _clip_motion_host(self, obj, attr, seq):
        """Minimal ClipMotionMixin host -- the members the mixin documents."""
        import logging

        outer = self

        class Host(ClipMotionMixin):
            def __init__(self):
                self.sequencer = seq
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._syncing = False
                self.logger = logging.getLogger("test.clip_motion_host")
                self.footers = []
                self._clip = outer._FakeClip(
                    {"obj": obj, "attr_name": attr, "shot_id": 0}
                )

            def _get_sequencer_widget(self):
                return outer._FakeWidget(self._clip)

            def _sync_to_widget(self, shot_id=None):
                pass

            def _sync_combobox(self):
                pass

            def _set_footer(self, text, *args, **kwargs):
                self.footers.append(text)

        return Host()

    def test_on_keys_moved_preserves_full_tangent_state(self):
        """Dragging keys in the clip view must not reset their tangents."""
        cube, crv = self._hand_tuned_cube("clipTanFidelity")
        before = snapshot_curve(crv)
        host = self._clip_motion_host(str(cube), "translateX", ShotSequencer())

        host.on_keys_moved(0, [(1.0, 21.0), (5.0, 25.0), (10.0, 30.0)])

        after = snapshot_curve(self._curve_of(cube))
        self._assert_shifted_identically(before, after, 20, "on_keys_moved")

    def test_on_keys_moved_preserves_tangents_for_a_sparse_selection(self):
        """Dragging some keys past one that stays put keeps every tangent."""
        cube, crv = self._hand_tuned_cube("clipSparse")
        before = snapshot_curve(crv)
        host = self._clip_motion_host(str(cube), "translateX", ShotSequencer())

        # Keys 1 and 10 move +20; the key at 5 stays where it is.
        host.on_keys_moved(0, [(1.0, 21.0), (10.0, 30.0)])

        after = snapshot_curve(self._curve_of(cube))
        self.assertEqual(
            [round(r["time"], 4) for r in after],
            [5.0, 21.0, 30.0],
            "the unselected key must stay put while the others move past it",
        )
        stayed = [r for r in after if abs(r["time"] - 5.0) < 1e-6]
        moved = [r for r in after if abs(r["time"] - 5.0) >= 1e-6]
        self._assert_shifted_identically(
            [before[0], before[2]], moved, 20, "sparse drag"
        )
        self._assert_shifted_identically(
            [before[1]], stayed, 0, "sparse drag (untouched key)"
        )

    def test_on_keys_moved_tolerates_drag_times_off_by_rounding(self):
        """Drag times arrive from the widget, so they match only to a tolerance.

        Pairing a reported time with a curve key by equality (or by a rounded
        equality) drops the key outright, and the whole drag silently becomes
        a no-op.  Mixed deltas so this runs through the cut-and-recreate path,
        which is where the pairing happens.
        """
        cube, crv = self._hand_tuned_cube("clipDrifted")
        before = snapshot_curve(crv)
        host = self._clip_motion_host(str(cube), "translateX", ShotSequencer())

        drift = 1e-5  # finer than the 1e-3 key window, coarser than 6dp rounding
        host.on_keys_moved(
            0, [(1.0 + drift, 21.0), (5.0 - drift, 26.0), (10.0 + drift, 32.0)]
        )

        after = snapshot_curve(self._curve_of(cube))
        self.assertEqual(
            [round(r["time"], 4) for r in after],
            [21.0, 26.0, 32.0],
            "a drag whose times differ from the curve's only by rounding must "
            "still move the keys",
        )
        for b, a in zip(before, after):
            self._assert_same_state(b, a, "drifted drag times")

    def test_on_keys_moved_preserves_tangents_for_mixed_deltas(self):
        """Per-key deltas that differ still have to carry the tangent state."""
        cube, crv = self._hand_tuned_cube("clipMixedDelta")
        before = snapshot_curve(crv)
        host = self._clip_motion_host(str(cube), "translateX", ShotSequencer())

        # 1 -> 21 (+20), 5 -> 26 (+21), 10 -> 32 (+22)
        host.on_keys_moved(0, [(1.0, 21.0), (5.0, 26.0), (10.0, 32.0)])

        after = snapshot_curve(self._curve_of(cube))
        self.assertEqual(
            [round(r["time"], 4) for r in after],
            [21.0, 26.0, 32.0],
            "mixed-delta drag must land every key on its own destination",
        )
        for b, a in zip(before, after):
            self._assert_same_state(b, a, "on_keys_moved mixed deltas")


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestTheSequencersOwnMembersAreNoHandEdit(unittest.TestCase):
    """An object keyed in the active shot is added by the panel as the
    SYSTEM's member, so the Shot Manifest does not read it as a hand edit
    (BACKLOG 2026-10-10: such a shot became "edited" and every later Build
    kept it, doc changes and all).  The panel's half of mayatk's
    ``TestTheSequencersOwnMembersAreNoHandEdit``, whose other cases stay
    there."""

    def setUp(self):
        cmds.file(new=True, force=True)
        ShotStore.clear_active()
        self.addCleanup(ShotStore.clear_active)
        self.store = ShotStore()
        self.mover = cmds.polyCube(name="keyed_mover")[0]
        cmds.setKeyframe(self.mover, at="translateX", t=5, v=0)
        cmds.setKeyframe(self.mover, at="translateX", t=40, v=9)
        # The doc names an object this scene does not have.
        self.step = BuilderStep("A01", "A", "SEC A", "", [BuilderObject("GHOST")])
        ShotManifest(self.store).update([self.step], initial_shot_length=50)
        self.shot = self.store.shot_by_name("A01")

    def _edited(self):
        return ShotManifest(self.store).edited_by_hand(self.shot)

    def test_an_object_keyed_in_the_active_shot_is_no_edit(self):
        ctrl = ShotSequencerController.__new__(ShotSequencerController)
        ctrl._sequencer = ShotSequencer(store=self.store)
        ctrl._edited_items = set(cmds.keyframe(self.mover, q=True, name=True))
        self.assertTrue(ctrl._auto_add_keyed_objects(self.shot.shot_id))
        self.assertFalse(self._edited())


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestDeleteKeysBracketing(unittest.TestCase):
    """Both key-delete paths must bracket through scene_edit.

    They were the last edit sites still opening a bare undo chunk and
    pushing their restore point AFTER the mutation, untagged — so the point
    could not restore anything, and being untagged the Maya Undo EVENT
    callback claimed it for somebody else's undo.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True, infinity=True)
        ShotStore.clear_active()

    def tearDown(self):
        ShotStore.clear_active()

    def _ctrl_with_clip(self):
        from unittest.mock import MagicMock

        loc = cmds.spaceLocator(name="del_loc")[0]
        for t in (1, 5, 10):
            cmds.setKeyframe(loc, at="translateX", t=t, v=float(t))

        store = ShotStore()
        store.define_shot("A", 0, 50, objects=cmds.ls(loc, long=True))
        ctrl = ShotSequencerController.__new__(ShotSequencerController)
        ctrl._sequencer = ShotSequencer(store=store)
        ctrl.logger = MagicMock()
        ctrl._segment_cache = {}
        ctrl._sub_row_cache = {}
        # Part of the mixin contract (`_syncing` — the re-entrancy guard every
        # edit path raises), so the stub has to carry it like the real object.
        ctrl._syncing = False
        ctrl._sync_to_widget = MagicMock()
        ctrl._set_footer = MagicMock()

        clip = MagicMock()
        clip.data = {
            "obj": cmds.ls(loc, long=True)[0],
            "attr_name": "translateX",
            "attributes": ["translateX"],
            "orig_start": 0.0,
            "orig_end": 50.0,
        }
        widget = MagicMock()
        widget.get_clip = MagicMock(side_effect=lambda cid: clip if cid == 1 else None)
        ctrl._get_sequencer_widget = MagicMock(return_value=widget)
        return ctrl, store, loc

    def test_delete_clip_keys_is_paired_and_predates_the_edit(self):
        ctrl, store, loc = self._ctrl_with_clip()
        ctrl._delete_clip_keys([1])
        self.assertEqual(cmds.keyframe(loc, q=True, timeChange=True) or [], [])
        tag = store.peek_boundary_tag()
        self.assertIsInstance(tag, tuple, "the restore point must be tagged")
        self.assertTrue(tag[0], "a key delete records a Maya undo step")
        self.assertEqual(tag[1], cmds.undoInfo(q=True, undoName=True))

    def test_a_delete_takes_the_system_claims_on_its_keys(self):
        """A key delete is a key edit like any other, so it runs the bracket's
        reconcile (``_key_scene_edit``): the claims on a deleted key -- a
        sample's and a gap hold's -- go with it instead of waiting on the
        frame for the next key that lands there to inherit them."""
        ctrl, store, loc = self._ctrl_with_clip()
        cmds.setKeyframe(loc, at="translateX", t=60, v=60.0)  # outside the clip
        crv = cmds.listConnections(f"{loc}.translateX", type="animCurve")[0]
        led = store.edit_ledger
        led.record_key(crv, 10.0, 0, "end")
        led.record_step(crv, 10.0, "auto", "auto")
        ctrl._delete_clip_keys([1])
        self.assertEqual(cmds.keyframe(crv, q=True), [60.0])
        self.assertEqual((led.key_times(crv), led.step_times(crv)), ([], []))

    def test_a_delete_takes_a_behaviors_authored_claim_too(self):
        """...and every OTHER claim on a deleted key: a behavior's authored
        claim is no sample, so the reconcile left it on the frame for the
        next key that lands there to inherit."""
        ctrl, store, loc = self._ctrl_with_clip()
        crv = cmds.listConnections(f"{loc}.translateX", type="animCurve")[0]
        led = store.edit_ledger
        led.record_authored(crv, 5.0, 0, "fade_in", loc)
        ctrl._delete_clip_keys([1])
        self.assertEqual(cmds.keyframe(loc, q=True, timeChange=True) or [], [])
        self.assertFalse(led.owns_any(crv, 5.0), led.to_dict())

    def test_a_deleted_sample_on_its_bound_takes_its_claim(self):
        """...a sample still ON its bound too -- where the system makes them.
        The reconcile passed a claim on its bound before asking whether its
        key was still there, so it waited on the frame for the next key."""
        ctrl, store, loc = self._ctrl_with_clip()
        for t in (50, 60):  # 50: A's end, inside the clip; 60: outside it
            cmds.setKeyframe(loc, at="translateX", t=t, v=float(t))
        crv = cmds.listConnections(f"{loc}.translateX", type="animCurve")[0]
        led = store.edit_ledger
        led.record_key(crv, 50.0, 0, "end")
        ctrl._delete_clip_keys([1])
        self.assertEqual(cmds.keyframe(crv, q=True), [60.0])
        self.assertEqual(led.key_times(crv), [])

    def test_a_delete_that_removes_nothing_leaves_no_restore_point(self):
        ctrl, store, _loc = self._ctrl_with_clip()
        depth = len(store._boundary_undo)
        ctrl._delete_clip_keys([999])  # no such clip -> no ops at all
        self.assertEqual(len(store._boundary_undo), depth)

    def test_a_failed_delete_discards_its_restore_point(self):
        """Every cutKey failing (locked/connected attrs on a referenced asset)
        must leave the ledger exactly as it was — an orphan restore point
        shifts every later undo by one, and losing the redo branch that the
        up-front push cleared costs the user a redo they never spent."""
        ctrl, store, loc = self._ctrl_with_clip()
        store.push_boundary_snapshot(tag=(False, "earlier"))
        store.update_shot(0, end=40)
        store.restore_boundary_snapshot()  # -> a redo branch exists
        depth = len(store._boundary_undo)

        with patch.object(cmds, "cutKey", side_effect=RuntimeError("locked")):
            ctrl._delete_clip_keys([1])

        self.assertEqual(len(store._boundary_undo), depth)
        self.assertTrue(
            store.has_boundary_snapshot(redo=True),
            "a failed delete must not cost the user their redo branch",
        )
        self.assertEqual(len(cmds.keyframe(loc, q=True, timeChange=True) or []), 3)


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestMoveToShotMenu(unittest.TestCase):
    """Next Shot / Previous Shot head the Move to Shot submenu.

    Nudging a selection one shot along the sequence is the move an animator
    makes most; by name it is a different entry every time, so the two
    relative moves lead the list and the named shots follow a separator.
    """

    @classmethod
    def setUpClass(cls):
        from qtpy.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        cmds.file(new=True, force=True)
        ShotStore.clear_active()
        self.store = ShotStore()
        self.a = self.store.define_shot("A", 0, 50)
        self.b = self.store.define_shot("B", 60, 100)
        self.c = self.store.define_shot("C", 110, 150)
        self.seq = ShotSequencer(store=self.store)

        self.ctrl = ShotSequencerController.__new__(ShotSequencerController)
        self.ctrl._sequencer = self.seq
        self.ctrl.ui = None
        self.ctrl._cmb_mode = "shots"
        self.ctrl._copy_to_shot = False
        self.moved = []
        self.ctrl._send_to_shot = lambda seqs, sid, noun="clip", copy=False: (
            self.moved.append((sid, noun, copy))
        )

    def tearDown(self):
        ShotStore.clear_active()

    def _menu(self, seqs, noun="clip"):
        from qtpy import QtWidgets

        menu = QtWidgets.QMenu()
        self.ctrl._populate_send_to_shot(menu, seqs, noun=noun)
        return menu

    @staticmethod
    def _labels(menu):
        return ["---" if a.isSeparator() else a.text() for a in menu.actions()]

    @staticmethod
    def _seq(start, end):
        return {"kind": "anim", "obj": "x", "start": start, "end": end}

    def test_the_neighbours_head_the_list(self):
        labels = self._labels(self._menu([self._seq(70, 90)]))
        self.assertEqual(labels[0], "Next Shot  (C)")
        self.assertEqual(labels[1], "Previous Shot  (A)")
        self.assertEqual(labels[2], "---")
        self.assertEqual(
            labels[3:],
            ["A  [0\u201350]", "C  [110\u2013150]"],
            "B is where it already is",
        )

    def test_the_first_shot_offers_no_previous(self):
        labels = self._labels(self._menu([self._seq(10, 20)]))
        self.assertEqual(labels[0], "Next Shot  (B)")
        self.assertEqual(labels[1], "---")
        self.assertNotIn("Previous Shot  (A)", labels)

    def test_the_last_shot_offers_no_next(self):
        labels = self._labels(self._menu([self._seq(120, 130)]))
        self.assertEqual(labels[0], "Previous Shot  (B)")
        self.assertNotIn("Next Shot", "".join(labels))

    def test_a_selection_spanning_shots_anchors_on_the_active_shot(self):
        self.store.set_active_shot(self.b.shot_id)
        labels = self._labels(self._menu([self._seq(10, 20), self._seq(120, 130)]))
        self.assertEqual(labels[:2], ["Next Shot  (C)", "Previous Shot  (A)"])
        self.assertEqual(
            labels[3:],
            ["A  [0\u201350]", "B  [60\u2013100]", "C  [110\u2013150]"],
            "no single source, so no shot is excluded",
        )

    def test_next_shot_moves_into_the_following_shot(self):
        menu = self._menu([self._seq(70, 90)], noun="key")
        next(a for a in menu.actions() if a.text().startswith("Next Shot")).trigger()
        self.assertEqual(self.moved, [(self.c.shot_id, "key", False)])

    def test_previous_shot_moves_into_the_preceding_shot(self):
        menu = self._menu([self._seq(70, 90)])
        next(
            a for a in menu.actions() if a.text().startswith("Previous Shot")
        ).trigger()
        self.assertEqual(self.moved, [(self.a.shot_id, "clip", False)])

    # -- Move / Copy: one submenu (2026-10-07) ------------------------------

    def _send_menu(self, seqs, suffix=""):
        from qtpy import QtWidgets

        parent = QtWidgets.QMenu()
        sub = self.ctrl._add_send_to_shot_menu(parent, seqs, suffix=suffix)
        self.addCleanup(parent.deleteLater)
        return parent, sub

    @staticmethod
    def _copy_box(sub):
        """The checkbox of the submenu's first row (``None`` when it has none)."""
        from qtpy import QtWidgets

        row = sub.actions()[0]
        if not isinstance(row, QtWidgets.QWidgetAction):
            return None
        return row.defaultWidget().findChild(QtWidgets.QCheckBox)

    def test_move_and_copy_share_one_list_of_shots(self):
        """Not a Move and a Copy submenu listing the same shots twice: one
        submenu, a Copy toggle at its head (2026-10-07: "Is there a way to make
        this less redundant?")."""
        parent, sub = self._send_menu([self._seq(70, 90)], suffix=" (2)")
        self.assertEqual([a.menu() for a in parent.actions()], [sub])
        self.assertEqual(sub.title(), "Move to Shot (2)")
        box = self._copy_box(sub)
        self.assertIsNotNone(box, "no Copy toggle heads the submenu")
        self.assertFalse(box.isChecked())
        self.assertEqual(
            self._labels(sub)[1:4], ["---", "Next Shot  (C)", "Previous Shot  (A)"]
        )

    def test_the_copy_toggle_turns_a_pick_into_a_copy(self):
        _parent, sub = self._send_menu([self._seq(70, 90)])
        self._copy_box(sub).setChecked(True)
        self.assertEqual(sub.title(), "Copy to Shot", "the title says what a pick does")
        next(a for a in sub.actions() if a.text().startswith("Next Shot")).trigger()
        self.assertEqual(self.moved, [(self.c.shot_id, "clip", True)])

    def test_the_toggle_holds_for_the_next_menu(self):
        _parent, sub = self._send_menu([self._seq(70, 90)])
        self._copy_box(sub).setChecked(True)
        _parent2, sub2 = self._send_menu([self._seq(70, 90)])
        self.assertEqual(sub2.title(), "Copy to Shot")
        self.assertTrue(self._copy_box(sub2).isChecked())


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestKeyTangentDrag(unittest.TestCase):
    """A dragged tangent handle lands on the curve as the angle (and, on a
    weighted curve, the weight) the handle vector stands for."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.store = ShotStore()
        self.seq = ShotSequencer(store=self.store)
        self.obj = cmds.polyCube(name="tan_cube")[0]
        for t, v in ((0, 0.0), (10, 5.0), (20, 0.0)):
            cmds.setKeyframe(self.obj, attribute="translateX", time=t, value=v)
        self.crv = cmds.listConnections(f"{self.obj}.translateX", type="animCurve")[0]
        self.seq.define_shot("A", 0, 20, objects=[self.obj])

    def _ctl(self):
        obj, seq, footers = self.obj, self.seq, []

        class _Clip:
            data = {"obj": obj, "attr_name": "translateX", "shot_id": 0}

        class _Widget:
            @staticmethod
            def get_clip(_cid):
                return _Clip()

            @staticmethod
            def select_keys(_wanted):
                return 0

        class _Ctl(ShotSequencerController):
            def __init__(self):  # bypass the panel's __init__
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._audio_segments_cache = None
                self._syncing = False

            sequencer = seq

            def _get_sequencer_widget(self):
                return _Widget()

            def _set_footer(self, text, **kw):
                footers.append(text)

            def _sync_to_widget(self, **kw):
                pass

        ctl = _Ctl()
        ctl.footers = footers
        return ctl

    def _tangent(self, t, **flag):
        return cmds.keyTangent(self.crv, q=True, time=(t, t), **flag)[0]

    def test_an_out_drag_sets_the_out_angle(self):
        ctl = self._ctl()
        ctl.on_keys_tangent_dragged([(1, [(10.0, 3.0, 3.0)])], "out", False)
        self.assertAlmostEqual(self._tangent(10, outAngle=True), 45.0, places=3)
        self.assertEqual(self._tangent(10, outTangentType=True), "fixed")

    def test_an_in_drag_sets_the_in_angle(self):
        ctl = self._ctl()
        cmds.keyTangent(self.crv, edit=True, time=(10, 10), lock=False)
        ctl.on_keys_tangent_dragged([(1, [(10.0, -4.0, 4.0)])], "in", False)
        self.assertAlmostEqual(self._tangent(10, inAngle=True), -45.0, places=3)

    def test_a_weighted_curve_takes_the_handle_length_as_weight(self):
        cmds.keyTangent(self.crv, edit=True, weightedTangents=True)
        ctl = self._ctl()
        ctl.on_keys_tangent_dragged([(1, [(10.0, 3.0, 4.0)])], "out", False)
        self.assertAlmostEqual(self._tangent(10, outWeight=True), 5.0, places=3)
        self.assertTrue(any("handle dragged" in f for f in ctl.footers))

    def test_a_carried_selection_writes_a_vector_per_key(self):
        """One gesture, one undo chunk, a different angle on each key: the
        drag carried the whole key selection."""
        ctl = self._ctl()
        ctl.on_keys_tangent_dragged(
            [(1, [(0.0, 3.0, 0.0), (10.0, 3.0, 3.0)])], "out", False
        )
        self.assertAlmostEqual(self._tangent(0, outAngle=True), 0.0, places=3)
        self.assertAlmostEqual(self._tangent(10, outAngle=True), 45.0, places=3)

    def test_an_unbroken_drag_swings_the_other_side(self):
        """uitk swings a unified key's other handle live, under the cursor.
        Maya has to write the same thing, or the release would snap it back."""
        ctl = self._ctl()
        self.assertTrue(self._tangent(10, lock=True), "the fixture key is unified")
        ctl.on_keys_tangent_dragged([(1, [(10.0, 3.0, 3.0)])], "out", False)
        self.assertAlmostEqual(self._tangent(10, inAngle=True), 45.0, places=3)

    def test_a_broken_drag_unlocks_the_key_and_leaves_the_other_side(self):
        ctl = self._ctl()
        before = self._tangent(10, inAngle=True)
        ctl.on_keys_tangent_dragged([(1, [(10.0, 3.0, 3.0)])], "out", True)
        self.assertFalse(self._tangent(10, lock=True), "Alt breaks the key")
        self.assertAlmostEqual(self._tangent(10, outAngle=True), 45.0, places=3)
        self.assertAlmostEqual(
            self._tangent(10, inAngle=True),
            before,
            places=3,
            msg="a broken key does not swing its partner",
        )
        self.assertTrue(any("handle broken" in f for f in ctl.footers))

    def test_the_retired_single_key_handler_stays_removed(self):
        """``on_key_tangent_dragged`` answered uitk's single-key signal, which
        nothing connected; both were retired 2026-09-21. One handler takes
        every tangent drag, a lone key included."""
        ctl = self._ctl()
        self.assertFalse(hasattr(type(ctl), "on_key_tangent_dragged"))
        ctl.on_keys_tangent_dragged([(1, [(10.0, 3.0, 3.0)])], "out", False)
        self.assertAlmostEqual(self._tangent(10, outAngle=True), 45.0, places=3)
        self.assertTrue(self._tangent(10, lock=True), "unbroken: the key stays unified")


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestARefusedDragReportsInsteadOfRaising(unittest.TestCase):
    """A clip dragged past the bound must never answer with a traceback.

    Overrunning expands the shot and ripples the neighbour, and the planner
    REFUSES that ripple when it would force two shots' disagreeing poses
    onto one frame.  Measured on a production assembly: the refusal came
    straight out of ``on_clip_moved`` as an unhandled
    ``ShotBoundaryConflict``, i.e. a traceback at the end of a mouse drag.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        ShotStore.clear_active()
        self.store = ShotStore()
        ShotStore.set_active(self.store)
        self.seq = ShotSequencer(store=self.store)

    def _ctl(self, clip_data):
        from pythontk import ShotBoundaryConflict

        seq, footers, warned, raised = self.seq, [], [], []

        class _Clip:
            data = clip_data
            start = clip_data["orig_start"]
            end = clip_data["orig_end"]

        class _Widget:
            shift_held_at_press = False

            @staticmethod
            def get_clip(_cid):
                return _Clip()

        class _Log:
            @staticmethod
            def warning(msg):
                warned.append(msg)

            @staticmethod
            def debug(*a, **kw):
                pass

        class _Ctl(ShotSequencerController):
            def __init__(self):  # bypass the panel's __init__
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._audio_segments_cache = None
                self._syncing = False
                self._shifted_out_keys = {}

            sequencer = seq
            logger = _Log()

            def _get_sequencer_widget(self):
                return _Widget()

            def _set_footer(self, text, **kw):
                footers.append(text)

            def _sync_to_widget(self, **kw):
                pass

            def _sync_combobox(self):
                pass

            def _expand_shot_range(self, *_a, **_kw):
                # The refusal's real origin: expanding past the bound ripples
                # the neighbour, and the planner declines the ripple.
                exc = ShotBoundaryConflict(["p"])
                raised.append(exc)
                raise exc

        ctl = _Ctl()
        ctl.footers, ctl.warned, ctl.raised = footers, warned, raised
        return ctl

    def _cube(self, name, keys):
        node = cmds.polyCube(name=name)[0]
        for t, v in sorted(keys.items()):
            cmds.setKeyframe(node, attribute="translateX", time=t, value=v)
        return node

    def _clip_data(self, obj, shot_id):
        return {
            "obj": obj,
            "attr_name": "translateX",  # the sub-row path
            "orig_start": 10.0,
            "orig_end": 20.0,
            "shot_id": shot_id,
        }

    def test_a_single_drag_reports_the_refusal(self):
        a = self._cube("refuseA", {10: 0, 20: 1})
        shot = self.seq.define_shot("A", 10, 20, objects=[a])
        ctl = self._ctl(self._clip_data(a, shot.shot_id))

        ctl.on_clip_moved(1, 40.0)  # must not raise

        self.assertEqual(ctl.warned, [str(ctl.raised[0])], "the refusal is logged")
        self.assertEqual(
            ctl.footers[-1],
            str(ctl.raised[0]),
            "the refusal must be the notice left standing, not overwritten "
            f"by a success message: {ctl.footers}",
        )

    def test_a_batch_drag_reports_the_refusal(self):
        a = self._cube("refuseB", {10: 0, 20: 1})
        shot = self.seq.define_shot("A", 10, 20, objects=[a])
        ctl = self._ctl(self._clip_data(a, shot.shot_id))

        ctl.on_clips_batch_moved([(1, 40.0)])  # must not raise

        self.assertEqual(ctl.warned, [str(ctl.raised[0])])
        self.assertEqual(ctl.footers[-1], str(ctl.raised[0]), f"{ctl.footers}")

    def test_the_keys_that_already_moved_are_still_undoable(self):
        """Each ripple declines before IT writes and a clip makes room before
        it lands (2026-09-22), but ``_expand_shot_range`` ripples the head
        before the tail -- a refused tail can follow a head that already
        moved the scene, so the restore point must survive the refusal."""
        cmds.undoInfo(state=True, infinity=True)  # the step must reach the queue
        a = self._cube("refuseC", {10: 0, 20: 1})
        shot = self.seq.define_shot("A", 10, 20, objects=[a])
        ctl = self._ctl(self._clip_data(a, shot.shot_id))
        refuse = ctl._expand_shot_range

        def ripple_then_refuse(*args, **kwargs):
            # The head's ripple moved a key; then the tail is refused.
            cmds.keyframe(a, edit=True, relative=True, timeChange=5, time=(20, 20))
            refuse(*args, **kwargs)

        ctl._expand_shot_range = ripple_then_refuse
        before = len(self.store._boundary_undo)

        ctl.on_clip_moved(1, 40.0)

        # The panel never drops a restore point by hand now; the store keeps
        # one whose edit reached Maya's queue, refused or not.
        self.assertEqual(
            len(self.store._boundary_undo),
            before + 1,
            "the scene changed, so the undo step must be kept",
        )
        self.assertTrue(self.store.peek_boundary_tag()[0], "and it is paired")


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestContextMenuPadding(unittest.TestCase):
    """The context menu's Add Leading/Trailing Frames entries.

    How much room a shot needs is the whole question the gesture asks, so the
    entries prompt for it; the field opens on the last answer so a run of
    shots padded by the same beat costs one keystroke each.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        ShotStore.clear_active()
        self.store = ShotStore()
        ShotStore.set_active(self.store)
        self.seq = ShotSequencer(store=self.store)

    def _ctl(self):
        seq = self.seq
        footers = []

        class _Ctl(ShotSequencerController):
            def __init__(self):  # bypass the panel's __init__
                self._segment_cache = {}
                self._sub_row_cache = {}
                self._audio_segments_cache = None
                self._syncing = False
                self._context_space_frames = self.CONTEXT_SPACE_FRAMES

            sequencer = seq

            def _set_footer(self, text, **kw):
                footers.append(text)

            def _after_shot_change(self, shot_id=None):
                pass

            # Nothing stands in for the store: a no-op pad cancels its own
            # ``scene_edit`` (no dead restore point), which is behaviour under
            # test here.

        ctl = _Ctl()
        ctl.footers = footers
        return ctl

    def _cube(self, name, keys):
        node = cmds.polyCube(name=name)[0]
        for t, v in sorted(keys.items()):
            cmds.setKeyframe(node, attribute="translateX", time=t, value=v)
        return node

    def test_the_prompt_opens_on_a_beat_of_room(self):
        self.assertEqual(ShotSequencerController.CONTEXT_SPACE_FRAMES, 15.0)

    # -- the amount prompt -------------------------------------------------

    def _prompting(self, answer):
        """A controller whose ``input_dialog`` returns *answer*, kwargs recorded."""
        import types

        ctl = self._ctl()
        seen = {}
        padded = []

        def _dialog(**kwargs):
            seen.update(kwargs)
            return answer

        ctl.sb = types.SimpleNamespace(input_dialog=_dialog)
        ctl.ui = None
        ctl._get_sequencer_widget = lambda: None
        ctl._add_shot_space = lambda shot_id, frames, edge: padded.append(
            (shot_id, frames, edge)
        )
        return ctl, seen, padded

    def test_the_typed_amount_is_what_gets_padded(self):
        shot = self.seq.define_shot("A", 10, 20)
        ctl, seen, padded = self._prompting("42")
        ctl._prompt_shot_space(shot, edge="leading")
        self.assertEqual(padded, [(shot.shot_id, 42.0, "leading")])
        self.assertEqual(seen["text"], "15", "field opens on the class default")

    def test_the_prompt_remembers_the_last_answer(self):
        shot = self.seq.define_shot("A", 10, 20)
        ctl, _seen, _padded = self._prompting("42")
        ctl._prompt_shot_space(shot, edge="leading")
        ctl2, seen2, _p2 = self._prompting("7")
        ctl2._context_space_frames = ctl._context_space_frames
        ctl2._prompt_shot_space(shot, edge="trailing")
        self.assertEqual(seen2["text"], "42")

    def test_cancelling_the_prompt_pads_nothing(self):
        shot = self.seq.define_shot("A", 10, 20)
        ctl, _seen, padded = self._prompting(None)
        ctl._prompt_shot_space(shot, edge="leading")
        self.assertEqual(padded, [])
        self.assertEqual(ctl._context_space_frames, ctl.CONTEXT_SPACE_FRAMES)

    def test_a_negative_amount_is_accepted(self):
        """Removing room is the same control in the other direction —
        ``add_shot_space`` clamps it to what is actually empty."""
        shot = self.seq.define_shot("A", 10, 20)
        ctl, seen, padded = self._prompting("-5")
        ctl._prompt_shot_space(shot, edge="leading")
        self.assertEqual(padded, [(shot.shot_id, -5.0, "leading")])
        self.assertTrue(seen["validate"]("-5"))

    def test_the_validator_rejects_junk_and_zero(self):
        shot = self.seq.define_shot("A", 10, 20)
        ctl, seen, _padded = self._prompting("1")
        ctl._prompt_shot_space(shot, edge="leading")
        validate = seen["validate"]
        for bad in ("", "  ", "abc", "0", "0.0", "12f"):
            self.assertFalse(validate(bad), f"{bad!r} should be rejected")
        for good in ("1", " 2.5 ", "-3"):
            self.assertTrue(validate(good), f"{good!r} should be accepted")

    def test_leading_padding_holds_the_start_and_pushes_the_content(self):
        a = self._cube("padMenuA", {10: 0, 20: 1})
        shot = self.seq.define_shot("A", 10, 20, objects=[a])
        ctl = self._ctl()
        ctl._add_shot_space(shot.shot_id, ctl.CONTEXT_SPACE_FRAMES, edge="leading")
        self.assertEqual((shot.start, shot.end), (10.0, 35.0))
        self.assertEqual(
            sorted(cmds.keyframe(f"{a}.translateX", q=True, timeChange=True)),
            [25.0, 35.0],
        )

    def test_trailing_padding_leaves_the_content_alone(self):
        a = self._cube("padMenuB", {10: 0, 20: 1})
        shot = self.seq.define_shot("A", 10, 20, objects=[a])
        ctl = self._ctl()
        ctl._add_shot_space(shot.shot_id, ctl.CONTEXT_SPACE_FRAMES, edge="trailing")
        self.assertEqual((shot.start, shot.end), (10.0, 35.0))
        self.assertEqual(
            sorted(cmds.keyframe(f"{a}.translateX", q=True, timeChange=True)),
            [10.0, 20.0],
        )

    def test_a_no_op_pad_leaves_no_dead_restore_point(self):
        """A restore point nothing moved would make the next undo do nothing
        visible -- the same contract the trim actions already keep."""
        a = self._cube("padMenuC", {10: 0, 20: 1})
        shot = self.seq.define_shot("A", 10, 20, objects=[a])
        ctl = self._ctl()
        ctl._add_shot_space(shot.shot_id, 0.0, edge="leading")
        self.assertFalse(self.store.has_boundary_snapshot())
        self.assertTrue(any("nothing to do" in f for f in ctl.footers))


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestTheKeySelectionMirrorStaysOffTheUndoQueue(unittest.TestCase):
    """The panel's key-selection mirror, end to end, costs no undo step and
    still selects (mayatk's ``TestSelectionMirrorsStayOffTheUndoQueue`` pins
    the host's guarded writers, ``SequencerHost.select_keys`` /
    ``mirror_selection``, and the premise that ``selectKey`` records).
    ``on_key_selection_changed`` also mirrors the objects and the channel
    scope: none of it may reach the queue either."""

    def setUp(self):
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True, infinity=True)
        self.obj = cmds.spaceLocator(name="mirrored")[0]
        for t, v in ((1, 0.0), (5, 3.0), (9, 1.0), (13, 4.0)):
            cmds.setKeyframe(self.obj, attribute="translateX", time=t, value=v)
        self.crv = cmds.listConnections(
            f"{self.obj}.translateX", type="animCurve", s=True, d=False
        )[0]

    def _times(self):
        return [round(t, 3) for t in (cmds.keyframe(self.crv, q=True) or [])]

    def _edit(self):
        """One real, named scene edit -- the thing Ctrl+Z has to reach."""
        cmds.undoInfo(openChunk=True, chunkName="probeEdit")
        cmds.keyframe(self.crv, edit=True, relative=True, timeChange=7.0, time=(0, 100))
        cmds.undoInfo(closeChunk=True)

    def _undo_cost(self, before, limit=30):
        for i in range(1, limit + 1):
            cmds.undo()
            if self._times() == before:
                return i
        return -1

    def test_key_selection_mirror_costs_no_undo_step(self):
        class _Clip:
            data = {"obj": None, "attr_name": "translateX"}

        class _Widget:
            def __init__(self, clip):
                self._clip = clip

            def get_clip(self, _cid):
                return self._clip

        class _Ctl(ShotSequencerController):
            # Subclassed, not duck-typed: __init__ is skipped (there is no
            # panel here) but every helper the mirror leans on comes along.
            _syncing = False
            ui = None  # no panel: the key line has no footer to go on

            def __init__(self, widget):
                self._widget = widget

            def _get_sequencer_widget(self):
                return self._widget

        clip = _Clip()
        clip.data = dict(clip.data, obj=self.obj)
        ctl = _Ctl(_Widget(clip))

        before = self._times()
        self._edit()
        ShotSequencerController.on_key_selection_changed(
            ctl, [{"clip_id": 0, "times": self._times()}]
        )
        self.assertEqual(self._undo_cost(before), 1)

    def test_key_selection_mirror_still_selects(self):
        """The guard must not cost the feature it protects."""

        class _Clip:
            pass

        clip = _Clip()
        clip.data = {"obj": self.obj, "attr_name": "translateX"}

        class _Widget:
            def get_clip(self, _cid):
                return clip

        class _Ctl(ShotSequencerController):
            _syncing = False
            ui = None  # no panel: the key line has no footer to go on

            def __init__(self):
                pass  # no panel to build; the mirror needs none

            def _get_sequencer_widget(self):
                return _Widget()

        cmds.selectKey(clear=True)
        ShotSequencerController.on_key_selection_changed(
            _Ctl(), [{"clip_id": 0, "times": [5.0, 13.0]}]
        )
        selected = sorted(
            round(t, 3) for t in (cmds.keyframe(self.crv, q=True, selected=True) or [])
        )
        self.assertEqual(selected, [5.0, 13.0])


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestGroupClipScaleIsOneEdit(unittest.TestCase):
    """An edge drag that scaled several clips arrives as ONE payload.

    The widget sends ``clips_batch_resized`` for a selection, already ordered
    so committing them one at a time never lands a clip on a span another has
    not left yet.  The controller must commit the whole list inside one
    ``scene_edit`` -- the gesture is one edit, so it is one Ctrl+Z.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True, infinity=True)
        ShotStore.clear_active()

    def tearDown(self):
        ShotStore.clear_active()

    class _Clip:
        def __init__(self, data):
            self.data = data

    class _Widget:
        def __init__(self, clips):
            self._clips = clips

        def get_clip(self, cid):
            return self._clips.get(cid)

    def _controller(self, clips):
        store = ShotStore()
        store.define_shot("A", 0, 100)
        ctrl = ShotSequencerController.__new__(ShotSequencerController)
        ctrl._sequencer = ShotSequencer(store=store)
        ctrl._syncing = False
        ctrl._segment_cache = {}
        ctrl._sub_row_cache = {}
        ctrl.logger = logging.getLogger("test_sequencer.groupscale")
        widget = self._Widget(clips)
        ctrl._get_sequencer_widget = lambda: widget
        ctrl._gap_edit_epilogue = lambda: None
        ctrl._set_footer = lambda *a, **kw: None
        return ctrl, store

    def _keyed(self, name, times):
        loc = cmds.spaceLocator(name=name)[0]
        for i, t in enumerate(times):
            cmds.setKeyframe(loc, at="translateX", t=t, v=float(i))
        return loc

    def _clip(self, obj, lo, hi, attr="translateX"):
        return self._Clip(
            {
                "obj": obj,
                "attr_name": attr,
                "shot_id": 0,
                "orig_start": lo,
                "orig_end": hi,
            }
        )

    def test_two_clips_scale_and_reverse_in_one_undo(self):
        a = self._keyed("scale_a", [0, 10])
        b = self._keyed("scale_b", [20, 30])
        clips = {1: self._clip(a, 0, 10), 2: self._clip(b, 20, 30)}
        ctrl, store = self._controller(clips)
        ctrl.on_clips_batch_resized([(1, 0.0, 5.0), (2, 10.0, 5.0)])
        self.assertEqual(cmds.keyframe(a, q=True, timeChange=True), [0.0, 5.0])
        self.assertEqual(cmds.keyframe(b, q=True, timeChange=True), [10.0, 15.0])
        paired, marker = store.peek_boundary_tag()
        self.assertTrue(paired)
        self.assertEqual(marker, store.undo_queue_top())
        cmds.undo()
        self.assertEqual(cmds.keyframe(a, q=True, timeChange=True), [0.0, 10.0])
        self.assertEqual(cmds.keyframe(b, q=True, timeChange=True), [20.0, 30.0])

    def test_a_single_resize_still_goes_through_the_same_commit(self):
        a = self._keyed("solo_a", [0, 10])
        ctrl, store = self._controller({1: self._clip(a, 0, 10)})
        ctrl.on_clip_resized(1, 0.0, 5.0)
        self.assertEqual(cmds.keyframe(a, q=True, timeChange=True), [0.0, 5.0])
        cmds.undo()
        self.assertEqual(cmds.keyframe(a, q=True, timeChange=True), [0.0, 10.0])

    def test_an_all_noop_batch_drops_its_restore_point(self):
        clips = {1: self._Clip({"is_audio": True, "shot_id": 0, "obj": "snd"})}
        ctrl, store = self._controller(clips)
        ctrl.on_clips_batch_resized([(1, 0.0, 5.0)])
        self.assertFalse(
            store.has_boundary_snapshot(), "a batch that wrote nothing is not an edit"
        )

    def test_an_empty_batch_is_a_no_op(self):
        ctrl, _store = self._controller({})
        ctrl.on_clips_batch_resized([])


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestKeyDeletePathsRaiseTheSyncGuard(unittest.TestCase):
    """Every path that cuts keys must hold ``_syncing`` while it does.

    ``cutKey`` fires the controller's ``MAnimMessage`` callbacks
    SYNCHRONOUSLY, and an unguarded pass arms the 200 ms keyframe debounce
    into a SECOND full rebuild on top of the explicit one the delete already
    does -- two teardowns of the same key dots a fifth of a second apart,
    from inside the Delete key's own dispatch.  Two of the three delete paths
    had no guard until 2026-09-11; this is the invariant, so a fourth cannot
    be written without one.

    (``_delete_selected_clip_keys``, the third, reads the live scene
    selection and so needs a real widget: it is covered end to end by
    ``shot_sequencer_real_scene_check.py --only delete_highlighted_keys``.)
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True, infinity=True)
        ShotStore.clear_active()

    def tearDown(self):
        ShotStore.clear_active()

    class _Clip:
        def __init__(self, data):
            self.data = data

    class _Widget:
        def __init__(self, clips):
            self._clips = clips

        def get_clip(self, cid):
            return self._clips.get(cid)

    def _controller(self, clips):
        store = ShotStore()
        store.define_shot("A", 0, 100)
        ctrl = ShotSequencerController.__new__(ShotSequencerController)
        ctrl._sequencer = ShotSequencer(store=store)
        ctrl._syncing = False
        ctrl._segment_cache = {}
        ctrl._sub_row_cache = {}
        ctrl.logger = logging.getLogger("test_sequencer.deleteguard")
        widget = self._Widget(clips)
        ctrl._get_sequencer_widget = lambda: widget
        ctrl._sync_to_widget = lambda *a, **kw: None
        ctrl._set_footer = lambda *a, **kw: None
        return ctrl, store

    @staticmethod
    def _spy_guard(ctrl, store):
        """Record ``_syncing`` as the edit's ``scene_edit`` opens."""
        import contextlib

        seen = []
        real = store.scene_edit

        @contextlib.contextmanager
        def spy(label="edit", snapshot=True):
            seen.append(ctrl._syncing)
            with real(label, snapshot=snapshot) as edit:
                yield edit  # a no-op path cancels through it

        store.scene_edit = spy
        return seen

    def _keyed(self, name, times):
        loc = cmds.spaceLocator(name=name)[0]
        for i, t in enumerate(times):
            cmds.setKeyframe(loc, at="translateX", t=t, v=float(i))
        return loc

    def test_delete_clip_keys_holds_the_guard(self):
        obj = self._keyed("del_clip_loc", [0, 10, 20])
        clips = {
            1: self._Clip(
                {
                    "obj": obj,
                    "attributes": ["translateX"],
                    "orig_start": 0,
                    "orig_end": 20,
                }
            )
        }
        ctrl, store = self._controller(clips)
        seen = self._spy_guard(ctrl, store)
        ctrl._delete_clip_keys([1])
        self.assertEqual(seen, [True])
        self.assertFalse(ctrl._syncing, "the guard must be released afterwards")
        self.assertEqual(cmds.keyframe(obj, q=True, timeChange=True) or [], [])

    def test_on_keys_deleted_holds_the_guard(self):
        obj = self._keyed("del_keys_loc", [0, 10, 20])
        clips = {1: self._Clip({"obj": obj, "attr_name": "translateX", "shot_id": 0})}
        ctrl, store = self._controller(clips)
        seen = self._spy_guard(ctrl, store)
        ctrl.on_keys_deleted(1, [10.0])
        self.assertEqual(seen, [True])
        self.assertFalse(ctrl._syncing)
        self.assertEqual(cmds.keyframe(obj, q=True, timeChange=True), [0.0, 20.0])

    def test_on_keys_deleted_takes_every_claim_on_the_key(self):
        obj = self._keyed("del_claim_loc", [0, 10, 20])
        clips = {1: self._Clip({"obj": obj, "attr_name": "translateX", "shot_id": 0})}
        ctrl, store = self._controller(clips)
        crv = cmds.listConnections(f"{obj}.translateX", type="animCurve")[0]
        store.edit_ledger.record_authored(crv, 10.0, 0, "fade_in", obj)

        ctrl.on_keys_deleted(1, [10.0])

        self.assertEqual(cmds.keyframe(obj, q=True, timeChange=True), [0.0, 20.0])
        self.assertFalse(store.edit_ledger.owns_any(crv, 10.0))

    def test_the_delete_key_takes_every_claim_on_the_keys_it_cuts(self):
        """The Delete key over a KEY selection (``_delete_selected_clip_keys``),
        the selection stood in for by the widget's ``selected_keys``."""
        obj = self._keyed("del_sel_loc", [0, 10, 20])
        clips = {1: self._Clip({"obj": obj, "attr_name": "translateX", "shot_id": 0})}
        ctrl, store = self._controller(clips)
        crv = cmds.listConnections(f"{obj}.translateX", type="animCurve")[0]
        store.edit_ledger.record_authored(crv, 10.0, 0, "fade_in", obj)

        widget = ctrl._get_sequencer_widget()
        widget.selected_keys = lambda: [{"clip_id": 1, "times": [10.0]}]
        # No panel: the refresh after the edit reads the shot combo.
        with patch.object(type(ctrl), "active_shot_id", None):
            ctrl._delete_selected_clip_keys()

        self.assertEqual(cmds.keyframe(obj, q=True, timeChange=True), [0.0, 20.0])
        self.assertFalse(store.edit_ledger.owns_any(crv, 10.0))

    def test_the_guard_is_restored_not_cleared(self):
        """A caller already inside its own guarded edit keeps it afterwards."""
        obj = self._keyed("nested_loc", [0, 10, 20])
        clips = {1: self._Clip({"obj": obj, "attr_name": "translateX", "shot_id": 0})}
        ctrl, _store = self._controller(clips)
        ctrl._syncing = True
        ctrl.on_keys_deleted(1, [10.0])
        self.assertTrue(ctrl._syncing)


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestResolveFullName(unittest.TestCase):
    """``_resolve_full_name``: a name the shots already hold is its own
    answer -- the graph outline names objects that way, and its row menu's
    Hide / Delete Track carry those names -- before a leaf match that could
    pick another object of the same leaf name."""

    def _controller(self, *shots):
        """A controller over one shot per *shots* entry (its objects)."""

        store = ShotStore()
        for i, objects in enumerate(shots):
            store.define_shot(f"S{i}", i * 100, i * 100 + 50, objects=objects)
        ctrl = ShotSequencerController.__new__(ShotSequencerController)
        ctrl._sequencer = ShotSequencer(store=store)
        return ctrl

    def test_a_held_name_resolves_to_itself(self):
        # The earlier shot's object shares the later one's leaf name.
        ctrl = self._controller(["|grp|wrench"], ["wrench"])
        self.assertEqual(ctrl._resolve_full_name("wrench"), "wrench")
        self.assertEqual(ctrl._resolve_full_name("|grp|wrench"), "|grp|wrench")

    def test_a_leaf_name_still_finds_its_object(self):
        ctrl = self._controller(["|grp|nut"])
        self.assertEqual(ctrl._resolve_full_name("nut"), "|grp|nut")

    def test_every_track_label_resolves_back_to_its_object(self):
        # The track header's Hide / Delete Track hand a track's label back
        # through ``_resolve_full_name``.  Labelled by leaf name alone, two
        # held objects of one leaf name (path-held, or one held bare) sent
        # each other's actions to the same object.
        cmds.file(new=True, force=True)
        cmds.group(empty=True, name="grp")
        for name in ("wrench", "bolt", "nut"):
            cmds.createNode("transform", name=name, parent="grp")
        for name in ("wrench", "bolt"):
            cmds.createNode("transform", name=name)
        ctrl = self._controller(
            ["|grp|wrench", "|grp|bolt"], ["wrench", "|bolt", "|grp|nut"]
        )
        ctrl._track_order_scope = "global"

        class _Widget:
            @staticmethod
            def add_track(label, **_kw):
                return label

        objects = ["|grp|wrench", "wrench", "|grp|bolt", "|bolt", "|grp|nut"]
        labels = ctrl._build_tracks(_Widget(), objects, objects)
        self.assertEqual(labels["|grp|nut"], "nut")
        for obj in objects:
            self.assertEqual(ctrl._resolve_full_name(labels[obj]), obj)


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestDeleteStaleShots(unittest.TestCase):
    """The shot list's Delete Shots > Stale: names the shots whose objects and
    keys are gone, asks, and drops their records -- one undo step, and no
    key or live shot moves (a Delete Shot would close the gap behind each).
    Empty, the other narrow scope, takes every shot with nothing keyed in it."""

    def setUp(self):
        from types import SimpleNamespace

        _new_scene()
        gone = _make_cube("staleGone", {1: 0, 50: 5})
        self.live = _make_cube("staleLive", {120: 0, 160: 3})
        self.store = ShotStore()
        self.store.define_shot("Gone", 1, 50, [str(gone)])
        self.store.define_shot("Live", 120, 160, [str(self.live)])
        cmds.delete(gone)
        self.footer = []
        # The controller's own collaborators, and nothing that builds a widget.
        self.ctrl = SimpleNamespace(
            sequencer=SimpleNamespace(store=self.store),
            ui=None,
            _get_sequencer_widget=lambda: None,
            _after_shot_change=lambda: None,
            _set_footer=self.footer.append,
        )

    def _remove(self, button, scope="stale"):
        """Run the *scope* delete, answering its question with *button*; return
        the question's text.  Patched with a function, never a bare MagicMock: a
        QObject subclass faults natively on a mock attribute (uitk/CLAUDE.md)."""
        from unittest import mock

        asked = []

        def answer(*args, **kwargs):
            asked.append(args[2])
            return button

        with mock.patch.object(
            QtWidgets.QMessageBox, "question", new=staticmethod(answer)
        ):
            ShotSequencerController.delete_shots(self.ctrl, scope)
        return asked[0] if asked else ""

    def test_confirmed_it_drops_only_the_stale_and_moves_no_key(self):
        asked = self._remove(QtWidgets.QMessageBox.Yes)
        self.assertIn("Gone [1–50]", asked)
        self.assertEqual([s.name for s in self.store.shots], ["Live"])
        self.assertEqual(
            cmds.keyframe(self.live, q=True, timeChange=True), [120.0, 160.0]
        )
        self.assertEqual(self.footer, ["Deleted 1 stale shot(s)"])

    def test_declined_it_drops_nothing(self):
        self._remove(QtWidgets.QMessageBox.Cancel)
        self.assertEqual([s.name for s in self.store.shots], ["Gone", "Live"])

    def test_one_undo_puts_them_back(self):
        self._remove(QtWidgets.QMessageBox.Yes)
        self.assertTrue(self.store.restore_boundary_snapshot())
        self.assertEqual(sorted(s.name for s in self.store.shots), ["Gone", "Live"])

    def test_the_empty_scope_takes_every_shot_that_holds_nothing(self):
        """A new shot never filled, past the animation (no member, no key);
        one that names a live object keyed only outside it (2026-10-10:
        "delete empty is leaving behind empty shots"); and the stale one."""
        self.store.define_shot("Unfilled", 200, 240)
        self.store.define_shot("Cleared", 170, 190, [str(self.live)])
        asked = self._remove(QtWidgets.QMessageBox.Yes, scope="empty")
        for row in ("Unfilled [200–240]", "Cleared [170–190]", "Gone [1–50]"):
            self.assertIn(row, asked)
        self.assertIn("nothing keyed in their frames", asked)
        self.assertEqual([s.name for s in self.store.shots], ["Live"])
        self.assertEqual(self.footer, ["Deleted 3 empty shot(s)"])
        self.assertEqual(
            cmds.keyframe(self.live, q=True, timeChange=True), [120.0, 160.0]
        )


# =========================================================================
# Controller tests -- a FakeSlots host, as the real-scene harness builds it
# =========================================================================


class _FakeSlots:
    """What the controller is built from: the real ``mtk``, a switchboard that
    resolves uitk's names, and a mock window around a live widget."""

    def __init__(self, widget):
        self.sb = _Switchboard(tk=mtk)
        self.tk = mtk
        self.ui = mock.MagicMock()
        self.ui.sequencer_widget = widget
        self.ui.cmb_shot = ComboBox()


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class _ControllerCase(unittest.TestCase):
    """Two shots over two cubes, a controller driving a live widget."""

    def setUp(self):
        _new_scene()
        self.a = _make_cube("ctlA", {0: 0, 40: 5})
        self.b = _make_cube("ctlB", {60: 0, 100: 5})
        self.store = ShotStore()
        self.store.define_shot("S0", 0, 50, [str(self.a)])
        self.store.define_shot("S1", 60, 120, [str(self.b)])
        # The panel's store is the scene's active one, which follows Maya's
        # undo itself (ShotStore.follow_native_step) -- as in production.
        ShotStore.clear_active()
        ShotStore.set_active(self.store)
        self.widget = SequencerWidget()
        self.widget.resize(900, 400)
        self.widget.show()
        self.slots = _FakeSlots(self.widget)
        self.ctrl = ShotSequencerController(self.slots)
        self.ctrl.sequencer = ShotSequencer(store=self.store)
        _process_events()

    def tearDown(self):
        try:
            self.ctrl.remove_callbacks()
        except Exception:
            pass
        ShotStore.clear_active()
        self.widget.close()
        self.widget.deleteLater()
        _process_events()

    def _shot(self, name):
        return self.store.shot_by_name(name)

    def _keys(self, cube):
        return sorted(cmds.keyframe(cube, q=True, at="translateX") or [])


class TestCallbackIdempotency(_ControllerCase):
    """Each scene hook registers once and comes off whole, against Maya's own
    callbacks (2026-04-13: the registrations had no guard and appended
    duplicate ids; a failed removal blocked re-registration).  Moved here from
    the retired ``mock_tests/test_sequencer_controller.py``, whose module-wide
    skip meant none of it ran."""

    def _undo_followers(self):
        """How often the controller listens for the store's native undo."""
        return ShotStore._native_step_listeners.count(self.ctrl._on_native_step)

    def test_each_registration_is_idempotent(self):
        self.ctrl._register_scene_callbacks()
        watch = self.ctrl._scene_watch
        ids = (watch.keyframe_cb, watch.time_change_cb)

        self.ctrl._register_scene_callbacks()

        self.assertEqual(self._undo_followers(), 1)
        self.assertIs(self.ctrl._scene_watch, watch, "one watcher, re-attached")
        self.assertIsNotNone(ids[0])
        self.assertIsNotNone(ids[1])
        self.assertEqual((watch.keyframe_cb, watch.time_change_cb), ids)

    def test_remove_clears_every_hook_and_registration_works_again(self):
        self.ctrl._register_scene_callbacks()
        watch = self.ctrl._scene_watch

        self.ctrl.remove_callbacks()
        self.assertEqual(self._undo_followers(), 0)
        self.assertIsNone(self.ctrl._scene_watch)
        self.assertFalse(watch.active, "the watcher's callbacks came off")
        self.assertIsNone(watch.keyframe_cb)
        self.assertIsNone(watch.time_change_cb)

        self.ctrl._register_scene_callbacks()
        self.assertEqual(self._undo_followers(), 1)
        self.assertIsNotNone(self.ctrl._scene_watch.keyframe_cb)
        self.assertIsNotNone(self.ctrl._scene_watch.time_change_cb)

    def test_remove_stops_the_keyframe_debounce(self):
        from unittest.mock import MagicMock

        timer = MagicMock()
        self.ctrl._keyframe_debounce = timer

        self.ctrl.remove_callbacks()

        timer.stop.assert_called_once()
        self.assertIsNone(self.ctrl._keyframe_debounce)

    def test_the_panel_redraws_once_after_its_store_followed_an_undo(self):
        """Only for a step that put this panel's store's restore point back:
        an unrelated undo's keys reach the panel through the keyframe
        callback, and another scene's store is not this panel's."""
        from unittest.mock import patch
        from pythontk import NativeStepFollowed

        self.ctrl._register_scene_callbacks()
        with patch.object(self.ctrl, "_after_shot_change") as redraw:
            ShotStore._on_native_step()  # nothing to put back
            redraw.assert_not_called()
            self.ctrl._on_native_step(NativeStepFollowed(applied=1, store=ShotStore()))
            redraw.assert_not_called()
            self.ctrl._on_native_step(NativeStepFollowed(applied=0, store=self.store))
            redraw.assert_not_called()
            self.ctrl._on_native_step(NativeStepFollowed(applied=1, store=self.store))
            redraw.assert_called_once_with()


class TestToolMarkersOnTheTimeline(_ControllerCase):
    """A Build's markers (the Shot Manifest's Marker mode) reach the timeline
    when they are written, and keep the owner tag a Build finds them by
    through the sequencer's own marker edits -- each of which rewrites EVERY
    marker from the widget (2026-10-11: "adding a marker in the sequencer
    instead of keying")."""

    TAG = {
        "owner": "shot_manifest",
        "shot_id": 0,
        "behavior": "fade_in",
        "objects": ["ctlA"],
    }

    def setUp(self):
        super().setUp()
        # The panel binds the ACTIVE store; this one is the fixture's.
        self.store.add_listener(self.ctrl._on_store_event)
        self.addCleanup(self.store.remove_listener, self.ctrl._on_store_event)
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        _process_events()

    def test_a_written_marker_shows_and_keeps_its_tag(self):
        self.store.set_markers(
            [
                {
                    "time": 0.0,
                    "note": "Fade In: ctlA",
                    "draggable": False,
                    "style": "diamond",
                    "data": dict(self.TAG),
                }
            ]
        )
        _process_events()
        (md,) = self.widget.markers()
        self.assertEqual(
            (md.time, md.note, md.style), (0.0, "Fade In: ctlA", "diamond")
        )
        self.assertEqual(md.data, self.TAG)
        # A hand's marker, added then moved: the store is rewritten from the
        # widget, the Build's marker with it.
        hand = self.widget.add_marker(time=30.0, note="mine")
        self.ctrl.on_marker_added(hand, 30.0)
        self.widget.get_marker(hand).time = 35.0
        self.ctrl.on_marker_moved(hand, 35.0)
        self.assertEqual([m.get("data") for m in self.store.markers], [self.TAG, None])
        self.assertEqual(self.store.markers[1]["time"], 35.0)

    def test_a_legacy_marker_reads_with_the_defaults(self):
        """A marker saved before style, line, opacity, drag or payload
        existed draws as the defaults say."""
        self.store.set_markers([{"time": 5.0, "note": "", "color": "#E8A84A"}])
        _process_events()
        (md,) = self.widget.markers()
        self.assertEqual(
            (md.draggable, md.style, md.line_style, md.opacity, md.data),
            (True, "triangle", "dashed", 1.0, {}),
        )


class TestActiveShotAtPlayhead(_ControllerCase):
    """The panel opens on the shot under the playhead, not the first one."""

    def test_first_sync_selects_the_shot_under_the_playhead(self):
        cmds.currentTime(80)
        self.ctrl._sync_combobox()
        self.assertEqual(self.ctrl.active_shot_id, self._shot("S1").shot_id)
        self.ctrl._sync_to_widget()
        self.assertEqual(self.widget.range_highlight(), (60.0, 120.0))

    def test_outside_every_shot_the_first_stands_in(self):
        cmds.currentTime(55)
        self.ctrl._sync_combobox()
        self.assertEqual(self.ctrl.active_shot_id, self._shot("S0").shot_id)

    def test_a_store_selection_wins_over_the_playhead(self):
        cmds.currentTime(80)
        self.store.set_active_shot(self._shot("S0").shot_id)
        self.ctrl._sync_combobox()
        self.assertEqual(self.ctrl.active_shot_id, self._shot("S0").shot_id)


class TestAShortNamedMemberDrawsATrack(_ControllerCase):
    """A member is stored as it was given -- often a short name -- and the
    track builder's existence check compared it against ``ls -long`` paths,
    so ``ctlA`` read as missing next to ``|ctlA`` and drew no track at all
    unless it was pinned (found 2026-10-06 building this fixture)."""

    def test_a_short_named_member_gets_its_track(self):
        self.assertEqual(self._shot("S0").objects, ["ctlA"])
        # The membership reconcile re-points a short name at its long path
        # (``_resolved_name``) before the track builder runs, which left this
        # check reaching only names it had already rewritten: held off here,
        # the builder meets the short name itself.
        self.ctrl._reconcile_needed = False
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        self.assertEqual(self._shot("S0").objects, ["ctlA"], "reconciled anyway")
        self.assertIn("ctlA", [t.name for t in self.widget.tracks()])


class TestSystemSamplesDrawNoDot(_ControllerCase):
    """The shot system's claimed bound samples shape the curve but are not
    the animator's keys: an expanded track draws no dot for them, so a
    navigation or snap never stops on one either.

    Reported 2026-10-06: "auto generated border keys ... cause clutter in the
    sequencer" -- every claimed sample drew a key dot on the shot's bound.
    """

    def test_a_claimed_sample_has_no_dot(self):
        # Keys 0, 40, 45: the one at 40 is claimed, INSIDE the clip's span, so
        # only the flag can hide its dot (out of span a dot hides anyway).
        cmds.setKeyframe(self.a, attribute="translateX", time=45, value=9)
        crv = cmds.listConnections(f"{self.a}.translateX", type="animCurve")[0]
        sid = self._shot("S0").shot_id
        self.store.edit_ledger.record_key(crv, 40.0, sid, "end")
        self.store.set_active_shot(sid)
        self.ctrl._sync_to_widget(shot_id=sid)
        tid = next(t.track_id for t in self.widget.tracks() if t.name == "ctlA")
        self.widget.expand_track(tid)
        _process_events()
        dots = {
            round(k._time): k.isVisible()
            for c in self.widget.clips()
            if c.sub_row and c.track_id == tid
            for k in self.widget._clip_items[c.clip_id]._keyframe_items
        }
        self.assertTrue(dots.get(0) and dots.get(45), dots)
        self.assertIs(dots.get(40), False, "the claimed sample drew a dot")


class TestANewShotTakesThePlayhead(_ControllerCase):
    """Creating a shot moves the playhead to its start (2026-10-06)."""

    def test_the_one_click_new_shot(self):
        cmds.currentTime(10)
        self.ctrl._create_shot_one_click()
        shot = self.ctrl.sequencer.shot_by_id(self.ctrl.active_shot_id)
        self.assertNotIn(shot.name, ("S0", "S1"))
        self.assertEqual(cmds.currentTime(q=True), shot.start)

    def test_an_inserted_shot(self):
        cmds.currentTime(10)
        self.ctrl._insert_shot(self._shot("S1").shot_id, before=True)
        shot = self.ctrl.sequencer.shot_by_id(self.ctrl.active_shot_id)
        self.assertNotIn(shot.name, ("S0", "S1"))
        self.assertEqual(cmds.currentTime(q=True), shot.start)


class TestChangingShotsMovesThePlayhead(_ControllerCase):
    """A shot change puts the playhead on the new shot's first frame, behind
    one global header option that is on by default (2026-10-07: "the playhead
    is still not moving to the start of a shot when we change shots.  this
    should be a global option in the shot sequencer header").  Every way of
    changing shots takes the same path."""

    def setUp(self):
        super().setUp()
        cmds.currentTime(10)
        self.store.set_active_shot(self._shot("S0").shot_id)
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()

    def _now(self):
        return cmds.currentTime(q=True)

    def test_the_option_is_on_by_default(self):
        self.assertTrue(self.ctrl._playhead_to_shot_start)

    def test_next_shot(self):
        self.ctrl._navigate_shot(1)
        self.assertEqual(self._now(), 60.0)

    def test_the_dropdown(self):
        from types import SimpleNamespace
        from tentacle.slots.tools.shot_sequencer import ShotSequencerSlots

        cmb = self.slots.ui.cmb_shot
        idx = next(
            i for i in range(cmb.count()) if cmb.itemData(i) == self._shot("S1").shot_id
        )
        host = SimpleNamespace(ui=self.slots.ui, controller=self.ctrl)
        ShotSequencerSlots.cmb_shot(host, idx)
        self.assertEqual(self.store.active_shot_id, self._shot("S1").shot_id)
        self.assertEqual(self._now(), 60.0)

    def test_a_click_on_a_shot_block(self):
        self.ctrl.on_shot_block_clicked("S1")
        self.assertEqual(self._now(), 60.0)

    def test_a_shot_picked_in_another_panel(self):
        """The Shots window, the manifest's Open in Shot Sequencer."""
        # The panel listens to the ACTIVE store; this fixture's is not one.
        self.store.add_listener(self.ctrl._on_store_event)
        self.addCleanup(self.store.remove_listener, self.ctrl._on_store_event)
        self.store.set_active_shot(self._shot("S1").shot_id)
        self.assertEqual(self._now(), 60.0)

    def test_a_slot_filled_after_a_delete_is_no_shot_change(self):
        """The Shots window selects the first shot once the active one is
        deleted: that fills an empty slot, the user changed no shot."""
        self.store.add_listener(self.ctrl._on_store_event)
        self.addCleanup(self.store.remove_listener, self.ctrl._on_store_event)
        self.store.set_active_shot(None)
        self.store.set_active_shot(self._shot("S1").shot_id)
        self.assertEqual(self._now(), 10.0)

    def test_the_shot_already_active_leaves_it(self):
        self.ctrl.on_shot_block_clicked("S0")
        self.assertEqual(self._now(), 10.0)

    def test_off_leaves_it_and_a_new_shot_too(self):
        self.ctrl._set_playhead_to_shot_start(False)
        self.ctrl._navigate_shot(1)
        self.assertEqual(self.store.active_shot_id, self._shot("S1").shot_id)
        self.assertEqual(self._now(), 10.0)
        self.ctrl._create_shot_one_click()
        self.assertEqual(self._now(), 10.0)

    def test_the_move_is_no_undo_step(self):
        """A view move: Ctrl+Z after it must reach the user's last edit."""
        cmds.undoInfo(state=True)
        cmds.setKeyframe(self.a, at="translateX", t=20, v=3.0)
        self.ctrl._navigate_shot(1)
        cmds.undo()
        self.assertNotIn(20.0, self._keys(self.a), "Ctrl+Z undid the key")


class TestAnEditDrawsOnce(_ControllerCase):
    """``ShotsEdited`` -- every ``scene_edit``'s announcement, for the panels
    that did not make the edit -- is not a reason for the sequencer to draw
    again: it redraws after its own edits, so reacting drew each twice."""

    def test_the_announcement_draws_nothing(self):
        from unittest.mock import patch
        from pythontk import ShotsEdited

        with patch.object(self.ctrl, "_sync_to_widget") as draw:
            self.ctrl._on_store_event(ShotsEdited(label="trim"))
        draw.assert_not_called()


class TestAnExportCreditsNoKeyToTheActiveShot(_ControllerCase):
    """Bug: with the Shot Sequencer open, an export's own key edits -- its
    tie and snap, put back after the write -- were banked as the user's
    keying, and the keying refresh added an object keyed in the active
    shot's frames to its members (blendertk measured it on a Unity send,
    2026-10-05).
    Fixed: 2026-10-11 -- the export is a transient edit
    (``ShotStore.transient_edit``) and the listeners bank nothing inside it.
    Maya reports the edits' keyframe callback at the next idle, after the
    bracket closed: armed then, the refresh fell back to the SELECTION and
    took a selected keyed non-member in (fresh GUI Maya, 2026-10-11), so
    that echo arms nothing.  The harness never idles: the echo is delivered
    by hand, as Maya's idle would."""

    def setUp(self):
        super().setUp()
        # Keyed inside S0 and not one of its members; the tie keys it out to
        # the export set's range.  Selected: what the refresh's fallback reads.
        self.c = _make_cube("ctlC", {10: 0, 30: 5})
        self.store.set_active_shot(self._shot("S0").shot_id)
        self.ctrl._extend_to_keys = True
        self.ctrl._edited_items.clear()
        # Maya's scene hooks are the host's watcher's (SequencerHost.watch_scene).
        self.watch = self.ctrl._scene_watch
        self.watch._pending.clear()
        self.watch._transient_echo = False
        cmds.select(str(self.c), replace=True)
        _process_events()

    def _idle(self):
        """Maya's idle after an edit: the batched keyframe callback, then the
        debounce's refresh if it armed."""
        self.watch._on_keyframe_edited()
        timer = self.ctrl._keyframe_debounce
        armed = timer is not None and timer.isActive()
        if armed:
            timer.stop()
            self.ctrl._on_keyframe_debounce_fire()
        return armed

    def _export(self):
        import pythontk as ptk
        from mayatk.env_utils.scene_exporter._scene_exporter import SceneExporter

        with ptk.TempArtifacts(prefix="mtk_transient_export_") as tmp:
            return SceneExporter(log_level="ERROR").perform_export(
                export_dir=str(tmp.dir_path()),
                objects=[str(self.a), str(self.c)],
                output_name="transient",
                export_visible=False,
                tasks={"tie_all_keyframes": True, "snap_keys_to_frame": True},
            )

    def _state(self):
        shot = self._shot("S0")
        return sorted(o.split("|")[-1] for o in shot.objects), shot.start, shot.end

    def test_an_exports_key_edits_join_and_grow_no_shot(self):
        before = self._state()
        c_keys = sorted(cmds.keyframe(str(self.c), q=True, tc=True) or [])
        self.assertTrue(self._export())
        self.assertEqual(
            sorted(cmds.keyframe(str(self.c), q=True, tc=True) or []),
            c_keys,
            "the export put its tie back",
        )
        banked = set(self.watch._pending) | self.ctrl._edited_items
        _process_events()
        armed = self._idle()
        self.assertEqual(self._state(), before)
        self.assertEqual(banked, set(), "nothing banked")
        self.assertFalse(armed, "the edits' idle echo armed the refresh")

    def test_the_animators_next_key_still_joins_the_shot(self):
        """The echo is consumed once: a key set after the export arms the
        refresh, and the keyed object joins the active shot."""
        self.assertTrue(self._export())
        self._idle()
        cmds.setKeyframe(str(self.c), attribute="translateY", t=20, v=2.0)
        self.assertTrue(self._idle(), "the animator's key armed nothing")
        self.assertIn("ctlC", self._state()[0])


class TestCopyToShotFromThePanel(_ControllerCase):
    """The panel's Copy to Shot (2026-10-07): the originals stay, the copy
    lands in the destination, the footer says Copied, and one Ctrl+Z takes
    the copy back."""

    def test_a_copied_clip_lands_and_one_undo_takes_it_back(self):
        cmds.undoInfo(state=True, infinity=True)
        footers = []
        self.ctrl._set_footer = lambda text, **_kw: footers.append(text)
        s0, s1 = self._shot("S0"), self._shot("S1")
        seqs = [
            sq
            for sq in self.ctrl.sequencer.collect_shot_sequences(
                s0.shot_id, include_audio=False
            )
            if sq["obj"].split("|")[-1] == "ctlA"
        ]
        self.assertTrue(seqs)
        self.ctrl._send_to_shot(seqs, s1.shot_id, copy=True)
        keys = self._keys(self.a)
        self.assertTrue({0.0, 40.0} <= set(keys), f"the originals stay: {keys}")
        s1 = self._shot("S1")
        self.assertTrue(
            [t for t in keys if s1.start <= t <= s1.end], f"nothing landed: {keys}"
        )
        self.assertEqual(footers[-1], "Copied 1 clip to S1")
        cmds.undo()
        self.assertEqual(self._keys(self.a), [0.0, 40.0], "one undo takes it back")

    def test_audio_alone_is_not_copied(self):
        footers = []
        self.ctrl._set_footer = lambda text, **_kw: footers.append(text)
        self.ctrl._send_to_shot(
            [{"kind": "audio", "obj": "trk", "start": 0.0, "end": 10.0}],
            self._shot("S1").shot_id,
            copy=True,
        )
        self.assertEqual(footers, ["Copy to Shot: audio clips are not copied."])

    def test_a_refused_landing_is_reported_not_raised(self):
        """A landing that would make two shots share a sample whose poses
        disagree is refused by the engine; the menu says so in the footer
        (the shot lane's edits do) instead of handing over a traceback."""
        from unittest.mock import patch
        from pythontk import ShotBoundaryConflict

        footers = []
        self.ctrl._set_footer = lambda text, **_kw: footers.append(text)
        seqs = self.ctrl.sequencer.collect_shot_sequences(
            self._shot("S0").shot_id, include_audio=False
        )
        with patch.object(
            self.ctrl.sequencer,
            "copy_sequences_to_shot",
            side_effect=ShotBoundaryConflict([("ctlA_translateX", 60.0, [5.0, 0.0])]),
        ):
            self.ctrl._send_to_shot(seqs, self._shot("S1").shot_id, copy=True)
        self.assertTrue(footers[-1].startswith("Copy to Shot: "), footers)
        self.assertIn("ctlA_translateX", footers[-1])


class TestANewShotUndoes(_ControllerCase):
    """A new shot is one undo step, from Maya's own Ctrl+Z as from the
    panel's, and every view follows it back.  Reported 2026-10-07: "new shot
    creation is not undoable, or if it is, the sequencer doesn't refresh
    properly" -- both were true: the first shot of a scene changed nothing
    Maya records, so Maya's undo went to the operation before it, and the
    panel's undo put the store back but left the dropdown and the highlight
    on the shot it had just removed."""

    def setUp(self):
        super().setUp()
        cmds.undoInfo(state=True, infinity=True)
        self.store.set_active_shot(self._shot("S0").shot_id)
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()

    def _listed(self):
        cmb = self.ctrl.ui.cmb_shot
        return [cmb.itemData(i) for i in range(cmb.count())]

    def _assert_back_on_s0(self):
        s0 = self._shot("S0")
        self.assertEqual([s.name for s in self.store.sorted_shots()], ["S0", "S1"])
        self.assertEqual(self._listed(), [s0.shot_id, self._shot("S1").shot_id])
        self.assertEqual(self.store.active_shot_id, s0.shot_id, "the shot it was on")
        self.assertEqual(self.ctrl.active_shot_id, s0.shot_id)
        self.assertEqual(self.widget.range_highlight(), (s0.start, s0.end))

    def test_mayas_undo_takes_back_the_first_shot_of_a_scene(self):
        for shot in list(self.store.shots):
            self.store.remove_shot(shot.shot_id)
        self.ctrl._sync_combobox()
        cmds.setKeyframe(self.a, at="translateY", t=5, v=1)  # the op before it
        self.ctrl._create_shot_one_click()
        self.assertEqual(len(self.store.shots), 1)
        cmds.undo()
        _process_events()
        self.assertEqual(self.store.shots, [], "Maya's undo reached the new shot")
        self.assertEqual(self._listed(), [])
        self.assertEqual(
            cmds.keyframe(self.a, q=True, at="translateY"), [5.0], "not the op before"
        )
        cmds.redo()
        _process_events()
        self.assertEqual(len(self.store.shots), 1)
        self.assertEqual(self.store.active_shot_id, self.store.shots[0].shot_id)

    def test_the_panels_undo_puts_the_dropdown_and_view_back(self):
        self.ctrl._create_shot_one_click()
        new_id = self.store.active_shot_id
        self.assertIn(new_id, self._listed())
        self.ctrl.on_undo()
        _process_events()
        self._assert_back_on_s0()
        self.ctrl.on_redo()
        _process_events()
        self.assertIn(new_id, self._listed())
        self.assertEqual(self.ctrl.active_shot_id, new_id, "redo: the new one again")

    def test_mayas_undo_puts_the_dropdown_and_view_back(self):
        self.ctrl._create_shot_one_click()
        cmds.undo()
        _process_events()
        self._assert_back_on_s0()

    def test_an_inserted_shot_undoes(self):
        self.ctrl._insert_shot(self._shot("S1").shot_id, before=True)
        self.assertEqual(len(self.store.shots), 3)
        cmds.undo()
        _process_events()
        self._assert_back_on_s0()
        self.assertEqual(self._keys(self.b), [60.0, 100.0], "the ripple went back")

    def test_a_detected_shot_undoes(self):
        """It was defined outside any scene_edit: no restore point, so no
        undo at all."""
        from types import SimpleNamespace
        from unittest import mock

        from tentacle.slots.tools._shot_sequencer.shot_edit_dialog import (
            ShotEditDialog,
        )
        from tentacle.slots.tools.shot_sequencer import ShotSequencerSlots

        cand = {"name": "Shot_1", "start": 130.0, "end": 170.0, "objects": []}
        self.ctrl.sequencer.detect_next_shot = lambda **_kw: cand
        panel = SimpleNamespace(controller=self.ctrl, ui=None, tk=mtk)
        with mock.patch.object(
            ShotEditDialog,
            "show",
            return_value=("Detected", 130.0, 170.0, ""),
        ):
            ShotSequencerSlots._detect_next_shot(panel)
        detected = self.store.shot_by_name("Detected")
        self.assertIsNotNone(detected)
        self.assertEqual(self.ctrl.active_shot_id, detected.shot_id)
        self.assertEqual(cmds.currentTime(q=True), 130.0, "the playhead landed")
        cmds.undo()
        _process_events()
        self._assert_back_on_s0()


class TestTheEditedShotIsTheOneShown(_ControllerCase):
    """An edit made on a shot other than the active one -- the shot lane's
    menu reaches every band -- draws THAT shot, so it becomes the active one:
    the timeline showed it while the dropdown and Maya's playback range stayed
    on the other (found in review, 2026-10-07)."""

    def test_padding_another_shot_makes_it_active(self):
        s0, s1 = self._shot("S0"), self._shot("S1")
        self.store.set_active_shot(s0.shot_id)
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        self.ctrl._add_shot_space(s1.shot_id, 10, "trailing")
        s1 = self._shot("S1")
        self.assertEqual(self.store.active_shot_id, s1.shot_id)
        self.assertEqual(self.ctrl.active_shot_id, s1.shot_id, "the dropdown")
        self.assertEqual(self.widget.range_highlight(), (s1.start, s1.end))


class TestEditShotOpensThePinnedShotsWindow(_ControllerCase):
    """Edit Shot opens the Shots window PINNED (2026-10-06): opened from the
    sequencer to edit a shot, it has to stay up while the user works in it,
    and its pin button then reads as the one that puts it away."""

    class _Window:
        def __init__(self, buttons=("pin",)):
            from types import SimpleNamespace

            self.pinned = False
            self.header = SimpleNamespace(buttons={b: object() for b in buttons})

        def set_pinned(self, value):
            self.pinned = bool(value)

    def test_edit_shot_pins_the_window(self):
        window = self._Window()
        self.slots.sb.handlers.marking_menu.show.return_value = window
        self.ctrl._edit_shot_dialog(self._shot("S1"))
        self.slots.sb.handlers.marking_menu.show.assert_called_with("shots")
        self.assertTrue(window.pinned)
        self.assertEqual(self.store.active_shot_id, self._shot("S1").shot_id)

    def test_a_window_with_no_pin_button_is_left_unpinned(self):
        """A pinned window refuses hide(); with no pin button to undo it, it
        would be stranded on screen.  Such a window never auto-hides anyway."""
        window = self._Window(buttons=("hide",))
        self.slots.sb.handlers.marking_menu.show.return_value = window
        self.ctrl._edit_shot_dialog(self._shot("S1"))
        self.assertFalse(window.pinned)


class TestShotLaneMenu(_ControllerCase):
    """The shot menu: a compact root whose verbs fan out into their forms."""

    @staticmethod
    def _rows(lst):
        return [w.text() for w in lst._row_widgets() if hasattr(w, "text")]

    def test_root_is_compact_and_rows_fan_out(self):
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        menu = self.ctrl._build_shot_lane_context_menu(30.0)
        try:
            root = self._rows(menu.list)
            self.assertEqual(root[0], 'Edit "S0"\u2026')
            for label in (
                "New Shot",
                "Split Here (30)",
                "Merge",
                "Move To",
                "Add Frames",
                "Trim Empty Space",
            ):
                self.assertIn(label, root)
            self.assertNotIn("Trim Leading Space", root, "lives in the flyout")
            self.assertNotIn("Refresh", root, "the header refreshes")
            # 2026-10-10: "the shot context menu should also have a delete
            # shot button" -- last, the one row that takes keys with it.
            self.assertEqual(root[-1], 'Delete "S0"\u2026')
            by_text = {
                w.text(): w for w in menu.list._row_widgets() if hasattr(w, "text")
            }
            self.assertEqual(
                self._rows(by_text["Trim Empty Space"].sublist),
                ["Trim Leading Space", "Trim Trailing Space"],
            )
            self.assertTrue(by_text["Trim Empty Space"].property("contextAction"))
            self.assertEqual(
                self._rows(by_text["New Shot"].sublist),
                ["Insert Shot Before", "Insert Shot After"],
            )
            split = self._rows(by_text["Split Here (30)"].sublist)
            self.assertEqual(len(split), 1)
            self.assertTrue(split[0].startswith("Split at Current Time"), split[0])
        finally:
            menu.dispose()

    def test_shot_menu_is_only_about_the_shot(self):
        """Key edits belong to a key selection and display toggles to the
        timeline; both used to hang off this menu."""
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        menu = self.ctrl._build_shot_lane_context_menu(30.0)
        try:
            root = self._rows(menu.list)
            for gone in (
                'Select "S0"',
                "Keys",
                "Tangents",
                "Extend to Keys",
                "Timeline",
            ):
                self.assertNotIn(gone, root)
        finally:
            menu.dispose()

    def test_delete_row_deletes_the_shot_under_the_click(self):
        from unittest import mock

        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        menu = self.ctrl._build_shot_lane_context_menu(90.0)  # over S1
        try:
            row = next(
                w
                for w in menu.list._row_widgets()
                if hasattr(w, "text") and w.text() == 'Delete "S1"…'
            )
            with mock.patch.object(
                QtWidgets.QMessageBox,
                "question",
                return_value=QtWidgets.QMessageBox.Yes,
            ):
                row.click()
            _process_events()
        finally:
            menu.dispose()
        self.assertEqual([s.name for s in self.store.shots], ["S0"])

    def test_outside_every_shot_only_creation_remains(self):
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        menu = self.ctrl._build_shot_lane_context_menu(55.0)
        try:
            self.assertEqual(self._rows(menu.list), ["New Shot"])
        finally:
            menu.dispose()

    def test_timeline_has_its_own_menu(self):
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        menu = self.ctrl._build_timeline_context_menu(30.0)
        try:
            rows = self._rows(menu.list)
            self.assertEqual(rows[0], "Add Marker at 30\u2026")
            self.assertIn("Show Gap Overlays", rows)
            self.assertNotIn("Refresh", rows, "the header button is the one Refresh")
        finally:
            menu.dispose()

    def test_move_to_lists_the_shots_in_running_order(self):
        """The flyout IS the running order, numbered as the user reads it.

        Where a pick lands, and which rows are inert, need more than two
        shots to mean anything -- see ``TestMoveToFlyout``.
        """
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        menu = self.ctrl._build_shot_lane_context_menu(30.0)
        try:
            by_text = {
                w.text(): w for w in menu.list._row_widgets() if hasattr(w, "text")
            }
            ordered = self.ctrl.sequencer.sorted_shots()
            self.assertEqual(
                self._rows(by_text["Move To"].sublist),
                [f"{i}. {s.name}" for i, s in enumerate(ordered, start=1)],
            )
        finally:
            menu.dispose()

    def test_move_to_position_reorders_and_pushes_the_rest_along(self):
        seq = self.ctrl.sequencer
        names_before = [s.name for s in seq.sorted_shots()]
        if len(names_before) < 2:
            self.skipTest("needs two shots to reorder")
        first = seq.sorted_shots()[0]
        self.ctrl.move_shot_to_position(first.shot_id, len(names_before))
        names_after = [s.name for s in seq.sorted_shots()]
        self.assertEqual(names_after[-1], names_before[0], "moved to the last slot")
        self.assertEqual(
            sorted(names_after), sorted(names_before), "no shot lost or duplicated"
        )


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestPanelHeader(unittest.TestCase):
    """The panel's chrome: one dismissal button (a tool panel is sticky: hide),
    and help kept short with the full guide linked.
    Added: 2026-10-11 (pin AND hide both showed)
    """

    def test_sticky_chrome_and_the_guide_link(self):
        from unittest.mock import MagicMock

        from uitk.widgets.header import Header
        from tentacle.slots.tools.shot_sequencer import ShotSequencerSlots

        slots = ShotSequencerSlots.__new__(ShotSequencerSlots)
        slots.controller = MagicMock()
        slots.sb = MagicMock()
        widget = MagicMock()
        slots.header_init(widget)
        widget.config_buttons.assert_called_with("refresh", "menu", "collapse", "hide")
        self.assertEqual(
            widget.set_help_text.call_args.kwargs["url"], ShotSequencerSlots.HELP_URL
        )
        self.assertTrue(ShotSequencerSlots.HELP_URL.endswith("docs/shot_sequencer.md"))
        header = Header()  # and a header asked for both keeps one
        self.addCleanup(header.deleteLater)
        header.config_buttons("refresh", "menu", "collapse", "pin", "hide")
        self.assertEqual(len({"pin", "hide"} & set(header.buttons)), 1)


@unittest.skipUnless(HAS_MAYA and HAS_QT, _SKIP_MSG)
class TestMoveToFlyout(unittest.TestCase):
    """Picking a shot lands the moved one in FRONT of it, both directions.

    Four shots on purpose: with two, "before the picked shot" and "at the
    picked shot's index" agree, so the off-by-one that only bites a
    downstream move is invisible.
    """

    NAMES = ("A", "B", "C", "D")

    def setUp(self):
        _new_scene()
        self.store = ShotStore()
        self.cubes = {}
        for i, name in enumerate(self.NAMES):
            start, end = i * 30, i * 30 + 20
            cube = _make_cube(f"mv{name}", {start: 0, end: 5})
            self.cubes[name] = cube
            self.store.define_shot(name, start, end, [str(cube)])
        # The scene's active store follows Maya's undo (as _ControllerCase).
        ShotStore.clear_active()
        ShotStore.set_active(self.store)
        self.addCleanup(ShotStore.clear_active)
        self.widget = SequencerWidget()
        self.widget.resize(900, 400)
        self.widget.show()
        self.ctrl = ShotSequencerController(_FakeSlots(self.widget))
        self.ctrl.sequencer = ShotSequencer(store=self.store)
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        _process_events()

    def tearDown(self):
        try:
            self.ctrl.remove_callbacks()
        except Exception:
            pass
        self.widget.close()
        self.widget.deleteLater()
        _process_events()

    def _order(self):
        return [s.name for s in self.ctrl.sequencer.sorted_shots()]

    def _pick(self, over_name, target_name):
        """Open the lane menu over *over_name* and click *target_name*'s row."""
        shot = self.store.shot_by_name(over_name)
        menu = self.ctrl._build_shot_lane_context_menu((shot.start + shot.end) / 2.0)
        try:
            rows = {w.text(): w for w in menu.list._row_widgets() if hasattr(w, "text")}
            sub = [
                w for w in rows["Move To"].sublist._row_widgets() if hasattr(w, "text")
            ]
            row = next(w for w in sub if w.text().endswith(target_name))
            self.assertTrue(row.isEnabled(), f"{row.text()} should be pickable")
            row.click()
            _process_events()
        finally:
            menu.dispose()

    def test_moving_downstream_lands_in_front_of_the_picked_shot(self):
        self.assertEqual(self._order(), ["A", "B", "C", "D"])
        self._pick("A", "C")
        self.assertEqual(self._order(), ["B", "A", "C", "D"])

    def test_moving_upstream_lands_in_front_of_the_picked_shot(self):
        self._pick("D", "B")
        self.assertEqual(self._order(), ["A", "D", "B", "C"])

    def test_moving_to_the_far_end_in_each_direction(self):
        self._pick("A", "D")
        self.assertEqual(self._order(), ["B", "C", "A", "D"])
        self._pick("A", "B")
        self.assertEqual(self._order(), ["A", "B", "C", "D"], "and back again")

    def test_the_rows_that_would_do_nothing_are_inert(self):
        """Its own row, and the neighbour it already sits in front of."""
        shot = self.store.shot_by_name("B")
        menu = self.ctrl._build_shot_lane_context_menu((shot.start + shot.end) / 2.0)
        try:
            rows = {w.text(): w for w in menu.list._row_widgets() if hasattr(w, "text")}
            state = {
                w.text()[-1]: w.isEnabled()
                for w in rows["Move To"].sublist._row_widgets()
                if hasattr(w, "text")
            }
            self.assertEqual(
                state, {"A": True, "B": False, "C": False, "D": True}, state
            )
        finally:
            menu.dispose()

    def test_undo_puts_the_dropdown_back_in_order(self):
        """The dropdown lists the shots; an undone reorder must reach it."""
        cmb = self.ctrl.ui.cmb_shot

        def labels():
            return [cmb.itemText(i).split()[0] for i in range(cmb.count())]

        before = labels()
        self.assertEqual(before, ["A", "B", "C", "D"], before)
        self._pick("A", "C")
        self.assertEqual(labels(), ["B", "A", "C", "D"])
        cmds.undo()
        _process_events()
        self.assertEqual(self._order(), ["A", "B", "C", "D"], "the store came back")
        self.assertEqual(labels(), before, "and so did the dropdown")

    def test_ruler_zone_routes_to_the_timeline_menu(self):
        """A right-click on the ruler is the timeline's, even over a shot."""
        seen = {}

        def _timeline(t):
            seen["t"] = t  # returns None: nothing for the caller to exec_

        self.ctrl._build_timeline_context_menu = _timeline
        self.ctrl._show_shot_lane_context_menu = lambda *a: seen.setdefault("shot", a)
        self.ctrl.on_zone_context_menu("ruler", 30.0, None)
        self.assertEqual(seen.get("t"), 30.0)
        self.assertNotIn("shot", seen)


class TestExtendToKeysOption(_ControllerCase):
    """One global option, capped by a reach; -1 means any distance."""

    def test_extend_grows_over_the_gap_key_within_reach(self):
        cmds.setKeyframe(self.a, at="translateX", t=55, v=6.0)
        self.ctrl._sync_combobox()
        self.ctrl._set_extend_reach(10)
        self.ctrl._extend_shot_to_keys(self._shot("S0").shot_id)
        self.assertEqual(self._shot("S0").end, 55.0)
        self.assertEqual(self._keys(self.a), [0.0, 40.0, 55.0], "the key stays")
        self.assertEqual(self._shot("S1").start, 65.0, "S1 rippled +5")

    def test_out_of_reach_leaves_the_shot(self):
        cmds.setKeyframe(self.a, at="translateX", t=58, v=6.0)
        self.ctrl._sync_combobox()
        self.ctrl._set_extend_reach(5)
        self.ctrl._extend_shot_to_keys(self._shot("S0").shot_id)
        self.assertEqual(self._shot("S0").end, 50.0)

    def test_minus_one_uncaps_the_reach(self):
        cmds.setKeyframe(self.a, at="translateX", t=58, v=6.0)
        self.ctrl._sync_combobox()
        self.ctrl._set_extend_reach(-1)
        self.assertIsNone(self.ctrl._extend_reach_arg, "-1 is the engine's None")
        self.ctrl._extend_shot_to_keys(self._shot("S0").shot_id)
        self.assertEqual(self._shot("S0").end, 58.0)

    def test_option_off_means_no_automatic_extend(self):
        cmds.setKeyframe(self.a, at="translateX", t=55, v=6.0)
        self.ctrl._sync_combobox()
        self.ctrl._set_extend_reach(10)
        self.ctrl._extend_to_keys = False
        self.assertFalse(self.ctrl._auto_extend_to_new_keys(self._shot("S0").shot_id))
        self.assertEqual(self._shot("S0").end, 50.0)

    def test_option_on_extends_on_a_keying_burst(self):
        cmds.setKeyframe(self.a, at="translateX", t=55, v=6.0)
        self.ctrl._sync_combobox()
        self.ctrl._set_extend_to_keys(True)
        self.ctrl._set_extend_reach(10)
        self.assertTrue(self.ctrl._auto_extend_to_new_keys(self._shot("S0").shot_id))
        self.assertEqual(self._shot("S0").end, 55.0)


class TestStashIsOneEntry(_ControllerCase):
    """Store Keys puts ONE thing away, however wide the gesture was.

    It used to call ``KeyStash.stash`` once per (object, attribute) job, so
    storing a three-channel selection left three clips to find, and to
    retrieve one at a time.
    """

    def setUp(self):
        super().setUp()
        from mayatk.anim_utils.key_stash._key_stash import KeyStash

        self.stash = KeyStash.active()
        for clip in list(self.stash.clips):
            self.stash.drop(clip.clip_id)
        for attr in ("translateY", "translateZ"):
            cmds.setKeyframe(self.a, at=attr, t=0, v=0.0)
            cmds.setKeyframe(self.a, at=attr, t=40, v=3.0)
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()

    def _targets(self, *attrs):
        sid = self._shot("S0").shot_id
        return [(str(self.a), a, [0.0, 40.0], sid) for a in attrs]

    def test_three_channels_stash_as_one_clip(self):
        before = len(self.stash.clips)
        self.ctrl._stash_key_targets(
            self._targets("translateX", "translateY", "translateZ")
        )
        self.assertEqual(
            len(self.stash.clips) - before, 1, "one gesture, one stash entry"
        )
        clip = self.stash.clips[-1]
        self.assertEqual(len(clip.curves), 3, "all three channels are IN that entry")
        self.assertEqual(clip.source_shot_id, self._shot("S0").shot_id)

    def test_two_objects_stash_as_one_clip(self):
        before = len(self.stash.clips)
        s0, s1 = self._shot("S0").shot_id, self._shot("S1").shot_id
        self.ctrl._stash_key_targets(
            [
                (str(self.a), "translateX", [0.0, 40.0], s0),
                (str(self.b), "translateX", [60.0, 100.0], s1),
            ]
        )
        self.assertEqual(len(self.stash.clips) - before, 1)
        clip = self.stash.clips[-1]
        self.assertEqual(len(clip.objects), 2)
        self.assertIsNone(
            clip.source_shot_id, "spanning two shots, it belongs to neither"
        )

    def test_only_the_named_channels_and_spans_are_taken(self):
        """A merged stash must not become a bounding box over the union.

        Asking for A.translateX and A.translateZ must leave translateY where
        it is -- the scope list is per target, not a range plus a channel
        set crossed together.
        """
        self.ctrl._stash_key_targets(self._targets("translateX", "translateZ"))
        self.assertEqual(
            sorted(cmds.keyframe(self.a, q=True, at="translateY") or []),
            [0.0, 40.0],
            "translateY was never asked for",
        )
        for gone in ("translateX", "translateZ"):
            self.assertFalse(
                cmds.keyframe(self.a, q=True, at=gone) or [],
                f"{gone} should have been parked",
            )

    def test_nothing_to_store_leaves_no_clip(self):
        before = len(self.stash.clips)
        self.ctrl._stash_key_targets(
            [(str(self.a), "translateX", [900.0, 950.0], self._shot("S0").shot_id)]
        )
        self.assertEqual(len(self.stash.clips), before, "no keys out there")


class TestKeySelectionEdits(_ControllerCase):
    """The Animation panel's key edits, scoped to a KEY selection.

    They used to be offered per shot, where "remove the intermediate keys"
    reached every member's every attribute over the whole span.
    """

    def setUp(self):
        super().setUp()
        # The panel's clipboard lives on the class (it survives a re-init).
        type(self.ctrl)._key_clipboard = {}

    def _targets(self, times=None):
        """The ``(obj, attr, times, shot_id)`` rows the key menu works from."""
        return [
            (
                str(self.a),
                "translateX",
                list(times or self._keys(self.a)),
                self._shot("S0").shot_id,
            )
        ]

    def test_the_edit_rows_are_spelled_as_blendertk_spells_them(self):
        """Pinned as a LITERAL: blendertk pins the same list, so a row added
        to one fork and not the other fails on the side that drifted."""
        self.assertEqual(
            [label for label, _m in self.ctrl._KEY_EDITS],
            [
                "Simplify",
                "Remove Intermediate Keys",
                "Snap Fractional Keys",
                "Invert Keys",
                "Align Keys",
                "Euler Filter",
            ],
        )

    def test_menu_offers_the_stash_and_edit_rows(self):
        from qtpy import QtWidgets

        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        menu = QtWidgets.QMenu()
        try:
            self.ctrl._add_key_edit_actions(menu, self._targets(), " (2)")
            labels = [a.text() for a in menu.actions() if a.text()]
            for want in ("Store Keys (2)", "Edit"):
                self.assertIn(want, labels)
            edit = next(a.menu() for a in menu.actions() if a.text() == "Edit")
            self.assertEqual(
                [a.text() for a in edit.actions()],
                [label for label, _m in self.ctrl._KEY_EDITS],
            )
        finally:
            menu.deleteLater()

    def test_no_menu_row_duplicates_a_bound_key(self):
        """Copy / Paste / Delete are Ctrl+C / Ctrl+V / Delete, not rows -- and
        no row reaches Maya's own clipboard (2026-10-10: removed, as blendertk
        has none; a Graph Editor view in the panel is the plan)."""
        from qtpy import QtWidgets

        menu = QtWidgets.QMenu()
        try:
            self.ctrl._add_key_edit_actions(menu, self._targets(), "")
            labels = " ".join(a.text() for a in menu.actions())
            for gone in ("Copy", "Paste", "Delete"):
                self.assertNotIn(gone, labels)
        finally:
            menu.deleteLater()

    def test_the_shortcut_resolves_its_own_targets(self):
        """A menu is handed its groups; a key press has to ask the widget."""
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        self.assertEqual(self.ctrl._selected_key_targets(), [], "nothing selected")
        widget = self.ctrl._get_sequencer_widget()
        groups = [{"clip_id": 123, "times": [0.0]}]
        widget.selected_keys = lambda: groups
        seen = []
        self.ctrl._key_targets = lambda w, g: seen.append((w, g)) or ["T"]
        self.assertEqual(self.ctrl._selected_key_targets(), ["T"])
        self.assertEqual(
            seen, [(widget, groups)], "the widget's selection, the menu's resolver"
        )

    def test_thin_keeps_only_the_outer_keys_of_the_selection(self):
        cmds.setKeyframe(self.a, at="translateX", t=20, v=2.0)
        self.assertEqual(self._keys(self.a), [0.0, 20.0, 40.0])
        self.ctrl._sync_combobox()
        self.ctrl._thin_selected_keys(self._targets([0.0, 20.0, 40.0]))
        self.assertEqual(self._keys(self.a), [0.0, 40.0])

    def test_snap_pulls_a_fractional_key_onto_a_whole_frame(self):
        cmds.setKeyframe(self.a, at="translateX", t=20.4, v=2.0)
        self.ctrl._sync_combobox()
        self.ctrl._snap_selected_keys(self._targets([0.0, 20.4, 40.0]))
        self.assertEqual(self._keys(self.a), [0.0, 20.0, 40.0])

    # -- the shot system's claims follow the key edits (mirror of blendertk) --

    def _claim(self, frame, behavior="fade_in"):
        """Claim cube A's translateX key at *frame* for a behavior of S0."""
        crv = cmds.keyframe(self.a, at="translateX", q=True, name=True)[0]
        self.ctrl.sequencer.ledger.record_authored(
            crv, frame, self._shot("S0").shot_id, behavior, str(self.a)
        )
        return crv

    def test_align_releases_the_claims_of_a_key_it_lands_on(self):
        """A key Align lands on is replaced and takes its claims with it: left
        on the frame, a behavior's claim passed to the arriving key, which the
        next Build deleted (BACKLOG 2026-10-04)."""
        cmds.setKeyframe(self.a, at="translateX", t=20, v=2.0)  # A: 0, 20, 40
        other = _make_cube("ctlC", {0: 1.0, 30: 2.0})
        crv = self._claim(0.0)
        sid = self._shot("S0").shot_id
        self.ctrl._sync_combobox()

        # Every selection starts on the earliest start (0): A's block lands
        # its 20 on A's own unselected, claimed 0.
        self.ctrl._align_selected_keys(
            [
                (str(other), "translateX", [0.0], sid),
                (str(self.a), "translateX", [20.0, 40.0], sid),
            ]
        )

        self.assertEqual(self._keys(self.a), [0.0, 20.0])
        led = self.ctrl.sequencer.ledger
        self.assertFalse(led.owns_any(crv, 0.0), led.to_dict())

    def test_invert_releases_the_claims_of_a_key_it_lands_on(self):
        for t, v in ((10, 1.0), (30, 3.0)):
            cmds.setKeyframe(self.a, at="translateX", t=t, v=v)  # A: 0, 10, 30, 40
        crv = self._claim(30.0)
        self.ctrl._sync_combobox()

        # Over [0, 40] the selected 10 lands on the unselected, claimed 30.
        self.ctrl._invert_selected_keys(self._targets([0.0, 10.0, 40.0]))

        self.assertEqual(self._keys(self.a), [0.0, 30.0, 40.0])
        led = self.ctrl.sequencer.ledger
        self.assertFalse(led.owns_any(crv, 30.0), led.to_dict())

    def test_invert_carries_the_claims_of_a_key_it_moves(self):
        """A claimed key the mirror MOVES keeps its claims: left at 10 they
        passed to the key arriving from 30, and the moved key read as the
        animator's."""
        for t, v in ((10, 1.0), (30, 3.0)):
            cmds.setKeyframe(self.a, at="translateX", t=t, v=v)  # A: 0, 10, 30, 40
        crv = self._claim(10.0)
        self.ctrl._sync_combobox()

        self.ctrl._invert_selected_keys(self._targets([0.0, 10.0, 30.0, 40.0]))

        led = self.ctrl.sequencer.ledger
        self.assertEqual(led.authored(), [(crv, 30.0)], led.to_dict())

    def test_paste_releases_the_claims_of_a_key_it_replaces(self):
        """Ctrl+V over a claimed key replaces it: its claims go with it."""
        cmds.setKeyframe(self.a, at="translateX", t=20, v=2.0)  # A: 0, 20, 40
        crv = self._claim(20.0)
        self.ctrl._sync_combobox()
        self.ctrl._copy_selected_keys(self._targets([40.0]))  # the value 5
        cmds.currentTime(20)

        self.ctrl._paste_selected_keys(self._targets([40.0]))

        self.assertEqual(
            cmds.keyframe(
                self.a, at="translateX", q=True, time=(20, 20), valueChange=True
            ),
            [5.0],
        )
        led = self.ctrl.sequencer.ledger
        self.assertFalse(led.owns_any(crv, 20.0), led.to_dict())

    def test_thin_releases_the_claims_of_the_keys_it_removes(self):
        """A deleted key takes its claims with it: left on the frame, a
        behavior's claim passed to the next key to land there."""
        cmds.setKeyframe(self.a, at="translateX", t=20, v=2.0)  # A: 0, 20, 40
        crv = self._claim(20.0)
        self.ctrl._sync_combobox()

        self.ctrl._thin_selected_keys(self._targets([0.0, 20.0, 40.0]))

        self.assertEqual(self._keys(self.a), [0.0, 40.0])
        led = self.ctrl.sequencer.ledger
        self.assertFalse(led.owns_any(crv, 20.0), led.to_dict())

    def test_simplify_releases_the_claims_of_the_keys_it_removes(self):
        """Both passes: a ramp key the reducer drops (the SHAPE pass) and a
        hold key the FLAT pass drops each give up their claims."""
        for f in range(0, 41, 4):  # a straight ramp: every middle key is neutral
            cmds.setKeyframe(self.a, at="translateX", t=f, v=float(f))
        cmds.keyTangent(self.a, at=["translateX"], itt="linear", ott="linear")
        crv = self._claim(8.0)
        self.ctrl._sync_combobox()

        self.ctrl._simplify_selected_keys(self._targets(self._keys(self.a)))

        self.assertEqual(self._keys(self.a), [0.0, 40.0])
        led = self.ctrl.sequencer.ledger
        self.assertFalse(led.owns_any(crv, 8.0), led.to_dict())

    def test_simplify_releases_the_claim_of_a_redundant_hold_key(self):
        for f, v in ((0, 1.0), (10, 1.0), (20, 1.0), (30, 1.0), (40, 0.0)):
            cmds.setKeyframe(self.a, at="translateX", t=f, v=v)
        cmds.keyTangent(self.a, at=["translateX"], ott="step")
        crv = self._claim(20.0)
        self.ctrl._sync_combobox()

        self.ctrl._simplify_selected_keys(self._targets(self._keys(self.a)))

        self.assertEqual(self._keys(self.a), [0.0, 40.0])
        led = self.ctrl.sequencer.ledger
        self.assertFalse(led.owns_any(crv, 20.0), led.to_dict())

    def _b_row(self, times):
        return [(str(self.b), "translateX", times, self._shot("S1").shot_id)]

    def _ott(self, cube, frame):
        crv = cmds.keyframe(cube, at="translateX", q=True, name=True)[0]
        return cmds.keyTangent(crv, q=True, time=(frame, frame), ott=True)[0]

    def _value(self, cube, frame):
        return cmds.keyframe(cube, at="translateX", q=True, t=(frame, frame), vc=True)

    def test_the_panels_copy_pastes_onto_another_object(self):
        """Ctrl+C / Ctrl+V are the panel's own clipboard (2026-10-10)."""
        self.ctrl._sync_combobox()
        self.ctrl._copy_selected_keys(self._targets([40.0]))  # A: the value 5
        cmds.currentTime(80)
        self.ctrl._paste_selected_keys(self._b_row([60.0]))
        self.assertEqual(self._keys(self.b), [60.0, 80.0, 100.0])
        self.assertEqual(self._value(self.b, 80), [5.0])

    def test_a_copied_gap_hold_pastes_as_the_key_was_before_the_hold(self):
        """2026-10-10: copying keys in the Graph Editor carried the shot
        system's gap hold -- the step it writes on the last key before a gap
        -- into the paste, as if the animator had keyed it."""
        self.ctrl._sync_combobox()
        self.ctrl.sequencer.reconcile_system_edits()  # holds A@40, before S1
        crv = cmds.keyframe(self.a, at="translateX", q=True, name=True)[0]
        claim = self.ctrl.sequencer.ledger.claimed_step(crv, 40.0)
        self.assertIsNotNone(claim, "the fixture's seam is not held")
        self.assertEqual(self._ott(self.a, 40), "step")

        self.ctrl._copy_selected_keys(self._targets([0.0, 40.0]))
        cmds.currentTime(70)
        self.ctrl._paste_selected_keys(self._b_row([60.0]))

        self.assertEqual(self._keys(self.b), [60.0, 70.0, 100.0, 110.0])
        self.assertEqual(self._ott(self.b, 110), claim[1])
        self.assertEqual(self._ott(self.a, 40), "step", "the source's hold stays")

    def test_a_step_pasted_over_a_held_seam_is_copied_as_a_step(self):
        """Bug: Ctrl+C read every step on a claimed seam as the system's
        hold, so the animator's own stepped key pasted over it (the claim
        stays on the frame) was copied with the old pre-hold tangent.
        Fixed: 2026-10-10"""
        self.ctrl._sync_combobox()
        self.ctrl.sequencer.reconcile_system_edits()  # holds A@40, before S1
        crv = cmds.keyframe(self.a, at="translateX", q=True, name=True)[0]
        self.assertIsNotNone(self.ctrl.sequencer.ledger.claimed_step(crv, 40.0))
        # What a Graph Editor paste leaves: another value, a fixed in side.
        cmds.setKeyframe(self.a, at="translateX", t=40, v=7.0)
        cmds.keyTangent(crv, time=(40, 40), itt="fixed", ott="step")

        self.ctrl._copy_selected_keys(self._targets([40.0]))
        cmds.currentTime(70)
        self.ctrl._paste_selected_keys(self._b_row([60.0]))

        self.assertEqual(self._value(self.b, 70), [7.0])
        self.assertEqual(self._ott(self.b, 70), "step")

    def test_the_held_value_pasted_with_another_slope_is_copied_as_a_step(self):
        """Bug: the copy knew the held key by its value alone, so the held
        value pasted back over the seam with another in slope read as the
        hold's -- ledger format 2 records the in half the hold froze, and
        the release already asks it.  Fixed: 2026-10-12"""
        self.ctrl._sync_combobox()
        self.ctrl.sequencer.reconcile_system_edits()  # holds A@40, before S1
        crv = cmds.keyframe(self.a, at="translateX", q=True, name=True)[0]
        claim = self.ctrl.sequencer.ledger.claimed_step(crv, 40.0)
        self.assertIsNotNone(claim, "the fixture's seam is not held")
        self.assertIsNotNone(claim.in_half, "the hold recorded no in half")
        angle = -35.0 if claim.in_half[0] > 0 else 35.0
        cmds.keyTangent(crv, time=(40, 40), lock=False)
        cmds.keyTangent(crv, time=(40, 40), itt="fixed", ott="step")
        cmds.keyTangent(crv, time=(40, 40), inAngle=angle)

        self.ctrl._copy_selected_keys(self._targets([40.0]))
        cmds.currentTime(70)
        self.ctrl._paste_selected_keys(self._b_row([60.0]))

        self.assertEqual(self._value(self.b, 70), self._value(self.a, 40))
        self.assertEqual(self._ott(self.b, 70), "step")

    def test_an_animators_step_is_copied_as_a_step(self):
        cmds.keyTangent(self.a, at="translateX", time=(0, 0), ott="step")
        self.ctrl._sync_combobox()
        self.ctrl._copy_selected_keys(self._targets([0.0]))
        cmds.currentTime(80)
        self.ctrl._paste_selected_keys(self._b_row([60.0]))
        self.assertEqual(self._ott(self.b, 80), "step")

    def test_the_spacing_between_rows_survives_and_nothing_selected_pastes_back(
        self,
    ):
        """The earliest copied key lands on the playhead and the rest keep
        their distance from it, across rows -- with nothing selected, back on
        the rows they came from."""
        self.ctrl._sync_combobox()
        self.ctrl._copy_selected_keys(self._targets([40.0]) + self._b_row([100.0]))
        cmds.currentTime(10)
        self.ctrl._paste_selected_keys([])
        self.assertEqual(self._keys(self.a), [0.0, 10.0, 40.0])
        self.assertEqual(self._keys(self.b), [60.0, 70.0, 100.0])
        self.assertEqual(self._value(self.b, 70), [5.0])

    def test_a_broken_tangent_pastes_broken(self):
        crv = cmds.keyframe(self.a, at="translateX", q=True, name=True)[0]
        cmds.setKeyframe(self.a, at="translateX", t=20, v=2.0)
        cmds.keyTangent(crv, time=(20, 20), lock=False)
        cmds.keyTangent(crv, time=(20, 20), inAngle=30.0, outAngle=-15.0)
        self.ctrl._sync_combobox()
        self.ctrl._copy_selected_keys(self._targets([20.0]))
        cmds.currentTime(80)
        self.ctrl._paste_selected_keys(self._b_row([60.0]))
        b_crv = cmds.keyframe(self.b, at="translateX", q=True, name=True)[0]
        self.assertEqual(
            cmds.keyTangent(b_crv, q=True, time=(80, 80), lock=True), [False]
        )
        self.assertAlmostEqual(
            cmds.keyTangent(b_crv, q=True, time=(80, 80), inAngle=True)[0], 30.0, 3
        )
        self.assertAlmostEqual(
            cmds.keyTangent(b_crv, q=True, time=(80, 80), outAngle=True)[0], -15.0, 3
        )

    def test_a_paste_onto_rows_gone_since_the_copy_says_nothing_pasted(self):
        """Bug: the paste counted (and selected) every copied row whatever
        landed -- the clipboard outlives the scene, so a row whose object was
        deleted since keyed nothing yet read "Pasted 1 key onto 1 row".
        Fixed: 2026-10-10"""
        self.ctrl._sync_combobox()
        self.ctrl._copy_selected_keys(self._targets([40.0]))
        cmds.delete(self.a)
        cmds.currentTime(80)
        self.ctrl._paste_selected_keys([])  # back onto the copied rows
        self.assertIn("Nothing pasted", self.ctrl.ui.footer.setText.call_args[0][0])

    def test_nothing_copied_pastes_nothing(self):
        self.ctrl._sync_combobox()
        cmds.selectKey(clear=True)
        cmds.selectKey(self.a, attribute="translateX", time=(0, 40))
        cmds.copyKey(animation="keys")  # Maya's clipboard is not the panel's
        cmds.currentTime(80)
        self.ctrl._paste_selected_keys(self._b_row([60.0]))
        self.assertEqual(self._keys(self.b), [60.0, 100.0])

    def test_the_scoped_edit_reports_whether_it_ran(self):
        ran, _ = self.ctrl._key_selection_edit([], "noop", lambda o, s: None)
        self.assertFalse(ran, "no targets, nothing to run")

    def _ramp(self, attr, first=0, last=40, step=4):
        """A straight ramp on *attr*: every middle key is shape-neutral."""
        for f in range(first, last + 1, step):
            cmds.setKeyframe(self.a, at=attr, t=f, v=float(f))
        cmds.keyTangent(self.a, at=[attr], itt="linear", ott="linear")

    def _attr_keys(self, attr):
        return sorted(cmds.keyframe(self.a, q=True, at=attr) or [])

    def test_simplify_drops_the_keys_that_carry_no_shape(self):
        self._ramp("translateX")
        self.assertEqual(len(self._attr_keys("translateX")), 11)
        self.ctrl._sync_combobox()

        self.ctrl._simplify_selected_keys(self._targets(self._attr_keys("translateX")))

        self.assertEqual(self._attr_keys("translateX"), [0.0, 40.0])

    def test_simplify_leaves_the_attributes_beside_the_selection_alone(self):
        self._ramp("translateX")
        self._ramp("translateZ")
        self.ctrl._sync_combobox()

        self.ctrl._simplify_selected_keys(self._targets(self._attr_keys("translateX")))

        self.assertEqual(self._attr_keys("translateX"), [0.0, 40.0])
        self.assertEqual(len(self._attr_keys("translateZ")), 11, "sibling untouched")

    def test_thin_narrows_to_the_selected_attribute(self):
        """The sub-row IS the scope: the object's other channels keep theirs."""
        self._ramp("translateX")
        self._ramp("translateZ")
        self.ctrl._sync_combobox()

        self.ctrl._thin_selected_keys(self._targets(self._attr_keys("translateX")))

        self.assertEqual(self._attr_keys("translateX"), [0.0, 40.0])
        self.assertEqual(len(self._attr_keys("translateZ")), 11, "sibling untouched")

    def test_simplify_drops_a_redundant_HOLD_key(self):
        """The pass that matters on real footage: a stepped hold's interiors.

        Reported from a production assembly, where Simplify appeared to do
        nothing -- the reducer alone will not touch a stepped curve, and a
        hold is normally spelled with step out-tangents.
        """
        for f, v in ((0, 1.0), (10, 1.0), (20, 1.0), (30, 1.0), (40, 0.0)):
            cmds.setKeyframe(self.a, at="translateX", t=f, v=v)
        cmds.keyTangent(self.a, at=["translateX"], ott="step")
        self.assertEqual(self._attr_keys("translateX"), [0.0, 10.0, 20.0, 30.0, 40.0])
        self.ctrl._sync_combobox()

        self.ctrl._simplify_selected_keys(self._targets(self._attr_keys("translateX")))

        # The hold collapses to the pair that still states it: the step out of
        # frame 0 carries the value all the way to 40, where it drops.
        self.assertEqual(self._attr_keys("translateX"), [0.0, 40.0])

    def test_simplify_does_not_move_the_curve(self):
        """Keys go, values do not: the hold reads the same at every frame."""
        for f, v in ((0, 1.0), (10, 1.0), (20, 1.0), (30, 1.0), (40, 0.0)):
            cmds.setKeyframe(self.a, at="translateX", t=f, v=v)
        cmds.keyTangent(self.a, at=["translateX"], ott="step")
        frames = list(range(0, 41, 2))
        before = [
            cmds.keyframe(self.a, at="translateX", q=True, eval=True, time=(f, f))[0]
            for f in frames
        ]
        self.ctrl._sync_combobox()

        self.ctrl._simplify_selected_keys(self._targets(self._attr_keys("translateX")))

        after = [
            cmds.keyframe(self.a, at="translateX", q=True, eval=True, time=(f, f))[0]
            for f in frames
        ]
        for f, b, a in zip(frames, before, after):
            self.assertAlmostEqual(b, a, places=6, msg=f"frame {f} moved")


class TestAttributeSelectionMirrorsTheChannelBox(_ControllerCase):
    """A sub-row IS a channel: selecting one highlights it in the Channel Box.

    Selecting an OBJECT row means the whole object, so it clears that
    highlight rather than listing the object's channels -- otherwise a scope
    the user set on one click keeps narrowing the edits they aim at the
    whole track afterwards.
    """

    def setUp(self):
        super().setUp()
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        self.mirrored = []
        self.ctrl._mirror_channels = lambda objects, attrs=(): self.mirrored.append(
            list(attrs)
        )

    def _clip(self, **data):
        tid = self.widget.add_track("probe")
        return self.widget.add_clip(tid, 0, 40, obj=str(self.a), **data)

    def test_a_sub_row_click_highlights_that_attribute(self):
        cid = self._clip(attr_name="translateX")
        self.ctrl.on_selection_changed([cid])
        self.assertEqual(self.mirrored, [["translateX"]])

    def test_an_object_row_click_clears_the_highlight(self):
        cid = self._clip(attributes=["translateX", "translateY"])
        self.ctrl.on_selection_changed([cid])
        self.assertEqual(self.mirrored, [[]], "the whole object, not its channels")

    def test_a_mixed_selection_is_object_scoped(self):
        sub = self._clip(attr_name="translateX")
        whole = self._clip(attributes=["translateX"])
        self.ctrl.on_selection_changed([sub, whole])
        self.assertEqual(self.mirrored, [[]])

    def test_a_header_label_click_clears_the_highlight(self):
        self.ctrl.on_track_selected([str(self.a)])
        self.assertEqual(self.mirrored, [[]])

    def test_a_key_selection_carries_its_attributes(self):
        cid = self._clip(attr_name="translateX")
        self.ctrl._mirror_key_selection([{"clip_id": cid, "times": [0.0, 40.0]}])
        self.assertEqual(self.mirrored, [["translateX"]])

    def test_an_emptied_key_selection_leaves_the_scope_alone(self):
        """It says nothing about scope; the clip selection outlives it."""
        self.ctrl._mirror_key_selection([])
        self.assertEqual(self.mirrored, [], "no call at all")

    def test_a_sub_row_label_click_selects_that_channel(self):
        """The header twin of clicking the sub-row's clip."""
        self.ctrl.on_sub_track_selected(
            [(str(self.a), "translateX"), (str(self.a), "translateZ")]
        )
        self.assertEqual(self.mirrored, [["translateX", "translateZ"]])
        self.assertIn(
            str(self.a), [n.split("|")[-1] for n in cmds.ls(sl=True, long=True) or []]
        )

    def test_a_sub_row_label_click_also_survives_a_list_payload(self):
        """Qt hands a Signal(list) back with its tuples turned into lists."""
        self.ctrl.on_sub_track_selected([[str(self.a), "translateY"]])
        self.assertEqual(self.mirrored, [["translateY"]])

    def test_the_header_wires_the_sub_row_signal(self):
        """The panel's own wiring connects the header's sub-row signal: read off
        the live connection, then acted on -- a label click the widget emits
        reaches the controller the slots built. Without its wiring row the
        click does nothing at all."""
        from types import SimpleNamespace

        from tentacle.slots.tools.shot_sequencer import ShotSequencerSlots

        switchboard = _Switchboard(tk=mtk)
        switchboard.loaded_ui = SimpleNamespace(shot_sequencer=self.slots.ui)
        panel = ShotSequencerSlots(switchboard)
        self.addCleanup(panel.controller.remove_callbacks)
        seen = []
        panel.controller._mirror_channels = lambda objects, attrs=(): seen.append(
            list(attrs)
        )
        self.assertIn(
            ("sub_track_selected", panel.controller.on_sub_track_selected),
            getattr(self.widget, "_slots_connections", []),
        )
        self.widget.sub_track_selected.emit([[str(self.a), "translateZ"]])
        _process_events()
        self.assertEqual(seen, [["translateZ"]])

    def test_a_clip_with_no_object_touches_nothing(self):
        tid = self.widget.add_track("probe")
        cid = self.widget.add_clip(tid, 0, 40, label="not an object")
        self.ctrl.on_selection_changed([cid])
        self.assertEqual(self.mirrored, [])


class _GraphEditorCase(_ControllerCase):
    """A controller over a live widget, with every Graph Editor closed first."""

    def setUp(self):
        # Decided before the fixture exists: a skip raised in setUp skips
        # tearDown, which would leave the widget and its callbacks alive.
        self._close_graph_editors()
        if self._shown():
            self.skipTest("this layout docks a Graph Editor in a view pane")
        super().setUp()
        self.addCleanup(self._close_graph_editors)

    @staticmethod
    def _close_graph_editors():
        for panel in cmds.getPanel(scriptType="graphEditor") or []:
            window = panel + "Window"  # tearOffRestorePanel's naming
            if cmds.workspaceControl(window, exists=True):
                cmds.workspaceControl(window, edit=True, close=True)
        _process_events()

    @staticmethod
    def _shown() -> list:
        """The Graph Editor panels open in a view pane or a window.

        A collapsed dock counts -- it is open, only folded.  The window's own
        flag is read because ``getPanel -visiblePanels`` lists neither that
        nor a freshly opened window's panel before Maya's next idle.
        """
        visible = set(cmds.getPanel(visiblePanels=True) or [])

        def windowed(panel):
            window = panel + "Window"
            if not cmds.workspaceControl(window, exists=True):
                return False
            return cmds.workspaceControl(window, query=True, visible=True)

        return [
            p
            for p in cmds.getPanel(scriptType="graphEditor") or []
            if p in visible or windowed(p)
        ]

    def _sub_row_clip(self):
        tid = self.widget.add_track("probe")
        return self.widget.add_clip(tid, 0, 40, obj=str(self.a), attr_name="translateX")


class TestSelectionLeavesTheGraphEditorAlone(_GraphEditorCase):
    """A panel click mirrors the selection into Maya; it opens no editor.

    An open Graph Editor follows the scene selection by itself, so the panel
    never needs to open one.  It used to (``GraphEditor``, which is
    ``tearOffRestorePanel``) on every clip or header click: a closed Graph
    Editor popped open, and a collapsed one expanded.
    """

    def test_a_clip_click_leaves_a_closed_graph_editor_closed(self):
        self.ctrl.on_selection_changed([self._sub_row_clip()])
        _process_events()
        self.assertEqual(self._shown(), [])
        selected = [n.split("|")[-1] for n in cmds.ls(sl=True, long=True) or []]
        self.assertIn(str(self.a), selected, "the selection itself still lands")

    def test_a_header_click_leaves_a_closed_graph_editor_closed(self):
        self.ctrl.on_track_selected([str(self.a)])
        self.ctrl.on_sub_track_selected([(str(self.a), "translateX")])
        _process_events()
        self.assertEqual(self._shown(), [])

    def test_an_open_graph_editor_still_lists_the_clicked_object(self):
        """Why nothing needs opening: an open one follows the selection."""
        import maya.mel as mel

        mel.eval("GraphEditor")  # the user's own open
        _process_events()
        panels = self._shown()
        self.assertTrue(panels, "the Graph Editor did not open")
        outline = panels[0] + "OutlineEd"
        if not mel.eval(f'isAutoLoad "{outline}"'):
            self.skipTest("the Graph Editor's Auto Load is off")
        listed = cmds.outlinerEditor(outline, query=True, mainListConnection=True)
        self.ctrl.on_track_selected([str(self.b)])
        _process_events()
        objects = cmds.selectionConnection(listed, query=True, object=True) or []
        self.assertEqual([o.split("|")[-1] for o in objects], [str(self.b)])


class TestAKeySelectionReachesTheGraphEditor(_GraphEditorCase):
    """Keys selected in the panel are selected in the Graph Editor, and a
    closed or collapsed Graph Editor stays that way (2026-10-07: "can we
    select keys in the graph editor when they are selected in the sequencer
    without showing the graph editor if its tab is currently minimized?").

    The Graph Editor lists the SELECTED objects' curves, so a key whose object
    is not selected is selected where nobody can see it -- and selecting an
    object CLEARS Maya's key selection (measured), so the objects go on the
    selection first and the keys after.
    """

    def _selected_keys(self) -> dict:
        return {
            crv: cmds.keyframe(crv, query=True, selected=True, timeChange=True)
            for crv in cmds.keyframe(query=True, selected=True, name=True) or []
        }

    def _a_tx(self) -> str:
        return cmds.listConnections(f"{self.a}.translateX", type="animCurve")[0]

    def _picked(self) -> set:
        return {n.split("|")[-1] for n in cmds.ls(sl=True, long=True) or []}

    def _select_keys(self, cid, times):
        """The panel's key mirror, its deferred Channel Box half run inline:
        Maya's idle queue never runs while the harness drives it through the
        command port, so ``flushIdleQueue`` would wait forever."""
        from unittest import mock
        from mayatk.anim_utils.shots.shot_sequencer import sequencer_host

        with mock.patch.object(
            sequencer_host.cmds, "evalDeferred", new=lambda fn, **_kw: fn()
        ):
            self.ctrl.on_key_selection_changed([{"clip_id": cid, "times": times}])
        _process_events()

    def test_the_keys_object_is_selected_and_its_keys_stay_selected(self):
        cmds.select(str(self.b), replace=True)  # not the key's object
        self._select_keys(self._sub_row_clip(), [40.0])
        self.assertEqual(self._selected_keys(), {self._a_tx(): [40.0]})
        self.assertIn(str(self.a), self._picked(), "the Graph Editor lists it")

    def test_the_footer_names_the_selected_keys(self):
        """The footer reads the selection: how many keys, their frames, on
        which channel of which object (2026-10-10: "footer should show key
        specific info when keys are selected like frame range, etc")."""
        from unittest import mock

        with mock.patch.object(self.ctrl, "_set_footer") as footer:
            self._select_keys(self._sub_row_clip(), [0.0, 40.0])
        text = footer.call_args[0][0]
        self.assertTrue(text.startswith("2 keys · frames 0–40 (40f"), text)
        self.assertIn("translateX on", text)

    def test_nothing_selected_in_maya_is_no_obstacle(self):
        """With no object and no key selected, the clear before the mirror
        raised ("Error retrieving default arguments") and no key was selected
        at all -- nor was an emptied panel selection mirrored."""
        cmds.select(clear=True)
        self.ctrl.on_key_selection_changed([])  # an emptied selection
        cmds.select(clear=True)
        self._select_keys(self._sub_row_clip(), [40.0])
        self.assertEqual(self._selected_keys(), {self._a_tx(): [40.0]})

    def test_a_wider_object_selection_is_kept(self):
        cmds.select([str(self.a), str(self.b)], replace=True)
        self._select_keys(self._sub_row_clip(), [40.0])
        self.assertEqual(self._picked(), {str(self.a), str(self.b)})
        self.assertEqual(self._selected_keys(), {self._a_tx(): [40.0]})

    def test_a_closed_graph_editor_stays_closed(self):
        self._select_keys(self._sub_row_clip(), [0.0])
        self.assertEqual(self._shown(), [])
        self.assertEqual(self._selected_keys(), {self._a_tx(): [0.0]})

    def test_a_collapsed_graph_editor_stays_collapsed(self):
        import maya.mel as mel

        mel.eval("GraphEditor")  # the user's own open
        _process_events()
        panels = self._shown()
        if not panels:
            self.skipTest("the Graph Editor did not open")
        window = panels[0] + "Window"
        if not cmds.workspaceControl(window, exists=True):
            self.skipTest("this layout holds the Graph Editor in a view pane")
        # The harness's Maya reads the user's prefs: put back the floating
        # state found, so no layout it might save carries this dock.
        if cmds.workspaceControl(window, query=True, floating=True):
            self.addCleanup(cmds.workspaceControl, window, edit=True, floating=True)
        cmds.workspaceControl(window, edit=True, dockToMainWindow=("right", False))
        cmds.workspaceControl(window, edit=True, collapse=True)
        _process_events()
        if not cmds.workspaceControl(window, query=True, collapse=True):
            self.skipTest("this Maya does not collapse the docked Graph Editor")
        self._select_keys(self._sub_row_clip(), [40.0])
        self.assertTrue(cmds.workspaceControl(window, query=True, collapse=True))
        self.assertEqual(self._selected_keys(), {self._a_tx(): [40.0]})
        listed = cmds.outlinerEditor(
            panels[0] + "OutlineEd", query=True, mainListConnection=True
        )
        objects = cmds.selectionConnection(listed, query=True, object=True) or []
        self.assertIn(str(self.a), [o.split("|")[-1] for o in objects])


class TestBoundCapDrags(_ControllerCase):
    """The caps before the first shot and after the last are those shots'
    own bounds: a plain drag moves the bound and nothing else."""

    def setUp(self):
        super().setUp()
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()

    def test_the_last_shots_tail_cap_moves_the_bound_only(self):
        self.ctrl.on_gap_left_resized(120.0, 130.0)
        s1 = self._shot("S1")
        self.assertEqual((s1.start, s1.end), (60.0, 130.0))
        self.assertEqual(self._keys(self.b), [60.0, 100.0], "keys stay")

    def test_the_first_shots_head_cap_moves_the_bound_only(self):
        self.ctrl.on_gap_resized(0.0, -10.0)
        s0 = self._shot("S0")
        self.assertEqual((s0.start, s0.end), (-10.0, 50.0))
        self.assertEqual(self._keys(self.a), [0.0, 40.0])

    def test_a_real_gap_edge_still_slides(self):
        self.ctrl.on_gap_left_resized(50.0, 55.0)
        s0 = self._shot("S0")
        self.assertEqual((s0.start, s0.end), (5.0, 55.0))
        self.assertEqual(self._keys(self.a), [5.0, 45.0])

    def test_both_caps_are_placed(self):
        caps = [
            (o._head, o._tail, o._start)
            for o in self.widget.layer("shot_lane")._gap_overlays
            if o._head or o._tail
        ]
        self.assertIn((True, False, 0.0), caps)
        self.assertIn((False, True, 120.0), caps)

    def test_the_lane_shows_every_shot_on_the_panels_layer(self):
        """The decoration lands on the shot layer (uitk's widget names no
        shot): one band per shot, the active one selected."""
        layer = self.widget.layer("shot_lane")
        self.assertEqual([b["name"] for b in layer._shot_blocks], ["S0", "S1"])
        self.assertEqual(
            layer.selected_shot()["id"], self.ctrl.active_shot_id, "the active one"
        )

    def test_lock_all_locks_the_layers_gaps_and_spares_the_caps(self):
        self.ctrl.on_gap_lock_all()
        gaps = self.widget.layer("shot_lane")._gap_overlays
        self.assertTrue(all(g._locked for g in gaps if not (g._head or g._tail)))
        self.assertFalse(any(g._locked for g in gaps if g._head or g._tail))
        self.ctrl.on_gap_unlock_all()
        self.assertFalse(any(g._locked for g in gaps))


class TestShotComboboxCells(_ControllerCase):
    """The shot dropdown's rows carry cells that edit the shot in place."""

    def setUp(self):
        super().setUp()
        self.cmb = self.slots.ui.cmb_shot
        self.ctrl._configure_shot_combobox(self.cmb)
        self.ctrl._sync_combobox()

    def test_rows_carry_cells(self):
        self.assertEqual(
            self.cmb.item_cells(1),
            {"name": "S1", "start": 60.0, "end": 120.0, "description": ""},
        )
        self.assertEqual(self.cmb.itemText(1), "S1  [60-120]")
        self.assertTrue(self.cmb.rename_on_double_click)

    def test_editing_the_name_renames(self):
        self.cmb.on_cells_edited.emit(0, {"name": "Opening"})
        self.assertEqual(self._shot("Opening").start, 0.0)
        self.assertEqual(self.cmb.itemText(0), "Opening  [0-50]")

    def test_editing_the_end_moves_that_bound_only(self):
        self.cmb.on_cells_edited.emit(0, {"end": 45})
        self.assertEqual(self._shot("S0").end, 45.0)
        self.assertEqual(self._keys(self.a), [0.0, 40.0], "keys stay")
        self.assertEqual(self._shot("S1").start, 55.0, "downstream rippled -5")

    def test_editing_the_start_moves_the_shot(self):
        self.cmb.on_cells_edited.emit(1, {"start": 70})
        s1 = self._shot("S1")
        self.assertEqual((s1.start, s1.end), (70.0, 130.0))
        self.assertEqual(self._keys(self.b), [70.0, 110.0], "keys ride")

    def test_a_blank_name_is_ignored(self):
        self.cmb.on_cells_edited.emit(0, {"name": "   "})
        self.assertIsNotNone(self._shot("S0"))


class TestGraphSync(_ControllerCase):
    """The graph editor over a real controller and a real scene.

    Every edit is checked in MAYA: the keys, the tangents, the curve
    attributes, the shot bounds -- and Ctrl+Z puts keys and bounds back.
    """

    def setUp(self):
        super().setUp()
        GraphSync = mtk.SequencerHost.graph_sync_cls()

        cmds.currentTime(0)
        self.ctrl._sync_combobox()
        self.ctrl._sync_to_widget()
        self.sync = GraphSync(self.ctrl, self.widget)
        self.widget.set_editor("graph")
        _process_events()
        self.g = self.widget.editor("graph")
        self.crv = cmds.listConnections(f"{self.a}.translateX", type="animCurve")[0]

    def tearDown(self):
        self.sync.detach()
        super().tearDown()

    def _times(self):
        return cmds.keyframe(self.crv, q=True, timeChange=True)

    def _values(self):
        return cmds.keyframe(self.crv, q=True, valueChange=True)

    def test_the_outline_is_the_shots_objects_and_their_curves(self):
        entry = next(e for e in self.g._outline if e["label"] == "ctlA")
        self.assertEqual(
            [(c["curve_id"], c["label"]) for c in entry["children"]],
            [(self.crv, "translateX")],
        )
        self.assertIn(self.crv, self.g.displayed_curve_ids())
        self.assertEqual(self.g.curve(self.crv).times(), [0.0, 40.0])

    def test_a_claimed_sample_draws_no_key(self):
        cmds.setKeyframe(self.a, attribute="translateX", time=50, insert=True)
        self.ctrl.sequencer.ledger.record_key(self.crv, 50.0, 0, "end")
        self.sync.sync()
        keys = {k.time: k.hidden for k in self.g.curve(self.crv).keys}
        self.assertEqual(keys, {0.0: False, 40.0: False, 50.0: True})

    def test_a_move_lands_time_and_value_in_maya(self):
        self.g.keys_edited.emit([(self.crv, [(40.0, -5.0, 2.5)])])
        self.assertEqual(self._times(), [0.0, 35.0])
        self.assertAlmostEqual(self._values()[1], 7.5, places=6)
        self.assertEqual(self.g.curve(self.crv).times(), [0.0, 35.0], "graph re-read")

    def test_a_value_only_move_keeps_the_times(self):
        self.g.keys_edited.emit([(self.crv, [(0.0, 0.0, -1.0), (40.0, 0.0, -1.0)])])
        self.assertEqual(self._times(), [0.0, 40.0])
        self.assertEqual(self._values(), [-1.0, 4.0])

    def test_a_move_past_the_shot_end_grows_the_shot_and_undo_restores_both(self):
        s0 = self._shot("S0")
        self.g.keys_edited.emit([(self.crv, [(40.0, 15.0, 0.0)])])
        self.assertEqual(self._times(), [0.0, 55.0])
        self.assertGreaterEqual(self._shot("S0").end, 55.0)
        self.ctrl.on_undo()
        self.assertEqual(self._times(), [0.0, 40.0])
        self.assertEqual((self._shot("S0").start, self._shot("S0").end), (0.0, 50.0))
        self.assertEqual(s0.shot_id, self._shot("S0").shot_id)

    def test_a_move_past_the_shot_end_grows_the_shot_after_a_shift_gesture(self):
        """Bug: the graph read the press modifiers the TRACKS record (the
        graph records none), so after a Shift gesture there -- Shift: free
        across bounds -- a key moved past its shot's end left it outside.
        Fixed: 2026-10-12"""
        self.widget.shift_held_at_press = True  # a tracks gesture's leftover
        self.g.keys_edited.emit([(self.crv, [(40.0, 15.0, 0.0)])])
        self.assertEqual(self._times(), [0.0, 55.0])
        self.assertGreaterEqual(self._shot("S0").end, 55.0)

    def test_a_seam_key_moved_into_the_later_shot_grows_nothing(self):
        """Bug: a key on a seam two flush shots share was edited as the
        EARLIER shot's, so moving it into the later one grew the earlier
        shot over it and rippled the later one away.
        Fixed: 2026-10-12"""
        self.store.update_shot(self._shot("S1").shot_id, start=50.0)
        cmds.setKeyframe(self.b, attribute="translateX", time=50, value=-1.0)
        crv_b = cmds.listConnections(f"{self.b}.translateX", type="animCurve")[0]
        self.sync.sync()
        self.g.keys_edited.emit([(crv_b, [(50.0, 5.0, 0.0)])])
        self.assertIn(55.0, cmds.keyframe(crv_b, q=True, timeChange=True))
        self.assertEqual((self._shot("S0").end, self._shot("S1").start), (50.0, 50.0))

    def test_a_graph_edit_drops_every_shots_cached_segments(self):
        """Bug: a graph edit dropped the cached segments only when a key
        moved inside a shot, so a neighbour keyed or cleared from the graph
        drew its old clips on the way back to the tracks (Adjacent / All).
        Fixed: 2026-10-12"""
        s1 = self._shot("S1").shot_id
        self.ctrl._segment_cache[s1] = ["stale"]
        crv_b = cmds.listConnections(f"{self.b}.translateX", type="animCurve")[0]
        self.g.keys_inserted.emit([(crv_b, 80.0)])
        self.assertNotEqual(self.ctrl._segment_cache.get(s1), ["stale"])

    def test_a_destroyed_widget_takes_the_syncs_maya_subscriptions(self):
        """Bug: a closed panel's GraphSync kept its scriptJobs and its
        anim-curve callback (only a slots re-init over the same widget
        detached it), and they held the dead panel.
        Fixed: 2026-10-12"""
        from qtpy import QtCore
        from mayatk.core_utils.script_job_manager import ScriptJobManager

        GraphSync = mtk.SequencerHost.graph_sync_cls()

        mgr = ScriptJobManager.instance()

        def owned(owner):
            subs = list(mgr._subs.values()) + list(mgr._om_subs.values())
            return [s for s in subs if s.owner is owner]

        other = SequencerWidget()
        sync = GraphSync(self.ctrl, other)
        self.assertTrue(owned(sync), "precondition: subscribed")
        other.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        self.assertEqual(owned(sync), [])

    def test_a_real_drag_on_the_canvas_moves_the_key(self):
        from qtpy import QtCore, QtGui

        self.g.frame_all()
        _process_events()
        view = self.widget._timeline
        vp = view.viewport()
        start = view.mapFromScene(self.g._point(self.crv, 40.0, 5.0))
        end = view.mapFromScene(self.g._point(self.crv, 30.0, 3.0))

        def send(kind, pos, buttons):
            ev = QtGui.QMouseEvent(
                kind,
                QtCore.QPointF(pos),
                QtCore.QPointF(vp.mapToGlobal(pos)),
                QtCore.Qt.LeftButton,
                buttons,
                QtCore.Qt.NoModifier,
            )
            QtWidgets.QApplication.sendEvent(vp, ev)

        send(QtCore.QEvent.MouseButtonPress, start, QtCore.Qt.LeftButton)
        for i in range(1, 7):
            pt = start + (end - start) * (i / 6)
            send(QtCore.QEvent.MouseMove, pt, QtCore.Qt.LeftButton)
        send(QtCore.QEvent.MouseButtonRelease, end, QtCore.Qt.NoButton)
        _process_events()
        self.assertEqual(self._times(), [0.0, 30.0])
        self.assertAlmostEqual(self._values()[1], 3.0, delta=0.15)

    def test_tangent_handles_write_angles(self):
        self.g.tangents_edited.emit([(self.crv, [(0.0, "out", 1.0, 1.0, False)])])
        out = cmds.keyTangent(self.crv, q=True, time=(0, 0), outAngle=True)[0]
        self.assertAlmostEqual(out, 45.0, places=3)
        self.g.tangents_edited.emit([(self.crv, [(40.0, "in", -1.0, 0.5, True)])])
        self.assertFalse(cmds.keyTangent(self.crv, q=True, time=(40, 40), lock=True)[0])

    def _drag_handle(self, side, scale):
        """A real drag of key 0's *side* handle to *scale* times its length."""
        from qtpy import QtCore, QtGui

        self.g.select_keys([(self.crv, 0.0)])
        self.g.frame_all()
        _process_events()
        curve = self.g.curve(self.crv)
        key = curve.keys[0]
        view = self.widget._timeline
        vp = view.viewport()
        p_key = self.g._point(self.crv, key.time, key.value)
        p_h = self.g._handle_point(self.crv, curve, key, side)
        start = view.mapFromScene(p_h)
        end = view.mapFromScene(p_key + (p_h - p_key) * scale)

        def send(kind, pos, buttons):
            ev = QtGui.QMouseEvent(
                kind,
                QtCore.QPointF(pos),
                QtCore.QPointF(vp.mapToGlobal(pos)),
                QtCore.Qt.LeftButton,
                buttons,
                QtCore.Qt.NoModifier,
            )
            QtWidgets.QApplication.sendEvent(vp, ev)

        send(QtCore.QEvent.MouseButtonPress, start, QtCore.Qt.LeftButton)
        for i in range(1, 7):
            send(
                QtCore.QEvent.MouseMove,
                start + (end - start) * (i / 6),
                QtCore.Qt.LeftButton,
            )
        send(QtCore.QEvent.MouseButtonRelease, end, QtCore.Qt.NoButton)
        _process_events()

    def test_a_weighted_handle_dragged_longer_or_shorter_changes_the_weight(self):
        self.g.select_keys([(self.crv, 0.0)])
        self.g.weighted_requested.emit(True, [self.crv])
        _process_events()
        self.assertTrue(self.g.curve(self.crv).weighted)
        w0 = cmds.keyTangent(self.crv, q=True, time=(0, 0), outWeight=True)[0]
        self._drag_handle("out", 1.6)
        w1 = cmds.keyTangent(self.crv, q=True, time=(0, 0), outWeight=True)[0]
        self.assertGreater(w1, w0 * 1.2, "dragged farther")
        self._drag_handle("out", 0.5)
        w2 = cmds.keyTangent(self.crv, q=True, time=(0, 0), outWeight=True)[0]
        self.assertLess(w2, w1 * 0.8, "dragged nearer")

    def test_delete_and_insert(self):
        self.g.keys_inserted.emit([(self.crv, 20.0)])
        self.assertEqual(self._times(), [0.0, 20.0, 40.0])
        self.g.keys_deleted.emit([(self.crv, [20.0])])
        self.assertEqual(self._times(), [0.0, 40.0])

    def test_types_weighting_and_infinity(self):
        self.g.tangent_type_requested.emit("linear", [(self.crv, [0.0, 40.0])])
        self.assertEqual(
            cmds.keyTangent(self.crv, q=True, outTangentType=True), ["linear", "linear"]
        )
        self.g.tangent_type_requested.emit("step", [(self.crv, [0.0])])
        self.assertEqual(
            cmds.keyTangent(self.crv, q=True, time=(0, 0), outTangentType=True),
            ["step"],
        )
        self.g.weighted_requested.emit(True, [self.crv])
        self.assertTrue(cmds.getAttr(f"{self.crv}.weightedTangents"))
        self.g.infinity_requested.emit("post", "cycle_offset", [self.crv])
        self.assertEqual(cmds.getAttr(f"{self.crv}.postInfinity"), 4)
        self.assertEqual(cmds.getAttr(f"{self.crv}.preInfinity"), 0)
        self.assertEqual(self.g.curve(self.crv).post_infinity, "cycle_offset")

    def test_the_graph_selection_reaches_maya(self):
        self.g.select_keys([(self.crv, 40.0)])
        self.assertEqual(cmds.keyframe(self.crv, q=True, selected=True), [40.0])
        self.g.select_keys([(self.crv, 0.0), (self.crv, 40.0)])
        self.assertEqual(cmds.keyframe(self.crv, q=True, selected=True), [0.0, 40.0])

    def test_copy_and_paste_act_on_the_graph_selection(self):
        self.g.select_keys([(self.crv, 40.0)])
        self.ctrl._copy_keys_shortcut()
        cmds.currentTime(20)
        self.g.select_keys([])
        self.ctrl._paste_keys_shortcut()  # back onto the row it came from
        self.assertEqual(self._times(), [0.0, 20.0, 40.0])
        self.assertAlmostEqual(self._values()[1], 5.0, places=6)
        self.assertEqual(self.g.curve(self.crv).times(), [0.0, 20.0, 40.0])

    def test_euler_filter_from_the_graph_menu(self):
        node = cmds.polyCube(name="spinner")[0]
        for t, rx in ((0, 170.0), (10, -170.0)):
            cmds.setKeyframe(node, attribute="rotateX", time=t, value=rx)
        self._shot("S0").objects.append(node)
        self.sync.sync()
        rot = cmds.listConnections(f"{node}.rotateX", type="animCurve")[0]
        self.g.select_keys([(rot, 0.0), (rot, 10.0)])
        menu = self.g.build_context_menu()
        edit = next(a.menu() for a in menu.actions() if a.text() == "Edit")
        next(a for a in edit.actions() if a.text() == "Euler Filter").trigger()
        self.assertEqual(cmds.keyframe(rot, q=True, valueChange=True), [170.0, 190.0])
        self.assertEqual(
            [k.value for k in self.g.curve(rot).keys], [170.0, 190.0], "re-read"
        )
        self.ctrl.on_undo()
        self.assertEqual(cmds.keyframe(rot, q=True, valueChange=True), [170.0, -170.0])

    def test_the_graph_menu_carries_the_key_edits(self):
        self.g.select_keys([(self.crv, 0.0), (self.crv, 40.0)])
        menu = self.g.build_context_menu()
        titles = [a.text() for a in menu.actions()]
        self.assertIn("Store Keys (2)", titles)
        edit = next(a.menu() for a in menu.actions() if a.text() == "Edit")
        self.assertEqual(
            [a.text() for a in edit.actions()],
            [label for label, _m in self.ctrl._KEY_EDITS],
        )

    def test_live_update_shows_the_drag_in_the_scene_and_a_cancel_restores(self):
        cmds.currentTime(0)
        preview = self.g.curve(self.crv).copy()
        preview.keys[0].value = 3.0
        self.g.curves_previewed.emit([(self.crv, preview)])
        self.assertAlmostEqual(cmds.getAttr(f"{self.a}.translateX"), 3.0, places=4)
        self.assertEqual(self._values(), [0.0, 5.0], "no key changed")
        self.g.preview_cancelled.emit()
        self.assertAlmostEqual(cmds.getAttr(f"{self.a}.translateX"), 0.0, places=4)

    def test_the_scopes_window_is_the_graphs_focus_range(self):
        self.sync.sync()
        self.assertEqual(self.g.focus_range, (0.0, 50.0))
        self.ctrl._shot_display_mode = "all"
        self.sync.sync()
        self.assertEqual(self.g.focus_range, (0.0, 120.0))

    def test_undo_puts_the_graph_back_too(self):
        self.g.keys_edited.emit([(self.crv, [(40.0, -5.0, 2.5)])])
        self.assertEqual(self.g.curve(self.crv).times(), [0.0, 35.0])
        self.ctrl.on_undo()
        _process_events()
        self.assertEqual(self._times(), [0.0, 40.0])
        self.assertEqual(self.g.curve(self.crv).times(), [0.0, 40.0], "graph re-read")

    def test_an_edit_made_in_maya_reaches_the_graph(self):
        cmds.setKeyframe(self.a, attribute="translateX", time=20, value=9.0)
        self.ctrl._sync_to_widget()  # what the keyframe debounce runs
        self.assertEqual(self.g.curve(self.crv).times(), [0.0, 20.0, 40.0])

    def _show_both_shots(self):
        self.ctrl._shot_display_mode = "all"
        self.sync.sync()
        ids = [e["label"] for e in self.g._outline]
        self.assertEqual(ids, ["ctlA", "ctlB"])
        return next(e["id"] for e in self.g._outline if e["label"] == "ctlB")

    def test_a_curve_edited_while_hidden_is_read_when_shown(self):
        b_id = self._show_both_shots()
        self.assertIn(self.crv, self.g._curves, "shown, so cached")
        self.assertTrue(self.g.focus_objects([b_id]))
        cmds.keyframe(self.crv, edit=True, relative=True, valueChange=3.0)
        self.sync.sync()
        a_id = next(e["id"] for e in self.g._outline if e["label"] == "ctlA")
        self.g.focus_objects([a_id])
        self.assertEqual([k.value for k in self.g.curve(self.crv).keys], [3.0, 8.0])

    def test_the_graph_follows_maya_selection(self):
        self._show_both_shots()
        cmds.select(self.b)
        self.sync._on_maya_selection()
        _process_events()
        b_curve = cmds.listConnections(f"{self.b}.translateX", type="animCurve")[0]
        self.assertEqual(self.g.displayed_curve_ids(), [b_curve])
        cmds.select(clear=True)
        self.sync._follow_selection()
        self.assertEqual(self.g.displayed_curve_ids(), [b_curve], "kept on clear")
        self.g.auto_load = False  # pinned
        cmds.select(self.a)
        self.sync._follow_selection()
        self.assertEqual(self.g.displayed_curve_ids(), [b_curve], "pinned")

    def test_a_member_keyed_only_on_one_side_of_the_shots_shown_stays_out(self):
        far = _make_cube("ctlFar", {300: 0, 340: 5})
        through = _make_cube("ctlThrough", {-100: 0, 200: 5})
        self._shot("S0").objects.extend([str(far), str(through)])
        self.sync.sync()
        self.assertEqual(
            [e["label"] for e in self.g._outline],
            ["ctlA", "ctlThrough"],
            "keyed across the shot, no key inside: it animates there",
        )

    def test_a_queued_follow_after_detach_does_nothing(self):
        self.sync._on_maya_selection()
        self.sync.detach()
        cmds.select(self.a)
        _process_events()  # the queued follow fires on a detached sync
        self.assertFalse(self.sync._follow_queued)


if __name__ == "__main__":
    unittest.main()
