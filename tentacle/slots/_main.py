# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``main`` start menus' Workspace tab.

**Set Workspace** is one flow in both DCCs: browse for a directory → a pick that
is not a workspace yet is OFFERED as a new default workspace built from the
shared template (``workspace.mel`` AND its rule folders — the same template
Workspace Map ▸ New Project and blendertk's Workspace Editor build from; *Retry*
re-browses, like Maya's "Try again") → open it. It lives here because Maya's own
``SetProject`` writes a bare marker on "Create default workspace"
(``sp_createAndSetDefaultProject($path, false)`` — the ``false`` is
*createDirectories*) and Blender has no native project system at all, so the
"build the standard folders" half is the ecosystem's, not either DCC's.
**Recent-workspace selection** (re-validate, then switch) is the same on both
sides too.

Only the directory browser, what counts as a workspace, how a default one is
built, where the session's workspace is read from and how one is opened are
DCC-specific — those are the hooks below.
"""

import os


class MainMixin:
    """Shared ``main`` Workspace-tab behavior. Mixed in ahead of the DCC Slots base."""

    # ------------------------------------------------------------------ hooks
    def _current_workspace_root(self) -> str:
        """The session's current workspace root ('' when none)."""
        raise NotImplementedError

    def _browse_workspace_dir(self, start: str) -> str:
        """Modal directory browser for Set Workspace; '' when dismissed."""
        raise NotImplementedError

    def _is_workspace(self, path) -> bool:
        """True if *path* is a workspace root this DCC can open as-is."""
        raise NotImplementedError

    def _create_default_workspace(self, path: str):
        """Build *path* as a new workspace from the shared template (marker + rule
        folders) — the engine's ``create_workspace``."""
        raise NotImplementedError

    def _switch_to_workspace(self, path: str):
        """Open *path*, bump it to most-recent, report it."""
        raise NotImplementedError

    # -------------------------------------------------------------- behavior
    def _set_workspace_interactive(self):
        """Set Workspace — browse for the project directory and open it.

        A pick that :meth:`_is_workspace` rejects is offered as a new default
        workspace (Yes / Retry / Cancel): *Yes* builds it through
        :meth:`_create_default_workspace`, *Retry* re-browses from the pick's
        parent, *Cancel* leaves the disk untouched. Nothing is ever built unasked.
        """
        # Hide first — the topmost marking-menu window would sit over the modal
        # dialogs.
        self.sb.handlers.marking_menu.hide()
        # Start where Maya's Set Project does: the current workspace's parent.
        start = os.path.dirname(os.path.normpath(self._current_workspace_root() or ""))
        while True:
            path = self._browse_workspace_dir(start if os.path.isdir(start) else "")
            if not path:
                return
            path = os.path.normpath(path)
            if self._is_workspace(path):
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
                self._create_default_workspace(path)
                break
            if choice != "Retry":
                return
            start = os.path.dirname(path)
        self._switch_to_workspace(path)

    def _set_workspace_from_path(self, path):
        """Switch to a recent workspace *path* (re-validated first)."""
        if not self._is_workspace(path):
            self.sb.message_box("Not a valid workspace.")
            return
        self._switch_to_workspace(path)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
