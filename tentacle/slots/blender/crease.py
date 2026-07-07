# !/usr/bin/python
# coding=utf-8
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Crease(SlotsBlender):
    """Blender port of the shared ``crease`` menu.

    Maya edge creasing → Blender Subdivision-Surface edge crease (``crease_edge`` attribute), via
    ``blendertk.edit_utils.crease_edges`` (creases selected edges in edit mode, all edges in object
    mode). Maya's *Set Smoothing Angle* (``chk000`` + ``s004``) maps to ``polySoftEdge``'s Blender
    equivalent: when enabled, the creased edges are also softened/hardened by the dihedral-angle
    threshold (``crease_edges(angle=)``). Crease transfer rides the native Data-Transfer operator
    (edge ``CREASE``).
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
        widget.option_box.menu.add(
            "QCheckBox", setText="Set Smoothing Angle", setObjectName="chk000",
            setToolTip="Also soften/harden the creased edges by a dihedral-angle threshold "
            "(Blender's equivalent of Maya's polySoftEdge). Enables the Angle field.",
        )
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Angle: ", setObjectName="s004",
            set_limits=[0, 180], setValue=30, setDisabled=True,
            setToolTip="Smoothing angle (degrees): an edge whose dihedral angle exceeds this is "
            "marked sharp/hard, otherwise smooth/soft (0 = all hard, 180 = all soft). Only active "
            "when 'Set Smoothing Angle' is checked.",
        )
        widget.option_box.menu.chk000.toggled.connect(
            widget.option_box.menu.s004.setEnabled
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
        menu = widget.option_box.menu
        angle = menu.s004.value() if menu.chk000.isChecked() else None
        btk.crease_edges(objects, amount=menu.s003.value(), angle=angle)

    @btk.undoable
    def b002(self, widget):
        """Transfer Crease Edges (active mesh → other selected, native Data-Transfer)."""
        self.transfer_from_active("CREASE", edge_mapping="NEAREST")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
