# !/usr/bin/python
# coding=utf-8
"""Display: one Slots class for both hosts.

The Display list's rows each call one ``self.tk.DisplayUtils`` toggle and say
the state it left. A toggle answers what it did (an object list, a bool, the
display mode now shown) or ``None`` / ``[]`` when there was nothing to act on;
the wording is the panel's. A row only one host can serve names that host
(the ``requires`` vocabulary of the ``.ui`` files) and is hidden elsewhere.
"""

from tentacle import Slots


class DisplaySlots(Slots):
    #: The Display list: ``{category: [(label, handler, requires), ...]}``. A
    #: handler acts and returns the message the list shows. *requires* names the
    #: one host that serves the row (``None``: both), applied through uitk's
    #: visibility policy like a ``.ui`` widget's ``requires`` tag.
    _LIST000_ITEMS = {
        "View": [
            ("Hide Selected", "_hide_selected", None),
            # Blender cannot select a hidden object (hide_set deselects it), so
            # there is no selection to reveal.
            ("Show Selected", "_show_selected", "maya"),
            ("Show Geometry", "_show_geometry", None),
            ("Component ID", "_component_id", None),
            ("Mat Override", "_mat_override", None),
        ],
        "Wireframe": [
            ("Wireframe Selected", "_wireframe_selected", None),
            ("Wireframe Inactive", "_wireframe_inactive", None),
            ("Template Selected", "_template_selected", None),
            ("Shaded Selected", "_shaded_selected", None),
            # Maya's object color palette; Blender has none (Color ID, beside
            # the list, colour-codes objects in both hosts).
            ("Set Wireframe Color", "_set_wireframe_color", "maya"),
        ],
        "XRay": [
            ("Xray Selected", "_xray_selected", None),
            ("Un-Xray All", "_un_xray_all", None),
            ("Xray Other", "_xray_other", None),
        ],
        "UV": [
            # No Blender overlay highlights UV-border edges (verified, 5.1).
            ("Display UV Border", "_uv_border_edges", "maya"),
            ("Checkered", "_uv_checkered", None),
            ("Borders", "_uv_border_edges", "maya"),
            ("Distortion", "_uv_distortion", None),
        ],
        "Normals": [
            ("Display Normal", "_display_normals", None),
            ("Soft Edge Display", "_soft_edge_display", None),
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.display
        self.submenu = self.sb.loaded_ui.display_submenu

    # --- Display expandable list ----------------------------------------

    def header_init(self, widget):
        """Header menu: the submenu's Display expandable list -- hover a row to
        fan its flyout right (list000_init applies the hover_menu preset here)."""
        # List leaves are one-shot actions: dismiss the menu once one is
        # triggered (category rows only navigate).
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            self.sb.registered_widgets.ExpandableList, setObjectName="list000"
        )

    def list000_init(self, widget):
        """Initialize the Display expandable list (categories -> actions)."""
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_overlay_left" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        root = widget.add("Display")
        for category, rows in self._LIST000_ITEMS.items():
            cat = root.sublist.add(category)
            items = cat.sublist.add([label for label, _handler, _requires in rows])
            for item, (_label, _handler, requires) in zip(items, rows):
                if requires:
                    item.setProperty("requires", requires)
                    self.sb.apply_visibility_policy(item)

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Run a Display row and report the state it left. Category rows are
        navigation only."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        parent = item.parent_item_text() or ""
        for label, handler, _requires in self._LIST000_ITEMS.get(parent, ()):
            if label == text:
                message = getattr(self, handler)()
                if message:
                    self.sb.message_box(message)
                return

    # --- report wording ---------------------------------------------------

    @staticmethod
    def _word(state):
        """A toggle's answer as the list shows it: a bool is On / Off, a mode
        name is title-cased (``"uv"`` -> ``"UV"``)."""
        if isinstance(state, bool):
            return "On" if state else "Off"
        return {"uv": "UV"}.get(state, str(state).title())

    @staticmethod
    def _count(title, objects):
        """*title* with how many objects a row acted on, or that none were selected."""
        if not objects:
            return f"{title}: <hl>nothing selected</hl>"
        return f"{title}: <hl>{len(objects)}</hl> object(s)"

    def _state(self, title, state, unavailable):
        """*title* with the state a toggle left, or *unavailable* when it had
        nothing to act on (it returned ``None``)."""
        if state is None:
            return f"{title}: <hl>{unavailable}</hl>"
        return f"{title}: <hl>{self._word(state)}</hl>"

    # --- View ---------------------------------------------------------------

    def _hide_selected(self):
        return self._count("Hide Selected", self.tk.DisplayUtils.hide_objects(None))

    def _show_selected(self):
        return self._count("Show Selected", self.tk.DisplayUtils.show_objects(None))

    def _show_geometry(self):
        """Every mesh visible, with what hides it: its parents and the display
        layers (Blender: collections)."""
        self.tk.DisplayUtils.set_visibility("mesh", True)
        return "Geometry: <hl>visible</hl>"

    def _component_id(self):
        """Maya cycles the selected meshes' vertex / edge / face / UV IDs; Blender
        toggles the viewport's index overlay."""
        return self._state(
            "Component ID Display",
            self.tk.DisplayUtils.cycle_component_ids(),
            "select a polygon mesh in a 3D viewport",
        )

    def _mat_override(self):
        return self._state(
            "Material Override",
            self.tk.DisplayUtils.toggle_material_override(),
            "no 3D viewport",
        )

    # --- Wireframe ------------------------------------------------------------

    def _wireframe_selected(self):
        state = self.tk.DisplayUtils.toggle_wireframe(None)
        if state == []:
            return "Wireframe Selected: <hl>nothing selected</hl>"
        return f"Wireframe Selected: <hl>{self._word(state)}</hl>"

    def _wireframe_inactive(self):
        return self._state(
            "Wireframe Inactive",
            self.tk.DisplayUtils.toggle_wireframe_inactive(),
            "no 3D viewport",
        )

    def _template_selected(self):
        """Template the selection; Blender's templated objects cannot be
        selected again, so there a click with nothing selected releases them."""
        result = self.tk.DisplayUtils.toggle_template(None)
        if not result:
            return "Template Selected: <hl>nothing selected</hl>"
        templated, objects = result
        verb = "templated" if templated else "released"
        return f"Template Selected: <hl>{len(objects)}</hl> object(s) {verb}"

    def _shaded_selected(self):
        return self._count(
            "Shaded Selected", self.tk.DisplayUtils.set_wireframe(None, False)
        )

    def _set_wireframe_color(self):
        opened = self.tk.UiUtils.open_editor("Wireframe Color")
        return "Wireframe Color: <hl>{}</hl>".format(
            "palette opened" if opened else "could not open the palette"
        )

    # --- XRay -----------------------------------------------------------------

    def _xray_selected(self):
        result = self.tk.DisplayUtils.toggle_xray(None)
        if not result:  # [] nothing selected; None nothing x-rayable in it
            return "Xray Selected: <hl>nothing selected</hl>"
        state, count = result
        return f"Xray Selected ({count}): <hl>{self._word(state)}</hl>"

    def _un_xray_all(self):
        self.tk.DisplayUtils.clear_xray()
        return "Xray: <hl>cleared on all objects</hl>"

    def _xray_other(self):
        result = self.tk.DisplayUtils.toggle_xray_others(None)
        if not result:
            return "Xray Other: <hl>nothing to toggle</hl>"
        state, count = result
        return f"Xray Other ({count}): <hl>{self._word(state)}</hl>"

    # --- UV -------------------------------------------------------------------

    def _uv_border_edges(self):
        state = self.tk.DisplayUtils.toggle_uv_border_edges(None)
        if state == []:
            return "UV Border Edges: <hl>nothing selected</hl>"
        return self._state("UV Border Edges", state, "no polygon mesh selected")

    def _uv_checkered(self):
        return self._state(
            "UV Checkered",
            self.tk.DisplayUtils.toggle_uv_checker(),
            "no UV editor open",
        )

    def _uv_distortion(self):
        """Maya toggles the UV Editor's distortion shading; Blender cycles its
        stretch overlay through Angle and Area."""
        return self._state(
            "UV Distortion",
            self.tk.DisplayUtils.toggle_uv_distortion(),
            "no UV editor open",
        )

    # --- Normals --------------------------------------------------------------

    def _display_normals(self):
        """Cycle face / vertex normals (and Maya's tangents) on and off."""
        return self._state(
            "Display Normals",
            self.tk.DisplayUtils.cycle_normals_display(),
            "select a polygon mesh in a 3D viewport",
        )

    def _soft_edge_display(self):
        return self._state(
            "Soft Edge Display",
            self.tk.DisplayUtils.toggle_soft_edge_display(),
            "select a polygon mesh in a 3D viewport",
        )

    # --- Buttons --------------------------------------------------------------

    def b013(self):
        """Exploded View: open the Exploded View panel."""
        self.sb.handlers.marking_menu.show("exploded_view")

    def b014(self):
        """Color ID: open the Color ID panel (color-code objects by ID)."""
        self.sb.handlers.marking_menu.show("color_id")
