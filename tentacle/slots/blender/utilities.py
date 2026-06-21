# !/usr/bin/python
# coding=utf-8
import bpy
from tentacle.slots.blender._slots_blender import SlotsBlender


class Utilities(SlotsBlender):
    """Blender port of the shared ``utilities`` menu.

    Measure/annotate map onto Blender's builtin viewport tools (``wm.tool_set_by_id`` — the
    same mechanism the selection-style toggles use); grease pencil adds a stroke object; the
    calculator is a shared DCC-agnostic panel.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def b000(self):
        """Measure"""
        self.set_viewport_tool("builtin.measure", "Measure")

    def b001(self):
        """Annotation"""
        self.set_viewport_tool("builtin.annotate", "Annotation")

    def b002(self):
        """Calculator"""
        self.sb.handlers.marking_menu.show("calculator")

    def b003(self):
        """Grease Pencil (add an empty stroke object to draw into)"""
        op = getattr(bpy.ops.object, "grease_pencil_add", None) or getattr(
            bpy.ops.object, "gpencil_add", None
        )
        if op is None:
            self.sb.message_box("Grease Pencil is not available in this Blender version.")
            return
        try:
            op(type="EMPTY")
        except (RuntimeError, TypeError) as e:
            self.sb.message_box(str(e))


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
