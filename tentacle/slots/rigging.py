# !/usr/bin/python
# coding=utf-8
"""Rigging: one Slots class for both hosts.

Each control reads its widgets and calls one operation of the host toolkit
(``self.tk``): ``RigUtils`` for locators, switches, skins, utility nodes and
auto-riggers, ``XformUtils`` for rotate orders, ``DisplayUtils`` for the local
axes. Maya's joints, skinClusters and constraint nodes are Blender's armature
bones, Armature modifiers and object constraints; the operation says how. What
differs per host by nature -- the utility nodes, the auto-riggers, the lock
scopes -- is the host's own list (``RigUtils.UTILITY_NODES`` / ``AUTO_RIGS`` /
``LOCK_SCOPES``). Add to Skin and the joint display scale are Maya's
(``requires``); the group display is Blender's.
"""

import pythontk as ptk

from tentacle import Slots


class RiggingSlots(Slots):
    #: Euler orders, Maya-spelled and in its ``rotateOrder`` enum order; both
    #: hosts' ``create_locator_at_object`` take these names.
    ROTATE_ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")

    #: Quick Rig's procedural rigs: ``{label: tool panel}``. The panel names are
    #: the tools' (``slots/tools``); the host's own auto-riggers follow them
    #: (``RigUtils.AUTO_RIGS``).
    PROCEDURAL_RIGS = {
        "Tube Rig": "tube_rig",
        "Articulated Rig": "articulated_rig",
        "Wheel Rig": "wheel_rig",
        "Shadow Rig": "shadow_rig",
        "Telescope Rig": "telescope_rig",
    }

    #: Lock / Unlock's scopes, labelled. The host lists the scopes it serves
    #: (``RigUtils.LOCK_SCOPES``: Blender has no channel box).
    LOCK_SCOPE_LABELS = {
        "auto": "Attrs: Auto",
        "channel_box": "Attrs: Channel Box",
        "all": "Attrs: All",
        "translate": "Attrs: Translate",
        "rotate": "Attrs: Rotate",
        "scale": "Attrs: Scale",
    }

    #: Maya's joint display scales: ``(radio objectName, label, kind)``, the
    #: kind ``DisplayUtils.joint_display_scale`` takes.
    DISPLAY_SCALES = (
        ("chk004", "Joints", "joint"),
        ("chk001", "IK", "ik_handle"),
        ("chk002", "IK\\FK", "ik_fk"),
    )

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.rigging

    # ------------------------------------------------------------------ helpers
    def _host_only(self, widget, host):
        """Tag a code-built *widget* only *host* serves (uitk hides it on the
        other host, CODE_STANDARD section 15). Returns True when this host
        serves it."""
        widget.setProperty("requires", host)
        return not self.sb.apply_visibility_policy(widget)

    def _settings_key(self, base):
        """*base* namespaced by host (uitk's ``host_namespace_suffix``): Maya
        and Blender share one settings store."""
        suffix = self.sb.ShortcutManager.host_namespace_suffix(
            getattr(self.sb, "context_tags", None)
        )
        return base + suffix

    @staticmethod
    def _affix_arg(field):
        """``(text, mode)`` for an affix field, as the operation wants them.

        Scene mode reports ``(None, "auto")``: ``None`` tells
        ``RigUtils.create_locator_at_object`` to take the shared convention's
        entry for that node type -- spelling AND placement -- so the mode beside
        it is moot. Every other state is the user's literal text, placed as the
        picker says.
        """
        mode = field.option_box.affix_mode
        return (None, "auto") if mode == "convention" else (field.text(), mode)

    # ------------------------------------------------------------------ header  b020
    def header_init(self, widget):
        """Init Rigging Header"""
        # Every entry is a one-shot action: dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            "QPushButton",
            setText="Rebind Skin Clusters",
            setObjectName="b020",
            setToolTip="Rebind the selected skinned mesh(es), keeping their weights "
            "and bind pose (Blender: re-point their Armature modifiers).",
        )

    def b020(self):
        """Rebind Skin Clusters

        Pass/fail goes to the message box; the per-object breakdown (which mesh
        was rebound / skipped / failed and why) is printed to the console by
        ``RigUtils.rebind_skin_clusters``.
        """
        selection = self.require_selection()
        if selection is None:
            return
        result = self.tk.RigUtils.rebind_skin_clusters(selection)
        rebound = result["rebound"]
        no_skin = result["no_skin_cluster"]
        wrong_type = result["wrong_type"]
        failed = result["failed"]

        if rebound and not (no_skin or wrong_type or failed):
            msg = f"Rebound <hl>{len(rebound)}</hl> skin(s)."
        elif not rebound:
            # Nothing succeeded: the single most relevant reason.
            if failed:
                msg = (
                    f"<hl>Failed</hl> to rebind <hl>{len(failed)}</hl> "
                    "object(s). See the console for details."
                )
            elif wrong_type and not no_skin:
                msg = "<hl>Incorrect object type</hl>: select a skinned mesh."
            elif no_skin and not wrong_type:
                msg = "The selected object(s) have <hl>no skin</hl> to rebind."
            else:
                msg = (
                    "Nothing rebound: <hl>no skin</hl> / <hl>incorrect type</hl>. "
                    "See the console for details."
                )
        else:
            # Partial success: a short tally, the details on the console.
            parts = [f"Rebound <hl>{len(rebound)}</hl>"]
            if no_skin:
                parts.append(f"<hl>{len(no_skin)}</hl> without a skin")
            if wrong_type:
                parts.append(f"<hl>{len(wrong_type)}</hl> wrong type")
            if failed:
                parts.append(f"<hl>{len(failed)}</hl> failed")
            msg = ", ".join(parts) + ". See the console for details."
        self.sb.message_box(msg)

    # ------------------------------------------------------------------ cmb001  Create
    def cmb001_init(self, widget):
        """Init Create: the host's rigging utility nodes."""
        widget.add(list(self.tk.RigUtils.UTILITY_NODES), header="Utility Node:")

    def cmb001(self, index, widget):
        """Create: a rigging utility node the host's way (Maya: joint / IK
        handle tools, a lattice, a cluster; Blender: an armature, an Empty)."""
        try:
            self.tk.RigUtils.create_utility_node(widget.items[index])
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ cmb002  Quick Rig
    def cmb002_init(self, widget):
        """Init Quick Rig: the procedural rig tools, then the host's own
        character auto-riggers (Maya: Quick Rig, HumanIK; Blender: Rigify)."""
        items = list(self.PROCEDURAL_RIGS) + list(self.tk.RigUtils.AUTO_RIGS)
        widget.add(items, header="Quick Rig:")

    def cmb002(self, index, widget):
        """Quick Rig: open a procedural rig tool, or run the host's auto-rigger."""
        text = widget.items[index]
        tool = self.PROCEDURAL_RIGS.get(text)
        if tool:
            self.sb.handlers.marking_menu.show(tool)
            return
        try:
            self.tk.RigUtils.auto_rig(text)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Could not run <hl>{text}</hl>.<br>{error}")

    # ------------------------------------------------------------------ tb000  Local Rotation Axes
    def tb000_init(self, widget):
        """Init Display Local Rotation Axes"""
        menu = widget.option_box.menu
        menu.setTitle("Display Local Rotation Axes")
        menu.add(
            "QCheckBox",
            setText="Joint Axes",
            setObjectName="chk000",
            setChecked=False,
            setToolTip="On: toggle the joints' axes (Blender: the armature bones'): "
            "the selected ones, or with none selected every one in the scene.\n"
            "Off: toggle the selected objects' own axes.",
        )
        # Maya's global display scale of joints, IK handles and IK/FK joints
        # (Display > Animation); Blender has no such scale. Never restored: the
        # value IS Maya's, and the type picked is per session.
        scale = menu.add(
            "QDoubleSpinBox",
            setPrefix="Display Scale: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.5, 2],
            setToolTip="Maya's global display scale of the type picked below.",
        )
        radios = {
            kind: menu.add(
                "QRadioButton",
                setText=text,
                setObjectName=name,
                setChecked=kind == "joint",
                setToolTip=f"Show and edit the {text} display scale.",
            )
            for name, text, kind in self.DISPLAY_SCALES
        }
        controls = (scale, *radios.values())
        for control in controls:
            control.restore_state = False
        served = [self._host_only(control, "maya") for control in controls]
        if not all(served):
            return

        def kind():
            return next((k for k, r in radios.items() if r.isChecked()), "joint")

        def show():
            scale.setValue(self.tk.DisplayUtils.joint_display_scale(kind()))

        self.mirror_app_state(scale, seed=show)
        for radio in radios.values():
            radio.toggled.connect(
                lambda on: on and self.mirror_app_state(scale, seed=show)
            )
        scale.valueChanged.connect(
            lambda value: self.tk.DisplayUtils.joint_display_scale(kind(), value)
        )

    def tb000(self, widget):
        """Toggle Display Local Rotation Axes"""
        joints = widget.option_box.menu.chk000.isChecked()
        state = self.tk.DisplayUtils.toggle_local_axes(None, joints=joints)
        if state is None:
            self.sb.message_box(
                "No joints to toggle (Blender: no armatures)."
                if joints
                else "Select the objects whose axes to toggle."
            )
            return
        self.sb.message_box(
            f"Local Rotation Axes: <hl>{'On' if state else 'Off'}</hl>"
        )

    # ------------------------------------------------------------------ tb001  Constraint Switch
    def tb001_init(self, widget):
        """Init Constraint Switch"""
        menu = widget.option_box.menu
        menu.setTitle("Create Constraint Switch")
        menu.add(
            "QLineEdit",
            setPlaceholderText="Switch Name:",
            setText="switch",
            setObjectName="t003",
            setToolTip="The name of the switch attribute to create on the "
            "constrained object (Blender: a custom property).",
        )
        menu.add(
            "QLineEdit",
            setPlaceholderText="Anchor Name:",
            setText="",
            setObjectName="t004",
            setToolTip="Optional: a locator (Blender: an Empty) at the world origin, "
            "added as one more constraint target.\n"
            "Leave blank to switch only the existing targets.",
        )
        menu.add(
            "QCheckBox",
            setText="Weighted",
            setObjectName="chk003",
            setChecked=False,
            setToolTip="Blend smoothly between targets (a float) instead of snapping "
            "to one.\nMaya: two-target constraints only.",
        )

    def tb001(self, widget):
        """Constraint Switch: one attribute driving a constraint's targets."""
        menu = widget.option_box.menu
        target = self.tk.CoreUtils.active_object()
        if target is None:
            self.sb.message_box(
                "Nothing selected.<br>Select a <hl>constraint</hl> "
                "(Blender: the constrained object)."
            )
            return
        try:
            result = self.tk.RigUtils.connect_switch_to_constraint(
                constraint_node=target,
                attr_name=menu.t003.text() or "switch",
                weighted=menu.chk003.isChecked(),
                overwrite_existing=True,
                anchor=menu.t004.text().strip(),
            )
        except (TypeError, ValueError) as error:
            self.sb.message_box(
                f"{error}<br>Select a <hl>constraint</hl> (parent, point, orient, "
                "scale or aim; Blender: the constrained object)."
            )
            return
        # ``switch_attr`` is the success signal: the operation reports why it
        # built nothing to the console.
        if not result.get("switch_attr"):
            self.sb.message_box(
                "Could not create a constraint switch on "
                f"<hl>{self.tk.CoreUtils.leaf_name(target)}</hl>.<br>"
                "See the console for details."
            )
            return
        self.sb.message_box(
            f"Constraint switch <hl>{result['switch_attr']}</hl> created."
        )

    # ------------------------------------------------------------------ tb003  Create Locator
    def _locator_child_type_key(self) -> str:
        """The convention key the Scene affix state previews.

        The active (last selected) object's own type, so the field shows "_CAM"
        with a camera picked and "_GEO" with a mesh. Falls back to the mesh entry
        for an empty selection or a type the convention does not name: the field
        must always show a real affix, never an empty lock.
        """
        node = self.tk.CoreUtils.active_object()
        key = self.tk.Naming.type_key(node) if node is not None else "mesh"
        return key if ptk.NamingConvention.affix(key) else "mesh"

    def _add_rotate_order_combo(self, menu):
        """Add Create Locator's ``cmb011`` rotate-order picker to *menu*, with
        its Fix Rotate Order action (:meth:`_fix_rotate_order`)."""
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb011",
            setToolTip=(
                "The locator's rotate order. Its FIRST letter is the axis the\n"
                "prop can spin about (in Object mode) through ONE channel at\n"
                "any pose. In xyz, once X is keyed (a prop lifted and tilted),\n"
                "a spin about the locator's own Z writes X, Y and Z.\n"
                "Pick the order whose first letter is the spin axis\n"
                "(zyx for a Z spin, yzx for Y, xyz for X), and whose middle\n"
                "letter is the axis it turns least: the order locks (gimbal)\n"
                "when the middle channel reaches 90.\n"
                "Not sure yet? Animate first, then press the sync button."
            ),
        )
        for order in self.ROTATE_ORDERS:
            cmb.addItem(f"Rotate Order: {order}", order)
        cmb.option_box.set_action(
            callback=self._fix_rotate_order,
            icon="sync",
            tooltip=self.sb.tooltip.fmt(
                title="Fix Rotate Order",
                body="Give each selected locator the rotate order its own keys "
                "turn in: the one that puts every keyed turn on a single "
                "channel. That is also what takes the wobble out of a keyed "
                "turn.",
                notes=[
                    "Every key keeps its pose; the curves are re-solved.",
                    "Unkeyed locators, and hinges every order serves alike, "
                    "are left alone.",
                ],
            ),
        )
        return cmb

    def _fix_rotate_order(self):
        """cmb011's action: re-solve each selected locator's rotate order from
        its keys (``XformUtils.set_rotate_order(order="auto")``, one undo step)."""
        before = self.tk.XformUtils.get_rotate_order(None)
        if not before:
            self.sb.message_box("Select the locator(s) whose rotate order to fix.")
            return
        nodes = list(before)
        self.tk.XformUtils.set_rotate_order(nodes, "auto")
        # Keyed by node, not label: two selected nodes can share a short name.
        after = self.tk.XformUtils.get_rotate_order(nodes)
        name = self.tk.CoreUtils.leaf_name
        fixed = [
            f"{name(node)}: {order} → {after[node]}"
            for node, order in before.items()
            if after.get(node, order) != order
        ]
        kept = [name(node) for node, order in before.items() if after.get(node) == order]
        lines = (["<hl>Rotate order fixed:</hl>"] + fixed) if fixed else []
        if kept:
            lines.append(
                f"Unchanged ({', '.join(kept)}): no rotation keys, or every "
                "keyed turn is already one channel."
            )
        self.sb.message_box("<br>".join(lines))

    def tb003_init(self, widget):
        """Init Create Locator at Selection"""
        menu = widget.option_box.menu
        menu.setTitle("Create Locator")
        menu.add("Separator", setTitle="Scale")
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Locator Scale: ",
            setObjectName="s001",
            set_limits=[0, 1000, 1, 3],
            setValue=1,
            setToolTip="The display size of the locator (Maya: its shape's "
            "localScale; Blender: the Empty's size).",
        )
        group_display = menu.add(
            "QComboBox",
            setObjectName="cmb012",
            setToolTip=(
                "How the group Empty draws. Either way it exports, and goes\n"
                "to Maya, as a group.\n"
                "None: nothing, as a Maya group. A repeat click on the\n"
                "locator's centre cycles to it, as Blender cycles every\n"
                "object under a click.\n"
                "Ring: a circle around the locator. It marks the rig and\n"
                "gives the group a handle, and the locator's centre stays\n"
                "the locator's."
            ),
        )
        for text, data in (("None", "none"), ("Ring", "ring")):
            group_display.addItem(f"Group Display: {text}", data)
        # Blender's: a Maya group has no display to choose.
        self._host_only(group_display, "blender")
        self._add_rotate_order_combo(menu)
        menu.add("Separator", setTitle="Naming")
        # Seeded from the shared naming convention, not from literals: the group
        # and the locator are nodes this tool creates, so their type is known.
        grp_field = menu.add(
            "QLineEdit",
            setPlaceholderText="Group Suffix:",
            setText=ptk.NamingConvention.affix("group"),
            setObjectName="t002",
            setToolTip=(
                "Affix for the created group's name.\n"
                "The button beside the field sets placement: Auto / Suffix /\n"
                "Prefix, or 'Scene', which takes the shared naming\n"
                "convention's group entry, spelling and placement both.\n"
                "Edit that spelling in the Naming panel."
            ),
        )
        grp_field.option_box.set_affix(
            default="convention",
            convention_key="group",
            # ``t002`` alone is far too generic to namespace on.
            settings_key=self._settings_key("rigging_create_locator_grp_affix"),
        )
        loc_field = menu.add(
            "QLineEdit",
            setPlaceholderText="Locator Suffix:",
            setText=ptk.NamingConvention.affix("locator"),
            setObjectName="t000",
            setToolTip=(
                "Affix for the created locator's name.\n"
                "The button beside the field sets placement: Auto / Suffix /\n"
                "Prefix, or 'Scene', which takes the shared naming\n"
                "convention's locator entry, spelling and placement both.\n"
                "Edit that spelling in the Naming panel."
            ),
        )
        loc_field.option_box.set_affix(
            default="convention",
            convention_key="locator",
            settings_key=self._settings_key("rigging_create_locator_loc_affix"),
        )
        # Same picker as the two fields above, with one difference: the child is
        # whatever the user selected, so its Scene state is bound to the
        # SELECTION's type rather than a fixed one (a camera is not "_GEO"). The
        # field previews the active object and the operation resolves the rest
        # per object.
        obj_field = menu.add(
            "QLineEdit",
            setPlaceholderText="Geometry Suffix:",
            setText=ptk.NamingConvention.affix("mesh"),
            setObjectName="t001",
            setToolTip=(
                "Affix for the existing object's name.\n"
                "The button beside the field sets placement: Auto / Suffix /\n"
                "Prefix, or 'Scene', which affixes each object for its own\n"
                "type from the shared naming convention (mesh → _GEO,\n"
                "camera → _CAM, ...). Edit those spellings in the Naming panel."
            ),
        )
        obj_field.option_box.set_affix(
            default="convention",
            convention_key=self._locator_child_type_key,
            settings_key=self._settings_key("rigging_create_locator_obj_affix"),
        )
        menu.add(
            "QCheckBox",
            setText="Strip Digits",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Strip any trailing digits from the name before affixing it.",
        )
        menu.add(
            "QCheckBox",
            setText="Strip Suffix",
            setObjectName="chk006",
            setChecked=True,
            setToolTip=(
                "Strip the defined suffixes (Group, Locator, Geometry) from the "
                "name before re-suffixing it.\nIn 'Scene' mode this widens to "
                "every affix in the shared naming convention, so an object "
                "mis-named '_GEO' becomes '_CAM' rather than '_GEO_CAM'."
            ),
        )
        menu.add("Separator", setTitle="Lock Channels")
        menu.add(
            "QCheckBox",
            setText="Lock Child Translate",
            setObjectName="chk007",
            setChecked=False,
            setToolTip="Lock the translate channels of the child object.",
        )
        menu.add(
            "QCheckBox",
            setText="Lock Child Rotation",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Lock the rotation channels of the child object.",
        )
        menu.add(
            "QCheckBox",
            setText="Lock Child Scale",
            setObjectName="chk009",
            setChecked=False,
            setToolTip="Lock the scale channels of the child object.",
        )
        # Remove is an action, not a setting: it rides the option box as an
        # icon button beside the options (the Render Effects panel's idiom).
        widget.option_box.set_action(
            callback=self._remove_locator,
            icon="circle_remove",
            tooltip=self.sb.tooltip.fmt(
                title="Remove Locator",
                body="Dissolve the locator rig on the selection: unlock the "
                "child channels, hand the children back to the locator's own "
                "parent (world transforms kept), then delete the locator, and "
                "its group when that is left childless.",
                notes=["Select the locator(s) or their group, not the rigged geometry."],
            ),
        )

    def tb003(self, widget):
        """Create Locator at Selection: each selected object rigged under a
        zeroed locator and group (``RigUtils.create_locator_at_object``); with
        nothing selected, a lone locator (``RigUtils.add_locator``)."""
        menu = widget.option_box.menu
        rotate_order = menu.cmb011.currentData()
        selection = self.tk.CoreUtils.selected_objects()
        if not selection:
            # Sized by its display, as on a rig: a transform scale would carry
            # into anything parented under it.
            self.tk.RigUtils.add_locator(
                size=menu.s001.value(), rotate_order=rotate_order
            )
            return
        # "Scene" hands the decision to the operation: None takes the shared
        # convention's entry for that node type, spelling AND placement.
        grp_suffix, grp_affix_mode = self._affix_arg(menu.t002)
        loc_suffix, loc_affix_mode = self._affix_arg(menu.t000)
        obj_suffix, obj_affix_mode = self._affix_arg(menu.t001)
        try:
            self.tk.RigUtils.create_locator_at_object(
                selection,
                loc_scale=menu.s001.value(),
                grp_suffix=grp_suffix,
                grp_affix_mode=grp_affix_mode,
                loc_suffix=loc_suffix,
                loc_affix_mode=loc_affix_mode,
                obj_suffix=obj_suffix,
                obj_affix_mode=obj_affix_mode,
                strip_digits=menu.chk005.isChecked(),
                strip_suffix=menu.chk006.isChecked(),
                lock_translate=menu.chk007.isChecked(),
                lock_rotation=menu.chk008.isChecked(),
                lock_scale=menu.chk009.isChecked(),
                rotate_order=rotate_order,
                group_display=menu.cmb012.currentData(),
            )
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Could not create the locator rig.<br><hl>{error}</hl>")

    def _remove_locator(self):
        """Remove Locator: tb003's option-box action, the rig dissolved
        (``RigUtils.remove_locator``, one undo step)."""
        removed = self.tk.RigUtils.remove_locator(self.tk.CoreUtils.selected_objects())
        if not removed:
            self.sb.message_box(
                "No locator rig selected.<br>Select the locator(s) to remove, "
                "or their group."
            )

    # ------------------------------------------------------------------ tb004  Lock / Unlock
    def tb004_init(self, widget):
        """Init Lock/Unlock Attributes"""
        menu = widget.option_box.menu
        menu.setTitle("Lock / Unlock Attributes")
        # Lock vs Unlock is a two-valued choice, not a modifier: a combobox
        # names both states (its item text drives the button label).
        action = menu.add(
            "QComboBox",
            setObjectName="cmb_lock",
            setToolTip="Whether the button locks or unlocks the chosen attributes.",
        )
        action.addItems(["Lock", "Unlock"])
        action.setCurrentText("Unlock")  # the prior default (checkbox off = unlock)
        action.currentTextChanged.connect(widget.setText)
        widget.setText(action.currentText())
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb010",
            setToolTip="Which attributes to affect.\n"
            "Auto: the channel-box selection, else every transform attribute.\n"
            "Channel Box: only the attributes selected in the channel box.\n"
            "All / Translate / Rotate / Scale: those transform channels.\n"
            "(Blender has no channel box: All, Translate, Rotate and Scale.)",
        )
        for scope in self.tk.RigUtils.LOCK_SCOPES:
            cmb.addItem(self.LOCK_SCOPE_LABELS.get(scope, scope.title()), scope)

    def tb004(self, widget):
        """Lock/Unlock Attributes"""
        menu = widget.option_box.menu
        lock = menu.cmb_lock.currentText() == "Lock"
        try:
            objects, attrs = self.tk.RigUtils.lock_transforms(
                None, lock=lock, scope=menu.cmb010.currentData() or "all"
            )
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        if not objects:
            self.sb.message_box(self.NOTHING_SELECTED)
            return
        action = "Locked" if lock else "Unlocked"
        self.sb.message_box(
            f"{action} <hl>{len(attrs)}</hl> attr(s) on "
            f"<hl>{len(objects)}</hl> object(s)."
        )

    # ------------------------------------------------------------------ tb005  Add to Skin (Maya)
    def tb005_init(self, widget):
        """Init Add to Skin (Maya: the .ui hides it in Blender)."""
        menu = widget.option_box.menu
        menu.setTitle("Add to Skin")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb_skin_mode",
            setToolTip="Merge: one mesh, one skinCluster (UVs, normals and "
            "per-face materials kept).\n"
            "Separate: each mesh keeps its own node, bound to the same "
            "joints under the same bind pose.",
        )
        cmb.addItem("Merge Into Skinned Mesh", True)
        cmb.addItem("Bind As Separate Mesh", False)
        menu.add(
            "QCheckBox",
            setText="Rigid Insert",
            setObjectName="chk_skin_rigid",
            setToolTip="Give each added mesh ONE set of weights so it moves as "
            "a solid part (a connector, a bolt).\n"
            "Off: weights vary per vertex, so it bends with the surface.",
        )

    def tb005(self, widget):
        """Add to Skin: the selected mesh(es) skinned to the LAST selected one."""
        selection = self.tk.CoreUtils.selected_objects()
        if len(selection) < 2:
            self.sb.message_box(
                "Select the mesh(es) to add, then the <hl>skinned mesh</hl> last."
            )
            return
        menu = widget.option_box.menu
        try:
            self.tk.SkinUtils.add_to_skin(
                selection[-1],
                selection[:-1],
                combine=menu.cmb_skin_mode.currentData(),
                rigid=menu.chk_skin_rigid.isChecked(),
            )
        except ValueError as error:
            self.sb.message_box(f"<hl>Add to Skin</hl>: {error}")
            return
        self.sb.message_box(
            f"Added <hl>{len(selection) - 1}</hl> mesh(es) to "
            f"<hl>{self.tk.CoreUtils.leaf_name(selection[-1])}</hl>."
        )

    # ------------------------------------------------------------------ b004  Render Effects
    def b004(self):
        """Render Effects: the shared tool panel."""
        self.sb.handlers.marking_menu.show("render_effects")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
