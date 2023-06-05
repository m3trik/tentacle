# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Symmetry_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # application symmetry state
        state = pm.symmetricModelling(query=True, symmetry=True)
        axis = pm.symmetricModelling(query=True, axis=True)
        widget = "chk000" if axis == "x" else "chk001" if axis == "y" else "chk002"
        getattr(self.sb.symmetry, widget).setChecked(state)

    def draggableHeader_init(self, widget):
        """ """
        cmb000 = widget.ctx_menu.add(
            self.sb.ComboBox, setObjectName="cmb000", setToolTip=""
        )
        items = [""]
        cmb000.addItems_(items, "")

    def chk000(self, *args, **kwargs):
        """Symmetry X"""
        state = kwargs.get("state")

        self.sb.toggle_widgets(setUnChecked="chk001,chk002")
        self.setSymmetry(state, "x")

    def chk001(self, *args, **kwargs):
        """Symmetry Y"""
        state = kwargs.get("state")

        self.sb.toggle_widgets(setUnChecked="chk000,chk002")
        self.setSymmetry(state, "y")

    def chk002(self, *args, **kwargs):
        """Symmetry Z"""
        state = kwargs.get("state")

        self.sb.toggle_widgets(setUnChecked="chk000,chk001")
        self.setSymmetry(state, "z")

    def chk004(self, *args, **kwargs):
        """Symmetry: Object"""
        self.sb.symmetry.chk005.setChecked(False)  # uncheck symmetry:topological

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = kwargs.get("widget")
        index = kwargs.get("index")

        if index > 0:
            if index == cmb.items.index(""):
                pass
            cmb.setCurrentIndex(0)

    def chk005(self, *args, **kwargs):
        """Symmetry: Topo"""
        self.sb.symmetry.chk004.setChecked(False)  # uncheck symmetry:object space
        if any(
            [
                self.sb.symmetry.chk000.isChecked(),
                self.sb.symmetry.chk001.isChecked(),
                self.sb.symmetry.chk002.isChecked(),
            ]
        ):  # (symmetry)
            pm.symmetricModelling(edit=True, symmetry=False)
            self.sb.toggle_widgets(setUnChecked="chk000,chk001,chk002")
            self.sb.message_box(
                "First select a seam edge and then check the symmetry button to enable topographic symmetry",
                message_type="Note",
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


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
