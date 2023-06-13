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
        widget.option_menu.add(
            "QCheckBox",
            setText="By UV Shell",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Average the normals of each object's faces per UV shell.",
        )

    def tb000(self, widget):
        """Display Face Normals"""
        size = float(widget.option_menu.s001.value())
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

    def tb001(self, widget):
        """Harden Edge Normals"""
        query_angle = widget.option_menu.s002.value()
        smoothing_angle = widget.option_menu.s003.value()
        harden_creased = widget.option_menu.chk005.isChecked()
        harden_uv_borders = widget.option_menu.chk006.isChecked()
        soften_other = widget.option_menu.chk004.isChecked()
        soft_edge_display = widget.option_menu.chk007.isChecked()

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
                uv_border_edges = pm.ls(mtk.get_uv_shell_border_edges(selected_edges))
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

    def tb002(self, widget):
        """Set Normals By Angle"""
        normalAngle = widget.option_menu.s000.value()

        objects = pm.ls(sl=True, objectsOnly=1, flatten=1)
        for obj in objects:
            sel = pm.ls(obj, sl=1)
            pm.polySetToFaceNormal(sel, setUserNormal=1)  # reset to face
            polySoftEdge = pm.polySoftEdge(
                sel, angle=normalAngle
            )  # smooth if angle is lower than specified amount. default:60
            if len(objects) == 1:
                return polySoftEdge

    def tb003(self, widget):
        """Lock/Unlock Vertex Normals"""
        all_ = widget.option_menu.chk001.isChecked()
        state = (
            widget.option_menu.chk002.isChecked()
        )  # pm.polyNormalPerVertex(vertex, q=True, freezeNormal=1)
        selection = pm.ls(sl=True, objectsOnly=1)
        maskObject = pm.selectMode(q=True, object=1)
        maskVertex = pm.selectType(q=True, vertex=1)

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

    def tb004(self, widget):
        """Average Normals"""
        by_uv_shell = widget.option_menu.chk003.isChecked()

        objects = pm.ls(sl=True, objectsOnly=1, flatten=1)
        mtk.average_normals(objects, by_uv_shell=by_uv_shell)

    def b001(self):
        """Soften Edge Normals"""
        sel = pm.ls(sl=1)
        if sel:
            pm.polySoftEdge(sel, angle=180, constructionHistory=0)

    def b002(self):
        """Transfer Normals"""
        source, *target = pm.ls(sl=1)
        mtk.transfer_normals(source, target)

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
            # normalMode 3: reverse and cut a new shell on selected face(s).
            # normalMode 4: reverse and propagate; Reverse the normal(s) and propagate this direction to all other faces in the shell.
            pm.polyNormal(sel, normalMode=3, userNormalMode=1)


# --------------------------------------------------------------------------------------------

# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated:


# @staticmethod
#   def get_normal_vector(obj):
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
