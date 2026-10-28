# !/usr/bin/python
# coding=utf-8
"""Utilities: one Slots class for both hosts.

Each button runs the host's own version of the utility through the toolkit's
``UiUtils`` (``self.tk``): Measure is the distance tool both hosts register
(``activate_tool``); Annotation and Pencil are each host's native feature, so
they differ by host on purpose (see the methods). The calculator is a shared
panel.
"""

from tentacle import Slots


class UtilitiesSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)

    def b000(self):
        """Measure: activate the distance-measure tool (Maya's Distance Tool,
        Blender's Measure tool)."""
        self.activate_tool("Measure")

    def b001(self):
        """Annotation: the host's own. Maya adds an annotation (a text label,
        prompted for) to the selected object; Blender activates its Annotate tool."""
        try:
            tool = self.tk.UiUtils.annotate()
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))
            return
        if tool:  # a tool was armed: confirm it, the marking menu closed on the click
            self.sb.message_box(f"<hl>{tool}</hl> tool active.")

    def b002(self):
        """Calculator: open the calculator panel."""
        self.sb.handlers.marking_menu.show("calculator")

    def b003(self):
        """Pencil: sketch with the host's pencil, Blue Pencil (Maya) or a new
        Grease Pencil object to draw into (Blender)."""
        try:
            self.tk.UiUtils.open_pencil()
        except RuntimeError as error:
            self.sb.message_box(str(error))
