# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Crease_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.creaseValue = 10

    def tb000_init(self, widget):
        """ """
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Crease Amount: ",
            setObjectName="s003",
            set_limits=(0, 10),
            setValue=10,
            setToolTip='Crease amount 0-10. Overriden if "max" checked.',
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Toggle Max",
            setObjectName="chk003",
            setToolTip="Toggle crease amount from it's current value to the maximum amount.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Un-Crease",
            setObjectName="chk002",
            setToolTip="Un-crease selected components or If in object mode, uncrease all.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Perform Normal Edge Hardness",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Toggle perform normal edge hardness.",
        )
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Hardness Angle: ",
            setObjectName="s004",
            set_limits=(0, 180),
            setValue=30,
            setToolTip="Normal edge hardness 0-180.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Crease Vertex Points",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="Crease vertex points.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Auto Crease",
            setObjectName="chk011",
            setToolTip="Auto crease selected object(s) within the set angle tolerance.",
        )
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Auto Crease: Low: ",
            setObjectName="s005",
            set_limits=(0, 180),
            setValue=85,
            setToolTip="Auto crease: low angle constraint.",
        )
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Auto Crease: high: ",
            setObjectName="s006",
            set_limits=(0, 180),
            setValue=95,
            setToolTip="Auto crease: max angle constraint.",
        )
        self.sb.toggle_widgets(widget.option_menu, setDisabled="s005,s006")

    def s003(self, value, widget):
        """Crease Amount
        Tracks the standard crease amount while toggles such as un-crease, and crease max temporarily change the spinbox value.
        """
        if not self.sb.crease.tb000.option_menu.chk002.isChecked():  # un-crease
            if not self.sb.crease.tb000.option_menu.chk003.isChecked():  # toggle max
                self.creaseValue = value
                text = self.sb.crease.tb000.text().split()[0]
                self.sb.crease.tb000.setText("{} {}".format(text, self.creaseValue))

    def chk002(self, state, widget):
        """Un-Crease"""
        if state:
            self.sb.crease.tb000.option_menu.s003.setValue(0)  # crease value
            self.sb.crease.tb000.option_menu.s004.setValue(180)  # normal angle
            self.sb.toggle_widgets(
                widget.option_menu, setChecked="chk002", setUnChecked="chk003"
            )
            self.sb.crease.tb000.option_menu.s003.setDisabled(True)
            text = "Un-Crease 0"
        else:
            self.sb.crease.tb000.option_menu.s003.setValue(
                self.creaseValue
            )  # crease value
            self.sb.crease.tb000.option_menu.s004.setValue(30)  # normal angle
            self.sb.crease.tb000.option_menu.s003.setEnabled(True)
            text = "{} {}".format("Crease", self.creaseValue)

        self.sb.crease.tb000.setText(text)

    def chk003(self, state, widget):
        """Crease: Max"""
        if state:
            self.sb.crease.tb000.option_menu.s003.setValue(10)  # crease value
            self.sb.crease.tb000.option_menu.s004.setValue(30)  # normal angle
            self.sb.toggle_widgets(
                widget.option_menu, setChecked="chk003", setUnChecked="chk002"
            )
            self.sb.crease.tb000.option_menu.s003.setDisabled(True)
            text = "Un-Crease 0"
        else:
            self.sb.crease.tb000.option_menu.s003.setValue(
                self.creaseValue
            )  # crease value
            self.sb.crease.tb000.option_menu.s004.setValue(60)  # normal angle
            self.sb.crease.tb000.option_menu.s003.setEnabled(True)
            text = "{} {}".format("Crease", self.creaseValue)

        self.sb.crease.tb000.setText(text)

    def chk011(self, state, widget):
        """Crease: Auto"""
        if state:
            self.sb.toggle_widgets(widget.option_menu, setEnabled="s005,s006")
        else:
            self.sb.toggle_widgets(widget.option_menu, setDisabled="s005,s006")

    def tb000(self, widget):
        """Crease"""
        creaseAmount = float(widget.option_menu.s003.value())
        normalAngle = int(widget.option_menu.s004.value())

        if widget.option_menu.chk011.isChecked():  # crease: Auto
            angleLow = int(widget.option_menu.s005.value())
            angleHigh = int(widget.option_menu.s006.value())

            pm.mel.eval("PolySelectConvert 2;")  # convert selection to edges
            # to get edges with angle between two degrees. mode=3 (All and Next) type=0x8000 (edge).
            constraint = pm.polySelectConstraint(
                mode=3, type=0x8000, angle=True, anglebound=(angleLow, angleHigh)
            )

        operation = 0  # Crease selected components
        pm.polySoftEdge(angle=0, constructionHistory=0)  # Harden edge normal
        if widget.option_menu.chk002.isChecked():
            objectMode = pm.selectMode(query=True, object=True)
            if objectMode:  # if in object mode,
                operation = 2  # 2-Remove all crease values from mesh
            else:
                operation = 1  # 1-Remove crease from sel components
                pm.polySoftEdge(angle=180, constructionHistory=0)  # soften edge normal

        if widget.option_menu.chk004.isChecked():  # crease vertex point
            pm.polyCrease(
                value=creaseAmount,
                vertexValue=creaseAmount,
                createHistory=True,
                operation=operation,
            )
        else:
            pm.polyCrease(
                value=creaseAmount, createHistory=True, operation=operation
            )  # PolyCreaseTool;

        if widget.option_menu.chk005.isChecked():  # adjust normal angle
            pm.polySoftEdge(angle=normalAngle)

        if widget.option_menu.chk011.isChecked():  # crease: Auto
            pm.polySelectConstraint(angle=False)  # turn off angle constraint

    def b000(self, widget):
        """Crease Set Transfer: Transform Node"""
        if self.sb.crease.b001.isChecked():
            newObject = str(pm.ls(sl=True))  # ex. [nt.Transform(u'pSphere1')]

            index1 = newObject.find("u")
            index2 = newObject.find(")")
            newObject = newObject[index1 + 1 : index2].strip("'")  # ex. pSphere1

            if newObject != "[":
                self.sb.crease.b001.setText(newObject)
            else:
                self.sb.crease.b001.setText("must select obj first")
                self.sb.toggle_widgets(widget.ui, setUnChecked="b001")
            if self.sb.crease.b000.isChecked():
                self.sb.toggle_widgets(widget.ui, setEnabled="b052")
        else:
            self.sb.crease.b001.setText("Object")

    def b001(self, widget):
        """Crease Set Transfer: Crease Set"""
        if self.sb.crease.b000.isChecked():
            creaseSet = str(pm.ls(sl=True))  # ex. [nt.CreaseSet(u'creaseSet1')]

            index1 = creaseSet.find("u")
            index2 = creaseSet.find(")")
            creaseSet = creaseSet[index1 + 1 : index2].strip("'")  # ex. creaseSet1

            if creaseSet != "[":
                self.sb.crease.b000.setText(creaseSet)
            else:
                self.sb.crease.b000.setText("must select set first")
                self.sb.toggle_widgets(widget.ui, setUnChecked="b000")
            if self.sb.crease.b001.isChecked():
                self.sb.toggle_widgets(widget.ui, setEnabled="b052")
        else:
            self.sb.crease.b000.setText("Crease Set")

    @mtk.undo
    def b002(self, widget):
        """Transfer Crease Edges"""
        # an updated version of this is in the maya python projects folder. transferCreaseSets.py
        # the use of separate buttons for donor and target mesh are deprecated.
        # add pm.polySoftEdge (angle=0, constructionHistory=0); #harden edge, when applying crease.

        creaseSet = str(self.sb.crease.b000.text())
        newObject = str(self.sb.crease.b001.text())

        sets = pm.sets(creaseSet, q=True)

        setArray = []
        for set_ in sets:
            name = str(set_)
            setArray.append(name)
        print(setArray)

        # pm.undoInfo (openChunk=1)
        for set_ in setArray:
            oldObject = "".join(
                set_.partition(".")[:1]
            )  # ex. pSphereShape1 from pSphereShape1.e[260:299]
            pm.select(set_, replace=1)
            value = pm.polyCrease(q=True, value=1)[0]
            name = set_.replace(oldObject, newObject)
            pm.select(name, replace=1)
            pm.polyCrease(value=value, vertexValue=value, createHistory=True)
            # print("crease:", name)
        # pm.undoInfo (closeChunk=1)

        self.sb.toggle_widgets(widget.ui, setDisabled="b052", setUnChecked="b000")
        self.sb.crease.b000.setText("Crease Set")
        # self.sb.crease.b001.setText("Object")

    def getCreasedEdges(self, edges):
        """Return any creased edges from a list of edges.

        Parameters:
                edges (str/obj/list): The edges to check crease state on.

        Returns:
                (list) edges.
        """
        creased_edges = [
            e for e in pm.ls(edges, flatten=1) if pm.polyCrease(e, q=1, value=1)[0] > 0
        ]

        return creased_edges


# --------------------------------------------------------------------------------------------

# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
# b008, b010, b011, b019, b024-27, b058, b059, b060
