# !/usr/bin/python
# coding=utf-8
import os

import maya.cmds as cmds
import maya.mel as mel
import pythontk as ptk
import mayatk as mtk
from uitk import Signals
from uitk.widgets.footer import FooterStatusController
from mayatk.core_utils.script_job_manager import ScriptJobManager
from tentacle.slots.maya._slots_maya import SlotsMaya


class SceneSlots(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.scene
        self.submenu = self.sb.loaded_ui.scene_submenu
        self._footer_controller = self._create_footer_controller()

    def header_init(self, widget):
        """Initialize Header"""
        if not widget.is_initialized:
            widget.menu.add("Separator", setTitle="Export")
            widget.menu.add(
                "QPushButton",
                setToolTip="Export scene assets with environment checks and presets.",
                setText="Scene Exporter",
                setObjectName="b002",
            )
            widget.menu.add(
                "QPushButton",
                setText="Export Scene",
                setObjectName="tb003",
                setToolTip="Export the scene to FBX (and optionally GLB) using the configured options.\nOptions live on the submenu's Export button (gear icon).",
            )
            widget.menu.add(
                "QPushButton",
                setText="Mesh Converter",
                setObjectName="b013",
                setToolTip="Open the FBX -> GLB converter window.\nBacked by godotengine/FBX2glTF; the binary is downloaded on first use.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Blender Bridge",
                setObjectName="b010",
                setToolTip="Send the selected objects to a fresh Blender (export FBX + run a chosen import template).",
            )
            widget.menu.add(
                "QPushButton",
                setText="Unity Bridge",
                setObjectName="b016",
                setToolTip="Send the selected objects to a Unity project (export FBX + copy into Assets/).",
            )
            widget.menu.add("Separator", setTitle="Manage")
            widget.menu.add(
                "QPushButton",
                setText="Reference Manager",
                setObjectName="b001",
                setToolTip="Open the reference manager.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Hierarchy Manager",
                setObjectName="b004",
                setToolTip="Open the hierarchy manager.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Naming",
                setObjectName="b005",
                setToolTip="Open the naming tool.",
            )
            widget.menu.add("Separator", setTitle="Recover")
            widget.menu.add(
                "QPushButton",
                setText="Save to Original Scene",
                setObjectName="b014",
                setToolTip="Save the currently open autosave back to the original scene file.\nEnabled only when an autosave is open and the original is locatable.",
            )
            widget.menu.add("Separator", setTitle="Fix")
            widget.menu.add(
                "QPushButton",
                setText="Cleanup Unknown",
                setObjectName="b006",
                setToolTip="Fix common scene issues:\n• Remove unknown/legacy nodes/plugins/expressions",
            )
            widget.menu.add(
                "QPushButton",
                setText="Fix OCIO",
                setObjectName="b009",
                setToolTip="Fix Maya Color Management / OCIO config preferences.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Fix Color Spaces",
                setObjectName="b011",
                setToolTip="Fix missing color space errors on file texture nodes.\nAuto-detects sRGB vs Raw based on texture type.",
            )
            widget.menu.add("Separator", setTitle="Diagnostics")
            widget.menu.add(
                self.sb.registered_widgets.PushButton,
                setText="Get Scene Info",
                setObjectName="tb001",
                setToolTip=(
                    "Show a formatted scene analysis report in the viewer "
                    "(poly count, draw calls, textures, fix-first items). "
                    "Profile (Adaptive / Generic) is set via the option box."
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="Toggle Command Ports",
                setObjectName="b012",
                setToolTip="Toggle Maya command ports on/off (MEL :7001, Python :7002).\nUsed for external editor connections.",
            )

    @Signals("textChanged", "returnPressed")
    def txt000(self, widget):
        """Workspace Scenes: Filter"""
        self.ui.cmb000.init_slot()

    def cmb000_init(self, widget):
        """Initialize Workspace Scenes"""
        if not widget.is_initialized:
            widget.refresh_on_show = True  # Call this method on show
            mgr = ScriptJobManager.instance()
            mgr.subscribe(
                "workspaceChanged", self._on_workspace_changed, owner=widget
            )
            mgr.connect_cleanup(widget, owner=widget)

        include = self.ui.txt000.text() or None

        scenes = {
            ptk.format_path(f, "file"): f
            for f in mtk.get_workspace_scenes(
                recursive=True, inc=include, basename_only=True
            )
        }
        widget.add(
            scenes,
            header="Scenes:",
            clear=True,
        )

    def _ensure_fbx_plugin(self):
        """Load fbxmaya if not already loaded. Returns True on success."""
        if cmds.pluginInfo("fbxmaya", query=True, loaded=True):
            return True
        try:
            cmds.loadPlugin("fbxmaya", quiet=True)
            return True
        except Exception as e:
            self.sb.message_box(f"Could not load FBX plugin:\n{e}")
            return False

    def _eval_fbx_uicallback(self, suffix):
        """Run ``FBXUICallBack -1 "<suffix>"`` after ensuring fbxmaya is loaded.

        Without the plugin, the MEL command does not exist and raises a
        confusing parse error in the script editor.
        """
        if not self._ensure_fbx_plugin():
            return
        try:
            mel.eval(f'FBXUICallBack -1 "{suffix}"')
        except Exception as e:
            self.sb.message_box(f"FBX UI callback failed:\n{e}")

    def cmb000(self, index, widget):
        """Workspace Scenes"""
        scene = widget.items[index]
        cmds.file(scene, open=True, force=True)

    def cmb002_init(self, widget):
        """Initialize Autosave"""
        # Fetch recent autosave files
        recent_autosaves = mtk.get_recent_autosave(
            filter_time=24, timestamp_format="%H:%M:%S"
        )

        # Prepare dictionary for ComboBox: key is 'path + timestamp', value is 'path'
        autosave_dict = {
            f"{i[1]}  {ptk.format_path(i[0], 'file')}": i[0] for i in recent_autosaves
        }

        # Add items to the ComboBox
        widget.add(
            autosave_dict,
            header="Autosave:",
            clear=True,
        )

    def cmb002(self, index, widget):
        """Autosave: reopen a recent autosaved scene file."""
        file = widget.items[index]
        try:
            cmds.file(file, open=True, force=True)
        except RuntimeError as e:
            self.sb.message_box(
                f"Could not open autosave:\n<hl>{ptk.format_path(file, 'file')}</hl>\n\n{e}"
            )

    def cmb003_init(self, widget):
        """Initialize Import"""
        widget.add(
            [
                "Import File",
                "Import Options",
                "FBX Import Presets",
                "OBJ Import Presets",
            ],
            header="Import",
        )

    def cmb003(self, index, widget):
        """Import: import a file, or open import / FBX / OBJ preset options."""
        text = widget.items[index]
        if text == "Import File":  # Import
            mel.eval("Import")
        elif text == "Import Options":  # Import options
            mel.eval("ImportOptions")
        elif text == "FBX Import Presets":  # FBX Import Presets
            self._eval_fbx_uicallback('editImportPresetInNewWindow" "fbx')
        elif text == "OBJ Import Presets":  # Obj Import Presets
            self._eval_fbx_uicallback('editImportPresetInNewWindow" "obj')

    def cmb004_init(self, widget):
        """Initialize Export"""
        items = [
            "Export Selection",
            "Export All",
            "Send to Unreal",
            "Send to Unity",
            "GoZ",
            "Send to 3dsMax: As New Scene",
            "Send to 3dsMax: Update Current",
            "Send to 3dsMax: Add to Current",
            "Export to Offline File",
            "Export Options",
            "FBX Export Presets",
            "OBJ Export Presets",
        ]
        widget.add(items, header="Export")

    def cmb004(self, index, widget):
        """Export: export the selection or whole scene (FBX, Send to Unreal, etc.)."""
        text = widget.items[index]
        if text == "Export Selection":
            self._ensure_fbx_plugin()
            mel.eval("ExportSelection")
        elif text == "Export All":
            mel.eval("Export")
        elif text == "Send to Unreal":
            mel.eval("SendToUnrealSelection")
        elif text == "Send to Unity":
            mel.eval("SendToUnitySelection")
        elif text == "GoZ":
            mel.eval(
                'print("GoZ"); source"C:/Users/Public/Pixologic/GoZApps/Maya/GoZBrushFromMaya.mel"; source "C:/Users/Public/Pixologic/GoZApps/Maya/GoZScript.mel";'
            )
        elif text == "Send to 3dsMax: As New Scene":  # Send to 3dsMax: As New Scene
            mel.eval("SendAsNewScene3dsMax")
        elif text == "Send to 3dsMax: Update Current":  # Send to 3dsMax: Update Current
            mel.eval("UpdateCurrentScene3dsMax")
        elif text == "Send to 3dsMax: Add to Current":  # Send to 3dsMax: Add to Current
            mel.eval("AddToCurrentScene3dsMax")
        elif text == "Export to Offline File":  # Export to Offline File
            mel.eval("ExportOfflineFileOptions")
        elif text == "Export Options":  # Export options
            mel.eval("ExportSelectionOptions")
        elif text == "FBX Export Presets":  # FBX Export Presets
            self._eval_fbx_uicallback('editExportPresetInNewWindow" "fbx')
        elif text == "OBJ Export Presets":  # Obj Export Presets
            self._eval_fbx_uicallback('editExportPresetInNewWindow" "obj')

    def cmb005_init(self, widget):
        """Initialize Recent Files"""
        recent_files = mtk.get_recent_files(slice(0, 20))
        truncated = ptk.truncate(recent_files, 165)
        widget.add(zip(truncated, recent_files), header="Recent Files", clear=True)

    def cmb005(self, index: int, widget):
        """Recent Files"""
        force = not mtk.get_env_info("scene_modified")
        cmds.file(widget.items[index], open=True, force=force, ignoreVersion=True)

    def list000_init(self, widget):
        """Initialize Recent Files"""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up")
        recent_files = mtk.get_recent_files(slice(0, 11))
        w1 = widget.add("Recent Files")
        truncated = ptk.truncate(recent_files, 65)
        w1.sublist.add(zip(truncated, recent_files))
        widget.setVisible(bool(recent_files))

    @Signals("on_item_interacted")
    def list000(self, item):
        """Recent Files"""
        data = item.item_data()
        cmds.file(data, open=True, force=True)

    def _on_workspace_changed(self):
        """Maya workspaceChanged scriptJob handler — refresh dependent UI."""
        self.ui.cmb000.init_slot()
        if self._footer_controller:
            self._footer_controller.update()

    def _create_footer_controller(self):
        footer = getattr(self.ui, "footer", None)
        if not footer:
            return None
        return FooterStatusController(
            footer=footer,
            resolver=self._resolve_workspace_text,
            default_text="No workspace set",
            truncate_kwargs={"length": 96, "mode": "middle"},
        )

    def _resolve_workspace_text(self) -> str:
        return mtk.get_env_info("workspace_dir") or ""

    def b000(self):
        """Autosave: Open Directory"""
        autosave_dir = os.environ.get("MAYA_AUTOSAVE_FOLDER", "")
        if not autosave_dir:
            return
        dirs = autosave_dir.split(";")[0]

        try:
            os.startfile(ptk.format_path(dirs))

        except FileNotFoundError:
            self.sb.message_box("The system cannot find the file specified.")

    def b001(self):
        """Open Reference Manager"""
        self.sb.handlers.marking_menu.show("reference_manager")

    def b002(self):
        """Scene Exporter"""
        self.sb.handlers.marking_menu.show("scene_exporter")

    def b010(self):
        """Blender Bridge — send the selection to a fresh Blender (mtk.BlenderBridge)."""
        self.sb.handlers.marking_menu.show("blender_bridge")

    def b016(self):
        """Unity Bridge — send the selection to a Unity project's Assets/ (mtk.UnityBridge)."""
        self.sb.handlers.marking_menu.show("unity_bridge")

    def tb003_init(self, widget):
        """Initialize Export."""
        if not widget.is_initialized:
            widget.option_box.menu.setTitle("Export Options")
            cmb_scope = widget.option_box.menu.add(
                "QComboBox",
                setObjectName="cmb_scope",
                setToolTip=(
                    "What to export:\n"
                    "• Entire Scene — export the full scene\n"
                    "• Selected Only — export only the current selection"
                ),
            )
            for text, data in [("Entire Scene", "all"), ("Selected Only", "selected")]:
                cmb_scope.addItem(text, data)

            cmb_save = widget.option_box.menu.add(
                "QComboBox",
                setObjectName="cmb_save",
                setToolTip=(
                    "Where to write the exported file(s):\n"
                    "• Alongside Scene File — same directory and basename as the open scene\n"
                    "• Prompt for File — choose the name and location each time "
                    "(filename pre-filled from the scene, editable)"
                ),
            )
            for text, data in [
                ("Alongside Scene File", "scene_dir"),
                ("Prompt for File", "prompt"),
            ]:
                cmb_save.addItem(text, data)

            chk_cameras = widget.option_box.menu.add(
                "QCheckBox",
                setText="Include Cameras",
                setObjectName="chk_cameras",
                setChecked=False,
                setToolTip=(
                    "Include camera nodes in the FBX export.\n"
                    "Applies to whole-scene export only; disabled in "
                    "Selected Only mode (cameras export only if selected)."
                ),
            )
            chk_lights = widget.option_box.menu.add(
                "QCheckBox",
                setText="Include Lights",
                setObjectName="chk_lights",
                setChecked=False,
                setToolTip=(
                    "Include light nodes in the FBX export.\n"
                    "Applies to whole-scene export only; disabled in "
                    "Selected Only mode (lights export only if selected)."
                ),
            )
            widget.option_box.menu.add(
                "QCheckBox",
                setText="Include Skins",
                setObjectName="chk_skins",
                setChecked=False,
                setToolTip=(
                    "Include skin clusters / skinning data in the FBX export.\n"
                    "Available in both scopes — skin weights travel with the "
                    "selected mesh."
                ),
            )
            widget.option_box.menu.add(
                "QCheckBox",
                setText="Include Tangents/Binormals",
                setObjectName="chk_tangents",
                setChecked=True,
                setToolTip=(
                    "Export per-vertex tangents and binormals — needed for "
                    "correct normal mapping on game assets.\n"
                    "On dense meshes this roughly doubles export time and file "
                    "size; untick for a faster export when tangents aren't needed "
                    "(e.g. photogrammetry meshes with a baked albedo)."
                ),
            )
            widget.option_box.menu.add(
                "QCheckBox",
                setText="Embed Textures",
                setObjectName="chk_embed",
                setChecked=True,
                setToolTip=(
                    "Copy texture files into the FBX so it is self-contained.\n"
                    "Untick to keep textures as external references — far "
                    "smaller/faster when maps are large (e.g. an 8K "
                    "photogrammetry texture already sitting beside the mesh)."
                ),
            )
            widget.option_box.menu.add(
                "QCheckBox",
                setText="Also Export GLB",
                setObjectName="chk_glb",
                setChecked=False,
                setToolTip=(
                    "After writing the FBX, also produce a GLB sidecar via\n"
                    "pythontk's MeshConvert (FBX2glTF). The FBX2glTF binary\n"
                    "is downloaded automatically on first use."
                ),
            )

            # Cameras and lights are scene-level categories: in Selected Only
            # mode they'd only export if explicitly selected, so the
            # "include all" intent doesn't apply — disable them. Skins are
            # intrinsic to the selected mesh, so they stay enabled in both
            # scopes.
            def _sync_scope(_idx=None):
                whole_scene = cmb_scope.currentData() == "all"
                chk_cameras.setEnabled(whole_scene)
                chk_lights.setEnabled(whole_scene)

            cmb_scope.currentIndexChanged.connect(_sync_scope)
            _sync_scope()

    # Triangle count at/above which an export with a mesh-cost-scaling option
    # (tangents) is slow enough on dense geometry — photogrammetry scans,
    # sculpts — to be worth a heads-up before the blocking write. Tunable.
    _DENSE_TRI_THRESHOLD = 5_000_000

    def _confirm_dense_export(self, selection_only, include_tangents):
        """Warn before a dense + taxing FBX export; return False if cancelled.

        Returns True (proceed) for the common, non-taxing case so the normal
        path is untouched — the dialog only appears when the export set is
        dense AND tangents are on, the combination that turns a quick export
        into a multi-minute one. ``message_box`` returns the clicked button
        text (or None if dismissed), so anything but "Yes" cancels.
        """
        if not include_tangents:
            return True
        meshes = (
            cmds.ls(selection=True, dag=True, type="mesh", noIntermediate=True)
            if selection_only
            else cmds.ls(type="mesh", noIntermediate=True)
        ) or []
        if not meshes:
            return True
        tris = cmds.polyEvaluate(meshes, triangle=True)
        if not isinstance(tris, int) or tris < self._DENSE_TRI_THRESHOLD:
            return True
        choice = self.sb.message_box(
            f"This export covers <hl>{tris:,}</hl> triangles with "
            f"<hl>Include Tangents/Binormals</hl> enabled, which can be slow "
            f"on dense meshes.<br><br>Untick it in the export options for a "
            f"much faster export.<br><br>Proceed anyway?",
            "Yes",
            "No",
        )
        return choice == "Yes"

    def tb003(self, widget):
        """Export Scene (FBX + optional GLB) using the configured options."""
        # Options always live on the submenu's tb003 (the PushButton with the
        # option_box gear). The header-menu entry is a plain QPushButton — it
        # reaches us via the same slot name but has no option_box of its own.
        opts_widget = self.submenu.tb003
        if not getattr(opts_widget, "is_initialized", False):
            self.tb003_init(opts_widget)
            opts_widget.is_initialized = True

        menu = opts_widget.option_box.menu
        scope = menu.cmb_scope.currentData()
        save_mode = menu.cmb_save.currentData()
        selection_only = scope == "selected"
        # Cameras/lights are inert in Selected Only mode (see tb003_init);
        # coerce to False so a stale checked-but-disabled box can't leak through.
        include_cameras = menu.chk_cameras.isChecked() and not selection_only
        include_lights = menu.chk_lights.isChecked() and not selection_only
        include_skins = menu.chk_skins.isChecked()
        include_tangents = menu.chk_tangents.isChecked()
        embed_textures = menu.chk_embed.isChecked()
        also_glb = menu.chk_glb.isChecked()
        if selection_only and not cmds.ls(selection=True):
            self.sb.message_box("No objects selected.")
            return

        if not self._confirm_dense_export(selection_only, include_tangents):
            return

        scene_path = cmds.file(query=True, sceneName=True) or ""

        if save_mode == "prompt":
            base = (
                os.path.splitext(os.path.basename(scene_path))[0]
                if scene_path
                else "untitled"
            )
            start_dir = (
                os.path.dirname(scene_path)
                if scene_path
                else (cmds.workspace(query=True, rootDirectory=True) or "")
            )
            # fileMode=0 is a save-style "any file" dialog; passing the full
            # default path as startingDirectory pre-fills an editable filename.
            picked = cmds.fileDialog2(
                fileMode=0,
                caption="Export FBX As",
                okCaption="Export",
                fileFilter="FBX (*.fbx)",
                dialogStyle=2,
                startingDirectory=os.path.join(start_dir, base + ".fbx"),
            )
            if not picked:
                return
            fbx_path = picked[0]
            if not fbx_path.lower().endswith(".fbx"):
                fbx_path += ".fbx"
        else:
            if not scene_path:
                self.sb.message_box(
                    "Scene has not been saved yet.<br>"
                    "Save the scene first, or choose <hl>Prompt for File</hl>."
                )
                return
            fbx_path = os.path.splitext(scene_path)[0] + ".fbx"

        # FBXExport is a single blocking call that scales with poly count, so on
        # dense scenes the UI sits frozen with no feedback. Run it inside the
        # footer progress context, painting a status before each heavy step
        # (tick() pumps the event loop) so it reads as working, not hung.
        # Tangents are the dominant controllable cost (~2x time/size on dense
        # meshes), hence the opt-out above. Let failures propagate out of the
        # context so it suppresses its "Complete" flash on a non-clean exit; the
        # `stage` marker disambiguates an FBX failure from a GLB one.
        stage = "fbx"
        glb_path = None
        try:
            with self.sb.progress(
                text="Exporting FBX… dense scenes can take a while"
            ) as tick:
                tick()  # paint the status before the blocking export
                mtk.export_scene_as_fbx(
                    file_path=fbx_path,
                    selection_only=selection_only,
                    FBXExportCameras=include_cameras,
                    FBXExportLights=include_lights,
                    FBXExportSkins=include_skins,
                    FBXExportTangents=include_tangents,
                    FBXExportEmbeddedTextures=embed_textures,
                )
                if also_glb:
                    stage = "glb"
                    tick(text="Converting to GLB…")
                    glb_path = ptk.MeshConvert.fbx_to_glb(
                        fbx_path,
                        overwrite=True,
                        auto_install=True,
                        prompt=False,
                    )
        except Exception as e:
            if stage == "glb":
                self.sb.message_box(f"FBX exported, but GLB conversion failed:<br>{e}")
            else:
                self.sb.message_box(f"FBX export failed:<br>{e}")
            return

        if glb_path:
            self.sb.message_box(
                f"Exported <hl>{os.path.basename(fbx_path)}</hl> and "
                f"<hl>{os.path.basename(glb_path)}</hl>."
            )
        else:
            self.sb.message_box(
                f"Exported <hl>{os.path.basename(fbx_path)}</hl>."
            )

    def b004(self):
        """Open Hierarchy Manager"""
        self.sb.handlers.marking_menu.show("hierarchy_manager")

    def b005(self):
        """Open Naming Tool"""
        self.sb.handlers.marking_menu.show("naming")

    def b006(self):
        """Scene Cleanup"""
        mtk.Diagnostics.cleanup_scene()

    def b009(self):
        """Fix OCIO"""
        mtk.Diagnostics.fix_ocio()

    _TB001_PROFILES = (
        ("Adaptive (Game Ready)", True),
        ("Generic", False),
    )

    _TB001_SCOPES = (
        ("Selected Objects", "selection"),
        ("Entire Scene", "all"),
    )

    # Section toggles for the Get Scene Info option box. The key
    # column maps 1:1 to ``mayatk.SceneInfoSection`` identifiers; the
    # analyzer skips collection phases that no selected section needs
    # (notably texture file IO when Textures + Pipeline + Summary +
    # Fix First are all unchecked). Keep this in section render order.
    _TB001_SECTIONS = (
        ("summary", "Executive Summary", True,
         "Scene-wide totals: meshes, instances, triangles, slots, GPU memory."),
        ("fix_first", "Fix First (High Impact)", True,
         "Prioritized remediation items based on budget overshoot."),
        ("pareto", "Pareto View", True,
         "Top 10 contributors to total triangles and draw calls."),
        ("offenders", "Top Issues by Asset", True,
         "Per-asset offender list with findings and fix plan."),
        ("categories", "Top Offenders by Category", True,
         "Materials correlated with high slot meshes."),
        ("textures", "Textures", True,
         "Dimension histogram, 4K analysis, heaviest texture files. "
         "Unchecking this skips per-texture file-size IO — fastest win on heavy scenes."),
        ("pipeline", "Pipeline Integrity", True,
         "Missing project textures and their impact on top offenders."),
        ("assumptions", "Data Assumptions", True,
         "Methodology footnotes (compression, GPU sizing). Untick to hide the trailing assumptions block."),
    )

    def tb001_init(self, widget):
        """Get Scene Info — option box."""
        widget.option_box.menu.setTitle("Get Scene Info")

        cmb_scope = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_scope1",  # NOT cmb_scope — collides with tb003's scope combo
            setToolTip=(
                "Selected Objects: audit only what is selected — fastest.\n"
                "Entire Scene: audit every mesh in the scene — can take "
                "several seconds on heavy scenes."
            ),
        )
        for label, data in self._TB001_SCOPES:
            cmb_scope.addItem(label, data)

        cmb_profile = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_profile",
            setToolTip=(
                "Adaptive (Game Ready): adaptive triangle budgeting based on "
                "object size — the recommended profile for game-ready scenes.\n"
                "Generic: a flat triangle budget across all objects."
            ),
        )
        for label, data in self._TB001_PROFILES:
            cmb_profile.addItem(label, data)

        widget.option_box.menu.add(
            self.sb.registered_widgets.Label,
            setText="Sections:",
            setObjectName="lbl_sections",
            setToolTip="Pick which report sections to query and render.",
        )
        for key, label, default_on, tooltip in self._TB001_SECTIONS:
            widget.option_box.menu.add(
                "QCheckBox",
                setText=label,
                setObjectName=f"chk_section_{key}",
                setChecked=default_on,
                setToolTip=tooltip,
            )

    def tb001(self, widget):
        """Get Scene Info — render the audit report to the viewer dialog."""
        scope = widget.option_box.menu.cmb_scope1.currentData() or "selection"
        adaptive = widget.option_box.menu.cmb_profile.currentData()
        if adaptive is None:
            adaptive = True  # default to game-ready when nothing's picked

        sections = [
            key
            for key, _label, _default, _tip in self._TB001_SECTIONS
            if getattr(widget.option_box.menu, f"chk_section_{key}").isChecked()
        ]
        if not sections:
            self.sb.message_box(
                "<hl>No sections selected</hl>. Tick at least one section in "
                "the option menu."
            )
            return

        # ``objects=None`` lets SceneAnalyzer.analyze fall back to its
        # selection-based default. For "all" we hand it every mesh shape
        # in the scene; the analyzer's resolver filters intermediates
        # and components for us. Pre-check the empty case in both
        # branches so the user sees a clear message instead of a blank
        # viewer.
        if scope == "all":
            objects = cmds.ls(type="mesh", long=True, ni=True) or []
            if not objects:
                self.sb.message_box(
                    "<hl>No mesh geometry</hl> found in the scene."
                )
                return
        else:
            if not (cmds.ls(selection=True, long=True) or []):
                self.sb.message_box(
                    "<hl>Nothing selected</hl>. Select objects, or pick "
                    "'Entire Scene' from the option menu."
                )
                return
            objects = None

        # ``progress_adapter`` auto-syncs the bar's max from the analyzer's
        # ``(current, 100, message)`` callbacks on the first tick.
        with self.sb.progress(text="Working: Get Scene Info") as update:
            html_dict = mtk.SceneAnalyzer.format_audit_html(
                adaptive=bool(adaptive),
                objects=objects,
                progress_callback=self.sb.progress_adapter(update),
                sections=sections,
            )
        html = "".join(html_dict.values()) if html_dict else ""
        if not html:
            self.sb.message_box(
                "<hl>No scene info</hl> available — analyze returned no records."
            )
            return

        self.sb.text_view_dialog(
            html,
            "Ok",
            title="Get Scene Info",
            size=(820, 560),
            monospace=False,
        )

    def b011(self):
        """Fix Color Spaces"""
        mtk.Diagnostics.fix_missing_color_spaces(force_update=True)

    def b012(self):
        """Toggle Command Ports"""
        is_open, ports = mtk.MayaConnection.toggle_command_ports()
        port_lines = "".join(
            f"<br> \u2022 {port} ({src})" for port, src in ports.items()
        )
        state = "OPENED" if is_open else "CLOSED"
        self.sb.message_box(
            f"Command Ports <hl>{state}</hl>{port_lines}",
            timeout=4,
        )
        # Mirror to console
        console_lines = ", ".join(f"{p} ({s})" for p, s in ports.items())
        print(f"Command Ports {state}: {console_lines}")

    def b007(self):
        """Import file: import a file via Maya's Import dialog."""
        self.ui.cmb003.call_slot(0)

    def b008(self):
        """Export Selection"""
        self.ui.cmb004.call_slot(0)

    def b013(self):
        """Mesh Converter (FBX -> GLB)"""
        ui = self.sb.handlers.external_app.launch("mesh_convert", show=False)

        # Default the file dialog to the current scene's directory.
        scene_path = cmds.file(query=True, sceneName=True) or ""
        if scene_path:
            ui.slots.source_dir = os.path.dirname(scene_path)

        # Provider used by the header "From FBX references" toggle — returns
        # FBX paths found on selected reference nodes. Components and non-DAG types in
        # the selection raise on referenceQuery; skip them silently.
        def _selected_fbx_paths():
            sel = cmds.ls(selection=True, long=True, objectsOnly=True) or []
            paths = []
            for node in sel:
                try:
                    if not cmds.referenceQuery(node, isNodeReferenced=True):
                        continue
                    ref_path = cmds.referenceQuery(
                        node, filename=True, withoutCopyNumber=True
                    ) or ""
                except RuntimeError:
                    continue
                if ref_path.lower().endswith(".fbx"):
                    paths.append(ref_path)
            # Dedupe while preserving order.
            return list(dict.fromkeys(paths))

        ui.slots.fbx_provider = _selected_fbx_paths

        self.sb.handlers.marking_menu.show(ui)

    def b014_init(self, widget):
        """Initialize Save to Original Scene.

        Resolves the original scene for the currently open autosave (via
        `mtk.find_original_for_autosave`) and reflects it on the button:
        enabled state, tooltip with the full destination path, and button
        text showing the destination basename truncated to its first 10
        characters. Subscribes to `SceneOpened` / `NewSceneOpened` so the
        button stays in sync as the active scene changes.
        """
        if not widget.is_initialized:
            widget.refresh_on_show = True
            self._b014_widget = widget
            mgr = ScriptJobManager.instance()
            mgr.subscribe("SceneOpened", self._on_scene_changed, owner=self)
            mgr.subscribe("NewSceneOpened", self._on_scene_changed, owner=self)
            mgr.connect_cleanup(widget, owner=self)

        current = cmds.file(query=True, sceneName=True) or ""
        is_autosave = bool(current) and mtk.matches_autosave_pattern(
            os.path.basename(current)
        )
        original = mtk.find_original_for_autosave(current) if is_autosave else None

        widget.setEnabled(bool(original))
        if original:
            widget.setToolTip(f"Save current autosave back to:\n{original}")
            short = ptk.truncate(os.path.basename(original), 10, mode="end")
            widget.setText(f"Save to: {short}")
        else:
            widget.setText("Save to Original Scene")
            if is_autosave:
                widget.setToolTip(
                    "Could not resolve the original scene for this autosave."
                )
            else:
                widget.setToolTip("Only available when an autosave file is open.")

    def _on_scene_changed(self):
        """SceneOpened/NewSceneOpened handler — refresh b014 enable state."""
        btn = getattr(self, "_b014_widget", None)
        if btn is not None:
            self.b014_init(btn)

    def b014(self):
        """Save to Original Scene.

        Saves the currently open autosave file back to its resolved
        original path (shown in the button text and tooltip). The existing
        original is backed up to `<path>.bak` first; if a `.bak` already
        exists, a timestamped variant is used so prior backups are
        preserved. See `mtk.save_autosave_to_original`.
        """
        current = cmds.file(query=True, sceneName=True) or ""
        original = mtk.find_original_for_autosave(current)
        if not original:
            self.sb.message_box("Could not resolve the original scene.")
            return

        choice = self.sb.message_box(
            f"Save current autosave to:<br><hl>{original}</hl><br>"
            "(Existing file will be backed up alongside it.)",
            "Save",
            "Cancel",
        )
        if choice != "Save":
            return

        saved = mtk.save_autosave_to_original(original)
        if saved:
            self.sb.message_box(f"Saved to <hl>{os.path.basename(saved)}</hl>.")
        else:
            self.sb.message_box("Save failed. See script editor for details.")

    def b015(self):
        """Remove String From Object Names."""
        # asterisk denotes startswith*, *endswith, *contains*
        from_ = str(self.ui.t000.text())
        to = str(self.ui.t001.text())
        replace = self.ui.chk004.isChecked()
        selected = self.ui.chk005.isChecked()

        objects = cmds.ls(from_) or []  # Stores a list of all objects starting with 'from_'
        if selected:  # get user selected objects instead
            objects = cmds.ls(sl=True) or []
        from_ = from_.strip("*")  # strip modifier asterisk from user input

        for obj in objects:  # Get a list of it's direct parent
            relatives = cmds.listRelatives(obj, parent=1) or []
            # If that parent starts with group, it came in root level and is pasted in a group, so ungroup it
            if relatives and "group" in relatives[0]:
                cmds.ungroup(relatives[0])

            newName = to
            if replace:
                newName = obj.replace(from_, to)
            cmds.rename(obj, newName)  # Rename the object with the new name


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
