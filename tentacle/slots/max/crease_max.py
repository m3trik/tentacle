# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.crease import Crease


class Crease_max(Crease, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.creaseValue = 10

        cmb = self.sb.crease.draggableHeader.ctxMenu.cmb000
        items = ["Crease Modifier"]
        cmb.addItems_(items, "Crease Modifiers:")

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.crease.draggableHeader.ctxMenu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "Crease Modifier":
                # check if modifier exists
                for obj in rt.selection:
                    mod = obj.modifiers[rt.Crease]
                    if mod == None:  # if not create
                        mod = rt.crease()
                        rt.addModifier(obj, mod)
                        # set modifier attributes
                        # mod.enabled = state

            rt.redrawViews()
            cmb.setCurrentIndex(0)

    def tb000(self, state=None):
        """Crease"""
        tb = self.sb.crease.tb000

        creaseAmount = int(tb.ctxMenu.s003.value())
        normalAngle = int(tb.ctxMenu.s004.value())

        # if tb.ctxMenu.chk011.isChecked(): #crease: Auto
        # 	angleLow = int(tb.ctxMenu.s005.value())
        # 	angleHigh = int(tb.ctxMenu.s006.value())

        # 	mel.eval("PolySelectConvert 2;") #convert selection to edges
        # 	contraint = pm.polySelectConstraint( mode=3, type=0x8000, angle=True, anglebound=(angleLow, angleHigh) ) # to get edges with angle between two degrees. mode=3 (All and Next) type=0x8000 (edge).

        creaseAmount = creaseAmount * 0.1  # convert to max 0-1 range

        for obj in rt.selection:
            if rt.classOf(obj) == "Editable_Poly":
                if tb.ctxMenu.chk011.isChecked():  # crease: Auto
                    minAngle = int(tb.ctxMenu.s005.value())
                    maxAngle = int(tb.ctxMenu.s006.value())

                    edgelist = self.getEdgesByAngle(minAngle, maxAngle)
                    rt.polyOp.setEdgeSelection(obj, edgelist)

                if tb.ctxMenu.chk004.isChecked():  # crease vertex point
                    obj.EditablePoly.setVertexData(1, creaseAmount)
                else:  # crease edge
                    obj.EditablePoly.setEdgeData(1, creaseAmount)

                if tb.ctxMenu.chk005.isChecked():  # adjust normal angle
                    edges = rt.polyop.getEdgeSelection(obj)
                    for edge in edges:
                        edgeVerts = rt.polyop.getEdgeVerts(obj, edge)
                        normal = rt.averageSelVertNormal(obj)
                        for vertex in edgeVerts:
                            rt.setNormal(obj, vertex, normal)
            else:
                print("Error: object type " + rt.classOf(obj) + " is not supported.")

    def b002(self):
        """Transfer Crease Edges"""
        # an updated version of this is in the maya python projects folder
        # the use of separate buttons for donor and target mesh are obsolete
        # add pm.polySoftEdge (angle=0, constructionHistory=0); #harden edge, when applying crease

        creaseSet = str(self.sb.crease.b000.text())
        newObject = str(self.sb.crease.b001.text())

        sets = pm.sets(creaseSet, query=1)

        setArray = []
        for set_ in sets:
            name = str(set_)
            setArray.append(name)
        print(setArray)

        pm.undoInfo(openChunk=1)
        for set_ in setArray:
            oldObject = "".join(
                set_.partition(".")[:1]
            )  # ex. pSphereShape1 from pSphereShape1.e[260:299]
            pm.select(set_, replace=1)
            value = pm.polyCrease(query=1, value=1)[0]
            name = set_.replace(oldObject, newObject)
            pm.select(name, replace=1)
            pm.polyCrease(value=value, vertexValue=value, createHistory=True)
            # print("crease:", name)
        pm.undoInfo(closeChunk=1)

        self.sb.toggle_widgets(
            setDisabled="b052", setUnChecked="b000"
        )  # ,self.sb.crease.b001])
        self.sb.crease.b000.setText("Crease Set")
        # self.sb.crease.b001.setText("Object")


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
