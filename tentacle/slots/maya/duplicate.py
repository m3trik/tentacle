# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


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
        widget.menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Center pivot on the object(s) before instancing.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk000",
            setChecked=False,
            setToolTip="Freeze transforms on the object(s) before instancing.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Delete History",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Delete history on the object(s) before instancing.",
        )

    def tb000(self, widget):
        """Convert to Instances"""
        freeze_transforms = widget.menu.chk000.isChecked()
        center_pivot = widget.menu.chk002.isChecked()
        delete_history = widget.menu.chk001.isChecked()

        # Get the list of selected transform nodes in the order they were selected
        selection = pm.ls(orderedSelection=True, transforms=True)
        if not selection:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires an object selection."
            )
            return

        mtk.instance(
            selection,
            freeze_transforms=freeze_transforms,
            center_pivot=center_pivot,
            delete_history=delete_history,
        )

    def b000(self):
        """Mirror"""
        ui = mtk.UiManager.instance(self.sb).get("mirror")
        ui.show()

    def b004(self):
        """Select Instanced Objects"""
        # Select instances of the selected objects or all instanced objects in the scene if not selection.
        objects = None or pm.ls(sl=1)
        instances = mtk.get_instances(objects)
        pm.select(instances)

    def b005(self):
        """Uninstance Selected Objects"""
        selection = pm.ls(sl=1)
        mtk.uninstance(selection)

    def b006(self):
        """Duplicate Linear"""
        ui = mtk.UiManager.instance(self.sb).get("duplicate_linear")
        ui.show()

    def b007(self):
        """Duplicate Radial"""
        ui = mtk.UiManager.instance(self.sb).get("duplicate_radial")
        ui.show()

    def b008(self):
        """Duplicate Grid"""
        ui = mtk.UiManager.instance(self.sb).get("duplicate_grid")
        ui.show()


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
