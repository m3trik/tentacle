# !/usr/bin/python
# coding=utf-8
"""Bevel: chamfer the selected polygon edges, with a live preview.

One Slots class for both hosts. The engine is the host toolkit's ``Bevel``
and the preview its ``Preview``, both reached through ``self.tk``.
"""

from tentacle import Slots


class BevelSlots(Slots):
    # Maya's polyBevel3 rewrites the mesh's edge topology in place: without a
    # geometry snapshot the preview's rollback leaves the bevel baked in, and
    # the captured edge indices shift, so the next refresh bevels other edges.
    # PRESERVE_GEOMETRY makes Maya's Preview snapshot the mesh and restore it on
    # rollback; Blender's Preview snapshots every operated object regardless.
    PRESERVE_GEOMETRY = True

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.bevel

        # Per-field reset buttons (uitk option-box): click resets a field to its
        # default; Alt/Ctrl+click bypasses it to default (greyed, restorable).
        # Must precede connect_multi/Preview — wrapping reparents the widgets and
        # invalidates any already-deferred wrapper (see add_reset_buttons docstring).
        self.sb.add_reset_buttons(self.ui)

        self.preview = self.tk.Preview(
            self,
            self.ui.chk000,
            self.ui.b000,
            message_func=self.sb.message_box,
            undo_message="Bevel",
        )
        self.sb.connect_multi(self.ui, "s000-1", "valueChanged", self.preview.refresh)

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Bevel",
                body="Add chamfer bevels to the selected polygon edges.",
                steps=[
                    "Select one or more polygon edges.",
                    "Set <b>Width</b> and <b>Segments</b> (1+).",
                    "Toggle <b>Preview</b> to iterate non-destructively, "
                    "or press <b>Create</b> to commit.",
                ],
                notes=[
                    "The other bevel options use the <i>Bevel.bevel</i> defaults.",
                ],
            )
        )

    def perform_operation(self, objects, contract=None):
        """Bevel *objects* (Maya's Preview passes its cleanup *contract*)."""
        self.tk.Bevel.bevel(objects, self.ui.s000.value(), self.ui.s001.value())
