# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class MaterialsSlots(SlotsBlender):
    """Blender port of the shared ``materials`` menu.

    Material get/assign/create/select map onto ``bpy.data.materials`` / ``material_slots``
    via ``blendertk.mat_utils`` (no shading engines in Blender). The Maya tools list
    (Stingray/game-shader/Arnold-bridge windows) is Maya-only and hidden.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.materials
        self.submenu = self.sb.loaded_ui.materials_submenu
        self.last_random_material = None

    # ------------------------------------------------------------------ cmb002  Current material
    def cmb002_init(self, widget):
        """Initialize the scene-materials combo (label -> material datablock)."""
        widget.refresh_on_show = True
        materials = {m.name: m for m in bpy.data.materials if not m.is_grease_pencil}
        widget.add(materials, header="Material:", clear=True)

    def cmb002(self, index, widget):
        """Current Material (selection only — assignment is on the b-buttons)."""

    # ------------------------------------------------------------------ tb000  Select By Material
    def tb000_init(self, widget):
        widget.option_box.menu.setTitle("Select By Material")
        widget.option_box.menu.add(
            "QCheckBox", setText="Get and Select", setObjectName="chk007",
            setToolTip="First set the current material from the selected object.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Add To Selection", setObjectName="chk008",
            setToolTip="Add to the current selection instead of replacing it.",
        )

    def tb000(self, widget):
        """Select By Material"""
        m = widget.option_box.menu
        if m.chk007.isChecked():
            self.b002(None)  # sync cmb002 from the active selection first
        mat = self.ui.cmb002.currentData()
        if mat is None:
            self.sb.message_box("No material selected in the materials list.")
            return
        users = btk.select_by_material(mat, add=m.chk008.isChecked())
        if not users:
            self.sb.message_box(f"No objects use <hl>{mat.name}</hl>.")

    # ------------------------------------------------------------------ b-slots
    def b002(self, widget):
        """Get Material: set the combo to the selection's material."""
        selection = self.selected_objects()
        if not selection:
            self.sb.message_box("<hl>Nothing selected</hl><br>Select mesh object(s).")
            return
        mats = btk.get_mats(selection[0])
        if len(mats) != 1:
            self.sb.message_box(
                "<hl>Invalid selection</hl><br>Selection must have exactly one material assigned."
            )
            return
        self.ui.cmb002.init_slot()
        index = self.ui.cmb002.items.index(mats[0]) if mats[0] in self.ui.cmb002.items else -1
        if index >= 0:
            self.ui.cmb002.setCurrentIndex(index)

    @btk.undoable
    def b004(self, widget):
        """Assign Random"""
        selection = self.selected_objects()
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return
        new_mat = btk.create_mat("random")
        btk.assign_mat(selection, new_mat)
        # Drop the previous random material once nothing uses it.
        last = self.last_random_material
        if last and last is not new_mat and last.users == 0:
            bpy.data.materials.remove(last)
        self.last_random_material = new_mat
        self.ui.cmb002.init_slot()

    @btk.undoable
    def b005(self, widget):
        """Assign Current"""
        selection = self.selected_objects()
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return
        mat = self.ui.cmb002.currentData()
        if mat is None:
            self.sb.message_box("No material selected in the materials list.")
            return
        btk.assign_mat(selection, mat)

    @btk.undoable
    def b006(self, widget):
        """Assign New Material"""
        selection = self.selected_objects()
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return
        mat = btk.create_mat("standard", name="Material")
        btk.assign_mat(selection, mat)
        self.ui.cmb002.init_slot()

    def b013(self):
        """Reload Textures"""
        btk.reload_textures()
        self.sb.message_box("Textures reloaded from disk.")

    # ------------------------------------------------------------------ list000  Assign list
    def list000_init(self, widget):
        """Assign list: scene materials + New + Random."""
        widget.refresh_on_show = True
        widget.fixed_item_height = 18
        widget.apply_preset("expand_right")
        widget.clear()
        root = widget.add("Assign")
        root.sublist.add(["New", "Random"])
        mats = [m.name for m in bpy.data.materials if not m.is_grease_pencil]
        if mats:
            root.sublist.add(sorted(mats))

    @Signals("on_item_interacted")
    def list000(self, item):
        """Assign the picked material (or a New/Random one) to the selection."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        if text == "New":
            self.b006(None)
        elif text == "Random":
            self.b004(None)
        else:
            mat = bpy.data.materials.get(text)
            if mat is not None:
                selection = self.selected_objects()
                if not selection:
                    self.sb.message_box("No renderable object is selected for assignment.")
                    return
                btk.assign_mat(selection, mat)

    # ------------------------------------------------------------------ hidden (Maya-only tools)
    def list001_init(self, widget):
        """Tools list — Maya-only windows (Stingray/game shader/Arnold bridge); hidden."""
        widget.setVisible(False)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
