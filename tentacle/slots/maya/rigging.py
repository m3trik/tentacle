# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk

# From this package:
from tentacle.slots.maya._slots_maya import SlotsMaya


class Rigging(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def header_init(self, widget):
        """Init Rigging Header"""
        widget.menu.add(
            "QPushButton",
            setText="Rebind Skin Clusters",
            setObjectName="b020",
            setToolTip="Rebinds skinClusters on the selected meshe(s), preserving weights, bind pose.",
        )
        widget.menu.b020.clicked.connect(self.b020)

    def b020(self):
        """Rebind Skin Clusters

        Simple pass/fail feedback goes to the message box; the per-object
        breakdown (which mesh was rebound / skipped / failed and why) is
        printed to the console by ``mtk.rebind_skin_clusters``.
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box("Nothing selected.")
            return

        result = mtk.rebind_skin_clusters(selection)
        rebound = result["rebound"]
        no_skin = result["no_skin_cluster"]
        wrong_type = result["wrong_type"]
        failed = result["failed"]

        if rebound and not (no_skin or wrong_type or failed):
            msg = f"Rebound <hl>{len(rebound)}</hl> skinCluster(s)."
        elif not rebound:
            # Nothing succeeded — surface the single most relevant reason.
            if failed:
                msg = (
                    f"<hl>Failed</hl> to rebind <hl>{len(failed)}</hl> "
                    "object(s). See console for details."
                )
            elif wrong_type and not no_skin:
                msg = "<hl>Incorrect object type</hl> — select a skinned mesh."
            elif no_skin and not wrong_type:
                msg = "Selected object(s) have <hl>no skinClusters</hl>."
            else:
                msg = (
                    "Nothing rebound — <hl>no skinClusters</hl> / "
                    "<hl>incorrect type</hl>. See console for details."
                )
        else:
            # Partial success — short tally, details on the console.
            parts = [f"Rebound <hl>{len(rebound)}</hl>"]
            if no_skin:
                parts.append(f"<hl>{len(no_skin)}</hl> w/o skinCluster")
            if wrong_type:
                parts.append(f"<hl>{len(wrong_type)}</hl> wrong type")
            if failed:
                parts.append(f"<hl>{len(failed)}</hl> failed")
            msg = ", ".join(parts) + ". See console for details."

        self.sb.message_box(msg)

    def cmb001_init(self, widget):
        """Init Create"""
        items = sorted(["Joints", "IK Handle", "Lattice", "Cluster"])
        widget.add(items, header="Utility Node:")

    def cmb001(self, index, widget):
        """Create: create a rigging utility node — joints, IK handle, lattice, or cluster."""
        text = widget.itemText(index)
        if text == "Joints":
            cmds.setToolTo("jointContext")  # create joint tool
        elif text == "IK Handle":
            cmds.setToolTo("ikHandleContext")  # create ik handle
        elif text == "Lattice":  # create lattice
            cmds.lattice(divisions=[2, 5, 2], objectCentered=1, ldv=[2, 2, 2])
        elif text == "Cluster":
            mel.eval("CreateCluster")  # create cluster

    def cmb002_init(self, widget):
        """Init Quick Rig"""
        items = ["Tube Rig", "Wheel Rig", "Shadow Rig", "Telescope Rig"]
        widget.add(items, header="Quick Rig:")

    def cmb002(self, index, widget):
        """Quick Rig: open a quick-rig tool (tube, wheel, shadow, or telescope rig)."""
        text = widget.items[index]
        if text == "Tube Rig":
            self.sb.handlers.marking_menu.show("tube_rig")
        elif text == "Wheel Rig":
            self.sb.handlers.marking_menu.show("wheel_rig")
        elif text == "Shadow Rig":
            self.sb.handlers.marking_menu.show("shadow_rig")
        elif text == "Telescope Rig":
            self.sb.handlers.marking_menu.show("telescope_rig")

    def chk000(self, state, widget):
        """Scale Joint"""
        # init global joint display size
        widget.ui.tb000.option_box.menu.s000.setValue(cmds.jointDisplayScale(q=True))

    def chk001(self, state, widget):
        """Scale IK"""
        # init IK handle display size
        widget.ui.tb000.option_box.menu.s000.setValue(cmds.ikHandleDisplayScale(q=True))

    def chk002(self, state, widget):
        """Scale IK/FK"""
        # init IKFK display size
        widget.ui.tb000.option_box.menu.s000.setValue(
            cmds.jointDisplayScale(q=True, ikfk=1)
        )

    def s000(self, value, widget):
        """Scale Joint/IK/FK"""
        if widget.ui.tb000.option_box.menu.chk000.isChecked():
            cmds.jointDisplayScale(value)  # set global joint display size
        elif widget.ui.tb000.option_box.menu.chk001.isChecked():
            cmds.ikHandleDisplayScale(value)  # set global IK handle display size
        else:  # widget.ui.chk002.isChecked():
            cmds.jointDisplayScale(value, ikfk=1)  # set global IKFK display size

    def tb000_init(self, widget):
        """Init Display Local Rotation Axes"""
        scale_joint_value = cmds.jointDisplayScale(q=True)
        widget.option_box.menu.setTitle("Display Local Rotation Axes")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.5, 2],
            setValue=scale_joint_value,
            setToolTip="Global display scale for the selected type.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Joints",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Display Joints.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="IK",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Display IK.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="IK\\FK",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Display IK\\FK.",
        )

    def tb000(self, widget):
        """Toggle Display Local Rotation Axes"""
        joints = cmds.ls(type="joint") or []  # get all scene joints

        if not joints:  # if no joints in the scene
            self.sb.message_box("No joints found in the scene.")
            return  # exit the function

        state = cmds.toggle(joints[0], q=True, localAxis=1)
        toggle = widget.option_box.menu.chk000.isChecked()

        if toggle:
            try:
                cmds.toggle(joints, localAxis=1)  # set display off
            except Exception as e:
                print(f"An error occurred while toggling local axes: {e}")

        self.sb.message_box(f"Display Local Rotation Axes:<hl>{state}</hl>")

    def tb001_init(self, widget):
        """Init Constraint Switch"""
        widget.option_box.menu.setTitle("Create Constraint Switch")
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Switch Name:",
            setText="switch",
            setObjectName="t003",
            setToolTip="The name of the switch attribute to create on the constrained object.",
        )
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Anchor Name:",
            setText="",
            setObjectName="t004",
            setToolTip="Optional: Create a locator at world origin as an additional constraint target.\nLeave blank to use only existing constraint targets.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Weighted",
            setObjectName="chk003",
            setChecked=False,
            setToolTip="For 2-target constraints: Enable smooth blending (float 0-1) instead of snap switching (enum).\nHas no effect on 1-target or 3+ target constraints.",
        )

    def tb001(self, widget):
        """Constraint Switch"""
        sel = cmds.ls(sl=True, flatten=True) or []
        if not sel:
            self.sb.message_box(
                "Nothing selected.<br>Select a <hl>constraint</hl> node."
            )
            return
        if not cmds.objectType(sel[0], isAType="constraint"):
            self.sb.message_box(
                f"<hl>{mtk.short_name(sel[0])}</hl> is not a constraint node."
                "<br>Select a <hl>constraint</hl> "
                "(parent, point, orient, scale, or aim)."
            )
            return

        switch_name = widget.option_box.menu.t003.text()
        weighted = widget.option_box.menu.chk003.isChecked()
        anchor_name = widget.option_box.menu.t004.text()

        result = mtk.connect_switch_to_constraint(
            constraint_node=sel[0],
            attr_name=switch_name,
            weighted=weighted,
            overwrite_existing=True,
            anchor=anchor_name,
        )
        # ``switch_attr`` is the authoritative success signal — set on every
        # success path and on none of the early-return failure paths (no
        # targets / unresolved driven node / weight mismatch). The function
        # warns the specifics to the console; point the user there.
        if not result.get("switch_attr"):
            self.sb.message_box(
                f"Could not create a constraint switch on "
                f"<hl>{mtk.short_name(sel[0])}</hl>.<br>"
                "See the script editor for details."
            )

    # ------------------------------------------------------------------
    # tb003 — Create Locator at Selection
    # ------------------------------------------------------------------

    def tb003_init(self, widget):
        """Init Create Locator at Selection"""
        widget.option_box.menu.setTitle("Create Locator")
        # Section: Scale
        widget.option_box.menu.add("Separator", setTitle="Scale")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Locator Scale: ",
            setObjectName="s001",
            set_limits=[0, 1000, 1, 3],
            setValue=1,
            setToolTip="The scale of the locator.",
        )
        # Section: Naming
        widget.option_box.menu.add("Separator", setTitle="Naming")
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Group Suffix:",
            setText="_GRP",
            setObjectName="t002",
            setToolTip="A string appended to the end of the created group's name.",
        )
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Locator Suffix:",
            setText="_LOC",
            setObjectName="t000",
            setToolTip="A string appended to the end of the created locator's name.",
        )
        widget.option_box.menu.add(
            "QLineEdit",
            setPlaceholderText="Geometry Suffix:",
            setText="_GEO",
            setObjectName="t001",
            setToolTip="A string appended to the end of the existing geometry's name.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Strip Digits",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Strip any trailing numeric characters from the name.\nIf the resulting name is not unique, maya will append a trailing digit.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Strip Suffix",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Strip any of the defined suffixes (Group, Locator, Geometry) from the name when enabled.",
        )
        # Section: Lock Channels
        widget.option_box.menu.add("Separator", setTitle="Lock Channels")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lock Child Translate",
            setObjectName="chk007",
            setChecked=False,
            setToolTip="Lock the translate values of the child object.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lock Child Rotation",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Lock the rotation values of the child object.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lock Child Scale",
            setObjectName="chk009",
            setToolTip="Lock the scale values of the child object.",
        )

    @mtk.undoable
    def tb003(self, widget):
        """Create Locator at Selection"""
        grp_suffix = widget.option_box.menu.t002.text()
        loc_suffix = widget.option_box.menu.t000.text()
        obj_suffix = widget.option_box.menu.t001.text()
        loc_scale = widget.option_box.menu.s001.value()
        strip_digits = widget.option_box.menu.chk005.isChecked()
        strip_suffix = widget.option_box.menu.chk006.isChecked()
        lock_translate = widget.option_box.menu.chk007.isChecked()
        lock_rotation = widget.option_box.menu.chk008.isChecked()
        lock_scale = widget.option_box.menu.chk009.isChecked()

        selection = cmds.ls(sl=True) or []
        if not selection:
            return mtk.create_locator(scale=loc_scale)

        try:
            mtk.create_locator_at_object(
                selection,
                loc_scale=loc_scale,
                grp_suffix=grp_suffix,
                loc_suffix=loc_suffix,
                obj_suffix=obj_suffix,
                strip_digits=strip_digits,
                strip_suffix=strip_suffix,
                lock_translate=lock_translate,
                lock_rotation=lock_rotation,
                lock_scale=lock_scale,
            )
        except Exception as e:
            self.sb.message_box(
                f"Could not create the locator rig.<br><hl>{e}</hl>"
            )

    def b003(self):
        """Remove Locator"""
        selection = cmds.ls(selection=True) or []
        mtk.remove_locator(selection)

    # ------------------------------------------------------------------
    # tb004 — Lock / Unlock Attributes
    # ------------------------------------------------------------------

    def tb004_init(self, widget):
        """Init Lock/Unlock Attributes"""
        widget.option_box.menu.setTitle("Lock / Unlock Attributes")
        # Lock vs Unlock is a two-valued choice, not a modifier — a combobox names
        # both states (its item text drives the button label). Extend with e.g.
        # "Toggle" here without touching the layout.
        action = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_lock",
            setToolTip="Whether the button locks or unlocks the chosen attributes.",
        )
        action.addItems(["Lock", "Unlock"])
        action.setCurrentText("Unlock")  # preserve prior default (checkbox off = unlock)
        action.currentTextChanged.connect(widget.setText)
        widget.setText(action.currentText())
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb010",
            setToolTip="Which attributes to affect.\n"
            "Auto: prefer channel-box selection, fall back to all transform attrs.\n"
            "Channel Box: only attributes currently selected in the channel box.\n"
            "All: all standard transform attributes (translate, rotate, scale).",
        )
        for text, data in [
            ("Attrs: Auto", "auto"),
            ("Attrs: Channel Box", "channel_box"),
            ("Attrs: All", "all"),
        ]:
            cmb.addItem(text, data)

    @mtk.undoable
    def tb004(self, widget):
        """Lock/Unlock Attributes"""
        lock = widget.option_box.menu.cmb_lock.currentText() == "Lock"
        mode = widget.option_box.menu.cmb010.currentData()

        selection = cmds.ls(selection=True, type="transform")
        if not selection:
            self.sb.message_box("Nothing selected.")
            return

        all_attrs = ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz")

        if mode == "channel_box":
            attrs = mtk.Attributes.get_selected_channels()
            if not attrs:
                self.sb.message_box("No attributes selected in the channel box.")
                return
        elif mode == "all":
            attrs = all_attrs
        else:  # auto
            attrs = mtk.Attributes.get_selected_channels() or all_attrs

        for node in selection:
            for attr in attrs:
                try:
                    cmds.setAttr(f"{node}.{attr}", lock=lock)
                except Exception:
                    pass

        action = "Locked" if lock else "Unlocked"
        self.sb.message_box(
            f"{action} <hl>{len(attrs)}</hl> attr(s) on "
            f"<hl>{len(selection)}</hl> object(s)."
        )

    def b004(self):
        """Render Opacity"""
        self.sb.handlers.marking_menu.show("render_opacity")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
