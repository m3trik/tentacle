# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Nurbs(SlotsBlender):
    """Blender port of the shared ``nurbs`` menu — largely HIDE per the plan (Blender has no
    Maya-grade NURBS/loft toolkit). Curve-to-Tube maps cleanly onto curve ``bevel_depth`` and
    Revolve onto a Screw modifier; the mel-dispatcher list and the rest are hidden/deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    def _selected_curves(self):
        return [o for o in self.selected_objects() if o.type == "CURVE"]

    # ------------------------------------------------------------------ clean maps
    @btk.undoable
    def b058(self):
        """Curve to Tube (curve bevel)."""
        curves = self._selected_curves()
        if not curves:
            self.sb.message_box("Curve to Tube requires selected curve(s).")
            return
        for c in curves:
            c.data.bevel_depth = c.data.bevel_depth or 0.1
            c.data.use_fill_caps = True

    @btk.undoable
    def tb000(self, widget):
        """Revolve (Screw modifier about Z)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Revolve requires a selection.")
            return
        for o in objects:
            if o.type in ("MESH", "CURVE") and not any(
                m.type == "SCREW" for m in o.modifiers
            ):
                o.modifiers.new(name="Screw", type="SCREW")

    # ------------------------------------------------------------------ hidden / deferred
    def list000_init(self, widget):
        """Maya NURBS action list (mel dispatcher) — hidden; no Blender analogue."""
        widget.setVisible(False)

    def tb001(self, widget):
        """Loft — Blender has no Maya-grade loft; bridge edge loops or use curve skinning."""
        self.sb.message_box("Loft is not applicable in Blender (bridge edge loops instead).")

    def b030(self):
        """Extrude — use mesh/curve extrude in Edit Mode (E)."""
        self.sb.message_box("Use Extrude (E) in Edit Mode.")

    def b056(self):
        """Image Tracer — not yet ported (Blender: import SVG / trace image add-on)."""
        self.sb.message_box("Image Tracer is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
