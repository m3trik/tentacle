# !/usr/bin/python
# coding=utf-8
import os
import html

import bpy
import pythontk as ptk
import blendertk as btk
from tentacle import SceneMixin, SlotsBlender


class SceneSlots(SceneMixin, SlotsBlender):
    """Blender port of the shared ``scene`` menu.

    Recent files / autosave recovery map onto Blender's own recent-files.txt and temp-dir
    autosaves (``btk.get_recent_files`` / ``btk.get_recent_autosave``); the submenu's
    Import / Export expandable lists route through Blender's native format operators
    (file dialogs via ``INVOKE_DEFAULT``).
    Reference Manager opens the library-link panel (``blender_menus/reference_manager``).
    Scene Exporter and Hierarchy Sync are native blendertk panels, both 1:1 with mayatk's:
    the former (task/check pipeline, FBX or GLB) reached from the Export list — see
    ``blendertk.env_utils.scene_exporter`` for which tasks/checks are ported vs. disabled
    placeholders (hierarchy_sync / smart_bake / data_export subsystems aren't ported yet);
    the latter for Diff/Fix (Pull isn't ported yet). The workspace model is shared with Maya
    (``workspace.mel`` projects via ``btk.current_workspace``; the footer mirrors Maya's
    workspace status). Maya's command ports have no Blender analogue and are deferred.
    """

    # (label -> bpy.ops path OR callable(slot)) for the submenu's Import / Export expandable
    # lists. Rows whose operator isn't registered in this Blender are dropped at list build
    # time (``resolve_op``) — Collada (wm.collada_import/export) was removed in Blender 5.0,
    # and a disabled add-on importer would otherwise sit as a permanently dead row. Op paths
    # are still resolved at call time too, so anything that disappears after the list built
    # degrades to a message instead of an AttributeError (invoke_op). Callables cover the
    # entries that aren't native operators — importers with no file browser to invoke, and
    # the Scene Exporter panel.
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
        # Was a header-menu button (b008) — a one-shot export, so it belongs
        # with its siblings here rather than in the Tools list.
        "Export Selection": lambda slot: slot.b008(),
        # The push mirror of Import's "Import Maya Scene" — same bridge, opposite
        # direction, so the two live symmetrically in the two lists.
        "Export .ma": lambda slot: slot._export_foreign_scene(),
        "Export FBX": "export_scene.fbx",
        "Export OBJ": "wm.obj_export",
        "Export glTF": "export_scene.gltf",
        "Export Collada": "wm.collada_export",
    }

    #: Blender has no ``workspaceChanged`` event, so the shared footer wiring
    #: refreshes on scene open/save (a session-pin change shows on the next file event).
    FOOTER_EVENTS = ("SceneOpened", "SceneSaved")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.scene
        self.submenu = self.sb.loaded_ui.scene_submenu
        self._footer_controller = self._create_footer_controller()

    def _script_job_manager(self):
        return btk.ScriptJobManager

    def _resolve_workspace_text(self) -> str:
        return btk.get_env_info("workspace_dir") or ""

    def _tools_items(self):
        """``category -> [(label, objectName, tooltip)]`` for the Tools list.

        Mirror of the Maya scene Tools list (portable subset). ``b011`` (Fix Color
        Spaces) is a genuine Blender build (data maps → 'Non-Color' by map type).
        ``b013`` (Mesh Converter) is the DCC-agnostic extapps/mesh_convert tool,
        launched via the shared external_app handler exactly like Maya. Maya-only
        entries (Save to Original Scene / the whole Recover category, Fix OCIO,
        Toggle Command Ports) are omitted — see the parity overrides. Reused
        objectNames carry the Maya label verbatim (cross-DCC QSettings rule);
        ``b_cleanup`` is Blender-specific (Maya's b006 means the unrelated
        'Cleanup Unknown'). ``b008`` Export Selection is not here: it is a
        one-shot export and now lives in the Export list with its siblings.

        A method rather than a class attribute because ``tb002``'s tooltip is
        built with the switchboard's formatter, which needs a live ``self.sb``.
        """
        return {
            "Bridges": [
                (
                    "Mesh Converter",
                    "b013",
                    "Open the FBX -> GLB converter window.\nBacked by godotengine/FBX2glTF; the binary is downloaded on first use.",
                ),
                (
                    "Maya Bridge",
                    "b010",
                    "Send the selected objects to a fresh Maya (export FBX + run a chosen import template).",
                ),
                (
                    "Unity Bridge",
                    "b016",
                    "Send the selected objects to a Unity project (export FBX + copy into Assets/).",
                ),
            ],
            "Manage": [
                ("Reference Manager", "b001", "Manage linked .blend libraries."),
                (
                    "Hierarchy Sync",
                    "b004",
                    "Diff/repair the scene hierarchy against a reference .blend.",
                ),
                ("Naming", "b005", "Blender's native Batch Rename."),
                (
                    "Audio Clips",
                    "b003",
                    "Manage scene-wide audio clips in the Video Sequence Editor "
                    "(add/remove/trim/sync).",
                ),
                (
                    "Blendshape Animator",
                    "b015",
                    "Build a morph between two meshes as a shape key, sculpt in-between "
                    "tweens to customize the curve, and apply them back.",
                ),
            ],
            "Fix": [
                (
                    "Scene Cleanup",
                    "b_cleanup",
                    "Purge orphan datablocks (meshes, materials, images … with no users).",
                ),
                (
                    "Fix Color Spaces",
                    "b011",
                    "Set data textures (normal / roughness / metallic / height …) to "
                    "'Non-Color' and color maps to 'sRGB', by map type — so PBR shading isn't gamma-wrong.",
                ),
                (
                    "Fix Non-Orthogonal Axes",
                    "tb002",
                    self.sb.tooltip.fmt(
                        title="Fix Non-Orthogonal Axes",
                        body="Fix the objects behind FBX's <i>Non-orthogonal matrix "
                        "support</i> warning — axes that aren't perpendicular don't "
                        "survive import / export.",
                        notes=[
                            "In Blender the skew is always inherited: an object under a "
                            "non-uniformly scaled, rotated parent evaluates to "
                            "non-perpendicular world axes.",
                            "Scope and a report-only dry run are set in the option box.",
                        ],
                    ),
                ),
            ],
            "Diagnostics": [
                (
                    "Get Scene Info",
                    "tb001",
                    "Show an object / poly / material summary in a viewer.\n"
                    "Use the option box to choose scope (Selected / Entire Scene).",
                ),
                (
                    "Scene Metadata",
                    "b017",
                    "Show the tool-authored metadata stored on the scene's data nodes "
                    "(data_internal + data_export) as JSON — shot metadata, audio manifests, etc.\n"
                    "Use Save in the viewer to write it to a .json file.",
                ),
            ],
        }

    def list003_init(self, widget):
        """Tools list: the scene actions that used to sit loose in the header
        menu (Bridges / Manage / Fix / Diagnostics), grouped into one expandable
        row in the panel body — mirror of the Maya fork.

        Every leaf is a real slot-wired widget carrying the objectName its
        header entry used, so its slot, tooltip, option box (``tb001`` /
        ``tb002``) and QSettings identity are unchanged — only the location
        moved.
        """
        widget.fixed_item_height = 18
        widget.apply_preset("header_menu")
        root = widget.add(
            "Tools",
            setToolTip="Scene bridges, management, fixes and diagnostics.",
        )
        for category, entries in self._tools_items().items():
            cat = root.sublist.add(category)
            for label, name, tooltip in entries:
                self.add_slot_widget(
                    cat.sublist,
                    setObjectName=name,
                    setText=label,
                    setToolTip=tooltip,
                )

    @SlotsBlender.Signals("on_item_interacted")
    def list003(self, item):
        """Dispatch a Tools leaf to its own slot.

        Category rows are navigation only. Leaves are slot-wired widgets, so
        ``call_slot`` routes through the switchboard's wrapper — which injects
        the ``widget`` argument for the slots that declare it, so both
        signatures work without a lookup table here. An option-box-wrapped
        leaf never arrives: the wrap leaves it out of the list's item set and
        its own ``clicked`` drives it (see ``Slots.add_slot_widget``).
        """
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        call = getattr(item, "call_slot", None)
        if callable(call):
            call()

    # ------------------------------------------------------- SceneMixin hooks
    NON_ORTHOGONAL_FIX_EFFECT = (
        "Fixing bakes the sheared world transform back into an orthogonal "
        "Loc/Rot/Scale via 'clear parent &amp; keep transform' — the object "
        "stays exactly where it is, but is un-parented in the process (a "
        "Blender object has no shear of its own to freeze). Objects without "
        "drivers, animation or constraints are untouched beyond that."
    )

    def _diagnostics(self):
        return btk.Diagnostics

    def _scene_objects(self):
        return list(bpy.context.scene.objects)

    def _selected_objects(self):
        return list(self.selected_objects())

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
        widget.apply_preset(
            "expand_up" if widget.ui.has_tags("submenu") else "header_menu"
        )
        recent_files = btk.get_recent_files(slice(0, 11))
        w1 = widget.add("Recent Files")
        truncated = ptk.truncate(recent_files, 65)
        w1.sublist.add(zip(truncated, recent_files))
        widget.setVisible(bool(recent_files))

    @SlotsBlender.Signals("on_item_interacted")
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
        # (expand_down would hang the sublist below it instead). The panel's
        # header-menu row fans right on hover instead.
        widget.apply_preset(
            "expand_overlay" if widget.ui.has_tags("submenu") else "header_menu"
        )
        root = widget.add(
            "Import",
            setToolTip="Import a file (FBX / OBJ / Maya scene …), or append/link from a .blend.",
        )
        root.sublist.add(
            [k for k, v in self._IMPORTERS.items() if callable(v) or self.resolve_op(v)]
        )

    @SlotsBlender.Signals("on_item_interacted")
    def list001(self, item):
        """Import"""
        entry = self._IMPORTERS.get(item.item_text())
        if callable(entry):
            entry(self)
        elif entry:
            self.invoke_op(entry)

    def _import_maya_scene(self):
        """Import a Maya scene (.ma/.mb) via ``btk.MayaSceneImport`` — a headless-Maya
        FBX round-trip by default (fresh mayapy converts the scene; instancing is
        carried by the format, materials rebuilt from a texture manifest; the USD
        route — native materials / animation / visibility, instancing replayed from
        a sidecar — is opt-in via the Reference Manager's route option or
        ``via="usd"``). Blocking: a scene conversion
        takes tens of seconds (mayapy startup + license checkout), so a wait cursor
        covers the run. Requires a local Maya install."""
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
            imported = btk.MayaSceneImport().import_scene(src)
        except Exception as e:
            self.sb.message_box(f"Maya scene import failed: <hl>{e}</hl>")
            return
        finally:
            app.restoreOverrideCursor()
        self.sb.message_box(
            f"Imported <hl>{len(imported)}</hl> object(s) from "
            f"<hl>{os.path.basename(src)}</hl>."
        )

    #: Export Scene's combo label for Maya's native format (SceneMixin hook).
    FOREIGN_FORMAT_LABEL = "MA"

    def _current_scene_path(self) -> str:
        """The open .blend, or "" when it has never been saved (SceneMixin hook)."""
        return bpy.data.filepath or ""

    def _foreign_scene_bridge(self):
        """The bridge that writes Maya's native format (SceneMixin hook).

        Materials ride the same ``.manifest.json`` sidecar the interactive Send to
        Maya uses, so ``Save As Maya Scene`` is not a second export path.
        """
        return btk.MayaBridge()

    def list002_init(self, widget):
        """Initialize Export.

        Population order keeps the two tools nearest the trigger row in both
        hosts. The submenu expands upward, so it is populated in reverse: the
        LAST item added sits nearest the trigger — Scene Exporter, then Export
        Scene (the tb003 PushButton folded in from the old submenu button,
        option-box gear and all) closest to the cursor, with the native
        one-shot format exporters that used to live on the Export combobox
        stacking above them. The panel's header_menu flyout fans right with
        its top row aligned to the trigger, so the same rows are added in the
        opposite order: tools first (top, nearest the trigger), one-shots
        below in natural order.
        """
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up" if submenu else "header_menu")
        root = widget.add(
            "Export",
            setToolTip="Export the scene or selection (FBX / OBJ / glTF …).",
        )
        one_shots = [
            k for k, v in self._EXPORTERS.items()
            if k != self._SCENE_EXPORTER and (callable(v) or self.resolve_op(v))
        ]
        exporter_tip = "Batch-export via a configurable task/check pipeline (FBX/GLB)."
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

    @SlotsBlender.Signals("on_item_interacted")
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
        cmb_format = widget.option_box.menu.add(
            "QComboBox", setObjectName="cmb_format",
            setToolTip=(
                "Output format:\n"
                "• FBX — the interchange default\n"
                "• OBJ — geometry only (no hierarchy, skinning or animation)\n"
                "• GLB — Blender's native glTF 2.0 exporter (no FBX hop; the\n"
                "  don't-reinvent answer to Maya's FBX2glTF conversion)\n"
                "• MA — a real Maya scene, via a fresh headless mayapy\n"
                "  (slower; a local Maya install is required)"
            ),
        )
        for text, data in self._export_format_items():
            cmb_format.addItem(text, data)

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

    # Triangle count at/above which an export with a mesh-cost-scaling option (tangents)
    # is slow enough on dense geometry — photogrammetry scans, sculpts — to be worth a
    # heads-up before the blocking write. Mirrors Maya's tb003 guard. Tunable.
    _DENSE_TRI_THRESHOLD = 5_000_000

    def _confirm_dense_export(self, selection_only, include_tangents):
        """Warn before a dense + taxing FBX export; return False if cancelled.

        Minimal port of the Maya twin: returns True (proceed) for the common, non-taxing
        case so the normal path is untouched — the dialog only appears when the export set
        is dense AND tangents are on, the combination that turns a quick export into a
        multi-minute one. Triangles are summed from the base meshes (per mesh:
        loops − 2·polygons — exact for the pre-modifier data, O(1) per mesh), filling
        polyEvaluate's role without evaluating modifiers. ``message_box`` returns the
        clicked button text (or None if dismissed), so anything but "Yes" cancels."""
        if not include_tangents:
            return True
        pool = (
            self.selected_objects()
            if selection_only
            else bpy.context.view_layer.objects
        )
        meshes = [o for o in pool if o.type == "MESH"]
        if not meshes:
            return True
        tris = sum(len(o.data.loops) - 2 * len(o.data.polygons) for o in meshes)
        if tris < self._DENSE_TRI_THRESHOLD:
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

        Unlike Maya, Blender writes GLB natively — no FBX hop and no conversion, so
        *tick* is unused here.
        """
        if export_format == "obj":
            btk.export_scene_as_obj(
                file_path=out_path,
                selection_only=options["selection_only"],
                materials=options["embed_textures"],
            )
            return

        if export_format == "glb":
            # window override: the bundled glTF exporter unconditionally calls
            # ``context.window.cursor_set('WAIT')`` — AttributeError when window is
            # None (the Qt-pump state); btk.FbxUtils wraps its own.
            with btk.window_context_override():
                bpy.ops.export_scene.gltf(
                    filepath=out_path,
                    export_format="GLB",
                    use_selection=options["selection_only"],
                    export_cameras=options["include_cameras"],
                    export_lights=options["include_lights"],
                )
            return

        object_types = {"MESH", "EMPTY", "OTHER"}
        if options["include_cameras"]:
            object_types.add("CAMERA")
        if options["include_lights"]:
            object_types.add("LIGHT")
        if options["include_skins"]:
            object_types.add("ARMATURE")
        btk.FbxUtils.export(
            filepath=out_path,
            selection_only=options["selection_only"],
            object_types=object_types,
            use_tspace=options["include_tangents"],
            path_mode="COPY" if options["embed_textures"] else "AUTO",
            embed_textures=options["embed_textures"],
        )

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
        """Hierarchy Sync — diff/repair the scene hierarchy against a reference .blend
        (native blendertk panel, 1:1 with mayatk's ``hierarchy_sync`` for Diff/Fix; Pull
        isn't ported yet — see ``blendertk.env_utils.hierarchy_sync`` for why)."""
        self.sb.handlers.marking_menu.show("hierarchy_sync")

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
