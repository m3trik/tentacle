# !/usr/bin/python
# coding=utf-8
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Crease(SlotsBlender):
    """Blender port of the shared ``crease`` menu.

    Maya edge creasing → Blender Subdivision-Surface edge crease (``crease_edge`` attribute), via
    ``blendertk.edit_utils.crease_edges`` (creases selected edges in edit mode, all edges in object
    mode). Maya's per-edge smoothing-angle option doesn't map (Blender crease is a single 0–1 value).
    Crease transfer (Data-Transfer edge data) is deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.crease
        self.submenu = self.sb.loaded_ui.crease_submenu

    def tb000_init(self, widget):
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Amount: ", setObjectName="s003",
            set_limits=[0, 10], setValue=10,
            setToolTip="Crease amount (0 = none, 10 = full) applied to the selected edges.",
        )
        widget.setText(f"Crease {widget.option_box.menu.s003.value()}")
        widget.option_box.menu.s003.valueChanged.connect(
            lambda value: widget.setText(f"Crease {value}")
        )

    @btk.undoable
    def tb000(self, widget):
        """Crease"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Crease requires a selection.")
            return
        btk.crease_edges(objects, amount=widget.option_box.menu.s003.value())

    def b002(self, widget):
        """Transfer Crease Edges — needs a Data-Transfer edge-data setup; not yet ported."""
        self.sb.message_box("Transfer Crease Edges is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
