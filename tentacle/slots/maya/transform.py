# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Transform(SlotsMaya):
    """ """

    def __init__(self, *args, **kwargs):
        """ """
        super().__init__(*args, **kwargs)

        self.ui = self.sb.transform
        self.submenu = self.sb.transform_submenu

    def cmb002_init(self, widget):
        """ """
        items = [
            "Point to Point",
            "2 Points to 2 Points",
            "3 Points to 3 Points",
            "Align Objects",
            "Position Along Curve",
            "Align Tool",
            "Snap Together Tool",
        ]
        widget.add(items, header="Align To")

    def cmb002(self, index, widget):
        """Align To"""
        text = widget.items[index]
        if text == "Point to Point":
            pm.mel.SnapPointToPointOptions()  # performSnapPtToPt 1; Select any type of point object or component.
        elif text == "2 Points to 2 Points":
            pm.mel.Snap2PointsTo2PointsOptions()  # performSnap2PtTo2Pt 1; Select any type of point object or component.
        elif text == "3 Points to 3 Points":
            pm.mel.Snap3PointsTo3PointsOptions()  # performSnap3PtTo3Pt 1; Select any type of point object or component.
        elif text == "Align Objects":
            pm.mel.performAlignObjects(1)  # Align the selected objects.
        elif text == "Position Along Curve":
            pm.mel.PositionAlongCurve()  # Position selected objects along a selected curve.
        elif text == "Align Tool":
            pm.mel.SetAlignTool()  # setToolTo alignToolCtx; Align the selection to the last selected object.
        elif text == "Snap Together Tool":
            pm.mel.SetSnapTogetherToolOptions()  # setToolTo snapTogetherToolCtx; toolPropertyWindow;) Snap two objects together.

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QComboBox",
            addItems=["Min", "Mid", "Max"],
            setObjectName="cmb004",
            setToolTip="Choose which point of the bounding box to align to.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Move to Origin",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Move to origin (xyz 0,0,0).",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Center pivot on objects bounding box.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Reset the selected transform and all of its children down to the shape level.",
        )

    def tb000(self, widget):
        """Drop To Grid"""
        align = widget.menu.cmb004.currentText()
        origin = widget.menu.chk014.isChecked()
        center_pivot = widget.menu.chk016.isChecked()
        freeze_transforms = widget.menu.chk017.isChecked()

        objects = pm.ls(sl=1, objectsOnly=1)
        mtk.drop_to_grid(objects, align, origin, center_pivot, freeze_transforms)
        pm.select(objects)  # reselect the original selection.

    def tb002_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk032",
            setChecked=True,
            setToolTip="The translation will be changed to 0, 0, 0.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk033",
            setToolTip="The rotation will be changed to 0, 0, 0.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk034",
            setChecked=True,
            setToolTip="The scale factor will be changed to 1, 1, 1.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk035",
            setChecked=True,
            setToolTip="Move the objects pivot to the center of it's bounding box.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Store Transforms",
            setObjectName="chk037",
            setChecked=True,
            setToolTip="Store the original transforms as custom attributes.",
        )

    def tb002(self, widget):
        """Freeze Transformations"""
        selected_objects = pm.selected()

        if len(selected_objects) == 0:
            self.sb.message_box("Please select at least one object.")
            return

        translate = widget.menu.chk032.isChecked()
        rotate = widget.menu.chk033.isChecked()
        scale = widget.menu.chk034.isChecked()
        center_pivot = widget.menu.chk035.isChecked()
        store_transforms = widget.menu.chk037.isChecked()

        # Store original transforms if the option is checked
        if store_transforms:
            for obj in selected_objects:
                mtk.store_transforms(obj)

        if center_pivot:
            pm.xform(selected_objects, centerPivots=1)

        pm.makeIdentity(selected_objects, apply=True, t=translate, r=rotate, s=scale)

    def tb003_init(self, widget):
        """ """
        widget.menu.mode = "popup"
        widget.menu.setTitle("CONSTRAINTS")
        edge_constraint = pm.xformConstraint(q=True, type=1) == "edge"
        surface_constraint = pm.xformConstraint(q=True, type=1) == "surface"
        values = [
            ("chk024", "Contrain: Edge", edge_constraint),
            ("chk025", "Constain: Surface", surface_constraint),
            ("chk026", "Make Live", True),
        ]
        for name, text, state in values:
            widget.menu.add(
                "QCheckBox",
                setObjectName=name,
                setText=text,
                setChecked=state,
            )

        def update_text():
            state = any(w.isChecked() for w in widget.menu.get_items(self.sb.QCheckBox))
            widget.setText("Constrain: ON" if state else "Constrain: OFF")

        # Connecting signals to update_text method
        self.sb.connect_multi(widget.menu, "chk024-26", "toggled", update_text)

    def tb004_init(self, widget):
        """ """
        widget.menu.mode = "popup"
        widget.menu.setTitle("SNAP")
        widget.menu.add(
            self.sb.CheckBox,
            setObjectName="chk021",
            setText="Snap Move",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setObjectName="s021",
            setPrefix="Increment:",
            setValue=0,
            set_limits=[1, 1000, 1, 1],
            setDisabled=True,
        )
        widget.menu.add(
            self.sb.CheckBox,
            setObjectName="chk022",
            setText="Snap Scale",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setObjectName="s022",
            setPrefix="Increment:",
            setValue=0,
            set_limits=[1, 1000, 1, 1],
            setDisabled=True,
        )
        widget.menu.add(
            self.sb.CheckBox,
            setObjectName="chk023",
            setText="Snap Rotate",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setObjectName="s023",
            setPrefix="Degrees:",
            setValue=0,
            set_limits=[1.40625, 360, 0.40625, 5],
            setDisabled=True,
        )
        # Set the values
        widget.menu.s021.setValue(pm.manipMoveContext("Move", q=True, snapValue=True))
        widget.menu.s022.setValue(pm.manipScaleContext("Scale", q=True, snapValue=True))
        widget.menu.s023.setValue(pm.manipRotateContext("Rotate", q=1, snapValue=True))

        def update_text():
            state = any(w.isChecked() for w in widget.menu.get_items(self.sb.CheckBox))
            widget.setText("Snap: ON" if state else "Snap: OFF")

        # Connecting signals to update_text method
        self.sb.connect_multi(widget.menu, "chk021-23", "toggled", update_text)

    def tb005_init(self, widget):
        """Initialize Move To Menu"""
        widget.menu.setTitle("MOVE TO")

        widget.menu.add(
            "QCheckBox",
            setText="Move All To Last",
            setObjectName="chk036",
            setChecked=True,
            setToolTip="If checked, all selected objects will move to align with the last selected object.\nIf unchecked, the first object will move to the remaining selected objects' bounding box.",
        )

    @mtk.undo
    def tb005(self, widget):
        """Move To"""
        move_all_to_last = widget.menu.chk036.isChecked()

        sel = pm.ls(orderedSelection=True, transforms=True)
        if not len(sel) > 1:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least two selected objects."
            )
            return

        # Move all to last selected object's position
        if move_all_to_last:
            target = sel[-1]
            mtk.move_to(sel[:-1], target)
        else:  # Move first object to remaining selected objects' bounding box or pivot point
            target = sel[1:]
            mtk.move_to(sel[0], target)

        pm.select(sel)

    def chk021(self, state, widget):
        """Transform Tool Snap Settings: Move"""
        tb = self.ui.tb004
        tb.init_slot()
        tb.menu.s021.setEnabled(state)  # Enable/Disable based on the checked state
        self.setTransformSnap("move", state)

    def chk022(self, state, widget):
        """Transform Tool Snap Settings: Scale"""
        tb = self.ui.tb004
        tb.init_slot()
        tb.menu.s022.setEnabled(state)  # Enable/Disable based on the checked state
        self.setTransformSnap("scale", state)

    def chk023(self, state, widget):
        """Transform Tool Snap Settings: Rotate"""
        tb = self.ui.tb004
        tb.init_slot()
        tb.menu.s023.setEnabled(state)  # Enable/Disable based on the checked state
        self.setTransformSnap("rotate", state)

    def chk024(self, state, widget):
        """Transform Constraints: Edge"""
        tb = self.ui.tb003
        tb.init_slot()
        if state:
            pm.xformConstraint(type="edge")
        else:
            pm.xformConstraint(type="none")

    def chk025(self, state, widget):
        """Transform Contraints: Surface"""
        tb = self.ui.tb003
        tb.init_slot()
        if state:
            pm.xformConstraint(type="surface")
        else:
            pm.xformConstraint(type="none")

    def chk026(self, state, widget):
        """Transform Constraints: Make Live"""
        tb = self.ui.tb003
        tb.init_slot()

        selection = pm.ls(sl=1, objectsOnly=1, type="transform")
        if state and selection:
            pm.makeLive(selection[0])
        else:
            pm.makeLive(none=True)

    def s021(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipMoveContext("Move", edit=1, snapValue=value)
        # UV move context
        pm.texMoveContext("texMoveContext", edit=1, snapValue=value)

    def s022(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipScaleContext("Scale", edit=1, snapValue=value)
        # UV scale context
        pm.texScaleContext("texScaleContext", edit=1, snapValue=value)

    def s023(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipRotateContext("Rotate", edit=1, snapValue=value)
        # UV rotate context
        pm.texRotateContext("texRotateContext", edit=1, snapValue=value)

    def b000(self, widget):
        """Object Transform Attributes"""
        node = pm.ls(sl=1, objectsOnly=1)
        if not node:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires a single selected object."
            )
            return

        node = mtk.get_transform_node(node[0])
        params = [
            "translateX",
            "translateY",
            "translateZ",
            "rotateX",
            "rotateY",
            "rotateZ",
            "scaleX",
            "scaleY",
            "scaleZ",
        ]
        try:
            attrs = mtk.get_node_attributes(node, params, mapping=True)
            window = self.sb.AttributeWindow(
                node,
                attrs,
                window_title=node.name(),
                set_attribute_func=lambda obj, n, v: getattr(obj, n).set(v),
            )
            window.set_style(theme="dark")
            window.set_flags(WindowStaysOnTopHint=True)
            window.show()
        except Exception as e:
            print(f"An error occurred while getting parameter values: {e}")

    def b001(self):
        """Match Scale"""
        selection = pm.ls(orderedSelection=True, flatten=True)
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least two selected objects."
            )
            return

        frm = selection[0]
        to = selection[1:]

        mtk.match_scale(frm, to)

    def b002(self):
        """Un-Freeze Transforms"""
        mtk.restore_transforms(pm.selected())

        # Debug: Final state
        obj = pm.selected()
        print(
            f"Final state: {obj} - "
            f"Translate: {pm.xform(obj, query=True, translation=True, worldSpace=True)}, "
            f"Rotate: {pm.xform(obj, query=True, rotation=True, worldSpace=True)}, "
            f"RotatePivot: {pm.xform(obj, query=True, rotatePivot=True, worldSpace=True)}, "
            f"ScalePivot: {pm.xform(obj, query=True, scalePivot=True, worldSpace=True)}"
        )

    def setTransformSnap(self, ctx, state):
        """Set the transform tool's move, rotate, and scale snap states.

        Parameters:
                ctx (str): valid: 'move', 'scale', 'rotate'
                state (int): valid: 0=off, 1=relative, 2=absolute
        """
        if ctx == "move":
            pm.manipMoveContext(
                "Move",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            pm.texMoveContext(
                "texMoveContext", edit=1, snap=False if state == 0 else True
            )  # uv move context

        elif ctx == "scale":
            pm.manipScaleContext(
                "Scale",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            pm.texScaleContext(
                "texScaleContext", edit=1, snap=False if state == 0 else True
            )  # uv scale context

        elif ctx == "rotate":
            pm.manipRotateContext(
                "Rotate",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            pm.texRotateContext(
                "texRotateContext", edit=1, snap=False if state == 0 else True
            )  # uv rotate context


# --------------------------------------------------------------------------------------------


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
