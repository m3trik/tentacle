# !/usr/bin/python
# coding=utf-8
"""Duplicate Radial: copies of the selection in a radial pattern about a pivot.

One Slots class for both hosts. The engine is the host toolkit's
``DuplicateRadial`` and the preview its ``Preview``, both reached through
``self.tk``.
"""

from tentacle import Slots


class DuplicateRadialSlots(Slots):
    # With keep_original=False, duplicate_radial deletes the original
    # transform. MUTATES_SELECTION=True tells Maya's Preview to duplicate+hide
    # the captured selection before perform_operation so rollback (and the next
    # refresh, which re-targets the same names) can restore it.
    MUTATES_SELECTION = True

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.duplicate_radial
        self.copies = {}

        # Output mode: independent copies vs shared-shape instances (was the
        # "Instance" checkbox). Copy is the default, matching the prior unchecked state.
        self.ui.cmb_inst.clear()
        self.ui.cmb_inst.add([("Copy", "copy"), ("Instance", "instance")])
        self.ui.cmb_inst.setAsCurrent("copy")

        # Per-field reset buttons (uitk option-box): click resets a field to its
        # default; Alt/Ctrl+click bypasses it to default (greyed, restorable).
        # Must precede connect_multi/Preview — wrapping reparents the widgets and
        # invalidates any already-deferred wrapper (see add_reset_buttons docstring).
        self.sb.add_reset_buttons(self.ui)

        self.preview = self.tk.Preview(
            self,
            self.ui.chk000,
            self.ui.b000,
            finalize_func=self.regroup_copies,
            message_func=self.sb.message_box,
            undo_message="Duplicate Radial",
        )
        self.sb.connect_multi(self.ui, "s000-16", "valueChanged", self.preview.refresh)
        self.sb.connect_multi(self.ui, "chk002-4", "toggled", self.preview.refresh)
        self.sb.connect_multi(self.ui, "chk006-8", "toggled", self.preview.refresh)
        self.sb.connect_multi(
            self.ui, "cmb_inst", "currentIndexChanged", self.preview.refresh
        )
        self.ui.cmb000.currentIndexChanged.connect(self.preview.refresh)

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Duplicate Radial",
                body="Duplicate selected objects in a radial / circular pattern "
                "around a chosen pivot.",
                steps=[
                    "Select one or more objects.",
                    "Set <b>Copies</b>, <b>Start Angle</b>, <b>End Angle</b>, and "
                    "the <b>Rotate Axis</b> (X / Y / Z).",
                    "Pick the <b>Pivot</b> — Object or World.",
                    "Optionally set per-copy <b>Translate</b> / <b>Rotate</b> / "
                    "<b>Scale</b> offsets and a <b>Pivot Offset</b>.",
                    "Toggle <b>Preview</b>, then <b>Duplicate</b> to commit.",
                ],
                sections=[
                    (
                        "Options",
                        [
                            "<b>Instance</b> — copies share one mesh; cheaper, and "
                            "edits propagate.",
                            "<b>Keep Original</b> — leave the source object in place "
                            "(off discards it after the pattern is built).",
                            "<b>Combine</b> — merge the result into a single mesh.",
                            "<b>Suffix</b> — append a location-based alphabetical "
                            "suffix to the copy names.",
                        ],
                    ),
                ],
                notes=[
                    "<b>Weight Bias</b> and <b>Weight Curve</b> control non-uniform "
                    "angular spacing between start and end angle.",
                ],
            )
        )

    def s015_init(self, widget):
        """Initialize Weight Bias."""
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Weight Bias",
                body="Controls the direction and strength of the bias — how far "
                "the spacing departs from linear, and toward which end.",
                bullets=[
                    "<code>0</code> — bias completely towards the start.",
                    "<code>0.5</code> (default) — no bias, linear distribution.",
                    "<code>1</code> — bias completely towards the end.",
                ],
                notes=[
                    "At the default 0.5, spacing is exactly linear and "
                    "<b>Weight Curve</b> has no visible effect — move this away "
                    "from 0.5 first.",
                ],
            )
        )

    def s016_init(self, widget):
        """Initialize Weight Curve."""
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Weight Curve",
                body="Shapes the curvature of the bias set by Weight Bias.",
                bullets=[
                    "<code>0</code> — no curvature; a linear effect.",
                    "<code>0.5</code> (default) — moderate curvature.",
                    "<code>1</code> — maximum curvature, sharply eased toward one end.",
                ],
                notes=[
                    "Has no visible effect while <b>Weight Bias</b> is at its "
                    "default (0.5) — the two ends of the sweep are then already "
                    "spaced identically regardless of this value.",
                ],
            )
        )

    def b001_init(self, widget):
        """Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
        current values as the defaults, Ctrl+Shift+Click forgets them)."""
        self._reset_gesture = self.sb.ResetGesture(widget)

    def perform_operation(self, objects, contract=None):
        """Duplicate *objects* radially from the panel's values.

        ``contract`` is the cleanup contract Maya's Preview passes (``None`` on
        commit); Blender's passes none. The engine needs neither.
        """
        num_copies = self.ui.s009.value()
        if num_copies < 1:
            raise ValueError("Set Copies to at least 1.")
        self.copies = self.tk.DuplicateRadial.duplicate_radial(
            objects,
            num_copies,
            start_angle=self.ui.s013.value(),
            end_angle=self.ui.s014.value(),
            weight_bias=self.ui.s015.value(),
            weight_curve=self.ui.s016.value(),
            rotate_axis=(
                "x"
                if self.ui.chk002.isChecked()
                else "y"
                if self.ui.chk003.isChecked()
                else "z"
            ),
            offset=(self.ui.s010.value(), self.ui.s011.value(), self.ui.s012.value()),
            translate=(
                self.ui.s000.value(),
                self.ui.s001.value(),
                self.ui.s002.value(),
            ),
            rotate=(self.ui.s003.value(), self.ui.s004.value(), self.ui.s005.value()),
            scale=(self.ui.s006.value(), self.ui.s007.value(), self.ui.s008.value()),
            pivot=self._resolve_pivot(self.ui.cmb000.currentIndex()),
            keep_original=self.ui.chk006.isChecked(),
            instance=self.ui.cmb_inst.currentData() == "instance",
            combine=self.ui.chk007.isChecked(),
            suffix=self.ui.chk008.isChecked(),
        )

    def regroup_copies(self):
        """The commit's finalize step: the host groups the committed copies."""
        self.tk.DuplicateRadial.regroup_copies(self.copies)

    @staticmethod
    def _resolve_pivot(pivot_index: int) -> str:
        """The pivot the dropdown's index names."""
        return {0: "object", 1: "world"}.get(pivot_index, "object")
