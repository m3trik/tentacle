# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from tentacle import SelectionMixin, SlotsMaya


class Selection(SelectionMixin, SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.ui = self.sb.loaded_ui.selection
        self.submenu = self.sb.loaded_ui.selection_submenu

    def list000_init(self, widget):
        """Select by Type: Hierarchical type list."""
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up" if submenu else "hover_menu")

        root = widget.add("By Type")

        # Settings entry, positioned nearest the trigger row in both hosts —
        # last in the submenu (expand_up: last-added sits at the bottom, by
        # the trigger), first in the panel (hover_menu fans right with its
        # top row aligned to the trigger): a
        # slot-wired button with a settings-gear prefix icon (set in
        # tb004_init) and no option box, so it stays a plain list row. Its
        # click is dispatched from list000 to open the scope / mode menu the
        # leaf actions read.
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

        categories = mtk.Selection.get_selection_categories()
        for category, types in categories.items():
            w = root.sublist.add(category)
            w.sublist.add(sorted(types))

        if submenu:
            self.add_slot_widget(root.sublist, **tb004_kwargs)

    @SlotsMaya.Signals("on_item_interacted")
    def list000(self, item):
        """Select by Type"""
        # Only leaf items (specific types) are actionable.
        # Root ("By Type") and category headers are navigation-only.
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        # The Settings row opens its scope/mode menu instead of acting as a
        # type filter. Two dispatch paths reach it, mutually exclusively: here
        # (plain event flow — the list consumes the release, so the button's
        # own clicked never fires) and its clicked (the marking menu fires a
        # menu-hosted leaf's clicked at release — it never routes a widget with
        # a clicked signal through on_item_interacted). Both delegate to tb004
        # so the menu opens exactly once in either context.
        if item.objectName() == "tb004":
            self.tb004(item)
            return

        selection_type = item.item_text()
        objects = self._by_type_scope_objects()
        if not objects:
            self.sb.message_box("Select by Type: no objects in the current scope.")
            return
        mode = self._by_type_mode()

        try:
            result = mtk.Selection.select_by_type(selection_type, objects, mode=mode)
            verb = {"add": "Added", "remove": "Removed"}.get(mode, "Selected")
            print(f"{verb} {len(result)} objects of type: {selection_type}")
        except ValueError:
            pass
        except Exception as e:
            self.sb.message_box(f"Error selecting by type '{selection_type}': {e}")

    def tb004_init(self, widget):
        """Select by Type settings menu.

        The row shows a settings-gear prefix icon and opens this menu on click
        (dispatched from ``list000``). The menu is the button's own MenuMixin
        menu — no option box (the gear would be redundant with the row click)
        and no apply button (the combos take effect the moment a leaf action
        reads them; MenuMixin menus default ``add_apply_button=False``).

        Self-labeling combos (the ``cmb_del_scope`` precedent — two radio
        groups in one menu would need manual QButtonGroup separation).
        """
        self.sb.IconManager.set_icon(widget, "settings")
        # Reproduce the prior option-box popup's config minus the apply button
        # (the sole change asked for): the row's own click opens it (dispatched
        # from list000), so no auto-trigger; the MenuMixin base defaults would
        # otherwise drop the header/defaults button and flip hide-on-leave.
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
        """Select by Type settings: open the scope/mode menu.

        Wired to the button's ``clicked`` (register_widget), so the marking
        menu — which fires a menu-hosted leaf's ``clicked`` at release-dispatch
        (``MarkingMenu._handle_widget_action``) — opens it; ``list000`` also
        calls this for the plain event-flow path. The two paths never both fire
        for one interaction.
        """
        widget.menu.show_as_popup(anchor_widget=widget, position="cursorPos")

    def _by_type_scope_objects(self):
        """The object pool Select by Type filters from, per the tb004 scope."""
        menu = self.submenu.tb004.menu
        scope = menu.cmb_bytype_scope.currentData() or "all"
        if scope == "selected":
            return cmds.ls(selection=True) or []
        if scope == "visible":
            return cmds.ls(visible=True) or []
        return cmds.ls() or []

    def _by_type_mode(self):
        """The selection mode Select by Type applies, per the tb004 setting."""
        menu = self.submenu.tb004.menu
        return menu.cmb_bytype_mode.currentData() or "replace"

    def cmb001_init(self, widget):
        """Reorder Selection Init"""
        widget.option_box.menu.setTitle("Reorder Selection")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reverse Order",
            setObjectName="chk009",
            setChecked=False,
            setToolTip="Reverse the reordered selection.",
        )
        # Get available reorder methods
        items = [
            "Name",
            "Hierarchy",
            "X Position",
            "Y Position",
            "Z Position",
            "Distance from Origin",
            "Volume",
            "Vertex Count",
            "Random",
            "Creation Time",
        ]
        widget.add(items, header="Reorder By:")

    def cmb001(self, index, widget):
        """Reorder Selection"""
        reverse = widget.option_box.menu.chk009.isChecked()

        # Map display names to method names
        method_map = {
            "Name": "name",
            "Hierarchy": "hierarchy",
            "X Position": "x",
            "Y Position": "y",
            "Z Position": "z",
            "Distance from Origin": "distance",
            "Volume": "volume",
            "Vertex Count": "vertex_count",
            "Random": "random",
            "Creation Time": "creation_time",
        }

        selected_option = widget.items[index]
        method = method_map.get(selected_option, "name")

        # Get current selection
        objects = cmds.ls(sl=True) or []
        if not objects:
            self.sb.message_box("No objects selected to reorder.")
            return

        # Reorder the objects
        reordered = mtk.reorder_objects(objects, method=method, reverse=reverse)

        # Reselect in new order
        if reordered:
            cmds.select(reordered)
            print(
                f"Reordered {len(reordered)} objects by {selected_option}{' (reversed)' if reverse else ''}"
            )

    # Convert To (list001): label -> conversion. The keys are the menu's rows,
    # arranged into category flyouts by SelectionMixin._CONVERT_TO_GROUPS
    # (Verts / Edges / Faces / UV's / Shell each convert on click and fan out
    # their related rows on hover). Every entry is Maya's own menu
    # command for that conversion (Polygons > Select > Convert Selection),
    # except Border Edges, which rides mtk.Components. The Blender fork's table
    # mirrors this one minus the two items it lacks (Vertex Faces, UV's),
    # ledgered in docs/parity_map.py.
    _CONVERT_TO_OPS = {
        "Verts": lambda self: mel.eval("PolySelectConvert 3"),
        "Vertex Faces": lambda self: mel.eval("PolySelectConvert 5"),
        "Vertex Perimeter": lambda self: mel.eval("ConvertSelectionToVertexPerimeter"),
        "Edges": lambda self: mel.eval("PolySelectConvert 2"),
        "Edge Loop": lambda self: mel.eval("SelectEdgeLoopSp"),
        "Edge Ring": lambda self: mel.eval("SelectEdgeRingSp"),
        "Contained Edges": lambda self: mel.eval("PolySelectConvert 20"),
        "Edge Perimeter": lambda self: mel.eval("ConvertSelectionToEdgePerimeter"),
        "Border Edges": lambda self: self._convert_to_border_edges(),
        "Faces": lambda self: mel.eval("PolySelectConvert 1"),
        "Face Path": lambda self: mel.eval('polySelectEdges "edgeRing"'),
        "Contained Faces": lambda self: mel.eval("PolySelectConvert 10"),
        "Face Perimeter": lambda self: mel.eval("polySelectFacePerimeter"),
        "UV's": lambda self: mel.eval("PolySelectConvert 4"),
        "UV Shell": lambda self: mel.eval("polySelectBorderShell 0"),
        "UV Shell Border": lambda self: mel.eval("polySelectBorderShell 1"),
        "UV Perimeter": lambda self: mel.eval("ConvertSelectionToUVPerimeter"),
        "UV Edge Loop": lambda self: mel.eval('polySelectEdges "edgeUVLoopOrBorder"'),
        "Shell": lambda self: mel.eval("polyConvertToShell"),
        "Shell Border": lambda self: mel.eval("polyConvertToShellBorder"),
    }

    @SlotsMaya.Signals("on_item_interacted")
    def list001(self, item):
        """Convert To: convert the component selection to verts, edges, faces, UVs, or shells."""
        self._dispatch_convert_to(item)

    def _convert_to_border_edges(self):
        """Convert To > Border Edges: the selection's naked (one-face) edges."""
        selection = cmds.ls(sl=True) or []
        all_edges = mtk.Components.get_components(selection, "edges")
        if not all_edges:
            self.sb.message_box("No valid selection to convert to border edges.")
            return
        cmds.select(mtk.Components.get_border_components(all_edges))

    # Selection constraints (b002-b007): objectName -> the polySelectConstraint
    # flags the button owns. Each constraint is its own independent flag on
    # Maya's one global constraint state (verified: setting one leaves the
    # others as they were), which is what lets more than one be enabled at a
    # time — Maya's own Modeling Toolkit menu (dR_setSelConst) writes all of
    # them on every pick, so it can only ever show one. Border is two flags
    # because MTK sets both (-bo -bp) for it. Glyph + label per button live in
    # SelectionMixin._CONSTRAINT_BUTTONS.
    _CONSTRAINT_FLAGS = {
        "b002": ("anglePropagation",),
        "b003": ("border", "borderPropagation"),
        "b004": ("loopPropagation",),
        "b005": ("ringPropagation",),
        "b006": ("shell",),
        "b007": ("uvEdgeLoopPropagation",),
    }
    _CONSTRAINT_ACTION_HINT = (
        "Toggle: constrains what drag-selection picks up while on. "
        "Several can be on at once."
    )

    def _constraint_is_on(self, widget):
        """Live state of *widget*'s constraint — Maya owns it, not QSettings."""
        flag = self._CONSTRAINT_FLAGS[widget.objectName()][0]
        return bool(cmds.polySelectConstraint(q=True, **{flag: True}))

    def _init_constraint_toggle(self, widget):
        """Dress the button and seed its checked state from Maya's live constraint.

        Re-run on every show (``refresh_on_show``): the constraint is global
        session state the Modeling Toolkit can change behind the panel's back,
        so a one-time seed would go stale. Mirrored, never restored — a
        persisted "on" replayed on panel open would silently switch the
        constraint on (see ``mirror_app_state``).
        """
        widget.refresh_on_show = True
        self._init_constraint_button(widget)
        self.mirror_app_state(
            widget, lambda: widget.setChecked(self._constraint_is_on(widget))
        )

    def _toggle_constraint(self, widget):
        """Write the button's checked state to its constraint flag(s) and report
        the full set now on, so a multi-constraint state reads at a glance."""
        state = widget.isChecked()
        flags = self._CONSTRAINT_FLAGS[widget.objectName()]
        cmds.polySelectConstraint(**{f: state for f in flags})
        # Keep the Modeling Toolkit's own constraint field honest when it is up.
        # The proc only exists once drInit.mel has been sourced (MTK panel built
        # in a GUI session); probing with `exists` first keeps the script editor
        # quiet — a bare failing mel.eval echoes "Error:" there even when Python
        # catches the RuntimeError.
        if mel.eval('exists "dR_updateSelConstField"'):
            try:
                mel.eval("dR_updateSelConstField")
            except RuntimeError:
                pass  # its textField torn down since — nothing to refresh
        on = [
            self._constraint_label(w)
            for name in self._CONSTRAINT_FLAGS
            for w in (getattr(widget.ui, name, None),)
            if w is not None and w.isChecked()
        ]
        self.sb.message_box(
            f"Selection Constraints: <hl>{', '.join(on) if on else 'OFF'}</hl>"
        )

    def b002_init(self, widget):
        """Selection constraint: Angle."""
        self._init_constraint_toggle(widget)

    def b002(self, widget):
        """Selection constraint: Angle (toggle)."""
        self._toggle_constraint(widget)

    def b003_init(self, widget):
        """Selection constraint: Border."""
        self._init_constraint_toggle(widget)

    def b003(self, widget):
        """Selection constraint: Border (toggle)."""
        self._toggle_constraint(widget)

    def b004_init(self, widget):
        """Selection constraint: Edge Loop."""
        self._init_constraint_toggle(widget)

    def b004(self, widget):
        """Selection constraint: Edge Loop (toggle)."""
        self._toggle_constraint(widget)

    def b005_init(self, widget):
        """Selection constraint: Edge Ring."""
        self._init_constraint_toggle(widget)

    def b005(self, widget):
        """Selection constraint: Edge Ring (toggle)."""
        self._toggle_constraint(widget)

    def b006_init(self, widget):
        """Selection constraint: Shell."""
        self._init_constraint_toggle(widget)

    def b006(self, widget):
        """Selection constraint: Shell (toggle)."""
        self._toggle_constraint(widget)

    def b007_init(self, widget):
        """Selection constraint: UV Edge Loop."""
        self._init_constraint_toggle(widget)

    def b007(self, widget):
        """Selection constraint: UV Edge Loop (toggle)."""
        self._toggle_constraint(widget)

    def chk000(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk001-2")

    def chk001(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk000,chk002")

    def chk002(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk000-1")

    def chk005_init(self, widget):
        """Create button group for radioboxes chk005, chk006, chk007"""
        self.sb.create_button_groups(widget.ui, "chk005-7")

        ctx = self.get_selection_tool()
        if ctx == "selectSuperContext":
            widget.ui.chk005.setChecked(True)
        elif ctx == "lassoSelectContext":
            widget.ui.chk006.setChecked(True)
        elif ctx == "artSelectContext":
            widget.ui.chk007.setChecked(True)

    def chk005(self, state, widget):
        """Select Style: Marquee"""
        if state:
            self.set_selection_tool("selectSuperContext")

    def chk006(self, state, widget):
        """Select Style: Lasso"""
        if state:
            self.set_selection_tool("lassoSelectContext")

    def chk007(self, state, widget):
        """Select Style: Paint"""
        if state:
            self.set_selection_tool("artSelectContext")

    def chk004(self, state, widget):
        """Ignore Backfacing (Camera Based Selection)"""
        if state:
            cmds.selectPref(useDepth=True)
            self.sb.message_box("Camera-based selection <hl>ON</hl>.")
        else:
            cmds.selectPref(useDepth=False)
            self.sb.message_box("Camera-based selection <hl>OFF</hl>.")

    def chkxxx(self, **kwargs):
        """Transform Constraints: Constraint CheckBoxes"""
        widget = kwargs.get("widget")
        state = kwargs.get("state")
        try:
            cmds.select(widget.text(), deselect=(not state))
        except KeyError:
            pass

    def tb000_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Edge Ring",
            setObjectName="chk000",
            setToolTip="Select component ring.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Edge Loop",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Select all contiguous components that form a loop with the current selection.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Edge Loop Path",
            setObjectName="chk021",
            setToolTip="The path along loop between two selected edges, vertices or UV's.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Shortest Edge Path",
            setObjectName="chk002",
            setToolTip="The shortest component path between two selected edges, vertices or UV's.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Border Edges",
            setObjectName="chk010",
            setToolTip="Select the object(s) border edges.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Step: ",
            setObjectName="s003",
            set_limits=[1, 100],
            setValue=1,
            setToolTip="Step Amount.",
        )

    def tb000(self, widget):
        """Select Nth: select edge loops/rings or shortest paths, stepping every Nth component."""
        edgeRing = widget.option_box.menu.chk000.isChecked()
        edgeLoop = widget.option_box.menu.chk001.isChecked()
        pathAlongLoop = widget.option_box.menu.chk021.isChecked()
        shortestPath = widget.option_box.menu.chk002.isChecked()
        borderEdges = widget.option_box.menu.chk010.isChecked()
        step = widget.option_box.menu.s003.value()

        selection = cmds.ls(orderedSelection=True) or []
        if not selection:
            self.sb.message_box("Operation requires a valid selection.")
            return

        result = []
        if edgeRing:
            result = mtk.Components.get_edge_path(selection, "edgeRing")

        elif edgeLoop:
            result = mtk.Components.get_edge_path(selection, "edgeLoop")

        elif pathAlongLoop:
            result = mtk.Components.get_edge_path(selection, "edgeLoopPath")

        elif shortestPath:
            result = mtk.Components.get_shortest_path(selection)

        elif borderEdges:
            all_edges = mtk.Components.get_components(selection, "edges")
            result = mtk.Components.get_border_components(all_edges)

        cmds.select(result[::step])

    # Select Similar's comparison metrics: (objectName, label, polyEvaluate
    # kwarg, checked by default, tooltip). One table so the option box, the
    # engine call and the no-match report can't drift apart. objectNames are
    # persisted state — never renumber them. Mirrors the Blender fork's
    # ``_SIMILAR_CRITERIA``.
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
            "The number of uv coordinates (for the current map).",
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
            "worldArea",
            True,
            "The surface area of the object's faces in world space.",
        ),
        (
            "chk019",
            "Bounding Box",
            "boundingBox",
            False,
            "The object's bounding box dimensions (size only — position and "
            "orientation are ignored).",
        ),
    )

    def tb001_init(self, widget):
        """ """
        menu = widget.option_box.menu
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
                "UV shells (a UV / UV-shell selection): how much two shells' shapes "
                "may differ and still count as the same shell -- 0 = identical, "
                "1 also absorbs the drift of two separately unfolded copies."
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
        """Select Similar.

        Object mode: geometry metrics (``mtk.get_similar_mesh``). A UV / UV-shell
        selection: shells of the same topology and shape as the selected shell(s)
        -- Maya's ``polyUVStackSimilarShells`` similarity, so what this selects is
        exactly what the UV panel's Stack (Similar) will stack -- searched across
        the hilited (component-mode) meshes without moving anything
        (``mtk.UvUtils.get_similar_uv_shells``). Other components: Maya's
        ``doSelectSimilar``.
        """
        menu = widget.option_box.menu
        tolerance = menu.s000.value()
        metrics = {
            kwarg: getattr(menu, name).isChecked()
            for name, _, kwarg, _, _ in self._SIMILAR_METRICS
        }

        if cmds.selectMode(q=True, object=True):
            # An empty selection is a different failure from an empty result —
            # telling someone to raise the tolerance when they haven't picked a
            # reference object is worse than saying nothing.
            selection = self.require_selection(
                "<b>Select Similar</b> needs a reference object.<br>"
                "Select the object you want to find matches for.",
                objectsOnly=True,
                type="transform",
            )
            if selection is None:
                return

            result = mtk.get_similar_mesh(
                selection,
                tolerance=tolerance,
                inc_orig=menu.chk020.isChecked(),
                select=True,
                **metrics,
            )
            # A no-match either silently clears the selection or (with Include
            # Original on) leaves it untouched — both read as "the button did
            # nothing". Compare against the originals rather than the returned
            # list so the report doesn't depend on that flag. `or []` is
            # load-bearing: get_similar_mesh returns None for a single-object
            # query with no matches, and cmds.ls(None) lists the entire scene.
            originals = set(cmds.ls(selection, long=True))
            matched = [
                m for m in cmds.ls(result or [], long=True) if m not in originals
            ]
            if not matched:
                compared = [
                    label
                    for _, label, kwarg, _, _ in self._SIMILAR_METRICS
                    if metrics[kwarg]
                ]
                self.sb.message_box(
                    "<b>Select Similar</b> found no matches for "
                    f"<hl>{', '.join(compared) or 'the default metrics'}</hl> "
                    f"at a tolerance of <hl>{tolerance}</hl>.<br>"
                    "Raise the tolerance, or clear metrics that vary between copies."
                )
        elif cmds.filterExpand(selectionMask=35):  # UV components (UV / UV-shell modes)
            reference = cmds.ls(sl=True) or []
            # The meshes being edited: hilited in component mode; fall back to
            # the shells' own objects (a UV selection made by script).
            candidates = cmds.ls(hilite=True) or cmds.ls(reference, objectsOnly=True)
            shells = mtk.UvUtils.get_similar_uv_shells(
                reference, candidates, tolerance=tolerance
            )
            if not shells:
                self.sb.message_box(
                    "<b>Select Similar</b> found no other UV shell with the "
                    f"selected shell's topology and shape at a tolerance of "
                    f"<hl>{tolerance}</hl>.<br>Raise the tolerance to allow "
                    "some shape drift."
                )
                return
            uvs = [uv for shell in shells for uv in shell]
            # One mode flag per call: `add` and `replace` are mutually
            # exclusive, and every other cmds.select in the monorepo passes
            # exactly one.
            if menu.chk020.isChecked():
                cmds.select(uvs, add=True)
            else:
                cmds.select(uvs, replace=True)
        else:
            try:
                mel.eval(f"doSelectSimilar 1 {{{tolerance}}};")
            except RuntimeError:
                # doSelectSimilar only supports a subset of component types and
                # raises (e.g. "Cannot convert data of type float[] to type
                # string[]") on unsupported ones like edges/vertices. This is an
                # expected, handled case — surface a friendly note instead of a
                # raw traceback.
                sel = cmds.ls(sl=1) or []
                comp = (
                    mtk.Components.get_component_type(sel[0], "plural") if sel else None
                )
                detail = f"<hl>{comp}</hl>" if comp else "the current selection type"
                self.sb.message_box(
                    f"<b>Select Similar</b> isn't supported for {detail}.<br>"
                    "Try a <hl>face</hl> or <hl>object</hl> selection instead."
                )

    def tb002_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lock Values",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Keep values in sync.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="x: ",
            setObjectName="s002",
            set_limits=[0, 1, 0.01, 2],
            setValue=0.05,
            setToolTip="Normal X range.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="y: ",
            setObjectName="s004",
            set_limits=[0, 1, 0.01, 2],
            setValue=0.05,
            setToolTip="Normal Y range.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="z: ",
            setObjectName="s005",
            set_limits=[0, 1, 0.01, 2],
            setValue=0.05,
            setToolTip="Normal Z range.",
        )

        def update_normal_ranges(value, widget):
            """Update all spin boxes if checkbox is checked."""
            if widget.option_box.menu.chk003.isChecked():
                # Update all spin boxes
                widget.option_box.menu.s002.setValue(value)
                widget.option_box.menu.s004.setValue(value)
                widget.option_box.menu.s005.setValue(value)

        # Connect signals
        widget.option_box.menu.s002.valueChanged.connect(
            lambda v: update_normal_ranges(v, widget)
        )
        widget.option_box.menu.s004.valueChanged.connect(
            lambda v: update_normal_ranges(v, widget)
        )
        widget.option_box.menu.s005.valueChanged.connect(
            lambda v: update_normal_ranges(v, widget)
        )

    def tb002(self, widget):
        """Select Island: Select Polygon Face Island"""
        range_x = float(widget.option_box.menu.s002.value())
        range_y = float(widget.option_box.menu.s004.value())
        range_z = float(widget.option_box.menu.s005.value())

        sel = cmds.ls(sl=1) or []
        selected_faces = (
            cmds.ls(
                mtk.Components.get_components(
                    sel, component_type="faces", flatten=True
                )
                or [],
                flatten=True,
            )
            or []
        )
        if not selected_faces:
            self.sb.message_box("The operation requires a face selection.")
            return

        similar_faces = mtk.Components.get_faces_with_similar_normals(
            selected_faces, range_x=range_x, range_y=range_y, range_z=range_z
        )
        islands = mtk.Components.get_contiguous_islands(similar_faces)
        selected_set = set(selected_faces)
        matching = [f for island in islands if island & selected_set for f in island]
        cmds.select(matching)

    def tb003_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Low:  ",
            setObjectName="s006",
            set_limits=[0, 180],
            setValue=70,
            setToolTip="Normal angle low range.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle High: ",
            setObjectName="s007",
            set_limits=[0, 180],
            setValue=160,
            setToolTip="Normal angle high range.",
        )

    def tb003(self, widget):
        """Select Edges By Angle"""
        angleLow = widget.option_box.menu.s006.value()
        angleHigh = widget.option_box.menu.s007.value()

        objects = cmds.ls(sl=1, objectsOnly=1) or []
        edges = mtk.Components.get_edges_by_normal_angle(
            objects, low_angle=angleLow, high_angle=angleHigh
        )
        cmds.select(edges)

        cmds.selectMode(component=1)
        cmds.selectType(edge=1)

    def b001(self):
        """Toggle Selectability"""
        mtk.Macros.m_toggle_selectability()

    @staticmethod
    def get_selection_tool():
        """Queries the current selection tool in Maya.

        Returns:
            str: The current selection tool.
        """
        try:
            return cmds.currentCtx()
        except Exception as e:
            print(f"# Error: {e}")
            return None

    @staticmethod
    def set_selection_tool(tool):
        """Sets the selection tool in Maya.

        Parameters:
            tool (str): The tool to set. Should be one of 'selectSuperContext', 'artSelectContext', 'lassoToolContext'.
        """
        valid_tools = ["selectSuperContext", "lassoSelectContext", "artSelectContext"]
        if tool not in valid_tools:
            print(f"Invalid tool. Tool should be one of {','.join(valid_tools)}.")
            return

        try:
            cmds.setToolTo(tool)
        except Exception as e:
            print(f"# Error: {e}")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
