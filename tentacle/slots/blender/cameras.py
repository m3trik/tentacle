# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


def _view3d_context():
    """A context-override dict pointing at the first VIEW_3D area/region, or ``None``.

    Viewport operators (``view3d.*``) are region-centric: when invoked from the Qt marking menu
    the active area isn't the 3D view, so they need an explicit override (unlike object/mesh ops).
    """
    wm = bpy.context.window_manager
    for win in getattr(wm, "windows", []) or []:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                return {"window": win, "area": area, "region": region, "scene": bpy.context.scene}
    return None


class Cameras(SlotsBlender):
    """Blender port of the shared ``cameras`` menu.

    Standard-view switching maps to ``view3d.view_axis`` (viewport ops, run under an explicit
    VIEW_3D override). Camera creation/selection + clip adjustment are object/data ops backed by
    ``blendertk.cam_utils``. Maya-only bits — per-camera exclusive/hidden visibility, align-to-poly,
    the persistent dolly/roll/truck/orbit manipulator tools — are deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.cameras
        try:
            self.sb.handlers.marking_menu.left_mouse_double_click.connect(self.toggle_camera_view)
        except AttributeError:
            pass

    @staticmethod
    def _scene_cameras():
        return [o for o in bpy.data.objects if o.type == "CAMERA"]

    def _set_view_axis(self, view_type):
        ctx = _view3d_context()
        if not ctx or not ctx.get("region"):
            self.sb.message_box("No 3D viewport available for view switching.")
            return
        with bpy.context.temp_override(**ctx):
            bpy.ops.view3d.view_axis(type=view_type)

    # ------------------------------------------------------------------ list000  Camera options
    def list000_init(self, widget):
        """Initialize Camera Options List"""
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True
            widget.fixed_item_height = 18

        w0 = widget.add("Create Camera")
        w0.sublist.add({"Standard Camera": 35, "Wide Angle Camera": 18, "Telephoto Camera": 85})

        cameras = self._scene_cameras()
        if cameras:
            w1 = widget.add("Select Camera")
            w1.sublist.add([c.name for c in cameras])

        w2 = widget.add("Camera Options")
        w2.sublist.add(["Auto Adjust Clipping", "Reset Clipping"])

    @Signals("on_item_interacted")
    def list000(self, item):
        """Camera Options List"""
        text = item.item_text()
        parent_text = item.parent_item_text()

        if parent_text == "Create Camera":
            bpy.ops.object.camera_add()
            cam = bpy.context.active_object
            cam.data.lens = float(item.item_data())  # focal length (mm), matches Maya focalLength

        elif parent_text == "Select Camera":
            cam = bpy.data.objects.get(text)
            if cam:
                bpy.ops.object.select_all(action="DESELECT")
                cam.select_set(True)
                bpy.context.view_layer.objects.active = cam
                bpy.context.scene.camera = cam  # make it the active (look-through) camera

        elif parent_text == "Camera Options":
            if text == "Auto Adjust Clipping":
                btk.adjust_camera_clipping(near_clip="auto", far_clip="auto")
            elif text == "Reset Clipping":
                btk.adjust_camera_clipping(near_clip="reset", far_clip="reset")

    # ------------------------------------------------------------------ b000-b006  standard views
    def b000(self):
        """Cameras: Back View"""
        self._set_view_axis("BACK")

    def b001(self):
        """Cameras: Top View"""
        self._set_view_axis("TOP")

    def b002(self):
        """Cameras: Right View"""
        self._set_view_axis("RIGHT")

    def b003(self):
        """Cameras: Left View"""
        self._set_view_axis("LEFT")

    def b004(self):
        """Cameras: Perspective View"""
        ctx = _view3d_context()
        if not ctx or not ctx.get("region"):
            self.sb.message_box("No 3D viewport available for view switching.")
            return
        # Ensure perspective projection (toggle only if currently orthographic).
        if ctx["region"].data and ctx["region"].data.view_perspective == "ORTHO":
            with bpy.context.temp_override(**ctx):
                bpy.ops.view3d.view_persportho()

    def b005(self):
        """Cameras: Front View"""
        self._set_view_axis("FRONT")

    def b006(self):
        """Cameras: Bottom View"""
        self._set_view_axis("BOTTOM")

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def b007(self):
        """Cameras: Align View — Maya align-camera-to-polygon has no direct Blender analogue."""
        self.sb.message_box("Align View is not yet implemented for Blender.")

    def b010(self):
        """Camera: Dolly — Blender viewport navigation is modal, not a persistent tool."""
        self.sb.message_box("Camera tools (dolly/roll/truck/orbit) are not applicable in Blender.")

    def b011(self):
        """Camera: Roll"""
        self.sb.message_box("Camera tools (dolly/roll/truck/orbit) are not applicable in Blender.")

    def b012(self):
        """Camera: Truck"""
        self.sb.message_box("Camera tools (dolly/roll/truck/orbit) are not applicable in Blender.")

    def b013(self):
        """Camera: Orbit"""
        self.sb.message_box("Camera tools (dolly/roll/truck/orbit) are not applicable in Blender.")

    # ------------------------------------------------------------------ double-click toggle
    def toggle_camera_view(self):
        """Toggle between the last two camera views in history (DCC-agnostic switchboard logic)."""
        slots = self.sb.get_methods_by_string_pattern(self, "b000-7")
        history = self.sb.slot_history(slice(-2, None), inc=slots)
        if not history:
            return
        if history[-1].__name__ == self.b004.__name__:
            if len(history) < 2:
                return
            last_non_persp_cam = history[-2]
            last_non_persp_cam()
            self.sb.slot_history(add=last_non_persp_cam)
        else:
            self.b004()
            self.sb.slot_history(add=self.b004)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
