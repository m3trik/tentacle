# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Symmetry(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def chk000_init(self, widget):
        """Set initial symmetry state"""
        state = pm.symmetricModelling(query=True, symmetry=True)
        axis = pm.symmetricModelling(query=True, axis=True)
        w = "chk000" if axis == "x" else "chk001" if axis == "y" else "chk002"
        getattr(widget.ui, w).setChecked(state)

    def chk005_init(self, widget):
        """Set symmetry reference space"""
        self.sb.create_button_groups(widget.ui, "chk004-5")

    def chk000(self, state, widget):
        """Symmetry X"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk001,chk002")
        self.setSymmetry(state, "x")

    def chk001(self, state, widget):
        """Symmetry Y"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk000,chk002")
        self.setSymmetry(state, "y")

    def chk002(self, state, widget):
        """Symmetry Z"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk000,chk001")
        self.setSymmetry(state, "z")

    def chk005(self, state, widget):
        """Symmetry: Topo"""
        if any(
            [
                self.sb.symmetry.chk000.isChecked(),
                self.sb.symmetry.chk001.isChecked(),
                self.sb.symmetry.chk002.isChecked(),
            ]
        ):  # (symmetry)
            pm.symmetricModelling(edit=True, symmetry=False)
            self.sb.toggle_multi(widget.ui, setUnChecked="chk000-2")
            self.sb.message_box(
                "First select a seam edge and then check the symmetry button to enable topographic symmetry",
                message_type="Info",
            )

    def setSymmetry(self, state, axis):
        space = "world"  # workd space
        if self.sb.symmetry.chk004.isChecked():  # object space
            space = "object"
        elif self.sb.symmetry.chk005.isChecked():  # topological symmetry
            space = "topo"

        state = state if state == 0 else 1  # for case when checkbox gives a state of 2.

        tolerance = 0.25
        pm.symmetricModelling(
            edit=True, symmetry=state, axis=axis, about=space, tolerance=tolerance
        )
        # if state:
        #   self.sb.message_box('Symmetry: <hl>{}</hl>'.format(axis.upper(), message_type='Result'))


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
