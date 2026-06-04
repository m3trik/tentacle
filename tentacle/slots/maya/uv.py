# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from uitk import IconManager

# From this package:
from tentacle.slots.maya._slots_maya import SlotsMaya


class UvSlots(SlotsMaya):
    # Auto Unwrap modes driven by Maya's polyProjection (single-shape
    # projection). These are exactly the modes that expose the Smart Fit
    # option, so tb001_init's gate and tb001's dispatch share this set.
    # Each key, title-cased, is also the polyProjection -type value.
    _PROJECTION_UNWRAP_MODES = ("planar", "cylindrical", "spherical")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.uv
        self.submenu = self.sb.loaded_ui.uv_submenu

        # Assure the maya UV plugin is loaded
        mtk.load_plugin("Unfold3D.mll")

        # Dual-state toggle state for b029 (Pin) and b030 (Stack).
        # Each button tracks the selection captured at its last successful
        # action; on the next click we compare to the live selection and reset
        # the toggle if it changed. This is more robust than a SelectionChanged
        # scriptJob — Maya can fire SelectionChanged as a side effect of UV
        # commands (e.g. texStackShells), which would silently reset our flag
        # mid-operation.
        self._b029_pinned = False
        self._b029_last_selection = None
        self._b030_stacked = False
        self._b030_last_selection = None
        self._b030_uv_snapshot = None

    def get_map_size(self):
        """Get the map size from the combobox as an int. ie. 2048"""
        return int(self.ui.cmb003.currentText())

    def header_init(self, widget):
        """Initialize UV Menu Header"""
        widget.menu.add(
            "QPushButton",
            setText="Create UV Snapshot",
            setObjectName="uv_snapshot",
            setToolTip="Save an image file of the current UV layout.",
        )
        widget.menu.uv_snapshot.clicked.connect(lambda: mel.eval("UVCreateSnapshot"))
        widget.menu.add(
            "QPushButton",
            setText="Open UV Editor",
            setObjectName="uv_editor",
            setToolTip="Open the texture coordinate mapping window.",
        )
        widget.menu.uv_editor.clicked.connect(lambda: mel.eval("TextureViewWindow"))
        widget.menu.add(
            "QPushButton",
            setText="RizomUV Bridge",
            setObjectName="btn_rizom_bridge",
            setToolTip="Round-trip selected meshes through RizomUV using a Lua preset.",
        )
        widget.menu.btn_rizom_bridge.clicked.connect(
            lambda: self.sb.handlers.marking_menu.show("rizom_bridge")
        )

    def cmb002_init(self, widget):
        """Initialize UV Transform Menu"""
        items = [
            "Flip U",
            "Flip V",
            "Rotate 45",
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
        - Pre-Scale Mode: How shells are scaled before packing
        - Pre-Rotate Mode: One-shot shell orientation before packing
        - Rotate Step/Min/Max: Packing-time rotation search (active when Max > Min)
        - Mutations: Optimization passes (higher = better pack, slower)
        - UDIM: Target UDIM tile space for the packed UVs

        Rotate Step is auto-disabled when Rotate Max <= Rotate Min (no range
        to step through).

        Parameters:
            widget: The parent widget to add menu items to
        """
        widget.option_box.menu.setTitle("Pack UVs")
        # Pre-Scale Mode. Empirically, u3dLayout has only two distinct -preScaleMode
        # behaviors in Maya 2025: omitted/0 keeps input UV proportions; any non-zero
        # value rescales shells by 3D area. Stock Maya's "Preserve UV" UI option
        # actually emits -scl 3, which empirically behaves as Preserve 3D — so don't
        # expose the broken intermediate values.
        cmb009 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb009",
            setToolTip=(
                "Maya u3dLayout -preScaleMode (only two distinct behaviors).\n"
                "Preserve UV: keep each shell's input UV proportions relative to the others.\n"
                "Preserve 3D: rescale shells uniformly so 3D surface area governs UV area."
            ),
        )
        for text, data in [
            ("Pre-Scale: Preserve UV", 0),
            ("Pre-Scale: Preserve 3D", 1),
        ]:
            cmb009.addItem(text, data)
        cmb009.setCurrentIndex(1)  # matches prior default (preScaleMode=1)

        # Pre-Rotate Mode. Mirrors Maya's stock dialog
        # (performPolyLayoutUV.mel:662-670). Values are passed through directly;
        # 0 = omit the flag.
        cmb010 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb010",
            setToolTip=(
                "Maya u3dLayout -preRotateMode. One-shot pre-orient before packing.\n"
                "Axis modes (X/Y/Z to V) use the underlying 3D mesh orientation."
            ),
        )
        for text, data in [
            ("Pre-Rotate: Off", 0),
            ("Pre-Rotate: Horizontal (long axis to U)", 1),
            ("Pre-Rotate: Vertical (long axis to V)", 2),
            ("Pre-Rotate: Axis X to V", 3),
            ("Pre-Rotate: Axis Y to V", 4),
            ("Pre-Rotate: Axis Z to V", 5),
        ]:
            cmb010.addItem(text, data)
        cmb010.setCurrentIndex(0)  # Off (matches prior default of 0)
        # Packing-time rotation search: active when Rotate Max > Rotate Min.
        # Independent of Pre-Rotate Mode.
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Step: ",
            setObjectName="s011",
            set_limits=[1, 360],
            setValue=90,
            setToolTip="Increment (degrees) between rotations tested during packing.\n"
            "Active only when Rotate Max > Rotate Min. Smaller steps cost more time.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Min: ",
            setObjectName="s012",
            set_limits=[0, 359],
            setValue=0,
            setToolTip="Minimum rotation (degrees) for packing-time rotation search.\n"
            "Rotation only activates when Rotate Max > Rotate Min.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Max: ",
            setObjectName="s013",
            set_limits=[0, 359],
            setValue=0,
            setToolTip="Maximum rotation (degrees) for packing-time rotation search.\n"
            "Defaults to 0 (rotation disabled). Set above Rotate Min to opt in;\n"
            "180 covers all unique orientations.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Mutations: ",
            setObjectName="s014",
            set_limits=[1, 64],
            setValue=1,
            setToolTip="Maya u3dLayout -mutations. Number of optimization passes.\n"
            "Higher values produce tighter packs at the cost of CPU time.\n"
            "Stock Maya only emits this flag when > 1.",
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

        # Gate: Rotate Step is meaningless when Rotate Max <= Rotate Min.
        menu = widget.option_box.menu

        def _sync_rotate_step():
            menu.s011.setEnabled(menu.s013.value() > menu.s012.value())

        menu.s012.valueChanged.connect(_sync_rotate_step)
        menu.s013.valueChanged.connect(_sync_rotate_step)
        _sync_rotate_step()

    def tb000(self, widget):
        """Pack UVs with specified settings.

        Performs UV packing operation on selected objects using Maya's u3dLayout command
        with user-specified scaling, rotation, and UDIM settings.

        The packing operation:
        1. Gets UV packing parameters from UI controls
        2. Calculates appropriate padding based on texture resolution
        3. Packs UVs from all selected meshes together into the target UDIM tile
           (falls back to per-mesh probing if the batched call fails, isolates
           the offending mesh, and re-packs the survivors together)

        Parameters:
            widget: The widget containing the menu controls with packing options

        UI Parameters used:
            scale (int): Pre-scale mode from cmb009 (Maya -preScaleMode)
                - 0: Preserve UV (no rescaling), 1: Preserve 3D (uniform by 3D area)
            rotate (int): Pre-rotate mode from cmb010 (Maya -preRotateMode)
                - 0: Off, 1: Horizontal, 2: Vertical, 3-5: Axis X/Y/Z to V
            rotate_step/min/max (int): Packing-time rotation search.
                Active only when max > min; independent of pre-rotate mode.
            mutations (int): s014 spinbox (Maya -mutations). Optimization passes;
                only emitted when > 1.
            UDIM (int): Target UDIM tile number (s004), e.g., 1001

        Note:
            - Requires at least one object to be selected
            - Automatically calculates shell and tile padding based on map size
            - Meshes with errors (e.g., non-manifold vertices) are skipped with a summary
        """
        scale = widget.option_box.menu.cmb009.currentData()
        rotate = widget.option_box.menu.cmb010.currentData()
        UDIM = widget.option_box.menu.s004.value()
        rotate_step = widget.option_box.menu.s011.value()
        rotate_min = widget.option_box.menu.s012.value()
        rotate_max = widget.option_box.menu.s013.value()
        mutations = widget.option_box.menu.s014.value()
        map_size = self.get_map_size()

        # UDIM = 1001 + u + 10*v   (u: 0-9, v: 0+); packBox is [umin, umax, vmin, vmax]
        u_tile, v_tile = (UDIM - 1001) % 10, (UDIM - 1001) // 10
        shellPadding = mtk.calculate_uv_padding(map_size, normalize=True)
        tilePadding = shellPadding / 2

        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.<b><br>The operation requires at least one selected object."
            )
            return

        # Get unique meshes from selection (handles both object and component selection)
        meshes = mtk.Components.get_components(selection, "mesh", flatten=False)
        if not meshes:
            meshes = cmds.ls(selection, type="transform", dag=True) or selection

        # Bulk-resolve UVs in one call; keep ranges unflattened ("pCube1.map[0:23]")
        # so we don't pay to expand millions of indices into individual strings.
        all_uvs = (
            cmds.polyListComponentConversion(meshes, fromFace=True, toUV=True) or []
        )
        if not all_uvs:
            self.sb.message_box("<b>No UVs found on selection.</b>")
            return

        pack_kwargs = dict(
            resolution=map_size,
            shellSpacing=shellPadding,
            tileMargin=tilePadding,
            preScaleMode=scale,
            preRotateMode=rotate,
            packBox=[u_tile, u_tile + 1, v_tile, v_tile + 1],
            multiObject=True,  # -m off causes all shells to stack at the tile center
        )
        # Rotate flags only when the user opts in (max > min). Maya's stock dialog
        # follows the same pattern: it omits these unless the "Rotate" checkbox is on.
        # Passing them with the default range (0..180) silently rotates shells even
        # when Pre-Rotate is set to Off.
        if rotate_max > rotate_min:
            pack_kwargs["rotateStep"] = rotate_step
            pack_kwargs["rotateMin"] = rotate_min
            pack_kwargs["rotateMax"] = rotate_max
        if mutations > 1:
            pack_kwargs["mutations"] = mutations

        def _classify(err):
            msg = str(err)
            low = msg.lower()
            if "non-manifold" in low:
                return "non-manifold vertices"
            if "overlapping" in low:
                return "overlapping UVs"
            return msg.split("\n")[0][:50]

        successful = []
        failed = []
        cmds.undoInfo(openChunk=True, chunkName="UV Pack")
        cmds.refresh(suspend=True)
        try:
            try:
                # Single batched pack — all meshes share the target tile together.
                cmds.u3dLayout(all_uvs, **pack_kwargs)
                successful = [str(m) for m in meshes]
            except RuntimeError:
                # Batch failed: probe each mesh to isolate the bad one(s),
                # then re-pack the survivors together so they share the tile.
                good = []
                for mesh in meshes:
                    uvs = (
                        cmds.polyListComponentConversion(
                            mesh, fromFace=True, toUV=True
                        )
                        or []
                    )
                    if not uvs:
                        continue
                    try:
                        cmds.u3dLayout(uvs, **pack_kwargs)
                        good.extend(uvs)
                        successful.append(str(mesh))
                    except RuntimeError as me:
                        failed.append((str(mesh), _classify(me)))
                if good:
                    try:
                        cmds.u3dLayout(good, **pack_kwargs)
                    except RuntimeError as ce:
                        # Survivors packed individually (each filling the tile);
                        # combine failed, so leave them as-is and surface the cause.
                        failed.append(("<combined re-pack>", _classify(ce)))
        finally:
            cmds.refresh(suspend=False)
            cmds.undoInfo(closeChunk=True)

        # Report summary
        if failed:
            failed_list = "<br>".join(
                f"• <b>{name}</b>: {reason}" for name, reason in failed
            )
            self.sb.message_box(
                f"<b>UV Pack Complete</b><br><br>"
                f"✓ Packed: {len(successful)} mesh(es)<br>"
                f"✗ Skipped: {len(failed)} mesh(es)<br><br>"
                f"<b>Skipped meshes:</b><br>{failed_list}<br><br>"
                f"<i>Tip: Use Mesh > Cleanup to fix non-manifold geometry.</i>"
            )
        elif successful:
            self.sb.message_box(
                f"<b>UV Pack Complete</b><br><br>"
                f"✓ Successfully packed {len(successful)} mesh(es)."
            )

    def tb001_init(self, widget):
        """Initialize Auto Unwrap.

        A single mode combobox (cmb011) selects the projection method, and the
        per-mode option controls beneath it auto-enable only for the modes they
        actually affect:
            - Scale Mode (cmb012) → Standard only (polyAutoProjection -scaleMode)
            - Smart Fit  (chk000) → Planar / Cylindrical / Spherical only
        Seam Only and Normal-Based expose no options, so both controls disable.

        Parameters:
            widget: The parent widget to add menu items to
        """
        menu = widget.option_box.menu
        menu.setTitle("Auto Unwrap")

        # Mode selector. Modes are mutually exclusive, so a combobox replaces the
        # former cluster of radio buttons. Item data is a lowercase mode key
        # consumed by tb001.
        cmb011 = menu.add(
            "QComboBox",
            setObjectName="cmb011",
            setToolTip=(
                "Projection method used to generate UVs.\n"
                "Standard: best-fit from multiple simultaneous planar projections.\n"
                "Seam Only: cut auto-detected seams without re-laying out UVs.\n"
                "Planar / Cylindrical / Spherical: project from a single shape.\n"
                "Normal-Based: planar projection along the averaged face normal."
            ),
        )
        for text, data in [
            ("Standard", "standard"),
            ("Seam Only", "seam"),
            ("Planar", "planar"),
            ("Cylindrical", "cylindrical"),
            ("Spherical", "spherical"),
            ("Normal-Based", "normal"),
        ]:
            cmb011.addItem(text, data)
        cmb011.setCurrentIndex(0)  # Standard (matches prior default)

        # Scale Mode (Standard only). Explicit data values fix the old tristate
        # checkbox, whose isChecked() collapsed to a bool and could never emit 2.
        cmb012 = menu.add(
            "QComboBox",
            setObjectName="cmb012",
            setToolTip=(
                "Maya polyAutoProjection -scaleMode (Standard only).\n"
                "None: keep the projected scale.\n"
                "Uniform: scale uniformly to fit the unit square.\n"
                "Stretch: non-proportional scale to fill the unit square."
            ),
        )
        for text, data in [
            ("Scale: None", 0),
            ("Scale: Uniform", 1),
            ("Scale: Stretch to Square", 2),
        ]:
            cmb012.addItem(text, data)
        cmb012.setCurrentIndex(1)  # Uniform (matches prior default of scaleMode=1)

        # Smart Fit (Planar / Cylindrical / Spherical only). Defaults on to
        # preserve the previous hardcoded polyProjection(smartFit=1) behavior.
        menu.add(
            "QCheckBox",
            setText="Smart Fit",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Best-fit the projection manipulator to the selection.\n"
            "Applies to Planar / Cylindrical / Spherical only.",
        )

        # Gate: enable only the options relevant to the selected mode.
        def _sync_options():
            mode = cmb011.currentData()
            menu.cmb012.setEnabled(mode == "standard")
            menu.chk000.setEnabled(mode in self._PROJECTION_UNWRAP_MODES)

        cmb011.currentIndexChanged.connect(_sync_options)
        _sync_options()

    @mtk.undoable
    def tb001(self, widget):
        """Auto Unwrap"""
        menu = widget.option_box.menu
        mode = menu.cmb011.currentData()
        scale_mode = menu.cmb012.currentData()
        smart_fit = menu.chk000.isChecked()

        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least one selected object."
            )
            return

        result = None
        for obj in selection:
            try:
                if mode == "seam":
                    result = cmds.u3dAutoSeam(obj, s=0, p=1)

                elif mode in self._PROJECTION_UNWRAP_MODES:
                    # Mode key doubles as the polyProjection -type value once titled.
                    obj_faces = mtk.Components.get_components(obj, "f")
                    result = cmds.polyProjection(
                        obj_faces,
                        type=mode.capitalize(),
                        insertBeforeDeformers=1,
                        smartFit=1 if smart_fit else 0,
                    )

                elif mode == "normal":
                    mel.eval(f'texNormalProjection 1 1 "{obj}"')  # Normal-Based unwrap

                else:  # standard
                    result = cmds.polyAutoProjection(
                        obj,
                        layoutMethod=0,
                        optimize=1,
                        insertBeforeDeformers=1,
                        scaleMode=scale_mode,  # 0 none, 1 uniform, 2 stretch to square
                        createNewMap=False,  # Create a new UV set, as opposed to editing the current one, or the one given by the -uvSetName flag.
                        projectBothDirections=0,  # If "on" : projections are mirrored on directly opposite faces. If "off" : projections are not mirrored on opposite faces.
                        layout=2,  # 0 UV pieces are set to no layout. 1 UV pieces are aligned along the U axis. 2 UV pieces are moved in a square shape.
                        planes=6,  # intermediate projections used. Valid numbers are 4, 5, 6, 8, and 12
                        percentageSpace=0.2,  # percentage of the texture area which is added around each UV piece.
                        worldSpace=0,
                    )  # 1=world reference. 0=object reference.

            except Exception as error:
                print(error)

        if len(selection) == 1:
            return result

    def tb004_init(self, widget):
        """Initialize Unfold UV"""
        widget.option_box.menu.setTitle("Unfold UV")
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
        if cmds.selectMode(query=True, object=True):
            cmds.selectMode(object=True)

        cmds.u3dUnfold(
            iterations=1,
            pack=0,
            borderintersection=1,
            triangleflip=1,
            mapsize=map_size,
            roomspace=0,
        )

        if optimize:
            cmds.u3dOptimize(
                iterations=10,
                power=1,
                surfangle=1,
                borderintersection=0,
                triangleflip=1,
                mapsize=map_size,
                roomspace=0,
            )

        if orient:
            mel.eval("texOrientShells")

        if stackSimilar:
            cmds.polyUVStackSimilarShells(tolerance=tolerance)

    def tb005_init(self, widget):
        """Initialize Straighten UV"""
        widget.option_box.menu.setTitle("Straighten")
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
            setText="Straighten UV",
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
        """Straighten UV"""
        u = widget.option_box.menu.chk018.isChecked()
        v = widget.option_box.menu.chk019.isChecked()
        angle = widget.option_box.menu.s001.value()
        straightenShell = widget.option_box.menu.chk020.isChecked()

        if u and v:
            mel.eval(f'texStraightenUVs "UV" {angle}')
        elif u:
            mel.eval(f'texStraightenUVs "U" {angle}')
        elif v:
            mel.eval(f'texStraightenUVs "V" {angle}')

        if straightenShell:
            mel.eval("texStraightenShell")

    def tb006_init(self, widget):
        """Initialize Distribute"""
        widget.option_box.menu.setTitle("Distribute")
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
            mel.eval('texDistributeShells 0 0 "right" {}')  # 'left', 'right'
        if v:
            mel.eval('texDistributeShells 0 0 "down" {}')  # 'up', 'down'

    def tb007_init(self, widget):
        """Initialize Cleanup UV Sets"""
        widget.option_box.menu.setTitle("Cleanup UV Sets")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Prefer Best Layout",
            setObjectName="chk029",
            setChecked=True,
            setToolTip="<b>Best Information Strategy</b><br>If checked: Analyzes all valid UV sets and picks the one with the best layout density (Fill Rate).<br>Ignores global scaling, prioritizing actual texture usage and validity.<br>If unchecked: Uses the currently active UV set.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Remove Empty Sets",
            setObjectName="chk035",
            setChecked=True,
            setToolTip="<b>Safe Cleanup</b><br>Deletes any UV sets that have no UV coordinates.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Secondary Sets",
            setObjectName="chk036",
            setChecked=False,
            setToolTip="<b>Aggressive Cleanup</b><br>If checked: Deletes ALL other UV sets, leaving only the primary one.<br>If unchecked: Only deletes empty sets (if enabled). Secondary sets with data are preserved.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Rename to 'map1'",
            setObjectName="chk037",
            setChecked=True,
            setToolTip="<b>Standardization</b><br>Renames the primary UV set to the default 'map1'.<br>This also moves it to the first index (canonical position).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Force Rename",
            setObjectName="chk038",
            setChecked=False,
            setToolTip="<b>Destructive Rename</b><br>If 'map1' already exists but isn't the primary set:<br>Checked: Overwrite/merge 'map1' with the primary set.<br>Unchecked: Skip renaming if 'map1' exists and has content.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Dry Run",
            setObjectName="chk030",
            setChecked=False,
            setToolTip="Preview changes in the Script Editor without modifying anything.",
        )

    def tb007(self, widget):
        """Cleanup UV Sets"""
        prefer_largest_area = widget.option_box.menu.chk029.isChecked()
        remove_empty = widget.option_box.menu.chk035.isChecked()
        keep_only_primary = widget.option_box.menu.chk036.isChecked()
        rename_to_map1 = widget.option_box.menu.chk037.isChecked()
        force_rename = widget.option_box.menu.chk038.isChecked()
        dry_run = widget.option_box.menu.chk030.isChecked()

        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.<b><br>The operation requires at least one selected object."
            )
            return

        results = mtk.Diagnostics.cleanup_uv_sets(
            selection,
            remove_empty=remove_empty,
            keep_only_primary=keep_only_primary,
            rename_to_map1=rename_to_map1,
            force_rename=force_rename,
            prefer_largest_area=prefer_largest_area,
            dry_run=dry_run,
        )

        # Generate summary report
        if not results:
            return

        report_lines = []
        for r in results:
            if r.error:
                report_lines.append(f"❌ <b>{r.shape}</b>: {r.error}")
                continue

            # Format specific details
            details = []
            if r.initial_sets:
                deleted_count = len(r.sets_to_delete)
                kept = r.primary_set

                if dry_run:
                    action = "Would keep"
                    del_action = "would delete"
                else:
                    action = "Kept"
                    del_action = "deleted"

                details.append(f"{action} '<b>{kept}</b>'")
                if r.final_name != kept and (rename_to_map1 or force_rename):
                    details.append(f" → renamed to '<b>{r.final_name}</b>'")

                if deleted_count > 0:
                    details.append(f", {del_action} {deleted_count} others")

            report_lines.append(f"• <b>{r.shape}</b>: {''.join(details)}")

        header = "<b>Dry Run Report</b>" if dry_run else "<b>Cleanup Complete</b>"
        self.sb.message_box(f"{header}<br><br>" + "<br>".join(report_lines))

    def tb008_init(self, widget):
        """Initialize Mirror UVs.

        Mirrors UVs across U or V. By default this uses the footprint-preserving
        reassignment mode (preserve_position=True), which keeps the UV point set
        unchanged and only reassigns which UV gets which point.
        """
        widget.option_box.menu.setTitle("Mirror UVs")
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Mirror U",
            setObjectName="chk031",
            setChecked=True,
            setToolTip="Mirror across U. Default mode preserves the UV footprint.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Mirror V",
            setObjectName="chk032",
            setToolTip="Mirror across V. Default mode preserves the UV footprint.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Per Shell",
            setObjectName="chk033",
            setChecked=True,
            setToolTip="If enabled, mirrors each UV shell independently.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Preserve Footprint",
            setObjectName="chk034",
            setChecked=True,
            setToolTip="If enabled, preserves the exact UV point set using one-to-one reassignment.\nIf disabled, performs a geometric mirror around the pivot.",
        )

    @mtk.undoable
    def tb008(self, widget):
        """Mirror UVs (footprint-preserving by default)."""
        mirror_u = widget.option_box.menu.chk031.isChecked()
        mirror_v = widget.option_box.menu.chk032.isChecked()
        per_shell = widget.option_box.menu.chk033.isChecked()
        preserve_position = widget.option_box.menu.chk034.isChecked()

        axis = "u" if mirror_u and not mirror_v else "v"

        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.<b><br>The operation requires at least one selected object."
            )
            return

        mtk.UvUtils.mirror_uvs(
            selection,
            axis=axis,
            per_shell=per_shell,
            preserve_position=preserve_position,
        )

    def cmb002(self, index, widget):
        """Transform"""
        text = widget.items[index]
        if text == "Flip U":
            cmds.polyFlipUV(flipType=0, local=1, usePivot=1, pivotU=0, pivotV=0)
        elif text == "Flip V":
            cmds.polyFlipUV(flipType=1, local=1, usePivot=1, pivotU=0, pivotV=0)
        elif text == "Rotate 45":
            angle = -45
            selected_objects = cmds.ls(sl=True) or []
            if not selected_objects:
                self.sb.message_box(
                    "<b>Nothing selected.<b><br>The operation requires at least one selected object."
                )
                return

            selected_uvs = cmds.polyListComponentConversion(selected_objects, toUV=True)
            selected_uvs = cmds.ls(selected_uvs, flatten=True) or []
            if not selected_uvs:
                self.sb.message_box(
                    "<b>No UVs found.<b><br>Select a mesh, faces, edges, or UVs."
                )
                return

            all_u, all_v = [], []
            for uv in selected_uvs:
                u, v = cmds.polyEditUV(uv, query=True, uValue=True, vValue=True)
                all_u.append(u)
                all_v.append(v)

            pivot_u = sum(all_u) / len(all_u)
            pivot_v = sum(all_v) / len(all_v)

            for uv in selected_uvs:
                cmds.polyEditUV(
                    uv, pivotU=pivot_u, pivotV=pivot_v, angle=angle, relative=True
                )
        elif text == "Align U Left":
            mel.eval('performAlignUV "minU"')
        elif text == "Align U Middle":
            mel.eval('performAlignUV "avgU"')
        elif text == "Align U Right":
            mel.eval('performAlignUV "maxU"')
        elif text == "Align U Top":
            mel.eval('performAlignUV "maxV"')
        elif text == "Align U Middle":
            mel.eval('performAlignUV "avgV"')
        elif text == "Align U Bottom":
            mel.eval('performAlignUV "minV"')
        elif text == "Linear Align":
            mel.eval("performLinearAlignUV")

    @mtk.undoable
    def b000(self, widget):
        """Transfer UV's"""
        ordered = cmds.ls(orderedSelection=1, flatten=1) or []
        if len(ordered) < 2:
            return self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires the selection of at least two polygon objects."
            )
        frm, *to = ordered

        for t in to:
            mtk.transfer_uvs(frm, t)

    def b003(self):
        """Get texel density."""
        density = mtk.get_texel_density(cmds.ls(sl=True) or [], self.get_map_size())
        self.ui.s003.setValue(density)

    @mtk.undoable
    def b004(self):
        """Set Texel Density"""
        density = self.ui.s003.value()
        map_size = self.get_map_size()

        mtk.set_texel_density(cmds.ls(sl=True) or [], density, map_size)

    def b005(self):
        """Cut UV's"""
        selection = cmds.ls(sl=True) or []
        selected_edges = cmds.filterExpand(selection, selectionMask=32)

        if not selection:
            self.sb.message_box("Nothing selected")
            return

        if selected_edges:
            # Map the selected edges to their respective objects
            edges_by_object = mtk.Components.map_components_to_objects(selected_edges)
            # Iterate through the objects and perform the cut operation on their edges
            for obj_name, edges in edges_by_object.items():
                cmds.polyMapCut(edges)
            # Re-select the edges after the operation
            cmds.select(selected_edges)
        else:
            # If no edges are selected, check for selected objects that are mesh transforms
            for obj in selection:
                if cmds.objectType(obj) == "transform":
                    shapes = cmds.listRelatives(
                        obj, shapes=True, noIntermediate=True
                    ) or []
                    for shape in shapes:
                        if cmds.objectType(shape) == "mesh":
                            # Cut the UVs along all edges of the mesh
                            cmds.polyMapCut(f"{shape}.e[*]")

    @mtk.undoable
    def b011(self):
        """Sew UVs"""
        selected = cmds.ls(sl=True, flatten=True) or []

        # Edges (component selection) — sew directly
        edges = cmds.filterExpand(selected, selectionMask=32) or []
        for edge in edges:
            cmds.polyMapSew(edge)

        # Transforms — sew all edges of their mesh shape
        transforms = cmds.ls(selected, type="transform") or []
        for obj in transforms:
            shapes = cmds.listRelatives(obj, shapes=True, noIntermediate=True) or []
            for shape in shapes:
                if cmds.objectType(shape) == "mesh":
                    cmds.polyMapSew(f"{shape}.e[*]")

    def b021(self, widget):
        """Unfold and Pack UVs"""
        self.ui.tb004.call_slot()  # perform unfold
        self.ui.tb000.call_slot()  # perform pack

    def tb022_init(self, widget):
        """Initialize Cut Hard Edges option menu."""
        widget.option_box.menu.setTitle("Cut Hard Edges")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Low:  ",
            setObjectName="s014",
            set_limits=[0, 180],
            setValue=70,
            setToolTip="Normal angle low range for hard-edge detection.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle High: ",
            setObjectName="s015",
            set_limits=[0, 180],
            setValue=180,
            setToolTip="Normal angle high range for hard-edge detection.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Include UV Borders",
            setObjectName="chk025",
            setChecked=False,
            setToolTip="Also cut along edges that are existing UV shell borders.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Include Auto Seams",
            setObjectName="chk026",
            setChecked=False,
            setToolTip="Also cut along seams auto-detected by u3dAutoSeam.",
        )

    @mtk.undoable
    def tb022(self, widget):
        """Cut UV hard edges (always), optionally also UV borders and auto-detected seams."""
        angle_low = widget.option_box.menu.s014.value()
        angle_high = widget.option_box.menu.s015.value()
        include_uv_borders = widget.option_box.menu.chk025.isChecked()
        include_auto_seams = widget.option_box.menu.chk026.isChecked()

        objects = cmds.ls(sl=True, objectsOnly=True) or []
        if not objects:
            self.sb.message_box("Nothing selected")
            return

        # Hard edges (always on) — cut along edges within the angle range.
        hard_edges = mtk.Components.get_edges_by_normal_angle(
            objects, low_angle=angle_low, high_angle=angle_high
        )
        if hard_edges:
            cmds.polyMapCut(hard_edges)

        # Optional: cut along existing UV shell border edges.
        if include_uv_borders:
            border_edges = mtk.UvUtils.get_uv_shell_border_edges(objects)
            if border_edges:
                cmds.polyMapCut(border_edges)

        # Optional: auto-detected seams via Unfold3D.
        if include_auto_seams:
            for obj in objects:
                try:
                    cmds.u3dAutoSeam(obj, s=0, p=1)
                except Exception as error:
                    print(error)

    def b023(self):
        """Move To Uv Space: Left"""
        selection = cmds.ls(sl=True) or []
        mtk.move_to_uv_space(selection, -1, 0)  # move left

    def b024(self):
        """Move To Uv Space: Down"""
        selection = cmds.ls(sl=True) or []
        mtk.move_to_uv_space(selection, 0, -1)  # move down

    def b025(self):
        """Move To Uv Space: Up"""
        selection = cmds.ls(sl=True) or []
        mtk.move_to_uv_space(selection, 0, 1)  # move up

    def b026(self):
        """Move To Uv Space: Right"""
        selection = cmds.ls(sl=True) or []
        mtk.move_to_uv_space(selection, 1, 0)  # move right

    def b029_init(self, widget):
        """Initialize Pin/Unpin button — static pin icon, non-checkable.

        Defensively strips any `checkable`/`text` properties a Qt Designer
        round-trip may have re-added, then installs the static `pin` icon.
        """
        widget.setCheckable(False)
        widget.setText("")
        IconManager.set_icon(widget, "pin", size=(16, 16))

    @mtk.undoable
    def b029(self, widget):
        """Pin / Unpin selected UVs (dual-state toggle).

        First click on a fresh selection pins; the next click unpins; and so
        on. A selection change since the last click resets the toggle, so the
        next click always starts with Pin.
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box("<b>Nothing selected.</b>")
            return
        uvs = cmds.polyListComponentConversion(selection, toUV=True) or []
        if not uvs:
            self.sb.message_box("<b>No UVs found in selection.</b>")
            return

        if self._b029_last_selection != selection:
            self._b029_pinned = False  # fresh selection — start with Pin
        self._b029_pinned = not self._b029_pinned
        cmds.polyPinUV(uvs, value=1.0 if self._b029_pinned else 0.0)
        self._b029_last_selection = list(selection)

    def b030_init(self, widget):
        """Initialize Stack button — static stack icon, non-checkable.

        Defensively strips any `checkable`/`text` properties a Qt Designer
        round-trip may have re-added, then installs the static `stack` icon.
        """
        widget.setCheckable(False)
        widget.setText("")
        IconManager.set_icon(widget, "stack", size=(16, 16))

    @mtk.undoable
    def b030(self, widget):
        """Stack / Unstack similar shells (dual-state toggle).

        First click on a fresh selection captures each selected UV's position
        and stacks similar shells (texStackShells). The next click restores
        those positions, returning shells to exactly where they were before
        the stack. A selection change since the last click resets the toggle
        and drops the snapshot.

        Per-UV capture and restore avoid an ordering ambiguity in bulk
        ``polyEditUV(..., query=True)``.
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box("<b>Nothing selected.</b>")
            return
        uvs = cmds.polyListComponentConversion(selection, toUV=True) or []
        uvs = cmds.ls(uvs, flatten=True) or []
        if not uvs:
            self.sb.message_box("<b>No UVs found in selection.</b>")
            return

        if self._b030_last_selection != selection:
            # Fresh selection — reset to "next click stacks" and drop any
            # snapshot from a previous selection.
            self._b030_stacked = False
            self._b030_uv_snapshot = None

        self._b030_stacked = not self._b030_stacked
        self._b030_last_selection = list(selection)

        if self._b030_stacked:
            snapshot = []
            for uv in uvs:
                pos = cmds.polyEditUV(uv, query=True)
                if pos and len(pos) >= 2:
                    snapshot.append((uv, pos[0], pos[1]))
            self._b030_uv_snapshot = snapshot
            mel.eval("texStackShells {}")
            return

        snapshot = self._b030_uv_snapshot or []
        self._b030_uv_snapshot = None
        if not snapshot:
            self.sb.message_box(
                "<b>No snapshot available.</b><br>"
                "Stack a selection first; Unstack restores the pre-stack positions."
            )
            return
        cmds.refresh(suspend=True)
        try:
            for uv, u, v in snapshot:
                if cmds.objExists(uv):
                    cmds.polyEditUV(uv, uValue=u, vValue=v, relative=False)
        finally:
            cmds.refresh(suspend=False)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
