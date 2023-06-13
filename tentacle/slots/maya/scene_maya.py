# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Scene_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def t000_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Ignore Case",
            setObjectName="chk000",
            setToolTip="Search case insensitive.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Regular Expression",
            setObjectName="chk001",
            setToolTip="When checked, regular expression syntax is used instead of the default '*' and '|' wildcards.",
        )

    def tb000_init(self, widget):
        """ """
        widget.option_menu.add(
            "QComboBox",
            addItems=["capitalize", "upper", "lower", "swapcase", "title"],
            setObjectName="cmb001",
            setToolTip="Set desired python case operator.",
        )

    def tb001_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Alphanumeric",
            setObjectName="chk005",
            setToolTip="When True use an alphanumeric character as a suffix when there is less than 26 objects else use integers.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Strip Trailing Integers",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Strip any trailing integers. ie. '123' of 'cube123'",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Strip Trailing Alphanumeric",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Strip any trailing uppercase alphanumeric chars that are prefixed with an underscore.  ie. 'A' of 'cube_A'",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Reverse",
            setObjectName="chk004",
            setToolTip="Reverse the naming order. (Farthest object first)",
        )

    def tb000(self, widget):
        """Convert Case"""
        case = widget.option_menu.cmb001.currentText()

        selection = pm.ls(sl=1)
        objects = selection if selection else pm.ls(objectsOnly=1)
        mtk.Edit.set_case(objects, case)

    def tb001(self, widget):
        """Convert Case"""
        alphanumeric = widget.option_menu.chk005.isChecked()
        strip_trailing_ints = widget.option_menu.chk002.isChecked()
        strip_trailing_alpha = widget.option_menu.chk003.isChecked()
        reverse = widget.option_menu.chk004.isChecked()

        selection = pm.ls(sl=1, objectsOnly=1, type="transform")
        mtk.Edit.append_location_based_suffix(
            selection,
            alphanumeric=alphanumeric,
            strip_trailing_ints=strip_trailing_ints,
            strip_trailing_alpha=strip_trailing_alpha,
            reverse=reverse,
        )

    def b000(self):
        """Rename"""
        find = (
            self.sb.scene.t000.text()
        )  # an asterisk denotes startswith*, *endswith, *contains*
        to = self.sb.scene.t001.text()
        regex = self.sb.scene.t000.option_menu.chk001.isChecked()
        ignore_case = self.sb.scene.t000.option_menu.chk000.isChecked()

        selection = pm.ls(sl=1)
        objects = selection if selection else pm.ls(objectsOnly=1)
        mtk.Edit.rename(objects, to, find, regex=regex, ignore_case=ignore_case)


# --------------------------------------------------------------------------------------------


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
