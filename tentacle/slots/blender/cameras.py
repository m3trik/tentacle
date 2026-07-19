# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class Cameras(SlotsBlender):
    """Blender port of the shared ``cameras`` menu.

    Standard-view switching maps to ``view3d.view_axis`` (viewport ops, run under an explicit
    VIEW_3D override). Camera creation/selection + clip adjustment are object/data ops backed by
    ``blendertk.cam_utils``. Dolly/Roll/Truck/Orbit (``b010``-``b013``) arm interactive Maya-style
    drag-nav tools — ``btk.navigate_view`` invokes a modal operator that drags the RegionView3D
    exactly like Maya's tumbleContext/trackContext/dollyContext (and a drag Roll). Per-camera
    exclusive/hidden visibility has no Blender primitive and is deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.cameras
        # Double-click gesture + keyable 'toggle_camera_view' command. Shared,
        # DCC-agnostic wiring on the base slot class (tentacle.slots._slots.Slots).
        self.register_camera_view_toggle()

    @staticmethod
    def _scene_cameras():
        return [o for o in bpy.data.objects if o.type == "CAMERA"]

    def _view3d_context(self, no_viewport="No 3D viewport available."):
        """The VIEW_3D override dict (validated to carry a WINDOW region), or ``None`` after
        messaging — the shared guard for viewport ops run from the Qt pump, where ``bpy.context``
        has no active VIEW_3D. Callers wrap their ``view3d.*`` ops in
        ``bpy.context.temp_override(**ctx)`` (see ``_set_view_axis`` / ``b007`` / ``b011``)."""
        ctx = btk.get_view3d_context()
        if ctx and ctx.get("region"):
            return ctx
        self.sb.message_box(no_viewport)
        return None

    def _set_view_axis(self, view_type):
        ctx = self._view3d_context("No 3D viewport available for view switching.")
        if ctx is None:
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
            cam = self.active_object()  # window-independent (bpy.context.active_object is None from the Qt-pump context)
            if cam is None or cam.type != "CAMERA":
                self.sb.message_box("Camera creation failed — the active object is not a camera.")
                return
            cam.data.lens = float(item.item_data())  # focal length (mm), matches Maya focalLength

        elif parent_text == "Select Camera":
            cam = bpy.data.objects.get(text)
            if cam:
                # Mode-independent deselect: ``object.select_all`` is an Object-Mode op (it
                # poll-fails in Edit Mode and from the Qt-pump context); a view-layer
                # ``select_set`` loop is neither mode- nor window-dependent.
                for o in bpy.context.view_layer.objects:
                    o.select_set(False)
                cam.select_set(True)
                bpy.context.view_layer.objects.active = cam
                bpy.context.scene.camera = cam  # make it the active (look-through) camera
                # Actually look through it (Maya twin: cmds.lookThru) — switch the viewport
                # into camera view, under the same override pattern as the axis views.
                ctx = btk.get_view3d_context()
                if ctx and ctx.get("region") and ctx["region"].data:
                    with bpy.context.temp_override(**ctx):
                        ctx["region"].data.view_perspective = "CAMERA"

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
        ctx = self._view3d_context("No 3D viewport available for view switching.")
        if ctx is None:
            return
        rv3d = ctx["region"].data
        if not rv3d:
            return
        with bpy.context.temp_override(**ctx):
            if rv3d.view_perspective == "CAMERA":
                # Leave camera view (Select Camera / a user camera view would otherwise
                # dead-end here — view_persportho only toggles PERSP<->ORTHO).
                rv3d.view_perspective = "PERSP"
            elif rv3d.view_perspective == "ORTHO":
                # Ensure perspective projection (toggle only if currently orthographic).
                bpy.ops.view3d.view_persportho()

    def b005(self):
        """Cameras: Front View"""
        self._set_view_axis("FRONT")

    def b006(self):
        """Cameras: Bottom View"""
        self._set_view_axis("BOTTOM")

    # ------------------------------------------------------------------ b007  Align View
    def b007(self):
        """Cameras: Align View (align the viewport to the active element's normal and frame
        the selection — Blender's Align-View-to-Active, the analogue of Maya's
        align-camera-to-polygon)."""
        ctx = self._view3d_context("No 3D viewport available for view switching.")
        if ctx is None:
            return
        if not self.selected_objects():
            self.sb.message_box("Nothing Selected.")
            return
        try:
            with bpy.context.temp_override(**ctx):
                bpy.ops.view3d.view_axis(type="TOP", align_active=True)
                bpy.ops.view3d.view_selected()
        except RuntimeError as error:
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ b010-b013  Nav tools
    # Maya's Dolly/Truck/Orbit arm interactive drag tools (setToolTo tumbleContext/trackContext/
    # dollyContext); Roll is a discrete cmds.roll. blendertk rolls our own faithful equivalents —
    # a modal operator that drags the RegionView3D exactly like Maya — armed here: LMB-drag to
    # navigate, RMB/Enter to finish, Esc to cancel. btk.navigate_view refuses in --background.
    def _nav(self, mode):
        """Arm the interactive viewport-nav tool for ``mode`` (btk.navigate_view)."""
        try:
            btk.navigate_view(mode)
        except RuntimeError as error:
            self.sb.message_box(str(error))

    def b010(self):
        """Camera: Dolly — arm the interactive dolly tool (LMB-drag to move the eye in/out)."""
        self._nav("DOLLY")

    def b011(self):
        """Camera: Roll — arm the interactive roll tool (LMB-drag to roll the view about its axis)."""
        self._nav("ROLL")

    def b012(self):
        """Camera: Truck — arm the interactive track/pan tool (LMB-drag to pan the view)."""
        self._nav("TRACK")

    def b013(self):
        """Camera: Orbit — arm the interactive tumble tool (LMB-drag to orbit the view)."""
        self._nav("ORBIT")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
