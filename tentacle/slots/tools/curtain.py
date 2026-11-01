# !/usr/bin/python
# coding=utf-8
"""Curtain: drape a pleated, gravity-sagged cloth curtain from a rail, with a
live preview and an in-panel preset combo.

One Slots class for both hosts over the host toolkit's ``Curtain``
(``self.tk``): the rail a selection describes, the drape, and the auto-rail
curve the panel shows while nothing usable is selected, each held as an object
name. The preview is the host's ``Preview``. The generated rail is pythontk's
``Polyline``, and the drape math is one vendored engine, so identical settings
drape identically in both hosts.
"""

import pythontk as ptk

from tentacle import Slots


class CurtainSlots(Slots):
    #: The rail Position fields and the axis each one sets. They share a tight
    #: row with Get, so they carry no reset buttons and no "X/Y/Z" prefixes: the
    #: value text is tinted by axis instead.
    POSITION_FIELDS = (("s025", "x"), ("s026", "y"), ("s027", "z"))

    # Maya's Preview rolls back only what perform_operation creates. The
    # auto-rail exists before the preview starts, so the in-place reshape
    # perform_operation gives it survives each rollback and only the curtain is
    # rebuilt. Preserving the selection would duplicate the rail and roll every
    # reshape back. Blender's Preview snapshots its selection regardless.
    PRESERVE_GEOMETRY = False

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.curtain
        self.last_curtain = None  # the current curtain's name
        self.presets = None  # the in-panel preset manager (cmb000_init)
        # Auto-rail: with nothing usable selected, the cloth hangs on the Rail
        # fields (``_generated``) and the panel owns a curve drawn through them
        # (``_driver``, its name). The curve shows where the cloth hangs and is
        # the selection the preview reads; it never outlives the preview.
        self._driver = None
        self._generated = False

        # Before the Preview connects, so the auto-rail is selected by the time
        # the preview reads the selection.
        self.ui.chk000.toggled.connect(self._ensure_rail)

        # Per-field reset buttons (uitk option-box): click resets a field to its
        # default; Alt/Ctrl+click bypasses it to default (greyed, restorable).
        # Must precede connect_multi/Preview — wrapping reparents the widgets and
        # invalidates any already-deferred wrapper (see add_reset_buttons docstring).
        self.sb.add_reset_buttons(
            self.ui, skip=tuple(name for name, _axis in self.POSITION_FIELDS)
        )

        self.preview = self.tk.Preview(
            self,
            self.ui.chk000,
            self.ui.b000,
            finalize_func=self._finalize,
            message_func=self.sb.message_box,
            undo_message="Curtain",
            # Select Result is the Preview's: it (de)selects the curtain after
            # every build and on commit, after _finalize drops the auto-rail.
            select_result_checkbox=self.ui.chk005,
            result_provider=lambda: self.last_curtain,
        )
        # After the Preview connects, so a cancelled preview's auto-rail goes
        # once the Preview has rolled back: Blender's Preview restores every
        # object it captured on that rollback, the rail included.
        self.ui.chk000.toggled.connect(self._drop_rail_on_cancel)

        self.sb.connect_multi(
            self.ui, "s000-27", "valueChanged", self._on_param_changed
        )
        self.sb.connect_multi(
            self.ui, "chk001,chk004", "toggled", self._on_param_changed
        )

        self._color_code_position_fields()
        # The footer reports the curtain's triangle count once one is built.
        self.ui.footer.setDefaultStatusText("Toggle Preview to drape a curtain.")

    # --------------------------------------------------------------- header

    def header_init(self, widget):
        """Configure header help text (the preset combo lives in the panel)."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Curtain",
                body="Drape a pleated cloth curtain from a <b>rail</b>: a selected "
                "curve, a mesh edge loop (in Blender: edges selected in Edit Mode) "
                "or two or more objects in a row, or a generated straight rail "
                "when nothing usable is selected.",
                steps=[
                    "Toggle <b>Preview</b> (a rail is auto-created from "
                    "Width/Curvature if you haven't selected your own).",
                    "Set <b>Hanging Points</b> (the pleats/pins) and <b>Fullness</b>.",
                    "Dial <b>Gravity</b> — how far the fabric falls between "
                    "hanging points.",
                    "Press <b>Create</b> to commit.",
                ],
                sections=[
                    (
                        "Model",
                        [
                            "Each <b>Hanging Point</b> is a pleat where the fabric "
                            "pins to the rail — one clean gather at the rail — and "
                            "bellies into a full fold between consecutive points, so "
                            "the count maps roughly 1:1 to the folds you see. The "
                            "spans sag down a real <b>catenary</b> (cosh).",
                            "<b>Gravity</b> sets the sag depth (wider gaps fall "
                            "further); <b>Catenary Tension</b> shapes that curve.",
                            "<b>Taper</b> gathers the pleats at the top and flares "
                            "them toward the hem.",
                            "<b>Mid Folds</b> fork V-folds down from some hang "
                            "points (seed varies which), breaking the plain in/out "
                            "belly; <b>Creases</b> add diagonal V break-lines; "
                            "<b>Sway</b> randomly leans a subset of the folds left "
                            "or right along the rail (not just in/out); the "
                            "<b>Ends</b> group bends each end; <b>Round</b> softens "
                            "the hooks.",
                        ],
                    ),
                ],
                notes=[
                    "The <b>preset</b> combo loads built-in looks "
                    "(Stage Swag, Shower Curtain) and saves your own.",
                    "<b>Select Result</b> selects the finished curtain on "
                    "<b>Create</b> so you can see the result.",
                    "Maya and Blender share the drape engine: identical settings "
                    "drape identically.",
                ],
            )
        )
        # Align every spinbox's value column once the panel's fonts and styles
        # are settled (deferred a tick so QFontMetrics sees the themed font).
        self.sb.QtCore.QTimer.singleShot(0, self._align_spinbox_prefixes)

    def cmb000_init(self, widget):
        """Wire the in-panel preset selector: the host's shipped presets under
        its user tier. A preset is a snapshot of the panel's fields; loading one
        refreshes the preview in one shot."""
        self.presets = self.sb.PresetManager(
            parent=self.ui,
            state=self.ui.state,
            preset_dir=self.tk.Curtain.PRESET_DIR,
            builtin_dir=self.tk.Curtain.BUILTIN_PRESET_DIR,
        )
        self.presets.wire_combo(widget, on_loaded=self._on_param_changed)

    # ------------------------------------------------- spinbox value alignment

    def _color_code_position_fields(self) -> None:
        """Tint the rail Position values red/green/blue for X/Y/Z.

        The fields carry no "X "/"Y "/"Z " prefixes; the axis-coded value text
        carries that meaning, with the tooltips naming the axis as a textual
        fallback. Colors come from ``pythontk.Palette.axes()``, applied through
        the uitk spinbox's ``set_text_color``.
        """
        axes = ptk.Palette.axes()
        for name, axis in self.POSITION_FIELDS:
            setter = getattr(getattr(self.ui, name, None), "set_text_color", None)
            if callable(setter):
                setter(axes[axis].hex)

    def _align_spinbox_prefixes(self) -> None:
        """Pad each spinbox prefix so the values line up within each group.

        The custom spin widgets add a single ``\\t`` after the prefix, which
        only lands on one tab stop — long prefixes ("Catenary Tension:") then
        overflow past short ones ("Seed:"), so the value columns don't align.
        Here we measure the widest prefix per section (with the widget's own
        font metrics) and right-pad the rest with spaces to match (font-correct
        to within a space width), bypassing the ``\\t``. Aligning per group —
        keyed on each spinbox's titled group — keeps short-labelled sections
        tight instead of indenting them to clear a long label elsewhere.
        """
        QtWidgets, QtGui = self.sb.QtWidgets, self.sb.QtGui
        group_type = self.sb.CollapsableGroup

        def group_of(widget):
            # The nearest titled group, not the immediate parent: the reset
            # buttons' option-box wrapping reparents each spinbox into its own
            # container, which would defeat the per-section alignment.
            parent = widget.parentWidget()
            while parent is not None:
                if isinstance(parent, group_type):
                    return parent
                parent = parent.parentWidget()
            return widget.parentWidget()

        groups = {}
        for spin in self.ui.findChildren(QtWidgets.QAbstractSpinBox):
            # The AUTHORED label, not the rendered one: uitk's PrefixColumnMixin
            # collapses (and past a point elides) the prefix to keep the value
            # visible in a narrow field, so prefix() can be a truncated form.
            # Falls back for a plain QSpinBox and for a re-run over prefixes
            # this method already padded (which the mixin leaves verbatim).
            base = getattr(spin, "prefix_label", lambda: "")() or spin.prefix().rstrip()
            if base:
                groups.setdefault(group_of(spin), []).append(
                    (spin, base, QtGui.QFontMetrics(spin.font()))
                )

        for entries in groups.values():
            widest = max(
                metrics.horizontalAdvance(base) for _s, base, metrics in entries
            )
            for spin, base, metrics in entries:
                space = metrics.horizontalAdvance(" ") or 1
                gap = widest + 2 * space - metrics.horizontalAdvance(base)
                text = base + " " * max(1, round(gap / space))
                # Bypass the custom setPrefix: an exact, hand-composed prefix is
                # the one form PrefixColumnMixin leaves alone, and routing it
                # through the override would strip this padding back off.
                if isinstance(spin, QtWidgets.QDoubleSpinBox):
                    QtWidgets.QDoubleSpinBox.setPrefix(spin, text)
                else:
                    QtWidgets.QSpinBox.setPrefix(spin, text)

    # ----------------------------------------------------------- rail / driver

    def _on_param_changed(self, *_):
        """A field changed: re-drape. With the preview off this does nothing,
        so a field nudge after a commit never builds a stray rail."""
        self.preview.refresh()

    def _field_rail(self):
        """The generated rail ``(points, closed)`` from the Width / Curvature /
        Closed / Position fields."""
        return ptk.Polyline.make(
            width=self.ui.s001.value(),
            curvature=self.ui.s002.value(),
            closed=self.ui.chk001.isChecked(),
            center=tuple(
                getattr(self.ui, name).value() for name, _a in self.POSITION_FIELDS
            ),
        )

    def _rail_cvs(self, points):
        """*points* resampled to one CV per hanging point: the auto-rail reads
        as the line of pins the cloth gathers on."""
        return ptk.Polyline.resample(points, max(2, int(self.ui.s003.value())))

    def _not_ours(self, objects):
        """*objects* without the panel's own auto-rail and curtain. Matched by
        name: Maya's selection reads node names, Blender's reads objects."""
        ours = {self._driver, self.last_curtain} - {None}
        return [o for o in objects if getattr(o, "name", o) not in ours]

    def _ensure_rail(self, state: bool) -> None:
        """Preview on: hang on the user's own rail, or build the auto-rail.

        With a usable rail selected the cloth hangs on it (Width/Curvature are
        ignored). Otherwise the panel enters *generated* mode and builds and
        selects the auto-rail: it satisfies the preview's selection gate and
        shows where the cloth hangs. Preview off is :meth:`_drop_rail_on_cancel`'s.
        """
        if not state:
            return
        selection = self._not_ours(self.tk.CoreUtils.selected_objects())
        if self.tk.Curtain.rail_from_selection(selection) is not None:
            self._drop_rail()  # one left over from an earlier session
            self._generated = False
            return
        self._generated = True
        points, closed = self._field_rail()
        self._driver = self.tk.Curtain.rail_curve(
            self._rail_cvs(points), closed, curve=self._driver, select=True
        )

    def _drop_rail_on_cancel(self, state: bool) -> None:
        """Preview off (cancelled, failed or committed): drop the auto-rail.

        Connected after the Preview, so it runs once the Preview has rolled
        back. The next preview reads the rail mode from the live selection again.
        """
        if not state:
            self._generated = False
            self._drop_rail()

    def _drop_rail(self) -> None:
        """Delete the auto-rail curve, if the panel holds one."""
        self.tk.Curtain.delete_rail_curve(self._driver)
        self._driver = None

    def _resolve_rail(self, objects):
        """The rail ``(points, closed)`` for this drape: the Rail fields in
        generated mode (read live, so they apply on every refresh), else the
        rail *objects* describe, falling back to the fields."""
        if not self._generated:
            rail = self.tk.Curtain.rail_from_selection(self._not_ours(objects))
            if rail is not None:
                points, closed = rail
                return points, closed or self.ui.chk001.isChecked()
        return self._field_rail()

    # --------------------------------------------------------------- buttons

    def b001_init(self, widget):
        """Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
        current values as the defaults, Ctrl+Shift+Click forgets them)."""
        self._reset_gesture = self.sb.ResetGesture(widget)

    def b002(self):
        """Get: set Position to the bounding-box center of the selection.

        Centers the generated rail on whatever is selected (its combined world
        bounding box), ignoring the panel's own auto-rail and curtain, so Get
        centers on the *external* target. The three fields are set with their
        signals blocked, then one re-drape follows.
        """
        selection = self._not_ours(self.tk.CoreUtils.selected_objects())
        if not selection:
            self.sb.message_box("Select object(s) to center the rail on.")
            return
        center = self.tk.XformUtils.get_bounding_box(selection, "center")
        for (name, _axis), value in zip(self.POSITION_FIELDS, center):
            widget = getattr(self.ui, name)
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self._on_param_changed()

    # ------------------------------------------------------------- operation

    def perform_operation(self, objects, contract=None):
        """Build the curtain from the resolved rail (the Preview's entry point;
        Maya's Preview passes its cleanup *contract*, Blender's none).

        In generated mode the auto-rail is reshaped in place first, so it tracks
        the Rail fields live. That happens here, after the host's rollback, in
        both hosts: Blender's Preview restores the rail it captured on every
        rollback, so a reshape made before the refresh would be undone.
        """
        points, closed = self._resolve_rail(objects)
        if self._generated and self._driver:
            self._driver = self.tk.Curtain.rail_curve(
                self._rail_cvs(points), closed, curve=self._driver
            )
        self.last_curtain = self.tk.Curtain.create(
            points,
            height=self.ui.s000.value(),
            hanging_points=int(self.ui.s003.value()),
            hang_jitter=self.ui.s023.value(),
            hang_seed=int(self.ui.s024.value()),
            gravity=self.ui.s004.value(),
            tension=self.ui.s005.value(),
            round_points=self.ui.s013.value(),
            round_gather=self.ui.s022.value(),
            fullness=self.ui.s006.value(),
            taper=self.ui.s007.value(),
            mid_folds=self.ui.s019.value(),
            mid_fold_seed=int(self.ui.s010.value()),
            creases=self.ui.s014.value(),
            crease_seed=int(self.ui.s015.value()),
            sway=self.ui.s020.value(),
            sway_seed=int(self.ui.s021.value()),
            end_bend_left=self.ui.s016.value(),
            end_bend_right=self.ui.s017.value(),
            end_bend_falloff=self.ui.s018.value(),
            irregularity=self.ui.s008.value(),
            density=self.ui.s009.value(),
            reduce=self.ui.s012.value(),
            thickness=self.ui.s011.value(),
            invert=self.ui.chk004.isChecked(),
            closed=closed,
        )
        self._update_footer()

    def _update_footer(self):
        """The curtain's triangle count in the footer, live as the preview
        re-drapes; with no curtain the footer falls back to its hint."""
        try:
            footer = self.ui.footer
        except AttributeError:  # a stub ui without one
            return
        tris = self.tk.Curtain.triangle_count(self.last_curtain)
        footer.setStatusText("" if tris is None else f"{tris:,} tris")

    def _finalize(self):
        """On commit, drop the auto-rail: a preview aid, not wanted in the
        committed scene. It runs inside the commit's undo step in both hosts,
        and before the Preview applies Select Result, so the curtain stays
        selected."""
        self._generated = False
        self._drop_rail()
