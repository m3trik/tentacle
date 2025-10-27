# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class UvSlots(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.uv
        self.submenu = self.sb.loaded_ui.uv_submenu

        # Assure the maya UV plugin is loaded
        mtk.load_plugin("Unfold3D.mll")

    def get_map_size(self):
        """Get the map size from the combobox as an int. ie. 2048"""
        return int(self.ui.cmb003.currentText())

    def header_init(self, widget):
        """ """
        widget.menu.add(
            "QPushButton",
            setText="Create UV Snapshot",
            setObjectName="uv_snapshot",
            setToolTip="Save an image file of the current UV layout.",
        )
        widget.menu.uv_snapshot.clicked.connect(pm.mel.UVCreateSnapshot)
        widget.menu.add(
            "QPushButton",
            setText="Open UV Editor",
            setObjectName="uv_editor",
            setToolTip="Open the texture coordinate mapping window.",
        )
        widget.menu.uv_editor.clicked.connect(pm.mel.TextureViewWindow)

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
        """Initialize UV packing tool interface.

        Sets up the UV packing options menu with controls for:
        - Pre-Scale Mode: Controls how UV shells are scaled before packing
        - Pre-Rotate Mode: Controls how UV shells are rotated during packing
        - Uniform Texel Density: Option to maintain consistent texture resolution
        - UDIM: Target UDIM tile space for the packed UVs

        Parameters:
            widget: The parent widget to add menu items to
        """
        widget.option_box.menu.setTitle("Pack: Options")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Pre-Scale Mode: ",
            setObjectName="s009",
            set_limits=[0, 2],
            setValue=1,
            setToolTip="Pre-scale mode for UV shells during packing:\n"
            "0 = No scaling (keep original size)\n"
            "1 = Uniform scaling (scale uniformly to fit)\n"
            "2 = Non-uniform scaling (stretch to optimize space)",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Pre-Rotate Mode: ",
            setObjectName="s010",
            set_limits=[0, 2],
            setValue=0,
            setToolTip="Pre-rotate mode for UV shells during packing:\n"
            "0 = No rotation (keep original orientation)\n"
            "1 = 90-degree steps only\n"
            "2 = Free rotation (any angle for optimal packing)",
        )
        # Rotation sampling controls (always available; respected when rotation enabled)
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Step: ",
            setObjectName="s011",
            set_limits=[1, 360],
            setValue=90,
            setToolTip="Increment (degrees) between tested rotations when Pre-Rotate Mode = 1 (stepped).\n"
            "A small increment can add lots of additional processing time.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Min: ",
            setObjectName="s012",
            set_limits=[0, 359],
            setValue=0,
            setToolTip="Minimum shell rotation (degrees) considered during packing.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Max: ",
            setObjectName="s013",
            set_limits=[0, 359],
            setValue=180,
            setToolTip="Maximum shell rotation (degrees) considered during packing.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="UDIM: ",
            setObjectName="s004",
            set_limits=[1001, 1200],
            setValue=1001,
            setToolTip="Set the desired UDIM tile space (1001-1200).\n"
            "1001 = First tile (0-1, 0-1 UV space)\n"
            "1002 = Second tile (1-2, 0-1 UV space), etc.",
        )

    def tb000(self, widget):
        """Pack UVs with specified settings.

        Performs UV packing operation on selected objects using Maya's u3dLayout command
        with user-specified scaling, rotation, and UDIM settings.

        The packing operation:
        1. Gets UV packing parameters from UI controls
        2. Calculates appropriate padding based on texture resolution
        4. Packs UV shells into the specified UDIM tile

        Parameters:
            widget: The widget containing the menu controls with packing options

        UI Parameters used:
            scale (int): Pre-scale mode from s009 spinbox
                - 0: No scaling (preserve original shell sizes)
                - 1: Uniform scaling (scale proportionally)
                - 2: Non-uniform scaling (stretch to optimize)
            rotate (int): Pre-rotate mode from s010 spinbox
                - 0: No rotation (preserve original orientation)
                - 1: 90-degree rotation steps only
                - 2: Free rotation (any angle)
            UDIM (int): Target UDIM tile number (s004), e.g., 1001

        Note:
            - Requires at least one object to be selected
            - Automatically calculates shell and tile padding based on map size
            - If uniform texel density is enabled, normalizes all shells before packing
        """
        scale = widget.option_box.menu.s009.value()
        rotate = widget.option_box.menu.s010.value()
        UDIM = widget.option_box.menu.s004.value()
        rotate_step = widget.option_box.menu.s011.value()
        rotate_min = widget.option_box.menu.s012.value()
        rotate_max = widget.option_box.menu.s013.value()
        map_size = self.get_map_size()

        U, D, I, M = [int(i) for i in str(UDIM)]  # UDIM ex. '1001'
        shellPadding = mtk.calculate_uv_padding(map_size, normalize=True)
        tilePadding = shellPadding / 2

        selection = pm.selected()
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.<b><br>The operation requires at least one selected object."
            )
            return
        uvs = pm.polyListComponentConversion(selection, fromFace=True, toUV=True)
        uvs_flattened = pm.ls(uvs, flatten=True)

        pm.u3dLayout(
            uvs_flattened,
            resolution=map_size,
            shellSpacing=shellPadding,
            tileMargin=tilePadding,
            preScaleMode=scale,
            preRotateMode=rotate,
            packBox=[M - 1, D, I, U],
            rotateStep=rotate_step,
            rotateMin=rotate_min,
            rotateMax=rotate_max,
        )

    def tb001_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Standard",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Scale Mode 1",
            setObjectName="chk001",
            setTristate=True,
            setChecked=True,
            setToolTip="0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Seam Only",
            setObjectName="chk002",
            setToolTip="Cut seams only.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Planar",
            setObjectName="chk003",
            setToolTip="Create UV texture coordinates for the current selection by using a planar projection shape.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Cylindrical",
            setObjectName="chk004",
            setToolTip="Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Spherical",
            setObjectName="chk005",
            setToolTip="Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Normal-Based",
            setObjectName="chk006",
            setToolTip="Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it's face normals.",
        )
        # widget.option_box.menu.chk001.toggled.connect(lambda state: self.sb.toggle_multi(widget.menu, setUnChecked='chk002-3') if state==1 else None)

    @mtk.undoable
    def tb001(self, widget):
        """Auto Unwrap"""
        standardUnwrap = widget.option_box.menu.chk000.isChecked()
        scaleMode = widget.option_box.menu.chk001.isChecked()
        seamOnly = widget.option_box.menu.chk002.isChecked()
        planarUnwrap = widget.option_box.menu.chk003.isChecked()
        cylindricalUnwrap = widget.option_box.menu.chk004.isChecked()
        sphericalUnwrap = widget.option_box.menu.chk005.isChecked()
        normalBasedUnwrap = widget.option_box.menu.chk006.isChecked()

        selection = pm.selected()
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
                    objFaces = mtk.Components.get_components(obj, "f")
                    if not objFaces:
                        objFaces = mtk.Components.get_components(obj, "f")
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
        widget.option_box.menu.trigger_button = "left"
        widget.option_box.menu.add_apply_button = False
        widget.option_box.menu.position = "bottom"
        widget.option_box.menu.setTitle("DISPLAY OPTIONS")

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
            widget.option_box.menu.add(
                self.sb.registered_widgets.CheckBox,
                setObjectName=chk,
                setText=typ,
                setChecked=state,
            )
            for chk, typ, state in values
        ]

        widget.option_box.menu.chk014.toggled.connect(
            lambda state: pm.textureWindow(panel, edit=True, displayCheckered=state)
        )
        widget.option_box.menu.chk015.toggled.connect(
            lambda state: pm.polyOptions(displayMapBorder=state)
        )
        widget.option_box.menu.chk016.toggled.connect(
            lambda state: pm.textureWindow(panel, edit=True, displayDistortion=state)
        )

    def tb003_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Back-Facing",
            setObjectName="chk008",
            setToolTip="Select all back-facing (using counter-clockwise winding order) components for the current selection.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Front-Facing",
            setObjectName="chk009",
            setToolTip="Select all front-facing (using counter-clockwise winding order) components for the current selection.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Overlapping",
            setObjectName="chk010",
            setToolTip="Select all components that share the same uv space.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Non-Overlapping",
            setObjectName="chk011",
            setToolTip="Select all components that do not share the same uv space.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Texture Borders",
            setObjectName="chk012",
            setToolTip="Select all components on the borders of uv shells.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Unmapped",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Select unmapped faces in the current uv set.",
        )

    def tb003(self, widget):
        """Select By Type"""
        back_facing = widget.option_box.menu.chk008.isChecked()
        front_facing = widget.option_box.menu.chk009.isChecked()
        overlapping = widget.option_box.menu.chk010.isChecked()
        nonOverlapping = widget.option_box.menu.chk011.isChecked()
        textureBorders = widget.option_box.menu.chk012.isChecked()
        unmapped = widget.option_box.menu.chk013.isChecked()

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
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Optimize",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="The Optimize UV Tool evens out the spacing between UVs on a mesh, fixing areas of distortion (overlapping UVs).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Orient",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Orient selected UV shells to run parallel with the most adjacent U or V axis.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Stack Similar",
            setObjectName="chk022",
            setChecked=True,
            setToolTip="Stack only shells that fall within the set tolerance.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.1, 1],
            setValue=1.0,
            setToolTip="Stack shells with uv's within the given range.",
        )

    def tb004(self, widget):
        """Unfold"""
        optimize = widget.option_box.menu.chk017.isChecked()
        orient = widget.option_box.menu.chk007.isChecked()
        stackSimilar = widget.option_box.menu.chk022.isChecked()
        tolerance = widget.option_box.menu.s000.value()
        map_size = self.get_map_size()

        # If selection mode is not object, switch to object mode
        if pm.selectMode(query=True, object=True):
            pm.selectMode(object=True)

        # Perform a preliminary unfold to optionally clean the mesh
        pm.mel.UnfoldUV()  # Prepares the context
        pm.mel.performUnfold(0)  # Mimics UI's behavior

        pm.u3dUnfold(
            iterations=1,
            pack=0,
            borderintersection=1,
            triangleflip=1,
            mapsize=map_size,
            roomspace=0,
        )

        if optimize:
            pm.u3dOptimize(
                iterations=10,
                power=1,
                surfangle=1,
                borderintersection=0,
                triangleflip=1,
                mapsize=map_size,
                roomspace=0,
            )

        if orient:
            pm.mel.texOrientShells()

        if stackSimilar:
            pm.polyUVStackSimilarShells(tolerance=tolerance)

    def tb005_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Angle: ",
            setObjectName="s001",
            set_limits=[0, 360],
            setValue=30,
            setToolTip="Set the maximum angle used for straightening uv's.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Straighten U",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Unfold UV's along a horizonal contraint.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Straighten V",
            setObjectName="chk019",
            setChecked=True,
            setToolTip="Unfold UV's along a vertical constaint.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Straighten Shell",
            setObjectName="chk020",
            setToolTip="Straighten a UV shell by unfolding UV's around a selected UV's edgeloop.",
        )

    def tb005(self, widget):
        """Straighten Uv"""
        u = widget.option_box.menu.chk018.isChecked()
        v = widget.option_box.menu.chk019.isChecked()
        angle = widget.option_box.menu.s001.value()
        straightenShell = widget.option_box.menu.chk020.isChecked()

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
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Distribute U",
            setObjectName="chk023",
            setChecked=True,
            setToolTip="Distribute along U.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Distribute V",
            setObjectName="chk024",
            setToolTip="Distribute along V.",
        )

    def tb006(self, widget):
        """Distribute"""
        u = widget.option_box.menu.chk023.isChecked()
        v = widget.option_box.menu.chk024.isChecked()

        if u:
            pm.mel.texDistributeShells(0, 0, "right", [])  # 'left', 'right'
        if v:
            pm.mel.texDistributeShells(0, 0, "down", [])  # 'up', 'down'

    def tb007_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Remove Empty",
            setObjectName="chk025",
            setChecked=True,
            setToolTip="Remove empty UV sets.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Keep Only Primary",
            setObjectName="chk026",
            setChecked=False,
            setToolTip="Keep only the primary UV set.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Rename Primary to Map1",
            setObjectName="chk027",
            setChecked=False,
            setToolTip="Rename the primary UV set to 'map1'. (default UV set name)",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Force Rename",
            setObjectName="chk028",
            setChecked=False,
            setToolTip="Force rename even if 'map1' already exists (by renaming the existing map1 to 'map1_conflict').",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Prefer Largest Area",
            setObjectName="chk029",
            setChecked=False,
            setToolTip="When multiple UV sets exist, choose the one with the largest actual face area coverage as primary.\nUses sum of UV face areas (not bounding box) to determine which set has the most comprehensive mapping.",
        )

    def tb007(self, widget):
        """Cleanup UV Sets"""
        remove_empty = widget.option_box.menu.chk025.isChecked()
        keep_only_primary = widget.option_box.menu.chk026.isChecked()
        rename_primary = widget.option_box.menu.chk027.isChecked()
        force_rename = widget.option_box.menu.chk028.isChecked()
        prefer_largest_area = widget.option_box.menu.chk029.isChecked()

        selection = pm.selected()
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.<b><br>The operation requires at least one selected object."
            )
            return

        mtk.cleanup_uv_sets(
            selection,
            remove_empty=remove_empty,
            keep_only_primary=keep_only_primary,
            rename_primary_to_map1=rename_primary,
            force_rename=force_rename,
            prefer_largest_area=prefer_largest_area,
        )

    def cmb002(self, index, widget):
        """Transform"""
        text = widget.items[index]
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

    def chk001(self, state, widget):
        """Auto Unwrap: Scale Mode CheckBox"""
        if state == 0:
            widget.option_box.menu.chk001.setText("Scale Mode 0")
        if state == 1:
            widget.option_box.menu.chk001.setText("Scale Mode 1")
            self.sb.toggle_multi(widget.menu, setUnChecked="chk002-6")
        if state == 2:
            widget.option_box.menu.chk001.setText("Scale Mode 2")

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

    @mtk.undoable
    def b000(self, widget):
        """Transfer UV's"""
        frm, *to = pm.ls(orderedSelection=1, flatten=1)
        if not to:
            return self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires the selection of at least two polygon objects."
            )

        for t in to:
            mtk.transfer_uvs(frm, t)

    def b002(self):
        """Stack Shells"""
        pm.mel.texStackShells({})
        # pm.mel.texOrientShells()

    def b003(self):
        """Get texel density."""
        density = mtk.get_texel_density(pm.selected(), self.get_map_size())
        self.ui.s003.setValue(density)

    @mtk.undoable
    def b004(self):
        """Set Texel Density"""
        density = self.ui.s003.value()
        map_size = self.get_map_size()

        mtk.set_texel_density(pm.selected(), density, map_size)

    def b005(self):
        """Cut UV's"""
        selection = pm.selected()
        selected_edges = pm.filterExpand(selection, selectionMask=32)

        if not selection:
            self.sb.message_box("Nothing selected")
            return

        if selected_edges:
            # Map the selected edges to their respective objects
            edges_by_object = mtk.Components.map_components_to_objects(selected_edges)
            # Iterate through the objects and perform the cut operation on their edges
            for obj_name, edges in edges_by_object.items():
                pm.polyMapCut(edges)
            # Re-select the edges after the operation
            pm.select(selected_edges)
        else:
            # If no edges are selected, check for selected objects that are mesh transforms
            for obj in selection:
                if isinstance(obj, pm.nodetypes.Transform):
                    shape = obj.getShape()
                    if shape and isinstance(shape, pm.nodetypes.Mesh):
                        # Cut the UVs along all edges of the mesh
                        pm.polyMapCut(shape.e[:])

    def b006(self):
        """Rotate UV's 90"""
        angle = -45
        selected_objects = pm.selected()

        # Convert shell selection to individual UVs
        selected_uvs = pm.polyListComponentConversion(selected_objects, toUV=True)
        selected_uvs = pm.ls(selected_uvs, flatten=True)

        # Calculate the pivot point for the UV shell
        all_u, all_v = [], []
        for uv in selected_uvs:
            u, v = pm.polyEditUV(uv, query=True, uValue=True, vValue=True)
            all_u.append(u)
            all_v.append(v)

        pivot_u = sum(all_u) / len(all_u)
        pivot_v = sum(all_v) / len(all_v)

        # Rotate UVs using the calculated pivot point
        for uv in selected_uvs:
            pm.polyEditUV(
                uv, pivotU=pivot_u, pivotV=pivot_v, angle=angle, relative=True
            )

    def b007(self):
        """Display UV Borders"""
        mtk.Macros.m_toggle_uv_border_edges()

    @mtk.undoable
    def b011(self):
        """Sew UVs"""
        selected = pm.selected(flatten=True)

        for obj in selected:
            # Check if the selected item is a mesh edge
            if isinstance(obj, pm.MeshEdge):
                pm.polyMapSew(obj)
            # Check if the selected item is a transform node (possibly a mesh object)
            elif isinstance(obj, pm.nodetypes.Transform):
                shape = obj.getShape()
                # Confirm the shape node is a mesh
                if shape and isinstance(shape, pm.nodetypes.Mesh):
                    pm.polyMapSew(shape.e[:])

    def b021(self, widget):
        """Unfold and Pack UVs"""
        self.ui.tb004.call_slot()  # perform unfold
        self.ui.tb000.call_slot()  # perform pack

    def b022(self):
        """Cut UV hard edges"""
        # perform select edges by angle.
        self.sb.loaded_ui.selection.tb003.call_slot()
        self.b005()  # Perform cut.

    def b023(self):
        """Move To Uv Space: Left"""
        selection = pm.selected()
        mtk.move_to_uv_space(selection, -1, 0)  # move left

    def b024(self):
        """Move To Uv Space: Down"""
        selection = pm.selected()
        mtk.move_to_uv_space(selection, 0, -1)  # move down

    def b025(self):
        """Move To Uv Space: Up"""
        selection = pm.selected()
        mtk.move_to_uv_space(selection, 0, 1)  # move up

    def b026(self):
        """Move To Uv Space: Right"""
        selection = pm.selected()
        mtk.move_to_uv_space(selection, 1, 0)  # move right


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
