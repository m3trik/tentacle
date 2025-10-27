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

    def header_init(self, widget):
        """ """
        widget.menu.setTitle("Rigging")
        widget.menu.add(
            "QPushButton",
            setText="Rebind Skin Clusters",
            setObjectName="b020",
            setToolTip="Rebinds skinClusters on the selected meshe(s), preserving weights, bind pose.",
        )
        widget.menu.b020.clicked.connect(
            lambda: mtk.rebind_skin_clusters(pm.selected())
        )

    def cmb001_init(self, widget):
        """ """
        items = ["Joints", "Locator", "IK Handle", "Lattice", "Cluster"]
        widget.add(items, header="Utility Node:")

    def cmb001(self, index, widget):
        """Create"""
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

    def cmb002_init(self, widget):
        """ """
        items = ["Tube Rig", "Wheel Rig"]
        widget.add(items, header="Quick Rig:")

    def cmb002(self, index, widget):
        """Quick Rig"""
        text = widget.items[index]
        if text == "Tube Rig":
            ui = mtk.UiManager.instance(self.sb).get("tube_rig")
            ui.show(pos="cursor", app_exec=True)
        elif text == "Wheel Rig":
            ui = mtk.UiManager.instance(self.sb).get("wheel_rig")
            ui.show(pos="cursor", app_exec=True)

    def chk000(self, state, widget):
        """Scale Joint"""
        # init global joint display size
        widget.ui.tb000.option_box.menu.s000.setValue(pm.jointDisplayScale(q=True))

    def chk001(self, state, widget):
        """Scale IK"""
        # init IK handle display size
        widget.ui.tb000.option_box.menu.s000.setValue(pm.ikHandleDisplayScale(q=True))

    def chk002(self, state, widget):
        """Scale IK/FK"""
        # init IKFK display size
        widget.ui.tb000.option_box.menu.s000.setValue(
            pm.jointDisplayScale(q=True, ikfk=1)
        )

    def s000(self, value, widget):
        """Scale Joint/IK/FK"""
        if widget.ui.tb000.option_box.menu.chk000.isChecked():
            pm.jointDisplayScale(value)  # set global joint display size
        elif widget.ui.tb000.option_box.menu.chk001.isChecked():
            pm.ikHandleDisplayScale(value)  # set global IK handle display size
        else:  # widget.ui.chk002.isChecked():
            pm.jointDisplayScale(value, ikfk=1)  # set global IKFK display size

    def tb000_init(self, widget):
        """ """
        scale_joint_value = pm.jointDisplayScale(q=True)
        widget.option_box.menu.setTitle("Display Local Rotation Axes")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.5, 2],
            setValue=scale_joint_value,
            setToolTip="Global display scale for the selected type.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Joints",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Display Joints.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="IK",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Display IK.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="IK\\FK",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Display IK\\FK.",
        )

    def tb000(self, widget):
        """Toggle Display Local Rotation Axes"""
        joints = pm.ls(type="joint")  # get all scene joints

        if not joints:  # if no joints in the scene
            self.sb.message_box("No joints found in the scene.")
            return  # exit the function

        state = pm.toggle(joints[0], q=True, localAxis=1)
        toggle = widget.option_box.menu.chk000.isChecked()

        if toggle:
            try:
                pm.toggle(joints, localAxis=1)  # set display off
            except Exception as e:
                print(f"An error occurred while toggling local axes: {e}")

        self.sb.message_box(f"Display Local Rotation Axes:<hl>{state}</hl>")

    def tb001_init(self, widget):
        """ """
        widget.option_box.menu.setTitle("Create Constraint Switch")
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Switch Name:",
            setText="switch",
            setObjectName="t003",
            setToolTip="The name of the switch attribute to create.",
        )
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Anchor Name:",
            setText="",
            setObjectName="t004",
            setToolTip="Create a helper locator to allow anchoring the constraint to world origin.\nIf a previous anchor exists of the same name, it will be reused.\nLeave blank to not create an anchor.\n(default: empty string)",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Weighted",
            setObjectName="chk003",
            setChecked=False,
            setToolTip="Create a weighted switch instead of a simple one.",
        )

    def tb001(self, widget):
        """Create Constraint Switch"""
        sel = pm.selected(flatten=True)

        switch_name = widget.option_box.menu.t003.text()
        weighted = widget.option_box.menu.chk003.isChecked()
        anchor_name = widget.option_box.menu.t004.text()

        mtk.connect_switch_to_constraint(
            constraint_node=sel[0] if sel else None,
            attr_name=switch_name,
            weighted=weighted,
            overwrite_existing=True,
            anchor=anchor_name,
        )

    def tb003_init(self, widget):
        """ """
        widget.option_box.menu.setTitle("Create Locator")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Locator Scale: ",
            setObjectName="s001",
            set_limits=[0, 1000, 1, 3],
            setValue=1,
            setToolTip="The scale of the locator.",
        )
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Group Suffix:",
            setText="_GRP",
            setObjectName="t002",
            setToolTip="A string appended to the end of the created group's name.",
        )
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Locator Suffix:",
            setText="_LOC",
            setObjectName="t000",
            setToolTip="A string appended to the end of the created locator's name.",
        )
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Geometry Suffix:",
            setText="_GEO",
            setObjectName="t001",
            setToolTip="A string appended to the end of the existing geometry's name.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Strip Digits",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Strip any trailing numeric characters from the name.\nIf the resulting name is not unique, maya will append a trailing digit.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lock Child Translate",
            setObjectName="chk007",
            setChecked=False,
            setToolTip="Lock the translate values of the child object.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lock Child Rotation",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Lock the rotation values of the child object.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lock Child Scale",
            setObjectName="chk009",
            setToolTip="Lock the scale values of the child object.",
        )

    @mtk.undoable
    def tb003(self, widget):
        """Create Locator at Selection"""
        grp_suffix = widget.option_box.menu.t002.text()
        loc_suffix = widget.option_box.menu.t000.text()
        obj_suffix = widget.option_box.menu.t001.text()
        loc_scale = widget.option_box.menu.s001.value()
        strip_digits = widget.option_box.menu.chk005.isChecked()
        lock_translate = widget.option_box.menu.chk007.isChecked()
        lock_rotation = widget.option_box.menu.chk008.isChecked()
        lock_scale = widget.option_box.menu.chk009.isChecked()

        selection = pm.selected()
        if not selection:
            return mtk.create_locator(scale=loc_scale)

        mtk.create_locator_at_object(
            selection,
            loc_scale=loc_scale,
            grp_suffix=grp_suffix,
            loc_suffix=loc_suffix,
            obj_suffix=obj_suffix,
            strip_digits=strip_digits,
            lock_translate=lock_translate,
            lock_rotation=lock_rotation,
            lock_scale=lock_scale,
        )

    def b003(self):
        """Remove Locator"""
        selection = pm.ls(selection=True)
        mtk.remove_locator(selection)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
