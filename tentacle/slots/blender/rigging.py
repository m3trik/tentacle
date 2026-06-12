# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Rigging(SlotsBlender):
    """Blender port of the shared ``rigging`` menu.

    The most divergent domain (skinCluster → Armature + vertex groups), so the name mirror is
    relaxed per the plan: locators map to Empties, local-rotation-axes to ``show_axis``,
    attribute locking to the transform lock flags. Constraint switching, Quick-Rig and the
    mayatk Render-Opacity tool are deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.rigging

    # ------------------------------------------------------------------ cmb001  Create
    def cmb001_init(self, widget):
        widget.add(["Armature", "Empty"], header="Create")

    @btk.undoable
    def cmb001(self, index, widget):
        """Create rigging primitives."""
        text = widget.items[index]
        if text == "Armature":
            bpy.ops.object.armature_add()
        elif text == "Empty":
            bpy.ops.object.empty_add(type="PLAIN_AXES")

    # ------------------------------------------------------------------ tb000  Local rotation axes
    @btk.undoable
    def tb000(self, widget):
        """Toggle Display Local Rotation Axes (``show_axis``)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Toggle Axes requires a selection.")
            return
        state = not objects[0].show_axis
        for o in objects:
            o.show_axis = state

    # ------------------------------------------------------------------ tb003/b003  Locators (Empties)
    @btk.undoable
    def tb003(self, widget):
        """Create Locator at Selection (an Empty at each selected object's origin;
        a lone Empty at the cursor when nothing is selected)."""
        objects = self.selected_objects()
        if not objects:
            bpy.ops.object.empty_add(type="PLAIN_AXES")
            return
        for o in objects:
            empty = bpy.data.objects.new(f"loc_{o.name}", None)
            empty.empty_display_type = "PLAIN_AXES"
            empty.location = o.matrix_world.translation
            bpy.context.collection.objects.link(empty)

    @btk.undoable
    def b003(self):
        """Remove Locator (delete selected Empties)."""
        empties = [o for o in self.selected_objects() if o.type == "EMPTY"]
        if not empties:
            self.sb.message_box("No Empties selected.")
            return
        for o in empties:
            bpy.data.objects.remove(o, do_unlink=True)

    # ------------------------------------------------------------------ tb004  Lock/Unlock Attributes
    def tb004_init(self, widget):
        menu = widget.option_box.menu
        menu.setTitle("Lock/Unlock Attributes")
        menu.add("QCheckBox", setText="Translate", setObjectName="chk_lock_translate",
                 setChecked=True, setToolTip="Lock/unlock the location channels.")
        menu.add("QCheckBox", setText="Rotate", setObjectName="chk_lock_rotate",
                 setChecked=True, setToolTip="Lock/unlock the rotation channels.")
        menu.add("QCheckBox", setText="Scale", setObjectName="chk_lock_scale",
                 setChecked=True, setToolTip="Lock/unlock the scale channels.")

    @btk.undoable
    def tb004(self, widget):
        """Lock/Unlock Attributes (toggles based on the first object's current state)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Lock/Unlock requires a selection.")
            return
        m = widget.option_box.menu
        state = not any(objects[0].lock_location)
        for o in objects:
            if m.chk_lock_translate.isChecked():
                o.lock_location = (state,) * 3
            if m.chk_lock_rotate.isChecked():
                o.lock_rotation = (state,) * 3
            if m.chk_lock_scale.isChecked():
                o.lock_scale = (state,) * 3

    # ------------------------------------------------------------------ deferred
    def cmb002(self, index, widget):
        """Quick Rig — Maya HumanIK workflow; Blender's analogue is the Rigify add-on."""
        self.sb.message_box("Quick Rig is not yet implemented for Blender (see Rigify).")

    def tb001(self, widget):
        """Constraint Switch — not yet ported (Blender bone constraints differ structurally)."""
        self.sb.message_box("Constraint Switch is not yet implemented for Blender.")

    def b004(self):
        """Render Opacity — mayatk tool; not yet ported."""
        self.sb.message_box("Render Opacity is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
