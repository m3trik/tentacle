# !/usr/bin/python
# coding=utf-8
"""The shot layer: the Shot Sequencer's shots on uitk's timeline.

Provides :class:`ShotLayer` -- the shot lane under the ruler, the gaps between
shots and the caps on the first and last shot's outer bounds, the shot
gestures and Ctrl+Shift+Click to switch shots -- and :class:`GapOverlay`, the
gap's scene item.  uitk's ``SequencerWidget`` names no domain: this is the
panel's vocabulary on it, plugged in through its layer seam
(``SequencerWidget.add_layer``; uitk's ``SequencerLayer`` protocol) and
touching the widget through its public surface only.

The layer draws and reports; the controller decides.  Its signals carry the
user's gestures out (``gap_resized``, ``shot_switch_requested``...), the
panel's wiring routes them to the controller's handlers (``gap_manager``,
``shot_lane``), and the controller hands the shots back in
(:meth:`ShotLayer.set_shot_blocks`, :meth:`ShotLayer.add_gap_overlay`).

uitk is reached through the Switchboard (``sb``) the controller hands in: the
gap item's bases (``HeldGeometryMixin``, ``DraggableItemMixin``) and the parts
it draws with (``FrameTooltip``, ``MenuUtils``, ``PatternRegistry``,
``CursorManager``, ``ClipItem``).
"""

from typing import List, Optional, Tuple

from qtpy import QtCore, QtGui, QtWidgets


class GapOverlay:
    """Diagonal-hatch overlay for a gap between shots (behaviour).

    Displays the gap duration as centered text and a tooltip on hover.
    Supports three drag modes:
    - **Right edge**: resize gap (shifts the next shot and all downstream).
    - **Left edge**: resize gap from the left (shifts the prev shot end).
    - **Center** (body drag): reposition the gap, keeping gap size constant.
      Automatically disabled when the gap is too narrow for a center zone.

    ``tail=True`` marks the zero-width overlay placed after the LAST shot,
    which has no following shot to form a real gap with.  It exposes only the
    left edge -- i.e. that shot's ``end`` -- so the final shot gets the same
    drag handle every other shot already has.  ``head=True`` is its twin
    before the FIRST shot: right edge only, that shot's ``start``.  Both are
    shot BOUNDS, not gaps: the strip sits just outside the shot (a real gap's
    edge handle does too), so the active shot's own bound handle keeps the
    pixels inside the bound, and the controller treats a drag on either as a
    bound move, never a slide.

    Behaviour only: the scene item is :meth:`item_class` -- this class on
    uitk's draggable-item bases, which a slots module reaches through the
    Switchboard alone, never by import.
    """

    _EDGE_WIDTH = 6  # px from each edge that triggers resize cursor
    _MIN_PX = 4  # minimum visual width so zero-width gaps remain visible

    @classmethod
    def item_class(cls, sb):
        """The gap's scene-item class: this behaviour first, then uitk's
        ``HeldGeometryMixin`` (layout-derived bounds held until announced),
        ``DraggableItemMixin`` (Escape and lost-grab cancel, snapping, the
        drag threshold) and ``QGraphicsItem``.

        Parameters:
            sb: The Switchboard (or any object resolving uitk's public names).
        """

        class GapOverlayItem(
            cls, sb.HeldGeometryMixin, sb.DraggableItemMixin, QtWidgets.QGraphicsItem
        ):
            """A :class:`GapOverlay` in the scene."""

        return GapOverlayItem

    def __init__(
        self,
        layer: "ShotLayer",
        start: float,
        end: float,
        color: str,
        alpha: int,
        locked: bool = False,
        tail: bool = False,
        head: bool = False,
    ):
        super().__init__()
        self._layer = layer
        self._sb = layer.sb
        self._timeline = layer.sequencer.timeline
        self._start = start
        self._end = end
        self._tail = tail
        self._head = head
        self._base_alpha = alpha
        self._color = QtGui.QColor(color)
        self._color.setAlpha(alpha)
        self._line_color = QtGui.QColor(color)
        self._line_color.setAlpha(min(255, alpha + 40))
        self._hovered = False
        # A head/tail handle is not a gap -- it has no second shot to key a
        # lock on, and a locked one would leave the first/last shot without
        # its only outer handle.  Locking is refused at the source.
        self._locked = locked and not (tail or head)
        self._drag_mode: Optional[str] = None  # "left", "right", "move", or None
        self._drag_origin_x: float = 0.0
        self._drag_origin_start: float = 0.0
        self._drag_origin_end: float = 0.0
        self.setZValue(-3)
        self.setAcceptHoverEvents(True)
        self._gap_frames = int(round(end - start))
        self._update_tooltip()
        self._drag_tooltip = self._sb.FrameTooltip()

    def _update_tooltip(self):
        self._gap_frames = max(0, int(round(self._end - self._start)))
        lock_label = " [Locked]" if self._locked else ""
        mode = self._drag_mode
        if self._tail:
            frame = int(round(self._start))
            self.setToolTip(
                f"Shot end: frame {frame}{lock_label}"
                "\nDrag to move the last shot's end (keys stay)"
                "\nRight-click for options"
            )
            return
        if self._head:
            frame = int(round(self._end))
            self.setToolTip(
                f"Shot start: frame {frame}{lock_label}"
                "\nDrag to move the first shot's start (keys stay)"
                "\nRight-click for options"
            )
            return
        if mode == "left":
            frame = int(round(self._start))
            info = f"◀ Left edge → frame {frame}"
        elif mode == "right":
            frame = int(round(self._end))
            info = f"Right edge ▶ → frame {frame}"
        elif mode == "move":
            info = (
                f"Sliding → {int(round(self._start))}–{int(round(self._end))}"
            )
        else:
            info = "Drag edges to resize · Drag center to reposition"
        self.setToolTip(
            f"Gap: {self._gap_frames} frame{'s' if self._gap_frames != 1 else ''}{lock_label}"
            f"\n{info}"
            "\nRight-click for options"
        )

    def _rect(self) -> QtCore.QRectF:
        return self._geometry()

    def _layout_geometry(self) -> QtCore.QRectF:
        tl = self._timeline
        x0 = tl.time_to_x(self._start)
        x1 = tl.time_to_x(self._end)
        w = x1 - x0
        if self._tail:
            # The strip sits just PAST the bound, where a real gap's edge
            # handle sits: centred on it, it covered the pixels inside the
            # bound that the active shot's own handle owns, and a press on
            # the last shot's end went to the wrong handle.
            x0, w = x1, self._MIN_PX
        elif self._head:
            x0, w = x0 - self._MIN_PX, self._MIN_PX
        elif w < self._MIN_PX:
            mid = (x0 + x1) * 0.5
            x0 = mid - self._MIN_PX * 0.5
            w = self._MIN_PX
        top, h = self._layer.sequencer.content_span()
        return QtCore.QRectF(x0, top, w, h)

    def boundingRect(self) -> QtCore.QRectF:
        r = self._rect()
        return r.adjusted(-self._EDGE_WIDTH, 0, self._EDGE_WIDTH, 0)

    def _hit_zone(self, pos: QtCore.QPointF) -> str:
        # A tail handle has no following shot, so "right" (move the next
        # shot's start) and "body" (slide the whole gap) have no target --
        # every press on it is a drag of the preceding shot's end; a head
        # handle is the mirror, every press drags the first shot's start.
        if self._tail:
            return "left"
        if self._head:
            return "right"
        r = self._rect()
        local_x = pos.x() - r.left()
        if local_x <= self._EDGE_WIDTH:
            return "left"
        if local_x >= r.width() - self._EDGE_WIDTH:
            return "right"
        return "body"

    def hoverEnterEvent(self, event):
        self._hovered = True
        self._color.setAlpha(min(255, self._base_alpha + 50))
        self._line_color.setAlpha(min(255, self._base_alpha + 90))
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self._color.setAlpha(self._base_alpha)
        self._line_color.setAlpha(min(255, self._base_alpha + 40))
        self.unsetCursor()
        self.update()

    def hoverMoveEvent(self, event):
        # A locked gap advertises no drag/resize affordance -- keep the
        # plain arrow so the SizeHor/OpenHand cursors don't imply an
        # interaction the press handler now refuses.
        if self._locked or self._clip_at(event.scenePos()):
            self.setCursor(QtCore.Qt.ArrowCursor)
            return
        zone = self._hit_zone(event.pos())
        if zone in ("left", "right"):
            self.setCursor(QtCore.Qt.SizeHorCursor)
        elif zone == "body":
            self.setCursor(QtCore.Qt.OpenHandCursor)
        else:
            self.setCursor(QtCore.Qt.ArrowCursor)

    def _clip_at(self, scene_pos: QtCore.QPointF) -> bool:
        """Return True if a clip item exists at *scene_pos*."""
        clip_cls = self._sb.ClipItem
        return any(isinstance(item, clip_cls) for item in self.scene().items(scene_pos))

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            event.ignore()
            return
        # A locked gap must not move or resize.  Ignore the press so it
        # falls through (e.g. to marquee) instead of starting a drag --
        # the drag/resize handlers and their gap_* signal emissions all
        # hang off the drag mode set below.
        if self._locked:
            event.ignore()
            return
        zone = self._hit_zone(event.pos())
        self._drag_mode = "move" if zone == "body" else zone  # "left"/"right"
        self._drag_origin_x = event.scenePos().x()
        self._drag_origin_start = self._start
        self._drag_origin_end = self._end
        # The grab cursor and the floating frame label are what a DRAG looks
        # like, and a press is not one until the pointer clears Qt's drag
        # distance -- showing them at press made every plain click (and the
        # first half of every double-click) flicker through a grab it never
        # performed.  Armed on the first real move, like the clip body.
        self._grab_armed = False
        self._press_screen_pos = event.screenPos()
        self._layer.sequencer.record_press_modifiers(event.modifiers())
        # Undo snapshot is captured lazily on the first real move -- a
        # plain click must not burn an undo step or wipe redo.
        self._undo_captured = False
        event.accept()

    def _arm_gap_grab(self, event) -> None:
        """Show the grab, now that the gesture is one."""
        self._grab_armed = True
        if self._drag_mode == "move":
            self._sb.CursorManager.push(self, QtCore.Qt.ClosedHandCursor)
        self._show_gap_drag_tooltip(event.scenePos())

    def mouseMoveEvent(self, event):
        if self._drag_mode is None:
            event.ignore()
            return
        if not self._grab_armed:
            if not self._past_drag_threshold(event):
                event.accept()  # still a click, as far as anyone can tell
                return
            self._arm_gap_grab(event)
        self._capture_drag_undo()
        dx = event.scenePos().x() - self._drag_origin_x
        ppu = self._timeline.pixels_per_unit
        dt = dx / ppu if ppu else 0

        if self._drag_mode == "right":
            new_end = self.snap_time(self._drag_origin_end + dt, self._timeline)
            if self._head:
                # A head handle has no left edge to clamp against (it IS the
                # start of the timeline); both edges follow the cursor so the
                # first shot can grow backwards as well as shrink.
                self._start = self._end = new_end
                self._update_tooltip()
                self.sync()
            elif new_end >= self._start:
                self._end = new_end
                self._update_tooltip()
                self.sync()
        elif self._drag_mode == "left":
            new_start = self.snap_time(self._drag_origin_start + dt, self._timeline)
            if self._tail:
                # A tail handle has no right edge to clamp against -- it IS
                # the end of the timeline.  Clamping it against ``_end``
                # (which equals ``_start`` on a zero-width tail) would let
                # the last shot shrink but never grow.  Drag both edges so
                # the handle simply follows the cursor.
                self._start = self._end = new_start
                self._update_tooltip()
                self.sync()
            elif new_start <= self._end:
                self._start = new_start
                self._update_tooltip()
                self.sync()
        elif self._drag_mode == "move":
            span = self._drag_origin_end - self._drag_origin_start
            new_start = self.snap_time(self._drag_origin_start + dt, self._timeline)
            self._start = new_start
            self._end = new_start + span
            self._update_tooltip()
            self.sync()
        self._update_gap_drag_tooltip(event.scenePos())
        event.accept()

    def _gap_drag_frame(self) -> float:
        if self._drag_mode == "right":
            return float(self._end)
        return float(self._start)

    def _gap_drag_label(self) -> str:
        """``"<verb> <frame>"`` -- what this drag does under the modifiers
        recorded at press, so the gesture reads at the cursor."""
        sq = self._layer.sequencer
        if self._drag_mode == "move":
            verb = "Slide gap"
        elif sq.shift_held_at_press:
            verb = "Retime"
        elif sq.ctrl_held_at_press:
            verb = "Trim"
        elif self._tail or self._head:
            verb = "Resize"  # a shot bound: the bound moves, nothing slides
        else:
            verb = "Slide"
        return f"{verb} {self._sb.FrameTooltip.format_frame(self._gap_drag_frame())}"

    def _show_gap_drag_tooltip(self, scene_pos):
        self._drag_tooltip.show(
            self.scene(),
            scene_pos,
            label=self._gap_drag_label(),
            color=self._line_color.name(),
        )

    def _update_gap_drag_tooltip(self, scene_pos):
        self._drag_tooltip.update(scene_pos, label=self._gap_drag_label())

    def _is_drag_active(self) -> bool:
        return self._drag_mode is not None

    def _restore_drag_state(self) -> None:
        self._start = self._drag_origin_start
        self._end = self._drag_origin_end
        self._sb.CursorManager.pop(self)  # no-op when the grab never armed
        self._drag_mode = None
        self._grab_armed = False
        self._update_tooltip()
        self.sync()

    def mouseReleaseEvent(self, event):
        if self._drag_mode is not None:
            layer = self._layer
            # The controller rebuilds from here, retiring this item while Qt
            # is still inside the release -- safe because the layer removes
            # it through ``SequencerWidget.remove_track_item`` (deferred).
            if self._drag_mode == "right":
                if abs(self._end - self._drag_origin_end) > 0.01:
                    layer.gap_resized.emit(self._drag_origin_end, self._end)
            elif self._drag_mode == "left":
                if abs(self._start - self._drag_origin_start) > 0.01:
                    layer.gap_left_resized.emit(self._drag_origin_start, self._start)
            elif self._drag_mode == "move":
                delta = self._start - self._drag_origin_start
                if abs(delta) > 0.01:
                    layer.gap_moved.emit(
                        self._drag_origin_start,
                        self._drag_origin_end,
                        self._start,
                        self._end,
                    )
            self._sb.CursorManager.pop(self)  # no-op when the grab never armed
            self._drag_mode = None
            self._grab_armed = False
            self._update_tooltip()
            self._drag_tooltip.hide()
        event.accept()

    def contextMenuEvent(self, event):
        menu_utils = self._sb.MenuUtils
        menu = menu_utils.styled_menu()
        act_lock = act_lock_all = act_unlock_all = None
        if not (self._tail or self._head):
            # A head/tail handle exposes no lock actions -- it is a shot-bound
            # handle, not a gap, and a "locked" one would be an inert
            # first/last-shot handle backed by no persistable store state.
            act_lock = menu.addAction("Unlock Gap" if self._locked else "Lock Gap")
            menu.addSeparator()
            act_lock_all = menu.addAction("Lock All Gaps")
            act_unlock_all = menu.addAction("Unlock All Gaps")

        # The controller's own rows (``on_gap_menu``).
        layer = self._layer
        layer.gap_menu_requested.emit(menu, self._start, self._end)
        if not menu.actions():
            return

        chosen = menu.exec_(menu_utils.menu_exec_pos(event))
        if chosen is None or self.scene() is None:
            # Dismissed, or a rebuild retired this overlay while the menu's
            # nested event loop ran -- a None==None match below would
            # otherwise toggle the lock on dismissal of a tail menu.
            return
        if chosen == act_lock:
            self._locked = not self._locked
            self._update_tooltip()
            self.update()
            layer.gap_lock_changed.emit(self._start, self._end, self._locked)
        elif chosen == act_lock_all:
            layer.gap_lock_all_requested.emit()
        elif chosen == act_unlock_all:
            layer.gap_unlock_all_requested.emit()

    def paint(self, painter: QtGui.QPainter, option, widget=None):
        r = self._rect()
        if r.width() < 1:
            return
        patterns = self._sb.PatternRegistry
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.save()
        painter.setClipRect(r)
        painter.fillRect(r, self._color)
        painter.fillRect(
            r,
            patterns.pattern_brush("diagonal", self._line_color, patterns.HATCH_SPARSE),
        )
        # Edge handle highlights
        w = r.width()
        hw = min(self._EDGE_WIDTH, w / 2)
        handle_alpha = self._base_alpha + 80 if self._hovered else self._base_alpha + 50
        handle_color = QtGui.QColor(self._line_color)
        handle_color.setAlpha(min(255, handle_alpha))
        painter.fillRect(QtCore.QRectF(r.left(), r.top(), hw, r.height()), handle_color)
        painter.fillRect(
            QtCore.QRectF(r.right() - hw, r.top(), hw, r.height()), handle_color
        )
        # Draw gap frame count label if wide enough
        if w > 30:
            label = str(self._gap_frames)
            font = painter.font()
            font.setPixelSize(10)
            painter.setFont(font)
            text_color = QtGui.QColor("#dddddd" if self._hovered else "#aaaaaa")
            painter.setPen(text_color)
            painter.drawText(r, QtCore.Qt.AlignCenter, label)
            # Paint lock icon to right of label when locked
            if self._locked and w > 40:
                self._paint_lock_icon(painter, r, text_color)
        painter.restore()

    def _paint_lock_icon(self, painter, rect, fg):
        """Draw a small lock glyph centered above the frame-count label."""
        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        icon_w, icon_h = 8, 10  # body(6) + shackle(4)
        ix = rect.center().x() - icon_w / 2
        iy = rect.center().y() - icon_h - 2  # just above the centered text
        painter.setPen(QtGui.QPen(fg, 1.2))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawArc(QtCore.QRectF(ix + 1, iy, 6, 6), 0 * 16, 180 * 16)
        painter.setBrush(fg)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(QtCore.QRectF(ix, iy + 4, 8, 6))
        painter.restore()


class ShotLayer(QtCore.QObject):
    """The Shot Sequencer's layer on a ``SequencerWidget`` (module docstring).

    Holds the shot lane's blocks and the gap overlays, and answers the
    widget's layer hooks: the lane's painting and grabs, Ctrl+Shift+Click,
    the gesture groups and legend rows, the timeline menu's entries and
    zone, the scroll extent, a re-layout and a clear.

    Parameters:
        sb: The Switchboard the panel's uitk names resolve on.
        sequencer: The ``SequencerWidget`` the layer is added to (and parented
            to, so it lives as long as the widget does).
    """

    #: The layer's name on the widget, and the zone its lane reports
    #: (``zone_context_menu_requested``): the controller's shot-lane menu
    #: keys on it (``ShotLaneMixin.on_zone_context_menu``).
    name = "shot_lane"
    #: The lane's height under the ruler, in pixels.
    lane_height = 12

    gap_resized = QtCore.Signal(float, float)  # (orig next start, new next start)
    gap_left_resized = QtCore.Signal(float, float)  # (orig prev end, new prev end)
    gap_moved = QtCore.Signal(float, float, float, float)  # old start/end, new
    gap_lock_changed = QtCore.Signal(float, float, bool)  # (start, end, locked)
    gap_lock_all_requested = QtCore.Signal()
    gap_unlock_all_requested = QtCore.Signal()
    #: (QMenu, gap_start, gap_end) -- add actions before it opens.
    gap_menu_requested = QtCore.Signal(object, float, float)
    #: (time) -- Ctrl+Shift+Click anywhere on the timeline.
    shot_switch_requested = QtCore.Signal(float)

    #: The shot grammar the legend shows before the widget's groups: a shot's
    #: own bound (its edges, the lane band's edges) never moves the shot's
    #: keys -- a plain drag moves the bound and the neighbouring shots ripple
    #: with their keys to keep the gaps; Ctrl moves the bound and nothing else
    #: (the shot grows into the gap over the keys there, or shrinks and leaves
    #: keys for the next shot); Shift retimes the keys into the new span.  The
    #: band's body moves the shot.  A gap's edge belongs to the shot beyond it:
    #: a plain drag slides that shot.
    SHOT_GESTURES = (
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
    )
    #: ``(group, keys)`` of a track-editor row -> the shot rows that follow it.
    GESTURES_AFTER = {
        ("Clips & keys", "Alt+Drag a scale end"): (
            ("Clips & keys", "Shift+Drag", "Cross shot bounds, bounds stay"),
        ),
        ("Timeline", "Drag"): (
            ("Timeline", "Ctrl+Shift+Click", "Switch to the shot under the cursor"),
        ),
    }
    #: ``(group, keys)`` of a track-editor row -> what it does here.
    GESTURE_WORDING = {
        ("Clips & keys", "Right-click"): "Tangents, lock, Move to Shot",
    }

    def __init__(self, sb, sequencer):
        super().__init__(sequencer)
        self.sb = sb
        self.sequencer = sequencer
        #: ``[{name, start, end, active, id?}, ...]`` -- ``active`` marks the
        #: selected shot; an optional ``id`` is carried through untouched so
        #: the controller gets its own identifier back.
        self._shot_blocks: List[dict] = []
        self._gap_overlays: list = []
        self._show_gap_overlays: bool = True
        #: The range highlight while a bound is dragged from the lane (the
        #: item is not the mouse grabber up there, so the layer drives it).
        self._edge_drag = None
        self._gap_cls = GapOverlay.item_class(sb)

    @classmethod
    def of(cls, sequencer, sb):
        """The shot layer on *sequencer*, added on first use.

        Parameters:
            sequencer: The ``SequencerWidget``.
            sb: The Switchboard, read only when the layer is built.
        """
        try:
            return sequencer.layer(cls.name)
        except KeyError:
            layer = cls(sb, sequencer)
            sequencer.add_layer(layer)
            return layer

    # -- the shot lane's blocks ------------------------------------------------

    def set_shot_blocks(self, blocks: list) -> None:
        """Show one band per shot on the lane.

        Parameters:
            blocks: ``[{"name", "start", "end", "active"}, ...]``; an optional
                ``id`` is carried through untouched, so the controller gets its
                own identifier back from :meth:`selected_shot`.
        """
        self._shot_blocks = list(blocks)
        self._repaint_lane()
        self.sequencer.refresh_extent()

    def clear_shot_blocks(self) -> None:
        """Remove every band from the lane."""
        self._shot_blocks.clear()
        self._repaint_lane()

    def selected_shot(self) -> Optional[dict]:
        """The block marked ``active``, or ``None``.

        The layer does not own shot selection -- the controller does, and says
        so through :meth:`set_shot_blocks` -- but a shortcut or menu acting on
        "the selected shot" needs to read it back without a parallel copy.
        """
        for blk in self._shot_blocks:
            if blk.get("active"):
                return blk
        return None

    def shot_block_at(self, time: float) -> Optional[dict]:
        """The block containing *time*, or ``None``."""
        for blk in self._shot_blocks:
            if blk["start"] <= time <= blk["end"]:
                return blk
        return None

    def _repaint_lane(self) -> None:
        """The lane is painted by the widget's header: ask for a repaint."""
        self.sequencer.timeline.viewport().update()

    # -- the gap overlays ------------------------------------------------------

    def add_gap_overlay(
        self,
        start: float,
        end: float,
        color: str = "#555555",
        alpha: int = 120,
        locked: bool = False,
        tail: bool = False,
        head: bool = False,
    ) -> None:
        """Add a diagonal-hatch overlay for a gap between shots.

        ``tail=True`` places a left-edge-only handle (pass ``start == end``
        at the last shot's end) so the final shot -- which has no following
        shot to form a gap with -- still gets a drag handle; ``head=True``
        is the right-edge-only twin at the first shot's start.  Both report
        through ``gap_left_resized`` / ``gap_resized`` like a gap edge; the
        controller tells them apart by the shot having no neighbour there.
        """
        item = self._gap_cls(
            self, start, end, color, alpha, locked=locked, tail=tail, head=head
        )
        item.setVisible(self._show_gap_overlays)
        self.sequencer.add_track_item(item)
        self._gap_overlays.append(item)
        self.sequencer.refresh_extent()

    def clear_gap_overlays(self) -> None:
        """Remove every gap overlay (deferred-safe: a release may be on the stack)."""
        for item in self._gap_overlays:
            self.sequencer.remove_track_item(item)
        self._gap_overlays.clear()

    def set_all_gap_overlays_locked(self, locked: bool) -> None:
        """Set the locked state on every gap overlay.

        Head/tail handles are exempt: they are shot-bound handles, not gaps,
        and a locked one would leave the first/last shot with no way to
        resize.
        """
        for item in self._gap_overlays:
            if item._tail or item._head:
                continue
            item._locked = locked
            item._update_tooltip()
            item.update()

    @property
    def show_gap_overlays(self) -> bool:
        """Whether the gap overlays show (the timeline menu's Show Gap Overlays)."""
        return self._show_gap_overlays

    @show_gap_overlays.setter
    def show_gap_overlays(self, value: bool) -> None:
        self._show_gap_overlays = value
        for item in self._gap_overlays:
            item.setVisible(value)

    # -- the lane's grabs: the range highlight's, offered up here ----------------

    def _band_zone(self, viewport_pos) -> str:
        """Which of the range highlight's grabs *viewport_pos* is over on the
        lane -- ``"left"``, ``"right"``, ``"move"`` -- or ``""``.

        The one answer both the cursor and the press ask for; asking twice let
        them disagree, which is a wrong cursor sitting over a live handle.
        The band offers all three: the two bounds, and the body -- the ONE
        place the whole shot can be dragged, since the highlight's own body
        passes presses through so the marquee keeps working inside the shot.
        Asked of the setting, not of the item: under another editor the track
        rows' items are hidden, and the lane still owns the grab.
        """
        sq = self.sequencer
        hl = sq.range_highlight_item
        if hl is None or not sq.show_range_highlight:
            return ""
        view = sq.timeline
        if view.hit_zone(viewport_pos.y()) != self.name:
            return ""
        return hl.zone_at(view.mapToScene(viewport_pos).x())

    def _sync_cursor(self, viewport_pos) -> None:
        """Show the resize cursor over a shot bound on the lane: the
        affordance the highlight's own hover gives below the header (up here
        the ruler item is topmost, so the cursor is the view's to set)."""
        zone = self._band_zone(viewport_pos)
        viewport = self.sequencer.timeline.viewport()
        if zone in ("left", "right"):
            viewport.setCursor(QtCore.Qt.SplitHCursor)
        elif zone == "move":
            viewport.setCursor(QtCore.Qt.OpenHandCursor)
        elif viewport.cursor().shape() in (
            QtCore.Qt.SplitHCursor,
            QtCore.Qt.OpenHandCursor,
        ):
            viewport.unsetCursor()

    def _finish_edge_drag(self) -> None:
        hl, self._edge_drag = self._edge_drag, None
        hl.finish_edge_drag()

    # -- the widget's layer hooks (uitk's ``SequencerLayer``) ---------------------

    def paint_lane(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        """Draw one band per shot in the lane's strip.

        Selection has to read at a glance without turning the lane into a
        second timeline, so it is carried by three quiet cues that agree with
        each other: a tinted band, a solid rule along the top of the lane, and
        bright ticks at the shot's two bounds.  Unselected shots get a flat
        dim band and a hairline separator -- enough to show the layout and
        nothing more.
        """
        if not self._shot_blocks:
            return
        tl = self.sequencer.timeline
        top, height = rect.top(), rect.height()
        vis_left, vis_right = rect.left(), rect.right()

        label_font = QtGui.QFont(painter.font())
        label_font.setPointSize(7)
        label_font.setBold(True)
        painter.setFont(label_font)
        metrics = QtGui.QFontMetrics(label_font)

        accent = QtGui.QColor(self.sequencer.SELECTED_ACCENT)
        # NO accent wash on the active band: every band gets the same neutral
        # tint, so the lane shows the LAYOUT and nothing else.  Which shot is
        # selected is said by the accent rule and bound ticks below, which are
        # lines rather than a background -- a second blue box stacked on the
        # range highlight read as one oversized block.
        band_fill = QtGui.QColor("#FFFFFF")
        band_fill.setAlpha(12)
        for blk in sorted(self._shot_blocks, key=lambda b: b["start"]):
            bx0 = tl.time_to_x(blk["start"])
            bx1 = tl.time_to_x(blk["end"])
            if bx1 < vis_left or bx0 > vis_right:
                continue
            is_active = bool(blk.get("active", False))
            band = QtCore.QRectF(bx0, top, max(1.0, bx1 - bx0), height)

            painter.fillRect(band, band_fill)

            painter.setPen(QtCore.Qt.NoPen)
            if is_active:
                # The rule says WHICH lane is selected; the ticks say exactly
                # where it starts and ends -- the band alone blurs at low zoom.
                rule = QtGui.QColor(accent)
                rule.setAlpha(230)
                painter.fillRect(QtCore.QRectF(bx0, top, band.width(), 2.0), rule)
                for x in (bx0, bx1 - 1.0):
                    painter.fillRect(QtCore.QRectF(x, top, 1.0, height), rule)
            else:
                sep = QtGui.QColor("#000000")
                sep.setAlpha(90)
                painter.fillRect(QtCore.QRectF(bx1 - 1.0, top, 1.0, height), sep)

            name = blk.get("name", "")
            if not name:
                continue
            s = round(blk["start"])
            e = round(blk["end"])
            label = f"{name}  {s}-{e}  {e - s}f"
            avail = max(0, int(bx1 - bx0) - 6)
            label = metrics.elidedText(label, QtCore.Qt.ElideRight, avail)
            tc = QtGui.QColor("#FFFFFF" if is_active else "#CCCCCC")
            tc.setAlpha(240 if is_active else 150)
            painter.setPen(tc)
            painter.drawText(QtCore.QPointF(bx0 + 3, rect.bottom() - 3), label)

    def mouse_press(self, event) -> bool:
        """Ctrl+Shift+Click anywhere switches to the shot there; a press on
        the lane over the range highlight's grab drags it.

        A shot bound is DRAWN on the lane, so it is grabbed there too -- and
        only there; the ruler proper scrubs, every row of it.  Driven directly
        rather than by extending the highlight's hit area up here: a
        view-dependent boundingRect re-enters the scene index on scroll and
        dies natively.
        """
        if event.button() != QtCore.Qt.LeftButton:
            return False
        view = self.sequencer.timeline
        mods = event.modifiers()
        if mods & QtCore.Qt.ControlModifier and mods & QtCore.Qt.ShiftModifier:
            t = view.x_to_time(view.mapToScene(event.pos()).x())
            self.shot_switch_requested.emit(t)
            return True
        zone = self._band_zone(event.pos())
        if not zone:
            return False
        # The press's own modifiers decide the grab: move, bound-only, retime.
        self.sequencer.record_press_modifiers(mods)
        hl = self.sequencer.range_highlight_item
        hl.begin_edge_drag(zone, view.mapToScene(event.pos()).x())
        self._edge_drag = hl
        return True

    def mouse_move(self, event) -> bool:
        """A lane drag's move (Alt: about the centre); otherwise the lane's
        cursor, on a hover."""
        if self._edge_drag is not None:
            if event.buttons():
                x = self.sequencer.timeline.mapToScene(event.pos()).x()
                self._edge_drag.update_edge_drag(x, event.modifiers())
                return True
            self._finish_edge_drag()  # its release went elsewhere
        self._sync_cursor(event.pos())
        return False

    def mouse_release(self, event) -> bool:
        """End a lane drag: the highlight emits if a bound moved."""
        if self._edge_drag is None or event.button() != QtCore.Qt.LeftButton:
            return False
        self._finish_edge_drag()
        return True

    def gesture_group_at(self, viewport_pos) -> Optional[str]:
        """``"Shot bounds"`` over the lane's grabs, a cap or the highlight's
        edges; ``"Gaps"`` over a gap; else the widget's."""
        view = self.sequencer.timeline
        zone = view.hit_zone(viewport_pos.y())
        if zone == self.name:
            return "Shot bounds" if self._band_zone(viewport_pos) else None
        if zone != "tracks":
            return None
        item = view.itemAt(viewport_pos)
        if isinstance(item, GapOverlay):
            # A head/tail cap is the first/last shot's own bound.
            return "Shot bounds" if (item._tail or item._head) else "Gaps"
        hl = self.sequencer.range_highlight_item
        if (
            item is not None
            and item is hl
            and hl.zone_at(view.mapToScene(viewport_pos).x()) in ("left", "right")
        ):
            return "Shot bounds"
        return None

    def claims_press(self, scene_pos) -> bool:
        """An unlocked gap's PAINTED rect keeps a press from the range
        highlight's edge.

        Those pixels are drawn as the gap's edge handle, so they must deliver
        gap semantics (no ripple).  Without this, which of two overlapping
        handles answers a plain edge drag -- the highlight's ripples the
        timeline, the gap's does not -- was decided by z-order and ~4px of
        cursor.  A gap of ZERO width is the exception: its strip is drawn
        centred on the seam only so it stays visible, it has no width of its
        own to resize, and on the shot's bound it IS the bound -- yielding to
        it turned a drag of a flush shot's end into a slide of the next shot
        (measured on a production assembly, 2026-10-06).
        """
        return any(
            item.isVisible()
            and not item._locked
            and item._end - item._start > 1e-6
            and item._rect().contains(scene_pos)
            for item in self._gap_overlays
        )

    def legend(self, editor: str, rows: Tuple) -> Tuple:
        """The track editor's legend with the shot grammar: the shot groups
        first, the shot rows in their places, the right-click's wording."""
        if editor != "tracks":
            return rows
        out = list(self.SHOT_GESTURES)
        for group, keys, description in rows:
            out.append(
                (group, keys, self.GESTURE_WORDING.get((group, keys), description))
            )
            out.extend(self.GESTURES_AFTER.get((group, keys), ()))
        return tuple(out)

    def context_entries(self, time: float, entries: list) -> list:
        """The timeline menu: the range overlays are the shots', and the gap
        overlays' toggle follows them."""
        out = [
            dict(entry, label="Show Shot Ranges")
            if entry is not None and entry.get("key") == "range_overlays"
            else entry
            for entry in entries
        ]
        out.append(
            {
                "key": "gap_overlays",
                "label": "Show Gap Overlays",
                "callback": lambda checked: setattr(
                    self, "show_gap_overlays", bool(checked)
                ),
                "checkable": True,
                "checked": bool(self.show_gap_overlays),
            }
        )
        return out

    def menu_zone(self, zone: str, time: float) -> str:
        """A right-click at a time some shot covers is the shot lane's,
        whatever the height -- a shot owns its whole timeline COLUMN, not
        just its band, so "right-click the shot" means the same over the
        tracks as over the band.  The RULER is exempt: it IS the timeline,
        and its own menu has to be reachable somewhere better than "wherever
        no shot happens to be"."""
        if zone == "tracks" and self.shot_block_at(time) is not None:
            return self.name
        return zone

    def time_bounds(self) -> Optional[Tuple[float, float]]:
        """The shots' and gaps' extent: a shot that no longer encloses any
        clip still has to be reachable."""
        spans = [(b["start"], b["end"]) for b in self._shot_blocks]
        spans += [(g._start, g._end) for g in self._gap_overlays]
        if not spans:
            return None
        return min(min(a, b) for a, b in spans), max(max(a, b) for a, b in spans)

    def relayout(self) -> None:
        """Re-derive the gaps' geometry: their height follows the rows."""
        for item in self._gap_overlays:
            item.sync()

    def clear(self) -> None:
        """The widget was cleared: no gaps, no bands."""
        self.clear_gap_overlays()
        self.clear_shot_blocks()
