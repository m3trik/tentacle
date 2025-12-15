# !/usr/bin/python
# coding=utf-8
import re

try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk

# From this package
from tentacle.slots.maya import SlotsMaya


class MaterialsSlots(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.materials
        self.submenu = self.sb.loaded_ui.materials_submenu

        # Set a class attribute to track the last created random material
        self.last_random_material = None

    def header_init(self, widget):
        """ """
        # Add a button to reload all textures in the scene.
        widget.menu.add(
            "QPushButton",
            setText="Reload Scene Textures",
            setObjectName="b013",
            setToolTip="Reload file textures for all scene materials.",
        )
        # Add a button to open the hypershade editor.
        widget.menu.add(
            "QPushButton",
            setToolTip="Open the Hypershade Window.",
            setText="Hypershade Editor",
            setObjectName="b007",
        )
        # Add a button to launch stringray arnold shader.
        widget.menu.add(
            "QPushButton",
            setToolTip="Create a stingray material network that can optionally be rendered in Arnold.",
            setText="Create Stingray Shader",
            setObjectName="b009",
        )
        # Add a button to launch the shader templates UI.
        widget.menu.add(
            "QPushButton",
            setToolTip="Open the Shader Templates UI to save and load shader graphs.",
            setText="Shader Templates",
            setObjectName="b011",
        )
        # Add a button to launch the Texture Path Editor.
        widget.menu.add(
            "QPushButton",
            setToolTip="Edit texture paths for materials in the scene.",
            setText="Texture Path Editor",
            setObjectName="b010",
        )
        # Add a button to launch map converter.
        widget.menu.add(
            "QPushButton",
            setToolTip="Convert existing texture maps to another type.",
            setText="Map Converter",
            setObjectName="b016",
        )
        widget.menu.add(
            "QPushButton",
            setText="Map Packer",
            setObjectName="b008",
            setToolTip="Pack up to 4 input grayscale maps into specified RGBA channels.",
        )

    def cmb002_init(self, widget):
        """ """
        if not widget.is_initialized:
            widget.refresh_on_show = True  # Call this method on show
            widget.editable = True
            widget.menu.setTitle("Material Options")
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Rename",
                setObjectName="lbl005",
                setToolTip="Rename the current material.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Rename (strip trailing ints)",
                setObjectName="lbl007",
                setToolTip="Rename the current material by removing trailing digits if present.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Delete",
                setObjectName="lbl002",
                setToolTip="Delete the current material.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Select Node",
                setObjectName="lbl004",
                setToolTip="Select the material node and show its attributes in the attribute editor.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Open in Editor",
                setObjectName="lbl006",
                setToolTip="Open the material in the hypershade editor.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Remove Duplicate Materials",
                setObjectName="b014",
                setToolTip="Find duplicate materials, remove duplicates, and reassign them to the original material.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Delete All Unused Materials",
                setObjectName="b015",
                setToolTip="Delete all unused materials.",
            )
            # Rename the material after editing has finished.
            widget.on_editing_finished.connect(
                lambda text: pm.rename(widget.currentData(), text)
            )
            # Initialize the widget every time before the popup is shown.
            widget.before_popup_shown.connect(widget.init_slot)
            # Update the assign button with the new material name.
            widget.on_editing_finished.connect(self.submenu.b005.init_slot)
            # Add the current material name to the assign button.
            widget.currentIndexChanged.connect(self.submenu.b005.init_slot)

        # Use 'restore_index=True' to save and restore the index
        materials_dict = mtk.get_scene_mats(
            exc="standardSurface", sort=True, as_dict=True
        )
        widget.add(materials_dict, clear=True, restore_index=True)

        # Create and set icons with color swatch
        for i, mat in enumerate(widget.items):
            icon = mtk.get_mat_swatch_icon(mat)
            if icon:
                widget.setItemIcon(i, icon)

    def lbl007(self):
        """Rename the current material by stripping trailing integers.

        - Compute new name by removing trailing digits from the current name.
        - Abort if the new name already exists or if nothing to change.
        - Refresh UI and keep selection on the renamed material.
        """
        mat = self.ui.cmb002.currentData()
        if not mat:
            return

        old_name = mat.name()
        new_name = re.sub(r"\d+$", "", old_name)

        # If stripping results in no change
        if new_name == old_name:
            self.sb.message_box(
                "<hl>No trailing integers</hl><br>No trailing integers to strip; rename not performed."
            )
            return

        # If stripping removes all characters
        if not new_name:
            self.sb.message_box(
                "<hl>Invalid new name</hl><br>Stripping digits results in an empty name. Rename aborted."
            )
            return

        # Ensure the target name doesn't already exist
        if pm.objExists(new_name):
            self.sb.message_box(
                f"<hl>Rename aborted</hl><br>A node named '<strong>{new_name}</strong>' already exists."
            )
            return

        try:
            pm.rename(mat, new_name)
        except Exception as e:
            self.sb.message_box(f"<hl>Rename failed</hl><br>{e}")
            return

        # Refresh the materials list and keep current selection on the new name
        self.ui.cmb002.init_slot()
        self.ui.cmb002.setAsCurrent(new_name)
        # Update the assign button text/icon
        self.submenu.b005.init_slot()

    def tb000_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Shell",
            setObjectName="chk005",
            setToolTip="Select object(s) containing the material.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Search in Selection Only",
            setObjectName="chk006",
            setChecked=False,
            setToolTip="When checked, search only within currently selected objects (if nothing is selected will default to all objects)\nWhen unchecked, always search all objects in the scene.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Get and Select",
            setObjectName="chk007",
            setChecked=False,
            setToolTip="When checked, first get the material from the current viewport selection and set it as the current material, then perform the selection.",
        )

    def tb000(self, widget):
        """Select By Material"""
        get_and_select = (
            widget.option_box.menu.chk007.isChecked()
        )  # Get and select option

        # If get_and_select is enabled, first get the material from current selection
        if get_and_select:
            selection = pm.ls(sl=True)
            if selection:
                mat = mtk.get_mats(selection[0])
                if len(mat) == 1:
                    # Refresh the materials list and set the found material as current
                    self.ui.cmb002.init_slot()
                    self.ui.cmb002.setAsCurrent(mat.pop().name())
                elif len(mat) == 0:
                    print(
                        "Get material failed: No material found on selected object. Proceeding with current material."
                    )
                    self.sb.message_box(
                        "<hl>No material found</hl><br>Selected object has no material assigned. Proceeding with current material."
                    )
                else:
                    print(
                        "Get material failed: Multiple materials found on selected object. Proceeding with current material."
                    )
                    self.sb.message_box(
                        "<hl>Multiple materials found</hl><br>Selected object has multiple materials assigned. Cannot determine single material. Proceeding with current material."
                    )
            else:
                print(
                    "Get material failed: Nothing selected. Proceeding with current material."
                )
                self.sb.message_box(
                    "<hl>Nothing selected</hl><br>Select mesh object(s) or face(s) to get material from. Proceeding with current material."
                )

        mat = self.ui.cmb002.currentData()
        if not mat:
            return

        shell = widget.option_box.menu.chk005.isChecked()  # Select by material: shell
        search_in_selection_only = (
            widget.option_box.menu.chk006.isChecked()
        )  # Search in selection only

        if search_in_selection_only:
            selection = pm.ls(sl=True, objectsOnly=True)
        else:
            selection = None  # Search all objects in the scene

        faces_with_mat = mtk.find_by_mat_id(mat, selection, shell=shell)

        pm.select(faces_with_mat)

    def lbl002(self):
        """Delete Material"""
        mat = self.ui.cmb002.currentData()  # get the mat obj from cmb002
        mat = pm.delete(mat)
        self.ui.cmb002.init_slot()  # refresh the materials list comboBox

    def b015(self, widget):
        """Delete Unused Materials"""
        pm.mel.hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes")
        self.ui.cmb002.init_slot()  # refresh the materials list comboBox

    def lbl004(self):
        """Select and Show Attributes: Show Material Attributes in the Attribute Editor."""
        mat = self.ui.cmb002.currentData()  # get the mat obj from cmb002
        pm.select(mat, replace=True)
        pm.mel.eval(f'showEditorExact("{mat}")')

    def lbl005(self):
        """Set the current combo box text as editable."""
        self.ui.cmb002.setEditable(True)
        self.ui.cmb002.option_box.menu.hide()

    def lbl006(self):
        """Open material in editor"""
        try:
            mat = self.ui.cmb002.currentData()
        except Exception:
            self.sb.message_box("No stored material or no valid object selected.")
            return

        if not mat:
            self.sb.message_box("No stored material or no valid object selected.")
            return

        mtk.graph_materials(mat)

    def b002(self, widget):
        """Get Material: Change the index to match the current material selection."""
        selection = pm.ls(sl=True)
        if not selection:
            self.sb.message_box(
                "<hl>Nothing selected</hl><br>Select mesh object(s) or face(s)."
            )
            return

        mat = mtk.get_mats(selection[0])
        if len(mat) != 1:
            self.sb.message_box(
                "<hl>Invalid selection</hl><br>Selection must have exactly one material assigned."
            )
            return

        self.ui.cmb002.init_slot()  # refresh the materials list comboBox
        self.ui.cmb002.setAsCurrent(mat.pop().name())  # pop: mat is a set

    def b004(self, widget):
        """Assign: Assign Random"""
        selection = pm.ls(sl=True, flatten=True)
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return

        # Create and assign a new random material
        new_mat = mtk.create_mat("random")
        mtk.assign_mat(selection, new_mat)

        # Check and delete the last random material if it's no longer in use
        if self.last_random_material and self.last_random_material != new_mat:
            # Check all shading engines connected to the last random material
            shading_engines = pm.listConnections(
                self.last_random_material, type="shadingEngine"
            )

            # Iterate through each shading engine to check if any geometry is connected
            is_in_use = False
            for se in shading_engines:
                if pm.listConnections(se, type="mesh"):
                    is_in_use = True
                    break

            # If the last random material is not in use, delete it
            if not is_in_use:
                pm.delete(self.last_random_material)

        # Update the last random material with the newly created one
        self.last_random_material = new_mat

        # Refresh the UI
        self.ui.cmb002.init_slot()
        self.ui.cmb002.setAsCurrent(new_mat.name())

        # Reselect the original selection so that this method can be called again if needed.
        pm.select(selection)

    def b005_init(self, widget):
        """ """
        if not widget.is_initialized:
            widget.refresh_on_show = True  # Call this method on show
            self.ui.cmb002.init_slot()
            self.ui.cmb002.is_initialized = True

        current_material = self.ui.cmb002.currentData()
        text = f"Assign: {current_material}"
        submenu_widget = self.submenu.b005
        submenu_widget.setText(text)
        submenu_widget.setMinimumWidth(submenu_widget.minimumSizeHint().width() + 25)
        if current_material:
            icon = mtk.get_mat_swatch_icon(current_material, [15, 15])
            if icon is not None:
                submenu_widget.setIcon(icon)

    def b005(self, widget):
        """Assign: Assign Current"""
        selection = pm.ls(sl=True, flatten=1)
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return

        mat = self.ui.cmb002.currentData()
        mtk.assign_mat(selection, mat)

    def b006(self, widget):
        """Assign: New Material"""
        renderable_objects = pm.ls(sl=True, type="mesh", dag=True, geometry=True)
        if not renderable_objects:
            self.sb.message_box("No renderable object is selected for assignment.")
            return
        pm.mel.eval(
            'buildObjectMenuItemsNow "MainPane|viewPanes|modelPanel4|modelPanel4|modelPanel4|modelPanel4ObjectPop";'
        )
        pm.mel.createAssignNewMaterialTreeLister("")

    def b007(self, widget):
        """Hypershade Editor"""
        pm.mel.HypershadeWindow()

    def b008(self, widget):
        """Map Packer"""
        from pythontk.img_utils import map_packer

        self.sb.register(
            "map_packer.ui",
            map_packer.MapPackerSlots,
            base_dir=map_packer,
        )

        ui = self.sb.get_ui("map_packer")
        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="translucentBgWithBorder")
        ui.header.config_buttons("menu", "hide")

        # Set the starting directory for the map converter
        source_images_dir = mtk.get_env_info("sourceimages")
        ui.slots.source_dir = source_images_dir

        self.sb.parent().show(ui)

    def b009(self, widget):
        """Create Stingray Shader"""
        ui = mtk.UiManager.instance(self.sb).get("stingray_arnold_shader")
        self.sb.parent().show(ui)

    def b010(self, widget):
        """Texture Path Editor"""
        ui = mtk.UiManager.instance(self.sb).get("texture_path_editor")
        self.sb.parent().show(ui)

    def b011(self, widget):
        """Shader Templates"""
        ui = mtk.UiManager.instance(self.sb).get("shader_templates")
        self.sb.parent().show(ui)

    def b013(self):
        """Reload Textures"""
        mtk.reload_textures()  # pm.mel.AEReloadAllTextures()
        confirmation_message = "<html><body><p style='font-size:16px; color:yellow;'>Textures are <strong>reloading ..</strong>.</p></body></html>"
        self.sb.message_box(confirmation_message)

    def b014(self):
        """Remove and Reassign Duplicates"""
        dups = mtk.find_materials_with_duplicate_textures()
        if dups:
            mtk.reassign_duplicate_materials(dups, delete=True)
            self.ui.cmb002.init_slot()

    def b016(self):
        """Map Converter"""
        from pythontk.img_utils import map_converter

        self.sb.register(
            "map_converter.ui",
            map_converter.MapConverterSlots,
            base_dir=map_converter,
        )

        ui = self.sb.get_ui("map_converter")
        ui.set_attributes(WA_TranslucentBackground=True)
        ui.set_flags(FramelessWindowHint=True)
        ui.style.set(theme="dark", style_class="translucentBgWithBorder")
        ui.header.config_buttons("menu", "hide")

        # Set the starting directory for the map converter
        source_images_dir = mtk.get_env_info("sourceimages")
        ui.slots.source_dir = source_images_dir

        self.sb.parent().show(ui)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
