# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Transform_maya(SlotsMaya):
    """ """

    def __init__(self, *args, **kwargs):
        """ """
        super().__init__(*args, **kwargs)

    def cmb001_init(self, widget):
        """ """
        widget.popupStyle = "qmenu"
        widget.option_menu.setTitle("Constaints")

        edge_constraint = (
            True if pm.xformConstraint(q=True, type=1) == "edge" else False
        )
        surface_constraint = (
            True if pm.xformConstraint(q=True, type=1) == "surface" else False
        )
        live_object = True if pm.ls(live=1) else False
        values = [
            ("chk024", "Contrain: Edge", edge_constraint),
            ("chk025", "Constain: Surface", surface_constraint),
            ("chk026", "Make Live", live_object),
        ]
        [
            widget.option_menu.add(
                self.sb.CheckBox, setObjectName=chk, setText=typ, setChecked=state
            )
            for chk, typ, state in values
        ]

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
            "Orient to Vertex/Edge Tool",
        ]
        widget.addItems_(items, "Align To")

    def cmb003_init(self, widget):
        """ """
        widget.popupStyle = "qmenu"
        widget.option_menu.setTitle("Snap")
        widget.option_menu.add(
            self.sb.CheckBox,
            setObjectName="chk021",
            setText="Snap Move: Off",
            setTristate=True,
        )
        widget.option_menu.add(
            "QDoubleSpinBox",
            setObjectName="s021",
            setPrefix="Increment:",
            setValue=0,
            set_limits=[1, 1000, 1, 1],
            setDisabled=True,
        )
        widget.option_menu.add(
            self.sb.CheckBox,
            setObjectName="chk022",
            setText="Snap Scale: Off",
            setTristate=True,
        )
        widget.option_menu.add(
            "QDoubleSpinBox",
            setObjectName="s022",
            setPrefix="Increment:",
            setValue=0,
            set_limits=[1, 1000, 1, 1],
            setDisabled=True,
        )
        widget.option_menu.add(
            self.sb.CheckBox,
            setObjectName="chk023",
            setText="Snap Rotate: Off",
            setTristate=True,
        )
        widget.option_menu.add(
            "QDoubleSpinBox",
            setObjectName="s023",
            setPrefix="Degrees:",
            setValue=0,
            set_limits=[1.40625, 360, 0.40625, 5],
            setDisabled=True,
        )
        moveValue = pm.manipMoveContext("Move", q=True, snapValue=True)
        widget.option_menu.s021.setValue(moveValue)
        scaleValue = pm.manipScaleContext("Scale", q=True, snapValue=True)
        widget.option_menu.s022.setValue(scaleValue)
        rotateValue = pm.manipRotateContext("Rotate", q=True, snapValue=True)
        widget.option_menu.s023.setValue(rotateValue)

    def tb000_init(self, widget):
        """ """
        # drop to grid.
        widget.option_menu.add(
            "QComboBox",
            addItems=["Min", "Mid", "Max"],
            setObjectName="cmb004",
            setToolTip="Choose which point of the bounding box to align to.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Move to Origin",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Move to origin (xyz 0,0,0).",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Center pivot on objects bounding box.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Reset the selected transform and all of its children down to the shape level.",
        )

    def tb001_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="X Axis",
            setObjectName="chk029",
            setDisabled=True,
            setToolTip="Align X axis",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Y Axis",
            setObjectName="chk030",
            setDisabled=True,
            setToolTip="Align Y axis",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Z Axis",
            setObjectName="chk031",
            setDisabled=True,
            setToolTip="Align Z axis",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Between Two Components",
            setObjectName="chk013",
            setToolTip="Align the path along an edge loop between two selected vertices or edges.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Align Loop",
            setObjectName="chk007",
            setToolTip="Align entire edge loop from selected edge(s).",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Average",
            setObjectName="chk006",
            setToolTip="Align to last selected object or average.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Auto Align",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Auto Align: Two Axes",
            setObjectName="chk011",
            setToolTip="",
        )

    def tb002_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk032",
            setChecked=True,
            setToolTip="The translation will be changed to 0, 0, 0.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk033",
            setToolTip="The rotation will be changed to 0, 0, 0.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk034",
            setChecked=True,
            setToolTip="The scale factor will be changed to 1, 1, 1.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk035",
            setChecked=True,
            setToolTip="Move the objects pivot to the center of it's bounding box.",
        )

    def chk010(self, state, widget):
        """Align Vertices: Auto Align"""
        if state:
            self.sb.toggle_widgets(widget.option_menu, setDisabled="chk029-31")
        else:
            self.sb.toggle_widgets(widget.option_menu, setEnabled="chk029-31")

    def chk021(self, state, widget):
        """Transform Tool Snap Settings: Move"""
        cmb = self.sb.transform.cmb003
        tri_state = cmb.option_menu.chk021.checkState_()
        text = {0: "Snap Move: Off", 1: "Snap Move: Relative", 2: "Snap Move: Absolute"}
        cmb.option_menu.chk021.setText(text[tri_state])
        cmb.option_menu.s021.setEnabled(tri_state)
        cmb.setCurrentText("Snap: OFF") if not any(
            (
                tri_state,
                cmb.option_menu.chk022.isChecked(),
                cmb.option_menu.chk023.isChecked(),
            )
        ) else cmb.setCurrentText("Snap: ON")

        self.setTransformSnap("move", tri_state)

    def chk022(self, state, widget):
        """Transform Tool Snap Settings: Scale"""
        cmb = self.sb.transform.cmb003
        tri_state = cmb.option_menu.chk022.checkState_()
        text = {
            0: "Snap Scale: Off",
            1: "Snap Scale: Relative",
            2: "Snap Scale: Absolute",
        }
        cmb.option_menu.chk022.setText(text[tri_state])
        cmb.option_menu.s022.setEnabled(tri_state)
        cmb.setCurrentText("Snap: OFF") if not any(
            (
                tri_state,
                cmb.option_menu.chk021.isChecked(),
                cmb.option_menu.chk023.isChecked(),
            )
        ) else cmb.setCurrentText("Snap: ON")

        self.setTransformSnap("scale", tri_state)

    def chk023(self, state, widget):
        """Transform Tool Snap Settings: Rotate"""
        cmb = self.sb.transform.cmb003
        tri_state = cmb.option_menu.chk023.checkState_()
        text = {
            0: "Snap Rotate: Off",
            1: "Snap Rotate: Relative",
            2: "Snap Rotate: Absolute",
        }
        cmb.option_menu.chk023.setText(text[tri_state])
        cmb.option_menu.s023.setEnabled(tri_state)
        cmb.setCurrentText("Snap: OFF") if not any(
            (
                tri_state,
                cmb.option_menu.chk021.isChecked(),
                cmb.option_menu.chk022.isChecked(),
            )
        ) else cmb.setCurrentText("Snap: ON")

        self.setTransformSnap("rotate", tri_state)

    def cmb002(self, index, widget):
        """Align To"""
        if index > 0:
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
                # import maya.app.general.positionAlongCurve
                # maya.app.general.positionAlongCurve.positionAlongCurve()
            elif text == "Align Tool":
                pm.mel.SetAlignTool()  # setToolTo alignToolCtx; Align the selection to the last selected object.
            elif text == "Snap Together Tool":
                pm.mel.SetSnapTogetherToolOptions()  # setToolTo snapTogetherToolCtx; toolPropertyWindow;) Snap two objects together.
            elif text == "Orient to Vertex/Edge Tool":
                pm.mel.orientToTool()  # Orient To Vertex/Edge
            widget.setCurrentIndex(0)

    def chk024(self, state, widget):
        """Transform Constraints: Edge"""
        cmb = self.sb.transform.cmb001

        if state:
            pm.xformConstraint(
                type="edge"
            )  # pm.manipMoveSetXformConstraint(edge=True);
        else:
            pm.xformConstraint(
                type="none"
            )  # pm.manipMoveSetXformConstraint(none=True);

        cmb.setCurrentText("Constrain: OFF") if not any(
            (
                state,
                cmb.option_menu.chk025.isChecked(),
                cmb.option_menu.chk026.isChecked(),
            )
        ) else cmb.setCurrentText("Constrain: ON")

    def chk025(self, state, widget):
        """Transform Contraints: Surface"""
        cmb = self.sb.transform.cmb001

        if state:
            pm.xformConstraint(
                type="surface"
            )  # pm.manipMoveSetXformConstraint(surface=True);
        else:
            pm.xformConstraint(
                type="none"
            )  # pm.manipMoveSetXformConstraint(none=True);

        cmb.setCurrentText("Constrain: OFF") if not any(
            (
                state,
                cmb.option_menu.chk024.isChecked(),
                cmb.option_menu.chk026.isChecked(),
            )
        ) else cmb.setCurrentText("Constrain: ON")

    def chk026(self, state, widget):
        """Transform Contraints: Make Live"""
        cmb = self.sb.transform.cmb001

        selection = pm.ls(sl=1, objectsOnly=1, type="transform")
        if state and selection:
            live_object = pm.ls(live=1)
            shape = mtk.Node.get_shape_node(selection[0])
            if shape not in str(live_object):
                pm.makeLive(
                    selection
                )  # construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
                # mtk.viewport_message('Make Live: <hl>On</hl> {0}'.format(selection[0].name()))
        else:
            pm.makeLive(none=True)
            # mtk.viewport_message('Make Live: <hl>Off</hl>')

        cmb.setCurrentText("Constrain: OFF") if not any(
            (
                state,
                cmb.option_menu.chk024.isChecked(),
                cmb.option_menu.chk025.isChecked(),
            )
        ) else cmb.setCurrentText("Constrain: ON")

    def s021(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipMoveContext("Move", edit=1, snapValue=value)
        pm.texMoveContext("texMoveContext", edit=1, snapValue=value)  # uv move context

    def s022(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipScaleContext("Scale", edit=1, snapValue=value)
        pm.texScaleContext(
            "texScaleContext", edit=1, snapValue=value
        )  # uv scale context

    def s023(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipRotateContext("Rotate", edit=1, snapValue=value)
        pm.texRotateContext(
            "texRotateContext", edit=1, snapValue=value
        )  # uv rotate context

    def tb000(self, widget):
        """Drop To Grid"""
        align = widget.option_menu.cmb004.currentText()
        origin = widget.option_menu.chk014.isChecked()
        center_pivot = widget.option_menu.chk016.isChecked()
        freeze_transforms = widget.option_menu.chk017.isChecked()

        objects = pm.ls(sl=1, objectsOnly=1)
        mtk.Xform.drop_to_grid(objects, align, origin, center_pivot, freeze_transforms)
        pm.select(objects)  # reselect the original selection.

    def tb001(self, widget):
        """Align Components

        Auto Align finds the axis with the largest variance, and sets the axis checkboxes accordingly before performing a regular align.
        """
        betweenTwoComponents = widget.option_menu.chk013.isChecked()
        autoAlign = widget.option_menu.chk010.isChecked()
        autoAlign2Axes = widget.option_menu.chk011.isChecked()  # Auto Align: Two Axes

        selection = pm.ls(orderedSelection=1, flatten=1)

        if betweenTwoComponents:
            if len(selection) > 1:
                componentsOnPath = mtk.Cmpt.get_edge_path(selection, "edgeLoopPath")
                pm.select(componentsOnPath)

        if autoAlign:  # set coordinates for auto align:
            if not len(selection) > 1:
                self.sb.message_box("Operation requires a component selection.")
                return

            point = pm.xform(selection, q=True, t=True, ws=True)
            # vertex point 1
            x1 = round(point[0], 4)
            y1 = round(point[1], 4)
            z1 = round(point[2], 4)

            # vertex point 2
            x2 = round(point[3], 4)
            y2 = round(point[4], 4)
            z2 = round(point[5], 4)

            # find the axis with the largest variance to determine direction.
            x = abs(x1 - x2)
            y = abs(y1 - y2)
            z = abs(z1 - z2)

            maskEdge = pm.selectType(query=True, edge=True)
            if maskEdge:
                selection = pm.polyListComponentConversion(fromEdge=1, toVertexFace=1)

            vertex = selection[0] if selection else None
            if vertex is None:
                self.sb.message_box("Unable to get component path.")
                return

            vertexTangent = pm.polyNormalPerVertex(vertex, query=True, xyz=True)

            tx = abs(round(vertexTangent[0], 4))
            ty = abs(round(vertexTangent[1], 4))
            tz = abs(round(vertexTangent[2], 4))

            axis = max(x, y, z)
            tangent = max(tx, ty, tz)

            if autoAlign2Axes:
                if axis == x:  # "yz"
                    self.sb.toggle_widgets(
                        widget.option_menu,
                        setChecked="chk030-31",
                        setUnChecked="chk029",
                    )
                if axis == y:  # "xz"
                    self.sb.toggle_widgets(
                        widget.option_menu,
                        setChecked="chk029,chk031",
                        setUnChecked="chk030",
                    )
                if axis == z:  # "xy"
                    self.sb.toggle_widgets(
                        widget.option_menu,
                        setChecked="chk029-30",
                        setUnChecked="chk031",
                    )
            else:
                if any(
                    [axis == x and tangent == ty, axis == y and tangent == tx]
                ):  # "z"
                    self.sb.toggle_widgets(
                        widget.option_menu,
                        setChecked="chk031",
                        setUnChecked="chk029-30",
                    )
                if any(
                    [axis == x and tangent == tz, axis == z and tangent == tx]
                ):  # "y"
                    self.sb.toggle_widgets(
                        widget.option_menu,
                        setChecked="chk030",
                        setUnChecked="chk029,chk031",
                    )
                if any(
                    [axis == y and tangent == tz, axis == z and tangent == ty]
                ):  # "x"
                    self.sb.toggle_widgets(
                        widget.option_menu,
                        setChecked="chk029",
                        setUnChecked="chk030-31",
                    )

        # align
        x = widget.option_menu.chk029.isChecked()
        y = widget.option_menu.chk030.isChecked()
        z = widget.option_menu.chk031.isChecked()
        avg = widget.option_menu.chk006.isChecked()
        loop = widget.option_menu.chk007.isChecked()

        if all([x, not y, not z]):  # align x
            mtk.Xform.align_vertices(mode=3, average=avg, edgeloop=loop)

        if all([not x, y, not z]):  # align y
            mtk.Xform.align_vertices(mode=4, average=avg, edgeloop=loop)

        if all([not x, not y, z]):  # align z
            mtk.Xform.align_vertices(mode=5, average=avg, edgeloop=loop)

        if all([not x, y, z]):  # align yz
            mtk.Xform.align_vertices(mode=0, average=avg, edgeloop=loop)

        if all([x, not y, z]):  # align xz
            mtk.Xform.align_vertices(mode=1, average=avg, edgeloop=loop)

        if all([x, y, not z]):  # align xy
            mtk.Xform.align_vertices(mode=2, average=avg, edgeloop=loop)

        if all([x, y, z]):  # align xyz
            mtk.Xform.align_vertices(mode=6, average=avg, edgeloop=loop)

    def tb002(self, widget):
        """Freeze Transformations"""
        selected_objects = pm.ls(selection=True)

        if len(selected_objects) == 0:
            self.sb.message_box("Please select at least one object.")
            return

        translate = widget.option_menu.chk032.isChecked()
        rotate = widget.option_menu.chk033.isChecked()
        scale = widget.option_menu.chk034.isChecked()
        center_pivot = widget.option_menu.chk035.isChecked()

        try:
            if center_pivot:
                pm.xform(selected_objects, centerPivots=1)

            pm.makeIdentity(
                selected_objects, apply=True, t=translate, r=rotate, s=scale
            )
        except Exception as e:
            print(f"An error occurred while freezing transformations: {e}")

    def b000(self, widget):
        """Object Transform Attributes"""
        node = pm.ls(sl=1, objectsOnly=1)
        if not node:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires a single selected object."
            )
            return

        transform_node = mtk.Node.get_transform_node(node[0])
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
            attrs = mtk.get_node_attributes(transform_node, params, mapping=True)
            self.sb.attribute_window(
                transform_node,
                window_title=transform_node.name(),
                set_attribute_func=lambda obj, n, v: getattr(obj, n).set(v),
                **attrs,
            )
        except Exception as e:
            print(f"An error occurred while getting parameter values: {e}")

    def b001(self):
        """Match Scale"""
        selection = pm.ls(sl=1)
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least two selected objects."
            )
            return

        frm = selection[0]
        to = selection[1:]

        mtk.Xform.match_scale(frm, to)

    def b003(self):
        """Center Pivot Object"""
        pm.mel.CenterPivot()

    def b005(self):
        """Move To"""
        sel = pm.ls(sl=1, transforms=1)
        if not sel:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least two selected objects."
            )
            return

        objects = sel[:-1]
        target = sel[-1]

        pm.matchTransform(
            objects, target, position=1, rotation=1, scale=0, pivots=1
        )  # move object to center of the last selected items bounding box
        pm.select(objects)

    def b012(self):
        """Make Live (Toggle)"""
        cmb = self.sb.transform.cmb001
        selection = pm.ls(sl=1, objectsOnly=1, type="transform")

        if selection:
            live_object = pm.ls(live=1)
            shape = mtk.Node.get_shape_node(selection[0])
            if shape not in str(live_object):
                self.chk026(state=1)
                cmb.option_menu.chk026.setChecked(True)
        else:
            self.chk026(state=0)
            cmb.option_menu.chk026.setChecked(False)

    def b014(self):
        """Center Pivot Component"""
        [pm.xform(s, centerPivot=1) for s in pm.ls(sl=1, objectsOnly=1, flatten=1)]
        # pm.mel.eval("moveObjectPivotToComponentCentre;")

    def b015(self):
        """Center Pivot World"""
        pm.xform(pivots=(0, 0, 0), worldSpace=1)

    def b016(self):
        """Set To Bounding Box"""
        pm.mel.eval("bt_alignPivotToBoundingBoxWin;")

    def b017(self):
        """Bake Pivot"""
        pm.mel.BakeCustomPivot()

    def b032(self):
        """Reset Pivot Transforms"""
        objs = pm.ls(type=["transform", "geometryShape"], sl=1)
        if len(objs) > 0:
            pm.xform(cp=1)

        pm.manipPivot(ro=1, rp=1)

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
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated ------------------------------------


# def cmb003(self):
#   '''Transform Tool Snapping: Disable All
#   '''
#   cmb = self.sb.transform.cmb003
#   self.sb.toggle_widgets(setUnChecked='chk021-23')
#   cmb.setCurrentText('Off') if not any((cmb.option_menu.chk021.isChecked(), cmb.option_menu.chk022.isChecked(), cmb.option_menu.chk023.isChecked())) else cmb.setCurrentText('On')


# def cmb003(self):
#   '''Transform Tool Snapping: Disable All
#   '''
#   cmb = self.sb.transform.lbl000
#   self.sb.toggle_widgets(setUnChecked='chk024-26')
#   cmb.setCurrentText('Off') if not any((cmb.option_menu.chk024.isChecked(), cmb.option_menu.chk025.isChecked(), cmb.option_menu.chk026.isChecked())) else cmb.setCurrentText('On')


# def s002(self, *args, **kwargs):
#   '''
#   Transform: Set Step
#   '''
#   value = self.sb.transform.s002.value()
#   self.sb.transform.s000.setStep(value)

# def s000(self, *args, **kwargs):
# '''
# Transform: Perform Transformations
# '''
# objects = pm.ls(sl=1, objectsOnly=1)
# xyz = self.getTransformValues()
# self.performTransformations(objects, xyz)

# def chk005(self, *args, **kwargs):
#   '''
#   Transform: Scale

#   '''
#   self.sb.toggle_widgets(setUnChecked='chk008-9', setChecked='chk000-2')
#   self.sb.transform.s000.setValue(2)
#   self.sb.transform.s000.setSingleStep(1)


# def chk008(self, *args, **kwargs):
#   '''
#   Transform: Move

#   '''
#   self.sb.toggle_widgets(setUnChecked='chk005,chk009,chk000-2')
#   self.sb.transform.s000.setValue(0.1)
#   self.sb.transform.s000.setSingleStep(0.1)


# def chk009(self, *args, **kwargs):
#   '''
#   Transform: Rotate

#   '''
#   self.sb.toggle_widgets(setUnChecked='chk005,chk008,chk000-2')
#   self.sb.transform.s000.setValue(45)
#   self.sb.transform.s000.setSingleStep(5)

# def b000(self):
#   '''
#   Transform negative axis
#   '''
#   #change the textfield to neg value and call performTransformations
#   textfield = float(self.sb.transform.s000.value())
#   if textfield >=0:
#       newText = -textfield
#       self.sb.transform.s000.setValue(newText)
#   self.performTransformations()


# def b001(self):
#   '''
#   Transform positive axis
#   '''
#   #change the textfield to pos value and call performTransformations
#   textfield = float(self.sb.transform.s000.value())
#   if textfield <0:
#       newText = abs(textfield)
#       self.sb.transform.s000.setValue(newText)
#   self.performTransformations()


#   def getTransformValues(self):
#   '''
#   Get the XYZ transform values from the various ui wgts.
#   '''
#   x = self.sb.transform.chk000.isChecked()
#   y = self.sb.transform.chk001.isChecked()
#   z = self.sb.transform.chk002.isChecked()
#   relative = self.sb.transform.chk005.isChecked()

#   amount = self.sb.transform.s002.value() #use the step as the transform amount
#   floatX=floatY=floatZ = 0

#   if relative: #else absolute.
#       currentScale = pm.xform(q=True, scale=1)
#       floatX = round(currentScale[0], 2)
#       floatY = round(currentScale[1], 2)
#       floatZ = round(currentScale[2], 2)

#   if x:
#       floatX = amount
#   if y:
#       floatY = amount
#   if z:
#       floatZ = amount

#   xyz = [floatX, floatY, floatZ]
#   return xyz


# def performTransformations(self, objects, xyz): #transform
#   '''

#   '''
#   relative = bool(self.sb.transform.chk003.isChecked())#Move absolute/relative toggle
#   worldspace = bool(self.sb.transform.chk004.isChecked())#Move object/worldspace toggle

#   scale = self.sb.transform.chk005.isChecked()
#   move = self.sb.transform.chk008.isChecked()
#   rotate = self.sb.transform.chk009.isChecked()

#   #Scale selected.
#   if scale:
#       if xyz[0] != -1: #negative values are only valid in relative mode and cannot scale relatively by one so prevent the math below which would scale incorrectly in this case.
#           #convert the decimal place system xform uses for negative scale values to an standard negative value
#           if xyz[0] < 0:
#               xyz[0] = xyz[0]/10.*2.5
#           if xyz[1] < 0:
#               xyz[1] = xyz[1]/10.*2.5
#           if xyz[2] < 0:
#               xyz[2] = xyz[2]/10.*2.5
#           pm.xform(objects, relative=relative, worldSpace=worldspace, objectSpace=(not worldspace), scale=(xyz[0], xyz[1], xyz[2]))

#   #Move selected relative/absolute, object/worldspace by specified amount.
#   if move:
#       pm.xform(objects, relative=relative, worldSpace=worldspace, objectSpace=(not worldspace), translation=(xyz[0], xyz[1], xyz[2]))

#   #Rotate selected
#   if rotate:
#       pm.xform(objects, relative=relative, worldSpace=worldspace, objectSpace=(not worldspace), rotation=(xyz[0], xyz[1], xyz[2]))


# def cmb002(self, *args, **kwargs):
#   '''
#   Transform Contraints

#   constrain along normals #checkbox option for edge amd surface constaints
#   setXformConstraintAlongNormal false;
#   '''
#   cmb = self.sb.transform.lbl000

#   if index=='setMenu':
#       cmb.option_menu.add(self.sb.Label, setObjectName='lbl000', setText='Disable All', setToolTip='Disable all constraints.')

#       items = ['Edge', 'Surface', 'Make Live']
#       cmb.addItems_(items, 'Off')
#       return

#   live_object = pm.ls(live=1)
#   print ("live_object:", live_object)
#   # if not live_object and text=='Make Live'):
#   #   cmb.setCurrentIndex(0)

#   if index>0:
#       text = cmb.items[index]
#       if text=='Edge'):
#           pm.xformConstraint(type='edge') #pm.manipMoveSetXformConstraint(edge=True);

#       elif text=='Surface'):
#           pm.xformConstraint(type='surface') #pm.manipMoveSetXformConstraint(surface=True);

#       elif text=='Make Live'):
#           print ('3')
#           selection = pm.ls(sl=1, objectsOnly=1, type='transform')
#           if not selection and not live_object:
#               print ('not selection and not live_object')
#               cmb.setCurrentIndex(0)
#               return 'Error: Nothing Selected.'

#           if not live_object:
#               print ('not live_object')
#               pm.makeLive(selection) #construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
#               mtk.viewport_message('Make Live: <hl>On</hl> {0}'.format(selection[0].name()))
#   else:
#       print ('0')
#       pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);
#       if live_object:
#           print ('none')
#           pm.makeLive(none=True)
#           mtk.viewport_message('Make Live: <hl>Off</hl>')
