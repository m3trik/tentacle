# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class Selection(SlotsBlender):
    """Blender port of the shared ``selection`` menu.

    Per the capability map (BLENDER_PORT_PLAN §5), selection maps almost entirely to **native
    Blender operators**, so most handlers call ``bpy.ops`` directly (proven to work from the Qt
    event-pump context); select-by-type rides ``object.select_by_type``; the dR_ selection
    constraints become one-shot selection expansion (no modal analogue). Reorder Selection is
    closed as not-applicable (no ordered object selection in Blender).
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

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _edit_mesh(select_mode=None):
        """Ensure the active object is a mesh in Edit Mode (optionally setting the component
        select mode). Returns the object, or None if there is no mesh to act on."""
        obj = bpy.context.active_object
        if not obj or obj.type != "MESH":
            return None
        if obj.mode != "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")
        if select_mode:
            bpy.ops.mesh.select_mode(type=select_mode)
        return obj

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
        if not self._edit_mesh("EDGE"):
            self.sb.message_box("Select Nth requires a mesh.")
            return
        if m.chk000.isChecked():            # Edge Ring
            bpy.ops.mesh.loop_multi_select(ring=True)
        elif m.chk001.isChecked():          # Edge Loop
            bpy.ops.mesh.loop_multi_select(ring=False)
        elif m.chk021.isChecked() or m.chk002.isChecked():   # Loop / Shortest path
            try:
                bpy.ops.mesh.shortest_path_select()
            except RuntimeError as e:
                self.sb.message_box(str(e))
        elif m.chk010.isChecked():          # Border edges
            bpy.ops.mesh.region_to_loop()

        step = m.s003.value()
        if step > 1:                        # keep every Nth (checker deselect)
            try:
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
        ("chk018", "World Area", "The surface area of the faces in world space.", False),
        ("chk019", "Bounding Box", "The object's bounding-box dimensions.", False),
        ("chk020", "Include Original", "Include the originally selected object(s) in the result.", False),
    )

    def tb001_init(self, widget):
        widget.option_box.menu.setTitle("Select Similar")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Tolerance: ", setObjectName="s000",
            set_limits=[0, 9999, 0.0, 3], setValue=0.0,
            setToolTip="The allowed difference in any compared metric (e.g. 4 allows a 4-component "
            "difference; 0.05 allows that much variance between bounding-box values).",
        )
        for name, label, tip, checked in self._SIMILAR_CRITERIA:
            widget.option_box.menu.add(
                "QCheckBox", setText=label, setObjectName=name, setChecked=checked, setToolTip=tip,
            )

    def tb001(self, widget):
        """Select Similar — object-level similarity by topology / area / bounding-box metrics
        (Maya parity, via ``btk.get_similar_mesh``); in Edit mode, fall back to Blender's native
        component ``select_similar``."""
        m = widget.option_box.menu
        obj = bpy.context.active_object
        if obj and obj.mode == "EDIT":
            vert, edge, face = bpy.context.tool_settings.mesh_select_mode
            mode = "FACE" if face else "EDGE" if edge else "VERT"
            try:
                bpy.ops.mesh.select_similar(
                    type=self._COMPONENT_DEFAULT[mode],
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
        if not self._edit_mesh():
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
        obj = self._edit_mesh("EDGE")
        if not obj:
            self.sb.message_box("Select Edges By Angle requires a mesh.")
            return
        n = btk.select_edges_by_angle(obj, low_angle=m.s006.value(), high_angle=m.s007.value())
        if not n:
            self.sb.message_box("No edges found in that angle range.")

    # ------------------------------------------------------------------ cmb003  Convert To
    def cmb003_init(self, widget):
        widget.add(
            ["Verts", "Edges", "Faces", "Edge Loop", "Edge Ring", "Border Edges", "Shell"],
            header="Convert To:",
        )

    def cmb003(self, index, widget):
        """Convert the current selection to another component type."""
        text = widget.items[index]
        if not self._edit_mesh():
            self.sb.message_box("Convert requires a mesh in edit mode.")
            return
        conversions = {
            "Verts": lambda: bpy.ops.mesh.select_mode(type="VERT"),
            "Edges": lambda: bpy.ops.mesh.select_mode(type="EDGE"),
            "Faces": lambda: bpy.ops.mesh.select_mode(type="FACE"),
            "Edge Loop": lambda: bpy.ops.mesh.loop_multi_select(ring=False),
            "Edge Ring": lambda: bpy.ops.mesh.loop_multi_select(ring=True),
            "Border Edges": lambda: bpy.ops.mesh.region_to_loop(),
            "Shell": lambda: bpy.ops.mesh.select_linked(),
        }
        op = conversions.get(text)
        if op:
            op()
        else:
            self.sb.message_box(f"'{text}' conversion not yet mapped for Blender.")

    # ------------------------------------------------------------------ chk004  Ignore Backfacing
    def chk004(self, state, widget):
        """Ignore Backfacing — toggle viewport X-ray (occlude) so only front faces select."""
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.show_xray = not state
        self.sb.message_box(f"Ignore Backfacing <hl>{'ON' if state else 'OFF'}</hl>.")

    # ------------------------------------------------------------------ chk005-007  Select Style
    def chk005_init(self, widget):
        self.sb.create_button_groups(widget.ui, "chk005-7")

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
        """Toggle Selectability of the selected object(s)."""
        objs = self.selected_objects()
        if not objs:
            self.sb.message_box("Toggle Selectability requires a selection.")
            return
        new_state = not objs[0].hide_select
        for o in objs:
            o.hide_select = new_state
        self.sb.message_box(f"Selectability <hl>{'OFF' if new_state else 'ON'}</hl>.")

    # ------------------------------------------------------------------ cmb005  Selection Constraints
    # Maya's dR_selConstraint* are persistent drag-select constraints; Blender has no modal
    # analogue, so each entry instead expands the CURRENT selection once by the same rule.
    _CONSTRAINT_OPS = {
        "Angle": lambda: bpy.ops.mesh.faces_select_linked_flat(),
        "Border": lambda: bpy.ops.mesh.region_to_loop(),
        "Edge Loop": lambda: bpy.ops.mesh.loop_multi_select(ring=False),
        "Edge Ring": lambda: bpy.ops.mesh.loop_multi_select(ring=True),
        "Shell": lambda: bpy.ops.mesh.select_linked(),
    }

    def cmb005_init(self, widget):
        widget.add(["OFF", *self._CONSTRAINT_OPS])

    def cmb005(self, index, widget):
        """Selection Constraints (one-shot in Blender: expands the current selection by
        the chosen rule — there is no persistent drag-select constraint to leave on)."""
        text = widget.items[index]
        op = self._CONSTRAINT_OPS.get(text)
        if op is None:  # OFF — nothing persistent to disable
            return
        if not self._edit_mesh("FACE" if text == "Angle" else None):
            self.sb.message_box("Selection Constraints require a mesh in Edit Mode.")
            return
        try:
            op()
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ closed (not applicable)
    def cmb001_init(self, widget):
        """Reorder Selection — hidden: Blender has no ordered *object* selection to feed
        (operators receive an unordered set; ``select_history`` is component-only)."""
        widget.setVisible(False)

    def cmb001(self, index, widget):
        """Reorder Selection — not applicable in Blender."""
        self.sb.message_box(
            "Reorder Selection is not applicable in Blender — operators act on an "
            "unordered selection set."
        )

    # ------------------------------------------------------------------ list000  Select by Type
    # Friendly label -> Object.type enum, grouped for the hierarchical list (Maya parity).
    _SELECT_TYPES = {
        "Geometry": {
            "Mesh": "MESH", "Curve": "CURVE", "Surface": "SURFACE",
            "Metaball": "META", "Text": "FONT", "Volume": "VOLUME",
        },
        "Helpers": {"Empty": "EMPTY", "Lattice": "LATTICE", "Armature": "ARMATURE"},
        "Lights & Cameras": {
            "Light": "LIGHT", "Light Probe": "LIGHT_PROBE",
            "Camera": "CAMERA", "Speaker": "SPEAKER",
        },
    }

    def list000_init(self, widget):
        """Select by Type: hierarchical type list."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up")
        root = widget.add("By Type")
        root.sublist.setMinimumWidth(widget.width() or 120)
        for category, types in self._SELECT_TYPES.items():
            w = root.sublist.add(category)
            w.sublist.add(sorted(types))

    @Signals("on_item_interacted")
    def list000(self, item):
        """Select by Type (native ``object.select_by_type``). Only leaf items act —
        the root and category headers are navigation-only."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        label = item.item_text()
        for types in self._SELECT_TYPES.values():
            if label in types:
                try:
                    bpy.ops.object.select_by_type(type=types[label])
                except (RuntimeError, TypeError) as e:  # enum drift across Blender versions
                    self.sb.message_box(str(e))
                return


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
