# !/usr/bin/python
# coding=utf-8
"""Curve to Tube: sweep a circular profile along the selected curves into a
NURBS or polygon tube, with a live preview.

One Slots class for both hosts. The engine is the host toolkit's
``CurveToTube`` and the preview its ``Preview``, both reached through
``self.tk``: Maya extrudes a NURBS surface (tessellated for polygon), Blender
bevels the curve (baked to a mesh for polygon).
"""

from tentacle import Slots


class CurveToTubeSlots(Slots):
    # A live polygon tube resamples its source curve in place (Maya's RDP ring
    # placement): PRESERVE_GEOMETRY makes Maya's Preview snapshot the selected
    # curves and restore them on rollback. Blender's Preview snapshots every
    # operated object regardless.
    PRESERVE_GEOMETRY = True

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.curve_to_tube
        self.last_tubes = []

        # Output-type combo (NURBS / Polygon) drives which options apply.
        self.ui.cmb000.add(list(self.tk.CurveToTube.OUTPUT_TYPES))
        # Polygon topology: quads vs triangles (was the "Quads" checkbox). Quads is
        # the default, matching the prior checked state.
        self.ui.cmb_topology.add([("Quads", "quads"), ("Triangles", "triangles")])
        self.ui.cmb_topology.setAsCurrent("quads")

        # Per-field reset buttons (uitk option-box): click resets a field to its
        # default; Alt/Ctrl+click bypasses it to default (greyed, restorable).
        # Must precede connect_multi/Preview — wrapping reparents the widgets and
        # invalidates any already-deferred wrapper (see add_reset_buttons docstring).
        self.sb.add_reset_buttons(self.ui)

        # Select Result is the Preview's: it (de)selects the tube(s) after every
        # build and on commit, and applies a toggle at once without a rebuild.
        # A selection with no curve in it is refused by the engine itself (the
        # Preview says why and switches off).
        self.preview = self.tk.Preview(
            self,
            self.ui.chk000,
            self.ui.b000,
            message_func=self.sb.message_box,
            undo_message="Curve to Tube",
            select_result_checkbox=self.ui.chk004,
            result_provider=lambda: self.last_tubes,
        )
        # Re-sweep live as any numeric field changes.
        self.sb.connect_multi(self.ui, "s000-3", "valueChanged", self.preview.refresh)
        # Output type and the poly-only toggles also re-sweep; the combo also
        # enables/disables the options that don't apply to the current type.
        self.ui.cmb000.currentIndexChanged.connect(self.preview.refresh)
        self.ui.cmb000.currentIndexChanged.connect(self._toggle_output_options)
        self.ui.chk001.toggled.connect(self.preview.refresh)  # Caps
        self.ui.cmb_topology.currentIndexChanged.connect(self.preview.refresh)
        self.ui.chk003.toggled.connect(self.preview.refresh)  # Keep History (live)

        self._toggle_output_options()

        # The footer doubles as a stats readout once a tube is built; a hint
        # until then.
        self.ui.footer.setDefaultStatusText("Select curve(s), then Preview.")

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Curve to Tube",
                body="Sweep a circular profile along the selected curves to build "
                "a tube: a smooth NURBS tube (in Blender, a beveled curve) or a "
                "polygon mesh.",
                steps=[
                    "Select one or more curves.",
                    "Pick an <b>Output</b> type (NURBS or Polygon).",
                    "Set <b>Radius</b> and <b>Sections</b> (sides around).",
                    "For polygon, set <b>Path Res</b> (ring density along the "
                    "curve) and toggle <b>Caps</b> / <b>Quads</b>.",
                    "Toggle <b>Preview</b> to iterate, then <b>Create</b> to commit.",
                ],
                notes=[
                    "<b>Sections</b> sets the profile smoothness for NURBS and "
                    "the exact number of sides for polygon.",
                    "<b>Path Res</b> sets the ring density along the path; higher "
                    "= finer. Maya places the rings by curvature (dense where the "
                    "curve bends, sparse on straight runs), Blender evenly. "
                    "<b>Path Res</b>, <b>Caps</b> and <b>Quads</b> apply to "
                    "polygon output only.",
                    "<b>Keep History</b> keeps the curve driving the tube: edit the "
                    "curve and the tube updates. The topology is the same either "
                    "way. (Blender has no live curve-to-mesh, so a polygon tube is "
                    "always baked there.)",
                    "<b>Select Result</b> selects the finished tube(s) so you can "
                    "see the resulting tessellation.",
                ],
            )
        )

    def _toggle_output_options(self, *_):
        """Enable only the options that apply to the current output type."""
        is_poly = self.ui.cmb000.currentData() == "polygon"
        self.ui.s002.setEnabled(is_poly)  # Path divisions
        self.ui.chk001.setEnabled(is_poly)  # Caps
        self.ui.cmb_topology.setEnabled(is_poly)  # Quads/Triangles
        self.ui.s003.setEnabled(not is_poly)  # Degree (NURBS profile)

    def b001_init(self, widget):
        """Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
        current values as the defaults, Ctrl+Shift+Click forgets them)."""
        self._reset_gesture = self.sb.ResetGesture(widget)

    def perform_operation(self, objects, contract=None):
        """Build the tube(s) along *objects* (Maya's Preview passes its cleanup
        *contract*, ``None`` on the commit replay; Blender's passes none)."""
        self.last_tubes = self.tk.CurveToTube.create(
            objects,
            output_type=self.ui.cmb000.currentData(),
            radius=self.ui.s000.value(),
            sections=self.ui.s001.value(),
            path_divisions=self.ui.s002.value(),
            degree=self.ui.s003.value(),
            caps=self.ui.chk001.isChecked(),
            quads=self.ui.cmb_topology.currentData() == "quads",
            live=self.ui.chk003.isChecked(),
        )
        # The host's stats for the build ("" falls back to the default hint).
        self.ui.footer.setStatusText(self.tk.CurveToTube.describe(self.last_tubes))
