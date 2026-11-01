# !/usr/bin/python
# coding=utf-8
"""Symmetry: one Slots class for both hosts.

The host owns the state and the toolkit's ``EditUtils`` reads and writes it
(``get_symmetry`` / ``set_symmetry``, a dict both ways): Maya's modeling
symmetry (``symmetricModelling``, one axis, scene-wide) and Blender's mesh
symmetry (the selected meshes' mirror flags, several axes possible). The
widgets mirror it rather than persisting their own copy (``mirror_app_state``).

The axes are a radio group: the first mirrored axis lights. Topological
symmetry needs no axis in Maya (a selected seam edge seeds it), so the axes are
disabled under it there; Blender matches mirrored vertices by topology across
the axes, which stay live (``by_axis`` in the state says which).
"""

from tentacle import Slots


class SymmetrySlots(Slots):
    #: How a report words each symmetry space (``get_symmetry()["space"]``).
    SPACE_LABELS = {"world": "World", "object": "Object", "topo": "Topological"}

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.symmetry
        self.submenu = self.sb.loaded_ui.symmetry_submenu

    def _report(self, state):
        """Surface live symmetry as ``Symmetry: <space> <axes>`` (axes highlighted);
        silent when it is off. Worded from the state the host reports back, not the
        clicked box, so it stays right through the radio deselect cascade."""
        if not state or not state.get("enabled"):
            return
        space = state.get("space")
        label = self.SPACE_LABELS.get(space, str(space).title())
        axes = "+".join(axis.upper() for axis in state.get("axes") or ())
        if axes:
            self.sb.message_box(f"Symmetry: {label} <hl>{axes}</hl>")
        else:
            self.sb.message_box(f"Symmetry: <hl>{label}</hl>")

    def _seed_axes(self, ui):
        """Check the axis box the host mirrors, signals blocked (reading the host is
        not the user editing it). The first mirrored axis wins: the group is a
        radio, and seeding bypasses its exclusivity handler, so a mesh mirrored in
        more than one axis must not light more than one box."""
        state = self.tk.EditUtils.get_symmetry()
        checked = next(iter(state.get("axes") or ()), None)
        for axis, box in zip("xyz", (ui.chk000, ui.chk001, ui.chk002)):
            self.mirror_app_state(box, lambda box=box, a=axis: box.setChecked(a == checked))

    def _disable_axes_unless_by_axis(self, ui, state):
        """Disable the axis boxes when the host's symmetry uses no axis (Maya's
        topological symmetry)."""
        if not state.get("by_axis", True):
            self.sb.toggle_multi(ui, setDisabled="chk000-2")

    def _toggle_axis(self, axis, state, widget):
        """Turn *axis* on or off; a refusal (Blender: no mesh selected) is shown and
        the boxes go back to what the host has. Only turning an axis on reports:
        switching the radio turns one axis off and another on, in either order, and
        one click must not toast twice."""
        try:
            result = self.tk.EditUtils.set_symmetry(axis=axis, state=bool(state))
        except ValueError as error:
            self.sb.message_box(str(error))
            ui = getattr(widget, "ui", None)
            if ui is not None:
                self._seed_axes(ui)
            return
        if state:
            self._report(result)

    # ------------------------------------------------------------------ chk000-2  axes
    def chk000_init(self, widget):
        """Seed the axis group from the host. The host owns the flags, so the group
        mirrors them rather than persisting its own copy: a stored axis restored over
        the host's would misreport it and re-fire the slot on panel open."""
        self.sb.create_button_groups(widget.ui, "chk000-2", allow_deselect=True)
        self._seed_axes(widget.ui)

    # The seed is cross-widget (first-axis-wins reads all three together), so it stays
    # in chk000_init, but each sibling marks ITSELF: uitk's immediate init path runs
    # slot-init -> state-init per widget and cannot promise chk000_init lands before
    # chk001/chk002 restore. Marking is idempotent.
    def chk001_init(self, widget):
        """Symmetry Y: mirrors the host; seeded by ``chk000_init``."""
        self.mirror_app_state(widget)

    def chk002_init(self, widget):
        """Symmetry Z: mirrors the host; seeded by ``chk000_init``."""
        self.mirror_app_state(widget)

    def chk000(self, state, widget):
        """Symmetry X: toggle modeling symmetry across the X axis."""
        self._toggle_axis("x", state, widget)

    def chk001(self, state, widget):
        """Symmetry Y: toggle modeling symmetry across the Y axis."""
        self._toggle_axis("y", state, widget)

    def chk002(self, state, widget):
        """Symmetry Z: toggle modeling symmetry across the Z axis."""
        self._toggle_axis("z", state, widget)

    # ------------------------------------------------------------------ chk004-5  space
    def chk004_init(self, widget):
        """Object space: mirrors the host; seeded by ``chk005_init``."""
        self.mirror_app_state(widget)

    def chk004(self, state, widget):
        """Symmetry: object space. The radio partner of Topo: it acts only when
        selected (a deselect means Topo took over and set its own space)."""
        if not state:
            return
        try:
            result = self.tk.EditUtils.set_symmetry(space="object")
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        self._report(result)

    def chk005_init(self, widget):
        """Seed the space radio (object vs topology) from the host."""
        self.sb.create_button_groups(widget.ui, "chk004-5")
        state = self.tk.EditUtils.get_symmetry()
        topo = state.get("space") == "topo"
        has_target = state.get("space") is not None  # Blender: an active mesh
        chk004, chk005 = widget.ui.chk004, widget.ui.chk005
        self.mirror_app_state(chk004, lambda: chk004.setChecked(has_target and not topo))
        self.mirror_app_state(chk005, lambda: chk005.setChecked(topo))
        self._disable_axes_unless_by_axis(widget.ui, state)

    def _revert_to_object_space(self):
        """Put the space radio back on Object without running either slot: the
        refused topology change left the host's space as it was."""
        for box, checked in ((self.ui.chk005, False), (self.ui.chk004, True)):
            was_blocked = box.blockSignals(True)
            try:
                box.setChecked(checked)
            finally:
                box.blockSignals(was_blocked)

    def chk005(self, state, widget):
        """Symmetry: by topology. Maya seeds it from a selected seam edge; a
        refusal returns the radio to object space and says why."""
        if not state:
            self.sb.toggle_multi(self.ui, setEnabled="chk000-2")
            return
        try:
            result = self.tk.EditUtils.set_symmetry(space="topo")
        except ValueError as error:
            self._revert_to_object_space()
            self.sb.message_box(str(error))
            return
        self._disable_axes_unless_by_axis(self.ui, result)
        self._report(result)
