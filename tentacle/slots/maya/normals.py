# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


class Normals(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb001_init(self, widget):
        """Initialize Set Normals By Angle"""
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Angle Threshold: ",
            setObjectName="s002",
            set_limits=[0, 180],
            setValue=90,
            setToolTip="The threshold of the normal angle in degrees to determine hardness.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Upper Hardness: ",
            setObjectName="s003",
            set_limits=[-1, 180],
            setValue=0,
            setToolTip="The hardness to apply to edges with a normal angle greater than or equal to the threshold.\n0, Edges will appear hard.\n180, Edges will appear soft.\n-1, Will Disable.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Lower Hardness: ",
            setObjectName="s004",
            set_limits=[-1, 180],
            setValue=180,
            setToolTip="The hardness to apply to edges with a normal angle less than the threshold.\n0, Edges will appear hard.\n180, Edges will appear soft.\n-1, Will Disable.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Unlock Normals First",
            setObjectName="chk_unlock_normals",
            setChecked=True,
            setToolTip="Unlock vertex normals before applying hardness.\nRequired for imported assets (FBX/Marmoset) — locked normals\nsilently block the smoothing update.",
        )

    def tb001(self, widget):
        """Set Normals By Angle"""
        angle_threshold = widget.option_box.menu.s002.value()
        upper_hardness = widget.option_box.menu.s003.value()
        lower_hardness = widget.option_box.menu.s004.value()
        unlock_normals = widget.option_box.menu.chk_unlock_normals.isChecked()

        # If value is -1, upper/lower hardess will be disabled.
        upper_hardness = upper_hardness if upper_hardness > -1 else None
        lower_hardness = lower_hardness if lower_hardness > -1 else None

        selection = cmds.ls(sl=True) or []
        mtk.Components.set_edge_hardness(
            selection,
            angle_threshold,
            upper_hardness,
            lower_hardness,
            unlock_normals=unlock_normals,
        )

        objects = cmds.ls(selection, objectsOnly=True) or []
        if objects:
            cmds.polyOptions(objects, se=True)  # Soft edge display.

    def tb004_init(self, widget):
        """Initialize Average Normals"""
        widget.option_box.menu.add(
            "QCheckBox",
            setText="By UV Shell",
            setObjectName="chk003",
            setToolTip="Average the normals of each object's faces per UV shell.",
        )

    def tb004(self, widget):
        """Average Normals"""
        by_uv_shell = widget.option_box.menu.chk003.isChecked()

        objects = cmds.ls(sl=True) or []
        mtk.Components.average_normals(objects, by_uv_shell=by_uv_shell)

    def _set_edge_hardness(self, angle):
        """Set edge normal hardness on the selection, then refresh soft-edge display.

        Parameters:
            angle (int): polySoftEdge angle — 180 fully softens, 0 fully hardens.
        """
        selection = cmds.ls(sl=True) or []
        # Map components to their respective objects. The dict key is a leaf
        # name that can collide across the scene, so resolve the unambiguous
        # object path from the path-qualified components instead.
        components_dict = mtk.Components.map_components_to_objects(selection)
        for components in components_dict.values():
            cmds.polySoftEdge(components, angle=angle)
            objects = cmds.ls(components, objectsOnly=True, long=True) or []
            if objects:
                cmds.polyOptions(objects, se=True)  # Set soft edge display.
        if selection:
            cmds.select(selection)  # Re-select the original selection

    def b000(self):
        """Soften Edge Normals"""
        self._set_edge_hardness(180)  # Maximum angle to soften.

    def b001(self):
        """Harden all selected edges."""
        self._set_edge_hardness(0)  # Minimum angle to harden.

    def b002(self):
        """Transfer Normals"""
        sel = cmds.ls(sl=1, fl=True) or []
        if len(sel) < 2:
            self.sb.message_box(
                "Select a source object and one or more target objects."
            )
            return
        source, *target = sel

        mtk.Components.transfer_normals([source] + target)

    def b004(self):
        """Toggle lock/unlock vertex normals."""
        mtk.Macros.m_lock_vertex_normals()

    def b006(self):
        """Set To Face"""
        cmds.polySetToFaceNormal()

    def tb010_init(self, widget):
        """Initialize Reverse Normals"""
        if not widget.is_initialized:
            widget.option_box.menu.setTitle("Reverse Normals")
            widget.option_box.menu.add(
                "QComboBox",
                setObjectName="cmb000",
                addItems=[
                    "Reverse",
                    "Propagate",
                    "Conform",
                    "Reverse and Extract",
                    "Reverse and Propagate",
                ],
                setCurrentIndex=3,
                setToolTip="Normal operation mode.",
            )

    def tb010(self, widget):
        """Reverse Normals"""
        mode = widget.option_box.menu.cmb000.currentIndex()

        for obj in cmds.ls(sl=1, objectsOnly=1) or []:
            sel = cmds.ls(obj, sl=1) or []
            # normalMode 0: Reverse
            # normalMode 1: Propagate
            # normalMode 2: Conform
            # normalMode 3: Reverse and Extract
            # normalMode 4: Reverse and Propagate
            if sel:
                cmds.polyNormal(sel, normalMode=mode, userNormalMode=1)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
