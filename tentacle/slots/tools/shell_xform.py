# !/usr/bin/python
# coding=utf-8
"""Shell Xform: move, flip, rotate, straighten, mirror, distribute, align and
orient the selected UV shells.

One Slots class for both hosts over the host toolkit's ``UvUtils`` (with its
``CoreUtils`` for the selection and ``UiUtils`` for the UV Editor), reached
through ``self.tk``. The move pad's step and snap math is pythontk's, so it is
the same rule in both hosts.
"""

import pythontk as ptk

from tentacle import Slots


class ShellXformSlots(Slots):
    #: SVG arrow icon installed on each move-pad button (Rotate keeps its glyphs).
    _MOVE_ICONS = {
        "b023": "arrow_left",
        "b025": "arrow_up",
        "b024": "arrow_down",
        "b026": "arrow_right",
    }

    #: Move-pad scope -> step in UV units, carried as the combo item's *data* so
    #: the label and the step it means cannot drift apart. ``None`` = derived at
    #: click time from the selection's own UV bounds.
    _MOVE_SCOPES = {
        "Tile": 1.0,
        "Half Tile": 0.5,
        "Quarter Tile": 0.25,
        "Selection Bounds": None,
    }

    # Snap modes for the move pad's option-box button, in cycle order (the
    # indices ARE the cycle positions, so `_snap_states` must list them in this
    # order). One tri-state button rather than two: the modes are mutually
    # exclusive answers to a single question — snap to what?
    _SNAP_OFF, _SNAP_GRID, _SNAP_SHELL = range(3)

    #: A UV extent at or below this is treated as collapsed: dividing by it would
    #: blow the grid math up, so the arrow falls back to a whole tile.
    _MIN_EXTENT = 1e-6

    #: Map size the tile border padding derives from. The normalized margin is
    #: map-size-invariant (``uv_tile_margin`` == 1/512 at every resolution), so
    #: this only names the rule — the panel needs no map-size control.
    _MAP_SIZE = 4096

    _NOTHING_SELECTED = "<b>Nothing selected.</b><br>Select mesh(es), faces, or UVs."
    _NO_UVS = (
        "<b>No UVs found.</b><br>Select a mesh, faces, edges, or UVs that carry UVs."
    )

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.shell_xform
        # Randomize advances the seed per click, so repeated clicks re-shuffle
        # rather than re-apply one offset.
        self._randomize_seed = 0

        # The move-pad icons are installed on the next event-loop tick: the
        # switchboard builds this slots instance mid-load, so the child widgets
        # aren't wired onto self.ui until register_children runs after __init__.
        self.sb.QtCore.QTimer.singleShot(0, self._initialize_ui)

    def _initialize_ui(self):
        """Install the move-pad arrow icons (deferred; see __init__)."""
        for name, icon in self._MOVE_ICONS.items():
            widget = getattr(self.ui, name, None)
            if widget is not None:
                widget.setText("")
                self.sb.IconManager.set_icon(widget, icon, size=(16, 16))

    def header_init(self, widget):
        """Header menu — Open UV Editor + panel help."""
        # Gesture-scoped window: pin button + auto-hide on key_show release.
        widget.config_buttons("menu", "collapse", "pin")
        widget.menu.add(
            "QPushButton",
            setText="Open UV Editor",
            setObjectName="open_uv_editor",
            setToolTip="Open the UV Editor to inspect the result.",
        )
        widget.menu.open_uv_editor.clicked.connect(self.open_uv_editor)
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Shell Xform",
                body="Move, flip, rotate, align, orient, and distribute the "
                "selected UV shells.",
                steps=[
                    "Select mesh(es), faces, or UVs (in Blender: mesh objects; "
                    "Move and Rotate shift each one's whole UV map, and the other "
                    "tools act on the shells the Edit Mode selection touches).",
                    "<b>Move</b> nudges the selection by one <i>scope</i> — a "
                    "whole tile, a fraction of one, or the selection's own size.",
                    "The snap button beside the scope cycles three modes: "
                    "<b>grey ▦</b> off (offset by the scope, keeping any drift), "
                    "<b>blue ▦</b> snap to the scope's grid inset by the border "
                    "padding, and <b>amber ⌖</b> snap to the next <i>shell</i> — "
                    "park against the nearest neighbour in that direction, "
                    "skipping gaps too small to fit and falling back to the grid "
                    "when nothing lies ahead.",
                    "<b>Gather to Tile</b> moves shells sitting outside the "
                    "selection's UDIM tile into it — whole-tile offsets keep "
                    "each shell's sub-tile position (no repack).",
                    "<b>Flip</b> mirrors each shell about its own center; "
                    "<b>Rotate</b> spins the selection about its center by the "
                    "angle field.",
                    "<b>Straighten / Mirror / Distribute</b> each expose their "
                    "own options in the option box (▸).",
                ],
                sections=[
                    (
                        "Align / Orient",
                        [
                            "<b>Align</b> snaps the selection's U or V to its min / "
                            "center / max, or spreads them along a line.",
                            "<b>Orient Shells</b> squares each shell to the nearest "
                            "axis; <b>To Edges</b> orients to a selected edge.",
                        ],
                    ),
                ],
            )
        )

    def _selection(self, message=None):
        """The current selection, or ``[]`` after showing *message* when it is
        empty: the shared guard every op slot runs first."""
        selection = self.tk.CoreUtils.selected_objects()
        if not selection:
            self.sb.message_box(message or self._NOTHING_SELECTED)
        return selection

    # ------------------------------------------------------------------ move to UV space (b023-b026)
    def cmb_move_scope_init(self, widget):
        """Move scope — how far one arrow press travels, plus the snap button.

        Items are built from ``_MOVE_SCOPES`` with the step as item data, so the
        step is read straight off the current item — a label edited in one place
        can no longer mean a different distance somewhere else. Snap rides along
        as an option-box button rather than extra items, because the mode
        composes with every scope instead of replacing one.
        """
        if widget.is_initialized:
            return
        widget.add(self._MOVE_SCOPES)
        # The ActionOption owns its own index persistence, so the restored mode
        # is whatever the user left it on. A fresh key: the old one held a bool
        # and would restore as a state index.
        self._snap_action = widget.option_box.set_action(
            states=self._snap_states(),
            settings_key="shell_xform_move_snap_mode",
        )

    def _snap_states(self):
        """Option-box cycle states for the snap button, in `_SNAP_*` order.

        Icon *and* tint change per state: two enabled modes are easy to confuse
        by colour alone, and the off state has to read as inert at a glance.
        Colours come from the shared status palette so they track the theme.
        """
        status = ptk.Palette.status()
        return [
            {
                "icon": "grid",
                "color": status["locked"][0],
                "tooltip": "Snap: off. Arrows offset by the scope, keeping any "
                "sub-tile drift. Click to snap to the grid.",
            },
            {
                "icon": "grid",
                "color": status["info"][0],
                "tooltip": "Snap: grid. Arrows land the selection on the scope's "
                "grid, inset by the tile border padding. Click to snap to shells.",
            },
            {
                "icon": "target",
                "color": status["warn"][0],
                "tooltip": "Snap: shell. Arrows park the selection against the "
                "next shell in that direction, keeping the border padding, and "
                "skip gaps too small to fit. Falls back to the grid when nothing "
                "lies ahead. Click to turn snapping off.",
            },
        ]

    def _snap_mode(self) -> int:
        """Current snap mode — `_SNAP_OFF`, `_SNAP_GRID`, or `_SNAP_SHELL`."""
        action = getattr(self, "_snap_action", None)
        return self._SNAP_OFF if action is None else int(action.current_state)

    def _move_step(self, bounds) -> tuple:
        """Per-axis ``(step_u, step_v)`` for the current scope.

        The step comes from the current item's data; ``None`` means "derive it
        from the selection", which is what *bounds* — a ``(u_min, v_min, u_max,
        v_max)`` tuple — is for. A degenerate extent (a shell collapsed on one
        axis) falls back to a whole tile so the arrow still does something.
        """
        step = self.ui.cmb_move_scope.currentData()
        if step is not None:
            return (step, step)

        u_min, v_min, u_max, v_max = bounds
        width, height = u_max - u_min, v_max - v_min
        return (
            width if width > self._MIN_EXTENT else 1.0,
            height if height > self._MIN_EXTENT else 1.0,
        )

    def _move(self, du: int, dv: int):
        """Nudge the selected UVs one step along ``(du, dv)``.

        The snap mode picks the rule: ``_SNAP_OFF`` offsets by the scope,
        ``_SNAP_GRID`` lands on the scope's padded grid, and ``_SNAP_SHELL``
        parks against the next neighbouring shell. Shell snap ignores the scope
        entirely — the neighbour sets the distance — and degrades to the grid
        rule whenever nothing lies ahead, so the arrow never reads as dead.
        """
        objects = self._selection(
            "<b>Nothing selected.</b><br>Select a mesh, faces, or UVs to move."
        )
        if not objects:
            return

        uv = self.tk.UvUtils
        bounds = uv.get_uv_bounds(objects)
        if bounds is None:
            self.sb.message_box(self._NO_UVS)
            return

        mode = self._snap_mode()
        snap = mode != self._SNAP_OFF
        margin = self._border_margin() if snap else 0.0

        offset_u = offset_v = None
        if mode == self._SNAP_SHELL:
            blockers = uv.get_neighbor_shell_bounds(objects)
            # Only the travelled axis can resolve — the other's direction is 0,
            # which `next_clear_offset` reports as None.
            offset_u = ptk.MathUtils.next_clear_offset(
                bounds, blockers, 0, du, margin=margin
            )
            offset_v = ptk.MathUtils.next_clear_offset(
                bounds, blockers, 1, dv, margin=margin
            )

        if offset_u is None and offset_v is None:
            # Snap anchors on the selection's lower-left corner, so "up" means the
            # shell's bottom edge lands on the next grid line — what the eye expects.
            # The grid is offset by the tile border padding, so a snapped shell sits
            # just inside the line rather than on it (a shell exactly on a tile seam
            # bleeds across it at render time). Snapping the *unpadded* anchor and
            # adding the margin back keeps the grid uniform in both directions —
            # padding the result instead would strand the reverse press on the
            # margin it just added, and the arrow would read as dead.
            step_u, step_v = self._move_step(bounds)
            offset_u = ptk.MathUtils.step_offset(
                bounds[0] - margin, step_u, du, snap=snap
            )
            offset_v = ptk.MathUtils.step_offset(
                bounds[1] - margin, step_v, dv, snap=snap
            )

        uv.move_to_uv_space(objects, offset_u or 0.0, offset_v or 0.0)

    def _border_margin(self) -> float:
        """Normalized tile border the snap keeps clear.

        Gather derives the same margin inside the engine from the same
        ``_MAP_SIZE``, and Distribute leaves it between shells, so every route
        insets by an identical amount.
        """
        return ptk.MathUtils.uv_tile_margin(self._MAP_SIZE)

    def b023(self):
        """Move To UV Space: Left"""
        self._move(-1, 0)

    def b024(self):
        """Move To UV Space: Down"""
        self._move(0, -1)

    def b025(self):
        """Move To UV Space: Up"""
        self._move(0, 1)

    def b026(self):
        """Move To UV Space: Right"""
        self._move(1, 0)

    def gather_to_udim(self):
        """Move shells sitting outside the selection's UDIM tile into it.

        The cheap counterpart to a repack: each stray shell keeps its
        sub-tile position, inset by the same border padding the snap uses.
        The target tile is the one most of the selection's shells already
        occupy, so the majority stays put.
        """
        objects = self._selection(
            "<b>Nothing selected.</b><br>Select mesh(es), faces, or UVs to gather."
        )
        if not objects:
            return

        moved = self.tk.UvUtils.gather_to_udim(objects, map_size=self._MAP_SIZE)
        if moved is None:
            self.sb.message_box(self._NO_UVS)
        elif not moved:
            self.sb.message_box(
                "<b>Nothing to gather.</b><br>Every shell is in the tile."
            )

    # ------------------------------------------------------------------ flip / rotate (b034-b037)
    def _flip(self, axis):
        """Geometrically flip the selected UVs across *axis* ('u'/'v'), each shell
        about its own center (the host's ``UvUtils.mirror_uvs``, footprint
        preservation off)."""
        objects = self._selection(
            "<b>Nothing selected.</b><br>Select a mesh, faces, or UVs to flip."
        )
        if objects:
            self.tk.UvUtils.mirror_uvs(
                objects, axis=axis, per_shell=True, preserve_position=False
            )

    def b034(self):
        """Flip U: mirror the selected UVs horizontally about each shell's center."""
        self._flip("u")

    def b035(self):
        """Flip V: mirror the selected UVs vertically about each shell's center."""
        self._flip("v")

    def _rotate(self, angle):
        """Rotate the selected UVs by *angle* degrees (CCW) about their center."""
        objects = self._selection()
        if objects and not self.tk.UvUtils.rotate_uvs(objects, angle):
            self.sb.message_box(self._NO_UVS)

    def b036(self):
        """Rotate the selected UVs counter-clockwise by the s041 angle."""
        self._rotate(self.ui.s041.value())

    def b037(self):
        """Rotate the selected UVs clockwise by the s041 angle."""
        self._rotate(-self.ui.s041.value())

    def s041(self, value, widget):
        """Rotate Angle — passive input; read by the Rotate buttons (b036/b037). Nothing to do."""

    # ------------------------------------------------------------------ tb005  Straighten
    def tb005_init(self, widget):
        """Initialize Straighten UV"""
        widget.option_box.menu.setTitle("Straighten")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Angle: ",
            setObjectName="s001",
            set_limits=[0, 360],
            setValue=30,
            setToolTip="Maximum angle used for straightening UVs.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Straighten UV",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Snap near-horizontal UV edges flat.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Straighten V",
            setObjectName="chk019",
            setChecked=True,
            setToolTip="Snap near-vertical UV edges flat.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Straighten Shell",
            setObjectName="chk020",
            setToolTip="Straighten the whole shell by unfolding its UVs around a "
            "selected UV's edge loop.",
        )

    def tb005(self, widget):
        """Straighten UV: selected UV edges within the angle snap flat; optionally
        straighten each whole shell too."""
        menu = widget.option_box.menu
        objects = self._selection(
            "<b>Nothing selected.</b><br>Select UV edges to straighten."
        )
        if not objects:
            return

        uv = self.tk.UvUtils
        # One undo step for the click: the edge pass and the shell pass are two
        # engine calls.
        with self.tk.CoreUtils.undo_chunk("Straighten UVs"):
            snapped = uv.straighten_uvs(
                objects,
                u=menu.chk018.isChecked(),
                v=menu.chk019.isChecked(),
                angle=menu.s001.value(),
            )
            shells = uv.straighten_uv_shells(objects) if menu.chk020.isChecked() else 0
        if not snapped and not shells:
            self.sb.message_box(
                "<b>Nothing straightened.</b><br>Select UV edges within the angle "
                "threshold (in Blender: in Edit Mode)."
            )

    # ------------------------------------------------------------------ tb006  Distribute
    def tb006_init(self, widget):
        """Initialize Distribute"""
        widget.option_box.menu.setTitle("Distribute")
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Distribute U",
            setObjectName="chk023",
            setChecked=True,
            setToolTip="Distribute along U, leaving the panel's tile border "
            "padding between adjacent shells.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Distribute V",
            setObjectName="chk024",
            setToolTip="Distribute along V, leaving the panel's tile border "
            "padding between adjacent shells.",
        )

    def tb006(self, widget):
        """Distribute: lay the selected UV shells out in a row along U or V.

        The gap left between adjacent shells is the panel's tile spacing
        (:meth:`_border_margin`) — the same clearance the move pad's shell snap
        parks against and Gather insets by; without it the shells butt edge to
        edge and the row bleeds across its own seams at render time.
        """
        axis = "u" if widget.option_box.menu.chk023.isChecked() else "v"
        objects = self._selection(
            "<b>Nothing selected.</b><br>Select the UV shells to distribute."
        )
        if objects and not self.tk.UvUtils.distribute_uv_shells(
            objects, axis=axis, spacing=self._border_margin()
        ):
            self.sb.message_box(
                "<b>Nothing distributed.</b><br>Needs two or more UV shells (in "
                "Blender's Edit Mode: shells the selection touches)."
            )

    # ------------------------------------------------------------------ tb008  Mirror
    def tb008_init(self, widget):
        """Initialize Mirror UVs.

        Mirrors UVs across U or V. By default this uses the footprint-preserving
        reassignment mode (preserve_position=True), which keeps the UV point set
        unchanged and only reassigns which UV gets which point.
        """
        widget.option_box.menu.setTitle("Mirror UVs")
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Mirror U",
            setObjectName="chk031",
            setChecked=True,
            setToolTip="Mirror across U. Default mode preserves the UV footprint.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Mirror V",
            setObjectName="chk032",
            setToolTip="Mirror across V. Default mode preserves the UV footprint.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Per Shell",
            setObjectName="chk033",
            setChecked=True,
            setToolTip="If enabled, mirrors each UV shell independently.",
        )
        # Preserve Footprint vs Geometric Mirror are two distinct algorithms, not a
        # modifier — a combobox names both states.
        mode = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_mirror_mode",
            setToolTip="Preserve Footprint: keeps the exact UV point set via "
            "one-to-one reassignment.\nGeometric Mirror: reflects the UVs around "
            "the pivot.",
        )
        mode.addItems(["Preserve Footprint", "Geometric Mirror"])
        # The prior default (the checkbox this combo replaced was on).
        mode.setCurrentText("Preserve Footprint")

    def tb008(self, widget):
        """Mirror UVs (footprint-preserving by default)."""
        menu = widget.option_box.menu
        objects = self._selection()
        if not objects:
            return
        footprint = menu.cmb_mirror_mode.currentText() == "Preserve Footprint"
        self.tk.UvUtils.mirror_uvs(
            objects,
            axis="u" if menu.chk031.isChecked() else "v",
            per_shell=menu.chk033.isChecked(),
            preserve_position=footprint,
        )

    # ------------------------------------------------------------------ Align
    def _align(self, axis, mode):
        """Shared body for the Align buttons: the host's ``UvUtils.align_uvs``,
        with a message when the selection yields nothing to align."""
        objects = self._selection()
        if objects and not self.tk.UvUtils.align_uvs(objects, axis=axis, mode=mode):
            self.sb.message_box(
                "<b>Nothing aligned.</b><br>Select UVs to align (in Blender: in "
                "Edit Mode, or a mesh in Object Mode)."
            )

    def align_u_min(self):
        """Align the selected UVs to their minimum U (left)."""
        self._align("u", "min")

    def align_u_avg(self):
        """Align the selected UVs to their average U (center)."""
        self._align("u", "avg")

    def align_u_max(self):
        """Align the selected UVs to their maximum U (right)."""
        self._align("u", "max")

    def align_v_min(self):
        """Align the selected UVs to their minimum V (bottom)."""
        self._align("v", "min")

    def align_v_avg(self):
        """Align the selected UVs to their average V (center)."""
        self._align("v", "avg")

    def align_v_max(self):
        """Align the selected UVs to their maximum V (top)."""
        self._align("v", "max")

    def linear_align(self):
        """Linearly align the selected UVs between their two end points."""
        self._align("u", "linear")  # the axis is ignored for linear

    # ------------------------------------------------------------------ Orient
    def orient_shells(self):
        """Orient each shell to run parallel with its nearest U/V axis."""
        objects = self._selection(
            "<b>Nothing selected.</b><br>Select mesh(es) or UVs to orient."
        )
        if objects and not self.tk.UvUtils.orient_shells(objects):
            self.sb.message_box(
                "<b>Nothing oriented.</b><br>Select UV shells (in Blender: in Edit "
                "Mode)."
            )

    def orient_edges(self):
        """Orient the shell so its selected edge runs along U or V."""
        objects = self._selection()
        if objects and not self.tk.UvUtils.orient_shells(objects, to_edge=True):
            self.sb.message_box(
                "<b>No edge selected.</b><br>Select a UV/mesh edge to orient the "
                "shell to (in Blender: in Edit Mode)."
            )

    def gather_shells(self):
        """Gather the selected shells together toward the 0-1 UV space."""
        objects = self._selection()
        if objects and not self.tk.UvUtils.gather_uv_shells(objects):
            self.sb.message_box(
                "<b>Nothing gathered.</b><br>Select shells sitting outside the 0-1 "
                "tile."
            )

    def randomize_shells(self):
        """Randomly offset the selected shells; each click advances the seed, so
        repeated clicks re-shuffle rather than re-apply one offset."""
        objects = self._selection()
        if not objects:
            return
        seed = self._randomize_seed
        self._randomize_seed += 1
        if not self.tk.UvUtils.randomize_uv_shells(objects, seed=seed):
            self.sb.message_box(
                "<b>Nothing randomized.</b><br>Select UV shells (in Blender: in "
                "Edit Mode)."
            )

    # ------------------------------------------------------------------ header
    def open_uv_editor(self):
        """Open the host's UV Editor."""
        if self.tk.UiUtils.open_editor("UV Editor") is None:
            self.sb.message_box("Could not open the UV Editor.")
