# !/usr/bin/python
# coding=utf-8
import os

import bpy
import pythontk as ptk
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class SceneSlots(SlotsBlender):
    """Blender port of the shared ``scene`` menu.

    Recent files / autosave recovery map onto Blender's own recent-files.txt and temp-dir
    autosaves (``btk.get_recent_files`` / ``btk.get_recent_autosave``); import/export route
    through Blender's native format operators (file dialogs via ``INVOKE_DEFAULT``).
    Reference Manager opens the library-link panel (``blender_menus/reference_manager``).
    Maya's workspace model, the remaining mayatk manager windows (hierarchy/exporter) and
    command ports have no Blender analogue and are deferred.
    """

    # (label -> bpy.ops path) for the import/export combos; resolved at call time so a
    # missing importer add-on degrades to a message instead of an AttributeError.
    _IMPORTERS = {
        "Import FBX": "import_scene.fbx",
        "Import OBJ": "wm.obj_import",
        "Import Collada": "wm.collada_import",
        "Append from .blend": "wm.append",
        "Link from .blend": "wm.link",
    }
    _EXPORTERS = {
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
        Spaces) is a genuine Blender build (data maps → 'Non-Color' by map type). Maya-only entries
        (Save to Original Scene, Fix OCIO, Toggle Command Ports, the Mesh Converter batch tool) are
        omitted — see the parity overrides. Reused objectNames carry the Maya label verbatim
        (cross-DCC QSettings rule); ``b_cleanup`` is Blender-specific (Maya's b006 means the
        unrelated 'Cleanup Unknown')."""
        widget.menu.add("Separator", setTitle="Export")
        widget.menu.add(
            "QPushButton", setText="Scene Exporter", setObjectName="b002",
            setToolTip="Open Blender's native FBX export dialog (carries its own presets).",
        )
        widget.menu.add(
            self.sb.registered_widgets.PushButton, setText="Export Scene", setObjectName="tb003",
            setToolTip="Export the whole scene to FBX.",
        )
        widget.menu.add(
            "QPushButton", setText="Export Selection", setObjectName="b008",
            setToolTip="Export only the selected objects (FBX).",
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
            setToolTip="Open the Outliner in its own window.",
        )
        widget.menu.add(
            "QPushButton", setText="Naming", setObjectName="b005",
            setToolTip="Blender's native Batch Rename.",
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

    # ------------------------------------------------------------------ cmb003/cmb004  Import/Export
    def cmb003_init(self, widget):
        widget.add(list(self._IMPORTERS), header="Import")

    def cmb003(self, index, widget):
        """Import"""
        op_path = self._IMPORTERS.get(widget.items[index])
        if op_path:
            self.invoke_op(op_path)

    def cmb004_init(self, widget):
        widget.add(list(self._EXPORTERS), header="Export")

    def cmb004(self, index, widget):
        """Export"""
        op_path = self._EXPORTERS.get(widget.items[index])
        if op_path:
            self.invoke_op(op_path)

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
        def _sync_scope(_idx=None):
            whole_scene = cmb_scope.currentData() == "all"
            chk_cameras.setEnabled(whole_scene)
            chk_lights.setEnabled(whole_scene)

        cmb_scope.currentIndexChanged.connect(_sync_scope)
        _sync_scope()

    def tb003(self, widget):
        """Export Scene — FBX (+ optional GLB) using the configured options.

        Options always live on the submenu's tb003 (the PushButton carrying the option-box gear);
        the header entry is a plain button reaching the same slot, so read options off the submenu."""
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
        """Unity Bridge — send the selection to a Unity project's Assets/ (btk.UnityBridge)."""
        self.sb.handlers.marking_menu.show("unity_bridge")

    def b005(self):
        """Naming — open the panel (Find / Rename / Convert Case / Strip Chars / Suffix by
        Location / Suffix by Type, each with an option box), served from blendertk by the
        BlenderUiHandler, mirroring Maya's Naming window (replaces the native Batch Rename op)."""
        self.sb.handlers.marking_menu.show("naming")

    def b007(self):
        """Import file"""
        self.ui.cmb003.call_slot(0)

    def b008(self):
        """Export Selection (FBX, selected objects only)."""
        if not self.selected_objects():
            self.sb.message_box("Export Selection requires a selection.")
            return
        self.invoke_op("export_scene.fbx", use_selection=True)

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
        html = "".join(report.get(key, "") for key, _l, _d, _t in self._TB001_SECTIONS)
        if not html:
            self.sb.message_box("<hl>No scene info</hl> available.")
            return
        self.sb.text_view_dialog(
            html, "Ok", title="Get Scene Info", size=(640, 600), monospace=False
        )

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def b002(self):
        """Scene Exporter — the mayatk batch/preset exporter window isn't ported; open Blender's
        native FBX export dialog (which carries its own operator presets via the +/− buttons) as
        the don't-reinvent stand-in."""
        self.invoke_op("export_scene.fbx")

    def b004(self):
        """Hierarchy Manager (Blender's native Outliner in a new window — the
        don't-reinvent answer; the mayatk diff/pull workflow is Maya-specific)."""
        try:
            btk.open_editor("Outliner")
        except Exception as e:
            self.sb.message_box(str(e))


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
