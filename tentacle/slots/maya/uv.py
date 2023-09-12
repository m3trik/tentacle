# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Uv(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Assure the maya UV plugin is loaded
        self.sb.preferences.slots.loadPlugin("Unfold3D.mll")
        # get the map size from the combobox as an int. ie. 2048
        self.getMapSize = lambda: int(self.sb.uv.cmb003.currentText())

    def header_init(self, widget):
        """ """
        widget.menu.add(
            "QPushButton",
            setText="Create UV Snapshot",
            setObjectName="b001",
            setToolTip="Save an image file of the current UV layout.",
        )

    def cmb002_init(self, widget):
        """ """
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
        widget.add(items, header="Transform:")

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QSpinBox",
            setPrefix="Pre-Scale Mode: ",
            setObjectName="s009",
            set_limits=[0, 2],
            setValue=1,
            setToolTip="Allow shell scaling during packing.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Pre-Rotate Mode: ",
            setObjectName="s010",
            set_limits=[0, 2],
            setValue=0,
            setToolTip="Allow shell rotation during packing.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Stack Similar: ",
            setObjectName="s011",
            set_limits=[0, 2],
            setValue=0,
            setToolTip="Find Similar shells. <br>state 1: Find similar shells, and pack one of each, ommiting the rest.<br>state 2: Find similar shells, and stack during packing.",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s006",
            set_limits=[0, 10, 0.1, 1],
            setValue=1.0,
            setToolTip="Stack Similar: Stack shells with uv's within the given range.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="UDIM: ",
            setObjectName="s004",
            set_limits=[1001, 1200],
            setValue=1001,
            setToolTip="Set the desired UDIM tile space.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Padding: ",
            setObjectName="s012",
            set_limits=[0, 1000],
            setValue=self.getMapSize() / 256 * 2,
            setToolTip="Set the shell spacing amount.",
        )

    def tb000(self, widget):
        """Pack UVs"""
        scale = widget.menu.s009.value()
        rotate = widget.menu.s010.value()
        UDIM = widget.menu.s004.value()
        padding = widget.menu.s012.value()
        # similar = widget.menu.s011.value()
        # tolerance = widget.menu.s006.value()
        mapSize = self.getMapSize()

        U, D, I, M = [int(i) for i in str(UDIM)]  # UDIM ex. '1001'
        shellPadding = padding * 0.000244140625
        tilePadding = shellPadding / 2

        selection = pm.ls(sl=1)
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.<b><br>The operation requires at least one selected object."
            )
            return
        uvs = pm.polyListComponentConversion(selection, fromFace=True, toUV=True)
        uvs = pm.ls(uvs, flatten=True)

        pm.u3dLayout(
            uvs,
            resolution=mapSize,
            shellSpacing=shellPadding,
            tileMargin=tilePadding,
            preScaleMode=scale,
            preRotateMode=rotate,
            packBox=[M - 1, D, I, U],
        )

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QRadioButton",
            setText="Standard",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Scale Mode 1",
            setObjectName="chk001",
            setTristate=True,
            setChecked=True,
            setToolTip="0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Seam Only",
            setObjectName="chk002",
            setToolTip="Cut seams only.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Planar",
            setObjectName="chk003",
            setToolTip="Create UV texture coordinates for the current selection by using a planar projection shape.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Cylindrical",
            setObjectName="chk004",
            setToolTip="Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Spherical",
            setObjectName="chk005",
            setToolTip="Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Normal-Based",
            setObjectName="chk006",
            setToolTip="Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it's face normals.",
        )
        # widget.menu.chk001.toggled.connect(lambda state: self.sb.toggle_multi(widget.menu, setUnChecked='chk002-3') if state==1 else None)

    @mtk.undo
    def tb001(self, widget):
        """Auto Unwrap"""
        standardUnwrap = widget.menu.chk000.isChecked()
        scaleMode = widget.menu.chk001.isChecked()
        seamOnly = widget.menu.chk002.isChecked()
        planarUnwrap = widget.menu.chk003.isChecked()
        cylindricalUnwrap = widget.menu.chk004.isChecked()
        sphericalUnwrap = widget.menu.chk005.isChecked()
        normalBasedUnwrap = widget.menu.chk006.isChecked()

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
                    objFaces = mtk.get_components(obj, "f")
                    if not objFaces:
                        objFaces = mtk.get_components(obj, "f")
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

    def tb002_init(self, widget):
        """Toggle UV Display Options"""
        widget.menu.mode = "popup"
        widget.menu.position = "bottom"
        widget.menu.setTitle("DISPLAY OPTIONS")

        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        checkered_state = pm.textureWindow(panel, q=True, displayCheckered=True)
        borders_state = True if pm.polyOptions(q=True, displayMapBorder=True) else False
        distortion_state = pm.textureWindow(panel, q=True, displayDistortion=True)

        values = [
            ("chk014", "Checkered", checkered_state),
            ("chk015", "Borders", borders_state),
            ("chk016", "Distortion", distortion_state),
        ]
        [
            widget.menu.add(
                self.sb.CheckBox, setObjectName=chk, setText=typ, setChecked=state
            )
            for chk, typ, state in values
        ]

        widget.menu.chk014.toggled.connect(
            lambda state: pm.textureWindow(panel, edit=True, displayCheckered=state)
        )
        widget.menu.chk015.toggled.connect(
            lambda state: pm.polyOptions(displayMapBorder=state)
        )
        widget.menu.chk016.toggled.connect(
            lambda state: pm.textureWindow(panel, edit=True, displayDistortion=state)
        )

    def tb003_init(self, widget):
        """ """
        widget.menu.add(
            "QRadioButton",
            setText="Back-Facing",
            setObjectName="chk008",
            setToolTip="Select all back-facing (using counter-clockwise winding order) components for the current selection.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Front-Facing",
            setObjectName="chk009",
            setToolTip="Select all front-facing (using counter-clockwise winding order) components for the current selection.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Overlapping",
            setObjectName="chk010",
            setToolTip="Select all components that share the same uv space.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Non-Overlapping",
            setObjectName="chk011",
            setToolTip="Select all components that do not share the same uv space.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Texture Borders",
            setObjectName="chk012",
            setToolTip="Select all components on the borders of uv shells.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Unmapped",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Select unmapped faces in the current uv set.",
        )

    def tb003(self, widget):
        """Select By Type"""
        back_facing = widget.menu.chk008.isChecked()
        front_facing = widget.menu.chk009.isChecked()
        overlapping = widget.menu.chk010.isChecked()
        nonOverlapping = widget.menu.chk011.isChecked()
        textureBorders = widget.menu.chk012.isChecked()
        unmapped = widget.menu.chk013.isChecked()

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

    def tb004_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Optimize",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="The Optimize UV Tool evens out the spacing between UVs on a mesh, fixing areas of distortion (overlapping UVs).",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Orient",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Orient selected UV shells to run parallel with the most adjacent U or V axis.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Stack Similar",
            setObjectName="chk022",
            setChecked=True,
            setToolTip="Stack only shells that fall within the set tolerance.",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.1, 1],
            setValue=1.0,
            setToolTip="Stack shells with uv's within the given range.",
        )

    def tb004(self, widget):
        """Unfold"""
        optimize = widget.menu.chk017.isChecked()
        orient = widget.menu.chk007.isChecked()
        stackSimilar = widget.menu.chk022.isChecked()
        tolerance = widget.menu.s000.value()
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

    def tb005_init(self, widget):
        """ """
        widget.menu.add(
            "QSpinBox",
            setPrefix="Angle: ",
            setObjectName="s001",
            set_limits=[0, 360],
            setValue=30,
            setToolTip="Set the maximum angle used for straightening uv's.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Straighten U",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Unfold UV's along a horizonal contraint.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Straighten V",
            setObjectName="chk019",
            setChecked=True,
            setToolTip="Unfold UV's along a vertical constaint.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Straighten Shell",
            setObjectName="chk020",
            setToolTip="Straighten a UV shell by unfolding UV's around a selected UV's edgeloop.",
        )

    def tb005(self, widget):
        """Straighten Uv"""
        u = widget.menu.chk018.isChecked()
        v = widget.menu.chk019.isChecked()
        angle = widget.menu.s001.value()
        straightenShell = widget.menu.chk020.isChecked()

        if u and v:
            pm.mel.texStraightenUVs("UV", angle)
        elif u:
            pm.mel.texStraightenUVs("U", angle)
        elif v:
            pm.mel.texStraightenUVs("V", angle)

        if straightenShell:
            pm.mel.texStraightenShell()

    def tb006_init(self, widget):
        """ """
        widget.menu.add(
            "QRadioButton",
            setText="Distribute U",
            setObjectName="chk023",
            setChecked=True,
            setToolTip="Distribute along U.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Distribute V",
            setObjectName="chk024",
            setToolTip="Distribute along V.",
        )

    def tb006(self, widget):
        """Distribute"""
        u = widget.menu.chk023.isChecked()
        v = widget.menu.chk024.isChecked()

        if u:
            pm.mel.texDistributeShells(0, 0, "right", [])  # 'left', 'right'
        if v:
            pm.mel.texDistributeShells(0, 0, "down", [])  # 'up', 'down'

    @mtk.undo
    def tb008(self, widget):
        """Transfer UV's"""
        frm, *to = pm.ls(orderedSelection=1, flatten=1)
        if not to:
            return self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires the selection of two polygon objects."
            )

        for t in to:
            mtk.transfer_uvs(frm, t)

    def cmb002(self, index, widget):
        """Transform"""
        if index > 0:
            text = widget.items[index]
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
            widget.setCurrentIndex(0)

    def chk001(self, state, widget):
        """Auto Unwrap: Scale Mode CheckBox"""
        if state == 0:
            widget.menu.chk001.setText("Scale Mode 0")
        if state == 1:
            widget.menu.chk001.setText("Scale Mode 1")
            self.sb.toggle_multi(widget.menu, setUnChecked="chk002-6")
        if state == 2:
            widget.menu.chk001.setText("Scale Mode 2")

    def chk014(self, state, widget):
        """Display: Checkered Pattern"""
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        pm.textureWindow(panel, edit=1, displayCheckered=state)

    def chk015(self, state, widget):
        """Display: Borders"""
        borderWidth = pm.optionVar(query="displayPolyBorderEdgeSize")[1]
        pm.polyOptions(displayMapBorder=state, sizeBorder=borderWidth)

    def chk016(self, state, widget):
        """Display: Distortion"""
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        pm.textureWindow(panel, edit=1, displayDistortion=state)

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
        objects = pm.ls(sl=True, objectsOnly=1, flatten=1)

        for obj in objects:
            if pm.selectMode(q=True, object=1):  # use all edges when in object mode.
                edges = obj.e[:]
            else:  # get any selected edges.
                edges = pm.ls(obj, sl=1)

            pm.polyMapCut(edges)

    def b006(self):
        """Rotate UV's 90"""
        angle = 45
        # issue with getting rotate pivot; queries returning None instead of float values.
        objects = pm.ls(sl=True, objectsOnly=1)
        # for obj in objects:
        #   pu = pm.polyEditUV(obj, q=True, pivotU=True)
        #   pv = pm.polyEditUV(obj, q=True, pivotV=True)

        #   pm.polyEditUV(obj, pivotU=pu, pivotV=pv, angle=angle, relative=True)
        pm.polyEditUV(objects, angle=angle, rr=True)

    def b011(self):
        """Sew UV's"""
        objects = pm.ls(sl=True, objectsOnly=1, flatten=1)

        for obj in objects:
            if pm.selectMode(q=True, object=1):  # use all edges when in object mode.
                edges = obj.e[:]
            else:  # get any selected edges.
                edges = pm.ls(obj, sl=1)

            pm.polyMapSew(edges)

    def b021(self, widget):
        """Unfold and Pack UVs"""
        self.sb.uv.tb004.call_slot()  # perform unfold
        self.sb.uv.tb000.call_slot()  # perform pack

    def b022(self):
        """Cut UV hard edges"""
        # perform select edges by angle.
        self.sb.selection.tb003.call_slot()
        self.b005()  # perform cut.

    def b023(self):
        """Move To Uv Space: Left"""
        selection = pm.ls(sl=True)
        mtk.move_to_uv_space(selection, -1, 0)  # move left

    def b024(self):
        """Move To Uv Space: Down"""
        selection = pm.ls(sl=True)
        mtk.move_to_uv_space(selection, 0, -1)  # move down

    def b025(self):
        """Move To Uv Space: Up"""
        selection = pm.ls(sl=True)
        mtk.move_to_uv_space(selection, 0, 1)  # move up

    def b026(self):
        """Move To Uv Space: Right"""
        selection = pm.ls(sl=True)
        mtk.move_to_uv_space(selection, 1, 0)  # move right


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
