# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from uitk import Signals
from tentacle.slots.maya import SlotsMaya


class Cameras(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.cameras

        try:
            self.sb.parent().left_mouse_double_click.connect(self.toggle_camera_view)
        except AttributeError:
            pass

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
            cameras = pm.ls(type=("camera"), l=True)
            startup_cameras = [
                camera
                for camera in cameras
                if pm.camera(camera.parent(0), q=True, startupCamera=True)
            ]
            non_startup_cameras_pynodes = list(set(cameras) - set(startup_cameras))
            non_startup_cameras = list(map(str, non_startup_cameras_pynodes))

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
            pm.camera(focalLength=focal_length)

        elif parent_text == "Select Camera":
            pm.select(text)
            pm.lookThru(text)

        elif parent_text == "Visibility Settings":
            if text == "Exclusive to Camera":
                pm.mel.eval("SetExclusiveToCamera;")
            elif text == "Hidden from Camera":
                pm.mel.eval("SetHiddenFromCamera;")
            elif text == "Remove from Exclusive":
                pm.mel.eval("CameraRemoveFromExclusive;")
            elif text == "Remove from Hidden":
                pm.mel.eval("CameraRemoveFromHidden;")
            elif text == "Remove All for Camera":
                pm.mel.eval("CameraRemoveAll;")
            elif text == "Remove All":
                pm.mel.eval("CameraRemoveAllForAll;")

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
        selection = pm.selected()
        if not selection:
            self.sb.message_box("Nothing Selected.")
            return

        if not pm.objExists("alignToPoly"):  # if no camera exists; create camera
            cam, camShape = pm.camera()
            pm.hide(cam)
            pm.rename(cam, "alignToPoly")

        # Check if camera view is orthoraphic
        ortho = int(pm.camera("alignToPoly", q=True, orthographic=1))
        if not ortho:
            pm.viewPlace("alignToPoly", ortho=1)

        pm.lookThru("alignToPoly")
        pm.AlignCameraToPolygon()
        pm.viewFit(fitFactor=5.0)

    def b010(self):
        """Camera: Dolly"""
        pm.viewPreset(camera="dolly")

    def b011(self):
        """Camera: Roll"""
        pm.viewPreset(camera="roll")

    def b012(self):
        """Camera: Truck"""
        pm.viewPreset(camera="truck")

    def b013(self):
        """Camera: Orbit"""
        pm.viewPreset(camera="orbit")

    def toggle_camera_view(self):
        """Toggle between the last two camera views in history."""
        slots = self.sb.get_methods_by_string_pattern(self, "b000-7")
        # Get the last two methods from the slot history
        history = self.sb.slot_history(slice(-2, None), inc=slots)
        if not history:
            return

        # If the last method is b004, call the last non-perspective camera
        if history[-1].__name__ == self.b004.__name__:
            last_non_persp_cam = history[-2]
            last_non_persp_cam()
            self.sb.slot_history(add=last_non_persp_cam)
        else:  # Otherwise, call b004
            self.b004()
            self.sb.slot_history(add=self.b004)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
