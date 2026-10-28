# !/usr/bin/python
# coding=utf-8
"""Dynamic Pipe: a pipe mesh that follows a chain of handles live.

One Slots class for both hosts over the host toolkit's ``DynamicPipe``
(``self.tk``): Maya lofts NURBS circles parented to locators, Blender sweeps a
beveled curve hooked to Empties.
"""

from tentacle import Slots


class DynamicPipeSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.dynamic_pipe
        self.pipe = None

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Dynamic Pipe",
                body="Build a pipe-style mesh through a chain of handles: each "
                "handle drives one cross-section, and moving a handle in the "
                "viewport reshapes the pipe live.",
                steps=[
                    "Place handles along the desired path: locators in Maya, "
                    "Empties in Blender.",
                    "Select them in path order (Maya follows the selection order; "
                    "Blender, which keeps none, follows their <b>names</b>: "
                    "handle_01, handle_02, ...).",
                    "Press <b>Initialize Pipe</b>.",
                ],
                notes=["Requires at least two handles."],
            )
        )

    def b000(self):
        """Initialize Pipe: build the pipe through the selected handles."""
        try:
            self.pipe = self.tk.DynamicPipe.from_selection()
        except ValueError as exc:
            self.sb.message_box(f"{exc} Then press Initialize Pipe.")
