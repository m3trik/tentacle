# !/usr/bin/python
# coding=utf-8
import bpy
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class DisplaySlots(SlotsBlender):
    """Blender port of the shared ``display`` menu.

    The display list is curated to the object-property toggles that map cleanly to Blender —
    visibility (``hide_set``), wireframe (``display_type``), and see-through (``show_in_front``).
    Maya's modelEditor / textureWindow editor settings (component-ID, material-override, wireframe-
    on-inactive, UV-editor displays, normal overlays) are viewport/editor state with no per-object
    Blender analogue and are omitted rather than shown as dead entries. The Explode-View and
    Color-Manager sub-windows aren't ported yet.
    """

    # (category -> [(label, handler_name)]); handlers act + return a state message.
    _LIST000_ITEMS = {
        "View": [
            ("Hide Selected", "_hide_selected"),
            ("Show All", "_show_all"),
        ],
        "Wireframe": [
            ("Wireframe Selected", "_wireframe_selected"),
            ("Shaded Selected", "_shaded_selected"),
        ],
        "XRay": [
            ("Xray Selected", "_xray_selected"),
            ("Un-Xray All", "_un_xray_all"),
            ("Xray Other", "_xray_other"),
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

    def _shaded_selected(self):
        sel = self.selected_objects()
        for o in sel:
            o.display_type = "TEXTURED"
        return f"Shaded Selected: <hl>{len(sel)}</hl> object(s)"

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

    # --- deferred (separate unported sub-windows) -----------------------
    def b013(self):
        """Explode View — separate window not ported to Blender yet."""
        self.sb.message_box("Explode View is not yet implemented for Blender.")

    def b014(self):
        """Color Manager — separate window not ported to Blender yet."""
        self.sb.message_box("Color Manager is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
