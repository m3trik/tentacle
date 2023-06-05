# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Vfx_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draggableHeader_init(self, widget):
        """ """ 
        cmb000 = widget.ctx_menu.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")
        files = [""]
        cmb000.addItems_(files, "")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = kwargs.get('widget')
        index = kwargs.get('index')

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
