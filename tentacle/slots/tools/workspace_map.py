# !/usr/bin/python
# coding=utf-8
"""Workspace Map: browse a folder tree of project workspaces and switch the
current one.

A thin driver over the host toolkit's ``WorkspaceMap`` (``self.tk``), which
finds the workspaces (a folder holding a ``workspace.mel``, the shared
Maya/Blender project format) under a root and measures each; this class shows
them as a tree. The header menu builds a project from the active workspace
template, marks the root folder as a shared project, or publishes the current
project's rules as a template (``EnvUtils``, the template store both hosts
read).

A Maya tool for now (``tentacle.slots.tools.HOSTS``): blendertk has no
``WorkspaceMap``; Blender reaches projects through the Workspace tab and edits
one in the Workspace Editor.
"""

import os
from typing import Dict, Optional

import pythontk as ptk

from tentacle import Slots


class WorkspaceMapSlots(Slots, ptk.LoggingMixin):
    #: How long the root field waits after a keystroke before it rescans (ms).
    ROOT_SETTLE_MS = 500

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("WARNING")
        self.ui = self.sb.loaded_ui.workspace_map
        self.engine = self.tk.WorkspaceMap()
        self._browse_option = None
        self._last_dir_valid = None
        self._updating_directory = False
        self.ui.txt000.setText(self.engine.current_working_dir)
        # The first scan waits for the panel to open: the switchboard builds
        # this instance mid-load.
        self.sb.defer_with_timer(lambda: self.refresh_tree(invalidate=True), ms=100)

    # ------------------------------------------------------------------ header
    def header_init(self, widget):
        """Project creation actions + help text.

        No ``config_buttons`` call: the panel takes the handler's default
        chrome (menu / collapse / pin-or-hide); setting it here would drop the
        collapse and dismissal buttons.
        """
        widget.menu.add("Separator", setTitle="Project:")
        widget.menu.add(
            "QPushButton",
            setText="New Project",
            setObjectName="new_project",
            setToolTip="Create a project under the root directory, built from the\n"
            "ACTIVE workspace template (shared with Blender). Maya's own\n"
            "Project Window can customize a project but cannot build one from\n"
            "a saved template.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Mark Root As Shared Project",
            setObjectName="mark_root",
            setToolTip="Write a workspace.mel into the ROOT folder describing the layout\n"
            "it already has, so Maya and Blender both resolve it as a project.\n"
            "No files move. For the unmarked folder you just browsed to: the\n"
            "tree itself only ever lists folders that are projects already.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Save Rules As Template",
            setObjectName="save_template",
            setToolTip="Publish the ACTIVE project's file rules as a named workspace\n"
            "template: what every later New Project (in Maya or Blender)\n"
            "is built from.",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Workspace Map",
                body="Browse a directory tree of workspaces and switch between "
                "them. A workspace is a folder holding a <i>workspace.mel</i>, "
                "the shared Maya/Blender project format, so projects authored "
                "in either application show up here.",
                steps=[
                    "Enter or browse to a root directory in the "
                    "<b>Root Directory</b> field (option box ▸ for browse / "
                    "Set To Workspace / Recursive Search).",
                    "Expand the tree and <b>double-click</b> a workspace to make "
                    "it the current project (the right-click menu does the same, "
                    "plus Explore Folder).",
                    "The header menu (▾) creates a project from the active "
                    "workspace template, or publishes the current project's "
                    "rules as a template.",
                ],
                sections=[
                    (
                        "Root Directory field option box (▸)",
                        [
                            "<b>Browse…</b>: pick a root directory.",
                            "<b>Set To Workspace</b>: set the root to the current "
                            "workspace's directory.",
                            "<b>Recursive Search</b>: also discover nested "
                            "workspace folders under each child folder.",
                        ],
                    ),
                    (
                        "Header menu (▾)",
                        [
                            "<b>New Project</b>: build one under the root from the "
                            "active workspace template.",
                            "<b>Mark Root As Shared Project</b>: write a "
                            "workspace.mel describing the root folder's existing "
                            "layout, so Blender sees it as a project too.",
                            "<b>Save Rules As Template</b>: publish the active "
                            "project's rules for future New Projects.",
                        ],
                    ),
                    (
                        "Tree right-click",
                        [
                            "<b>Open Workspace</b>: make it the current project.",
                            "<b>Explore Folder</b>: open it in the file browser.",
                        ],
                    ),
                ],
            )
        )

    # ------------------------------------------------------------------ fields
    def txt000_init(self, widget):
        """The root directory field: browse, Set To Workspace, Recursive Search."""
        if not widget.is_initialized:
            self._browse_option = self.sb.BrowseOption(
                wrapped_widget=widget,
                mode="directory",
                title="Select a root directory",
                start_dir=lambda: self.engine.current_workspace,
            )
            widget.option_box.add_option(self._browse_option)
            # The field is a plain QLineEdit (no ``.menu`` of its own): the two
            # rows go in its option box, where the help says they are. The
            # objectName must NOT shadow the .ui's b001 (same dispatch and
            # state key): named after its slot instead.
            menu = widget.option_box.menu
            menu.add(
                "QPushButton",
                setText="Set To Workspace",
                setObjectName="set_to_workspace",
                setToolTip="Set the root folder to that of the current workspace.",
            )
            menu.add(
                "QCheckBox",
                setText="Recursive Search",
                setObjectName="chk000",
                setChecked=True,
                setToolTip="Also search sub-folders.",
            )
            widget.textChanged.connect(
                lambda text: self.sb.defer_with_timer(
                    lambda: self.update_current_dir(text), ms=self.ROOT_SETTLE_MS
                )
            )
        self.update_current_dir()

    def txt001_init(self, widget):
        """The workspace-name filter."""
        if not widget.is_initialized:
            widget.setPlaceholderText("Filter workspaces...")
            widget.textChanged.connect(self.filter_workspaces)

    def tree000_init(self, widget):
        """The workspace tree, its double-click and its right-click menu."""
        if not widget.is_initialized:
            widget.setColumnCount(3)
            widget.setHeaderLabels(["Workspace", "Scenes", "Size"])
            widget.setSelectionMode(self.sb.QtWidgets.QAbstractItemView.SingleSelection)
            widget.setAlternatingRowColors(True)
            # Double-click (NOT selection) switches the project: changing the
            # current project is a scene-wide side effect, so it needs a
            # deliberate gesture; arrowing through the tree must not retarget it.
            widget.itemDoubleClicked.connect(lambda *_: self.btn_open_workspace())
            widget.menu.add(
                "QPushButton",
                setText="Open Workspace",
                setObjectName="btn_open_workspace",
                setToolTip="Make the selected workspace the current project.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Explore Folder",
                setObjectName="btn_explore_folder",
                setToolTip="Open the workspace folder in the file browser.",
            )

    # ------------------------------------------------------------------ the tree
    def update_current_dir(self, text: Optional[str] = None) -> None:
        """Retarget the scan at the root field's directory (rescans only when it
        changed, or became valid again)."""
        if self._updating_directory:
            return
        self._updating_directory = True
        try:
            new_dir = os.path.normpath((text or self.ui.txt000.text()).strip())
            is_valid = os.path.isdir(new_dir)
            changed = new_dir != self.engine.current_working_dir
            self.ui.txt000.setToolTip(new_dir if is_valid else "Invalid directory")
            self.ui.txt000.set_action_color("reset" if is_valid else "invalid")
            revalidate = is_valid and (changed or self._last_dir_valid is False)
            self._last_dir_valid = is_valid
            if revalidate:
                self.engine.current_working_dir = new_dir  # rescans
                self.update_tree()
            elif not is_valid:
                self.ui.tree000.clear()
        finally:
            self._updating_directory = False

    def update_tree(self, filter_text: Optional[str] = None) -> None:
        """Rebuild the tree from the last scan, narrowed to *filter_text*."""
        self.populate_tree(self.engine.get_workspace_tree_data(filter_text))

    def populate_tree(self, tree_data: Dict) -> None:
        """Clear and refill the tree: a row per parent folder, its workspaces
        under it (name, scene count, scene size).

        The clear is part of populating: a filter keystroke that refilled
        without it appended a duplicate set of rows per character typed.
        """
        tree = self.ui.tree000
        tree.clear()
        item_class = self.sb.QtWidgets.QTreeWidgetItem
        role = self.sb.QtCore.Qt.UserRole
        for parent_name, parent_data in tree_data.items():
            parent_item = item_class(tree)
            parent_item.setText(0, parent_name)
            parent_item.setData(0, role, parent_data)
            for name, data in parent_data.get("workspaces", {}).items():
                item = item_class(parent_item)
                item.setText(0, name)
                item.setText(1, str(data.get("scene_count", 0)))
                item.setText(2, f"{data.get('size_mb', 0):.1f} MB")
                item.setData(0, role, data)
        tree.expandAll()

    def refresh_tree(self, invalidate: bool = False) -> None:
        """Refill the tree; *invalidate* rescans the root first."""
        if invalidate:
            self.engine.invalidate_workspace_data()
        self.update_tree()

    def selected_workspace(self) -> Optional[Dict]:
        """The workspace row under the tree cursor, or None (a folder row is none)."""
        item = self.ui.tree000.currentItem()
        if item is None:
            return None
        data = item.data(0, self.sb.QtCore.Qt.UserRole)
        if isinstance(data, dict) and data.get("type") == "workspace":
            return data
        return None

    def filter_workspaces(self, text) -> None:
        self.update_tree(filter_text=text)

    # ------------------------------------------------------------------ actions
    def b000(self) -> None:
        """Browse for the root directory."""
        if self._browse_option is not None:
            self._browse_option.browse()
            return
        start_dir = self.ui.txt000.text()
        if not os.path.isdir(start_dir):
            start_dir = self.engine.current_workspace
        picked = self.sb.dir_dialog("Select a root directory", start_dir=start_dir)
        if picked:
            self.ui.txt000.setText(picked)

    def b001(self) -> None:
        """Set to Workspace."""
        self.set_to_workspace()

    def b002(self) -> None:
        """Refresh: rescan the root."""
        self.refresh_tree(invalidate=True)

    def set_to_workspace(self) -> None:
        """Set the root to the current workspace's folder."""
        self.ui.txt000.setText(self.engine.current_workspace)

    def chk000(self, checked) -> None:
        """Recursive Search: rescan when it changes."""
        if self._updating_directory:
            return
        # ``toggled`` sends a bool, ``stateChanged`` a Qt.CheckState (2: checked).
        # The bool goes first: it IS an int, and ``True == 2`` is False.
        checked = checked if isinstance(checked, bool) else checked == 2
        if self.engine.recursive_search == checked:
            return
        self.engine.recursive_search = checked
        self.refresh_tree(invalidate=True)

    def btn_open_workspace(self) -> None:
        """Make the selected workspace the current project."""
        path = (self.selected_workspace() or {}).get("path")
        if not (path and os.path.isdir(path)):
            return
        opened = self.tk.EnvUtils.set_current_workspace(path)
        if opened:
            self.sb.message_box(f"Workspace set to:<br>{opened}")

    def btn_explore_folder(self) -> None:
        """Open the selected workspace's folder in the file browser."""
        path = (self.selected_workspace() or {}).get("path")
        if path and os.path.isdir(path):
            ptk.FileUtils.open_explorer(path, logger=self.logger)

    # ------------------------------------------------------------------ projects
    def new_project(self) -> None:
        """Create a project under the root from the ACTIVE template."""
        name = (self.sb.input_dialog("New Project", "Project folder name:", "") or "").strip()
        if not name:
            return
        try:
            ws = self.engine.create_project(name)
        except OSError as e:
            self.sb.message_box(str(e))
            return
        self.refresh_tree()
        if ws is not None:
            self.sb.message_box(f"Created project:<br>{ws.root}")

    def mark_root(self) -> None:
        """Mark the ROOT directory as a shared Maya/Blender project."""
        root = self.engine.current_working_dir
        if ptk.Workspace(root).is_marked:
            self.sb.message_box(
                f"<hl>{os.path.basename(os.path.normpath(root))}</hl> is already a project."
            )
            return
        try:
            ws = self.engine.mark_root_as_project()
        except OSError as e:
            self.sb.message_box(str(e))
            return
        if ws is None:
            self.sb.message_box("Set a valid root directory first.")
            return
        self.refresh_tree()
        self.sb.message_box(f"Marked as a shared project:<br>{ws.root}")

    def save_template(self) -> None:
        """Publish the ACTIVE project's file rules as a named workspace template."""
        name = (self.sb.input_dialog("Save Template", "Template name:", "") or "").strip()
        if not name:
            return
        try:
            saved = self.tk.EnvUtils.save_workspace_template(name)
        except ValueError as e:
            self.sb.message_box(str(e))
            return
        self.sb.message_box(f"Saved template <hl>{saved}</hl>: new projects build from it.")
