# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
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
            pm.mel.SnapPointToPointOptions()  # performSnapPtToPt 1; Select any type of point object or component.
        elif text == "2 Points to 2 Points":
            pm.mel.Snap2PointsTo2PointsOptions()  # performSnap2PtTo2Pt 1; Select any type of point object or component.
        elif text == "3 Points to 3 Points":
            pm.mel.Snap3PointsTo3PointsOptions()  # performSnap3PtTo3Pt 1; Select any type of point object or component.
        elif text == "Align Objects":
            pm.mel.performAlignObjects(1)  # Align the selected objects.
        elif text == "Position Along Curve":
            pm.mel.PositionAlongCurve()  # Position selected objects along a selected curve.
        elif text == "Align Tool":
            pm.mel.SetAlignTool()  # setToolTo alignToolCtx; Align the selection to the last selected object.
        elif text == "Snap Together Tool":
            pm.mel.SetSnapTogetherToolOptions()  # setToolTo snapTogetherToolCtx; toolPropertyWindow;) Snap two objects together.

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

        objects = pm.ls(sl=1, objectsOnly=1)
        mtk.drop_to_grid(objects, align, origin, center_pivot, freeze_transforms)
        pm.select(objects)  # reselect the original selection.

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
        objects = pm.selected()
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
        strategy_index = widget.option_box.menu.cmb_connection_strategy.currentIndex()
        connection_strategy = ["preserve", "disconnect", "delete"][strategy_index]

        # Store transforms before freezing so they can be restored later
        if store_transforms:
            mtk.store_transforms(objects, accumulate=True)

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

    def tb003_init(self, widget):
        """Constraints Init"""
        widget.option_box.menu.trigger_button = "left"
        widget.option_box.menu.add_apply_button = False
        widget.option_box.menu.setTitle("CONSTRAINTS")
        edge_constraint = pm.xformConstraint(q=True, type=1) == "edge"
        surface_constraint = pm.xformConstraint(q=True, type=1) == "surface"
        values = [
            ("chk024", "Contrain: Edge", edge_constraint),
            ("chk025", "Constain: Surface", surface_constraint),
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
            pm.manipMoveContext("Move", q=True, snapValue=True)
        )
        widget.option_box.menu.s022.setValue(
            pm.manipScaleContext("Scale", q=True, snapValue=True)
        )
        widget.option_box.menu.s023.setValue(
            pm.manipRotateContext("Rotate", q=1, snapValue=True)
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

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Move All To Last",
            setObjectName="chk036",
            setChecked=True,
            setToolTip="If checked, all selected objects will move to align with the last selected object.\nIf unchecked, the first object will move to the remaining selected objects' bounding box.",
        )

    @mtk.undoable
    def tb005(self, widget):
        """Move To"""
        move_all_to_last = widget.option_box.menu.chk036.isChecked()

        sel = pm.ls(orderedSelection=True, transforms=True)
        if not len(sel) > 1:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least two selected objects."
            )
            return

        # Move all to last selected object's position
        if move_all_to_last:
            source = sel[:-1]
            target = sel[-1]
            mtk.move_to(source, target)
            pm.select(source)
        else:  # Move first object to remaining selected objects' bounding box or pivot point
            source = sel[0]
            target = sel[1:]
            mtk.move_to(source, target)
            pm.select(source)

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
            pm.xformConstraint(type="edge")
        else:
            pm.xformConstraint(type="none")

    def chk025(self, state, widget):
        """Transform Contraints: Surface"""
        tb = self.ui.tb003
        tb.init_slot()
        if state:
            pm.xformConstraint(type="surface")
        else:
            pm.xformConstraint(type="none")

    def chk026(self, state, widget):
        """Transform Constraints: Make Live"""
        tb = self.ui.tb003
        tb.init_slot()

        selection = pm.ls(sl=1, objectsOnly=1, type="transform")
        if state and selection:
            pm.makeLive(selection[0])
        else:
            pm.makeLive(none=True)

    def s021(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipMoveContext("Move", edit=1, snapValue=value)
        # UV move context
        pm.texMoveContext("texMoveContext", edit=1, snapValue=value)

    def s022(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipScaleContext("Scale", edit=1, snapValue=value)
        # UV scale context
        pm.texScaleContext("texScaleContext", edit=1, snapValue=value)

    def s023(self, value, widget):
        """Transform Tool Snap Settings: Spinboxes"""
        pm.manipRotateContext("Rotate", edit=1, snapValue=value)
        # UV rotate context
        pm.texRotateContext("texRotateContext", edit=1, snapValue=value)

    def b_snap_ts(self):
        """Snap Toolset"""
        self.sb.handlers.marking_menu.show("snap")

    def b001(self):
        """Match Scale"""
        selection = pm.ls(orderedSelection=True, flatten=True)
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
        mtk.restore_transforms(pm.selected())

    def setTransformSnap(self, ctx, state):
        """Set the transform tool's move, rotate, and scale snap states.

        Parameters:
                ctx (str): valid: 'move', 'scale', 'rotate'
                state (int): valid: 0=off, 1=relative, 2=absolute
        """
        if ctx == "move":
            pm.manipMoveContext(
                "Move",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            pm.texMoveContext(
                "texMoveContext", edit=1, snap=False if state == 0 else True
            )  # uv move context

        elif ctx == "scale":
            pm.manipScaleContext(
                "Scale",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            pm.texScaleContext(
                "texScaleContext", edit=1, snap=False if state == 0 else True
            )  # uv scale context

        elif ctx == "rotate":
            pm.manipRotateContext(
                "Rotate",
                edit=1,
                snap=False if state == 0 else True,
                snapRelative=True if state == 1 else False,
            )  # state: 0=off, 1=relative, 2=absolute
            pm.texRotateContext(
                "texRotateContext", edit=1, snap=False if state == 0 else True
            )  # uv rotate context


# --------------------------------------------------------------------------------------------


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
