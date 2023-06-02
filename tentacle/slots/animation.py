# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Animation(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.animation.draggableHeader.ctx_menu
        if not ctx.contains_items:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

        ctx = self.sb.animation.tb000.option_menu
        if not ctx.contains_items:
            ctx.add(
                "QSpinBox",
                setPrefix="Frame: ",
                setObjectName="s000",
                set_limits="0-10000 step1",
                setValue=1,
                setToolTip="",
            )
            ctx.add(
                "QCheckBox",
                setText="Relative",
                setObjectName="chk000",
                setChecked=True,
                setToolTip="",
            )
            ctx.add(
                "QCheckBox",
                setText="Update",
                setObjectName="chk001",
                setChecked=True,
                setToolTip="",
            )

        ctx = self.sb.animation.tb001.option_menu
        if not ctx.contains_items:
            ctx.add(
                "QSpinBox",
                setPrefix="Time: ",
                setObjectName="s001",
                set_limits="0-10000 step1",
                setValue=1,
                setToolTip="The desired start time for the inverted keys.",
            )
            ctx.add(
                "QCheckBox",
                setText="Relative",
                setObjectName="chk002",
                setChecked=False,
                setToolTip="Start time position as relative or absolute.",
            )

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.animation.draggableHeader

    def tb000(self, state=None):
        """Set Current Frame"""
        tb = self.sb.animation.tb000

        frame = self.sb.invert_on_modifier(tb.option_menu.s000.value())
        relative = tb.option_menu.chk000.isChecked()
        update = tb.option_menu.chk001.isChecked()

        self.setCurrentFrame(frame, relative=relative, update=update)

    def tb001(self, state=None):
        """Invert Selected Keyframes"""
        tb = self.sb.animation.tb001

        time = tb.option_menu.s001.value()
        relative = tb.option_menu.chk002.isChecked()

        self.invertSelectedKeyframes(time=time, relative=relative)
