# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.symmetry import Symmetry


class Symmetry_max(Symmetry, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb000 = self.sb.symmetry.draggableHeader.ctx_menu
        items = [""]
        cmb000.addItems_(items, "")

        # set initial checked state
        # state = pm.symmetricModelling(query=True, symmetry=True) #application symmetry state
        # axis = pm.symmetricModelling(query=True, axis=True)
        # widget = 'chk000' if axis=='x' else 'chk001' if axis=='y' else 'chk002'
        # getattr(self.sb.symmetry, widget).setChecked(state)
        # getattr(self.sb.symmetry_submenu, widget).setChecked(state)

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.symmetry.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def chk005(self, state=None):
        """Symmetry: Topo"""
        self.sb.symmetry.chk004.setChecked(False)  # uncheck symmetry:object space
        # if any ([self.sb.symmetry.chk000.isChecked(), self.sb.symmetry.chk001.isChecked(), self.sb.symmetry.chk002.isChecked()]): #(symmetry)
        # 	pm.symmetricModelling(edit=True, symmetry=False)
        # 	self.sb.toggle_widgets(setUnChecked='chk000-2')
        # 	return 'Note: First select a seam edge and then check the symmetry button to enable topographic symmetry'

    def setSymmetry(self, state, axis):
        """"""
        # space = "world" #workd space
        # if self.sb.symmetry.chk004.isChecked(): #object space
        # 	space = "object"
        # elif self.sb.symmetry.chk005.isChecked(): #topological symmetry
        # 	space = "topo"

        if axis == "x":
            _axis = 0  # 0(x), 1,(y), 2(z)
        if axis == "y":
            _axis = 1
        if axis == "z":
            _axis = 2

        state = state if state == 0 else 1  # for case when checkbox gives a state of 2.

        for obj in rt.selection:
            # check if modifier exists
            mod = obj.modifiers[rt.Symmetry]
            if mod == None:  # if not create
                mod = rt.symmetry()
                rt.addModifier(obj, mod)

            # set attributes
            mod.enabled = state
            mod.threshold = 0.01
            mod.axis = _axis
            mod.flip = negative

        rt.redrawViews()
        self.sb.message_box(
            "Symmetry: " + axis.capitalize() + " <hl>" + str(state) + "</hl>"
        )


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
