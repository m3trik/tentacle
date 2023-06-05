# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Rendering_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draggableHeader_init(self, widget):
        """ """
        cmb = widget.option_menu.add(
            self.sb.ComboBox, setObjectName="cmb000", setToolTip=""
        )
        items = [""]
        cmb.addItems_(items, "")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = kwargs.get("widget")
        index = kwargs.get("index")

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def cmb001_init(self, widget):
        """Render: camera"""
        lst = {c.name(): c for c in pm.ls(type="camera") if "Target" not in c.name()}
        widget.addItems_(lst)

    def b000(self, *args, **kwargs):
        """Render Current Frame"""
        cmb = kwargs.get("widget")
        index = kwargs.get("index")

        pm.render(camera=cmb.items[index])  # render with selected camera

    def b001(self, *args, **kwargs):
        """Open Render Settings Window"""
        pm.mel.unifiedRenderGlobalsWindow()

    def b002(self, *args, **kwargs):
        """Redo Previous Render"""
        pm.mel.redoPreviousRender("render")

    def b003(self, *args, **kwargs):
        """Editor: Render Setup"""
        pm.mel.RenderSetupWindow()

    def b004(self, *args, **kwargs):
        """Editor: Rendering Flags"""
        pm.mel.renderFlagsWindow()

    def b005(self, *args, **kwargs):
        """Apply Vray Attributes To Selected Objects"""
        selection = pm.ls(selection=True)
        currentID = 1
        for obj in selection:
            # get renderable shape nodes relative to transform, iterate through and apply subdivision
            shapes = pm.listRelatives(obj, s=1, ni=1)
            if shapes:
                for shape in shapes:
                    pm.mel.eval(
                        "vray addAttributesFromGroup " + shape + " vray_subdivision 1;"
                    )
                    pm.mel.eval(
                        "vray addAttributesFromGroup " + shape + " vray_subquality 1;"
                    )
            # apply object ID to xform. i don't like giving individual shapes IDs.
            pm.mel.eval("vray addAttributesFromGroup " + obj + " vray_objectID 1;")
            pm.setAttr(obj + ".vrayObjectID", currentID)
            currentID += 1

    def b006(self, *args, **kwargs):
        """Load Vray Plugin"""
        if self.loadVRayPlugin(query=True):
            self.loadVRayPlugin(unload=True)
        else:
            self.loadVRayPlugin()

    def loadVRayPlugin(self, unload=False, query=False):
        """Load/Unload the Maya Vray Plugin if it exists.

        Parameters:
                unload (bool): Unload the VRay plugin.
                query (bool): Query the state of the VRay Plugin.
        """
        if query:
            return (
                True if pm.pluginInfo("vrayformaya.mll", query=1, loaded=1) else False
            )

        vray = ["vrayformaya.mll", "vrayformayapatch.mll"]

        if unload:
            try:
                pm.unloadPlugin(vray)
            except:
                pm.unloadPlugin(vray, force=1)
                self.sb.message_box(
                    "{0}{1}{2}".format("Force unloadPlugin:", str(vray), " "),
                    message_type="Result",
                )
        else:
            pm.loadPlugin(vray)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
