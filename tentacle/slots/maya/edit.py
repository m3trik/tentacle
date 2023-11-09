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

        self.ui = self.sb.edit
        self.submenu = self.sb.edit_submenu

        # Refresh the combo box on every view show
        self.ui.cmb001.before_popup_shown.connect(self.ui.cmb001.init_slot)

    def cmb001_init(self, widget):
        """ """
        widget.refresh = True
        try:
            selection = pm.ls(sl=1, objectsOnly=1)
            obj_hist = pm.listHistory(selection, pruneDagObjects=1)
            items = {str(o): o for o in obj_hist}
        except RuntimeError:
            items = ["No selection."]
        widget.add(items, header="History", clear=True)

    def cmb001(self, index, widget):
        """Object History Attributes"""
        if widget.items[index] != "No selection.":
            node = widget.itemData(index)
            if node:
                attrs = mtk.get_node_attributes(
                    node,
                    mapping=True,
                    visible=True,
                    keyable=True,
                )
                window = self.sb.AttributeWindow(
                    node,
                    attrs,
                    window_title=node.name(),
                    set_attribute_func=lambda obj, n, v: getattr(obj, n).set(v),
                )
                window.set_style(theme="dark")
                window.set_flags(WindowStaysOnTopHint=True)
                window.show()
        else:
            self.sb.message_box("Found no items to list the history for.")

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="All Geometry",
            setObjectName="chk005",
            setToolTip="Clean All scene geometry.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Repair",
            setObjectName="chk004",
            setToolTip="Repair matching geometry. Else, select only.",
        )  # add(self.sb.CheckBox, setText='Select Only', setObjectName='chk004', setTristate=True, setCheckState=2, setToolTip='Select and/or Repair matching geometry. <br>0: Repair Only<br>1: Repair and Select<br>2: Select Only')
        widget.menu.add(
            "QCheckBox",
            setText="Merge vertices",
            setObjectName="chk024",
            setChecked=True,
            setToolTip="Merge overlapping vertices on the object(s) before executing the clean command.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="N-Gons",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Find N-gons.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Non-Manifold Geometry",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Check for nonmanifold polys.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Non-Manifold Vertex",
            setObjectName="chk021",
            setToolTip="A connected vertex of non-manifold geometry where the faces share a single vertex.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Quads",
            setObjectName="chk010",
            setToolTip="Check for quad sided polys.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Concave",
            setObjectName="chk011",
            setToolTip="Check for concave polys.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Non-Planar",
            setObjectName="chk003",
            setToolTip="Check for non-planar polys.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Holed",
            setObjectName="chk012",
            setToolTip="Check for holed polys.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Lamina",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Check for lamina polys.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Shared UV's",
            setObjectName="chk016",
            setToolTip="Unshare uvs that are shared across vertices.",
        )
        # widget.menu.add('QCheckBox', setText='Invalid Components', setObjectName='chk019', setToolTip='Check for invalid components.')
        widget.menu.add(
            "QCheckBox",
            setText="Zero Face Area",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Check for 0 area faces.",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Face Area Tolerance:   ",
            setObjectName="s006",
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for face areas.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Zero Length Edges",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Check for 0 length edges.",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Edge Length Tolerance: ",
            setObjectName="s007",
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for edge length.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Zero UV Face Area",
            setObjectName="chk015",
            setToolTip="Check for 0 uv face area.",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="UV Face Area Tolerance:",
            setObjectName="s008",
            setDisabled=True,
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for uv face areas.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Overlapping Faces",
            setObjectName="chk025",
            setToolTip="Find any overlapping duplicate faces. (can be very slow on dense objects)",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Overlapping Duplicate Objects",
            setObjectName="chk022",
            setToolTip="Find any duplicate overlapping geometry at the object level.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Omit Selected Objects",
            setObjectName="chk023",
            setDisabled=True,
            setToolTip="Overlapping Duplicate Objects: Search for duplicates of any selected objects while omitting the initially selected objects.",
        )
        widget.menu.chk013.toggled.connect(
            lambda state: widget.menu.s006.setEnabled(True if state else False)
        )
        widget.menu.chk014.toggled.connect(
            lambda state: widget.menu.s007.setEnabled(True if state else False)
        )
        widget.menu.chk015.toggled.connect(
            lambda state: widget.menu.s008.setEnabled(True if state else False)
        )
        widget.menu.chk022.stateChanged.connect(
            lambda state: self.sb.toggle_multi(
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
        )  # disable non-relevant options.

    def tb000(self, widget):
        """Mesh Cleanup"""
        # [0] All selectable meshes
        allMeshes = int(widget.menu.chk005.isChecked())
        repair = widget.menu.chk004.isChecked()  # repair or select only
        # [3] check for quads polys
        quads = int(widget.menu.chk010.isChecked())
        mergeVertices = widget.menu.chk024.isChecked()
        # [4] check for n-sided polys
        nsided = int(widget.menu.chk002.isChecked())
        # [5] check for concave polys
        concave = int(widget.menu.chk011.isChecked())
        holed = int(widget.menu.chk012.isChecked())  # [6] check for holed polys
        # [7] check for non-planar polys
        nonplanar = int(widget.menu.chk003.isChecked())
        # [8] check for 0 area faces
        zeroGeom = int(widget.menu.chk013.isChecked())
        zeroGeomTol = widget.menu.s006.value()  # [9] tolerance for face areas
        # [10] check for 0 length edges
        zeroEdge = int(widget.menu.chk014.isChecked())
        zeroEdgeTol = widget.menu.s007.value()  # [11] tolerance for edge length
        # [12] check for 0 uv face area
        zeroMap = int(widget.menu.chk015.isChecked())
        zeroMapTol = widget.menu.s008.value()  # [13] tolerance for uv face areas
        # [14] Unshare uvs that are shared across vertices
        sharedUVs = int(widget.menu.chk016.isChecked())
        # [15] check for nonmanifold polys
        nonmanifold = int(widget.menu.chk017.isChecked())
        # [16] check for lamina polys [default -1]
        # lamina = -int(widget.menu.chk018.isChecked())
        split_non_manifold_vertex = widget.menu.chk021.isChecked()
        invalidComponents = 0  # int(widget.menu.chk019.isChecked()) #[17] a guess what this arg does. not checked. default is 0.
        overlappingFaces = widget.menu.chk025.isChecked()
        overlappingDuplicateObjects = (
            widget.menu.chk022.isChecked()
        )  # find overlapping geometry at object level.
        omitSelectedObjects = (
            widget.menu.chk023.isChecked()
        )  # Search for duplicates of any selected objects while omitting the initially selected objects.

        objects = pm.ls(sl=1, transforms=1)

        if overlappingDuplicateObjects:
            duplicates = mtk.get_overlapping_duplicates(
                retain_given_objects=omitSelectedObjects, select=True, verbose=True
            )
            self.sb.message_box(
                "Found {} duplicate overlapping objects.".format(len(duplicates)),
                message_type="Result",
            )
            pm.delete(duplicates) if repair else pm.select(duplicates)
            return

        if mergeVertices:
            [
                pm.polyMergeVertex(obj.verts, distance=0.0001) for obj in objects
            ]  # merge vertices on each object.

        if overlappingFaces:
            duplicates = mtk.get_overlapping_faces(objects)
            self.sb.message_box(
                "Found {} duplicate overlapping faces.".format(len(duplicates)),
                message_type="Result",
            )
            pm.delete(duplicates) if repair else pm.select(duplicates, add=1)

        mtk.clean_geometry(
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
            split_non_manifold_vertex=split_non_manifold_vertex,
        )

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="For All Objects",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Delete history on All objects or just those selected.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Delete Unused Nodes",
            setObjectName="chk019",
            setChecked=True,
            setToolTip="Delete unused nodes.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Delete Deformers",
            setObjectName="chk020",
            setToolTip="Delete deformers.",
        )
        widget.menu.add(
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
            (widget.menu.chk019, widget.menu.chk020, widget.menu.chk030),
        )
        objects = pm.ls(sl=True, objectsOnly=1) or pm.ls(typ="mesh")

        # Delete unused nodes
        if unused_nodes:
            pm.mel.MLdeleteUnused()
            pm.delete(mtk.get_groups(empty=True))

        # Delete history
        if deformers:
            pm.delete(objects, constructionHistory=1)
            self.sb.message_box("<hl>Delete history</hl>")
        else:
            pm.bakePartialHistory(objects, prePostDeformers=1)
            self.sb.message_box("<hl>Delete non-deformer history</hl>")

        # Optimize the scene
        if optimize:
            pm.mel.OptimizeScene()

    def tb002(self, widget):
        """Delete Selected"""
        mtk.delete_selected()

    def tb004_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="UnLock",
            setObjectName="chk027",
            setChecked=True,
            setToolTip="Unlock nodes (else lock).",
        )
        widget.menu.chk027.toggled.connect(
            lambda state: widget.setText("Unlock Nodes" if state else "Lock Nodes")
        )

    @mtk.undo
    def tb004(self, widget):
        """Node Locking"""
        unlock = widget.menu.chk027.isChecked()

        selection = pm.ls(sl=True)
        # If not selection use all nodes
        nodes = selection if selection else pm.ls()
        for node in nodes:
            pm.lockNode(node, lock=not unlock)

    def b000(self):
        """Cut On Axis"""
        module = mtk.edit_utils.cut_on_axis
        slot_class = module.CutOnAxisSlots

        self.sb.register("cut_on_axis.ui", slot_class, base_dir=module)
        self.sb.cut_on_axis.slots.preview.enable_on_show = True
        self.sb.parent().set_ui("cut_on_axis")

    @SlotsMaya.hide_main
    def b001(self):
        """Object History Attributes: get most recent node"""
        cmb = self.ui.cmb001
        index = cmb.items.index(cmb.items[-1])
        cmb.call_slot(index)

    @SlotsMaya.hide_main
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
