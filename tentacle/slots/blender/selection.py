# !/usr/bin/python
# coding=utf-8
import math

import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class Selection(SlotsBlender):
    """Blender port of the shared ``selection`` menu.

    Per the capability map (BLENDER_PORT_PLAN §5), selection maps almost entirely to **native
    Blender operators**, so most handlers call ``bpy.ops`` directly (proven to work from the Qt
    event-pump context); select-by-type rides ``object.select_by_type``. Maya-tool-specific
    widgets with no clean Blender analogue (reorder, dR_ constraints) are deferred with a
    clear message.
    """

    # Maya "Marquee/Lasso/Paint" select styles -> Blender's box/lasso/circle select tools.
    _SELECT_TOOLS = {
        "chk005": "builtin.select_box",
        "chk006": "builtin.select_lasso",
        "chk007": "builtin.select_circle",
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
    def tb001_init(self, widget):
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Threshold: ", setObjectName="s000",
            set_limits=[0, 1, 0.01, 3], setValue=0.1,
            setToolTip="Allowed difference for the similarity match.",
        )

    def tb001(self, widget):
        """Select Similar"""
        threshold = widget.option_box.menu.s000.value()
        obj = bpy.context.active_object
        try:
            if obj and obj.mode == "EDIT":
                bpy.ops.mesh.select_similar(threshold=threshold)
            else:
                bpy.ops.object.select_grouped(type="TYPE")
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ tb002  Select Island
    def tb002_init(self, widget):
        # chk022: first number free in BOTH this file and maya/selection.py — the QSettings
        # store is shared across DCCs, so reusing a Maya name for a different option bleeds state.
        widget.option_box.menu.add(
            "QCheckBox", setText="By Seam", setObjectName="chk022",
            setToolTip="Stop the island growth at marked seams.",
        )

    def tb002(self, widget):
        """Select Island (connected region)"""
        if not self._edit_mesh():
            self.sb.message_box("Select Island requires a mesh.")
            return
        delimit = {"SEAM"} if widget.option_box.menu.chk022.isChecked() else set()
        bpy.ops.mesh.select_linked(delimit=delimit)

    # ------------------------------------------------------------------ tb003  Select Edges By Angle
    def tb003_init(self, widget):
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Angle: ", setObjectName="s006",
            set_limits=[0, 180], setValue=30,
            setToolTip="Select edges sharper than this angle (degrees).",
        )

    def tb003(self, widget):
        """Select Edges By Angle"""
        angle = widget.option_box.menu.s006.value()
        if not self._edit_mesh("EDGE"):
            self.sb.message_box("Select Edges By Angle requires a mesh.")
            return
        bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(angle))

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
            try:
                bpy.ops.wm.tool_set_by_id(name=tool)
            except Exception as e:
                self.sb.message_box(str(e))

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

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def cmb001_init(self, widget):
        widget.option_box.menu.setTitle("Reorder Selection")
        widget.option_box.menu.add(
            "QCheckBox", setText="Reverse Order", setObjectName="chk009",
            setToolTip="Reverse the reordered selection.",
        )
        widget.add(["Name", "X Position", "Y Position", "Z Position", "Random"], header="Reorder By:")

    def cmb001(self, index, widget):
        """Reorder Selection — not yet ported to Blender."""
        self.sb.message_box("Reorder Selection is not yet implemented for Blender.")

    def cmb005_init(self, widget):
        widget.add(["OFF", "Angle", "Border", "Edge Loop", "Edge Ring", "Shell"])

    def cmb005(self, index, widget):
        """Selection Constraints — Maya draggable-constraint tool has no direct Blender analogue."""
        self.sb.message_box("Selection Constraints are not yet implemented for Blender.")

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
