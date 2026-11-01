# !/usr/bin/python
# coding=utf-8
"""Bridge: connect two open edge loops with new polygon faces, with a live preview.

One Slots class for both hosts. The engine is the host toolkit's ``Bridge``
and the preview its ``Preview``, both reached through ``self.tk``. ``Bridge``
also names the options its host cannot build (``UNSUPPORTED_OPTIONS``; Blender's
bmesh bridge is linear only), and the panel disables those controls.
"""

from tentacle import Slots


class BridgeSlots(Slots):
    # polyBridgeEdge mutates the mesh in place with construction history. On a
    # historyless mesh (e.g. a freshly combined cylinder) the preview rollback
    # would bake the bridge in when it deletes the auto-created orig-shape,
    # closing the border so the next refresh/commit fails. PRESERVE_GEOMETRY
    # makes Maya's Preview snapshot the owning mesh and restore it on rollback;
    # Blender's Preview snapshots every operated object regardless.
    PRESERVE_GEOMETRY = True

    #: The Type combo's items (cmb000), in order: ``Bridge.bridge``'s curve types.
    CURVE_TYPES = ("linear", "blend", "curve")

    #: The option controls, by the ``Bridge.bridge`` keyword each one sets.
    OPTION_WIDGETS = {"taper": "s003", "twist": "s004", "cleanup_curves": "chk001"}

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.bridge

        # Before add_reset_buttons/connect_multi wrap the widgets.
        self._disable_unsupported_options()

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
            # The preview turns on as the panel opens, so the selected loops
            # bridge at once.
            enable_on_show=True,
            undo_message="Bridge",
        )

        self.sb.connect_multi(
            self.ui, "cmb000", "currentIndexChanged", self.preview.refresh
        )
        self.sb.connect_multi(self.ui, "s000-4", "valueChanged", self.preview.refresh)
        self.sb.connect_multi(self.ui, "chk001", "toggled", self.preview.refresh)

    def _disable_unsupported_options(self):
        """Grey out each control whose ``Bridge.bridge`` option (or Type item)
        the host cannot honor, with the host's reason as its tooltip.

        ``Bridge.UNSUPPORTED_OPTIONS`` maps an option or curve-type name to the
        reason: empty in Maya, the bmesh gaps in Blender. Disabled rather than
        hidden, so the layout stays one panel; a Type item is disabled on its
        own, so Linear still bridges.
        """
        unsupported = self.tk.Bridge.UNSUPPORTED_OPTIONS
        for option, name in self.OPTION_WIDGETS.items():
            reason = unsupported.get(option)
            if reason:
                widget = getattr(self.ui, name)
                widget.setEnabled(False)
                widget.setToolTip(reason)

        model = self.ui.cmb000.model()
        for index, curve_type in enumerate(self.CURVE_TYPES):
            reason = unsupported.get(curve_type)
            item = model.item(index) if reason and model is not None else None
            if item is not None:
                item.setFlags(item.flags() & ~self.sb.QtCore.Qt.ItemIsEnabled)
                item.setToolTip(reason)

    def header_init(self, widget):
        """Configure header help text."""
        # Gesture-scoped window: pin button + auto-hide on key_show release.
        widget.config_buttons("menu", "collapse", "pin")
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Bridge",
                body="Connect two open edge loops with new polygon faces.",
                steps=[
                    "Select the border edges of two open loops on the same mesh, "
                    "with matching edge counts (in Blender: in Edit Mode).",
                    "Pick a <b>Type</b>: Linear / Blend / Curve. Curve builds a "
                    "NURBS handle you can shape, and the bridge rebuilds on each "
                    "preview or commit.",
                    "Adjust <b>Divisions</b>, <b>Smoothing Angle</b>, <b>Offset</b>, "
                    "<b>Taper</b>, and <b>Twist</b>.",
                    "Toggle <b>Preview</b> to iterate, or press <b>Create</b> to "
                    "commit.",
                ],
                notes=[
                    "<b>Cleanup</b> deletes the control curve and construction "
                    "history a Curve bridge leaves behind.",
                    "A control the host cannot build is disabled, its tooltip "
                    "says why (Blender bridges Linear only: no Blend, Curve, "
                    "Taper, Twist or Cleanup).",
                ],
            )
        )

    def perform_operation(self, objects, contract=None):
        """Bridge *objects* (Maya's Preview passes its cleanup *contract*)."""
        index = self.ui.cmb000.currentIndex()
        self.tk.Bridge.bridge(
            objects,
            curve_type=(
                self.CURVE_TYPES[index]
                if 0 <= index < len(self.CURVE_TYPES)
                else "linear"
            ),
            divisions=self.ui.s000.value(),
            smoothing_angle=self.ui.s001.value(),
            offset=self.ui.s002.value(),
            taper=self.ui.s003.value(),
            twist=self.ui.s004.value(),
            cleanup_curves=self.ui.chk001.isChecked(),
        )
