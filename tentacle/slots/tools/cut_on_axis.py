# !/usr/bin/python
# coding=utf-8
"""Cut On Axis: slice the selected meshes along an axis, then optionally delete
or mirror the cut half.

One Slots class for both hosts. The engine is the host toolkit's ``CutOnAxis``
and the preview its ``Preview``, both reached through ``self.tk``.
"""

from tentacle import Slots
from .duplicate_linear import INTERPOLATION_MODES


class CutOnAxisSlots(Slots):
    # Maya's polyCut mutates the mesh in place. On a historyless mesh (frozen /
    # imported) it spawns an intermediate orig-shape that holds the only
    # pristine copy, so the preview's node-diff rollback would bake the cut in
    # instead of reverting it -> cuts stack on every value change. Opting into
    # geometry preservation makes Maya's Preview snapshot the mesh and restore
    # it on rollback; Blender's Preview snapshots every operated object anyway.
    PRESERVE_GEOMETRY = True

    #: The Pivot combo's entries, in order.
    PIVOTS = ("manip", "object", "world", "center")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.cut_on_axis

        # Populate the interpolation combobox (distribution of cuts across the
        # span). Populate before add_reset_buttons so the default is captured.
        self.ui.cmb001.clear()
        self.ui.cmb001.add(INTERPOLATION_MODES, prefix="Interpolation:")
        self.ui.cmb001.setAsCurrent("linear")

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
            undo_message="Cut On Axis",
        )

        # Connect sliders and checkboxes to preview refresh function.
        # s000 Amount, s001 Offset, s002 Spacing, s003 Weight Bias, s004 Weight Curve.
        self.sb.connect_multi(self.ui, "chk001-6", "clicked", self.preview.refresh)
        self.sb.connect_multi(self.ui, "s000-4", "valueChanged", self.preview.refresh)
        self.ui.cmb000.currentIndexChanged.connect(self.preview.refresh)
        self.ui.cmb001.currentIndexChanged.connect(self.preview.refresh)
        self.ui.cmb001.currentIndexChanged.connect(self.toggle_weight_ui)

        # Initialize the weight-field enabled state for the default mode.
        self.toggle_weight_ui()

        # Refresh the preview when the viewport pivot changes (selection, tool
        # or manipulator drag release), where the host has a watcher for it
        # (Maya's scriptJob-driven PivotWatcher; Blender has none yet: a Manip
        # pivot re-samples on the next widget-driven refresh). Gated to an
        # active preview; the watcher dedups by selection + context, so the
        # deferred SelectionChanged the operation's own select fires does not
        # re-enter.
        watcher = getattr(self.tk, "PivotWatcher", None)
        if watcher is not None:
            self._pivot_watcher = watcher(
                self.preview.refresh,
                gate=lambda: self.preview.is_enabled,
                owner=self,
            )
            self._pivot_watcher.start()
            self._pivot_watcher.attach_widget(self.ui)

    def header_init(self, widget):
        """Configure header help text."""
        # Gesture-scoped window: pin button + auto-hide on key_show release.
        widget.config_buttons("menu", "collapse", "pin")
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Cut on Axis",
                body="Slice selected meshes along an axis, then optionally "
                "delete or mirror the cut half.",
                steps=[
                    "Select one or more mesh objects.",
                    "Check an <b>Axis</b> (X / -X / Y / -Y / Z / -Z).",
                    "Pick a <b>Pivot</b> — Manip / Object / World / Center.",
                    "Set <b>Amount</b> (number of slices) and <b>Offset</b>.",
                    "Optionally set <b>Spacing</b> and an <b>Interpolation</b> "
                    "curve to control cut distribution.",
                    "Toggle <b>Preview</b>, then press <b>Cut</b> to commit.",
                ],
                sections=[
                    (
                        "Options",
                        [
                            "<b>Spacing</b> — gap between adjacent cuts. 0 fills "
                            "the axis evenly; &gt;0 fixes the span between cuts.",
                            "<b>Interpolation</b> — distribute cuts across the "
                            "span (linear keeps them even; ease/weighted bias "
                            "density toward one end). <b>Bias</b>/<b>Curve</b> "
                            "tune the selected curve.",
                            "<b>Delete</b> — discard faces on the negative side of "
                            "the axis after cutting.",
                            "<b>Mirror</b> — after deleting one side, mirror the "
                            "remaining half across the axis to rebuild symmetric "
                            "geometry.",
                            "<b>Manip</b> — Maya's manipulator pivot; in Blender, "
                            "the Transform Pivot Point setting.",
                        ],
                    ),
                ],
            )
        )

    def toggle_weight_ui(self):
        """Enable the weight fields only for the modes that consume them:
        'linear'/'smooth_step' use neither; 'weighted' uses both bias and
        curve; every other mode uses the curve only (as Duplicate Linear)."""
        mode = self.ui.cmb001.currentData()
        self.ui.s003.setEnabled(mode == "weighted")  # Weight Bias
        self.ui.s004.setEnabled(mode not in ("linear", "smooth_step"))  # Weight Curve

    def perform_operation(self, objects, contract=None):
        """Cut *objects* (Maya's Preview passes its cleanup *contract*)."""
        pivot_index = self.ui.cmb000.currentIndex()
        pivot = self.PIVOTS[pivot_index] if pivot_index < len(self.PIVOTS) else "center"
        self.tk.CutOnAxis.perform_cut_on_axis(
            objects,
            axis=self.sb.get_axis_from_checkboxes("chk001-4", self.ui),
            pivot=pivot,
            cuts=self.ui.s000.value(),
            cut_offset=self.ui.s001.value(),
            cut_spacing=self.ui.s002.value(),
            distribution=self.ui.cmb001.currentData(),
            weight_bias=self.ui.s003.value(),
            weight_curve=self.ui.s004.value(),
            delete=self.ui.chk005.isChecked(),
            mirror=self.ui.chk006.isChecked(),
            # axis_frame left unset: the panel's pivot names the frame (an
            # object-space pivot cuts along the object's own axes, "world" and
            # "center" cut along the world's).
        )
