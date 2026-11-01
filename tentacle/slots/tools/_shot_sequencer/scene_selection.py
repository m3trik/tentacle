# !/usr/bin/python
# coding=utf-8
"""Tracks and the scene selection.

Provides :class:`SceneSelectionMixin`, mixed into
:class:`~.controller.ShotSequencerController`: hiding, showing and deleting
tracks; mirroring clip, track, channel and key selections onto the scene (the
object selection, the channel scope, the Graph Editor's keys); the track and
header context menus.

Every write to the scene is the host's (``self.host``, the host library's
``SequencerHost``), and every one is a view mirror, never an undo step: this
runs on every click and again on the rebuild after each edit, so a recorded
selection buried the panel's own edits one Ctrl+Z deeper per click.
"""

from qtpy import QtWidgets

import pythontk as ptk


class SceneSelectionMixin:
    """Tracks, and the scene selection that follows the sequencer's."""

    def hide_track(self, track_names) -> None:
        """Hide one or more tracks by name, persist, and rebuild the widget."""
        if self.sequencer is None:
            return
        if isinstance(track_names, str):
            track_names = [track_names]
        for name in track_names:
            self.sequencer.set_object_hidden(self._resolve_full_name(name), True)
        self._sync_to_widget()

    def show_track(self, track_name: str) -> None:
        """Un-hide a track by object name, persist, and rebuild the widget."""
        if self.sequencer is None:
            return
        self.sequencer.set_object_hidden(track_name, False)
        self._sync_to_widget()

    def delete_track(self, track_names) -> None:
        """Permanently remove objects from all shots and rebuild the widget."""
        if self.sequencer is None:
            return
        if isinstance(track_names, str):
            track_names = [track_names]
        for name in track_names:
            self.sequencer.store.remove_object_from_shots(self._resolve_full_name(name))
        self._sync_to_widget()

    def on_selection_changed(self, clip_ids: list) -> None:
        """Select the clicked clips' objects, and their CHANNEL if they name one.

        An open Graph Editor follows that selection; a closed one stays closed
        (:meth:`_select_and_show`).  A sub-row clip means one channel, exactly
        as picking it in the host's channel list does (Maya's Channel Box
        highlight, Blender's fcurve channel selection), and every helper that
        reads that scope narrows with it (:meth:`_mirror_channels`).  An object
        row means the whole object, so it clears the channel scope rather than
        listing the object's channels -- a mixed selection is therefore
        object-scoped.
        """
        if not clip_ids or self._syncing:
            return
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        resolved, labels = [], []
        channel_attrs, whole_object = [], False
        for cid in clip_ids:
            clip = widget.get_clip(cid)
            if clip is None:
                continue
            obj = clip.data.get("obj")
            if not obj:
                continue
            resolved.append(self._resolve_full_name(obj))
            attr_name = clip.data.get("attr_name")
            if attr_name:
                if attr_name not in channel_attrs:
                    channel_attrs.append(attr_name)
            else:
                whole_object = True
            attrs = clip.data.get("attributes") or ([attr_name] if attr_name else [])
            start, end = clip.data.get("orig_start"), clip.data.get("orig_end")
            parts = [obj]
            if attrs:
                parts.append(", ".join(a for a in attrs[:3] if a))
                if len(attrs) > 3:
                    parts[-1] += f" +{len(attrs) - 3}"
            if start is not None and end is not None:
                parts.append(f"{start:.0f}–{end:.0f} ({int(end - start)}f)")
            labels.append(" · ".join(parts))
        self._select_and_show(resolved)
        if channel_attrs or whole_object:  # something addressable was clicked
            self._mirror_channels(resolved, () if whole_object else channel_attrs)
        if labels:
            self._set_footer(
                "  |  ".join(labels[:3])
                + (f"  (+{len(labels) - 3} more)" if len(labels) > 3 else "")
            )

    def on_track_selected(self, track_names: list) -> None:
        """Select the objects whose track labels were clicked in the header.

        A header label names the OBJECT, so the channel scope is cleared:
        whatever attribute scope a previous sub-row click left behind would
        otherwise keep narrowing edits the user has since aimed at the whole
        track.
        """
        if not track_names:
            return
        names = [self._resolve_full_name(n) for n in track_names]
        self._select_and_show(names)
        self._mirror_channels(names)

    def on_sub_track_selected(self, rows: list) -> None:
        """Select a channel when its sub-row label is clicked in the header.

        ``rows`` is ``[(track_name, attr_name), ...]``.  The twin of clicking
        the sub-row's CLIP: the object goes on the scene selection and the
        attributes become the channel scope, so picking channels here scopes
        an edit exactly as picking them in the host's channel list does.
        """
        if not rows:
            return
        objects, attrs = [], []
        for track_name, attr_name in rows:
            full = self._resolve_full_name(track_name)
            if full not in objects:
                objects.append(full)
            if attr_name and attr_name not in attrs:
                attrs.append(attr_name)
        self._select_and_show(objects)
        self._mirror_channels(objects, attrs)
        shown = ", ".join(attrs[:6]) + (f" +{len(attrs) - 6}" if len(attrs) > 6 else "")
        self._set_footer(
            f"{len(attrs)} channel{'s' if len(attrs) != 1 else ''}: {shown}"
        )

    def on_clip_locked(self, clip_id: int, locked: bool) -> None:
        """Persist per-object clip lock and propagate to sibling clips."""
        widget = self._get_sequencer_widget()
        if widget is None or self.sequencer is None:
            return
        clip = widget.get_clip(clip_id)
        if clip is None:
            return
        obj_name = clip.data.get("obj")
        if not obj_name:
            return

        store = self.sequencer.store
        if locked:
            store.locked_objects.add(obj_name)
        else:
            store.locked_objects.discard(obj_name)

        # Propagate to every clip (main + sub-row) for the same object.
        # The originating clip is included -- contextMenuEvent routes
        # through set_clip_locked, and a redundant call is harmless.
        for cd in widget.clips():
            if cd.data.get("obj") == obj_name:
                widget.set_clip_locked(cd.clip_id, locked)
        self._sub_row_cache.clear()

    def on_track_menu(self, menu, track_names) -> None:
        """Add the track actions to the track header's context menu.

        Reveal in Outliner for the tracks whose objects the scene holds, Copy
        Names for every track, and the host's attribute spreadsheet where it
        has one (``SequencerHost.ATTRIBUTE_SPREADSHEET``).
        """
        if not track_names:
            return
        full = [self._resolve_full_name(n) for n in track_names]
        menu.addSeparator()
        resolved = [name for name in full if self.host.object_exists(name)]
        if resolved:
            menu.addAction(
                "Reveal in Outliner",
                lambda objs=list(resolved): self._reveal_in_outliner(objs),
            )
        # Offered for every track, resolved or not -- pasting the name of an
        # object the scene no longer holds is exactly how it gets found again.
        shorts = [self.host.leaf_name(name) for name in full]
        copy_label = (
            f"Copy '{shorts[0]}' to Clipboard"
            if len(shorts) == 1
            else f"Copy {len(shorts)} Names to Clipboard"
        )
        menu.addAction(copy_label, lambda n=list(shorts): self._copy_names(n))
        if self.host.ATTRIBUTE_SPREADSHEET:
            menu.addAction(
                "Attribute Spreadsheet",
                lambda names=list(track_names): self._open_spreadsheet(names),
            )

    def on_header_menu(self, menu) -> None:
        """Add settings actions to the header background context menu (none)."""

    @staticmethod
    def _copy_names(names) -> None:
        """Put the given short names on the clipboard, one per line."""
        QtWidgets.QApplication.clipboard().setText("\n".join(names))

    def _open_spreadsheet(self, track_names) -> None:
        """Select the tracks' objects and open the host's attribute spreadsheet."""
        self._select_and_show([self._resolve_full_name(n) for n in track_names])
        if not self.host.open_attribute_spreadsheet():
            self._set_footer(
                f"The attribute spreadsheet is not available in {self.host.APP}."
            )

    def _select_and_show(self, objects: list) -> None:
        """Select the given objects; the editors that follow it show them.

        Nothing is opened.  An open Graph Editor follows the scene selection
        as the Outliner and the channel list do, so opening one only ever
        changed the user's layout: every clip or header click -- and every
        marquee move that caught a clip -- expanded a collapsed Graph Editor,
        or opened a closed one and moved the panel focus into it.

        Nothing selectable leaves the selection alone: a click on an audio
        clip, an audio header or a missing object's clip must not wipe what
        the user had selected (an audio track's name selects its source
        instead -- ``SequencerHost.mirror_selection``).  Not an undo step.
        """
        if not objects:
            return
        self.host.mirror_selection(list(objects))

    def _mirror_channels(self, objects, attrs=()) -> None:
        """Make *attrs* the channel scope of *objects*; empty clears it.

        The panel's attribute selection and the host's channel selection are
        meant to be one thing -- a sub-row IS a channel -- so a click here
        selects there, and every helper that already reads that scope (Maya's
        Channel Box highlight, Blender's fcurve channel selection) narrows to
        the same channels without being told twice.  The key edits carry
        their own explicit attribute scope rather than reading it back out of
        the UI, so a failed mirror costs the highlight and nothing else.
        """
        self.host.select_channels(
            list(dict.fromkeys(objects or ())), list(dict.fromkeys(attrs or ()))
        )

    def on_key_selection_changed(self, key_groups: list) -> None:
        """Sync the host's Graph Editor key selection to the sequencer's.

        Parameters:
            key_groups: ``[{clip_id, times}, ...]`` -- one entry per clip
                with selected keyframe items.
        """
        if self._syncing:
            # During a rebuild the scene selection empties as items are torn
            # down.  Mirroring that would clear the user's Graph Editor key
            # selection on every refresh.
            return
        self._show_key_selection(key_groups)
        self._mirror_key_selection(key_groups)

    def _show_key_selection(self, key_groups: list) -> None:
        """Put the selected keys on the footer -- how many, their frame range,
        on which channels of which objects
        (``ShotSequencer.describe_key_selection``; 2026-10-10: "footer should
        show key specific info when keys are selected like frame range,
        etc").  An emptied key selection leaves the footer as it is: the clip
        selection that outlives it already wrote it."""
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        rows = []
        for group in key_groups:
            clip = widget.get_clip(group["clip_id"])
            if clip is not None:
                data = clip.data
                rows.append(
                    (data.get("obj") or "", data.get("attr_name"), group["times"])
                )
        text = ptk.ShotSequencer.describe_key_selection(rows)
        if text:
            self._set_footer(text)

    def _mirror_key_selection(self, key_groups: list) -> None:
        """Put *key_groups* on the host's Graph Editor key selection.

        Resolves the widget's clips to ``(obj, attr, times)`` rows and hands
        them to :meth:`_apply_key_selection`; the key menu asserts the same
        selection from its own targets (:meth:`_select_target_keys`).
        Object-level clips name no channel and add nothing.
        """
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        rows = []
        for group in key_groups:
            clip = widget.get_clip(group["clip_id"])
            if clip is None:
                continue
            obj_name = clip.data.get("obj")
            attr_name = clip.data.get("attr_name")
            if not obj_name or not attr_name:
                continue
            rows.append((obj_name, attr_name, group["times"]))
        if rows:
            # Before the keys: selecting an object can clear the host's key
            # selection (Maya's does).
            self._select_key_objects([o for o, _a, _t in rows])
        self._apply_key_selection(rows)
        if rows:
            # The picked keys' channels become the channel scope.  An EMPTIED
            # key selection says nothing about attribute scope -- the clip
            # selection that outlives it already made that call, and clearing
            # here would undo it whenever the two signals cross.
            self._mirror_channels([o for o, _a, _t in rows], [a for _o, a, _t in rows])

    def _select_key_objects(self, objects) -> None:
        """Add the selected keys' *objects* to the object selection.

        The Graph Editor lists the SELECTED objects' curves, so a key whose
        object is not selected is selected where nobody can see it -- open the
        Graph Editor, or expand its collapsed tab, and nothing shows
        (2026-10-07: "can we select keys in the graph editor when they are
        selected in the sequencer without showing the graph editor if its tab
        is currently minimized?").  Nothing is opened or expanded, as
        :meth:`_select_and_show`.  ADDED, not replaced: a wider selection --
        the clips around those keys, or whatever the user picked elsewhere --
        stays.  Not an undo step, as every mirror here.
        """
        names = list(dict.fromkeys(objects))
        if names:
            self.host.select_objects(names, add=True)

    def _select_target_keys(self, targets: list) -> None:
        """Put the key menu's *targets* on the Graph Editor key selection.

        The edits offered there read that selection rather than taking a
        range (``invert_keys``, ``align_selected_keyframes``,
        ``copy_keys(mode="selected")``, a selected-only snap), and the
        reaction that normally keeps it in step is skipped while the panel is
        rebuilding -- so it can be a rebuild out of date by the time a menu
        opens on it.  Asserted from *targets* rather than the raw groups:
        that is already the resolved, writable selection the menu was built
        from.
        """
        self._apply_key_selection([(o, a, t) for o, a, t, _s in targets])

    def _apply_key_selection(self, rows) -> int:
        """Select exactly the ``(obj, attr, times)`` *rows*' keys; the count.

        Every key in the scene is deselected first, so an emptied panel
        selection leaves no keys selected on other objects for the next Graph
        Editor operation to act on.  Not an undo step: a recorded key
        selection pushed one entry per (curve, time) AFTER the edit that
        caused the rebuild, so a group gesture took a Ctrl+Z per key just to
        walk back to its own step (``SequencerHost.select_keys``).
        """
        return self.host.select_keys(rows)

    def _reveal_in_outliner(self, objects) -> None:
        """Select and reveal object(s) in the host's Outliner."""
        self.tk.UiUtils.reveal_in_outliner(list(objects))

    def _resolve_full_name(self, short_name: str) -> str:
        """Map a track's display name back to the object it stands for.

        Handles both regular object tracks and audio tracks (prefixed with
        ``♫ ``).  A name the shots already hold is its own answer (the
        graph outline names objects so, and so does a track whose leaf
        another held object shares -- ``_build_tracks``), before a leaf
        match; a track is labelled by a bare leaf only where no other held
        object shares it, so that match is unique.  Anything else is the
        scene's to answer (``SequencerHost.full_name``: Maya's unique long
        DAG path, an audio track's source node included).
        """
        if short_name.startswith("♫ "):
            short_name = short_name[2:]
        if self.sequencer is not None:
            objects = [obj for shot in self.sequencer.shots for obj in shot.objects]
            if short_name in objects:
                return short_name
            for obj in objects:
                if self.host.leaf_name(obj) == short_name:
                    return obj
        return self.host.full_name(short_name)

    def on_clip_renamed(self, clip_id: int, new_label: str) -> None:
        """Inline rename of a clip: display-only (an object's name owns its
        identity, and clips carry no names of their own)."""
