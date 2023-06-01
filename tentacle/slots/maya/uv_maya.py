# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)

import mayatk as mtk
from tentacle.slots.maya import SlotsMaya
from tentacle.slots.uv import Uv


class Uv_maya(Uv, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb.preferences.slots.loadPlugin(
            "Unfold3D.mll"
        )  # assure the maya UV plugin is loaded.

        cmb000 = self.sb.uv.draggableHeader.ctx_menu.cmb000
        items = [
            "UV Editor",
            "UV Set Editor",
            "UV Tool Kit",
            "UV Linking: Texture-Centric",
            "UV Linking: UV-Centric",
            "UV Linking: Paint Effects/UV",
            "UV Linking: Hair/UV",
            "Flip UV",
        ]
        cmb000.addItems_(items, "Maya UV Editors")

        cmb001 = self.sb.uv.cmb001
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        cmb001.option_menu.chk014.setChecked(
            pm.textureWindow(panel, displayCheckered=1, query=1)
        )  # checkered state
        cmb001.option_menu.chk015.setChecked(
            True if pm.polyOptions(query=1, displayMapBorder=1) else False
        )  # borders state
        cmb001.option_menu.chk016.setChecked(
            pm.textureWindow(panel, query=1, displayDistortion=1)
        )  # distortion state

        cmb002 = self.sb.uv.cmb002
        items = [
            "Flip U",
            "Flip V",
            "Align U Left",
            "Align U Middle",
            "Align U Right",
            "Align V Top",
            "Align V Middle",
            "Align V Bottom",
            "Linear Align",
        ]
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
            setValue=0,
            setToolTip="Allow shell rotation during packing.",
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
            setPrefix="Padding: ",
            setObjectName="s012",
            set_limits="0-999 step1",
            setValue=self.getMapSize() / 256 * 2,
            setToolTip="Set the shell spacing amount.",
        )

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.uv.draggableHeader.ctx_menu.cmb000

        if index > 0:  # hide main menu and perform operation
            text = cmb.items[index]
            self.sb.parent().hide()
            if text == "UV Editor":
                pm.mel.eval("TextureViewWindow;")
            elif text == "UV Set Editor":
                pm.mel.eval("uvSetEditor;")
            elif text == "UV Tool Kit":
                pm.mel.eval("toggleUVToolkit;")
            elif text == "UV Linking: Texture-Centric":
                pm.mel.eval("textureCentricUvLinkingEditor;")
            elif text == "UV Linking: UV-Centric":
                pm.mel.eval("uvCentricUvLinkingEditor;")
            elif text == "UV Linking: Paint Effects/UV":
                pm.mel.eval("pfxUVLinkingEditor;")
            elif text == "UV Linking: Hair/UV":
                pm.mel.eval("hairUVLinkingEditor;")
            elif text == "Flip UV":
                pm.mel.eval("performPolyForceUV flip 1;")
            cmb.setCurrentIndex(0)

    def cmb001(self, index=-1):
        """Display"""
        cmb = self.sb.uv.cmb001

    def cmb002(self, index=-1):
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

        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
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

        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        pm.textureWindow(panel, edit=1, displayDistortion=state)

    def tb000(self, state=None):
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
        UDIM = tb.option_menu.s004.value()
        padding = tb.option_menu.s012.value()
        similar = tb.option_menu.s011.value()
        tolerance = tb.option_menu.s006.value()
        mapSize = self.getMapSize()

        U, D, I, M = [int(i) for i in str(UDIM)]  # UDIM ex. '1001'
        shellPadding = padding * 0.000244140625
        tilePadding = shellPadding / 2
        sel = self.uvShellSelection()  # assure the correct selection mask.

        # if rotate==0:
        #   self.orientShells(sel)

        # if similar>0:
        #   dissimilar = pm.polyUVStackSimilarShells(sel, tolerance=tolerance, onlyMatch=True)
        #   dissimilarUVs = [s.split() for s in dissimilar] if dissimilar else []
        #   dissimilarFaces = pm.polyListComponentConversion(dissimilarUVs, fromUV=1, toFace=1)
        #   pm.u3dLayout(dissimilarFaces, resolution=mapSize, shellSpacing=shellPadding, tileMargin=tilePadding, preScaleMode=scale, preRotateMode=rotate, packBox=[M-1, D, I, U]) #layoutScaleMode (int), multiObject (bool), mutations (int), packBox (float, float, float, float), preRotateMode (int), preScaleMode (int), resolution (int), rotateMax (float), rotateMin (float), rotateStep (float), shellSpacing (float), tileAssignMode (int), tileMargin (float), tileU (int), tileV (int), translate (bool)

        # elif similar==2:
        #   pm.select(dissimilarFaces, toggle=1)
        #   similarFaces = pm.ls(sl=1)
        #   pm.polyUVStackSimilarShells(similarFaces, dissimilarFaces, tolerance=tolerance)

        # else:
        pm.u3dLayout(
            sel,
            scl=similar,
            resolution=mapSize,
            shellSpacing=shellPadding,
            tileMargin=tilePadding,
            preScaleMode=scale,
            preRotateMode=rotate,
            packBox=[M - 1, D, I, U],
        )  # layoutScaleMode (int), multiObject (bool), mutations (int), packBox (float, float, float, float), preRotateMode (int), preScaleMode (int), resolution (int), rotateMax (float), rotateMin (float), rotateStep (float), shellSpacing (float), tileAssignMode (int), tileMargin (float), tileU (int), tileV (int), translate (bool)

    @mtk.undo
    @SlotsMaya.attr
    def tb001(self, state=None):
        """Auto Unwrap"""
        tb = self.sb.uv.tb001

        standardUnwrap = tb.option_menu.chk000.isChecked()
        scaleMode = tb.option_menu.chk001.isChecked()
        seamOnly = tb.option_menu.chk002.isChecked()
        planarUnwrap = tb.option_menu.chk003.isChecked()
        cylindricalUnwrap = tb.option_menu.chk004.isChecked()
        sphericalUnwrap = tb.option_menu.chk005.isChecked()
        normalBasedUnwrap = tb.option_menu.chk006.isChecked()

        selection = pm.ls(selection=1, flatten=1)
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
                    objFaces = mtk.Cmpt.get_components(obj, "f")
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

                    if len(selection) == 1:
                        return polyAutoProjection

            except Exception as error:
                print(error)

    def tb003(self, state=None):
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

    def tb004(self, state=None):
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
        orient = tb.option_menu.chk007.isChecked()
        stackSimilar = tb.option_menu.chk022.isChecked()
        tolerance = tb.option_menu.s000.value()
        mapSize = self.getMapSize()

        pm.u3dUnfold(
            iterations=1,
            pack=0,
            borderintersection=1,
            triangleflip=1,
            mapsize=mapSize,
            roomspace=0,
        )  # pm.mel.performUnfold(0)

        if optimize:
            pm.u3dOptimize(
                iterations=10,
                power=1,
                surfangle=1,
                borderintersection=0,
                triangleflip=1,
                mapsize=mapSize,
                roomspace=0,
            )  # pm.mel.performPolyOptimizeUV(0)

        if orient:
            pm.mel.texOrientShells()

        if stackSimilar:
            pm.polyUVStackSimilarShells(tolerance=tolerance)

    def tb005(self, state=None):
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

    def tb006(self, state=None):
        """Distribute"""
        tb = self.sb.uv.tb006

        u = tb.option_menu.chk023.isChecked()
        v = tb.option_menu.chk024.isChecked()

        if u:
            pm.mel.texDistributeShells(0, 0, "right", [])  #'left', 'right'
        if v:
            pm.mel.texDistributeShells(0, 0, "down", [])  #'up', 'down'

    @mtk.undo
    def tb008(self, state=None):
        """Transfer UV's"""
        tb = self.sb.uv.tb008

        toSimilar = tb.option_menu.chk025.isChecked()
        similarTol = tb.option_menu.s013.value()
        deleteConstHist = tb.option_menu.chk026.isChecked()

        frm, *to = pm.ls(orderedSelection=1, flatten=1)
        if toSimilar:
            to = "similar"
        elif not to:
            return self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires the selection of two polygon objects."
            )

        self.transferUVs(frm, to, tolerance=similarTol, deleteConstHist=deleteConstHist)

    def b001(self):
        """Create UV Snapshot"""
        pm.mel.UVCreateSnapshot()

    def b002(self):
        """Stack Shells"""
        pm.mel.texStackShells({})
        # pm.mel.texOrientShells()

    def b003(self):
        """Get texel density."""
        density = pm.mel.texGetTexelDensity(self.getMapSize())
        self.sb.uv.s003.setValue(density)

    def b004(self):
        """Set Texel Density"""
        density = self.sb.uv.s003.value()
        mapSize = self.getMapSize()
        pm.mel.texSetTexelDensity(density, mapSize)

    def b005(self):
        """Cut UV's"""
        objects = pm.ls(selection=1, objectsOnly=1, flatten=1)

        for obj in objects:
            if pm.selectMode(query=1, object=1):  # use all edges when in object mode.
                edges = obj.e[:]
            else:  # get any selected edges.
                edges = pm.ls(obj, sl=1)

            pm.polyMapCut(edges)

    def b006(self):
        """Rotate UV's 90"""
        angle = 45
        # issue with getting rotate pivot; queries returning None instead of float values.
        objects = pm.ls(selection=1, objectsOnly=1)
        # for obj in objects:
        #   pu = pm.polyEditUV(obj, q=True, pivotU=True)
        #   pv = pm.polyEditUV(obj, q=True, pivotV=True)

        #   pm.polyEditUV(obj, pivotU=pu, pivotV=pv, angle=angle, relative=True)
        pm.polyEditUV(objects, angle=angle, rr=True)

    def b011(self):
        """Sew UV's"""
        objects = pm.ls(selection=1, objectsOnly=1, flatten=1)

        for obj in objects:
            if pm.selectMode(query=1, object=1):  # use all edges when in object mode.
                edges = obj.e[:]
            else:  # get any selected edges.
                edges = pm.ls(obj, sl=1)

            pm.polyMapSew(edges)

    def orientShells(self, objects):
        """Rotate UV shells to run parallel with the most adjacent U or V axis of their bounding box.

        Parameters:
                objects (str/obj/list): Polygon mesh objects and/or components.
        """
        for obj in pm.ls(objects, objectsOnly=1):
            obj_compts = [
                i for i in objects if obj in pm.ls(i, objectsOnly=1)
            ]  # filter components for only this object.
            pm.polyLayoutUV(
                obj_compts,
                flipReversed=0,
                layout=0,
                layoutMethod=1,
                percentageSpace=0.2,
                rotateForBestFit=3,
                scale=0,
                separate=0,
            )

    def moveSelectedToUvSpace(self, u, v, relative=True):
        """Move sny selected objects to the given u and v coordinates.

        Parameters:
                u (int): u coordinate.
                v (int): v coordinate.
                relative (bool): Move relative or absolute.
        """
        sel = self.uvShellSelection()  # assure the correct selection mask.

        pm.polyEditUV(sel, u=u, v=v, relative=relative)

    @classmethod
    def uvShellSelection(cls):
        """Select all faces of any selected geometry.
        If the current selection is not maskFacet, maskUv, or maskUvShell,
        switch the component mode to uv shell.

        Returns:
                (list) the selected faces.
        """
        selection = pm.ls(sl=1)
        if not selection:
            cls.message_box(
                "<b>Nothing selected.<b><br>The operation requires at lease one selected object."
            )
            return

        objects = pm.ls(selection, objectsOnly=1)
        objectMode = pm.selectMode(query=1, object=1)

        maskFacet = pm.selectType(query=1, facet=1)
        maskUv = pm.selectType(query=1, polymeshUV=1)
        maskUvShell = pm.selectType(query=1, meshUVShell=1)

        if all((objects, objectMode)) or not any(
            (objectMode, maskFacet, maskUv, maskUvShell)
        ):
            selection = []
            for obj in objects:
                pm.selectMode(component=1)
                pm.selectType(meshUVShell=1)
                selection.append(obj.f[:])  # append all faces of the object.
            pm.select(selection, add=True)

        return selection

    @staticmethod
    def getUvShellSets(objects=None, returned_type="shells"):
        """Get All UV shells and their corresponding sets of faces.

        Parameters:
                objects (obj/list): Polygon object(s) or Polygon face(s).
                returned_type (str): The desired returned type. valid values are: 'shells', 'IDs'. If None is given, the full dict will be returned.

        Returns:
                (list)(dict) dependant on the given returned_type arg. ex. {0L:[[MeshFace(u'pShape.f[0]'), MeshFace(u'pShape.f[1]')], 1L:[[MeshFace(u'pShape.f[2]'), MeshFace(u'pShape.f[3]')]}
        """
        faces = mtk.Cmpt.get_components(objects, "faces", flatten=1)

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
        elif returned_type == "IDs":
            shells = shells.keys()

        return shells

    @staticmethod
    def getUvShellBorderEdges(objects):
        """Get the edges that make up any UV islands of the given objects.

        Parameters:
            objects (str/obj/list): Polygon objects, mesh UVs, or Edges.

        Returns:
            (list): UV border edges.
        """
        uv_border_edges = []
        for obj in pm.ls(objects):
            # If the obj is a mesh object, get its shape
            if isinstance(obj, pm.nt.Transform):
                obj = obj.getShape()

            # If the obj is a mesh shape, get its UV borders
            if isinstance(obj, pm.nt.Mesh):
                # Get the connected edges to the selected UVs
                connected_edges = pm.polyListComponentConversion(
                    obj, fromUV=True, toEdge=True
                )
                connected_edges = pm.ls(connected_edges, flatten=True)
            elif isinstance(obj, pm.general.MeshEdge):
                # If the object is already an edge, no conversion is necessary
                connected_edges = pm.ls(obj, flatten=True)
            elif isinstance(obj, pm.general.MeshUV):
                # If the object is a UV, convert it to its connected edges
                connected_edges = pm.polyListComponentConversion(
                    obj, fromUV=True, toEdge=True
                )
                connected_edges = pm.ls(connected_edges, flatten=True)
            else:
                raise ValueError(f"Unsupported object type: {type(obj)}")

            for edge in connected_edges:
                edge_uvs = pm.ls(
                    pm.polyListComponentConversion(edge, tuv=True), fl=True
                )
                edge_faces = pm.ls(
                    pm.polyListComponentConversion(edge, tf=True), fl=True
                )
                if (
                    len(edge_uvs) > 2 or len(edge_faces) < 2
                ):  # If an edge has more than two uvs or less than 2 faces, it's a uv border edge.
                    uv_border_edges.append(edge)

        return uv_border_edges

    @mtk.undo
    def transferUVs(
        self,
        frm,
        to="similar",
        tolerance=0.0,
        sampleSpace="component",
        deleteConstHist=True,
    ):
        """Transfer UV's from one group of objects to another.

        Parameters:
                frm (str/obj/list): The objects to transfer uv's from.
                to (str/obj/list): The objects to transfer uv's to.
                                If 'similar' is given, the scene will be searched for similar objects.
                tolerance (float) =
                sampleSpace (str): Selects which space the attribute transfer is performed in. valid: 'world', 'local', 'component', 'topology'
                deleteConstHist (bool): Remove construction history for the objects transferring from.
                                Otherwise, the UV's will be lost should any of the frm objects be deleted.
        """
        sampleSpace = {"world": 0, "local": 1, "component": 4, "topology": 5}[
            sampleSpace
        ]

        frm = pm.ls(frm)
        to = pm.ls(to)

        # pm.undoInfo(openChunk=1)
        for f in frm:
            if to == "similar":
                to = self.sb.edit.slots.get_similar_mesh(
                    f, tolerance=tolerance, face=1, area=1
                )

            for t in to:
                if pm.polyEvaluate(f, face=1, format=True) == pm.polyEvaluate(
                    t, face=1, format=True
                ):
                    pm.transferAttributes(
                        f,
                        t,
                        transferPositions=0,
                        transferNormals=0,
                        transferUVs=2,
                        transferColors=2,
                        sampleSpace=sampleSpace,
                        sourceUvSpace="map1",
                        searchMethod=3,
                        flipUVs=0,
                        colorBorders=1,
                    )  # transfer to the object if it is similar, but keep in transfer list in case an exact match is found later.
                    to.remove(
                        t
                    )  # remove the obj from the transfer list when an exact match is found.

        for remaining in to:
            print(
                "Result: No Exact match found for: {}. Making final attempt ..".format(
                    remaining.name()
                )
            )
            ss = 5 if sampleSpace != 5 else 4
            pm.transferAttributes(frm, remaining, transferUVs=2, sampleSpace=ss)

        pm.delete(frm, constructionHistory=deleteConstHist)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

# deprecated:

# for f in frm:
#   if to=='similar':
#       to = self.sb.edit.slots.get_similar_mesh(f, tolerance=tolerance, face=1, area=1)

#   for t in to:
#       if pm.polyEvaluate(f, face=1, area=1, format=True)==pm.polyEvaluate(t, face=1, area=1, format=True):
#           pm.polyTransfer(t, alternateObject=f, uvSets=True) # pm.transferAttributes(frm, to, transferUVs=2, sampleSpace=4) #-transferNormals 0 -transferUVs 2 -transferColors 2 -sourceUvSpace "map1" -targetUvSpace "map1" -searchMethod 3-flipUVs 0 -colorBorders 1 ;
#           to.remove(t) #remove the obj from the transfer list when an exact match is found.
#       elif pm.polyEvaluate(f, face=1, format=True)==pm.polyEvaluate(t, face=1, format=True):
#           pm.transferAttributes(f, t, transferPositions=0, transferNormals=0, transferUVs=2, transferColors=2, sampleSpace=5, sourceUvSpace='map1', searchMethod=3, flipUVs=0, colorBorders=1) #transfer to the object if it is similar, but keep in transfer list in case an exact match is found later.

# for remaining in to:
#   print('Result: No Exact match found for: {}. Making final attempt ..'.format(remaining.name()))
#   pm.transferAttributes(frm, remaining, transferUVs=2, sampleSpace=4)

# pm.delete(frm, constructionHistory=deleteConstHist)
# # pm.undoInfo(closeChunk=1)

# def transferUVs(frm, to):
#       '''
#       '''
#       # pm.undoInfo(openChunk=1)
#       set1 = pm.listRelatives(frm, children=1)
#       set2 = pm.listRelatives(to, children=1)

#       for frm in set1:
#           for to in set2:
#               if pm.polyEvaluate(frm)==pm.polyEvaluate(to):
#                   pm.polyTransfer(frm, alternateObject=to, uvSets=True) # pm.transferAttributes(frm, to, transferUVs=2, sampleSpace=4) #-transferNormals 0 -transferUVs 2 -transferColors 2 -sourceUvSpace "map1" -targetUvSpace "map1" -searchMethod 3-flipUVs 0 -colorBorders 1 ;
#                   set2.remove(to) #remove the obj from the transfer list when an exact match is found.
#               elif pm.polyEvaluate(frm, face=1)==pm.polyEvaluate(to, face=1) and pm.polyEvaluate(frm, boundingBox=1)==pm.polyEvaluate(to, boundingBox=1):
#                   print (frm, to, pm.polyEvaluate(frm, face=1), pm.polyEvaluate(frm))
#                   pm.transferAttributes(frm, to, transferUVs=2, sampleSpace=4) #transfer to the object if it is similar, but keep in transfer list in case an exact match is found later.

#       for remaining in set2:
#           print('Error: No match found for: {}.'.format(remaining.name()))
#           pm.transferAttributes(set1, remaining, transferUVs=2, sampleSpace=4)

#       pm.delete(to, constructionHistory=1)
#       # pm.undoInfo(closeChunk=1)
