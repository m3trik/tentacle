# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
import pythontk as ptk

# From this package:
from tentacle import MaterialsMixin, SlotsMaya


class MaterialsSlots(MaterialsMixin, SlotsMaya):
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
                "Mat Updater",
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
            (
                "Emissive Groups",
                "b027",
                "Author named face groups whose emissive regions a game "
                "engine can toggle or dim independently, sharing one all-on "
                "emissive map. Bakes membership into a vertex color set "
                "(rides the FBX) or an _EMask texture, and publishes the "
                "manifest Unity's EmissiveGroupController reads.",
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
        # Folded in from the header menu's Utilities section.
        "Utilities": [
            (
                "Reload Scene Textures",
                "b013",
                "Reload file textures for all scene materials.",
            ),
            (
                "Get Material Info",
                "tb001",
                "Show a formatted report of textures, sizes, bit depth, "
                "file size, and optimization recommendations. Scope "
                "(textures, current material, all materials, selected "
                "objects), default-material / unassigned filters, and "
                "which fields to include are set via the option box.",
            ),
            (
                "Enable Viewport Opacity",
                "tb002",
                "Wire each material's opacity map into the slot its shader "
                "type uses, so transparency shows in the viewport. Materials "
                "without an opacity map are left alone. Scope (selected, "
                "visible, scene) and the viewport transparency mode are set "
                "via the option box.",
            ),
            ("Hypershade Editor", "b007", "Open the Hypershade Window."),
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.materials
        self.submenu = self.sb.loaded_ui.materials_submenu

        # Set a class attribute to track the last created random material
        self.last_random_material = None
        # External tools (compositor, metashape_workflow, ...) self-describe
        # via extapps' entry points and are auto-registered by
        # ExternalAppHandler on host construction, so they appear in the UI
        # browser without first loading this UI.

    def b007(self):
        """Hypershade Editor"""
        mel.eval("HypershadeWindow")

    # --- Assign list ----------------------------------------------------

    def list000_init(self, widget):
        """Assign list: scene materials + 'New' + 'Random'.

        Re-populated on every show so the list reflects the current scene
        contents and the current cmb002 selection. Releasing on the root
        assigns the current material; the row's wording is surface-dependent
        (see the mixin's ``_assign_root_text``).

        This *is* the panel's assign surface — it replaced the Assign /
        Assign Random / New buttons, each of which reached one action where
        the list reaches all of them plus every material in the scene (and
        reports the result, which the bare Assign button did not).
        """
        if not getattr(widget, "_assign_list_configured", False):
            widget.refresh_on_show = True
            widget.fixed_item_height = 18
            widget.apply_preset(
                "expand_right" if widget.ui.has_tags("submenu") else "hover_menu"
            )
            widget._assign_list_configured = True
            # Ensure cmb002 is populated — the submenu's root row reads
            # currentData() off it (see the mixin's _assign_root_text).
            if not getattr(self.ui.cmb002, "is_initialized", False):
                self.ui.cmb002.init_slot()
                self.ui.cmb002.is_initialized = True

        widget.clear()

        root = widget.add(self._assign_root_text(widget))

        # Special actions first
        root.sublist.add("New")
        root.sublist.add("Random")

        # Then every scene material, sorted
        scene_mats = mtk.MatUtils.get_scene_mats(
            exc="standardSurface", sort=True
        ) or []
        for mat in scene_mats:
            root.sublist.add(str(mat))

    @SlotsMaya.Signals("on_item_interacted")
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
              the connected ``_refresh_assign_lists`` so both Assign lists'
              root labels update).
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

        Uses ``expand_up`` in the submenu so the categories sublist overlays
        the root's lower-left corner (the sublist's last item lines up with
        the ``Tools`` trigger button), and deeper item sublists fan right.
        In the panel the list is a body row whose flyouts fan right on hover.

        Rows are plain labels dispatched by ``list001``, EXCEPT entries whose
        slot defines an ``*_init``: that init builds the option box (tb001's
        report scope/filters, tb002's scope + transparency mode), which is
        lost on a plain label, so those are added as real slot-wired widgets.
        """
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_up" if widget.ui.has_tags("submenu") else "hover_menu"
        )

        root = widget.add("Tools")

        for category, items in self._TOOLS_ITEMS.items():
            cat = root.sublist.add(category)
            for label, slot_name, *rest in items:
                tooltip = rest[0] if rest else ""
                if slot_name and hasattr(self, f"{slot_name}_init"):
                    self.add_slot_widget(
                        cat.sublist,
                        setObjectName=slot_name,
                        setText=label,
                        setToolTip=tooltip,
                    )
                else:
                    cat.sublist.add(label, setToolTip=tooltip)

    @SlotsMaya.Signals("on_item_interacted")
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
            chk_hide_arnold = widget.option_box.menu.add(
                "QCheckBox",
                setText="Hide Arnold Shaders",
                setObjectName="chk_hide_arnold",
                setChecked=False,
                setToolTip=(
                    "Hide Arnold shaders (aiStandardSurface, aiToon, …) from the "
                    "list — useful when every game material carries a parallel "
                    "Arnold preview shader (see Tools > Arnold Preview Shader).\n"
                    "Off by default. Arnold *utility* nodes (aiMultiply, bump2d, …) "
                    "are never listed: they're shading-network helpers, not materials."
                ),
            )
            # Re-populate the combo when toggled. The submenu Assign list's
            # contents don't depend on these toggles, so it needs no refresh.
            chk_hide_defaults.toggled.connect(widget.init_slot)
            chk_hide_arnold.toggled.connect(widget.init_slot)
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
            # Every Edit / View entry is a one-shot action — dismiss the
            # context menu once one is triggered.
            widget.menu.hide_on_trigger = True
            widget.menu.add("Separator", setTitle="Edit")
            # "Rename" label + prefix/suffix affix option box (shared, DCC-agnostic).
            self._add_rename_control(widget.menu)
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
            # Registered-widget lookup, not an import: the Switchboard's widget
            # registry already carries every public class under uitk/widgets/.
            self._strip_alpha_option = self.sb.registered_widgets.ActionOption(
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
            widget.on_editing_finished.connect(self._rename_current)
            # Initialize the widget every time before the popup is shown.
            widget.before_popup_shown.connect(widget.init_slot)
            # Refresh BOTH Assign lists (panel + submenu) when the current
            # material changes — their root row mirrors it (see the mixin).
            widget.on_editing_finished.connect(self._refresh_assign_lists)
            widget.currentIndexChanged.connect(self._refresh_assign_lists)

        # Use 'restore_index=True' to save and restore the index. Default
        # materials are shown unless the option-box toggle hides them.
        # (Shading-network utility nodes — aiMultiply, bump2d, … — are dropped
        # by get_scene_mats itself; they were never materials.)
        materials_dict = mtk.MatUtils.get_scene_mats(
            sort=True,
            as_dict=True,
            exclude_defaults=self._list_option("chk_hide_defaults"),
            exc_classification=(
                "rendernode/arnold*"
                if self._list_option("chk_hide_arnold")
                else None
            ),
        )
        widget.add(materials_dict, clear=True, restore_index=True)

        # Create and set icons with color swatch
        for i, mat in enumerate(widget.items):
            icon = mtk.MatUtils.get_mat_swatch_icon(mat)
            if icon:
                widget.setItemIcon(i, icon)

    #: objectNames of the cmb002 option-box list-filter checkboxes. The label
    #: shown when one is reported comes off the widget itself — a second copy
    #: here would be free to drift from the text the user actually sees.
    _LIST_FILTERS = ("chk_hide_defaults", "chk_hide_arnold")

    def _list_filter(self, name: str):
        """The named cmb002 option-box filter checkbox, or None if not built yet."""
        option_box = self.ui.cmb002.option_box
        menu = option_box.get_menu(create=False) if option_box else None
        return getattr(menu, name, None) if menu else None

    def _list_option(self, name: str) -> bool:
        """Whether the named cmb002 option-box list-filter checkbox is checked.

        Returns False when the option box / checkbox hasn't been created yet, so
        a population pass that runs before init is safe (each filter's "off"
        state is the unfiltered one).
        """
        chk = self._list_filter(name)
        return bool(chk and chk.isChecked())

    def _list_filter_names(self):
        """Labels of the cmb002 list filters currently enabled (see MaterialsMixin)."""
        return [
            chk.text()
            for chk in map(self._list_filter, self._LIST_FILTERS)
            if chk is not None and chk.isChecked()
        ]

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

    def _rename_current(self, text):
        """Rename the current material to ``text`` (combo edit-finished).

        Re-populates cmb002 afterward so the item text AND data reflect the
        actual result — Maya may adjust the requested name (invalid characters,
        collisions) — then restores the selection on the renamed material.

        Returns the resulting (possibly Maya-adjusted) name on success, or None
        when nothing was renamed (no material, empty/unchanged name, or a
        failed ``cmds.rename``). Callers that aren't the ``on_editing_finished``
        signal (e.g. the affix field) use this to react to the outcome.
        """
        mat = self.ui.cmb002.currentData()
        if not (mat and text):
            return None
        old_name = str(mat)
        if text == old_name:
            return None
        try:
            new_name = cmds.rename(old_name, text)
        except Exception as e:
            self.sb.message_box(f"<hl>Rename failed</hl><br>{old_name}: {e}")
            # The combo item already carries the typed name (the edit-commit
            # happens widget-side, before this handler runs) — re-sync it
            # with the scene so a failed rename isn't displayed as done.
            self._refresh_material_lists()
            return None
        self._refresh_material_lists()
        self.ui.cmb002.setAsCurrent(new_name)
        return new_name

    def _refresh_after_rename(self, current_old, renamed):
        """Re-populate the material lists and restore selection on the current mat.

        The refresh comes first so the combo and both Assign lists carry the new
        names before the selection is restored; ``setAsCurrent`` then re-fires
        :meth:`_refresh_assign_lists` through ``currentIndexChanged`` if it
        actually moves the index, so no trailing refresh is needed here.
        """
        self._refresh_material_lists()
        for old, new in renamed:
            if old == current_old:
                self.ui.cmb002.setAsCurrent(new)
                break

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
        # Search scope is a choice between two named sets, not a modifier.
        scope = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_search_scope",
            setToolTip="All Objects: search the whole scene.\nSelection Only: search within the current selection (falls back to all objects if nothing is selected).",
        )
        scope.addItems(["All Objects", "Selection Only"])
        scope.setCurrentText("All Objects")  # preserve prior default (checkbox off)
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
        widget.option_box.menu.add(
            "QCheckBox",
            setText="No Material",
            setObjectName="chk009",
            setChecked=False,
            setToolTip=(
                "Select the objects carrying NO material instead of the current one "
                "— geometry still on Maya's default shader, plus any shape bound to "
                "no shading engine at all.\n"
                "Object-level, so Shell and Get and Select don't apply; scope and "
                "Add to Selection still do."
            ),
        )

    def tb000(self, widget):
        """Select By Material — the option box supplies the parameters."""
        menu = widget.option_box.menu
        return self.select_by_mat(
            shell=menu.chk005.isChecked(),
            in_selection=menu.cmb_search_scope.currentText() == "Selection Only",
            get_first=menu.chk007.isChecked(),
            add=menu.chk008.isChecked(),
            unassigned=menu.chk009.isChecked(),
        )

    def select_by_mat(
        self,
        shell=False,
        in_selection=False,
        get_first=False,
        add=False,
        unassigned=False,
    ):
        """Select the geometry carrying the current material.

        The parameterized primitive behind every select-by-material entry point
        (``tb000``'s option box, the submenu's one-shot ``b003``, marking menus).
        Takes plain values so callers don't have to reach into — or temporarily
        mutate — another widget's option-box state.

        Parameters:
            shell (bool): Select whole objects instead of the matching faces.
                Ignored when ``unassigned`` — that search is object-level.
            in_selection (bool): Search within the current selection only
                (falls back to the whole scene when nothing is selected).
            get_first (bool): Adopt the material of the current selection as the
                current material (cmb002) before searching. Ignored when
                ``unassigned`` — that search doesn't read cmb002.
            add (bool): Add the matches to the existing selection instead of
                replacing it.
            unassigned (bool): Select the objects carrying NO material instead
                (default-shaded or orphaned — see ``mtk.MatUtils.find_unassigned``).
                cmb002 is bypassed entirely: "no material" is not a material, so it
                never becomes the current one.

        Returns:
            list: The components/objects selected (empty when nothing matched or
            no current material was resolved).
        """
        prior_selection = cmds.ls(sl=True, flatten=True) or []

        if get_first and not unassigned:  # adopt the selection's material first
            self._adopt_selection_mat(" Proceeding with current material.")

        # Scope: the selection (both finders fall back to the whole scene on an
        # empty list) or None for every object in the scene.
        selection = (cmds.ls(sl=True, objectsOnly=True) or []) if in_selection else None

        if unassigned:
            matches = mtk.MatUtils.find_unassigned(selection)
            # Scope-neutral wording: "everything is assigned" would be a lie under
            # Selection Only, which only looked at part of the scene.
            empty_message = (
                "<hl>No matches</hl><br>No objects without a material were found."
            )
        else:
            mat = self.ui.cmb002.currentData()
            if not mat:
                return []
            matches = mtk.MatUtils.find_by_mat_id(mat, selection, shell=shell)
            empty_message = (
                f"<hl>No matches</hl><br>No objects found with material "
                f"'<strong>{mat}</strong>'."
            )

        if not matches:
            self.sb.message_box(empty_message)
            return []

        if add and prior_selection:
            cmds.select(prior_selection, replace=True)
            cmds.select(matches, add=True)
        else:
            cmds.select(matches)
        return list(matches)

    def lbl002(self):
        """Delete Material"""
        mat = self.ui.cmb002.currentData()  # get the mat obj from cmb002
        if not mat:
            return
        cmds.delete(str(mat))
        self._refresh_material_lists()

    def b015(self, widget):
        """Delete Unused Materials"""
        mel.eval('hyperShadePanelMenuCommand "hyperShadePanel1" "deleteUnusedNodes"')
        self._refresh_material_lists()

    def lbl004(self):
        """Select and Show Attributes: Show Material Attributes in the Attribute Editor."""
        mat = self.ui.cmb002.currentData()  # get the mat obj from cmb002
        if not mat:
            return
        cmds.select(str(mat), replace=True)
        mel.eval(f'showEditorExact("{mat}")')

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

    def _selection_mats(self):
        """Material names on the current selection, or None when nothing is selected.

        The DCC half of the shared ``_adopt_selection_mat`` (see ``MaterialsMixin``).
        ``get_mats`` returns a de-duplicated list of names (not a set).
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            return None
        return [str(m) for m in mtk.MatUtils.get_mats(selection[0])]

    def b002(self, widget):
        """Get Material: Change the index to match the current material selection."""
        self._adopt_selection_mat()

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
        self._refresh_material_lists()
        self.ui.cmb002.setAsCurrent(str(new_mat))

        # Reselect the original selection so that this method can be called again if needed.
        cmds.select(selection)

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
        ui = self.sb.handlers.external_app.launch("packer", show=False)
        ui.slots.source_dir = mtk.get_env_info("sourceimages")
        self.sb.handlers.marking_menu.show(ui)

    def b009(self, widget):
        """Create Game Shader"""
        self.sb.handlers.marking_menu.show("game_shader")

    def b026(self, widget):
        """Arnold Preview Shader (parallel aiStandardSurface for in-Maya Arnold preview; not an
        external-app bridge — renamed from 'Arnold Bridge' to avoid that confusion)."""
        self.sb.handlers.marking_menu.show("arnold_bridge")

    def b027(self, widget):
        """Emissive Groups"""
        self.sb.handlers.marking_menu.show("emissive_groups")

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
            self._refresh_material_lists()

    def b016(self):
        """Map Converter"""
        ui = self.sb.handlers.external_app.launch("converter", show=False)
        ui.slots.source_dir = mtk.get_env_info("sourceimages")

        # The panel is DCC-agnostic: it owns the Scope picker, we own what each
        # scope means here. Providers are called at tool time, so they always
        # read the *current* selection rather than whatever was live at launch.
        def _paths(**scope):
            """Texture paths for one scope, minus the maps Maya ships itself.

            Every tool on this panel WRITES (optimize, convert, repack), and a
            StingrayPBS material carries file nodes for Maya's own preset
            environment maps under MAYA_LOCATION — a read-only tree, so feeding
            them in only ever produced a PermissionError per selected shader.
            """
            return mtk.MatUtils.get_texture_paths(exclude_bundled=True, **scope)

        def _from_objects():
            sel = cmds.ls(selection=True, long=True) or []
            return _paths(objects=sel) if sel else []

        def _from_materials():
            mats = cmds.ls(selection=True, materials=True) or []
            return _paths(materials=mats) if mats else []

        def _from_file_nodes():
            nodes = cmds.ls(selection=True, type="file") or []
            return _paths(file_nodes=nodes) if nodes else []

        def _from_chosen_materials():
            mats = self._choose_scene_materials()
            return _paths(materials=mats) if mats else []

        for label, provider in (
            ("Selected Objects", _from_objects),
            ("Selected Materials", _from_materials),
            ("Selected File Nodes", _from_file_nodes),
            ("Choose Materials...", _from_chosen_materials),
        ):
            ui.slots.register_scope(label, provider)

        self.sb.handlers.marking_menu.show(ui)

    def _choose_scene_materials(self):
        """Multi-select picker over the scene's materials. Returns [] on cancel."""
        materials = sorted(mtk.MatUtils.get_scene_mats() or [], key=str)
        if not materials:
            self.sb.message_box("<hl>No materials</hl><br>The scene has none.")
            return []

        return self.sb.list_input_dialog(
            materials,
            title="Choose Materials",
            label="Select the material(s) to pull textures from:",
            parent=self.sb.parent(),
        )

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

    # Scope choices for tb002 — label, value passed to get_mats_by_scope.
    _TB002_SCOPES = (
        ("Selected Objects", "selected"),
        ("Visible Objects", "visible"),
        ("All Scene Materials", "scene"),
    )

    def tb002_init(self, widget):
        """Enable Viewport Opacity — option box."""
        widget.option_box.menu.setTitle("Enable Viewport Opacity")
        # NOT "cmb_scope": tb001's option box already owns that name, and a widget
        # objectName is the StateManager key (plus the cross-surface sync key) — the
        # two scope combos would overwrite each other's persisted choice.
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_opacity_scope",
            setToolTip=(
                "Selected Objects: materials on the current selection.\n"
                "Visible Objects: materials on visible geometry.\n"
                "All Scene Materials: every material, assigned or not."
            ),
        )
        for label, data in self._TB002_SCOPES:
            cmb.addItem(label, data)
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Depth Peeling",
            setObjectName="chk_depth_peeling",
            setChecked=False,
            setToolTip=(
                "Switch Viewport 2.0 to depth-peeled transparency so "
                "overlapping transparent faces (decals, foliage) sort "
                "correctly. Costs viewport performance; off leaves the "
                "current transparency mode alone."
            ),
        )

    def tb002(self, widget):
        """Enable Viewport Opacity — wire opacity maps for the chosen scope."""
        menu = widget.option_box.menu
        scope = menu.cmb_opacity_scope.currentData() or "selected"
        scope_label = menu.cmb_opacity_scope.currentText() or scope

        materials = mtk.MatUtils.get_mats_by_scope(scope)
        if not materials:
            self.sb.message_box(
                f"<hl>No materials</hl><br>Nothing found for scope: {scope_label}."
            )
            return

        results = mtk.MatUtils.enable_viewport_opacity(
            materials,
            transparency_algorithm=(
                "depth_peeling" if menu.chk_depth_peeling.isChecked() else None
            ),
        )

        enabled = [m for m, s in results.items() if s == "enabled"]
        already = [m for m, s in results.items() if s == "already enabled"]
        skipped = [m for m, s in results.items() if s == "no opacity map"]
        failed = {m: s for m, s in results.items() if s.startswith("unsupported")}

        lines = [
            f"<hl>Viewport opacity</hl> — {scope_label}<br>",
            f"Enabled: <strong>{len(enabled)}</strong><br>",
            f"Already enabled: <strong>{len(already)}</strong><br>",
            f"No opacity map: <strong>{len(skipped)}</strong>",
        ]
        if failed:
            lines.append(
                "<br>Unsupported: <strong>"
                + ", ".join(f"{m} ({s})" for m, s in failed.items())
                + "</strong>"
            )
        self.sb.message_box("".join(lines))

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
        self.sb.handlers.external_app.launch("compositor")

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
