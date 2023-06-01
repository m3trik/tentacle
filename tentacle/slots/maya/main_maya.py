# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)

from uitk.switchboard import signals
from tentacle.slots.maya import SlotsMaya
from tentacle.slots.main import Main


class Main_maya(Main, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def list000_init(self, widget):
        """ """
        widget.clear()
        widget.is_initialized = False
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

    @signals("on_item_interacted")
    def list000(self, item):
        """ """
        text = item.item_text()
        data = item.item_data()
        parent_text = item.parent_item_text()

        if parent_text == "Recent Commands":
            data()

        elif parent_text == "History":
            pm.select(text)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated: -----------------------------------

#   node history
#   selection = pm.ls(sl=1, objectsOnly=1, flatten=1)
#   if selection:
#       history = selection[0].history()[1:]
#       for node in history:
#           parent = tree.add('QLabel', 'History', childHeader=node.name(), refresh=1, setText=node.name())
#           # print(parent, node.name())
#           attributes = mtk.Node.get_node_attributes(node) #get dict containing attributes:values of the history node.
#           spinboxes = [tree.add('QDoubleSpinBox', parent, refresh=1, set_spinbox_by_value=[k, v])
#               for k, v in attributes.items()
#                   if isinstance(v, (float, int, bool))]

#           set signal/slot connections:
#           wgts.= [tree.add(self.MultiWidget, parent, refresh=1, set_by_value=[k, v])
#               for k, v in attributes.items()
#                   if isinstance(v, (float, int, bool))]

#           for multiWidget in wgts.
#               attr = multiWidget.children_(index=0).text()
#               w = multiWidget.children_(index=1)
#               type_ = w.__class__.__name__

#               if type_ in ['QSpinBox', 'QDoubleSpinBox']:
#                   w.valueChanged.connect(
#                       lambda value, widget=w, node=node: mtk.Node.set_node_attributes(node, {attr:w.value()}))

#           [w.valueChanged.connect(
#               lambda value, widget=w, node=node: mtk.Node.set_node_attributes(node, {widget.prefix().rstrip(': '):value}))
#                   for w in spinboxes] #set signal/slot connections
