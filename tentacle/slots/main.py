# !/usr/bin/python
# coding=utf-8
"""Main: the start menu hub and its Workspace tab, one Slots class for both hosts.

The start page's buttons (``main#startmenu.ui``) route to the other categories
through their ``target`` property alone, so nothing here touches them. The
Workspace tab (``list000``) is the slot's work:

**Set Workspace** is one flow in both hosts: browse for a directory; a pick that
is not a workspace yet is OFFERED as a new default workspace built from the
shared template (``workspace.mel`` and its rule folders; *Retry* re-browses, like
Maya's "Try again"); then it opens. Maya's own Set Project writes a bare marker
on "Create default workspace" and Blender has no project system, so building
the standard folders is the ecosystem's half (``EnvUtils.create_workspace``).

What a workspace is, how one opens and where the session's workspace and scene
come from are the host toolkit's (``self.tk.EnvUtils``): Maya's is a folder with
a ``workspace.mel``, opened as File > Set Project opens it; Blender's may also
be a plain folder of .blend files, pinned for the session.
"""

import os

import pythontk as ptk

from tentacle import Slots


class MainSlots(Slots):
    #: The recent-workspaces history's settings key, host-namespaced at use
    #: (QSettings is shared by both hosts, and a Maya project history is not a
    #: Blender one).
    RECENT_KEY = "workspace_recent_projects"

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.main

    # ------------------------------------------------------------------ the Workspace tab
    def list000_init(self, widget):
        """Initialize the Workspace tab.

        Rows: ``Set Workspace`` (click prompts for a project dir; its flyout nests
        ``Auto Set Workspace`` and a ``Recent Workspaces`` sub-flyout), ``Edit
        Workspace`` (the host's project editor), then the workspace-name row (the
        row opens the workspace root; its flyout browses the dir tree), then
        ``Scene Directory`` (opens the saved scene's folder; its flyout's ``Copy
        Path`` copies the full path; absent for an unsaved scene). The dir-browser
        rows carry a folder icon that sets them apart from the action rows above.
        Rebuilt on every show (``refresh_on_show``) so the dir tree and recent list
        stay current.
        """
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True
            # Built once, off __init__ so a settings read can't break construction.
            self._workspace_store = self.sb.RecentValuesStore(
                settings_key=self._recent_key(),
                max_recent=10,
                display_format="auto",
                validator=self.tk.EnvUtils.is_workspace,
            )
            if not self._workspace_store.values:
                # First use under the host's key: carry over the history kept under
                # the shared key before the key was host-namespaced (Maya's).
                legacy = self.sb.RecentValuesStore(settings_key=self.RECENT_KEY)
                for path in legacy.values:
                    self._workspace_store.add(path)
        # The host's own recent projects, on every show: ``add`` appends only what
        # is new and never reorders, so a project opened outside this tab appears.
        for path in self.tk.EnvUtils.get_recent_projects(slice(0, 10)):
            if self.tk.EnvUtils.is_workspace(path):
                self._workspace_store.add(path)
        widget.fixed_item_height = 18
        # Sublists fan out to the RIGHT, not down: a downward flyout would open
        # straight over the rows beneath it.
        widget.apply_preset("expand_right")

        # --- workspace editing ---
        set_ws = widget.add("Set Workspace", data="__set_dir__")
        set_ws.sublist.add("Auto Set Workspace", data="__auto__")
        # Recent workspaces nest one level deeper; the parent row has no data, so
        # it only expands.
        valid = self._workspace_store.valid_values()
        if valid:
            recent = set_ws.sublist.add("Recent Workspaces")
            display = self._workspace_store.display_map(valid)
            for path in valid:
                recent.sublist.add(display[path], data=("__recent__", path))
        widget.add("Edit Workspace", data="__editor__")

        # --- the current workspace's dir browser (a folder icon marks each dir row) ---
        root = self.tk.EnvUtils.workspace_root()
        if root and os.path.isdir(root):
            # Native separators, so every row's data opens in the system browser.
            root = os.path.normpath(root)
            w = widget.add(os.path.basename(root), data=root)
            self.sb.IconManager.set_label_icon(w, "folder_filled")
            self._populate_dir_sublist(w.sublist, root, max_depth=2)

        # The open scene's folder (saved scenes only): one click to its dir.
        self._add_scene_dir_row(widget)

        widget.setVisible(True)

    def _recent_key(self):
        """``workspace_recent_projects_<host>``, by uitk's host-namespacing rule
        (``ShortcutManager.host_namespace_suffix`` of the switchboard's
        ``context_tags``): the suffix every other per-host store uses."""
        suffix = self.sb.ShortcutManager.host_namespace_suffix(
            getattr(self.sb, "context_tags", None)
        )
        return self.RECENT_KEY + suffix

    def _populate_dir_sublist(self, sublist, path, max_depth=2):
        """Fill *sublist* with *path*'s visible sub-folders, recursing to
        *max_depth*; a folder with no sub-folders gets no flyout. Folders only: a
        click opens the folder in the system browser."""
        try:
            dirs = sorted(
                d
                for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d)) and not d.startswith(".")
            )
        except OSError:
            return

        for d in dirs:
            full_path = os.path.join(path, d)
            item = sublist.add(d, data=full_path)
            self.sb.IconManager.set_label_icon(item, "folder_filled")
            if max_depth > 1:
                try:
                    has_subdirs = any(
                        sd
                        for sd in os.listdir(full_path)
                        if os.path.isdir(os.path.join(full_path, sd))
                        and not sd.startswith(".")
                    )
                except OSError:
                    continue
                if has_subdirs:
                    self._populate_dir_sublist(item.sublist, full_path, max_depth - 1)

    def _add_scene_dir_row(self, widget):
        """Add a ``Scene Directory`` row that opens the open scene's folder, only
        when the scene is saved and that folder still exists.

        Its data is the folder itself, so a click takes :meth:`list000`'s
        directory branch; its flyout holds ``Copy Path``. The scene comes from
        ``EnvUtils.saved_scene_path``: Maya's batch mode reports an unsaved scene as
        a phantom ``<project>/untitled`` whose folder would pass as the scene's.
        """
        scene = self.tk.EnvUtils.saved_scene_path()
        if not scene:
            return
        scene_dir = os.path.dirname(os.path.normpath(scene))
        if not os.path.isdir(scene_dir):
            return
        row = widget.add("Scene Directory", data=scene_dir, setToolTip=scene_dir)
        self.sb.IconManager.set_label_icon(row, "folder_filled")
        row.sublist.add(
            "Copy Path", data=("__copy_path__", scene_dir), setToolTip=scene_dir
        )

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Workspace tab dispatch: the editing actions, recent-workspace selection,
        and the directory-browser rows."""
        data = item.item_data()
        if data == "__set_dir__":
            self._set_workspace_interactive()
        elif data == "__auto__":
            self._auto_set_workspace()
        elif data == "__editor__":
            self._open_workspace_editor()
        elif isinstance(data, tuple) and data and data[0] == "__recent__":
            self._set_workspace_from_path(data[1])
        elif isinstance(data, tuple) and data and data[0] == "__copy_path__":
            self.sb.QtWidgets.QApplication.clipboard().setText(data[1])
            self.sb.handlers.marking_menu.hide()
            self.sb.message_box(f"Copied: <hl>{data[1]}</hl>")
        elif data and os.path.isdir(str(data)):
            ptk.FileUtils.open_explorer(str(data))
            self.sb.handlers.marking_menu.hide()

    # ------------------------------------------------------------------ workspace editing
    def _set_workspace_interactive(self):
        """Set Workspace: browse for the project directory and open it.

        A pick that is not a workspace is offered as a new default workspace (Yes
        / Retry / Cancel): *Yes* builds it from the shared template, *Retry*
        re-browses from the pick's parent, *Cancel* leaves the disk untouched.
        Nothing is ever built unasked.
        """
        # Hide first: the topmost marking-menu window would sit over the dialogs.
        self.sb.handlers.marking_menu.hide()
        # Start where Maya's Set Project does: the current workspace's parent.
        start = os.path.dirname(
            os.path.normpath(self.tk.EnvUtils.workspace_root() or "")
        )
        while True:
            path = self.tk.UiUtils.browse_directory(
                start if os.path.isdir(start) else "",
                caption="Set Workspace",
                ok_caption="Set",
            )
            if not path:
                return
            path = os.path.normpath(path)
            if self.tk.EnvUtils.is_workspace(path):
                break
            choice = self.sb.message_box(
                f"<hl>{os.path.basename(path)}</hl> is not a workspace.<br>"
                "Create a default workspace there (workspace.mel + the standard "
                "folders from the active template)?",
                "Yes",
                "Retry",
                "Cancel",
            )
            if choice == "Yes":
                self.tk.EnvUtils.create_workspace(path)
                break
            if choice != "Retry":
                return
            start = os.path.dirname(path)
        self._switch_to_workspace(path)

    def _set_workspace_from_path(self, path):
        """Switch to a recent workspace *path*, re-validated first."""
        if not self.tk.EnvUtils.is_workspace(path):
            self.sb.message_box("Not a valid workspace.")
            return
        self._switch_to_workspace(path)

    def _auto_set_workspace(self):
        """Auto Set Workspace: the workspace that holds the open scene (the
        nearest ``workspace.mel`` above it; Blender also takes the session pin and
        the file's own folder), then switch to it."""
        root = self.tk.EnvUtils.find_workspace_using_path()
        if not root:
            self.sb.message_box("No workspace found.")
            return
        self._switch_to_workspace(root)

    def _switch_to_workspace(self, path):
        """Open *path* as the session's workspace, bump it to most-recent, report it.

        Normalized first: a stored path may keep the trailing separator Maya's
        ``workspace -q -rd`` returns, which would collapse ``basename`` to ``""``.
        """
        path = os.path.normpath(path)
        self.tk.EnvUtils.set_current_workspace(path)
        self._workspace_store.record(path)
        self.sb.message_box(f"Workspace set to <hl>{os.path.basename(path)}</hl>.")
        self.sb.handlers.marking_menu.hide()

    def _open_workspace_editor(self):
        """Edit Workspace: tentacle's Workspace Editor where it is served
        (``slots.tools.HOSTS``: Blender, which has no project editor of its own),
        else the host's own Project Window."""
        if self.sb.ui_name_resolves("workspace_editor"):
            self.sb.handlers.marking_menu.show("workspace_editor")
            return
        if self.tk.UiUtils.open_editor("Project Window") is None:
            self.sb.message_box("Could not open the <strong>Project Window</strong>.")
        self.sb.handlers.marking_menu.hide()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
