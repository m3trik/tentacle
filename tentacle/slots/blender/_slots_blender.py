# !/usr/bin/python
# coding=utf-8
import bpy
from tentacle.slots._slots import Slots


class SlotsBlender(Slots):
    """App specific methods inherited by all other Blender slot classes."""

    def __init__(self, switchboard):
        super().__init__(switchboard)

    @staticmethod
    def selected_objects():
        """The current object selection (filtered of ``None``) — shared by all Blender slots."""
        return [o for o in (bpy.context.selected_objects or []) if o]
