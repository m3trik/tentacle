# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
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
        selection = pm.ls(orderedSelection=True, transforms=True)
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
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Select all instanced objects in the scene instead of just instances of selected objects.",
        )

    def tb001(self, widget):
        """Select Instanced Objects"""
        all_instanced = widget.option_box.menu.chk000.isChecked()

        if all_instanced:
            # Select all instanced objects in the scene
            instances = mtk.get_instances(objects=None)
        else:
            # Select instances of the selected objects only
            selection = pm.ls(sl=1)
            if not selection:
                self.sb.message_box(
                    "<strong>Nothing selected</strong>.<br>Select objects to find their instances, or enable 'All Instanced Objects' option."
                )
                return
            instances = mtk.get_instances(selection)

        if instances:
            pm.select(instances)
        else:
            self.sb.message_box("<strong>No instanced objects found</strong>.")

    def b000(self):
        """Mirror"""
        self.sb.handlers.marking_menu.show("mirror")

    def b005(self):
        """Uninstance Selected Objects"""
        selection = pm.ls(sl=1)
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
