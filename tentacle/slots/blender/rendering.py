# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Rendering(SlotsBlender):
    """Blender port of the shared ``rendering`` menu.

    Render-frame / show-last-render map onto ``render.render`` / ``render.view_show``;
    playblast maps onto Blender's OpenGL viewport render; render settings live in the
    Properties editor. Maya's Render-Setup / Rendering-Flags editors have no analogue.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.rendering

    # ------------------------------------------------------------------ cmb001  Render camera
    def cmb001_init(self, widget):
        """Initialize the render-camera combo (label -> camera object)."""
        widget.refresh_on_show = True
        cameras = {o.name: o for o in bpy.data.objects if o.type == "CAMERA"}
        widget.add(cameras, header="Camera:", clear=True)
        current = bpy.context.scene.camera
        if current and current.name in cameras:
            widget.setCurrentIndex(list(cameras).index(current.name))

    def cmb001(self, index, widget):
        """Set the scene's active (render) camera."""
        cam = widget.currentData()
        if cam is not None:
            bpy.context.scene.camera = cam

    # ------------------------------------------------------------------ tb000  Playblast
    def tb000_init(self, widget):
        widget.option_box.menu.setTitle("Playblast")
        widget.option_box.menu.add(
            "QCheckBox", setText="Current Viewport", setObjectName="chk000",
            setToolTip="Capture the viewport as-is (shading/overlays) instead of the camera view.",
        )

    def tb000(self, widget):
        """Export Playblast (OpenGL viewport render of the frame range)."""
        view_context = widget.option_box.menu.chk000.isChecked()
        try:
            bpy.ops.render.opengl(animation=True, view_context=view_context)
        except RuntimeError as e:
            self.sb.message_box(str(e))
            return
        self.sb.message_box(
            f"Playblast written to <hl>{bpy.context.scene.render.filepath}</hl>."
        )

    # ------------------------------------------------------------------ b-slots
    def b000(self):
        """Render Current Frame"""
        try:
            bpy.ops.render.render("INVOKE_DEFAULT")
        except RuntimeError as e:
            self.sb.message_box(str(e))

    def b001(self):
        """Render Settings (Properties editor, Render tab)"""
        btk.open_editor("Properties")

    def b002(self):
        """Show Last Render"""
        try:
            bpy.ops.render.view_show("INVOKE_DEFAULT")
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def b003(self):
        """Render Setup — Maya editor; Blender uses View Layers (Properties editor)."""
        self.sb.message_box("Render Setup is not applicable in Blender (use View Layers).")

    def b004(self):
        """Rendering Flags — Maya editor with no Blender analogue."""
        self.sb.message_box("Rendering Flags editor is not applicable in Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
