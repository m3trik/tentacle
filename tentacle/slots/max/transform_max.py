# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.transform import Transform


class Transform_max(Transform, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb000 = self.sb.transform.draggableHeader.ctxMenu.cmb000
        items = [""]
        cmb000.addItems_(items, "")

        cmb001 = self.sb.transform.cmb001
        cmb001.ctxMenu.add(
            "QRadioButton",
            setObjectName="chk017",
            setText="Standard",
            setChecked=True,
            setToolTip="",
        )
        cmb001.ctxMenu.add(
            "QRadioButton", setObjectName="chk018", setText="Body Shapes", setToolTip=""
        )
        cmb001.ctxMenu.add(
            "QRadioButton", setObjectName="chk019", setText="NURBS", setToolTip=""
        )
        cmb001.ctxMenu.add(
            "QRadioButton",
            setObjectName="chk020",
            setText="Point Cloud Shapes",
            setToolTip="",
        )
        cmb001.ctxMenu.add(
            self.sb.Label,
            setObjectName="lbl000",
            setText="Disable All",
            setToolTip="Disable all constraints.",
        )
        self.sb.connect_multi(
            "chk017-20", "toggled", self.cmb001, cmb001.ctxMenu
        )  # connect to this method on toggle

        cmb002 = self.sb.transform.cmb002
        items = [
            "Point to Point",
            "2 Points to 2 Points",
            "3 Points to 3 Points",
            "Align Objects",
            "Position Along Curve",
            "Align Tool",
            "Snap Together Tool",
        ]
        cmb002.addItems_(items, "Align To")

        cmb003 = self.sb.transform.cmb003
        # moveValue = pm.manipMoveContext('Move', q=True, snapValue=True)
        # cmb003.menu_.s021.setValue(moveValue)
        # scaleValue = pm.manipScaleContext('Scale', q=True, snapValue=True)
        # cmb003.menu_.s022.setValue(scaleValue)
        # rotateValue = pm.manipRotateContext('Rotate', q=True, snapValue=True)
        # cmb003.menu_.s023.setValue(rotateValue)

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.transform.draggableHeader.ctxMenu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def cmb001(self, index=-1):
        """Transform Contraints

        constrain along normals #checkbox option for edge amd surface constaints
        setXformConstraintAlongNormal false;
        """
        cmb = self.sb.transform.cmb001

        cmb.menu_.clear()
        if cmb.ctxMenu.chk017.isChecked():  # Standard
            cmb.setItemText(0, "Standard")  # set cetagory title in standard model/view
            items = [
                "Grid Points",
                "Pivot",
                "Perpendicular",
                "Vertex",
                "Edge/Segment",
                "Face",
                "Grid Lines",
                "Bounding Box",
                "Tangent",
                "Endpoint",
                "Midpoint",
                "Center Face",
            ]
        if cmb.ctxMenu.chk018.isChecked():  # Body Shapes
            cmb.setItemText(
                0, "Body Shapes"
            )  # set category title in standard model/view
            items = ["Vertex_", "Edge", "Face_", "End Edge", "Edge Midpoint"]
        if cmb.ctxMenu.chk019.isChecked():  # NURBS
            cmb.setItemText(0, "NURBS")  # set category title in standard model/view
            items = [
                "CV",
                "Curve Center",
                "Curve Tangent",
                "Curve End",
                "Surface Normal",
                "Point",
                "Curve Normal",
                "Curve Edge",
                "Surface Center",
                "Surface Edge",
            ]
        if cmb.ctxMenu.chk020.isChecked():  # Point Cloud Shapes
            cmb.setItemText(
                0, "Point Cloud Shapes"
            )  # set category title in standard model/view
            items = ["Point Cloud Vertex"]

        widgets = [cmb.menu_.add("QCheckBox", setText=t) for t in items]

        for w in widgets:
            try:
                w.disconnect()  # disconnect all previous connections.
            except TypeError:
                pass  # if no connections are present; pass
            w.toggled.connect(
                lambda state, widget=w: self.chkxxx(state=state, widget=widget)
            )

    def cmb002(self, index=-1):
        """Align To"""
        cmb = self.sb.transform.cmb002

        if index > 0:
            text = cmb.items[index]
            if text == "Point to Point":
                mel.eval(
                    "SnapPointToPointOptions;"
                )  # performSnapPtToPt 1; Select any type of point object or component.
            elif text == "2 Points to 2 Points":
                mel.eval(
                    "Snap2PointsTo2PointsOptions;"
                )  # performSnap2PtTo2Pt 1; Select any type of point object or component.
            elif text == "3 Points to 3 Points":
                mel.eval(
                    "Snap3PointsTo3PointsOptions;"
                )  # performSnap3PtTo3Pt 1; Select any type of point object or component.
            elif text == "Align Objects":
                mel.eval("performAlignObjects 1;")  # Align the selected objects.
            elif text == "Position Along Curve":
                mel.eval(
                    "PositionAlongCurve;"
                )  # Position selected objects along a selected curve.
                # import maya.app.general.positionAlongCurve
                # maya.app.general.positionAlongCurve.positionAlongCurve()
            elif text == "Align Tool":
                mel.eval(
                    "SetAlignTool;"
                )  # setToolTo alignToolCtx; Align the selection to the last selected object.
            elif text == "Snap Together Tool":
                mel.eval(
                    "SetSnapTogetherToolOptions;"
                )  # setToolTo snapTogetherToolCtx; toolPropertyWindow;) Snap two objects together.

    def cmb003(self, index=-1):
        """Transform Tool Snapping"""
        cmb = self.sb.transform.cmb003

    def s021(self, value=None):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipMoveContext("Move", edit=1, snapValue=value)
        pm.texMoveContext("texMoveContext", edit=1, snapValue=value)  # uv move context

    def s022(self, value=None):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipScaleContext("Scale", edit=1, snapValue=value)
        pm.texScaleContext(
            "texScaleContext", edit=1, snapValue=value
        )  # uv scale context

    def s023(self, value=None):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipRotateContext("Rotate", edit=1, snapValue=value)
        pm.texRotateContext(
            "texRotateContext", edit=1, snapValue=value
        )  # uv rotate context

    def chkxxx(self, **kwargs):
        """Transform Constraints: Constraint CheckBoxes"""
        try:
            self.setSnapState(kwargs["widget"].text(), kwargs["state"])
        except KeyError:
            pass

    def tb000(self, state=None):
        """Drop To Grid"""
        tb = self.sb.transform.tb000

        align = tb.ctxMenu.cmb004.currentText()
        origin = tb.ctxMenu.chk014.isChecked()
        center_pivot = tb.ctxMenu.chk016.isChecked()

        objects = pm.ls(sl=1, objectsOnly=1)
        SlotsMax.drop_to_grid(objects, align, origin, center_pivot)
        pm.select(objects)  # reselect the original selection.

    def tb001(self, state=None):
        """Align Vertices

        Auto Align finds the axis with the largest variance, and set the axis checkboxes accordingly before performing a regular align.
        """
        tb = self.sb.transform.tb001

        betweenTwoComponents = tb.ctxMenu.chk013.isChecked()
        autoAlign = tb.ctxMenu.chk010.isChecked()
        autoAlign2Axes = tb.ctxMenu.chk011.isChecked()  # Auto Align: Two Axes

        selection = pm.ls(orderedSelection=1)

        if betweenTwoComponents:
            if len(selection) > 1:
                componentsOnPath = SlotsMax.getPathAlongLoop(
                    [selection[0], selection[-1]]
                )
                pm.select(componentsOnPath)

        if autoAlign:  # set coordinates for auto align:
            if len(selection) > 1:
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
                    selection = pm.polyListComponentConversion(
                        fromEdge=1, toVertexFace=1
                    )

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
                            tb.ctxMenu, setChecked="chk030-31", setUnChecked="chk029"
                        )
                    if axis == y:  # "xz"
                        self.sb.toggle_widgets(
                            tb.ctxMenu,
                            setChecked="chk029,chk031",
                            setUnChecked="chk030",
                        )
                    if axis == z:  # "xy"
                        self.sb.toggle_widgets(
                            tb.ctxMenu, setChecked="chk029-30", setUnChecked="chk031"
                        )
                else:
                    if any(
                        [axis == x and tangent == ty, axis == y and tangent == tx]
                    ):  # "z"
                        self.sb.toggle_widgets(
                            tb.ctxMenu, setChecked="chk031", setUnChecked="chk029-30"
                        )
                    if any(
                        [axis == x and tangent == tz, axis == z and tangent == tx]
                    ):  # "y"
                        self.sb.toggle_widgets(
                            tb.ctxMenu,
                            setChecked="chk030",
                            setUnChecked="chk029,chk031",
                        )
                    if any(
                        [axis == y and tangent == tz, axis == z and tangent == ty]
                    ):  # "x"
                        self.sb.toggle_widgets(
                            tb.ctxMenu, setChecked="chk029", setUnChecked="chk030-31"
                        )
            else:
                self.sb.message_box("Operation requires a component selection.")
                return

        # align
        x = tb.ctxMenu.chk029.isChecked()
        y = tb.ctxMenu.chk030.isChecked()
        z = tb.ctxMenu.chk031.isChecked()
        avg = tb.ctxMenu.chk006.isChecked()
        loop = tb.ctxMenu.chk007.isChecked()

        if all([x, not y, not z]):  # align x
            self.align_vertices(mode=3, average=avg, edgeloop=loop)

        if all([not x, y, not z]):  # align y
            self.align_vertices(mode=4, average=avg, edgeloop=loop)

        if all([not x, not y, z]):  # align z
            self.align_vertices(mode=5, average=avg, edgeloop=loop)

        if all([not x, y, z]):  # align yz
            self.align_vertices(mode=0, average=avg, edgeloop=loop)

        if all([x, not y, z]):  # align xz
            self.align_vertices(mode=1, average=avg, edgeloop=loop)

        if all([x, y, not z]):  # align xy
            self.align_vertices(mode=2, average=avg, edgeloop=loop)

        if all([x, y, z]):  # align xyz
            self.align_vertices(mode=6, average=avg, edgeloop=loop)

    @Slots.hideMain
    def b000(self):
        """Object Transform Attributes"""
        selection = list(rt.selection)
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires a single selected object."
            )
            return

        obj = selection[0]

        props = [
            "pos.x",
            "pos.y",
            "pos.z",
            "rotation.x_rotation",
            "rotation.y_rotation",
            "rotation.z_rotation",
            "scale.x",
            "scale.y",
            "scale.z",
            "center",
            "pivot.x",
            "pivot.y",
            "pivot.z",
        ]
        attrs = {p: getattr(obj, p) for p in props}

        self.setAttributeWindow(obj, checkableLabel=True, **attrs)

    def b001(self):
        """Match Scale"""
        selection = list(rt.selection)
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least two selected object."
            )
            return

        frm = selection[0]
        to = selection[1:]

        SlotsMaya.match_scale(to, frm)

    def lbl000(self):
        """Transform Constraints: Disable All"""
        widgets = self.sb.transform.cmb001.ctxMenu.children_(of_type=["QCheckBox"])
        [w.setChecked(False) for w in widgets if w.isChecked()]

    def lbl001(self):
        """Transform Tool Snapping: Disable All"""
        cmb = self.sb.transform.cmb003
        self.sb.toggle_widgets(setDisabled="chk021-23")
        cmb.setCurrentText("Off") if not any(
            (state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk023.isChecked())
        ) else cmb.setCurrentText("On")

    def b002(self):
        """Freeze Transformations"""
        maxEval('macros.run "Animation Tools" "FreezeTransform"')

    def b003(self):
        """Center Pivot Object"""
        for obj in rt.selection:
            rt.toolMode.coordsys(obj)
            obj.pivot = obj.center

    def b005(self):
        """Move To"""
        sel = [
            s for s in rt.getCurrentSelection()
        ]  # rebuild selection array in python.

        objects = sel[:-1]
        target = sel[-1]
        # move object(s) to center of the last selected items bounding box
        for obj in objects:
            obj.center = target.center

    def b014(self):
        """Center Pivot Component"""
        [pm.xform(s, centerPivot=1) for s in pm.ls(sl=1, objectsOnly=1, flatten=1)]
        # mel.eval("moveObjectPivotToComponentCentre;")

    def b015(self):
        """Center Pivot World"""
        mel.eval("xform -worldSpace -pivots 0 0 0;")

    def b016(self):
        """Set To Bounding Box"""
        mel.eval("bt_alignPivotToBoundingBoxWin;")

    def b017(self):
        """Bake Pivot"""
        mel.eval("BakeCustomPivot;")

    def b032(self):
        """Reset Pivot Transforms"""
        maxEval(
            """
            { string $objs[] = `ls -sl -type transform -type geometryShape`;
            if (size($objs) > 0) { xform -cp; } manipPivot -rp -ro; };
            """
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

    def setSnapState(self, fn, state):
        """Grid and Snap Settings: Modify grid and snap states.

        Parameters:
                fn (str): Snap string name.
                state (bool): Desired snap state.

        Valid fn arguments for snap name:
                Body Shapes: (1) 'Vertex_', 'Edge', 'Face_', 'End Edge', 'Edge Midpoint'
                NURBS: (2) 'CV', 'Curve Center', 'Curve Tangent', 'Curve End', 'Surface Normal', 'Point', 'Curve Normal', 'Curve Edge', 'Surface Center','Surface Edge'
                Point Cloud Shapes: (3) 'Point Cloud Vertex'
                Standard: (4,5,6,7) 'Grid Points', 'Pivot', 'Perpendicular', 'Vertex', 'Edge/Segment', 'Face', 'Grid Lines', 'Bounding Box', 'Tangent', 'Endpoint', 'Midpoint', 'Center Face'

        ex. setSnapState('Edge', True)
        """
        snaps = {
            1: ["Vertex_", "Edge", "Face_", "End Edge", "Edge Midpoint"],  # Body Shapes
            2: [
                "CV",
                "Curve Center",
                "Curve Tangent",
                "Curve End",
                "Surface Normal",
                "Point",
                "Curve Normal",
                "Curve Edge",
                "Surface Center",
                "Surface Edge",
            ],  # NURBS
            3: ["Point Cloud Vertex"],  # Point Cloud Shapes
            4: ["Grid Points", "Pivot"],  # Standard
            5: ["Perpendicular", "Vertex"],  # Standard
            6: ["Edge/Segment", "Face"],  # Standard
            7: [
                "Grid Lines",
                "Bounding Box",
                "Tangent",
                "Endpoint",
                "Midpoint",
                "Center Face",
            ],  # Standard
        }

        for category, lst in snaps.items():
            if fn in lst:
                index = lst.index(fn) + 1  # add 1 to align with max array.
                rt.snapmode.setOSnapItemActive(
                    category, index, state
                )  # ie. rt.snapmode.setOSnapItemActive(3, 1, False) #'Point Cloud Shapes'->'Point Cloud Vertex'->Off
                print(fn, "|", state)

    def align_vertices(self, selection, mode):
        """Align Vertices

        Align all vertices at once by putting each vert index and coordinates in a dict (or two arrays) then if when iterating through a vert falls within the tolerance specified in a textfield align that vert in coordinate. then repeat the process for the other coordinates x,y,z specified by checkboxes. using edges may be a better approach. or both with a subObjectLevel check
        create edge alignment tool and then use subObjectLevel check to call either that function or this one from the same buttons.
        to save ui space; have a single align button, x, y, z, and align 'all' checkboxes and a tolerance textfield.

        Parameters:
                selection (list): vertex selection
                mode (int): valid values are: 0 (YZ), 1 (XZ), 2 (XY), 3 (X), 4 (Y), 5 (Z)

        notes:
        'vertex.pos.x = vertPosX' ect doesnt work. had to use maxscript
        """
        # maxEval('undo "align_vertices" on')
        componentArray = selection.selectedVerts

        if len(componentArray) == 0:
            self.sb.message_box("No vertices selected.")
            return

        if len(componentArray) < 2:
            self.sb.message_box("Selection must contain at least two vertices.")
            return

        lastSelected = componentArray[
            -1
        ]  # 3ds max re-orders array by vert index, so this doesnt work for aligning to last selected
        # ~ print(lastSelected.pos)
        aX = lastSelected.pos[0]
        aY = lastSelected.pos[1]
        aZ = lastSelected.pos[2]

        for vertex in componentArray:
            # ~ print(vertex.pos)
            vX = vertex.pos[0]
            vY = vertex.pos[1]
            vZ = vertex.pos[2]

            maxEval("global alignXYZ")

            if mode == 0:  # align YZ
                maxEval(
                    """
                fn alignXYZ mode vertex vX vY vZ aX aY aZ=
                (
                    vertex.pos.x = vX
                    vertex.pos.y = aY
                    vertex.pos.z = aZ
                )
                """
                )

            if mode == 1:  # align XZ
                maxEval(
                    """
                fn alignXYZ mode vertex vX vY vZ aX aY aZ=
                (
                    vertex.pos.x = aX
                    vertex.pos.y = vY
                    vertex.pos.z = aZ
                )
                """
                )

            if mode == 2:  # align XY
                maxEval(
                    """
                fn alignXYZ mode vertex vX vY vZ aX aY aZ=
                (
                    vertex.pos.x = aX
                    vertex.pos.y = aY
                    vertex.pos.z = vZ
                )
                """
                )

            if mode == 3:  # X
                maxEval(
                    """
                fn alignXYZ mode vertex vX vY vZ aX aY aZ=
                (
                    vertex.pos.x = aX
                    vertex.pos.y = vY
                    vertex.pos.z = vZ
                )
                """
                )

            if mode == 4:  # Y
                maxEval(
                    """
                fn alignXYZ mode vertex vX vY vZ aX aY aZ=
                (
                    vertex.pos.x = vX
                    vertex.pos.y = aY
                    vertex.pos.z = vZ
                )
                """
                )

            if mode == 5:  # Z
                maxEval(
                    """
                fn alignXYZ mode vertex vX vY vZ aX aY aZ=
                (
                    vertex.pos.x = vX
                    vertex.pos.y = vY
                    vertex.pos.z = aZ
                )
                """
                )

            print(100 * "-")
            print("vertex.index:", vertex.index)
            print("position:", vX, vY, vZ)
            print("align:   ", aX, aY, aZ)

            rt.alignXYZ(mode, vertex, vX, vY, vZ, aX, aY, aZ)

            self.sb.message_box(
                "{0}{1}{2}{3}".format(
                    "result: ", vertex.pos[0], vertex.pos[1], vertex.pos[2]
                )
            )

    def scaleObject(self, size, x, y, z):
        """
        Parameters:
                size (float) = Scale amount
                x (bool): Scale in the x direction.
                y (bool): Scale in the y direction.
                z (bool): Scale in the z direction.

        Basically working except for final 'obj.scale([s, s, s])' command in python. variable definitions included for debugging.
        to get working an option is to use the maxEval method in the align_vertices function.
        """
        textField_000 = 1.50
        isChecked_002 = True
        isChecked_003 = True
        isChecked_004 = True

        s = textField_000
        x = isChecked_002
        y = isChecked_003
        z = isChecked_004
        # -------------------------
        s = size
        selection = rt.selection

        for obj in selection:
            if isChecked_002 and isChecked_003 and isChecked_004:
                obj.scale([s, s, s])
            if not isChecked_002 and isChecked_003 and isChecked_004:
                obj.scale([1, s, s])
            if isChecked_002(not isChecked_003) and isChecked_004:
                obj.scale([s, 1, s])
            if isChecked_002 and isChecked_003(not isChecked_004):
                obj.scale([s, s, 1])
            if not isChecked_002(not isChecked_003) and isChecked_004:
                obj.scale([1, 1, s])
            if isChecked_002(not isChecked_003)(not isChecked_004):
                obj.scale([s, 1, 1])
            if isChecked_002 and isChecked_003 and isChecked_004:
                obj.scale([1, s, 1])
            if not isChecked_002(not isChecked_003)(not isChecked_004):
                obj.scale([1, 1, 1])

    def compareSize(self, obj1, obj2, factor):
        """Compares two point3 sizes from obj bounding boxes.

        Parameters:
                obj1 (obj):
                obj2 (obj):
                factor () =
        """
        maxEval(
            """
        s1 = obj1.max - obj1.min --determine bounding boxes
        s2 = obj2.max - obj2.min
        
        if (s2.x >= (s1.x*(1-factor)) AND s2.x <= (s1.x*(1+factor))) OR (s2.x >= (s1.y*(1-factor)) AND s2.x <= (s1.y*(1+factor))) OR (s2.x >= (s1.z*(1-factor)) AND s2.x <= (s1.z*(1+factor)))THEN
            if (s2.y >= (s1.y*(1-factor)) AND s2.y <= (s1.y*(1+factor))) OR (s2.y >= (s1.x*(1-factor)) AND s2.y <= (s1.x*(1+factor))) OR (s2.y >= (s1.z*(1-factor)) AND s2.y <= (s1.z*(1+factor))) THEN
                if (s2.z >= (s1.z*(1-factor)) AND s2.z <= (s1.z*(1+factor))) OR (s2.z >= (s1.x*(1-factor)) AND s2.z <= (s1.x*(1+factor))) OR (s2.z >= (s1.y*(1-factor)) AND s2.z <= (s1.y*(1+factor))) THEN
                (
                    dbgSelSim ("  Size match on '" + obj1.name + "' with '" + obj2.name + "'")
                    return true
                )
                else return false
            else return false
        else return false           
        """
        )


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

# deprecated:

# maxEval('max tti')

# maxEval('macros.run \"PolyTools\" \"TransformTools\")


# def b000(self):
#   '''
#   Transform: negative
#   '''
#   #change the textfield to neg value and call performTransformations
#   textfield = float(self.sb.transform.s000.value())
#   if textfield >=0:
#       newText = -textfield
#       self.sb.transform.s000.setValue(newText)
#   self.performTransformations()


# def b001(self):
#   '''
#   Transform: positive
#   '''
#   #change the textfield to pos value and call performTransformations
#   textfield = float(self.sb.transform.s000.value())
#   if textfield <0:
#       newText = abs(textfield)
#       self.sb.transform.s000.setValue(newText)
#   self.performTransformations()
