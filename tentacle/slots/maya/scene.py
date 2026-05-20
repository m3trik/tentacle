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
                "QPushButton",
                setText="Scene Audit",
                setObjectName="b010",
                setToolTip="Analyze scene for performance issues (poly count, draw calls, textures).",
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
        """Autosave"""
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
        """Import"""
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
        """Export"""
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

    def tb000_init(self, widget):
        """Initialize Set Workspace"""
        if not widget.is_initialized:
            widget.setToolTip(
                "Click to set the project directory. Current workspace shown in footer."
            )
            widget.option_box.menu.setTitle("Workspace Options")
            widget.option_box.menu.add(
                "QPushButton",
                setObjectName="lbl005",
                setText="Auto Set Workspace",
                setToolTip="Determine the workspace directory by moving up directory levels until a workspace is found.",
            )
            widget.option_box.menu.add(
                "QPushButton",
                setObjectName="lbl004",
                setText="Open Workspace Root",
                setToolTip="Open the project root directory.",
            )

            from uitk.widgets.optionBox.options.recent_values import RecentValuesOption

            self._recent_workspaces = RecentValuesOption(
                wrapped_widget=widget,
                settings_key="workspace_recent_projects",
                max_recent=10,
            )
            widget.option_box.add_option(self._recent_workspaces)

            # Seed from Maya's recent projects (only valid workspaces)
            if not self._recent_workspaces.recent_values:
                for p in mtk.get_recent_projects(slice(0, 10), format="standard"):
                    if os.path.isfile(os.path.join(p, "workspace.mel")):
                        self._recent_workspaces.add_recent_value(p)

            self._recent_workspaces.value_selected.connect(self._open_recent_workspace)

    def tb000(self, widget):
        """Set Workspace"""
        mel.eval("SetProject")
        # Record the newly set workspace
        workspace = mtk.get_env_info("workspace")
        if hasattr(self, "_recent_workspaces") and workspace:
            self._recent_workspaces.record(workspace)
        if self._footer_controller:
            self._footer_controller.update()

    def _open_recent_workspace(self, path):
        """Open a workspace from the recent list."""
        if not os.path.isfile(os.path.join(str(path), "workspace.mel")):
            self.sb.message_box("Not a valid workspace.")
            return
        cmds.workspace(path, openWorkspace=True)
        workspace_name = os.path.basename(path)
        self.sb.message_box(f"Workspace set to {workspace_name}.")
        if self._footer_controller:
            self._footer_controller.update()

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

    def lbl004(self):
        """Open current project root"""
        dir_ = cmds.workspace(q=True, rd=1)  # current project path.
        os.startfile(ptk.format_path(dir_))

    def lbl005(self):
        """Auto Set Workspace"""
        workspace = mtk.find_workspace_using_path()
        if workspace:
            cmds.workspace(workspace, openWorkspace=True)
            workspace_name = os.path.basename(workspace)
            self.sb.message_box(f"Workspace set to {workspace_name}.")
            if self._footer_controller:
                self._footer_controller.update()
        else:
            self.sb.message_box("No workspace found.")

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
                    "• Prompt for Directory — pick a directory each time"
                ),
            )
            for text, data in [
                ("Alongside Scene File", "scene_dir"),
                ("Prompt for Directory", "prompt"),
            ]:
                cmb_save.addItem(text, data)

            widget.option_box.menu.add(
                "QCheckBox",
                setText="Include Cameras",
                setObjectName="chk_cameras",
                setChecked=False,
                setToolTip="Include camera nodes in the FBX export.",
            )
            widget.option_box.menu.add(
                "QCheckBox",
                setText="Include Lights",
                setObjectName="chk_lights",
                setChecked=False,
                setToolTip="Include light nodes in the FBX export.",
            )
            widget.option_box.menu.add(
                "QCheckBox",
                setText="Include Skins",
                setObjectName="chk_skins",
                setChecked=False,
                setToolTip="Include skin clusters / skinning data in the FBX export.",
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
        include_cameras = menu.chk_cameras.isChecked()
        include_lights = menu.chk_lights.isChecked()
        include_skins = menu.chk_skins.isChecked()
        also_glb = menu.chk_glb.isChecked()

        selection_only = scope == "selected"
        if selection_only and not cmds.ls(selection=True):
            self.sb.message_box("No objects selected.")
            return

        scene_path = cmds.file(query=True, sceneName=True) or ""

        if save_mode == "prompt":
            fd_kwargs = dict(
                fileMode=3,
                caption="Select Export Directory",
                okCaption="Export",
                dialogStyle=2,
            )
            if scene_path:
                fd_kwargs["startingDirectory"] = os.path.dirname(scene_path)
            picked = cmds.fileDialog2(**fd_kwargs)
            if not picked:
                return
            out_dir = picked[0]
            base = (
                os.path.splitext(os.path.basename(scene_path))[0]
                if scene_path
                else "untitled"
            )
            fbx_path = os.path.join(out_dir, base + ".fbx")
        else:
            if not scene_path:
                self.sb.message_box(
                    "Scene has not been saved yet.<br>"
                    "Save the scene first, or choose <hl>Prompt for Directory</hl>."
                )
                return
            fbx_path = os.path.splitext(scene_path)[0] + ".fbx"

        try:
            mtk.export_scene_as_fbx(
                file_path=fbx_path,
                selection_only=selection_only,
                FBXExportCameras=include_cameras,
                FBXExportLights=include_lights,
                FBXExportSkins=include_skins,
            )
        except Exception as e:
            self.sb.message_box(f"FBX export failed:<br>{e}")
            return

        if also_glb:
            try:
                glb_path = ptk.MeshConvert.fbx_to_glb(
                    fbx_path,
                    overwrite=True,
                    auto_install=True,
                    prompt=False,
                )
            except Exception as e:
                self.sb.message_box(
                    f"FBX exported, but GLB conversion failed:<br>{e}"
                )
                return
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

    def b010(self):
        """Scene Audit"""
        mtk.SceneAnalyzer.run_audit(adaptive=True)

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
        """Import file"""
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
