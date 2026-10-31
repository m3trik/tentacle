# !/usr/bin/python
# coding=utf-8
"""Animation: one Slots class for both hosts.

Every key operation is the host toolkit's (``self.tk``): ``AnimUtils``,
``StaggerKeys``, ``ScaleKeys`` and ``SegmentKeys``, one undo step in its host.
A slot reads its option box, calls the operation and words the answer; an
option only one host serves (Maya's Channel Box, its tangent sides, its
dependency-graph traversal) is tagged ``requires`` and hidden on the other.

Each key edit runs under :meth:`AnimationSlots._key_edit`, so the shot claims
of the keys it touches follow them: a key it replaces or deletes takes its
claims with it, a key it moves carries them along.
"""

import contextlib
import logging

from tentacle import Slots

_logger = logging.getLogger(__name__)


class AnimationSlots(Slots):
    #: ``label -> pythontk.MathUtils.round_value mode`` for every snap combo, in
    #: COMBO ORDER: the combos persist by index, so rows are appended here, never
    #: reordered. Read by Snap Keys (tb009) and the Repair list's Snap Fractional
    #: Key Times (tb021).
    SNAP_METHODS = {
        "Nearest": "nearest",
        "Floor": "floor",
        "Ceil": "ceil",
        "Half Up": "half_up",
        "Preferred": "preferred",
        "Aggressive Preferred": "aggressive_preferred",
    }

    #: The Method tooltip of both snap combos (tb009, tb021).
    TIP_SNAP_METHOD = {
        "title": "Method",
        "body": "How a fractional key time is rounded.",
        "sections": [
            (
                "Plain rounding",
                [
                    "<b>Nearest</b> — to the closest whole frame.",
                    "<b>Floor</b> / <b>Ceil</b> — always down / always up.",
                    "<b>Half Up</b> — .5 always rounds up.",
                ],
            ),
            (
                "Clean-number snapping",
                [
                    "<b>Preferred</b> — snap to a round number only "
                    "when very close (24 &#8594; 25, 99 &#8594; 100).",
                    "<b>Aggressive Preferred</b> — snap from farther "
                    "out (48 &#8594; 50, 73 &#8594; 75).",
                ],
            ),
        ],
        "notes": [
            "The clean-number modes move keys that were already on "
            "whole frames — reach for them to tidy timing, not just to "
            "de-fraction it."
        ],
    }

    #: ``category -> [(label, objectName, tooltip, requires)]`` for the Tools
    #: list. *requires* names the one host that serves the row (``None``: both),
    #: applied through uitk's visibility policy like a ``.ui`` widget's tag.
    _TOOLS_ITEMS = {
        "Sequencing": [
            (
                "Shot Manifest",
                "b004",
                "Import a CSV sequence document and build scenes.",
                None,
            ),
            (
                "Shot Sequencer",
                "b000",
                "Open the sequencer for managing per-scene animation with ripple editing.",
                None,
            ),
        ],
        "Repair": [
            (
                "Repair Corrupted Curves",
                "tb015",
                "Repair corrupted animation curves: keys with NaN or infinite values "
                "or absurd key times.\nScoped like the rest of this section: the "
                "selected objects, or the whole scene when nothing is selected.\n"
                "Use the option box to choose which fixes apply.",
                None,
            ),
            (
                "Snap Fractional Key Times",
                "tb021",
                "Put every key sitting on a fractional frame back onto a whole one.\n"
                "Scoped like the rest of this section: the selected objects (in Maya\n"
                "with their descendants), or the whole scene when nothing is selected.\n"
                "Use the option box to choose the rounding method.",
                None,
            ),
            (
                "Repair Visibility Tangents",
                "b001",
                "Force 'step' tangents on visibility curves for selected objects (or all if none selected).",
                "maya",
            ),
        ],
        "Bake": [
            (
                "Smart Bake",
                "tb020",
                "Open the Smart Bake panel.\n"
                "Analyzes and bakes constraints, driven keys and drivers, expressions,\n"
                "IK, motion paths and blend shapes — with a one-click Unbake to\n"
                "reverse the most recent bake, even after a scene reopen.",
                None,
            ),
        ],
        "Stash": [
            (
                "Key Stash",
                "b006",
                "Open the Key Stash: park selected keys out of the working animation\n"
                "(inert, not exported, kept across sessions), preview a stored range\n"
                "on demand, and retrieve it later.",
                None,
            ),
        ],
        "Playback": [
            (
                "Fit Playback Range",
                "b005",
                "Set the playback range to the keyed extent of the selection, "
                "or of the whole scene when nothing is selected.",
                None,
            ),
        ],
        "Info": [
            (
                "Get Animation Info",
                "tb016",
                "Show segmented keyframe info in a formatted viewer.\n"
                "Use the option box to choose scope (Selected / All), sort order "
                "and output flags.",
                None,
            ),
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.animation
        self.submenu = self.sb.loaded_ui.animation_submenu
        # The panel's key clipboard (Copy Keys / Paste Keys): the host's copy
        # buffer and the frame the playhead stood on when it was taken.
        self._copied = None
        self._copied_frame = None

    # ------------------------------------------------------------------ helpers
    @classmethod
    def _count(cls, result):
        """How many things an operation's answer names: a number as it is, a
        sequence by its length, a mapping by its leaves (``{obj: {curve:
        [frames]}}`` counts the frames)."""
        if result is None:
            return 0
        if isinstance(result, (bool, int, float)):
            return int(result)
        if isinstance(result, dict):
            return sum(cls._count(value) for value in result.values())
        try:
            return len(result)
        except TypeError:
            return 1

    @staticmethod
    def _did_nothing(result):
        """Whether an operation's answer says it acted on nothing: ``False``,
        ``0`` or an empty list. ``None`` (an operation that answers nothing)
        says nothing either way."""
        return result is not None and not result

    @contextlib.contextmanager
    def _key_edit(self, label, objects=None, claimed_only=False):
        """Run a key edit under the active shot store's ``key_edit``.

        Yields ``(on_replace, on_move)`` for the edit to take: a key it
        replaces or deletes takes its shot claims with it, and a key it moves
        carries them along. With claims the edit is one undo step paired with
        the store's restore point (``ShotStore.key_edit``).

        A scene whose shot record is unreadable makes ``active()`` raise
        ``ValueError`` (it never reads such a record as empty). The edit still
        runs, as it did before key edits carried claims, with ``(None, None)``
        and the reason logged: a damaged shot record must not take the whole
        Animation panel down with it.

        Parameters:
            label: The undo step's name.
            objects: The objects the edit touches; ``None`` lets the store
                resolve each curve's owners itself.
            claimed_only: Hand no hooks when the store claims nothing -- for an
                edit whose hook costs a key-time read on every key it removes
                (Optimize), so a production scene with no claims pays none.
        """
        try:
            store = self.tk.ShotStore.active()
        except ValueError as error:
            _logger.warning("%s: shot claims not carried: %s", label, error)
            store = None
        if store is None or (claimed_only and not store.edit_ledger):
            yield None, None
            return
        with store.key_edit(label, objects) as hooks:
            yield hooks

    # ------------------------------------------------------------------ Tools list
    def list000_init(self, widget):
        """Tools list: Sequencing / Repair / Bake / Stash / Playback / Info.

        Rows are plain labels dispatched by ``list000``, EXCEPT entries whose
        slot defines an ``*_init``: that init builds the option box (tb015,
        tb016, tb021), which is lost on a plain label, so those are added as
        real slot-wired widgets carrying their original objectNames.

        The submenu hosts the same list where the Shot Sequencer / Shot
        Manifest buttons used to sit (upper-left of the radial overlay), so it
        opens upward over itself and fans left; the panel row fans right.
        Category order follows suit: the upward flyout is anchored at the
        trigger's bottom edge, so its LAST-added row is the one that lands
        under the cursor -- populated in reverse there to put Sequencing (the
        two buttons this list replaced) where those buttons used to be.
        """
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_overlay_up_left" if submenu else "hover_menu")
        root = widget.add(
            "Tools",
            setToolTip="Sequencing, repair, bake, playback and info tools.",
        )
        categories = list(self._TOOLS_ITEMS.items())
        if submenu:
            categories.reverse()
        for category, rows in categories:
            cat = root.sublist.add(category)
            for label, slot_name, tooltip, requires in rows:
                if hasattr(self, f"{slot_name}_init"):
                    item = self.add_slot_widget(
                        cat.sublist,
                        setObjectName=slot_name,
                        setText=label,
                        setToolTip=tooltip,
                    )
                else:
                    item = cat.sublist.add(label, setToolTip=tooltip)
                if requires:
                    self.requires(item, requires)

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Dispatch a Tools leaf to its slot method."""
        self._dispatch_tools_row(item)

    def tb020(self, widget):
        """Smart Bake"""
        self.sb.handlers.marking_menu.show("smart_bake")

    def b000(self):
        """Open Shot Sequencer"""
        self.sb.handlers.marking_menu.show("shot_sequencer")

    def b004(self):
        """Open Shot Manifest"""
        self.sb.handlers.marking_menu.show("shot_manifest")

    def b006(self):
        """Open Key Stash"""
        self.sb.handlers.marking_menu.show("key_stash")

    def b001(self):
        """Repair Visibility Tangents (Maya: the Tools row is ``requires="maya"``):
        stepped tangents on the visibility curves of the selection, or of the
        whole scene when nothing is selected."""
        self.run_operation(
            self.tk.Diagnostics.repair_visibility_tangents,
            objects=self.tk.CoreUtils.selected_objects() or None,
        )

    def b005(self):
        """Fit Playback Range: to the keyed extent of the selection, or of the
        whole scene when nothing is selected."""
        applied = self.tk.AnimUtils.fit_playback_range(
            self.tk.CoreUtils.selected_objects() or None
        )
        if not applied:
            self.sb.message_box("Nothing keyed to fit the playback range to.")
            return
        self.sb.message_box(
            f"Playback range set to <hl>{applied[0]:g}-{applied[1]:g}</hl>."
        )

    # ------------------------------------------------------------------ tb000  Go To Frame
    def tb000_init(self, widget):
        """Go To Frame Init"""
        menu = widget.option_box.menu
        menu.setTitle("Go To Frame")
        menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s000",
            set_limits=[-999999, 999999],
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(
                title="Frame",
                body="The frame to move the playhead to — read as an absolute "
                "frame number or as an offset, per <b>Mode</b> below.",
                notes=["Ignored while a Snap mode other than None is selected."],
            ),
        )
        cmb000 = menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="How the <b>Frame</b> value above is interpreted.",
                bullets=[
                    "<b>Absolute</b> — jump to that frame number.",
                    "<b>Relative</b> — offset from the current frame "
                    "(the default, so <code>1</code> steps forward one frame).",
                ],
            ),
        )
        for text, data in [
            ("Mode: Absolute", "Absolute"),
            ("Mode: Relative", "Relative"),
        ]:
            cmb000.addItem(text, data)
        cmb000.setCurrentIndex(1)

        # Nearest/Floor/Ceil are APPENDED, not inserted in rounding order: the
        # combo persists by index, so reordering would repoint a stored choice.
        cmb001 = menu.add(
            "QComboBox",
            setObjectName="cmb001",
            setToolTip=self.sb.tooltip.fmt(
                title="Snap",
                body="Re-round the <b>current</b> frame to a clean number. Any "
                "mode but None overrides Frame/Mode above — nothing jumps, the "
                "playhead is snapped where it already stands.",
                bullets=[
                    "<b>None</b> — no snapping; Frame/Mode drive the move.",
                    "<b>Preferred</b> — snap to a clean number only when very "
                    "close (24 &#8594; 25, 99 &#8594; 100).",
                    "<b>Aggressive</b> — snap to a clean number even from "
                    "farther out (48 &#8594; 50, 73 &#8594; 75).",
                    "<b>Nearest / Floor / Ceil</b> — plain rounding of a "
                    "fractional playhead to a whole frame.",
                ],
                notes=[
                    "Only Floor and Ceil respond to <b>Invert</b> below — it "
                    "swaps the two.",
                    "(Blender reads the sub-frame playhead, so these are "
                    "meaningful mid-scrub there.)",
                ],
            ),
        )
        for text, data in [
            ("Snap: None", "none"),
            ("Snap: Preferred", "preferred"),
            ("Snap: Aggressive", "aggressive"),
            ("Snap: Nearest", "nearest"),
            ("Snap: Floor", "floor"),
            ("Snap: Ceil", "ceil"),
        ]:
            cmb001.addItem(text, data)
        menu.add(
            "QCheckBox",
            setText="Update",
            setObjectName="chk001",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Update",
                bullets=[
                    "<b>On</b> (default) — the scene re-evaluates at the new "
                    "time, so the viewport follows the playhead.",
                    "<b>Off</b> — only the time slider moves; the world is left "
                    "standing at the old time.",
                ],
                notes=[
                    "Off is the fast way to reposition the playhead in a heavy "
                    "scene without paying for a re-evaluation."
                ],
            ),
        )
        menu.add(
            self.sb.registered_widgets.Label,
            setText="Set To Current Frame",
            setObjectName="lbl020",
            setToolTip="Write the current frame into the Frame field above.",
        )
        menu.lbl020.clicked.connect(
            lambda: menu.s000.setValue(
                int(round(self.tk.AnimUtils.get_current_frame()))
            )
        )
        menu.add(
            "QCheckBox",
            setText="Toggle Single frame",
            setObjectName="chk010",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Toggle Single Frame",
                body="Park <b>Frame</b> at a one-frame nudge "
                "(<code>+1</code>/<code>-1</code>, sign following its current "
                "value) and restore the previous value when unchecked.",
            ),
        )
        widget._previous_frame_value = 1

        def toggle_single_frame(state):
            spinbox = menu.s000
            if state:
                widget._previous_frame_value = spinbox.value() or 1
                spinbox.setValue(-1 if widget._previous_frame_value > 0 else 1)
            else:
                spinbox.setValue(widget._previous_frame_value)

        menu.chk010.toggled.connect(toggle_single_frame)
        menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk011",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Invert",
                body="Reverse the direction of the move.",
                bullets=[
                    "<b>Snap: None</b> — flips the sign of <b>Frame</b>, "
                    "turning a <code>+N</code> nudge into <code>-N</code>. "
                    "The box also tracks the sign, so typing a negative "
                    "Frame ticks it on.",
                    "<b>Snap: Floor / Ceil</b> — swaps the two, so a "
                    "round-down snap rounds up instead.",
                ],
                notes=[
                    "No effect under Preferred, Aggressive or Nearest — "
                    "those modes have no direction to reverse."
                ],
            ),
        )

        def toggle_inverted(_state):
            menu.s000.setValue(-menu.s000.value())

        menu.chk011.toggled.connect(toggle_inverted)

        def update_invert_checkbox(value):
            block = menu.chk011.blockSignals(True)
            menu.chk011.setChecked(value < 0)
            menu.chk011.blockSignals(block)

        menu.s000.valueChanged.connect(update_invert_checkbox)

        # Snapping re-rounds the CURRENT frame, so the frame-entry controls
        # have nothing to feed and grey out for every mode but None.
        self.sb.enable_when(menu, "s000,cmb000,lbl020,chk010", "cmb001", "none")
        # Invert needs a direction to reverse: the Frame field's sign, or a
        # directional snap. The clean-number modes have neither.
        self.sb.enable_when(menu, "chk011", "cmb001", {"none", "floor", "ceil"})

    def tb000(self, widget):
        """Go To Frame: move the playhead to a frame (absolute, or relative to
        the current one), or snap it where it stands."""
        menu = widget.option_box.menu
        snap_mode = menu.cmb001.currentData()
        if snap_mode == "none":
            time = menu.s000.value()
            relative = menu.cmb000.currentData() == "Relative"
        else:  # snap the current frame in place
            time, relative = None, False
        self.tk.AnimUtils.set_current_frame(
            time=time,
            update=menu.chk001.isChecked(),
            relative=relative,
            snap_mode=snap_mode,
            invert_snap=menu.chk011.isChecked(),
        )

    # ------------------------------------------------------------------ tb001  Invert Keys
    def tb001_init(self, widget):
        """Invert Keyframes Init"""
        menu = widget.option_box.menu
        menu.setTitle("Invert Keys")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb035",
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="Which axis of the curve gets mirrored.",
                bullets=[
                    "<b>X</b> — mirror key <i>times</i>: the animation plays backwards.",
                    "<b>Y</b> — mirror key <i>values</i> about <b>Pivot</b>: "
                    "the motion flips, the timing is untouched.",
                    "<b>X &amp; Y</b> — both.",
                ],
                notes=["The Time controls apply to X; Pivot applies to Y."],
            ),
        )
        for text, data in [
            ("Mode: X", "horizontal"),
            ("Mode: Y", "vertical"),
            ("Mode: X & Y", "both"),
        ]:
            cmb.addItem(text, data)
        menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Time: ",
            setObjectName="s001",
            set_limits=[-100000, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Time",
                bullets=[
                    "<b>Auto</b> (-1, default) — mirror the keys <b>in place</b>: "
                    "the animation reverses inside its own range. A move, not a "
                    "copy, so Relative and Delete Original do not apply.",
                    "<b>Any other value</b> — leave the source alone and place a "
                    "<b>reversed copy</b> starting here.",
                ],
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Pivot: ",
            setObjectName="d000",
            set_limits=[-100000, 100000],
            setValue=0.0,
            setToolTip=self.sb.tooltip.fmt(
                title="Pivot",
                body="The value each key is mirrored about in <b>Y</b> mode: a "
                "key at <code>pivot + n</code> lands at <code>pivot - n</code>.",
                notes=["Unused in X mode — there are no values to flip there."],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk002",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Relative",
                bullets=[
                    "<b>On</b> (default) — <b>Time</b> is an offset from the "
                    "last key, so the copy lands just past the source.",
                    "<b>Off</b> — <b>Time</b> is an absolute frame number.",
                ],
                notes=["Ignored while Time is Auto — nothing is copied there."],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Delete Original",
            setObjectName="chk005",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Delete Original",
                body="Remove the source keys once the reversed copy is placed, "
                "turning the copy into a move.",
                notes=[
                    "Already implied when Time is Auto — an in-place mirror is "
                    "a move by definition.",
                    "A source key that a copy key lands on is the copy's now; "
                    "it is not removed.",
                ],
            ),
        )
        # Time controls apply to the X (horizontal) axis, the value pivot to Y.
        # Relative/Delete Original describe the reversed COPY, so they also go
        # dead at Time = Auto, where invert_keys mirrors in place and ignores
        # both.
        self.sb.enable_when(menu, "s001", "cmb035", {"horizontal", "both"})
        self.sb.enable_when(menu, "d000", "cmb035", {"vertical", "both"})
        self.sb.enable_when(
            menu,
            "chk002,chk005",
            ["cmb035", "s001"],
            lambda mode, time: mode in {"horizontal", "both"} and time != -1,
        )

    def tb001(self, widget):
        """Invert Keys: mirror key times and/or values (Maya prefers the keys
        picked in the Graph Editor, falling back to every key)."""
        objects = self.require_selection("Invert Keys requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        time = menu.s001.value()
        # A key the mirror lands on is replaced and one it moves carries its
        # shot claims along; with claims it is one undo step with them.
        with self._key_edit("Invert Keys", objects) as (rep, mov):
            self.run_operation(
                self.tk.AnimUtils.invert_keys,
                objects,
                time=None if time == -1 else time,
                relative=menu.chk002.isChecked(),
                delete_original=menu.chk005.isChecked(),
                mode=menu.cmb035.currentData(),
                value_pivot=menu.d000.value(),
                on_replace=rep,
                on_move=mov,
            )

    # ------------------------------------------------------------------ tb002  Adjust Spacing
    def tb002_init(self, widget):
        """Adjust Spacing Init"""
        menu = widget.option_box.menu
        menu.setTitle("Adjust Spacing")
        menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Frame: ",
            setObjectName="s002",
            set_limits=[-100000, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Frame",
                body="Where the shift starts. Every key at or after this time "
                "moves; everything before it stays put.",
                notes=["<b>Auto</b> (-1) uses the current playhead time."],
            ),
        )
        menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[-100000, 100000],
            setValue=1,
            setToolTip=self.sb.tooltip.fmt(
                title="Amount",
                body="How far the affected keys move.",
                bullets=[
                    "<b>Positive</b> — pushes keys later, opening up time.",
                    "<b>Negative</b> — pulls keys earlier, compressing timing.",
                ],
                notes=[
                    "<b>Exact Gap</b> re-reads this as a target gap size, which "
                    "only makes sense as a positive value."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk004",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Relative",
                body="How <b>Frame</b> above is read — this does not change how "
                "far the keys move.",
                bullets=[
                    "<b>On</b> (default) — Frame is an offset from the current "
                    "playhead time.",
                    "<b>Off</b> — Frame is an absolute frame number.",
                ],
                notes=["Ignored while Frame is Auto."],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Preserve Keys",
            setObjectName="chk003",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Preserve Keys",
                body="If a key already sits exactly on the start frame, re-anchor "
                "it at its own value instead of letting the shift drag it along.",
                notes=[
                    "Only keys the current scope can see count — under "
                    "<b>Scope: Selected Keys</b>, an unselected key on the start "
                    "frame is invisible to this."
                ],
            ),
        )
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb036",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                body="Which curves the shift reaches.",
                bullets=[
                    "<b>Selected Objects</b> — every curve on the selection.",
                    "<b>Selected Keys</b> — only the keys picked in the Graph "
                    "Editor (or Dope Sheet); the object selection is ignored.",
                    "<b>Entire Scene</b> — every animated curve in the scene.",
                ],
            ),
        )
        for text, data in [
            ("Scope: Selected Objects", "objects"),
            ("Scope: Selected Keys", "keys"),
            ("Scope: Entire Scene", "scene"),
        ]:
            cmb.addItem(text, data)
        menu.add(
            "QCheckBox",
            setText="Exact Gap",
            setObjectName="chk021",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Exact Gap",
                body="Re-reads <b>Amount</b> as the gap you want, not the "
                "distance to move: the shift is sized so the first key after the "
                "start frame lands exactly on "
                "<code>start&nbsp;+&nbsp;amount</code>.",
                notes=[
                    "Use it to clear a precise window for new animation, "
                    "whatever the keys were doing before."
                ],
            ),
        )

    def tb002(self, widget):
        """Adjust Spacing: shift every key at or after the frame by the amount."""
        menu = widget.option_box.menu
        scope = menu.cmb036.currentData()
        if scope == "scene":
            objects = None
        else:
            objects = self.require_selection("Adjust Spacing requires a selection.")
            if objects is None:
                return
        time = menu.s002.value()
        # The keys it moves (and any it lands on) carry their shot claims along.
        with self._key_edit("Adjust Spacing", objects) as (rep, mov):
            moved = self.run_operation(
                self.tk.AnimUtils.adjust_key_spacing,
                objects,
                spacing=menu.s003.value(),
                time=None if time == -1 else time,
                relative=menu.chk004.isChecked(),
                preserve_keys=menu.chk003.isChecked(),
                selected_keys_only=scope == "keys",
                exact_gap=menu.chk021.isChecked(),
                on_replace=rep,
                on_move=mov,
            )
        if self._did_nothing(moved):
            self.sb.message_box("No keys at or after the frame.")

    # ------------------------------------------------------------------ tb003  Stagger Keys
    def tb003_init(self, widget):
        """Stagger Keys Init"""
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Stagger Keys",
                body="Re-time the selected objects so their animations play one "
                "after another instead of on top of each other.",
                notes=[
                    "(Maya: with keys selected in the Graph Editor, only those "
                    "keys are staggered; otherwise every key on the selection is.)",
                    "Option box: the gap or fixed interval between blocks, "
                    "grouping for objects that overlap or touch, and the order.",
                ],
            )
        )
        menu = widget.option_box.menu
        menu.setTitle("Stagger Keys")
        menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Start Frame: ",
            setObjectName="s005",
            set_limits=[-100000, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Start Frame",
                body="Where the first block's animation begins.",
                notes=["<b>Auto</b> (-1) starts from the earliest existing key."],
            ),
        )
        # QDoubleSpinBox, not QSpinBox: a value strictly between -1.0 and 1.0
        # is a FRACTION of each block's duration (both hosts' stagger_keys).
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Spacing: ",
            setObjectName="s004",
            set_limits=[-100000, 100000],
            setDecimals=2,
            setSingleStep=1.0,
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(
                title="Spacing",
                sections=[
                    (
                        "Sequential (Use Intervals off)",
                        [
                            "<b>0</b> (default) — blocks run end-to-start with no gap.",
                            "<b>Positive</b> — that many frames of gap.",
                            "<b>Negative</b> — that many frames of overlap.",
                            "<b>Strictly between -1 and 1</b> — read as a "
                            "<i>fraction of each block's own duration</i> "
                            "(<code>0.5</code> = a half-length gap, "
                            "<code>-0.3</code> = a 30% overlap).",
                        ],
                    ),
                    (
                        "Use Intervals on",
                        [
                            "The fixed interval between block starts — "
                            "<code>100</code> places blocks at 0, 100, 200…",
                        ],
                    ),
                ],
                notes=[
                    "The fraction range is exclusive: <code>1.0</code> and "
                    "<code>-1.0</code> mean one literal frame, not 100%."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Use Intervals",
            setObjectName="chk025",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Intervals",
                body="Place each block on a fixed grid instead of packing them "
                "end-to-start.",
                bullets=[
                    "<b>Off</b> (default) — each block starts where the previous "
                    "one ended, plus <b>Spacing</b>.",
                    "<b>On</b> — <b>Spacing</b> becomes the interval between "
                    "block starts (100 &#8594; frames 0, 100, 200…).",
                ],
                notes=[
                    "(Maya: a block too long to fit is pushed on to the next interval.)"
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Group Overlapping",
            setObjectName="chk014",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Group Overlapping",
                body="Objects whose key ranges overlap are re-timed together as "
                "one block, so their relative timing survives the stagger.",
                notes=[
                    "Without this, every object is staggered on its own and "
                    "objects animated in sync come apart."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Group Touching",
            setObjectName="chk029",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Group Touching",
                body="Widen grouping to blocks that merely <i>touch</i> — one "
                "ending on the exact frame the next begins — not just blocks "
                "that overlap.",
                bullets=[
                    "<b>Off</b> (default) — touching blocks stay separate and "
                    "are staggered apart.",
                    "<b>On</b> — they are merged and move as one.",
                ],
                notes=[
                    "Turns <b>Group Overlapping</b> on for you — checking this "
                    "alone is enough."
                ],
            ),
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Channel Box Attrs Only",
                setObjectName="chk024",
                setChecked=False,
                setToolTip=self.sb.tooltip.fmt(
                    title="Channel Box Attrs Only",
                    body="Restrict the stagger to the attributes highlighted in "
                    "the Channel Box, leaving every other curve where it is.",
                    notes=[
                        "With nothing highlighted the operation is refused rather "
                        "than silently widening to every attribute."
                    ],
                ),
            ),
            "maya",
        )
        menu.add(
            "QCheckBox",
            setText="Smooth Tangents",
            setObjectName="chk009",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Smooth Tangents",
                body="Re-solve tangents to auto (auto-clamped) on the re-timed "
                "keys so the seams between staggered blocks do not pop.",
                notes=[
                    "(Maya: visibility curves are forced back to stepped either "
                    "way — a smoothed visibility curve would fade objects in and "
                    "out.)"
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk008",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Invert",
                body="Reverse the order the objects are laid out in, so the last "
                "one goes first.",
            ),
        )

    def tb003(self, widget):
        """Stagger Keys: re-time the selected objects to play one after another."""
        objects = self.require_selection("Stagger Keys requires a selection.")
        if objects is None:  # one object is valid: a re-time via Start Frame
            return
        menu = widget.option_box.menu
        start = menu.s005.value()
        # The keys it re-times carry their shot claims along; a segment laid on
        # the next one's start key replaces it, and takes its claims.
        with self._key_edit("Stagger Keys", objects) as (rep, mov):
            staggered = self.run_operation(
                self.tk.StaggerKeys.stagger_keys,
                objects,
                start_frame=None if start == -1 else start,
                spacing=menu.s004.value(),
                use_intervals=menu.chk025.isChecked(),
                avoid_overlap=True,
                invert=menu.chk008.isChecked(),
                smooth_tangents=menu.chk009.isChecked(),
                group_overlapping=menu.chk014.isChecked(),
                merge_touching=menu.chk029.isChecked(),
                channel_box_attrs_only=menu.chk024.isChecked(),
                verbose=True,
                on_replace=rep,
                on_move=mov,
            )
        if self._did_nothing(staggered):
            self.sb.message_box("Nothing to stagger: the selection holds no keys.")

    # ------------------------------------------------------------------ tb004  Transfer Keys
    def tb004_init(self, widget):
        """Transfer Keys Init"""
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Transfer Keys",
                body="Copy the source object's keyframes onto every other "
                "selected object. The source is the <b>first</b> selected "
                "object (Maya) or the <b>active</b> one (Blender).",
                notes=[
                    "(Maya: with keys selected in the Graph Editor, only those "
                    "keys and their attributes are transferred.)",
                    "Option box: offset the animation onto each target's own "
                    "current pose, and clean up the source before copying.",
                ],
            )
        )
        menu = widget.option_box.menu
        menu.setTitle("Transfer Keys")
        menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk006",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Relative",
                bullets=[
                    "<b>On</b> (default) — the source's motion is offset onto "
                    "each target's own current values, so a target keeps the "
                    "pose it is standing in and inherits the movement.",
                    "<b>Off</b> — targets are keyed to the source's literal "
                    "values and snap onto it.",
                ],
            ),
        )
        # Blender transfers an independent copy of the source's whole action,
        # whose handles travel with it: there is no tangent choice to make.
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Tangents",
                setObjectName="chk007",
                setChecked=True,
                setToolTip=self.sb.tooltip.fmt(
                    title="Tangents",
                    body="Carry the source's tangent handles across as well, so "
                    "the targets ease exactly like the source.",
                    notes=["Off leaves the targets on Maya's default tangents."],
                ),
            ),
            "maya",
        )
        menu.add(
            "QCheckBox",
            setText="Optimize Before Transfer",
            setObjectName="chk035",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Optimize Before Transfer",
                body="Run <b>Optimize Keys</b> over the source first, so "
                "redundant keys are not copied onto every target.",
                notes=[
                    "This edits the source curves, not just the copy — the "
                    "cleanup stays behind after the transfer."
                ],
            ),
        )

    def tb004(self, widget):
        """Transfer Keys: from the source (first selected in Maya, active in
        Blender) onto the other selected objects."""
        menu = widget.option_box.menu
        # A target key a transferred one replaces takes its shot claims with it,
        # and so does a source key the optimize deletes.
        with self._key_edit("Transfer Keys") as (rep, _mov):
            transferred = self.run_operation(
                self.tk.AnimUtils.transfer_keyframes,
                None,
                relative=menu.chk006.isChecked(),
                transfer_tangents=menu.chk007.isChecked(),
                optimize=menu.chk035.isChecked(),
                on_replace=rep,
                on_delete=rep,
            )
        if transferred == []:
            self.sb.message_box("The source object has no keys to transfer.")

    # ------------------------------------------------------------------ tb005  Intermediate Keys
    def tb005_init(self, widget):
        """Add/Remove Intermediate Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Intermediate Keys")
        menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Start Time: ",
            setObjectName="s021",
            set_limits=[-1, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Start Time",
                body="First frame of the window that gets sampled.",
                notes=["<b>Auto</b> (-1) uses each curve's own first key."],
            ),
        )
        menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="End Time: ",
            setObjectName="s006",
            set_limits=[-1, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="End Time",
                body="Last frame of the window that gets sampled.",
                notes=["<b>Auto</b> (-1) uses each curve's own last key."],
            ),
        )
        menu.add(
            "QSpinBox",
            setPrefix="Percent: ",
            setObjectName="s007",
            set_limits=[0, 100],
            setValue=5,
            setToolTip=self.sb.tooltip.fmt(
                title="Percent",
                body="How densely the window is sampled — the share of the "
                "interior frames that get a key, spread evenly.",
                rows=[
                    ("100", "a key on every interior frame (a full bake)"),
                    ("50", "every other frame"),
                    ("5", "the default — a sparse scattering"),
                ],
                notes=[
                    "Density is measured against each curve's <i>own</i> span, "
                    "so short and long curves stay proportionally keyed.",
                    "Never samples to nothing: below one frame's worth it "
                    "still places a single key.",
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Ignore Visibility",
            setObjectName="chk028",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Ignore Visibility",
                body="Leave visibility curves (Blender: <code>hide_viewport</code> "
                "/ <code>hide_render</code>) out of both the add and the remove "
                "pass.",
                notes=[
                    "Worth having on when baking: a sampled visibility curve "
                    "turns a clean on/off switch into a run of stepped keys."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Remove Intermediate Keys",
            setObjectName="chk027",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Remove Intermediate Keys",
                body="Flip the button from adding keys to stripping them.",
                bullets=[
                    "<b>Off</b> (default) — sample new keys across the window "
                    "at <b>Percent</b> density.",
                    "<b>On</b> — cut every key strictly inside the window, "
                    "leaving only its two end keys.",
                ],
                notes=["<b>Percent</b> greys out — it only drives the add pass."],
            ),
        )
        # Percent only drives the add-keys branch.
        self.sb.enable_when(menu, "s007", "chk027", invert=True)

    def tb005(self, widget):
        """Add/Remove Intermediate Keys over a window (-1 on a bound: each
        curve's own first / last key)."""
        objects = self.require_selection("Intermediate Keys requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        start, end = menu.s021.value(), menu.s006.value()
        time_range = (
            None
            if start == -1 and end == -1
            else (None if start == -1 else start, None if end == -1 else end)
        )
        ignore = "visibility" if menu.chk028.isChecked() else None
        if menu.chk027.isChecked():
            # A removed key takes its shot claims with it, as a replaced one does.
            with self._key_edit("Remove Intermediate Keys", objects) as (rep, _mov):
                removed = self.run_operation(
                    self.tk.AnimUtils.remove_intermediate_keys,
                    objects,
                    time_range=time_range,
                    ignore=ignore,
                    on_delete=rep,
                )
            if removed is None:
                return
            count = self._count(removed)
            self.sb.message_box(
                f"Removed {count} intermediate keyframe(s)."
                if count
                else "No intermediate keyframes found to remove."
            )
            return
        added = self.run_operation(
            self.tk.AnimUtils.add_intermediate_keys,
            objects,
            time_range=time_range,
            percent=menu.s007.value(),
            ignore=ignore,
        )
        if self._did_nothing(added):
            self.sb.message_box("No intermediate keys to add in the selection.")

    # ------------------------------------------------------------------ tb006  Move Keys
    def tb006_init(self, widget):
        """Move Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Move Keys")
        menu.add(
            "QCheckBox",
            setText="Move Selected Keys",
            setObjectName="chk031",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Move Selected Keys",
                bullets=[
                    "<b>On</b> (default) — move only the keys picked in the "
                    "Graph Editor (or Dope Sheet).",
                    "<b>Off</b> — move every key on the selected objects.",
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Maintain Spacing",
            setObjectName="chk012",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Maintain Spacing",
                bullets=[
                    "<b>On</b> (default) — the selection moves as one rigid "
                    "block; the offsets between objects are preserved.",
                    "<b>Off</b> — every object is moved onto the current frame "
                    "independently, stacking them together.",
                ],
            ),
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Channel Box Only",
                setObjectName="chk033",
                setChecked=False,
                setToolTip=self.sb.tooltip.fmt(
                    title="Channel Box Only",
                    body="Restrict the move to the attributes highlighted in the "
                    "Channel Box.",
                    notes=["Composes with <b>Move Selected Keys</b> either way."],
                ),
            ),
            "maya",
        )
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb_align",
            setToolTip=self.sb.tooltip.fmt(
                title="Align",
                body="Which end of the moved key range lands on the current frame.",
                bullets=[
                    "<b>Start</b> — the earliest key lands there; the animation "
                    "runs forward from the playhead.",
                    "<b>End</b> — the latest key lands there; the animation "
                    "arrives at the playhead.",
                    "<b>Auto</b> — picks whichever end is nearer: End when the "
                    "range's midpoint sits before the playhead, Start otherwise.",
                ],
            ),
        )
        for text, data in [
            ("Align: Auto", "auto"),
            ("Align: Start", "start"),
            ("Align: End", "end"),
        ]:
            cmb.addItem(text, data)

    def tb006(self, widget):
        """Move Keys: move the selection's keys to the current frame."""
        objects = self.require_selection(
            "Move Keys requires a selection: objects, or objects with keys picked."
        )
        if objects is None:
            return
        menu = widget.option_box.menu
        # A key the move lands on is replaced and one it moves carries its shot
        # claims along.
        with self._key_edit("Move Keys", objects) as (rep, mov):
            moved = self.run_operation(
                self.tk.AnimUtils.move_keys_to_frame,
                objects,
                selected_keys_only=menu.chk031.isChecked(),
                retain_spacing=menu.chk012.isChecked(),
                channel_box_attrs_only=menu.chk033.isChecked(),
                align=menu.cmb_align.currentData(),
                on_replace=rep,
                on_move=mov,
            )
        if self._did_nothing(moved):
            self.sb.message_box("Nothing keyed in the selection to move.")

    # ------------------------------------------------------------------ tb007  Align Keys
    def tb007_init(self, widget):
        """Align Selected Keyframes Init"""
        menu = widget.option_box.menu
        menu.setTitle("Align Selected Keyframes")
        menu.add(
            "QCheckBox",
            setText="Use Earliest Frame",
            setObjectName="chk013",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Earliest Frame",
                body="Which object's selection the others line up with. Each "
                "object's selected keys move as one block, keeping their "
                "spacing, until every selection starts on the same frame.",
                bullets=[
                    "<b>On</b> (default) — the earliest selection start wins.",
                    "<b>Off</b> — the latest selection start wins.",
                ],
                notes=[
                    "Ignored once <b>Frame</b> below is set to anything but "
                    "Auto — an explicit target needs no election."
                ],
            ),
        )
        menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Frame: ",
            setObjectName="spn000",
            setMinimum=-10000,
            setMaximum=10000,
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Frame",
                body="Start every object's selected keys on this exact frame, "
                "each selection keeping its spacing.",
                notes=[
                    "<b>Auto</b> (-1) elects the target from the selection "
                    "instead, per <b>Use Earliest Frame</b> above."
                ],
            ),
        )
        # An explicit target frame makes the earliest/latest election moot.
        self.sb.enable_when(menu, "chk013", "spn000", -1)

    def tb007(self, widget):
        """Align Selected Keyframes: the keys picked in the Graph Editor (or
        Dope Sheet), each object's as one block."""
        objects = self.require_selection(
            "Align Keys requires objects with selected keyframes."
        )
        if objects is None:
            return
        menu = widget.option_box.menu
        frame = menu.spn000.value()
        # A key the block lands on is replaced and one it moves carries its shot
        # claims along; with claims it is one undo step with them.
        with self._key_edit("Align Keys", objects) as (rep, mov):
            aligned = self.run_operation(
                self.tk.AnimUtils.align_selected_keyframes,
                objects,
                target_frame=None if frame == -1 else frame,
                use_earliest=menu.chk013.isChecked(),
                on_replace=rep,
                on_move=mov,
            )
        if self._did_nothing(aligned):
            self.sb.message_box(
                "No selected keyframes found. Select keys in the Graph Editor "
                "(or Dope Sheet) first."
            )

    # ------------------------------------------------------------------ tb008  Visibility Keys
    def tb008_init(self, widget):
        """Set Visibility Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Set Visibility Keys")
        # Visible vs Hidden is a two-valued choice, not a modifier: name both states.
        vis = menu.add(
            "QComboBox",
            setObjectName="cmb_visibility",
            setToolTip=self.sb.tooltip.fmt(
                title="Visibility",
                body="The state written at the chosen frame(s) — <b>Visible</b> "
                "keys the object shown, <b>Hidden</b> keys it hidden (Blender: "
                "<code>hide_viewport</code> and <code>hide_render</code>).",
            ),
        )
        vis.addItems(["Visible", "Hidden"])
        vis.setCurrentText("Visible")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb002",
            setToolTip=self.sb.tooltip.fmt(
                title="When",
                body="Where the visibility key is written.",
                bullets=[
                    "<b>Range Start</b> / <b>Range End</b> — on the first / "
                    "last frame of each object's own keyed range.",
                    "<b>Both Ends</b> — on each end.",
                    "<b>Before Start</b> / <b>After End</b> — one frame outside "
                    "the range, so the state is already settled when the "
                    "animation begins or ends.",
                    "<b>Current Frame</b> — on the playhead, ignoring the "
                    "keyed range entirely.",
                ],
                notes=[
                    "The range is detected per object, so a mixed selection is "
                    "keyed at each object's own boundaries."
                ],
            ),
        )
        # Current Frame is appended last: the combo persists by index.
        for text, data in [
            ("When: Range Start", "start"),
            ("When: Range End", "end"),
            ("When: Both Ends", "both"),
            ("When: Before Start", "before_start"),
            ("When: After End", "after_end"),
            ("When: Current Frame", "current"),
        ]:
            cmb.addItem(text, data)
        menu.add(
            "QSpinBox",
            setPrefix="Offset: ",
            setObjectName="s008",
            set_limits=[-10000, 10000],
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(
                title="Offset",
                body="Nudge the chosen frame(s) — positive moves the key later, "
                "negative earlier.",
                notes=[
                    "Stacks with <b>Before Start</b> / <b>After End</b>, which "
                    "already step one frame out on their own."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Group Overlapping",
            setObjectName="chk016",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Group Overlapping",
                body="Objects whose key ranges overlap are keyed against the "
                "group's combined range instead of each object's own.",
                notes=[
                    "Use it when several objects make up one prop, so the whole "
                    "prop appears and disappears together."
                ],
            ),
        )

    def tb008(self, widget):
        """Set Visibility Keys"""
        objects = self.require_selection("Visibility Keys requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        # A visibility key of the other state it replaces takes its shot claims.
        with self._key_edit("Visibility Keys", objects) as (rep, _mov):
            keyed = self.run_operation(
                self.tk.AnimUtils.set_visibility_keys,
                objects,
                visible=menu.cmb_visibility.currentText() == "Visible",
                when=menu.cmb002.currentData(),
                offset=menu.s008.value(),
                group_overlapping=menu.chk016.isChecked(),
                on_replace=rep,
            )
        if self._did_nothing(keyed):
            self.sb.message_box(
                "No visibility keys set: the selection has no keyed range for "
                "the chosen When mode."
            )

    # ------------------------------------------------------------------ tb009  Snap Keys
    def tb009_init(self, widget):
        """Snap Keys to Frames Init"""
        menu = widget.option_box.menu
        menu.setTitle("Snap Keys to Frames")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb003",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SNAP_METHOD),
        )
        for text, data in self.SNAP_METHODS.items():
            cmb.addItem(text, data)
        menu.add(
            "QCheckBox",
            setText="Selected Keys Only",
            setObjectName="chk017",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Selected Keys Only",
                bullets=[
                    "<b>Off</b> (default) — snap every key on the selected objects.",
                    "<b>On</b> — snap only the keys picked in the Graph Editor "
                    "(or Dope Sheet).",
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Use Time Range",
            setObjectName="chk018",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Time Range",
                body="Limit the snap to keys inside the scene's <b>playback "
                "range</b> (the time slider's start/end; Blender's preview "
                "range when it is on).",
                notes=["Keys outside the range keep their fractional times."],
            ),
        )

    def tb009(self, widget):
        """Snap Keys to Frames"""
        objects = self.require_selection("Snap Keys requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        time_range = None
        if menu.chk018.isChecked():
            settings = self.tk.EnvUtils.scene_settings()
            time_range = (settings["frame_start"], settings["frame_end"])
        # A snap never replaces a key (a taken target is skipped); the keys it
        # moves carry their shot claims along.
        with self._key_edit("Snap Keys", objects) as (_rep, mov):
            snapped = self.run_operation(
                self.tk.AnimUtils.snap_keys_to_frames,
                objects,
                method=menu.cmb003.currentData(),
                selected_only=menu.chk017.isChecked(),
                time_range=time_range,
                on_move=mov,
            )
        if snapped is None:
            return
        count = self._count(snapped)
        self.sb.message_box(
            f"Snapped {count} keyframe(s) to whole frames."
            if count
            else "No keys needed snapping (already on whole frames)."
        )

    # ------------------------------------------------------------------ tb010  Delete Keys
    def tb010_init(self, widget):
        """Delete Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Delete Keys")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb004",
            setToolTip=self.sb.tooltip.fmt(
                title="Time Range",
                body="Which keys, relative to the playhead, are deleted.",
                rows=[
                    ("All Keyframes", "every key on the selection"),
                    ("Current Frame", "only keys sitting on the playhead"),
                    ("Before Current", "everything earlier, playhead kept"),
                    ("Before &amp; Current", "everything earlier, playhead too"),
                    ("After Current", "everything later, playhead kept"),
                    ("Current &amp; After", "everything later, playhead too"),
                ],
            ),
        )
        for text, data in [
            ("All Keyframes", "all"),
            ("Current Frame", "current"),
            ("Before Current", "before"),
            ("Before & Current", "before|current"),
            ("After Current", "after"),
            ("Current & After", "after|current"),
        ]:
            cmb.addItem(text, data)
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Channel Box Only",
                setObjectName="chk020",
                setChecked=False,
                setToolTip=self.sb.tooltip.fmt(
                    title="Channel Box Only",
                    bullets=[
                        "<b>Off</b> (default) — delete keys on every keyable "
                        "attribute.",
                        "<b>On</b> — delete only on the attributes highlighted in "
                        "the Channel Box.",
                    ],
                ),
            ),
            "maya",
        )

    def tb010(self, widget):
        """Delete Keys: on the selection, over the chosen time range."""
        objects = self.require_selection("Delete Keys requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        scope = menu.cmb004.currentData()
        # A deleted key takes its shot claims with it, as a replaced one does.
        with self._key_edit("Delete Keys", objects) as (rep, _mov):
            deleted = self.run_operation(
                self.tk.AnimUtils.delete_keys,
                objects,
                time=None if scope == "all" else scope,
                channel_box_only=menu.chk020.isChecked(),
                on_delete=rep,
            )
        if self._did_nothing(deleted):
            self.sb.message_box("Nothing keyed in the selection for the chosen range.")

    # ------------------------------------------------------------------ tb011  Tie Keyframes
    def tb011_init(self, widget):
        """Tie/Untie Keyframes Init"""
        menu = widget.option_box.menu
        menu.setTitle("Tie/Untie Keyframes")
        menu.add(
            "QCheckBox",
            setText="Use Absolute Range",
            setObjectName="chk023",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Absolute Range",
                body="Which range gets the bookend keys.",
                bullets=[
                    "<b>Off</b> (default) — the scene's playback range.",
                    "<b>On</b> — the true keyed extent, from the earliest to "
                    "the latest key across the objects.",
                ],
                notes=[
                    "Tie only. Untie removes exactly the bookends tying "
                    "inserted, so it has no range to choose."
                ],
            ),
        )
        # Tie vs Untie is a two-valued choice, not a modifier: name both states.
        tie = menu.add(
            "QComboBox",
            setObjectName="cmb_tie",
            setToolTip=self.sb.tooltip.fmt(
                title="Tie / Untie",
                bullets=[
                    "<b>Tie</b> — insert bookend keys at the range boundaries "
                    "so every animated object is pinned at both ends.",
                    "<b>Untie</b> — remove those bookends again, leaving "
                    "genuine animation intact.",
                ],
                notes=[
                    "Scoped to the selected objects, or to every keyed object "
                    "when nothing is selected."
                ],
            ),
        )
        tie.addItems(["Tie", "Untie"])
        tie.setCurrentText("Tie")
        # Absolute range describes where bookends go IN, so it is dead in
        # Untie mode (tb011 only forwards it when tying).
        self.sb.enable_when(menu, "chk023", "cmb_tie", 0)

    def tb011(self, widget):
        """Tie/Untie Keyframes: the selection, or every keyed object when
        nothing is selected."""
        menu = widget.option_box.menu
        objects = self.tk.CoreUtils.selected_objects() or None
        if menu.cmb_tie.currentText() == "Untie":
            # Untie removes exactly the recorded bookends; a removed bookend
            # takes its shot claims with it.
            with self._key_edit("Untie Keys", objects) as (rep, _mov):
                result = self.run_operation(
                    self.tk.AnimUtils.untie_keyframes, objects, on_delete=rep
                )
            verb, nothing = "Untied", "No bookend keys to untie."
        else:
            result = self.run_operation(
                self.tk.AnimUtils.tie_keyframes,
                objects,
                absolute=menu.chk023.isChecked(),
            )
            verb, nothing = "Tied", "Every animated curve already has its bookends."
        if result is None:
            return
        count = self._count(result)
        self.sb.message_box(
            f"{verb} <hl>{count}</hl> bookend key(s)." if count else nothing
        )

    # ------------------------------------------------------------------ tb012 / tb018  Copy / Paste
    def tb012_init(self, widget):
        """Copy Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Copy Keys")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb038",
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="What gets captured from the selection.",
                bullets=[
                    "<b>Auto</b> — the first of these that finds anything: the "
                    "picked keys, the selected channels (Maya), then keyed "
                    "values at the current frame.",
                    "<b>Current Frame</b> — a value snapshot of every keyed "
                    "attribute at the playhead.",
                    "<b>Selected Keys</b> — the picked keys with their times "
                    "and tangents, so a whole passage can be replayed.",
                    "<b>Selected Channels</b> — the values of the highlighted "
                    "channels (Maya: the Channel Box; Blender: the channels "
                    "selected in the animation editors).",
                    "<b>Copy + Paste</b> — capture in Auto mode and immediately "
                    "paste at the playhead onto the same selection, in one click.",
                ],
                notes=[
                    "Everything but Copy + Paste only stores; use <b>Paste "
                    "Keys</b> to apply it.",
                    "Maya copies every selected object and pastes by name; "
                    "Blender copies the active object and pastes onto any.",
                ],
            ),
        )
        for text, data in [
            ("Mode: Auto", "auto"),
            ("Mode: Current Frame", "current_frame"),
            ("Mode: Selected Keys", "selected"),
            ("Mode: Selected Channels", "channel_box"),
            ("Mode: Copy + Paste", "copy_paste"),
        ]:
            cmb.addItem(text, data)

    def tb012(self, widget):
        """Copy Keys: capture the selection's keys or values for Paste Keys (Copy
        + Paste also pastes them at the playhead onto the same selection)."""
        mode = widget.option_box.menu.cmb038.currentData()
        # The copy answers what it captured, or nothing (an empty buffer).
        copied = self.tk.AnimUtils.copy_keys(
            None, mode="auto" if mode == "copy_paste" else mode
        )
        if not copied:
            self.sb.message_box(
                {
                    "auto": "Nothing to copy: no picked keys, selected channels "
                    "or keyed values at the current frame.",
                    "current_frame": "No keyed attributes at the current frame.",
                    "selected": "No keys picked in the Graph Editor (or Dope Sheet).",
                    "channel_box": "No channels selected.",
                    "copy_paste": "Nothing to copy from the selection.",
                }.get(mode, "Nothing to copy.")
            )
            return

        if mode == "copy_paste":
            objects = self.require_selection()
            if objects is None:
                return
            # A pasted key that replaces one takes its shot claims with it.
            with self._key_edit("Paste Keys", objects) as (rep, _mov):
                pasted = self.run_operation(
                    self.tk.AnimUtils.paste_keys,
                    objects,
                    copied,
                    target_time=self.tk.AnimUtils.get_current_frame(),
                    on_replace=rep,
                )
            count = self._count(pasted)
            self.sb.message_box(
                f"Copied and pasted keys onto {count} object(s)."
                if count
                else "No matching objects found."
            )
            return

        self._copied = copied
        self._copied_frame = self.tk.AnimUtils.get_current_frame()
        counts = self.tk.AnimUtils.copied_key_counts(copied)
        self.sb.message_box(
            f"Copied {counts['keys']} key(s) across {counts['attributes']} "
            f"attribute(s) from {counts['objects']} object(s)."
        )

    def tb018_init(self, widget):
        """Paste Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Paste Keys")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb039",
            setToolTip=self.sb.tooltip.fmt(
                title="Paste At",
                bullets=[
                    "<b>At Playhead</b> — shifted so the earliest copied key "
                    "lands on the current frame; later keys keep their "
                    "spacing.",
                    "<b>At Copy Frame</b> — the same, on the frame the playhead "
                    "stood on when the copy was taken, wherever it is now.",
                ],
            ),
        )
        for text, data in [
            ("At Playhead", "playhead"),
            ("At Copy Frame", "source"),
        ]:
            cmb.addItem(text, data)

    def tb018(self, widget):
        """Paste Keys: paste the copied keys onto the selection."""
        if not self._copied:
            self.sb.message_box("No keys stored. Use <b>Copy Keys</b> first.")
            return
        objects = self.require_selection()
        if objects is None:
            return
        target_time = (
            self._copied_frame
            if widget.option_box.menu.cmb039.currentData() == "source"
            else self.tk.AnimUtils.get_current_frame()
        )
        # A pasted key that replaces one takes its shot claims with it.
        with self._key_edit("Paste Keys", objects) as (rep, _mov):
            pasted = self.run_operation(
                self.tk.AnimUtils.paste_keys,
                objects,
                self._copied,
                target_time=target_time,
                on_replace=rep,
            )
        if pasted is None:
            return
        count = self._count(pasted)
        if not count:
            self.sb.message_box(
                "No matching objects found. Select the objects you copied from "
                "(Maya pastes by name)."
            )
            return
        message = f"Pasted keys onto {count} object(s)."
        if count < len(objects):
            message += f"\n{len(objects) - count} object(s) not found in the copy."
        self.sb.message_box(message)

    # ------------------------------------------------------------------ tb013  Select Keys
    def tb013_init(self, widget):
        """Select Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Select Keys")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb041",
            setToolTip=self.sb.tooltip.fmt(
                title="Time Range",
                body="Which keys, relative to the playhead, get selected.",
                rows=[
                    ("All", "every key on the selection"),
                    ("Current", "only keys sitting on the playhead"),
                    ("Before / After", "everything earlier / later, playhead kept"),
                    ("Before|Current", "everything earlier, playhead too"),
                    ("After|Current", "everything later, playhead too"),
                    ("Range", "the explicit Start/End frames below"),
                ],
            ),
        )
        for text, data in [
            ("All", "all"),
            ("Current", "current"),
            ("Before", "before"),
            ("After", "after"),
            ("Before|Current", "before|current"),
            ("After|Current", "after|current"),
            ("Range", "range"),
        ]:
            cmb.addItem(text, data)
        menu.add(
            "QSpinBox",
            setPrefix="Start Frame: ",
            setObjectName="s012",
            set_limits=[-10000, 10000],
            setValue=1,
            setToolTip="First frame of the window, in Range mode.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="End Frame: ",
            setObjectName="s013",
            set_limits=[-10000, 10000],
            setValue=100,
            setToolTip="Last frame of the window, in Range mode.",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Channel Box Only",
                setObjectName="chk034",
                setChecked=False,
                setToolTip=self.sb.tooltip.fmt(
                    title="Channel Box Only",
                    body="Restrict the selection to the attributes highlighted "
                    "in the Channel Box.",
                ),
            ),
            "maya",
        )
        menu.add(
            "QCheckBox",
            setText="Add to Selection",
            setObjectName="chk039",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Add to Selection",
                body="Extend the current key selection instead of replacing it "
                "— run the button repeatedly to build a set out of several "
                "ranges.",
            ),
        )
        # Start/End only feed the explicit Range mode.
        self.sb.enable_when(menu, "s012,s013", "cmb041", "range")

    def tb013(self, widget):
        """Select Keys: on the selection, within a time range (shown in the
        Graph Editor / Dope Sheet)."""
        objects = self.require_selection("Select Keys requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        scope = menu.cmb041.currentData()
        if scope == "range":
            time = (menu.s012.value(), menu.s013.value())
        elif scope == "all":
            time = None
        else:
            time = scope
        selected = self.run_operation(
            self.tk.AnimUtils.select_keys,
            objects,
            time=time,
            channel_box_only=menu.chk034.isChecked(),
            add_to_selection=menu.chk039.isChecked(),
        )
        if selected is None:
            return
        count = self._count(selected)
        self.sb.message_box(
            f"Selected {count} keyframe(s)."
            if count
            else "No keyframes found to select."
        )

    # ------------------------------------------------------------------ tb014  Scale Keys
    def tb014_init(self, widget):
        """Scale Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Scale Keys")
        # Re-applied by the mode switch below, so rendered once here.
        uniform_tooltip = self.sb.tooltip.fmt(
            title="Factor (Uniform mode)",
            body="How the block is stretched in time — read per "
            "<b>Relative / Absolute</b> below.",
            sections=[
                (
                    "Relative — a multiplier",
                    [
                        "<b>1.0</b> — no change.",
                        "<b>0.5</b> — half as long, so it plays twice as fast.",
                        "<b>2.0</b> — twice as long, so it plays half as fast.",
                    ],
                ),
                (
                    "Absolute — a target duration",
                    [
                        "The block is scaled to span exactly this many frames, "
                        "whatever it spanned before.",
                    ],
                ),
            ],
        )
        speed_tooltip = self.sb.tooltip.fmt(
            title="Speed (Speed mode)",
            body="The block is retimed until its sampled world-space motion "
            "hits this speed; the new duration is distance &#247; speed.",
            sections=[
                (
                    "Absolute — a target speed",
                    [
                        "In units per frame. <b>5.0</b> retimes every block to "
                        "travel 5 units each frame, so objects that move "
                        "different distances end up moving at one shared pace.",
                    ],
                ),
                (
                    "Relative — a speed multiplier",
                    [
                        "<b>2.0</b> makes each block twice as fast as it "
                        "already was, keeping their relative pacing.",
                    ],
                ),
            ],
        )
        cmb_mode = menu.add(
            "QComboBox",
            setObjectName="cmb014",
            block_signals_on_restore=False,  # the restore drives update_mode_ui
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="What <b>Factor</b> is measured against.",
                bullets=[
                    "<b>Uniform</b> — plain time scaling about a pivot. Factor "
                    "is a multiplier, or a target duration in frames.",
                    "<b>Speed</b> — the block is retimed until its <i>motion</i> "
                    "hits the target speed; the duration falls out of "
                    "distance &#247; speed. Samples translation and rotation.",
                    "<b>Speed: Linear</b> — translation only.",
                    "<b>Speed: Rotation</b> — rotation only.",
                ],
                notes=[
                    "Speed modes need real world-space movement — an object "
                    "that only changes colour or visibility has no distance to "
                    "normalise and is skipped.",
                    "(Maya: a Graph Editor key selection narrows Uniform mode "
                    "only; Speed modes always retime the whole block.)",
                ],
            ),
        )
        for text, data in [
            ("Uniform Mode", "uniform"),
            ("Speed Mode", "speed"),
            ("Speed Mode: Linear", "speed_linear"),
            ("Speed Mode: Rotation", "speed_rotation"),
        ]:
            cmb_mode.addItem(text, data)
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Factor: ",
            setObjectName="d001",
            setMinimum=0.01,
            setMaximum=100000.0,
            setSingleStep=0.1,
            setValue=1.0,
            setDecimals=2,
            setToolTip=uniform_tooltip,
        )
        cmb_group = menu.add(
            "QComboBox",
            setObjectName="cmb033",
            setToolTip=self.sb.tooltip.fmt(
                title="Grouping",
                body="What shares one pivot and one time range.",
                bullets=[
                    "<b>Single Group</b> — the whole selection scales about one "
                    "pivot, so the objects keep their offsets from each other.",
                    "<b>Per Object Pivots</b> — each object (or, with Split "
                    "Static Segments, each segment) scales about its own start.",
                    "<b>Group Overlaps</b> — objects whose key ranges overlap "
                    "share a group pivot; unrelated objects scale independently.",
                ],
            ),
        )
        for text, data in [
            ("Single Group", "single_group"),
            ("Per Object Pivots", "per_object"),
            ("Group Overlaps", "overlap_groups"),
        ]:
            cmb_group.addItem(text, data)
        cmb_snap = menu.add(
            "QComboBox",
            setObjectName="cmb034",
            setToolTip=self.sb.tooltip.fmt(
                title="Snap",
                body="Scaling lands keys on fractional frames; this decides how "
                "they are rounded back afterwards. Applies to both modes.",
                bullets=[
                    "<b>Nearest</b> (default) — to the closest whole frame.",
                    "<b>Preferred</b> — snap to a clean number when close "
                    "(24 &#8594; 25, 99 &#8594; 100).",
                    "<b>Aggressive</b> — snap to a clean number from farther "
                    "out (48 &#8594; 50, 73 &#8594; 75).",
                    "<b>None</b> — keep the exact decimal times.",
                ],
                notes=[
                    "Pick None when the scale is an intermediate step and the "
                    "rounding error would compound."
                ],
            ),
        )
        for text, data in [
            ("Snap: Nearest", "nearest"),
            ("Snap: Preferred", "preferred"),
            ("Snap: Aggressive", "aggressive_preferred"),
            ("Snap: None", "none"),
        ]:
            cmb_snap.addItem(text, data)
        menu.add(
            "QSpinBox",
            setPrefix="Samples: ",
            setObjectName="s014",
            setMinimum=8,
            setMaximum=512,
            setSingleStep=8,
            setValue=64,
            setToolTip=self.sb.tooltip.fmt(
                title="Samples",
                body="How many points along each block are evaluated to measure "
                "the distance it travels.",
                bullets=[
                    "<b>Higher</b> — truer distance on a curving or "
                    "stop-and-start path, but slower.",
                    "<b>Lower</b> — faster, at the cost of cutting corners.",
                ],
                notes=[
                    "64 is a good balance; 32-128 covers most work.",
                    "Speed modes only — greyed out under Uniform, which needs "
                    "no motion measurement.",
                ],
            ),
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Channel Box Attrs Only",
                setObjectName="chk_channel_box",
                setChecked=False,
                setToolTip=self.sb.tooltip.fmt(
                    title="Channel Box Attrs Only",
                    body="Restrict the scale to the attributes highlighted in the "
                    "Channel Box, leaving every other curve at its current timing.",
                    notes=[
                        "With nothing highlighted the operation is refused rather "
                        "than silently widening to every attribute."
                    ],
                ),
            ),
            "maya",
        )
        # Absolute vs Relative is a two-valued mode, not a modifier: name both states.
        scale_mode = menu.add(
            "QComboBox",
            setObjectName="cmb_scale_mode",
            setToolTip=self.sb.tooltip.fmt(
                title="Relative / Absolute",
                body="Whether <b>Factor</b> is a change or a destination.",
                rows=[
                    ("Uniform · Relative", "a multiplier &mdash; 2.0 is twice as long"),
                    ("Uniform · Absolute", "a target duration in frames"),
                    (
                        "Speed · Relative",
                        "a speed multiplier &mdash; 2.0 is twice as fast",
                    ),
                    ("Speed · Absolute", "a target speed in units per frame"),
                ],
                notes=[
                    "Switching Mode resets this to that mode's usual choice "
                    "&mdash; Relative for Uniform, Absolute for Speed."
                ],
            ),
        )
        scale_mode.addItems(["Relative", "Absolute"])
        scale_mode.setCurrentText("Relative")
        menu.add(
            "QCheckBox",
            setText="Split Static Segments",
            setObjectName="chk_split_static",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Split Static Segments",
                body="Treat an object's separate bursts of animation as "
                "independent blocks, using the flat holds between them as the "
                "cut points.",
                bullets=[
                    "<b>On</b> (default) — each burst is scaled on its own, so "
                    "the holds between them absorb the change.",
                    "<b>Off</b> — every key on the object scales as one block, "
                    "stretching the holds along with the motion.",
                ],
                notes=[
                    "Turn it off when an object's whole timeline is one "
                    "continuous performance you want retimed end to end."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Group Touching",
            setObjectName="chk_merge_touching",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Group Touching",
                body="Widen grouping to blocks that merely <i>touch</i> — one "
                "ending on the exact frame the next begins — not just blocks "
                "that overlap.",
                bullets=[
                    "<b>Off</b> (default) — touching blocks scale separately.",
                    "<b>On</b> — they are merged and scale about one pivot.",
                ],
                notes=[
                    "Only bites under <b>Group Overlaps</b>; the other two "
                    "grouping modes already decide their own blocks."
                ],
            ),
        )
        # Nothing to merge unless the grouping pass looks at ranges.
        self.sb.enable_when(menu, "chk_merge_touching", "cmb033", "overlap_groups")
        cmb_pivot = menu.add(
            "QComboBox",
            setObjectName="cmb_scale_pivot",
            setToolTip=self.sb.tooltip.fmt(
                title="Pivot",
                body="The frame the scale is anchored to — the one point that "
                "does not move.",
                bullets=[
                    "<b>First Key</b> (default) — each group's own start frame, "
                    "so a block grows or shrinks forward from where it began.",
                    "<b>Current Frame</b> — the playhead, for every group. Keys "
                    "before it move the other way.",
                ],
            ),
        )
        for text, data in [
            ("Pivot: First Key", "first_key"),
            ("Pivot: Current Frame", "current"),
        ]:
            cmb_pivot.addItem(text, data)

        def update_mode_ui(index):
            is_speed_mode = index > 0
            menu.s014.setEnabled(is_speed_mode)
            # The RANGE is deliberately mode-independent (see d001 above): a
            # per-mode setRange clamped an Absolute target duration and whatever
            # value the settings restored.
            if is_speed_mode:
                menu.d001.setPrefix("Speed: ")
                menu.d001.setSingleStep(0.5)
                menu.d001.setValue(5.0)
                menu.d001.setToolTip(speed_tooltip)
                menu.cmb_scale_mode.setCurrentText("Absolute")
            else:
                menu.d001.setPrefix("Factor: ")
                menu.d001.setSingleStep(0.1)
                menu.d001.setValue(1.0)
                menu.d001.setToolTip(uniform_tooltip)
                menu.cmb_scale_mode.setCurrentText("Relative")

        cmb_mode.currentIndexChanged.connect(update_mode_ui)
        update_mode_ui(0)

    #: ``cmb014`` data -> ``(mode, include_rotation)`` for ``ScaleKeys.scale_keys``.
    _SCALE_MODES = {
        "uniform": ("uniform", False),
        "speed": ("speed", True),
        "speed_linear": ("speed", False),
        "speed_rotation": ("speed", "only"),
    }

    def tb014(self, widget):
        """Scale Keys: retime the selection's keys about a pivot."""
        objects = self.require_selection("Scale Keys requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        mode, include_rotation = self._SCALE_MODES.get(
            menu.cmb014.currentData(), ("uniform", False)
        )
        factor = menu.d001.value()
        absolute = menu.cmb_scale_mode.currentText() == "Absolute"
        channel_box_only = menu.chk_channel_box.isChecked()
        pivot = (
            self.tk.AnimUtils.get_current_frame()
            if menu.cmb_scale_pivot.currentData() == "current"
            else None
        )
        # A key the scale (or its snap) lands on is replaced and one it moves
        # carries its shot claims along.
        with self._key_edit("Scale Keys", objects) as (rep, mov):
            scaled = self.run_operation(
                self.tk.ScaleKeys.scale_keys,
                objects=objects,
                factor=factor,
                mode=mode,
                pivot=pivot,
                keys="auto",
                channel_box_attrs_only=channel_box_only,
                group_mode=menu.cmb033.currentData(),
                snap_mode=menu.cmb034.currentData(),
                samples=menu.s014.value(),
                include_rotation=include_rotation,
                absolute=absolute,
                split_static=menu.chk_split_static.isChecked(),
                merge_touching=menu.chk_merge_touching.isChecked(),
                prevent_overlap=True,
                verbose=True,
                on_replace=rep,
                on_move=mov,
            )
        if scaled is None:
            return
        count = self._count(scaled)
        if not count:
            self.sb.message_box("No keyframes found to scale.")
            return
        if mode == "speed":
            amount = f"{factor:.2f} units/frame" if absolute else f"{factor:.2f}x speed"
        else:
            amount = f"to {factor:.2f} frames" if absolute else f"{factor * 100:.0f}%"
        context = " (channel box)" if channel_box_only else ""
        self.sb.message_box(f"Scaled {count} keyframe(s){context} {amount}.")

    # ------------------------------------------------------------------ tb015  Repair Corrupted Curves
    def tb015_init(self, widget):
        """Repair Corrupted Curves Init"""
        menu = widget.option_box.menu
        menu.setTitle("Repair Corrupted Curves")
        menu.add(
            "QCheckBox",
            setText="Delete Unfixable Curves",
            setObjectName="chk036",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Delete Unfixable Curves",
                body="Remove curves left with no usable keys once the fixes "
                "below have run.",
                notes=[
                    "Off leaves a broken curve connected but empty, which keeps "
                    "the attribute driven and unkeyable by hand."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Fix Infinite Values",
            setObjectName="chk037",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Fix Infinite Values",
                body="Repair keys whose <i>value</i> is NaN, infinite, or past "
                "the <b>Value Threshold</b> below.",
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Fix Invalid Times",
            setObjectName="chk038",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Fix Invalid Times",
                body="Repair keys sitting at an absurd <i>frame</i> — the "
                "<code>-165916080</code>-style times a corrupted curve picks up "
                "and that stretch the Graph Editor to uselessness.",
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Time Threshold: ",
            setObjectName="d015",
            set_limits=[1000, 999999999],
            setValue=100000,
            setToolTip=self.sb.tooltip.fmt(
                title="Time Threshold",
                body="The largest frame number treated as plausible. A key "
                "beyond it, in either direction, counts as corrupted.",
                notes=["Raise it if a legitimately long scene trips the check."],
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Value Threshold: ",
            setObjectName="d016",
            set_limits=[1000, 999999999],
            setValue=1000000,
            setToolTip=self.sb.tooltip.fmt(
                title="Value Threshold",
                body="The largest key value treated as plausible. Anything "
                "beyond it counts as corrupted.",
                notes=[
                    "Scene-scale dependent — a rig working in millimetres "
                    "needs a higher ceiling than one working in metres."
                ],
            ),
        )

    def tb015(self, widget):
        """Repair Corrupted Curves: the selected objects (in Maya with their
        descendants), or the whole scene when nothing is selected."""
        menu = widget.option_box.menu
        objects = self.tk.CoreUtils.selected_objects() or None
        scope = "the selected objects" if objects else "the scene"
        # A key (or curve) it deletes takes its shot claims with it.
        with self._key_edit("Repair Curves", objects) as (rep, _mov):
            result = self.run_operation(
                self.tk.AnimUtils.repair_corrupted_curves,
                objects,
                delete_corrupted=menu.chk036.isChecked(),
                fix_infinite=menu.chk037.isChecked(),
                fix_invalid_times=menu.chk038.isChecked(),
                time_range_threshold=menu.d015.value(),
                value_threshold=menu.d016.value(),
                on_delete=rep,
            )
        if result is None:
            return
        if not result["corrupted_found"]:
            self.sb.message_box(
                f"No corrupted curves found on {scope}. Animation is clean."
            )
            return
        message = (
            f"Found {result['corrupted_found']} corrupted curve(s) on {scope}:\n"
            f"  • Repaired: {result['curves_repaired']}\n"
            f"  • Deleted: {result['curves_deleted']}\n"
            f"  • Keys fixed: {result['keys_fixed']}"
        )
        details = result.get("details") or []
        if details:
            message += "\n\nFirst issues:\n" + "\n".join(
                f"  • {detail}" for detail in details[:3]
            )
            if len(details) > 3:
                message += f"\n  ... and {len(details) - 3} more"
        self.sb.message_box(message)

    # ------------------------------------------------------------------ tb021  Snap Fractional Key Times
    def tb021_init(self, widget):
        """Snap Fractional Key Times Init"""
        menu = widget.option_box.menu
        menu.setTitle("Snap Fractional Key Times")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb042",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SNAP_METHOD),
        )
        for text, data in self.SNAP_METHODS.items():
            cmb.addItem(text, data)

    def tb021(self, widget):
        """Snap Fractional Key Times: the repair-scoped twin of Snap Keys.

        tb009 is the artist edit: it acts on the objects in hand and refuses to
        run without a selection. This one takes the scope the rest of the
        Repair section takes -- the selected objects (in Maya with their
        descendants), or the whole scene when nothing is selected -- which is
        what a scene arriving with fractional times (a retime, a scaled import)
        needs, and what the exporter's ``check_floating_point_keys`` flags.
        """
        objects = self.tk.CoreUtils.selected_objects() or None
        scope = "the selected objects" if objects else "the scene"
        # The store resolves each curve's owners: the scope reaches descendants.
        with self._key_edit("Snap Keys") as (_rep, mov):
            report = self.run_operation(
                self.tk.AnimUtils.repair_fractional_keys,
                objects,
                method=widget.option_box.menu.cmb042.currentData(),
                on_move=mov,
            )
        if report is None:
            return
        if not report["curves"]:
            self.sb.message_box(f"No animation curves found on {scope}.")
            return
        if not report["snapped"]:
            self.sb.message_box(f"No keys on {scope} sit on a fractional frame.")
            return
        message = f"Snapped {report['snapped']} fractional key(s) on {scope}."
        # A key whose target frame is already taken is SKIPPED, not merged over
        # (merging would discard the tangents of the key already there), so a
        # partial pass is a normal outcome and is said out loud.
        if report["off_frame"]:
            message += (
                "\n\nSome keys are still off-frame: the whole frame they would "
                "land on is already taken, and moving them would discard the "
                "key sitting there. Clear the blocking key and run again."
            )
        self.sb.message_box(message)

    # ------------------------------------------------------------------ tb016  Get Animation Info
    def tb016_init(self, widget):
        """Get Animation Info Init"""
        menu = widget.option_box.menu
        menu.setTitle("Get Animation Info")
        cmb_scope = menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                bullets=[
                    "<b>Selected</b> — only the current selection.",
                    "<b>All Scene Objects</b> — every object in the scene.",
                ],
            ),
        )
        for label, data in [
            ("Scope: Selected", "selected"),
            ("Scope: All Scene Objects", "all"),
        ]:
            cmb_scope.addItem(label, data)
        cmb_traversal = menu.add(
            "QComboBox",
            setObjectName="cmb_traversal",
            setToolTip=self.sb.tooltip.fmt(
                title="Traversal",
                body="Widen the report past the literal selection by walking "
                "the dependency graph, so animation that drives (or is driven "
                "by) the selection is included.",
                bullets=[
                    "<b>None</b> — the selection exactly as picked.",
                    "<b>Upstream</b> — also what feeds it (controls, "
                    "constraints, drivers).",
                    "<b>Downstream</b> — also what it feeds.",
                    "<b>Both</b> — either direction.",
                ],
                notes=[
                    "Greyed out under Scope = All Scene Objects, which "
                    "already covers everything."
                ],
            ),
        )
        self.requires(cmb_traversal, "maya")
        for label, data in [
            ("Traversal: None", None),
            ("Traversal: Upstream", "upstream"),
            ("Traversal: Downstream", "downstream"),
            ("Traversal: Both", "both"),
        ]:
            cmb_traversal.addItem(label, data)
        self.sb.enable_when(menu, "cmb_traversal", "cmb_scope", "selected")
        menu.add(
            "QCheckBox",
            setText="Sort by Time",
            setObjectName="chk_sort_time",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Sort by Time",
                body="Order the report by each entry's start frame instead of "
                "alphabetically by object name — reads as a running order "
                "rather than an index.",
            ),
        )
        menu.add(
            "QCheckBox",
            setText="CSV Output",
            setObjectName="chk_csv_output",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="CSV Output",
                body="Render the report as comma-separated rows, ready to paste "
                "into a spreadsheet.",
                notes=["The viewer switches to a monospace font for CSV."],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Ignore Holds",
            setObjectName="chk_ignore_holds",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Ignore Holds",
                body="Whether a static hold at either end counts as part of an "
                "object's animation.",
                bullets=[
                    "<b>On</b> (default) — ranges report where the object is "
                    "actually <i>moving</i>.",
                    "<b>Off</b> — leading and trailing holds are folded into "
                    "the range, matching the raw key extents.",
                ],
            ),
        )

    def tb016(self, widget):
        """Get Animation Info: render the report to the viewer dialog.

        Feedback while running is the progress bar; the dialog opens when the
        report is ready, which is its own "done" signal.
        """
        menu = widget.option_box.menu
        scope = menu.cmb_scope.currentData() or "selected"
        objects = None
        if scope == "selected":
            objects = self.require_selection(
                "<hl>Nothing selected</hl><br>"
                "Select object(s) or switch Scope to All Scene Objects."
            )
            if objects is None:
                return
        csv_output = menu.chk_csv_output.isChecked()
        with self.sb.progress(text="Working: Get Animation Info") as update:
            text = self.run_operation(
                self.tk.SegmentKeys.format_scene_info_html,
                objects=objects,
                detailed=True,
                by_time=menu.chk_sort_time.isChecked(),
                csv_output=csv_output,
                ignore_holds=menu.chk_ignore_holds.isChecked(),
                traversal=(
                    menu.cmb_traversal.currentData() if scope == "selected" else None
                ),
                progress_callback=self.sb.progress_adapter(update),
            )
        if text is None:
            return
        if not text:
            self.sb.message_box("<hl>No animation</hl> found in the selected scope.")
            return
        # Non-modal viewer, so the host stays responsive while reading.
        self.sb.text_view_dialog(
            text,
            "Ok",
            title="Get Animation Info",
            size=(780, 520),
            monospace=csv_output,
        )

    # ------------------------------------------------------------------ tb017  Step Tangents
    def tb017_init(self, widget):
        """Step Tangents Init"""
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Step Tangents",
                body="Set the interpolation of animation keys: stepped (hold) — "
                "values jump between keys, the blocking / pose-to-pose look — "
                "or back to linear or smooth.",
                notes=[
                    "Option box: the type, which keys to affect (auto, current "
                    "time, selected, all) and, in Maya, which tangent side."
                ],
            )
        )
        menu = widget.option_box.menu
        menu.setTitle("Step Tangents")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb037",
            setToolTip=self.sb.tooltip.fmt(
                title="Keys",
                body="Which keys get the interpolation.",
                bullets=[
                    "<b>Auto</b> — the first of these that finds anything: the "
                    "picked keys, the Channel Box attributes (Maya), keys on "
                    "the current frame, then everything.",
                    "<b>Current Time</b> — only keys sitting on the playhead.",
                    "<b>Selected</b> — only the picked keys; refuses to run if "
                    "none are.",
                    "<b>All</b> — every key on the selected objects.",
                ],
            ),
        )
        for text, data in [
            ("Keys: Auto", "auto"),
            ("Keys: Current Time", "current_time"),
            ("Keys: Selected", "selected"),
            ("Keys: All", "all"),
        ]:
            cmb.addItem(text, data)
        # Blender's interpolation belongs to the segment LEAVING a key, Maya's
        # out side; it has no step-next to set on an in side.
        cmb_tan = menu.add(
            "QComboBox",
            setObjectName="cmb040",
            setToolTip=self.sb.tooltip.fmt(
                title="Tangent",
                body="Which side of the key gets the type.",
                bullets=[
                    "<b>Out</b> (default) — the key holds its value forward "
                    "until the next key, the usual blocking hold.",
                    "<b>In</b> — the key snaps to its value at the last "
                    "moment (<code>stepnext</code>).",
                    "<b>Both</b> — either side.",
                ],
            ),
        )
        self.requires(cmb_tan, "maya")
        for text, data in [
            ("Tangent: Out", "out"),
            ("Tangent: In", "in"),
            ("Tangent: Both", "both"),
        ]:
            cmb_tan.addItem(text, data)
        cmb_interp = menu.add(
            "QComboBox",
            setObjectName="cmb_interp",
            setToolTip=self.sb.tooltip.fmt(
                title="Interpolation",
                body="The type the keys get.",
                bullets=[
                    "<b>Stepped</b> — values hold and jump; the blocking / "
                    "pose-to-pose look.",
                    "<b>Linear</b> — straight ramps between keys, constant "
                    "speed and hard corners.",
                    "<b>Smooth</b> — eased handles (Maya: auto tangents; "
                    "Blender: Bezier).",
                ],
            ),
        )
        for text, data in [
            ("Stepped", "stepped"),
            ("Linear", "linear"),
            ("Smooth", "smooth"),
        ]:
            cmb_interp.addItem(text, data)

    def tb017(self, widget):
        """Step Tangents: set the interpolation of the chosen keys."""
        menu = widget.option_box.menu
        result = self.run_operation(
            self.tk.AnimUtils.set_key_interpolation,
            None,
            interpolation=menu.cmb_interp.currentData(),
            keys=menu.cmb037.currentData(),
            tangent=menu.cmb040.currentData(),
        )
        if result is None:
            return
        if result["curves"]:
            self.sb.message_box(f"Set {result['curves']} curve(s).")
        else:
            self.sb.message_box("No keys found. Select objects with keyframes.")

    # ------------------------------------------------------------------ tb019  Optimize Keys
    def tb019_init(self, widget):
        """Optimize Keys Init"""
        menu = widget.option_box.menu
        menu.setTitle("Optimize Keys")
        menu.add(
            "QCheckBox",
            setText="Remove Static Curves",
            setObjectName="chk000",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Remove Static Curves",
                body="Delete whole curves that never change — animation that "
                "exists but does nothing.",
                notes=[
                    "Maya keeps a curve held at a value other than the "
                    "attribute's default: it is holding a pose. Blender writes "
                    "the held value back to the property before the curve goes, "
                    "so the pose is unchanged."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Remove Flat Keys",
            setObjectName="chk030",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Remove Flat Keys",
                body="Thin out runs of keys that all hold the same value, "
                "keeping the two that bound the hold.",
                notes=[
                    "The timing is unchanged — the hold still starts and ends "
                    "where it did, with fewer keys spelling it out."
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Simplify Curves",
            setObjectName="chk032",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Simplify Curves",
                body="Drop any key whose absence changes the curve's shape by "
                "less than <b>Tolerance</b> (Maya: its <code>keyReducer</code> "
                "filter).",
                notes=[
                    "The one lossy phase — it reshapes moving curves, not just "
                    "redundant ones. Off by default; reach for it on baked or "
                    "mocap data, not on hand-animated curves.",
                    "Ignored while <b>Reduce To Extremes</b> is on, which runs "
                    "its own reduction.",
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Reduce To Extremes",
            setObjectName="chk040",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Reduce To Extremes",
                body="Reduce baked curves to their endpoints, peaks, valleys and "
                "hold boundaries, with tangents refit to trace the baked motion "
                "— a bake thinned to its shape, not reversed (that is Smart "
                "Bake's Unbake).",
                notes=[
                    "Stepped curves get the flat-key pass instead. "
                    "<b>Simplify Curves</b> and <b>Tolerance</b> are ignored.",
                    "Lossy by nature: a sine-like motion drifts by a few percent "
                    "of its amplitude between keys; the report shows the largest "
                    "deviation.",
                ],
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="d017",
            set_limits=[0.0001, 1.0],
            setValue=0.001,
            setDecimals=4,
            setSingleStep=0.001,
            setToolTip=self.sb.tooltip.fmt(
                title="Tolerance",
                body="How far a value may drift before a key is considered "
                "worth keeping. Drives both <b>Remove Flat Keys</b> (how equal "
                "counts as flat) and <b>Simplify Curves</b>.",
                bullets=[
                    "<b>Smaller</b> — more faithful, fewer keys removed.",
                    "<b>Larger</b> — leaner curves, more visible drift.",
                ],
                notes=[
                    "It is measured in scene units, so the same number is "
                    "stricter on a rotation curve than on a translation one.",
                    "Ignored while <b>Reduce To Extremes</b> is on.",
                ],
            ),
        )
        # Reduce To Extremes replaces the simplify/tolerance pass outright (tb019
        # sends a negative tolerance as its sentinel), so both controls grey out.
        self.sb.enable_when(menu, "chk032,d017", "chk040", invert=True)

    @Slots.Cancelable(120)
    def tb019(self, widget):
        """Optimize Keys: remove redundant animation data from the selection,
        or from the whole scene when nothing is selected."""
        menu = widget.option_box.menu
        selected = self.tk.CoreUtils.selected_objects()
        objects = selected or None
        stats = {}
        # A key (or curve) it deletes takes its shot claims with it. Nothing
        # claimed: no hook, so a production scene pays no key-time reads.
        with self._key_edit("Optimize Keys", objects, claimed_only=True) as (rep, _):
            with self.sb.progress(text="Working: Optimize Keys") as update:
                optimized = self.run_operation(
                    self.tk.AnimUtils.optimize_keys,
                    objects,
                    # A negative tolerance is optimize_keys' extremes sentinel.
                    value_tolerance=(
                        -1 if menu.chk040.isChecked() else menu.d017.value()
                    ),
                    remove_static_curves=menu.chk000.isChecked(),
                    remove_flat_keys=menu.chk030.isChecked(),
                    simplify_keys=menu.chk032.isChecked(),
                    recursive=True,
                    quiet=True,
                    stats=stats,
                    progress_callback=self.sb.progress_adapter(update),
                    on_delete=rep,
                )
        if optimized is None and not stats:
            return
        cb, ca = stats.get("curves_before", 0), stats.get("curves_after", 0)
        kb, ka = stats.get("keys_before", 0), stats.get("keys_after", 0)
        scope = "selected objects" if selected else "scene"
        message = (
            f"Optimized {scope}:\n"
            f"  • Curves: {cb} → {ca} ({cb - ca} removed)\n"
            f"  • Keys: {kb:,} → {ka:,} ({kb - ka:,} removed)"
        )
        if kb:
            message += f" ({(1 - ka / kb) * 100:.1f}% reduction)"
        if "reduced" in stats:
            message += (
                f"\n  • Reduced to extremes: {stats['reduced']} curves, "
                f"max deviation {stats['reduce_max_error']:.4f}"
            )
        self.sb.message_box(message)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
