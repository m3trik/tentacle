# !/usr/bin/python
# coding=utf-8
"""Crease: one Slots class for both hosts.

Every operation is the host toolkit's ``Components`` (``self.tk``), given
``None`` for the selection; each is one undo step in its host. Maya creases
with ``polyCrease`` / ``polySoftEdge``; Blender sets the Subdivision Surface
edge crease and the edges' smooth flag. In component mode (Maya) or Edit Mode
(Blender) the selected edges are creased, otherwise every edge of the selected
meshes.
"""

from tentacle import Slots


class CreaseSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.crease
        self.submenu = self.sb.loaded_ui.crease_submenu

    def tb000_init(self, widget):
        """Initialize Crease: the amount and the optional smoothing angle."""
        menu = widget.option_box.menu
        menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[0, 10],
            setValue=10,
            setToolTip="The crease applied to the selected edges: "
            "0 (no crease) to 10 (full crease).",
        )
        menu.add(
            "QCheckBox",
            setText="Set Smoothing Angle",
            setObjectName="chk000",
            setToolTip="Also soften or harden the creased edges by their angle. "
            "Enables the Angle field.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Angle: ",
            setObjectName="s004",
            set_limits=[0, 180],
            setValue=30,
            setDisabled=True,
            setToolTip="Smoothing angle (degrees): an edge whose angle exceeds it "
            "is hardened, the rest softened (0: all hard, 180: all soft).\n"
            "Only active when 'Set Smoothing Angle' is checked.",
        )
        menu.chk000.toggled.connect(menu.s004.setEnabled)
        # Self-labelling: the amount lives in the option box, so the button says it.
        self.sb.text_from(menu, widget, "s003", "Crease {}".format)

    def tb000(self, widget):
        """Crease: crease the selected edges (subdivision sharpness), softening or
        hardening them by angle when the option box asks for it."""
        menu = widget.option_box.menu
        angle = menu.s004.value() if menu.chk000.isChecked() else None
        creased = self.tk.Components.crease_edges(
            None, amount=menu.s003.value(), angle=angle
        )
        if not creased:
            self.sb.message_box("Crease requires an edge or mesh selection.")

    def b002(self, widget):
        """Transfer Crease Edges: from the first selected (Maya) or active (Blender)
        mesh to the other selected meshes."""
        try:
            targets = self.tk.Components.transfer_creased_edges(None)
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        if targets == []:
            self.sb.message_box(
                "Select a source object and one or more target objects."
            )
