# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Scripting_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draggableHeader_init(self, widget):
        """ """
        cmb = widget.ctx_menu.add(
            self.sb.ComboBox, setObjectName="cmb000", setToolTip=""
        )
        files = [""]
        cmb.addItems_(files, "")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = kwargs.get("widget")
        index = kwargs.get("index")

        if index > 0:
            if index == cmb.items.index(""):
                pass
            cmb.setCurrentIndex(0)

    def chk000(self, *args, **kwargs):
        """Toggle Mel/Python"""
        chk = kwargs.get("chk")
        state = kwargs.get("state")

        if state:
            chk.setText("python")
        else:
            chk.setText("MEL")

    def b000(self, *args, **kwargs):
        """Toggle Script Output Window"""
        state = pm.workspaceControl("scriptEditorOutputWorkspace", query=1, visible=1)
        pm.workspaceControl("scriptEditorOutputWorkspace", edit=1, visible=not state)

    def b001(self, *args, **kwargs):
        """Command Line Window"""
        pm.mel.eval("commandLineWindow;")

    def b002(self, *args, **kwargs):
        """Script Editor"""
        pm.mel.eval("ScriptEditor;")

    def b003(self, *args, **kwargs):
        """New Tab"""
        label = "MEL"
        if self.sb.scripting.chk000.isChecked():
            label = ".py"
        # self.sb.scripting.tabWidget.addTab(label)
        self.sb.scripting.tabWidget.insertTab(0, label)

    def b004(self, *args, **kwargs):
        """Delete Tab"""
        index = self.sb.scripting.tabWidget.currentIndex()
        self.sb.scripting.tabWidget.removeTab(index)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
