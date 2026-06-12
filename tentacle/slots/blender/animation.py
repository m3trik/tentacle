# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Animation(SlotsBlender):
    """Blender port of the shared ``animation`` menu.

    The key-timing operations (invert/stagger/snap/scale/step/copy/paste) are plain math over
    ``fcurve.keyframe_points`` via ``blendertk.anim_utils`` — the §5 finding that animation is
    volume, not difficulty. Maya-editor-bound features (transfer, align, intermediate keys,
    select-keys, visibility keys, repair, shot sequencer/manifest) are deferred with messages.
    Option-box widget names reused from Maya carry the same option (cross-DCC QSettings rule).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.animation
        self._copied_action = None

    # ------------------------------------------------------------------ tb000  Go To Frame
    def tb000_init(self, widget):
        widget.option_box.menu.setTitle("Go To Frame")
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Frame: ", setObjectName="s000",
            set_limits=[-100000, 100000], setValue=1,
            setToolTip="The frame to jump to.",
        )

    def tb000(self, widget):
        """Go To Frame"""
        bpy.context.scene.frame_set(widget.option_box.menu.s000.value())

    # ------------------------------------------------------------------ key-timing ops
    @btk.undoable
    def tb001(self, widget):
        """Invert Keys (mirror key times about the range center — reverses the motion)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Invert Keys requires a selection.")
            return
        btk.invert_keys(objects)

    def tb003_init(self, widget):
        widget.option_box.menu.setTitle("Stagger Keys")
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Spacing: ", setObjectName="s004",
            set_limits=[0, 10000], setValue=5,
            setToolTip="Frames between one object's last key and the next object's first.",
        )

    @btk.undoable
    def tb003(self, widget):
        """Stagger Keys (re-time selected objects sequentially)."""
        objects = self.selected_objects()
        if len(objects) < 2:
            self.sb.message_box("Stagger Keys requires 2+ selected objects.")
            return
        btk.stagger_keys(objects, spacing=widget.option_box.menu.s004.value())

    @btk.undoable
    def tb009(self, widget):
        """Snap Keys to Frames"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Snap Keys requires a selection.")
            return
        btk.snap_keys(objects)

    @btk.undoable
    def tb010(self, widget):
        """Delete Keys (clear all animation on the selection)."""
        cleared = btk.delete_keys(self.selected_objects())
        if not cleared:
            self.sb.message_box("Nothing keyed in the selection.")

    def tb012(self, widget):
        """Copy Keys (from the active object)."""
        active = bpy.context.view_layer.objects.active
        self._copied_action = btk.copy_keys(active) if active else None
        if self._copied_action is None:
            self.sb.message_box("The active object has no keys to copy.")

    @btk.undoable
    def tb018(self, widget):
        """Paste Keys (independent copies onto the selection)."""
        if self._copied_action is None:
            self.sb.message_box("Nothing copied — use Copy Keys first.")
            return
        btk.paste_keys(self.selected_objects(), self._copied_action)

    def tb014_init(self, widget):
        widget.option_box.menu.setTitle("Scale Keys")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Factor: ", setObjectName="d001",
            set_limits=[0.01, 100, 0.1, 2], setValue=2.0,
            setToolTip="Scale key times by this factor (about each action's first key).",
        )

    @btk.undoable
    def tb014(self, widget):
        """Scale Keys"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Scale Keys requires a selection.")
            return
        btk.scale_keys(objects, factor=widget.option_box.menu.d001.value())

    @btk.undoable
    def tb017(self, widget):
        """Step Tangents (constant interpolation on every key)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Step Tangents requires a selection.")
            return
        btk.set_stepped(objects)

    # ------------------------------------------------------------------ b-slots
    def b005(self):
        """Fit Playback Range (to the keyed extent of the selection, or the whole scene)."""
        objects = self.selected_objects() or None
        applied = btk.fit_playback_range(objects)
        if applied is None:
            self.sb.message_box("Nothing keyed to fit the range to.")
        else:
            self.sb.message_box(f"Playback range set to <hl>{applied[0]}-{applied[1]}</hl>.")

    # ------------------------------------------------------------------ deferred
    def b000(self):
        """Shot Sequencer — mayatk window; not yet ported."""
        self.sb.message_box("Shot Sequencer is not yet implemented for Blender.")

    def b004(self):
        """Shot Manifest — mayatk window; not yet ported."""
        self.sb.message_box("Shot Manifest is not yet implemented for Blender.")

    def tb002(self, widget):
        """Adjust Key Spacing — not yet ported."""
        self.sb.message_box("Adjust Key Spacing is not yet implemented for Blender.")

    def tb004(self, widget):
        """Transfer Keys — not yet ported."""
        self.sb.message_box("Transfer Keys is not yet implemented for Blender.")

    def tb005(self, widget):
        """Add/Remove Intermediate Keys — not yet ported."""
        self.sb.message_box("Intermediate Keys is not yet implemented for Blender.")

    def tb006(self, widget):
        """Move Keys — use the Dope Sheet (G to grab keys)."""
        self.sb.message_box("Move Keys is not yet implemented for Blender (use the Dope Sheet).")

    def tb007(self, widget):
        """Align Keys — not yet ported."""
        self.sb.message_box("Align Keys is not yet implemented for Blender.")

    def tb008(self, widget):
        """Set Visibility Keys — not yet ported."""
        self.sb.message_box("Visibility Keys is not yet implemented for Blender.")

    def tb013(self, widget):
        """Select Keys — use the Dope Sheet / Graph Editor."""
        self.sb.message_box("Select Keys is not yet implemented for Blender (use the Dope Sheet).")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
