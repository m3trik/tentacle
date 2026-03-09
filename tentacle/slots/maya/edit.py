# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from uitk import Signals
from tentacle.slots.maya._slots_maya import SlotsMaya


class Edit(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.edit
        self.submenu = self.sb.loaded_ui.edit_submenu

    def header_init(self, widget):
        """Initialize header menu"""
        widget.menu.add(
            "QPushButton",
            setText="Attribute Manager",
            setObjectName="b_attr_mgr",
            setToolTip="Open the Attribute Manager.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Cut On Axis",
            setObjectName="b000",
            setToolTip="Cut selected objects on axis.",
        )

    def tb000_init(self, widget):
        """Initialize Mesh Cleanup"""
        widget.option_box.menu.add("Separator", setTitle="General")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="All Geometry",
            setObjectName="chk005",
            setToolTip="Clean All scene geometry.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Repair",
            setObjectName="chk004",
            setToolTip="Repair matching geometry. Else, select only.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete History",
            setObjectName="chk026",
            setChecked=True,
            setToolTip="Bake non-deformer history before executing the cleanup operation.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Merge vertices",
            setObjectName="chk024",
            setChecked=False,
            setToolTip="Merge overlapping vertices on the object(s) before executing the clean command.",
        )
        widget.option_box.menu.add("Separator", setTitle="Topology")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="N-Gons",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Find N-gons.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Non-Manifold Geometry",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Check for nonmanifold polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Quads",
            setObjectName="chk010",
            setToolTip="Check for quad sided polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Concave",
            setObjectName="chk011",
            setToolTip="Check for concave polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Non-Planar",
            setObjectName="chk003",
            setToolTip="Check for non-planar polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Holed",
            setObjectName="chk012",
            setToolTip="Check for holed polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lamina",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Check for lamina polys.",
        )
        widget.option_box.menu.add("Separator", setTitle="UVs")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Shared UV's",
            setObjectName="chk016",
            setToolTip="Unshare uvs that are shared across vertices.",
        )
        widget.option_box.menu.add("Separator", setTitle="Tolerances")
        # widget.option_box.menu.add('QCheckBox', setText='Invalid Components', setObjectName='chk019', setToolTip='Check for invalid components.')
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Zero Face Area",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Check for 0 area faces.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Face Area Tolerance:   ",
            setObjectName="s006",
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for face areas.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Zero Length Edges",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Check for 0 length edges.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Edge Length Tolerance: ",
            setObjectName="s007",
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for edge length.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Zero UV Face Area",
            setObjectName="chk015",
            setToolTip="Check for 0 uv face area.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="UV Face Area Tolerance:",
            setObjectName="s008",
            setDisabled=True,
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for uv face areas.",
        )
        widget.option_box.menu.add("Separator", setTitle="Overlapping")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Overlapping Faces",
            setObjectName="chk025",
            setToolTip="Find any overlapping duplicate faces. (can be very slow on dense objects)",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Overlapping Duplicate Objects",
            setObjectName="chk022",
            setToolTip="Find any duplicate overlapping geometry at the object level.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Omit Selected Objects",
            setObjectName="chk023",
            setDisabled=True,
            setToolTip="Overlapping Duplicate Objects: Search for duplicates of any selected objects while omitting the initially selected objects.",
        )
        widget.option_box.menu.chk013.toggled.connect(
            lambda state: widget.option_box.menu.s006.setEnabled(
                True if state else False
            )
        )
        widget.option_box.menu.chk014.toggled.connect(
            lambda state: widget.option_box.menu.s007.setEnabled(
                True if state else False
            )
        )
        widget.option_box.menu.chk015.toggled.connect(
            lambda state: widget.option_box.menu.s008.setEnabled(
                True if state else False
            )
        )
        widget.option_box.menu.chk022.stateChanged.connect(
            lambda state: (
                self.sb.toggle_multi(
                    widget.menu,
                    setDisabled="chk002-3,chk005,chk010-21,chk024,s006-8",
                    setEnabled="chk023",
                )
                if state
                else self.sb.toggle_multi(
                    widget.menu,
                    setEnabled="chk002-3,chk005,chk010-21,s006-8",
                    setDisabled="chk023",
                )
            )
        )  # disable non-relevant options.

    def tb000(self, widget):
        """Mesh Cleanup"""
        # [0] All selectable meshes
        allMeshes = int(widget.option_box.menu.chk005.isChecked())
        repair = widget.option_box.menu.chk004.isChecked()  # repair or select only
        # [3] check for quads polys
        quads = int(widget.option_box.menu.chk010.isChecked())
        mergeVertices = widget.option_box.menu.chk024.isChecked()
        # [4] check for n-sided polys
        nsided = int(widget.option_box.menu.chk002.isChecked())
        # [5] check for concave polys
        concave = int(widget.option_box.menu.chk011.isChecked())
        holed = int(
            widget.option_box.menu.chk012.isChecked()
        )  # [6] check for holed polys
        # [7] check for non-planar polys
        nonplanar = int(widget.option_box.menu.chk003.isChecked())
        # [8] check for 0 area faces
        zeroGeom = int(widget.option_box.menu.chk013.isChecked())
        zeroGeomTol = (
            widget.option_box.menu.s006.value()
        )  # [9] tolerance for face areas
        # [10] check for 0 length edges
        zeroEdge = int(widget.option_box.menu.chk014.isChecked())
        zeroEdgeTol = (
            widget.option_box.menu.s007.value()
        )  # [11] tolerance for edge length
        # [12] check for 0 uv face area
        zeroMap = int(widget.option_box.menu.chk015.isChecked())
        zeroMapTol = (
            widget.option_box.menu.s008.value()
        )  # [13] tolerance for uv face areas
        # [14] Unshare uvs that are shared across vertices
        sharedUVs = int(widget.option_box.menu.chk016.isChecked())
        # [15] check for nonmanifold polys
        nonmanifold = int(widget.option_box.menu.chk017.isChecked())
        # [16] check for lamina polys [default -1]
        # lamina = -int(widget.option_box.menu.chk018.isChecked())
        invalidComponents = 0  # int(widget.option_box.menu.chk019.isChecked()) #[17] a guess what this arg does. not checked. default is 0.
        overlappingFaces = widget.option_box.menu.chk025.isChecked()
        # Find overlapping geometry at object level.
        overlappingDuplicateObjects = widget.option_box.menu.chk022.isChecked()
        # Search for duplicates of any selected objects while omitting the initially selected objects.
        omitSelectedObjects = widget.option_box.menu.chk023.isChecked()
        delete_history = widget.option_box.menu.chk026.isChecked()

        objects = pm.ls(sl=1, transforms=1)

        if overlappingDuplicateObjects:
            duplicates = mtk.get_overlapping_duplicates(
                retain_given_objects=omitSelectedObjects, select=True, verbose=True
            )
            self.sb.message_box(
                f"Found {len(duplicates)} duplicate overlapping objects."
            )
            pm.delete(duplicates) if repair else pm.select(duplicates)
            return

        if mergeVertices:  # Merge vertices on each object.
            mtk.merge_vertices(objects, tolerance=0.0001)

        if overlappingFaces:
            duplicates = mtk.get_overlapping_faces(objects)
            self.sb.message_box(f"Found {len(duplicates)} duplicate overlapping faces.")
            pm.delete(duplicates) if repair else pm.select(duplicates, add=1)

        try:
            mtk.Diagnostics.clean_geometry(
                objects,
                allMeshes=allMeshes,
                repair=repair,
                quads=quads,
                nsided=nsided,
                concave=concave,
                holed=holed,
                nonplanar=nonplanar,
                zeroGeom=zeroGeom,
                zeroGeomTol=zeroGeomTol,
                zeroEdge=zeroEdge,
                zeroEdgeTol=zeroEdgeTol,
                zeroMap=zeroMap,
                zeroMapTol=zeroMapTol,
                sharedUVs=sharedUVs,
                nonmanifold=nonmanifold,
                invalidComponents=invalidComponents,
                bakePartialHistory=delete_history,
            )
        except (ValueError, RuntimeError) as exc:
            pm.warning(str(exc))
            self.sb.message_box(str(exc))
            return

    def tb001_init(self, widget):
        """Initialize Delete History"""
        widget.option_box.menu.add(
            "QCheckBox",
            setText="For All Objects",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Delete history on All objects or just those selected.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Unused Nodes",
            setObjectName="chk019",
            setChecked=True,
            setToolTip="Delete unused nodes.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Deformers",
            setObjectName="chk020",
            setToolTip="Delete deformers.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Optimize Scene",
            setObjectName="chk030",
            setToolTip="Remove unused scene objects.",
        )

    def tb001(self, widget):
        """Delete History"""
        import maya.cmds as cmds

        unused_nodes, deformers, optimize = map(
            lambda chk: chk.isChecked(),
            (
                widget.option_box.menu.chk019,
                widget.option_box.menu.chk020,
                widget.option_box.menu.chk030,
            ),
        )

        # Use cmds for bulk queries (avoids PyMEL object wrapping overhead)
        sel = cmds.ls(sl=True, objectsOnly=True, long=True)
        if sel:
            objects = sel
            # Batch-extract non-intermediate shapes from all selected at once
            shapes = set(
                cmds.listRelatives(sel, shapes=True, fullPath=True, noIntermediate=True)
                or []
            )
        else:
            # All non-intermediate mesh shapes in scene
            all_meshes = cmds.ls(typ="mesh", long=True) or []
            intermediates = set(cmds.ls(intermediateObjects=True, long=True) or [])
            shapes = set(all_meshes) - intermediates
            objects = list(shapes)

        result_msg = None

        # Suspend viewport refresh for the duration of the cleanup
        pm.refresh(suspend=True)
        try:
            if unused_nodes:
                pm.mel.MLdeleteUnused()
                # Fast empty-group deletion via DAG path parsing
                # A "group" is an exact-type transform with no shape children.
                # An "empty group" is a group with no DAG children at all.
                all_dag = cmds.ls(dag=True, long=True) or []
                exact_transforms = set(cmds.ls(exactType="transform", long=True) or [])
                shape_parents = {
                    s.rsplit("|", 1)[0] for s in (cmds.ls(shapes=True, long=True) or [])
                }
                dag_parents = {p.rsplit("|", 1)[0] for p in all_dag if "|" in p} - {""}
                groups = exact_transforms - shape_parents
                empty_groups = [g for g in groups if g not in dag_parents]
                if empty_groups:
                    # Re-validate existence (MLdeleteUnused may have removed some)
                    existing = cmds.ls(empty_groups, long=True) or []
                    if existing:
                        cmds.delete(existing)

            if deformers:
                if objects:
                    cmds.delete(objects, constructionHistory=True)
                result_msg = "<hl>Delete history</hl>"
            else:
                if shapes:
                    try:
                        cmds.bakePartialHistory(list(shapes), prePostDeformers=True)
                        result_msg = "<hl>Delete non-deformer history</hl>"
                    except RuntimeError as error:
                        print(f"Bake Partial History Failed: {error}")

            if optimize:
                pm.mel.OptimizeScene()
        finally:
            pm.refresh(suspend=False)
            pm.refresh(force=True)

        if result_msg:
            self.sb.message_box(result_msg)

    def tb002(self, widget):
        """Delete Selected"""
        mtk.delete_selected()

    def tb004_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Toggle Lock/UnLock",
            setObjectName="chk027",
            setChecked=True,
            setToolTip="Unlock nodes (else lock).",
        )
        widget.option_box.menu.chk027.toggled.connect(
            lambda state: widget.setText("Unlock Nodes" if state else "Lock Nodes")
        )

    @mtk.undoable
    def tb004(self, widget):
        """Node Locking"""
        unlock = widget.option_box.menu.chk027.isChecked()

        selection = pm.ls(sl=True)
        # If not selection use all nodes
        nodes = selection if selection else pm.ls()
        for node in nodes:
            pm.lockNode(node, lock=not unlock)

    def b_attr_mgr(self):
        """Attribute Manager"""
        self.sb.handlers.marking_menu.show("attribute_manager")

    def b000(self):
        """Cut On Axis"""
        self.sb.handlers.marking_menu.show("cut_on_axis")

    # --- Create Expandable List -----------------------------------------

    def list000_init(self, widget):
        """Initialize Create Primitives list."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_left")

        root = widget.add("Create")
        root.sublist.setMinimumWidth(widget.width() or 120)

        primitives = {
            "Polygon": [
                "Cube",
                "Sphere",
                "Cylinder",
                "Plane",
                "Circle",
                "Cone",
                "Pyramid",
                "Torus",
                "Helix",
                "Tube",
                "GeoSphere",
                "Platonic Solids",
                "Text",
            ],
            "NURBS": [
                "Cube",
                "Sphere",
                "Cylinder",
                "Cone",
                "Plane",
                "Torus",
                "Circle",
                "Square",
            ],
            "Light": [
                "Ambient",
                "Directional",
                "Point",
                "Spot",
                "Area",
                "Volume",
            ],
            "Control": [
                "Diamond",
                "Arrow",
                "Two Way Arrow",
                "Four Way Arrow",
                "Chevron",
                "Target",
                "Box",
                "Beveled Cube",
                "Ball",
                "Torus",
                "Helix",
                "Geosphere",
                "Pyramid",
                "Star",
            ],
        }

        for category, types in primitives.items():
            w = root.sublist.add(category)
            w.sublist.add(types)

    @Signals("on_item_interacted")
    def list000(self, item):
        """Create Primitive"""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        text = item.item_text()
        parent_text = item.parent_item_text() or ""

        if parent_text == "Control":
            control_map = {
                "Diamond": ("diamond", {}),
                "Arrow": ("arrow", {}),
                "Two Way Arrow": ("two_way_arrow", {}),
                "Four Way Arrow": ("four_way_arrow", {}),
                "Chevron": ("chevron", {}),
                "Target": ("target", {}),
                "Box": ("box", {}),
                "Beveled Cube": ("beveled_cube", {}),
                "Ball": ("ball", {}),
                "Torus": ("torus", {}),
                "Helix": ("helix", {}),
                "Geosphere": ("geosphere", {}),
                "Pyramid": ("pyramid", {}),
                "Star": ("star", {}),
            }
            if text in control_map:
                preset, kwargs = control_map[text]
                ctrl = mtk.Controls.create(preset, name=text.replace(" ", ""), **kwargs)
                pm.select(ctrl)
        else:
            try:
                mtk.Primitives.create_default_primitive(parent_text, text)
                pm.selectMode(object=True)
            except Exception as e:
                pm.warning(f"Error creating {parent_text} {text}: {e}")

    # --- Convert Expandable List ----------------------------------------

    _CONVERT_COMMANDS = {
        "NURBS to Polygons": "performnurbsToPoly 0;",
        "NURBS to Subdiv": "performSubdivCreate 0;",
        "Polygons to Subdiv": "performSubdivCreate 0;",
        "Smooth Mesh Preview to Polygons": "performSmoothMeshPreviewToPolygon;",
        "Polygon Edges to Curve": "polyToCurve -form 2 -degree 3 -conformToSmoothMeshPreview 1;",
        "Type to Curves": "convertTypeCapsToCurves;",
        "Subdiv to Polygons": "performSubdivTessellate  false;",
        "Subdiv to NURBS": "performSubdToNurbs 0;",
        "NURBS Curve to Bezier": "nurbsCurveToBezier;",
        "Bezier Curve to NURBS": "bezierCurveToNurbs;",
        "Paint Effects to NURBS": "performPaintEffectsToNurbs  false;",
        "Paint Effects to Curves": "performPaintEffectsToCurve  false;",
        "Texture to Geometry": "performTextureToGeom 0;",
        "Displacement to Polygons": "displacementToPoly;",
        "Displacement to Poly w/ History": "setupAnimatedDisplacement;",
        "Fluid to Polygons": "fluidToPoly;",
        "nParticle to Polygons": "particleToPoly;",
        "Instance to Object": "convertInstanceToObject;",
        "Geometry to Bounding Box": "performGeomToBBox 0;",
    }

    def list001_init(self, widget):
        """Initialize Convert list."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_down")

        root = widget.add("Convert")
        root.sublist.setMinimumWidth(180)
        root.sublist.add(list(self._CONVERT_COMMANDS))

    @Signals("on_item_interacted")
    def list001(self, item):
        """Convert"""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        text = item.item_text()
        cmd = self._CONVERT_COMMANDS.get(text)
        if cmd:
            try:
                pm.mel.eval(cmd)
            except Exception as e:
                pm.warning(f"Convert '{text}' failed: {e}")

    def b021(self):
        """Tranfer Maps"""
        pm.mel.performSurfaceSampling(1)

    def b022(self):
        """Transfer Vertex Order"""
        pm.mel.TransferVertexOrder()

    def b023(self):
        """Transfer Attribute Values"""
        pm.mel.TransferAttributeValues()

    def b027(self):
        """Shading Sets"""
        selected_objects = pm.selected(type="surfaceShape")
        if selected_objects:
            pm.mel.performTransferShadingSets(0)
        else:
            raise ValueError(
                "Please select at least one surface to perform the shading transfer."
            )


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
