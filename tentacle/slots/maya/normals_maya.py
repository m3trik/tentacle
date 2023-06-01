# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)

import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Normals_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dh = self.sb.normals.draggableHeader
        dh.ctx_menu.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

    def tb000_init(self, widget):
        """ """
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Display Size: ",
            setObjectName="s001",
            set_limits="1-100 step1",
            setValue=1,
            setToolTip="Normal display size.",
        )

    def tb001_init(self, widget):
        """ """
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Query Angle: ",
            setObjectName="s002",
            set_limits="0-180 step1",
            setValue=90,
            setToolTip="The normal angle to query threshold in degrees.",
        )
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Smoothing Angle: ",
            setObjectName="s003",
            set_limits="0-180 step1",
            setValue=0,
            setToolTip="The normal smoothing angle in degrees.\n 0, Edges will appear hard.\n180, Edges will appear soft.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Harden Creased Edges",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Harden creased edges.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Harden UV Borders",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Harden UV shell border edges.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Soften All Other",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="Soften all non-hardened edges.\nLimited by the current selection.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Soft Edge Display",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Turn on soft edge display for the object.",
        )

    def tb002_init(self, widget):
        """ """
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Angle: ",
            setObjectName="s000",
            set_limits="0-180 step1",
            setValue=60,
            setToolTip="Angle degree.",
        )

    def tb003_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Lock",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Toggle Lock/Unlock.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="All",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Lock/Unlock All.",
        )
        widget.option_menu.chk002.toggled.connect(
            lambda state, w=widget.option_menu.chk002: w.setText("Lock")
            if state
            else w.setText("Unlock")
        )

    def tb004_init(self, widget):
        """ """
        print("tb004_init:", widget.ui.name, widget.name)
        widget.option_menu.add(
            "QCheckBox",
            setText="By UV Shell",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Average the normals of each object's faces per UV shell.",
        )

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.normals.draggableHeader.ctx_menu.cmb000

        if index > 0:
            if index == cmb.items.index(""):
                pass
            cmb.setCurrentIndex(0)

    def tb000(self, state=None):
        """Display Face Normals"""
        tb = self.sb.normals.tb000

        size = float(tb.option_menu.s001.value())
        # state = pm.polyOptions (query=True, displayNormal=True)
        state = ptk.cycle([1, 2, 3, 0], "displayNormals")
        if state == 0:  # off
            pm.polyOptions(displayNormal=0, sizeNormal=0)
            pm.polyOptions(displayTangent=False)
            mtk.viewport_message("Normals Display <hl>Off</hl>.")

        if state == 1:  # facet
            pm.polyOptions(displayNormal=1, facet=True, sizeNormal=size)
            pm.polyOptions(displayTangent=False)
            mtk.viewport_message("<hl>Facet</hl> Normals Display <hl>On</hl>.")

        if state == 2:  # Vertex
            pm.polyOptions(displayNormal=1, point=True, sizeNormal=size)
            pm.polyOptions(displayTangent=False)
            mtk.viewport_message("<hl>Vertex</hl> Normals Display <hl>On</hl>.")

        if state == 3:  # tangent
            pm.polyOptions(displayTangent=True)
            pm.polyOptions(displayNormal=0)
            mtk.viewport_message("<hl>Tangent</hl> Display <hl>On</hl>.")

    def tb001(self, state=None):
        """Harden Edge Normals"""
        tb = self.sb.normals.tb001

        query_angle = tb.option_menu.s002.value()
        smoothing_angle = tb.option_menu.s003.value()
        harden_creased = tb.option_menu.chk005.isChecked()
        harden_uv_borders = tb.option_menu.chk006.isChecked()
        soften_other = tb.option_menu.chk004.isChecked()
        soft_edge_display = tb.option_menu.chk007.isChecked()

        selected_objects = pm.selected(objectsOnly=True)

        hard_edges = []
        evaluated_edges = []
        for obj in selected_objects:
            all_edges = pm.ls(pm.polyListComponentConversion(obj, toEdge=True), fl=True)
            selected_edges = pm.ls(pm.filterExpand(sm=32), fl=True) or all_edges
            evaluated_edges.extend(selected_edges)

            angled_edges = mtk.get_edges_by_normal_angle(
                selected_edges, high_angle=query_angle
            )
            hard_edges.extend(angled_edges)

            creased_edges = []
            if harden_creased:
                creased_edges = pm.ls(
                    self.sb.crease.slots.getCreasedEdges(selected_edges)
                )
                hard_edges.extend(creased_edges)

            uv_border_edges = []
            if harden_uv_borders:
                uv_border_edges = pm.ls(
                    self.sb.uv.slots.getUvShellBorderEdges(selected_edges)
                )
                hard_edges.extend(uv_border_edges)

        if hard_edges:  # Set hard edges.
            pm.polySoftEdge(hard_edges, angle=smoothing_angle, constructionHistory=True)

        if soften_other:
            soft_edges = [
                e for e in evaluated_edges if e not in pm.ls(hard_edges, flatten=True)
            ]
            if soft_edges:  # Set soft edges.
                pm.polySoftEdge(
                    soft_edges,
                    angle=180,
                    constructionHistory=True,
                )

        pm.polyOptions(selected_objects, se=soft_edge_display)
        pm.select(hard_edges)

    @SlotsMaya.attr
    def tb002(self, state=None):
        """Set Normals By Angle"""
        tb = self.sb.normals.tb002

        normalAngle = str(tb.option_menu.s000.value())

        objects = pm.ls(selection=1, objectsOnly=1, flatten=1)
        for obj in objects:
            sel = pm.ls(obj, sl=1)
            pm.polySetToFaceNormal(sel, setUserNormal=1)  # reset to face
            polySoftEdge = pm.polySoftEdge(
                sel, angle=normalAngle
            )  # smooth if angle is lower than specified amount. default:60
            if len(objects) == 1:
                return polySoftEdge

    def tb003(self, state=None):
        """Lock/Unlock Vertex Normals"""
        tb = self.sb.normals.tb003

        all_ = tb.option_menu.chk001.isChecked()
        state = (
            tb.option_menu.chk002.isChecked()
        )  # pm.polyNormalPerVertex(vertex, query=1, freezeNormal=1)
        selection = pm.ls(selection=1, objectsOnly=1)
        maskObject = pm.selectMode(query=1, object=1)
        maskVertex = pm.selectType(query=1, vertex=1)

        if not selection:
            self.sb.message_box("Operation requires at least one selected object.")
            return

        if (all_ and maskVertex) or maskObject:
            for obj in selection:
                vertices = mtk.Cmpt.get_components(obj, "vertices", flatten=1)
                for vertex in vertices:
                    if not state:
                        pm.polyNormalPerVertex(vertex, unFreezeNormal=1)
                    else:
                        pm.polyNormalPerVertex(vertex, freezeNormal=1)
                if not state:
                    mtk.viewport_message("Normals <hl>UnLocked</hl>.")
                else:
                    mtk.viewport_message("Normals <hl>Locked</hl>.")
        elif maskVertex and not maskObject:
            if not state:
                pm.polyNormalPerVertex(unFreezeNormal=1)
                mtk.viewport_message("Normals <hl>UnLocked</hl>.")
            else:
                pm.polyNormalPerVertex(freezeNormal=1)
                mtk.viewport_message("Normals <hl>Locked</hl>.")
        else:
            self.sb.message_box(
                "Selection must be object or vertex.", message_type="Warning"
            )
            return

    def tb004(self, state=None):
        """Average Normals"""
        tb = self.sb.normals.tb004

        byUvShell = tb.option_menu.chk003.isChecked()

        objects = pm.ls(selection=1, objectsOnly=1, flatten=1)
        self.averageNormals(objects, byUvShell=byUvShell)

    def b001(self):
        """Soften Edge Normals"""
        sel = pm.ls(sl=1)
        if sel:
            pm.polySoftEdge(sel, angle=180, constructionHistory=0)

    def b002(self):
        """Transfer Normals"""
        source, *target = pm.ls(sl=1)
        self.transferNormals(source, target)

    def b003(self):
        """Soft Edge Display"""
        g_cond = pm.polyOptions(q=1, ae=1)
        if g_cond[0]:
            pm.polyOptions(se=1)
        else:
            pm.polyOptions(ae=1)

    def b005(self):
        """Maya Bonus Tools: Adjust Vertex Normals"""
        pm.mel.bgAdjustVertexNormalsWin()

    def b006(self):
        """Set To Face"""
        pm.polySetToFaceNormal()

    def b010(self):
        """Reverse Normals"""
        for obj in pm.ls(sl=1, objectsOnly=1):
            sel = pm.ls(obj, sl=1)
            pm.polyNormal(
                sel, normalMode=3, userNormalMode=1
            )  # 3: reverse and cut a new shell on selected face(s). 4: reverse and propagate; Reverse the normal(s) and propagate this direction to all other faces in the shell.

    def averageNormals(self, objects, byUvShell=False):
        """Average Normals

        Parameters:
                byUvShell (bool): Average each UV shell individually.
        """
        pm.undoInfo(openChunk=1)
        for obj in objects:
            if byUvShell:
                obj = pm.ls(obj, transforms=1)
                sets_ = self.sb.uv.slots.getUvShellSets(obj)
                for set_ in sets_:
                    pm.polySetToFaceNormal(set_)
                    pm.polyAverageNormal(set_)
            else:
                sel = pm.ls(obj, sl=1)
                if not sel:
                    sel = obj
                pm.polySetToFaceNormal(sel)
                pm.polyAverageNormal(sel)
        pm.undoInfo(closeChunk=1)

    @staticmethod
    def getNormalVector(obj):
        """Get the normal vectors of the given poly object.

        Parameters:
                obj (str/obj/list): A polygon mesh or it's component(s).

        Returns:
                dict - {int:[float, float, float]} face id & vector xyz.
        """
        obj = pm.ls(obj)
        normals = pm.polyInfo(obj, faceNormals=1)

        regex = "[A-Z]*_[A-Z]* *[0-9]*: "

        dict_ = {}
        for n in normals:
            l = list(
                s.replace(regex, "") for s in n.split() if s
            )  # ['FACE_NORMAL', '150:', '0.935741', '0.110496', '0.334931\n']

            key = int(l[1].strip(":"))  # int face number as key ie. 150
            value = list(
                float(i) for i in l[-3:]
            )  # vector list as value. ie. [[0.935741, 0.110496, 0.334931]]
            dict_[key] = value

        return dict_

    @classmethod
    def getFacesWithSimilarNormals(
        cls,
        faces,
        transforms=[],
        similarFaces=[],
        rangeX=0.1,
        rangeY=0.1,
        rangeZ=0.1,
        returned_type="str",
    ):
        """Filter for faces with normals that fall within an X,Y,Z tolerance.

        Parameters:
                faces (list): ['polygon faces'] - faces to find similar normals for.
                similarFaces (list): optional ability to add faces from previous calls to the return value.
                transforms (list): [<shape nodes>] - objects to check faces on. If none are given the objects containing the given faces will be used.
                rangeX = float - x axis tolerance
                rangeY = float - y axis tolerance
                rangeZ = float - z axis tolerance
                returned_type (str): The desired returned object type.
                                                valid: 'str'(default), 'obj'(shape object), 'transform'(as string), 'int'(valid only at sub-object level).
        Returns:
                (list) faces that fall within the given normal range.

        ex. getFacesWithSimilarNormals(selectedFaces, rangeX=0.5, rangeY=0.5, rangeZ=0.5)
        """
        faces = pm.ls(
            faces, flatten=1
        )  # work on a copy of the argument so that removal of elements doesn't effect the passed in list.
        for face in faces:
            normals = cls.getNormalVector(face)

            for k, v in normals.items():
                sX, sY, sZ = v

                if not transforms:
                    transforms = pm.ls(face, objectsOnly=True)

                for node in transforms:
                    for f in cls.get_components(
                        node, "faces", returned_type=returned_type, flatten=1
                    ):
                        n = cls.getNormalVector(f)
                        for k, v in n.items():
                            nX, nY, nZ = v

                            if (
                                sX <= nX + rangeX
                                and sX >= nX - rangeX
                                and sY <= nY + rangeY
                                and sY >= nY - rangeY
                                and sZ <= nZ + rangeZ
                                and sZ >= nZ - rangeZ
                            ):
                                similarFaces.append(f)
                                if (
                                    f in faces
                                ):  # If the face is in the loop que, remove it, as has already been evaluated.
                                    faces.remove(f)

        return similarFaces

    @staticmethod
    def transferNormals(source, target):
        """Transfer normal information from one object to another.

        Parameters:
                source (str/obj/list): The transform node to copy normals from.
                target (str/obj/list): The transform node(s) to copy normals to.
        """
        pm.undoInfo(openChunk=1)
        s, *other = pm.ls(source)
        # store source transforms
        sourcePos = pm.xform(s, q=1, t=1, ws=1)
        sourceRot = pm.xform(s, q=1, ro=1, ws=1)
        sourceScale = pm.xform(s, q=1, s=1, ws=1)

        for t in pm.ls(target):
            # store target transforms
            targetPos = pm.xform(t, q=1, t=1, ws=1)
            targetRot = pm.xform(t, q=1, ro=1, ws=1)
            targetScale = pm.xform(t, q=1, s=1, ws=1)

            # move target to source position
            pm.xform(t, t=sourcePos, ws=1)
            pm.xform(t, ro=sourceRot, ws=1)
            pm.xform(t, s=sourceScale, ws=1)

            # copy normals
            pm.polyNormalPerVertex(t, ufn=0)
            pm.transferAttributes(s, t, pos=0, nml=1, uvs=0, col=0, spa=0, sm=3, clb=1)
            pm.delete(t, ch=1)

            # restore t position
            pm.xform(t, t=targetPos, ws=1)
            pm.xform(t, ro=targetRot, ws=1)
            pm.xform(t, s=targetScale, ws=1)
        pm.undoInfo(closeChunk=1)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated:


# @staticmethod
#   def getNormalVector(obj):
#       '''Get the normal vectors from the given poly object.

#       Parameters:
#           obj (str/obj/list): A polygon mesh or component(s).

#       Returns:
#           dict - {int:[float, float, float]} face id & vector xyz.
#       '''
#       obj = pm.ls(obj)
#       type_ = pm.objectType(obj)

#       if type_=='mesh': #get face normals
#           normals = pm.polyInfo(obj, faceNormals=1)

#       elif type_=='transform': #get all normals for the given obj
#           numFaces = pm.polyEvaluate(obj, face=1) #returns number of faces as an integer
#           normals=[]
#           name = obj.name()
#           for n in range(0, numFaces): #for (number of faces):
#               array = pm.polyInfo('{0}[{1}]'.format(name, n) , faceNormals=1) #get normal info from the rest of the object's faces
#               string = ' '.join(array)
#               n.append(str(string))

#       else: #get face normals from the user component selection.
#           normals = pm.polyInfo(faceNormals=1) #returns the face normals of selected faces

#       regex = "[A-Z]*_[A-Z]* *[0-9]*: "

#       dict_={}
#       for n in normals:
#           l = list(s.replace(regex,'') for s in n.split() if s) #['FACE_NORMAL', '150:', '0.935741', '0.110496', '0.334931\n']

#           key = int(l[1].strip(':')) #int face number as key ie. 150
#           value = list(float(i) for i in l[-3:])  #vector list as value. ie. [[0.935741, 0.110496, 0.334931]]
#           dict_[key] = value

#       return dict_
