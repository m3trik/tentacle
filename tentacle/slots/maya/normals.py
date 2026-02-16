# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
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

    def tb001(self, widget):
        """Set Normals By Angle"""
        angle_threshold = widget.option_box.menu.s002.value()
        upper_hardness = widget.option_box.menu.s003.value()
        lower_hardness = widget.option_box.menu.s004.value()

        # If value is -1, upper/lower hardess will be disabled.
        upper_hardness = upper_hardness if upper_hardness > -1 else None
        lower_hardness = lower_hardness if lower_hardness > -1 else None

        selection = pm.ls(sl=True)
        # Reset the normals before the operation with object selections.
        if pm.selectMode(query=True, object=True):
            pm.polySetToFaceNormal(selection)

        mtk.Components.set_edge_hardness(
            selection, angle_threshold, upper_hardness, lower_hardness
        )

        objects = pm.ls(selection, objectsOnly=True)
        pm.polyOptions(objects, se=True)  # Soft edge display.

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

        objects = pm.ls(sl=True)
        mtk.Components.average_normals(objects, by_uv_shell=by_uv_shell)

    def b000(self):
        """Soften Edge Normals"""
        selection = pm.selected()
        # Map components to their respective objects
        components_dict = mtk.Components.map_components_to_objects(selection)
        # Loop through each object and its corresponding components
        for obj, components in components_dict.items():
            pm.polySoftEdge(components, angle=180)  # Use maximum angle to soften
            pm.polyOptions(obj, se=True)  # Set soft edge display.
        pm.select(selection)  # Re-select the original selection

    def b001(self):
        """Harden all selected edges."""
        selection = pm.selected()
        # Map components to their respective objects
        components_dict = mtk.Components.map_components_to_objects(selection)
        # Loop through each object and its corresponding components
        for obj, components in components_dict.items():
            pm.polySoftEdge(components, angle=0)  # Use minimum angle to harden
            pm.polyOptions(obj, se=True)  # Set soft edge display.
        pm.select(selection)  # Re-select the original selection

    def b002(self):
        """Transfer Normals"""
        source, *target = pm.ls(sl=1, fl=True)
        if not source or not target:
            self.sb.message_box(
                "Select a source object and one or more target objects."
            )
            return

        mtk.Components.transfer_normals(source, target)

    def b003(self):
        """Soft Edge Display"""
        mtk.Macros.m_soft_edge_display()

    def b004(self):
        """Toggle lock/unlock vertex normals."""
        mtk.Macros.m_lock_vertex_normals()

    def b005(self):
        """Display Face Normals"""
        mtk.Macros.m_normals_display()

    def b006(self):
        """Set To Face"""
        pm.polySetToFaceNormal()

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

        for obj in pm.ls(sl=1, objectsOnly=1):
            sel = pm.ls(obj, sl=1)
            # normalMode 0: Reverse
            # normalMode 1: Propagate
            # normalMode 2: Conform
            # normalMode 3: Reverse and Extract
            # normalMode 4: Reverse and Propagate
            pm.polyNormal(sel, normalMode=mode, userNormalMode=1)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
