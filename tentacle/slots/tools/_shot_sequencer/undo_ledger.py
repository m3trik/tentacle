# !/usr/bin/python
# coding=utf-8
"""The shot sequencer's undo ledger.

Provides :class:`UndoLedgerMixin` -- mixed into
:class:`~.controller.ShotSequencerController`. Every structural edit records
the shot boundaries before it (``store.scene_edit``); the widget's undo/redo
requests step the host's own undo queue, and the restore points follow only
the steps that were the panel's edits (``SequencerHost.step_undo``).
"""


class UndoLedgerMixin:
    """Shot-boundary restore points, and the panel's Undo / Redo."""

    # Boundary snapshots delegate to the STORE's ledger (pythontk
    # ShotStore.push/restore/redo_boundary_snapshot): scene keyframes ride
    # the host's undo queue but shot bounds live in the store, outside it, and
    # more than one panel mutates them — per-controller stacks desynced
    # from each other and from the queue.  One ledger per store = per
    # scene, so a scene swap isolates it for free.

    def _save_shot_state(self) -> None:
        """Record the current shot boundaries as an UNTAGGED restore point.

        No production path calls this: every shot edit brackets through the
        store's ``scene_edit``, which pushes the restore point BEFORE the
        mutation and tags it with the step it put on the host's undo queue.
        An untagged point reads as "always ours" to the store's
        ``_native_step_crossed`` (the pre-pairing behaviour), so a caller that
        pushes one gives up the pairing.  Prefer ``scene_edit``.
        """
        if self.sequencer is not None:
            self.sequencer.store.push_boundary_snapshot()

    def _restore_shot_state(self) -> None:
        """Apply the most recent restore point (the undo direction).

        Membership is restored symmetrically: a shot ABSENT from the
        snapshot is removed (undoing an insert leaves no phantom), and a
        shot the snapshot names but the store lost is re-created from its
        record (undoing a delete — the keys were never deleted with it).
        """
        if self.sequencer is not None:
            self.sequencer.store.restore_boundary_snapshot()

    def _redo_shot_state(self) -> None:
        """Re-apply the state undo stepped back from (the redo direction).

        Without this, a redo re-applies the scene keys while the bounds
        stay restored — resurrecting the keys-outside-their-shot state.
        """
        if self.sequencer is not None:
            self.sequencer.store.redo_boundary_snapshot()

    # The host's own undo and redo (Ctrl+Z in a viewport, Edit > Undo) are the
    # STORE's to follow -- ``ShotStore.follow_native_step``, which tells an
    # undo of our edit from anybody else's -- with this panel open or not.
    # The panel's Undo / Redo below step the host's queue themselves: how one
    # step splits between the ledger and the queue is the host's
    # (``SequencerHost.step_undo``: Maya plans it up front from the queue's
    # chunk names, Blender lets the store follow what the undo did).

    def on_undo(self) -> None:
        """Handle undo_requested from the widget: one step of the host's undo,
        the shot bounds following only when the step was a shot edit."""
        self._step_host_undo(redo=False)

    def on_redo(self) -> None:
        """Handle redo_requested from the widget (see :meth:`on_undo`)."""
        self._step_host_undo(redo=True)

    def _step_host_undo(self, redo: bool) -> None:
        """Step the host's undo (*redo*: its redo) and redraw once.

        The panel's own redraw hooks are held while the host steps (the
        queue walk, the restore, the native step), so a Ctrl+Z is one
        rebuild -- :meth:`_after_shot_change`, after it.
        """
        store = self.sequencer.store if self.sequencer is not None else None
        self._syncing = True
        try:
            stepped = self.host.step_undo(store, redo=redo)
        except Exception:
            self.logger.debug("%s failed", "redo" if redo else "undo", exc_info=True)
            stepped = True  # whatever it did reached the scene: redraw
        finally:
            self._syncing = False
        if stepped:
            self._after_shot_change()
