# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.scripting import Scripting


class Scripting_max(Scripting, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.scripting.draggableHeader.ctx_menu.cmb000
        items = [""]
        contents = cmb.addItems_(items, "")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.scripting.draggableHeader.ctx_menu.cmb000

        if index > 0:
            if index == cmb.items.index(""):
                pass
            cmb.setCurrentIndex(0)

    def b000(self):
        """Toggle Script Output Window"""
        state = pm.workspaceControl("scriptEditorOutputWorkspace", q=True, visible=1)
        pm.workspaceControl("scriptEditorOutputWorkspace", edit=1, visible=not state)

    def b001(self):
        """Command Line Window"""
        maxEval("commandLineWindow_;")

    def b002(self):
        """Script Editor"""
        maxEval("ScriptEditor;")

    def b003(self):
        """New Tab"""
        label = "Maxscript"
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
