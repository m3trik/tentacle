# !/usr/bin/python
# coding=utf-8
"""Duplicate Grid: copies of the selection in a 3D grid.

One Slots class for both hosts. The engine is the host toolkit's
``DuplicateGrid`` and the preview its ``Preview``, both reached through
``self.tk``.
"""

from tentacle import Slots


class DuplicateGridSlots(Slots):
    # Defensive backstop, in parity with DuplicateLinear/Radial. duplicate_grid
    # neither deletes nor mutates the source, so the rollback already restores
    # cleanly; MUTATES_SELECTION=True keeps Maya's Preview duplicate+hide
    # UUID-restore backstop anyway, as cheap insurance against the source being
    # touched on the (headlessly-untestable) interactive path. Blender's Preview
    # snapshots every operated object regardless.
    MUTATES_SELECTION = True

    # Total duplicates above which we ask the user to confirm before building
    # (a grid grows cubically, unlike the linear and radial counts).
    BULK_THRESHOLD = 1000

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.duplicate_grid

        # Largest grid count the user has approved this session (so a confirmed
        # bulk build doesn't re-prompt on every preview refresh).
        self._confirmed_count = 0

        # Per-field reset buttons (uitk option-box): click resets a field to its
        # default; Alt/Ctrl+click bypasses it to default (greyed, restorable).
        # Must precede connect_multi/Preview — wrapping reparents the widgets and
        # invalidates any already-deferred wrapper (see add_reset_buttons docstring).
        self.sb.add_reset_buttons(self.ui)

        # Per-axis Spacing X/Y/Z (s003-5) each get a lock toggle: locking two or
        # more links them so a change to one shifts the others by the same delta.
        # Same wrap-before-defer ordering constraint as add_reset_buttons.
        self.sb.link_spinboxes(self.ui, "s003-5")

        self.preview = self.tk.Preview(
            self,
            self.ui.chk000,
            self.ui.b000,
            message_func=self.sb.message_box,
            undo_message="Duplicate Grid",
        )
        # s000-2 are the X/Y/Z counts, s003-5 the per-axis spacing.
        self.sb.connect_multi(self.ui, "s000-5", "valueChanged", self.preview.refresh)

        # Output mode: how the copies are produced; combine yields one mesh, the
        # others a group.
        self.ui.cmb000.add(
            [
                ("Combine", "combine"),
                ("Instance", "instance"),
                ("Unique", "copy"),
            ],
            prefix="Output:",
        )
        self.ui.cmb000.setAsCurrent("instance")
        self.ui.cmb000.currentIndexChanged.connect(self.preview.refresh)

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Duplicate Grid",
                body="Duplicate selected objects into a 3D grid layout.",
                steps=[
                    "Select one or more objects.",
                    "Set per-axis counts <b>Dimensions X/Y/Z</b> (minimum 1) and "
                    "the per-axis <b>Spacing X/Y/Z</b> gap added between copies.",
                    "Each field has a reset button; each spacing field also has a "
                    "<b>lock</b> — lock two or more to move them together by the "
                    "same amount. Resetting a field clears its lock.",
                    "Toggle <b>Preview</b> to iterate, or press <b>Create</b> "
                    "to commit.",
                ],
                sections=[
                    (
                        "Output",
                        [
                            "<b>Combine</b> — merge every copy into a single mesh.",
                            "<b>Instance</b> — copies that share one mesh (cheaper; "
                            "editing any copy updates the rest), grouped.",
                            "<b>Unique</b> — independent copies, grouped.",
                        ],
                    ),
                ],
                notes=[
                    "Spacing may be negative to overlap copies. Very large grids "
                    "prompt for confirmation first.",
                ],
            )
        )

    def b001_init(self, widget):
        """Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
        current values as the defaults, Ctrl+Shift+Click forgets them). Any reset
        re-arms the large-grid confirmation."""
        ResetGesture = self.sb.ResetGesture

        self._reset_gesture = ResetGesture(
            widget, on_performed=lambda _action: setattr(self, "_confirmed_count", 0)
        )

    def perform_operation(self, objects, contract=None):
        """Lay *objects* out in the grid (Maya's Preview passes its cleanup
        *contract*)."""
        dimensions = (self.ui.s000.value(), self.ui.s001.value(), self.ui.s002.value())
        # Per-axis spacing: Spacing X / Y / Z (s003 / s004 / s005).
        spacing = (self.ui.s003.value(), self.ui.s004.value(), self.ui.s005.value())
        if not self._confirm_bulk(dimensions, objects):
            self.copies = []
            return
        self.copies = self.tk.DuplicateGrid.duplicate_grid(
            objects,
            dimensions=dimensions,
            spacing=spacing,
            mode=self.ui.cmb000.currentData(),
        )

    def _confirm_bulk(self, dimensions, objects) -> bool:
        """Gate large builds behind a confirmation dialog.

        Returns True to proceed. The approved magnitude is cached so a confirmed
        bulk build doesn't re-prompt on every preview refresh; on decline during
        a live preview the preview is switched off so dragging the count up
        doesn't re-prompt on every tick -- deferred to the event loop, since
        we're inside a refresh and Maya's ``disable`` no-ops there.
        """
        x, y, z = dimensions
        total = abs(x) * abs(y) * abs(z) * max(len(objects), 1)
        if total <= self.BULK_THRESHOLD or total <= self._confirmed_count:
            return True

        proceed = (
            self.sb.message_box(
                f"This will create <b>{total:,}</b> objects, which may be slow.<br>"
                "Continue?",
                "Yes",
                "No",
            )
            == "Yes"
        )
        if proceed:
            self._confirmed_count = total
            return True

        if self.preview.is_enabled:
            from qtpy import QtCore

            QtCore.QTimer.singleShot(0, self.preview.disable)
        return False
