# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Edit(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.edit
        self.submenu = self.sb.loaded_ui.edit_submenu

    def header_init(self, widget):
        """Initialize header menu"""
        widget.menu.add(
            "QPushButton",
            setText="Cut On Axis",
            setObjectName="b000",
            setToolTip="Cut selected objects on axis.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Snap",
            setObjectName="b001",
            setToolTip="Open the snap toolset.",
        )

    def tb000_init(self, widget):
        """Initialize Mesh Cleanup"""
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
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Shared UV's",
            setObjectName="chk016",
            setToolTip="Unshare uvs that are shared across vertices.",
        )
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
        # Get the state of the checkboxes and selected or all mesh objects
        unused_nodes, deformers, optimize = map(
            lambda chk: chk.isChecked(),
            (
                widget.option_box.menu.chk019,
                widget.option_box.menu.chk020,
                widget.option_box.menu.chk030,
            ),
        )
        objects = pm.ls(sl=True, objectsOnly=True) or pm.ls(typ="mesh")

        if unused_nodes:  # Delete unused nodes
            pm.mel.MLdeleteUnused()
            pm.delete(mtk.get_groups(empty=True))

        if deformers:  # Delete all history
            pm.delete(objects, constructionHistory=True)
            self.sb.message_box("<hl>Delete history</hl>")
        else:  # Delete non-deformer history
            shapes = mtk.get_shape_node(objects)
            if shapes:
                try:
                    pm.bakePartialHistory(shapes, prePostDeformers=True)
                    self.sb.message_box("<hl>Delete non-deformer history</hl>")
                except RuntimeError as error:
                    print(f"Bake Partial History Failed: {error}")

        # Optimize the scene
        if optimize:
            pm.mel.OptimizeScene()

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

    def b000(self):
        """Cut On Axis"""
        ui = self.sb.handlers.ui.get("cut_on_axis")
        self.sb.parent().show(ui)

    def b001(self):
        """Snap Toolset"""
        ui = self.sb.handlers.ui.get("snap")
        self.sb.parent().show(ui)

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
