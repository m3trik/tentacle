# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)

import mayatk as mtk
from tentacle.slots.maya import SlotsMaya
from tentacle.slots.edit import Edit


class Edit_maya(Edit, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dh = self.sb.edit.draggableHeader
        items = ["Cleanup", "Transfer: Attribute Values", "Transfer: Shading Sets"]
        dh.ctx_menu.cmb000.addItems_(items, "Maya Editors")

        tb000 = self.sb.edit.tb000
        tb000.option_menu.add(
            "QCheckBox",
            setText="All Geometry",
            setObjectName="chk005",
            setToolTip="Clean All scene geometry.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Repair",
            setObjectName="chk004",
            setToolTip="Repair matching geometry. Else, select only.",
        )  # add(self.sb.CheckBox, setText='Select Only', setObjectName='chk004', setTristate=True, set_check_state=2, setToolTip='Select and/or Repair matching geometry. <br>0: Repair Only<br>1: Repair and Select<br>2: Select Only')
        tb000.option_menu.add(
            "QCheckBox",
            setText="Merge vertices",
            setObjectName="chk024",
            setChecked=True,
            setToolTip="Merge overlapping vertices on the object(s) before executing the clean command.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="N-Gons",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Find N-gons.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Non-Manifold Geometry",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Check for nonmanifold polys.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Non-Manifold Vertex",
            setObjectName="chk021",
            setToolTip="A connected vertex of non-manifold geometry where the faces share a single vertex.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Quads",
            setObjectName="chk010",
            setToolTip="Check for quad sided polys.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Concave",
            setObjectName="chk011",
            setToolTip="Check for concave polys.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Non-Planar",
            setObjectName="chk003",
            setToolTip="Check for non-planar polys.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Holed",
            setObjectName="chk012",
            setToolTip="Check for holed polys.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Lamina",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Check for lamina polys.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Shared UV's",
            setObjectName="chk016",
            setToolTip="Unshare uvs that are shared across vertices.",
        )
        # tb000.option_menu.add('QCheckBox', setText='Invalid Components', setObjectName='chk019', setToolTip='Check for invalid components.')
        tb000.option_menu.add(
            "QCheckBox",
            setText="Zero Face Area",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Check for 0 area faces.",
        )
        tb000.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Face Area Tolerance:   ",
            setObjectName="s006",
            set_limits="0.0-10 step.000010",
            setValue=0.000010,
            setToolTip="Tolerance for face areas.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Zero Length Edges",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Check for 0 length edges.",
        )
        tb000.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Edge Length Tolerance: ",
            setObjectName="s007",
            set_limits="0.0-10 step.000010",
            setValue=0.000010,
            setToolTip="Tolerance for edge length.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Zero UV Face Area",
            setObjectName="chk015",
            setToolTip="Check for 0 uv face area.",
        )
        tb000.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="UV Face Area Tolerance:",
            setObjectName="s008",
            setDisabled=True,
            set_limits="0.0-10 step.000010",
            setValue=0.000010,
            setToolTip="Tolerance for uv face areas.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Overlapping Faces",
            setObjectName="chk025",
            setToolTip="Find any overlapping duplicate faces. (can be very slow on dense objects)",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Overlapping Duplicate Objects",
            setObjectName="chk022",
            setToolTip="Find any duplicate overlapping geometry at the object level.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Omit Selected Objects",
            setObjectName="chk023",
            setDisabled=True,
            setToolTip="Overlapping Duplicate Objects: Search for duplicates of any selected objects while omitting the initially selected objects.",
        )
        tb000.option_menu.chk013.toggled.connect(
            lambda state: tb000.option_menu.s006.setEnabled(True if state else False)
        )
        tb000.option_menu.chk014.toggled.connect(
            lambda state: tb000.option_menu.s007.setEnabled(True if state else False)
        )
        tb000.option_menu.chk015.toggled.connect(
            lambda state: tb000.option_menu.s008.setEnabled(True if state else False)
        )
        tb000.option_menu.chk022.stateChanged.connect(
            lambda state: self.sb.toggle_widgets(
                tb000.option_menu,
                setDisabled="chk002-3,chk005,chk010-21,chk024,s006-8",
                setEnabled="chk023",
            )
            if state
            else self.sb.toggle_widgets(
                tb000.option_menu,
                setEnabled="chk002-3,chk005,chk010-21,s006-8",
                setDisabled="chk023",
            )
        )  # disable non-relevant options.
        # sync widgets
        self.sb.sync_widgets(
            tb000.option_menu.chk004, self.sb.edit_submenu.chk004, attributes="setChecked"
        )
        self.sb.sync_widgets(
            tb000.option_menu.chk010, self.sb.edit_submenu.chk010, attributes="setChecked"
        )

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.edit.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "Cleanup":
                pm.mel.CleanupPolygonOptions()
            elif text == "Transfer: Attribute Values":
                pm.mel.TransferAttributeValuesOptions()
                # pm.mel.eval('performTransferAttributes 1;') #Transfer Attributes Options
            elif text == "Transfer: Shading Sets":
                pm.mel.performTransferShadingSets(1)
            cmb.setCurrentIndex(0)

    @SlotsMaya.attr
    def cmb001(self, index=-1):
        """Object History Attributes"""
        cmb = self.sb.edit.cmb001

        try:
            items = list(
                set(
                    [
                        n.name()
                        for n in pm.listHistory(
                            pm.ls(sl=1, objectsOnly=1), pruneDagObjects=1
                        )
                    ]
                )
            )  # levels=1, interestLevel=2,
        except RuntimeError:
            items = ["No selection."]
        cmb.addItems_(items, "History")

        cmb.setCurrentIndex(0)
        if index > 0:
            if cmb.items[index] != "No selection.":
                return pm.ls(cmb.items[index])

    def tb000(self, state=None):
        """Mesh Cleanup"""
        tb = self.sb.edit.tb000

        allMeshes = int(tb.option_menu.chk005.isChecked())  # [0] All selectable meshes
        repair = tb.option_menu.chk004.isChecked()  # repair or select only
        quads = int(tb.option_menu.chk010.isChecked())  # [3] check for quads polys
        mergeVertices = tb.option_menu.chk024.isChecked()
        nsided = int(tb.option_menu.chk002.isChecked())  # [4] check for n-sided polys
        concave = int(tb.option_menu.chk011.isChecked())  # [5] check for concave polys
        holed = int(tb.option_menu.chk012.isChecked())  # [6] check for holed polys
        nonplanar = int(
            tb.option_menu.chk003.isChecked()
        )  # [7] check for non-planar polys
        zeroGeom = int(tb.option_menu.chk013.isChecked())  # [8] check for 0 area faces
        zeroGeomTol = tb.option_menu.s006.value()  # [9] tolerance for face areas
        zeroEdge = int(tb.option_menu.chk014.isChecked())  # [10] check for 0 length edges
        zeroEdgeTol = tb.option_menu.s007.value()  # [11] tolerance for edge length
        zeroMap = int(tb.option_menu.chk015.isChecked())  # [12] check for 0 uv face area
        zeroMapTol = tb.option_menu.s008.value()  # [13] tolerance for uv face areas
        sharedUVs = int(
            tb.option_menu.chk016.isChecked()
        )  # [14] Unshare uvs that are shared across vertices
        nonmanifold = int(
            tb.option_menu.chk017.isChecked()
        )  # [15] check for nonmanifold polys
        lamina = -int(
            tb.option_menu.chk018.isChecked()
        )  # [16] check for lamina polys [default -1]
        split_non_manifold_vertex = tb.option_menu.chk021.isChecked()
        invalidComponents = 0  # int(tb.option_menu.chk019.isChecked()) #[17] a guess what this arg does. not checked. default is 0.
        overlappingFaces = tb.option_menu.chk025.isChecked()
        overlappingDuplicateObjects = (
            tb.option_menu.chk022.isChecked()
        )  # find overlapping geometry at object level.
        omitSelectedObjects = (
            tb.option_menu.chk023.isChecked()
        )  # Search for duplicates of any selected objects while omitting the initially selected objects.

        objects = pm.ls(sl=1, transforms=1)

        if overlappingDuplicateObjects:
            duplicates = mtk.Edit.get_overlapping_dup_objects(
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
            duplicates = mtk.Edit.get_overlapping_faces(objects)
            self.sb.message_box(
                "Found {} duplicate overlapping faces.".format(len(duplicates)),
                message_type="Result",
            )
            pm.delete(duplicates) if repair else pm.select(duplicates, add=1)

        mtk.Edit.clean_geometry(
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

    def tb001(self, state=None):
        """Delete History"""
        tb = self.sb.edit.tb001

        all_ = tb.option_menu.chk018.isChecked()
        unusedNodes = tb.option_menu.chk019.isChecked()
        deformers = tb.option_menu.chk020.isChecked()
        optimize = tb.option_menu.chk030.isChecked()

        objects = pm.ls(selection=1, objectsOnly=1) if not all_ else pm.ls(typ="mesh")

        if unusedNodes:
            pm.mel.MLdeleteUnused()  # pm.mel.hyperShadePanelMenuCommand('hyperShadePanel1', 'deleteUnusedNodes')
            # delete empty groups:
            empty = mtk.Node.get_groups(empty=True)
            pm.delete(empty)

        try:  # delete history
            if all_:
                pm.delete(objects, constructionHistory=1)
            else:
                pm.bakePartialHistory(objects, prePostDeformers=1)
        except Exception:
            pass

        if optimize:
            pm.mel.OptimizeScene()

        # display viewPort messages
        if all_:
            if deformers:
                mtk.viewport_message("delete <hl>all</hl> history.")
            else:
                mtk.viewport_message("delete <hl>all non-deformer</hl> history.")
        else:
            if deformers:
                mtk.viewport_message("delete history on " + str(objects))
            else:
                mtk.viewport_message(
                    "delete <hl>non-deformer</hl> history on " + str(objects)
                )

    def tb002(self, state=None):
        """Delete"""
        tb = self.sb.edit.tb002

        deleteRing = tb.option_menu.chk000.isChecked()
        deleteLoop = tb.option_menu.chk001.isChecked()

        # selectionMask = pm.selectMode (query=True, component=True)
        maskVertex = pm.selectType(query=True, vertex=True)
        maskEdge = pm.selectType(query=True, edge=True)
        # maskFacet = pm.selectType(query=True, facet=True)

        objects = pm.ls(sl=1, objectsOnly=1)
        for obj in objects:
            if pm.objectType(obj, isType="joint"):
                pm.removeJoint(obj)  # remove joints

            elif pm.objectType(obj, isType="mesh"):
                if maskEdge:
                    selection = pm.ls(obj, sl=1, flatten=1)
                    if deleteRing:
                        pm.polyDelEdge(
                            mtk.Cmpt.get_edge_path(selection, "edgeRing"),
                            cleanVertices=True,
                        )  # pm.polySelect(edges, edgeRing=True) #select the edge ring.
                    if deleteLoop:
                        pm.polyDelEdge(
                            mtk.Cmpt.get_edge_path(selection, "edgeLoop"),
                            cleanVertices=True,
                        )  # pm.polySelect(edges, edgeLoop=True) #select the edge loop.
                    else:
                        pm.polyDelEdge(selection, cleanVertices=True)  # delete edges

                elif maskVertex:
                    pm.polyDelVertex()  # try delete vertices
                    if pm.ls(sl=1) == objects:  # if nothing was deleted:
                        pm.mel.eval(
                            "polySelectSp -loop;"
                        )  # convert selection to edge loop
                        pm.polyDelEdge(cleanVertices=True)  # delete edges

                else:  # all([selectionMask==1, maskFacet==1]):
                    pm.delete(obj)  # delete faces\mesh objects

    def tb003(self, state=None):
        """Delete Along Axis"""
        tb = self.sb.edit.tb003

        axis = self.sb.get_axis_from_checkboxes("chk006-9", tb.option_menu)

        pm.undoInfo(openChunk=1)
        objects = pm.ls(sl=1, objectsOnly=1)

        for obj in objects:
            mtk.Edit.delete_along_axis(obj, axis)
        pm.undoInfo(closeChunk=1)

    @mtk.undo
    def tb004(self, state=None):
        """Delete Along Axis"""
        tb = self.sb.edit.tb004

        allNodes = tb.option_menu.chk026.isChecked()
        unlock = tb.option_menu.chk027.isChecked()

        # pm.undoInfo(openChunk=1)
        nodes = pm.ls() if allNodes else pm.ls(selection=1)
        for node in nodes:
            pm.lockNode(node, lock=not unlock)
        # pm.undoInfo(closeChunk=1)

    @SlotsMaya.hideMain
    def b001(self):
        """Object History Attributes: get most recent node"""
        cmb = self.sb.edit.cmb001
        self.cmb001()  # refresh the contents of the combobox.

        items = pm.ls(cmb.items[-1])
        if items:
            self.setAttributeWindow(items, checkable_label=True)
        else:
            self.sb.message_box("Found no items to list the history for.")
            return

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
        pm.mel.performTransferShadingSets(0)


# --------------------------------------------------------------------------------------------


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
# b008, b009, b011
