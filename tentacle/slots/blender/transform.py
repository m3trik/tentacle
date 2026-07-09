# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class TransformSlots(SlotsBlender):
    """Blender port of the shared ``transform`` menu.

    The object-transform ops (drop-to-grid, freeze/un-freeze, move-to, match-scale,
    scale-connected-edges) are backed by ``blendertk.xform_utils`` (mirrors ``mtk.*``); the header
    adds Fix Non-Orthogonal Axes (``btk.fix_non_orthogonal_axes``) + a master Snap toggle. Align-To
    rides native ``object.align``; Transform Snap maps onto the scene tool-settings increment snap
    (``use_snap_translate/rotate/scale``) — the per-transform toggles, not Maya's numeric increment
    values (grid-driven in Blender). Make-Live maps onto face-projection snapping (tb003 Constrain
    menu); Maya rig/channel-box/DG-connection extras have no Blender analogue and are classified in
    the parity overrides.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.transform
        self.submenu = self.sb.loaded_ui.transform_submenu

    def header_init(self, widget):
        """Header — Fix Non-Orthogonal Axes + the Snap Toolset button. ``b_snap_ts`` mirrors Maya
        (cross-DCC rule: same objectName → same concept): it opens the Snap panel (vertex / surface
        / grid mesh-snapping), served from blendertk by the BlenderUiHandler. Transform-increment
        snapping (Blender's other 'snap' sense) is configured in the Transform Snap / Constraints
        option boxes (tb003/tb004), which carry their own objectNames."""
        widget.menu.add(
            "QPushButton", setText="Fix Non-Orthogonal Axes", setObjectName="fix_non_ortho_axes",
            setToolTip="Bake out non-orthogonal (sheared) axes on the selected objects "
            "(shear breaks FBX export).",
        )
        widget.menu.add(
            "QPushButton", setText="Snap", setObjectName="b_snap_ts",
            setToolTip="Open the Snap panel — snap vertices to a surface, the closest vertex, or "
            "the world grid.",
        )

    def b_snap_ts(self):
        """Snap Toolset — open the Snap panel (mirror of Maya's b_snap_ts)."""
        self.sb.handlers.marking_menu.show("snap")

    def fix_non_ortho_axes(self):
        """Fix Non-Orthogonal Axes (bake out shear on the selected objects)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Fix Non-Orthogonal Axes requires a selection.")
            return
        fixed = btk.fix_non_orthogonal_axes(objects)
        if fixed:
            self.sb.message_box(f"Fixed non-orthogonal axes on <hl>{len(fixed)}</hl> object(s).")
        else:
            self.sb.message_box("No non-orthogonal (sheared) axes found.")

    def _selection_source_target(self):
        """(source_objects, target) using Blender's active object as the target (= Maya's
        last-ordered-selection)."""
        target = self.active_object()
        source = [o for o in self.selected_objects() if o is not target]
        return source, target

    # ------------------------------------------------------------------ tb000  Drop To Grid
    def tb000_init(self, widget):
        widget.option_box.menu.add(
            "QComboBox", addItems=["Min", "Mid", "Max"], setObjectName="cmb004",
            setToolTip="Which bounding-box point to drop onto the grid (Z=0).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Move to Origin", setObjectName="chk014", setChecked=True,
            setToolTip="Move to the world origin (0,0,0) first.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Center Pivot", setObjectName="chk016", setChecked=True,
            setToolTip="Re-center the object origin on its bounding box.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Freeze Transforms", setObjectName="chk017", setChecked=True,
            setToolTip="Apply (bake) the transform after dropping.",
        )

    @btk.undoable
    def tb000(self, widget):
        """Drop To Grid"""
        m = widget.option_box.menu
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Drop To Grid requires a selection.")
            return
        btk.drop_to_grid(
            objects, align=m.cmb004.currentText(),
            origin=m.chk014.isChecked(), center_pivot=m.chk016.isChecked(),
        )
        if m.chk017.isChecked():
            btk.freeze_transforms(objects, location=True, rotation=False, scale=False)
        for o in objects:
            o.select_set(True)

    # ------------------------------------------------------------------ tb002  Freeze Transforms
    # chk032-34 / cmb_center_pivot / chk037 reuse the Maya names + labels for the SAME options.
    # Maya's rig-specific extras (Freeze Children, Restore Rig Anchors, Connection Strategy,
    # From Channel Box, Delete History) have no clean Blender analogue and are not mirrored.
    _CENTER_PIVOT_GEO = {"MESH", "CURVE", "SURFACE", "FONT", "META"}

    def tb002_init(self, widget):
        widget.option_box.menu.setTitle("Freeze Transforms")
        widget.option_box.menu.add(
            "QCheckBox", setText="Translate", setObjectName="chk032", setChecked=True,
            setToolTip="Bake translation -> 0,0,0.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Rotate", setObjectName="chk033",
            setToolTip="Bake rotation -> 0,0,0.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Scale", setObjectName="chk034", setChecked=True,
            setToolTip="Bake scale -> 1,1,1.",
        )
        widget.option_box.menu.add(
            "QComboBox", setObjectName="cmb_center_pivot",
            addItems=["Center Pivot: None", "Center Pivot: Mesh", "Center Pivot: All"],
            setCurrentIndex=0,
            setToolTip="After freezing, re-center the object origin on its bounding box.\n"
            "• None: leave the origin\n• Mesh: mesh objects only\n• All: all geometry objects",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Freeze Children", setObjectName="chk039",
            setToolTip="Also apply the transform to every descendant object (recursive), "
            "not just the selection.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Store Transforms", setObjectName="chk037", setChecked=True,
            setToolTip="Stamp the pre-freeze channels so Un-Freeze Transforms can restore them.",
        )

    @btk.undoable
    def tb002(self, widget):
        """Freeze Transformations"""
        m = widget.option_box.menu
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Freeze Transforms requires a selection.")
            return
        if m.chk039.isChecked():  # Freeze Children: extend to all descendants (deduped, order-kept)
            objects = list(dict.fromkeys(
                objects + [c for o in objects for c in o.children_recursive]
            ))
        btk.freeze_transforms(
            objects, location=m.chk032.isChecked(),
            rotation=m.chk033.isChecked(), scale=m.chk034.isChecked(),
            store=m.chk037.isChecked(),
        )
        # Center pivot runs AFTER freeze: freeze (location) sends the origin to world 0, then
        # this re-centers it on geometry (Blender's origin is the pivot — no separate channel).
        pivot_mode = m.cmb_center_pivot.currentIndex()  # 0 None, 1 Mesh, 2 All
        if pivot_mode:
            targets = [
                o for o in objects
                if (o.type == "MESH" if pivot_mode == 1 else o.type in self._CENTER_PIVOT_GEO)
            ]
            if targets:
                btk.center_pivot(targets, mode="object")

    # ------------------------------------------------------------------ tb005  Move To
    def tb005_init(self, widget):
        widget.option_box.menu.setTitle("Move To")
        widget.option_box.menu.add(
            "QComboBox", addItems=btk.XformUtils.get_pivot_options(), setObjectName="cmb005",
            setToolTip="Target pivot to align the source object(s) to.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Move All To Last", setObjectName="chk036", setChecked=True,
            setToolTip="Checked: all selected objects move to the active object.\n"
            "Unchecked: the active object moves to the other selected objects' bounding box.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Match Scale", setObjectName="chk_match_scale",
            setToolTip="Also rescale the moved object(s) to the target's bounding-box size.",
        )

    @btk.undoable
    def tb005(self, widget):
        """Move To (align source object(s) to the active/target object)."""
        m = widget.option_box.menu
        pivot = m.cmb005.currentText() or "center"
        others, active = self._selection_source_target()
        if not others or not active:
            self.sb.message_box("Move To requires 2+ selected objects (active = target).")
            return
        # Move All To Last: others -> active. Unchecked: active -> the others' combined bbox.
        source, target = (others, active) if m.chk036.isChecked() else ([active], others)
        if m.chk_match_scale.isChecked():
            btk.match_scale(source, target)
        btk.move_to(source, target, pivot=pivot)

    # ------------------------------------------------------------------ b001  Match Scale
    @btk.undoable
    def b001(self):
        """Match Scale (rescale source object(s) to the active/target object)."""
        source, target = self._selection_source_target()
        if not source or not target:
            self.sb.message_box("Match Scale requires 2+ selected objects (active = target).")
            return
        btk.match_scale(source, target)

    # ------------------------------------------------------------------ cmb002  Align To
    # Combo label -> object.align axis set (centers, relative to the active object).
    _ALIGN_AXES = {
        "Align X to Active": {"X"},
        "Align Y to Active": {"Y"},
        "Align Z to Active": {"Z"},
        "Align Centers to Active": {"X", "Y", "Z"},
    }

    def cmb002_init(self, widget):
        widget.add(list(self._ALIGN_AXES), header="Align To")

    @btk.undoable
    def cmb002(self, index, widget):
        """Align To (object centers onto the active object's, native ``object.align``)."""
        axis = self._ALIGN_AXES.get(widget.items[index])
        if axis is None:
            return
        if len(self.selected_objects()) < 2:
            self.sb.message_box("Align requires 2+ selected objects (active = target).")
            return
        try:
            bpy.ops.object.align(
                align_mode="OPT_2", relative_to="OPT_4", align_axis=axis
            )
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ tb004  Transform Snap
    def _set_snap(self, **kinds):
        """Apply transform-kind snap flags (``translate``/``rotate``/``scale``) to the scene
        tool settings; snapping enables on INCREMENT while any kind is on."""
        ts = bpy.context.scene.tool_settings
        for kind, state in kinds.items():
            setattr(ts, f"use_snap_{kind}", bool(state))
        enabled = ts.use_snap_translate or ts.use_snap_rotate or ts.use_snap_scale
        ts.use_snap = enabled
        if enabled:
            try:
                ts.snap_elements = {"INCREMENT"}
            except AttributeError:  # 4.x split: snap_elements_base/_individual
                ts.snap_elements_base = {"INCREMENT"}

    def tb004_init(self, widget):
        widget.option_box.menu.setTitle("SNAP")
        ts = bpy.context.scene.tool_settings
        widget.option_box.menu.add(
            "QCheckBox", setText="Snap Move", setObjectName="chk021",
            setChecked=ts.use_snap_translate,
            setToolTip="Snap translation to increments (Blender grid-increment snap).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Snap Scale", setObjectName="chk022",
            setChecked=ts.use_snap_scale,
            setToolTip="Snap scaling to increments.",
        )

    def tb004(self, widget):
        """Transform Snap (per-transform increment snapping via the scene tool settings — Blender
        snaps to the grid increment; the Maya numeric increment spinboxes are not mirrored)."""
        m = widget.option_box.menu
        self._set_snap(translate=m.chk021.isChecked(), scale=m.chk022.isChecked())

    # chk023 (Snap Rotate) is a static widget in transform#submenu.ui (its sibling chk021/chk022
    # are tb004 option-box-only), so it stays a standalone live toggle here rather than being
    # re-built in tb004_init (which would duplicate the objectName). Parity: done-elsewhere.
    def chk023_init(self, widget):
        """Snap Rotate toggle — reflect the live tool-settings state."""
        widget.setChecked(bpy.context.scene.tool_settings.use_snap_rotate)

    def chk023(self, state, widget):
        """Snap: Rotate (increment rotation snapping)."""
        self._set_snap(rotate=state)

    # ------------------------------------------------------------------ tb001  Scale Connected Edges
    def tb001_init(self, widget):
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="s001",
            setPrefix="Scale Factor:",
            setValue=1.1,
            set_limits=[-999, 999, 0.1],
            setToolTip="Scale factor to apply to scaling by as a percentage.",
        )

    @btk.undoable
    def tb001(self, widget):
        """Scale Connected Edges (each connected set of selected edges scales about its
        own centroid — edit-mode workflow)."""
        factor = widget.option_box.menu.s001.value()
        scaled = btk.scale_connected_edges(self.selected_objects(), scale_factor=factor)
        if not scaled:
            self.sb.message_box(
                "<strong>No connected edges scaled.</strong><br>Select edges on a mesh "
                "in Edit Mode first."
            )

    # ------------------------------------------------------------------ b002  Un-Freeze Transforms
    @btk.undoable
    def b002(self):
        """Un-Freeze Transforms (restore the channels stamped by Freeze; the object's
        world position is preserved)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Un-Freeze Transforms requires a selection.")
            return
        restored = btk.restore_transforms(objects)
        if not restored:
            self.sb.message_box(
                "<strong>Nothing to restore.</strong><br>No selected object carries "
                "stored freeze data (it is stamped by Freeze Transforms)."
            )

    # ------------------------------------------------------------------ tb003  Transform Constraints
    # Maya's xformConstraint maps onto snap-to-element during move: Constrain Edge/Surface
    # become EDGE/FACE snap (single-element, like Maya's one-type-at-a-time constraint).
    # Make Live (chk026) maps onto face-projection snapping (FACE_NEAREST, Blender's
    # retopology "stick to surface"): Maya designates one live surface, Blender projects
    # onto every snap-target surface (use_snap_self/_nonedit gate the pool) — accepted delta.
    # Edge/Surface/Make-Live act as a radio cluster (Blender's snap setters cross-clear the
    # base/individual axes); any toggle off turns snapping off.
    @staticmethod
    def _snap_elements():
        """Live snap-element set (combined ``snap_elements`` where present, else the base
        set) — used for the Edge/Surface (EDGE/FACE) constraint reflection."""
        ts = bpy.context.scene.tool_settings
        try:
            return set(ts.snap_elements)
        except AttributeError:  # 4.x split: snap_elements_base/_individual
            return set(ts.snap_elements_base)

    @staticmethod
    def _snap_individual():
        """Live per-element projection modes (FACE_PROJECT/FACE_NEAREST) as a set."""
        ts = bpy.context.scene.tool_settings
        try:
            return set(ts.snap_elements_individual)
        except AttributeError:  # pre-4.0 combined property
            return {e for e in ts.snap_elements if e in ("FACE_NEAREST", "FACE_PROJECT")}

    def _set_constraint_snap(self, element, state):
        """Apply/clear an element constraint (``EDGE``/``FACE``) via the scene snap
        settings — enabling one replaces the other; disabling turns snapping off."""
        ts = bpy.context.scene.tool_settings
        if state:
            try:
                ts.snap_elements = {element}
            except AttributeError:
                ts.snap_elements_base = {element}
            ts.use_snap = True
            ts.use_snap_translate = True
        else:
            ts.use_snap = False

    def _set_project_snap(self, state):
        """Make Live analogue — toggle face-projection snapping so transformed geometry
        sticks to surfaces (FACE_NEAREST, the per-element 'individual' snap axis). Enabling
        replaces any Edge/Surface base constraint: Blender's snap setters cross-clear the
        base/individual axes, so the three act as a radio cluster like chk024<->chk025;
        disabling turns snapping off (mirrors ``_set_constraint_snap``)."""
        ts = bpy.context.scene.tool_settings
        if state:
            try:  # 4.0+: FACE_NEAREST/FACE_PROJECT live in the 'individual' set
                ts.snap_elements_individual = {"FACE_NEAREST"}
            except AttributeError:  # pre-split combined property
                ts.snap_elements = {"FACE_NEAREST"}
            ts.use_snap = True
            ts.use_snap_translate = True
        else:
            ts.use_snap = False

    def tb003_init(self, widget):
        """Constraints Init (mirrors the Maya option box; state reflects the live snap)."""
        widget.option_box.menu.trigger_button = "left"
        widget.option_box.menu.add_apply_button = False
        widget.option_box.menu.setTitle("CONSTRAINTS")
        use_snap = bpy.context.scene.tool_settings.use_snap
        active = self._snap_elements() if use_snap else set()
        individual = self._snap_individual() if use_snap else set()
        values = [
            ("chk024", "Constrain: Edge", "EDGE" in active),
            ("chk025", "Constrain: Surface", "FACE" in active),
            ("chk026", "Make Live", "FACE_NEAREST" in individual),
        ]
        for name, text, state in values:
            widget.option_box.menu.add(
                "QCheckBox",
                setObjectName=name,
                setText=text,
                setChecked=state,
            )

        def update_text():
            state = any(
                w.isChecked() for w in widget.option_box.menu.get_items("QCheckBox")
            )
            widget.setText("Constrain: ON" if state else "Constrain: OFF")

        update_text()
        self.sb.connect_multi(widget.menu, "chk024-26", "toggled", update_text)

    def chk024(self, state, widget):
        """Transform Constraints: Edge (snap-to-edge during move)."""
        self._set_constraint_snap("EDGE", state)
        self.ui.tb003.init_slot()

    def chk025(self, state, widget):
        """Transform Constraints: Surface (snap-to-face during move)."""
        self._set_constraint_snap("FACE", state)
        self.ui.tb003.init_slot()

    def chk026(self, state, widget):
        """Transform Constraints: Make Live (project transformed geometry onto surfaces —
        Blender's retopology face-snap; Maya's makeLive analogue)."""
        self._set_project_snap(state)
        self.ui.tb003.init_slot()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
