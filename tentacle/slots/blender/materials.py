# !/usr/bin/python
# coding=utf-8
import bpy
import pythontk as ptk
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class MaterialsSlots(SlotsBlender):
    """Blender port of the shared ``materials`` menu — mirrors the Maya slot's workflow against
    ``blendertk.MatUtils`` (materials on ``obj.material_slots`` / ``bpy.data.materials``; textures
    are ``TEX_IMAGE`` nodes — no shading engines / file nodes). The material/texture **info report**
    (``tb001``) renders via ``pythontk.MatReport`` (the SSoT shared with mayatk) and exposes
    ``Include Optimization Analysis`` (best-effort via the shared ``ptk.MapOptimizer`` — degrades to
    a per-texture "unavailable" note if Blender's Python lacks Pillow). The only Maya widgets dropped
    are ``Hide/Exclude Default Materials`` (Blender has no auto-created built-in defaults to filter).
    The Tools submenu lists, grouped by what they act on: native ``blendertk`` panels (Update
    Materials / Game Shader / Shader Templates / Texture Path Editor / Image to Plane) that work on
    the live scene; the host-agnostic ``extapps`` panels (Map Converter / Packer / Compositor and
    the photogrammetry workflows), surfaced exactly as in Maya via ``external_app.launch`` (wired in
    ``tcl_blender``); and the Marmoset / Substance / Unity **bridges**, which export the Blender
    *selection* to FBX and hand off to the matching extapps workflow (the Blender analogue of Maya's
    bridges — for Unity, Maya keeps a native panel while Blender reuses the extapps one).
    Maya-only shaders (Arnold preview) have no Blender equivalent and are absent.
    """

    # Submenu Tools list. Categories group tools by *what they act on* (mirrors Maya):
    #   "Materials (scene)"   — mutate the live node networks.
    #   "Texture Maps (files)" — standalone, host-agnostic ``extapps`` panels that
    #                            operate on texture files on disk.
    # Each entry is (label, slot_name, tooltip); tooltip may be "".
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
                "and re-wire the results back into their node networks. Works "
                "in-scene — it modifies materials. For per-file work on the "
                "textures themselves, use Map Converter under Texture Maps.",
            ),
            (
                "Game Shader",
                "b009",
                "Build a game-shader material network from texture maps.",
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
        "Bridges": [
            ("Marmoset Bridge", "b019", ""),
            ("Substance Bridge", "b020", ""),
            ("Unity Bridge", "b026", ""),
        ],
        "External": [
            ("Map Compositor", "b022", ""),
            ("Metashape Workflow", "b023", ""),
            ("RealityCapture Workflow", "b024", ""),
            ("Brush Splat Workflow", "b025", ""),
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.materials
        self.submenu = self.sb.loaded_ui.materials_submenu
        self.last_random_material = None

    # ------------------------------------------------------------------ header (Utilities)
    def header_init(self, widget):
        """Header menu — Utilities (Setup tools live in the submenu Tools list, mirroring Maya)."""
        widget.menu.add("Separator", setTitle="Utilities")
        widget.menu.add(
            "QPushButton", setText="Reload Scene Textures", setObjectName="b013",
            setToolTip="Reload file textures for all scene materials.",
        )
        widget.menu.add(
            self.sb.registered_widgets.PushButton, setText="Get Material Info", setObjectName="tb001",
            setToolTip="Show a formatted report of materials/textures (resolution, mode, format, "
            "bit depth, file size). Scope + filters are set via the option box.",
        )
        widget.menu.add(
            "QPushButton", setText="Shader Editor", setObjectName="b_shader_editor",
            setToolTip="Open the Shader (node) Editor — Blender's analogue of Maya's Hypershade.",
            clicked=lambda: btk.open_editor("Shader Editor"),
        )

    # ------------------------------------------------------------------ cmb002  Material list
    def cmb002_init(self, widget):
        """Materials combo: scene materials with color swatches + option box (Cleanup) + a
        right-click Edit/View menu (Rename / Delete / Select Node / Open in Editor)."""
        if not widget.is_initialized:
            widget.refresh_on_show = True
            widget.editable = True

            # Option box — Cleanup actions. (Maya's 'Hide Default Materials' toggle is omitted:
            # Blender has no built-in default materials to hide.)
            widget.option_box.menu.setTitle("Material List Options")
            widget.option_box.menu.add("Separator", setTitle="Cleanup")
            widget.option_box.menu.add(
                "QPushButton", setText="Remove Duplicate Materials", setObjectName="b014",
                setToolTip="Find materials sharing the same texture files, reassign their objects "
                "to one canonical material, and delete the duplicates.",
            )
            widget.option_box.menu.add(
                "QPushButton", setText="Delete All Unused Materials", setObjectName="b015",
                setToolTip="Delete materials assigned to no object (fake-user materials are kept).",
            )

            # Right-click context menu — Edit / View.
            widget.menu.add("Separator", setTitle="Edit")
            widget.menu.add(
                self.sb.registered_widgets.Label, setText="Rename", setObjectName="lbl005",
                setToolTip="Rename the current material (makes the combo editable).",
            )
            lbl007 = widget.menu.add(
                self.sb.registered_widgets.Label, setText="Rename (strip trailing ints & _)",
                setObjectName="lbl007",
                setToolTip="Strip trailing digits/underscores from the current material's name.",
            )
            lbl007.option_box.set_action(
                callback=self.lbl007_global, icon="list",
                tooltip="Strip trailing ints & _ from ALL scene materials.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label, setText="Delete", setObjectName="lbl002",
                setToolTip="Delete the current material.",
            )
            widget.menu.add("Separator", setTitle="View / Select")
            widget.menu.add(
                self.sb.registered_widgets.Label, setText="Select Node", setObjectName="lbl004",
                setToolTip="Select the object(s) using this material.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label, setText="Open in Editor", setObjectName="lbl006",
                setToolTip="Open this material in the Shader Editor.",
            )

            widget.on_editing_finished.connect(self._rename_current)
            widget.before_popup_shown.connect(widget.init_slot)
            widget.currentIndexChanged.connect(self.submenu.list000.init_slot)
            widget.on_editing_finished.connect(self.submenu.list000.init_slot)

        materials_dict = btk.get_scene_mats(sort=True, as_dict=True)
        widget.add(materials_dict, clear=True, restore_index=True)
        for i, mat in enumerate(widget.items):
            icon = btk.get_mat_swatch_icon(mat)
            if icon:
                widget.setItemIcon(i, icon)

    def cmb002(self, index, widget):
        """Current Material (selection only — assignment is on the b-buttons)."""

    def _rename_current(self, text):
        """Rename the current material datablock to ``text`` (combo edit-finished)."""
        mat = self.ui.cmb002.currentData()
        if mat and text:
            mat.name = text

    # ------------------------------------------------------------------ tb000  Select By Material
    def tb000_init(self, widget):
        widget.option_box.menu.setTitle("Select By Material")
        widget.option_box.menu.add(
            "QCheckBox", setText="Shell", setObjectName="chk005",
            setToolTip="Select whole object(s) using the material (else select the faces).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Search in Selection Only", setObjectName="chk006",
            setToolTip="Search only within the current selection (else the whole scene).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Get and Select", setObjectName="chk007",
            setToolTip="First set the current material from the active selection, then select.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Add to Selection", setObjectName="chk008",
            setToolTip="Add matches to the current selection instead of replacing it.",
        )

    def tb000(self, widget):
        """Select By Material"""
        m = widget.option_box.menu
        prior = list(self.selected_objects())

        if m.chk007.isChecked():  # get the material from the active selection first
            self.b002(None)

        mat = self.ui.cmb002.currentData()
        if mat is None:
            self.sb.message_box("No material selected in the materials list.")
            return

        pool = prior if m.chk006.isChecked() else None
        users = btk.find_by_mat_id(mat, objects=pool)
        if not users:
            self.sb.message_box(f"No objects use <hl>{mat.name}</hl>.")
            return

        # leave any component mode first (mode_set polls on the active object — guard the no-active
        # and already-object cases so it can't raise)
        active = bpy.context.view_layer.objects.active
        if active and active.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if not m.chk008.isChecked():
            bpy.ops.object.select_all(action="DESELECT")
        for o in users:
            o.select_set(True)
        bpy.context.view_layer.objects.active = users[0]

        if not m.chk005.isChecked():  # face mode: highlight the material's faces in edit mode
            self._select_material_faces(users, mat)

    @staticmethod
    def _select_material_faces(objects, mat):
        """Enter Edit Mode and select the faces assigned to ``mat`` across ``objects``."""
        for obj in objects:
            for i, slot in enumerate(obj.material_slots):
                if slot.material is mat:
                    obj.active_material_index = i
                    break
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        try:
            bpy.ops.object.material_slot_select()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ tb001  Get Material Info
    _TB001_SCOPES = (
        ("Textures", "textures"),
        ("Current Material", "current"),
        ("All Materials", "all"),
        ("Selected Objects", "selected"),
    )

    def tb001_init(self, widget):
        """Get Material Info — option box. (Maya's Exclude/Hide-Default-Materials options are
        omitted — Blender has no auto-created default materials to filter.)"""
        menu = widget.option_box.menu
        menu.setTitle("Get Material Info")
        cmb = menu.add(
            "QComboBox", setObjectName="cmb_scope",
            setToolTip="Textures: every scene texture.\nCurrent Material: the cmb002 pick.\n"
            "All Materials: every scene material.\nSelected Objects: materials on the selection.",
        )
        for label, data in self._TB001_SCOPES:
            cmb.addItem(label, data)
        menu.add(
            "QCheckBox", setText="Exclude Unassigned Materials", setObjectName="chk_exclude_unassigned",
            setChecked=False, setToolTip="Drop materials assigned to no object.",
        )
        menu.add(
            "QCheckBox", setText="Include Textures", setObjectName="chk_include_textures",
            setChecked=True, setToolTip="Include the per-node texture list.",
        )
        menu.add(
            "QCheckBox", setText="Include Image Metadata", setObjectName="chk_include_metadata",
            setChecked=True, setToolTip="Include resolution / mode / format / bit depth per texture.",
        )
        # chk_include_optimization reuses the Maya name/label. Runs the shared ptk.MapOptimizer per
        # texture (best-effort — if Blender's Python lacks Pillow, each texture reports the analysis
        # as unavailable rather than failing the report).
        menu.add(
            "QCheckBox", setText="Include Optimization Analysis", setObjectName="chk_include_optimization",
            setChecked=False,
            setToolTip="Report whether each texture would benefit from a resize / mode / bit-depth "
            "change. Requires Pillow in Blender's Python; otherwise noted as unavailable per texture.",
        )

    def tb001(self, widget):
        """Get Material Info — render a formatted report to the text-view dialog."""
        menu = widget.option_box.menu
        scope = menu.cmb_scope.currentData() or "current"
        scope_label = menu.cmb_scope.currentText() or scope
        exclude_unassigned = menu.chk_exclude_unassigned.isChecked()
        include_textures = menu.chk_include_textures.isChecked()
        include_metadata = menu.chk_include_metadata.isChecked()
        include_optimization = menu.chk_include_optimization.isChecked()

        if scope == "textures":
            info = btk.get_texture_info()
            html = btk.format_texture_info_html(info) if info else None
            title = f"Texture Info — {len(info)} texture(s)"
        else:
            kwargs = dict(
                include_textures=include_textures,
                include_image_metadata=include_metadata,
                exclude_unassigned=exclude_unassigned,
                optimize_check=include_optimization,
            )
            if scope == "current":
                mat = self.ui.cmb002.currentData()
                if not mat:
                    self.sb.message_box("<hl>No current material</hl><br>Pick a material first.")
                    return
                records = btk.get_mat_info(materials=[mat], **kwargs)
                title = f"Material Info — {mat.name}"
            elif scope == "selected":
                sel = self.selected_objects()
                if not sel:
                    self.sb.message_box("<hl>Nothing selected</hl><br>Select object(s) to report.")
                    return
                records = btk.get_mat_info(objects=sel, **kwargs)
                title = f"Material Info — {len(sel)} selected object(s)"
            else:  # all
                records = btk.get_mat_info(**kwargs)
                title = f"Material Info — all ({len(records)} material(s))"
            html = btk.format_mat_info_html(records) if records else None

        if html is None:
            self.sb.message_box(f"<hl>No data</hl> for scope: {scope_label}.")
            return
        try:
            self.sb.text_view_dialog(html, "Ok", title=title, size=(760, 520), monospace=False)
        except Exception:  # fall back to a plain box if the host has no dialog
            self.sb.message_box(html)

    # ------------------------------------------------------------------ Submenu Assign list
    def list000_init(self, widget):
        """Assign list: 'Assign: <current>' root + New / Random + scene materials."""
        if not getattr(widget, "_assign_list_configured", False):
            widget.refresh_on_show = True
            widget.fixed_item_height = 18
            widget.apply_preset("expand_right")
            widget._assign_list_configured = True
            if not getattr(self.ui.cmb002, "is_initialized", False):
                self.ui.cmb002.init_slot()
                self.ui.cmb002.is_initialized = True

        widget.clear()
        current = self.ui.cmb002.currentData()
        root = widget.add(f"Assign: {current.name}" if current else "Assign")
        root.sublist.setMinimumWidth(widget.width() or 160)
        root.sublist.add("New")
        root.sublist.add("Random")
        for mat in btk.get_scene_mats(sort=True):
            root.sublist.add(mat.name)

    @Signals("on_item_interacted")
    def list000(self, item):
        """Assign list: root assigns the current material; New/Random route to b006/b004;
        any other leaf is a material name assigned directly."""
        text = item.item_text()
        parent = item.parent_item_text()
        if parent is None:  # root release
            current = self.ui.cmb002.currentData()
            if not current:
                self.sb.message_box("<hl>No current material</hl><br>Pick a material first.")
                return
            self._assign_named(current.name)
            return
        if text == "New":
            self.b006(item)
        elif text == "Random":
            self.b004(item)
        else:
            self._assign_named(text)

    def _assign_named(self, mat_name):
        """Assign the named material to the selection and report; sync cmb002."""
        selection = self.selected_objects()
        if not selection:
            self.sb.message_box("<hl>Nothing selected</hl><br>Select object(s) first.")
            return
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            self.sb.message_box(f"<hl>No such material</hl><br>{mat_name}")
            return
        btk.assign_mat(selection, mat)
        self.ui.cmb002.setAsCurrent(mat_name)
        self.sb.message_box(f"Assigned <hl>{mat_name}</hl> to <hl>{len(selection)}</hl> object(s).")

    # ------------------------------------------------------------------ Submenu Tools list
    def list001_init(self, widget):
        """Tools list (Setup tools with a native Blender op)."""
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
        """Dispatch a Tools-list selection to its slot method."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        parent = item.parent_item_text() or ""
        for label, slot_name, *_ in self._TOOLS_ITEMS.get(parent, ()):
            if label == text:
                getattr(self, slot_name)()
                return

    # ------------------------------------------------------------------ b-slots (assign / get)
    def b002(self, widget=None):
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
        self.ui.cmb002.setAsCurrent(mats[0].name)

    @btk.undoable
    def b004(self, widget=None):
        """Assign Random"""
        selection = self.selected_objects()
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return
        new_mat = btk.create_mat("random")
        btk.assign_mat(selection, new_mat)
        last = self.last_random_material
        if last and last is not new_mat and not btk.is_mat_assigned(last):
            bpy.data.materials.remove(last)
        self.last_random_material = new_mat
        self.ui.cmb002.init_slot()
        self.ui.cmb002.setAsCurrent(new_mat.name)

    @btk.undoable
    def b005(self, widget=None):
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
    def b006(self, widget=None):
        """Assign New Material"""
        selection = self.selected_objects()
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return
        mat = btk.create_mat("standard", name="Material")
        btk.assign_mat(selection, mat)
        self.ui.cmb002.init_slot()
        self.ui.cmb002.setAsCurrent(mat.name)

    def b013(self):
        """Reload Scene Textures"""
        btk.reload_textures()
        self.sb.message_box("Textures reloaded from disk.")

    @btk.undoable
    def b014(self):
        """Remove Duplicate Materials"""
        dups = btk.find_materials_with_duplicate_textures()
        if not dups:
            self.sb.message_box("No duplicate-texture materials found.")
            return
        reassigned = btk.reassign_duplicate_materials(dups, delete=True)
        self.ui.cmb002.init_slot()
        self.sb.message_box(f"Removed duplicates — reassigned <hl>{reassigned}</hl> slot(s).")

    @btk.undoable
    def b015(self, widget=None):
        """Delete All Unused Materials"""
        removed = btk.delete_unused_materials()
        self.ui.cmb002.init_slot()
        self.sb.message_box(f"Deleted <hl>{len(removed)}</hl> unused material(s).")

    # ------------------------------------------------------------------ context-menu (lbl) slots
    def lbl002(self):
        """Delete the current material."""
        mat = self.ui.cmb002.currentData()
        if mat is None:
            return
        bpy.data.materials.remove(mat)
        self.ui.cmb002.init_slot()

    def lbl004(self):
        """Select Node — select the object(s) using the current material."""
        mat = self.ui.cmb002.currentData()
        if mat is None:
            self.sb.message_box("No current material.")
            return
        users = btk.select_by_material(mat)
        if not users:
            self.sb.message_box(f"No objects use <hl>{mat.name}</hl>.")

    def lbl005(self):
        """Rename — make the combo editable so the user can type a new name."""
        self.ui.cmb002.setEditable(True)
        self.ui.cmb002.option_box.menu.hide()

    def lbl006(self):
        """Open in Editor — graph the current material in the Shader Editor."""
        mat = self.ui.cmb002.currentData()
        if mat is None:
            self.sb.message_box("No current material.")
            return
        btk.graph_materials(mat)

    def lbl007(self):
        """Rename the current material by stripping trailing integers/underscores."""
        mat = self.ui.cmb002.currentData()
        if mat is None:
            return
        base = ptk.StrUtils.format_suffix(mat.name, strip="_", strip_trailing_ints=True)
        if not base:
            self.sb.message_box("<hl>Invalid name</hl><br>Stripping leaves an empty name.")
            return
        if base == mat.name:
            self.sb.message_box("<hl>No trailing suffix</hl><br>Nothing to strip.")
            return
        if bpy.data.materials.get(base) is not None:
            self.sb.message_box(f"<hl>Rename aborted</hl><br>'{base}' already exists.")
            return
        mat.name = base
        self.ui.cmb002.init_slot()
        self.ui.cmb002.setAsCurrent(base)

    def lbl007_global(self):
        """Strip trailing ints/underscores from ALL scene materials (skips on-collision)."""
        materials = btk.get_scene_mats(sort=True)
        names = [m.name for m in materials]
        rename_map = ptk.StrUtils.resolve_name_collisions(
            names, strip="_", strip_trailing_ints=True
        )
        by_name = {m.name: m for m in materials}
        renamed = 0
        for old, new in rename_map.items():
            if new in names or bpy.data.materials.get(new) is not None:
                continue  # would collide with a non-input node
            by_name[old].name = new
            renamed += 1
        self.ui.cmb002.init_slot()
        self.sb.message_box(f"<hl>Strip trailing — global</hl><br>Renamed: <strong>{renamed}</strong>.")

    # ------------------------------------------------------------------ Setup tools
    def b021(self):
        """Image to Plane — open the panel (batch image→plane with aspect sizing, material affix
        naming, grouping, and remove), served from blendertk by the BlenderUiHandler, mirroring
        Maya's image-to-plane window (replaces the one-shot native Import-Images-as-Planes op)."""
        self.sb.handlers.marking_menu.show("image_to_plane")

    def b010(self):
        """Texture Path Editor — co-located blendertk panel (list / repath / resolve-missing /
        normalize paths). Subsumes Maya's b010 and the old native Find-Missing-Files."""
        self.sb.handlers.marking_menu.show("texture_path_editor")

    def b009(self):
        """Game Shader — co-located blendertk panel (auto-build a Principled material from a PBR
        texture set; classify + wire each map). Mirrors Maya's b009."""
        self.sb.handlers.marking_menu.show("game_shader")

    def b011(self):
        """Shader Templates — co-located blendertk panel (Principled-BSDF presets: create new /
        apply to selected)."""
        self.sb.handlers.marking_menu.show("shader_templates")

    def b018(self):
        """Update Materials (Material Updater) — co-located blendertk panel (batch-reprocess material
        textures via the shared pythontk factory and repath the image nodes). Mirrors Maya's b018."""
        self.sb.handlers.marking_menu.show("mat_updater")

    # ------------------------------------------------------------------ external app launchers
    # The standalone ``extapps`` panels (registered in ``tcl_blender``). DCC-agnostic, so these
    # mirror the Maya handlers. They run in-process; ``extapps`` is put on Blender's ``sys.path``
    # by ``tcl_blender._QtBootstrap.bootstrap_paths``. Every launch goes through ``_launch_extapp`` so a missing
    # package surfaces as a message box instead of a traceback (Maya's auto-install can't apply on
    # Blender — see the registration note in ``tcl_blender``).
    def _safe_launch(self, app, show):
        """``external_app.launch`` wrapped so a failure is a message box, not a traceback/hang.
        Returns the ui (in-process widget) or None. Shared by the extapp + bridge launchers."""
        try:
            return self.sb.handlers.external_app.launch(app, show=show)
        except Exception as error:
            self.sb.message_box(
                f"<hl>Couldn't open {app.replace('_', ' ').title()}</hl><br>{error}"
            )
            return None

    def _launch_extapp(self, app, source_dir=False):
        """Launch a registered ``extapps`` panel in-process, surfacing any failure as a message.

        ``source_dir=True`` (Map Packer / Converter) pre-fills the panel's source dir from the saved
        .blend's directory — the Blender analogue of Maya's ``sourceimages`` — then shows it via the
        marking menu; otherwise the handler shows it directly.
        """
        ui = self._safe_launch(app, show=not source_dir)
        if ui is None or not source_dir:
            return
        src = btk.get_env_info("workspace")
        if src and getattr(ui, "slots", None) is not None:
            ui.slots.source_dir = src
        self.sb.handlers.marking_menu.show(ui)

    def b008(self):
        """Map Packer"""
        self._launch_extapp("packer", source_dir=True)

    def b016(self):
        """Map Converter"""
        self._launch_extapp("converter", source_dir=True)

    def b022(self):
        """Map Compositor"""
        self._launch_extapp("compositor")

    def b023(self):
        """Metashape Workflow"""
        self._launch_extapp("metashape_workflow")

    def b024(self):
        """RealityCapture Workflow"""
        self._launch_extapp("realityscan_workflow")

    def b025(self):
        """Brush Splat Workflow"""
        self._launch_extapp("gaussian_splat_workflow")

    # ------------------------------------------------------------------ external-app bridges
    # The "Reuse extapps" bridge approach: export the current selection to FBX, then launch the
    # DCC-agnostic extapps workflow with that mesh pre-filled — the Blender analogue of Maya's
    # Substance/Marmoset bridges (which export the Maya selection). Maya objectNames mirrored
    # (Marmoset b019 / Substance b020).
    def _launch_bridge(self, app, prefill):
        """Export the selection to FBX and launch ``app`` (an extapps workflow) with it pre-filled.

        ``prefill`` is the slots method name that accepts the mesh path (``set_model_path`` /
        ``set_mesh_path``). Any failure surfaces as a message box rather than a traceback."""
        selection = btk.selected_objects()
        if not selection:
            self.sb.message_box("<hl>Nothing selected</hl><br>Select mesh object(s) to send.")
            return
        try:
            fbx = btk.export_selection_fbx(objects=selection)
        except Exception as error:
            self.sb.message_box(f"<hl>Export failed</hl><br>{error}")
            return
        ui = self._safe_launch(app, show=False)
        if ui is None:
            return
        setter = getattr(getattr(ui, "slots", None), prefill, None)
        if callable(setter):
            setter(fbx)
        self.sb.handlers.marking_menu.show(ui)

    def b019(self):
        """Marmoset Bridge — export selection → Marmoset Toolbag workflow."""
        self._launch_bridge("marmoset_workflow", "set_model_path")

    def b020(self):
        """Substance Bridge — export selection → Substance Painter workflow."""
        self._launch_bridge("substance_workflow", "set_mesh_path")

    def b026(self):
        """Unity Bridge — export selection → Unity Workflow (copy into a project's Assets/)."""
        self._launch_bridge("unity_workflow", "set_model_path")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
