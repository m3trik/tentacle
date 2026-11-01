# !/usr/bin/python
# coding=utf-8
"""Marker persistence for the shot sequencer controller.

Provides :class:`MarkerManagerMixin` — mixed into
:class:`~.controller.ShotSequencerController` to persist marker
add/move/change/remove events to the host's ``ShotSequencer`` model.  Host-free:
it reads the widget's markers and writes the engine's marker dicts.
"""

from __future__ import annotations

__all__ = ["MarkerManagerMixin"]


class _MarkerManagerMixinInternal(object):
    """Internal helpers for MarkerManagerMixin."""

    @staticmethod
    def _marker_to_dict(md) -> dict:
        """Serialize a widget marker into the store's marker dict shape.

        A tool's payload (``data``: the Shot Manifest's owner tag) rides
        along, so a marker edit made here never orphans a tool's marker.
        """
        out = {
            "time": md.time,
            "note": md.note,
            "color": md.color,
            "draggable": md.draggable,
            "style": md.style,
            "line_style": md.line_style,
            "opacity": md.opacity,
        }
        if md.data:
            out["data"] = dict(md.data)
        return out


class MarkerManagerMixin(_MarkerManagerMixinInternal):
    """Mixin supplying marker CRUD persistence.

    Expects the host class to provide:

    * ``sequencer`` — the host's ``ShotSequencer`` instance
    * ``_get_sequencer_widget()``
    """

    def on_marker_added(self, marker_id: int, time: float) -> None:
        """Persist a newly added marker."""
        if self.sequencer is None:
            return
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        md = widget.get_marker(marker_id)
        if md is None:
            return
        self.sequencer.markers.append(_MarkerManagerMixinInternal._marker_to_dict(md))
        # Markers are serialized with the store — without marking it
        # dirty the edit is silently dropped on the next save cycle.
        self.sequencer.store.mark_dirty()

    def on_marker_moved(self, marker_id: int, new_time: float) -> None:
        """Update persisted marker time."""
        self._rebuild_markers_store()

    def on_marker_changed(self, marker_id: int) -> None:
        """Update persisted marker note/color."""
        self._rebuild_markers_store()

    def on_marker_removed(self, marker_id: int) -> None:
        """Remove marker from persistent store."""
        self._rebuild_markers_store()

    def _rebuild_markers_store(self) -> None:
        """Rebuild the sequencer's markers list from the widget's markers."""
        if self.sequencer is None:
            return
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        self.sequencer.markers = [
            _MarkerManagerMixinInternal._marker_to_dict(md) for md in widget.markers()
        ]
        self.sequencer.store.mark_dirty()
