# !/usr/bin/python
# coding=utf-8
"""Workspace Editor: the minimal take on Maya's File ▸ Project Window -- one
project-root field, one file-rules table, and rule edits that write through to
``workspace.mel`` at once (no Accept step).

A Blender tool (``tentacle.slots.tools.HOSTS``): Blender has no project system,
so this panel is its project window, while Maya's own Project Window is Maya's
(the Workspace tab's Edit Workspace row opens each host's; Maya users are never
offered a second one).

- **Project Root**: a single path field. Browsing to or typing an existing
  workspace loads its rules and makes it the current workspace; a fresh path
  shows the active template, and the project (marker + folders) is created, and
  made current, by **Create Project** or by the first rule edit. Option-box
  icons: browse, and open in the file browser.
- **Rule table**: RULE ▸ LOCATION plus per-row icons (reset the rule to its
  template default, remove it). Every committed edit, add, remove, reset or
  template load saves at once (merge-preserving: hand-written ``workspace.mel``
  lines survive; removed rows are deleted).
- **Nice Names ↔ File Rules** (Maya's Edit ▸ View toggle, header menu): rows show
  Maya's Project Window labels (``ptk.RULE_NICE_NAMES``, same order) or the raw
  rule keys; the raw view makes the rule column editable.
- **Templates** (header menu): uitk's ``PresetManager`` combo over
  ``ptk.WorkspaceTemplates``, the store both hosts read, so a template saved
  here is what ``create_workspace`` builds a Maya project from too. The ACTIVE
  template is what every new workspace is built from.

The workspace model is pythontk's (``ptk.Workspace``); the current workspace and
the template rules are the host toolkit's ``EnvUtils`` (``self.tk``).
"""

import os

import pythontk as ptk
from qtpy import QtCore, QtWidgets

from tentacle import Slots


class WorkspaceEditorSlots(Slots, ptk.LoggingMixin):
    #: How long the root field waits after a keystroke before it retargets (ms).
    ROOT_SETTLE_MS = 500

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("WARNING")
        self.logger.set_log_prefix("[workspace_editor] ")
        self.ui = self.sb.loaded_ui.workspace_editor
        self._loaded_rules = {}  # rules as last written/read: the removal-diff baseline
        self._nice_view = True  # Maya's default: View in Nice names
        self._updating = False  # suppress write-through during programmatic populates
        self._preset_mgr = None  # uitk PresetManager over the workspace-template store
        self._root_gen = 0  # root-field debounce generation (see _on_root_changed)

    # ------------------------------------------------------------------ header
    def header_init(self, widget):
        """Rule add, view toggle, reset/clear, template combo, help text."""
        widget.config_buttons("refresh", "menu", "collapse", "hide")
        widget.refresh_requested.connect(self._load)
        widget.menu.add("Separator", setTitle="Project:")
        widget.menu.add(
            "QPushButton",
            setText="Create Project",
            setObjectName="btn_create",
            setToolTip="Build the project at the current root now: marker + the active\n"
            "template's rule folders (Maya's File ▸ Project Window ▸ New). Editing\n"
            "any rule does this implicitly; this is the explicit verb.",
        ).clicked.connect(self.create_project)
        widget.menu.add("Separator", setTitle="File Rules:")
        widget.menu.add(
            "QPushButton",
            setText="Add New File Rule",
            setObjectName="btn_add_rule",
            setToolTip="Append an empty rule row (Maya's Custom Data Locations ▸ Add new\n"
            "file rule); it saves once both cells are filled in. Added in Nice Names\n"
            "view, a known label (e.g. 'Render Data') resolves to its rule key.",
        ).clicked.connect(self.add_rule)
        widget.menu.add(
            "QCheckBox",
            setText="View File Rules",
            setObjectName="chk_raw_names",
            setChecked=False,
            setToolTip="Show raw file-rule keys instead of nice names, and make the rule\n"
            "column editable (Maya's Edit ▸ View in File Rules).",
        ).toggled.connect(self._on_view_toggled)
        widget.menu.add("Separator", setTitle="Edit:")
        widget.menu.add(
            "QPushButton",
            setText="Reset Settings",
            setObjectName="btn_reset",
            setToolTip="Restore the default file rules (the active template's) and save\n"
            "(Maya's Edit ▸ Reset Settings, applied immediately).",
        ).clicked.connect(self.reset_rules)
        widget.menu.add(
            "QPushButton",
            setText="Clear Settings",
            setObjectName="btn_clear",
            setToolTip="Remove every file rule from the project and save (Maya's Edit ▸\n"
            "Clear Settings, applied immediately; hand-written lines survive).",
        ).clicked.connect(self.clear_rules)
        widget.menu.add("Separator", setTitle="Templates:")
        combo = widget.menu.add(
            self.sb.ComboBox,
            setObjectName="cmb_template",
            setToolTip="Workspace templates: picking one loads its rules into the project\n"
            "and makes it the ACTIVE default every new workspace is built from\n"
            "(here and in Maya). Icons save the current rules as a template;\n"
            "the menu renames/deletes.",
        )
        self._preset_mgr = self.sb.PresetManager(
            preset_dir=str(ptk.WorkspaceTemplates.store().user_dir),
            value_provider=self._gather,
            value_applier=self._apply_template,
        )
        self._preset_mgr.wire_combo(combo, placeholder="Templates…")
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Workspace Editor (Project Window)",
                body="Define a shared Maya/Blender project workspace, the mirror of "
                "Maya's File ▸ Project Window. File rules map a location (Scenes, "
                "Source Images, …) to a folder; both applications resolve through "
                "the rules, never through hardcoded folder names. Edits save to "
                "workspace.mel immediately: there is no Accept step.",
                steps=[
                    "Set the <b>Project Root</b> (▸ browses; an existing workspace "
                    "loads its rules and becomes the current workspace, a fresh path "
                    "shows the active template).",
                    "<b>Create Project</b> (header menu) builds it: marker + rule "
                    "folders. Editing any rule on a fresh path does the same "
                    "implicitly.",
                    "Edit the rule table (<b>double-click</b> a location cell; the row "
                    "icons reset a rule to its template default or remove it).",
                    "The header menu adds rules, toggles Nice Names ↔ File Rules, "
                    "and resets/clears the rules.",
                    "The <b>Templates</b> combo saves/loads named rule sets; the "
                    "active one defines how every new workspace is built, in "
                    "<i>both</i> applications (Maya reads the same store).",
                ],
            )
        )

    # ------------------------------------------------------------------ fields
    @staticmethod
    def _rewire(widget, signal_name, handler):
        """Bind *handler* to ``widget.<signal_name>`` as its only subscriber.

        These widgets outlive this Slots instance (a UI reload leaves
        ``is_initialized`` stamped on the persisted QWidget), so the connects run
        on EVERY ``_init`` or a rebuilt panel's edits stay bound to a dead
        ``self`` and silently do nothing.

        The previous handler is remembered ON THE WIDGET, not looked up from
        ``self``: the binding to drop belongs to the *old* instance, which
        ``signal.disconnect(self.<method>)`` would never match. Tracking it by
        reference also avoids the blanket ``disconnect()`` that makes PySide warn
        against a signal with nothing attached (every first call).
        """
        conns = getattr(widget, "_ws_editor_conns", None)
        if conns is None:
            conns = {}
            widget._ws_editor_conns = conns
        signal = getattr(widget, signal_name)
        previous = conns.get(signal_name)
        if previous is not None:
            try:
                signal.disconnect(previous)
            except (RuntimeError, TypeError):
                pass  # already gone with the old instance
        signal.connect(handler)
        conns[signal_name] = handler

    def txt000_init(self, widget):
        """Project Root: one full path (browse + open-folder option-box actions)."""
        if not getattr(widget, "is_initialized", False):
            widget.refresh_on_show = True
            widget.option_box.browse(
                mode="directory",
                title="Select Project Root",
                tooltip="Browse for the project root folder (an existing workspace\n"
                "loads its rules).",
            )
            widget.option_box.add_action(
                callback=self.open_folder,
                icon="open_external",
                tooltip="Open the project root in the system file browser.",
            )
        last = self.ui.settings.value("workspace_root") or ""
        ws = self.tk.EnvUtils.current_workspace()
        if ws is not None:
            last = ws.root
        if last and not widget.text():
            widget.setText(last)
        # Debounced, not per-keystroke: retargeting reloads the rule table AND makes
        # the path the current workspace, so a raw textChanged would do both for
        # every partial path that happens to exist while the user types. Enter
        # commits immediately. (textChanged rather than editingFinished because the
        # browse action sets the text programmatically, which emits only the former.)
        self._rewire(widget, "textChanged", self._on_root_changed)
        self._rewire(widget, "returnPressed", self._on_root_committed)

    def tbl000_init(self, widget):
        if not getattr(widget, "is_initialized", False):
            widget.refresh_on_show = True
            widget.actions.add(
                column=2,
                states={
                    "reset": {
                        "icon": "undo",
                        "tooltip": "Reset this rule to its template default.",
                        "action": lambda row, col: self.reset_row(row),
                    }
                },
            )
            widget.actions.add(
                column=3,
                states={
                    "remove": {
                        "icon": "trash",
                        "tooltip": "Remove this rule (deleted from workspace.mel).",
                        "action": lambda row, col: self.remove_row(row),
                    }
                },
            )
        self._rewire(widget, "itemChanged", self._on_item_changed)
        self._load()

    # ------------------------------------------------------------------ root resolution
    def _root(self):
        """The project root path ('' when unset)."""
        widget = getattr(self.ui, "txt000", None)
        return widget.text().strip() if widget is not None else ""

    def _on_root_changed(self, _text=None):
        """Root-field edit: retarget once the typing settles.

        A real debounce, not a plain defer: ``defer_with_timer`` is a
        ``QTimer.singleShot``, so every keystroke would still fire its own
        deferred call, one per partial path for anyone typing slower than the
        delay. The generation stamp lets all but the last one do nothing.
        """
        self._root_gen += 1
        gen = self._root_gen
        self.sb.defer_with_timer(lambda: self._on_root_settled(gen), ms=self.ROOT_SETTLE_MS)

    def _on_root_settled(self, gen):
        if gen == self._root_gen:  # nothing typed since: this edit is the final one
            self._on_root_committed()

    def _on_root_committed(self):
        """A committed root path (Enter / browse / settled typing) retargets the panel."""
        self._root_gen += 1  # Enter supersedes any debounce still in flight
        path = self._root()
        self.ui.settings.setValue("workspace_root", path)
        ws = ptk.Workspace.load(path) if path else None
        if ws is not None and ws.is_marked:
            self._load()
            self._set_current(path)  # selecting an existing project root makes it current
        elif self._loaded_rules or not path:
            # Retargeted from an existing project to an unbuilt path: show a fresh
            # template-seeded definition (nothing written until a rule is edited).
            self._loaded_rules = {}
            self._populate(self.tk.EnvUtils.workspace_template_rules())

    def _set_current(self, root):
        """Make *root* the session's current workspace: done when a project root is
        selected or first built here (Maya's Set Project analogue), so the panel
        needs no explicit button."""
        if root and os.path.isdir(root):
            self.tk.EnvUtils.set_current_workspace(root)

    # ------------------------------------------------------------------ table
    def _load(self):
        """(Re)load the rule table from the project's workspace.mel, or the active
        template for a project that is not built yet."""
        table = getattr(self.ui, "tbl000", None)
        if table is None:
            return
        root = self._root()
        ws = ptk.Workspace.load(root) if root else None
        self._loaded_rules = dict(ws.rules) if ws is not None and ws.is_marked else {}
        self._populate(self._loaded_rules or self.tk.EnvUtils.workspace_template_rules())

    @staticmethod
    def _ordered(rules):
        """Rules in Maya's Project Window display order (``RULE_NICE_NAMES`` order for
        the known vocabulary, then customs alphabetically)."""
        known = [k for k in ptk.RULE_NICE_NAMES if k in rules]
        custom = sorted(k for k in rules if k not in ptk.RULE_NICE_NAMES)
        return [(k, rules[k]) for k in known + custom]

    def _populate(self, rules):
        table = self.ui.tbl000
        ordered = self._ordered(rules)
        rows = [
            [
                ptk.RULE_NICE_NAMES.get(key, key) if self._nice_view else key,
                folder,
                "",
                "",
            ]
            for key, folder in ordered
        ] or [["", "", "", ""]]  # Clear keeps the table shape + one blank starter row
        self._updating = True
        try:
            table.add(rows, headers=["RULE:", "LOCATION:", "", ""])  # add() clears
            for r in range(table.rowCount()):
                rule_item = table.item(r, 0)
                folder_item = table.item(r, 1)
                key = ordered[r][0] if r < len(ordered) else None
                if rule_item is not None:
                    if key is not None:
                        rule_item.setData(QtCore.Qt.UserRole, key)
                    flags = rule_item.flags()
                    if self._nice_view and key is not None:
                        rule_item.setFlags(flags & ~QtCore.Qt.ItemIsEditable)
                    else:
                        rule_item.setFlags(flags | QtCore.Qt.ItemIsEditable)
                if folder_item is not None:
                    folder_item.setFlags(folder_item.flags() | QtCore.Qt.ItemIsEditable)
                self._set_row_actions(r)
            self._apply_column_sizing()
        finally:
            self._updating = False

    def _apply_column_sizing(self):
        """LOCATION fills the row width; the reset/remove action icons stay pinned to the
        far right at row height. Re-applied after every ``add()`` (which resets column
        state: TableActions re-fixes its own columns, this re-stretches LOCATION)."""
        header = self.ui.tbl000.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # RULE
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # LOCATION

    def _set_row_actions(self, row):
        """Attach the per-row reset/remove action icons."""
        table = self.ui.tbl000
        table.actions.set(row, 2, "reset")
        table.actions.set(row, 3, "remove")

    @staticmethod
    def _key_for_label(text):
        """The rule key a user-typed nice-name *text* stands for, else the text itself.

        A row added while in Nice Names view has no UserRole key, so its cell text IS
        the key candidate, and the user is looking at labels, so they type one
        ("Render Data"). Without this reverse lookup that label was written verbatim
        as the rule name (``workspace -fr "Render Data" …``), which Maya does not
        recognize. Matched case-insensitively; an unknown label is a custom rule and
        passes through unchanged.
        """
        text = str(text or "").strip()
        if not text:
            return ""
        folded = text.casefold()
        for key, label in ptk.RULE_NICE_NAMES.items():
            if label.casefold() == folded:
                return key
        return text

    def _key_at(self, row):
        """The raw rule key of *row*: from UserRole in nice-name view (labels aren't
        keys), from the cell text in file-rules view (where the key column is editable)."""
        item = self.ui.tbl000.item(row, 0)
        if item is None:
            return ""
        if self._nice_view:
            key = item.data(QtCore.Qt.UserRole)
            if not key:  # a row added in this view: the text is a label, not a key
                return self._key_for_label(item.text())
        else:
            key = item.text()
        return str(key or "").strip()

    def _gather(self):
        """The table's rules as a dict; blank/incomplete rows are skipped."""
        table = getattr(self.ui, "tbl000", None)
        if table is None:
            return {}
        rules = {}
        for r in range(table.rowCount()):
            key = self._key_at(r)
            folder_item = table.item(r, 1)
            folder = (folder_item.text() if folder_item else "").strip()
            if key and folder:
                rules[key] = folder
        return rules

    def _on_view_toggled(self, raw):
        """Nice Names ↔ File Rules (Maya's Edit ▸ View toggle): re-renders the current
        table content; no write (the rules are unchanged)."""
        rules = self._gather()
        self._nice_view = not bool(raw)
        self._populate(rules)

    # ------------------------------------------------------------------ write-through
    def _write(self):
        """Save the table to the project's workspace.mel, the real-time Accept. Creates
        the project (marker + rule folders) on the first rule edit of a fresh path."""
        root = self._root()
        if not root:
            self.ui.footer.setStatusText("Set a project root to save rule edits.")
            return False
        rules = self._gather()
        removed = set(self._loaded_rules) - set(rules)
        if not rules and not removed:
            return False  # empty definition on an unbuilt path: nothing to write
        try:
            ws = ptk.Workspace(root, rules)
            ws.save(create_dirs=True, remove=removed)
        except OSError as e:
            self.sb.message_box(str(e))
            return False
        self._loaded_rules = dict(rules)
        self._set_current(root)  # a just-built project becomes the current workspace
        if self._preset_mgr is not None:
            self._preset_mgr.refresh_modified_state()
        self.ui.footer.setStatusText(f"Saved {os.path.basename(os.path.normpath(root))}")
        return True

    def _on_item_changed(self, item):
        """A committed user cell edit saves immediately."""
        if not self._updating:
            self._write()

    # ------------------------------------------------------------------ row actions
    def add_rule(self):
        """Append an empty, editable rule row (saves once both cells are filled)."""
        table = self.ui.tbl000
        r = table.rowCount()
        self._updating = True
        try:
            table.insertRow(r)
            for c in range(2):
                item = QtWidgets.QTableWidgetItem("")
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                table.setItem(r, c, item)
            self._set_row_actions(r)
        finally:
            self._updating = False
        table.editItem(table.item(r, 0))

    def reset_row(self, row):
        """Reset *row*'s location to the active template's default for its rule."""
        key = self._key_at(row)
        default = self.tk.EnvUtils.workspace_template_rules().get(key)
        if default is None:
            self.ui.footer.setStatusText(f"No template default for '{key or '(blank)'}'.")
            return
        item = self.ui.tbl000.item(row, 1)
        if item is not None and item.text() != default:
            item.setText(default)  # itemChanged → write-through

    def remove_row(self, row):
        """Remove *row* and delete its rule from workspace.mel."""
        table = self.ui.tbl000
        self._updating = True
        try:
            table.removeRow(row)
            for r in range(table.rowCount()):
                self._set_row_actions(r)  # re-sync action states to the shifted rows
        finally:
            self._updating = False
        self._write()

    def reset_rules(self):
        """Restore the default file rules (the active template's) and save."""
        self._populate(self.tk.EnvUtils.workspace_template_rules())
        self._write()

    def clear_rules(self):
        """Remove every file rule and save (hand-written marker lines survive)."""
        self._populate({})
        self._write()

    # ------------------------------------------------------------------ project actions
    def create_project(self):
        """Build the project at the current root: marker + the active template's rule
        folders (Maya's File ▸ Project Window ▸ New). Idempotent on an existing
        project: its own rules win, so this never clobbers one."""
        root = self._root()
        if not root:
            self.ui.footer.setStatusText("Set a project root first.")
            return
        try:
            ws = self.tk.EnvUtils.create_workspace(root)
        except OSError as e:
            self.sb.message_box(str(e))
            return
        if ws is None:
            return
        self._set_current(root)
        self._load()
        self.ui.footer.setStatusText(f"Created {os.path.basename(os.path.normpath(root))}")

    def open_folder(self):
        """Open the project root in the system file browser."""
        root = self._root()
        if not (root and os.path.isdir(root)):
            self.sb.message_box(
                "The project doesn't exist yet: use <b>Create Project</b> (header "
                "menu), or edit a rule to build it implicitly."
            )
            return
        try:
            ptk.FileUtils.reveal_in_file_manager(root)
        except (FileNotFoundError, OSError) as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ templates
    def _apply_template(self, rules):
        """PresetManager value applier: load a template's rules into the project."""
        rules = ptk.WorkspaceTemplates.rules_from(rules)
        self._populate(rules)
        self._write()
        return len(rules)
