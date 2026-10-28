#!/usr/bin/python
# coding=utf-8
"""The Shot Sequencer's shot layer on uitk's ``SequencerWidget``.

:class:`~tentacle.slots.tools._shot_sequencer.shot_layer.ShotLayer` is the
panel's shots on the generic timeline -- the shot lane under the ruler, the
gaps between shots and the caps on the first and last shot's outer bounds,
the shot gestures, Ctrl+Shift+Click -- plugged in through the widget's layer
seam.  These are the tests uitk kept for them while they lived in the widget
(``test_sequencer.py``), with their assertions kept: what moved is where the
calls go (the layer, not the widget), never what they check.  The seam itself
is uitk's (``TestLayerSeam``); the controller's answers to the layer's signals
are ``test_shot_sequencer_controller.py`` (``--in-maya``).

Plain Qt, offscreen, no DCC::

    python tentacle/test/run_tests.py test_shot_sequencer_layer
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy import QtCore, QtGui, QtTest, QtWidgets

import uitk
from uitk import SequencerWidget
from uitk.testing import TestSandbox

import tentacle
from _host import qt_widgets_available
from tentacle.slots.tools._shot_sequencer.shot_layer import GapOverlay, ShotLayer

TestSandbox.activate()  # the widget's layout settings stay off the live stores
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

#: The ruler's height and the shot lane's under it (uitk's ``_RULER_HEIGHT``,
#: read off the widget with no layer added).
RULER = None
LANE = ShotLayer.lane_height
_SKIP = "needs Qt widgets"


def _ruler_height():
    global RULER
    if RULER is None:
        bare = SequencerWidget()
        RULER = int(bare._content_top)
        bare.deleteLater()
    return RULER


class _Sb:
    """The Switchboard as the layer reads it: uitk's public names."""

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(uitk, name)


@unittest.skipUnless(qt_widgets_available(), _SKIP)
class _LayerCase(unittest.TestCase):
    """A widget with the shot layer added, as the panel adds it."""

    #: ``(width, height)`` to size the widget to, or ``None``.
    SIZE = None
    SHOW = False

    def setUp(self):
        self.w = SequencerWidget()
        if self.SIZE:
            self.w.resize(*self.SIZE)
        if self.SHOW:
            self.w.show()
        self.layer = ShotLayer.of(self.w, _Sb())
        self.tl = self.w._timeline
        self.RULER = _ruler_height()

    def tearDown(self):
        self.w.close()
        self.w.deleteLater()

    def _gap(self, *args, **kw):
        self.layer.add_gap_overlay(*args, **kw)
        return self.layer._gap_overlays[-1]

    def _vx(self, time):
        return int(self.tl.time_to_x(time) - self.tl.horizontalScrollBar().value())

    def _lane_y(self):
        return self.RULER + LANE // 2

    def _view_drag(self, from_time, to_time, y, modifiers=None):
        """Press, move and release on the view, in viewport coordinates."""
        C, G = QtCore, QtGui
        modifiers = C.Qt.NoModifier if modifiers is None else modifiers
        for kind, x, btn, btns in (
            (C.QEvent.MouseButtonPress, self._vx(from_time), C.Qt.LeftButton, C.Qt.LeftButton),
            (C.QEvent.MouseMove, self._vx(to_time), C.Qt.NoButton, C.Qt.LeftButton),
            (C.QEvent.MouseButtonRelease, self._vx(to_time), C.Qt.LeftButton, C.Qt.NoButton),
        ):
            ev = G.QMouseEvent(kind, C.QPointF(x, y), btn, btns, modifiers)
            if kind == C.QEvent.MouseButtonPress:
                self.tl.mousePressEvent(ev)
            elif kind == C.QEvent.MouseMove:
                self.tl.mouseMoveEvent(ev)
            else:
                self.tl.mouseReleaseEvent(ev)

    @staticmethod
    def _scene_ev(kind, scene_pt, button=None, modifiers=None, screen_pt=None):
        ev = QtWidgets.QGraphicsSceneMouseEvent(kind)
        if button is not None:
            ev.setButton(button)
            ev.setButtons(button)
        ev.setScenePos(scene_pt)
        ev.setPos(scene_pt)
        # The grab arms on SCREEN travel (``_past_drag_threshold``), so a
        # simulated drag has to carry a screen position like a real one.
        if screen_pt is None:
            screen_pt = QtCore.QPoint(int(scene_pt.x()), int(scene_pt.y()))
        ev.setScreenPos(screen_pt)
        if modifiers is not None:
            ev.setModifiers(modifiers)
        return ev


# ---------------------------------------------------------------- the layer


class TestTheLayerOnTheWidget(_LayerCase):
    """The panel's layer is one per widget, added under its zone's name."""

    def test_of_adds_it_once(self):
        self.assertIs(self.w.layer(ShotLayer.name), self.layer)
        self.assertIs(ShotLayer.of(self.w, _Sb()), self.layer)
        self.assertEqual(ShotLayer.name, "shot_lane", "the zone the menus key on")

    def test_it_lives_as_long_as_the_widget(self):
        self.assertIs(self.layer.parent(), self.w)

    def test_the_gap_item_is_built_on_uitks_parts(self):
        item = self._gap(10, 20)
        self.assertIsInstance(item, GapOverlay)
        self.assertIsInstance(item, uitk.HeldGeometryMixin)
        self.assertIsInstance(item, uitk.DraggableItemMixin)
        self.assertIsInstance(item, QtWidgets.QGraphicsItem)


# ------------------------------------------------------------ gap overlays


class TestGapOverlays(_LayerCase):
    """Gap overlay creation, visibility, and lifecycle."""

    def test_add_gap_overlay(self):
        """add_gap_overlay creates a scene item and tracks it."""
        self.layer.add_gap_overlay(50, 60)
        self.assertEqual(len(self.layer._gap_overlays), 1)

    def test_add_multiple_gap_overlays(self):
        self.layer.add_gap_overlay(10, 20)
        self.layer.add_gap_overlay(30, 40)
        self.layer.add_gap_overlay(70, 80)
        self.assertEqual(len(self.layer._gap_overlays), 3)

    def test_clear_gap_overlays(self):
        self.layer.add_gap_overlay(10, 20)
        self.layer.add_gap_overlay(30, 40)
        self.layer.clear_gap_overlays()
        self.assertEqual(len(self.layer._gap_overlays), 0)

    def test_gap_overlay_visible_by_default(self):
        """Gaps are visible when _show_gap_overlays is True (default)."""
        self.assertTrue(self.layer._show_gap_overlays)
        self.layer.add_gap_overlay(10, 20)
        self.assertTrue(self.layer._gap_overlays[0].isVisible())

    def test_gap_overlay_hidden_when_disabled(self):
        """Gaps created while show_gap_overlays=False are hidden."""
        self.layer.show_gap_overlays = False
        self.layer.add_gap_overlay(10, 20)
        self.assertFalse(self.layer._gap_overlays[0].isVisible())

    def test_toggle_show_gap_overlays(self):
        """Toggling show_gap_overlays updates all existing gaps."""
        self.layer.add_gap_overlay(10, 20)
        self.layer.add_gap_overlay(30, 40)
        self.layer.show_gap_overlays = False
        for item in self.layer._gap_overlays:
            self.assertFalse(item.isVisible())
        self.layer.show_gap_overlays = True
        for item in self.layer._gap_overlays:
            self.assertTrue(item.isVisible())

    def test_gap_overlay_locked_flag(self):
        """add_gap_overlay(locked=True) sets the locked flag."""
        self.layer.add_gap_overlay(10, 20, locked=True)
        self.assertTrue(self.layer._gap_overlays[0]._locked)

    def test_gap_overlay_unlocked_by_default(self):
        self.layer.add_gap_overlay(10, 20)
        self.assertFalse(self.layer._gap_overlays[0]._locked)

    def test_set_all_gap_overlays_locked(self):
        self.layer.add_gap_overlay(10, 20)
        self.layer.add_gap_overlay(30, 40)
        self.layer.set_all_gap_overlays_locked(True)
        for item in self.layer._gap_overlays:
            self.assertTrue(item._locked)
        self.layer.set_all_gap_overlays_locked(False)
        for item in self.layer._gap_overlays:
            self.assertFalse(item._locked)

    def test_clear_decorations_removes_gaps(self):
        """The widget's clear_decorations clears the layer with the rest."""
        self.layer.add_gap_overlay(10, 20)
        self.w.add_marker(time=25)
        self.w.clear_decorations()
        self.assertEqual(len(self.layer._gap_overlays), 0)

    def test_a_widget_clear_removes_gaps_and_bands(self):
        self.layer.add_gap_overlay(10, 20)
        self.layer.set_shot_blocks([{"name": "S", "start": 0, "end": 50, "active": True}])
        self.w.clear()
        self.assertEqual(self.layer._gap_overlays, [])
        self.assertEqual(self.layer._shot_blocks, [])

    def test_gap_overlay_is_scene_item(self):
        """Gap overlays are added to the QGraphicsScene, under the track rows."""
        self.layer.add_gap_overlay(10, 20)
        scene = self.w._timeline.scene()
        gap_items = [item for item in scene.items() if isinstance(item, GapOverlay)]
        self.assertEqual(len(gap_items), 1)
        self.assertIs(gap_items[0].parentItem(), self.w.editor("tracks").content_root)

    def test_gap_edge_click_does_not_start_marquee(self):
        """Clicking a gap overlay edge must start a gap drag, not a marquee.

        Bug: mousePressEvent in TimelineView checked ItemIsSelectable
        which gap overlays don't have, so clicks fell to marquee code.
        Fixed: 2026-04-07
        """
        self.w.resize(800, 400)
        self.w.show()
        self.w.add_track("obj_A")
        self.layer.add_gap_overlay(50, 70)
        QtWidgets.QApplication.processEvents()

        tl = self.w._timeline
        gap_item = self.layer._gap_overlays[0]
        # Ensure the gap is within the visible viewport before mapping
        gap_rect = gap_item._rect()
        tl.ensureVisible(gap_rect, 50, 50)
        QtWidgets.QApplication.processEvents()
        # Map the right edge of the gap to view coords
        right_edge = QtCore.QPointF(gap_rect.right() - 2, gap_rect.center().y())
        view_pos = tl.mapFromScene(right_edge)

        # Simulate a left-button press at the gap's right edge
        QtTest.QTest.mousePress(
            tl.viewport(),
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier,
            QtCore.QPoint(int(view_pos.x()), int(view_pos.y())),
        )

        # Marquee should NOT have started
        self.assertFalse(
            tl._marquee_active,
            "Marquee started instead of forwarding to gap overlay!",
        )


# ---------------------------------------------------------- the shot lane


class TestShotBlocks(_LayerCase):
    """Shot blocks on the lane."""

    def test_set_shot_blocks(self):
        """set_shot_blocks populates the lane with blocks."""
        blocks = [
            {"name": "Shot_A", "start": 0, "end": 50, "active": True},
            {"name": "Shot_B", "start": 60, "end": 100, "active": False},
        ]
        self.layer.set_shot_blocks(blocks)
        self.assertEqual(len(self.layer._shot_blocks), 2)

    def test_clear_shot_blocks(self):
        blocks = [{"name": "S", "start": 0, "end": 50, "active": True}]
        self.layer.set_shot_blocks(blocks)
        self.layer.clear_shot_blocks()
        self.assertEqual(len(self.layer._shot_blocks), 0)

    def test_shot_blocks_replaced_on_set(self):
        """Calling set_shot_blocks replaces previous blocks."""
        self.layer.set_shot_blocks([{"name": "A", "start": 0, "end": 50, "active": True}])
        self.layer.set_shot_blocks(
            [
                {"name": "B", "start": 0, "end": 30, "active": True},
                {"name": "C", "start": 40, "end": 80, "active": False},
            ]
        )
        self.assertEqual(len(self.layer._shot_blocks), 2)

    def test_the_selected_shot_reads_back_with_its_id(self):
        self.layer.set_shot_blocks(
            [
                {"id": 7, "name": "A", "start": 0, "end": 50, "active": False},
                {"id": 9, "name": "B", "start": 60, "end": 90, "active": True},
            ]
        )
        self.assertEqual(self.layer.selected_shot()["id"], 9)
        self.assertEqual(self.layer.shot_block_at(70)["id"], 9)
        self.assertIsNone(self.layer.shot_block_at(55))
        self.layer.clear_shot_blocks()
        self.assertIsNone(self.layer.selected_shot())

    def _painted_lane(self, blocks, width=400):
        """The lane as :meth:`ShotLayer.paint_lane` draws *blocks* into a
        strip *width* wide over black."""
        self.layer.set_shot_blocks(blocks)
        image = QtGui.QImage(width, LANE, QtGui.QImage.Format_ARGB32)
        image.fill(QtGui.QColor(0, 0, 0))
        painter = QtGui.QPainter(image)
        try:
            self.layer.paint_lane(painter, QtCore.QRectF(0, 0, width, LANE))
        finally:
            painter.end()
        return image

    def test_the_active_band_carries_the_accent_rule(self):
        """Selection reads as a rule along the lane's top in the widget's
        accent, the active band's alone."""
        accent = QtGui.QColor(self.w.SELECTED_ACCENT)
        x_end = self.tl.time_to_x(100)
        image = self._painted_lane(
            [
                {"name": "A", "start": 0, "end": 100, "active": True},
                {"name": "B", "start": 100, "end": 200, "active": False},
            ]
        )
        # Clear of both labels: A's ends well before 3/4 of its band, and B's
        # starts 3px into its own.
        on = image.pixelColor(int(x_end * 0.75), 0)
        off = image.pixelColor(int(x_end) + 1, 0)
        self.assertGreater(on.blue(), 150, on.getRgb())
        self.assertGreater(on.blue(), on.red() + 60, "the accent's blue")
        self.assertLess(abs(on.blue() - accent.blue()), 40)
        self.assertLess(off.blue(), 60, f"an unselected band has no rule: {off.getRgb()}")

    def test_no_blocks_paint_nothing(self):
        image = self._painted_lane([])
        self.assertEqual(image.pixelColor(50, 0).getRgb()[:3], (0, 0, 0))


class TestTheLaneInTheHeader(_LayerCase):
    """The lane is its own strip: the ruler is ruler all the way down, the
    content clears both (uitk's ``TestContentTop`` / ``TestTimelineHitZones``
    with the shot layer added)."""

    def test_content_top_clears_the_ruler_and_the_lane(self):
        self.assertEqual(self.w._content_top, self.RULER + LANE)

    def test_the_lane_is_its_own_zone(self):
        self.assertEqual(self.tl.hit_zone(self.RULER - 1), "ruler")
        self.assertEqual(self.tl.hit_zone(self.RULER), "shot_lane")
        top = self.w._content_top
        self.assertEqual(self.tl.hit_zone(top - 1), "shot_lane")
        self.assertEqual(self.tl.hit_zone(top), "tracks")

    def test_the_lane_still_grabs_the_bound_under_another_editor(self):
        self.w.resize(800, 400)
        self.w.show()
        self.w.set_range_highlight(10, 60)
        self.w.set_editor("graph")
        x = self.tl.mapFromScene(self.tl.time_to_x(60), 0).x()
        zone = self.layer._band_zone(QtCore.QPoint(int(x), self.RULER + 3))
        self.assertEqual(zone, "right")


class TestShotLaneSitsBelowTheRuler(_LayerCase):
    """The shot band is its own strip; the ruler is ruler all the way down.

    Reported live, twice: "the blue shot border still overlaps the shot
    timeline ... we need to be able to click into that timeline area without
    selecting the shot".  The band used to occupy the bottom half of the
    ruler, so the active shot's accent rule was painted inside it and the
    bottom 12px of the ruler grabbed the shot instead of scrubbing.
    """

    SIZE = (900, 400)
    SHOW = True

    def setUp(self):
        super().setUp()
        self.tid = self.w.add_track("A")
        self.w.add_clip(self.tid, 40.0, 80.0, "c")
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": 40.0, "end": 120.0, "active": True}]
        )
        self.w.set_range_highlight(40.0, 120.0)
        self.emitted = []
        self.w.range_highlight_changed.connect(lambda a, b: self.emitted.append((a, b)))
        self.moved = []
        self.w.playhead_moved.connect(self.moved.append)

    def test_every_row_of_the_ruler_scrubs(self):
        """Including the bottom row, which the band used to own."""
        for y in (2, self.RULER // 2, self.RULER - 1):
            with self.subTest(y=y):
                self.emitted.clear()
                self.moved.clear()
                self._view_drag(120.0, 150.0, y=y)
                self.assertEqual(self.emitted, [], "the ruler must not resize the shot")
                self.assertTrue(self.moved, "it scrubs")

    def test_the_band_below_the_ruler_still_grabs_the_shot(self):
        self._view_drag(120.0, 150.0, y=self._lane_y())
        self.assertEqual(len(self.emitted), 1, self.emitted)
        self.assertEqual(self.moved, [], "the band moves the shot, it does not scrub")

    def test_the_ruler_item_covers_the_band_it_paints(self):
        ruler = self.tl._scene.ruler
        self.assertEqual(ruler.boundingRect().height(), self.RULER + LANE)

    def test_the_highlight_starts_clear_of_the_ruler(self):
        top = self.w._range_highlight._rect().top()
        self.assertGreaterEqual(top, self.RULER + LANE)

    def test_the_track_labels_line_up_with_the_tracks(self):
        margin = self.w._header._layout.contentsMargins().top()
        self.assertEqual(margin, self.RULER + LANE)


class TestShotBoundsDragFromTheRuler(_LayerCase):
    """A shot's bounds are drawn on the lane band, so they drag from there.

    They were drawn but inert: the highlight's hit area stops at the content
    top and a press on the band scrubbed the playhead instead.  The layer
    drives the item's own drag rather than the item reaching its geometry up
    into the ruler -- a view-dependent ``boundingRect`` re-enters the scene
    index on scroll and dies natively (measured: access violation).
    """

    SIZE = (900, 400)
    SHOW = True

    def setUp(self):
        super().setUp()
        self.tid = self.w.add_track("A")
        self.w.add_clip(self.tid, 40.0, 80.0, "c")
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": 40.0, "end": 120.0, "active": True}]
        )
        self.w.set_range_highlight(40.0, 120.0)
        self.SPAN = 120.0 - 40.0
        self.emitted = []
        self.w.range_highlight_changed.connect(lambda a, b: self.emitted.append((a, b)))
        self.moved = []
        self.w.playhead_moved.connect(self.moved.append)

    def _drag(self, from_time, to_time, y=None, modifiers=None):
        self._view_drag(
            from_time, to_time, self._lane_y() if y is None else y, modifiers
        )

    def test_dragging_the_end_bound_on_the_ruler_resizes_the_shot(self):
        """A grab of a bound moves that bound; the other stays."""
        self._drag(120.0, 150.0)
        self.assertEqual(len(self.emitted), 1, self.emitted)
        start, end = self.emitted[0]
        self.assertAlmostEqual(start, 40.0, places=0)
        self.assertAlmostEqual(end, 150.0, places=0)
        self.assertFalse(self.w.ctrl_held_at_press)

    def test_alt_dragging_a_bound_resizes_about_the_centre(self):
        """Alt: the other bound moves as far the other way (the graph's scale)."""
        self._drag(120.0, 150.0, modifiers=QtCore.Qt.AltModifier)
        self.assertEqual(len(self.emitted), 1, self.emitted)
        start, end = self.emitted[0]
        self.assertAlmostEqual(end, 150.0, places=0)
        self.assertAlmostEqual(start, 10.0, places=0, msg="mirrored about 80")

    def test_ctrl_dragging_the_end_bound_on_the_ruler_resizes_the_shot(self):
        self._drag(120.0, 150.0, modifiers=QtCore.Qt.ControlModifier)
        self.assertEqual(len(self.emitted), 1, self.emitted)
        start, end = self.emitted[0]
        self.assertAlmostEqual(start, 40.0, places=0)
        self.assertAlmostEqual(end, 150.0, places=0)
        self.assertTrue(self.w.ctrl_held_at_press)

    def test_dragging_the_start_bound_on_the_ruler_resizes_the_shot(self):
        self._drag(40.0, 20.0)
        self.assertEqual(len(self.emitted), 1, self.emitted)
        start, end = self.emitted[0]
        self.assertAlmostEqual(start, 20.0, places=0)
        self.assertAlmostEqual(end, 120.0, places=0)

    def test_ctrl_dragging_the_start_bound_on_the_ruler_resizes_the_shot(self):
        self._drag(40.0, 20.0, modifiers=QtCore.Qt.ControlModifier)
        self.assertEqual(len(self.emitted), 1, self.emitted)
        start, end = self.emitted[0]
        self.assertAlmostEqual(start, 20.0, places=0)
        self.assertAlmostEqual(end, 120.0, places=0)

    def test_the_band_between_the_bounds_moves_the_whole_shot(self):
        """The band is the ONE place the shot can be dragged bodily.

        The highlight's own body passes presses through so the timeline's
        marquee works inside the active shot -- it spans every track row of
        that shot, so claiming the gesture there left nowhere to marquee.
        The band is where the shot's extent is already drawn, so it is where
        the move lives instead.
        """
        self._drag(80.0, 90.0)
        self.assertEqual(len(self.emitted), 1, "a body drag emits once")
        start, end = self.emitted[0]
        self.assertAlmostEqual(
            end - start, self.SPAN, places=3, msg="a move must not resize the shot"
        )
        self.assertEqual(self.moved, [], "the band moves the shot, it does not scrub")

    def test_the_tick_row_above_the_lane_still_scrubs(self):
        self._drag(120.0, 150.0, y=2)
        self.assertEqual(self.emitted, [])
        self.assertTrue(self.moved)

    def test_a_press_without_a_move_emits_nothing(self):
        """Same zero-motion gate the item's own release keeps."""
        self._drag(120.0, 120.0)
        self.assertEqual(self.emitted, [])

    def test_no_handle_is_offered_when_the_highlight_is_hidden(self):
        self.w.show_range_highlight = False
        self._drag(120.0, 150.0)
        self.assertEqual(self.emitted, [])
        self.assertTrue(self.moved, "it scrubs, as the ruler otherwise would")

    def test_the_lane_shows_the_resize_cursor_over_a_bound(self):
        C, G = QtCore, QtGui
        hover = G.QMouseEvent(
            C.QEvent.MouseMove,
            C.QPointF(self._vx(120.0), self._lane_y()),
            C.Qt.NoButton,
            C.Qt.NoButton,
            C.Qt.NoModifier,
        )
        self.tl.mouseMoveEvent(hover)
        self.assertEqual(self.tl.viewport().cursor().shape(), C.Qt.SplitHCursor)

    def test_a_drag_whose_release_went_elsewhere_ends_on_the_next_hover(self):
        C, G = QtCore, QtGui
        y = self._lane_y()
        self.tl.mousePressEvent(
            G.QMouseEvent(
                C.QEvent.MouseButtonPress,
                C.QPointF(self._vx(120.0), y),
                C.Qt.LeftButton,
                C.Qt.LeftButton,
                C.Qt.NoModifier,
            )
        )
        self.tl.mouseMoveEvent(
            G.QMouseEvent(
                C.QEvent.MouseMove,
                C.QPointF(self._vx(150.0), y),
                C.Qt.NoButton,
                C.Qt.LeftButton,
                C.Qt.NoModifier,
            )
        )
        self.tl.mouseMoveEvent(  # the release never came
            G.QMouseEvent(
                C.QEvent.MouseMove,
                C.QPointF(self._vx(160.0), y),
                C.Qt.NoButton,
                C.Qt.NoButton,
                C.Qt.NoModifier,
            )
        )
        self.assertIsNone(self.layer._edge_drag)
        self.assertEqual(len(self.emitted), 1, "the drag committed where it was")


class TestCtrlShiftClickSwitchesShots(_LayerCase):
    """Ctrl+Shift+Click anywhere on the timeline asks for the shot there."""

    SIZE = (900, 400)
    SHOW = True

    def test_it_reports_the_time_and_takes_the_press(self):
        asked, moved = [], []
        self.layer.shot_switch_requested.connect(asked.append)
        self.w.playhead_moved.connect(moved.append)
        mods = QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
        for y in (5, self._lane_y(), int(self.w._content_top) + 100):
            self.tl.mousePressEvent(
                QtGui.QMouseEvent(
                    QtCore.QEvent.MouseButtonPress,
                    QtCore.QPointF(self._vx(80.0), y),
                    QtCore.Qt.LeftButton,
                    QtCore.Qt.LeftButton,
                    mods,
                )
            )
            self.tl.mouseReleaseEvent(
                QtGui.QMouseEvent(
                    QtCore.QEvent.MouseButtonRelease,
                    QtCore.QPointF(self._vx(80.0), y),
                    QtCore.Qt.LeftButton,
                    QtCore.Qt.NoButton,
                    mods,
                )
            )
        self.assertEqual(len(asked), 3)
        for t in asked:
            self.assertAlmostEqual(t, 80.0, places=0)
        self.assertEqual(moved, [], "no scrub")
        self.assertFalse(self.tl._marquee_active, "no marquee")


class TestShotLaneCoversTheWholeColumn(_LayerCase):
    """Right-clicking a shot over its TRACKS means the shot.

    The refinement used to apply only inside the ruler strip, so a
    right-click over the tracks -- which is most of the shot -- reported
    "tracks" and the consumer answered with the widget's own marker menu:
    no edit, no delete, nothing about the shot under the cursor.  The RULER
    is the other way round: it is the timeline itself, and it keeps its own
    zone so the timeline's menu has somewhere to open that does not depend
    on finding a spot no shot covers.
    """

    SIZE = (900, 400)

    def setUp(self):
        super().setUp()
        self.w.zone_menu_enabled = True
        self.tid = self.w.add_track("A")
        self.w.add_clip(self.tid, 0.0, 200.0, "c")
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": 40.0, "end": 120.0, "active": True}]
        )
        self.zones = []
        self.w.zone_context_menu_requested.connect(
            lambda zone, t, pos: self.zones.append((zone, t))
        )

    def _right_click(self, time, y):
        tl = self.w._timeline
        x = int(tl.time_to_x(time) - tl.horizontalScrollBar().value())
        ev = QtGui.QContextMenuEvent(
            QtGui.QContextMenuEvent.Mouse,
            QtCore.QPoint(x, y),
            tl.viewport().mapToGlobal(QtCore.QPoint(x, y)),
        )
        tl.contextMenuEvent(ev)

    def _empty_track_y(self):
        """Well below the single track: an item under the cursor forwards the
        event to ITS menu, which blocks on ``exec_``."""
        return int(self.w._content_top + 120)

    def test_a_click_over_the_tracks_inside_a_shot_is_the_shot_lane(self):
        self._right_click(80.0, self._empty_track_y())
        self.assertEqual([z for z, _t in self.zones], ["shot_lane"])

    def test_a_click_over_the_ruler_is_the_ruler_even_inside_a_shot(self):
        self._right_click(80.0, 4)
        self.assertEqual([z for z, _t in self.zones], ["ruler"])

    def test_the_shot_band_itself_is_always_the_shot_lane(self):
        """Between the ruler and the tracks: the band the shot is drawn in."""
        self._right_click(80.0, int(self.w._content_top) - 4)
        self.assertEqual([z for z, _t in self.zones], ["shot_lane"])

    def test_a_click_outside_every_shot_is_still_the_tracks(self):
        self._right_click(180.0, self._empty_track_y())
        self.assertEqual([z for z, _t in self.zones], ["tracks"])

    def test_the_reported_time_is_where_the_user_clicked(self):
        self._right_click(80.0, self._empty_track_y())
        self.assertAlmostEqual(self.zones[0][1], 80.0, places=0)


# ------------------------------------------------------- the scroll extent


class TestShotSpansWidenTheScene(_LayerCase):
    """Resizing a shot has to move the scrollable extent with it; a shot band
    before frame 0 is reachable on its own (no clip need follow it)."""

    SIZE = (900, 400)

    def setUp(self):
        super().setUp()
        self.tid = self.w.add_track("A")
        self.w.add_clip(self.tid, 0.0, 50.0, "c")

    def _reaches(self, time):
        rect = self.w._timeline._scene.sceneRect()
        x = self.w._timeline.time_to_x(time)
        return rect.left() <= x <= rect.right()

    def test_shot_blocks_widen_the_scene(self):
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": 0.0, "end": 8000.0, "active": True}]
        )
        self.assertTrue(self._reaches(8000.0))

    def test_a_gap_overlay_widens_the_scene(self):
        self.layer.add_gap_overlay(6000.0, 6500.0)
        self.assertTrue(self._reaches(6500.0))

    def test_a_shot_band_before_zero_widens_the_scene_alone(self):
        """The band is the thing the user resized; no clip need follow it."""
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": -80.0, "end": -20.0, "active": True}]
        )
        self.w._timeline._update_scene_rect()
        left = self.w._timeline._scene.sceneRect().left()
        self.assertLessEqual(left, self.w._timeline.time_to_x(-80.0))

    def test_an_inverted_block_does_not_pull_the_extent_inward(self):
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": 9000.0, "end": 7000.0, "active": True}]
        )
        self.assertTrue(self._reaches(9000.0))

    def test_a_bulk_rebuild_still_recomputes_only_once_at_exit(self):
        tl = self.w._timeline
        calls = []
        original = tl._update_scene_rect
        tl._update_scene_rect = lambda: (calls.append(1), original())[1]
        try:
            with self.w.bulk_updates():
                self.w.set_range_highlight(0.0, 900.0)
                self.layer.set_shot_blocks(
                    [{"id": 1, "name": "s", "start": 0.0, "end": 900.0}]
                )
                self.layer.add_gap_overlay(900.0, 950.0)
        finally:
            del tl._update_scene_rect
        self.assertEqual(len(calls), 1)


# ------------------------------------------------------------ gap gestures


class TestLockedGapNoDrag(_LayerCase):
    """A locked gap advertises a lock state but its drag handlers ignored
    ``_locked`` -- a locked gap could still be resized/moved and emit
    gap_resized / gap_left_resized / gap_moved.  It must now be inert."""

    SIZE = (800, 400)
    SHOW = True

    def _press(self, gap, scene_pt):
        ev = self._scene_ev(
            QtCore.QEvent.GraphicsSceneMousePress,
            scene_pt,
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier,
        )
        gap.mousePressEvent(ev)
        return ev

    def _move(self, gap, scene_pt):
        ev = self._scene_ev(QtCore.QEvent.GraphicsSceneMouseMove, scene_pt)
        gap.mouseMoveEvent(ev)
        return ev

    def _release(self, gap):
        ev = QtWidgets.QGraphicsSceneMouseEvent(QtCore.QEvent.GraphicsSceneMouseRelease)
        ev.setButton(QtCore.Qt.LeftButton)
        gap.mouseReleaseEvent(ev)
        return ev

    def test_locked_gap_press_starts_no_drag_and_emits_nothing(self):
        gap = self._gap(50, 70, locked=True)
        r = gap._rect()
        edge = QtCore.QPointF(r.right() - 1, r.center().y())  # resize zone
        emitted = []
        self.layer.gap_resized.connect(lambda *a: emitted.append(("resized", a)))
        self.layer.gap_moved.connect(lambda *a: emitted.append(("moved", a)))
        self.layer.gap_left_resized.connect(lambda *a: emitted.append(("left", a)))

        self._press(gap, edge)
        self.assertIsNone(gap._drag_mode, "locked gap must not enter a drag mode")
        self._move(gap, QtCore.QPointF(r.right() + 40, r.center().y()))
        self._release(gap)

        self.assertEqual(emitted, [], "a locked gap must emit no gap_* signals")
        self.assertEqual((gap._start, gap._end), (50.0, 70.0), "geometry unchanged")

    def test_unlocked_gap_right_edge_still_resizes_and_emits(self):
        """Control: the locked guard must not disable UNLOCKED gaps."""
        gap = self._gap(50, 70, locked=False)
        r = gap._rect()
        edge = QtCore.QPointF(r.right() - 1, r.center().y())
        emitted = []
        self.layer.gap_resized.connect(lambda a, b: emitted.append((a, b)))

        self._press(gap, edge)
        self.assertEqual(gap._drag_mode, "right")
        self._move(gap, QtCore.QPointF(r.right() + 40, r.center().y()))
        self._release(gap)
        self.assertEqual(len(emitted), 1, "unlocked gap resize must still emit")

    def test_a_gap_drag_captures_one_undo_step(self):
        gap = self._gap(50, 70)
        r = gap._rect()
        before = len(self.w._undo_stack)
        self._press(gap, QtCore.QPointF(r.right() - 1, r.center().y()))
        self._move(gap, QtCore.QPointF(r.right() + 40, r.center().y()))
        self._move(gap, QtCore.QPointF(r.right() + 60, r.center().y()))
        self.assertEqual(len(self.w._undo_stack), before + 1)
        self.assertTrue(gap.cancel_drag(), "Escape cancels it")
        self.assertEqual((gap._start, gap._end), (50.0, 70.0))


class TestNoGrabCursorUntilTheDragArms(_LayerCase):
    """A press is a click until the pointer clears Qt's drag distance: a gap
    press showed the grab and the frame label at PRESS, so every plain click
    flickered through a grab it never performed."""

    SIZE = (900, 400)

    def test_a_gap_press_does_not_arm_the_grab(self):
        gap = self._gap(50, 90)
        r = gap._rect()
        gap.mousePressEvent(
            self._scene_ev(
                QtCore.QEvent.GraphicsSceneMousePress,
                QtCore.QPointF(r.center().x(), r.center().y()),
                QtCore.Qt.LeftButton,
                screen_pt=QtCore.QPoint(500, 300),
            )
        )
        self.assertIsNotNone(gap._drag_mode, "the drag mode is still recorded")
        self.assertFalse(gap._grab_armed)
        self.assertFalse(gap._drag_tooltip.is_visible())


class TestTailGapOverlay(_LayerCase):
    """The last shot has no following shot, so the between-shots gap loop
    leaves it with no drag handle at its end.  A zero-width ``tail`` overlay
    supplies one, and it must expose ONLY the left edge (its right edge and
    body have no shot to act on)."""

    def test_tail_overlay_is_all_left_zone(self):
        gap = self._gap(100, 100, tail=True)
        r = gap._rect()
        for x in (r.left(), r.center().x(), r.right()):
            self.assertEqual(
                gap._hit_zone(QtCore.QPointF(x, r.center().y())),
                "left",
                "every press on a tail handle drags the preceding shot's end",
            )

    def test_tail_overlay_left_drag_emits_gap_left_resized(self):
        gap = self._gap(100, 100, tail=True)
        r = gap._rect()
        emitted = []
        self.layer.gap_left_resized.connect(lambda a, b: emitted.append((a, b)))
        centre = QtCore.QPointF(r.center().x(), r.center().y())
        gap.mousePressEvent(
            self._scene_ev(
                QtCore.QEvent.GraphicsSceneMousePress, centre, QtCore.Qt.LeftButton
            )
        )
        self.assertEqual(gap._drag_mode, "left")
        gap.mouseMoveEvent(
            self._scene_ev(
                QtCore.QEvent.GraphicsSceneMouseMove,
                QtCore.QPointF(r.center().x() + 40, r.center().y()),
            )
        )
        rel = QtWidgets.QGraphicsSceneMouseEvent(QtCore.QEvent.GraphicsSceneMouseRelease)
        rel.setButton(QtCore.Qt.LeftButton)
        gap.mouseReleaseEvent(rel)

        self.assertEqual(len(emitted), 1)
        self.assertAlmostEqual(emitted[0][0], 100.0)
        self.assertGreater(emitted[0][1], 100.0)

    def test_regular_gap_still_exposes_all_three_zones(self):
        self.w._timeline._pixels_per_unit = 4.0
        gap = self._gap(50, 90)
        r = gap._rect()
        y = r.center().y()
        self.assertEqual(gap._hit_zone(QtCore.QPointF(r.left() + 1, y)), "left")
        self.assertEqual(gap._hit_zone(QtCore.QPointF(r.center().x(), y)), "body")
        self.assertEqual(gap._hit_zone(QtCore.QPointF(r.right() - 1, y)), "right")


class TestTailLockImmunity(_LayerCase):
    """A tail handle is a shot-end handle, not a gap: locking it (any path)
    would leave the LAST shot with no way to resize."""

    def test_lock_all_gaps_skips_the_tail(self):
        self.layer.add_gap_overlay(50, 70)
        self.layer.add_gap_overlay(100, 100, tail=True)
        self.layer.set_all_gap_overlays_locked(True)
        gap, tail = self.layer._gap_overlays
        self.assertTrue(gap._locked)
        self.assertFalse(tail._locked, "lock-all must never brick the tail handle")

    def test_constructing_a_locked_tail_is_refused(self):
        self.layer.add_gap_overlay(100, 100, tail=True, locked=True)
        self.assertFalse(self.layer._gap_overlays[0]._locked)


class TestShotBoundCaps(_LayerCase):
    """The head/tail overlays are the first/last shot's own bound handles:
    each sits just OUTSIDE its bound (as a real gap's edge handle does), so
    the active shot's own handle keeps the pixels inside the bound, and its
    drag reads as a bound move, not a slide."""

    SIZE = (800, 300)

    def setUp(self):
        super().setUp()
        self.w.add_track("T")

    def _cap(self, **kw):
        return self._gap(100, 100, **kw)

    def test_tail_strip_starts_at_the_bound(self):
        item = self._cap(tail=True)
        r = item._rect()
        self.assertAlmostEqual(r.left(), self.tl.time_to_x(100), places=3)
        self.assertEqual(r.width(), item._MIN_PX)

    def test_head_strip_ends_at_the_bound(self):
        item = self._cap(head=True)
        r = item._rect()
        self.assertAlmostEqual(r.right(), self.tl.time_to_x(100), places=3)
        self.assertEqual(r.width(), item._MIN_PX)

    def test_caps_expose_one_edge_each(self):
        self.assertEqual(self._cap(tail=True)._hit_zone(QtCore.QPointF(0, 0)), "left")
        self.assertEqual(self._cap(head=True)._hit_zone(QtCore.QPointF(0, 0)), "right")

    def test_caps_never_lock(self):
        head = self._cap(head=True, locked=True)
        tail = self._cap(tail=True, locked=True)
        self.layer.add_gap_overlay(10, 20)
        self.layer.set_all_gap_overlays_locked(True)
        self.assertFalse(head._locked)
        self.assertFalse(tail._locked)
        self.assertTrue(self.layer._gap_overlays[-1]._locked)

    def test_a_plain_cap_drag_reads_as_a_resize(self):
        for kw in ({"tail": True}, {"head": True}):
            item = self._cap(**kw)
            item._drag_mode = "left" if kw.get("tail") else "right"
            self.w.record_press_modifiers(QtCore.Qt.NoModifier)
            self.assertTrue(item._gap_drag_label().startswith("Resize "), kw)
            self.w.record_press_modifiers(QtCore.Qt.ControlModifier)
            self.assertTrue(item._gap_drag_label().startswith("Trim "), kw)
            self.w.record_press_modifiers(QtCore.Qt.ShiftModifier)
            self.assertTrue(item._gap_drag_label().startswith("Retime "), kw)
        gap = self._gap(10, 20)
        gap._drag_mode = "left"
        self.w.record_press_modifiers(QtCore.Qt.NoModifier)
        self.assertTrue(gap._gap_drag_label().startswith("Slide "))

    def test_a_head_cap_can_be_dragged_both_ways(self):
        item = self._cap(head=True)
        item._drag_mode = "right"
        item._drag_origin_x = self.tl.time_to_x(100)
        item._drag_origin_start = item._drag_origin_end = 100.0
        item._undo_captured = True
        item._grab_armed = True
        dx = self.tl.time_to_x(80) - self.tl.time_to_x(100)

        class _Ev:
            def __init__(self, x):
                self._x = x

            def scenePos(self):
                return QtCore.QPointF(self._x, 0)

            def accept(self):
                pass

        item.mouseMoveEvent(_Ev(item._drag_origin_x + dx))
        self.assertAlmostEqual(item._end, 80.0, places=3, msg="grew backwards")
        self.assertAlmostEqual(item._start, 80.0, places=3)

    def test_gesture_context_calls_a_cap_a_shot_bound(self):
        seen = []
        self.w.shortcut_overlay_visible = True
        self.w._set_gesture_context = seen.append
        item = self._cap(tail=True)
        gap = self._gap(10, 20)
        self.w.show()
        for overlay, expected in ((item, "Shot bounds"), (gap, "Gaps")):
            view_pos = self.tl.mapFromScene(overlay._rect().center())
            self.assertIs(self.tl.itemAt(view_pos), overlay)
            self.tl._sync_gesture_context(view_pos)
            self.assertEqual(seen[-1], expected)


class TestTheShotBoundOwnsItsEdge(_LayerCase):
    """At a bound, an unlocked gap's PAINTED rect answers as the gap; a gap of
    zero width does not (it IS the bound there) -- uitk's
    ``TestTheShotBoundOwnsItsEdge``, the gap half (``ShotLayer.claims_press``)."""

    SIZE = (900, 400)
    SHOW = True

    def setUp(self):
        super().setUp()
        own = self.w.add_track("own")
        nbr = self.w.add_track("nbr")
        self.own = self.w.add_clip(own, 40, 80)  # ends ON the bound
        self.mid = self.w.add_clip(nbr, 40, 30)  # ends well inside the shot
        self.w.add_clip(
            nbr, 120, 60, locked=True, read_only=True, dimmed=True
        )  # the next shot's, starting on the bound
        self.w.set_range_highlight(40, 120)
        QtWidgets.QApplication.processEvents()
        self.bounds = []
        self.w.range_highlight_changed.connect(lambda a, b: self.bounds.append((a, b)))

    def _row_y(self, cid):
        return self.w._clip_items[cid].sceneBoundingRect().center().y()

    def _drag(self, scene_x, scene_y, dx):
        C, G = QtCore, QtGui
        start = self.tl.mapFromScene(C.QPointF(scene_x, scene_y))
        end = self.tl.mapFromScene(C.QPointF(scene_x + dx, scene_y))
        for kind, pt, btn, btns in (
            (C.QEvent.MouseButtonPress, start, C.Qt.LeftButton, C.Qt.LeftButton),
            (C.QEvent.MouseMove, end, C.Qt.NoButton, C.Qt.LeftButton),
            (C.QEvent.MouseButtonRelease, end, C.Qt.LeftButton, C.Qt.NoButton),
        ):
            ev = G.QMouseEvent(
                kind,
                C.QPointF(pt),
                C.QPointF(self.tl.viewport().mapToGlobal(pt)),
                btn,
                btns,
                C.Qt.NoModifier,
            )
            {
                C.QEvent.MouseButtonPress: self.tl.mousePressEvent,
                C.QEvent.MouseMove: self.tl.mouseMoveEvent,
                C.QEvent.MouseButtonRelease: self.tl.mouseReleaseEvent,
            }[kind](ev)

    def _bound_x(self):
        return self.tl.time_to_x(120)

    def test_a_zero_width_gap_on_the_bound_yields_to_it(self):
        """At a gap of zero the gap overlay is a strip centred on the seam;
        it has no width of its own to resize, so the bound is what a press
        there grabs (measured on the production assembly: the press went to
        the gap and slid the next shot)."""
        self.layer.add_gap_overlay(120, 120)
        gaps = []
        self.layer.gap_resized.connect(lambda *a: gaps.append(a))
        self.layer.gap_left_resized.connect(lambda *a: gaps.append(a))
        self._drag(self._bound_x() + 1, self._row_y(self.mid), -40)
        self.assertEqual(len(self.bounds), 1, "the bound drag never started")
        self.assertEqual(gaps, [])

    def test_a_real_gaps_edge_still_answers_as_the_gap(self):
        self.layer.add_gap_overlay(120, 140)
        gaps = []
        self.layer.gap_left_resized.connect(lambda *a: gaps.append(a))
        self._drag(self._bound_x() + 2, self._row_y(self.mid), 30)
        self.assertEqual(self.bounds, [])
        self.assertEqual(len(gaps), 1)

    def test_a_hidden_gap_claims_nothing(self):
        self.layer.add_gap_overlay(120, 140)
        self.layer.show_gap_overlays = False
        self._drag(self._bound_x() + 2, self._row_y(self.mid), 30)
        self.assertEqual(len(self.bounds), 1, "the bound answers")


class TestBoundHandleGrammar(_LayerCase):
    """A gap's edge press records Ctrl, and its frame label names the trim."""

    SIZE = (900, 400)
    SHOW = True

    def test_a_gap_edge_press_records_ctrl_and_labels_the_trim(self):
        self.w.add_track("A")
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": 40.0, "end": 120.0, "active": True}]
        )
        self.w.set_range_highlight(40.0, 120.0)
        gap = self._gap(120, 160)
        r = gap._rect()
        pt = QtCore.QPointF(r.right() - 1, r.center().y())
        gap.mousePressEvent(
            self._scene_ev(
                QtCore.QEvent.GraphicsSceneMousePress,
                pt,
                QtCore.Qt.LeftButton,
                QtCore.Qt.ControlModifier,
            )
        )
        self.assertEqual(gap._drag_mode, "right")
        self.assertTrue(self.w.ctrl_held_at_press)
        self.assertTrue(gap._gap_drag_label().startswith("Trim 160"))


# --------------------------------------------------------- legend and menus


class TestTheShotLegend(_LayerCase):
    """The track view's legend is the shot grammar: the shot groups first,
    the shot rows in their places (uitk's ``TestShortcutOverlay`` /
    ``TestEditorSeam`` with the layer added)."""

    SIZE = (900, 400)
    SHOW = True

    #: The legend as the panel showed it before the layer moved: the order and
    #: every row, word for word.
    EXPECTED = (
        ("Shot bounds", "Drag", "Move the bound; neighbours ripple (keys stay)"),
        ("Shot bounds", "Ctrl+Drag", "Move the bound only; a neighbour's gives way"),
        ("Shot bounds", "Shift+Drag", "Retime keys into the new span"),
        ("Shot bounds", "Alt+Drag", "Resize about the shot's centre"),
        ("Shot bounds", "Drag band", "Move the shot (keys ride)"),
        ("Gaps", "Drag edge", "Slide the shot beyond it (gap changes)"),
        ("Gaps", "Ctrl+Drag edge", "Move that bound only (keys stay)"),
        ("Gaps", "Shift+Drag edge", "Retime that shot into the new span"),
        ("Gaps", "Drag body", "Slide the gap (active shot's edge follows)"),
        ("Gaps", "Right-click", "Lock / unlock the gap"),
        ("Clips & keys", "Drag", "Move keys (ripple)"),
        ("Clips & keys", "Drag edge", "Scale the clip's keys"),
        ("Clips & keys", "Drag edge (multi)", "Scale the whole selection as one"),
        ("Clips & keys", "Shift (keys selected)", "Scale box: drag an end to retime"),
        ("Clips & keys", "Alt+Drag a scale end", "Scale about the playhead instead"),
        ("Clips & keys", "Shift+Drag", "Cross shot bounds, bounds stay"),
        ("Clips & keys", "Ctrl", "Snap to whole frames"),
        ("Clips & keys", "Right-click", "Tangents, lock, Move to Shot"),
        ("Tangents", "Drag a handle", "Reshape every selected key's tangent"),
        ("Tangents", "Ctrl+Drag", "Reshape the grabbed key only"),
        ("Tangents", "Shift+Drag", "Give every selected key this exact tangent"),
        ("Tangents", "Alt+Drag", "Break the tangent (dotted while held)"),
        ("Timeline", "Drag", "Marquee select (Space moves it)"),
        ("Timeline", "Ctrl+Shift+Click", "Switch to the shot under the cursor"),
        ("Timeline", "Wheel / Middle-drag", "Zoom / pan"),
    )

    def test_the_legend_is_the_panels_word_for_word(self):
        self.assertEqual(self.w._legend, self.EXPECTED)

    def test_gestures_are_registered_with_the_manager(self):
        mgr = self.w._shortcut_mgr
        self.assertEqual(
            list(mgr.gestures),
            ["Shot bounds", "Gaps", "Clips & keys", "Tangents", "Timeline"],
        )
        entry = mgr.shortcuts["Ctrl+Drag (Shot bounds)"]
        self.assertTrue(entry["read_only"], "listed in the editor, not rebindable")

    def test_another_editor_shows_its_own_and_the_track_view_gets_them_back(self):
        groups = self.w._shortcut_mgr.gestures
        self.w.set_editor("graph")
        self.assertNotIn("Shot bounds", groups)
        self.w.set_editor("tracks")
        self.assertEqual(self.w._legend, self.EXPECTED)

    def test_the_hovered_group_is_the_one_shown(self):
        self.w.shortcut_overlay_visible = True
        overlay = self.w.shortcut_overlay
        self.assertEqual(overlay.shown_group, "Shot bounds")
        self.w._set_gesture_context("Gaps")
        self.assertEqual(overlay.shown_group, "Gaps")
        self.assertIn("Lock / unlock the gap", overlay._label.text())
        self.assertNotIn("Marquee", overlay._label.text())
        self.w._set_gesture_context(None)
        self.assertEqual(overlay.shown_group, "Shot bounds")

    def test_the_timeline_reports_the_group_under_the_pointer(self):
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": 40.0, "end": 120.0, "active": True}]
        )
        self.w.set_range_highlight(40.0, 120.0)
        gap = self._gap(120, 160)
        self.w.shortcut_overlay_visible = True
        centre = gap._rect().center()
        vp = self.tl.mapFromScene(centre)
        self.tl._sync_gesture_context(QtCore.QPoint(vp.x(), vp.y()))
        self.assertEqual(self.w.shortcut_overlay.shown_group, "Gaps")

    def test_the_lane_and_the_highlights_edge_are_shot_bounds(self):
        self.w.add_track("A")
        self.w.set_range_highlight(40.0, 120.0)
        self.w.shortcut_overlay_visible = True
        x = self._vx(120.0)
        self.tl._sync_gesture_context(QtCore.QPoint(x, self._lane_y()))
        self.assertEqual(self.w._gesture_context, "Shot bounds")
        self.tl._sync_gesture_context(QtCore.QPoint(self._vx(80.0), self._lane_y()))
        self.assertEqual(self.w._gesture_context, "Shot bounds", "the band's body")
        self.tl._sync_gesture_context(QtCore.QPoint(self._vx(300.0), self._lane_y()))
        self.assertEqual(self.w._gesture_context, "Timeline", "no grab there")
        edge = self.tl.mapFromScene(
            self.w.range_highlight_item._rect().topRight() + QtCore.QPointF(-1, 5)
        )
        self.tl._sync_gesture_context(edge)
        self.assertEqual(self.w._gesture_context, "Shot bounds")

    def test_on_modifier_opens_on_the_page_the_pointer_is_over(self):
        """The lit group is a mouse-MOVE answer and the legend rises between
        two of them, so the group is tracked while it is still hidden."""
        self.layer.set_shot_blocks(
            [{"id": 1, "name": "s", "start": 40.0, "end": 120.0, "active": True}]
        )
        self.w.set_range_highlight(40.0, 120.0)
        gap = self._gap(120, 160)
        self.w.shortcut_overlay_mode = "modifier"
        centre = gap._rect().center()
        vp = self.tl.mapFromScene(centre)
        self.tl._sync_gesture_context(QtCore.QPoint(vp.x(), vp.y()))
        self.w.set_modifiers_held(QtCore.Qt.ControlModifier)
        self.assertEqual(self.w.shortcut_overlay.shown_group, "Gaps")


class TestTheTimelineMenu(_LayerCase):
    """The timeline's own entries, as the panel shows them: the range overlays
    are the shots', the gap overlays' toggle follows them (uitk's
    ``TestDefaultContextEntries`` / ``TestDefaultContextActionsFoldIntoAnyMenu``)."""

    SIZE = (900, 400)

    def test_entries_shape(self):
        entries = self.tl.default_context_entries(42.0)
        labels = [e["label"] for e in entries if e is not None]
        self.assertEqual(labels[0], "Add Marker at 42…")
        self.assertIn(None, entries, "a separator after the marker entry")
        self.assertEqual(
            labels[1:], ["Show Shot Ranges", "Show Active Range", "Show Gap Overlays"]
        )
        for e in entries[2:]:
            self.assertTrue(e["checkable"])
            self.assertTrue(e["checked"], "every display toggle starts on")

    def test_a_toggle_callback_drives_the_layer(self):
        entries = self.tl.default_context_entries(0.0)
        gaps = next(e for e in entries if e and e["label"] == "Show Gap Overlays")
        gaps["callback"](False)
        self.assertFalse(self.layer.show_gap_overlays)
        self.assertFalse(self.tl.default_context_entries(0.0)[-1]["checked"])
        gaps["callback"](True)
        self.assertTrue(self.layer.show_gap_overlays)

    def test_the_shot_ranges_toggle_drives_the_range_overlays(self):
        entries = self.tl.default_context_entries(0.0)
        ranges = next(e for e in entries if e and e["label"] == "Show Shot Ranges")
        ranges["callback"](False)
        self.assertFalse(self.w.show_range_overlays)

    def test_qmenu_rendering_matches_the_entries(self):
        menu = QtWidgets.QMenu()
        handled = self.tl.add_default_context_actions(menu, 7.0)
        acts = [a for a in menu.actions() if not a.isSeparator()]
        self.assertEqual(
            [a.text() for a in acts],
            [e["label"] for e in self.tl.default_context_entries(7.0) if e],
        )
        gap_act = acts[-1]
        self.assertTrue(gap_act.isCheckable() and gap_act.isChecked())
        gap_act.setChecked(False)
        self.assertTrue(handled(gap_act))
        self.assertFalse(self.layer.show_gap_overlays)
        self.assertFalse(handled(None))
        menu.deleteLater()

    def test_the_handler_owns_its_own_actions_and_nothing_else(self):
        menu = QtWidgets.QMenu(self.w)
        mine = menu.addAction("Delete Shot")
        handled = self.tl.add_default_context_actions(menu, 42.0)
        toggle = next(a for a in menu.actions() if a.text() == "Show Gap Overlays")
        toggle.setChecked(False)
        self.assertTrue(handled(toggle))
        self.assertFalse(self.layer.show_gap_overlays)
        self.assertFalse(handled(mine), "a consumer action must fall through")
        self.assertFalse(handled(None), "a dismissed menu is nobody's action")

    def test_the_gap_menu_offers_the_lock_rows_and_the_controllers(self):
        """The gap's own menu: lock rows (none on a cap), then the controller's
        rows through ``gap_menu_requested`` -- read before it opens."""
        rows = []

        def capture(menu, start, end):
            rows.append(([a.text() for a in menu.actions()], start, end))
            menu.clear()  # nothing left to open: the menu returns unshown

        self.layer.gap_menu_requested.connect(capture)
        gap = self._gap(50, 70)
        cap = self._gap(100, 100, tail=True)
        for item in (gap, cap):
            event = QtWidgets.QGraphicsSceneContextMenuEvent(
                QtCore.QEvent.GraphicsSceneContextMenu
            )
            item.contextMenuEvent(event)
        self.assertEqual(
            rows[0], (["Lock Gap", "", "Lock All Gaps", "Unlock All Gaps"], 50, 70)
        )
        self.assertEqual(rows[1], ([], 100, 100), "a cap offers no lock")


# ------------------------------------------------------- held geometry


class TestItemsHoldTheGeometryTheSceneIndexed(_LayerCase):
    """A gap answers the bounds it was indexed under until it syncs (uitk's
    ``TestItemsHoldTheGeometryTheSceneIndexed``: the BSP index files an item
    under the rect it returned when indexed; a live rect missed the cells at
    removal and the next repaint dereferenced a destroyed item)."""

    SIZE = (900, 400)

    def setUp(self):
        super().setUp()
        for name in ("a", "b", "c", "d"):
            tid = self.w.add_track(name)
            self.w.add_clip(tid, 60, 40)

    def test_a_gap_overlay_holds_through_a_zoom(self):
        item = self._gap(101.0, 120.0)
        before = QtCore.QRectF(item.boundingRect())
        self.w._timeline._pixels_per_unit *= 2.0  # the bare input, no refresh
        self.assertEqual(item.boundingRect(), before, "moved without a sync")
        item.sync()
        self.assertNotEqual(item.boundingRect(), before, "the sync never followed")

    def test_a_row_change_re_derives_the_gaps(self):
        item = self._gap(101.0, 120.0)
        before = QtCore.QRectF(item.boundingRect())
        for name in ("e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p"):
            self.w.add_track(name)  # rows past the viewport: the gap grows
        self.assertGreater(item.boundingRect().height(), before.height())

    def test_the_new_shot_undo_rebuild_does_not_crash(self):
        """The calls the shot sequencer made, replayed: a new first shot
        drawn, then the rebuild that cleared it.  Run in a child process --
        before the fix it died natively, which would take this suite down."""
        script = (
            "import os, sys\n"
            "from qtpy import QtWidgets\n"
            "app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])\n"
            "import uitk\n"
            "from uitk import SequencerWidget\n"
            "from tentacle.slots.tools._shot_sequencer.shot_layer import ShotLayer\n"
            "class Sb:\n"
            "    def __getattr__(self, name):\n"
            "        return getattr(uitk, name)\n"
            "w = SequencerWidget(); w.resize(900, 400); w.show(); app.processEvents()\n"
            "layer = ShotLayer.of(w, Sb())\n"
            "w.clear(); tid = w.add_track('ctlB')\n"
            "w.add_clip(track_id=tid, start=60.0, duration=40.0)\n"
            "w.set_playhead(1.0); w.set_active_range(1.0, 120.0); w.frame_shot()\n"
            "app.processEvents()\n"
            "with w.bulk_updates():\n"
            "    w.clear(keep_range_highlight=True); tid = w.add_track('ctlB')\n"
            "    w.add_clip(track_id=tid, start=60.0, duration=40.0)\n"
            "    w.set_playhead(1.0); w.set_active_range(1.0, 101.0)\n"
            "    w.set_range_highlight(1.0, 101.0)\n"
            "    layer.set_shot_blocks([{'id': 0, 'name': 'S', 'start': 1.0,"
            " 'end': 101.0, 'active': True}])\n"
            "    layer.add_gap_overlay(101.0, 101.0, tail=True)\n"
            "    layer.add_gap_overlay(1.0, 1.0, head=True)\n"
            "app.processEvents()\n"
            "w.clear(); w._timeline._scene.update()\n"
            "for _ in range(5): app.processEvents()\n"
            "print('survived', flush=True)\n"
            "os._exit(0)\n"
        )
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        roots = [str(Path(tentacle.__file__).resolve().parents[1])]
        roots += [p for p in sys.path if p]
        env["PYTHONPATH"] = os.pathsep.join(
            dict.fromkeys(roots + [env.get("PYTHONPATH", "")]).keys()
        ).strip(os.pathsep)
        proc = subprocess.run(
            [sys.executable, "-c", script],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertIn("survived", proc.stdout, proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
