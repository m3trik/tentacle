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
        self.ui = self.sb.loaded_ui.lighting
        self.submenu = self.sb.loaded_ui.lighting_submenu

    def header_init(self, widget):
        """ """
        # Add a button to launch the hdr manager.
        widget.menu.add(
            "QPushButton",
            setText="HDR Manager",
            setObjectName="b000",
            setToolTip="Manage the scene's HDR shader.",
        )

    def b000(self):
        """Launch the HDR Manager."""
        ui = mtk.UiManager.instance(self.sb).get("hdr_manager")
        self.sb.parent().show(ui)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
