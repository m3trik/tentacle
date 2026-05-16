# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
import pythontk as ptk

# From this package:
from tentacle.slots.maya._slots_maya import SlotsMaya


class MaterialsSlots(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.materials
        self.submenu = self.sb.loaded_ui.materials_submenu

        # Set a class attribute to track the last created random material
        self.last_random_material = None

    def header_init(self, widget):
        """Initialize the header menu"""
        # Section: Utilities
        widget.menu.add("Separator", setTitle="Utilities")
        widget.menu.add(
            "QPushButton",
            setText="Reload Scene Textures",
            setObjectName="b013",
            setToolTip="Reload file textures for all scene materials.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Print Texture Info",
            setObjectName="b017",
            setToolTip="Print information about all texture files in the scene to the script editor.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Hypershade Editor",
            setObjectName="b007",
            setToolTip="Open the Hypershade Window.",
            clicked=lambda: mel.eval("HypershadeWindow"),
        )
        # Section: Setup
        widget.menu.add("Separator", setTitle="Setup")
        widget.menu.add(
            "QPushButton",
            setText="Image to Plane",
            setObjectName="b021",
            setToolTip="Create textured polygon planes from image files with correct aspect ratios.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Material Updater",
            setObjectName="b018",
            setToolTip="Update material networks with new textures and settings.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Shader Templates",
            setObjectName="b011",
            setToolTip="Open the Shader Templates UI to save and load shader graphs.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Texture Path Editor",
            setObjectName="b010",
            setToolTip="Edit texture paths for materials in the scene.",
        )
        # Section: Conversion
        widget.menu.add("Separator", setTitle="Conversion")
        widget.menu.add(
            "QPushButton",
            setText="Game Shader",
            setObjectName="b009",
            setToolTip="Create an exportable game shader network that can optionally be rendered in Arnold.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Map Converter",
            setObjectName="b016",
            setToolTip="Convert existing texture maps to another type.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Map Packer",
            setObjectName="b008",
            setToolTip="Pack up to 4 input grayscale maps into specified RGBA channels.",
        )
        # Section: External Tools
        widget.menu.add("Separator", setTitle="External Tools")
        widget.menu.add(
            "QPushButton",
            setText="Marmoset Bridge",
            setObjectName="b019",
            setToolTip=(
                "Open the Marmoset Toolbag bridge: pick a template "
                "(import / bake / lookdev), tune parameters, then send "
                "the selection to Toolbag."
            ),
        )
        widget.menu.add(
            "QPushButton",
            setText="Send to Substance Painter",
            setObjectName="b020",
            setToolTip="Export selection to Adobe Substance 3D Painter.",
        )

    def cmb002_init(self, widget):
        """Initialize Materials"""
        if not widget.is_initialized:
            widget.refresh_on_show = True  # Call this method on show
            widget.editable = True
            widget.menu.add("Separator", setTitle="Edit")
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Rename",
                setObjectName="lbl005",
                setToolTip="Rename the current material.",
            )
            lbl007 = widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Rename (strip trailing ints & _)",
                setObjectName="lbl007",
                setToolTip="Rename the current material by removing trailing digits and underscores if present.",
            )
            lbl007.option_box.set_action(
                callback=self.lbl007_global,
                icon="list",
                tooltip="Strip trailing ints & _ from ALL scene materials.",
            )
            # Toggle: how same-base name conflicts are resolved.
            # Off (default): skip conflicting groups (legacy behavior).
            # On: rename group members with alphabetical suffixes (mat_A, mat_B, ...).
            from uitk.widgets.optionBox.options.action import ActionOption

            self._strip_alpha_option = ActionOption(
                wrapped_widget=lbl007,
                callback=None,
                states=[
                    {
                        "icon": "font",
                        "tooltip": (
                            "Name conflicts: <strong>skip</strong> (default).<br>"
                            "Click to resolve conflicts with alphabetical suffixes "
                            "(mat_A, mat_B, mat_C, ...)."
                        ),
                    },
                    {
                        "icon": "font",
                        "color": "#5fb878",
                        "tooltip": (
                            "Name conflicts: <strong>alphabetical</strong> "
                            "(mat_A, mat_B, mat_C, ...).<br>"
                            "Click to disable and skip conflicts instead."
                        ),
                    },
                ],
                settings_key="materials_strip_collision_alpha",
            )
            lbl007.option_box.add_option(self._strip_alpha_option)
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="Delete",
                setObjectName="lbl002",
                setToolTip="Delete the current material.",
            )
            # Section: View / Select
            widget.menu.add("Separator", setTitle="View / Select")
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
            # Section: Cleanup
            widget.menu.add("Separator", setTitle="Cleanup")
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
                lambda text: cmds.rename(str(widget.currentData()), text)
            )
            # Initialize the widget every time before the popup is shown.
            widget.before_popup_shown.connect(widget.init_slot)
            # Update the assign button with the new material name.
            widget.on_editing_finished.connect(self.submenu.b005.init_slot)
            # Add the current material name to the assign button.
            widget.currentIndexChanged.connect(self.submenu.b005.init_slot)

        # Use 'restore_index=True' to save and restore the index
        materials_dict = mtk.MatUtils.get_scene_mats(
            exc="standardSurface", sort=True, as_dict=True
        )
        widget.add(materials_dict, clear=True, restore_index=True)

        # Create and set icons with color swatch
        for i, mat in enumerate(widget.items):
            icon = mtk.MatUtils.get_mat_swatch_icon(mat)
            if icon:
                widget.setItemIcon(i, icon)

    def _collision_mode_is_alpha(self):
        """Read the persistent toggle on the lbl007 option box.

        Returns True when same-base name conflicts should be resolved with
        alphabetical suffixes (mat_A, mat_B, ...) rather than skipped.
        """
        opt = getattr(self, "_strip_alpha_option", None)
        return bool(opt and opt.current_state == 1)

    def _strip_material_names(self, materials):
        """Strip trailing ints/underscores across the given materials and apply renames.

        Delegates the strip + collision-resolution logic to
        ``pythontk.StrUtils.resolve_name_collisions``. The option-box toggle
        controls whether multi-member groups get alphabetical suffixes
        (``mat_A``, ``mat_B``, ...) or are skipped. Single-member groups
        always strip to base.

        Parameters:
            materials: Iterable of Maya material nodes.

        Returns:
            dict with keys:
                renamed: list[(old_name, new_name)] successfully renamed.
                no_change: list[old_name] that needed no strip (already at base
                    in a singleton group, or skipped because of toggle-off conflict).
                conflicts: list[old_name] whose target collided with a non-input
                    scene node.
                failed: list[str] error messages from cmds.rename failures.
        """
        materials = list(materials)
        name_to_mat = {str(m).rsplit("|", 1)[-1]: m for m in materials}
        candidates = list(name_to_mat.keys())

        rename_map = ptk.StrUtils.resolve_name_collisions(
            candidates,
            strip="_",
            strip_trailing_ints=True,
            collision_suffix="alpha" if self._collision_mode_is_alpha() else None,
        )

        renamed, conflicts, failed = [], [], []
        no_change = [n for n in candidates if n not in rename_map]
        candidate_set = set(candidates)

        for old_name, new_name in rename_map.items():
            # Allow the rename if the target collides only with another candidate
            # (which will itself be renamed away), but not with an unrelated node.
            if new_name not in candidate_set and cmds.objExists(new_name):
                conflicts.append(old_name)
                continue
            try:
                cmds.rename(str(name_to_mat[old_name]), new_name)
                renamed.append((old_name, new_name))
            except Exception as e:
                failed.append(f"{old_name}: {e}")

        return {
            "renamed": renamed,
            "no_change": no_change,
            "conflicts": conflicts,
            "failed": failed,
        }

    def _refresh_after_rename(self, current_old, renamed):
        """Refresh the materials combo and restore selection on the current mat."""
        self.ui.cmb002.init_slot()
        for old, new in renamed:
            if old == current_old:
                self.ui.cmb002.setAsCurrent(new)
                break
        self.submenu.b005.init_slot()

    def lbl007(self):
        """Rename the current material by stripping trailing integers and underscores.

        With the option-box alpha toggle ON, the current material's collision
        group (other materials sharing the same stripped base) is renamed
        alphabetically together so the convention stays consistent. With the
        toggle OFF, only the current material is renamed and the operation
        aborts on conflict.
        """
        mat = self.ui.cmb002.currentData()
        if not mat:
            return

        old_name = str(mat).rsplit("|", 1)[-1]
        target_base = ptk.StrUtils.format_suffix(
            old_name, strip="_", strip_trailing_ints=True
        )
        if not target_base:
            self.sb.message_box(
                "<hl>Invalid new name</hl><br>Stripping suffix results in an empty name. Rename aborted."
            )
            return

        # Scope the operation: alpha mode renames the whole group; skip mode renames just the current.
        if self._collision_mode_is_alpha():
            all_materials = mtk.MatUtils.get_scene_mats(
                exc="standardSurface", sort=True
            )
            scope = [
                m
                for m in all_materials
                if ptk.StrUtils.format_suffix(
                    str(m).rsplit("|", 1)[-1], strip="_", strip_trailing_ints=True
                )
                == target_base
            ]
        else:
            scope = [mat]

        result = self._strip_material_names(scope)

        if old_name in result["no_change"]:
            self.sb.message_box(
                "<hl>No trailing suffix</hl><br>No trailing integers or underscores to strip; rename not performed."
            )
            return
        if old_name in result["conflicts"]:
            self.sb.message_box(
                f"<hl>Rename aborted</hl><br>A node named '<strong>{target_base}</strong>' already exists."
            )
            return
        if result["failed"]:
            self.sb.message_box(f"<hl>Rename failed</hl><br>{result['failed'][0]}")
            return

        self._refresh_after_rename(old_name, result["renamed"])

    def lbl007_global(self):
        """Rename ALL scene materials by stripping trailing integers and underscores.

        Same-base groups are resolved per the option-box alpha toggle: skipped
        (default) or renamed with alphabetical suffixes (mat_A, mat_B, mat_C, ...).
        Reports a summary at the end.
        """
        materials = list(
            mtk.MatUtils.get_scene_mats(exc="standardSurface", sort=True)
        )
        if not materials:
            self.sb.message_box(
                "<hl>No materials</hl><br>No materials found in scene."
            )
            return

        current = self.ui.cmb002.currentData()
        current_old = str(current).rsplit("|", 1)[-1] if current else None

        result = self._strip_material_names(materials)
        self._refresh_after_rename(current_old, result["renamed"])

        mode = "alpha" if self._collision_mode_is_alpha() else "skip"
        self.sb.message_box(
            f"<hl>Strip trailing — global ({mode})</hl><br>"
            f"Renamed: <strong>{len(result['renamed'])}</strong><br>"
            f"No change: <strong>{len(result['no_change'])}</strong><br>"
            f"Conflicts: <strong>{len(result['conflicts'])}</strong><br>"
            f"Failed: <strong>{len(result['failed'])}</strong>"
        )

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
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Add to Selection",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="When checked, add matches to the existing selection instead of replacing it.",
        )

    def tb000(self, widget):
        """Select By Material"""
        get_and_select = (
            widget.option_box.menu.chk007.isChecked()
        )  # Get and select option
        add_to_selection = widget.option_box.menu.chk008.isChecked()
        prior_selection = cmds.ls(sl=True, flatten=True) or []

        # If get_and_select is enabled, first get the material from current selection
        if get_and_select:
            selection = cmds.ls(sl=True) or []
            if selection:
                mat = mtk.MatUtils.get_mats(selection[0])
                if len(mat) == 1:
                    # Refresh the materials list and set the found material as current
                    self.ui.cmb002.init_slot()
                    self.ui.cmb002.setAsCurrent(str(mat.pop()))
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
            selection = cmds.ls(sl=True, objectsOnly=True) or []
        else:
            selection = None  # Search all objects in the scene

        faces_with_mat = mtk.MatUtils.find_by_mat_id(mat, selection, shell=shell)

        if not faces_with_mat:
            print(f"No objects found with material: {mat}")
            self.sb.message_box(
                f"<hl>No matches</hl><br>No objects found with material '<strong>{mat}</strong>'."
            )
            return

        if add_to_selection and prior_selection:
            cmds.select(prior_selection, replace=True)
            cmds.select(faces_with_mat, add=True)
        else:
            cmds.select(faces_with_mat)

    def lbl002(self):
        """Delete Material"""
        mat = self.ui.cmb002.currentData()  # get the mat obj from cmb002
        cmds.delete(str(mat))
        self.ui.cmb002.init_slot()  # refresh the materials list comboBox

    def b015(self, widget):
        """Delete Unused Materials"""
        mel.eval('hyperShadePanelMenuCommand "hyperShadePanel1" "deleteUnusedNodes"')
        self.ui.cmb002.init_slot()  # refresh the materials list comboBox

    def lbl004(self):
        """Select and Show Attributes: Show Material Attributes in the Attribute Editor."""
        mat = self.ui.cmb002.currentData()  # get the mat obj from cmb002
        cmds.select(str(mat), replace=True)
        mel.eval(f'showEditorExact("{mat}")')

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

        mtk.MatUtils.graph_materials(mat)

    def b002(self, widget):
        """Get Material: Change the index to match the current material selection."""
        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<hl>Nothing selected</hl><br>Select mesh object(s) or face(s)."
            )
            return

        mat = mtk.MatUtils.get_mats(selection[0])
        if len(mat) != 1:
            self.sb.message_box(
                "<hl>Invalid selection</hl><br>Selection must have exactly one material assigned."
            )
            return

        self.ui.cmb002.init_slot()  # refresh the materials list comboBox
        self.ui.cmb002.setAsCurrent(str(mat.pop()))  # pop: mat is a set

    def b004(self, widget):
        """Assign Random"""
        selection = cmds.ls(sl=True, flatten=True) or []
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return

        # Create and assign a new random material
        new_mat = mtk.MatUtils.create_mat("random")
        mtk.MatUtils.assign_mat(selection, new_mat)

        # Check and delete the last random material if it's no longer in use
        if self.last_random_material and self.last_random_material != new_mat:
            # Check all shading engines connected to the last random material
            shading_engines = cmds.listConnections(
                str(self.last_random_material), type="shadingEngine"
            ) or []

            # Iterate through each shading engine to check if any geometry is connected
            is_in_use = False
            for se in shading_engines:
                if cmds.listConnections(se, type="mesh"):
                    is_in_use = True
                    break

            # If the last random material is not in use, delete it
            if not is_in_use:
                cmds.delete(str(self.last_random_material))

        # Update the last random material with the newly created one
        self.last_random_material = new_mat

        # Refresh the UI
        self.ui.cmb002.init_slot()
        self.ui.cmb002.setAsCurrent(str(new_mat))

        # Reselect the original selection so that this method can be called again if needed.
        cmds.select(selection)

    def b005_init(self, widget):
        """Initialize Assign Current"""
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
            icon = mtk.MatUtils.get_mat_swatch_icon(current_material, [15, 15])
            if icon is not None:
                submenu_widget.setIcon(icon)

    def b005(self, widget):
        """Assign Current"""
        selection = cmds.ls(sl=True, flatten=1) or []
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return

        mat = self.ui.cmb002.currentData()
        mtk.MatUtils.assign_mat(selection, mat)

    def b006(self, widget):
        """Assign: New Material"""
        renderable_objects = cmds.ls(sl=True, type="mesh", dag=True, geometry=True) or []
        if not renderable_objects:
            self.sb.message_box("No renderable object is selected for assignment.")
            return
        mel.eval(
            'buildObjectMenuItemsNow "MainPane|viewPanes|modelPanel4|modelPanel4|modelPanel4|modelPanel4ObjectPop";'
        )
        mel.eval('createAssignNewMaterialTreeLister ""')

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
        ui.header.config_buttons("menu", "minimize", "hide")

        # Set the starting directory for the map converter
        source_images_dir = mtk.get_env_info("sourceimages")
        ui.slots.source_dir = source_images_dir

        self.sb.handlers.marking_menu.show(ui)

    def b009(self, widget):
        """Create Game Shader"""
        self.sb.handlers.marking_menu.show("game_shader")

    def b010(self, widget):
        """Texture Path Editor"""
        self.sb.handlers.marking_menu.show("texture_path_editor")

    def b011(self, widget):
        """Shader Templates"""
        self.sb.handlers.marking_menu.show("shader_templates")

    def b013(self):
        """Reload Textures and Reset Viewport"""
        mtk.MatUtils.reload_textures()
        mtk.DisplayUtils.reset_viewport()
        confirmation_message = "<html><body><p style='font-size:16px; color:yellow;'>Textures Reloaded & Viewport Reset.</p></body></html>"
        self.sb.message_box(confirmation_message)

    def b014(self):
        """Remove and Reassign Duplicates"""
        dups = mtk.MatUtils.find_materials_with_duplicate_textures()
        if dups:
            mtk.MatUtils.reassign_duplicate_materials(dups, delete=True)
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
        ui.header.config_buttons("menu", "minimize", "hide")

        # Set the starting directory for the map converter
        source_images_dir = mtk.get_env_info("sourceimages")
        ui.slots.source_dir = source_images_dir

        def _selected_texture_paths():
            sel = cmds.ls(selection=True, long=True) or []
            return mtk.MatUtils.get_texture_paths(objects=sel) if sel else []

        ui.slots.texture_provider = _selected_texture_paths

        self.sb.handlers.marking_menu.show(ui)

    def b017(self, widget):
        """Print Texture Info"""
        info_list = mtk.MatUtils.get_texture_info()

        print(f"\n{'='*60}")
        print(f"Found {len(info_list)} valid textures in scene.")
        print(f"{'='*60}")

        for info in info_list:
            print(f"Name: {info['name']}")
            print(f"  Path:   {info['path']}")
            print(f"  Size:   {info['size']:,} bytes")
            print(f"  Res:    {info['width']}x{info['height']}")
            print(f"  Mode:   {info['mode']}")
            print(f"  Format: {info['format']}")
            print("-" * 40)

        self.sb.message_box(
            f"Printed info for {len(info_list)} textures to Script Editor."
        )

    def b018(self, widget):
        """Material Updater"""
        self.sb.handlers.marking_menu.show("mat_updater")

    def b021(self, widget):
        """Image to Plane"""
        self.sb.handlers.marking_menu.show("image_to_plane")

    def b019(self, widget):
        """Marmoset Bridge"""
        self.sb.handlers.marking_menu.show("marmoset_bridge")

    def b020(self, widget):
        """Send to Substance Painter"""
        try:
            from mayatk.mat_utils.substance import SubstanceBridge

            bridge = SubstanceBridge()
            exported_fbx = bridge.send(headless=False)
            if exported_fbx:
                print(f"Substance Painter Export Successful: {exported_fbx}")
        except Exception as e:
            print(f"Substance Painter Export Failed: {e}")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
