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
        """The current object selection (filtered of ``None``) — shared by all Blender slots.

        Delegates to ``btk.selected_objects`` (the SSoT reader), which reads the selection from
        ``view_layer.objects`` rather than ``bpy.context.selected_objects``. The latter is a
        *screen-context* member that returns ``[]`` whenever ``bpy.context.window`` is ``None`` —
        the state the slots run in when driven from tentacle's Qt event-pump timer — which is why
        operations reported *nothing selected* while an object was in fact selected."""
        return btk.selected_objects()

    @staticmethod
    def active_object():
        """The active object (or ``None``) — shared by all Blender slots.

        Delegates to ``btk.active_object`` (reads ``view_layer.objects.active``), robust against the
        ``bpy.context.window is None`` state the Qt event-pump timer context exhibits, unlike
        ``bpy.context.active_object`` (which returns ``None`` there)."""
        return btk.active_object()

    def ensure_edit_mode(self, obj_type="MESH", select_mode=None):
        """Put an object of ``obj_type`` into Edit Mode (Maya's *component* mode), optionally
        setting the mesh component mask (``select_mode``: "VERT"/"EDGE"/"FACE"). Returns the
        object, or None when there is nothing of that type to edit (callers surface their own
        message — the useful wording differs per tool).

        Prefers the active object, falling back to the first selected object of ``obj_type``
        and activating it: Maya's component tools act on the *selection*, so a curve tool must
        still work when a selected curve isn't the active object (``btk.target_weld`` makes the
        same fall-back for the same reason).
        """
        obj = self.active_object()  # not bpy.context.active_object: None from the Qt-pump context
        if not obj or obj.type != obj_type:
            # ``selected_objects`` reads view_layer.objects — which is what makes the ``active``
            # assignment below safe: an object sourced from bpy.data could be excluded from the
            # view layer, and assigning that raises.
            candidates = [o for o in self.selected_objects() if o.type == obj_type]
            if not candidates:
                return None
            obj = candidates[0]
            bpy.context.view_layer.objects.active = obj
        if obj.mode != "EDIT":
            try:
                bpy.ops.object.mode_set(mode="EDIT")
            except RuntimeError:  # hidden / linked object — not editable
                return None
        if select_mode:
            bpy.ops.mesh.select_mode(type=select_mode)
        return obj

    def set_viewport_tool(self, tool_id, label=None, edit_type=None):
        """Activate a builtin viewport workspace tool (knife / loop-cut / poly-build /
        measure / select-styles). ``label`` (a friendly name) shows a passive confirmation
        toast on success — the active-tool change is otherwise easy to miss when triggered
        from the marking menu rather than the toolbar. Returns True when the tool was set.

        ``edit_type`` ("MESH" / "CURVE") declares that the tool exists **only** in that object
        type's Edit Mode; the object is switched into it first (see the mode gotcha below).

        Three gotchas when driven from the Qt marking menu rather than the viewport:

        - Blender resolves a workspace tool by (space_type, *context mode*), so setting an
          Edit-Mode-only tool while in Object Mode logs "Tool 'builtin.knife' not found for
          space 'VIEW_3D'" and changes nothing. That is a ``report({'WARNING'})``, **not** an
          exception — the ``except`` below never sees it, so the tool silently stays put while
          the success toast still fires. Maya's equivalents enter component mode implicitly, so
          ``edit_type`` does it here rather than leaking a Blender-internal warning. Verified
          per-mode availability (Blender 5.1): knife / loop_cut / poly_build are EDIT_MESH-only,
          pen / draw are EDIT_CURVE-only; measure / annotate / select_* exist in every mode and
          so pass no ``edit_type``.
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
        if edit_type and not self.ensure_edit_mode(edit_type):
            self.sb.message_box(
                f"<hl>{label or tool_id}</hl> needs an active or selected "
                f"{edit_type.lower()} object."
            )
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
        for area in btk.get_areas("VIEW_3D"):
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
        active = self.active_object()
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
