# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Duplicate(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.duplicate.draggableHeader.ctx_menu
        if not ctx.contains_items:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.duplicate.draggableHeader

    def radialArray(self):
        """Radial Array: Reset"""
        self.chk015()  # calling chk015 directly from valueChanged would pass the returned spinbox value to the create arg

    def duplicateArray(self):
        """Duplicate: Reset"""
        self.chk016()  # calling chk015 directly from valueChanged would pass the returned spinbox value to the create arg

    def chk007(self, state=None):
        """Duplicate: Translate To Components"""
        if self.sb.duplicate_linear.chk007.isChecked():
            self.sb.toggle_widgets(
                setEnabled="chk008,b034,cmb001", setDisabled="chk000,chk009,s005"
            )
            self.b008()
        else:
            self.sb.toggle_widgets(
                setDisabled="chk008,b034,cmb001", setEnabled="chk000,chk009,s005"
            )

    def chk011(self, state=None):
        """Radial Array: Instance/Duplicate Toggle"""
        self.chk015()  # calling chk015 directly from valueChanged would pass the returned spinbox value to the create arg

    def chk012(self, state=None):
        """Radial Array: X Axis"""
        self.sb.toggle_widgets(setChecked="chk012", setUnChecked="chk013,chk014")
        self.chk015()

    def chk013(self, state=None):
        """Radial Array: Y Axis"""
        self.sb.toggle_widgets(setChecked="chk013", setUnChecked="chk012,chk014")
        self.chk015()

    def chk014(self, state=None):
        """Radial Array: Z Axis"""
        self.sb.toggle_widgets(setChecked="chk014", setUnChecked="chk012,chk013")
        self.chk015()

    def b002(self):
        """Duplicate: Create"""
        self.sb.duplicate_linear.chk016.setChecked(
            False
        )  # must be in the false unchecked state to catch the create flag in chk015
        self.chk016(create=True)

    def b003(self):
        """Radial Array: Create"""
        self.sb.duplicate_radial.chk015.setChecked(
            False
        )  # must be in the false unchecked state to catch the create flag in chk015
        self.chk015(create=True)

    def b006(self):
        """ """
        self.sb.parent().set_ui("duplicate_linear")
        self.sb.duplicate_linear.s002.valueChanged.connect(
            self.duplicateArray
        )  # update duplicate array
        self.sb.duplicate_linear.s003.valueChanged.connect(self.duplicateArray)
        self.sb.duplicate_linear.s004.valueChanged.connect(self.duplicateArray)
        self.sb.duplicate_linear.s005.valueChanged.connect(self.duplicateArray)
        self.sb.duplicate_linear.s007.valueChanged.connect(self.duplicateArray)
        self.sb.duplicate_linear.s008.valueChanged.connect(self.duplicateArray)
        self.sb.duplicate_linear.s009.valueChanged.connect(self.duplicateArray)
        self.sb.duplicate_linear.s010.valueChanged.connect(self.duplicateArray)
        self.sb.duplicate_linear.s011.valueChanged.connect(self.duplicateArray)
        self.sb.duplicate_linear.s012.valueChanged.connect(self.duplicateArray)

    def b007(self):
        """ """
        self.sb.parent().set_ui("duplicate_radial")
        self.sb.duplicate_radial.s000.valueChanged.connect(
            self.radialArray
        )  # update radial array
        self.sb.duplicate_radial.s001.valueChanged.connect(self.radialArray)

    def b008(self):
        """Add Selected Components To cmb001"""
        cmb = self.sb.duplicate_linear.cmb001

        selection = pm.ls(selection=1, flatten=1)

        for obj in selection:
            cmb.add(obj)
