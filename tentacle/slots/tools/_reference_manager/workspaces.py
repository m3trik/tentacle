# !/usr/bin/python
# coding=utf-8
"""The Reference Manager's workspace browser: the Root Directory, the workspace
combo it fills (each root remembers its last pick), the footer's workspace
status, and the session's project.

Private to :mod:`tentacle.slots.tools.reference_manager`; a collaborator of the
panel's controller (:mod:`.controller`), whose engine answers what a workspace is
on each host (``find_available_workspaces``, ``current_working_dir``).
"""

import html
import os
from typing import Optional

import pythontk as ptk


class WorkspaceBrowser:
    """The Root Directory and Workspaces fields (see the module docstring)."""

    #: Max per-root workspace selections remembered.
    WORKSPACE_HISTORY_MAX = 50

    def __init__(self, controller):
        self.c = controller
        self.updating_directory = False  # guards cascading combo / dir events
        self._last_dir_valid = None

    def root_dir(self) -> str:
        """The Root Directory field's text."""
        field = getattr(self.c.ui, "txt000", None)
        return field.text().strip() if field is not None else ""

    def workspace_dir(self) -> str:
        """The workspace being browsed: the combo's selection, else the root."""
        combo = getattr(self.c.ui, "cmb000", None)
        if combo is not None and combo.count() and combo.currentIndex() >= 0:
            data = combo.itemData(combo.currentIndex())
            if data:
                return data
        return self.root_dir()

    def _workspace_history(self) -> dict:
        settings = getattr(self.c.ui, "settings", None)
        return dict((settings.value("workspace_history") if settings else None) or {})

    def save_workspace_selection(self, root_dir: str, workspace_name: str):
        """Remember which workspace was last selected for *root_dir* (capped)."""
        if not (root_dir and workspace_name):
            return
        history = self._workspace_history()
        history[self.c.norm(root_dir)] = workspace_name
        if len(history) > self.WORKSPACE_HISTORY_MAX:
            history = dict(list(history.items())[-self.WORKSPACE_HISTORY_MAX :])
        self.c.ui.settings.setValue("workspace_history", history)

    def restore_workspace_index(self, widget) -> bool:
        """Select the workspace last used for the current root, if still listed."""
        root = self.root_dir()
        if not root:
            return False
        saved = self._workspace_history().get(self.c.norm(root))
        if saved:
            for i in range(widget.count()):
                if widget.itemText(i) == saved:
                    widget.setCurrentIndex(i)
                    return True
        return False

    def update_current_dir(self, text: Optional[str] = None):
        """The Root Directory changed (or was validated): rescan its workspaces when
        it is a new valid folder, clear the panel when it is no folder at all."""
        if self.updating_directory:
            return
        self.updating_directory = True
        try:
            text = text or self.c.ui.txt000.text()
            new_dir = os.path.normpath(text.strip()) if text.strip() else ""
            is_valid = bool(new_dir) and os.path.isdir(new_dir)
            # Compared normalized: a host workspace query keeps forward slashes and a
            # trailing separator, which would read as "changed" on every startup.
            changed = self.c.norm(new_dir) != self.c.norm(
                self.c.engine.current_working_dir or ""
            )
            revalidate = is_valid and (changed or self._last_dir_valid is False)
            self._last_dir_valid = is_valid
            if revalidate:
                self.c.engine.current_working_dir = new_dir
                self.update_workspace_combo(new_dir)
            elif not is_valid:
                self.c.ui.cmb000.clear()
                self.c.ui.tbl000.setRowCount(0)
                self.update_workspace_footer()
        finally:
            self.updating_directory = False

    def update_workspace_combo(self, root_dir=None):
        """Repopulate the workspace combo from the workspaces under *root_dir* (the
        Root Directory field by default) and select the best match: the in-memory
        selection, else the one remembered for this root, else the first.

        The single source of truth for populating ``cmb000``.
        """
        root_dir = root_dir or self.root_dir() or self.c.engine.current_working_dir
        widget = self.c.ui.cmb000
        if not root_dir or not os.path.isdir(root_dir):
            widget.clear()
            self.c.ui.tbl000.setRowCount(0)
            return
        workspaces = self.c.engine.find_available_workspaces(root_dir)
        blocked = widget.blockSignals(True)
        try:
            current_index = widget.currentIndex()
            current_path = (
                widget.itemData(current_index) if current_index >= 0 else None
            )
            widget.clear()
            widget.add(workspaces)
            if workspaces:
                restored = False
                if current_path:
                    for i in range(widget.count()):
                        if widget.itemData(i) == current_path:
                            widget.setCurrentIndex(i)
                            restored = True
                            break
                if not restored:
                    restored = self.restore_workspace_index(widget)
                if not restored:
                    widget.setCurrentIndex(0)
            else:
                self.c.logger.warning(f"No workspaces in {root_dir}")
        finally:
            widget.blockSignals(blocked)
        # Signals were blocked: load the selected workspace by hand.
        if widget.count() > 0 and widget.currentIndex() >= 0:
            self.set_workspace(widget.itemData(widget.currentIndex()), invalidate=True)
        else:
            self.c.ui.tbl000.setRowCount(0)

    def set_workspace(self, workspace_path: str, invalidate: bool = True) -> bool:
        """Browse *workspace_path* and refresh the file list. The host's own project
        is NOT changed here -- only opening a scene (or the Set Project action) does."""
        if not workspace_path or not os.path.isdir(workspace_path):
            self.c.logger.warning(f"Invalid workspace path: {workspace_path}")
            return False
        current = self.c.engine.current_working_dir
        same = bool(current) and self.c.norm(workspace_path) == self.c.norm(current)
        if not same:
            self.c.engine.current_working_dir = workspace_path
            root = self.root_dir()
            if root:
                self.save_workspace_selection(root, os.path.basename(workspace_path))
        self.c.refresh_file_list(invalidate=invalidate)
        self.update_workspace_footer()
        return True

    def update_workspace_footer(self):
        """Name the browsed workspace in the footer's status."""
        footer = getattr(self.c.ui, "footer", None)
        if footer is None:
            return
        name = os.path.basename((self.workspace_dir() or "").rstrip("/\\"))
        footer.setStatusText(f"Workspace: {name}" if name else "")

    def flash_footer(self, text, level="success"):
        """Show *text* in the footer's status for a moment, then the workspace again."""
        footer = getattr(self.c.ui, "footer", None)
        if footer is None:
            return
        footer.setStatusText(text, level=level)
        self.c.sb.defer_with_timer(self.update_workspace_footer, ms=3000)

    def set_project(self):
        """Set the host's project (session workspace) to the browsed workspace -- the
        explicit counterpart of the automatic set on scene open, for switching without
        opening anything (``EnvUtils.set_current_workspace``: Maya's ``workspace -o``,
        Blender's session pin)."""
        workspace = self.workspace_dir()
        if not workspace or not os.path.isdir(workspace):
            self.c.message("Select a valid workspace first.")
            return False
        env = self.c.tk.EnvUtils
        try:
            if self.c.norm(env.workspace_root() or "") != self.c.norm(workspace):
                env.set_current_workspace(workspace)
                self.c.logger.info(f"Set the project to: {workspace}")
        except Exception as e:  # noqa: BLE001 - reported
            self.c.message(
                f"Failed to set the project:<br>{html.escape(str(e), quote=False)}"
            )
            return False
        name = os.path.basename(os.path.normpath(workspace))
        self.flash_footer(f"Project set: {name}")
        return True

    def set_root_to_current(self):
        """Set the Root Directory to the host's current workspace."""
        self.c.ui.txt000.setText(self.c.engine.current_workspace)

    def open_root_dir(self):
        """Reveal the Root Directory in the file manager."""
        root = self.root_dir()
        if not (root and os.path.isdir(root)):
            self.c.message("Set a valid root directory first.")
            return
        ptk.FileUtils.open_explorer(root, logger=self.c.logger)

    def new_workspace(self):
        """Create a marked workspace (``workspace.mel``, rules from the active
        template) under the Root Directory, and browse it."""
        root = self.root_dir()
        if not (root and os.path.isdir(root)):
            self.c.message("Set a valid root directory first.")
            return
        name = (
            self.c.sb.input_dialog("New Workspace", "Workspace folder name:", "") or ""
        ).strip()
        if not name:
            return
        try:
            ws = self.c.tk.EnvUtils.create_workspace(os.path.join(root, name))
        except OSError as e:
            self.c.message(html.escape(str(e), quote=False))
            return
        self.c.engine.invalidate_workspace_files()
        self.update_workspace_combo(root)
        if ws is not None:
            self.select_workspace(ws.root)

    def mark_workspace(self):
        """Mark the browsed workspace as a shared Maya/Blender project: a
        ``workspace.mel`` describing the layout it already has (nothing moves)."""
        ws_dir = self.workspace_dir()
        if not (ws_dir and os.path.isdir(ws_dir)):
            self.c.message("Pick a workspace (or set a root directory) first.")
            return
        try:
            ws = self.c.tk.EnvUtils.promote_workspace(ws_dir)
        except OSError as e:
            self.c.message(html.escape(str(e), quote=False))
            return
        if ws is None:
            self.c.message("Could not mark the workspace.")
            return
        self.c.engine.invalidate_workspace_files()
        self.update_workspace_combo()
        self.select_workspace(ws.root)

    def select_workspace(self, path):
        """Select the combo entry whose data is *path* (after a repopulate)."""
        combo = self.c.ui.cmb000
        target = self.c.norm(path)
        for i in range(combo.count()):
            if self.c.norm(combo.itemData(i) or "") == target:
                combo.setCurrentIndex(i)
                return
