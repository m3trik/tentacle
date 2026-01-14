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
            result = pm.displaySurface(item, xRay=True, query=True)
            if result is not None:
                pm.displaySurface(item, xRay=(not result[0]))

    def b006(self):
        """Un-Xray All"""
        # Get all mesh transforms and disable xray on each
        meshes = pm.ls(type="mesh")
        for mesh in meshes:
            transform = mesh.getParent()
            if transform:
                pm.displaySurface(transform, xRay=False)

    def b007(self):
        """Xray Other"""
        # Get all mesh transforms
        meshes = pm.ls(type="mesh")
        all_mesh_transforms = set(
            mesh.getParent() for mesh in meshes if mesh.getParent()
        )
        # Get the currently selected objects
        selected_objects = set(pm.ls(sl=True, transforms=True))
        # Filter out the selected objects
        non_selected_objects = all_mesh_transforms - selected_objects

        for item in non_selected_objects:
            result = pm.displaySurface(item, xRay=True, query=True)
            if result is not None:
                pm.displaySurface(item, xRay=(not result[0]))

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
