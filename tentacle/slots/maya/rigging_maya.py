# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Rigging_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def cmb001_init(self, widget):
        """ """
        items = ["Joints", "Locator", "IK Handle", "Lattice", "Cluster"]
        widget.addItems_(items, "Create")

    def tb000_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Joints",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Display Joints.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="IK",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Display IK.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="IK\\FK",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Display IK\\FK.",
        )
        widget.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.5, 2],
            setValue=1.0,
            setToolTip="Global Display Scale for the selected type.",
        )
        self.chk000(None, widget)  # init scale joint value

    def tb001_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Align world",
            setObjectName="chk003",
            setToolTip="Align joints with the worlds transform.",
        )

    def tb002_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Template Child",
            setObjectName="chk004",
            setChecked=False,
            setToolTip="Template child object(s) after parenting.",
        )

    def tb003_init(self, widget):
        """ """
        widget.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Locator Scale: ",
            setObjectName="s001",
            set_limits=[0, 1000, 1, 3],
            setValue=1,
            setToolTip="The scale of the locator.",
        )
        widget.option_menu.add(
            "QLineEdit",
            setPlaceholderText="Group Suffix:",
            setText="_GRP",
            setObjectName="t002",
            setToolTip="A string appended to the end of the created group's name.",
        )
        widget.option_menu.add(
            "QLineEdit",
            setPlaceholderText="Locator Suffix:",
            setText="",
            setObjectName="t000",
            setToolTip="A string appended to the end of the created locator's name.",
        )
        widget.option_menu.add(
            "QLineEdit",
            setPlaceholderText="Geometry Suffix:",
            setText="",
            setObjectName="t001",
            setToolTip="A string appended to the end of the existing geometry's name.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Strip Suffix",
            setObjectName="chk016",
            setToolTip="Strip any of preexisting suffixes from the group name before appending the new ones.\nA suffix is defined as anything trailing an underscore.\nAny user-defined suffixes are stripped by default.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Strip Digits",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Strip any trailing numeric characters from the name.\nIf the resulting name is not unique, maya will append a trailing digit.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Parent",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Parent to object to the locator.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Freeze transforms on the locator.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Bake Child Pivot",
            setObjectName="chk011",
            setChecked=True,
            setToolTip="Bake pivot positions on the child object.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Lock Child Translate",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Lock the translate values of the child object.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Lock Child Rotation",
            setObjectName="chk008",
            setChecked=True,
            setToolTip="Lock the rotation values of the child object.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Lock Child Scale",
            setObjectName="chk009",
            setToolTip="Lock the scale values of the child object.",
        )

    def tb004_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk012",
            setChecked=False,
            setToolTip="",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk013",
            setChecked=False,
            setToolTip="",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk014",
            setChecked=False,
            setToolTip="",
        )
        self.sb.connect_multi(
            (
                widget.option_menu.chk012,
                widget.option_menu.chk013,
                widget.option_menu.chk014,
            ),
            "toggled",
            [
                lambda state: self.sb.rigging.widget.setText(
                    "Lock Attributes"
                    if any(
                        (
                            widget.option_menu.chk012.isChecked(),
                            widget.option_menu.chk013.isChecked(),
                            widget.option_menu.chk014.isChecked(),
                        )
                    )
                    else "Unlock Attributes"
                ),
                lambda state: self.sb.rigging_submenu.widget.setText(
                    "Lock Transforms"
                    if any(
                        (
                            widget.option_menu.chk012.isChecked(),
                            widget.option_menu.chk013.isChecked(),
                            widget.option_menu.chk014.isChecked(),
                        )
                    )
                    else "Unlock Attributes"
                ),
            ],
        )

    def cmb001(self, index, widget):
        """Create"""
        if index > 0:
            text = widget.items[index]
            if text == "Joints":
                pm.setToolTo("jointContext")  # create joint tool
            elif text == "Locator":
                pm.spaceLocator(p=[0, 0, 0])  # locator
            elif text == "IK Handle":
                pm.setToolTo("ikHandleContext")  # create ik handle
            elif text == "Lattice":  # create lattice
                pm.lattice(divisions=[2, 5, 2], objectCentered=1, ldv=[2, 2, 2])
            elif text == "Cluster":
                pm.mel.eval("CreateCluster;")  # create cluster
            widget.setCurrentIndex(0)

    def chk000(self, state, widget):
        """Scale Joint"""
        self.sb.toggle_widgets(widget.option_menu, setUnChecked="chk001-2")
        # init global joint display size
        self.sb.rigging.tb000.option_menu.s000.setValue(pm.jointDisplayScale(q=True))

    def chk001(self, state, widget):
        """Scale IK"""
        self.sb.toggle_widgets(widget.option_menu, setUnChecked="chk000, chk002")
        # init IK handle display size
        self.sb.rigging.tb000.option_menu.setValue(pm.ikHandleDisplayScale(q=True))

    def chk002(self, state, widget):
        """Scale IK/FK"""
        self.sb.toggle_widgets(widget.option_menu, setUnChecked="chk000-1")
        # init IKFK display size
        self.sb.rigging.tb000.option_menu.setValue(pm.jointDisplayScale(q=True, ikfk=1))

    def s000(self, value, widget):
        """Scale Joint/IK/FK"""
        value = self.sb.rigging.tb000.option_menu.value()

        if self.sb.rigging.chk000.isChecked():
            pm.jointDisplayScale(value)  # set global joint display size
        elif self.sb.rigging.chk001.isChecked():
            pm.ikHandleDisplayScale(value)  # set global IK handle display size
        else:  # self.sb.rigging.chk002.isChecked():
            pm.jointDisplayScale(value, ikfk=1)  # set global IKFK display size

    def tb000(self, widget):
        """Toggle Display Local Rotation Axes"""
        joints = pm.ls(type="joint")  # get all scene joints
        state = pm.toggle(joints[0], q=True, localAxis=1)

        if widget.option_menu.isChecked():
            if not state:
                toggle = True
        else:
            if state:
                toggle = True

        if toggle:
            pm.toggle(joints, localAxis=1)  # set display off

        mtk.viewport_message("Display Local Rotation Axes:<hl>" + str(state) + "</hl>")

    def tb001(self, widget):
        """Orient Joints"""
        orientJoint = "xyz"  # orient joints
        alignWorld = widget.option_menu.chk003.isChecked()

        if alignWorld:
            orientJoint = "none"  # orient joint to world

        pm.joint(edit=1, orientJoint=orientJoint, zeroScaleOrient=1, ch=1)

    def tb002(self, widget):
        """Constraint: Parent"""
        template = widget.option_menu.chk004.isChecked()
        objects = pm.ls(sl=1, objectsOnly=1)

        for obj in objects[:-1]:
            pm.parentConstraint(obj, objects[:-1], maintainOffset=1, weight=1)

            if template:
                if not pm.toggle(obj, template=1, q=True):
                    pm.toggle(obj, template=1, q=True)

    @mtk.undo
    def tb003(self, widget):
        """Create Locator at Selection"""
        grp_suffix = widget.option_menu.t002.text()
        loc_suffix = widget.option_menu.t000.text()
        obj_suffix = widget.option_menu.t001.text()
        parent = widget.option_menu.chk006.isChecked()
        freeze_transforms = widget.option_menu.chk010.isChecked()
        bake_child_pivot = widget.option_menu.chk011.isChecked()
        scale = widget.option_menu.s001.value()
        strip_digits = widget.option_menu.chk005.isChecked()
        strip_suffix = widget.option_menu.chk016.isChecked()
        lock_translate = widget.option_menu.chk007.isChecked()
        lock_rotation = widget.option_menu.chk008.isChecked()
        lock_scale = widget.option_menu.chk009.isChecked()

        selection = pm.ls(selection=True)
        if not selection:
            return mtk.create_locator(scale=scale)

        mtk.create_locator_at_object(
            selection,
            parent=parent,
            freeze_transforms=freeze_transforms,
            bake_child_pivot=bake_child_pivot,
            scale=scale,
            grp_suffix=grp_suffix,
            loc_suffix=loc_suffix,
            obj_suffix=obj_suffix,
            strip_digits=strip_digits,
            strip_suffix=strip_suffix,
            lock_translate=lock_translate,
            lock_rotation=lock_rotation,
            lock_scale=lock_scale,
        )

    def tb004(self, widget):
        """Lock/Unlock Attributes"""
        lock_translate = widget.option_menu.chk012.isChecked()
        lock_rotation = widget.option_menu.chk013.isChecked()
        lock_scale = widget.option_menu.chk014.isChecked()

        sel = pm.ls(sl=True)
        mtk.set_attr_lock_state(
            sel, translate=lock_translate, rotate=lock_rotation, scale=lock_scale
        )

    @SlotsMaya.hide_main
    def b000(self):
        """Object Transform Limit Attributes"""
        node = pm.ls(sl=1, objectsOnly=1)
        if not node:
            self.sb.message_box("Operation requires a single selected object.")
            return

        params = [
            "enableTranslationX",
            "translationX",
            "enableTranslationY",
            "translationY",
            "enableTranslationZ",
            "translationZ",
            "enableRotationX",
            "rotationX",
            "enableRotationY",
            "rotationY",
            "enableRotationZ",
            "rotationZ",
            "enableScaleX",
            "scaleX",
            "enableScaleY",
            "scaleY",
            "enableScaleZ",
            "scaleZ",
        ]

        attrs = mtk.get_parameter_values(node, "transformLimits", params)
        self.setAttributeWindow(
            node, fn=SlotsMaya.set_parameter_values, fn_args="transformLimits", **attrs
        )

    def b001(self):
        """Connect Joints"""
        pm.connectJoint(cm=1)

    def b002(self):
        """Insert Joint Tool"""
        pm.setToolTo("insertJointContext")  # insert joint tool

    def b003(self):
        """Remove Locator"""
        selection = pm.ls(selection=True)
        mtk.remove_locator(selection)

    def b004(self):
        """Reroot"""
        pm.reroot()  # re-root joints

    def b006(self):
        """Constraint: Point"""
        pm.pointConstraint(offset=[0, 0, 0], weight=1)

    def b007(self):
        """Constraint: Scale"""
        pm.scaleConstraint(offset=[1, 1, 1], weight=1)

    def b008(self):
        """Constraint: Orient"""
        pm.orientConstraint(offset=[0, 0, 0], weight=1)

    def b009(self):
        """Constraint: Aim"""
        pm.aimConstraint(
            offset=[0, 0, 0],
            weight=1,
            aimVector=[1, 0, 0],
            upVector=[0, 1, 0],
            worldUpType="vector",
            worldUpVector=[0, 1, 0],
        )

    def b010(self):
        """Constraint: Pole Vector"""
        pm.orientConstraint(offset=[0, 0, 0], weight=1)


# --------------------------------------------------------------------------------------------

# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated:

# def createLocatorAtSelection(suffix='_LOC', strip_digits=False, strip='', scale=1, parent=False, freezeChildTransforms=False, bake_child_pivot=False, lock_translate=False, lock_rotation=False, lock_scale=False, _fullPath=False):
#   '''Create locators with the same transforms as any selected object(s).
#   If there are vertices selected it will create a locator at the center of the selected vertices bounding box.

#   Parameters:
#       suffix (str): A string appended to the end of the created locators name. (default: '_LOC') '_LOC#'
#       strip_digits (bool): Strip numeric characters from the string. If the resulting name is not unique, maya will append a trailing digit. (default=False)
#       strip (str): Strip a specific character set from the locator name. The locators name is based off of the selected objects name. (default=None)
#       scale (float) = The scale of the locator. (default=1)
#       parent (bool): Parent to object to the locator. (default=False)
#       freezeChildTransforms (bool): Freeze transforms on the child object. (Valid only with parent flag) (default=False)
#       bake_child_pivot (bool): Bake pivot positions on the child object. (Valid only with parent flag) (default=False)
#       lock_translate (bool): Lock the translate values of the child object. (default=False)
#       lock_rotation (bool): Lock the rotation values of the child object. (default=False)
#       lock_scale (bool): Lock the scale values of the child object. (default=False)
#       _fullPath (bool): Internal use only (recursion). Use full path names for Dag objects. This can prevent naming conflicts when creating the locator. (default=False)

#   Example:
#       createLocatorAtSelection(strip='_GEO', suffix='', strip_digits=True, scale=10, parent=True, lock_translate=True, lock_rotation=True)
#   '''
#   import pymel.core as pm
#   sel = pm.ls(selection=True, long=_fullPath, objectsOnly=True)
#   sel_verts = pm.filterExpand(sm=31)

#   if not sel:
#       error = '# Error: Nothing Selected. #'
#       print (error)
#       return error

#   def _formatName(name, strip_digits=strip_digits, strip=strip, suffix=suffix):
#       if strip_digits:
#           name_ = ''.join([i for i in name if not i.isdigit()])
#       return name_.replace(strip, '')+suffix

#   def _parent(obj, loc, parent=parent, freezeChildTransforms=freezeChildTransforms, bake_child_pivot=bake_child_pivot):
#       if parent: #parent
#           if freezeChildTransforms:
#               pm.makeIdentity(obj, apply=True, t=1, r=1, s=1, normal=2) #normal parameter: 1=the normals on polygonal objects will be frozen. 2=the normals on polygonal objects will be frozen only if its a non-rigid transformation matrix.
#           if bake_child_pivot:
#               pm.select(obj); pm.mel.BakeCustomPivot() #bake pivot on child object.
#           objParent = pm.listRelatives(obj, parent=1)
#           pm.parent(obj, loc)
#           pm.parent(loc, objParent)

#   def _lockChildAttributes(obj, lock_translate=lock_translate, lock_rotation=lock_rotation, lock_scale=lock_scale):
#       try: #split in case of long name to get the obj attribute.  ex. 'f15e_door_61_bellcrank|Bolt_GEO.tx' to: Bolt_GEO.tx
#           setAttrs = lambda attrs: [pm.setAttr('{}.{}'.format(obj.split('|')[-1], attr), lock=True) for attr in attrs]
#       except: #if obj is type object:
#           setAttrs = lambda attrs: [pm.setAttr('{}.{}'.format(obj, attr), lock=True) for attr in attrs]

#       if lock_translate: #lock translation values
#           setAttrs(('tx','ty','tz'))

#       if lock_rotation: #lock rotation values
#           setAttrs(('rx','ry','rz'))

#       if lock_scale: #lock scale values
#           setAttrs(('sx','sy','sz'))

#   _fullPath = lambda: self.createLocatorAtSelection(suffix=suffix, strip_digits=strip_digits,
#               strip=strip, parent=parent, scale=scale, _fullPath=True,
#               lock_translate=lock_translate, lock_rotation=lock_rotation, lock_scale=lock_scale)

#   if sel_verts: #vertex selection

#       objName = sel_verts[0].split('.')[0]
#       locName = _formatName(objName, strip_digits, strip, suffix)

#       loc = pm.spaceLocator(name=locName)
#       if not any([loc, _fullPath]): #if locator creation fails; try again using the objects full path name.
#           _fullPath()

#       pm.scale(scale, scale, scale)

#       bb = pm.exactWorldBoundingBox(sel_verts)
#       pos = ((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2)
#       pm.move(pos[0], pos[1], pos[2], loc)

#       _parent(objName, loc)
#       _lockChildAttributes(objName)

#   else: #object selection
#       for obj in sel:

#           objName = obj.name()
#           locName = _formatName(objName, strip_digits, strip, suffix)

#           loc = pm.spaceLocator(name=locName)
#           if not any([loc, _fullPath]): #if locator creation fails; try again using the objects fullpath name.
#               _fullPath()

#           pm.scale(scale, scale, scale)

#           tempConst = pm.parentConstraint(obj, loc, mo=False)
#           pm.delete(tempConst)
#           pm.select(clear=True)

#           _parent(obj, loc)
#           _lockChildAttributes(objName)
