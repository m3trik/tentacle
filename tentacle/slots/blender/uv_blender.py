# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.uv import Uv


class Uv_blender(Uv, SlotsBlender):
    def __init__(self, *args, **kwargs):
        SlotsBlender.__init__(self, *args, **kwargs)
        Uv.__init__(self, *args, **kwargs)

        cmb000 = self.sb.uv.draggableHeader.ctx_menu.cmb000
        items = []
        cmb000.addItems_(items, "UV Editors")

        cmb001 = self.sb.uv.cmb001
        # panel = pm.get_panel(scriptType='polyTexturePlacementPanel')
        # cmb001.option_menu.chk014.setChecked(pm.textureWindow(panel, displayCheckered=1, q=True)) #checkered state
        # cmb001.option_menu.chk015.setChecked(True if pm.polyOptions(q=True, displayMapBorder=1) else False) #borders state
        # cmb001.option_menu.chk016.setChecked(pm.textureWindow(panel, q=True, displayDistortion=1)) #distortion state

        cmb002 = self.sb.uv.cmb002
        items = []
        cmb002.addItems_(items, "Transform:")

        tb000 = self.sb.uv.tb000
        tb000.option_menu.add(
            "QSpinBox",
            setPrefix="Pre-Scale Mode: ",
            setObjectName="s009",
            set_limits="0-2 step1",
            setValue=1,
            setToolTip="Allow shell scaling during packing.",
        )
        tb000.option_menu.add(
            "QSpinBox",
            setPrefix="Pre-Rotate Mode: ",
            setObjectName="s010",
            set_limits="0-2 step1",
            setValue=1,
            setToolTip="Allow shell rotation during packing.",
        )
        tb000.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Rotate Step: ",
            setObjectName="s007",
            set_limits="0.0-360 step22.5",
            setValue=22.5,
            setToolTip="Set the allowed rotation increment contraint.",
        )
        tb000.option_menu.add(
            "QSpinBox",
            setPrefix="Stack Similar: ",
            setObjectName="s011",
            set_limits="0-2 step1",
            setValue=0,
            setToolTip="Find Similar shells. <br>state 1: Find similar shells, and pack one of each, ommiting the rest.<br>state 2: Find similar shells, and stack during packing.",
        )
        tb000.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s006",
            set_limits="0.0-10 step.1",
            setValue=1.0,
            setToolTip="Stack Similar: Stack shells with uv's within the given range.",
        )
        tb000.option_menu.add(
            "QSpinBox",
            setPrefix="UDIM: ",
            setObjectName="s004",
            set_limits="1001-1200 step1",
            setValue=1001,
            setToolTip="Set the desired UDIM tile space.",
        )
        tb000.option_menu.add(
            "QSpinBox",
            setPrefix="Map Size: ",
            setObjectName="s005",
            set_limits="512-8192 step512",
            setValue=2048,
            setToolTip="UV map resolution.",
        )

        tb007 = self.sb.uv.tb007
        # tb007.option_menu.b099.released.connect(lambda: tb007.option_menu.s003.setValue(float(pm.mel.texGetTexelDensity(tb007.option_menu.s002.value())))) #get and set texel density value.

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.uv.draggableHeader.ctx_menu.cmb000

        if index > 0:  # hide main menu and perform operation
            text = cmb.items[index]
            self.sb.parent().hide()
            if text == "UV Editor":
                mel.eval("TextureViewWindow;")
            elif text == "UV Set Editor":
                mel.eval("uvSetEditor;")
            elif text == "UV Tool Kit":
                mel.eval("toggleUVToolkit;")
            elif text == "UV Linking: Texture-Centric":
                mel.eval("textureCentricUvLinkingEditor;")
            elif text == "UV Linking: UV-Centric":
                mel.eval("uvCentricUvLinkingEditor;")
            elif text == "UV Linking: Paint Effects/UV":
                mel.eval("pfxUVLinkingEditor;")
            elif text == "UV Linking: Hair/UV":
                mel.eval("hairUVLinkingEditor;")
            elif text == "Flip UV":
                mel.eval("performPolyForceUV flip 1;")
            cmb.setCurrentIndex(0)

    def cmb001(self, *args, **kwargs):
        """Display"""
        cmb = self.sb.uv.cmb001

    def cmb002(self, *args, **kwargs):
        """Transform"""
        cmb = self.sb.uv.cmb002

        if index > 0:
            text = cmb.items[index]
            self.sb.parent().hide()  # hide hotbox then perform operation
            if text == "Flip U":
                pm.polyFlipUV(flipType=0, local=1, usePivot=1, pivotU=0, pivotV=0)
            elif text == "Flip V":
                pm.polyFlipUV(flipType=1, local=1, usePivot=1, pivotU=0, pivotV=0)
            elif text == "Align U Left":
                pm.mel.performAlignUV("minU")
            elif text == "Align U Middle":
                pm.mel.performAlignUV("avgU")
            elif text == "Align U Right":
                pm.mel.performAlignUV("maxU")
            elif text == "Align U Top":
                pm.mel.performAlignUV("maxV")
            elif text == "Align U Middle":
                pm.mel.performAlignUV("avgV")
            elif text == "Align U Bottom":
                pm.mel.performAlignUV("minV")
            elif text == "Linear Align":
                pm.mel.performLinearAlignUV()
            cmb.setCurrentIndex(0)

    def chk014(self):
        """Display: Checkered Pattern"""
        cmb = self.sb.uv.cmb001
        state = cmb.option_menu.chk014.isChecked()

        panel = pm.get_panel(scriptType="polyTexturePlacementPanel")
        pm.textureWindow(panel, edit=1, displayCheckered=state)

    def chk015(self):
        """Display: Borders"""
        cmb = self.sb.uv.cmb001
        state = cmb.option_menu.chk015.isChecked()

        borderWidth = pm.optionVar(query="displayPolyBorderEdgeSize")[1]
        borders = pm.polyOptions(displayMapBorder=state, sizeBorder=borderWidth)

    def chk016(self):
        """Display: Distortion"""
        cmb = self.sb.uv.cmb001
        state = cmb.option_menu.chk016.isChecked()

        panel = pm.get_panel(scriptType="polyTexturePlacementPanel")
        pm.textureWindow(panel, edit=1, displayDistortion=state)

    def tb000(self, *args, **kwargs):
        """Pack UV's

        pm.u3dLayout:
                layoutScaleMode (int),
                multiObject (bool),
                mutations (int),
                packBox (float, float, float, float),
                preRotateMode (int),
                preScaleMode (int),
                resolution (int),
                rotateMax (float),
                rotateMin (float),
                rotateStep (float),
                shellSpacing (float),
                tileAssignMode (int),
                tileMargin (float),
                tileU (int),
                tileV (int),
                translate (bool)
        """
        tb = self.sb.uv.tb000

        scale = tb.option_menu.s009.value()
        rotate = tb.option_menu.s010.value()
        rotateStep = tb.option_menu.s007.value()
        UDIM = tb.option_menu.s004.value()
        mapSize = tb.option_menu.s005.value()
        similar = tb.option_menu.s011.value()
        tolerance = tb.option_menu.s006.value()

        U, D, I, M = [int(i) for i in str(UDIM)]

        sel = self.UvShellSelection()  # assure the correct selection mask.
        if similar > 0:
            dissimilar = pm.polyUVStackSimilarShells(
                sel, tolerance=tolerance, onlyMatch=True
            )
            dissimilarUVs = [s.split() for s in dissimilar] if dissimilar else []
            dissimilarFaces = pm.polyListComponentConversion(
                dissimilarUVs, fromUV=1, toFace=1
            )
            pm.u3dLayout(
                dissimilarFaces,
                resolution=mapSize,
                preScaleMode=scale,
                preRotateMode=rotate,
                rotateStep=rotateStep,
                shellSpacing=0.005,
                tileMargin=0.005,
                packBox=[M - 1, D, I, U],
            )  # layoutScaleMode (int), multiObject (bool), mutations (int), packBox (float, float, float, float), preRotateMode (int), preScaleMode (int), resolution (int), rotateMax (float), rotateMin (float), rotateStep (float), shellSpacing (float), tileAssignMode (int), tileMargin (float), tileU (int), tileV (int), translate (bool)

        elif similar == 2:
            pm.select(dissimilarFaces, toggle=1)
            similarFaces = pm.ls(sl=1)
            pm.polyUVStackSimilarShells(
                similarFaces, dissimilarFaces, tolerance=tolerance
            )

        else:
            pm.u3dLayout(
                sel,
                resolution=mapSize,
                preScaleMode=scale,
                preRotateMode=rotate,
                rotateStep=rotateStep,
                shellSpacing=0.005,
                tileMargin=0.005,
                packBox=[M - 1, D, I, U],
            )  # layoutScaleMode (int), multiObject (bool), mutations (int), packBox (float, float, float, float), preRotateMode (int), preScaleMode (int), resolution (int), rotateMax (float), rotateMin (float), rotateStep (float), shellSpacing (float), tileAssignMode (int), tileMargin (float), tileU (int), tileV (int), translate (bool)

    @SlotsBlender.attr
    def tb001(self, *args, **kwargs):
        """Auto Unwrap"""
        tb = self.sb.uv.tb001

        standardUnwrap = tb.option_menu.chk000.isChecked()
        scaleMode = tb.option_menu.chk001.isChecked()
        seamOnly = tb.option_menu.chk002.isChecked()
        planarUnwrap = tb.option_menu.chk003.isChecked()
        cylindricalUnwrap = tb.option_menu.chk004.isChecked()
        sphericalUnwrap = tb.option_menu.chk005.isChecked()
        normalBasedUnwrap = tb.option_menu.chk006.isChecked()

        selection = pm.ls(sl=True, flatten=1)
        for obj in selection:
            try:
                if seamOnly:
                    autoSeam = pm.u3dAutoSeam(obj, s=0, p=1)
                    return autoSeam if len(selection) == 1 else autoSeam

                elif any((cylindricalUnwrap, sphericalUnwrap, planarUnwrap)):
                    unwrapType = "Planar"
                    if cylindricalUnwrap:
                        unwrapType = "Cylindrical"
                    elif sphericalUnwrap:
                        unwrapType = "Spherical"
                    objFaces = mtk.Cmpt.get_components("f")
                    if not objFaces:
                        objFaces = mtk.Cmpt.get_components(obj, "f")
                    pm.polyProjection(
                        objFaces, type=unwrapType, insertBeforeDeformers=1, smartFit=1
                    )

                elif normalBasedUnwrap:
                    pm.mel.texNormalProjection(1, 1, obj)  # Normal-Based unwrap

                elif standardUnwrap:
                    polyAutoProjection = pm.polyAutoProjection(
                        obj,
                        layoutMethod=0,
                        optimize=1,
                        insertBeforeDeformers=1,
                        scaleMode=scaleMode,
                        createNewMap=False,  # Create a new UV set, as opposed to editing the current one, or the one given by the -uvSetName flag.
                        projectBothDirections=0,  # If "on" : projections are mirrored on directly opposite faces. If "off" : projections are not mirrored on opposite faces.
                        layout=2,  # 0 UV pieces are set to no layout. 1 UV pieces are aligned along the U axis. 2 UV pieces are moved in a square shape.
                        planes=6,  # intermediate projections used. Valid numbers are 4, 5, 6, 8, and 12
                        percentageSpace=0.2,  # percentage of the texture area which is added around each UV piece.
                        worldSpace=0,
                    )  # 1=world reference. 0=object reference.

                    return (
                        polyAutoProjection
                        if len(selection) == 1
                        else polyAutoProjection
                    )

            except Exception as error:
                print(error)

    def tb002(self, *args, **kwargs):
        """Stack"""
        tb = self.sb.uv.tb002

        orient = tb.option_menu.chk021.isChecked()
        stackSimilar = tb.option_menu.chk022.isChecked()
        tolerance = tb.option_menu.s000.value()
        sel = self.UvShellSelection()  # assure the correct selection mask.

        if stackSimilar:
            pm.polyUVStackSimilarShells(sel, tolerance=tolerance)
        else:
            pm.mel.texStackShells([])
        if orient:
            pm.mel.texOrientShells()

    def tb003(self, *args, **kwargs):
        """Select By Type"""
        tb = self.sb.uv.tb003

        back_facing = tb.option_menu.chk008.isChecked()
        front_facing = tb.option_menu.chk009.isChecked()
        overlapping = tb.option_menu.chk010.isChecked()
        nonOverlapping = tb.option_menu.chk011.isChecked()
        textureBorders = tb.option_menu.chk012.isChecked()
        unmapped = tb.option_menu.chk013.isChecked()

        if back_facing:
            pm.mel.selectUVFaceOrientationComponents({}, 0, 2, 1)
        elif front_facing:
            pm.mel.selectUVFaceOrientationComponents({}, 0, 1, 1)
        elif overlapping:
            pm.mel.selectUVOverlappingComponents(1, 0)
        elif nonOverlapping:
            pm.mel.selectUVOverlappingComponents(0, 0)
        elif textureBorders:
            pm.mel.selectUVBorderComponents({}, "", 1)
        elif unmapped:
            pm.mel.selectUnmappedFaces()

    def tb004(self, *args, **kwargs):
        """Unfold

        Synopsis: u3dUnfold [flags] [String...]
        Flags:
          -bi -borderintersection  on|off
         -ite -iterations          Int
          -ms -mapsize             Int
           -p -pack                on|off
          -rs -roomspace           Int
          -tf -triangleflip        on|off

        Synopsis: u3dOptimize [flags] [String...]
        Flags:
          -bi -borderintersection  on|off
         -ite -iterations          Int
          -ms -mapsize             Int
         -pow -power               Int
          -rs -roomspace           Int
          -sa -surfangle           Float
          -tf -triangleflip        on|off
        """
        tb = self.sb.uv.tb004

        optimize = tb.option_menu.chk017.isChecked()
        amount = 1  # tb.option_menu.s008.value()

        pm.u3dUnfold(
            iterations=1,
            pack=0,
            borderintersection=1,
            triangleflip=1,
            mapsize=2048,
            roomspace=0,
        )  # pm.mel.performUnfold(0)

        if optimize:
            pm.u3dOptimize(
                iterations=amount,
                power=1,
                surfangle=1,
                borderintersection=0,
                triangleflip=1,
                mapsize=2048,
                roomspace=0,
            )  # pm.mel.performPolyOptimizeUV(0)

    def tb005(self, *args, **kwargs):
        """Straighten Uv"""
        tb = self.sb.uv.tb005

        u = tb.option_menu.chk018.isChecked()
        v = tb.option_menu.chk019.isChecked()
        angle = tb.option_menu.s001.value()
        straightenShell = tb.option_menu.chk020.isChecked()

        if u and v:
            pm.mel.texStraightenUVs("UV", angle)
        elif u:
            pm.mel.texStraightenUVs("U", angle)
        elif v:
            pm.mel.texStraightenUVs("V", angle)

        if straightenShell:
            pm.mel.texStraightenShell()

    def tb006(self, *args, **kwargs):
        """Distribute"""
        tb = self.sb.uv.tb006

        u = tb.option_menu.chk023.isChecked()
        v = tb.option_menu.chk024.isChecked()

        if u:
            pm.mel.texDistributeShells(0, 0, "right", [])  #'left', 'right'
        if v:
            pm.mel.texDistributeShells(0, 0, "down", [])  #'up', 'down'

    def tb007(self, *args, **kwargs):
        """Set Texel Density"""
        tb = self.sb.uv.tb007

        mapSize = tb.option_menu.s002.value()
        density = tb.option_menu.s003.value()

        pm.mel.texSetTexelDensity(density, mapSize)

    def b001(self):
        """Create UV Snapshot"""
        pm.mel.UVCreateSnapshot()

    @SlotsBlender.undoChunk
    def b002(self):
        """Transfer UV's"""
        selection = pm.ls(orderedSelection=1, flatten=1)
        if len(selection) < 2:
            return "Error: <b>Nothing selected.</b><br>The operation requires the selection of two polygon objects."

        # pm.undoInfo(openChunk=1)
        set1 = pm.listRelatives(selection[0], children=1)
        set2 = pm.listRelatives(selection[1:], children=1)

        for frm in set1:
            for to in set2:
                if pm.polyEvaluate(frm) == pm.polyEvaluate(to):
                    pm.transferAttributes(
                        frm, to, transferUVs=2, sampleSpace=4
                    )  # -transferNormals 0 -transferUVs 2 -transferColors 2 -sourceUvSpace "map1" -targetUvSpace "map1" -searchMethod 3-flipUVs 0 -colorBorders 1 ;
                    pm.bakePartialHistory(to, prePostDeformers=1)
                    set2.remove(
                        to
                    )  # remove the obj from the transfer list when an exact match is found.
                elif pm.polyEvaluate(frm, face=1) == pm.polyEvaluate(
                    to, face=1
                ) and pm.polyEvaluate(frm, boundingBox=1) == pm.polyEvaluate(
                    to, boundingBox=1
                ):
                    pm.transferAttributes(
                        frm, to, transferUVs=2, sampleSpace=4
                    )  # transfer to the object if it is similar, but keep in transfer list in case an exact match is found later.
                    pm.bakePartialHistory(to, prePostDeformers=1)

        for remaining in set2:
            print("Error: No match found for: {}.".format(remaining.name()))
        # pm.undoInfo(closeChunk=1)

    def b005(self):
        """Cut UV's"""
        objects = pm.ls(sl=True, objectsOnly=1, shapes=1, flatten=1)

        for obj in objects:
            sel = pm.ls(obj, sl=1)
            pm.polyMapCut(sel)

    def b011(self):
        """Sew UV's"""
        objects = pm.ls(sl=True, objectsOnly=1, shapes=1, flatten=1)

        for obj in objects:
            sel = pm.ls(obj, sl=1)

            pm.polyMapSew(sel) if len(objects) == 1 else pm.polyMapSew(sel)

    def moveSelectedToUvSpace(self, u, v, relative=True):
        """Move sny selected objects to the given u and v coordinates.

        Parameters:
                u (int): u coordinate.
                v (int): v coordinate.
                relative (bool): Move relative or absolute.
        """
        sel = self.UvShellSelection()  # assure the correct selection mask.

        pm.polyEditUV(sel, u=u, v=v, relative=relative)

    def UvShellSelection(self):
        """Select all faces of any selected geometry, and switch the component mode to uv shell,
        if the current selection is not maskFacet, maskUv, or maskUvShell.

        Returns:
                (list) the selected faces.
        """
        selection = pm.ls(sl=1)
        if not selection:
            return "Error: <b>Nothing selected.<b><br>The operation requires at lease one selected object."

        objects = pm.ls(selection, objectsOnly=1)
        objectMode = pm.selectMode(q=True, object=1)

        maskFacet = pm.selectType(q=True, facet=1)
        maskUv = pm.selectType(q=True, polymeshUV=1)
        maskUvShell = pm.selectType(q=True, meshUVShell=1)

        if all((objects, objectMode)) or not any(
            (objectMode, maskFacet, maskUv, maskUvShell)
        ):
            for obj in objects:
                pm.selectMode(component=1)
                pm.selectType(meshUVShell=1)
                selection = mtk.Cmpt.get_components(obj, "f", flatten=False)
                pm.select(selection, add=True)

        return selection

    def getUvShellSets(self, objects=None, returned_type="shells"):
        """Get All UV shells and their corresponding sets of faces.

        Parameters:
                objects (obj/list): Polygon object(s) or Polygon face(s).
                returned_type (str): The desired returned type. valid values are: 'shells', 'shellIDs'. If None is given, the full dict will be returned.

        Returns:
                (list)(dict) dependant on the given returned_type arg. ex. {0L:[[MeshFace(u'pShape.f[0]'), MeshFace(u'pShape.f[1]')], 1L:[[MeshFace(u'pShape.f[2]'), MeshFace(u'pShape.f[3]')]}
        """
        if not objects:
            objects = pm.ls(sl=True, objectsOnly=1, transforms=1, flatten=1)

        if not isinstance(objects, (list, set, tuple)):
            objects = [objects]

        objectType = self.get_type(objects[0])
        if objectType == "Polygon Face":
            faces = objects
        else:
            faces = mtk.Cmpt.get_components(objects, "faces")

        shells = {}
        for face in faces:
            shell_Id = pm.polyEvaluate(face, uvShellIds=True)

            try:
                shells[shell_Id[0]].append(face)
            except KeyError:
                try:
                    shells[shell_Id[0]] = [face]
                except IndexError:
                    pass

        if returned_type == "shells":
            shells = list(shells.values())
        elif returned_type == "shellIDs":
            shells = shells.keys()

        return shells

    def getUvShellBorderEdges(self, objects):
        """Get the edges that make up any UV islands of the given objects.

        Parameters:
                objects (str/obj/list): Polygon mesh objects.

        Returns:
                (list) uv border edges.
        """
        mesh_edges = []
        for obj in pm.ls(objects, objectsOnly=1):
            try:  # Try to get edges from provided objects.
                mesh_edges.extend(
                    pm.ls(pm.polyListComponentConversion(obj, te=True), fl=True, l=True)
                )
            except Exception as error:
                pass

        if len(mesh_edges) <= 0:  # Error if no valid objects were found
            raise RuntimeError("No valid mesh objects or components were provided.")

        pm.progressWindow(
            t="Find UV Border Edges", pr=0, max=len(mesh_edges), ii=True
        )  # Start progressWindow

        uv_border_edges = list()  # Find and return uv border edges
        for edge in mesh_edges:  # Filter through the mesh(s) edges.
            if pm.progressWindow(
                q=True, ic=True
            ):  # Kill if progress window is cancelled
                pm.progressWindow(ep=True)  # End progressWindow
                raise RuntimeError("Cancelled by user.")

            pm.progressWindow(e=True, s=1, st=edge)  # Update the progress window status

            edge_uvs = pm.ls(pm.polyListComponentConversion(edge, tuv=True), fl=True)
            edge_faces = pm.ls(pm.polyListComponentConversion(edge, tf=True), fl=True)
            if (
                len(edge_uvs) > 2
            ):  # If an edge has more than two uvs, it is a uv border edge.
                uv_border_edges.append(edge)
            elif (
                len(edge_faces) < 2
            ):  # If an edge has less than 2 faces, it is a border edge.
                uv_border_edges.append(edge)

        pm.progressWindow(ep=True)  # End progressWindow

        return uv_border_edges


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
