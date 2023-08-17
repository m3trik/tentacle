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

    def tb000(self, widget):
        """Convert to Instances"""
        selection = pm.ls(sl=1, transforms=1)
        if not selection:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires an object selection."
            )
            return

        # If ordered selection is not on, turn it on. If off, the current selection is likely not ordered.
        if not pm.selectPref(q=1, trackSelectionOrder=1):
            pm.selectPref(trackSelectionOrder=1)
        mtk.convert_to_instances(selection)

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
        ui_file = mtk.duplicate_linear.get_ui_file()
        slot_class = mtk.duplicate_linear.DuplicateLinearSlots

        self.sb.register(ui_file, slot_class)
        self.sb.parent().set_ui("duplicate_linear")

    def b007(self):
        """Duplicate Radial"""
        ui_file = mtk.duplicate_radial.get_ui_file()
        slot_class = mtk.duplicate_radial.DuplicateRadialSlots

        self.sb.register(ui_file, slot_class)
        self.sb.parent().set_ui("duplicate_radial")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
