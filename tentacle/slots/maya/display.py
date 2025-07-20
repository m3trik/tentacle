# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class DisplaySlots(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.display
        self.submenu = self.sb.loaded_ui.display_submenu

    def header_init(self, widget):
        """ """
        widget.menu.add(
            "QPushButton",
            setText="Exploded View",
            setObjectName="b013",
            setToolTip="Open the exploded view window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Color Manager",
            setObjectName="b014",
            setToolTip="Open the color manager window.",
        )

    def b000(self):
        """Set Wireframe color"""
        pm.mel.objectColorPalette()

    def b001(self):
        """Wireframe Selected"""
        mtk.Macros.m_wireframe_toggle()

    def b002(self):
        """Hide Selected"""
        selection = pm.ls(sl=True)
        pm.hide(selection)

    def b003(self):
        """Show Selected"""
        selection = pm.ls(sl=True)
        pm.showHidden(selection)

    def b004(self):
        """Show Geometry"""
        mtk.set_visibility("mesh", True)

    def b005(self):
        """Xray Selected"""
        objects = pm.ls(sl=True, transforms=True)
        for item in objects:
            pm.displaySurface(
                item, xRay=(not pm.displaySurface(item, xRay=True, query=True)[0])
            )

    def b006(self):
        """Un-Xray All"""
        # Get all model panels
        model_panels = pm.getPanel(type="modelPanel")

        for panel in model_panels:
            # Set the X-ray mode to False
            pm.modelEditor(panel, edit=True, xray=False)

    def b007(self):
        """Xray Other"""
        # Get all transform nodes in the scene
        all_objects = pm.ls(type="transform")
        # Get the currently selected objects
        selected_objects = pm.ls(sl=True, transforms=True)
        # Filter out the selected objects
        non_selected_objects = [
            obj for obj in all_objects if obj not in selected_objects
        ]

        for item in non_selected_objects:
            pm.displaySurface(
                item, xRay=(not pm.displaySurface(item, xRay=True, query=True)[0])
            )

    def b009(self):
        """Toggle Material Override"""
        mtk.Macros.m_material_override()

    def b011(self):
        """Toggle Component ID Display"""
        mtk.Macros.m_component_id_display()

    def b012(self):
        """Wireframe Non Active (Wireframe All But The Selected Item)"""
        current_panel = mtk.get_panel(withFocus=1)
        state = pm.modelEditor(current_panel, q=True, activeOnly=1)
        pm.modelEditor(current_panel, edit=1, activeOnly=not state)

    def b013(self):
        """Explode View GUI"""
        ui = mtk.UiManager.instance(self.sb).get("exploded_view")
        self.sb.parent().show(ui)

    def b014(self):
        """Color Manager GUI"""
        ui = mtk.UiManager.instance(self.sb).get("color_manager")
        self.sb.parent().show(ui)

    def b021(self):
        """Template Selected"""
        pm.toggle(template=1)  # pm.toggle(template=1, q=True)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
