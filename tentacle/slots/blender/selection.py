# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle import SelectionMixin, SlotsBlender


class Selection(SelectionMixin, SlotsBlender):
    """Blender port of the shared ``selection`` menu.

    Per the capability map (BLENDER_PORT_PLAN §5), selection maps almost entirely to **native
    Blender operators**, so most handlers call ``bpy.ops`` directly (proven to work from the Qt
    event-pump context); select-by-type (``list000``) rides ``btk.Selection`` -- a full mirror of
    mayatk's ``Selection._SELECTION_CONFIG`` category breadth (Animation/Dynamics/Geometry/
    Hierarchy/Scene/UV), built from Object-level bpy primitives instead of Maya's string-node type
    lookups; the selection-constraint icon row (``b002``-``b007``) becomes one-shot selection
    expansion (no modal analogue). Reorder Selection rides the rolled ``btk.SelectionOrder`` tracker +
    ``btk.reorder_objects`` (Blender records no object click order natively; the tracker
    maintains one).
    """

    # Maya "Marquee/Lasso/Paint" select styles -> Blender's box/lasso/circle select tools.
    _SELECT_TOOLS = {
        "chk005": ("builtin.select_box", "Box Select"),
        "chk006": ("builtin.select_lasso", "Lasso Select"),
        "chk007": ("builtin.select_circle", "Circle Select"),
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.ui = self.sb.loaded_ui.selection
        self.submenu = self.sb.loaded_ui.selection_submenu

    # ------------------------------------------------------------------ tb000  Select Nth
    def tb000_init(self, widget):
        widget.option_box.menu.add(
            "QRadioButton", setText="Edge Ring", setObjectName="chk000",
            setToolTip="Select component ring.",
        )
        widget.option_box.menu.add(
            "QRadioButton", setText="Edge Loop", setObjectName="chk001", setChecked=True,
            setToolTip="Select the edge loop running through the selection.",
        )
        widget.option_box.menu.add(
            "QRadioButton", setText="Edge Loop Path", setObjectName="chk021",
            setToolTip="The loop path between two selected edges/verts.",
        )
        widget.option_box.menu.add(
            "QRadioButton", setText="Shortest Edge Path", setObjectName="chk002",
            setToolTip="The shortest component path between two selected edges/verts.",
        )
        widget.option_box.menu.add(
            "QRadioButton", setText="Border Edges", setObjectName="chk010",
            setToolTip="Select the border edges of the current face region.",
        )
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Step: ", setObjectName="s003",
            set_limits=[1, 100], setValue=1, setToolTip="Select every Nth component.",
        )

    def tb000(self, widget):
        """Select Nth"""
        m = widget.option_box.menu
        # The path branches run on the user's two picked verts/edges — forcing edge mode
        # there would rebuild the selection and clear the select history the shortest-path
        # op reads, so only ring/loop/border (edge-product branches) force "EDGE".
        needs_edge = m.chk000.isChecked() or m.chk001.isChecked() or m.chk010.isChecked()
        if not self.ensure_edit_mode("MESH", "EDGE" if needs_edge else None):
            self.sb.message_box("Select Nth requires a mesh.")
            return
        if m.chk000.isChecked():            # Edge Ring
            btk.Selection.loop_multi_select(ring=True)
        elif m.chk001.isChecked():          # Edge Loop
            btk.Selection.loop_multi_select()
        elif m.chk021.isChecked() or m.chk002.isChecked():   # Loop / Shortest path
            try:
                bpy.ops.mesh.shortest_path_select()
            except RuntimeError as e:
                self.sb.message_box(str(e))
        elif m.chk010.isChecked():          # Border edges
            bpy.ops.mesh.region_to_loop()

        step = m.s003.value()
        if step > 1:                        # keep 1 of every `step` (checker deselect)
            try:
                # Headless-verified (Blender 5.1): select_nth(skip=step-1, nth=1) keeps 1 of
                # every `step` (12-vert circle, skip=3/nth=1 -> 3 kept) — Maya-parity with
                # result[::step]. The RNA labels ("Selected"/"Deselected") suggest the
                # opposite mapping; trust the measurement, not the labels.
                bpy.ops.mesh.select_nth(skip=step - 1, nth=1)
            except RuntimeError as e:
                self.sb.message_box(str(e))

    # ------------------------------------------------------------------ tb001  Select Similar
    # Maya offers a fixed set of similarity criteria (Area, Normal, …); Blender's
    # ``mesh.select_similar`` takes ONE ``type`` whose valid values depend on the active
    # component mode, so we expose a mode-aware combo (label -> {select-mode: enum}). The combo
    # objectName is Blender-specific (Maya used per-criterion checkboxes — a different model).
    # Component-mode (Edit) fallback: Maya's tb001 runs object-level Select Similar by the
    # checkboxes below, and a generic ``doSelectSimilar`` in component mode (no per-type UI). The
    # blender analogue picks a sensible native ``select_similar`` type for the active component mode.
    _COMPONENT_DEFAULT = {"VERT": "NORMAL", "EDGE": "LENGTH", "FACE": "AREA"}

    # (objectName, label, tooltip, default-checked) for the object-similarity criteria — Maya's
    # widgets/objectNames, backed by ``btk.get_similar_mesh`` (polyEvaluate-metric parity).
    _SIMILAR_CRITERIA = (
        ("chk011", "Vertex", "The number of vertices.", True),
        ("chk012", "Edge", "The number of edges.", True),
        ("chk013", "Face", "The number of faces.", True),
        ("chk014", "Triangle", "The number of triangles.", False),
        ("chk015", "Shell", "The number of shells (disconnected pieces).", False),
        ("chk016", "Uv Coord", "The number of UV coordinates.", False),
        ("chk017", "Area", "The surface area of the faces in local space.", False),
        ("chk018", "World Area", "The surface area of the faces in world space.", True),
        ("chk019", "Bounding Box", "The object's bounding-box dimensions.", False),
        ("chk020", "Include Original", "Include the originally selected object(s) in the result.", False),
    )

    def tb001_init(self, widget):
        widget.option_box.menu.setTitle("Select Similar")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Tolerance: ", setObjectName="s000",
            set_limits=[0, 9999, 0.1, 3], setValue=0.0,
            setToolTip="The allowed difference in any compared metric (e.g. 4 allows a 4-component "
            "difference; 0.05 allows that much variance between bounding-box values).\n"
            "In Edit Mode the value feeds Blender's native select_similar threshold, which is "
            "normalized 0-1 (larger values are clamped to 1).\n"
            "UV shells (UV editor in Island select mode): how much two shells' shapes may "
            "differ and still count as the same shell -- 0 = identical, 1 also absorbs the "
            "drift of two separately unfolded copies.",
        )
        for name, label, tip, checked in self._SIMILAR_CRITERIA:
            widget.option_box.menu.add(
                "QCheckBox", setText=label, setObjectName=name, setChecked=checked, setToolTip=tip,
            )

    @staticmethod
    def _uv_island_select_mode():
        """True when the UV editor is in Island select mode — the analogue of Maya's UV-shell
        selection type. Blender 5 made it the ``use_uv_select_island`` toggle; 4.x had it as
        the ``uv_select_mode`` enum's ``ISLAND`` value."""
        ts = bpy.context.scene.tool_settings
        return bool(getattr(ts, "use_uv_select_island", False)) or (
            getattr(ts, "uv_select_mode", "") == "ISLAND"
        )

    def tb001(self, widget):
        """Select Similar — object-level similarity by topology / area / bounding-box metrics
        (Maya parity, via ``btk.get_similar_mesh``); in Edit mode with the UV editor in Island
        select mode, the UV shells sharing the selected shell's topology and shape
        (``btk.get_similar_uv_shells`` -- the Stack (Similar) oracle, Maya's UV-shell branch);
        otherwise Blender's native component ``select_similar``."""
        m = widget.option_box.menu
        obj = self.active_object()
        if obj and obj.mode == "EDIT":
            if self._uv_island_select_mode():
                found = btk.get_similar_uv_shells(
                    [o for o in self.selected_objects() if o.type == "MESH"],
                    tolerance=m.s000.value(),
                    include_reference=m.chk020.isChecked(),
                    select=True,
                )
                if not found:
                    self.sb.message_box(
                        "<b>Select Similar</b> found no other UV shell with the selected "
                        f"shell's topology and shape at a tolerance of <hl>{m.s000.value()}</hl>."
                        "<br>Raise the tolerance to allow some shape drift."
                    )
                return
            vert, edge, face = bpy.context.tool_settings.mesh_select_mode
            mode = "FACE" if face else "EDGE" if edge else "VERT"
            try:
                bpy.ops.mesh.select_similar(
                    type=self._COMPONENT_DEFAULT[mode],
                    # Native threshold is a normalized 0-1 tolerance (RNA hard range) — the
                    # component-count tolerances documented for object mode don't apply here.
                    threshold=min(max(m.s000.value(), 0.0), 1.0),
                )
            except RuntimeError as e:
                self.sb.message_box(str(e))
            return
        matched = btk.get_similar_mesh(
            self.selected_objects(),
            tolerance=m.s000.value(),
            inc_orig=m.chk020.isChecked(),
            select=True,
            vertex=m.chk011.isChecked(),
            edge=m.chk012.isChecked(),
            face=m.chk013.isChecked(),
            triangle=m.chk014.isChecked(),
            shell=m.chk015.isChecked(),
            uvcoord=m.chk016.isChecked(),
            area=m.chk017.isChecked(),
            world_area=m.chk018.isChecked(),
            bounding_box=m.chk019.isChecked(),
        )
        if not matched:
            self.sb.message_box(
                "No similar objects found (select a reference object and enable a criterion)."
            )

    # ------------------------------------------------------------------ tb002  Select Island
    # Native ``select_linked`` delimiters {objectName: (label, delimit enum)}. By Normal is the
    # direct analogue of Maya's "island within a normal range" (growth stops at normal
    # discontinuities). objectNames are Blender-specific (Maya's island option box used a
    # Lock-Values + normal-range model).
    _ISLAND_DELIMIT = {
        "chk022": ("By Seam", "SEAM"),
        "chk_island_sharp": ("By Sharp Edges", "SHARP"),
        "chk_island_normal": ("By Normal Angle", "NORMAL"),
        "chk_island_material": ("By Material", "MATERIAL"),
        "chk_island_uv": ("By UV Border", "UV"),
    }

    def tb002_init(self, widget):
        widget.option_box.menu.setTitle("Select Island")
        for name, (label, delim) in self._ISLAND_DELIMIT.items():
            widget.option_box.menu.add(
                "QCheckBox", setText=label, setObjectName=name,
                setToolTip=f"Stop the island growth at {delim.lower()} boundaries.",
            )

    def tb002(self, widget):
        """Select Island (connected region; growth stopped at the checked boundaries)."""
        if not self.ensure_edit_mode("MESH"):
            self.sb.message_box("Select Island requires a mesh.")
            return
        m = widget.option_box.menu
        delimit = {
            delim for name, (_label, delim) in self._ISLAND_DELIMIT.items()
            if getattr(m, name).isChecked()
        }
        bpy.ops.mesh.select_linked(delimit=delimit)

    # ------------------------------------------------------------------ tb003  Select Edges By Angle
    def tb003_init(self, widget):
        m = widget.option_box.menu
        m.add(
            "QDoubleSpinBox", setPrefix="Angle Low:  ", setObjectName="s006",
            set_limits=[0, 180], setValue=70,
            setToolTip="Lower bound of the edge dihedral-angle range (degrees).",
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Angle High: ", setObjectName="s007",
            set_limits=[0, 180], setValue=160,
            setToolTip="Upper bound of the edge dihedral-angle range (degrees).",
        )

    def tb003(self, widget):
        """Select Edges By Angle (within the Low–High range, via ``btk.select_edges_by_angle``)."""
        m = widget.option_box.menu
        obj = self.ensure_edit_mode("MESH", "EDGE")
        if not obj:
            self.sb.message_box("Select Edges By Angle requires a mesh.")
            return
        n = btk.select_edges_by_angle(obj, low_angle=m.s006.value(), high_angle=m.s007.value())
        if not n:
            self.sb.message_box("No edges found in that angle range.")

    # ------------------------------------------------------------------ list001  Convert To
    # Mirror of Maya's 20-item Convert-To list, minus 2 ledgered in tentacle/docs/parity_map.py
    # (HANDLERS["selection"]): Vertex Faces (Maya's vtxFace sub-component -- a per-corner
    # split-normal-style component with no Blender selection-mode analogue) and UV's (Maya's
    # .map[] component, only selectable from the UV Editor's own mode, not a 3D-viewport
    # component type). The UV-domain conversions UV Shell / UV Shell Border / UV Perimeter /
    # UV Edge Loop ARE ported as real bmesh UV-graph helpers on ``btk.Selection`` (a UV-island
    # boundary = mesh-open edge or a UV seam splitting a manifold surface in UV space).
    # Touching-vs-contained (plain "Faces"/"Edges" vs. "Contained Faces"/"Contained Edges") is a
    # single native ``use_expand`` flag -- see ``btk.Selection.convert_to``'s docstring;
    # Perimeter/Path/Border items have no single native op and are real bmesh helpers.
    #
    # label -> op(obj): every entry acts on the edit-mode mesh ``_run_convert_to`` resolves.
    # The keys are the menu's rows, grouped into category flyouts by
    # SelectionMixin._CONVERT_TO_GROUPS; the "UV's" category has no op here (see above),
    # so its row is a navigation-only header for the four UV conversions.
    _CONVERT_TO_OPS = {
        "Verts": lambda obj: bpy.ops.mesh.select_mode(type="VERT"),
        "Vertex Perimeter": lambda obj: btk.Selection.select_vertex_perimeter(obj),
        "Edges": lambda obj: btk.Selection.convert_to(obj, "EDGE"),
        "Edge Loop": lambda obj: btk.Selection.loop_multi_select(),
        "Edge Ring": lambda obj: btk.Selection.loop_multi_select(ring=True),
        "Contained Edges": lambda obj: btk.Selection.convert_to(obj, "EDGE", contained=True),
        "Edge Perimeter": lambda obj: btk.Selection.select_edge_perimeter(obj),
        "Border Edges": lambda obj: btk.Selection.select_border_edges(obj),
        "Faces": lambda obj: btk.Selection.convert_to(obj, "FACE"),
        "Face Path": lambda obj: btk.Selection.select_face_path(obj),
        "Contained Faces": lambda obj: btk.Selection.convert_to(obj, "FACE", contained=True),
        "Face Perimeter": lambda obj: btk.Selection.select_face_perimeter(obj),
        "UV Shell": lambda obj: btk.Selection.select_uv_shell(obj),
        "UV Shell Border": lambda obj: btk.Selection.select_uv_shell_border(obj),
        "UV Perimeter": lambda obj: btk.Selection.select_uv_perimeter(obj),
        "UV Edge Loop": lambda obj: btk.Selection.select_uv_edge_loop(obj),
        "Shell": lambda obj: bpy.ops.mesh.select_linked(),
        "Shell Border": lambda obj: btk.Selection.select_shell_border(obj),
    }

    @SlotsBlender.Signals("on_item_interacted")
    def list001(self, item):
        """Convert the current selection to another component type (Maya Convert-To parity)."""
        self._dispatch_convert_to(item)

    def _run_on_edit_mesh(self, op, mask=None, missing="This operation requires a mesh in Edit Mode."):
        """Run ``op(obj)`` against the edit-mode mesh (``ensure_edit_mode``), optionally
        forcing the component *mask*; *missing* is the message when there is no mesh to
        edit. A bmesh helper's / operator's RuntimeError is user feedback, not a traceback.
        Shared by Convert To and the constraint row — both are "one op on the edit mesh"."""
        obj = self.ensure_edit_mode("MESH", mask)
        if not obj:
            self.sb.message_box(missing)
            return
        try:
            op(obj)
        except RuntimeError as e:
            self.sb.message_box(str(e))

    def _run_convert_to(self, label, op):
        """Blender's Convert To runner: every entry acts on the edit-mode mesh."""
        self._run_on_edit_mesh(op, missing="Convert requires a mesh in edit mode.")

    # ------------------------------------------------------------------ chk004  Ignore Backfacing
    def chk004_init(self, widget):
        """Reflect the live viewport X-ray state (the DCC owns it — see ``mirror_app_state``).

        With no 3D viewport there is nothing to mirror, so the box is left at its .ui default
        rather than seeded: chk004 is the *inverse* of X-ray, and a bare ``not xray`` would
        read the absent viewport as "no X-ray" and claim Ignore-Backfacing is ON."""
        areas = btk.get_areas("VIEW_3D")
        seed = None
        if areas:
            xray = areas[0].spaces.active.shading.show_xray
            seed = lambda: widget.setChecked(not xray)  # noqa: E731
        self.mirror_app_state(widget, seed)

    def chk004(self, state, widget):
        """Ignore Backfacing — toggle viewport X-ray (occlude) so only front faces select."""
        for area in btk.get_areas("VIEW_3D"):  # window-independent (context.screen is None from the Qt-pump context)
            area.spaces.active.shading.show_xray = not state
        self.sb.message_box(f"Ignore Backfacing <hl>{'ON' if state else 'OFF'}</hl>.")

    # ------------------------------------------------------------------ chk005-007  Select Style
    def chk005_init(self, widget):
        # The active viewport tool is Blender's to own, so these three are never persisted:
        # a restored "Marquee" fired chk005 on panel open, silently re-setting the tool and
        # popping set_viewport_tool's "<hl>Box Select</hl> tool active." toast every time the
        # selection submenu initialized. Maya's counterpart seeds the group from the live
        # tool (get_selection_tool); Blender resolves the active tool per workspace+mode
        # rather than from one global context, so nothing is seeded and the group opens
        # unchecked until the user picks a style.
        #
        # Each of the three marks ITSELF rather than chk005_init marking all three: uitk's
        # immediate init path runs slot-init -> state-init per widget, and chk006 precedes
        # chk005 in the .ui, so a sibling-marking chk005_init would run too late to stop
        # chk006 restoring. (The deferred path batches both phases, so it never noticed.)
        self.sb.create_button_groups(widget.ui, "chk005-7")
        self.mirror_app_state(widget)

    def chk006_init(self, widget):
        """Select Style: Lasso — mirrors the active tool; see ``chk005_init``."""
        self.mirror_app_state(widget)

    def chk007_init(self, widget):
        """Select Style: Circle — mirrors the active tool; see ``chk005_init``."""
        self.mirror_app_state(widget)

    def _set_select_style(self, state, widget):
        if not state:
            return
        tool = self._SELECT_TOOLS.get(widget.objectName())
        if tool:
            self.set_viewport_tool(*tool)

    def chk005(self, state, widget):
        """Select Style: Box (Marquee)"""
        self._set_select_style(state, widget)

    def chk006(self, state, widget):
        """Select Style: Lasso"""
        self._set_select_style(state, widget)

    def chk007(self, state, widget):
        """Select Style: Circle (Paint)"""
        self._set_select_style(state, widget)

    # ------------------------------------------------------------------ b001  Toggle Selectability
    @btk.undoable
    def b001(self):
        """Toggle Selectability of the selected object(s).

        Blender asymmetry vs. Maya's reference-display toggle: setting ``hide_select = True``
        immediately drops the object from the selection (an unselectable object cannot stay
        selected — verified). A naive "toggle whatever is selected" handler could therefore turn
        selectability OFF but never back ON, because the second click would find nothing selected.
        So: when there IS a selection, make it non-selectable (OFF); when there is NONE, restore
        every currently non-selectable object — re-selecting it — as the recovery path (there is
        no selection left to toggle otherwise)."""
        objs = self.selected_objects()
        if objs:  # a selected object is by definition selectable -> make it non-selectable
            for o in objs:
                o.hide_select = True
            self.sb.message_box(f"Selectability <hl>OFF</hl> ({len(objs)} object(s)).")
            return
        # Nothing selected: hide_select auto-deselected our targets, so recover by re-enabling
        # (and re-selecting) every object currently marked non-selectable. Scope to the active
        # view layer (what selected_objects reads / where the auto-deselect happened) so we don't
        # reach into other scenes. Clearing hide_select is the essential part and never raises;
        # re-selecting is best-effort and guarded — select_set raises on a view-layer-excluded
        # object (which view_layer.objects can still include — verified), so restore its
        # selectability but skip re-selecting it rather than aborting the loop.
        vl = getattr(bpy.context, "view_layer", None)
        hidden = [o for o in (vl.objects if vl else ()) if o.hide_select]
        if not hidden:
            self.sb.message_box("Toggle Selectability requires a selection.")
            return
        for o in hidden:
            o.hide_select = False
            try:
                o.select_set(True)
            except RuntimeError:
                pass  # not in the active view layer (excluded collection) — selectability is restored regardless
        self.sb.message_box(f"Selectability <hl>ON</hl> ({len(hidden)} object(s)).")

    # ------------------------------------------------------------------ b002-b007  Selection Constraints
    # Maya's polySelectConstraint flags are persistent drag-select constraints; Blender has no
    # modal analogue, so each button instead expands the CURRENT selection once by the same
    # rule (and pressing several in turn stacks the expansions -- the one-shot reading of
    # "more than one constraint at a time"). Same objectNames / glyphs as the Maya fork
    # (SelectionMixin._CONSTRAINT_BUTTONS); UV Edge Loop rides the same bmesh UV-graph helper
    # as the Convert To entry. Angle expands a FACE selection (faces_select_linked_flat is
    # face-mode only), so it forces the face mask; the rest keep the current mask.
    _CONSTRAINT_OPS = {
        "b002": (lambda obj: bpy.ops.mesh.faces_select_linked_flat(), "FACE"),
        "b003": (lambda obj: bpy.ops.mesh.region_to_loop(), None),
        "b004": (lambda obj: btk.Selection.loop_multi_select(), None),
        "b005": (lambda obj: btk.Selection.loop_multi_select(ring=True), None),
        "b006": (lambda obj: bpy.ops.mesh.select_linked(), None),
        "b007": (lambda obj: btk.Selection.select_uv_edge_loop(obj), None),
    }
    _CONSTRAINT_ACTION_HINT = (
        "One-shot: expands the current selection by this rule "
        "(Blender has no persistent drag-select constraint)."
    )

    def _init_constraint_oneshot(self, widget):
        """Dress the button; a one-shot has no state, so it is not a toggle here.

        The shared .ui declares the row checkable for the Maya fork's toggles;
        cleared here so a press can't leave a Blender button reading "on" for a
        constraint that was never left switched on (and so nothing is persisted).
        """
        widget.setCheckable(False)
        self._init_constraint_button(widget)

    def _expand_by_constraint(self, widget):
        """Expand the current selection once by *widget*'s constraint rule."""
        op, mask = self._CONSTRAINT_OPS[widget.objectName()]
        self._run_on_edit_mesh(
            op, mask, missing="Selection Constraints require a mesh in Edit Mode."
        )

    def b002_init(self, widget):
        """Selection constraint: Angle."""
        self._init_constraint_oneshot(widget)

    def b002(self, widget):
        """Selection constraint: Angle (one-shot expand)."""
        self._expand_by_constraint(widget)

    def b003_init(self, widget):
        """Selection constraint: Border."""
        self._init_constraint_oneshot(widget)

    def b003(self, widget):
        """Selection constraint: Border (one-shot expand)."""
        self._expand_by_constraint(widget)

    def b004_init(self, widget):
        """Selection constraint: Edge Loop."""
        self._init_constraint_oneshot(widget)

    def b004(self, widget):
        """Selection constraint: Edge Loop (one-shot expand)."""
        self._expand_by_constraint(widget)

    def b005_init(self, widget):
        """Selection constraint: Edge Ring."""
        self._init_constraint_oneshot(widget)

    def b005(self, widget):
        """Selection constraint: Edge Ring (one-shot expand)."""
        self._expand_by_constraint(widget)

    def b006_init(self, widget):
        """Selection constraint: Shell."""
        self._init_constraint_oneshot(widget)

    def b006(self, widget):
        """Selection constraint: Shell (one-shot expand)."""
        self._expand_by_constraint(widget)

    def b007_init(self, widget):
        """Selection constraint: UV Edge Loop."""
        self._init_constraint_oneshot(widget)

    def b007(self, widget):
        """Selection constraint: UV Edge Loop (one-shot expand)."""
        self._expand_by_constraint(widget)

    # ------------------------------------------------------------------ cmb001  Reorder Selection
    def cmb001_init(self, widget):
        """Reorder Selection — backed by the rolled ``btk.SelectionOrder`` tracker (Blender
        records no object click order natively; the tracker maintains one, and reorder
        writes the sorted order into it for order-consuming tools)."""
        widget.option_box.menu.setTitle("Reorder Selection")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reverse Order",
            setObjectName="chk009",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Reverse Order",
                body="Sort descending — reverse the order the chosen method produces.",
            ),
        )
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
        """Reorder Selection (sort via ``btk.reorder_objects``, record the order on
        ``btk.SelectionOrder`` — Blender reselection alone can't carry order)."""
        reverse = widget.option_box.menu.chk009.isChecked()
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

        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("No objects selected to reorder.")
            return
        reordered = btk.reorder_objects(objects, method=method, reverse=reverse)
        if reordered:
            btk.SelectionOrder.set_order(reordered)
            # Make the last-in-order object active (Blender's own "newest pick" convention).
            bpy.context.view_layer.objects.active = reordered[-1]
            self.sb.message_box(
                f"Reordered <hl>{len(reordered)}</hl> object(s) by {selected_option}"
                f"{' (reversed)' if reverse else ''}."
            )

    # ------------------------------------------------------------------ list000  Select by Type
    # Category breadth mirrors mayatk's Selection._SELECTION_CONFIG 1:1 (same category + leaf
    # labels); the underlying handlers live in ``btk.Selection`` and use Blender-native
    # primitives (Object.type / modifiers / constraints / physics / UV data) instead of Maya's
    # string-node type lookups. See blendertk/blendertk/edit_utils/selection.py's module
    # docstring for the full "why" (which Maya leaves have no Blender analogue -> tracked ``na``
    # in tentacle/docs/parity_map.py instead of silently dropped).
    def list000_init(self, widget):
        """Select by Type: hierarchical type list."""
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

        categories = btk.Selection.get_selection_categories()
        for category, types in categories.items():
            w = root.sublist.add(category)
            w.sublist.add(sorted(types))

        if submenu:
            self.add_slot_widget(root.sublist, **tb004_kwargs)

    def tb004_init(self, widget):
        """Select by Type settings menu (mirror of the Maya slot's tb004).

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
            "• All Objects: every object in the file.\n"
            "• Selected: the current selection only.\n"
            "• Visible: objects visible in the view layer only.",
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
        """The object pool Select by Type filters from, per the tb004 scope.

        Selected reads via ``self.selected_objects()`` (view_layer-based) —
        ``bpy.context.selected_objects`` is a screen-context member that
        returns ``[]`` in the Qt event-pump state the slots run in.
        """
        menu = self.submenu.tb004.menu
        scope = menu.cmb_bytype_scope.currentData() or "all"
        if scope == "selected":
            return self.selected_objects()
        if scope == "visible":
            vl = bpy.context.view_layer
            return [o for o in vl.objects if o.visible_get(view_layer=vl)]
        return list(bpy.data.objects)

    def _by_type_mode(self):
        """The selection mode Select by Type applies, per the tb004 setting."""
        menu = self.submenu.tb004.menu
        return menu.cmb_bytype_mode.currentData() or "replace"

    @SlotsBlender.Signals("on_item_interacted")
    def list000(self, item):
        """Select by Type (native bpy predicates via ``btk.Selection``). Only leaf items act —
        the root and category headers are navigation-only."""
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
        label = item.item_text()
        objects = self._by_type_scope_objects()
        if not objects:
            self.sb.message_box("Select by Type: no objects in the current scope.")
            return
        mode = self._by_type_mode()
        try:
            result = btk.Selection.select_by_type(label, objects, mode=mode)
            verb = {"add": "Added", "remove": "Removed"}.get(mode, "Selected")
            print(f"{verb} {len(result)} objects of type: {label}")
        except ValueError:
            pass
        except Exception as e:
            self.sb.message_box(f"Error selecting by type '{label}': {e}")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
