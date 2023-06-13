# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Display_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def b000(self):
        """Set Wireframe color"""
        pm.mel.objectColorPalette()

    def b001(self):
        """Toggle Visibility"""
        pm.mel.ToggleVisibilityAndKeepSelection()

    def b002(self):
        """Hide Selected"""
        selection = pm.ls(sl=True)
        pm.hide(selection)  # pm.mel.HideSelectedObjects()

    def b003(self):
        """Show Selected"""
        selection = pm.ls(sl=True)
        pm.showHidden(selection)  # pm.mel.ShowSelectedObjects()

    def b004(self):
        """Show Geometry"""
        pm.mel.hideShow(geometry=1, show=1)

    def b005(self):
        """Xray Selected"""
        # Get all dag shapes in the current selection
        selection = pm.ls(sl=True, dag=True, s=True)

        for obj in selection:
            # Query the xray state and toggle it
            x_state = obj.getAttr("displaySurface")
            obj.setAttr("displaySurface", not x_state)

    def b006(self):
        """Un-Xray All"""
        # Get all visible, non-intermediate surface shapes in the scene
        scene_objects = pm.ls(vis=True, fl=True, dag=True, ni=True, typ="surfaceShape")

        for obj in scene_objects:
            # If the object's xray state is on, turn it off
            x_state = obj.getAttr("displaySurface")
            if x_state:
                obj.setAttr("displaySurface", 0)

    def b007(self):
        """Xray Other"""
        # Get all visible, non-intermediate surface shapes in the scene
        scene_objects = pm.ls(vis=True, fl=True, dag=True, ni=True, typ="surfaceShape")
        # Get all shapes in the current selection
        selected_objects = pm.ls(sl=True, dagObjects=True, shapes=True)

        for obj in scene_objects:
            # If the object is not in the selection, toggle its xray state
            if obj not in selected_objects:
                x_state = obj.getAttr("displaySurface")
                obj.setAttr("displaySurface", not x_state)

    def b008(self):
        """Filter Objects"""
        pm.mel.bt_filterActionWindow()

    def b009(self):
        """Toggle Material Override"""
        currentPanel = mtk.get_panel(withFocus=True)
        state = pm.modelEditor(currentPanel, q=True, useDefaultMaterial=1)
        pm.modelEditor(currentPanel, edit=1, useDefaultMaterial=not state)
        mtk.viewport_message("Default Material Override: <hl>{}</hl>.".format(state))

    def b010(self):
        """Toggle Explode Selected"""
        mtk.ExplodedView.toggle_explode()

    def b011(self):
        """Toggle Component Id Display"""
        index = ptk.cycle([0, 1, 2, 3, 4], "componentID")

        visible = pm.polyOptions(q=True, displayItemNumbers=1)
        if not visible:
            self.sb.message_box("Nothing selected.")
            return

        dinArray = [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]

        if index == 4:
            i = 0
            for _ in range(4):
                if visible[i] is True:
                    pm.polyOptions(
                        relative=1, displayItemNumbers=dinArray[i], activeObjects=1
                    )
                i += 1

        elif visible[index] is not True and index != 4:
            pm.polyOptions(
                relative=1, displayItemNumbers=dinArray[index], activeObjects=1
            )

            i = 0
            for _ in range(4):
                if visible[i] is True and i != index:
                    pm.polyOptions(
                        relative=1, displayItemNumbers=dinArray[i], activeObjects=1
                    )
                i += 1

        if index == 0:
            mtk.viewport_message("[1,0,0,0] <hl>vertIDs</hl>.")
        elif index == 1:
            mtk.viewport_message("[0,1,0,0] <hl>edgeIDs</hl>.")
        elif index == 2:
            mtk.viewport_message("[0,0,1,0] <hl>faceIDs</hl>.")
        elif index == 3:
            mtk.viewport_message("[0,0,0,1] <hl>compIDs(UV)</hl>.")
        elif index == 4:
            mtk.viewport_message("component ID <hl>Off</hl>.")

    def b012(self):
        """Wireframe Non Active (Wireframe All But The Selected Item)"""
        current_panel = mtk.get_panel(withFocus=1)
        state = pm.modelEditor(current_panel, q=True, activeOnly=1)
        pm.modelEditor(current_panel, edit=1, activeOnly=not state)

    def b013(self):
        """Explode View GUI"""
        mtk.exploded_view.launch_gui(move_to_cursor=True, frameless_window=True)

    def b021(self):
        """Template Selected"""
        pm.toggle(template=1)  # pm.toggle(template=1, q=True)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
