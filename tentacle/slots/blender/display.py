# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class DisplaySlots(SlotsBlender):
    """Blender port of the shared ``display`` menu.

    The display list is curated to the object-property toggles that map cleanly to Blender —
    visibility (``hide_set``), wireframe (``display_type``), and see-through (``show_in_front``).
    Maya's modelEditor / textureWindow editor settings (component-ID, material-override, UV-editor
    displays) are viewport/editor state with no per-object Blender analogue and are omitted rather
    than shown as dead entries; the ones that DO map (wireframe-on-inactive → non-selected
    ``display_type``, face-normals overlay) are wired below. Explode View is a toggle backed by
    ``btk.explode_view`` (bbox-driven separation with exact restore); Color Manager opens the
    co-located swatch-palette panel.
    """

    # (category -> [(label, handler_name)]); handlers act + return a state message.
    _LIST000_ITEMS = {
        "View": [
            ("Hide Selected", "_hide_selected"),
            ("Show All", "_show_all"),
        ],
        "Wireframe": [
            ("Wireframe Selected", "_wireframe_selected"),
            ("Wireframe Inactive", "_wireframe_inactive"),
            ("Shaded Selected", "_shaded_selected"),
            ("Set Wireframe Color", "_set_wireframe_color"),
        ],
        "XRay": [
            ("Xray Selected", "_xray_selected"),
            ("Un-Xray All", "_un_xray_all"),
            ("Xray Other", "_xray_other"),
        ],
        "Normals": [
            ("Display Normals", "_display_normals"),
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.display
        self.submenu = self.sb.loaded_ui.display_submenu

    # --- Display expandable list ----------------------------------------
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

    # --- List handlers (act + return a state message) -------------------
    def _hide_selected(self):
        sel = self.selected_objects()
        for o in sel:
            o.hide_set(True)
        return (
            f"Hide Selected: <hl>{len(sel)}</hl> object(s)"
            if sel else "Hide Selected: <hl>nothing selected</hl>"
        )

    def _show_all(self):
        for o in bpy.data.objects:
            o.hide_set(False)
        return "Show All: <hl>unhidden</hl>"

    def _wireframe_selected(self):
        sel = self.selected_objects()
        for o in sel:
            o.display_type = "SOLID" if o.display_type == "WIRE" else "WIRE"
        return (
            f"Wireframe Selected: <hl>{len(sel)}</hl> toggled"
            if sel else "Wireframe Selected: <hl>nothing selected</hl>"
        )

    def _wireframe_inactive(self):
        """Show every non-selected mesh as wireframe (toggle — restore to textured if any
        inactive mesh is already wire). Blender's per-object analogue of Maya's
        wireframe-on-inactive viewport mode."""
        sel = set(self.selected_objects())
        inactive = [o for o in bpy.data.objects if o.type == "MESH" and o not in sel]
        wire = any(o.display_type == "WIRE" for o in inactive)
        for o in inactive:
            o.display_type = "TEXTURED" if wire else "WIRE"
        return f"Wireframe Inactive: <hl>{'Off' if wire else 'On'}</hl> ({len(inactive)})"

    def _shaded_selected(self):
        sel = self.selected_objects()
        for o in sel:
            o.display_type = "TEXTURED"
        return f"Shaded Selected: <hl>{len(sel)}</hl> object(s)"

    def _set_wireframe_color(self):
        """Set Wireframe Color — Blender has no 8-slot object-color palette (Maya's
        ``objectColorPalette``); route to the Color Manager panel, which color-codes objects
        via object color / material / vertex (a superset of Maya's wireframe-color swatches)."""
        self.sb.handlers.marking_menu.show("color_manager")
        return "Wireframe Color: <hl>Color Manager opened</hl>"

    def _display_normals(self):
        """Toggle the viewport face-normals overlay (visible in Edit Mode) — the Blender
        analogue of Maya's Display ▸ Normals."""
        toggled = 0
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                ov = area.spaces.active.overlay
                ov.show_face_normals = not ov.show_face_normals
                toggled += 1
        return f"Display Normals: <hl>{'toggled' if toggled else 'no 3D viewport'}</hl>"

    def _xray_selected(self):
        sel = self.selected_objects()
        for o in sel:
            o.show_in_front = not o.show_in_front
        return (
            f"Xray Selected: <hl>{len(sel)}</hl> toggled"
            if sel else "Xray Selected: <hl>nothing selected</hl>"
        )

    def _un_xray_all(self):
        for o in bpy.data.objects:
            o.show_in_front = False
        return "Xray: <hl>cleared on all objects</hl>"

    def _xray_other(self):
        sel = set(self.selected_objects())
        other = [o for o in bpy.data.objects if o.type == "MESH" and o not in sel]
        for o in other:
            o.show_in_front = not o.show_in_front
        return f"Xray Other: <hl>{len(other)}</hl> object(s)"

    def b013(self):
        """Explode View — open the Exploded View panel (Explode / Un-Explode / Un-Explode All /
        Toggle), served from blendertk by the BlenderUiHandler, mirroring Maya's exploded-view
        window."""
        self.sb.handlers.marking_menu.show("exploded_view")

    def b014(self):
        """Color Manager — swatch palette to color-code objects (material / object color / vertex)."""
        self.sb.handlers.marking_menu.show("color_manager")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
