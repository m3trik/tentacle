# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.display import Display


class Display_maya(Display, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.display.draggableHeader.ctxMenu.cmb000
        items = [""]
        cmb.addItems_(items, "")

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.display.draggableHeader.ctxMenu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def b000(self):
        """Set Wireframe color"""
        pm.mel.objectColorPalette()

    def b001(self):
        """Toggle Visibility"""
        pm.mel.ToggleVisibilityAndKeepSelection()

    def b002(self):
        """Hide Selected"""
        selection = pm.ls(selection=1)
        pm.hide(selection)  # pm.mel.HideSelectedObjects()

    def b003(self):
        """Show Selected"""
        selection = pm.ls(selection=1)
        pm.showHidden(selection)  # pm.mel.ShowSelectedObjects()

    def b004(self):
        """Show Geometry"""
        pm.mel.hideShow(geometry=1, show=1)

    def b005(self):
        """Xray Selected"""
        pm.mel.eval(
            """
		string $sel[] = `ls -sl -dag -s`;
		for ($object in $sel) 
			{
			int $xState[] = `displaySurface -query -xRay $object`;
			displaySurface -xRay ( !$xState[0] ) $object;
			}
		"""
        )

    def b006(self):
        """Un-Xray All"""
        pm.mel.eval(
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

    def b007(self):
        """Xray Other"""
        pm.mel.eval(
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

    def b008(self):
        """Filter Objects"""
        pm.mel.bt_filterActionWindow()

    def b009(self):
        """Toggle Material Override"""
        from maya.cmds import getPanel  # pymel getPanel is broken in ver: 2022.

        currentPanel = getPanel(withFocus=True)
        state = pm.modelEditor(currentPanel, query=1, useDefaultMaterial=1)
        pm.modelEditor(currentPanel, edit=1, useDefaultMaterial=not state)
        mtk.viewportMessage("Default Material Override: <hl>{}</hl>.".format(state))

    def b010(self):
        """Toggle Explode Selected"""
        mtk.ExplodedView.toggle_explode()

    def b011(self):
        """Toggle Component Id Display"""
        index = ptk.cycle([0, 1, 2, 3, 4], "componentID")

        visible = pm.polyOptions(query=1, displayItemNumbers=1)
        if not visible:
            self.sb.message_box("Nothing selected.")
            return

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
            mtk.viewportMessage("[1,0,0,0] <hl>vertIDs</hl>.")
        elif index == 1:
            mtk.viewportMessage("[0,1,0,0] <hl>edgeIDs</hl>.")
        elif index == 2:
            mtk.viewportMessage("[0,0,1,0] <hl>faceIDs</hl>.")
        elif index == 3:
            mtk.viewportMessage("[0,0,0,1] <hl>compIDs(UV)</hl>.")
        elif index == 4:
            mtk.viewportMessage("component ID <hl>Off</hl>.")

    def b012(self):
        """Wireframe Non Active (Wireframe All But The Selected Item)"""
        current_panel = pm.getPanel(withFocus=1)
        state = pm.modelEditor(current_panel, query=1, activeOnly=1)
        pm.modelEditor(current_panel, edit=1, activeOnly=not state)

    def b013(self):
        """Explode View GUI"""
        mtk.exploded_view.launch_gui(move_to_cursor=True, frameless_window=True)

    def b021(self):
        """Template Selected"""
        pm.toggle(template=1)  # pm.toggle(template=1, query=1)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
