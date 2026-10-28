# !/usr/bin/python
# coding=utf-8
"""Widget sync: rebuilding the sequencer from the scene.

Provides :class:`WidgetSyncMixin` -- mixed into
:class:`~.controller.ShotSequencerController`. The full rebuild (content,
decoration, viewport), the shotless scene-wide view, tracks, clips, audio
tracks and per-attribute sub-rows, the header settings and attribute colours,
and the display-mode toggles that trigger a rebuild.

Every scene read goes through the host library: its ``SegmentCollector``
(``SequencerHost.segment_collector()``) and its ``SequencerHost`` (the
playhead and playback range, which objects exist, track labels and icons,
motion segments, an object's animated attributes, audio segments, the shot
system's claimed samples).
"""

from collections import Counter, defaultdict
from hashlib import md5
from typing import Optional

import pythontk as ptk


class WidgetSyncMixin:
    """Rebuilding the widget from the scene: tracks, clips, sub-rows, decoration."""

    def _set_view_mode(self, mode: str) -> None:
        """Set the shot display mode and rebuild the widget."""
        self._shot_display_mode = mode
        if self._playback_range_mode != "off":
            self._apply_view_playback_range()
        self._sync_to_widget()

    def _set_playback_range_mode(self, mode: str) -> None:
        """Set the playback-range tracking mode.

        *mode* must be one of ``"off"``, ``"follows_view"``, or
        ``"locked"``.
        """
        self._playback_range_mode = mode
        if mode != "off":
            self._apply_view_playback_range()

    def _set_cmb_mode(self, mode: str) -> None:
        """Switch the combobox between shots and scene markers."""
        self._cmb_mode = mode
        # Keep the mode selector in sync (guard against re-entry)
        cmb_mode = self._cmb_mode_widget
        if cmb_mode is not None:
            idx = 1 if mode == "markers" else 0
            if cmb_mode.currentIndex() != idx:
                cmb_mode.blockSignals(True)
                cmb_mode.setCurrentIndex(idx)
                cmb_mode.blockSignals(False)
        self._sync_combobox()

    def _visible_shots(self, active_shot):
        """Return the shots to render based on ``_shot_display_mode``."""
        if self._shot_display_mode == "current":
            return [active_shot]
        sorted_shots = self.sequencer.sorted_shots()
        if self._shot_display_mode == "all":
            return sorted_shots
        # "adjacent" — previous + current + next
        idx = next(
            (i for i, s in enumerate(sorted_shots) if s.shot_id == active_shot.shot_id),
            None,
        )
        if idx is None:
            return [active_shot]
        result = []
        if idx > 0:
            result.append(sorted_shots[idx - 1])
        result.append(active_shot)
        if idx < len(sorted_shots) - 1:
            result.append(sorted_shots[idx + 1])
        return result

    def _sync_to_widget(
        self, shot_id: Optional[int] = None, *, frame: bool = False
    ) -> None:
        """Full rebuild: content + decoration + viewport.

        When the display mode is ``"adjacent"`` or ``"all"``, clips from
        non-active shots are also rendered (greyed-out, locked) and their
        ranges are shown as non-interactive overlays.

        Parameters:
            shot_id: Shot to display.  Falls back to :attr:`active_shot_id`.
            frame: If True, reframe the viewport on the active shot.
        """
        widget, shot = self._resolve_sync_target(shot_id)
        if widget is None or shot is None:
            # No shots — try scene-wide display
            widget = self._get_sequencer_widget()
            if (
                widget is not None
                and self.sequencer is not None
                and not self.sequencer.shots
            ):
                self._sync_shotless(widget, frame=frame)
            return

        h_scroll, zoom, expanded_names = self._save_viewport_state(widget)
        if self._content_stale:
            # The rows were not built while another editor showed: the
            # expansion to put back is the one they had before.
            expanded_names = expanded_names or set(self._stale_expanded)
        self._stale_expanded = frozenset(expanded_names)
        visible_shots = self._visible_shots(shot)

        # bulk_updates defers the per-add scene-rect recompute (which
        # walks every clip/marker/gap) to one pass at exit — without it
        # a rebuild is O(n²) in clip count.
        bulk = getattr(widget, "bulk_updates", None)
        if callable(bulk):
            with bulk():
                self._rebuild_content(widget, shot, visible_shots)
                self._rebuild_decoration(widget, shot, visible_shots)
        else:
            self._rebuild_content(widget, shot, visible_shots)
            self._rebuild_decoration(widget, shot, visible_shots)
        self._restore_viewport(widget, frame, h_scroll, zoom, expanded_names)
        self._update_footer_shot_summary()

    def _sync_shotless(self, widget, *, frame: bool = False) -> None:
        """Populate the widget with scene-wide animation when no shots exist.

        Discovers animated objects across the full playback range and
        displays them as tracks/clips so the user can inspect animation
        before defining any shots.  Without a scene to ask (no playback
        range) it leaves the widget as it is.
        """
        host = self.host
        rng = host.playback_range()
        if rng is None:
            return
        start, end = rng

        h_scroll, zoom, expanded_names = self._save_viewport_state(widget)
        widget.clear()
        self._sync_header_settings(widget)

        if end <= start:
            self._restore_viewport(widget, frame, h_scroll, zoom, expanded_names)
            self._set_footer("No valid playback range.")
            return

        discovered = self.sequencer._find_keyed_transforms(start, end)
        if not discovered:
            self._restore_viewport(widget, frame, h_scroll, zoom, expanded_names)
            self._set_footer("No animated objects in scene.")
            return

        scene_shot = ptk.ShotBlock(
            shot_id=-1,
            name="Scene",
            start=start,
            end=end,
            objects=sorted(set(discovered)),
        )

        # The synthetic scene_shot (id -1) isn't in the store -- collect its
        # motion segments directly (same pipeline as collect_object_segments).
        segments = host.motion_segments(scene_shot.objects, (start, end))

        segments_by_shot = {scene_shot.shot_id: segments}
        all_objects = set(scene_shot.objects) | {seg["obj"] for seg in segments}

        track_ids = self._build_tracks(
            widget, all_objects, all_objects, active_shot=scene_shot
        )
        self._build_clips(widget, scene_shot, [scene_shot], segments_by_shot, track_ids)
        self._ensure_scene_attr_colors(widget)
        self._build_audio_tracks(widget, scene_shot, [scene_shot])

        current_time = host.current_time()
        widget.set_playhead(start if current_time is None else current_time)
        widget.set_active_range(start, end)

        self._restore_viewport(widget, frame, h_scroll, zoom, expanded_names)
        n = len(scene_shot.objects)
        self._set_footer(
            f"Scene  {start:.0f}–{end:.0f}  ·  {n} object{'s' if n != 1 else ''}"
        )

    def _drop_caches(self) -> None:
        """Forget every cached read of the scene: shot and sub-row segments,
        the audio segments, and the membership reconcile (re-run on the next
        rebuild)."""
        self._segment_cache.clear()
        self._sub_row_cache.clear()
        self._audio_segments_cache = None
        self._reconcile_needed = True

    def refresh(self) -> None:
        """Clear cached segments and rebuild the sequencer widget."""
        self._drop_caches()
        self._sync_to_widget()

    # ---- _sync_to_widget helpers -----------------------------------------

    def _resolve_sync_target(self, shot_id=None):
        """Return ``(widget, shot)`` or ``(None, None)`` if unavailable."""
        widget = self._get_sequencer_widget()
        if widget is None or self.sequencer is None:
            return None, None

        if shot_id is None:
            shot_id = self.active_shot_id
        if shot_id is None:
            return None, None

        shot = self.sequencer.shot_by_id(shot_id)
        if shot is None:
            return None, None
        return widget, shot

    def _save_viewport_state(self, widget):
        """Capture scroll, zoom, and expanded tracks for later restoration."""
        state = widget.viewport_state()
        return state["h_scroll"], state["zoom"], set(state["expanded"])

    def _rebuild_content(self, widget, shot, visible_shots) -> None:
        """Clear widget and rebuild tracks + clips from segments (expensive)."""
        # Suppress store-event → _sync_to_widget re-entrancy for the
        # entire rebuild.  Both reconciliation and auto-discovery may
        # call store.update_shot(); without this guard each call would
        # trigger a nested _sync_to_widget mid-build → duplicate tracks.
        # Restored, not cleared: a caller that rebuilds from inside its own
        # guard would otherwise have it dropped here, halfway through.
        was_syncing = self._syncing
        self._syncing = True
        try:
            widget.clear(keep_range_highlight=True)
            self._sub_row_cache.clear()
            self._sync_header_settings(widget)

            # Re-resolve any stale object paths (e.g. parent renamed) across
            # ALL shots before collecting segments so that global track sets
            # and segment caches never mix old and new paths.  Gated by a
            # dirty flag so pure shot-switches (which can't rename nodes)
            # don't pay the path-resolve cost on every rebuild.
            if self._reconcile_needed:
                if self.sequencer.reconcile_all_shots():
                    self._segment_cache.clear()
                self._reconcile_needed = False

            # The rows are hidden while another editor (the graph) shows:
            # collecting every object's segments for them is the expensive
            # half of a rebuild, so it waits for the switch back
            # (``_on_editor_changed``).
            editor = getattr(widget, "active_editor", None)
            if editor is not None and editor.name != "tracks":
                self._content_stale = True
                return
            self._content_stale = False

            collector = self.host.segment_collector()
            segments_by_shot, all_objects = collector.collect_segments(
                self.sequencer,
                shot,
                visible_shots,
                self._segment_cache,
                self._shifted_out_keys,
                self.logger,
            )

            # When "global" scope is active, expand the object set to include
            # every object across all shots so track positions never shift.
            if self._track_order_scope == "global":
                for s in self.sequencer.sorted_shots():
                    all_objects.update(s.objects)

            active_objects = collector.active_object_set(shot, segments_by_shot)
            track_ids = self._build_tracks(
                widget, all_objects, active_objects, active_shot=shot
            )
            self._build_clips(widget, shot, visible_shots, segments_by_shot, track_ids)
            self._ensure_scene_attr_colors(widget)
            self._build_audio_tracks(widget, shot, visible_shots)
        finally:
            self._syncing = was_syncing

    #: The track rows were skipped by a rebuild while another editor showed.
    _content_stale = False
    #: The rows' expansion as it was before they went stale.
    _stale_expanded = frozenset()

    def _on_editor_changed(self, name: str) -> None:
        """Follow the widget's editor however it was switched -- the view
        button, a host call -- so a rebuild puts back the view on screen, not
        a stale one; and build the rows a rebuild skipped once the track
        editor shows again."""
        if name != "tracks":
            self._view = name
        elif self._view not in ("standard", "compact"):
            widget = self._get_sequencer_widget()
            flat = widget is not None and widget.row_metrics.flat_keys
            self._view = "compact" if flat else "standard"
        if name == "tracks" and self._content_stale and not self._syncing:
            self._sync_to_widget()

    def _rebuild_decoration(self, widget, shot, visible_shots) -> None:
        """Recreate overlays, markers, gap indicators, and active-shot tint."""
        current_time = self.host.current_time()
        widget.set_playhead(shot.start if current_time is None else current_time)
        widget.set_hidden_tracks(sorted(self.sequencer.hidden_objects))
        widget.set_active_range(shot.start, shot.end)
        widget.set_range_highlight(shot.start, shot.end)

        # Populate the shot lane with all shots so the user always sees
        # the full shot structure (including gaps) regardless of display mode.
        all_sorted = self.sequencer.sorted_shots()
        store = self.sequencer.store
        shot_blocks = [
            {
                "id": s.shot_id,
                "name": s.name,
                "start": s.start,
                "end": s.end,
                "active": s.shot_id == shot.shot_id,
            }
            for s in all_sorted
        ]
        widget.set_shot_blocks(shot_blocks)

        for m in self.sequencer.markers:
            widget.add_marker(
                time=m["time"],
                note=m.get("note", ""),
                color=m.get("color"),
                draggable=m.get("draggable", True),
                style=m.get("style", "triangle"),
                line_style=m.get("line_style", "dashed"),
                opacity=m.get("opacity", 1.0),
                data=m.get("data"),
            )

        # Gap overlays between ALL consecutive shots — they serve as
        # interactive handles the user can drag even when gap is zero.
        gap_count = 0
        for i in range(len(all_sorted) - 1):
            left = all_sorted[i]
            right = all_sorted[i + 1]
            gap_start = left.end
            gap_end = right.start
            gap_size = gap_end - gap_start
            if gap_size > -0.5:
                locked = store.is_gap_locked(left.shot_id, right.shot_id)
                widget.add_gap_overlay(gap_start, gap_end, locked=locked)
                gap_count += 1
        # The last shot has no following shot, so the loop above leaves it
        # with no drag handle at its end — the one shot in the timeline that
        # could not be resized like the others.  A zero-width tail overlay
        # supplies that handle; its left edge IS the shot's end, which
        # on_gap_left_resized already knows how to act on.
        if all_sorted:
            widget.add_gap_overlay(all_sorted[-1].end, all_sorted[-1].end, tail=True)
            # ...and the FIRST shot's start, which no gap precedes either.
            widget.add_gap_overlay(all_sorted[0].start, all_sorted[0].start, head=True)
        self.logger.debug(
            "Gap overlays: %d created across %d shots", gap_count, len(all_sorted)
        )

        # Gray tint over inactive shot regions so the active shot
        # stands out visually against the rest of the timeline.
        for s in all_sorted:
            if s.shot_id != shot.shot_id:
                widget.add_range_overlay(s.start, s.end, color="#000000", alpha=40)

    #: Set by the first :meth:`_restore_viewport`; see its docstring.
    _viewport_framed = False

    def _restore_viewport(self, widget, frame, h_scroll, zoom, expanded_names) -> None:
        """Restore scroll/zoom/expansion and trigger geometry recalculation.

        The FIRST restore always frames: there is no prior view to preserve
        on the first build, and the panel opening on frame 0 of a
        several-thousand-frame scene starts every session by hunting for the
        shot being worked on.  (``SequencerWidget.frame_on_first_show`` does
        the same at show time; whichever runs last frames the same range, so
        the two agree however the panel is brought up.)
        """
        frame = frame or not self._viewport_framed
        self._viewport_framed = True
        if frame:
            widget.refresh()
            widget.frame_shot()
        else:
            widget.restore_viewport_state({"zoom": zoom, "h_scroll": h_scroll})

        widget.sub_row_provider = self._provide_sub_rows

        if expanded_names:
            for td in widget.tracks():
                if td.name in expanded_names:
                    widget.expand_track(td.track_id)

    #: The window's views, ``(name, label, icon)`` in the view button's cycle
    #: order.  Standard and Compact are row densities of the track editor
    #: (``uitk.RowMetrics`` presets of the same names); Graph is the graph
    #: editor (``GraphSync`` feeds it).
    VIEWS = (
        ("standard", "Standard", "list"),
        ("compact", "Compact", "menu"),
        ("graph", "Graph", "activity"),
    )
    #: The view showing (:meth:`_set_view`), put back on every rebuild.
    _view = "standard"

    def _set_view(self, view: str) -> None:
        """Show *view* (a name in :attr:`VIEWS`): the view button's verb."""
        self._view = view
        self._apply_view(self._get_sequencer_widget(), view)

    def _apply_view(self, widget, view) -> None:
        """Put *widget* in the named View (an entry of :attr:`VIEWS`).

        A name the widget knows nothing of -- a menu not built yet answers
        with its placeholder -- changes nothing: this runs on every rebuild.
        """
        if widget is None:
            return
        RowMetrics = self.sb.RowMetrics
        if view in RowMetrics.preset_names():
            widget.set_editor("tracks")
            widget.row_metrics = RowMetrics.preset(view)
        elif view in widget.editor_names():
            widget.set_editor(view)

    def _sync_header_settings(self, widget) -> None:
        """Push header spinbox values and attribute colors to the widget."""
        spn_snap = getattr(self.ui, "spn_snap", None)
        if spn_snap is not None:
            widget.snap_interval = float(spn_snap.value())
        # Read on every rebuild so the widget also picks up the value the
        # checkbox restored from settings on load.
        chk_snap_keys = getattr(self.ui, "chk_snap_to_keys", None)
        if chk_snap_keys is not None:
            widget.snap_to_keys = bool(chk_snap_keys.isChecked())
        cmb_overlay = getattr(self.ui, "cmb_shortcut_overlay", None)
        if cmb_overlay is not None:
            # Only a value the widget knows: this runs on EVERY rebuild, and
            # a menu that has not been built yet answers with whatever its
            # placeholder feels like -- which must not take the sync down.
            mode = cmb_overlay.itemData(cmb_overlay.currentIndex())
            if mode in widget.SHORTCUT_OVERLAY_MODES:
                widget.shortcut_overlay_mode = mode

        # QSettings.allKeys() is a disk-backed scan (~4ms each) — cache
        # the resolved color map and only rebuild when the color dialog
        # publishes a new one via btn_colors.
        if self._color_map_cache is None:
            self._color_map_cache = self.sb.AttributeColorDialog.load_color_map(
                ptk.Palette.channels()
            )
        widget.attribute_colors = self._color_map_cache

    # Palette for auto-assigning colors to scene-specific attributes
    # not present in the user's color map (e.g. custom/plugin attrs).
    _AUTO_PALETTE = [
        "#5B8BD4",
        "#6EBF6E",
        "#D4A65B",
        "#C45C5C",
        "#8E6FBF",
        "#5BBFB4",
        "#BF6E8E",
        "#8EB05B",
    ]

    def _ensure_scene_attr_colors(self, widget) -> None:
        """Auto-assign colors to scene attributes missing from the color map.

        Scans all clips for attribute names not yet in
        ``widget.attribute_colors`` and assigns each a deterministic
        color from ``_AUTO_PALETTE`` (hash-based so the same attribute
        always gets the same color).  The widget's live color map is
        updated in-place so that both ``ClipItem._resolve_color`` and
        ``_provide_sub_rows`` see the assignments.
        """
        if widget is None:
            return
        color_map = widget.attribute_colors
        changed = False
        for attr in widget.clip_attributes():
            if attr not in color_map:
                # Deterministic hash — same attribute always maps to
                # the same palette slot (built-in hash() is randomized).
                idx = int(md5(attr.encode()).hexdigest(), 16) % len(self._AUTO_PALETTE)
                color_map[attr] = self._AUTO_PALETTE[idx]
                changed = True
        if changed:
            widget.attribute_colors = color_map

    def _build_tracks(
        self, widget, all_objects, active_objects, active_shot=None
    ) -> dict:
        """Create one track per unique object and return ``{obj_name: track_id}``.

        Non-pinned objects that no longer exist in the scene are silently
        skipped.  Pinned objects (e.g. from a manifest) are kept with a
        'missing' icon so users can see them and re-import.
        """
        host = self.host
        obj_classes = active_shot.classify_objects() if active_shot else {}
        track_ids: dict = {}
        _NOT_FOUND_COLOR = "#E0A0A0"
        if self._track_order_scope == "global":
            ordered = sorted(all_objects)
        else:
            sorted_active = sorted(o for o in all_objects if o in active_objects)
            sorted_inactive = sorted(o for o in all_objects if o not in active_objects)
            ordered = sorted_active + sorted_inactive

        # One batched existence check for every track (scenes with many tracks
        # hit this on every rebuild).  A member is stored as it was given --
        # in Maya often a short name -- and the host resolves each before it
        # answers, so ``ctlA`` is not missing beside ``|ctlA``.
        existing = host.existing(ordered)

        # A track is labelled by its leaf name unless another object the
        # shots hold shares it -- then by its stored name, which
        # ``_resolve_full_name`` matches first -- so every label the header
        # hands back (Hide, Delete Track, ...) resolves to its own object.
        held = {obj for shot in self.sequencer.shots for obj in shot.objects}
        leaf_counts = Counter(host.leaf_name(o) for o in held.union(ordered))

        for obj_name in ordered:
            if self.sequencer.is_object_hidden(obj_name):
                continue
            exists = obj_name in existing
            # Skip missing objects unless they are pinned
            if not exists and not self.sequencer.store.is_object_pinned(obj_name):
                continue
            in_active = obj_name in active_objects
            icon = host.node_icon(obj_name) if exists else None
            if not exists and icon is None:
                icon = self.sb.IconManager.get(
                    "close", size=(16, 16), color=_NOT_FOUND_COLOR
                )
            color_kw: dict = {}
            status = obj_classes.get(obj_name, "valid")
            if status != "valid":
                pair = ptk.SHOT_PALETTE.get(status)
                if pair is not None:
                    fg, bg = pair[0], pair[1]
                    if bg:
                        color_kw["color"] = bg
                    if fg:
                        color_kw["text_color"] = fg
            leaf = host.leaf_name(obj_name)
            tid = widget.add_track(
                obj_name if leaf_counts[leaf] > 1 else leaf,
                icon=icon,
                dimmed=not in_active or not exists,
                italic=not in_active and exists,
                **color_kw,
            )
            track_ids[obj_name] = tid
        return track_ids

    def _build_clips(self, widget, shot, visible_shots, segments_by_shot, track_ids):
        """Add animation and stepped clips for each visible shot."""
        host = self.host
        collector = host.segment_collector()
        seq = self.sequencer
        for vs in visible_shots:
            is_active = vs.shot_id == shot.shot_id
            segs = segments_by_shot.get(vs.shot_id, [])
            obj_classes = vs.classify_objects()

            by_obj: dict = defaultdict(list)
            for seg in segs:
                by_obj[seg["obj"]].append(seg)

            store = seq.store if seq else None

            for obj_name in sorted(set(vs.objects) | set(by_obj)):
                if seq.is_object_hidden(obj_name):
                    continue
                tid = track_ids.get(obj_name)
                if tid is None:
                    continue
                obj_segs = by_obj.get(obj_name, [])
                if not obj_segs:
                    continue

                extra: dict = {}
                if not is_active:
                    extra = {"locked": True, "read_only": True, "dimmed": True}
                elif store and obj_name in store.locked_objects:
                    extra = {"locked": True}
                status = obj_classes.get(obj_name, "valid")
                if status != "valid":
                    pair = ptk.SHOT_PALETTE.get(status)
                    if pair is not None and pair[0]:
                        extra["status_color"] = pair[0]

                # Merge adjacent segments separated only by flat-key
                # gaps so the main track shows fewer, larger clips.
                # Stepped (zero-duration) segments are kept separate — they
                # are point events and must not be absorbed into spans.
                gap = store.detection_threshold if store else 10.0
                span_segs = [sg for sg in obj_segs if not sg.get("is_stepped")]
                stepped_segs = [sg for sg in obj_segs if sg.get("is_stepped")]
                merged = [
                    {
                        "start": cluster[0]["start"],
                        "end": max(sg["end"] for sg in cluster),
                        "segs": cluster,
                    }
                    for cluster in ptk.ShotDetection.cluster_spans(
                        span_segs, gap=gap, inclusive=True
                    )
                ]

                for m in merged:
                    s = m["start"]
                    e = m["end"]
                    attrs = collector.extract_attributes(m["segs"])
                    clip_extra = dict(extra)
                    if is_active and attrs:
                        clip_extra["label_center"] = collector.abbreviate_attrs(attrs)
                    widget.add_clip(
                        track_id=tid,
                        start=s,
                        duration=e - s,
                        label="",
                        shot_id=vs.shot_id,
                        obj=obj_name,
                        orig_start=s,
                        orig_end=e,
                        attributes=attrs,
                        # The object row's ticks drop the shot system's own
                        # claimed samples (the ledger, keyed per host).
                        summary_times=collector.summary_times(
                            m["segs"],
                            lambda crv, o=obj_name: host.claimed_key_times(seq, o, crv),
                        ),
                        **clip_extra,
                    )

                # Stepped (zero-duration) clips, one per point event -- a
                # hold-only member's own marks, or the lone key Move to Shot
                # just brought here, so the row shows where it landed.
                for seg in stepped_segs:
                    t = seg["start"]
                    # Skip stepped keys that fall inside a merged span —
                    # the span clip already covers that time.
                    if any(m["start"] <= t <= m["end"] for m in merged):
                        self.logger.debug(
                            "[SYNC]   stepped key at %s inside span -- skipped",
                            t,
                        )
                        continue
                    widget.add_clip(
                        track_id=tid,
                        start=t,
                        duration=0.0,
                        label="",
                        shot_id=vs.shot_id,
                        obj=obj_name,
                        orig_start=t,
                        orig_end=t,
                        is_stepped=True,
                        stepped_key_time=t,
                        **dict(extra),
                    )

    def _build_audio_tracks(self, widget, shot, visible_shots) -> None:
        """Add audio tracks and clips for visible shots.

        Iterates the host's audio segments (``SequencerHost.audio_segments``:
        Maya's unified audio carrier, Blender's sound strips).  Each canonical
        ``track_id`` becomes one widget track; segments are keyed into the
        sequencer with ``audio_track_id`` for downstream consumers.
        """
        scene_start = min(vs.start for vs in visible_shots)
        scene_end = max(vs.end for vs in visible_shots)
        # Audio discovery is a heavy scene read (~28ms per rebuild on a busy
        # Maya carrier).  Segments only change on audio edits, not on
        # shot-switches — cache by range.
        cache_key = (scene_start, scene_end)
        cached = self._audio_segments_cache
        if cached is not None and cached[0] == cache_key:
            segs = cached[1]
        else:
            try:
                segs = self.host.audio_segments(scene_start, scene_end)
            except Exception:
                # Surfaced, not swallowed -- a silently missing audio track
                # reads as "no audio" -- but never the end of the rebuild.
                self.logger.warning("audio segment collection failed", exc_info=True)
                segs = []
            self._audio_segments_cache = (cache_key, segs)

        # Group by canonical track_id.
        by_track: dict = defaultdict(list)
        for seg in segs:
            by_track[seg.track_id].append(seg)

        for track_id, track_segs in by_track.items():
            if self.sequencer.is_object_hidden(track_id):
                continue

            # Pre-compute visible clip descriptors; skip the track
            # entirely if no segment strictly overlaps any visible shot.
            clip_descs: list = []
            for seg in track_segs:
                for vs in visible_shots:
                    vis_start = max(seg.start, vs.start)
                    vis_end = min(seg.end, vs.end)
                    if vis_end <= vis_start:
                        continue
                    clip_descs.append((seg, vs, vis_start, vis_end))

            if not clip_descs:
                continue

            icon = self.host.audio_track_icon(track_id)
            widget_track_id = widget.add_track(track_id, icon=icon)

            for seg, vs, vis_start, vis_end in clip_descs:
                is_active = vs.shot_id == shot.shot_id

                full_waveform = seg.waveform or []
                full_dur = seg.end - seg.start
                if full_waveform and full_dur > 0:
                    n = len(full_waveform)
                    frac_lo = (vis_start - seg.start) / full_dur
                    frac_hi = (vis_end - seg.start) / full_dur
                    i_lo = int(frac_lo * n)
                    i_hi = max(i_lo + 1, int(frac_hi * n))
                    vis_waveform = full_waveform[i_lo:i_hi]
                else:
                    vis_waveform = full_waveform

                extra: dict = {}
                if not is_active:
                    extra = {"locked": True, "read_only": True, "dimmed": True}

                widget.add_clip(
                    track_id=widget_track_id,
                    start=vis_start,
                    duration=vis_end - vis_start,
                    label=seg.label or track_id,
                    color="#3A7D44",
                    is_audio=True,
                    audio_track_id=seg.track_id,
                    file_path=seg.file_path,
                    waveform=vis_waveform,
                    orig_start=seg.start,
                    orig_end=seg.end,
                    vis_start=vis_start,  # a drag reports where THIS landed
                    shot_id=vs.shot_id,
                    **extra,
                )

    def _on_frame_on_shot_change_toggled(self, checked: bool) -> None:
        if self.sequencer is None:
            return
        self.sequencer.store.frame_on_shot_change = checked
        self.sequencer.store.mark_dirty()

    def _on_select_on_load_toggled(self, checked: bool) -> None:
        if self.sequencer is None:
            return
        self.sequencer.store.select_on_load = checked
        self.sequencer.store.mark_dirty()
        # A cross-scene preference: saved by the panel that changes it (a
        # store save no longer writes the prefs file).
        self.sequencer.store._save_user_prefs()

    def _set_show_internal_holds(self, enabled: bool) -> None:
        """Toggle flat-key span visibility in attribute sub-rows."""
        self._show_internal_holds = enabled
        self._sub_row_cache.clear()
        self._sync_to_widget()

    def _provide_sub_rows(self, track_id, track_name):
        """Return per-attribute sub-row data for a track.

        Called by the widget's ``sub_row_provider`` protocol when a user
        double-clicks a header label to expand a track.

        Uses the same motion-segment pipeline as the object row
        (``SequencerHost.motion_segments``) so that hold absorption,
        hold-only synthesis, and motion detection are consistent between
        both views.  Every keyed channel gets a row -- custom properties and
        visibility too -- and each a full-range background curve preview.

        Returns:
            ``[(attr_name, [(start, dur, label, color, extra), ...]), ...]``
            where *extra* is a dict of kwargs passed through to ``add_clip``.
        """
        if self.sequencer is None:
            return []

        shot_id = self.active_shot_id
        if shot_id is None:
            return []
        shot = self.sequencer.shot_by_id(shot_id)
        if shot is None:
            return []

        obj_name = self._resolve_full_name(track_name)

        # Return cached result if available
        cache_key = (shot_id, track_name)
        cached = self._sub_row_cache.get(cache_key)
        if cached is not None:
            return cached

        host = self.host
        # The object's scene name (Maya: the long DAG path, so an ambiguous
        # short name never errors) and its animated attributes, each mapped
        # to its first curve -- the names drive the per-attribute iteration
        # below, the curves feed the full-range background previews.
        resolved, attr_to_curve = host.attribute_curves(obj_name)
        if resolved is None or not attr_to_curve:
            return []
        obj_name = resolved

        collector = host.segment_collector()
        widget = self._get_sequencer_widget()
        color_map = widget.attribute_colors if widget else {}
        show_holds = self._show_internal_holds

        store = self.sequencer.store if self.sequencer else None
        is_obj_locked = bool(store and obj_name in store.locked_objects)

        # Determine the visible time range for the full-range curve based
        # on the current display mode.
        visible = self._visible_shots(shot)
        curve_range_start = min(s.start for s in visible)
        curve_range_end = max(s.end for s in visible)

        result = []
        for attr_name in sorted(attr_to_curve):
            # Reuse the same pipeline as the object row, filtered to just
            # this attribute's curves.
            segs = host.motion_segments(
                [obj_name],
                (shot.start, shot.end),
                attributes=[attr_name],
                ignore_holds=not show_holds,
            )

            if not segs:
                continue

            # Determine which segments are pure holds by comparing
            # against active-only results.  A segment is a pure hold
            # only when it has zero overlap with any active span.
            # Motion-extended segments (motion + trailing hold) keep
            # normal styling since they contain real motion.
            hold_ranges: set = set()
            if show_holds:
                active_segs = host.motion_segments(
                    [obj_name],
                    (shot.start, shot.end),
                    attributes=[attr_name],
                    ignore_holds=True,
                )
                active_spans = [(a["start"], a["end"]) for a in active_segs]
                for seg in segs:
                    ss, se = seg["start"], seg["end"]
                    # Pure hold: no overlap with any active span
                    if not any(a_s < se and a_e > ss for a_s, a_e in active_spans):
                        hold_ranges.add((ss, se))

            color = color_map.get(attr_name)
            segments = []
            for seg in segs:
                s, e = seg["start"], seg["end"]

                # Build curve preview from the segment's own curves.  The
                # shot system's claimed bound samples shape the curve but get
                # no dot: they are not the animator's keys, and drawn they
                # were "auto generated border keys" on every bound (2026-10-06).
                preview = None
                for crv in seg.get("curves", []):
                    preview = collector.build_curve_preview(
                        crv,
                        s,
                        e,
                        hidden_times=host.claimed_key_times(
                            self.sequencer, obj_name, crv
                        ),
                    )
                    if preview:
                        break
                # A zero-length segment is a point event, as on the object row
                # (``is_stepped``); ``attributes`` names the row's one channel
                # the way an object-row clip names its several.
                extra = {
                    "obj": obj_name,
                    "attr_name": attr_name,
                    "shot_id": shot_id,
                    "orig_start": s,
                    "orig_end": e,
                    "is_stepped": abs(e - s) < 1e-6,
                    "attributes": [attr_name],
                }
                if preview:
                    extra["curve_preview"] = preview
                if (s, e) in hold_ranges:
                    extra["is_hold"] = True
                if is_obj_locked:
                    extra["locked"] = True
                segments.append((s, max(e - s, 0.0), attr_name, color, extra))
            result.append((attr_name, segments))

        # Push full-range background curve previews to the widget for each
        # attribute sub-row.  These are static reference lines painted in
        # drawBackground — no interaction, no updates during drag.
        if widget is not None:
            for attr_name, _ in result:
                crv = attr_to_curve.get(attr_name)
                if crv is None:
                    continue
                bg_preview = collector.build_curve_preview(
                    crv, curve_range_start, curve_range_end
                )
                hex_color = color_map.get(attr_name, "#CCCCCC")
                widget.set_bg_curve_preview(
                    track_id, attr_name, bg_preview, color=hex_color or "#CCCCCC"
                )

        self._sub_row_cache[cache_key] = result
        return result
