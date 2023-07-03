# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Mirror_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="-",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Perform mirror along the negative axis.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="X",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Perform mirror along X axis.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Y",
            setObjectName="chk002",
            setToolTip="Perform mirror along Y axis.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Z",
            setObjectName="chk003",
            setToolTip="Perform mirror along Z axis.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="World Space",
            setObjectName="chk008",
            setChecked=True,
            setToolTip="Mirror in world space instead of object space.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Un-Instance",
            setObjectName="chk009",
            setChecked=True,
            setToolTip="Un-Instance any previously instanced objects before mirroring.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Instance",
            setObjectName="chk004",
            setToolTip="Instance the mirrored object(s).",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Cut",
            setObjectName="chk005",
            setToolTip="Perform a delete along specified axis before mirror.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Merge",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Merge the mirrored geometry with the original.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Merge Mode: ",
            setObjectName="s001",
            set_limits=[0, 2],
            setValue=0,
            setToolTip="0) Do not merge border edges.<br>1) Border edges merged.<br>2) Border edges extruded and connected.",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Merge Threshold: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.001, 3],
            setValue=0.005,
            setToolTip="Merge vertex distance.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Delete Original",
            setObjectName="chk010",
            setToolTip="Delete the original objects after mirroring.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Delete History",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Delete non-deformer history on the object before performing the operation.",
        )

    def tb000(self, widget):
        """Mirror Geometry"""
        axis = self.sb.get_axis_from_checkboxes("chk000-3", widget.menu)
        # 1) object space, 2) world space.
        axisPivot = 2 if widget.menu.chk008.isChecked() else 1
        # cut mesh on axis before mirror.
        cutMesh = widget.menu.chk005.isChecked()
        # Un-Instance any previously instanced objects before mirroring.
        uninstance = widget.menu.chk009.isChecked()
        instance = widget.menu.chk004.isChecked()
        merge = widget.menu.chk007.isChecked()
        mergeMode = widget.menu.s001.value()
        mergeThreshold = widget.menu.s000.value()
        # delete the original objects after mirroring.
        deleteOriginal = widget.menu.chk010.isChecked()
        # delete the object's non-deformer history.
        deleteHistory = widget.menu.chk006.isChecked()

        objects = pm.ls(sl=1)

        self.sb.duplicate.slots.unInstance(objects)

        return self.mirrorGeometry(
            objects,
            axis=axis,
            axisPivot=axisPivot,
            cutMesh=cutMesh,
            instance=instance,
            merge=merge,
            mergeMode=mergeMode,
            mergeThreshold=mergeThreshold,
            deleteOriginal=deleteOriginal,
            deleteHistory=deleteHistory,
        )

    def b000(self):
        """Mirror: X"""
        self.sb.mirror.tb000.menu.chk001.setChecked(True)
        self.sb.mirror.tb000.call_slot()

    def b001(self):
        """Mirror: Y"""
        self.sb.mirror.tb000.menu.chk002.setChecked(True)
        self.sb.mirror.tb000.call_slot()

    def b002(self):
        """Mirror: Z"""
        self.sb.mirror.tb000.menu.chk003.setChecked(True)
        self.sb.mirror.tb000.call_slot()

    @mtk.undo
    def mirrorGeometry(
        self,
        objects=None,
        axis="-x",
        axisPivot=2,
        cutMesh=False,
        instance=False,
        merge=False,
        mergeMode=1,
        mergeThreshold=0.005,
        deleteOriginal=False,
        deleteHistory=True,
    ):
        """Mirror geometry across a given axis.

        Parameters:
                objects (obj): The objects to mirror. If None; any currently selected objects will be used.
                axis (string) = The axis in which to perform the mirror along. case insensitive. (valid: 'x', '-x', 'y', '-y', 'z', '-z')
                axisPivot (int): The pivot on which to mirror on. valid: 0) Bounding Box, 1) Object, 2) World.
                cutMesh (bool): Perform a delete along specified axis before mirror.
                instance (bool): Instance the mirrored object(s).
                merge (bool): Merge the mirrored geometry with the original.
                mergeMode (int): 0) Do not merge border edges. 1) Border edges merged. 2) Border edges extruded and connected.
                mergeThreshold (float) = Merge vertex distance.
                deleteOriginal (bool): Delete the original objects after mirroring.
                deleteHistory (bool): Delete non-deformer history on the object before performing the operation.

        Returns:
                (obj) The polyMirrorFace history node if a single object, else None.
        """
        direction = {
            # the direction dict:
            "-x": (0, 0, (-1, 1, 1)),
            #  first index: axis direction: 0=negative axis, 1=positive.
            "x": (1, 0, (-1, 1, 1)),
            #    second index: axis_as_int: 0=x, 1=y, 2=z
            "-y": (0, 1, (1, -1, 1)),
            #   remaining three are (x, y, z) scale values. #Used only when scaling an instance.
            "y": (1, 1, (1, -1, 1)),
            "-z": (0, 2, (1, 1, -1)),
            "z": (1, 2, (1, 1, -1)),
        }

        axis = axis.lower()  # assure case.
        axisDirection, axis_as_int, scale = direction[axis]
        # ex. (1, 5, (1, 1,-1)) broken down as: axisDirection=1, axis_as_int=5, scale: (x=1, y=1, z=-1)

        if not objects:
            objects = pm.ls(sl=1)
            if not objects:
                self.sb.message_box(
                    "<b>Nothing selected.<b><br>Operation requires at least one selected polygon object."
                )
                return

        # pm.undoInfo(openChunk=1)
        for obj in pm.ls(objects, objectsOnly=1):
            if deleteHistory:
                pm.mel.BakeNonDefHistory(obj)

            if cutMesh:
                self.sb.edit.slots.delete_along_axis(
                    obj, axis
                )  # delete mesh faces that fall inside the specified axis.

            if instance:  # create instance and scale negatively
                # bt_convertToMirrorInstanceMesh(0); #x=0, y=1, z=2, -x=3, -y=4, -z=5
                inst = pm.instance(obj)
                pm.xform(
                    inst, scale=scale
                )  # pm.scale(z,x,y, pivot=(0,0,0), relative=1) #swap the xyz values to transform the instanced node
                return inst if len(objects) == 1 else inst

            else:  # mirror
                print("axis:", axis_as_int)
                polyMirrorFaceNode = pm.ls(
                    pm.polyMirrorFace(
                        obj,
                        axis=axis_as_int,
                        axisDirection=axisDirection,
                        mirrorAxis=axisPivot,
                        mergeMode=mergeMode,
                        mirrorPosition=0,
                        mergeThresholdType=1,
                        mergeThreshold=mergeThreshold,
                        smoothingAngle=30,
                        flipUVs=0,
                        ch=1,
                    )
                )[
                    0
                ]  # mirrorPosition x, y, z - This flag specifies the position of the custom mirror axis plane

                if not merge:
                    polySeparateNode = pm.ls(pm.polySeparate(obj, uss=1, inp=1))[2]

                    pm.connectAttr(
                        polyMirrorFaceNode.firstNewFace,
                        polySeparateNode.startFace,
                        force=True,
                    )
                    pm.connectAttr(
                        polyMirrorFaceNode.lastNewFace,
                        polySeparateNode.endFace,
                        force=True,
                    )

        if deleteOriginal and not merge:
            for obj in objects:
                pm.delete(obj)
        try:
            if len(objects) == 1:
                return polyMirrorFaceNode
        except AttributeError:
            return None
        # pm.undoInfo(closeChunk=1)


# --------------------------------------------------------------------------------------------

# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated:


# if axis=='X': #'x'
#           axisDirection = 0 #positive axis
#           axis_ = 0 #axis
#           x=-1; y=1; z=1 #scale values

#       elif axis=='-X': #'-x'
#           axisDirection = 1 #negative axis
#           axis_ = 1 #0=-x, 1=x, 2=-y, 3=y, 4=-z, 5=z
#           x=-1; y=1; z=1 #if instance: used to negatively scale

#       elif axis=='Y': #'y'
#           axisDirection = 0
#           axis_ = 2
#           x=1; y=-1; z=1

#       elif axis=='-Y': #'-y'
#           axisDirection = 1
#           axis_ = 3
#           x=1; y=-1; z=1

#       elif axis=='Z': #'z'
#           axisDirection = 0
#           axis_ = 4
#           x=1; y=1; z=-1

#       elif axis=='-Z': #'-z'
#           axisDirection = 1
#           axis_ = 5
#           x=1; y=1; z=-1

# def chk000(self, *args, **kwargs):
#   '''
#   Delete: Negative Axis. Set Text Mirror Axis
#   '''
#   axis = "X"
#   if self.sb.mirror.chk002.isChecked():
#       axis = "Y"
#   if self.sb.mirror.chk003.isChecked():
#       axis = "Z"
#   if self.sb.mirror.chk000.isChecked():
#       axis = '-'+axis
#   self.sb.mirror.tb000.setText('Mirror '+axis)
#   self.sb.mirror.tb003.setText('Delete '+axis)


# #set check states
# def chk000(self, *args, **kwargs):
#   '''
#   Delete: X Axis
#   '''
#   self.sb.toggle_widgets(setUnChecked='chk002,chk003')
#   axis = "X"
#   if self.sb.mirror.chk000.isChecked():
#       axis = '-'+axis
#   self.sb.mirror.tb000.setText('Mirror '+axis)
#   self.sb.mirror.tb003.setText('Delete '+axis)


# def chk002(self, *args, **kwargs):
#   '''
#   Delete: Y Axis
#   '''
#   self.sb.toggle_widgets(setUnChecked='chk001,chk003')
#   axis = "Y"
#   if self.sb.mirror.chk000.isChecked():
#       axis = '-'+axis
#   self.sb.mirror.tb000.setText('Mirror '+axis)
#   self.sb.mirror.tb003.setText('Delete '+axis)


# def chk003(self, *args, **kwargs):
#   '''
#   Delete: Z Axis
#   '''
#   self.sb.toggle_widgets(setUnChecked='chk001,chk002')
#   axis = "Z"
#   if self.sb.mirror.chk000.isChecked():
#       axis = '-'+axis
#   self.sb.mirror.tb000.setText('Mirror '+axis)
#   self.sb.mirror.tb003.setText('Delete '+axis)


# def chk005(self, *args, **kwargs):
# '''
# Mirror: Cut
# '''
# keep menu and submenu in sync:
# if self.mirror_submenu.chk005.isChecked():
#   self.sb.toggle_widgets(setChecked='chk005')
# else:
#   self.sb.toggle_widgets(setUnChecked='chk005')
