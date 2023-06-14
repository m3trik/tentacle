# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from uitk.switchboard import signals
from tentacle.slots.maya import SlotsMaya


class Cameras_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb.parent().left_mouse_double_click.connect(self.toggle_camera_view)

    def list000_init(self, widget):
        """ """
        widget.clear()
        widget.refresh = True
        widget.fixed_item_height = 18
        widget.sublist_x_offset = -10
        widget.sublist_y_offset = -10

        try:
            cameras = pm.ls(type=("camera"), l=True)  # Get all cameras
            # filter all startup / default cameras
            startup_cameras = [
                camera
                for camera in cameras
                if pm.camera(camera.parent(0), q=True, startupCamera=True)
            ]
            # get non-default cameras. these are all PyNodes
            non_startup_cameras_pynodes = list(set(cameras) - set(startup_cameras))
            # non-PyNode, regular string name list
            non_startup_cameras = map(str, non_startup_cameras_pynodes)

        except AttributeError:
            non_startup_cameras = []

        if list(non_startup_cameras):
            w1 = widget.add("Cameras")
            w1.sublist.add(non_startup_cameras)

        w2 = widget.add("Per Camera Visibility")
        per_camera_visibility = [
            "Exclusive to Camera",
            "Hidden from Camera",
            "Remove from Exclusive",
            "Remove from Hidden",
            "Remove All for Camera",
            "Remove All",
        ]
        w2.sublist.add(per_camera_visibility)

        w3 = widget.add("Editors")
        editors = ["Camera Sequencer", "Camera Set Editor"]
        w3.sublist.add(editors)

    @signals("on_item_interacted")
    def list000(self, item):
        """ """
        text = item.item_text()
        parent_text = item.parent_item_text()

        if parent_text == "Create":
            if text == "Custom Camera":  # Create a camera with the specified settings
                camera = pm.camera(
                    centerOfInterest=5,
                    focalLength=35,
                    horizontalFilmAperture=1.41732,
                    verticalFilmAperture=0.94488,
                )
            elif text == "Set Custom Camera":  # Set the camera to the perspective view
                home_panel = mtk.get_panel(withFocus=True)
                if pm.modelPanel(home_panel, query=True, camera=True) == "persp":
                    pm.cameraView(camera, edit=True, setCamera=True)

            elif text == "Camera From View":
                mtk.Cam.create_camera_from_view()

            elif parent_text == "Cameras":
                pm.select(text)
                pm.lookThru(text)

        if parent_text == "Editors":
            if text == "Camera Sequencer":
                pm.mel.eval("SequenceEditor;")

            elif text == "Camera Set Editor":
                pm.mel.eval("cameraSetEditor;")

        if parent_text == "Per Camera Visibility":
            if text == "Exclusive to Camera":
                pm.mel.eval(
                    "SetExclusiveToCamera;"
                )  # doPerCameraVisibility 0; Make selected objects exclusive to the selected (or current) camera.
            elif text == "Hidden from Camera":
                pm.mel.eval(
                    "SetHiddenFromCamera;"
                )  # doPerCameraVisibility 1; Make selected objects hidden from the selected (or current) camera.
            elif text == "Remove from Exclusive":
                pm.mel.eval(
                    "CameraRemoveFromExclusive;"
                )  # doPerCameraVisibility 2; Remove selected objects from the selected (or current) camera's exclusive list.
            elif text == "Remove from Hidden":
                pm.mel.eval(
                    "CameraRemoveFromHidden;"
                )  # doPerCameraVisibility 3; Remove the selected objects from the selected (or current) camera's hidden list.
            elif (
                text == "Remove All for Camera"
            ):  # Remove all hidden or exclusive objects for the selected (or current) camera.
                pm.mel.eval("CameraRemoveAll;")  # doPerCameraVisibility 4;
            elif text == "Remove All":
                pm.mel.eval(
                    "CameraRemoveAllForAll;"
                )  # doPerCameraVisibility 5; Remove all hidden or exclusive objects for all cameras.

        if parent_text == "Options":
            if text == "Group Cameras":
                mtk.Cam.group_cameras()
            elif text == "Adjust Clipping":
                self.clippingMenu.show()
            elif text == "Toggle Safe Frames":  # Viewport Safeframes Toggle
                mtk.Cam.toggle_safe_frames()

    def chk000(self, state, widget):
        """Camera Clipping: Auto Clip"""
        if state:
            self.sb.toggle_widgets(self.clippingMenu, setDisabled="s000-1")
        else:
            self.sb.toggle_widgets(self.clippingMenu, setEnabled="s000-1")

        activeCamera = mtk.Cam.get_current_cam()
        if not activeCamera:
            self.sb.message_box("No Active Camera.")
            return

        pm.viewClipPlane(activeCamera, autoClipPlane=True)

    def s000(self, value, widget):
        """Camera Clipping: Near Clip"""
        activeCamera = mtk.Cam.get_current_cam()
        if not activeCamera:
            self.sb.message_box("No Active Camera.")
            return

        pm.viewClipPlane(activeCamera, nearClipPlane=value)

    def s001(self, value, widget):
        """Camera Clipping: Far Clip"""
        activeCamera = mtk.Cam.get_current_cam()
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
                set_limits=(0.01, 10, 0.1, 2),
                setToolTip="Adjust the current cameras near clipping plane.",
            )
            self._clippingMenu.add(
                "QSpinBox",
                setPrefix="Near Clip: ",
                setObjectName="s001",
                set_limits=(10, 10000),
                setToolTip="Adjust the current cameras far clipping plane.",
            )

        # set widget states for the active camera
        activeCamera = mtk.Cam.get_current_cam()
        if not activeCamera:
            self.sb.toggle_widgets(self._clippingMenu, setDisabled="s000-1,chk000")

        elif pm.viewClipPlane(
            activeCamera, q=True, autoClipPlane=1
        ):  # if autoClipPlane is active:
            self._clippingMenu.chk000.setChecked(True)
            self.sb.toggle_widgets(self._clippingMenu, setDisabled="s000-1")

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
        # Get all slot methods from b000 to b007
        slots = self.sb.get_slots_from_string(self, "b000-7")

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


# --------------------------------------------------------------------------------------------

# module name
print(__name__)

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated -------------------------------------


# def tree000(self, wItem=None, column=None):
#       '''

#       '''
#       tree = self.sb.cameras.tree000

#       if not any([wItem, column]):
#           if not tree.refresh: #static list items -----------
#               tree.expandOnHover = True
#               tree.convert(tree.getTopLevelItems(), 'QLabel') #construct the tree using the existing contents.

#               l = []
#               [tree.add('QLabel', 'Editors', setText=s) for s in l]


#           #refreshed list items -----------------------------
#           try:
#               cameras = pm.ls(type=('camera'), l=True) #Get all cameras
#               startup_cameras = [camera for camera in cameras if pm.camera(camera.parent(0), startupCamera=True, q=True)] #filter all startup / default cameras
#               non_startup_cameras_pynodes = list(set(cameras) - set(startup_cameras)) #get non-default cameras. these are all PyNodes
#               non_startup_cameras_transform_pynodes = map(lambda x: x.parent(0), non_startup_cameras_pynodes) #get respective transform names
#               non_startup_cameras = map(str, non_startup_cameras_pynodes) #non-PyNode, regular string name list
#               non_startup_cameras_transforms = map(str, non_startup_cameras_transform_pynodes)
#           except AttributeError: non_startup_cameras=[]
#           [tree.add('QLabel', 'Cameras', refresh=True, setText=s) for s in non_startup_cameras]

#           l = ['Camera Sequencer', 'Camera Set Editor']
#           [tree.add('QLabel', 'Editors', setText=s) for s in l]
#           return

#       widget = tree.get_widget(wItem, column)
#       text = tree.getWidgetText(wItem, column)
#       header = tree.getHeaderFromColumn(column)
#       print(header, text, column)

#       if header=='Create':
#           if text=='Custom Camera':
#               pm.mel.eval('camera -centerOfInterest 5 -focalLength 35 -lensSqueezeRatio 1 -cameraScale 1 -horizontalFilmAperture 1.41732 -horizontalFilmOffset 0 -verticalFilmAperture 0.94488 -verticalFilmOffset 0 -filmFit Fill -overscan 1 -motionBlur 0 -shutterAngle 144 -nearClipPlane 0.1 -farClipPlane 10000 -orthographic 0 -orthographicWidth 30 -panZoomEnabled 0 -horizontalPan 0 -verticalPan 0 -zoom 1; objectMoveCommand; cameraMakeNode 1 "";')
#           if text=='Set Custom Camera':
#               pm.mel.eval('string $homeName = `cameraView -camera persp`;') #cameraView -edit -camera persp -setCamera $homeName;
#           if text=='Camera From View':
#               print('No Maya Version')

#       if header=='Cameras':
#           pm.select(text)
#           pm.lookThru(text)

#       if header=='Editors':
#           if text=='Camera Sequencer':
#               pm.mel.eval('SequenceEditor;')
#           if text=='Camera Set Editor':
#               pm.mel.eval('cameraSetEditor;')

#       if header=='Options':
#           if text=='Group Cameras':
#               mtk.Cam.group_cameras()
#           if text=='Adjust Clipping':
#               self.clippingMenu.show()
#           if text=='Toggle Safe Frames': #Viewport Safeframes Toggle
#               mtk.Cam.toggle_safe_frames()


# def cmb001(self, *args, **kwargs):
#   '''
#   Additional Cameras

#   '''
#   # Get all cameras first
#   cameras = pm.ls(type=('camera'), l=True)
#   # Let's filter all startup / default cameras
#   startup_cameras = [camera for camera in cameras if pm.camera(camera.parent(0), startupCamera=True, q=True)]
#   # non-default cameras are easy to find now. Please note that these are all PyNodes
#   non_startup_cameras_pynodes = list(set(cameras) - set(startup_cameras))
#   # Let's get their respective transform names, just in-case
#   non_startup_cameras_transform_pynodes = map(lambda x: x.parent(0), non_startup_cameras_pynodes)
#   # Now we can have a non-PyNode, regular string names list of them
#   non_startup_cameras = map(str, non_startup_cameras_pynodes)
#   non_startup_cameras_transforms = map(str, non_startup_cameras_transform_pynodes)

#   cmb = self.sb.cameras.cmb001

#   contents = cmb.addItems_(non_startup_cameras, "Cameras")

#   if not index:
#       index = cmb.currentIndex()
#   if index!=0:
#       pm.select (contents[index])
#       cmb.setCurrentIndex(0)


# def cmb002(self, *args, **kwargs):
#   '''
#   Create

#   '''
#   cmb = self.sb.cameras.cmb002

#   items = ['Custom Camera', 'Set Custom Camera', 'Camera From View']
#   contents = cmb.addItems_(items, "Create")

#   if not index:
#       index = cmb.currentIndex()
#   if index!=0:
#       if index==1:
#           pm.mel.eval('cameraView -edit -camera persp -setCamera $homeName;')
#       if index==2:
#           pm.mel.eval('string $homeName = `cameraView -camera persp`;')
#       if index==3:
#           pm.mel.eval('print "--no code--")
#       cmb.setCurrentIndex(0)


# def cmb003(self, *args, **kwargs):
#   '''
#   Options

#   '''
#   cmb = self.sb.cameras.cmb003

#   items = ['Group Cameras']
#   contents = cmb.addItems_(items, "Options")

#   if not index:
#       index = cmb.currentIndex()
#   if index!=0:
#       if index==1:
#           pm.mel.eval('''
#           if (`objExists cameras`)
#           {
#             print "Group 'cameras' already exists";
#           }
#           else
#           {
#             group -world -name cameras side front top persp;
#             hide cameras;
#             // Now add non-default cameras to group
#             if (`objExists back`)
#             {
#               parent back cameras;
#             }
#             if (`objExists bottom`)
#             {
#               parent bottom cameras;
#             }
#             if (`objExists left`)
#             {
#               parent left cameras;
#             }
#             if (`objExists alignToPoly`)
#             {
#               parent alignToPoly cameras;
#             }
#           }
#           ''')
#       cmb.setCurrentIndex(0)
