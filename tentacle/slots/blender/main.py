# !/usr/bin/python
# coding=utf-8
import os

import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class Main(SlotsBlender):
    """Blender port of the shared ``main`` start menu — a directory browser of the
    current file's folder.

    Maya browses the *project workspace* (a structured tree of sub-folders); Blender has
    no project concept, so the equivalent is simply the **current ``.blend``'s directory
    contents** — its sub-folders (expandable) and files (a file opens in its default app,
    a ``.blend`` in Blender; a folder opens in the system browser). ``btk.get_env_info
    ('workspace')`` resolves to the saved ``.blend``'s directory; the list hides for an
    unsaved file.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.main

    def list000_init(self, widget):
        """Initialize Workspace Browser"""
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True
        widget.fixed_item_height = 18
        widget.apply_preset("expand_down")

        workspace = btk.get_env_info("workspace")
        workspace_dir = btk.get_env_info("workspace_dir")

        if not workspace or not os.path.isdir(workspace):
            # Unsaved .blend → no folder to browse. Show a hint row rather than
            # an invisible list (which reads as "broken"); Blender, unlike Maya,
            # has no default project so this is the common just-launched state.
            widget.add("Save the .blend to browse its folder")  # no data → inert
            widget.setVisible(True)
            return

        w = widget.add(workspace_dir, data=workspace)
        w.sublist.setMinimumWidth(widget.width())
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
        """Workspace Browser — open the clicked entry: a file in its default app
        (a ``.blend`` opens Blender), a folder in the system file browser."""
        data = item.item_data()
        if data and os.path.exists(str(data)):
            os.startfile(str(data))
            self.sb.handlers.marking_menu.hide()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
