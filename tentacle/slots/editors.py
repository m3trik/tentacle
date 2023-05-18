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
        list000.position = "right"
        list000.offset = 19
        list000.drag_interaction = True

        w1 = list000.add(setText="General Editors")
        w2 = list000.add(setText="Modeling Editors")
        w3 = list000.add(setText="Animation Editors")
        w4 = list000.add(setText="Rendering Editors")
        w5 = list000.add(setText="Relationship Editors")
