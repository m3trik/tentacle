# !/usr/bin/python
# coding=utf-8
"""Telescope Rig: nested segments that extend and retract between a base and an
end handle, driven by the distance between them.

One Slots class for both hosts over the host toolkit's ``TelescopeRig``
(``self.tk``), which also reads the selection's roles the way the host orders
it (Maya: selection order; Blender, which keeps none: Empties are handles and
the segments run from the active object).
"""

import logging

import pythontk as ptk

from tentacle import Slots


class TelescopeRigSlots(Slots, ptk.LoggingMixin):
    #: The Aim Axis combo's entries, in order (the combo saves its index).
    AXES = ("x", "y", "z")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.telescope_rig
        self.bundle = None  # most recent build, for a selection-less Remove

        # The panel's own records stream to the log panel (txt003).
        self._mirror_engine_log(self)
        self.logger.info("Telescope Rig Tool initialized.", preset="italic")

        # Clickable log links (action:// URIs in the QTextBrowser).
        if hasattr(self.ui.txt003, "anchorClicked"):
            self.ui.txt003.anchorClicked.connect(self._on_log_link_clicked)

        self.ui.btn_build.clicked.connect(self.build_rig)
        self.ui.btn_remove.clicked.connect(self.remove_rig)

        self._init_tooltips()

    def _on_log_link_clicked(self, url) -> None:
        """Dispatch clickable ``action://`` links from the log panel."""
        self.tk.UiUtils.dispatch_log_link(url, self.logger)

    def _mirror_engine_log(self, owner) -> None:
        """Stream *owner*'s log into this panel's browser.

        ``setup_logging_redirect`` also raises the logger to INFO, and that is
        load-bearing for an engine: ``TelescopeRig()`` sets its class logger to
        WARNING, where its report (run banner, build group, summary box) is
        gated off. So each engine is mirrored AFTER it is constructed.
        """
        owner.logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
        owner.logger.setup_logging_redirect(self.ui.txt003)

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Telescope Rig",
                body="Build a telescoping segment rig: nested segments extend "
                "and retract between a base and an end handle, driven by the "
                "distance between them.",
                sections=[
                    (
                        "Selection",
                        [
                            "<b>Segments</b> — at least 2. Maya follows the "
                            "selection order (base end first); Blender, which "
                            "keeps none, orders them by distance from the "
                            "<b>active</b> object, so make the base end active.",
                            "<b>Handles</b> — optional: locators in Maya, Empties "
                            "in Blender. In Maya a handle selected first is the "
                            "base and one selected last the end; in Blender each "
                            "goes to the end of the strut it sits nearer. Any "
                            "handle you leave out is created for you at the outer "
                            "end of the strut.",
                        ],
                    ),
                ],
                steps=[
                    "Select the segments, and your own base/end handles if you "
                    "want to control where they sit.",
                    "Set <b>Aim Axis</b> to the segments' long axis.",
                    "Leave <b>Collapsed Dist</b> on <i>Auto</i>, or enter the "
                    "base-to-end distance at which the segments are fully "
                    "retracted.",
                    "Press <b>Build Telescope Rig</b>.",
                ],
                notes=[
                    "Two segments build a sliding strut: the halves ride their "
                    "handles and never stretch.",
                    "<b>Remove Telescope Rig</b> tears down the rig on the "
                    "selection (or the last one built), including any handles "
                    "it created.",
                    "Build results stream to the log panel; object names there "
                    "are links that select the object.",
                    "A build is one undo step, and so is a removal.",
                ],
            )
        )

    def _init_tooltips(self):
        """Set the polished (uitk ``fmt``) tooltips for every option and action."""
        ui = self.ui

        ui.cmb_axis.setToolTip(
            self.sb.tooltip.fmt(
                title="Aim Axis",
                body="The segments' long axis — the local axis that points "
                "from the base toward the end handle. The rig aims every "
                "segment along it and drives that axis' scale.",
                notes=[
                    "The other two scale channels are locked at build time "
                    "so the stack can't shear.",
                    "Auto-created handles are placed along this axis, at the "
                    "outer ends of the first and last segment.",
                ],
            )
        )
        ui.spin_collapsed.setToolTip(
            self.sb.tooltip.fmt(
                title="Collapsed Distance",
                body="Base-to-end distance at which the segments are fully "
                "retracted (nested). As the end handle pulls farther than "
                "this, the segments slide apart to bridge the gap.",
                notes=[
                    "<b>Auto</b> (0) measures the longest segment along the "
                    "aim axis — fully nested, the strut is as long as its "
                    "longest tube.",
                    "Must be greater than 0 and less than the current "
                    "base-to-end distance.",
                    "Pushing closer than this distance clamps the segments "
                    "at their fully-nested size.",
                    "Ignored for a two-segment strut — there is no interior "
                    "segment to scale.",
                ],
            )
        )
        ui.btn_build.setToolTip(
            self.sb.tooltip.fmt(
                title="Build Telescope Rig",
                body="Wires the segments so they extend and retract as the gap "
                "between the base and end handles changes.",
                steps=[
                    "Select the <b>segments</b> <i>(min 2)</i>: in extension "
                    "order in Maya; in Blender with the base end <b>active</b>.",
                    "Optionally add your own <b>base</b>/<b>end</b> handles "
                    "(locators in Maya, Empties in Blender) — either one you "
                    "omit is created at the outer end of the strut.",
                    "Press <b>Build Telescope Rig</b>.",
                ],
                notes=[
                    "Needs at least 2 segments: two is a sliding strut, three "
                    "or more telescope.",
                    "Object names in the log are links that select the object.",
                ],
            )
        )
        ui.btn_remove.setToolTip(
            self.sb.tooltip.fmt(
                title="Remove Telescope Rig",
                body="Deletes what the build created (constraints and the "
                "distance-driven scaling), restores the channel locks it "
                "changed, and puts the segments back on their build pose.",
                steps=[
                    "Select any part of the rig — a handle or a segment.",
                    "Press <b>Remove Telescope Rig</b>.",
                ],
                notes=[
                    "Handles the build created are deleted; handles you "
                    "supplied are kept.",
                    "With nothing selected, the most recent build in this "
                    "session is removed.",
                    "The build record is stamped on the base handle, so a rig "
                    "from an earlier session still tears down cleanly.",
                ],
            )
        )

    def _aim_axis(self) -> str:
        """The Aim Axis combo's axis token (``"y"`` for an unset combo)."""
        index = self.ui.cmb_axis.currentIndex()
        return self.AXES[index] if 0 <= index < len(self.AXES) else "y"

    def build_rig(self):
        """Build Telescope Rig: rig the selected segments between their handles."""
        base_locator, segments, end_locator = self.tk.TelescopeRig.partition_selection()
        if len(segments) < 2:
            self.logger.error("Insufficient selection.")
            self.sb.message_box(
                "Selection Error:\n"
                "Select at least 2 segments:\n"
                "1. Segments (min 2) — in selection order (Maya), or ordered "
                "by distance from the active object (Blender)\n"
                "2. Base/End handles (optional — locators in Maya, Empties in "
                "Blender; created if omitted)"
            )
            return

        collapsed_distance = self.ui.spin_collapsed.value() or None  # 0 is Auto
        aim_axis = self._aim_axis()

        try:
            rig = self.tk.TelescopeRig()
            self._mirror_engine_log(rig)

            # ONE record for the whole read-back of the selection: separate
            # info lines render as blank-line-separated paragraphs above the
            # engine's own banner.
            if self.logger.isEnabledFor(logging.INFO):
                detected = []
                for role, node in (("Base", base_locator), ("End", end_locator)):
                    if node is None:
                        detected.append(f"{role:<9}: auto (created)")
                    else:
                        link = self.logger.log_link(node, "select", node=node)
                        detected.append(f"{role:<9}: {link}")
                detected.append(
                    f"{'Segments':<9}: {len(segments)} (aim axis {aim_axis.upper()})"
                )
                self.logger.log_group("Selection", detected)

            self.bundle = rig.setup_telescope_rig(
                base_locator=base_locator,
                end_locator=end_locator,
                segments=segments,
                collapsed_distance=collapsed_distance,
                aim_axis=aim_axis,
            )
        except Exception as e:
            self.logger.error(f"Error setting up rig: {e}")
            self.sb.message_box(f"Error setting up rig: {e}")

    def remove_rig(self):
        """Remove Telescope Rig: tear down the rigs on the selection, or the
        session's last build with nothing selected."""
        selection = self.tk.CoreUtils.selected_objects()
        if selection:
            bundles = self.tk.TelescopeRig.find_bundles(selection)
            empty_msg = "No telescope rig found on the selected objects."
        else:
            bundles = [self.bundle] if self.bundle else []
            empty_msg = (
                "Nothing selected and no rig built this session.\n"
                "Select a rig handle or segment and try again."
            )
        if not bundles:
            self.logger.error(empty_msg.splitlines()[0])
            self.sb.message_box(empty_msg)
            return

        try:
            rig = self.tk.TelescopeRig()
            self._mirror_engine_log(rig)
            rig.teardown(bundles)  # every rig in one call: one undo step
            if self.bundle in bundles:  # equal: the same rig, found again
                self.bundle = None
        except Exception as e:
            self.logger.error(f"Error removing rig: {e}")
            self.sb.message_box(f"Error removing rig: {e}")
