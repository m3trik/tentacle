# !/usr/bin/python
# coding=utf-8
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

    def _active_mesh_data(self):
        """The active object's mesh data, or None when it isn't a mesh — the single read
        behind both the state reports and the ``*_init`` seeds. Goes through
        ``active_object`` (btk's SSoT reader) rather than ``bpy.context.active_object``,
        which is None from the Qt event-pump context the slots run in."""
        active = self.active_object()
        return active.data if (active and active.type == "MESH") else None

    def _set_mirror(self, axis, state):
        for o in self._selected_meshes():
            setattr(o.data, f"use_mirror_{axis}", bool(state))

    def _report_symmetry_state(self):
        """When an axis is mirrored, surface it as ``Symmetry: <space> <axis>`` (axis
        highlighted); stay silent otherwise. Reading the active mesh rather than the
        ``state`` arg keeps the feedback accurate through the radio deselect cascade."""
        me = self._active_mesh_data()
        if not me:
            return
        axes = [a.upper() for a in ("x", "y", "z") if getattr(me, f"use_mirror_{a}")]
        if not axes:
            return
        space = "Topological" if me.use_mirror_topology else "Position"
        self.sb.message_box(f"Symmetry: {space} <hl>{'+'.join(axes)}</hl>")

    # ------------------------------------------------------------------ chk000-2  axis symmetry
    def chk000_init(self, widget):
        """Set initial symmetry state from the active mesh.

        The mesh owns these flags, so the group mirrors them rather than persisting its own
        copy — a stored axis restored over the mesh's would both misreport the mesh and
        re-fire the slot, re-mirroring it and popping ``_report_symmetry_state``'s toast on
        panel open. Seeding blocks signals for the same reason: ``init_slot`` blocks only
        ``widget`` (chk000), so the plain ``setChecked`` this replaces fired chk001/chk002's
        slots whenever the active mesh was mirrored in Y or Z."""
        self.sb.create_button_groups(widget.ui, "chk000-2", allow_deselect=True)
        me = self._active_mesh_data()
        # First mirrored axis wins: the UI groups the axes as a radio, and seeding with
        # signals blocked bypasses the group's own exclusivity handler, so a mesh mirrored
        # in more than one axis must not light up more than one box.
        checked = next(
            (a for a in "xyz" if me and getattr(me, f"use_mirror_{a}")), None
        )
        for axis, w in zip("xyz", (widget.ui.chk000, widget.ui.chk001, widget.ui.chk002)):
            self.mirror_app_state(w, lambda w=w, a=axis: w.setChecked(a == checked))

    # The axis seed is inherently cross-widget (first-axis-wins needs all three read
    # together), so it stays in chk000_init — but each sibling still marks ITSELF, because
    # uitk's immediate init path runs slot-init -> state-init per widget and cannot promise
    # chk000_init lands before chk001/chk002 restore. Marking is idempotent: whichever runs
    # first opts the widget out, and chk000_init still seeds the right box.
    def chk001_init(self, widget):
        """Symmetry Y — mirrors the active mesh; seeded by ``chk000_init``."""
        self.mirror_app_state(widget)

    def chk002_init(self, widget):
        """Symmetry Z — mirrors the active mesh; seeded by ``chk000_init``."""
        self.mirror_app_state(widget)

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

    def chk004_init(self, widget):
        """Match-by-position — mirrors the active mesh; seeded by ``chk005_init``."""
        self.mirror_app_state(widget)

    def chk005_init(self, widget):
        """Set symmetry reference space (position vs topology), mirrored from the active mesh."""
        self.sb.create_button_groups(widget.ui, "chk004-5")
        me = self._active_mesh_data()
        topo = bool(me and me.use_mirror_topology)
        chk004, chk005 = widget.ui.chk004, widget.ui.chk005
        self.mirror_app_state(chk004, lambda: chk004.setChecked(bool(me) and not topo))
        self.mirror_app_state(chk005, lambda: chk005.setChecked(topo))

    def chk005(self, state, widget):
        """Symmetry: Topo (match mirrored verts by topology instead of position)."""
        for o in self._selected_meshes():
            o.data.use_mirror_topology = bool(state)
        self._report_symmetry_state()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
