# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from uitk import Signals
from tentacle.slots.maya import SlotsMaya


class Main(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def list000_init(self, widget):
        """ """
        widget.clear()
        widget.refresh = True
        widget.fixed_item_height = 18
        widget.sublist_x_offset = -10
        widget.sublist_y_offset = -10

        w1 = widget.add("Recent Commands")
        recent_commands = {
            m.__doc__.split("\n")[0]: m
            for m in self.sb.slot_history(slice(None, -12))
            if m.__doc__
        }
        w1.sublist.add(recent_commands)

        w2 = widget.add("History")
        obj = pm.ls(sl=True)
        if obj:
            history = {str(node): node for node in pm.listHistory(obj)}
            w2.sublist.add(history)

    @Signals("on_item_interacted")
    def list000(self, item):
        """ """
        text = item.item_text()
        data = item.item_data()
        parent_text = item.parent_item_text()

        if parent_text == "Recent Commands":
            data()

        elif parent_text == "History":
            pm.select(text)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
