# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from uitk import Signals
from tentacle.slots.maya._slots_maya import SlotsMaya


class DisplaySlots(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.display
        self.submenu = self.sb.loaded_ui.display_submenu

    # --- Display Expandable List ----------------------------------------

    # (category, label) order is preserved; each entry maps to a wrapper
    # method that performs the action and returns a formatted state
    # message for sb.message_box.
    _LIST000_ITEMS = {
        "View": [
            ("Hide Selected", "_list_hide_selected"),
            ("Show Selected", "_list_show_selected"),
            ("Show Geometry", "_list_show_geometry"),
            ("Component ID", "_list_component_id"),
            ("Mat Override", "_list_mat_override"),
        ],
        "Wireframe": [
            ("Wireframe Selected", "_list_wireframe_selected"),
            ("Wireframe Inactive", "_list_wireframe_inactive"),
            ("Template Selected", "_list_template_selected"),
            ("Set Wireframe Color", "_list_set_wireframe_color"),
        ],
        "XRay": [
            ("Xray Selected", "_list_xray_selected"),
            ("Un-Xray All", "_list_un_xray_all"),
            ("Xray Other", "_list_xray_other"),
        ],
        "UV": [
            ("Display UV Border", "_list_uv_border"),
            ("Checkered", "_list_uv_checkered"),
            ("Borders", "_list_uv_borders"),
            ("Distortion", "_list_uv_distortion"),
        ],
        "Normals": [
            ("Display Normal", "_list_display_normal"),
            ("Soft Edge Display", "_list_soft_edge"),
        ],
    }

    def list000_init(self, widget):
        """Initialize Display expandable list (categories → actions)."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_overlay_left")

        root = widget.add("Display")
        root.sublist.setMinimumWidth(widget.width() or 120)

        for category, items in self._LIST000_ITEMS.items():
            cat = root.sublist.add(category)
            cat.sublist.add([label for label, _ in items])

    @Signals("on_item_interacted")
    def list000(self, item):
        """Dispatch a Display action and report state via message_box."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        text = item.item_text()
        parent = item.parent_item_text() or ""

        for label, handler_name in self._LIST000_ITEMS.get(parent, ()):
            if label == text:
                handler = getattr(self, handler_name, None)
                if callable(handler):
                    msg = handler()
                    if msg:
                        self.sb.message_box(msg)
                return

    # --- List wrappers (return formatted state message) -----------------

    def _list_hide_selected(self):
        sel = cmds.ls(sl=True) or []
        self.b002()
        return (
            f"Hide Selected: <hl>{len(sel)}</hl> object(s)"
            if sel
            else "Hide Selected: <hl>nothing selected</hl>"
        )

    def _list_show_selected(self):
        sel = cmds.ls(sl=True) or []
        self.b003()
        return (
            f"Show Selected: <hl>{len(sel)}</hl> object(s)"
            if sel
            else "Show Selected: <hl>nothing selected</hl>"
        )

    def _list_show_geometry(self):
        self.b004()
        return "Geometry: <hl>visible</hl>"

    def _list_component_id(self):
        self.b011()
        return "Component ID Display: <hl>toggled</hl>"

    def _list_mat_override(self):
        panel = cmds.playblast(activeEditor=True)
        self.b009()
        if panel:
            state = cmds.modelEditor(panel, q=True, useDefaultMaterial=True)
            return f"Material Override: <hl>{'On' if state else 'Off'}</hl>"
        return "Material Override: <hl>no active panel</hl>"

    def _list_wireframe_selected(self):
        self.b001()
        return "Wireframe Selected: <hl>cycled</hl>"

    def _list_wireframe_inactive(self):
        self.b012()
        panel = mtk.get_panel(withFocus=1)
        state = cmds.modelEditor(panel, q=True, activeOnly=1) if panel else None
        if state is None:
            return "Wireframe Inactive: <hl>toggled</hl>"
        return f"Wireframe Inactive: <hl>{'On' if state else 'Off'}</hl>"

    def _list_template_selected(self):
        sel = cmds.ls(sl=True) or []
        self.b021()
        return (
            f"Template Selected: <hl>{len(sel)}</hl> object(s)"
            if sel
            else "Template Selected: <hl>nothing selected</hl>"
        )

    def _list_set_wireframe_color(self):
        self.b000()
        return "Wireframe Color: <hl>palette opened</hl>"

    def _list_xray_selected(self):
        sel = cmds.ls(sl=True, transforms=True) or []
        self.b005()
        if not sel:
            return "Xray Selected: <hl>nothing selected</hl>"
        result = cmds.displaySurface(sel[-1], xRay=True, query=True)
        state = bool(result[0]) if result else False
        return f"Xray Selected ({len(sel)}): <hl>{'On' if state else 'Off'}</hl>"

    def _list_un_xray_all(self):
        self.b006()
        return "Xray: <hl>cleared on all meshes</hl>"

    def _list_xray_other(self):
        meshes = cmds.ls(type="mesh", long=True) or []
        all_transforms = set()
        for m in meshes:
            p = mtk.NodeUtils.get_parent(m, full_path=True)
            if p:
                all_transforms.add(p)
        selected = set(cmds.ls(sl=True, transforms=True, long=True) or [])
        other = all_transforms - selected
        self.b007()
        return f"Xray Other: <hl>{len(other)}</hl> object(s)"

    def _list_uv_border(self):
        self.b022()
        return "UV Border Edges: <hl>toggled</hl>"

    def _list_uv_checkered(self):
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        new_state = not bool(cmds.textureWindow(panel, q=True, displayCheckered=True))
        cmds.textureWindow(panel, edit=True, displayCheckered=new_state)
        return f"UV Checkered: <hl>{'On' if new_state else 'Off'}</hl>"

    def _list_uv_borders(self):
        new_state = not bool(cmds.polyOptions(q=True, displayMapBorder=True))
        border_width = cmds.optionVar(query="displayPolyBorderEdgeSize")[1]
        cmds.polyOptions(displayMapBorder=new_state, sizeBorder=border_width)
        return f"UV Borders: <hl>{'On' if new_state else 'Off'}</hl>"

    def _list_uv_distortion(self):
        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        new_state = not bool(cmds.textureWindow(panel, q=True, displayDistortion=True))
        cmds.textureWindow(panel, edit=True, displayDistortion=new_state)
        return f"UV Distortion: <hl>{'On' if new_state else 'Off'}</hl>"

    def _list_display_normal(self):
        self.b024()
        return "Face Normals: <hl>toggled</hl>"

    def _list_soft_edge(self):
        self.b023()
        return "Soft Edge Display: <hl>toggled</hl>"

    # --- Display Actions ------------------------------------------------

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
