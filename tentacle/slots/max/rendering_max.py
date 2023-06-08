# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.rendering import Rendering


class Rendering_max(Rendering, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.rendering.draggableHeader.ctx_menu.cmb000
        items = [""]
        cmb.addItems_(items, "")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.rendering.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def cmb001(self, *args, **kwargs):
        """Render: camera"""
        cmb = self.sb.rendering.cmb001

        self.cams = [cam for cam in rt.cameras if "Target" not in str(cam)]
        if self.cams:
            items = [str(cam.name) for cam in self.cams]  # camera names
            cmb.addItems_(items, clear=True)

    def b000(self, *args, **kwargs):
        """Render Current Frame"""
        cmb = self.sb.rendering.cmb001
        index = cmb.currentIndex()

        try:
            rt.render(camera=self.cams[index])  # render with selected camera
        except:
            rt.render()

    def b001(self, *args, **kwargs):
        """Open Render Settings Window"""
        maxEval("unifiedRenderGlobalsWindow;")

    def b002(self, *args, **kwargs):
        """Redo Previous Render"""
        pass

    def b003(self, *args, **kwargs):
        """Editor: Render Setup"""
        maxEval("max render scene")

    def b004(self, *args, **kwargs):
        """Editor: Rendering Flags"""
        maxEval("renderFlagsWindow;")

    def b005(self, *args, **kwargs):
        """Apply Vray Attributes To Selected Objects"""
        selection = pm.ls(sl=True)
        currentID = 1
        for obj in selection:
            # get renderable shape nodes relative to transform, iterate through and apply subdivision
            shapes = pm.listRelatives(obj, s=1, ni=1)
            if shapes:
                for shape in shapes:
                    mel.eval(
                        "vray addAttributesFromGroup " + shape + " vray_subdivision 1;"
                    )
                    mel.eval(
                        "vray addAttributesFromGroup " + shape + " vray_subquality 1;"
                    )
            # apply object ID to xform. i don't like giving individual shapes IDs.
            mel.eval("vray addAttributesFromGroup " + obj + " vray_objectID 1;")
            pm.setAttr(obj + ".vrayObjectID", currentID)
            currentID += 1

    def b006(self, *args, **kwargs):
        """Load Vray Plugin"""


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
