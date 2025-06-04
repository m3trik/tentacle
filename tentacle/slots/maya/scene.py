# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from uitk import Signals
from tentacle.slots.maya import SlotsMaya


class Scene(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.scene
        self.submenu = self.sb.loaded_ui.scene_submenu

    def txt000_init(self, widget):
        """ """
        widget.menu.setTitle("Find")
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

    @Signals("returnPressed")
    def txt000(self, widget):
        """Find"""
        # An asterisk denotes startswith*, *endswith, *contains*
        regex = widget.ui.txt000.menu.chk001.isChecked()
        ign_case = widget.ui.txt000.menu.chk000.isChecked()

        text = widget.text()
        if text:
            obj_names = [str(i) for i in pm.ls()]
            found = ptk.find_str(text, obj_names, regex=regex, ignore_case=ign_case)
            pm.select(found)

    def txt001_init(self, widget):
        """ """
        widget.menu.setTitle("Rename")
        widget.menu.add(
            "QCheckBox",
            setText="Retain Suffix",
            setObjectName="chk002",
            setToolTip="Retain the suffix of the selected object(s).",
        )

    # The LineEdit text parameter is not emitted on `returnPressed`
    @Signals("returnPressed")
    def txt001(self, widget):
        """Rename"""
        # An asterisk denotes startswith*, *endswith, *contains*
        find = widget.ui.txt000.text()
        to = widget.text()
        regex = widget.ui.txt000.menu.chk001.isChecked()
        ign_case = widget.ui.txt000.menu.chk000.isChecked()
        retain_suffix = widget.ui.txt001.menu.chk002.isChecked()

        selection = pm.selected() or pm.ls()
        mtk.Naming.rename(
            selection,
            to,
            find,
            regex=regex,
            ignore_case=ign_case,
            retain_suffix=retain_suffix,
        )

    def tb000_init(self, widget):
        """ """
        widget.menu.setTitle("Convert Case")
        widget.menu.add(
            "QComboBox",
            addItems=["capitalize", "upper", "lower", "swapcase", "title"],
            setObjectName="cmb001",
            setToolTip="Set desired python case operator.",
        )

    def tb000(self, widget):
        """Convert Case"""
        case = widget.menu.cmb001.currentText()

        selection = pm.ls(sl=1)
        objects = selection if selection else pm.ls(objectsOnly=1)
        mtk.Naming.set_case(objects, case)

    def tb001_init(self, widget):
        """ """
        widget.menu.setTitle("Suffix By Location")
        widget.menu.add(
            "QCheckBox",
            setText="First Object As Reference",
            setObjectName="chk006",
            setToolTip="Use the first selected object as the reference point, otherwise the scene origin (0,0,0) will be used.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Alphabetical",
            setObjectName="chk005",
            setToolTip="Use an alphabet character as a suffix when there is less than 26 objects, else use integers.",
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
            setText="Strip Trailing Alphabetical",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Strip any trailing uppercase alphabet chars that are prefixed with an underscore.  ie. 'A' of 'cube_A'",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Reverse",
            setObjectName="chk004",
            setToolTip="Reverse the naming order. (Farthest object first)",
        )

    def tb001(self, widget):
        """Suffix By Location"""
        first_obj_as_ref = widget.menu.chk006.isChecked()
        alphabetical = widget.menu.chk005.isChecked()
        strip_trailing_ints = widget.menu.chk002.isChecked()
        strip_trailing_alpha = widget.menu.chk003.isChecked()
        reverse = widget.menu.chk004.isChecked()

        selection = pm.ls(sl=True, objectsOnly=True, type="transform")
        mtk.Naming.append_location_based_suffix(
            selection,
            first_obj_as_ref=first_obj_as_ref,
            alphabetical=alphabetical,
            strip_trailing_ints=strip_trailing_ints,
            strip_trailing_alpha=strip_trailing_alpha,
            reverse=reverse,
        )

    def tb002_init(self, widget):
        """ """
        widget.menu.setTitle("Strip Chars")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Num Chars:",
            setObjectName="s000",
            setValue=1,
            setToolTip="The number of characters to delete.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Trailing",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Whether to delete characters from the rear of the name.",
        )

    def tb002(self, widget):
        """Strip Chars"""
        sel = pm.selected()
        kwargs = {
            "num_chars": widget.menu.s000.value(),
            "trailing": widget.menu.chk005.isChecked(),
        }
        mtk.Naming.strip_chars(sel, **kwargs)

    def tb003_init(self, widget):
        """ """
        widget.menu.setTitle("Suffix By Type")
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Group Suffix",
            setText="_GRP",
            setObjectName="tb003_txt000",
            setToolTip="Suffix for transform groups.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Locator Suffix",
            setText="_LOC",
            setObjectName="tb003_txt001",
            setToolTip="Suffix for locators.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Joint Suffix",
            setText="_JNT",
            setObjectName="tb003_txt002",
            setToolTip="Suffix for joints.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Mesh Suffix",
            setText="_GEO",
            setObjectName="tb003_txt003",
            setToolTip="Suffix for meshes.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Nurbs Curve Suffix",
            setText="_CRV",
            setObjectName="tb003_txt004",
            setToolTip="Suffix for nurbs curves.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Camera Suffix",
            setText="_CAM",
            setObjectName="tb003_txt005",
            setToolTip="Suffix for cameras.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Light Suffix",
            setText="_LGT",
            setObjectName="tb003_txt006",
            setToolTip="Suffix for lights.",
        )
        widget.menu.add(
            "QLineEdit",
            setPlaceholderText="Display Layer Suffix",
            setText="_LYR",
            setObjectName="tb003_txt007",
            setToolTip="Suffix for display layers.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Strip Trailing Integers",
            setObjectName="tb003_chk002",
            setChecked=True,
            setToolTip="Strip any trailing integers. ie. '123' of 'cube123'",
        )

    def tb003(self, widget):
        """Suffix By Type"""
        objects = pm.ls(sl=True, objectsOnly=True)

        kwargs = {
            "group_suffix": widget.menu.tb003_txt000.text(),
            "locator_suffix": widget.menu.tb003_txt001.text(),
            "joint_suffix": widget.menu.tb003_txt002.text(),
            "mesh_suffix": widget.menu.tb003_txt003.text(),
            "nurbs_curve_suffix": widget.menu.tb003_txt004.text(),
            "camera_suffix": widget.menu.tb003_txt005.text(),
            "light_suffix": widget.menu.tb003_txt006.text(),
            "display_layer_suffix": widget.menu.tb003_txt007.text(),
            "strip_trailing_ints": widget.menu.tb003_chk002.isChecked(),
        }
        mtk.Naming.suffix_by_type(objects, **kwargs)


# --------------------------------------------------------------------------------------------


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
