# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
from tentacle.slots.maya._slots_maya import SlotsMaya


class Symmetry(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = self.sb.loaded_ui.symmetry
        self.submenu = self.sb.loaded_ui.symmetry_submenu

    def _report_symmetry_state(self):
        """When symmetry is active, surface it as ``Symmetry: <space> <axis>`` (axis
        highlighted); stay silent when it's off. Querying the scene rather than trusting
        the ``state`` arg keeps the feedback accurate through the radio deselect cascade."""
        if not cmds.symmetricModelling(query=True, symmetry=True):
            return
        about = cmds.symmetricModelling(query=True, about=True) or ""
        if about == "topo":
            self.sb.message_box("Symmetry: <hl>Topological</hl>")
            return
        axis = (cmds.symmetricModelling(query=True, axis=True) or "").upper()
        self.sb.message_box(f"Symmetry: {about.capitalize() or 'Object'} <hl>{axis}</hl>")

    def chk000_init(self, widget):
        """Set initial symmetry state"""
        self.sb.create_button_groups(widget.ui, "chk000-2", allow_deselect=True)
        state = cmds.symmetricModelling(query=True, symmetry=True)
        axis = cmds.symmetricModelling(query=True, axis=True)
        w = "chk000" if axis == "x" else "chk001" if axis == "y" else "chk002"
        getattr(widget.ui, w).setChecked(state)

    def chk000(self, state, widget):
        """Symmetry X: toggle modeling symmetry across the X axis."""
        cmds.symmetricModelling(edit=True, symmetry=bool(state), axis="x")
        self._report_symmetry_state()

    def chk001(self, state, widget):
        """Symmetry Y: toggle modeling symmetry across the Y axis."""
        cmds.symmetricModelling(edit=True, symmetry=bool(state), axis="y")
        self._report_symmetry_state()

    def chk002(self, state, widget):
        """Symmetry Z: toggle modeling symmetry across the Z axis."""
        cmds.symmetricModelling(edit=True, symmetry=bool(state), axis="z")
        self._report_symmetry_state()

    def chk004(self, state, widget):
        """Symmetry: Object space (radio partner of Topo; only acts when selected —
        deselection means Topo took over and sets about='topo' itself)."""
        if state:
            cmds.symmetricModelling(edit=True, about="object")
            self._report_symmetry_state()

    def chk005_init(self, widget):
        """Set symmetry reference space"""
        self.sb.create_button_groups(widget.ui, "chk004-5")

    def chk005(self, state, widget):
        """Symmetry: Topo"""
        if state:
            self.sb.toggle_multi(self.ui, setDisabled="chk000-2")

            selected_edges = cmds.filterExpand(selectionMask=32)
            if not selected_edges:
                self.ui.chk004.setChecked(True)
                self.sb.message_box("<hl>Select an edge first</hl> to seed topological symmetry.")
                return

            try:
                cmds.symmetricModelling(edit=True, symmetry=bool(state), about="topo")
            except RuntimeError:
                self.ui.chk004.setChecked(True)
                self.sb.message_box(
                    "Topological symmetry <hl>could not be activated</hl>.<br>"
                    "Select a <hl>seam edge</hl> before activation."
                )
                return
        else:
            self.sb.toggle_multi(self.ui, setEnabled="chk000-2")

        self._report_symmetry_state()


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
