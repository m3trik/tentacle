# !/usr/bin/python
# coding=utf-8
import bpy
from tentacle.slots.blender._slots_blender import SlotsBlender


class Symmetry(SlotsBlender):
    """Blender port of the shared ``symmetry`` menu.

    Maya's ``symmetricModelling`` tool maps directly onto Blender's per-mesh symmetry flags
    (``mesh.use_mirror_x/y/z`` + ``use_mirror_topology``), applied to the selected mesh(es).
    Mesh-data props → **headless-testable**. The shared UI groups the axes as a radio (one axis
    at a time); the topology radio selects position- vs topology-based matching.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.symmetry
        self.submenu = self.sb.loaded_ui.symmetry_submenu

    def _selected_meshes(self):
        return [o for o in self.selected_objects() if o.type == "MESH"]

    def _set_mirror(self, axis, state):
        for o in self._selected_meshes():
            setattr(o.data, f"use_mirror_{axis}", bool(state))

    def _report_symmetry_state(self):
        """When an axis is mirrored, surface it as ``Symmetry: <space> <axis>`` (axis
        highlighted); stay silent otherwise. Reading the active mesh rather than the
        ``state`` arg keeps the feedback accurate through the radio deselect cascade."""
        active = bpy.context.view_layer.objects.active
        if not (active and active.type == "MESH"):
            return
        me = active.data
        axes = [a.upper() for a in ("x", "y", "z") if getattr(me, f"use_mirror_{a}")]
        if not axes:
            return
        space = "Topological" if me.use_mirror_topology else "Position"
        self.sb.message_box(f"Symmetry: {space} <hl>{'+'.join(axes)}</hl>")

    # ------------------------------------------------------------------ chk000-2  axis symmetry
    def chk000_init(self, widget):
        """Set initial symmetry state from the active mesh."""
        self.sb.create_button_groups(widget.ui, "chk000-2", allow_deselect=True)
        active = bpy.context.view_layer.objects.active
        if not (active and active.type == "MESH"):
            return
        me = active.data
        if me.use_mirror_x:
            widget.ui.chk000.setChecked(True)
        elif me.use_mirror_y:
            widget.ui.chk001.setChecked(True)
        elif me.use_mirror_z:
            widget.ui.chk002.setChecked(True)

    def chk000(self, state, widget):
        """Symmetry X"""
        self._set_mirror("x", state)
        self._report_symmetry_state()

    def chk001(self, state, widget):
        """Symmetry Y"""
        self._set_mirror("y", state)
        self._report_symmetry_state()

    def chk002(self, state, widget):
        """Symmetry Z"""
        self._set_mirror("z", state)
        self._report_symmetry_state()

    # ------------------------------------------------------------------ chk004-5  match mode
    def chk004(self, state, widget):
        """Symmetry: match by position (Blender mirror flags are always object-space;
        radio partner of Topo — only acts when selected)."""
        if state:
            for o in self._selected_meshes():
                o.data.use_mirror_topology = False
            self._report_symmetry_state()

    def chk005_init(self, widget):
        """Set symmetry reference space (position vs topology)."""
        self.sb.create_button_groups(widget.ui, "chk004-5")

    def chk005(self, state, widget):
        """Symmetry: Topo (match mirrored verts by topology instead of position)."""
        for o in self._selected_meshes():
            o.data.use_mirror_topology = bool(state)
        self._report_symmetry_state()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
