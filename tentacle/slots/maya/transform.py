# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


class TransformSlots(SlotsMaya):
    """ """

    def __init__(self, *args, **kwargs):
        """ """
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.transform
        self.submenu = self.sb.loaded_ui.transform_submenu

    def header_init(self, widget):
        """Header Init"""
        widget.menu.add(
            "QPushButton",
            setText="Fix Non-Orthogonal Axes",
            setObjectName="fix_non_ortho_axes",
            setToolTip="Fix non-orthogonal axes (shear) on selected objects.",
            clicked=lambda: mtk.Diagnostics.fix_non_orthogonal_axes(),
        )
        widget.menu.add(
            "QPushButton",
            setText="Snap",
            setObjectName="b_snap_ts",
            setToolTip="Open the snap toolset.",
        )

    def cmb002_init(self, widget):
        """Align To Init"""
        items = [
            "Point to Point",
            "2 Points to 2 Points",
            "3 Points to 3 Points",
            "Align Objects",
            "Position Along Curve",
            "Align Tool",
            "Snap Together Tool",
        ]
        widget.add(items, header="Align To")

    def cmb002(self, index, widget):
        """Align To"""
        text = widget.items[index]
        if text == "Point to Point":
            mel.eval("SnapPointToPointOptions")
        elif text == "2 Points to 2 Points":
            mel.eval("Snap2PointsTo2PointsOptions")
        elif text == "3 Points to 3 Points":
            mel.eval("Snap3PointsTo3PointsOptions")
        elif text == "Align Objects":
            mel.eval("performAlignObjects 1")
        elif text == "Position Along Curve":
            mel.eval("PositionAlongCurve")
        elif text == "Align Tool":
            mel.eval("SetAlignTool")
        elif text == "Snap Together Tool":
            mel.eval("SetSnapTogetherToolOptions")

    def tb000_init(self, widget):
        """Drop To Grid Init"""
        widget.option_box.menu.add(
            "QComboBox",
            addItems=["Min", "Mid", "Max"],
            setObjectName="cmb004",
            setToolTip="Choose which point of the bounding box to align to.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Move to Origin",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Move to origin (xyz 0,0,0).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Center pivot on objects bounding box.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Reset the selected transform and all of its children down to the shape level.",
        )

    def tb000(self, widget):
        """Drop To Grid"""
        align = widget.option_box.menu.cmb004.currentText()
        origin = widget.option_box.menu.chk014.isChecked()
        center_pivot = widget.option_box.menu.chk016.isChecked()
        freeze_transforms = widget.option_box.menu.chk017.isChecked()

        objects = cmds.ls(sl=1, objectsOnly=1) or []
        mtk.drop_to_grid(objects, align, origin, center_pivot, freeze_transforms)
        if objects:
            cmds.select(objects)  # reselect the original selection.

    def tb001_init(self, widget):
        """Scale Connected Edges Init"""
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="s001",
            setPrefix="Scale Factor:",
            setValue=1.1,
            set_limits=[-999, 999, 0.1],
            setToolTip="Scale factor to apply to scaling by as a percentage.",
        )

    def tb001(self, widget):
        """Scale Connected Edges"""
        factor = widget.option_box.menu.s001.value()
        mtk.scale_connected_edges(scale_factor=factor)

    def tb002_init(self, widget):
        """Freeze Transformations Init"""
        widget.option_box.menu.setTitle("Freeze Transforms")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk032",
            setChecked=True,
            setToolTip="The translation will be changed to 0, 0, 0.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk033",
            setToolTip="The rotation will be changed to 0, 0, 0.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk034",
            setChecked=True,
            setToolTip="The scale factor will be changed to 1, 1, 1.",
        )
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_center_pivot",
            addItems=["Center Pivot: None", "Center Pivot: Mesh", "Center Pivot: All"],
            setCurrentIndex=0,
            setToolTip="Move the objects pivot to the center of its bounding box.\n• None: Don't center pivot\n• Mesh: Center pivot on mesh objects only\n• All: Center pivot on all objects",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Freeze Children",
            setObjectName="chk039",
            setToolTip="Freeze all descendant transform nodes.",
        )
        widget.option_box.menu.add(
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
        widget.option_box.menu.add(
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
        widget.option_box.menu.add(
            "QCheckBox",
            setText="From Channel Box",
            setObjectName="chk040",
            setChecked=False,
            setToolTip="Use the selected attributes in the channel box to determine what to freeze.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Store Transforms",
            setObjectName="chk037",
            setChecked=True,
            setToolTip="Store the original transforms as custom attributes.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete History",
            setObjectName="chk038",
            setChecked=True,
            setToolTip="Delete the objects history.",
        )

        self.sb.toggle_multi(
            widget.option_box.menu,
            trigger="chk040",
            on_True={"setDisabled": "chk032-34"},
            on_False={"setEnabled": "chk032-34"},
        )

    def tb002(self, widget):
        """Freeze Transformations"""
        objects = cmds.ls(sl=True) or []
        if not objects:
            self.sb.message_box("Please select at least one object.")
            return

        center_pivot = (
            widget.option_box.menu.cmb_center_pivot.currentIndex()
        )  # 0=None, 1=Mesh, 2=All
        translate = widget.option_box.menu.chk032.isChecked()
        rotate = widget.option_box.menu.chk033.isChecked()
        scale = widget.option_box.menu.chk034.isChecked()
        force = True if len(objects) == 1 else False
        store_transforms = widget.option_box.menu.chk037.isChecked()
        delete_history = widget.option_box.menu.chk038.isChecked()
        freeze_children = widget.option_box.menu.chk039.isChecked()
        from_channel_box = widget.option_box.menu.chk040.isChecked()
        restore_rig_anchors = (
            widget.option_box.menu.chk_restore_rig_anchors.isChecked()
        )
        strategy_index = widget.option_box.menu.cmb_connection_strategy.currentIndex()
        connection_strategy = ["preserve", "disconnect", "delete"][strategy_index]

        # Store transforms before freezing so they can be restored later.
        # When freezing children the cascade reaches descendants, so traverse
        # the same set or unfreeze on a child will warn about missing attrs.
        if store_transforms:
            mtk.store_transforms(objects, accumulate=True, traverse=freeze_children)

        mtk.freeze_transforms(
            objects,
            center_pivot=center_pivot,
            t=translate,
            r=rotate,
            s=scale,
            force=force,
            delete_history=delete_history,
            freeze_children=freeze_children,
            connection_strategy=connection_strategy,
            from_channel_box=from_channel_box,
        )

        if restore_rig_anchors:
            mtk.restore_rig_anchors(objects, traverse=True)

    def tb003_init(self, widget):
        """Constraints Init"""
        widget.option_box.menu.trigger_button = "left"
        widget.option_box.menu.add_apply_button = False
        widget.option_box.menu.setTitle("CONSTRAINTS")
        edge_constraint = cmds.xformConstraint(q=True, type=1) == "edge"
        surface_constraint = cmds.xformConstraint(q=True, type=1) == "surface"
        values = [
            ("chk024", "Constrain: Edge", edge_constraint),
            ("chk025", "Constrain: Surface", surface_constraint),
            ("chk026", "Make Live", True),
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

        # Connecting signals to update_text method
        self.sb.connect_multi(widget.menu, "chk024-26", "toggled", update_text)

    def tb004_init(self, widget):
        """Snap Init"""
        widget.option_box.menu.trigger_button = "left"
        widget.option_box.menu.add_apply_button = False
        widget.option_box.menu.setTitle("SNAP")
        widget.option_box.menu.add(
            self.sb.registered_widgets.CheckBox,
            setObjectName="chk021",
            setText="Snap Move",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="s021",
            setPrefix="Increment:",
            setValue=0,
            set_limits=[1, 1000, 1, 1],
            setDisabled=True,
        )
        widget.option_box.menu.add(
            self.sb.registered_widgets.CheckBox,
            setObjectName="chk022",
            setText="Snap Scale",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="s022",
            setPrefix="Increment:",
            setValue=0,
            set_limits=[1, 1000, 1, 1],
            setDisabled=True,
        )
        widget.option_box.menu.add(
            self.sb.registered_widgets.CheckBox,
            setObjectName="chk023",
            setText="Snap Rotate",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="s023",
            setPrefix="Degrees:",
            setValue=0,
            set_limits=[1.40625, 360, 0.40625, 5],
            setDisabled=True,
        )
        # Set the values
        widget.option_box.menu.s021.setValue(
            cmds.manipMoveContext("Move", q=True, snapValue=True)
        )
        widget.option_box.menu.s022.setValue(
            cmds.manipScaleContext("Scale", q=True, snapValue=True)
        )
        widget.option_box.menu.s023.setValue(
            cmds.manipRotateContext("Rotate", q=1, snapValue=True)
        )

        def update_text():
            state = any(
                w.isChecked() for w in widget.option_box.menu.get_items("CheckBox")
            )
            widget.setText("Snap: ON" if state else "Snap: OFF")

        # Connecting signals to update_text method
        self.sb.connect_multi(widget.menu, "chk021-23", "toggled", update_text)

    def tb005_init(self, widget):
        """Move To Init"""
        widget.option_box.menu.setTitle("MOVE TO")

        # Pivot combobox — driven by the mayatk pivot helper (like the Mirror /
        # Duplicate panels) so it stays in sync. currentData() yields the raw
        # pivot key ('manip', 'object', 'center', 'xmax', ...).
        cmb = widget.option_box.menu.add(
            self.sb.registered_widgets.ComboBox,
            setObjectName="cmb005",
            setToolTip="Which point of the target to align the source object(s) to.\n"
            "Manip / Object pivot, or any bounding-box location (center + extents).",
        )
        # Exclude pivots that aren't meaningful for a translate-only "move to
        # target" op, leaving manip / object / bounding-box locations:
        #   'baked'  — differs from 'object' only by orientation, which move_to
        #              ignores, so it resolves to the same point as 'object'.
        #   'world'  — the origin, ignoring the target entirely (use Drop To Grid).
        skip = {"baked", "world"}
        pivot_options = [
            p for p in mtk.XformUtils.get_pivot_options() if p not in skip
        ]
        cmb.add(pivot_options, prefix="Pivot:")
        cmb.setAsCurrent("center")  # historical default (target bounding-box center)

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Move All To Last",
            setObjectName="chk036",
            setChecked=True,
            setToolTip="If checked, all selected objects will move to align with the last selected object.\nIf unchecked, the first object will move to the remaining selected objects' bounding box.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Match Scale",
            setObjectName="chk_match_scale",
            setChecked=False,
            setToolTip="Also uniformly rescale the moved object(s) to match the target's bounding-box size (no per-axis distortion).",
        )

    @mtk.undoable
    def tb005(self, widget):
        """Move To"""
        pivot = widget.option_box.menu.cmb005.currentData() or "center"
        move_all_to_last = widget.option_box.menu.chk036.isChecked()
        do_match_scale = widget.option_box.menu.chk_match_scale.isChecked()

        sel = cmds.ls(orderedSelection=True, transforms=True) or []
        if not len(sel) > 1:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least two selected objects."
            )
            return

        if move_all_to_last:  # all but the last move to the last object
            source, target = sel[:-1], sel[-1]
        else:  # the first object moves to the remaining objects' combined bounding box
            source, target = sel[0], sel[1:]

        if do_match_scale:  # uniformly resize source to the target's bounding-box size
            mtk.match_scale(source, target, average=True)
        mtk.move_to(source, target, pivot=pivot)
        cmds.select(source)

    def chk021(self, state, widget):
        """Transform Tool Snap Settings: Move"""
        tb = self.ui.tb004
        tb.init_slot()
        tb.option_box.menu.s021.setEnabled(
            state
        )  # Enable/Disable based on the checked state
        self.setTransformSnap("move", state)

    def chk022(self, state, widget):
        """Transform Tool Snap Settings: Scale"""
        tb = self.ui.tb004
        tb.init_slot()
        tb.option_box.menu.s022.setEnabled(
            state
        )  # Enable/Disable based on the checked state
        self.setTransformSnap("scale", state)

    def chk023(self, state, widget):
        """Transform Tool Snap Settings: Rotate"""
        tb = self.ui.tb004
        tb.init_slot()
        tb.option_box.menu.s023.setEnabled(
            state
        )  # Enable/Disable based on the checked state
        self.setTransformSnap("rotate", state)

    def chk024(self, state, widget):
        """Transform Constraints: Edge"""
        tb = self.ui.tb003
        tb.init_slot()
        if state:
            cmds.xformConstraint(type="edge")
        else:
            cmds.xformConstraint(type="none")

    def chk025(self, state, widget):
        """Transform Contraints: Surface"""
        tb = self.ui.tb003
        tb.init_slot()
        if state:
            cmds.xformConstraint(type="surface")
        else:
            cmds.xformConstraint(type="none")

    def chk026(self, state, widget):
        """Transform Constraints: Make Live"""
        tb = self.ui.tb003
        tb.init_slot()

        selection = cmds.ls(sl=1, objectsOnly=1, type="transform") or []
        if state and selection:
            cmds.makeLive(selection[0])
        else:
            cmds.makeLive(none=True)

    def s021(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        cmds.manipMoveContext("Move", edit=1, snapValue=value)
        # UV move context
        cmds.texMoveContext("texMoveContext", edit=1, snapValue=value)

    def s022(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        cmds.manipScaleContext("Scale", edit=1, snapValue=value)
        # UV scale context
        cmds.texScaleContext("texScaleContext", edit=1, snapValue=value)

    def s023(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        cmds.manipRotateContext("Rotate", edit=1, snapValue=value)
        # UV rotate context
        cmds.texRotateContext("texRotateContext", edit=1, snapValue=value)

    def b_snap_ts(self):
        """Snap Toolset"""
        self.sb.handlers.marking_menu.show("snap")

    def b001(self):
        """Match Scale"""
        selection = cmds.ls(orderedSelection=True, flatten=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least two selected objects."
            )
            return

        frm = selection[0]
        to = selection[1:]

        mtk.match_scale(frm, to)

    def b002(self):
        """Un-Freeze Transforms"""
        mtk.restore_transforms(cmds.ls(sl=True) or [])

    def setTransformSnap(self, ctx, state):
        """Set the transform tool's move, rotate, and scale snap states.

        Parameters:
                ctx (str): valid: 'move', 'scale', 'rotate'
                state (int): valid: 0=off, 1=relative, 2=absolute
        """
        if ctx == "move":
            cmds.manipMoveContext(
                "Move",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            cmds.texMoveContext(
                "texMoveContext", edit=1, snap=False if state == 0 else True
            )  # uv move context

        elif ctx == "scale":
            cmds.manipScaleContext(
                "Scale",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            cmds.texScaleContext(
                "texScaleContext", edit=1, snap=False if state == 0 else True
            )  # uv scale context

        elif ctx == "rotate":
            cmds.manipRotateContext(
                "Rotate",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            cmds.texRotateContext(
                "texRotateContext", edit=1, snap=False if state == 0 else True
            )  # uv rotate context


# --------------------------------------------------------------------------------------------


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
