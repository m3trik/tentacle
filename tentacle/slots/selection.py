# !/usr/bin/python
# coding=utf-8
"""Selection: one Slots class for both hosts.

Every operation is the host toolkit's ``Selection`` / ``EditUtils``
(``self.tk``), given ``None`` for the selection. An operation with nothing to
act on returns ``[]`` and the slot says so; a state the user can fix raises
``ValueError`` and a host refusal ``RuntimeError``, both shown as the host
words them.

Two pieces are the host's own and are read from it, not assumed:

* the **Convert To** list (``list001``): a root row whose flyout is one row per
  component category (Verts, Edges, Faces, UV's, Shell), each converting on
  click and fanning out its related conversions on hover. The shape is
  :attr:`SelectionSlots._CONVERT_TO_GROUPS`; a row shows only when the host
  lists its conversion (``Selection.get_conversion_types``): Blender has no
  Vertex Faces or UV component, so "UV's" is a header there.
* the **selection-constraint row** (``b002``-``b007``): Maya keeps persistent
  ``polySelectConstraint`` flags, so the buttons are toggles mirroring them
  (several can be on at once); Blender has no drag-select constraint to leave
  on, so each press expands the current selection once. The host says which
  (``Selection.get_selection_constraints`` is ``None`` where nothing persists).
"""

from tentacle import Slots


class SelectionSlots(Slots):
    """The ``selection`` panel. Not to be confused with the HUD's selection
    readout (``slots/hud.py``)."""

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.selection
        self.submenu = self.sb.loaded_ui.selection_submenu

    # ------------------------------------------------------------------ list000  Select by Type
    def list000_init(self, widget):
        """Select by Type: hierarchical type list."""
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up" if submenu else "hover_menu")
        root = widget.add("By Type")

        # Settings entry, positioned nearest the trigger row in both layouts:
        # last in the submenu (expand_up: last-added sits at the bottom, by the
        # trigger), first in the panel (hover_menu fans right with its top row
        # aligned to the trigger). A slot-wired button with a settings-gear
        # prefix icon (set in tb004_init) and no option box, so it stays a plain
        # list row; its click is dispatched from list000 to open the scope /
        # mode menu the leaf actions read.
        tb004_kwargs = dict(
            setObjectName="tb004",
            setText="Settings",
            setToolTip=(
                "Select by Type settings.\n"
                "Set the scope the type filters draw from, and whether matches\n"
                "replace, add to, or remove from the existing selection."
            ),
        )
        if not submenu:
            self.add_slot_widget(root.sublist, **tb004_kwargs)

        for category, types in self.tk.Selection.get_selection_categories().items():
            row = root.sublist.add(category)
            row.sublist.add(sorted(types))

        if submenu:
            self.add_slot_widget(root.sublist, **tb004_kwargs)

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Select by Type"""
        # Only leaf items (specific types) act; the root and the category
        # headers are navigation only.
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        # The Settings row opens its scope / mode menu instead of acting as a
        # type filter. Two dispatch paths reach it, mutually exclusively: here
        # (plain event flow: the list consumes the release, so the button's own
        # clicked never fires) and its clicked (the marking menu fires a
        # menu-hosted leaf's clicked at release and never routes a widget with
        # a clicked signal through on_item_interacted). Both delegate to tb004,
        # so the menu opens exactly once either way.
        if item.objectName() == "tb004":
            self.tb004(item)
            return
        label = item.item_text()
        menu = self.submenu.tb004.menu
        mode = menu.cmb_bytype_mode.currentData() or "replace"
        self.run_operation(
            self.tk.Selection.select_by_type,
            label,
            None,
            mode=mode,
            scope=menu.cmb_bytype_scope.currentData() or "all",
            empty=f"Select by Type: no <hl>{label}</hl> in the current scope.",
        )

    def tb004_init(self, widget):
        """Select by Type settings menu.

        The row shows a settings-gear prefix icon and opens this menu on click
        (dispatched from ``list000``). The menu is the button's own menu: no
        option box (the gear would repeat the row click) and no apply button
        (the combos take effect the moment a leaf action reads them).
        Self-labeling combos: two radio groups in one menu would need manual
        QButtonGroup separation.
        """
        self.sb.IconManager.set_icon(widget, "settings")
        widget.configure_menu(
            trigger_button="none",
            add_header=True,
            add_apply_button=False,
            add_defaults_button=True,
            hide_on_leave=True,
            match_parent_width=False,
        )
        menu = widget.menu
        menu.setTitle("Select By Type")
        scope = menu.add(
            "QComboBox",
            setObjectName="cmb_bytype_scope",
            setToolTip="The pool of objects the type filters draw from:\n"
            "• All Objects: every object in the scene.\n"
            "• Selected: the current selection only.\n"
            "• Visible: visible objects only.",
        )
        for label, data in [
            ("Scope: All Objects", "all"),
            ("Scope: Selected", "selected"),
            ("Scope: Visible", "visible"),
        ]:
            scope.addItem(label, data)
        mode = menu.add(
            "QComboBox",
            setObjectName="cmb_bytype_mode",
            setToolTip="How the matches combine with the existing selection:\n"
            "• Replace: select only the matches.\n"
            "• Add: add the matches to the current selection.\n"
            "• Remove: deselect the matches.",
        )
        for label, data in [
            ("Mode: Replace", "replace"),
            ("Mode: Add", "add"),
            ("Mode: Remove", "remove"),
        ]:
            mode.addItem(label, data)

    def tb004(self, widget):
        """Select by Type settings: open the scope / mode menu.

        Wired to the button's ``clicked`` (register_widget), so the marking
        menu, which fires a menu-hosted leaf's ``clicked`` at release-dispatch,
        opens it; ``list000`` also calls this for the plain event-flow path.
        The two paths never both fire for one interaction.
        """
        widget.menu.show_as_popup(anchor_widget=widget, position="cursorPos")

    # ------------------------------------------------------------------ cmb002  Rig Picking Mode
    _RIG_PICKING = (
        ("Picking: Rig Aware", "rig"),
        ("Picking: Normal", "normal"),
        ("Picking: Meshes Only", "meshes_only"),
    )

    def cmb002_init(self, widget):
        """Rig Picking Mode: mirrors the scene, never restored (see
        mirror_app_state). Maya's: its rigs lock their skinned meshes, which
        the modes lift (the ``.ui`` tags it ``requires="maya"``).

        Re-read on every show: a rig re-locks its mesh on (re)bind, and a scene
        open swaps the state wholesale.
        """
        widget.refresh_on_show = True
        widget.add(list(self._RIG_PICKING))
        modes = [mode for _, mode in self._RIG_PICKING]
        self.mirror_app_state(
            widget,
            lambda: widget.setCurrentIndex(
                modes.index(self.tk.Selection.get_rig_selection_mode())
            ),
        )

    def cmb002(self, index, widget):
        """Rig Picking Mode"""
        mode = widget.itemData(index)
        if not mode:
            return
        locked = self.tk.Selection.set_rig_selection_mode(mode)
        label = widget.itemText(index).split(": ")[-1]
        self.sb.message_box(
            f"Picking: <hl>{label}</hl> ({len(locked)} rigged mesh(es))."
        )

    # ------------------------------------------------------------------ cmb001  Reorder Selection
    #: The Reorder By rows (display order: saved as an index) and the method each runs.
    _REORDER_METHODS = (
        ("Name", "name"),
        ("Hierarchy", "hierarchy"),
        ("X Position", "x"),
        ("Y Position", "y"),
        ("Z Position", "z"),
        ("Distance from Origin", "distance"),
        ("Volume", "volume"),
        ("Vertex Count", "vertex_count"),
        ("Random", "random"),
        ("Creation Time", "creation_time"),
    )

    def cmb001_init(self, widget):
        """Reorder Selection Init"""
        widget.option_box.menu.setTitle("Reorder Selection")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reverse Order",
            setObjectName="chk009",
            setChecked=False,
            setToolTip="Reverse the order the chosen method produces.",
        )
        widget.add([label for label, _ in self._REORDER_METHODS], header="Reorder By:")

    def cmb001(self, index, widget):
        """Reorder Selection: reselect the selection in the chosen order."""
        label = widget.items[index]
        method = dict(self._REORDER_METHODS).get(label, "name")
        reverse = widget.option_box.menu.chk009.isChecked()
        reordered = self.run_operation(
            self.tk.Selection.reorder_selection,
            None,
            method=method,
            reverse=reverse,
            empty="No objects selected to reorder.",
        )
        if reordered:
            self.sb.message_box(
                f"Reordered <hl>{len(reordered)}</hl> object(s) by {label}"
                f"{' (reversed)' if reverse else ''}."
            )

    # ------------------------------------------------------------------ list001  Convert To
    #: Convert To rows -> the host's conversion names. The keys are the menu's
    #: rows, arranged into category flyouts by :attr:`_CONVERT_TO_GROUPS`.
    _CONVERT_TO = {
        "Verts": "vertices",
        "Vertex Faces": "vertex_faces",
        "Vertex Perimeter": "vertex_perimeter",
        "Edges": "edges",
        "Edge Loop": "edge_loop",
        "Edge Ring": "edge_ring",
        "Contained Edges": "contained_edges",
        "Edge Perimeter": "edge_perimeter",
        "Border Edges": "border_edges",
        "Faces": "faces",
        "Face Path": "face_path",
        "Contained Faces": "contained_faces",
        "Face Perimeter": "face_perimeter",
        "UV's": "uvs",
        "UV Shell": "uv_shell",
        "UV Shell Border": "uv_shell_border",
        "UV Perimeter": "uv_perimeter",
        "UV Edge Loop": "uv_edge_loop",
        "Shell": "shell",
        "Shell Border": "shell_border",
    }

    #: Convert To menu shape: ``{category: (member, ...)}`` in display order. A
    #: category is itself a row (clicking "Verts" converts to verts); hovering
    #: it fans out its members. A row whose conversion the host lacks is not
    #: shown, and a category it lacks is a navigation-only header for the
    #: members it has.
    _CONVERT_TO_GROUPS = {
        "Verts": ("Vertex Faces", "Vertex Perimeter"),
        "Edges": (
            "Edge Loop",
            "Edge Ring",
            "Contained Edges",
            "Edge Perimeter",
            "Border Edges",
        ),
        "Faces": ("Face Path", "Contained Faces", "Face Perimeter"),
        "UV's": ("UV Shell", "UV Shell Border", "UV Perimeter", "UV Edge Loop"),
        "Shell": ("Shell Border",),
    }

    def _convert_to_rows(self):
        """The Convert To rows this host serves."""
        served = set(self.tk.Selection.get_conversion_types())
        return {label for label, name in self._CONVERT_TO.items() if name in served}

    def list001_init(self, widget):
        """Convert To: category rows that convert on click and expand on hover.

        ``expand_overlay`` in the submenu: the category flyout covers the
        "Convert To" row itself (top row aligned to it, at least as wide as it)
        and grows downward, with each category's members fanning right;
        ``hover_menu`` in the panel, where the row is a layout-managed header
        menu that fans right on hover.
        """
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_overlay" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        root = widget.add(
            "Convert To",
            setToolTip="Convert the component selection to another component type.",
        )
        rows = self._convert_to_rows()
        for category, members in self._CONVERT_TO_GROUPS.items():
            members = [m for m in members if m in rows]
            if category not in rows and not members:
                continue
            if category in rows:
                tip = f"Click: convert to {category}."
                if members:
                    tip += " Hover: related conversions."
            else:
                tip = f"{category} conversions."
            row = root.sublist.add(category, setToolTip=tip)
            if members:
                row.sublist.add(members)

    @Slots.Signals("on_item_interacted")
    def list001(self, item):
        """Convert To: convert the component selection to verts, edges, faces, UVs or shells.

        Any row whose conversion the host serves runs, a category row ("Verts")
        as much as a leaf ("Vertex Faces"); the root and a category the host
        lacks are navigation only.
        """
        label = item.item_text()
        if label not in self._convert_to_rows():
            return
        self.run_operation(
            self.tk.Selection.convert_selection,
            self._CONVERT_TO[label],
            empty="<b>Nothing to convert.</b><br>"
            "Select components first (Blender: of a mesh in Edit Mode).",
        )

    # ------------------------------------------------------------------ b002-b007  Selection Constraints
    #: The constraint row, in .ui order: ``objectName -> (constraint, label)``.
    #: The constraint name is also the button's icon. objectNames are persisted
    #: / parity keys: never renumber them.
    _CONSTRAINT_BUTTONS = {
        "b002": ("angle", "Angle"),
        "b003": ("border", "Border"),
        "b004": ("edge_loop", "Edge Loop"),
        "b005": ("edge_ring", "Edge Ring"),
        "b006": ("shell", "Shell"),
        "b007": ("uv_edge_loop", "UV Edge Loop"),
    }

    #: What a press does, by whether the host keeps the constraint on.
    _CONSTRAINT_ACTION_HINT = {
        True: "Toggle: constrains what drag-selection picks up while on. "
        "Several can be on at once.",
        False: "One-shot: expands the current selection by this rule "
        "(Blender has no persistent drag-select constraint).",
    }

    #: Glyph extent for the row: a 16px icon in the 19px-high buttons the .ui
    #: declares. A constant rather than a ``fit_icon`` read of the button's
    #: height, which is Qt's 16777215 default on a button not yet capped by a
    #: .ui (a gigantic rasterization).
    _CONSTRAINT_ICON_SIZE = 16

    def _init_constraint_button(self, widget):
        """Dress a constraint button (themed glyph, no text, tooltip) and, where
        the host keeps constraints on, seed it from the host's live state.

        Re-run on every show (``refresh_on_show``): Maya's constraint is global
        session state its Modeling Toolkit can change behind the panel's back.
        Mirrored, never restored: a persisted "on" replayed on panel open would
        silently switch the constraint on (see ``mirror_app_state``). Where
        nothing persists (Blender) the button is a one-shot, so it is not
        checkable: it never reads "on" for a constraint that is not on.
        """
        constraint, label = self._CONSTRAINT_BUTTONS[widget.objectName()]
        on = self.tk.Selection.get_selection_constraints()
        persistent = on is not None
        widget.refresh_on_show = True
        widget.setCheckable(persistent)
        widget.setText("")
        self.sb.IconManager.set_icon(
            widget, constraint, size=self._CONSTRAINT_ICON_SIZE
        )
        widget.setToolTip(
            f"Selection constraint: {label}.\n"
            f"{self._CONSTRAINT_ACTION_HINT[persistent]}"
        )
        self.mirror_app_state(
            widget,
            (lambda: widget.setChecked(constraint in on)) if persistent else None,
        )

    def _apply_constraint(self, widget):
        """Switch *widget*'s constraint on or off (Maya) or expand the selection
        by it once (Blender), and report the constraints now on."""
        constraint = self._CONSTRAINT_BUTTONS[widget.objectName()][0]
        state = widget.isChecked() if widget.isCheckable() else True
        on = self.run_operation(self.tk.Selection.set_selection_constraint, constraint, state)
        if on is None:  # a refusal, or a one-shot expansion: nothing stays on
            return
        labels = [
            label for name, label in self._CONSTRAINT_BUTTONS.values() if name in on
        ]
        self.sb.message_box(
            f"Selection Constraints: <hl>{', '.join(labels) if labels else 'OFF'}</hl>"
        )

    def b002_init(self, widget):
        """Selection constraint: Angle."""
        self._init_constraint_button(widget)

    def b002(self, widget):
        """Selection constraint: Angle."""
        self._apply_constraint(widget)

    def b003_init(self, widget):
        """Selection constraint: Border."""
        self._init_constraint_button(widget)

    def b003(self, widget):
        """Selection constraint: Border."""
        self._apply_constraint(widget)

    def b004_init(self, widget):
        """Selection constraint: Edge Loop."""
        self._init_constraint_button(widget)

    def b004(self, widget):
        """Selection constraint: Edge Loop."""
        self._apply_constraint(widget)

    def b005_init(self, widget):
        """Selection constraint: Edge Ring."""
        self._init_constraint_button(widget)

    def b005(self, widget):
        """Selection constraint: Edge Ring."""
        self._apply_constraint(widget)

    def b006_init(self, widget):
        """Selection constraint: Shell."""
        self._init_constraint_button(widget)

    def b006(self, widget):
        """Selection constraint: Shell."""
        self._apply_constraint(widget)

    def b007_init(self, widget):
        """Selection constraint: UV Edge Loop."""
        self._init_constraint_button(widget)

    def b007(self, widget):
        """Selection constraint: UV Edge Loop."""
        self._apply_constraint(widget)

    # ------------------------------------------------------------------ chk004-007  viewport picking
    def chk004_init(self, widget):
        """Ignore Backfacing mirrors the host's live state (never restored);
        left at the .ui default where there is none to read (Blender with no 3D
        viewport)."""
        state = self.tk.Selection.get_ignore_backfacing()
        self.mirror_app_state(
            widget, None if state is None else (lambda: widget.setChecked(state))
        )

    def chk004(self, state, widget):
        """Ignore Backfacing: select only what faces the camera (Maya:
        camera-based selection; Blender: X-ray off)."""
        on = bool(state)
        self.tk.Selection.set_ignore_backfacing(on)
        self.sb.message_box(f"Ignore Backfacing <hl>{'ON' if on else 'OFF'}</hl>.")

    #: Select Style checkboxes -> the viewport tool each activates.
    _SELECT_STYLES = {
        "chk005": "Marquee Select",
        "chk006": "Lasso Select",
        "chk007": "Paint Select",
    }

    def _init_select_style(self, widget):
        """Seed a Select Style box from the host's active tool and opt it out of
        restore: the active tool is the host's, and a restored "on" would re-set
        the tool (and toast) every time the menu opens.

        Each box marks ITSELF: uitk's immediate init path runs slot-init then
        state-init per widget, and chk006 precedes chk005 in the .ui, so a
        sibling-marking init would run too late to stop chk006 restoring.
        Only a match is checked: the boxes form an exclusive group.
        """
        active = self.tk.UiUtils.current_tool() == self._SELECT_STYLES[
            widget.objectName()
        ]
        self.mirror_app_state(widget, (lambda: widget.setChecked(True)) if active else None)

    def chk005_init(self, widget):
        """Select Style: Marquee (and the three boxes' exclusive group)."""
        self.sb.create_button_groups(widget.ui, "chk005-7")
        self._init_select_style(widget)

    def chk006_init(self, widget):
        """Select Style: Lasso"""
        self._init_select_style(widget)

    def chk007_init(self, widget):
        """Select Style: Paint (Blender: Circle Select)"""
        self._init_select_style(widget)

    def _set_select_style(self, state, widget):
        if state:
            self.activate_tool(self._SELECT_STYLES[widget.objectName()])

    def chk005(self, state, widget):
        """Select Style: Marquee"""
        self._set_select_style(state, widget)

    def chk006(self, state, widget):
        """Select Style: Lasso"""
        self._set_select_style(state, widget)

    def chk007(self, state, widget):
        """Select Style: Paint"""
        self._set_select_style(state, widget)

    # ------------------------------------------------------------------ b001  Toggle Selectability
    def b001(self):
        """Toggle Selectability of the selected objects. Blender drops an object
        it makes unselectable from the selection, so there, with nothing
        selected, every unselectable object is made selectable again."""
        result = self.run_operation(
            self.tk.Selection.toggle_selectability,
            None,
            empty="Toggle Selectability needs a selection.",
        )
        if result:
            selectable, objects = result
            self.sb.message_box(
                f"Selectability <hl>{'ON' if selectable else 'OFF'}</hl> "
                f"({len(objects)} object(s))."
            )

    # ------------------------------------------------------------------ tb000  Select Nth
    def chk000(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk001-2")

    def chk001(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk000,chk002")

    def chk002(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk000-1")

    #: Select Nth's paths: ``(objectName, label, path, tooltip)``, in menu order.
    _EDGE_PATHS = (
        ("chk000", "Edge Ring", "edge_ring", "Select the edge ring through the selection."),
        (
            "chk001",
            "Edge Loop",
            "edge_loop",
            "Select the edge loop running through the selection.",
        ),
        (
            "chk021",
            "Edge Loop Path",
            "edge_loop_path",
            "The path along the loop between two selected edges or vertices.",
        ),
        (
            "chk002",
            "Shortest Edge Path",
            "shortest_path",
            "The shortest path between two selected edges or vertices.",
        ),
        (
            "chk010",
            "Border Edges",
            "border_edges",
            "Select the border edges of the selection.",
        ),
    )

    def tb000_init(self, widget):
        """Initialize Select Nth"""
        menu = widget.option_box.menu
        menu.setTitle("Select Nth")
        for name, label, path, tooltip in self._EDGE_PATHS:
            menu.add(
                "QRadioButton",
                setText=label,
                setObjectName=name,
                setChecked=path == "edge_loop",
                setToolTip=tooltip,
            )
        menu.add(
            "QSpinBox",
            setPrefix="Step: ",
            setObjectName="s003",
            set_limits=[1, 100],
            setValue=1,
            setToolTip="Keep every Nth component of the path.",
        )

    def tb000(self, widget):
        """Select Nth: select edge loops, rings or paths, keeping every Nth component."""
        menu = widget.option_box.menu
        path = next(
            (p for name, _, p, _ in self._EDGE_PATHS if getattr(menu, name).isChecked()),
            "edge_loop",
        )
        self.run_operation(
            self.tk.Selection.select_edge_path,
            None,
            path=path,
            step=menu.s003.value(),
            empty="<b>Nothing selected.</b><br>"
            "Select Nth needs an edge or vertex selection (Blender: of a mesh).",
        )

    # ------------------------------------------------------------------ tb001  Select Similar
    #: Select Similar's object metrics: ``(objectName, label, metric, checked,
    #: tooltip)``. objectNames are persisted state: never renumber them.
    _SIMILAR_METRICS = (
        ("chk011", "Vertex", "vertex", True, "The number of vertices."),
        ("chk012", "Edge", "edge", True, "The number of edges."),
        ("chk013", "Face", "face", True, "The number of faces."),
        ("chk014", "Triangle", "triangle", False, "The number of triangles."),
        (
            "chk015",
            "Shell",
            "shell",
            False,
            "The number of shells (disconnected pieces).",
        ),
        (
            "chk016",
            "Uv Coord",
            "uvcoord",
            False,
            "The number of UV coordinates (of the current UV set).",
        ),
        (
            "chk017",
            "Area",
            "area",
            False,
            "The surface area of the object's faces in local space.",
        ),
        (
            "chk018",
            "World Area",
            "world_area",
            True,
            "The surface area of the object's faces in world space.",
        ),
        (
            "chk019",
            "Bounding Box",
            "bounding_box",
            False,
            "The object's bounding-box dimensions (size only: position and "
            "orientation are ignored).",
        ),
    )

    def tb001_init(self, widget):
        """Initialize Select Similar"""
        menu = widget.option_box.menu
        menu.setTitle("Select Similar")
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 9999, 0.1, 3],
            setValue=0.0,
            setToolTip=(
                "The allowed difference in any of the compared results.\n"
                "ie. A tolerance of 4 allows for a difference of 4 components.\n"
                "ie. A tolerance of 0.05 allows for that amount of variance between "
                "any of the bounding box values.\n"
                "UV shells (a UV-shell selection; Blender: the UV editor in Island "
                "select mode): how much two shells' shapes may differ and still "
                "count as the same shell -- 0 = identical, 1 also absorbs the drift "
                "of two separately unfolded copies.\n"
                "Other components in Blender: the native Select Similar threshold, "
                "normalized 0-1 (larger values count as 1)."
            ),
        )
        for name, label, _, checked, tooltip in self._SIMILAR_METRICS:
            menu.add(
                "QCheckBox",
                setText=label,
                setObjectName=name,
                setChecked=checked,
                setToolTip=tooltip,
            )
        menu.add(
            "QCheckBox",
            setText="Include Original",
            setObjectName="chk020",
            setToolTip=(
                "Include the original selected object(s) / UV shell(s) in the "
                "final selection."
            ),
        )

    def tb001(self, widget):
        """Select Similar: objects by the checked metrics; with a UV-shell
        selection, the shells of the same topology and shape (what the UV
        panel's Stack (Similar) stacks); other components by the host's own
        Select Similar."""
        # An empty selection is a different failure from an empty result:
        # telling someone to raise the tolerance when they have not picked a
        # reference is worse than saying nothing.
        if (
            self.require_selection(
                "<b>Select Similar</b> needs a reference.<br>"
                "Select the object or components you want to find matches for."
            )
            is None
        ):
            return
        menu = widget.option_box.menu
        tolerance = menu.s000.value()
        metrics = {
            metric: getattr(menu, name).isChecked()
            for name, _, metric, _, _ in self._SIMILAR_METRICS
        }
        result = self.run_operation(
            self.tk.Selection.select_similar,
            None,
            tolerance=tolerance,
            include_original=menu.chk020.isChecked(),
            **metrics,
        )
        if not result:  # a refusal (already shown)
            return
        scope, matched = result
        if matched:
            return
        if scope == "objects":
            compared = [
                label
                for _, label, metric, _, _ in self._SIMILAR_METRICS
                if metrics[metric]
            ]
            self.sb.message_box(
                "<b>Select Similar</b> found no matches for "
                f"<hl>{', '.join(compared) or 'the default metrics'}</hl> "
                f"at a tolerance of <hl>{tolerance}</hl>.<br>"
                "Raise the tolerance, or clear metrics that vary between copies."
            )
        elif scope == "uv_shells":
            self.sb.message_box(
                "<b>Select Similar</b> found no other UV shell with the selected "
                f"shell's topology and shape at a tolerance of <hl>{tolerance}</hl>."
                "<br>Raise the tolerance to allow some shape drift."
            )

    # ------------------------------------------------------------------ tb002  Select Island
    #: Blender's Select Linked delimiters: ``objectName -> (label, delimiter)``.
    #: Growth also stops at these boundaries; Maya's island has none.
    _ISLAND_DELIMIT = {
        "chk022": ("By Seam", "SEAM"),
        "chk_island_sharp": ("By Sharp Edges", "SHARP"),
        "chk_island_normal": ("By Normal Direction", "NORMAL"),
        "chk_island_material": ("By Material", "MATERIAL"),
        "chk_island_uv": ("By UV Border", "UV"),
    }

    def tb002_init(self, widget):
        """Initialize Select Island"""
        menu = widget.option_box.menu
        menu.setTitle("Select Island")
        menu.add(
            "QCheckBox",
            setText="Lock Values",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Keep the three ranges in sync.",
        )
        ranges = [
            menu.add(
                "QDoubleSpinBox",
                setPrefix=f"{axis}: ",
                setObjectName=name,
                set_limits=[0, 1, 0.01, 2],
                setValue=0.05,
                setToolTip=f"How far a face's normal {axis.upper()} may differ "
                "from a selected face's and still join the island.",
            )
            for axis, name in (("x", "s002"), ("y", "s004"), ("z", "s005"))
        ]

        def sync(value):
            # Signals stay live so each synced range persists; Qt emits no
            # valueChanged for an unchanged value, which ends the cascade.
            if menu.chk003.isChecked():
                for spin in ranges:
                    spin.setValue(value)

        for spin in ranges:
            spin.valueChanged.connect(sync)

        for name, (label, delimiter) in self._ISLAND_DELIMIT.items():
            chk = menu.add(
                "QCheckBox",
                setText=label,
                setObjectName=name,
                setToolTip=f"Also stop the island at {delimiter.lower()} boundaries.",
            )
            chk.setProperty("requires", "blender")
            self.sb.apply_visibility_policy(chk)

    def tb002(self, widget):
        """Select Island: the contiguous faces, around the selected ones, whose
        normals are within the ranges."""
        menu = widget.option_box.menu
        self.run_operation(
            self.tk.Selection.select_island,
            None,
            range_x=menu.s002.value(),
            range_y=menu.s004.value(),
            range_z=menu.s005.value(),
            delimit={
                delimiter
                for name, (_, delimiter) in self._ISLAND_DELIMIT.items()
                if getattr(menu, name).isChecked()
            },
            empty="<b>Nothing selected.</b><br>"
            "Select Island needs a face selection (Blender: in Edit Mode).",
        )

    # ------------------------------------------------------------------ tb003  Select Edges By Angle
    def tb003_init(self, widget):
        """Initialize Select Edges By Angle"""
        menu = widget.option_box.menu
        menu.setTitle("Select Edges By Angle")
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Low:  ",
            setObjectName="s006",
            set_limits=[0, 180],
            setValue=70,
            setToolTip="The low end of the angle between an edge's two faces (degrees).",
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle High: ",
            setObjectName="s007",
            set_limits=[0, 180],
            setValue=160,
            setToolTip="The high end of the angle between an edge's two faces (degrees).",
        )

    def tb003(self, widget):
        """Select Edges By Angle: the selected meshes' edges within the range."""
        menu = widget.option_box.menu
        edges = self.run_operation(
            self.tk.EditUtils.select_edges_by_angle,
            None,
            low_angle=menu.s006.value(),
            high_angle=menu.s007.value(),
            empty="<b>Nothing selected.</b><br>Select Edges By Angle needs a mesh.",
        )
        if edges == 0:
            self.sb.message_box("No edges found in that angle range.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
