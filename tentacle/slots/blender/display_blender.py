# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.display import Display


class Display_blender(Display, SlotsBlender):
    def __init__(self, *args, **kwargs):
        SlotsBlender.__init__(self, *args, **kwargs)
        Display.__init__(self, *args, **kwargs)

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
        mel.eval("ToggleVisibilityAndKeepSelection();")

    def b002(self, *args, **kwargs):
        """Hide Selected"""
        mel.eval("HideSelectedObjects;")

    def b003(self, *args, **kwargs):
        """Show Selected"""
        mel.eval("ShowSelectedObjects;")

    def b004(self, *args, **kwargs):
        """Show Geometry"""
        mel.eval("hideShow -geometry -show;")

    def b005(self, *args, **kwargs):
        """Xray Selected"""
        mel.eval(
            """
		string $sel[] = `ls -sl -dag -s`;
		for ($object in $sel) 
			{
			int $xState[] = `displaySurface -query -xRay $object`;
			displaySurface -xRay ( !$xState[0] ) $object;
			}
		"""
        )

    def b006(self, *args, **kwargs):
        """Un-Xray All"""
        mel.eval(
            """
		string $scene[] = `ls -visible -flatten -dag -noIntermediate -type surfaceShape`;
		for ($object in $scene)
			{
			int $state[] = `displaySurface -query -xRay $object`;
			if ($state[0] == 1)
				{
				displaySurface -xRay 0 $object;
				}
			}
		"""
        )

    def b007(self, *args, **kwargs):
        """Xray Other"""
        mel.eval(
            """
		//xray all except currently selected
		{
		string $scene[] = `ls -visible -flatten -dag -noIntermediate -type surfaceShape`;
		string $selection[] = `ls -selection -dagObjects -shapes`;
		for ($object in $scene)
			{
			if (!stringArrayContains ($object, $selection))
				{
				int $state[] = `displaySurface -query -xRay $object`;
				displaySurface -xRay ( !$state[0] ) $object;
				}
			}
		}
		"""
        )

    def b008(self, *args, **kwargs):
        """Filter Objects"""
        mel.eval("bt_filterActionWindow;")

    def b009(self, *args, **kwargs):
        """Toggle Material Override"""
        from maya.cmds import get_panel  # pymel get_panel is broken in ver: 2022.

        currentPanel = get_panel(withFocus=True)
        state = pm.modelEditor(currentPanel, query=1, useDefaultMaterial=1)
        pm.modelEditor(currentPanel, edit=1, useDefaultMaterial=not state)
        self.mtk.viewport_message(
            "Default Material Override: <hl>{}</hl>.".format(state)
        )

    def b011(self, *args, **kwargs):
        """Toggle Component Id Display"""
        index = ptk.cycle([0, 1, 2, 3, 4], "componentID")

        visible = pm.polyOptions(query=1, displayItemNumbers=1)
        if not visible:
            return "# Error: Nothing selected. #"
        dinArray = [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]

        if index == 4:
            i = 0
            for _ in range(4):
                if visible[i] == True:
                    pm.polyOptions(
                        relative=1, displayItemNumbers=dinArray[i], activeObjects=1
                    )
                i += 1

        elif visible[index] != True and index != 4:
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
            self.mtk.viewport_message("[1,0,0,0] <hl>vertIDs</hl>.")
        elif index == 1:
            self.mtk.viewport_message("[0,1,0,0] <hl>edgeIDs</hl>.")
        elif index == 2:
            self.mtk.viewport_message("[0,0,1,0] <hl>faceIDs</hl>.")
        elif index == 3:
            self.mtk.viewport_message("[0,0,0,1] <hl>compIDs(UV)</hl>.")
        elif index == 4:
            self.mtk.viewport_message("component ID <hl>Off</hl>.")

    def b012(self, *args, **kwargs):
        """Wireframe Non Active (Wireframe All But The Selected Item)"""
        current_panel = pm.get_panel(withFocus=1)
        state = pm.modelEditor(current_panel, query=1, activeOnly=1)
        pm.modelEditor(current_panel, edit=1, activeOnly=not state)

    def b021(self, *args, **kwargs):
        """Template Selected"""
        pm.toggle(template=1)  # pm.toggle(template=1, query=1)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
