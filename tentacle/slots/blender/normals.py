# !/usr/bin/python
# coding=utf-8
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Normals(SlotsBlender):
    """Blender port of the shared ``normals`` menu.

    Backed by ``blendertk.edit_utils`` normal/shading helpers (bmesh): soften/harden (smooth vs
    flat shading), set-by-angle (mark sharp edges → Blender split normals follow them), flip, and
    recalculate; normal transfer rides the native Data-Transfer operator. Normal lock/unlock maps
    to custom split normals (add = lock, clear = unlock).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    # ------------------------------------------------------------------ tb001  Set Normals By Angle
    def tb001_init(self, widget):
        # s002/s003/s004/chk_unlock_normals reuse the Maya names + labels for the SAME options.
        # Blender edges are binary sharp/smooth, so the 0..180 hardness *value* collapses to
        # hard (< 90) / soft (≥ 90); -1 disables that bucket (leaves those edges as-is).
        widget.option_box.menu.setTitle("Set Normals By Angle")
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Angle Threshold: ", setObjectName="s002",
            set_limits=[0, 180], setValue=90,
            setToolTip="Edges with a dihedral angle ≥ this (degrees) get Upper Hardness; below get Lower.",
        )
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Upper Hardness: ", setObjectName="s003",
            set_limits=[-1, 180], setValue=0,
            setToolTip="Hardness for edges at/above the threshold.\n0 = hard, 180 = soft, -1 = leave as-is.",
        )
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Lower Hardness: ", setObjectName="s004",
            set_limits=[-1, 180], setValue=180,
            setToolTip="Hardness for edges below the threshold.\n0 = hard, 180 = soft, -1 = leave as-is.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Unlock Normals", setObjectName="chk_unlock_normals",
            setChecked=True,
            setToolTip="Clear custom split normals before applying.\nRequired for imported assets "
            "(FBX/Marmoset) — locked/custom normals silently block the smoothing update.",
        )

    @btk.undoable
    def tb001(self, widget):
        """Set Normals By Angle"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Set Normals By Angle requires a selection.")
            return
        m = widget.option_box.menu
        if m.chk_unlock_normals.isChecked():
            cleared = btk.clear_custom_split_normals(objects)
            if cleared:  # silent when nothing was locked — this is a pre-step, not the operation
                self.sb.message_box(
                    f"Cleared custom split normals on <hl>{cleared}</hl> mesh(es)."
                )
        # -1 -> None (disable that bucket), mirroring the Maya slot.
        upper = m.s003.value()
        lower = m.s004.value()
        btk.set_edge_hardness(
            objects,
            angle=m.s002.value(),
            upper_hardness=upper if upper > -1 else None,
            lower_hardness=lower if lower > -1 else None,
        )

    # ------------------------------------------------------------------ tb004  Average Normals
    def tb004_init(self, widget):
        # chk003 reuses the Maya name/label (By UV Shell) for the SAME option.
        widget.option_box.menu.setTitle("Average Normals")
        widget.option_box.menu.add(
            "QCheckBox", setText="By UV Shell", setObjectName="chk003",
            setToolTip="Average (soften) normals within each UV island independently — UV-seam "
            "edges stay hard, so shells smooth separately (the common game-art normal setup).",
        )

    @btk.undoable
    def tb004(self, widget):
        """Average Normals — soften edges so vertex normals are averaged across shared faces;
        By UV Shell keeps UV-island boundaries hard so each shell is smoothed independently."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Average Normals requires a selection.")
            return
        btk.average_normals(objects, by_uv_shell=widget.option_box.menu.chk003.isChecked())

    # ------------------------------------------------------------------ b-slots
    def _component_scope(self):
        """True when the active object is in Edit Mode — Maya parity: soften/harden/reverse
        act on the *selected components* there, not the whole mesh (the engine falls back to
        whole-object when nothing is component-selected)."""
        obj = self.active_object()
        return bool(obj and obj.mode == "EDIT")

    @btk.undoable
    def b000(self):
        """Soften Edge Normals (smooth shading)."""
        btk.set_shading(
            self.selected_objects(), smooth=True, selected_only=self._component_scope()
        )

    @btk.undoable
    def b001(self):
        """Harden Edge Normals (flat shading)."""
        btk.set_shading(
            self.selected_objects(), smooth=False, selected_only=self._component_scope()
        )

    @btk.undoable
    def b006(self):
        """Set To Face (vertex normals follow faces = flat shading)."""
        btk.set_shading(self.selected_objects(), smooth=False)

    # ------------------------------------------------------------------ tb010  Reverse Normals
    def tb010_init(self, widget):
        if not widget.is_initialized:
            widget.option_box.menu.setTitle("Reverse Normals")
            widget.option_box.menu.add(
                "QComboBox", setObjectName="cmb000",
                addItems=["Flip", "Recalculate Outside", "Recalculate Inside"],
                setToolTip="Normal operation mode.",
            )

    @btk.undoable
    def tb010(self, widget):
        """Reverse Normals"""
        objects = self.selected_objects()
        if not objects:
            return
        mode = widget.option_box.menu.cmb000.currentText()
        if mode == "Recalculate Outside":
            btk.recalculate_normals(objects, inside=False)
        elif mode == "Recalculate Inside":
            btk.recalculate_normals(objects, inside=True)
        else:
            btk.flip_normals(objects, selected_only=self._component_scope())

    # ------------------------------------------------------------------ b002  Transfer Normals
    @btk.undoable
    def b002(self):
        """Transfer Normals (active mesh → other selected, native Data-Transfer
        custom split normals)."""
        self.transfer_from_active("CUSTOM_NORMAL")

    # ------------------------------------------------------------------ b004  Un/Lock Normals
    @btk.undoable
    def b004(self):
        """Toggle lock/unlock vertex normals — Maya parity (m_lock_vertex_normals): report the
        state the selection is now IN, not the mechanism that got it there. Custom split normals
        are Blender's lock (locking bakes the current normals; unlocking clears them, which is
        what frees imported assets to re-smooth). A mixed selection reads as unlocked, so the
        toggle locks it whole."""
        # Mesh-filtered, not just non-empty: the engine skips non-meshes, so an empty/light/armature
        # selection would report a state ("Locked") that nothing was actually put into.
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("Un/Lock Normals requires a mesh selection.")
            return
        if btk.has_custom_split_normals(objects):
            btk.clear_custom_split_normals(objects)
            self.sb.message_box("Normals <hl>Unlocked</hl>.")
        else:
            btk.add_custom_split_normals(objects)
            self.sb.message_box("Normals <hl>Locked</hl>.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
