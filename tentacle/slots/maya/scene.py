# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from uitk import signals
from tentacle.slots.maya import SlotsMaya


class Scene(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def txt000_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Ignore Case",
            setObjectName="chk000",
            setToolTip="Search case insensitive.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Regular Expression",
            setObjectName="chk001",
            setToolTip="When checked, regular expression syntax is used instead of the default '*' and '|' wildcards.",
        )

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QComboBox",
            addItems=["capitalize", "upper", "lower", "swapcase", "title"],
            setObjectName="cmb001",
            setToolTip="Set desired python case operator.",
        )

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Alphanumeric",
            setObjectName="chk005",
            setToolTip="When True use an alphanumeric character as a suffix when there is less than 26 objects else use integers.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Strip Trailing Integers",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Strip any trailing integers. ie. '123' of 'cube123'",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Strip Trailing Alphanumeric",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Strip any trailing uppercase alphanumeric chars that are prefixed with an underscore.  ie. 'A' of 'cube_A'",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Reverse",
            setObjectName="chk004",
            setToolTip="Reverse the naming order. (Farthest object first)",
        )

    def txt000(self, text, widget):
        """Select By Name"""
        # An asterisk denotes startswith*, *endswith, *contains*
        if text:
            pm.select(pm.ls(text))

    # The LineEdit text parameter is not emitted on `returnPressed`
    @signals("returnPressed")
    def txt001(self, widget):
        """Rename"""
        # An asterisk denotes startswith*, *endswith, *contains*
        find = widget.ui.txt000.text()
        to = widget.text()
        regex = widget.ui.txt000.menu.chk001.isChecked()
        ignore_case = widget.ui.txt000.menu.chk000.isChecked()

        selection = pm.ls(sl=1, objectsOnly=True)
        mtk.rename(selection, to, find, regex=regex, ignore_case=ignore_case)

    def tb000(self, widget):
        """Convert Case"""
        case = widget.menu.cmb001.currentText()

        selection = pm.ls(sl=1)
        objects = selection if selection else pm.ls(objectsOnly=1)
        mtk.set_case(objects, case)

    def tb001(self, widget):
        """Convert Case"""
        alphanumeric = widget.menu.chk005.isChecked()
        strip_trailing_ints = widget.menu.chk002.isChecked()
        strip_trailing_alpha = widget.menu.chk003.isChecked()
        reverse = widget.menu.chk004.isChecked()

        selection = pm.ls(sl=1, objectsOnly=1, type="transform")
        mtk.append_location_based_suffix(
            selection,
            alphanumeric=alphanumeric,
            strip_trailing_ints=strip_trailing_ints,
            strip_trailing_alpha=strip_trailing_alpha,
            reverse=reverse,
        )


# --------------------------------------------------------------------------------------------


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
