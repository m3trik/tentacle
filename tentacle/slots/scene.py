# !/usr/bin/python
# coding=utf-8
"""Scene: one Slots class for both hosts.

Every host call goes through the host toolkit (``self.tk``):

* **Recent files / autosaves** (``list000`` / ``cmb002``): ``EnvUtils.get_recent_files``
  / ``get_recent_autosave`` list them, ``EnvUtils.open_scene`` opens one.
* **Import / Export** (``list001`` / ``list002``): this panel's own rows -- the other
  DCC's scene through the host's foreign-scene bridge (``EnvUtils.foreign_scene_bridge``
  / ``foreign_scene_import``), glTF and USD through that pull engine, the USD and glTF
  one-shots through ``EnvUtils.export_scene`` -- and the host's own import / export
  commands (``EnvUtils.get_file_commands`` / ``run_file_command``: Maya's File-menu
  dialogs, Send To and preset editors; Blender's operators with their file browsers).
* **Export Scene** (``tb003``): the option box, the guards and the path, then one
  ``EnvUtils.export_scene`` write -- or the foreign bridge for the other DCC's format.
* **Tools** (``list003``): bridges, managers, fixes and diagnostics, each a slot-wired
  leaf. A leaf only one host serves names that host (``requires``) and is hidden on
  the other; the tool panels it opens are tentacle's shared tools
  (``marking_menu.show``).
* **The workspace footer**: refreshed on the host's workspace events
  (``ScriptJobManager.WORKSPACE_EVENTS``).

Where the other DCC is named (Import Blender Scene, the Maya Bridge ...) the name comes
off the foreign bridge (``spec.app.name``, ``save_extensions``), so one table serves both
hosts.
"""

import functools
import html
import os

import pythontk as ptk

from tentacle import Slots


class SceneSlots(Slots):
    # ------------------------------------------------------------------ export tables
    #: ``(label, data)`` for the Export Scene format combo -- the formats BOTH hosts
    #: write. The other DCC's native format is appended (:meth:`_export_format_items`),
    #: so the combo is "the portable four plus the other DCC" on either side. ``"glb"``
    #: matches ``SceneExporter``'s own ``output_format`` vocabulary.
    EXPORT_FORMATS = (("FBX", "fbx"), ("OBJ", "obj"), ("GLB", "glb"), ("USD", "usd"))
    #: Output extension per portable format (``"foreign"`` resolves from the bridge).
    EXPORT_EXTENSIONS = {"fbx": ".fbx", "obj": ".obj", "glb": ".glb", "usd": ".usd"}
    #: Every extension a format's writer takes, where that is more than its default: a
    #: USD layer is text, crate or a package by its extension, and both hosts' writers
    #: pick the encoding off it (``.usdz`` packages the layer with its maps).
    EXPORT_EXTENSION_SPELLINGS = {"usd": ptk.USD_EXTENSIONS}
    #: ``(label, data)`` for the Transfer-via combo: the carrier a scene hand-off
    #: travels as (the foreign export and the Import <other DCC> Scene pull).
    #: pythontk's carrier vocabulary verbatim -- the bridges refuse any other.
    EXPORT_TRANSFER_ITEMS = tuple(
        (carrier.upper(), carrier) for carrier in ptk.CARRIER_EXTENSIONS
    )
    #: The Export Scene option box's combo objectNames. ``cmb_export_format`` was
    #: ``cmb_format`` until USD was inserted in front of the foreign twin: uitk
    #: persists a combo by INDEX, so the rename orphans a stored "Blend"/"MA"
    #: choice rather than silently turning it into "USD".
    EXPORT_FORMAT_COMBO = "cmb_export_format"
    EXPORT_TRANSFER_COMBO = "cmb_transfer"
    #: ``(label, data)`` for the Export Scene scope combo. Selected Only LEADS: the
    #: leading item is what an unconfigured option box shows.
    EXPORT_SCOPE_ITEMS = (("Selected Only", "selected"), ("Entire Scene", "all"))
    #: ``(label, data)`` for the save-location combo. Project Export Folder leads, so
    #: the default route is the no-prompt one the button labels "Quick".
    EXPORT_SAVE_ITEMS = (
        ("Project Export Folder", "export_dir"),
        ("Prompt for File", "prompt"),
    )
    #: The button label's scope word, per ``cmb_scope`` data value.
    EXPORT_SCOPE_LABELS = {"all": "Scene", "selected": "Sel"}
    #: The save mode that writes without asking -- the one the label marks "Quick".
    EXPORT_QUICK_SAVE_MODE = "export_dir"
    #: What an Export-list one-shot writes: the whole scene, every type. The list's
    #: entries carry no options of their own -- Export Scene is the configured route.
    ONE_SHOT_EXPORT_OPTIONS = {
        "selection_only": False,
        "include_cameras": True,
        "include_lights": True,
        "include_skins": True,
        "include_tangents": True,
        "embed_textures": True,
    }
    #: Triangle count at/above which an export with tangents on (a cost that scales
    #: with the mesh) earns a heads-up before the blocking write. Tunable.
    _DENSE_TRI_THRESHOLD = 5_000_000

    # ------------------------------------------------------------------ list tables
    #: The Import list, in order: ``(label, method, requires)``. A row naming no
    #: method is the host's own import command of that name, listed where
    #: ``EnvUtils.get_file_commands("import")`` offers it; a host command this table
    #: does not name follows the rows. ``{app}`` is the other DCC (its bridge's app).
    #: *requires* names the one host that serves a row (None: both).
    _IMPORT_ROWS = (
        ("Import File", None, None),
        ("Import Options", None, None),
        # Blender's: its stock FBX importer plays one take; FbxUtils.import_fbx
        # imports every take (Maya's Import File runs its own FBX importer).
        ("Import FBX", "_import_fbx", "blender"),
        ("Import OBJ", None, None),
        ("Import {app} Scene", "_import_foreign_scene", None),
        ("Import glTF", "_import_gltf", None),
        ("Import USD", "_import_usd", None),
        ("Import Collada", None, None),
        ("Append from .blend", None, None),
        ("Link from .blend", None, None),
        ("FBX Import Presets", None, None),
        ("OBJ Import Presets", None, None),
    )
    #: The Export list's one-shots, in order (see :attr:`_IMPORT_ROWS`). ``{ext}`` is
    #: the other DCC's scene extension.
    _EXPORT_ROWS = (
        ("Export Selection", None, None),
        ("Export {ext}", "_export_foreign_scene", None),
        ("Export USD", "_export_usd", None),
        ("Export FBX", None, None),
        ("Export OBJ", None, None),
        # Maya has no glTF writer: Export Scene's GLB route as a one-shot. Blender's
        # own glTF exporter is its "Export glTF" command, the row below.
        ("Export glTF", "_export_gltf", "maya"),
        ("Export glTF", None, None),
        ("Export Collada", None, None),
        ("Export All", None, None),
        ("Send to Unreal", None, None),
        ("Send to Unity", None, None),
        ("GoZ", None, None),
        ("Send to 3dsMax: As New Scene", None, None),
        ("Send to 3dsMax: Update Current", None, None),
        ("Send to 3dsMax: Add to Current", None, None),
        ("Export to Offline File", None, None),
        ("Export Options", None, None),
        ("FBX Export Presets", None, None),
        ("OBJ Export Presets", None, None),
    )
    #: The Export list's tool-panel row: a launcher rather than a one-shot, added
    #: beside Export Scene (nearest the trigger row).
    _SCENE_EXPORTER = "Scene Exporter"

    # ------------------------------------------------------------------ footer
    FOOTER_DEFAULT_TEXT = "No workspace set"
    FOOTER_TRUNCATE = {"length": 96, "mode": "middle"}
    #: Set in ``__init__`` from :meth:`_create_footer_controller`. Declared here
    #: because the handler reads it, and the subscription is live from inside that
    #: call -- before the assignment lands.
    _footer_controller = None

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.scene
        self.submenu = self.sb.loaded_ui.scene_submenu
        self._footer_controller = self._create_footer_controller()

    # ------------------------------------------------------------------ host facts
    def _foreign_bridge(self):
        """The bridge class that writes the other DCC's native scene (mayatk's
        ``BlenderBridge``, blendertk's ``MayaBridge``): its ``spec.app.name`` names
        that app, its ``save_extensions`` the files it writes."""
        return self.tk.EnvUtils.foreign_scene_bridge()

    def _foreign_app(self) -> str:
        """The other DCC's display name: "Blender" in Maya, "Maya" in Blender."""
        return self._foreign_bridge().spec.app.name

    def _scene_path(self) -> str:
        """The open scene, or "" when it has never been saved."""
        return self.tk.EnvUtils.saved_scene_path() or ""

    def _browse_start(self) -> str:
        """Where a file browser opens: beside the open scene, else in the workspace."""
        return os.path.dirname(self._scene_path()) or (
            self.tk.EnvUtils.workspace_root() or ""
        )

    def _report_error(self, error):
        """Show a host refusal as text: errors quote paths like ``</>``."""
        self.sb.message_box(html.escape(str(error)))

    # ------------------------------------------------------------------ workspace footer
    def _create_footer_controller(self):
        """Bind the panel footer to the workspace resolver and return its controller.

        The footer refreshes on the host's workspace events
        (``ScriptJobManager.WORKSPACE_EVENTS``: Maya's ``workspaceChanged``; Blender
        has none, so its scene open / save). The footer is owned by the MainWindow,
        so it outlives every widget ``_init``; the controller comes off the footer
        widget itself (``footer.status_controller``), uitk reached through the
        switchboard's window only.
        """
        footer = getattr(self.ui, "footer", None)
        if not footer:
            return None
        jobs = self.tk.ScriptJobManager
        mgr = jobs.instance()
        for event in jobs.WORKSPACE_EVENTS:
            mgr.subscribe(event, self._on_workspace_changed, owner=footer)
        mgr.connect_cleanup(footer, owner=footer)
        return footer.status_controller(
            resolver=self._workspace_status,
            default_text=self.FOOTER_DEFAULT_TEXT,
            truncate_kwargs=self.FOOTER_TRUNCATE,
        )

    def _workspace_status(self) -> str:
        """The footer's text: the current workspace's folder name, or ""."""
        root = self.tk.EnvUtils.workspace_root()
        return os.path.basename(os.path.normpath(root)) if root else ""

    def _on_workspace_changed(self):
        """Workspace event handler: refresh the footer's workspace status."""
        if self._footer_controller:
            self._footer_controller.update()

    # ------------------------------------------------------------------ list000 Recent Files
    def list000_init(self, widget):
        """Initialize Recent Files."""
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_up" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        recent_files = self.tk.EnvUtils.get_recent_files(slice(0, 11))
        w1 = widget.add("Recent Files")
        truncated = ptk.truncate(recent_files, 65)
        w1.sublist.add(zip(truncated, recent_files))
        widget.setVisible(bool(recent_files))

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Recent Files: open the picked scene."""
        data = item.item_data()
        if data:  # the "Recent Files" category row carries no file
            self._open_scene(str(data))

    def _open_scene(self, path):
        """Open *path* in place of the current scene; say so when it would not open."""
        if not self.tk.EnvUtils.open_scene(path):
            self.sb.message_box(
                f"Could not open <hl>{ptk.format_path(path, 'file')}</hl>.<br>"
                "See the script output for the reason."
            )

    # ------------------------------------------------------------------ cmb002 Autosave
    def cmb002_init(self, widget):
        """Initialize Autosave: the last day's autosaves, newest first."""
        recent_autosaves = self.tk.EnvUtils.get_recent_autosave(
            filter_time=24, timestamp_format="%H:%M:%S"
        )
        widget.add(
            {
                f"{stamp}  {ptk.format_path(path, 'file')}": path
                for path, stamp in recent_autosaves
            },
            header="Autosave:",
            clear=True,
        )

    def cmb002(self, index, widget):
        """Autosave: reopen a recent autosaved scene."""
        self._open_scene(widget.items[index])

    # ------------------------------------------------------------------ list001/002 rows
    def _list_rows(self, rows, direction):
        """``[(label, action, requires)]`` for the Import or Export list: *rows* in
        their order, a method row bound here, a command row kept only where the host
        offers that command (``EnvUtils.get_file_commands(direction)``), then any host
        command *rows* does not name."""
        bridge = self._foreign_bridge()
        names = {"app": bridge.spec.app.name, "ext": bridge.save_extensions[0]}
        offered = list(self.tk.EnvUtils.get_file_commands(direction))
        resolved = []
        for label, method, requires in rows:
            if method is None:
                if label in offered:
                    offered.remove(label)
                    resolved.append((label, self._file_command(label), requires))
                continue
            resolved.append((label.format(**names), getattr(self, method), requires))
        return resolved + [(name, self._file_command(name), None) for name in offered]

    def _file_command(self, name):
        """The action running the host's own import / export command *name*."""
        return functools.partial(self._run_file_command, name)

    def _run_file_command(self, name):
        """Run the host's own import / export command *name*; a refusal (nothing
        selected, a plug-in that will not load) reaches the user as the host words it."""
        try:
            self.tk.EnvUtils.run_file_command(name)
        except (RuntimeError, ValueError) as error:
            self._report_error(error)

    def _add_rows(self, sublist, rows):
        """Add *rows* to *sublist*: each item carries its action as its data, and a
        row only one host serves is hidden on the other (uitk's ``requires`` policy)."""
        for label, action, requires in rows:
            item = sublist.add(label, data=action)
            if requires:
                item.setProperty("requires", requires)
                self.sb.apply_visibility_policy(item)

    @staticmethod
    def _run_item(item):
        """Run a list item's action; a category row carries none."""
        action = item.item_data()
        if callable(action):
            action()

    # ------------------------------------------------------------------ list001 Import
    def list001_init(self, widget):
        """Initialize Import."""
        widget.fixed_item_height = 18
        # Lowest list in the submenu: open downward, covering the root row. The
        # panel's header-menu row fans right on hover instead.
        widget.apply_preset(
            "expand_overlay" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        root = widget.add(
            "Import",
            setToolTip=f"Import a file: FBX, OBJ, glTF, USD, a {self._foreign_app()} "
            "scene -- or open the host's own import options.",
        )
        self._add_rows(root.sublist, self._list_rows(self._IMPORT_ROWS, "import"))

    @Slots.Signals("on_item_interacted")
    def list001(self, item):
        """Import: run the picked row."""
        self._run_item(item)

    def _pull_scene(self, file_types, title, filter_description, kind, importer=None):
        """Browse for a file and pull it into the scene.

        Every Import row that reaches the scene through the foreign-scene engine
        (``EnvUtils.foreign_scene_import``) shares this body -- only the browse filter
        and the wording differ -- so the carrier choice, the wait cursor and the
        failure report cannot drift between them. The other DCC's scene converts
        through a fresh headless app and travels as Export Scene's Transfer-via
        carrier; a USD file imports natively (the carrier is inert); a glTF imports
        each host's own way (KTX2 decoded first).

        Parameters:
            file_types: Browse filter globs, e.g. ``["*.blend"]``.
            title: File-dialog title.
            filter_description: File-dialog filter label.
            kind: What failed, for the error message ("Blender scene", "USD").
            importer: ``importer(path) -> imported objects`` run in place of the
                engine, for a file the host imports natively; the carrier is inert.
        """
        src = self.sb.file_dialog(
            file_types=file_types,
            title=title,
            start_dir=self._browse_start(),
            filter_description=filter_description,
            allow_multiple=False,
        )
        if not src:
            return
        app = self.sb.QtWidgets.QApplication
        app.setOverrideCursor(self.sb.QtCore.Qt.WaitCursor)
        try:
            if importer is not None:
                imported = importer(src)
            else:
                engine = self.tk.EnvUtils.foreign_scene_import()
                imported = engine().import_scene(src, via=self._transfer_carrier())
        except Exception as error:  # noqa: BLE001 - every engine failure, one report
            self.sb.message_box(
                f"{kind} import failed: <hl>{html.escape(str(error))}</hl>"
            )
            return
        finally:
            app.restoreOverrideCursor()
        self.sb.message_box(
            f"Imported <hl>{len(imported)}</hl> object(s) from "
            f"<hl>{os.path.basename(src)}</hl>."
        )

    def _import_foreign_scene(self):
        """Import the other DCC's scene (Import list row): a .blend into Maya, a
        .ma / .mb into Blender, converted in a fresh headless app."""
        app = self._foreign_app()
        extensions = self.tk.EnvUtils.foreign_scene_import().SCENE_EXTENSIONS
        self._pull_scene(
            [f"*{ext}" for ext in extensions],
            f"Import {app} Scene",
            f"{app} Scenes",
            f"{app} scene",
        )

    def _import_gltf(self):
        """Import a glTF container (.glb / .gltf): Blender imports it natively, Maya
        through a fresh headless Blender (else pythontk's glTF -> FBX); a KTX2 file is
        decoded first either way."""
        self._pull_scene(["*.glb", "*.gltf"], "Import glTF", "glTF Files", "glTF")

    def _import_usd(self):
        """Import a USD layer or package through the host's interchange import (every
        prim, animation read as keys), never the stock importer's defaults."""
        self._pull_scene(
            [f"*{ext}" for ext in ptk.USD_EXTENSIONS], "Import USD", "USD Files", "USD"
        )

    def _import_fbx(self):
        """Import an FBX with ALL its animation (Blender's row): the takes that agree
        play as one, the alternatives are parked in Key Stash."""
        self._pull_scene(
            ["*.fbx"],
            "Import FBX",
            "FBX Files",
            "FBX",
            importer=self.tk.FbxUtils.import_fbx,
        )

    # ------------------------------------------------------------------ list002 Export
    def list002_init(self, widget):
        """Initialize Export.

        Population order keeps the two tools nearest the trigger row. The submenu
        expands upward, so it is populated in reverse: the LAST item added sits
        nearest the trigger -- Scene Exporter, then Export Scene (``tb003``, its
        option-box gear and all) closest to the cursor, the one-shots stacking above.
        The panel's hover_menu flyout fans right with its top row at the trigger, so
        the same rows go in the opposite order: tools first, one-shots below.
        """
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_up" if submenu else "hover_menu")
        root = widget.add(
            "Export",
            setToolTip="Export the scene or the selection: FBX, OBJ, glTF, USD, a "
            f"{self._foreign_app()} scene, Send To, presets.",
        )
        one_shots = self._list_rows(self._EXPORT_ROWS, "export")
        exporter = (
            self._SCENE_EXPORTER,
            self._open_scene_exporter,
            None,
        )
        # Registering tb003 runs tb003_init (building the option-box menu), wires
        # clicked -> tb003, and binds ui.tb003 so the panel's entry reads the shared
        # options.
        tb003_kwargs = dict(
            setObjectName="tb003",
            # Placeholder only -- tb003_init's wiring relabels it from the options.
            setText=self._default_export_button_text(),
            setToolTip=(
                "Export the scene or the selection -- the entry's own label says\n"
                "which, in what format, and whether it writes straight into the\n"
                "project (Quick) or prompts for a location.\n"
                "Click the gear icon to configure scope, format, included types,\n"
                "and save location."
            ),
        )
        if submenu:
            self._add_rows(root.sublist, one_shots[::-1])
            self._add_rows(root.sublist, [exporter])
            self.add_slot_widget(root.sublist, **tb003_kwargs)
        else:
            self.add_slot_widget(root.sublist, **tb003_kwargs)
            self._add_rows(root.sublist, [exporter])
            self._add_rows(root.sublist, one_shots)

    @Slots.Signals("on_item_interacted")
    def list002(self, item):
        """Export: run the picked one-shot or open the Scene Exporter.

        tb003 never arrives here -- its option-box wrap swapped it out of the list's
        item set, so its own clicked signal drives the slot (``Slots.add_slot_widget``).
        """
        self._run_item(item)

    def _open_scene_exporter(self):
        """Scene Exporter: the shared task / check export panel."""
        self.sb.handlers.marking_menu.show("scene_exporter")

    def _export_usd(self):
        """Export USD (Export list row): the whole scene through Export Scene's USD writer."""
        self._export_one_shot("usd")

    def _export_gltf(self):
        """Export glTF (Maya's Export list row): Export Scene's GLB route, FBX plus
        FBX2glTF, as a one-shot."""
        self._export_one_shot("glb")

    # ------------------------------------------------------------------ tb003 Export Scene
    def _export_format_items(self):
        """``[(label, data), ...]`` for the format combo, the other DCC's last."""
        return [*self.EXPORT_FORMATS, (self._foreign_format_label(), "foreign")]

    def _foreign_format_label(self) -> str:
        """The other DCC's native format as the format combo names it ("BLEND" in
        Maya, "MA" in Blender): its bridge's first save extension."""
        return self._foreign_bridge().save_extensions[0].lstrip(".").upper()

    def _transfer_carrier(self, menu=None) -> str:
        """The Transfer-via choice (``"fbx"`` / ``"usd"``) off the Export Scene option
        box -- *menu* when the caller holds it, else the panel's own ``tb003`` (the
        Import list's pull rows share the setting); ``"fbx"`` before it exists."""
        if menu is None:
            widget = getattr(getattr(self, "ui", None), "tb003", None)
            menu = getattr(getattr(widget, "option_box", None), "menu", None)
        combo = getattr(menu, self.EXPORT_TRANSFER_COMBO, None)
        return (combo.currentData() if combo is not None else None) or "fbx"

    def _export_button_text(self, scope, save_mode, format_label) -> str:
        """The Export button's label, spelled out from the options it will run with:
        "Quick Export Sel GLB", "Export Scene FBX". *Quick* marks the no-prompt route;
        the suffix is the format combo's LABEL, so the other DCC's format reads as the
        host names it."""
        prefix = "Quick " if save_mode == self.EXPORT_QUICK_SAVE_MODE else ""
        scope_label = self.EXPORT_SCOPE_LABELS.get(
            scope, self.EXPORT_SCOPE_LABELS["selected"]
        )
        return " ".join(p for p in (f"{prefix}Export", scope_label, format_label) if p)

    def _default_export_button_text(self) -> str:
        """The label for the option defaults -- each combo's LEADING item, built off
        the same tables the combos are so it cannot drift from them."""
        return self._export_button_text(
            self.EXPORT_SCOPE_ITEMS[0][1],
            self.EXPORT_SAVE_ITEMS[0][1],
            self.EXPORT_FORMATS[0][0],
        )

    def tb003_init(self, widget):
        """Initialize Export Scene's option box."""
        if getattr(widget, "is_initialized", False):
            return
        app = self._foreign_app()
        foreign = self._foreign_format_label()
        menu = widget.option_box.menu
        menu.setTitle("Export Options")
        cmb_scope = menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip=(
                "What to export:\n"
                "• Selected Only — export only the current selection\n"
                "• Entire Scene — export the full scene"
            ),
        )
        # By DATA, not index: Selected Only leads now, so an index persisted against
        # the old order would silently select the other scope. A stale int no-ops on
        # restore (findData misses) and is overwritten on the next save.
        cmb_scope.restore_by = "data"
        for text, data in self.EXPORT_SCOPE_ITEMS:
            cmb_scope.addItem(text, data)

        cmb_save = menu.add(
            "QComboBox",
            setObjectName="cmb_save",
            setToolTip=(
                "Where to write the exported file(s):\n"
                "• Project Export Folder — the export folder of the scene's "
                "workspace: its project, else the scene's own folder (the FBX "
                "export rule, else data/), under the scene's name\n"
                "• Prompt for File — choose the name and location each time "
                "(filename pre-filled from the scene, editable)"
            ),
        )
        for text, data in self.EXPORT_SAVE_ITEMS:
            cmb_save.addItem(text, data)

        menu.add(
            "QCheckBox",
            setText="Include Cameras",
            setObjectName="chk_cameras",
            setChecked=False,
            setToolTip=(
                "Include cameras in the export.\n"
                "Applies to whole-scene export only; disabled in Selected Only "
                "mode (cameras export only if selected)."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Include Lights",
            setObjectName="chk_lights",
            setChecked=False,
            setToolTip=(
                "Include lights in the export.\n"
                "Applies to whole-scene export only; disabled in Selected Only "
                "mode (lights export only if selected)."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Include Skins",
            setObjectName="chk_skins",
            setChecked=False,
            setToolTip=(
                "Include skinning: skin clusters (Maya) or armatures (Blender) and "
                "their weights.\nAvailable in both scopes — the weights travel with "
                "the selected mesh."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Include Tangents/Binormals",
            setObjectName="chk_tangents",
            setChecked=True,
            setToolTip=(
                "Export per-vertex tangents and binormals — needed for correct "
                "normal mapping on game assets.\n"
                "On dense meshes this roughly doubles export time and file size; "
                "untick for a faster export when tangents aren't needed (e.g. "
                "photogrammetry meshes with a baked albedo)."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Embed Textures",
            setObjectName="chk_embed",
            setChecked=True,
            setToolTip=(
                "Copy texture files into the FBX so it is self-contained.\n"
                "Untick to keep textures as external references — far "
                "smaller/faster when maps are large (e.g. an 8K photogrammetry "
                "texture already sitting beside the mesh)."
            ),
        )
        cmb_format = menu.add(
            "QComboBox",
            setObjectName=self.EXPORT_FORMAT_COMBO,
            setToolTip=(
                "Output format:\n"
                "• FBX — the interchange default\n"
                "• OBJ — geometry only (no hierarchy, skinning or animation)\n"
                "• GLB — glTF binary (Maya: FBX through FBX2glTF, the intermediate\n"
                "  discarded; Blender: its own glTF exporter)\n"
                "• USD — a .usd layer through the interchange export\n"
                "  (UsdPreviewSurface materials; animation sampled where it moves)\n"
                f"• {foreign} — a real {app} scene, via a fresh headless {app}\n"
                f"  (slower; a local {app} install is required)"
            ),
        )
        for text, data in self._export_format_items():
            cmb_format.addItem(text, data)
        cmb_transfer = menu.add(
            "QComboBox",
            setObjectName=self.EXPORT_TRANSFER_COMBO,
            setToolTip=(
                "Transfer via — the intermediate a scene hand-off travels as:\n"
                "• FBX — the default; carries instancing natively\n"
                "• USD — native materials, typed scene graph, sampled animation;\n"
                "  an instanced / linked-duplicate selection is refused (use FBX)\n"
                f"Applies to the {foreign} export and to Import {app} Scene; the\n"
                "native formats ignore it."
            ),
        )
        for text, data in self.EXPORT_TRANSFER_ITEMS:
            cmb_transfer.addItem(text, data)

        self._wire_export_options(widget)

    def _wire_export_options(self, widget):
        """Keep the Export button's label and the scene-only toggles in step.

        Cameras and lights are scene-level categories: in Selected Only mode they
        would export only if explicitly selected, so the "include all" intent does
        not apply. That is uitk's declarative rule (``enable_when``), which re-applies
        on late registration and on a preset load made with signals blocked.

        The label is its text sibling (``text_from``), derived from ALL THREE combos.
        The format combo opts out of the default reader: its items carry data, and
        the button wants to say "FBX", not "fbx". The carrier is deliberately NOT
        gated on the format: the Import list's pull rows read it too.
        """
        menu = widget.option_box.menu
        self.sb.enable_when(menu, "chk_cameras,chk_lights", "cmb_scope", "all")
        self.sb.text_from(
            menu,
            widget,
            ["cmb_scope", "cmb_save", self.EXPORT_FORMAT_COMBO],
            self._export_button_text,
            value={self.EXPORT_FORMAT_COMBO: lambda w: w.currentText()},
        )

    def tb003(self, widget):
        """Export Scene in the chosen format, using the configured options.

        Every trigger is a tb003 PushButton carrying its own option-box gear, so the
        options come off the widget that was clicked; uitk mirrors a value into every
        related surface's store on change, so the panel and submenu agree.
        """
        menu = widget.option_box.menu
        export_format = getattr(menu, self.EXPORT_FORMAT_COMBO).currentData()
        selection_only = menu.cmb_scope.currentData() == "selected"
        options = {
            "selection_only": selection_only,
            # Inert in Selected Only mode (tb003_init); coerced so a stale
            # checked-but-disabled box cannot leak through.
            "include_cameras": menu.chk_cameras.isChecked() and not selection_only,
            "include_lights": menu.chk_lights.isChecked() and not selection_only,
            "include_skins": menu.chk_skins.isChecked(),
            "include_tangents": menu.chk_tangents.isChecked(),
            "embed_textures": menu.chk_embed.isChecked(),
        }
        selection = self.tk.CoreUtils.selected_objects() if selection_only else None
        if selection_only and not selection:
            self.sb.message_box("No objects selected.")
            return

        if not self._confirm_export_cost(export_format, options):
            return

        out_path = self._resolve_export_path(
            menu.cmb_save.currentData(),
            self._export_extension(export_format),
            self._export_spellings(export_format),
        )
        if not out_path:
            return

        if export_format == "foreign":
            # A multi-second app launch with its own wait cursor and reporting, not a
            # host-side write -- so not under the progress context below.
            result = self._run_foreign_export(
                out_path, selection, carrier=self._transfer_carrier(menu)
            )
            if result:
                self.sb.message_box(
                    f"Exported <hl>{ptk.format_path(result['output'], 'file')}</hl> "
                    f"({result['duration']:.1f}s)."
                )
            return

        self._write_native(export_format, out_path, options)

    def _export_extension(self, export_format: str) -> str:
        """Output extension for a format-combo data value; the other DCC's comes off
        its bridge, which already declares it."""
        if export_format == "foreign":
            return self._foreign_bridge().save_extensions[0]
        return self.EXPORT_EXTENSIONS[export_format]

    def _export_spellings(self, export_format: str):
        """Every extension a typed name may keep for *export_format*, or ``None`` (the
        default alone). The other DCC's come off its bridge -- a Maya scene is
        ``.ma`` or ``.mb`` -- so a typed ``shot.mb`` stays one."""
        if export_format == "foreign":
            return tuple(self._foreign_bridge().save_extensions)
        return self.EXPORT_EXTENSION_SPELLINGS.get(export_format)

    def _resolve_export_path(self, save_mode: str, extension: str, accepted=None):
        """Output path for *save_mode*, or ``None`` to cancel (reported to the user).

        ``"export_dir"`` writes into the export folder of the scene's workspace
        (``ptk.Workspace.export_dir``: the ``FBX export`` rule, then ``FBX``, else
        ``data/``; made on write) under the scene's own name. That workspace is the
        scene's project, else the scene's own folder (``DataNodes.scene_workspace``).
        ``"prompt"`` asks, pre-filled with exactly that path (the scene's folder while
        the export folder does not exist yet). An unsaved scene has no name to write
        under, so that combination is the one hard error.

        *accepted* are the extensions a picked name may carry as typed (default:
        *extension* alone); any other name gets *extension* appended.
        """
        scene_path = self._scene_path()
        base = os.path.splitext(os.path.basename(scene_path))[0] or "untitled"
        label = extension.lstrip(".").upper()
        accepted = tuple(accepted or (extension,))
        ws = self.tk.DataNodes.scene_workspace()

        if save_mode == "prompt":
            start_dir = ws.export_dir() if ws is not None else ""
            if not os.path.isdir(start_dir):
                # Asking makes no folder: start where something exists.
                start_dir = self._browse_start()
            picked = self.sb.save_file_dialog(
                file_types=[f"*{ext}" for ext in accepted],
                title=f"Export {label} As",
                # A FILE path, not a directory: it pre-fills the name box.
                start_dir=os.path.join(start_dir, base + extension),
                filter_description=f"{label} Files",
            )
            if not picked:
                return None
            # Qt does not reliably append the filter's suffix to a bare name, and the
            # writer picks its translator off the extension.
            return picked if picked.lower().endswith(accepted) else picked + extension

        if not scene_path:
            self.sb.message_box(
                "Scene has not been saved yet.<br>Save the scene first, or choose "
                "<hl>Prompt for File</hl> in the export options."
            )
            return None
        if ws is None:
            # A saved scene always has a workspace (its project, else its own folder);
            # None means that folder no longer exists.
            return os.path.splitext(scene_path)[0] + extension
        return os.path.join(ws.export_dir(create=True), base + extension)

    def _confirm_export_cost(self, export_format, options) -> bool:
        """The dense-export gate for *options*; False when the user cancels. OBJ
        carries no tangent channel, so that cost is not paid there."""
        return self._confirm_dense_export(
            options["selection_only"],
            options["include_tangents"] and export_format != "obj",
        )

    def _confirm_dense_export(self, selection_only, include_tangents) -> bool:
        """Warn before a dense export with tangents on; False if cancelled.

        True (proceed) for the common case: the dialog appears only when the export
        set is dense AND tangents are on, the combination that turns a quick export
        into a multi-minute one (``EnvUtils.scene_triangle_count``).
        """
        if not include_tangents:
            return True
        tris = self.tk.EnvUtils.scene_triangle_count(selection_only=selection_only)
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

    def _write_native(self, export_format, out_path, options):
        """Write *out_path* through the host's writer (``EnvUtils.export_scene``),
        then report either outcome.

        A single blocking call that scales with poly count, so it runs inside the
        footer progress context with a status painted first (``tick()`` pumps the
        event loop) -- working, not hung. A failure propagates out of the context so
        it skips its "Complete" flash, then lands in one report.
        """
        label = os.path.splitext(out_path)[1].lstrip(".").upper()
        try:
            with self.sb.progress(
                text=f"Exporting {label}… dense scenes can take a while"
            ) as tick:
                tick()  # paint the status before the blocking export
                self.tk.EnvUtils.export_scene(
                    out_path, export_format, progress=tick, **options
                )
        except Exception as error:  # noqa: BLE001 - every writer, one report
            self.sb.message_box(f"Export failed:<br>{html.escape(str(error))}")
            return
        self.sb.message_box(f"Exported <hl>{ptk.format_path(out_path, 'file')}</hl>.")

    def _export_one_shot(self, export_format: str):
        """Write the WHOLE scene in native *export_format* (an Export-list one-shot):
        every type, through Export Scene's writer, behind its own prompt, which takes
        every spelling the writer does (a USD layer as ``.usda`` / ``.usdc`` /
        ``.usdz``)."""
        options = dict(self.ONE_SHOT_EXPORT_OPTIONS)
        if not self._confirm_export_cost(export_format, options):
            return
        out_path = self._resolve_export_path(
            "prompt",
            self._export_extension(export_format),
            self._export_spellings(export_format),
        )
        if out_path:
            self._write_native(export_format, out_path, options)

    # ------------------------------------------------------------------ the other DCC's scene
    def _run_foreign_export(self, out_path, objects=None, carrier: str = "fbx"):
        """Run the blocking bridge hand-off; return its result dict, or ``None``.

        *carrier* is the intermediate the hand-off travels as (the Transfer-via
        choice). A fresh headless target app starts, imports and saves, so a wait
        cursor covers the run and the destination is chosen BEFORE it starts. The
        bridge reports a handled failure by returning ``None`` (having logged the
        reason), so both that and a raised error reach the user.
        """
        bridge = self._foreign_bridge()
        app = bridge.spec.app.name  # the TARGET app
        qapp = self.sb.QtWidgets.QApplication
        qapp.setOverrideCursor(self.sb.QtCore.Qt.WaitCursor)
        try:
            result = bridge().save_as(
                out_path, objects, params={ptk.CARRIER_PARAM: carrier}
            )
        except Exception as error:  # noqa: BLE001 - every bridge failure, one report
            self.sb.message_box(
                f"Export to {app} failed: <hl>{html.escape(str(error))}</hl>"
            )
            return None
        finally:
            qapp.restoreOverrideCursor()

        if not result:  # handled failure -- the bridge already logged the reason
            self.sb.message_box(
                f"Export to {app} <hl>failed</hl>.<br>See the script output for the "
                f"reason (a local {app} install is required)."
            )
        return result

    def _export_foreign_scene(self):
        """Write the WHOLE scene in the other DCC's native format (Export list row):
        the push mirror of Import <other DCC> Scene, behind its own prompt."""
        bridge = self._foreign_bridge()
        app = bridge.spec.app.name
        extensions = bridge.save_extensions
        base = os.path.splitext(os.path.basename(self._scene_path()))[0] or "untitled"
        dest = self.sb.save_file_dialog(
            file_types=[f"*{ext}" for ext in extensions],
            title=f"Export {app} Scene",
            start_dir=os.path.join(self._browse_start(), base + extensions[0]),
            filter_description=f"{app} Scenes",
        )
        if not dest:
            return
        result = self._run_foreign_export(dest, carrier=self._transfer_carrier())
        if result:
            self.sb.message_box(
                f"Exported <hl>{ptk.format_path(result['output'], 'file')}</hl> "
                f"({result['duration']:.1f}s)."
            )

    # ------------------------------------------------------------------ list003 Tools
    #: Tooltip for the Tools list's root row.
    TOOLS_ROOT_TOOLTIP = "Scene bridges, management, fixes and diagnostics."
    #: Shown before a non-orthogonal fix: what it does to the object, per host.
    NON_ORTHOGONAL_FIX_EFFECT = (
        "Fixing bakes the shear out: each object stays where it is and looks "
        "identical. Maya freezes its rotate/scale into the shape (translate channels "
        "and their connections are never touched); Blender clears its parent, keeping "
        "the transform, so the object is un-parented (a Blender object has no shear "
        "of its own to freeze)."
    )

    def _tools_items(self):
        """``{category: [(label, objectName, tooltip, requires), ...]}`` for the Tools
        list. *requires* names the one host that serves a leaf (None: both); a label or
        tooltip naming ``{app}`` names the other DCC. A method, not a class attribute:
        one tooltip is built with the switchboard's formatter."""
        return {
            "Bridges": [
                (
                    "Mesh Converter",
                    "b013",
                    "Open the FBX -> GLB converter window.\nBacked by "
                    "godotengine/FBX2glTF; the binary is downloaded on first use.",
                    None,
                ),
                (
                    "{app} Bridge",
                    "b010",
                    "Send the selected objects to a fresh {app} (export FBX + run a "
                    "chosen import template).",
                    None,
                ),
                (
                    "Unity Bridge",
                    "b016",
                    "Send the selected objects to a Unity project (export FBX + copy "
                    "into Assets/).",
                    None,
                ),
            ],
            "Manage": [
                (
                    "Reference Manager",
                    "b001",
                    "Open the Reference Manager: the workspace's scenes and the "
                    "scene's references (Blender: linked libraries).",
                    None,
                ),
                (
                    "Hierarchy Sync",
                    "b004",
                    "Diff and repair the scene hierarchy against a reference scene.",
                    None,
                ),
                (
                    "Naming",
                    "b005",
                    "Find, rename and suffix objects (the Naming tool).",
                    None,
                ),
                (
                    "Audio Clips",
                    "b003",
                    "Manage the scene's audio clips: add, remove, trim, and sync the "
                    "scene range.",
                    None,
                ),
                (
                    "Blendshape Animator",
                    "b015",
                    "Build a morph between two meshes, sculpt in-between tweens to "
                    "customize the curve, and apply them back.",
                    None,
                ),
            ],
            "Recover": [
                (
                    "Save to Original Scene",
                    "b014",
                    "Save the currently open autosave back to the original scene "
                    "file.\nEnabled only when an autosave is open and the original "
                    "is locatable.",
                    # Maya's autosave names its scene; recovering a Blender
                    # autosave to its .blend is not built (BACKLOG).
                    "maya",
                ),
            ],
            "Fix": [
                (
                    "Cleanup Unknown",
                    "b006",
                    "Fix common scene issues:\n• Remove unknown/legacy "
                    "nodes/plugins/expressions",
                    "maya",
                ),
                (
                    "Scene Cleanup",
                    "b_cleanup",
                    "Purge orphan datablocks (meshes, materials, images … with no "
                    "users).",
                    "blender",
                ),
                (
                    "Fix OCIO",
                    "b009",
                    "Fix Maya Color Management / OCIO config preferences.",
                    "maya",
                ),
                (
                    "Fix Color Spaces",
                    "b011",
                    "Give each texture its color space by map type: data maps "
                    "(normal, roughness, metallic, height …) raw, color maps sRGB "
                    "(Maya: also repairs file nodes whose color space is missing).",
                    None,
                ),
                (
                    "Fix Mangled Names",
                    "b018",
                    "Repair scratch/mangled node names — accumulated "
                    "'__uninst_tmp' tokens, '__RZTMP' Rizom suffixes, 'FBXASC###' "
                    "import escapes, underscore runs — on transforms AND shapes, "
                    "then conform shapes to '<transform>Shape'.\nScope: selection, "
                    "or the whole scene when nothing is selected.\nSame repair the "
                    "Scene Exporter's 'Fix Mangled Names' task runs.",
                    "maya",
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
                            "Shear on the object itself (Maya; a Blender object "
                            "cannot carry its own).",
                            "Shear inherited from a non-uniformly scaled, rotated "
                            "parent — which reads as zero shear on the object.",
                        ],
                        notes=[
                            "Scope and a report-only dry run are set in the option box.",
                        ],
                    ),
                    None,
                ),
            ],
            "Diagnostics": [
                (
                    "Get Scene Info",
                    "tb001",
                    "Show a scene report in the viewer: file, units and a census; "
                    "rendered vs unique triangles, draw calls, materials and texture "
                    "memory; and a prioritized Fix First list. Object and material "
                    "names select what they name (Blender: a material opens in the "
                    "Shader Editor).\nScope, profile (Adaptive / Generic) and "
                    "sections are set via the option box.",
                    None,
                ),
                (
                    "Scene Metadata",
                    "b017",
                    "Show the tool-authored metadata stored on the scene's data nodes "
                    "(data_internal + data_export) as JSON — shot metadata, audio "
                    "manifests, bake sessions, etc.\nUse Save in the viewer to write "
                    "it to a .json file.",
                    None,
                ),
                (
                    "Check GLB / FBX",
                    "b019",
                    "Run the Scene Exporter's post-write gates (Verify The Written "
                    "File) over .glb / .fbx files already on disk — a truncated "
                    "container, a dropped take, a NaN in an accessor, a clip that "
                    "disagrees with its take.\nA .glb and .fbx sharing a name are "
                    "checked together. Report only.",
                    None,
                ),
                (
                    "Toggle Command Ports",
                    "b012",
                    "Toggle Maya command ports on/off (MEL :7001, Python :7002).\n"
                    "Used for external editor connections.",
                    "maya",
                ),
            ],
        }

    def _tools_leaf(self, requires):
        """The widget class ``add_slot_widget`` builds a Tools leaf from: uitk's
        PushButton, tagged *requires* BEFORE it registers, so the visibility policy
        hides it ahead of its ``*_init`` (which then never runs on the other host)."""

        def build():
            leaf = self.sb.registered_widgets.PushButton()
            if requires:
                leaf.setProperty("requires", requires)
            return leaf

        return build

    def list003_init(self, widget):
        """Tools list: the scene actions grouped into one expandable row.

        Every leaf is a real slot-wired widget carrying its objectName, so its slot,
        tooltip, option box (``tb001`` / ``tb002``) and QSettings identity follow it.
        A category whose every leaf one host serves is hidden on the other too.

        The submenu's trigger row is a narrow strip near the right edge, so its
        flyout opens ON TOP of that row and the categories fan LEFT. The panel's row
        is a layout-managed header menu and fans right on hover.
        """
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_overlay_left" if submenu else "hover_menu")
        app = self._foreign_app()
        root = widget.add("Tools", setToolTip=self.TOOLS_ROOT_TOOLTIP)
        for category, entries in self._tools_items().items():
            cat = root.sublist.add(category)
            hosts = {requires for *_, requires in entries}
            if len(hosts) == 1 and None not in hosts:
                cat.setProperty("requires", hosts.pop())
                self.sb.apply_visibility_policy(cat)
            for label, name, tooltip, requires in entries:
                self.add_slot_widget(
                    cat.sublist,
                    widget_class=self._tools_leaf(requires),
                    setObjectName=name,
                    setText=label.format(app=app),
                    setToolTip=tooltip.replace("{app}", app),
                )

    @Slots.Signals("on_item_interacted")
    def list003(self, item):
        """Dispatch a Tools leaf to its own slot.

        Category rows are navigation only. Leaves are slot-wired widgets, so
        ``call_slot`` routes through the switchboard's wrapper, which injects the
        ``widget`` argument for the slots that declare it. An option-box-wrapped leaf
        never arrives: the wrap leaves it out of the list's item set.
        """
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        call = getattr(item, "call_slot", None)
        if callable(call):
            call()

    # ------------------------------------------------------------------ Tools: bridges
    def b013(self):
        """Mesh Converter (FBX -> GLB): the DCC-agnostic extapps tool, its file
        dialog starting beside the open scene, and its "From FBX references" toggle
        reading the FBX files behind the selected references
        (``ReferenceManager.selected_reference_paths``)."""
        ui = self.sb.handlers.external_app.launch("mesh_convert", show=False)
        scene = self._scene_path()
        if scene:
            ui.slots.source_dir = os.path.dirname(scene)
        ui.slots.fbx_provider = functools.partial(
            self.tk.ReferenceManager.selected_reference_paths, (".fbx",)
        )
        self.sb.handlers.marking_menu.show(ui)

    def b010(self):
        """The other DCC's bridge: the shared tool named after its TARGET app
        (``blender_bridge`` in Maya, ``maya_bridge`` in Blender)."""
        self.sb.handlers.marking_menu.show(f"{self._foreign_app().lower()}_bridge")

    def b016(self):
        """Unity Bridge: send the selection to a Unity project's Assets/."""
        self.sb.handlers.marking_menu.show("unity_bridge")

    # ------------------------------------------------------------------ Tools: manage
    def b001(self):
        """Reference Manager (Maya references, Blender linked libraries)."""
        self.sb.handlers.marking_menu.show("reference_manager")

    def b004(self):
        """Hierarchy Sync: diff / pull / fix the hierarchy against a reference scene."""
        self.sb.handlers.marking_menu.show("hierarchy_sync")

    def b005(self):
        """Naming: the shared Naming tool."""
        self.sb.handlers.marking_menu.show("naming")

    def b003(self):
        """Audio Clips: the shared tool over the host's ``AudioClips``."""
        self.sb.handlers.marking_menu.show("audio_clips")

    def b015(self):
        """Blendshape Animator: the shared tool over the host's ``BlendshapeAnimator``."""
        self.sb.handlers.marking_menu.show("blendshape_animator")

    # ------------------------------------------------------------------ Tools: recover (Maya)
    def b014_init(self, widget):
        """Initialize Save to Original Scene: enabled, labelled and tooltipped from the
        original of the open autosave, re-read on every scene open."""
        if getattr(widget, "hidden_by_policy", None) == "requires":
            return  # not this host's (list003 tags it before it registers)
        if not widget.is_initialized:
            widget.refresh_on_show = True
            self._b014_widget = widget
            mgr = self.tk.ScriptJobManager.instance()
            mgr.subscribe("SceneOpened", self._on_scene_changed, owner=self)
            mgr.subscribe("NewSceneOpened", self._on_scene_changed, owner=self)
            mgr.connect_cleanup(widget, owner=self)

        current = self._scene_path()
        env = self.tk.EnvUtils
        is_autosave = bool(current) and env.matches_autosave_pattern(
            os.path.basename(current)
        )
        original = env.find_original_for_autosave(current) if is_autosave else None

        widget.setEnabled(bool(original))
        if original:
            widget.setToolTip(f"Save current autosave back to:\n{original}")
            short = ptk.truncate(os.path.basename(original), 10, mode="end")
            widget.setText(f"Save to: {short}")
        else:
            widget.setText("Save to Original Scene")
            widget.setToolTip(
                "Could not resolve the original scene for this autosave."
                if is_autosave
                else "Only available when an autosave file is open."
            )

    def _on_scene_changed(self):
        """Scene open handler: refresh b014."""
        button = getattr(self, "_b014_widget", None)
        if button is not None:
            self.b014_init(button)

    def b014(self):
        """Save to Original Scene: save the open autosave back to its original, the
        existing original backed up first (``EnvUtils.save_autosave_to_original``)."""
        original = self.tk.EnvUtils.find_original_for_autosave(self._scene_path())
        if not original:
            self.sb.message_box("Could not resolve the original scene.")
            return
        choice = self.sb.message_box(
            f"Save current autosave to:<br><hl>{original}</hl><br>"
            "(The existing file is backed up to its incrementalSave folder.)",
            "Save",
            "Cancel",
        )
        if choice != "Save":
            return
        saved = self.tk.EnvUtils.save_autosave_to_original(original)
        if saved:
            self.sb.message_box(f"Saved to <hl>{os.path.basename(saved)}</hl>.")
        else:
            self.sb.message_box("Save failed. See the script output for details.")

    # ------------------------------------------------------------------ Tools: fix
    def b006(self):
        """Cleanup Unknown (Maya): unknown nodes and plugins, legacy XGen expressions."""
        result = self.tk.Diagnostics.cleanup_scene() or {}
        unknown = result.get("unknown") or {}
        nodes = len(unknown.get("nodes") or ())
        plugins = len(unknown.get("plugins") or ())
        xgen = result.get("xgen_removed") or 0
        if not (nodes or plugins or xgen):
            self.sb.message_box("Cleanup Unknown: <hl>nothing to remove</hl>.")
            return
        self.sb.message_box(
            f"Cleanup Unknown: removed <hl>{nodes}</hl> unknown node(s), "
            f"<hl>{plugins}</hl> plugin(s), <hl>{xgen}</hl> XGen expression(s)."
        )

    def b_cleanup(self):
        """Scene Cleanup (Blender): purge orphan datablocks (no users, no fake user)."""
        removed = self.tk.CoreUtils.cleanup_scene()
        if not removed:
            self.sb.message_box("Scene Cleanup: <hl>nothing to purge</hl>.")
            return
        total = sum(removed.values())
        detail = "".join(f"<br> • {coll}: {n}" for coll, n in sorted(removed.items()))
        self.sb.message_box(
            f"Scene Cleanup: purged <hl>{total}</hl> orphan(s).{detail}"
        )

    def b009(self):
        """Fix OCIO (Maya): repair the Color Management / OCIO config preferences."""
        self.tk.Diagnostics.fix_ocio()

    #: Changes Fix Color Spaces lists before it says how many more there were.
    _B011_REPORT_LIMIT = 20

    def b011(self):
        """Fix Color Spaces: each texture's color space by its map type
        (``Diagnostics.fix_missing_color_spaces``), the changes listed."""
        result = self.tk.Diagnostics.fix_missing_color_spaces(force_update=True)
        changes = result.get("changes") or []
        if not changes:
            self.sb.message_box("Fix Color Spaces: <hl>nothing to change</hl>.")
            return
        shown = changes[: self._B011_REPORT_LIMIT]
        detail = "".join(
            f"<br> • {html.escape(str(c.get('node')))}: "
            f"{html.escape(str(c.get('from') or '∅'))} → "
            f"{html.escape(str(c.get('to')))}"
            for c in shown
        )
        if len(changes) > len(shown):
            detail += f"<br> … and {len(changes) - len(shown)} more"
        self.sb.message_box(
            f"Fix Color Spaces: updated <hl>{len(changes)}</hl> texture(s).{detail}"
        )

    def b018(self):
        """Fix Mangled Names (Maya): the selection, or the whole scene when nothing is
        selected."""
        result = self.tk.Diagnostics.repair_mangled_names(
            objects=self.tk.CoreUtils.selected_objects() or None
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

    # ------------------------------------------------------------------ Tools: diagnostics
    def b012(self):
        """Toggle Command Ports (Maya): MEL :7001, Python :7002."""
        is_open, ports = self.tk.MayaConnection.toggle_command_ports()
        port_lines = "".join(
            f"<br> • {port} ({src})" for port, src in ports.items()
        )
        state = "OPENED" if is_open else "CLOSED"
        self.sb.message_box(f"Command Ports <hl>{state}</hl>{port_lines}", timeout=4)
        # Mirror to the console: the ports are what an external editor dials.
        console_lines = ", ".join(f"{p} ({s})" for p, s in ports.items())
        self.sb.logger.log_raw(f"Command Ports {state}: {console_lines}")

    def b017(self):
        """Scene Metadata: the tool-authored data-node channels (``DataNodes.dump``)
        in the shared data viewer, whose Save writes a ``.json`` beside the scene."""
        self.sb.data_view_dialog(
            self.tk.DataNodes.dump(),
            title="Scene Metadata",
            save_path=self.tk.EnvUtils.scene_artifact_path("_scene_metadata.json"),
            empty_message="<hl>No scene metadata</hl> is stored — this scene has no "
            "<b>data_internal</b> / <b>data_export</b> channels yet.",
        )

    #: Extension -> ``ExportVerifier`` input for the files Check GLB / FBX reads.
    CHECK_DELIVERABLE_TYPES = {".glb": "glb", ".fbx": "fbx"}

    def b019(self):
        """Check GLB / FBX: the Scene Exporter's post-write gates over files on disk.

        The ``pythontk.ExportVerifier`` pass the exporter's *Verify The Written File*
        row runs, for a deliverable that already exists. Any number of files; a
        ``.glb`` and ``.fbx`` sharing a stem are checked as one deliverable, and the
        verifier finds each one's scene-data sidecar. Report only.
        """
        picked = self.sb.file_dialog(
            file_types=["*" + ext for ext in self.CHECK_DELIVERABLE_TYPES],
            title="Check GLB / FBX",
            start_dir=self._browse_start(),
            filter_description="Deliverables",
            allow_multiple=True,
        )
        if not picked:
            return
        groups = self._deliverable_groups(
            [picked] if isinstance(picked, str) else picked
        )
        if not groups:
            self.sb.message_box(
                "Pick a <hl>.glb</hl> or <hl>.fbx</hl> deliverable to check."
            )
            return

        results = []
        with self.sb.progress(text="Checking deliverables…") as tick:
            for inputs in groups:
                path = inputs["glb"] or inputs["fbx"]
                tick(text=f"Checking {os.path.basename(path)}…")
                try:
                    verifier = ptk.ExportVerifier(**inputs)
                    results.append((inputs, verifier.sidecar_path, verifier.run()))
                except Exception as error:  # noqa: BLE001 - one bad file never hides the rest
                    results.append((inputs, None, error))

        self.sb.text_view_dialog(
            self._format_deliverable_checks(results),
            "Ok",
            title="Check GLB / FBX",
            size=(820, 560),
            monospace=True,
            word_wrap=True,
        )

    @classmethod
    def _deliverable_groups(cls, paths):
        """``[{"glb": path | None, "fbx": path | None}, ...]`` in pick order: files
        pair by folder + stem; anything that is not a deliverable is dropped."""
        groups = {}
        for path in paths:
            stem, ext = os.path.splitext(path)
            kind = cls.CHECK_DELIVERABLE_TYPES.get(ext.lower())
            if kind:
                groups.setdefault(os.path.normcase(stem), {"glb": None, "fbx": None})[
                    kind
                ] = path
        return list(groups.values())

    @staticmethod
    def _format_deliverable_checks(results):
        """Render ``[(inputs, sidecar, report | exception), ...]`` as report HTML: a
        headline counting the verdicts, then each deliverable's files, the sidecar its
        gates read and the verifier's own summary. A WARN does not fail one."""
        unread = sum(isinstance(r, Exception) for _, _, r in results)
        failed = sum(not isinstance(r, Exception) and not r.ok for _, _, r in results)
        headline = (
            f"{len(results)} deliverable(s) checked: "
            f"{len(results) - failed - unread} passed, {failed} failed"
        )
        if unread:
            headline += f", {unread} could not be checked"

        lines = [headline]
        for inputs, sidecar, report in results:
            files = [p for p in (inputs["glb"], inputs["fbx"]) if p]
            stem = os.path.splitext(os.path.basename(files[0]))[0]
            kinds = " + ".join(os.path.splitext(p)[1].lower() for p in files)
            lines += [
                "",
                f"== {stem}  ({kinds}) ==",
                f"folder:  {os.path.dirname(files[0])}",
            ]
            if isinstance(report, Exception):
                lines.append(f"could not check: {report}")
                continue
            lines.append(
                "sidecar: "
                + (
                    os.path.basename(sidecar)
                    if sidecar
                    else "none found (its gates skip)"
                )
            )
            lines.append(report.summary())
        return "<pre>{}</pre>".format(html.escape("\n".join(lines)))

    # ------------------------------------------------------------------ tb001 Get Scene Info
    #: ``(label, data)`` for the Get Scene Info scope and profile combos.
    _TB001_SCOPES = (
        ("Selected Objects", "selection"),
        ("Entire Scene", "all"),
    )
    _TB001_PROFILES = (
        ("Adaptive (Game Ready)", True),
        ("Generic", False),
    )
    #: Tooltips for the section toggles, per section key. The sections themselves --
    #: keys, labels, render order -- are the host's ``SceneInfoSection``.
    _TB001_SECTION_TIPS = {
        "overview": "The file, units, frame range and a census: meshes and instances "
        "(Blender: linked duplicates), rig, animation, shading, lights, and Maya's "
        "namespaces and unknown nodes / Blender's libraries. Scene-wide, whatever "
        "the scope.",
        "summary": "Totals for the scope: rendered vs unique triangles and "
        "vertices, draw calls, materials, texture memory against its budget.",
        "fix_first": "The prioritized to-do list: missing textures, texture memory, "
        "broken geometry, budgets, meshes without a material, leftover UV snapshots "
        "(Maya), missing libraries (Blender) -- most severe first.",
        "pareto": "The meshes that carry the most rendered triangles (instances "
        "counted), and multi-material meshes by draw calls.",
        "offenders": "Meshes with their own issues -- over-budget triangles, "
        "n-gons, UV sets, slots, oversized unique textures -- worst first.",
        "materials": "Every material in scope: who wears it, its maps, max "
        "resolution and GPU memory, transparency and missing files.",
        "textures": "Texture memory (GPU estimate, uncompressed, on disk), the "
        "resolution histogram and the heaviest maps.",
        "pipeline": "Missing texture files and meshes without a material; Maya's "
        "leftover UV snapshots and unknown nodes and plugins, Blender's missing "
        "libraries.",
        "assumptions": "How the numbers are counted: instances, draw calls, "
        "budgets, texture compression.",
    }

    def tb001_init(self, widget):
        """Get Scene Info -- option box: scope, profile, and one toggle per section."""
        menu = widget.option_box.menu
        menu.setTitle("Get Scene Info")

        cmb_scope = menu.add(
            "QComboBox",
            setObjectName="cmb_scope1",  # NOT cmb_scope -- tb003's scope combo
            setToolTip=(
                "Selected Objects: audit only what is selected — fastest.\n"
                "Entire Scene: audit every mesh in the scene — can take "
                "several seconds on heavy scenes."
            ),
        )
        for label, data in self._TB001_SCOPES:
            cmb_scope.addItem(label, data)

        cmb_profile = menu.add(
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

        menu.add(
            self.sb.registered_widgets.Label,
            setText="Sections:",
            setObjectName="lbl_sections",
            setToolTip="Pick which report sections to query and render.",
        )
        sections = self.tk.SceneInfoSection
        for key in sections.ALL:
            menu.add(
                "QCheckBox",
                # A button's "&" marks its mnemonic: "Notes & Assumptions" would lose
                # the ampersand and bind Alt+Space. "&&" is a literal one.
                setText=sections.LABELS[key].replace("&", "&&"),
                setObjectName=f"chk_section_{key}",
                setChecked=True,
                setToolTip=self._TB001_SECTION_TIPS.get(key, ""),
            )

    def tb001(self, widget):
        """Get Scene Info -- render the sectioned audit report to the viewer dialog."""
        menu = widget.option_box.menu
        scope = menu.cmb_scope1.currentData() or "selection"
        adaptive = menu.cmb_profile.currentData()
        if adaptive is None:
            adaptive = True  # default to game-ready when nothing's picked

        sections = [
            key
            for key in self.tk.SceneInfoSection.ALL
            if getattr(menu, f"chk_section_{key}").isChecked()
        ]
        if not sections:
            self.sb.message_box(
                "<hl>No sections selected</hl>. Tick at least one section in "
                "the option menu."
            )
            return
        # Entire Scene is resolved by the analyzer itself (every mesh INSTANCE). The
        # selection is read whole: Maya's audit resolves a selected object set too.
        if scope != "all" and not self.tk.CoreUtils.selected_objects():
            self.sb.message_box(
                "<hl>Nothing selected</hl>. Select objects, or pick "
                "'Entire Scene' from the option menu."
            )
            return

        # progress_adapter auto-syncs the bar's max from the analyzer's
        # (current, 100, message) callbacks on the first tick.
        with self.sb.progress(text="Working: Get Scene Info") as update:
            html_dict = self.tk.SceneAnalyzer.format_audit_html(
                adaptive=bool(adaptive),
                scope=scope,
                progress_callback=self.sb.progress_adapter(update),
                sections=sections,
            )
        self.sb.text_view_dialog(
            "".join(html_dict.values()),  # always titled: "_header" leads
            "Ok",
            title="Get Scene Info",
            size=(960, 720),
            monospace=False,
            # Object and material names are action:// links; the logger names one
            # deleted or renamed since the report was run.
            link_handler=functools.partial(
                self.tk.UiUtils.dispatch_log_link, logger=self.sb.logger
            ),
        )

    # ------------------------------------------------------------------ tb002 non-orthogonal
    _TB002_SCOPES = (
        ("Selected Objects", "selection"),
        ("Entire Scene", "all"),
    )
    #: Rows rendered in the report before it is truncated -- the cut always stated.
    _TB002_REPORT_LIMIT = 200

    def tb002_init(self, widget):
        """Fix Non-Orthogonal Axes -- option box."""
        menu = widget.option_box.menu
        menu.setTitle("Fix Non-Orthogonal Axes")
        cmb_scope = menu.add(
            "QComboBox",
            # NOT cmb_scope / cmb_scope1 -- the Export (tb003) and Get Scene Info
            # (tb001) scope combos on this same panel.
            setObjectName="cmb_scope2",
            setToolTip=(
                "Selected Objects: check only what is selected.\n"
                "Entire Scene: check every object — this is what FBX export "
                "sees, so use it when chasing the export warning."
            ),
        )
        for label, data in self._TB002_SCOPES:
            cmb_scope.addItem(label, data)
        menu.add(
            "QCheckBox",
            setText="Break Driving Connections",
            setObjectName="chk_break_connections",
            setChecked=False,
            setToolTip=(
                "Objects whose transform is DRIVEN (constraints, animation, "
                "expressions) are skipped by default — the fix and the driver "
                "would fight over the same channels, so there is no accurate "
                "way to keep both.\n"
                "Tick to permanently remove those drivers and fix the objects "
                "anyway. Position-only drivers never block the fix and are "
                "always kept."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Report Only (Dry Run)",
            setObjectName="chk_dry_run",
            setChecked=False,
            setToolTip=(
                "List the offending objects without changing anything.\n"
                "Run this first to see what would be touched."
            ),
        )

    def tb002(self, widget):
        """Fix Non-Orthogonal Axes.

        The FBX plug-in's "Non-orthogonal matrix support" warning fires when an
        object's evaluated axes are not perpendicular -- it carries shear itself, or
        sits under a non-uniformly scaled, rotated ancestor. Both are detected; the
        fix bakes the transform so the object looks identical but exports correctly.
        """
        menu = widget.option_box.menu
        scope = menu.cmb_scope2.currentData() or "selection"
        dry_run = menu.chk_dry_run.isChecked()
        break_connections = menu.chk_break_connections.isChecked()
        diagnostics = self.tk.Diagnostics

        objects = diagnostics.transforms_in_scope(scope)
        if not objects:
            self.sb.message_box(
                "<hl>Empty scene</hl> — nothing to check."
                if scope == "all"
                else "<hl>Nothing selected</hl>. Select objects, or pick "
                "'Entire Scene' from the option menu."
            )
            return

        with self.sb.progress(text="Checking for non-orthogonal axes…") as tick:
            tick()
            found = diagnostics.get_non_orthogonal(objects, detailed=True)

        if not found:
            self.sb.message_box(
                "No <hl>non-orthogonal axes</hl> found — nothing to fix."
            )
            return

        if dry_run:
            self.sb.text_view_dialog(
                self._format_non_orthogonal(found),
                "Ok",
                title="Non-Orthogonal Axes (Report Only)",
                size=(620, 440),
                monospace=True,
                word_wrap=False,
            )
            return

        inherited = sum(1 for i in found.values() if i["cause"] == "inherited")
        driven = sum(1 for i in found.values() if i.get("driven"))
        text = f"<hl>{len(found)}</hl> object(s) have non-orthogonal axes"
        if inherited:
            text += f" ({inherited} inheriting it from a parent)"
        text += f".<br><br>{self.NON_ORTHOGONAL_FIX_EFFECT}"
        if driven:
            text += (
                f"<br><br><hl>{driven}</hl> of them are DRIVEN (constraints/"
                "animation) and will be "
                + (
                    "fixed by removing their drivers."
                    if break_connections
                    else "skipped — enable <hl>Break Driving Connections</hl> "
                    "to include them."
                )
            )
        # message_box buttons must be Qt standard-button names ("Yes", "Cancel" ...):
        # anything else is dropped, leaving a Cancel-only box.
        choice = self.sb.message_box(text + "<br><br>Fix them?", "Yes", "Cancel")
        if choice != "Yes":
            return

        with self.sb.progress(text="Fixing non-orthogonal axes…") as tick:
            tick()
            fixed = diagnostics.fix_non_orthogonal_axes(
                objects, quiet=True, break_connections=break_connections
            )
            tick(text="Verifying…")
            # Re-resolve for the verify: a fix can rename objects (Maya uninstances
            # before freezing), so the pre-fix list may be stale. Selection scope
            # keeps the original list -- the fix may have consumed the selection.
            remaining = diagnostics.get_non_orthogonal(
                diagnostics.transforms_in_scope("all") if scope == "all" else objects
            )

        message = f"Fixed <hl>{len(fixed)}</hl> of <hl>{len(found)}</hl> object(s)."
        if remaining:
            message += (
                f"<br><br><hl>{len(remaining)}</hl> could not be fixed — see "
                "the script output. Driven objects need <hl>Break Driving "
                "Connections</hl> (or bake the animation first); referenced "
                "objects must be fixed in their source file."
            )
        self.sb.message_box(message)

    def _format_non_orthogonal(self, found):
        """Render a ``get_non_orthogonal(detailed=True)`` diagnosis as report HTML.

        Skew is the worst axis-pair cosine: 0 is perpendicular, and the larger it
        gets the further the object is from something FBX can represent.
        """
        rows = sorted(found.items(), key=lambda kv: kv[1]["skew"], reverse=True)
        shown, dropped = (
            rows[: self._TB002_REPORT_LIMIT],
            rows[self._TB002_REPORT_LIMIT :],
        )

        lines = [
            f"{len(found)} object(s) with non-orthogonal axes",
            "",
            f"{'SKEW':<10}{'CAUSE':<12}{'OBJECT':<26}DRIVEN BY",
            f"{'-' * 10}{'-' * 12}{'-' * 26}{'-' * 20}",
        ]
        for obj, info in shown:
            name = getattr(obj, "name", None) or str(obj)
            driven = ", ".join(info.get("driven") or [])
            lines.append(
                f"{info['skew']:<10.5f}{info['cause']:<12}"
                f"{name.split('|')[-1]:<26}{driven}"
            )
        if dropped:
            lines.append(f"... and {len(dropped)} more (report truncated)")
        lines += [
            "",
            "cause 'shear'     - the object carries shear on its own transform",
            "cause 'inherited' - a non-uniformly scaled, rotated ancestor shears it",
            "DRIVEN BY         - the fix skips these unless Break Driving",
            "                    Connections is enabled (drivers and the fix",
            "                    fight over the same channels)",
        ]
        return "<pre>{}</pre>".format(html.escape("\n".join(lines)))


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
