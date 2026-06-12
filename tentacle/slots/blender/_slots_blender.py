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

    def transfer_from_active(self, data_type, **kwargs):
        """Run native Data-Transfer from the active mesh to the other selected meshes
        (shared by Transfer Normals / Transfer UVs). Returns True when the op ran."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        active = bpy.context.view_layer.objects.active
        if active not in objects or len(objects) < 2:
            self.sb.message_box("Select target mesh(es) with the source mesh active.")
            return False
        try:
            bpy.ops.object.data_transfer(
                data_type=data_type, loop_mapping="POLYINTERP_NEAREST", **kwargs
            )
            return True
        except RuntimeError as e:
            self.sb.message_box(str(e))
            return False
