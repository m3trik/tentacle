# !/usr/bin/python
# coding=utf-8
import os
import html

import bpy
import pythontk as ptk
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class SceneSlots(SlotsBlender):
    """Blender port of the shared ``scene`` menu.

    Recent files / autosave recovery map onto Blender's own recent-files.txt and temp-dir
    autosaves (``btk.get_recent_files`` / ``btk.get_recent_autosave``); the submenu's
    Import / Export expandable lists route through Blender's native format operators
    (file dialogs via ``INVOKE_DEFAULT``).
    Reference Manager opens the library-link panel (``blender_menus/reference_manager``).
    Scene Exporter and Hierarchy Manager are native blendertk panels, both 1:1 with mayatk's:
    the former (task/check pipeline, FBX or GLB) reached from the Export list — see
    ``blendertk.env_utils.scene_exporter`` for which tasks/checks are ported vs. disabled
    placeholders (hierarchy_manager / smart_bake / data_export subsystems aren't ported yet);
    the latter for Diff/Fix (Pull isn't ported yet). Maya's workspace model and command ports
    have no Blender analogue and are deferred.
    """

    # (label -> bpy.ops path OR callable(slot)) for the submenu's Import / Export expandable
    # lists; op paths are resolved at call time so a missing importer add-on degrades to a
    # message instead of an AttributeError. Callables cover the entries that aren't native
    # operators — importers with no file browser to invoke, and the Scene Exporter panel.
    _IMPORTERS = {
        "Import FBX": "import_scene.fbx",
        "Import OBJ": "wm.obj_import",
        "Import Collada": "wm.collada_import",
        "Import Maya Scene": lambda slot: slot._import_maya_scene(),
        "Append from .blend": "wm.append",
        "Link from .blend": "wm.link",
    }
    # The Export list's tool-panel entry — a launcher rather than a one-shot export, so
    # list002_init adds it separately (last, nearest the trigger row) with a tooltip.
    # Named so the dict key and that filter can't drift apart.
    _SCENE_EXPORTER = "Scene Exporter"

    _EXPORTERS = {
        _SCENE_EXPORTER: lambda slot: slot.sb.handlers.marking_menu.show("scene_exporter"),
        "Export FBX": "export_scene.fbx",
        "Export OBJ": "wm.obj_export",
        "Export glTF": "export_scene.gltf",
        "Export Collada": "wm.collada_export",
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.scene
        self.submenu = self.sb.loaded_ui.scene_submenu

    def header_init(self, widget):
        """Header menu — mirror of the Maya scene header (portable subset). ``b011`` (Fix Color
        Spaces) is a genuine Blender build (data maps → 'Non-Color' by map type). ``b013`` (Mesh
        Converter) is the DCC-agnostic extapps/mesh_convert tool, launched via the shared
        external_app handler exactly like Maya. Maya-only entries (Save to Original Scene, Fix OCIO,
        Toggle Command Ports) are omitted — see the parity overrides. Reused objectNames carry the
        Maya label verbatim (cross-DCC QSettings rule); ``b_cleanup`` is Blender-specific (Maya's
        b006 means the unrelated 'Cleanup Unknown')."""
        widget.menu.add("Separator", setTitle="Export")
        widget.menu.add(
            "QPushButton", setText="Export Scene", setObjectName="b018",
            setToolTip="Export the whole scene to FBX.\nOptions live on the submenu's Export list ▸ Export Scene entry (gear icon).",
        )
        widget.menu.add(
            "QPushButton", setText="Export Selection", setObjectName="b008",
            setToolTip="Export only the selected objects (FBX).",
        )
        widget.menu.add(
            "QPushButton", setText="Mesh Converter", setObjectName="b013",
            setToolTip="Open the FBX -> GLB converter window.\nBacked by godotengine/FBX2glTF; the binary is downloaded on first use.",
        )
        widget.menu.add(
            "QPushButton", setText="Maya Bridge", setObjectName="b010",
            setToolTip="Send the selected objects to a fresh Maya (export FBX + run a chosen import template).",
        )
        widget.menu.add(
            "QPushButton", setText="Unity Bridge", setObjectName="b016",
            setToolTip="Send the selected objects to a Unity project (export FBX + copy into Assets/).",
        )
        widget.menu.add("Separator", setTitle="Manage")
        widget.menu.add(
            "QPushButton", setText="Reference Manager", setObjectName="b001",
            setToolTip="Manage linked .blend libraries.",
        )
        widget.menu.add(
            "QPushButton", setText="Hierarchy Manager", setObjectName="b004",
            setToolTip="Diff/repair the scene hierarchy against a reference .blend.",
        )
        widget.menu.add(
            "QPushButton", setText="Naming", setObjectName="b005",
            setToolTip="Blender's native Batch Rename.",
        )
        widget.menu.add(
            "QPushButton", setText="Audio Clips", setObjectName="b003",
            setToolTip="Manage scene-wide audio clips in the Video Sequence Editor "
            "(add/remove/trim/sync).",
        )
        widget.menu.add(
            "QPushButton", setText="Blendshape Animator", setObjectName="b015",
            setToolTip="Build a morph between two meshes as a shape key, sculpt in-between "
            "tweens to customize the curve, and apply them back.",
        )
        widget.menu.add("Separator", setTitle="Fix")
        widget.menu.add(
            "QPushButton", setText="Scene Cleanup", setObjectName="b_cleanup",
            setToolTip="Purge orphan datablocks (meshes, materials, images … with no users).",
        )
        widget.menu.add(
            "QPushButton", setText="Fix Color Spaces", setObjectName="b011",
            setToolTip="Set data textures (normal / roughness / metallic / height …) to "
            "'Non-Color' and color maps to 'sRGB', by map type — so PBR shading isn't gamma-wrong.",
        )
        widget.menu.add("Separator", setTitle="Diagnostics")
        widget.menu.add(
            self.sb.registered_widgets.PushButton, setText="Get Scene Info", setObjectName="tb001",
            setToolTip="Show an object / poly / material summary in a viewer.\n"
            "Use the option box to choose scope (Selected / Entire Scene).",
        )
        widget.menu.add(
            "QPushButton", setText="Scene Metadata", setObjectName="b017",
            setToolTip="Show the tool-authored metadata stored on the scene's data nodes "
            "(data_internal + data_export) as JSON — shot metadata, audio manifests, etc.\n"
            "Use Save in the viewer to write it to a .json file.",
        )

    def _open_file(self, filepath):
        try:
            bpy.ops.wm.open_mainfile(filepath=filepath)
        except RuntimeError as e:
            self.sb.message_box(
                f"Could not open:\n<hl>{ptk.format_path(filepath, 'file')}</hl>\n\n{e}"
            )

    # ------------------------------------------------------------------ list000  Recent Files
    def list000_init(self, widget):
        """Initialize Recent Files"""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up")
        recent_files = btk.get_recent_files(slice(0, 11))
        w1 = widget.add("Recent Files")
        truncated = ptk.truncate(recent_files, 65)
        w1.sublist.add(zip(truncated, recent_files))
        widget.setVisible(bool(recent_files))

    @Signals("on_item_interacted")
    def list000(self, item):
        """Recent Files"""
        data = item.item_data()
        if data:
            self._open_file(str(data))

    # ------------------------------------------------------------------ cmb002  Autosave
    def cmb002_init(self, widget):
        """Initialize Autosave (recent temp-dir .blend autosaves, newest first)."""
        recent_autosaves = btk.get_recent_autosave(filter_time=24)
        autosave_dict = {
            f"{stamp}  {ptk.format_path(path, 'file')}": path
            for path, stamp in recent_autosaves
        }
        widget.add(autosave_dict, header="Autosave:", clear=True)

    def cmb002(self, index, widget):
        """Autosave"""
        self._open_file(widget.items[index])

    # ------------------------------------------------------------------ list001/list002  Import/Export
    def list001_init(self, widget):
        """Initialize Import"""
        widget.fixed_item_height = 18
        # Lowest list in the submenu: open downward, covering the root row
        # (expand_down would hang the sublist below it instead).
        widget.apply_preset("expand_overlay")
        root = widget.add(
            "Import",
            setToolTip="Import a file (FBX / OBJ / Collada / Maya scene), or append/link from a .blend.",
        )
        root.sublist.add(list(self._IMPORTERS))

    @Signals("on_item_interacted")
    def list001(self, item):
        """Import"""
        entry = self._IMPORTERS.get(item.item_text())
        if callable(entry):
            entry(self)
        elif entry:
            self.invoke_op(entry)

    def _import_maya_scene(self):
        """Import a Maya scene (.ma/.mb) via ``btk.import_maya_scene`` — a headless-Maya
        FBX round-trip (fresh mayapy converts the scene; the FBX is imported and cleaned
        up). Blocking: a scene conversion takes tens of seconds (mayapy startup + license
        checkout), so a wait cursor covers the run. Requires a local Maya install."""
        src = self.sb.file_dialog(
            file_types=["*.ma", "*.mb"],
            title="Import Maya Scene",
            filter_description="Maya Scenes",
            allow_multiple=False,
        )
        if not src:
            return
        app = self.sb.QtWidgets.QApplication
        app.setOverrideCursor(self.sb.QtCore.Qt.WaitCursor)
        try:
            imported = btk.import_maya_scene(src)
        except Exception as e:
            self.sb.message_box(f"Maya scene import failed: <hl>{e}</hl>")
            return
        finally:
            app.restoreOverrideCursor()
        self.sb.message_box(
            f"Imported <hl>{len(imported)}</hl> object(s) from "
            f"<hl>{os.path.basename(src)}</hl>."
        )

    def list002_init(self, widget):
        """Initialize Export.

        The list expands upward, so it is populated in reverse: the LAST item
        added sits nearest the trigger row. The two tools go last — Scene
        Exporter, then Export Scene (the tb003 PushButton folded in from the old
        submenu button, option-box gear and all) closest to the cursor — with the
        native one-shot format exporters that used to live on the Export combobox
        stacking above them.
        """
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up")
        root = widget.add(
            "Export",
            setToolTip="Export the scene or selection (FBX / OBJ / glTF / Collada).",
        )
        one_shots = [k for k in self._EXPORTERS if k != self._SCENE_EXPORTER]
        root.sublist.add(one_shots[::-1])
        root.sublist.add(
            self._SCENE_EXPORTER,
            setToolTip="Batch-export via a configurable task/check pipeline (FBX/GLB).",
        )
        # Registration runs tb003_init (building the option-box menu), wires
        # clicked -> tb003, and binds self.submenu.tb003 so the header's plain
        # "Export Scene" entry (b018) can read the shared options.
        self.add_slot_widget(
            root.sublist,
            setObjectName="tb003",
            setText="Export Scene",
            setToolTip=(
                "Export the scene to FBX (and optionally GLB).\n"
                "Click the gear icon to configure scope, included types, and save location."
            ),
        )

    @Signals("on_item_interacted")
    def list002(self, item):
        """Export.

        tb003 never arrives here — its option-box wrap swapped it out of the list's
        item set, so the list no longer consumes its releases and its own clicked
        signal drives the slot (see ``Slots.add_slot_widget``).
        """
        entry = self._EXPORTERS.get(item.item_text())
        if callable(entry):
            entry(self)
        elif entry:
            self.invoke_op(entry)

    # ------------------------------------------------------------------ tb003  Scene Exporter
    def tb003_init(self, widget):
        """Initialize the Scene Exporter option box — the Blender counterpart of Maya's tb003.

        Every control maps to a native ``bpy.ops.export_scene.fbx`` parameter, so these are
        genuine builds (not stand-ins): scope→``use_selection``, the include toggles→``object_types``,
        Tangents→``use_tspace``, Embed→``path_mode``/``embed_textures``. Reused objectNames match the
        Maya exporter so the option state is shared across DCCs (the cross-DCC QSettings rule)."""
        if getattr(widget, "is_initialized", False):
            return
        widget.option_box.menu.setTitle("Export Options")
        cmb_scope = widget.option_box.menu.add(
            "QComboBox", setObjectName="cmb_scope",
            setToolTip=(
                "What to export:\n"
                "• Entire Scene — export the full scene\n"
                "• Selected Only — export only the current selection"
            ),
        )
        for text, data in [("Entire Scene", "all"), ("Selected Only", "selected")]:
            cmb_scope.addItem(text, data)

        cmb_save = widget.option_box.menu.add(
            "QComboBox", setObjectName="cmb_save",
            setToolTip=(
                "Where to write the exported file(s):\n"
                "• Alongside Scene File — same directory and basename as the open .blend\n"
                "• Prompt for File — choose the name and location each time"
            ),
        )
        for text, data in [("Alongside Scene File", "scene_dir"), ("Prompt for File", "prompt")]:
            cmb_save.addItem(text, data)

        chk_cameras = widget.option_box.menu.add(
            "QCheckBox", setText="Include Cameras", setObjectName="chk_cameras",
            setChecked=False,
            setToolTip=(
                "Include camera objects in the FBX (object_types += CAMERA).\n"
                "Whole-scene export only; disabled in Selected Only mode "
                "(cameras export only if selected)."
            ),
        )
        chk_lights = widget.option_box.menu.add(
            "QCheckBox", setText="Include Lights", setObjectName="chk_lights",
            setChecked=False,
            setToolTip=(
                "Include light objects in the FBX (object_types += LIGHT).\n"
                "Whole-scene export only; disabled in Selected Only mode "
                "(lights export only if selected)."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Include Skins", setObjectName="chk_skins",
            setChecked=False,
            setToolTip=(
                "Include armatures + skin deformation (object_types += ARMATURE).\n"
                "Available in both scopes — the armature and weights travel with the mesh."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Include Tangents/Binormals", setObjectName="chk_tangents",
            setChecked=True,
            setToolTip=(
                "Export per-vertex tangent space (use_tspace) — needed for correct normal "
                "mapping on game assets.\nRequires a UV map; untick for a faster export when "
                "tangents aren't needed (e.g. a photogrammetry mesh with a baked albedo)."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Embed Textures", setObjectName="chk_embed",
            setChecked=True,
            setToolTip=(
                "Pack texture files into the FBX so it is self-contained "
                "(path_mode=COPY, embed_textures).\nUntick to keep textures as external "
                "references — far smaller/faster when maps are large."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Also Export GLB", setObjectName="chk_glb",
            setChecked=False,
            setToolTip=(
                "After writing the FBX, also write a GLB beside it via Blender's native "
                "glTF 2.0 exporter (the don't-reinvent answer to Maya's FBX2glTF sidecar)."
            ),
        )

        # Cameras/lights are scene-level: in Selected Only mode they'd only export if
        # explicitly selected, so the "include all" intent doesn't apply — disable them.
        # The button label mirrors the scope so the submenu entry reads as what it will
        # do (QSettings restore re-fires the signal, so a persisted scope re-labels on
        # init too).
        def _sync_scope(_idx=None):
            whole_scene = cmb_scope.currentData() == "all"
            chk_cameras.setEnabled(whole_scene)
            chk_lights.setEnabled(whole_scene)
            widget.setText("Export Scene" if whole_scene else "Export Sel")

        cmb_scope.currentIndexChanged.connect(_sync_scope)
        _sync_scope()

    def tb003(self, widget):
        """Export Scene — FBX (+ optional GLB) using the configured options.

        Options always live on the submenu's tb003 (the PushButton carrying the option-box
        gear, created by list002_init as the Export list's first entry); the header entry is
        a plain button reaching the same slot, so read options off the submenu. If the Export
        list hasn't built yet (header clicked before the submenu initialized), force it."""
        opts_widget = getattr(self.submenu, "tb003", None)
        if opts_widget is None:
            self.sb.init_slot(self.submenu.list002)
            opts_widget = self.submenu.tb003
        if not getattr(opts_widget, "is_initialized", False):
            self.tb003_init(opts_widget)
            opts_widget.is_initialized = True

        menu = opts_widget.option_box.menu
        scope = menu.cmb_scope.currentData()
        save_mode = menu.cmb_save.currentData()
        selection_only = scope == "selected"
        # Cameras/lights are inert in Selected Only mode (see tb003_init); coerce to False
        # so a stale checked-but-disabled box can't leak through.
        include_cameras = menu.chk_cameras.isChecked() and not selection_only
        include_lights = menu.chk_lights.isChecked() and not selection_only
        include_skins = menu.chk_skins.isChecked()
        include_tangents = menu.chk_tangents.isChecked()
        embed_textures = menu.chk_embed.isChecked()
        also_glb = menu.chk_glb.isChecked()

        if selection_only and not self.selected_objects():
            self.sb.message_box("No objects selected.")
            return

        fbx_path = self._resolve_export_path(save_mode)
        if not fbx_path:
            return

        object_types = {"MESH", "EMPTY", "OTHER"}
        if include_cameras:
            object_types.add("CAMERA")
        if include_lights:
            object_types.add("LIGHT")
        if include_skins:
            object_types.add("ARMATURE")

        try:
            btk.FbxUtils.export(
                filepath=fbx_path,
                selection_only=selection_only,
                object_types=object_types,
                use_tspace=include_tangents,
                path_mode="COPY" if embed_textures else "AUTO",
                embed_textures=embed_textures,
            )
        # AttributeError covers a disabled io_scene_fbx add-on (the op wouldn't exist).
        except (RuntimeError, AttributeError) as e:
            self.sb.message_box(f"<b>FBX export failed.</b><br><small>{e}</small>")
            return

        msg = f"Exported FBX:<br><hl>{ptk.format_path(fbx_path, 'file')}</hl>"
        if also_glb:
            glb_path = os.path.splitext(fbx_path)[0] + ".glb"
            # Best-effort sidecar: the FBX already succeeded, so never let a missing/disabled
            # glTF add-on (AttributeError) or an export error turn into a traceback — degrade.
            try:
                bpy.ops.export_scene.gltf(
                    filepath=glb_path,
                    export_format="GLB",
                    use_selection=selection_only,
                    export_cameras=include_cameras,
                    export_lights=include_lights,
                )
                msg += f"<br>+ GLB: <hl>{ptk.format_path(glb_path, 'file')}</hl>"
            except Exception as e:
                msg += f"<br><small>(GLB skipped: {e})</small>"
        self.sb.message_box(msg)

    def _resolve_export_path(self, save_mode):
        """Resolve the FBX output path for ``save_mode`` ('scene_dir' next to the .blend, or
        'prompt' via a save dialog). Returns the path, or None to cancel."""
        blend_path = bpy.data.filepath or ""
        if save_mode == "prompt":
            base = os.path.splitext(os.path.basename(blend_path))[0] or "untitled"
            start = os.path.join(os.path.dirname(blend_path), base + ".fbx")
            picked, _ = self.sb.QtWidgets.QFileDialog.getSaveFileName(
                self.ui, "Export FBX As", start, "FBX (*.fbx)"
            )
            if not picked:
                return None
            return picked if picked.lower().endswith(".fbx") else picked + ".fbx"
        if not blend_path:
            self.sb.message_box(
                "Scene has not been saved yet.<br>Save the .blend first, or choose "
                "<hl>Prompt for File</hl> in the export options."
            )
            return None
        return os.path.splitext(blend_path)[0] + ".fbx"

    def b011(self):
        """Fix Color Spaces — set data textures to 'Non-Color' / color maps to 'sRGB' by map type
        (the Blender analogue of Maya's OCIO color-space repair; see ``btk.fix_color_spaces``)."""
        changed = btk.fix_color_spaces()
        if not changed:
            self.sb.message_box("Fix Color Spaces: <hl>nothing to change</hl>.")
            return
        detail = "".join(
            f"<br> • {name}: {old or '∅'} → {new}"
            for name, (old, new) in sorted(changed.items())
        )
        self.sb.message_box(
            f"Fix Color Spaces: updated <hl>{len(changed)}</hl> image(s).{detail}"
        )

    def b001(self):
        """Reference Manager (library links — File ▸ Link manager panel)."""
        self.sb.handlers.marking_menu.show("reference_manager")

    def b010(self):
        """Maya Bridge — send the selection to a fresh Maya (btk.MayaBridge)."""
        self.sb.handlers.marking_menu.show("maya_bridge")

    def b016(self):
        """Unity Bridge — send the selection to a Unity project's Assets/ (btk.UnityBridge).
        Native blendertk panel (env_utils/unity_bridge), 1:1 with mayatk's; exposed here in the
        Scene menu mirroring Maya's scene.py b016 (Marmoset / Substance stay in the Materials
        menu's External group)."""
        self.sb.handlers.marking_menu.show("unity_bridge")

    def b005(self):
        """Naming — open the panel (Find / Rename / Convert Case / Strip Chars / Suffix by
        Location / Suffix by Type, each with an option box), served from blendertk by the
        BlenderUiHandler, mirroring Maya's Naming window (replaces the native Batch Rename op)."""
        self.sb.handlers.marking_menu.show("naming")

    def b018(self):
        """Export Scene — header-menu launcher for tb003 (the submenu Export
        list's entry that carries the option box). A distinct objectName
        because a slot file must not add two widgets named tb003 (mirrors
        Maya's b018)."""
        self.tb003(None)

    def b008(self):
        """Export Selection (FBX, selected objects only)."""
        if not self.selected_objects():
            self.sb.message_box("Export Selection requires a selection.")
            return
        self.invoke_op("export_scene.fbx", use_selection=True)

    def b013(self):
        """Mesh Converter (FBX -> GLB).

        Launches the DCC-agnostic extapps/mesh_convert tool (pythontk.MeshConvert /
        FBX2glTF) through the shared external_app handler — the same handler the
        materials bridges use — defaulting its source directory to the current
        .blend's folder. Maya's 'From FBX references' provider has no Blender
        counterpart (Blender links .blend libraries, not FBX, and an imported FBX
        leaves no live reference to trace back), so no fbx_provider is wired; the
        converter's own file picker is used to choose inputs.
        """
        ui = self.sb.handlers.external_app.launch("mesh_convert", show=False)
        blend_path = bpy.data.filepath or ""
        if blend_path:
            ui.slots.source_dir = os.path.dirname(blend_path)
        self.sb.handlers.marking_menu.show(ui)

    def b_cleanup(self):
        """Scene Cleanup — purge orphan datablocks (no users / no fake user)."""
        removed = btk.cleanup_scene()
        if not removed:
            self.sb.message_box("Scene Cleanup: <hl>nothing to purge</hl>.")
            return
        total = sum(removed.values())
        detail = "".join(f"<br> • {coll}: {n}" for coll, n in sorted(removed.items()))
        self.sb.message_box(f"Scene Cleanup: purged <hl>{total}</hl> orphan(s).{detail}")

    # ------------------------------------------------------------------ tb001  Get Scene Info
    # Section toggles (key -> Maya objectName chk_section_<key>, label, default, tooltip). Mirror of
    # the Maya SceneAnalyzer sections; drives btk.analyze_scene's budgeted, sectioned audit.
    _TB001_SECTIONS = (
        ("summary", "Executive Summary", True, "Scene-wide totals + profile + over-budget count."),
        ("fix_first", "Fix First (High Impact)", True, "Worst meshes exceeding the triangle budget."),
        ("pareto", "Pareto View", True, "Top-10 contributors to total triangles."),
        ("offenders", "Top Issues by Asset", True, "Per-asset over-budget table."),
        ("categories", "Top Offenders by Category", True, "Multi-material meshes."),
        ("textures", "Textures", True, "Texture dimension histogram (1K/2K/4K+)."),
        ("pipeline", "Pipeline Integrity", True, "Missing referenced texture files."),
        ("assumptions", "Data Assumptions", True, "Methodology footnotes (budget, triangulation)."),
    )

    def tb001_init(self, widget):
        # cmb_scope1 / cmb_profile / lbl_sections / chk_section_<key> reuse the Maya names + labels.
        m = widget.option_box.menu
        m.setTitle("Get Scene Info")
        cmb = m.add(
            "QComboBox", setObjectName="cmb_scope1",
            setToolTip="Selected Objects: audit only the selection.\nEntire Scene: audit every object.",
        )
        for label, data in [("Selected Objects", "selection"), ("Entire Scene", "all")]:
            cmb.addItem(label, data)
        cmb_profile = m.add(
            "QComboBox", setObjectName="cmb_profile",
            setToolTip="Adaptive (Game Ready): per-mesh triangle budget scaled by object size.\n"
            "Generic: a flat 100k triangle budget across all meshes.",
        )
        for label, data in [("Adaptive (Game Ready)", True), ("Generic", False)]:
            cmb_profile.addItem(label, data)
        m.add(
            self.sb.registered_widgets.Label, setText="Sections:", setObjectName="lbl_sections",
            setToolTip="Pick which report sections to render.",
        )
        for key, label, default_on, tooltip in self._TB001_SECTIONS:
            m.add("QCheckBox", setText=label, setObjectName=f"chk_section_{key}",
                  setChecked=default_on, setToolTip=tooltip)

    def tb001(self, widget):
        """Get Scene Info — render the budgeted, sectioned audit (btk.analyze_scene) to the viewer."""
        m = widget.option_box.menu
        scope = m.cmb_scope1.currentData() or "selection"
        if scope == "selection":
            objects = self.selected_objects()
            if not objects:
                self.sb.message_box(
                    "<hl>Nothing selected</hl> — select objects, or pick 'Entire Scene'."
                )
                return
        else:
            objects = None
        adaptive = m.cmb_profile.currentData()
        adaptive = True if adaptive is None else bool(adaptive)
        sections = [
            key for key, _l, _d, _t in self._TB001_SECTIONS
            if getattr(m, f"chk_section_{key}").isChecked()
        ]
        if not sections:
            self.sb.message_box("<hl>No sections selected</hl> — tick at least one section.")
            return
        report = btk.analyze_scene(objects, adaptive=adaptive, sections=sections)
        # Named report_html (not ``html``) so the module-level ``import html`` used by
        # b017's ``html.escape`` stays reachable — a bare ``html`` local would shadow it.
        report_html = "".join(report.get(key, "") for key, _l, _d, _t in self._TB001_SECTIONS)
        if not report_html:
            self.sb.message_box("<hl>No scene info</hl> available.")
            return
        self.sb.text_view_dialog(
            report_html, "Ok", title="Get Scene Info", size=(640, 600), monospace=False
        )

    def b004(self):
        """Hierarchy Manager — diff/repair the scene hierarchy against a reference .blend
        (native blendertk panel, 1:1 with mayatk's ``hierarchy_manager`` for Diff/Fix; Pull
        isn't ported yet — see ``blendertk.env_utils.hierarchy_manager`` for why)."""
        self.sb.handlers.marking_menu.show("hierarchy_manager")

    def b003(self):
        """Audio Clips — native blendertk panel over the Video Sequence Editor (add/remove/
        trim a clip + scene-range sync), 1:1 role with mayatk's ``AudioClipsSlots``. Mayatk's
        launcher lives inside the (not-yet-ported) Shot Manifest panel; this sits here in
        Scene ▸ Manage instead until that panel exists — see
        ``blendertk.audio_utils.audio_clips`` for the scope. ``b003`` (not Maya's ``b012``,
        "Toggle Command Ports" — a Maya command-port concept with no Blender analogue) to
        avoid a cross-DCC objectName collision (see ``test_blender_slots.py``'s semantics
        guard); ``b003`` is unused by Maya's ``scene.py``."""
        self.sb.handlers.marking_menu.show("audio_clips")

    def b015(self):
        """Blendshape Animator — native blendertk panel (base+target mesh -> keyed shape key,
        driver-driven corrective "tween" shapes for a custom curve); the panel/engine is 1:1 with
        mayatk's ``BlendshapeAnimatorSlots`` (Maya's blendShape multi-target in-betweens have no
        direct Blender equivalent; see ``blendertk.anim_utils.blendshape_animator.applicator``
        for how they're rebuilt). This button itself is a new, Blender-only marking-menu entry
        point, not a mirror of an existing tentacle launcher: mayatk's ``BlendshapeAnimatorSlots``
        has no tentacle-Maya wiring of its own (it's only reachable via
        ``MayaUiHandler.instance().show("blendshape_animator")``)."""
        self.sb.handlers.marking_menu.show("blendshape_animator")

    def b017(self):
        """Scene Metadata — dump the tool-authored data-node channels to the viewer (mirror of
        Maya's ``b017``; reads ``btk.DataNodes.dump`` — every custom property on the
        ``data_internal`` / ``data_export`` Empties, JSON-decoded). The viewer's Save button
        writes the same report to a ``.json`` file."""
        report = btk.DataNodes.format_dump()
        if not report:
            self.sb.message_box(
                "<hl>No scene metadata</hl> is stored — this scene has no "
                "<b>data_internal</b> / <b>data_export</b> channels yet."
            )
            return

        dlg = self.sb.text_view_dialog(
            f"<pre>{html.escape(report)}</pre>",
            "Save", "Ok",
            title="Scene Metadata", size=(720, 560), monospace=True, word_wrap=False,
        )
        # "Save" is an Accept-role button (it closes the viewer); wire the export via the
        # sanctioned realtime hook so the same click writes the file.
        dlg.button_box.clicked.connect(
            lambda btn, text=report: self._export_scene_metadata(btn, text)
        )

    def _export_scene_metadata(self, button, text):
        """Write the Scene Metadata report to a chosen ``.json`` (viewer Save button)."""
        if button.text().replace("&", "") != "Save":
            return
        blend_path = bpy.data.filepath or ""
        base = (os.path.splitext(os.path.basename(blend_path))[0] or "untitled") + "_scene_metadata.json"
        start = os.path.join(os.path.dirname(blend_path), base)
        picked, _ = self.sb.QtWidgets.QFileDialog.getSaveFileName(
            self.ui, "Save Scene Metadata As", start, "JSON (*.json)"
        )
        if not picked:
            return
        if not picked.lower().endswith(".json"):
            picked += ".json"
        ptk.FileUtils.atomic_write_text(picked, text)
        self.sb.message_box(f"Saved scene metadata to <hl>{ptk.format_path(picked, 'file')}</hl>.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
