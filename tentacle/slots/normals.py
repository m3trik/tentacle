# !/usr/bin/python
# coding=utf-8
"""Normals: one Slots class for both hosts.

Every operation is the host toolkit's ``Components`` (``self.tk``), given
``None`` for the selection; each is one undo step in its host. With nothing
selected, an operation returns ``[]`` without running (``CoreUtils.selected``).
"""

from tentacle import Slots


class NormalsSlots(Slots):
    #: Shown when an operation ran on an empty selection (it returned ``[]``).
    NOTHING_SELECTED = (
        "<b>Nothing selected.</b><br>"
        "The operation requires at least one selected object."
    )

    def _report(self, result):
        """Say so when *result* is the ``[]`` of an empty selection; for these
        operations a run returns ``None``."""
        if result == []:
            self.sb.message_box(self.NOTHING_SELECTED)

    def tb001_init(self, widget):
        """Initialize Set Normals By Angle"""
        menu = widget.option_box.menu
        menu.setTitle("Set Normals By Angle")
        menu.add(
            "QSpinBox",
            setPrefix="Angle Threshold: ",
            setObjectName="s002",
            set_limits=[0, 180],
            setValue=90,
            setToolTip="Edges at or above this angle (degrees) take Upper Hardness; "
            "edges below it, Lower Hardness.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Upper Hardness: ",
            setObjectName="s003",
            set_limits=[-1, 180],
            setValue=0,
            setToolTip="The hardness for edges at or above the threshold.\n"
            "0, the edges appear hard.\n180, they appear soft.\n-1, they are left as they are.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Lower Hardness: ",
            setObjectName="s004",
            set_limits=[-1, 180],
            setValue=180,
            setToolTip="The hardness for edges below the threshold.\n"
            "0, the edges appear hard.\n180, they appear soft.\n-1, they are left as they are.",
        )
        menu.add(
            "QCheckBox",
            setText="Unlock Normals",
            setObjectName="chk_unlock_normals",
            setChecked=True,
            setToolTip="Unlock the normals before applying hardness.\n"
            "Required for imported assets (FBX/Marmoset): locked normals\n"
            "silently block the smoothing update.\n"
            "When off, meshes with locked normals are left untouched and named.",
        )

    def tb001(self, widget):
        """Set Normals By Angle"""
        menu = widget.option_box.menu
        upper = menu.s003.value()
        lower = menu.s004.value()
        locked = self.tk.Components.set_edge_hardness(
            None,
            menu.s002.value(),
            upper if upper > -1 else None,  # -1 leaves that bucket as it is
            lower if lower > -1 else None,
            unlock_normals=menu.chk_unlock_normals.isChecked(),
        )
        if locked:
            names = "<br>".join(str(o).rsplit("|", 1)[-1] for o in locked)
            self.sb.message_box(
                "<b>Locked normals detected</b><br><br>"
                "These objects have locked normals, which silently "
                "block the smoothing update:<br><br>"
                f'<font style="color: Yellow;">{names}</font><br><br>'
                "Enable <b>Unlock Normals</b> in the option box, then run again."
            )

    def tb004_init(self, widget):
        """Initialize Average Normals"""
        menu = widget.option_box.menu
        menu.setTitle("Average Normals")
        menu.add(
            "QCheckBox",
            setText="By UV Shell",
            setObjectName="chk003",
            setToolTip="Average the normals within each UV shell on its own: "
            "UV-shell borders stay hard.",
        )

    def tb004(self, widget):
        """Average Normals"""
        self._report(
            self.tk.Components.average_normals(
                None, by_uv_shell=widget.option_box.menu.chk003.isChecked()
            )
        )

    def b000(self):
        """Soften Edge Normals"""
        self._report(self.tk.Components.set_edge_softness(None, soft=True))

    def b001(self):
        """Harden Edge Normals"""
        self._report(self.tk.Components.set_edge_softness(None, soft=False))

    def b002(self):
        """Transfer Normals: from the first selected (Maya) or active (Blender)
        mesh to the other selected meshes."""
        try:
            result = self.tk.Components.transfer_normals(None)
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        if result == []:
            self.sb.message_box(
                "Select a source object and one or more target objects."
            )

    def b004(self):
        """Toggle lock/unlock normals."""
        locked = self.tk.Components.toggle_normal_lock(None)
        if locked is True:
            self.sb.message_box("Normals <hl>Locked</hl>.")
        elif locked is False:
            self.sb.message_box("Normals <hl>Unlocked</hl>.")
        else:
            self.sb.message_box("Un/Lock Normals requires a mesh selection.")

    def b006(self):
        """Set To Face: vertex normals follow their faces (faceted shading)."""
        self._report(self.tk.Components.set_to_face_normals(None))

    def tb010_init(self, widget):
        """Initialize Reverse Normals: Maya's five ``polyNormal`` modes, in both
        hosts."""
        if not widget.is_initialized:
            widget.option_box.menu.setTitle("Reverse Normals")
            widget.option_box.menu.add(
                "QComboBox",
                setObjectName="cmb000",
                addItems=[
                    "Reverse",
                    "Propagate",
                    "Conform",
                    "Reverse and Extract",
                    "Reverse and Propagate",
                ],
                setCurrentIndex=3,
                setToolTip="Normal operation mode.",
            )

    def tb010(self, widget):
        """Reverse Normals"""
        self._report(
            self.tk.Components.reverse_normals(
                None, mode=widget.option_box.menu.cmb000.currentIndex()
            )
        )
