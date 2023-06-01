# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.subdivision import Subdivision


class Subdivision_max(Subdivision, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set 3ds Max specific naming
        self.sb.subdivision.gb000.setTitle("TurboSmooth")
        self.sb.subdivision.s000.setPrefix("Iterations:  ")
        self.sb.subdivision.s001.setPrefix("RenderIters: ")
        self.sb.subdivision.s000.setValue(0)
        self.sb.subdivision.s001.setValue(0)

        ctx = self.sb.subdivision.draggableHeader.ctx_menu
        if not ctx.containsMenuItems:
            ctx.add(
                self.sb.ComboBox,
                setObjectName="cmb000",
                setToolTip="Max Subdivision Editiors.",
            )
            # ctx.add(self.sb.ComboBox, setObjectName='cmb001', setToolTip='Smooth Proxy.')
            # ctx.add(self.sb.ComboBox, setObjectName='cmb002', setToolTip='Maya Subdivision Operations.')

        cmb = self.sb.subdivision.draggableHeader.ctx_menu.cmb000
        items = [
            "TurboSmooth",
            "TurboSmooth Pro",
            "OpenSubDiv",
            "Subdivide",
            "Subdivide (WSM)",
            "MeshSmooth",
            "Optimize",
            "Pro Optimizer",
            "Add Divisions",
        ]
        cmb.addItems_(items, "3dsMax Subdivision Modifiers")

        # cmb = self.sb.subdivision.draggableHeader.ctx_menu.cmb001
        # items = ['Create Subdiv Proxy','Remove Subdiv Proxy Mirror','Crease Tool','Toggle Subdiv Proxy Display', 'Both Proxy and Subdiv Display']
        # cmb.addItems_(items, 'Smooth Proxy')

        # cmb = self.sb.subdivision.draggableHeader.ctx_menu.cmb002
        # items = ['Reduce Polygons','Add Divisions','Smooth']
        # cmb.addItems_(items, 'Maya Subdivision Operations')

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.subdivision.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "TurboSmooth":
                mod = rt.TurboSmooth()
                mod.iterations = 0
                mod.renderIterations = 1
                mod.useRenderIterations = True
                mod.explicitNormals = True
                mod.sepByMats = True
                rt.modpanel.addModToSelection(mod)

            if text == "TurboSmooth Pro":
                mod = TurboSmooth_Pro()
                mod.iterations = 0
                mod.renderIterations = 1
                mod.useRenderIterations = True
                mod.explicitNormals = True
                mod.visualizeCreases = True
                mod.smmoothCorners = False
                mod.creaseSmoothingGroups = True
                mod.creaseMaterials = True
                rt.modpanel.addModToSelection(mod)

            if text == "OpenSubDiv":
                mod = OpenSubdiv()
                mod.iterations = 0
                mod.renderIterations = 1
                mod.useRenderIterations = True
                rt.modpanel.addModToSelection(mod)

            if text == "Subdivide":
                mod = subdivide()
                mod.size = 0.075
                rt.modpanel.addModToSelection(mod)

            if text == "Subdivide (WSM)":
                mod = subdivideSpacewarpModifier()
                mod.size = 40
                rt.modpanel.addModToSelection(mod)

            if text == "MeshSmooth":
                mod = meshsmooth()
                mod.iterations = 0
                mod.renderIterations = 1
                mod.useRenderIterations = True
                mod.useRenderSmoothness = True
                rt.modpanel.addModToSelection(mod)

            if text == "Optimize":
                mod = optimize()
                rt.modpanel.addModToSelection(mod)

            if text == "Pro optimizer":
                mod = ProOptimizer()
                rt.modpanel.addModToSelection(mod)

            if text == "Add Divisions":
                maxEval(
                    """
				Try (
					local A = modPanel.getCurrentObject()
					A.popupDialog #Tessellate
				)
				Catch ()
				"""
                )
            cmb.setCurrentIndex(0)

    def s000(self, value=None):
        """Division Level"""
        value = self.sb.subdivision.s000.getValue()

        geometry = rt.selection

        for obj in geometry:
            try:
                obj.modifiers["TurboSmooth"].iterations = value
            except:
                pass

    def s001(self, value=None):
        """Tesselation Level"""
        value = self.sb.subdivision.s001.getValue()

        geometry = rt.selection

        for obj in geometry:
            try:
                obj.modifiers["TurboSmooth"].renderIterations = value
            except:
                pass

    def b005(self):
        """Reduce"""
        mel.eval("ReducePolygon;")

    def b008(self):
        """Add Divisions - Subdivide Mesh"""
        maxEval('macros.run "Modifiers" "Tessellate"')

    def b009(self):
        """Smooth"""
        maxEval('macros.run "Modifiers" "Smooth"')

    def b010(self):
        """"""
        pass

    def b011(self):
        """Convert Smooth Preview"""
        # convert smooth mesh preview to polygons
        geometry = rt.selection

        if not len(geometry):
            geometry = rt.geometry

        for obj in geometry:
            try:
                renderIters = obj.modifiers["TurboSmooth"].renderIterations
                obj.modifiers["TurboSmooth"].iterations = renderIters

                modifiers = [mod.name for mod in obj.modifiers]
                if modifiers:
                    index = modifiers.index("TurboSmooth") + 1
                rt.maxOps.CollapseNodeTo(obj, index, False)
            except:
                pass


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
