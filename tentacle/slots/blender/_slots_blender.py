# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots._slots import Slots


class SlotsBlender(Slots):
    """App specific methods inherited by all other Blender slot classes."""

    def __init__(self, switchboard):
        super().__init__(switchboard)

    @staticmethod
    def selected_objects():
        """The current object selection (filtered of ``None``) — shared by all Blender slots."""
        return [o for o in (bpy.context.selected_objects or []) if o]

    def set_viewport_tool(self, tool_id, label=None):
        """Activate a builtin viewport workspace tool (knife / loop-cut / poly-build /
        measure / select-styles). ``label`` (a friendly name) shows a passive confirmation
        toast on success — the active-tool change is otherwise easy to miss when triggered
        from the marking menu rather than the toolbar. Returns True when the tool was set.

        Two gotchas when driven from the Qt marking menu rather than the viewport:

        - ``wm.tool_set_by_id`` targets the *active* space's tool, but the active area isn't
          the 3D view here (``context.space_data`` is ``None``), so a bare call silently
          no-ops — it returns success while the tool never changes (the "Multi-Cut does
          nothing" report). Run it under a VIEW_3D override (as ``btk.call_native_menu`` /
          the camera view-switching override do) so it lands on the real viewport.
        - A scripted tool change doesn't refresh the toolbar/header the way a viewport click
          does, so the active-tool **icon never updates** even though the tool is set. Tag the
          3D viewport(s) for redraw afterward so the new tool is reflected.
        """
        ctx = btk.get_view3d_context()
        if not ctx:
            self.sb.message_box("No 3D viewport available — open a 3D view to use this tool.")
            return False
        # ``get_view3d_context`` may yield ``region=None``; setting a tool doesn't need a region,
        # so drop the None rather than guard on it (which would refuse an otherwise-valid set).
        ctx = {k: v for k, v in ctx.items() if v is not None}
        try:
            with bpy.context.temp_override(**ctx):
                bpy.ops.wm.tool_set_by_id(name=tool_id)
        except Exception as e:
            self.sb.message_box(str(e))
            return False
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
        if label:
            self.sb.message_box(f"<hl>{label}</hl> tool active.")
        return True

    @staticmethod
    def resolve_op(op_path):
        """The ``bpy.ops`` callable at a dotted path (``"wm.link"``), or None when the
        operator (possibly add-on-provided) isn't registered in this Blender."""
        group, _, name = op_path.partition(".")
        return getattr(getattr(bpy.ops, group, None), name, None)

    def invoke_op(self, op_path, **kwargs):
        """Invoke an operator's dialog by dotted path (``INVOKE_DEFAULT``), degrading to a
        message when it is unavailable or rejects the context. Returns True when invoked."""
        op = self.resolve_op(op_path)
        if op is None:
            self.sb.message_box(f"Operator <hl>{op_path}</hl> is not available.")
            return False
        try:
            op("INVOKE_DEFAULT", **kwargs)
            return True
        except RuntimeError as e:
            self.sb.message_box(str(e))
            return False

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
