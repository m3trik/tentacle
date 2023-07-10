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
        widget.add(items, header="Align To")

    def tb000_init(self, widget):
        """ """
        # drop to grid.
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

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="X Axis",
            setObjectName="chk029",
            setDisabled=True,
            setToolTip="Align X axis",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Y Axis",
            setObjectName="chk030",
            setDisabled=True,
            setToolTip="Align Y axis",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Z Axis",
            setObjectName="chk031",
            setDisabled=True,
            setToolTip="Align Z axis",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Between Two Components",
            setObjectName="chk013",
            setToolTip="Align the path along an edge loop between two selected vertices or edges.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Align Loop",
            setObjectName="chk007",
            setToolTip="Align entire edge loop from selected edge(s).",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Average",
            setObjectName="chk006",
            setToolTip="Align to last selected object or average.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Auto Align",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Auto Align: Two Axes",
            setObjectName="chk011",
            setToolTip="",
        )

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

    def tb003_init(self, widget):
        """ """
        widget.menu.mode = "popup"
        widget.menu.position = "bottom"
        widget.menu.setTitle("CONSTRAINTS")
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
            widget.menu.add(
                self.sb.CheckBox, setObjectName=chk, setText=typ, setChecked=state
            )
            for chk, typ, state in values
        ]

    def tb004_init(self, widget):
        """ """
        widget.menu.mode = "popup"
        widget.menu.position = "bottom"
        widget.menu.setTitle("SNAP")
        widget.menu.add(
            self.sb.CheckBox,
            setObjectName="chk021",
            setText="Snap Move: Off",
            setTristate=True,
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
            setText="Snap Scale: Off",
            setTristate=True,
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
            setText="Snap Rotate: Off",
            setTristate=True,
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setObjectName="s023",
            setPrefix="Degrees:",
            setValue=0,
            set_limits=[1.40625, 360, 0.40625, 5],
            setDisabled=True,
        )
        moveValue = pm.manipMoveContext("Move", q=True, snapValue=True)
        widget.menu.s021.setValue(moveValue)
        scaleValue = pm.manipScaleContext("Scale", q=True, snapValue=True)
        widget.menu.s022.setValue(scaleValue)
        rotateValue = pm.manipRotateContext("Rotate", q=True, snapValue=True)
        widget.menu.s023.setValue(rotateValue)

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

    def chk010(self, state, widget):
        """Align Vertices: Auto Align"""
        if state:
            self.sb.toggle_widgets(widget.ui.tb001.menu, setDisabled="chk029-31")
        else:
            self.sb.toggle_widgets(widget.ui.tb001.menu, setEnabled="chk029-31")

    def chk021(self, state, widget):
        """Transform Tool Snap Settings: Move"""
        tb = self.sb.transform.tb004
        tb.init_slot()
        tri_state = tb.menu.chk021.checkState()
        text = {0: "Snap Move: Off", 1: "Snap Move: Relative", 2: "Snap Move: Absolute"}
        tb.menu.chk021.setText(text[tri_state])
        tb.menu.s021.setEnabled(tri_state)
        tb.setText("Snap: OFF") if not any(
            (
                tri_state,
                tb.menu.chk022.isChecked(),
                tb.menu.chk023.isChecked(),
            )
        ) else tb.setText("Snap: ON")

        self.setTransformSnap("move", tri_state)

    def chk022(self, state, widget):
        """Transform Tool Snap Settings: Scale"""
        tb = self.sb.transform.tb004
        tb.init_slot()
        tri_state = tb.menu.chk022.checkState()
        text = {
            0: "Snap Scale: Off",
            1: "Snap Scale: Relative",
            2: "Snap Scale: Absolute",
        }
        tb.menu.chk022.setText(text[tri_state])
        tb.menu.s022.setEnabled(tri_state)
        tb.setText("Snap: OFF") if not any(
            (
                tri_state,
                tb.menu.chk021.isChecked(),
                tb.menu.chk023.isChecked(),
            )
        ) else tb.setText("Snap: ON")

        self.setTransformSnap("scale", tri_state)

    def chk023(self, state, widget):
        """Transform Tool Snap Settings: Rotate"""
        tb = self.sb.transform.tb004
        tb.init_slot()
        tri_state = tb.menu.chk023.checkState()
        text = {
            0: "Snap Rotate: Off",
            1: "Snap Rotate: Relative",
            2: "Snap Rotate: Absolute",
        }
        tb.menu.chk023.setText(text[tri_state])
        tb.menu.s023.setEnabled(tri_state)
        tb.setText("Snap: OFF") if not any(
            (
                tri_state,
                tb.menu.chk021.isChecked(),
                tb.menu.chk022.isChecked(),
            )
        ) else tb.setText("Snap: ON")

        self.setTransformSnap("rotate", tri_state)

    def chk024(self, state, widget):
        """Transform Constraints: Edge"""
        tb = self.sb.transform.tb003
        tb.init_slot()
        if state:
            pm.xformConstraint(type="edge")
        else:
            pm.xformConstraint(type="none")

        tb.setText("Constrain: OFF") if not any(
            (
                state,
                tb.menu.chk025.isChecked(),
                tb.menu.chk026.isChecked(),
            )
        ) else tb.setText("Constrain: ON")

    def chk025(self, state, widget):
        """Transform Contraints: Surface"""
        tb = self.sb.transform.tb003
        tb.init_slot()
        if state:
            pm.xformConstraint(type="surface")
        else:
            pm.xformConstraint(type="none")

        tb.setText("Constrain: OFF") if not any(
            (
                state,
                tb.menu.chk024.isChecked(),
                tb.menu.chk026.isChecked(),
            )
        ) else tb.setText("Constrain: ON")

    def chk026(self, state, widget):
        """Transform Contraints: Make Live"""
        tb = self.sb.transform.tb003
        tb.init_slot()
        selection = pm.ls(sl=1, objectsOnly=1, type="transform")
        if state and selection:
            live_objects = pm.ls(live=1)
            shape = mtk.get_shape_node(selection[0])
            if shape not in live_objects:
                # Construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
                pm.makeLive(selection)
        else:
            pm.makeLive(none=True)

        tb.setText("Constrain: OFF") if not any(
            (
                state,
                tb.menu.chk024.isChecked(),
                tb.menu.chk025.isChecked(),
            )
        ) else tb.setText("Constrain: ON")

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
        align = widget.menu.cmb004.currentText()
        origin = widget.menu.chk014.isChecked()
        center_pivot = widget.menu.chk016.isChecked()
        freeze_transforms = widget.menu.chk017.isChecked()

        objects = pm.ls(sl=1, objectsOnly=1)
        mtk.drop_to_grid(objects, align, origin, center_pivot, freeze_transforms)
        pm.select(objects)  # reselect the original selection.

    def tb001(self, widget):
        """Align Components

        Auto Align finds the axis with the largest variance, and sets the axis checkboxes accordingly before performing a regular align.
        """
        betweenTwoComponents = widget.menu.chk013.isChecked()
        autoAlign = widget.menu.chk010.isChecked()
        autoAlign2Axes = widget.menu.chk011.isChecked()  # Auto Align: Two Axes

        selection = pm.ls(orderedSelection=1, flatten=1)

        if betweenTwoComponents:
            if len(selection) > 1:
                componentsOnPath = mtk.get_edge_path(selection, "edgeLoopPath")
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
                        widget.menu,
                        setChecked="chk030-31",
                        setUnChecked="chk029",
                    )
                if axis == y:  # "xz"
                    self.sb.toggle_widgets(
                        widget.menu,
                        setChecked="chk029,chk031",
                        setUnChecked="chk030",
                    )
                if axis == z:  # "xy"
                    self.sb.toggle_widgets(
                        widget.menu,
                        setChecked="chk029-30",
                        setUnChecked="chk031",
                    )
            else:
                if any(
                    [axis == x and tangent == ty, axis == y and tangent == tx]
                ):  # "z"
                    self.sb.toggle_widgets(
                        widget.menu,
                        setChecked="chk031",
                        setUnChecked="chk029-30",
                    )
                if any(
                    [axis == x and tangent == tz, axis == z and tangent == tx]
                ):  # "y"
                    self.sb.toggle_widgets(
                        widget.menu,
                        setChecked="chk030",
                        setUnChecked="chk029,chk031",
                    )
                if any(
                    [axis == y and tangent == tz, axis == z and tangent == ty]
                ):  # "x"
                    self.sb.toggle_widgets(
                        widget.menu,
                        setChecked="chk029",
                        setUnChecked="chk030-31",
                    )

        # align
        x = widget.menu.chk029.isChecked()
        y = widget.menu.chk030.isChecked()
        z = widget.menu.chk031.isChecked()
        avg = widget.menu.chk006.isChecked()
        loop = widget.menu.chk007.isChecked()

        if all([x, not y, not z]):  # align x
            mtk.align_vertices(mode=3, average=avg, edgeloop=loop)

        if all([not x, y, not z]):  # align y
            mtk.align_vertices(mode=4, average=avg, edgeloop=loop)

        if all([not x, not y, z]):  # align z
            mtk.align_vertices(mode=5, average=avg, edgeloop=loop)

        if all([not x, y, z]):  # align yz
            mtk.align_vertices(mode=0, average=avg, edgeloop=loop)

        if all([x, not y, z]):  # align xz
            mtk.align_vertices(mode=1, average=avg, edgeloop=loop)

        if all([x, y, not z]):  # align xy
            mtk.align_vertices(mode=2, average=avg, edgeloop=loop)

        if all([x, y, z]):  # align xyz
            mtk.align_vertices(mode=6, average=avg, edgeloop=loop)

    def tb002(self, widget):
        """Freeze Transformations"""
        selected_objects = pm.ls(selection=True)

        if len(selected_objects) == 0:
            self.sb.message_box("Please select at least one object.")
            return

        translate = widget.menu.chk032.isChecked()
        rotate = widget.menu.chk033.isChecked()
        scale = widget.menu.chk034.isChecked()
        center_pivot = widget.menu.chk035.isChecked()

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
            window.show()
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

        mtk.match_scale(frm, to)

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
        tb = self.sb.transform.tb003
        selection = pm.ls(sl=1, objectsOnly=1, type="transform")

        if selection:
            live_object = pm.ls(live=1)
            shape = mtk.get_shape_node(selection[0])
            if shape not in str(live_object):
                self.chk026(state=1)
                tb.menu.chk026.setChecked(True)
        else:
            self.chk026(state=0)
            tb.menu.chk026.setChecked(False)

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
