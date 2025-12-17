# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Create(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.create
        self.submenu = self.sb.loaded_ui.create_submenu

    def cmb001_init(self, widget):
        """ """
        items = ["Polygon", "NURBS", "Light", "Control"]
        widget.add(items)

        widget.currentIndexChanged.connect(
            lambda i, w=widget: self.cmb002_init(w.ui.cmb002)
        )

    def cmb002_init(self, widget):
        """ """
        index = widget.ui.cmb001.currentIndex()

        if index == 1:
            items = [
                "Cube",
                "Sphere",
                "Cylinder",
                "Cone",
                "Plane",
                "Torus",
                "Circle",
                "Square",
            ]

        elif index == 2:
            items = ["Ambient", "Directional", "Point", "Spot", "Area", "Volume"]

        elif index == 3:
            items = [
                "Circle",
                "Square",
                "Diamond",
                "Arrow",
                "Two Way Arrow",
                "Four Way Arrow",
                "Chevron Left",
                "Chevron Right",
                "Target",
                "Secondary",
                "Box",
                "Ball",
            ]

        else:  # Default to polygon  primitives.
            items = [
                "Cube",
                "Sphere",
                "Cylinder",
                "Plane",
                "Circle",
                "Cone",
                "Pyramid",
                "Torus",
                "Tube",
                "GeoSphere",
                "Platonic Solids",
                "Text",
            ]

        widget.add(items, clear=True)

    def tb000_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Move the created object to the center point of any selected object(s).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Uniformly scale the created object to match the averaged scale of any selected object(s).",
        )

    def tb000(self, widget):
        """Create Primitive"""
        baseType = self.ui.cmb001.currentText()
        subType = self.ui.cmb002.currentText()
        scale = widget.option_box.menu.chk001.isChecked()
        translate = widget.option_box.menu.chk000.isChecked()

        if baseType == "Control":
            self._create_control(subType)
        else:
            hist_node = mtk.Primitives.create_default_primitive(
                baseType, subType, scale=scale, translate=translate
            )
            pm.selectMode(object=True)  # place scene select type in object mode.
            pm.select(
                hist_node
            )  # select the transform node so that you can see any edits

    def _create_control(self, subType):
        """Create a NURBS control curve."""
        # Map UI names to preset names and optional kwargs
        control_map = {
            "Circle": ("circle", {}),
            "Square": ("square", {}),
            "Diamond": ("diamond", {}),
            "Arrow": ("arrow", {}),
            "Two Way Arrow": ("two_way_arrow", {}),
            "Four Way Arrow": ("four_way_arrow", {}),
            "Chevron Left": ("chevron", {"direction": "left"}),
            "Chevron Right": ("chevron", {"direction": "right"}),
            "Target": ("target", {}),
            "Secondary": ("secondary", {}),
            "Box": ("box", {}),
            "Ball": ("ball", {}),
        }

        if subType in control_map:
            preset, kwargs = control_map[subType]
            ctrl = mtk.Controls.create(preset, name=subType.replace(" ", ""), **kwargs)
            pm.select(ctrl)

    def b001(self):
        """Create poly cube"""
        mtk.Primitives.create_default_primitive("Polygon", "Cube")

    def b002(self):
        """Create poly sphere"""
        mtk.Primitives.create_default_primitive("Polygon", "Sphere")

    def b003(self):
        """Create poly cylinder"""
        mtk.Primitives.create_default_primitive("Polygon", "Cylinder")

    def b004(self):
        """Create poly plane"""
        mtk.Primitives.create_default_primitive("Polygon", "Plane")

    def b005(self):
        """Create 6 sided poly cylinder"""
        mtk.Primitives.create_default_primitive("Polygon", "Cylinder", subdivisionsX=6)


# --------------------------------------------------------------------------------------------


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
