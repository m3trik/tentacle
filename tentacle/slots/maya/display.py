# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


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
        mel.eval("objectColorPalette")

    def b001(self):
        """Wireframe Selected"""
        mtk.Macros.m_wireframe_toggle()

    def b002(self):
        """Hide Selected"""
        selection = cmds.ls(sl=True)
        if selection:
            cmds.hide(selection)

    def b003(self):
        """Show Selected"""
        selection = cmds.ls(sl=True)
        if selection:
            cmds.showHidden(selection)

    def b004(self):
        """Show Geometry"""
        mtk.set_visibility("mesh", True)

    def b005(self):
        """Xray Selected"""
        objects = cmds.ls(sl=True, transforms=True) or []
        for item in objects:
            result = cmds.displaySurface(item, xRay=True, query=True)
            if result is not None:
                cmds.displaySurface(item, xRay=(not result[0]))

    def b006(self):
        """Un-Xray All"""
        meshes = cmds.ls(type="mesh", long=True) or []
        for mesh in meshes:
            transform = mtk.NodeUtils.get_parent(mesh, full_path=True)
            if transform:
                cmds.displaySurface(transform, xRay=False)

    def b007(self):
        """Xray Other"""
        meshes = cmds.ls(type="mesh", long=True) or []
        all_mesh_transforms = set()
        for mesh in meshes:
            parent = mtk.NodeUtils.get_parent(mesh, full_path=True)
            if parent:
                all_mesh_transforms.add(parent)
        selected_objects = set(cmds.ls(sl=True, transforms=True, long=True) or [])
        non_selected_objects = all_mesh_transforms - selected_objects

        for item in non_selected_objects:
            result = cmds.displaySurface(item, xRay=True, query=True)
            if result is not None:
                cmds.displaySurface(item, xRay=(not result[0]))

    def b009(self):
        """Toggle Material Override"""
        mtk.Macros.m_material_override()

    def b011(self):
        """Toggle Component ID Display"""
        mtk.Macros.m_component_id_display()

    def b012(self):
        """Wireframe Non Active (Wireframe All But The Selected Item)"""
        current_panel = mtk.get_panel(withFocus=1)
        state = cmds.modelEditor(current_panel, q=True, activeOnly=1)
        cmds.modelEditor(current_panel, edit=1, activeOnly=not state)

    def b013(self):
        """Explode View GUI"""
        self.sb.handlers.marking_menu.show("exploded_view")

    def b014(self):
        """Color Manager GUI"""
        self.sb.handlers.marking_menu.show("color_manager")

    def b021(self):
        """Template Selected"""
        cmds.toggle(template=1)

    def b022(self):
        """Display UV Borders"""
        mtk.Macros.m_toggle_uv_border_edges()

    def chk014_init(self, widget):
        """Initialize UV Display: Checkered toggle from current state."""
        widget.setCheckable(True)
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        widget.setChecked(bool(cmds.textureWindow(panel, q=True, displayCheckered=True)))

    def chk014(self, state, widget):
        """UV Display: Checkered Pattern"""
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        cmds.textureWindow(panel, edit=1, displayCheckered=state)

    def chk015_init(self, widget):
        """Initialize UV Display: Borders toggle from current state."""
        widget.setCheckable(True)
        widget.setChecked(bool(cmds.polyOptions(q=True, displayMapBorder=True)))

    def chk015(self, state, widget):
        """UV Display: Borders"""
        borderWidth = cmds.optionVar(query="displayPolyBorderEdgeSize")[1]
        cmds.polyOptions(displayMapBorder=state, sizeBorder=borderWidth)

    def chk016_init(self, widget):
        """Initialize UV Display: Distortion toggle from current state."""
        widget.setCheckable(True)
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        widget.setChecked(bool(cmds.textureWindow(panel, q=True, displayDistortion=True)))

    def chk016(self, state, widget):
        """UV Display: Distortion"""
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        cmds.textureWindow(panel, edit=1, displayDistortion=state)

    def b023(self):
        """Soft Edge Display"""
        mtk.Macros.m_soft_edge_display()

    def b024(self):
        """Display Face Normals"""
        mtk.Macros.m_normals_display()


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
