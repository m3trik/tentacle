# !/usr/bin/python
# coding=utf-8
import os

try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from uitk import Signals
from tentacle.slots.maya._slots_maya import SlotsMaya


class Main(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.main

    def list000_init(self, widget):
        """Initialize Workspace Browser"""
        widget.clear()
        if not widget.is_initialized:
            widget.refresh_on_show = True
        widget.fixed_item_height = 18
        widget.apply_preset("expand_down")

        workspace = mtk.get_env_info("workspace")
        workspace_dir = mtk.get_env_info("workspace_dir")

        if not workspace or not os.path.isdir(workspace):
            widget.setVisible(False)
            return

        w = widget.add(workspace_dir, data=workspace)
        w.sublist.setMinimumWidth(widget.width())
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
        """Workspace Browser"""
        data = item.item_data()
        if data and os.path.isdir(str(data)):
            os.startfile(str(data))
            self.sb.handlers.marking_menu.hide()


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
