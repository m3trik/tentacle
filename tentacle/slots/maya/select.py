# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk

# From this package:
from tentacle.slots.maya import SlotsMaya


class SelectSlots(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb = kwargs.get("switchboard")
        self.ui = mtk.UiManager.instance(self.sb).get("select", header=True)

        menu = self.ui.centralWidget()
        menu.add("QPushButton", setText="Test", clicked=self.test, row=0)
        menu.add(self.sb.registered_widgets.Separator, row=1)
        menu.add("QLabel", setText="Custom Label", row=2)

    def test(self, *args, **kwargs):
        print(f"test {args} {kwargs}")

    def hello(self, *args, **kwargs):
        print(f"hello {args} {kwargs}")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
