# !/usr/bin/python
# coding=utf-8
import blendertk as btk
from tentacle import Slots


class SlotsBlender(Slots):
    """App specific methods inherited by all other Blender slot classes.

    Each helper delegates to the blendertk operation that holds its logic now,
    keeping its old result and message, until the last Blender fork merges into a
    composed category class (``slots/<category>.py``), which calls the same
    operations through ``self.tk`` (mayatk answering them in Maya). It reaches
    ``btk`` directly rather than through ``self.tk`` so a fork behaves the same
    under a test's switchboard.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    @staticmethod
    def selected_objects():
        """The current object selection: ``btk.CoreUtils.selected_objects`` (the
        window's view layer, so it holds in the Qt-pump state, where
        ``bpy.context.selected_objects`` is empty)."""
        return btk.CoreUtils.selected_objects()

    @staticmethod
    def active_object():
        """The active object (or ``None``): ``btk.CoreUtils.active_object`` (the
        window's view layer; ``bpy.context.active_object`` is ``None`` in the
        Qt-pump state)."""
        return btk.CoreUtils.active_object()

    @staticmethod
    def effective_fps() -> float:
        """The scene frame rate as the user understands it, ``fps / fps_base`` (an
        NTSC-style 24 / 1.001 reads 23.98, not 24): the ``fps`` of
        ``btk.EnvUtils.scene_settings``."""
        return btk.EnvUtils.scene_settings()["fps"]

    def ensure_edit_mode(self, obj_type="MESH", select_mode=None):
        """Put an object of ``obj_type`` into Edit Mode, optionally setting the mesh
        component mask (``"VERT"`` / ``"EDGE"`` / ``"FACE"``):
        ``btk.CoreUtils.ensure_component_mode``. Returns the object, or None when
        there is nothing of that type to edit (callers word their own message)."""
        return btk.CoreUtils.ensure_component_mode(obj_type, select_mode)

    def ensure_object_mode(self):
        """Leave Edit (or any other) Mode before object-level work:
        ``btk.CoreUtils.ensure_object_mode``. Returns False, after a message, when
        Blender refuses the switch."""
        try:
            return btk.CoreUtils.ensure_object_mode()
        except RuntimeError as error:
            self.sb.message_box(f"Could not exit to Object Mode: {error}")
            return False

    def set_viewport_tool(self, tool_id, label=None, edit_type=None):
        """Activate a builtin viewport tool by idname: ``btk.UiUtils.set_tool``,
        which enters the Edit Mode an edit-only tool needs (its registry knows
        which; ``edit_type`` words the message). ``label`` shows a confirmation on
        success. Returns True when the tool was set."""
        try:
            btk.UiUtils.set_tool(tool_id)
        except ValueError:
            kind = (edit_type or "matching").lower()
            self.sb.message_box(
                f"<hl>{label or tool_id}</hl> needs an active or selected {kind} object."
            )
            return False
        except RuntimeError as error:  # no 3D view, or Blender refused the tool
            self.sb.message_box(str(error))
            return False
        if label:
            self.sb.message_box(f"<hl>{label}</hl> tool active.")
        return True

    @staticmethod
    def resolve_op(op_path):
        """The ``bpy.ops`` callable at a dotted path (``"wm.link"``), or None when the
        operator is not registered: ``btk.UiUtils.get_operator``."""
        return btk.UiUtils.get_operator(op_path)

    def invoke_op(self, op_path, **kwargs):
        """Invoke an operator's dialog by dotted path (``INVOKE_DEFAULT``):
        ``btk.UiUtils.invoke_operator_dialog``, degrading to a message when it is
        unavailable or rejects the context. Returns True when invoked."""
        try:
            invoked = btk.UiUtils.invoke_operator_dialog(op_path, **kwargs)
        except RuntimeError as error:
            self.sb.message_box(str(error))
            return False
        if invoked is None:
            self.sb.message_box(f"Operator <hl>{op_path}</hl> is not available.")
            return False
        return True

    def transfer_from_active(self, data_type, **kwargs):
        """Run native Data Transfer from the active mesh to the other selected meshes
        (Transfer Normals / UVs / Crease ...): ``btk.Components.transfer_mesh_data``.
        Returns True when it ran."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if self.active_object() not in objects or len(objects) < 2:
            self.sb.message_box("Select target mesh(es) with the source mesh active.")
            return False
        try:
            btk.Components.transfer_mesh_data(None, data_type, **kwargs)
        except ValueError as error:  # the operator's own report
            self.sb.message_box(str(error))
            return False
        return True
