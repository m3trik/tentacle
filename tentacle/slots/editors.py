# !/usr/bin/python
# coding=utf-8
from uitk.switchboard import signals
from tentacle.slots import Slots


class Editors(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        """

    def list000_init(self, root):
        """ """
        print("list000_init:", root)
        root.sublist_x_offset = -19

        w1 = root.add("General Editors")
        w2 = root.add("Modeling Editors")
        w3 = root.add("Animation Editors")
        w4 = root.add("Rendering Editors")
        w5 = root.add("Relationship Editors")

        print(root.name, root.isVisible())

    @signals("on_item_interacted")
    def list000(self, item):
        """ """
        print("list000:", item)
