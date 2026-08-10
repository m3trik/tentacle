# !/usr/bin/python
# coding=utf-8
import os
import html
import shutil

import maya.cmds as cmds
import maya.mel as mel
import pythontk as ptk
import mayatk as mtk
from tentacle import SceneMixin, SlotsMaya


class SceneSlots(SceneMixin, SlotsMaya):
    #: Maya fires a real workspace event; the shared mixin does the wiring.
    FOOTER_EVENTS = ("workspaceChanged",)

    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.scene
        self.submenu = self.sb.loaded_ui.scene_submenu
        self._footer_controller = self._create_footer_controller()

    TOOLS_ROOT_TOOLTIP = "Scene bridges, management, recovery, fixes and diagnostics."

    def _tools_items(self):
        return {
            "Bridges": [
                (
                    "Mesh Converter",
                    "b013",
                    "Open the FBX -> GLB converter window.\nBacked by godotengine/FBX2glTF; the binary is downloaded on first use.",
                ),
                (
                    "Blender Bridge",
                    "b010",
                    "Send the selected objects to a fresh Blender (export FBX + run a chosen import template).",
                ),
                (
                    "Unity Bridge",
                    "b016",
                    "Send the selected objects to a Unity project (export FBX + copy into Assets/).",
                ),
            ],
            "Manage": [
                ("Reference Manager", "b001", "Open the reference manager."),
                ("Hierarchy Sync", "b004", "Open the hierarchy sync."),
                ("Naming", "b005", "Open the naming tool."),
            ],
            "Recover": [
                (
                    "Save to Original Scene",
                    "b014",
                    "Save the currently open autosave back to the original scene file.\nEnabled only when an autosave is open and the original is locatable.",
                ),
            ],
            "Fix": [
                (
                    "Cleanup Unknown",
                    "b006",
                    "Fix common scene issues:\n• Remove unknown/legacy nodes/plugins/expressions",
                ),
                (
                    "Fix OCIO",
                    "b009",
                    "Fix Maya Color Management / OCIO config preferences.",
                ),
                (
                    "Fix Color Spaces",
                    "b011",
                    "Fix missing color space errors on file texture nodes.\nAuto-detects sRGB vs Raw based on texture type.",
                ),
                (
                    "Fix Mangled Names",
                    "b018",
                    "Repair scratch/mangled node names — accumulated "
                    "'__uninst_tmp' tokens, '__RZTMP' Rizom suffixes, "
                    "'FBXASC###' import escapes, underscore runs — on "
                    "transforms AND shapes, then conform shapes to "
                    "'<transform>Shape'.\nScope: selection, or the whole "
                    "scene when nothing is selected.\nSame repair the Scene "
                    "Exporter's 'Fix Mangled Names' task runs.",
                ),
                (
                    "Fix Non-Orthogonal Axes",
                    "tb002",
                    self.sb.tooltip.fmt(
                        title="Fix Non-Orthogonal Axes",
                        body="Fix the objects behind FBX's <i>Non-orthogonal matrix "
                        "support</i> warning — axes that aren't perpendicular don't "
                        "survive import / export.",
                        bullets=[
                            "Shear on the object itself.",
                            "Shear inherited from a non-uniformly scaled, rotated "
                            "parent — which reads as zero shear on the object.",
                        ],
                        notes=[
                            "Scope and a report-only dry run are set in the option box.",
                        ],
                    ),
                ),
            ],
            "Diagnostics": [
                (
                    "Get Scene Info",
                    "tb001",
                    "Show a formatted scene analysis report in the viewer "
                    "(poly count, draw calls, textures, fix-first items). "
                    "Profile (Adaptive / Generic) is set via the option box.",
                ),
                (
                    "Scene Metadata",
                    "b017",
                    "Show the tool-authored metadata stored on the scene's "
                    "data nodes (data_internal + data_export) as JSON — shot "
                    "metadata, audio manifests, bake sessions, etc.\n"
                    "Use Save in the viewer to write it to a .json file.",
                ),
                (
                    "Toggle Command Ports",
                    "b012",
                    "Toggle Maya command ports on/off (MEL :7001, Python :7002).\nUsed for external editor connections.",
                ),
            ],
        }

    @SlotsMaya.Signals("on_item_interacted")
    def list003(self, item):
        """Dispatch a Tools leaf to its own slot (shared: ``SceneMixin``)."""
        self._dispatch_tools_item(item)

    # ------------------------------------------------------- SceneMixin hooks
    NON_ORTHOGONAL_FIX_EFFECT = (
        "Fixing freezes each object's rotate/scale, baking the shear into its "
        "shape — the object stays where it is and looks identical. Translate "
        "channels and their connections (constraints, animation) are never "
        "touched."
    )

    def _diagnostics(self):
        return mtk.Diagnostics

    def _scene_objects(self):
        return cmds.ls(transforms=True, long=True) or []

    def _selected_objects(self):
        # objectsOnly resolves component selections (faces/verts/edges) to
        # their shapes; list_transforms walks shapes up to the owning
        # transforms — so a component selection checks the object it's on
        # instead of silently checking nothing.
        return mtk.NodeUtils.list_transforms(
            cmds.ls(selection=True, objectsOnly=True, long=True) or []
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

    # (label -> callable(slot)) for the submenu's Import / Export expandable
    # lists. Callables take the slots instance so they can reach the FBX
    # plugin / preset-window helpers and the marking-menu handler.
    _IMPORTERS = {
        "Import File": lambda slot: mel.eval("Import"),
        "Import Options": lambda slot: mel.eval("ImportOptions"),
        "Import Blender Scene": lambda slot: slot._import_blender_scene(),
        "FBX Import Presets": lambda slot: slot._eval_fbx_uicallback(
            'editImportPresetInNewWindow" "fbx'
        ),
        "OBJ Import Presets": lambda slot: slot._eval_fbx_uicallback(
            'editImportPresetInNewWindow" "obj'
        ),
    }
    # The Export list's tool-panel entry — a launcher rather than a one-shot
    # export, so list002_init adds it separately (last, nearest the trigger row)
    # with a tooltip. Named so the dict key and that filter can't drift apart.
    _SCENE_EXPORTER = "Scene Exporter"

    _EXPORTERS = {
        _SCENE_EXPORTER: lambda slot: slot.sb.handlers.marking_menu.show(
            "scene_exporter"
        ),
        "Export Selection": lambda slot: slot._export_selection(),
        # The push mirror of Import's "Import Blender Scene" — same bridge, opposite
        # direction, so the two live symmetrically in the two lists.
        "Export .blend": lambda slot: slot._export_foreign_scene(),
        "Export All": lambda slot: mel.eval("Export"),
        "Send to Unreal": lambda slot: mel.eval("SendToUnrealSelection"),
        "Send to Unity": lambda slot: mel.eval("SendToUnitySelection"),
        "GoZ": lambda slot: mel.eval(
            'print("GoZ"); source"C:/Users/Public/Pixologic/GoZApps/Maya/GoZBrushFromMaya.mel"; source "C:/Users/Public/Pixologic/GoZApps/Maya/GoZScript.mel";'
        ),
        "Send to 3dsMax: As New Scene": lambda slot: mel.eval("SendAsNewScene3dsMax"),
        "Send to 3dsMax: Update Current": lambda slot: mel.eval(
            "UpdateCurrentScene3dsMax"
        ),
        "Send to 3dsMax: Add to Current": lambda slot: mel.eval(
            "AddToCurrentScene3dsMax"
        ),
        "Export to Offline File": lambda slot: mel.eval("ExportOfflineFileOptions"),
        "Export Options": lambda slot: mel.eval("ExportSelectionOptions"),
        "FBX Export Presets": lambda slot: slot._eval_fbx_uicallback(
            'editExportPresetInNewWindow" "fbx'
        ),
        "OBJ Export Presets": lambda slot: slot._eval_fbx_uicallback(
            'editExportPresetInNewWindow" "obj'
        ),
    }

    def _export_selection(self):
        """Export Selection — ensure fbxmaya is loaded so FBX shows in the type list."""
        self._ensure_fbx_plugin()
        mel.eval("ExportSelection")

    def list001_init(self, widget):
        """Initialize Import"""
        widget.fixed_item_height = 18
        # Lowest list in the submenu: open downward, covering the root row
        # (expand_down would hang the sublist below it instead). The panel's
        # header-menu row fans right on hover instead.
        widget.apply_preset(
            "expand_overlay" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        root = widget.add(
            "Import",
            setToolTip="Import a file or a Blender scene, or open Import / FBX / OBJ preset options.",
        )
        root.sublist.add(list(self._IMPORTERS))

    @SlotsMaya.Signals("on_item_interacted")
    def list001(self, item):
        """Import: import a file, or open import / FBX / OBJ preset options."""
        action = self._IMPORTERS.get(item.item_text())
        if action:
            action(self)

    def _import_blender_scene(self):
        """Import a Blender scene (.blend) via ``mtk.BlenderSceneImport`` — a
        headless-Blender FBX round-trip by default (a fresh ``blender --background``
        converts the scene; instancing is carried by the format, materials rebuilt
        from a texture manifest; the USD route — native materials / animation,
        instancing replayed from a sidecar — is opt-in via the Reference Manager's
        route option or ``via="usd"``). Mirror of the Blender slots' "Import Maya Scene".
        Blocking: a scene conversion takes seconds (no license checkout — Blender is
        free), so a wait cursor covers the run. Requires a local Blender install."""
        src = self.sb.file_dialog(
            file_types=["*.blend"],
            title="Import Blender Scene",
            filter_description="Blender Scenes",
            allow_multiple=False,
        )
        if not src:
            return
        app = self.sb.QtWidgets.QApplication
        app.setOverrideCursor(self.sb.QtCore.Qt.WaitCursor)
        try:
            imported = mtk.BlenderSceneImport().import_scene(src)
        except Exception as e:
            self.sb.message_box(f"Blender scene import failed: <hl>{e}</hl>")
            return
        finally:
            app.restoreOverrideCursor()
        self.sb.message_box(
            f"Imported <hl>{len(imported)}</hl> object(s) from "
            f"<hl>{os.path.basename(src)}</hl>."
        )

    #: Export Scene's combo label for Blender's native format (SceneMixin hook).
    FOREIGN_FORMAT_LABEL = "Blend"

    def _current_scene_path(self) -> str:
        """The open scene, or "" when it has never been saved (SceneMixin hook).

        Through the engine, not ``cmds.file(sceneName=True)``: batch reports an
        unsaved scene as a phantom extensionless ``<project>/untitled``, which would
        pass the mixin's "has this been saved?" check and silently write the export
        into the default project instead of asking the user to save.
        """
        return mtk.saved_scene_path()

    def _foreign_scene_bridge(self):
        """The bridge that writes Blender's native format (SceneMixin hook).

        Materials ride the same ``.manifest.json`` sidecar the interactive Send to
        Blender uses, so ``Save As Blender Scene`` is not a second export path. No
        license checkout on that side, so the run is seconds rather than the tens the
        Blender fork's Maya-bound twin costs.
        """
        return mtk.BlenderBridge()

    def list002_init(self, widget):
        """Initialize Export.

        Population order keeps the two tools nearest the trigger row in both
        hosts. The submenu expands upward, so it is populated in reverse: the
        LAST item added sits nearest the trigger — Scene Exporter, then Export
        Scene (the tb003 PushButton folded in from the old submenu button,
        option-box gear and all) closest to the cursor, with the one-shot
        actions that used to live on the Export combobox stacking above them.
        The panel's hover_menu flyout fans right with its top row aligned to
        the trigger, so the same rows are added in the opposite order: tools
        first (top, nearest the trigger), one-shots below in natural order.
        """
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up" if submenu else "hover_menu")
        root = widget.add(
            "Export",
            setToolTip="Export the scene or selection (FBX, Send To, presets).",
        )
        one_shots = [k for k in self._EXPORTERS if k != self._SCENE_EXPORTER]
        exporter_tip = "Export scene assets with environment checks and presets."
        # Registration of tb003 runs tb003_init (building the option-box menu),
        # wires clicked -> tb003, and binds ui.tb003 so the panel fork's entry
        # can read the submenu's shared options.
        tb003_kwargs = dict(
            setObjectName="tb003",
            setText="Export Scene",
            setToolTip=(
                "Export the scene to FBX (and optionally GLB).\n"
                "Click the gear icon to configure scope, included types, and save location."
            ),
        )
        if submenu:
            root.sublist.add(one_shots[::-1])
            root.sublist.add(self._SCENE_EXPORTER, setToolTip=exporter_tip)
            self.add_slot_widget(root.sublist, **tb003_kwargs)
        else:
            self.add_slot_widget(root.sublist, **tb003_kwargs)
            root.sublist.add(self._SCENE_EXPORTER, setToolTip=exporter_tip)
            root.sublist.add(one_shots)

    @SlotsMaya.Signals("on_item_interacted")
    def list002(self, item):
        """Export: the one-shot export actions and the Scene Exporter launcher.

        tb003 never arrives here — its option-box wrap swapped it out of the
        list's item set, so the list no longer consumes its releases and its
        own clicked signal drives the slot (see ``Slots.add_slot_widget``).
        """
        action = self._EXPORTERS.get(item.item_text())
        if action:
            action(self)

    def list000_init(self, widget):
        """Initialize Recent Files"""
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_up" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        recent_files = mtk.get_recent_files(slice(0, 11))
        w1 = widget.add("Recent Files")
        truncated = ptk.truncate(recent_files, 65)
        w1.sublist.add(zip(truncated, recent_files))
        widget.setVisible(bool(recent_files))

    @SlotsMaya.Signals("on_item_interacted")
    def list000(self, item):
        """Recent Files"""
        data = item.item_data()
        if not data:  # the "Recent Files" category row carries no file
            return
        cmds.file(data, open=True, force=True)

    def _script_job_manager(self):
        return mtk.ScriptJobManager

    def _resolve_workspace_text(self) -> str:
        return mtk.get_env_info("workspace_dir") or ""

    def b001(self):
        """Open Reference Manager"""
        self.sb.handlers.marking_menu.show("reference_manager")

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
            cmb_format = widget.option_box.menu.add(
                "QComboBox",
                setObjectName="cmb_format",
                setToolTip=(
                    "Output format:\n"
                    "• FBX — the interchange default\n"
                    "• OBJ — geometry only (no hierarchy, skinning or animation)\n"
                    "• GLB — written via FBX2glTF; the intermediate FBX goes to a\n"
                    "  temp dir and is discarded, so only the .glb is delivered\n"
                    "• Blend — a real Blender scene, via a fresh headless Blender\n"
                    "  (slower; a local Blender install is required)"
                ),
            )
            for text, data in self._export_format_items():
                cmb_format.addItem(text, data)

            # Cameras and lights are scene-level categories: in Selected Only
            # mode they'd only export if explicitly selected, so the
            # "include all" intent doesn't apply — disable them. Skins are
            # intrinsic to the selected mesh, so they stay enabled in both
            # scopes. The button label mirrors the scope so the submenu entry
            # reads as what it will do (QSettings restore re-fires the signal,
            # so a persisted scope re-labels on init too).
            def _sync_scope(_idx=None):
                whole_scene = cmb_scope.currentData() == "all"
                chk_cameras.setEnabled(whole_scene)
                chk_lights.setEnabled(whole_scene)
                widget.setText("Export Scene" if whole_scene else "Export Sel")

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

    def _export_scene_native(self, export_format, out_path, options, tick):
        """Write FBX / OBJ / GLB (SceneMixin hook).

        Maya has no GLB writer, so a GLB is an FBX plus an FBX2glTF conversion. The
        intermediate goes to a TEMP dir rather than next to the deliverable: writing
        it beside the target would overwrite whatever .fbx the user already had
        there, and a "delete it afterwards" cleanup cannot run when the process dies
        mid-convert (only TempArtifacts' age-gated sweep reclaims it then). Same rule
        ``SceneExporter`` follows for its own ``output_format="glb"``. The converter
        does take a ``dst``, but writing straight to the target would leave a partial
        .glb there if it failed — the deliverable is only touched on success.
        """
        if export_format == "obj":
            mtk.export_scene_as_obj(
                file_path=out_path,
                selection_only=options["selection_only"],
                materials=options["embed_textures"],
            )
            return

        write_path, tempdir = out_path, None
        if export_format == "glb":
            tempdir = ptk.TempArtifacts("scene_export_glb").dir_path()
            write_path = os.path.join(
                tempdir, os.path.splitext(os.path.basename(out_path))[0] + ".fbx"
            )

        mtk.export_scene_as_fbx(
            file_path=write_path,
            selection_only=options["selection_only"],
            FBXExportCameras=options["include_cameras"],
            FBXExportLights=options["include_lights"],
            FBXExportSkins=options["include_skins"],
            FBXExportTangents=options["include_tangents"],
            FBXExportEmbeddedTextures=options["embed_textures"],
        )
        if export_format != "glb":
            return

        # The scene sidecar repairs what the FBX hop mistranslates (modern-
        # shader base colour / emissive) and rides embedded in the GLB. The
        # Blender fork deliberately has no counterpart: it writes GLB through
        # Blender's native glTF exporter — no FBX hop, nothing to repair.
        sidecar = None
        try:
            objects = (
                cmds.ls(selection=True, long=True)
                if options["selection_only"]
                else cmds.ls(assemblies=True, long=True)
            )
            sidecar = ptk.MeshConvert.build_scene_sidecar(
                mtk.SceneState.read(
                    objects, include_textures=options["embed_textures"]
                ),
                source=mtk.SceneState.source(),
                asset=os.path.basename(write_path),
            )
        except Exception:  # a bare GLB still beats no GLB
            self.sb.logger.warning("Scene sidecar skipped.", exc_info=True)

        tick(text="Converting to GLB…")
        glb_path = ptk.MeshConvert.fbx_to_glb(
            write_path, overwrite=True, auto_install=True, prompt=False, sidecar=sidecar
        )
        if not (glb_path and os.path.isfile(glb_path)):
            raise RuntimeError("FBX to GLB conversion produced no file.")
        shutil.move(glb_path, out_path)

    def b004(self):
        """Open Hierarchy Sync"""
        self.sb.handlers.marking_menu.show("hierarchy_sync")

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
        # Named report_html (not ``html``) so the module-level ``import html`` used by
        # b017's ``html.escape`` stays reachable — a bare ``html`` local would shadow it.
        report_html = "".join(html_dict.values()) if html_dict else ""
        if not report_html:
            self.sb.message_box(
                "<hl>No scene info</hl> available — analyze returned no records."
            )
            return

        self.sb.text_view_dialog(
            report_html,
            "Ok",
            title="Get Scene Info",
            size=(820, 560),
            monospace=False,
        )

    def b011(self):
        """Fix Color Spaces"""
        mtk.Diagnostics.fix_missing_color_spaces(force_update=True)

    def b018(self):
        """Fix Mangled Names"""
        result = mtk.Diagnostics.repair_mangled_names(
            objects=cmds.ls(sl=True, long=True) or None
        )
        renamed = len(result["renamed"])
        conformed = result["shapes_conformed"]
        if renamed or conformed:
            self.sb.message_box(
                f"Repaired <hl>{renamed}</hl> mangled name(s), "
                f"conformed <hl>{conformed}</hl> shape(s).",
                timeout=4,
            )
        else:
            self.sb.message_box("No mangled names found.", timeout=2)

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

    def b017(self):
        """Scene Metadata — dump the tool-authored data-node channels to the viewer.

        Renders ``mtk.DataNodes.dump`` (every channel on ``data_internal`` +
        ``data_export``, JSON-decoded) as pretty JSON. The viewer's Save button
        writes the same report to a ``.json`` file.
        """
        report = mtk.DataNodes.format_dump()
        if not report:
            self.sb.message_box(
                "<hl>No scene metadata</hl> is stored — this scene has no "
                "<b>data_internal</b> / <b>data_export</b> channels yet."
            )
            return

        dlg = self.sb.text_view_dialog(
            f"<pre>{html.escape(report)}</pre>",
            "Save",
            "Ok",
            title="Scene Metadata",
            size=(720, 560),
            monospace=True,
            word_wrap=False,
        )
        # "Save" is an Accept-role button (it closes the viewer); wire the export
        # via the sanctioned realtime hook so the same click writes the file.
        dlg.button_box.clicked.connect(
            lambda btn, text=report: self._export_scene_metadata(btn, text)
        )

    def _export_scene_metadata(self, button, text):
        """Write the Scene Metadata report to a chosen ``.json`` (viewer Save button)."""
        if button.text().replace("&", "") != "Save":
            return
        scene_path = cmds.file(query=True, sceneName=True) or ""
        base = (
            os.path.splitext(os.path.basename(scene_path))[0]
            if scene_path
            else "untitled"
        ) + "_scene_metadata.json"
        start_dir = (
            os.path.dirname(scene_path)
            if scene_path
            else (cmds.workspace(query=True, rootDirectory=True) or "")
        )
        picked = cmds.fileDialog2(
            fileMode=0,
            caption="Save Scene Metadata As",
            okCaption="Save",
            fileFilter="JSON (*.json)",
            dialogStyle=2,
            startingDirectory=os.path.join(start_dir, base),
        )
        if not picked:
            return
        path = picked[0]
        if not path.lower().endswith(".json"):
            path += ".json"
        ptk.FileUtils.atomic_write_text(path, text)
        self.sb.message_box(f"Saved scene metadata to <hl>{os.path.basename(path)}</hl>.")

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
            mgr = mtk.ScriptJobManager.instance()
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


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
