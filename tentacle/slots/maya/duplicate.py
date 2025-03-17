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

    def tb000_init(self, widget):
        widget.menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk000",
            setChecked=False,
            setToolTip="Freeze transforms on the object(s) before instancing.",
        )

    def tb000(self, widget):
        """Convert to Instances"""
        freeze_transforms = widget.menu.chk000.isChecked()
        # Get the list of selected transform nodes in the order they were selected
        selection = pm.ls(orderedSelection=True, transforms=True)
        if not selection:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires an object selection."
            )
            return

        # Freeze transforms if the option is checked
        if freeze_transforms:
            for obj in selection:
                pm.makeIdentity(obj, apply=True, t=1, r=1, s=1, n=0)

        mtk.convert_to_instances(selection)

    def b000(self):
        """Mirror"""
        from mayatk.edit_utils import mirror

        self.sb.register("mirror.ui", mirror.MirrorSlots, base_dir=mirror)
        self.sb.loaded_ui.mirror.slots.preview.enable_on_show = True
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
        from mayatk.edit_utils import duplicate_linear

        self.sb.register(
            "duplicate_linear.ui",
            duplicate_linear.DuplicateLinearSlots,
            base_dir=duplicate_linear,
        )
        self.sb.parent().set_ui("duplicate_linear")

    def b007(self):
        """Duplicate Radial"""
        from mayatk.edit_utils import duplicate_radial

        self.sb.register(
            "duplicate_radial.ui",
            duplicate_radial.DuplicateRadialSlots,
            base_dir=duplicate_radial,
        )
        self.sb.parent().set_ui("duplicate_radial")

    def b008(self):
        """Duplicate Grid"""
        from mayatk.edit_utils import duplicate_grid

        self.sb.register(
            "duplicate_grid.ui",
            duplicate_grid.DuplicateGridSlots,
            base_dir=duplicate_grid,
        )
        self.sb.parent().set_ui("duplicate_grid")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
