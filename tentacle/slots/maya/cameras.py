# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from uitk import Signals
from tentacle.slots.maya._slots_maya import SlotsMaya


class Cameras(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.cameras

        # Double-click gesture + keyable 'toggle_camera_view' command. Shared,
        # DCC-agnostic wiring on the base slot class (tentacle.slots._slots.Slots).
        self.register_camera_view_toggle()

    def list000_init(self, widget):
        """Initialize Camera Options List"""
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True  # This method called on each show
            widget.fixed_item_height = 18

        # Define camera types and their focal lengths
        camera_types = {
            "Standard Camera": 35,
            "Wide Angle Camera": 18,
            "Telephoto Camera": 85,
        }

        # Add 'Create' as the first parent item and its sublist
        w0 = widget.add("Create Camera")
        w0.sublist.add(camera_types)

        # Existing code for finding and listing cameras
        try:
            scene_cameras = cmds.ls(type="camera", l=True) or []
            startup_cameras = []
            non_startup_cameras = []
            for camera in scene_cameras:
                parent = mtk.NodeUtils.get_parent(camera, full_path=True)
                if parent and cmds.camera(parent, q=True, startupCamera=True):
                    startup_cameras.append(camera)
                else:
                    non_startup_cameras.append(camera)

        except AttributeError:
            non_startup_cameras = []

        if non_startup_cameras:
            w1 = widget.add("Select Camera")
            w1.sublist.add(non_startup_cameras)

        w2 = widget.add("Visibility Settings")
        per_camera_visibility = [
            "Exclusive to Camera",
            "Hidden from Camera",
            "Remove from Exclusive",
            "Remove from Hidden",
            "Remove All for Camera",
            "Remove All",
        ]
        w2.sublist.add(per_camera_visibility)

        w3 = widget.add("Camera Options")
        options = ["Auto Adjust Clipping", "Reset Clipping"]
        w3.sublist.add(options)

    @Signals("on_item_interacted")
    def list000(self, item):
        """Camera Options List"""
        text = item.item_text()
        parent_text = item.parent_item_text()

        if parent_text == "Create Camera":
            focal_length = item.item_data()
            cmds.camera(focalLength=focal_length)

        elif parent_text == "Select Camera":
            cmds.select(text)
            cmds.lookThru(text)

        elif parent_text == "Visibility Settings":
            if text == "Exclusive to Camera":
                mel.eval("SetExclusiveToCamera;")
            elif text == "Hidden from Camera":
                mel.eval("SetHiddenFromCamera;")
            elif text == "Remove from Exclusive":
                mel.eval("CameraRemoveFromExclusive;")
            elif text == "Remove from Hidden":
                mel.eval("CameraRemoveFromHidden;")
            elif text == "Remove All for Camera":
                mel.eval("CameraRemoveAll;")
            elif text == "Remove All":
                mel.eval("CameraRemoveAllForAll;")

        elif parent_text == "Camera Options":
            if text == "Auto Adjust Clipping":
                print("Auto Adjust Clipping selected")
                mtk.adjust_camera_clipping(near_clip="auto", far_clip="auto")
            elif text == "Reset Clipping":
                mtk.adjust_camera_clipping(near_clip="reset", far_clip="reset")

    def b000(self):
        """Cameras: Back View"""
        mtk.switch_viewport_camera("back")

    def b001(self):
        """Cameras: Top View"""
        mtk.switch_viewport_camera("top")

    def b002(self):
        """Cameras: Right View"""
        mtk.switch_viewport_camera("side")

    def b003(self):
        """Cameras: Left View"""
        mtk.switch_viewport_camera("left")

    def b004(self):
        """Cameras: Perspective View"""
        mtk.switch_viewport_camera("persp")

    def b005(self):
        """Cameras: Front View"""
        mtk.switch_viewport_camera("front")

    def b006(self):
        """Cameras: Bottom View"""
        mtk.switch_viewport_camera("bottom")

    def b007(self):
        """Cameras: Align View"""
        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box("Nothing Selected.")
            return

        if not cmds.objExists("alignToPoly"):  # if no camera exists; create camera
            cam, camShape = cmds.camera()
            cmds.hide(cam)
            cmds.rename(cam, "alignToPoly")

        # Check if camera view is orthoraphic
        ortho = int(cmds.camera("alignToPoly", q=True, orthographic=1))
        if not ortho:
            cmds.viewPlace("alignToPoly", ortho=1)

        cmds.lookThru("alignToPoly")
        mel.eval("AlignCameraToPolygon")
        cmds.viewFit(fitFactor=5.0)

    def b010(self):
        """Camera: Dolly"""
        cmds.setToolTo("dollyContext")

    def b011(self):
        """Camera: Roll"""
        # Maya has no interactive 'roll' tool context; roll the active camera
        # about its view axis (a discrete nudge, not a drag tool).
        cam = mtk.CamUtils.get_current_cam()
        if cam:
            cmds.roll(cam, degree=15, relative=True)

    def b012(self):
        """Camera: Truck"""
        # 'Truck' is Maya's Track tool (pan the camera perpendicular to the view).
        cmds.setToolTo("trackContext")

    def b013(self):
        """Camera: Orbit"""
        # 'Orbit' is Maya's Tumble tool.
        cmds.setToolTo("tumbleContext")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
