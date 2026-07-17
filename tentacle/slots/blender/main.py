# !/usr/bin/python
# coding=utf-8
import os

import blendertk as btk
from uitk import Signals, RecentValuesStore
from tentacle.slots.blender._slots_blender import SlotsBlender


class Main(SlotsBlender):
    """Blender port of the shared ``main`` start menu — a workspace switcher (primary) with
    a read-only directory browser of the current workspace (secondary), mirroring Maya's
    ``list000`` at the behavior level.

    Maya's *workspace* is a project root holding ``workspace.mel``, set/switched independently
    of the loaded scene (``cmds.workspace``). Blender has no such standalone project state — its
    closest analogue is simply **the open ``.blend``'s directory** (``btk.get_env_info
    ('workspace')``), and a "workspace folder" is one that directly holds ``.blend`` files
    (``btk.find_workspaces``). So "switching workspace" in Blender means picking which ``.blend``
    to work from via Blender's own native Open/Save-As dialogs, rather than repointing project
    settings underneath an unchanged scene. ``Set Workspace`` (always present) does that; its
    flyout nests ``Auto Set Workspace`` (walk up the current folder tree for the nearest one) and
    a ``Recent Workspaces`` sub-flyout (persisted, jump back in one click). ``Current Workspace:
    <dir>`` (only added when the open .blend's folder is a valid workspace) is the secondary
    browser: its sub-folders (expandable) and files (a file opens in its default app, a ``.blend``
    in Blender; a folder opens in the system browser) — folders *and* files, unlike Maya's
    folders-only tree, since Blender has no rigid ``scenes/`` sub-structure to browse around.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.main

    def list000_init(self, widget):
        """Initialize the Workspace tab.

        Two root rows: ``Set Workspace`` (click opens Blender's native Open/Save-As dialog;
        its flyout nests ``Auto Set Workspace`` and a ``Recent Workspaces`` sub-flyout) and
        ``Current Workspace: <dir>`` (only added if the open file's folder is a valid
        workspace; its flyout browses the dir tree). Rebuilt on every show
        (``refresh_on_show``) so the dir tree and recent list stay current.
        """
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True
            # Shared recent-workspaces model (valid Blender workspace folders only), built
            # once (kept off the slot __init__ so a recent-files read can't break
            # construction). Namespaced "_blender" so it never collides with Maya's project
            # history under the same QSettings store (host-namespaced persistence — Maya and
            # Blender workspaces are different concepts even though both are "project dirs").
            self._workspace_store = RecentValuesStore(
                settings_key="workspace_recent_projects_blender",
                max_recent=10,
                display_format="auto",
                validator=self._is_workspace,
            )
        # Re-seed from Blender's own recent-files list on every show, not just the very
        # first init: unlike Maya's synchronous ``SetProject``, Set Workspace's Open/Save-As
        # dialogs run modally (INVOKE_DEFAULT) and return before the user actually picks a
        # file, so there is no call-site moment at which to record the result. Picking up a
        # newly opened/saved workspace from Blender's own recent-files.txt the next time this
        # tab is shown is how it ever reaches Recent Workspaces — otherwise the very folder
        # Set Workspace was just used to switch to would never appear in its own history.
        # ``add()`` is idempotent (skips values already present, doesn't reorder), so this is
        # safe and cheap to re-run on every show.
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

        # --- the current workspace dir browser ---
        workspace = btk.get_env_info("workspace")
        workspace_dir = btk.get_env_info("workspace_dir")
        if workspace and os.path.isdir(workspace):
            w = widget.add(f"Current Workspace: {workspace_dir}", data=workspace)
            self._populate_dir_contents(w.sublist, workspace, max_depth=2)

        widget.setVisible(True)

    def _populate_dir_contents(self, sublist, path, max_depth=2):
        """Populate ``sublist`` with ``path``'s contents: sub-folders first (expandable,
        recursed to ``max_depth``), then files (leaves). Plain file-browser order."""
        try:
            entries = sorted(e for e in os.listdir(path) if not e.startswith("."))
        except OSError:
            return

        dirs, files = [], []
        for e in entries:
            full = os.path.join(path, e)
            (dirs if os.path.isdir(full) else files).append((e, full))

        for name, full in dirs:
            item = sublist.add(name, data=full)
            if max_depth > 1:
                self._populate_dir_contents(item.sublist, full, max_depth - 1)
        for name, full in files:
            sublist.add(name, data=full)

    @Signals("on_item_interacted")
    def list000(self, item):
        """Workspace tab dispatch — editing actions, recent-workspace selection, and the
        directory-browser entries."""
        data = item.item_data()
        if data == "__set_dir__":
            self._set_workspace_interactive()
        elif data == "__auto__":
            self._auto_set_workspace()
        elif isinstance(data, tuple) and data and data[0] == "__recent__":
            self._set_workspace_from_path(data[1])
        elif data and os.path.exists(str(data)):
            os.startfile(str(data))
            self.sb.handlers.marking_menu.hide()

    # ------------------------------------------------------------------ workspace editing

    @staticmethod
    def _is_workspace(path):
        """True if *path* is a Blender workspace folder — one that directly contains at
        least one ``.blend`` file. Blender has no ``workspace.mel``-style marker, so this
        mirrors Maya's ``_is_workspace`` check via the same ``btk.find_workspaces``
        primitive the folder-discovery flyout already uses."""
        if not path or not os.path.isdir(path):
            return False
        return os.path.normpath(path) in btk.find_workspaces(path, recursive=False)

    def _set_workspace_interactive(self):
        """Set Workspace — open Blender's native file browser: Open (to switch to a
        different saved .blend, and thus its folder) when a file is already open, or Save
        As (to establish a working folder on the very first save) when unsaved. Blender has
        no project state independent of the open file, so "setting" a workspace means
        picking which file to work from — the always-actionable root row Maya's ``Set
        Workspace`` maps to (replacing the old dead-end hint row for the unsaved case)."""
        op_path = "wm.open_mainfile" if btk.get_env_info("workspace") else "wm.save_as_mainfile"
        self.invoke_op(op_path)
        self.sb.handlers.marking_menu.hide()

    def _auto_set_workspace(self):
        """Auto Set Workspace — walk up from the current .blend's folder (or the current
        working directory when unsaved) until an ancestor directly holds .blend files,
        mirroring ``mtk.find_workspace_using_path``'s up-the-tree semantics."""
        start = btk.get_env_info("workspace") or os.getcwd()
        found = None
        d = start
        while d:
            if self._is_workspace(d):
                found = os.path.normpath(d)
                break
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
        if not found:
            self.sb.message_box("No workspace found.")
            return
        self._workspace_store.record(found)
        # Truthful toast: nothing in Blender is switched here (there is no Maya-style
        # workspace state to set) — the folder is found and recorded in Recent Workspaces.
        self.sb.message_box(
            f"Found workspace <hl>{os.path.basename(found)}</hl> — "
            "recorded in Recent Workspaces."
        )
        self.sb.handlers.marking_menu.hide()

    def _set_workspace_from_path(self, path):
        """Jump to a recent workspace *path* (re-validates it still holds .blend files) —
        opens its folder and bumps it to most-recent."""
        if not self._is_workspace(path):
            self.sb.message_box("Not a valid workspace.")
            return
        os.startfile(path)
        self._workspace_store.record(path)  # bump to most-recent
        self.sb.message_box(
            f"Opened workspace folder <hl>{os.path.basename(path)}</hl>."
        )
        self.sb.handlers.marking_menu.hide()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
