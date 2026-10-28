# !/usr/bin/python
# coding=utf-8
"""Key Stash: park keys out of the working animation as clips, then preview or
retrieve them.

One Slots class for both hosts over the host toolkit's ``KeyStash`` store
(``self.tk``), which also reads each Store source the way its host keeps it
(Maya: the Graph Editor key selection, the time slider's drag-selected range,
the playback range; Blender: the selected keys, the preview range, the scene
frame range) and selects a clip's objects. A thin driver: each control resolves
the active store and calls one method on it, and the clip list repaints from
the store's change events, so a stash made from the Shot Sequencer's clip menu
shows up here without any wiring between the two panels.
"""

from typing import Optional

import pythontk as ptk

from tentacle import Slots


class KeyStashSlots(Slots, ptk.LoggingMixin):
    #: Store Keys' sources, in the Source combo's order (it saves its index):
    #: ``(label, source)``, each source one of ``KeyStash.STASH_SOURCES``.
    SOURCES = (
        ("Selected Keys", "selected_keys"),
        ("Timeline Selection", "timeline_selection"),
        ("Playback Range", "playback_range"),
    )
    #: Where Retrieve puts a clip back, in the Retrieve At combo's order.
    RETRIEVE_AT = ("Original Frames", "Current Time")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("WARNING")
        self.logger.set_log_prefix("[Key Stash] ")
        self.ui = self.sb.loaded_ui.key_stash
        self._bound_store = None
        self._initialized = False
        # Deferred: child widgets aren't wired onto self.ui until
        # register_children runs after __init__ returns.
        self.sb.QtCore.QTimer.singleShot(0, self._initialize_ui)

    # ---- setup -----------------------------------------------------------

    def header_init(self, widget) -> None:
        """Configure header buttons, the refresh action and the help text."""
        widget.config_buttons("refresh", "collapse", "pin")
        widget.refresh_requested.connect(self.refresh_from_scene)
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Key Stash",
                body="Park keys out of the working animation and bring them "
                "back later. A stored clip is inert: it does not evaluate, "
                "export or bake, and it survives save and reopen.",
                steps=[
                    "Pick a <b>Source</b>: the selected keys, the <b>Timeline "
                    "Selection</b> (Maya: a drag-selected time slider range; "
                    "Blender: the preview range) or the <b>Playback Range</b> "
                    "(Blender: the scene frame range). The last two act on the "
                    "selected objects.",
                    "Click <b>Store Keys</b>. The keys leave a plain gap; the "
                    "neighbours interpolate across it.",
                    "Select a clip in the list. <b>Preview</b> plays it on its "
                    "objects through a temporary override, without retrieving "
                    "it; <b>In Context</b> keeps the scene animation outside "
                    "the clip's range.",
                    "<b>Retrieve</b> puts the keys back (on their original "
                    "frames, or starting at the current time) and forgets the "
                    "clip. <b>Drop</b> deletes them for good.",
                ],
                notes=[
                    "Double-click a clip to select its objects.",
                    "Refresh (header) re-reads the scene: clips whose stored "
                    "keys were deleted or undone away are pruned.",
                ],
            )
        )

    def _initialize_ui(self) -> None:
        """Populate the combos and bind the store (deferred from __init__)."""
        if self._initialized:
            return
        self._initialized = True
        self.ui.cmb000.add(list(self.SOURCES))
        self.ui.cmb000.current_text_prefix = "Source:  "
        self.ui.cmb001.add(list(self.RETRIEVE_AT))
        self.ui.cmb001.current_text_prefix = "Retrieve At:  "
        tree = self.ui.tree000
        tree.itemSelectionChanged.connect(self._sync_buttons)
        tree.itemDoubleClicked.connect(self._select_clip_objects)
        stash = self.tk.KeyStash
        stash.add_invalidation_listener(self._on_store_invalidated)
        # The operations write the record inside their undo steps, so an undo
        # or redo can move it under the store: the host re-reads it then, and
        # the store's change event repaints this panel (ended with the panel).
        stash.watch_undo(owner=self, widget=self.ui)
        self.refresh()

    @property
    def store(self):
        """The host's active store, (re)bound to this panel's change listener."""
        store = self.tk.KeyStash.active()
        if store is not self._bound_store:
            if self._bound_store is not None:
                self._bound_store.remove_listener(self._on_store_changed)
            store.add_listener(self._on_store_changed)
            self._bound_store = store
        return store

    def _on_store_invalidated(self, _event) -> None:
        self._bound_store = None
        self.refresh()

    def _on_store_changed(self, _event) -> None:
        self.refresh()

    # ---- view ------------------------------------------------------------

    def refresh(self) -> None:
        """Repaint the clip list from the store."""
        from qtpy import QtCore, QtWidgets

        store = self.store
        tree = self.ui.tree000
        selected = self._selected_clip_id()
        tree.clear()
        for clip in store.clips:
            label = clip.label
            if store.is_previewing(clip.clip_id):
                label += "  (previewing)"
            # Each object's leaf: Maya records long DAG paths, Blender's names
            # are flat (the split is the DCC-agnostic leaf ptk's shots use).
            objects = ", ".join(o.rsplit("|", 1)[-1] for o in clip.objects)
            span = ""
            if clip.start is not None:
                span = (
                    f"{clip.start:g}"
                    if clip.start == clip.end
                    else f"{clip.start:g} - {clip.end:g}"
                )
            stored = clip.created.replace("T", " ")[:16]
            item = QtWidgets.QTreeWidgetItem([label, objects, span, stored])
            item.setData(0, QtCore.Qt.UserRole, clip.clip_id)
            item.setToolTip(0, f"{clip.key_count} keys on {len(clip.curves)} curves")
            item.setToolTip(1, "\n".join(clip.objects))
            tree.addTopLevelItem(item)
            if clip.clip_id == selected:
                item.setSelected(True)
        for col in range(tree.columnCount()):
            tree.resizeColumnToContents(col)
        count = len(store.clips)
        plural = "" if count == 1 else "s"
        self.ui.footer.setDefaultStatusText(
            f"{count} stored clip{plural}" if count else "No stored clips"
        )
        self._sync_buttons()

    def refresh_from_scene(self) -> None:
        """Header refresh: prune clips whose stored keys are gone, then repaint."""
        gone = self.store.reconcile()
        self.refresh()
        if gone:
            self._footer(
                f"Pruned {len(gone)} clip(s) whose keys are gone from the scene.",
                "warning",
            )
        else:
            self._footer("Clip list is in sync with the scene.")

    def _selected_clip_id(self) -> Optional[int]:
        from qtpy import QtCore

        items = self.ui.tree000.selectedItems()
        if not items:
            return None
        return items[0].data(0, QtCore.Qt.UserRole)

    def _sync_buttons(self) -> None:
        clip_id = self._selected_clip_id()
        has_clip = clip_id is not None
        store = self._bound_store
        previewing = store is not None and store.is_previewing()
        self.ui.b001.setEnabled(has_clip)
        self.ui.b003.setEnabled(has_clip)
        self.ui.chk001.setEnabled(has_clip or previewing)
        # In Context is read when a preview starts; a running one won't re-read it.
        self.ui.chk000.setEnabled(not previewing)
        self._set_checked_silently(self.ui.chk001, previewing)

    @staticmethod
    def _set_checked_silently(widget, checked: bool) -> None:
        widget.blockSignals(True)
        try:
            widget.setChecked(checked)
        finally:
            widget.blockSignals(False)

    def _footer(self, msg: str, level: str = "info") -> None:
        self.ui.footer.setText(msg, level=level)
        getattr(self.logger, level if level != "success" else "info")(msg)

    def _select_clip_objects(self, item, _column: int = 0) -> None:
        """Double-click on a clip: select the clip's objects that still exist."""
        from qtpy import QtCore

        store = self.store
        clip = store.get_clip(item.data(0, QtCore.Qt.UserRole))
        if clip is None:
            return
        present = store.select_clip_objects(clip.clip_id)
        if not present:
            self._footer("None of the clip's objects exist in the scene.", "warning")
            return
        self._footer(f"Selected {len(present)} object(s) of '{clip.label}'.")

    # ---- slots -----------------------------------------------------------

    def b000(self) -> None:
        """Store Keys"""
        try:
            # A source the scene can't answer yet (nothing selected, no range
            # marked) is refused with what to do, as a ValueError.
            clip = self.store.stash_from(self.ui.cmb000.currentData())
        except ValueError as exc:
            self._footer(str(exc), "warning")
            return
        except RuntimeError as exc:
            self._footer(f"Store failed: {exc}".rstrip(), "error")
            return
        if clip is None:
            self._footer("No keys found to store.", "warning")
            return
        self._footer(f"Stored {clip.key_count} keys as '{clip.label}'.", "success")

    def b001(self) -> None:
        """Retrieve"""
        clip_id = self._selected_clip_id()
        if clip_id is None:
            self._footer("Select a stored clip to retrieve.", "warning")
            return
        at = None
        if self.ui.cmb001.currentText() == "Current Time":
            at = self.tk.AnimUtils.get_current_frame()
        try:
            restored = self.store.retrieve(clip_id, at=at)
        except RuntimeError as exc:
            # A scene-side refusal (locked or referenced target, a paste with
            # nowhere to land) must reach the panel, not only the log.
            self._footer(f"Retrieve failed: {exc}".rstrip(), "error")
            return
        if restored:
            self._footer(f"Retrieved {restored} keys.", "success")
        else:
            self._footer(
                "Nothing retrieved — the clip's objects are gone (the log says which).",
                "warning",
            )

    def chk001(self, checked: bool) -> None:
        """Preview (toggle)"""
        store = self.store
        if not checked:
            if store.end_preview():
                self._footer("Preview ended.")
            return
        clip_id = self._selected_clip_id()
        if clip_id is None:
            self._set_checked_silently(self.ui.chk001, False)
            self._footer("Select a stored clip to preview.", "warning")
            return
        try:
            store.preview(clip_id, in_context=self.ui.chk000.isChecked())
        except (KeyError, ValueError, RuntimeError) as exc:
            self._set_checked_silently(self.ui.chk001, False)
            self._footer(str(exc), "error")
            return
        self._footer("Previewing — scrub the range; uncheck Preview to end.")

    def b003(self) -> None:
        """Drop"""
        clip_id = self._selected_clip_id()
        if clip_id is None:
            self._footer("Select a stored clip to drop.", "warning")
            return
        clip = self.store.get_clip(clip_id)
        if clip is None:
            self.refresh()
            return
        answer = self.sb.message_box(
            f"Delete <b>{clip.label}</b> ({clip.key_count} keys) for good?",
            "Yes",
            "No",
        )
        if answer != "Yes":
            return
        self.store.drop(clip_id)
        self._footer(f"Dropped '{clip.label}'.")
