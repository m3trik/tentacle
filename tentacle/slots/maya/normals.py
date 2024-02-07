# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Normals(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QSpinBox",
            setPrefix="Display Size: ",
            setObjectName="s001",
            set_limits=[1, 100],
            setValue=1,
            setToolTip="Normal display size.",
        )

    def tb000(self, widget):
        """Display Face Normals"""
        size = widget.menu.s001.value()
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

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QSpinBox",
            setPrefix="Angle Threshold: ",
            setObjectName="s002",
            set_limits=[0, 180],
            setValue=90,
            setToolTip="The threshold of the normal angle in degrees to determine hardness.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Upper Hardness: ",
            setObjectName="s003",
            set_limits=[-1, 180],
            setValue=0,
            setToolTip="The hardness to apply to edges with a normal angle greater than or equal to the threshold.\n0, Edges will appear hard.\n180, Edges will appear soft.\n-1, Will Disable.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Lower Hardness: ",
            setObjectName="s004",
            set_limits=[-1, 180],
            setValue=180,
            setToolTip="The hardness to apply to edges with a normal angle less than the threshold.\n0, Edges will appear hard.\n180, Edges will appear soft.\n-1, Will Disable.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Soft Edge Display",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Turn on soft edge display for the object.",
        )

    def tb001(self, widget):
        """Set Normals By Angle"""
        angle_threshold = widget.menu.s002.value()
        upper_hardness = widget.menu.s003.value()
        lower_hardness = widget.menu.s004.value()
        soft_edge_display = widget.menu.chk007.isChecked()

        # If value is -1, upper/lower hardess will be disabled.
        upper_hardness = upper_hardness if upper_hardness > -1 else None
        lower_hardness = lower_hardness if lower_hardness > -1 else None

        selection = pm.ls(sl=True)
        # Reset the normals before the operation with object selections.
        if pm.selectMode(query=True, object=True):
            pm.polySetToFaceNormal(selection)

        mtk.set_edge_hardness(
            selection, angle_threshold, upper_hardness, lower_hardness
        )

        objects = pm.ls(selection, objectsOnly=True)
        pm.polyOptions(objects, se=soft_edge_display)

    def tb003_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Lock",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Toggle Lock/Unlock.",
        )
        widget.menu.chk002.toggled.connect(
            lambda state, w=widget.menu.chk002: w.setText("Lock")
            if state
            else w.setText("Unlock")
        )

    def tb003(self, widget):
        """Lock/Unlock Vertex Normals"""
        state = widget.menu.chk002.isChecked()
        selection = pm.ls(sl=True)

        if not selection:
            self.sb.message_box("Operation requires at least one selected object.")
            return

        vertices = pm.polyListComponentConversion(
            selection, fromFace=True, toVertex=True
        )

        if not state:
            pm.polyNormalPerVertex(vertices, unFreezeNormal=True)
            mtk.viewport_message("Normals <hl>UnLocked</hl>.")
        else:
            pm.polyNormalPerVertex(vertices, freezeNormal=True)
            mtk.viewport_message("Normals <hl>Locked</hl>.")

    def tb004_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="By UV Shell",
            setObjectName="chk003",
            setToolTip="Average the normals of each object's faces per UV shell.",
        )

    def tb004(self, widget):
        """Average Normals"""
        by_uv_shell = widget.menu.chk003.isChecked()

        objects = pm.ls(sl=True)
        mtk.average_normals(objects, by_uv_shell=by_uv_shell)

    def b000(self):
        """Soften Edge Normals"""
        selection = pm.ls(sl=True, fl=True)
        if selection:
            pm.polySoftEdge(selection, angle=180)  # Use maximum angle to soften
            pm.select(selection)  # Re-select the original selection

    def b001(self):
        """Harden all selected edges."""
        selection = pm.ls(sl=True, fl=True)
        if selection:
            pm.polySoftEdge(selection, angle=0)  # Use minimum angle to harden
            pm.select(selection)  # Re-select the original selection

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
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
