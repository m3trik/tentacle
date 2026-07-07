# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.api.OpenMaya as om
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


class Duplicate(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def header_init(self, widget):
        """ """
        widget.menu.add(
            "QPushButton",
            setText="Mirror",
            setObjectName="b000",
            setToolTip="Open the mirror window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Linear",
            setObjectName="b006",
            setToolTip="Open the duplicate linear window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Radial",
            setObjectName="b007",
            setToolTip="Open the duplicate radial window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Grid",
            setObjectName="b008",
            setToolTip="Open the duplicate grid window.",
        )

    def tb002_init(self, widget):
        """Initialize Auto Instance — configure option-box menu."""
        menu = widget.option_box.menu
        menu.setTitle("Auto Instance")

        menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            setDecimals=5,
            setMinimum=0.0,
            setMaximum=10.0,
            setSingleStep=0.0001,
            setValue=0.001,
            setToolTip="Maximum average vertex deviation for two meshes to be considered identical.",
        )
        menu.add(
            "QCheckBox",
            setText="Require Same Material",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="Only match objects that share the same assigned material(s).",
        )
        menu.add(
            "QCheckBox",
            setText="Check UVs",
            setObjectName="chk005",
            setChecked=False,
            setToolTip="Additionally require matching UV layout (slower).",
        )
        chk_hierarchy = menu.add(
            "QCheckBox",
            setText="Match Whole Hierarchies",
            setObjectName="chk006",
            setChecked=False,
            setToolTip=(
                "On: compare and instance entire group/assembly hierarchies.\n"
                "Off: compare and instance individual mesh transforms only (leaf mode).\n"
                "Ignored (grayed out) when Separate Combined Meshes is enabled — "
                "that mode determines hierarchy vs. leaf matching itself."
            ),
        )
        chk_separate = menu.add(
            "QCheckBox",
            setText="Separate Combined Meshes",
            setObjectName="chk007",
            setChecked=False,
            setToolTip="Split combined meshes into their original parts and reassemble matching assemblies before instancing.",
        )
        chk_combine = menu.add(
            "QCheckBox",
            setText="Combine Reassembled Assemblies",
            setObjectName="chk008",
            setChecked=True,
            setEnabled=False,
            setToolTip=(
                "Merge each reassembled assembly into a single combined mesh "
                "before instancing — assembly-level instances instead of many "
                "micro part instances. Uncheck to keep parts separate and "
                "instance assemblies as hierarchies."
            ),
        )
        # Separate Combined Meshes derives its own hierarchy/leaf mode
        # internally (AutoInstancer._run) — Match Whole Hierarchies has no
        # effect while it's on, so disable it to avoid a misleading control.
        chk_separate.toggled.connect(chk_combine.setEnabled)
        chk_separate.toggled.connect(lambda checked: chk_hierarchy.setEnabled(not checked))

        chk_combine_rest = menu.add(
            "QCheckBox",
            setText="Combine Non-Instanced",
            setObjectName="chk009",
            setChecked=True,
            setToolTip=(
                "After instancing, merge everything that did not become an "
                "instance (unique leftovers, one-off assemblies) into combined "
                "meshes — fewer draw calls for a game-ready result.\n"
                "Skipped automatically for non-static setups."
            ),
        )
        chk_by_mat = menu.add(
            "QCheckBox",
            setText="   By Material",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Combine into one mesh per assigned material.",
        )
        chk_by_dist = menu.add(
            "QCheckBox",
            setText="   By Distance",
            setObjectName="chk011",
            setChecked=True,
            setToolTip="Subdivide combine groups by spatial proximity (culling-friendly).",
        )
        s_dist = menu.add(
            "QDoubleSpinBox",
            setPrefix="Cluster Distance: ",
            setObjectName="s001",
            setDecimals=0,
            setMinimum=1.0,
            setMaximum=1000000.0,
            setSingleStep=100.0,
            setValue=10000.0,
            setToolTip="Maximum distance between meshes combined into the same cluster.",
        )
        chk_combine_rest.toggled.connect(chk_by_mat.setEnabled)
        chk_combine_rest.toggled.connect(chk_by_dist.setEnabled)
        chk_combine_rest.toggled.connect(s_dist.setEnabled)

    def tb002(self, widget):
        """Auto Instance: find and convert geometrically identical meshes
        into instances of a single prototype (scans the selection, or the
        whole scene if nothing is selected)."""
        menu = widget.option_box.menu

        created = mtk.auto_instance(
            None,
            tolerance=menu.s000.value(),
            require_same_material=menu.chk004.isChecked(),
            check_uvs=menu.chk005.isChecked(),
            check_hierarchy=menu.chk006.isChecked(),
            separate_combined=menu.chk007.isChecked(),
            combine_assemblies=menu.chk008.isChecked(),
            combine_non_instanced=menu.chk009.isChecked(),
            combine_by_material=menu.chk010.isChecked(),
            combine_by_distance=menu.chk011.isChecked(),
            combine_distance_threshold=menu.s001.value(),
        )

        survivors = [n for n in created if cmds.objExists(n)]
        if survivors:
            cmds.select(survivors, replace=True)
            om.MGlobal.displayInfo(
                f"Auto Instance: {len(survivors)} node(s) instanced or combined."
            )
        else:
            self.sb.message_box(
                "<strong>No matching geometry found</strong>.<br>"
                "No identical meshes to instance and nothing to combine."
            )

    def tb000_init(self, widget):
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Center pivot on the object(s) before instancing.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk000",
            setChecked=False,
            setToolTip="Freeze transforms on the object(s) before instancing.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete History",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Delete history on the object(s) before instancing.",
        )

    def tb000(self, widget):
        """Convert to Instances"""
        freeze_transforms = widget.option_box.menu.chk000.isChecked()
        center_pivot = widget.option_box.menu.chk002.isChecked()
        delete_history = widget.option_box.menu.chk001.isChecked()

        # Get the list of selected transform nodes in the order they were selected
        selection = cmds.ls(orderedSelection=True, transforms=True) or []
        if not selection:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires an object selection."
            )
            return

        if len(selection) < 2:
            self.sb.message_box(
                "<strong>Insufficient selection</strong>.<br>Operation requires at least two objects: source and target(s)."
            )
            return

        mtk.replace_with_instances(
            selection,
            freeze_transforms=freeze_transforms,
            center_pivot=center_pivot,
            delete_history=delete_history,
        )

    def tb001_init(self, widget):
        widget.option_box.menu.add(
            "QCheckBox",
            setText="All Instanced Objects",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Select all instanced objects in the scene instead of just instances of selected objects.",
        )

    def tb001(self, widget):
        """Select Instanced Objects"""
        all_instanced = widget.option_box.menu.chk003.isChecked()

        if all_instanced:
            # Select all instanced objects in the scene
            instances = mtk.get_instances(objects=None)
        else:
            # Select instances of the selected objects only
            selection = cmds.ls(sl=1) or []
            if not selection:
                self.sb.message_box(
                    "<strong>Nothing selected</strong>.<br>Select objects to find their instances, or enable 'All Instanced Objects' option."
                )
                return
            instances = mtk.get_instances(selection)

        if instances:
            cmds.select(instances)
        else:
            self.sb.message_box("<strong>No instanced objects found</strong>.")

    def b000(self):
        """Mirror: open the Mirror tool window."""
        self.sb.handlers.marking_menu.show("mirror")

    def b005(self):
        """Uninstance Selected Objects"""
        selection = cmds.ls(sl=1) or []
        mtk.uninstance(selection)

    def b006(self):
        """Duplicate Linear"""
        self.sb.handlers.marking_menu.show("duplicate_linear")

    def b007(self):
        """Duplicate Radial"""
        self.sb.handlers.marking_menu.show("duplicate_radial")

    def b008(self):
        """Duplicate Grid"""
        self.sb.handlers.marking_menu.show("duplicate_grid")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
