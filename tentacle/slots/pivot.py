# !/usr/bin/python
# coding=utf-8
"""Pivot: one Slots class for both hosts.

Every operation is the host toolkit's ``XformUtils`` (``self.tk``), given ``None``
for the selection; each is one undo step in its host, and with nothing selected
returns ``[]`` without running. Maya edits its pivots: each object's rotate and
scale pivots, and the temporary manipulator pivot. Blender has one object
origin, always baked, and its temporary pivot is the 3D cursor; so Reset Pivot's
orientation and Transfer Pivot's channel, bake and space options are Maya's
(tagged ``requires="maya"``, hidden in Blender).
"""

from tentacle import Slots


class PivotSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.pivot
        self.submenu = self.sb.loaded_ui.pivot_submenu

    # ------------------------------------------------------------------ tb000  Reset Pivot
    def tb000_init(self, widget):
        """Initialize Reset Pivot."""
        menu = widget.option_box.menu
        menu.setTitle("Reset Pivot")
        menu.add(
            "QCheckBox",
            setText="Reset Pivot Position",
            setObjectName="chk000",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Reset Pivot Position",
                body="Move the pivot back to its default.",
                notes=[
                    "Maya: the manipulator pivot returns to the object's own pivot, "
                    "discarding any temporary offset (<code>manipPivotReset</code>).",
                    "Blender: the origin returns to the geometry's bounding-box center.",
                ],
            ),
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Reset Pivot Orientation",
                setObjectName="chk001",
                setChecked=True,
                setToolTip=self.sb.tooltip.fmt(
                    title="Reset Pivot Orientation",
                    body="Return the manipulator to the object's own orientation, "
                    "discarding any temporary re-orientation "
                    "(<code>manipPivotReset</code>).",
                ),
            ),
            "maya",
        )

    def tb000(self, widget):
        """Reset Pivot: the selection's pivot position and/or orientation."""
        menu = widget.option_box.menu
        reset = self.tk.XformUtils.reset_pivot(
            None,
            position=menu.chk000.isChecked(),
            orientation=menu.chk001.isChecked(),
        )
        if reset == []:
            self.sb.message_box(self.NOTHING_SELECTED)
            return
        self.sb.message_box(f"Pivot reset on <hl>{len(reset)}</hl> object(s).")

    # ------------------------------------------------------------------ tb001  Center Pivot
    def tb001_init(self, widget):
        """Initialize Center Pivot."""
        menu = widget.option_box.menu
        menu.setTitle("Center Pivot")
        menu.add(
            "QRadioButton",
            setText="Component",
            setObjectName="chk002",
            setToolTip="Center the pivot on the selected components' bounding-box "
            "center (Blender: the geometry's median).",
        )
        menu.add(
            "QRadioButton",
            setText="Object",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Center the pivot on the object's bounding-box center.",
        )
        menu.add(
            "QRadioButton",
            setText="World",
            setObjectName="chk004",
            setToolTip="Move the pivot to the world origin (0, 0, 0).",
        )

    def tb001(self, widget):
        """Center Pivot"""
        menu = widget.option_box.menu
        if menu.chk002.isChecked():
            mode = "component"
        elif menu.chk004.isChecked():
            mode = "world"
        else:
            mode = "object"
        if self.tk.XformUtils.center_pivot(None, mode=mode) == []:
            self.sb.message_box("Center Pivot requires a selection.")

    def b000(self):
        """Center Pivot: Object"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk003.setChecked(True)
        self.ui.tb001.call_slot()

    def b001(self):
        """Center Pivot: Component"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk002.setChecked(True)
        self.ui.tb001.call_slot()

    def b002(self, widget):
        """Center Pivot: World"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk004.setChecked(True)
        self.ui.tb001.call_slot()

    # ------------------------------------------------------------------ tb002  Transfer Pivot
    def tb002_init(self, widget):
        """Initialize Transfer Pivot. Only the Mirror axis serves Blender, whose single
        origin is always baked and read in world space: the transfer IS its
        translate channel."""
        menu = widget.option_box.menu
        menu.setTitle("Transfer Pivot")
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Translate",
                setObjectName="chk005",
                setChecked=True,
                setToolTip="Transfer the translation pivot.",
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Rotate",
                setObjectName="chk006",
                setChecked=False,
                setToolTip=self.sb.tooltip.fmt(
                    title="Rotate",
                    body="Transfer the pivot ORIENTATION as well as its position.",
                    notes=[
                        "Off by default — most transfers only want the pivot point.",
                        "The object never moves: its geometry is pinned while the "
                        "pivot re-frames.",
                    ],
                ),
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Scale",
                setObjectName="chk007",
                setChecked=True,
                setToolTip="Transfer the scale pivot.",
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Bake",
                setObjectName="chk008",
                setChecked=True,
                setToolTip=self.sb.tooltip.fmt(
                    title="Bake",
                    body="Whether the transferred pivot is <b>permanent</b> or a "
                    "temporary manipulator pivot.",
                    notes=[
                        "<b>On</b>: written into each target's own pivot attributes "
                        "— saved with the scene.",
                        "<b>Off</b>: only the manipulator is moved. Transient, "
                        "shared by all targets, and cleared by Reset Pivot.",
                    ],
                ),
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="World Space",
                setObjectName="chk009",
                setChecked=True,
                setToolTip="Whether to use world space for transformations.",
            ),
            "maya",
        )
        cmb000 = menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip=self.sb.tooltip.fmt(
                title="Mirror",
                body="Reflect the transferred pivot across the chosen world "
                "axis-plane through the origin.",
                notes=[
                    "Use it when the target is a mirrored copy of the source.",
                    "<b>None</b> transfers the pivot unreflected.",
                ],
            ),
        )
        for text, data in [
            ("Mirror: None", ""),
            ("Mirror: X", "x"),
            ("Mirror: Y", "y"),
            ("Mirror: Z", "z"),
        ]:
            cmb000.addItem(text, data)

    def tb002(self, widget):
        """Transfer Pivot: from the source (Maya: the first selected; Blender: the
        active object) to the other selected objects, which end selected."""
        menu = widget.option_box.menu
        try:
            targets = self.tk.XformUtils.transfer_pivot(
                None,
                translate=menu.chk005.isChecked(),
                rotate=menu.chk006.isChecked(),
                scale=menu.chk007.isChecked(),
                bake=menu.chk008.isChecked(),
                world_space=menu.chk009.isChecked(),
                mirror=menu.cmb000.currentData(),
                select_targets_after_transfer=True,
            )
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        if targets == []:
            self.sb.message_box(
                "Select a source object and one or more targets (the source is "
                "the first selected in Maya, the active object in Blender)."
            )

    # ------------------------------------------------------------------ tb003  World-Aligned Pivot
    def tb003_init(self, widget):
        """Initialize World-Aligned Pivot."""
        menu = widget.option_box.menu
        menu.setTitle("World-Aligned Pivot")
        menu.add(
            "QCheckBox",
            setText="Manip Pivot",
            setObjectName="chk010",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Manip Pivot",
                body="Set a temporary, world-aligned manipulator "
                "(Blender: the Global transform orientation).",
                notes=[
                    "Off: the object pivot is permanently world-aligned instead "
                    "(Blender bakes the rotation into the object's data).",
                    "Maya: works on a component selection too, the pivot landing on "
                    "the components' bounding-box center.",
                ],
            ),
        )

    def tb003(self, widget):
        """World-Aligned Pivot: the manipulator (temporary) or the object pivot
        (permanent) of the selection."""
        manip = widget.option_box.menu.chk010.isChecked()
        try:
            done = self.tk.XformUtils.world_align_pivot(
                None, pivot_type="manip" if manip else "object", mode="set"
            )
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))
            return
        if not done:
            self.sb.message_box(
                "World-Aligned Pivot requires a selection (Blender: objects with "
                "geometry data)."
            )
        elif manip:
            self.sb.message_box("World-aligned <hl>manipulator</hl> set (temporary).")
        else:
            self.sb.message_box("World-aligned <hl>object</hl> pivot set (permanent).")

    # ------------------------------------------------------------------ b004  Bake Pivot
    def b004(self):
        """Bake Pivot: make the temporary pivot (Maya: the manipulator pivot;
        Blender: the 3D cursor) the selection's own, geometry unmoved."""
        try:
            baked = self.tk.XformUtils.bake_pivot(None, position=True, orientation=True)
        except RuntimeError as error:
            self.sb.message_box(str(error))
            return
        if baked == []:
            self.sb.message_box("Bake Pivot requires a selection.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
