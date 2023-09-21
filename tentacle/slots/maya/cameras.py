# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from uitk.switchboard import signals
from tentacle.slots.maya import SlotsMaya


class Cameras(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb.parent().left_mouse_double_click.connect(self.toggle_camera_view)

    def list000_init(self, widget):
        widget.clear()
        widget.refresh = True
        widget.fixed_item_height = 18
        widget.sublist_x_offset = -10
        widget.sublist_y_offset = -10

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
        options = ["Auto Adjust Clipping"]
        w3.sublist.add(options)

    @signals("on_item_interacted")
    def list000(self, item):
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
                mtk.adjust_camera_clipping(auto=True)

    def chk000(self, state, widget):
        """Camera Clipping: Auto Clip"""
        if state:
            self.sb.toggle_multi(self.clippingMenu, setDisabled="s000-1")
        else:
            self.sb.toggle_multi(self.clippingMenu, setEnabled="s000-1")

        activeCamera = mtk.get_current_cam()
        if not activeCamera:
            self.sb.message_box("No Active Camera.")
            return

        pm.viewClipPlane(activeCamera, autoClipPlane=True)

    def s000(self, value, widget):
        """Camera Clipping: Near Clip"""
        activeCamera = mtk.get_current_cam()
        if not activeCamera:
            self.sb.message_box("No Active Camera.")
            return

        pm.viewClipPlane(activeCamera, nearClipPlane=value)

    def s001(self, value, widget):
        """Camera Clipping: Far Clip"""
        activeCamera = mtk.get_current_cam()
        if not activeCamera:
            self.sb.message_box("No Active Camera.")
            return

        pm.viewClipPlane(activeCamera, farClipPlane=value)

    def b000(self):
        """Cameras: Back View"""
        try:  # if pm.objExists('back'):
            pm.lookThru("back")

        except Exception:
            cam, camShape = pm.camera()  # create camera
            pm.lookThru(cam)

            pm.rename(cam, "back")
            pm.viewSet(back=1)  # initialize the camera view
            pm.hide(cam)

            grp = pm.ls("cameras", transforms=1)
            if grp and self.is_group(
                grp[0]
            ):  # add the new cam to 'cameras' group (if it exists).
                pm.parent(cam, "cameras")

    def b001(self):
        """Cameras: Top View"""
        try:
            pm.lookThru("topShape")

        except Exception:
            pm.lookThru("|top")

    def b002(self):
        """Cameras: Right View"""
        try:
            pm.lookThru("sideShape")

        except Exception:
            pm.lookThru("|side")

    def b003(self):
        """Cameras: Left View"""
        try:  # if pm.objExists('back'):
            pm.lookThru("left")

        except Exception:
            cam, camShape = pm.camera()  # create camera
            pm.lookThru(cam)

            pm.rename(cam, "left")
            pm.viewSet(leftSide=1)  # initialize the camera view
            pm.hide(cam)

            grp = pm.ls("cameras", transforms=1)
            if grp and self.is_group(
                grp[0]
            ):  # add the new cam to 'cameras' group (if it exists).
                pm.parent(cam, "cameras")

    def b004(self):
        """Cameras: Perspective View"""
        try:
            pm.lookThru("perspShape")

        except Exception:
            pm.lookThru("|persp")

    def b005(self):
        """Cameras: Front View"""
        try:
            pm.lookThru("frontShape")

        except Exception:
            pm.lookThru("|front")

    def b006(self):
        """Cameras: Bottom View"""
        try:  # if pm.objExists('back'):
            pm.lookThru("bottom")

        except Exception:
            cam, camShape = pm.camera()  # create camera
            pm.lookThru(cam)

            pm.rename(cam, "bottom")
            pm.viewSet(bottom=1)  # initialize the camera view
            pm.hide(cam)

            grp = pm.ls("cameras", transforms=1)
            if grp and self.is_group(
                grp[0]
            ):  # add the new cam to 'cameras' group (if it exists).
                pm.parent(cam, "cameras")

    def b007(self):
        """Cameras: Align View"""
        selection = pm.ls(sl=1)
        if not selection:
            self.sb.message_box("Nothing Selected.")
            return

        if not pm.objExists("alignToPoly"):  # if no camera exists; create camera
            cam, camShape = pm.camera()
            pm.rename(cam, "alignToPoly")
            pm.hide(cam)

            grp = pm.ls("cameras", transforms=1)
            if grp and self.is_group(
                grp[0]
            ):  # add the new cam to 'cameras' group (if it exists).
                pm.parent(cam, "cameras")

        ortho = int(
            pm.camera("alignToPoly", q=True, orthographic=1)
        )  # check if camera view is orthoraphic
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

    @property
    def clippingMenu(self):
        """Menu: Camera clip plane settings.

        Returns:
                (obj) menu as a property.
        """
        if not hasattr(self, "_clippingMenu"):
            self._clippingMenu = self.sb.Menu(self.sb.cameras, position="cursorPos")
            self._clippingMenu.add(
                "QPushButton",
                setText="Auto Clip",
                setObjectName="chk000",
                setCheckable=True,
                setToolTip="When Auto Clip is ON, geometry closer to the camera than 3 units is not displayed. Turn OFF to manually define.",
            )
            self._clippingMenu.add(
                "QDoubleSpinBox",
                setPrefix="Far Clip:  ",
                setObjectName="s000",
                set_limits=[0.01, 10, 0.1, 2],
                setToolTip="Adjust the current cameras near clipping plane.",
            )
            self._clippingMenu.add(
                "QSpinBox",
                setPrefix="Near Clip: ",
                setObjectName="s001",
                set_limits=[10, 10000],
                setToolTip="Adjust the current cameras far clipping plane.",
            )

        # set widget states for the active camera
        activeCamera = mtk.get_current_cam()
        if not activeCamera:
            self.sb.toggle_multi(self._clippingMenu, setDisabled="s000-1,chk000")

        elif pm.viewClipPlane(
            activeCamera, q=True, autoClipPlane=1
        ):  # if autoClipPlane is active:
            self._clippingMenu.chk000.setChecked(True)
            self.sb.toggle_multi(self._clippingMenu, setDisabled="s000-1")

        nearClip = (
            pm.viewClipPlane(activeCamera, q=True, nearClipPlane=1)
            if activeCamera
            else 1.0
        )
        farClip = (
            pm.viewClipPlane(activeCamera, q=True, farClipPlane=1)
            if activeCamera
            else 1000.0
        )

        self._clippingMenu.s000.setValue(nearClip)
        self._clippingMenu.s001.setValue(farClip)

        return self._clippingMenu

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
