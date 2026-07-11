# !/usr/bin/python
# coding=utf-8
import os

import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from uitk import Signals, RecentValuesStore
from tentacle.slots.maya._slots_maya import SlotsMaya


class Main(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.main

    def list000_init(self, widget):
        """Initialize the Workspace tab.

        Two root rows: ``Set Workspace`` (click prompts for a project dir; its
        flyout nests ``Auto Set Workspace`` and a ``Recent Workspaces``
        sub-flyout) and ``Current Workspace: <name>`` (the row opens the
        workspace root; its flyout browses the dir tree). Rebuilt on every show
        (``refresh_on_show``) so the dir tree and recent list stay current.
        """
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True
            # Shared recent-workspaces model (valid Maya workspaces only), keyed
            # by the same settings namespace the old Set Workspace option box
            # used — so existing history carries over. Built once (kept off the
            # slot __init__ so a recent-projects read can't break construction),
            # seeded from Maya's recent projects on first ever use.
            self._workspace_store = RecentValuesStore(
                settings_key="workspace_recent_projects",
                max_recent=10,
                display_format="auto",
                validator=self._is_workspace,
            )
            if not self._workspace_store.values:
                for p in mtk.get_recent_projects(slice(0, 10), format="standard"):
                    if self._is_workspace(p):
                        self._workspace_store.add(p)
        widget.fixed_item_height = 18
        # Sublists fan out to the RIGHT, not down: a downward flyout would open
        # straight over the rows beneath it (Set Workspace sits above the
        # current-workspace dir browser).
        widget.apply_preset("expand_right")

        # --- workspace editing ---
        # Set Workspace prompts for the project dir on click; its flyout nests
        # the auto-detect alternative and the recent-workspaces sub-flyout.
        set_ws = widget.add("Set Workspace", data="__set_dir__")
        set_ws.sublist.add("Auto Set Workspace", data="__auto__")
        # Recent workspaces nest one level deeper, under Set Workspace (parent
        # row has no data so it only expands, never sets a workspace); valid
        # Maya workspaces only.
        valid = self._workspace_store.valid_values()
        if valid:
            recent = set_ws.sublist.add("Recent Workspaces")
            display = self._workspace_store.display_map(valid)
            for v in valid:
                recent.sublist.add(display[v], data=("__recent__", v))

        # --- the current workspace dir browser ---
        workspace = mtk.get_env_info("workspace")
        workspace_dir = mtk.get_env_info("workspace_dir")
        if workspace and os.path.isdir(workspace):
            # Maya returns a forward-slash path; normalize once so every entry's
            # data (root + nested dirs, built via os.path.join) uses native
            # separators and reliably opens in the system file browser.
            workspace = os.path.normpath(workspace)
            w = widget.add(f"Current Workspace: {workspace_dir}", data=workspace)
            self._populate_dir_sublist(w.sublist, workspace, max_depth=2)

        widget.setVisible(True)

    def _populate_dir_sublist(self, sublist, path, max_depth=2):
        """Recursively populate directory sublists."""
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
            if max_depth > 1:
                try:
                    has_subdirs = any(
                        sd
                        for sd in os.listdir(full_path)
                        if os.path.isdir(os.path.join(full_path, sd))
                        and not sd.startswith(".")
                    )
                    if has_subdirs:
                        self._populate_dir_sublist(
                            item.sublist, full_path, max_depth - 1
                        )
                except OSError:
                    pass

    @Signals("on_item_interacted")
    def list000(self, item):
        """Workspace tab dispatch — editing actions, recent-workspace selection,
        and directory-browser entries."""
        data = item.item_data()
        if data == "__set_dir__":
            self._set_workspace_interactive()
        elif data == "__auto__":
            self._auto_set_workspace()
        elif isinstance(data, tuple) and data and data[0] == "__recent__":
            self._set_workspace_from_path(data[1])
        elif data and os.path.isdir(str(data)):
            os.startfile(str(data))
            self.sb.handlers.marking_menu.hide()

    # ------------------------------------------------------------------ workspace editing

    @staticmethod
    def _is_workspace(path):
        """True if *path* is a Maya workspace root (contains a workspace.mel)."""
        return bool(path) and os.path.isfile(os.path.join(str(path), "workspace.mel"))

    def _set_workspace_interactive(self):
        """Set Workspace — prompt for the project directory (MEL SetProject)."""
        mel.eval("SetProject")
        workspace = mtk.get_env_info("workspace")
        if workspace:
            # cmds.workspace(q=True, rd=True) keeps a trailing slash; normalize
            # before storing so a later os.path.basename() on this entry (e.g.
            # reselecting it from Recent Workspaces) doesn't collapse to "".
            self._workspace_store.record(os.path.normpath(workspace))
        self.sb.handlers.marking_menu.hide()

    def _auto_set_workspace(self):
        """Auto Set Workspace — walk up parent dirs until a workspace is found."""
        workspace = mtk.find_workspace_using_path()
        if not workspace:
            self.sb.message_box("No workspace found.")
            return
        self._switch_to_workspace(workspace)

    def _set_workspace_from_path(self, path):
        """Switch to a recent workspace *path* (re-validates the workspace.mel)."""
        if not self._is_workspace(path):
            self.sb.message_box("Not a valid workspace.")
            return
        self._switch_to_workspace(path)

    def _switch_to_workspace(self, path):
        """Set Maya's workspace to *path*, bump it to most-recent, and report it.

        Normalizes first (strips any trailing slash — Maya's own
        ``workspace -q -rd`` keeps one, which would otherwise collapse
        ``os.path.basename()`` below to ``""``) so the confirmation message
        always shows the real workspace name.
        """
        path = os.path.normpath(path)
        cmds.workspace(path, openWorkspace=True)
        self._workspace_store.record(path)
        self.sb.message_box(f"Workspace set to <hl>{os.path.basename(path)}</hl>.")
        self.sb.handlers.marking_menu.hide()


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
