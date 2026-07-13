# !/usr/bin/python
# coding=utf-8
import bpy
import pythontk as ptk
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Rigging(SlotsBlender):
    """Blender port of the shared ``rigging`` menu.

    The most divergent domain (Maya skinCluster/joint/IK → Blender Armature + vertex groups +
    constraints), but most operations map cleanly and reuse the Maya objectNames: locators are
    Empties (tb003 — LOC/GRP/GEO hierarchy, naming, channel locks), attribute locking drives the
    transform lock flags (tb004), local-rotation-axes toggles ``show_axis``/``show_axes`` (tb000),
    Rebind Skin refreshes the Armature modifier preserving vertex-group weights (b020), and the
    Constraint Switch is built natively from a custom property driving the constraints' influence
    (tb001). Quick Rig wraps the bundled Rigify add-on. The Maya joint/IK display-scale knobs and
    the Render-Opacity Unity-pipeline tool have no Blender analogue and are excused/deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.rigging

    # ------------------------------------------------------------------ header  b020 Rebind Skin
    def header_init(self, widget):
        # b020 reuses the Maya header objectName/label (Rebind Skin Clusters).
        widget.menu.add(
            "QPushButton", setText="Rebind Skin Clusters", setObjectName="b020",
            setToolTip="Refresh the Armature modifier binding on the selected mesh(es), preserving "
            "vertex-group weights (the Blender analogue of rebinding a skinCluster).",
        )

    @btk.undoable
    def b020(self):
        """Rebind Skin Clusters — refresh each selected mesh's Armature modifier (re-point it at its
        armature), keeping the vertex groups/weights intact. Falls back to the mesh's armature parent."""
        meshes = [o for o in self.selected_objects() if o.type == "MESH"]
        if not meshes:
            self.sb.message_box("Rebind Skin requires selected mesh(es).")
            return
        active = bpy.context.view_layer.objects.active
        scene_arm = active if (active and active.type == "ARMATURE") else None
        rebound = 0
        for mesh in meshes:
            arm_mods = [m for m in mesh.modifiers if m.type == "ARMATURE"]
            arm = next((m.object for m in arm_mods if m.object), None)
            if arm is None and mesh.parent and mesh.parent.type == "ARMATURE":
                arm = mesh.parent
            arm = arm or scene_arm
            if arm is None:
                continue
            for m in arm_mods:  # drop stale modifiers; vertex groups (weights) persist on the mesh
                mesh.modifiers.remove(m)
            mod = mesh.modifiers.new(name="Armature", type="ARMATURE")
            mod.object = arm
            mod.use_vertex_groups = True
            rebound += 1
        self.sb.message_box(f"Rebound skin on <hl>{rebound}</hl> mesh(es).")

    # ------------------------------------------------------------------ cmb001  Create
    def cmb001_init(self, widget):
        widget.add(["Armature", "Empty"], header="Create")

    @btk.undoable
    def cmb001(self, index, widget):
        """Create rigging primitives."""
        text = widget.items[index]
        if text == "Armature":
            bpy.ops.object.armature_add()
        elif text == "Empty":
            bpy.ops.object.empty_add(type="PLAIN_AXES")

    # ------------------------------------------------------------------ tb000  Local rotation axes
    def tb000_init(self, widget):
        # chk000 reuses the Maya name/label (Joints). Maya's IK / IK\\FK radios (chk001/chk002) and
        # the global display-scale spinbox (s000) have no Blender analogue and are excused.
        widget.option_box.menu.setTitle("Display Local Rotation Axes")
        widget.option_box.menu.add(
            "QCheckBox", setText="Joints", setObjectName="chk000", setChecked=False,
            setToolTip="Target armature BONE axes (show_axes) instead of object axes (show_axis).",
        )

    @btk.undoable
    def tb000(self, widget):
        """Toggle Display Local Rotation Axes — object axes (show_axis), or armature bone axes
        (show_axes) when 'Joints' is on."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Toggle Axes requires a selection.")
            return
        if widget.option_box.menu.chk000.isChecked():
            arms = [o for o in objects if o.type == "ARMATURE"]
            if not arms:
                self.sb.message_box("No armatures selected (Joints mode targets bone axes).")
                return
            state = not arms[0].data.show_axes
            for a in arms:
                a.data.show_axes = state
        else:
            state = not objects[0].show_axis
            for o in objects:
                o.show_axis = state

    # ------------------------------------------------------------------ tb001  Constraint Switch
    def tb001_init(self, widget):
        # t003 / t004 / chk003 reuse the Maya names + labels for the SAME options.
        m = widget.option_box.menu
        m.setTitle("Create Constraint Switch")
        m.add(
            "QLineEdit", setPlaceholderText="Switch Name:", setText="switch", setObjectName="t003",
            setToolTip="Name of the custom property created on the active object to drive the switch.",
        )
        m.add(
            "QLineEdit", setPlaceholderText="Anchor Name:", setText="", setObjectName="t004",
            setToolTip="Optional: create an Empty at the world origin as an additional Copy-Transforms "
            "target before building the switch. Leave blank to switch only existing constraints.",
        )
        m.add(
            "QCheckBox", setText="Weighted", setObjectName="chk003", setChecked=False,
            setToolTip="Smooth float blend between targets (influence falls off with distance from "
            "each index) instead of a hard snap to the nearest target.",
        )

    @btk.undoable
    def tb001(self, widget):
        """Constraint Switch — drive the active object's constraints' influence from a single custom
        property (the Blender analogue of Maya's IK/FK switch attribute). Snap (nearest index) or,
        when Weighted, a smooth float blend; an optional anchor Empty adds one more target first."""
        m = widget.option_box.menu
        active = bpy.context.view_layer.objects.active
        if active is None:
            self.sb.message_box("Constraint Switch requires an active (constrained) object.")
            return
        switch_name = m.t003.text() or "switch"
        weighted = m.chk003.isChecked()
        anchor_name = m.t004.text().strip()

        if anchor_name:  # add an anchor Empty at world origin as an extra Copy-Transforms target
            anchor = bpy.data.objects.new(anchor_name, None)
            anchor.empty_display_type = "PLAIN_AXES"
            bpy.context.collection.objects.link(anchor)
            con = active.constraints.new(type="COPY_TRANSFORMS")
            con.target = anchor

        constraints = [c for c in active.constraints if getattr(c, "target", None)]
        if len(constraints) < 2:
            self.sb.message_box(
                "Constraint Switch needs the active object to have <hl>2+</hl> targeted constraints "
                "(add them, or use an Anchor Name to create one)."
            )
            return

        n = len(constraints)
        active[switch_name] = 0.0
        try:  # clamp the property's UI slider to the valid index range (4.x id-prop UI API)
            active.id_properties_ui(switch_name).update(min=0.0, max=float(n - 1))
        except (AttributeError, TypeError):
            pass
        for i, con in enumerate(constraints):
            con.driver_remove("influence")
            drv = con.driver_add("influence").driver
            var = drv.variables.new()
            var.name = "s"
            var.type = "SINGLE_PROP"
            var.targets[0].id = active
            var.targets[0].data_path = f'["{switch_name}"]'
            # Only abs() is used (always in Blender's restricted driver namespace; round() isn't
            # guaranteed). Weighted = triangular falloff; snap = 1 when i is the nearest index.
            drv.expression = (
                f"max(0.0, 1.0 - abs(s - {i}))" if weighted else f"1.0 if abs(s - {i}) < 0.5 else 0.0"
            )
        self.sb.message_box(
            f"Constraint Switch '<hl>{switch_name}</hl>' drives <hl>{n}</hl> constraints on "
            f"{active.name}."
        )

    # ------------------------------------------------------------------ tb003/b003  Locators (Empties)
    def tb003_init(self, widget):
        # s001 / t000 / t001 / t002 / chk005 / chk006 / chk007 / chk008 / chk009 reuse the Maya
        # names + labels for the SAME options. Locators are Empties; the GRP/LOC/GEO hierarchy maps
        # onto parented Empties + the renamed geometry.
        m = widget.option_box.menu
        m.setTitle("Create Locator")
        m.add("Separator", setTitle="Scale")
        m.add(
            "QDoubleSpinBox", setPrefix="Locator Scale: ", setObjectName="s001",
            set_limits=[0, 1000, 1, 3], setValue=1.0, setToolTip="Display size of the locator Empty.",
        )
        m.add("Separator", setTitle="Naming")
        m.add(
            "QLineEdit", setPlaceholderText="Group Suffix:", setText="_GRP", setObjectName="t002",
            setToolTip="Suffix appended to the created group (parent Empty) name.",
        )
        m.add(
            "QLineEdit", setPlaceholderText="Locator Suffix:", setText="_LOC", setObjectName="t000",
            setToolTip="Suffix appended to the created locator (Empty) name.",
        )
        m.add(
            "QLineEdit", setPlaceholderText="Geometry Suffix:", setText="_GEO", setObjectName="t001",
            setToolTip="Suffix appended to the existing geometry's name.",
        )
        m.add(
            "QCheckBox", setText="Strip Digits", setObjectName="chk005", setChecked=True,
            setToolTip="Strip trailing digits from the base name before applying suffixes.",
        )
        m.add(
            "QCheckBox", setText="Strip Suffix", setObjectName="chk006", setChecked=True,
            setToolTip="Strip an existing Group/Locator/Geometry suffix from the base name first.",
        )
        m.add("Separator", setTitle="Lock Channels")
        m.add(
            "QCheckBox", setText="Lock Child Translate", setObjectName="chk007", setChecked=False,
            setToolTip="Lock the geometry's location channels after parenting it to the locator.",
        )
        m.add(
            "QCheckBox", setText="Lock Child Rotation", setObjectName="chk008", setChecked=False,
            setToolTip="Lock the geometry's rotation channels.",
        )
        m.add(
            "QCheckBox", setText="Lock Child Scale", setObjectName="chk009", setChecked=False,
            setToolTip="Lock the geometry's scale channels.",
        )

    @staticmethod
    def _locator_base_name(name, suffixes, strip_digits, strip_suffix):
        """Derive the base name for a locator set: optionally strip a known suffix then trailing
        digits/underscores (shared pythontk string logic)."""
        base = name
        if strip_suffix:
            for suf in suffixes:
                if suf and base.endswith(suf):
                    base = base[: -len(suf)]
                    break
        if strip_digits:
            base = ptk.StrUtils.format_suffix(base, strip="_", strip_trailing_ints=True) or base
        return base

    @btk.undoable
    def tb003(self, widget):
        """Create Locator at Selection — an Empty (locator) at each selected object's origin,
        parented under a group Empty, with the geometry renamed and (optionally) channel-locked.
        A lone Empty at the cursor when nothing is selected."""
        objects = self.selected_objects()
        m = widget.option_box.menu
        if not objects:
            bpy.ops.object.empty_add(type="PLAIN_AXES")
            return
        scale = m.s001.value()
        grp_suffix, loc_suffix, obj_suffix = m.t002.text(), m.t000.text(), m.t001.text()
        strip_digits, strip_suffix = m.chk005.isChecked(), m.chk006.isChecked()
        lock = (m.chk007.isChecked(), m.chk008.isChecked(), m.chk009.isChecked())
        suffixes = (grp_suffix, loc_suffix, obj_suffix)

        for o in objects:
            coll = o.users_collection[0] if o.users_collection else bpy.context.scene.collection
            base = self._locator_base_name(o.name, suffixes, strip_digits, strip_suffix)
            loc = bpy.data.objects.new(f"{base}{loc_suffix}", None)
            loc.empty_display_type = "PLAIN_AXES"
            loc.empty_display_size = scale
            loc.matrix_world = o.matrix_world.copy()
            coll.objects.link(loc)

            grp = bpy.data.objects.new(f"{base}{grp_suffix}", None)
            grp.empty_display_type = "PLAIN_AXES"
            grp.matrix_world = o.matrix_world.copy()
            coll.objects.link(grp)

            loc.parent = grp
            loc.matrix_parent_inverse = grp.matrix_world.inverted()
            # parent geometry to the locator so it follows; keep its world transform
            o.parent = loc
            o.matrix_parent_inverse = loc.matrix_world.inverted()
            if obj_suffix and not o.name.endswith(obj_suffix):
                o.name = f"{base}{obj_suffix}"
            o.lock_location = (lock[0],) * 3
            o.lock_rotation = (lock[1],) * 3
            o.lock_scale = (lock[2],) * 3

    @btk.undoable
    def b003(self):
        """Remove Locator (delete selected Empties)."""
        empties = [o for o in self.selected_objects() if o.type == "EMPTY"]
        if not empties:
            self.sb.message_box("No Empties selected.")
            return
        for o in empties:
            bpy.data.objects.remove(o, do_unlink=True)

    # ------------------------------------------------------------------ tb004  Lock/Unlock Attributes
    def tb004_init(self, widget):
        # cmb_lock / cmb010 mirror the Maya panel. Maya's cmb010 'Channel Box' scope has no
        # Blender analogue (no channel box), so the combo offers per-transform-group scopes instead.
        m = widget.option_box.menu
        m.setTitle("Lock / Unlock Attributes")
        # Lock vs Unlock is a two-valued choice, not a modifier — a combobox names both
        # states (its item text drives the button label); extend with e.g. "Toggle" later.
        action = m.add(
            "QComboBox", setObjectName="cmb_lock",
            setToolTip="Whether the button locks or unlocks the chosen channels.",
        )
        action.addItems(["Lock", "Unlock"])
        action.setCurrentText("Unlock")  # preserve prior default (checkbox off = unlock)
        action.currentTextChanged.connect(widget.setText)
        widget.setText(action.currentText())
        cmb = m.add(
            "QComboBox", setObjectName="cmb010",
            setToolTip="Which transform channels to affect (Blender has no channel box).",
        )
        for text, data in [
            ("Attrs: All", "all"), ("Attrs: Translate", "translate"),
            ("Attrs: Rotate", "rotate"), ("Attrs: Scale", "scale"),
        ]:
            cmb.addItem(text, data)

    @btk.undoable
    def tb004(self, widget):
        """Lock/Unlock Attributes (transform channel lock flags, per the chosen scope)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Lock/Unlock requires a selection.")
            return
        m = widget.option_box.menu
        lock = m.cmb_lock.currentText() == "Lock"
        scope = m.cmb010.currentData() or "all"
        for o in objects:
            if scope in ("all", "translate"):
                o.lock_location = (lock,) * 3
            if scope in ("all", "rotate"):
                o.lock_rotation = (lock,) * 3
            if scope in ("all", "scale"):
                o.lock_scale = (lock,) * 3
        action = "Locked" if lock else "Unlocked"
        self.sb.message_box(f"{action} <hl>{scope}</hl> channels on <hl>{len(objects)}</hl> object(s).")

    # ------------------------------------------------------------------ cmb002  Quick Rig (Rigify)
    @staticmethod
    def _enable_rigify():
        """Enable the bundled Rigify add-on (idempotent). Returns True when available."""
        import addon_utils

        try:
            addon_utils.enable("rigify", default_set=True)
            return True
        except Exception:
            return False

    def cmb002_init(self, widget):
        # Procedural rigs (mayatk parity — each opens its co-located blendertk panel) +
        # Rigify character rigging (Blender-native; Maya does this via HumanIK, not Quick Rig).
        widget.add(
            ["Telescope Rig", "Wheel Rig", "Shadow Rig", "Tube Rig", "Human Meta-Rig",
             "Basic Human Meta-Rig", "Generate Rig"],
            header="Quick Rig:",
        )

    @btk.undoable
    def cmb002(self, index, widget):
        """Quick Rig — a procedural rig opens its panel (mayatk parity); the Rigify items add a
        meta-rig, or Generate Rig on the active meta-rig armature."""
        text = widget.items[index]
        if text == "Telescope Rig":
            self.sb.handlers.marking_menu.show("telescope_rig")
            return
        if text == "Wheel Rig":
            self.sb.handlers.marking_menu.show("wheel_rig")
            return
        if text == "Shadow Rig":
            self.sb.handlers.marking_menu.show("shadow_rig")
            return
        if text == "Tube Rig":
            self.sb.handlers.marking_menu.show("tube_rig")
            return
        if not self._enable_rigify():
            self.sb.message_box("The Rigify add-on could not be enabled.")
            return
        try:
            if text == "Human Meta-Rig":
                bpy.ops.object.armature_human_metarig_add()
            elif text == "Basic Human Meta-Rig":
                bpy.ops.object.armature_basic_human_metarig_add()
            elif text == "Generate Rig":
                obj = bpy.context.view_layer.objects.active
                if not obj or obj.type != "ARMATURE":
                    self.sb.message_box("Generate Rig requires an active meta-rig armature.")
                    return
                bpy.ops.pose.rigify_generate()
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ deferred
    def b004(self):
        """Render Opacity — co-located blendertk panel (keyable per-object ``opacity`` prop driving
        Principled Alpha; ``key_fade`` dual-keys opacity + render visibility for the Maya→Unity
        parity invariant). Mirrors Maya's rigging b004."""
        self.sb.handlers.marking_menu.show("render_opacity")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
