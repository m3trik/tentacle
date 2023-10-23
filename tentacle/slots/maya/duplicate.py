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

    def b000(self):
        """Mirror"""
        module = mtk.edit_utils.mirror
        slot_class = module.MirrorSlots

        self.sb.register("mirror.ui", slot_class, base_dir=module)
        self.sb.mirror.slots.preview.enable_on_show = True
        self.sb.parent().set_ui("mirror")

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
        module = mtk.edit_utils.duplicate_linear
        slot_class = module.DuplicateLinearSlots

        self.sb.register("duplicate_linear.ui", slot_class, base_dir=module)
        self.sb.parent().set_ui("duplicate_linear")

    def b007(self):
        """Duplicate Radial"""
        module = mtk.edit_utils.duplicate_radial
        slot_class = module.DuplicateRadialSlots

        self.sb.register("duplicate_radial.ui", slot_class, base_dir=module)
        self.sb.parent().set_ui("duplicate_radial")

    def b008(self):
        """Duplicate Grid"""
        module = mtk.edit_utils.duplicate_grid
        slot_class = module.DuplicateGridSlots

        self.sb.register("duplicate_grid.ui", slot_class, base_dir=module)
        self.sb.parent().set_ui("duplicate_grid")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
