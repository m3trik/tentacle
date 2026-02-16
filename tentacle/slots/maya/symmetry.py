# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya._slots_maya import SlotsMaya


class Symmetry(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = self.sb.loaded_ui.symmetry
        self.submenu = self.sb.loaded_ui.symmetry_submenu

    def chk000_init(self, widget):
        """Set initial symmetry state"""
        self.sb.create_button_groups(widget.ui, "chk000-2", allow_deselect=True)
        state = pm.symmetricModelling(query=True, symmetry=True)
        axis = pm.symmetricModelling(query=True, axis=True)
        w = "chk000" if axis == "x" else "chk001" if axis == "y" else "chk002"
        getattr(widget.ui, w).setChecked(state)

    def chk000(self, state, widget):
        """Symmetry X"""
        pm.symmetricModelling(edit=True, symmetry=bool(state), axis="x")

    def chk001(self, state, widget):
        """Symmetry Y"""
        pm.symmetricModelling(edit=True, symmetry=bool(state), axis="y")

    def chk002(self, state, widget):
        """Symmetry Z"""
        pm.symmetricModelling(edit=True, symmetry=bool(state), axis="z")

    def chk005_init(self, widget):
        """Set symmetry reference space"""
        self.sb.create_button_groups(widget.ui, "chk004-5")

    def chk005(self, state, widget):
        """Symmetry: Topo"""
        if state:
            self.sb.toggle_multi(self.ui, setDisabled="chk000-2")

            selected_edges = pm.filterExpand(selectionMask=32)
            if not selected_edges:
                self.ui.chk004.setChecked(True)
                self.sb.message_box("First select an edge.")
                return

            try:
                pm.symmetricModelling(edit=True, symmetry=bool(state), about="topo")
            except RuntimeError:
                self.sb.message_box(
                    "Topological symmetry cannot be activated.\nYou must select a seam edge before activation can occur."
                )
        else:
            self.sb.toggle_multi(self.ui, setEnabled="chk000-2")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
