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
    """The panel's Undo / Redo over the shot-boundary restore points."""

    # The restore points are the STORE's ledger (pythontk ShotStore): scene
    # keyframes ride the host's undo queue but shot bounds live in the store,
    # outside it, and more than one panel mutates them -- per-controller
    # stacks desynced from each other and from the queue.  One ledger per
    # store = per scene, so a scene swap isolates it for free; every shot edit
    # records its point through the store's ``scene_edit``.

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
