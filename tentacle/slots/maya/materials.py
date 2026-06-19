# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
import pythontk as ptk
from uitk import Signals
# From this package:
from tentacle.slots.maya._slots_maya import SlotsMaya


class MaterialsSlots(SlotsMaya):
    # Submenu Tools list — categories group tools by *what they act on* so the
    # similarly-named texture tools stop reading as interchangeable:
    #   "Materials (scene)"  — mutate the live shading network.
    #   "Texture Maps (files)" — operate on texture files on disk.
    # Each entry is (label, slot_name, tooltip); the slot stays on this class so
    # marking-menu and other entry points can still reach it. Tooltip may be "".
    _TOOLS_ITEMS = {
        "Setup": [
            ("Image to Plane", "b021", ""),
            ("Shader Templates", "b011", ""),
            ("Texture Path Editor", "b010", ""),
        ],
        "Materials (scene)": [
            (
                "Update Materials",
                "b018",
                "Reprocess the textures on selected (or all) scene materials "
                "and re-wire the results back into their shading networks "
                "(standardSurface / StingrayPBS / aiStandardSurface). Works "
                "in-scene — it modifies materials. For per-file work on the "
                "textures themselves, use Map Converter under Texture Maps.",
            ),
            (
                "Game Shader",
                "b009",
                "Build a StingrayPBS game-shader network from texture maps.",
            ),
            (
                "Arnold Preview Shader",
                "b026",
                "Create a parallel aiStandardSurface so materials preview "
                "correctly under Arnold in Maya.",
            ),
        ],
        "Texture Maps (files)": [
            (
                "Map Converter",
                "b016",
                "Standalone texture-file toolbox: convert formats, resize / "
                "optimize, normal-map DirectX↔OpenGL, spec-gloss→PBR, "
                "and pack / unpack ORM · MRAO · MSAO. Operates on files "
                "on disk (or the selection's textures) — it does not modify "
                "materials.",
            ),
            (
                "Map Packer",
                "b008",
                "Pack up to four separate channel maps into combined RGBA "
                "textures (ORM, mask maps, …) across texture sets.",
            ),
        ],
        "External": [
            ("Marmoset Bridge", "b019", ""),
            ("Substance Bridge", "b020", ""),
            ("Map Compositor", "b022", ""),
            ("Metashape Workflow", "b023", ""),
            ("RealityCapture Workflow", "b024", ""),
            ("Brush Splat Workflow", "b025", ""),
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.materials
        self.submenu = self.sb.loaded_ui.materials_submenu

        # Set a class attribute to track the last created random material
        self.last_random_material = None
        # External tools (map_compositor, metashape_workflow) are
        # registered up-front in tcl_maya.TclMaya.__init__ so they
        # appear in the UI browser without first loading this UI.

    def header_init(self, widget):
        """Initialize the header menu (Utilities only — Setup/Conversion/External live in the submenu Tools list)."""
        widget.menu.add("Separator", setTitle="Utilities")
        widget.menu.add(
            "QPushButton",
            setText="Reload Scene Textures",
            setObjectName="b013",
            setToolTip="Reload file textures for all scene materials.",
        )
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setText="Get Material Info",
            setObjectName="tb001",
            setToolTip=(
                "Show a formatted report of textures, sizes, bit depth, "
                "file size, and optimization recommendations. Scope "
                "(textures, current material, all materials, selected "
                "objects), default-material / unassigned filters, and "
                "which fields to include are set via the option box."
            ),
        )
        widget.menu.add(
            "QPushButton",
            setText="Hypershade Editor",
            setObjectName="b007",
            setToolTip="Open the Hypershade Window.",
            clicked=lambda: mel.eval("HypershadeWindow"),
        )

    # --- Submenu Assign list -------------------------------------------

    def list000_init(self, widget):
        """Assign list: scene materials + 'New' + 'Random'.

        Re-populated on every show so the list reflects the current scene
        contents and the current cmb002 selection. The root mirrors the
        current material; releasing on it assigns that material.
        """
        if not getattr(widget, "_assign_list_configured", False):
            widget.refresh_on_show = True
            widget.fixed_item_height = 18
            widget.apply_preset("expand_right")
            widget._assign_list_configured = True
            # Ensure cmb002 is populated so we can read currentData below.
            if not getattr(self.ui.cmb002, "is_initialized", False):
                self.ui.cmb002.init_slot()
                self.ui.cmb002.is_initialized = True

        widget.clear()

        current = self.ui.cmb002.currentData()
        root_text = f"Assign: {current}" if current else "Assign"
        root = widget.add(root_text)
        root.sublist.setMinimumWidth(widget.width() or 160)

        # Special actions first
        root.sublist.add("New")
        root.sublist.add("Random")

        # Then every scene material, sorted
        scene_mats = mtk.MatUtils.get_scene_mats(
            exc="standardSurface", sort=True
        ) or []
        for mat in scene_mats:
            root.sublist.add(str(mat))

    @Signals("on_item_interacted")
    def list000(self, item):
        """Dispatch Assign list selection.

        - Releasing on the root assigns the current cmb002 material.
        - 'New' / 'Random' route to b006 / b004.
        - Any other leaf is treated as a material name and assigned directly.
        Result is reported via sb.message_box in every branch.
        """
        text = item.item_text()
        parent = item.parent_item_text()

        # Root release: assign the current cmb002 material.
        if parent is None:
            current = self.ui.cmb002.currentData()
            if not current:
                self.sb.message_box(
                    "<hl>No current material</hl><br>"
                    "Pick a material in the main UI first."
                )
                return
            self._assign_material_with_feedback(str(current))
            return

        if text == "New":
            self.b006(item)
            return
        if text == "Random":
            self.b004(item)
            return

        # Otherwise treat as a material name — assign directly.
        self._assign_material_with_feedback(text)

    def _assign_material_with_feedback(self, mat_name):
        """Assign ``mat_name`` to the current selection and report the result.

        Side effects:
            - Sets cmb002's current material to ``mat_name`` (which fires
              the connected ``list000.init_slot`` so the root label updates).
            - Emits an sb.message_box describing success or the failure reason.
        """
        selection = cmds.ls(sl=True, flatten=True) or []
        if not selection:
            self.sb.message_box(
                "<hl>Nothing selected</hl><br>"
                "Select object(s) before assigning a material."
            )
            return
        try:
            mtk.MatUtils.assign_mat(selection, mat_name)
        except Exception as e:
            self.sb.message_box(
                f"<hl>Assign failed</hl><br>{mat_name}: {e}"
            )
            return
        # Push the assigned material into cmb002 — this propagates to the
        # submenu Assign list's root label via the cmb002 signal connections.
        self.ui.cmb002.setAsCurrent(mat_name)
        self.sb.message_box(
            f"Assigned <hl>{mat_name}</hl> to "
            f"<hl>{len(selection)}</hl> object(s)."
        )

    # --- Submenu Tools list --------------------------------------------

    def list001_init(self, widget):
        """Tools list: Setup / Conversion / External (mirrors prior header sections).

        Uses ``expand_up`` so the categories sublist overlays the root's
        lower-left corner (the sublist's last item lines up with the
        ``Tools`` trigger button), and deeper item sublists fan right.
        """
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up")

        root = widget.add("Tools")
        root.sublist.setMinimumWidth(widget.width() or 160)

        for category, items in self._TOOLS_ITEMS.items():
            cat = root.sublist.add(category)
            for label, _slot, *rest in items:
                cat.sublist.add(label, setToolTip=rest[0] if rest else "")

    @Signals("on_item_interacted")
    def list001(self, item):
        """Dispatch Tools list selection to the matching slot method."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        text = item.item_text()
        parent = item.parent_item_text() or ""

        for label, slot_name, *_ in self._TOOLS_ITEMS.get(parent, ()):
            if label == text:
                slot = getattr(self, slot_name, None)
                if not callable(slot):
                    return
                # Tool slots all take a widget arg; the list item suffices.
                try:
                    slot(item)
                except TypeError:
                    slot()
                return

    def cmb002_init(self, widget):
        """Initialize Materials"""
        if not widget.is_initialized:
            widget.refresh_on_show = True  # Call this method on show
            widget.editable = True
            # Option box (a separate dropdown from the right-click context
            # menu built below): list-population options for the materials combo.
            widget.option_box.menu.setTitle("Material List Options")
            chk_hide_defaults = widget.option_box.menu.add(
                "QCheckBox",
                setText="Hide Default Materials",
                setObjectName="chk_hide_defaults",
                setChecked=False,
                setToolTip=(
                    "Hide Maya's built-in default materials (lambert1, "
                    "standardSurface1, particleCloud1, …) from the list.\n"
                    "Off by default; user-created materials are always shown."
                ),
            )
            # Re-populate the combo when toggled. The submenu Assign list's
            # contents don't depend on this toggle, so it needs no refresh.
            chk_hide_defaults.toggled.connect(widget.init_slot)
            # Cleanup actions (moved here from the right-click context menu).
            widget.option_box.menu.add("Separator", setTitle="Cleanup")
            widget.option_box.menu.add(
                "QPushButton",
                setText="Remove Duplicate Materials",
                setObjectName="b014",
                setToolTip="Find duplicate materials, remove duplicates, and reassign them to the original material.",
            )
            widget.option_box.menu.add(
                "QPushButton",
                setText="Delete All Unused Materials",
                setObjectName="b015",
                setToolTip="Delete all unused materials.",
            )
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
            # Rename the material after editing has finished.
            widget.on_editing_finished.connect(
                lambda text: cmds.rename(str(widget.currentData()), text)
            )
            # Initialize the widget every time before the popup is shown.
            widget.before_popup_shown.connect(widget.init_slot)
            # Refresh the submenu Assign list when the current material changes.
            widget.on_editing_finished.connect(self.submenu.list000.init_slot)
            widget.currentIndexChanged.connect(self.submenu.list000.init_slot)

        # Use 'restore_index=True' to save and restore the index. Default
        # materials are shown unless the option-box toggle hides them.
        materials_dict = mtk.MatUtils.get_scene_mats(
            sort=True,
            as_dict=True,
            exclude_defaults=self._hide_default_materials(),
        )
        widget.add(materials_dict, clear=True, restore_index=True)

        # Create and set icons with color swatch
        for i, mat in enumerate(widget.items):
            icon = mtk.MatUtils.get_mat_swatch_icon(mat)
            if icon:
                widget.setItemIcon(i, icon)

    def _hide_default_materials(self) -> bool:
        """Whether cmb002's 'Hide Default Materials' option-box toggle is on.

        Returns False (defaults shown) when the option box / checkbox hasn't
        been created yet, so a population pass that runs before init is safe.
        """
        option_box = self.ui.cmb002.option_box
        menu = option_box.get_menu(create=False) if option_box else None
        chk = getattr(menu, "chk_hide_defaults", None) if menu else None
        return bool(chk and chk.isChecked())

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
        self.submenu.list000.init_slot()

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

    def b005(self, widget):
        """Assign Current (main UI button)"""
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
        ui = self.sb.handlers.external_app.launch("map_packer", show=False)
        ui.slots.source_dir = mtk.get_env_info("sourceimages")
        self.sb.handlers.marking_menu.show(ui)

    def b009(self, widget):
        """Create Game Shader"""
        self.sb.handlers.marking_menu.show("game_shader")

    def b026(self, widget):
        """Arnold Preview Shader (parallel aiStandardSurface for in-Maya Arnold preview; not an
        external-app bridge — renamed from 'Arnold Bridge' to avoid that confusion)."""
        self.sb.handlers.marking_menu.show("arnold_bridge")

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
        ui = self.sb.handlers.external_app.launch("map_converter", show=False)
        ui.slots.source_dir = mtk.get_env_info("sourceimages")

        def _selected_texture_paths():
            sel = cmds.ls(selection=True, long=True) or []
            return mtk.MatUtils.get_texture_paths(objects=sel) if sel else []

        ui.slots.texture_provider = _selected_texture_paths

        self.sb.handlers.marking_menu.show(ui)

    def b018(self, widget):
        """Update Materials (Material Updater) — reprocess scene materials' textures and re-wire them."""
        self.sb.handlers.marking_menu.show("mat_updater")

    _TB001_SCOPES = (
        ("Textures", "textures"),
        ("Current Material", "current"),
        ("All Materials", "all"),
        ("Selected Objects", "selected"),
    )

    def tb001_init(self, widget):
        """Get Material Info — option box."""
        widget.option_box.menu.setTitle("Get Material Info")
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip=(
                "Textures: every scene texture file.\n"
                "Current Material: the material picked in cmb002.\n"
                "All Materials: every scene material.\n"
                "Selected Objects: materials assigned to the current "
                "viewport selection."
            ),
        )
        for label, data in self._TB001_SCOPES:
            cmb.addItem(label, data)
        # Scope filters — apply to scopes that gather more than one material.
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Exclude Default Materials",
            setObjectName="chk_exclude_defaults",
            setChecked=True,
            setToolTip=(
                "Drop Maya's built-in defaults (lambert1, standardSurface1, …) "
                "from the report. Has no effect on the Current Material scope."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Exclude Unassigned Materials",
            setObjectName="chk_exclude_unassigned",
            setChecked=False,
            setToolTip=(
                "Drop materials whose shading engines have no geometry "
                "assigned. Most useful on the All Materials scope — "
                "selection-derived and Current scopes are already "
                "guaranteed to be assigned."
            ),
        )
        # Field toggles — control how much info each material record carries.
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Include Textures",
            setObjectName="chk_include_textures",
            setChecked=True,
            setToolTip=(
                "Include the per-file-node texture list. Uncheck for a "
                "lightweight name + type report."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Include Image Metadata",
            setObjectName="chk_include_metadata",
            setChecked=True,
            setToolTip=(
                "Include resolution, mode, format, and bit depth per "
                "texture. Skipping this avoids opening images with PIL."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Include Optimization Analysis",
            setObjectName="chk_include_optimization",
            setChecked=True,
            setToolTip=(
                "Run the texture optimizer per texture and report whether "
                "a resize, mode change, or bit-depth change is recommended."
            ),
        )

    def tb001(self, widget):
        """Get Material Info — render a formatted report to the viewer dialog.

        Validates scope inputs *before* opening the footer progress so
        a quick bail-out (no current material, empty selection, …)
        doesn't trigger the misleading "Complete" flash that
        :class:`FooterProgressContext` emits on normal context exit.
        """
        menu = widget.option_box.menu
        cmb = menu.cmb_scope
        scope = cmb.currentData() or "current"
        scope_label = cmb.currentText() or scope

        exclude_defaults = menu.chk_exclude_defaults.isChecked()
        exclude_unassigned = menu.chk_exclude_unassigned.isChecked()
        include_textures = menu.chk_include_textures.isChecked()
        include_metadata = menu.chk_include_metadata.isChecked()
        include_optimization = menu.chk_include_optimization.isChecked()

        # Pre-validate scope inputs.
        get_mat_info_kwargs = None
        if scope == "current":
            mat = self.ui.cmb002.currentData()
            if not mat:
                self.sb.message_box(
                    "<hl>No current material</hl><br>Pick a material first."
                )
                return
            get_mat_info_kwargs = {"materials": [str(mat)]}
            title = f"Material Info — {mat}"
        elif scope == "selected":
            sel = cmds.ls(sl=True, flatten=True) or []
            if not sel:
                self.sb.message_box(
                    "<hl>Nothing selected</hl><br>"
                    "Select object(s) to report their assigned materials."
                )
                return
            get_mat_info_kwargs = {"objects": sel}
            title = f"Material Info — {len(sel)} selected object(s)"

        with self.sb.progress(
            text=f"Working: Get Material Info ({scope_label})"
        ) as update:
            cb = self.sb.progress_adapter(update)
            if scope == "textures":
                # Resolve the texture scope via materials so the same
                # default/unassigned filters apply to the texture list.
                tex_materials = mtk.MatUtils.get_scene_mats(
                    exclude_defaults=exclude_defaults
                ) or []
                if exclude_unassigned:
                    tex_materials = [
                        m for m in tex_materials if mtk.MatUtils.is_mat_assigned(m)
                    ]
                info = (
                    mtk.MatUtils.get_texture_info(materials=tex_materials)
                    if tex_materials
                    else []
                )
                if not info:
                    html = None
                else:
                    html = mtk.MatUtils.format_texture_info_html(info)
                    title = f"Texture Info — {len(info)} texture(s)"
            else:
                # "current" scope explicitly targets one material, so the
                # scope-wide filters would just drop the user's pick.
                apply_scope_filters = scope != "current"
                common_kwargs = dict(
                    optimize_check=include_optimization,
                    allow_palette=True,
                    progress_callback=cb,
                    include_textures=include_textures,
                    include_image_metadata=include_metadata,
                    exclude_defaults=exclude_defaults if apply_scope_filters else False,
                    exclude_unassigned=(
                        exclude_unassigned if apply_scope_filters else False
                    ),
                )
                if get_mat_info_kwargs is None:  # scope == "all"
                    records = mtk.MatUtils.get_mat_info(**common_kwargs)
                    title = f"Material Info — all ({len(records)} material(s))"
                else:
                    records = mtk.MatUtils.get_mat_info(
                        **common_kwargs, **get_mat_info_kwargs
                    )
                html = (
                    mtk.MatUtils.format_mat_info_html(records) if records else None
                )

        if html is None:
            if scope == "textures":
                self.sb.message_box("<hl>No textures</hl> found in scene.")
            else:
                self.sb.message_box(
                    f"<hl>No materials</hl> for scope: {scope_label}."
                )
            return

        # Non-modal viewer: Maya stays responsive while the user reads
        # the report. The Ok button closes the window via WindowPanel's
        # close(); the window's X button works too.
        self.sb.text_view_dialog(
            html,
            "Ok",
            title=title,
            size=(760, 520),
            monospace=False,
        )

    def b021(self, widget):
        """Image to Plane"""
        self.sb.handlers.marking_menu.show("image_to_plane")

    def b019(self, widget):
        """Marmoset Bridge"""
        self.sb.handlers.marking_menu.show("marmoset_bridge")

    def b020(self, widget):
        """Substance Bridge"""
        self.sb.handlers.marking_menu.show("substance_bridge")

    def b022(self, widget):
        """Map Compositor"""
        self.sb.handlers.external_app.launch("map_compositor")

    def b023(self, widget):
        """Metashape Workflow"""
        self.sb.handlers.external_app.launch("metashape_workflow")

    def b024(self, widget):
        """RealityCapture Workflow"""
        self.sb.handlers.external_app.launch("realityscan_workflow")

    def b025(self, widget):
        """Brush Splat Workflow"""
        self.sb.handlers.external_app.launch("gaussian_splat_workflow")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
