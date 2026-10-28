# !/usr/bin/python
# coding=utf-8
"""Transform: one Slots class for both hosts.

Every operation is the host toolkit's ``XformUtils`` / ``Diagnostics``
(``self.tk``); each is one undo step in its host. Where a selection-relative
operation needs a distinguished object, each host keeps its own: Maya's
selection order (the last selected is Move To's target, the first selected
is what Match Scale resizes), Blender's active object.

Freeze Transforms' channel-box, delete-history, connection and rig-anchor
options are Maya's (tagged ``requires="maya"``, hidden in Blender), as are
Transform Snap's move and scale increments: Blender snaps translation to the
grid and has no scale increment. Align To lists the modes the host's
``XformUtils.ALIGN_MODES`` offers (Maya's snap/align commands; Blender's
align-to-active by axis). Snap and Constrain toggles apply live and mirror the
host's state: the host owns it, so the boxes never persist a copy.
"""

from tentacle import Slots


class TransformSlots(Slots):
    #: Transform Snap: the checkbox and increment spinbox of each kind, by the
    #: ``XformUtils.set_transform_snap`` kind they drive.
    _SNAP = {"move": ("chk021", "s021"), "scale": ("chk022", "s022"), "rotate": ("chk023", "s023")}

    #: Transform Constraints: checkbox -> ``XformUtils.set_transform_constraint`` kind.
    _CONSTRAINTS = {"chk024": "edge", "chk025": "surface", "chk026": "live"}

    #: Freeze Transforms' combo indexes -> the library's strategy names (order is saved).
    _CONNECTION_STRATEGIES = ("preserve", "disconnect", "delete")
    _INSTANCE_STRATEGIES = ("skip", "preserve", "uninstance")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.transform
        self.submenu = self.sb.loaded_ui.transform_submenu

    def _maya_only(self, widget):
        """Tag an option only Maya serves; uitk hides it in Blender."""
        widget.setProperty("requires", "maya")
        self.sb.apply_visibility_policy(widget)
        return widget

    def header_init(self, widget):
        """Header: Fix Non-Orthogonal Axes and the Snap panel."""
        # Every entry is a one-shot action — dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            "QPushButton",
            setText="Fix Non-Orthogonal Axes",
            setObjectName="fix_non_ortho_axes",
            setToolTip="Bake out non-orthogonal (sheared) axes on the selected objects "
            "(shear breaks FBX export).",
        )
        widget.menu.add(
            "QPushButton",
            setText="Snap",
            setObjectName="b_snap_ts",
            setToolTip="Open the Snap panel: snap vertices to a surface, the closest "
            "vertex, or the grid.",
        )

    def fix_non_ortho_axes(self):
        """Fix Non-Orthogonal Axes: bake out shear on the selected objects."""
        selection = self.require_selection(
            "Fix Non-Orthogonal Axes requires a selection."
        )
        if selection is None:
            return
        fixed = self.tk.Diagnostics.fix_non_orthogonal_axes(selection)
        if fixed:
            self.sb.message_box(
                f"Fixed non-orthogonal axes on <hl>{len(fixed)}</hl> object(s)."
            )
        else:
            self.sb.message_box("No non-orthogonal (sheared) axes found.")

    def b_snap_ts(self):
        """Snap: open the shared Snap panel."""
        self.sb.handlers.marking_menu.show("snap")

    # ------------------------------------------------------------------ cmb002  Align To
    def cmb002_init(self, widget):
        """Align To: the modes the host offers."""
        widget.add(list(self.tk.XformUtils.ALIGN_MODES), header="Align To")

    def cmb002(self, index, widget):
        """Align To: run the chosen mode on the selection."""
        try:
            self.tk.XformUtils.align_to(widget.items[index])
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ tb000  Drop To Grid
    def tb000_init(self, widget):
        """Initialize Drop To Grid."""
        menu = widget.option_box.menu
        menu.add(
            "QComboBox",
            addItems=["Min", "Mid", "Max"],
            setObjectName="cmb004",
            setToolTip="Which point of the bounding box lands on the ground plane.",
        )
        menu.add(
            "QCheckBox",
            setText="Move to Origin",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Move to the world origin (0, 0, 0) first.",
        )
        menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Center the pivot on the bounding box (Blender: the origin).",
        )
        menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Freeze the transform after dropping (Blender: the location).",
        )

    def tb000(self, widget):
        """Drop To Grid"""
        menu = widget.option_box.menu
        dropped = self.tk.XformUtils.drop_to_grid(
            None,
            align=menu.cmb004.currentText(),
            origin=menu.chk014.isChecked(),
            center_pivot=menu.chk016.isChecked(),
            freeze_transforms=menu.chk017.isChecked(),
        )
        if dropped == []:
            self.sb.message_box("Drop To Grid requires a selection.")

    # ------------------------------------------------------------------ tb001  Scale Connected Edges
    def tb001_init(self, widget):
        """Initialize Scale Connected Edges (the scale factor option)."""
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="s001",
            setPrefix="Scale Factor:",
            setValue=1.1,
            set_limits=[-999, 999, 0.1],
            setToolTip="The factor each connected set of edges scales by, about its "
            "own center.",
        )

    def tb001(self, widget):
        """Scale Connected Edges: each connected set of selected edges scales about
        its own center."""
        scaled = self.tk.XformUtils.scale_connected_edges(
            None, scale_factor=widget.option_box.menu.s001.value()
        )
        if not scaled:
            self.sb.message_box(
                "<strong>No connected edges scaled.</strong><br>Select edges on a "
                "mesh (Blender: in Edit Mode) first."
            )

    # ------------------------------------------------------------------ tb002  Freeze Transforms
    def tb002_init(self, widget):
        """Initialize Freeze Transforms."""
        menu = widget.option_box.menu
        menu.setTitle("Freeze Transforms")
        menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk032",
            setChecked=True,
            setToolTip="The translation will be changed to 0, 0, 0.",
        )
        menu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk033",
            setToolTip="The rotation will be changed to 0, 0, 0.",
        )
        menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk034",
            setChecked=True,
            setToolTip="The scale factor will be changed to 1, 1, 1.",
        )
        self._maya_only(
            menu.add(
                "QCheckBox",
                setText="From Channel Box",
                setObjectName="chk040",
                setChecked=False,
                setToolTip="Use the selected attributes in the channel box to determine "
                "what to freeze.",
            )
        )
        # Store Transforms is deliberately NOT an option: the bake history the
        # freeze stamps is what Un-Freeze Transforms reads, so turning it off only
        # ever breaks the un-freeze. It is always stamped (the libraries' default).
        menu.add(
            "QComboBox",
            setObjectName="cmb_center_pivot",
            addItems=["Center Pivot: None", "Center Pivot: Mesh", "Center Pivot: All"],
            setCurrentIndex=0,
            setToolTip="Move the pivot (Blender: the origin) to the center of the bounding "
            "box after freezing.\n• None: leave it\n• Mesh: mesh objects only\n"
            "• All: all objects",
        )
        menu.add(
            "QCheckBox",
            setText="Freeze Children",
            setObjectName="chk039",
            setToolTip="Also freeze every descendant of the selected objects.",
        )
        self._maya_only(
            menu.add(
                "QCheckBox",
                setText="Restore Rig Anchors",
                setObjectName="chk_restore_rig_anchors",
                setChecked=True,
                setToolTip=(
                    "After freeze, re-anchor each GRP > LOC > GEO rig to its world\n"
                    "pivot: lift the world position from vertex coordinates back onto\n"
                    "the GRP's translate, shift mesh vertices and rotate/scale pivots\n"
                    "to compensate. Restores the canonical create_locator_at_object\n"
                    "hierarchy. Skips rigs whose LOC has incoming animation curves\n"
                    "(those weren't disturbed by the freeze)."
                ),
            )
        )
        self._maya_only(
            menu.add(
                "QComboBox",
                setObjectName="cmb_connection_strategy",
                addItems=[
                    "Preserve Connections (Warn and Skip)",
                    "Disconnect Incoming Connections",
                    "Delete Connection Nodes",
                ],
                setCurrentIndex=0,
                setToolTip=(
                    "Select the fallback when translate/rotate/scale are driven:\n"
                    "• Preserve: warn and skip freeze\n"
                    "• Disconnect: break incoming plugs\n"
                    "• Delete: break plugs and delete their driver nodes"
                ),
            )
        )
        menu.add(
            "QComboBox",
            setObjectName="cmb_instance_strategy",
            addItems=[
                "Instances: Warn and Skip",
                "Instances: Preserve (bake in place)",
                "Instances: Uninstance",
            ],
            setCurrentIndex=1,
            setToolTip=(
                "An instanced object (Maya: a shared shape; Blender: shared object\n"
                "data) cannot be frozen in place without changing every instance:\n"
                "• Warn and Skip: leave them untouched\n"
                "• Preserve: freeze one member and compensate the others —\n"
                "  instancing and appearance both survive; only the frozen\n"
                "  member ends at identity\n"
                "• Uninstance: break the instance links, then freeze each"
            ),
        )
        self._maya_only(
            menu.add(
                "QCheckBox",
                setText="Delete History",
                setObjectName="chk038",
                setChecked=True,
                setToolTip="Delete the objects' construction history.",
            )
        )

        self.sb.enable_when(menu, "chk032-34", "chk040", invert=True)

    def tb002(self, widget):
        """Freeze Transformations"""
        objects = self.require_selection("Freeze Transforms requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        # One call: Freeze, then (Restore Rig Anchors) each collapsed rig's anchor.
        self.tk.RigUtils.freeze_and_reanchor(
            objects,
            center_pivot=menu.cmb_center_pivot.currentIndex(),  # 0 None, 1 Mesh, 2 All
            translate=menu.chk032.isChecked(),
            rotate=menu.chk033.isChecked(),
            scale=menu.chk034.isChecked(),
            force=len(objects) == 1,  # unlock locked channels for a single object only
            delete_history=menu.chk038.isChecked(),
            freeze_children=menu.chk039.isChecked(),
            connection_strategy=self._CONNECTION_STRATEGIES[
                menu.cmb_connection_strategy.currentIndex()
            ],
            instance_strategy=self._INSTANCE_STRATEGIES[
                menu.cmb_instance_strategy.currentIndex()
            ],
            from_channel_box=menu.chk040.isChecked(),
            reanchor=menu.chk_restore_rig_anchors.isChecked(),
        )

    # ------------------------------------------------------------------ b002  Un-Freeze Transforms
    def b002_init(self, widget):
        """Initialize Un-Freeze Transforms."""
        menu = widget.option_box.menu
        menu.setTitle("Un-Freeze Transforms")
        menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk_unfreeze_t",
            setChecked=True,
            setToolTip="Restore the stored translation values.",
        )
        menu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk_unfreeze_r",
            setChecked=True,
            setToolTip="Restore the stored rotation values.",
        )
        menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk_unfreeze_s",
            setChecked=True,
            setToolTip="Restore the stored scale values.",
        )
        menu.add(
            "QCheckBox",
            setText="Unfreeze Children",
            setObjectName="chk_unfreeze_children",
            setToolTip="Also restore all descendants.\nMirrors the Freeze Transforms > "
            "Freeze Children option.",
        )
        menu.add(
            "QPushButton",
            setText="Restore Authored Axes",
            setObjectName="b_restore_axes",
            setToolTip=self.sb.tooltip.fmt(
                title="Restore Authored Axes",
                body="Aim the transform gizmo at the object's <b>pre-freeze</b> axes, "
                "read from its stored freeze history. Non-destructive - the object "
                "stays frozen.",
                notes=[
                    "A freeze zeroes the rotation, so a frozen object's local axes ARE "
                    "the world axes and the gizmo can no longer show the frame the "
                    "asset was modelled in.",
                    "Maya aims its manipulator pivot; Blender sets a custom transform "
                    "orientation.",
                    "With several objects selected the last one wins - one gizmo.",
                ],
            ),
        )
        # No explicit clicked.connect: a menu widget auto-binds to the slot
        # method sharing its objectName, so wiring it by hand as well would fire
        # the handler twice.

    def b_restore_axes(self):
        """Restore Authored Axes: point the gizmo at the pre-freeze frame."""
        node = self.tk.XformUtils.restore_original_axes(None)
        if node is None:
            self.sb.message_box(
                "<strong>Nothing to restore.</strong><br>No selected object carries "
                "stored freeze data (it is stamped by Freeze Transforms)."
            )
        else:
            self.sb.message_box(
                f"Gizmo aimed at <hl>{self.tk.CoreUtils.leaf_name(node)}</hl>'s "
                "authored axes."
            )

    def b002(self, widget):
        """Un-Freeze Transforms: restore the channels Freeze stamped (the object's
        world position is kept)."""
        objects = self.require_selection("Un-Freeze Transforms requires a selection.")
        if objects is None:
            return
        menu = widget.option_box.menu
        channels = [
            channel
            for channel, chk in (
                ("translate", menu.chk_unfreeze_t),
                ("rotate", menu.chk_unfreeze_r),
                ("scale", menu.chk_unfreeze_s),
            )
            if chk.isChecked()
        ]
        if not channels:
            self.sb.message_box(
                "Please enable at least one channel (Translate, Rotate, or Scale)."
            )
            return
        restored = self.tk.XformUtils.restore_transforms(
            objects,
            channels=channels,
            traverse=menu.chk_unfreeze_children.isChecked(),
        )
        if not restored:
            self.sb.message_box(
                "<strong>Nothing to restore.</strong><br>No selected object carries "
                "stored freeze data (it is stamped by Freeze Transforms)."
            )

    # ------------------------------------------------------------------ tb005 / b001  Move To, Match Scale
    def tb005_init(self, widget):
        """Initialize Move To."""
        menu = widget.option_box.menu
        menu.setTitle("MOVE TO")
        # The pivots the host's Move To can use, in its saved order (the combo
        # persists an index): manip / object pivot or a bounding-box location.
        cmb = menu.add(
            self.sb.registered_widgets.ComboBox,
            setObjectName="cmb005",
            setToolTip="Which point of the target to align the moved object(s) to: a "
            "pivot, or any bounding-box location (center and extents).",
        )
        cmb.add(list(self.tk.XformUtils.MOVE_TO_PIVOTS), prefix="Pivot:")
        cmb.setAsCurrent("center")
        menu.add(
            "QCheckBox",
            setText="Move All To Last",
            setObjectName="chk036",
            setChecked=True,
            setToolTip="Checked: every other selected object moves to the last selected "
            "(Blender: the active object).\nUnchecked: that object moves to the others' "
            "combined bounding box.",
        )
        menu.add(
            "QCheckBox",
            setText="Match Scale",
            setObjectName="chk_match_scale",
            setChecked=False,
            setToolTip="Also uniformly rescale the moved object(s) to the target's "
            "bounding-box size (no per-axis distortion).",
        )

    def tb005(self, widget):
        """Move To: move the selected objects onto the target, by a chosen pivot."""
        menu = widget.option_box.menu
        moved = self.tk.XformUtils.move_to_target(
            None,
            pivot=menu.cmb005.currentData() or "center",
            all_to_last=menu.chk036.isChecked(),
            match_scale=menu.chk_match_scale.isChecked(),
        )
        if not moved:
            self.sb.message_box(
                "<b>Move To</b> needs two or more selected objects: the last selected "
                "(Blender: the active object) is the target."
            )

    def b001(self):
        """Match Scale: scale the first selected (Blender: the active) object to the
        other selected objects' combined bounding box."""
        if not self.tk.XformUtils.match_scale(None, None):
            self.sb.message_box(
                "<b>Match Scale</b> needs two or more selected objects: the first "
                "selected (Blender: the active object) is scaled to the others."
            )

    # ------------------------------------------------------------------ tb003  Transform Constraints
    def tb003_init(self, widget):
        """Constraints: Edge / Surface / Make Live, seeded from the host."""
        menu = widget.option_box.menu
        menu.trigger_button = "left"
        menu.add_apply_button = False
        menu.setTitle("CONSTRAINTS")
        state = self.tk.XformUtils.get_transform_constraint()
        for name, text in (
            ("chk024", "Constrain: Edge"),
            ("chk025", "Constrain: Surface"),
            ("chk026", "Make Live"),
        ):
            menu.add(
                "QCheckBox",
                setObjectName=name,
                setText=text,
                setChecked=state[self._CONSTRAINTS[name]],
            )
        # Self-labelling, from the three boxes it means; applied at wire time, so
        # the label matches a scene that already has a constraint.
        self.sb.text_from(
            menu,
            widget,
            "chk024-26",
            lambda *on: "Constrain: ON" if any(on) else "Constrain: OFF",
        )

    def _init_constraint(self, widget):
        """Mirror a constraint box (the option box's or the submenu's) from the host."""
        kind = self._CONSTRAINTS[widget.objectName()]
        state = self.tk.XformUtils.get_transform_constraint()[kind]
        self.mirror_app_state(widget, lambda: widget.setChecked(state))

    def chk024_init(self, widget):
        self._init_constraint(widget)

    def chk025_init(self, widget):
        self._init_constraint(widget)

    def chk026_init(self, widget):
        self._init_constraint(widget)

    def _set_constraint(self, name, state):
        self.ui.tb003.init_slot()
        self.tk.XformUtils.set_transform_constraint(self._CONSTRAINTS[name], state)

    def chk024(self, state, widget):
        """Transform Constraints: Edge"""
        self._set_constraint("chk024", state)

    def chk025(self, state, widget):
        """Transform Constraints: Surface"""
        self._set_constraint("chk025", state)

    def chk026(self, state, widget):
        """Transform Constraints: Make Live (Blender: project onto surfaces)"""
        self._set_constraint("chk026", state)

    # ------------------------------------------------------------------ tb004  Transform Snap
    def tb004_init(self, widget):
        """Snap: Move / Scale / Rotate increment snapping, seeded from the host."""
        menu = widget.option_box.menu
        menu.trigger_button = "left"
        menu.add_apply_button = False
        menu.setTitle("SNAP")
        snap = self.tk.XformUtils.get_transform_snap()
        for kind, text, limits in (
            ("move", "Snap Move", [1, 1000, 1, 1]),
            ("scale", "Snap Scale", [1, 1000, 1, 1]),
            ("rotate", "Snap Rotate", [1.40625, 360, 0.40625, 5]),
        ):
            chk, spin = self._SNAP[kind]
            menu.add(
                self.sb.registered_widgets.CheckBox,
                setObjectName=chk,
                setText=text,
                setChecked=snap[kind]["enabled"],
            )
            increment = snap[kind]["increment"]
            spinbox = menu.add(
                "QDoubleSpinBox",
                setObjectName=spin,
                setPrefix="Degrees:" if kind == "rotate" else "Increment:",
                set_limits=limits,
                setEnabled=snap[kind]["enabled"],
                **({} if increment is None else {"setValue": increment}),
            )
            if kind != "rotate":
                # Blender snaps translation to the grid and has no scale increment.
                self._maya_only(spinbox)
        self.sb.text_from(
            menu,
            widget,
            "chk021-23",
            lambda *on: "Snap: ON" if any(on) else "Snap: OFF",
        )

    def _snap_kind(self, name):
        return next(kind for kind, names in self._SNAP.items() if name in names)

    def _init_snap(self, widget):
        """Mirror a snap box or increment (the option box's or the submenu's) from
        the host."""
        name = widget.objectName()
        snap = self.tk.XformUtils.get_transform_snap()[self._snap_kind(name)]
        if name.startswith("chk"):
            self.mirror_app_state(widget, lambda: widget.setChecked(snap["enabled"]))
        elif snap["increment"] is not None:
            self.mirror_app_state(widget, lambda: widget.setValue(snap["increment"]))
        else:
            self.mirror_app_state(widget)

    def chk021_init(self, widget):
        self._init_snap(widget)

    def chk022_init(self, widget):
        self._init_snap(widget)

    def chk023_init(self, widget):
        self._init_snap(widget)

    def s021_init(self, widget):
        self._init_snap(widget)

    def s022_init(self, widget):
        self._init_snap(widget)

    def s023_init(self, widget):
        self._init_snap(widget)

    def _set_snap(self, kind, state):
        """Toggle *kind* snapping, enabling its increment spinbox to match."""
        tb = self.ui.tb004
        tb.init_slot()
        getattr(tb.option_box.menu, self._SNAP[kind][1]).setEnabled(bool(state))
        self.tk.XformUtils.set_transform_snap(kind, state)

    def chk021(self, state, widget):
        """Transform Snap: Move"""
        self._set_snap("move", state)

    def chk022(self, state, widget):
        """Transform Snap: Scale"""
        self._set_snap("scale", state)

    def chk023(self, state, widget):
        """Transform Snap: Rotate"""
        self._set_snap("rotate", state)

    def s021(self, value, widget):
        """Transform Snap: the move increment."""
        self.tk.XformUtils.set_transform_snap("move", increment=value)

    def s022(self, value, widget):
        """Transform Snap: the scale increment."""
        self.tk.XformUtils.set_transform_snap("scale", increment=value)

    def s023(self, value, widget):
        """Transform Snap: the rotate increment (degrees)."""
        self.tk.XformUtils.set_transform_snap("rotate", increment=value)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
