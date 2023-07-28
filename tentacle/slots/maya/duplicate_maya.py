# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Duplicate_maya(SlotsMaya):
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
        """ """
        mtk.duplicate_linear.launch_gui(move_to_cursor=True, frameless=True)

    def b007(self):
        """ """
        mtk.duplicate_radial.launch_gui(move_to_cursor=True, frameless=True)


# --------------------------------------------------------------------------------------------


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
