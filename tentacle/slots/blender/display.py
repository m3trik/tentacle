# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class DisplaySlots(SlotsBlender):
    """Blender port of the shared ``display`` menu.

    The display list is curated to the object-property and per-viewport-overlay toggles that map
    cleanly to Blender — visibility (``hide_set``), wireframe (``display_type``), see-through
    (``show_in_front``), and the ``View3DOverlay``/``View3DShading``/``SpaceUVEditor`` viewport
    toggles that ARE Blender's per-viewport analogues of Maya's modelEditor / textureWindow editor
    settings (component-ID, material-override, UV-editor displays are themselves viewport/editor
    state in Maya too, not per-object — see each handler's docstring for the confirmed-live
    mapping). Only items with no verified Blender surface at all are omitted (UV Border/Checkered/
    Borders — see the UV category comment below). Explode View is a toggle backed by
    ``btk.explode_view`` (bbox-driven separation with exact restore); Color ID opens the
    co-located swatch-palette panel.
    """

    # (category -> [(label, handler_name)]); handlers act + return a state message.
    _LIST000_ITEMS = {
        "View": [
            ("Hide Selected", "_hide_selected"),
            ("Show All", "_show_all"),
            ("Component ID", "_component_id"),
            ("Mat Override", "_mat_override"),
        ],
        "Wireframe": [
            ("Wireframe Selected", "_wireframe_selected"),
            ("Wireframe Inactive", "_wireframe_inactive"),
            ("Template Selected", "_template_selected"),
            ("Shaded Selected", "_shaded_selected"),  # Blender-only extra (see parity_map DEFAULT_DELTAS)
            ("Set Wireframe Color", "_set_wireframe_color"),
        ],
        "XRay": [
            ("Xray Selected", "_xray_selected"),
            ("Un-Xray All", "_un_xray_all"),
            ("Xray Other", "_xray_other"),
        ],
        # Border/Checkered/Borders dropped — verified live (Blender 5.1) that neither a UV-editor
        # checker-background overlay nor a mesh/UV border-edge-highlight overlay (with adjustable
        # width) exists on SpaceUVEditor/View3DOverlay; see parity_map.py HANDLERS['display'] for
        # the per-item rationale. Distortion maps directly to SpaceUVEditor.show_stretch.
        "UV": [
            ("Distortion", "_uv_distortion"),
        ],
        "Normals": [
            ("Display Normals", "_display_normals"),
            ("Soft Edge Display", "_soft_edge_display"),
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

    def _template_selected(self):
        """Template the selection — dimmed WIRE, non-renderable, non-selectable — the Blender
        analogue of Maya's Display ▸ Wireframe ▸ Template Selected (b021 -> cmds.toggle(template=1);
        matches blendertk.reference_manager's 'template' mode: display_type='WIRE' + hide_select).

        Toggle handling accounts for a Blender quirk verified live (5.1): setting hide_select=True
        DESELECTS the object, so templated objects can't be re-selected to untemplate. So: with a
        selection, this templates it; with nothing selected, it releases every templated object
        (display_type=='WIRE' AND hide_select — a pair only this handler sets together)."""
        sel = self.selected_objects()
        if sel:
            for o in sel:
                o.display_type = "WIRE"
                o.hide_render = True
                o.hide_select = True  # deselects as a side effect in Blender
            return f"Template Selected: <hl>{len(sel)}</hl> object(s) templated"
        templated = [o for o in bpy.data.objects if o.hide_select and o.display_type == "WIRE"]
        for o in templated:
            o.hide_select = False
            o.hide_render = False
            o.display_type = "TEXTURED"
        return (
            f"Template Selected: <hl>{len(templated)}</hl> released"
            if templated else "Template Selected: <hl>nothing selected</hl>"
        )

    def _shaded_selected(self):
        sel = self.selected_objects()
        for o in sel:
            o.display_type = "TEXTURED"
        return f"Shaded Selected: <hl>{len(sel)}</hl> object(s)"

    def _set_wireframe_color(self):
        """Set Wireframe Color — Blender has no 8-slot object-color palette (Maya's
        ``objectColorPalette``); route to the Color ID panel, which color-codes objects
        via object color / material / vertex (a superset of Maya's wireframe-color swatches)."""
        self.sb.handlers.marking_menu.show("color_id")
        return "Wireframe Color: <hl>Color ID opened</hl>"

    def _display_normals(self):
        """Cycle the viewport normals overlay Off -> Face -> Vertex -> Off (visible in Edit Mode) —
        the Blender analogue of Maya's Display ▸ Normals, whose mtk.Macros.m_normals_display cycles
        Off/Facet/Vertex/Tangent. Tangent has no View3DOverlay counterpart in Blender 5.1 (no
        show_tangent RNA — verified live) and is dropped from the cycle; see parity_map.py
        HANDLERS['display']. Every VIEW_3D area is driven to the SAME next state off the first
        area's state (the split-viewport-consistency convention _mat_override uses)."""
        areas = btk.get_areas("VIEW_3D")  # window-independent (context.screen is None from the Qt-pump context)
        if not areas:
            return "Display Normals: <hl>no 3D viewport</hl>"
        ov0 = areas[0].spaces.active.overlay
        if ov0.show_vertex_normals:      # Vertex -> Off
            state, label = (False, False), "Off"
        elif ov0.show_face_normals:      # Face -> Vertex
            state, label = (False, True), "Vertex"
        else:                            # Off -> Face
            state, label = (True, False), "Face"
        for area in areas:
            ov = area.spaces.active.overlay
            ov.show_face_normals, ov.show_vertex_normals = state
        return f"Display Normals: <hl>{label}</hl>"

    def _soft_edge_display(self):
        """Toggle the viewport sharp-edge overlay (``View3DOverlay.show_edge_sharp``) — the
        Blender analogue of Maya's Soft Edge Display (both are per-viewport edge-shading state,
        not per-object; confirmed live in Blender 5.1)."""
        toggled = 0
        for area in btk.get_areas("VIEW_3D"):
            ov = area.spaces.active.overlay
            ov.show_edge_sharp = not ov.show_edge_sharp
            toggled += 1
        return f"Soft Edge Display: <hl>{'toggled' if toggled else 'no 3D viewport'}</hl>"

    def _component_id(self):
        """Toggle the viewport index-numbers overlay (``View3DOverlay.show_extra_indices``) — the
        Blender analogue of Maya's Component ID Display (both are per-viewport overlay state, not
        per-object; confirmed live in Blender 5.1)."""
        toggled = 0
        for area in btk.get_areas("VIEW_3D"):
            ov = area.spaces.active.overlay
            ov.show_extra_indices = not ov.show_extra_indices
            toggled += 1
        return f"Component ID Display: <hl>{'toggled' if toggled else 'no 3D viewport'}</hl>"

    def _mat_override(self):
        """Toggle the viewport's solid-shading color source between Material and a flat Single
        color (``View3DShading.color_type``) — the Blender analogue of Maya's Material Override
        (both replace real material feedback with a flat default look; confirmed live in
        Blender 5.1: MATERIAL/OBJECT/RANDOM/VERTEX/TEXTURE/SINGLE).

        Every ``VIEW_3D`` area is driven to the SAME resulting state in one click (any area
        already in Single -> all areas go back to Material, mirroring ``_wireframe_inactive``'s
        any()-driven convention) — toggling each area independently off its own prior state would
        let a split/quad viewport end up half On/half Off while the message reports only one of
        them (confirmed live: a 2-way split with divergent starting states produced a mismatched
        message before this fix)."""
        areas = btk.get_areas("VIEW_3D")
        if not areas:
            return "Material Override: <hl>no 3D viewport</hl>"
        turn_on = not any(a.spaces.active.shading.color_type == "SINGLE" for a in areas)
        new_type = "SINGLE" if turn_on else "MATERIAL"
        for a in areas:
            a.spaces.active.shading.color_type = new_type
        return f"Material Override: <hl>{'On' if turn_on else 'Off'}</hl>"

    def _uv_distortion(self):
        """Cycle the UV Editor's stretch (distortion) overlay: Off -> Angle -> Area -> Off
        (``SpaceUVEditor.show_stretch`` / ``display_stretch_type``) — the Blender analogue of
        Maya's textureWindow UV Distortion display and its distortion sub-modes (confirmed live
        in Blender 5.1).

        The next phase is decided once, from the first matched editor's current phase, then
        applied to every ``IMAGE_EDITOR`` area — keeping multiple open UV editors in lockstep
        (and the returned message accurate for all of them), the same reasoning as
        ``_mat_override``."""
        areas = btk.get_areas("IMAGE_EDITOR")
        if not areas:
            return "UV Distortion: <hl>no UV editor open</hl>"
        uv0 = areas[0].spaces.active.uv_editor
        if not uv0.show_stretch:
            show, stretch_type, state = True, "ANGLE", "On (Angle)"
        elif uv0.display_stretch_type == "ANGLE":
            show, stretch_type, state = True, "AREA", "On (Area)"
        else:
            show, stretch_type, state = False, uv0.display_stretch_type, "Off"
        for a in areas:
            uv = a.spaces.active.uv_editor
            uv.show_stretch = show
            uv.display_stretch_type = stretch_type
        return f"UV Distortion: <hl>{state}</hl>"

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
        """Color ID — swatch palette to color-code objects (material / object color / vertex)."""
        self.sb.handlers.marking_menu.show("color_id")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
