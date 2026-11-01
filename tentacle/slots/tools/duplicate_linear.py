# !/usr/bin/python
# coding=utf-8
"""Duplicate Linear: copies of the selection along a line, each interpolating
toward an end-state translate / rotate / scale offset.

One Slots class for both hosts. The engine is the host toolkit's
``DuplicateLinear`` and the preview its ``Preview``, both reached through
``self.tk``.
"""

from tentacle import Slots

#: The interpolation curves the array tools offer (a curated, monotonic subset
#: of ``ptk.ProgressionCurves``), shared with Cut On Axis so the two present the
#: same weighting.
INTERPOLATION_MODES = [
    ("Linear", "linear"),
    ("Ease In", "ease_in"),
    ("Ease Out", "ease_out"),
    ("Ease In-Out", "ease_in_out"),
    ("Exponential", "exponential"),
    ("Smooth Step", "smooth_step"),
    ("Weighted", "weighted"),
]


class DuplicateLinearSlots(Slots):
    # Defensive: duplicate_linear itself does not delete the original, but
    # the captured selection can be invalidated between refreshes (e.g. the
    # user invoked another tool that deleted it, or a sibling preview op
    # mutated the scene). MUTATES_SELECTION=True makes Maya's Preview
    # duplicate+hide the captured originals so rollback can restore them by
    # UUID, turning a hard "No object matches name" crash into a no-op
    # refresh. Blender's Preview snapshots every operated object regardless.
    MUTATES_SELECTION = True

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.duplicate_linear

        # Ensure preview cleanup triggers when resetting defaults
        self.ui.chk000.block_signals_on_restore = False

        # The pivots the host's operations resolve.
        self.ui.cmb002.clear()
        self.pivot_options = self.tk.XformUtils.get_pivot_options()
        self.ui.cmb002.add(self.pivot_options, prefix="Pivot:")

        # Populate calculation mode combobox
        self.ui.cmb001.clear()
        self.ui.cmb001.add(INTERPOLATION_MODES, prefix="Interpolation:")

        # Set default calculation mode to "Weighted" to match tool defaults
        self.ui.cmb001.setAsCurrent("weighted")

        # Output mode: independent copies vs shared-shape instances (was the "Inst"
        # checkbox). Instance is the default, matching the prior checked state.
        self.ui.cmb_inst.clear()
        self.ui.cmb_inst.add([("Copy", "copy"), ("Instance", "instance")])
        self.ui.cmb_inst.setAsCurrent("instance")

        # Per-field reset buttons (uitk option-box): click resets a field to its
        # default; Alt/Ctrl+click bypasses it to default (greyed, restorable).
        # Must precede connect_multi/Preview — wrapping reparents the widgets and
        # invalidates any already-deferred wrapper (see add_reset_buttons docstring).
        self.sb.add_reset_buttons(self.ui)

        self.preview = self.tk.Preview(
            self,
            self.ui.chk000,
            self.ui.b000,
            message_func=self.sb.message_box,
            undo_message="Duplicate Linear",
        )
        self.sb.connect_multi(self.ui, "s000-11", "valueChanged", self.preview.refresh)
        for name in ("cmb002", "cmb001", "cmb_inst"):
            self.sb.connect_multi(
                self.ui, name, "currentIndexChanged", self.preview.refresh
            )
        self.sb.connect_multi(
            self.ui, "cmb001", "currentIndexChanged", self.toggle_weight_ui
        )

        # Initialize the UI state
        self.toggle_weight_ui()

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Duplicate Linear",
                body="Duplicate selected objects along a linear path with "
                "per-copy translate, rotate, and scale offsets.",
                steps=[
                    "Select one or more objects.",
                    "Set <b>Copies</b> and the end-state <b>Translate</b> / "
                    "<b>Rotate</b> / <b>Scale</b> offsets — each copy interpolates "
                    "from source to that final offset.",
                    "Pick an interpolation <b>Mode</b> (linear, ease in/out, "
                    "weighted, sine, bounce, elastic, …).",
                    "Pick a <b>Pivot</b>.",
                    "Toggle <b>Preview</b>, then <b>Create</b> to commit.",
                ],
                notes=[
                    "<b>Weight Bias</b> only applies to the <i>weighted</i> mode; "
                    "<b>Weight Curve</b> applies to non-linear modes. Disabled "
                    "spinners are simply ignored by the current mode.",
                    "<b>Instance</b> copies share one mesh, so an edit to one "
                    "shows in all; <b>Copy</b> makes independent ones.",
                ],
            )
        )

    def toggle_weight_ui(self):
        """Disable the weight spinners the current interpolation mode ignores:
        ``linear`` and ``smooth_step`` (a fixed Hermite curve) use neither,
        ``weighted`` uses the bias and the curve, the rest the curve alone
        (``pythontk``'s ``ProgressionCurves``)."""
        mode = self.ui.cmb001.currentData()
        self.ui.s010.setEnabled(mode in ["weighted"])  # Weight Bias
        self.ui.s011.setEnabled(mode not in ["linear", "smooth_step"])  # Weight Curve

    def b001_init(self, widget):
        """Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
        current values as the defaults, Ctrl+Shift+Click forgets them)."""
        ResetGesture = self.sb.ResetGesture

        self._reset_gesture = ResetGesture(widget)

    def perform_operation(self, objects, contract=None):
        """Duplicate *objects* along the line (Maya's Preview passes its cleanup
        *contract*)."""
        num_copies = self.ui.s009.value() - 1  # Include the orig object in the count
        translate = (self.ui.s000.value(), self.ui.s001.value(), self.ui.s002.value())
        rotate = (self.ui.s003.value(), self.ui.s004.value(), self.ui.s005.value())
        scale = (self.ui.s006.value(), self.ui.s007.value(), self.ui.s008.value())
        self.copies = self.tk.DuplicateLinear.duplicate_linear(
            objects,
            num_copies,
            translate,
            rotate,
            scale,
            self.ui.s010.value(),  # weight bias
            self.ui.s011.value(),  # weight curve
            self.ui.cmb002.currentData(),  # pivot
            self.ui.cmb001.currentData(),  # interpolation mode
            self.ui.cmb_inst.currentData() == "instance",
        )
