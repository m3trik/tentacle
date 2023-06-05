# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.display import Display


class Display_max(Display, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.display.draggableHeader.ctx_menu.cmb000
        items = [""]
        cmb.addItems_(items, "")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.display.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def b000(self, *args, **kwargs):
        """Set Wireframe color"""
        pm.mel.objectColorPalette()

    def b001(self, *args, **kwargs):
        """Toggle Visibility"""
        sel = [s for s in rt.getCurrentSelection()]

        for obj in sel:
            if obj.visibility == True:
                obj.visibility = False
            else:
                obj.visibility = True

    def b002(self, *args, **kwargs):
        """Hide Selected"""
        sel = [s for s in rt.getCurrentSelection()]

        for obj in sel:
            if not obj.isHiddenInVpt:
                obj.isHidden = True

    def b003(self, *args, **kwargs):
        """Show Selected"""
        sel = [s for s in rt.getCurrentSelection()]

        for obj in sel:
            if obj.isHiddenInVpt:
                obj.isHidden = False

    def b004(self, *args, **kwargs):
        """Show Geometry"""
        geometry = rt.geometry

        for obj in geometry:
            if obj.isHiddenInVpt:
                obj.isHidden = False

    def b005(self, *args, **kwargs):
        """Xray Selected"""
        sel = [s for s in rt.getCurrentSelection()]

        for s in sel:
            s.xray = True

    def b006(self, *args, **kwargs):
        """Un-Xray All"""
        geometry = [g for g in rt.geometry]

        for g in geometry:
            g.xray = False

    def b007(self, *args, **kwargs):
        """Xray Other"""
        sel = [s for s in rt.getCurrentSelection()]
        geometry = [g for g in rt.geometry]

        for g in geometry:
            if g not in sel:
                g.xray = True

    def b008(self, *args, **kwargs):
        """Filter Objects"""
        mel.eval("bt_filterActionWindow;")

    def b009(self, *args, **kwargs):
        """Override Material"""
        if self.sb.display.chk000.isChecked():  # override with UV checker material
            self.toggleMaterialOverride(checker=1)
        else:
            self.toggleMaterialOverride()

    def b010(self, *args, **kwargs):
        """"""
        pass

    def b011(self, *args, **kwargs):
        """Toggle Component ID Display"""
        index = ptk.cycle([0, 1, 2, 3, 4], "componentID")

        visible = pm.polyOptions(query=1, displayItemNumbers=1)
        dinArray = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

        if index == 4:
            i = 0
            for _ in range(4):
                if visible[i] == True:
                    pm.polyOptions(
                        relative=1, displayItemNumbers=dinArray[i], activeObjects=1
                    )
                i += 1

        if visible[index] != True and index != 4:
            pm.polyOptions(
                relative=1, displayItemNumbers=dinArray[index], activeObjects=1
            )

            i = 0
            for _ in range(4):
                if visible[i] == True and i != index:
                    pm.polyOptions(
                        relative=1, displayItemNumbers=dinArray[i], activeObjects=1
                    )
                i += 1

        if index == 0:
            self.sb.message_box("<hl>Vertex IDs</hl>.")  # [1,0,0,0]
            return
        elif index == 1:
            self.sb.message_box("<hl>Edge IDs</hl>.")  # [0,1,0,0]
            return
        elif index == 2:
            self.sb.message_box("<hl>Face IDs</hl>.")  # [0,0,1,0]
            return
        elif index == 3:
            self.sb.message_box("<hl>Component IDs (UV)</hl>.")  # [0,0,0,1]
            return
        elif index == 4:
            self.sb.message_box("Component ID <hl>Off</hl>.")
            return

    def b012(self, *args, **kwargs):
        """Wireframe Non Active (Wireframe All But The Selected Item)"""
        viewport = rt.viewport.activeViewport

        state = ptk.cycle([0, 1], "wireframeInactive")

        if state:
            if not rt.viewport.isWire():
                self.maxUiSetChecked("415", 62, 163, True)  # set viewport to wireframe
            self.maxUiSetChecked(
                "40212", 62, 130, True
            )  # Shade selected objects Checked
        else:
            self.maxUiSetChecked(
                "40212", 62, 130, False
            )  # Shade selected objects unchecked

    def b013(self, *args, **kwargs):
        """Viewport Configuration"""
        maxEval('actionMan.executeAction 0 "40023"')

    def b021(self, *args, **kwargs):
        """Template Selected"""
        sel = [s for s in rt.getCurrentSelection()]

        for obj in sel:
            if obj.isFrozen == True:
                obj.isFrozen = False
            else:
                obj.isFrozen = True

    def b024(self, *args, **kwargs):
        """Polygon Display Options"""
        mel.eval("CustomPolygonDisplayOptions")
        # mel.eval("polysDisplaySetup 1;")


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
