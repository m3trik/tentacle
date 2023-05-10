# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.scripting import Scripting


class Scripting_blender(Scripting, Slots_blender):
    def __init__(self, *args, **kwargs):
        Slots_blender.__init__(self, *args, **kwargs)
        Scripting.__init__(self, *args, **kwargs)

        cmb = self.sb.scripting.draggableHeader.ctxMenu.cmb000
        files = [""]
        contents = cmb.addItems_(files, "")

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.scripting.draggableHeader.ctxMenu.cmb000

        if index > 0:
            if index == cmd.items.index(""):
                pass
            cmb.setCurrentIndex(0)

    def b000(self):
        """Toggle Script Output Window"""
        state = pm.workspaceControl("scriptEditorOutputWorkspace", query=1, visible=1)
        pm.workspaceControl("scriptEditorOutputWorkspace", edit=1, visible=not state)

    def b001(self):
        """Command Line Window"""
        mel.eval("commandLineWindow;")

    def b002(self):
        """Script Editor"""
        mel.eval("ScriptEditor;")

    def b003(self):
        """New Tab"""
        label = "MEL"
        if self.sb.scripting.chk000.isChecked():
            label = ".py"
        # self.sb.scripting.tabWidget.addTab(label)
        self.sb.scripting.tabWidget.insertTab(0, label)

    def b004(self):
        """Delete Tab"""
        index = self.sb.scripting.tabWidget.currentIndex()
        self.sb.scripting.tabWidget.removeTab(index)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
