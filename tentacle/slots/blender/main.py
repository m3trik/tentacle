# !/usr/bin/python
# coding=utf-8
import os

import blendertk as btk
from tentacle import MainMixin, SlotsBlender


class Main(MainMixin, SlotsBlender):
    """Blender port of the shared ``main`` start menu — a workspace switcher (primary) with
    a read-only directory browser of the current workspace (secondary), mirroring Maya's
    ``list000`` at the behavior level.

    Blender now has real standalone workspace state, shared with Maya: a workspace is a
    project root (ideally marked by a ``workspace.mel`` — the shared Maya/Blender project
    format — else a plain folder of ``.blend`` files), and the *current* workspace is
    blendertk's session pin (``btk.set_current_workspace``, the ``workspace -o`` analogue)
    falling back to the open .blend's resolved root (``btk.current_workspace``). So ``Set
    Workspace`` switches the pin from a directory picker exactly like Maya's Set Workspace
    (a pick that isn't a workspace yet is offered as a new one built from the shared
    template — marker + rule folders — in both DCCs); its flyout nests ``Auto Set Workspace`` (resolve from the open file and pin it) and a
    ``Recent Workspaces`` sub-flyout (persisted, jump back in one click). ``Edit
    Workspace`` opens the blendertk panel that creates a workspace / customizes its file
    rules (Maya's row opens the native Project Window). The workspace-name row then browses
    the directory tree: sub-folders (expandable), each opening in the system browser on
    click — folders only, like Maya's tree. The dir-browser rows carry a folder icon that
    sets them apart from the action rows above.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.main

    def list000_init(self, widget):
        """Initialize the Workspace tab.

        Root rows mirror Maya's: ``Set Workspace`` (click prompts for the project dir and
        pins it; its flyout nests ``Auto Set Workspace`` and a ``Recent Workspaces``
        sub-flyout), ``Edit Workspace`` (create / customize a workspace's file rules), then
        the workspace-name row (the row opens the workspace root; its flyout browses the dir
        tree). The dir-browser rows carry a folder icon that sets them apart from the action
        rows above. Rebuilt on every show (``refresh_on_show``) so the dir tree and recent
        list stay current.
        """
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True
            # Shared recent-workspaces model (valid Blender workspace folders only), built
            # once (kept off the slot __init__ so a recent-files read can't break
            # construction). Namespaced "_blender" so it never collides with Maya's project
            # history under the same QSettings store (host-namespaced persistence — Maya and
            # Blender workspaces are different concepts even though both are "project dirs").
            self._workspace_store = self.sb.RecentValuesStore(
                settings_key="workspace_recent_projects_blender",
                max_recent=10,
                display_format="auto",
                validator=self._is_workspace,
            )
        # Re-seed from Blender's own recent-files list on every show: Set Workspace records
        # its picks synchronously now (pin-based, like Maya's SetProject), but folders the
        # user reached through Blender's own Open/Save-As still only surface here. ``add()``
        # is idempotent (skips values already present, doesn't reorder), so this is safe and
        # cheap to re-run on every show.
        for recent_file in btk.get_recent_files(slice(0, 10)):
            folder = os.path.dirname(recent_file)
            if self._is_workspace(folder):
                self._workspace_store.add(folder)
        widget.fixed_item_height = 18
        # Sublists fan out to the RIGHT, not down: with two permanent root rows (Set
        # Workspace above Current Workspace), a downward flyout would open straight over
        # the row beneath it — same reasoning as Maya's list000.
        widget.apply_preset("expand_right")

        # --- workspace editing ---
        set_ws = widget.add("Set Workspace", data="__set_dir__")
        set_ws.sublist.add("Auto Set Workspace", data="__auto__")
        # Recent workspaces nest one level deeper, under Set Workspace (parent row has no
        # data so it only expands, never sets a workspace); valid workspace folders only.
        valid = self._workspace_store.valid_values()
        if valid:
            recent = set_ws.sublist.add("Recent Workspaces")
            display = self._workspace_store.display_map(valid)
            for path in valid:
                recent.sublist.add(display[path], data=("__recent__", path))

        # Edit Workspace — create a workspace / customize its file rules (Maya's row
        # opens the native Project Window; here it's the blendertk panel).
        widget.add("Edit Workspace", data="__editor__")

        # --- the current workspace dir browser ---
        # The workspace name on its own row (browses the tree). A folder icon
        # on this row and every nested dir marks them as directories, setting
        # the browser apart from the action rows above (no "Current Workspace"
        # separator — the icon is the differentiator now).
        workspace = btk.get_env_info("workspace")
        workspace_dir = btk.get_env_info("workspace_dir")
        if workspace and os.path.isdir(workspace):
            w = widget.add(workspace_dir, data=workspace)
            self.sb.IconManager.set_label_icon(w, "folder_filled")
            self._populate_dir_contents(w.sublist, workspace, max_depth=2)

        widget.setVisible(True)

    def _populate_dir_contents(self, sublist, path, max_depth=2):
        """Populate ``sublist`` with ``path``'s sub-folders (expandable, recursed to
        ``max_depth``) — folders only, like Maya's tree; a click opens the folder in the
        system browser."""
        try:
            dirs = sorted(
                e
                for e in os.listdir(path)
                if not e.startswith(".") and os.path.isdir(os.path.join(path, e))
            )
        except OSError:
            return

        for name in dirs:
            full = os.path.join(path, name)
            item = sublist.add(name, data=full)
            self.sb.IconManager.set_label_icon(item, "folder_filled")
            if max_depth > 1:
                self._populate_dir_contents(item.sublist, full, max_depth - 1)

    @SlotsBlender.Signals("on_item_interacted")
    def list000(self, item):
        """Workspace tab dispatch — editing actions, recent-workspace selection, and the
        directory-browser entries."""
        data = item.item_data()
        if data == "__set_dir__":
            self._set_workspace_interactive()
        elif data == "__auto__":
            self._auto_set_workspace()
        elif data == "__editor__":
            self._open_workspace_editor()
        elif isinstance(data, tuple) and data and data[0] == "__recent__":
            self._set_workspace_from_path(data[1])
        elif data and os.path.isdir(str(data)):
            os.startfile(str(data))
            self.sb.handlers.marking_menu.hide()

    # ------------------------------------------------------------------ workspace editing

    @staticmethod
    def _is_workspace(path):
        """True if *path* is a workspace folder — marked by a ``workspace.mel`` (the shared
        Maya/Blender project format) or directly holding ``.blend`` files — via the same
        marker-aware ``btk.find_workspaces`` primitive the folder-discovery flyout uses."""
        if not path or not os.path.isdir(path):
            return False
        return os.path.normpath(path) in btk.find_workspaces(path, recursive=False)

    # MainMixin hooks — the browse → offer → build → open flow itself lives once in
    # ``slots/_main.py`` (Maya's twin supplies fileDialog2 / mtk.create_workspace).
    def _current_workspace_root(self):
        return btk.get_env_info("workspace") or ""

    def _browse_workspace_dir(self, start):
        """Qt directory browser; '' when dismissed."""
        from qtpy import QtWidgets

        return QtWidgets.QFileDialog.getExistingDirectory(None, "Set Workspace", start)

    def _create_default_workspace(self, path):
        """Marker + rule folders from the shared template (``btk.create_workspace``).
        Only reached for a pick that is neither marked nor a folder of .blend files —
        a flat blend folder stays a zero-ceremony unmarked workspace (promoting one is
        the Workspace Editor's *Mark* job, not this row's)."""
        return btk.create_workspace(path)

    def _auto_set_workspace(self):
        """Auto Set Workspace — resolve the workspace from the open .blend (nearest
        ``workspace.mel`` root above it, else its own folder) and pin it, mirroring Maya's
        ``mtk.find_workspace_using_path`` walk-up + switch."""
        import bpy

        ws = btk.current_workspace(bpy.data.filepath or os.getcwd())
        if ws is None or not (ws.is_marked or self._is_workspace(ws.root)):
            self.sb.message_box("No workspace found.")
            return
        self._switch_to_workspace(ws.root)

    def _switch_to_workspace(self, path):
        """Pin *path* as the session's current workspace, bump it to most-recent, and
        report it — the Blender twin of Maya's ``_switch_to_workspace``
        (``cmds.workspace(path, openWorkspace=True)`` → ``btk.set_current_workspace``)."""
        path = os.path.normpath(path)
        btk.set_current_workspace(path)
        self._workspace_store.record(path)
        self.sb.message_box(f"Workspace set to <hl>{os.path.basename(path)}</hl>.")
        self.sb.handlers.marking_menu.hide()

    def _open_workspace_editor(self):
        """Edit Workspace — the blendertk panel that creates a workspace and customizes
        its file rules (Maya's twin row opens the native Project Window)."""
        self.sb.handlers.marking_menu.show("workspace_editor")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
