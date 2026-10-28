# !/usr/bin/python
# coding=utf-8
"""Reference Manager: a workspace scene-file manager -- browse a project's scene
files, open / save / rename / delete them, and reference them into the open scene.

One Slots class for both hosts: the ``.ui``'s widgets routed to the panel's
controller (:class:`~tentacle.slots.tools._reference_manager.controller.ReferenceManagerController`),
which composes the host toolkit's ``ReferenceManager`` (``self.tk``). The engine
owns what each host does its own way: what a reference is (Maya: a file reference
under a namespace; Blender: a linked library), which rows are native and which
foreign (baked through the other DCC's bridge before they can be referenced or
opened), how a scene opens, saves, renames and deletes, and the session's project.
"""

from tentacle import Slots
from ._reference_manager.controller import ReferenceManagerController


class ReferenceManagerSlots(Slots):
    """Switchboard slots for the ``reference_manager.ui`` panel."""

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.reference_manager
        # Set while the panel builds: a checkbox's restored state is not a toggle.
        self._initializing = True
        self.controller = ReferenceManagerController(self)
        self.ui.txt000.setText(self.controller.engine.current_working_dir or "")

        # A scene opened anywhere (this panel, the host's File menu) re-lists the
        # table. Deferred a tick: the host fires the event inside its own open.
        mgr = self.tk.ScriptJobManager.instance()
        mgr.subscribe(
            "SceneOpened",
            lambda: self.sb.defer_with_timer(self.controller.refresh_file_list, ms=0),
            owner=self,
        )
        mgr.connect_cleanup(self.ui, owner=self)

        self._setup_footer_actions()
        self.controller.workspaces.update_workspace_footer()
        self._initializing = False

        def _after_build():
            # The selection sync first: the cosmetic column apply must never
            # preempt it if it raises (defer_with_timer logs and swallows).
            self.controller.sync_selection_to_references()
            self.controller.apply_notes_column_visibility()

        self.sb.defer_with_timer(_after_build, ms=100)

    # ------------------------------------------------------------------ wiring helpers
    @staticmethod
    def _rewire_signal(widget, signal, slot, key):
        """Connect *signal* to *slot*, first dropping ONLY this panel's prior
        connection for *key*.

        The widget outlives a slots reload, so a bare ``connect`` would leave the old
        instance bound beside the new one; a blanket ``disconnect()`` would strip the
        widget's own internal connections too (the table's context menu, the item
        delegate's editor lifecycle). The stored ``Connection`` is dropped through the
        static ``QObject.disconnect`` (the signal form warns on a Connection it cannot
        match); a Connection whose receiver was collected is falsy and skipped.
        """
        from qtpy import QtCore

        conns = getattr(widget, "_rm_signal_conns", None)
        if conns is None:
            conns = {}
            widget._rm_signal_conns = conns
        old = conns.get(key)
        if old:
            try:
                QtCore.QObject.disconnect(old)
            except (RuntimeError, TypeError):
                pass
        conns[key] = signal.connect(slot)

    def _setup_footer_actions(self):
        """Build the footer's Un-Reference All and Save To Workspace once (the footer
        persists across a slots reload), then (re)wire them to THIS instance."""
        footer = getattr(self.ui, "footer", None)
        if footer is None or not hasattr(footer, "add_widget"):
            return
        if not getattr(footer, "_rm_actions_built", False):
            footer._rm_actions_built = True
            arrow = self.sb.QtGui.QCursor(self.sb.QtCore.Qt.ArrowCursor)
            height = max(footer.height() - 2, 1)
            # Add order IS the left-to-right order (each lands before the size grip).
            unref_btn = self.sb.QtWidgets.QPushButton("Un-Reference All", footer)
            unref_btn.setToolTip("Remove every reference from the scene.")
            unref_btn.setCursor(arrow)
            unref_btn.setFixedHeight(height)
            footer.add_widget(unref_btn, side="right", background=True)
            footer._rm_unref_btn = unref_btn
            save_btn = self.sb.QtWidgets.QPushButton("Save To Workspace", footer)
            save_btn.setObjectName("btn_save_footer")
            save_btn.setCursor(arrow)
            save_btn.setFixedHeight(height)
            # Static fallback: the live tooltip below previews the exact path.
            save_btn.setToolTip(
                "Save the current scene into the workspace using the header menu's "
                "Naming options."
            )
            footer.add_widget(save_btn, side="right", background=True)
            footer._rm_save_btn = save_btn
        save_btn = getattr(footer, "_rm_save_btn", None)
        if save_btn is not None:
            self._rewire_signal(
                save_btn,
                save_btn.clicked,
                self.controller.files.save_to_workspace,
                "save",
            )
            self.sb.tooltip.bind(save_btn, self.controller.files.save_scene_preview)
        unref_btn = getattr(footer, "_rm_unref_btn", None)
        if unref_btn is not None:
            self._rewire_signal(
                unref_btn,
                unref_btn.clicked,
                self.controller.references.unreference_all,
                "unref",
            )

    # ------------------------------------------------------------------ header
    def header_init(self, widget):
        """Header buttons, the Naming / Filter-Display / Foreign Scenes / Include
        Types / Operations menu, and the help text."""
        # Runs on every call: the header outlives a slots reload, so its buttons and
        # the signals below are re-targeted at THIS instance each time.
        widget.config_buttons("refresh", "menu", "collapse", "pin")
        # Tap-to-pin: releasing the marking-menu key right after the panel opens pins
        # it -- the user came here to work. Holding it still auto-hides on release.
        widget.pin_on_tap = True
        self._rewire_signal(
            widget,
            widget.refresh_requested,
            lambda *_: self.controller.refresh_file_list(invalidate=True),
            "hdr_refresh",
        )
        if widget.is_initialized:
            self._wire_header_menu(widget.menu)
            return
        menu = widget.menu
        # Save / load the naming + filter settings as named presets.
        menu.add_presets = True
        menu.presets.preset_dir = self.controller.engine.PRESET_DIR

        # Naming: panel-wide. Save applies all three; Rename applies case + suffix and
        # moves a {name} folder; Delete removes an emptied {name} folder; the filters
        # below match against suffix + folder structure.
        menu.add("Separator", setTitle="Naming:")
        menu.add(
            "QComboBox",
            setObjectName="cmb_case_style",
            setToolTip="Case convention applied to the file name on Save and Rename.",
            addItems=list(self.controller.CASE_STYLES),
        )
        menu.add(
            "QLineEdit",
            setObjectName="txt_suffix",
            setPlaceholderText="Suffix (e.g. _v01)…",
            setToolTip="Suffix appended to the file name on Save and Rename (excluded "
            "from case formatting) — also what Filter by Suffix and Hide Suffix match.",
        )
        menu.add(
            "QLineEdit",
            setObjectName="txt_subfolder_structure",
            setText="{scenes}",
            setPlaceholderText="Folder Structure (e.g. {scenes}/{name})…",
        )

        menu.add("Separator", setTitle="Filter / Display:")
        for name, text, tip in (
            (
                "chk_filter_suffix",
                "Filter by Suffix",
                "Show only files whose name ends with the Suffix above.",
            ),
            (
                "chk_filter_folder_structure",
                "Filter by Folder Structure",
                "Show only files whose location matches the Folder Structure above.",
            ),
            (
                "chk_hide_suffix",
                "Hide Suffix",
                "Hide the suffix from the displayed file name.",
            ),
            (
                "chk_hide_extension",
                "Hide Extension",
                "Hide the file extension from the displayed file name.",
            ),
            (
                "chk_show_notes_column",
                "Show Notes Column",
                "Show the Notes column (per-file comments). Hidden by default.",
            ),
        ):
            menu.add(
                "QCheckBox",
                setText=text,
                setObjectName=name,
                setChecked=False,
                setToolTip=tip,
            )

        # Foreign-scene conversion route. FBX (default): instancing is native to the
        # format on both sides, so shared geometry survives with no sidecar replay. USD:
        # richer materials plus native animation, but instances are rebuilt from the
        # conversion sidecar. Item order is APPEND-ONLY (the combo saves its index); the
        # default moves via setCurrentIndex, which must follow addItems.
        menu.add("Separator", setTitle="Foreign Scenes:")
        menu.add(
            "QComboBox",
            addItems=["Convert via USD", "Convert via FBX"],
            setCurrentIndex=1,  # FBX
            setObjectName="cmb_conversion_route",
            setToolTip=(
                "Intermediate used when opening / importing / referencing a foreign "
                "scene.\n"
                "FBX (default): instancing is carried by the format itself, so a "
                "scene keeps its shared geometry without a rebuild step.\n"
                "USD: richer materials, plus animation arrives natively — but "
                "instances are rebuilt from a sidecar. Prefer it for look-heavy "
                "scenes, and check instancing survived."
            ),
        )
        # No Rig setting: how a scene's rig logic travels is asked per scene, and only
        # when it has some (controller.resolve_rig_mode).

        # Include Types: one horizontal row of per-type toggles. The host's own scene
        # types list by default; a foreign row bakes before it is referenced.
        menu.add_row(
            [
                (
                    "QCheckBox",
                    {
                        "setObjectName": f"chk_include_{t}",
                        "setText": t,
                        "setChecked": self.controller.include_type_checked_by_default(
                            t
                        ),
                        "setToolTip": self.controller.include_type_tooltip(t),
                    },
                )
                for t in self.controller.INCLUDE_TYPES
            ],
            title="Include Types:",
            justify="expand",
        )

        menu.add("Separator", setTitle="Operations:")
        # Scene assemblies are Maya's: a host without them (Blender) builds no button.
        if getattr(self.tk, "AssemblyManager", None) is not None:
            menu.add(
                "QPushButton",
                setText="Convert to Assembly",
                setObjectName="btn_convert_assembly",
                setToolTip="Replace every reference with an assembly-definition "
                "representation.",
            )
        menu.add(
            "QPushButton",
            setText="Unlink and Import All",
            setObjectName="btn_unlink_import_all",
            setToolTip="Import every reference's contents as local data (removes the "
            "reference links). In Maya, the button beside it cycles the namespace "
            "handling.",
        )
        self.controller.references.add_unlink_namespace_action(
            menu.btn_unlink_import_all
        )
        # Un-Reference All lives on the footer only (_setup_footer_actions).
        self._wire_header_menu(menu)
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Reference Manager",
                body="A workspace scene-file manager: browse a project's scene files, "
                "open / save / rename / delete them, and reference them into the "
                "current scene (Blender: linked libraries).",
                steps=[
                    "Set a <b>Root Directory</b> (▸ to browse / recent); pick a <b>Workspace</b>.",
                    "Click the row's <b>reference</b> icon to reference / un-reference, the "
                    "<b>open</b> icon to open the scene, the <b>display</b> icon to cycle "
                    "Normal → Reference → Template. Selecting rows references them too.",
                    "<b>Double-click</b> the name to rename; right-click for the full action menu.",
                    "<b>Double-click</b> the <b>Notes</b> column to annotate a file (saved with the project).",
                ],
                sections=[
                    (
                        "Footer",
                        [
                            "<b>Un-Reference All</b> removes every reference from the scene.",
                            "<b>Save To Workspace</b> saves the current scene into the "
                            "workspace using the <b>Naming</b> options; hovering the "
                            "button previews the exact path it would write.",
                        ],
                    ),
                    (
                        "Header menu",
                        [
                            "<b>Naming</b> (case / suffix / folder structure) is "
                            "panel-wide: Save and Rename apply it, and the filters "
                            "below match against it.",
                            "<b>Filter by Suffix / Folder Structure</b> narrow the list; "
                            "<b>Hide Suffix / Extension</b> shorten the displayed name; "
                            "<b>Show Notes Column</b> reveals Notes.",
                            "<b>Include Types</b> (ma / mb / fbx / usd / blend) picks which "
                            "file types list. The host's own types reference natively; a "
                            "foreign row's reference icon bakes it to a cached scene and "
                            "references that — right-click <b>Unlink and Import</b> for a "
                            "local copy instead.",
                            "<b>Operations</b>: <b>Unlink and Import All</b> (Maya: and "
                            "<b>Convert to Assembly</b>; the button beside Unlink cycles "
                            "what an unlink does with the namespace).",
                        ],
                    ),
                    (
                        "Root Directory (▸ option box)",
                        [
                            "Browse / recent folders; <b>Open Directory</b>; <b>Set To "
                            "Current Workspace</b>; <b>Recursive Search</b>; <b>Ignore Empty "
                            "Workspaces</b>; <b>New Workspace</b> / <b>Mark As Workspace</b> "
                            "(a workspace.mel project both Maya and Blender read).",
                        ],
                    ),
                    (
                        "Filter field (▸ option box)",
                        [
                            "Toggle the filter on/off; <b>Ignore Case</b>; choose what it "
                            "matches — <b>Files</b>, <b>Notes</b>, or both.",
                        ],
                    ),
                ],
                notes=[
                    "<b>Right-click</b> a file row for its actions (open, rename, "
                    "delete, copy path, reveal, …).",
                    "The <b>Workspaces</b> field's ▸ action sets the session's project "
                    "to the selected workspace (opening a scene from the list does it "
                    "automatically).",
                ],
            )
        )

    def _wire_header_menu(self, menu):
        """(Re)wire the header menu's live parts to THIS instance: each Include Types
        toggle re-filters, and the Folder Structure field shows its live preview."""
        for t in self.controller.INCLUDE_TYPES:
            chk = getattr(menu, f"chk_include_{t}", None)
            if chk is not None:
                self._rewire_signal(
                    chk,
                    chk.toggled,
                    lambda *_: self.controller.refresh_file_list(),
                    f"include_{t}",
                )
        self.controller.files.wire_structure_tooltip(menu)

    # ------------------------------------------------------------------ table
    def tbl000_init(self, widget):
        """Table setup: the one-time construction, then the signals re-wired to this
        instance every time (the table outlives a slots reload), then -- when it was
        already built -- a refresh (the table re-inits on every show).

        The construction MUST precede the wiring: ``actions.add`` sizes its column,
        and Qt 6.5's ``setSectionResizeMode`` on a section not yet created is a native
        access violation.
        """
        built = widget.is_initialized
        if not built:
            widget.is_initialized = True
            widget.refresh_on_show = True
            widget.setColumnCount(5)
            widget.setHorizontalHeaderLabels(["FILES:", "", "", "", "NOTES:"])
            # FILES (and NOTES, when shown) stretch; the three icon columns keep the
            # fixed squares TableActions gives them. moveSection is visual-only: every
            # logical column index stays valid.
            header = widget.horizontalHeader()
            QHeaderView = self.sb.QtWidgets.QHeaderView
            header.setStretchLastSection(False)
            header.setSectionResizeMode(self.controller.COL_NAME, QHeaderView.Stretch)
            header.setSectionResizeMode(self.controller.COL_NOTES, QHeaderView.Stretch)
            for visual, logical in enumerate(self.controller.VISUAL_COLUMN_ORDER):
                header.moveSection(header.visualIndex(logical), visual)
            # Editing is started by hand (double-click), never by Qt's own triggers.
            QAbstractItemView = self.sb.QtWidgets.QAbstractItemView
            widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
            widget.setSelectionBehavior(QAbstractItemView.SelectRows)
            # The selection IS the reference set: a click toggles one row without
            # dropping the others.
            widget.setSelectionMode(QAbstractItemView.MultiSelection)
            widget.setSortingEnabled(True)
            widget.verticalHeader().setVisible(False)
            for name, text, tip in (
                (
                    "btn_open_scene",
                    "Open",
                    "Open this scene file — reads it back from disk when it is already\n"
                    "the open scene (the action reads 'Reopen' then).",
                ),
                ("btn_rename_scene", "Rename", "Rename this scene file."),
                ("btn_delete_scene", "Delete", "Delete this scene file."),
                (
                    "btn_toggle_reference",
                    "Reference / Unreference",
                    "Toggle the reference state of this scene.",
                ),
                (
                    "btn_unlink_import",
                    "Unlink and Import",
                    "Make an active reference's data local, or, for a foreign row,\n"
                    "convert + import its contents (a USD row with no reference imports\n"
                    "directly).",
                ),
                (
                    "btn_open_file_location",
                    "Open File Location",
                    "Open the containing folder in the file explorer.",
                ),
                (
                    "btn_copy_path",
                    "Copy Path",
                    "Copy the file's full path to the clipboard.",
                ),
            ):
                widget.menu.add(
                    "QPushButton", setText=text, setObjectName=name, setToolTip=tip
                )
        self._wire_table_signals(widget)
        if built and self.ui.cmb000.count():
            self.controller.refresh_file_list()

    def _wire_table_signals(self, widget):
        """(Re)wire the table's icon columns and signals to this instance (idempotent:
        ``actions.add`` overwrites by column, the signals re-wire precisely)."""
        c = self.controller
        current_clr = widget.ACTION_COLOR_MAP["current"][0]
        widget.actions.add(
            c.COL_REF,
            states={
                "unreferenced": {
                    "icon": "link",
                    "color": "#555555",
                    "tooltip": "Not referenced — click to add reference",
                    "action": c.references.toggle_reference_at_row,
                },
                "referenced": {
                    "icon": "link",
                    "color": "#6b8fa3",
                    "tooltip": "Referenced — click to remove reference",
                    "action": c.references.toggle_reference_at_row,
                },
            },
        )
        widget.actions.add(
            c.COL_OPEN,
            states={
                "default": {
                    "icon": "open_external",
                    "color": "#555555",
                    "tooltip": "Open Scene",
                    "action": c.files.open_scene_at_row,
                },
                "current": {
                    "icon": "open_external",
                    "color": current_clr,
                    "tooltip": "Current Scene",
                    "action": c.files.open_scene_at_row,
                },
            },
        )
        widget.actions.add(
            c.COL_DISPLAY,
            states={
                "off": {
                    "icon": "grid",
                    "color": "#555555",
                    "tooltip": "Display: Normal — click to lock (Reference)",
                    "action": c.references.cycle_display_mode_at_row,
                },
                "reference": {
                    "icon": "lock",
                    "color": "#d4a84a",
                    "tooltip": "Display: Reference (locked, normal shading) — click for "
                    "Template (wireframe + locked)",
                    "action": c.references.cycle_display_mode_at_row,
                },
                "template": {
                    "icon": "grid",
                    "color": "#6b8fa3",
                    "tooltip": "Display: Template (wireframe + locked) — click to restore Normal",
                    "action": c.references.cycle_display_mode_at_row,
                },
                "unavailable": {
                    "icon": "grid",
                    "color": "#3a3a3a",
                    "tooltip": "Display overrides are only available for active references",
                },
            },
        )
        for key, signal, slot in (
            ("dbl", widget.itemDoubleClicked, c.item_double_clicked),
            ("sel", widget.itemSelectionChanged, c.handle_item_selection),
            # The right-clicked row: the menu's actions act on it, not the selection.
            ("ctx", widget.customContextMenuRequested, c.capture_context_row),
            ("chg", widget.itemChanged, c.item_changed),
            ("editor", widget.itemDelegate().closeEditor, c.editor_closed),
        ):
            self._rewire_signal(widget, signal, slot, key)

    # The row context menu (objectNames are the switchboard's auto-wired slots).
    def btn_open_scene(self):
        """Open the right-clicked row's scene (a reopen on the open scene's row)."""
        path = self.controller.row_path(self.controller.context_row())
        if not path:
            self.sb.message_box("No scene selected.")
            return
        self.controller.files.open_path(path)

    def btn_rename_scene(self):
        """Rename the right-clicked row's scene."""
        self.controller.files.rename_scene()

    def btn_delete_scene(self):
        """Delete the right-clicked row's scene."""
        self.controller.files.delete_scene()

    def btn_toggle_reference(self):
        """Reference / unreference the right-clicked row."""
        row = self.controller.context_row()
        if row is not None:
            self.controller.references.toggle_reference_at_row(row)

    def btn_unlink_import(self):
        """Unlink and import the right-clicked row (make it local / import it)."""
        self.controller.references.unlink_import_row()

    def btn_open_file_location(self):
        """Reveal the right-clicked row's file."""
        self.controller.files.open_file_location()

    def btn_copy_path(self):
        """Copy the right-clicked row's full path."""
        self.controller.files.copy_path()

    # ------------------------------------------------------------------ root directory
    def txt000_init(self, widget):
        """Root Directory: recent-folder pins, the browse / open / workspace actions
        and the scan options in its option box."""
        if not widget.is_initialized:
            # One settings key on both hosts: uitk host-namespaces it ("..._maya",
            # "..._blender"), so each keeps its own list.
            widget.option_box.pin(
                settings_key="reference_manager_directories",
                single_click_restore=True,
            )
            # The directory picker, fired by the b000 "Set Directory…" item.
            self._browse_option = self.sb.BrowseOption(
                wrapped_widget=widget,
                mode="directory",
                title="Select a root directory",
                start_dir=lambda: self.controller.engine.current_workspace,
            )
            box_menu = widget.option_box.menu
            for kind, kwargs in (
                (
                    "QPushButton",
                    dict(
                        setText="Set Directory…",
                        setObjectName="b000",
                        setToolTip="Browse for a root directory.",
                    ),
                ),
                (
                    "QPushButton",
                    dict(
                        setText="Open Directory",
                        setObjectName="b006",
                        setToolTip="Open the root directory in the file explorer.",
                    ),
                ),
                (
                    "QPushButton",
                    dict(
                        setText="Set To Current Workspace",
                        setObjectName="b001",
                        setToolTip="Set the root directory to the session's current workspace.",
                    ),
                ),
                (
                    "QCheckBox",
                    dict(
                        setText="Recursive Search",
                        setObjectName="chk000",
                        setChecked=True,
                        setToolTip="Also search sub-folders for workspaces.",
                    ),
                ),
                (
                    "QCheckBox",
                    dict(
                        setText="Ignore Empty Workspaces",
                        setObjectName="chk003",
                        setChecked=True,
                        setToolTip="Skip workspaces that contain no scene files.",
                    ),
                ),
                (
                    "QPushButton",
                    dict(
                        setText="New Workspace…",
                        setObjectName="btn_new_workspace",
                        setToolTip="Create a project workspace under the root: a workspace.mel\n"
                        "(a project both Maya and Blender read) plus the standard subfolders.",
                    ),
                ),
                (
                    "QPushButton",
                    dict(
                        setText="Mark As Workspace",
                        setObjectName="btn_mark_workspace",
                        setToolTip="Write a workspace.mel describing the selected workspace\n"
                        "folder's existing layout (no files are moved).",
                    ),
                ),
            ):
                box_menu.add(kind, **kwargs)
            widget.set_validator(
                "dir", debounce_ms=500, invalid_tooltip="Invalid directory"
            )
            widget.validated.connect(
                lambda _ok, text: self.controller.workspaces.update_current_dir(text)
            )
        self.controller.workspaces.update_current_dir()

    def b000(self):
        """Browse for a root directory."""
        self._browse_option.browse()

    def b006(self):
        """Open the root directory in the file explorer."""
        self.controller.workspaces.open_root_dir()

    def b001(self):
        """Set the root directory to the session's current workspace."""
        self.controller.workspaces.set_root_to_current()

    def btn_new_workspace(self):
        """Create a workspace under the root."""
        self.controller.workspaces.new_workspace()

    def btn_mark_workspace(self):
        """Mark the selected workspace folder as a project."""
        self.controller.workspaces.mark_workspace()

    @staticmethod
    def _as_bool(checked) -> bool:
        """A checkbox signal's state as a bool (``Qt.Checked`` is 2)."""
        return (
            checked == 2
            if isinstance(checked, int) and not isinstance(checked, bool)
            else bool(checked)
        )

    def chk000(self, checked):
        """Recursive Search: rescan the root's workspaces."""
        if self._initializing or self.controller.workspaces.updating_directory:
            return
        value = self._as_bool(checked)
        if self.controller.engine.recursive_search == value:
            return
        self.controller.engine.recursive_search = value
        self.controller.workspaces.update_workspace_combo()

    def chk003(self, checked):
        """Ignore Empty Workspaces: rescan the root's workspaces."""
        if self._initializing or self.controller.workspaces.updating_directory:
            return
        value = self._as_bool(checked)
        if self.controller.engine.ignore_empty_workspaces == value:
            return
        self.controller.engine.ignore_empty_workspaces = value
        self.controller.workspaces.update_workspace_combo()

    # ------------------------------------------------------------------ workspaces
    def cmb000_init(self, widget):
        """Workspaces: its ▸ action sets the session's project to the selection (on
        every init: ``set_action`` replaces the prior action, re-targeting it at this
        instance), then the combo fills from the root."""
        widget.option_box.set_action(
            callback=self.controller.workspaces.set_project,
            icon="home",
            tooltip="Set the session's project to the selected workspace.\n"
            "Opening a scene from the list sets it automatically; this "
            "applies it without opening anything.",
        )
        self.controller.workspaces.update_workspace_combo()

    def cmb000(self, index, widget):
        """Browse the selected workspace."""
        if index == -1 or self.controller.workspaces.updating_directory:
            return
        path = widget.itemData(index)
        if path:
            self.controller.workspaces.set_workspace(path, invalidate=False)

    # ------------------------------------------------------------------ filter
    def txt001_init(self, widget):
        """Filter: an on/off toggle (persisted), Ignore Case and what it matches."""
        if not widget.is_initialized:
            widget.option_box.clear_option = True
            widget.option_box.set_toggle(
                icon="filter",
                tooltip_on="Filter enabled. Click to disable.",
                tooltip_off="Filter disabled. Click to enable.",
                initial=self.controller.filter_enabled,
                gate_wrapped=True,  # grey out the field while the filter is off
                on_toggled=self._toggle_filter,
                settings_key="reference_manager_filter",
            )
            # The restored toggle state, before the first listing reads it.
            toggle = widget.option_box.find_option(self.sb.ToggleOption)
            if toggle is not None:
                self.controller.filter_enabled = toggle.is_on
            widget.option_box.menu.add(
                "QCheckBox",
                setText="Ignore Case",
                setObjectName="chk_ignore_case",
                setChecked=True,
                setToolTip="Ignore case when filtering.",
            )
            widget.option_box.menu.add(
                "QComboBox",
                setObjectName="cmb_filter_target",
                setToolTip="Choose what the filter text matches against.",
                addItems=["Filter: All", "Filter: Files", "Filter: Notes"],
            )

    def txt001(self, text):
        """Filter the list by the typed text."""
        self.controller.filter_text = (text or "").strip()
        self.controller.refresh_file_list(invalidate=False)

    def _toggle_filter(self, enabled):
        self.controller.filter_enabled = bool(enabled)
        self.controller.refresh_file_list(invalidate=False)

    def chk_ignore_case(self, checked):
        """Re-filter."""
        self.controller.refresh_file_list(invalidate=False)

    def cmb_filter_target(self, index, widget=None):
        """Re-filter."""
        self.controller.refresh_file_list(invalidate=False)

    # ------------------------------------------------------------------ header menu
    def chk_filter_suffix(self, checked):
        """Re-filter."""
        self.controller.refresh_file_list(invalidate=False)

    def chk_filter_folder_structure(self, checked):
        """Re-filter."""
        self.controller.refresh_file_list(invalidate=False)

    def chk_hide_suffix(self, checked):
        """Re-label."""
        self.controller.refresh_file_list(invalidate=False)

    def chk_hide_extension(self, checked):
        """Re-label."""
        self.controller.refresh_file_list(invalidate=False)

    def chk_show_notes_column(self, checked):
        """Show / hide the Notes column."""
        self.controller.apply_notes_column_visibility()

    def txt_suffix(self, text):
        """Re-filter when a filter reads the suffix."""
        self.controller.refilter_on_naming_change()

    def txt_subfolder_structure(self, text):
        """Re-filter when a filter reads the folder structure."""
        self.controller.refilter_on_naming_change()

    def btn_convert_assembly(self):
        """Convert every reference to an assembly (Maya)."""
        self.controller.references.convert_to_assembly()

    def btn_unlink_import_all(self):
        """Unlink and import every reference."""
        self.controller.references.unlink_all()
