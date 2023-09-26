# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Rigging(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def cmb001_init(self, widget):
        """ """
        items = ["Joints", "Locator", "IK Handle", "Lattice", "Cluster"]
        widget.add(items, header="Create")

    def tb000_init(self, widget):
        """ """
        scale_joint_value = pm.jointDisplayScale(q=True)
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.5, 2],
            setValue=scale_joint_value,
            setToolTip="Global display scale for the selected type.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Joints",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Display Joints.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="IK",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Display IK.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="IK\\FK",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Display IK\\FK.",
        )

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Align world",
            setObjectName="chk003",
            setToolTip="Align joints with the worlds transform.",
        )

    def tb002_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Template Child",
            setObjectName="chk004",
            setChecked=False,
            setToolTip="Template child object(s) after parenting.",
        )

    def tb003_init(self, widget):
        """ """
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Locator Scale: ",
            setObjectName="s001",
            set_limits=[0, 1000, 1, 3],
            setValue=1,
            setToolTip="The scale of the locator.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Group Suffix:",
            setText="_GRP",
            setObjectName="t002",
            setToolTip="A string appended to the end of the created group's name.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Locator Suffix:",
            setText="",
            setObjectName="t000",
            setToolTip="A string appended to the end of the created locator's name.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Geometry Suffix:",
            setText="",
            setObjectName="t001",
            setToolTip="A string appended to the end of the existing geometry's name.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Strip Suffix",
            setObjectName="chk016",
            setToolTip="Strip any of preexisting suffixes from the group name before appending the new ones.\nA suffix is defined as anything trailing an underscore.\nAny user-defined suffixes are stripped by default.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Strip Digits",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Strip any trailing numeric characters from the name.\nIf the resulting name is not unique, maya will append a trailing digit.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Parent",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Parent to object to the locator.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Freeze transforms on the locator.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Bake Child Pivot",
            setObjectName="chk011",
            setChecked=True,
            setToolTip="Bake pivot positions on the child object.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Lock Child Translate",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Lock the translate values of the child object.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Lock Child Rotation",
            setObjectName="chk008",
            setChecked=True,
            setToolTip="Lock the rotation values of the child object.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Lock Child Scale",
            setObjectName="chk009",
            setToolTip="Lock the scale values of the child object.",
        )

    def tb004_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk012",
            setChecked=False,
            setToolTip="",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk013",
            setChecked=False,
            setToolTip="",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk014",
            setChecked=False,
            setToolTip="",
        )
        self.sb.connect_multi(
            widget.menu,
            "chk012-14",
            "toggled",
            [
                lambda state: widget.setText(
                    "Lock Attributes"
                    if any(
                        (
                            widget.menu.chk012.isChecked(),
                            widget.menu.chk013.isChecked(),
                            widget.menu.chk014.isChecked(),
                        )
                    )
                    else "Unlock Attributes"
                ),
                lambda state: widget.setText(
                    "Lock Transforms"
                    if any(
                        (
                            widget.menu.chk012.isChecked(),
                            widget.menu.chk013.isChecked(),
                            widget.menu.chk014.isChecked(),
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
        # init global joint display size
        widget.ui.tb000.menu.s000.setValue(pm.jointDisplayScale(q=True))

    def chk001(self, state, widget):
        """Scale IK"""
        # init IK handle display size
        widget.ui.tb000.menu.s000.setValue(pm.ikHandleDisplayScale(q=True))

    def chk002(self, state, widget):
        """Scale IK/FK"""
        # init IKFK display size
        widget.ui.tb000.menu.s000.setValue(pm.jointDisplayScale(q=True, ikfk=1))

    def s000(self, value, widget):
        """Scale Joint/IK/FK"""
        if widget.ui.tb000.menu.chk000.isChecked():
            pm.jointDisplayScale(value)  # set global joint display size
        elif widget.ui.tb000.menu.chk001.isChecked():
            pm.ikHandleDisplayScale(value)  # set global IK handle display size
        else:  # widget.ui.chk002.isChecked():
            pm.jointDisplayScale(value, ikfk=1)  # set global IKFK display size

    def tb000(self, widget):
        """Toggle Display Local Rotation Axes"""
        joints = pm.ls(type="joint")  # get all scene joints

        if not joints:  # if no joints in the scene
            self.sb.message_box("No joints found in the scene.")
            return  # exit the function

        state = pm.toggle(joints[0], q=True, localAxis=1)
        toggle = widget.menu.isChecked() != state

        if toggle:
            try:
                pm.toggle(joints, localAxis=1)  # set display off
            except Exception as e:
                print(f"An error occurred while toggling local axes: {e}")

        self.sb.message_box(f"Display Local Rotation Axes:<hl>{state}</hl>")

    def tb001(self, widget):
        """Orient Joints"""
        orientJoint = "xyz"  # orient joints
        alignWorld = widget.menu.chk003.isChecked()

        if alignWorld:
            orientJoint = "none"  # orient joint to world

        joints = pm.ls(type="joint", sl=True)  # get selected joints

        if not joints:  # if no joints are selected
            joints = pm.ls(type="joint")  # get all joints in the scene
            if not joints:  # if no joints in the scene
                self.sb.message_box("No joints found.")
                return  # exit the function
        try:
            for joint in joints:
                pm.joint(
                    joint, edit=1, orientJoint=orientJoint, zeroScaleOrient=1, ch=1
                )
        except Exception as e:
            print(f"An error occurred while orienting joints: {e}")

    def tb002(self, widget):
        """Constraint: Parent"""
        template = widget.menu.chk004.isChecked()
        objects = pm.ls(sl=1, objectsOnly=1)

        for obj in objects[:-1]:
            pm.parentConstraint(obj, objects[:-1], maintainOffset=1, weight=1)

            if template:
                if not pm.toggle(obj, template=1, q=True):
                    pm.toggle(obj, template=1, q=True)

    @mtk.undo
    def tb003(self, widget):
        """Create Locator at Selection"""
        grp_suffix = widget.menu.t002.text()
        loc_suffix = widget.menu.t000.text()
        obj_suffix = widget.menu.t001.text()
        parent = widget.menu.chk006.isChecked()
        freeze_transforms = widget.menu.chk010.isChecked()
        bake_child_pivot = widget.menu.chk011.isChecked()
        scale = widget.menu.s001.value()
        strip_digits = widget.menu.chk005.isChecked()
        strip_suffix = widget.menu.chk016.isChecked()
        lock_translate = widget.menu.chk007.isChecked()
        lock_rotation = widget.menu.chk008.isChecked()
        lock_scale = widget.menu.chk009.isChecked()

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
        lock_translate = widget.menu.chk012.isChecked()
        lock_rotation = widget.menu.chk013.isChecked()
        lock_scale = widget.menu.chk014.isChecked()

        sel = pm.ls(sl=True)
        mtk.set_attr_lock_state(
            sel, translate=lock_translate, rotate=lock_rotation, scale=lock_scale
        )

    def b000(self, widget):
        """Object Transform Limit Attributes"""
        selected_objects = pm.ls(selection=True, objectsOnly=True)

        if len(selected_objects) != 1:
            self.sb.message_box("Operation requires a single selected object.")
            return

        node = selected_objects[0]

        params = {
            "enableTranslationX": "etx",
            "translationX": "tx",
            "enableTranslationY": "ety",
            "translationY": "ty",
            "enableTranslationZ": "etz",
            "translationZ": "tz",
            "enableRotationX": "erx",
            "rotationX": "rx",
            "enableRotationY": "ery",
            "rotationY": "ry",
            "enableRotationZ": "erz",
            "rotationZ": "rz",
            "enableScaleX": "esx",
            "scaleX": "sx",
            "enableScaleY": "esy",
            "scaleY": "sy",
            "enableScaleZ": "esz",
            "scaleZ": "sz",
        }

        def set_transform_limit(node, attr, value):
            arg = params.get(attr)
            if arg is not None and isinstance(value, list) and len(value) == 2:
                kwargs = {arg: tuple(value)}
                pm.transformLimits(node, **kwargs)

        try:
            attrs = mtk.get_parameter_mapping(
                node, "transformLimits", list(params.keys())
            )
            window = self.sb.AttributeWindow(
                node,
                attrs,
                window_title=node.name(),
                set_attribute_func=set_transform_limit,
                allow_unsupported_types=True,
            )
            window.set_style(theme="dark")
            window.set_flags(WindowStaysOnTopHint=True)
            window.show()
        except Exception as e:
            print(f"An error occurred while getting parameter values: {e}")

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
        selected_objects = pm.ls(selection=True)

        if len(selected_objects) < 2:
            self.sb.message_box(
                "Please select two objects before applying a point constraint."
            )
            return

        source = selected_objects[0]
        target = selected_objects[1]

        try:
            pm.pointConstraint(source, target, offset=[0, 0, 0], weight=1)
        except Exception as e:
            print(f"An error occurred while applying the point constraint: {e}")

    def b007(self):
        """Constraint: Scale"""
        selected_objects = pm.ls(selection=True)

        if len(selected_objects) < 2:
            self.sb.message_box(
                "Please select two objects before applying a scale constraint."
            )
            return

        source = selected_objects[0]
        target = selected_objects[1]

        try:
            pm.scaleConstraint(source, target, offset=[1, 1, 1], weight=1)
        except Exception as e:
            print(f"An error occurred while applying the scale constraint: {e}")

    def b008(self):
        """Constraint: Orient"""
        selected_objects = pm.ls(selection=True)

        if len(selected_objects) < 2:
            self.sb.message_box(
                "Please select two objects before applying an orient constraint."
            )
            return

        source = selected_objects[0]
        target = selected_objects[1]

        try:
            pm.orientConstraint(source, target, offset=[0, 0, 0], weight=1)
        except Exception as e:
            print(f"An error occurred while applying the orient constraint: {e}")

    def b009(self):
        """Constraint: Aim"""
        selected_objects = pm.ls(selection=True)

        if len(selected_objects) < 2:
            self.sb.message_box(
                "Please select two objects before applying an aim constraint."
            )
            return

        source = selected_objects[0]
        target = selected_objects[1]

        try:
            pm.aimConstraint(
                source,
                target,
                offset=[0, 0, 0],
                weight=1,
                aimVector=[1, 0, 0],
                upVector=[0, 1, 0],
                worldUpType="vector",
                worldUpVector=[0, 1, 0],
            )
        except Exception as e:
            print(f"An error occurred while applying the aim constraint: {e}")

    def b010(self):
        """Constraint: Pole Vector"""
        selected_objects = pm.ls(selection=True)

        if len(selected_objects) < 2:
            self.sb.message_box(
                "Please select two objects before applying a pole vector constraint."
            )
            return

        source = selected_objects[0]
        target = selected_objects[1]

        try:
            pm.poleVectorConstraint(source, target, offset=[0, 0, 0], weight=1)
        except Exception as e:
            print(f"An error occurred while applying the pole vector constraint: {e}")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
