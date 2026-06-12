# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Normals(SlotsBlender):
    """Blender port of the shared ``normals`` menu.

    Backed by ``blendertk.edit_utils`` normal/shading helpers (bmesh): soften/harden (smooth vs
    flat shading), set-by-angle (mark sharp edges → Blender split normals follow them), flip, and
    recalculate; normal transfer rides the native Data-Transfer operator. Per-vertex normal
    locking (Maya-specific) stays deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    # ------------------------------------------------------------------ tb001  Set Normals By Angle
    def tb001_init(self, widget):
        widget.option_box.menu.setTitle("Set Normals By Angle")
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Angle Threshold: ", setObjectName="s002",
            set_limits=[0, 180], setValue=30,
            setToolTip="Mark edges sharp where the dihedral angle ≥ this (degrees); smooth elsewhere.",
        )

    @btk.undoable
    def tb001(self, widget):
        """Set Normals By Angle"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Set Normals By Angle requires a selection.")
            return
        btk.set_edge_hardness(objects, angle=widget.option_box.menu.s002.value())

    # ------------------------------------------------------------------ tb004  Average Normals
    def tb004_init(self, widget):
        widget.option_box.menu.setTitle("Average Normals")

    @btk.undoable
    def tb004(self, widget):
        """Average Normals (smooth shading averages vertex normals)."""
        btk.set_shading(self.selected_objects(), smooth=True)

    # ------------------------------------------------------------------ b-slots
    @btk.undoable
    def b000(self):
        """Soften Edge Normals (smooth shading)."""
        btk.set_shading(self.selected_objects(), smooth=True)

    @btk.undoable
    def b001(self):
        """Harden Edge Normals (flat shading)."""
        btk.set_shading(self.selected_objects(), smooth=False)

    @btk.undoable
    def b006(self):
        """Set To Face (vertex normals follow faces = flat shading)."""
        btk.set_shading(self.selected_objects(), smooth=False)

    # ------------------------------------------------------------------ tb010  Reverse Normals
    def tb010_init(self, widget):
        if not widget.is_initialized:
            widget.option_box.menu.setTitle("Reverse Normals")
            widget.option_box.menu.add(
                "QComboBox", setObjectName="cmb000",
                addItems=["Flip", "Recalculate Outside", "Recalculate Inside"],
                setToolTip="Normal operation mode.",
            )

    @btk.undoable
    def tb010(self, widget):
        """Reverse Normals"""
        objects = self.selected_objects()
        if not objects:
            return
        mode = widget.option_box.menu.cmb000.currentText()
        if mode == "Recalculate Outside":
            btk.recalculate_normals(objects, inside=False)
        elif mode == "Recalculate Inside":
            btk.recalculate_normals(objects, inside=True)
        else:
            btk.flip_normals(objects)

    # ------------------------------------------------------------------ b002  Transfer Normals
    @btk.undoable
    def b002(self):
        """Transfer Normals (active mesh → other selected, native Data-Transfer
        custom split normals)."""
        self.transfer_from_active("CUSTOM_NORMAL")

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def b004(self):
        """Lock/Unlock Vertex Normals — Maya normal locking has no direct Blender analogue."""
        self.sb.message_box("Lock/Unlock Vertex Normals is not applicable in Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
