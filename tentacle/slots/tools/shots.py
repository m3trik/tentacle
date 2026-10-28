# !/usr/bin/python
# coding=utf-8
"""Shots: the scene's shot settings, the selected shot's fields and edits, and
the edits every shot takes -- the settings the Shot Manifest and the Shot
Sequencer read from the store.

One Slots class for both hosts: the ``.ui``'s widgets routed to the controller
(:class:`~tentacle.slots.tools._shots.controller.ShotsController`), which
reaches the host's store and ``ShotSequencer`` through ``self.tk``. The shots
engine is pythontk's.
"""

from tentacle import Slots
from ._shots.controller import ShotsController


class ShotsSlots(Slots):
    """Switchboard slots for the ``shots.ui`` panel."""

    #: The option-box rows the controller builds at runtime and the slots below
    #: answer to. No ``.ui`` declares them; saved settings key on these names,
    #: so they never change.
    RUNTIME_WIDGETS = (
        "chk_delete_contents",
        "chk_close_gap",
        "btn_move_shot",
        "cmb_swap_mode",
        "cmb_swap_with",
        "chk_swap_retain_name",
        "chk_swap_retain_description",
        "chk_swap_retain_locked",
        "chk_swap_retain_metadata",
        "btn_trim_leading",
        "btn_trim_trailing",
        "btn_trim_both",
        "btn_trim_all_leading",
        "btn_trim_all_trailing",
        "btn_trim_all_both",
        "btn_add_leading_space",
        "btn_add_trailing_space",
        "spn_gap",
        "cmb_gap_scope",
        "chk_override_locks",
        "spn_shift_all",
        "cmb_delete_scope",
        "chk_drop_stale_shots",
    )

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.shots
        self.controller = ShotsController(self)

    # ---- header ----------------------------------------------------------

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Shots",
                body="Generation settings, shot properties, and gap control shared by the Shot Manifest and Shot Sequencer.",
                sections=[
                    (
                        "Quick Start",
                        [
                            "Choose a generation mode and set <b>Min Gap</b>.",
                            "Open the Shot Manifest or Shot Sequencer to generate shots.",
                            "Edit one shot in <b>Selected Shot</b>; act on the whole timeline in <b>All Shots</b>.",
                            "The shot dropdown's arrows step to the previous / next shot; <b>+</b> appends a new one (Initial Length long, the gap after the last shot).",
                        ],
                    ),
                    (
                        "Generate from Animation",
                        [
                            "<b>Auto-Detect</b> — Scans all scene animation; groups contiguous segments separated by gaps larger than Min Gap.",
                            "<b>All Keys</b> — Each selected keyframe becomes a shot boundary (select keys in the Graph Editor first).",
                            "<b>Skip Zero-Value</b> — Like All Keys but ignores keys with a value of 0.",
                            "<b>Zero = Shot End</b> — Non-zero keys start shots, zero-value keys end them (Min Gap is disabled).",
                            "<b>Min Gap</b> — Minimum frame gap that separates segments into distinct shots.",
                        ],
                    ),
                    (
                        "Build Defaults",
                        [
                            "<b>Initial Length</b> — Default frame length for a new shot before content-driven resizing.",
                            "<b>Fit</b> — Extend Only grows a shot to fit its content but never shrinks. Shrink &amp; Extend resizes to fit exactly.",
                            "<b>Snap to Whole Frames</b> — Round all frame values to integers at write time.",
                        ],
                    ),
                    (
                        "Selected Shot",
                        [
                            "<b>Name</b> — Human-readable shot label.",
                            "<b>Start / End</b> — Frame range (syncs with Sequencer).",
                            "<b>Description</b> — Free-text notes.",
                            "<b>Move To</b> — Set position; click option box ▸ to reorder.",
                            "<b>Swap With</b> — Trades timeline places with the shot picked in the option box ▸ (named on the button), each taking its keys along. <b>Retain</b> options leave a name, description, lock or metadata in place instead, so the animation changes places under them. Mode <b>Copy Over</b> instead replaces the picked shot's animation with a copy of the selected shot's (its length too); the picked shot keeps its name, description, lock and metadata.",
                            "<b>Add Space</b> — Frames of empty room; option box ▸ to add it at the head or the tail. The shot's start never moves: leading room pushes the shot's content and everything after it later. A negative value removes room.",
                            "<b>Trim Empty</b> — Trim both ends; option box ▸ for leading / trailing only.",
                            "<b>Delete</b> — Removes the shot, its keys, and the space it occupied; option box ▸ to keep either.",
                        ],
                    ),
                    (
                        "All Shots",
                        [
                            "<b>Apply Gap</b> — Re-space the shots to the gap its option box ▸ holds. The option box also picks the scope (All Shots / Start / End / Start &amp; End) and <b>Override Locked Gaps</b>, which spends the gap on locked gaps too, without unlocking them.",
                            "<b>Shift To</b> — Moves every shot so the first one starts on the frame set in its option box ▸ (named on the button), keeping their spacing and the animation inside them.",
                            "<b>Trim Empty (All)</b> — Trim every shot; option box ▸ for leading / trailing only.",
                            "<b>Delete Shots</b> — Deletes shot records by scope, picked in the option box ▸ and named on the button: <b>Stale</b> (every object they name is gone from the file and nothing in their frames is keyed; an export ships them as takes that hold still, and names them), <b>Empty</b> (nothing they name is keyed in their frames) or <b>All</b>. No key or other shot moves. The option box's <b>Leave Stale Shots Out of Exports</b> keeps the stale shots' records but leaves them out of every export of this file.",
                        ],
                    ),
                ],
            )
        )

    # ---- widget slots (objectName -> method) ---------------------------------

    def spn_detection(self, value):
        """Detection threshold changed."""
        self.controller.on_detection_changed(value)

    def cmb_detection_mode(self, index):
        """Detection mode combobox changed."""
        self.controller.on_detection_mode_changed(index)

    def spn_initial_length(self, value):
        """Initial shot length changed."""
        self.controller.on_initial_length_changed(value)

    def cmb_fit_mode(self, index):
        """Fit mode combobox changed."""
        self.controller.on_fit_mode_changed(index)

    def chk_snap_whole_frames(self, checked):
        """Snap-to-whole-frames checkbox toggled."""
        self.controller.on_snap_whole_frames_changed(checked)

    # ---- shot editor slots -----------------------------------------------

    def cmb_shot_select(self, index):
        """Shot selector combobox changed."""
        self.controller.on_shot_selected(index)

    def txt_shot_name(self, text=None):
        """Shot name edited (debounced: the field's text, not the signal's)."""
        self.controller.on_shot_name_changed(self.ui.txt_shot_name.text())

    def spn_shot_start(self, value):
        """Shot start frame changed."""
        self.controller.on_shot_start_changed(value)

    def spn_shot_end(self, value):
        """Shot end frame changed."""
        self.controller.on_shot_end_changed(value)

    def txt_shot_desc(self, text=None):
        """Shot description edited (debounced: the field's text)."""
        self.controller.on_shot_desc_changed(self.ui.txt_shot_desc.text())

    def b000(self):
        """Delete the selected shot."""
        self.controller.on_delete_shot()

    def btn_delete_shots(self):
        """Delete the shots of the scope picked in the option box (All Shots)."""
        self.controller.on_delete_shots(self.controller.delete_scope())

    def cmb_delete_scope(self, index):
        """A scope was picked: the button says what a click now deletes."""
        self.controller.label_delete_shots()

    def chk_drop_stale_shots(self, checked):
        """Leave Stale Shots Out of Exports toggled (Delete Shots' option box)."""
        self.controller.on_drop_stale_shots_changed(checked)

    def btn_move_shot(self):
        """Move shot to the position in spn_move_to."""
        self.controller.on_move_shot()

    def btn_swap_shot(self):
        """Swap with, or copy over, the shot picked in the option box."""
        self.controller.on_swap_shot()

    def cmb_swap_with(self, index):
        """A shot was picked: the button names what a click swaps with."""
        self.controller.label_swap_shot()

    def cmb_swap_mode(self, index):
        """A mode was picked: the button says what a click now does."""
        self.controller.label_swap_shot()

    def btn_apply_gap(self):
        """Apply the gap in the option box (spn_gap) to the scope it picks."""
        self.controller.on_gap_changed(
            self.ui.spn_gap.value(),
            scope=self.ui.cmb_gap_scope.currentData(),
            respect_locks=not self.controller._option_checked(
                "chk_override_locks", False
            ),
        )

    def btn_shift_all(self):
        """Re-base every shot onto the frame in the option box (spn_shift_all)."""
        self.controller.on_shift_all_shots(float(self.ui.spn_shift_all.value()))

    def btn_trim_empty(self):
        """Trim both ends of the selected shot."""
        self.controller.on_trim_empty("both")

    def btn_trim_leading(self):
        """Trim the selected shot's leading space."""
        self.controller.on_trim_empty("leading")

    def btn_trim_trailing(self):
        """Trim the selected shot's trailing space."""
        self.controller.on_trim_empty("trailing")

    def btn_trim_both(self):
        """Trim both ends of the selected shot (option box twin of the button)."""
        self.controller.on_trim_empty("both")

    def btn_trim_all(self):
        """Trim both ends of every shot."""
        self.controller.on_trim_all_shots("both")

    def btn_trim_all_leading(self):
        """Trim every shot's leading space."""
        self.controller.on_trim_all_shots("leading")

    def btn_trim_all_trailing(self):
        """Trim every shot's trailing space."""
        self.controller.on_trim_all_shots("trailing")

    def btn_trim_all_both(self):
        """Trim both ends of every shot (option box twin of the button)."""
        self.controller.on_trim_all_shots("both")

    def btn_add_leading_space(self):
        """Add empty room before the selected shot."""
        self.controller.on_add_space("leading")

    def btn_add_trailing_space(self):
        """Add empty room after the selected shot."""
        self.controller.on_add_space("trailing")
