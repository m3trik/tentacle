# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk

# From this Package:
from tentacle.slots.maya import SlotsMaya


class Lighting(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb = kwargs.get("switchboard")

    def header_init(self, widget):
        """ """
        # Add a button to launch the hdr manager.
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setToolTip="Manage the scene's HDR shader.",
            setText="HDR Manager",
            setObjectName="b000",
        )
        ui = mtk.UiManager.instance(self.sb).get("hdr_manager")
        widget.menu.b000.clicked.connect(lambda: self.sb.parent().show(ui))


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
