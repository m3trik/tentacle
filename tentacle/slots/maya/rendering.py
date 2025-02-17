# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya
import pythontk as ptk
import mayatk as mtk


class Rendering(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.rendering
        self.submenu = self.sb.loaded_ui.rendering_submenu

    def cmb001_init(self, widget):
        """Render: camera"""
        lst = {c.name(): c for c in pm.ls(type="camera") if "Target" not in c.name()}
        widget.add(lst)

    def b000(self):
        """Render Current Frame"""
        self.ui.cmb001.init_slot()
        camera = self.ui.cmb001.currentText()
        pm.render(camera)  # render with selected camera

    def b001(self):
        """Open Render Settings Window"""
        pm.mel.unifiedRenderGlobalsWindow()

    def b002(self):
        """Redo Previous Render"""
        pm.mel.redoPreviousRender("render")

    def b003(self):
        """Editor: Render Setup"""
        pm.mel.RenderSetupWindow()

    def b004(self):
        """Editor: Rendering Flags"""
        pm.mel.renderFlagsWindow()

    def b005(self):
        """Apply Vray Attributes To Selected Objects"""
        if not self.load_vray_plugin(query=True):
            print("VRay plugin is not loaded. Loading it now.")
            self.load_vray_plugin()

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

    def b006(self):
        """Load Vray Plugin"""
        mtk.vray_plugin()

    def b007(self):
        """Export Playblast"""
        # create playblast to the users desktop and compress it
        playblast_path = mtk.create_playblast(
            filepath="%USERPROFILE%/Desktop", compression="iyuv"
        )
        ptk.compress_video(input_filepath=playblast_path, delete_original=True)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
