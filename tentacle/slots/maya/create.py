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

    def cmb001_init(self, widget):
        """ """
        items = ["Polygon", "NURBS", "Light"]
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
        widget.menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Move the created object to the center point of any selected object(s).",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Uniformly scale the created object to match the averaged scale of any selected object(s).",
        )

    def tb000(self, widget):
        """Create Primitive"""
        baseType = self.sb.create.cmb001.currentText()
        subType = self.sb.create.cmb002.currentText()
        scale = widget.menu.chk001.isChecked()
        translate = widget.menu.chk000.isChecked()

        hist_node = mtk.create_default_primitive(baseType, subType, scale, translate)
        pm.selectMode(object=True)  # place scene select type in object mode.
        pm.select(hist_node)  # select the transform node so that you can see any edits

    def b001(self):
        """Create poly cube"""
        mtk.create_default_primitive("Polygon", "Cube")

    def b002(self):
        """Create poly sphere"""
        mtk.create_default_primitive("Polygon", "Sphere")

    def b003(self):
        """Create poly cylinder"""
        mtk.create_default_primitive("Polygon", "Cylinder")

    def b004(self):
        """Create poly plane"""
        mtk.create_default_primitive("Polygon", "Plane")

    def b005(self):
        """Create 6 sided poly cylinder"""
        cyl = mtk.create_default_primitive("Polygon", "Cylinder")
        mtk.set_node_attributes(cyl, subdivisionsAxis=6)


# --------------------------------------------------------------------------------------------


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
