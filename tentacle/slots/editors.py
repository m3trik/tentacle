# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Editors(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        """
        list000 = self.sb.editors_lower_submenu.list000
        list000.drag_interaction = True

        w1 = list000.add("General Editors")
        w2 = list000.add("Modeling Editors")
        w3 = list000.add("Animation Editors")
        w4 = list000.add("Rendering Editors")
        w5 = list000.add("Relationship Editors")
