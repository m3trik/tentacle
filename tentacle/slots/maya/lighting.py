# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Lighting(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def header_init(self, widget):
        """ """
        # Add a button to launch the hdr manager.
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setToolTip="Manage the scene's HDR shader.",
            setText="HDR Manager",
            setObjectName="b000",
        )
        from mayatk.light_utils import hdr_manager

        self.sb.register(
            "hdr_manager.ui", hdr_manager.HdrManagerSlots, base_dir=hdr_manager
        )
        widget.menu.b000.clicked.connect(lambda: self.sb.parent().set_ui("hdr_manager"))


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
