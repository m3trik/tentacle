# !/usr/bin/python
# coding=utf-8
"""Mirror: mirror the selected meshes across an axis, with a live preview.

One Slots class for both hosts. The engine is the host toolkit's ``EditUtils``
(``mirror`` / ``mirror_instance`` / ``cut_along_axis``) and the preview its
``Preview``, both reached through ``self.tk``.
"""

from tentacle import Slots


class MirrorSlots(Slots):
    # Maya's polySeparate inside EditUtils.mirror deletes the original
    # transform: MUTATES_SELECTION=True tells Maya's Preview to duplicate+hide
    # the selection before perform_operation so rollback can restore it.
    # Blender's Preview snapshots every operated object regardless.
    MUTATES_SELECTION = True

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.mirror

        # A merge mode the host's mirror can't do stays listed but disabled, so
        # the combo keeps one item order (it saves an index). Before
        # add_reset_buttons/connect_multi wrap the widgets.
        self._disable_unsupported_merge_modes()

        # Per-field reset buttons (uitk option-box) on the Pivot / Merge Mode
        # combos — Mirror has no numeric params, and the Axis checkboxes are a
        # mutually-exclusive group (a per-box reset would be confusing). Click
        # resets the combo to its default; Alt/Ctrl+click bypasses it.
        # Must precede connect_multi/Preview — wrapping reparents the widgets and
        # invalidates any already-deferred wrapper (see add_reset_buttons docstring).
        self.sb.add_reset_buttons(self.ui, "cmb000-1")

        self.preview = self.tk.Preview(
            self,
            self.ui.chk000,
            self.ui.b000,
            message_func=self.sb.message_box,
            undo_message="Mirror",
        )

        # The '-' (negative axis) toggle only changes the result for the
        # bounding-box pivots — Center symmetrizes and the sign picks which half
        # survives; Border picks the min vs max face. For Manip/Object/World the
        # mirror reflects across a fixed plane, so the sign is a no-op there.
        # Connect BEFORE the preview-refresh wiring so the enabled/checked state
        # is settled before perform_operation re-reads the axis on a pivot change.
        self.ui.cmb000.currentIndexChanged.connect(self._sync_axis_sign_enabled)

        # Instance output shares the source's shape, so the geometry-level
        # options (merge / delete half / uninstance) have nothing to act on.
        # Same connect-before-preview ordering rationale as the axis sign.
        self.sb.enable_when(self.ui, "cmb001,chk006", "chk007", invert=True)

        # Connect combos and checkboxes to preview refresh function
        self.sb.connect_multi(
            self.ui, "cmb000-1", "currentIndexChanged", self.preview.refresh
        )
        self.sb.connect_multi(self.ui, "chk001-7", "clicked", self.preview.refresh)

        # Refresh the preview when the viewport pivot changes (selection, tool
        # or manipulator drag release), where the host has a watcher for it
        # (Maya's scriptJob-driven PivotWatcher; Blender has none yet: a Manip
        # pivot re-samples on the next widget-driven refresh). EditUtils.mirror
        # deletes and re-selects the transform, which fires SelectionChanged on
        # the next idle — the watcher's signature dedup absorbs that self-fire.
        watcher = getattr(self.tk, "PivotWatcher", None)
        if watcher is not None:
            self._pivot_watcher = watcher(
                self.preview.refresh,
                gate=lambda: self.preview.is_enabled,
                owner=self,
            )
            self._pivot_watcher.start()
            self._pivot_watcher.attach_widget(self.ui)

        # Settle the '-' toggle's enabled state for the initial (default /
        # restored) pivot before the user interacts.
        self._sync_axis_sign_enabled()

    def _disable_unsupported_merge_modes(self) -> None:
        """Disable each Merge Mode item (index - 1 is its ``mergeMode``) the
        host's mirror doesn't support (``EditUtils.MIRROR_MERGE_MODES``):
        Blender's has no Merge: Extrude yet."""
        supported = self.tk.EditUtils.MIRROR_MERGE_MODES
        model = self.ui.cmb001.model()
        for index in range(self.ui.cmb001.count()):
            if index - 1 in supported:
                continue
            item = model.item(index) if model is not None else None
            if item is not None:
                item.setFlags(item.flags() & ~self.sb.QtCore.Qt.ItemIsEnabled)
                item.setToolTip("Not supported by this host's mirror yet.")

    def header_init(self, widget):
        """Configure header help text."""
        # Gesture-scoped window: pin button + auto-hide on key_show release.
        widget.config_buttons("menu", "collapse", "pin")
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Mirror",
                body="Mirror selected meshes across an axis, optionally merging "
                "seam vertices and discarding the original half.",
                steps=[
                    "Select one or more mesh objects.",
                    "Check an <b>Axis</b> (X / Y / Z). The <b>—</b> toggle makes "
                    "it negative; it only applies to the Bounding Box pivots and "
                    "is disabled otherwise.",
                    "Pick a <b>Pivot</b> — Manip / Object / World, or a Bounding "
                    "Box pivot (see below).",
                    "Pick a <b>Merge Mode</b>.",
                    "Toggle <b>Preview</b> to iterate, or press <b>Create</b> "
                    "to commit.",
                ],
                sections=[
                    (
                        "Mirror plane",
                        [
                            "<b>Manip</b> / <b>Object</b> — the plane passes through "
                            "that pivot and follows the object's <b>own</b> axes, so a "
                            "rotated object mirrors about its own X/Y/Z (the same frame "
                            "rule Cut On Axis uses). Manip is Maya's manipulator pivot; "
                            "in Blender, the Transform Pivot Point setting.",
                            "<b>World</b> and both <b>Bounding Box</b> pivots use world "
                            "axes regardless of how the object is rotated.",
                        ],
                    ),
                    (
                        "Bounding Box pivots",
                        [
                            "<b>Center</b> — keep one half and mirror it across the "
                            "center to symmetrize. The <b>—</b> toggle flips which "
                            "half is kept.",
                            "<b>Border</b> — mirror across the max face of the axis; "
                            "the <b>—</b> toggle flips it to the min face.",
                        ],
                    ),
                    (
                        "Options",
                        [
                            "<b>Instance</b> — output a linked copy instead of new "
                            "geometry: the mirrored half shares the source's mesh, "
                            "so editing either half updates both. Merge Mode, "
                            "Delete Original and Un-Instance don't apply, and the "
                            "Bounding Box (center) pivot can't be used (it cuts "
                            "geometry). Best for modeling: the linked half carries "
                            "a negative scale, which game engines handle unevenly — "
                            "bake it (Un-Instance, then freeze scale) before export, "
                            "or mirror with Instance off.",
                            "Instance links are broken automatically — mirroring a "
                            "shared mesh would rewrite every other instance.",
                            "<b>Delete Original Half</b> — discard the source side "
                            "after the mirror copy is created (Merge OFF only).",
                        ],
                    ),
                ],
            )
        )

    def prepare_operation(self, objects):
        """Break instance links once, before the preview contract exists.

        Mirroring geometry can never leave a shape shared (Maya's separate
        mode's polySeparate consumes the transform and would take every sibling
        instance with it), but forking inside ``perform_operation`` is
        unreversible: rollback deletes the forked shape as a created node and
        leaves the transform empty. Doing it here — once, at enable, outside
        any contract — keeps every later refresh/rollback cycle clean.

        Instance OUTPUT is exempt: it only ever adds a new instance of the
        source, so the source's existing links are none of its business.
        """
        if not self.ui.chk007.isChecked():
            self.tk.NodeUtils.uninstance(objects)

    def perform_operation(self, objects, contract=None):
        """Mirror *objects* (Maya's Preview passes its cleanup *contract*)."""
        axis = self.sb.get_axis_from_checkboxes(
            "chk001-4", self.ui
        )  # e.g. "x" or "-x"; "-" only honored for the bounding-box pivots
        # get_axis_from_checkboxes returns "" / "-" when no X/Y/Z is selected;
        # guard here so both paths give the same clear error instead of a raw
        # KeyError downstream (cut_along_axis doesn't validate the axis).
        if axis.lstrip("-") not in ("x", "y", "z"):
            raise ValueError("Select an axis (X / Y / Z) to mirror across.")

        pivot_index = self.ui.cmb000.currentIndex()
        edit = self.tk.EditUtils

        # Instance output: the mirrored half is a linked copy of the source's
        # shape, reflected purely in its transform. Symmetrize (bounding-box
        # center) cuts and rebuilds geometry, so the two are incompatible —
        # say so instead of silently falling through to the geometry path.
        if self.ui.chk007.isChecked():
            if pivot_index == 3:
                raise ValueError(
                    "Instance output can't symmetrize — the Bounding Box (center) "
                    "pivot cuts geometry. Pick another pivot, or uncheck Instance."
                )
            edit.mirror_instance(
                objects, axis=axis, pivot=self._resolve_pivot(pivot_index, axis)
            )
            return

        # Bounding Box (center): reflecting the whole object across its own
        # center just overlaps it, so this pivot SYMMETRIZES instead — cut at
        # the center, keep one half, and mirror it across the cut plane. The
        # axis sign picks which half survives; cut_along_axis's convention is
        # inverted vs. this panel ("x" there deletes the +X half), so invert=True
        # makes the UI's "+X" keep the +X half.
        if pivot_index == 3:
            # Symmetrize cuts and rebuilds geometry, so a shared shape would take
            # every sibling instance with it — break the link first, always. (The
            # mirror engine does the same internally; cut_along_axis is a general
            # cutting op, so the panel owns the decision here.)
            self.tk.NodeUtils.uninstance(objects)
            edit.cut_along_axis(
                objects,
                axis=axis,
                invert=True,
                pivot="center",
                amount=1,
                delete=True,
                mirror=True,
                # axis_frame left unset: "center" is a bounding-box pivot, so
                # the cut and its mirror both resolve to world axes.
            )
            return

        edit.mirror(
            objects,
            axis=axis,
            pivot=self._resolve_pivot(pivot_index, axis),
            # The combo's index - 1 is the mergeMode (-1: OFF).
            mergeMode=self.ui.cmb001.currentIndex() - 1,
            delete_original=self.ui.chk006.isChecked(),
        )

    @staticmethod
    def _axis_sign_relevant(pivot_index: int) -> bool:
        """Whether the '-' (negative axis) toggle changes the mirror result.

        Only the bounding-box pivots use the sign: Center (index 3) picks which
        half survives the symmetrize; Border (index 4) picks the min vs max face.
        Manip / Object / World reflect across a fixed plane, so the sign is a
        no-op there and the toggle is disabled.
        """
        return pivot_index in (3, 4)

    def _sync_axis_sign_enabled(self, *args) -> None:
        """Enable the '-' toggle only where the sign matters; uncheck it when
        disabling so a stale sign can't leak into a pivot that ignores it."""
        relevant = self._axis_sign_relevant(self.ui.cmb000.currentIndex())
        self.ui.chk001.setEnabled(relevant)
        if not relevant and self.ui.chk001.isChecked():
            self.ui.chk001.setChecked(False)

    @staticmethod
    def _resolve_pivot(pivot_index: int, axis: str) -> str:
        """The pivot the combo's index names. The bounding-box BORDER pivot
        (index 4) takes the axis sign: +axis -> the max face, -axis -> the min
        face, flipping the side the geometry doubles toward (unknown axis:
        ``xmax``)."""
        base = axis.lstrip("-")
        if base in ("x", "y", "z"):
            face = f"{base}min" if axis.startswith("-") else f"{base}max"
        else:
            face = "xmax"
        return {0: "manip", 1: "object", 2: "world", 3: "center", 4: face}.get(
            pivot_index, "manip"
        )
